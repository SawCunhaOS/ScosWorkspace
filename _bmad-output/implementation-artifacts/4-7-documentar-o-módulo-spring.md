# Story 4.7: Documentar o módulo `spring`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor usando aspectos genéricos do Spring,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender como `ScosRule` se integra à minha aplicação.

## Acceptance Criteria

1. **Given** o módulo `spring` (Epic 1, Story 1.8), **When** a documentação é adicionada, **Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso.

## Tasks / Subtasks

- [ ] Task 1: Confirmar pré-requisito (AC: #1)
  - [ ] **Confirmado por leitura direta**: `spring` **ainda não existe** — nasce na Story 1.8, recebendo `ScosRule`, `ScosRuleService`, `NormalizeStrings`, `StringProcessingAspect`, `ScosOnStartupListener`, `ScosStartupListener` (hoje em `utils/src/main/java/.../annotation/rules/`, `.../aspect/`, `.../listener/`, confirmado via `find`)
- [ ] Task 2: Javadoc em toda API pública (AC: #1)
  - [ ] Cobrir as 6 classes/interfaces migradas, incluindo o contrato `ScosStartupListener` (interface que `ScosOnStartupListener` consome via `List<ScosStartupListener>` — documentar essa relação de consumo no Javadoc da interface)
- [ ] Task 3: Comentários inline onde a lógica não é óbvia (AC: #1)
  - [ ] `StringProcessingAspect`/`NormalizeStrings`: comentar a decisão de onde/quando a normalização de string é aplicada, se não for óbvio pela assinatura
- [ ] Task 4: README com diagrama Mermaid (AC: #1)
  - [ ] Criar `spring/README.md` explicando o propósito (aspectos genéricos do Spring, sem JPA/Servlet — dependência só de `core`)
  - [ ] Diagrama Mermaid do fluxo: aplicação consumidora implementa `ScosStartupListener` → `ScosOnStartupListener` (bean do Spring) coleta todos via `List<ScosStartupListener>` e dispara no evento de startup

## Dev Notes

- Esta story só pode rodar depois da Story 1.8 (extração do módulo).
- `spring` depende de `core` mas não importa `jakarta.servlet`/`jakarta.persistence`/`spring.data` (regra ArchUnit local da própria Story 1.8) — mencionar essa fronteira no README como parte do "propósito" do módulo.

### Project Structure Notes

- Arquivo novo: `spring/README.md`.
- Javadoc adicionado às classes públicas de `spring`.

### References

- [Source: _bmad-output/implementation-artifacts/1-8-extrair-o-módulo-spring.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-47-documentar-o-módulo-spring]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
