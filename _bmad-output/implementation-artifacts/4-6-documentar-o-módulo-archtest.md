# Story 4.6: Documentar o módulo `archtest`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor entendendo a suíte de regras cross-módulo,
Eu quero um README explicando o propósito do módulo,
Para saber onde adicionar uma nova regra ArchUnit cross-módulo.

## Acceptance Criteria

1. **Given** o módulo `archtest` (Epic 1, Story 1.6), **When** a documentação é adicionada, **Then** o README explica o propósito (regras ArchUnit cross-módulo, sem código de produção) e lista as regras existentes.
2. **And** não se aplica gate de Javadoc (módulo sem API pública de produção).

## Tasks / Subtasks

- [ ] Task 1: Confirmar pré-requisito (AC: #1)
  - [ ] **Confirmado por leitura direta**: `archtest` **ainda não existe** — nasce na Story 1.6 (`scope=test`, sem código de produção) e recebe suas primeiras regras cross-módulo na Story 1.14 (proibição de depender de `web`, proibição de ciclo)
  - [ ] Esta story deve rodar depois da Story 1.14, para que o README já liste as regras reais existentes, não um placeholder
- [ ] Task 2: README explicando propósito e listando regras (AC: #1)
  - [ ] Criar `archtest/README.md` explicando: por que este módulo existe (nenhum módulo de implementação individual enxerga o classpath inteiro sozinho, então regras que citam mais de um módulo — ex.: "nada depende de `web`", "sem ciclo entre módulos" — precisam de um módulo dedicado que dependa de todos os outros só para teste)
  - [ ] Listar as regras existentes no momento (as da Story 1.14: proibição de dependência de `web` fora de aplicações consumidoras, proibição de ciclo) com uma frase de propósito cada
  - [ ] Explicar onde adicionar uma nova regra cross-módulo futura (mesmo módulo, não duplicar a regra dentro de um módulo de implementação individual — é a distinção que a Story 1.6/1.14 já estabelece entre regra local por módulo e regra cross-módulo)
- [ ] Task 3: Confirmar que o gate de Javadoc não se aplica (AC: #2)
  - [ ] Nenhuma ação de código necessária — só documentar explicitamente no README que este módulo é `scope=test` e por isso está fora do escopo do Checkstyle/Javadoc obrigatório (mesma exceção que os módulos de teste normalmente têm)

## Dev Notes

- Ordem de dependência: esta story só faz sentido depois da Story 1.14 (regras cross-módulo já existentes) — documentar antes disso resultaria num README sem conteúdo real para listar.
- Diferente das stories `*-api` (4.3-4.5), aqui não há frase de abertura obrigatória — o propósito é distinto (suíte de teste, não contrato de anotação sem implementação).

### Project Structure Notes

- Arquivo novo: `archtest/README.md`.
- Nenhuma alteração de código (módulo já sem Javadoc exigido).

### References

- [Source: _bmad-output/implementation-artifacts/1-6-criar-o-módulo-archtest-para-regras-cross-módulo.md]
- [Source: _bmad-output/implementation-artifacts/1-14-impor-regras-archunit-cross-módulo-e-remover-utils-do-reacto.md] (regras reais a listar)
- [Source: _bmad-output/planning-artifacts/epics.md#story-46-documentar-o-módulo-archtest]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
