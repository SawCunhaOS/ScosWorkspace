---
name: 'jdempotent — Qualidade de Teste Redis'
type: architecture-spine
purpose: build-substrate
altitude: epic
paradigm: 'Layered modular library (Spring Boot autoconfiguration)'
scope: 'Estrategia de testes do modulo jdempotent (parte Redis): separacao unit/integration, cobertura das 3 topologias (Standalone/Sentinel/Cluster) com infra real, fail-fast em config invalida, concorrencia real e throughput informativo'
status: final
created: '2026-08-29'
updated: '2026-08-29'
binds: [AD-1, AD-2, AD-4, AD-5]
sources: ['_bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/ARCHITECTURE-SPINE.md']
companions: []
---

# Architecture Spine — jdempotent — Qualidade de Teste Redis

## Design Paradigm

Herdado sem alteração da spine pai: **Layered modular library** (Spring Boot autoconfiguration). Esta spine não introduz paradigma novo — só regras de teste dentro do módulo `jdempotent` já existente.

## Inherited Invariants

| Inherited | From parent | Binds here |
| --- | --- | --- |
| AD-1 — Fronteira e direção de dependência | architecture-SawCunhaOS-Foundation-2026-08-19 | Testes novos vivem dentro do próprio módulo `jdempotent` (scope `test`); nenhum módulo novo é criado só para infraestrutura de teste |
| AD-2 — Contrato de aquisição de idempotência | architecture-SawCunhaOS-Foundation-2026-08-19 | Todo teste de concorrência/topologia desta spine valida contra `tryAcquire(key, payloadHash, ttl) → Lease` e o comportamento fail-open com circuit breaker — nunca contra o fluxo antigo `contains → store → setResponse` |
| AD-4 — Piso de documentação obrigatório | architecture-SawCunhaOS-Foundation-2026-08-19 | Toda classe de teste nova segue o mesmo piso de Javadoc já cobrado pelo Checkstyle no módulo |
| AD-5 — ArchUnit como mecanismo de imposição | architecture-SawCunhaOS-Foundation-2026-08-19 | Nenhuma regra cross-módulo nasce aqui; o split unit/IT desta spine é local ao `jdempotent`, não uma regra ArchUnit |

## Invariants & Rules

### AD-6 — Split unit/integration test via Failsafe + sufixo IT [ADOPTED]

- **Binds:** módulo `jdempotent`, toda classe de teste que sobe Testcontainers/Docker Compose
- **Prevents:** `mvn test` (Surefire) subindo Docker durante execução de unit test — causa raiz confirmada dos erros `ContainerLaunchException`/porta já alocada documentados nos Dev Agent Records das Stories 3.1, 3.4 e 3.5
- **Rule:** `maven-failsafe-plugin:3.5.4` (mesma linha de release do `maven-surefire-plugin:3.5.4` já herdado do `scos-bom`) adicionado ao `pom.xml` do `jdempotent`, bindado às fases `integration-test`/`verify`. Sufixo único e obrigatório: `*ITTest.java` (mantém a convenção já em uso por `RedisIdempotentRepositoryTryAcquireITTest` da Story 3.5 — não introduzir um segundo sufixo `*IT.java`). **Os padrões default de include/exclude do Surefire/Failsafe não reconhecem `*ITTest.java`** (Surefire inclui `**/*Test.java` por padrão — que colide e pega `*ITTest.java` hoje; Failsafe inclui só `**/IT*.java`/`**/*IT.java`/`**/*ITCase.java` — que NÃO pega `*ITTest.java`), então ambos os plugins recebem configuração explícita: `maven-surefire-plugin` com `<excludes><exclude>**/*ITTest.java</exclude></excludes>`, `maven-failsafe-plugin` com `<includes><include>**/*ITTest.java</include></includes>`. `mvn test` roda só unit (rápido, sem Docker); `mvn verify` roda unit + integration. `PrimeNumbersJdempotentEnableTest`/`PrimeNumbersJdempotentDisableTest` (hoje sem sufixo IT, rodando incorretamente sob Surefire) são renomeadas para `*ITTest`. `InMemoryIdempotentRepositoryTryAcquireTest` (Story 3.5, sem Testcontainers) permanece unit test — só sobe `ConcurrentHashMap`, não Docker. **CI (`.github/workflows/build.yml`) hoje só roda `mvn -B test`/`mvn -B -Panalyze test`, nunca `verify`** — sem ajuste, o AD-6 teria o efeito líquido de PARAR de rodar os testes de integração em CI (regressão, não correção). Em vez de trocar a fase dos steps globais existentes (o que rodaria `verify` no reactor inteiro, afetando módulos sem Failsafe configurado), um novo step dedicado e escopado — `mvn -B -pl jdempotent -am verify` — é adicionado ao job de build, logo após o step "Run tests" (linha 45), preservando o comportamento e o tempo de execução dos demais módulos.

### AD-7 — Cobertura de topologia Redis parametrizada [ADOPTED]

- **Binds:** `RedisIdempotentRepository`, as 3 topologias suportadas (Standalone, Sentinel, Cluster)
- **Prevents:** triplicar a mesma lógica de asserts em 3 classes `ITTest` quase idênticas; divergência silenciosa entre o que cada topologia realmente valida
- **Rule:** uma única classe `*ITTest` parametrizada (`@ParameterizedTest` + `@MethodSource` ou enum de topologia) monta a infraestrutura Testcontainers correspondente por topologia e roda o mesmo conjunto de asserts **só através do contrato `tryAcquire(...) → Lease`** (AD-2 herdado) — nunca via `contains`/`store`/`setResponse` isolados, que são o fluxo antigo que AD-2 proíbe exercitar como caminho de aquisição de lock. Um `@BeforeEach` cria e destrói a instância de `RedisIdempotentRepository` por método de teste, mas os containers Testcontainers (um por topologia) sobem uma única vez por classe (`static`, ciclo de vida da classe) e são compartilhados entre os métodos parametrizados da mesma topologia — evita o custo de subir 3 infraestruturas completas por método de teste. Complementa — não substitui — `ScosJdempotentRedisConfigurationTest` (Story 3.1, `ApplicationContextRunner` sem infra real, continua validando só a resolução de `RedisConfiguration`).

### AD-8 — Fail-fast em configuração de Redis inválida, nas 3 topologias (não em Redis inalcançável) [ADOPTED]

- **Binds:** `ScosJdempotentRedisConfiguration`, inicialização do contexto Spring, as 3 topologias suportadas (Standalone, Sentinel, Cluster)
- **Prevents:** erro tardio e obscuro (NPE ou exceção genérica numa chamada de negócio real) quando a configuração de Redis está malformada/incompleta (ex.: `cluster.nodes` vazio, `sentinel.master` ausente, host/porta de standalone inválidos, topologia ambígua)
- **Rule:** teste de contexto (`ApplicationContextRunner`) prova que, com uma configuração de Redis **malformada/incompleta** (não com Redis simplesmente fora do ar), o contexto falha a subir (`context.getStartupFailure()` presente) com causa raiz identificável na mensagem/causa da exceção — fail-fast, nunca fail-silent. **Escopo estendido às 3 topologias** (amendment desta rodada): a Story 3.18 cobriu só Cluster (`cluster.max-redirects=not-a-number`); a próxima story adiciona o mesmo padrão para Standalone (ex.: `port` não-numérico) e Sentinel (ex.: `sentinel.master` ausente com `sentinel.nodes` presente), sempre sem depender de rede real, no mesmo `ScosJdempotentRedisConfigurationTest`. **Continua explicitamente restrito a config inválida.** "Redis alcançável na rede mas indisponível/fora do ar" **não** é coberto por este AD — a conexão é `lazy` (`ScosJdempotentRedisConfiguration` não seta `validateConnection=true`), então esse caso hoje não falha o contexto, e forçá-lo a falhar colidiria com AD-2 herdado (Redis indisponível deve ser sempre fail-open, nunca travar a aplicação). Este AD também não cobre `@ConditionalOnProperty(enabled=false)` (desligamento deliberado do módulo) — confirmado nesta rodada (usuário, 2026-08-29) que módulo desligado deliberadamente **continua fail-open**, sem mudança de comportamento de produção; esse caminho permanece em Deferred.

### AD-9 — Throughput informativo, não gate [ADOPTED]

- **Binds:** teste de TPS do `jdempotent` contra Redis real
- **Prevents:** gate de CI flaky por variação de hardware/ambiente compartilhado
- **Rule:** teste `*ITTest` via Testcontainers dispara um **número fixo de operações** `tryAcquire` concorrentes (não uma janela de tempo fixo — número fixo dá um denominador determinístico para o cálculo de TPS; janela de tempo fixo teria throughput variável por definição, tornando o log incomparável entre execuções) e **loga** o TPS resultante (operações / tempo decorrido medido); o assert cobre apenas ausência de erro/exceção durante a execução, nunca um piso mínimo de TPS. Mesma fase Failsafe (AD-6) dos demais testes de integração.

## Consistency Conventions

| Concern | Convention |
| --- | --- |
| Nome de classe de teste | `*Test` = unit (Surefire); `*IT.java`/`*ITTest.java` = integração via Testcontainers/Docker (Failsafe) — AD-6 |
| Fase de build | `mvn test` = só unit; `mvn verify` = unit + integration |
| Assert de throughput | Sempre log/relatório, nunca `assertTrue(tps > limiar)` — AD-9 |

## Stack

| Name | Version |
| --- | --- |
| maven-failsafe-plugin (novo) | `3.5.4` (não gerenciado pelo `scos-bom`; mesma versão do `maven-surefire-plugin` já herdado — Surefire e Failsafe são liberados em lockstep pelo projeto Apache Maven) |
| testcontainers-bom | `2.0.5` (já gerenciado pelo `scos-bom`, sem mudança) |

## Structural Seed

```text
jdempotent/
  src/test/java/.../core/aspect/          # unit tests (*Test) — inalterado
  src/test/java/.../core/datasource/      # InMemoryIdempotentRepositoryTryAcquireTest (*Test, unit)
  src/test/java/.../redis/repository/     # *ITTest (Failsafe) — RedisIdempotentRepositoryTryAcquireITTest,
                                           # nova classe parametrizada de topologia, novo teste de TPS
  src/test/java/.../redis/configuration/  # ScosJdempotentRedisConfigurationTest (*Test, unit, sem infra real)
                                           # + novo teste de fail-fast (config invalida) nesta mesma classe ou uma nova *Test
```

## Capability → Architecture Map

| Capability / Área | Vive em | Governado por |
| --- | --- | --- |
| Split unit/integration | `jdempotent/pom.xml` (Failsafe) | AD-6 |
| Cobertura de topologia Redis | `jdempotent/redis/repository` | AD-7, AD-1, AD-2 (herdado) |
| Fail-fast config inválida | `jdempotent/redis/configuration` | AD-8 |
| Throughput informativo | `jdempotent/redis/repository` | AD-9 |

## Deferred

- **Fail-fast quando o Redis está alcançável mas fora do ar (não config inválida)** — colidiria com o fail-open do AD-2 herdado; a aplicação deve continuar subindo normalmente nesse caso (decisão explícita do usuário nesta run, não um gap por omissão).
- **Extensão do padrão Failsafe/sufixo IT para o módulo `audit`** (também usa Testcontainers hoje, mesma dor potencial de Docker subindo sob Surefire) — decisão explícita do usuário de manter esta spine restrita ao `jdempotent`; revisitar como story própria se a mesma dor aparecer em `audit`.
- **`@ConditionalOnProperty(enabled=false)` do jdempotent** (desligamento deliberado, distinto do cenário fail-fast do AD-8) — não pedido nesta rodada; **reconfirmado explicitamente com o usuário na rodada de amendment (2026-08-29)**: módulo desligado continua fail-open, sem mudança de comportamento de produção. Revisitar só se surgir um AC específico para esse caminho.
- **Hardening do fixture `docker-compose.yml`** (`PrimeNumbersJdempotentEnableITTest`/`DisableITTest`, portas fixas `6379`/`26379`, flakiness documentada em `deferred-work.md`) — não bloqueia AD-7 (a nova classe parametrizada monta sua própria infra via `GenericContainer`/porta dinâmica, não reusa esse compose), mas segue sem dono; story dedicada de hardening continua fora de escopo desta spine.
- **Divergência entre AD-2 (Lua script) e a implementação real do `tryAcquire`** (Story 3.5 usou `SET NX PX` via `setIfAbsent`, não um script Lua) — não é escopo desta spine de testes; fica registrada aqui para não se perder, mas a resolução (aceitar a implementação como satisfazendo AD-2 na prática, ou exigir Lua script) é da review da Story 3.5, não desta frente de trabalho.
- **Cobertura de "fail-open com circuit breaker" (AD-2 herdado) nos testes de topologia/concorrência desta spine** — não implementada aqui porque o circuit breaker em si (Resilience4j, Story 3.7) ainda está `ready-for-dev`, não `done`; não há comportamento de produção para testar ainda. Revisitar como amendment desta spine (ou uma AD nova) quando a Story 3.7 for implementada.
