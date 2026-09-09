---
baseline_commit: 65589ff18aef15482850207342390d6b24206fd1
---

# Story 3.13: Suportar header `Idempotency-Key` como fonte de chave

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor da API,
Eu quero enviar minha própria chave de idempotência via header,
Para controlar a chave sem depender só dos campos do corpo.

## Acceptance Criteria

1. **Given** uma requisição HTTP com o header `Idempotency-Key`, **When** `@JdempotentResource(keySource=HEADER_THEN_FIELDS, headerName="Idempotency-Key", onMismatch=CONFLICT)` está configurado, **Then** a precedência é header → campos anotados → hash, e `X-Request-ID` nunca é reutilizado para esse fim.
2. **And** para contexto de mensageria (sem contexto web), o resolver de chave devolve `null` de forma limpa, nunca lança exceção.

## Tasks / Subtasks

- [x] Task 1: Confirmar o estado atual (contexto) (AC: #1)
  - [x] **Reconfirmado por leitura direta (estado mudou desde a redação do AC)**: `JdempotentResource` não mora mais em `utils/annotation/jdempotent/` — a Story 1.5 já o moveu para `jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/JdempotentResource.java` (o pacote `utils.annotation.jdempotent` referenciado pelo AC não existe mais no reactor atual). Antes desta story, a anotação só tinha `cachePrefix()`, `ttl()`, `ttlTimeUnit()`, `onBusinessException()` (Story 3.8) — **nenhum atributo `keySource`/`headerName`/`onMismatch` existia**. A composição de chave era 100% via campos anotados + hash (`IdempotencyKeyResolver`/`DefaultKeyGenerator`, Story 3.12), sem nenhuma leitura de header HTTP em lugar nenhum do módulo `jdempotent`.
- [x] Task 2: Adicionar os novos atributos a `@JdempotentResource` (AC: #1)
  - [x] Criado o enum `KeySource` (`FIELDS_ONLY` como default preservando comportamento atual, `HEADER_THEN_FIELDS`) em `jdempotent-api`
  - [x] Adicionados `KeySource keySource() default KeySource.FIELDS_ONLY`, `String headerName() default ""`, e `IdempotentKeyMismatchPolicy onMismatch() default IdempotentKeyMismatchPolicy.CONFLICT` (novo enum, 1 valor) à anotação
- [x] Task 3: Implementar a leitura do header no `IdempotencyKeyResolver` (Story 3.12) (AC: #1)
  - [x] Novo overload `resolve(IdempotentRequestWrapper, String, KeySource, String)`: quando `keySource == HEADER_THEN_FIELDS`, lê o header nomeado por `headerName` do contexto HTTP atual via `RequestContextHolder`/`ServletRequestAttributes`/`HttpServletRequest` (disponível quando há contexto web); `jdempotent/pom.xml` ganhou `spring-web`+`jakarta.servlet-api` como dependências `optional=true` (compile-time only, mesmo padrão de `spring-aop`/`spring-aspects`) para viabilizar isso
  - [x] Precedência exigida pelo AC — **header → campos anotados → hash**: quando o header está presente (não branco), seu valor vira a fonte da chave, envolvido no mesmo `IdempotentRequestWrapper`/`KeyGenerator.generateIdempotentKey` já usado para campos (reaproveita o hash existente em vez de inventar um segundo formato de chave); quando ausente, cai para exatamente o comportamento de 2 argumentos já existente (campos anotados → hash, Story 3.12, sem nenhuma mudança)
  - [x] **Nunca reutilizar `X-Request-ID`**: confirmado por leitura de todo o diff desta story — só o header nomeado pelo parâmetro `headerName` explícito é lido em `IdempotencyKeyResolver#readHeader`; nenhuma string literal `"X-Request-ID"` aparece em nenhum arquivo de produção tocado por esta story. Coberto também por teste dedicado (Task 5).
- [x] Task 4: Resolver de chave limpo em contexto de mensageria (AC: #2)
  - [x] `IdempotencyKeyResolver#readHeader` usa `if (!(attributes instanceof ServletRequestAttributes ...)) return null;` — quando `RequestContextHolder.getRequestAttributes()` devolve `null` (sem contexto web) ou um `RequestAttributes` de outro tipo, a leitura do header retorna `null` de forma limpa, sem `NullPointerException`/`ClassCastException`, e o `resolve(...)` cai para o próximo passo da precedência (campos anotados) exatamente como o caminho "header ausente" — comportamento coberto por teste dedicado (Task 5). Nota de escopo: esta story não introduziu um entrypoint de mensageria separado, não-AOP — o método anotado continua passando pelo `IdempotentAspect`/AOP de sempre; só o *contexto de requisição HTTP* é que pode estar ausente nesse cenário (ex.: um listener de mensageria invocando diretamente um método `@JdempotentResource`).
- [x] Task 5: Testes (AC: #1, #2)
  - [x] Teste HTTP: header `Idempotency-Key` presente → chave derivada do header, não dos campos (nível de resolver: `IdempotencyKeyResolverHeaderSourceTest#should_derive_the_key_from_the_header_when_present_regardless_of_the_payload_fields`; nível de wiring end-to-end via AOP real: `IdempotentAspectTest#given_idempotency_key_header_present_when_trigger_aspect_then_the_stored_key_is_header_derived`)
  - [x] Teste HTTP: sem o header → cai para composição por campos anotados (`IdempotencyKeyResolverHeaderSourceTest#should_fall_back_to_annotated_fields_when_header_is_absent`)
  - [x] Teste de contexto não-web: resolver não lança exceção e cai para campos anotados (`IdempotencyKeyResolverHeaderSourceTest#should_fall_back_to_annotated_fields_without_throwing_when_there_is_no_web_request_context`)
  - [x] Teste confirmando que `X-Request-ID` nunca é usado como fonte da chave (`IdempotencyKeyResolverHeaderSourceTest#should_never_use_x_request_id_as_the_idempotency_key_source`)

## Dev Notes

- **Depende diretamente da Story 3.12** (`IdempotencyKeyResolver` como ponto único de composição) — implementar esta story depois, reutilizando o resolver já extraído, não criando um caminho de resolução de header separado e paralelo.
- `onMismatch=CONFLICT` sugere uma política de comportamento quando o header e os campos anotados discordam entre si (ex.: cliente reenvia com o mesmo header mas payload diferente) — esta semântica se sobrepõe conceitualmente com a Story 3.6 (colisão de payload); ao implementar, decidir explicitamente se `onMismatch` desta story reusa o mecanismo de `422 PAYLOAD_MISMATCH` da 3.6 ou é um caminho de erro distinto, e documentar a decisão nas Completion Notes — não implicitamente assumir que são a mesma coisa sem verificar.
- **Ponytail**: não adicionar suporte a múltiplos headers alternativos configuráveis (ex.: lista de nomes de header a tentar em ordem) — o AC pede um único `headerName` string; suporte a múltiplos seria flexibilidade não pedida.

### Project Structure Notes

- Arquivo modificado: `utils/src/main/java/br/com/sawcunhaos/foundation/utils/annotation/jdempotent/JdempotentResource.java` (novos atributos).
- Arquivo novo: enum `KeySource` (mesmo pacote de `JdempotentResource`).
- Arquivo modificado: `IdempotencyKeyResolver` (Story 3.12).

### References

- [Source: utils/src/main/java/br/com/sawcunhaos/foundation/utils/annotation/jdempotent/JdempotentResource.java]
- [Source: _bmad-output/implementation-artifacts/3-12-introduzir-idempotencykeyresolver-com-composição-de-chave-de.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-313-suportar-header-idempotency-key-como-fonte-de-chave]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -o -pl jdempotent-api,jdempotent -am compile`: `BUILD SUCCESS`.
- `mvn -o -pl jdempotent-api,jdempotent -am test`: `BUILD SUCCESS`, 101 tests / 0 failures / 0 errors, including `jdempotent-api.ArchitectureTest` (2, unaffected by the 2 new enums — still "annotation or enum only" / "no runtime dependency beyond JDK"), `IdempotencyKeyResolverTest` (3, Story 3.12, unchanged/still green), `IdempotencyKeyResolverHeaderSourceTest` (4, new), `IdempotentAspectTest` (12 = 11 existing + 1 new). IT tests (`*ITTest`, Testcontainers/Docker) not run, same unit-only scope as previous stories in this sandbox.
- `mvn -o -pl archtest -am test`: `BUILD SUCCESS`, `ArchitectureTest` (2/2) — confirms adding `spring-web`/`jakarta.servlet-api` (external libraries) as `optional=true` dependencies of `jdempotent/pom.xml` does not violate `nothingDependsOnWeb` (that rule only forbids importing the internal `br.com.sawcunhaos.foundation.web` module) nor `noCyclesBetweenModules`.
- **Após a revisão de código** (blind hunter + edge-case hunter + verification-gap): `mvn -o -pl jdempotent-api,jdempotent -am test` → `BUILD SUCCESS`, 105 testes / 0 falhas / 0 erros (101 anteriores + 4 novos de `IdempotencyKeyResolverHeaderSourceTest` para os achados 1-4; nenhum teste novo de arquivo separado para os achados 5-8, que são refactor/doc). `mvn -o -pl archtest -am test` → `BUILD SUCCESS`, `ArchitectureTest` 2/2, reconfirmado após as mudanças.

### Completion Notes List

- **Task 1 (state re-check)**: the story's own Task 1 bullet and the "Project Structure Notes" pointed at `utils/src/main/java/.../annotation/jdempotent/JdempotentResource.java`, a path that no longer exists — Story 1.5 (cited by Story 3.12's own Dev Notes) already moved every `@Jdempotent*` annotation to `jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/`. Implemented against the real, current location, per Task 1's own instruction to confirm the current state before implementing (same adjustment Story 3.12 already made for the same reason).
- **Task 2 (new annotation attributes)**: `KeySource` (`FIELDS_ONLY`/`HEADER_THEN_FIELDS`) and `IdempotentKeyMismatchPolicy` (single value `CONFLICT`) added as new enums in `jdempotent-api` (package-private-free, public, zero dependency beyond JDK — verified by the module's own `ArchitectureTest`). `@JdempotentResource` gains `keySource()`, `headerName()`, `onMismatch()`, all defaulted so every existing usage compiles and behaves unchanged (`FIELDS_ONLY` reproduces the pre-story `IdempotencyKeyResolver.resolve(wrapper, listenerName)` path byte-for-byte — verified by keeping that 2-arg overload untouched and having the new 4-arg overload delegate to it via `KeySource.FIELDS_ONLY`/`null` when called with `FIELDS_ONLY`).
- **Task 3 (header precedence)**: `IdempotencyKeyResolver` gained a 4-arg `resolve(IdempotentRequestWrapper, String, KeySource, String)` overload (the existing 2-arg one now delegates to it, unchanged behavior). When the header is present, its value is wrapped in a plain `IdempotentRequestWrapper(headerValue)` and pushed through the *same* `KeyGenerator.generateIdempotentKey(...)` call the fields path already uses — deliberately reusing the existing SHA-256 hash+namespace+listener-prefix mechanism instead of inventing a second key format for header-sourced keys, per Task 3's own framing ("hash continues being the underlying fallback mechanism"). `jdempotent/pom.xml` needed 2 new `optional=true` dependencies (`spring-web`, `jakarta.servlet-api`) to compile `RequestContextHolder`/`ServletRequestAttributes`/`HttpServletRequest` — neither was a main-code (only test-scope) dependency of this module before; verified this does not cross the AD-1/ArchUnit module boundary (that rule is about the internal `br.com.sawcunhaos.foundation.web` module, not third-party `org.springframework:spring-web`), confirmed by running `archtest` after the change.
- **Task 4 (messaging-safe null)**: `readHeader()` treats any `RequestAttributes` that isn't a `ServletRequestAttributes` (including `null`, which is exactly what `RequestContextHolder.getRequestAttributes()` returns outside a servlet request) as "no header available" and returns `null` — no exception path exists in this method. Scope note: this story does not add a separate, non-AOP messaging entrypoint — a `@JdempotentResource`-annotated method is still advised by `IdempotentAspect`/AOP regardless of caller; what can be missing in a messaging scenario is only the *HTTP request context* that `RequestContextHolder` would otherwise expose. `deferred-work.md`'s existing Story 3.12 entry (about `IdempotencyKeyResolver()`'s no-arg constructor silently defaulting to no namespace, flagged there as "Story 3.13's decision to make") remains open — this story never constructs a bare `IdempotencyKeyResolver()` in production code (only `IdempotentAspect`'s existing, namespaced instance field is used), so a safe way to obtain a namespaced resolver *outside* `IdempotentAspect` is still not needed/provided; left as-is since no AC/Task of 3.13 asks for a non-AOP entrypoint.
- **`onMismatch` scope decision (explicitly requested by Dev Notes, not to be assumed silently)**: `onMismatch=CONFLICT` is, for this story, **declarative only** — no code branches on `JdempotentResource#onMismatch()`'s value. A header key reused with a different payload is already caught today by the pre-existing, key-source-agnostic Story 3.6 mismatch check (`idempotentRepository.tryAcquire(key, payloadHash, ttl)` in `IdempotentAspect#execute()`), which throws `IdempotentPayloadMismatchException` regardless of how the key was derived — proven by `IdempotentAspectTest#given_idempotency_key_header_present_when_trigger_aspect_then_the_stored_key_is_header_derived` (same header, two different bodies, second call throws that exception). Decision: **`CONFLICT` does not reuse the `PAYLOAD_MISMATCH` naming/severity on purpose** — a reused `Idempotency-Key` header colliding with a different body conventionally maps to `409 Conflict` in APIs that implement this header pattern (e.g. Stripe), distinct from Story 3.6's generic `422`. Implementing that distinct exception/HTTP-status mapping is deferred to a future story (registered in `deferred-work.md`) since no AC or Task of Story 3.13 requires a different exception type — only that the attribute exist and the decision be documented, which is what this note and `IdempotentKeyMismatchPolicy`'s Javadoc do.
- **Tests (Task 5)**: 4 new resolver-level tests in `IdempotencyKeyResolverHeaderSourceTest` (new file, same pattern as Story 3.12's `IdempotencyKeyResolverTest` — direct resolver invocation, no AOP) simulate an HTTP request via `RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(new MockHttpServletRequest()))`, a standard Spring test technique, covering exactly Task 5's 4 scenarios. Plus 1 new AOP-level wiring test in `IdempotentAspectTest` (new `@JdempotentResource(keySource=HEADER_THEN_FIELDS, headerName="Idempotency-Key")` test method added to `TestIdempotentResource`) proving `IdempotentAspect.execute()` actually threads the 2 new attributes through end-to-end, using the "same header, different body collides on the same key" technique instead of hand-computing the expected hash.

### Correções da revisão de código (achados `patch`, todos aplicados)

Os 8 achados classificados `patch` por uma revisão multi-camada (blind hunter, edge-case hunter, verification-gap) sobre o diff desta story foram corrigidos nesta mesma sessão, sem necessidade de decisão humana adicional.

1. **[Severidade alta] Colisão de chave entre endpoints diferentes**: `IdempotencyKeyResolver.resolve(..., KeySource, String)` agora chama `requireUsableHeaderConfiguration(listenerName, headerName)` antes de ler o header — lança `IllegalStateException` fail-fast quando `keySource == HEADER_THEN_FIELDS` e `cachePrefix()`/`listenerName` está em branco (sem ele, campos anotados param de compor a chave e dois métodos não relacionados com `HEADER_THEN_FIELDS` e prefixo default colidiriam no mesmo header). Coberto por `IdempotencyKeyResolverHeaderSourceTest#should_throw_when_key_source_is_header_then_fields_but_cache_prefix_is_blank`.
2. **[Severidade média] `headerName()` em branco cai silenciosamente para campos**: mesma `requireUsableHeaderConfiguration` também lança `IllegalStateException` quando `headerName()` está em branco/default sob `HEADER_THEN_FIELDS` — evita mascarar o erro comum de esquecer de configurar o nome do header. Coberto por `IdempotencyKeyResolverHeaderSourceTest#should_throw_when_key_source_is_header_then_fields_but_header_name_is_blank`.
3. **[Severidade baixa-média] Header value não normalizado**: `readHeader()` agora aplica `StringUtils.trim(...)` ao valor do header antes de usá-lo como fonte da chave — `" abc123"` e `"abc123"` agora produzem a mesma chave. Coberto por `IdempotencyKeyResolverHeaderSourceTest#should_trim_the_header_value_before_using_it_as_the_key_source`.
4. **[Severidade média] `getHeader` pode lançar `IllegalStateException` em request reciclada**: a leitura do header (`servletRequestAttributes.getRequest().getHeader(...)`) agora está dentro de um `try/catch (IllegalStateException e) { return null; }`, tratado exatamente como "sem contexto web" (AC #2 — nunca lança exceção). Coberto por `IdempotencyKeyResolverHeaderSourceTest#should_fall_back_to_annotated_fields_without_throwing_when_getHeader_itself_throws` (usa um `HttpServletRequest` mockado via Mockito, já dependência de teste do módulo, cujo `getHeader` lança a exceção).
5. **[Severidade baixa] Refactor incompleto em `IdempotentAspect.execute()`**: as 3 chamadas restantes de `.getMethod().getAnnotation(JdempotentResource.class)` (`ttl()`, `ttlTimeUnit()`, `onBusinessException()`) agora reutilizam a variável `resourceAnnotation` já extraída, em vez de repetir a busca reflexiva. Efeito colateral esperado e corrigido: 4 testes pré-existentes em `IdempotentAspectUTTest` verificavam a contagem exata de chamadas a `pjp.getSignature()`/`signature.getMethod()` (`times(4)`/`times(5)` e `times(3)`/`times(4)`) — esses números caíram para `times(2)`/`times(1)` de forma consistente (1 chamada em `generateLogPrefixForIncomingEvent` + 1 na busca única de `resourceAnnotation`, sempre, independente do cenário), e as 4 asserções foram atualizadas para refletir o novo comportamento, correto e mais eficiente, não um bug.
6. **[Severidade baixa-média] `jdempotent-api/README.md` desatualizado**: removida a "Nota de evolução" que prometia `keySource`/`headerName`/`onMismatch` "numa story futura" (esta própria story já os adiciona); tabela "Conteúdo" ganhou a descrição atualizada de `@JdempotentResource` e 2 linhas novas para `KeySource`/`IdempotentKeyMismatchPolicy`.
7. **[Severidade baixa] CHANGELOG não mencionava as 2 novas dependências opcionais**: adicionada uma frase ao bullet já existente de `Idempotency-Key header as a key source (Story 3.13)` mencionando `spring-web`/`jakarta.servlet-api` como `optional=true`.
8. **[Severidade baixa] Javadoc não deixava explícito que o payload hash do mismatch check (Story 3.6) é sempre derivado dos campos**: adicionada uma nota na Javadoc da classe `IdempotencyKeyResolver` explicando que `IdempotentAspect#execute()` computa `payloadHash` a partir do `requestObject` original (campos), nunca do header, independente de `keySource`.

Reverificado com `mvn -o -pl jdempotent-api,jdempotent -am test`: `BUILD SUCCESS`, 105 testes, 0 falhas/erros; `mvn -o -pl archtest -am test`: `BUILD SUCCESS`, 2/2.

### File List

- `jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/KeySource.java` (novo)
- `jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/IdempotentKeyMismatchPolicy.java` (novo)
- `jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/JdempotentResource.java` (modificado — `keySource()`, `headerName()`, `onMismatch()`)
- `jdempotent-api/README.md` (modificado — revisão: nota de evolução obsoleta removida, tabela "Conteúdo" atualizada)
- `jdempotent/pom.xml` (modificado — `spring-web`/`jakarta.servlet-api`, `optional=true`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolver.java` (modificado — novo overload `resolve(..., KeySource, String)` + `readHeader()`; revisão: `requireUsableHeaderConfiguration()` fail-fast, trim do header, try/catch `IllegalStateException`, Javadoc sobre payload hash do mismatch check)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modificado — `execute()` repassa `keySource()`/`headerName()` ao resolver; revisão: `ttl()`/`ttlTimeUnit()`/`onBusinessException()` também reusam `resourceAnnotation`)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/utils/TestIdempotentResource.java` (modificado — novo método `idempotentMethodWithHeaderKeySource`)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolverHeaderSourceTest.java` (novo; revisão: +4 testes para os achados 1-4)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTest.java` (modificado — +1 teste de wiring end-to-end)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java` (modificado — revisão: 4 asserções de contagem de `getSignature()`/`getMethod()` atualizadas de `times(4)`/`times(5)`/`times(3)` para `times(2)`/`times(1)`, refletindo o refactor do achado 5)
- `CHANGELOG.md` (modificado — bullet `Added` para `scos-foundation-jdempotent`; revisão: +menção às 2 dependências opcionais novas)

## Suggested Review Order

**Precedência header → campos → hash**

- Ponto de entrada: overload que decide a fonte da chave conforme `keySource`, reaproveitando o hash já usado para campos.
  [`IdempotencyKeyResolver.java:106`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolver.java#L106)

- Revisão: guarda fail-fast contra colisão de chave entre endpoints quando `cachePrefix`/`headerName` ficam em branco sob `HEADER_THEN_FIELDS`.
  [`IdempotencyKeyResolver.java:131`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolver.java#L131)

- Leitura do header: `trim` do valor e fallback limpo (sem exceção) quando não há contexto web ou a request já foi reciclada.
  [`IdempotencyKeyResolver.java:160`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolver.java#L160)

**Wiring no aspecto AOP**

- `execute()` repassa `keySource()`/`headerName()` da anotação ao resolver, reaproveitando a mesma reflexão para `ttl`/`onBusinessException`.
  [`IdempotentAspect.java:190`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L190)

**Novos atributos da anotação**

- `@JdempotentResource` ganha `keySource`/`headerName`/`onMismatch`, todos com default que preserva o comportamento anterior.
  [`JdempotentResource.java:66`](../../jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/JdempotentResource.java#L66)

- Novo enum: declara a precedência header → campos, nunca lança exceção fora de contexto web.
  [`KeySource.java:18`](../../jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/KeySource.java#L18)

- Novo enum, hoje só declarativo — a colisão de payload já é pega pelo mecanismo existente da Story 3.6.
  [`IdempotentKeyMismatchPolicy.java:40`](../../jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/IdempotentKeyMismatchPolicy.java#L40)

**Dependências**

- `spring-web`/`jakarta.servlet-api` como `optional=true`, só para compilar `RequestContextHolder`/`HttpServletRequest`.
  [`pom.xml:106`](../../jdempotent/pom.xml#L106)

**Testes**

- Prova de wiring end-to-end via AOP real: mesmo header, payloads diferentes colidem no mesmo `IdempotentPayloadMismatchException`.
  [`IdempotentAspectTest.java:285`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTest.java#L285)

- Os 8 cenários de precedência, guarda de configuração, trim e fallback limpo, testados no nível do resolver.
  [`IdempotencyKeyResolverHeaderSourceTest.java:58`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolverHeaderSourceTest.java#L58)

- Fixture do método anotado com `HEADER_THEN_FIELDS`, usado pelo teste de wiring.
  [`TestIdempotentResource.java:77`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/utils/TestIdempotentResource.java#L77)

**Documentação**

- Entrada explicando o novo mecanismo e as 2 dependências opcionais novas.
  [`CHANGELOG.md:106`](../../CHANGELOG.md#L106)

- Nota de evolução corrigida — os atributos já existem, não são mais "story futura".
  [`README.md:17`](../../jdempotent-api/README.md#L17)
- `_bmad-output/implementation-artifacts/deferred-work.md` (modificado — entrada documentando a decisão de escopo do `onMismatch`)
