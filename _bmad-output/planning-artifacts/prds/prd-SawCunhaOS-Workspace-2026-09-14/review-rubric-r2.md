# PRD Quality Review — Scripts de Consulta Rápida para scos-map (rodada 2)

## Overall verdict
A PRD está madura para virar stories: tem tese única (custo em tokens do `Read` de JSON minificado), evidência medida (benchmark de 9 perguntas, experimento com subagent) e decisões registradas com o que se abriu mão. Os problemas que restam são de verificabilidade fina, não de direção: um conflito entre o limite de 30 linhas das skills e a documentação exigida por subcomando, uma linha de base que é proxy tratada como fato, e um envelope de confiança sem regra para subcomandos que leem mais de um fato. Nenhum bloqueador crítico.

## Decision-readiness — strong
As decisões aparecem como decisões e com custo nomeado: CLI por fato em vez de jq (addendum, tabela de opções), interface única JSON+TSV "contra a recomendação inicial de menor escopo", subagent descartado com número (~34K vs ~770 tokens) e gatilho explícito de reabertura (">100KB"). SM-1 aceita abertamente que em TSV o CLI só empata com `grep` ("a interface única" é o ganho). `[NOTE FOR PM]` em FR-2 marca a tensão real (não virar jq genérico). §8 "Nenhuma" é honesto: a OQ restante foi de fato resolvida (só `deps` combina dois arquivos).

### Findings
- **medium** Suposições fechadas sem ressalva sobre o proxy (§7 SM-1, §9 "Nenhuma pendente") — a linha de base "9 de 9 ≤ 10% do `Read`" e "JSON 4 de 4 ≤ `grep`" vem de um "proxy do CLI, que ainda não existe": é o recorte mínimo ideal, ou seja, um limite inferior. As metas de SM-1 ficam coladas nesse piso (TSV: "paridade ... ~60 bytes"; Q3 e Q9 já estão em +59 bytes), então um CLI real com qualquer linha extra reprova. A amostra de subagent é n=1 (admitido no addendum, mas não marcado). *Fix:* manter um `[ASSUMPTION]` indexado: "o CLI real fica dentro da margem do proxy", com dono e condição (rodar o benchmark contra o CLI na primeira story).

## Substance over theater — strong
Sem personas decorativas, sem seção de inovação, sem NFR de boilerplate. NFR-1 e FR-9 têm limiares do produto (50 linhas, 30 linhas, `.scos-map-query.log`). A Vision cita bytes reais e serviria só a este problema. Único traço de mobília: FR-8 (log) existe por pedido do usuário mas nenhuma métrica o consome (ver low abaixo).

## Strategic coherence — strong
Tese, escopo e métricas se alinham: SM-1 mede a economia, SM-C1 protege a acurácia (envelope), SM-C2 protege contra o custo da própria documentação. FR-3/FR-4 são o diferencial reconhecido. Forma de MVP coerente (problema-resolvendo).

### Findings
- **medium** SM-C2 não protege a promessa da Vision (§1 vs §7) — a Vision promete ser mais barato "do que o `Read` ... e, na maioria das perguntas, do que o `grep`", mas SM-C2 só exige "nunca acima do `Read` do fato". Somando as ~30 linhas de skill + `--help` ao contexto, perguntas como Q4 (CLI 130 B vs `grep` 474 B) ou Q6 (224 B vs 365 B) passam a custar mais que o `grep` sem violar nenhuma métrica; o piso do `Read` (3,5KB no menor caso) é frouxo. *Fix:* acrescentar ao SM-C2 um benchmark de sessão (N perguntas seguidas, docs contados uma vez) comparado ao `grep`, ou reduzir a promessa da Vision.
- **low** SM-2 sem método de amostragem (§7) — "em amostra de transcrições, ≥ 90%" não diz tamanho da amostra, período nem linha de base atual. *Fix:* fixar N e janela, ou declarar SM-2 como verificação manual pontual.

## Done-ness clarity — adequate
A maioria das FRs tem consequências verificáveis e várias são muito boas: FR-9 (teto de 50, aviso literal, teste incluindo `arquivos` sem filtro), FR-5 (primeira linha com formato exato e enums), FR-6 (golden tests), FR-7 (teste que falha se linha da tabela não tiver subcomando ou exceção motivada), FR-4 (campos nomeados do fato `snapshots_locais`).

### Findings
- **high** Limite de 30 linhas da skill conflita com a documentação exigida (FR-1, FR-6, FR-11) — FR-1 exige "exemplo de saída real (3–5 linhas)" por subcomando no `--help`/`SKILL.md`; FR-6 exige o formato de cada subcomando documentado em "`--help` e seção no `SKILL.md`"; são ~10 subcomandos (layout, config, deps, gerenciadas, docs, reactor, arquivos, arestas, conflitos, snapshots) = 30 a 50 linhas só de exemplos. FR-11 limita o corpo de `scos-query` e `scos-map` a "no máximo 30 linhas". "SKILL.md" é ambíguo (qual das duas skills?), e FR-7 ainda pede aviso de tamanho dos fatos grandes na mesma skill. Os testes de aceitação não podem passar todos ao mesmo tempo, ou os exemplos vão só para o `--help` e a skill perde o contrato. *Fix:* decidir onde mora o quê: exemplos e formato só no `--help` (custo pago só quando pedido), skill com uma linha por subcomando; reescrever FR-1/FR-6 para dizer "`--help`", e FR-7 para dizer qual skill.
- **medium** Envelope de FR-5 indefinido para subcomando que lê mais de um fato (FR-5, §8) — §8 diz que `deps` "lê os dois internamente" (`deps.json` + `deps.tsv`), mas FR-5 prevê uma única linha `# confianca=... estado=... gerado=...`. Se um é `fresco` e o outro `obsoleto`, ou `declarada` vs `resolvida`, qual valor vai no cabeçalho? SM-C1 não consegue ser verificado sem essa regra. *Fix:* regra explícita (ex.: pior caso entre os fatos, ou duas linhas de cabeçalho) e um caso de teste.
- **medium** Teto medido em linhas, não em bytes (FR-9) — 50 linhas de `config.json` (valores longos) ou de `bytecode_edges.tsv` podem passar de 5–7KB; a meta de economia é em bytes (SM-1). O benchmark (maior resposta 17 linhas) não exercita o pior caso. *Fix:* acrescentar teto de bytes por linha ou total (ex.: truncar linha em N caracteres com marca), ou um teste com o maior fato de cada tipo.
- **medium** Conteúdo de cada subcomando ainda não especificado (FR-1, FR-2; addendum "Pendências") — FR-1 define a saída como "um recorte textual" e FR-2 como "coluna + padrão, ou caminho dentro da estrutura do fato"; o que `layout`, `config`, `docs` e `reactor` devolvem por padrão fica para a "primeira story". Os casos de teste de FR-2 só cobrem os `awk` dos TSVs. Para os fatos JSON, que são o foco da Vision, não há consequência testável de conteúdo. *Fix:* uma linha por subcomando JSON com o que ele devolve sem filtro (campos/ordem), mesmo que esboçada.
- **low** Cabeçalho de FR-3 com reticências (`# confianca=alta estado=fresco ... | 0 conflitos`) — não bate com o formato exato de FR-5 (inclui `gerado=<timestamp>`); `| 0 conflitos` é uma extensão não declarada em FR-5. *Fix:* alinhar o exemplo a FR-5 e declarar o sufixo.

## Scope honesty — strong
Non-Goals fazem trabalho real (subagent, `scos-map-build`, grep de código, análise arquitetural, novos fatos). Tier 2/3 voltou ao escopo via FR-10 e §6.1 declara isso. Out of Scope de §6.2 traz gatilhos de reabertura (spike de tokens, `gain`). Densidade de itens abertos baixa (0 OQ, 0 assumptions, 2 `[NOTE FOR PM]`), coerente com stakes internos, com a ressalva do proxy já registrada em Decision-readiness.

## Downstream usability — adequate
Glossário completo; "Envelope de confiança", "Benchmark canônico" e "Log de custo" agora definidos; vocabulário `heuristica`/`confianca`/`estado` uniforme. IDs FR-1..FR-11 e NFR-1, SM-1/2/C1/C2 únicos e com referências que resolvem. UJs com protagonista único ("o agente") — aceitável para ferramenta interna de ator único.

### Findings
- **low** UJs cobrem 3 dos 11 FRs (§2.3) — FR-10 (arestas, os maiores fatos, Q9 do benchmark) e `docs`/`config`/`deps` não têm jornada; stories de FR-10 não herdam contexto. *Fix:* uma UJ-4 de uma frase para arestas de bytecode.
- **low** Addendum com texto desatualizado — o cabeçalho ainda diz "proposta de mecanismo de invocação via subagent" e a primeira seção diz "Falta medir o custo do grep equivalente (baseline de SM-1)", ambos superados pelas medições de 2026-10-02 no mesmo arquivo. *Fix:* ajustar as duas frases.
- **low** FR-8 sem consumidor nem retenção (§4.5) — nenhuma SM usa o log (SM-1 é benchmark offline) e o `gain` está fora do MVP; sem política de rotação o arquivo cresce sem limite. Aceitável como pedido do usuário. *Fix:* uma linha: "sem rotação na v1" ou um limite.

## Shape fit — strong
Capacidade enxuta, ator único, UJs de uma frase, brownfield bem referenciado (`AGENTS.md`, `SKILL.md`, `fact_state`, `snapshots_locais`). FR-7 e FR-11 são entregáveis de empacotamento misturados a requisitos de comportamento, mas isso é razoável para uma ferramenta interna.

## Mechanical notes
- **Assumptions Index:** vazio e sem `[ASSUMPTION]` inline; roundtrip fecha trivialmente (ver finding de proxy).
- **IDs:** FR-1..FR-11 contíguos e únicos, mas FR-9 e FR-10 aparecem em §4.1 antes de FR-3..FR-8 (ordem de leitura não numérica); sem lacunas. Sem referências quebradas (FR-5/FR-9 citadas em FR-10, FR-1 em FR-10 resolvem).
- **Glossário:** consistente; "SKILL.md" sem qualificar skill (ver high). Termo "Subagent" mantido no Glossário apesar de fora do MVP, ok porque referenciado em Non-Goals.
- **Números:** tabela do addendum bate com o texto do SM-1 e da Vision (0,3%–6,9%; Read 3,5KB–958KB; `grep` 365–3.031 B).
- **Memlog:** consistente com o PRD (decisões de fechamento); linha "(assumption) Pendentes ..." fica superada por decisões posteriores, sem impacto.

## Delta vs rodada 1
**Resolvidos (10):** limite de saída (FR-9); Tier 2/3 (FR-10); formato do envelope (FR-5, com vocabulário real e `fact_state`); definição de "desatualizado" (FR-4 lê `snapshots_locais`); FR-2 enumerado nos `awk` documentados + `[NOTE FOR PM]`; exemplo de saída por subcomando (FR-1, mas ver high de conflito com FR-11); instrumentação de SM-1/SM-2/SM-C1 (benchmark canônico, checagem estática, teste de contrato); OQ-1 e OQ-3 removidas; conflito FR-8 x FR-1 (log fora de `.scos-map/`); premissa da Vision medida; drift `heuristico`/`heuristica`, "Envelope" no glossário, dependência do addendum declarada em §0.
**Ainda abertos (atenuados):** conteúdo por subcomando para os JSON (antes "FR-1 só testa o contrato comum", agora só falta o conteúdo padrão); UJs cobrem poucos FRs; SM-2 ainda depende de amostragem de transcrições (agora declarado como tal); bytes como proxy de tokens (agora assumido explicitamente e com meta quantitativa).
**Novos nesta rodada:** conflito 30 linhas x documentação por subcomando (high); envelope para fatos múltiplos; teto em linhas vs bytes; SM-C2 frouxo frente à promessa da Vision; proxy como piso das metas; texto desatualizado no addendum; FR-8 sem consumidor.
