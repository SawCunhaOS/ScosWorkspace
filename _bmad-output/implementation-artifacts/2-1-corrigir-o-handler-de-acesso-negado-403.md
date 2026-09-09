# Story 2.1: Corrigir o handler de acesso negado (403)

Status: done

<!-- baseline_commit: 5ac4320f6c2e050095d3054cad511139bda2e259 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor da API protegida por Spring Security,
Eu quero que uma negação de autorização real responda `403`,
Para não receber `500` num erro que na verdade é de permissão.

## Acceptance Criteria

1. **Given** um teste que reproduz o bug (chamada negada por `org.springframework.security.access.AccessDeniedException` hoje capturada como `500`), **When** o teste é escrito e falha antes da correção, **Then** o handler passa a capturar `AccessDeniedException` e responde `403`.
2. **And** o handler existente para `AuthorizationDeniedException` continua lado a lado, sem substituição.

## Tasks / Subtasks

- [x] Task 1 — teste que reproduz o bug, TDD (NFR5) (AC: #1)
  - [x] Escrever um teste que invoca `ExceptionsHandler.handleAccessDeniedException` com uma instância de `org.springframework.security.access.AccessDeniedException` e espera `403`. Antes da correção este teste FALHA — hoje esse tipo não é capturado por nenhum `@ExceptionHandler` específico e cai no `@ExceptionHandler(Exception.class)` genérico (`handleGenericException`, linha 270 de `ExceptionsHandler.java`), que responde `500`
  - [x] Confirmar a falha rodando o teste antes de tocar no código de produção
- [x] Task 2: Trocar o tipo capturado pelo handler (AC: #1)
  - [x] Em `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java`, trocar o import `java.nio.file.AccessDeniedException` (linha 45) por `org.springframework.security.access.AccessDeniedException`
  - [x] O método `handleAccessDeniedException(AccessDeniedException ex, HttpServletRequest request)` (linha 240-252) já responde `403` corretamente — a correção é só o tipo capturado, a lógica interna não muda
- [x] Task 3: Corrigir o teste existente que hoje usa o tipo errado (AC: #1)
  - [x] `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerAccessDeniedTest.java` hoje importa e instancia `java.nio.file.AccessDeniedException` — trocar para `org.springframework.security.access.AccessDeniedException` (o construtor de ambos aceita uma `String`, a chamada `new AccessDeniedException("/api/admin/users")` continua válida sem outra alteração)
- [x] Task 4: Confirmar que os dois handlers continuam lado a lado (AC: #2)
  - [x] Confirmar que `handleAccessDeniedException(AuthorizationDeniedException ex, HttpServletRequest request)` (linha 254-266) não é tocado nesta story — nenhuma alteração de assinatura, nenhuma remoção

## Dev Notes

- **Bug real confirmado no código atual** (`exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java`): existem hoje 2 handlers de "acesso negado" — um para `java.nio.file.AccessDeniedException` (linha 240, **tipo errado**, nunca lançado pelo Spring Security em runtime) e um para `org.springframework.security.access.AuthorizationDeniedException` (linha 254, correto e já funcional). Quando o Spring Security lança sua própria `org.springframework.security.access.AccessDeniedException` (que é o tipo real usado por `@PreAuthorize`/voters mais antigos, distinto de `AuthorizationDeniedException` que é o mecanismo mais novo), nenhum handler específico casa — cai no `Exception.class` genérico e responde `500`. Esta story fecha exatamente essa lacuna.
- O teste existente `ExceptionsHandlerAccessDeniedTest.java` hoje passa com o tipo nio porque o handler (mesmo com o tipo errado) responde 403 para o que foi instanciado nele — o teste não expõe o bug porque testa o handler com o tipo que ele já captura, não o tipo real que o Spring Security lança. Por isso a Task 1 exige escrever contra o tipo `org.springframework.security.access.AccessDeniedException` especificamente.
- **NFR5** (TDD): o teste da Task 1 deve ser escrito e confirmado falhando antes de tocar em `ExceptionsHandler.java`.
- Não modificar `ScosProblemDetails`, `LocaleService` nem o `ScosExceptionCode.ACCESS_DENIED` — o formato de resposta (403, título "Access Denied", `SCOS-004`) já está correto, só o tipo capturado está errado.

### Project Structure Notes

- Arquivo modificado: `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` (só o import, linha 45).
- Arquivo modificado: `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerAccessDeniedTest.java` (só o import/instanciação).
- Nenhum módulo novo, nenhuma dependência nova.

### References

- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java]
- [Source: exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerAccessDeniedTest.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-21-corrigir-o-handler-de-acesso-negado-403]
- [Source: _bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/prd.md]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

- RED confirmado: `mvn -pl exception test -Dtest=ExceptionsHandlerAccessDeniedTest` falha em compilação após trocar só o import do teste para `org.springframework.security.access.AccessDeniedException` (produção ainda com `java.nio.file.AccessDeniedException`) — `no suitable method found for handleAccessDeniedException(org.springframework.security.access.AccessDeniedException, MockHttpServletRequest)`.
- GREEN confirmado: após trocar o import em `ExceptionsHandler.java`, mesmo teste passa (`Tests run: 1, Failures: 0`).
- Suíte completa do módulo `exception`: `mvn -pl exception test` → `Tests run: 12, Failures: 0, Errors: 0, Skipped: 0`, `BUILD SUCCESS`.
- **Revisão de 3 camadas (blind-hunter, edge-case-hunter, verification-gap)**: nenhum achado exigiu mudança de código. Dois pontos investigados e fechados com evidência:
  1. O tipo antigo removido (`java.nio.file.AccessDeniedException`) não é lançado em nenhum outro lugar do reactor — confirmado via `grep -rn "java.nio.file.AccessDeniedException"` em todo o repositório (fora de `target/`), zero ocorrências. Nenhum caminho de código regride de 403 para 500.
  2. `org.springframework.security.authorization.AuthorizationDeniedException extends org.springframework.security.access.AccessDeniedException` (confirmado via `javap` no jar `spring-security-core:7.1.1`) — os dois `@ExceptionHandler` desta classe agora têm uma relação de herança que não existia antes (o tipo antigo, `java.nio.file.AccessDeniedException`, não tinha relação nenhuma com `AuthorizationDeniedException`). Isso não é um bug: o mecanismo de resolução de `@ExceptionHandler` do Spring MVC já escolhe o handler mais específico da hierarquia por padrão, e os dois handlers desta classe produzem `ProblemDetail` byte-a-byte idênticos (mesmo `HttpStatus.FORBIDDEN`, mesmo `ScosExceptionCode.ACCESS_DENIED`) — a única diferença é o texto da mensagem de log interna. Mesmo que a resolução escolhesse o handler "errado", nenhum consumidor da API notaria. Nenhum teste de integração via `MockMvc`/`@WebMvcTest` existe para provar a resolução em tempo real, mas isso é o padrão já estabelecido em todos os testes de `ExceptionsHandler` neste módulo (invocação direta do método), não uma lacuna introduzida por esta story.

### Completion Notes List

- AC #1: import trocado de `java.nio.file.AccessDeniedException` para `org.springframework.security.access.AccessDeniedException` em produção e no teste; nenhuma alteração de lógica no handler. TDD confirmado (RED por falha de compilação → GREEN).
- AC #2: `handleAccessDeniedException(AuthorizationDeniedException ex, ...)` (linhas 254-266 antes da mudança) não foi tocado — confirmado por `git diff`, que só mostra as duas linhas de import alteradas em cada arquivo.
- Nenhum módulo novo, nenhuma dependência nova, conforme Dev Notes.

### File List

- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` — import `java.nio.file.AccessDeniedException` substituído por `org.springframework.security.access.AccessDeniedException`
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerAccessDeniedTest.java` — mesmo import corrigido

## Suggested Review Order

- O import corrigido — a causa raiz do bug (tipo de filesystem nunca lançado pelo Spring Security, em vez do tipo real).
  [`ExceptionsHandler.java:35`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L35)

- O handler que passa a capturar o tipo certo — lógica interna intocada, só a assinatura do `@ExceptionHandler`.
  [`ExceptionsHandler.java:240`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L240)

- O handler irmão para `AuthorizationDeniedException`, confirmadamente lado a lado sem alteração (AC #2).
  [`ExceptionsHandler.java:255`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L255)

- O teste que expõe o bug antes da correção (TDD/NFR5) e prova a correção depois.
  [`ExceptionsHandlerAccessDeniedTest.java:55`](../../exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerAccessDeniedTest.java#L55)
