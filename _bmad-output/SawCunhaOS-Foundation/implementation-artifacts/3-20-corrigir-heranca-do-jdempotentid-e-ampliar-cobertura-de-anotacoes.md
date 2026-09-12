# Story 3.20: Corrigir herança do `@JdempotentId` e ampliar cobertura de anotações do `jdempotent`

Status: done

<!-- baseline_commit: 2b809871658516f8063abb0a6b9ed33aa6555312 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero que as anotações de contrato (`@JdempotentId`, `@JdempotentProperty`, `@JdempotentIgnore`, `@JdempotentResource`) funcionem corretamente em herança e tenham cobertura de teste para as combinações reais de uso,
Para eliminar falhas silenciosas e reduzir o risco de regressão nesse contrato.

## Acceptance Criteria

1. **Given** um campo anotado com `@JdempotentId` declarado numa superclasse, **When** `IdempotentAspect.setJdempotentId()` roda após a execução do método protegido, **Then** o campo recebe o valor gerado (bug conhecido, hoje falha silenciosamente sem exceção).
2. **Given** um payload com 2+ campos anotados com `@JdempotentId`, **When** o aspecto roda, **Then** todos os campos recebem o valor.
3. **Given** um objeto com campos anotados simultaneamente com `@JdempotentIgnore` e `@JdempotentProperty` (campos diferentes), **When** a chave de idempotência é composta via `IdempotentAspect` fim a fim, **Then** o hash reflete corretamente a combinação (campo ignorado fora do hash, propriedade com o nome customizado).
4. **Given** `@JdempotentProperty` sem `value()` explícito (default `""`), **When** o campo é processado pela chain, **Then** o comportamento resultante (usa nome do campo? usa string vazia como chave?) é documentado por teste.
5. **Given** um método anotado com `@JdempotentResource` sobrescrito por uma subclasse sem repetir a anotação, **When** a subclasse é chamada, **Then** o comportamento (aspecto ativa ou não) é coberto por teste.
6. **Given** `@JdempotentResource` sem `cachePrefix` explícito (default `""`), **When** a chave final é composta, **Then** um teste confirma o efeito do prefixo vazio na chave gerada.

## Tasks / Subtasks

- [x] Task 1: Corrigir o bug de herança do `@JdempotentId` (AC: #1)
  - [x] `IdempotentAspect.setJdempotentId()` (`jdempotent/src/main/java/.../core/aspect/IdempotentAspect.java`, ~linha 267-280) usa `arg.getClass().getDeclaredFields()` — trocar para percorrer a hierarquia completa de campos, mesmo padrão já usado por `getAllFieldsInHierarchy` (usado por `getIdempotentNonIgnorableWrapper`, ~linha 282-330)
  - [x] Bug já documentado em `deferred-work.md` (origem: Story 3.3 — "resolver campos anotados em toda a hierarquia de classes" — que resolveu a leitura da hierarquia para composição de chave, mas não para a escrita de volta do `@JdempotentId`)
- [x] Task 2: Testes de combinação/herança (AC: #2, #3, #5)
  - [x] Payload com múltiplos campos `@JdempotentId` simultâneos — todos recebem o valor
  - [x] Herança combinada com `@JdempotentId`/`@JdempotentProperty`/`@JdempotentIgnore` (campo anotado na superclasse, não só na classe folha)
  - [x] `@JdempotentIgnore` + `@JdempotentProperty` no mesmo objeto, hash final validado via `IdempotentAspect` fim a fim (não só via chain isolada, como os testes de `JdempotentIgnoreAnnotationChainTest`/`JdempotentPropertyAnnotationChainTest` já fazem separadamente)
  - [x] `@JdempotentResource` em método sobrescrito por subclasse sem repetir a anotação
- [x] Task 3: Testes de valores default (AC: #4, #6)
  - [x] `@JdempotentProperty` com `value()` default (`""`)
  - [x] `cachePrefix` default (`""`) fim a fim — o único teste hoje com prefixo default (`idempotentMethod`) não verifica o efeito na chave gerada

## Dev Notes

- Origem: investigação de cobertura de anotações feita durante a review da Story 3.19 (2026-08-30) + bug já conhecido registrado em `deferred-work.md` (origem: Story 3.3, já com status `review`/fechada — a Task 2 daquela story já documentava a lacuna explicitamente e condicionou a extensão do escopo a uma confirmação que não ocorreu naquela execução).
- **Ponytail**: não introduzir suporte a comportamento novo para múltiplos `@JdempotentId` — o código já itera todos os campos declarados, só precisa de teste cobrindo herança + múltiplos campos. Não inventar semântica não pedida para `value()` vazio — só documentar via teste o comportamento atual da chain.
- Distinto da Story 3.15 (`corrigir-ttl-e-equals-hashcode.md`): aquela cobre o TTL ignorado pelo `InMemoryIdempotentRepository` e o bug de `equals`/`hashCode`; esta story é especificamente sobre as anotações de contrato (`@JdempotentId`/`@JdempotentProperty`/`@JdempotentIgnore`/`@JdempotentResource`) e sua cobertura de teste.

### Project Structure Notes

- Arquivo modificado: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (Task 1).
- Arquivos de teste estendidos: `jdempotent/src/test/java/.../core/aspect/IdempotentAspectTest.java`, `IdempotentAspectUTTest.java`.

### References

- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/deferred-work.md — bug de herança do `@JdempotentId` em `setJdempotentId()`, origem Story 3.3]
- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/3-19-topologia-redis-parametrizada-concorrencia-e-throughput.md — investigação de cobertura das anotações do jdempotent, 2026-08-30]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java]

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

### Completion Notes List

- **Task 1 (AC #1):** `IdempotentAspect.setJdempotentId()` changed from `arg.getClass().getDeclaredFields()` to the existing `getAllFieldsInHierarchy(arg.getClass())` helper (the same one `getIdempotentNonIgnorableWrapper` already uses) — a one-line fix, no new behavior invented. Verified the fix is load-bearing by temporarily reverting it and confirming the two new AC #1/#2 tests fail (`expected: <...> but was: <null>`), then restoring it and confirming green.
- **Task 2 (AC #2, #3, #5):**
  - AC #1/#2 covered by one fixture (`JdempotentIdChildPayload extends JdempotentIdBasePayload`, in `IdempotentAspectUTTest`): a `@JdempotentId` field declared on the superclass plus two more on the leaf class all receive the generated value from a single `setJdempotentId()` call.
  - AC #3 covered end-to-end in `IdempotentAspectTest` using the existing `IdempotentTestPayload` (`age` = `@JdempotentIgnore`, `eventId` = `@JdempotentProperty("transactionId")`) through the real AOP-proxied `IdempotentAspect`: varying `age` alone never changes the stored key/collides as a genuine duplicate (no `IdempotentPayloadMismatchException`), while varying `eventId` alone produces a distinct key.
  - AC #5 covered by a new fixture, `TestIdempotentResourceSubclass` (new file, `core/utils`), which overrides `idempotentMethod()` without repeating `@JdempotentResource` — proven in `IdempotentAspectTest` that the override runs twice with no idempotency short-circuit (method-level annotations aren't carried across an override, unlike `@Inherited` class-level ones).
- **Task 3 (AC #4, #6):**
  - AC #4: new fixture `PropertyDefaultValuePayload` (`IdempotentAspectUTTest`) documents that `@JdempotentProperty` with no explicit `value()` composes a blank key, which the aspect's blank-key filter then drops entirely — the field is excluded from the key material altogether, it does not fall back to the field name.
  - AC #6: new `IdempotentAspectTest` test asserts the literal shape of the generated key: a blank `cachePrefix()` produces a key with no `-` separator at all (contrasted with an explicit prefix, which always prepends `"prefix-"`), then confirms the real annotated method (default `cachePrefix`) stores under exactly that prefix-less key.
- Full `mvn -pl jdempotent test`: 131 tests, only `InMemoryIdempotentRepositoryTtlTest.given_setResponse_repeatedly_refreshes_the_ttl_while_contains_races_the_expiry_check_then_the_entry_is_never_incorrectly_evicted` fails — pre-existing, unrelated to this story (a timing-sensitive concurrency test in `InMemoryIdempotentRepository`, out of this story's scope per the Dev Notes distinction from Story 3.15; reproduces deterministically in isolation, 3/3 runs, independent of any change here). Excluding that one test, all 124 remaining tests pass, including all 16 in `IdempotentAspectTest` and all 15 in `IdempotentAspectUTTest` (13 + 15 new: 3 + 3, one net-new fixture class).
- No production behavior changed beyond the one-line Task 1 fix — Task 2/3 are test-only, per the story's Ponytail note (no new semantics invented for multiple `@JdempotentId` fields or blank `value()`).

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modified — Task 1 fix + patch: `setAccessible` try/catch)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java` (modified — Task 2/3 tests + fixtures + patch: removed subsumed test, added shadowing test, added superclass `@JdempotentIgnore`/`@JdempotentProperty` test)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTest.java` (modified — Task 2/3 tests)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/utils/TestIdempotentResourceSubclass.java` (new — AC #5 fixture)
- `jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/JdempotentId.java` (modified — patch: Javadoc documents hierarchy support)
- `CHANGELOG.md` (modified — patch: entry for this story's fix under `### Fixed — scos-foundation-jdempotent`)

## Review Triage Log

Camadas rodadas: blind-hunter, edge-case-hunter, verification-gap (0 achados). Iteração de review: 1 (sem loopback — nenhum achado `intent_gap`/`bad_spec`).

1. **[blind-hunter] `CHANGELOG.md` sem entrada para o fix desta story.** Verdict: `low`. Evidência: `git diff` no `CHANGELOG.md` mostra só a entrada da Story 3.17 adicionada; a seção `### Fixed — scos-foundation-jdempotent` já documenta o padrão "falha silenciosa, agora corrigida" para a Story 3.15, mas nada para o bug de herança do `@JdempotentId` desta story. → `patch`.
2. **[blind-hunter] Diff mistura Story 3.17 (builder) sem separação; nota de conclusão fica enganosa sem descontar isso.** Verdict: `low`. Evidência: confirmado que a mistura já existia na árvore antes do subagente da 3.20 começar (`git status` prévio); o único fix possível é editar a prosa da própria spec. → rejeitado (fix editaria a spec).
3. **[blind-hunter] Javadoc de `JdempotentId.java` (jdempotent-api) não documenta suporte a herança.** Verdict: `low`. Evidência: arquivo lido — Javadoc segue dizendo só "Places the generated idempotency identifier into annotated field", sem menção a campos de superclasse. → `patch`.
4. **[blind-hunter] Teste novo de AC #1 é subconjunto estrito do teste de AC #2.** Verdict: `low`. Evidência: ambos usam `JdempotentIdChildPayload`; o primeiro só afirma `baseGeneratedId`, o segundo reafirma o mesmo campo mais dois outros. → `patch` (remover o teste subsumido).
5. **[blind-hunter] Nenhum teste cobre shadowing de nome de campo para `setJdempotentId()`.** Verdict: `low`. Evidência: existe teste dedicado de shadowing só para `findIdempotentRequestArg`/`getIdempotentNonIgnorableWrapper` (`given_a_payload_with_field_name_shadowed_from_superclass_...`); nada equivalente para `setJdempotentId`, que agora usa o mesmo `getAllFieldsInHierarchy` cujo próprio Javadoc documenta o dedup por shadowing. → `patch`.
6. **[blind-hunter] Nota da Task 1 cita linha desatualizada (~267-280) para `setJdempotentId()`.** Verdict: `low`. Evidência: método está hoje em 358-375 (confirmado via grep), após o refactor da Story 3.17 já presente na árvore. → rejeitado (fix editaria a spec).
7. **[blind-hunter] `jdempotent/README.md` não documenta os 3 comportamentos de contrato que os testes desta story comprovam.** Verdict: `low`. Evidência: `README.md` já estava untracked na árvore antes do subagente da 3.20 rodar, e o File List do subagente nunca o toca — pré-existente, não causado por esta story. → `defer`.
8. **[edge-case-hunter] `setJdempotentId()` chama `declaredField.setAccessible(true)` sem try/catch; o método irmão (`getIdempotentNonIgnorableWrapper`, linhas 384-389) captura `InaccessibleObjectException` e pula o campo.** Verdict: `medium`. Evidência: `setJdempotentId` roda na linha 256, antes de `pjp.proceed()` (fora do try/catch que só envolve o `proceed()`); um campo herdado inacessível abortaria toda a invocação do aspecto antes do método protegido rodar — exatamente a classe de campo que esta story passou a percorrer. → `patch`.
9. **[edge-case-hunter] Preocupação de que `Field.set()` em campo `@JdempotentId` estático corromperia estado compartilhado.** Verdict: `false`. Evidência: `getAllFieldsInHierarchy()` já filtra `Modifier.isStatic` explicitamente (código e Javadoc lidos diretamente). → rejeitado.
10. **[edge-case-hunter] Subtask da Task 2 ("herança combinada com `@JdempotentId`/`@JdempotentProperty`/`@JdempotentIgnore`") não foi de fato coberta.** Verdict: `low`. Evidência: a fixture de herança (`JdempotentIdChildPayload`) só tem campos `@JdempotentId`; o teste combo de AC #3 usa `IdempotentTestPayload`, que é flat (sem superclasse) — o caminho de leitura subjacente é código de produção inalterado e já provado pela Story 3.3, então é lacuna de cobertura/rastreabilidade, não suspeita de bug em runtime. → `patch`.
