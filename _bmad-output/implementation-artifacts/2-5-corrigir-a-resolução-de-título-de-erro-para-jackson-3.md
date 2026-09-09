# Story 2.5: Corrigir a resolução de título de erro para Jackson 3

Status: done

<!-- baseline_commit: e39265a91948864b30444b45afea7b75fbac811e -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor da API recebendo erros de deserialização,
Eu quero uma mensagem de erro correta mesmo com Jackson 3,
Para não receber um título genérico ou quebrado.

## Acceptance Criteria

1. **Given** um teste que confirma se o regex atual de `resolveTitle` ainda casa com as mensagens do Jackson 3, **When** o teste falha (regex desatualizado) ou passa, **Then** `resolveTitle` passa a navegar a causa (`InvalidFormatException`/`MismatchedInputException.getPath()`) em vez de usar regex.

## Tasks / Subtasks

- [x] Task 0 — resolver a divergência de nome antes de tocar em código (bloqueante) (AC: #1)
  - [x] **ATENÇÃO — discrepância confirmada entre o epics.md e o código real**: o epics.md descreve esta story como uma correção em um método chamado `resolveTitle` que usaria regex. No código atual, `ExceptionsHandler.resolveTitle` (linha 303-309) **não usa regex** — é só um `try/catch` em volta de `localeService.getMessage(title)` (esse é o alvo da **Story 2.6**, FR34, não desta). O regex baseado em `Pattern`/`Matcher` que de fato existe no arquivo está em `handleHttpMessageNotReadable` (linhas 85-98), tratando exceções de deserialização (`ex.getMessage()` de `HttpMessageNotReadableException`) — é esse método, não `resolveTitle`, que corresponde à intenção da AC (extrair campo/tipo de uma mensagem de erro de deserialização) e ao FR14 do PRD
  - [x] Tratar esta story como sendo sobre `handleHttpMessageNotReadable`, não sobre o método literalmente chamado `resolveTitle` — se essa leitura estiver errada, escalar para quem mantém o épico antes de implementar, não decidir ad-hoc
- [x] Task 1: Escrever o teste de regressão contra o regex atual (AC: #1)
  - [x] Capturar uma mensagem real de `InvalidFormatException`/`MismatchedInputException` lançada pelo Jackson 3 (`tools.jackson.*`, confirmar a mensagem exata gerada por essa versão, não assumir o formato do Jackson 2) ao desserializar um enum inválido, e confirmar se os patterns atuais (`patternField = "(\\[\\\"[\\w,\\s]+\\\"\\])"`, `patternType = "(\\[[\\w,\\s]+\\])"`, linhas 86-87) ainda casam
- [x] Task 2: Substituir regex por navegação de causa (AC: #1)
  - [x] Reescrever `handleHttpMessageNotReadable` para extrair `field`/`typesEnum` navegando `ex.getCause()` quando for `InvalidFormatException`/`MismatchedInputException` (Jackson 3, pacote `tools.jackson.databind.exc`, não `com.fasterxml.jackson.databind.exc` — Jackson 2), usando `getPath()` (lista de `Reference`, cada uma com ~~`getFieldName()`~~ **correção pós-revisão**: o método real em Jackson 3 é `getPropertyName()` — `Reference` não tem `getFieldName()`, que é o nome legado do Jackson 2; confirmado lendo `tools.jackson.core.JacksonException.Reference` diretamente. A implementação já usava `getPropertyName()` corretamente; só este texto do Task estava desatualizado) e `getTargetType()`, em vez de fazer regex sobre `ex.getMessage()`
  - [x] Manter o fallback atual (`field`/`typesEnum` vazios) para o caso em que a causa não é nenhum desses dois tipos, preservando o comportamento hoje existente para outras causas de `HttpMessageNotReadableException`

## Dev Notes

- **Isto não é uma correção pontual, é uma investigação de nomes primeiro**: o epics.md e o código real discordam sobre qual método faz o quê. Não implementar às cegas contra o nome do método — implementar contra o comportamento descrito (regex sobre mensagem de erro de deserialização Jackson).
- O projeto já usa Jackson 3 (`tools.jackson.*`, confirmado no `ScosJacksonConfig` e no ADD-6 do epics.md — `jackson-bom:3.2.1`), então os tipos de exceção corretos vêm de `tools.jackson.databind.exc.InvalidFormatException`/`MismatchedInputException`, não do pacote legado `com.fasterxml.jackson`.
- Esta story só toca `handleHttpMessageNotReadable`. `resolveTitle` (o método com esse nome literal) é tratado separadamente na Story 2.6 — não misturar as duas correções no mesmo commit.

### Project Structure Notes

- Arquivo modificado: `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` (método `handleHttpMessageNotReadable`, linhas 76-106).
- Novo teste em `exception/src/test/java/br/com/sawcunhaos/foundation/exception/`.

### References

- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-25-corrigir-a-resolução-de-título-de-erro-para-jackson-3]
- [Source: _bmad-output/planning-artifacts/epics.md] (ADD-6 — versões fixadas, Jackson `jackson-bom:3.2.1`)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -o -pl exception -am -DskipITs test` → BUILD SUCCESS. Reactor: `scos-foundation` (0.9s), `scos-foundation-validation-api` (6.2s), `scos-foundation-core` (7.3s), `scos-foundation-exception` (13.8s). Exception module: `Tests run: 33, Failures: 0, Errors: 0, Skipped: 0` (27 pre-existing after Story 2.4 + 6 new in `ExceptionsHandlerJackson3DeserializationTest`). **Correção pós-revisão**: esta nota originalmente afirmava "39... (33 pré-existentes + 6 novos)" — contagem errada; o baseline pré-story era 27 (confirmado por `mvn -o -pl exception -am test` da Story 2.4), então 27+6=33, não 39.
- Standalone probe (outside Maven, `javac`/`java` against `jackson-core-3.2.2.jar` + `jackson-databind-3.2.2.jar` + `jackson-annotations-2.22.jar` from the local `.m2`) used during investigation to capture the *real* Jackson 3 exception message/`getPath()`/`getTargetType()` output for an invalid-enum deserialization, both top-level and nested, before writing any test — confirms the message text and `Reference`/`Class` API surface documented below. Scratch files were deleted after use; not part of the diff.
- **Pós-revisão de 3 camadas**: mais uma rodada do mesmo probe standalone (mesmos jars), confirmando `getPath()`/`getTargetType()` para 3 cenários adicionais cobrados pelos revisores: elemento inválido de array (`Color[]` com `"PURPLE"` no índice 1) → `path.size=1`, `propertyName=null`, `index=1`, `targetType=Color` (enum); enum "nu" no nível raiz (`"PURPLE"` direto, sem wrapper) → `path.size=0`, `targetType=Color` (enum); mismatch não-enum (`{"n":"notanumber"}` num record com `int n`) → `path.size=1`, `propertyName="n"`, `targetType=int` (não-enum). `ExceptionsHandlerJackson3DeserializationTest` estendida de 6 para 9 casos para cobrir os 3. `mvn -o -pl exception -am -DskipITs test` → `Tests run: 36, Failures: 0, Errors: 0, Skipped: 0`, `BUILD SUCCESS`.

### Completion Notes List

- Confirmed via Task 0's own conclusion (already resolved in this story file) that the target is `ExceptionsHandler.handleHttpMessageNotReadable`, not `resolveTitle`. Did not touch `resolveTitle` (lines 350-356), which stays for Story 2.6.
- Task 1 (baseline): captured Jackson 3's real message for `InvalidFormatException` on an invalid enum value, e.g. for a top-level field: `Cannot deserialize value of type \`Color\` from String "PURPLE": not one of the values accepted for Enum class: [RED, BLUE, GREEN] ... (through reference chain: Leaf["color"])`. The old regex (`patternField`/`patternType`) **still matches** this simple, top-level case (`field="color"`, `typesEnum="[RED, BLUE, GREEN]"`) — Jackson 3 kept a textually similar message shape. However, for a **nested** field (e.g. `Outer.middle.leaf.color`), `Matcher.find()` on `patternField` returns the FIRST bracketed segment in the reference chain (`["middle"]`, the outermost one), not the leaf field that actually failed (`["color"]`) — a real bug, reproduced in `oldRegexGrabsWrongFieldForNestedPath`. Also noted: the enum-values list embedded in the message (`[RED, BLUE, GREEN]`) is in Jackson's internal (hash-based) order, not declaration order — another reason not to parse it from text. Both findings are documented as standalone assertions against the real captured message (independent of the handler), per Task 1's own scope.
- Task 2: rewrote `handleHttpMessageNotReadable` to check `ex.getCause() instanceof MismatchedInputException` (Jackson 3, `tools.jackson.databind.exc`). Used a single `instanceof` check against `MismatchedInputException` rather than two separate checks for `InvalidFormatException`/`MismatchedInputException`, since `InvalidFormatException extends MismatchedInputException` in Jackson 3 (confirmed by reading the decompiled/sourced 3.2.2 jar) — one check covers both, per the story's own guidance not to add anything not asked for. `field` = `getPropertyName()` of the LAST entry in `getPath()` (the leaf, fixing the nested-field bug found in Task 1), falling back to `""` if the path is empty or the property name is null (e.g. array index references). `typesEnum` = built from `getTargetType().getEnumConstants()` (declaration order, deterministic) joined as `"[A, B, C]"` when the target type is an enum, else left as `""` — this only fires for enum-mismatch cases, same as the old regex's practical effect, but without depending on message text shape. Fallback (`field`/`typesEnum` both `""`) preserved for any other cause type (verified with a `RuntimeException` cause and with no cause at all).
- Removed now-unused `java.util.regex.Matcher`/`Pattern` imports from the production file; added `tools.jackson.core.JacksonException` (for `Reference`), `tools.jackson.databind.exc.MismatchedInputException`, `java.util.Arrays`, `java.util.stream.Collectors`.
- Added `ExceptionsHandlerJackson3DeserializationTest` (6 tests) covering both Task 1 (2 baseline/regression tests run directly against a real Jackson 3 message, independent of the handler) and Task 2 (4 tests exercising the rewritten handler: top-level cause, nested cause, non-Jackson cause fallback, no-cause fallback). Real `MismatchedInputException` instances are obtained by actually invoking `tools.jackson.databind.json.JsonMapper.readValue` against a local test enum/record hierarchy (no mocking of Jackson types), so the tests exercise the real Jackson 3 API surface rather than an assumption about it.
- No changes to `resolveTitle`, to any other exception handler method, or to any file belonging to the concurrently in-progress Story 2.10 (`core/.../Constant.java`, `web/.../LoggingInitialFilter.java`, root `pom.xml`, `validation/pom.xml`, `codegen/.../api.mustache`) — confirmed via `git status --short` before finishing that only this story's files are modified/untracked.
- Did not stage or commit anything, per instructions; left all changes in the working tree for review.

### Revisão de 3 camadas

Achados triados (blind-hunter, edge-case-hunter, verification-gap):

- **Patch**: `typesEnum` era construído com `.map(Object::toString)` — para um enum que sobrescreve `toString()` (comum para rótulos legíveis), reportaria o literal errado em vez do que o Jackson de fato aceita na deserialização (que casa contra o nome da constante, não `toString()`). Trocado para `.map(constant -> ((Enum<?>) constant).name())`. Confirmado de forma independente por blind-hunter e edge-case-hunter.
- **Patch**: zero cobertura de teste para o caso em que a última `Reference` de `getPath()` é um índice de array (`getPropertyName() == null`) — `field` deveria cair para `""`, não `null`. Confirmado de forma independente por edge-case-hunter e verification-gap (este último com reprodução concreta via probe direto contra os jars reais: `Color[]` com valor inválido no índice 1 → `path.size=1`, `propertyName=null`, `index=1`, `targetType=Color`). Teste `fallsBackToEmptyFieldForIndexOnlyPath` adicionado.
- **Patch**: zero cobertura para um enum "nu" no nível raiz (`getPath()` vazio, mas `getTargetType()` ainda é o enum) — os dois blocos (`field` via `path`, `typesEnum` via `targetType`) são `if`s irmãos independentes, não aninhados, então `typesEnum` já era computado corretamente mesmo com `path` vazio; só faltava o teste confirmando isso. Confirmado por verification-gap com reprodução concreta (`"PURPLE"` direto contra `Color.class` → `path.size=0`, `targetType=Color`). Teste `emptyPathStillPopulatesTypesEnumForBareTopLevelEnum` adicionado.
- **Patch**: zero cobertura para um `targetType` não-enum (ex.: mismatch numérico) — `field` deveria ser extraído normalmente enquanto `typesEnum` permanece `""`. Confirmado por blind-hunter, reprodução via probe (`{"n":"notanumber"}` num record com `int n` → `path.size=1`, `propertyName="n"`, `targetType=int`). Teste `nonEnumTargetTypeLeavesTypesEnumEmpty` adicionado.
- **Patch**: o texto do Task 2 ainda citava `getFieldName()` como o método de `Reference` usado, mas essa API não existe em Jackson 3 (é nome legado do Jackson 2) — a implementação já usava corretamente `getPropertyName()`, só o texto do Task estava desatualizado. Texto corrigido inline (ver Task 2 acima). Confirmado por blind-hunter.
- **Patch**: Debug Log afirmava "39 testes (33 pré-existentes + 6 novos)" — aritmética errada; o baseline real pré-story era 27 (confirmado pela suíte completa da Story 2.4), então 27+6=33, não 39. Corrigido acima. Confirmado por blind-hunter e verificado de forma independente rodando `mvn -o -pl exception -am test` antes de qualquer patch.
- **Patch**: os testes usavam o literal `"SCOS-001"` em vez de `ScosExceptionCode.ATTRIBUTE_NOT_VALID.getCode()` — se o código mudar, os testes param de verificar o caminho real sem falhar. Trocado para a referência simbólica em todas as ocorrências. Confirmado por blind-hunter.
- **Rejeitado com evidência**: edge-case-hunter apontou risco de `NullPointerException` se `mie.getPath()` retornasse `null`. Verificado lendo o fonte real de `tools.jackson.core.JacksonException.getPath()` (jar `jackson-core-3.2.2-sources.jar`): o método nunca retorna `null`, sempre `Collections.emptyList()` quando o campo interno é `null`. Alarme falso.
- **Rejeitado com evidência**: edge-case-hunter sugeriu percorrer toda a cadeia de causas (`getCause().getCause()...`), não só `ex.getCause()`. A Task 2 da própria story pede explicitamente navegação de um único nível (`"navegando ex.getCause() quando for..."`), e não há evidência de que a integração Spring+Jackson 3 para `HttpMessageNotReadableException` encadeie a exceção de deserialização mais de um nível abaixo — sem caminho de produção confirmado, e fora do que a AC pediu.
- **Rejeitado com evidência**: blind-hunter apontou que a seção `## Suggested Review Order` (convenção das Stories 2.1-2.4) está ausente no diff revisado — é adicionada agora, nesta mesma etapa de finalização (step-05), não uma omissão do subagente de implementação.
- **Rejeitado com evidência**: blind-hunter questionou a Task 0 não ter evidência de escalonamento ao dono do épico, apesar do próprio Task pedir isso "se a leitura estiver errada". A leitura (o alvo real é `handleHttpMessageNotReadable`, não `resolveTitle`) foi verificada de forma independente por este orquestrador antes de despachar a implementação (`resolveTitle` de fato não usa regex, confirmado por leitura direta do código) — não estava errada, então nenhum escalonamento era necessário.
- **Rejeitado com evidência**: blind-hunter apontou que `@MockitoSettings(strictness = Strictness.LENIENT)` no nível da classe de teste enfraquece a detecção de stubbing desnecessário do Mockito — é a mesma convenção já usada em toda a suíte de testes de `ExceptionsHandler` (`ExceptionsHandlerLogLevelTest`, `ExceptionsHandlerValidationTest`, etc.), não uma escolha nova desta story.
- **Rejeitado com evidência**: blind-hunter apontou que 2 dos 6 testes originais (`oldRegex*`) não tocam o código de produção. É exatamente o escopo pedido pela própria Task 1 ("teste de regressão contra o regex atual", documentação standalone do bug, independente do handler) — não é uma lacuna, é o que foi pedido.
- **Rejeitado com evidência**: blind-hunter apontou que nenhum teste novo afirma sobre o `ProblemDetail`/corpo de resposta final, só sobre os argumentos passados a `localeService.getMessage(...)` via `verify()`. O `verify()` já fixa exatamente o comportamento que esta story mudou (quais valores são extraídos de `field`/`typesEnum`); a montagem do `ProblemDetail` a partir desses valores é código pré-existente e não mudou nesta story.
- **Rejeitado com evidência**: blind-hunter apontou que os arquivos do probe standalone usado na investigação foram apagados, não sendo reprodutíveis por um revisor. Os testes que ficam no diff usam chamadas reais ao `JsonMapper` do Jackson 3 (não mocks, não valores fixos copiados do probe) — são reprodutíveis de forma independente por qualquer revisor, sem depender do probe descartado.
- **Adiado para `deferred-work.md`**: `epics.md`/`prd.md` (FR14) ainda descrevem esta correção como sendo em `resolveTitle` — desatualizado desde que o Task 0 desta própria story confirmou que o alvo real é `handleHttpMessageNotReadable`. Corrigir os documentos de planejamento está fora do escopo desta story de bug-fix.
- **Adiado para `deferred-work.md`**: `SCOS-001` (`ATTRIBUTE_NOT_VALID`, usado por `handleHttpMessageNotReadable` na linha do `localeService.getMessage(...)`, não tocada por esta story) não tem placeholders `{0}`/`{1}` no bundle de mensagens — é `SCOS-002`/`ENUM_ERROR` (usado só para `type`/`title` do `ProblemDetail`, 3 linhas abaixo) que tem os placeholders. Ou seja, mesmo com `field`/`typesEnum` agora extraídos corretamente por esta story, eles nunca aparecem no texto de `detail` de uma resposta real, porque são passados para o template errado. Achado por verification-gap; confirmado pré-existente e não causado por esta story (a linha do `localeService.getMessage` não foi tocada, só os valores de `field`/`typesEnum` que ela recebe).

### File List

- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` (modified — `handleHttpMessageNotReadable`, now around lines 77-118; import block updated; `Enum::name` instead of `Object::toString` for `typesEnum`, fixed on review)
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerJackson3DeserializationTest.java` (new; extended from 6 to 9 cases on review — array-index path, bare top-level enum, non-enum target type; literal `"SCOS-001"` replaced with `ScosExceptionCode.ATTRIBUTE_NOT_VALID.getCode()`)

## Suggested Review Order

**A extração de `field`/`typesEnum` (o core da story)**

- `handleHttpMessageNotReadable` — checagem única `instanceof MismatchedInputException` (cobre `InvalidFormatException` também, é subtipo em Jackson 3), `field` do último elemento de `getPath()`, `typesEnum` de `getTargetType().getEnumConstants()` via `Enum::name` (corrigido na revisão — era `Object::toString`).
  [`ExceptionsHandler.java:79`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L79)

**Os testes (Task 1 documenta o bug, Task 2 prova o fix)**

- `oldRegexGrabsWrongFieldForNestedPath` — a evidência do bug real: o regex antigo pega o campo errado (`"middle"`, o mais externo) em vez do que realmente falhou (`"color"`, o leaf), num caminho aninhado.
  [`ExceptionsHandlerJackson3DeserializationTest.java:105`](../../exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerJackson3DeserializationTest.java#L105)

- Os 3 casos de borda adicionados na revisão: índice de array (`propertyName == null`), enum "nu" no nível raiz (`path` vazio), tipo não-enum (`typesEnum` deve ficar vazio).
  [`ExceptionsHandlerJackson3DeserializationTest.java:182`](../../exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerJackson3DeserializationTest.java#L182)

**A decisão de nomes (Task 0, já resolvida antes da implementação)**

- Confirmação de que o alvo real é `handleHttpMessageNotReadable`, não `resolveTitle` — `epics.md`/`prd.md` continuam desatualizados quanto a isso (ver `deferred-work.md`).
  [`2-5-corrigir-a-resolução-de-título-de-erro-para-jackson-3.md:21`](#tasks--subtasks)
