# Story 3.9: Posicionar o aspecto de idempotência fora do escopo transacional

Status: done

<!-- baseline_commit: 2f03f3317ca095943fa7a6afe9c6d6399cb2c917 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor usando `@Transactional`,
Eu quero que um rollback de transação não deixe a chave de idempotência órfã no Redis,
Para não bloquear indevidamente uma nova tentativa legítima.

## Acceptance Criteria

1. **Given** um método anotado com `@Jdempotent*` e `@Transactional` que sofre rollback, **When** o `@Order` do aspecto está fora do escopo do `@Transactional`, **Then** a chave não fica presa no Redis após o rollback.

## Tasks / Subtasks

- [x] Task 1: Confirmar a lacuna atual (contexto) (AC: #1)
  - [x] **Confirmado por leitura direta**: `IdempotentAspect` (`@Aspect`, `@Around` em `execute()`) **não declara nenhum `@Order`** — busca por `@Order`/`Ordered.` em todo `jdempotent/src/main/java` não encontrou nenhuma ocorrência. Sem `@Order` explícito, a ordem de execução entre o aspecto de idempotência e o interceptor transacional do Spring (`@Transactional`, que tem sua própria ordem de AOP, tipicamente próxima de `Ordered.LOWEST_PRECEDENCE` por padrão) fica sujeita à ordem de registro dos beans — não determinística o suficiente para garantir a semântica exigida por este AC
  - [x] O risco concreto: se o aspecto de idempotência executa **dentro** do escopo da transação (interceptor transacional "por fora", aspecto de idempotência "por dentro"), um rollback da transação desfaz efeitos de banco mas **não desfaz** a chave já gravada no Redis pelo `IdempotentAspect` (Redis não participa da transação JDBC/JPA) — a chave fica presa até o TTL expirar, bloqueando uma nova tentativa legítima do mesmo consumidor
- [x] Task 2: Definir e aplicar o `@Order` correto (AC: #1)
  - [x] Adicionado `@Order(Ordered.HIGHEST_PRECEDENCE)` a `IdempotentAspect` — garante que ele executa **fora** (outer) do interceptor transacional, independentemente da ordem de registro dos beans
  - [x] Valor concreto de `@Order`: `Ordered.HIGHEST_PRECEDENCE` (`Integer.MIN_VALUE`) — menor que a ordem padrão do interceptor transacional do Spring (`BeanFactoryTransactionAttributeSourceAdvisor`, `Ordered.LOWEST_PRECEDENCE` por padrão, a menos que o consumidor sobrescreva via `@EnableTransactionManagement(order=...)`), o que coloca o aspecto de idempotência sempre "por fora" no proxy AOP
- [x] Task 3: Teste de rollback (AC: #1)
  - [x] Escrito `IdempotentAspectTransactionalRollbackTest` (novo contexto Spring real com `@EnableAspectJAutoProxy` + `@EnableTransactionManagement`, `IdempotentAspectTest`-style) com um método `@Transactional` + `@JdempotentResource` que lança uma exceção de negócio causando rollback. Dois testes:
    1. Confirma que a transação realmente fez rollback (via `PlatformTransactionManager` fake que rastreia `doRollback`/`doCommit` — módulo não tem DataSource/JDBC real) e que a chave correspondente **não existe mais** no `InMemoryIdempotentRepository` logo após.
    2. Inspeciona a cadeia de `Advisor`s do proxy AOP real (`Advised#getAdvisors()`) e confirma que o advisor do `IdempotentAspect` está posicionado **antes** (outer) do `BeanFactoryTransactionAttributeSourceAdvisor` transacional.
  - **Resultado observado, documentado conforme pedido pela task**: o teste 1 (exceção de negócio → rollback → chave removida) **passa mesmo sem o `@Order`** — `IdempotentAspect.execute()` sempre envolve `pjp.proceed()` num try/catch que remove a chave em qualquer exceção, independente de o interceptor transacional estar "dentro" ou "fora"; a exceção lançada diretamente pelo método de negócio sempre desenrola por esse catch de qualquer forma. Já o teste 2 (ordenação real dos advisors) **falha sem o `@Order`** — confirma exatamente o cenário de risco descrito na Task 1: sem ordenação explícita, o `BeanFactoryTransactionAttributeSourceAdvisor` fica posicionado antes do advisor do `IdempotentAspect` na cadeia do proxy (interceptor transacional "por fora", aspecto de idempotência "por dentro"). Com o `@Order(Ordered.HIGHEST_PRECEDENCE)` aplicado, ambos os testes passam. O `@Order` explícito continua necessário mesmo o teste 1 passando "por acidente", pois torna a ordenação determinística (não dependente de ordem de registro de beans) e cobre o caso que o teste 1 não consegue exercitar sem um `DataSource`/JDBC real: uma falha de commit *após* o método retornar com sucesso.

## Dev Notes

- Esta story interage com a Story 3.4 (registro do bean `IdempotentAspect` via `@ConditionalOnMissingBean`) e com a Story 3.8 (política `RELEASE`/`KEEP_FAILED` no mesmo bloco `catch`) — as três tocam a mesma região de `ScosJdempotentConfig`/`IdempotentAspect.execute()`. Coordenar a ordem de implementação para não conflitar em merge (sugestão: 3.4 → 3.8 → 3.9, já que 3.9 só adiciona `@Order`, não muda a lógica do `catch` em si).
- **Atenção**: se a Story 3.5 (lock atômico) já estiver implementada quando esta story for feita, o "remove no catch" pode ter mudado de forma/local — reconferir contra o código real no momento da implementação, não assumir que as linhas 183-189 ainda existem exatamente como descritas aqui.
- Não introduzir um mecanismo de compensação/two-phase-commit entre Redis e o banco — fora de escopo, não pedido pelo AC. A solução é puramente de ordenação de AOP.

### Project Structure Notes

- Arquivo modificado: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (adição de `@Order`).

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-39-posicionar-o-aspecto-de-idempotência-fora-do-escopo-transacional]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -pl jdempotent test` (unit tests, com o fix aplicado): todos verdes.
- `mvn -pl jdempotent verify` (unit + integration tests, com o fix aplicado): todos verdes (`RedisIdempotentRepositoryFailOpenITTest`, `RedisIdempotentRepositoryTopologyITTest`, `PrimeNumbersJdempotentDisableITTest`, `RedisIdempotentRepositoryTopologySmokeITTest`, `RedisIdempotentRepositoryTpsSweepITTest`, `RedisIdempotentRepositoryTpsSpringContextITTest`, `PrimeNumbersJdempotentEnableITTest`, `PrimeNumbersJdempotentRedisUnavailableITTest`).
- `mvn -pl jdempotent -Dtest=IdempotentAspectTransactionalRollbackTest test`, rodado 3x manualmente para documentar o comportamento antes/depois do `@Order` (ver Task 3 acima): com o fix, 2/2 passam; sem o `@Order` (temporariamente removido e restaurado), o teste de ordenação de advisors falha como esperado e o teste de exceção de negócio passa mesmo assim (documentado).

### Completion Notes List

- Adicionado `@Order(Ordered.HIGHEST_PRECEDENCE)` em `IdempotentAspect` (única mudança de produção) — garante que o aspecto de idempotência envolve (outer) o interceptor transacional do Spring, independente da ordem de registro dos beans.
- Não foi necessário nenhum mecanismo de compensação/two-phase-commit entre Redis e banco (fora de escopo, conforme Dev Notes) — a solução é puramente de ordenação de AOP, como já antecipado pela story.
- Teste novo usa um `PlatformTransactionManager` fake (`RollbackTrackingTransactionManager`, sem `DataSource`/JDBC real — o módulo jdempotent não tem essa dependência) para provar que a transação realmente executou um rollback real via Spring (`@Transactional` + `@EnableTransactionManagement`), não apenas que uma exceção foi lançada.
- Reutilizado o padrão já existente em `TestAopContext`/`TestIdempotentResource`/`IdempotentAspectTest` (contexto Spring real com `@EnableAspectJAutoProxy`, proxy AOP real, não mocks) para o novo teste, em vez de criar um mecanismo de teste novo.
- Story interage com 3.4/3.8 na mesma região de código, conforme Dev Notes — não houve conflito: a única mudança de produção desta story é a anotação `@Order` na classe, e o bloco `catch`/lógica de `RELEASE`/`KEEP_FAILED` da Story 3.8 (linhas ~209-233) não foi tocado.

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modificado: `@Order(Ordered.HIGHEST_PRECEDENCE)`)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTransactionalRollbackTest.java` (novo; ajustado na revisão — teste de falha de commit pós-retorno + identificação de advisors por tipo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/TestAopTransactionalContext.java` (novo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/RollbackTrackingTransactionManager.java` (novo; ajustado na revisão — `failNextCommit()`)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/utils/TestTransactionalIdempotentResource.java` (novo; ajustado na revisão — segundo método sem exceção)

## Suggested Review Order

**Fix de produção: ordenação do aspecto**

- Único ponto de mudança de produção — anotação que garante que `IdempotentAspect` envolve (outer) o interceptor transacional do Spring, independente da ordem de registro dos beans.
  [`IdempotentAspect.java:78`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L78)

**Teste: caso que a ordenação realmente resolve (commit falha após retorno bem-sucedido)**

- Adicionado na revisão (achado de gap de verificação): prova que uma falha de commit pós-retorno não deixa resposta de sucesso obsoleta cacheada — o caso que motivou o `@Order`.
  [`IdempotentAspectTransactionalRollbackTest.java:133`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTransactionalRollbackTest.java#L133)

- `failNextCommit()` simula a falha de commit sem exigir `DataSource`/JDBC real, que este módulo não possui.
  [`RollbackTrackingTransactionManager.java:62`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/RollbackTrackingTransactionManager.java#L62)

**Teste: prova direta da ordenação dos advisors**

- Ajustado na revisão (achado de robustez): identifica os advisors por tipo/identidade (`AbstractAspectJAdvice`/`BeanFactoryTransactionAttributeSourceAdvisor`) em vez de valor de `@Order` ou substring de nome de classe.
  [`IdempotentAspectTransactionalRollbackTest.java:174`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTransactionalRollbackTest.java#L174)

**Teste: caminho de rollback por exceção de negócio (AC #1)**

- Confirma que o cenário literal do AC (rollback por exceção de negócio) não deixa a chave órfã — passa mesmo sem `@Order` (ver Javadoc da classe), mas documenta a lacuna que motivou a Task 3.
  [`IdempotentAspectTransactionalRollbackTest.java:94`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTransactionalRollbackTest.java#L94)

**Suporte: contexto Spring com AOP + transação reais**

- Contexto de teste com `@EnableAspectJAutoProxy` + `@EnableTransactionManagement`, mesmo formato de `TestAopContext` já existente, para exercitar o proxy AOP real.
  [`TestAopTransactionalContext.java:36`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/TestAopTransactionalContext.java#L36)

- Fixture com o método `@Transactional` + `@JdempotentResource` usado pelos três testes.
  [`TestTransactionalIdempotentResource.java:26`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/utils/TestTransactionalIdempotentResource.java#L26)
