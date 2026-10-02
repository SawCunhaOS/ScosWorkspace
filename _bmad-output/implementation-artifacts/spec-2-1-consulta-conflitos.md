---
title: 'Story 2.1: Consulta conflitos'
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

**Problem:** o agente só vê conflitos de versão entre os três repos lendo `workspace.json` (18,5 KB) inteiro; o CLI não tem escopo `workspace`.

**Approach:** subcomando `conflitos` (`ESCOPO=workspace`, sem projeto) lendo só `conflitos_de_versao_cruzados`; infra de escopo workspace no `cli.py`/`fatos.py` (classe `Workspace`) reutilizada pela 2.2.

## Boundaries & Constraints

**Always:** `consultar` pura; fato lido via `fatos.py`; estado = pior caso dos `head` de `derivado_de` (obsoleto < desconhecido < fresco; igual com repo sujo em `projetos[].git.dirty` → desconhecido; HEAD ilegível → desconhecido); células por `tsv_clean`; zero conflitos nunca dá saída vazia.

**Never:** aceitar projeto/módulo (exit 2); acessar `~/.m2`; alterar o gerador; inventar fato ausente (exit 3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Conflitos | `conflitos` | uma linha por `ga`: `ga \t versão:repos \| …` (sufixo `(gerenciada)` preservado) | — |
| Árvore suja | fixture resolvida+parcial | `confianca=resolvida estado=<pior> completude=parcial`, `# limitacao:` do fato + "mapa gerado com alteracoes nao commitadas" | — |
| Zero | `itens: []` | cabeçalho + limitação + `# 0 de 0 linhas casam \| fontes: workspace.json` | — |
| Projeto passado | `conflitos proj` | — | exit 2 |
| Fato ausente | sem a chave | — | exit 3 |

</intent-contract>

## Code Map

- `ferramentas/scos-map/scos_map_query/cli.py` -- `projeto` vira opcional; escopo `workspace` monta `fatos.Workspace` (substitui o `ponytail` de _executar).
- `ferramentas/scos-map/scos_map_query/fatos.py` -- nova classe `Workspace` (`conflitos()`, estado por `.git/HEAD`, reaproveita `_head_atual`/`_commits_desde`).
- `ferramentas/scos-map/scos_map_query/comandos/reactor.py` -- molde de comando.
- `ferramentas/scos-map/tests/fixtures.py` / `test_scos_map_query.py` / `test_benchmark_sm1.py` / `golden/` -- fixture de workspace, testes, Q7.

## Tasks & Acceptance

**Execution:**
- `scos_map_query/fatos.py` -- classe `Workspace` + `conflitos()` -- leitura única do fato
- `scos_map_query/cli.py` -- projeto opcional, escopo workspace, exit 2 com projeto -- AD-10
- `scos_map_query/comandos/conflitos.py` -- comando com AJUDA (obsoleto, árvore suja, scope test, `(gerenciada)`) -- FR-3
- `tests/fixtures.py`, `tests/test_scos_map_query.py`, `tests/golden/conflitos.txt`, `tests/test_benchmark_sm1.py` -- fixture, golden, casos da matriz, Q7 com CLI/Read ≤ 10%

**Acceptance Criteria:**
- Given fixture com `conflitos_de_versao_cruzados`, when `conflitos`, then uma linha por biblioteca equivalente ao fato; com projeto → exit 2.
- Given resolvida+parcial suja, when cabeçalho, then envelope e cláusula de árvore suja com pior caso entre os heads.
- Given zero conflitos, when roda, then nunca saída vazia.
- Given Q7 no mapa real, then conteúdo e contagem conferem e CLI/Read ≤ 10%.

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
- Implementado: `conflitos`. Infra de escopo `workspace` (`cli.py`: `projeto` opcional, exit 2 com projeto; `fatos.Workspace`).
- Arquivos: `scos_map_query/{cli,fatos}.py`, `comandos/conflitos.py`, `tests/test_scos_map_query.py`, `tests/test_benchmark_sm1.py`, `tests/golden/conflitos.txt`.
- Revisão: 4 patches aplicados, 1 deferido (head por produtor), demais rejeitados (ver log). Follow-up recomendado: false.
- Verificação: `python3 -m unittest discover -s tests -t tests` → 190 testes OK; smoke no mapa real (`conflitos` 2 itens, `snapshots` 1 produtor, `estado=obsoleto` pois os repos andaram desde o mapa).
- Riscos: golden de snapshots gerado da saída real (só guarda regressão); linhas `# limitacao:` do fato e do comando se sobrepõem em redação. Sem commit (política do workspace: commit só com autorização/por epic).
