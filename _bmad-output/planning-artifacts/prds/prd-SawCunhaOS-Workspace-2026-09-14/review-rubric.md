# PRD Quality Review — Scripts de Consulta Rápida para scos-map (rodada 3)

## Overall verdict
A PRD está pronta para virar stories. Tem tese única e medida (custo em tokens do `Read` de JSON minificado), decisões com o custo nomeado (interface única contra a recomendação de escopo mínimo, subagent descartado com número), 14 FRs com consequências testáveis e uma única suposição aberta, indexada com dono. O risco que sobra é um buraco entre o benchmark e o contrato: os filtros "congelados" de FR-2 não cobrem várias das 12 perguntas que SM-1 usa como teste, e a meta de JSON de SM-1 fecha sem margem. Nenhum crítico.

## Decision-readiness — strong
As decisões estão escritas como decisões. Exemplos: "decisão confirmada com o usuário" (§2.2), a tabela de opções do addendum, o `[NOTE FOR PM]` de FR-2 sobre não virar jq genérico, o `[NOTE FOR PM]` de §6.2 admitindo que em TSV o CLI "não ganha em bytes sobre o `grep`/`awk`", e FR-4 aceitando o falso-obsoleto ("os 5 commits novos da Foundation ... são de docs"). §8 "Nenhuma" é honesto, porque as OQs foram resolvidas. A única incerteza real está em §9 e é a que mais importa (CLI real dentro da margem do proxy).

Sem findings.

## Substance over theater — strong
Sem personas decorativas, sem seção de inovação, sem NFR de boilerplate. Os limiares são do produto: 50 linhas / 6.000 B / 240 caracteres (FR-9), 30 linhas / 2.000 caracteres / 160 de descrição (FR-11), 300 ms com protótipo medido (NFR-2). A Vision cita bytes medidos ("de 3,5KB a 958KB" contra "311 B a 15KB") e não serve a outro PRD. FR-8 continua sem leitor automático, mas §4.5 e §6.2 dizem isso abertamente.

Sem findings.

## Strategic coherence — strong
Tese, escopo e métricas se alinham. SM-1 mede a economia, SM-C1 protege o envelope contra a perda de acurácia e SM-C2 mede a sessão inteira, com o custo das skills e do `--help`. A promessa foi reduzida de forma honesta: "mais barato que o `grep` por consulta, não por sessão". Os fatos em TSV têm o ganho redefinido como acurácia, e não como bytes. A forma do MVP é coerente (resolver um problema).

### Findings
- **low** Bytes como proxy de tokens (§1, §7 SM-1) — a Vision fala em "tokens", mas todas as metas são em bytes. Caminhos, hashes e TSV tokenizam pior que prosa, então a razão CLI/`Read` em tokens pode diferir da razão em bytes. §6.2 já diz que bytes são "só piso". *Fix:* uma frase em SM-1: "bytes é proxy de tokens; não medimos tokens".

## Done-ness clarity — adequate
Muito melhor que na rodada 2. A tabela "Conteúdo padrão por subcomando" dá a saída sem filtro de cada um. FR-5 traz formato exato, regra de pior caso e enums. FR-9 tem teto duplo, truncamento e ordem estável. FR-11 mede linhas e caracteres. FR-12 a FR-14 trazem as regras de não-afirmação (`[heuristica]`, "nunca 'não existe teste'", `--sem-chamador` não é código morto). O que impede "strong" é a relação entre os filtros e o benchmark.

### Findings
- **high** Filtros congelados não cobrem o benchmark que valida o CLI (FR-2 × FR-6 × SM-1 × addendum) — FR-2 fecha o conjunto de filtros em 4 linhas (`--modulo`, `--kind`, `--commits-90d-min`, `--todos-modulos`, `--ga` em `deps`, e os de `arestas`). O benchmark exige respostas que dependem de recortes fora desse conjunto. Q2 pede só os arquivos de config em `etc/api/organization`, mas `config` devolve `path \t bytes` de todos os arquivos, e `config.json` tem 142KB. Q5 pede docs "sobre nomenclatura" (`docs`, sem filtro de texto). Q4 pede a versão do jackson na BOM, e `gerenciadas` não tem `--ga` (só `deps` tem). Sem esses filtros, FR-9 corta em 50 linhas / 6.000 B e a asserção de conteúdo de FR-6 ("a resposta contém o conteúdo esperado") falha. Os bytes do proxy (581 B, 549 B, 183 B) só existem porque o proxy recortou como o CLI ainda não pode. *Fix:* acrescentar à tabela de FR-2 os filtros que o benchmark usa (`config --prefixo`, `docs --contem`/`--titulo`, `gerenciadas --ga`) ou um `--grep <texto>` simples (substring na linha de saída) válido para todos os subcomandos de texto. Em seguida, cobrir cada pergunta do benchmark com um filtro já listado.
- **medium** "Conjunto fechado e congelado" contradito pelas flags de FR-4/5/12/13/14 (FR-2 × FR-4, FR-5, FR-12, FR-13, FR-14) — FR-2 diz que o conjunto "é fechado e congelado nesta PRD". Mesmo assim, outros FRs introduzem `--detalhe`, `--base`, `--arquivos`, `--balde`, `--lacunas`, `--sem-chamador`, `--entrypoints`, `--limit`, `--bytes`, `--all`. Dá para ler que o congelamento vale só para filtros de linha, mas o texto não diz isso, e o teste "golden por linha da tabela" cobre só 4 linhas. *Fix:* uma frase em FR-2 separando filtros de linha (congelados) de seletores de visão e de tetos (definidos no FR do subcomando), e declarar que cada flag nomeada em FR-4/5/9/12/13/14 tem ao menos um caso golden.
- **medium** Latência medida no fato errado para FR-10 (NFR-2 × FR-10) — NFR-2 afirma "Verificado" com `layout.json` de 54KB, mas os maiores fatos que o CLI vai ler são `bytecode_edges.tsv` de 958KB / 6.936 linhas (UJ-4, Q9, Q10). Filtrar e truncar isso em stdlib provavelmente cabe nos 300 ms, mas não foi medido. *Fix:* medir `arestas` sobre o maior TSV (proxy de uma linha de código já serve) ou rebaixar o "Verificado" para "estimado para fatos pequenos; medir arestas na primeira story".
- **low** Ordem de pior caso de `estado` incompleta (FR-5) — a lista `obsoleto, desconhecido, ausente, indisponivel, fresco` omite `disponivel` e `nao_aplicavel`, que o Glossário lista como valores válidos. Um subcomando com um fato `disponivel` e outro `fresco` não tem ordem definida. *Fix:* inserir os dois na lista (por exemplo, `nao_aplicavel` e `disponivel` equivalentes a `fresco`).
- **low** Orçamento de 2.000 caracteres da skill `scos-query` não foi verificado (FR-11 × FR-7) — o corpo precisa conter o comando literal, 12 linhas de roteamento (nome → pergunta), o aviso de `--all`, o aviso de tamanho dos fatos grandes (FR-7) e a linha de "perguntas abertas" (addendum). Dá cerca de 100 a 120 caracteres por linha de roteamento, apertado mas viável. *Fix:* rascunhar a skill na primeira story antes de fixar o teste de 2.000 caracteres, ou aceitar o ajuste do limite.

## Scope honesty — strong
Os Non-Goals fazem trabalho real (subagent, `scos-map-build`, grep de código, análise arquitetural, novos fatos). §6.2 traz gatilhos de reabertura (spike de tokens, `gain`). §0 declara o addendum como leitura obrigatória. Densidade de itens abertos: 0 OQ, 1 `[ASSUMPTION]`, 3 `[NOTE FOR PM]`, adequada ao stakes interno. A suposição de SM-1 está indexada com dono e condição de fechamento. Não há des-escopo silencioso: tests, bytecode e callgraph entraram por decisão do usuário e o memlog registra isso.

Sem findings.

## Downstream usability — strong
O Glossário cobre os termos usados (Fato, Envelope, Frescor barato, Benchmark canônico, Log de custo). IDs FR-1..FR-14, NFR-1/2, SM-1/2/C1/C2 e UJ-1..5 são únicos e as referências cruzadas resolvem. Os FRs saem em ordem temática, não numérica, e §0 declara que "os IDs são estáveis, a ordem é temática". O protagonista único ("o agente") é aceitável para uma ferramenta de ator único.

### Findings
- **low** UJs não cobrem FR-12, FR-13, FR-14, FR-8 e FR-11 (§2.3) — são cinco jornadas para 14 FRs. FR-12 a FR-14 são consultas novas sem história de uso, mas cada uma tem regras de não-afirmação muito específicas, e o contexto de uso ajudaria quem escrever as stories. *Fix:* uma frase em UJ-5 ou uma UJ-6 ("o agente pergunta se um módulo tem teste antes de alterá-lo e não conclui 'não testado'").

## Shape fit — strong
Capacidade enxuta para um ator único, UJs de uma frase, brownfield bem referenciado (`AGENTS.md`, `SKILL.md`, `snapshots_locais`, `fact_state`). A mistura de comportamento (FR-1..5, 9, 10, 12..14) com empacotamento (FR-6, 7, 11) é razoável para uma ferramenta interna.

## Mechanical notes
- **Assumptions Index:** 1 `[ASSUMPTION]` inline (§7 SM-1) e 1 entrada em §9; o roundtrip fecha. As suposições de frescor e latência estão registradas como fechadas por verificação. Ver o finding de latência sobre o que "fechada" cobre.
- **IDs:** FR-1..FR-14 contíguos e únicos. Sem referências quebradas (FR-5/FR-9 em FR-10, FR-12/13/14 em FR-7 e §6.1 resolvem).
- **Glossário:** consistente (`heuristica`, `confianca`, `estado`). "Subagent" não está mais no Glossário e só aparece em Non-Goals, o que é coerente.
- **Números:** a tabela do addendum bate com o texto. 12/12 ≤ 10% do Read, JSON 4 de 5, TSV 4 de 4, Q10 única acima dos tetos, e as faixas 0,3%–5,5% e 0,27×–1,54×. A tabela lista Q11/Q12 antes de Q9/Q10 (ordem de inclusão); sem impacto.
- **SM-1, margem zero:** 4 de 5 perguntas com `grep` possível é exatamente 80%. Uma única regressão do CLI real em JSON (Q1, Q2, Q5, Q6) reprova a meta, e o proxy já é piso. A suposição de §9 cobre o risco, mas a meta não tem folga (*low*).
- **Memlog:** as linhas "(assumption) Pendentes com dono: ... FR-5 ... NFR-2" e "exceções motivadas em FR-7" estão superadas por decisões posteriores (fechamento da verificação; FR-12/13/14 no MVP). Sem impacto no PRD.
- **Seções exigidas:** presentes para o stakes interno.

## Delta vs rodada 2
**Resolvidos:** conflito de 30 linhas x documentação (exemplos e formato vão só para `--help`; FR-1, FR-6 e FR-11 reescritos, com inventário no addendum); envelope para mais de um fato (regra de pior caso e `# fontes:` em FR-5); teto em linhas vs bytes (FR-9 passou a 50 linhas e 6.000 B); conteúdo padrão por subcomando JSON (tabela em FR-1); cabeçalho de FR-3 alinhado a FR-5; proxy tratado como fato (agora `[ASSUMPTION]` indexada); SM-C2 frouxo (agora benchmark de sessão de 5 perguntas); SM-2 sem método (N=20, 5 sessões); UJ de arestas (UJ-4, mais UJ-5); texto desatualizado do addendum; FR-8 sem retenção ("sem rotação na v1"); escrita concorrente do log.
**Ainda abertos:** cobertura de FRs por UJs (agora 5 UJs, mas FR-12 a FR-14 e FR-8/11 sem jornada, *low*); SM-1 depende do CLI real (agora declarado e indexado; a meta de JSON ficou sem folga).
**Novos nesta rodada:** filtros congelados não cobrem o benchmark (high); "congelado" contradito pelas flags de outros FRs (medium); latência não medida para os maiores TSV (medium); ordem de `estado` incompleta, orçamento de 2.000 caracteres e bytes≠tokens (low).
