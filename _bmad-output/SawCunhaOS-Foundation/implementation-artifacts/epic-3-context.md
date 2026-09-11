# Epic 3 Context: Confiabilidade de Idempotência sob Concorrência e Falha do Redis

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Tornar o módulo `jdempotent` seguro sob concorrência real e falha do Redis. Chamadas concorrentes com a mesma chave nunca duplicam efeito de negócio: a segunda chamada recebe `409 IN_PROGRESS` explícito (não `null` silencioso) via lock atômico, e uma chamada com a mesma chave mas payload diferente recebe `422 PAYLOAD_MISMATCH` em vez da resposta cacheada compartilhada (mismatch tem precedência sobre in-progress quando os dois coincidem na mesma janela de corrida). Quando o Redis fica indisponível ou lento, o módulo falha aberto (nunca fail-closed) atrás de um circuit breaker — nesse cenário, quem garante a não-duplicidade de fato é a constraint `UNIQUE` do banco, não o cache (idempotência em cache é fast-path, não garantia). O épico também corrige um conjunto de bugs de correção/segurança que bloqueavam a adoção segura do módulo: NPE em Redis não-Sentinel, hashing fraco (MD5), resolução incompleta de hierarquia de campos, bean duplicado do aspecto, TTL ignorado, `equals`/`hashCode` incorretos e desserialização insegura no Redis.

## Stories

- Story 3.1: Corrigir a inicialização do `RedisConnectionFactory`
- Story 3.2: Migrar hashing de MD5 para SHA-256
- Story 3.3: Resolver campos anotados em toda a hierarquia de classes
- Story 3.4: Registrar `IdempotentAspect` sem duplicidade e sem `ThreadLocal`
- Story 3.5: Tornar a aquisição do lock atômica (`tryAcquire`/`Lease`)
- Story 3.6: Detectar colisão de payload sob a mesma chave
- Story 3.7: Garantir fail-open com circuit breaker quando o Redis está indisponível
- Story 3.8: Tornar a política de falha por exceção de negócio declarável por método
- Story 3.9: Posicionar o aspecto de idempotência fora do escopo transacional
- Story 3.10: Tornar o namespace de prefixo de chave configurável
- Story 3.11: Expor métricas de idempotência
- Story 3.12: Introduzir `IdempotencyKeyResolver` com composição de chave declarativa
- Story 3.13: Suportar header `Idempotency-Key` como fonte de chave
- Story 3.14: Migrar configuração para `@ConfigurationProperties`
- Story 3.15: Corrigir TTL e `equals`/`hashCode`
- Story 3.16: Adicionar allowlist de tipos no `PolymorphicRedisSerializer`
- Story 3.17: Substituir construtores telescópicos por builder e documentar o princípio de design

## Requirements & Constraints

- Critério de sucesso: zero colisão/duplicidade de processamento em operação normal (Redis disponível). Sob degradação (fail-open), duplicidade é risco aceito — a garantia passa a ser a constraint `UNIQUE` do banco.
- Todo endpoint com chave natural (ex.: login, tenant+cpf) precisa de constraint `UNIQUE` no banco antes de habilitar `jdempotent` — pré-requisito, não recomendação; documentado no README do módulo e no checklist de revisão de endpoints.
- Fail-open é inegociável: indisponibilidade/lentidão do Redis nunca bloqueia a requisição de negócio; o circuit breaker detecta lentidão respeitando `spring.data.redis.timeout`.
- A chave de idempotência é sempre resolvida por um único resolver compartilhado — nunca reimplementada por entrypoint (aspecto HTTP vs. listener de mensageria). Sem contexto web, o resolver devolve `null` de forma limpa, nunca lança exceção (o módulo não é HTTP-only).
- TTL do lease é sempre `java.time.Duration` (nunca tipo numérico cru em unidade implícita) e configurável por método.
- `X-Request-ID` nunca é reaproveitado como chave de idempotência; a fonte via header usa `Idempotency-Key` dedicado, com precedência header → campos anotados → hash.
- Cobertura de teste: mínimo 80% (jacoco) nas áreas tocadas por este épico (concorrência, colisão de hex, aspecto duplicado, indisponibilidade de Redis via Testcontainers). Cada correção de bug precisa de teste que reproduza a falha antes do fix; nenhuma mudança de comportamento além do declarado por story.
- Sem guia de migração formal ou aviso a consumidores nesta release (lib ainda SNAPSHOT, base piloto) — o CHANGELOG é a única superfície de comunicação.
- Riscos operacionais de alta probabilidade a vigiar: (a) cliente gerando a chave dentro do próprio laço de retry anula a deduplicação — mitigado por documentação e pela métrica `.hit` próxima de zero; (b) fail-open lento (Redis fora somando o timeout completo por chamada) pode saturar o pool de threads antes de qualquer alerta disparar — mitigado pelo circuit breaker e por um timeout de comando Redis enxuto.
- Sob pressão de prazo, cortar volume de trabalho (3.12 a 3.17 são candidatas a adiamento), nunca contrato — nunca introduzir lock não-atômico ou fail-closed silencioso (3.1, 3.2, 3.3, 3.5, 3.6, 3.7, 3.9 não são candidatas a corte).

## Technical Decisions

- Contrato de aquisição: `tryAcquire(key, payloadHash, ttl) → Lease`, substituindo o fluxo não-atômico `contains → store → setResponse`. A arquitetura original previa Lua script; a implementação real da Story 3.5 usa `SET NX PX` (`setIfAbsent`) — aceito como satisfazendo o contrato até revisão indicar o contrário.
- Circuit breaker: `io.github.resilience4j:resilience4j-spring-boot4:2.4.0` (não `-spring-boot3`), `optional=true`, fixado explicitamente no `pom.xml` do `jdempotent` — não é gerenciado por nenhum BOM do projeto.
- Métricas via interface própria `IdempotencyMetrics`, no-op por padrão, Micrometer condicional (nunca acoplar direto ao Micrometer): `idempotency.acquired`, `.hit`, `.in_progress`, `.mismatch`, `.backend_error`, `.degraded` (gauge 0/1), `.degraded.transitions` (counter).
- Hashing migra de MD5/`Integer.toHexString` para SHA-256 via enum `CryptographyAlgorithm` + `HexFormat.of().formatHex()`; resolução de campos anotados percorre toda a hierarquia de classes, não só `getDeclaredFields()`.
- `IdempotentAspect` deve se autorregistrar com `@ConditionalOnMissingBean` (evita bean duplicado com múltiplos pontos de registro) e não pode usar `ThreadLocal` para `MessageDigest` (quebra sob virtual threads).
- `@Order` do aspecto fica fora do escopo do `@Transactional`, para que um rollback nunca deixe a chave órfã no Redis.
- Conexão Redis vem do `RedisConnectionFactory` gerenciado pelo Spring Boot, não de uma `RedisSentinelConfiguration` montada à mão (hoje causa NPE em `getSentinel()` para Redis standalone/cluster).
- Namespace de prefixo de chave passa a ser propriedade Spring obrigatória (falha explícita se ausente), substituindo o fallback silencioso via `System.getenv(APP_NAME)`. Configuração geral migra de `@Value` solto para `@ConfigurationProperties`; o `EnvironmentPostProcessor` do módulo (hoje mal declarado em `AutoConfiguration.imports`, nunca executa) precisa ser corrigido.
- Política de falha por exceção de negócio é declarável por método: `RELEASE` (default, remove a chave, permite retry) ou `KEEP_FAILED` (grava o erro como resultado, evita duplicar efeito colateral).
- `PolymorphicRedisSerializer` precisa de allowlist de tipos permitidos, checada antes de `Class.forName` sobre valor vindo do Redis (risco de desserialização de tipo arbitrário).
- Construtores telescópicos são substituídos por builder; o README do módulo documenta "cache é fast-path, não garantia", a obrigatoriedade da constraint `UNIQUE` e a ordem relativa recomendada dos três timeouts independentes: `ttl` do lease > `slow-call-duration-threshold` do circuit breaker > `spring.data.redis.timeout` (com margem) — dimensionamento exato fica a cargo de cada time consumidor.
- Convenção de teste do módulo (`maven-failsafe-plugin:3.5.4`, mesma linha do Surefire já herdado): unit test usa sufixo padrão `*Test` (Surefire, roda em `mvn test`); qualquer teste que suba Testcontainers/Docker usa sufixo único `*ITTest.java`, bindado às fases `integration-test`/`verify` do Failsafe (roda em `mvn verify`) — evita Docker subindo durante unit test. Testes de concorrência/topologia exercitam só o contrato `tryAcquire(...) → Lease`, nunca `contains`/`store`/`setResponse` isolados. Teste de fail-fast cobre config de Redis malformada/incompleta nas 3 topologias (Standalone/Sentinel/Cluster) via `ApplicationContextRunner` — não cobre Redis alcançável mas fora do ar (esse caso é fail-open, não fail-fast). Teste de throughput/TPS é sempre informativo (log), nunca gate (`assertTrue(tps > limiar)` é proibido).

## Cross-Story Dependencies

- Ordem de build interna recomendada: correção de chave (3.2, 3.3, 3.4) → contrato de execução concorrente (3.5, 3.1, 3.8, 3.9, 3.10) → chave composta declarativa (3.12) → header como fonte de chave (3.13) → endurecimento em paralelo (3.14–3.17).
- Story 3.6 (`422 PAYLOAD_MISMATCH`) tem precedência sobre o `409 IN_PROGRESS` da Story 3.5 quando as duas condições coincidem na mesma janela de corrida.
- Story 3.13 (header) e qualquer entrypoint futuro de mensageria dependem do `IdempotencyKeyResolver` único introduzido na Story 3.12.
- As métricas da Story 3.11 dependem de instrumentação adicionada por outras stories: `in_progress`/`hit`/`acquired` vêm da 3.5, `mismatch` da 3.6, `backend_error`/`degraded`/`degraded.transitions` da 3.7.
- Dependência leve com o Épico 1 (decomposição do `utils`): as anotações `@Jdempotent*` precisam já estar em `jdempotent-api` antes das mudanças deste épico, para não mover a mesma classe duas vezes.
