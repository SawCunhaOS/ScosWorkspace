# Reconciliação do memlog com prd.md e addendum.md

Escopo: `.memlog.md` (37 entradas, linhas 6 a 42; as linhas 1 a 4 são frontmatter) contra `prd.md` (319 linhas, 14 FRs) e `addendum.md`. Os números das entradas são os números de linha do arquivo. Legenda: **PRD** = refletida no PRD; **ADD** = refletida no addendum; **SUP(n)** = superada pela entrada n; **EVT** = evento histórico, não é requisito; **PARCIAL** = refletida com desvio, descrito na nota.

## 1. Auditoria do memlog

| # | Tipo | Resumo | Situação | Onde / nota |
|---|---|---|---|---|
| 6 | note (user) | Pedido inicial: scripts Python pequenos, saída estilo grep, voltados à estrutura do scos-map | PRD | §1 Vision, §3 "Saída estilo grep", FR-1. O "scripts" no plural virou um CLI único por decisão do usuário (14). |
| 7 | insight (user) | A dor é custo de tokens, não latência | PRD | §1 Vision, SM-1. A latência sobrevive como NFR-2. Ver lacuna L1: a métrica é bytes, não tokens. |
| 8 | decision (user) | Interno, fast path, só o agente, Tier 1 a 3 | PRD | §2.2 (só o agente), §6.1. A parte "Tier 1 a 3" foi reduzida por 18/38 e restaurada por 18 e 42. Stakes e modo são metadado de processo e não aparecem no PRD (aceitável). Ver L5. |
| 9 | idea (user) | Subagent com modelo barato devolve dados curados; menos alucinação, saída bruta fora do contexto | SUP(32) | Descartada do MVP em §5 e no experimento do addendum. Passou por 13, 24 e 25 antes. |
| 10 | note | Levantamento: scos-map.py sem modo de consulta, JSON minificado em uma linha, tamanhos | ADD | "Evidência de tamanho" do addendum, §1 Vision. |
| 11 | note | Prior art: jq, ast-grep/ripgrep, ctags, Aider | ADD | "Prior art considerado". O jq virou concorrente medido em SM-1 (35). |
| 12 | decision (PM) | A saída compacta carrega confiança/frescor | PRD | FR-5, §4.3. |
| 13 | decision (PM) | Subagent como requisito de capacidade (CLI estável); orquestração vai ao addendum | SUP(24, 32) | O contrato estável sobrevive em FR-6. O addendum não tem seção de orquestração: só o experimento descartado. A justificativa "consumo por subagent" sumiu de FR-6, que fala em "automações". |
| 14 | decision (user) | Comandos por fato, cross-repo na v1, interface única JSON+TSV (contra a recomendação de escopo mínimo) | PRD, ADD | FR-1, FR-2, FR-3, FR-4; addendum "Opções de desenho" e "Sobreposição com TSV". |
| 15 | event | Rascunho completo (7 FRs, 4 features, 2 OQ) | EVT, SUP(23) | A contagem está obsoleta. |
| 16 | decision (user) | Novo requisito: log de custo por chamada; fase 1 proxy de tamanho, fase 2 tokens reais | PARCIAL | Fase 1 em FR-8. Fase 2 foi superada por 20 (e por §6.2). Ver L2. |
| 17 | event | Validação 1: grade Poor, 3 críticos, 10 altos | EVT | Relatórios `validation-report-r1.*`. |
| 18 | decision | Tier 2/3 volta ao MVP via `arestas` (FR-10) | PRD | FR-10, §6.1. Ampliada por 42. |
| 19 | decision | FR-4 com regra determinística (jar mais antigo que o commit) e exceção a "só lê fatos" | SUP(26, 34) | 26 removeu a exceção; 34 trocou por frescor barato (HEAD gravado contra HEAD lido). |
| 20 | decision | FR-8 só bytes/linhas; tokens reais saem | PRD | FR-8, §6.2, addendum "Log de custo". Decisão de PM, sem confirmação do usuário (ver L2). |
| 21 | decision | SM-1 canônico: CLI ≤10% do Read e ≤ grep em ≥80% | SUP(31, 39) | Refinada em SM-1 (por tipo de fato; sem meta ≤10% abaixo de 2KB). |
| 22 | decision (PM) | FR-9 teto de 50 linhas; envelope com enum atual/obsoleto/heuristica; OQ-1/OQ-3 removidas; log fora de `.scos-map/`; FR-2 limitado; SM-2/SM-C1; SM-C2 e NFR-1 | PARCIAL | FR-9, FR-8, FR-2, SM-2, SM-C1, SM-C2, NFR-1 e §8 (sem OQ) estão no PRD. O enum `atual\|obsoleto\|heuristica` foi superado por 27 e 34; o teto de 50 linhas por 36. |
| 23 | change | PRD com 10 FRs, 1 NFR, 1 OQ | EVT, SUP(42) | Desatualizada. O PRD atual tem FR-1 a FR-14, NFR-1/2 e 0 OQ. |
| 24 | decision (user) | Skills pequenas; subagent no MVP como FR-11 (skill + agente), com gate experimental | SUP(32) | A parte "skills pequenas" está em FR-11 (descrição ≤160 chars, corpo ≤30 linhas e ≤2.000 chars). O agente dedicado caiu em 32. |
| 25 | decision (user) | Subagent só quando compensa; chamada direta por padrão; delegar se a saída exceder o teto | SUP(32) | "Chamada direta" está em FR-11/§4.6. A regra de delegação condicional não está no PRD. |
| 26 | decision | FR-4 só lê `snapshots_locais`; exceção removida | PRD | FR-4 ("O CLI só lê o fato e `.git/HEAD`"). |
| 27 | decision | FR-5 propaga `confianca`/`estado` reais, sem remapear | PRD | FR-5, §3 Glossário. 34 acrescentou `desconhecido`. |
| 28 | decision | OQ-2 resolvida (só `deps` combina json+tsv); caminhos do CLI e do log firmes; stdlib | PRD, ADD | FR-1 (`deps`), FR-8, NFR-1, addendum "Pendências". |
| 29 | assumption | Pendentes: Vision, teto de 50 linhas, metas de SM-1, modelo/limiar de FR-11 | SUP(30, 31, 32) | 30 fechou Vision e teto; 31 as metas; 32 tornou o modelo/limiar de FR-11 sem objeto. |
| 30 | decision | Medição: Read 3,5KB a 958KB contra grep; Vision confirmada; o teto de 50 linhas bastou (maior resposta 17) | PARCIAL, SUP(35, 36) | A Vision e as medidas estão em §1 e no addendum. A frase "maior resposta 17" foi contradita pela Q10 (107 linhas) de 35; FR-9 hoje registra o estouro. |
| 31 | decision (user) | SM-1 por tipo de fato (JSON e TSV) | PRD | SM-1. Refinada por 39. |
| 32 | decision (user) | Experimento: Haiku 34.315 tokens contra ~770 direto; FR-11 só skill fina; subagent não-objetivo, reaberto só para saídas >100KB | PARCIAL | §5, FR-11, addendum "Experimento". O gatilho de reabertura mudou de ">100KB" para "digest que preserve o cabeçalho, com teste de fidelidade" (ver L3). |
| 33 | event | Validação 2: Poor por regra, 2 críticos novos | EVT | `validation-report-r2.*`. |
| 34 | decision | Frescor barato (HEAD gravado contra `.git/HEAD`); `snapshots_locais` agrupado por produtor; estado `desconhecido` | PRD, ADD | FR-5, FR-4, §3 "Frescor barato", addendum "Verificação do frescor". |
| 35 | decision | Benchmark refeito (cabeçalho real, Q3 com transitivas, jq como 4º caminho, Q10 quente, asserção de conteúdo) | PRD, ADD | SM-1, addendum "Medições", FR-6. |
| 36 | decision | Envelope com completude/limitação/desvios, rodapé N de M, teto duplo 50 linhas + 6000 B, filtros de arestas | PRD | FR-5, FR-9, FR-2. |
| 37 | decision | FR-11 mede linhas e caracteres; exemplos só em `--help`; inventário no addendum; FR-2 vira tabela com 3 awk | PRD, ADD | FR-11, FR-2, addendum "Inventário". |
| 38 | decision | 3 linhas de roteamento sem subcomando; exceções motivadas; "Tier 1 a 3 completo" só para arestas | SUP(42) | Superada: FR-12, FR-13 e FR-14 fecham 12 de 12 em FR-7. |
| 39 | decision | Medianos: SM-1 sem meta abaixo de 2KB, TSV ≤ máx(grep+64B, 1,1×grep); SM-C2 por sessão; SM-2 N=20/5 sessões; FR-8 com raiz por ancestral; NFR-1/2; UJ-4/5 | PRD | SM-1, SM-C2, SM-2, FR-8, NFR-1, NFR-2, §2.3. |
| 40 | assumption | Pendentes: SM-1 (CLI real), FR-5 (frescor), NFR-2 (latência) | PARCIAL, SUP(41) | Frescor e latência foram fechados por 41. Só SM-1 resta em §9. |
| 41 | decision | Frescor verificado nos 3 repos; falso-obsoleto aceito; latência ≈10 ms contra teto de 300 ms; resta só SM-1 | PRD, ADD | §9, FR-5, NFR-2, addendum. |
| 42 | decision (user) | Incluir tests, bytecode e callgraph no MVP (FR-12/13/14); roteamento 12/12; benchmark de 12 perguntas | PRD, ADD | FR-12, FR-13, FR-14, FR-7, §6.1, addendum. Mais recente. |

### Resultado
- Total: 37 entradas.
- Refletidas integralmente (PRD/ADD): 6, 7, 10, 11, 12, 14, 18, 20, 26, 27, 28, 31, 34, 35, 36, 37, 39, 41, 42.
- Superadas ou revertidas: 9, 13, 19, 21, 24, 25, 29, 38 (mais as parcialmente superadas 16, 22, 30, 40).
- Eventos históricos, sem requisito: 15, 17, 23, 33.
- Com desvio entre memlog e PRD (PARCIAL): 8, 16, 22, 30, 32, 40.
- **Órfãs (nem refletidas nem superadas): 0.** Nenhuma decisão ficou sem destino.
- Desatualização do próprio memlog:
  - A entrada 23 e o frontmatter (`topic`) não registram a contagem atual (14 FRs).
  - Não há entrada sobre a Validação 3, embora 42 tenha adicionado 3 FRs depois da rodada 2.
  - O PRD segue com `status: draft`.

### Itens do PRD sem entrada correspondente no memlog (rastreabilidade inversa)
- Checagem de `schema_versao` 2.1 (FR-1), vinda do SKILL.md.
- Flag `--base` (FR-5), `motivo_vazio` (FR-10), baldes e `provavel_falso_positivo` (FR-13).
- A regra de `desvios[]` e UJ-1 a UJ-3 aparecem só como derivação do SKILL.md atual.
- Isso é derivação, não invenção, mas as decisões não têm trilha no memlog.

## 2. Reconciliação de inputs (ideias e intenções do usuário que a estrutura de FRs deixou cair)

**L1. A dor declarada é tokens (entrada 7), mas nada no PRD mede tokens.**
- O SM-1 mede bytes, e o número de "~770 tokens" é estimativa bytes/3,5.
- O único número de tokens medido (34.315, do subagent) é de outra grandeza.
- Para o usuário, "mais barato em tokens" é o critério de sucesso. O PRD o substitui por proxy de bytes. Isso está declarado ("estimativa com proxy"), mas não há nem sugestão de como validar tokens reais (por exemplo, o contador do `/context` antes e depois).
- A promessa da Vision ("mais barato em tokens") é mais forte do que o que o SM-1 prova.

**L2. O pedido explícito de log de custo (16, "decision by user") foi reduzido por decisão de PM (20) sem confirmação registrada.**
- Sobrou o log de bytes/linhas sem leitor: `gain` está fora do MVP e FR-8 admite "leitura manual".
- A intenção do usuário era a economia "verificável ao longo do tempo". O artefato entregue só grava.
- Falta um critério mínimo de consumo, por exemplo um comando de soma ou o uso do log como evidência de SM-2/SM-C2.
- A fase 2 (tokens reais) ficou como "spike condicional", sem dono nem gatilho de revisão.

**L3. Subagent: a intenção do usuário (9, 24, 25, 32) foi trocada por uma regra diferente da que ele decidiu, com evidência fraca.**
- O objetivo original tinha dois ganhos: menos alucinação e saída bruta fora do contexto principal. O PRD só trata o segundo, e só para dizer que não funciona com saída literal.
- O gatilho de reabertura que o usuário disse (32, ">100KB") não está no PRD. O PRD pôs "digest que preserve o cabeçalho com teste de fidelidade".
- A regra do usuário (25) de "delegar só se a saída exceder o teto" desapareceu junto com o agente.
- O descarte se apoia em amostra única e em uma comparação entre grandezas diferentes (tokens totais de um subagent contra uma estimativa em bytes). O próprio addendum admite isso.
- A entrada 13 pedia que o contrato estável fosse feito "para consumo por subagent". FR-6 diz "automações" e perdeu a justificativa.

**L4. Interface única que "substitui o padrão awk" (14): o awk some da skill, mas o CLI cobre só 3 filtros congelados.**
- FR-11 enxuga o `SKILL.md`, portanto as dicas de `awk` saem. FR-2 congela os filtros e recusa "todo awk possível".
- Para uma pergunta TSV fora dos 3 filtros, o fallback de FR-7 é `Read` do fato bruto. Em `bytecode_edges.tsv` isso são 958KB, exatamente a dor da entrada 7.
- O fallback de TSV (`grep`/`awk` direto, não `Read`) não está especificado. A decisão do usuário contra o escopo mínimo trouxe uma lacuna de caminho ruim que o PRD não fecha.

**L5. Tom e escopo: "Interno, Fast path" (8) contra um PRD que cresceu para 14 FRs, 2 NFRs, 12 perguntas de benchmark e 2 rodadas de validação com grade Poor.**
- Ninguém registrou, e o usuário não confirmou, que o escopo pós-validação ainda é "fast path".
- A rodada 2 terminou em "Poor por regra" e as correções foram aplicadas sem uma Validação 3. Depois delas, 42 acrescentou FR-12 a FR-14.
- O PRD continua `draft`, com os 3 FRs mais novos nunca validados.
- Recomendação: registrar a decisão sobre o nível de rigor ou rodar a validação final antes do `bmad-build`.

**Sem lacuna:** o pedido inicial (6), a decisão cross-repo e Tier 1 a 3 (8, 14, 42), skills finas (24, 37), envelope de confiança (12) e "só o agente chama" (8, §2.2) estão fielmente refletidos.
