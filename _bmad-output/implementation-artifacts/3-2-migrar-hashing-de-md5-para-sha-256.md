# Story 3.2: Migrar hashing de MD5 para SHA-256

Status: done

<!-- baseline_commit: 10598982470e4a33a18f902387597f4095e5cb54 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero hashing criptograficamente mais forte,
Para reduzir risco de colisão de hex.

## Acceptance Criteria

1. **Given** o hashing atual via MD5 e `Integer.toHexString`, **When** a migração é concluída, **Then** o hashing usa SHA-256 via enum `CryptographyAlgorithm` e a formatação hex usa `HexFormat.of().formatHex()`.
2. **And** um teste de colisão de hex (payloads escolhidos para produzir hashes diferentes) cobre a nova implementação.

## Tasks / Subtasks

- [x] Task 1: Trocar o algoritmo de hash em `IdempotentAspect` (AC: #1)
  - [x] Em `IdempotentAspect.java`, o `ThreadLocal<MessageDigest>` (linhas 89-107) hoje chama `MessageDigest.getInstance(CryptographyAlgorithm.MD5.value())` — trocar para `CryptographyAlgorithm.SHA256.value()`
  - [x] O enum `CryptographyAlgorithm` (em `jdempotent/core/constant/CryptographyAlgorithm.java`) **já contém** o valor `SHA256("SHA-256")` — não é necessário criar o enum, só usar o valor que já existe
- [x] Task 2: Trocar a formatação hex em `DefaultKeyGenerator` (AC: #1)
  - [x] Em `DefaultKeyGenerator.generateIdempotentKey()` (linha 60-62), o loop `for (byte b : digest) { builder.append(Integer.toHexString(0xFF & b)); }` produz hex **sem zero-padding** (ex.: byte `0x0F` vira `"f"`, não `"0f"` — risco real de colisão textual entre bytes diferentes que gera exatamente a ambiguidade que a Story pretende eliminar)
  - [x] Substituir por `HexFormat.of().formatHex(digest)`, que já produz a string hex completa com zero-padding em uma chamada — elimina o loop manual inteiro
- [x] Task 3: Achado — propriedade morta relacionada a este hashing (AC: #1, não bloqueante para esta story)
  - [x] `ConfigUtility.java` (`jdempotent/core/config/ConfigUtility.java`) declara `@Value("${scos.jdempotent.cryptography.algorithm:md5}") private String algorithm;` — esse campo **não tem getter e não é lido em nenhum lugar do código** (`DefaultKeyGenerator` ignora essa propriedade e usa o algoritmo hardcoded via `CryptographyAlgorithm`). Não resolvido aqui — documentado como candidato a "propriedade morta" para a Story 3.14 (`@ConfigurationProperties`), que trata explicitamente da remoção de propriedades mortas. Nenhuma alteração de código feita neste arquivo.
- [x] Task 4: Teste de colisão de hex (AC: #2)
  - [x] Escrever teste com dois payloads que, sob a formatação antiga (`Integer.toHexString` sem padding), produziriam prefixos de hex ambíguos, e confirmar que a nova formatação (`HexFormat`) produz hashes SHA-256 completos e distintos

## Dev Notes

- **Confirmado por leitura direta**: `IdempotentAspect.java` linha 94 usa `CryptographyAlgorithm.MD5.value()`; `DefaultKeyGenerator.java` linha 61 usa `Integer.toHexString(0xFF & b)` sem `String.format("%02x", ...)` nem equivalente — o padding realmente falta.
- O enum `CryptographyAlgorithm` já é mais rico do que o epics.md sugere: além de `MD5`/`SHA256`, também tem `SHA1`. Não introduzir seleção dinâmica de algoritmo nesta story (isso seria escopo especulativo não pedido) — trocar direto para `SHA256` hardcoded, mantendo o mesmo padrão de uso atual (um único algoritmo fixo no código).
- O `ThreadLocal<MessageDigest>` em si (uso de `ThreadLocal` para armazenar o `MessageDigest`) é tratado pela Story 3.4 (FR29), não por esta — não remover o `ThreadLocal` aqui, só trocar o algoritmo dentro dele.
- **NFR4**: esta story não altera a assinatura de `generateIdempotentKey` nem introduz configuração nova — troca mecânica de algoritmo e formatação.

### Project Structure Notes

- Arquivos modificados: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java`, `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGenerator.java`.
- Nenhum arquivo novo é criado (o enum `CryptographyAlgorithm` já existe com o valor necessário).

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L89-L107]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGenerator.java#L46-L65]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/constant/CryptographyAlgorithm.java]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/config/ConfigUtility.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-32-migrar-hashing-de-md5-para-sha-256]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5

### Debug Log References

### Completion Notes List

- `IdempotentAspect.java`: `MessageDigest.getInstance(CryptographyAlgorithm.MD5.value())` → `CryptographyAlgorithm.SHA256.value()` (única linha alterada, `ThreadLocal` mantido intacto).
- `DefaultKeyGenerator.java`: loop manual `for (byte b : digest) { builder.append(Integer.toHexString(0xFF & b)); }` substituído por `builder.append(HexFormat.of().formatHex(digest))`; import `java.util.HexFormat` adicionado.
- Task 3 (propriedade morta em `ConfigUtility.java`) documentada como não-bloqueante; nenhum código alterado nesse arquivo, conforme instruído — fica candidata para a Story 3.14.
- Task 4: criado `DefaultKeyGeneratorTest.java` (novo arquivo, pacote `core.generator`, antes sem cobertura própria) com dois testes:
  - `should_produce_distinct_hex_for_digests_that_collide_under_unpadded_formatting`: usa `MessageDigest` mockado (Mockito) para forçar os bytes `{0x01,0x23}` e `{0x12,0x03}`, que colidem sob a formatação antiga (`"123"` para ambos) e produzem hex distintos e corretos (`"0123"` / `"1203"`) com `HexFormat`.
  - `should_produce_full_length_sha256_hex_for_distinct_payloads`: usa `MessageDigest` real (SHA-256) com dois payloads diferentes, confirma chaves distintas e comprimento total de 64 hex chars.
- Efeito colateral necessário (não listado nas tasks, mas decorrência direta da Task 1): `IdempotentAspectITTest.java` e `IdempotentAspectWithErrorCallbackITTest.java` recalculavam a `IdempotencyKey` esperada chamando `MessageDigest.getInstance(CryptographyAlgorithm.MD5.value())` diretamente, fora do aspecto. Com o aspecto agora usando SHA-256, essas chamadas passaram a gerar uma chave diferente da produzida pelo aspecto, quebrando 5 testes (`assertTrue(idempotentRepository.contains(...))` falhando). Troquei `CryptographyAlgorithm.MD5` por `CryptographyAlgorithm.SHA256` nesses dois arquivos de teste (todas as ocorrências) para manter a asserção coerente com o comportamento real do aspecto — sem isso a suíte não compila/passa após a Task 1.
- Verificação: `mvn -pl jdempotent test` (suíte completa). Resultado: 45 testes, 0 falhas, 3 erros — os 3 erros são em `PrimeNumbersJdempotentEnableTest`/`PrimeNumbersJdempotentDisableTest` (Testcontainers/Docker Compose, porta 6379 já em uso no ambiente local), não relacionados a esta story. Todos os testes relevantes (`IdempotentAspectITTest`, `IdempotentAspectWithErrorCallbackITTest`, `IdempotentAspectUTTest`, `DefaultKeyGeneratorTest`) passaram: 0 falhas, 0 erros.
- **Patches pós-review** (achados `patch` do Blind Hunter e do Edge Case Hunter, aplicados após a implementação):
  - `DefaultKeyGeneratorTest.java`: as duas asserções que comparavam a chave inteira por igualdade exata (`"listener-0123"`, `"listener-1203"`, comprimento `9 + 64`) não levavam em conta que `DefaultKeyGenerator` lê `System.getenv(EnvironmentVariableUtils.APP_NAME)` no construtor e prefixa a chave com `"{appName}-"` quando essa env var está definida — em um ambiente com `APP_NAME` setado (ex.: CI), os testes quebrariam por causa do ambiente, não por regressão. Trocado para `assertTrue(...endsWith(...))` e verificação de comprimento mínimo (`>=`) em vez de igualdade exata.
  - `README.md` (linha ~516): a linha `Algoritmos de hash: MD5, SHA-1, SHA-256` documentava os 3 algoritmos como opção configurável; corrigida para `Hashing de chave: SHA-256 (fixo, via HexFormat)`, refletindo que esta story removeu o último uso de MD5 e não há seleção dinâmica de algoritmo.
  - Reverificado após os patches: `mvn -pl jdempotent test -Dtest=DefaultKeyGeneratorTest,IdempotentAspectITTest,IdempotentAspectWithErrorCallbackITTest,IdempotentAspectUTTest` → 20 testes, 0 falhas, 0 erros.

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modificado)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGenerator.java` (modificado)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGeneratorTest.java` (novo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectITTest.java` (modificado — ajuste de asserção, ver Completion Notes)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/callback/IdempotentAspectWithErrorCallbackITTest.java` (modificado — ajuste de asserção, ver Completion Notes)
- `README.md` (modificado — patch pós-review, ver Completion Notes)

## Suggested Review Order

**Migração do algoritmo de hash**

- Ponto de entrada: troca de MD5 para SHA-256 no `ThreadLocal<MessageDigest>` do aspecto.
  [`IdempotentAspect.java:94`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L94)

**Correção do bug de padding hex**

- `HexFormat.formatHex` substitui o loop manual que perdia o zero à esquerda e causava colisão textual entre bytes distintos.
  [`DefaultKeyGenerator.java:61`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGenerator.java#L61)

**Testes**

- Teste de colisão de hex (AC #2): bytes que colidiam sob o formato antigo agora geram chaves distintas.
  [`DefaultKeyGeneratorTest.java:43`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGeneratorTest.java#L43)

- Teste com SHA-256 real confirmando chaves de 64 hex chars para payloads distintos.
  [`DefaultKeyGeneratorTest.java:70`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGeneratorTest.java#L70)

- Asserções tolerantes ao prefixo opcional de `APP_NAME` (patch pós-review, evita flakiness em CI).
  [`DefaultKeyGeneratorTest.java:65`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGeneratorTest.java#L65)

- Chave esperada recalculada com SHA-256 nos testes de integração do aspecto (efeito colateral necessário da Task 1).
  [`IdempotentAspectITTest.java:89`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectITTest.java#L89)

- Mesmo ajuste de chave esperada no cenário de callback de erro.
  [`IdempotentAspectWithErrorCallbackITTest.java:70`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/callback/IdempotentAspectWithErrorCallbackITTest.java#L70)

**Documentação**

- README atualizado para não anunciar mais MD5/SHA-1 como algoritmos configuráveis (patch pós-review).
  [`README.md:516`](../../README.md#L516)
