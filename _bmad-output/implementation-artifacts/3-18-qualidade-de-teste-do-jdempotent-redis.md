---
title: 'Separar unit/integration test do jdempotent e adicionar fail-fast em config Redis inválida'
type: 'chore'
created: '2026-08-29'
status: 'done'
baseline_commit: '2df6d446b95929881e5cc3e9eff65d5258e44046'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-29/ARCHITECTURE-SPINE.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** O módulo `jdempotent` mistura testes unitários e de integração sob `mvn test` (Surefire sobe Docker/Testcontainers durante unit test, causando os erros de porta já documentados nas Stories 3.1/3.4/3.5), e não tem cobertura de fail-fast quando a configuração de Redis está malformada.

**Approach:** Introduzir `maven-failsafe-plugin` com sufixo `*ITTest.java` explícito (AD-6), ajustar o CI para rodar a fase `verify` do `jdempotent`, renomear os dois testes de integração pré-existentes sem esse sufixo, e adicionar um teste de fail-fast para configuração de Redis inválida (AD-8). Fundação para a story seguinte (topologia parametrizada + throughput, carve-off já registrado em `deferred-work.md`).

## Boundaries & Constraints

**Always:** Sufixo único `*ITTest.java` para toda classe que sobe Testcontainers/Docker; `maven-surefire-plugin`/`maven-failsafe-plugin` com `<excludes>`/`<includes>` explícitos (os defaults de nenhum dos dois reconhecem `*ITTest.java` corretamente); o novo step de CI é escopado ao `jdempotent` (`-pl jdempotent`), nunca troca a fase do step "Run tests" global.

**Ask First:** Qualquer necessidade de tocar código de produção do `jdempotent` além de `ScosJdempotentRedisConfiguration` (só para o teste de fail-fast, sem mudar comportamento) — esta story é só de testes/build.

**Never:** Estender o padrão Failsafe/`*ITTest` para o módulo `audit` (deferred na spine); testar "Redis alcançável mas fora do ar" como cenário de fail-fast (isso é fail-open, AD-2 herdado); criar a classe parametrizada de topologia ou o teste de TPS (carve-off, story seguinte).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Config Redis malformada | `spring.data.redis.cluster.max-redirects=not-a-number` (tipo inválido, sem depender de rede) | `context.getStartupFailure()` presente, causa raiz identificável (erro de binding) | Contexto falha a subir, nunca silenciosamente |
| `mvn test` no jdempotent | Nenhuma flag extra | Só unit tests rodam; nenhum container Docker sobe | N/A |
| `mvn verify` no jdempotent | Nenhuma flag extra | Unit + integration (`*ITTest`, incluindo os 2 renomeados e o já existente da Story 3.5) rodam | Falha de integration test falha o `verify` |

</frozen-after-approval>

## Code Map

- `jdempotent/pom.xml:237-240` -- `maven-surefire-plugin` sem `<configuration>` hoje
- `.github/workflows/build.yml:44-45` -- step "Run tests" (`mvn -B test`, reactor inteiro), referência para o novo step
- `jdempotent/src/test/.../redis/test/PrimeNumbersJdempotentEnable/DisableTest.java` -- sem sufixo IT hoje, sobem `docker-compose.yml`
- `jdempotent/src/test/.../redis/repository/RedisIdempotentRepositoryTryAcquireITTest.java` -- já com sufixo correto (Story 3.5), não editar
- `jdempotent/src/test/.../core/datasource/InMemoryIdempotentRepositoryTryAcquireTest.java` -- sem Testcontainers, não leva sufixo `ITTest`, não tocar
- `jdempotent/src/main/.../redis/configuration/ScosJdempotentRedisConfiguration.java:75` -- `setValidateConnection(false)`, conexão lazy (por isso fail-fast cobre só config inválida)
- `jdempotent/src/test/.../redis/configuration/ScosJdempotentRedisConfigurationTest.java` -- `ApplicationContextRunner` da Story 3.1, recebe o novo teste

## Tasks & Acceptance

**Execution:**
- [x] `jdempotent/pom.xml` -- adicionar `<configuration><excludes>**/*ITTest.java</excludes></configuration>` ao `maven-surefire-plugin` existente e um novo `<plugin>` `maven-failsafe-plugin:3.5.4` com `<includes>**/*ITTest.java</includes>` e `<executions>` padrão (`integration-test`, `verify`)
- [x] `.github/workflows/build.yml` -- adicionar step novo `Run jdempotent integration tests` (`mvn -B -pl jdempotent -am verify`) logo após o step "Run tests" existente (linha 45)
- [x] Renomear `PrimeNumbersJdempotentEnableTest.java`/`PrimeNumbersJdempotentDisableTest.java` para `PrimeNumbersJdempotentEnableITTest.java`/`PrimeNumbersJdempotentDisableITTest.java` (arquivo + nome da classe, sem mudar lógica)
- [x] `ScosJdempotentRedisConfigurationTest.java` -- adicionar teste `contextoFalhaComConfigClusterMalformada()`: `spring.data.redis.cluster.max-redirects=not-a-number`, asserta `context.getStartupFailure()` presente e causa raiz identificável

**Acceptance Criteria:**
- Given uma configuração de Redis malformada (tipo inválido, sem depender de rede), when o contexto Spring sobe, then a inicialização falha com causa raiz identificável (fail-fast), nunca silenciosamente.
- Given uma configuração de Redis válida (as 3 topologias), when o contexto Spring sobe, then não há regressão em relação à cobertura já existente da Story 3.1.
- Given `mvn test` no módulo `jdempotent`, when executado, then nenhum container Docker é iniciado e só testes unitários rodam.
- Given `mvn verify` no módulo `jdempotent` (ou o novo step de CI), when executado, then o wiring do Failsafe/sufixo `*ITTest` (AD-6) está correto — comprovado isolando `RedisIdempotentRepositoryTryAcquireITTest` (Story 3.5, porta dinâmica) sob `verify`. **Ajustado por decisão humana em 2026-08-29**: `PrimeNumbersJdempotentEnableITTest`/`DisableITTest` continuam falhando sob `verify` por um bug pré-existente de porta fixa no `docker-compose.yml` (confirmado idêntico no `baseline_commit`, não causado por esta story) — corrigir a fixture está fora do escopo autorizado ("renomear sem mudar lógica"); registrado em `deferred-work.md` para uma story de hardening do fixture Docker Compose.

## Spec Change Log

## Design Notes

Topologia parametrizada (AD-7) e TPS (AD-9) são carve-off (gate de token count) para a story seguinte, registrada em `deferred-work.md`; depende do Failsafe desta story já estar wireado.

## Verification

**Commands:**
- `mvn -pl jdempotent -am test` -- expected: só unit tests rodam, sem nenhum log de Testcontainers/Docker
- `mvn -pl jdempotent -am verify` -- expected: unit + todos os `*ITTest` (incluindo os 2 renomeados) passam
- `mvn -pl jdempotent -am -Dtest=ScosJdempotentRedisConfigurationTest test` -- expected: 4 testes (3 da Story 3.1 + o novo de fail-fast) passam

## Dev Agent Record

### Debug Log References

- `mvn -pl jdempotent test` (sem `-am`; `-am` falha por reconstruir o reactor inteiro e aplicar `-Dtest`/o filtro do módulo-alvo a módulos irmãos sem o teste, um problema pré-existente do reactor, não desta story) -- `BUILD SUCCESS`, 0 falhas/erros, nenhum log de Testcontainers/Docker no output. Confirma o AC de `mvn test`.
- `mvn -pl jdempotent -Dtest=ScosJdempotentRedisConfigurationTest test` -- `Tests run: 4, Failures: 0, Errors: 0` (3 da Story 3.1 + `contextoFalhaComConfigClusterMalformada`). Confirma o AC de fail-fast.
- `mvn -pl jdempotent verify` -- **falha**, não por causa do wiring do Failsafe (AD-6) em si, mas por uma colisão de porta pré-existente entre os dois testes renomeados (`PrimeNumbersJdempotentEnableITTest`/`DisableITTest`), ver Completion Notes.
- `mvn -pl jdempotent -Dit.test=RedisIdempotentRepositoryTryAcquireITTest verify` (isolado) -- `BUILD SUCCESS`. Confirma que o Failsafe/sufixo `*ITTest` (AD-6) em si está corretamente wireado; o teste da Story 3.5 (porta dinâmica) roda e passa sob `verify`.

### Completion Notes List

- AD-6 implementado exatamente como especificado: `maven-surefire-plugin` com `<excludes>**/*ITTest.java</excludes>`, novo `maven-failsafe-plugin:3.5.4` com `<includes>**/*ITTest.java</includes>` e `<executions>` (`integration-test`, `verify`); novo step de CI escopado (`mvn -B -pl jdempotent -am verify`) logo após "Run tests"; os dois testes sem sufixo renomeados (arquivo + classe, sem mudar lógica); novo teste de fail-fast em `ScosJdempotentRedisConfigurationTest`.
- **Achado bloqueante, fora do escopo autorizado desta story ("sem mudar lógica" nas renomeações; produção só pode ser tocada em `ScosJdempotentRedisConfiguration`)**: `PrimeNumbersJdempotentEnableITTest`/`DisableITTest` usam `src/test/resources/docker-compose.yml` com portas de host **fixas** (`6379:6379`, `26379:26379`) e um `@Container` de **instância** (não `static`), então o Testcontainers JUnit5 extension sobe/derruba um `ComposeContainer` novo a cada método de teste. Entre um método/classe e o próximo, o Docker não libera a porta a tempo (race de teardown vs. novo `compose up -d`), e a segunda tentativa falha com `Bind for 0.0.0.0:6379 failed: port is already allocated` ou timeout esperando a porta abrir.
  - **Confirmado pré-existente, não introduzido por esta story**: reproduzido de forma idêntica no `baseline_commit` (antes de qualquer mudança desta story), rodando só `PrimeNumbersJdempotentEnableTest` sozinho via `mvn -Dtest=PrimeNumbersJdempotentEnableTest test` -- os próprios 2 métodos da mesma classe colidem entre si (mesmo root cause dos erros de porta já documentados nas Stories 3.1/3.4/3.5 citados no Problem desta story).
  - `RedisIdempotentRepositoryTryAcquireITTest` (Story 3.5) não é afetado -- usa um `GenericContainer` `static` com porta mapeada dinamicamente, exatamente para evitar esse problema (documentado no próprio Javadoc da classe).
  - Corrigir exigiria mudar a fixture (`docker-compose.yml` e/ou tornar o `@Container` `static`/compartilhado por classe) -- **mudança de lógica de teste fora do que a Task 3 autorizou** ("Renomear ... sem mudar lógica"). Não corrigido nesta implementação; registrado aqui para decisão humana em vez de resolvido por adivinhação.
  - Efeito prático: `mvn verify` no módulo (local e no novo step de CI) falha hoje por essa causa pré-existente, não pelo wiring do Failsafe -- confirmado isolando `RedisIdempotentRepositoryTryAcquireITTest` sozinho sob `verify` (passa) e reproduzindo a falha sem nenhuma mudança desta story no `baseline_commit`.
- **Achado adicional (verificação pós-implementação, corrigido nesta story por decisão humana em 2026-08-29)**: `IdempotentAspectITTest`, `IdempotentWithoutAspectITTest` e `IdempotentAspectWithErrorCallbackITTest` já usavam o sufixo `ITTest` antes desta story, mas nenhuma das 3 usa Testcontainers/Docker (são testes de contexto Spring/AOP puro com `InMemoryIdempotentRepository`) — o novo `<excludes>**/*ITTest.java</excludes>` do Surefire as varreu para fora de `mvn test` (confirmado: 38 testes antes da correção, nenhuma das 3 classes presente). Renomeadas (arquivo + classe + as 2 auto-referências em `@ContextConfiguration(classes = {...})`, sem mudar lógica) para `IdempotentAspectTest`, `IdempotentWithoutAspectTest`, `IdempotentAspectWithErrorCallbackTest` — restaura as 3 ao loop rápido do Surefire, coerente com a intenção real do AD-6 (sufixo reservado para quem precisa de infra real). `mvn -pl jdempotent test` após a correção: 50 testes, 0 falhas.
- **Rodada de review (blind-hunter, edge-case-hunter, verification-gap, 2026-08-29)**: 2 patches aplicados, ambos triviais e fora do `<frozen-after-approval>`: (1) `<failIfNoTests>true</failIfNoTests>` no `maven-failsafe-plugin`, protegendo contra o `verify` passar silenciosamente com zero testes de integração executados se o padrão `**/*ITTest.java` algum dia parar de casar com algo; (2) comentários que citam AD-6/AD-8 por sigla agora apontam para o caminho do arquivo da spine de arquitetura, legível fora do contexto BMAD. **Decisão humana explícita**: o novo step de CI (`mvn -B -pl jdempotent -am verify`) fica **vermelho intencionalmente** por causa do bug pré-existente de porta fixa (ver acima) — não foi adicionada nenhuma exclusão/skip para mascarar isso; o CI fica vermelho até a story de hardening do fixture Docker Compose corrigir de fato. Achado adicional registrado em `deferred-work.md`: o job `security-check` do CI (`mvn -Panalyze test`, nunca `verify`) perde silenciosamente a cobertura JaCoCo dos 3 testes `*ITTest` do módulo após o novo `<excludes>` do Surefire — fora do escopo autorizado (exigiria mudar o POM raiz).

## Suggested Review Order

**Split unit/integration (AD-6)**

- Surefire ganha `<excludes>` para `*ITTest.java`; Failsafe novo com `<includes>`/`failIfNoTests` e as 2 execuções.
  [`pom.xml:239-265`](../../jdempotent/pom.xml#L239)
- Novo step de CI escopado ao módulo, logo após o "Run tests" global.
  [`build.yml:47-48`](../../.github/workflows/build.yml#L47)

**Colisão de sufixo com testes que não usam Docker**

- 3 classes que já eram `*ITTest` sem precisar de Testcontainers, renomeadas para voltar ao loop rápido do Surefire.
  [`IdempotentAspectTest.java:54`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTest.java#L54)
  [`IdempotentWithoutAspectTest.java:31`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentWithoutAspectTest.java#L31)
  [`IdempotentAspectWithErrorCallbackTest.java:48`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/callback/IdempotentAspectWithErrorCallbackTest.java#L48)

**Fail-fast em config Redis inválida (AD-8)**

- Novo teste prova que config malformada falha o contexto com causa raiz identificável.
  [`ScosJdempotentRedisConfigurationTest.java:92`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfigurationTest.java#L92)

**Peripherals — renomeações sem mudança de lógica**

- Sufixo corrigido para as classes que já usam Testcontainers/docker-compose (bug de porta fixa pré-existente, deixado vermelho intencionalmente).
  [`PrimeNumbersJdempotentEnableITTest.java:52`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/test/PrimeNumbersJdempotentEnableITTest.java#L52)
  [`PrimeNumbersJdempotentDisableITTest.java:50`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/test/PrimeNumbersJdempotentDisableITTest.java#L50)
