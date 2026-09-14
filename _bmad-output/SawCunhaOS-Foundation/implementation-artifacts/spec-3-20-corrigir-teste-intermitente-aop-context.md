---
title: 'Corrigir teste intermitente given_aop_context_then_run_with_aop_context'
type: 'bugfix'
created: '2026-09-14'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `IdempotentAspectTest.given_aop_context_then_run_with_aop_context` (jdempotent/src/test/java/.../core/aspect/IdempotentAspectTest.java:80) busca a anotação `@JdempotentResource` via `TestIdempotentResource.class.getDeclaredMethods()[1]` — um lookup por índice fixo cuja ordem não é garantida pela JVM, causando falha intermitente (`expected: not <null>`) quando a suíte completa do módulo roda (reproduzido 2/3 vezes). Item de débito registrado em `deferred-work.md`, origem Story 3.20.

**Approach:** Trocar o lookup por índice fixo por uma busca determinística: percorrer `getDeclaredMethods()` e pegar a anotação `@JdempotentResource` do primeiro método que a possuir, em vez de depender de posição de array.

</frozen-after-approval>

## Implementation Notes

- `IdempotentAspectTest.given_aop_context_then_run_with_aop_context` trocado de `TestIdempotentResource.class.getDeclaredMethods()[1]` para `Arrays.stream(...).map(getAnnotation).filter(nonNull).findFirst()` — pega a anotação `@JdempotentResource` do primeiro método que a possuir, sem depender de posição de array (não garantida pela JVM).
- Verificado: `mvn -pl jdempotent test` (suíte completa do módulo) rodado 3x seguidas — o teste alvo passou nas 3, sem nenhuma falha. A única falha remanescente nas 3 execuções é `InMemoryIdempotentRepositoryTtlTest.given_setResponse_repeatedly_refreshes_the_ttl_while_contains_races_the_expiry_check_then_the_entry_is_never_incorrectly_evicted` — pré-existente, já documentada como não relacionada (débito da Story 3.15/3.20, timing-sensitive concurrency test), fora do escopo deste fix.
- Ajuste pós-review (blind-hunter, achado 2): `Arrays.stream(...).findFirst()` ainda deixava a asserção quase tautológica (10 dos 12 métodos declarados em `TestIdempotentResource` têm `@JdempotentResource` — qualquer um faria o teste passar mesmo se o método originalmente visado perdesse a anotação). Trocado para `getDeclaredMethod("idempotentMethod", IdempotentTestPayload.class).getAnnotation(...)` — igualmente determinístico, mas nomeia exatamente o método sob teste; elimina o import `Arrays` e o método de teste passa a declarar `throws NoSuchMethodException`.
- Comentário de 2 linhas adicionado acima do teste (achado 3), seguindo a convenção já usada no arquivo para testes ligados a story/débito (ex.: Story 3.13, 3.15).
- `assertNotNull` ganhou mensagem de falha explícita (achado 5), para que uma regressão futura não volte a produzir um `expected: not <null>` sem contexto.
- Re-verificado após o ajuste: `mvn -pl jdempotent test` — `IdempotentAspectTest`: 16/16 passam; única falha remanescente é a mesma `InMemoryIdempotentRepositoryTtlTest` pré-existente e fora de escopo.

## Review Triage Log

Camada rodada: blind-hunter (7 achados, N mínimo = 2).

1. **Branch `release/1.2.0` em vez de `fix/x.y.z`.** Verdict: `false`. Evidência: `git branch -a`/`git tag` confirmam que não há tag `1.2.0` (release ainda não publicada) e as únicas branches `fix/*` existentes (`fix/1.0.1`, `fix/1.1.1`) correspondem a releases já lançadas — a convenção do workspace usa `fix/x.y.z` para patch pós-lançamento, não durante estabilização. Story 3.17/3.20 já foram implementadas direto em `release/1.2.0`, mesmo padrão seguido aqui.
2. **Asserção quase tautológica (10/12 métodos de `TestIdempotentResource` têm `@JdempotentResource`).** Verdict: `low`. Evidência: `findFirst()` sobre o stream resolvia o determinismo mas não a especificidade. → `patch`: trocado para `getDeclaredMethod("idempotentMethod", ...)`.
3. **Falta comentário explicando a mudança, quebrando convenção do arquivo (Story 3.13/3.15/3.19).** Verdict: `low`. Evidência: confirmado por leitura do arquivo — testes vizinhos ligados a story/débito sempre têm comentário. → `patch`.
4. **`.filter(annotation -> annotation != null)` deveria ser `Objects::nonNull`.** Verdict: `low`. Evidência: estilo, correto. → resolvido de forma diferente (achado 2 eliminou o stream inteiro, tornando este ponto sem objeto).
5. **`assertNotNull` sem mensagem de falha.** Verdict: `low`. Evidência: uma regressão futura reproduziria a mesma falha pouco informativa que motivou esta story. → `patch`.
6. **Spec/débito vive no repo do workspace, não no Foundation — risco de desconexão do histórico.** Verdict: `low`. Evidência: real, mas resolvido garantindo que a mensagem de commit referencia a story/spec. → `patch` (via mensagem de commit).
7. **Confirmação de que não há outra instância do mesmo antipadrão no repo.** Não é achado de problema (positivo/escopo completo) — nenhuma ação.

## Ampliação de escopo (a pedido do usuário)

O usuário pediu, antes do commit, para também corrigir `InMemoryIdempotentRepositoryTtlTest.given_setResponse_repeatedly_refreshes_the_ttl_while_contains_races_the_expiry_check_then_the_entry_is_never_incorrectly_evicted` — a outra falha intermitente documentada em `deferred-work.md` (origem Story 3.20, item Completion Notes: "só ... falha — pre-existing, unrelated"), para fechar de fato os dois itens de débito da story antes do commit.

**Investigação:** o teste seedava/atualizava a entrada com TTL de 1ms enquanto 8 threads (4 writers + 4 readers) batalhavam pelo lock por chave do `ConcurrentHashMap`. Reproduzido isoladamente 3x: `observedAbsent` chegava a 70–170 **milhões** por execução — não é jitter raro, é sistemático. Causa raiz: com TTL=1ms, o tempo entre dois refreshes sucessivos (sob a contenção de 8 threads no mesmo bucket) frequentemente ultrapassa 1ms mesmo sob implementação correta — expiração legítima, não perda de update. Confirmado experimentalmente (reintroduzindo temporariamente o `getIfNotExpired()` não-atômico pré-Story-3.15 e revertendo em seguida) que a janela da race de identidade que este teste pretende capturar é da ordem de **nanossegundos**, ordens de magnitude menor que qualquer TTL de parede estável sob contenção real — nenhum valor de TTL isola as duas coisas.

**Fix aplicado:** TTL de refresh elevado para 100ms (variável local, com comentário explicando o histórico), com warm-up (refreshers iniciam e rodam por 1 período de TTL antes dos readers começarem a contar, evitando expiração de cold-start), contador de tentativas de leitura (`readAttempts > 1000`, contra passagem vazia caso as threads mal rodem) e verificação de integridade da resposta (`assertEquals("alive", ...)`) além da ausência. Javadoc do método atualizado para não afirmar mais uma garantia que o teste, no timing atual, não sustenta — documentado como smoke test de carga concorrente, não mais como detector confiável da race de identidade específica (essa já é prevenida estruturalmente pelo único caminho `computeIfPresent` atômico em `AbstractIdempotentRepository`).

**Verificado:** classe isolada 3x (7/7 verde) e suíte completa do módulo 3x (132/132 verde, `BUILD SUCCESS`).

**Deferido:** um teste unitário determinístico e independente de timing para a race de identidade (mutar-então-ler sob interleaving controlado contra `setResponse`/`getIfNotExpired`) — a lacuna de cobertura real que sobra após esta correção — registrado em `deferred-work.md`.

