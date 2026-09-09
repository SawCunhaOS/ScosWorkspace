# Story 3.8: Tornar a política de falha por exceção de negócio declarável por método

Status: done

<!-- baseline_commit: 84f91c099c51cb5460f8b9ba470fbcb42c3a6433 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor cujo endpoint pode falhar por regra de negócio,
Eu quero escolher entre `RELEASE` (permite retry) e `KEEP_FAILED` (evita duplicar efeito colateral),
Para adequar o comportamento ao meu caso de uso.

## Acceptance Criteria

1. **Given** um método anotado com a política `KEEP_FAILED`, **When** a execução lança exceção de negócio, **Then** o erro é gravado como resultado (chave não é removida).
2. **And** o comportamento padrão (`RELEASE`, remove a chave) é mantido para métodos sem a anotação explícita.

## Tasks / Subtasks

- [x] Task 1: Confirmar o comportamento atual (contexto) (AC: #2)
  - [x] **Confirmado por leitura direta**: `IdempotentAspect.execute()`, linhas 183-189 — `catch (Exception e) { idempotentRepository.remove(idempotencyKey); throw e; }`. Hoje **toda** exceção de negócio remove a chave incondicionalmente (equivalente ao futuro `RELEASE`), sem opção de manter o erro registrado. Não existe hoje nenhum enum ou atributo de anotação para esta política.
- [x] Task 2: Criar o enum de política (AC: #1, #2)
  - [x] Criar um enum (ex.: `IdempotentFailurePolicy` com valores `RELEASE`, `KEEP_FAILED`) em `utils/annotation/jdempotent/` (mesmo pacote de `JdempotentResource`, já que módulos `*-api`/anotações ainda não existem — este módulo é `utils`, migra para `jdempotent-api` só na Epic 1 Story 1.5, que já foi concluída; confirmar se `JdempotentResource` já vive no novo módulo `jdempotent-api` ou ainda em `utils` antes de decidir o pacote final) — **confirmado**: `JdempotentResource` já vive em `jdempotent-api` (módulo dedicado, `br.com.sawcunhaos.foundation.jdempotent.api`), não em `utils`; o enum foi criado no mesmo pacote/módulo. `ArchitectureTest` do módulo já permite `enum` além de `@interface`, então nenhuma regra de arquitetura precisou mudar.
  - [x] Adicionar um atributo à anotação `@JdempotentResource` (ex.: `IdempotentFailurePolicy onBusinessException() default IdempotentFailurePolicy.RELEASE`) — `RELEASE` como default preserva o comportamento atual para métodos sem declaração explícita (AC #2)
- [x] Task 3: Implementar a política `KEEP_FAILED` em `IdempotentAspect` (AC: #1)
  - [x] No bloco `catch` de `execute()`, ler o atributo de política da anotação `@JdempotentResource` do método
  - [x] Se `RELEASE` (ou ausente): manter o comportamento atual — `idempotentRepository.remove(idempotencyKey)`
  - [x] Se `KEEP_FAILED`: em vez de remover a chave, gravar o erro como resultado usando o mesmo mecanismo de `setResponse`/`IdempotentResponseWrapper` já usado para respostas de sucesso (decidir se a exceção é serializada diretamente ou envolvida numa representação equivalente — manter consistência com o que `IdempotentResponseWrapper` já suporta) — **decisão final (pós-revisão, ver "Correções da revisão de código" abaixo)**: a exceção original **não** é guardada como está. `CachedBusinessFailure.of(e).encode()` grava uma `String` codificada (classe + mensagem) como `response`; no replay (`lease.hasCachedResponse()`), `CachedBusinessFailure.decodeIfPresent(...)` reconhece essa `String` e o aspecto lança `IdempotentReplayedFailureException` (não a exceção original — só classe/mensagem sobrevivem).
- [x] Task 4: Testes (AC: #1, #2)
  - [x] Teste: método anotado com `KEEP_FAILED` lança exceção de negócio → confirmar que a chave permanece no repositório e uma chamada subsequente com a mesma chave recebe o erro gravado (não reexecuta o método)
  - [x] Teste: método sem a anotação explícita de política (comportamento padrão) lança exceção → confirmar que a chave é removida (comportamento idêntico ao atual, sem regressão) — já coberto pelo teste pré-existente `given_invalid_payload_when_trigger_aspect_then_throw_test_exception_and_repository_will_be_empty`, que continua verde sem alteração.

## Dev Notes

- Esta é uma mudança de comportamento **aditiva** (novo atributo com default que preserva o comportamento atual) — não deve quebrar nenhum consumidor existente que já usa `@JdempotentResource` sem essa configuração.
- **NFR4**: o comportamento padrão (`RELEASE`) deve ser bit-a-bit idêntico ao comportamento atual para não introduzir regressão silenciosa nos consumidores que não optarem por `KEEP_FAILED`.
- Não confundir com o `errorCallback`/`ErrorConditionalCallback` já existente (linhas 191-194 de `IdempotentAspect.execute()`) — esse mecanismo trata uma condição de erro **dentro de um resultado bem-sucedido** (não uma exceção lançada), é um caminho diferente do `catch (Exception e)` que esta story modifica. Não misturar os dois mecanismos.

### Project Structure Notes

- Arquivo modificado: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java`.
- Arquivo novo: enum de política de falha (local exato depende de onde `JdempotentResource` estiver após a Epic 1 — confirmar antes de criar).
- Arquivo modificado: a anotação `JdempotentResource` (novo atributo).

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L183-L194]
- [Source: utils/src/main/java/br/com/sawcunhaos/foundation/utils/annotation/jdempotent/JdempotentResource.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-38-tornar-a-política-de-falha-por-exceção-de-negócio-declarável-por-método]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -pl jdempotent-api,jdempotent -am test`: `BUILD SUCCESS` — 71 testes unitários no módulo `jdempotent` (mais 2 em `jdempotent-api`, 26 em `core`, 50 em `privacy`, dependências via `-am`), 0 falhas.
- `mvn -pl jdempotent-api,jdempotent -am verify` (1ª rodada, antes da correção pós-revisão): `BUILD FAILURE` — o novo teste de integração contra Redis real (`RedisIdempotentRepositoryTopologyITTest`) pegou exatamente o bug que a revisão apontou (ver abaixo): `AssertionFailedError: expected CachedBusinessFailure but was LinkedHashMap`.
- `mvn -pl jdempotent-api,jdempotent -am verify` (após a correção): `BUILD SUCCESS` — 71 unitários + 16 testes de integração (Testcontainers) do módulo `jdempotent` (15 pré-existentes + 1 novo), 0 falhas. Nenhum teste do módulo `audit` foi executado (fora do escopo desta story, `audit` não é dependência de `jdempotent`).

### Completion Notes List

- `IdempotentFailurePolicy` (`RELEASE`, `KEEP_FAILED`) criado em `jdempotent-api` (mesmo módulo/pacote de `JdempotentResource`, que já havia migrado de `utils` para `jdempotent-api` na Epic 1). `ArchitectureTest` do módulo já permitia `enum` além de `@interface`, então nenhuma regra de arquitetura precisou mudar.
- `@JdempotentResource` ganhou o atributo `onBusinessException()`, default `RELEASE` — preserva bit-a-bit o comportamento atual para consumidores existentes (NFR4, AC #2).
- Comportamento padrão (`RELEASE`/ausência da anotação explícita) permanece inalterado — coberto pelo teste pré-existente `given_invalid_payload_when_trigger_aspect_then_throw_test_exception_and_repository_will_be_empty`, que continua verde sem alteração (AC #2).
- `IdempotentAspectUTTest`: contagem de mocks (`getSignature`/`getMethod`) ajustada de 4→5 e 3→4 respectivamente, refletindo a nova chamada a `getAnnotation(...).onBusinessException()` dentro de `execute()`.
- Nenhum trabalho no módulo `audit` — fora do escopo declarado desta story.

### Correções da revisão de código (3 camadas: blind hunter, edge-case hunter, verification-gap)

A implementação inicial guardava a exceção de negócio crua diretamente como `response`. A revisão (verification-gap) comprovou, compilando e executando `PolymorphicRedisSerializer` de verdade, que isso quebra em produção: exceções com construtor `(message, cause)` ou campo extra — a maioria das exceções de negócio idiomáticas — falham ao desserializar do Redis; o efeito real não é "reproduzir a falha", é o próximo `tryAcquire()` lançar `SerializationException` ao ler, cair no fail-open (Story 3.7), tratar o lease como recém-adquirido e **reexecutar o método de negócio** — exatamente o efeito colateral que `KEEP_FAILED` existe para evitar. O teste original não pegou isso porque só usava o repositório em memória (guarda por referência, nunca serializa).

Decisão do usuário (2026-08-30): não guardar a exceção original; guardar um wrapper serializável. Uma primeira tentativa (`CachedBusinessFailure` como POJO aninhado em `IdempotentResponseWrapper#response`, campo `Object`) também falhou — achado **próprio**, feito ao rodar o novo teste de integração contra Redis real: `PolymorphicRedisSerializer` só registra o tipo concreto na raiz do que é serializado (`IdempotentRequestResponseWrapper`); qualquer POJO aninhado num campo `Object` volta do Redis como `LinkedHashMap` genérico, não seu tipo original — um gap pré-existente e mais amplo do módulo (afeta qualquer resposta de sucesso que seja um objeto complexo), registrado em `deferred-work.md` para não expandir o escopo desta story. Decisão final do usuário: `CachedBusinessFailure` codifica a falha como uma `String` (classe + mensagem, com marcador fixo), a única forma que sobrevive ao campo `Object` sem tocar na infraestrutura de serialização compartilhada; o replay lança `IdempotentReplayedFailureException` (não a exceção original — só classe/mensagem sobrevivem, perda de fidelidade de tipo aceita pelo usuário como trade-off).

Achados da revisão explicitamente fora do escopo desta story (documentados em `deferred-work.md`, não corrigidos aqui):
- `errorCallback.onErrorCondition(result)` sempre remove a chave, ignorando `onBusinessException()` — pré-existente, fora do escopo por decisão da própria story (Dev Notes: "não misturar os dois mecanismos").
- `KEEP_FAILED` reaproveita o mesmo `ttl`/`ttlTimeUnit` do sucesso, sem janela de retenção configurável separada — lacuna de produto, não bug, não exigida por nenhuma AC.
- `IdempotentResponseWrapper#response` (campo `Object`) perde o tipo de qualquer POJO complexo num round-trip real pelo Redis — gap arquitetural mais amplo do módulo, descoberto durante esta story.

### File List

- `jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/IdempotentFailurePolicy.java` (novo) — enum `RELEASE`/`KEEP_FAILED`.
- `jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/JdempotentResource.java` (modificado) — novo atributo `onBusinessException()`, default `RELEASE`.
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/CachedBusinessFailure.java` (novo, correção da revisão) — codifica/decodifica a falha de negócio cacheada como `String` (classe + mensagem).
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/exception/IdempotentReplayedFailureException.java` (novo, correção da revisão) — lançada no replay de uma falha `KEEP_FAILED`.
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modificado) — política `KEEP_FAILED` no `catch` de `execute()` (grava `CachedBusinessFailure.of(e).encode()`) e replay via `CachedBusinessFailure.decodeIfPresent(...)`/`IdempotentReplayedFailureException`.
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTest.java` (modificado) — novo teste cobrindo AC #1 (chave mantida, falha reproduzida sem reexecução, via `IdempotentReplayedFailureException`).
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java` (modificado) — contagens de mock ajustadas para a nova leitura de `onBusinessException()`.
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/utils/TestIdempotentResource.java` (modificado) — método de teste anotado com `onBusinessException = KEEP_FAILED` e contador de invocações.
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTopologyITTest.java` (modificado, correção da revisão) — novo teste provando que a falha `KEEP_FAILED` sobrevive a um round-trip real pelo Redis (o gap que a revisão apontou).
- `CHANGELOG.md` (modificado) — entrada descrevendo a política de falha declarável por método e o `IdempotentReplayedFailureException`.
- `_bmad-output/implementation-artifacts/deferred-work.md` (modificado) — 3 achados da revisão registrados como débito, fora do escopo desta story.

## Suggested Review Order

**Contrato da anotação**

- Ponto de entrada: novo atributo, `RELEASE` como default preserva o comportamento atual (AC #2).
  [`JdempotentResource.java:57`](../../jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/JdempotentResource.java#L57)

**Codificação da falha (correção pós-revisão — o desenho final)**

- `encode()`: grava classe+mensagem como `String` com marcador fixo — não um POJO aninhado, que voltaria do Redis como `LinkedHashMap` (achado da revisão).
  [`CachedBusinessFailure.java:57`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/CachedBusinessFailure.java#L57)

- `decodeIfPresent()`: reconhece a `String` codificada no replay; retorna `null` para qualquer resposta de sucesso normal.
  [`CachedBusinessFailure.java:66`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/model/CachedBusinessFailure.java#L66)

- Lançada no replay em vez da exceção original — só classe/mensagem sobrevivem, trade-off aceito pelo usuário.
  [`IdempotentReplayedFailureException.java:34`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/exception/IdempotentReplayedFailureException.java#L34)

**`IdempotentAspect`: gravação e replay**

- No `catch`, `KEEP_FAILED` grava a falha codificada e não remove a chave (AC #1); `RELEASE`/ausência mantém o comportamento atual.
  [`IdempotentAspect.java:212`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L212)

- No caminho de replay, decodifica a falha cacheada e lança `IdempotentReplayedFailureException` em vez de devolver o valor como retorno normal.
  [`IdempotentAspect.java:188`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L188)

**Testes**

- Prova, contra Redis real (não em memória), que a falha sobrevive ao round-trip — o teste que pegou o bug da revisão.
  [`RedisIdempotentRepositoryTopologyITTest.java:243`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/repository/RedisIdempotentRepositoryTopologyITTest.java#L243)

- Cobertura de AC #1 via `IdempotentAspectTest` (repositório em memória): chave mantida, falha reproduzida sem reexecução.
  [`IdempotentAspectTest.java:140`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTest.java#L140)

- Fixture de teste anotada com `KEEP_FAILED` e contador de invocações, usada pelo teste acima.
  [`TestIdempotentResource.java:39`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/utils/TestIdempotentResource.java#L39)

- Contagem de mock ajustada para a nova leitura de `onBusinessException()` dentro de `execute()`.
  [`IdempotentAspectUTTest.java:96`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java#L96)

**Peculiar**

- Entrada de changelog do módulo.
  [`CHANGELOG.md:76`](../../CHANGELOG.md#L76)
