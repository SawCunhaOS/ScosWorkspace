# Validation Report — Scripts de Consulta Rápida para scos-map

- **PRD:** `/home/sawcunha/Projetos/SCOS/_bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Workspace-2026-09-14/prd.md`
- **Rubric:** `.claude/skills/bmad-prd/assets/prd-validation-checklist.md`
- **Run at:** 2026-10-02T11:05:03-03:00
- **Grade:** Poor

## Overall verdict
A rubrica considera a PRD madura para virar stories: tese única, evidência medida e decisões registradas com o que se abriu mão. Cinco dimensões estão *strong* e duas *adequate*, com 11 achados (0 críticos, 1 alto). O alto é um conflito de critérios: o limite de 30 linhas das skills (FR-11) não cabe junto dos exemplos e formatos por subcomando exigidos por FR-1, FR-6 e FR-7.

O revisor adversarial, que verificou o código e os fatos reais, discorda do grau de prontidão e levanta 2 críticos: (1) FR-5 reutiliza `fact_state`, que exige varredura do repositório e git a cada consulta, e não cobre `snapshots_locais`, que não tem `derivado_de` e sairia sempre `fresco` — falso-fresco na UJ-2; (2) o proxy do benchmark é otimista (cabeçalho fixo, Q3 ignora as transitivas, respostas não equivalentes, `jq` nunca medido). Pela regra de nota, qualquer achado crítico dá **Poor**, mas a nota subiu em substância: os 3 críticos da rodada 1 foram resolvidos ou reduzidos, e os 2 novos são mais estreitos e verificáveis. Os pontos em comum (conflito 30 linhas × exemplos, envelope para mais de um fato, teto só em linhas, proxy como piso) são os de maior confiança.

## Dimension verdicts
- Decision-readiness — strong
- Substance over theater — strong
- Strategic coherence — strong
- Done-ness clarity — adequate
- Scope honesty — strong
- Downstream usability — adequate
- Shape fit — strong

## Findings by severity

### Critical (2)

**[Adversarial]** — C1. FR-5: `fact_state` não é barato de reutilizar e não cobre `snapshots_locais` (§ FR-5, FR-4; scos-map.py:2742, 3819)
`fact_state(fato, files_by_path, files, root)` exige `scan_files` + MultiGit (git e hash de blobs) e, para bytecode, leitura de `target/classes`: contradiz "só lê fatos" e "não acessa o git", e a latência nunca é medida. Além disso `snapshots_locais` não tem `derivado_de` (verificado): passa por `fact_state` e sai sempre `fresco`, mesmo com o fato de 2026-09-14 já com 18 dias. Falso-fresco exatamente na UJ-2.
Fix: Decidir: pagar o `scan_files` (medir e assumir a latência) ou usar frescor barato (`head` gravado vs `git rev-parse HEAD`, `gerado_em`). Para `snapshots_locais`, comparar `repo_local.head` com o HEAD atual; teste: fixture velha não pode sair `fresco`. Considerar o custo de import de `scos-map.py` (hífen no nome, ~3,9 mil linhas).

**[Adversarial]** — C2. O proxy do CLI no benchmark é otimista e não valida SM-1 (§ `benchmark-baseline.py`, SM-1)
Cabeçalho fixo `alta/fresco` para todas as perguntas (na realidade há `resolvida`, `media`, `parcial`); Q3 ignora `_transitivas_comuns.tsv`, que o `SKILL.md` manda nunca ignorar; respostas não equivalentes (Q1, Q5); o script só mede bytes, nunca compara conteúdo; Q8 não filtra nada (os 10 itens estão `jar_desatualizado`); `jq` está instalado e nunca é medido; não há latência; o baseline do `Read` nunca foi verificado.
Fix: Rodar o CLI real assim que existir, com asserção de conteúdo; incluir `jq` como quarto caminho; medir latência; casos com `deps` dependente de transitivas e com mistura de estados; rotular a tabela como "estimativa otimista".

### High (7)

**[Rubrica · Done-ness clarity]** — Limite de 30 linhas conflita com a documentação exigida (§ FR-1, FR-6, FR-7, FR-11)
FR-1 e FR-6 exigem exemplo e formato por subcomando no `--help`/`SKILL.md`; com ~10 subcomandos são 30–50 linhas só de exemplos, e FR-11 limita o corpo da skill a 30. "SKILL.md" é ambíguo (qual das duas skills?). Os testes de aceitação não passam todos ao mesmo tempo.
Fix: Decidir onde mora o quê: exemplos e formato só no `--help`, skill com uma linha por subcomando; reescrever FR-1/FR-6/FR-7 para dizer "`--help`" e qual skill.

**[Adversarial]** — H1. Envelope incompleto: perde `completude`/`limitacoes`; "exatamente como constam" é falso (§ FR-5, SM-C1)
`layout.json` não tem `estado` nem `gerado_em`. O fato de conflitos é `resolvida` + `parcial` com árvore suja; `resolvida` nem está em SM-C1. O `status` imprime as limitações, o envelope não, e FR-4 as manda para o `--help`.
Fix: Acrescentar `completude=` e uma linha `# limitacao:` quando `parcial`; definir a fonte de cada campo; incluir `resolvida` em SM-C1.

**[Adversarial]** — H2. FR-9: teto só em linhas, ordem indefinida, "50 bastou" em amostra viciada (§ FR-9, FR-2, FR-10)
`ScosPaginated` tem 82 arestas internas de entrada e já estoura o teto. Não se diz quais 50 linhas sobrevivem nem se o cabeçalho conta; o aviso pode levar a concluir "o módulo não usa X". "Refine com filtro" conflita com FR-2, que fechou os filtros.
Fix: Teto duplo (linhas e bytes), ordem determinística, aviso "N de M casam", filtro de origem/destino explícito em FR-2 para FR-10; recalibrar com perguntas quentes.

**[Adversarial]** — H3. Experimento do subagent: n=1, unidades diferentes, equilíbrio de 120KB incoerente (§ addendum, §5)
34.315 tokens medidos contra 770 estimados por bytes/3,5. O equilíbrio de 120KB assume resumo a custo zero, mas a devolução literal "nunca" compensa; o limiar de 100KB não tem fundamento.
Fix: Reescrever como "hipótese descartada, amostra única, reabrir se aparecer digest" e remover o número 120KB/100KB.

**[Adversarial]** — H4. FR-4/UJ-2: `snapshots_locais` gera alarme constante (§ FR-4, UJ-2)
Todos os 10 itens estão `jar_desatualizado`; um commit de docs na Foundation marca todos os jars. O agente aprende a ignorar o sinal.
Fix: Mostrar a limitação na saída e agrupar por `produzido_por`, em vez de uma linha por GA.

**[Adversarial]** — H5. FR-11: critério mede linhas, não tokens, e as FRs 1/6/7/11 são incompatíveis (§ FR-11, FR-7, FR-1, FR-6)
O `SKILL.md` atual tem 218 linhas; reduzir a ponteiro apaga conteúdo (interpretação de confiança, armadilha do `deps.tsv`) sem inventário de para onde vai, e a armadilha das transitivas reintroduz o erro "o módulo não usa X".
Fix: Medir por caracteres/tokens; decidir onde moram os exemplos; listar o que a skill perde e onde fica.

**[Adversarial]** — H6. FR-2: "equivalente via CLI" de `awk` ad hoc é superfície vaga (§ FR-2, FR-7, FR-11)
Exemplos reais do `SKILL.md` usam operador numérico (`$10>5`) e glob sobre todos os módulos (`facts/*/deps.tsv`); a assinatura de FR-1 não os cobre. O conjunto muda quando FR-7/FR-11 reescrevem o `SKILL.md`.
Fix: Enumerar os filtros numa tabela fixa na PRD e congelar; incluir `deps` sem módulo e operadores numéricos.

### Medium (11)

**[Rubrica · Decision-readiness]** — Suposições fechadas sem ressalva sobre o proxy (§ §7 SM-1, §9)
A linha de base "9 de 9 ≤ 10% do Read" vem de um "proxy do CLI, que ainda não existe": é o recorte mínimo ideal, um limite inferior. As metas ficam coladas nesse piso (Q3 e Q9 já em +59 bytes). A amostra do subagent é n=1.
Fix: Manter um `[ASSUMPTION]` indexado ("o CLI real fica dentro da margem do proxy") com dono e condição: rodar o benchmark contra o CLI na primeira story.

**[Rubrica · Strategic coherence]** — SM-C2 não protege a promessa da Vision (§ §1 vs §7)
A Vision promete ser mais barato que o `grep` na maioria das perguntas, mas SM-C2 só exige "nunca acima do Read". Somando skill e `--help`, Q4 (130 B vs 474 B) e Q6 (224 B vs 365 B) podem passar a custar mais que o `grep` sem violar métrica.
Fix: Benchmark de sessão (N perguntas seguidas, docs contados uma vez) comparado ao `grep`, ou reduzir a promessa da Vision.

**[Rubrica · Done-ness clarity]** — Envelope de FR-5 indefinido para subcomando que lê mais de um fato (§ FR-5, §8)
`deps` lê `deps.json` e `deps.tsv`, mas FR-5 prevê um único cabeçalho. Com estados diferentes, não se sabe qual vai nele; SM-C1 fica não verificável.
Fix: Regra explícita (pior caso entre os fatos, ou duas linhas de cabeçalho) e um caso de teste.

**[Rubrica · Done-ness clarity]** — Teto medido em linhas, não em bytes (§ FR-9)
50 linhas de `config.json` ou `bytecode_edges.tsv` podem passar de 5–7KB; o benchmark (maior resposta: 17 linhas) não exercita o pior caso.
Fix: Teto de bytes por linha ou total, ou teste com o maior fato de cada tipo.

**[Rubrica · Done-ness clarity]** — Conteúdo padrão dos subcomandos JSON não especificado (§ FR-1, FR-2, addendum)
O que `layout`, `config`, `docs` e `reactor` devolvem sem filtro fica para a primeira story; os testes de FR-2 só cobrem os `awk` dos TSVs.
Fix: Uma linha por subcomando JSON com campos e ordem, mesmo esboçada.

**[Adversarial]** — M1. SM-1: meta ≤10% quebra em fatos pequenos; meta de TSV é circular (§ SM-1)
O cabeçalho (~58 B) sozinho passa de 10% de um fato de 617 bytes. A tolerância de TSV (60 B) está calibrada ao resultado: Q9 sai por 59 B. 80% de 4 JSON é "todas".
Fix: Meta de ≤10% só para fatos acima de X KB; tolerância de TSV em número absoluto e percentual; dizer que 9 perguntas são regressão, não generalização.

**[Adversarial]** — M2. Motivação: TSV "só interface única" vs. custo do envelope e FR-10 (§ §1, FR-10)
Para TSV o ganho em bytes é ~0, mas FR-10 (maior risco) está no MVP e SM-1 mede exatamente o que não rende.
Fix: Registrar que o ganho em TSV é acurácia/envelope e medir isso (ex.: aviso de `bytecode_edges.tsv` obsoleto).

**[Adversarial]** — M3. Resíduos da decisão revertida do subagent e §8/§9 "Nenhuma" (§ §4.4, glossário, addendum)
§4.4 ainda fala em "subagent intermediário"; o addendum ainda diz que o desenho com agente "fica como ponto de partida"; há `[NOTE FOR PM]` abertas.
Fix: Podar glossário e §4.4; mover o experimento ao addendum.

**[Adversarial]** — M4. FR-8: raiz do workspace ambígua, concorrência e log sem leitor (§ FR-8)
Se o agente roda de dentro de um repo, "raiz do workspace" é ambígua; appends concorrentes sem lock podem intercalar linhas; ninguém consome o log.
Fix: Definir a raiz como o diretório que contém `.scos-map/workspace.json` (ou variável de ambiente); limite/rotação ou cortar FR-8 até existir o `gain`.

**[Adversarial]** — M5. NFR-1: nome "fixo" diverge do comando real (§ NFR-1, glossário)
Não há wrapper/PATH; o agente digitará `python3 ferramentas/scos-map/scos-map-query.py`, e a skill carregaria esse caminho em cada exemplo. Versão mínima de Python não dita.
Fix: Fixar o comando literal e a versão mínima de Python.

**[Adversarial]** — M6. Filtro com zero resultado lido como "não usa X" (§ FR-1, FR-2, FR-10)
Só FR-3 trata zero linhas; um `deps` filtrado por `jjwt` com zero casas parece "o módulo não usa jjwt", errado pela armadilha das transitivas.
Fix: Toda saída lista fontes consultadas e contagem de casamentos.

### Low (8)

**[Rubrica · Strategic coherence]** — SM-2 sem método de amostragem (§ §7)
Sem tamanho de amostra, período nem linha de base.
Fix: Fixar N e janela, ou declarar verificação manual pontual.

**[Rubrica · Done-ness clarity]** — Cabeçalho de FR-3 com reticências (§ FR-3)
`# confianca=alta estado=fresco ... | 0 conflitos` não bate com o formato exato de FR-5.
Fix: Alinhar o exemplo a FR-5 e declarar o sufixo.

**[Rubrica · Downstream usability]** — UJs cobrem 3 dos 11 FRs (§ §2.3)
FR-10 (arestas, os maiores fatos) e `docs`/`config`/`deps` não têm jornada.
Fix: UJ-4 de uma frase para arestas de bytecode.

**[Rubrica · Downstream usability]** — Addendum com texto desatualizado (§ addendum)
O cabeçalho ainda fala em "proposta de mecanismo via subagent" e uma seção diz "Falta medir o grep equivalente", ambos superados.
Fix: Ajustar as duas frases.

**[Rubrica · Downstream usability]** — FR-8 sem consumidor nem retenção (§ §4.5)
Nenhuma SM usa o log e o `gain` está fora do MVP; sem rotação o arquivo cresce sem limite.
Fix: Uma linha: "sem rotação na v1", ou um limite.

**[Adversarial]** — L1. Q7/Q8: baseline do `Read` é só 18,5KB (§ Q7, Q8)
A economia absoluta é modesta (~5k tokens); o valor dessas consultas é semântico, não de bytes.
Fix: Registrar isso.

**[Adversarial]** — L2. UJs cobrem 3 dos 8 subcomandos (§ §2.3)
FR-10, o maior risco, está no MVP sem jornada.
Fix: UJ de arestas.

**[Adversarial]** — L3. Benchmark não portável (§ `benchmark-baseline.py`)
Caminho absoluto, timestamp fixo, mapa de repos ignorados pelo git e script não versionado; "repetível" só nesta máquina e estado.
Fix: Fixtures em `tests/` ou registrar o hash do mapa usado.

## O que está bom
Preservar: FR-4 lê o fato `snapshots_locais`, que existe com os campos citados (verificado); envelope com cabeçalho único e marca só quando difere, com teste de contrato; medição real em lugar de suposição (a inversão `Read` vs `grep` nos JSON é genuína); descarte do subagent no MVP; NFR-1 stdlib-only confere com `scos-map.py`; teste golden por subcomando e erro com o comando de build a rodar.

## Mechanical notes
- Delta vs rodada 1 (rubrica): cerca de 10 achados resolvidos — limite de saída (FR-9), Tier 2/3 (FR-10), formato do envelope, definição de "desatualizado" (FR-4), FR-2 enumerado, instrumentação de SM-1/SM-2/SM-C1, OQ-1 e OQ-3, conflito FR-8×FR-1, premissa da Vision medida e drift de glossário. Atenuados: conteúdo por subcomando, UJs, SM-2. Novos: 7.
- Delta vs rodada 1 (adversarial): resolvidos os críticos de tokens reais do FR-8 e de teto de saída; SM-1 e FR-4 resolvidos só em parte (surgiram C1 e C2); abertos: escopo TSV, exemplo por subcomando, jornadas. O adversarial trouxe 2 críticos novos que a rubrica não viu, ambos verificados no código.
- Assumptions Index vazio e sem `[ASSUMPTION]` inline: o roundtrip fecha, mas ver o achado do proxy (rubrica) e C2 (adversarial).
- IDs FR-1..FR-11, NFR-1, SM-1/2/C1/C2 contíguos e únicos; FR-9 e FR-10 aparecem em §4.1 antes de FR-3..FR-8 (ordem de leitura não numérica). Tabela do addendum bate com o texto de SM-1 e da Vision.
- Memlog consistente com o PRD; a linha "(assumption) Pendentes ..." está superada por decisões posteriores, sem impacto.

## Reviewer files
- `review-rubric.md`
- `review-adversarial-general.md`
