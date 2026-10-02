# Revisão adversarial geral, rodada 3: PRD "Scripts de Consulta Rápida para scos-map"

Escopo: `prd.md` (319 linhas), `addendum.md`, `.memlog.md`, `benchmark-baseline.py`, `prototipo-frescor.py`. Verificado contra `ferramentas/scos-map/scos-map.py`, `SawCunhaOS-*/.scos-map`, `.scos-map/workspace.json`, `.claude/skills/scos-map/SKILL.md`, `.claude/skills/scos-map-build/SKILL.md` e `AGENTS.md`. O review da rodada 2 só foi lido depois de formada esta visão (ver "Delta vs rodada 2").

## Veredito

Sem críticos. A PRD amadureceu (envelope, tetos, filtros em tabela, benchmark com 12 perguntas). Mas ainda **não está pronta para `bmad-build`**: tem 7 achados altos. Os mais graves: a premissa de FR-7 sobre o `AGENTS.md` é falsa; o frescor barato é cego ao caso de uso real e hoje devolve "obsoleto" em 100% da amostra; FR-12/13/14 furam o "conjunto fechado e congelado" de FR-2; a meta de SM-1 passa por zero margem. O escopo cresceu (13 subcomandos, 13 goldens, `--help` absorvendo ~20 linhas do inventário, FR-14 sobre um fato que está `indisponivel` em todos os módulos) sem que o ganho esperado tenha crescido junto.

Contagem: 0 críticos, 7 altos, 8 médios, 6 baixos.

---

## ALTO

### H1. Frescor barato: cego ao caso real, 100% "obsoleto" na amostra e falso-fresco com mapa gerado sujo
- Onde: FR-5 ("Igual → `fresco`; diferente → `obsoleto`"), FR-4, Glossário "Frescor barato", addendum "Verificação do frescor barato".
- Evidência: o addendum mostra os 3 repositórios `obsoleto` (taxa de 3/3, uma amostra de 3). A UJ-2 ("posso confiar no `-SNAPSHOT` antes do `mvn clean install`?") responde hoje `obsoleto`. Um sinal que sempre dispara não informa e treina o agente a ignorá-lo. Os 5 commits novos da Foundation são de docs, ou seja, falso-obsoleto medido, não hipotético.
- Pior: o inverso é aceito. O agente trabalha **no meio de uma story** (UJ-1), com alterações não commitadas, e o CLI diz `fresco`. A limitação "não detecta alterações não commitadas" vai só no corpo de FR-5 e na saída "quando o fato foi gerado com árvore suja". Os três mapas atuais têm `git.dirty=true` (verificado em `SawCunhaOS-Flow/.scos-map/index.json`) e o `conflitos_de_versao_cruzados` declara "o fato nao corresponde a nenhum commit". Se o HEAD coincidir com o gravado, o envelope sai `estado=fresco` para um fato gerado de árvore suja. Isso é falso-fresco, a pior direção.
- Correção: (a) fato com `git.dirty=true` nunca sai `fresco`; rebaixar para `desconhecido` ou acrescentar um valor explícito. (b) Opcional e barato: permitir um único `git rev-list --count <head>..HEAD` quando `git` existe, para dar "N commits desde o mapa" (o agente julga se é só doc). Cair para a leitura de `.git/HEAD` só sem git. A proibição absoluta de subprocesso troca informação por 5 ms. (c) Medir a taxa de falso-obsoleto em mais de 3 pontos (o `git log` já mostra).

### H2. FR-7 afirma "A tabela de `AGENTS.md` tem 12 linhas": ela tem 7. E 13 subcomandos não casam com 12 linhas
- Onde: FR-7 ("A tabela de `AGENTS.md` tem 12 linhas e todas têm subcomando no MVP"), addendum inventário ("Roteamento (12 linhas) | skill `scos-query` ... e `AGENTS.md`").
- Evidência: `AGENTS.md` linhas 74 a 82 têm 7 linhas (layout, config, deps, gerenciadas, docs, reactor, arquivos). Faltam testes, conflito cruzado, snapshots, bytecode e callgraph. As 12 linhas estão no `SKILL.md` (linhas 63 a 74), não no `AGENTS.md`. Logo FR-7 implica editar `AGENTS.md` (acrescentar 5 linhas), mas isso não está dito, e o teste "falha se houver linha sem subcomando" olharia uma tabela que não existe.
- Além disso: §6.1 e FR-1 listam **13 subcomandos** (inclui `arestas`), FR-7 exige "uma linha por subcomando" na skill, mas fala em 12 linhas. A linha "quem referencia quem, ciclos, higiene de dependência" do `SKILL.md` aponta para `bytecode.json`, e `arestas` (bytecode_edges.tsv) não tem linha de roteamento própria. Qual subcomando a linha 73 roteia, `bytecode` ou `arestas`?
- Correção: corrigir o texto para "7 linhas hoje; a PRD acrescenta 5"; decidir se `arestas` tem linha própria (13 linhas) e ajustar FR-7, FR-11 e o inventário.

### H3. FR-5: precedência do `estado` ignora fatos que já trazem `estado`/`frescor` próprios, e a ordenação de pior caso é incompleta
- Onde: FR-5 ("se o fato grava `estado`, é esse"; ordem "`obsoleto`, `desconhecido`, `ausente`, `indisponivel`, `fresco`").
- Evidência: `bytecode.json` real tem `estado: "disponivel"` **e** `frescor: {"estado": "fresco", "compilado_em": ...}`. Pela regra, o envelope diz `estado=disponivel` e a obsolescência do bytecode (o `target/classes` compilado antes das mudanças) nunca é calculada nem mostrada. `disponivel` e `nao_aplicavel` constam do vocabulário do Glossário, mas faltam na lista de pior caso, então `deps` + `bytecode` numa mesma consulta não tem ordem definida. O callgraph real é `estado: "indisponivel"`: cabeçalho `confianca=-`, mas o `# fontes:` precisa dizer isso.
- Contradição residual: o exemplo de FR-3 mostra `estado=fresco`. O `conflitos_de_versao_cruzados` real tem `derivado_de` com os heads dos 3 repositórios (`ec4075f862c9`, `a8e5569a595a`, `e03ad8ce65a2`), e todos já diferem dos HEADs atuais (addendum). O cabeçalho verdadeiro hoje seria `obsoleto`. O exemplo escolhido ilustra o caso que o addendum prova inexistente. Também não está dito como se compara um fato com 3 heads (suponho pior caso, mas é só suposição).
- Correção: tabela única de precedência (fato.estado, fato.frescor.estado, head), lista de ordenação completa com todos os valores, e trocar o exemplo de FR-3 por `obsoleto`.

### H4. FR-12/13/14 (e FR-1, FR-4) furam o "conjunto fechado e congelado" de FR-2
- Onde: FR-2 ("O conjunto abaixo é fechado e congelado"), FR-12 (`--arquivos`), FR-13 (`--balde`), FR-14 (`--de`, `--para`, `--entrypoints`, `--lacunas`, `--sem-chamador`), FR-1 (`--base`), FR-4 (`--detalhe`), FR-9 (`--limit`, `--bytes`, `--all`).
- Problemas concretos:
  1. FR-2 diz que é congelado, mas a tabela só tem 4 linhas e cada FR novo cria flags de filtro. São ≥10 flags nominais fora do congelamento. Ou o congelamento é falso ou FR-12/13/14 violam a PRD.
  2. FR-12 diz "Zero arquivos de teste **para um alvo**", mas não existe flag de alvo (`--alvo`?). O comportamento não é especificável.
  3. Inconsistência de interface: FR-1 manda projeto e módulo como **posicionais**, FR-2 usa `arquivos <projeto> --modulo organization` (flag) e `deps <projeto> --todos-modulos`. Um agente (e um golden test) precisa de uma regra única.
  4. FR-9 diz que o rodapé indica "um filtro do conjunto de FR-2 ou FR-10", mas `tests`, `bytecode`, `callgraph` truncados não têm filtro nesse conjunto.
- Correção: redefinir o congelamento como "filtros de **bytes/linhas por pergunta** definidos nas tabelas de cada FR" e listar todas as flags numa tabela única; definir `--alvo` ou remover a promessa; escolher uma convenção módulo posicional vs flag.

### H5. SM-1 e o benchmark: meta no limite, baselines inflados e asserções fracas
- Onde: SM-1, addendum "Medições", `benchmark-baseline.py`.
- Pontos verificados:
  1. **Zero margem pós-hoc.** "JSON: CLI ≤ `grep` em ≥ 80% das perguntas com `grep` possível (hoje 5 perguntas, 4 de 5)". 4/5 é exatamente 80%, e o proxy é "o piso ideal". A Q2 está em 0,93× (581 B contra 622 B, 41 B de folga). Qualquer byte a mais no envelope real (por exemplo a linha `# fontes:` de FR-5 ou `[heuristica]`) reprova a meta. A meta foi calibrada para o dado, não para o objetivo; o critério de decisão do que fazer se estourar é "recalibrar a meta ou enxugar o envelope", ou seja, nunca falha.
  2. **`grep` não equivalente.** Q4 compara `gerenciadas.tsv` com `grep` no `pom.xml`; Q5 devolve só nomes de arquivo (sem título); Q11 devolve imports. O addendum admite Q11, mas conta Q5 e Q4 como vitórias de bytes sem ressalva.
  3. **Baseline do `Read` inflado.** O ganho "0,3% a 5,5%" supõe um `Read` do fato inteiro. O próprio addendum marca `[não verificado]` que o `Read` tem limite de tamanho (e arquivos de 142KB e 958KB provavelmente nem são lidos inteiros). O headline de 12/12 ≤ 10% mede um agente que não existe. O comparador honesto é o `grep` (e `jq`), onde o resultado é 4/5 no limite. Q11 soma `tests.json` + `tests.tsv` ao `Read`, mas a resposta só precisa do JSON; Q3 soma `deps.json`. Bytes divididos por 3,5 como tokens também é frágil para JSON minificado.
  3b. **Q3 não exercita a armadilha das transitivas.** O `_transitivas_comuns.tsv` do Flow tem 52 B, e `facts/_raiz/deps.tsv` tem só o cabeçalho. A "união" que justifica o CLI contribui com zero linhas na amostra. E `add(...) if L else None` no script pula a pergunta em silêncio se `L` ficar vazio.
  4. **Asserção de conteúdo trivial.** `add()` só testa `esperado in o` com uma substring (`"domain"` na Q6, `"pacote_base"` na Q1, `"annotations"` na Q7). FR-6 promete "asserção de conteúdo contra a resposta esperada"; o benchmark atual não compara a resposta, e uma saída errada com essa substring passa.
  5. **Q7, Q8, Q12 não têm `grep`**: ficam fora do critério de ≥80%, de modo que as perguntas de maior valor (cruzadas) não pesam na meta que decide sucesso.
- Correção: definir a meta de JSON como "nenhuma pergunta de JSON > 1,6× `grep`" ou "soma"; ou aceitar explicitamente que JSON é paridade e vender acurácia. Trocar o baseline de `Read` por "`Read` com limite padrão da ferramenta, mais a segunda leitura" ou remover o 10% como meta. Comparar a resposta por conjunto de linhas esperadas (golden), não substring. Gerar uma pergunta com transitivas reais.

### H6. FR-11: as regras de interpretação migram para `--help`, que o agente só vê se pedir
- Onde: FR-11 ("As regras de interpretação ... viram comportamento do CLI e `--help`"), addendum inventário (Regras 4 e 5, Documentação, Testes, Dependências no bytecode.json).
- Problema: o inventário prova "nenhuma seção se perde", mas só no destino formal. As regras 4 ("doc antiga ao lado de código recente"), 5 ("histórico de arquivo não está no mapa") e "Documentação (subtipos, frontmatter literal)" ficam apenas em `--help docs` / `--help arquivos`, e nenhum requisito faz a saída carregar essa advertência. A skill de 30 linhas / 2.000 caracteres não as tem. Um agente que chama `docs` sem `--help` nunca as lê, e o único sinal embutido (envelope) não cobre essas regras. Só FR-12/13/14 transformam regra em comportamento da saída.
- Também: (i) a descrição de ≤160 caracteres para `scos-map` e `scos-query` reduz a capacidade de disparo (a atual tem ~380 caracteres e lista os gatilhos); duas skills com descrições curtas e sobrepostas competem para disparar. (ii) FR-11 diz "A skill `scos-map-build` não é alterada", mas a descrição dela (`SKILL.md`, frontmatter) manda "Para apenas LER o mapa ... use a skill scos-map"; com `scos-map` virando ponteiro, o encaminhamento passa por dois saltos, e `AGENTS.md` também cita `scos-map` como skill de consulta. (iii) 2.000 caracteres contendo 12 ou 13 linhas de tabela, comando literal, aviso de `--all`, aviso de tamanho de fato, "perguntas abertas" e a regra de chamada são apertados; não está dito se o frontmatter conta no limite. (iv) `scos-query` não tem localização definida (`.claude/skills/scos-query/`?).
- Correção: para cada regra que hoje só ficaria em `--help`, decidir entre uma linha `# aviso:` na saída do subcomando (preferível, custa bytes só quando relevante) ou uma linha na skill; ajustar o inventário. Reescrever o teste para checar que a regra aparece na saída ou na skill, não só no `--help`.

### H7. FR-14 (callgraph) é especificado sem dado real e sem formato de fixture
- Onde: FR-14, addendum "Pendências", FR-1 (linha `callgraph`).
- Evidência: em todos os 8 módulos Flow o `callgraph.json` é `estado: "indisponivel"` ("java-callgraph.jar nao encontrado") e não existe `callgraph_edges.tsv` (o PRD admite). O gerador (`scos-map.py` ~linhas 2506 a 2536) emite o arquivo, as `arestas_ambiguas`, `entrypoints`, `metodos_sem_chamador`, mas FR-14 diz "colunas conforme o cabeçalho do arquivo". Isso é inverificável: o teste usaria "um fixture gerado" por quem implementa, que reflete o entendimento do implementador e não o do gerador. O contrato de FR-6 ("golden que falha em qualquer mudança") fica ancorado em um arquivo inventado.
- Correção: gerar o fixture a partir do gerador (reaproveitar `tests/fixtures.py`) ou fixar as colunas na PRD copiando-as do código do gerador; senão rebaixar FR-14 no MVP ao caso `indisponivel` (estado, motivo, comando sugerido), que é o único real, e deixar arestas para quando houver dado.

---

## MÉDIO

### M1. O protótipo de frescor não prova o que o PRD afirma sobre `packed-refs`
- Onde: FR-5 ("O `.git/HEAD` foi lido com sucesso nos três repositórios, inclusive com `packed-refs`"), Glossário, addendum.
- Evidência: nos três repositórios o ref atual é **loose** (`refs/heads/develop`, `release/1.2.0`, `fix/1.4.4` existem como arquivo). O ramo `packed-refs` do `prototipo-frescor.py` nunca foi exercitado, então a frase do PRD não é sustentada. Além disso, `.git` como arquivo (worktree) leva a `gitdir` onde os refs vivem no `commondir`; `g / ref` não existe e o `open(packed-refs)` levanta `FileNotFoundError` (sem tratamento: o protótipo cairia em traceback, que FR-2 proíbe). Não há leitura de `git.disponivel`, nem de `derivado_de` de `workspace.json` (3 heads). Compara prefixo de 12 caracteres sem especificar a regra de prefixo.
- Correção: teste com repositório de fixture com ref empacotado e com worktree; tratar `FileNotFoundError` como `desconhecido`; reescrever a frase do PRD para o que foi realmente verificado.

### M2. FR-9 vs benchmark: comparar 50 linhas truncadas contra o `grep` completo
- Onde: FR-9 ("107 linhas casam na Q10"), SM-1.
- Na Q10 o CLI devolve 6.021 B (50 linhas) contra 15.636 B (107 linhas): respostas diferentes. Se o agente precisa das 107, paga a segunda chamada (`--all`) mais os cabeçalhos, e ninguém contabiliza isso (nem o custo do `--help` consultado). O "0,39×" da Q10 é uma vitória por truncamento. Reportar também o custo da resposta completa (CLI `--all`).

### M3. SM-C2 sub-especificado
- "5 perguntas seguidas do benchmark" sem dizer quais 5; o total contra `Read` depende fortemente da escolha (Q7/Q8 18KB contra Q1/Q9 54KB e 958KB). Não diz se o lado `Read` carrega as 10,6KB do `SKILL.md` antigo. O `--help` cresce com o inventário (≈20 linhas migradas para `--help`), mas não há teto de tamanho do `--help`. Fixar as 5 perguntas e o teto de bytes por `--help`.

### M4. FR-13: baldes condicionais e frescor próprio do fato ignorado
- No `bytecode.json` real só existem `deps_usadas_via_transitiva` e `deps_ignoradas_na_analise`; `deps_usadas_ausentes_do_pom` e `deps_declaradas_sem_uso` são condicionais (`scos-map.py` ~2366 a 2367). FR-13 trata "balde ausente = nada achado", mas "ausente" também é "não calculado" (por exemplo `transitivas_resolvidas` falso). Além disso, `frescor` do fato (compilado_em) aparece no resumo, mas, como em H3, não alimenta `estado`. Pior caso: o resumo diz "0 usadas ausentes do pom" para um bytecode compilado antes de mudanças no pom.

### M5. SM-2 é auto-avaliada e a linha de base é ambígua
- "numa verificação manual pontual de quem implementa ... A linha de base atual é medida nessa mesma verificação": quem implementa avalia o próprio resultado, e a base "atual" só existe depois da adoção. Sem aleatoriedade ou terceiro. É secundária, mas vira o único indicador de adesão real.

### M6. Escopo: o MVP carrega FR-8 sem leitor e FR-14 sem dado, e 13 goldens
- FR-8 "hoje não tem leitor automático" (§6.2) e a PRD o mantém "por pedido do usuário"; FR-14 (H7) trata um fato indisponível; FR-12/13 resolvem perguntas de baixa frequência (Q11, Q12) e custam golden, `--help` e inventário cada uma. A economia demonstrada está em 5 perguntas JSON (layout, config, docs, reactor, tests); nos TSV o CLI "não ganha em bytes" (§6.2). Sugestão: marcar FR-12/13/14 como segunda fatia (já são independentes por subcomando) e entregar primeiro FR-1/2/3/4/5/9/11, que sustentam SM-1.

### M7. "Contrato de saída estável" convive com `schema_versao != 2.1` = erro duro
- FR-1 manda sair com erro se `schema_versao != 2.1`; `SCHEMA_VERSAO = "2.1"` está hardcoded no gerador (linha 40). Todo bump do gerador, mesmo compatível, derruba o CLI inteiro e o mapa precisa ser regenerado. FR-6 promete saída independente de mudanças internas dos fatos. Definir uma regra (major.minor) ou assumir explicitamente o acoplamento. `workspace.json` também tem `schema_versao`; a regra não diz se ela é checada.

### M8. FR-8: localização do log e `.gitignore`
- O `.gitignore` do workspace hoje só lista os 3 repositórios; a entrada do log não existe e, dentro de cada repositório, o `.gitignore` é outro. Clone isolado ou CI sem `.scos-map/workspace.json`: o comportamento não é definido ("nunca impede a consulta" cobre falha de escrita, não ausência da raiz). O registro também não guarda código de saída nem versão de schema, o que torna o log inútil para auditar erros.

---

## BAIXO

### L1. UJs cobrem 5 de 13 subcomandos
- Não há UJ para tests (FR-12), bytecode (FR-13), callgraph (FR-14), layout/config/docs fora UJ-1. Persistente desde a rodada 1.

### L2. `.memlog.md` desatualizado
- Última linha de contagem: "(change) PRD agora tem 10 FRs, 1 NFR, 1 open question". A PRD tem 14 FRs, 2 NFRs, zero OQs. Linhas intermediárias sobre FR-11 com "gate experimental" e "agente dedicado" foram superadas. Falta registrar esta rodada.

### L3. Truncamento de `# limitacao:` em 160 caracteres sem reticências
- O texto de `snapshots_locais` junta 2 limitações com 159 caracteres (borda). Um acréscimo no gerador corta a segunda limitação, justo a que FR-4 exige dizer ("alterações não commitadas ou em stash"). Truncar por cláusula ou marcar com `…`.

### L4. NFR-2 medido só com `layout.json` de 54KB
- "30× abaixo do teto" vale para um arquivo de 54KB. `bytecode_edges.tsv` (958KB), `files.tsv` (222KB) e `config.json` (142KB) não foram medidos, e o protótipo não inclui o log nem a busca do diretório ancestral.

### L5. Pequenos defeitos do `benchmark-baseline.py`
- `ok = (cl <= 0.10 * rd or rd < 2048)` mantém um ramo morto (todos os `Read` ≥ 3,5KB), assim como a cláusula "fatos de 2KB ou mais" de SM-1. O `jq` é pré-requisito não declarado. `Path(...).parents[4]` fixa a profundidade. `hdr()` usa `fato.get('estado','fresco')`, ou seja, o proxy assume fresco, contradizendo o frescor medido no addendum, e o proxy da Q3 usa `{"confianca": "resolvida"}` inventado em vez do pior caso real entre `deps.tsv` e `_transitivas_comuns.tsv`.

### L6. Ordem e rótulos do addendum
- A tabela de medição lista Q11 e Q12 antes de Q9 e Q10; a "Leitura" fala em "Q5–Q8, Q11, Q12" para `jq` mas a tabela mostra `n/a` em outras; fácil de se perder ao implementar o teste.

---

## O que está bom (preservar)
- Tabela "Conteúdo padrão por subcomando" com campos verificados nos fatos reais (por exemplo as colunas de `files.tsv` e `tests.tsv` batem com os arquivos).
- Teto duplo (linhas e bytes), ordem estável e rodapé `N de M` sempre presente.
- Envelope com `# limitacao:` e marca por linha só quando difere; "vazio nunca é silêncio".
- Decisão honesta registrada: nos TSV o ganho é acurácia, não bytes; o `jq` entra como concorrente medido.
- Não-objetivos claros (subagent, geração de fatos) e FR-8 sem tokens falsos.
- Inventário do `SKILL.md` no addendum, com destino por seção.

## Prioridade sugerida
1. H2 e H3 (correção factual de FR-7 e da precedência de `estado`): barato e destrava os testes.
2. H1 (semântica do frescor e falso-fresco com `git.dirty`).
3. H4 (tabela única de flags e interface posicional) e H6 (onde mora cada regra).
4. H5 (meta e baseline de SM-1) e H7 (fixture de FR-14 ou rebaixar).
5. Médios e baixos na próxima edição do addendum e do `.memlog.md`.

---

## Delta vs rodada 2

Resolvidos (verificados na PRD atual):
- R2-C1 (custo e semântica de `fact_state`): **resolvido na forma**. O CLI não usa `fact_state`; lê `.git/HEAD`. Mas o fundo reabriu como H1 (falso-obsoleto 3/3, falso-fresco com mapa sujo) e M1 (packed-refs não exercitado).
- R2-C2 (proxy otimista, sem `jq`, Q3/Q7/Q8): **parcialmente resolvido**. Há `jq`, cabeçalho real, Q3 com transitivas, latência, Q10 quente e asserção. Persistem a asserção por substring, o `grep` não equivalente e a meta sem margem (H5), e o proxy ainda não é o CLI real.
- R2-H1 (`completude`/limitação no envelope): resolvido (FR-5).
- R2-H2 (teto só em linhas): resolvido (FR-9, linhas e bytes, ordem estável). Restou M2 (truncado vs completo).
- R2-H3 (experimento de subagent): resolvido por descarte com amostra única declarada.
- R2-H5 (FR-11 por linhas/caracteres, exemplos em `--help`, inventário): **resolvido na forma**; aberto no fundo (H6: regras só em `--help`, descrições de 160 caracteres, `scos-map-build` aponta para `scos-map`).
- R2-H6 / filtros "equivalentes" de `awk` (FR-2): **parcialmente resolvido**: tabela com 3 `awk` reais, mas FR-12/13/14 a descaracterizam (H4).
- R2-M (metas ≤10% em fatos pequenos, tolerância TSV): resolvido (SM-1, mas a cláusula de 2KB virou ramo morto, L5).
- R2-M (log na raiz, comando literal, Python ≥ 3.10): resolvido (FR-8, NFR-1); M8 é resíduo.
- R2-M3 (§8/§9 vs memlog): §8/§9 limpos; o `.memlog.md` segue desalinhado (L2).
- R2-M6 (vazio vs filtros): resolvido por FR-2 ("cabeçalho, zero linhas e rodapé").

Ainda abertos:
- R2-L2 (UJs cobrem poucos subcomandos): agravado (5 de 13, L1).
- R2-L3 (proveniência frágil): melhorou (benchmark portátil, `gerado_em` impresso), resíduos em L5.
- R2-L1 (baseline de Q7/Q8 pequeno): reconhecido no addendum; não mais um problema.

Novos nesta rodada: H2 (AGENTS.md com 7 linhas, não 12; 13 subcomandos), H3 (precedência de `estado`, ordem incompleta, exemplo de FR-3), H4 (FR-12/13/14 contra FR-2; `--alvo` inexistente; posicional vs flag), H7 (FR-14 sem dado real), M4, M5, M6 (escopo), M7 (`schema_versao`), M8, L3, L4, L6, e as partes novas de H1, H5 e H6 citadas acima.
