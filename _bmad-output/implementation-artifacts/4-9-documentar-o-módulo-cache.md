# Story 4.9: Documentar o módulo `cache`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor usando cache Redis,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender a configuração de `PolymorphicRedisSerializer`.

## Acceptance Criteria

1. **Given** o módulo `cache` (Epic 1, Story 1.10), **When** a documentação é adicionada, **Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso.

## Tasks / Subtasks

- [ ] Task 1: Confirmar pré-requisito (AC: #1)
  - [ ] **Confirmado por leitura direta**: `cache` **ainda não existe** — nasce na Story 1.10, recebendo `PolymorphicRedisSerializer` e demais classes de `configuration/cache/*` (hoje em `utils/src/main/java/.../configuration/cache/`, confirmado via `find`, 5 classes), dependendo só de `core`
  - [ ] Se a Story 3.16 (allowlist de tipos no `PolymorphicRedisSerializer`) já estiver implementada quando esta story rodar, documentar a allowlist como parte do contrato de segurança da classe — é uma mudança de comportamento relevante para quem lê o Javadoc
- [ ] Task 2: Javadoc em toda API pública (AC: #1)
  - [ ] Cobrir as 5 classes de `configuration/cache/*`, com atenção especial a `PolymorphicRedisSerializer` — documentar explicitamente o contrato de segurança (allowlist de tipos, se já implementada) no Javadoc da classe, não só o comportamento de serialização
- [ ] Task 3: Comentários inline onde a lógica não é óbvia (AC: #1)
  - [ ] Comentar a decisão de desserialização polimórfica e, se aplicável, por que a allowlist existe (achado de segurança da Story 3.16 — `Class.forName` sobre valor vindo do Redis sem allowlist antes)
- [ ] Task 4: README com diagrama Mermaid (AC: #1)
  - [ ] Criar `cache/README.md` explicando o propósito (cache Redis isolado, sem herdar JPA)
  - [ ] Diagrama Mermaid: aplicação grava objeto polimórfico no Redis via `PolymorphicRedisSerializer` → leitura desserializa checando a allowlist (se já implementada) → rejeita tipo fora da allowlist

## Dev Notes

- Esta story só pode rodar depois da Story 1.10 (extração do módulo).
- Dependência cruzada com o Epic 3: `PolymorphicRedisSerializer` é tocado pela Story 3.16 (allowlist) — se 3.16 já estiver `done`/`in-progress` no momento desta documentação, refletir a allowlist no Javadoc; se não, documentar o estado atual e não inventar a allowlist antes de existir.

### Project Structure Notes

- Arquivo novo: `cache/README.md`.
- Javadoc adicionado às classes de `cache`.

### References

- [Source: _bmad-output/implementation-artifacts/1-10-extrair-o-módulo-cache.md]
- [Source: _bmad-output/implementation-artifacts/3-16-adicionar-allowlist-de-tipos-no-polymorphicredisserializer.md] (dependência cruzada condicional)
- [Source: _bmad-output/planning-artifacts/epics.md#story-49-documentar-o-módulo-cache]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
