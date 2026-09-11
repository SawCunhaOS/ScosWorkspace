# PRD Quality Review — PRD-SawCunhaOS-Foundation-2026-08-18

## Overall verdict

PRD disciplinado e incomum na sua concretude para uma consolidação de 3 planos técnicos: trade-offs são nomeados com o que se perde (OQ-1, OQ-2), o sequenciamento tem justificativa explícita por linha ("Por quê"), e quase todo FR carrega uma consequência testável (código de status, classe, config). É corretamente sub-formalizado para uma lib interna — sem personas nem UJs, e isso é acerto de shape, não lacuna. Os riscos reais estão a jusante: a conclusão do FR-18 está fragmentada em 3 fases não contíguas sem sub-identificadores, e as decisões D1–D3 tomadas durante a consolidação (não extraídas literalmente dos planos de origem) não são marcadas como tal, dificultando saber o que veio do plano original vs. o que foi julgamento do PM nesta calibração.

## Decision-readiness — strong

Trade-offs são nomeados com o que se perde, não só o que se ganha: OQ-1 admite que rotas hoje incorretas (500) vão virar 403/400/501 e que "consumidores que dependiam do comportamento antigo (mesmo incorreto) podem quebrar" (linha 88) — sem suavizar. OQ-2 declara a regra de corte sob pressão de prazo em termos operacionais ("cortar volume de trabalho... nunca quebrar contrato", linha 89) em vez de deixar isso implícito. A seção `## Comunicação e Migração` (linha 84) é uma decisão-como-decisão: assume explicitamente que não haverá guia de migração, com dupla justificativa auditável, não uma "consideração".

As 5 Open Questions (linhas 88–92) são genuinamente abertas — cada uma tem *Dono* e *Condição de revisão* concretos, funcionando como `[NOTE FOR PM]` em tensões reais (OQ-5 é literalmente "risco de a renomeação mascarar mudança de comportamento", não um checkpoint seguro).

### Findings
- **medium** Decisões D1/D2 sem trade-off explícito (§ FR-18, linha 51) — D3 tem justificativa própria ("diverge da inclinação original do plano por isolamento total de dependência"), mas D1 ("web... aceita a dependência formal de cache") e D2 ("validation... passa a ter jakarta.persistence-api como provided") são declaradas como fato consumado, sem dizer qual alternativa foi descartada e por quê. Quem for questionar "por que dependência formal em vez de acoplamento fraco?" não encontra a resposta no PRD. *Fix:* uma frase por decisão nomeando a alternativa rejeitada, no mesmo padrão de D3.

## Substance over theater — strong

Sem seção de personas — correto para este produto (times consumidores de uma lib, não usuários finais), não é lacuna. A Visão (linha 10) é específica ao repositório e ao momento ("enquanto o versionamento ainda é SNAPSHOT e a base de consumidores é piloto/restrita") — não é um parágrafo que serviria para qualquer PRD da categoria. As NFRs citam limiares e mecanismos concretos em vez de adjetivos: NFR-3 especifica "80% nas áreas tocadas pela Fase 0 do F1 (testes de concorrência, colisão de hex, duplo `IdempotentAspect`, indisponibilidade de Redis via Testcontainers)" (linha 79) — não há um único "deve ser escalável/seguro/confiável" solto no documento. Sem findings aqui.

## Strategic coherence — strong

A tese está na Visão: corrigir defeitos reais e aproveitar a janela SNAPSHOT/piloto para sanar a dívida estrutural que os causou, antes da adoção ampla. A tabela `## Sequenciamento e Fases` (linhas 63–72) deriva a ordem da tese, não de facilidade — a coluna "Por quê" argumenta risco e dependência técnica em cada linha (ex.: linha 67, "menor risco, maior ganho isolado"), e o próprio texto justifica a ordem invertida (corrigir com módulo parado antes de mover) para manter o diff separável. Métricas de Sucesso medem exatamente a tese (zero erro de auth mal classificado, zero colisão de idempotência, redução de dependências transitivas, cobertura ArchUnit) — não métricas de atividade. Contra-métricas presentes e ligadas ao risco real da migração (linhas 21–22). Sem findings aqui.

## Done-ness clarity — adequate

A maioria esmagadora dos 24 FRs carrega consequência testável e verificável por código: status HTTP específico (FR-1, FR-2, FR-9, FR-10, FR-15), classe/exceção exata a capturar (FR-9), método a sobrescrever (FR-13), algoritmo exato (FR-5), API específica (FR-2's `tryAcquire(key, payloadHash, ttl) → Lease`). Não há ocorrência de "tratar graciosamente" ou "performance razoável" em nenhum FR — incomum e positivo para este dimensão.

Duas exceções pontuais:

### Findings
- **medium** FR-21 sem critério verificável para preservar complexidade O(n) (§ FR-21, linha 54) — "preservando... a característica O(n) do caminho quente do `JsonMasker`" é uma afirmação técnica real, mas não há benchmark, teste de carga ou limiar definido que a torne falsificável como critério de "pronto". *Fix:* adicionar um teste de regressão de performance (ex.: benchmark JMH com limite de tempo por N elementos) ou nomear explicitamente como aceito sem verificação automatizada.
- **low** FR-4 depende de um valor não fixado nesta versão (§ FR-4, linha 31; cf. OQ-3, linha 90) — "detectando lentidão via `slow-call-duration-threshold`" não tem valor numérico, e a lacuna já está corretamente exposta como OQ-3 em vez de escondida. Não é falha de scope honesty (está declarado), mas o FR sozinho não é "pronto" sem essa decisão. *Fix:* referenciar OQ-3 inline no texto do FR-4 para deixar a dependência explícita no ponto de uso, não só na seção de riscos.

## Scope honesty — adequate

O não-escopo mais importante do documento — ausência de guia de migração — está explícito e justificado (`## Comunicação e Migração`, linha 84), não inferido. As 5 Open Questions cobrem tensões reais com dono e gatilho de revisão. O de-scoping sob pressão de prazo (OQ-2) é proposto abertamente, não silencioso.

### Findings
- **medium** Decisões D1–D3 não marcadas como `[ASSUMPTION]` ou `[NOTE FOR PM]` (§ FR-18, linha 51) — o documento não usa a tag `[ASSUMPTION]` em nenhum lugar, mas D1/D2/D3 são claramente julgamentos feitos durante a consolidação desta PRD (D3 até diz explicitamente "diverge da inclinação original do plano"), não extrações literais dos 3 planos de origem. Sem marcação, um leitor não consegue distinguir "isto veio do plano técnico original" de "isto foi decidido agora, nesta calibração". Isso também deixa sem Índice de Assunções para round-trip. *Fix:* marcar D1–D3 como `[ASSUMPTION]` ou `[DECISÃO DO PM]` com short rationale, indexadas ao final.

## Downstream usability — adequate

IDs de FR (1–24), NFR (1–4) e OQ (1–5) são contíguos, únicos, sem duplicatas. Referências cruzadas na tabela de sequenciamento (ex. "FR-9, FR-10, FR-12 a FR-17" linha 66) resolvem corretamente contra a lista de FRs.

### Findings
- **medium** FR-18 fragmentado em 3 fases não contíguas sem sub-identificador (§ Sequenciamento e Fases, linhas 67, 68, 70) — a tabela referencia "parte de FR-18" (Fase 2, linha 67), "parte de FR-18" de novo (Fase 3, linha 68) e "resto de FR-18 a FR-20, FR-24" (Fase 4/5, linha 70), mas o próprio texto do FR-18 (linha 51) lista todos os módulos-alvo em um único bullet, sem indicar qual pedaço pertence a qual fase. Para quem for quebrar isso em stories, fica sob reconstrução manual qual subconjunto de "criar `core`, `spring`, `web`, `cache`, `jpa`, `validation`, `*-api`, `feign`" corresponde a cada uma das 3 fases. *Fix:* sub-identificar (FR-18a/b/c) ou anexar a cada linha da tabela a lista exata de módulos tocados naquela fase.
- **low** Sem seção de Glossário (documento inteiro) — o jargão do domínio é majoritariamente identificadores de código (nomes de classe, anotação, config), que são inerentemente unívocos, então o impacto é baixo. Ainda assim, conceitos recorrentes entre FRs — "fail-open"/"fail-closed", "lock de idempotência", "colisão de chave" vs. "colisão de hex" (NFR-3, linha 79 — hash collision, conceito distinto de colisão de chave do FR-1) — se beneficiariam de uma definição de uma linha para handoff limpo à arquitetura.

## Shape fit — strong

Ausência total de personas e UJs é o ajuste correto para uma lib interna consumida por times, não por usuários finais — o PRD não finge uma jornada de usuário que não existe. As Métricas de Sucesso são operacionais (taxa de erro por status, cobertura ArchUnit), coerente com "single-operator"/internal-tool. É fortemente brownfield e trata isso bem: referências ao código existente são precisas e verificáveis (`getBeanResults().get(0)` linha 40, `Integer.toHexString` linha 32, "3 adapters de `java.time`" linha 54, "71 classes atuais" linha 56) — não há menção genérica a "o código legado". Sem findings aqui.

## Mechanical notes

- Nenhuma tag `[ASSUMPTION]` no documento — ver finding em Scope honesty. Não há Índice de Assunções para conferir roundtrip porque não há assunções marcadas.
- IDs contíguos e sem gaps: FR-1..24, NFR-1..4, OQ-1..5. Nenhuma referência cruzada quebrada encontrada.
- "Colisão de hex" (NFR-3, linha 79) e "colisão de chave" (FR-1, linha 28) usam a palavra "colisão" para dois conceitos diferentes (colisão de hash criptográfico vs. colisão de chave de negócio com payloads distintos) — não é erro, mas vale desambiguar no glossário sugerido acima.
- Sem seção `UJs` — coerente com Shape fit strong, não é omissão.
- Seções presentes cobrem o que as apostas deste documento exigem: Visão, Métricas de Sucesso (+ contra-métricas), Features/FRs, Sequenciamento, NFRs, Comunicação e Migração, Riscos/OQs. Faltam Glossário e uma seção formal de Non-Goals — ambas de impacto baixo dado o formato deste PRD (ver findings acima).
