# Story 4.14: Documentar o módulo `audit`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor usando auditoria,
Eu quero um diagrama de fluxo de uso,
Para entender o fluxo sem ler o código.

## Acceptance Criteria

1. **Given** o módulo `audit` (README já existente, repontado para `core` na Story 2.8), **When** o diagrama Mermaid é adicionado ao README, **Then** o README passa a ter o diagrama do fluxo típico de uso.
2. **And** toda API pública mantém Javadoc (gate já ativo).

## Tasks / Subtasks

- [ ] Task 1: Confirmar o estado real do README e do Javadoc antes de mexer (AC: #1, #2)
  - [ ] **Confirmado por leitura direta**: `audit/README.md` já existe e é extenso (324 linhas) — cobre arquitetura interna, configuração, exemplos de uso, tuning, troubleshooting e migrations
  - [ ] **Confirmado por leitura direta**: o README já tem um diagrama, mas em **ASCII art puro** (seção "Arquitetura interna (v1.2.0)", linhas 9-49), não em Mermaid — o AC pede diagrama Mermaid especificamente, então a ASCII art existente não satisfaz o AC como está; decidir entre converter a ASCII existente para Mermaid ou adicionar um `sequenceDiagram`/`flowchart` Mermaid complementar sem remover a ASCII (a ASCII já é detalhada e legível em texto puro/terminal — avaliar se vale preservar como referência rápida e adicionar o Mermaid como visualização alternativa, ou substituir; documentar a decisão tomada nas Completion Notes)
  - [ ] **Confirmado por leitura direta**: `ScosAuditQueryService.java` (interface pública) já tem Javadoc de classe com `@since 1.2.0` — o gate de Javadoc já parece cumprido nas classes-chave amostradas; fazer uma varredura completa em todas as classes públicas do módulo antes de assumir 100% de cobertura (a amostra não é exaustiva)
- [ ] Task 2: Adicionar diagrama Mermaid do fluxo típico de uso (AC: #1)
  - [ ] Converter (ou complementar) o diagrama ASCII já existente em `audit/README.md` para um `flowchart`/`sequenceDiagram` Mermaid cobrindo o mesmo fluxo já documentado: produção de eventos (`@Auditable` entidade/método) → `ScosAuditServiceBean` → `ScosAuditQueue` → `ScosAuditBatchConsumer` (hash-chain opcional) → `SFA_LOG_AUDIT`/`SFA_AUDIT_DLQ` → consulta/integridade
  - [ ] Preservar o conteúdo textual já existente (configuração, exemplos de código, troubleshooting) — esta story só adiciona/converte o diagrama, não reescreve o README inteiro
- [ ] Task 3: Varredura completa de Javadoc em API pública (AC: #2)
  - [ ] Confirmar (não assumir a partir da amostra) que toda classe/interface/método público de `audit` tem Javadoc — preencher qualquer lacuna encontrada, já que o gate está descrito como "já ativo" mas isso não foi confirmado exaustivamente aqui

## Dev Notes

- Esta é uma das duas únicas stories do epic (junto da 4.15) que documenta um módulo **já existente e não tocado estruturalmente** por este ciclo — a mudança aqui é estritamente aditiva (diagrama) e de verificação (Javadoc), não uma documentação do zero como a maioria das outras stories deste epic.
- `audit` é repontado para consumir `ScosException` do `core` na Story 2.8 — se essa story já tiver rodado quando esta documentação for feita, mencionar no README que `audit` depende de `core` para o contrato de exceção (mudança de dependência relevante para quem lê o README).

### Project Structure Notes

- Arquivo modificado: `audit/README.md` (diagrama Mermaid adicionado/convertido; conteúdo textual existente preservado).
- Possíveis pequenos ajustes de Javadoc em classes públicas não cobertas (a confirmar na Task 3).

### References

- [Source: audit/README.md] (README existente, 324 linhas, diagrama ASCII nas linhas 9-49)
- [Source: audit/src/main/java/br/com/sawcunhaos/foundation/audit/specification/ScosAuditQueryService.java] (Javadoc já presente, amostra confirmada)
- [Source: _bmad-output/implementation-artifacts/2-8-mover-o-contrato-de-domínio-do-exception-para-o-core.md] (dependência cruzada condicional)
- [Source: _bmad-output/planning-artifacts/epics.md#story-414-documentar-o-módulo-audit]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
