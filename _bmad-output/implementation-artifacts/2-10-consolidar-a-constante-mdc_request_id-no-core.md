# Story 2.10: Consolidar a constante `MDC_REQUEST_ID` no `core`

Status: done

<!-- baseline_commit: 139f70feb63ae06ebe29291555b882199fd1fd92 -->

<!-- Nota de fechamento: esta story foi implementada e commitada diretamente pelo usuário (fora do fluxo /bmad-build), em paralelo às Stories 2.1-2.9 desta mesma sessão — confirmado via `git log`/`git status` (nenhuma mudança pendente relacionada quando esta story foi retomada). O AC #1 (fonte única, zero duplicação) está satisfeito na prática: `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/Constant.java` (novo enum, `REQUEST_ID_HEADER("X-Request-ID")`) é referenciado exclusivamente por `LoggingInitialFilter`/`ScosProblemDetails` (ambos em `web`, confirmado via grep — nenhuma declaração local duplicada restante, nenhum literal `"X-Request-ID"` hardcoded fora de Javadoc). `LoggingFinalFilter` nunca referenciou essa constante — a suposição da Dev Notes original de que ele também precisaria mudar está incorreta/desatualizada, confirmado lendo seu conteúdo atual. A implementação real diverge da Task 2 em dois pontos específicos: (1) usa uma classe NOVA (`Constant`, um enum) em vez de uma classe utilitária já existente do `core`; (2) o nome da constante é `REQUEST_ID_HEADER`, não `MDC_REQUEST_ID`. Perguntado ao usuário se deveria refazer para bater com a letra da spec ou aceitar como está — resposta: aceitar como está. Task/Dev Notes abaixo corrigidas para refletir o que foi de fato implementado, sem tocar em código. `mvn -o -pl core,web -am test`: `Tests run: 58, Failures: 0, Errors: 0, Skipped: 0`, `BUILD SUCCESS`. -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero uma única fonte para a constante de correlação de log,
Para eliminar duplicidade entre `web` e `core`.

## Acceptance Criteria

1. **Given** `MDC_REQUEST_ID` hoje duplicada entre `ScosProblemDetails` (agora em `web`, Story 2.9) e `LoggingInitialFilter` (em `web`, Epic 1 Story 1.12), **When** a constante é consolidada em um único ponto no módulo `core`, **Then** ambas as classes em `web` referenciam a mesma constante do `core`, sem duplicação.

## Tasks / Subtasks

- [x] Task 1: Confirmar as duas definições atuais antes de consolidar (AC: #1)
  - [x] `ScosProblemDetails.java` (movida para `web` na Story 2.9) e `LoggingInitialFilter.java` (movida para `web` na Story 1.12 do Epic 1) tinham declarações locais duplicadas do mesmo literal `"X-Request-ID"` — confirmado como a mesma constante duplicada por propósito (chave de MDC/header de correlação), tratada como tal
- [x] Task 2: Criar a constante única em `core` (AC: #1)
  - [x] **Implementado de forma diferente da prescrição original**: em vez de uma constante `MDC_REQUEST_ID` numa classe utilitária já existente, foi criado `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/Constant.java` (novo enum, `REQUEST_ID_HEADER("X-Request-ID")`) — implementado diretamente pelo usuário, fora do fluxo `/bmad-build`, em paralelo às Stories 2.1-2.9. Perguntado ao usuário se deveria refazer para bater com a letra da Task (nome `MDC_REQUEST_ID`, sem classe nova) ou aceitar como está — decisão: aceitar como está, já que o objetivo real (fonte única, zero duplicação) está satisfeito
- [x] Task 3: Repontar as duas classes em `web` (AC: #1)
  - [x] `ScosProblemDetails` usa `Constant.REQUEST_ID_HEADER.getValue()` via import estático, sem declaração local própria (confirmado via grep)
  - [x] `LoggingInitialFilter` usa `Constant.REQUEST_ID_HEADER.getValue()` via import estático, sem declaração local própria (confirmado via grep). **`LoggingFinalFilter` nunca referenciou essa constante** — a suposição original de que ele também precisaria mudar estava incorreta (confirmado lendo seu conteúdo atual: não usa `X-Request-ID`/MDC de correlação em nenhum ponto)
  - [x] Nenhum teste (`ExceptionsHandlerMdcTest` e os demais do módulo `web`) depende do nome antigo — suíte completa de `core`+`web` roda verde (`mvn -o -pl core,web -am test`: 58/58, 0 falhas)

## Dev Notes

- Depende das Stories 2.9 (`ScosProblemDetails` já em `web`) e 1.12 do Epic 1 (`LoggingInitialFilter`/`LoggingFinalFilter` já em `web`) — antes disso as duas classes estão em módulos diferentes (`exception` e `utils`) e "consolidar em `core`" não teria as duas pontas já no lugar certo para repontar.
- Escopo mínimo: só a constante muda de dono, não o comportamento de MDC/logging em si — nenhuma outra alteração nos filtros ou no handler. Confirmado: a implementação real não mudou nenhum comportamento de MDC/logging, só a fonte da constante.
- ~~Não introduzir uma classe `Constants`/`WebConstants` genérica no `core`~~ — na prática, a implementação real introduziu um enum dedicado (`Constant`) para hospedar essa constante, divergindo desta orientação. Aceito como está por decisão do usuário (ver comentário de fechamento no topo do arquivo).

### Project Structure Notes

- Módulo `core` ganhou a constante `REQUEST_ID_HEADER` (não `MDC_REQUEST_ID`) no enum `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/Constant.java` (classe nova, não uma classe utilitária já existente).
- `web/.../model/ScosProblemDetails.java` e `web/.../filter/LoggingInitialFilter.java` removeram sua declaração local e passaram a importar `Constant.REQUEST_ID_HEADER` do `core`. `LoggingFinalFilter.java` não precisou de nenhuma mudança (nunca referenciou essa constante).

### References

- [Source: core/src/main/java/br/com/sawcunhaos/foundation/core/enums/Constant.java] (caminho real; a story original citava `exception/.../ScosProblemDetails.java` e `utils/.../LoggingInitialFilter.java`, ambos desatualizados — `exception` não existe mais desde a Story 2.9, `utils` desde a Story 1.14 do Épico 1)
- [Source: web/src/main/java/br/com/sawcunhaos/foundation/web/model/ScosProblemDetails.java]
- [Source: web/src/main/java/br/com/sawcunhaos/foundation/web/filter/LoggingInitialFilter.java]
- [Source: _bmad-output/implementation-artifacts/1-12-extrair-o-módulo-web.md]
- [Source: _bmad-output/implementation-artifacts/2-9-mover-a-tradução-http-do-exception-para-o-web-e-registrar-vi.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-210-consolidar-a-constante-mdc_request_id-no-core]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5) — retomada/fechamento; implementação original feita diretamente pelo usuário

### Debug Log References

- `git log`/`git status` ao retomar esta story: nenhuma mudança pendente relacionada — `Constant.java` e os dois consumidores já estavam commitados (parte do histórico da sessão, commits do usuário em paralelo às Stories 2.1-2.9).
- `grep -rn "X-Request-ID" web/src/main/` → só ocorrências em Javadoc/comentário, nenhum literal hardcoded em código.
- `grep -n "REQUEST_ID|Constant" web/src/main/java/.../filter/LoggingFinalFilter.java` → vazio, confirmando que este arquivo nunca precisou da mudança.
- `mvn -o -pl core,web -am -DskipITs test` → `BUILD SUCCESS`, `Tests run: 58, Failures: 0, Errors: 0, Skipped: 0`.

### Completion Notes List

- AC #1 confirmado satisfeito na prática: fonte única (`Constant.REQUEST_ID_HEADER`), zero duplicação, ambos os consumidores (`ScosProblemDetails`, `LoggingInitialFilter`) repontados, `LoggingFinalFilter` não precisava de mudança (não referenciava a constante).
- Implementação diverge da Task 2 original em nome (`REQUEST_ID_HEADER` em vez de `MDC_REQUEST_ID`) e em local (classe nova `Constant`, não uma classe utilitária existente do `core`) — decisão consciente do usuário, mantida como está; não revertida nem renomeada nesta revisão. Ver comentário de fechamento no topo do arquivo para o histórico completo da decisão.
- Nenhum código foi alterado nesta sessão para fechar esta story — o trabalho técnico já estava commitado; esta passagem só corrigiu a documentação da própria story (Tasks, Dev Notes, References) para refletir o que foi de fato implementado, e confirmou via teste que está tudo funcionando.

### File List

- Nenhum arquivo de código alterado nesta sessão (implementação já commitada previamente pelo usuário: `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/Constant.java`, `web/src/main/java/br/com/sawcunhaos/foundation/web/model/ScosProblemDetails.java`, `web/src/main/java/br/com/sawcunhaos/foundation/web/filter/LoggingInitialFilter.java`).
- `_bmad-output/implementation-artifacts/2-10-consolidar-a-constante-mdc_request_id-no-core.md` (este arquivo, documentação corrigida para refletir a implementação real).
