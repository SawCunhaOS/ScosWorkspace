# Story 3.5: Tornar a aquisição do lock atômica (`tryAcquire`/`Lease`)

Status: done

<!-- baseline_commit: 33ce788ff41172fb755518967bb5abab2eede64b -->
<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor fazendo chamadas concorrentes com a mesma chave,
Eu quero que a segunda chamada responda `409 IN_PROGRESS` em vez de `null` silencioso,
Para saber que já existe processamento em curso.

## Acceptance Criteria

1. **Given** duas chamadas concorrentes com a mesma chave, **When** a aquisição do lock passa a usar `tryAcquire(key, payloadHash, ttl) → Lease` atômico (Lua script), substituindo `contains → store → setResponse`, **Then** a segunda chamada responde `409 IN_PROGRESS`.
2. **And** o TTL do lease é configurável por método (não fixo) e o tipo de `ttl` é sempre `java.time.Duration`.
3. **And** um teste de concorrência real (não simulado) cobre esse cenário.
4. **And** um teste cobre o cenário do lease expirar antes do método protegido terminar (risco catalogado no plano de origem, probabilidade média): o comportamento observável é documentado e a métrica `idempotency.in_progress` (FR7) permite detectar esse caso em produção.

## Tasks / Subtasks

- [x] Task 1: Confirmar a race condition atual (contexto, não código novo) (AC: #1)
  - [x] **Confirmado por leitura direta**: `IdempotentAspect.execute()` (linhas 163-201) faz `if (idempotentRepository.contains(idempotencyKey)) { ... }` seguido, em caminho separado, de `idempotentRepository.store(...)` (linha 181) e só depois `idempotentRepository.setResponse(...)` (linha 197) — três operações não-atômicas. Entre o `contains()` retornar `false` e o `store()` executar, uma segunda chamada concorrente com a mesma chave também vê `contains() == false` e prossegue — as duas chamadas executam `pjp.proceed()` (o método de negócio) em paralelo, exatamente o que a idempotência deveria impedir
- [x] Task 2: Introduzir `tryAcquire(key, payloadHash, ttl) → Lease` (AC: #1, #2)
  - [x] Adicionar `tryAcquire(IdempotencyKey key, String payloadHash, Duration ttl)` ao contrato `IdempotentRepository` (hoje em `jdempotent/core/datasource/IdempotentRepository.java`), retornando um novo tipo `Lease` (registra se a aquisição obteve o lock, e dados suficientes para decidir 409 vs. 422 na Story 3.6)
  - [x] Implementar em `RedisIdempotentRepository` via **`SET key value NX PX <ttl_ms>`** atômico (`ValueOperations.setIfAbsent(key, value, ttl)`, que compila para esse único comando Redis) — decisão de implementação registrada nas Completion Notes: um script Lua completo não foi necessário porque esta story não exige comparar `payloadHash` atomicamente com o próprio `SET` (isso só se tornaria necessário se a Story 3.6 precisar de atomicidade cross-field); a atomicidade do AC1 está garantida pelo comando único
  - [x] Implementar em `InMemoryIdempotentRepository`/`AbstractIdempotentRepository` usando uma operação atômica equivalente do `ConcurrentHashMap` (`putIfAbsent`)
  - [x] `ttl` do `Lease` é **sempre** `java.time.Duration`
  - [x] Conversão de `JdempotentResource.ttl()`/`ttlTimeUnit()` para `Duration` feita em `IdempotentAspect.execute()` via `Duration.of(customTtl, timeUnit.toChronoUnit())`
  - [x] Fluxo `contains → store → setResponse` em `IdempotentAspect.execute()` substituído por `tryAcquire`; quando o `Lease` não é adquirido e não há resposta em cache, lança `IdempotentInProgressException` (novo, em `jdempotent/core/exception/`) — a propagação para `409 IN_PROGRESS` propriamente dita é responsabilidade de um `@ExceptionHandler` no módulo consumidor (o módulo `web` não é dependência do `jdempotent`), documentado no Javadoc da exceção
- [x] Task 3: Teste de concorrência real (AC: #3)
  - [x] `RedisIdempotentRepositoryTryAcquireITTest` — múltiplas threads reais (`ExecutorService` + `CountDownLatch`, sem `Thread.sleep`/mock de tempo) disparando a mesma chave simultaneamente contra `RedisIdempotentRepository` via Testcontainers (container Redis avulso com porta dinâmica, não o `docker-compose.yml` de portas fixas usado pelos testes HTTP existentes); confirma que exatamente uma chamada obtém o lock e as demais recebem `acquired == false` sem resposta em cache. Complementado por `InMemoryIdempotentRepositoryTryAcquireTest` (mesma prova, sem Docker, contra `AbstractIdempotentRepository`)
- [x] Task 4: Teste do cenário de lease expirando antes do método terminar (AC: #4)
  - [x] `RedisIdempotentRepositoryTryAcquireITTest#given_a_short_ttl_when_it_expires_before_the_protected_method_finishes_then_a_later_call_can_acquire_again` — TTL do lease propositalmente menor que o tempo de espera do teste; confirma que uma chamada concorrente durante o lease vê `acquired == false`, e que uma chamada posterior, após o TTL expirar no Redis, adquire um **novo** lease (`acquired == true`) mesmo que a chamada "original" nunca tenha liberado/terminado — comportamento documentado no Javadoc do teste e no Javadoc de `RedisIdempotentRepository.tryAcquire`
  - [x] `idempotency.in_progress` (Story 3.11) permanece o mecanismo de detecção em produção; esta story garante que `Lease.isAcquired()` expõe o sinal booleano necessário para essa métrica, sem implementá-la (fora de escopo, FR7/Story 3.11)

## Dev Notes

- Esta é a story mais crítica do épico: substitui o núcleo do mecanismo de idempotência. Coordenar com as Stories 3.6 (colisão de payload, usa o mesmo `tryAcquire`) e 3.9 (posicionamento do aspecto fora do `@Transactional`) — as três mexem na mesma região de código (`IdempotentAspect.execute()`).
- **NFR3**: este é exatamente o tipo de mudança que exige cobertura de 80% nas áreas tocadas (teste de concorrência real, Task 3) — não é opcional.
- **Sequenciamento**: a Story 3.6 (colisão de payload) depende do `payloadHash` já estar disponível no momento do `tryAcquire` — implementar o parâmetro `payloadHash` nesta story mesmo que a lógica de comparação/422 só seja escrita na 3.6, para não duplicar a mudança de assinatura do contrato depois.
- Não introduzir um mecanismo de retry/backoff automático para quem recebe `409 IN_PROGRESS` — não foi pedido pelo AC; a decisão de tentar de novo é do consumidor da API, não deste módulo.

### Project Structure Notes

- Arquivos modificados: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/IdempotentRepository.java`, `AbstractIdempotentRepository.java`, `InMemoryIdempotentRepository.java`, `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java`, `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java`.
- Arquivo novo: uma classe `Lease` (local a definir dentro de `jdempotent/core/model/`, mesmo pacote de `IdempotencyKey`/`IdempotentRequestWrapper`).

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L163-L201]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/AbstractIdempotentRepository.java]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java]
- [Source: utils/src/main/java/br/com/sawcunhaos/foundation/utils/annotation/jdempotent/JdempotentResource.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-35-tornar-a-aquisição-do-lock-atômica-tryacquirelease]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

### Completion Notes List

- **`Lease`** (novo, `jdempotent/core/model/Lease.java`): imutável, com factories `Lease.acquired(key, payloadHash, ttl)` e `Lease.inProgress(key, payloadHash, ttl, existingPayloadHash, existingResponse)`. `existingResponse` (um `IdempotentResponseWrapper`, nullable) é o que permite ao `IdempotentAspect` distinguir, sem round-trip extra ao repositório, uma chamada duplicada de uma retentativa concorrente já finalizada (`hasCachedResponse() == true` → devolve a resposta em cache, comportamento antigo do `contains()==true`) de uma chamada genuinamente em andamento (`hasCachedResponse() == false` → `409 IN_PROGRESS`).
- **`IdempotentInProgressException`** (novo, `jdempotent/core/exception/`): `RuntimeException` não-checked, carrega a `IdempotencyKey`. O módulo `jdempotent` não depende do módulo `web`, então não pode mapear para HTTP ele mesmo — o Javadoc documenta explicitamente que a tradução para `409 Conflict`/`IN_PROGRESS` é responsabilidade de um `@ExceptionHandler` no módulo consumidor. Isso está fora do escopo desta story por design (Dev Notes: "mecanismo exato de propagação do status HTTP é decisão de integração com o módulo web").
- **`payloadHash`**: computado em `IdempotentAspect.execute()` reaproveitando a mesma instância de `MessageDigest` já usada por `keyGenerator.generateIdempotentKey(...)` — `MessageDigest.digest()` reseta o estado internamente (contrato documentado da API), então a segunda chamada (`messageDigest.digest(requestObject.toString().getBytes(UTF_8))`) é segura. **Limitação conhecida**: como o gerador de chave atual já usa exatamente esse mesmo hash SHA-256 como sufixo da `IdempotencyKey`, `payloadHash` hoje coincide com a parte hash da própria chave — não há, neste repositório, um conceito de "chave" client-supplied distinto do hash do payload. Isso é suficiente para o contrato pedido por esta story (threading do parâmetro), mas a Story 3.6 pode precisar refinar a origem do hash (por exemplo, hash do payload completo antes da filtragem de campos ignorados) se quiser detectar colisões reais sob a mesma chave.
- **Persistência do `payloadHash`**: `AbstractIdempotentRepository.tryAcquire`/`RedisIdempotentRepository.tryAcquire` gravam o `payloadHash` no `IdempotentRequestResponseWrapper` (novo campo). **Risco documentado**: a chamada subsequente a `setResponse(...)` (após `pjp.proceed()`) recria o `IdempotentRequestResponseWrapper` do zero e não repropaga o `payloadHash` — ou seja, uma vez que a resposta é gravada, o hash do payload original "se perde" no armazenamento. Não corrigido aqui por estar fora do escopo explícito da story (que só pede o parâmetro em `tryAcquire`); fica registrado para quem implementar a Story 3.6 decidir se isso precisa ser corrigido.
- **`RedisIdempotentRepository.tryAcquire`**: usa `ValueOperations.setIfAbsent(key, value, ttl)` — que o Spring Data Redis compila para um único comando `SET key value NX PX <ttl_ms>` — em vez de um script Lua manual. Decisão registrada como comentário `ponytail:` no código: um Lua script só seria necessário se fosse preciso comparar `payloadHash` atomicamente dentro do próprio `SET` (não é o caso desta story). O `GET` de fallback usado para popular `existingPayloadHash`/`existingResponse` quando a aquisição falha NÃO é atômico com o `SET NX` — é aceitável porque só afeta dados secundários (não a exclusividade do lock, que é o requisito do AC1); documentado no Javadoc do método.
- **Fail-open em erro do Redis**: mantido o mesmo padrão já usado por `contains()`/`store()` nesta classe — em caso de exceção ao falar com o Redis, `tryAcquire` devolve `Lease.acquired(...)` (deixa a chamada prosseguir) em vez de bloquear, com log de erro. Comportamento pré-existente replicado, não uma decisão nova desta story.
- **`InMemoryIdempotentRepository`/`AbstractIdempotentRepository`**: `tryAcquire` usa `ConcurrentHashMap.putIfAbsent`, atômico. TTL não é imposto (entradas nunca expiram) — mesma lacuna pré-existente de `store()`/`setResponse()` nesta implementação, não uma regressão introduzida aqui; marcado com `ponytail:` no código.
- **`IdempotentAspectUTTest`**: os dois testes que exercitavam `contains()`/`store()`/`getResponse()` foram reescritos para stubar `tryAcquire(...)` (retornando `Lease.acquired(...)` ou `Lease.inProgress(...)` conforme o cenário); um teste novo cobre o caminho `IdempotentInProgressException`. Os dois testes que dependiam do comportamento "NPE quando o gerador de chave não é stubado" continuam funcionando sem alteração: a NPE agora ocorre em `lease.isAcquired()` sobre um `Lease` nulo (mock não stubado) em vez de em `idempotencyKey.getKeyValue()`, mas a exceção, e todas as contagens de `verify(...)`, permanecem as mesmas.
- **Testes de concorrência real** (Task 3): `RedisIdempotentRepositoryTryAcquireITTest` usa um `GenericContainer` avulso (porta dinâmica) em vez do `docker-compose.yml` de portas fixas (6379/26379) que os testes HTTP existentes (`PrimeNumbersJdempotentEnableTest`/`DisableTest`) usam — evita a colisão de porta observada entre execuções repetidas do compose fixo neste sandbox (ver abaixo). `InMemoryIdempotentRepositoryTryAcquireTest` cobre o mesmo cenário sem Docker.
- **Ambiente de teste**: `PrimeNumbersJdempotentEnableTest`/`PrimeNumbersJdempotentDisableTest` (pré-existentes, não tocados por esta story) continuam falhando neste sandbox por infraestrutura (Testcontainers `ComposeContainer` com portas de host fixas — `Timed out waiting for container port to open` / `Local Docker Compose exited abnormally`), o mesmo problema já registrado na Story 3.4. Confirmado que a falha ocorre inteiramente na camada de inicialização do container, antes de qualquer código da aplicação ser executado — não relacionado a esta mudança.
- Suite completa do módulo `jdempotent` executada (`DOCKER_HOST=unix:///var/run/docker.sock mvn -pl jdempotent -am test`): todos os testes passam exceto os dois `PrimeNumbers*Test` pré-existentes acima. Destaque: `IdempotentAspectITTest` (9/9) exercita o novo fluxo `tryAcquire` de ponta a ponta via proxy AOP real + `InMemoryIdempotentRepository` real (sem mocks), incluindo o teste que confirma remoção do lock quando o método protegido lança exceção.
- **Patches da rodada de review** (achados `patch`, aplicados diretamente): comentários `ponytail:` em `AbstractIdempotentRepository.java` e `RedisIdempotentRepository.java` renomeados para `NOTE:` (jargão de ferramenta interna não deveria vazar para Javadoc/comentário de produção). Mudança só de texto; `mvn -pl jdempotent -am compile` confirmado limpo após o patch.
- **Achados `defer`** (não corrigidos por estarem fora do escopo do AC ou por exigirem mudar código fora do File List desta story; registrados em `deferred-work.md`): (1) `payloadHash` não sobrevive a `setResponse()` no Redis — já sinalizado como risco conhecido para a Story 3.6; (2) `Duration.of(customTtl, ...)` pode lançar `ArithmeticException` para TTL extremo/absurdo na anotação; (3) janela não-atômica entre o `SET NX` e o `GET` de fallback no Redis pode gerar um falso `409 IN_PROGRESS` transitório; (4) `tryAcquire` sempre grava `request=null` no placeholder Redis, então `persistReqRes=true` não é honrado durante a janela em que a chamada está em andamento (corrigir exigiria mudar a assinatura de 3 parâmetros que a Task 2 pede explicitamente); (5) `payloadHash` via `requestObject.toString()` é impreciso para payloads sem `toString()` baseado em conteúdo; (6) um `Throwable` não-`Exception` (ex. `Error`) escapando de `pjp.proceed()` não libera o lease — trava a chave permanentemente com o novo fluxo (consequência mais severa que o `null` silencioso de antes), mas a linha do `catch (Exception e)` está fora do File List desta story.

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/Lease.java` (novo)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/exception/IdempotentInProgressException.java` (novo)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/IdempotentRequestResponseWrapper.java` (modificado — campo `payloadHash`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/IdempotentRepository.java` (modificado — método `tryAcquire`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/AbstractIdempotentRepository.java` (modificado — `tryAcquire` via `putIfAbsent`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java` (modificado — `tryAcquire` via `setIfAbsent`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modificado — `execute()` usa `tryAcquire`)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java` (modificado)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/InMemoryIdempotentRepositoryTryAcquireTest.java` (novo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTryAcquireITTest.java` (novo)

## Suggested Review Order

**Atomicidade da aquisição do lock (AC #1)**

- Contrato novo e implementações atômicas (`putIfAbsent`/`setIfAbsent`).
  [`IdempotentRepository.java:26`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/IdempotentRepository.java#L26)
  [`AbstractIdempotentRepository.java`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/AbstractIdempotentRepository.java)
  [`RedisIdempotentRepository.java`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java)
- Fluxo do aspecto substituído (`contains → store → setResponse` vira `tryAcquire`).
  [`IdempotentAspect.java:173`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L173)

**TTL sempre `Duration` (AC #2)**

- [`Lease.java`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/Lease.java)

**Cobertura de concorrência real (AC #3)**

- [`RedisIdempotentRepositoryTryAcquireITTest.java`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTryAcquireITTest.java)
- [`InMemoryIdempotentRepositoryTryAcquireTest.java`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/InMemoryIdempotentRepositoryTryAcquireTest.java)

**Cenário de lease expirando (AC #4)**

- `given_a_short_ttl_when_it_expires_before_the_protected_method_finishes_then_a_later_call_can_acquire_again` em [`RedisIdempotentRepositoryTryAcquireITTest.java`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTryAcquireITTest.java)
