# Story 2.4: Padronizar log por faixa de status HTTP

Status: done

<!-- baseline_commit: e4a1b8786fa5872b4b9a7dcc3f7f37ad60b7b658 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

<!-- Correção pré-implementação: (1) `utils/src/main/java/br/com/sawcunhaos/foundation/utils/listener/ScosOnStartupListener.java` (Task 3, References) não existe mais — o módulo `utils` foi removido no Épico 1 (Story 1.14); a classe foi para `spring/src/main/java/br/com/sawcunhaos/foundation/spring/listener/ScosOnStartupListener.java` já na Story 1.8. A conclusão de escopo da Dev Notes (não mexer nela, é de outro módulo) continua válida, só o caminho estava desatualizado. (2) A contagem "só mais 1 outra classe usa @Log4j2" também está desatualizada: hoje são 5 classes (`ExceptionsHandler.java` — alvo desta story —, `spring/.../ScosOnStartupListener.java`, e mais 3 criadas na Story 1.15 do Épico 1: `jdempotent/.../JdempotentAnnotationCountListener.java`, `audit/.../AuditableAnnotationCountListener.java`, `exception/.../listener/ValidationAnnotationCountListener.java`). Não muda o escopo da Task 3 (ainda é só `ExceptionsHandler.java`), só corrige a premissa citada como justificativa. (3) Os números de linha do Task 1 (83, 115, 146, 175, 208, 223, 237, 244, 258, 272) estão desatualizados — as Stories 2.1-2.3 já modificaram este mesmo arquivo (novo import, novo handler `handleMethodNotImplementedException`). Linhas reais confirmadas via grep antes de despachar a implementação: 84, 116, 147, 191, 224, 239, 253, 260, 274, 290, 302 (11 handlers, não 10 — o novo de `MethodNotImplementedException` da Story 2.3 também precisa da faixa correta de log). -->

## Story

Como operador monitorando a aplicação,
Eu quero que erros `4xx` logem em `WARN` sem stack trace e `5xx` em `ERROR` com stack trace,
Para não poluir alertas com ruído de erro de cliente.

## Acceptance Criteria

1. **Given** exceções mapeadas para diferentes faixas de status, **When** cada uma é tratada pelo handler, **Then** `4xx` loga em `WARN` sem stack trace, `5xx` em `ERROR` com stack trace, e `ScosNoContentException` (204) em `DEBUG`.
2. **And** o handler genérico (fallback sem tipo específico) é o único que loga `ERROR` incondicionalmente.
3. **And** todo uso de Log4j2 direto é substituído por `@Slf4j`.

## Tasks / Subtasks

- [x] Task 1: Levantar o estado atual de log em `ExceptionsHandler.java` (AC: #1, #2)
  - [x] Hoje **todo** handler chama `log.error("handleSecurity - <Nome>: ", ex)` incondicionalmente, incluindo os que respondem `403`/`400`/`204`/`501` — nenhuma diferenciação por faixa de status existe (linhas atuais, confirmadas via grep antes desta story: 84, 116, 147, 191, 224, 239, 253, 260, 274, 290, 302 — 11 handlers, não os 10 do levantamento original; a Story 2.3 do Épico 2 adicionou `handleMethodNotImplementedException` desde então)
  - [x] Mapear cada handler para sua faixa de status real: `handleHttpMessageNotReadable`→400, `handleMethodArgumentNotValid`→400, `handleHandlerMethodValidationException`→400, `handleConstraintViolationException`→400, `handleScosException`→variável (`resolveHttpCode(exception.getHttpCode())`, pode ser 4xx ou 5xx conforme o `ExceptionCode` usado), `handleScosNoRollbackException`→variável (mesmo padrão), `handleScosNoContentException`→204, `handleAccessDeniedException` (ambos overloads)→403, `handleMethodNotImplementedException`→501 (**novo desde o levantamento original, Story 2.3** — fixo 5xx, precisa `ERROR` com stack trace), `handleGenericException`→500
- [x] Task 2: Aplicar o nível de log correto por faixa (AC: #1, #2)
  - [x] Para os handlers de status fixo 4xx (validação, access denied): `log.warn(...)` sem passar a exceção como último argumento (evita stack trace no append padrão do SLF4J)
  - [x] Para `handleScosNoContentException`: `log.debug(...)`
  - [x] Para `handleScosException`/`handleScosNoRollbackException` (status dinâmico via `resolveHttpCode`): decidir o nível **depois** de resolver o `HttpStatus` — `WARN` sem stack trace se `4xx`, `ERROR` com stack trace se `5xx`. Extrair essa decisão para um método privado único (ex.: `logByStatus(HttpStatus status, String context, Throwable ex)`) reaproveitado pelos dois handlers, para não duplicar a lógica de faixa
  - [x] `handleGenericException` continua `log.error(...)` incondicional (é o único fallback sem tipo específico, AC #2) — não precisa da lógica de faixa, seu status é sempre 500
- [x] Task 3: Substituir `@Log4j2` por `@Slf4j` (AC: #3)
  - [x] `ExceptionsHandler.java` usa `lombok.extern.log4j.Log4j2` (import linha 28, anotação linha 70) — trocar para `lombok.extern.slf4j.Slf4j` (padrão já usado em 16 outras classes do repo; só mais 1 outra classe no repo inteiro usa `@Log4j2` hoje: `utils/.../listener/ScosOnStartupListener.java`, que pertence ao módulo `spring` do Epic 1 e está **fora do escopo desta story** — confirmar com quem mantém o épico antes de tocar nela, já que o AC não delimita módulo)
- [x] Task 4: Testes (AC: #1, #2)
  - [x] Cobrir com teste (usando `ListAppender`/captura de log, ou verificação de nível via mock de logger se o padrão do repo já suportar) que um handler 4xx não inclui stack trace e um handler 5xx inclui

## Dev Notes

- **Estado real confirmado**: hoje não existe nenhuma diferenciação de nível de log no arquivo — é uma padronização genuína, não uma correção de bug pontual.
- `handleScosException`/`handleScosNoRollbackException` são os únicos dois casos onde o status HTTP **não** é fixo no código (vem de `exception.getHttpCode()` via `resolveHttpCode`) — por isso a decisão do nível de log tem que acontecer depois de resolver o status, não pode ser hardcoded por handler como nos demais.
- Escopo desta story é só o módulo `exception` (futuro `web`, Epic 1 Story 1.12) — o `@Log4j2` de `ScosOnStartupListener.java` pertence ao módulo `spring` e não tem relação com o tratamento de erro HTTP; tratá-lo aqui seria misturar dois módulos numa mesma story. Documentado como decisão consciente de escopo, não omissão.
- Não introduzir uma abstração de "log level resolver" genérica reaproveitável por todo o projeto — o método privado da Task 2 resolve só o caso concreto de `ScosException`/`ScosNoRollbackException` deste handler; generalizar além disso não foi pedido pelo epics.md.

### Project Structure Notes

- Arquivo modificado: `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` (import, todas as chamadas `log.error`, novo método privado de decisão de nível).
- Nenhum módulo novo.

### References

- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java]
- [Source: utils/src/main/java/br/com/sawcunhaos/foundation/utils/listener/ScosOnStartupListener.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-24-padronizar-log-por-faixa-de-status-http]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -pl exception -am -DskipITs test -Dtest='ExceptionsHandler*Test' -Dsurefire.failIfNoSpecifiedTests=false` → todas as 7 classes de teste de `ExceptionsHandler*` existentes no módulo, incluindo a nova `ExceptionsHandlerLogLevelTest` (`tests="2" errors="0" skipped="0" failures="0"`).
- `mvn -pl exception -am -DskipITs test` (suíte completa do módulo) → `BUILD SUCCESS`, sem falhas.
- **Pós-revisão de 3 camadas**: `ExceptionsHandlerLogLevelTest` estendida de 2 para 12 casos (cobertura confirmada faltante pelos 3 revisores — ver abaixo). `mvn -o -pl core,exception -am -DskipITs test -Dtest='ExceptionsHandler*Test' -Dsurefire.failIfNoSpecifiedTests=false` → `Tests run: 23, Failures: 0, Errors: 0, Skipped: 0`. `mvn -o -pl exception -am -DskipITs test` (suíte completa do módulo) → `Tests run: 27, Failures: 0, Errors: 0, Skipped: 0`, `BUILD SUCCESS`.

### Completion Notes List

- AC #1/#2 (Task 2): os 6 handlers de status HTTP fixo em faixa `4xx` (`handleHttpMessageNotReadable`, `handleMethodArgumentNotValid`, `handleHandlerMethodValidationException`, `handleConstraintViolationException`, `handleAccessDeniedException` × 2 overloads) trocaram `log.error("...", ex)` por `log.warn("...: {}", ex.getMessage())` — a exceção deixa de ser o último argumento, então o SLF4J não anexa stack trace.
- `handleScosNoContentException` (204) trocou para `log.debug(...)`, mantendo a exceção como argumento (a AC não exige omitir stack trace nesse nível, só `WARN`/`ERROR`).
- `handleMethodNotImplementedException` (501, fixo 5xx) e `handleGenericException` (500, fallback único) permaneceram `log.error("...", ex)` incondicional — já estavam corretos, nenhuma mudança de comportamento necessária ali.
- `handleScosException`/`handleScosNoRollbackException`: extraído o método privado único `logByStatus(HttpStatus status, String context, Throwable ex)`, chamado depois de resolver `resolveHttpCode(exception.getHttpCode())` uma única vez (armazenado em variável local `status`, reaproveitada também no corpo do `ProblemDetail` e no `ResponseEntity.status(...)`, eliminando a dupla chamada a `resolveHttpCode` que já existia antes desta story). `logByStatus` usa `status.is4xxClientError()` como critério: `WARN` sem stack trace se `4xx`, `ERROR` com stack trace em qualquer outro caso (`5xx`). **Correção pós-revisão (blind-hunter confirmado)**: esta nota originalmente afirmava que o fallback de `resolveHttpCode` para um `httpCode` não resolvível também logava `ERROR` — incorreto. `resolveHttpCode` cai em `HttpStatus.BAD_REQUEST` (400) quando `httpCode` não resolve, e 400 é `4xx`, então esse caso loga `WARN` como qualquer outro 4xx. Texto e o Javadoc de `logByStatus` corrigidos; teste de regressão cobrindo exatamente esse caminho adicionado (Task 4).
- AC #3 (Task 3): `import lombok.extern.log4j.Log4j2` → `import lombok.extern.slf4j.Slf4j`, `@Log4j2` → `@Slf4j` em `ExceptionsHandler.java`. Escopo respeitado — nenhuma das outras 4 classes que usam `@Log4j2` no repo (`ValidationAnnotationCountListener` no mesmo módulo `exception`, e as de `jdempotent`/`audit`/`spring`) foi tocada, conforme decisão de escopo documentada nas Dev Notes.
- Task 4: novo `ExceptionsHandlerLogLevelTest.java`, usando `ch.qos.logback.core.read.ListAppender` anexado ao logger logback de `ExceptionsHandler` (disponível transitivamente via `spring-boot-starter-web`/`spring-boot-starter-logging`, sem nova dependência). Dois casos, ambos via `handleScosException` com um `ExceptionCode` anônimo de teste (`httpCode` 400 e 500, já que nenhum `ScosExceptionCode` real de produção mapeia para 5xx via `getHttpCode()` — o `default` da interface é sempre 400): 4xx → nível `WARN` e `event.getThrowableProxy() == null`; 5xx → nível `ERROR` e `event.getThrowableProxy().getClassName()` igual à classe da exceção lançada.
- **Estendido pós-revisão de 3 camadas** (achados confirmados pelos 3 revisores, ver seção abaixo): `ExceptionsHandlerLogLevelTest` passou de 2 para 12 casos, agora cobrindo diretamente todos os handlers tocados por esta story — os 6 handlers `4xx` fixos (`handleHttpMessageNotReadable`, `handleMethodArgumentNotValid`, `handleHandlerMethodValidationException`, `handleConstraintViolationException`, `handleAccessDeniedException` × 2 overloads, incluindo o overload de `AuthorizationDeniedException`, que não tinha nenhuma cobertura de teste, nem de resposta HTTP nem de log), `handleScosNoRollbackException` (4xx/5xx via `logByStatus`, zero cobertura antes), `handleScosNoContentException` (`DEBUG`, zero cobertura antes) e o caminho de fallback de `resolveHttpCode` para `httpCode` não resolvível (→ 400 → `WARN`, ver correção acima). Helper privado `assertLogged(Level, boolean expectStackTrace)` extraído para evitar duplicação entre os 12 casos; também substitui `appender.list.get(0)` por `assertFalse(appender.list.isEmpty())` antes do `get`, evitando um `IndexOutOfBoundsException` opaco caso o evento de log nunca chegue ao appender.
- Nenhum módulo novo, nenhuma dependência nova adicionada ao `pom.xml`.

### Revisão de 3 camadas

Achados triados (blind-hunter, edge-case-hunter, verification-gap):

- **Patch**: os 6 handlers `4xx` fixos convertidos para `log.warn` não tinham nenhuma asserção de nível de log — só o corpo da resposta HTTP era verificado em `ExceptionsHandlerValidationTest`/`ExceptionsHandlerAccessDeniedTest`. Cobertura adicionada em `ExceptionsHandlerLogLevelTest` (confirmado pelos 3 revisores).
- **Patch**: `handleScosNoRollbackException` e `handleScosNoContentException` tinham cobertura de teste zero em todo o repositório. Testes adicionados.
- **Patch**: Completion Notes e o Javadoc de `logByStatus` afirmavam incorretamente que o fallback de `resolveHttpCode` (código não resolvível) logava `ERROR` — o código real cai em `WARN` (fallback é 400, `4xx`). Documentação corrigida, teste de regressão adicionado (blind-hunter).
- **Patch**: Debug Log afirmava "9 classes de teste" quando só existem 7 classes `ExceptionsHandler*Test`. Corrigido para 7 (blind-hunter e verification-gap, independentemente).
- **Patch**: `appender.list.get(0)` sem `assertFalse(isEmpty())` antes falharia com `IndexOutOfBoundsException` opaco se o evento de log nunca chegasse ao appender. Guard adicionado (edge-case-hunter e blind-hunter, independentemente).
- **Patch**: 3 linhas em branco consecutivas deixadas após o comentário de correção pré-implementação, no topo do arquivo. Removidas (blind-hunter).
- **Adiado para `deferred-work.md`**: `logByStatus` roteia qualquer status que não seja `4xx` para o ramo `ERROR`/com-stack-trace — incluindo um hipotético `1xx`/`2xx`/`3xx`, caso algum `ExceptionCode` algum dia retorne um `httpCode` fora da faixa de erro (edge-case-hunter). Nenhum `ScosExceptionCode` de produção faz isso hoje (todos são `4xx`, exceto `NOT_IMPLEMENTED` que é tratado por outro handler fixo), e a interface `ExceptionCode.getHttpCode()` tem `default` 400 — cenário sem caminho de produção conhecido. Redesenhar `logByStatus` para uma terceira faixa não foi pedido pela AC; registrado para não se perder caso um `ExceptionCode` futuro use uma faixa não-erro.
- **Rejeitado com evidência**: o comentário de correção pré-implementação (topo do arquivo) "agrupa 3 correções não relacionadas num único parágrafo denso" (blind-hunter) — é o mesmo padrão usado nas Stories 2.2/2.3 desta mesma sprint; convenção já estabelecida, não um problema desta story especificamente.
- **Rejeitado com evidência**: o comentário `baseline_commit` "não está documentado" (blind-hunter) — presente em todas as stories do Épico 2 desde a 2.1, é uma convenção do próprio workflow BMAD, não algo introduzido ou omitido por esta story.
- **Rejeitado com evidência**: "o diff não demonstra que `ch.qos.logback` está no classpath do módulo `exception`" (blind-hunter) — o próprio teste (`ExceptionsHandlerLogLevelTest`, já existente antes desta revisão) importa e usa `ListAppender`/`Logger`/`ILoggingEvent` diretamente e compila/roda com sucesso; a suíte completa do módulo (`mvn -pl exception -am test`) confirma isso na prática, não é uma afirmação não verificada.

### File List

- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` — `@Log4j2`→`@Slf4j`; `log.error`→`log.warn` (sem stack trace) nos 6 handlers 4xx fixos; `log.debug` em `handleScosNoContentException`; novo método privado `logByStatus(HttpStatus, String, Throwable)` reaproveitado por `handleScosException`/`handleScosNoRollbackException`, que agora resolvem `HttpStatus` uma única vez em variável local; Javadoc de `logByStatus` corrigido na revisão (fallback não-resolvível → `WARN`, não `ERROR`).
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerLogLevelTest.java` — cobre a política de nível de log por faixa de status via `ListAppender`; estendido na revisão de 2 para 12 casos (ver "Revisão de 3 camadas").

## Suggested Review Order

**A decisão de nível por faixa**

- `logByStatus(HttpStatus, String, Throwable)` — critério único `status.is4xxClientError()` reaproveitado por `handleScosException`/`handleScosNoRollbackException`; Javadoc corrigido na revisão para não afirmar que o fallback de `resolveHttpCode` loga `ERROR` (na verdade loga `WARN`, é `4xx`).
  [`ExceptionsHandler.java:329`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L329)

- Os 6 handlers `4xx` fixos que trocaram `log.error(ex)` por `log.warn(ex.getMessage())` — a exceção deixa de ser o último argumento, então o SLF4J não anexa stack trace.
  [`ExceptionsHandler.java:84`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L84)

- `handleScosNoContentException` (204) → `log.debug(...)`, mantendo a exceção como argumento.
  [`ExceptionsHandler.java:253`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L253)

**Os testes (o ponto mais revisado nesta story)**

- `ExceptionsHandlerLogLevelTest` — 12 casos: `ScosException`/`ScosNoRollbackException` 4xx/5xx, o fallback de `resolveHttpCode` não resolvível, `ScosNoContentException` (`DEBUG`), e os 6 handlers `4xx` fixos incluindo o overload de `AuthorizationDeniedException` (sem cobertura de teste alguma antes desta story).
  [`ExceptionsHandlerLogLevelTest.java`](../../exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerLogLevelTest.java)

- Helper `assertLogged(Level, boolean)` — guarda `assertFalse(appender.list.isEmpty())` antes de indexar, evitando `IndexOutOfBoundsException` opaco.
  [`ExceptionsHandlerLogLevelTest.java:99`](../../exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerLogLevelTest.java#L99)

**A troca de logger (AC #3)**

- `@Log4j2` → `@Slf4j`, escopo limitado a `ExceptionsHandler.java` conforme Dev Notes.
  [`ExceptionsHandler.java:71`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L71)
