# Story 4.12: Documentar o módulo `feign`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor integrando via Feign,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender `JacksonEncoderCustom`/`DecoderCustom`.

## Acceptance Criteria

1. **Given** o módulo `feign` (Epic 1, Story 1.13), **When** a documentação é adicionada, **Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso.

## Tasks / Subtasks

- [ ] Task 1: Confirmar pré-requisito (AC: #1)
  - [ ] **Confirmado por leitura direta**: `feign` **ainda não existe** — nasce na Story 1.13, recebendo `JacksonEncoderCustom`, `JacksonDecoderCustom` (hoje em `utils/src/main/java/.../configuration/feign/`, confirmado via `find`, 2 classes), dependendo só de `core`
- [ ] Task 2: Javadoc em toda API pública (AC: #1)
  - [ ] Cobrir `JacksonEncoderCustom`/`JacksonDecoderCustom` — documentar a customização em relação ao encoder/decoder Feign padrão e a relação com a migração Gson→Jackson (Story 1.3)
- [ ] Task 3: Comentários inline onde a lógica não é óbvia (AC: #1)
  - [ ] Comentar qualquer tratamento de erro/exceção específico do encoder/decoder que não seja óbvio pela assinatura
- [ ] Task 4: README com diagrama Mermaid (AC: #1)
  - [ ] Criar `feign/README.md` explicando o propósito (integração Feign isolada, sem forçar essa dependência em quem usa só `web`/`core`)
  - [ ] Diagrama Mermaid: cliente Feign da aplicação → `JacksonEncoderCustom` (request) / `JacksonDecoderCustom` (response) → serviço remoto

## Dev Notes

- Esta story só pode rodar depois da Story 1.13 (extração do módulo).
- Menor módulo do epic em número de classes (2) — manter a documentação proporcional ao escopo, sem inflar Dev Notes além do necessário.

### Project Structure Notes

- Arquivo novo: `feign/README.md`.
- Javadoc adicionado às 2 classes de `feign`.

### References

- [Source: _bmad-output/implementation-artifacts/1-13-extrair-o-módulo-feign.md]
- [Source: _bmad-output/implementation-artifacts/1-3-migrar-serialização-json-de-gson-para-jackson.md] (contexto da customização Jackson)
- [Source: _bmad-output/planning-artifacts/epics.md#story-412-documentar-o-módulo-feign]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
