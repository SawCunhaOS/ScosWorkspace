# Story 4.4: Documentar o módulo `jdempotent-api`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor de domínio puro,
Eu quero saber pelo README que este artefato não executa nada sozinho,
Para não integrá-lo sem a implementação correspondente.

## Acceptance Criteria

1. **Given** o módulo `jdempotent-api` (Epic 1, Story 1.5), **When** a documentação é adicionada, **Then** o README abre com "este artefato não executa nada; a implementação é `scos-foundation-jdempotent`" e traz diagrama Mermaid do fluxo típico de uso.
2. **And** toda anotação pública tem Javadoc.

## Tasks / Subtasks

- [ ] Task 1: Confirmar pré-requisito (AC: #1)
  - [ ] **Confirmado por leitura direta**: `jdempotent-api` **ainda não existe** — nasce na Story 1.5, movendo as anotações `@Jdempotent*` (5 anotações hoje em `utils/src/main/java/.../annotation/jdempotent/`, confirmado via `find`) para este módulo
  - [ ] Este módulo também recebe, mais tarde no Epic 3, o novo atributo/anotação `@JdempotentProperty` (Story 3.12) — se a Story 3.12 já estiver implementada quando esta story rodar, documentar também essa anotação; se não, documentar só o que existir no momento
- [ ] Task 2: README com frase de abertura obrigatória e diagrama (AC: #1)
  - [ ] Criar `jdempotent-api/README.md` iniciando com "este artefato não executa nada; a implementação é `scos-foundation-jdempotent`"
  - [ ] Diagrama Mermaid: aplicação anota método com `@JdempotentResource`/`@JdempotentId`/`@JdempotentProperty` (vindo de `jdempotent-api`) → precisa de `scos-foundation-jdempotent` no classpath para o aspecto interceptar e aplicar a lógica de idempotência
- [ ] Task 3: Javadoc em toda anotação pública (AC: #2)
  - [ ] Cobrir as 5 anotações originais e, se já existir no momento da implementação, `@JdempotentProperty` (Story 3.12) — Javadoc de contrato, não de implementação

## Dev Notes

- Mesma regra das demais stories `*-api` (4.3, 4.5): sem gate de cobertura Jacoco, só `@interface`/`enum`.
- Se a Story 3.13 (header `Idempotency-Key`) já tiver introduzido o atributo `keySource`/`onMismatch` em `@JdempotentResource` no momento desta documentação, cobrir esses atributos também — este módulo evolui ao longo do Epic 3, então o Javadoc deve refletir o estado real das anotações no momento em que esta story roda, não uma foto congelada do epics.md.

### Project Structure Notes

- Arquivo novo: `jdempotent-api/README.md`.
- Javadoc adicionado às anotações movidas/criadas em `jdempotent-api`.

### References

- [Source: _bmad-output/implementation-artifacts/1-5-criar-módulos-api-e-mover-as-anotações-de-contrato.md]
- [Source: _bmad-output/implementation-artifacts/3-12-introduzir-idempotencykeyresolver-com-composição-de-chave-de.md] (possível anotação adicional a documentar)
- [Source: _bmad-output/implementation-artifacts/3-13-suportar-header-idempotency-key-como-fonte-de-chave.md] (possíveis atributos adicionais)
- [Source: _bmad-output/planning-artifacts/epics.md#story-44-documentar-o-módulo-jdempotent-api]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
