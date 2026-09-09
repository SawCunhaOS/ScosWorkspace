# Story 2.3: Retornar 501 para funcionalidade não implementada

Status: done

<!-- baseline_commit: 4d3c25d33b8d899a06799eba95708ac203401de3 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

<!-- Correção pré-implementação: o spec original referenciava `utils/src/main/java/br/com/sawcunhaos/foundation/utils/enums/ScosExceptionCode.java`, um caminho que não existe mais — o módulo `utils` foi removido do reactor na Story 1.14 do Épico 1, e `ScosExceptionCode` foi movido para `core` já na Story 1.9. Corrigido para `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ScosExceptionCode.java` (3 ocorrências: Task 1, Project Structure Notes, References) antes de despachar a implementação. `SCOS-010` confirmado disponível (códigos existentes vão de SCOS-001 a SCOS-009). -->

## Story

Como consumidor da API,
Eu quero que uma rota marcada como não implementada responda `501`,
Para distinguir isso de um erro genérico de servidor.

## Acceptance Criteria

1. **Given** uma chamada que lança `MethodNotImplementedException`, **When** o handler processa a exceção, **Then** a resposta é `501` em vez do `500` genérico atual.

## Tasks / Subtasks

- [x] Task 1: Adicionar handler dedicado (AC: #1)
  - [x] `exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/MethodNotImplementedException.java` hoje **não** estende `ScosException` — é uma `RuntimeException` simples sem `code`/`httpCode`. Sem handler próprio, ela cai no `@ExceptionHandler(Exception.class)` genérico (`handleGenericException`, linha 270 de `ExceptionsHandler.java`) e responde `500`
  - [x] Adicionar `@ExceptionHandler(MethodNotImplementedException.class)` em `ExceptionsHandler.java`, seguindo o mesmo padrão do handler de `AccessDeniedException` (que também não usa `ScosException`): montar o `ProblemDetail` via `ScosProblemDetails.of(...)` com `HttpStatus.NOT_IMPLEMENTED` (501) hardcoded, sem depender de um `getHttpCode()` de enum
  - [x] Não existe hoje uma constante `ScosExceptionCode` para "não implementado" — adicionar um código de erro dedicado (ex.: `ScosExceptionCode.NOT_IMPLEMENTED("SCOS-010", "Not Implemented")`) em `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ScosExceptionCode.java`, seguindo exatamente o padrão dos 9 códigos já existentes ali (não reaproveitar `GENERIC`, que é semanticamente "erro interno genérico", não "não implementado")
- [x] Task 2: Teste (AC: #1)
  - [x] Teste unitário chamando o novo handler diretamente com uma instância de `MethodNotImplementedException`, mesmo padrão dos testes existentes (`@Mock LocaleService`, `@InjectMocks ExceptionsHandler`), confirmando `501` e o novo código/título

## Dev Notes

- **Confirmado no código atual**: `MethodNotImplementedException` (`exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/MethodNotImplementedException.java`) estende `RuntimeException` puro — nenhum handler específico existe hoje em `ExceptionsHandler.java` para ela, então cai no fallback genérico e responde `500`.
- Não seguir o padrão de `ScosException`/`ScosNoRollbackException` (que recebem `ExceptionCode` no construtor) para `MethodNotImplementedException` — mudar a hierarquia dessa exceção está fora do escopo desta story (é só sobre a resposta HTTP do handler). Usar o mesmo padrão simples do handler de `AccessDeniedException`: montar o `ProblemDetail` direto no handler, sem exigir que a exceção carregue o `ExceptionCode`.
- Escopo intencionalmente pequeno: **não** adicionar aqui nenhuma lógica de "quais rotas retornam not-implemented" — a story só garante que, quando essa exceção específica é lançada (por quem já a usa hoje em código consumidor), a resposta HTTP é `501`.

### Project Structure Notes

- Arquivo modificado: `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` (novo `@ExceptionHandler`).
- Arquivo modificado: `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ScosExceptionCode.java` (novo enum constant `NOT_IMPLEMENTED`, código `SCOS-010`).
- Novo arquivo de teste em `exception/src/test/java/br/com/sawcunhaos/foundation/exception/`.

### References

- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/MethodNotImplementedException.java]
- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java]
- [Source: core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ScosExceptionCode.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-23-retornar-501-para-funcionalidade-não-implementada]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -pl core -am clean install -DskipTests` e `mvn -pl exception -am clean install -DskipTests` → `BUILD SUCCESS`.
- `mvn -pl core -am test -Dtest=ScosExceptionCodeTest -Dsurefire.failIfNoSpecifiedTests=false` → `Tests run: 5, Failures: 0, Errors: 0, Skipped: 0`.
- `mvn -pl exception -am test` (suíte completa do módulo) → todas as classes com `Failures: 0, Errors: 0`, incluindo a nova `ExceptionsHandlerMethodNotImplementedTest` (`Tests run: 1, Failures: 0, Errors: 0, Skipped: 0`).

### Completion Notes List

- AC #1: adicionado `@ExceptionHandler(MethodNotImplementedException.class)` em `ExceptionsHandler.java`, entre `handleAccessDeniedException`/`handleAuthorizationDeniedException` e o fallback genérico `handleGenericException`. Segue exatamente o padrão do handler de `AccessDeniedException`: monta o `ProblemDetail` via `ScosProblemDetails.of(HttpStatus.NOT_IMPLEMENTED, ScosExceptionCode.NOT_IMPLEMENTED, detail, request.getRequestURI())`, com `HttpStatus.NOT_IMPLEMENTED` hardcoded (não depende de `getHttpCode()`, já que `MethodNotImplementedException` continua um `RuntimeException` puro, sem alterar sua hierarquia, conforme o escopo da story).
- Novo código de erro `ScosExceptionCode.NOT_IMPLEMENTED("SCOS-010", "Not Implemented")` adicionado ao final do enum em `core/`, seguindo o mesmo padrão Javadoc + `AllArgsConstructor` dos 9 códigos existentes. Confirmado que nenhum teste no repositório itera o enum exigindo uma contagem fixa (`ScosExceptionCodeTest` testa códigos específicos, não a contagem total), então a adição não quebra nada existente.
- Nenhuma alteração na hierarquia de `MethodNotImplementedException` (permanece `RuntimeException` simples), conforme Dev Notes da story.
- Nenhum módulo novo, nenhuma dependência nova.
- **Revisão de 3 camadas.** Achados triados:
  - **Patch**: o teste novo não afirmava `problem.getDetail()`/`problem.getInstance()` — inconsistente com `ExceptionsHandlerScosExceptionTest`, que testa os dois. Adicionadas as duas asserções.
  - **Patch**: `ScosExceptionCode.NOT_IMPLEMENTED` (`SCOS-010`) não tinha entrada nos bundles de mensagem (`core/src/main/resources/scos_utils_messages{,_en}.properties`) — adicionada (`"Funcionalidade não implementada."`/`"Functionality not implemented."`).
  - **Rejeitado com evidência**: o prefixo de log `"handleSecurity - "` "mislabeling" uma exceção não relacionada a segurança — é a convenção já estabelecida em toda a classe (usado até em `handleGenericException`, que também não é especificamente sobre segurança); não é um erro desta story. `localeService.getMessage(code)` sem guarda contra `null` — o mesmo padrão exato já existe em 5 outros pontos da classe (4 pré-existentes a esta story) — risco real, mas não introduzido nem agravado aqui; ver `deferred-work.md`. `MethodNotImplementedException` "nunca lançada em código de produção" — esperado por design: é uma biblioteca de fundação, a exceção é lançada por aplicações consumidoras externas (fora deste repositório), conforme a própria Dev Notes da story já explicita.
  - **Verificado e descartado**: `epics.md` (fonte de origem) não tem o mesmo caminho obsoleto de `ScosExceptionCode` corrigido no início desta story — nada a corrigir lá. Não existe catálogo formal de códigos `SCOS-0xx` (README/OpenAPI) para atualizar.
  - **Adiado para `deferred-work.md`**: `SCOS-009` (`EMAIL_INVALID`, de story anterior) tem a mesma lacuna de mensagem que `SCOS-010` tinha — fora do escopo desta story corrigir um código que não é seu; padrão de `localeService.getMessage(code)` sem guarda de `null` em toda a classe; se `MethodNotImplementedException` deveria eventualmente estender `ScosException` como as outras 9 — decisão de design deliberadamente adiada pela própria story, registrada para não se perder.
  - Verificação adicional feita pelo orquestrador (não pelo subagente de implementação): `mvn clean install` (reactor completo) e `mvn -o test` (suíte completa) rodados após a atualização do `scos-bom` para `1.4.4-SNAPSHOT` (ver Debug Log acima) — reactor inteiro verde, só a flakiness pré-existente do Docker em `jdempotent` (documentada desde a Story 1.10).

### File List

- `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ScosExceptionCode.java` — novo enum constant `NOT_IMPLEMENTED("SCOS-010", "Not Implemented")`.
- `../../core/src/main/resources/scos_message/scos_utils_messages.properties` — nova entrada `SCOS-010` (revisão).
- `../../core/src/main/resources/scos_message/scos_utils_messages_en.properties` — nova entrada `SCOS-010` (revisão).
- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` — novo `@ExceptionHandler(MethodNotImplementedException.class)` (`handleMethodNotImplementedException`) + import de `MethodNotImplementedException`.
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerMethodNotImplementedTest.java` — novo, teste unitário confirmando `501`/`SCOS-010`/`Not Implemented`/`detail`/`instance` no `ProblemDetail`, mesmo padrão de `ExceptionsHandlerAccessDeniedTest`/`ExceptionsHandlerScosExceptionTest`.

## Suggested Review Order

**O handler novo**

- `@ExceptionHandler(MethodNotImplementedException.class)` — mesmo padrão do handler de `AccessDeniedException` (Story 2.1), `HttpStatus.NOT_IMPLEMENTED` hardcoded por design.
  [`ExceptionsHandler.java:286`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L286)

- O código de erro novo, `SCOS-010`.
  [`ScosExceptionCode.java:53`](../../core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ScosExceptionCode.java#L53)

**O teste**

- Cobre `501`/`SCOS-010`/título/`detail`/`instance` — as duas últimas asserções adicionadas na revisão.
  [`ExceptionsHandlerMethodNotImplementedTest.java:48`](../../exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerMethodNotImplementedTest.java#L48)
