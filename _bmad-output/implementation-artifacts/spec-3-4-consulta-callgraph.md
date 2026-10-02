---
title: 'Story 3.4: Consulta callgraph'
type: 'feature'
created: '2026-10-02'
status: 'done'
baseline_revision: '655bf6f5b7c90f92c51f52b50dc10aaf67f64c07'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '_bmad-output/implementation-artifacts/epic-3-context.md'
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** o agente confunde ausência de dado (callgraph indisponível) ou ausência de aresta com ausência de chamada.

**Approach:** subcomando `callgraph <projeto> <módulo>` (`ESCOPO=modulo`) sobre `callgraph.json` (+ `callgraph_edges.tsv`): fato não `disponivel` → resumo com `estado`, `motivo`, `comando_sugerido`, exit 0; disponível → resumo e filtros `--de`, `--para`, `--entrypoints`, `--lacunas`, `--sem-chamador`. Entrega o fixture de callgraph disponível em `fixtures.py`.

## Boundaries & Constraints

**Always:** `# aviso: ausencia de aresta nao prova ausencia de chamada` (≤ 100 B) em qualquer estado do fato; `aviso` do fato (proxies, reflexão, implementações em runtime) em `# limitacao:` quando existir; `--sem-chamador` sempre com `# limitacao:` "nao e lista de codigo morto: endpoints HTTP, @Scheduled e @EventListener nao tem chamador no bytecode"; `--de`/`--para` casam `Classe#metodo` ou prefixo (`startswith`); `--entrypoints` = arestas cuja classe de origem (nome simples antes de `#`/`$`) é a de algum `entrypoints[].path` (nome do arquivo sem `.java`); resumo (`arestas_total`, `arestas_ambiguas`, `entrypoints`, `lacunas`, `sem_chamador` = contagens) fora do teto; `--lacunas` lista `tipo, path, anotacao, motivo`; `--sem-chamador` lista `metodo, aviso`; `refinar` do truncamento: `--de <metodo> ou --para <metodo>`; só o `estado` não `disponivel` faz sair `comando_sugerido`; `AJUDA` ≤ 1500 B.

**Never:** saída vazia sem explicação; código ≠ 0 para fato indisponível; disparar geração; ler `callgraph_edges.tsv` sem filtro de aresta.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Indisponível | fato `indisponivel` (`java-callgraph.jar nao encontrado`) | cabeçalho + `# motivo:` + resumo com `comando_sugerido` + `# aviso:` | exit 0 |
| Resumo | disponível, sem flag | `arestas_total`, `arestas_ambiguas`, `entrypoints`, `lacunas`, `sem_chamador` | — |
| Por origem | `--de Classe#m` | linhas `de\tpara\tinvoke\tcerteza` | — |
| Entrypoints | `--entrypoints` | arestas de classes de entrypoint | — |
| Lacunas | `--lacunas` | `tipo\tpath\tanotacao\tmotivo` | — |
| Sem chamador | `--sem-chamador` | `metodo\taviso` + limitação de código morto | — |
| Fato ausente | módulo sem `callgraph` no índice | — | exit 3 |
| Tabela ausente | disponível, filtro de aresta, sem `.tsv` | — | exit 3 citando o arquivo |

</intent-contract>

## Code Map

- `ferramentas/scos-map/scos_map_query/fatos.py` -- novo `Mapa.callgraph(modulo)` = `self._fato(modulo, "callgraph")` (estado `indisponivel` já chega via `_abrir`/`_meta`, motivo vem do índice) e `Mapa.callgraph_arestas(modulo, dados)` → `_tabela(dados["arestas_arquivo"] relativo ao projeto, "callgraph_edges", meta.estado, meta.confianca)`. O ramo é por `dados.get("estado") == "disponivel"`, não pelo estado do envelope.
- Formato do gerador: `ferramentas/scos-map/scos-map.py` (~l. 2455–2540) — `callgraph.json`: `estado`, `motivo`, `comando_sugerido` (indisponível); disponível: `arestas_arquivo`, `arestas_total`, `arestas_ambiguas`, `aviso`, `lacunas_conhecidas[{tipo,path,anotacao|alvo,motivo}]`, `entrypoints[{path,anotacao,nota}]`, `metodos_sem_chamador[{metodo,aviso}]`; TSV `de, para, invoke, certeza` (`Classe#metodo`, `certeza` = `resolvida|ambigua`). Exemplo real indisponível: `SawCunhaOS-Flow/.scos-map/facts/organization/flow-organization-usecase/callgraph.json`.
- `ferramentas/scos-map/tests/fixtures.py::mapa_sintetico` -- novo fixture (exigido): `app` com `callgraph` disponível (`facts/app/callgraph.json` + `callgraph_edges.tsv` com colunas do gerador: ≥ 5 arestas, 1 ambígua, 1 classe de entrypoint, 1 lacuna `proxy_spring`, 2 `metodos_sem_chamador`) e `lib/core` com `callgraph` `indisponivel` (motivo "java-callgraph.jar nao encontrado", `comando_sugerido`). Se o `callgraph` do `app` já foi declarado no índice pela 3.1, só preencher os arquivos.
- `scos_map_query/comandos/deps.py` -- molde de flags; `render.py` -- `Resultado.avisos/limitacoes/refinar`.
- `tests/test_scos_map_query.py` (`TestCallgraph`), `tests/golden/callgraph.txt` (estado indisponível) e `callgraph_arestas.txt` (disponível com `--de`).

## Tasks & Acceptance

**Execution:**
- `scos_map_query/fatos.py` -- `callgraph()`, `callgraph_arestas()`
- `scos_map_query/comandos/callgraph.py` -- comando e 5 modos, AJUDA/EXEMPLO
- `tests/fixtures.py`, `tests/test_scos_map_query.py`, `tests/golden/` -- fixture disponível + matriz + goldens + `--help` + um teste que o `# aviso:` ≤ 100 B em ambos os estados
- (se o fixture for inviável: entregar só o caso `indisponivel` e registrar o motivo no `Auto Run Result`)

**Acceptance Criteria:**
- Given fato `indisponivel`, when `callgraph <p> <m>`, then envelope, `motivo` e `comando_sugerido`, exit 0, nunca vazio.
- Given fixture disponível, when sem filtro / `--de` / `--para` / `--entrypoints` / `--lacunas` / `--sem-chamador`, then conforme a matriz, com a limitação do fato e a de código morto.
- Given qualquer saída, then `# aviso:` "ausencia de aresta nao prova ausencia de chamada".

## Spec Change Log

## Review Triage Log

Ver o log conjunto em spec-3-1-consulta-arestas.md (2026-10-02).

## Verification

**Commands:**
- `cd ferramentas/scos-map && python3 -m unittest discover -s tests -t tests` -- expected: OK
- `python3 ferramentas/scos-map/scos-map-query.py callgraph SawCunhaOS-Flow flow-organization-usecase` -- expected: exit 0, `estado=indisponivel`, `comando_sugerido`

## Auto Run Result

Status: done
- Implementado: `callgraph` (indisponível + disponível com os 5 modos), fixture disponível, `--help`, avisos ≤ 100 B.
- Arquivos: `comandos/callgraph.py`, `fatos.py`, `fixtures.py`, testes, `golden/callgraph*.txt`.
- Revisão conjunta 3.1–3.4: 4 patches aplicados, 2 deferidos, demais rejeitados (ver log). Follow-up recomendado: false.
- Verificação: `python3 -m unittest discover -s tests -t tests` → 232 testes OK.
- Riscos: sem commit nos três repos (política); golden gerado da saída real guarda só regressão.
