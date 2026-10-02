# Revisão adversarial — ARCHITECTURE-SPINE scos-map-query

Data: 2026-10-02. Alvo: `ARCHITECTURE-SPINE.md` (somente leitura). Contexto: `prd.md` (FR-1 a FR-14, NFR-1/2). Verificação pontual no mapa real: `SawCunhaOS-Flow/.scos-map/` (módulos aninhados, `_raiz`, `_transitivas_comuns.tsv` na pasta `facts/` do projeto).

Método: para cada achado, duas unidades de uma ou duas stories diferentes, cada uma obedecendo todos os ADs ao pé da letra, e que mesmo assim produzem saída ou comportamento incompatível. Ordem: severidade (S1 bloqueia a integração ou quebra o envelope; S2 gera divergência de saída/golden; S3 lacuna menor).

**Veredito:** a spine fixa bem as fronteiras de camada (quem imprime, quem abre arquivo), mas deixa em aberto o conteúdo dos três tipos do contrato (`Resultado`, `Secao`, `Meta`) e a divisão de cálculo entre `comandos/`, `fatos.py` e `render.py`. Hoje dois implementadores independentes não conseguem encaixar suas peças. São 6 achados S1, 12 S2 e 6 S3.

---

## S1 — Bloqueiam a integração

### S1-1. `Secao` não tem `total`: quem calcula "n de M" e trunca?

- **ADs:** AD-1 (comando é puro), AD-2 (`Secao(nome, colunas, linhas)`, cabeçalho `(<mostradas> de <total>)`), AD-4 (rodapé `n de M`), AD-6 (render aplica teto).
- **Unidade A (`comandos/arestas.py`, story FR-10):** a flag `--limit` está na lista de flags do módulo (AD-1); A aplica `args.limit` e devolve `linhas[:limit]`. Como `Secao` só tem `linhas`, o total real (107) se perde.
- **Unidade B (`render.py`, story FR-9):** recebe `linhas` já curtas, calcula `total = len(linhas)` e escreve `(50 de 50)`, rodapé `50 de 50`. Nada diz que houve omissão; o rodapé de truncamento nunca dispara.
- Variante: A devolve tudo e B trunca, mas `M` do rodapé vira soma dos `len` de seções, sem saber se linhas de resumo contam como "casam" (ver S2-2).
- **Correção (AD-2 apertado):** "`Secao(nome, colunas, linhas, total)`. `linhas` é sempre o conjunto completo que casa com os filtros do subcomando; `total = len(linhas)` é preenchido pelo comando. O comando **nunca** aplica `--limit`, `--bytes`, `--all` nem truncamento de linha; só `render.py` corta e calcula `mostradas`. Rodapé: `n` = soma das mostradas, `M` = soma dos `total` das seções de dados." E AD-1: "`args` entregue ao comando não inclui `limit/bytes/all/base`" (ver S1-4).

### S1-2. Quem monta o `Meta` de cada fato e como ele chega ao render

- **ADs:** AD-1 (`consultar(args, mapa)`), AD-3 (`fatos.py` devolve registros e `Meta`), AD-4 (render combina as `Meta`), diagrama de sequência (`C->>R: Resultado e Meta`).
- **Unidade A (`comandos/deps.py`):** recebe `mapa`, chama `mapa.ler("deps.tsv")` e `mapa.ler("_transitivas_comuns.tsv")`; guarda os `Meta` retornados num atributo `Resultado.metas` (nome inventado).
- **Unidade B (`cli.py`):** supõe que `mapa` é só um acessor de dados e coleta `Meta` por conta própria, chamando `fatos.meta(...)` para uma lista fixa de fatos por subcomando que ele mesmo escreveu. Para `deps --todos-modulos` lista os fatos do módulo corrente, não dos N módulos percorridos.
- Resultado: o cabeçalho mostra o estado de um subconjunto dos fatos que de fato foram lidos. É exatamente o que AD-4 diz prevenir.
- **Correção (novo AD-11):** "`mapa` é criado por `cli.py` (via `fatos.abrir(raiz, projeto)`) e **registra cada fato lido**: `mapa.lidos` é a lista ordenada de `Meta`, uma por arquivo de fato efetivamente aberto. `render` recebe `mapa.lidos`; `Resultado` não carrega `Meta`. Comando que lê um fato sem passar por `mapa` é erro." Definir também `Meta.fonte` (ver S1-3).

### S1-3. `Meta` não tem nome/arquivo do fato nem `schema_versao`, mas o envelope e o log exigem ambos

- **ADs:** AD-3 (campos de `Meta`: `confianca, estado, completude, base, desvios, heads, limitacoes`), AD-4 (`# fontes: <fato>(<conf>,<estado>)` e rodapé `fontes: <arquivos>`), AD-9/FR-8 (log traz `schema_versao`).
- **Unidade A (`fatos.py`):** implementa os campos exatos de AD-3.
- **Unidade B (`render.py`):** precisa escrever `deps.tsv(declarada,fresco)` e `fontes: facts/organization/deps.tsv`. Sem `Meta.fato` e `Meta.arquivo`, extrai nome do fato de `Meta.base` (texto livre) ou do nome da função chamada.
- Dois formatos concorrentes: o rodapé usa *arquivos* (caminho relativo a quê?), a linha `# fontes:` usa *fato*. A spine nunca diz que são o mesmo identificador.
- Mesma lacuna para o log: `schema_versao` não está em nenhum tipo.
- **Correção (AD-3):** "`Meta` ganha `fato` (ex.: `deps`), `arquivo` (caminho relativo à raiz do workspace, com `/`), `motivo` (para `indisponivel`, FR-5), `schema_versao` (do índice/`workspace.json` de origem), `gerado`. O rodapé e `# fontes:` usam o mesmo identificador: `<arquivo>`. Formato único: `# fontes: <arquivo>(<confianca>,<estado>) ...`."

### S1-4. Como `--limit/--bytes/--all/--base` chegam (ou não) aos subcomandos

- **ADs:** AD-1 ("expõe `PERGUNTA`, as flags e `consultar(args, mapa)`"), AD-6 (flags sobrescrevem tetos), AD-10 (filtro sempre flag nomeada com mesmo nome).
- **Unidade A (`comandos/config.py`):** declara as próprias flags (`--prefixo`) e, por ser "todos os subcomandos", acrescenta `--limit` e `--all` no seu `argparse` fragment, com `type=int`.
- **Unidade B (`comandos/docs.py`):** não declara as comuns, achando que `cli.py` as injeta.
- Resultado: `config --limit 5` e `docs --limit 5` se comportam diferente; `--base` em B falha com "unrecognized arguments" (argparse sai com código 2 e escreve em stderr, violando AD-5 "canal único").
- **Correção (AD-1 e AD-6):** "As flags comuns (`--limit`, `--bytes`, `--all`, `--base`) pertencem exclusivamente a `cli.py`, que as registra em todo subparser e as consome para montar `Opcoes` entregue ao `render`. O módulo de `comandos/` declara só as flags específicas (`FLAGS`, lista de especificações) e nunca vê as comuns. `--all` com `--limit`/`--bytes`: erro de uso (código 2)." Acrescentar: o argparse deve ser subclassado para que erro de uso saia por `ErroConsulta(2)` em stdout, não stderr (S2-9).

### S1-5. Formato do cabeçalho de seção diverge entre PRD e AD-2

- **PRD FR-1:** `## <nome> (<mostradas> de <total>) <colunas separadas por TAB>` (espaço após o parêntese).
- **AD-2:** `## <nome> (<mostradas> de <total>)<TAB><colunas por TAB>`.
- **Unidade A (golden de `layout`):** segue o AD-2 (a spine vale, PRD §0). **Unidade B (`--help` e exemplo de `snapshots`):** copia o exemplo do PRD. O exemplo do `--help` é caso de aceitação (FR-1); um dos dois falha.
- **Correção:** AD-2 explicita um único exemplo literal com TAB marcado como `\t`, e o PRD é corrigido. "Seção sem colunas (`pacote_base=`) é permitida: cabeçalho `## nome (m de t)` sem TAB."

### S1-6. Erro não carrega `Meta`: cabeçalho de erro e `ausente`

- **ADs:** AD-5 (`ErroConsulta(codigo, mensagem, acao)`, "depois do cabeçalho quando o fato existe"), AD-4 (rodapé em toda saída).
- **PRD:** FR-5 diz "Fato sem dado: `confianca=-` e `estado=ausente`" como saída legítima; FR-1 diz "fato não gerado: código 3".
- **Unidade A (`arestas`, FR-10):** `bytecode_edges.tsv` ausente → `raise ErroConsulta(3, ...)`. `main` captura e imprime só `# erro: ...`; sem `Meta` (não está na exceção), não há cabeçalho, e o log registra código 3 sem `schema_versao`.
- **Unidade B (`callgraph`, FR-14):** fato com `estado=indisponivel` → retorna `Resultado` normal com `motivo` e `comando_sugerido`, código 0.
- Duas saídas incompatíveis para o mesmo tipo de situação ("fato não utilizável"), sem regra de qual é erro. Para `deps`, onde falta `_transitivas_comuns.tsv`, A aborta, B segue com união parcial (o que reabre a armadilha UJ-5).
- Além disso, o rodapé "última linha de toda saída" conflita com o `# erro:` como última linha.
- **Correção (novo AD-12):** "Tabela de estados de leitura: `ausente` (arquivo inexistente) → `ErroConsulta(3)`; `indisponivel` e `nao_aplicavel` → `Resultado` normal (código 0) com o motivo no envelope. Se um subcomando lê vários fatos e **algum** está `ausente`: erro 3 citando qual, nunca união parcial. `ErroConsulta` ganha `metas` (os lidos até ali, preenchidos por `main` a partir de `mapa.lidos`); o render imprime cabeçalho + `# erro:` + rodapé `0 de 0` e depois o código." Fecha também a ordem: erro é a penúltima linha, rodapé a última.

---

## S2 — Divergência de saída e de golden

### S2-1. Teto: por seção ou global? E prioridade entre seções

- **ADs:** AD-2 ("seção cortada continua visível `0 de N`"), AD-6.
- **Unidade A (render):** teto global, enche a primeira seção até 50 e as demais viram `0 de N`.
- **Unidade B (render alternativo/teste):** teto por seção, 50 cada. Pior: em `reactor`, a seção de módulos (poucos) consome o teto e as arestas (a parte útil) saem `0 de N`; em `layout`, o `pacote_base` some.
- **Correção (AD-6):** "Os tetos são globais por invocação, consumidos na ordem das seções. Para evitar que a primeira seção consuma tudo, cada seção de dados recebe antes no mínimo `min(total, 5)` linhas e o restante do teto é preenchido na ordem das seções." Alternativa mais simples: teto por seção. O texto atual não escolhe. `--limit N` tem o mesmo escopo do teto padrão.

### S2-2. Linhas de resumo e linhas "que casam"

- **ADs:** AD-2, AD-4. `tests`, `bytecode`, `callgraph` têm saída-resumo (contagens) sem filtro e linhas com filtro.
- **Unidade A (`tests`):** devolve o resumo como `Secao("resumo", ...)` com 6 linhas; `M` do rodapé = 6.
- **Unidade B (`bytecode`):** devolve o resumo como `avisos` (texto) e `Secao` só quando `--balde`; `M` = 0 no resumo.
- O agente lê "0 de 0 linhas casam" numa consulta com dados: o inverso do propósito do rodapé. Também: resumo conta no teto de 50?
- **Correção (AD-2):** "`Secao.tipo` ∈ {`dados`, `resumo`}. Só `dados` entra em `n`/`M` e no teto; `resumo` sai sempre inteiro (limitado a 20 linhas pelo comando) e é contado à parte: o rodapé fica `# <n> de <M> linhas casam | fontes:` e, se só houver seções `resumo`, `# resumo | fontes:`."

### S2-3. Truncamento de linha corta a marca `[confianca]` e a marca `[heuristica]`

- **ADs:** AD-6 (linha truncada em 240 caracteres com `…`), Conventions (marca `[confianca]` no fim da linha), PRD FR-12 (`alvo_heuristico` sempre com `[heuristica]`).
- **Unidade A (`tests`):** acrescenta `[heuristica]` ao final da última célula. **Unidade B (render):** trunca a 240 caracteres. Linha longa perde a marca, que é a única proteção contra "X está testada". Contagem de "240 caracteres" também é ambígua (caracteres vs bytes; antes ou depois do `tsv_clean`; `--all` desliga ou não).
- **Correção (AD-2/AD-6):** "A marca é uma coluna própria (`marca`, última coluna da `Secao`), preenchida pelo comando; o truncamento age só nas demais células, nunca na marca. O limite de 240 conta caracteres Unicode depois do `tsv_clean`. `--all` remove só os tetos de linhas e bytes; o corte de 240 continua valendo."

### S2-4. "Marca só quando difere do cabeçalho": quem compara?

- **ADs:** Conventions (marca só na linha que difere do cabeçalho), AD-4 (cabeçalho é pior caso), AD-1 (comando é puro e não conhece o cabeçalho).
- **Unidade A (`comandos/deps.py`):** marca `[heuristica]` em toda linha cujo registro tenha `confianca=heuristica`. **Unidade B (`render`):** não interpreta fato e só remove marca se idêntica ao cabeçalho, mas o cabeçalho de `deps` é pior-caso entre dois fatos (`declarada` e `heuristica`), logo as linhas `declarada` do fato bom ficam sem marca, e o agente as lê como `heuristica`.
- PRD ainda manda a marca `[heuristica]` em `tests` *sempre*, contradizendo "só quando difere".
- **Correção:** "Cada linha de `Secao` carrega `confianca` própria (campo opcional, vindo do registro ou de `desvios`), nunca texto. O render compara com a `confianca` **do fato de origem da linha** (`Secao.fonte`), não com o pior caso, e acrescenta a marca. Marcas semânticas (`[transitiva]`, `[provavel_falso_positivo]`) são outra coisa: coluna `marca`, escritas pelo comando, não sujeitas à comparação. Exceção explícita de FR-12: `[heuristica]` sempre."

### S2-5. Pior caso: ordens se contradizem e `completude` não tem ordem

- **ADs:** AD-3 (`estado` final por precedência, em `fatos.py`), AD-4 (render combina pelo pior caso).
- Precedência de FR-5: `ausente/indisponivel/nao_aplicavel` valem como estão e vencem o frescor. Ordem de pior caso: `obsoleto` > `desconhecido` > `ausente` > ... Dois fatos, um `indisponivel`, outro `obsoleto`: A (fatos) diz `indisponivel`; B (render) diz `obsoleto`, e ambos "obedecem".
- `completude` aparece no cabeçalho mas não tem ordem; `parcial` vs `completo` vs ausente?
- **Correção (AD-4):** listar as duas ordens completas, incluindo `completude` (`parcial` < `completa`; ausente é ignorada), e declarar que a ordem vale **só** entre fatos; dentro de um fato vale a precedência de AD-3. Teste: tabela de verdade nas combinações.

### S2-6. `commits_desde_o_mapa` com vários repositórios, e quem chama `git`

- **ADs:** AD-9 (única chamada `git rev-list --count` por repositório), AD-3/AD-4.
- `conflitos` tem 3 heads; `snapshots` tem um por produtor. O cabeçalho tem um único `commits_desde_o_mapa=N`.
- **Unidade A (`fatos.py`):** soma. **Unidade B (`render`):** pior caso (máximo). Qual repositório? E quem executa: `fatos.py` (lê `.git`) ou `render.py` (monta cabeçalho)? `subprocess` não é proibido para `comandos/` pelo teste de AST (ver S3-1).
- **Correção:** "`fatos.py` calcula e guarda em `Meta.commits_desde` (dict repo→N, ou `None`). Cabeçalho: um campo só se há um repositório; com vários, `commits_desde_o_mapa=<repo>:<N>,...` ordenado pela ordem de `Meta.heads`."

### S2-7. Ordem de saída: união de fatos e agrupamento

- **ADs:** AD-6 ("ordem do fato de origem, sem reordenar").
- **`deps`:** lê `deps.tsv` e `_transitivas_comuns.tsv`. A: diretas e depois transitivas. B: intercala por GA. Sem `--todos-modulos` é módulo único; com ele, ordem dos módulos: do `index.json` (`modulos`), alfabética, ou a do `glob`?
- **`snapshots`:** agrupa por produtor; ordem de primeira aparição ou alfabética?
- No mapa real: `facts/_transitivas_comuns.tsv` fica na pasta do **projeto**, não do módulo (verificado em `SawCunhaOS-Flow/.scos-map/facts/`), então a "união" inclui um arquivo compartilhado por todos os módulos: sob `--todos-modulos` ele repete N vezes ou entra uma só?
- **Correção (AD-6):** "Ordem de saída = ordem das seções do comando; dentro da seção, ordem do arquivo; entre módulos, a ordem de `index.json.modulos[]`; agrupamentos preservam a ordem de primeira aparição. Fato compartilhado entre módulos (`_transitivas_comuns.tsv`) é lido e emitido uma vez, em seção própria `transitivas (compartilhadas)`." Cada comando de várias fontes documenta a ordem no `--help`.

### S2-8. O rodapé de truncamento: quem sugere a flag, e onde fica

- **ADs:** AD-6 ("o rodapé sugere uma flag da tabela de FR-2"), AD-1 (comando puro, não sabe se houve corte), AD-4 (render não interpreta fato).
- A: não sugere nada (não sabe do corte). B (render): hardcode `--all`, que está na tabela de FR-2 e portanto cumpre a letra, mas é a pior sugestão (o skill avisa contra `--all`). O PRD também diz que o rodapé "informa N de M quando há omissão" e "sugere": numa linha só, ou em linha separada? Golden diverge.
- **Correção:** "`Resultado.refinar`: lista ordenada de flags sugeridas, preenchida pelo comando, sempre (ex.: `arestas` → `--de`, `--para`, `--pacote`). O render usa a primeira que ainda não foi passada e **nunca** sugere `--all` como primeira opção. Formato: linha própria `# truncado: use --pacote <p>` imediatamente antes do rodapé; rodapé continua uma linha."

### S2-9. `argparse` quebra "canal único" e contrato de código 2

- **ADs:** AD-5 (erro em stdout, código 2 uso inválido), AD-9 (log).
- `argparse` escreve em **stderr** e chama `sys.exit(2)`. Unidade A usa o padrão; unidade B captura `SystemExit`. Em A, o agente recebe saída em stderr sem `# erro:`, sem log; em B, sai `# erro:` em stdout.
- Também: nome de projeto inexistente → código 2 (uso) ou 3 (ausente)? Módulo informado para fato de projeto (`reactor`, `arquivos`)? Hoje: PRD diz projeto/módulo inexistente = 3; argumento sobrando = indefinido.
- **Correção (AD-5):** "`cli.py` usa `ArgumentParser` subclassado cujo `error()` levanta `ErroConsulta(2, ...)`; `--help` é a única saída de `argparse` para stdout e não passa pelo log. Projeto ou módulo que não existem: 3. Argumento posicional a mais ou em falta: 2."

### S2-10. Escopo posicional não está no contrato do módulo (projeto, módulo, `_raiz`, aninhamento)

- **ADs:** AD-1 (contrato: `PERGUNTA`, flags, `consultar`), AD-5 (`resolver(projeto, modulo)`), AD-10.
- Nada diz quais subcomandos são "por módulo". Mapa real: fatos por módulo vivem em `facts/<mod>/` (`_raiz`, `audit`, `infrastructure`, `organization`...) e módulos aninhados aparecem como subpastas (`facts/audit/flow-audit-sdk/`); `_reactor.json` e `_transitivas_comuns.tsv` estão em `facts/`; `files.tsv` na raiz do `.scos-map`.
- **Unidade A (`layout`):** módulo opcional, sem módulo = todos. **Unidade B (`config`):** módulo obrigatório, sem módulo = código 2. **Unidade C (`resolver`):** módulo `audit/flow-audit-sdk` → `facts/audit/flow-audit-sdk/`; **D:** exige id Maven. `_raiz` é nome de módulo digitável?
- **Correção (AD-1 e AD-5):** "Todo `comandos/<x>.py` declara `ESCOPO` ∈ {`workspace`, `projeto`, `modulo`}. `modulo`: módulo posicional obrigatório; módulo = caminho relativo sob `facts/` exatamente como em `index.json.modulos[]` (inclui `_raiz` e `/`); `--todos-modulos` só existe em `deps` e só substitui o módulo. Tabela fixa: workspace = conflitos, snapshots; projeto = reactor, arquivos; módulo = os demais." `resolver` devolve `Caminhos` (nome fixo) e é o único que conhece a árvore.

### S2-11. Cabeçalhos fixos: "seção vazia" e `0 de 0`

- A: seção sem linhas não é emitida (FR-3: "cabeçalho, limitação e rodapé"). B: emite `## conflitos (0 de 0)<TAB>ga<TAB>...`. Golden diverge. Mesma questão: seção que é `0 de N` por corte mostra cabeçalho (AD-2), mas `0 de 0` não.
- **Correção (AD-2):** "Seção com `total = 0` é emitida (`(0 de 0)`) quando o comando a declara; o comando sempre declara as seções do §4.0, mesmo vazias."

### S2-12. Valores de célula: `None`, ausente, inteiro, booleano

- AD-3 "chave ausente como vazio". `Secao.linhas` não declara o tipo da célula. A converte `None` em `""`; B em `-`; o cabeçalho usa `-` para `confianca` ausente. `tsv_clean` sobre inteiro (`bytes` em `config`) levanta `AttributeError` → código 1 em produção.
- **Correção (AD-2):** "Células são `str`; o comando converte. Ausente = `-` em todo lugar (nunca vazio, para a coluna não parecer deslocada)." Revisar AD-3 para que a mesma convenção valha nos leitores.

---

## S3 — Lacunas menores

### S3-1. Teste de AST permeável

AD-1 proíbe `open`, `print`, `sys.stdout`, `os.environ`. Passam: `Path(...).read_text()`, `io.open`, `os.getenv`, `subprocess`, `sys.stderr`, `logging`, `input`. Uma unidade "obedece" e lê arquivo pelo `pathlib`. **Correção:** lista branca de imports em `comandos/` (`modelo`, `fatos` só pelo parâmetro `mapa`, `re`, `typing`, `dataclasses`) em vez de lista negra de nomes.

### S3-2. Registro de comandos x módulos auxiliares

AD-8 define o registro como "a lista dos módulos de `comandos/`". Uma helper compartilhada (`_filtros.py`, para o `--ga` de `deps` e `gerenciadas`) vira "subcomando" e quebra o teste da tabela de 13 linhas; sem helper, `deps` e `gerenciadas` implementam `--ga` com sensibilidade a maiúsculas diferente. **Correção:** helpers vão para `scos_map_query/filtros.py` (fora de `comandos/`), e módulos de `comandos/` começando com `_` não entram no registro. `comandos/tests.py` casa com o padrão de descoberta `test*.py` do `unittest`; considerar renomear o arquivo (`comandos/testes.py`) ou fixar o padrão da suíte.

### S3-3. `--help` e exemplos não têm lugar no contrato

FR-1/FR-6 exigem `--help` por subcomando com formato e exemplo (também caso de aceitação) e ≤ 1.500 bytes; AD-1 só prevê `PERGUNTA`. Uma unidade põe o exemplo em docstring, outra em `AJUDA`. **Correção:** contrato do módulo acrescenta `EXEMPLO` (string literal TSV) e `AJUDA` (≤ 1.500 bytes); `--help confianca` pertence a `cli.py`.

### S3-4. Comparação de `schema_versao` e quem valida

AD-7 usa "Maior/Menor" ambíguos (major/minor ou maior/menor valor?). Comparação por string faz `2.10 < 2.9`. A validação aparece no `cli.py` (diagrama) e em `fatos.py` (Binds). Aviso `# aviso: schema` não tem campo em `Meta` ou `Resultado`. **Correção:** "compara tupla de inteiros `(major, minor)`; quem valida é `fatos.abrir`, que devolve o aviso em `Meta.avisos`; major diferente → `ErroConsulta(4)`."

### S3-5. Log: bytes, linhas, formato e quem fornece o código

AD-9 diz só que `render.py` faz um append. Faltam: formato (TSV? campos e ordem); "bytes" = `len(stdout.encode('utf-8'))` ou só dados; "linhas" = todas ou só `n`; timestamp UTC `Z`; código de saída (o `main` o determina depois do `render` imprimir); `schema_versao` (S1-3); quem lê `SCOS_MAP_QUERY_LOG` e `SCOS_MAP_QUERY_DEBUG`. Erros de uso (2) não sabem subcomando/projeto. **Correção (AD-9):** "Registro TSV: `ts_utc \t subcomando \t projeto \t modulo \t bytes_stdout_utf8 \t linhas_stdout \t codigo \t schema_versao`; `-` para o que não se conhece. `render.emitir(texto_inputs..., codigo)` escreve stdout e log juntos; `main` chama `emitir` em todos os caminhos (inclusive erro 1 e 2). Sem raiz de workspace: não grava (já em FR-8)."

### S3-6. Envelope sem teto: `# fontes:` e rodapé crescem com o número de módulos

AD-2 exclui cabeçalho, limitação e rodapé do teto. `deps --todos-modulos` no Flow (≥ 8 módulos, cada um com 2 fatos) emite dezenas de `fontes`; `# limitacao:` também cresce. Isso foge ao SM-1 sem que o teto veja. **Correção:** "`# fontes:` agrupa por fato (`deps.tsv×8`) e a soma de linhas de envelope é limitada a 12 linhas / 1.500 bytes; excedente vira `… +N fontes`."

---

## O que já está bom e deve ser preservado

- Dependência unidirecional e `render` como único ponto de impressão (AD-1/AD-5).
- `tsv_clean` na saída e `split('\t')` na entrada, simétricos ao gerador (AD-3/AD-6).
- Acesso por nome de coluna (AD-3) e `SCHEMA_TESTADO` como constante única.
- Exceção explícita para `conflitos`/`snapshots` (AD-10), que evita a convenção "projeto obrigatório" onde ela não vale.
- Roteamento com fonte única (`PERGUNTA`) e teste da tabela (AD-8).

## Ordem sugerida de fechamento

1. Fechar os tipos em `modelo.py` (S1-1, S1-2, S1-3, S2-2, S2-12): `Resultado`, `Secao(nome, colunas, linhas, total, tipo, fonte, marca)`, `Meta`, `ErroConsulta`, `Opcoes`. Um único AD "Contrato de tipos", com os campos listados, antes de qualquer story de subcomando.
2. Fixar a divisão de cálculo (S1-4, S2-1, S2-8): comando só filtra e agrupa; render conta, trunca e sugere; `cli` possui flags comuns.
3. Tabela de estados e erros (S1-6, S2-9, S2-5).
4. Ordem de saída e escopo de módulo (S2-7, S2-10), depois as lacunas S3.
