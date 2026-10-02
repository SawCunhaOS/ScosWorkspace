# Validation Report — Scripts de Consulta Rápida para scos-map

- **PRD:** `/home/sawcunha/Projetos/SCOS/_bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Workspace-2026-09-14/prd.md`
- **Rubric:** `.claude/skills/bmad-prd/assets/prd-validation-checklist.md`
- **Run at:** 2026-10-02T10:36:09-03:00
- **Grade:** Poor

## Overall verdict
A PRD tem tese nítida e bem fundamentada (o `Read` de JSON minificado custa mais tokens que `grep`; o CLI `scos-map-query` com envelope de confiança corrige isso sem sacrificar acurácia) e forma adequada a uma ferramenta interna de ator único. O risco está na verificabilidade: nada limita o tamanho da saída, SM-1/SM-2/SM-C1 não têm instrumentação e o escopo de Tier 2/3 decidido no memlog sumiu do MVP sem aviso.

A revisão adversarial muda o peso do quadro: levanta 3 achados críticos — SM-1 sem baseline e com meta de empate, FR-8 inviável como descrito (o script não enxerga o uso de tokens do subagent) e FR-4 sem definição de "desatualizado" além de violar "só lê fatos" — e conclui que a PRD não está pronta para `bmad-build`. Pela regra de nota (qualquer achado crítico = Poor) o grau é **Poor**, embora o revisor de rubrica não tenha classificado nada como crítico; os pontos convergentes entre os dois (limite de saída, métricas, Tier 2/3, envelope FR-5, OQ-1/OQ-3) são os de maior confiança.

## Dimension verdicts
- Decision-readiness — adequate
- Substance over theater — strong
- Strategic coherence — adequate
- Done-ness clarity — thin
- Scope honesty — adequate
- Downstream usability — adequate
- Shape fit — strong

## Findings by severity

### Critical (3)

**[Adversarial]** — C1. SM-1 não é testável nem ambicioso (§ prd:177)
Meta "paridade ou menos que o grep": empate já é fracasso frente à Vision. "Grep equivalente" não é definido (respostas não equivalentes). O log de FR-8 só mede o lado do CLI, então SM-1 não é computável a partir dele. Unidade é bytes, não tokens; a premissa nunca foi medida.
Fix: Benchmark fechado de N perguntas canônicas; medir offline `Read`, grep e CLI; meta numérica (ex.: CLI ≤10% do `Read` e ≤ grep em ≥80%), exigindo resposta correta.

**[Adversarial]** — C2. FR-8: "tokens reais via subagent" é inviável como descrito (§ prd:144, add:48)
O script roda dentro do Bash do subagent e não vê o bloco de uso, que só chega ao orquestrador. Persistir exigiria escrita extra do LLM principal, custando tokens. A assumption real ("a orquestração é capturável por script") não está verificada.
Fix: Reduzir FR-8 a log de bytes/linhas, ou fazer um spike com critério de saída (existe API/hook que entregue isso a um script?).

**[Adversarial]** — C3. FR-4 viola "só lê fatos" e não define "desatualizado" (§ prd:95, prd:99, prd:45)
Exige inspecionar `~/.m2` e o estado do git em tempo de consulta. "Desatualizado" e "recentemente" não têm critério; um falso "não desatualizado" faz a UJ-2 rodar build com SNAPSHOT velho.
Fix: Verificar o que `workspace.json` já tem; se nada, cortar da v1 ou escrever regra determinística (jar mais antigo que o último commit = desatualizado; sem `~/.m2` = "desconhecido", nunca "não").

### High (10)

**[Rubrica · Strategic coherence]** — Métricas sem instrumentação (§ §7 SM-1, SM-2, SM-C1)
A linha de base do grep, o denominador de SM-2 e a detecção de SM-C1 não têm origem definida; o log só cobre o CLI.
Fix: Dizer como cada SM é medido (SM-1: benchmark fixo de N perguntas; SM-2: amostragem de transcrições; SM-C1: teste automatizado com fato `obsoleto`/`heuristico`).

**[Rubrica · Done-ness clarity]** — Nenhum limite de tamanho de saída (§ FR-1)
`files` sem filtro continua com 952 linhas/222KB; sem teto ou paginação o CLI repete o problema da Vision.
Fix: Teto padrão de linhas com aviso de truncamento e flag explícita para desligar.

**[Rubrica · Done-ness clarity]** — Tier 2/3 contradiz o memlog (§ §6.2, §4.1 vs. memlog)
Nenhum subcomando cobre `bytecode_edges.tsv`/callgraph, os maiores arquivos. A decisão do usuário ("Tier 1 a 3 completo") foi de-escopada sem sinalização.
Fix: Incluir subcomando de arestas de bytecode ou registrar a redução como `[NOTE FOR PM]` e atualizar o memlog.

**[Rubrica · Done-ness clarity]** — FR-5 sem formato nem granularidade (§ FR-5)
A confiança é por fato, não por linha; não diz como mapear nem como representar `obsoleto` e `heuristico` ao mesmo tempo. FR-6 e SM-C1 ficam não testáveis.
Fix: Fixar o formato (ex.: coluna final `[atual|obsoleto|heuristica]`) e o comportamento com dois estados.

**[Adversarial]** — H1. Escopo vs. dor: TSV e "todo awk" (§ prd:78, add:13, add:27, add:33)
A dor é dos JSON; FR-2 ("todo filtro awk") é ilimitado, não testável e vira o mini-DSL genérico que o addendum descartou. Alternativa barata nunca avaliada: o gerador emitir fatos um campo por linha (NDJSON ou `chave<TAB>valor`) ou uma receita de uma linha no `SKILL.md`.
Fix: Registrar a alternativa na tabela do addendum e limitar FR-2 às linhas `awk` literais do `SKILL.md`/`AGENTS.md`, cada uma com teste.

**[Adversarial]** — H2. Sem limite de saída (§ add:43, prd:68)
O addendum diz que FR-5/FR-6 "já garantem" saída pequena; não garantem. `files` sem filtro é o fato inteiro linha a linha (222KB/952 linhas).
Fix: Novo FR: teto padrão (ex.: 50 linhas), `--limit`/`--all` e linha "N linhas omitidas"; teste de que nenhuma invocação sem `--all` excede o teto.

**[Adversarial]** — H3. Subagent pode aumentar tokens e reintroduzir alucinação (§ add:39-40, add:43, prd:52)
Cada delegação paga prompt, resposta e system prompt; com saída de 1–5 linhas custa mais. O resumo é lossy e pode derrubar o envelope de confiança que SM-C1 protege. A assumption contamina FR-6.
Fix: Tirar a assumption de FR-6; registrar como hipótese com experimento (CLI direto vs. via subagent: tokens totais e fidelidade da flag `obsoleto`).

**[Adversarial]** — H4. FR-5 "toda linha": custo por linha e semântica indefinida (§ prd:108, prd:112, prd:183)
Repetir marcador em cada linha multiplica tokens (oposto de SM-1). Granularidade (fato vs. entrada) indefinida. `obsoleto` é computado (mtimes), não persistido: escopo escondido. `heuristica`/`heuristico` inconsistente.
Fix: Definir enum, granularidade e fonte de `obsoleto`; envelope uma vez no cabeçalho e marca por linha só quando difere.

**[Adversarial]** — H5. SM-2 e SM-C1 não mensuráveis (§ prd:180, prd:183)
SM-2 não tem denominador nem instrumentação (o log não registra `Read`). "Tratada como atual" em SM-C1 é decisão do agente, não observável.
Fix: SM-2 como checagem estática da tabela de roteamento + amostragem; SM-C1 como teste de contrato com fixture `obsoleto`.

**[Adversarial]** — H6. Contradições entre PRD, memlog e open questions (§ prd:172, prd:187, prd:189, prd:72)
Memlog diz "Tier 1 a 3 completo" e a PRD exclui; OQ-1 já decidida em §6.2; memlog diz 7 FRs/2 OQ e a PRD tem 8/3; OQ-3 cogita log em `.scos-map/`, o que fere FR-1 e pode ser acusado como sujeira.
Fix: Decidir e remover OQ-1 e OQ-3 (log fora de `.scos-map/` e do git); declarar o destino de Tier 2/3.

### Medium (16)

**[Rubrica · Decision-readiness]** — OQ-1 já respondida (§ §8 item 1 vs §6.2)
A PRD diz que o subagent está fora do MVP e depois pergunta se entra.
Fix: Remover a pergunta ou reformulá-la como gatilho de revisão.

**[Rubrica · Decision-readiness]** — OQ-3 sem default (§ §8 item 3, FR-8)
Decide se SM-1 é por projeto ou global e se o log fere a regra de FR-1.
Fix: Propor default (log único no workspace, fora de `.scos-map/`) e marcá-lo `[ASSUMPTION]`.

**[Rubrica · Substance over theater]** — Premissa central não medida (§ §1 Vision, addendum "Evidência de tamanho")
"Mais caro que grep" é tratada como fato e não aparece como `[ASSUMPTION]`.
Fix: Medir 2–3 perguntas reais (grep vs `Read`) ou marcar como assumption. Esse número também é a linha de base de SM-1.

**[Rubrica · Strategic coherence]** — SM-1 usa bytes como proxy de tokens (§ FR-8, §6.2)
"Paridade ou menos" que o grep é limiar frouxo, quase indistinguível do status quo.
Fix: Limiar quantitativo (ex.: ≤50% dos bytes do grep) ou justificar a paridade.

**[Rubrica · Done-ness clarity]** — FR-4 não define "desatualizado" (§ §4.2)
Não diz o que é comparado (mtime do jar vs. HEAD? hash?) nem se `workspace.json` já carrega o dado; o CLI "nunca compila nem escreve".
Fix: Nomear o campo ou a regra de comparação e confirmar a fonte.

**[Rubrica · Done-ness clarity]** — FR-2 "sem perda de cobertura" difícil de verificar (§ FR-2)
Não há conjunto enumerado de consultas `awk` com equivalente.
Fix: Listar as consultas do `SKILL.md` como casos de aceitação.

**[Rubrica · Done-ness clarity]** — FR-1 só testa o contrato comum (§ FR-1)
Nenhuma consequência por fato (`layout`, `config`, `docs`, `reactor`) nem exemplo de saída.
Fix: Um exemplo de saída por subcomando no addendum.

**[Rubrica · Scope honesty]** — Suposição mal classificada em FR-6 (§ §4.4)
A orquestração via subagent é decisão de escopo já tomada, não inferência por confirmar; FR-6 fica sem a exigência de capacidade que o memlog prometeu.
Fix: Virar nota de escopo; manter como assumption só o não confirmado.

**[Rubrica · Scope honesty]** — Assumptions não marcadas (§ vários)
(a) JSONs estáveis o bastante para fixar subcomandos; (b) `Read` de JSON minificado é o caminho usado hoje; (c) o log pode ser escrito sem violar "nunca escreve em `.scos-map/`".
Fix: Marcar e indexar.

**[Rubrica · Scope honesty]** — Conflito FR-8 × FR-1 (§ FR-1 Out of Scope, FR-8)
FR-1 proíbe escrever em `.scos-map/`; FR-8 grava um log cujo local pode ser `.scos-map/` (OQ-3).
Fix: Declarar o log fora de `.scos-map/` e reescrever a exceção em FR-1.

**[Adversarial]** — M1. FR-1 não define o que cada subcomando devolve (§ prd:68)
"Recorte textual": sem esquema para `layout`, `config`, `deps`, `docs`, `reactor`; achatar o `config.json` de 142KB exige regras.
Fix: Exemplo real de 3–5 linhas por subcomando no addendum, que serve de teste de aceitação.

**[Adversarial]** — M2. FR-6 "contrato estável" é circular (§ FR-6)
"Atualizar a documentação no mesmo commit" é processo, não requisito testável.
Fix: Testes golden por subcomando em `ferramentas/scos-map/tests/`.

**[Adversarial]** — M3. Vazio vs. erro ambíguo (§ prd:92, prd:69)
Saída vazia também ocorre com `workspace.json` ausente ou obsoleto; o agente concluiria "sem conflitos".
Fix: Sempre emitir ao menos o cabeçalho de confiança ("0 conflitos | confianca=atual").

**[Adversarial]** — M4. Ausência de requisitos não-funcionais (§ geral)
Sem versão do Python/dependências, caminho do script, regra de allowlist de Bash, compatibilidade com a pasta de testes. Título diz "Scripts", Vision diz "CLI único".
Fix: Seção curta de NFR/integração: stdlib, caminho único, allowlist, cobertura por subcomando.

**[Adversarial]** — M5. Custo de descoberta e round-trips ignorados (§ geral)
`--help`/`SKILL.md` carregados e várias chamadas podem anular o ganho; nenhuma métrica cobre.
Fix: Contra-métrica: tokens totais por pergunta canônica, incluindo documentação e todas as chamadas.

**[Adversarial]** — M6. FR-7 sem critério de adesão (§ FR-7)
"Read vira fallback" não impede o agente de usar `Read`; só existência de linhas é testada.
Fix: Assumir que adesão é verificável por amostragem; aviso no `SKILL.md` com o tamanho dos fatos grandes.

### Low (7)

**[Rubrica · Decision-readiness]** — `[NOTE FOR PM]` só em itens seguros (§ §6.2)
A tensão FR-2 vs. rejeição do jq genérico fica sem aviso.
Fix: Adicionar um NOTE em FR-2.

**[Rubrica · Done-ness clarity]** — FR-7 testa existência, não comportamento (§ FR-7)
"Ou está listada como exceção" deixa o teste passar trivialmente.
Fix: Opcional.

**[Rubrica · Downstream usability]** — FR-6 e FR-8 dependem do addendum "não normativo" (§ §4.4, §4.5)
A extração de stories pode perder a dependência.
Fix: Citar o trecho na FR ou tornar o addendum leitura obrigatória.

**[Rubrica · Downstream usability]** — UJ-1 realiza só `layout` (§ UJ-1)
Nenhuma jornada exercita `config`, `deps` ou `docs`.
Fix: Opcional.

**[Adversarial]** — L1. Título provisório e nome normativo informal (§ prd:9, prd:46)
`scos-map-query` é "nome de trabalho" mas usado como normativo.
Fix: Fixar o nome antes das stories.

**[Adversarial]** — L2. Jornadas cobrem 3 dos 7 subcomandos (§ UJ-1..3)
FRs sem jornada são candidatos a corte (ver H1).
Fix: Opcional.

**[Adversarial]** — L3. Dados do addendum sem proveniência (§ add:9-11)
Tamanhos de 2026-09-14 sem comando reproduzível.
Fix: Incluir `du`/`wc -c` e tokens estimados para baseline recomputável de SM-1.

## O que está bom
Preservar: diagnóstico específico (JSON minificado em linha única, `Read` sem truncamento); Non-Goals bem delimitados; separação entre orquestração (subagent) e contrato do CLI; SM-C1 e FR-5 reconhecem o risco certo (economizar tokens perdendo o sinal de frescor); subcomando por fato espelhando a tabela de roteamento; log best-effort que nunca bloqueia a consulta.

## Mechanical notes
- Roundtrip das assumptions fecha (FR-6 e FR-8 no índice e vice-versa); IDs FR-1..FR-8, UJ-1..3, SM-1, SM-2, SM-C1 contíguos, sem referência quebrada.
- `.memlog.md` defasado: registra 7 FRs e 2 open questions; a PRD tem 8 FRs e 3 OQs.
- Drift de glossário: `heuristica` (§1, FR-5) vs. `heuristico` (FR-5 consequência, SM-C1); "frescor de workspace" (UJ-2) vs. "Frescor de SNAPSHOT local" (FR-4); "reactor" vs. "fronteiras entre módulos"; "envelope de confiança" usado mas ausente do Glossário.
- "Working title — confirmar" ainda aberto no corpo; `status: draft` é coerente.
- Contagem: o resumo do revisor de rubrica falou em 22 achados (11 médios, 7 baixos), mas `review-rubric.md` lista 18 (4 altos, 10 médios, 4 baixos). O relatório usa os 18 do arquivo.

## Reviewer files
- `review-rubric.md`
- `review-adversarial-general.md`
