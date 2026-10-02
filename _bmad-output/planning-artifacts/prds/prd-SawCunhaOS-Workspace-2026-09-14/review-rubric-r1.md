# PRD Quality Review — Scripts de Consulta Rápida para scos-map

## Overall verdict
A PRD tem uma tese nítida e bem fundamentada: o `Read` de JSON minificado custa mais tokens que `grep`, e o CLI `scos-map-query` com envelope de confiança corrige isso sem sacrificar acurácia. A forma é adequada a uma ferramenta interna de ator único, e os Non-Goals e o addendum são honestos. O risco está na verificabilidade: nada limita o tamanho da saída (o objetivo central), as métricas SM-1/SM-2/SM-C1 não têm instrumentação que as meça, e o escopo de Tier 2/3 decidido no memlog sumiu do MVP sem aviso. Antes de virar stories, a PRD precisa de pelo menos esses três ajustes.

## Decision-readiness — adequate
As decisões grandes estão registradas como decisões: CLI específico por fato (não jq genérico), interface única JSON+TSV "contra a recomendação inicial de menor escopo" (addendum, "Sobreposição com TSV"), subagent fora do MVP. O trade-off do TSV é nomeado com o que se aceitou perder. Isso é bom e deve ser preservado.

Fraquezas: a Open Question 1 ("o disparo via subagent ... deve ser implementado já nesta iniciativa ...?") já está respondida em §6.2 ("fica para uma iteração seguinte"), então é retórica. A Open Question 3 (onde vive o log de custo) é aberta de verdade e bloqueia FR-8 e a leitura de SM-1, mas não tem default proposto. Há só dois `[NOTE FOR PM]`, ambos em itens seguros (ergonomia humana, comando `gain`); nenhum marca a tensão real, que é a sobreposição de FR-2 com o desenho "jq" rejeitado.

### Findings
- **medium** OQ-1 já respondida (§8 item 1 vs §6.2) — a PRD diz que o subagent está fora do MVP e depois pergunta se entra. *Fix:* remover a pergunta ou reformulá-la como gatilho de revisão ("quando reabrir?").
- **medium** OQ-3 sem default (§8 item 3, FR-8) — decide se SM-1 é por projeto ou global, e se o log fere a regra de FR-1. *Fix:* propor um default (ex.: um único log no workspace, fora de `.scos-map/`) e marcá-lo `[ASSUMPTION]`.
- **low** `[NOTE FOR PM]` só em itens seguros (§6.2) — a tensão FR-2 (filtro por "caminho dentro da estrutura do fato") versus a rejeição do jq genérico fica sem aviso. *Fix:* adicionar um NOTE em FR-2.

## Substance over theater — strong
Não há personas decorativas, nem seção de inovação, nem NFRs de boilerplate. O addendum traz números reais (142KB, 54KB, 958KB, 952 linhas) e prior art que de fato moldou a decisão (jq descartado com motivo). A Vision é específica do problema e não serviria a outro PRD.

Ressalva: a Vision afirma que o `scos-map` hoje "sai mais caro que simplesmente rodar `grep`", mas o addendum só mede o tamanho dos fatos e nunca o custo de um grep equivalente. A afirmação é plausível, não demonstrada.

### Findings
- **medium** Premissa central não medida (§1 Vision, addendum "Evidência de tamanho") — "mais caro que ... `grep`" é tratada como fato e não aparece como `[ASSUMPTION]`. *Fix:* medir 2 ou 3 perguntas reais (grep vs `Read`) e registrar o resultado, ou marcar como assumption. Esse número seria também a linha de base de SM-1.

## Strategic coherence — adequate
A tese é única e todas as FRs servem a ela (recortar, sinalizar confiança, medir custo). A prioridade por valor também está explícita: FR-3 e FR-4 são o diferencial que nenhum grep resolve. O counter-metric SM-C1 contrabalança SM-1 de forma correta, o que é raro e bom.

O problema é que as métricas não validam a tese de modo executável. SM-1 compara com "um `grep` equivalente", mas o log de FR-8 só registra chamadas ao CLI, nunca ao grep. SM-2 (≥90% das perguntas respondidas sem `Read` bruto) exige observar as chamadas de `Read`, e nada na PRD instrumenta isso. SM-C1 ("zero") não diz como se detecta uma ocorrência.

### Findings
- **high** Métricas sem instrumentação (§7 SM-1, SM-2, SM-C1) — o log (FR-8) é a única fonte de dados e só cobre o CLI. A linha de base do grep, o denominador de SM-2 e a detecção de SM-C1 não têm origem definida. *Fix:* para cada SM, dizer como é medido (ex.: SM-1 por benchmark fixo de N perguntas comparando bytes de saída; SM-2 por revisão amostral de transcrições; SM-C1 por teste automatizado que consulta fatos `obsoleto`/`heuristico` e verifica o envelope).
- **medium** SM-1 usa bytes como proxy de tokens (FR-8, §6.2) — "paridade ou menos" que o grep é um limiar frouxo que mal se distingue do status quo. *Fix:* definir um limiar quantitativo (ex.: ≤50% dos bytes do grep) ou justificar a paridade.

## Done-ness clarity — thin
FR-1, FR-3, FR-5 e FR-8 têm consequências testáveis e boas (exit code não-zero com o comando de build a rodar, log best-effort, saída vazia = sem conflito). O ponto fraco é que a propriedade que define o produto, saída compacta, não é limitada por nenhuma FR.

### Findings
- **high** Nenhum limite de tamanho de saída (FR-1, "recorte textual, uma unidade de informação por linha") — o addendum admite que `files` sem filtro continua grande (952 linhas, 222KB) e que o subagent seria necessário "para consultas que ainda assim produzem saída grande". Sem teto ou paginação, o CLI pode repetir o problema que a Vision quer resolver. *Fix:* adicionar uma consequência testável: teto padrão de linhas com aviso de truncamento ("N linhas omitidas; use filtro") e uma flag explícita para desligá-lo.
- **high** Escopo de Tier 2/3 contradiz o memlog (§6.2 "Suporte a Tier 3 ... além do que já existe" e §4.1 lista de subcomandos vs. memlog "Escopo: Tier 1 a 3 completo") — nenhum subcomando cobre `bytecode_edges.tsv`/callgraph, justamente os maiores arquivos (958KB, 674KB no addendum). A decisão do usuário foi de-escopada sem sinalização, o que o rubric chama de "silenciosa". *Fix:* ou incluir um subcomando de arestas de bytecode em FR-1, ou registrar explicitamente a redução como `[NOTE FOR PM]` e atualizar o memlog.
- **high** FR-5 sem formato definido nem granularidade ("Toda linha ... carrega ... estado de confiança"; "ex.: sufixo ou coluna dedicada") — a confiança é anotada por fato e não por linha, e a PRD não diz como o estado de um fato se mapeia para as linhas, nem como se representa um fato `obsoleto` e `heuristico` ao mesmo tempo. Sem isso, FR-6 (contrato estável) e SM-C1 não são testáveis. *Fix:* fixar o formato (ex.: coluna final `[atual|obsoleto|heuristica]`) e o comportamento quando há dois estados.
- **medium** FR-4 não define "desatualizado" (§4.2) — "em relação ao estado atual do repositório de origem" não diz o que é comparado (timestamp do jar no `~/.m2` vs. HEAD? hash?). Também não está confirmado que o `workspace.json` já carrega esse dado, e a PRD insiste que o CLI "nunca compila nem escreve". *Fix:* nomear o campo do fato ou a regra de comparação e confirmar a fonte.
- **medium** FR-2 "sem perda de cobertura" é de difícil verificação — não há conjunto enumerado de consultas `awk` que devem ter equivalente. *Fix:* listar as consultas do `SKILL.md` que viram casos de teste de aceitação.
- **medium** FR-1 só testa o contrato comum — não há consequência por fato (o que `layout`, `config`, `docs`, `reactor` devolvem) nem exemplo de saída. *Fix:* um exemplo de saída por subcomando, no addendum ou numa seção de contrato.
- **low** FR-7 testa por existência de linha equivalente na tabela, não por comportamento — aceitável, mas "ou está explicitamente listada como exceção" deixa o teste passar trivialmente.

## Scope honesty — adequate
§5 e §6.2 são claros e fazem trabalho real (não substitui `scos-map-build`, não faz análise arquitetural, não adiciona fatos). A decisão de deixar o subagent fora do MVP é explícita e vem com a consequência (log só com proxy). Densidade de itens abertos baixa (3 OQ, 2 ASSUMPTION, 2 NOTE), coerente com stakes internos.

Lacunas: o rebaixamento de Tier 2/3 (acima), e suposições implícitas não marcadas.

### Findings
- **medium** Suposição mal classificada em FR-6 (§4.4) — "o mecanismo de disparo via subagent ... é registrado no addendum.md como abordagem recomendada" é uma decisão de escopo já tomada (memlog), não uma inferência por confirmar. Isso dilui o sentido de `[ASSUMPTION]` e deixa FR-6 sem a exigência de capacidade que o memlog disse ter virado requisito. *Fix:* transformar em nota de escopo e manter como assumption só o que de fato não foi confirmado.
- **medium** Assumptions não marcadas — (a) a estrutura dos JSONs é estável o bastante para fixar subcomandos; (b) o `Read` de JSON minificado é de fato o caminho usado pelos agentes hoje; (c) o log pode ser escrito em algum lugar sem violar "nunca escreve em `.scos-map/`". *Fix:* marcar e indexar.
- **medium** Conflito entre FR-8 e FR-1 Out of Scope — FR-1 diz que o CLI "nunca ... escreve em `.scos-map/`", e FR-8 grava um log cujo local pode ser `.scos-map/` (OQ-3). *Fix:* declarar que o log vive fora de `.scos-map/` e reescrever a exceção em FR-1.

## Downstream usability — adequate
Glossário presente e útil, IDs FR-1 a FR-8 contíguos e sem duplicatas, referências cruzadas resolvem (FR-6 -> addendum, FR-8 -> SM-1). §0 orienta o leitor. Há um UJ por feature principal, com o agente como protagonista único.

Pontos de atrito: UJ cobre só FR-1, FR-3 e FR-4; FR-2, FR-5, FR-6, FR-7 e FR-8 não têm jornada. Para um CLI interno isso é aceitável. O addendum diz "nada aqui é normativo", mas FR-6 e FR-8 dependem dele para o contrato de saída e o enriquecimento, então quem for extrair stories precisa ler os dois.

### Findings
- **low** FR-6 e FR-8 dependem do addendum "não normativo" (§4.4, §4.5) — a extração de stories pode perder essa dependência. *Fix:* citar na própria FR o trecho necessário, ou deixar o addendum explicitamente como leitura obrigatória.
- **low** UJ-1 realiza só `layout`, mas FR-1 cobre sete fatos — nenhuma jornada exercita `config`, `deps` ou `docs`. *Fix:* opcional; uma frase a mais.

## Shape fit — strong
A forma de capacidade enxuta, com UJs de uma frase e um único ator, combina com ferramenta interna de ator único; o §2.3 declara isso. Não há personas nem seções de formalização excessiva. O contexto brownfield é bem referenciado (`AGENTS.md`, `SKILL.md`, comandos `awk` existentes). Nada a corrigir.

## Mechanical notes
- **Assumptions Index:** as duas assumptions inline (FR-6, FR-8) estão no índice e vice-versa. O roundtrip fecha. Ver a ressalva de classificação acima.
- **IDs:** FR-1..FR-8, UJ-1..3, SM-1, SM-2, SM-C1 contíguos; nenhuma referência quebrada. O memlog está defasado ("7 FRs ... 2 open questions"; a PRD tem 8 FRs e 3 OQ) — atualizar para evitar confusão.
- **Glossary drift:** "frescor de workspace" (UJ-2) vs. "Frescor de SNAPSHOT local" (FR-4); "reactor" (FR-1) vs. "fronteiras entre módulos" (§1, §3); `heuristica` (§1, FR-5 título/glossário) vs. `heuristico` (FR-5 consequência, SM-C1) — o valor real do campo `confianca` deveria ser confirmado e usado de forma uniforme. "Envelope de confiança" é usado em FR-5/SM-C1 mas não está no Glossário.
- **Título:** "*Working title — confirmar.*" ainda aberto no corpo; `status: draft` coerente.
- **Seções exigidas para stakes internos:** todas presentes (Vision, Target User, Glossário, Features/FRs, Non-Goals, MVP, SM, OQ, Assumptions).
