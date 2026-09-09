---
baseline_commit: 2686e1f8b31f4de53c80a5f8e65af48c84e0d017
---

# Story 3.11: Expor métricas de idempotência

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como operador monitorando idempotência em produção,
Eu quero métricas de acerto/colisão/degradação,
Para detectar problemas como cliente gerando chave dentro do laço de retry.

## Acceptance Criteria

1. **Given** operações de idempotência ocorrendo (acquire, hit, colisão, erro de backend, degradação), **When** `IdempotencyMetrics` é implementado (no-op por padrão, Micrometer condicional), **Then** as métricas `idempotency.acquired`, `.hit`, `.in_progress`, `.mismatch`, `.backend_error`, `.degraded` (gauge 0/1) e `.degraded.transitions` (counter) são expostas corretamente.

## Tasks / Subtasks

- [x] Task 1: Confirmar a lacuna atual (contexto) (AC: #1)
  - [x] **Confirmado por leitura direta**: busca por `Metrics`/`Micrometer` em todo `jdempotent/src/main/java` não encontrou nenhuma ocorrência — não existe hoje nenhuma instrumentação de métricas no módulo. Esta story cria o mecanismo do zero.
- [x] Task 2: Definir a interface `IdempotencyMetrics` (AC: #1)
  - [x] Criar a interface `IdempotencyMetrics` com métodos correspondentes a cada evento: `acquired()`, `hit()`, `inProgress()`, `mismatch()`, `backendError()`, `degraded(boolean)` (gauge 0/1), `degradedTransition()` (counter)
  - [x] Implementação **no-op por padrão** (classe que não faz nada em cada método) registrada como bean default — consumidores que não têm Micrometer no classpath não pagam custo nem erro de bean ausente
  - [x] Implementação condicional via Micrometer (`@ConditionalOnClass(MeterRegistry.class)` ou equivalente) que de fato registra as métricas via `Counter`/`Gauge` do Micrometer quando o consumidor tem a dependência
- [x] Task 3: Instrumentar os pontos de emissão (AC: #1)
  - [x] `idempotency.acquired`: emitido quando `tryAcquire` (Story 3.5) obtém o lock com sucesso
  - [x] `idempotency.hit`: emitido quando uma chave já tem resposta cacheada e a resposta é servida do cache (caminho `contains() == true` / equivalente pós-Story 3.5)
  - [x] `idempotency.in_progress`: emitido quando `tryAcquire` indica que a chave já está em processamento (409, Story 3.5) — esta métrica é o mecanismo de detecção em produção do cenário de lease expirando citado na Story 3.5 AC #4
  - [x] `idempotency.mismatch`: emitido quando a checagem de payload (Story 3.6) detecta `422 PAYLOAD_MISMATCH`
  - [x] `idempotency.backend_error`: emitido quando uma operação contra o repositório (Redis) falha e cai no caminho de fail-open (Story 3.7)
  - [x] `idempotency.degraded` (gauge 0/1): reflete se o módulo está atualmente operando em modo degradado (ex.: circuit breaker aberto, Story 3.7) — 1 quando degradado, 0 quando normal
  - [x] `idempotency.degraded.transitions` (counter): incrementado a cada transição de estado (normal→degradado ou degradado→normal), não a cada verificação
- [x] Task 4: Testes (AC: #1)
  - [x] Teste unitário por evento: confirmar que cada operação do `IdempotentAspect`/repositórios chama o método correto de `IdempotencyMetrics` exatamente uma vez por ocorrência
  - [x] Teste confirmando que, sem Micrometer no classpath, a implementação no-op é usada sem erro de contexto Spring

## Dev Notes

- Esta story depende funcionalmente das Stories 3.5 (acquire/in_progress), 3.6 (mismatch) e 3.7 (backend_error/degraded) já terem os pontos de decisão implementados — os nomes de evento desta story mapeiam diretamente para os resultados que `tryAcquire`/`Lease` (3.5) e o circuit breaker (3.7) já produzem. Implementar esta story **depois** das três, para instrumentar pontos que já existem, em vez de adivinhar a interface antes dela existir.
- **Ponytail**: não criar uma abstração de "provider de métricas" plugável além de Micrometer (ex.: suporte a múltiplos backends de métricas simultâneos) — não foi pedido; o AC pede especificamente Micrometer condicional com fallback no-op, nada além disso.
- `idempotency.degraded` como gauge 0/1 (não um enum de estados) é uma decisão explícita do AC — não substituir por um valor mais granular (ex.: estado do circuit breaker CLOSED/OPEN/HALF_OPEN) sem confirmação; se for útil expor o estado detalhado também, isso seria uma métrica adicional, não substituta.

### Project Structure Notes

- Arquivo novo: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/metrics/IdempotencyMetrics.java` (interface) e implementações (no-op, Micrometer).
- Arquivos modificados: `IdempotentAspect.java`, `RedisIdempotentRepository.java` (pontos de emissão).

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java]
- [Source: _bmad-output/implementation-artifacts/3-5-tornar-a-aquisição-do-lock-atômica-tryacquire-lease.md]
- [Source: _bmad-output/implementation-artifacts/3-7-garantir-fail-open-com-circuit-breaker-quando-o-redis-está-i.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-311-expor-métricas-de-idempotência]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- **Pinned BOM `br.com.sawcunhaos:scos-bom:1.4.4-SNAPSHOT` is not resolvable in this sandbox**: confirmed via direct `curl` against `https://central.sonatype.com/repository/maven-snapshots/br/com/sawcunhaos/scos-bom/maven-metadata.xml`, which lists only `1.4.0-SNAPSHOT` as published (`1.4.4-SNAPSHOT` itself returns `404`). This blocks the entire reactor (any module, not just `jdempotent`), predates this story (root `pom.xml`'s parent version was last touched at Story 2.9), and is unrelated to this change — a pre-existing environment/publishing gap.
- **Worked around locally, for verification only, then reverted**: a complete `scos-bom:1.3.1-SNAPSHOT` POM was already cached locally (`~/.m2/repository/br/com/sawcunhaos/scos-bom/1.3.1-SNAPSHOT/`). Temporarily repointed both `scos-bom` references in root `pom.xml` (the `<parent>` and the `dependencyManagement` import) from `1.4.4-SNAPSHOT` to `1.3.1-SNAPSHOT`, ran the real build against it, then reverted `pom.xml` via `git checkout -- pom.xml` (confirmed clean via `git diff`/`git status` afterward — no residual change). This is a proxy BOM version, not the pinned one, so third-party dependency versions it manages could differ slightly from the real target; a CI run against the real `1.4.4-SNAPSHOT` (once published) is still the authoritative check, but this gives actual compiler/test-runner evidence rather than only manual reasoning.
- **`mvn -pl jdempotent -am compile` (offline, against the proxy BOM)**: `BUILD SUCCESS`, exit 0, no errors.
- **`mvn -pl jdempotent -am test-compile`**: `BUILD SUCCESS`, exit 0, no errors (needed network once, for `com.tngtech.archunit:archunit-junit5` test dependency of the sibling `jdempotent-api` module — unrelated to this story).
- **`mvn -pl jdempotent -am test`**: `BUILD SUCCESS`, exit 0. All 19 test classes / 93 tests in the module green (0 failures, 0 errors), confirmed via `target/surefire-reports/*.txt`, including every file touched by this story: `IdempotentAspectTest` (10), `IdempotentAspectUTTest` (12, incl. the new per-event `IdempotencyMetrics` assertions), `RedisIdempotentRepositoryTest` (20, incl. the new `backendError`/`degraded`/`degradedTransition` test), `MicrometerIdempotencyMetricsTest` (2, new), `ScosJdempotentMetricsConfigurationTest` (3, new), `ScosJdempotentConfigTest` (1), `ScosJdempotentPropertiesTest` (3) — the latter two confirm the pre-existing tests still pass after wiring `IdempotencyMetrics` into `ScosJdempotentConfig`'s constructor. IT tests (`*ITTest`, Testcontainers/Docker) were not run — same scope as previous stories' unit-only verification pass in this sandbox; nothing in this story's `tryAcquire`/circuit-breaker-adjacent code paths that the existing IT suite already covers was changed, only new emission calls added alongside them.
- Also manually verified against the actual API surfaces of `resilience4j-circuitbreaker` and `micrometer-core` jars via `javap` (`CircuitBreaker`/`CircuitBreaker.EventPublisher`/`CircuitBreaker.StateTransition`/`Counter.Builder`/`Gauge.Builder`) before the build above confirmed it — kept here as it explains *why* the design was expected to compile, not just that it did.

### Completion Notes List

- **`IdempotencyMetrics`** (novo, `jdempotent/core/metrics/`): interface com um método por evento (`acquired`, `hit`, `inProgress`, `mismatch`, `backendError`, `degraded(boolean)`, `degradedTransition`) + `NoOpIdempotencyMetrics` (default) + `MicrometerIdempotencyMetrics` (registra `Counter`/`Gauge` reais).
- **Wiring Spring** (`ScosJdempotentMetricsConfiguration`, novo `@AutoConfiguration`, registrado em `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`): um único `@Bean` `@ConditionalOnClass(MeterRegistry.class)` usa `ObjectProvider<MeterRegistry>` (não `MeterRegistry` direto) para resolver o registry — isso evita depender da ordem relativa entre a auto-configuração deste módulo e a do actuator/Micrometer do consumidor (que só provê o bean `MeterRegistry` de fato); se nenhum `MeterRegistry` existir mesmo com Micrometer no classpath, cai em no-op sem erro. Um segundo `@Bean` `@ConditionalOnMissingBean(IdempotencyMetrics.class)` é o fallback no-op puro (sem Micrometer no classpath algum). **Achado ao implementar**: como os dois `@Bean` de `IdempotencyMetrics` (Micrometer-condicional e no-op) precisam ser resolvidos ANTES de `ScosJdempotentConfig` (que agora os consome via `@RequiredArgsConstructor`), eles não podiam viver na mesma classe `ScosJdempotentConfig` sem criar uma dependência circular (a config precisaria de um bean que ela mesma declara) — por isso viraram uma classe de auto-configuração própria, não mencionada no Project Structure Notes original da story (que só citava `IdempotentAspect.java`/`RedisIdempotentRepository.java` como "arquivos modificados"); `ScosJdempotentConfig.java` também precisou ser modificado para injetar e repassar o `IdempotencyMetrics` resolvido.
- **`IdempotentAspect`**: `idempotencyMetrics` é um campo mutável com `@Setter`, default `NoOpIdempotencyMetrics` — não um parâmetro de construtor, para não precisar tocar as 7 sobrecargas de construtor já existentes (mesmo padrão já usado por `idempotentRepository`). `ScosJdempotentConfig` chama o setter depois de construir o aspecto. `acquired()`/`hit()`/`inProgress()`/`mismatch()` emitidos nos 4 ramos correspondentes de `execute()`, na mesma ordem de precedência já estabelecida pelas Stories 3.5/3.6 (mismatch > cached-response/hit > in-progress > acquired).
- **`RedisIdempotentRepository`**: novo construtor de 3 parâmetros (`..., IdempotencyMetrics)`; o de 2 parâmetros delega para ele com `NoOpIdempotencyMetrics` — nenhum teste/caller existente quebra. `backendError()` chamado em todos os 6 blocos `catch` (contains/getResponse/store/tryAcquire/remove/setResponse), incluindo quando a exceção é o próprio `CallNotPermittedException` do circuit breaker (interpretação: qualquer motivo que force o caminho de fail-open conta como `backend_error` para fins de observabilidade, não só falhas de rede genuínas contra o Redis). `degraded`/`degradedTransition` ligados ao `EventPublisher.onStateTransition` do circuit breaker real (construído no mesmo construtor): "degraded" = estado != `CLOSED` (`OPEN` e `HALF_OPEN` contam igualmente); um `AtomicBoolean` local garante que `degradedTransition()` só incrementa quando o booleano observável realmente muda de valor (ex.: `OPEN` → `HALF_OPEN` não conta como transição nova, já que ambos já eram "degradado").
- **Dependência nova**: `io.micrometer:micrometer-core` (`optional=true`) em `jdempotent/pom.xml` — versão NÃO fixada explicitamente (diferente do `resilience4j-spring-boot4` da Story 3.7, que precisou de pin por ADD-3): `spring-boot-dependencies` (importado via `scos-bom`) já gerencia a versão do Micrometer, então não há necessidade/motivo para fixar aqui.
- **Testes**: estendidos os testes já existentes por cenário em `IdempotentAspectUTTest` (um `@Mock IdempotencyMetrics` + `verify(...)` adicionado a cada um dos 5 testes que já cobriam acquired/hit/in_progress/mismatch, em vez de duplicar novos testes) + um teste novo em `RedisIdempotentRepositoryTest` que dirige o circuit breaker real a abrir via 5 chamadas falhas mockadas (sem Docker: a lógica de contagem de falhas do resilience4j é pura, não depende de Redis de verdade) para provar `backendError()`/`degraded(true)`/`degradedTransition()`. Novo `MicrometerIdempotencyMetricsTest` verifica os nomes exatos dos meters contra um `SimpleMeterRegistry` real (os outros testes só verificam chamadas contra um `IdempotencyMetrics` mockado, nunca exercitam o Micrometer de verdade). Novo `ScosJdempotentMetricsConfigurationTest` cobre os 3 cenários de `@ConditionalOnClass`/`ObjectProvider` (Micrometer ausente / presente sem bean `MeterRegistry` / presente com bean) via `ApplicationContextRunner` + `FilteredClassLoader`, exatamente o mecanismo oficial do Spring Boot para testar auto-configuração condicional — cobre literalmente a Task 4 ("sem Micrometer no classpath, a implementação no-op é usada sem erro de contexto Spring"). **Efeito colateral necessário**: `ScosJdempotentConfigTest`/`ScosJdempotentPropertiesTest` (pré-existentes) precisaram adicionar `ScosJdempotentMetricsConfiguration.class` ao `withUserConfiguration(...)` de seus `ApplicationContextRunner`, já que `ScosJdempotentConfig` agora exige um bean `IdempotencyMetrics` no contexto — sem esse ajuste, os testes existentes quebrariam com `NoSuchBeanDefinitionException` em vez de exercitar o que originalmente testavam.
- **CHANGELOG.md**: nova entrada na seção `Added — scos-foundation-jdempotent module`, mesmo padrão das entradas anteriores desse módulo.
- **Verificado por build real** (ver Debug Log References acima): `mvn -pl jdempotent -am compile`/`test-compile`/`test` rodaram de verdade (não só leitura/`javap`), contra uma versão proxy do BOM (`1.3.1-SNAPSHOT`, já cacheada localmente) já que a versão pinada `1.4.4-SNAPSHOT` não está publicada em nenhum repositório alcançável deste sandbox — `pom.xml` raiz foi restaurado ao original (`git checkout`) logo depois, confirmado limpo. `BUILD SUCCESS` nos três; 93 testes/19 classes de teste do módulo, 0 falhas/erros. Testes `*ITTest` (Testcontainers/Docker) não foram executados, mesmo escopo de verificação já usado pelas stories anteriores neste sandbox.

### Correções da revisão de código (achados `patch`, todos aplicados)

Todos os 6 achados classificados `patch` por uma revisão multi-camada foram corrigidos nesta mesma sessão, sem necessidade de decisão humana adicional. Nenhum arquivo novo foi criado nesta rodada — todos os arquivos tocados já estavam no File List abaixo.

1. **Emissão de métricas agora protegida (fail-open não pode depender de `IdempotencyMetrics`)**: `IdempotentAspect` e `RedisIdempotentRepository` ganharam cada um um `private void emitMetricSafely(Runnable, String eventName)` que captura `Exception`, loga um `warn` e nunca propaga. Todas as chamadas a `idempotencyMetrics.*()` (4 em `IdempotentAspect.execute()`, 6 `backendError()` + 2 (`degraded`/`degradedTransition`) em `RedisIdempotentRepository`) passam por ele agora. Uma implementação customizada de `IdempotencyMetrics` que lance exceção não quebra mais nem o fluxo de negócio do aspecto nem a garantia de fail-open do repositório (Story 3.7).
2. **`ScosJdempotentMetricsConfiguration.micrometerIdempotencyMetrics`**: trocado `meterRegistryProvider.getIfAvailable()` por `.getIfUnique()` — 2+ beans `MeterRegistry` não-`@Primary` no contexto do consumidor (ex.: exporters Prometheus + CloudWatch simultâneos) agora caem em no-op em vez de derrubar o contexto com `NoUniqueBeanDefinitionException`.
3. **`ScosJdempotentConfig`**: o campo `private final IdempotencyMetrics idempotencyMetrics` (bean obrigatório) virou `private final ObjectProvider<IdempotencyMetrics> idempotencyMetricsProvider`, resolvido via `.getIfAvailable(NoOpIdempotencyMetrics::new)` dentro de cada um dos 2 métodos `@Bean`. Um consumidor que exclua `ScosJdempotentMetricsConfiguration` via `spring.autoconfigure.exclude` mas mantenha `ScosJdempotentConfig` ativo não perde mais `IdempotentAspect`/`RedisIdempotentRepository` inteiros (`NoSuchBeanDefinitionException`) por causa de uma métrica opcional — comportamento pré-Story-3.11 preservado.
4. **Cobertura de `backend_error` estendida**: `RedisIdempotentRepositoryTest` ganhou 5 testes novos (um por operação: `getResponse`, `store`, `tryAcquire`, `remove`, `setResponse`), cada um forçando a chamada Redis correspondente a lançar e verificando `backendError()` exatamente uma vez contra um mock — antes só `contains()` (via o teste de circuit breaker) tinha essa cobertura.
5. **Cobertura do "colapso de transições redundantes" do circuit breaker**: novo teste (`given_the_breaker_transitions_open_to_half_open_to_closed_then_only_the_actual_flips_emit_degraded_events`) usa `transitionToOpenState()`/`transitionToHalfOpenState()`/`transitionToClosedState()` do circuit breaker real (mesma técnica de `RedisIdempotentRepositoryFailOpenITTest`, Story 3.7) para provar: `OPEN → HALF_OPEN` não reemite `degraded`/`degradedTransition` (ambos já eram "degradado"), e `HALF_OPEN → CLOSED` emite `degraded(false)`/`degradedTransition()` exatamente uma vez (recuperação).
6. **Wiring `ScosJdempotentConfig` → `IdempotentAspect` agora verificado**: `IdempotentAspect.idempotencyMetrics` ganhou `@Getter` (antes só `@Setter`). `ScosJdempotentConfigTest` ganhou um teste novo e `ScosJdempotentPropertiesTest` teve uma asserção adicionada ao teste existente que já busca o bean `IdempotentAspect` real — ambos confirmam `aspect.getIdempotencyMetrics() == context.getBean(IdempotencyMetrics.class)` (mesma instância, não apenas "não nulo").
7. **Bug encontrado ao escrever o teste do item 4** (não fazia parte dos achados triados, mas bloqueava a suíte): o teste novo de `store()` inicialmente usava `valueOperations.set(any(), any(), any(), any())` — a assinatura real de `ValueOperations.set(K, V, long, TimeUnit)` tem o terceiro parâmetro como `long` primitivo, não `Long`; `any()` genérico retorna `null`, causando `NullPointerException` ao tentar autounboxing. Corrigido para `anyLong()` na terceira posição.

Reverificado com `mvn -pl jdempotent -am clean test` (mesmo proxy de BOM `1.3.1-SNAPSHOT`, revertido depois): `BUILD SUCCESS`, 19 classes de teste / 90 testes, 0 falhas/erros — `RedisIdempotentRepositoryTest` foi de 20 para 26 (+5 `backendError` por operação, +1 transições `OPEN→HALF_OPEN→CLOSED`) e `ScosJdempotentConfigTest` foi de 1 para 2 (+1 wiring). Números por classe confirmados via `target/surefire-reports/*.txt`.

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/metrics/IdempotencyMetrics.java` (novo)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/metrics/NoOpIdempotencyMetrics.java` (novo)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/metrics/MicrometerIdempotencyMetrics.java` (novo)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentMetricsConfiguration.java` (novo)
- `jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` (modificado — registra `ScosJdempotentMetricsConfiguration`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfig.java` (modificado — injeta/repassa `IdempotencyMetrics`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modificado — campo `idempotencyMetrics` + emissão de `acquired`/`hit`/`inProgress`/`mismatch`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java` (modificado — construtor com `IdempotencyMetrics`, emissão de `backendError`/`degraded`/`degradedTransition`)
- `jdempotent/pom.xml` (modificado — nova dependência `io.micrometer:micrometer-core`, `optional=true`)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java` (modificado — `@Mock IdempotencyMetrics` + `verify(...)` por cenário)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTest.java` (modificado — teste novo de `backendError`/`degraded`/`degradedTransition`)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/metrics/MicrometerIdempotencyMetricsTest.java` (novo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentMetricsConfigurationTest.java` (novo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfigTest.java` (modificado — adiciona `ScosJdempotentMetricsConfiguration` ao runner)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentPropertiesTest.java` (modificado — adiciona `ScosJdempotentMetricsConfiguration` ao runner)
- `CHANGELOG.md` (modificado — entrada `Added — scos-foundation-jdempotent module`)

## Suggested Review Order

**Contrato de métricas**

- Ponto de entrada: um método por evento do AC, com o mapeamento para `idempotency.*` documentado em Javadoc.
  [`IdempotencyMetrics.java:34`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/metrics/IdempotencyMetrics.java#L34)

- Implementação padrão: todos os métodos vazios, zero custo para quem não tem Micrometer.
  [`NoOpIdempotencyMetrics.java:23`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/metrics/NoOpIdempotencyMetrics.java#L23)

- Implementação real: registra `Counter`/`Gauge` sob os 7 nomes exatos exigidos pelo AC.
  [`MicrometerIdempotencyMetrics.java:41`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/metrics/MicrometerIdempotencyMetrics.java#L41)

**Wiring Spring (resolução do bean, robustez de auto-configuração)**

- Dois candidatos condicionais (Micrometer+registry vs no-op); `getIfUnique()` evita derrubar o contexto com múltiplos `MeterRegistry` (correção da revisão).
  [`ScosJdempotentMetricsConfiguration.java:52`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentMetricsConfiguration.java#L52)

- `ObjectProvider<IdempotencyMetrics>`, não bean obrigatório — excluir a auto-configuration de métricas não derruba mais o aspecto inteiro (correção da revisão).
  [`ScosJdempotentConfig.java:51`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfig.java#L51)

- Resolução com fallback no-op e wiring manual no aspecto construído (padrão setter, não construtor, para não tocar as 7 sobrecargas existentes).
  [`ScosJdempotentConfig.java:60`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfig.java#L60)

**Pontos de emissão e garantia de fail-open**

- Helper que blinda toda emissão contra exceção de uma implementação customizada de `IdempotencyMetrics` (correção da revisão).
  [`RedisIdempotentRepository.java:353`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L353)

- Listener do circuit breaker: `degraded`/`degradedTransition` só disparam na transição real (`compareAndSet`), não a cada checagem.
  [`RedisIdempotentRepository.java:117`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L117)

- `backendError()` no caminho de fail-open — representativo dos 6 pontos de emissão (`contains`/`getResponse`/`store`/`tryAcquire`/`remove`/`setResponse`).
  [`RedisIdempotentRepository.java:151`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L151)

- Mesmo helper de proteção, versão do aspecto.
  [`IdempotentAspect.java:417`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L417)

- Os 4 pontos de emissão do aspecto, na ordem de precedência já estabelecida pelas Stories 3.5/3.6 (mismatch > hit > in_progress > acquired).
  [`IdempotentAspect.java:199`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L199)

**Testes**

- Cobertura do circuit breaker completa: `CLOSED→OPEN` (pré-existente) e agora `OPEN→HALF_OPEN→CLOSED` sem reemissão espúria (correção da revisão).
  [`RedisIdempotentRepositoryTest.java:394`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTest.java#L394)

- Novo teste de recuperação do breaker (`OPEN→HALF_OPEN→CLOSED`), a lacuna mais específica apontada pela revisão.
  [`RedisIdempotentRepositoryTest.java:487`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTest.java#L487)

- Um dos 5 testes novos de `backendError()` por operação (antes só `contains()` tinha cobertura).
  [`RedisIdempotentRepositoryTest.java:420`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTest.java#L420)

- Confirma que o `IdempotentAspect` montado pela auto-configuration usa a mesma instância de `IdempotencyMetrics` do contexto (correção da revisão).
  [`ScosJdempotentConfigTest.java:59`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfigTest.java#L59)

- Os 3 cenários condicionais (`ApplicationContextRunner` + `FilteredClassLoader`): Micrometer ausente, presente sem `MeterRegistry`, presente com `MeterRegistry`.
  [`ScosJdempotentMetricsConfigurationTest.java:41`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentMetricsConfigurationTest.java#L41)

- Verifica os nomes exatos dos 7 meters contra um `SimpleMeterRegistry` real, não um mock.
  [`MicrometerIdempotencyMetricsTest.java:41`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/metrics/MicrometerIdempotencyMetricsTest.java#L41)

- Entrada do CHANGELOG explicando o mecanismo para quem consome o módulo.
  [`CHANGELOG.md:89`](../../CHANGELOG.md#L89)
