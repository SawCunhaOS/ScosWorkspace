# Revisão adversarial — PRD "Scripts de Consulta Rápida para scos-map"

Escopo: `prd.md`, `addendum.md`, `.memlog.md`. Referências `prd:N` são linhas do `prd.md`; `add:N` são linhas do `addendum.md`.

## Veredito

**Não pronto para `bmad-build`.** O problema (JSON minificado caro em tokens) é real e bem evidenciado. A solução, porém, foi inflada além da dor declarada. A métrica principal é fraca e inmensurável como escrita. O mecanismo de subagent e o FR-8 têm falhas arquiteturais não percebidas. Vários FRs ("recorte textual", "desatualizado", "toda linha") não têm critério de aceite objetivo.

Contagem: 3 críticos, 6 altos, 6 médios, 3 baixos.

---

## CRITICAL

### C1. SM-1 não é testável nem ambicioso: baseline inexistente, meta "paridade", proxy errada
- Citação (prd:177): "Meta: paridade ou menos que o `grep` equivalente".
- A Vision (prd:17, 21) vende "voltar a ser mais barato que grep". A meta aceita **empate**, e empate já é um fracasso para quem adotou o scos-map pela economia.
- Não há definição de "grep equivalente". Um `grep` no código-fonte devolve uma resposta diferente da de um fato do scos-map (dependências resolvidas, heurística de entry point). A comparação é entre respostas não equivalentes. Quem escolhe o grep "equivalente" decide o resultado.
- O log (FR-8) só mede o custo do lado `scos-map-query`. O lado `grep` não é medido por nada, então SM-1 não pode ser computado a partir do log como o PRD afirma ("medido a partir do log de custo").
- A unidade é "Tokens/tamanho de saída" (bytes). Bytes não são tokens, e o próprio PRD diz que tokens reais só chegam depois (prd:144, 169). Na v1, SM-1 só tem a proxy.
- A premissa "hoje é mais caro que grep" nunca foi medida. O addendum (add:9-12) mede **tamanho de arquivo**, não tokens da pergunta via grep. O diagnóstico é plausível, mas não está demonstrado.
- **Correção:**
  1. Fixar um benchmark fechado: N perguntas canônicas (as 3 UJs + 5 a 7 da tabela de roteamento) com a resposta esperada.
  2. Medir uma vez, offline, três custos: `Read` do fato (baseline atual), `grep` equivalente e CLI.
  3. Meta numérica, por exemplo "CLI ≤ 10% do `Read` e ≤ grep em ≥ 80% das perguntas". Exigir que a resposta do CLI seja correta (igual à do fato).
  4. Isso dispensa o log como fonte de SM-1.

### C2. FR-8: o enriquecimento com "tokens reais via subagent" é arquiteturalmente impossível como descrito
- Citação (prd:144): "quando chamado através do subagent, o registro é enriquecido com o uso real de tokens". Addendum (add:48): "só capturar e persistir o que a orquestração já expõe".
- Quem grava o log é o script Python, rodando dentro do Bash do subagent. O script **não tem acesso** ao bloco de uso (tokens/tool-uses/duração). Esse bloco só existe na notificação de conclusão entregue ao agente **orquestrador**, depois que o subagent termina. Para persisti-lo, o orquestrador (o LLM principal) teria de executar uma escrita extra a cada chamada. Isso custa tokens, vai contra o objetivo e não é um "campo adicional" no CLI.
- O PRD classifica isso como `[ASSUMPTION]` de sequenciamento (prd:144, 194), quando a suposição real é "a camada de orquestração é capturável por script". Essa suposição não é verificada.
- Além disso, o tamanho de saída do CLI é uma proxy ruim do custo real via subagent. O custo real inclui prompt do subagent, system prompt, raciocínio e resumo.
- **Correção:** retirar a promessa de tokens reais do FR-8 e do addendum, ou transformá-la em spike com critério de saída ("existe API/hook que entregue isso a um script? sim/não"). Fixar FR-8 como "log de bytes/linhas por chamada" e nada mais.

### C3. FR-4 viola o princípio "só lê fatos" e não tem definição de "desatualizado"
- Citação (prd:95): "se um `-SNAPSHOT` resolvido do `~/.m2` local ... está desatualizado em relação ao estado atual do repositório de origem".
- O Glossário (prd:45) diz que o CLI "não gera fatos novos". FR-1 diz que ele nunca compila. FR-4 exige inspecionar `~/.m2` e o git/estado do repo de origem. Isso é computação nova em tempo de consulta. Pode ser um fato já existente em `workspace.json`, mas o PRD não diz isso.
- Não define "desatualizado". Candidatos: mtime do jar contra o último commit, hash, ou timestamp de `install` contra HEAD. Cada um dá um resultado diferente, e o critério é a feature inteira.
- "workspace.json ... não regenerado recentemente" (prd:99): "recentemente" não é critério. O `obsoleto` do scos-map é definido por mudança de fonte, não por tempo.
- A UJ-2 usa isso para decidir rodar `mvn clean install`. Um falso "não desatualizado" gera build com SNAPSHOT velho, um erro silencioso de alto custo.
- **Correção:** (a) verificar em `workspace.json` quais campos de SNAPSHOT já existem; (b) se não existirem, tirar FR-4 da v1 ou escrever uma regra determinística de frescor com casos de teste (jar mais antigo que o último commit tocando o módulo = desatualizado; sem `~/.m2` = "desconhecido", nunca "não").

---

## HIGH

### H1. Escopo vs. dor: unificar TSV e cobrir "todo awk" não serve à dor declarada
- A dor (memlog; add:13) é "especificamente dos fatos em JSON"; "os TSVs já têm um caminho barato hoje". O usuário, contra a recomendação de escopo mínimo (add:33), pediu cobrir TSV também.
- FR-2 (prd:78) cria um requisito ilimitado: "Todo filtro hoje expressável em uma linha de `awk` ... continua expressável". Isso não é testável. Exige reimplementar `awk` sobre três TSVs. Na prática vira um mini-DSL, e é exatamente a "opção genérica" que o addendum descartou (add:27).
- **Alternativa não avaliada e muito mais barata:** o addendum só avaliou `jq` como interface. Nunca considerou mudar o gerador para emitir os fatos de forma consultável, com um campo por linha (NDJSON ou `chave<TAB>valor`). Assim o `grep`/`awk` já recomendado funciona. O PRD declara em Non-Goals que não "adiciona novos tipos de fato", mas isso é mudança de formato, não de tipo. Ou uma receita de uma linha por fato no `SKILL.md` (`python3 -c`/`jq`). Documentar por que foi descartada.
- **Correção:** registrar essa alternativa na tabela do addendum. Limitar FR-2 a um conjunto fechado e enumerado de filtros: as linhas `awk` literalmente presentes no `SKILL.md` e `AGENTS.md`, cada uma com um teste.

### H2. Sem limite de saída: nada garante que a "saída compacta" seja compacta
- Citação (add:43): "FR-5/FR-6 já garantem que a saída bruta do CLI é pequena". **Não garantem.** Nenhum FR impõe teto de linhas/bytes, paginação, `--limit` ou marcador de truncamento.
- O próprio addendum cita `files` sem filtro (222KB/952 linhas), `bytecode_edges.tsv` de 958KB e `config.json` de 142KB.
- FR-1 (prd:68) diz que a saída "nunca é o JSON/TSV bruto do fato inteiro". Mas um `arquivos` sem filtro **é** o fato inteiro, linha a linha.
- Sem teto, a premissa de SM-1 e a justificativa do subagent ("para consultas que ainda assim produzem saída grande") ficam órfãs.
- **Correção:** novo FR: teto padrão (ex.: 50 linhas), `--limit`/`--all` explícito e linha final "N linhas omitidas, refine com X". Teste: nenhuma invocação sem `--all` excede o teto.

### H3. O mecanismo de subagent provavelmente aumenta tokens e reintroduz alucinação, e o PRD o promove sem evidência
- Citações: add:39-40 ("menos chance de misturar esse fato com suposições"); prd:52.
- **Custo:** cada delegação paga prompt de tarefa, resposta, e o system prompt/ferramentas do subagent. Se a resposta bruta do CLI já for de 1 a 5 linhas, o subagent custa mais tokens totais e mais latência. O addendum menciona o "overhead" (add:43) e não fecha a conta.
- **Fidelidade:** um resumo por modelo barato é **lossy** sobre um dado estruturado que já é exato. Ele pode dropar o envelope de confiança (FR-5), a coisa que o SM-C1 protege. A alegação "reduz alucinação" é inversa: adiciona um passo gerativo entre o fato e o agente.
- **Contradição interna:** a Vision de "texto determinístico e curto" torna o subagent desnecessário. Se a saída é pequena, não precisa; se é grande, o problema é H2.
- O PRD ainda mistura isso ao contrato de saída (FR-6 carrega a `[ASSUMPTION]` do subagent). O requisito de estabilidade ficou contaminado por uma suposição de orquestração.
- **Correção:** tirar a assumption do FR-6 (contrato estável vale por si). Registrar no addendum a hipótese como hipótese, com experimento: mesmas N perguntas, CLI direto vs. via subagent, comparando tokens totais e fidelidade (o resumo preserva a flag `obsoleto`?). Só então decidir.

### H4. FR-5 "toda linha" carrega o envelope: custo de tokens por linha e semântica indefinida
- Citação (prd:108): "Toda linha de saída ... carrega ... o estado de confiança".
- Repetir um marcador em cada linha multiplica tokens. É o oposto do SM-1. Um cabeçalho único (`# confianca=atual gerado=...`) mais exceções por linha seria mais barato e igualmente seguro.
- Não está claro onde vivem `confianca`/`estado`/`obsoleto`/`heuristica`: por fato, por entrada ou por campo? Quando a granularidade é por entrada (heurística por convenção de nome), funciona por linha. Quando é por fato, é redundância pura.
- `obsoleto` (AGENTS.md: "o fonte mudou depois do fato ser gerado") é **computado** (comparação de mtimes, como faz o `status`), não um campo persistido no fato. Se for assim, todo subcomando precisa recalcular frescor, o que é escopo escondido e custo de I/O. O PRD o trata como dado já disponível ("já mantém").
- Grafia inconsistente: `heuristica` (prd:19), `heuristico` (prd:112, 183). Define-se um enum de valores.
- **Correção:** definir o enum, a granularidade e a fonte de `obsoleto` (persistido vs. recomputado). Critério: o envelope aparece uma vez no cabeçalho, mais marca por linha só quando a linha difere do cabeçalho.

### H5. SM-2 e SM-C1 não são mensuráveis como escritos
- SM-2 (prd:180): "Proporção de perguntas de navegação ... respondidas via `scos-map-query` sem precisar abrir ... via `Read`. Meta ≥ 90%". Não há denominador (que conjunto de perguntas?) nem instrumentação. O log (FR-8) registra só chamadas ao CLI, não os `Read` que ocorreram. Não existe fonte de dados para a razão.
- SM-C1 (prd:183): "Ocorrência de resposta tratada como atual quando o fato estava obsoleto sem sinalização. Meta: zero". "Tratada como atual" é uma decisão do agente, não observável. O que dá para testar é "o CLI emitiu o envelope em 100% das saídas de fatos obsoletos". Isso é teste automatizado de FR-5, não métrica de produto.
- **Correção:** SM-2 vira checagem estática: toda linha da tabela de roteamento tem subcomando (já é a Consequence de FR-7), mais amostragem manual de transcrições. SM-C1 vira teste de contrato (fixture com fato `obsoleto`, afirmar que o marcador está na saída).

### H6. Contradições de escopo entre PRD, memlog e open questions
- Memlog: "Escopo: Tier 1 a 3 completo". O PRD (prd:172) exclui "Suporte a Tier 3 ... além do que já existe". A lista de subcomandos (prd:59, 159) não inclui `bytecode_edges` (o maior arquivo, 958KB). A promessa "Tier 1 a 3" some sem registro de decisão.
- Open Question 1 (prd:187) pergunta se o subagent entra nesta iniciativa. A seção 6.2 (prd:169) já decide que não. A questão está resolvida e continua listada como aberta. Isso bloqueia leitores.
- Memlog diz "7 FRs ... 2 open questions". O PRD tem 8 FRs e 3 questões. O artefato de contexto está desatualizado.
- FR-1 diz "o CLI nunca ... escreve em `.scos-map/`" (prd:72). OQ3 (prd:189) cogita gravar o log **dentro de** `.scos-map/`. A pergunta é de gravidade média por si só, mas a OQ3 bloqueia FR-8 e fere FR-1. Além disso, o `status`/`obsoleto` do scos-map pode tratar o log como arquivo novo e acusar sujeira.
- **Correção:** decidir e remover OQ1 e OQ3 (sugestão: log no workspace, fora de `.scos-map/` e fora do git, ex.: `.scos-map-query.log` no `.gitignore`); declarar o destino de Tier 2/3 e `bytecode_edges` explicitamente.

---

## MEDIUM

### M1. "Recorte textual", "unidade de informação por linha": FR-1 não define o que cada subcomando devolve
- Citação (prd:68): "é um recorte textual, uma unidade de informação por linha". Não existe nenhum esquema de saída para `layout`, `config`, `deps`, `docs` ou `reactor`. A PRD delega isso a FR-6 ("documenta um formato"), mas isso transfere para o implementador a decisão central do produto. Os JSONs são hierárquicos; achatar `config.json` (142KB) em linhas exige regras (caminho com ponto? chave=valor?).
- **Correção:** um exemplo de saída por subcomando (entrada e saída reais de 3 a 5 linhas) no addendum, que serviria também de teste de aceitação.

### M2. FR-6 "contrato estável" é circular e não verificável
- "Mudança ... exige atualizar `SKILL.md`/documentação no mesmo commit" é processo, não requisito testável. Sem teste golden/snapshot de formato, "estável" é só intenção.
- **Correção:** exigir testes golden por subcomando em `ferramentas/scos-map/tests/` (a pasta já existe), que quebram em qualquer mudança de formato.

### M3. Erros: semântica vazia vs. erro ambígua entre FRs
- FR-3 (prd:92): "saída vazia = sem conflitos, não erro". Mas saída vazia também ocorre se `workspace.json` não existe ou está obsoleto. A regra de erro de FR-1 (prd:69) cobre "fato não gerado", mas FR-3/4 não a referenciam. Um agente lendo vazio conclui "sem conflitos" quando o mapa pode estar velho (a classe de erro que SM-C1 diz proibir).
- **Correção:** sempre emitir ao menos o cabeçalho de confiança, mesmo com zero linhas de dados ("0 conflitos | confianca=atual"). Vazio absoluto nunca significa sucesso.

### M4. Ausência total de requisitos não-funcionais
- Sem: versão do Python e dependências (o gerador é stdlib?), limite de latência na invocação, localização/nome do arquivo (`ferramentas/scos-map/scos-map-query.py`? subcomando de `scos-map.py`?), como o agente o invoca de forma estável (as consultas pedem permissão de Bash a cada chamada diferente? a allowlist de `.claude/settings` foi pensada?), nem compatibilidade com a pasta de testes existente. O título diz "Scripts" (plural), a Vision diz "CLI único".
- **Correção:** seção curta de NFR e de integração: stdlib apenas, caminho único, regra de allowlist, cobertura de testes por subcomando.

### M5. Alternativa de round-trips e custo de descoberta ignorados
- Um CLI com 7+ subcomandos e flags exige que o agente carregue a documentação (SKILL.md, `--help`) e talvez faça várias chamadas onde um `Read` bastava. Nenhuma métrica cobre isso: custo da documentação do CLI no contexto, nem número de chamadas por pergunta. Pode anular o ganho.
- **Correção:** contra-métrica "tokens totais por pergunta canônica, incluindo o texto do SKILL.md carregado e todas as chamadas".

### M6. FR-7 mexe na skill como se fosse trivial, sem critério de adesão
- "Read do fato bruto vira fallback explícito" não impede o agente de usar `Read`. Sem hook ou regra, a taxa de adesão depende do prompt. O Consequence testa apenas a existência de linhas na tabela. Não há como saber que o agente de fato roteia para o CLI.
- **Correção:** aceitar que adesão só é verificável por amostragem de transcrição, e dizer isso. Considerar um aviso no SKILL.md com o tamanho dos fatos grandes ("não use Read em `config.json` > 20KB").

---

## LOW

### L1. Título provisório e status
- "*Working title — confirmar.*" (prd:9), `status: draft`. O nome `scos-map-query` é chamado de "nome de trabalho" no Glossário (prd:46), mas é usado como nome normativo em todos os FRs. Fixar o nome antes das stories.

### L2. Jornadas cobrem só 3 dos 7 subcomandos
- UJ-1 a UJ-3 cobrem layout, frescor e conflitos. `config`, `deps`, `gerenciadas`, `docs` e `arquivos` não têm jornada, e FR-2 (filtros) realiza só UJ-1 por implicação. FRs sem jornada são candidatos a corte (ver H1).

### L3. Dados do addendum datados e sem proveniência
- Os números de tamanho (add:9-11) vêm de uma leitura de 2026-09-14 sem comando reproduzível. Incluir o comando (`du`, `wc -c`) e, de preferência, tokens estimados (bytes/3.5), para que SM-1 tenha baseline recomputável.

---

## O que está bom (preservar)
- Diagnóstico claro e específico (JSON minificado em linha única, `Read` sem truncamento) e Non-Goals bem delimitados (não gera fatos, não substitui grep, não toca tier).
- Decisão de separar orquestração (subagent) do contrato do CLI. Falta apenas limpar a assumption de FR-6.
- Contra-métrica SM-C1 e FR-5 reconhecem o risco certo: economizar tokens perdendo o sinal de frescor.
- Subcomando por fato espelhando a tabela de roteamento existente e FR-7 com critério verificável de cobertura 1:1.
- Logging best-effort que nunca bloqueia a consulta (prd:145).

## Prioridade sugerida antes de implementar
1. Reescrever SM-1 com benchmark fechado e meta real (C1) e remover a promessa de tokens reais do FR-8 (C2).
2. Verificar se FR-4 já tem fonte em `workspace.json`; senão, cortar ou especificar (C3).
3. Adicionar teto de saída (H2) e definir o envelope de confiança (H4).
4. Avaliar a alternativa barata de formato de fato (H1) antes de aceitar o escopo de TSV.
5. Fechar OQ1 e OQ3, reconciliar Tier 1-3 (H6).
