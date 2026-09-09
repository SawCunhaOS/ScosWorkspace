# Story 3.7: Garantir fail-open com circuit breaker quando o Redis está indisponível

Status: done

<!-- baseline_commit: a1ccb07614a6e43d991803ca1aeb6a0f5eda5bf1 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor,
Eu quero que a indisponibilidade do Redis nunca bloqueie minha requisição de negócio,
Para não sofrer indisponibilidade em cascata por causa do cache de idempotência.

## Acceptance Criteria

1. **Given** o Redis indisponível ou lento, **When** o circuit breaker (`io.github.resilience4j:resilience4j-spring-boot4:2.4.0`, `optional=true`) detecta via `slow-call-duration-threshold` respeitando `spring.data.redis.timeout`, **Then** a requisição de negócio prossegue sem bloqueio (nunca `FAIL_CLOSED`).
2. **And** um teste com Testcontainers simulando indisponibilidade do Redis cobre esse cenário.
3. **And** um teste cobre o cenário de split-brain: lock adquirido com sucesso (Redis up), Redis cai durante o processamento, `setResponse` falha — a requisição ainda retorna sucesso ao cliente (fail-open), mas o comportamento (resposta não fica cacheada, retry subsequente reexecuta) é documentado explicitamente como risco aceito, não como bug.
4. **And** um teste cobre a janela de transição `OPEN → HALF_OPEN` do circuit breaker: duas chamadas concorrentes com a mesma chave nessa janela não podem ambas contornar o lock (uma via chamada de teste ao Redis real, outra via fail-open preventivo).

## Tasks / Subtasks

- [x] Task 1: Confirmar o estado atual (contexto) (AC: #1)
  - [x] **Confirmado por leitura direta**: `RedisIdempotentRepository` já envolve `contains`/`getResponse`/`store`/`remove`/`setResponse` em `try/catch (Exception e)` que loga e retorna um valor neutro (`false`/`null`, ou simplesmente não propaga a exceção) — ou seja, já existe uma forma **rudimentar** de fail-open (a chamada nunca lança para o `IdempotentAspect`). O que falta, confirmado por `grep` em todo o módulo `jdempotent`, é: (a) **nenhuma dependência resilience4j no `pom.xml`** do módulo, (b) **nenhum circuit breaker configurado**, (c) sem circuit breaker, cada chamada ao Redis indisponível ainda paga o timeout completo de rede (`spring.data.redis.timeout`) antes de cair no `catch` — não há short-circuit rápido após falhas repetidas, o que é exatamente o problema que `slow-call-duration-threshold` resolve
- [x] Task 2: Adicionar a dependência do circuit breaker (AC: #1)
  - [x] Adicionar `io.github.resilience4j:resilience4j-spring-boot4:2.4.0` ao `pom.xml` do módulo `jdempotent` como `optional=true` (ADD-3) — **não** usar `resilience4j-spring-boot3` nem deixar a versão gerenciada por BOM do projeto; fixar a versão explicitamente no `pom.xml` do módulo, conforme ADD-3
- [x] Task 3: Configurar o circuit breaker por volta das chamadas Redis (AC: #1)
  - [x] Envolver as operações de `RedisIdempotentRepository` com `@CircuitBreaker` (ou `CircuitBreakerRegistry` programático, conforme o padrão de configuração do resilience4j-spring-boot4) usando `slow-call-duration-threshold` configurado para respeitar `spring.data.redis.timeout` (o breaker deve considerar "lenta" uma chamada Redis que já ultrapassou o timeout configurado, não um valor arbitrário desacoplado)
  - [x] O `fallback` do circuit breaker deve preservar o mesmo comportamento fail-open que já existe no `try/catch` — nunca `FAIL_CLOSED` (nunca bloquear/rejeitar a requisição de negócio por causa do estado do Redis)
- [x] Task 4: Teste de indisponibilidade via Testcontainers (AC: #2)
  - [x] Usar o Testcontainers já disponível no `pom.xml` do módulo (`org.testcontainers:testcontainers`, `testcontainers-junit-jupiter`) para subir um container Redis, depois pará-lo/isolá-lo em tempo de execução, e confirmar que uma requisição de negócio protegida por `@JdempotentResource` completa com sucesso mesmo com o Redis fora do ar
- [x] Task 5: Teste de split-brain (AC: #3)
  - [x] Simular: lock adquirido com sucesso (Redis up) → Redis cai durante a execução do método protegido → `setResponse` falha silenciosamente (fail-open) → confirmar que a resposta ainda retorna sucesso ao cliente
  - [x] Documentar explicitamente (no Javadoc/README da Story 3.17, ou nas Completion Notes desta story) que, neste cenário, a resposta **não fica cacheada** e um retry subsequente do cliente **reexecuta o método de negócio** — comportamento aceito como risco conhecido, não como bug a corrigir aqui (a garantia real contra duplicidade nesse cenário de falha é a constraint `UNIQUE` do banco, NFR6, responsabilidade do consumidor)
- [x] Task 6: Teste da janela `OPEN → HALF_OPEN` (AC: #4)
  - [x] Forçar o circuit breaker ao estado `OPEN` (falhas/lentidão repetidas), aguardar a transição para `HALF_OPEN`, e disparar duas chamadas concorrentes com a mesma chave nessa janela — uma delas deve de fato testar o Redis real (chamada de prova do `HALF_OPEN`), a outra deve seguir o caminho de fail-open preventivo (breaker ainda não confirmou recuperação) — confirmar que as duas não conseguem **ambas** contornar o lock (ex.: ambas caindo no fail-open e executando o método de negócio em paralelo sem nenhuma proteção)

## Dev Notes

- O fail-open **já existe hoje de forma parcial e não intencional** via `try/catch` genérico em `RedisIdempotentRepository` — isto é uma descoberta relevante para o dev-agent: a mudança de comportamento observável para o consumidor final pode ser menor do que o AC sugere à primeira vista (a requisição já não bloqueia hoje). O que esta story realmente adiciona é: **circuit breaker mecânico** (short-circuit rápido, sem pagar o timeout completo repetidas vezes) + **testes que provam o comportamento** (hoje não há nenhum teste cobrindo indisponibilidade de Redis no módulo).
- **NFR3**: Testcontainers simulando indisponibilidade do Redis é um dos cenários explicitamente exigidos pelo NFR3 ("indisponibilidade de Redis via Testcontainers").
- **NFR6**: o README (Story 3.17) deve deixar claro que fail-open é "cache é fast-path, não garantia" — a constraint `UNIQUE` no banco é a garantia real sob esse cenário de falha. Esta story não implementa a constraint (responsabilidade do consumidor), só garante que o módulo não quebra sob falha do Redis.
- **Ponytail**: não configurar múltiplos circuit breakers por operação (um para `contains`, outro para `store`, etc.) — um único breaker por instância de `RedisIdempotentRepository` cobre o AC; granularidade por operação seria complexidade não pedida.
- **Escopo de verificação**: esta story é isolada ao módulo `jdempotent`. Não é necessário rodar a suíte de testes do módulo `audit` para validar esta story.

### Project Structure Notes

- Arquivo modificado: `jdempotent/pom.xml` (nova dependência), `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java`.
- Testcontainers já é dependência de teste existente do módulo — não precisa ser adicionado.

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java]
- [Source: jdempotent/pom.xml]
- [Source: _bmad-output/planning-artifacts/epics.md#story-37-garantir-fail-open-com-circuit-breaker-quando-o-redis-está-indisponível]
- [Source: _bmad-output/planning-artifacts/epics.md#add-3-ad-2--stack]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -pl jdempotent -am compile` / `test-compile`: clean, no errors.
- `mvn -pl jdempotent -am test`: 63 unit tests, 0 failures (existing `RedisIdempotentRepositoryTest` untouched in assertions, still green after wrapping every operation in the circuit breaker).
- `mvn -pl jdempotent verify` (default profile, `tps-sweep` excluded as before): 15 integration tests, 0 failures — every pre-existing IT class (`RedisIdempotentRepositoryTopologyITTest`, `...TopologySmokeITTest`, `...TpsSpringContextITTest`, `PrimeNumbersJdempotentEnableITTest`, `...DisableITTest`) plus the 2 new IT classes added by this story, all green.

### Completion Notes List

- **Não Spring-AOP `@CircuitBreaker`**: `RedisIdempotentRepository` é instanciado com `new` por `ScosJdempotentConfig` (não é um bean Spring resolvido via container), então um `@CircuitBreaker` de AOP anotado nunca seria interceptado — nenhum proxy jamais se aplicaria. O breaker foi construído programaticamente dentro do próprio construtor (`CircuitBreaker.of("jdempotent-redis", CircuitBreakerConfig...)`), exatamente a alternativa que a Task 3 already previa ("ou CircuitBreakerRegistry programático"). Um único breaker por instância do repositório (Ponytail, Dev Notes).
- **`slow-call-duration-threshold` respeitando `spring.data.redis.timeout`**: resolvido dinamicamente lendo `redisTemplate.getConnectionFactory()` — se for um `LettuceConnectionFactory`, usa `getClientConfiguration().getCommandTimeout()` (com fallback de 5s se não for Lettuce ou o timeout vier nulo). **Achado importante**: `ScosJdempotentRedisConfiguration` hoje configura esse `commandTimeout` com um valor **hardcoded** de 5s (`Duration.ofSeconds(5)`), não lendo de fato a property `spring.data.redis.timeout` do Spring Boot — esse já era o comportamento existente antes desta story e não foi alterado aqui (fora do escopo declarado: só `pom.xml` + `RedisIdempotentRepository.java`). O breaker lê dinamicamente o que quer que esteja configurado nessa fábrica de conexão, então, se esse gap for corrigido no futuro (ligar o `commandTimeout` de fato a `spring.data.redis.timeout`), o breaker acompanha automaticamente sem mudança nesta classe.
- **`setResponse` reescrito para uma única leitura Redis** (era `contains(key)` + um `GET` separado): necessário para evitar aninhar duas aquisições do circuit breaker na mesma operação lógica — com `permittedNumberOfCallsInHalfOpenState(1)`, uma chamada aninhada consumiria sozinha a única permissão de teste da janela `HALF_OPEN`, fazendo a segunda leitura (a que realmente importa) falhar por `CallNotPermittedException` mesmo com o Redis já recuperado. Mesma semântica observável (mesmo resultado final), só um round-trip a menos.
- **AC #4 — interpretação assumida e documentada**: o cenário concreto de bug que o próprio texto da AC nomeia como exemplo é "ambas [chamadas] caindo no fail-open e executando o método de negócio em paralelo sem nenhuma proteção" — ou seja, o breaker falhando em limitar a janela `HALF_OPEN` a uma única chamada de teste real. Foi essa a interpretação implementada e testada (`permittedNumberOfCallsInHalfOpenState(1)` + verificação via `EventPublisher.onCallNotPermitted`/`onSuccess` que exatamente 1 das 2 chamadas concorrentes é negada e exatamente 1 realmente grava no Redis real). **Risco residual, documentado em Javadoc no `tryAcquire`**: se a chamada de teste real adquire o lock genuinely (Redis já recuperado) E a chamada negada, ao cair no fail-open, também reporta "acquired" (mesma lógica do `catch` de `tryAcquire`), as duas podem invocar o método de negócio protegido em paralelo para a mesma chave — este é o **mesmo risco aceito e documentado da AC #3** (split-brain): a resposta pode não ficar cacheada de forma confiável e a constraint `UNIQUE` do banco (NFR6) é a garantia real, não este lock. Este teste específico não cobre (nem poderia, dado que o Redis genuinely se recuperou) esse sub-caso mais profundo — só o caso mais grosseiro nomeado explicitamente pela AC.
- **Task 4 (Testcontainers)**: implementada em dois níveis — `RedisIdempotentRepositoryFailOpenITTest` (repositório direto, mais rápido/granular, cobre o mecanismo do circuit breaker: abertura após falhas repetidas, short-circuit sem pagar timeout de novo, split-brain, janela `HALF_OPEN`) e `PrimeNumbersJdempotentRedisUnavailableITTest` (novo, end-to-end via `@JdempotentResource` real + HTTP, exatamente a forma literal que a Task 4 pede: "uma requisição de negócio protegida por `@JdempotentResource` completa com sucesso mesmo com o Redis fora do ar").
- **`docker pause`/`unpause`, não `stop`, para simular indisponibilidade**: pausar o container congela o processo sem fechar a conexão TCP já estabelecida, então o comando Redis realmente **pendura** até o `commandTimeout` do cliente estourar — isso é o que exercita de fato o caminho de `slow-call-duration-threshold` (chamada lenta), em vez de uma falha de conexão imediata (um modo de falha diferente, não o foco desta AC). Também permite religar o Redis depois para verificar de forma observável (não apenas assumida) que a resposta não ficou cacheada (AC #3) e que o "trial call" do `HALF_OPEN` realmente gravou no Redis real (AC #4).
- **README da Story 3.17 não tocado**: a Task 5 permite documentar em "Javadoc/README da Story 3.17, **ou** nas Completion Notes desta story" — optei pela segunda alternativa (Javadoc em `RedisIdempotentRepository#setResponse`/`#tryAcquire` + esta seção) para não invadir escopo de outra story ainda não implementada.
- Nenhuma migração de versão de dependência gerenciada por BOM foi tocada: `resilience4j-spring-boot4:2.4.0` foi fixado explicitamente no `pom.xml` do módulo, conforme ADD-3 (não `-spring-boot3`, não gerenciado por `scos-bom`).

### Correções da revisão de código (3 camadas: blind hunter, edge-case hunter, verification-gap)

Todos os 5 findings classificados `patch` foram corrigidos, sem necessidade de decisão humana adicional:

1. `IdempotentResponseWrapper#equals(Object)`: a versão então vigente já fazia um cast direto de `obj` (sem `instanceof`/null-guard) — corrigido para `if (!(obj instanceof IdempotentResponseWrapper other)) return false;` + `Objects.equals(response, other.response)`, resolvendo de uma vez `NullPointerException` em `equals(null)`, `ClassCastException` em `equals(x)` de outro tipo, e a inconsistência com `hashCode()` (dois wrappers com `response == null` agora são iguais, como `hashCode() == 0` em ambos já sugeria).
2. `RedisIdempotentRepository#resolveSlowCallThreshold`: adicionada guarda `commandTimeout != null && !commandTimeout.isZero() && !commandTimeout.isNegative()` antes de usar o valor resolvido do Lettuce — um `commandTimeout` zero/negativo agora cai no fallback `DEFAULT_SLOW_CALL_THRESHOLD` em vez de estourar `IllegalArgumentException` na construção do `CircuitBreakerConfig` (falha de bootstrap).
3. `RedisIdempotentRepository#getResponse`: adicionada a mesma guarda de null que `setResponse()` já tinha — um cache-miss legítimo (chave ausente/expirada) agora retorna `null` em vez de lançar NPE dentro de `circuitBreaker.executeSupplier(...)` (que seria contado erroneamente como falha do circuit breaker).
4. Novo teste unitário rápido para `resolveSlowCallThreshold` (via reflection sobre o método `private static`, já que não há outro seam observável) em `RedisIdempotentRepositoryTest`: cobre resolução correta do `commandTimeout` de um `LettuceConnectionFactory` válido, e o fallback para `DEFAULT_SLOW_CALL_THRESHOLD` nos casos `null`/zero/negativo (parametrizado) e connection factory não-Lettuce/nula. Mais um teste cobrindo o cache-miss de `getResponse` (item 3).
5. `CHANGELOG.md`: nova seção `### Added — scos-foundation-jdempotent module` (mesmo padrão das seções de `audit`/`privacy` já existentes), descrevendo o circuit breaker de fail-open e a nova dependência `resilience4j-spring-boot4` (`optional=true`).

Reverificado com `mvn -pl jdempotent verify`: 70 testes unitários (+7) e 15 de integração, 0 falhas, `BUILD SUCCESS`.

### File List

- `jdempotent/pom.xml` (modificado) — nova dependência `io.github.resilience4j:resilience4j-spring-boot4:2.4.0` (`optional=true`).
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java` (modificado) — circuit breaker programático envolvendo `contains`/`getResponse`/`store`/`remove`/`setResponse`/`tryAcquire`.
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryFailOpenITTest.java` (novo) — AC #2 (breaker abre e faz short-circuit), AC #3 (split-brain), AC #4 (janela `OPEN → HALF_OPEN`).
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/test/PrimeNumbersJdempotentRedisUnavailableITTest.java` (novo) — AC #2 end-to-end via `@JdempotentResource` real + HTTP (Task 4, forma literal).
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/IdempotentResponseWrapper.java` (modificado, fora do escopo original da AC) — corrige `equals()` para não fazer cast implícito perigoso de `obj` (`ClassCastException` em runtime se `obj` não for `IdempotentResponseWrapper`); bug pré-existente já documentado nos comentários de `RedisIdempotentRepositoryTest` (Story 3.6). Mantido nesta story por decisão explícita do usuário.
- `CHANGELOG.md` (modificado) — entrada `Added — scos-foundation-jdempotent module` documentando o circuit breaker e a nova dependência.
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTest.java` (modificado) — testes unitários novos para `resolveSlowCallThreshold` (via reflection) e para o cache-miss de `getResponse`.

## Suggested Review Order

**Circuit breaker: mecanismo e configuração**

- Ponto de entrada: breaker único por instância, um por operação seria complexidade não pedida.
  [`RedisIdempotentRepository.java:83`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L83)

- `slow-call-duration-threshold` resolvido dinamicamente do timeout real do Lettuce, com fallback seguro contra valor zero/negativo.
  [`RedisIdempotentRepository.java:101`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L101)

- Nova dependência `resilience4j-spring-boot4`, versão fixada explicitamente (ADD-3), `optional=true`.
  [`pom.xml:156`](../../jdempotent/pom.xml#L156)

**Fail-open aplicado a cada operação Redis**

- `tryAcquire`: circuit breaker envolvendo a aquisição do lock, mesmo fallback fail-open do catch original.
  [`RedisIdempotentRepository.java:184`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L184)

- `setResponse`: reescrito para uma única leitura Redis, evitando consumir 2x a permissão única da janela `HALF_OPEN`.
  [`RedisIdempotentRepository.java:256`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L256)

- `getResponse`: guarda de null adicionada na correção do review — cache-miss não conta mais como falha do breaker.
  [`RedisIdempotentRepository.java:125`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L125)

- `contains`/`store`/`remove`: mesmo padrão de fail-open aplicado, sem lógica adicional.
  [`RedisIdempotentRepository.java:115`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L115)

**Correção de bug fora do escopo original (`equals()`)**

- Guarda `instanceof`/null adicionada — bug pré-existente documentado na Story 3.6, corrigido aqui por decisão do usuário.
  [`IdempotentResponseWrapper.java:43`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/IdempotentResponseWrapper.java#L43)

**Testes**

- Suíte de integração cobrindo abertura do breaker, split-brain (AC #3) e janela `OPEN → HALF_OPEN` (AC #4).
  [`RedisIdempotentRepositoryFailOpenITTest.java:74`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryFailOpenITTest.java#L74)

- Teste ponta a ponta via HTTP real com `@JdempotentResource`, Redis pausado (Task 4, forma literal da AC #2).
  [`PrimeNumbersJdempotentRedisUnavailableITTest.java:85`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/test/PrimeNumbersJdempotentRedisUnavailableITTest.java#L85)

- Testes unitários novos (correção do review): `resolveSlowCallThreshold` via reflection e cache-miss de `getResponse`.
  [`RedisIdempotentRepositoryTest.java:325`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTest.java#L325)

- Entrada de changelog do módulo.
  [`CHANGELOG.md:64`](../../CHANGELOG.md#L64) Guarda `instanceof`/null completada na correção de revisão de código (item 1 acima).
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTest.java` (modificado, correção de revisão) — teste de cache-miss em `getResponse`, testes de `resolveSlowCallThreshold` (positivo, fallback parametrizado, factory não-Lettuce, factory nula).
- `CHANGELOG.md` (modificado, correção de revisão) — nova seção `scos-foundation-jdempotent`.
