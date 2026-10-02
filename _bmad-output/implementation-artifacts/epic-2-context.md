# Epic 2 Context: Consultas cruzadas do workspace

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

O agente vê num único comando os conflitos de versão entre os três repositórios (`conflitos`) e se cada `-SNAPSHOT` local está atrás do repositório produtor (`snapshots`), sem carregar `workspace.json` inteiro. São os dois subcomandos de escopo workspace do CLI `scos-map-query`, que reusam a infra entregue no Epic 1.

## Stories

- Story 2.1: Consulta `conflitos`
- Story 2.2: Consulta `snapshots`

## Requirements & Constraints

- `conflitos` e `snapshots` têm `ESCOPO=workspace`: não recebem projeto (passar um → código 2) e leem só `workspace.json` (e `.git/HEAD` no caso de `snapshots`).
- `conflitos`: uma linha por biblioteca divergente (`ga`, versões e repositórios), equivalente em conteúdo a `conflitos_de_versao_cruzados`. Zero conflitos → cabeçalho + limitação + `# 0 de 0 linhas casam | fontes: workspace.json`, nunca saída vazia. `--help` explica obsoleto, árvore suja, scope `test` e sufixo `(gerenciada)`.
- `snapshots`: uma linha por repositório produtor (`produtor`, N jars, estados, max_atraso, ação recomendada), agrupada; `--detalhe` uma linha por coordenada (`ga`, versão, `estado`, `acao`, `atraso_dias`). Não acessa `~/.m2` nem varre arquivos; opcionalmente conta commits.
- Estado do snapshot: `repo_local.head` diferente do HEAD atual → `obsoleto`; igual com mapa gerado sujo → `desconhecido`; HEAD ilegível → `desconhecido`; fixture com head divergente nunca sai `fresco`.
- `# limitacao:` obrigatória em `snapshots`: mtime do jar não prova conteúdo, commit só de documentação também marca atraso, alterações não commitadas/stash não contam. `--help` explica `jar_atual` ≠ "contém o último commit".
- Fato `resolvida`+`parcial` (árvore suja): cabeçalho `confianca=resolvida estado=<…> completude=parcial`, `# limitacao:` e cláusula "mapa gerado com alterações não commitadas", com pior caso entre os três `head`.
- Golden e `--help` (formato + exemplo real de 3–5 linhas) por subcomando em `ferramentas/scos-map/tests/`; benchmark Q7 (`conflitos`) e Q8 (`snapshots`) conferidos por conteúdo e contagem independente, CLI/`Read` ≤ 10%.

## Technical Decisions

- Cada comando é um módulo em `scos_map_query/comandos/` com `NOME`, `PERGUNTA`, `ESCOPO`, `FLAGS`, `AJUDA` (≤ 1.500 B), `EXEMPLO`, `consultar(args, mapa) -> Resultado`; função pura (sem E/S, `print`, ambiente; imports só da lista branca), registrando cada fato lido em `mapa.lidos`. O registro cresce sozinho a partir dos módulos.
- O comando filtra/agrupa e preenche `total`, `marca`, `refinar`; o render calcula envelope, teto (50 linhas / 6.000 B), `n/M` e rodapé. Só `fatos.py` conhece o formato dos fatos e calcula `estado` (precedência: disponibilidade > `frescor` do fato > frescor barato via `.git/HEAD`; vários `head` → pior caso).
- Única chamada `git` permitida: `rev-list --count <head>..HEAD` (somente leitura, em `fatos.py`; testar com hash abreviado de 12 caracteres). Células passam por `tsv_clean`.
- Fixtures novos em `fixtures.py`: `resolvida`+`parcial` com árvore suja, fato `obsoleto` e HEAD ilegível (criados no Epic 1/Story 1.8, reutilizados na 2.1), e estado misto (`jar_atual`, `jar_desatualizado`, `jar_ausente`) para a 2.2.

## Cross-Story Dependencies

- Depende da infra do Epic 1 (`modelo`, `fatos`, `render`, `cli`, envelope, teto, log) e dos fixtures de estado/SM-C1 criados lá.
- A 2.1 e a 2.2 são independentes entre si; ambas alimentam a tabela de roteamento do Epic 4 via `PERGUNTA`.
