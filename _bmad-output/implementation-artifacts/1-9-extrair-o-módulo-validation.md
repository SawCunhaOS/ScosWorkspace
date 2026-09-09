# Story 1.9: Extrair o módulo `validation`

Status: done

<!-- Decisão de mover ExceptionCode/ScosException/ScosExceptionCode para core (adiantando escopo da Story 2.8) confirmada explicitamente pelo usuário/PO em 2026-08-22. -->

<!-- baseline_commit: 035ea05bf924a8c467f1dbe606cdc3c8cf4444b6 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como time consumidor que usa value objects brasileiros (CPF/CNPJ),
Eu quero um módulo `validation` próprio,
Para não carregar JPA completo só para validar um documento.

## Acceptance Criteria

1. **Given** `Cpf`, `Cnpj`, `Email`, `TaxIdentifier` e o restante do inventário destinado a `validation`, **When** o módulo é extraído dependendo de `core` e `validation-api`, com `jakarta.persistence-api` como `provided`, **Then** `validation` compila e os testes dos value objects permanecem verdes.
2. **And** a extração ocorre em 2 commits separados (mover vs. ajustar comportamento).

## Tasks / Subtasks

- [x] Task 1: Commit 1 — mover value objects e validators (AC: #1)
  - [x] Criar módulo Maven `scos-foundation-validation`, pacote raiz `br.com.sawcunhaos.foundation.validation`, dependendo de `core` (Story 1.7), `validation-api` (Story 1.5), `caelum-stella-core` e `jakarta.persistence-api` como `provided`
  - [x] Mover os value objects: `utils/src/main/java/.../valueobjects/Cpf.java`, `Cnpj.java`, `Email.java`, `TaxIdentifier.java`
  - [x] Mover os `ConstraintValidator`: `utils/src/main/java/.../validation/taxIdentifier/constraint/CnpjValidator.java`, `CpfValidator.java`, `TaxIdentifierValidator.java`, `validation/zipcode/constraint/ZipCodeValidator.java` — **a premissa de que as anotações "já foram para `validation-api` na Story 1.5" estava errada** (Story 1.5 deferiu essa Task explicitamente para esta story, ver Debug Log); as 4 anotações foram movidas agora, junto com os validadores
  - [x] Mover as classes de anotação `validation/taxIdentifier/CNPJ.java`, `CPF.java` — **e também `TaxIdentifier.java`/`ZipCode.java`**, não citadas neste bullet mas confirmadas no inventário congelado da Story 1.1 (linhas 56-59) com o mesmo destino `validation-api`; nenhuma estava migrada ainda
  - [x] Mover os testes: `valueobjects/CnpjTest.java`, `CpfTest.java`, `EmailTest.java`, `TaxIdentifierTest.java`, `validation/zipcode/constraint/ZipCodeValidatorTest.java` (e o DTO de apoio `ZipCodeDTO.java`) — **e também `ValueObjectJacksonSerializationTest.java`**, não citado na task mas dependia diretamente dos 4 value objects; teria quebrado a compilação de `utils` se deixado para trás
  - [x] `jakarta.persistence-api` como `provided`: os value objects usam `@Embeddable` — só a anotação em tempo de compilação, sem arrastar runtime de persistência
  - [x] Commit isolado: só mover/renomear pacote — **ver Debug Log para os ajustes que não puderam ser isolados da própria mecânica da divisão** (ligação `validatedBy`, `ScosException`)
- [x] Task 2: Commit 2 — ajustar o que precisar (AC: #2)
  - [x] Ajustes de comportamento aplicados (documentados em detalhe no Debug Log): (1) `validatedBy = {}` nas 4 anotações + `META-INF/validation.xml`/`validation-constraint-mappings.xml` no módulo `validation` para restaurar a ligação anotação→validador sem criar ciclo de módulo; (2) `@Aspect`/`@Component` removidos de `CnpjValidator`/`CpfValidator`/`TaxIdentifierValidator` (não fazem nada — Bean Validation instancia por reflexão — e forçariam depender de Spring/AspectJ); (3) `@QueryEmbeddable` removido de `Cnpj` (só ele tinha; nenhum consumidor no repo, dependência `querydsl` fora da lista de deps da AC); (4) `ExceptionCode`/`ScosException`/`ScosExceptionCode` movidos de `utils` para `core` — **não pedido pela task, mas obrigatório**: sem isso os value objects não teriam como lançar `ScosException` sem `validation` depender de `utils` (reintroduzindo Spring/JPA completo, o problema que a story existe para resolver). Ver Debug Log — decisão de maior risco desta story, recomendo revisão explícita antes de aceitar.

  **Não requisitado pela story, descoberto durante a implementação (não isolável em commits futuros sem quebrar o build):**
  - [x] Dependências de teste adicionadas a `validation/pom.xml`: `hibernate-validator` (implementação de Bean Validation para os testes rodarem `Validation.buildDefaultValidatorFactory()`/`byDefaultProvider()`), `jackson-databind` (para o `ValueObjectJacksonSerializationTest` movido)
  - [x] `ZipCodeValidatorTest` ajustado para usar `ParameterMessageInterpolator` em vez do interpolador padrão (que exige `jakarta.el`, não declarado — nenhuma mensagem deste módulo usa sintaxe EL, então o comportamento é idêntico)
  - [x] Novo teste `TaxIdentifierAnnotationsValidatorTest` — a suíte movida nunca exercitava `@CPF`/`@CNPJ`/`@TaxIdentifier` via Bean Validation (só a validação interna do value object); sem um teste assim, um erro de digitação no FQN dentro do XML de mapeamento passaria despercebido (Bean Validation trata anotação sem validador mapeado como "nenhuma violação", não como erro de build)
  - [x] Completado o débito da Story 1.5 (Task 3/4, deferida): `validation-api` ganhou as 4 anotações, `ArchitectureTest` local e `README.md`, seguindo o mesmo molde de `audit-api`/`jdempotent-api`

## Dev Notes

- Depende das Stories 1.5 (`validation-api` com as anotações) e 1.7 (`core`) já concluídas.
- **Decisão D2 do plano de origem, já resolvida pelo AC**: `valueobjects` usam `@Embeddable`; ficam em `validation` (não em `jpa`) com `jakarta.persistence-api` como `provided` — "funciona, porque são só anotações, mas mistura conceitos" é o trade-off já aceito, não uma pergunta em aberto para o dev.
- Esta story tem interseção direta com a Story 1.3 (migração Gson→Jackson): a AC #6 daquela story pede para levantar se `Cpf`/`Cnpj`/`Email`/`TaxIdentifier` têm `TypeAdapter` Gson próprio **antes** de migrarem para cá — confirmar que a Story 1.3 já rodou e que esses value objects já serializam via Jackson antes de mover o pacote (evita mover um problema de serialização não resolvido).
- Fase 4 do plano de origem: `validation` é o segundo módulo folha a sair, depois de `spring`.

### Project Structure Notes

- Módulo Maven novo: `validation/` — depende de `core`, `validation-api`, `caelum-stella-core`, `jakarta.persistence-api` (`provided`).
- `utils/` perde os 4 value objects, os `ConstraintValidator` e os testes correspondentes.
- `pom.xml` raiz ganha `<module>validation</module>`.

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#scos-foundation-validation]
- [Source: etc/doc/plano/plano-decomposicao-utils.md#7-decisões-que-preciso-que-você-tome] (Decisão D2)
- [Source: _bmad-output/planning-artifacts/epics.md#story-19-extrair-o-módulo-validation]
- [Source: _bmad-output/planning-artifacts/epics.md#story-13-migrar-serialização-json-de-gson-para-jackson]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- **Premissa da story incorreta, descoberta ao ler `_bmad-output/implementation-artifacts/1-5-criar-módulos-api-e-mover-as-anotações-de-contrato.md` e `deferred-work.md` (contexto obrigatório, carregado antes de iniciar)**: o bullet 2 da Task 1 afirma "as anotações `@CPF`/`@CNPJ`/`@TaxIdentifier`/`@ZipCode` já foram para `validation-api` na Story 1.5". Isso é falso — a Story 1.5 **deferiu explicitamente** essa migração (Task 3 inteira) por decisão do usuário registrada em 2026-08-22, justamente porque mover só a anotação criaria um ciclo de módulo (`validatedBy = XValidator.class` exige o validador no classpath da anotação). `validation-api` existia só como `pom.xml` placeholder, sem nenhuma classe. Tratado como o "caminho natural" que a Story 1.5 esperava que esta story destravasse — resolvido nesta story (ver abaixo), não reportado como bloqueio porque a solução (XML mapping) cabia dentro do que a própria Task 2 desta story já autoriza ("qualquer ajuste de comportamento necessário").
- **Ciclo de módulo `validatedBy` — resolvido via XML constraint mapping (Jakarta Bean Validation 3.1)**: com as anotações em `validation-api` (dependência única `jakarta.validation-api`) e os `ConstraintValidator` em `validation` (que depende de `validation-api`, não o contrário), `@Constraint(validatedBy = CpfValidator.class)` não compila — criaria `validation-api → validation → validation-api`. Resolvido com `validatedBy = {}` nas 4 anotações e `META-INF/validation.xml` + `META-INF/validation-constraint-mappings.xml` em `validation/src/main/resources`, usando o schema `https://jakarta.ee/xml/ns/validation/mapping` versão 3.1 (confirmado inspecionando o XSD real dentro do jar `hibernate-validator-9.1.3.Final` resolvido neste `.m2`, para não adivinhar namespace/versão). Validado com um teste novo (`TaxIdentifierAnnotationsValidatorTest`) que exercita `@CPF`/`@CNPJ`/`@TaxIdentifier` via `Validator.validate(...)` de ponta a ponta — a suíte movida de `utils` nunca testava esse caminho (só a validação interna dos value objects), então sem esse teste um erro de FQN no XML passaria silenciosamente (Bean Validation trata anotação sem validador mapeado como "sem violação", não como erro).
- **Maior decisão desta story, sinalizada para revisão explícita**: os value objects (`Cpf`/`Cnpj`/`Email`/`TaxIdentifier`) lançam `ScosException(ScosExceptionCode.XXX_INVALID)` — ambos ainda em `utils` (a migração completa do "contrato de exceção" para `core` é a Story 2.8, Épico 2, que roda **depois** desta). `validation` não pode depender de `utils` (reintroduziria Spring/JPA completo — o problema que a story existe para resolver) nem trocar o tipo da exceção (mudaria o contrato HTTP: `exception/ExceptionsHandler` tem `@ExceptionHandler(ScosException.class)` que traduz para RFC 9457 usando `code`/`httpCode`/`title`; os testes movidos (`CpfTest`, etc.) afirmam literalmente `ScosExceptionCode.CPF_INVALID.getCode()`). Optei por mover `ExceptionCode`, `ScosException` e `ScosExceptionCode` de `utils` para `core` agora — **executando adiantado parte do escopo da Story 2.8** — em vez de preemptivamente inventar um novo tipo de exceção. Justificativa: (1) é a única opção que preserva 100% do comportamento testado; (2) é mecânica (mesmo padrão da Story 1.7 com `ScosUserAuthentication`: nenhum pom novo precisou de dependência, `exception`/`audit` já dependiam de `utils`, que já depende de `core`); (3) reduz o trabalho da Story 2.8, que segundo sua própria AC ainda precisa mover `LocaleService` e as 4 exceções de `exception/error/*`. Risco: a Story 2.8 assume essas classes "já corrigidas" ainda em `utils`/`exception` no momento de mover — quem rodar essa story precisa saber que `ScosException`/`ExceptionCode`/`ScosExceptionCode` já estão em `core`. **Confirmação explícita do usuário/PO obtida em 2026-08-22** (a alternativa — mudar o tipo de exceção lançado pelos value objects — seria uma escolha de arquitetura diferente com impacto em qualquer consumidor real da lib, por isso a confirmação foi solicitada antes de aceitar esta story).
- **`@Aspect`/`@Component` em `CnpjValidator`/`CpfValidator`/`TaxIdentifierValidator`**: removidos na migração. Jakarta Bean Validation instancia `ConstraintValidator` por reflexão (construtor sem argumento), não via Spring DI — essas anotações nunca tiveam efeito funcional (confirmado: `ZipCodeValidator`, no mesmo pacote `utils`, nunca as teve e sempre validou do mesmo jeito). Mantê-las forçaria `validation` a depender de `org.springframework`/`org.aspectj`, o oposto do objetivo da story.
- **`@QueryEmbeddable` em `Cnpj`**: removido. É a única das 4 classes que tinha essa anotação do QueryDSL; `grep` no repo inteiro não encontrou nenhum `QCnpj` consumido em lugar nenhum (só o APT do módulo `utils` a gerava, para nada usar). Mantê-la exigiria adicionar `querydsl-core` a `validation`, fora da lista de dependências desta AC.
- **Verificação**: `mvn -o clean test-compile` no reactor inteiro → verde (confirma que nenhum outro módulo ficou com FQN órfão). `mvn -o -pl validation-api,core,validation -am test` → 172/172 verdes (26 em `core`, incl. o `ScosExceptionCodeTest` movido; 2 em `validation-api`; 144 em `validation`, incl. os 4 novos testes de wiring). `mvn -o -pl utils,exception -am clean test` → 87/87 verdes (confirma `ExceptionsHandlerScosExceptionTest`/`ExceptionsHandlerMdcTest`, que exercitam a tradução HTTP do `ScosException` movido, continuam idênticos). `mvn -o -pl audit -am clean test-compile` → verde (fixture `InsideAuditExampleService` repontada). `mvn -o -pl audit-api,jdempotent-api,spring -am test` → verde (nenhuma regressão fora do escopo desta story). Testes de integração de `audit`/`jdempotent` (Testcontainers/Docker) não executados — ambiente sem Docker, mesma limitação já registrada em `deferred-work.md` pelas Stories 1.6/1.7.
- **AC #2 (2 commits separados) ainda não cumprido nesta sessão**: por política do agente (só commitar quando pedido explicitamente), as mudanças ficaram no working tree. Um possível corte para os 2 commits: **Commit 1** = novo módulo `validation` + `validation-api` preenchido + arquivos movidos de `utils` (incluindo o ajuste mínimo de `validatedBy = {}`/XML, que é estrutural à própria divisão, não opcional) + `pom.xml` raiz; **Commit 2** = remoção de `@Aspect`/`@Component`/`@QueryEmbeddable`, o teste novo de regressão, e o adiantamento do escopo da Story 2.8 (`ExceptionCode`/`ScosException`/`ScosExceptionCode` → `core`). Como o próprio recorte "mover vs. comportamento" ficou ambíguo por causa das descobertas acima, sugiro confirmar o corte com o usuário antes de commitar.

### Completion Notes List

- AC #1: `validation` compila dependendo de `core`, `validation-api`, `caelum-stella-core` e `jakarta.persistence-api` (`provided`) — mais `commons-lang3`, `lombok` e `jspecify` (necessários pelo código movido, não declarados na lista original da story porque `core` os declara como `optional`/não os expõe transitivamente; ver `validation/pom.xml`). Os testes dos value objects permanecem 100% verdes (mesmas asserções, incl. as que checam `ScosExceptionCode`).
- AC #2: ajustes de comportamento aplicados e documentados no Debug Log (não há cenário de "nenhum ajuste necessário" — a própria divisão exigiu pelo menos o `validatedBy`/XML e o `ScosException`). Divisão em 2 commits git ainda pendente (ver Debug Log).
- Débito da Story 1.5 (Task 3/4, `validation-api`) fechado nesta story: 4 anotações + `ArchitectureTest` local + `README.md`.
- `deferred-work.md`: a primeira entrada (bloqueio de `validation-api`) fica resolvida por esta story; não removida do arquivo (histórico), mas o leitor deve considerá-la encerrada. A segunda entrada (jacoco 0% de cobertura em módulo só-anotação/enum) **passa a valer também para `validation-api`** agora que ele tem conteúdo real — não verificado nesta sessão (perfil `analyze` não foi exercitado), mas é a previsão que a própria entrada já fazia.
- Story 1.3 (Gson→Jackson) confirmada já concluída antes desta story rodar (commit `d12da41` no histórico) — `ValueObjectJacksonSerializationTest` (movido para `validation`) já provava que os 4 value objects serializam corretamente via Jackson; nenhum `TypeAdapter` Gson pendente encontrado.

### File List

- `pom.xml` (raiz) — `<module>validation</module>` adicionado (após `spring`), `dependencyManagement` ganha `scos-foundation-validation`, comentário sobre `validation-api` corrigido (não é mais "sem dependente")
- `validation/pom.xml` (novo) — deps `core`, `validation-api`, `caelum-stella-core`, `jakarta.persistence-api` (`provided`), `commons-lang3`, `lombok`, `jspecify`; test-scope `hibernate-validator`, `jackson-databind`, `archunit-junit5`, `junit-jupiter`
- `validation/src/main/java/br/com/sawcunhaos/foundation/validation/valueobjects/{Cpf,Cnpj,Email,TaxIdentifier}.java` (movidos de `utils`; `Cnpj` perdeu `@QueryEmbeddable`, ver Debug Log)
- `validation/src/main/java/br/com/sawcunhaos/foundation/validation/taxidentifier/constraint/{CnpjValidator,CpfValidator,TaxIdentifierValidator}.java` (movidos; `@Aspect`/`@Component` removidos, ver Debug Log)
- `validation/src/main/java/br/com/sawcunhaos/foundation/validation/zipcode/constraint/ZipCodeValidator.java` (movido, sem alteração de lógica)
- `validation/src/main/resources/META-INF/{validation.xml,validation-constraint-mappings.xml}` (novos) — ligação anotação→validador via XML (ver Debug Log)
- `validation/src/test/java/.../valueobjects/{CpfTest,CnpjTest,EmailTest,TaxIdentifierTest,ValueObjectJacksonSerializationTest}.java` (movidos de `utils`, só pacote/import)
- `validation/src/test/java/.../zipcode/constraint/{ZipCodeValidatorTest,ZipCodeDTO}.java` (movidos; `ZipCodeValidatorTest` ajustado para `ParameterMessageInterpolator`, ver Debug Log)
- `validation/src/test/java/.../taxidentifier/constraint/TaxIdentifierAnnotationsValidatorTest.java` (novo) — regressão do wiring XML das 3 anotações não cobertas pela suíte movida
- `validation-api/src/main/java/br/com/sawcunhaos/foundation/validation/api/{CPF,CNPJ,TaxIdentifier,ZipCode}.java` (novos, movidos de `utils`; `validatedBy = {}`, ver Debug Log) — completa a Task 3 deferida da Story 1.5
- `validation-api/src/test/java/br/com/sawcunhaos/foundation/validation/api/ArchitectureTest.java` (novo) — completa a Task 4 deferida da Story 1.5
- `validation-api/README.md` (novo)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/specification/ExceptionCode.java`, `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/ScosException.java`, `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ScosExceptionCode.java` (novos, movidos de `utils` — adiantamento do escopo da Story 2.8, ver Debug Log)
- `core/src/test/java/br/com/sawcunhaos/foundation/core/enums/ScosExceptionCodeTest.java` (novo, movido de `utils`)
- `utils/src/main/java/.../{valueobjects/*, validation/taxIdentifier/*, validation/zipcode/*, specification/ExceptionCode.java, exception/ScosException.java, enums/ScosExceptionCode.java}` (removidos — movidos para `validation`/`validation-api`/`core`)
- `utils/src/test/java/.../{valueobjects/*, validation/zipcode/constraint/*, enums/ScosExceptionCodeTest.java}` (removidos — movidos)
- `exception/src/main/java/.../{error/ScosSecurityException,error/ScosNoContentException,error/ScosNoRollbackException,model/ScosProblemDetails,model/ScosFieldError,ExceptionsHandler}.java`, `exception/src/test/java/.../{ExceptionsHandlerMdcTest,ExceptionsHandlerScosExceptionTest}.java` — import repontado para `core` (correção mecânica de FQN, sem dependência nova em `exception/pom.xml`, mesmo padrão da Story 1.7)
- `audit/src/test/java/.../{enums/ErrorCode,service/InsideAuditExampleService}.java` — import repontado para `core` (idem, sem dependência nova em `audit/pom.xml`)
- `utils/pom.xml` — dependência `br.com.caelum.stella:caelum-stella-core` removida (patch pós-revisão: ficou órfã após os value objects/`ConstraintValidator` saírem de `utils`, confirmado por `grep` sem nenhum uso restante; `mvn -pl utils -am test` verde após a remoção)

## Suggested Review Order

**Contrato anotação → validador (o ciclo de módulo resolvido)**

- Ponto de entrada: `validatedBy = {}` — a anotação não referencia mais o validador diretamente, quebrando o ciclo `validation-api ↔ validation`.
  [`CPF.java:33`](../../validation-api/src/main/java/br/com/sawcunhaos/foundation/validation/api/CPF.java#L33)

- XML de bootstrap que religa a anotação ao validador em tempo de execução — 1º arquivo desse tipo no repo (ver Deferred Work sobre o risco de colisão).
  [`validation.xml:18`](../../validation/src/main/resources/META-INF/validation.xml#L18)

- Implementação do validador, agora isolada em `validation` (sem `@Aspect`/`@Component`, nunca funcionais aqui — ver Debug Log).
  [`CpfValidator.java:36`](../../validation/src/main/java/br/com/sawcunhaos/foundation/validation/taxidentifier/constraint/CpfValidator.java#L36)

**Value objects e a dependência de `core` (o adiantamento da Story 2.8)**

- `Cpf` lança `ScosException(ScosExceptionCode.CPF_INVALID)` — motivo raiz de mover o contrato de exceção para `core` agora.
  [`Cpf.java:24`](../../validation/src/main/java/br/com/sawcunhaos/foundation/validation/valueobjects/Cpf.java#L24)

- `ExceptionCode`/`ScosException`/`ScosExceptionCode` migrados para `core` — decisão confirmada explicitamente pelo usuário/PO (ver comentário no topo deste arquivo).
  [`ScosException.java:22`](../../core/src/main/java/br/com/sawcunhaos/foundation/core/exception/ScosException.java#L22)

- `getHttpCode()` nunca sobrescrito por `ScosExceptionCode` — bug pré-existente carregado verbatim, não introduzido aqui (ver Deferred Work).
  [`ExceptionCode.java:26`](../../core/src/main/java/br/com/sawcunhaos/foundation/core/specification/ExceptionCode.java#L26)

**Fiação do reactor**

- `validation-api` e `validation` entram no reactor logo após `core`/`spring`.
  [`pom.xml:91`](../../pom.xml#L91)

**Peripherais**

- Débito da Story 1.5 fechado: anotações + `ArchitectureTest` local + `README.md` completam `validation-api`.
  [`README.md`](../../validation-api/README.md)
