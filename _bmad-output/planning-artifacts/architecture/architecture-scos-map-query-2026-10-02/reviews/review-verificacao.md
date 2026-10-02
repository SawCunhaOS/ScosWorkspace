# Revisão de verificação — ARCHITECTURE-SPINE (scos-map-query)

Lente: cada decisão foi checada contra a realidade (gerador, fatos, mapas), não de memória. Somente leitura. Data: 2026-10-02. Python local: 3.14.4.

**Veredito:** a spine está majoritariamente fiel ao gerador e aos mapas, mas tem um erro concreto nos exemplos (nome do módulo), uma contradição de git/frescor e algumas pressuposições de `Meta` que a realidade não sustenta.

## Alta severidade

### A1. Módulo posicional: a chave real é o caminho relativo, não o nome do artefato
- Evidência: `SawCunhaOS-Flow/.scos-map/index.json` -> `modulos` tem chaves `organization/flow-organization-usecase`, `security/flow-security-starter`, `_raiz`; `workspace.json` -> `projetos[].modulos` idem; o campo `modulo` dentro de cada fato também (`"modulo": "organization/flow-organization-usecase"`); pasta física `facts/organization/flow-organization-usecase/`. Não existe a chave `flow-organization-usecase` isolada.
- Impacto: exemplo `flow-organization-usecase` falha se o `resolver()` casar por igualdade com a chave. Também há agregadores (`organization`, `audit`) com fatos próprios (`facts/organization/deps.tsv`) e `_raiz`.
- Correção: AD-5/AD-10 devem dizer que `modulo` aceita a chave exata e, por conveniência, sufixo único (basename) quando não ambíguo; erro com lista de candidatos se ambíguo/ausente. Confirmar que basenames são únicos nos 3 projetos (no Flow, sim). Atualizar os exemplos.

### A2. Frescor e git: spine e realidade divergem
- Evidência: o gerador nunca usa `git rev-list` (`grep rev-list scos-map.py` -> vazio). Usa `rev-parse HEAD`, `status --porcelain`, `log -1 --format=%H|%at` (scos-map.py:296-343, 3444). O frescor em `fact_state` (scos-map.py:2743-2770) compara blobs de `derivado_de` com `files_by_path` recalculado — o CLI sem git não consegue fazer isso. O protótipo do PRD (`prds/.../prototipo-frescor.py`) lê `.git/HEAD` sem subprocesso e compara com `index.json -> git.head`/`git.dirty`, e introduz o estado `desconhecido`.
- A spine: (a) AD-9 diz que a única chamada de git é `rev-list --count` — mas nenhuma AD explica o frescor por HEAD; (b) AD-3/AD-4 falam em "estado final (precedência de FR-5)" sem citar a fonte (`.git/HEAD`), nem o estado `desconhecido`, que não existe no vocabulário do gerador (`fresco|obsoleto|ausente|indisponivel|nao_aplicavel`); (c) `rev-list --count` aparece sem dizer o intervalo (`<head_gravado>..HEAD`, com head de 12 chars abreviado; funciona se não ambíguo — não verificado; `snapshots_locais.itens[].repo_local.head` tem 12 chars).
- Correção: registrar em AD-3/AD-9 que frescor = leitura de `.git/HEAD` (arquivo, não subprocesso) vs `index.json.git.head/dirty`, listar o vocabulário de `estado` (incluindo `desconhecido`), e definir o uso exato de `rev-list --count`. Dizer que `Meta.estado` por fato vem de `index.json -> modulos.<m>.fatos.<f>.estado` (valor do momento da geração) e que o frescor do CLI é por repositório, não por arquivo.

## Média severidade

### M1. `Meta` pressupõe campos que não existem de modo uniforme
Contagem sobre os 221 JSON de fatos (`facts/**/*.json`) dos 3 mapas:
| campo | presença real |
|---|---|
| `fato`,`modulo`,`base` | 100% |
| `confianca` | 166/221; ausente em `callgraph.json` (todos, são sem dado), em fatos `nao_aplicavel`/`indisponivel` |
| `derivado_de` | 157; ausente em callgraph, em 9 `layout.json` |
| `completude` | só `deps`, `docs`, `tests` (75); `layout`, `config`, `bytecode`, `_reactor` não têm |
| `desvios` | 0 ocorrências hoje (gerador só grava se não vazio: scos-map.py:802) |
| `estado` dentro do fato | só nos sem dado e bytecode/callgraph (82); não é o frescor |
| `frescor` | só `bytecode.json` (27), com forma `{estado, compilado_em}` — e todos hoje `fresco` |
- Impacto: AD-3 diz "chave ausente = vazio" (ok), mas `Meta.estado` "final" não é um campo do fato; `completude` ausente deve ser tratada como "não declarada", não "total". `desvios` nunca foi exercitado em mapa real — só em fixtures; sem golden real.
- Valores reais de `confianca`: `alta|media|resolvida` (CONFIANCAS no gerador; confirmar lista completa — aqui só vi estes três). `completude.nivel`: `total|parcial`.

### M2. `derivado_de` tem três formas, a spine só cobre duas
- Fatos por módulo: dict `arquivo -> blob de 12 chars` (confirmado, ex.: `bytecode.json`: `{"organization/flow-organization-usecase/pom.xml": "23de6f336337"}`). OK com AD-3.
- `workspace.json -> conflitos_de_versao_cruzados.derivado_de`: dict `projeto -> {"head": "ec4075f862c9", "deps_sha": "a98dcba4a1c9"}` — não é `repo->head` (string); é repo -> objeto com dois campos. Se a spine/PRD assume `repo->head` direto, está errado.
- `snapshots_locais`: sem `derivado_de` (chaves: fato, modulo, base, confianca, completude, itens, total, m2); o head fica em `itens[].repo_local.head`. `conflitos_de_versao_cruzados` não tem `estado`.
- Há ainda `derivado_de_agregado` (27 fatos, bytecode) e `assinatura_classes`, que entram no frescor do gerador e que a spine ignora. Como o CLI descarta por arquivo, ok — mas diga isso.

### M3. `tsv_clean`: comportamento exato difere do texto
- `TSV_SEP_RE = re.compile(r"[\t\r\n]+")` (scos-map.py:168) e `tsv_clean` (171-177): **uma sequência** de tab/CR/LF vira **um** espaço (`"a\r\nb"` -> `"a b"`, não `"a  b"`); `None` -> `""`. AD-3/AD-6 dizem "tab, CR, LF viram espaço". Se o render reimplementar por caractere, goldens divergem do gerador. Recomenda-se reutilizar a mesma regex e declarar "sequência vira um espaço".
- Confirmado: `write_tsv` (scos-map.py:180-186) escreve cabeçalho, `\t`.join, `\n`, UTF-8. `split('\t')` é seguro porque toda célula passa por `tsv_clean` (fixture `tsv_campo_com_tab`, fixtures.py:241). Cuidado: `splitlines()` quebra em outros separadores Unicode (U+2028 etc.) — usar `split('\n')`; não verificado se `tsv_clean` cobre esses.

### M4. Corpo do fato nem sempre é TSV; nomes dos arquivos
- Confirmado: TSVs têm linha de cabeçalho. Colunas declaradas em `index.json -> tabelas` (ex.: `files.tsv`: path, blob, bytes, lines, module, kind, last_commit, last_modified, author, commits_90d, tracked; `deps.tsv`: tipo, ga, versao, origem, scope, divergente; `tests.tsv`: path, tipo, alvo_heuristico, linhas, last_modified, commits_90d; `bytecode_edges.tsv`: de, para, tipo, origem; `gerenciadas.tsv`: ga, versao, origem, scope; `_transitivas_comuns.tsv`: ga, versao, scope). Dá para o leitor validar o cabeçalho contra `tabelas` (a spine não aproveita isso).
- Fatos têm campo `corpo`/`corpo_colunas` (62) apontando o TSV; `deps.json` ainda aponta `fecho_comum_arquivo: ../_transitivas_comuns.tsv` — as transitivas comuns não estão em `deps.tsv`. O subcomando `deps` precisa ler os dois, e AD-3 não menciona.
- TSVs com 0 linhas existem (`deps.tsv` de agregadores) — só cabeçalho. Tratar.
- Divergência de nomes: o subcomando `arestas` lê `bytecode_edges.tsv`; `arquivos` lê `files.tsv` (na raiz do `.scos-map`, não em `facts/`). A Structural Seed não registra esse mapeamento.

## Baixa severidade / confirmado

- **Python:** `scos-map.py` parseia com `feature_version=(3,10)` (verificado com `ast.parse`); não usa `match`, `tomllib`, `StrEnum`. Para o CLI: `argparse`, `pathlib`, `json`, `subprocess`, `re` existem em 3.10. Cuidado só com `from __future__`/`X | Y` em anotações (ok em 3.10), `dataclass(slots=True, kw_only=True)` (3.10 ok), `Path.walk` (3.12, evitar), `itertools.batched` (3.12, evitar), `tomllib` (3.11, evitar). A spine diz "≥ 3.10 (ambiente atual 3.14)"; ambiente atual confirmado 3.14.4; o piso 3.10 não foi testado em intérprete real (só parse do gerador). Não há `python_requires` no README do gerador para confirmar o piso.
- `schema_versao`: `SCHEMA_VERSAO = "2.1"` (scos-map.py:40), gravado em `index.json` (2833) e `workspace.json` (3712); os 3 mapas lidos têm 2.1 (`.scos-map/workspace.json`, Flow, Foundation). Confirmado. O valor é string `"2.1"`: comparar como tupla de inteiros, não float (2.10 vs 2.1).
- Chaves de `workspace.json` confirmadas: `schema_versao, gerador_versao, tipo, gerado_em, raiz, como_usar, projetos, descoberta, totais, conflitos_de_versao_cruzados, snapshots_locais, achados`. `projetos[]`: `projeto, index, ecossistemas, arquivos, por_tipo, git, tier_executado, metricas, modulos`. `conflitos` tem `itens[].versoes` (versão -> lista de `Projeto/modulo`), `total`; `snapshots_locais` tem `m2: "~/.m2/repository"` e `total: 10`. Cuidado: a chave `achados` (ciclos de pacote etc.) não é lida por nenhum dos 13 subcomandos — FR coberto?
- **`podar`** (scos-map.py:189-201): remove `None`, `[]`, `{}`, `""`; mantém `False` e `0`. Confirmado, portanto chave ausente = vazio é legítimo (AD-3 correto). Mas a poda é recursiva: um campo `completude.limitacoes: []` pode sumir dentro do objeto.
- **13 subcomandos:** fatos reais por módulo existentes: `layout, config, deps, gerenciadas(tsv), docs, tests, bytecode, callgraph`; de projeto: `_reactor.json`, `files.tsv`; de workspace: `conflitos_de_versao_cruzados`, `snapshots_locais`; `arestas` = `bytecode_edges.tsv`. Coerente (13). `config.json` só em 20/41 e `docs.json` só em 13/41 — o leitor precisa tratar "fato ausente" por módulo como `ausente` (já previsto).
- **Seed:** `ferramentas/scos-map/` tem `README.md, scos-map.py, tests/{fixtures.py,test_scos_map.py}`; `scos_map_query/`, `scos-map-query.py` e `.claude/skills/scos-query` não existem ainda (esperado, é o alvo). Skills `scos-map` e `scos-map-build` existem em `.claude/skills/`. O arquivo de testes é monolítico (`test_scos_map.py`, 35.9K) — "suíte ganha testes do CLI" ok.
- **Callgraph:** `callgraph.json` do `usecase` está `estado: indisponivel` ("java-callgraph.jar nao encontrado") com `lacunas_conhecidas` — Deferred em FR-14 coerente; nenhuma fixture de callgraph disponível não foi verificada em `fixtures.py` (a lista de funções não tem uma explícita; só `jdeps_falso`, `bytecode_sem_aresta`).
- **Tamanho:** `index.json` do Flow tem 31 KB; o `files.tsv` do Flow tem 217 KB; ler `files.tsv` inteiro por chamada é viável, mas a medição "≈ 10 ms" (Deferred) não pôde ser reproduzida aqui.
- **Mermaid (3 blocos):** não renderizei (sem `mmdc` local). Leitura: `graph LR` e `graph TD` com rótulos entre aspas e `<br/>` — válidos; o rótulo de aresta `|"cabeçalho # aviso # limitacao<br/>..."|` contém `#`, que o Mermaid usa para entidades (`#35;`); sem `;` não deve quebrar, mas é o ponto de maior risco — troque por "aviso e limitacao". `sequenceDiagram`: participantes e mensagens bem formados; `C->>C` (auto-chamada) é válido; `[modulo]` e `[--flags]` no texto da mensagem são aceitos. Nenhum erro sintático identificado por inspeção; renderização real não confirmada.
- A tabela de camadas diz que `fatos.py` "devolve `Meta` com `estado` final", mas o Seed descreve `fatos.py` como "leitores de fatos + frescor" — consistente, porém contradiz AD-4 "não recalcula frescor" apenas aparentemente (render não recalcula, fatos sim). Vale esclarecer.

## Não confirmado / possivelmente desatualizado
1. Lista completa de valores de `confianca` (vi `alta|media|resolvida`; `CONFIANCAS` no gerador não foi lido por inteiro).
2. `rev-list --count <head12>..HEAD` com hash abreviado e repos com árvore suja (os 3 repos estão com `dirty: true` hoje; `fatos_obsoletos: 0` no workspace mesmo assim).
3. Piso Python 3.10 em intérprete real.
4. Unicidade do basename de módulo entre projetos (Foundation e BOM não foram varridos para colisão).
5. Render dos diagramas Mermaid.
