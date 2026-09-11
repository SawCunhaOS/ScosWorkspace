# Reconciliação — plano-atualizacao-jdempotent.md vs PRD

## Gaps encontrados

1. **Princípio central ausente.** "Idempotência em cache é fast-path, não garantia" (seção 2 do plano) — a frase-guia de todo o plano, que o próprio plano exige que vá no README do módulo — não aparece em nenhum lugar do PRD (FRs, NFRs, riscos). É a peça qualitativa mais importante e foi completamente apagada pela estrutura de requisitos funcionais.

2. **Premissa fixa #2 (constraint UNIQUE obrigatória) ausente.** O plano declara, duas vezes (premissas fixas e seção 2.4 "Consequência que precisa estar registrada"), que a constraint `UNIQUE` no banco deixa de ser recomendação e vira **obrigação** para todo método com chave natural, e que isso precisa entrar no README e no checklist de revisão de endpoints. Nenhuma FR, NFR ou risco do PRD menciona essa obrigação — nem sequer o risco correspondente ("Duplicata criada durante degradação", mitigado exatamente por essa constraint) foi carregado para a seção de Riscos do PRD.

3. **Premissa fixa #3 / seção 2.6 (delegar conexão Redis ao Spring Boot) ausente das FRs.** O plano descreve um bug real de produção: `ScosJdempotentRedisConfiguration` monta `RedisSentinelConfiguration` assumindo Sentinel, e `getSentinel()` é `null` (NPE no startup) para qualquer app com Redis standalone/cluster. A correção — parar de construir `LettuceConnectionFactory` própria e injetar o `RedisConnectionFactory` que o Boot já monta via `@ConditionalOnBean` — não vira nenhuma FR. FR-4 toca de raspão só o timeout (`spring.data.redis.timeout`), mas não a causa raiz nem o bug de NPE.

4. **Fase 5 "Endurecimento" inteira ausente como FR.** Nenhum item da tabela da Fase 5 tem correspondente em FR-1 a FR-8: migração `@Value` → `@ConfigurationProperties`; `EnvironmentPostProcessor` declarado em `AutoConfiguration.imports` e por isso **nunca executa** (bug real, não cosmético); TTL ignorado por completo no `InMemoryIdempotentRepository` (default em 4 de 7 construtores); `equals`/`hashCode` não-reflexivo/não-simétrico no `IdempotentRequestWrapper` (SpotBugs suprimido incorretamente); allowlist no `PolymorphicRedisSerializer` (achado de segurança: `Class.forName` sobre valor vindo do Redis sem validação de tipo); construtores telescópicos → builder; README do módulo. Isso é uma fase de 2 dias inteira de correções reais que desapareceu.

5. **Política de falha declarável (RELEASE/KEEP_FAILED) ausente.** Seção 2.3 do plano descreve uma funcionalidade específica e não trivial (comportamento em exceção configurável por método, default `RELEASE`). Não há FR correspondente — a única menção a "release"/lease no PRD é dentro do contrato `tryAcquire`/`Lease` (FR-2), que não cobre a política de exceção pós-execução.

6. **Riscos de alta probabilidade do plano original perdidos ou diluídos.** A tabela de riscos do plano (seção 6) tem dois itens marcados **Alta**: "Cliente gera chave dentro do laço de retry" (o erro mais comum do padrão, segundo o plano) e "Fail-open lento: Redis fora somando 5s por requisição e saturando o pool". Nenhum dos dois aparece como risco explícito no PRD — FR-4/OQ-3 tocam o tema do timeout/circuit breaker, mas sem carregar a gravidade ("Alta" probabilidade) nem a orientação operacional associada ("alinhar com os times consumidores que a chave deve ser gerada antes do laço de retry", seção 4.6). Também ausentes: "Degradação passa despercebida por dias" e "Header perdido em `@Async`" (RequestContextHolder é ThreadLocal).

7. **Observabilidade reduzida a uma frase genérica.** FR-7 diz apenas "Expor métricas via interface IdempotencyMetrics (no-op / Micrometer condicional)". Perdido: a lista concreta de métricas (`idempotency.acquired`, `.hit`, `.in_progress`, `.mismatch`, `.backend_error`, `.degraded`, `.degraded.transitions`); o alerta obrigatório (`idempotency.degraded == 1` por mais de X minutos); e o insight mais valioso do plano — "taxa de hit próxima de zero num endpoint com retry ativo denuncia chave sendo gerada dentro do laço de retry do cliente" (seção 2.7), que é o mecanismo de detecção do risco item 6 acima. Também some a ideia de que a Fase 0 de testes vira asserção numérica via `SimpleMeterRegistry`, não "parece funcionar".

8. **`@Order` do aspecto fora de `@Transactional` (seção 2.5) ausente.** Sem essa ordem explícita, um rollback deixa a chave órfã no Redis. Não há FR nem risco correspondente no PRD.

9. **"O módulo não é só HTTP" (seção 4.3) ausente.** FR-3 descreve o header apenas do ângulo HTTP (`headerName="Idempotency-Key"`), mas o plano insiste que o aspecto também serve consumidores de mensageria (chama `cachePrefix` de "listener name") e que o resolver **precisa devolver `null` limpo** e nunca estourar quando não há contexto web. Essa restrição de design, e o risco correlato de header sumir em execução `@Async` (ThreadLocal do `RequestContextHolder`), não aparecem no PRD.

10. **Namespace de chave obrigatório ausente.** Seção 2.4 do plano aponta um bug concreto: `DefaultKeyGenerator` lê o nome da app via `System.getenv(APP_NAME)` (fora do modelo Spring, silenciosamente vazio se ausente) e propõe torná-lo propriedade Spring obrigatória, prefixando toda chave — necessário porque o Redis pode ser compartilhado entre aplicações. Não vira FR.

11. **Correções pontuais da Fase 1 sem FR própria.** O `@ConditionalOnMissingBean(IdempotentAspect.class)` (corrige bean duplicado, item 1.3) e a remoção do `ThreadLocal` de `MessageDigest` (contraproducente com virtual threads, NPE latente, item 1.5) aparecem apenas indiretamente — o teste de "duplo aspecto" é citado em NFR-3, mas a correção em si não tem FR. A causa raiz do bug (`ScosJdempotentConfig` sem `@ConditionalOnMissingBean`) fica implícita.

## Cobertura confirmada

- Contrato `Lease` (ACQUIRED/IN_PROGRESS/COMPLETED/PAYLOAD_MISMATCH) e a virada de `null` silencioso para `409`/`422`: bem coberto em FR-1/FR-2.
- Migração de hash (MD5→SHA-256, `HexFormat`) e correção da varredura de hierarquia de classes: FR-5/FR-6.
- Header `Idempotency-Key`, precedência header → campos → hash, e a rejeição explícita de reaproveitar `X-Request-ID`: FR-3 (mesmo perdendo o "por quê" — ver gap 9).
- Chave composta declarativa (`IdempotencyKeyResolver`, `@JdempotentProperty` como seletor, serialização canônica `TreeMap`, `@JdempotentId` saindo da composição): bem coberto em FR-8.
- Fail-open como premissa inegociável (nunca `FAIL_CLOSED`) e o circuit breaker via Resilience4j com detecção por lentidão: capturado em FR-4, embora sem a profundidade de justificativa do plano original.
- Liberdade de versão (SNAPSHOT, sem guia de migração, "cortar volume não contrato" em caso de aperto de prazo): bem refletido em "Comunicação e Migração" e OQ-2.
- Ordem de execução em relação ao plano de decomposição do `utils` (mover anotações antes de mexer nelas aqui, para não mover a mesma classe duas vezes): bem coberto na tabela de "Sequenciamento e Fases", linha 7.
