---
title: "Review Adversarial — PRD Melhorias e Adequação SawCunhaOS-Foundation"
status: draft
created: 2026-08-18
reviewer: revisor adversarial (automatizado)
target: prd.md (mesma pasta)
---

# Review Adversarial do PRD

Metodologia: cada seção do PRD foi lida buscando ativamente por afirmações não verificáveis, contradições entre seções, mecanismos de verificação ausentes e decisões justificadas apenas por rótulo (D1/D2/D3) sem registro de alternativas consideradas. Escopo combinado a pedido: não questionar a ausência de jornada de usuário final (deliberado, produto é lib técnica).

---

## CRÍTICO

### C1 — "Todas as fases" contradiz a própria justificativa de dependência de F1

**Severidade**: critical
**Localização**: `## Sequenciamento e Fases`, linha da tabela #7 (F1, coluna "Fase(s)" = "Todas as fases"; coluna "Por quê" = "Trabalha sobre a estrutura final dos módulos `-api`/`core`, evitando mover as anotações duas vezes")

A própria linha da tabela se contradiz. Se o motivo declarado para a ordem de F1 é que ele "trabalha sobre a estrutura final dos módulos `-api`/`core`" — estrutura essa que só fica pronta na Fase 4/5 (linha #6) — então F1 não pode, ao mesmo tempo, rodar em "todas as fases" (o que inclui a Fase 0, antes de qualquer coisa existir). NFR-1 exige que "nenhuma fase pode ser adiantada em relação à sua dependência ali listada", mas essa linha não declara qual é a dependência real de F1 dentro da própria tabela — ela aponta a razão (esperar a estrutura final) e depois ignora essa razão ao dizer "todas as fases".

**Pergunta que expõe o problema**: Se FR-1 a FR-8 dependem da estrutura final de `-api`/`core` (linha 6), como FR-1 a FR-8 podem começar a ser implementados em "todas as fases", incluindo antes da linha 6 ser concluída, sem violar NFR-1?

---

### C2 — FR-4 (fail-open) garante exatamente a duplicidade que a Métrica de Sucesso promete zerar

**Severidade**: critical
**Localização**: FR-4 ("Garantir fail-open quando o Redis está indisponível... nunca `FAIL_CLOSED`") vs. `## Métricas de Sucesso`, item 2 ("Zero colisão ou duplicidade de processamento de idempotência em produção")

Fail-open, por definição, significa que quando o Redis (armazenamento de estado de idempotência) está fora do ar, requisições concorrentes passam sem proteção de lock — ou seja, duplicidade de processamento é o comportamento *esperado e desejado* pelo próprio FR-4 durante uma indisponibilidade. A métrica de sucesso, porém, promete "zero" duplicidade sem nenhuma ressalva, exceção ou janela de tolerância declarada para o cenário de indisponibilidade do Redis que o próprio FR-4 antecipa e escolhe permitir.

**Pergunta que expõe o problema**: Durante uma indisponibilidade do Redis (cenário que FR-4 trata como esperado e não excepcional), o processamento duplicado que ocorre é contado contra a métrica "zero duplicidade" ou não? Se não é contado, onde está escrita essa exceção? Se é contado, a métrica é estruturalmente impossível de atingir enquanto FR-4 existir como especificado.

---

### C3 — Guarda-rail arquitetural (FR-19/FR-20) chega depois do maior risco que ele deveria prevenir

**Severidade**: critical
**Localização**: `## Sequenciamento e Fases`, linhas #3, #4 (Fase 2 e 3 — criação de `*-api` e extração de `core`, sem menção a FR-19/20) vs. linha #6 (Fase 4-5 — "resto de FR-18 a FR-20")

A Visão do PRD identifica a causa raiz dos bugs como "acoplamento invertido entre `utils`/`exception`" e propõe FR-19/FR-20 (regras ArchUnit) como o mecanismo que impede a repetição desse erro de design. Mas, pela tabela, as regras ArchUnit só são implementadas/promovidas a `pluginManagement` na Fase 4-5 (linha 6) — depois que `core` já foi extraído (Fase 3, linha 4) e os módulos `*-api` já foram criados (Fase 2, linha 3). Ou seja: exatamente os módulos mais sensíveis ao acoplamento invertido (`core`, `*-api`) são criados sem o guarda-rail automatizado que deveria impedir a regressão, e só recebem a rede de segurança depois de já existirem.

**Pergunta que expõe o problema**: Se `core` for extraído na Fase 3 e alguém (acidentalmente) fizer `core` importar `org.springframework` nesse momento, o que detecta isso antes da Fase 4-5, quando FR-19/20 finalmente existem? Por que o guarda-rail não é a primeira coisa criada, e não a última?

---

## ALTO

### H1 — Única superfície de comunicação (CHANGELOG) chega depois das mudanças que quebram consumidores

**Severidade**: high
**Localização**: `## Comunicação e Migração` ("O CHANGELOG... previsto na Fase 5 do F3, é a única superfície de comunicação") vs. `## Sequenciamento e Fases`, linha #2 (F2 — correções de status HTTP em Fase 0-2) e OQ-1

As correções de status HTTP que o próprio OQ-1 assume como risco de quebra para consumidores (500→403/400/501) são entregues na Fase 0-2 (linha 2). O único artefato de comunicação previsto — o CHANGELOG — só é escrito na Fase 5, a última fase de todo o roadmap. Ou seja, mesmo a comunicação mínima e informal que o PRD escolheu manter chega depois que as mudanças que ela deveria anunciar já estão em produção.

**Pergunta que expõe o problema**: Um consumidor piloto que atualiza a dependência logo após a Fase 0-2 e começa a receber `403`/`400` onde antes recebia `500` vai encontrar o quê no CHANGELOG nesse momento? Se a resposta é "nada, porque o CHANGELOG só existe na Fase 5", em que sentido essa é "a" superfície de comunicação para essas mudanças específicas?

---

### H2 — Contra-métrica de rollback depende de um canal de feedback que a seção de Comunicação declara não existir

**Severidade**: high
**Localização**: `### Contra-métricas` ("Nº de consumidores piloto com build quebrado ou pedido de rollback...") vs. `## Comunicação e Migração` ("Sem processo formal de guia de migração ou aviso direto aos consumidores")

Contar "pedidos de rollback" pressupõe que existe um canal pelo qual consumidores piloto reportam problemas de volta à equipe da lib. A seção de Comunicação e Migração explicitamente decide não estabelecer aviso direto nem guia formal. Sem canal de entrada estabelecido, "zero pedidos de rollback" é indistinguível de "ninguém foi avisado o suficiente para perceber o problema e reclamar".

**Pergunta que expõe o problema**: Que canal concreto (issue tracker, canal de chat, e-mail) um consumidor piloto usa para "pedir rollback", e quem está monitorando esse canal? Se a resposta não existe, como essa contra-métrica é medida — por inferência de silêncio?

---

### H3 — OQ-2 referencia um "teto estimado combinado" que não existe em nenhuma outra parte do PRD

**Severidade**: high
**Localização**: OQ-2 ("revisitar se o esforço ultrapassar ~14 dias úteis (metade do teto estimado combinado)")

Não há, em nenhuma seção anterior do documento, uma estimativa de esforço total, prazo combinado, ou "teto" para os três planos. O número 14 dias (e a alegação de que é "metade" de outro número — 28 dias — que também não aparece em lugar nenhum) surge sem lastro dentro do próprio artefato.

**Pergunta que expõe o problema**: Onde está registrado o "teto estimado combinado" do qual 14 dias é metade? Se ele vive só em um dos três planos de origem (não citado aqui) e não neste PRD, como um revisor deste documento verifica ou contesta esse número?

---

### H4 — OQ-3 delega dimensionamento a um consumidor que, pela própria seção de Comunicação, não será avisado

**Severidade**: high
**Localização**: OQ-3 ("*Dono*: time consumidor em cada ambiente") vs. `## Comunicação e Migração`

OQ-3 atribui a responsabilidade de dimensionar `timeout`/`slow-call-duration-threshold` ao "time consumidor em cada ambiente" — mas a seção de Comunicação e Migração decide não notificar consumidores nem produzir guia formal. Um time consumidor não pode dimensionar um parâmetro de uma mudança de comportamento (fail-open com circuit breaker) que ele não sabe que existe.

**Pergunta que expõe o problema**: Como o "time consumidor em cada ambiente" vai saber que precisa dimensionar `slow-call-duration-threshold` se nenhuma comunicação formal ou informal está prevista para avisá-lo dessa nova responsabilidade? Esse dono foi de fato consultado/informado, ou é uma atribuição no papel sem via de chegada?

---

### H5 — Métrica de "cobertura ArchUnit" mede a existência de regras, não a suficiência delas (caso `web`/D1 não é coberto)

**Severidade**: high
**Localização**: `## Métricas de Sucesso`, item 4 vs. FR-19 (lista regras para `core`, `spring`, `*-api`, "nenhum módulo depende de `web` exceto aplicações", "sem ciclos") vs. FR-18/D1 ("`web`... aceita a dependência formal de `cache`")

FR-19 não define nenhuma regra restringindo as dependências que o próprio módulo `web` pode ter (só regras sobre quem pode depender de `web`, sobre `core`, `spring` e `*-api`). A decisão D1 (registrada dentro de FR-18) formaliza que `web` passa a depender de `cache` — presumivelmente trazendo Redis para qualquer consumidor de utilitários web, mesmo os que não usam cache. Como não há regra ArchUnit cobrindo as dependências do próprio `web`, a "cobertura de 100% dos módulos" prometida na métrica pode ser tecnicamente verdadeira (as regras que existem cobrem 100% dos módulos aos quais se aplicam) enquanto o vazamento de dependência transitiva que a Visão do documento (e o exemplo do `DateUtils`) tenta evitar continua ocorrendo sem detecção, exatamente no módulo onde D1 o introduziu deliberadamente.

**Pergunta que expõe o problema**: Que regra ArchUnit detectaria se `web` (ou qualquer módulo além dos citados em FR-19) acumulasse dependências desnecessárias no futuro? Se a resposta é "nenhuma", a métrica "cobertura de regras ArchUnit... cada módulo novo só importa o que seu papel permite" é verdadeira apenas para o subconjunto de módulos que FR-19 escolheu regrar — não para todos os módulos, como o texto da métrica afirma.

---

## MÉDIO

### M1 — OQ-4 é chamado de "dependência externa... não controlada aqui" mas recebe Dono e Condição de revisão como se fosse controlada aqui

**Severidade**: medium
**Localização**: `## Sequenciamento e Fases`, último parágrafo ("Dependência externa a este PRD... não controlada aqui") vs. OQ-4 ("*Dono*: responsável pelo módulo `audit`. *Condição de revisão*: confirmar se existe...")

O parágrafo final da seção de Sequenciamento classifica a questão do hash-chain do `audit` como algo "fora dos 3 planos, não controlada aqui" — mas OQ-4 atribui a essa mesma questão um dono e uma condição de revisão explícita dentro deste PRD, como se fosse, de fato, controlada aqui. As duas afirmações não podem ser simultaneamente verdadeiras sem qualificação adicional.

**Pergunta que expõe o problema**: Este PRD controla ou não controla a resolução do hash-chain do `audit`? Se não controla, por que atribui dono e condição de revisão (mecanismos de governança) a ela? Se controla ao ponto de ter dono e critério, por que é descrita como "não controlada aqui"?

---

### M2 — OQ-1: condição de revisão pressupõe observabilidade sobre produção de terceiros que o PRD não estabelece em nenhum lugar

**Severidade**: medium
**Localização**: OQ-1 ("*Condição de revisão*: monitorar taxa de erro por status código nos primeiros dias após o deploy da 1.2.0")

"Monitorar taxa de erro por status código" é uma prática normal para um time que opera seu próprio serviço, mas aqui o produto é uma biblioteca consumida por times externos — a produção onde os códigos de status realmente aparecem é a dos consumidores, não da equipe responsável pelo F2. Não há, em nenhuma parte do documento, uma fonte de dados, dashboard compartilhado, ou acordo de observabilidade cross-team que permita ao "responsável pelo F2" efetivamente monitorar isso.

**Pergunta que expõe o problema**: Que sistema o "responsável pelo F2" abre para "monitorar taxa de erro por status código" de aplicações que rodam em ambientes de outros times? Se essa telemetria não é compartilhada hoje, essa condição de revisão é executável ou é uma aspiração que soa bem no papel?

---

### M3 — OQ-5 quebra o próprio padrão de formato das outras Open Questions e é a de menor rigor apesar de proteger a premissa central do PRD

**Severidade**: medium
**Localização**: OQ-5 (sem linha "*Dono*:", diferente de OQ-1 a OQ-4)

OQ-1 a OQ-4 seguem consistentemente o formato "*Dono*: ... *Condição de revisão*: ...". OQ-5 — que trata exatamente do risco que a Visão do PRD usa para justificar todo o projeto ("renomeação mascarando mudança de comportamento") — não tem dono nomeado, apenas "mantido como item de atenção na revisão de código", sem especificar quem revisa, com que checklist, ou sob qual critério de aprovação/reprovação.

**Pergunta que expõe o problema**: Quem é o dono de OQ-5? Se a resposta é "quem fizer a revisão de código", isso não é um dono — é a ausência de um, e é inconsistente com o rigor aplicado a OQ-1 a OQ-4 para um risco que o próprio documento trata como central ao motivo de existir do projeto.

---

### M4 — Decisões D1/D2/D3 são rotuladas mas não justificadas com alternativas registradas

**Severidade**: medium
**Localização**: FR-18 (parênteses "decisão D1", "decisão D2", "decisão D3")

As três decisões de arquitetura mais relevantes da decomposição modular (F3) aparecem como anotações de uma frase dentro de FR-18, sem uma seção de decisão que registre: o que foi considerado, por que a alternativa vencedora foi escolhida, e qual o custo aceito. D3 é o caso mais evidente: o texto admite que "diverge da inclinação original do plano" mas justifica com uma única frase ("por isolamento total de dependência"), sem quantificar o ganho nem discutir o custo de manter um 10º submódulo para o que provavelmente são duas classes (`JacksonEncoderCustom`/`JacksonDecoderCustom`).

**Pergunta que expõe o problema**: Se alguém discordar de D1, D2 ou D3 daqui a 3 meses, onde estão registradas as alternativas descartadas e o motivo pelo qual essa decisão pesou mais do que elas? Uma decisão citada por rótulo sem ficha de decisão é revisável ou é definitiva por fiat?

---

### M5 — Provenance da tabela de sequenciamento combinado é atribuída inteiramente a um único plano de origem que trata de outro assunto

**Severidade**: medium
**Localização**: `## Sequenciamento e Fases` ("Ordem definida na origem (`plano-ajuste-exception.md`, seção 9)")

A tabela intercala fases de F1 (idempotência), F2 (exception) e F3 (utils) — três planos distintos. A atribuição da ordem inteira a uma única seção de um único plano (o de exception) é uma alegação de rastreabilidade forte que merece verificação: é plausível que o plano de correção de exception já definisse, em sua seção 9, a ordem de execução da decomposição do `utils` e da idempotência também?

**Pergunta que expõe o problema**: A seção 9 de `plano-ajuste-exception.md` realmente define a intercalação de F1 e F3, ou essa tabela consolidada foi sintetizada por quem escreveu este PRD e a atribuição de fonte está incompleta/incorreta?

---

### M6 — Métricas "zero ocorrências" (itens 1 e 2) não têm mecanismo de medição, fonte de dado ou janela de tempo definidos

**Severidade**: medium
**Localização**: `## Métricas de Sucesso`, itens 1 e 2

"Zero ocorrências... após o deploy" não diz: medido onde (logs de qual sistema, de quem), por quanto tempo (1 dia? para sempre?), e por quem. Como observado em M2, a "produção" relevante aqui pertence a times consumidores externos, não à equipe que executa este PRD. Uma métrica de sucesso sem fonte de dado declarada não é verificável — é uma aspiração com formato de métrica.

**Pergunta que expõe o problema**: Em que dashboard ou log agregado alguém vai efetivamente contar "0" para essas duas métricas, e até quando essa contagem continua sendo válida como critério de sucesso do release?

---

## BAIXO

### L1 — NFR-3 (cobertura de teste) só cobre a Fase 0 do F1; a correção do bug de segurança (F2) não tem NFR de cobertura equivalente

**Severidade**: low
**Localização**: NFR-3 ("mínimo de 80% nas áreas tocadas pela Fase 0 do F1")

O bug de segurança anunciado na Visão como motivador do release (403 classificado como 500) é corrigido por FR-9/FR-10, que pertencem a F2 — mas nenhuma NFR de cobertura de teste é declarada para F2, apenas para a Fase 0 do F1. Dado que F2 é apresentado como o item de maior severidade (classificação de erro de segurança), a ausência de um piso de cobertura equivalente é uma lacuna de priorização.

**Pergunta que expõe o problema**: Por que a correção do bug de segurança (F2) não tem uma NFR de cobertura mínima declarada, quando a idempotência (F1, Fase 0) tem 80% explícito?

---

### L2 — NFR-4 não tem mecanismo de verificação, ao contrário de FR-19/20

**Severidade**: low
**Localização**: NFR-4 ("nenhuma alteração de comportamento além do declarado durante mover/renomear")

Diferente de FR-19/20, que ganham um mecanismo automatizado de verificação (ArchUnit), NFR-4 é uma regra de "confiança" sem teste, diff de comportamento, ou gate de CI que a valide. É reforçada apenas por convenção de processo (2 commits separados, NFR-2), não por verificação.

**Pergunta que expõe o problema**: Se um commit "mover/renomear" acidentalmente alterar comportamento, o que além da revisão humana detecta isso antes do merge?

---

### L3 — Preservação de característica O(n) no `JsonMasker` (FR-21) não tem teste/benchmark associado

**Severidade**: low
**Localização**: FR-21 ("preservando... a característica O(n) do caminho quente do `JsonMasker`")

Complexidade algorítmica é uma afirmação não funcional que precisa de instrumentação (benchmark, profiling, ou teste de carga com dataset crescente) para ser verificada — não é algo que `jacoco:check` ou teste unitário comum capturam. O FR não menciona nenhum desses mecanismos.

**Pergunta que expõe o problema**: Que teste falha se a migração Gson→Jackson acidentalmente introduzir uma operação O(n²) ou O(n log n) no caminho quente do `JsonMasker`?

---

### L4 — Premissa "base de consumidores é piloto/restrita" (fundamento de toda a decisão de não comunicar) não é sustentada por nenhum dado no documento

**Severidade**: low
**Localização**: `## Visão` e `## Comunicação e Migração`

Toda a decisão de pular guia de migração e aviso direto repousa sobre a alegação de que a base de consumidores é "piloto/restrita" — mas o PRD não diz quantos consumidores existem, quais são, ou como se sabe que nenhum deles trata o SNAPSHOT como estável de fato.

**Pergunta que expõe o problema**: Quantos consumidores usam a lib hoje, e como foi verificado que nenhum deles trata a versão SNAPSHOT como dependência de produção estável, antes de decidir que avisá-los formalmente é dispensável?

---

### L5 — FR-20 registra as regras ArchUnit em um profile Maven opt-in (`analyze`) sem declarar se ele roda por padrão em CI

**Severidade**: low
**Localização**: FR-20 ("Impor as regras do FR-19 via testes ArchUnit no perfil `analyze`... promovido... para `pluginManagement` do POM pai")

Um profile Maven não ativado por padrão só roda quando alguém passa `-Panalyze` explicitamente. O documento não declara se o pipeline de CI ativa esse profile em todo build/PR. Sem essa afirmação, "cobertura em 100% dos módulos" significa apenas que as regras existem no código, não que são de fato aplicadas a cada mudança — o que é justamente o tipo de garantia frágil que a Visão do PRD diz querer evitar.

**Pergunta que expõe o problema**: O profile `analyze` roda automaticamente em todo build de CI, ou precisa ser invocado manualmente? Se for manual, o que impede alguém de mesclar uma violação de arquitetura sem nunca rodar o profile?

---

## Resumo de severidades

| Severidade | Qtd |
|---|---|
| Critical | 3 |
| High | 5 |
| Medium | 6 |
| Low | 5 |

**Veredito**: o PRD tem boa granularidade técnica nos FRs, mas a camada de governança (métricas, decisões, riscos, comunicação) tem furos estruturais: métricas "zero" sem fonte de dado, uma decisão explícita de não comunicar mudanças que o próprio documento classifica como quebradoras, um guarda-rail arquitetural que chega depois do risco que deveria mitigar, e uma linha de sequenciamento que se contradiz dentro da própria tabela.
