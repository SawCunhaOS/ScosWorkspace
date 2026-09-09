---
baseline_commit: 2408eba05d9404625669658de54eb361c4fbbd77
---

# Story 1.5: Criar módulos `*-api` e mover as anotações de contrato

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como time consumidor de domínio puro (ex.: SCOS-Flow),
Eu quero anotações `@Auditable`/`@Jdempotent*`/de validação disponíveis sem depender de implementação,
Para poder anotar meu domínio sem carregar Spring/JPA.

## Acceptance Criteria

1. **Given** as anotações hoje presas aos módulos de implementação, **When** `audit-api`, `jdempotent-api` e `validation-api` são criados, **Then** cada um contém apenas `@interface`/`enum`, sem dependência além de `jakarta.validation-api`.
2. **And** uma regra ArchUnit local em cada módulo `*-api` falha o build se qualquer classe de lógica ou dependência de runtime além de `jakarta.validation-api` for adicionada.

## Tasks / Subtasks

- [x] Task 1: Criar o módulo `scos-foundation-audit-api` (AC: #1)
  - [x] Novo módulo Maven, pacote `br.com.sawcunhaos.foundation.audit.api`, sem dependência de runtime
  - [x] Mover `utils/src/main/java/.../annotation/audit/Auditable.java` e `AuditAction.java` para o novo módulo
  - [x] Repontar `audit/pom.xml` para depender de `scos-foundation-audit-api` em vez de `scos-foundation-utils` para essas duas anotações (o restante da dependência de `audit` em `utils` continua até a Story 1.7/2.8)
  - [x] README do módulo abre com "este artefato não executa nada; a implementação é `scos-foundation-audit`" (mesma frase exigida pela Story 1.15)
- [x] Task 2: Criar o módulo `scos-foundation-jdempotent-api` (AC: #1)
  - [x] Novo módulo Maven, pacote `br.com.sawcunhaos.foundation.jdempotent.api`, sem dependência de runtime
  - [x] Mover as 5 anotações de `utils/src/main/java/.../annotation/jdempotent/`: `JdempotentId.java`, `JdempotentIgnore.java`, `JdempotentProperty.java`, `JdempotentRequestPayload.java`, `JdempotentResource.java`
  - [x] Repontar `jdempotent/pom.xml` para depender de `scos-foundation-jdempotent-api`
  - [x] **Coordenação necessária**: a Story 3.13 (Épico 3) adiciona atributos novos a `@JdempotentResource` (`keySource`, `headerName`, `onMismatch`) — esta story só move a anotação como está hoje; os atributos novos entram depois, no módulo `-api` já criado aqui
  - [x] README abre com "este artefato não executa nada; a implementação é `scos-foundation-jdempotent`"
- [ ] Task 3: Criar o módulo `scos-foundation-validation-api` (AC: #1) — **DEFERRED, decisão do usuário (2026-08-22): adiada até a Story 1.9 mover os `ConstraintValidator`; ver Debug Log References e `deferred-work.md`**
  - [x] Novo módulo Maven (`pom.xml` criado), pacote `br.com.sawcunhaos.foundation.validation.api`, dependência única declarada: `jakarta.validation-api`
  - [ ] Mover as anotações de validação de `utils/src/main/java/.../validation/`: `CPF.java`, `CNPJ.java`, `TaxIdentifier.java` (a anotação, não o value object `valueobjects/TaxIdentifier.java` — confirmado: são classes distintas, o value object fica em `utils/.../valueobjects/TaxIdentifier.java` e não é tocado), `zipcode/ZipCode.java` — **não movidas**: conflito de design encontrado, ver nota abaixo
  - [ ] Os `ConstraintValidator` (`CnpjValidator`, `CpfValidator`, `TaxIdentifierValidator`, `ZipCodeValidator`) **não** vão para `validation-api` — são lógica de validação, ficam no módulo `validation` (Story 1.9); `validation-api` recebe só a anotação `@interface`
  - [ ] Nenhum consumidor repontado ainda nesta story (os `ConstraintValidator` continuam em `utils` até a Story 1.9)
  - [ ] README abre com "este artefato não executa nada; a implementação é `scos-foundation-validation`"
- [x] Task 4: Regra ArchUnit por módulo `*-api` (AC: #2) — feita para `audit-api` e `jdempotent-api`; `validation-api` pendente (bloqueada pela Task 3)
  - [x] `audit-api` e `jdempotent-api`: teste ArchUnit local (`ArchitectureTest`, usa a dependência gerenciada pela Story 1.4) que falha se qualquer classe do módulo não for `@interface` ou `enum`, e se qualquer dependência além do JDK for declarada — validado com controle negativo (classe não-anotação/enum inserida e removida, teste falhou como esperado, ver Debug Log)
  - [ ] `validation-api`: DEFERRED junto com a Task 3, até a Story 1.9
  - [x] Cada regra nasce no mesmo commit que cria o módulo que protege — não adiar para uma story posterior de "regras cross-módulo" (essas cross-módulo são a Story 1.14, via `archtest`; esta regra é local a cada `*-api` e roda dentro do próprio módulo)

## Dev Notes

- **Divergência a resolver antes de mover, não depois**: o inventário de anotações do plano de origem lista "18 anotações" no `utils`, mas a árvore atual (`utils/src/main/java/.../annotation/request/`) contém **6** classes de request (`ScosRequestDELETE`, `ScosRequestGET`, `ScosRequestMapping`, `ScosRequestPATCH`, `ScosRequestPOST`, `ScosRequestPUT`), e o plano só cita 5 (sem `PATCH`) na tabela de destino. `ScosRequestPATCH` também vai para `web` (mesma família de `ScosRequestGET/POST/PUT/DELETE`), mas **não é escopo desta story** — `web` não ganha módulo `-api` (ver Princípio no addendum do PRD: `@ScosController`/`@ScosRequest*` marcam beans Spring, sem consumidor de domínio puro plausível). Registrar essa contagem revisada nas Completion Notes para manter o inventário da Story 1.1 consistente.
- Esta story **não move** `ScosController`, `ScosRequestMapping`/`GET`/`POST`/`PUT`/`PATCH`/`DELETE`, `ScosRule`, `ScosRuleService` nem `NormalizeStrings` — essas vão direto para `web`/`spring` nas Stories 1.8/1.12, sem módulo `-api` companheiro (decisão já registrada no addendum: só ganham `-api` anotações com consumidor plausível de domínio puro).
- Regra que impede o `*-api` de virar um novo `utils` (citação direta do plano de origem, é o critério de aceite real por trás do AC #1/#2): "ele contém apenas anotações e os enums que as anotações referenciam nos seus atributos. Nada mais — sem helper, sem constante solta, sem interface de serviço."
- **Ordem de execução (NFR1 / plano de origem, Fase 2)**: esta story deve rodar **antes** de qualquer trabalho do Épico 3 (`jdempotent`) que toque `@JdempotentResource`, porque a Story 3.13 desse épico escreve atributos novos na anotação e espera que ela já esteja no módulo `-api` final.
- Modo de falha silencioso a ter em mente (não é escopo desta story corrigir, mas informa o design): depender só do `-api` compila e não faz nada em runtime sem o módulo de implementação no classpath — é isso que a Story 1.15 (log de contagem na subida) e o README padronizado desta story mitigam.

### Project Structure Notes

- 3 módulos Maven novos: `audit-api`, `jdempotent-api`, `validation-api`, cada um `pom.xml` + `README.md` + as anotações movidas + 1 teste ArchUnit local.
- `utils/pom.xml` perde as classes movidas; `audit/pom.xml` e `jdempotent/pom.xml` ganham dependência nova nos respectivos `-api`.
- Adicionar os 3 módulos novos em `<modules>` do `pom.xml` raiz.

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#estratégia--api-anotação-separada-da-implementação]
- [Source: etc/doc/plano/plano-decomposicao-utils.md#todas-as-anotações-por-destino]
- [Source: _bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/addendum.md#princípio-por-que-web-e-spring-não-ganham-módulo--api-companheiro]
- [Source: _bmad-output/planning-artifacts/epics.md#story-15-criar-módulos-api-e-mover-as-anotações-de-contrato]
- [Source: _bmad-output/planning-artifacts/epics.md#story-313-suportar-header-idempotency-key-como-fonte-de-chave]

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- **Bloqueio na Task 3 (`validation-api`), levado ao usuário em vez de resolvido por adivinhação (regra do projeto)**: `CPF.java`/`CNPJ.java`/`TaxIdentifier.java`/`ZipCode.java` hoje declaram `@Constraint(validatedBy = XValidator.class)`, uma referência de **compilação** ao `ConstraintValidator` concreto. A task pede mover só a anotação para `validation-api` (dependência única: `jakarta.validation-api`) e manter o `ConstraintValidator` em `utils` até a Story 1.9. Isso é estruturalmente impossível sem quebrar uma das duas pontas:
  - Se `CPF.java` (em `validation-api`) mantém `validatedBy = CpfValidator.class`, `validation-api` passa a depender de `utils` (onde `CpfValidator` mora) — viola a AC #1 (dependência única `jakarta.validation-api`) e cria ciclo de módulo (`utils → validation-api → utils`, já que `utils` também precisaria depender de `validation-api` pela anotação).
  - Se `validatedBy` é esvaziado (`validatedBy = {}`) para manter `validation-api` limpo, o Bean Validation deixa de descobrir o validador em tempo de execução sem um mapeamento XML adicional (`META-INF/validation.xml`) — quebra `ZipCodeValidatorTest` (`utils/src/test/.../ZipCodeValidatorTest.java`), que hoje passa chamando `Validation.buildDefaultValidatorFactory().getValidator().validate(zipCodeDTO)` de ponta a ponta. Isso violaria NFR2 (build verde a cada commit) e não está no escopo desta story (mapeamento XML é reescrita de lógica, não "mover e renomear").
  - Mover os `ConstraintValidator` junto para `validation-api` resolveria a compilação, mas a própria task proíbe isso explicitamente (validadores são lógica, não contrato) e arrastaria `caelum-stella-core`/`commons-lang3`/Spring para o módulo `-api`.
  Nenhuma das três opções cabe dentro do que a story autoriza sem decisão do usuário — pausado aqui, `pom.xml` do `validation-api` criado mas sem as anotações movidas.
  **Decisão do usuário (2026-08-22)**: adiar a Task 3 inteira até a Story 1.9 mover os `ConstraintValidator` de `utils` para o módulo `validation` — nenhuma das opções de contorno (mapeamento XML, mover os validadores agora) foi autorizada. Entrada registrada em `_bmad-output/implementation-artifacts/deferred-work.md` para rastreio fora desta story. `validation-api` fica como placeholder (`pom.xml` só com dependência `jakarta.validation-api`, registrado em `<modules>` do pom raiz) até então.
- Validação positiva: `mvn -o -pl audit-api,jdempotent-api,validation-api,privacy,utils,exception,audit,jdempotent -am compile` e `...test-compile` verdes (offline, `.m2` local). `mvn -o -pl audit-api,jdempotent-api test`: 2/2 testes ArchUnit verdes em cada módulo.
- Controle negativo: inseri temporariamente uma classe `Scratch` (não `@interface`/`enum`) em `audit-api`, rodei `mvn -o -pl audit-api test` → falhou como esperado (`Architecture Violation ... Scratch is neither an annotation type nor an enum`); removida a classe, suíte voltou a verde. Confirma que a regra ArchUnit não passa vacuamente.
- Testes de integração de `audit`/`jdempotent` (testcontainers) não executados nesta validação — só `test-compile`, para confirmar que a troca de import (`utils.annotation.*` → `audit.api`/`jdempotent.api`) compila; ambiente sem Docker validado neste agente.

### Completion Notes List

- AC1 (parcial): `audit-api` e `jdempotent-api` criados, contêm só `@interface`/`enum`, zero dependência de runtime além do JDK. `validation-api` tem `pom.xml` (dependência única `jakarta.validation-api`) mas ainda sem as anotações — **deferido por decisão do usuário (2026-08-22)**, ver Debug Log e `deferred-work.md`.
- AC2 (parcial): regra ArchUnit local nasceu no mesmo commit/módulo para `audit-api` e `jdempotent-api`. Deferido para `validation-api` junto com a Task 3.
- Verificação final pós-decisão: `mvn -o compile` no reactor inteiro (verde) e `mvn -o -pl audit-api,jdempotent-api test` (2/2 ArchUnit verdes em cada) reconfirmados com o estado atual (validation-api como placeholder, sem código-fonte).
- **Revisão (3 camadas: blind-hunter, edge-case-hunter, verification-gap) — 1 achado `patch` aplicado, restante `reject`**:
  - **Corrigido**: `jdempotent/src/main/java/.../core/aspect/IdempotentAspect.java:162` — o pointcut do AspectJ (`@Around("@annotation(...)")`) é uma string literal opaca ao `javac`; o `import` de `JdempotentResource` foi repontado para `jdempotent.api` nesta story, mas a string do pointcut continuou apontando para `utils.annotation.jdempotent.JdempotentResource` (classe já deletada). Resultado: o aspecto nunca interceptava métodos anotados, zerando a proteção de idempotência em produção — `mvn compile` ficava verde (bug invisível ao compilador) mas `IdempotentAspectITTest` (não usa Docker/testcontainers, roda no `mvn test` normal) falhava 8/9. O verification-gap reproduziu a falha e a correção; grep no repo inteiro (`utils\.annotation\.audit\|utils\.annotation\.jdempotent`) confirmou ser a única referência obsoleta restante. Corrigido para `jdempotent.api.JdempotentResource`; `IdempotentAspectITTest` volta a passar 9/9; reactor `mvn -o compile test-compile` verde.
  - **Polimento aplicado**: comentário em `pom.xml` raiz corrigido — dizia que `utils/audit/jdempotent` dependem dos 3 módulos `-api` novos, mas `validation-api` ainda não tem nenhum dependente (Task 3 deferida).
  - **Rejeitado** (sem ação): `validation-api` vazio sem README/ArchitectureTest (intencional, decisão do usuário); ausência de guarda ArchUnit contra futuro ciclo em módulo ainda vazio (especulativo); `JdempotentResource` sem `@Target` (confirmado pré-existente, não introduzido por esta story); demais consumidores de FQN antigo fora de `audit`/`jdempotent`/`utils` (grep repo-wide não encontrou nenhum); `utils/pom.xml` sem alteração (confirmado correto — nada em `utils` usa mais essas anotações); preocupação de semver/breaking change (fora do escopo da story); duplicação das 2 `ArchitectureTest` sem base compartilhada (intencional — regra AC #2 pede teste local por módulo); README de `jdempotent-api` citando "Story 3.13" (pedido explícito da própria story, Task 2); atualização de BOM externo (especulativo); falta de ADR do padrão `*-api` (nível de projeto, fora desta story); alinhamento de `maven.compiler.source/target=25` (confirmado sem conflito — reactor compila limpo).
- Divergência de contagem de anotações (Dev Notes): confirmado nesta análise — `utils/.../annotation/request/` tem **6** classes (`ScosRequestDELETE/GET/Mapping/PATCH/POST/PUT`), não 5; nenhuma delas é tocada por esta story (vão para `web` nas Stories 1.8/1.12, sem `-api` companheiro). Registrando para manter o inventário da Story 1.1 consistente, como pedido nos Dev Notes.
- `audit/pom.xml` e `jdempotent/pom.xml` **não** perderam a dependência em `scos-foundation-utils` — cada um ganhou uma dependência **adicional** no seu `-api` (a Dev Note de Task 1 já previa isso: "o restante da dependência de audit em utils continua até a Story 1.7/2.8").
- `utils/pom.xml` não precisou de nenhuma dependência nova para as Tasks 1/2: nada dentro de `utils` usava `Auditable`/`AuditAction`/`Jdempotent*` (confirmado por grep no repo inteiro) — só os módulos `audit`/`jdempotent` os consumiam.

### File List

- `pom.xml` (raiz) — `audit-api`, `jdempotent-api`, `validation-api` adicionados a `<modules>` (antes de `privacy`, já que são folhas sem dependência) e a `<dependencyManagement>`
- `audit-api/pom.xml` (novo) — módulo Maven sem dependência de runtime, ArchUnit+JUnit em escopo `test`
- `audit-api/src/main/java/br/com/sawcunhaos/foundation/audit/api/Auditable.java` (novo, movido de `utils`)
- `audit-api/src/main/java/br/com/sawcunhaos/foundation/audit/api/AuditAction.java` (novo, movido de `utils`)
- `audit-api/src/test/java/br/com/sawcunhaos/foundation/audit/api/ArchitectureTest.java` (novo) — regra local AD-5
- `audit-api/README.md` (novo) — abre com a frase padrão exigida
- `jdempotent-api/pom.xml` (novo) — mesmo molde de `audit-api`
- `jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/{JdempotentId,JdempotentIgnore,JdempotentProperty,JdempotentRequestPayload,JdempotentResource}.java` (novos, movidos de `utils`)
- `jdempotent-api/src/test/java/br/com/sawcunhaos/foundation/jdempotent/api/ArchitectureTest.java` (novo) — regra local AD-5
- `jdempotent-api/README.md` (novo) — abre com a frase padrão exigida, registra a nota de coordenação da Story 3.13
- `validation-api/pom.xml` (novo) — dependência única `jakarta.validation-api` + ArchUnit/JUnit em `test`; **sem código-fonte ainda** (bloqueado)
- `utils/src/main/java/.../annotation/audit/` (removido, 2 arquivos + diretório)
- `utils/src/main/java/.../annotation/jdempotent/` (removido, 5 arquivos + diretório)
- `audit/pom.xml` — dependência nova em `scos-foundation-audit-api`
- `audit/src/main/java/.../service/ScosAuditServiceBean.java`, `.../service/ScosHibernateAuditListener.java` — import de `Auditable` repontado para `audit.api`
- `audit/src/test/java/.../service/CountryReadService.java`, `.../domain/entity/Country.java` — import repontado
- `jdempotent/pom.xml` — dependência nova em `scos-foundation-jdempotent-api`
- `jdempotent/src/main/java/.../core/aspect/IdempotentAspect.java`, `.../core/chain/JdempotentIgnoreAnnotationChain.java`, `.../core/chain/JdempotentPropertyAnnotationChain.java` — imports repontados
- `jdempotent/src/test/java/.../redis/test/app/controller/PrimeNumbersController.java`, `.../core/utils/IdempotentTestPayload.java`, `.../core/utils/TestIdempotentResource.java`, `.../core/aspect/IdempotentAspectITTest.java`, `.../core/aspect/IdempotentAspectUTTest.java` — imports repontados

## Suggested Review Order

**Estrutura dos módulos `*-api`**

- Ponto de entrada: os 3 módulos novos entram como folhas do reactor, antes de `privacy`/`utils`.
  [`pom.xml:84`](../../pom.xml#L84)

- `dependencyManagement` centraliza a versão dos 3 módulos `-api` para o restante do reactor.
  [`pom.xml:136`](../../pom.xml#L136)

**Bug crítico corrigido na revisão: pointcut do AspectJ**

- String literal do pointcut não foi repontada junto com o `import`; zerava a idempotência em runtime até a correção (ver Debug Log).
  [`IdempotentAspect.java:162`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L162)

**Módulo `audit-api` (completo)**

- Anotação de contrato, movida sem alteração semântica.
  [`Auditable.java:22`](../../audit-api/src/main/java/br/com/sawcunhaos/foundation/audit/api/Auditable.java#L22)

- Enum referenciado pelo atributo `action()` da anotação acima.
  [`AuditAction.java:15`](../../audit-api/src/main/java/br/com/sawcunhaos/foundation/audit/api/AuditAction.java#L15)

- Regra ArchUnit local que impede o módulo de virar um novo `utils`.
  [`ArchitectureTest.java:35`](../../audit-api/src/test/java/br/com/sawcunhaos/foundation/audit/api/ArchitectureTest.java#L35)

**Módulo `jdempotent-api` (completo)**

- A anotação central que o bug acima deixou de fato inoperante até a correção.
  [`JdempotentResource.java:24`](../../jdempotent-api/src/main/java/br/com/sawcunhaos/foundation/jdempotent/api/JdempotentResource.java#L24)

**Módulo `validation-api` (deferido por decisão do usuário)**

- Só o `pom.xml` existe; anotações ficam em `utils` até a Story 1.9 destravar o ciclo de dependência.
  [`validation-api/pom.xml:1`](../../validation-api/pom.xml#L1)

- Motivo completo do adiamento, para rastreio fora desta story.
  [`deferred-work.md:1`](deferred-work.md#L1)

**Consumidores repontados**

- `audit`/`jdempotent` ganham dependência nova nos respectivos `-api`, mantendo a dependência existente em `utils`.
  [`audit/pom.xml:108`](../../audit/pom.xml#L108)
  [`jdempotent/pom.xml:149`](../../jdempotent/pom.xml#L149)
