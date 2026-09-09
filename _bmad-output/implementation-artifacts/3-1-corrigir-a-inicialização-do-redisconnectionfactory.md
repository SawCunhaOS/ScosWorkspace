# Story 3.1: Corrigir a inicialização do `RedisConnectionFactory`

Status: done

<!-- baseline_commit: 60d4a74993f714e7c86249a17a152c6b449df3e1 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como time consumidor com Redis standalone ou cluster,
Eu quero que o módulo inicialize sem NPE,
Para poder habilitar `jdempotent` sem workaround.

## Acceptance Criteria

1. **Given** uma aplicação com Redis standalone/cluster (não Sentinel), **When** o módulo inicializa usando `RedisConnectionFactory` do Spring Boot em vez de montar `RedisSentinelConfiguration` hardcoded, **Then** a inicialização não lança NPE em `getSentinel()`.

## Tasks / Subtasks

- [x] Task 1: Remover a montagem manual de `RedisSentinelConfiguration` (AC: #1)
  - [x] Em `ScosJdempotentRedisConfiguration.lettuceConnectionFactory()` (linhas 56-94), remover a construção de `new RedisSentinelConfiguration().master(redisProperties.getSentinel().getMaster())` — hoje isso chama `.getSentinel()` incondicionalmente; em topologia standalone/cluster (não Sentinel) essa chamada retorna `null` e `.getMaster()` lança NPE
  - [x] Substituir por resolução de topologia a partir da mesma `DataRedisProperties` já injetada nesta classe (a mesma fonte que o `RedisAutoConfiguration` nativo do Boot usa para decidir standalone/sentinel/cluster): `redisConfiguration()` agora ramifica em `sentinelConfiguration()`/`clusterConfiguration()`/`standaloneConfiguration()` conforme `getSentinel()`/`getCluster()` estejam presentes, só chamando `.getMaster()` dentro do ramo Sentinel (nota: o bean da lib continua sendo o `LettuceConnectionFactory` nomeado `JdempotentLettuceConnectionFactory` — a menção original a "injetar o bean autoconfigurado do Boot" não se aplica literalmente, pois isso descartaria o `LettuceClientConfiguration` customizado exigido pela subtask seguinte)
  - [x] Mantido o `LettuceClientConfiguration` customizado (timeouts de comando/conexão, `disconnectedBehavior`) inalterado — só a montagem hardcoded do Sentinel foi substituída
- [x] Task 2: Preservar o bean `JdempotentRedisTemplate` (AC: #1)
  - [x] `redisTemplate()` (linhas 96-105) continua recebendo a connection factory por parâmetro — só trocou a origem do bean, não a assinatura do método nem o `PolymorphicRedisSerializer` já configurado
- [x] Task 3: Cobrir os três cenários de topologia com teste
  - [x] Teste de contexto Spring com `spring.data.redis.host`/`port` apenas (standalone) confirmando que a inicialização não lança `NullPointerException`
  - [x] Teste confirmando que a topologia Sentinel configurada via `spring.data.redis.sentinel.*` continua funcionando (não é regressão desta correção); teste adicional de topologia Cluster incluído por cobrir o mesmo branch novo introduzido no código

## Dev Notes

- **Bug real confirmado por leitura direta do código** (não é hipotético): `ScosJdempotentRedisConfiguration.java`, método `lettuceConnectionFactory()`, linhas 61-75 — `redisProperties.getSentinel().getMaster()` é chamado sem checar se `getSentinel()` retorna `null`. Em `application.yml` com `spring.data.redis.host`/`port` (standalone) e sem bloco `sentinel:`, `DataRedisProperties.getSentinel()` retorna `null` e a inicialização quebra com NPE antes mesmo do contexto Spring subir.
- A classe já injeta `DataRedisProperties redisProperties` (Spring Boot `spring.data.redis.*`) via `@RequiredArgsConstructor` — é a mesma propriedade que o `RedisAutoConfiguration` nativo do Boot usa para decidir standalone vs. sentinel vs. cluster automaticamente. Não é necessário introduzir uma nova fonte de configuração.
- O `LettuceClientConfiguration` manual (timeouts, `autoReconnect`, `disconnectedBehavior=REJECT_COMMANDS`) é comportamento deliberado desta lib e deve ser preservado — a correção é só na fonte da topologia de conexão, não na configuração de resiliência do cliente Lettuce.
- **NFR4** (escopo de mudança): não alterar o `PolymorphicRedisSerializer` nem o `StringRedisSerializer` já configurados no `redisTemplate()` — fora do escopo desta story (`PolymorphicRedisSerializer` é tratado na Story 3.16).

### Project Structure Notes

- Arquivo modificado: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfiguration.java`.
- Nenhum módulo novo é criado nesta story.

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfiguration.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-31-corrigir-a-inicialização-do-redisconnectionfactory]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/ARCHITECTURE-SPINE.md]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- Confirmado via `javap`/decompilação de `spring-boot-data-redis-4.1.1.jar` que `DataRedisProperties.getSentinel()`/`getCluster()` são campos simples sem inicialização default (permanecem `null` quando o bloco YAML correspondente não é definido) — é exatamente essa a causa do NPE original.
- `mvn -pl jdempotent -Dtest=ScosJdempotentRedisConfigurationTest test`: `Tests run: 3, Failures: 0, Errors: 0` — os 3 cenários (standalone, cluster, sentinel) inicializam sem NPE.
- `mvn -pl jdempotent test` (suíte completa do módulo): `Tests run: 43, Failures: 0, Errors: 3` — os 3 erros são em `PrimeNumbersJdempotentEnableTest`/`PrimeNumbersJdempotentDisableTest` (testes de integração via Testcontainers/Docker Compose com Redis Sentinel), com `ContainerLaunchException: Timed out waiting for container port to open` / `Local Docker Compose exited abnormally... port is already allocated`.
- Verificado que essa falha é pré-existente e ambiental, não uma regressão desta story: (1) reproduzida de forma idêntica com `git stash` do código-fonte original (antes da minha alteração); (2) mesmo padrão de falha já documentado no Dev Agent Record da Story 2.9 (`ContainerLaunchException`/Docker Compose Redis Sentinel, ambiente sandboxed); (3) as portas fixas `6379`/`26379` do `docker-compose.yml` de teste colidem com containers `redis`/`redis-sentinel` órfãos de outras execuções neste ambiente.

### Completion Notes List

- Removida a montagem incondicional de `RedisSentinelConfiguration` em `lettuceConnectionFactory()`, que chamava `redisProperties.getSentinel().getMaster()` sem checar `null`. Substituída por `redisConfiguration()`, que ramifica em `sentinelConfiguration()` / `clusterConfiguration()` / `standaloneConfiguration()` conforme `redisProperties.getSentinel()`/`getCluster()` estejam presentes (mesma precedência usada internamente pelo `RedisAutoConfiguration` nativo do Boot: sentinel > cluster > standalone).
- `LettuceClientConfiguration` (timeouts de comando/conexão, `autoReconnect`, `disconnectedBehavior=REJECT_COMMANDS`) preservado sem alteração — só a origem da configuração de topologia (`RedisConfiguration`) mudou.
- `redisTemplate()` inalterado: mesma assinatura, mesmo `@Qualifier`, mesmos serializers (`StringRedisSerializer`/`PolymorphicRedisSerializer`) — fora de escopo por NFR4.
- O bean de conexão continua sendo montado manualmente pela própria classe (nomeado `JdempotentLettuceConnectionFactory`), não substituído pelo bean autoconfigurado do Boot — fazer isso descartaria o `LettuceClientConfiguration` customizado que a Task 1 explicitamente pede para preservar. A menção da Dev Note a "`RedisAutoConfiguration`" foi interpretada como referência à mesma fonte de propriedades (`DataRedisProperties`) e à mesma lógica de resolução de topologia, não como instrução de reaproveitar o bean do Boot.
- `RedisClusterConfiguration`/`RedisStandaloneConfiguration` seguem o mesmo padrão de `password`/`database` (quando aplicável) já usado no ramo Sentinel original; nenhum campo novo (`username`, SSL) foi adicionado, mantendo o mesmo escopo de propriedades que o código original já tratava.
- Criado `ScosJdempotentRedisConfigurationTest` (`ApplicationContextRunner` sobre `ScosJdempotentRedisConfiguration`, seguindo o padrão já usado em `ScosPrivacyAutoConfigurationTest`) com 3 testes: standalone (regressão do bug, sem `sentinel`/`cluster`), cluster (branch novo) e sentinel (regressão do comportamento pré-existente). Nenhum dos três precisa de Redis real/Testcontainers — a criação do `LettuceConnectionFactory` não abre conexão de rede na inicialização (`validateConnection=false`), então o teste de contexto puro já é suficiente para provar a ausência do NPE.
- Suíte completa do módulo `jdempotent` roda limpa exceto pelos 2 testes de integração Testcontainers pré-existentes (`PrimeNumbersJdempotentEnableTest`/`DisableTest`), cuja falha foi confirmada como ambiental e não causada por esta story (ver Debug Log References).
- **Patches da rodada de review** (achados `patch`, aplicados diretamente por não haver subagente de implementação reengajável): (1) restaurada a mensagem de log por topologia — cada método `sentinelConfiguration()`/`clusterConfiguration()`/`standaloneConfiguration()` agora loga qual topologia foi de fato selecionada, revertendo a regressão de observabilidade introduzida pelo log genérico único; (2) os 3 testes de `ScosJdempotentRedisConfigurationTest` foram reforçados para não apenas checar `hasNotFailed()`, mas também `isRedisSentinelAware()`/`isClusterAware()` (confirma qual `RedisConfiguration` foi de fato produzida) e a propagação de `password`/`database`/`cluster.max-redirects`. `mvn -pl jdempotent -Dtest=ScosJdempotentRedisConfigurationTest test`: `Tests run: 3, Failures: 0, Errors: 0` após os patches.
- **Achados `defer`** (não causados por esta story ou fora do escopo do AC #1, registrados em `deferred-work.md`): (1) `ScosCacheConfiguration.scosLettuceConnectionFactory()` (`cache` module) tem o mesmo bug de NPE incondicional em `getSentinel().getMaster()` — **achado de maior severidade da revisão**, não corrigido nesta story por estar fora do File List; (2) `clusterConfiguration()` não valida `cluster.nodes` vazio; (3) precedência sentinel>cluster>standalone não documentada/alertada quando ambos os blocos coexistem; (4) nenhuma topologia conecta `redisProperties.getSsl()` ao `LettuceClientConfiguration` (pré-existente).

### File List

**Modified:**
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfiguration.java`

**Created:**
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfigurationTest.java`

## Suggested Review Order

**Resolução de topologia (fix do NPE)**

- Ponto de entrada: dispara a montagem da connection factory e a resolução da topologia.
  [`ScosJdempotentRedisConfiguration.java:60`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfiguration.java#L60)

- Novo método central: ramifica sentinel → cluster → standalone em vez de assumir Sentinel sempre.
  [`ScosJdempotentRedisConfiguration.java:86`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfiguration.java#L86)

- Ramo Sentinel: lógica original preservada, agora só executa quando `getSentinel()` não é nulo (raiz do fix).
  [`ScosJdempotentRedisConfiguration.java:96`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfiguration.java#L96)

- Ramo Cluster: novo, monta `RedisClusterConfiguration` a partir de `spring.data.redis.cluster.*`.
  [`ScosJdempotentRedisConfiguration.java:117`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfiguration.java#L117)

- Ramo Standalone: novo, elimina o NPE ao não depender mais do bloco `sentinel:`.
  [`ScosJdempotentRedisConfiguration.java:133`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfiguration.java#L133)

**Testes**

- Standalone: cenário do bug original, agora inicializa sem NPE; valida password/database aplicados.
  [`ScosJdempotentRedisConfigurationTest.java:33`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfigurationTest.java#L33)

- Cluster: cobre o branch novo; valida `max-redirects` e password propagados.
  [`ScosJdempotentRedisConfigurationTest.java:52`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfigurationTest.java#L52)

- Sentinel: prova de não regressão do comportamento pré-existente.
  [`ScosJdempotentRedisConfigurationTest.java:71`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfigurationTest.java#L71)
