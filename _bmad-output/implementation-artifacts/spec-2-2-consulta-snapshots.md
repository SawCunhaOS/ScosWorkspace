---
title: 'Story 2.2: Consulta snapshots'
type: 'feature'
created: '2026-10-02'
status: 'done'
baseline_revision: 'd3d607982bd6a590e436dc1446b0fd2d78eb79c1'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** o agente não sabe se os `-SNAPSHOT` do `~/.m2` estão atrás do repo produtor sem ler `workspace.json` inteiro.

**Approach:** subcomando `snapshots` (`ESCOPO=workspace`) sobre `snapshots_locais`, agrupado por produtor, `--detalhe` por coordenada; estado pelo `repo_local.head` vs `.git/HEAD`, reusando `fatos.Workspace` da 2.1.

## Boundaries & Constraints

**Always:** só lê o fato e `.git/HEAD` (+ `rev-list --count` opcional); estado: head diferente → `obsoleto`; igual com mapa sujo → `desconhecido`; HEAD ilegível → `desconhecido`; head divergente nunca `fresco`; `# limitacao:` com mtime≠conteúdo, commit só de docs marca atraso, não commitado/stash não contam; estados mistos aparecem agrupados.

**Never:** acessar `~/.m2` ou varrer arquivos; projeto/módulo (exit 2).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Agrupado | `snapshots` | `produtor \t N jar(s) \t estados \t max_atraso \t acao` | — |
| Detalhe | `snapshots --detalhe` | `ga \t versao \t estado \t acao \t atraso_dias` | — |
| Head divergente | `repo_local.head` ≠ HEAD atual | cabeçalho `estado=obsoleto` | — |
| Misto | atual+desatualizado+ausente | os 3 estados na coluna `estados` | — |
| Fato ausente | sem a chave | — | exit 3 |

</intent-contract>

## Code Map

- `ferramentas/scos-map/scos_map_query/fatos.py` -- `Workspace.snapshots()` (da 2.1).
- `ferramentas/scos-map/scos_map_query/comandos/conflitos.py` -- molde workspace.
- `ferramentas/scos-map/tests/fixtures.py` -- fixture de estado misto; `test_benchmark_sm1.py` -- Q8.

## Tasks & Acceptance

**Execution:**
- `scos_map_query/fatos.py` -- `Workspace.snapshots()` -- leitura do fato
- `scos_map_query/comandos/snapshots.py` -- comando, `--detalhe`, AJUDA (`jar_atual` ≠ "contém o último commit")
- `tests/` -- fixture misto, golden, estados de head, Q8 com CLI/Read ≤ 10%

**Acceptance Criteria:**
- Given `snapshots_locais`, when `snapshots`, then uma linha por produtor; `--detalhe` uma por coordenada.
- Given head gravado, when estado calculado, then regras de obsoleto/desconhecido acima.
- Given a saída, then `# limitacao:` FR-4 presente.
- Given estado misto, then agrupado sem esconder a mistura; Q8 passa.

## Verification

**Commands:**
- `cd ferramentas/scos-map && python3 -m unittest discover -s tests -t tests` -- expected: OK

## Review Triage Log

### 2026-10-02 — Review pass única (2.1 e 2.2, 4 camadas sobre o diff conjunto)
- patch: bloco `Meta` duplicado extraído para `Workspace._registrar`; `derivado` vazio dava `estado=fresco` → agora `desconhecido`; `estado` nulo no agrupamento de snapshots; testes de pior caso multi-repo, cláusula de árvore suja e zero itens.
- defer: heads distintos no mesmo produtor (vale o do último item; o gerador grava um head por repo — `ponytail:` no código).
- reject: guardas para schema malformado (`produzido_por` nulo, `versoes` não-lista, `atraso_dias` não numérico) — arquivo gerado pelo próprio gerador; `acao` divergente por produtor; `_repos` mostrar `A,A (gerenciada)` (informação correta); docs/SKILL/AGENTS (Epic 4); fixtures inline em vez de `fixtures.py`.
- false: `--limit/--bytes` ignorados (mesmo `render.montar`, verificado); log sem projeto; Q7/Q8 vácuos; `""` posicional.

## Auto Run Result

Status: done
- Implementado: `snapshots` (+ `--detalhe`). Infra de escopo `workspace` (`cli.py`: `projeto` opcional, exit 2 com projeto; `fatos.Workspace`).
- Arquivos: `scos_map_query/{cli,fatos}.py`, `comandos/snapshots.py`, `tests/test_scos_map_query.py`, `tests/test_benchmark_sm1.py`, `tests/golden/snapshots.txt`.
- Revisão: 4 patches aplicados, 1 deferido (head por produtor), demais rejeitados (ver log). Follow-up recomendado: false.
- Verificação: `python3 -m unittest discover -s tests -t tests` → 190 testes OK; smoke no mapa real (`conflitos` 2 itens, `snapshots` 1 produtor, `estado=obsoleto` pois os repos andaram desde o mapa).
- Riscos: golden de snapshots gerado da saída real (só guarda regressão); linhas `# limitacao:` do fato e do comando se sobrepõem em redação. Sem commit (política do workspace: commit só com autorização/por epic).
