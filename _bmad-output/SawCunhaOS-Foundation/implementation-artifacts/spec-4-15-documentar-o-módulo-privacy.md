---
title: 'Documentar o módulo privacy'
type: 'chore'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
baseline_revision: '228ab40282886e41da030e5ccbbd4d292c05a4f4'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/4-15-documentar-o-módulo-privacy.md']
---

<intent-contract>

## Intent

**Problem:** A story assumia que `privacy` não tinha o perfil `analyze` e que o README carregava "seu próprio Gson"; o README não tinha diagrama e o Checkstyle acusava 24 avisos `SummaryJavadoc` (Javadoc sem resumo).

**Approach:** Diagrama Mermaid `flowchart` no README, correção das afirmações de dependência, e resumos Javadoc em português nas lacunas. Só documentação: nenhum comportamento, assinatura ou `pom.xml` é alterado.

## Boundaries & Constraints

**Always:** documentar o contrato real lido do código; preservar o conteúdo textual do README; registrar divergências story/código.
**Never:** alterar código, assinaturas, `pom.xml` ou testes; ativar `failOnViolation` (Story 4.16).

</intent-contract>

## Code Map

- `privacy/README.md` -- seção "Why a dedicated module": Gson -> Jackson, dependentes reais; novo flowchart Mermaid
- `privacy/src/main/java/.../{DataMaskingService,config/PrivacyConfig,core/MaskingEngine,crypto/*,logback/ScosMaskingConverterSupport,specification/DataMaskingValues,spring/*}` -- resumo Javadoc nos blocos só com `@return`/`@param`
- `pom.xml` (raiz, linha ~356) -- o perfil `analyze` (Jacoco 0.80, Checkstyle) já é herdado por todos os módulos

## Tasks & Acceptance

**Execution:**
- `privacy/README.md` -- Mermaid + correções -- feito
- Javadoc `privacy` -- 24 `SummaryJavadoc` (e os 11 `SingleLineJavadoc`/11 `RequireEmptyLine...` correlatos) -> 0 -- feito
- `privacy/pom.xml` -- sem alteração: ver divergências

**Acceptance Criteria:**
- Given o módulo `privacy`, when `mvn -Panalyze verify` roda, then o Checkstyle cobre `privacy` e o README tem o diagrama do fluxo de uso.

## Review Triage Log

Revisão adversarial inline (subagentes não usados nesta execução), contra o código:
1. Divergência da story: `privacy/pom.xml` "sem profile analyze" é falso; o perfil está no `pom.xml` raiz e é herdado por todos os módulos (audit/jdempotent/etc. também não o declaram localmente). Nada a copiar; `-Panalyze verify` em `privacy` roda (Jacoco check passa, BUILD SUCCESS).
2. README dizia "carries its own Gson": falso desde a Story 1.3 (usa `jackson-databind`, só `JsonNode`). Corrigido.
3. README dizia "`utils` e `audit` dependem de `privacy`" e que os filtros de log ficam em `utils`: falso. Dependentes diretos: `web`, `audit`, `jdempotent`, `archtest`; os filtros (`LoggingInitialFilter`/`LoggingFinalFilter`) estão em `web`. Corrigido.
4. Diagrama conferido contra o código: headers só no `LoggingInitialFilter`; body em Initial e Final; cifra em `ScosAuditServiceBean`.
5. Os ~1850 avisos restantes do Checkstyle (Indentation Google 2 espaços, LineLength 100, import order) são de estilo, pré-existentes e fora do escopo; `failOnViolation` fica para a 4.16 (`defer`, já coberto).

## Auto Run Result

Status: done. `mvn -o -pl privacy test`: 50 testes, 0 falhas. `mvn -Panalyze verify -pl privacy`: BUILD SUCCESS. Checkstyle: avisos Javadoc 0 (SummaryJavadoc 24 -> 0). Sem commit (decisão do humano).
