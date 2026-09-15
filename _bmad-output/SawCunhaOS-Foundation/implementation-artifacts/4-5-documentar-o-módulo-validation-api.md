# Story 4.5: Documentar o módulo `validation-api`

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor de domínio puro,
Eu quero saber pelo README que este artefato não executa nada sozinho,
Para não integrá-lo sem a implementação correspondente.

## Acceptance Criteria

1. **Given** o módulo `validation-api` (Epic 1, Story 1.5), **When** a documentação é adicionada, **Then** o README abre com "este artefato não executa nada; a implementação é `scos-foundation-validation`" e traz diagrama Mermaid do fluxo típico de uso.
2. **And** toda anotação pública tem Javadoc.

## Tasks / Subtasks

- [x] Task 1: Confirmar pré-requisito (AC: #1)
  - [x] **Confirmado por leitura direta (nesta execução)**: `validation-api` já existe — nasceu na Story 1.9 (não na 1.5 como registrado acima; confirmado pelo comentário do `pom.xml` raiz do reactor), com as 4 anotações (`@CPF`, `@CNPJ`, `@TaxIdentifier`, `@ZipCode`) e `README.md` com a frase de abertura e a tabela "Conteúdo" já presentes.
- [x] Task 2: README com frase de abertura obrigatória e diagrama (AC: #1)
  - [x] `validation-api/README.md` já abria com a frase exigida (pré-existente) — não alterada.
  - [x] Seção "Fluxo típico de uso" com diagrama Mermaid adicionada, no padrão de `jdempotent-api/README.md`: app consumidora anota campo/DTO com cada anotação → efeito só com `scos-foundation-validation` no classpath (um `ConstraintValidator` por anotação, ligado via `META-INF/validation.xml`).
- [x] Task 3: Javadoc em toda anotação pública (AC: #2)
  - [x] Javadoc adicionado a `message()`/`groups()`/`payload()` nas 4 anotações — só faltava documentação de atributo; o Javadoc de tipo já existia e foi preservado sem alteração.

## Dev Notes

- Mesma regra das demais stories `*-api` (4.3, 4.4): sem gate de cobertura Jacoco, só `@interface`/`enum`.
- Não confundir `validation-api` (anotações Bean Validation, ex.: `@Cpf`, `@Cnpj`) com o módulo `validation` (Story 1.9, os value objects `Cpf`/`Cnpj`/`Email`/`TaxIdentifier` propriamente ditos) — são dois módulos distintos documentados por stories distintas (esta e a 4.8).

### Project Structure Notes

- Arquivo novo: `validation-api/README.md`.
- Javadoc adicionado às anotações movidas para `validation-api`.

### References

- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/1-5-criar-módulos-api-e-mover-as-anotações-de-contrato.md]
- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/1-9-extrair-o-módulo-validation.md] (módulo de implementação correspondente, não confundir)
- [Source: _bmad-output/SawCunhaOS-Foundation/planning-artifacts/epics.md#story-45-documentar-o-módulo-validation-api]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (bmad-build, rota oneshot)

### Debug Log References

### Completion Notes List

- Diagrama Mermaid ("Fluxo típico de uso") adicionado ao README, um nó por anotação e um nó por `ConstraintValidator` concreto; Javadoc adicionado aos atributos `message()`/`groups()`/`payload()` das 4 anotações. `mvn -pl validation-api -am test` verde (`ArchitectureTest`) antes e depois da revisão.
- `message()` documentado como um código `SCOS-XXX` (não mensagem literal), citando o módulo (`scos-foundation-core`) onde `ScosExceptionCode` vive e o risco de sobrescrevê-lo com um literal (rompe a resolução via `LocaleService`). No caso de `ZipCode`, o Javadoc também deixa explícita a colisão real encontrada: o default `SCOS-009` já é atribuído a `EMAIL_INVALID` em `ScosExceptionCode`, sem código dedicado a CEP no registro.
- Revisão blind-hunter encontrou 9 achados: 4 aplicados como patch simples (diagrama com nó por validador, aviso de sobrescrita de `message()`, referência ao módulo `core`, colisão `SCOS-009`/`EMAIL_INVALID` explicitada no Javadoc), 4 fora de escopo adiados para `deferred-work.md` (null-handling de `CpfValidator` pertence à Story 4.8; lacuna do gate mecânico de checkstyle pertence às Stories 4.1/4.16; índice de módulos do README raiz, mesma lacuna já registrada pela Story 4.2; drift de ordenação de meta-anotações em `ZipCode.java`, pré-existente), e 1 achado de baixo valor rejeitado (`@Repeatable` em `groups()`). Detalhe completo: `## Review Triage Log` da spec.
- Spec completa: `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/spec-4-5-documentar-o-módulo-validation-api.md`.

### File List

- `SawCunhaOS-Foundation/validation-api/README.md` (seção "Fluxo típico de uso" com diagrama Mermaid)
- `SawCunhaOS-Foundation/validation-api/src/main/java/br/com/sawcunhaos/foundation/validation/api/CPF.java` (Javadoc de atributo)
- `SawCunhaOS-Foundation/validation-api/src/main/java/br/com/sawcunhaos/foundation/validation/api/CNPJ.java` (Javadoc de atributo)
- `SawCunhaOS-Foundation/validation-api/src/main/java/br/com/sawcunhaos/foundation/validation/api/TaxIdentifier.java` (Javadoc de atributo)
- `SawCunhaOS-Foundation/validation-api/src/main/java/br/com/sawcunhaos/foundation/validation/api/ZipCode.java` (Javadoc de atributo)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/deferred-work.md` (4 achados adiados)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/sprint-status.yaml` (status da story)
