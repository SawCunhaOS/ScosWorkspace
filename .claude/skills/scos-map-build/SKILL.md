---
name: scos-map-build
description: Gera, regenera e mantem o mapa estrutural .scos-map/ dos repositorios SCOS. Use quando nao existe mapa, quando o status acusa fatos obsoletos, quando e preciso escalar para bytecode ou callgraph, ou para diagnosticar por que um fato saiu vazio, indisponivel ou com confianca rebaixada. Para apenas LER o mapa e responder perguntas sobre o codigo, use a skill scos-query.
---

# scos-map-build (geracao e manutencao)

Produz `.scos-map/`. Quem consome o mapa e a skill `scos-map` - esta aqui so
gera e conserta.

## Escolher o comando

`scos-map` abaixo e abreviacao de `python3 ferramentas/scos-map/scos-map.py`,
rodado da raiz do workspace (nao ha binario no PATH).

```bash
scos-map scan .          # UM projeto (pom.xml/package.json na raiz)
scos-map workspace .     # VARIOS projetos lado a lado
scos-map status .        # o que esta obsoleto
```

Na duvida rode `workspace`: se a raiz for um projeto unico, ele degrada para
`scan` sozinho. Cada projeto recebe seu proprio `<projeto>/.scos-map/`, e a
raiz ganha `.scos-map/workspace.json`.

**Se a saida avisar sobre diretorios nao visitados por `--max-depth`**, algum
projeto pode estar fora do mapa. Isso aparece inclusive quando nenhum projeto
e encontrado - confira antes de concluir que o workspace esta vazio.

## Orcamento - nao escale sem necessidade

**Tier 1** (padrao) - segundos, sem build. Layout, config, deps, docs, tests.
Responde a maioria das perguntas de navegacao. E o que se roda no dia a dia.

**Tier 2** (`--tier 2`) - exige `target/classes`. So escale quando a pergunta
for de qualidade arquitetural: ciclos entre pacotes, dependencia usada e nao
declarada, versao de bytecode. O script **nunca compila sozinho**: se o
bytecode estiver ausente ou obsoleto ele pergunta. Nao passe `--compile` sem
que o usuario tenha autorizado.

**Tier 3** (`--tier 3 --callgraph-jar <path>`) - grafo de metodo. So com
pedido explicito; exige o jar do java-callgraph.

## Fazer tudo de uma vez

```bash
scos-map workspace . --all      # tier 3 + compila sem perguntar + maven online
```

Antes de gastar o tempo ele imprime um **plano** com o que vai rodar e o que
falta no ambiente (jdeps, mvn, jar do callgraph). No fim imprime **ACHADOS**.
`--all` liga `--online`: se a rede for restrita, use `--tier 3 --compile`.

## Regenerar so o necessario

O scan reaproveita fatos cujas fontes nao mudaram; `--full` ignora o cache.

```bash
scos-map workspace . --only scos-foundation   # so um projeto
scos-map scan . --full                        # regenera tudo
```

Com `--only`, os demais projetos ficam no indice marcados como cache e o
`workspace.json` continua descrevendo o workspace inteiro. Mas o **fato
cruzado** passa a apontar para o head em cache dos outros: se algum tiver
avancado, o `status` vai acusar `obsoleto` - e a correcao e rodar
`scos-map workspace .` sem `--only`.

## Flags que importam

| flag | quando |
|---|---|
| `--tier 1\|2\|3` | escalar analise (ver orcamento) |
| `--all` | quadro completo, sem perguntas |
| `--full` | ignorar cache e regenerar tudo |
| `--only <a,b>` | reprocessar projetos especificos |
| `--compile` / `--no-compile` | autorizar ou proibir `mvn compile` |
| `--online` | permitir que o Maven baixe artefatos |
| `--max-depth N` | busca por projetos mais profunda (default 3) |
| `--m2-repo <path>` | repositorio local do Maven |
| `--callgraph-jar <path>` | tier 3 |

## Diagnostico

**`bytecode_edges.tsv` vazio.** O fato traz `motivo_vazio`, `diagnostico`
(linhas lidas/casadas/descartadas) e `amostra_saida` com a saida crua do
jdeps. Causas ja vistas: jar multi-release no classpath (o jdeps aborta
inteiro - o script reexecuta com `--multi-release` automaticamente, veja
`jdeps_tentativas`) e modulo de pacote unico.

**`deps` com `confianca: declarada`.** O `mvn` nao rodou. `resolucao_indisponivel`
diz por que. Sem isso nao ha transitivas, e a divisao de baldes do
`bytecode.json` fica pouco confiavel.

**`config` com `confianca: media`.** Falta PyYAML no ambiente
(`pip install pyyaml`). Sem ele, lista, ancora, alias e multi-documento nao
sao interpretados e chaves podem faltar.

**`completude: parcial` citando effective-pom.** O `help:effective-pom` nao
rodou; heranca, properties e BOM importado foram deduzidos do `pom.xml` e
podem divergir do que o Maven resolve.

**Fato `obsoleto` logo apos gerar.** Confira o `mudou`: se citar "bytecode
recompilado", algo regerou codigo (OpenAPI, MapStruct) sem mexer em
`src/main` - isso e detectado de proposito.

**Correcao no gerador nao aparece no mapa.** O scan reaproveita fatos cujas
fontes nao mudaram, inclusive `bytecode`. Depois de mudar o gerador, regenere
com `--full`.

**`bytecode` `nao_aplicavel` em modulo jar.** Modulo sem fonte JVM de
producao, sem `.proto` e sem plugin gerador no pom (so resources/testes), ou
que compilou e nao gerou classe nenhuma.

## Requisitos do ambiente

Nenhuma dependencia pip e obrigatoria. Ganhos por ferramenta presente:

| ferramenta | o que habilita |
|---|---|
| `git` | blob sha confiavel, churn, data de alteracao, frescor cruzado |
| PyYAML | `config` com confianca `alta` |
| `mvn` | transitivas resolvidas, effective-pom, classpath do jdeps |
| JDK (nao so JRE) | `jdeps` para o tier 2 |
| java-callgraph.jar | tier 3 |

Ausencia de qualquer uma degrada o fato correspondente com o motivo escrito -
nunca falha em silencio.

## Suite de testes

```bash
cd ferramentas/scos-map && python3 -m unittest discover -s tests -t tests
```

Sem rede, sem Maven (o helper `rodar` tira o `mvn` do PATH), sem pip. Rode
antes de qualquer mudanca no gerador.

**Ao adicionar um campo novo ao JSON**, o teste deve verificar como o campo se
comporta **na ausencia do dado**, nao so na presenca. A maioria dos erros
deste projeto foi afirmar demais quando o dado nao existia: `alta` sobre
parser fraco, `disponivel` com zero arestas, `fresco` com bytecode velho.

**Ao mudar o formato de saida**, incremente `SCHEMA_VERSAO` e atualize a
skill `scos-map` na mesma mudanca - ela para se ler um schema que nao
conhece. `GERADOR_VERSAO` muda livremente.
