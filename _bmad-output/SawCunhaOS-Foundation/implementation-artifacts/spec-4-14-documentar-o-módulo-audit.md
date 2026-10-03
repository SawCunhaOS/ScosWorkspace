---
title: 'Documentar o módulo audit'
type: 'chore'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
baseline_revision: '228ab40282886e41da030e5ccbbd4d292c05a4f4'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/4-14-documentar-o-módulo-audit.md']
---

<intent-contract>

## Intent

**Problem:** O README do módulo `audit` só tinha o fluxo em ASCII (sem Mermaid) e a story assumia o gate de Javadoc já cumprido; o Checkstyle `analyze` acusava 31 avisos Javadoc (tipos/métodos sem doc em configuração, serviços, jobs e repositórios).

**Approach:** Diagrama Mermaid `flowchart` no README (ASCII mantida), Javadoc em português nas lacunas, e correção do que README/Javadoc afirmavam e o código não cumpre. Só documentação: nenhum comportamento ou assinatura é alterado.

## Boundaries & Constraints

**Always:** documentar o contrato real lido do código; preservar CRLF/LF de cada arquivo; registrar divergências story/código.
**Never:** alterar código, assinaturas, `pom.xml` ou testes.

</intent-contract>

## Code Map

- `audit/README.md` -- Mermaid, nota de dependência de `core`, nota de registro do listener, correção da fila (`ConcurrentLinkedQueue`)
- `audit/src/main/java/.../configuration/**`, `service/*`, `domain/repository/*` -- Javadoc de tipos/métodos públicos
- `specification/ScosAuditService.java`, `domain/entity/ActionType.java` -- aviso de que `ScosAuditReadAspect` não existe

## Tasks & Acceptance

**Execution:**
- `audit/README.md` -- Mermaid + notas -- feito
- Javadoc nas lacunas do `audit` -- feito (31 -> 0 avisos Javadoc no Checkstyle)

**Acceptance Criteria:**
- Given o módulo `audit`, when a documentação é completada, then o README tem o diagrama Mermaid do fluxo e toda API pública tem Javadoc.

## Review Triage Log

Revisão adversarial inline (subagentes não usados nesta execução), contra o código:
1. Story dizia gate de Javadoc "já cumprido": falso, havia 31 lacunas; preenchidas.
2. `ScosAuditReadAspect` (README/CHANGELOG/Javadoc) não existe; `@Auditable(READ)` em método não é processado. Documentado; `defer`.
3. `ScosHibernateAuditListener` não é registrado por nenhuma autoconfiguração (só no teste); README dizia "isso é suficiente". Corrigido; `defer`.
4. README dizia `LinkedBlockingQueue`; é `ConcurrentLinkedQueue` + contador (pode exceder levemente a capacidade). Corrigido.
5. `reprocessEntry` é chamado por `this` (sem proxy) e a DLQ não tem limite de tentativas; documentado; `defer`.
6. Retenção: tombstone hasheado com `now()` distinto do persistido e `eventOrder` null; `eventOrder` reinicia a cada JVM. Possível quebra de `verifyChain`; não verificado; `defer`.
7. CRLF/LF preservados por arquivo; nenhuma linha de código alterada.

## Auto Run Result

Status: done. Checkstyle `analyze` em `audit`: avisos Javadoc 31 -> 0. Testes: ver relatório. Sem commit (decisão do humano).
