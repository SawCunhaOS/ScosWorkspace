---
name: scos-map
description: Consulta a estrutura dos repositorios do SCOS (SawCunhaOS) - um projeto ou o workspace inteiro com varios projetos lado a lado - onde ficam os arquivos, configuracoes, dependencias e versoes, e como os modulos se relacionam. Use quando a pergunta for sobre a organizacao do codigo e nao sobre o conteudo de um arquivo especifico ja conhecido.
---

# scos-map

Indice estrutural de repositorio. **E um indice, nao um substituto do codigo**:
ele diz onde achar, com que confianca e quao fresco esta cada fato. Para ler
conteudo, abra o arquivo pelo caminho que o indice deu.

## Passo 0 - sempre

```bash
python3 scos-map.py status .        # ja existe mapa? o que esta obsoleto?
```

Se nao existir mapa, decida entre projeto e workspace:

```bash
python3 scos-map.py scan .          # UM projeto (tem pom.xml/package.json na raiz)
python3 scos-map.py workspace .     # VARIOS projetos lado a lado
```

Na duvida rode `workspace`: se a raiz for um projeto unico ele degrada para
`scan` sozinho. Cada projeto recebe seu proprio `<projeto>/.scos-map/`, e a raiz
ganha `.scos-map/workspace.json`.

**Em workspace, leia `workspace.json` primeiro.** Ele lista os projetos e
aponta o `index.json` de cada um. Abra so o index do projeto relevante.
`conflitos_de_versao_cruzados` compara bibliotecas ENTRE projetos - e o unico
fato que nenhum mapa individual enxerga.

Em projeto unico, leia **apenas** `.scos-map/index.json`. Ele lista modulos, ecossistemas e
o estado de cada fato. Escolha os fatos que a pergunta exige e abra so aqueles.
Nunca leia todos os arquivos de fato "para ter o quadro completo".

## Roteamento - qual fato responde o que

| A pergunta e sobre | Abra |
|---|---|
| onde mora o que, convencao de pacote, pontos de entrada | `facts/<mod>/layout.json` |
| onde ficam as configs, quais chaves e perfis existem | `facts/<mod>/config.json` |
| dependencias, versoes, divergencia declarada x resolvida | `facts/<mod>/deps.json` |
| documentacao: existe doc sobre X? onde? | `facts/<mod>/docs.json` |
| fronteiras entre modulos, conflito de versao entre eles | `facts/_reactor.json` |
| listar/filtrar arquivos, churn, data de alteracao | `files.tsv` (use grep/awk) |
| quem referencia quem, ciclos, higiene de dependencia | `facts/<mod>/bytecode.json` (tier 2) |
| qual metodo chama qual | `facts/<mod>/callgraph.json` (tier 3) |

`files.tsv` e tabular: prefira `grep` e `awk` a carregar o arquivo inteiro.

```bash
awk -F'\t' '$5=="organization" && $6=="codigo"' .scos-map/files.tsv
awk -F'\t' '$10>5' .scos-map/files.tsv          # arquivos quentes (churn 90d)
```

## Orcamento - nao escale sem necessidade

## Fazer tudo de uma vez

```bash
python3 scos-map.py workspace . --all      # ou: scan . --all
```

`--all` = tier 3 + compila sem perguntar + maven online. Antes de gastar o
tempo ele imprime um **plano** dizendo o que vai rodar e o que esta faltando
no ambiente (jdeps, mvn, jar do callgraph). No fim imprime **ACHADOS**:
versoes divergentes entre projetos, ciclos entre pacotes, dependencias usadas
mas nao declaradas, e o que ficou sem analisar e por que. O mesmo conteudo
fica em `workspace.json` no campo `achados`.

Use `--all` quando quiser o quadro completo. Para uso rotineiro prefira o
tier 1: e o que responde as perguntas de navegacao, em segundos.

Reprocessar so o que mudou num workspace:

```bash
python3 scos-map.py workspace . --only scos-foundation
```

Os demais projetos ficam no indice marcados como cache - o `workspace.json`
continua descrevendo o workspace inteiro.

**Tier 1** (`scan .`) - segundos, sem build. Cobre layout, config, deps e docs.
Responde a grande maioria das perguntas de navegacao. Rode sempre.

**Tier 2** (`scan . --tier 2`) - exige `target/classes`. So escale quando a
pergunta for de qualidade arquitetural: ciclos entre pacotes, dependencia usada
mas nao declarada, dependencia declarada e nao usada, versao de bytecode.
O script **nunca compila sozinho**: se o bytecode estiver ausente ou obsoleto
ele pergunta. Nao passe `--compile` sem que o usuario tenha autorizado.

**Tier 3** (`scan . --tier 3 --callgraph-jar <path>`) - grafo de metodo.
So com pedido explicito. Exige o jar do java-callgraph.

## Como interpretar o retorno

Todo fato traz `confianca` e procedencia. Respeite:

- `alta` - veio de bytecode ou manifesto. Pode afirmar.
- `resolvida` - versao real do lockfile/dependency:tree.
- `declarada` - so o manifesto foi lido; a versao real pode diferir.
  O campo `resolucao_indisponivel` diz por que.
- `media` - jdeps sem classpath completo; deps externas podem estar incompletas.
**Dependencias no bytecode.json** vem em quatro baldes, e o balde importa:
`deps_usadas_ausentes_do_pom` e o unico com risco imediato (usada e nem
resolvida). `deps_usadas_via_transitiva` e normal em Spring Boot (starter
traz tudo) - so vira risco se o intermediario mudar.
`deps_declaradas_sem_uso` precisa de confirmacao humana: reflexao, SPI e uso
so em runtime nao aparecem no bytecode. Itens com
`provavel_falso_positivo: true` (modulo interno do reator agregado por
component scan, driver/logger/migracao que atuam por configuracao) ficam fora
dos ACHADOS de proposito - nao reporte como problema. `deps_ignoradas_na_analise` saiu de
proposito (scope test/provided, starter, processador de anotacao) - nunca
reporte isso como problema. Se `transitivas_resolvidas` for false, a divisao
entre os dois primeiros baldes nao e confiavel.

- `jdeps_tentativas` presente = o jdeps abortou na primeira execucao e foi
  reexecutado (tipicamente jar multi-release). O resultado final e valido.
- `aviso_nao_resolvidas` = classpath incompleto; `deps_nao_declaradas` fica
  pouco confiavel nesse modulo.
- `bytecode_edges.tsv` vazio nao e silencio: o fato traz `motivo_vazio`,
  `diagnostico` (linhas lidas/casadas/descartadas) e `amostra_saida`.
  Leia isso antes de concluir que o modulo nao tem dependencias.
- `media` com `frescor.estado: obsoleto` - o grafo foi lido de bytecode
  antigo porque o fonte mudou e nao deu para recompilar (veja `frescor.nota`).
  Arestas novas podem faltar e arestas ja removidas podem aparecer. Util para
  orientar, nao para afirmar.
- `parcial` - **so o callgraph**. Leia `lacunas_conhecidas` antes de concluir
  qualquer coisa. Proxy do Spring (`@Transactional`, `@Cacheable`), repositorio
  do Spring Data e reflexao **nao aparecem** no grafo estatico.
- `heuristica` - inferencia por convencao de nome. Confirme antes de afirmar.

Regras que evitam conclusao errada:

1. Fato com `estado: obsoleto` foi gerado antes de mudancas nas fontes listadas
   em `mudou`. Diga isso ao usuario ou regenere antes de responder.
2. `metodos_sem_chamador` **nao e lista de codigo morto**. Endpoint HTTP,
   `@Scheduled` e `@EventListener` nunca tem chamador no bytecode.
3. `estado: nao_aplicavel` e resultado legitimo, nao erro. React nao tem
   equivalente de bytecode; modulo agregador (`packaging=pom`) nao tem codigo.
4. Doc antiga ao lado de codigo recente e sinal de defasagem: compare
   `last_modified` do doc com o churn do modulo antes de trata-la como verdade.
5. Historico de arquivo nao esta no mapa. Se precisar, rode
   `git log --follow -- <caminho>` no caminho que o indice deu.

## Perguntas abertas

"Me explique esse repo" e o caso particular: leia `index.json` +
`facts/_reactor.json` e o `layout.json` dos modulos maiores. Nao abra tudo.