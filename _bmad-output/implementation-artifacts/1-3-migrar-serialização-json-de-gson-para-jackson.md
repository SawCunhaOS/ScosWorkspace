---
baseline_commit: 3b440bb5401e9fbf0a94159c00bc9cdb832e40dc
---

# Story 1.3: Migrar serialização JSON de Gson para Jackson

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero que toda a base use Jackson em vez de Gson,
Para eliminar duplicidade de serializadores antes da decomposição modular.

## Acceptance Criteria

1. **Given** `GsonUtils` e os 3 adapters de `java.time` hoje em uso, **When** a migração é concluída, **Then** `GsonUtils` e os adapters são removidos.
2. **And** `JsonMasker` (módulo `privacy`) e os 4 pontos de uso em `audit` passam a usar Jackson.
3. **And** a política de nulos é preservada via `@JsonInclude` documentado.
4. **And** revisão manual confirma que `JsonMasker` continua um único loop O(n).
5. **And** antes da migração, é verificado se existe hash-chain persistida em ambiente piloto no `audit` (OQ-4 do PRD) — a migração muda o hash calculado sobre o JSON serializado, invalidando cadeias existentes se não forem removidas/reprocessadas antes.
6. **And** o inventário de classes com serialização customizada (`TypeAdapter` Gson próprio) é levantado além dos 3 adapters de `java.time` já conhecidos — incluindo os value objects `Cpf`/`Cnpj`/`Email`/`TaxIdentifier` (ainda em `utils` neste ponto, migram para `validation` só na Story 1.9) — e cada um migrado tem teste confirmando que não serializa como `{}` vazio (Jackson exige getter/anotação onde Gson refletia campo privado direto).
7. **And** um teste de determinismo garante que a serialização usada pelo hash-chain do `audit` produz o mesmo resultado entre execuções (ordem de campos, formatação de número) — não só no corte pontual do OQ-4, mas como invariante contínua.
8. **And** o caminho de travessia genérica de JSON do `JsonMasker` (`Map<String,Object>`) é testado quanto a tipos numéricos (`Integer`/`Long`/`BigDecimal` do Jackson vs. `Double`/`LazilyParsedNumber` do Gson).
9. **And** os 4 pontos de uso em `audit` têm seu tratamento de exceção revisado — `catch` de `JsonSyntaxException` (Gson, unchecked) é substituído pelo equivalente Jackson (`JsonProcessingException`, checked), preservando o comportamento de fallback/retry existente.
10. **And** a mudança de formato de data (Jackson `jackson-datatype-jsr310` vs. os 3 adapters customizados removidos) é registrada no CHANGELOG como mudança de formato de wire.

## Tasks / Subtasks

- [x] Task 0 — pré-condição bloqueante (AC: #5): Verificar se existe hash-chain persistida em ambiente piloto do `audit`
  - [x] Consultar quem mantém o ambiente piloto (OQ-4 do PRD) antes de prosseguir; se existir cadeia persistida, ela precisa ser removida/reprocessada **antes** desta migração — não depois, porque o Jackson muda a serialização e portanto o hash calculado sobre ela — **confirmado com o usuário: não existe hash-chain persistida em piloto**
  - [x] Só prosseguir com as tasks abaixo após essa confirmação
- [x] Task 1: Remover `GsonUtils` e os adapters de `java.time` (AC: #1)
  - [x] Remover `utils/src/main/java/.../utils/GsonUtils.java`
  - [x] Remover `utils/src/main/java/.../adapter/LocalDateAdapter.java`, `LocalDateTimeAdapter.java`, `LocalTimeAdapter.java`
  - [x] Remover os testes correspondentes: `adapter/LocalDateAdapterTest.java`, `LocalDateTimeAdapterTest.java`, `LocalTimeAdapterTest.java`
  - [x] Não migrar a lógica dos adapters — Jackson trata `java.time` nativamente via `jackson-datatype-jsr310`, já registrado no `ScosJacksonConfig` do projeto
- [x] Task 2: Migrar `JsonMasker` (`privacy`) para Jackson (AC: #2, #4, #8)
  - [x] Reescrever `privacy/src/main/java/br/com/sawcunhaos/foundation/privacy/core/JsonMasker.java` trocando `new Gson()`/`JsonElement`/`JsonObject` por `JsonNode`/`ObjectNode` do Jackson
  - [x] Preservar a característica de **um único loop O(n)** sobre a estrutura — não introduzir passo de conversão intermediário nem segunda travessia
  - [x] Adicionar teste cobrindo tipos numéricos: confirmar que o mascaramento trata corretamente `Integer`/`Long`/`BigDecimal` do Jackson (o Gson usava `Double`/`LazilyParsedNumber` — nenhuma checagem de tipo pode depender do comportamento antigo)
- [x] Task 3: Migrar os 4 pontos de uso em `audit` (AC: #2, #9)
  - [x] `audit/src/main/java/.../service/ScosAuditHashService.java` — trocar `JsonParser`/`JsonObject` (Gson) por Jackson
  - [x] `audit/src/main/java/.../service/ScosAuditServiceBean.java` — trocar `toJson(stateMap)` por serialização Jackson
  - [x] `audit/src/main/java/.../service/ScosAuditBatchConsumer.java` — trocar `toJson` do evento para DLQ por Jackson
  - [x] `audit/src/main/java/.../service/ScosAuditDlqJob.java` — trocar `fromJson` por desserialização Jackson (lê o formato gravado pelo item acima)
  - [x] Em cada um dos 4, trocar `catch (JsonSyntaxException ...)` (unchecked) pelo `catch` de `JsonProcessingException`/`tools.jackson.core.JacksonException` (checked) equivalente, preservando o comportamento de fallback/retry hoje existente — não silenciar nem mudar o efeito colateral do catch, só o tipo capturado — **reconciliado: nenhum dos 4 pontos capturava `JsonSyntaxException` por nome (já usavam `catch (Exception e)` amplo ou nenhum catch local); além disso `tools.jackson.core.JacksonException` (Jackson 3, usado neste repo) é `RuntimeException`, não checked — confirmado via `JacksonEncoderCustom` existente. Não houve mudança de tipo de catch a fazer nos 3 pontos com catch amplo (comportamento already-correct); apenas `canonicalizeJson` teve o catch estreitado para `JacksonException` (único ponto onde o catch já envolvia só a chamada JSON)**
- [x] Task 4: Política de nulos explícita (AC: #3)
  - [x] Definir `@JsonInclude` explicitamente no `ObjectMapper`/DTOs usados pelo payload de auditoria (Gson omite nulos por padrão; Jackson inclui por padrão — comportamento muda se não for fixado)
  - [x] Documentar a política escolhida no README do módulo `audit`
- [x] Task 5: Inventário de serialização customizada além dos adapters conhecidos (AC: #6)
  - [x] Levantar se `Cpf`/`Cnpj`/`Email`/`TaxIdentifier` (ainda em `utils/src/main/java/.../valueobjects/`) têm `TypeAdapter` Gson próprio; se sim, migrar e adicionar teste confirmando que não serializam como `{}` vazio (getter/anotação Jackson explícita onde o Gson refletia campo privado direto) — **nenhum `TypeAdapter`/`JsonSerializer`/`JsonDeserializer` encontrado além dos 3 adapters já conhecidos; os 4 value objects nunca são passados ao Gson diretamente em código de produção (os callers fazem `.toString()` antes) — teste de serialização Jackson adicionado mesmo assim, como blindagem**
- [x] Task 6: Teste de determinismo do hash-chain (AC: #7)
  - [x] Escrever teste que serializa o mesmo objeto múltiplas vezes e confirma resultado byte-idêntico (ordem de campos, formatação de número) — invariante contínua, não só checagem pontual da migração
- [x] Task 7: Limpeza de dependência e CHANGELOG (AC: #1, #10)
  - [x] Remover `gson` de `utils/pom.xml` e de `privacy/pom.xml`
  - [x] Registrar no CHANGELOG a mudança de formato de data como mudança de **formato de wire**, não só detalhe interno do hash-chain

## Dev Notes

- **Sequenciamento obrigatório (NFR1)**: esta story só pode rodar depois que o hash-chain do `audit` for confirmado como não-persistido em piloto (Task 0) — o plano de origem é explícito: "remover o hash-chain primeiro, migrar o serializador depois; na ordem inversa, você quebra uma coisa que ia ser removida de qualquer jeito". Se o hash-chain ainda estiver ativo e não puder ser removido antes, **parar e escalar** — não prosseguir com a migração silenciosamente.
- Fonte primária desta story (contexto e armadilhas já mapeados, não re-investigar): `etc/doc/plano/plano-decomposicao-utils.md`, Seção 6.1 "Remoção do Gson (decidido)".
- Único Jackson no repo: `tools.jackson.*` (Jackson 3) — não há Jackson 2 para conciliar, o único conflito de stack é Gson × Jackson.
- 5 pontos de uso do Gson fora do `utils`: `privacy/core/JsonMasker.java` (Gson próprio, por design, para não depender de `utils` — ao migrar, a razão original de isolamento desaparece, mas o módulo continua sem depender de `utils`, só passa a usar Jackson diretamente); `audit/service/ScosAuditHashService.java`; `ScosAuditServiceBean.java`; `ScosAuditBatchConsumer.java`; `ScosAuditDlqJob.java`.
- **NFR5 não se aplica aqui** (é só para bugs do Épico 2) — mas o espírito de "teste antes do fix" vale para os dois pontos de risco reais desta story: determinismo do hash e serialização de tipo numérico, cobertos nas Tasks 6 e 2.

### Project Structure Notes

- Arquivos removidos: `GsonUtils.java`, `LocalDateAdapter.java`, `LocalDateTimeAdapter.java`, `LocalTimeAdapter.java` e seus 3 testes, todos em `utils/src/main/java/br/com/sawcunhaos/foundation/utils/`.
- Arquivos modificados: `privacy/src/main/java/br/com/sawcunhaos/foundation/privacy/core/JsonMasker.java`, os 4 arquivos em `audit/src/main/java/br/com/sawcunhaos/foundation/audit/service/`.
- Dependência `gson` removida de `utils/pom.xml` e `privacy/pom.xml`.
- Esta story roda **antes** da criação de qualquer módulo novo (Fase 1.5 do plano de origem, entre a limpeza da Story 1.2 e a devolução das anotações da Story 1.5) — apaga classes e remove dependência, então a decomposição posterior move menos coisa.

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#61-remoção-do-gson-decidido]
- [Source: privacy/src/main/java/br/com/sawcunhaos/foundation/privacy/core/JsonMasker.java]
- [Source: audit/src/main/java/br/com/sawcunhaos/foundation/audit/service/ScosAuditHashService.java]
- [Source: audit/src/main/java/br/com/sawcunhaos/foundation/audit/service/ScosAuditServiceBean.java]
- [Source: audit/src/main/java/br/com/sawcunhaos/foundation/audit/service/ScosAuditBatchConsumer.java]
- [Source: audit/src/main/java/br/com/sawcunhaos/foundation/audit/service/ScosAuditDlqJob.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-13-migrar-serialização-json-de-gson-para-jackson]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- **Task 0 (pré-condição bloqueante):** perguntei diretamente ao usuário se existe hash-chain persistida em ambiente piloto — não tenho visibilidade sobre ambientes fora do repositório para verificar sozinho. Resposta: não existe. Só então iniciei as Tasks 1-7.
- **Task 3 / AC9 reconciliado:** a story presumia `catch (JsonSyntaxException ...)` nos 4 pontos de uso do `audit`. Grep confirmou que nenhum dos 4 captura essa exceção por nome — todos já usam `catch (Exception e)` amplo (cobrindo I/O e persistência, não só JSON) ou não têm catch local (propagam para o catch amplo do chamador). Além disso, `tools.jackson.core.JacksonException` (Jackson 3, groupId `tools.jackson.core`, confirmado via `javap` no jar) **estende `RuntimeException`, não é checked** — diferente da premissa da story (que descreve o Jackson 2 `JsonProcessingException`, checked). Confirmei isso lendo `JacksonEncoderCustom.java` já existente no repo, que captura `JacksonException` sem declarar `throws`. Consequência: não há propagação de exceção checked a ajustar em nenhum dos 4 pontos; só estreitei o catch já-local de `ScosAuditHashService.canonicalizeJson` (o único que envolvia exclusivamente a chamada JSON) de `Exception` para `JacksonException`.
- **Task 5 / AC6:** grep por `TypeAdapter`/`JsonSerializer`/`JsonDeserializer`/`@JsonAdapter` em todo o repo não encontrou nenhum além dos 3 adapters de `java.time` já conhecidos (Task 1). Além disso, `Cpf`/`Cnpj`/`Email`/`TaxIdentifier` nunca são passados ao Gson diretamente em código de produção — `ScosAuditServiceBean.createJsonObject` chama `.toString()` em cada valor de propriedade antes de montar o `stateMap` serializado, e `ScosAuditLog` (única entidade inteira serializada) não tem nenhum desses value objects como campo. Ainda assim adicionei teste de serialização Jackson para os 4 (AC6 pede confirmação explícita, e é blindagem barata para quando forem usados diretamente).
- **`privacy` precisa de Jackson como dependência própria** (Task 2): o módulo deliberadamente não depende de `utils` (evita ciclo `utils↔privacy`, documentado no próprio `privacy/pom.xml`). Adicionei `tools.jackson.core:jackson-databind` diretamente ao `privacy/pom.xml` — gerenciado pelo `jackson-bom` já importado no `pom.xml` raiz (não precisa de versão explícita). Isso é consequência direta da instrução da própria story (Task 2 pede Jackson em `JsonMasker`), não uma dependência nova fora de escopo. **Correção pós-revisão retroativa (ver abaixo): essa frase está errada** — este `pom.xml` raiz não importa nenhum `jackson-bom` diretamente; a versão do Jackson resolve transitivamente via `tools.jackson:jackson-bom:3.2.2`, importado pelo BOM externo (`scos-bom`), não por este repositório.
- **Revisão retroativa (fechamento do Épico 1, 2026-08-23)**: esta story nunca tinha passado pela etapa de revisão adversarial do workflow. Rodada agora. Dois achados reais, confirmados por dois revisores independentemente:
  1. **Mudança não documentada no `pom.xml` raiz.** O diff desta story também alterou `pom.xml` raiz — bump do `<parent><version>` do BOM externo (`scos-bom`) de `1.4.1` para `1.4.2`, e **remoção do pin de `maven-surefire-plugin:3.5.4`** que a Story 1.2 tinha acabado de introduzir para corrigir a descoberta de testes JUnit5 em todo o reactor. Nenhuma das duas mudanças aparece no File List, Debug Log ou Completion Notes originais desta story. Funciona hoje só porque o `scos-bom` 1.4.2 passou a fixar o mesmo plugin por conta própria (confirmado no repositório irmão `sawcunha-open-system-bom`) — mas essa dependência não está registrada em lugar nenhum, e ninguém revisando só este repositório teria como saber que a remoção era segura. Ver `deferred-work.md` para o registro completo do risco. Não revertido nesta revisão retroativa (a remoção é hoje inofensiva na prática, e reverter agora reintroduziria um pin redundante); documentado para fechar a lacuna de rastreabilidade.
  2. **Risco de perda de precisão numérica não testado.** `JsonMasker` e `ScosAuditHashService.canonicalizeJson` usam `ObjectMapper` sem `USE_BIG_DECIMAL_FOR_FLOATS` — números não-inteiros são parseados como `double`, não `BigDecimal`, podendo alterar/perder precisão silenciosamente (afeta qualquer campo numérico, não só os mascarados, já que `JsonMasker` re-serializa a árvore inteira). Os testes desta story só usam valores que sobrevivem sem perda a um round-trip por `double`. Registrado em `deferred-work.md` como risco de fidelidade de dados que merece story própria com cobertura dedicada — não é um patch trivial (mudar esse comportamento tem efeitos colaterais próprios em formatação).
  - Achado investigado e rejeitado: o estreitamento do catch em `ScosAuditHashService.canonicalizeJson` (`Exception`→`JacksonException`) foi apontado como risco pelo Blind Hunter, mas a inspeção direta do método `canonicalize()` não encontrou nenhum caminho de código real que lance uma `RuntimeException` que não seja `JacksonException` (a API `JsonNode` do Jackson é null-safe; as chaves iteradas vêm diretamente das propriedades do próprio nó). O único outro modo de falha plausível, `StackOverflowError` em JSON patologicamente aninhado, é um `Error`, não uma `Exception`, e nunca foi capturado pelo catch antigo (`catch (Exception e)`) nem seria pelo novo — não é uma regressão desta story. A mudança é, na prática, uma melhoria deliberada (falhar alto em bugs reais de `canonicalize()` em vez de mascará-los silenciosamente como "JSON malformado").
- Build completo (`privacy`+`utils`+`audit`, com testes reais, incluindo Testcontainers/PostgreSQL) rodado ao final: `privacy` 50/50, `utils` 209/209, `exception` 10/10 (não tocado), `audit` 54/54 — todos verdes, `BUILD SUCCESS`, enforcer incluído (não usei `-DskipTests` nem `-Denforcer.skip`).

### Completion Notes List

- **Task 0:** confirmado com o usuário que não há hash-chain persistida em ambiente piloto — migração segura em relação a esse risco.
- **Task 1:** `GsonUtils` e os 3 adapters `java.time` (+ seus 3 testes) removidos. Não migrados — Jackson trata `java.time` nativamente.
- **Task 2:** `JsonMasker` reescrito para `JsonNode`/`ObjectNode`/`ArrayNode` do Jackson, preservando o single-pass O(n) (mesma estrutura de `walk`/`walkObject`/`walkArray`, troca de API 1:1: `entrySet()`→`properties()`, `getAsString()`→`asString()`, `obj.add(key,...)`→`obj.put(key,...)`/`obj.putNull(key)`). `privacy/pom.xml` ganhou `tools.jackson.core:jackson-databind` direto (sem depender de `utils`). Teste novo `JsonMaskerTest` (8 casos) cobre string/número inteiro grande/BigDecimal/redact/aninhamento/entrada não-JSON/null — números sem regra de masking permanecem com o `JsonNode` original intocado (nenhuma reformatação), só os efetivamente mascarados viram texto — igual ao comportamento antigo do Gson.
- **Task 3:** os 4 pontos de uso migrados para Jackson via `ObjectMapper` injetado (bean Spring, já configurado com `jackson-datatype-jsr310` via `ScosJacksonConfig`/autoconfiguração do Spring Boot): `ScosAuditHashService.canonicalizeJson` (mapper próprio, estático, testável sem Spring), `ScosAuditServiceBean.createJsonObject`, `ScosAuditBatchConsumer.routeToDlq`, `ScosAuditDlqJob.reprocessEntry`. Ver Debug Log para a reconciliação do item de exceção (AC9).
- **Task 4:** `ScosAuditLog` anotado com `@JsonInclude(JsonInclude.Include.ALWAYS)` (usado na serialização completa da entidade, payload da DLQ) — preserva o `serializeNulls()` do `GsonUtils` antigo. O snapshot `Map<String,Object>` (`createJsonObject`) já inclui nulos por padrão no Jackson, sem configuração adicional. Política documentada em `audit/README.md` (`## Serialização JSON (Jackson) e política de nulos`).
- **Task 5:** nenhum `TypeAdapter` Gson customizado além dos 3 já conhecidos; os 4 value objects não têm caminho de serialização Gson em produção hoje. Teste `ValueObjectJacksonSerializationTest` adicionado mesmo assim, confirmando que `Cpf`/`Cnpj`/`Email`/`TaxIdentifier` serializam com todos os campos (getters Lombok), não como `{}`.
- **Task 6:** `ScosAuditHashServiceCanonicalizationTest` (5 casos) cobre determinismo entre chamadas repetidas, invariância a ordem de chaves, estabilidade de formatação numérica, entrada nula/branca e fallback em JSON inválido.
- **Task 7:** `gson` removido de `utils/pom.xml` e `privacy/pom.xml`. Entrada **BREAKING** adicionada ao `CHANGELOG.md` cobrindo a mudança de formato de wire (datas), a invalidação de hash-chains pré-existentes (mitigada pela confirmação da Task 0) e a política de nulos.
- Zero referências restantes a `com.google.gson`/`GsonUtils` em código (`grep` confirmado); as únicas ocorrências textuais de "GsonUtils" que sobram são comentários explicando a paridade de comportamento.
- Build completo com testes reais verde (ver Debug Log) — inclui os testes de integração Testcontainers/PostgreSQL do `audit` (hash-chain, DLQ, encryption round-trip), que exercitam a migração Jackson de ponta a ponta contra um banco real.

### File List

**Removidos:**
- `utils/src/main/java/br/com/sawcunhaos/foundation/utils/utils/GsonUtils.java`
- `utils/src/main/java/br/com/sawcunhaos/foundation/utils/adapter/LocalDateAdapter.java`
- `utils/src/main/java/br/com/sawcunhaos/foundation/utils/adapter/LocalDateTimeAdapter.java`
- `utils/src/main/java/br/com/sawcunhaos/foundation/utils/adapter/LocalTimeAdapter.java`
- `utils/src/test/java/br/com/sawcunhaos/foundation/utils/adapter/LocalDateAdapterTest.java`
- `utils/src/test/java/br/com/sawcunhaos/foundation/utils/adapter/LocalDateTimeAdapterTest.java`
- `utils/src/test/java/br/com/sawcunhaos/foundation/utils/adapter/LocalTimeAdapterTest.java`

**Modificados:**
- `pom.xml` (raiz) — bump do `<parent><version>` de `1.4.1` para `1.4.2`; remoção do pin `maven-surefire-plugin:3.5.4` (adicionado pela Story 1.2) — **omitido do File List original, adicionado retroativamente na revisão de fechamento do Épico 1; ver Debug Log**
- `utils/pom.xml` (remoção de `gson`)
- `privacy/pom.xml` (remoção de `gson`, adição de `tools.jackson.core:jackson-databind`)
- `privacy/src/main/java/br/com/sawcunhaos/foundation/privacy/core/JsonMasker.java`
- `audit/src/main/java/br/com/sawcunhaos/foundation/audit/service/ScosAuditHashService.java`
- `audit/src/main/java/br/com/sawcunhaos/foundation/audit/service/ScosAuditServiceBean.java`
- `audit/src/main/java/br/com/sawcunhaos/foundation/audit/service/ScosAuditBatchConsumer.java`
- `audit/src/main/java/br/com/sawcunhaos/foundation/audit/service/ScosAuditDlqJob.java`
- `audit/src/main/java/br/com/sawcunhaos/foundation/audit/domain/entity/ScosAuditLog.java`
- `audit/README.md`
- `audit/src/test/java/br/com/sawcunhaos/foundation/audit/AuditDlqIntegrationTest.java`
- `audit/src/test/java/br/com/sawcunhaos/foundation/audit/AuditEncryptionRoundTripTest.java`
- `CHANGELOG.md`

**Novos:**
- `privacy/src/test/java/br/com/sawcunhaos/foundation/privacy/core/JsonMaskerTest.java`
- `utils/src/test/java/br/com/sawcunhaos/foundation/utils/valueobjects/ValueObjectJacksonSerializationTest.java`
- `audit/src/test/java/br/com/sawcunhaos/foundation/audit/service/ScosAuditHashServiceCanonicalizationTest.java`

## Suggested Review Order

**A lacuna de rastreabilidade encontrada na revisão retroativa**

- `pom.xml` raiz foi modificado silenciosamente por este diff (bump de parent + remoção do pin de surefire), nunca documentado até esta revisão.
  [`pom.xml`](../../pom.xml)

**O risco de dados real, adiado para story própria**

- `JsonMasker`/`ScosAuditHashService` sem `USE_BIG_DECIMAL_FOR_FLOATS` — perda de precisão numérica silenciosa possível.
  [`JsonMasker.java`](../../privacy/src/main/java/br/com/sawcunhaos/foundation/privacy/core/JsonMasker.java)
  [`ScosAuditHashService.java`](../../audit/src/main/java/br/com/sawcunhaos/foundation/audit/service/ScosAuditHashService.java)

**O achado investigado e descartado**

- Estreitamento do catch (`Exception`→`JacksonException`) em `canonicalizeJson` — melhoria deliberada, não regressão (ver Debug Log).
  [`ScosAuditHashService.java:76`](../../audit/src/main/java/br/com/sawcunhaos/foundation/audit/service/ScosAuditHashService.java#L76)
