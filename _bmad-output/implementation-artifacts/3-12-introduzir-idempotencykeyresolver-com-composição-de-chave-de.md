---
baseline_commit: d39fb496012fdde465eabca8251f191ea13fbf10
---

# Story 3.12: Introduzir `IdempotencyKeyResolver` com composição de chave declarativa

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor definindo minha chave de idempotência,
Eu quero selecionar explicitamente os campos via `@JdempotentProperty`, com serialização canônica,
Para ter uma chave determinística independente da ordem dos campos.

## Acceptance Criteria

1. **Given** uma classe anotada com múltiplos `@JdempotentProperty`, **When** a chave é composta via `IdempotencyKeyResolver` usando serialização canônica (`TreeMap`), **Then** a chave resultante é determinística e `@JdempotentId` deixa de compor a chave.
2. **And** o mesmo `IdempotencyKeyResolver` é o único ponto de composição de chave, reutilizável por qualquer entrypoint futuro (HTTP ou mensageria).

## Tasks / Subtasks

- [x] Task 1: Confirmar o estado atual (contexto) (AC: #1)
  - [x] **`@JdempotentProperty` já existe** (`utils/annotation/jdempotent/JdempotentProperty.java`, atributo `value()`) e já é processado por `JdempotentPropertyAnnotationChain` — este AC não introduz a anotação do zero, aproveita a que já existe.
  - [x] **Confirmado por leitura direta**: a cadeia de resolução (`JdempotentIgnoreAnnotationChain` → `JdempotentPropertyAnnotationChain` → `JdempotentDefaultChain`, montada em `IdempotentAspect.fillChains()`) **não tem nenhum elo que trate `@JdempotentId` de forma especial** — um campo anotado só com `@JdempotentId` (sem `@JdempotentIgnore`) cai no `JdempotentDefaultChain`, que usa o valor do campo normalmente na composição da chave. Ou seja, **hoje `@JdempotentId` de fato compõe a chave** (confirma a premissa do FR8 de que isso precisa parar) — `@JdempotentId` deveria servir só para receber de volta o valor gerado (via `IdempotentAspect.setJdempotentId()`, linha 278), não para influenciar o hash de entrada
- [x] Task 2: Excluir `@JdempotentId` da composição de chave (AC: #1)
  - [x] Adicionar um elo à cadeia (ou modificar `JdempotentDefaultChain`) que detecta `@JdempotentId` e retorna uma `KeyValuePair` vazia (mesmo padrão de retorno usado por `JdempotentIgnoreAnnotationChain` para campos ignorados), para que esse campo nunca entre na composição do hash
- [x] Task 3: Criar `IdempotencyKeyResolver` como ponto único de composição (AC: #1, #2)
  - [x] Extrair a lógica hoje espalhada entre `IdempotentAspect.getIdempotentNonIgnorableWrapper()` (coleta de campos + chain) e `DefaultKeyGenerator.generateIdempotentKey()` (hash + prefixo) para uma classe `IdempotencyKeyResolver` dedicada, que se torna o único lugar que sabe como transformar um `IdempotentRequestWrapper` numa `IdempotencyKey`
  - [x] Usar serialização canônica via `TreeMap` (ordenação determinística por chave) ao montar o material a ser hasheado a partir dos `KeyValuePair` coletados pela `annotationChain` — hoje a ordem de iteração de `getDeclaredFields()` não é garantida entre execuções/JVMs da mesma forma que uma estrutura ordenada garante; a serialização canônica elimina essa fonte de não-determinismo
  - [x] `IdempotentAspect.execute()` passa a chamar `IdempotencyKeyResolver` em vez de orquestrar diretamente `getIdempotentNonIgnorableWrapper()` + `keyGenerator.generateIdempotentKey()`
  - [x] O `IdempotencyKeyResolver` deve ser desenhado sem acoplamento a `ProceedingJoinPoint`/AspectJ — ele recebe dados já extraídos (ex.: `IdempotentRequestWrapper`, `listenerName`), não o join point do AOP. Isto é o que garante o AC #2: o mesmo resolver poder ser reutilizado por um futuro entrypoint de mensageria (que não tem `ProceedingJoinPoint`), sem duplicar a lógica de composição de chave
- [x] Task 4: Testes (AC: #1, #2)
  - [x] Teste: uma classe com múltiplos campos `@JdempotentProperty` gera a mesma chave independente da ordem de declaração dos campos na classe (prova de determinismo via `TreeMap`)
  - [x] Teste: um campo anotado só com `@JdempotentId` **não** influencia o hash resultante (compara a chave gerada com e sem esse campo presente, mesmos demais campos — deve ser idêntica)
  - [x] Teste: `IdempotencyKeyResolver` invocado diretamente (sem passar por `IdempotentAspect`/AOP) produz o mesmo resultado que o caminho via aspecto — prova de que é reutilizável fora do contexto HTTP/AOP

## Dev Notes

- Esta story depende da Story 1.5 do Epic 1 (módulo `jdempotent-api`, onde as anotações `@Jdempotent*` podem ter migrado) — confirmar o pacote atual de `JdempotentProperty`/`JdempotentId` no momento da implementação; ver `_bmad-output/implementation-artifacts/1-5-criar-módulos-api-e-mover-as-anotações-de-contrato.md` para o inventário de destino.
- Esta story também é pré-requisito direto da Story 3.13 (header `Idempotency-Key`), que exige "o mesmo `IdempotencyKeyResolver` é o único ponto de composição de chave, reutilizável por qualquer entrypoint" (ADD-4) — implementar 3.12 antes de 3.13.
- **NFR4**: extrair a lógica existente para uma classe nova não deve mudar o valor de hash resultante para o caso comum (campos sem `@JdempotentId` presentes) — só o caso com `@JdempotentId` muda de comportamento, que é exatamente o AC desta story.

### Project Structure Notes

- Arquivo novo: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolver.java` (ou pacote equivalente).
- Arquivos modificados: `IdempotentAspect.java` (usa o resolver em vez de orquestrar diretamente), cadeia de anotações (exclusão de `@JdempotentId`).

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L162-L201,L293-L322]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/chain/JdempotentPropertyAnnotationChain.java]
- [Source: utils/src/main/java/br/com/sawcunhaos/foundation/utils/annotation/jdempotent/JdempotentProperty.java]
- [Source: utils/src/main/java/br/com/sawcunhaos/foundation/utils/annotation/jdempotent/JdempotentId.java]
- [Source: _bmad-output/implementation-artifacts/1-5-criar-módulos-api-e-mover-as-anotações-de-contrato.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-312-introduzir-idempotencykeyresolver-com-composição-de-chave-declarativa]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -pl jdempotent-api,jdempotent -am compile`: `BUILD SUCCESS`.
- `mvn -pl jdempotent-api,jdempotent -am test` (full module, not just the files touched by this story): `BUILD SUCCESS`, 95 tests / 0 failures / 0 errors across `jdempotent` + `jdempotent-api`, confirmed via the Surefire summary lines (`IdempotentAspectTest` 11, `IdempotentAspectUTTest` 12, `IdempotencyKeyResolverTest` 2 new, `JdempotentIdAnnotationChainTest` 2 new, `DefaultKeyGeneratorTest` 2, `RedisIdempotentRepositoryTest` 26, etc.). Re-ran the affected subset (chain tests, `IdempotentAspectTest`, `IdempotentAspectUTTest`, the two new generator tests) 3x back-to-back to rule out flakiness — all green every time. IT tests (`*ITTest`, Testcontainers/Docker) were not run, same scope as previous stories' unit-only verification pass in this sandbox.
- **Side note, no code impact**: `pom.xml`'s `scos-bom` import version was found rewritten from the pinned `1.4.4-SNAPSHOT` to `1.3.1-SNAPSHOT` partway through this session (same proxy-BOM symptom Story 3.11 documented, cause not fully identified — possibly a build-tool side effect from an earlier `mvn install`, not an edit I made intentionally). Reverted via `git checkout -- pom.xml`; re-ran compile/test against the restored `1.4.4-SNAPSHOT` and it still resolves and passes cleanly in this environment (unlike the harder unresolvability 3.11 hit), so no workaround was needed this time. `pom.xml` is unmodified in the final diff.

### Completion Notes List

- **Task 2 (`@JdempotentId` exclusion)**: added `JdempotentIdAnnotationChain` (new file), following the exact existing `JdempotentIgnoreAnnotationChain` pattern (empty `KeyValuePair` when the annotation is present, delegate to `nextChain` otherwise) rather than special-casing it inside `JdempotentDefaultChain` — this codebase already gives every annotation its own chain link, so a new field-owning annotation gets the same treatment. Wired into `IdempotentAspect.fillChains()` right after `JdempotentIgnoreAnnotationChain` and *before* `JdempotentPropertyAnnotationChain`, so a field carrying both `@JdempotentId` and `@JdempotentProperty` is still excluded (an edge case not covered by any AC/test, but the ordering choice is defensible and documented in the code comment).
- **Task 3 (`IdempotencyKeyResolver`, single point of composition)**: new class `jdempotent/.../core/generator/IdempotencyKeyResolver.java`. Public API is deliberately minimal: `resolve(IdempotentRequestWrapper, String listenerName)` — no `ProceedingJoinPoint`, no `MessageDigest`/`StringBuilder` plumbing exposed to callers (it manages its own `MessageDigest` internally), matching Task 3's explicit requirement that it be usable by a future non-AOP entrypoint (Story 3.13, messaging).
  - **Design decision worth flagging**: rather than re-implementing the hash+prefix algorithm inside the new class, `IdempotencyKeyResolver` wraps a `KeyGenerator` (a `DefaultKeyGenerator` in practice) and delegates to it. This was a deliberate choice over a literal code move, for two reasons: (1) `ScosJdempotentPropertiesTest` reaches into `IdempotentAspect`'s private `keyGenerator` field via `ReflectionTestUtils` and calls `generateIdempotentKey(...)` on it directly to assert the Story 3.10 namespace-prefix wiring — that field, its name, and its namespaced `DefaultKeyGenerator` instance had to keep working unchanged; (2) `IdempotentAspectUTTest`'s `@InjectMocks`-built `IdempotentAspect` stubs `DefaultKeyGenerator.generateIdempotentKey(...)` directly — wrapping (not replacing) that same generator meant this existing test kept working with zero changes. `IdempotentAspect` now holds both `keyGenerator` (unchanged, still constructor-supplied) and a new `keyResolver` field built from it (`new IdempotencyKeyResolver(this.keyGenerator)`) in all 7 constructors; `execute()` calls only `keyResolver.resolve(...)` now, never `keyGenerator` directly.
  - Field collection (`IdempotentAspect.getIdempotentNonIgnorableWrapper()`/`findIdempotentRequestArg()`) was **not** relocated into the resolver — it stays where it is. Moving it would have required changing what `IdempotentRequestWrapper` wraps, which is also used, unrelated to this story, for the Story 3.6 payload-mismatch hash (`payloadHash` in `IdempotentAspect.execute()`) — out of scope here and risked silently changing that feature's behavior. AC #2's "reusable by any future entrypoint" is satisfied by the resolver's own AOP-free signature; the story's Project Structure Notes also only list `IdempotencyKeyResolver.java` (new) + `IdempotentAspect.java`/the chain (modified), not `IdempotentIgnorableWrapper.java`'s field-collection method itself moving.
- **Task 3 (`TreeMap` canonical serialization)**: implemented as a single-line, single-file change — `IdempotentIgnorableWrapper.nonIgnoredFields` changed from `HashMap` to `TreeMap`. This is exactly "the material to be hashed, built from the `KeyValuePair`s collected by the `annotationChain`" the task describes, at the exact site it's collected (`IdempotentAspect.getIdempotentNonIgnorableWrapper()`'s `wrapper.getNonIgnoredFields().put(...)`), with zero change needed in the resolver or the aspect. Verified safe against `TreeMap`'s null-key restriction: keys reaching `.put()` are always non-blank (guarded by the existing `StringUtils.isBlank` filter), so no field/annotation name can ever be `null` there.
  - **NFR4 caveat (flagging explicitly, not silently)**: the Dev Notes state the common case (no `@JdempotentId` present) should keep the same resulting hash. Taken literally (bit-for-bit identical to the pre-story hash), that is **not achievable together with AC #1's determinism requirement** for any class with 2+ composed fields whose `HashMap` bucket order didn't already coincide with alphabetical order — switching to `TreeMap` **does** change the resulting key for such cases (that's the entire point of fixing the non-determinism). I read NFR4 as scoping "don't introduce other, unrelated behavior changes during the extraction" (e.g. don't drop the namespace prefix, don't change the algorithm) rather than "no hash may ever change," since AC #1 itself requires the ordering fix. This means **every existing stored idempotency key becomes unreachable after this deploys** (a new call with the same payload composes a different key) — acceptable for a short-TTL dedup mechanism but worth calling out explicitly as an operational note for rollout, not just an implementation detail.
- **Tests (Task 4)**: 3 new/changed test files, all reusing existing fixtures/patterns rather than inventing new scaffolding:
  1. `IdempotencyKeyResolverTest` (new) — `should_produce_the_same_key_regardless_of_field_declaration_order` (two local classes with the same `@JdempotentProperty` keys/values declared in reversed order) and `should_not_let_a_jdempotent_id_field_influence_the_resulting_key` (same `IdempotentTestPayload`, `generatedId` null vs non-null). Both call `IdempotentAspect.getIdempotentNonIgnorableWrapper(...)` directly (no AOP/join point) to build the wrapper, then `IdempotencyKeyResolver.resolve(...)` — proving the resolver is usable stand-alone, per AC #2.
  2. `IdempotentAspectTest` (extended, +1 test) — `given_resolver_invoked_directly_without_aop_when_compared_to_the_aspect_flow_then_produces_the_same_key`: builds the expected key via `new IdempotencyKeyResolver().resolve(...)` (mirroring how existing tests in this file already build their expected key via `defaultKeyGenerator.generateIdempotentKey(...)`), then drives the real AOP-proxied `testIdempotentResource.idempotentMethod(...)` and asserts the stored key matches — this is Task 4's third test verbatim ("resolver invoked directly, without going through the aspect, matches the aspect's own key").
  3. `JdempotentIdAnnotationChainTest` (new) — same shape as the existing `JdempotentIgnoreAnnotationChainTest` (empty pair when annotated, delegates to `nextChain` otherwise).
  - `IdempotentTestPayload` (shared test fixture) gained a `@JdempotentId private String generatedId` field for reuse across the above — confirmed it does not affect any existing assertion (all existing `nonIgnoredFields().size()` checks already expected exactly the non-`@JdempotentId` fields, and no test scans/counts annotations on this class by package).

### Correções da revisão de código (achados `patch`, todos aplicados)

Os 8 achados classificados `patch` por uma revisão multi-camada (blind hunter, edge-case hunter, verification-gap) foram corrigidos nesta mesma sessão, sem necessidade de decisão humana adicional. O subagente de implementação original ficou indisponível (limite de sessão da API) antes de aplicar os achados, então as correções abaixo foram aplicadas diretamente.

1. **Lacuna de teste na precedência `@JdempotentId` + `@JdempotentProperty` no mesmo campo** (achado do verification-gap, o mais sério dos 8): o comentário em `IdempotentAspect.fillChains()` já afirmava que um campo com as duas anotações é excluído da chave, mas nenhum teste provava isso — uma futura troca de ordem dos elos da cadeia reintroduziria o bug corrigido por esta story sem quebrar nenhum teste existente. Adicionado `IdempotencyKeyResolverTest#should_exclude_a_field_that_carries_both_jdempotent_id_and_jdempotent_property`, com fixture dedicada (`FieldWithBothAnnotations`), asserindo diretamente que o campo nunca chega a `nonIgnoredFields`.
2. **`IdempotentAspectTest#given_resolver_invoked_directly_without_aop_...`**: usava `new IdempotencyKeyResolver()` (sem namespace) e montava o `IdempotentIgnorableWrapper` manualmente — só "provava" equivalência com o fluxo real do aspecto por coincidência (os dois usavam namespace nulo). Corrigido para envolver o mesmo bean `defaultKeyGenerator` que `TestAopContext` já injeta no `IdempotentAspect` real, e para montar o wrapper via `IdempotentAspect#getIdempotentNonIgnorableWrapper`, igual `IdempotencyKeyResolverTest` já fazia.
3. **`IdempotencyKeyResolver.resolve()` alocava um `StringBuilder` novo a cada chamada**, descartando silenciosamente o pooling via `ThreadLocal` que `IdempotentAspect` já mantinha para esse mesmo caminho. Adicionado um `ThreadLocal<StringBuilder>` próprio da classe (mesmo padrão do aspecto, mas não compartilhado com ele, para não recriar acoplamento com `IdempotentAspect` — AC #2).
4. **Lógica de `MessageDigest.getInstance(SHA256)` + catch duplicada** entre `IdempotentAspect.execute()` e `IdempotencyKeyResolver.resolve()`: extraída para `CryptographyAlgorithm#newDigest()`, único ponto que sabe transformar o algoritmo num `MessageDigest` pronto.
5. **CHANGELOG**: o bullet `Added` de `IdempotencyKeyResolver` não mencionava a exclusão de `@JdempotentId` (só aparecia na seção `BREAKING`) — adicionada uma frase cobrindo isso também no bullet `Added`.
6. **`JdempotentIdAnnotationChainTest#should_process_and_return_empty_pair_for_jdempotent_id_field`**: só verificava que o par retornado era vazio, não que a cadeia de fato interrompe (short-circuit). Adicionado `verifyNoInteractions(jdempotentPropertyAnnotationChain)`.
7. **`JdempotentIdAnnotationChainTest#should_not_process_when_given_another_annotated_field`**: nome enganoso — o campo usado (`name`) não tem nenhuma anotação, não "outra anotação". Renomeado para `should_delegate_to_next_chain_when_field_has_no_jdempotent_id`.
8. **`IdempotentAspect.keyGenerator`/`keyResolver`**: declarados `final` — cada um é atribuído exatamente uma vez, em todos os 7 construtores, nunca reatribuído depois.

Reverificado com `mvn -pl jdempotent-api,jdempotent -am test` (offline): `BUILD SUCCESS`, 96 testes (95 + 1 novo teste do achado #1), 0 falhas/erros.

Os 2 achados classificados `defer` foram registrados em `deferred-work.md` (não bloqueiam esta story): o construtor sem argumentos de `IdempotencyKeyResolver` cair silenciosamente para namespace vazio (decisão que pertence à Story 3.13, que constrói o entrypoint que precisaria de um resolver namespaçado fora do `IdempotentAspect`), e a falta de orientação de mitigação para consumidores com TTL longo na nota `BREAKING` do CHANGELOG.

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolver.java` (novo; revisão: pooling de `StringBuilder` próprio, usa `CryptographyAlgorithm#newDigest()`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/chain/JdempotentIdAnnotationChain.java` (novo)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/IdempotentIgnorableWrapper.java` (modificado — `HashMap` → `TreeMap`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modificado — novo campo `keyResolver`, `fillChains()` inclui `JdempotentIdAnnotationChain`, `execute()` usa o resolver; revisão: `keyGenerator`/`keyResolver` agora `final`, usa `CryptographyAlgorithm#newDigest()`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/constant/CryptographyAlgorithm.java` (modificado — revisão: novo método `newDigest()`, único ponto de criação de `MessageDigest` a partir do algoritmo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolverTest.java` (novo; revisão: +1 teste de campo com dupla anotação)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/chain/JdempotentIdAnnotationChainTest.java` (novo; revisão: `verifyNoInteractions` + renome de teste)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTest.java` (modificado — +1 teste; revisão: reescrito para usar `defaultKeyGenerator`/`getIdempotentNonIgnorableWrapper`)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/utils/IdempotentTestPayload.java` (modificado — campo `generatedId` para os novos testes)
- `CHANGELOG.md` (modificado — entradas `Added`/`BREAKING` para `scos-foundation-jdempotent`, mesmo padrão das stories anteriores desse módulo; revisão: bullet `Added` também menciona a exclusão de `@JdempotentId`)

## Suggested Review Order

**`IdempotencyKeyResolver` — ponto único de composição de chave**

- Ponto de entrada: API pública mínima, sem acoplamento a AOP/`ProceedingJoinPoint`, reutilizável por futuros entrypoints (AC #2).
  [`IdempotencyKeyResolver.java:73`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolver.java#L73)

- `IdempotentAspect.execute()` agora só chama o resolver, nunca mais orquestra hash+prefixo diretamente.
  [`IdempotentAspect.java:195`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L195)

- Revisão: `MessageDigest` centralizado num único método, elimina a duplicação entre aspecto e resolver.
  [`CryptographyAlgorithm.java:57`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/constant/CryptographyAlgorithm.java#L57)

- Revisão: pooling de `StringBuilder` próprio da classe, evita realocação a cada chamada.
  [`IdempotencyKeyResolver.java:50`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolver.java#L50)

- Revisão: `keyGenerator`/`keyResolver` agora `final` — atribuídos uma vez, nunca reatribuídos.
  [`IdempotentAspect.java:94`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L94)

**Exclusão de `@JdempotentId` da composição da chave (AC #1)**

- Novo elo da cadeia: campo anotado com `@JdempotentId` retorna par vazio, nunca compõe o hash.
  [`JdempotentIdAnnotationChain.java:32`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/chain/JdempotentIdAnnotationChain.java#L32)

- Ordem deliberada: `@JdempotentId` é checado antes de `@JdempotentProperty`, então vence mesmo se ambos coexistirem no campo.
  [`IdempotentAspect.java:419`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L419)

**Serialização canônica (AC #1)**

- `TreeMap` substitui `HashMap` — ordem determinística por nome de campo, elimina a fonte de não-determinismo.
  [`IdempotentIgnorableWrapper.java:35`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/IdempotentIgnorableWrapper.java#L35)

**Testes**

- Revisão (achado mais importante): prova que um campo com as duas anotações ao mesmo tempo é excluído — a lacuna que a revisão encontrou.
  [`IdempotencyKeyResolverTest.java:77`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolverTest.java#L77)

- Revisão: prova real de equivalência resolver-vs-aspecto, usando o mesmo `DefaultKeyGenerator` namespaçado do contexto Spring de teste.
  [`IdempotentAspectTest.java:270`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTest.java#L270)

- Revisão: confirma que a cadeia interrompe de verdade (short-circuit), não só que o par retornado é vazio.
  [`JdempotentIdAnnotationChainTest.java:55`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/chain/JdempotentIdAnnotationChainTest.java#L55)

- Determinismo por ordem de declaração de campo, prova central do AC #1.
  [`IdempotencyKeyResolverTest.java:44`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolverTest.java#L44)

- `@JdempotentId` sozinho não influencia o hash — caso simples do AC #1.
  [`IdempotencyKeyResolverTest.java:59`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolverTest.java#L59)

- Fixture compartilhada ganhou o campo `generatedId` para os testes acima.
  [`IdempotentTestPayload.java:33`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/utils/IdempotentTestPayload.java#L33)

- Entrada `Added`/`BREAKING` explicando o mecanismo e o impacto operacional para consumidores.
  [`CHANGELOG.md:99`](../../CHANGELOG.md#L99)
