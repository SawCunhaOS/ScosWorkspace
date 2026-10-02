---
title: 'Story 1.1: Consulta de layout ponta a ponta com envelope de confiança'
type: 'feature'
created: '2026-10-02'
status: 'done'
followup_review_recommended: false
baseline_commit: '9e13cf5e74a2520adf299e0ba6015ce37486f6d5'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-scos-map-query-2026-10-02/ARCHITECTURE-SPINE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** o agente abre `layout.json` inteiro (centenas de linhas de `derivado_de`) só para saber pacote base, áreas e entry points de um módulo, sem sinal de confiança ou frescor.

**Approach:** criar o esqueleto do CLI `scos-map-query` (`modelo`, `fatos`, `render`, `cli`) com o subcomando `layout` ponta a ponta, conforme AD-1…AD-7 e AD-9…AD-12 da spine, e registrar no fim a razão CLI/`grep` e CLI/`Read` da Q1 contra o mapa real.

## Boundaries & Constraints

**Always:** só stdlib, Python ≥ 3.10; entry fino `ferramentas/scos-map/scos-map-query.py` + pacote `scos_map_query/`; não importar `scos-map.py`; `comandos/layout.py` puro (sem E/S, `print`, `os.environ`, `sys.stdout`; imports só da lista branca); toda célula por `tsv_clean`; erros em stdout, nunca em stderr nem traceback; `SCHEMA_TESTADO = (2, 1)` em um único lugar; somente leitura do mapa.

**Never:** teto de saída, `--limit/--bytes/--all/--base`, log de custo e os outros 12 subcomandos (Stories 1.2+); `filtros.py` (sem uso ainda); gerar fatos ou chamar o gerador; `git` fora de `fatos.py` (só `rev-list --count`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Feliz | `layout <projeto> <módulo>` em subpasta do workspace | cabeçalho `# confianca=… estado=… gerado=…`, `## pacote_base`, `## areas`, `## entrypoints` (m de t), `# n de M linhas casam \| fontes: …/layout.json`; igual ao golden | N/A |
| Sem raiz | nenhum ancestral com `.scos-map/workspace.json` | — | código 3, `# erro: … \| acao: <scos-map-build>` |
| Alvo inválido | projeto/módulo inexistente | — | código 3, uma linha |
| Uso inválido | módulo ausente, módulo em escopo de projeto, basename ambíguo | — | código 2 (ambíguo lista opções) |
| Estado | HEAD ≠ `git.head` do mapa | `estado=obsoleto` (nunca `fresco`), `commits_desde_o_mapa=N` | HEAD ilegível → `desconhecido` |
| Envelope | `completude=parcial` / sem `confianca` | `# limitacao:` / `confianca=-` | N/A |
| Schema | 2.1 ou menor / 2.x maior / outra major | aceita / `# aviso: schema <v> mais novo que o testado (2.1)` / — | major: código 4 |
| Interno | exceção inesperada | — | código 1 `# erro: interno`; `SCOS_MAP_QUERY_DEBUG=1` mostra traceback |
| Ajuda | `layout --help` | `AJUDA` literal ≤ 1.500 B com `EXEMPLO` (3–5 linhas, também caso de teste) | argparse nunca escreve em stderr |

</frozen-after-approval>

## Code Map

- `ferramentas/scos-map/scos-map.py` -- gerador; só referência (`tsv_clean` l.171, `SCHEMA_VERSAO="2.1"`, `fact_state` l.2742). Não tocar nem importar.
- `ferramentas/scos-map/tests/fixtures.py`, `tests/test_scos_map.py` -- padrão da suíte (`unittest`, `BaseFixture`, `tempfile`, `git_init`); adicionar fixture de mapa sintético escrito à mão (`gerado_em` e `head` fixos) em vez de rodar o gerador.
- `<projeto>/.scos-map/index.json` -- `modulos{caminho→{fatos{layout{estado,arquivo,motivo?}}}}`, `git.head` (12 chars), `gerado_em`, `schema_versao`; `workspace.json` -- `projetos[{projeto,index}]`.
- `<projeto>/.scos-map/facts/<mód>/layout.json` -- `confianca`, `base`, `pacote_base`, `areas[{caminho,papel,arquivos}]`, `entrypoints[{path,tipo,rota?}]` (chave real é `entrypoints`; `completude`, `desvios` ausentes em layout).
- Mapa real para o smoke: `SawCunhaOS-Flow/.scos-map` (módulo `organization/flow-organization-usecase`, 303 arquivos).

## Tasks & Acceptance

**Execution:**
- [x] `scos_map_query/modelo.py` -- `Secao`, `Resultado`, `Meta`, `Opcoes`, `ErroConsulta(codigo, msg, acao)` -- contrato AD-2
- [x] `scos_map_query/fatos.py` -- `SCHEMA_TESTADO`, `abrir`, leitor de layout, `estado` (disponibilidade > estado do fato no índice > `.git/HEAD` vs `git.head`), `commits_desde` -- AD-3/AD-7/AD-12
- [x] `scos_map_query/render.py` -- `tsv_clean`, envelope, rodapé, `emitir` (stdout; log fica na 1.3) -- AD-4/AD-6
- [x] `scos_map_query/cli.py` + `scos-map-query.py` -- `ArgumentParser` com `error()`→`ErroConsulta(2)`, `resolver()`, registro por varredura de `comandos/`, `main`, códigos 0–4 -- AD-5
- [x] `scos_map_query/comandos/layout.py` -- `NOME/PERGUNTA/ESCOPO/FLAGS/AJUDA/EXEMPLO/consultar` -- AD-1
- [x] `tests/fixtures.py`, `tests/test_scos_map_query.py`, `tests/golden/layout*.txt` -- fixtures de mapa sintético, goldens, AST (imports/`open|print|input`/`sys.stdout`/`os.environ`), `SCHEMA_TESTADO`, `ast.parse(feature_version=(3,10))`, hash de 12 chars no `rev-list`
- [x] Esta spec (Implementation Notes) -- registrar razões da Q1 (bytes CLI vs `grep`/`Read`); se estourar a meta, enxugar envelope antes de 1.2

**Acceptance Criteria:**
- Given o fixture e as situações da matriz, when a suíte roda, then todos os casos passam e a saída bate com os goldens.
- Given o mapa real, when `layout organization/flow-organization-usecase` roda, then sai ≤ 300 ms e a Q1 é registrada.

## Implementation Notes

- Implementado direto (sem subagente). Arquivos: `scos-map-query.py`, `scos_map_query/{modelo,fatos,render,cli}.py`, `comandos/layout.py`, `tests/test_scos_map_query.py`, `tests/golden/layout.txt`, fixture `mapa_sintetico` em `tests/fixtures.py`. Suíte completa: 119 testes OK.
- **Q1 contra o mapa real (SM-1):** CLI 737 B vs `grep` 1.506 B = **0,49×** (meta ≤ 1,0×); vs `Read` de `layout.json` 54.798 B = **1,3%** (meta ≤ 10%); latência ≈ 30 ms (meta ≤ 300 ms). Suposição de SM-1 confirmada; envelope não precisa ser enxugado antes da 1.2.
- Envelope ainda sem `# fontes:` agrupado nem teto de 12 linhas (`ponytail:` em `render.py`; entra com o primeiro subcomando de vários fatos, Story 1.7). Escopo `workspace` fora do `cli._executar` até o Epic 2.
- Erro com fato já lido (ex.: erro interno) imprime envelope + `# erro:` + rodapé (AD-12), então não é "uma linha"; erros de resolução (antes de ler fato) são uma linha.

## Design Notes

Seções: `pacote_base` (1 linha), `areas` (`caminho papel arquivos`), `entrypoints` (`path tipo rota`); todas `dados`, declaradas mesmo vazias. `estado`: `fresco` do índice ainda é rebaixado a `obsoleto` se `HEAD` do repo do projeto ≠ `git.head` (prefixo de 12), e a `desconhecido` se ilegível ou sem `git.head`.

## Verification

**Commands:**
- `cd ferramentas/scos-map && python3 -m unittest discover -s tests -t tests` -- expected: OK, incluindo a suíte antiga
- `python3 ferramentas/scos-map/scos-map-query.py layout SawCunhaOS-Flow organization/flow-organization-usecase` -- expected: saída compacta com envelope, código 0

## Review Triage Log

### 2026-10-02 — Review pass (diff 1.1–1.4 completo)
- verdicts: ~35 findings (4 camadas) — high 0, medium 5, low 4, false 3, maybe-false 0 (resto agrupado/duplicado)
- findings:
  - `[medium]` `patch` BrokenPipe/stdout fechado em `emitir` gera traceback — `try/except BrokenPipeError` em `render.emitir`.
  - `[medium]` `patch` fato JSON que não é objeto vira `interno` (exit 1) — `_fato` agora exit 3 `formato inesperado` + `ACAO_GERAR`.
  - `[medium]` `patch` barra final/`./` em projeto/módulo dava inexistente — `resolver` normaliza.
  - `[medium]` `patch` `git.head` do índice inválido entrava no `rev-list` — `re.fullmatch` em `_commits_desde`.
  - `[medium]` `patch` gap de teste `packed-refs`, barra final, fato malformado, head inválido — 3 testes novos (147 OK).
  - `[low]` `defer` `estado=fresco` ignora working tree sujo — limitação do desenho AD-7 (só HEAD); documentar no Epic 4.
  - `[low]` `defer` testes de `motivo`/`indisponivel`, detached HEAD, `_refinar` combinado, `--help` posicional — cobertura secundária.
  - `[low]` `reject` log sem rotação, `allow_abbrev`, import por invocação, `rev-list` sempre — custo/uso negligível, correção adicionaria complexidade.
  - `[low]` `reject` `parse_intermixed_args` — não suporta subparsers; flags entre posicionais é uso incomum.
  - `[false]` `reject` escopo 1.2–1.4 "vazou" para 1.1 — o diff revisado inclui 1.2–1.4 por construção.
  - `[false]` `reject` Q1 só no markdown — SM-1 é medição manual por desenho (AC da 1.1).
  - `[false]` `reject` nenhuma skill/AGENTS aponta para a CLI — escopo da Story 4.x.

## Auto Run Result

Resumo: esqueleto `scos-map-query` + `layout` revisados; 5 patches (4 de código, 1 de testes). Sem commit por política do usuário (commit só por epic).
Verificação: `python3 -m unittest discover -s tests -t tests` → 147 testes OK.
Follow-up review: false. Riscos residuais: frescor ignora working tree.
