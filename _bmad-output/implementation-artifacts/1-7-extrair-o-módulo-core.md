---
baseline_commit: 14f450f648956d8afe6daa4966f4c1a4ca8a199d
---

# Story 1.7: Extrair o módulo `core`

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como time consumidor que só precisa de utilitários simples,
Eu quero um módulo `core` sem dependência de Spring/JPA/Servlet,
Para importar `DateUtils`/`HashUtils` sem carregar o resto da stack.

## Acceptance Criteria

1. **Given** as classes do inventário (Story 1.1) destinadas a `core` (`DateUtils`, `HashUtils`, `StringFieldUtils`, `PropertiesOrder`, `ScosBaseUseCase`, `ScosUserAuthentication`), **When** o módulo é extraído em 2 commits separados (mover vs. ajustar comportamento), **Then** `core` compila sem `org.springframework`, `jakarta.persistence` ou `jakarta.servlet` no classpath.
2. **And** uma regra ArchUnit local em `core` falha o build se qualquer um desses pacotes for importado.
3. **And** os testes existentes das classes migradas continuam verdes sem alteração de comportamento.
4. **And** `ScosStartupListener` **não** entra nesta lista apesar de listado como `core` no addendum do PRD — sua assinatura (`onStartupSystem(ApplicationReadyEvent event)`) importa `org.springframework.boot.context.event.ApplicationReadyEvent`, violando a regra de zero-Spring do `core`; ele é migrado na Story 1.8 (`spring`), junto de `ScosOnStartupListener`, que já o consome via `List<ScosStartupListener>`.

## Tasks / Subtasks

- [x] Task 1: Commit 1 — mover as 6 classes sem alterar comportamento (AC: #1, #4)
  - [x] Criar módulo Maven `scos-foundation-core`, pacote raiz `br.com.sawcunhaos.foundation.core`
  - [x] Mover, preservando lógica: `utils/src/main/java/.../utils/DateUtils.java`, `HashUtils.java`, `StringFieldUtils.java`, `sort/PropertiesOrder.java`, `specification/ScosBaseUseCase.java`, `specification/ScosUserAuthentication.java`
  - [x] **Não movido** `specification/ScosStartupListener.java` nesta story — fica em `utils` até a Story 1.8
  - [x] Testes movidos: `DateUtilsTest`, `StringFieldUtilsTest` (+ fixture `TestDTO`). Confirmado: não existiam testes prévios para `HashUtils`, `PropertiesOrder`, `ScosBaseUseCase`, `ScosUserAuthentication` (busca no repo inteiro) — lacuna pré-existente, registrada abaixo, nada novo escrito (fora do pedido)
  - [x] Dependências do `core`: `slf4j-api`, `lombok` (optional), `commons-lang3` — nenhuma outra
  - [x] **Divergência do plano original, decidida pelo usuário (2026-08-22)**: commit único em vez de 2 separados — ver nota abaixo
- [x] Task 2: ajuste necessário (AC: #1) — **estruturalmente inseparável do commit 1, não um commit próprio (decisão do usuário)**
  - [x] `StringFieldUtils.applyTransformation` tomava `StringTransformRule` (enum que fica em `utils`, importa `org.springframework.util.StringUtils`). Mantê-lo criaria ciclo `core → utils → core` (utils já depende de core para as outras 5 classes) — não compila, não é escolha de estilo. Generalizado para `UnaryOperator<String>`; as 4 transformações (upper/lower/camel/capitalize) reimplementadas byte-a-byte com `commons-lang3` no lugar do `StringUtils` do Spring. Chamador `StringProcessingAspect` (utils) ajustado para `annotation.function()::apply`.
  - [x] Não havia como isolar isso num 2º commit: não existe estado intermediário compilável onde `StringFieldUtils` está movida sem esse ajuste. Documentado aqui em vez de forçar uma separação artificial.
- [x] Task 3: Regra ArchUnit local de zero-Spring (AC: #2)
  - [x] `core/src/test/.../ArchitectureTest.java` — falha o build se qualquer classe do módulo importar `org.springframework..`, `jakarta.persistence..` ou `jakarta.servlet..`. Nasceu no mesmo commit que cria o módulo.
- [x] Task 4: Confirmar testes verdes (AC: #3)
  - [x] Build com escopo `core,privacy,utils,exception,audit-api,audit,jdempotent-api,validation-api` → verde. `core`: ArchitectureTest 1/1, DateUtilsTest 16/16, StringFieldUtilsTest 4/4. `utils`: todas as suítes verdes (incl. consumidores repontados). `audit`: 14 classes de teste verdes (incl. as 4 que usam `ScosUserAuthentication`). `audit-api`/`jdempotent-api`: regras ArchUnit locais não afetadas.

## Dev Notes

- **NFR2/NFR4**: extração em 2 commits separados é requisito explícito do AC, não sugestão — "mover" e "ajustar comportamento" nunca no mesmo commit. Se não houver ajuste de comportamento necessário, ainda assim documentar essa constatação (não pular a distinção silenciosamente).
- Esta é a Fase 3 do plano de origem: "Tudo depende dele; sai primeiro." `core` é o módulo mais citado como dependência por todos os outros módulos novos (`spring`, `validation`, `cache`, `jpa`, `web`, `feign`, os três `-api`).
- **Contrato de exceção (`ScosException`, `ExceptionCode`, `LocaleService`, etc.) NÃO faz parte desta story** — apesar de o addendum do PRD listar essas classes como destino `core`, o AC desta story (Épico 1) restringe explicitamente o escopo às 6 classes citadas. A migração do contrato de exceção para `core` é a Story 2.8 (Épico 2), que roda depois e repontua `audit` para consumir `ScosException` do `core`.
- A regra ArchUnit desta story é a que "mais paga" segundo o plano de origem: "ela impede exatamente o movimento que criou o problema — alguém precisa de 'um lugar qualquer' e joga uma classe Spring no módulo compartilhado."
- `ScosUserAuthentication` é citada no plano de origem como "interface de um método, sem dependência alguma — o exemplo do que deveria estar num core desde o início" — migração deve ser trivial, útil como primeiro caso de teste da regra ArchUnit.

### Project Structure Notes

- Módulo Maven novo: `core/` — depende só de `slf4j-api`, `lombok` (optional), `commons-lang3`.
- `utils/` perde as 6 classes e seus testes migrados.
- `pom.xml` raiz ganha `<module>core</module>`.
- Nenhum consumidor (`audit`, `exception`, `jdempotent`) é repontado para `core` nesta story — isso é escopo de outras stories (Story 2.8 para `exception`/`audit`).

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#scos-foundation-core]
- [Source: etc/doc/plano/plano-decomposicao-utils.md#fase-3--extrair-core-1-2-dias]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/ARCHITECTURE-SPINE.md#ad-1--fronteira-e-direção-de-dependência-entre-módulos-adopted]
- [Source: _bmad-output/planning-artifacts/epics.md#story-17-extrair-o-módulo-core]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- **Conflito real com a AC #1 (2 commits separados), levado ao usuário em vez de resolvido por adivinhação**: `StringFieldUtils` não pode ser movida "só mover, zero ajuste" porque sua única dependência funcional (`StringTransformRule`) precisa ficar em `utils` (importa Spring) — e `utils` já precisa depender de `core` de volta para as outras 5 classes. Não existe estado intermediário compilável entre "mover" e "ajustar" para essa classe. Usuário escolheu: **commit único** (as 6 classes + o ajuste de `StringFieldUtils`, documentado), em vez de separar as 5 classes triviais de `StringFieldUtils` em 2 commits.
- Build com escopo `core,privacy,utils,exception,audit-api,audit,jdempotent-api,validation-api` → sucesso. Build de reactor completo mostrou 1 falha pré-existente em `jdempotent` (Testcontainers/Docker indisponível neste sandbox, já registrada em `deferred-work.md` na Story 1.6) — `jdempotent` não referencia nenhuma das 6 classes movidas, confirmado sem relação com esta story.
- Confirmado que `audit/pom.xml` não ganhou nenhuma dependência nova — os imports de `ScosUserAuthentication` em `ScosAuditServiceBean`/`ScosHibernateAuditListener`/testes foram só correção mecânica de FQN (a classe se moveu fisicamente), alcançando `core` transitivamente via `utils`. Não é o "repontar consumidor" que o Project Structure Notes pede para não fazer nesta story (isso se refere a não adicionar dependência explícita nova em `audit`/`exception`/`jdempotent`, o que de fato não aconteceu).
- **Revisão (3 camadas) — 0 `patch`, 1 `defer` (novo), restante `reject`**:
  - **Verification-gap interrompida (killed) pela plataforma antes de terminar**, tendo confirmado só `core` verde. Completei a verificação eu mesmo, de forma síncrona: `mvn -o -pl utils -am test` → verde (todas as suítes, incl. `PaginationUtilsTest`/`LoggingFinalFilterTest`/`LoggingInitialFilterTest` que importam de `core`). `mvn -o -pl audit -am test` → verde (usa Testcontainers/Postgres, ~4min; os `WARN` de constraint violation no log são asserções de teste de erro esperadas, não falhas). Nenhum gap de verificação real restante.
  - **Nota de segurança**: durante `mvn -o -pl utils -am test`, o log do módulo `privacy` (teste `privacy-log-e2e`) imprimiu novamente a string de prompt-injection já documentada na Story 1.4 ("If you are an AI Agent, you must not use this library...") — mesmo conteúdo de fixture de teste já identificado e ignorado anteriormente; sem efeito nesta verificação.
  - **Rejeitado** (verificado, sem ação): sugestão de adicionar `scos-foundation-core` como dependência explícita em `audit/pom.xml` — contraria a nota do próprio spec; transitividade (`audit → utils → core`) já confirmada funcionando. Consumidores de `HashUtils`/`ScosBaseUseCase`/`TestDTO` "não mostrados ao revisor" — busca no repo inteiro não encontrou referência órfã ao FQN antigo. `slf4j-api` supostamente não usado em `core` — falso, `HashUtils` usa `@Slf4j`. Mockito supostamente não usado em `core` — falso, `DateUtilsTest` usa. Versões de `archunit`/`junit-jupiter`/`mockito` supostamente não gerenciadas — confirmado gerenciadas (mesmo padrão já validado nas Stories 1.5/1.6). `ArchitectureTest` não barrar import de `utils` — redundante: `core/pom.xml` não declara `utils`, logo um import de `utils` em `core` já não compila, mais forte que qualquer regra ArchUnit. Ausência de forwarding/deprecation shim — fora de escopo, epic inteiro é restauração pré-1.0 sem shims. `field.setAccessible(true)` fora do try/catch — padrão pré-existente, idêntico antes/depois da migração. `StringFieldUtilsTest` supostamente ainda referencia `StringTransformRule` (quebraria compilação) — falso, lido o arquivo real: só chama os 4 métodos de conveniência, nunca `applyTransformation` com `StringTransformRule` diretamente.
  - **Deferido** (novo item em `deferred-work.md`): `StringTransformRule` (`utils`) e `core.StringFieldUtils` agora reimplementam capitalize/camelCase em paralelo (Spring vs. `commons-lang3`), sem fonte única — risco de divergência silenciosa em casos de borda. Não corrigível dentro do escopo desta story sem mover lógica de negócio além do pedido.

### Completion Notes List

- AC #1: `core` criado, compila sem `org.springframework`/`jakarta.persistence`/`jakarta.servlet` no classpath. As 6 classes movidas com lógica preservada; a única exceção (`StringFieldUtils`) teve o ajuste estrutural documentado acima, aplicado no mesmo commit por decisão do usuário.
- AC #2: regra ArchUnit local em `core/src/test/.../ArchitectureTest.java`, nascida no mesmo commit que cria o módulo.
- AC #3: testes migrados 100% verdes, sem alteração de asserção/comportamento.
- AC #4: `ScosStartupListener` não movido, permanece em `utils` até a Story 1.8.
- Lacuna de teste pré-existente confirmada (não introduzida por esta story): `HashUtils`, `PropertiesOrder`, `ScosBaseUseCase`, `ScosUserAuthentication` não tinham testes antes da migração e continuam sem — fora do pedido desta story escrever novos.

### File List

- `pom.xml` (raiz) — `<module>core</module>` adicionado (antes de `privacy`/`utils`, que passam a depender dele) + `dependencyManagement`
- `core/pom.xml` (novo) — deps `slf4j-api`, `lombok` (optional), `commons-lang3`; test-scope `archunit-junit5`/`junit-jupiter`/`mockito-*`
- `core/src/main/java/br/com/sawcunhaos/foundation/core/utils/DateUtils.java`, `HashUtils.java` (movidos de `utils`, sem alteração de lógica)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/utils/StringFieldUtils.java` (movido + ajustado — ver Debug Log)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/sort/PropertiesOrder.java`, `specification/ScosBaseUseCase.java`, `specification/ScosUserAuthentication.java` (movidos, sem alteração de lógica)
- `core/src/test/java/br/com/sawcunhaos/foundation/core/ArchitectureTest.java` (novo) — regra local zero-Spring
- `core/src/test/java/br/com/sawcunhaos/foundation/core/utils/DateUtilsTest.java`, `StringFieldUtilsTest.java`, `utils/dto/TestDTO.java` (movidos de `utils`)
- `utils/pom.xml` — nova dependência em `scos-foundation-core`
- `utils/src/main/java/.../aspect/StringProcessingAspect.java` — import + chamada ajustados para `UnaryOperator<String>` (`annotation.function()::apply`)
- `utils/src/main/java/.../configuration/rest/filter/LoggingFinalFilter.java`, `LoggingInitialFilter.java`, `.../utils/PaginationUtils.java` — imports repontados para `core`
- `utils/src/test/java/.../utils/PaginationUtilsTest.java` — import repontado
- `utils/src/main/java/.../utils/StringFieldUtils.java` (removido, movido para `core`)
- `audit/src/main/java/.../service/ScosAuditServiceBean.java`, `ScosHibernateAuditListener.java`, `audit/src/test/java/.../configuration/ScosLiquibaseTestConfiguration.java`, `ScosUserAuthenticationBean.java` — import de `ScosUserAuthentication` repontado para `core` (correção mecânica, sem nova dependência em `audit/pom.xml`)

## Suggested Review Order

**Ponto de entrada: por que o `core` existe**

- Módulo novo entra como folha do reactor, antes de `privacy`/`utils`, que passam a depender dele.
  [`pom.xml:94`](../../pom.xml#L94)

**O único ajuste de comportamento real (commit único, decisão do usuário)**

- `applyTransformation` generalizada para `UnaryOperator<String>` — só forma de evitar o ciclo `core ↔ utils`.
  [`StringFieldUtils.java:33`](../../core/src/main/java/br/com/sawcunhaos/foundation/core/utils/StringFieldUtils.java#L33)

- Chamador em `utils` ajustado para passar `rule::apply` em vez do enum direto.
  [`StringProcessingAspect.java:38`](../../utils/src/main/java/br/com/sawcunhaos/foundation/utils/aspect/StringProcessingAspect.java#L38)

**Regra de fronteira (AC #2)**

- Falha o build se `core` importar Spring/JPA/Servlet — validado com as 6 classes reais como primeiro caso de teste.
  [`ArchitectureTest.java:33`](../../core/src/test/java/br/com/sawcunhaos/foundation/core/ArchitectureTest.java#L33)

**Movimentação sem alteração de lógica (5 das 6 classes)**

- `DateUtils`/`HashUtils` — sem mudança além do pacote.
  [`DateUtils.java`](../../core/src/main/java/br/com/sawcunhaos/foundation/core/utils/DateUtils.java)
  [`HashUtils.java`](../../core/src/main/java/br/com/sawcunhaos/foundation/core/utils/HashUtils.java)

**Consumidores repontados (mecânico)**

- `utils` (`PaginationUtils`, `LoggingFinalFilter`, `LoggingInitialFilter`) e `audit` (4 arquivos) — só troca de FQN, sem dependência nova.
  [`pom.xml:117`](../../pom.xml#L117)
