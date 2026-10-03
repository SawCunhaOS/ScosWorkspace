# Story 4.8: Documentar o módulo `validation`

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor usando value objects brasileiros,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender o contrato de `Cpf`/`Cnpj`/`Email`/`TaxIdentifier`.

## Acceptance Criteria

1. **Given** o módulo `validation` (Epic 1, Story 1.9), **When** a documentação é adicionada, **Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso.

## Tasks / Subtasks

- [x] Task 1: Confirmar pré-requisito (AC: #1)
  - [x] **Confirmado por leitura direta**: `validation` **ainda não existe** — nasce na Story 1.9, recebendo `Cpf`, `Cnpj`, `Email`, `TaxIdentifier` (hoje em `utils/src/main/java/.../valueobjects/`, confirmado via `find`) e dependendo de `core` + `validation-api`, com `jakarta.persistence-api` como `provided`
- [x] Task 2: Javadoc em toda API pública (AC: #1)
  - [x] Cobrir os 4 value objects: contrato de construção/validação, formato esperado de entrada, o que cada um valida (dígito verificador de CPF/CNPJ, formato de e-mail)
- [x] Task 3: Comentários inline onde a lógica não é óbvia (AC: #1)
  - [x] Comentar algoritmo de validação de dígito verificador de CPF/CNPJ se a lógica não for autoexplicativa pelo nome dos métodos
- [x] Task 4: README com diagrama Mermaid (AC: #1)
  - [x] Criar `validation/README.md` explicando a relação com `validation-api` (as anotações `@Cpf`/`@Cnpj` ficam em `validation-api`; os value objects que implementam a validação ficam aqui) e com `jakarta.persistence-api` como `provided` (não força JPA completo em quem só quer validar um documento)
  - [x] Diagrama Mermaid: aplicação usa `Cpf.of(valor)` (ou equivalente) → validação de dígito verificador → objeto imutável válido ou exceção

## Dev Notes

- Esta story só pode rodar depois da Story 1.9 (extração do módulo).
- Não confundir com `validation-api` (Story 4.5) — este módulo tem a implementação (value objects), o outro só as anotações Bean Validation.

### Project Structure Notes

- Arquivo novo: `validation/README.md`.
- Javadoc adicionado aos value objects de `validation`.

### References

- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/1-9-extrair-o-módulo-validation.md]
- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/4-5-documentar-o-módulo-validation-api.md] (módulo `-api` relacionado, não confundir)
- [Source: _bmad-output/SawCunhaOS-Foundation/planning-artifacts/epics.md#story-48-documentar-o-módulo-validation]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5.5

### Debug Log References

### Completion Notes List

- Pré-requisito: o módulo `validation` já existe (Story 1.9, `done`) com os 4 value objects e os 4 `ConstraintValidator`s; a nota "ainda não existe" da story estava desatualizada.
- Javadoc de tipo + construtor + setter + construtor JPA nos 4 value objects e `isValid` nos 4 validadores; comentários inline nas decisões não óbvias (ordem CNPJ→CPF, `type` só em sucesso, regex de e-mail + checagens explícitas, `$` do Java no CEP).
- Contrato real documentado (difere do texto da story): value objects **não** são imutáveis (há setter), só aceitam dígitos sem pontuação e `null` quebra `@NonNull` com exceção que não é `ScosException`.
- `validation/README.md` criado (relação com `validation-api`, `jakarta.persistence-api` `provided`, diagrama Mermaid, tabela de códigos `SCOS-006..009`).
- `mvn -pl validation -am test` verde; checkstyle do perfil `analyze` sem violações de Javadoc. Spec: `spec-4-8-documentar-o-módulo-validation.md`.

### File List
- `SawCunhaOS-Foundation/validation/README.md` (novo)
- `SawCunhaOS-Foundation/validation/src/main/java/.../valueobjects/{Cpf,Cnpj,Email,TaxIdentifier}.java` (Javadoc/comentários)
- `SawCunhaOS-Foundation/validation/src/main/java/.../taxidentifier/constraint/{CpfValidator,CnpjValidator,TaxIdentifierValidator}.java` e `.../zipcode/constraint/ZipCodeValidator.java` (Javadoc/comentários)
