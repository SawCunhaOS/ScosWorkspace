---
title: 'Documentar o módulo validation'
type: 'chore'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/4-8-documentar-o-módulo-validation.md']
---

<intent-contract>

## Intent

**Problem:** O módulo `validation` (Story 1.9, `done`; a nota "ainda não existe" da story estava desatualizada) tem os 4 value objects e 4 validadores sem Javadoc, sem README e sem diagrama.

**Approach:** Javadoc na API pública (tipo, construtor, setter, `isValid`), comentários inline onde a lógica não é óbvia e `validation/README.md` com diagrama Mermaid. Só documentação: nenhum comportamento, assinatura ou nome (inclusive `setTaxIdentifier` em `Cpf`/`Cnpj`) é alterado.

## Boundaries & Constraints

**Always:** documentar o contrato real (não imutável, só dígitos sem pontuação, `null` fora de `ScosException`, `null` rejeitado pelos validadores).
**Never:** alterar código, `validation-api` ou o índice do README raiz.

</intent-contract>

## Code Map

- `validation/src/main/java/.../valueobjects/` -- `Cpf`, `Cnpj`, `Email`, `TaxIdentifier` (`@Embeddable`)
- `validation/src/main/java/.../taxidentifier/constraint/`, `.../zipcode/constraint/` -- 4 `ConstraintValidator`s
- `validation/src/main/resources/META-INF/validation.xml` -- liga anotação a validador
- `validation-api/README.md`, `spring/README.md` -- modelo de estilo

## Tasks & Acceptance

**Execution:**
- `valueobjects/*.java`, `*Validator.java` -- Javadoc + comentários inline
- `validation/README.md` -- novo, com diagrama Mermaid

**Acceptance Criteria:**
- Given o módulo `validation`, when a documentação é adicionada, then toda API pública tem Javadoc, decisões não óbvias têm comentário inline e o README traz diagrama Mermaid.

## Review Triage Log

Revisão adversarial feita inline (sem subagentes), 5 achados:
1. Javadoc dos validadores usava `@param value` com nome errado (checkstyle `JavadocMethod`) -- `patch`, corrigido.
2. Comentário do `ZipCodeValidator` dizia que `$` casa o valor inteiro; em Java também casa antes de `\n` final -- `patch`, comentário corrigido; o comportamento (aceita `"01001000\n"`) -- `defer`.
3. `Cpf`/`Cnpj.setTaxIdentifier` (nome copiado) -- `defer`.
4. `null` em `CpfValidator`/`CnpjValidator`/`TaxIdentifierValidator` lança exceção em vez de ser tratado (convenção Bean Validation); `ZipCode` rejeita `null` -- documentado, correção `defer`.
5. Seção do README raiz sem `validation` -- `defer` (já registrado em 4.2/4.5).

## Verification

- `mvn -pl validation -am test` -- verde
- checkstyle do perfil `analyze` -- sem violações de Javadoc
