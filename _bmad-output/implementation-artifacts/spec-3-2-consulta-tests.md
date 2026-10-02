---
title: 'Story 3.2: Consulta tests'
type: 'feature'
created: '2026-10-02'
status: 'done'
baseline_revision: '655bf6f5b7c90f92c51f52b50dc10aaf67f64c07'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '_bmad-output/implementation-artifacts/epic-3-context.md'
warnings: []
deferred:
  - summary: >-
      Fato tests não está no índice: estado sempre `fresco`; módulo sem tests.json dá exit 3.
    evidence: |-
      Index real não lista tests em modulos[m].fatos. Decidir se o gerador deve indexar o fato (unverified se o exit 3 incomoda).
    location: >-
      ferramentas/scos-map/scos_map_query/fatos.py (Mapa.tests)
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** o agente tende a afirmar "X está testada" a partir do nome de um teste.

**Approach:** subcomando `tests <projeto> <módulo>` (`ESCOPO=modulo`): seção `resumo` (raízes, arquivos, tipos, frameworks, cobertura) a partir de `tests.json`; `--arquivos` e `--alvo` leem `tests.tsv`. Todo `alvo_heuristico` sai com `[heuristica]` e o `--help` ensina o limite da inferência.

## Boundaries & Constraints

**Always:** `# aviso: alvo e heuristica; existe teste chamado XTest, nao prova cobertura` (≤ 100 B); `cobertura` sempre com o `estado` do fato (`nao_analisado` ≠ "sem cobertura"); frameworks com `origem` (`declarada`/`inferida`); `--alvo X` (casamento por substring sem diferenciar caixa, via `filtros.contem`) implica listar arquivos; zero arquivos listados ou `arquivos == 0` → linha do resumo `resultado\tnenhum arquivo de teste identificado nas raizes analisadas: <raizes>` (nunca "nao existe teste"); coluna `marca` (última) = `[heuristica]` em toda linha de arquivo; `resumo` fora do teto; `AJUDA` ≤ 1500 B e explica "existe um teste chamado XTest, nunca X esta testada".

**Never:** afirmar cobertura; gerar fatos; ler `tests.tsv` sem `--arquivos`/`--alvo`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Resumo | `tests proj app` | seção `resumo` (campo/valor): raizes, arquivos, tipos, frameworks, cobertura | — |
| Arquivos | `--arquivos` | `path\ttipo\talvo_heuristico\tlinhas\tcommits_90d\tmarca` com `[heuristica]` | — |
| Alvo | `--alvo FooBean` | só linhas cujo alvo contém FooBean | — |
| Alvo sem teste | `--alvo Nada` | linha `resultado` "nenhum arquivo de teste identificado nas raizes analisadas: src/test/java, src/test" | — |
| Cobertura | `cobertura.estado=nao_analisado` | resumo traz `cobertura\tnao_analisado (motivo)` | — |
| Fato ausente | sem `facts/<m>/tests.json` | — | exit 3 |
| Tabela ausente | `--arquivos` sem `tests.tsv` | — | exit 3 citando o arquivo |

</intent-contract>

## Code Map

- `ferramentas/scos-map/scos_map_query/fatos.py` -- novo `Mapa.tests(modulo)`: o fato `tests` **não consta** em `indice.modulos[m].fatos` (só o `tests.tsv` em `tabelas`), então o caminho é por convenção: `self._abrir("tests", {"arquivo": "facts/%s/tests.json" % modulo, "estado": "fresco"})` (arquivo ausente → erro 3, pois `estado` não é de disponibilidade). Novo `Mapa.tests_arquivos(modulo, dados)` → `self._tabela("facts/%s/%s" % (modulo, dados.get("corpo") or "tests.tsv"), "tests", meta.estado, meta.confianca)`.
- `tests.json` real (`SawCunhaOS-Flow/.scos-map/facts/organization/flow-organization-usecase/tests.json`): `raizes[]`, `arquivos`, `classes`, `frameworks[{nome,origem,base}]`, `por_tipo{unit:92}`, `cobertura{estado,motivo}`, `completude{nivel:parcial,limitacoes[]}`, `corpo`, `corpo_colunas`. `tests.tsv`: `path, tipo, alvo_heuristico, linhas, last_modified, commits_90d`.
- `scos_map_query/comandos/deps.py` -- molde de duas seções; `scos_map_query/filtros.py` -- `contem`; `render.py` -- seção `tipo="resumo"` sai inteira, fora de `n/M`; `render._linha` nunca corta a coluna `marca`.
- `tests/fixtures.py::mapa_sintetico` -- ganha `facts/app/tests.json` + `tests.tsv` (≥ 3 linhas, uma sem alvo), com `completude.parcial` e `cobertura.nao_analisado`; `tests/test_scos_map_query.py` (`TestTests`), `tests/golden/tests.txt`, `tests/test_benchmark_sm1.py` (Q11).

## Tasks & Acceptance

**Execution:**
- `scos_map_query/fatos.py` -- `tests()`, `tests_arquivos()` -- leitura por convenção de caminho
- `scos_map_query/comandos/tests.py` -- comando, flags `--arquivos` (store_true), `--alvo`, AJUDA/EXEMPLO, aviso
- `tests/fixtures.py`, `tests/test_scos_map_query.py`, `tests/golden/tests.txt` -- fixture, matriz, golden, `--help`
- `tests/test_benchmark_sm1.py` -- Q11 no mapa real: `tests proj modulo --alvo <classe>` confere conteúdo contra `tests.tsv` lido direto; razão vs `grep` registrada, sem exigir ≤ 1.0 (grep menor tolerado)

**Acceptance Criteria:**
- Given `tests.json` e `.tsv`, when `tests <p> <m>`, then resumo com `cobertura` e o `estado`; `--arquivos` lista com `[heuristica]`.
- Given `--alvo` sem casamento, then a frase com as raízes, nunca "não existe teste".
- Given qualquer saída, then `# aviso:` ≤ 100 B presente.
- Given Q11 no mapa real, then conteúdo confere e a razão é registrada.

## Spec Change Log

## Review Triage Log

Ver o log conjunto em spec-3-1-consulta-arestas.md (2026-10-02).

## Verification

**Commands:**
- `cd ferramentas/scos-map && python3 -m unittest discover -s tests -t tests` -- expected: OK

## Auto Run Result

Status: done
- Implementado: `tests` (`--arquivos`, `--alvo`), `Mapa.tests/tests_arquivos`, Q11 (razão registrada, 5,27x).
- Desvio: módulo `comandos/arquivos_de_teste.py` (`NOME=tests`) porque guarda proíbe arquivos `test*`.
- Arquivos: `fatos.py`, `comandos/arquivos_de_teste.py`, testes, `golden/tests.txt`.
- Revisão conjunta 3.1–3.4: 4 patches aplicados, 2 deferidos, demais rejeitados (ver log). Follow-up recomendado: false.
- Verificação: `python3 -m unittest discover -s tests -t tests` → 232 testes OK.
- Riscos: sem commit nos três repos (política); golden gerado da saída real guarda só regressão.
