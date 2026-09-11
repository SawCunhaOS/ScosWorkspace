---
name: scos-map
description: Consulta a estrutura dos repositorios do SCOS (SawCunhaOS) - um projeto ou o workspace inteiro com varios projetos lado a lado. Responde onde ficam arquivos, configuracoes, dependencias e versoes, como os modulos se relacionam, que testes existem e se um SNAPSHOT local esta atrasado. Use quando a pergunta for sobre a organizacao do codigo e nao sobre o conteudo de um arquivo especifico ja conhecido.
---

# scos-map (consulta)

Le o mapa em `.scos-map/`. **E um indice, nao um substituto do codigo**: diz
onde achar, com que confianca e quao fresco esta cada fato. Para ler
conteudo, abra o arquivo pelo caminho que o indice deu.

Para **gerar ou regenerar** o mapa, use a skill `scos-map-build`.

## Passo 0 - sempre

`scos-map` e abreviacao de `python3 ferramentas/scos-map/scos-map.py`, rodado da
raiz do workspace (nao ha binario no PATH).

```bash
scos-map status .          # ja existe mapa? o que esta obsoleto?
```

- Nao existe mapa, ou o `status` diz que falta: peca a skill `scos-map-build`.
- Existe: leia **apenas** `.scos-map/index.json` (projeto) ou
  `.scos-map/workspace.json` (varios projetos lado a lado).

Escolha os fatos que a pergunta exige e abra so aqueles. Nunca leia todos os
arquivos de fato "para ter o quadro completo" - o mapa foi desenhado para ser
lido em pedacos.

## Contrato

Esta skill le `schema_versao: "2.1"`. Se o indice trouxer outro schema,
**reporte a divergencia e pare** - nao tente adivinhar o formato.
`gerador_versao` e implementacao e pode mudar sem afetar a leitura.

`tier_executado` e o maior tier que produziu dado; `tier_pedido` e o que foi
pedido. Tier 3 pedido sem o jar do callgraph fica `tier_executado: 2`.

## Envelope de fato

Todo fato declara a confianca **do caso comum** uma vez, no topo:

- `confianca` - vale para o fato inteiro. Ausente = fato SEM DADO; quem
  informa e `estado` (`ausente`, `indisponivel`, `nao_aplicavel`).
- `base` - de onde o dado saiu literalmente (`PyYAML safe_load`,
  `mvn help:effective-pom`, `jdeps -verbose`...). **Nunca afirme algo cuja
  base nao esteja aqui.**
- `completude.nivel` - `total` ou `parcial`; se parcial, `limitacoes[]` diz o
  que ficou de fora. Ausente = total.
- `desvios[]` - itens que NAO seguem a confianca do envelope, cada um com a
  sua e o motivo. Item que nao esta em `desvios` herda o envelope.
- `derivado_de` - path -> sha (12) das fontes do fato.

`confianca`, `frescor` e `completude` sao independentes: um fato pode ser
`alta` + `obsoleto` + `parcial` ao mesmo tempo. `estado` no indice e rollup
recomputado do disco, nunca verdade gravada.

## Roteamento - qual fato responde o que

| A pergunta e sobre | Abra |
|---|---|
| onde mora o que, convencao de pacote, pontos de entrada | `facts/<mod>/layout.json` |
| onde ficam as configs, quais chaves e perfis existem | `facts/<mod>/config.json` |
| dependencias, versoes, divergencia declarada x resolvida | `facts/<mod>/deps.json` + `deps.tsv` |
| versoes que um BOM fixa (`dependencyManagement` do proprio pom) | `facts/<mod>/gerenciadas.tsv` |
| documentacao: existe doc sobre X? onde? | `facts/<mod>/docs.json` |
| testes: quantos, de que tipo, frameworks, ArchUnit | `facts/<mod>/tests.json` + `tests.tsv` |
| fronteiras entre modulos, conflito de versao entre eles | `facts/_reactor.json` |
| conflito de versao ENTRE projetos do workspace | `workspace.json` -> `conflitos_de_versao_cruzados` |
| SNAPSHOT local atrasado | `workspace.json` -> `snapshots_locais` |
| listar/filtrar arquivos, churn, data de alteracao | `files.tsv` |
| quem referencia quem, ciclos, higiene de dependencia | `facts/<mod>/bytecode.json` (tier 2) |
| qual metodo chama qual | `facts/<mod>/callgraph.json` (tier 3) |

## Tabelas (TSV)

O indice traz `tabelas`: cada TSV com suas colunas e numero de linhas.
**Consulte isso antes de abrir qualquer TSV** - da para montar o `awk` sem
carregar o arquivo. Toda tabela tem cabecalho na primeira linha.

```bash
awk -F'\t' '$5=="organization" && $6=="codigo"' .scos-map/files.tsv
awk -F'\t' '$10>5' .scos-map/files.tsv                  # arquivos quentes
awk -F'\t' '$2 ~ /jjwt/ {print FILENAME, $2, $3}' .scos-map/facts/*/deps.tsv
```

**`deps.tsv` nao tem a lista completa.** Ele traz as diretas e apenas as
transitivas que fogem do fecho comum; as iguais (versao e scope) em todos os modulos ficam
uma unica vez em `facts/_transitivas_comuns.tsv`. Quando o envelope trouxer
`transitivas_no_fecho_comum`, a lista do modulo e `deps.tsv` +
`_transitivas_comuns.tsv`. **Nunca responda "o modulo nao usa X" olhando so
o `deps.tsv`.**

Na coluna `origem`, `effective-pom` significa que a versao veio do proprio
Maven (heranca, property e BOM ja resolvidos). Outros valores (`propria`,
`herdada:...`, `propriedade:...`, `bom`) foram deduzidos do `pom.xml`.

## Como interpretar a confianca

- `alta` - bytecode ou manifesto. Pode afirmar.
- `resolvida` - versao real do lockfile / `dependency:tree`.
- `declarada` - so o manifesto foi lido; a versao real pode diferir.
- `media` em `config` - o ambiente nao tem PyYAML e as chaves vieram de
  varredura de indentacao: lista, ancora, alias e multi-documento nao foram
  interpretados. Chave que voce nao encontrar pode existir mesmo assim.
- `media` em `bytecode` - jdeps sem classpath completo, ou bytecode
  `obsoleto` (o fonte mudou depois da ultima compilacao). Arestas novas
  podem faltar e arestas removidas podem aparecer. Serve para orientar, nao
  para afirmar.
- `parcial` - **so o callgraph**. Leia `lacunas_conhecidas` antes de
  concluir: proxy do Spring (`@Transactional`, `@Cacheable`), repositorio do
  Spring Data e reflexao **nao aparecem** no grafo estatico.
- `heuristica` - inferencia por convencao de nome. Confirme antes de afirmar.
- `conflito` (so em `desvios`) - `parse_pom` deduziu uma versao e o
  `effective-pom` respondeu outra. O valor gravado e o do effective-pom.
  Costuma ser property sobrescrita por profile ou BOM importado.

## Regras que evitam conclusao errada

1. Fato `obsoleto` foi gerado antes de mudancas nas fontes listadas em
   `mudou`. Diga isso ao usuario ou peca a regeneracao antes de responder.
2. `metodos_sem_chamador` **nao e lista de codigo morto**. Endpoint HTTP,
   `@Scheduled` e `@EventListener` nunca tem chamador no bytecode.
3. `estado: nao_aplicavel` e resultado legitimo, nao erro. React nao tem
   equivalente de bytecode; modulo agregador (`packaging=pom`) nao tem codigo.
4. Doc antiga ao lado de codigo recente e sinal de defasagem: compare
   `last_modified` do doc com o churn do modulo antes de trata-la como verdade.
5. Historico de arquivo nao esta no mapa. Se precisar, rode
   `git log --follow -- <caminho>` no caminho que o indice deu.
6. `bytecode_edges.tsv` vazio nao e silencio: o fato traz `motivo_vazio`,
   `diagnostico` e `amostra_saida`. Leia antes de concluir que o modulo nao
   tem dependencias.

## Dependencias no bytecode.json

Quatro baldes, e o balde importa:

- `deps_usadas_ausentes_do_pom` - **unico com risco imediato** (usada e nem
  resolvida).
- `deps_usadas_via_transitiva` - normal em Spring Boot (o starter traz). Vira
  risco so se o intermediario mudar. Ordenado por `referencias`: quanto
  maior, mais vale declarar explicitamente.
- `deps_declaradas_sem_uso` - precisa de confirmacao humana: reflexao, SPI e
  uso so em runtime nao aparecem no bytecode. Itens com
  `provavel_falso_positivo: true` (modulo interno agregado por component
  scan, driver/logger/migracao) **nao devem ser reportados como problema**.
- `deps_ignoradas_na_analise` - fora da comparacao de proposito (scope
  test/provided, starter, processador de anotacao). Nunca reporte como
  problema.

Se `transitivas_resolvidas` for false, a divisao entre os dois primeiros
baldes nao e confiavel.

`usadas_fora_do_jdeps` lista deps declaradas cuja classe so aparece em
descritor do bytecode (anotacao como `repositoryBaseClass = X.class`,
assinatura generica): o jdeps nao as reporta, entao contam como usadas.
Ausente = nada achado ou o jar nao estava no `~/.m2` - nao prova falta de uso.

## Testes

`tests.json` traz raizes varridas, frameworks (com `origem`: `declarada` no
manifesto ou `inferida` por import), contagem por tipo e regras ArchUnit.
O corpo esta em `tests.tsv`.

Tres coisas que **nunca** se afirma a partir deste fato:

1. **"a classe X esta coberta por teste"** - `alvo_heuristico` e casamento de
   nome. Diga "existe um teste chamado XTest", nunca "X esta testada".
2. **"nao existe teste para X"** - o certo e "nenhum arquivo de teste
   identificado nas raizes analisadas", citando `raizes`.
3. **qualquer coisa sobre cobertura** - `cobertura.estado` e `nao_analisado`.
   Ausencia de teste no mapa nao e ausencia de cobertura.

## Documentacao

`docs.json` classifica cada documento em `subtipo` (`adr`, `prd`, `epic`,
`story`, `spec`, `runbook`, `arquitetura`, `changelog`, `readme`, `outro`) e
diz por onde (`subtipo_por`: `caminho` ou `titulo`). `gerados_por_bmad` conta
o que veio de `_bmad-output/`.

Frontmatter (`status`, `owner`, `epic`) e lido **literalmente**. Ausencia de
`status` nao significa rascunho nem aprovado. `subtipo: outro` significa fora
de convencao, nao irrelevante.

## O fato cruzado do workspace

`conflitos_de_versao_cruzados` e o unico fato que nenhum mapa individual
enxerga - e o unico montado a partir do mapa **em cache** dos outros
projetos. Por isso tem `derivado_de: { <projeto>: { head, deps_sha } }`.

Scope `test` fica fora da comparacao. Modulo com sufixo ` (gerenciada)` e a
versao que o `dependencyManagement` (BOM) fixa, nao uso: conflito com ele
significa que o consumidor resolve uma versao diferente da que a BOM declara.

`status` recomputa contra o disco: se algum projeto moveu de commit ou teve as
deps regeradas, vem `obsoleto` com `mudou`. **Nao responda sobre conflito de
versao entre projetos com o fato obsoleto.**

`completude: parcial` com "arvore suja" significa que algum projeto tem
alteracao nao commitada: o fato nao corresponde a nenhum commit.

## SNAPSHOT local vs fonte ao lado

`snapshots_locais`. Quando um projeto consome outro do workspace como
`-SNAPSHOT`, o jar vem do `~/.m2` e pode estar **atras** do fonte ao lado.

Se `estado` for `jar_desatualizado` ou `jar_ausente`, **o codigo que voce le
no repo produtor nao e o que o consumidor executa**. Diga isso antes de
concluir qualquer coisa sobre o comportamento do consumidor, e cite `acao`.

`jar_atual` significa "o jar e mais novo que o ultimo commit", nao "o jar
contem o ultimo commit".

## Perguntas abertas

"Me explique esse repo" e caso particular: leia `index.json` +
`facts/_reactor.json` e o `layout.json` dos modulos maiores. Nao abra tudo.
