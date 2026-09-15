# Story 4.2: Documentar o módulo `core`

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor avaliando o `core` antes de importar,
Eu quero Javadoc completo, comentários onde a lógica não é óbvia, README e diagrama de fluxo,
Para entender o contrato sem ler a implementação.

## Acceptance Criteria

1. **Given** o módulo `core` (Epic 1, Story 1.7; Epic 2, Story 2.8), **When** a documentação é adicionada, **Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso.

## Tasks / Subtasks

- [x] Task 1: Confirmar pré-requisito — módulo `core` existe (AC: #1)
  - [x] **Confirmado por leitura direta do repositório** (nesta execução): o módulo `core` já existe, com os 17 arquivos esperados das Stories 1.7 e 2.8 (`DateUtils`, `HashUtils`, `StringFieldUtils`, `PropertiesOrder`, `ScosBaseUseCase`, `ScosUserAuthentication`, `Constant`, `ScosExceptionCode`, `SpecificationFunction`, `ValueType`, `ScosException`, `ExceptionCode`, `LocaleService`, `MethodNotImplementedException`, `ScosNoContentException`, `ScosNoRollbackException`, `ScosSecurityException`).
  - [x] 1.7 e 2.8 confirmadas `done` no `sprint-status.yaml` antes de iniciar.
- [x] Task 2: Javadoc em toda API pública do `core` (AC: #1)
  - [x] Javadoc de classe/interface/enum e de todo método/constante pública ainda sem documentação, com `@since 1.2.0` (padrão de `audit/ScosAuditQueryService.java`) — ver Completion Notes para a verificação de que `1.2.0` é o valor correto (o módulo `core` não existe nas releases `1.0.0`/`1.1.0`).
  - [x] Cobre tanto as classes utilitárias (Stories 1.1/1.7) quanto o contrato de exceção (Story 2.8).
- [x] Task 3: Comentários inline onde a lógica não é óbvia (AC: #1)
  - [x] Comentários adicionados nos pontos não-óbvios reais (ver Completion Notes): overloads de `isDateValid`, exceções-marcador vazias, reflection em `StringFieldUtils`, motivo do enum `Constant`, contratos de `PropertiesOrder`/`SpecificationFunction`/`ScosUserAuthentication`, ausência de limite inferior em `isDateValid(day, month)`, branch morto no mesmo método, `NullPointerException` não documentado em `HashUtils.createHash`.
- [x] Task 4: README com diagrama Mermaid (AC: #1)
  - [x] `core/README.md` criado com diagrama Mermaid do fluxo típico, seção de dependência Maven, utilitários, enums, exceções (RFC 9457), contratos a implementar e troubleshooting — seguindo a estrutura de seções de `audit/README.md` adaptada (sem Spring/JPA).

## Dev Notes

- Esta story só pode rodar depois que `core` já contiver seu conteúdo final (pós Stories 1.7 e 2.8) — documentar antes disso arrisca documentar um estado transitório.
- Padrão de Javadoc já estabelecido no repositório (seguir, não reinventar): ver `audit/src/main/java/.../specification/ScosAuditQueryService.java` — resumo curto, `<p>` para detalhe, tag `@since`.
- `core` não tem README hoje porque o módulo não existe — este é o primeiro README do módulo, não uma atualização.

### Project Structure Notes

- Arquivo novo: `core/README.md`.
- Arquivos modificados: as classes públicas de `core` (Javadoc adicionado/revisado).

### References

- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/1-7-extrair-o-módulo-core.md]
- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/2-8-mover-o-contrato-de-domínio-do-exception-para-o-core.md]
- [Source: audit/src/main/java/br/com/sawcunhaos/foundation/audit/specification/ScosAuditQueryService.java] (padrão de Javadoc a seguir)
- [Source: audit/README.md] (padrão de estrutura de README a seguir)
- [Source: _bmad-output/SawCunhaOS-Foundation/planning-artifacts/epics.md#story-42-documentar-o-módulo-core]
- [Source: _bmad-output/SawCunhaOS-Foundation/planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/prd.md] (NFR7: piso de documentação obrigatório, bloqueia release 1.2.0)

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

### Completion Notes List

- Javadoc adicionado em todo método/classe/interface/enum público de `core` ainda sem documentação (12 dos 17 arquivos estavam total ou parcialmente sem Javadoc), com `@since 1.2.0`, seguindo o padrão de `audit/ScosAuditQueryService.java`. **Verificado, não só copiado**: o revisor (blind-hunter) apontou que a maioria das classes "existe desde 1.0.0/1.1.0"; conferido via `git ls-tree`/`pom.xml` de cada tag que o módulo `core` (artefato `scos-foundation-core`) **não existe em nenhuma das tags `1.0.0`/`1.1.0`** — as classes com histórico anterior viviam em módulos diferentes (`exception`, `utils`) com FQN diferente, e `StringFieldUtils` mudou de assinatura ao migrar (Story 1.7). `@since 1.2.0` está correto para as 17 classes.
- Comentários inline adicionados nos pontos não-óbvios: os dois overloads de `isDateValid` (bissexto-aware vs. não, e a ausência de limite inferior no overload de 2 args — `isDateValid(0, 1)`/`isDateValid(-5, 3)` retornam `true`), um branch morto/redundante no mesmo método (`day <= MONTH_30_DAY && MONTHS_31_DAYS.contains(month)` nunca é alcançado), as exceções-marcador vazias (`ScosNoContentException` → HTTP 204; `ScosNoRollbackException` → pensada para `@Transactional(noRollbackFor=...)`; `ScosSecurityException` → sem uso ainda), o motivo do enum `Constant` de uma constante só, o contrato de `PropertiesOrder`/`SpecificationFunction`/`ScosUserAuthentication` (confirmado lendo os consumidores reais em `web.PaginationUtils`, `jpa.SpecificationRepository`, `audit.ScosHibernateAuditListener`), `HashUtils.createHash` lançando `NullPointerException` não documentado antes, e a reflection insegura de `StringFieldUtils.applyTransformation` (comentário `//` da Story 1.7 virou Javadoc do método público, texto preservado).
- `isWeenkend` (typo histórico) **não foi renomeado** — fora de escopo de uma story de documentação; documentado com nota explicando o nome. Nenhuma classe foi renomeada ou removida.
- Observação para triagem futura (não bloqueia esta story): `ValueType`, `ScosSecurityException` e `ScosBaseUseCase` não têm nenhum consumidor encontrado no reactor; `HashUtils` não tem teste próprio (`HashUtilsTest` não existe). Documentadas normalmente como API pública (com nota de "sem uso hoje" no Javadoc, por transparência), sem remover nada.
- `core/README.md` criado (módulo não tinha nenhum) com diagrama Mermaid do fluxo típico (um nó por contrato de `specification`, com as setas reais de injeção em `web`/`audit`/`jpa`), dependência Maven, seção de enums, utilitários, exceções RFC 9457, tabela de contratos a implementar e troubleshooting.
- Revisão (blind-hunter): 11 achados — 1 falso (o `@since` em massa, ver acima), 1 adiado (`README.md` raiz não lista `core` nem outros módulos do Epic 1 — pré-existente, cross-cutting, registrado em `deferred-work.md`), 9 corrigidos diretamente (detalhe completo no Review Triage Log do spec).
- `mvn -pl core -am compile` e `mvn -pl core test` verdes antes e depois dos patches da revisão (`ArchitectureTest`/`noSpringNoJpaNoServlet` incluído — nenhum import de Spring/JPA/Servlet introduzido).

### File List

- `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/Constant.java` (Javadoc)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ScosExceptionCode.java` (`@since`)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/SpecificationFunction.java` (Javadoc)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ValueType.java` (Javadoc)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/MethodNotImplementedException.java` (Javadoc)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/ScosException.java` (Javadoc, incl. campos)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/ScosNoContentException.java` (Javadoc)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/ScosNoRollbackException.java` (Javadoc)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/ScosSecurityException.java` (Javadoc)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/sort/PropertiesOrder.java` (Javadoc)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/specification/ExceptionCode.java` (Javadoc de `getHttpCode`, `@since`)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/specification/LocaleService.java` (Javadoc)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/specification/ScosBaseUseCase.java` (Javadoc)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/specification/ScosUserAuthentication.java` (Javadoc)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/utils/DateUtils.java` (Javadoc + comentários inline)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/utils/HashUtils.java` (`@since`, `@throws`)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/utils/StringFieldUtils.java` (Javadoc)
- `core/README.md` (novo)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/4-2-documentar-o-módulo-core.md` (este arquivo — Completion Notes, File List, tasks, status)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/sprint-status.yaml` (status da story)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/spec-4-2-documentar-o-módulo-core.md` (novo — spec do bmad-build para esta execução, rota `oneshot`)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/deferred-work.md` (nova entrada — README raiz desatualizado)
