# Story 2.7: Unificar o formato de erro em `handleExceptionInternal`, incluindo 404 nativo

Status: done

<!-- baseline_commit: 82f548b4735653b58966ab95f3655c507b74a9eb -->

<!-- Correção pré-implementação: Task 2/Project Structure Notes pedem um teste `@WebMvcTest`/`MockMvc` com `spring.mvc.throw-exception-if-no-handler-found=true` configurado — isso exige um contexto Spring MVC autoconfigurado pelo Boot (a property só é consumida por `WebMvcAutoConfiguration`, não por um `MockMvcBuilders.standaloneSetup()` puro). Confirmado que `exception/pom.xml` hoje só tem `spring-test` (bruto) em escopo `test`, sem `spring-boot-starter-test`/`spring-boot-test-autoconfigure` — `@WebMvcTest` não compilaria. Não é uma decisão arquitetural nova: `jdempotent/pom.xml` e `privacy/pom.xml` já usam `spring-boot-starter-test` em escopo `test`, sem exclusões. Adicionar a mesma dependência (escopo `test`) a `exception/pom.xml`, seguindo esse padrão já estabelecido no reactor. -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor da API,
Eu quero receber o mesmo formato de erro (`ScosProblemDetails`) em qualquer situação, inclusive rota inexistente,
Para não precisar tratar dois formatos diferentes.

## Acceptance Criteria

1. **Given** um teste que reproduz o formato nativo do Spring hoje devolvido para 404/método não suportado/media type inválido, **When** o teste é escrito e falha antes da correção, **Then** `handleExceptionInternal` é sobrescrito para unificar o formato em todos os casos, incluindo 404 de rota inexistente.

## Tasks / Subtasks

- [x] Task 1 — pré-requisito bloqueante, confirmar antes de implementar (AC: #1)
  - [x] **Achado crítico**: hoje não existe, em nenhum lugar do repositório, a propriedade `spring.mvc.throw-exception-if-no-handler-found=true` (confirmado por busca — nenhum `application.yml`/`.properties` do projeto define isso). Sem essa propriedade `true`, o Spring Boot **nunca lança** `NoResourceFoundException`/`NoHandlerFoundException` para rota inexistente — o `DispatcherServlet` despacha para o handler estático padrão, que produz a página de erro Whitelabel/JSON default do Boot **sem passar pelo `ControllerAdvice`**. Sobrescrever só `handleExceptionInternal` não é suficiente para cobrir 404 de rota inexistente se essa propriedade não estiver ligada na aplicação consumidora
  - [x] Documentar essa propriedade como pré-requisito de configuração da aplicação consumidora (README do módulo `exception`/futuro `web`) — este módulo não pode setá-la sozinho por código (é uma propriedade do `DispatcherServlet` da aplicação hospedeira), mas deve alertar claramente que sem ela o 404 de rota inexistente não passa a ser unificado
- [x] Task 2 — teste que reproduz o formato nativo, TDD (NFR5) (AC: #1)
  - [x] Escrever um teste de contexto Spring MVC (`MockMvc`, com `throw-exception-if-no-handler-found=true` configurado no teste) que confirma que hoje 404/`HttpRequestMethodNotSupportedException`/`HttpMediaTypeNotAcceptableException` retornam o corpo nativo do Spring, não um `ScosProblemDetails` — deve falhar contra o comportamento atual
- [x] Task 3: Sobrescrever `handleExceptionInternal` (AC: #1)
  - [x] Em `ExceptionsHandler.java`, adicionar `@Override protected ResponseEntity<Object> handleExceptionInternal(Exception ex, Object body, HttpHeaders headers, HttpStatusCode statusCode, WebRequest request)` — hoje esse método **não existe** na classe (herda o comportamento default de `ResponseEntityExceptionHandler`, que é o que produz o formato nativo para os casos não cobertos pelos `@Override` específicos já existentes: `NoResourceFoundException`, `HttpRequestMethodNotSupportedException`, `HttpMediaTypeNotAcceptableException`, etc.)
  - [x] Reaproveitar `ScosProblemDetails.of(...)`/`enrich(...)` já usados nos outros handlers — o corpo unificado precisa ter o mesmo formato `type/title/status/detail/instance/code/requestId/timestamp`

## Dev Notes

- Esta é a única story do Epic 2 onde o gap real não está só no código do handler, mas numa propriedade de configuração da aplicação hospedeira — não é um detalhe menor, é o que decide se a AC #1 (404 de rota inexistente) é sequer alcançável sem mudança na aplicação consumidora. Sinalizar isso com destaque no PR/README, não deixar implícito.
- `handleExceptionInternal` é o método "coringa" do `ResponseEntityExceptionHandler` — todo `@Override` mais específico já existente (`handleHttpMessageNotReadable`, `handleMethodArgumentNotValid`, `handleHandlerMethodValidationException`) continua funcionando como está; esta story só cobre os casos que **não** têm um `@Override` específico e hoje caem no comportamento default do Spring.
- Não duplicar lógica: se o body/status já vier populado pelo Spring com informação útil, reaproveitar o que der (ex.: o `statusCode` recebido), só trocando o formato de saída para `ScosProblemDetails`.

### Project Structure Notes

- Arquivo modificado: `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` (novo `@Override handleExceptionInternal`).
- Novo teste de contexto MVC (`@WebMvcTest`/`MockMvc`) em `exception/src/test/java/br/com/sawcunhaos/foundation/exception/`.
- Documentação nova/atualizada: alertar sobre `spring.mvc.throw-exception-if-no-handler-found=true` como pré-requisito (README do módulo, ou nota na Story 2.9 quando o módulo virar autoconfiguração).

### References

- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-27-unificar-o-formato-de-erro-em-handleexceptioninternal-incluindo-404-nativo]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `git stash push -- exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` — isolou a mudança da Task 3 para provar a fase RED do TDD (Task 2) contra o comportamento *pré*-fix.
- `mvn -pl exception -am -DskipITs test-compile` (online, sem `-o`) — 1ª tentativa falhou: `package org.springframework.boot.test.autoconfigure.web.servlet does not exist` / `cannot find symbol class WebMvcTest`. Investigado via `curl` no repositório Maven Central: no Spring Boot 4.1.1 (pinado por `scos-bom:1.4.4-SNAPSHOT` → `spring-boot-dependencies.version=4.1.1`), `@WebMvcTest` foi *movido* para um artefato novo e dedicado, `org.springframework.boot:spring-boot-webmvc-test`, com pacote novo `org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest` — não está mais em `spring-boot-test-autoconfigure` nem no pacote `org.springframework.boot.test.autoconfigure.web.servlet` (válido só até Boot 3.x). `spring-boot-starter-test` sozinho (conforme a correção pré-implementação no topo desta story) não é suficiente nesta versão do Boot.
- Corrigido: import do teste ajustado para `org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest`; adicionada dependência `org.springframework.boot:spring-boot-webmvc-test` (escopo `test`) em `exception/pom.xml`, além de `spring-boot-starter-test`.
- `mvn -pl exception -am -DskipITs test-compile` (online) — `BUILD SUCCESS` (compila).
- `mvn -pl exception -am -DskipITs test` (online, ainda com o handler pré-fix stashado) — erro `IllegalState: Unable to find a @SpringBootConfiguration`. Corrigido criando `TestBootConfiguration` (marker `@SpringBootConfiguration` vazio no mesmo pacote do teste — módulo é uma lib, sem classe de aplicação própria).
- Reexecutado — os 3 testes novos rodaram mas com status incorretos (404 em vez de 405/406 para os casos de método/`Accept`). Debug com `.andDo(print())` temporário mostrou que `PingController` nunca foi registrado como bean (`Handler: ResourceHttpRequestHandler`, `Resolved Exception: NoResourceFoundException` mesmo para `POST /ping`) — `@WebMvcTest(controllers = PingController.class)` sozinho não faz component-scan porque o `@SpringBootConfiguration` marker não carrega `@ComponentScan`. Corrigido adicionando `@Import({ExceptionsHandler.class, PingController.class})` (registra o controller explicitamente, sem depender de scan). Bloco de debug (`print()` + teste temporário) removido depois de confirmar a causa.
- `mvn -pl exception -am -DskipITs test` (online, handler ainda pré-fix/stashado) — **fase RED confirmada**: `Tests run: 41, Failures: 3` — as 3 falhas são exatamente as 3 asserções `$.code` dos testes novos (`No value at JSON path "$.code"` / `PathNotFoundException`), com status HTTP já corretos (404/405/406), provando que hoje o corpo é o nativo do Spring (sem `code`/`ScosProblemDetails`) e não o formato unificado.
- `git stash pop` — restaurou o `@Override handleExceptionInternal` (Task 3).
- `mvn -o -pl exception -am -DskipITs test` (comando oficial da story, offline) — **fase GREEN**: `Tests run: 41, Failures: 0, Errors: 0, Skipped: 0` — `BUILD SUCCESS`. Relatório individual (`exception/target/surefire-reports/...ExceptionsHandlerHandleExceptionInternalTest.txt`): `Tests run: 3, Failures: 0, Errors: 0, Skipped: 0`.
- **Pós-revisão de 3 camadas**: `mvn -o -pl core,exception -am -DskipITs test` → `BUILD SUCCESS`, `Tests run: 41, Failures: 0, Errors: 0, Skipped: 0` (mesma contagem — os patches estenderam asserções em testes já existentes, não criaram métodos novos).

### Completion Notes List

- **Task 1 (documentação)**: criado `exception/README.md` (módulo não tinha nenhum README antes — confirmado via `find exception -iname "README*"`). Documenta `spring.mvc.throw-exception-if-no-handler-found=true` como pré-requisito da aplicação consumidora para que 404 de rota inexistente também saia como `ScosProblemDetails`, explica por que este módulo não pode ligar essa propriedade sozinho (é consumida pela `WebMvcAutoConfiguration` do `DispatcherServlet` da aplicação hospedeira, fora do alcance de um `@ControllerAdvice`), e deixa claro que 405/406 (`HttpRequestMethodNotSupportedException`/`HttpMediaTypeNotAcceptableException`) **não** dependem dessa propriedade — já funcionam com o fix da Task 3 independentemente da configuração da aplicação consumidora.
- **Task 2 (teste TDD)**: `ExceptionsHandlerHandleExceptionInternalTest` (`@WebMvcTest(controllers = PingController.class)`) cobre os 3 casos do AC #1 (404 rota inexistente, 405 método não suportado, 406 `Accept` inválido), com `@TestPropertySource(properties = "spring.mvc.throw-exception-if-no-handler-found=true")`. Confirmado falhando (RED) contra o handler pré-fix e passando (GREEN) depois — ver Debug Log acima.
- **Gap de dependência maior que o previsto na correção pré-implementação**: a nota no topo desta story cobria corretamente o gap de `spring-test` bruto → `spring-boot-starter-test`, mas não previa que, na versão real do Spring Boot deste repo (4.1.1, via `scos-bom`), `@WebMvcTest` foi extraído para um artefato novo (`spring-boot-webmvc-test`) com pacote próprio — descoberto empiricamente ao rodar a build (ver Debug Log). Resolvido adicionando essa segunda dependência de teste, sem alterar a decisão original (mantido `spring-boot-starter-test` como a correção pré-implementação pedia, apenas complementado).
- **Ambiguidade resolvida — fixture do `@WebMvcTest`**: como o módulo `exception` é uma biblioteca sem classe `@SpringBootApplication` própria, o bootstrapper de teste do Boot não encontra uma `@SpringBootConfiguration` por busca ascendente de pacote. Resolvido com uma classe marcador vazia (`TestBootConfiguration`, mesmo pacote do teste). Como essa configuração não tem `@ComponentScan`, `@WebMvcTest(controllers = PingController.class)` não registra o controller automaticamente — resolvido com `@Import({ExceptionsHandler.class, PingController.class})`, registrando os dois beans explicitamente em vez de depender de scan.
- **`handleExceptionInternal` (Task 3)**: usa `ScosExceptionCode.GENERIC` (`SCOS-003`) como `code`, mesmo fallback já usado por `handleGenericException` para "erro genérico/não categorizado" — plausível para um catch-all que cobre qualquer exceção sem `@Override` específico, não só 500. `title` é derivado do `HttpStatus.resolve(statusCode.value()).getReasonPhrase()` (cai para `GENERIC.getTitle()` só se o status não for resolvível), e `detail` reaproveita `ex.getMessage()` diretamente (cai para `title` se `null`) — evita duplicar lógica de i18n para um catch-all genérico, conforme pedido nas Dev Notes ("reaproveitar o que der, ex.: o `statusCode` recebido"). Os 3 `@Override`s existentes (`handleHttpMessageNotReadable`, `handleMethodArgumentNotValid`, `handleHandlerMethodValidationException`) e os demais `@ExceptionHandler` não foram tocados.
- Usado `@MockitoBean` (não `@MockBean`, deprecado) para mockar `LocaleService` no teste novo, consistente com a API de bean-override do Spring Framework 7 usada pelo Boot 4.1.1 deste repo.

### Revisão de 3 camadas

Achados triados (blind-hunter, edge-case-hunter, verification-gap):

- **Patch**: `handleExceptionInternal` não replicava o guard `response.isCommitted()` presente na implementação padrão de `ResponseEntityExceptionHandler` que esta story sobrescreve por completo — escrever corpo num response já commitado lançaria `IllegalStateException`. Guard adicionado, espelhando o comportamento original do Spring (loga `WARN` e retorna `null`, deixando o container tratar). Confirmado por blind-hunter.
- **Patch**: o log usava `log.warn(...)` incondicional para qualquer status, inconsistente com o padrão já estabelecido na classe (`logByStatus`, usado por `handleScosException`/`handleScosNoRollbackException`: `WARN` sem stack trace para `4xx`, `ERROR` com stack trace para `5xx`). Reaproveitado `logByStatus` diretamente (já calcula o `HttpStatus` resolvido). Confirmado de forma independente por edge-case-hunter e blind-hunter.
- **Patch**: `detail` só caía para `title` quando `ex.getMessage()` fosse `null`, não quando fosse uma string vazia/em branco não-nula — troca de `!= null` por `!= null && !isBlank()`. Baixa probabilidade prática (as exceções que hoje alcançam este catch-all sempre têm mensagem populada pelo próprio Spring), mas correção barata. Confirmado por edge-case-hunter.
- **Patch**: nenhum teste verificava o header `Allow` no caso 405 (`HttpRequestMethodNotSupportedException`) — o único efeito observável de `handleExceptionInternal` repassar `headers`, já que é o único handler da classe que usa `.headers(headers)`. Um "ajuste de consistência" futuro (remover essa chamada para bater com o padrão dos outros handlers) derrubaria o header silenciosamente sem quebrar nenhum teste existente. Asserção `header().string("Allow", containsString("GET"))` adicionada. Confirmado de forma independente por verification-gap (com demonstração concreta) e blind-hunter.
- **Patch**: nenhum teste verificava `Content-Type: application/problem+json`, o contrato central documentado da classe/módulo. Asserção adicionada ao caso 404. Confirmado por blind-hunter.
- **Patch**: `ScosExceptionCode.GENERIC`'s Javadoc afirmava categoricamente "(HTTP 500)", mas esta story passou a usar o mesmo código também para 404/405/406/etc via `handleExceptionInternal` — Javadoc corrigido para descrever os dois usos (fallback de exceção não tratada, HTTP 500; e catch-all de `handleExceptionInternal`, status variável). Confirmado por blind-hunter.
- **Patch**: o README raiz (seção "SCOS Foundation Exception") não mencionava o pré-requisito `spring.mvc.throw-exception-if-no-handler-found=true` nem linkava o novo `exception/README.md` — um consumidor que só lê a documentação principal não descobriria esse requisito crítico. Seção atualizada com link e resumo, seguindo o mesmo padrão já usado para `privacy/README.md` (linha 129 do README raiz). Confirmado por blind-hunter.
- **Rejeitado com evidência**: blind-hunter e edge-case-hunter (independentemente) apontaram que `title`/`detail` não passam por `localeService` (ao contrário de todo outro handler da classe, incluindo `handleGenericException`), quebrando i18n neste catch-all especificamente. As Dev Notes desta própria story pedem explicitamente: "reaproveitar o que der (ex.: o `statusCode` recebido), só trocando o formato de saída para `ScosProblemDetails`" — reaproveitar `HttpStatus.getReasonPhrase()`/`ex.getMessage()` diretamente é exatamente essa instrução seguida à risca, não uma omissão. Introduzir i18n aqui exigiria decidir uma convenção de chave nova (mesma classe de decisão já adiada na Story 2.6), fora do escopo desta story.
- **Rejeitado com evidência**: edge-case-hunter e blind-hunter (independentemente) apontaram risco de vazamento de mensagens internas de exceções do Spring MVC (`ex.getMessage()` cru) para o cliente da API. Mesma justificativa das Dev Notes acima — reaproveitar `ex.getMessage()` é comportamento pedido explicitamente. Adicionalmente, as exceções que de fato alcançam este catch-all no uso normal (`NoResourceFoundException`, `HttpRequestMethodNotSupportedException`, `HttpMediaTypeNotAcceptableException`) já têm mensagens padronizadas e seguras para exposição externa por design do próprio Spring — não é um risco novo introduzido por esta story, é o mesmo texto que o Spring já exibiria por padrão sem este handler.
- **Rejeitado com evidência**: blind-hunter apontou duplicação de `spring-test` (bruto) e `spring-boot-starter-test` (que já traz `spring-test` transitivamente) em `exception/pom.xml`. `jdempotent/pom.xml` já tem exatamente a mesma duplicação — convenção pré-existente no reactor, não introduzida por esta story.
- **Rejeitado com evidência**: blind-hunter apontou ausência de entrada no `CHANGELOG.md` para uma mudança de formato de resposta potencialmente "breaking". Confirmado (revisão da Story 2.3) que nenhuma story do Épico 2 até agora (2.1-2.6) recebeu entrada de changelog para suas correções — convenção já estabelecida para bug fixes deste épico, não uma lacuna específica desta story.
- **Rejeitado com evidência**: blind-hunter sugeriu um teste de regressão confirmando que os 3 `@Override`s específicos pré-existentes continuam tendo precedência sobre o novo catch-all genérico. Isso testaria o próprio mecanismo de despacho do Spring (`@ExceptionHandler`/`@Override` mais específico vence), não lógica desta biblioteca — já implicitamente exercitado pelos 38 outros testes pré-existentes que invocam os handlers específicos diretamente e recebem as respostas no formato esperado deles.
- **Rejeitado com evidência**: blind-hunter apontou que o Debug Log só documenta builds com `-pl exception -am` (módulo isolado), sem evidência de build de reactor completo confirmando que as 2 novas dependências de teste não causam divergência de versão em `jdempotent`/`privacy` (que também usam `spring-boot-starter-test`). Dependências de escopo `test` são locais ao classpath de teste do próprio módulo — não existe mecanismo pelo qual afetem o build de outro módulo do reactor, que já declara suas próprias dependências de teste de forma independente via o mesmo BOM.

### File List

- `exception/pom.xml` (modificado — 2 novas dependências de teste: `spring-boot-starter-test`, `spring-boot-webmvc-test`)
- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` (modificado — novo `@Override handleExceptionInternal`; revisão adicionou guard `isCommitted()`, log via `logByStatus`, fallback de `detail` para string em branco)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ScosExceptionCode.java` (modificado na revisão — Javadoc de `GENERIC` corrigido)
- `README.md` (modificado na revisão — seção "SCOS Foundation Exception" linka `exception/README.md` e resume o pré-requisito)
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerHandleExceptionInternalTest.java` (novo; revisão adicionou asserções de `Content-Type` e header `Allow`)
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/TestBootConfiguration.java` (novo)
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/support/PingController.java` (novo)
- `exception/README.md` (novo)

## Suggested Review Order

**O fix (o catch-all novo)**

- `handleExceptionInternal` — guard `isCommitted()`, log via `logByStatus` (consistente com o resto da classe), `code`/`type` sempre `GENERIC`/`SCOS-003` (única opção semanticamente plausível entre os 10 códigos existentes para um catch-all de status variável).
  [`ExceptionsHandler.java:196`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java#L196)

- Javadoc de `GENERIC` corrigido para descrever os dois usos (500 fixo vs. catch-all de status variável).
  [`ScosExceptionCode.java:33`](../../core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ScosExceptionCode.java#L33)

**O pré-requisito de configuração (a parte não-óbvia desta story)**

- `exception/README.md` — por que a propriedade `spring.mvc.throw-exception-if-no-handler-found` não pode ser ligada pelo próprio módulo, e o que funciona com/sem ela.
  [`exception/README.md`](../../exception/README.md)

**Os testes**

- `ExceptionsHandlerHandleExceptionInternalTest` — 3 casos (404/405/406) via `@WebMvcTest` real, não mocks; verificado RED contra o handler pré-fix antes do GREEN (ver Debug Log). Revisão adicionou `Content-Type`/`Allow`.
  [`ExceptionsHandlerHandleExceptionInternalTest.java`](../../exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerHandleExceptionInternalTest.java)
