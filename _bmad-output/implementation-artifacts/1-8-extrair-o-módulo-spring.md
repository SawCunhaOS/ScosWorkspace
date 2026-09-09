# Story 1.8: Extrair o módulo `spring`

Status: done

<!-- baseline_commit: ba8b66d8364c7890fd27c0c4b0d0ca204270b952 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como time consumidor que usa aspectos genéricos do Spring,
Eu quero um módulo `spring` isolado,
Para não herdar JPA/Servlet ao usar `ScosRule`.

## Acceptance Criteria

1. **Given** as classes do inventário destinadas a `spring` (`ScosRule`, `ScosRuleService`, `NormalizeStrings`, `StringProcessingAspect`, `ScosOnStartupListener`, `ScosStartupListener` — **+ `StringTransformRule`, 7ª classe migrada por necessidade técnica não prevista nesta lista original; ver Debug Log Reference**), **When** o módulo é extraído em 2 commits separados, **Then** `spring` depende de `core` mas não importa `jakarta.servlet`, `jakarta.persistence` nem `spring.data`.
2. **And** uma regra ArchUnit local em `spring` impõe essa restrição.
3. **And** os testes migrados permanecem verdes.

## Tasks / Subtasks

- [x] Task 1: Commit 1 — mover as 6 classes (AC: #1)
  - [x] Criar módulo Maven `scos-foundation-spring`, pacote raiz `br.com.sawcunhaos.foundation.spring`, dependendo de `core` (Story 1.7) + `spring-context` + `spring-aop`
  - [x] Mover: `utils/src/main/java/.../annotation/rules/ScosRule.java`, `ScosRuleService.java`, `annotation/normalizestrings/NormalizeStrings.java`, `aspect/StringProcessingAspect.java`, `listener/ScosOnStartupListener.java`
  - [x] Mover `specification/ScosStartupListener.java` **para cá**, não para `core` — apesar do addendum do PRD listá-la como `core`, seu método `onStartupSystem(ApplicationReadyEvent event)` importa `org.springframework.boot.context.event.ApplicationReadyEvent`, violando a regra de zero-Spring do `core` (confirmado pela própria Story 1.7, AC #4) — migra junto de `ScosOnStartupListener`, que já a consome via `List<ScosStartupListener>`
  - [x] Commit isolado: só mover/renomear pacote, zero mudança de lógica — **com uma 7ª classe adicionada ao escopo por necessidade técnica, não prevista no AC**: `enums/StringTransformRule.java` (+ `StringTransformRuleTest`) também migrou de `utils` para `spring`. Ver Debug Log Reference abaixo.
- [x] Task 2: Commit 2 — ajustar o que precisar (AC: #1)
  - [x] Aplicar separadamente qualquer ajuste de comportamento necessário; documentar se não houver nenhum — **nenhum ajuste de comportamento foi necessário**: todas as mudanças de import/FQN são consequência mecânica do próprio "mover" (mesmo padrão que a Story 1.7 tratou como "mecânico", não "ajuste"). Por isso o código ficou em um único commit em vez de dois — mesma divergência documentada e já aceita na Story 1.7 (ver Debug Log Reference).
- [x] Task 3: Regra ArchUnit local (AC: #2)
  - [x] Teste ArchUnit dentro do módulo `spring` que falha se qualquer classe importar `jakarta.servlet..`, `jakarta.persistence..` ou `org.springframework.data..`
- [x] Task 4: Confirmar testes verdes (AC: #3)
  - [x] Rodar a suíte migrada; nenhum teste específico das 6 classes do AC foi localizado em `utils/src/test` (confirmado) — a única suíte migrada foi `StringTransformRuleTest` (5 testes), que veio junto da 7ª classe. Ausência de cobertura das 6 classes originais documentada nas Completion Notes, sem inventar teste novo fora do escopo desta story de extração.

## Dev Notes

- Depende da Story 1.7 (`core`) já concluída — `spring` importa `core`.
- Propósito do módulo, citado no plano de origem: "existe para que o `core` continue livre de Spring — sem ele, essas classes forçariam a quebra dessa regra."
- `ScosRule`/`ScosRuleService` não têm nenhum consumidor dentro da própria foundation (são estereótipos para as aplicações consumidoras) — isso é esperado, não é sinal de código morto a remover nesta story.
- Fase 4 do plano de origem: ordem de extração dos módulos folha é `spring` → `validation` → `cache` → `jpa` → `web` (do menos para o mais acoplado) — `spring` é o primeiro depois de `core`.

### Project Structure Notes

- Módulo Maven novo: `spring/` — depende de `core`, `spring-context`, `spring-aop`, além de `org.springframework.boot:spring-boot` (necessário para `ApplicationReadyEvent`, não listado no Dev Notes original mas inevitável — ver Debug Log), `org.aspectj:aspectjweaver` (anotações `@Aspect`/`@Around` do `StringProcessingAspect`) e `org.apache.logging.log4j:log4j-api` (lombok `@Log4j2` do `ScosOnStartupListener`).
- `utils/` perde as 6 classes migradas (incluindo `ScosStartupListener`, cujo destino final diverge do addendum do PRD conforme já sinalizado na Story 1.7) **+ `enums/StringTransformRule.java`** (7ª classe, não listada no AC — ver Debug Log).
- `pom.xml` raiz ganha `<module>spring</module>` (logo após `core`, antes de `privacy`/`utils` — `spring` não depende de `utils` e vice-versa).

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#scos-foundation-spring]
- [Source: _bmad-output/implementation-artifacts/1-7-extrair-o-módulo-core.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-18-extrair-o-módulo-spring]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- **Conflito real não coberto pela lista literal de 6 classes do AC, resolvido por engenharia com precedente direto na Story 1.7 (não é "adivinhação de solução"; documentado aqui em vez de simplesmente aplicado em silêncio)**: `NormalizeStrings.function()` é um atributo de anotação — só pode ser primitivo, `String`, `Class`, enum ou anotação (não pode virar `UnaryOperator<String>`, ao contrário do que a Story 1.7 fez com `StringFieldUtils.applyTransformation`). O tipo do atributo é `StringTransformRule`, que mora em `utils/enums` e importa `org.springframework.util.StringUtils`. Três opções avaliadas:
  1. **`spring` depender de `utils`** — rejeitada: inverteria a direção de dependência que esta própria story existe para estabelecer (o "Story" do topo do arquivo é literalmente "não herdar JPA/Servlet ao usar `ScosRule`" — se `spring` puxasse `utils`, herdaria JPA/Servlet/Redis/cache transitivamente, o oposto do objetivo). Também romperia a ordem de extração "do menos para o mais acoplado" do plano de origem (`spring` é o primeiro módulo-folha, extraído antes de qualquer outro justamente por ser o menos acoplado).
  2. **Mudar o tipo do atributo** (ex.: `Class<? extends UnaryOperator<String>>`) — rejeitada: muda a API pública da anotação (comportamento/contrato, não só "mover"), o que a Task 1 explicitly proíbe ("zero mudança de lógica").
  3. **Mover `StringTransformRule` junto com `NormalizeStrings` para `spring`** (escolhida) — zero mudança de lógica (só pacote), mesma técnica que a própria Story 1.7 já usou para `ScosStartupListener`: a lista de 6 classes do addendum do PRD ficou desatualizada assim que a regra de fronteira do módulo foi estabelecida, e a classe correspondente migrou para onde sua dependência funcional (Spring) exige. `StringTransformRule` já importa `org.springframework.util.StringUtils` sem violar a regra ArchUnit de `spring` (que só proíbe `jakarta.servlet..`, `jakarta.persistence..` e `org.springframework.data..` — Spring genérico é permitido, é a razão de o módulo existir).
  - Nota: o inventário congelado (`inventario-classe-modulo.md`, Story 1.1) lista `StringTransformRule` como destino `core`, não `spring`. Essa atribuição já estava tecnicamente inviável desde a Story 1.7 (moveria `org.springframework.util.StringUtils` para dentro do módulo zero-Spring) e ficou documentada como débito em `deferred-work.md` na própria Story 1.7 (implementações paralelas `StringTransformRule` vs. `core.StringFieldUtils`). Esta story não resolve esse débito (ainda há 2 implementações de capitalize/camelCase) — só atualiza a localização física de uma delas, de `utils` para `spring`. `deferred-work.md` atualizado para refletir a nova localização.
- **Dependências de `spring/pom.xml` além do `core`/`spring-context`/`spring-aop` citado no Dev Notes**: compilação exigiu 3 dependências adicionais, todas inevitáveis dado o código real das classes movidas (nenhuma delas viola AC #1 — nenhuma é `jakarta.servlet`, `jakarta.persistence` ou `org.springframework.data`):
  - `org.springframework.boot:spring-boot` — `ApplicationReadyEvent` (usado por `ScosStartupListener`/`ScosOnStartupListener`) vive nesse artefato, não em `spring-context`/`spring-aop`.
  - `org.aspectj:aspectjweaver` — `StringProcessingAspect` usa a sintaxe de anotação AspectJ (`@Aspect`/`@Around`/`ProceedingJoinPoint`/`MethodSignature`), necessária no classpath de compilação mesmo com Spring AOP em modo proxy.
  - `org.apache.logging.log4j:log4j-api` — `ScosOnStartupListener` usa `lombok.extern.log4j.Log4j2`.
  - Todas as 3 já eram gerenciadas transitivamente via `spring-boot-dependencies`/`spring-framework-bom` importados no `scos-bom` pai — nenhuma versão explícita precisou ser fixada no `spring/pom.xml`.
- Verificação: `mvn -o -pl spring -am test` → verde (`ArchitectureTest` 1/1, `StringTransformRuleTest` 5/5). `mvn -o -pl core,spring,privacy,utils,exception,audit-api,jdempotent-api,validation-api,audit -am test` → verde no reactor completo (mesmo escopo usado como referência pela Story 1.7), confirmando que `utils` continua compilando/passando sem as 7 classes migradas e sem nenhuma dependência nova em `utils/pom.xml`.

### Completion Notes List

- AC #1: módulo `scos-foundation-spring` criado, depende de `core` + `spring-context`/`spring-aop` (+ 3 dependências adicionais inevitáveis, ver Debug Log); não importa `jakarta.servlet`, `jakarta.persistence` nem `org.springframework.data` em nenhuma classe própria.
- AC #2: regra ArchUnit local em `spring/src/test/.../ArchitectureTest.java`, nascida no mesmo commit que cria o módulo (mesmo padrão da Story 1.7).
- AC #3: única suíte de teste migrada (`StringTransformRuleTest`, 5 testes) 100% verde, sem alteração de asserção. As 6 classes citadas no AC nunca tiveram teste próprio em `utils/src/test` — confirmado por busca no repo inteiro antes da migração; lacuna pré-existente, não introduzida por esta story, não coberta por teste novo (fora do pedido desta story de extração).
- **Desvio de escopo, documentado e não escondido**: uma 7ª classe (`StringTransformRule`, + seu teste) migrou junto das 6 do AC, por ser a única dependência funcional de `NormalizeStrings` e não poder ficar para trás sem violar a direção de dependência que esta story existe para estabelecer (`spring` não pode depender de `utils`). Justificativa completa e alternativas descartadas no Debug Log Reference acima.
- Task 1 vs. Task 2: nenhum ajuste de comportamento foi necessário (diferente da Story 1.7, onde `StringFieldUtils` teve que ser generalizada). Todas as mudanças nos arquivos movidos são atualizações de FQN/pacote — parte mecânica do "mover", não "ajustar comportamento". Por isso o código ficou em um único commit, como já aconteceu (por motivo distinto) na Story 1.7.
- `archtest` (módulo cross-módulo, Story 1.6) **não** ganhou dependência em `scos-foundation-spring` — mesmo padrão da Story 1.7, que também não adicionou `core` a `archtest`; fora do escopo desta story de extração de um único módulo.

### File List

- `pom.xml` (raiz) — `<module>spring</module>` adicionado (logo após `core`) + `dependencyManagement` para `scos-foundation-spring`
- `spring/pom.xml` (novo) — deps `scos-foundation-core`, `spring-context`, `spring-aop`, `spring-boot`, `aspectjweaver`, `lombok` (optional), `log4j-api`; test-scope `archunit-junit5`/`junit-jupiter`/`mockito-*`
- `spring/src/main/java/br/com/sawcunhaos/foundation/spring/annotation/rules/ScosRule.java`, `ScosRuleService.java` (movidos de `utils`, sem alteração de lógica)
- `spring/src/main/java/br/com/sawcunhaos/foundation/spring/annotation/normalizestrings/NormalizeStrings.java` (movido; import de `StringTransformRule` repontado para o novo pacote)
- `spring/src/main/java/br/com/sawcunhaos/foundation/spring/aspect/StringProcessingAspect.java` (movido; import de `NormalizeStrings` e literal do `@Around` repontados)
- `spring/src/main/java/br/com/sawcunhaos/foundation/spring/listener/ScosOnStartupListener.java` (movido; import de `ScosStartupListener` repontado)
- `spring/src/main/java/br/com/sawcunhaos/foundation/spring/specification/ScosStartupListener.java` (movido, sem alteração de lógica)
- `spring/src/main/java/br/com/sawcunhaos/foundation/spring/enums/StringTransformRule.java` (movido de `utils` — 7ª classe, ver Debug Log — sem alteração de lógica)
- `spring/src/test/java/br/com/sawcunhaos/foundation/spring/ArchitectureTest.java` (novo) — regra local zero-`jakarta.servlet`/`jakarta.persistence`/`org.springframework.data`
- `spring/src/test/java/br/com/sawcunhaos/foundation/spring/enums/StringTransformRuleTest.java` (movido de `utils`, sem alteração de asserção)
- `_bmad-output/implementation-artifacts/deferred-work.md` — item da Story 1.7 sobre `StringTransformRule` atualizado para refletir a nova localização (`spring`, não mais `utils`)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/utils/StringFieldUtils.java` — comentário da Story 1.7 atualizado (FQN antigo de `StringTransformRule` estava desatualizado após a migração); zero mudança de lógica/comportamento, só o comentário

## Suggested Review Order

**Manifesto do novo módulo**

- Ponto de entrada: novo artefato Maven, depende só de `core` + Spring genérico (AC #1).
  [`spring/pom.xml:26`](../../spring/pom.xml#L26)

- 3 dependências não previstas no Dev Notes original, adicionadas por necessidade real de compilação.
  [`spring/pom.xml:111`](../../spring/pom.xml#L111)

**Classes movidas (Task 1, zero mudança de lógica)**

- Atributo de anotação aponta para `StringTransformRule` — motivo raiz do desvio de escopo (7ª classe).
  [`NormalizeStrings.java:27`](../../spring/src/main/java/br/com/sawcunhaos/foundation/spring/annotation/normalizestrings/NormalizeStrings.java#L27)

- Aspecto AOP consome `annotation.function()::apply` — ponte entre a anotação e `core.StringFieldUtils` (Story 1.7).
  [`StringProcessingAspect.java:38`](../../spring/src/main/java/br/com/sawcunhaos/foundation/spring/aspect/StringProcessingAspect.java#L38)

- Interface migrada para `spring` (não `core`) por importar `ApplicationReadyEvent` — decisão já tomada no AC, não nova.
  [`ScosStartupListener.java:16`](../../spring/src/main/java/br/com/sawcunhaos/foundation/spring/specification/ScosStartupListener.java#L16)

- Listener consome `List<ScosStartupListener>`; log ainda cita o nome de classe antigo (débito pré-existente, ver Deferred Work).
  [`ScosOnStartupListener.java:37`](../../spring/src/main/java/br/com/sawcunhaos/foundation/spring/listener/ScosOnStartupListener.java#L37)

**Desvio de escopo: 7ª classe (`StringTransformRule`)**

- Enum movido de `utils` para `spring` — só ele importa `org.springframework.util.StringUtils`, não pode virar `UnaryOperator<String>` (é atributo de anotação).
  [`StringTransformRule.java:17`](../../spring/src/main/java/br/com/sawcunhaos/foundation/spring/enums/StringTransformRule.java#L17)

- `CAPITALIZE` tem edge case de espaço em branco líder (ver Deferred Work) — comportamento pré-existente, não corrigido aqui.
  [`StringTransformRule.java:47`](../../spring/src/main/java/br/com/sawcunhaos/foundation/spring/enums/StringTransformRule.java#L47)

**Regra ArchUnit local (AC #2)**

- Nasce no mesmo commit que cria o módulo; único guardião de que `spring` não importa Servlet/JPA/Spring Data.
  [`ArchitectureTest.java:33`](../../spring/src/test/java/br/com/sawcunhaos/foundation/spring/ArchitectureTest.java#L33)

**Fiação do reactor e débito documentado**

- `spring` entra logo após `core` no reactor; `utils` não depende dele.
  [`pom.xml:97`](../../pom.xml#L97)

- Comentário da Story 1.7 corrigido para o FQN novo de `StringTransformRule` — zero mudança de comportamento.
  [`StringFieldUtils.java:28`](../../core/src/main/java/br/com/sawcunhaos/foundation/core/utils/StringFieldUtils.java#L28)

- 4 itens novos de débito registrados durante a revisão desta story (inventário desatualizado, exception silenciosa no listener, log com nome antigo, edge case de espaço líder).
  [`deferred-work.md:13`](../../deferred-work.md#L13)

**Peripherais**

- Única suíte de teste migrada; cobre as 4 transformações do enum, não as 6 outras classes do AC (lacuna pré-existente, documentada nas Completion Notes).
  [`StringTransformRuleTest.java:21`](../../spring/src/test/java/br/com/sawcunhaos/foundation/spring/enums/StringTransformRuleTest.java#L21)
