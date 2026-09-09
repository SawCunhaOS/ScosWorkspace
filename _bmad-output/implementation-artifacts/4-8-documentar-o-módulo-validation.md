# Story 4.8: Documentar o módulo `validation`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor usando value objects brasileiros,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender o contrato de `Cpf`/`Cnpj`/`Email`/`TaxIdentifier`.

## Acceptance Criteria

1. **Given** o módulo `validation` (Epic 1, Story 1.9), **When** a documentação é adicionada, **Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso.

## Tasks / Subtasks

- [ ] Task 1: Confirmar pré-requisito (AC: #1)
  - [ ] **Confirmado por leitura direta**: `validation` **ainda não existe** — nasce na Story 1.9, recebendo `Cpf`, `Cnpj`, `Email`, `TaxIdentifier` (hoje em `utils/src/main/java/.../valueobjects/`, confirmado via `find`) e dependendo de `core` + `validation-api`, com `jakarta.persistence-api` como `provided`
- [ ] Task 2: Javadoc em toda API pública (AC: #1)
  - [ ] Cobrir os 4 value objects: contrato de construção/validação, formato esperado de entrada, o que cada um valida (dígito verificador de CPF/CNPJ, formato de e-mail)
- [ ] Task 3: Comentários inline onde a lógica não é óbvia (AC: #1)
  - [ ] Comentar algoritmo de validação de dígito verificador de CPF/CNPJ se a lógica não for autoexplicativa pelo nome dos métodos
- [ ] Task 4: README com diagrama Mermaid (AC: #1)
  - [ ] Criar `validation/README.md` explicando a relação com `validation-api` (as anotações `@Cpf`/`@Cnpj` ficam em `validation-api`; os value objects que implementam a validação ficam aqui) e com `jakarta.persistence-api` como `provided` (não força JPA completo em quem só quer validar um documento)
  - [ ] Diagrama Mermaid: aplicação usa `Cpf.of(valor)` (ou equivalente) → validação de dígito verificador → objeto imutável válido ou exceção

## Dev Notes

- Esta story só pode rodar depois da Story 1.9 (extração do módulo).
- Não confundir com `validation-api` (Story 4.5) — este módulo tem a implementação (value objects), o outro só as anotações Bean Validation.

### Project Structure Notes

- Arquivo novo: `validation/README.md`.
- Javadoc adicionado aos value objects de `validation`.

### References

- [Source: _bmad-output/implementation-artifacts/1-9-extrair-o-módulo-validation.md]
- [Source: _bmad-output/implementation-artifacts/4-5-documentar-o-módulo-validation-api.md] (módulo `-api` relacionado, não confundir)
- [Source: _bmad-output/planning-artifacts/epics.md#story-48-documentar-o-módulo-validation]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
