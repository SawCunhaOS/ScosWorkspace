---
title: Scripts de Consulta Rápida para scos-map
status: final
created: 2026-09-14
updated: 2026-10-02
---

# PRD: Scripts de Consulta Rápida para scos-map

## 0. Objetivo do Documento

A arquitetura (camadas, regras de fronteira, contrato de saída) está na spine `_bmad-output/planning-artifacts/architecture/architecture-scos-map-query-2026-10-02/ARCHITECTURE-SPINE.md`; onde ela e este texto divergirem, vale a spine. Esta PRD serve à pessoa que vai implementar (via `bmad-build`) um CLI Python de consulta sobre o `.scos-map/`, e a quem revisar o resultado depois. Ela assume conhecimento prévio do `scos-map` (gerador em `ferramentas/scos-map/scos-map.py`, skills `scos-map`/`scos-map-build`, tabela de roteamento de fatos em `AGENTS.md`) e não repete essa documentação — só referencia. O Glossário (§3) fixa o vocabulário. Os requisitos (§4) têm IDs globais estáveis e ordem temática. As suposições aparecem inline como `[ASSUMPTION]` e estão indexadas em §9. Os cabeçalhos em inglês (Vision, Features, Non-Goals, Consequences) seguem o template de PRD do BMad. O `addendum.md` é **leitura obrigatória** para FR-6, FR-8 e FR-11 (contrato de saída, por que não há tokens reais no log, inventário do que sai do `SKILL.md`) e traz as medições que sustentam SM-1 e a exclusão do subagent. A ordem sugerida de entrega está em §6.1.

## 1. Vision

Hoje, quando o agente (Claude Code) precisa responder uma pergunta de organização de código sobre um dos repositórios do SCOS, a skill `scos-map` o instrui a abrir com `Read` o arquivo JSON do fato relevante (`layout.json`, `config.json`, `_reactor.json` etc.). Esses arquivos JSON são gerados minificados, numa única linha, e podem passar de 100KB. O agente gasta tokens de contexto com o arquivo inteiro para responder uma pergunta pontual. Medição de 2026-10-02 (12 perguntas, `benchmark-baseline.py`): o `Read` do fato custa de 3,5KB a 958KB, enquanto o `grep` equivalente custa de 311 B a 15,6KB — nos fatos em JSON, a inversão se confirma: o `grep` é mais barato que o `Read`.

Esta iniciativa fecha essa lacuna com um CLI único de consulta (`scos-map-query`) entre o agente e o `.scos-map/`: recebe um tipo de fato (layout, config, deps, docs, fronteiras entre módulos, arestas de bytecode, conflitos de versão entre repositórios, frescor de SNAPSHOT, arquivos) e devolve texto compacto, linha-a-linha — nunca o fato bruto inteiro e nunca acima de um teto de linhas e bytes. Toda saída carrega o envelope de confiança (cabeçalho, limitação, marcas por linha e rodapé com a contagem de linhas que casam e as fontes consultadas), definido em FR-5, para que ganhar tokens não custe acurácia.

O resultado esperado: consultar o `scos-map` volta a ser mais barato — em tokens — do que o `Read` do fato, e, nos fatos em JSON, do que o `grep` equivalente. Nos fatos em TSV o CLI empata com o `grep`/`awk` em bytes; o ganho ali é a interface única, o envelope de confiança e a armadilha das dependências transitivas tratada pelo CLI (um `deps.tsv` sozinho nunca prova "o módulo não usa X"). Soma-se a vantagem que só o `scos-map` tem: dependências entre módulos, conflitos de versão cruzados entre os três repositórios e frescor de SNAPSHOT local.

## 2. Target User

### 2.1 Jobs To Be Done

- Como agente, preciso responder "onde mora o quê / quais as dependências e versões / que documentação existe / onde estão as fronteiras entre módulos" gastando o mínimo de tokens de contexto possível — sem abrir JSON/TSV bruto.
- Como agente, preciso saber se a resposta que recebi é um fato atual, obsoleto, parcial ou heurístico, sem rodar um comando de `status` à parte.
- Como agente, preciso que as instruções de consulta custem poucos tokens de contexto: skills curtas, que só carregam o necessário.
- Como agente, preciso de uma consulta que só o `scos-map` resolve — conflito de versão entre os três repositórios, ou se um `-SNAPSHOT` local da Foundation está desatualizado — sem carregar `workspace.json` inteiro.

### 2.2 Non-Users (v1)

Uso interativo humano no terminal **não é o alvo de design** desta v1 — quem chama é o agente, via Bash (decisão confirmada com o usuário). O CLI continua utilizável por um humano (texto plano), mas nenhuma ergonomia extra (cores, paginação, autocomplete) é objetivo desta versão.

### 2.3 Key User Journeys

*Ator único (agente), CLI interno: forma enxuta, uma frase por jornada.*

- **UJ-1.** O agente, no meio de uma story, precisa do entry point e da convenção de pacote de um módulo Maven — chama o subcomando `layout` e recebe algumas linhas em vez do `layout.json` inteiro.
- **UJ-2.** O agente precisa decidir se pode confiar num `-SNAPSHOT` local da Foundation antes de rodar `mvn clean install` na Organization — chama o subcomando `snapshots` e recebe uma linha por repositório produtor: atualizado, desatualizado ou desconhecido.
- **UJ-3.** O agente investiga um conflito de dependência entre Foundation e Flow — chama o subcomando `conflitos` e recebe só as bibliotecas divergentes.
- **UJ-4.** O agente quer saber quem usa uma classe antes de alterá-la — chama o subcomando `arestas` filtrando por destino e recebe as arestas, com a indicação de truncamento no rodapé.
- **UJ-5.** O agente precisa saber se um módulo usa uma biblioteca (ex.: `jjwt`) — chama o subcomando `deps` e recebe a união de diretas e transitivas, sem concluir "não usa" a partir de só uma das tabelas.
- **UJ-6.** O agente quer saber como um módulo é testado e quais dependências ele usa sem declarar — chama os subcomandos `tests` ou `bytecode` e recebe o resumo, com o aviso de que o nome de um teste não prova cobertura.

## 3. Glossário

- **Fato** — unidade de informação extraída e persistida pelo `scos-map-build` em `.scos-map/` (ex.: `layout.json`, `config.json`, `deps.tsv`, `_reactor.json`). É o que o CLI consulta; ele não gera fatos novos.
- **scos-map-query** — nome do produto: o CLI único de consulta desta PRD. O comando que o agente digita é literal: `python3 ferramentas/scos-map/scos-map-query.py <subcomando> ...` (NFR-1). Substitui, para quem chama, o `Read` direto de JSON e o `awk` direto sobre TSV.
- **Tier 1 / 2 / 3** — profundidade de geração de fatos já definida pelo `scos-map-build` (1: scan/workspace sem build; 2: exige bytecode compilado; 3: callgraph). O CLI consome fatos de qualquer tier já gerado; não decide nem dispara geração.
- **Confiança / estado / completude** — campos que o `.scos-map` grava por fato e que o CLI propaga sem remapear: `confianca` (`alta`, `resolvida`, `declarada`, `media`, `parcial`, `heuristica`, `conflito`), `estado` (`fresco`, `obsoleto` — o fonte mudou depois do fato ser gerado —, `ausente`, `indisponivel`, `nao_aplicavel`, `disponivel`) e `completude` (nível e limitações). O CLI acrescenta apenas o valor `desconhecido` a `estado`, quando não consegue verificar o frescor. Detalhe na seção de confiança do `SKILL.md` atual; a legenda passa a sair de `--help confianca` (FR-11).
- **Envelope de confiança** — cabeçalho, linha de limitação, marcas por linha e rodapé que toda saída traz; regra completa em FR-5.
- **Frescor barato** — verificação de `estado` que compara o `head` gravado no fato com o HEAD atual lido de `.git/HEAD`, sem varrer arquivos; conservadora, acusa `obsoleto` por qualquer commit novo; regra completa em FR-5.
- **Workspace vs. projeto vs. módulo** — workspace é o `.scos-map/workspace.json` na raiz do SCOS; projeto é um dos três repositórios (`SawCunhaOS-Foundation`, `SawCunhaOS-Flow`, `sawcunha-open-system-bom`); módulo é um módulo Maven dentro de um projeto.
- **Conflito de versão cruzado** (`conflitos_de_versao_cruzados`) — fato de workspace: mesma biblioteca com versões divergentes declaradas entre os três repositórios.
- **Saída estilo grep** — texto plano, uma unidade de informação por linha, sem embelezar JSON.
- **Benchmark canônico** — conjunto fechado de 12 perguntas de navegação, cada uma com resposta esperada, usado para medir SM-1 e SM-C2 (§7). É um conjunto de regressão, não prova de generalização.
- **Log de custo por chamada** — registro append-only de cada invocação do CLI, com bytes e linhas de saída (FR-8).

## Índice de requisitos

Os IDs são estáveis; a ordem do texto é temática.

| ID | Requisito | Feature |
|---|---|---|
| FR-1 | Consulta por fato via subcomando dedicado | 4.1 CLI único de consulta por fato |
| FR-2 | Filtros e flags | 4.1 CLI único de consulta por fato |
| FR-3 | Conflitos de versão cruzados | 4.2 Consultas cross-repo de workspace |
| FR-4 | Frescor de SNAPSHOT local | 4.2 Consultas cross-repo de workspace |
| FR-5 | Envelope de confiança na saída | 4.3 Sinalização de confiança e frescor |
| FR-6 | Contrato de saída estável | 4.4 Empacotamento para consumo automatizado |
| FR-7 | Roteamento passa a apontar para o CLI primeiro | 4.4 Empacotamento para consumo automatizado |
| FR-8 | Log de custo por chamada | 4.5 Observabilidade de custo por chamada |
| FR-9 | Teto de saída | 4.1 CLI único de consulta por fato |
| FR-10 | Consulta de arestas de bytecode (Tier 2 e 3) | 4.1 CLI único de consulta por fato |
| FR-11 | Skills finas de consulta | 4.6 Skills finas |
| FR-12 | Consulta de testes | 4.1 CLI único de consulta por fato |
| FR-13 | Consulta de dependências no bytecode | 4.1 CLI único de consulta por fato |
| FR-14 | Consulta de callgraph (Tier 3) | 4.1 CLI único de consulta por fato |
| NFR-1 | Dependências, comando e localização | 4.7 Restrições de integração |
| NFR-2 | Latência | 4.7 Restrições de integração |

## 4. Features

### 4.0 Mapa de subcomandos

Os 13 subcomandos do `scos-map-query` e o que cada um devolve sem filtro, na ordem do fato de origem (campos já existentes nos fatos, verificados em 2026-10-02):

| Subcomando | Fato(s) lido(s) | Linha de saída (sem filtro) |
|---|---|---|
| `layout` | `layout.json` | `pacote_base=<pacote>`; depois `caminho \t papel \t arquivos` por área; `entrypoint \t tipo` por entry point |
| `config` | `config.json` | `path \t bytes` por arquivo de configuração (valores nunca aparecem) |
| `deps` | `deps.tsv` + `_transitivas_comuns.tsv` + `deps.json` | `ga \t versão \t scope \t origem`, diretas e transitivas, com marca `[transitiva]` |
| `gerenciadas` | `gerenciadas.tsv` | `ga \t versão \t origem \t scope` |
| `docs` | `docs.json` | `path \t título \t subtipo` |
| `reactor` | `_reactor.json` | `id \t tipo` por módulo; `de -> para (scope)` por aresta interna |
| `arquivos` | `files.tsv` | `path \t kind \t module \t commits_90d` |
| `arestas` | `bytecode_edges.tsv` | `de \t para \t tipo \t origem` (FR-10) |
| `conflitos` | `workspace.json` | `ga \t versão:repositórios \| ...` (FR-3) |
| `snapshots` | `workspace.json` | uma linha por repositório produtor (FR-4) |
| `tests` | `tests.json` + `tests.tsv` | resumo (raízes, arquivos, tipos, frameworks, cobertura) e `path \t tipo \t alvo_heuristico [heuristica]` (FR-12) |
| `bytecode` | `bytecode.json` | resumo por balde de dependência; com `--balde`, `artefato \t referencias` (FR-13) |
| `callgraph` | `callgraph.json` (+ `callgraph_edges.tsv`) | `estado`, `motivo` e `comando_sugerido` quando indisponível; senão `de \t para \t invoke \t certeza` (FR-14) |

### 4.1 CLI único de consulta por fato

**Descrição:** Um único CLI (`scos-map-query`: entry fino `scos-map-query.py` mais o pacote `scos_map_query/`, NFR-1) expõe um subcomando por tipo de fato — mapeando 1:1 a tabela de roteamento da skill `scos-query` — cobrindo fatos em JSON e em TSV, Tier 1 a 3. Realiza UJ-1, UJ-4, UJ-5 e UJ-6.

**Functional Requirements:**

#### FR-1: Consulta por fato via subcomando dedicado
O agente invoca um subcomando correspondente a um tipo de fato, informando projeto e módulo (quando aplicável), e recebe apenas a informação pedida em texto plano.

**Consequences (testable):**
- Cada subcomando aceita projeto (obrigatório) e módulo (quando o fato é por módulo) como argumentos posicionais.
- A saída nunca é o JSON/TSV bruto do fato inteiro — é um recorte textual, uma unidade de informação por linha, limitado pelos tetos de FR-9.
- Cada subcomando devolve por padrão o conteúdo da tabela de §4.0, na ordem do fato de origem.
- Fato não gerado, ou projeto/módulo inexistente: código de saída 3 e uma linha `# erro: <mensagem> | acao: <comando de scos-map-build a rodar>`. Todo erro sai em **stdout** (canal único, passa pelo mesmo renderizador e pelo log). Códigos: 0 ok (inclui zero linhas e `nao_aplicavel`), 1 falha interna (linha `# erro: interno`, sem traceback; o traceback só com `SCOS_MAP_QUERY_DEBUG=1`), 2 uso inválido, 3 fato/projeto/módulo ausente, 4 `schema_versao` com versão maior incompatível.
- A raiz do workspace é o ancestral mais próximo do diretório corrente que contém `.scos-map/workspace.json`; um projeto só existe se listado ali. Sem `workspace.json` o CLI falha (código 3): não há modo de projeto isolado.
- Convenção de interface única: o projeto é argumento posicional obrigatório; o módulo é argumento posicional, obrigatório nos fatos por módulo (o caminho relativo de `index.json`, por exemplo `organization/flow-organization-usecase`, ou o basename quando for único) e proibido nos fatos de projeto e de workspace; todo filtro é uma flag nomeada (tabela de FR-2). Os nomes não mudam entre subcomandos. Única exceção: `conflitos` e `snapshots` leem só `workspace.json` e **não recebem projeto**.
- Formato de saída pensado para LLM ler, não para humano: regular, sem prosa, sem alinhamento nem decoração. Os dados saem em seções; cada seção abre com `## <nome> (<mostradas> de <total>)` seguido de uma coluna por TAB (`\t<coluna>`) e segue com linhas TSV; seção sem colunas usa só o título. Subcomando de seção única usa o mesmo formato. Toda célula passa por `tsv_clean` (tab, CR e LF viram espaço, como no gerador), para nenhuma coluna deslocar. Seção cortada pelo teto continua visível, com a contagem (por exemplo `0 de 40`).
- `schema_versao`, no índice do projeto e em `workspace.json`: versão maior igual à testada (`2.x`) é aceita. Versão menor mais nova que `2.1`: o CLI segue e acrescenta `# aviso: schema <v> mais novo que o testado (2.1)`. Versão maior diferente: erro de uma linha reportando a divergência, sem adivinhar o formato.
- Cada subcomando documenta no **`--help`** (não na skill) o formato de saída e um exemplo real de 3–5 linhas; o exemplo é também caso de teste de aceitação.

*Conteúdo padrão de cada subcomando: tabela de §4.0.*

**Out of Scope:**
- Gerar ou atualizar fatos — papel exclusivo do `scos-map-build`. O CLI nunca compila e nunca escreve em `.scos-map/`; a única escrita permitida é o log de FR-8, fora dessa pasta.

#### FR-2: Filtros e flags
O agente restringe a saída por flags nomeadas. As três consultas `awk` documentadas hoje formam a **suíte de compatibilidade congelada**: reescrever o `SKILL.md` (FR-7, FR-11) não a altera. As demais flags são as da tabela única abaixo.

| Consulta `awk` documentada (congelada) | Equivalente no CLI |
|---|---|
| `awk -F'\t' '$5=="organization" && $6=="codigo"' files.tsv` | `arquivos <projeto> --em-modulo organization --kind codigo` |
| `awk -F'\t' '$10>5' files.tsv` (arquivos quentes) | `arquivos <projeto> --commits-90d-min 6` |
| `awk -F'\t' '$2 ~ /jjwt/ {print FILENAME, $2, $3}' facts/*/deps.tsv` | `deps <projeto> --todos-modulos --ga jjwt` |

**Tabela única de flags.** Cada linha das duas tabelas é um caso golden. `--em-modulo` filtra a coluna `module` de `files.tsv`; não escolhe o módulo do fato.

| Flag | Subcomando(s) | Efeito |
|---|---|---|
| `--limit N`, `--bytes N`, `--all` | todos | sobrescreve os tetos de FR-9 |
| `--base` | todos | acrescenta a `base` do fato (FR-5) |
| `--em-modulo`, `--kind`, `--commits-90d-min` | `arquivos` | filtros por coluna de `files.tsv` |
| `--ga` | `deps`, `gerenciadas` | filtra por coordenada (substring) |
| `--todos-modulos` | `deps` | percorre todos os módulos do projeto |
| `--prefixo` | `config`, `docs` | filtra por prefixo de `path` |
| `--texto` | `docs` | filtra por termo em `path` ou título (sem diferenciar maiúsculas) |
| `--de`, `--para` | `arestas`, `callgraph` | origem e destino (classe ou prefixo) |
| `--pacote` | `arestas` | pacote (prefixo) |
| `--arquivos`, `--alvo <classe>` | `tests` | lista `tests.tsv`; restringe ao alvo (`alvo_heuristico`) |
| `--balde <nome>` | `bytecode` | escolhe o balde de dependências |
| `--entrypoints`, `--lacunas`, `--sem-chamador` | `callgraph` | seleções do fato |
| `--detalhe` | `snapshots` | uma linha por coordenada |

**Consequences (testable):**
- `--commits-90d-min` aceita comparação numérica.
- Filtro inválido (coluna/caminho inexistente) retorna erro de uma linha, não um traceback.
- Filtro sem resultado segue FR-5: cabeçalho, zero linhas e rodapé com as fontes consultadas.
- O rodapé de truncamento (FR-9) sugere sempre uma flag desta tabela aplicável ao subcomando.
- Os 12 casos do benchmark (SM-1) usam só flags desta tabela: Q2 usa `config --prefixo`, Q4 `gerenciadas --ga`, Q5 `docs --texto`.

`[NOTE FOR PM]` O conjunto de flags é fechado: não vira filtro genérico estilo jq, descartado no addendum. A alternativa mais barata não escolhida (gerador emitir fatos uma chave por linha) está no addendum.

#### FR-9: Teto de saída
Nenhuma invocação devolve mais linhas ou bytes que os tetos padrão, a menos que o agente peça explicitamente.

**Consequences (testable):**
- Os dois tetos valem juntos: 50 linhas e 6.000 bytes de dados (cabeçalho, linha de limitação, títulos de seção e rodapé não contam); o primeiro a estourar trunca a saída. Linha individual truncada em 240 caracteres com `…`.
- As linhas que sobrevivem são as primeiras na ordem do fato de origem (estável, sem reordenar). O rodapé de FR-5 informa `N de M linhas casam` quando há omissão, e sugere uma flag da tabela de FR-2 que refina a consulta.
- `--limit N`, `--bytes N` e `--all` sobrescrevem os tetos de forma explícita.
- Teste: nenhuma invocação sem `--all` excede os tetos, inclusive `arquivos` sem filtro e uma consulta quente de `arestas` (107 linhas casam na Q10 do benchmark).
- Medido: só a Q10 do benchmark passa dos tetos; a economia nessa pergunta vem do truncamento (números no addendum).

#### FR-10: Consulta de arestas de bytecode (Tier 2 e 3)
O agente consulta as arestas de bytecode/callgraph de um módulo (`bytecode_edges.tsv`, os maiores fatos do mapa), filtrando por origem, destino ou pacote. Realiza UJ-4.

**Consequences (testable):**
- Subcomando `arestas <projeto> <módulo>` aceita os filtros `--de`, `--para` e `--pacote` de FR-2 e respeita FR-5 e FR-9.
- Módulo sem `bytecode_edges.tsv` gerado: erro de FR-1 indicando o comando de build com `--tier 2`/`--tier 3`; o CLI nunca dispara essa geração.
- Quando o arquivo existe mas está vazio, o rodapé traz `motivo_vazio` e `diagnostico` do fato: arestas vazias não são silêncio e não provam que o módulo não tem dependências.

#### FR-12: Consulta de testes
O agente consulta os testes de um módulo: quantos, de que tipo, quais frameworks e se há regras ArchUnit.

**Consequences (testable):**
- Sem filtro, devolve o resumo de `tests.json` (raízes varridas, arquivos, tipos, frameworks com `origem` `declarada` ou `inferida`, `cobertura`); com `--arquivos`, lê `tests.tsv` (`path`, `tipo`, `alvo_heuristico`, `linhas`, `commits_90d`).
- `alvo_heuristico` sai sempre com a marca `[heuristica]`: é casamento de nome. O `--help tests` explica que a saída permite afirmar "existe um teste chamado XTest", nunca "X está testada".
- Zero arquivos de teste para um `--alvo` produz "nenhum arquivo de teste identificado nas raízes analisadas: <raízes>", citando as `raizes`; nunca "não existe teste".
- A `cobertura` é sempre exibida com o `estado` do fato (hoje `nao_analisado`); ausência de teste no mapa não é ausência de cobertura.

#### FR-13: Consulta de dependências no bytecode
O agente consulta a higiene de dependências de um módulo a partir de `bytecode.json` (Tier 2).

**Consequences (testable):**
- Sem filtro, devolve o resumo: contagem por balde (`deps_usadas_ausentes_do_pom`, `deps_usadas_via_transitiva`, `deps_declaradas_sem_uso`, `deps_ignoradas_na_analise`), `frescor` e `transitivas_resolvidas`. Com `--balde <nome>`, uma linha por item (`artefato \t referencias`).
- Só `deps_usadas_ausentes_do_pom` é apresentado como risco imediato. Itens com `provavel_falso_positivo: true` saem marcados `[provavel_falso_positivo]` e `deps_ignoradas_na_analise` nunca aparece como problema. O `--help bytecode` explica as duas regras.
- Se `transitivas_resolvidas` for falso, o envelope traz `# limitacao:` dizendo que a divisão entre os dois primeiros baldes não é confiável.
- Os baldes `deps_usadas_ausentes_do_pom` e `deps_declaradas_sem_uso` são condicionais: ausente com `transitivas_resolvidas` verdadeiro significa "nada achado"; ausente com `transitivas_resolvidas` falso significa "não calculado", e a saída diz isso em vez de "0". `usadas_fora_do_jdeps` ausente não prova falta de uso (jar fora do `~/.m2`).
- O `estado` do cabeçalho considera o `frescor` próprio do fato (`compilado_em`), segundo a precedência de FR-5: um bytecode compilado antes de mudanças nas fontes sai `obsoleto`.

#### FR-14: Consulta de callgraph (Tier 3)
O agente consulta o grafo de chamadas de métodos de um módulo quando ele foi gerado.

**Consequences (testable):**
- Fato com `estado` diferente de `disponivel` (ex.: `java-callgraph.jar nao encontrado`): saída com o cabeçalho de FR-5, o `motivo` e o `comando_sugerido` do fato; nunca saída vazia.
- Fato disponível: sem filtro, resumo (`arestas_total`, `arestas_ambiguas`, `entrypoints`); com filtros `--de`, `--para` ou `--entrypoints`, linhas de `callgraph_edges.tsv` (colunas `de`, `para`, `invoke`, `certeza`, as do gerador); `--lacunas` lista `lacunas_conhecidas`. A advertência do fato ("proxies, reflexão e implementações geradas em runtime não aparecem") vai sempre na linha `# limitacao:`, pois a `completude` é parcial.
- `--sem-chamador` lista `metodos_sem_chamador`, sempre com a marca de que não é lista de código morto: endpoints HTTP, `@Scheduled` e `@EventListener` nunca têm chamador no bytecode.
- Neste mapa o `callgraph` está `indisponivel` em todos os módulos (jar não instalado) e não existe `callgraph_edges.tsv` real.
- O caso disponível é testado com um fixture produzido por `ferramentas/scos-map/tests/fixtures.py`, com as colunas do gerador. Se essa produção se mostrar inviável na story, FR-14 entrega só o caso `indisponivel` no MVP e as arestas ficam para quando houver dado real.

#### FR-3: Conflitos de versão cruzados
O agente consulta, num único comando, quais bibliotecas têm versões divergentes entre os três repositórios, com uma linha por biblioteca em conflito (nome, versões e repositórios onde cada versão aparece).

**Consequences (testable):**
- Equivalente em conteúdo a `conflitos_de_versao_cruzados` de `workspace.json`, sem abrir esse arquivo.
- Biblioteca sem conflito não aparece. Zero conflitos produz o cabeçalho de FR-5 (ex.: `# confianca=resolvida estado=obsoleto completude=parcial gerado=<ts>` — hoje `obsoleto`, pois os três `head` gravados já diferem dos atuais —, linha de limitação) e o rodapé `# 0 de 0 linhas casam | fontes: workspace.json` — nunca saída vazia.

#### FR-4: Frescor de SNAPSHOT local
O agente checa, num único comando, se os `-SNAPSHOT` do `~/.m2` local estão atrás do repositório produtor, lendo o fato `snapshots_locais` de `workspace.json`.

**Consequences (testable):**
- Por padrão, uma linha por repositório produtor: `produtor \t N jar(s) \t estados \t max_atraso \t ação recomendada`. `--detalhe` lista uma linha por coordenada (`ga`, versão, `estado` do fato — `jar_atual`, `jar_desatualizado` ou `jar_ausente` —, `acao`, `atraso_dias`). O agrupamento evita 10 linhas repetidas quando todo o repositório produtor mudou.
- `estado` do próprio fato: o `repo_local.head` gravado é comparado com o HEAD atual do repositório produtor pela regra do frescor barato (FR-5): diferente → `obsoleto`; igual com mapa gerado sujo → `desconhecido`; HEAD ilegível → `desconhecido`.
- O CLI só lê o fato, `.git/HEAD` e, opcionalmente, conta commits (FR-5): não acessa `~/.m2` nem varre arquivos.
- A limitação aparece **na saída**, em `# limitacao:`: o mtime do jar não prova o conteúdo; um commit só de documentação também marca atraso; alterações não commitadas ou em stash não são consideradas.
- Teste: um fixture com `snapshots_locais` cujo `head` difere do HEAD atual nunca sai com `estado=fresco`.

### 4.3 Sinalização de confiança e frescor

**Descrição:** Requisito transversal às features 4.1 e 4.2: nenhuma saída compacta pode custar a perda do sinal de confiança do `.scos-map`.

**Functional Requirements:**

#### FR-5: Envelope de confiança na saída
Toda saída de qualquer subcomando carrega o estado do fato de origem, usando o vocabulário que o próprio `.scos-map` grava, e um rodapé de contagem.

**Consequences (testable):**

*Cabeçalho*
- Primeira linha de toda saída: `# confianca=<valor> estado=<valor> [completude=<nível>] gerado=<timestamp>`. `confianca` e `completude` vêm do fato. `gerado` vem do `gerado_em` do `index.json` do projeto (ou de `workspace.json` para fatos de workspace).
- Fato sem `confianca` é fato sem dado: o cabeçalho traz `confianca=-` e o `estado` (`ausente`, `indisponivel`, `nao_aplicavel`) diz por quê; `nao_aplicavel` é resultado legítimo, não erro.
- `--base` acrescenta a `base` do fato (de onde o dado saiu), para nunca afirmar algo cuja base não esteja declarada.
- Quando o `git` está no PATH, o cabeçalho acrescenta `commits_desde_o_mapa=N`, de um único `git rev-list --count <head>..HEAD` por repositório (única chamada ao `git`; só leitura), para o agente julgar se a mudança é relevante; sem `git`, o campo é omitido e o frescor continua pela leitura de `.git/HEAD`.
- Erros também emitem o cabeçalho quando o fato existe.

*Precedência de `estado`*
- `estado` segue uma precedência única, da mais forte para a mais fraca:
  1. `estado` de disponibilidade que impede o uso — `ausente`, `indisponivel`, `nao_aplicavel` — vale como está.
  2. `frescor.estado` do próprio fato, quando existe (ex.: `bytecode.json` com `disponivel` e `frescor: fresco/obsoleto`).
  3. Frescor barato pelo `head` gravado (`git.head` do `index.json`; `derivado_de[<repo>].head` ou `repo_local.head` em `workspace.json`) contra o HEAD atual lido de `.git/HEAD`: diferente → `obsoleto`; igual com `git.dirty` verdadeiro na geração → `desconhecido`; igual e limpo → `fresco`; ilegível → `desconhecido`.
  - Casos especiais: um fato com vários `head` (o de conflitos tem três) usa o pior caso; `disponivel` sem `frescor` nem `head` comparável resulta em `desconhecido`.
- O CLI **não** reutiliza `fact_state` do gerador, que exige varrer arquivos e usar o git, e não importa `scos-map.py`.

*Vários fatos*
- Quando o subcomando lê mais de um fato (ex.: `deps`), o cabeçalho mostra o **pior caso** entre eles — `confianca` da pior para a melhor: `conflito`, `heuristica`, `parcial`, `media`, `declarada`, `resolvida`, `alta`; `estado`: `obsoleto`, `desconhecido`, `ausente`, `indisponivel`, `nao_aplicavel`, `disponivel`, `fresco` — e uma linha `# fontes: <fato>(<confianca>,<estado>) ...` lista cada um. Fato `indisponivel` aparece no `# fontes:` com o `motivo`.

*Linhas, limitação, aviso e rodapé*
- Linhas individuais só repetem a marca quando diferem do cabeçalho: uma entrada `heuristica` num fato de `confianca=alta`, ou um item listado em `desvios[]` do fato (que declara a própria `confianca` e o motivo), termina em `[<confianca>]`.
- Quando `completude` é `parcial`, segue uma linha `# limitacao: <limitações>`, truncada por cláusula (nunca no meio de uma) e com `…` se alguma foi omitida. Mapa gerado com árvore suja acrescenta a cláusula "mapa gerado com alterações não commitadas".
- Subcomandos cujo fato tem regra de leitura própria emitem ainda uma linha `# aviso:` de no máximo 100 bytes (ex.: `docs`: "frontmatter lido literalmente; sem status não é rascunho"; `arquivos`: "histórico de arquivo não está no mapa"; `tests`, `bytecode`, `callgraph`: FR-12 a FR-14). A regra completa vive no `--help` do subcomando; o aviso evita que ela dependa de o agente pedir ajuda.
- Última linha de toda saída: `# <n> de <M> linhas casam | fontes: <arquivos consultados>`, mesmo com zero linhas, para que "nenhuma linha" nunca seja lido como "não usa" sem saber o que foi consultado.

*Limitação aceita*
- O frescor barato acusa `obsoleto` por qualquer commit novo, inclusive só de documentação, e não detecta alterações não commitadas feitas depois da geração; `commits_desde_o_mapa` ajuda a julgar. Evidência e testes do protótipo `prototipo-frescor.py` estão no addendum.

### 4.4 Empacotamento para consumo automatizado

**Descrição:** Requisitos que tornam o CLI consumível de forma confiável por um agente sem exigir conhecimento da estrutura interna dos fatos.

**Functional Requirements:**

#### FR-6: Contrato de saída estável
O CLI documenta um formato de saída estável por subcomando (colunas/linhas independentes de mudanças internas na estrutura dos fatos), para que automações dependam dele sem reparsing ad-hoc.

**Consequences (testable):**
- O formato de cada subcomando está documentado no `--help` (FR-1), com o exemplo real.
- Cada subcomando tem teste golden em `ferramentas/scos-map/tests/` que falha em qualquer mudança de formato; alterar o formato exige atualizar o golden e o `--help` no mesmo commit.
- O benchmark canônico vira teste executável na mesma suíte assim que o CLI existir, com asserção de conteúdo contra a resposta esperada de cada pergunta (SM-1).
- Os goldens usam os mapas sintéticos de `ferramentas/scos-map/tests/fixtures.py`, sem fixtures novos.
- Fronteira de camadas: as funções de `comandos/` não fazem E/S. Um teste por AST falha se algum módulo de `comandos/` referenciar `open`, `print`, `sys.stdout` ou `os.environ`; só `fatos.py` abre arquivo e só `render.py` imprime.
- A versão de schema testada (`2.1`) é uma constante única, com teste; qualquer evolução do schema do gerador obriga a revisar leitores, goldens e `--help`.

#### FR-7: Roteamento passa a apontar para o CLI primeiro
A tabela de roteamento da skill `scos-query` (o `AGENTS.md` só aponta para ela) indica o subcomando correspondente como primeira opção; `Read` do fato bruto vira fallback explícito.

**Consequences (testable):**
- Cada linha da tabela de roteamento tem um subcomando equivalente. Exceção só vale se listada com motivo na própria tabela; o teste falha se houver linha sem subcomando e sem exceção motivada.
- Hoje o `SKILL.md` tem 12 linhas de roteamento e o `AGENTS.md` só 7. O MVP unifica numa **única tabela de 13 linhas, só na skill `scos-query`**, uma por subcomando de fato (`arestas` ganha linha própria, separada de `bytecode`). O `AGENTS.md` perde a tabela e ganha uma linha apontando para a skill. A fonte única é a constante `PERGUNTA` de cada módulo de `comandos/`, que também alimenta o `--help` geral. Teste: a tabela da skill tem exatamente os subcomandos e as `PERGUNTA` do registro; divergência falha a suíte. Se surgir um fato novo sem subcomando, entra como exceção motivada na tabela.
- Fallback para TSV: o que o CLI não cobrir se consulta com `grep`/`awk` usando as colunas documentadas no `--help`, nunca com `Read` do TSV inteiro; `Read` do fato bruto é fallback só para JSON.
- A tabela de roteamento da skill `scos-query` (única do repositório) tem uma linha por subcomando (nome → pergunta que responde, 13 linhas) e um aviso do tamanho dos fatos grandes (ex.: `config.json` ≈142KB) para desestimular `Read` direto. A adesão do agente só é verificável por amostragem de transcrições (SM-2).

### 4.5 Observabilidade de custo por chamada

**Descrição:** Registrar o custo de cada chamada para que a economia prometida seja verificável ao longo do tempo (pedido do usuário). Complementa o benchmark de SM-1.

**Functional Requirements:**

#### FR-8: Log de custo por chamada
Toda invocação grava um registro append-only com timestamp, subcomando, projeto/módulo, bytes e linhas de saída.

**Consequences (testable):**
- O custo registrado é só de bytes e linhas de saída; tokens reais estão fora desta PRD (ver addendum).
- O arquivo é `.scos-map-query.log` no diretório ancestral mais próximo do diretório corrente que contém `.scos-map/workspace.json`, fora de `.scos-map/` e listado no `.gitignore`; a variável de ambiente `SCOS_MAP_QUERY_LOG` o sobrescreve. Funciona do mesmo jeito quando o agente roda de dentro de um dos repositórios.
- Cada registro é gravado com uma única chamada de escrita em modo append, para que execuções paralelas não intercalem linhas.
- Sem rotação nem limite na v1; o consumidor é a leitura manual até existir o comando `gain` (§6.2).
- Cada registro traz também o código de saída e o `schema_versao` lido, para auditar erros.
- Falha ao escrever o log nunca impede a consulta de responder. Sem `.scos-map/workspace.json` em qualquer ancestral o CLI nem chega a consultar: falha com código 3 (FR-1) e não grava log.

### 4.6 Skills finas

**Descrição:** Pedido do usuário: as instruções de consulta devem ser pequenas e diretas, para economizar tokens. A chamada ao CLI é sempre direta pelo Bash.

**Functional Requirements:**

#### FR-11: Skills finas de consulta
Existe uma skill nova, `scos-query`, curta, que ensina o agente a chamar `scos-map-query`, e a skill `scos-map` (hoje com 218 linhas / 10,6KB) é reduzida a um ponteiro curto para ela.

**Consequences (testable):**
- Para cada uma das duas skills, em `.claude/skills/scos-query/SKILL.md` e `.claude/skills/scos-map/SKILL.md`: descrição de no máximo 300 caracteres (hoje ≈ 380; basta para listar os gatilhos de disparo) e corpo, sem o frontmatter, de no máximo 30 linhas e 2.000 caracteres. Teste: contagem de linhas e de caracteres.
- O `--help` de cada subcomando tem no máximo 1.500 bytes e `--help confianca` no máximo 2.500, para a documentação não anular a economia (SM-C2).
- A skill `scos-query` contém só: a regra de chamar o CLI direto, o comando literal (NFR-1), a tabela de roteamento de FR-7 e o aviso de `--all`. Formato, exemplos e legenda de confiança não moram na skill: saem de `--help` por subcomando e de `--help confianca`.
- Nenhum conteúdo do `SKILL.md` atual se perde: o inventário no `addendum.md` lista cada seção e o destino dela (CLI, `--help`, `scos-query`, `scos-map-build` ou descartada com motivo), e cada regra da seção "Regras que evitam conclusão errada" tem destino registrado. Teste: o inventário cobre todas as seções do `SKILL.md` atual.
- A armadilha das transitivas (um `deps.tsv` sozinho não prova que o módulo não usa X) deixa de depender de texto de skill: o subcomando `deps` sempre une as tabelas (FR-1) e o rodapé lista as fontes (FR-5).
- As regras de interpretação de testes, baldes de `bytecode.json` e `callgraph.json` viram comportamento do CLI e `--help` (FR-12, FR-13, FR-14), não texto de skill.
- A skill `scos-map-build` não é alterada, exceto a referência na descrição, que passa a apontar para `scos-query` como skill de leitura (idem `AGENTS.md`).
- Teste de destino das regras: cada regra do inventário aparece na saída do subcomando (linha `# aviso:` ou limitação, FR-5, FR-12 a FR-14) ou em uma das duas skills. Para as regras de alto risco (as que evitam concluir "não usa X", "está testada" ou "está obsoleto"), constar só no `--help` não basta.

### 4.7 Restrições de integração

#### NFR-1: Dependências, comando e localização
O CLI usa apenas a biblioteca padrão e exige o Python 3.10 como versão mínima (como o gerador `scos-map.py`, verificado), sem usar nada que dependa de versão mais nova, embora a máquina local tenha 3.14, vive em `ferramentas/scos-map/`, como um entry fino `scos-map-query.py` mais o pacote `scos_map_query/` (`modelo.py`, `fatos.py`, `render.py`, `cli.py` e um módulo por subcomando em `comandos/`), e é invocado pelo comando literal `python3 ferramentas/scos-map/scos-map-query.py <subcomando> ...`, de modo que uma única regra de allowlist de Bash cubra todas as consultas. Não importa `scos-map.py` (nome com hífen e cerca de 3,9 mil linhas): duplica só o mínimo necessário (leitura de `.git/HEAD`).

#### NFR-2: Latência
Cada invocação responde em no máximo 300 ms numa máquina local. Verificado em protótipo: processo completo com `layout.json` de 54KB ≈ 10 ms; varredura do maior fato (`bytecode_edges.tsv` de 958KB) ≈ 1 ms de CPU; leitura de `.git/HEAD` < 0,1 ms. O teto de 300 ms tem folga de 30×.

## 5. Non-Goals (Explicit)

- Não delega a consulta a subagent.
  - *Decisão:* a hipótese foi descartada do MVP.
  - *Evidência:* amostra única, com 34.315 tokens totais de um subagent Haiku contra ~770 tokens estimados por bytes/3,5 para a chamada direta (grandezas diferentes). Como o subagent devolveria a saída literal, o contexto principal receberia as mesmas linhas; só um digest filtrado poderia economizar, e isso arrisca perder o envelope.
  - *Reabrir:* apenas se surgir um digest que preserve o cabeçalho, com teste de fidelidade.
- Não substitui `scos-map-build` nem gera/escala tiers — só lê fatos já gerados (FR-10 consulta bytecode já gerado, não o gera).
- Não substitui `grep`/`Explore` para busca em código-fonte bruto.
- Não é ferramenta de análise de qualidade arquitetural (ciclos, dependência não declarada).
- Não adiciona novos tipos de fato ao `scos-map-build`.

## 6. MVP Scope

### 6.1 In Scope

- CLI `scos-map-query` com os 13 subcomandos do mapa de §4.0, JSON e TSV, Tier 1 a 3 (FR-1, FR-2, FR-10, FR-12, FR-13, FR-14).
- Tetos de saída (FR-9) e envelope de confiança com rodapé (FR-5) em toda saída.
- Conflitos cruzados (FR-3) e frescor de SNAPSHOT (FR-4).
- Contrato de saída com testes golden e benchmark executável (FR-6) e roteamento (FR-7).
- Skills finas `scos-query` e `scos-map` reduzida, com inventário do que sai do `SKILL.md` (FR-11).
- Log de bytes/linhas por chamada (FR-8) e restrições de integração (NFR-1, NFR-2).

**Ordem sugerida de entrega** (dependências, não escopo): primeiro FR-1, FR-2, FR-3, FR-4, FR-5, FR-9 e FR-11, que sustentam SM-1; depois FR-10, FR-12, FR-13 e FR-14, independentes entre si por subcomando; FR-6, FR-7 e FR-8 acompanham cada fatia.

### 6.2 Out of Scope for MVP

- Ergonomia de terminal para uso humano — `[NOTE FOR PM]` revisitar se o uso humano direto crescer.
- Tokens reais por chamada no log — o script não enxerga o uso de tokens de um subagent; só reentra se um spike achar API/hook que o entregue.
- Comando de relatório agregado sobre o log (`gain`) — `[NOTE FOR PM]` revisitar quando o log acumular dados; FR-8 existe por pedido do usuário e hoje não tem leitor automático.
- Novos tipos de fato não gerados hoje pelo `scos-map-build`.

`[NOTE FOR PM]` Nos TSV o ganho do CLI é de acurácia, não de bytes (ver §1). FR-10 está no MVP por decisão do usuário (Tier 1 a 3 completo), e SM-1 mede bytes apenas como referência mínima.

## 7. Success Metrics

**Primary**
- **SM-1**: Bytes de saída por pergunta do benchmark canônico (`benchmark-baseline.py`, 12 perguntas) em quatro caminhos: `Read` do fato, `grep` equivalente, `jq` sob medida e `scos-map-query`. Bytes são proxy de tokens (≈ bytes/3,5, estimativa; JSON minificado tokeniza pior), e a dor declarada é em tokens: a medição em tokens reais fica fora do MVP (FR-8, addendum). O benchmark vira teste executável com o CLI real (FR-6): cada resposta é conferida por contagem independente de linhas (`grep -c`/`jq length`) e pelo conteúdo esperado, não só por uma substring. Metas:
  - **Contra o `grep`, JSON**: mediana de CLI/`grep` ≤ 1,0× e nenhuma pergunta acima de 1,6×.
  - **Contra o `grep`, TSV**: CLI ≤ máx(`grep` + 64 bytes, 1,1 × `grep`).
  - **Contra o `Read`**: CLI ≤ 10% dos bytes do `Read` do fato. Esse `Read` é integral; o limite de tamanho da própria ferramenta não foi verificado, então o 10% é referência informativa e a meta decisiva é a do `grep`.
  - O `jq` sob medida não é meta (comparação no addendum).

  **Linha de base** (estimativa com proxy do CLI, o melhor caso; detalhe no addendum): 12 de 12 ≤ 10% do `Read`; JSON com mediana de 0,94× do `grep`; TSV de 0,39× a 1,03×. `[ASSUMPTION: o CLI real fica dentro da margem do proxy; revisar rodando o benchmark contra o CLI na primeira story]` Valida FR-1, FR-5, FR-9, FR-6.

**Secondary**
- **SM-2**: Cobertura de roteamento: toda linha da tabela da skill `scos-query` tem subcomando (checagem estática de FR-7) e, em verificação feita por quem revisa (não por quem implementou) sobre 20 perguntas de navegação em 5 sessões após a adoção, ≥ 90% foram respondidas sem `Read` de fato bruto. A linha de base é contada retroativamente nas últimas 5 sessões anteriores à adoção, pelo mesmo critério. Valida FR-1, FR-2, FR-7.

**Counter-metrics (não otimizar)**
- **SM-C1**: Saída sem o envelope correspondente ao fato (cabeçalho ausente ou divergente do que o fato grava) quando o fato tem `estado` diferente de `fresco`, `confianca` diferente de `alta` ou `completude` presente. Meta: zero, verificado por testes de contrato com fixtures de fato `obsoleto`, de `resolvida`+`parcial` (como o fato de conflitos, com árvore suja) e de HEAD ilegível (`desconhecido`). Contrabalança SM-1.
- **SM-C2**: Bytes totais de uma sessão de 5 perguntas seguidas do benchmark — Q1, Q5, Q6, Q7 e Q9 —, com skill carregada uma vez, `--help` dos subcomandos usados (dentro dos tetos de FR-11) e todas as saídas. Meta: ≤ 10% do total da mesma sessão via `Read`, incluindo as 10,6KB do `SKILL.md` antigo no lado do `Read`. O total contra o `grep` é registrado como informação, sem meta: em sessões curtas o custo fixo da skill domina, e a promessa de ser mais barato que o `grep` vale por consulta, não por sessão.

## 8. Open Questions

Nenhuma.

## 9. Assumptions Index

- §7 SM-1 — o CLI real fica dentro da margem do proxy do benchmark. Dono: quem implementa a story do CLI. Revisar: rodando o benchmark contra o CLI; se estourar, recalibrar a meta ou enxugar o envelope. É a única suposição que só se fecha com o CLI pronto.

Fechadas por verificação em 2026-10-02 (ver `addendum.md`): o frescor barato (FR-5) e a latência (NFR-2).

---

*Ver também `addendum.md` para: números de tamanho dos fatos (com comandos reproduzíveis), prior art, opções de desenho de CLI e da alternativa de formato do gerador, medições do benchmark e do experimento com subagent, e o inventário do `SKILL.md`.*
