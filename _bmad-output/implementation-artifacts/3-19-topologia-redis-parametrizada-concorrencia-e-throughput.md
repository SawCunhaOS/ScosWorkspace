---
title: 'Cobertura de topologia Redis parametrizada (Standalone/Sentinel/Cluster), fail-fast nas 3 topologias e throughput informativo'
type: 'chore'
created: '2026-08-29'
status: 'done'
baseline_commit: 'f77a2be30cb6d1134535f67a43576f1428ee9f65'
review_loop_iteration: 2
context: ['{project-root}/_bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-29/ARCHITECTURE-SPINE.md', '{project-root}/_bmad-output/test-artifacts/test-design-epic-3.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** O módulo `jdempotent` (Redis) tem hoje concorrência real testada só implicitamente em Standalone (`RedisIdempotentRepositoryTryAcquireITTest`, Story 3.5), fail-fast de config inválida testado só para Cluster (Story 3.18), e nenhum teste de throughput/TPS. Isso é o carve-off explícito da Story 3.18 (registrado em `deferred-work.md`), liberado agora que a fundação Failsafe/sufixo `*ITTest` (AD-6) já está wireada.

**Approach:** Implementar as 3 decisões já `[ADOPTED]` na spine (AD-7, AD-8 estendido, AD-9), seguindo o test design de risco em `test-design-epic-3.md`: (1) uma única classe `*ITTest` parametrizada por topologia (enum + `@MethodSource`) que roda a **bateria completa** de concorrência (10 threads) só em Standalone — migrando `RedisIdempotentRepositoryTryAcquireITTest` (Story 3.5) para dentro dela — e um **smoke de concorrência** mais barato (2–3 chamadas) em Sentinel e Cluster, sempre só através do contrato `tryAcquire(...) → Lease`; (2) estender `ScosJdempotentRedisConfigurationTest` com fail-fast de config inválida para Standalone e Sentinel (Cluster já feito na 3.18); (3) um teste de TPS informativo (sem gate) usando N chaves distintas para medir throughput real, não o caminho barato de `in-progress`.

**Emenda (renegociada pelo humano durante a review desta story, 2026-08-30):** (4) Além do teste de TPS de wiring manual (item 3), adicionar um segundo teste de TPS informativo que sobe um contexto Spring real (reaproveitando `JdempotentTestApplication`/`@SpringBootTest`, o mesmo app de teste usado por `PrimeNumbersJdempotentEnableITTest`) e mede o mesmo `tryAcquire` concorrente por um repository resolvido via injeção de dependência — sem substituir o teste manual, que continua existindo. (5) O bug de porta fixa do `docker-compose.yml` (`6379`/`26379`) que quebra `PrimeNumbersJdempotentEnableITTest`/`DisableITTest` — carve-off antes documentado em `deferred-work.md` e deliberadamente fora de escopo — passa a ser corrigido nesta story: substituir o `ComposeContainer` de porta fixa por containers Testcontainers de porta dinâmica (mesmo padrão de Sentinel já resolvido nesta story para `RedisIdempotentRepositoryTopologyITTest`), injetando host/porta via `@DynamicPropertySource` em vez dos valores fixos de `spring.data.redis.*` do `application.yml` de teste.

## Boundaries & Constraints

**Always:** Todo assert de concorrência/topologia passa só pelo contrato `tryAcquire(key, payloadHash, ttl) -> Lease` (AD-2 herdado) — nunca `contains`/`store`/`setResponse` isolados. Containers Testcontainers de infra real sobem 1x por topologia (`static`, ciclo de vida de classe), nunca recriados por método. Toda classe nova que suba Testcontainers/Docker usa o sufixo `*ITTest.java` (AD-6, já wireado pela Story 3.18) — nunca reintroduzir o padrão de porta fixa em classes novas. O teste de TPS usa N chaves distintas (nunca uma única chave compartilhada entre as operações concorrentes) para medir o caminho real de `SET NX PX`, não o caminho barato de `in-progress`.

**Ask First:** Qualquer necessidade de tocar código de produção além de `ScosJdempotentRedisConfiguration` (e só se estritamente necessário para o fail-fast, sem mudar comportamento) — esta story é só de testes/build, igual à 3.18. Se a infra de Sentinel (R-001 do test design) não estabilizar dentro do timebox razoável, voltar ao usuário com a proposta de reduzir o smoke de Sentinel a um teste de wiring sem concorrência, em vez de decidir sozinho ou fazer skip silencioso.

**Emenda (2026-08-30):** o bug de porta fixa do `docker-compose.yml`/`ComposeContainer` usado por `PrimeNumbersJdempotentEnableITTest`/`DisableITTest` deixou de estar "deliberadamente fora deste escopo" — por decisão explícita do humano, corrigi-lo (migrando para containers de porta dinâmica) passa a ser parte desta story. A restrição "nunca reintroduzir o padrão de porta fixa" acima continua valendo para qualquer classe nova.

**Never:** Testar "Redis alcançável mas fora do ar" como fail-fast (é fail-open, AD-2 herdado). Fazer `@ConditionalOnProperty(enabled=false)` do jdempotent falhar a subida da aplicação (confirmado explicitamente fora de escopo — módulo desligado continua fail-open, comportamento de produção não muda). Estender o padrão Failsafe/`*ITTest` ao módulo `audit` (deferred na spine). Colocar piso mínimo de TPS (`assertTrue(tps > limiar)`) — AD-9 é informativo por design, nunca um gate.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Concorrência real, 10 threads, mesma chave, topologia Standalone | `tryAcquire` chamado simultaneamente por 10 threads reais contra Redis Standalone real (Testcontainers) | Exatamente 1 `Lease.isAcquired()==true`; os outros 9 `in-progress` | N/A |
| Smoke de concorrência, 2-3 chamadas, mesma chave, topologia Sentinel | `tryAcquire` chamado concorrentemente contra Redis Sentinel real (master + sentinel via Testcontainers) | Exatamente 1 `acquired`, os demais `in-progress` — mesmo resultado do contrato, provando que o wiring da conexão via Sentinel funciona | Se a infra de Sentinel não estabilizar (R-001), teste falha com mensagem clara de infra (assert de smoke `SENTINEL get-master-addr-by-name`), não timeout confuso |
| Smoke de concorrência, 2-3 chamadas, mesma chave, topologia Cluster | `tryAcquire` chamado concorrentemente contra Redis Cluster real (Testcontainers) | Exatamente 1 `acquired`, os demais `in-progress` | N/A |
| Config Redis malformada, topologia Standalone | `spring.data.redis.port=not-a-number` (tipo inválido, sem depender de rede) | `context.getStartupFailure()` presente, causa raiz identificável | Contexto falha a subir, nunca silenciosamente |
| Config Redis malformada, topologia Sentinel | `spring.data.redis.sentinel.master=jdempotent`, `spring.data.redis.sentinel.nodes[0]=localhost:not-a-port` (porta não numérica, sem depender de rede) | `context.getStartupFailure()` presente, causa raiz identificável (`NumberFormatException` dentro de `sentinelConfiguration()`) | Contexto falha a subir, nunca silenciosamente |
| Teste de TPS, N operações `tryAcquire` concorrentes, N chaves distintas | Número fixo de operações contra Redis real (Testcontainers, reaproveita o container Standalone) | TPS medido é logado; nenhuma exceção lançada durante a execução | Nenhum piso mínimo de TPS assertado — só ausência de erro |
| `mvn test` no jdempotent após esta story | Nenhuma flag extra | Continua só unit tests, nenhum container Docker sobe (não regredir AD-6) | N/A |
| `mvn verify` no jdempotent após esta story | Nenhuma flag extra | Unit + integration (incluindo as 3 topologias + TPS) rodam | Falha de integration test falha o `verify` |
| Teste de TPS via contexto Spring real, N operações `tryAcquire` concorrentes | Repository resolvido por DI a partir de `JdempotentTestApplication`/contexto Spring | TPS medido é logado; nenhuma exceção lançada; mesmo contrato informativo do teste de TPS manual | Nenhum piso mínimo assertado |
| `PrimeNumbersJdempotentEnableITTest`/`DisableITTest` após a correção de porta fixa | `mvn verify` no módulo `jdempotent` | Sobe Redis/Sentinel via porta dinâmica (não mais `6379`/`26379` fixos) e os 2 testes passam | N/A |

</frozen-after-approval>

## Code Map

- `jdempotent/src/test/java/.../redis/repository/RedisIdempotentRepositoryTryAcquireITTest.java` -- Story 3.5, migrar/absorver os 2 métodos existentes para dentro da nova classe parametrizada (não recriar do zero); arquivo pode ser removido após a migração ou mantido como classe-base, decisão do Dev.
- `jdempotent/src/test/java/.../redis/repository/` -- nova classe parametrizada de topologia (nome sugerido: `RedisIdempotentRepositoryTopologyITTest.java`), enum de topologia (`Standalone`/`Sentinel`/`Cluster`) + `@MethodSource`, containers `static` por topologia.
- `jdempotent/src/test/java/.../redis/configuration/ScosJdempotentRedisConfigurationTest.java` -- adicionar 2 métodos novos de fail-fast (`contextoFalhaComConfigStandaloneMalformada`, `contextoFalhaComConfigSentinelMalformada`), mesmo padrão do `contextoFalhaComConfigClusterMalformada` já existente (Story 3.18).
- `jdempotent/src/main/java/.../redis/configuration/ScosJdempotentRedisConfiguration.java:96-115` -- `sentinelConfiguration()`, ponto onde o `NumberFormatException` do teste de fail-fast Sentinel precisa ocorrer (dentro do `forEach` que faz `Integer.parseInt(parts[1])`); **não modificar comportamento**, só usar como alvo do teste.
- `jdempotent/src/main/java/.../redis/repository/RedisIdempotentRepository.java:104` -- `tryAcquire`, único método exercitado por todos os testes novos de concorrência/TPS.
- `jdempotent/pom.xml` -- já tem `maven-failsafe-plugin`/`testcontainers-bom` wireados (Story 3.18); avaliar se a nova imagem de Cluster (ex.: `grokzen/redis-cluster`) precisa de dependência de teste adicional (Testcontainers genérico já cobre `GenericContainer`, provavelmente nenhuma dependência nova é necessária).
- `jdempotent/src/test/resources/docker-compose.yml` -- **não usar como referência de padrão** para os novos containers; os novos testes usam `GenericContainer`/porta dinâmica, como `RedisIdempotentRepositoryTryAcquireITTest` já fazia.
- `jdempotent/src/test/java/.../redis/test/PrimeNumbersJdempotentEnableITTest.java:54-60` -- substituir o `ComposeContainer` de porta fixa (`docker-compose.yml`) por containers Testcontainers de porta dinâmica (mesmo padrão Sentinel de `RedisIdempotentRepositoryTopologyITTest`), injetando `spring.data.redis.*` via `@DynamicPropertySource` em vez do `application.yml` fixo.
- `jdempotent/src/test/java/.../redis/test/PrimeNumbersJdempotentDisableITTest.java` -- mesma correção de porta dinâmica que o Enable.
- `jdempotent/src/test/resources/application.yml:12-22` -- os valores fixos `spring.data.redis.port`/`sentinel.nodes` deixam de ser a fonte de verdade para os testes de PrimeNumbers depois da migração para `@DynamicPropertySource` (decisão do Dev: manter como fallback ou remover as chaves agora mortas).
- `jdempotent/src/test/java/.../redis/test/app/JdempotentTestApplication.java` -- app Spring Boot de teste já existente; reaproveitar (não modificar) como base do novo teste de TPS via contexto Spring.
- `jdempotent/src/test/java/.../redis/repository/RedisIdempotentRepositoryTopologyITTest.java` -- adicionar o segundo teste de TPS (via contexto Spring), ao lado do `tpsInformativoComChavesDistintas` já existente (wiring manual).
- `jdempotent/src/test/java/.../redis/repository/RedisIdempotentRepositoryTpsSweepITTest.java` -- (iteração 8) classe nova, sweep de TPS por nível de concorrência, gated pelo profile Maven `tps-sweep`.
- `jdempotent/pom.xml` -- (iteração 8) property `tps.sweep.exclude` + profile `tps-sweep` (zera a property) para isolar `RedisIdempotentRepositoryTpsSweepITTest` do `mvn verify` normal.

## Tasks & Acceptance

**Execution:**

- [x] Criar a classe parametrizada de topologia (`RedisIdempotentRepositoryTopologyITTest` ou nome equivalente), com enum de topologia e `@MethodSource`; migrar os 2 métodos de `RedisIdempotentRepositoryTryAcquireITTest` (Story 3.5) para rodar como a bateria completa (10 threads) do caso Standalone.
- [x] Montar a infra de Sentinel via Testcontainers: pré-alocar portas de host (master + sentinel) antes de criar os containers, vincular explicitamente essas portas, configurar `REDIS_SENTINEL_ANNOUNCE_IP`/`REDIS_SENTINEL_ANNOUNCE_PORT` (bitnami) apontando para o host reachable pela JVM de teste; adicionar assert de smoke da própria infra (`SENTINEL get-master-addr-by-name` retorna o host esperado) antes da lógica de concorrência (mitigação de R-001).
- [x] Montar a infra de Cluster via Testcontainers (avaliar imagem autocontida tipo `grokzen/redis-cluster` para evitar bootstrap manual multi-nó — mitigação de R-002).
- [x] Adicionar o smoke de concorrência (2-3 chamadas) para Sentinel e Cluster na classe parametrizada, mesmo contrato `tryAcquire → Lease` do caso Standalone.
- [x] `ScosJdempotentRedisConfigurationTest` -- adicionar `contextoFalhaComConfigStandaloneMalformada()` (`spring.data.redis.port=not-a-number`) e `contextoFalhaComConfigSentinelMalformada()` (`spring.data.redis.sentinel.nodes[0]` com porta não numérica), mesmo padrão de assert do teste de Cluster já existente.
- [x] Adicionar o teste de TPS informativo (reaproveitando o container Standalone da classe parametrizada): número fixo de operações `tryAcquire` concorrentes, **N chaves distintas** (UUID por operação ou pool pequeno reciclado — mitigação de R-004), log do TPS medido, assert só de ausência de erro/exceção.
- [x] Verificar manualmente (rodando o teste isoladamente) que `spring.data.redis.port=not-a-number` de fato falha o binding do Spring Boot antes do bean da `ScosJdempotentRedisConfiguration` rodar (R-005) — se não falhar como esperado, ajustar o cenário de config inválida de Standalone para outro campo que realmente dispare a falha.
- [x] (Emenda) Adicionar um segundo teste de TPS informativo que sobe um contexto Spring real (`JdempotentTestApplication`) e mede o mesmo `tryAcquire` concorrente via repository resolvido por DI, mantendo o teste de TPS de wiring manual já existente.
- [x] (Emenda) Corrigir `PrimeNumbersJdempotentEnableITTest`/`DisableITTest`: substituir o `ComposeContainer` de porta fixa por containers de porta dinâmica (mesmo padrão Sentinel já resolvido nesta story), injetando a config via `@DynamicPropertySource`.
- [x] (Emenda) Confirmar que `mvn -pl jdempotent verify` passa 100% no módulo, sem o vermelho pré-existente do bug de porta fixa.

**Acceptance Criteria:**

- Given concorrência real (10 threads) contra Redis Standalone, when `tryAcquire` é chamado simultaneamente com a mesma chave, then exatamente 1 chamada acquire, as outras 9 recebem `in-progress` (equivalente ao já provado pela Story 3.5, agora dentro da classe parametrizada).
- Given concorrência real (2-3 chamadas) contra Redis Sentinel ou Cluster, when `tryAcquire` é chamado simultaneamente com a mesma chave, then exatamente 1 chamada acquire, as outras recebem `in-progress` — provando que o wiring de conexão de cada topologia entrega o mesmo contrato do Standalone.
- Given uma configuração de Redis malformada (Standalone ou Sentinel, tipo inválido, sem depender de rede), when o contexto Spring sobe, then a inicialização falha com causa raiz identificável (fail-fast, nunca silenciosamente) — mesmo padrão já provado para Cluster na Story 3.18.
- Given um número fixo de operações `tryAcquire` concorrentes com chaves distintas contra Redis real, when o teste de TPS roda, then nenhuma exceção é lançada e o TPS medido é logado — nunca um piso mínimo assertado.
- Given `mvn test` no módulo `jdempotent`, when executado, then nenhum container Docker é iniciado e só testes unitários rodam (não regredir AD-6).
- Given `mvn verify` no módulo `jdempotent`, when executado, then a classe parametrizada de topologia (3 topologias) e o teste de TPS rodam junto com os demais `*ITTest` existentes.
- Given o teste de TPS via contexto Spring real, when executado concorrentemente, then nenhuma exceção é lançada e o TPS é logado — mesmo contrato informativo do teste manual, nunca um piso mínimo.
- Given `mvn -pl jdempotent verify` após a correção do bug de porta fixa, when executado, then `PrimeNumbersJdempotentEnableITTest`/`DisableITTest` passam via porta dinâmica, sem depender das portas fixas `6379`/`26379`.

## Spec Change Log

### 2026-08-30 — Emenda de escopo por decisão do humano (durante Step 4/Review)

- **Gatilho:** pedido explícito do usuário durante a review desta story, fora do fluxo automático de review findings (confirmado via pergunta direta ao humano): (1) adicionar um teste de TPS que também suba um contexto Spring real; (2) trazer para dentro desta story a correção do bug de porta fixa do `docker-compose.yml` que quebra `PrimeNumbersJdempotentEnableITTest`/`DisableITTest` — antes um carve-off documentado em `deferred-work.md`.
- **O que foi emendado:** `Intent`/`Approach` (itens 4 e 5), `Boundaries & Constraints` (a proibição de porta fixa passou a valer só para classes novas; a correção do `docker-compose.yml` existente deixou de estar fora de escopo), matriz I/O (2 linhas novas), `Code Map`, `Tasks & Acceptance` (3 itens novos), `Verification`.
- **Estado ruim evitado:** manter o teste de TPS cobrindo só o wiring manual (sem provar o caminho de autoconfiguração/DI real) e deixar o `mvn verify` do módulo intencionalmente vermelho por um bug de infra que já tinha correção conhecida (mesmo padrão de porta dinâmica já resolvido nesta story para Sentinel).
- **KEEP (preservar, não reverter):** toda a implementação já feita e testada antes desta emenda — `RedisIdempotentRepositoryTopologyITTest` (concorrência Standalone/Sentinel/Cluster), os 2 testes de fail-fast (`ScosJdempotentRedisConfigurationTest`), e o teste de TPS de wiring manual (`tpsInformativoComChavesDistintas`) — continua exatamente como está; a emenda só adiciona por cima.

## Design Notes

Este é o carve-off registrado em `deferred-work.md` pela Story 3.18 (gate de token count do spec original, que somava as 4 frentes: split unit/IT, topologia, fail-fast, TPS). A spine `architecture-SawCunhaOS-Foundation-2026-08-29` já adota AD-7/AD-9 e teve AD-8 estendido nesta sessão (amendment, antes da autoria desta story) para cobrir as 3 topologias em vez de só Cluster.

O test design completo (risco, coverage plan, estimativas) está em `_bmad-output/test-artifacts/test-design-epic-3.md` (Murat/Test Architect) — em especial: (1) a recomendação de rodar a bateria COMPLETA de concorrência só em Standalone e um smoke mais barato em Sentinel/Cluster (a atomicidade vem do primitivo `SET NX PX` do Redis, idêntico nas 3 topologias — o que realmente varia é o wiring de conexão, já coberto sem infra real pela Story 3.1); (2) o risco R-001 (infra Sentinel frágil, score 6) e sua mitigação (pré-alocação de porta + announce-ip/port + assert de smoke); (3) o risco R-004 (TPS medido no caminho errado se usar uma única chave, score 6) e sua mitigação (N chaves distintas).

## Verification

**Commands:**

- `mvn -pl jdempotent -am test` -- expected: só unit tests rodam, sem nenhum log de Testcontainers/Docker (não regredir AD-6)
- `mvn -pl jdempotent -am -Dtest=ScosJdempotentRedisConfigurationTest test` -- expected: 6 testes (4 já existentes da Story 3.1/3.18 + 2 novos de fail-fast Standalone/Sentinel) passam
- `mvn -pl jdempotent -Dit.test=RedisIdempotentRepositoryTopologyITTest verify` (isolado) -- expected: `BUILD SUCCESS`, cobrindo as 3 topologias + smoke de concorrência + os 2 testes de TPS (manual e via Spring)
- `mvn -pl jdempotent -Dit.test=PrimeNumbersJdempotentEnableITTest,PrimeNumbersJdempotentDisableITTest verify` (isolado, pós-correção) -- expected: `BUILD SUCCESS` via porta dinâmica
- `mvn -pl jdempotent verify` -- expected (pós-emenda): `BUILD SUCCESS` completo no módulo, sem o vermelho pré-existente do bug de porta fixa
- `mvn -pl jdempotent verify` (sem profile) -- expected (iteração 8): `RedisIdempotentRepositoryTpsSweepITTest` NÃO roda (excluído por padrão)
- `mvn -Ptps-sweep -pl jdempotent verify` -- expected (iteração 8): `RedisIdempotentRepositoryTpsSweepITTest` roda junto com os demais `*ITTest`, `BUILD SUCCESS`

## Dev Agent Record

### Debug Log References

**Iteration 1 (pre-emenda):**

- `RedisIdempotentRepositoryTopologyITTest` isolated run: 3 consecutive local passes (5/5 tests each), satisfying R-001's verification bar.
- `mvn -pl jdempotent test`: 52 unit tests, no Testcontainers/Docker log lines (AD-6 not regressed).
- `mvn -pl jdempotent verify`: new topology class passed; `PrimeNumbersJdempotentEnableITTest`/`DisableITTest` failed with the (then still in-scope-as-deferred) fixed-port collision — matched the story's documented expectation at that point.

**Iteration 3 (review round 3 — blind-hunter + edge-case-hunter, 5 point patches; verification-gap found nothing):**

- `mvn -pl jdempotent test`: 52 unit tests, still no Docker.
- The 5 changed/touched IT classes isolated in one run (`-Dit.test=RedisIdempotentRepositoryTopologyITTest,RedisIdempotentRepositoryTopologySmokeITTest,RedisIdempotentRepositoryTpsSpringContextITTest,PrimeNumbersJdempotentEnableITTest,PrimeNumbersJdempotentDisableITTest`): pass, 9/9.
- `mvn -pl jdempotent verify` (full module): **`BUILD SUCCESS`**, 52 unit + 9 integration, run once (prior round already validated reproducibility 3x for this same infra) — no container leaks (`docker ps -a` clean after a >15s wait for Ryuk).

**Iteration 2 (pós-emenda, review patches + scope additions):**

- `mvn -pl jdempotent test`: 52 unit tests, still no Docker (AD-6 intact after the split into 3 IT classes).
- `RedisIdempotentRepositoryTopologyITTest` (Standalone-only, 3 tests) isolated: pass.
- `RedisIdempotentRepositoryTopologySmokeITTest` (Sentinel+Cluster, 2 tests) isolated: pass, including the new `smokeCheckClusterInfra`.
- `RedisIdempotentRepositoryTpsSpringContextITTest` (1 test) isolated: pass, DI-resolved repository, TPS logged (~1785-2700 ops/s across runs, informative only).
- `PrimeNumbersJdempotentEnableITTest`,`PrimeNumbersJdempotentDisableITTest` isolated: pass after 2 fixes (see Completion Notes — the stale idempotency-key hash was the real blocker, not the port dynamism itself).
- `mvn -pl jdempotent verify` (full module): **`BUILD SUCCESS`**, 52 unit + 9 integration tests, run **3 consecutive times** — no failures, no container leaks (`docker ps -a` clean after each run, confirmed via a >15s wait for Ryuk's own self-termination).

### Completion Notes List

**Iteration 1 items** — see git history / the class Javadoc for the Sentinel host-gateway wiring, the Cluster `protected-mode` template override, and the `Wait.forLogMessage(".*All 16384 slots covered.*")` fix (all still in place, unchanged in substance, just relocated by the item-9 split below).

**Iteration 2 (review patches + emenda) — what changed:**

- **Split into 3 files** (patch 9): `RedisIdempotentRepositoryTopologyITTest` (Standalone: full battery, TTL test, manual-wiring TPS test — 3 tests), `RedisIdempotentRepositoryTopologySmokeITTest` (Sentinel+Cluster smoke — 2 tests), `RedisIdempotentRepositoryTpsSpringContextITTest` (new, DI-resolved TPS — 1 test). A shared `SentinelContainerFixture` (new, `redis.repository` package, public) factors out the master+sentinel container-pair recipe, now reused by the Smoke class AND by both `PrimeNumbersJdempotentEnableITTest`/`DisableITTest` (rule-of-three: 3 consumers).
- **`smokeCheckClusterInfra`** (patch 1) added alongside the existing `smokeCheckSentinelInfra`: a plain `PING` through the cluster-aware connection before the concurrency asserts, same "fail with a clear infra message, not a confusing count mismatch" reasoning.
- **`smokeCheckSentinelInfra`** (patches 2/3/6): now try-with-resources for both the `RedisSentinelConnection` (its `close()` is checked-`IOException`, caught and rethrown as `UncheckedIOException` so the method no longer declares `throws IOException`) and the `RedisConnection` (unchecked `close()`, no extra handling needed); the reported master is now filtered by `SENTINEL.masterName` instead of blindly taking `masters().iterator().next()`.
- **Timeouts + pool safety** (patches 4/5): every `future.get()` in the concurrency loops (Standalone battery, Sentinel/Cluster smoke, both TPS tests) now uses `future.get(30, TimeUnit.SECONDS)`; every `ExecutorService` is now shut down in a `finally` block, so a thrown exception mid-run no longer leaks pool threads.
- **`repositoryUsing(...)`** (patch 7): dropped the unnecessary `(RedisTemplate)` cast — the constructor already accepts the raw `RedisTemplate` type.
- **Sentinel wait timeout** (patch 8): `SentinelContainerFixture`'s sentinel container now has an explicit `.withStartupTimeout(Duration.ofSeconds(60))`, matching the Cluster container's explicit timeout.
- **Second TPS test, DI-resolved** (emenda item 4): `RedisIdempotentRepositoryTpsSpringContextITTest` boots `JdempotentTestApplication` (`@SpringBootTest(webEnvironment = NONE)`), resolves the repository via `@Autowired IdempotentAspect` → `getIdempotentRepository()` (an `IdempotentRepository`, not cast to the concrete class — the interface already declares `tryAcquire`), same 500-op/N-distinct-key/no-floor measurement as the manual test. Its own Standalone container is started manually inside `@DynamicPropertySource` (not `@Container`/`@Testcontainers`) — Spring needs the port before the container-lifecycle extension would otherwise start it.
- **PrimeNumbers fixed-port fix** (emenda item 5): both classes dropped `ComposeContainer`/`docker-compose.yml` for a `SentinelContainerFixture` pair started manually inside `@DynamicPropertySource` (same ordering reason as above) and torn down in `@AfterAll`. `application.yml`'s now-dead `spring.data.redis.*` keys (fixed port/password/sentinel block) were removed — each `@SpringBootTest` class supplies its own connection info dynamically. `docker-compose.yml` itself was deleted (nothing references it anymore).
- **Real bug found and fixed while verifying the PrimeNumbers fix**: `PrimeNumbersJdempotentEnableITTest`'s hardcoded `KEY_DEFAULT_PRIME_NUMBER` used a stale, shorter (MD5-length) hash; `DefaultKeyGenerator` actually produces a SHA-256 hash today. This mismatch pre-dates this story — it was invisible before because the fixed-port infra bug always failed the test before reaching that assertion. Confirmed the real hash is deterministic across 3 separate runs (`ea2cfd6b48da4f849a45691d17d1bc2a40cd95e359017f43c590e3ff1ca4dffb`) via a temporary `docker exec redis-cli KEYS *` probe (removed afterward) and updated the constant. This is a test-only data fix, no production code touched, within the story's "Ask First" boundary (test/build-only scope).
- No production code touched in either iteration.
- Not fully exercised: the GitHub Actions CI run itself (`.github/workflows/build.yml`'s `mvn -B -pl jdempotent -am verify` step, Story 3.18) — only reproduced locally, 3 consecutive full `mvn verify` passes with Docker + network confirmed available in this environment.

**Iteration 3 (review round 3, 5 point patches — verification-gap found no gaps):**

- **Dead import** (patch 1): `RedisIdempotentRepositoryTopologySmokeITTest` no longer imports `com.github.dockerjava.api.model.PortBinding` — the Cluster port binding only ever used `Ports.Binding.bindPort(...)`/`bindings.bind(...)`, never the `PortBinding` constructor directly.
- **`pool.shutdownNow()` on the non-happy path** (patch 2): all 4 concurrency/TPS methods (Standalone battery, manual TPS, Sentinel/Cluster smoke, Spring-context TPS) now track a `completedNormally` boolean set only after the asserts pass; the `finally` calls `pool.shutdown()` when true, or `pool.shutdownNow()` + `futures.forEach(f -> f.cancel(true))` when false. A plain `catch (Exception e)` wouldn't have covered this since JUnit's `assertDoesNotThrow`/`assertEquals` failures throw `AssertionError` (an `Error`, not an `Exception`) — the boolean-flag-in-`finally` shape covers both checked exceptions (`TimeoutException` etc.) and assertion failures uniformly.
- **Port-collision guard** (patch 3): `SentinelContainerFixture.build()` now retries `findFreePort()` until the sentinel port differs from the master port (each call opens+closes its own socket, no reservation between the two calls, so a same-port collision was theoretically possible).
- **`afterPropertiesSet()` ordering** (patch 4): in the Sentinel/Cluster smoke test, `connectionFactory.afterPropertiesSet()` now runs inside the `try` (right before first use) instead of before it, so a throw from it still routes through the `finally` that calls `connectionFactory.destroy()` — no more leaking a partially-constructed factory.
- **Orphaned master container** (patch 5): in both `PrimeNumbersJdempotentEnableITTest`/`DisableITTest`'s `@DynamicPropertySource`, `SENTINEL.sentinel.start()` is now wrapped in a try/catch that stops `SENTINEL.master` before rethrowing, so a sentinel-container startup failure no longer leaves the master running unattended.
- No production code touched.

**Iteration 4 (2026-08-30, pedido direto do humano fora do fluxo de review):**

- Os 2 testes de TPS (`tpsInformativoComChavesDistintas` e `tpsInformativoViaContextoSpring`) trocaram `Executors.newFixedThreadPool(20)` por `Executors.newVirtualThreadPerTaskExecutor()` — Java 25 (`java.version=25` no pom raiz), virtual threads estáveis desde o Java 21. Sem mudança de escopo além da troca do executor: mesmos 500 ops, mesmas chaves distintas, mesmo timeout de 30s por `future.get`, mesmo padrão `shutdown()`/`shutdownNow()`+cancel no `finally`.
- Verificado isolado (`RedisIdempotentRepositoryTopologyITTest`: 3/3; `RedisIdempotentRepositoryTpsSpringContextITTest`: 1/1) e via `mvn -pl jdempotent verify` completo: `BUILD SUCCESS`, 52 unit + 9 integration.
- TPS logado pós-mudança (informativo, não comparável a benchmark): manual 2733,6 ops/s (500 ops em 0,183s), via Spring 1706,4 ops/s (500 ops em 0,293s) — mesma variação run-a-run já observada antes da troca, não atribuível a virtual threads especificamente.

**Iteration 5 (2026-08-30, pedido direto do humano):** `operationCount` dos 2 testes de TPS subiu de `500` para `5000` — racional do humano: a infra mínima de produção prevista é de ~100 conexões com o banco, então 5000 ops é um piso mais realista de carga para o teste informativo do que 500. Sem outra mudança (mesmo `TASK_TIMEOUT` de 30s por `future.get`, mesmas chaves distintas). Verificado isolado (3/3 e 1/1) e via `mvn -pl jdempotent verify` completo: `BUILD SUCCESS`, 52 unit + 9 integration. TPS logado: manual 5146,4 ops/s (5000 ops em 0,972s), via Spring 4801,0 ops/s (5000 ops em 1,041s) — com amostra maior os dois ficaram bem mais próximos entre si.

**Iteration 6 (2026-08-30, pedido direto do humano — sweep por nível de concorrência):** Investigação prévia mostrou que `ScosJdempotentRedisConfiguration.lettuceConnectionFactory()` (`jdempotent/src/main/java/.../redis/configuration/ScosJdempotentRedisConfiguration.java:60-73`) usa Lettuce sem pooling — uma única conexão Netty multiplexada, tanto em produção quanto nos testes desta story; "100 conexões" não mapeia para um parâmetro configurável hoje. Esclarecido com o humano: o eixo do sweep pedido (10/30/50/100/150/300) é nível de concorrência (chamadores simultâneos), não tamanho de pool; 10 mil é por nível (não total); vira um 3º método de teste, ao lado dos 2 já existentes, sem substituí-los.

- Novo `tpsInformativoPorNivelDeConcorrencia()` em `RedisIdempotentRepositoryTopologyITTest` (reaproveita o mesmo container/`standaloneRepository` da classe): para cada nível em `{10, 30, 50, 100, 150, 300}`, roda `10_000` operações `tryAcquire` com chaves distintas (R-004) usando `Executors.newFixedThreadPool(concurrency)` — pool fixo por nível, não virtual threads (aqui a concorrência é a variável controlada, ao contrário dos 2 testes de TPS acima onde ela é livre). Mesmo padrão de timeout (`future.get(30, SECONDS)`) e `shutdown()`/`shutdownNow()`+cancel no `finally`. Continua informativo (AD-9) — nenhum piso mínimo assertado em nenhum nível.
- Verificado isolado (1/1, 38,3s de wall-clock a frio) e via `mvn -pl jdempotent verify` completo: `BUILD SUCCESS`, 52 unit + 10 integration (a classe passou a ter 4 testes).
- Resultado do sweep (informativo, não é benchmark controlado — 1 execução): `concurrency=10 → 4301,7 ops/s`, `30 → 16946,3 ops/s`, `50 → 19427,4 ops/s`, `100 → 19080,7 ops/s`, `150 → 18767,2 ops/s`, `300 → 18724,6 ops/s`. Achado interessante: o throughput sobe até `~50` de concorrência e satura em torno de `~19k ops/s` dali em diante — consistente com uma única conexão Lettuce multiplexada sendo o gargalo, não o número de chamadores.

**Iteration 7 (2026-08-30, pedido direto do humano):** `OPERATIONS_PER_LEVEL` do sweep subiu de `10_000` para `100_000` (600 mil `tryAcquire` no total, 6 níveis). Verificado isolado (1/1, 67s de wall-clock a frio) e via `mvn -pl jdempotent verify` completo: `BUILD SUCCESS`, 52 unit + 10 integration (a classe do sweep sozinha levou 39,35s dentro do `verify` completo, ante 8,5s com 10 mil/nível). Resultado: `concurrency=10 → 11740,2 ops/s`, `30 → 19241,1 ops/s`, `50 → 19398,3 ops/s`, `100 → 20645,0 ops/s`, `150 → 22005,5 ops/s`, `300 → 20968,2 ops/s` — mesmo padrão de saturação a partir de `~30`, agora com amostra 10x maior.

**Iteration 8 (2026-08-30, pedido direto do humano — isolar o sweep atrás de um profile Maven):** o sweep (600 mil ops, ~35-40s dentro do `verify`) foi extraído de `RedisIdempotentRepositoryTopologyITTest` para sua própria classe, `RedisIdempotentRepositoryTpsSweepITTest` (container Standalone próprio, reaproveita `RedisIdempotentRepositoryTopologyITTest.repositoryUsing(...)` package-private, mesmo padrão já usado por `RedisIdempotentRepositoryTopologySmokeITTest`). `jdempotent/pom.xml` ganhou a property `tps.sweep.exclude` (default `**/*TpsSweepITTest.java`, excluída do Failsafe) e o profile `tps-sweep` (zera a property, reincluindo a classe). `RedisIdempotentRepositoryTopologyITTest` volta a ter só 3 testes (bateria, TTL, TPS manual).

- Verificado sem profile: `RedisIdempotentRepositoryTpsSweepITTest` não roda, `mvn -pl jdempotent verify` volta a 9 integration tests, `BUILD SUCCESS`.
- Verificado com `mvn -Ptps-sweep -pl jdempotent verify`: `RedisIdempotentRepositoryTpsSweepITTest` roda (10 integration tests), `BUILD SUCCESS`. Resultado: `concurrency=10 → 12457,8 ops/s`, `30 → 19772,9 ops/s`, `50 → 19839,3 ops/s`, `100 → 21936,2 ops/s`, `150 → 22526,6 ops/s`, `300 → 21279,9 ops/s`.

**Iteration 9 (2026-08-30, pedido direto do humano — repetição estatística):** cada nível do sweep passou a rodar 1 execução de warm-up descartada (mitiga o viés de JIT/conexão fria já apontado na avaliação crítica dos resultados de execução única) + `5` medições reais, reportando média e desvio-padrão em vez de um valor único. `WARMUP_REPETITIONS=1`, `MEASURED_REPETITIONS=5` — 6 passagens × 6 níveis × 100 mil ops = 3,6 milhões de `tryAcquire` no total.

- Verificado isolado com `-Ptps-sweep`: 1/1, 196,6s (~3min17s de medição pura, ~3min40s de wall-clock incluindo boot da JVM/container). Verificado sem profile via `mvn -pl jdempotent verify`: `BUILD SUCCESS`, 52 unit + 9 integration (sweep continua excluído por padrão).
- Resultado (média ± desvio-padrão, n=5 por nível): `concurrency=10 → 14348,4 ± 865,2 ops/s`, `30 → 20140,0 ± 710,1`, `50 → 20647,4 ± 1106,1`, `100 → 21761,3 ± 539,8`, `150 → 22041,8 ± 346,9`, `300 → 22031,2 ± 1905,4`. Desvio-padrão baixo (exceto em 10 e 300) confirma que o padrão de saturação a partir de `~30` é real, não ruído — mas 300 ainda mostra dispersão notável (uma medição de 18635,8 entre quatro de ~22-23k), sinal de que mesmo com repetição a cauda de latência em alta concorrência não é totalmente estável.

## Suggested Review Order

**Infra compartilhada**

- Ponto de entrada: builder do par master+sentinel (host-gateway, announce-ip/port), reusado por 3 classes de teste.
  [`SentinelContainerFixture.java:53`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/SentinelContainerFixture.java#L53)

**Concorrência real por topologia (AD-7)**

- Bateria completa de concorrência (10 threads), migrada da Story 3.5, agora isolada da infra de Sentinel/Cluster.
  [`RedisIdempotentRepositoryTopologyITTest.java:106`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTopologyITTest.java#L106)

- Smoke parametrizado (Sentinel/Cluster); pre-check de infra roda antes do assert de concorrência para evitar falha confusa.
  [`RedisIdempotentRepositoryTopologySmokeITTest.java:219`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTopologySmokeITTest.java#L219)

- `smokeCheckSentinelInfra`/`smokeCheckClusterInfra` — a mesma mitigação de R-001 agora simétrica nas 2 topologias.
  [`RedisIdempotentRepositoryTopologySmokeITTest.java:289`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTopologySmokeITTest.java#L289)

- Bootstrap do container Cluster (`grokzen/redis-cluster`, 6 nós, porta descoberta em runtime) — mitigação de R-002.
  [`RedisIdempotentRepositoryTopologySmokeITTest.java:161`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTopologySmokeITTest.java#L161)

**TPS informativo (AD-9)**

- Teste de TPS via wiring manual (chaves distintas, sem piso mínimo) — continua existindo após a emenda.
  [`RedisIdempotentRepositoryTopologyITTest.java:179`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTopologyITTest.java#L179)

- Teste de TPS via contexto Spring real (repository resolvido por DI) — item novo da emenda, ao lado do manual.
  [`RedisIdempotentRepositoryTpsSpringContextITTest.java:88`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTpsSpringContextITTest.java#L88)

**Fail-fast de config inválida (AD-8 estendido)**

- Fail-fast Standalone (`port=not-a-number`) e Sentinel (`nodes[0]` porta inválida) — mesmo padrão do Cluster (Story 3.18).
  [`ScosJdempotentRedisConfigurationTest.java:113`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfigurationTest.java#L113)

**Correção do bug de porta fixa (emenda, item 5)**

- `ComposeContainer` de porta fixa trocado por `SentinelContainerFixture` via `@DynamicPropertySource`; hash de idempotência corrigido (bug real pré-existente exposto pela correção).
  [`PrimeNumbersJdempotentEnableITTest.java:64`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/test/PrimeNumbersJdempotentEnableITTest.java#L64)

- Mesma correção de porta dinâmica no cenário com o módulo desligado.
  [`PrimeNumbersJdempotentDisableITTest.java:56`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/test/PrimeNumbersJdempotentDisableITTest.java#L56)

- Chaves `spring.data.redis.*` fixas removidas — cada `@SpringBootTest` agora se auto-configura via `@DynamicPropertySource`.
  [`application.yml:14`](../../jdempotent/src/test/resources/application.yml#L14)

**Periféricos**

- `docker-compose.yml` (porta fixa `6379`/`26379`) removido — nada mais o referencia.
- `RedisIdempotentRepositoryTryAcquireITTest.java` (Story 3.5) removido — os 2 métodos migraram, sem perda de asserção, para dentro de `RedisIdempotentRepositoryTopologyITTest`.
