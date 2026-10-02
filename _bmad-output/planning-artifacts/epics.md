---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Workspace-2026-09-14/prd.md
  - _bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Workspace-2026-09-14/addendum.md
  - _bmad-output/planning-artifacts/architecture/architecture-scos-map-query-2026-10-02/ARCHITECTURE-SPINE.md
---

# SawCunhaOS-Workspace (scos-map-query) - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for SawCunhaOS-Workspace (iniciativa `scos-map-query`: CLI Python de consulta compacta sobre `.scos-map/`), decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

Nota de rastreabilidade: os IDs de requisito seguem os IDs estáveis do PRD (`FR-1`…`FR-14`, `NFR-1`, `NFR-2`) e das decisões da spine (`AD-1`…`AD-12`), em vez de renumerar.

## Requirements Inventory

### Functional Requirements

- **FR-1**: Consulta por fato via subcomando dedicado. Projeto (posicional obrigatório) e módulo (posicional, só nos fatos por módulo) → texto plano, uma unidade por linha, nunca o fato bruto; conteúdo padrão = tabela §4.0 (13 subcomandos). Raiz = ancestral com `.scos-map/workspace.json` (sem ele: código 3, sem modo isolado). Códigos de saída: 0 ok, 1 interno, 2 uso inválido, 3 fato/projeto/módulo ausente, 4 `schema_versao` major incompatível; erros em stdout como `# erro: <msg> | acao: <comando>`. `conflitos` e `snapshots` não recebem projeto. Formato em seções `## <nome> (<mostradas> de <total>)` + colunas TSV, células via `tsv_clean`. `schema_versao` 2.x aceito (minor mais novo → `# aviso:`). Cada subcomando documenta no `--help` formato + exemplo real de 3–5 linhas (também caso de teste). O CLI nunca gera fatos, nunca compila, nunca escreve em `.scos-map/`.
- **FR-2**: Filtros e flags (conjunto fechado). Suíte de compatibilidade congelada dos 3 `awk` documentados (`arquivos --em-modulo/--kind`, `arquivos --commits-90d-min`, `deps --todos-modulos --ga`). Tabela única: `--limit/--bytes/--all`, `--base`, `--em-modulo/--kind/--commits-90d-min`, `--ga`, `--todos-modulos`, `--prefixo`, `--texto`, `--de/--para`, `--pacote`, `--arquivos/--alvo`, `--balde`, `--entrypoints/--lacunas/--sem-chamador`, `--detalhe`. Filtro inválido → erro de uma linha; filtro sem resultado segue FR-5; rodapé de truncamento sugere flag aplicável; os 12 casos do benchmark usam só flags da tabela. Cada linha da tabela é um caso golden.
- **FR-3**: Conflitos de versão cruzados. `conflitos`: uma linha por biblioteca divergente (nome, versões e repositórios), equivalente a `conflitos_de_versao_cruzados` de `workspace.json`; sem conflito não aparece; zero conflitos → cabeçalho FR-5 + rodapé `# 0 de 0 linhas casam | fontes: workspace.json`, nunca saída vazia.
- **FR-4**: Frescor de SNAPSHOT local. `snapshots`: uma linha por repositório produtor (`produtor \t N jar(s) \t estados \t max_atraso \t ação`); `--detalhe` uma linha por coordenada. `estado` do fato via `repo_local.head` vs HEAD atual (frescor barato); lê só o fato e `.git/HEAD` (+ contagem opcional de commits), sem acessar `~/.m2`. Limitação (mtime do jar não prova conteúdo; commit só de docs marca atraso; alterações não commitadas ignoradas) vai na saída em `# limitacao:`. Fixture com `head` divergente nunca sai `fresco`.
- **FR-5**: Envelope de confiança em toda saída. Cabeçalho `# confianca=<v> estado=<v> [completude=<n>] gerado=<ts>` (+ `commits_desde_o_mapa=N` quando há `git`; `--base` acrescenta `base`); `confianca=-` quando o fato não tem; precedência de `estado` (disponibilidade > `frescor` do fato > frescor barato por `.git/HEAD`; vários `head` → pior caso; `disponivel` sem comparável → `desconhecido`); não reutiliza `fact_state` nem importa `scos-map.py`; vários fatos → pior caso + linha `# fontes:`; marca por linha só quando difere do cabeçalho (`desvios[]`, `heuristica`); `# limitacao:` quando `completude=parcial` (truncada por cláusula); `# aviso:` ≤ 100 bytes por subcomando (`docs`, `arquivos`, `tests`, `bytecode`, `callgraph`); última linha `# <n> de <M> linhas casam | fontes: <arquivos>` mesmo com zero linhas.
- **FR-6**: Contrato de saída estável. Formato documentado no `--help` com exemplo real; teste golden por subcomando em `ferramentas/scos-map/tests/` (alterar formato exige atualizar golden + `--help` no mesmo commit); benchmark canônico como teste executável com asserção de conteúdo (SM-1); goldens usam os mapas sintéticos de `fixtures.py`; teste por AST proíbe `open`/`print`/`sys.stdout`/`os.environ` em `comandos/`; `SCHEMA_TESTADO` (2.1) constante única com teste.
- **FR-7**: Roteamento aponta para o CLI primeiro. Única tabela de 13 linhas (uma por subcomando; `arestas` separada de `bytecode`) só na skill `scos-query`; `AGENTS.md` perde a tabela e ganha uma linha apontando para a skill; fonte única = constante `PERGUNTA` de cada módulo de `comandos/` (alimenta também o `--help` geral); teste: tabela da skill = `NOME`/`PERGUNTA` do registro; exceção só se listada com motivo; fallback TSV = `grep`/`awk` com colunas do `--help`, nunca `Read` do TSV inteiro; aviso do tamanho dos fatos grandes (ex.: `config.json` ≈142KB).
- **FR-8**: Log de custo por chamada. `.scos-map-query.log` na raiz do workspace (fora de `.scos-map/`, no `.gitignore`; `SCOS_MAP_QUERY_LOG` sobrescreve); registro append-only com uma única escrita: ts, subcomando, projeto/módulo, bytes e linhas de saída, código de saída, `schema_versao`; sem rotação; falha de escrita nunca impede a resposta; sem `workspace.json` → código 3 e sem log. Tokens reais estão fora do escopo.
- **FR-9**: Teto de saída. Padrão 50 linhas e 6.000 bytes de dados (cabeçalho, limitação, títulos e rodapé não contam); linha individual truncada em 240 caracteres com `…`; linhas na ordem do fato; rodapé informa `N de M` e sugere flag de FR-2; `--limit/--bytes/--all` sobrescrevem; nenhuma invocação sem `--all` excede os tetos (inclusive `arquivos` sem filtro e `arestas` quente, 107 linhas na Q10).
- **FR-10**: Consulta de arestas de bytecode (Tier 2 e 3). `arestas <projeto> <módulo>` com `--de/--para/--pacote`, respeitando FR-5 e FR-9; sem `bytecode_edges.tsv` → erro de FR-1 indicando build `--tier 2/3` (nunca dispara geração); arquivo vazio → rodapé com `motivo_vazio` e `diagnostico`.
- **FR-11**: Skills finas de consulta. Skill nova `scos-query` e `scos-map` reduzida a ponteiro: cada uma com descrição ≤ 300 caracteres e corpo (sem frontmatter) ≤ 30 linhas e 2.000 caracteres; `--help` de subcomando ≤ 1.500 bytes e `--help confianca` ≤ 2.500; `scos-query` contém só regra de chamada direta, comando literal, tabela de roteamento e aviso de `--all`; inventário do `SKILL.md` no addendum cobre todas as seções (nenhum conteúdo se perde) e cada regra de "Regras que evitam conclusão errada" tem destino testado; regras de alto risco ("não usa X", "está testada", "está obsoleto") não podem ficar só no `--help`; `scos-map-build` só muda a referência na descrição.
- **FR-12**: Consulta de testes. `tests`: resumo de `tests.json` (raízes, arquivos, tipos, frameworks com `origem`, `cobertura`); `--arquivos` lê `tests.tsv`; `alvo_heuristico` sempre com `[heuristica]`; zero arquivos para `--alvo` → "nenhum arquivo de teste identificado nas raízes analisadas: <raízes>"; `cobertura` sempre com o `estado` do fato.
- **FR-13**: Consulta de dependências no bytecode. `bytecode`: resumo por balde (`deps_usadas_ausentes_do_pom`, `deps_usadas_via_transitiva`, `deps_declaradas_sem_uso`, `deps_ignoradas_na_analise`), `frescor`, `transitivas_resolvidas`; `--balde` lista itens; só `deps_usadas_ausentes_do_pom` é risco imediato; `[provavel_falso_positivo]`; `transitivas_resolvidas` falso → `# limitacao:`; baldes condicionais (ausente ≠ 0 quando não calculado); `estado` considera `frescor` próprio (`compilado_em`).
- **FR-14**: Consulta de callgraph (Tier 3). `callgraph`: fato `indisponivel` → cabeçalho + `motivo` + `comando_sugerido` (nunca vazio); disponível → resumo, `--de/--para/--entrypoints` sobre `callgraph_edges.tsv`, `--lacunas`; advertência do fato sempre em `# limitacao:`; `--sem-chamador` com marca de que não é lista de código morto; caso disponível testado com fixture de `fixtures.py` (se inviável, MVP entrega só `indisponivel`).

### NonFunctional Requirements

- **NFR-1**: Dependências, comando e localização. Só stdlib, Python ≥ 3.10 (sem recursos mais novos); vive em `ferramentas/scos-map/` (entry fino `scos-map-query.py` + pacote `scos_map_query/` com `modelo.py`, `fatos.py`, `render.py`, `cli.py`, `comandos/`); comando literal `python3 ferramentas/scos-map/scos-map-query.py <subcomando> ...` (uma regra de allowlist cobre tudo); não importa `scos-map.py`.
- **NFR-2**: Latência. ≤ 300 ms por invocação em máquina local (protótipo ≈ 10 ms).
- **SM-1** (métrica de sucesso, gate de qualidade): benchmark canônico de 12 perguntas contra o CLI real. JSON: mediana CLI/`grep` ≤ 1,0× e nenhuma > 1,6×; TSV: CLI ≤ máx(`grep` + 64 B, 1,1 × `grep`); contra o `Read`: ≤ 10% (informativo). Respostas conferidas por contagem independente e conteúdo esperado. Suposição aberta: CLI real fica na margem do proxy.
- **SM-2** (secundária, pós-adoção): toda linha da tabela da skill tem subcomando (estático); ≥ 90% de 20 perguntas em 5 sessões sem `Read` de fato bruto (verificação por revisor, não pelo implementador).
- **SM-C1** (counter-metric): zero saídas sem envelope correspondente ao fato, verificado por fixtures de fato `obsoleto`, `resolvida`+`parcial` (árvore suja) e HEAD ilegível (`desconhecido`).
- **SM-C2** (counter-metric): sessão de 5 perguntas (Q1, Q5, Q6, Q7, Q9) com skill + `--help` + saídas ≤ 10% do total via `Read` (incluindo 10,6KB do `SKILL.md` antigo).

### Additional Requirements

Starter template: **nenhum** (extensão do repositório existente; sem greenfield).

Da arquitetura (spine, `AD-1`…`AD-12`) e do addendum:

- **AD-1** Contrato do subcomando: cada `comandos/<x>.py` expõe `NOME`, `PERGUNTA`, `ESCOPO` (`workspace`/`projeto`/`modulo`), `FLAGS`, `AJUDA` (≤ 1.500 B), `EXEMPLO` (3–5 linhas TSV, caso de aceitação) e `consultar(args, mapa) -> Resultado`; função pura sobre `mapa` (registra cada fato em `mapa.lidos`); nunca faz E/S, `print`, lê ambiente nem aplica `--limit/--bytes/--all/--base`. Escopos: workspace = `conflitos`, `snapshots`; projeto = `reactor`, `arquivos`; módulo = `layout`, `config`, `deps`, `gerenciadas`, `docs`, `arestas`, `tests`, `bytecode`, `callgraph`. Teste: lista branca de imports em `comandos/` (`modelo`, `filtros`, `re`, `typing`, `dataclasses`, `collections`), proibição de `open/print/input`; `comandos/_*.py` fora do registro; nenhum arquivo do pacote casa `test*.py`.
- **AD-2** Tipos em `modelo.py`: `Secao(nome, colunas, linhas, total, tipo, fonte)`, `Resultado(secoes, avisos, limitacoes, refinar)`, `Meta(...)`, `Opcoes`, `ErroConsulta`; marca = coluna `marca` (última), só quando a `confianca` da linha difere da do fato fonte (`[heuristica]` de `tests` sempre); seção `resumo` sai inteira (≤ 20 linhas), fora do teto e de `n/M`; seções declaradas mesmo vazias.
- **AD-3** Só `fatos.py` conhece o formato dos fatos: acesso por nome (TSV pelo cabeçalho), chave ausente = `None`; calcula `estado` final (precedência de FR-5) e `commits_desde`; `deps` une `deps.tsv` do módulo + `facts/_transitivas_comuns.tsv` (lido uma vez, seção `transitivas`).
- **AD-4** Envelope no render: pior caso entre fatos (ordens fixas de `confianca` e `estado`), `# fontes:` agrupado (`deps.tsv×8`), envelope ≤ 12 linhas e 1.500 B (`… +N fontes`), `commits_desde_o_mapa` por repositório; rodapé com `n`/`M` somando só seções `dados`; só `resumo` → `# resumo | fontes: ...`.
- **AD-5** `resolver(projeto, modulo)` única função que conhece a árvore do mapa; módulo = caminho de `index.json` (aceita basename único; ambíguo → erro 2); `ArgumentParser` subclassado cujo `error()` levanta `ErroConsulta(2)`; `--help` imprime `AJUDA` literal; erros em stdout; só `cli.py` e `render.py` leem `os.environ`; `SCOS_MAP_QUERY_DEBUG=1` mostra traceback.
- **AD-6** `tsv_clean(v) = re.sub(r"[\t\r\n]+", " ", str(v))` em toda célula; truncamento de linha 240 chars (nunca na coluna `marca`; `--all` não desliga); teto global 50 linhas / 6.000 B consumido na ordem das seções `dados`; linha `# truncado: use <flag>` antes do rodapé.
- **AD-7** `SCHEMA_TESTADO = (2, 1)` constante única; comparação por tuplas de inteiros (major diferente → erro 4; minor maior → aviso).
- **AD-8** `PERGUNTA` é a fonte única do roteamento; registro = módulos de `comandos/` (menos `_*.py`), sem dispatch manual; tabela de 13 linhas só na skill `scos-query`.
- **AD-9** Somente leitura, uma exceção de escrita: log via `render.emitir(...)` (stdout + log, em todos os caminhos inclusive erro 1 e 2); registro TSV `ts_utc, subcomando, projeto, modulo, bytes_stdout_utf8, linhas_stdout, codigo, schema_versao`; única chamada de `git` = `rev-list --count <head>..HEAD` (somente leitura, em `fatos.py`).
- **AD-10** `conflitos` e `snapshots` (`ESCOPO=workspace`) leem só `workspace.json` e não recebem projeto; `--todos-modulos` só em `deps` e substitui o módulo.
- **AD-11** O comando filtra/agrupa e preenche `total`, `marca`, `refinar`; o render calcula `mostradas`, corta, conta `n/M` e monta `# truncado:`; flags comuns (`--limit/--bytes/--all/--base`) pertencem a `cli.py`; `--all` com `--limit`/`--bytes` → erro 2.
- **AD-12** Estados de leitura: fato `ausente` → erro 3; `indisponivel`/`nao_aplicavel` → resultado normal (código 0, `motivo` no envelope); união de vários fatos que perde algum → erro 3 citando qual, nunca união parcial; erro imprime cabeçalho (se houve fato lido), `# erro:` e rodapé.
- **Estrutura**: `ferramentas/scos-map/scos-map-query.py` + pacote `scos_map_query/` (`modelo`, `fatos`, `render`, `cli`, `filtros`, `comandos/` com 13 módulos); `.claude/skills/scos-query/SKILL.md` (novo) e `.claude/skills/scos-map/SKILL.md` (ponteiro); `.gitignore` + `.scos-map-query.log`; `AGENTS.md` troca a tabela por 1 linha apontando para `scos-query`; `scos-map-build` só edita a referência na descrição.
- **Testes** (suíte `ferramentas/scos-map/tests/` com `fixtures.py`): golden por subcomando e flag (mapa sintético com `gerado_em` e git fixos; `--help` golden = `AJUDA`); tabela da skill = `NOME`/`PERGUNTA`; lista branca de imports; `SCHEMA_TESTADO`; mínimo 3.10 via `ast.parse(feature_version=(3, 10))` + proibição de APIs > 3.10 (`tomllib`, `datetime.UTC`, `enum.StrEnum`, `typing.Self`, `ExceptionGroup`, `except*`); suíte num 3.10 real quando houver; teste de `git rev-list` com hash abreviado de 12 caracteres; latência ≤ 300 ms no maior fixture; benchmark SM-1 contra o mapa real (pulado se não existir).
- **Fixtures novos** (só os exigidos): callgraph disponível (FR-14), estado misto (Q8) e `resolvida`+`parcial` (SM-C1).
- **Pendências do addendum (primeira story)**: exemplo real de 3–5 linhas por subcomando junto dos goldens; rodar o benchmark contra o CLI real e validar a suposição de SM-1; escrever os `--help` que absorvem o inventário (`confianca`, `docs`, `arquivos`, `conflitos`, `snapshots`, `deps`, `tests`, `bytecode`, `callgraph`); fixture de callgraph; `# aviso:` de `docs` e `arquivos` (≤ 100 B); editar `scos-map-build` e `AGENTS.md`.
- **Ordem de entrega do PRD (§6.1)**: fundação (FR-1, 2, 3, 4, 5, 9, 11) sustenta SM-1; depois FR-10, 12, 13, 14 (independentes por subcomando); FR-6, 7, 8 acompanham cada fatia.
- **Fora de escopo / diferido**: subagent/digest, tokens reais no log, comando `gain`, cache entre chamadas, ergonomia humana, novos tipos de fato.

### UX Design Requirements

Não se aplica: o produto é um CLI consumido por agente (PRD §2.2), sem UI e sem documentos DESIGN.md/EXPERIENCE.md.

### FR Coverage Map

FR-1: Epic 1 - Subcomando por fato, resolver, códigos de saída (cada epic acrescenta os seus subcomandos)
FR-2: Epic 1 - Filtros e flags, incluindo a suíte `awk` congelada
FR-3: Epic 2 - `conflitos`
FR-4: Epic 2 - `snapshots`
FR-5: Epic 1 - Envelope de confiança (infra reusada pelos demais epics)
FR-6: Epics 1, 2 e 3 - Golden e `--help` por subcomando, no epic que o entrega
FR-7: Epic 4 - Tabela única de roteamento
FR-8: Epic 1 - Log de custo por chamada
FR-9: Epic 1 - Teto de saída
FR-10: Epic 3 - `arestas`
FR-11: Epic 4 - Skills finas
FR-12: Epic 3 - `tests`
FR-13: Epic 3 - `bytecode`
FR-14: Epic 3 - `callgraph`

NFR-1 e NFR-2: Epic 1. SM-1 e SM-C1: Epics 1 e 2. SM-C2 e base de SM-2: Epic 4.

## Epic List

### Epic 1: Consulta compacta e confiável dos fatos de projeto
O agente consulta layout, configs, dependências, versões gerenciadas, docs, reactor e arquivos de um projeto com o CLI, recebendo poucas linhas com envelope de confiança, teto de saída e log de custo, em vez de abrir o JSON/TSV inteiro.
**FRs covered:** FR-1, FR-2, FR-5, FR-6, FR-8, FR-9
**Subcomandos:** `layout`, `config`, `deps`, `gerenciadas`, `docs`, `reactor`, `arquivos`
**Notas:** primeira story = esqueleto (`modelo`, `fatos`, `render`, `cli`) com um subcomando ponta a ponta e smoke da Q1 do benchmark (valida cedo a suposição de SM-1); a Story 1.8 fecha Q1–Q6 como teste executável.

### Epic 2: Consultas cruzadas do workspace
O agente vê num único comando os conflitos de versão entre os três repositórios e se cada `-SNAPSHOT` local está atrás do repositório produtor.
**FRs covered:** FR-3, FR-4, FR-6
**Notas:** `ESCOPO=workspace` (sem projeto, AD-10); fixtures de estado misto (Q8) e `resolvida`+`parcial` (SM-C1).

### Epic 3: Consultas profundas de bytecode, testes e callgraph (Tier 2 e 3)
O agente consulta arestas de bytecode, testes, higiene de dependências e callgraph de um módulo, com os avisos que impedem conclusões erradas.
**FRs covered:** FR-6, FR-10, FR-12, FR-13, FR-14
**Notas:** subcomandos independentes entre si; FR-14 entrega só `indisponivel` se o fixture de callgraph for inviável.

### Epic 4: Skills finas e roteamento para o CLI
O agente passa a usar o CLI por padrão: skill `scos-query` com a tabela única de 13 linhas, `scos-map` como ponteiro, `AGENTS.md` e `scos-map-build` apontando para ela, sem perder conteúdo do `SKILL.md` antigo.
**FRs covered:** FR-7, FR-11
**Notas:** por último, pois a tabela exige os 13 subcomandos no registro (AD-8).


## Epic 1: Consulta compacta e confiável dos fatos de projeto

O agente consulta layout, configs, dependências, versões gerenciadas, docs, reactor e arquivos de um projeto com o CLI, recebendo poucas linhas com envelope de confiança, teto de saída e log de custo, em vez de abrir o JSON/TSV inteiro.

### Story 1.1: Consulta de `layout` ponta a ponta com envelope de confiança

As a agente (Claude Code),
I want chamar `python3 ferramentas/scos-map/scos-map-query.py layout <projeto> <módulo>`,
So that eu receba o pacote base, as áreas e os entry points de um módulo em poucas linhas, com o estado de confiança do fato, sem abrir o `layout.json` inteiro.

**Acceptance Criteria:**

**Given** um mapa sintético de `fixtures.py` com `layout.json` de um módulo
**When** o agente roda `layout <projeto> <módulo>`
**Then** a saída traz, nesta ordem: o cabeçalho `# confianca=… estado=… gerado=…`, uma seção `## … (m de t)` por tipo de dado (pacote base, áreas e entry points) e a última linha `# <n> de <M> linhas casam | fontes: …/layout.json`
**And** nenhuma célula contém TAB, CR ou LF (`tsv_clean`) e o módulo não faz E/S, `print` nem lê ambiente (AD-1)
**And** o resultado bate com o golden em `ferramentas/scos-map/tests/` (FR-6).

**Given** o diretório corrente em qualquer subpasta do workspace
**When** o CLI resolve a raiz
**Then** usa o ancestral mais próximo que contém `.scos-map/workspace.json`
**And** sem esse arquivo sai com código 3 e a linha `# erro: <mensagem> | acao: <comando de scos-map-build>`, em stdout (AD-5).

**Given** projeto inexistente, módulo inexistente, módulo ausente em escopo `modulo`, módulo informado em escopo de projeto, ou basename ambíguo
**When** o CLI é invocado
**Then** projeto ou módulo inexistente sai com código 3, uso inválido com código 2 (o ambíguo lista as opções), sempre em uma linha de erro, sem traceback
**And** erro interno sai com código 1 e `# erro: interno`; `SCOS_MAP_QUERY_DEBUG=1` mostra o traceback.

**Given** o estado do fato em cada situação
**When** o cabeçalho é montado
**Then** `estado` segue a precedência de FR-5 (disponibilidade, depois `frescor` do fato, depois `.git/HEAD` contra o `head` gravado, que dá `obsoleto`, `fresco` ou `desconhecido`)
**And** o fixture com HEAD diferente nunca sai `fresco`, e `commits_desde_o_mapa=N` aparece quando `git` está no PATH, com hash abreviado de 12 caracteres coberto em teste
**And** `completude=parcial` gera a linha `# limitacao:` e fato sem `confianca` gera `confianca=-` (SM-C1).

**Given** `schema_versao` do mapa
**When** é `2.1` ou menor, `2.x` mais novo, ou de outra major
**Then** a primeira é aceita, a segunda segue com `# aviso: schema <v> mais novo que o testado (2.1)` e a terceira sai com código 4 sem adivinhar formato
**And** `SCHEMA_TESTADO = (2, 1)` existe em um único lugar, com teste (AD-7).

**Given** o pacote `scos_map_query/` e `scos-map-query.py`
**When** a suíte roda
**Then** a lista branca de imports de `comandos/` (`modelo`, `filtros`, `re`, `typing`, `dataclasses`, `collections`) e a proibição de `open`/`print`/`input` passam
**And** o CLI usa só stdlib e não importa `scos-map.py` (NFR-1)
**And** `layout --help` imprime o `AJUDA` literal (≤ 1.500 bytes, com o `EXEMPLO` de 3 a 5 linhas, que também é caso de teste) e `argparse` nunca escreve em stderr (AD-5)
**And** o teste por AST de `comandos/` proíbe também `sys.stdout` e `os.environ` (FR-6), além de `open`/`print`/`input`.

**Given** o mapa real e a Q1 do benchmark
**When** o smoke roda contra o CLI real ao fim desta story
**Then** a razão CLI/`grep` e CLI/`Read` da Q1 é registrada na própria story, validando cedo a suposição de SM-1 (PRD §9)
**And** se estourar a meta, o envelope é enxugado ou a meta recalibrada antes das Stories 1.2 a 1.7.

### Story 1.2: Teto de saída e flags comuns

As a agente (Claude Code),
I want que nenhuma consulta devolva mais que um teto de linhas e bytes, a menos que eu peça,
So that uma consulta quente não consuma meu contexto.

**Acceptance Criteria:**

**Given** um fixture de `layout` com mais de 50 linhas de dados ou mais de 6.000 bytes
**When** a consulta roda sem flags
**Then** a saída traz no máximo 50 linhas e 6.000 bytes de dados (cabeçalho, limitação, títulos de seção e rodapé não contam), na ordem do fato, sem reordenar
**And** a seção cortada continua visível com a contagem (`## … (0 de 40)`) e uma linha `# truncado: use <flag>` antes do rodapé, sugerindo uma flag válida de FR-2 e nunca `--all` primeiro
**And** o rodapé informa `N de M linhas casam`.

**Given** uma linha individual com mais de 240 caracteres
**When** a saída é renderizada
**Then** a linha é truncada em 240 caracteres Unicode com `…`, nunca na coluna `marca`, e `--all` não desliga esse truncamento (AD-6).

**Given** as flags comuns registradas por `cli.py` em todo subparser
**When** o agente usa `--limit N`, `--bytes N` ou `--all`
**Then** o teto é sobrescrito de forma explícita, e `--all` junto com `--limit` ou `--bytes` sai com código 2 (AD-11)
**And** `--base` acrescenta a `base` do fato ao envelope e o comando não declara nem vê essas flags
**And** uma seção `resumo` sai inteira (até 20 linhas), fora do teto e da contagem `n`/`M`.

**Given** a suíte de testes
**When** roda o teste de teto
**Then** nenhuma invocação sem `--all` excede os tetos, e o caso está coberto por golden (FR-6, FR-9).

### Story 1.3: Log de custo por chamada

As a revisor do projeto,
I want um registro append-only de bytes e linhas de cada invocação,
So that a economia prometida seja verificável ao longo do tempo.

**Acceptance Criteria:**

**Given** uma invocação bem-sucedida
**When** `render.emitir(...)` escreve a saída
**Then** acrescenta ao `.scos-map-query.log`, na raiz do workspace e fora de `.scos-map/`, um registro TSV `ts_utc, subcomando, projeto, modulo, bytes_stdout_utf8, linhas_stdout, codigo, schema_versao` (`-` para o desconhecido), em uma única chamada de escrita em modo append (AD-9)
**And** vale o mesmo quando o agente roda de dentro de um dos repositórios.

**Given** `SCOS_MAP_QUERY_LOG` definido
**When** o CLI grava o log
**Then** usa esse caminho em vez do padrão, e só `cli.py` e `render.py` leem `os.environ`.

**Given** erro de código 1 ou 2
**When** `main` termina
**Then** o registro é gravado com o código de saída (todo caminho passa por `emitir`)
**And** sem `workspace.json` em qualquer ancestral o CLI sai com código 3 e não grava log.

**Given** o log não pode ser gravado (diretório sem permissão)
**When** a consulta roda
**Then** a resposta sai normalmente e sem erro
**And** `.scos-map-query.log` está listado no `.gitignore` da raiz.

### Story 1.4: Consulta de `config` e `docs`

As a agente (Claude Code),
I want listar arquivos de configuração e documentação por prefixo ou termo,
So that eu ache onde mora a config ou a doc sem abrir `config.json` (≈142KB) nem `docs.json`.

**Acceptance Criteria:**

**Given** um fixture de `config.json`
**When** o agente roda `config <projeto> <módulo>`
**Then** a saída traz `path \t bytes` por arquivo, valores nunca aparecem, e `--prefixo` filtra por prefixo de `path`
**And** o golden e o `EXEMPLO` real de 3–5 linhas no `--help` passam.

**Given** um fixture de `docs.json`
**When** o agente roda `docs <projeto> <módulo>`
**Then** a saída traz `path \t título \t subtipo`, `--texto` filtra por termo em `path` ou título sem diferenciar maiúsculas e `--prefixo` filtra por prefixo
**And** a saída traz a linha `# aviso:` de até 100 bytes ("frontmatter lido literalmente; sem status não é rascunho") e a `completude` parcial gera `# limitacao:` (FR-5)
**And** o `--help docs` explica os subtipos e a regra de documento antigo ao lado de código recente.

**Given** um filtro sem resultado ou inválido
**When** o comando roda
**Then** o sem resultado traz cabeçalho, zero linhas e rodapé com as fontes consultadas, e o inválido sai em uma linha de erro, sem traceback (FR-2).

### Story 1.5: Consulta de `reactor` e `gerenciadas`

As a agente (Claude Code),
I want ver as fronteiras entre módulos e as versões que a BOM gerencia,
So that eu decida dependências sem ler `_reactor.json` nem `gerenciadas.tsv`.

**Acceptance Criteria:**

**Given** um fixture de `_reactor.json`
**When** o agente roda `reactor <projeto>`
**Then** a saída traz `id \t tipo` por módulo e `de -> para (scope)` por aresta interna, em seções separadas, na ordem do fato
**And** o subcomando de escopo `projeto` rejeita módulo posicional com código 2.

**Given** um fixture de `gerenciadas.tsv`
**When** o agente roda `gerenciadas <projeto> <módulo>`
**Then** a saída traz `ga \t versão \t origem \t scope` e `--ga` filtra por substring de coordenada (via `filtros.py`, compartilhado)
**And** o acesso às colunas do TSV é por nome (pelo cabeçalho), nunca por posição (AD-3).

**Given** os dois subcomandos
**When** a suíte roda
**Then** cada um tem golden, `EXEMPLO` real e `AJUDA` ≤ 1.500 bytes.

### Story 1.6: Consulta de `arquivos` com a suíte `awk` congelada

As a agente (Claude Code),
I want filtrar `files.tsv` por módulo, tipo e número de commits,
So that eu ache arquivos quentes ou de um módulo sem rodar `awk` sobre o TSV inteiro.

**Acceptance Criteria:**

**Given** um fixture de `files.tsv`
**When** o agente roda `arquivos <projeto>` sem filtro
**Then** a saída traz `path \t kind \t module \t commits_90d`, limitada pelo teto de FR-9, com `# aviso:` "histórico de arquivo não está no mapa".

**Given** as três consultas `awk` congeladas de FR-2
**When** são reproduzidas como `--em-modulo organization --kind codigo` e `--commits-90d-min 6`
**Then** cada uma devolve exatamente as linhas que o `awk` equivalente devolveria sobre o mesmo fixture (teste de compatibilidade)
**And** `--commits-90d-min` aceita comparação numérica e `--em-modulo` filtra a coluna `module`, sem escolher o módulo do fato.

**Given** coluna ou valor de filtro inválido
**When** o comando roda
**Then** sai erro de uma linha, sem traceback, e o rodapé de truncamento sugere uma flag desta tabela.

### Story 1.7: Consulta de `deps` com união de transitivas

As a agente (Claude Code),
I want consultar as dependências de um módulo juntando diretas e transitivas,
So that eu nunca conclua "não usa X" a partir de só uma das tabelas.

**Acceptance Criteria:**

**Given** `deps.tsv` do módulo e `facts/_transitivas_comuns.tsv` do projeto
**When** o agente roda `deps <projeto> <módulo>`
**Then** a saída une as duas fontes, com linhas `ga \t versão \t scope \t origem` e a marca `[transitiva]`, e o `_transitivas_comuns.tsv` é lido uma vez, em seção própria `transitivas` (AD-3)
**And** `--ga` filtra por coordenada (substring).

**Given** `--todos-modulos`
**When** o agente roda `deps <projeto> --todos-modulos --ga jjwt`
**Then** o comando percorre todos os módulos do projeto, substitui o módulo posicional, e reproduz o resultado do `awk` congelado de FR-2
**And** `--todos-modulos` não existe em outros subcomandos (AD-10).

**Given** o subcomando lê mais de um fato
**When** o envelope é montado
**Then** o cabeçalho mostra o pior caso de `confianca` e `estado` (ordens de AD-4) e a linha `# fontes: <arquivo>(<confianca>,<estado>) …` lista cada um, agrupada (`deps.tsv×8`) e limitada a 12 linhas e 1.500 bytes (`… +N fontes`)
**And** se qualquer fato da união estiver ausente, sai erro 3 citando qual, nunca união parcial (AD-12).

**Given** o `--help deps`
**When** o agente o lê
**Then** explica a coluna `origem` (`effective-pom`) e a armadilha das transitivas.

### Story 1.8: Guardas de qualidade e benchmark SM-1 (Q1–Q6)

As a revisor do projeto,
I want testes que provem teto, versão mínima, latência e o benchmark contra o CLI real,
So that a promessa de economia e de confiança seja verificável de forma automática.

**Acceptance Criteria:**

**Given** o benchmark canônico (`benchmark-baseline.py`) e o mapa real
**When** o teste roda as perguntas Q1 a Q6 contra o CLI real
**Then** cada resposta é conferida por contagem independente de linhas e por conteúdo esperado, não só por substring
**And** a razão CLI/`grep` fica dentro da meta de SM-1 (JSON: mediana ≤ 1,0× e nenhuma > 1,6×; TSV: ≤ máx(`grep` + 64 B, 1,1 × `grep`)) e CLI/`Read` ≤ 10%
**And** o benchmark é portado de `benchmark-baseline.py` para `ferramentas/scos-map/tests/` só com stdlib (NFR-1): `jq` não é exigido (a coluna `jq` do addendum é informativa e sai do teste) e a comparação com `grep` usa `subprocess`
**And** o teste é pulado se o mapa real ou o `grep` não existirem; se a meta estourar, o resultado é registrado para recalibrar a meta ou enxugar o envelope (suposição de SM-1).

**Given** o pacote inteiro
**When** o teste de versão mínima roda
**Then** `ast.parse(feature_version=(3, 10))` passa em todos os arquivos e nenhuma API acima de 3.10 aparece (`tomllib`, `datetime.UTC`, `enum.StrEnum`, `typing.Self`, `ExceptionGroup`, `except*`)
**And** a suíte também roda num interpretador 3.10 quando houver um.

**Given** o maior fixture disponível até esta story (ex.: `files.tsv`; a latência sobre `bytecode_edges.tsv` é reconferida na Story 3.1)
**When** a latência é medida
**Then** cada invocação responde em ≤ 300 ms (NFR-2).

**Given** fixtures de fato `obsoleto`, `resolvida`+`parcial` com árvore suja e HEAD ilegível (criados nesta story em `fixtures.py`; a Story 2.1 os reutiliza)
**When** os testes de contrato rodam
**Then** o envelope corresponde ao que o fato grava, com zero divergências (SM-C1)
**And** o registro é montado a partir dos módulos de `comandos/` (menos `_*.py`), sem dispatch escrito à mão, e cresce sozinho a cada subcomando novo (AD-8).

## Epic 2: Consultas cruzadas do workspace

O agente vê num único comando os conflitos de versão entre os três repositórios e se cada `-SNAPSHOT` local está atrás do repositório produtor.

### Story 2.1: Consulta `conflitos`

As a agente (Claude Code),
I want listar as bibliotecas com versões divergentes entre os três repositórios,
So that eu investigue conflitos sem carregar `workspace.json` inteiro.

**Acceptance Criteria:**

**Given** um fixture de `workspace.json` com `conflitos_de_versao_cruzados`
**When** o agente roda `conflitos` (sem projeto, `ESCOPO=workspace`)
**Then** a saída traz uma linha por biblioteca (`ga \t versão:repositórios | …`), equivalente em conteúdo ao fato
**And** passar um projeto sai com código 2 (AD-10).

**Given** o fixture `resolvida`+`parcial` com árvore suja
**When** o cabeçalho é montado
**Then** traz `confianca=resolvida estado=<…> completude=parcial`, a linha `# limitacao:` e a cláusula "mapa gerado com alterações não commitadas", com o pior caso entre os três `head` (SM-C1)
**And** o `--help conflitos` explica obsoleto, árvore suja, scope `test` e o sufixo `(gerenciada)`.

**Given** zero conflitos
**When** o comando roda
**Then** a saída traz o cabeçalho, a linha de limitação e `# 0 de 0 linhas casam | fontes: workspace.json`, nunca saída vazia (FR-3).

**Given** o benchmark Q7
**When** roda contra o CLI real
**Then** a resposta é conferida por contagem e conteúdo, e CLI/`Read` ≤ 10%.

### Story 2.2: Consulta `snapshots`

As a agente (Claude Code),
I want saber se os `-SNAPSHOT` do `~/.m2` estão atrás do repositório produtor,
So that eu decida se preciso rodar `mvn clean install` antes de buildar a Organization.

**Acceptance Criteria:**

**Given** `snapshots_locais` em `workspace.json`
**When** o agente roda `snapshots`
**Then** a saída traz uma linha por repositório produtor (`produtor \t N jar(s) \t estados \t max_atraso \t ação recomendada`), agrupada
**And** `--detalhe` lista uma linha por coordenada (`ga`, versão, `estado` do fato, `acao`, `atraso_dias`).

**Given** um `repo_local.head` gravado
**When** o estado é calculado
**Then** head diferente do HEAD atual dá `obsoleto`, igual com mapa gerado sujo dá `desconhecido`, HEAD ilegível dá `desconhecido`, e o fixture com head divergente nunca sai `fresco`
**And** o CLI só lê o fato e `.git/HEAD` (e opcionalmente conta commits), sem acessar `~/.m2` nem varrer arquivos.

**Given** a saída
**When** é lida pelo agente
**Then** a linha `# limitacao:` diz que o mtime do jar não prova o conteúdo, que commit só de documentação também marca atraso e que alterações não commitadas ou em stash não contam (FR-4)
**And** o `--help snapshots` explica `jar_atual` ≠ "contém o último commit".

**Given** um fixture de estado misto (`jar_atual`, `jar_desatualizado`, `jar_ausente`)
**When** o comando roda
**Then** os estados aparecem agrupados sem esconder a mistura, e o benchmark Q8 passa com conteúdo e razão CLI/`Read` ≤ 10%.

## Epic 3: Consultas profundas de bytecode, testes e callgraph (Tier 2 e 3)

O agente consulta arestas de bytecode, testes, higiene de dependências e callgraph de um módulo, com os avisos que impedem conclusões erradas.

### Story 3.1: Consulta `arestas`

As a agente (Claude Code),
I want listar as arestas de bytecode de um módulo filtrando por origem, destino ou pacote,
So that eu saiba quem usa uma classe antes de alterá-la, sem abrir um TSV de 958KB.

**Acceptance Criteria:**

**Given** um fixture de `bytecode_edges.tsv`
**When** o agente roda `arestas <projeto> <módulo> --para <classe>`
**Then** a saída traz `de \t para \t tipo \t origem`, e `--de`, `--para` e `--pacote` filtram por classe ou prefixo
**And** o teto de FR-9 e o envelope de FR-5 se aplicam, com o rodapé de truncamento sugerindo um dos filtros.

**Given** o módulo sem `bytecode_edges.tsv`
**When** o comando roda
**Then** sai erro de código 3 indicando o comando de build com `--tier 2`/`--tier 3`, e o CLI nunca dispara a geração.

**Given** o arquivo existe mas está vazio
**When** o comando roda
**Then** o rodapé traz `motivo_vazio` e `diagnostico` do fato e a saída deixa claro que arestas vazias não provam que o módulo não tem dependências.

**Given** o maior fato do mapa (`bytecode_edges.tsv`, 958KB)
**When** a latência é medida
**Then** a invocação responde em ≤ 300 ms (NFR-2).

**Given** o benchmark Q9 e Q10
**When** rodam contra o CLI real
**Then** a Q9 (17 linhas) e a Q10 (107 linhas casam, truncada, com aviso) passam em conteúdo e dentro das metas de SM-1.

### Story 3.2: Consulta `tests`

As a agente (Claude Code),
I want saber como um módulo é testado,
So that eu nunca afirme "X está testada" a partir do nome de um teste.

**Acceptance Criteria:**

**Given** `tests.json` e `tests.tsv`
**When** o agente roda `tests <projeto> <módulo>`
**Then** a saída traz o resumo (raízes varridas, arquivos, tipos, frameworks com `origem` `declarada` ou `inferida`, `cobertura` com o `estado` do fato), em seção `resumo`
**And** `--arquivos` lê `tests.tsv` (`path`, `tipo`, `alvo_heuristico`, `linhas`, `commits_90d`) e `--alvo <classe>` restringe ao alvo.

**Given** `alvo_heuristico`
**When** é exibido
**Then** sai sempre com a marca `[heuristica]` e o `--help tests` explica que se pode afirmar "existe um teste chamado XTest", nunca "X está testada".

**Given** `--alvo` sem arquivos de teste
**When** o comando roda
**Then** a saída diz "nenhum arquivo de teste identificado nas raízes analisadas: <raízes>", nunca "não existe teste"
**And** a `cobertura` sai sempre com o `estado` do fato.

**Given** a saída de `tests`
**When** é emitida
**Then** traz `# aviso:` de até 100 bytes: "alvo é heurística; existe teste chamado XTest, não prova cobertura" (FR-5)

**Given** o benchmark Q11
**When** roda contra o CLI real
**Then** a resposta é conferida em conteúdo e a razão é registrada (a meta tolera o `grep` menor sem tipos nem cobertura).

### Story 3.3: Consulta `bytecode`

As a agente (Claude Code),
I want ver a higiene de dependências de um módulo a partir do bytecode,
So that eu saiba o que o módulo usa sem declarar, sem tratar falso positivo como risco.

**Acceptance Criteria:**

**Given** `bytecode.json`
**When** o agente roda `bytecode <projeto> <módulo>`
**Then** a saída traz o resumo com contagem por balde (`deps_usadas_ausentes_do_pom`, `deps_usadas_via_transitiva`, `deps_declaradas_sem_uso`, `deps_ignoradas_na_analise`), `frescor` e `transitivas_resolvidas`
**And** `--balde <nome>` lista `artefato \t referencias`.

**Given** os baldes
**When** são apresentados
**Then** só `deps_usadas_ausentes_do_pom` é apresentado como risco imediato, itens com `provavel_falso_positivo: true` saem com `[provavel_falso_positivo]` e `deps_ignoradas_na_analise` nunca aparece como problema.

**Given** `transitivas_resolvidas` falso
**When** o envelope é montado
**Then** traz `# limitacao:` dizendo que a divisão dos dois primeiros baldes não é confiável, e balde ausente sai como "não calculado", nunca como "0"
**And** o `estado` considera o `frescor` próprio do fato (`compilado_em`): bytecode compilado antes de mudanças nas fontes sai `obsoleto`.

**Given** a saída de `bytecode`
**When** é emitida
**Then** traz `# aviso:` de até 100 bytes: "só deps_usadas_ausentes_do_pom é risco; demais baldes são higiene" (FR-5)

**Given** o benchmark Q12
**When** roda contra o CLI real
**Then** a resposta passa em conteúdo e CLI/`Read` ≤ 10%.

### Story 3.4: Consulta `callgraph`

As a agente (Claude Code),
I want consultar o grafo de chamadas de métodos quando ele existir,
So that eu veja chamadores sem confundir ausência de dado com ausência de chamada.

**Acceptance Criteria:**

**Given** o fato com `estado` diferente de `disponivel` (ex.: `java-callgraph.jar nao encontrado`)
**When** o agente roda `callgraph <projeto> <módulo>`
**Then** a saída traz o cabeçalho de FR-5, o `motivo` e o `comando_sugerido` do fato, nunca saída vazia, com código 0.

**Given** um fixture de callgraph disponível, produzido em `ferramentas/scos-map/tests/fixtures.py` com as colunas do gerador (`de`, `para`, `invoke`, `certeza`)
**When** o agente roda sem filtro, com `--de`/`--para`/`--entrypoints`, `--lacunas` ou `--sem-chamador`
**Then** sem filtro sai o resumo (`arestas_total`, `arestas_ambiguas`, `entrypoints`), os filtros leem `callgraph_edges.tsv`, `--lacunas` lista `lacunas_conhecidas` e `--sem-chamador` lista `metodos_sem_chamador`
**And** a advertência do fato (proxies, reflexão e implementações geradas em runtime não aparecem) vai sempre em `# limitacao:` e `--sem-chamador` sempre diz que não é lista de código morto (endpoints HTTP, `@Scheduled` e `@EventListener` não têm chamador no bytecode).

**Given** a saída de `callgraph` (qualquer estado do fato)
**When** é emitida
**Then** traz `# aviso:` de até 100 bytes: "ausência de aresta não prova ausência de chamada" (FR-5)

**Given** a produção do fixture se mostrar inviável
**When** a story é fechada
**Then** a entrega cobre só o caso `indisponivel`, com o motivo registrado, e as arestas ficam para quando houver dado real (risco declarado de FR-14).

## Epic 4: Skills finas e roteamento para o CLI

O agente passa a usar o CLI por padrão: skill `scos-query` com a tabela única de 13 linhas, `scos-map` como ponteiro, `AGENTS.md` e `scos-map-build` apontando para ela, sem perder conteúdo do `SKILL.md` antigo.

### Story 4.1: `--help` geral e `--help confianca`

As a agente (Claude Code),
I want ler a legenda do envelope e a lista de subcomandos direto do CLI,
So that a skill não precise carregar formato, exemplos nem legenda.

**Acceptance Criteria:**

**Given** o registro dos módulos de `comandos/` (menos `_*.py`)
**When** o agente roda `--help`
**Then** lista os 13 subcomandos com a `PERGUNTA` de cada um, sem dispatch escrito à mão (AD-8).

**Given** `--help confianca`
**When** é lido
**Then** traz a legenda de `confianca`, `estado` (incluindo `desconhecido`), `completude`, `desvios`, `base` e `nao_aplicavel` como resultado legítimo, em no máximo 2.500 bytes
**And** o `--help` de cada subcomando tem no máximo 1.500 bytes, com teste.

**Given** as regras do inventário que dependem do `--help` (`docs`, `arquivos`, `deps`, `conflitos`, `snapshots`, `tests`, `bytecode`, `callgraph`)
**When** a suíte roda
**Then** cada `--help` cobre as regras que o inventário do addendum atribui a ele.

### Story 4.2: Skill `scos-query` com a tabela única de roteamento

As a agente (Claude Code),
I want uma skill curta que me diga qual subcomando chamar para cada pergunta,
So that eu use o CLI primeiro e deixe `Read` do fato bruto como último recurso.

**Acceptance Criteria:**

**Given** `.claude/skills/scos-query/SKILL.md`
**When** a suíte conta tamanho
**Then** a descrição tem no máximo 300 caracteres e o corpo (sem frontmatter) no máximo 30 linhas e 2.000 caracteres
**And** o corpo contém só: regra de chamar o CLI direto, comando literal (`python3 ferramentas/scos-map/scos-map-query.py <subcomando> ...`), a tabela de roteamento, o aviso de `--all` e uma linha para perguntas abertas (ler `index.json`, `_reactor.json` e o `layout.json` dos maiores módulos).

**Given** a tabela de roteamento
**When** o teste a compara com o registro
**Then** tem exatamente 13 linhas, os `NOME` e as `PERGUNTA` do registro (`arestas` separada de `bytecode`), e divergência falha a suíte (AD-8)
**And** linha sem subcomando só vale com exceção motivada na própria tabela
**And** traz o aviso do tamanho dos fatos grandes (ex.: `config.json` ≈ 142KB) e o fallback `grep`/`awk` para TSV, nunca `Read` do TSV inteiro.

### Story 4.3: `scos-map` como ponteiro e teste de destino das regras

As a mantenedor do workspace,
I want reduzir a skill `scos-map` a um ponteiro curto sem perder nenhuma regra,
So that o custo de contexto caia e as regras de alto risco continuem entregues ao agente.

**Acceptance Criteria:**

**Given** `.claude/skills/scos-map/SKILL.md`
**When** a suíte conta tamanho
**Then** a descrição tem no máximo 300 caracteres e o corpo no máximo 30 linhas e 2.000 caracteres, apontando para `scos-query` e citando `status` do `scos-map.py`.

**Given** o inventário do `SKILL.md` antigo (218 linhas) no addendum
**When** o teste de inventário roda
**Then** cobre todas as seções do `SKILL.md` antigo, cada uma com destino (CLI, `--help`, `scos-query`, `scos-map-build` ou descartada com motivo) e cada regra de "Regras que evitam conclusão errada" tem destino registrado
**And** cada regra aparece na saída do subcomando (`# aviso:` ou `# limitacao:`) ou em uma das duas skills.

**Given** as regras de alto risco ("não usa X", "está testada", "está obsoleto")
**When** o teste de destino roda
**Then** estar só no `--help` não basta: a regra aparece na saída do subcomando ou na skill.

### Story 4.4: Referências em `AGENTS.md` e `scos-map-build`, e métrica de sessão

As a agente (Claude Code),
I want que `AGENTS.md` e `scos-map-build` apontem para `scos-query` como skill de leitura,
So that eu encontre a única tabela de roteamento e a adoção seja medida.

**Acceptance Criteria:**

**Given** o `AGENTS.md` da raiz
**When** a story é fechada
**Then** a tabela de roteamento sai e entra uma linha apontando para a skill `scos-query`, sem outras mudanças de conteúdo.

**Given** a skill `scos-map-build`
**When** a story é fechada
**Then** só a referência na descrição muda, passando a apontar para `scos-query` como skill de leitura, e o restante fica intacto.

**Given** o benchmark de sessão (Q1, Q5, Q6, Q7 e Q9, com a skill carregada uma vez, os `--help` usados e todas as saídas)
**When** é executado
**Then** o total fica em ≤ 10% do total da mesma sessão via `Read`, incluindo as 10,6KB do `SKILL.md` antigo no lado do `Read` (SM-C2)
**And** o total contra o `grep` é registrado como informação, sem meta
**And** o procedimento de verificação de SM-2 (20 perguntas em 5 sessões, por quem revisa) fica documentado para a pós-adoção.
