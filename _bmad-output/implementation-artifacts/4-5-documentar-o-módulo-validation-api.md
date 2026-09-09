# Story 4.5: Documentar o módulo `validation-api`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor de domínio puro,
Eu quero saber pelo README que este artefato não executa nada sozinho,
Para não integrá-lo sem a implementação correspondente.

## Acceptance Criteria

1. **Given** o módulo `validation-api` (Epic 1, Story 1.5), **When** a documentação é adicionada, **Then** o README abre com "este artefato não executa nada; a implementação é `scos-foundation-validation`" e traz diagrama Mermaid do fluxo típico de uso.
2. **And** toda anotação pública tem Javadoc.

## Tasks / Subtasks

- [ ] Task 1: Confirmar pré-requisito (AC: #1)
  - [ ] **Confirmado por leitura direta**: `validation-api` **ainda não existe** — nasce na Story 1.5, movendo as anotações de validação (hoje em `utils/src/main/java/.../validation/taxIdentifier/` e `.../validation/zipcode/`, confirmado via `find`) para este módulo
- [ ] Task 2: README com frase de abertura obrigatória e diagrama (AC: #1)
  - [ ] Criar `validation-api/README.md` iniciando com "este artefato não executa nada; a implementação é `scos-foundation-validation`"
  - [ ] Diagrama Mermaid: aplicação anota campo/DTO com anotação de validação de `validation-api` (ex.: CPF/CNPJ/CEP) → precisa de `scos-foundation-validation` no classpath para o validador (`ConstraintValidator`) ter efeito
- [ ] Task 3: Javadoc em toda anotação pública (AC: #2)
  - [ ] Cobrir as anotações de `taxIdentifier` (CPF/CNPJ) e `zipcode` movidas para este módulo

## Dev Notes

- Mesma regra das demais stories `*-api` (4.3, 4.4): sem gate de cobertura Jacoco, só `@interface`/`enum`.
- Não confundir `validation-api` (anotações Bean Validation, ex.: `@Cpf`, `@Cnpj`) com o módulo `validation` (Story 1.9, os value objects `Cpf`/`Cnpj`/`Email`/`TaxIdentifier` propriamente ditos) — são dois módulos distintos documentados por stories distintas (esta e a 4.8).

### Project Structure Notes

- Arquivo novo: `validation-api/README.md`.
- Javadoc adicionado às anotações movidas para `validation-api`.

### References

- [Source: _bmad-output/implementation-artifacts/1-5-criar-módulos-api-e-mover-as-anotações-de-contrato.md]
- [Source: _bmad-output/implementation-artifacts/1-9-extrair-o-módulo-validation.md] (módulo de implementação correspondente, não confundir)
- [Source: _bmad-output/planning-artifacts/epics.md#story-45-documentar-o-módulo-validation-api]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
