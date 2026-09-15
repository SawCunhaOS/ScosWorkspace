# Story 4.3: Documentar o módulo `audit-api`

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor de domínio puro,
Eu quero saber pelo README que este artefato não executa nada sozinho,
Para não integrá-lo sem a implementação correspondente.

## Acceptance Criteria

1. **Given** o módulo `audit-api` (Epic 1, Story 1.5), **When** a documentação é adicionada, **Then** o README abre com "este artefato não executa nada; a implementação é `scos-foundation-audit`" e traz diagrama Mermaid do fluxo típico de uso.
2. **And** toda anotação pública tem Javadoc.

## Tasks / Subtasks

- [x] Task 1: Confirmar pré-requisito (AC: #1)
  - [x] **Confirmado por leitura direta (nesta execução)**: o módulo `audit-api` já existe (Story 1.5, `done`), com `Auditable.java`, `AuditAction.java`, `ArchitectureTest.java` e um `README.md` já criado — restava só o diagrama Mermaid e o Javadoc de tipo.
  - [x] Story 1.5 confirmada `done` no `sprint-status.yaml` antes de iniciar.
- [x] Task 2: README com frase de abertura obrigatória e diagrama (AC: #1)
  - [x] `audit-api/README.md` já abria com a frase exigida (pré-existente) — não alterada.
  - [x] Seção "Fluxo típico de uso" com diagrama Mermaid adicionada, no padrão de `core/README.md` (Story 4.2): app consumidora anota `@Auditable` → efeito só com `scos-foundation-audit` no classpath (listener Hibernate para C/U/D + `auditRead()`, invocação de leitura por método definida pela implementação).
- [x] Task 3: Javadoc em toda anotação pública (AC: #2)
  - [x] Javadoc de tipo adicionado em `Auditable` e em `AuditAction`, explicando o contrato sem descrever a implementação — ver Completion Notes para o ajuste feito após revisão.

## Dev Notes

- Não se aplica o gate de cobertura Jacoco (NFR3) aqui — módulo `*-api` não tem lógica de runtime, só `@interface`/`enum` (regra ArchUnit local da Story 1.5).
- A frase de abertura do README é um requisito literal repetido em várias stories deste epic (4.3, 4.4, 4.5) e também na Story 1.15 (log de inicialização) — manter a redação idêntica entre os três READMEs `*-api`, trocando só o nome do módulo de implementação.

### Project Structure Notes

- Arquivo novo: `audit-api/README.md`.
- Javadoc adicionado às anotações movidas para `audit-api`.

### References

- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/1-5-criar-módulos-api-e-mover-as-anotações-de-contrato.md]
- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/1-15-emitir-log-de-inicialização-por-módulo-de-implementação.md] (mesma frase de abertura exigida)
- [Source: _bmad-output/SawCunhaOS-Foundation/planning-artifacts/epics.md#story-43-documentar-o-módulo-audit-api]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (bmad-build, rota oneshot)

### Debug Log References

### Completion Notes List

- Javadoc de tipo em `Auditable`/`AuditAction`; diagrama Mermaid no README. `mvn -pl audit-api -am test` verde (`ArchitectureTest`, 2 testes) antes e depois da revisão.
- Revisão blind-hunter encontrou que a primeira versão do Javadoc de `Auditable` afirmava disparo automático de auditoria de leitura no nível de método — não existe (nenhum `@Aspect` no módulo `audit`; único uso de `@Auditable(action=READ)` do repositório nunca é chamado por teste). Reescrito para não afirmar automação nesse nível e para citar `auditRead()` (o caminho de leitura de fato automático, no nível de tipo). Diagrama ajustado no mesmo sentido; nome de classe concreta removido do diagrama (mantida a descrição genérica "listener Hibernate" já pedida pela story). Javadoc por constante de `AuditAction` removido (só reafirmava o nome, sem informação nova). Detalhe completo: `## Review Triage Log` da spec.
- Achado real, mas fora de escopo, adiado para `deferred-work.md`: o caminho `@Auditable(action = AuditAction.READ)` não é processado por nada em tempo de execução no módulo `audit` — a classe `ScosAuditReadAspect`, citada em Javadoc pré-existente (`ActionType.SELECT`), não existe no código.
- Spec completa: `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/spec-4-3-documentar-o-módulo-audit-api.md`.

### File List

- `audit-api/src/main/java/br/com/sawcunhaos/foundation/audit/api/Auditable.java` (Javadoc de tipo)
- `audit-api/src/main/java/br/com/sawcunhaos/foundation/audit/api/AuditAction.java` (Javadoc de tipo)
- `audit-api/README.md` (seção "Fluxo típico de uso" com diagrama Mermaid)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/deferred-work.md` (achado adiado)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/sprint-status.yaml` (status da story)
