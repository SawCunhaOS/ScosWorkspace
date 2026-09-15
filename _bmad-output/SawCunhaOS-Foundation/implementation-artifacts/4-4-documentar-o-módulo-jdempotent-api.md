# Story 4.4: Documentar o módulo `jdempotent-api`

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor de domínio puro,
Eu quero saber pelo README que este artefato não executa nada sozinho,
Para não integrá-lo sem a implementação correspondente.

## Acceptance Criteria

1. **Given** o módulo `jdempotent-api` (Epic 1, Story 1.5), **When** a documentação é adicionada, **Then** o README abre com "este artefato não executa nada; a implementação é `scos-foundation-jdempotent`" e traz diagrama Mermaid do fluxo típico de uso.
2. **And** toda anotação pública tem Javadoc.

## Tasks / Subtasks

- [x] Task 1: Confirmar pré-requisito (AC: #1)
  - [x] **Confirmado por leitura direta (nesta execução)**: `jdempotent-api` já existe (Story 1.5, `done`), com as 5 anotações `@Jdempotent*` e os 3 enums de apoio.
  - [x] `@JdempotentProperty` (Story 3.12) e os atributos `keySource`/`headerName`/`onMismatch` (Story 3.13) já existem no código atual, apesar de ambas as stories ainda estarem `review` no sprint-status — documentado o estado real do código, não o epics.md congelado.
- [x] Task 2: README com frase de abertura obrigatória e diagrama (AC: #1)
  - [x] `jdempotent-api/README.md` já abria com a frase exigida (pré-existente) — não alterada.
  - [x] Seção "Fluxo típico de uso" com diagrama Mermaid adicionada, no padrão de `audit-api/README.md`: app consumidora anota cada `@Jdempotent*` → efeito só com `scos-foundation-jdempotent` no classpath (aspecto AOP que calcula o hash da chave).
- [x] Task 3: Javadoc em toda anotação pública (AC: #2)
  - [x] Cobertas as 5 anotações originais e `@JdempotentProperty` — só `JdempotentIgnore` e `JdempotentProperty` (tipo e atributo `value()`) precisavam de Javadoc novo/reescrito; as demais já estavam completas e verificadas consistentes com o código real.

## Dev Notes

- Mesma regra das demais stories `*-api` (4.3, 4.5): sem gate de cobertura Jacoco, só `@interface`/`enum`.
- Se a Story 3.13 (header `Idempotency-Key`) já tiver introduzido o atributo `keySource`/`onMismatch` em `@JdempotentResource` no momento desta documentação, cobrir esses atributos também — este módulo evolui ao longo do Epic 3, então o Javadoc deve refletir o estado real das anotações no momento em que esta story roda, não uma foto congelada do epics.md.

### Project Structure Notes

- Arquivo novo: `jdempotent-api/README.md`.
- Javadoc adicionado às anotações movidas/criadas em `jdempotent-api`.

### References

- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/1-5-criar-módulos-api-e-mover-as-anotações-de-contrato.md]
- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/3-12-introduzir-idempotencykeyresolver-com-composição-de-chave-de.md] (possível anotação adicional a documentar)
- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/3-13-suportar-header-idempotency-key-como-fonte-de-chave.md] (possíveis atributos adicionais)
- [Source: _bmad-output/SawCunhaOS-Foundation/planning-artifacts/epics.md#story-44-documentar-o-módulo-jdempotent-api]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (bmad-build, rota oneshot)

### Debug Log References

### Completion Notes List

- Diagrama Mermaid ("Fluxo típico de uso") adicionado ao README; Javadoc de tipo reescrito em `JdempotentIgnore`/`JdempotentProperty`; Javadoc adicionado ao atributo `JdempotentProperty.value()`. `mvn -pl jdempotent-api -am test` verde (`ArchitectureTest`, 2 regras) antes e depois da revisão.
- Antes de escrever o Javadoc, verificada no módulo de implementação (`jdempotent/.../core/chain/`) a semântica real: `@JdempotentProperty` com `value()` vazio (default) tem o mesmo efeito prático de `@JdempotentIgnore` — campo excluído do hash porque a chave blank é descartada pelo filtro do aspecto (confirmado por teste da Story 3.20). `@JdempotentIgnore` tem precedência sobre `@JdempotentProperty` quando ambas anotam o mesmo campo (ordem da chain). Ambos os fatos documentados explicitamente, pois o Javadoc anterior não os mencionava.
- Revisão blind-hunter encontrou 8 achados: 6 aplicados como patch simples (aresta faltante no diagrama para `@JdempotentRequestPayload`, rótulo do aspecto incompleto sobre `keySource`, `@return` vazio em `value()`, precedência Ignore/Property não documentada, colisão silenciosa de `value()` duplicado, e reformulação de rótulo de aresta), 1 fora de escopo adiado para `deferred-work.md` (tabela "Conteúdo" não atualizada — vedado pelo Approach congelado da spec), e 1 verificado como falso (citar "Story 3.12" em `JdempotentIgnore`/`JdempotentProperty` — ambos os arquivos existem desde o commit inicial do projeto, antes de qualquer story numerada). Detalhe completo: `## Review Triage Log` da spec.
- Spec completa: `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/spec-4-4-documentar-o-módulo-jdempotent-api.md`.

### File List

- `jdempotent-api/README.md` (seção "Fluxo típico de uso" com diagrama Mermaid)
- `jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/JdempotentIgnore.java` (Javadoc de tipo)
- `jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/JdempotentProperty.java` (Javadoc de tipo e do atributo `value()`)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/deferred-work.md` (achado adiado)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/sprint-status.yaml` (status da story)
