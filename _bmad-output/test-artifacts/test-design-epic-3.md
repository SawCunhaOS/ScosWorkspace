---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-08-29'
---

# Test Design: Epic 3 — Confiabilidade de Idempotência sob Concorrência e Falha do Redis (jdempotent/Redis, cobertura de qualidade de teste — carve-off da Story 3.18)

**Date:** 2026-08-29
**Author:** Sawcunha (Murat — Test Architect)
**Status:** Draft

---

## Executive Summary

**Scope:** Test design de nível épico para o carve-off da Story 3.18 no Épico 3 (`jdempotent`/Redis): implementação de AD-7 (topologia Redis parametrizada Standalone/Sentinel/Cluster com concorrência real via Testcontainers), AD-9 (throughput/TPS informativo) e a extensão de AD-8 (fail-fast em config inválida) para as 3 topologias — decisões já `[ADOPTED]` na spine `architecture-SawCunhaOS-Foundation-2026-08-29/ARCHITECTURE-SPINE.md`.

**Risk Summary:**

- Total de riscos identificados: 6
- Riscos de alta prioridade (score ≥6): 2 (R-001 infra Sentinel, R-004 desenho do TPS)
- Categorias críticas: TECH (infra Testcontainers), PERF (desenho do teste de TPS)

**Coverage Summary:**

- Cenários P0: 2 (~5h)
- Cenários P1: 4 (~16h)
- Cenários P2/P3: 1 (~4h)
- **Esforço total**: ~25–35h (~3–4.5 dias)

---

## Not in Scope

| Item | Reasoning | Mitigation |
| --- | --- | --- |
| `@ConditionalOnProperty(enabled=false)` fazer a app falhar ao subir | Confirmado explicitamente com o usuário nesta rodada: módulo desligado deliberadamente continua fail-open, sem mudança de comportamento de produção | Nenhuma — comportamento atual mantido, registrado em Deferred na spine |
| Fail-fast quando Redis está alcançável mas fora do ar (não config inválida) | Colidiria com AD-2 herdado (Redis indisponível é sempre fail-open, nunca trava a aplicação) | Nenhuma — decisão explícita já registrada na spine |
| Estender o padrão Failsafe/sufixo `*ITTest` ao módulo `audit` | Fora do escopo desta spine (restrita a `jdempotent`); mesma dor potencial registrada como Deferred para story própria | Revisitar como story dedicada se a mesma dor aparecer em `audit` |
| Hardening do fixture `docker-compose.yml` (`PrimeNumbersJdempotentEnableITTest`/`DisableITTest`, portas fixas 6379/26379) | Bug pré-existente e já documentado em `deferred-work.md`, sem dono; não bloqueia AD-7 (nova classe usa infra própria via `GenericContainer`/porta dinâmica) | Story de hardening dedicada, fora deste escopo |
| Divergência AD-2 (Lua script) vs. implementação real (`SET NX PX`/`setIfAbsent`, Story 3.5) | Já registrada como Deferred na spine; resolução pertence à review da Story 3.5, não a esta frente de testes | Nenhuma ação aqui |

---

## Risk Assessment

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner | Timeline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | TECH | Infra Testcontainers de Sentinel é frágil: o cliente Lettuce pergunta ao Sentinel o endereço do master via `SENTINEL get-master-addr-by-name`, e por padrão o Sentinel anuncia o IP interno do container Docker (inalcançável pela JVM de teste rodando no host); há um bug conhecido e aberto no `bitnami/containers` (#46594) em que `REDIS_SENTINEL_ANNOUNCE_IP` às vezes não é honrado | 3 | 2 | 6 | Pré-alocar (via `ServerSocket` fechado logo em seguida) as portas de host do master e do sentinel ANTES de criar os containers; vincular essas portas explicitamente (`withCreateContainerCmdModifier`/binding fixo, não mapeamento aleatório do Testcontainers) para que o valor já seja conhecido no momento de configurar `REDIS_SENTINEL_ANNOUNCE_IP`/`REDIS_SENTINEL_ANNOUNCE_PORT` (bitnami) apontando para o host reachable pela JVM de teste; adicionar um assert de smoke na infra (`SENTINEL get-master-addr-by-name` retorna o host esperado) ANTES de rodar a lógica de concorrência, para falhar rápido com mensagem clara de infra em vez de um timeout confuso dentro de `tryAcquire`; se não estabilizar no timebox, escalar para decisão explícita do usuário (reduzir o leg de Sentinel a um smoke de wiring) em vez de skip silencioso | Dev | Autoria da Story 3.19 |
| R-004 | PERF | O teste de TPS (AD-9) pode, se todas as operações concorrentes usarem a MESMA chave, medir majoritariamente GETs baratos de `in-progress` em vez de SETs reais (`setIfAbsent`) — o TPS logado ficaria artificialmente alto e não representativo do throughput real de aquisição | 3 | 2 | 6 | Usar N chaves distintas (UUID por operação, ou um pool pequeno reciclado round-robin para também exercitar algum `in-progress` legítimo) — detalhar isso explicitamente na Task da story, já que a Rule de AD-9 na spine não especifica esse ponto | Dev | Autoria da Story 3.19 |

### Medium-Priority Risks (Score 3-4)

| Risk ID | Category | Description | Probability | Impact | Score | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-002 | TECH | Infra Testcontainers de Cluster (bootstrap multi-nó, atribuição de slots) tem complexidade própria distinta da de Sentinel | 2 | 2 | 4 | Usar uma imagem de cluster autocontida (ex.: `grokzen/redis-cluster`, que bootstrapa os nós internamente e suporta IP de anúncio configurável) em vez de montar múltiplos `GenericContainer` manualmente | Dev |
| R-003 | TECH | A classe parametrizada nova poderia, por copy-paste de testes vizinhos, reintroduzir asserts contra `contains`/`store`/`setResponse` isolados — o fluxo antigo que AD-2 herdado proíbe exercitar como caminho de aquisição | 2 | 2 | 4 | Checklist de review explícito: a classe nova só chama `tryAcquire(...)`/inspeciona `Lease`, nunca `contains()`/`store()`/`setResponse()` diretamente | Dev |

### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | Probability | Impact | Score | Action |
| --- | --- | --- | --- | --- | --- | --- |
| R-005 | DATA | Extensão de AD-8 a Standalone assume que `spring.data.redis.port=not-a-number` falha o binding do Spring Boot (`DataRedisProperties.port` é `int`) antes do bean da `ScosJdempotentRedisConfiguration` rodar — inferido do tipo do campo, não confirmado neste run | 1 | 2 | 2 | Verificar rodando o teste isoladamente durante a autoria, antes de considerar a AC atendida |
| R-006 | OPS | 3 novas topologias + concorrência + TPS aumentam o tempo de `mvn -B -pl jdempotent -am verify` no CI (múltiplos containers subindo em sequência) | 2 | 1 | 2 | Monitorar o tempo do step de CI dedicado; sem ação agora |

### Risk Category Legend

- **TECH**: Técnico/Arquitetura (infraestrutura de teste, complexidade de setup)
- **SEC**: Segurança — fora de escopo nesta story
- **PERF**: Performance (desenho do teste de throughput)
- **DATA**: Integridade de dados/config (comportamento de binding assumido, não confirmado)
- **BUS**: Impacto de negócio — nenhum identificado (story é só de testes/build)
- **OPS**: Operações (tempo de CI)

---

## NFR Planning

**Purpose:** Capturar thresholds de NFR específicos deste carve-off, validação planejada e evidência esperada para um `nfr-assess` posterior. Não é uma auditoria final de evidência.

| NFR Category | Requirement / Threshold | Risk Link | Planned Validation | Evidence Needed |
| --- | --- | --- | --- | --- |
| Reliability | Zero duplicação de exclusividade de lock sob concorrência real, nas 3 topologias (critério de sucesso do Épico 3, `epic-3-context.md`) | R-001, R-002, R-003 | Integration test via Testcontainers (`*ITTest`, Failsafe) | Relatório JUnit XML de `mvn -pl jdempotent verify` |
| Performance | TPS informativo, **sem piso mínimo por design** (AD-9 — decisão deliberada, não um threshold ausente) | R-004 | Integration test via Testcontainers com N chaves distintas, log estruturado — **não k6**: `jdempotent` é biblioteca sem endpoint HTTP, a carga é uma chamada de método JVM direta | Log de execução do teste (stdout/relatório Failsafe) |
| Maintainability | Jacoco ≥80% nas áreas tocadas (NFR-3 herdado da spine pai, AD-4) | — | Já coberto pelo perfil `analyze` existente, sem ação nova | Relatório Jacoco existente |

**Unknown thresholds:** Nenhum por omissão. "Sem piso de TPS" é decisão deliberada de AD-9, documentada como tal — não é um gap a esclarecer.

---

## Entry Criteria

- [x] Spine de arquitetura com AD-7/AD-8/AD-9 `[ADOPTED]` (amendment desta sessão para AD-8)
- [x] Fundação Failsafe/sufixo `*ITTest` já wireada (Story 3.18, done)
- [ ] Story 3.19 (arquivo de story formal) criada a partir deste test design
- [ ] Padrão de infra Sentinel (R-001) validado manualmente antes de considerar a Task concluída

## Exit Criteria

- [ ] Todos os testes P0 passando (bateria completa de concorrência em Standalone)
- [ ] Testes P1 passando ou triados (smoke Sentinel/Cluster + fail-fast Standalone/Sentinel) — ver gate específico de R-001 abaixo
- [ ] Nenhum bug de alta severidade aberto
- [ ] `mvn -pl jdempotent test` continua sem subir Docker (não regredir AD-6)

---

## Test Coverage Plan

### P0 (Critical)

**Criteria**: Garantia central do Épico 3 (exclusividade do lock sob concorrência real), sem workaround se quebrar.

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| AD-7 — bateria completa de concorrência (10 threads) contra `tryAcquire→Lease` em Standalone | Integration (`*ITTest`) | R-003 | 2 | Dev | Migrar/absorver `RedisIdempotentRepositoryTryAcquireITTest` (Story 3.5) para dentro da classe parametrizada, não recriar |

**Total P0**: 2 tests, ~5 hours

### P1 (High)

**Criteria**: Extensão de garantia já adotada (AD-8) a topologias que faltavam, e validação de wiring de conexão nas topologias mais complexas de montar em Testcontainers.

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| AD-7 — smoke de concorrência (2–3 chamadas) em Sentinel | Integration (`*ITTest`) | R-001 | 1 | Dev | Maior parte do esforço é a infra (ver mitigação R-001), não a lógica do teste |
| AD-7 — smoke de concorrência (2–3 chamadas) em Cluster | Integration (`*ITTest`) | R-002 | 1 | Dev | Usar imagem de cluster autocontida |
| AD-8 estendido — fail-fast config inválida em Standalone (`port=not-a-number`) | Unit (`ApplicationContextRunner`) | R-005 | 1 | Dev | Mesmo padrão da Story 3.18 para Cluster |
| AD-8 estendido — fail-fast config inválida em Sentinel (`sentinel.nodes` com porta não numérica) | Unit (`ApplicationContextRunner`) | R-005 | 1 | Dev | Falha dentro de `sentinelConfiguration()` via `Integer.parseInt`, sem depender de rede |

**Total P1**: 4 tests, ~16 hours

### P2 (Medium)

**Criteria**: Observabilidade informativa, sem gate de correção.

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
| --- | --- | --- | --- | --- | --- |
| AD-9 — TPS informativo, N operações `tryAcquire` concorrentes com chaves distintas | Integration (`*ITTest`, reaproveita container Standalone) | R-004 | 1 | Dev | Assert só de ausência de erro; log do TPS medido |

**Total P2**: 1 test, ~4 hours

### P3 (Low)

Nenhum cenário P3 identificado (sem UI/E2E, sem funcionalidade cosmética neste escopo).

**Total P3**: 0 tests, 0 hours

---

## Execution Order

### Smoke Tests (<5 min)

**Purpose**: Feedback rápido, pega quebras óbvias sem subir Docker

- [ ] `mvn -pl jdempotent test` — só unit, inclui os 2 novos fail-fast (Standalone/Sentinel) (~1min)

**Total**: 2 cenários (dentro da suíte unit existente)

### P0 Tests (<10 min)

**Purpose**: Validação da garantia central de exclusividade do lock

- [ ] Bateria completa de concorrência — Standalone (Integration)

**Total**: 2 cenários (métodos migrados de `RedisIdempotentRepositoryTryAcquireITTest`)

### P1 Tests (<30 min)

**Purpose**: Cobertura de wiring das topologias restantes + fail-fast completo

- [ ] Smoke de concorrência — Sentinel (Integration)
- [ ] Smoke de concorrência — Cluster (Integration)
- [ ] Fail-fast Standalone/Sentinel (Unit, já rodou no smoke acima)

**Total**: 4 cenários

### P2/P3 Tests (<60 min)

**Purpose**: Observabilidade de throughput

- [ ] TPS informativo (Integration)

**Total**: 1 cenário

---

## Resource Estimates

### Test Development Effort

| Priority | Count | Hours/Test | Total Hours | Notes |
| --- | --- | --- | --- | --- |
| P0 | 2 | 2.5 | 5 | Migração de teste existente, não do zero |
| P1 | 4 | 4.0 | 16 | Maior parte é infra Sentinel/Cluster (R-001/R-002), não a lógica do teste |
| P2 | 1 | 4.0 | 4 | Desenho de medição/log de TPS + N chaves distintas |
| **Total** | **7** | **-** | **~25** | **~3–4.5 dias (faixa larga por incerteza de infra Sentinel)** |

### Prerequisites

**Test Data:**

- Chaves de idempotência via UUID por operação (concorrência e TPS) — sem factory dedicada necessária, `IdempotencyKey` já é suficiente

**Tooling:**

- Testcontainers (`testcontainers-bom` já gerenciado, `2.0.5`) para os 3 containers de topologia
- `bitnami/redis` + `bitnami/redis-sentinel` (Sentinel) — imagens já em uso pelo módulo (docker-compose existente)
- `grokzen/redis-cluster` (ou equivalente autocontido) para Cluster — nova imagem, avaliar versão atual antes de fixar

**Environment:**

- Docker disponível no runner de CI (já um pré-requisito do módulo, `PrimeNumbersJdempotentEnableITTest` já exige isso)
- Sem dependência de rede externa — todos os containers são locais ao runner

---

## Quality Gate Criteria

### Pass/Fail Thresholds

- **P0 pass rate**: 100% (bateria completa Standalone, sem exceção)
- **P1 pass rate**: ≥95% — se a infra de Sentinel (R-001) não estabilizar no timebox, escalar para decisão explícita do usuário (reduzir o smoke de Sentinel a um teste de wiring sem concorrência) em vez de skip silencioso
- **P2 pass rate**: informativo, sem gate de valor — gate é só "não lançou exceção" (AD-9 por design)
- **High-risk mitigations**: R-001 e R-004 com mitigação aplicada antes de considerar a story pronta para review

### Coverage Targets

- Garantia de exclusividade do lock: 100% das 3 topologias com pelo menos um teste de concorrência real
- Fail-fast de config inválida: 100% das 3 topologias (Cluster já feito na 3.18)

### Non-Negotiable Requirements

- [ ] Todos os testes P0 passam
- [ ] Nenhum item de risco alto (≥6) sem mitigação aplicada ou decisão explícita do usuário registrada
- [ ] `mvn -pl jdempotent test` continua sem subir Docker (não regredir AD-6, Story 3.18)
- [ ] Nenhum teste novo assert contra `contains`/`store`/`setResponse` isolados (R-003)

---

## Mitigation Plans

### R-001: Infra Testcontainers de Sentinel frágil (Score: 6)

**Mitigation Strategy:** Pré-alocar portas de host (master + sentinel) via `ServerSocket` fechado antes de criar os containers; vincular essas portas explicitamente ao criar os containers (não deixar o Testcontainers escolher aleatoriamente); configurar `REDIS_SENTINEL_ANNOUNCE_IP`/`REDIS_SENTINEL_ANNOUNCE_PORT` (bitnami) com o host/porta pré-alocados, reachable pela JVM de teste; adicionar assert de smoke da própria infra (`SENTINEL get-master-addr-by-name` retorna o host esperado) antes da lógica de concorrência.
**Owner:** Dev (autoria da Story 3.19)
**Timeline:** Durante a implementação da Story 3.19
**Status:** Planned
**Verification:** Teste de smoke passa de forma reproduzível em pelo menos 3 execuções locais consecutivas antes de considerar a Task concluída; se não estabilizar, escalar ao usuário.

### R-004: Desenho do teste de TPS mede o caminho errado (Score: 6)

**Mitigation Strategy:** Usar N chaves distintas (UUID por operação) nas operações concorrentes do teste de TPS, garantindo que a maioria das operações exercite o `SET NX PX` real, não o caminho barato de `in-progress`.
**Owner:** Dev (autoria da Story 3.19)
**Timeline:** Durante a implementação da Story 3.19
**Status:** Planned
**Verification:** Revisão de código confirma N chaves distintas (não uma única chave compartilhada) antes de aceitar o teste.

---

## Assumptions and Dependencies

### Assumptions

1. `spring.data.redis.port=not-a-number` de fato falha o binding do Spring Boot antes do bean da `ScosJdempotentRedisConfiguration` rodar (R-005, não confirmado neste run).
2. As imagens `bitnami/redis`/`bitnami/redis-sentinel` já usadas pelo docker-compose do módulo continuam adequadas para a nova infra Testcontainers (só muda o mecanismo de porta/anúncio, não a imagem).
3. O runner de CI onde `mvn -B -pl jdempotent -am verify` roda tem Docker disponível e suporta os 3 containers de topologia sem limite de recursos que cause timeout.

### Dependencies

1. Fundação Failsafe/sufixo `*ITTest` da Story 3.18 (done) — bloqueante, já satisfeita.
2. Amendment desta sessão à spine (AD-8 estendido às 3 topologias) — já fechado (`ARCHITECTURE-SPINE.md`, `.memlog.md`).

### Risks to Plan

- **Risk**: R-001 (infra Sentinel) não estabiliza dentro do timebox da story.
  - **Impact**: Leg de Sentinel de AD-7 fica incompleto ou instável no CI.
  - **Contingency**: Reduzir o escopo do leg de Sentinel a um teste de wiring (sem concorrência real), registrar em `deferred-work.md`, e levar a decisão ao usuário explicitamente antes de fechar a story.

---

## Follow-on Workflows (Manual)

- Rodar `/bmad-build` (ou o fluxo de autoria de story equivalente) para produzir o arquivo formal da Story 3.19 a partir deste test design.
- Rodar `bmad-testarch-automate` depois da implementação, se cobertura adicional além deste plano for necessária.

---

## Approval

**Test Design Approved By:**

- [ ] Product Manager: — Date: —
- [ ] Tech Lead: — Date: —
- [ ] QA Lead: — Date: —

**Comments:**

---

## Interworking & Regression

| Service/Component | Impact | Regression Scope |
| --- | --- | --- |
| `RedisIdempotentRepositoryTryAcquireITTest` (Story 3.5) | Migrado/absorvido para dentro da nova classe parametrizada — não deve regredir os 2 testes já existentes | Os 2 métodos de teste atuais devem continuar passando após a migração |
| `ScosJdempotentRedisConfigurationTest` (Story 3.1/3.18) | Ganha 2 novos métodos de fail-fast (Standalone, Sentinel) — os 4 métodos já existentes não devem regredir | Os 4 testes já existentes (3 topologias válidas + fail-fast Cluster) |
| CI — step `Run jdempotent integration tests` (Story 3.18) | Tempo de execução aumenta (mais containers) | Nenhuma mudança de comportamento esperada além do tempo, salvo decisão explícita sobre R-001 |

---

## Appendix

### Knowledge Base References

- `risk-governance.md` — framework de classificação de risco
- `probability-impact.md` — metodologia de scoring de risco
- `test-levels-framework.md` — seleção de nível de teste
- `test-priorities-matrix.md` — priorização P0-P3

### Related Documents

- Epic: `_bmad-output/implementation-artifacts/epic-3-context.md`
- Architecture: `_bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-29/ARCHITECTURE-SPINE.md`
- Story anterior (fundação): `_bmad-output/implementation-artifacts/3-18-qualidade-de-teste-do-jdempotent-redis.md`
- Trabalho adiado relacionado: `_bmad-output/implementation-artifacts/deferred-work.md`

---

**Generated by**: BMad TEA Agent - Test Architect Module (Murat)
**Workflow**: `bmad-testarch-test-design`
**Version**: 4.0 (BMad v6)
