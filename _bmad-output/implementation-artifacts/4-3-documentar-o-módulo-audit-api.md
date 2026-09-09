# Story 4.3: Documentar o módulo `audit-api`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor de domínio puro,
Eu quero saber pelo README que este artefato não executa nada sozinho,
Para não integrá-lo sem a implementação correspondente.

## Acceptance Criteria

1. **Given** o módulo `audit-api` (Epic 1, Story 1.5), **When** a documentação é adicionada, **Then** o README abre com "este artefato não executa nada; a implementação é `scos-foundation-audit`" e traz diagrama Mermaid do fluxo típico de uso.
2. **And** toda anotação pública tem Javadoc.

## Tasks / Subtasks

- [ ] Task 1: Confirmar pré-requisito (AC: #1)
  - [ ] **Confirmado por leitura direta**: o módulo `audit-api` **ainda não existe** neste repositório — nasce na Story 1.5, que move a anotação `@Auditable` (hoje em `utils/src/main/java/.../annotation/audit/`, confirmado via `find`) para um módulo `*-api` contendo apenas `@interface`/`enum`
  - [ ] Não iniciar antes da Story 1.5 estar implementada
- [ ] Task 2: README com frase de abertura obrigatória e diagrama (AC: #1)
  - [ ] Criar `audit-api/README.md` iniciando literalmente com a frase "este artefato não executa nada; a implementação é `scos-foundation-audit`" (mesma frase exigida pela Story 1.15 do Epic 1 para todo módulo `-api`)
  - [ ] Diagrama Mermaid mostrando: aplicação consumidora anota entidade/método com `@Auditable` (vindo de `audit-api`) → precisa do módulo `scos-foundation-audit` no classpath para a anotação ter efeito → listener Hibernate/aspecto processa a anotação
- [ ] Task 3: Javadoc em toda anotação pública (AC: #2)
  - [ ] `@Auditable` e demais anotações movidas para este módulo recebem Javadoc explicando o contrato (o que a anotação sinaliza), não a implementação (que não está neste módulo)

## Dev Notes

- Não se aplica o gate de cobertura Jacoco (NFR3) aqui — módulo `*-api` não tem lógica de runtime, só `@interface`/`enum` (regra ArchUnit local da Story 1.5).
- A frase de abertura do README é um requisito literal repetido em várias stories deste epic (4.3, 4.4, 4.5) e também na Story 1.15 (log de inicialização) — manter a redação idêntica entre os três READMEs `*-api`, trocando só o nome do módulo de implementação.

### Project Structure Notes

- Arquivo novo: `audit-api/README.md`.
- Javadoc adicionado às anotações movidas para `audit-api`.

### References

- [Source: _bmad-output/implementation-artifacts/1-5-criar-módulos-api-e-mover-as-anotações-de-contrato.md]
- [Source: _bmad-output/implementation-artifacts/1-15-emitir-log-de-inicialização-por-módulo-de-implementação.md] (mesma frase de abertura exigida)
- [Source: _bmad-output/planning-artifacts/epics.md#story-43-documentar-o-módulo-audit-api]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
