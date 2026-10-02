---
name: scos-query
description: Consulta compacta do mapa .scos-map/ via CLI scos-map-query - layout, config, deps, versoes, conflitos, SNAPSHOTs, testes, bytecode e callgraph dos repos SCOS. Use para perguntas sobre organizacao do codigo antes de ler fatos brutos.
---

# scos-query (consulta)

Chame o CLI direto; `Read` do fato bruto so como ultimo recurso. Da raiz do workspace:
`python3 ferramentas/scos-map/scos-map-query.py <subcomando> ...` (`--help`, `<subcomando> --help`, `--help confianca`).

| Subcomando | Pergunta |
|---|---|
| `arestas` | quem usa a classe X (arestas de bytecode do modulo) |
| `arquivos` | que arquivos existem num modulo ou quais sao os mais mexidos |
| `tests` | que testes existem para o modulo ou para a classe X (heuristica) |
| `bytecode` | quais dependencias o bytecode usa sem declarar (risco x higiene) |
| `callgraph` | quem chama o metodo X (callgraph estatico do modulo) |
| `config` | quais arquivos de configuracao o modulo tem e onde moram |
| `conflitos` | quais bibliotecas tem versoes divergentes entre os repos |
| `deps` | o modulo usa a biblioteca X, em que versao e de onde vem |
| `docs` | que documentacao existe sobre um assunto no modulo |
| `gerenciadas` | que versao de dependencia a BOM fixa para o modulo |
| `layout` | onde mora o que no modulo: pacote base, areas e entry points |
| `reactor` | quais modulos o projeto tem e quem depende de quem |
| `snapshots` | os jars SNAPSHOT do ~/.m2 estao atrasados em relacao ao repo produtor |

`--all` remove o teto de saida (50 linhas/6.000 B): use so se o recorte nao basta.
`deps.tsv` nao traz as transitivas comuns (`_transitivas_comuns.tsv`). Lendo fato cru: `schema_versao` diferente de 2.1, reporte e pare.
Fatos grandes (ex.: `config.json` ~142KB) nunca com `Read`; TSV so com `grep`/`awk`, nunca inteiro.
Ausencia nao e prova: antes de concluir "nao usa X", "esta testada" ou "esta obsoleto", leia `# aviso:`/`# limitacao:` e o cabecalho da saida.
Pergunta aberta ("explique este repo"): ler `index.json`, `_reactor.json` e o `layout.json` dos maiores modulos.
