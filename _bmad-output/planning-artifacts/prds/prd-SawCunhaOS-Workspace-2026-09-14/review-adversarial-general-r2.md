# Revisão adversarial (rodada 2): PRD "Scripts de Consulta Rápida para scos-map"

Escopo: `prd.md`, `addendum.md`, `.memlog.md`, `benchmark-baseline.py`. Verificado contra `ferramentas/scos-map/scos-map.py`, `.scos-map/workspace.json`, `SawCunhaOS-Flow/.scos-map/` e `.claude/skills/scos-map/SKILL.md`. A seção "Delta vs rodada 1" no fim foi escrita só depois de formada esta avaliação.

## Veredito

**Quase pronto, mas ainda não confiável como está.** A PRD melhorou muito: teto, envelope, FR-4 sobre fato existente e SM-1 por tipo de fato estão bem melhores. As medições novas, porém, são mais fracas do que o texto as apresenta. O "proxy do CLI" é desenhado à mão e tem um viés que o torna otimista. O comparador "grep" não é o concorrente real. A promessa central de FR-5 ("reutiliza `fact_state`") esconde um custo grande e uma lacuna factual. Há contradições residuais entre seções.

Contagem: 2 críticos, 6 altos, 6 médios, 3 baixos.

---

## CRITICAL

### C1. FR-5: `fact_state` não é uma função "barata de reutilizar", e não cobre `snapshots_locais`
- Citações: FR-5 "`obsoleto` é recomputado na consulta reutilizando a função `fact_state` (e a checagem equivalente de `workspace.json`) ... o CLI não reimplementa a regra"; FR-4 "o CLI só lê o fato: não acessa `~/.m2` nem o git em tempo de consulta ... o princípio 'só lê fatos' não tem exceção".
- Verificado em `scos-map.py:2742`: `fact_state(fato, files_by_path, files, root)` precisa de `files_by_path` e `files`. No `cmd_status_one` (linha 3819) eles vêm de `MultiGit(root)` + `detect_modules` + `scan_files`, ou seja, varredura do repositório inteiro com subprocessos git e hash de blobs. Para fatos de bytecode ele ainda abre `target/classes` (`assinatura_classes`).
  - Isso **contradiz** "só lê fatos" e "não acessa o git em tempo de consulta". A PRD só proíbe `~/.m2`/git no FR-4, mas FR-5 exige git em toda consulta.
  - Contradiz também a motivação original do memlog (agente achou o scos-map "mais lento que grep"). O custo de latência por chamada nunca é medido: o benchmark mede só bytes.
- Para `workspace.json`, "a checagem equivalente" existe só para `conflitos_de_versao_cruzados` (`avaliar_fato_cruzado`, linha 3776). Eu verifiquei que `snapshots_locais` **não tem `derivado_de`** (`'derivado_de' in snapshots_locais` é `False`). Passado por `fact_state`, ele devolve `fresco` para sempre. Resultado concreto: um fato gerado em 2026-09-14 (hoje é 2026-10-02, 18 dias) sai com `estado=fresco` mesmo com `~/.m2` e HEAD já diferentes. É falso-fresco exatamente na UJ-2 (decidir `mvn clean install`).
- O FR-4 diz "se `workspace.json` estiver `obsoleto` (critério de FR-5), o cabeçalho sinaliza", mas o critério de FR-5 não alcança esse fato.
- **Correção:** (a) decidir explicitamente: ou o CLI paga o `scan_files` (e então medir e declarar latência e remover o "só lê fatos"), ou usa um frescor barato (`gerado_em` vs `git rev-parse HEAD`, comparação de `head` gravado em `derivado_de`). (b) Para `snapshots_locais`, comparar o `ultimo_commit`/`head` gravado em `repo_local` com o HEAD atual (um `git rev-parse` por repo) ou, no mínimo, sinalizar `estado=obsoleto` quando `gerado_em` for anterior a N dias. (c) Adicionar critério de teste: invocação em fixture com fato `snapshots_locais` velho não pode sair `fresco`. (d) Registrar que `scos-map.py` tem hífen no nome e ~3,9 mil linhas; importá-lo exige `importlib` e custo de import por chamada.

### C2. O "proxy do CLI" do benchmark é otimista e não valida o que SM-1 afirma
O SM-1 diz "9 de 9 ≤ 10% do `Read` (0,3% a 6,9%)", mas o número vem de `benchmark-baseline.py`, que é um proxy escrito à mão por quem conhece a resposta. Problemas verificados no script:
1. **Cabeçalho hard-coded**: `HDR="# confianca=alta estado=fresco gerado=2026-09-15T00:32:06Z\n"` para todas as perguntas. Na realidade: `deps` é `resolvida`/`declarada`; Q7 é `resolvida` com `completude=parcial` ("arvore suja em SawCunhaOS-Flow, ..."); Q8 é `media`. O cabeçalho real e as marcas por linha serão mais longos, e o proxy nunca os exerce.
2. **Q3 ignora uma armadilha documentada**: o `SKILL.md` diz "`deps.tsv` nao tem a lista completa ... **Nunca responda 'o modulo nao usa X' olhando so o `deps.tsv`**" (transitivas ficam em `_transitivas_comuns.tsv`). O proxy da Q3 filtra só `deps.tsv`. O subcomando `deps` real precisa unir `deps.tsv` + `_transitivas_comuns.tsv` (+ `deps.json`, ver §8), então o resultado e o tamanho serão outros, e o `grep` também (o grep da Q3 tem o mesmo defeito de resposta incompleta).
3. **Respostas não equivalentes**: Q1 `grep '^package'` devolve nomes de pacote, o CLI devolve `pacote_base` + 3 áreas com `papel` (informação diferente). Q5: o CLI casa `path+titulo` de `docs.json`, o `grep -ril` casa o **conteúdo** dos `.md`. Q4 compara `gerenciadas.tsv` com `pom.xml`. SM-1 exige "a resposta precisa ser igual à do fato", mas o script nunca compara conteúdos, só mede bytes. O `ok` é só razão de tamanho.
4. **Q7/Q8 não são "compactos"**: Q7 serializa cada item com `json.dumps` (800 bytes para 2 itens; os itens carregam listas de módulos inteiras). Q8: todos os 10 itens estão `jar_desatualizado`, então o filtro `estado!="jar_atual"` não filtra nada; a medição não testa o caso real de mistura.
5. **Concorrente errado**: `jq` está instalado (`/usr/bin/jq`). Um `jq -c '{pacote_base,areas:[.areas[]|.papel]}' layout.json` responde a Q1 em poucas centenas de bytes sem CLI novo. O benchmark compara contra `Read` do fato inteiro (que é o pior caso) e contra `grep` no código-fonte, nunca contra `jq`/`python -c` sobre o fato. O addendum descarta `jq` como "interface direta", mas não o mede como baseline; a alegação "o CLI vence os dois" omite o terceiro concorrente que o próprio addendum cita como prior art mais próximo.
6. **Baseline do `Read` talvez inflado**: o PRD assume que o agente paga 142KB lendo `config.json`. Isso não foi verificado (o `Read` tool tem limite de tamanho/tokens e erra acima dele; o agente na prática já recorre a `jq`/`python`/`offset`). Se o `Read` falha, o baseline real é outro.
7. **Latência e tokens ausentes**: a métrica é bytes; a PRD chama `bytes/3,5` de tokens no addendum. Sem tempo de execução por chamada (ver C1).
- **Correção:** (a) o benchmark deve rodar o CLI **real** assim que existir (SM-1 vira teste executável na suíte), com asserção de conteúdo contra uma resposta esperada por pergunta; (b) incluir `jq` como quarto caminho; (c) medir latência por chamada; (d) incluir um caso Q8 com mistura de estados e um caso com `deps` que dependa de `_transitivas_comuns.tsv`; (e) rotular a tabela do addendum como "estimativa otimista com proxy", não como baseline, e reescrever a frase de SM-1 de acordo.

---

## HIGH

### H1. O envelope de FR-5 é incompleto: perde `completude`/`limitacoes`, e "exatamente como constam no fato" é falso
- FR-5: `estado` e `confianca` "exatamente como constam no fato". Verifiquei `layout.json`: tem `confianca: alta`, mas **não tem `estado` nem `gerado_em`** (esses estão no `index.json`, `gerado_em` também no `workspace.json`). A fonte de `gerado=<timestamp>` e de `estado` não é especificada. `disponivel` está no enum, mas não aparece em nenhum fato que eu inspecionei.
- O fato `conflitos_de_versao_cruzados` tem `confianca=resolvida` **e** `completude.nivel=parcial` com limitação "arvore suja em SawCunhaOS-Flow, SawCunhaOS-Foundation, sawcunha-open-system-bom: o fato nao corresponde a nenhum commit". `snapshots_locais` tem `completude.limitacoes` (mtime não prova conteúdo). O `status` do próprio scos-map imprime essas limitações (`!`), o envelope da PRD não. SM-C1 só testa os cinco valores de `confianca`; `resolvida` está **fora** da lista de SM-C1 e do critério, então um fato `resolvida`+`parcial` com árvore suja passa como confiável. O envelope pode ser sintaticamente correto e semanticamente enganoso.
- FR-4 ("esses limites aparecem no `--help`") empurra a limitação para fora da saída: o agente que lê só a saída não vê. Isso contradiz a justificativa do envelope.
- **Correção:** acrescentar `completude=<nivel>` ao cabeçalho e uma linha `# limitacao: ...` (truncada) quando `parcial`; definir a fonte de cada campo do cabeçalho; incluir `resolvida` em SM-C1.

### H2. FR-9: teto em linhas, não em bytes, ordem de truncamento indefinida, e o 50 foi validado em amostra viciada
- "Teto padrão de 50 linhas (medido: a maior resposta do benchmark teve 17 linhas)". As 9 perguntas foram escolhidas pelo autor e a Q9 usa `ValidateAuthorityUseCase`, uma classe com 3 arestas de saída (17 linhas no total). Medi o mesmo `bytecode_edges.tsv`: `ScosPaginated` aparece como destino de **82** arestas internas e `ReasonEntityType` 44; uma pergunta natural ("quem usa `ScosPaginated`?") já estoura o teto de 50. Logo "o teto bastou" é falso fora do benchmark; o texto fechou a assunção sem evidência.
- Teto por linhas não limita bytes: linhas de `docs` ou `config` podem ser longas; um limite de linhas deixa uma resposta de 50 linhas enormes passar. SM-C2 cobre o total, mas FR-9 não.
- Não se especifica **quais** 50 linhas sobrevivem (ordem do arquivo? ordenação?), nem se o cabeçalho conta no teto. O agente que recebe "# N linhas omitidas" pode concluir ausência ("o módulo não usa X") a partir de uma lista truncada, o erro que a skill já proíbe para `deps.tsv`. O aviso de omissão não diz se a omissão é de linhas que casam com o filtro ou do conjunto.
- A "linha de aviso" pede "refine com <filtro>", mas FR-2 limitou os filtros ao conjunto fechado de `awk` documentados; um agente pode não ter filtro para refinar (ex.: `arestas` por destino exato não é um `awk` documentado). Conflito direto FR-2 x FR-10 x FR-9.
- **Correção:** teto duplo (linhas e bytes); ordem determinística e documentada; aviso com "N de M linhas casam"; FR-10 deve ter filtro destino/origem explícito em FR-2; reabrir a calibração do 50 com perguntas "quentes".

### H3. Experimento do subagent: n=1, comparação de unidades diferentes, e o ponto de equilíbrio de 120KB é incoerente
- "~45×" vem de **uma** execução; 34.315 tokens vs "~770 tokens", sendo que 770 é `2.693/3,5` (estimado, não medido). Tokens totais de subagent (que incluem prompt de sistema/ferramentas, em cache e com preço por token de Haiku, mais barato) são comparados a bytes/3,5 do contexto principal. Comparação de custo exigiria preço, cache e variância; o addendum usa a palavra "tokens" para duas grandezas diferentes.
- "O ponto de equilíbrio fica em torno de 120KB": isso é 34.315 × 3,5 (overhead convertido em bytes), assumindo que a saída seria ressumida a custo marginal zero. Mas o parágrafo seguinte diz que a devolução literal "não poupa contexto principal". As duas afirmações não podem ser verdadeiras juntas: se o subagent devolve literal, **nunca** há equilíbrio, qualquer que seja o tamanho; só um digest dá ganho. O limiar de "~100KB" que a PRD guarda para reabrir é, portanto, um número sem fundamento.
- A decisão (descartar o subagent) provavelmente está certa, mas a justificativa publicada é fraca. Para uma PRD interna, o ideal é registrar como "descartado por simplicidade", não por "medição".
- **Correção:** reescrever como "hipótese descartada; amostra única; reabrir se aparecer digest" e remover o número 120KB/100KB ou derivá-lo corretamente.

### H4. FR-4 / UJ-2: o fato `snapshots_locais` já é velho e 100% "desatualizado" no estado atual, e a regra de "atraso" é fraca
- Todos os 10 itens de `snapshots_locais` estão `jar_desatualizado` (contei). O fato diz `mtime ... nao e prova de conteudo` e `commit nao empurrado ou stash nao sao considerados`. O agente vai receber 10 linhas "desatualizado" sempre que houver qualquer commit novo na Foundation, sem distinguir mudança de código de mudança de docs (os commits recentes da Foundation são `docs(...)`: stories 4.x só documentam). Resultado: alarme constante, a pergunta "preciso de `mvn clean install`?" fica quase sempre "sim", e o agente aprende a ignorar o sinal.
- `atraso_dias` mede dias entre mtime do jar e último commit, não "o código mudou". Sem filtro por módulo produtor (um commit em `docs/` marca todos os jars da Foundation).
- **Correção:** aceitar a limitação no corpo do `--help` não basta; exibir a limitação na saída (H1) e considerar agrupar por `produzido_por` (uma linha por repo + contagem) em vez de uma linha por GA, o que reduz tokens e alarme.

### H5. FR-11 "só skills finas": o critério (≤30 linhas, desc ≤1 linha) é de forma, não de custo, e a própria PRD já tem o `SKILL.md` com 218 linhas
- Citação: FR-11 "A descrição ... no máximo 1 linha e o corpo no máximo 30 linhas. Teste: contagem de linhas". Linhas não são tokens; uma linha pode ter 500 caracteres. Teste mede o que é fácil.
- A skill `scos-map` atual tem 218 linhas (`wc -l`). FR-7 diz "reduzida a um ponteiro curto", mas FR-7 também exige que `SKILL.md` contenha exemplos de saída por subcomando (FR-1/FR-6: "exemplo ... no `--help`/`SKILL.md`"), o aviso de tamanho dos fatos grandes e a tabela de roteamento (1:1 com subcomando). 8 subcomandos × (3–5 linhas de exemplo) = 24–40 linhas só de exemplo, o que estoura 30 linhas para `scos-query` sozinho. As consequências de FR-1, FR-6, FR-7 e FR-11 são mutuamente incompatíveis: ou os exemplos vivem no `--help` (e o agente paga uma chamada extra, justo o que SM-C2 diz medir) ou a skill passa de 30 linhas.
- Também: "a skill `scos-map` é reduzida a um ponteiro" implica **apagar** conteúdo que o `scos-map-build`/humanos usam (interpretação de confiança, armadilha do `deps.tsv`). Não há inventário do que sai nem para onde vai. A armadilha do `_transitivas_comuns.tsv` desaparecendo da skill reintroduz o erro "o módulo não usa X".
- **Correção:** medir por caracteres/tokens; decidir onde moram os exemplos; listar o que a skill `scos-map` perde e onde fica; `--help` curto por subcomando.

### H6. FR-2 ainda é uma superfície grande e vaga: "equivalente via CLI" de `awk` ad hoc
- "Cada comando `awk -F'\t'` ... literalmente presente no `SKILL.md` e no `AGENTS.md` tem um equivalente". Os exemplos reais do `SKILL.md` são `$5=="organization" && $6=="codigo"`, `$10>5` (coluna numérica, churn), `$2 ~ /jjwt/ {print FILENAME,$2,$3}` **sobre `facts/*/deps.tsv` (todos os módulos, glob)**. O terceiro é consulta cross-módulo de um projeto: a assinatura "projeto + módulo posicionais" de FR-1 não a cobre. `$10>5` exige operadores numéricos; o FR-2 diz "coluna + padrão", sem operador. O conjunto "fechado" muda quando o `SKILL.md` muda, e como FR-11/FR-7 reduzem o `SKILL.md`, o conjunto de exigências de FR-2 muda **por efeito colateral** da edição da skill (o teste de FR-2 depende de um texto que FR-7/FR-11 vão reescrever).
- **Correção:** enumerar os filtros em tabela fixa dentro da PRD (comando, equivalência, caso de teste) e congelar; adicionar `deps` sem módulo (todos) e operadores numéricos explicitamente.

---

## MEDIUM

### M1. SM-1: meta "≤ 10% do `Read`" quebra em fatos pequenos e a meta de TSV é vazia
- O cabeçalho de FR-5 custa ~58 bytes. Para fatos pequenos (BOM inteira = 60KB; `gerenciadas.tsv` = 3,5KB; `deps.json` do usecase = 617 bytes), 10% de 617 bytes são 61 bytes: o cabeçalho sozinho passa. SM-1 pede ≤10% do `Read` para toda pergunta, o que é matematicamente impossível para fatos < ~600 bytes.
- A meta de TSV ("paridade com o `grep`, tolerância ~60 bytes") reconhece que no TSV o CLI **não ganha**: Q3 1,10× e Q9 1,02× na linha de base com proxy. Q9 sai por 59 bytes de diferença (3.090 vs 3.031), no limite exato da tolerância de 60: um único byte de formato a mais reprova. O critério é calibrado ao resultado já obtido (circular).
- "≥ 80% das perguntas com `grep` possível" em amostra de 4 JSON: 80% de 4 é 3,2, ou seja, 4 de 4. Estatisticamente, é "todas".
- **Correção:** meta de ≤10% apenas para fatos > X KB; tolerância de TSV como número absoluto + percentual; 9 perguntas é um conjunto de regressão, não evidência de generalização, e deve ser dito.

### M2. Contradição residual de motivação: TSV "só interface única" vs. custo do envelope
- Seção 1 afirma "na maioria das perguntas, do que o `grep` equivalente". A linha de base: dos 9, o CLI é menor que o grep em 6 (Q1, Q2, Q4, Q5, Q6 e Q7/Q8 sem grep); é pior ou empata nos dois TSV com perguntas reais (Q3 e Q9). Para TSV, a PRD admite que o ganho é só "interface única" e ainda assim FR-10 (maior risco, arestas) está no MVP. O custo de implementação do TSV (FR-10 + parte de FR-2) é alto para ganho declarado ~0 em bytes. A decisão do usuário foi consciente (addendum), mas SM-1 mede exatamente aquilo em que ela não rende.
- **Correção:** registrar no PRD que, para TSV, o ganho esperado é de **acurácia/envelope**, não de bytes, e medir isso (ex.: o CLI avisa quando `bytecode_edges.tsv` está obsoleto, o `awk` não). Senão, as métricas premiam o que não foi o objetivo.

### M3. §8/§9 "Nenhuma" e `.memlog.md` desalinhados
- §8 diz "Nenhuma" e §9 "Nenhuma pendente", mas a PRD tem `[NOTE FOR PM]` abertas (FR-2, 6.2) e a Q8 aponta limitações não resolvidas (H1/H4). O `.memlog.md` registra "(assumption) Pendentes ... modelo/limiar do FR-11" e depois "FR-11 só skill fina, sem agente": limpo, mas o addendum ainda diz "O desenho (skill `scos-query` fina + agente de modelo barato com Bash apenas) fica como ponto de partida" e `prd.md` §4.4 ainda descreve o empacotamento "(e, no futuro, por um subagent intermediário)" com FR-6 apresentado como pré-requisito para esse subagent.
- O Glossário ainda define "Subagent" como termo e "Non-Goals" cita o subagent: artefatos de uma decisão revertida. Não é erro, mas ocupa tokens de leitura do implementador.
- **Correção:** podar o Glossário e §4.4 da referência a subagent; mover o experimento inteiro ao addendum.

### M4. FR-8: log na raiz do workspace contradiz a execução "por repo" e é globalmente concorrente
- "`.scos-map-query.log` na raiz do workspace, listado no `.gitignore`". Verifiquei: `.scos-map-query.log` não existe e o `.gitignore` raiz lista só os três repos; o `.gitignore` é versionado no repo do workspace (ok), mas o CLI também deve funcionar dentro de um repo isolado (os três têm `.scos-map/` próprio, e cada um tem AGENTS.md próprio). Se o agente roda a partir do `SawCunhaOS-Flow/`, "raiz do workspace" é ambígua (um diretório acima?). Appends concorrentes (agentes paralelos) sem lock podem intercalar linhas; best-effort cobre falha, não corrupção.
- O log registra bytes/linhas, mas FR-8 nunca diz quem consome. §6.2 adia o `gain`. Escrita permanente sem leitor é custo sem valor (YAGNI); o log só justifica SM-C2 se algo o ler.
- **Correção:** definir raiz como "diretório pai que contém `.scos-map/workspace.json`" ou variável de ambiente; limite de tamanho/rotação ou cortar FR-8 até o `gain` existir.

### M5. NFR-1: "um único prefixo de comando" colide com o nome do arquivo e com o diretório
- "vive em `ferramentas/scos-map/scos-map-query.py`", chamado como `scos-map-query` (Glossário: "nome fixo"). Não existe wrapper/shebang/PATH definido; o agente chamará `python3 ferramentas/scos-map/scos-map-query.py ...` (comprido, um prefixo de allowlist é possível, mas a skill de 30 linhas precisa carregar esse caminho em cada exemplo) ou o nome curto `scos-map-query` que não existe no PATH. O nome "fixo" e o artefato real divergem. Também `python3` do ambiente: o gerador exige Python >= ? (a PRD diz só "stdlib").
- **Correção:** fixar o comando literal que o agente digita e a versão mínima de Python.

### M6. FR-3 / "vazio nunca significa sucesso" vs. filtros que retornam zero linhas
- FR-3 trata zero conflitos com cabeçalho. FR-1/FR-2/FR-10 não dizem o mesmo para "filtro sem resultado" (ex.: `deps` filtrado por `jjwt` com zero casas). Zero linhas de dado com cabeçalho `estado=fresco` é lido como "o módulo não usa jjwt", e a armadilha do `_transitivas_comuns.tsv` (C2.2) torna isso errado. Falta um rodapé `# 0 linhas casam; fontes consultadas: deps.tsv, _transitivas_comuns.tsv`.
- **Correção:** toda saída deve listar fontes consultadas e contagem de casamentos.

---

## LOW

### L1. `Read` de `workspace.json` é só 18,5KB, e o baseline de Q7/Q8 é mais fraco do que parece
- Q7/Q8 comparam com "18.500 bytes" do `Read`. É pequeno; a economia absoluta (~17KB, ~5k tokens) é modesta e Q7/Q8 são as únicas perguntas "só o scos-map resolve", usadas como justificativa estratégica ("o que nenhum `grep` resolve"). Um `jq '.conflitos_de_versao_cruzados.itens'` custa ~1KB. Registrar que o valor dessas duas consultas é a semântica (frescor/envelope), não bytes.

### L2. UJs cobrem 3 dos 8 subcomandos, de novo
- UJ-1 a UJ-3 realizam layout, snapshots, conflitos. `config`, `deps`, `gerenciadas`, `docs`, `arquivos`, `arestas` (FR-10, o maior risco) não têm jornada. FR-10 está no MVP sem jornada que o justifique, enquanto a Q9 é a pergunta que sai em paridade no TSV (M2).

### L3. Datas e proveniência frágeis
- O benchmark tem `HDR` com timestamp fixo e caminhos absolutos (`R="/home/sawcunha/Projetos/SCOS"`), abre `.scos-map` de repos ignorados pelo `.gitignore` raiz (`/SawCunhaOS-Flow/`): o "benchmark canônico" não é reproduzível em outra máquina nem após regenerar o mapa (tamanhos mudam), e o `.py` está untracked. SM-1 diz "medidas offline e repetíveis"; só são repetíveis nesta máquina e neste estado do mapa. Fixar fixtures no `tests/` ou registrar o hash do mapa usado.

---

## O que está bom (preservar)
- FR-4 passou a ler o fato `snapshots_locais`, que **de fato existe** com os campos citados (`ga`, `versao`, `estado`, `acao`, `atraso_dias`, `confianca=media`): verificado em `workspace.json`.
- Envelope com cabeçalho único + marca só quando difere (barato) e testes de contrato (SM-C1) com fixture `obsoleto`.
- Medição real em vez de suposição: a inversão `Read` vs `grep` para JSON é genuína (54KB/142KB vs <2KB).
- Decisão correta de descartar o subagent no MVP e de deixar `scos-map-build` intocado; NFR-1 stdlib-only confere com `scos-map.py`.
- Teste golden por subcomando (FR-6) e erro com o comando de `scos-map-build` a rodar (FR-1).

## Prioridade sugerida
1. C1: decidir o custo/semântica real de frescor (e o falso-fresco de `snapshots_locais`).
2. C2: trocar o proxy por um teste executável com o CLI real, incluir `jq` e latência, e corrigir Q3/Q7/Q8.
3. H1/H2: completar o envelope (`completude`) e fixar o teto em bytes, ordem e contagem.
4. H5: reconciliar FR-1/6/7/11 (exemplos x 30 linhas).
5. Limpar contradições residuais (M3, H3).

---

## Delta vs rodada 1

Resolvidos (verificados na PRD atual):
- R1-C1 (SM-1 sem baseline): parcialmente resolvido. Há benchmark fechado, meta numérica e baseline, mas ver C2 desta rodada (proxy otimista, sem `jq`, sem comparação de conteúdo).
- R1-C2 (tokens reais do FR-8 inviáveis): **resolvido**; FR-8 só grava bytes/linhas e o addendum explica por quê.
- R1-C3 (FR-4 sem definição / violava "só lê fatos"): **parcialmente resolvido**; agora lê `snapshots_locais`, que existe. Mas surge o problema novo de frescor desse fato (C1 desta rodada) e a regra de atraso por mtime (H4).
- R1-H2 (sem teto): resolvido por FR-9, porém ver H2 desta rodada (linhas, não bytes; 50 validado em amostra viciada).
- R1-H3 (subagent): resolvido por descarte, com justificativa fraca (H3 desta rodada).
- R1-H4 (envelope por linha/enum/`obsoleto`): **resolvido na forma** (cabeçalho único, enum, `fact_state`); **aberto no fundo** (custo do `fact_state`, falta `completude`, fonte dos campos): C1, H1.
- R1-H5 (SM-2/SM-C1 não mensuráveis): resolvido (checagem estática e fixture).
- R1-H6 (contradições e OQs): resolvido (OQs fechadas, Tier 2/3 via FR-10, log fora de `.scos-map/`); restam resíduos de subagent no Glossário/§4.4 (M3).
- R1-M2 (FR-6 sem golden): resolvido. R1-M3 (vazio vs erro): resolvido para FR-3/FR-5, residual em filtros (M6). R1-M4 (NFR): resolvido por NFR-1, com lacuna de comando literal (M5). R1-M5 (custo de documentação): resolvido por SM-C2, mas ver H5. R1-M6 (adesão): resolvido (reconhecida amostragem, aviso de tamanho). R1-L1 (título/nome): parcialmente (M5).

Ainda abertos da rodada 1:
- R1-H1 (escopo TSV / alternativa de formato do gerador): a alternativa agora está registrada no addendum e FR-2 foi limitado, mas continua frágil (H6, M2); `jq` nunca é medido (C2.5).
- R1-M1 (exemplo de saída por subcomando): empurrado para "primeira story" (pendência do addendum), ainda sem schema; agravado pela tensão com 30 linhas (H5).
- R1-L2 (UJs cobrem poucos subcomandos): continua (L2).
- R1-L3 (comandos reproduzíveis): melhorou (addendum), mas o benchmark não é portável (L3).

Novos nesta rodada: C1, C2 (parcialmente derivado de R1-C1), H1, H2 (calibragem), H3 (rigor do experimento), H4, H5, H6, M1, M4, M5 (em parte), M6, L1, L3.
