---
runScope: 'epic-level'
runKey: 'epic-3'
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-08-29'
inputDocuments:
  - '_bmad-output/implementation-artifacts/epic-3-context.md'
  - '_bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-29/ARCHITECTURE-SPINE.md'
  - '_bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-29/.memlog.md'
  - '_bmad-output/implementation-artifacts/3-18-qualidade-de-teste-do-jdempotent-redis.md'
  - '_bmad-output/implementation-artifacts/deferred-work.md'
  - 'jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java'
  - 'jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfiguration.java'
  - 'jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTryAcquireITTest.java'
  - 'jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/InMemoryIdempotentRepositoryTryAcquireTest.java'
  - 'jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfigurationTest.java'
  - 'web:Testcontainers Redis Sentinel dynamic mapped port announce-ip (2026-08-29)'
  - 'web:bitnami/containers issue #46594 (REDIS_SENTINEL_ANNOUNCE_IP not honored)'
---

## Step 1 & 2

(ver seções anteriores — Epic-Level, epic_num=3, contexto e coverage existente carregados)

## Step 3: Testability & Risk Assessment

### 🚨 Testability Concern (ACTIONABLE)

**A parametrização por topologia da AD-7 provavelmente triplica custo/flakiness sem triplicar confiança real.** A atomicidade de `tryAcquire` vem do primitivo `SET key value NX PX` do próprio Redis (garantia do servidor, idêntica em Standalone/Sentinel/Cluster) — o que muda entre topologias é só a **resolução da conexão** (`ScosJdempotentRedisConfiguration.redisConfiguration()`), já coberta sem infra real pela Story 3.1 (`ScosJdempotentRedisConfigurationTest`, `ApplicationContextRunner`). Rodar a bateria COMPLETA de concorrência (10+ threads) 3x (uma por topologia) testa 3x o mesmo primitivo do servidor e 1x cada wiring de conexão — desproporcional ao risco real, e infla a superfície de flakiness exatamente nas topologias mais frágeis de montar via Testcontainers (Sentinel, Cluster).

**Recomendação:** bateria completa de concorrência (10+ threads, todos os asserts do contrato Lease) só em **Standalone** (migrando/absorvendo `RedisIdempotentRepositoryTryAcquireITTest` da Story 3.5 para dentro da classe parametrizada, em vez de recriar); em **Sentinel** e **Cluster**, um **smoke de concorrência mais barato** (2–3 chamadas concorrentes) que prova só que o wiring da topologia entrega o mesmo resultado do contrato (exatamente uma `acquired`, as demais `in-progress`) — suficiente para a garantia que falta (conexão correta), sem pagar o custo total da bateria completa 3x.

### ✅ Testability Assessment Summary

- Contrato `tryAcquire(...) → Lease` já é a única superfície testada (Story 3.5) — nenhum acoplamento a `contains`/`store`/`setResponse` isolados nos testes novos, coerente com AD-2 herdado.
- `RedisIdempotentRepositoryTryAcquireITTest` já demonstra o padrão correto de container Testcontainers de porta dinâmica (evita a fragilidade de porta fixa documentada em `deferred-work.md`) — ponto de partida real para a nova classe, não teoria.
- `ScosJdempotentRedisConfigurationTest` já isola resolução de topologia sem infra real (`ApplicationContextRunner`) — base direta para estender o fail-fast (AD-8) a Standalone/Sentinel sem inventar padrão novo.

### ASRs (Architecturally Significant Requirements)

- **ACTIONABLE**: AD-9 (TPS) não especifica quantas *chaves distintas* usar. Se todas as operações concorrentes usarem a MESMA chave, toda operação após a primeira retorna `in-progress` num GET barato (não um SET real) — o TPS medido não representaria throughput real de aquisição. Precisa de N chaves distintas (ou um pool pequeno reciclado) — ver risco PERF-004 abaixo.
- **FYI**: AD-2 herdado (fail-open + circuit breaker) não é exercitado por nenhum teste desta spine — o circuit breaker (Story 3.7) ainda está `ready-for-dev`; já registrado como Deferred na spine, não uma lacuna desta story.

### Risk Assessment

| Risk ID | Categoria | Descrição | Prob. | Impacto | Score | Ação |
| --- | --- | --- | --- | --- | --- | --- |
| R-001 | TECH | Infra Testcontainers de Sentinel é frágil: cliente Lettuce pede o endereço do master ao Sentinel, que por padrão anuncia o IP interno do container Docker (inalcançável pela JVM de teste no host); bug conhecido no bitnami/containers (#46594) onde `REDIS_SENTINEL_ANNOUNCE_IP` às vezes não é honrado. | 3 | 2 | 6 | MITIGATE |
| R-002 | TECH | Infra Testcontainers de Cluster (bootstrap multi-nó, atribuição de slots) tem complexidade própria distinta de Sentinel. | 2 | 2 | 4 | MONITOR |
| R-003 | TECH | Classe parametrizada nova poderia, por copy-paste de testes vizinhos, reintroduzir asserts contra `contains`/`store`/`setResponse` isolados — o fluxo antigo que AD-2 proíbe exercitar como caminho de aquisição. | 2 | 2 | 4 | MONITOR |
| R-004 | PERF | Teste de TPS (AD-9) usando UMA única chave para todas as operações concorrentes mede principalmente GETs baratos de `in-progress`, não SETs reais — TPS logado ficaria artificialmente alto e não representativo. | 3 | 2 | 6 | MITIGATE |
| R-005 | DATA | Extensão de AD-8 a Standalone assume que `spring.data.redis.port=not-a-number` falha o binding do Spring Boot (`DataRedisProperties.port` é `int`) antes mesmo do bean da `ScosJdempotentRedisConfiguration` rodar — comportamento não confirmado neste run, só inferido do tipo do campo. | 1 | 2 | 2 | DOCUMENT (verificar rodando o teste antes de dar a story por concluída) |
| R-006 | OPS | 3 novas topologias + concorrência + TPS aumentam o tempo de `mvn -B -pl jdempotent -am verify` no CI (múltiplos containers subindo). | 2 | 1 | 2 | DOCUMENT |

**Nenhum risco score=9 (BLOCK).** R-001 e R-004 (score 6, MITIGATE) têm mitigação concreta abaixo; nenhum bloqueia a story, mas ambos precisam de decisão explícita na autoria (não silenciosa).

### NFR Planning

| Categoria | Requisito/Threshold | Risco vinculado | Validação planejada | Evidência esperada |
| --- | --- | --- | --- | --- |
| Reliability | Zero duplicação de exclusividade de lock sob concorrência real, nas 3 topologias (critério de sucesso do Épico 3) | R-001, R-002, R-003 | Integration test via Testcontainers (`*ITTest`, Failsafe) | Relatório JUnit XML de `mvn -pl jdempotent verify` |
| Performance | TPS informativo, **sem piso mínimo por design** (AD-9) | R-004 | Integration test via Testcontainers, log estruturado (não k6 — `jdempotent` é biblioteca, sem endpoint HTTP para k6 apontar; a carga é uma chamada de método JVM direta) | Log de execução do teste (stdout/relatório Surefire-Failsafe) |
| Maintainability | Jacoco ≥80% nas áreas tocadas (NFR-3 herdado, AD-4) | — | Já coberto pelo perfil `analyze` existente | Relatório Jacoco existente |
| Security | N/A nesta story (fora de escopo — allowlist do `PolymorphicRedisSerializer` é Story 3.16) | — | — | — |

**Thresholds ausentes:** nenhum por omissão — o "sem piso de TPS" é decisão deliberada de AD-9 (não é gap, está documentado como tal).

## Step 4: Coverage Plan & Execution Strategy

### Coverage Matrix

**P0**

| Requisito | Nível | Risco | Qtde testes | Owner | Notas |
| --- | --- | --- | --- | --- | --- |
| AD-7 — bateria completa de concorrência real (10 threads) contra `tryAcquire→Lease` em Standalone, migrando `RedisIdempotentRepositoryTryAcquireITTest` (Story 3.5) para a classe parametrizada | Integration (`*ITTest`, Testcontainers) | R-003 | 2 (os 2 métodos já existentes, migrados) | Dev | Sem workaround se a exclusividade do lock quebrar em produção — é o critério de sucesso do Épico 3 |

**Total P0**: 2 testes, ~4–6 horas (migração + adaptação para o enum/`@MethodSource` de topologia)

**P1**

| Requisito | Nível | Risco | Qtde testes | Owner | Notas |
| --- | --- | --- | --- | --- | --- |
| AD-7 — smoke de concorrência (2–3 chamadas) em Sentinel e Cluster, mesmo contrato Lease | Integration (`*ITTest`, Testcontainers) | R-001, R-002 | 2 (1 por topologia) | Dev | Ver mitigação de R-001 (pré-alocar porta + announce-ip/port + assert de smoke da própria infra antes da lógica) |
| AD-8 estendido — fail-fast de config inválida em Standalone (`port=not-a-number`) e Sentinel (`sentinel.nodes` com porta não numérica) | Unit (`ApplicationContextRunner`, sem infra real) | R-005 | 2 | Dev | Mesmo padrão já usado para Cluster (Story 3.18) |

**Total P1**: 4 testes, ~10–16 horas (Sentinel smoke inclui o trabalho de infra do R-001)

**P2**

| Requisito | Nível | Risco | Qtde testes | Owner | Notas |
| --- | --- | --- | --- | --- | --- |
| AD-9 — teste de TPS informativo, N operações `tryAcquire` concorrentes com chaves distintas, log do TPS medido | Integration (`*ITTest`, Testcontainers, reaproveita o container Standalone da classe parametrizada) | R-004 | 1 | Dev | Sem gate; assert só de ausência de erro/exceção |

**Total P2**: 1 teste, ~3–5 horas

**P3**

Nenhum cenário P3 identificado neste escopo (não há UI/E2E nem funcionalidade cosmética aqui).

### NFR Coverage e Evidência

- Reliability → coberto pela matriz P0/P1 acima (Testcontainers real, 3 topologias).
- Performance (TPS) → coberto por P2 acima; evidência = log estruturado, não gate de CI.
- Maintainability → sem ação nova, herdado do perfil `analyze` já existente.

### Execution Strategy

- **PR**: `mvn -pl jdempotent test` (só unit — inclui os 2 novos testes de fail-fast AD-8, rápido, sem Docker).
- **Nightly/CI dedicado** (já existe o step escopado da Story 3.18, `mvn -B -pl jdempotent -am verify`): roda a classe parametrizada completa (Standalone P0 + Sentinel/Cluster P1 smoke) + o teste de TPS (P2). Não adicionar ao PR-fast-path — Testcontainers de 3 topologias facilmente ultrapassa os <15min recomendados para PR.

### Resource Estimates

| Prioridade | Qtde | Horas/teste | Total | Notas |
| --- | --- | --- | --- | --- |
| P0 | 2 | ~2.5 | ~5h | Migração de teste existente, não do zero |
| P1 | 4 | ~4 | ~16h | Maior parte é a infra de Sentinel (R-001) e Cluster (R-002), não a lógica do teste em si |
| P2 | 1 | ~4 | ~4h | Desenho de medição/log de TPS + N chaves distintas |
| **Total** | **7** | – | **~25–35h (~3–4.5 dias)** | Faixa larga por causa da incerteza de infra Sentinel (R-001) |

### Quality Gates

- P0 (Standalone, bateria completa): 100% pass, obrigatório.
- P1 (Sentinel/Cluster smoke + fail-fast Standalone/Sentinel): ≥95% pass; se a infra de Sentinel (R-001) não estabilizar dentro do timebox, **escalar para decisão explícita do usuário** (reduzir a smoke de Sentinel a um teste de wiring sem concorrência, ou aceitar adiar o leg de Sentinel para uma story de hardening) — nunca skip silencioso.
- P2 (TPS): sem gate de valor (AD-9 é informativo por design); gate é só "não lançou exceção".
- `mvn -pl jdempotent test` continua sem subir Docker (não regredir AD-6).
