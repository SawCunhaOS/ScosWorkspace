# Epic 1 Context: Consulta compacta e confiável dos fatos de projeto

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

O agente consulta layout, configs, dependências, versões gerenciadas, docs, reactor e arquivos de um projeto via CLI Python (`scos-map-query`) sobre `.scos-map/`, recebendo poucas linhas com envelope de confiança, teto de saída e log de custo, em vez de abrir JSON/TSV inteiro. A primeira story entrega o esqueleto ponta a ponta com um subcomando (`layout`) e valida cedo a suposição de SM-1.

## Stories

- Story 1.1: Consulta de `layout` ponta a ponta com envelope de confiança
- Story 1.2: Teto de saída e flags comuns
- Story 1.3: Log de custo por chamada
- Story 1.4: Consulta de config e docs
- Story 1.5: Consulta de reactor e gerenciadas
- Story 1.6: Consulta de arquivos com a suíte awk congelada
- Story 1.7: Consulta de deps com união de transitivas
- Story 1.8: Guardas de qualidade e benchmark SM-1 (Q1–Q6)

## Requirements & Constraints

- Só stdlib, Python ≥ 3.10; vive em `ferramentas/scos-map/` (entry fino `scos-map-query.py` + pacote `scos_map_query/` com `modelo.py`, `fatos.py`, `render.py`, `cli.py`, `comandos/`); não importa `scos-map.py`; comando `python3 ferramentas/scos-map/scos-map-query.py <subcomando> ...`; ≤ 300 ms por chamada.
- Saída em texto plano: cabeçalho `# confianca=… estado=… gerado=…`, seções `## nome (m de t)` com colunas TSV, rodapé `# n de M linhas casam | fontes: …`, mesmo com zero linhas. Células passam por `tsv_clean`.
- Raiz = ancestral mais próximo com `.scos-map/workspace.json`. Códigos: 0 ok, 1 interno, 2 uso inválido, 3 ausente, 4 schema major incompatível. Erros em stdout: `# erro: <msg> | acao: <comando>`, sem traceback (`SCOS_MAP_QUERY_DEBUG=1` mostra).
- Teto padrão 50 linhas / 6.000 B de dados; linha truncada em 240 chars com `…`; `--limit/--bytes/--all` sobrescrevem.
- Golden por subcomando em `ferramentas/scos-map/tests/` com mapas sintéticos de `fixtures.py`; `--help` documenta formato + exemplo de 3–5 linhas.
- Somente leitura de `.scos-map/`; única escrita é o log; única chamada `git` = `rev-list --count`.

## Technical Decisions

- Contrato de `comandos/<x>.py`: `NOME`, `PERGUNTA`, `ESCOPO`, `FLAGS`, `AJUDA` (≤ 1.500 B), `EXEMPLO`, `consultar(args, mapa) -> Resultado`; função pura, sem E/S/`print`/ambiente; lista branca de imports; registro = módulos não `_*.py`.
- Tipos em `modelo.py` (`Secao`, `Resultado`, `Meta`, `Opcoes`, `ErroConsulta`); só `fatos.py` conhece o formato dos fatos e calcula `estado`; render monta envelope (pior caso entre fatos), rodapé e truncamento; só `cli.py`/`render.py` leem `os.environ`; saída via `render.emitir`.
- `resolver(projeto, modulo)` é a única função que conhece a árvore do mapa; `ArgumentParser` subclassado com `error()` → `ErroConsulta(2)`.
- `SCHEMA_TESTADO = (2, 1)` constante única; major diferente → 4, minor maior → `# aviso:`.
- Fato `ausente` → erro 3; `indisponivel`/`nao_aplicavel` → resultado normal.

## Cross-Story Dependencies

- 1.1 cria a infra (modelo/fatos/render/cli) reusada por todas as demais; 1.8 fecha Q1–Q6 como teste executável; Epics 2–4 reusam a infra.
