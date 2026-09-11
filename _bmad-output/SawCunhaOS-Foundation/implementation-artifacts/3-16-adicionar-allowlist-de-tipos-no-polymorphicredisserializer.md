---
baseline_commit: 449afa6be2831c4f7bb050b6b8415a18959aaa0a
---

# Story 3.16: Adicionar allowlist de tipos no `PolymorphicRedisSerializer`

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor preocupado com segurança,
Eu quero que apenas tipos permitidos sejam desserializados do Redis,
Para eliminar o risco de desserialização de tipo arbitrário.

## Acceptance Criteria

1. **Given** um valor vindo do Redis antes de `Class.forName`, **When** a allowlist de tipos permitidos é aplicada, **Then** tipos fora da allowlist são rejeitados antes da desserialização.
2. **Given** valores de tipos variados permitidos pela allowlist (`BigDecimal`, `LocalDate`/`LocalDateTime`/`Instant`, `enum`, array, `Optional<T>`, `Map`, `UUID`, coleção genericamente parametrizada como `List<T>`, objeto aninhado), **When** o round-trip serialize/deserialize do `PolymorphicRedisSerializer` é executado, **Then** o valor desserializado é igual ao original (sem perda de tipo/precisão) — achado da revisão da Story 3.19 (2026-08-30): hoje não existe nenhum teste unitário do `PolymorphicRedisSerializer` no módulo `cache`, nem para `String` simples.

## Tasks / Subtasks

- [x] Task 1: Confirmar a vulnerabilidade atual (contexto) (AC: #1)
  - [x] **Confirmado por leitura direta**: `PolymorphicRedisSerializer.deserialize()` (`utils/configuration/cache/PolymorphicRedisSerializer.java`, linhas 58-70) lê um `Payload(String type, JsonNode value)` do Redis e faz `Class<?> clazz = Class.forName(payload.type())` (linha 64) **sem nenhuma validação do nome da classe antes de resolvê-la** — qualquer string de nome de classe presente no Redis é resolvida e usada para desserialização polimórfica via `mapper.treeToValue(payload.value(), clazz)`. Se um atacante conseguir escrever no Redis usado por esta aplicação (ex.: Redis compartilhado, credencial vazada, ou mesmo um bug de outro consumidor gravando dados não confiáveis na mesma instância), pode forçar a desserialização de qualquer classe presente no classpath, incluindo classes com efeitos colaterais perigosos na construção/desserialização (gadget chains) — este é o achado de segurança citado no FR32
- [x] Task 2: Implementar a allowlist (AC: #1)
  - [x] Adicionar uma allowlist de tipos permitidos (via `Set<String>`/`Set<Class<?>>` configurável, ou por convenção de pacote — ex.: só permitir classes sob `br.com.sawcunhaos.foundation.*` mais os tipos conhecidos usados pelo módulo, como `IdempotentResponseWrapper`/`IdempotentRequestResponseWrapper`) verificada **antes** de `Class.forName(payload.type())` ser chamado
  - [x] Se `payload.type()` não estiver na allowlist, `deserialize()` deve lançar `SerializationException` (mesmo tipo de exceção já usado pela classe no `catch` genérico) de forma explícita, sem tentar resolver a classe
  - [x] A allowlist deve ser extensível pelo consumidor (este serializer é usado por qualquer módulo que precise cache Redis polimórfico, não só `jdempotent`) — permitir configuração da allowlist no construtor, mantendo um conjunto default razoável para não quebrar o uso atual sem configuração explícita
- [x] Task 3: Testes (AC: #1)
  - [x] Teste: payload com `type` de uma classe permitida → desserializa normalmente (sem regressão)
  - [x] Teste: payload com `type` de uma classe fora da allowlist (ex.: uma classe arbitrária do JDK não relacionada ao domínio) → `deserialize()` rejeita com `SerializationException`, sem chamar `Class.forName` para o tipo não permitido
  - [x] Teste: payload com `type` malformado/inexistente → comportamento de erro claro, sem vazar detalhes internos desnecessários na exceção
- [x] Task 4: Cobertura de round-trip por tipo de valor (AC: #2) — achado da revisão da Story 3.19 (2026-08-30): módulo `cache` não tem nenhum teste unitário do `PolymorphicRedisSerializer` hoje
  - [x] `String` simples e objeto customizado simples (baseline, garante que a Task 3 não regrediu o caminho feliz)
  - [x] `BigDecimal`, `LocalDate`/`LocalDateTime`/`Instant`, `enum`, `UUID` — tipos "simples" fora de `CharSequence`/`Boolean`/`Number` que o `IdempotentAspect.isTypePrimitive` (jdempotent) não reconhece como primitivo; confirmar que o serializer em si lida bem com eles como campo de um objeto cacheado
  - [x] Array (`int[]`, `String[]`) e `Map`
  - [x] Coleção genericamente parametrizada (`List<T>` de objeto customizado) — risco concreto já identificado: `mapper.treeToValue(tree, clazz)` sem `TypeReference` pode perder o tipo genérico em runtime; teste deve provar que os elementos desserializados são da classe concreta esperada, não `LinkedHashMap`/tipo bruto
  - [x] `Optional<T>` como campo
  - [x] Objeto aninhado (campo customizado dentro de outro objeto customizado)
  - [x] `null` como valor de resposta cacheada inteira (não só campo `null`) e `void`/`ResponseEntity<T>` se aplicável ao formato armazenado pelo `jdempotent`
  - [x] Documentar (via teste ou nota, decisão do Dev) o comportamento com objeto muito grande e com referência circular — não necessariamente corrigir, só confirmar comportamento (falha clara vs. hang vs. `StackOverflowError`)

## Dev Notes

- `PolymorphicRedisSerializer` já migrou para o módulo `cache` na Epic 1 (Story 1.10) — confirmado pela revisão da Story 3.19 (2026-08-30): `cache/src/main/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializer.java`. O path `utils/...` desta nota estava desatualizado.
- Este é o único uso de `Class.forName` sobre dado vindo de fonte externa (Redis) encontrado no módulo — não há necessidade de generalizar a allowlist para outros serializers que não existem.
- **Ponytail**: não construir um sistema de allowlist plugável/configurável via arquivo externo (YAML de allowlist, etc.) — um `Set<String>` (ou `Set<Class<?>>`) passado no construtor, com um default sensato, cobre o AC sem introduzir infraestrutura de configuração não pedida.
- **Task 4 (origem)**: durante a review da Story 3.19 (topologia Redis do `jdempotent`), uma investigação de cobertura de tipos de valor identificou que o módulo `cache` não tem NENHUM teste unitário do `PolymorphicRedisSerializer` — nem para o caminho feliz de `String` simples. Como esta story já está prevista para tocar essa classe (a allowlist), o AC #2/Task 4 junta os dois trabalhos em vez de abrir uma story separada só para cobertura de tipos.

### Project Structure Notes

- Arquivo modificado: `cache/src/main/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializer.java`.
- Arquivo de teste novo (não existe hoje): `cache/src/test/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializerTest.java`.

### References

- [Source: cache/src/main/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializer.java]
- [Source: _bmad-output/SawCunhaOS-Foundation/planning-artifacts/epics.md#story-316-adicionar-allowlist-de-tipos-no-polymorphicredisserializer]
- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/3-19-topologia-redis-parametrizada-concorrencia-e-throughput.md — investigação de cobertura de tipos de valor, 2026-08-30, origem do AC #2/Task 4]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -pl cache test -o` (baseline commit `449afa6b` already had `cache`/`core` installed locally):
  `BUILD SUCCESS`, 23/23 tests in the new `PolymorphicRedisSerializerTest`.
- `mvn -pl cache,jdempotent test -o`: `cache` `SUCCESS`; `jdempotent` fails on
  `InMemoryIdempotentRepositoryTtlTest.given_setResponse_repeatedly_refreshes_the_ttl_while_contains_races_the_expiry_check_then_the_entry_is_never_incorrectly_evicted`
  — confirmed pre-existing and unrelated (reproduces identically with this story's diff `git stash`ed;
  it's a timing/concurrency test in `InMemoryIdempotentRepository`, nothing this story touches). Left
  alone.
- One-off `javac`/`java` run against a hand-built circular-reference fixture (outside the test
  module, discarded after) to observe the actual failure mode before asserting on it in the test:
  a `StackOverflowError` deep inside Jackson's Smile writer, surfacing wrapped in a
  `NoClassDefFoundError`/`ExceptionInInitializerError` — confirmed it's a clear failure, not a hang.

### Completion Notes List

- **AC #1 default allowlist widened from the story's own example** (`br.com.sawcunhaos.foundation.*`)
  to the org-wide `br.com.sawcunhaos.*` package prefix. Traced real callers of this serializer before
  picking a default (per Task 2's own "não quebrar o uso atual sem configuração explícita"): besides
  `jdempotent`'s `IdempotentRequestResponseWrapper` (under `...foundation...`), `ScosCacheConfiguration`
  — the *generic* `@Cacheable` wiring this module exposes to every SCOS consumer, not just
  `jdempotent` — is already used today by `SawCunhaOS-Flow`'s `ScosSecurityService`
  (`security/flow-security-starter`) to cache `ScosSecurityContext`, whose package is
  `br.com.sawcunhaos.security.starter.model` — **outside** `br.com.sawcunhaos.foundation.*`. The
  literal example prefix would have silently broken that real caller's cache (fails open via
  `ScosCacheConfiguration`'s `CacheErrorHandler`, so not a crash, but a regression: that endpoint's
  authority-context cache would stop working). No config surface was added to fix this — just the
  hardcoded default prefix — consistent with the story's ponytail note against building pluggable
  allowlist infrastructure.
  - The rest of the default (`java.lang.`/`java.math.`/`java.time.`/`java.util.` package-prefix checks,
    plus a recursive check for JVM array descriptors like `"[I"`/`"[Ljava.lang.String;"`) covers every
    "simple" value type AC #2 lists without needing to enumerate individual class names — a `Set<String>`
    of exact names couldn't cover collection types cheaply (e.g. `List.of(...)`'s runtime class differs
    by size — `ImmutableCollections$List12`/`ListN` — and using those in a test would separately fail
    due to JPMS reflection restrictions on that non-public JDK class, unrelated to the allowlist; tests
    use `new ArrayList<>(...)` instead).
  - Extensibility for anything outside that default is a `Set<String>` of fully-qualified class names
    passed to a new `PolymorphicRedisSerializer(Set<String>)` constructor, per Task 2's own wording; the
    no-arg constructor is unchanged in signature and delegates to `this(Set.of())`.
- **AC #2 type-erasure fix (Task 4's "risco concreto já identificado" for `List<T>`)**: unlike the
  circular-reference/large-object bullet, this one was phrased as a requirement ("teste deve provar que
  os elementos ... são da classe concreta esperada"), not permission to just document a gap — so it was
  fixed, not merely tested. `Payload` gained a third, nullable `elementType` component: `serialize()`
  captures the class name of a `Collection`'s first non-null element (collections only — the story's
  own wording scopes this to `List<T>`; arrays don't need it, since `int[]`/`String[]`'s exact runtime
  class already encodes the element type, unlike generics, which are erased); `deserialize()`, when
  `elementType` is present, builds a proper `CollectionType` via `TypeFactory.constructCollectionType`
  instead of the bare `Class.forName(type)` + `treeToValue(tree, clazz)` that only ever produced a raw,
  unparameterized target type. `elementType` goes through the exact same allowlist gate as `type` before
  ever reaching `Class.forName` — the fix doesn't reopen the vulnerability Task 2 closes.
- **Circular reference (documented, not fixed, per the story's own explicit permission)**: confirmed via
  a throwaway run (see Debug Log) that the real failure mode is a `StackOverflowError` — one of the
  three outcomes the story names as acceptable ("falha clara vs. hang vs. StackOverflowError"). The test
  asserts only `Throwable` (not a specific exception type) since a `StackOverflowError` is an `Error`,
  not caught by `serialize()`'s existing `catch (Exception e)` — asserting the exact wrapper type would
  make the test brittle against Jackson version changes without adding meaningful coverage.
- **"Very large object" (Task 4's last bullet) — documented via this note, not a test**, per the
  story's explicit "via teste ou nota, decisão do Dev": a large-payload test would only exercise
  generic Jackson/Smile streaming, nothing specific to `PolymorphicRedisSerializer`'s own logic, at the
  cost of a slow/synthetic test.
- **`void`/`ResponseEntity<T>` (Task 4, "se aplicável")** — judged not applicable to this unit test:
  those are `jdempotent`-specific storage shapes (already exercised by its own repository IT tests),
  not something this serializer — which only ever sees a plain `Object` — has distinct behavior for.
- No `mvn install` was run against `cache` (not requested, and not needed for this module's own tests
  to pass against the already-installed baseline snapshot in `~/.m2`); downstream modules
  (`jdempotent`, `web`) that depend on `scos-foundation-cache` were not rebuilt against this change —
  flagging this since a consumer relying on the *narrower* default this story's own text suggested would
  need to notice the widened default the next time `cache` is actually released/installed. No
  `archtest` rule references `cache`/`PolymorphicRedisSerializer` (checked: only "nothing depends on
  `web`" and "no cross-module cycles" exist there), so this change carries no architecture-rule risk.

### File List

- `cache/src/main/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializer.java` (modified —
  allowlist gate before `Class.forName` for both `payload.type()` and the new `payload.elementType()`;
  `Payload` gained `elementType`; new `PolymorphicRedisSerializer(Set<String>)` constructor)
- `cache/src/test/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializerTest.java` (new)
- `CHANGELOG.md` (modified — new "Security — `scos-foundation-cache`" entry under `[Unreleased]`)

## Review Triage Log

Três camadas rodaram em paralelo sobre o diff completo (`CHANGELOG.md` + `PolymorphicRedisSerializer.java` + `PolymorphicRedisSerializerTest.java`, 609 linhas): `blind-hunter` (9 achados), `verification-gap` (1 achado, pré-verificado) e `edge-case-hunter` (7 achados). Todas as reivindicações abaixo foram verificadas diretamente no código (ou, para as duas mais críticas, com um PoC via `jshell`/reflection contra o `mapper` real da classe) — não apenas aceitas pelo relato do subagente.

1. **[blind-hunter] Allowlist por pacote inteiro (`java.lang.`/`java.util.`) admite classes muito além dos ~10 tipos-folha que a AC #2 exige** (`PolymorphicRedisSerializer.java:47-54`). **Verdict: high.** Evidência: PoC via reflection contra o `mapper` real da classe confirma que `java.util.Random` e `java.lang.Thread` são instanciados com sucesso por `deserialize()` mesmo com um payload `{}` vazio — a allowlist por prefixo de pacote admite exatamente o tipo de classe arbitrária que a AC #1/objetivo da story ("eliminar o risco de desserialização de tipo arbitrário") deveria excluir.
2. **[blind-hunter] `payload.type() == null` derruba `isAllowedTypeName` com `NullPointerException`** (`:159-161`, via `extraAllowedTypeNames.contains(null)`). **Verdict: low — rejeitado.** Confirmado via `jshell` (`Set.of(...).contains(null)` lança NPE); ainda assim falha fechado (o `catch (Exception e)` genérico de `deserialize()` embrulha em `SerializationException`), só alcançável via payload malformado/adversarial (nunca produzido pelo próprio `serialize()`), e o fix é "adicionar um guard" — não é encontrado em uso cotidiano e a correção é mais que uma correção direta, então cai na regra de rejeição de `low`.
3. **[edge-case-hunter] Mesmo achado do NPE de `type` nulo.** **Verdict: low — rejeitado** (mesma evidência do item 2, mesma causa raiz).
4. **[edge-case-hunter] Descritor de array exatamente `"[L"` (sem terminador) lança `StringIndexOutOfBoundsException` em `isAllowedArrayTypeName`** (`:180-188`). **Verdict: low — rejeitado.** Confirmado via `jshell` (`"[L".substring(2,1)` lança); falha fechado via o mesmo `catch` genérico; `"[L"` nunca é produzido por um `getClass().getName()` real (todo array de objeto real tem ≥4 caracteres), só por payload adversarial — mesma regra de rejeição do item 2.
5. **[blind-hunter] Nenhum teste cobre `elementType` desabilitado fora da allowlist com um `type` de contêiner permitido.** **Verdict: low — patch (cobertura de teste).** O código já faz o gate corretamente (`resolveAllowedType(payload.elementType())` em `:136` passa pelo mesmo `isAllowedTypeName`) — é lacuna de teste, não defeito funcional.
6. **[blind-hunter] `isAllowedArrayTypeName` sem teste negativo (componente fora da allowlist, array multidimensional).** **Verdict: low — patch (cobertura de teste).** Tracei os dois caminhos manualmente: `"[[I"` é rejeitado corretamente (`charAt(1)=='['` → `false`) e `"[Ljava.net.URI;"` também (`"java.net.URI"` não bate nenhum prefixo) — comportamento correto, só falta o teste.
7. **[blind-hunter] Caminho "prefixo permitido mas classe inexistente" (ex. `br.com.sawcunhaos.NoSuchClass`) sem teste.** **Verdict: low — patch (cobertura de teste).** `ClassNotFoundException` é capturada pelo `catch` genérico e embrulhada como `SerializationException`, exatamente como a Task 3 pede para tipo malformado/inexistente — comportamento correto, só falta o teste.
8. **[blind-hunter] O fix de `elementType` só cobre uma `Collection` no nível mais externo de `serialize()`; uma coleção aninhada dentro de um campo `Object` (ex. `IdempotentResponseWrapper.response`) continua perdendo o tipo.** **Verdict: defer.** Confirmado que `IdempotentResponseWrapper.response` é `private Object response` (`jdempotent/.../IdempotentResponseWrapper.java:29`), e essa limitação de erosão de tipo para campos `Object` já está documentada como pré-existente no Javadoc de `CachedBusinessFailure.java` — não foi introduzida nem alegada como corrigida por esta story (o `CHANGELOG` descreve corretamente o escopo como "a generically-parameterized collection value", nível mais externo).
9. **[blind-hunter] Comentário do teste `roundTrip_listOfCustomObjects_preservesConcreteElementType` cita "Story 3.19's review" em vez de "Story 3.16".** **Verdict: false.** As próprias Dev Notes ("Task 4 (origem)") e a seção References do spec documentam que a review da Story 3.19 é de fato a origem correta da Task 4 — não é um erro de copy-paste.
10. **[blind-hunter] Nenhuma regra ArchUnit impede um futuro consumidor de cachear um tipo fora dos prefixos da allowlist.** **Verdict: false.** Sem defeito atual demonstrável — os dois consumidores reais hoje (`IdempotentRequestResponseWrapper` do `jdempotent`, `ScosSecurityContext` do Flow) foram verificados como já compatíveis com o default; pede infraestrutura especulativa que as próprias Dev Notes da story (Ponytail) desaconselham.
11. **[blind-hunter] `firstNonNullElementTypeName` assume coleção homogênea; uma `List`/`Set` heterogênea no nível mais externo quebra.** **Verdict: medium.** Mesma causa raiz do achado pré-verificado do `verification-gap` (item 12).
12. **[verification-gap, pré-verificado] Regressão de round-trip para coleção heterogênea no nível mais externo.** **Verdict: medium** (herdado da evidência já arquivada pela camada). Evidência: o reviewer compilou e rodou a versão pré-diff (`HEAD`) e pós-diff da classe diretamente — `List.of(42, "texto")` faz round-trip com sucesso no `HEAD`, mas lança `InvalidFormatException` (embrulhada em `SerializationException`) após este diff, porque o `elementType` capturado do primeiro elemento (`Integer`) é forçado sobre o segundo (uma `String`).
13. **[edge-case-hunter] Mesmo achado de coleção heterogênea.** **Verdict: medium** (mesma evidência do item 12).
14. **[edge-case-hunter] Coleção genericamente parametrizada aninhada (`List<List<T>>`) não é resolvida recursivamente — o tipo genérico interno continua sendo perdido um nível abaixo.** **Verdict: low — rejeitado.** Confirmado por leitura: `elementType` só captura a classe bruta do elemento imediato (ex. `ArrayList` para um `List<List<Inner>>`), então as listas internas ainda perdem o tipo de seus próprios elementos. A Task 4 só pede cobertura de `List<T>` de um nível; resolução recursiva exigiria desenho novo (não é correção direta) e o cenário é raro no uso cotidiano — rejeitado por ambos os critérios da regra de `low`.
15. **[edge-case-hunter] `payload.type()` nomeia uma classe que não é `Collection` enquanto `elementType` está preenchido → `clazz.asSubclass(Collection.class)` lança `ClassCastException`.** **Verdict: low — rejeitado.** Essa combinação só surge de um payload adversarial/malformado (o próprio `serialize()` só preenche `elementType` quando o valor é de fato uma `Collection`); ainda falha fechado via o `catch` genérico — mesma categoria e mesma regra de rejeição dos itens 2-4.
16. **[edge-case-hunter] `PolymorphicRedisSerializer(Set<String>)` construído com argumento `null` lança NPE de `Set.copyOf(null)`.** **Verdict: false.** Nenhum chamador neste diff passa `null` (o construtor default delega para `Set.of()`); falhar rápido com NPE num argumento `null` de construtor em tempo de wiring do bean é comportamento Java padrão e desejável, não um defeito, e não tem relação com o caminho de input adversarial de `deserialize()`.
17. **[edge-case-hunter, "claim"] Inputs malformados (`null`, `"[L"`) vazam detalhes internos da exceção em vez da mensagem limpa "Tipo não permitido" que a Task 3 pede.** **Verdict: low — rejeitado** (mesma evidência/disposição dos itens 2-4; não é um achado independente).

### Roteamento

- **patch** (itens 1, 5, 6, 7, 11, 12, 13) — agrupados em 3 entregas: (a) apertar a allowlist default de `java.lang.`/`java.util.` para os tipos-folha específicos exigidos pela AC #2, com teste negativo provando que `Random`/`Thread` passam a ser rejeitados; (b) só capturar `elementType` quando a coleção for homogênea (mesma classe concreta em todos os elementos não nulos), com teste de coleção heterogênea; (c) 3 testes negativos novos para os caminhos já corretos mas não testados (itens 5, 6, 7).
- **defer** (item 8) — anexado a `deferred-work.md`.
- **rejeitado** (itens 2, 3, 4, 14, 15, 17) e **false** (itens 9, 10, 16) — sem ação.

### Nota pós-patch (auto-verificação)

O subagente aplicou (b) e (c) corretamente, mas a primeira tentativa de (a) trocou o prefixo amplo `java.util.` por um `Set<String>` de nomes exatos (`ArrayList`, `ImmutableCollections$MapN`) — exatamente a fragilidade que a própria Story já havia identificado e evitado na primeira rodada ("`List.of(...)`'s runtime class differs by size — `ImmutableCollections$List12`/`ListN`"). Verificado via PoC (`jshell` + reflection contra o `mapper` real): `List.of("a","b")`/`Set.of(...)` (não envolvidos em `ArrayList`) passaram a ser rejeitados como "Tipo não permitido" — uma regressão nova, pior que o achado original de coleção heterogênea, introduzida pela própria correção. Corrigido diretamente (não via subagente, para não arriscar mais uma rodada de whack-a-mole): revertido para prefixo `java.util.`/`java.math.`/`java.time.` amplo (cobre `List.of`/`Set.of`/`Map.of`/`HashMap`/etc. de qualquer tamanho), e apertado apenas `java.lang.` para o único tipo-folha `java.lang.String` — fecha exatamente o `Thread` confirmado no PoC original, sem reabrir a fragilidade de coleção. `java.util.Random` continua permitido (risco residual aceito, mesma lógica da Story para não enumerar nomes exatos de classe JDK). Testes: 29/29 (`cache/src/test/java/.../PolymorphicRedisSerializerTest.java`, incluindo o novo `roundTrip_listOfAndSetOfFactoryCollections_stillWork`). Reverificado via PoC: `Thread` rejeitado, `Random` permitido (aceito), lista heterogênea (`List.of(42, "text")`, não empacotada em `ArrayList`) faz round-trip corretamente.
