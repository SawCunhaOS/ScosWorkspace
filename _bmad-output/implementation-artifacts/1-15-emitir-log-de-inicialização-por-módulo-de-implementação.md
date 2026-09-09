# Story 1.15: Emitir log de inicialização por módulo de implementação

Status: done

<!-- baseline_commit: 2bc2e9bc00c4ca8153b5a31081a1ea2cff00b6cf -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor operando em produção,
Eu quero um log `INFO` na subida de cada módulo de implementação informando quantas classes anotadas foram encontradas,
Para detectar um módulo `-api` usado sem a implementação correspondente no classpath.

## Acceptance Criteria

1. **Given** uma aplicação consumidora com anotações de `jdempotent-api`/`audit-api`/`validation-api` no classpath, **When** a aplicação sobe com o módulo de implementação correspondente presente, **Then** um log `INFO` é emitido contando quantas classes anotadas foram encontradas.
2. **And** módulos `*-api` não emitem esse log (não têm lógica de runtime).
3. **And** cada README de módulo `-api` abre com a frase "este artefato não executa nada; a implementação é `scos-foundation-<x>`".

## Tasks / Subtasks

- [x] Task 1: Listener de contagem no módulo `jdempotent` (AC: #1)
  - [x] Implementar um `ApplicationListener<ApplicationReadyEvent>` (ou reaproveitar mecanismo de startup já existente no módulo, se houver) que faz scan do classpath da aplicação consumidora por classes anotadas com `@JdempotentResource`/`@JdempotentId` e loga em `INFO` a contagem encontrada
- [x] Task 2: Listener de contagem no módulo `audit` (AC: #1)
  - [x] Mesmo mecanismo, contando classes anotadas com `@Auditable`
- [x] Task 3: Listener de contagem no módulo `validation` (AC: #1) — **implementado em `exception`, não em `validation`; ver Debug Log**
  - [x] Mesmo mecanismo, contando campos/classes anotados com `@CPF`/`@CNPJ`/`@TaxIdentifier`/`@ZipCode` — este é o caso menos direto dos três, porque a validação Bean Validation já faz seu próprio scan implícito; o log aqui é só observabilidade (contagem visível), não integração nova com o mecanismo de validação existente
- [x] Task 4: Confirmar que os módulos `*-api` não emitem log (AC: #2)
  - [x] `audit-api`, `jdempotent-api`, `validation-api` (Story 1.5) não recebem nenhum listener — são só anotações, sem lógica de runtime, por definição
- [x] Task 5: Confirmar a frase padrão nos READMEs dos `*-api` (AC: #3)
  - [x] Verificar que os READMEs criados na Story 1.5 já abrem com "este artefato não executa nada; a implementação é `scos-foundation-<x>`" (a Story 1.5 já pede essa frase); se algum README não seguir o padrão exato, corrigir aqui

## Dev Notes

- Depende da Story 1.5 (`*-api` criados) já concluída — o log detecta justamente o cenário "anotação do `-api` presente, implementação ausente ou vice-versa".
- Modo de falha que este log mitiga (citação do plano de origem): "depender só do `-api` compila e não faz nada em tempo de execução — sem o módulo de implementação no classpath, não há listener nem aspecto para ler a anotação. Nenhum erro, nenhum aviso." O log de contagem é o sinal visível: zero classes anotadas com o módulo ligado, ou anotações presentes sem o módulo, viram sinal detectável em produção.
- Esta é a última story do Épico 1 — depende implicitamente de `jdempotent` e `audit` já estarem repontados para os `-api` correspondentes (Story 1.5) para o scan ter algo consistente para contar.
- Não é escopo desta story mudar o comportamento funcional de `jdempotent`/`audit`/`validation` — só adicionar o log de contagem na subida.

### Project Structure Notes

- Arquivos novos: um listener de startup por módulo de implementação (`jdempotent`, `audit`, `validation`), seguindo o padrão que já existe no repo para listeners on-startup (`ScosOnStartupListener`/`ScosStartupListener`, migrados para `spring` na Story 1.8 — usar o mesmo padrão de extensão, se aplicável, ou `ApplicationListener<ApplicationReadyEvent>` direto).
- Nenhum arquivo em `audit-api`, `jdempotent-api`, `validation-api` é tocado (AC #2 exige ausência de lógica ali).

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#o-modo-de-falha-a-documentar]
- [Source: _bmad-output/implementation-artifacts/1-5-criar-módulos-api-e-mover-as-anotações-de-contrato.md]
- [Source: _bmad-output/implementation-artifacts/1-8-extrair-o-módulo-spring.md] (padrão `ScosOnStartupListener`/`ScosStartupListener`)
- [Source: _bmad-output/planning-artifacts/epics.md#story-115-emitir-log-de-inicialização-por-módulo-de-implementação]

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- **Task 3 replanejada, decisão do usuário**: `validation/pom.xml` documenta explicitamente, desde a Story 1.9, a decisão de não ter Spring/AspectJ nesse módulo ("No Spring, no AspectJ: CnpjValidator/CpfValidator/TaxIdentifierValidator carried unused @Aspect/@Component from utils... dropped on the move rather than pulling Spring/AspectJ into this module"). Implementar a Task 3 ao pé da letra (um `ApplicationListener` dentro de `validation`) reverteria essa decisão. Perguntado ao usuário antes de agir; decisão: manter `validation` sem Spring e implementar o listener de contagem em outro módulo que já tem Spring. Escolhido `exception`: já depende de `spring-boot-starter-validation` e trata `MethodArgumentNotValidException` (falhas de Bean Validation), então tem afinidade de domínio direta com os campos `@CPF`/`@CNPJ`/`@TaxIdentifier`/`@ZipCode`. Adicionada dependência nova `scos-foundation-validation-api` (módulo de contrato puro, zero deps) a `exception/pom.xml`.
- Mecanismo de scan escolhido: `AutoConfigurationPackages.get(beanFactory)` (API padrão do Spring Boot para uma lib/módulo descobrir o(s) pacote(s) base da aplicação consumidora sem configuração extra do lado do consumidor — o mesmo mecanismo que `@EntityScan` usa por padrão) + `ClassPathScanningCandidateComponentProvider` com um `TypeFilter` que aceita qualquer classe, seguido de `Class.forName(name, false, classLoader)` (verifica/liga a classe **sem** rodar `<clinit>`) para inspecionar reflexivamente métodos/campos/o próprio tipo em busca da anotação. Zero dependência nova de biblioteca de scanning (nada de Reflections/ClassGraph) — só Spring Boot, já presente nos 3 módulos.
- Bug de compilação pego na primeira tentativa nos 3 listeners: `catch (ClassNotFoundException | NoClassDefFoundError | LinkageError e)` não compila — `NoClassDefFoundError` é subclasse de `LinkageError`, alternativas de multi-catch não podem estar relacionadas por herança. Corrigido removendo `NoClassDefFoundError` (já coberto por `LinkageError`) nos 3 arquivos.
- Lógica de contagem extraída para um método `countAnnotatedElements(List<String> basePackages)` package-visible em cada listener, separado de `onApplicationEvent(ApplicationReadyEvent)`, para ser testável sem precisar subir um `ApplicationContext` real.
- `mvn -o -pl jdempotent test` (suíte completa, não só o teste novo): `Tests run: 40` (38 pré-existentes + 2 novos), `Failures: 0`, `Errors: 3` — os mesmos 3 erros de flakiness pré-existente do Docker Compose de portas fixas do módulo `jdempotent` (já documentado em `deferred-work.md` desde a Story 1.10, reconfirmado na Story 1.14); nenhuma regressão nova.
- `mvn -o -pl exception test` (suíte completa): `Tests run: 12` em 7 classes, `Failures: 0, Errors: 0` em todas — confirma que a nova dependência `scos-foundation-validation-api` e o novo listener não quebraram nada.
- `mvn -o -pl audit test` (suíte completa, com Docker/Testcontainers Postgres+MySQL): `Tests run: 56` em 16 classes, `Failures: 0, Errors: 0` em todas — confirma que o novo listener bean não quebra o bootstrap do contexto Spring existente em nenhum dos testes de integração do módulo.
- `mvn -o clean install -DskipTests` no reactor completo: BUILD SUCCESS.
- Task 4/5: zero mudança necessária — confirmado via `grep` que nenhum dos 3 módulos `-api` tem `@Component`/`ApplicationListener`, e os 3 READMEs já abrem com a frase exata exigida pela AC #3 (herdada da Story 1.5).
- **3 revisores adversariais** (blind-hunter, edge-case-hunter, verification-gap) disparados contra o diff. Achado mais grave, de longe, encontrado independentemente pelo edge-case-hunter e reconfirmado pelo verification-gap: `AuditableAnnotationCountListener`/`JdempotentAnnotationCountListener` eram só `@Component`, mas `audit` e `jdempotent` são documentados (`etc/doc/skills/scos-audit-config/SKILL.md`, `scos-jdempotent-config/SKILL.md`: "Auto-configura por `AutoConfiguration.imports`") como módulos que **não** dependem do `@ComponentScan` da aplicação consumidora — sobem via `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`. Um `@Component` sozinho nesses 2 módulos nunca seria instanciado numa app consumidora real: o log prometido pela AC #1 simplesmente nunca apareceria, silenciosamente. Prova concreta: o próprio `JdempotentTestApplication` (harness de teste do módulo) exclui via regex exatamente o pacote onde o listener foi criado (`br.com.sawcunhaos.foundation.jdempotent.core.*`), e nenhum dos 2 novos testes sobe um `ApplicationContext` real (só chamam `countAnnotatedElements(...)` direto), então esse buraco nunca teria sido pego por nenhum teste do diff original. **Corrigido**: as 2 classes foram adicionadas ao `AutoConfiguration.imports` de cada módulo, no mesmo padrão que todo outro bean desses 2 módulos já usa. Verificado de verdade (não só suposto): re-rodei um teste de `jdempotent` e a suíte completa de `audit`, e vi a linha de log real disparar a partir de um `ApplicationReadyEvent` genuíno num contexto Spring vivo — `JdempotentAnnotationCountListener: found 1 @JdempotentResource/@JdempotentId usage(s)...` e `AuditableAnnotationCountListener: found 4 @Auditable usage(s)...`. `exception` não precisou desse fix — não tem `AutoConfiguration.imports` nenhum, ativa por `@ComponentScan(basePackages={"br.com.sawcunhaos"})` mesmo (documentado em `scos-exception-config/SKILL.md`), que é o mecanismo correto e já estabelecido para esse módulo.
- Outros achados do blind-hunter, corrigidos nos 3 listeners: (1) `AutoConfigurationPackages.get(...)` sem tratamento — lança `IllegalStateException` se `@EnableAutoConfiguration` nunca rodou (bootstrap não-padrão), e isso propagaria para fora de `onApplicationEvent`, potencialmente abortando a subida da app consumidora por causa de uma feature de observabilidade; envolvido em `try/catch`, loga `WARN` e sai sem contar. (2) Nenhum dedup de classes escaneadas entre `basePackages` — se `AutoConfigurationPackages.get()` retornar pacotes aninhados/sobrepostos (possível conforme o próprio Javadoc de `AutoConfigurationPackages.register()`), a mesma classe seria contada mais de uma vez; corrigido coletando nomes de classe num `Set` antes de contar. (3) `catch (... | LinkageError e)` logava em `DEBUG`, escondendo um bug real numa classe genuinamente quebrada da app consumidora sem nenhum sinal visível; subido para `WARN`.
- Achado do edge-case-hunter, corrigido: nem `AuditableAnnotationCountListener` nem `JdempotentAnnotationCountListener` tinham `@ConditionalOnProperty`, diferente de todo outro bean de configuração desses 2 módulos (`ScosAuditConfiguration`/`ScosJdempotentConfig`, ambos condicionados a `scos.audit.enabled`/`scos.jdempotent.enabled`). Adicionado o mesmo gate a cada listener, para respeitar a intenção de uma app consumidora que desabilite o módulo explicitamente.
- Achados verificados e rejeitados com evidência: `@Auditable` tem `@Target({TYPE, METHOD})` (sem `FIELD`, então não há sub-contagem por campo); `@CPF`/`@CNPJ`/`@TaxIdentifier`/`@ZipCode` têm `@Target({FIELD, PARAMETER})` (sem `METHOD`, então não há sub-contagem por getter); o "cabeçalho de licença malformado" apontado é na verdade a convenção já estabelecida do repositório inteiro (confirmado contra dezenas de outros arquivos nesta sessão); o pacote `jdempotent.core.listener` segue a convenção já existente do próprio módulo (`core.aspect`, `core.callback`, etc.), não é uma inconsistência; a diferença AssertJ (em `jdempotent`) vs JUnit puro (em `audit`/`exception`) reflete exatamente o que está transitivamente disponível em cada módulo, não uma inconsistência; `SecurityException` de `SecurityManager` é impossível neste projeto — `SecurityManager` foi **removido** do JDK a partir da versão 24 (JEP 486), e este reactor roda em Java 25.
- Achados adiados para `deferred-work.md` (não corrigidos nesta story — engenharia maior, fora de proporção para a última story do épico): classes/interfaces abstratas ficam invisíveis ao scan (`ClassPathScanningCandidateComponentProvider` só retorna candidatos concretos — um `@Auditable` numa entidade base abstrata nunca seria contado); custo de performance do scan completo (`Class.forName` + reflexão em toda classe do(s) pacote(s) base, em toda subida de app, sem cache/opt-out/amostragem — real, mas uma reescrita seria não-trivial: a alternativa mais óbvia, `AnnotationMetadata` baseado em ASM do próprio Spring, não expõe anotação em campo, então não resolve `@JdempotentId`/`@CPF` etc. sem um visitor ASM customizado); duplicação de código entre os 3 listeners quase idênticos (tradeoff deliberado, documentado, para não criar um módulo compartilhado só para isto).
- Lacuna de verificação reconhecida (achado do verification-gap): `ValidationAnnotationCountListenerTest` só testa `countAnnotatedElements(...)` diretamente — `exception` não tem nenhum `@SpringBootTest` neste repositório, então, diferente de `jdempotent`/`audit` (onde o log real foi observado disparando num `ApplicationReadyEvent` genuíno), não há nenhuma evidência neste repositório de que `ValidationAnnotationCountListener` de fato sobe como bean e dispara em um contexto Spring real. O mecanismo (`@ComponentScan(basePackages={"br.com.sawcunhaos"})`) já é usado com sucesso por `ExceptionsHandler` (`@ControllerAdvice`) neste módulo, então a confiança é alta, mas fica registrado como lacuna honesta, não como "testado".

### Completion Notes List

- AC #1: 3 listeners `ApplicationListener<ApplicationReadyEvent>` novos — `JdempotentAnnotationCountListener` (jdempotent), `AuditableAnnotationCountListener` (audit), `ValidationAnnotationCountListener` (exception, não validation — ver Debug Log). Cada um faz `AutoConfigurationPackages.get(...)` + scan de classpath + reflexão, e loga em `INFO` a contagem de usos encontrados.
- AC #2: satisfeita por construção — nenhum arquivo em `audit-api`/`jdempotent-api`/`validation-api` foi tocado.
- AC #3: satisfeita sem mudança — os 3 READMEs já abriam com a frase exigida desde a Story 1.5.
- Desvio da Task 3/Dev Notes original: a story presumia o listener de `validation` dentro do próprio módulo `validation`, seguindo "o mesmo mecanismo" das outras duas. Na prática, `validation` é deliberadamente livre de Spring desde a Story 1.9, e essa restrição não foi reavaliada nem no planejamento desta story nem no `epics.md`. Resolvido com o usuário: o listener existe (a contagem funciona, testada), mas vive em `exception`, não em `validation`.
- Correção pós-revisão mais importante: `audit`/`jdempotent` precisaram de registro explícito em `AutoConfiguration.imports` — um `@Component` sozinho nunca seria descoberto numa app consumidora real desses 2 módulos (eles não dependem de `@ComponentScan` do lado do consumidor). Ver Debug Log para o achado completo e a correção.

### File List

- `jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` — adicionada entrada para `JdempotentAnnotationCountListener`
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/listener/JdempotentAnnotationCountListener.java` (novo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/listener/JdempotentAnnotationCountListenerTest.java` (novo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/listener/sample/SampleJdempotentUsage.java` (novo, fixture)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/listener/empty/SampleNoJdempotentUsage.java` (novo, fixture)
- `audit/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` — adicionada entrada para `AuditableAnnotationCountListener`
- `audit/src/main/java/br/com/sawcunhaos/foundation/audit/listener/AuditableAnnotationCountListener.java` (novo)
- `audit/src/test/java/br/com/sawcunhaos/foundation/audit/listener/AuditableAnnotationCountListenerTest.java` (novo)
- `audit/src/test/java/br/com/sawcunhaos/foundation/audit/listener/sample/SampleAuditableUsage.java` (novo, fixture)
- `audit/src/test/java/br/com/sawcunhaos/foundation/audit/listener/empty/SampleNoAuditableUsage.java` (novo, fixture)
- `exception/pom.xml` — adicionada dependência `scos-foundation-validation-api`
- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/listener/ValidationAnnotationCountListener.java` (novo)
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/listener/ValidationAnnotationCountListenerTest.java` (novo)
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/listener/sample/SampleValidationUsage.java` (novo, fixture)
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/listener/empty/SampleNoValidationUsage.java` (novo, fixture)

## Suggested Review Order

**O bug mais grave da revisão, e a correção**

- `@Component` sozinho não bastava em `audit`/`jdempotent` — precisava de registro em `AutoConfiguration.imports`, senão o listener nunca sobe numa app consumidora real.
  [`audit/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`](../../audit/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports)
  [`jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`](../../jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports)

**Os 3 listeners (mesma lógica, 3 lugares)**

- Mecanismo de scan + as 4 correções pós-revisão (try/catch em `AutoConfigurationPackages.get()`, dedup via `Set`, log level do catch, `@ConditionalOnProperty`).
  [`JdempotentAnnotationCountListener.java`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/listener/JdempotentAnnotationCountListener.java)
  [`AuditableAnnotationCountListener.java`](../../audit/src/main/java/br/com/sawcunhaos/foundation/audit/listener/AuditableAnnotationCountListener.java)
  [`ValidationAnnotationCountListener.java`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/listener/ValidationAnnotationCountListener.java)

**O desvio de escopo (Task 3)**

- Listener de `@CPF`/`@CNPJ`/`@TaxIdentifier`/`@ZipCode` vive em `exception`, não em `validation` — decisão do usuário para não reverter a política "sem Spring" da Story 1.9.
  [`exception/pom.xml:103`](../../exception/pom.xml#L103)
