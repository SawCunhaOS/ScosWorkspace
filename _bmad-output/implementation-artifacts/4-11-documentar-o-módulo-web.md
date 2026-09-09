# Story 4.11: Documentar o módulo `web`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor de endpoints REST,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender como `ScosController` e o tratamento de erro se conectam.

## Acceptance Criteria

1. **Given** o módulo `web` (Epic 1, Story 1.12; Epic 2, Story 2.9), **When** a documentação é adicionada, **Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso.

## Tasks / Subtasks

- [ ] Task 1: Confirmar pré-requisito (AC: #1)
  - [ ] **Confirmado por leitura direta**: `web` **ainda não existe** — nasce na Story 1.12 (`ScosController`, `IpAddressExtractor`, `ScosResponseUtils`, `PaginationUtils`, `JacksonXmlUtils`, `MultiReadHttpServletRequest`, `ScosJacksonConfig`, `LoggingInitialFilter`/`LoggingFinalFilter`, dependendo de `core`+`cache`+`privacy`) e recebe o tratamento de erro HTTP na Story 2.9 (`ExceptionsHandler`, `ScosProblemDetails`, `ScosFieldError`, `ExceptionUtils`, registrados via `AutoConfiguration.imports`)
  - [ ] Esta é a documentação mais ampla do epic — cobre dois conjuntos de classes de origens diferentes (Epic 1 e Epic 2), unificados no mesmo módulo
- [ ] Task 2: Javadoc em toda API pública (AC: #1)
  - [ ] Cobrir as 8 classes de `web` (Story 1.12) e as 4 classes do tratamento de erro (Story 2.9), incluindo a ativação via `@ConditionalOnProperty(scos.web.error-handler.enabled, matchIfMissing=true)` — documentar essa property no Javadoc de `ExceptionsHandler`
- [ ] Task 3: Comentários inline onde a lógica não é óbvia (AC: #1)
  - [ ] `MultiReadHttpServletRequest`: comentar por que é necessário reler o corpo da requisição (logging + processamento, sem esse wrapper o stream só pode ser lido uma vez)
  - [ ] `LoggingInitialFilter`/`LoggingFinalFilter`: comentar a relação com `MDC_REQUEST_ID` (consolidado no `core` pela Story 2.10)
- [ ] Task 4: README com diagrama Mermaid (AC: #1)
  - [ ] Criar `web/README.md` explicando o propósito (`@Cacheable` embutido, tratamento de erro HTTP automático ao importar o módulo)
  - [ ] Diagrama Mermaid do fluxo de requisição: `LoggingInitialFilter` → controller (`ScosController`) → exceção → `ExceptionsHandler` (`AutoConfiguration.imports`) → `ScosProblemDetails` (RFC 7807) → `LoggingFinalFilter`

## Dev Notes

- Esta story só pode rodar depois das Stories 1.12 e 2.9 (as duas contribuem classes para este módulo).
- `@Cacheable` funciona nas anotações `ScosRequestGET/POST/PUT/DELETE` (AC da Story 1.12) — documentar essa integração no README, é um comportamento não-óbvio de só importar o módulo.
- Consolidação de `MDC_REQUEST_ID` no `core` (Story 2.10) é relevante para o Javadoc de `LoggingInitialFilter`/`ScosProblemDetails` — referenciar a constante única, não duplicar a explicação.

### Project Structure Notes

- Arquivo novo: `web/README.md`.
- Javadoc adicionado às classes de `web` (origem Epic 1 e Epic 2).

### References

- [Source: _bmad-output/implementation-artifacts/1-12-extrair-o-módulo-web.md]
- [Source: _bmad-output/implementation-artifacts/2-9-mover-a-tradução-http-do-exception-para-o-web-e-registrar-vi.md]
- [Source: _bmad-output/implementation-artifacts/2-10-consolidar-a-constante-mdc_request_id-no-core.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-411-documentar-o-módulo-web]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
