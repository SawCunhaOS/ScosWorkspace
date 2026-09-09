# Story 2.9: Mover a tradução HTTP do `exception` para o `web` e registrar via autoconfiguração

Status: done

<!-- baseline_commit: 562ce4ac3667fc2b98f0ac3ddb938b7b38c51593 -->

<!-- Correção pré-implementação (substancial): a Task 1 lista só 4 classes principais e ~6 testes — a lista real é maior.

(1) **5 classes principais, não 4** — falta `ValidationAnnotationCountListener.java` (`exception/src/main/java/.../exception/listener/`) na lista da Task 1. Ela precisa mover também: a Task 3 exige que `exception/src/main/java` fique vazio antes de remover o módulo, e ela é a única classe principal não coberta pela Story 2.8 nem pela Task 1 desta story. Mover para `web/src/main/java/br/com/sawcunhaos/foundation/web/listener/ValidationAnnotationCountListener.java` (mesmo padrão de subpacote de `JdempotentAnnotationCountListener`/`AuditableAnnotationCountListener` nos módulos irmãos). **Ela continua um `@Component` simples** (descoberta via `@ComponentScan`, não via `AutoConfiguration.imports`) — mover não deve trocar seu mecanismo de ativação, só o pacote; isso é diferente do que a Task 2 pede para `ExceptionsHandler` especificamente.

(2) **15 arquivos de teste, não ~6** — a lista real completa (confirmada via `find exception/src/test`): `ExceptionsHandlerAccessDeniedTest`, `ExceptionsHandlerHandleExceptionInternalTest`, `ExceptionsHandlerInternalErrorTest`, `ExceptionsHandlerJackson3DeserializationTest`, `ExceptionsHandlerLogLevelTest`, `ExceptionsHandlerMdcTest`, `ExceptionsHandlerMethodNotImplementedTest`, `ExceptionsHandlerResolveTitleTest`, `ExceptionsHandlerScosExceptionTest`, `ExceptionsHandlerValidationTest`, `listener/ValidationAnnotationCountListenerTest`, `listener/empty/SampleNoValidationUsage`, `listener/sample/SampleValidationUsage`, `model/ScosFieldErrorTest`, mais os fixtures de suporte da Story 2.7 (`support/PingController.java`, `TestBootConfiguration.java`, usados pelo `@WebMvcTest`). Todos precisam mover junto, preservando a estrutura de subpacote relativa (`listener/`, `model/`, `support/`).

(3) **Dependência `mapstruct` em `exception/pom.xml` não é usada por nada** (confirmado via grep — nenhuma classe de `exception/src/main` importa `mapstruct`/`@Mapper`) — não carregar para `web/pom.xml`, é peso morto histórico.

(4) **Dependências que `web` de fato precisa ganhar** (confirmado via grep de uso real em `exception/src/main`, comparado com o que `web/pom.xml` já tem hoje): `spring-security-core` (usado por `ExceptionsHandler` para `AccessDeniedException`/`AuthorizationDeniedException`), `spring-boot-starter-validation` (usado por `ExceptionsHandler`/`ExceptionUtils` para `jakarta.validation.*`), `scos-foundation-validation-api` (usado por `ValidationAnnotationCountListener` para `@CPF`/`@CNPJ`/`@TaxIdentifier`/`@ZipCode`) — todas em escopo `compile`. Em escopo `test`: `spring-boot-starter-test` + `spring-boot-webmvc-test` (necessárias para `ExceptionsHandlerHandleExceptionInternalTest`, que usa `@WebMvcTest` — Boot 4.1.1 partiu `@WebMvcTest` num artefato dedicado, ver Story 2.7 para o histórico completo desse gap).

(5) **`web` não tem `ArchitectureTest`/regra ArchUnit local hoje** (confirmado via `find`) — sem risco de conflito com as novas classes/dependências.

(6) **Consumidores de `scos-foundation-exception` a repontar (Task 3, 2º item)**: `pom.xml` raiz (linha `&lt;module&gt;exception&lt;/module&gt;` + entrada em `dependencyManagement`, ambas removidas junto com o diretório) e `archtest/pom.xml` (dependência `scope=test` em `scos-foundation-exception`, sem nenhum import direto — usada só para escaneamento ArchUnit de classpath, mesma razão pela qual `archtest` já depende de todo módulo do reactor). `archtest` **já depende de `scos-foundation-web`** (confirmado) — não precisa repontar para lugar nenhum, só remover a linha agora redundante de `scos-foundation-exception`. `audit/pom.xml` já foi repontado na Story 2.8 (confirmado, zero referência restante) — nada a fazer aí nesta story. -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor da API,
Eu quero que o tratamento de erro HTTP seja ativado automaticamente ao importar o módulo `web`,
Para não precisar de código de integração manual.

## Acceptance Criteria

1. **Given** `ExceptionsHandler`, `ScosProblemDetails`, `ScosFieldError`, `ExceptionUtils` já corrigidos e testados, **When** são movidos para o módulo `web` (criado no Epic 1) e registrados via `AutoConfiguration.imports`, **Then** o handler é ativado por padrão via `@ConditionalOnProperty(scos.web.error-handler.enabled, matchIfMissing=true)` e ordenado com `@Order(Ordered.LOWEST_PRECEDENCE)`.
2. **And** `scos-foundation-exception` deixa de existir como módulo e sai do reactor Maven.

## Tasks / Subtasks

- [x] Task 1: Mover as 5 classes para `web` (AC: #1)
  - [x] Mover `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java`, `exception/.../model/ScosProblemDetails.java`, `exception/.../model/ScosFieldError.java`, `exception/.../utils/ExceptionUtils.java` para `web/src/main/java/br/com/sawcunhaos/foundation/web/...` (Story 1.12, Epic 1)
  - [x] Mover também `exception/.../listener/ValidationAnnotationCountListener.java` para `web/.../web/listener/ValidationAnnotationCountListener.java` (não listada na Task 1 original, mas necessária para `exception/src/main/java` ficar vazio — permanece `@Component` simples, sem AutoConfiguration wrapper)
  - [x] Ajustar imports internos para os tipos movidos ao `core` na Story 2.8 (`ScosException`, `ExceptionCode`, `LocaleService`, `ScosNoContentException`, `ScosNoRollbackException`, `MethodNotImplementedException`) e para os próprios tipos movidos nesta story (`br.com.sawcunhaos.foundation.exception.*` → `br.com.sawcunhaos.foundation.web.*`)
  - [x] Mover os 15 arquivos de teste (não ~6): `ExceptionsHandlerAccessDeniedTest`, `ExceptionsHandlerHandleExceptionInternalTest`, `ExceptionsHandlerInternalErrorTest`, `ExceptionsHandlerJackson3DeserializationTest`, `ExceptionsHandlerLogLevelTest`, `ExceptionsHandlerMdcTest`, `ExceptionsHandlerMethodNotImplementedTest`, `ExceptionsHandlerResolveTitleTest`, `ExceptionsHandlerScosExceptionTest`, `ExceptionsHandlerValidationTest`, `listener/ValidationAnnotationCountListenerTest`, `listener/empty/SampleNoValidationUsage`, `listener/sample/SampleValidationUsage`, `model/ScosFieldErrorTest`, `support/PingController.java`, `TestBootConfiguration.java`
- [x] Task 2: Registrar via `AutoConfiguration.imports` (AC: #1)
  - [x] `web` hoje não tem `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` — criar `web/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` seguindo o padrão já usado em `jdempotent`/`audit`/`privacy` (um FQN de classe de configuração por linha)
  - [x] `ExceptionsHandler` é hoje um `@ControllerAdvice` direto (não uma `@Configuration` com `@Bean`) — para registrar via `AutoConfiguration.imports` com `@ConditionalOnProperty` e `@Order`, envolvê-lo numa classe `@AutoConfiguration` dedicada (ex.: `ScosWebErrorHandlerAutoConfiguration`) que declara `ExceptionsHandler` como `@Bean` com `@ConditionalOnProperty(prefix = "scos.web.error-handler", name = "enabled", matchIfMissing = true)` e `@Order(Ordered.LOWEST_PRECEDENCE)` — sem alterar a lógica interna do `ExceptionsHandler` em si
- [x] Task 3: Remover o módulo `exception` do reactor (AC: #2)
  - [x] Depois que as Stories 2.8 e 2.9 esvaziarem `exception/src/main/java` e `exception/src/test/java` por completo, remover `<module>exception</module>` e a entrada `scos-foundation-exception` de `dependencyManagement` do `pom.xml` raiz, e apagar o diretório `exception/` inteiro
  - [x] Atualizar `archtest/pom.xml` (única outra referência restante a `scos-foundation-exception`, dependência `scope=test` usada só para escaneamento ArchUnit) — removida sem repontar para lugar nenhum, pois `archtest` já depende de `scos-foundation-web` separadamente. `audit/pom.xml` já foi repontado na Story 2.8 (confirmado, zero referência restante) — nada a fazer aí

## Dev Notes

- Depende diretamente da Story 2.8 (classes de domínio já em `core`) e da Story 1.12 do Epic 1 (`web` já existe, dependendo de `core`+`cache`+`privacy`).
- **Padrão de referência já existente no repo** para `AutoConfiguration.imports`: `jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` — reaproveitar o mesmo formato (uma linha, FQN completo), não inventar um novo.
- Esta story depende também da Story 2.7 (200/404 unificado): mover o handler antes de resolver o gap do `throw-exception-if-no-handler-found` deixaria a Story 2.7 sem onde aterrissar sua correção — a ordem correta é 2.1–2.7 (correções de comportamento) antes de 2.8–2.9 (movimentação de módulo), para não misturar commit de "mover" com commit de "corrigir" na mesma classe (NFR2).
- `@ConditionalOnProperty(matchIfMissing = true)` significa: se a aplicação consumidora não setar `scos.web.error-handler.enabled`, o handler fica ativo por padrão (comportamento atual, sem regressão) — só desativa explicitamente com `scos.web.error-handler.enabled=false`.

### Project Structure Notes

- Módulo `web` (Epic 1, Story 1.12) ganha: `ExceptionsHandler`, `ScosProblemDetails`, `ScosFieldError`, `ExceptionUtils`, mais a nova classe `ScosWebErrorHandlerAutoConfiguration`.
- Novo arquivo: `web/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`.
- Módulo `exception` removido do reactor Maven (`pom.xml` raiz) e do disco.
- `audit/pom.xml` perde a dependência `scos-foundation-exception` (já repontada para `core` na Story 2.8; nada resta que justifique a dependência em `exception`).

### References

- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java]
- [Source: jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports]
- [Source: _bmad-output/implementation-artifacts/1-12-extrair-o-módulo-web.md]
- [Source: _bmad-output/implementation-artifacts/2-8-mover-o-contrato-de-domínio-do-exception-para-o-core.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-29-mover-a-tradução-http-do-exception-para-o-web-e-registrar-via-autoconfiguração]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `git mv` of 5 main classes + 15 test/fixture files from `exception/src/...` to `web/src/...` (preserving relative subpackages), followed by `sed -i 's/br\.com\.sawcunhaos\.foundation\.exception/br.com.sawcunhaos.foundation.web/g'` over exactly those 20 moved files to rewrite package declarations and cross-file imports. Verified afterward with `grep -rl "foundation\.exception" web/src` → no matches.
- `mvn -o -pl core,web,archtest -am -DskipITs test` (exact command from the story spec): **BUILD FAILURE** — not caused by this story's changes. `core`, `web`, `feign`, `privacy`, `audit`, etc. all SUCCESS; `jdempotent` fails with `Tests run: 40, Failures: 0, Errors: 3` — the 3 errors are `PrimeNumbersJdempotentEnableTest`/`PrimeNumbersJdempotentDisableTest`, both Testcontainers/Docker-Compose Redis Sentinel tests, failing with `ContainerLaunchException: Timed out waiting for container port to open`. Reproduced identically with `dangerouslyDisableSandbox: true` (docker daemon present, `docker version`/`docker compose version` both resolve) — confirmed environmental (sandboxed container networking), not a regression from this story: the `jdempotent` module and its tests were not touched by Story 2.9. Because `archtest` depends on `jdempotent` in test scope, Maven's reactor never reaches `archtest` when `jdempotent` fails (SKIPPED), even with `-fae`.
- Re-ran `mvn -o -pl core,web,archtest -am -DskipITs -Dtest='!PrimeNumbersJdempotentEnableTest,!PrimeNumbersJdempotentDisableTest' -Dsurefire.failIfNoSpecifiedTests=false test` to exclude only those 2 pre-existing Docker-dependent tests and let the reactor reach `archtest`: **BUILD SUCCESS**, all 16 reactor modules SUCCESS. Ground-truth counts from `target/surefire-reports/*.txt` after this run: `core` 26/26 (Failures 0, Errors 0, Skipped 0), `web` 58/58 (Failures 0, Errors 0, Skipped 0 — includes all 10 moved `ExceptionsHandler*Test` classes, `ValidationAnnotationCountListenerTest`, `ScosFieldErrorTest`, plus the 5 pre-existing web tests), `archtest` 2/2 (Failures 0, Errors 0, Skipped 0).
- `mvn -o clean install -DskipTests` (full reactor, no `-pl`, 16 modules, `exception` no longer listed): first attempt failed compiling `scos-foundation-web` (`package tools.jackson.dataformat.xml does not exist`) — self-inflicted regression: an `Edit` to `web/pom.xml` had accidentally deleted the pre-existing `jackson-dataformat-xml` dependency block (needed by the pre-existing `JacksonXmlUtils.java`, unrelated to this story). Restored the block (see File List) and re-ran: **BUILD SUCCESS**, all 16 modules SUCCESS in 36.975s.
- Final re-run of `mvn -o -pl core,web,archtest -am -DskipITs test` (exact story command, no exclusions) to confirm the documented failure is still isolated to `jdempotent`/Testcontainers and not `core`/`web`/`archtest`: same result as the first run — `core`/`web` SUCCESS (26/26 and 58/58 per `target/surefire-reports`), `jdempotent` FAILURE (same 2 Docker tests), `archtest` SKIPPED as a consequence (not a `core`/`web`/`archtest` regression).

### Completion Notes List

- Moved all 5 main classes (`ExceptionsHandler`, `ValidationAnnotationCountListener`, `ScosFieldError`, `ScosProblemDetails`, `ExceptionUtils`) and all 15 test/fixture files from `exception` to `web`, per the story's pre-implementation correction comment (which supersedes the original Task 1 prose's undercount of 4 classes/~6 tests). `exception/src/main/java` and `exception/src/test/java` are fully empty of files after the move (confirmed via `find`), satisfying Task 3's precondition.
- `ValidationAnnotationCountListener` kept its plain `@Component`/`@ComponentScan` activation mechanism unchanged (only the package moved) — it was NOT wrapped in the new `@AutoConfiguration` machinery, since the story correction comment explicitly scopes that wrapper to `ExceptionsHandler` only.
- Created `ScosWebErrorHandlerAutoConfiguration` (`web/src/main/java/br/com/sawcunhaos/foundation/web/`), an `@AutoConfiguration` class with `@ConditionalOnProperty(prefix = "scos.web.error-handler", name = "enabled", matchIfMissing = true)` at the class level and a `@Bean` method (`@Order(Ordered.LOWEST_PRECEDENCE)`) that constructs `ExceptionsHandler` explicitly (`new ExceptionsHandler(localeService)`, matching its existing Lombok `@RequiredArgsConstructor`). `ExceptionsHandler` itself is untouched — still `@ControllerAdvice`, no internal logic changed. Pattern modeled on `privacy/src/main/java/.../ScosPrivacyAutoConfiguration.java` (closest existing example of an `@AutoConfiguration` wrapping beans with `@ConditionalOnProperty`).
- Created `web/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` with a single line (`br.com.sawcunhaos.foundation.web.ScosWebErrorHandlerAutoConfiguration`), following the exact one-FQN-per-line format of `jdempotent`'s equivalent file — `web` had no such file before this story.
- `web/pom.xml`: added compile-scope `spring-security-core`, `spring-boot-starter-validation`, `scos-foundation-validation-api`, and test-scope `spring-boot-starter-test` + `spring-boot-webmvc-test` (kept the pre-existing test-scope `spring-test`, still needed by `LoggingFilterMaskingE2ETest`). Deliberately did NOT add `mapstruct` (confirmed unused in `exception/src/main`, per the story's own correction note). **Self-caught mistake**: an early `Edit` on `web/pom.xml` accidentally deleted the pre-existing `jackson-dataformat-xml` dependency (needed by `JacksonXmlUtils.java`, unrelated to this story) — caught by the full-reactor `clean install` compile failure, fixed by restoring the exact original block; final `git diff web/pom.xml` is now purely additive.
- Root `pom.xml`: removed `<module>exception</module>` from `<modules>` and the `scos-foundation-exception` entry from `<dependencyManagement>`.
- `archtest/pom.xml`: removed the now-dead `scos-foundation-exception` test-scope dependency (used only for ArchUnit classpath scanning, no direct imports existed) — not repointed anywhere since `archtest` already depends on `scos-foundation-web` separately.
- Deleted the entire `exception/` directory (`pom.xml`, `README.md`, `.gitignore`, empty `src/main/java/.../exception/error` dir, `target/`) — the directory no longer exists on disk.
- Ambiguity resolved: the story's own Debug Log instruction to run `mvn -o -pl core,web,archtest -am -DskipITs test` produces a `BUILD FAILURE` in this sandboxed environment purely due to `jdempotent`'s Testcontainers-based Redis Sentinel tests timing out on Docker Compose networking — verified this is pre-existing/environmental (reproduced with sandbox disabled too, docker daemon present but container networking still times out) and unrelated to Story 2.9 (module untouched). To still produce ground-truth pass/fail counts for `core`/`web`/`archtest` as instructed, re-ran the same command with only those 2 Docker-dependent test classes excluded via `-Dtest='!...'`; all three target modules were 100% green. Documented both runs above rather than silently only reporting the passing one.
- No `exception`-package references remain anywhere in the repo (`grep -rl "br\.com\.sawcunhaos\.foundation\.exception"` returns nothing outside `target/` build output, which was left alone). One unrelated pre-existing staged change was noticed in `codegen/src/main/resources/mustaches/apiDelegate.mustache` (an import fix from `exception.error.MethodNotImplementedException` to `core.exception.MethodNotImplementedException`, apparently a Story 2.8 leftover) — left untouched as out of scope for this story.

### File List

**Moved (main, `exception` → `web`, package `br.com.sawcunhaos.foundation.exception.*` → `br.com.sawcunhaos.foundation.web.*`):**
- `web/src/main/java/br/com/sawcunhaos/foundation/web/ExceptionsHandler.java`
- `web/src/main/java/br/com/sawcunhaos/foundation/web/listener/ValidationAnnotationCountListener.java`
- `web/src/main/java/br/com/sawcunhaos/foundation/web/model/ScosFieldError.java`
- `web/src/main/java/br/com/sawcunhaos/foundation/web/model/ScosProblemDetails.java`
- `web/src/main/java/br/com/sawcunhaos/foundation/web/utils/ExceptionUtils.java`

**Moved (test/fixtures, same package rename):**
- `web/src/test/java/br/com/sawcunhaos/foundation/web/ExceptionsHandlerAccessDeniedTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/ExceptionsHandlerHandleExceptionInternalTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/ExceptionsHandlerInternalErrorTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/ExceptionsHandlerJackson3DeserializationTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/ExceptionsHandlerLogLevelTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/ExceptionsHandlerMdcTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/ExceptionsHandlerMethodNotImplementedTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/ExceptionsHandlerResolveTitleTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/ExceptionsHandlerScosExceptionTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/ExceptionsHandlerValidationTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/TestBootConfiguration.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/listener/ValidationAnnotationCountListenerTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/listener/empty/SampleNoValidationUsage.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/listener/sample/SampleValidationUsage.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/model/ScosFieldErrorTest.java`
- `web/src/test/java/br/com/sawcunhaos/foundation/web/support/PingController.java`

**Created:**
- `web/src/main/java/br/com/sawcunhaos/foundation/web/ScosWebErrorHandlerAutoConfiguration.java` — new `@AutoConfiguration` class wrapping `ExceptionsHandler` as a `@Bean` (`@ConditionalOnProperty(prefix = "scos.web.error-handler", name = "enabled", matchIfMissing = true)`, `@Order(Ordered.LOWEST_PRECEDENCE)`)
- `web/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` — registers `ScosWebErrorHandlerAutoConfiguration`

**Modified:**
- `web/pom.xml` — added compile deps `spring-security-core`, `spring-boot-starter-validation`, `scos-foundation-validation-api`; added test deps `spring-boot-starter-test`, `spring-boot-webmvc-test`

## Verificação e fechamento

Esta story foi fechada a partir de verificação direta do orquestrador (sem o passo padrão de revisão em 3 camadas por agentes, a pedido explícito do usuário — "fecha a story ela já tá pronta"), cobrindo:

- `git diff --cached` de `web/pom.xml`, `pom.xml` raiz e `archtest/pom.xml` — conferidos linha a linha contra o comentário de correção pré-implementação; todos batem exatamente (nenhuma dependência morta carregada, nenhuma real faltando).
- Conteúdo de `ScosWebErrorHandlerAutoConfiguration.java` e do novo `AutoConfiguration.imports` — conferidos; o construtor `new ExceptionsHandler(localeService)` bate com o construtor gerado por Lombok (`@RequiredArgsConstructor`) da classe movida, que permanece inalterada.
- `git status --short` confirma que os 4 arquivos movidos usaram `git mv` (aparecem como `R` já no stage, não como delete+add separados).
- `mvn -o -pl core,web,archtest -am -DskipITs test`: `core` 26/26 e `web` 58/58 confirmados via `target/surefire-reports` (0 falhas/erros); `jdempotent` falha com o mesmo padrão pré-existente e já documentado nesta sessão (`ContainerLaunchException`/Docker Compose Redis Sentinel, módulo não tocado por esta story) — reproduzido de forma idêntica em execução independente do orquestrador, confirmando o achado do subagente. `archtest` não foi re-confirmado nesta última rodada (o rerun com `-fae` para contornar `jdempotent` foi interrompido antes de concluir), mas o subagente já reportou `archtest` 2/2 numa rodada anterior com os 2 testes de Docker excluídos, e `archtest/src/test` não referencia o pacote `exception` em nenhuma regra (confirmado via grep) — sem sinal de risco real de regressão ali.
- `git diff --cached -- web/pom.xml` confirmado puramente aditivo (sem remoções acidentais), corroborando o auto-fix que o subagente relatou (recuperação da dependência `jackson-dataformat-xml` que havia apagado sem querer).
- `archtest/src/test` não cita o pacote/módulo `exception` em nenhuma regra ArchUnit (confirmado via grep) — nada para atualizar ali além da remoção da dependência já feita.
- `pom.xml` (root) — removed `<module>exception</module>` and the `scos-foundation-exception` `dependencyManagement` entry
- `archtest/pom.xml` — removed the `scos-foundation-exception` test-scope dependency

**Deleted:**
- `exception/` (entire directory: `pom.xml`, `README.md`, `.gitignore`, and the now-empty `src/main/java`, `src/test/java` trees)
