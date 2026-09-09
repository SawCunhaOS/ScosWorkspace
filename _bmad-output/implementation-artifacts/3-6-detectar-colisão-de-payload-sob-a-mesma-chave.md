# Story 3.6: Detectar colisão de payload sob a mesma chave

Status: done

<!-- baseline_commit: 6b17cd20590ac394ecfa2c5c6dd152f6b683d3ed -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor,
Eu quero que duas requisições distintas com a mesma chave mas payload diferente respondam `422 PAYLOAD_MISMATCH`,
Para não receber por engano a resposta cacheada de outra requisição.

## Acceptance Criteria

1. **Given** duas requisições com a mesma chave e hash de payload distinto, **When** a segunda chega, **Then** a resposta é `422 PAYLOAD_MISMATCH` em vez da resposta cacheada compartilhada.
2. **And** quando as duas condições coincidem na mesma janela de corrida (mesma chave, payload diferente, primeira ainda em processamento), a checagem de mismatch de payload tem precedência sobre o `409 IN_PROGRESS` — a segunda requisição recebe `422 PAYLOAD_MISMATCH`, não `409`, porque o mismatch é semanticamente o erro mais específico.

## Tasks / Subtasks

- [x] Task 1: Confirmar a lacuna atual (contexto) (AC: #1)
  - [x] **Confirmado por leitura direta**: nem `IdempotentAspect.execute()` nem `AbstractIdempotentRepository`/`RedisIdempotentRepository` fazem qualquer comparação de payload hoje — `contains(key)` só olha a chave, nunca o conteúdo. Duas requisições com a mesma chave (ex.: colisão de hash, ou reuso indevido de `Idempotency-Key` pelo cliente) e payloads diferentes recebem hoje a **mesma resposta cacheada** da primeira, silenciosamente — o bug que este AC elimina
- [x] Task 2: Comparar `payloadHash` no `tryAcquire` (AC: #1)
  - [x] Esta story depende do `tryAcquire(key, payloadHash, ttl)` introduzido na Story 3.5 — usar o `payloadHash` já recebido nesse contrato para comparar contra o hash da requisição em andamento associada à mesma chave
  - [x] Se a chave já existe (lock ativo ou resposta já cacheada) **e** o `payloadHash` armazenado difere do `payloadHash` da nova requisição, o `Lease`/resultado de `tryAcquire` deve sinalizar mismatch de forma distinguível de "já em progresso" (AC #1 e #2 exigem que o chamador consiga diferenciar os dois casos)
  - [x] Propagar esse sinal até o ponto de integração HTTP como `422 PAYLOAD_MISMATCH` (mecanismo exato de propagação de status é decisão de integração com o módulo `web`, documentar a interface aqui, mesmo padrão da Story 3.5)
- [x] Task 3: Precedência de mismatch sobre `409 IN_PROGRESS` na janela de corrida (AC: #2)
  - [x] Cenário: chave A, payload P1 chega e adquire o lock (ainda processando); chave A, payload P2 (diferente) chega **enquanto P1 ainda está em processamento** — o resultado correto é `422 PAYLOAD_MISMATCH`, não `409 IN_PROGRESS`, mesmo que "já em progresso" também seja tecnicamente verdade
  - [x] Implementar a ordem de checagem dentro da mesma operação atômica do `tryAcquire`: comparar `payloadHash` **antes** de decidir se o resultado é "lock obtido", "já em progresso" ou "mismatch" — não fazer duas chamadas separadas ao repositório (uma para checar payload, outra para checar lock), que reintroduziria a mesma classe de race condition que a Story 3.5 elimina
- [x] Task 4: Testes (AC: #1, #2)
  - [x] Teste sequencial: primeira requisição completa, segunda com payload diferente chega depois → `422 PAYLOAD_MISMATCH`
  - [x] Teste de concorrência real (threads reais, mesmo padrão da Story 3.5 Task 3): primeira requisição ainda em processamento, segunda com payload diferente chega na janela de corrida → `422 PAYLOAD_MISMATCH`, nunca `409`

## Dev Notes

- Esta story **depende tecnicamente da Story 3.5** estar implementada primeiro — o `tryAcquire`/`Lease` é o mecanismo que ambas compartilham. Não implementar comparação de payload em cima do fluxo antigo `contains → store → setResponse` (seria trabalho descartável assim que a 3.5 substituir o fluxo).
- **NFR3**: cobertura de 80% aplica-se também aqui — colisão de payload é um dos cenários explicitamente citados no NFR3 ("testes de... colisão de hex").
- A precedência do AC #2 (mismatch > in-progress) é uma decisão de design deliberada do epics.md, não uma sugestão — implementar exatamente essa ordem, não a ordem inversa nem "o que chegar primeiro".

### Project Structure Notes

- Arquivos modificados: mesmos da Story 3.5 (`IdempotentRepository`, `AbstractIdempotentRepository`, `InMemoryIdempotentRepository`, `RedisIdempotentRepository`, `IdempotentAspect`) — esta story estende o mesmo mecanismo, não cria um caminho paralelo.

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L163-L201]
- [Source: _bmad-output/implementation-artifacts/3-5-tornar-a-aquisição-do-lock-atômica-tryacquire-lease.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-36-detectar-colisão-de-payload-sob-a-mesma-chave]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

### Completion Notes List

- **`Lease.mismatch(...)`** (novo, `Lease.java`): terceiro estado, junto de `acquired`/`inProgress`, com um novo campo `boolean mismatch` (Lombok `@Getter` gera `isMismatch()`). Documentado que o chamador deve checar `isMismatch()` antes de `hasCachedResponse()`.
- **Decisão de precedência (AC #2)** implementada dentro da própria `tryAcquire` de cada repositório, sobre o mesmo valor `existing`/`GET` de fallback já lido para popular `existingPayloadHash`/`existingResponse` — nenhuma chamada adicional ao repositório foi introduzida: `AbstractIdempotentRepository.tryAcquire` decide sobre o retorno de `putIfAbsent`; `RedisIdempotentRepository.tryAcquire` decide sobre o `GET` de fallback já existente após o `SET NX` falhar. Em ambos, se `existingPayloadHash != null && !existingPayloadHash.equals(payloadHash)` o retorno é `Lease.mismatch(...)` — antes de considerar cache ou in-progress.
- **`IdempotentPayloadMismatchException`** (novo, `jdempotent/core/exception/`): mesmo padrão de `IdempotentInProgressException` (Story 3.5) — `RuntimeException` carregando a `IdempotencyKey`, com Javadoc documentando que a tradução para `422 Unprocessable Entity`/`PAYLOAD_MISMATCH` é responsabilidade de um `@ExceptionHandler` no módulo consumidor (o módulo `jdempotent` não depende do módulo `web`). Nenhum `@ExceptionHandler` real existe hoje neste repositório nem para `IdempotentInProgressException` (confirmado por leitura: o único `@ControllerAdvice` de teste, `CustomExceptionHandler`, é um catch-all genérico que devolve 500) — consistente com o Dev Notes da Story 3.5, fora de escopo por design.
- **`IdempotentAspect.execute()`**: checa `lease.isMismatch()` antes de `lease.hasCachedResponse()`, lançando `IdempotentPayloadMismatchException` — isso garante a precedência do AC #2 automaticamente, já que o `Lease` retornado pelo repositório já resolveu a precedência.
- **Bug crítico encontrado e corrigido (fora do escopo original do File List, mas necessário para o AC #1 no caminho sequencial)**: `RedisIdempotentRepository.setResponse(...)` recriava o `IdempotentRequestResponseWrapper` do zero (via `prepareValue(request, response)`) sem repropagar `payloadHash` — exatamente o risco catalogado nas Completion Notes da Story 3.5 ("payloadHash não sobrevive a setResponse() no Redis"). Sem a correção, o teste sequencial do AC #1 (primeira requisição completa, segunda com payload diferente chega depois) teria falhado no backend Redis: `existingPayloadHash` viraria `null` após o primeiro `setResponse`, e a segunda chamada cairia no ramo de cache em vez de mismatch. Corrigido copiando `requestResponseWrapper.getPayloadHash()` (já lido pelo método) para o novo valor antes de persistir. `AbstractIdempotentRepository`/`InMemoryIdempotentRepository` não tinham esse bug — o `setResponse` de lá muta o wrapper existente em vez de recriá-lo.
- **Testes**: unitários em `IdempotentAspectUTTest` (mismatch com resposta cacheada e mismatch em progresso, ambos via `Lease` mockado), `InMemoryIdempotentRepositoryTryAcquireTest` (sequencial + concorrência real de 2 threads) e `RedisIdempotentRepositoryTest` (mismatch via mocks do `ValueOperations`, incluindo teste dedicado da correção do `setResponse`). Concorrência real contra Redis de verdade (Testcontainers) adicionada em `RedisIdempotentRepositoryTopologyITTest` (2 threads reais, mesma chave, payloads diferentes) mais o cenário sequencial pós-`setResponse` no mesmo arquivo — seguindo o padrão de "Standalone leg" já estabelecido pela Story 3.19 (o arquivo `RedisIdempotentRepositoryTryAcquireITTest` referenciado nas Dev Notes da Story 3.5 foi substituído por este na Story 3.19).
- Suite completa do módulo `jdempotent` executada: `mvn -pl jdempotent -am test` (unitários, todos verdes) e `mvn -pl jdempotent -am integration-test -Dit.test=RedisIdempotentRepositoryTopologyITTest,RedisIdempotentRepositoryTopologySmokeITTest,PrimeNumbersJdempotentEnableITTest,PrimeNumbersJdempotentDisableITTest` (todos verdes, incluindo os testes HTTP end-to-end pré-existentes que exercitam o aspecto real).
- **Não corrigido / fora de escopo**: nenhum `@ExceptionHandler` HTTP real foi adicionado (nem para `IdempotentInProgressException`, que já não tinha um; nem para a nova exceção) — consistente com a decisão explícita da Story 3.5 de que a integração com `web` fica para outra story/módulo consumidor.

#### Ajustes da revisão de código (achados `patch`, todos aplicados)

- **`Lease.java`**: os bullets do Javadoc de classe agora deixam explícito, na própria lista (não só num parágrafo separado abaixo), que `isMismatch()` deve ser checado antes de decidir entre replay de cache e "em progresso" — terceiro bullet adicionado e os dois originais reescritos como "mismatch false E ...".
- **`IdempotentPayloadMismatchException.java`**: removida a linha em branco antes do cabeçalho de licença.
- **`IdempotentPayloadMismatchExceptionTest.java`** (novo): cobre mensagem contendo `key.getKeyValue()`, `getKey()` retornando a chave passada, e o construtor com `key == null` (sem NPE, mensagem reflete `null`).
- **`InMemoryIdempotentRepositoryTryAcquireTest`** (`given_concurrent_real_threads_with_same_key_and_different_payloads_when_tryAcquire_then_the_loser_sees_a_mismatch`): `ExecutorService` agora em try/finally, mesmo padrão de `shutdown()`/`shutdownNow()`+cancelamento de futures já usado em `RedisIdempotentRepositoryTopologyITTest`.
- **`RedisIdempotentRepositoryTest`** (`given_the_same_payload_hash_already_stored_under_the_key_when_tryAcquire_then_lease_is_in_progress_not_mismatch`): adicionadas asserções de `hasCachedResponse()`/`getExistingResponse()` (ambas nulas/falsas, confirmando que é genuinamente in-progress). Novo teste irmão `given_the_same_payload_hash_already_finished_with_a_cached_response_when_tryAcquire_then_lease_is_not_mismatch_and_exposes_the_cached_response` cobre o caso complementar (mesma hash, resposta já cacheada) — usa `assertSame`, não `assertEquals`, porque `IdempotentResponseWrapper#equals(Object)` tem um bug pré-existente (compara `response.equals(obj)` em vez de `obj.response`), não relacionado a esta story; a descoberta ficou documentada como comentário no teste, sem corrigir a classe de produção (fora do escopo dos achados `patch` desta rodada).
- Suite reexecutada após os 5 ajustes: `mvn -pl jdempotent -am test` (63 testes, 0 falhas/erros) e `mvn -pl jdempotent -am integration-test -Dit.test=RedisIdempotentRepositoryTopologyITTest,RedisIdempotentRepositoryTopologySmokeITTest,PrimeNumbersJdempotentEnableITTest,PrimeNumbersJdempotentDisableITTest` (10 testes, 0 falhas/erros).

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/Lease.java` (modificado — estado `mismatch`; revisão: bullets do Javadoc)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/exception/IdempotentPayloadMismatchException.java` (novo; revisão: linha em branco inicial removida)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/IdempotentRepository.java` (modificado — Javadoc de `tryAcquire`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/AbstractIdempotentRepository.java` (modificado — checagem de mismatch em `tryAcquire`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java` (modificado — checagem de mismatch em `tryAcquire`; correção do `payloadHash` em `setResponse`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modificado — `execute()` lança `IdempotentPayloadMismatchException` quando `lease.isMismatch()`)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java` (modificado)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/InMemoryIdempotentRepositoryTryAcquireTest.java` (modificado; revisão: try/finally no teste de concorrência)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTest.java` (modificado; revisão: asserções de cache/in-progress + novo teste)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTopologyITTest.java` (modificado)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/exception/IdempotentPayloadMismatchExceptionTest.java` (novo, achado de revisão #3)

## Suggested Review Order

**Precedência de mismatch no ponto de integração**

- Entrada: mismatch checado antes de cache/in-progress, lançando a nova exceção.
  [`IdempotentAspect.java:176`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L176)

**Novo estado `mismatch` no modelo `Lease`**

- Terceiro estado do lease, com Javadoc atualizado após a revisão para checagem correta.
  [`Lease.java:100`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/Lease.java#L100)

**Detecção de colisão em `tryAcquire` (in-memory e Redis)**

- Comparação de `payloadHash` reaproveita o mesmo valor já lido para o lock, sem round-trip extra.
  [`AbstractIdempotentRepository.java:84`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/AbstractIdempotentRepository.java#L84)

- Mesma lógica sobre o `GET` de fallback do backend Redis, decidida antes de `inProgress`.
  [`RedisIdempotentRepository.java:119`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L119)

- Bug crítico corrigido: `payloadHash` agora sobrevive ao `setResponse()` no Redis, pré-condição do AC #1.
  [`RedisIdempotentRepository.java:171`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L171)

**Nova exceção de domínio**

- `IdempotentPayloadMismatchException`, mesmo padrão de `IdempotentInProgressException` (Story 3.5).
  [`IdempotentPayloadMismatchException.java:37`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/exception/IdempotentPayloadMismatchException.java#L37)

**Testes**

- Mismatch com cache e mismatch em progresso (precedência sobre 409), via `Lease` mockado.
  [`IdempotentAspectUTTest.java:164`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java#L164)

- Sequencial e concorrência real (2 threads) contra o repositório in-memory.
  [`InMemoryIdempotentRepositoryTryAcquireTest.java:114`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/InMemoryIdempotentRepositoryTryAcquireTest.java#L114)

- Mismatch via mocks do `ValueOperations`, incluindo a correção do `setResponse`.
  [`RedisIdempotentRepositoryTest.java:219`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTest.java#L219)

- Concorrência real contra Redis via Testcontainers (padrão "Standalone leg" da Story 3.19).
  [`RedisIdempotentRepositoryTopologyITTest.java:157`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTopologyITTest.java#L157)

- Cobertura dedicada da exceção: mensagem, `getKey()`, e ramo `key == null`.
  [`IdempotentPayloadMismatchExceptionTest.java:27`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/exception/IdempotentPayloadMismatchExceptionTest.java#L27)
