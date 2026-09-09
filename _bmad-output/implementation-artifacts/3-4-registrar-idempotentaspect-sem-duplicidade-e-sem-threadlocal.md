# Story 3.4: Registrar `IdempotentAspect` sem duplicidade e sem `ThreadLocal`

Status: done

<!-- baseline_commit: 359836ebec064f3642391dc5450c0b1e8b7003b7 -->
<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero que o aspecto não duplique bean quando há mais de um ponto de registro, e não use `ThreadLocal` para `MessageDigest`,
Para evitar NPE latente sob carga com virtual threads.

## Acceptance Criteria

1. **Given** mais de um ponto de registro do aspecto no contexto Spring, **When** `IdempotentAspect` é registrado com `@ConditionalOnMissingBean`, **Then** apenas um bean existe.
2. **And** o uso de `ThreadLocal` para `MessageDigest` é removido.
3. **And** um teste cobre o cenário de "duplo `IdempotentAspect`".

## Tasks / Subtasks

- [x] Task 1: Corrigir a duplicidade de bean em `ScosJdempotentConfig` (AC: #1)
  - [x] **Bug real confirmado**: `ScosJdempotentConfig.java` declara dois métodos `@Bean` que retornam `IdempotentAspect` — `getIdempotentAspectOnErrorConditionalCallback()` (linha 46, `@ConditionalOnBean(ErrorConditionalCallback.class)`) e `getIdempotentAspect()` (linha 51, sem nenhuma condicional). Quando a aplicação consumidora registra um bean `ErrorConditionalCallback`, **ambos** os métodos são elegíveis e o Spring cria dois beans `IdempotentAspect` no contexto — nenhum dos dois tem `@ConditionalOnMissingBean`
  - [x] Adicionar `@ConditionalOnMissingBean(IdempotentAspect.class)` a `getIdempotentAspect()` (o bean "default", sem callback de erro), garantindo que ele só é criado se o bean com callback não tiver sido criado primeiro
  - [x] Confirmar a ordem de avaliação das condições do Spring (`@ConditionalOnBean` de um método é avaliado antes do `@ConditionalOnMissingBean` do outro na mesma fase de configuração) — se a ordem de declaração dos métodos na classe importar para o resultado, documentar isso explicitamente nas Completion Notes
- [x] Task 2: Remover o `ThreadLocal<MessageDigest>` (AC: #2)
  - [x] Em `IdempotentAspect.java`, linhas 89-107, o `ThreadLocal<MessageDigest>` existe para evitar recriar o `MessageDigest` (que não é thread-safe) a cada chamada — mas retenção de estado por thread é um padrão problemático sob **virtual threads** (Java 25/Spring Boot 4.1, conforme ADD-6): cada requisição pode rodar numa virtual thread nova, então o `ThreadLocal` deixa de ter benefício de reuso e ainda mantém referências que podem crescer sem bound conforme threads são criadas e descartadas
  - [x] Substituir por instanciação direta de `MessageDigest.getInstance(CryptographyAlgorithm.SHA256.value())` a cada chamada de `execute()` (custo de criação de `MessageDigest` é baixo comparado ao I/O de Redis já presente no fluxo) — **não** introduzir um pool de `MessageDigest` nem outro mecanismo de cache: seria abstração não pedida pelo AC, que só pede a remoção do `ThreadLocal`
  - [x] O `ThreadLocal<StringBuilder> stringBuilders` (linhas 73-86) **não está no escopo desta story** — o AC #2 cita especificamente `MessageDigest`; não remover o `StringBuilder` sem confirmação, para não misturar duas mudanças de comportamento não relacionadas no mesmo commit (NFR2)
- [x] Task 3: Teste de duplo `IdempotentAspect` (AC: #3)
  - [x] Escrever um teste de contexto Spring que registra um bean `ErrorConditionalCallback` e carrega `ScosJdempotentConfig`, então confirma via `applicationContext.getBeansOfType(IdempotentAspect.class)` que **exatamente um** bean existe
  - [x] Este teste deve **falhar contra o código atual** (hoje produz dois beans) e passar após a correção — reproduz o disaster antes do fix, no espírito do NFR5 mesmo não sendo formalmente exigido por este epic

## Dev Notes

- Ambos os bugs (duplicidade de bean e uso de `ThreadLocal`) são **confirmados por leitura direta** do código-fonte, não hipotéticos: `ScosJdempotentConfig.java` (linhas 40-53) e `IdempotentAspect.java` (linhas 89-107).
- `@ConditionalOnMissingBean(IdempotentAspect.class)` é o mecanismo padrão do Spring Boot para este exato problema — não é necessário nenhum código customizado de deduplicação.
- **NFR2**: as duas correções (duplicidade de bean, remoção de `ThreadLocal`) são comportamentos distintos — considerar 2 commits separados se a granularidade do time exigir rastreabilidade fina, mas ambos cabem nesta única story porque os dois ACs (#1 e #2) pertencem ao mesmo FR29.

### Project Structure Notes

- Arquivos modificados: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfig.java`, `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java`.

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfig.java]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L89-L107]
- [Source: _bmad-output/planning-artifacts/epics.md#story-34-registrar-idempotentaspect-sem-duplicidade-e-sem-threadlocal]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

### Completion Notes List

- Adicionado `@ConditionalOnMissingBean(IdempotentAspect.class)` a `getIdempotentAspect()`. A ordem de declaração dos métodos importa para o resultado: `getIdempotentAspectOnErrorConditionalCallback()` (com `@ConditionalOnBean(ErrorConditionalCallback.class)`) está declarado **antes** de `getIdempotentAspect()` (com `@ConditionalOnMissingBean`) na classe. Spring processa métodos `@Bean` de uma mesma classe `@Configuration`/`@AutoConfiguration` na ordem de declaração no source (via leitura ASM, não reflection), então quando `ErrorConditionalCallback` está presente: o primeiro método já registra o bean `IdempotentAspect` antes do segundo método ser avaliado, e a condição `@ConditionalOnMissingBean` do segundo já encontra esse bean e não cria o duplicado. Se a ordem fosse invertida, `@ConditionalOnMissingBean` seria avaliado primeiro (sem nenhum `IdempotentAspect` ainda no contexto) e criaria o bean default de qualquer forma, resultando de novo em dois beans. Não foi necessário inverter nada porque a ordem já estava correta no código existente — apenas confirmado e documentado aqui.
- Removido `ThreadLocal<MessageDigest> messageDigests` de `IdempotentAspect.java`. `execute()` agora chama `MessageDigest.getInstance(CryptographyAlgorithm.SHA256.value())` diretamente a cada invocação; o `NoSuchAlgorithmException` (praticamente inalcançável, já que SHA-256 é obrigatório em toda JVM padrão) agora propaga como `IllegalStateException` em vez de ser engolido com um log e retornar `null` (que era a causa raiz do NPE em `messageDigest.reset()` do `ThreadLocal` antigo). Mensagem da exceção inclui o nome do algoritmo (`"Algorithm not supported: " + CryptographyAlgorithm.SHA256.value()`) para facilitar diagnóstico em produção caso esse caminho seja atingido (ajuste pós-revisão da story).
- `ThreadLocal<StringBuilder> stringBuilders` mantido sem alteração, conforme escopo da story.
- Teste `ScosJdempotentConfigTest.naoDuplicaIdempotentAspectQuandoErrorConditionalCallbackEstaRegistrado` criado em `jdempotent/src/test/java/.../redis/configuration/ScosJdempotentConfigTest.java`. Confirmado manualmente (via `git stash` do fix) que o teste falha contra o código antigo (2 beans) e passa após a correção (1 bean).
- Suite completa do módulo `jdempotent` executada (`mvn -pl jdempotent -am test`): 45/48 testes passam; as 3 falhas restantes (`PrimeNumbersJdempotentEnableTest`/`PrimeNumbersJdempotentDisableTest`) são de Testcontainers/Docker Compose indisponível no ambiente sandbox, não relacionadas a esta mudança.

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfig.java` (modificado)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modificado)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfigTest.java` (novo)

## Suggested Review Order

**Duplicidade de bean (AC #1)**

- Guarda que impede o segundo bean quando o de callback já foi registrado antes.
  [`ScosJdempotentConfig.java:52`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfig.java#L52)

**Remoção do `ThreadLocal<MessageDigest>` (AC #2)**

- `MessageDigest` instanciado direto por chamada; falha de algoritmo agora propaga em vez de virar NPE silenciosa.
  [`IdempotentAspect.java:151`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L151)

**Cobertura de teste (AC #3)**

- Contexto Spring real com `ErrorConditionalCallback` registrado, prova que só um `IdempotentAspect` existe.
  [`ScosJdempotentConfigTest.java:39`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfigTest.java#L39)
