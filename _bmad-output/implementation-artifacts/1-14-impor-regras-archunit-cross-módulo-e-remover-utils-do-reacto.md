# Story 1.14: Impor regras ArchUnit cross-módulo e remover `utils` do reactor

Status: done

<!-- baseline_commit: f41276ac847655f65aea408a4f7f96c0e2d54fbe -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero que o build falhe automaticamente se qualquer módulo violar a fronteira de dependência global,
Para que a decomposição não regrida silenciosamente.

## Acceptance Criteria

1. **Given** o módulo `archtest` (Story 1.6) e todos os módulos extraídos (Stories 1.5–1.13), **When** as regras cross-módulo são adicionadas, **Then** o build falha se algum módulo além de uma aplicação consumidora depender de `web`.
2. **And** o build falha se houver ciclo entre quaisquer dois módulos do reactor.
3. **And** após a última classe migrada, `scos-foundation-utils` é removido do reactor Maven.
4. **And** pendência conhecida, não bloqueante desta story: FR-19/AD-1 definem regras negativas explícitas só para `core`, `spring`, `*-api` e a proibição genérica de depender de `web` — não há regra declarada especificamente para o que `cache`/`jpa`/`feign`/`audit-api` **não podem** importar. A cobertura "100%" de FR-20 é satisfeita aqui pelas regras cross-módulo (ciclo, dependência de `web`) mais o próprio grafo de dependência Maven; se uma regra negativa específica para esses módulos for necessária, isso deve ser levantado com quem mantém o PRD/Architecture antes da implementação, não decidido ad-hoc nesta story.

## Tasks / Subtasks

- [x] Task 0: Confirmar pré-condição — todas as Stories 1.5 a 1.13 concluídas (todas as classes migradas para os módulos novos)
  - [x] Verificar no `sprint-status.yaml` que 1-5 até 1-13 estão `done` antes de iniciar; esta story depende de que **nenhuma classe reste em `utils`**
- [x] Task 1: Regra cross-módulo "nada depende de `web` exceto aplicações" (AC: #1)
  - [x] Adicionar em `archtest` (Story 1.6) uma classe de teste ArchUnit que falha se qualquer módulo do reactor (`core`, `spring`, `validation`, `cache`, `jpa`, `feign`, `audit`, `jdempotent`, os três `-api`, `privacy`) importar pacotes de `br.com.sawcunhaos.foundation.web`
- [x] Task 2: Regra cross-módulo "sem ciclo entre módulos" (AC: #2)
  - [x] Adicionar em `archtest` uma classe de teste ArchUnit de detecção de ciclo (`slices().matching(...).should().beFreeOfCycles()` ou equivalente) cobrindo todos os módulos do reactor
- [x] Task 3: Remover `utils` do reactor (AC: #3)
  - [x] Confirmar (via `grep`) que nenhuma classe restante em `utils/src/main/java` está sem módulo de destino migrado — o inventário congelado na Story 1.1 é a referência de conferência
  - [x] Remover `<module>utils</module>` de `pom.xml` raiz
  - [x] Remover a pasta `utils/` do repositório
  - [x] Remover qualquer `<dependency>scos-foundation-utils</dependency>` residual em `audit/pom.xml`, `exception/pom.xml`, `jdempotent/pom.xml` — na prática `exception` já não dependia mais de `utils` chegando nesta story: a Story 1.9 antecipou a migração de `ExceptionCode`/`ScosException`/`ScosExceptionCode` para `core` (decisão confirmada com o usuário, ver Completion Notes da 1.9), então a única dependência residual real encontrada em `exception` era `scos-foundation-core` faltando explicitamente (chegava transitivo via `utils`) — corrigida. `audit`/`jdempotent` já dependiam só dos módulos novos.
- [x] Task 4: Registrar a pendência conhecida (AC: #4)
  - [x] Deixar explícito nas Completion Notes que a ausência de regra negativa específica para `cache`/`jpa`/`feign`/`audit-api` é uma decisão consciente desta story, não uma omissão — e que qualquer regra negativa adicional para esses módulos exige alinhamento com quem mantém PRD/Architecture antes de ser implementada ad-hoc

## Dev Notes

- Esta é a Fase 5 do plano de origem: "remoção e documentação" — última fase antes do piso de documentação do Épico 4.
- **Ordem de execução (NFR1)**: esta story é a última do bloco de extração modular — só faz sentido depois que Stories 1.5 a 1.13 já moveram todas as classes. Rodar fora de ordem quebra a AC #3 (classe sem destino ainda em `utils`).
- Regras que citam **um módulo só** (ex.: "`core` não importa Spring", já criada na Story 1.7) não são repetidas aqui — só as regras que citam mais de um módulo entram em `archtest`, conforme o princípio já estabelecido na Story 1.6.
- A dependência residual de `exception` em `utils` (contrato de exceção) é esperada nesta altura — a extinção completa de `exception` só acontece nas Stories 2.8/2.9 do Épico 2, que dependem de `core` já existir (Story 1.7, já concluída neste ponto). Não forçar essa migração aqui, é fora do escopo do Épico 1.

### Project Structure Notes

- `archtest/src/test/java/` ganha as primeiras classes de teste reais (regra "sem depender de `web`", regra "sem ciclo").
- `utils/` é removido do repositório e de `pom.xml` raiz.
- Verificar `dependencyManagement` do `pom.xml` raiz por qualquer entrada residual de `scos-foundation-utils` a remover junto.

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#fase-5--remoção-e-documentação-1-dia]
- [Source: etc/doc/plano/plano-decomposicao-utils.md#9-como-impedir-que-o-utils-volte-a-crescer]
- [Source: _bmad-output/implementation-artifacts/1-1-congelar-o-inventário-classe-módulo.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-114-impor-regras-archunit-cross-módulo-e-remover-utils-do-reactor]

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- Primeira tentativa de `mvn -o -pl archtest -am test-compile` falhou em `audit`: `ScosLogDataSourceConfiguration`/`ScosAuditBatchConsumer` usam `io.micrometer.core.instrument.{MeterRegistry,Counter,DistributionSummary}` (`@Autowired(required = false)`), chegavam transitivamente via `scos-foundation-utils`'s `spring-boot-starter-actuator`. Corrigido adicionando `spring-boot-starter-actuator` explícito em `audit/pom.xml`. Re-run: BUILD SUCCESS.
- `exception/pom.xml` não declarava `scos-foundation-core` apesar de `ExceptionsHandler.java` importar `core.exception.ScosException`/`core.enums.ScosExceptionCode` diretamente — só ficou visível ao remover `utils` do reactor (chegava transitivo via `utils`, que também depende de `core`). Corrigido com dependência explícita.
- `LocaleService`/`ValueType` movidos de `utils` para `core` (destino já congelado no inventário da Story 1.1); 6 arquivos em `exception` (classe + 5 testes) e 1 em `audit` (`LocaleUtilsBean`, teste) tiveram o import repontado via `sed`.
- `AuditTestApplication.java` (teste) tinha um `@ComponentScan` apontando para o pacote agora vazio `br.com.sawcunhaos.foundation.utils.configuration.hibernate` — removido (inofensivo, mas enganoso).
- Mensagens i18n `scos_utils_messages.properties`/`scos_utils_messages_en.properties` (SCOS-001 a SCOS-008, casam com `ScosExceptionCode`) — confirmado via grep exaustivo (`spring.messages.basename`, `ResourceBundleMessageSource`, `setBasename`) que não há wiring nenhum dentro deste repositório; concluído que é um bundle público para apps consumidoras configurarem `spring.messages.basename`, preservado via `git mv` para `core/src/main/resources/` mantendo os nomes de arquivo originais.
- `utils/src/main/resources/mustaches/*.mustache` (13 templates estilo OpenAPI-Generator, não 11 — contagem inicial errada) — **CORREÇÃO PÓS-REVISÃO**: a primeira investigação rodou `grep -rln -i "mustache" --include="*.md" .` e o resultado incluiu `etc/doc/ideia/rfc9457-exception-compliance.md`, mas esse hit não foi aberto/lido antes de concluir "zero referências" — erro de execução, não de método. O Blind Hunter (revisão desta story) reabriu o arquivo e mostrou que a seção "Impacto na Geração de Controllers via Swagger (Mustache)" (linhas 232-270) documenta `api.mustache`/`apiController.mustache`/`apiDelegate.mustache`/`responseType.mustache` como um mecanismo de geração de controllers real e ativamente em uso por serviços consumidores (via OpenAPI Generator), não um artefato morto. Os 13 arquivos foram restaurados (`git restore --source=<baseline> -- utils/src/main/resources/mustaches/`) e o destino final foi levantado com o usuário em vez de decidido ad-hoc (para não repetir o mesmo erro): confirmado que o mecanismo é real e deve ser preservado, e a decisão do usuário foi criar um módulo novo dedicado. **Resolução**: novo módulo `codegen` (`scos-foundation-codegen`) criado — só recursos, zero código Java, zero dependência de runtime — hospedando os 13 templates em `codegen/src/main/resources/mustaches/`; registrado em `<modules>` e `dependencyManagement` do `pom.xml` raiz, com `README.md` próprio explicando o propósito e como um consumidor externo aponta o `templateDirectory` do `openapi-generator-maven-plugin` para o jar. Build completo (`mvn -o clean install -DskipTests`) confirma o jar do novo módulo empacota os 13 arquivos corretamente.
- `mvn -o clean install -DskipTests` no reactor completo: BUILD SUCCESS (rodado 2x — antes e depois da criação do módulo `codegen`).
- `mvn -o test` no reactor completo (com Docker disponível para os testcontainers de `audit`/`jdempotent`): todos os módulos passam, exceto `jdempotent` (`PrimeNumbersJdempotentDisableTest`/`PrimeNumbersJdempotentEnableTest`, `ContainerLaunchException: port is already allocated` nas portas fixas `6379`/`26379` do `docker-compose.yml` de teste). Confirmado via `git diff --stat <baseline>..HEAD -- jdempotent/` que o módulo está byte-a-byte idêntico ao baseline desta story — reproduzido de forma idêntica tanto no reactor completo quanto isolando `mvn -o -pl jdempotent test`, então não é regressão desta story; é reconfirmação da flakiness estrutural já registrada em `deferred-work.md` desde a Story 1.10 (portas fixas em vez de dinâmicas).
- `mvn -o -pl archtest test` (sem `-am`, contra os jars já instalados no `~/.m2` pelo `install` completo, para evitar que `-am` puxe `jdempotent` e pare no mesmo erro acima antes de chegar em `archtest`): `Tests run: 2, Failures: 0, Errors: 0` — as duas regras cross-módulo (`nothingDependsOnWeb`, `noCyclesBetweenModules`) confirmadas passando de fato, não só inferidas pela ausência de erro num log em modo `-q`.
- **3 revisores adversariais** (blind-hunter, edge-case-hunter, verification-gap) disparados contra o diff (`git diff <baseline>..HEAD`). O agente verification-gap falhou por limite de sessão da ferramenta antes de terminar; as checagens que ele faria (claim "zero referências" do mustache, se as regras ArchUnit realmente rodam e passam, se `exception` já não dependia de `utils`) foram refeitas diretamente. Achados dos outros dois, triados:
  - **intent_gap (loopback aplicado)**: a exclusão dos 13 templates `.mustache` estava errada — ver correção acima. Causa raiz: um `grep` que retornou um hit real (`etc/doc/ideia/rfc9457-exception-compliance.md`) não foi aberto antes de concluir "zero referências".
  - **patch (corrigido nesta story)**: comentário impreciso em `audit/pom.xml` (dizia que `LocaleService` chegava transitivamente via `privacy`, que na verdade não depende de `core`); CRLF ausente em `ArchitectureTest.java` (único arquivo `.java` novo desta story sem terminador de linha consistente com o resto do repo); duas steps de CI (`Archive utils module artifacts`, `Publish utils module security report`) em `.github/workflows/build.yml` apontando para `utils/target/`, um diretório que não existe mais.
  - **reject (verificado e descartado)**: exclusão `br.com.insidesoftwares.jdempotent:redis` removida de `audit/pom.xml` junto com o bloco `<dependency>scos-foundation-utils</dependency>` inteiro — confirmado que esse groupId não aparece em nenhum pom.xml vivo do repositório, então a exclusão não protegia nada que ainda exista; citação "AD-5" no Javadoc de `ArchitectureTest.java` — confirmado como decisão de arquitetura real e documentada (`ARCHITECTURE-SPINE.md`), não uma citação inventada.
  - **defer (registrado em `deferred-work.md`)**: docs de consumidor (`README.md` raiz, `audit/README.md`, `etc/doc/skills/*`, `etc/doc/commit-convention.md`) continuam descrevendo `scos-foundation-utils` como módulo existente — sinalizado como bloqueante para o piso de documentação do Épico 4, não corrigido aqui (reescrita de escala substancial, fora da AC/Tasks desta story); CI nunca ganhou steps de archive/security-report para os 8 módulos novos do Épico 1 (gap pré-existente desde a Story 1.6, não introduzido por esta story); as duas regras cross-módulo de `archtest` não enxergam código de `src/test/java` de nenhum módulo (limitação estrutural do ArchUnit/test-jar publishing); `ValueType` tem zero consumidores no repo inteiro, mas seu destino (`core`) já estava congelado no inventário da Story 1.1 — não é uma decisão nova desta story, só registrado para visibilidade futura.

### Completion Notes List

- AC #1 e #2: `archtest/src/test/java/.../ArchitectureTest.java` criado com duas regras: `nothingDependsOnWeb` (nenhum módulo fora de `web` pode importar `br.com.sawcunhaos.foundation.web..`) e `noCyclesBetweenModules` (`slices().matching("br.com.sawcunhaos.foundation.(*)..")` livre de ciclos). `archtest/pom.xml` ganhou dependências de teste explícitas para todos os módulos que precisam estar no classpath analisado (`core`, `spring`, `validation`, `cache`, `jpa`, `web`, `feign`, mais os já existentes `privacy`, `exception`, `audit`, `jdempotent`, os três `-api`).
- AC #3: `utils` removido do reactor — `<module>utils</module>` e a entrada `scos-foundation-utils` do `dependencyManagement` removidos de `pom.xml` raiz; pasta `utils/` deletada por completo (histórico preservado, incluindo os `git mv`/renames detectados pelo git para `LocaleService`/`ValueType`/os dois `.properties`, que foram movidos para `core`, e os 13 templates `.mustache`, movidos para o novo módulo `codegen` — ver correção pós-revisão no Debug Log).
- Efeito colateral desta story: novo módulo `codegen` (`scos-foundation-codegen`) criado — não fazia parte do plano original da story (nasceu da correção do erro de exclusão dos templates mustache), registrado em `<modules>`/`dependencyManagement` do `pom.xml` raiz junto com o resto do AC #3.
- AC #4: pendência documentada — não existe regra ArchUnit negativa específica dizendo o que `cache`/`jpa`/`feign`/`audit-api` **não podem** importar (só a regra genérica "nada depende de `web`" e a regra de ciclo). Decisão consciente desta story: qualquer regra negativa adicional para esses módulos precisa de alinhamento com quem mantém PRD/Architecture antes de ser implementada ad-hoc.
- Desvio em relação à Dev Note original da story (linha 43, "a dependência residual de `exception` em `utils` é esperada nesta altura"): essa nota presumia que a extinção de `exception` só aconteceria no Épico 2 (Stories 2.8/2.9). Na prática isso já tinha sido antecipado na Story 1.9 (decisão confirmada com o usuário: mover `ExceptionCode`/`ScosException`/`ScosExceptionCode` de `utils` para `core`), então `exception` chegou nesta story já sem depender de `utils` para o contrato de exceção — a única lacuna real encontrada foi `scos-foundation-core` não declarado explicitamente (Errors and Fixes #8 acima) e o import de `LocaleService`.
- 3ª dependência transitiva oculta desta linha de stories descoberta em `audit` (`spring-boot-starter-actuator`/micrometer) — mesmo padrão dos casos anteriores (`exception` × 2 em Stories 1.12/1.14): módulo nunca declarou uma dependência que só existia porque `utils` a carregava transitivamente.

### File List

- `pom.xml` (raiz) — removido `<module>utils</module>` e a entrada `scos-foundation-utils` de `dependencyManagement`; adicionado `<module>codegen</module>` e a entrada `scos-foundation-codegen`
- `archtest/pom.xml` — dependências de teste reescritas (utils removido; core/spring/validation/cache/jpa/web/feign adicionados)
- `archtest/src/test/java/br/com/sawcunhaos/foundation/archtest/ArchitectureTest.java` (novo)
- `codegen/pom.xml` (novo módulo — só recursos, zero código Java)
- `codegen/README.md` (novo)
- `codegen/src/main/resources/mustaches/*.mustache` (13 arquivos, movidos de `utils`)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/specification/LocaleService.java` (movido de `utils`)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/ValueType.java` (movido de `utils`)
- `../../core/src/main/resources/scos_message/scos_utils_messages.properties` (movido de `utils`)
- `../../core/src/main/resources/scos_message/scos_utils_messages_en.properties` (movido de `utils`)
- `exception/pom.xml` — adicionada dependência explícita `scos-foundation-core`; removida `scos-foundation-utils`
- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` — import de `LocaleService` repontado para `core`
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerInternalErrorTest.java` — import repontado
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerScosExceptionTest.java` — import repontado
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerAccessDeniedTest.java` — import repontado
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerMdcTest.java` — import repontado
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerValidationTest.java` — import repontado
- `audit/pom.xml` — removida `scos-foundation-utils`; adicionada `spring-boot-starter-actuator` explícita; comentário sobre origem transitiva de `LocaleService` corrigido pós-revisão
- `audit/src/test/java/br/com/sawcunhaos/foundation/audit/configuration/LocaleUtilsBean.java` — import repontado
- `audit/src/test/java/br/com/sawcunhaos/foundation/audit/AuditTestApplication.java` — `@ComponentScan` entry para pacote vazio de `utils` removida
- `.github/workflows/build.yml` — removidas as 2 steps de CI que apontavam para `utils/target/`
- `_bmad-output/implementation-artifacts/deferred-work.md` — 5 entradas novas (ver Debug Log)
- `utils/` (pasta inteira removida do repositório)

## Suggested Review Order

**As duas regras cross-módulo novas (AC #1, #2)**

- `nothingDependsOnWeb`/`noCyclesBetweenModules` — o coração da story; confirmado rodando de fato (`Tests run: 2, Failures: 0`), não só compilando.
  [`ArchitectureTest.java:33`](../../archtest/src/test/java/br/com/sawcunhaos/foundation/archtest/ArchitectureTest.java#L33)

**O erro pego pela revisão e sua correção**

- Templates mustache quase apagados por engano (grep achou a evidência, mas não foi lida) — decisão final (novo módulo `codegen`) tomada com o usuário, não decidida sozinha.
  [`codegen/pom.xml`](../../codegen/pom.xml) · [`codegen/README.md`](../../codegen/README.md)

**Dependências transitivas ocultas que a remoção de `utils` expôs**

- `exception` sem `scos-foundation-core` explícito.
  [`exception/pom.xml:91`](../../exception/pom.xml#L91)
- `audit` sem `spring-boot-starter-actuator` explícito (micrometer).
  [`audit/pom.xml:115`](../../audit/pom.xml#L115)

**Remoção do reactor**

- `utils` sai de `<modules>`/`dependencyManagement`; `codegen` entra nos dois.
  [`pom.xml:84`](../../pom.xml#L84)
