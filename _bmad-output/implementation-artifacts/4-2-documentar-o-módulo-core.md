# Story 4.2: Documentar o módulo `core`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor avaliando o `core` antes de importar,
Eu quero Javadoc completo, comentários onde a lógica não é óbvia, README e diagrama de fluxo,
Para entender o contrato sem ler a implementação.

## Acceptance Criteria

1. **Given** o módulo `core` (Epic 1, Story 1.7; Epic 2, Story 2.8), **When** a documentação é adicionada, **Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso.

## Tasks / Subtasks

- [ ] Task 1: Confirmar pré-requisito — módulo `core` existe (AC: #1)
  - [ ] **Confirmado por leitura direta do repositório**: o módulo `core` (diretório `core/`, `pom.xml` próprio) **ainda não existe** neste repositório — ele nasce na Story 1.7 (extração de `DateUtils`/`HashUtils`/`StringFieldUtils`/`PropertiesOrder`/`ScosBaseUseCase`/`ScosUserAuthentication`) e recebe as classes de exceção de domínio na Story 2.8 (`ScosException`, `ExceptionCode`, `ScosExceptionCode`, `LocaleService`, `ScosNoContentException`, `ScosNoRollbackException`, `ScosSecurityException`, `MethodNotImplementedException`)
  - [ ] Não iniciar esta story antes de 1.7 e 2.8 estarem implementadas (`in-progress`/`done` no sprint-status.yaml) — esta story documenta um módulo que precisa já existir com suas classes finais
- [ ] Task 2: Javadoc em toda API pública do `core` (AC: #1)
  - [ ] Adicionar/revisar Javadoc de classe (resumo, `@since 1.2.0` seguindo o padrão já usado em `audit` — ex.: `ScosAuditQueryService.java`) e de método público em todas as classes migradas para `core`
  - [ ] Cobrir tanto as classes utilitárias (Stories 1.1/1.7) quanto o contrato de exceção (Story 2.8)
- [ ] Task 3: Comentários inline onde a lógica não é óbvia (AC: #1)
  - [ ] Revisar cada classe migrada por decisões não-óbvias herdadas do código original (ex.: por que `HashUtils` usa SHA-256 e não outro algoritmo, por que `ScosUserAuthentication` tem o formato que tem) e comentar só onde o "porquê" não é evidente pelo nome/estrutura
- [ ] Task 4: README com diagrama Mermaid (AC: #1)
  - [ ] Criar `core/README.md` (módulo novo, sem README herdado) descrevendo o propósito (zero dependência de Spring/JPA/Servlet — regra ArchUnit local da Story 1.7) e um diagrama Mermaid do fluxo típico (ex.: consumidor importa `core` isoladamente → usa `DateUtils`/`HashUtils` sem carregar o resto da stack)
  - [ ] Seguir o padrão de README já estabelecido em `audit/README.md` (seções: dependência Maven, exemplos de uso, troubleshooting) como referência de estilo, adaptado ao escopo de um módulo sem Spring

## Dev Notes

- Esta story só pode rodar depois que `core` já contiver seu conteúdo final (pós Stories 1.7 e 2.8) — documentar antes disso arrisca documentar um estado transitório.
- Padrão de Javadoc já estabelecido no repositório (seguir, não reinventar): ver `audit/src/main/java/.../specification/ScosAuditQueryService.java` — resumo curto, `<p>` para detalhe, tag `@since`.
- `core` não tem README hoje porque o módulo não existe — este é o primeiro README do módulo, não uma atualização.

### Project Structure Notes

- Arquivo novo: `core/README.md`.
- Arquivos modificados: as classes públicas de `core` (Javadoc adicionado/revisado).

### References

- [Source: _bmad-output/implementation-artifacts/1-7-extrair-o-módulo-core.md]
- [Source: _bmad-output/implementation-artifacts/2-8-mover-o-contrato-de-domínio-do-exception-para-o-core.md]
- [Source: audit/src/main/java/br/com/sawcunhaos/foundation/audit/specification/ScosAuditQueryService.java] (padrão de Javadoc a seguir)
- [Source: audit/README.md] (padrão de estrutura de README a seguir)
- [Source: _bmad-output/planning-artifacts/epics.md#story-42-documentar-o-módulo-core]
- [Source: _bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/prd.md] (NFR7: piso de documentação obrigatório, bloqueia release 1.2.0)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
