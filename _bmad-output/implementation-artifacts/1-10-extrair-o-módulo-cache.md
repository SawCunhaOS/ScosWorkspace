# Story 1.10: Extrair o módulo `cache`

Status: done

<!-- baseline_commit: 594bbf8f3030c13e8bdc4f48e268d773733c1286 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como time consumidor que usa cache Redis,
Eu quero um módulo `cache` isolado,
Para não herdar JPA ao habilitar apenas cache.

## Acceptance Criteria

1. **Given** `PolymorphicRedisSerializer` e demais classes de `configuration/cache/*` do inventário, **When** o módulo `cache` é extraído dependendo apenas de `core`, **Then** `cache` compila isoladamente e os testes migrados permanecem verdes.
2. **And** a extração ocorre em 2 commits separados.

## Tasks / Subtasks

- [x] Task 1: Commit 1 — mover as classes de `configuration/cache/*` (AC: #1)
  - [x] Criar módulo Maven `scos-foundation-cache`, pacote raiz `br.com.sawcunhaos.foundation.cache`, dependendo só de `core` + `spring-boot-starter-cache` + `spring-boot-starter-data-redis` (+ 4 dependências adicionais inevitáveis, ver Debug Log)
  - [x] Mover: `utils/src/main/java/.../configuration/cache/PolymorphicRedisSerializer.java`, `ScosCacheConfiguration.java`, `ScosCacheKeyGenerator.java`, `configuration/cache/properties/ScosCacheModel.java`, `ScosCacheProperties.java`
  - [x] `jackson-dataformat-smile` acompanha `PolymorphicRedisSerializer` para este módulo (é a única classe que a usa) — traz `tools.jackson.core:jackson-databind` transitivamente (`SmileMapper` estende `ObjectMapper`), sem precisar declará-lo à parte
  - [x] Mover testes correspondentes, se existentes — **nenhum existia**: busca no repo inteiro antes da migração não encontrou teste próprio para nenhuma das 5 classes (confirmado, não é lacuna introduzida por esta story)
  - [x] Commit isolado: só mover/renomear pacote, zero mudança de lógica — **com um ajuste mecânico obrigatório no mesmo commit**: `jdempotent` importava `PolymorphicRedisSerializer` de `utils.configuration.cache` (único uso de `utils` nesse módulo); o import e a dependência Maven foram repontados para `scos-foundation-cache` no mesmo commit, senão o reactor não compilaria entre um commit e outro. Ver Debug Log.
- [x] Task 2: Commit 2 — ajustar o que precisar (AC: #2)
  - [x] Aplicar separadamente qualquer ajuste de comportamento necessário; documentar se não houver nenhum — **nenhum ajuste de comportamento no código movido**; os ajustes desta task são só de composição de classpath (dependências de teste/limpeza), documentados em detalhe no Debug Log
  - [x] **Não antecipar** a correção de allowlist do `PolymorphicRedisSerializer` (`Class.forName` sobre valor vindo do Redis) nesta story — é a Story 3.16 (Épico 3, FR32) que faz essa correção de segurança; esta story só move o código como está hoje — **confirmado**: `PolymorphicRedisSerializer.deserialize()` idêntico ao original, nenhuma allowlist adicionada

## Dev Notes

- Depende da Story 1.7 (`core`) já concluída.
- **Achado de segurança relevante para quem for depois**: o plano de origem já sinaliza que `PolymorphicRedisSerializer` faz `Class.forName` sobre valor vindo do Redis sem allowlist — "é aqui que aterrissa a correção de allowlist apontada no review de segurança." Esta story move o código **sem corrigir** a vulnerabilidade (é escopo do FR32/Story 3.16, Épico 3) — não confundir "mover" com "corrigir": manter o comportamento idêntico é o próprio objetivo do AC #1/#2 (NFR4).
- Fase 4 do plano de origem: `cache` é o terceiro módulo folha a sair (depois de `spring`, `validation`).

### Project Structure Notes

- Módulo Maven novo: `cache/` — depende de `core`, `spring-boot-starter-cache`, `spring-boot-starter-data-redis` (+ `spring-cloud-context`, `jakarta.validation-api`, `jackson-dataformat-smile`, `lombok`; ver Debug Log).
- `utils/` perde as classes de `configuration/cache/*` e, no commit 2, as dependências `spring-boot-starter-data-redis`/`spring-data-redis`/`jackson-dataformat-smile` que ficaram órfãs (nenhuma outra classe de `utils` fala com Redis ou usa Smile).
- `pom.xml` raiz ganha `<module>cache</module>` (logo após `validation`, antes de `privacy`/`utils`) + `dependencyManagement` para `scos-foundation-cache`.
- `jdempotent` troca a dependência `scos-foundation-utils` por `scos-foundation-cache` (único uso de `utils` ali era `PolymorphicRedisSerializer`) — alinha com o grafo alvo do AD-1 (`jdempotent → core, jdempapi, cache, privacy`) antes mesmo da Story 1.14 remover `utils` do reactor.

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#scos-foundation-cache]
- [Source: _bmad-output/planning-artifacts/epics.md#story-110-extrair-o-módulo-cache]
- [Source: _bmad-output/planning-artifacts/epics.md#story-316-adicionar-allowlist-de-tipos-no-polymorphicredisserializer]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/ARCHITECTURE-SPINE.md#ad-1] (grafo alvo `jdempotent → core, jdempapi, cache, privacy`)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- **Dependências de `cache/pom.xml` além de `core`/`spring-boot-starter-cache`/`spring-boot-starter-data-redis` citadas no Dev Notes**: compilação exigiu 4 adicionais, nenhuma delas viola AC #1 (nenhuma é JPA/Servlet):
  - `org.springframework.cloud:spring-cloud-context` — `ScosCacheModel`/`ScosCacheProperties` usam `@RefreshScope` (reload dinâmico via Spring Cloud Config). Mais estreita que o `spring-cloud-starter` completo usado em `utils`/`jdempotent` (sem `spring-cloud-commons`, sem `spring-security-crypto`/`bouncycastle` transitivos) — só o necessário para a anotação.
  - `jakarta.validation:jakarta.validation-api` — `@NotBlank`/`@NotNull`/`@Min`/`@Valid` nos dois POJOs de propriedade; só a anotação, sem implementação (mesma decisão de `validation/pom.xml` para `jakarta.persistence-api`: contrato em tempo de compilação, a implementação é responsabilidade de quem consome).
  - `tools.jackson.dataformat:jackson-dataformat-smile` — já previsto no Dev Notes/Task 1; confirmado que traz `jackson-databind` transitivamente (o pom do artefato declara a dependência), então não precisou ser listado à parte.
  - `org.projectlombok:lombok` (`optional`) — `@Data`/`@Slf4j`/`@RequiredArgsConstructor` no código movido.
  - Todas as 4 já eram gerenciadas transitivamente via `scos-bom` (spring-cloud-dependencies/spring-boot-dependencies importados no pai) — nenhuma versão explícita precisou ser fixada em `cache/pom.xml`.
- **Ajuste mecânico obrigatório dentro do próprio Commit 1 (não um "ajuste de comportamento" da Task 2)**: `jdempotent/src/main/java/.../redis/configuration/ScosJdempotentRedisConfiguration.java` importava `PolymorphicRedisSerializer` de `br.com.sawcunhaos.foundation.utils.configuration.cache` — único uso de `scos-foundation-utils` em todo o módulo `jdempotent` (confirmado por busca; nenhuma outra classe main/test referencia `foundation.utils`). Sem repontar esse import e trocar a dependência Maven (`scos-foundation-utils` → `scos-foundation-cache`) no mesmo commit da move, o reactor não compilaria entre os dois commits — mesma categoria de ajuste que a Story 1.8 tratou como "mecânico", não "comportamento" (mudança de FQN é consequência direta do mover, não uma decisão de design nova). A troca de dependência também antecipa parte do grafo alvo do AD-1 (`jdempotent → core, jdempapi, cache, privacy`, sem `utils`).
- **Regressão real encontrada e corrigida ainda dentro da sessão, antes de qualquer commit** (o estado quebrado transitório não ficou no código final — a correção, sim, permanece e está registrada no File List; a nota abaixo documenta a trilha de decisão): remover a dependência `scos-foundation-utils` de `jdempotent` também removeu, por tabela, o `spring-boot-starter-web` que `utils` trazia transitivamente. O módulo de teste `jdempotent/src/test/.../redis/test/app/` (`JdempotentTestApplication` + `PrimeNumbersController` + `CustomExceptionHandler`) é uma app Spring Boot de mentira só para os testes de integração, e `CustomExceptionHandler extends ResponseEntityExceptionHandler` (spring-webmvc) — nenhuma classe de produção usa `org.springframework.web.*` em `jdempotent` (confirmado por busca), só esse harness de teste. `mvn -pl jdempotent -am test` falhou com `FileNotFoundException` na classe do Spring MVC até eu adicionar `spring-boot-starter-web` como dependência **de teste** em `jdempotent/pom.xml` (Commit 2 — é consequência da divisão, não do próprio mover, então não cabia no Commit 1).
- **Segunda regressão, mesma causa raiz, corrigida em seguida**: com o webmvc resolvido, o mesmo teste passou a falhar com `jakarta.validation.NoProviderFoundException` — `JdempotentTestApplication` tem `@ComponentScan(basePackages = "br.com.sawcunhaos.foundation")` (escaneia tudo, não só o pacote `jdempotent`), então ele também instancia `ScosCacheConfiguration` (agora alcançável via a nova dependência em `scos-foundation-cache`), que faz bind de `ScosCacheProperties` (`@Validated`) — e Spring Boot exige um provider JSR-380 real no classpath para isso, não só a API. `cache/pom.xml` deliberadamente não tem um provider (AC #1 restringe as dependências do módulo); antes, `utils`'s `spring-boot-starter-validation` supria isso de graça. Corrigido com `hibernate-validator` como dependência de teste em `jdempotent/pom.xml` (mesmo padrão que `validation/pom.xml` já usa para seus próprios testes) — Commit 2, mesma razão da anterior.
- **Verificação**: `mvn -o -pl cache -am compile` → verde. `mvn -o compile` (reactor inteiro) → verde. `mvn -o -pl utils -am test` → 11/11 verdes (confirma que remover `spring-boot-starter-data-redis`/`spring-data-redis`/`jackson-dataformat-smile` de `utils/pom.xml` não quebrou nada — nenhuma classe restante em `utils` os usava). `mvn -o -pl jdempotent -am test` → 35/35 verdes, exceto 2 testes (`PrimeNumbersJdempotentDisableTest`/`PrimeNumbersJdempotentEnableTest`) que falham por `ContainerLaunchException`/Docker Compose (rede/porta), **não relacionado ao código desta story** — confirmado isolando a causa: (1) `docker compose up -d` manual do mesmo arquivo (`jdempotent/src/test/resources/docker-compose.yml`) funciona isoladamente; (2) o arquivo compose não referencia nenhuma classe movida; (3) mesma classe de limitação já registrada em `deferred-work.md` por stories anteriores ("jdempotent... erro de Testcontainers/Docker Compose"), mas ali por falta de Docker no sandbox daquela sessão — aqui o Docker existe, a falha é fragilidade de porta fixa (`6379`/`26379`) entre execuções consecutivas de teste, mesmo com `mvn -o test` completo do reactor (audit+jdempotent, ~6min) rodando antes. Não é uma regressão desta story: o compose/portas fixos já existiam antes da extração do módulo `cache`, e nada no diff desta story toca `docker-compose.yml`, `PrimeNumbersController` ou a configuração de Testcontainers. `mvn -o test -pl '!jdempotent' -am` (reactor completo exceto jdempotent) → `BUILD SUCCESS`, todos os módulos verdes incluindo `cache` (sem testes próprios, ver acima).
- **Verificação adicional pós-revisão, isolando classpath de Docker**: rodar `mvn -o -pl jdempotent -am test -Dtest=PrimeNumbersJdempotentEnableTest,PrimeNumbersJdempotentDisableTest -Dsurefire.failIfNoSpecifiedTests=false` (com Docker disponível neste ambiente) mostra o contexto Spring subindo com sucesso — `Started PrimeNumbersJdempotentDisableTest`, Tomcat inicializado, `ScosCacheConfiguration` carregada e logando normalmente — sem `NoProviderFoundException` nem `FileNotFoundException` de webmvc. A falha ocorre só depois, no `TestcontainersExtension`/Docker Compose (`ContainerLaunchException: Local Docker Compose exited abnormally`/porta já alocada), mesmo após limpar manualmente containers/redes órfãos de execuções anteriores. Isso confirma de forma observada (não só narrada) que o fix de classpath (`spring-boot-starter-web` + `hibernate-validator` em `jdempotent/pom.xml`) resolve o problema que motivou sua adição — o Debug Log original relatava a correção por narrativa de depuração ad-hoc, não por uma execução capturada que passasse dessa etapa; esta nota fecha essa lacuna de verificação.

### Completion Notes List

- AC #1: `scos-foundation-cache` criado, depende de `core` + `spring-boot-starter-cache`/`spring-boot-starter-data-redis` (+ 4 dependências adicionais inevitáveis, ver Debug Log); compila isoladamente (`mvn -pl cache -am compile` verde). Nenhum teste existia para as 5 classes migradas antes da extração (confirmado por busca no repo inteiro) — "testes migrados permanecem verdes" vale trivialmente (não há teste para regredir); lacuna pré-existente, não introduzida por esta story.
- AC #2: extração em exatamente 2 commits git — **Commit 1** (`parte 1 - mover`): novo módulo `cache` + as 5 classes movidas (zero mudança de lógica) + `pom.xml` raiz + o ajuste mecânico obrigatório em `jdempotent` (troca de dependência/import, consequência direta do mover — mesma categoria que a Story 1.8 já tratou como mecânica, não comportamental); **Commit 2** (`parte 2 - ajustes`): as 2 dependências de teste em `jdempotent/pom.xml` (`spring-boot-starter-web`, `hibernate-validator`) necessárias só por causa da divisão de módulo (antes chegavam de graça via `utils`) + limpeza de `utils/pom.xml` (3 dependências órfãs removidas). Nenhum ajuste de **comportamento** no código movido foi necessário — a task pedia para documentar isso explicitamente caso não houvesse nenhum.
- **Não antecipada** a correção de allowlist do `PolymorphicRedisSerializer` — confirmado que `deserialize()` é idêntico ao original (`Class.forName(payload.type())` sem validação), escopo da Story 3.16 (FR32).
- `jdempotent` deixou de depender de `scos-foundation-utils` inteiramente (era seu único uso) e passou a depender de `scos-foundation-cache` diretamente — antecipa parte do grafo alvo do AD-1 (`jdempotent → core, jdempapi, cache, privacy`) mesmo antes da Story 1.14 (remoção de `utils` do reactor).
- 2 testes de integração de `jdempotent` (`PrimeNumbersJdempotentDisableTest`/`PrimeNumbersJdempotentEnableTest`) não passam neste ambiente por fragilidade de Docker Compose com portas fixas entre execuções consecutivas — não é regressão desta story (ver Debug Log para a investigação completa). Demais 35 testes de `jdempotent` verdes; reactor inteiro (exceto esses 2) verde.
- `archtest` não ganhou dependência em `scos-foundation-cache` — mesmo padrão das Stories 1.8/1.9, fora do escopo desta story de extração de um único módulo.
- Nenhuma regra ArchUnit local foi criada em `cache` (diferente de `spring`, Story 1.8) — nem a story nem o AC pedem uma; seguido o mesmo precedente de `validation` (Story 1.9), que também não tem.

### File List

- `pom.xml` (raiz) — `<module>cache</module>` adicionado (logo após `validation`) + `dependencyManagement` para `scos-foundation-cache` + comentário sobre ordem de extração dos módulos-folha
- `cache/pom.xml` (novo) — deps `scos-foundation-core`, `spring-boot-starter-cache`, `spring-boot-starter-data-redis`, `spring-cloud-context`, `jakarta.validation-api`, `jackson-dataformat-smile`, `lombok` (optional); test-scope `archunit-junit5`/`junit-jupiter`/`mockito-*`
- `cache/src/main/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializer.java`, `ScosCacheConfiguration.java`, `ScosCacheKeyGenerator.java` (movidos de `utils`, sem alteração de lógica; só pacote/imports internos repontados)
- `cache/src/main/java/br/com/sawcunhaos/foundation/cache/properties/ScosCacheModel.java`, `ScosCacheProperties.java` (movidos, idem)
- `jdempotent/pom.xml` — Commit 1: dependência `scos-foundation-utils` (com exclusões JPA) trocada por `scos-foundation-cache` (sem exclusões, não precisa). Commit 2: `spring-boot-starter-web` e `hibernate-validator` adicionados como dependências de teste (ver Debug Log)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfiguration.java` — import de `PolymorphicRedisSerializer` repontado para `br.com.sawcunhaos.foundation.cache` (Commit 1, mecânico)
- `utils/src/main/java/br/com/sawcunhaos/foundation/utils/configuration/cache/**` (removido — movido para `cache`)
- `utils/pom.xml` (Commit 2) — dependências `spring-boot-starter-data-redis`, `spring-data-redis`, `jackson-dataformat-smile` removidas (órfãs após a extração; `spring-boot-starter-cache` e `spring-cloud-starter` permanecem, ainda usadas por outras classes de `utils`)

## Suggested Review Order

**O ajuste mecânico que não podia esperar pelo Commit 2**

- `jdempotent` era o único consumidor de `PolymorphicRedisSerializer` fora de `utils` — sem repontar aqui no Commit 1, o reactor quebra entre os dois commits.
  [`ScosJdempotentRedisConfiguration.java:18`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisConfiguration.java#L18)

**As duas regressões de classpath descobertas pelos testes (Commit 2)**

- `spring-webmvc` só era usado pelo harness de teste (`CustomExceptionHandler`), nunca por código de produção — por isso a correção é dependência de teste, não main.
  [`CustomExceptionHandler.java:22`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/test/app/exception/CustomExceptionHandler.java#L22)

- `hibernate-validator` precisou entrar porque o `@ComponentScan` amplo do app de teste alcança `ScosCacheConfiguration` mesmo sem nenhum teste testar cache diretamente.
  [`JdempotentTestApplication.java:24`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/test/app/JdempotentTestApplication.java#L24)

**O código movido em si (zero mudança de lógica)**

- `deserialize()` idêntico ao original — `Class.forName` sem allowlist, deliberadamente não corrigido aqui (Story 3.16).
  [`PolymorphicRedisSerializer.java:64`](../../cache/src/main/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializer.java#L64)

**Fiação do reactor**

- `cache` entra no reactor logo após `validation`, antes de `privacy`/`utils`.
  [`pom.xml:98`](../../pom.xml#L98)
