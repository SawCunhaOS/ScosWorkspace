# Revisão (rubric walker) — ARCHITECTURE-SPINE scos-map-query

Data: 2026-10-02. Somente leitura sobre a spine. Fontes cruzadas: `prd.md`, `addendum.md`, `.memlog.md` da spine, `ferramentas/scos-map/scos-map.py` (SCHEMA_VERSAO = "2.1", confirmado) e `ferramentas/scos-map/tests/` (unittest, `fixtures.py`, `README.md`).

## Veredito

Spine sólida no paradigma (pipeline com renderizador único), com 10 ADs bem escolhidos, cobertura completa de FR-1..FR-14/NFR-1/NFR-2 no mapa e diagramas mermaid válidos. Mas o contrato entre `comandos/` e o resto (o que é `mapa`, onde moram flags/ajuda/aviso, como as `Meta` chegam ao renderizador) está aberto, e há pontos de formato e teste que fariam stories independentes divergirem. Aprovada com ressalvas: corrigir os achados high antes de fatiar em stories. Nenhum critical.

## Resumo do checklist

| Item | Resultado |
| --- | --- |
| Fixa os pontos reais de divergência, sem omitir | Parcial (H1, H3, H4, H5, M1, M2, M3) |
| Rule aplicável/testável e previne o declarado | Parcial (AD-1 tem brecha, AD-6 colide com marcas, AD-4 sem semântica de n/M) |
| Deferred não faz unidades divergirem | OK, com ressalva (M7: formato do log é pré-requisito do `gain`) |
| Tecnologia nomeada com versão verificada | Parcial: schema 2.1 verificado no gerador; "Python ≥ 3.10" não verificado (M8) |
| Ratifica o código existente | OK no schema, `tsv_clean`, poda de chaves, unittest; tensão com `fixtures` (H6) |
| Cobre FR-1..14, NFR-1, NFR-2 | OK nominalmente; FR-2 (flags globais), FR-11 (limites) e NFR-2 sem mecanismo (M5, M6) |
| Operação/ambiente decidida | OK ("não se aplica" explícito), mas faltam `.gitignore` e codificação (M9, M10) |
| Mermaid válido e coerente | Sintaxe válida; 2 incoerências com ADs (L1, M4) |
| Contradições com o PRD sincronizado | H3 (formato do título de seção), H6 ("sem fixtures novos") |

## Achados

### HIGH

**H1. O contrato de `comandos/<x>.py` está incompleto e a pureza de AD-1 contradiz a dependência `comandos → fatos`.**
- Por quê: AD-1 diz que o módulo expõe `PERGUNTA`, "as flags" e `consultar(args, mapa) -> Resultado`, "função pura". Mas (a) `mapa` nunca é definido (objeto com métodos de leitura? dict de registros?), (b) o diagrama e a regra de dependência mandam `comandos → fatos`, ou seja, o comando chama o leitor, que abre arquivo: não é pura, e a tabela de camadas diz "E/S de qualquer tipo: não faz"; o memlog falava em `(registros, Meta) -> Resultado`. (c) AD-4 faz o renderizador combinar as `Meta` de todos os fatos lidos, mas `Resultado` (AD-2) carrega só seções, avisos e limitações, sem `Meta`; no diagrama de sequência o `cli.py` lê os fatos antes de saber quais o subcomando precisa (`deps` lê três). (d) Flags, texto de `--help` por subcomando, exemplo de 3 a 5 linhas (caso de aceitação de FR-1/FR-6) e `# aviso:` de ≤100 bytes (FR-5) não têm lugar declarado: "expõe as flags" não diz se é lista declarativa ou função que configura o parser. Treze stories independentes vão inventar treze formas.
- Menor correção: acrescentar a AD-1 a assinatura exata: constantes `PERGUNTA`, `FLAGS` (lista de `(nome, tipo, ajuda)`), `AJUDA`, `EXEMPLO`, `AVISO`; `consultar(args, mapa)` onde `mapa` é um objeto de `fatos.py` com um método por fato (`mapa.fato("layout", projeto, modulo) -> (registros, Meta)`) que **registra** cada `Meta` lida; `Resultado` ganha `metas: list[Meta]` preenchida por esse registro, e o contexto (subcomando, projeto, módulo, schema) para o log. Assumir que "pura" significa "sem E/S própria, só via `mapa`" e reescrever a tabela de camadas assim.

**H2. O corte de linha em 240 caracteres (AD-6) pode apagar a marca `[confianca]`, que fica no fim da linha.**
- Por quê: a convenção de dados põe `[heuristica]`/`[confianca]` ao final da linha só quando difere do cabeçalho; FR-12 e FR-14 dependem dessa marca para impedir "X está testada". AD-6 trunca a linha em 240 caracteres com `…`, e `alvo_heuristico`/`path` longos estouram isso. A marca some silenciosamente, violando SM-C1. A spine não diz quem anexa a marca (comando ou renderizador; o renderizador "não interpreta fato") nem a ordem truncar versus marcar.
- Menor correção: em AD-6, truncar as células de dados **antes** de anexar a marca, ou tornar a marca uma coluna própria final (`confianca_linha`), e declarar que o comando preenche a marca em `Secao.linhas` e o renderizador nunca a corta. Teste: linha com 300 caracteres mantém a marca.

**H3. Título de seção: a spine (TAB) e o PRD (espaço) divergem, e `n de M` do rodapé não tem semântica.**
- Por quê: AD-2 define `## <nome> (<mostradas> de <total>)<TAB><colunas por TAB>`; FR-1 do PRD escreve `... de <total>) <colunas separadas por TAB>` (espaço). Os goldens fixam bytes, então uma das duas versões quebra. Além disso AD-4 e AD-2 não dizem o que é `n` e `M` no rodapé `# <n> de <M> linhas casam`: n é mostradas ou casadas? M é total do fato ou total após o filtro? O PRD (FR-3: `0 de 0`; FR-9: `N de M quando há omissão`) é ambíguo e FR-9 manda o teto valer globalmente por ordem (memlog, opção iii), regra que nem AD-2 nem AD-6 repetem: `--limit` é por seção ou global?
- Menor correção: escolher TAB (coerente com "colunas por TAB") e corrigir o PRD FR-1; definir em AD-4: `n` = linhas **mostradas** somadas, `M` = linhas que casam o filtro somadas (antes do teto), e em AD-6 que o teto e `--limit` são globais, consumidos na ordem das seções, e `(mostradas de total)` por seção usa o mesmo `total` pós-filtro.

**H4. Erros: `ErroConsulta` não consegue emitir o cabeçalho, e o `argparse` fura o "canal único".**
- Por quê: AD-5 manda o erro sair depois do cabeçalho "quando o fato existe", mas `ErroConsulta(codigo, mensagem, acao)` não leva `Meta`, e capturar só em `main` perde as `Meta` já lidas. O `argparse` por padrão escreve erro de uso em **stderr** e sai com 2, contrariando "erro em stdout, mesmo renderizador, mesmo log" (FR-1) e não passa pelo log. Também não se diz quem converte código em `sys.exit` (render ou main) nem se `--help` (stdout, exit 0) é logado.
- Menor correção: `ErroConsulta` ganha `metas` opcional (preenchido pelo `mapa` de H1); `cli.py` usa `ArgumentParser` subclassado com `error()` que levanta `ErroConsulta(2, ...)`; `main` é o único que chama `sys.exit(codigo)`, depois de `render`. Dizer se `--help` é logado (sugestão: não).

**H5. Resolução de módulo e fatos por módulo não estão decididos (ponto de divergência do `resolver()` e dos comandos).**
- Por quê: AD-5 faz `resolver(projeto, modulo)` a única montagem de caminho e AD-10 diz "módulo opcional só nos fatos por módulo", mas a spine não lista quais fatos são por módulo (config e docs moram em `facts/_raiz/`; layout/deps/tests/bytecode/arestas/callgraph por módulo), nem como se nomeia o módulo (id do reactor, caminho `organization/flow-organization-usecase`, módulo aninhado `facts/<a>/<b>/` coberto por fixture existente `workspace_modulos_aninhados`), nem o que acontece se o módulo é omitido num fato por módulo (erro 2? agregado do projeto? `_raiz`?). Isso é exatamente onde duas stories divergem.
- Menor correção: em AD-5/AD-10 acrescentar tabela subcomando → escopo (`_raiz`, módulo obrigatório, módulo opcional, workspace) e a regra de identificação do módulo (id do `index.json`); módulo omitido em fato por módulo = exit 2 com a lista de módulos válidos (ou `_raiz`, mas decidir).

**H6. Determinismo dos goldens e do benchmark SM-1 não está resolvido; "sem fixtures novos" é falso na prática.**
- Por quê: (a) os fixtures geram mapas rodando o gerador, então `gerado_em`, `head` de git e `commits_desde_o_mapa` variam por execução e por ambiente (com ou sem `git` no PATH o cabeçalho muda, FR-5), portanto golden byte-a-byte falha ou exige normalização que a spine não define; (b) `--help` por `argparse` muda entre 3.10 e 3.14 (formatação de uso/metavar), e o golden do `--help` mais o teto de 1.500 bytes ficam presos à versão do Python, embora a Stack aceite ≥ 3.10; (c) o benchmark SM-1 do PRD foi medido sobre o mapa **real** (958KB, `jq`), mas a spine manda o teste usar `fixtures.py` sintético: os mapas sintéticos não reproduzem Q9/Q10, 12 de 12 ≤ 10% do `Read`, nem as contagens esperadas; não se diz se roda contra o mapa real (não hermético, defasado) ou contra fixture; (d) a linha "Testes" diz "sem fixtures novos", mas o Deferred manda a primeira story de FR-14 criar fixture de callgraph e SM-C1 exige fixtures de `obsoleto`, `resolvida`+`parcial`, HEAD ilegível e estado misto (Q8).
- Menor correção: AD-6 (ou novo AD de testes) declara: relógio e HEAD injetáveis (`SCOS_MAP_QUERY_NOW`/normalização de `gerado=` e `commits_desde_o_mapa` nos goldens), `--help` com texto fixo (constante `AJUDA`, `RawDescriptionHelpFormatter`) para ser independente da versão do Python; benchmark SM-1 hermético com fixture sintético dimensionado ou marcado como teste opcional contra o mapa real; trocar "sem fixtures novos" por "fixtures novos só em `fixtures.py`".

### MEDIUM

**M1. AD-1 tem brecha: a lista proibida (`open`, `print`, `sys.stdout`, `os.environ`) não cobre `Path.read_text/open`, `subprocess`, `os`, `sys.exit`, `io`.** Um comando passa no teste e ainda faz E/S. Correção: o teste de AST inverte a regra para permitir-lista de imports em `comandos/` (`modelo`, `fatos`, `re`, `typing`, `collections`...), ou amplia a lista proibida.

**M2. Quem chama `git rev-list --count` e onde mora `commits_desde_o_mapa`?** AD-9 permite a chamada, mas nenhum módulo é dono (a tabela de camadas só deixa `fatos.py` abrir arquivo), e `Meta` (AD-3) não tem o campo. Correção: `fatos.py` dono da leitura de `.git/HEAD` e do `rev-list`; `Meta.commits_desde_o_mapa` (opcional, omitido sem `git`).

**M3. Formato do log e dados de contexto não decididos.** FR-8 pede timestamp, subcomando, projeto/módulo, bytes, linhas, código de saída e `schema_versao`; AD-9 só fixa local e "uma chamada de escrita em append". O formato (TSV? campos? ordem) é pré-requisito do futuro `gain` (Deferred) e `Resultado` não carrega projeto/módulo/schema. Correção: acrescentar em AD-9 a linha de log TSV com colunas nomeadas e escrever com um único `os.write` em `O_APPEND` (um `print` com buffer pode intercalar).

**M4. Quem valida o schema?** O diagrama de sequência diz `C->>C: resolver() e valida schema` (cli), AD-7 liga a validação a `fatos.py`. Além disso AD-7 ("Maior igual: aceita. Menor mais novo...") é telegráfico e não trata minor **mais antigo** que 2.1 (ex.: 2.0, sem `snapshots_locais`?). Correção: validar em `fatos.py` ao abrir `index.json`/`workspace.json`; reescrever como "major igual a 2: aceita; minor > 1: aviso; minor < 1: aviso `mais velho`".

**M5. NFR-2 (≤ 300 ms) tem "governança" apenas nominal ("AD-3, só lê o necessário") e nenhum teste.** AD-3 não diz isso, e o custo de `subprocess git rev-list` por repositório (3 chamadas em `conflitos`) não está nas medições do addendum (que mediu só leitura de `.git/HEAD`). Correção: teste de latência simples na suíte (limite generoso, ex.: 300 ms em `layout`/`arestas` no fixture) e medir o `rev-list`; opcional `commits_desde_o_mapa` só quando barato.

**M6. Flags globais e FR-11 sem dono.** `--limit/--bytes/--all/--base` (FR-2) valem para todos os subcomandos, mas AD-10 e a convenção de nomes só falam de filtros; ninguém declara que `cli.py` os injeta em cada subparser. Os limites de FR-11 (descrição ≤300, corpo ≤30 linhas/2.000 caracteres, `--help` ≤1.500 B, `--help confianca` ≤2.500 B) e o teste "toda linha da tabela tem subcomando ou exceção motivada" (FR-7) não aparecem na linha "Testes". Correção: acrescentar a AD-8/AD-10 e à linha "Testes".

**M7. Deferred toca o contrato futuro.** "Comando gain" depende do formato do log (M3), que deve ser decidido agora; "Fixture de callgraph" bifurca o escopo de FR-14 (implementar ou não o ramo `disponivel`), o que é aceitável, mas anotar que o ramo disponível fica atrás de `estado == disponivel` com ou sem fixture, para duas stories não divergirem. "Operação e ambiente" não é adiamento, é decisão "não se aplica"; remover da lista de Deferred para não confundir.

**M8. "Python ≥ 3.10" sem verificação.** O gerador usa `from __future__ import annotations` e stdlib, mas a spine não registra que o piso foi testado (ex.: `vermin` ou execução em 3.10); só o 3.14.4 foi observado. Correção: marcar como "não verificado em 3.10" ou verificar; ligado a H6(b).

**M9. Artefatos fora do pacote sem dono.** O `.gitignore` do workspace não lista `.scos-map-query.log` (FR-8 exige), nem a edição de `AGENTS.md` (1 linha) e da descrição de `scos-map-build` aparecem no Structural Seed. Correção: acrescentar ao Seed.

**M10. Codificação e quebra de linha da saída não são fixadas.** `…` e acentos em stdout dependem do locale; goldens e o teto em bytes (6.000) são em bytes UTF-8. Correção: `render.py` reconfigura `sys.stdout` para UTF-8 e `\n`, e conta bytes em UTF-8.

### LOW

**L1. Diagrama 1 omite a chamada a `git` e a leitura de `.git/HEAD` (AD-9/AD-3) e mostra `Resolver` fora de módulo; o diagrama 2 chama `CLI` de "scos-map-query" com `scos-map` antigo apontando; coerente, mas sem as setas de erro.** Sintaxe dos dois blocos mermaid e do sequenceDiagram é válida.

**L2. Teto de dados (AD-2/AD-6) exclui "cabeçalho, limitação, títulos, rodapé" mas não cita `# aviso:`, `# fontes:`, `# erro:`.** Dizer que toda linha `#` não conta.

**L3. Autoridade circular.** O PRD diz "vale a spine" e a spine delega ordens de pior caso a FR-5 do PRD (AD-4). Copiar as duas listas de ordem para a spine ou declarar FR-5 como parte normativa.

**L4. Importação nos testes.** A suíte roda com `unittest discover -s tests -t tests` e carrega o gerador por `importlib` (hífen); `scos_map_query` está um nível acima. Dizer que os testes do CLI chamam o entry por `subprocess` (como já fazem para o gerador) ou inserem `RAIZ` em `sys.path`.

**L5. `allow_abbrev` do argparse** aceita `--com` por prefixo e contraria "flags congeladas". Desligar (`allow_abbrev=False`).

## O que já está bom (preservar)

- Paradigma de renderizador único e a regra "só `fatos.py` abre arquivo, só `render.py` imprime" com teste de AST.
- Leitura de TSV por nome de coluna, descarte de `derivado_de`, chave ausente = vazio (ratifica a poda do gerador); `split('\t')` seguro porque o gerador neutraliza tab/CR/LF.
- `SCHEMA_TESTADO = "2.1"` em um só lugar, igual ao `SCHEMA_VERSAO` do gerador; revisão obrigatória ao evoluir.
- AD-8 (`PERGUNTA` como fonte única do roteamento, teste tabela-da-skill = registro) e AD-10 (exceção explícita de workspace).
- Mapa Capability→Architecture cobre todas as FR/NFR; "Operação e ambiente" declarada explicitamente.
