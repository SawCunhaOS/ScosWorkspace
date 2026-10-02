# Addendum — Scripts de Consulta Rápida para scos-map

Material de apoio à PRD (`prd.md`): evidência de dimensionamento, medições, opções consideradas, hipóteses descartadas e o inventário do `SKILL.md`. Leitura obrigatória: FR-6 → *Medições* e *Pendências*; FR-8 → *Hipóteses descartadas* (log de custo); FR-11 → *Inventário do `SKILL.md`*. O restante é contexto para quem for desenhar a arquitetura e as stories.

## Evidência de tamanho (custo em tokens hoje)

Levantado lendo o `.scos-map/` já gerado nos três repositórios (2026-09-14). Reproduzível com `du -sh <repo>/.scos-map` e `wc -c -l <arquivo>`; tokens estimados ≈ bytes/3,5. O custo do `grep` equivalente está nas medições abaixo.

- `SawCunhaOS-Flow/.scos-map`: 3,8MB no total. `facts/_raiz/config.json` = 142KB numa única linha (minificado). `layout.json` do módulo usecase = 54KB numa linha. `facts/organization/flow-organization-usecase/bytecode_edges.tsv` = 958KB/6936 linhas; `flow-organization-domain/bytecode_edges.tsv` = 674KB. `files.tsv` = 222KB/952 linhas.
- `SawCunhaOS-Foundation/.scos-map`: 1,2MB no total. `facts/_raiz/docs.json` = 25KB numa linha. Vários `bytecode_edges.tsv` de 48-80KB.
- `sawcunha-open-system-bom/.scos-map`: 60KB no total — projeto sem código, confirma que o custo escala com o tamanho do módulo.
- Como os JSONs são minificados numa linha só, o `Read` tool não trunca por linha: uma pergunta pontual (“qual o entry point do usecase?”) paga os 54KB inteiros de `layout.json` em tokens, mesmo que a resposta caiba em uma linha. `[não verificado]` O limite de tamanho do próprio `Read` pode interromper leituras muito grandes, o que mudaria o baseline do `Read` nesses casos.
- Os TSVs já têm um caminho barato hoje via `awk -F'\t'` (recomendado no `SKILL.md`) — o problema de custo em tokens é especificamente dos fatos em JSON.

## Medições de 2026-10-02

Benchmark canônico de 12 perguntas.

Script reproduzível e portátil: `benchmark-baseline.py` (nesta pasta). Ele localiza a raiz do workspace por `$SCOS_ROOT` ou pelo ancestral que contém `.scos-map/workspace.json`, e exige `python3`, `jq` e `grep`. O "CLI" é um **proxy**, ou seja, o piso ideal do que o CLI real fará: recorte mínimo do fato, mais o cabeçalho de FR-5 montado com a `confianca` e a `completude` reais de cada fato (e a linha `# limitacao:` quando parcial), mais o rodapé e os tetos de FR-9 (50 linhas, 6.000 bytes). O script confere cada resposta por contagem independente de linhas (`grep -c`/`jq length`) e por conteúdo esperado, mas ainda não compara o texto completo com a saída do `grep`. Os cabeçalhos usam o `estado` real do mapa de hoje (`obsoleto`), e a Q5 inclui a linha `# aviso:`. Quando o CLI real existir, a coluna do CLI passa a vir dele.

*Mapas usados: Flow `2026-09-15T00:32:06Z`, Foundation e BOM `…:16Z`, workspace `…:17Z`.

| Pergunta | `Read` | `grep` | `jq` sob medida | CLI (proxy) | CLI/Read | CLI/grep |
|---|---:|---:|---:|---:|---:|---:|
| Q1 pacote base e áreas do usecase | 54.798 | 1.506 | 462 | 410 | 0,7% | 0,27× |
| Q2 arquivos de config em `etc/api/organization` | 142.056 | 622 | 498 | 583 | 0,4% | 0,94× |
| Q3 dependências jackson do usecase (`deps.tsv` + transitivas) | 12.819 | 1.129 | n/a | 701 | 5,5% | 0,62× |
| Q4 versão de jackson gerenciada pela BOM | 3.570 | 474 | n/a | 185 | 5,2% | 0,39× |
| Q5 docs sobre nomenclatura (path/título, com `# aviso:`) | 51.045 | 681 | 251 | 661 | 1,3% | 0,97× |
| Q6 dependências internas do domain | 10.431 | 365 | 213 | 272 | 2,6% | 0,75× |
| Q7 conflitos de versão cruzados | 18.500 | n/a | 133 | 457 | 2,5% | n/a |
| Q8 SNAPSHOTs (agrupado por produtor) | 18.500 | n/a | 39 | 390 | 2,1% | n/a |
| Q11 frameworks e tipos de teste do usecase | 17.893 | 311 | 155 | 480 | 2,7% | 1,54× |
| Q12 deps usadas via transitiva (`bytecode.json`) | 6.100 | n/a | 209 | 327 | 5,4% | n/a |
| Q9 arestas de `ValidateAuthorityUseCase` (17 linhas) | 957.682 | 3.031 | n/a | 3.131 | 0,3% | 1,03× |
| Q10 arestas com `ScosPaginated` (107 linhas; pergunta quente) | 957.682 | 15.636 | n/a | 6.023 (truncado); 15.752 com `--all` | 0,6% | 0,39× (1,01× com `--all`) |*

| Pergunta | `Read` | `grep` | `jq` sob medida | CLI (proxy) | CLI/Read | CLI/grep |
|---|---:|---:|---:|---:|---:|---:|
| Q1 pacote base e áreas do usecase | 54.798 | 1.506 | 462 | 410 | 0,7% | 0,27× |
| Q2 arquivos de config em `etc/api/organization` | 142.056 | 622 | 498 | 583 | 0,4% | 0,94× |
| Q3 dependências jackson do usecase (`deps.tsv` + transitivas) | 12.819 | 1.129 | n/a | 701 | 5,5% | 0,62× |
| Q4 versão de jackson gerenciada pela BOM | 3.570 | 474 | n/a | 185 | 5,2% | 0,39× |
| Q5 docs sobre nomenclatura (path/título, com `# aviso:`) | 51.045 | 681 | 251 | 661 | 1,3% | 0,97× |
| Q6 dependências internas do domain | 10.431 | 365 | 213 | 272 | 2,6% | 0,75× |
| Q7 conflitos de versão cruzados | 18.500 | n/a | 133 | 457 | 2,5% | n/a |
| Q8 SNAPSHOTs (agrupado por produtor) | 18.500 | n/a | 39 | 390 | 2,1% | n/a |
| Q9 arestas de `ValidateAuthorityUseCase` (17 linhas) | 957.682 | 3.031 | n/a | 3.131 | 0,3% | 1,03× |
| Q10 arestas com `ScosPaginated` (107 linhas; pergunta quente) | 957.682 | 15.636 | n/a | 6.023 (truncado); 15.752 com `--all` | 0,6% | 0,39× (1,01× com `--all`) |
| Q11 frameworks e tipos de teste do usecase | 17.893 | 311 | 155 | 480 | 2,7% | 1,54× |
| Q12 deps usadas via transitiva (`bytecode.json`) | 6.100 | n/a | 209 | 327 | 5,4% | n/a |

**Resultado.** Contra o `Read`, 12 de 12 ficam em 10% ou menos (0,3% a 5,5%). Nos JSON, a mediana de CLI/`grep` é 0,94× (0,27× a 1,54×), dentro da meta de SM-1; nos TSV, 0,39× a 1,03×. A única pergunta acima do `grep` é a Q11 (1,54×); a Q9 fica um pouco acima (1,03×), dentro da tolerância. A Q10 só fica abaixo do `grep` por causa do truncamento.

**Por tipo de fato.**
- **JSON:** o `Read` é 10 a 400× o `grep`. O `jq` feito à mão por quem conhece a estrutura é menor que o CLI em Q2, Q5–Q8, Q11 e Q12, mas não traz envelope nem rodapé; o CLI paga cerca de 200 a 300 bytes por isso e dispensa conhecer a estrutura.
- **TSV:** Q3 e Q10 vencem o `grep` porque o CLI devolve só as colunas úteis e trunca linhas longas; Q9 fica praticamente empatada com o `grep` (+98 bytes de cabeçalho e rodapé, 1,03×), dentro da tolerância de SM-1. A Q10 é a única que passa dos tetos e mostra o aviso de truncamento.

**Ressalvas por pergunta.**
- **Q2:** pouca folga (583 contra 622 B).
- **Q3:** o `_transitivas_comuns.tsv` do Flow tem 52 bytes, então a união com `deps.tsv` contribui com zero linhas. Essa união é o que justifica o subcomando `deps`; o ganho está provado pelo desenho, não pela medição.
- **Q4 e Q5:** os `grep` comparados não são respostas equivalentes: Q4 compara com o `pom.xml`; Q5 devolve só nomes de arquivo, sem título.
- **Q7 e Q8:** não têm `grep` possível. O `Read` de `workspace.json` pesa só 18,5KB; o valor dessas consultas é a semântica (envelope, frescor, agrupamento), não o tamanho. Na Q8 os 10 itens estão `jar_desatualizado`, então não há caso de mistura de estados; esse caso fica como fixture da primeira story (SM-C1). Agrupada por produtor, a saída cai para uma linha por repositório.
- **Q11:** o `grep` de imports devolve uma resposta diferente e menor (sem tipos nem cobertura); o ganho ali é de conteúdo e envelope, não de bytes.

**Limites da amostra.** 12 perguntas são um conjunto de regressão, não prova de generalização. O "CLI" é proxy do piso ideal. O mapa usado já está defasado (ver a seção *Verificação do frescor barato e da latência*). Latência do proxy: partida do Python ≈ 9 ms, carga do maior JSON abaixo de 1 ms, `jq` ≈ 3 ms (NFR-2).

**Linha de base de SM-1** (referência para a meta, que está no PRD): 12 de 12 ≤ 10% do `Read`; JSON com mediana 0,94× e máximo 1,54× do `grep`; TSV de 0,39× a 1,03×; `jq` sob medida não é meta.

## Verificação do frescor barato e da latência

Protótipo `prototipo-frescor.py` (nesta pasta): lê `.git/HEAD` sem subprocesso, trata HEAD destacado, `.git` como arquivo (worktree com `commondir`) e `packed-refs`, nunca levanta exceção (ilegível → `desconhecido`) e aplica a regra de FR-5 (head diferente → `obsoleto`; igual com mapa gerado sujo → `desconhecido`; igual e limpo → `fresco`).

**Testes com repositórios temporários criados com `git`:** ref solto, `packed-refs` real (o ref solto deixou de existir após `git pack-refs --all`), worktree, worktree após novo commit, HEAD destacado, diretório sem repositório e caminho inexistente. Todos os casos corretos, e os três estados da regra de FR-5 também.

**Repositórios reais (hoje):**

| Repositório | HEAD lido | `head` gravado no mapa | Resultado | Observação |
|---|---|---|---|---|
| `SawCunhaOS-Flow` | `1c08e865f70a` | `ec4075f862c9` | `obsoleto` | 1 commit, 5 arquivos alterados |
| `SawCunhaOS-Foundation` | `228ab4028288` | `a8e5569a595a` | `obsoleto` | 5 commits, todos `docs(...)`: falso-obsoleto |
| `sawcunha-open-system-bom` | `f3fb8ed4bc93` | `e03ad8ce65a2` | `obsoleto` | — |

Os três mapas foram gerados com árvore suja (`git.dirty=true`), então mesmo com HEAD igual o estado seria `desconhecido`, nunca `fresco`. O sinal hoje dispara nos três repositórios (amostra de 3): é correto, porque os mapas estão de fato defasados, mas um sinal que sempre dispara informa pouco; por isso o cabeçalho traz `commits_desde_o_mapa` (FR-5) e o agente pode julgar se a mudança é só documentação. **Latência:** leitura de `.git/HEAD` ≈ 0,07 ms; processo completo com um `layout.json` de 54KB ≈ 10 ms; varredura do `bytecode_edges.tsv` de 958KB ≈ 1 ms de CPU.

## Alternativas consideradas

Por que este desenho e não outro.

### Prior art

- **jq** — filtro compacto sobre JSON no shell; é o padrão mais próximo do pedido original. Descartado como *interface direta* porque exigiria que quem chama conheça a estrutura interna de cada JSON do `scos-map`, e a saída não traz envelope de confiança. **Passa a ser medido** como concorrente em SM-1 (coluna `jq` abaixo): um `jq` escrito sob medida costuma ser menor que o CLI nos JSON.
- **ast-grep / ripgrep** — grep estruturado por AST ou texto; saída line-oriented compacta. Referência de formato de saída, não de mecanismo.
- **ctags / universal-ctags** — índice símbolo→localização consultável sem carregar o índice inteiro. Referência conceitual.
- **Aider "repo map"** — resume a estrutura do repositório para caber em poucos tokens de contexto; filosofia equivalente à do `scos-map`.

### Opções de desenho de CLI

Decisão registrada na PRD: específico por fato.


| Opção | Prós | Contras | Decisão |
|---|---|---|---|
| Genérico estilo `jq` (um script, filtro livre sobre qualquer fato) | Máxima flexibilidade; um único ponto de manutenção | Exige que quem chama conheça a estrutura interna de cada JSON; reintroduz parte do custo cognitivo que se quer eliminar | Descartado |
| Específico por tipo de fato (um subcomando por linha da tabela de roteamento) | Mapeia 1:1 com o vocabulário que a skill já usa; saída e flags nascem no formato certo por pergunta | Mais subcomandos para manter conforme novos fatos aparecem | **Escolhido** |
| Mudar o formato do gerador: emitir fatos uma chave por linha (NDJSON ou `chave<TAB>valor`) para `grep`/`awk` já servirem | Custo mínimo; sem CLI novo | Muda formato dos fatos (impacta consumidores e testes do gerador); não dá envelope de confiança nem teto de saída | Não escolhido — usuário preferiu CLI único; reavaliar se o CLI se mostrar caro de manter |
| Híbrido (comandos dedicados para os mais usados + fallback genérico) | Cobre o comum com ergonomia e mantém via de escape | Duas superfícies de API para manter | Não escolhido nesta rodada — considerar se aparecer fato fora do padrão |

### Interface única JSON+TSV

O usuário optou por unificar JSON+TSV num único CLI (`scos-map-query`) em vez de manter o `awk` recomendado hoje para TSV — contra a recomendação inicial de menor escopo (cobrir só o gap dos JSONs e preservar o padrão `awk` existente). FR-2 foi limitado aos três comandos `awk` documentados (mais os filtros de `arestas`) para não virar o filtro genérico descartado acima. Trade-off aceito conscientemente: mais superfície de implementação agora, em troca de uma única interface. Nos TSV o CLI não ganha em bytes sobre o `grep`/`awk`; o ganho esperado é de **acurácia**: envelope de confiança, união de `deps.tsv` com as transitivas, aviso de fato obsoleto. A alternativa de mudar o formato do gerador continua registrada acima como a opção mais barata.

## Hipóteses descartadas ou adiadas

Cada uma traz o motivo e a condição de reabertura.

### Experimento com subagent

Hipótese descartada; amostra única.


Uma consulta equivalente à Q9 (`grep` limitado a 50 linhas, 2.693 bytes) foi executada por um subagent Haiku, que devolveu a saída literal: **34.315 tokens totais medidos**, 4 tool uses, 26 s. A chamada direta no contexto principal custaria cerca de 770 tokens, número **estimado** (2.693 bytes / 3,5), não medido. As duas grandezas não são comparáveis: os 34.315 tokens do subagent incluem prompt de sistema e ferramentas, passam por cache e têm preço de Haiku; os 770 são só contexto principal. A fidelidade foi perfeita (17 linhas idênticas). É uma única execução, sem variância nem preço.

Conclusão que se sustenta sem inventar um ponto de equilíbrio: se o subagent devolve a saída **literal**, as mesmas linhas voltam ao contexto principal e a delegação nunca economiza contexto principal; só um **digest filtrado** poderia, e isso reabre o risco de perder o envelope de confiança. Por isso a hipótese foi descartada do MVP por simplicidade. Reabrir apenas se surgir um digest que preserve o cabeçalho, com teste de fidelidade e amostra maior que um.

### Log de custo (FR-8): por que não há tokens reais

Versão anterior propunha enriquecer o log com o uso de tokens do subagent. Isso é inviável como descrito. O script roda dentro do Bash do subagent e não enxerga o bloco de uso (tokens, tool uses, duração), que só chega ao orquestrador na notificação de conclusão. Persistir esse bloco exigiria uma escrita extra do agente principal a cada chamada. Por isso FR-8 grava só bytes e linhas. Reabrir apenas via spike com critério de saída: existe API/hook que entregue o uso a um script? Sim ou não.

## Inventário do `SKILL.md` atual

Suporte a FR-11: o que sai do `SKILL.md` e para onde vai.

O `SKILL.md` de `scos-map` tem 218 linhas / 10,6KB. Nenhuma seção se perde; cada uma tem destino. Neste inventário, `--help` é o `--help` do `scos-map-query`, por subcomando ou como `--help confianca`.

| Seção atual | Destino |
|---|---|
| Passo 0 – sempre (comando, `status`, ler só o índice, nunca ler todos os fatos) | skill `scos-query` (comando literal e regra de não ler todos os fatos); `status` continua no `scos-map.py`, citado pelo ponteiro da skill `scos-map` |
| Contrato (`schema_versao 2.1`; divergência: reportar e parar) | CLI: checagem em FR-1 |
| Envelope de fato (`confianca`, `base`, `completude`, `desvios`, `derivado_de`) | FR-5 (cabeçalho, `# limitacao:`, marca por `desvios[]`, `--base`) e `--help confianca` |
| Roteamento (12 linhas no `SKILL.md`; 7 no `AGENTS.md`) | skill `scos-query` (única tabela, 13 linhas); uma linha por subcomando (`arestas` com linha própria); `AGENTS.md` só aponta para a skill; testes, higiene de dependências e callgraph apontam para `tests`, `bytecode` e `callgraph` (FR-12 a FR-14) |
| Tabelas (TSV): colunas, 3 comandos `awk` | FR-1 (conteúdo por subcomando), FR-2 (filtros congelados), `--help` por subcomando |
| Tabelas (TSV): `deps.tsv` não tem a lista completa; origem `effective-pom` | `deps` sempre une `deps.tsv` + `_transitivas_comuns.tsv` (FR-1); rodapé com fontes (FR-5); `--help deps` explica `origem` |
| Como interpretar a confiança | `--help confianca` |
| Regra 1: fato `obsoleto` | FR-5 (envelope) |
| Regra 2: `metodos_sem_chamador` não é código morto | FR-14 (`--sem-chamador` sempre com a marca) e `--help callgraph` |
| Regra 3: `nao_aplicavel` é resultado legítimo | FR-5 (estado propagado) e `--help confianca` |
| Regra 4: doc antiga ao lado de código recente | `# aviso:` de `docs` (FR-5) e `--help docs` |
| Regra 5: histórico de arquivo não está no mapa | `# aviso:` de `arquivos` (FR-5) e `--help arquivos` |
| Regra 6: `bytecode_edges.tsv` vazio traz `motivo_vazio` | FR-10 (rodapé com `motivo_vazio` e `diagnostico`) |
| Dependências no `bytecode.json` (quatro baldes) | FR-13 e `--help bytecode` |
| Testes (três coisas que nunca se afirma) | FR-12 (marca `[heuristica]`, mensagem de raízes, `cobertura` sempre exibida) e `--help tests` |
| Documentação (subtipos, frontmatter literal) | `# aviso:` de `docs` (frontmatter literal) e `--help docs` (subtipos) |
| O fato cruzado do workspace (obsoleto, árvore suja, scope `test`, sufixo `(gerenciada)`) | `--help conflitos`; obsoleto e árvore suja pelo envelope (FR-5, FR-3) |
| SNAPSHOT local vs fonte ao lado (`jar_atual` ≠ "contém o último commit") | `--help snapshots`; limitação dita na saída (FR-4) |
| Perguntas abertas ("me explique esse repo") | skill `scos-query`, uma linha: ler `index.json`, `_reactor.json` e o `layout.json` dos maiores módulos |

## Pendências

### Em aberto (trabalho da primeira story)

- Exemplo de saída real (3–5 linhas) por subcomando: produzir na primeira story, junto dos testes golden (FR-1, FR-6).
- Rodar o benchmark contra o CLI real e transformá-lo em teste executável com asserção de conteúdo completa (SM-1, FR-6); incluir fixture de estado misto (Q8) e de `resolvida`+`parcial` (SM-C1).
- Escrever os `--help` que absorvem as seções do inventário (`confianca`, `docs`, `arquivos`, `conflitos`, `snapshots`, `deps`, `tests`, `bytecode`, `callgraph`).
- Gerar um fixture de callgraph disponível com `ferramentas/scos-map/tests/fixtures.py` (o mapa atual tem `estado=indisponivel` em todos os módulos) para testar FR-14, com as colunas do gerador (`de`, `para`, `invoke`, `certeza`); se inviável, FR-14 entrega só o caso `indisponivel` no MVP.
- Escrever o `# aviso:` de uma linha (≤ 100 bytes) de `docs` e de `arquivos`, e confirmar que ele cabe nas metas de SM-1 (a Q5 já o inclui: 661 B, 0,97× do `grep`).
- Editar `scos-map-build` (só a referência na descrição) e `AGENTS.md` (uma linha apontando para a skill, sem tabela) para apontar para `scos-query`.

### Resolvido (registro de decisão)

- `workspace.json` já traz `snapshots_locais` (`ga`, `versao`, `produzido_por`, `jar_em_m2`, `estado`, `acao`, `atraso_dias`), com `confianca=media` e limitações declaradas; FR-4 só lê esse fato. Esse fato não tem `derivado_de`, então o frescor dele vem da comparação de `repo_local.head` com o HEAD atual (FR-4, FR-5).
- `scos-map.py` é stdlib-only. Verificado também que `fact_state` do gerador exige varredura de arquivos e git (`scan_files`, MultiGit) e que `snapshots_locais` não tem `derivado_de`, por isso o CLI não o reutiliza.
