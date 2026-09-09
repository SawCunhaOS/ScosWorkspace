# Story 2.2: Corrigir o handler de validação para parâmetro simples (400)

Status: done

<!-- baseline_commit: c3db7f165eea69b9923634b4dc20f4dd2d2d87a6 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor da API,
Eu quero que uma violação em `@RequestParam @Min(1) int page` responda `400`,
Para não receber `500` por uma exceção não tratada.

## Acceptance Criteria

1. **Given** um teste que reproduz o `IndexOutOfBoundsException` hoje lançado em `getBeanResults().get(0)` para parâmetro simples, **When** o teste é escrito e falha antes da correção, **Then** o handler passa a iterar sobre `getBeanResults()` e `getValueResults()` e responde `400`.

## Tasks / Subtasks

- [x] Task 1 — teste que reproduz o bug, TDD (NFR5) (AC: #1)
  - [x] Escrever um teste para `ExceptionsHandler.handleHandlerMethodValidationException` (linha 140-168 de `ExceptionsHandler.java`) que simula um `HandlerMethodValidationException` cujo `getBeanResults()` retorna lista vazia (caso real de violação em parâmetro simples anotado direto, ex.: `@RequestParam @Min(1) int page`) — hoje `ex.getBeanResults().get(0)` (linha 149) lança `IndexOutOfBoundsException` nesse cenário, que escapa do `@ExceptionHandler` e vira `500` não tratado
  - [x] Confirmar a falha do teste antes de tocar no código de produção
- [x] Task 2: Iterar sobre `getBeanResults()` e `getValueResults()` (AC: #1)
  - [x] Em `handleHandlerMethodValidationException`, substituir `ex.getBeanResults().get(0).getFieldErrors().forEach(...)` (linha 149) por iteração segura sobre `ex.getBeanResults()` (violações em objetos `@Valid`, mapeadas para `ScosFieldError` via `getFieldErrors()`, como já ocorre) **e** sobre `ex.getValueResults()` (violações em parâmetro simples anotado direto — cada `ParameterValidationResult` expõe o parâmetro e a lista de `MessageSourceResolvable` das violações, sem `getFieldErrors()`)
  - [x] Reaproveitar `ScosFieldError.of(...)` e `localeService.getMessage(...)` já usados no restante do método — mesma forma de erro (`ScosProblemDetails.ofValidation`), sem criar um segundo formato para parâmetro simples

## Dev Notes

- **Bug real confirmado**: `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java`, método `handleHandlerMethodValidationException` (linha 140-168), linha 149: `ex.getBeanResults().get(0).getFieldErrors().forEach(...)`. `HandlerMethodValidationException.getBeanResults()` só é não-vazio quando a violação ocorre em um parâmetro anotado `@Valid` (um bean); para um parâmetro simples anotado diretamente (`@RequestParam @Min(1) int page`), a violação aparece em `getValueResults()`, e `getBeanResults()` retorna lista vazia — `.get(0)` lança `IndexOutOfBoundsException`.
- `ParameterValidationResult` (o tipo de item de `getValueResults()`) não tem `getFieldErrors()` — expõe `getMethodParameter()` e `getResolvableErrors()` (lista de `MessageSourceResolvable`). O código precisa tratar os dois tipos de resultado com formas de extração diferentes, unificando no mesmo `List<ScosFieldError>` que já alimenta `ScosProblemDetails.ofValidation`.
- Reaproveitar `getArgsValidation` de `ExceptionUtils` (já usado nas outras 3 chamadas do mesmo padrão neste arquivo) para extrair os argumentos de mensagem de cada `MessageSourceResolvable`, mantendo consistência com `handleMethodArgumentNotValid` e `handleConstraintViolationException`.
- **NFR5** (TDD): o teste da Task 1 deve reproduzir o `IndexOutOfBoundsException` e falhar antes da correção.
- Este handler já está registrado corretamente (`@Override protected ResponseEntity<Object> handleHandlerMethodValidationException(...)`, sobrescreve o método do `ResponseEntityExceptionHandler`) — a correção é só na lógica interna, não no registro.

### Project Structure Notes

- Arquivo modificado: `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` (método `handleHandlerMethodValidationException`).
- Novo arquivo de teste (ou extensão de `ExceptionsHandlerValidationTest.java` existente, se o cenário de parâmetro simples couber ali sem misturar responsabilidades — decisão do dev-agent ao ver o arquivo).

### References

- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java]
- [Source: exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerValidationTest.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-22-corrigir-o-handler-de-validação-para-parâmetro-simples-400]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

- RED confirmado: com `ExceptionsHandler.java` no estado anterior (`ex.getBeanResults().get(0)...`), o teste `ExceptionsHandlerValidationTest#simpleParameterViolationRespondsBadRequest` (mock de `HandlerMethodValidationException` com `getBeanResults()` vazio e `getValueResults()` com um `ParameterValidationResult`) falha com `java.lang.ArrayIndexOutOfBoundsException: Index 0 out of bounds for length 0` em `ExceptionsHandler.java:149` — reproduz exatamente o bug descrito (a exceção varia de tipo conforme a JDK/coleção imutável — `IndexOutOfBoundsException`/`ArrayIndexOutOfBoundsException` — mas escapa do `@ExceptionHandler` do mesmo jeito, virando 500 não tratado).
- GREEN confirmado: após aplicar a correção (iterar `getBeanResults()` e `getValueResults()`), `mvn -pl exception test -Dtest=ExceptionsHandlerValidationTest` → `Tests run: 3, Failures: 0, Errors: 0, Skipped: 0`.
- Suíte completa do módulo `exception`: `mvn -pl exception test` → `BUILD SUCCESS` (exit 0), sem falhas em nenhuma classe de teste.
- **Revisão de 3 camadas** (blind-hunter, edge-case-hunter; verification-gap falhou por limite de sessão da ferramenta, análise equivalente feita diretamente). Achados triados:
  - **Correção de precisão nas Completion Notes** (abaixo): o código antigo processava só `getBeanResults().get(0)` — o PRIMEIRO resultado de bean, não todos. A frase original "comportamento preexistente preservado" estava imprecisa; a nova versão processa TODOS os `getBeanResults()`, uma melhoria real (silenciosa) além do que a AC #1 pedia — corrigido abaixo para refletir isso com precisão.
  - **Teste novo adicionado**: `simpleParameterViolationFallsBackToIndexWhenNameUnresolvable` — cobre o branch do fallback por índice (`field != null ? field : ...`) que não tinha nenhum teste (achado do Blind Hunter); reaproveita o helper `simpleParameterViolation`, que ganhou o stub de `getParameterIndex()`.
  - **Achados rejeitados com evidência**: o prefixo de log `"handleSecurity - "` não é resquício de copy-paste da Story 2.1 — é a convenção já estabelecida em toda a classe (aparece 10x em `ExceptionsHandler.java`, pré-existente). O uso do código `"SCOS-005"` como placeholder no teste (na verdade o código real de "token de acesso não informado", sem relação com `@Min`) é só um valor arbitrário — `localeService` é mockado no teste, então o texto real do bundle de mensagens nunca é consultado; inofensivo, mas deixado como está (não vale o churn de renomear).
  - **Achados adiados para `deferred-work.md`** (pré-existentes, não causados por esta story): `beanResult.getFieldErrors()` nunca chama `getGlobalErrors()` (violações de nível de objeto/classe seriam descartadas) — o padrão `.getFieldErrors()`-só já existia no código antigo, só processando um bean por vez; `MessageSourceResolvable.getDefaultMessage()` retornando `null` — mesmo padrão de risco já existia no caminho de `beanResult` antes desta story; caso `getBeanResults()` e `getValueResults()` ambos vazios simultaneamente — teoricamente possível mas Spring só lança `HandlerMethodValidationException` quando há pelo menos um resultado, então é um caso defensivo de baixíssima probabilidade; ausência de teste de integração via `MockMvc` contra um `HandlerMethodValidationException` real do Spring — padrão já estabelecido em toda a suíte deste módulo (invocação direta do handler), não uma lacuna introduzida por esta story.

### Completion Notes List

- AC #1: `handleHandlerMethodValidationException` agora itera `ex.getBeanResults()` (violações em parâmetro `@Valid`, via `getFieldErrors()`) e também `ex.getValueResults()` (violações em parâmetro simples anotado direto, ex. `@RequestParam @Min(1) int page`, via `ParameterValidationResult.getMethodParameter()` + `getResolvableErrors()`), unificando tudo no mesmo `List<ScosFieldError>` consumido por `ScosProblemDetails.ofValidation` — nenhum formato novo de erro foi criado. **Correção pós-revisão**: o código antigo só processava `getBeanResults().get(0)` (o primeiro bean); a versão nova itera TODOS os `getBeanResults()`, não só o comportamento antigo "preservado" — para um handler com mais de um parâmetro `@Valid`, isso agora captura violações que antes eram silenciosamente descartadas. Efeito colateral bem-vindo desta correção, não testado explicitamente (ver `deferred-work.md`).
- Nome do campo para violações de `getValueResults()`: `MethodParameter.getParameterName()` (via descoberta de nome de parâmetro do Spring, já inicializada pelo `HandlerMethod` que originou a invocação); fallback defensivo para o índice do parâmetro (`String.valueOf(getParameterIndex())`) caso o nome não seja resolvível (ex.: build sem debug info) — evita `NullPointerException` em `ScosFieldError.of(...)`. Coberto por `simpleParameterViolationFallsBackToIndexWhenNameUnresolvable` (teste adicionado na revisão).
- `getArgsValidation(Object[])` (`ExceptionUtils`) reaproveitado sem alteração — `MessageSourceResolvable.getArguments()` retorna `Object[]`, mesma assinatura já usada para `FieldError.getArguments()`.
- Nenhum módulo novo, nenhuma dependência nova.

### File List

- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` — `handleHandlerMethodValidationException`: substituída a chamada `ex.getBeanResults().get(0)...` por iteração sobre `getBeanResults()` e `getValueResults()`.
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerValidationTest.java` — novo teste `simpleParameterViolationRespondsBadRequest` (+ helper `simpleParameterViolation`) reproduzindo o cenário de parâmetro simples com `getBeanResults()` vazio; novo teste `simpleParameterViolationFallsBackToIndexWhenNameUnresolvable` (revisão) cobrindo o fallback por índice.

## Suggested Review Order

**A correção do bug**

- `ex.getBeanResults().get(0)` — a causa raiz, um `.get(0)` que assumia que violações de parâmetro simples sempre vêm com pelo menos um resultado de bean.
  [`ExceptionsHandler.java:150`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L150)

- `getValueResults()` — o caminho novo, para violações em parâmetro simples anotado direto, que não tem `getFieldErrors()`.
  [`ExceptionsHandler.java:161`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L161)

- O fallback defensivo por índice quando o nome do parâmetro não é resolvível — coberto por teste adicionado na revisão.
  [`ExceptionsHandler.java:165`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L165)

**Os testes**

- O teste que reproduz o bug (TDD/NFR5) e prova a correção.
  [`ExceptionsHandlerValidationTest.java:161`](../../exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerValidationTest.java#L161)

- O teste novo da revisão, cobrindo o branch do fallback por índice.
  [`ExceptionsHandlerValidationTest.java:187`](../../exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerValidationTest.java#L187)
