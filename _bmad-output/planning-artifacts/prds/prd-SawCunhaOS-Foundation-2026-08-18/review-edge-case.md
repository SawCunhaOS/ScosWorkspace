---
title: "Revisão de Edge Cases — PRD Melhorias e Adequação SawCunhaOS-Foundation"
source-prd: "./prd.md"
created: 2026-08-18
reviewer: "edge-case hunter"
---

# Revisão de Edge Cases

Um item por cenário: descrição, por que o PRD não cobre, severidade.

## 1. Concorrência/timing não cobertos pelos FRs de F1

### 1.1 — Expiração do Lease durante processamento em andamento
**Cenário**: `tryAcquire(key, payloadHash, ttl) → Lease` (FR-2) concede um lease com TTL fixo. Se o processamento do handler demorar mais que o TTL (payload grande, dependência externa lenta), o lease expira no Redis enquanto a operação ainda está em voo. Uma segunda requisição com a mesma chave chega nesse intervalo, encontra a chave livre, adquire um novo lease e reexecuta a mesma operação não-idempotente em paralelo — exatamente o cenário que FR-2 foi criado para impedir.
**Por que o PRD não cobre**: FR-2 descreve apenas a atomicidade da aquisição (`tryAcquire`) e o retorno `409 IN_PROGRESS` para chamada concorrente, mas não define renovação/extensão de TTL, nem o que ocorre quando o TTL é mais curto que o tempo real de processamento. NFR-3 pede teste de "indisponibilidade de Redis" mas não teste de "TTL menor que duração do processamento".
**Severidade**: critical

### 1.2 — Lease não liberado após exceção no handler
**Cenário**: O handler decorado lança exceção depois de `tryAcquire` ter sucesso. Não há FR definindo se o lease é liberado (permitindo retry imediato do cliente) ou se permanece "IN_PROGRESS" até o TTL expirar (fazendo o cliente legítimo receber `409` por até `ttl` segundos após uma falha real do servidor).
**Por que o PRD não cobre**: FR-2 documenta apenas o caminho feliz (lock atômico) e o caminho de colisão concorrente; o caminho de erro dentro do lease não tem requisito equivalente, nem métrica dedicada em FR-7 para "leases abandonados por exceção".
**Severidade**: high

### 1.3 — Split-brain entre aquisição (Redis up) e gravação da resposta (Redis cai no meio)
**Cenário**: `tryAcquire` é bem-sucedido via Redis (circuit breaker fechado). Durante o processamento, o Redis fica lento/indisponível e o circuit breaker abre. Ao tentar persistir a resposta (`setResponse`), o fail-open (FR-4) permite que a requisição retorne sucesso ao cliente sem que a resposta tenha sido de fato cacheada. Um retry subsequente do cliente com a mesma `Idempotency-Key`, já com Redis recuperado, não vai encontrar registro algum e reexecutará a operação inteira (duplicando efeitos colaterais não-idempotentes).
**Por que o PRD não cobre**: FR-4 só menciona fail-open no nível "quando Redis indisponível" como propriedade global, mas não trata a transição de estado do circuit breaker *no meio* de uma única requisição, nem a reconciliação de leases "adquiridos mas nunca persistidos". FR-7 (métricas) não lista essa condição como métrica obrigatória.
**Severidade**: critical

### 1.4 — Janela de half-open do circuit breaker
**Cenário**: Durante o estado `HALF_OPEN` do Resilience4j, apenas chamadas de teste limitadas passam para o Redis real. Se duas requisições concorrentes com a mesma chave chegam nessa janela, uma pode ser a "chamada de teste" (vai ao Redis, obtém lock real) e a outra pode ser rejeitada preventivamente pelo CB e cair no fail-open (bypassa o lock inteiramente) — resultando em processamento duplicado mesmo com Redis parcialmente saudável.
**Por que o PRD não cobre**: FR-4 cita `slow-call-duration-threshold` mas não fala do comportamento de concorrência especificamente durante a transição `OPEN → HALF_OPEN → CLOSED`.
**Severidade**: high

### 1.5 — Três relógios de timeout não reconciliados
**Cenário**: Existem três parâmetros de tempo distintos e independentes: `spring.data.redis.timeout` (FR-4), `slow-call-duration-threshold` do circuit breaker (FR-4) e o `ttl` do lease (FR-2). Nenhuma relação de ordem entre eles é exigida. Se `ttl` < `redis.timeout`, uma chamada lenta ao Redis (ainda dentro do timeout, portanto "válida") pode terminar depois que o lease já é considerado expirado por outro nó, criando ambiguidade sobre quem é o dono real do lock.
**Por que o PRD não cobre**: OQ-3 delega dimensionamento de timeout ao time consumidor, mas não exige nenhuma invariante relativa entre os três valores (ex.: `ttl > redis.timeout + margem`).
**Severidade**: medium

### 1.6 — Precedência entre FR-1 (mismatch de payload) e FR-2 (lock em progresso)
**Cenário**: Duas requisições quase simultâneas usam a mesma chave, mas com payloads diferentes. Não está definido se o sistema primeiro tenta `tryAcquire` (retornando `409 IN_PROGRESS` para a segunda) ou primeiro compara o hash do payload contra o que está em processamento (retornando `422 PAYLOAD_MISMATCH`, semanticamente mais correto). A ordem de checagem afeta diretamente qual código de erro o cliente recebe.
**Por que o PRD não cobre**: FR-1 e FR-2 são escritos como requisitos independentes; nenhum descreve a ordem de avaliação quando ambas condições coincidem na mesma janela de corrida.
**Severidade**: medium-high

## 2. Interações entre FRs de features diferentes que podem conflitar

### 2.1 — FR-11 pode injetar dependência Spring no `core`, violando a regra que FR-19/FR-20 vão impor
**Cenário**: FR-11 move `LocaleService` (entre outras classes) para o `core`. Serviços de resolução de locale tipicamente dependem de `LocaleContextHolder`/`MessageSource` do Spring. Se isso for verdade aqui, a classe movida por FR-11 viola diretamente a regra "core não importa `org.springframework`" que FR-19 define e FR-20 passa a impor via ArchUnit no perfil `analyze` promovido para `pluginManagement` (cobertura 100%). O build quebraria exatamente na Fase 3 (passo 5 do sequenciamento), quando o `core` já existe e a régua ArchUnit já está ativa.
**Por que o PRD não cobre**: FR-11 e FR-19 nunca são citados como dependentes entre si; o Sequenciamento apenas diz que o passo 5 "só é possível depois que o core existe", sem verificar se o conteúdo movido é compatível com as regras estruturais que o próprio F3 está introduzindo ao mesmo tempo no `core`.
**Severidade**: critical

### 2.2 — Registro de `ExceptionsHandler` (FR-12) feito duas vezes por causa do sequenciamento
**Cenário**: FR-12 (registrar via `AutoConfiguration.imports`) é executado no passo 2 (Fase 0-2 do F2), quando `ExceptionsHandler` ainda vive no módulo antigo `scos-foundation-exception`. O arquivo `META-INF/spring/....AutoConfiguration.imports` referencia o FQCN da classe naquele pacote. Só no passo 6 (Fase 4-5 do F3) a classe é fisicamente movida para o módulo `web` (FR-18). Isso obriga a editar o conteúdo do `AutoConfiguration.imports` numa segunda vez, no momento da extração do módulo `web` — exatamente o "mover a anotação duas vezes" que o próprio racional do passo 7 do Sequenciamento diz querer evitar (mas ali essa preocupação é citada só para o F1, não para o FR-12 do F2).
**Por que o PRD não cobre**: o argumento "evitar mover duas vezes" é usado explicitamente para justificar a ordem do F1 (passo 7), mas o mesmo risco recai sobre FR-12 e não é mencionado. Além disso, editar esse arquivo de recurso na extração do módulo `web` não é claramente "mover/renomear" nem "mudança de comportamento" para efeitos do NFR-2 (2 commits separados) — fica em uma zona cinzenta: se o autoconfig-import ficar desatualizado por um commit, o handler de erro simplesmente para de ser registrado, silenciosamente (sem erro de compilação).
**Severidade**: high

### 2.3 — FR-17 (consolidar `MDC_REQUEST_ID` no `core`) sem fase definida no Sequenciamento
**Cenário**: A tabela de Sequenciamento cita explicitamente FR-9, FR-10, FR-12 a FR-17 no passo 2, mas o "consolidar no `core`" de FR-17 só faz sentido depois que o `core` existe (passo 4, Fase 3) — ou seja, o mesmo problema de ordem que motivou mover FR-11 para o passo 5. FR-17 aparece agrupado com correções que rodam "com o módulo ainda no lugar" (antes do `core` existir), mas seu conteúdo (mover uma constante para o `core`) é uma operação de movimentação de módulo, não uma correção de comportamento.
**Por que o PRD não cobre**: FR-17 está listado na mesma linha da tabela que as correções de bug puras (FR-9, FR-10, FR-16), mas semanticamente pertence ao grupo de "mover para o core" do passo 5, criando ambiguidade sobre em qual fase ele realmente deveria rodar — e sobre se ele duplica a constante temporariamente entre `ScosProblemDetails` e `LoggingInitialFilter` durante a transição.
**Severidade**: medium

### 2.4 — FR-24 exige comportamento em tempo de execução dentro de módulos que FR-19 proíbe de ter dependências
**Cenário**: FR-24 exige que cada módulo `*-api` emita um log `INFO` na inicialização da aplicação consumidora, contando quantas classes anotadas foram encontradas — isso implica alguma forma de scanning de classpath/contexto Spring e uso de um logger, ou seja, no mínimo SLF4J e algum gatilho de ciclo de vida (`ApplicationListener`, `@PostConstruct`, etc). Mas FR-19 exige que módulos `*-api` "contenham apenas `@interface`/`enum`, sem dependência além de `jakarta.validation-api`". Não há como um módulo `*-api` implementar a lógica de FR-24 dentro das restrições de FR-19.
**Por que o PRD não cobre**: FR-19 e FR-24 nunca são cruzados um contra o outro; nenhuma nota indica que a lógica de contagem/log de FR-24 deveria, na verdade, viver no módulo `spring` (observando os `*-api`) e não dentro do próprio `*-api`. Como escrito, os dois requisitos são estruturalmente contraditórios e a regra ArchUnit de FR-20 (que cobre 100% dos módulos) provavelmente vai falhar a build assim que FR-24 for implementado literalmente dentro de um `*-api`.
**Severidade**: critical

### 2.5 — FR-14 assume Jackson 3, mas nenhuma FR fixa a versão de destino da migração de FR-21
**Cenário**: FR-14 diz explicitamente "compatível com Jackson 3" ao trocar regex por navegação de causa (`InvalidFormatException`/`MismatchedInputException.getPath()`). FR-21 migra Gson → Jackson na base inteira, mas não declara qual versão major do Jackson é o alvo (Spring Boot ainda tipicamente embarca Jackson 2.x; Jackson 3 é uma major diferente com pacote `tools.jackson.*` em vez de `com.fasterxml.jackson.*`). Se F3 (que roda primeiro, passo 1) migrar para Jackson 2.x e F2 (passo 2) escrever código assumindo API de Jackson 3, o código não compila ou usa a API errada.
**Por que o PRD não cobre**: nenhuma FR define a versão-alvo do Jackson; a menção a "Jackson 3" aparece isolada em FR-14 sem ligação com FR-21, que é quem efetivamente decide a dependência.
**Severidade**: medium-high

### 2.6 — Value objects (`Cpf`/`Cnpj`/`Email`/`TaxIdentifier`) movidos para `validation` (FR-18) podem ter serialização não coberta pelo inventário de FR-21
**Cenário**: FR-21 lista explicitamente "os 3 adapters de `java.time`" e "4 pontos de uso em `audit`" como escopo conhecido da migração Gson→Jackson, mas não menciona se os value objects que estão sendo simultaneamente movidos por FR-18 têm adapters Gson próprios (comum para tipos como CPF/CNPJ que normalmente serializam como string simples via `TypeAdapter` customizado). Se existirem, ficam fora do inventário declarado de FR-21 e a migração incompleta gera comportamento de serialização divergente para esses tipos.
**Por que o PRD não cobre**: FR-23 exige inventário completo das 71 classes por *destino de módulo*, mas não exige inventário cruzado de "quais classes têm serialização customizada" — não há intersecção declarada entre o inventário de FR-23 e o escopo de FR-21.
**Severidade**: high

## 3. Falha ou reversão no meio de uma fase do Sequenciamento

### 3.1 — Nenhuma estratégia de rollback para reversão tardia de um passo já "enterrado" por passos subsequentes
**Cenário**: Se um problema em um passo anterior (ex.: passo 5, mover exceptions para `core` — ver 2.1) só é descoberto depois que os passos 6 e 7 já foram concluídos (módulos folha extraídos, F1 já reescrito sobre a nova estrutura de `-api`/`core`), reverter apenas o passo 5 exige desfazer múltiplas extrações de módulo que já dependem da posição atual das exceptions no `core`. Não há critério de rollback por fase, nem plano de "reversão em cascata".
**Por que o PRD não cobre**: NFR-2 garante build verde a cada commit e separa commits de "mover" vs. "ajustar comportamento", o que ajuda a *progredir* com segurança, mas nada no PRD trata reversão depois que fases subsequentes já foram construídas sobre o resultado da fase com problema.
**Severidade**: high

### 3.2 — Granularidade de reversão dentro de uma fase que agrupa múltiplos FRs
**Cenário**: O passo 2 do Sequenciamento agrupa seis FRs (FR-9, FR-10, FR-12 a FR-17) em uma única fase "Fase 0 a 2". Se um problema for encontrado especificamente em FR-13 (unificação do formato 404) depois que FR-9/FR-10/FR-16 já foram validados e potencialmente já consumidos por testes de outras fases, não há indicação se a fase inteira deve ser revertida ou se FR-13 pode ser revertido isoladamente.
**Por que o PRD não cobre**: o Sequenciamento trata "fase" como unidade atômica de ordenação entre planos, mas não define granularidade de reversão dentro de uma fase que na prática contém FRs independentes entre si.
**Severidade**: medium

### 3.3 — OQ-2 referencia "fases 3-5 do F1" que não existem na tabela de Sequenciamento
**Cenário**: OQ-2 diz que, sob pressão de prazo, a diretriz é "cortar volume de trabalho (ex.: adiar fases 3-5 do F1)". Mas a tabela de Sequenciamento trata F1 inteiro como um único passo (#7, "Todas as fases"), sem nenhuma subdivisão declarada de FR-1 a FR-8 em fases numeradas 0-5. Não há como identificar operacionalmente quais FRs compõem "fase 3-5 do F1" para de fato cortá-las sob pressão — a mitigação de OQ-2 não é executável como está descrita.
**Por que o PRD não cobre**: a subdivisão em fases granular parece existir apenas no documento de origem do F1 (não citado/anexado aqui), mas o PRD consolidado não traz essa tabela, criando uma referência pendurada (dangling reference) entre um risco (OQ-2) e um requisito que o leitor do PRD não consegue mapear.
**Severidade**: high

### 3.4 — Falha da dependência externa (hash-chain do `audit`) bloqueando a Fase 1.5 sem plano B
**Cenário**: O PRD declara que a Fase 1.5 do F3 (Gson→Jackson) depende de uma ação externa e não controlada por este PRD: remoção/reprocessamento do hash-chain do `audit` (OQ-4). Se essa dependência externa atrasar ou não acontecer, a Fase 1.5 fica bloqueada — mas como a Fase 1.5 é o primeiro passo de todo o sequenciamento (passo 1), isso bloqueia toda a cadeia de 7 passos que vem depois. Não há plano de contingência (ex.: seguir com F2 em paralelo antes de F3 Fase 1.5, já que aparentemente não haveria conflito direto de arquivos entre eles nessa janela específica) nem critério de "quanto tempo esperar antes de reordenar".
**Por que o PRD não cobre**: OQ-4 documenta a dependência e seu dono, mas trata apenas da condição de revisão ("confirmar se existe hash-chain persistido"), não do que fazer operacionalmente se a resposta demorar ou for "sim, existe e não pode ser removido agora".
**Severidade**: high

## 4. Edge cases na migração Gson→Jackson (FR-21) além da política de nulos

### 4.1 — Determinismo de serialização para o hash-chain do `audit` a longo prazo
**Cenário**: OQ-4 trata apenas da invalidação *pontual* do hash-chain no momento do corte (hashes antigos ficam inválidos). Mas não discute se a serialização Jackson usada dali em diante é *deterministicamente estável* entre versões/reinicializações da aplicação (ordem de campos, presença de espaços, formatação de números) da mesma forma que a reflexão por ordem de declaração do Gson garantia. Se algum `ObjectMapper` compartilhado tiver `MapperFeature.SORT_PROPERTIES_ALPHABETICALLY` habilitado (ou vier a ser habilitado no futuro sem ninguém perceber o impacto), o hash-chain quebra de novo, silenciosamente, sem nenhum "big bang" de migração para alertar.
**Por que o PRD não cobre**: FR-21 e OQ-4 tratam a mudança de hash como evento único de corte, não como uma invariante contínua que precisa ser garantida (e testada) daqui para frente.
**Severidade**: critical

### 4.2 — Estratégia de introspecção: campos privados sem getters (Gson) vs. convenção JavaBean (Jackson)
**Cenário**: Gson serializa por reflexão direta de campos, inclusive privados sem getter. Jackson, por padrão, usa introspecção baseada em getters/setters (ou requer configuração/anotação para acessar campos diretamente, ou suporte a records/`@JsonCreator` para tipos imutáveis). Qualquer classe do domínio (incluindo os value objects `Cpf`/`Cnpj`/`Email`/`TaxIdentifier` movidos por FR-18) escrita assumindo acesso direto a campo pode serializar como `{}` vazio sob Jackson sem erro de compilação nem exceção em runtime — falha silenciosa.
**Por que o PRD não cobre**: FR-21 menciona apenas a política de nulos como diferença comportamental conhecida e aceita; não há menção à estratégia de introspecção de campos como outra fonte de divergência de payload.
**Severidade**: critical

### 4.3 — Tipos numéricos em estruturas genéricas (`Map<String,Object>`/JSON não tipado)
**Cenário**: Para deserialização em estruturas genéricas (comum no `JsonMasker`, que precisa percorrer JSON arbitrário para mascarar campos), Gson tipicamente produz `Double`/`LazilyParsedNumber` para números, enquanto Jackson (via `ObjectMapper` para `Object`/`Map`) tipicamente produz `Integer`/`Long`/`Double`/`BigDecimal` dependendo do valor. Qualquer lógica que faça `instanceof Double` ou comparação de tipo numérico dentro do caminho O(n) do `JsonMasker` (citado explicitamente em FR-21 como característica a preservar) pode se comportar de forma diferente após a migração.
**Por que o PRD não cobre**: FR-21 preserva explicitamente "a característica O(n)" (desempenho) do `JsonMasker`, mas não menciona a preservação de *comportamento* de tipagem ao percorrer estruturas genéricas — só cobre nulos.
**Severidade**: high

### 4.4 — Diferença de exceções lançadas em JSON malformado
**Cenário**: Gson lança `JsonSyntaxException` (unchecked) para JSON malformado; Jackson lança `JsonProcessingException`/subclasses (checked, `extends IOException`). Qualquer `catch` específico de exceção Gson nos 4 pontos de uso citados em `audit` (`ScosAuditHashService`, `ScosAuditServiceBean`, `ScosAuditBatchConsumer`, `ScosAuditDlqJob`) deixa de capturar a exceção equivalente do Jackson, alterando o comportamento de fallback/retry nesses pontos (exceção não tratada se propaga onde antes era capturada).
**Por que o PRD não cobre**: FR-21 lista os 4 pontos de uso como escopo de migração, mas não pede auditoria de tratamento de exceção nesses pontos — só liga a preocupação de compatibilidade a FR-14, que é sobre o handler HTTP do F2, não sobre o módulo `audit`.
**Severidade**: medium-high

### 4.5 — Formatação de datas além dos 3 adapters removidos
**Cenário**: FR-21 remove os 3 adapters customizados de `java.time` do Gson, delegando a serialização de datas ao suporte nativo do Jackson (`jackson-datatype-jsr310`). O formato padrão do Jackson para `Instant`/`OffsetDateTime` (presença/ausência de offset, precisão de nanosegundos vs. milissegundos, `WRITE_DATES_AS_TIMESTAMPS`) pode diferir do formato que os 3 adapters customizados produziam. Isso é uma mudança de formato de wire para qualquer consumidor externo que dependa do formato de data atual — não apenas para o hash-chain interno já coberto por OQ-4.
**Por que o PRD não cobre**: apenas a política de nulos é citada como mudança de comportamento intencionalmente aceita; a mudança de formato de data não é mencionada nem como aceita nem como rejeitada — fica noqueada.
**Severidade**: high

## 5. FRs com dependência implícita não numerada

### 5.1 — FR-16 (padronização de log por status) depende implicitamente de FR-9/FR-10 já estarem corrigidos
**Cenário**: FR-16 padroniza log de `4xx` como `WARN` sem stack trace e `5xx` como `ERROR` com stack trace. Antes de FR-9/FR-10 corrigirem a classificação de status (403 misclassificado como 500, 400 misclassificado como 500), o código de status observado pelo logger de FR-16 é o *errado*. Se FR-16 for implementado/testado antes de FR-9/FR-10 dentro da mesma fase (ambos estão no passo 2, sem ordem interna definida), os testes de FR-16 podem validar contra o status incorreto.
**Por que o PRD não cobre**: FR-16 e FR-9/FR-10 estão listados na mesma célula da tabela de Sequenciamento sem ordem relativa entre si, apesar de FR-16 semanticamente precisar rodar *depois* que a classificação de status já esteja correta para ter efeito observável correto.
**Severidade**: medium

### 5.2 — FR-12 depende implicitamente da existência do módulo `web` de FR-18, mas é executado antes dele
**Cenário**: Já detalhado em 2.2 — FR-12 registra `ExceptionsHandler` via `AutoConfiguration.imports` no passo 2, mas o módulo `web` onde essa classe deveria residir definitivamente (segundo FR-11) só é criado no passo 6. Isso é uma dependência de ordem não declarada como tal na tabela (a tabela só declara a dependência de FR-11 em relação ao `core`, não a dependência de FR-12 em relação ao `web`).
**Por que o PRD não cobre**: repetido de 2.2, listado aqui pela ótica específica de "dependência implícita entre FRs não numerada" pedida no escopo desta seção.
**Severidade**: high

### 5.3 — FR-8 (`@JdempotentProperty`/`IdempotencyKeyResolver`) depende implicitamente de FR-6 (percorrer hierarquia de classes) já estar em vigor
**Cenário**: FR-8 introduz um seletor explícito de campos com serialização canônica via `TreeMap`. Para que esse seletor funcione corretamente em classes com herança, ele precisa da mesma correção de percurso de hierarquia que FR-6 descreve (hoje limitado a `getDeclaredFields()`). Se FR-8 for implementado sem reaproveitar a correção de FR-6, o novo seletor herda o mesmo bug que FR-6 foi criado para corrigir.
**Por que o PRD não cobre**: FR-6 e FR-8 não se referenciam mutuamente; nada impede uma implementação onde o mecanismo de resolução de campos de FR-8 seja escrito do zero, sem reusar a correção de hierarquia de FR-6.
**Severidade**: medium

### 5.4 — FR-20 (regra ArchUnit no perfil `analyze`) depende de FR-19 estar totalmente especificado antes de virar teste automatizado, mas FR-19 tem lacuna sobre o módulo `feign`
**Cenário**: FR-19 define regras estruturais para `core`, `spring`, `*-api` e proíbe qualquer módulo (exceto aplicações) de depender de `web`. FR-18 cria um módulo `feign` dedicado (decisão D3) e um módulo `web` com dependência formal de `cache` (decisão D1). FR-19 nunca menciona explicitamente que regras se aplicam a `feign`, `cache`, `jpa` ou `audit-api` individualmente — só cobre `core`, `spring`, `*-api` e a proibição genérica de depender de `web`. FR-20, que promete "cobertura em 100% dos módulos", precisa preencher essa lacuna de regras não declaradas para módulos específicos, mas o PRD não define quais são essas regras (ex.: `feign` pode importar `jakarta.persistence`? `cache` pode importar Redis diretamente?).
**Por que o PRD não cobre**: FR-19 é escrito como lista fechada de regras para módulos específicos citados nominalmente; FR-20 promete cobertura total, criando uma dependência implícita de que todas as regras faltantes serão "inventadas" na hora de escrever os testes ArchUnit, sem que o PRD documente qual é o critério.
**Severidade**: medium
