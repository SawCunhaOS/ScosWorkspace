---
baseline_commit: e4b2bf4d03abf6ba76372117aa789386405eb01f
---

# Story 3.15: Corrigir TTL e `equals`/`hashCode`

Status: in-review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero que o TTL configurado seja sempre respeitado e que os objetos de requisição tenham `equals`/`hashCode` corretos,
Para eliminar comportamento inconsistente entre construtores.

## Acceptance Criteria

1. **Given** os 7 construtores de `InMemoryIdempotentRepository` (hoje 4 ignoram o TTL configurado), **When** a correção é aplicada, **Then** todos os construtores respeitam o TTL.
2. **And** `equals`/`hashCode` de `IdempotentRequestWrapper` passam a ser reflexivos e simétricos.

## Tasks / Subtasks

- [x] Task 1: **Discrepância confirmada entre o epics.md e o código real — ler antes de implementar** (AC: #1)
  - [x] O epics.md descreve "os 7 construtores de `InMemoryIdempotentRepository` (hoje 4 ignoram o TTL configurado)". **Por leitura direta do código atual, isso não bate**: `InMemoryIdempotentRepository.java` tem **apenas 1 construtor** (`public InMemoryIdempotentRepository()`, sem parâmetro de TTL). O TTL não é passado por construtor nenhum neste repositório — é passado como **parâmetro dos métodos** `store(key, request, ttl, timeUnit)` e `setResponse(key, request, response, ttl, timeUnit)` (assinaturas herdadas de `IdempotentRepository`/`AbstractIdempotentRepository`)
  - [x] **O bug real, confirmado por leitura de `AbstractIdempotentRepository.java`** (linhas 39-52): tanto `store()` (linha 40-42: `getMap().put(key, new IdempotentRequestResponseWrapper(request))`) quanto `setResponse()` (linha 44-52) **recebem `ttl`/`timeUnit` como parâmetro e os ignoram completamente** — nunca usados no corpo do método. Como `getMap()` retorna um `ConcurrentHashMap` puro (sem suporte nativo a expiração de entrada), o TTL é ignorado **em 100% das chamadas**, não em "4 de 7 construtores". Isto é uma contradição textual entre o épico e o código real — implementar a correção contra o **código real** (os métodos que ignoram o parâmetro), não contra a contagem de "7 construtores" do epics.md, que não corresponde ao estado atual do arquivo
  - [x] Se o time que mantém o PRD/epics.md quiser reconciliar essa contagem específica de "7 construtores", isso é uma decisão de quem mantém o plano de origem — este story não deve inventar 7 construtores que não existem só para bater com o texto; documentar a discrepância nas Completion Notes para rastreabilidade
- [x] Task 2: Fazer `InMemoryIdempotentRepository`/`AbstractIdempotentRepository` respeitar o TTL (AC: #1)
  - [x] Implementar expiração de entrada no repositório em memória — como `ConcurrentHashMap` não expira entradas nativamente, isso exige guardar o instante de expiração junto ao valor (ex.: em `IdempotentRequestResponseWrapper` ou um wrapper equivalente) e checar expiração em `contains()`/`getResponse()` (removendo/ignorando entradas expiradas), ou usar um mecanismo de scheduler para limpeza — escolher a abordagem mais simples que cumpre o AC sem introduzir uma dependência nova (ex.: Caffeine) não pedida pelo escopo
  - [x] `store()` e `setResponse()` passam a usar de fato o `ttl`/`timeUnit` recebido como parâmetro, em vez de ignorá-lo
  - [x] Confirmar que `RedisIdempotentRepository` (que já usa TTL corretamente via `valueOperations.set(key, value, ttl, timeUnit)`, linhas 79 e 109) não precisa de mudança — o bug é específico do repositório em memória
- [x] Task 3: Corrigir `equals`/`hashCode` de `IdempotentRequestWrapper` (AC: #2)
  - [x] **Bug real confirmado**: `IdempotentRequestWrapper.equals()` (linhas 54-57) hoje é `!Objects.isNull(request) && request.stream().anyMatch(req -> req.equals(obj))` — compara se **qualquer elemento da lista interna `request`** é igual ao objeto `obj` passado, em vez de comparar se `obj` é outro `IdempotentRequestWrapper` com a mesma lista `request`. Isso quebra tanto a reflexividade (`x.equals(x)` pode ser `false` se `x` não é elemento da sua própria lista) quanto a simetria (`x.equals(y)` pode ser `true` enquanto `y.equals(x)` é `false`, já que `y` não necessariamente implementa `equals` do mesmo jeito)
  - [x] Reescrever `equals()` para o contrato padrão: checar `this == obj`, depois `obj instanceof IdempotentRequestWrapper`, depois comparar `Objects.equals(this.request, other.request)`
  - [x] `hashCode()` (linha 50-52) já delega para `request.hashCode()` — manter consistente com o novo `equals()` (deve permanecer `Objects.hashCode(request)` ou equivalente)
  - [x] **Atenção ao comentário `@SuppressFBWarnings(EQ_UNUSUAL, ...)`** já presente na classe (linhas 35-37), que justifica o `equals` atual como "intencional... mudar alteraria o comportamento de dedup" — este comentário está descrevendo o próprio bug que este AC pede para corrigir; ao aplicar a correção, remover ou atualizar esse `@SuppressFBWarnings` para não deixar uma justificativa desatualizada no código
- [x] Task 4: Testes (AC: #1, #2)
  - [x] Teste: armazenar uma entrada com TTL curto no repositório em memória, aguardar a expiração, confirmar que `contains()`/`getResponse()` não retornam mais a entrada
  - [x] Teste de reflexividade: `wrapper.equals(wrapper)` é sempre `true`
  - [x] Teste de simetria: para dois wrappers `a` e `b` com o mesmo `request`, `a.equals(b) == b.equals(a)`
  - [x] Confirmar que a mudança de `equals()` não quebra o uso de `IdempotentRequestWrapper` como chave/valor em qualquer `Map`/`Set` existente no módulo (buscar todos os usos antes de alterar)
  - [x] **Gap identificado na revisão da Story 3.19 (2026-08-30)**: `@JdempotentResource(ttl=X, ttlTimeUnit=Y)` nunca foi validado fim a fim quanto a expiração real — o único teste com TTL customizado (`PrimeNumbersJdempotentEnableITTest`, `ttl=30, ttlTimeUnit=SECONDS`) só confirma que a chave é gravada, nunca aguarda a expiração. Usando o mesmo padrão de teste desta task (TTL curto + aguardar expiração), estender para cobrir o caminho `@JdempotentResource` → `IdempotentAspect.execute()` → repositório, não só o repositório isolado

## Dev Notes

- **Esta é a discrepância mais significativa encontrada neste epic entre o texto do epics.md e o código real** — documentar isso é mais importante do que forçar a implementação a "bater" artificialmente com a contagem de 7 construtores citada no plano de origem. O comportamento observável a corrigir (TTL sempre ignorado no repositório em memória) é o mesmo espírito do AC, só a causa raiz descrita está desatualizada.
- **NFR4**: a introdução de expiração no repositório em memória é uma mudança de comportamento real (hoje entradas nunca expiram nesse repositório) — não é "mover/renomear", é correção de bug funcional, coerente com o objetivo declarado da story.
- Mudar `equals()`/`hashCode()` de uma classe usada como valor em estruturas de dados é sensível — revisar todos os pontos de uso de `IdempotentRequestWrapper` no módulo antes de aplicar, para confirmar que nenhum código depende do comportamento quebrado atual (mesmo que "depender de um bug" seja indesejável, precisa ser identificado antes do fix, não descoberto depois em produção).
- Nota de execução: esta story não altera o módulo `audit`; ao rodar a suíte de testes, não é necessário executar os testes do módulo `audit`.

### Project Structure Notes

- Arquivos modificados: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/InMemoryIdempotentRepository.java`, `AbstractIdempotentRepository.java`, `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/IdempotentRequestWrapper.java`.

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/InMemoryIdempotentRepository.java]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/AbstractIdempotentRepository.java#L39-L52]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/IdempotentRequestWrapper.java#L49-L57]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepository.java#L76-L83,L102-L114]
- [Source: _bmad-output/planning-artifacts/epics.md#story-315-corrigir-ttl-e-equalshashcode]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -o -pl jdempotent -am install -DskipTests`: `BUILD SUCCESS` (upstream `jdempotent-api`/`core`/`cache`/`privacy` installed locally so the module can be tested in isolation).
- `mvn -o -pl jdempotent test`: `BUILD SUCCESS`, 121 tests / 0 failures / 0 errors — includes the 3 new `InMemoryIdempotentRepositoryTtlTest`, 1 new `InMemoryIdempotentRepositoryTryAcquireTest` case (7 total, was 6), 5 new `IdempotentRequestWrapperTest`, and 1 new `IdempotentAspectTest` end-to-end case (13 total, was 12). `*ITTest` (Redis/Testcontainers) excluded by the module's own `maven-surefire-plugin` config, same unit-only scope as prior stories in this sandbox; `audit` module not run per this story's own execution note.

### Completion Notes List

- **AC #1 scope, as redefined by Task 1's own discrepancy analysis**: implemented against the real bug (`store()`/`setResponse()` in `AbstractIdempotentRepository` ignoring their `ttl`/`timeUnit` parameters), not against the epics.md text's "7 constructors, 4 ignore TTL" (confirmed by direct reading: `InMemoryIdempotentRepository` has exactly 1, no-arg constructor; TTL is a method parameter, never a constructor parameter, in this repository). Not reconciling that count is a deliberate choice per Task 1's own closing instruction; flagging it here again for traceability.
- **Expiration mechanism**: `IdempotentRequestResponseWrapper` (the map value shared by both `AbstractIdempotentRepository`/`InMemoryIdempotentRepository` and, separately, as the Redis-serialized value type) gained a nullable `expiresAt` (`Instant`) field and an `isExpired()` query. Chosen over a scheduled evictor (simpler, no new dependency, no background thread) — `ttl<=0`/`null` computes `expiresAt=null` (never expires), preserving the pre-existing behavior for the `@JdempotentResource` default (`ttl=0`). `contains()`/`getResponse()` treat an expired entry as absent and evict it lazily (compare-and-remove, so a concurrent `setResponse()` refresh is never clobbered).
- **Scope decision beyond the literal Task 2 bullets, made necessary by tracing the real call path (documented per this repo's "always surface details, never guess" convention)**: `IdempotentAspect.execute()` — the actual `@JdempotentResource` runtime path — never calls `contains()`/`getResponse()`; it calls `tryAcquire()` exclusively (`Lease` result). `tryAcquire()`'s pre-existing `putIfAbsent` treats any physically-present map entry as a live holder of the key, expired or not — so without also fixing `tryAcquire()`, a second real call after the configured TTL elapsed would still incorrectly replay the first call's stale cached response instead of re-executing (confirmed by tracing `Lease.inProgress`/`hasCachedResponse()` back into `IdempotentAspect.execute()`, and reproduced by the new `IdempotentAspectTest` end-to-end test before this part of the fix was added). `tryAcquire()` now atomically swaps out an expired `existing` entry via `getMap().replace(key, existing, placeholder)` (CAS, retried if a concurrent caller wins the swap first) instead of treating it as a live holder — zero behavior change for the non-expired case (same `putIfAbsent` fast path, same mismatch/in-progress logic). This stays inside `AbstractIdempotentRepository.java`, already one of the 3 files this story's own "Project Structure Notes" names — no new file was touched to make this change. Flagging it explicitly since Task 2's bullets named only `contains()`/`getResponse()`/`store()`/`setResponse()`, not `tryAcquire()`; the AC's actual wording ("TTL configurado seja sempre respeitado") and Dev Notes ("o mesmo espírito do AC" is the observable behavior, not the literal method list) is what this decision follows.
- **`@SuppressFBWarnings(EQ_UNUSUAL, ...)` on `IdempotentRequestWrapper`**: removed (not just reworded) — the justification described exactly the bug being fixed ("equals() intentionally matches wrapped elements... changing it would alter dedup behavior"), so keeping any form of it would leave a stale claim in the code. Only `EI_EXPOSE_REP2` (unrelated, still accurate) remains suppressed.
- **Map/Set usage of `IdempotentRequestWrapper` (Task 4)**: searched the whole module (`grep` for `Map<...IdempotentRequestWrapper`, `Set<...IdempotentRequestWrapper`, `HashMap<IdempotentRequestWrapper`, `HashSet<IdempotentRequestWrapper`, and any direct `.equals(`/`wrapper.equals(` call site) — no hits. `IdempotentRequestWrapper` is only ever a field value (inside `IdempotentRequestResponseWrapper`) or a method parameter/return value, never a `Map`/`Set` key or element anywhere in `jdempotent`. The equals()/hashCode() fix could not have been masking a dedup bug elsewhere in this module.
- **Story 3.19 gap test (Task 4)**: added `TestIdempotentResource#idempotentMethodWithShortTtl` (`ttl=200, ttlTimeUnit=MILLISECONDS`) and a new `IdempotentAspectTest` case that calls it through the real AOP-proxied `IdempotentAspect.execute()`, asserts `contains()`/`getResponse()` are populated immediately, sleeps past the TTL, then asserts both report the entry as gone — proving the annotation-driven path (not just the repository in isolation) honors a short TTL end-to-end. Did not touch `PrimeNumbersJdempotentEnableITTest` itself (Redis/Testcontainers, `ttl=30s` fixed on the controller) — a 30+ second sleep there would be slow for no added coverage; the new in-memory, Spring-context-only test (`TestAopContext`, no Docker) proves the same annotation-to-repository wiring faster and is consistent with how `IdempotentAspectTest`'s other wiring tests are already structured.
- **File List below is more complete than "Project Structure Notes"' 3-file list**: `IdempotentRequestResponseWrapper.java` needed the new `expiresAt`/`isExpired()` field (Task 2's own bullet already named it as the expected location: "ex.: em `IdempotentRequestResponseWrapper` ou um wrapper equivalente"), and 4 test files were added/changed for Task 4. No new production classes were introduced.

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/AbstractIdempotentRepository.java` (modified — `contains()`/`getResponse()` treat an expired entry as absent and evict it lazily; `store()`/`setResponse()` compute and set `expiresAt` from `ttl`/`timeUnit`; `tryAcquire()` atomically replaces an expired existing entry instead of treating it as a live holder; Javadoc updated to match)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/IdempotentRequestResponseWrapper.java` (modified — new `expiresAt` field + `isExpired()`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/IdempotentRequestWrapper.java` (modified — `equals()`/`hashCode()` rewritten to the standard contract; stale `EQ_UNUSUAL` `@SuppressFBWarnings` removed)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/InMemoryIdempotentRepositoryTtlTest.java` (new — TTL expiration coverage for `store()`/`setResponse()`, and a zero-TTL "never expires" regression check)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/datasource/InMemoryIdempotentRepositoryTryAcquireTest.java` (modified — +1 test: `tryAcquire()` reacquires the lock after the previous holder's TTL elapsed)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/model/IdempotentRequestWrapperTest.java` (new — reflexivity, symmetry, and a regression test pinning down the old element-comparison bug)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/utils/TestIdempotentResource.java` (modified — new `idempotentMethodWithShortTtl` fixture, `ttl=200ms`)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTest.java` (modified — +1 end-to-end test for the Story 3.19 gap)
- `CHANGELOG.md` (modified — new "Fixed — `scos-foundation-jdempotent`" entry under `[Unreleased]`)
