# Review Adversarial — jdempotent, Qualidade de Teste Redis (spine 2026-08-29)

Alvo: `ARCHITECTURE-SPINE.md` (AD-6..AD-9), lido junto com a spine pai `2026-08-19` (AD-1, AD-2, AD-4, AD-5) para checar herança.

Método: para cada AD, construir dois engenheiros hipotéticos que implementam a mesma regra em paralelo, obedecendo a letra do texto, e ver se produzem builds/artefatos incompatíveis. Depois, checar contradição com invariantes herdados e dimensões silenciosas.

---

## Achado 1 (crítico) — AD-6: sufixo `*ITTest.java` não é pego pelo Failsafe por padrão

**A regra:** "Toda classe que sobe Testcontainers/Docker Compose usa sufixo `*IT.java` ou `*ITTest.java` e é excluída do `maven-surefire-plugin`". O `maven-failsafe-plugin` é novo no `pom.xml` do `jdempotent`, não gerenciado pelo `scos-bom` — ou seja, sem `<includes>` herdado de lugar nenhum.

**O problema:** os padrões de inclusão *default* do Failsafe são `**/IT*.java`, `**/*IT.java`, `**/*ITCase.java`. Uma classe chamada `FooITTest.java` **não bate com nenhum desses três padrões** (o nome termina em `Test.java`, não em `IT.java`). A AD nunca especifica um `<includes>` explícito no `pom.xml` cobrindo `*ITTest.java`.

**Dois engenheiros, ambos obedecendo a AD-6 ao pé da letra:**
- **Engenheiro A** cria `RedisIdempotentRepositoryTryAcquireIT.java` (sufixo `*IT.java`) — cai certinho no include default do Failsafe, roda em `mvn verify`.
- **Engenheiro B** segue o exemplo literal do próprio texto da AD-6 e renomeia `PrimeNumbersJdempotentEnableTest` → `PrimeNumbersJdempotentEnableITTest` (sufixo `*ITTest.java`, exatamente como a AD instrui). Essa classe é corretamente excluída do Surefire (via `<excludes>`), mas **nunca é pega pelo Failsafe** sem um `<includes>` explícito que a AD não pede.

**Resultado:** exatamente as duas classes que a AD-6 cita como motivação (`PrimeNumbersJdempotentEnableTest`/`DisableTest`, hoje "rodando incorretamente sob Surefire") passam, após a "correção", a **não rodar em nenhuma fase** — nem `mvn test` (excluídas de propósito) nem `mvn verify` (não batem no include default). Build verde, teste morto. Isso é pior que o problema original que a AD-6 diz resolver.

**Fechar com:** a AD precisa fixar OU um único sufixo (eliminar a ambiguidade `*IT.java` vs `*ITTest.java`) OU, se ambos ficam, obrigar um `<includes>**/*IT.java,**/*ITTest.java</includes>` explícito no `maven-failsafe-plugin` — hoje só o `<excludes>` do Surefire está especificado, o `<includes>` do Failsafe não.

---

## Achado 2 (alto) — AD-7 usa vocabulário que a própria spine, na mesma tabela de Inherited Invariants, proíbe como sinal de "fluxo antigo"

A tabela "Inherited Invariants" desta mesma spine, linha AD-2, diz textualmente: *"Todo teste de concorrência/topologia desta spine valida contra `tryAcquire(...)  → Lease` e o comportamento fail-open com circuit breaker — **nunca** contra o fluxo antigo `contains → store → setResponse`."*

A Rule da AD-7 (que é exatamente "o teste de concorrência/topologia desta spine") lista os asserts como: *"`tryAcquire` atômico sob concorrência real, `contains`, `setResponse`"* — citando `contains` e `setResponse` lado a lado com `tryAcquire`, sem deixar claro se são (a) checagens funcionais pós-aquisição, independentes da garantia de atomicidade, ou (b) parte do mecanismo de verificação de não-duplicidade sob concorrência.

**Dois engenheiros, ambos citando a AD-7 ao pé da letra:**
- **Engenheiro A** usa `tryAcquire` como único mecanismo de exclusão mútua sob concorrência e chama `contains`/`setResponse` só depois, como checagem de estado final (leitura), nunca como parte da corrida. Conforme AD-2 herdada.
- **Engenheiro B** lê a lista de asserts da AD-7 como uma receita de teste e monta a verificação de não-duplicidade entrelaçando `contains → tryAcquire → setResponse` entre threads concorrentes ("testar os mesmos asserts... sob concorrência real" é o texto literal da AD-7) — reconstruindo exatamente o fluxo `contains → store → setResponse` que a AD-2 herdada proíbe.

**Também é um silêncio, não só uma colisão de nomes:** a obrigação de validar "o comportamento fail-open com circuit breaker" (texto herdado, vinculante — está em `binds: [AD-2]` no front matter) **não aparece em nenhuma Rule concreta de AD-6 a AD-9**. AD-8 cobre fail-fast na inicialização (cenário diferente, explicitamente distinto por texto próprio), AD-9 é throughput, AD-7 não menciona circuit breaker nenhuma vez. Ou seja: a spine herda uma obrigação de teste (fail-open sob circuit breaker, por topologia) e não a operacionaliza em nenhum AD novo, nem a lista em Deferred/Open Questions — fica muda.

**Fechar com:** reescrever a Rule da AD-7 para deixar explícito que `contains`/`setResponse` são checagens de leitura pós-condição, não mecanismo de exclusão mútua; e decidir explicitamente se a validação de fail-open+circuit-breaker por topologia é escopo desta spine (e vira uma AD-10, ou item da AD-7) ou fica Deferred com justificativa — hoje está em nenhum dos dois estados.

---

## Achado 3 (médio) — AD-7 não fixa a estrutura da parametrização nem o ciclo de vida dos containers

"`@ParameterizedTest` + `@MethodSource` ou enum de topologia" autoriza duas arquiteturas de teste incompatíveis:

- **Engenheiro A:** `@MethodSource` retornando `Stream<Arguments>`, container Testcontainers sobe **por invocação de parâmetro** (isolamento total, custo de CI alto — 3x subida de container por método de teste).
- **Engenheiro B:** `enum Topology { STANDALONE, SENTINEL, CLUSTER }` com `@EnumSource`, containers `static` compartilhados subindo uma vez em `@BeforeAll` (barato, mas risco de vazamento de estado/chave entre iterações de topologia se nada reseta o Redis entre elas).

Nenhuma das duas viola a letra da AD-7. O nome da classe também não é fixado (Structural Seed só diz "nova classe parametrizada de topologia", sem nome) e o `Consistency Conventions` não cobre isso. Resultado prático: divergência real em custo de CI, isolamento de teste e nome de classe entre quem implementa primeiro vs. quem copia o padrão depois.

**Fechar com:** decidir lifecycle dos containers (por-parâmetro vs. compartilhado+reset) e fixar o nome de classe no Structural Seed, do jeito que já foi feito para `RedisIdempotentRepositoryTryAcquireITTest`.

---

## Achado 4 (médio) — AD-8 assume um comportamento de produção que pode não existir (conexão lazy)

AD-8 exige que o contexto Spring falhe a subir tanto para "configuração inválida" quanto para "Redis inalcançável". Essas são duas classes de falha tecnicamente diferentes:

- **Config inválida** (propriedade obrigatória ausente/malformada) falha naturalmente no *property binding*, antes mesmo de qualquer I/O — fácil de testar com `ApplicationContextRunner`.
- **Redis inalcançável** (host/porta sintaticamente válidos, mas sem serviço do outro lado) só derruba o contexto na subida **se algo no bean de conexão fizer um ping eager**. Drivers Redis (Lettuce/Jedis) tipicamente conectam **lazy** — o `RedisConnectionFactory` é criado com sucesso e só falha na primeira operação real. Se não existir hoje um health-check/ping eager no `ScosJdempotentRedisConfiguration`, o cenário "inalcançável" da AD-8 é **impossível de tornar verdadeiro só com teste** — precisaria de código de produção novo (uma verificação eager no `@PostConstruct` ou similar), o que é uma decisão arquitetural que esta spine nunca menciona nem autoriza.

**Dois engenheiros:**
- **Engenheiro A** testa só o caminho "config inválida" e declara a AD-8 satisfeita.
- **Engenheiro B** tenta testar "Redis inalcançável" literalmente, descobre que o contexto sobe normal (comportamento lazy), e fica sem saber se deve (i) golpear a AD como já satisfeita pelo caso de config inválida, (ii) escrever um teste que vai falhar contra o comportamento real do produto, ou (iii) abrir uma story de produção para adicionar verificação eager — nenhuma dessas opções está autorizada ou decidida pela spine.

**Fechar com:** a spine precisa dizer explicitamente se "Redis inalcançável" cobre também mudança de código de produção (eager health check) ou se o escopo real da AD-8 é só "config inválida" (e o nome/texto da AD deveria refletir isso, não prometer os dois cenários).

---

## Achado 5 (baixo/médio) — AD-9: "número fixo de operações... por um tempo fixo" mistura dois desenhos de teste de throughput

A frase da Rule ("roda um número fixo de operações `tryAcquire` concorrentes por um tempo fixo") descreve, ao mesmo tempo, um teste limitado por contagem (N operações, mede o tempo total) e um teste limitado por tempo (roda por D segundos, conta quantas operações completaram) — são loops de controle diferentes.

- **Engenheiro A:** `for i in 1..N: submit(tryAcquire)`, `awaitAll`, `TPS = N / elapsed`.
- **Engenheiro B:** roda um `while (Instant.now() < deadline)` por D segundos fixos, conta operações completas, `TPS = count / D`.

Como o assert é só "sem erro/exceção" (nunca um piso de TPS), isso não quebra CI — mas os dois testes não são comparáveis entre si nem produzem uma série histórica útil de TPS (o próprio propósito "informativo" do AD-9 fica comprometido se cada implementação mede algo estruturalmente diferente). Nível de concorrência (quantas threads simultâneas) também não é fixado.

**Fechar com:** escolher um dos dois desenhos (recomendo tempo fixo + contagem, é o padrão usual de teste de throughput) e fixar o grau de concorrência (ex.: tamanho de thread pool) na Rule.

---

## Achado 6 (alto, silêncio da spine) — nada garante que o CI realmente rode `mvn verify`

Toda a AD-6 depende de `mvn verify` (não `mvn test`) para as novas classes `*IT`/`*ITTest` rodarem em algum lugar. A spine não toca em nenhum arquivo de pipeline (CI), não menciona se o estágio de CI hoje invoca `mvn test` ou `mvn verify`, e não lista isso em Deferred/Open Questions.

Se o pipeline atual só chama `mvn test` (motivo original, aliás, pelo qual os testes IT problemáticos foram escritos sem sufixo — para serem executados em CI), a AD-6 tem o efeito líquido de **parar de rodar completamente** os testes de integração em CI (incluindo o novo teste de topologia da AD-7, o novo teste de fail-fast da AD-8, e o novo teste de throughput da AD-9), silenciosamente, porque ninguém decidiu mudar o comando de CI. Isso é uma regressão maior que o bug que a spine tenta corrigir (testes rodando errado sob Surefire vira: testes não rodando em lugar nenhum).

**Fechar com:** adicionar ao escopo (ou a uma AD nova, ou pelo menos a uma linha explícita nesta spine) a atualização do pipeline de CI para invocar `mvn verify`, ou registrar isso como Open Question/Deferred explícito — hoje está em silêncio total, não é nem decidido nem listado como pendência.

---

## Achado 7 (baixo) — paralelismo/forking do Failsafe entre as 3 topologias não é endereçado

A causa-raiz documentada (Stories 3.1/3.4/3.5) é `ContainerLaunchException`/porta já alocada. AD-7 sobe potencialmente 3 conjuntos de containers (Standalone/Sentinel/Cluster) na mesma classe parametrizada. Nada na spine fixa `forkCount`/execução serial vs. paralela do Failsafe para essa classe — se o Failsafe rodar com paralelismo default e os containers não isolarem portas dinamicamente (Testcontainers normalmente isola, mas Sentinel/Cluster multi-container tem mais superfície), existe risco real de reintroduzir o mesmo sintoma que motivou toda a spine. Vale ao menos uma linha explícita dizendo que a execução é sequencial/serial por padrão do Failsafe (que é o default) e que isso é intencional.

---

## Checagem de contradição com ADs herdadas (AD-1, AD-2, AD-4, AD-5)

- **AD-1** (fronteira/direção de dependência): não violado. Nenhuma AD nova cria módulo, e o `maven-failsafe-plugin` é config local ao `pom.xml` do `jdempotent`.
- **AD-2** (contrato de aquisição): **ver Achado 2** — a obrigação herdada de validar fail-open+circuit-breaker "em todo teste de concorrência/topologia desta spine" não é operacionalizada em nenhuma Rule concreta (AD-7 não a implementa), e a lista de asserts da AD-7 usa vocabulário (`contains`, `setResponse`) que colide com o texto que a própria AD-2 herdada proíbe.
- **AD-4** (piso de documentação): não violado — a linha herdada só exige Javadoc nas classes de teste novas, escopo compatível.
- **AD-5** (ArchUnit como mecanismo de imposição): não violado — a linha herdada corretamente escopa que o split unit/IT é local ao módulo, não cross-módulo, então não precisa de regra ArchUnit. Consistente.

Nenhuma AD nova **enfraquece explicitamente** o texto de uma AD herdada (não há reescrita ou afrouxamento direto de regra). O problema é o inverso: AD-2 herdada exige algo que nenhuma AD nova entrega (gap de operacionalização), não uma contradição de texto.

## Dimensões que deveriam estar decididas/deferidas e estão silenciosas

1. **Pipeline de CI não menciona `mvn verify`** (Achado 6) — nem decidido, nem Deferred, nem Open Question.
2. **Fail-open + circuit breaker por topologia** (Achado 2) — obrigação herdada sem Rule que a cubra, e sem menção em Deferred.
3. **Include pattern do Failsafe para `*ITTest.java`** (Achado 1) — mecânica de build necessária para a AD-6 funcionar, ausente do texto da própria Rule.
4. **Lifecycle de containers na AD-7** (Achado 3) — arquitetura de teste com duas leituras válidas e incompatíveis.
5. **Viabilidade técnica de "Redis inalcançável" sob conexão lazy** (Achado 4) — pressupõe comportamento de produção não confirmado.

Todo o resto (versionamento pós-1.2.0, timeout/circuit breaker por ambiente, extensão do padrão Failsafe para `audit`, divergência Lua-script vs. `SET NX PX`) já está corretamente listado em Deferred na spine — esses não são achados novos, a spine já os endereçou de forma honesta.
