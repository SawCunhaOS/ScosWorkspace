# Story 3.3: Resolver campos anotados em toda a hierarquia de classes

Status: done

<!-- baseline_commit: 8ef6f537b280035a0236b1b0348dbbdef2cd8c3e -->
<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor com hierarquia de herança nos DTOs,
Eu quero que todos os campos anotados componham a chave,
Para não ter colisão por campo herdado ignorado.

## Acceptance Criteria

1. **Given** uma classe com campos anotados herdados de uma superclasse, **When** a chave é composta, **Then** a resolução percorre toda a hierarquia (não apenas `getDeclaredFields()`).

## Tasks / Subtasks

- [x] Task 1: Corrigir a coleta de campos em `IdempotentAspect.getIdempotentNonIgnorableWrapper()` (AC: #1)
  - [x] Em `IdempotentAspect.java`, linha 296, `Field[] declaredFields = arg.getClass().getDeclaredFields();` só enxerga os campos declarados na classe concreta do argumento — campos declarados em superclasses (via `extends`) nunca entram no loop e portanto nunca passam pela `annotationChain` (`JdempotentIgnoreAnnotationChain` → `JdempotentPropertyAnnotationChain` → `JdempotentDefaultChain`)
  - [x] Substituir por uma coleta que percorre `arg.getClass()` e todos os `getSuperclass()` até `Object.class`, concatenando os `getDeclaredFields()` de cada nível
  - [x] Preservar o comportamento atual para campos da própria classe (não reordenar nem deduplicar além do necessário para evitar processar o mesmo campo duas vezes em caso de shadowing de nome entre subclasse e superclasse)
- [x] Task 2: Teste com hierarquia de herança (AC: #1)
  - [x] Criar um DTO de teste com uma superclasse tendo um campo anotado (`@JdempotentProperty` ou campo simples sem anotação, conforme o comportamento padrão da `JdempotentDefaultChain`) e confirmar que o valor da superclasse aparece na chave composta
  - [x] Cobrir também o caminho `setJdempotentId()` (linha 281, mesmo padrão de `getDeclaredFields()` sem herança) **apenas se o epics.md ou o dono do requisito confirmar que também deve percorrer hierarquia** — o AC desta story menciona explicitamente "a chave é composta", que é o caminho de `getIdempotentNonIgnorableWrapper()`; `setJdempotentId()` tem outro propósito (gravar o valor gerado de volta no campo `@JdempotentId`) e não foi citado no AC — não estender o escopo sem confirmação. **Não confirmado**: nem o epics.md nem o dono do requisito confirmaram extensão de escopo, então `setJdempotentId()` foi deixado como está (sem herança), conforme instruído.

## Dev Notes

- **Confirmado por leitura direta**: `IdempotentAspect.java` usa `arg.getClass().getDeclaredFields()` em dois pontos (linha 281, dentro de `setJdempotentId()`, e linha 296, dentro de `getIdempotentNonIgnorableWrapper()`). O AC desta story cobre explicitamente a composição da chave (linha 296) — o outro uso (linha 281) é uma dúvida em aberto documentada na Task 2, não assumida como dentro do escopo.
- A cadeia de responsabilidade (`AnnotationChain`) já processa qualquer `Field` que receber — o bug não está na cadeia, está na coleta de campos que alimenta a cadeia. Corrigir na origem (coleta), não na cadeia.
- **Ponytail**: não introduzir cache de reflection (ex.: `Map<Class<?>, List<Field>>`) nesta story — não foi pedido no AC e adiciona estado mutável estático sem necessidade comprovada; se performance de reflection repetida virar problema medido, isso é uma otimização a discutir depois, não uma antecipação aqui.

### Project Structure Notes

- Arquivo modificado: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java`.

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L293-L310]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/chain/JdempotentDefaultChain.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-33-resolver-campos-anotados-em-toda-a-hierarquia-de-classes]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

### Completion Notes List

- `IdempotentAspect.getIdempotentNonIgnorableWrapper()`: substituído `arg.getClass().getDeclaredFields()` por um novo método privado `getAllFieldsInHierarchy(Class<?>)`, que sobe por `getSuperclass()` até `Object.class` (exclusive), concatenando `getDeclaredFields()` de cada nível. Deduplicação por nome via `Set<String>` preserva apenas o campo mais próximo da subclasse em caso de shadowing (ordem subclasse → superclasse).
- `setJdempotentId()` (linha 281) **não foi alterado** — a Task 2 condicionava essa extensão de escopo a confirmação externa (epics.md ou dono do requisito), que não ocorreu nesta execução; comportamento mantido como estava (sem herança), conforme a nota explícita da própria task.
- Nenhum cache de reflection foi introduzido (respeitando a nota Ponytail da story) — `getAllFieldsInHierarchy` recalcula a lista a cada chamada.
- Teste: adicionado `given_a_payload_with_field_inherited_from_superclass_when_find_idempotent_request_then_key_includes_inherited_field` em `IdempotentAspectUTTest.java`, com duas classes de teste aninhadas (`BasePayload` com `baseField`, `ChildPayload extends BasePayload` com `name`, ambas `@Data` do Lombok). O teste confirma que `baseField` (herdado, sem anotação, resolvido pela `JdempotentDefaultChain`) aparece na `IdempotentIgnorableWrapper` junto com o campo próprio `name`.
- **Observação**: ao iniciar esta story, `IdempotentAspect.java` já estava com a Task 1 implementada como alteração não commitada no working tree (não fazia parte do commit `8ef6f53` referenciado como baseline). O código encontrado já correspondia exatamente ao que a Task 1 pedia (mesmo método `getAllFieldsInHierarchy`, mesma dedução por nome, mesmo Javadoc). Esta execução verificou essa implementação linha a linha contra o AC/Tasks, confirmou que estava correta, e então completou o que faltava (Task 2 — teste).
- **Patches pós-review** (achados `patch` do Blind Hunter, Edge Case Hunter e Verification Gap, aplicados após a implementação inicial):
  1. `getAllFieldsInHierarchy`: campos `static` (ex.: `serialVersionUID`) agora são pulados via `Modifier.isStatic(field.getModifiers())` — antes eram coletados e entravam indevidamente na composição da chave, comportamento novo introduzido pela travessia de hierarquia e ausente na versão anterior (que só olhava a classe concreta).
  2. `getIdempotentNonIgnorableWrapper()`: o `declaredField.setAccessible(true)` agora está dentro de um `try/catch (InaccessibleObjectException e)` que pula o campo problemático (`continue`) e loga em debug, em vez de propagar a exceção — mitiga o risco de `InaccessibleObjectException` em runtime ao subir a hierarquia até ancestrais de módulos da JDK (ex.: `Enum`, `Throwable`), risco que não existia antes porque só a classe concreta do argumento era lida.
  3. Javadoc de `getAllFieldsInHierarchy`: removida a promessa de "fields in subclass-to-superclass order" — o retorno é inserido num `HashMap` (`IdempotentIgnorableWrapper.nonIgnoredFields`) que não preserva ordem, então a garantia documentada não tinha efeito observável e induzia a erro. Mantida/reescrita a explicação sobre dedup por shadowing (correta e relevante) e adicionada uma nota explícita sobre a não-garantia de ordem.
  4. `IdempotentAspectUTTest.java`: adicionado `given_a_payload_with_field_name_shadowed_from_superclass_when_find_idempotent_request_then_key_uses_subclass_value`, com `ShadowingBasePayload`/`ShadowingChildPayload` (ambas com campo `name`, mesmo nome). O valor da superclasse é setado via reflection direta no campo herdado (evita conflito de override entre setters gerados pelo Lombok); o valor do subclasse via o setter público gerado pelo Lombok. Asserção confirma que só o valor da subclasse (`"childValue"`) aparece na chave composta, provando o comportamento de shadowing documentado no Javadoc.
- Verificação final: `mvn -pl jdempotent -am test -Dtest=IdempotentAspectUTTest` → 9 testes, 0 falhas, 0 erros. `mvn -pl jdempotent -am test` (suíte completa) → 47 testes, 0 falhas, 3 erros — os 3 erros são em `PrimeNumbersJdempotentEnableTest`/`PrimeNumbersJdempotentDisableTest` (Testcontainers/Docker Compose, porta 6379 já em uso no ambiente local), pré-existentes e não relacionados a esta story.

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modificado — Task 1 já estava alterada no working tree ao iniciar, verificada como correta; patches pós-review aplicados: skip de campos `static`, guard contra `InaccessibleObjectException`, Javadoc de ordem corrigido)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java` (modificado — novo teste de hierarquia + classes de teste aninhadas; patch pós-review: novo teste de shadowing de nome)

## Suggested Review Order

**Coleta de campos na hierarquia**

- Ponto de entrada: novo método que sobe `getSuperclass()` até `Object.class` coletando campos de cada nível.
  [`IdempotentAspect.java:331`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L331)

- Campos `static` (ex.: `serialVersionUID`) são pulados para não poluir a chave com valores constantes.
  [`IdempotentAspect.java:336`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L336)

- Ponto de uso: o loop de composição da chave passou a chamar `getAllFieldsInHierarchy` em vez de `getDeclaredFields()`.
  [`IdempotentAspect.java:303`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L303)

**Guarda contra falha de acesso a campos da JDK**

- `setAccessible(true)` agora tolera `InaccessibleObjectException` ao alcançar ancestrais internos da JDK (ex.: `Enum`, `Throwable`), pulando o campo em vez de propagar.
  [`IdempotentAspect.java:304`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L304)

**Testes**

- Prova que um campo herdado sem anotação (via `JdempotentDefaultChain`) entra na chave composta.
  [`IdempotentAspectUTTest.java:257`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java#L257)

- Prova o shadowing: campo de mesmo nome em super/subclasse — só o valor da subclasse deve prevalecer.
  [`IdempotentAspectUTTest.java:281`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java#L281)

- Fixtures de teste: `BasePayload`/`ChildPayload` (herança simples) e `ShadowingBasePayload`/`ShadowingChildPayload` (mesmo nome de campo).
  [`IdempotentAspectUTTest.java:306`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectUTTest.java#L306)
