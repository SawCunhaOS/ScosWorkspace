# Story 1.12: Extrair o módulo `web`

Status: done

<!-- baseline_commit: 8726a9c5b2cec63fcef020c8113a5bed09b3aac8 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como time consumidor de endpoints REST,
Eu quero um módulo `web` com `@Cacheable` embutido,
Para ligar controllers sem montar a integração manualmente.

## Acceptance Criteria

1. **Given** `ScosController`, `IpAddressExtractor`, `ScosResponseUtils`, `PaginationUtils`, `JacksonXmlUtils`, `MultiReadHttpServletRequest`, `ScosJacksonConfig`, `LoggingInitialFilter`/`LoggingFinalFilter` do inventário, **When** o módulo `web` é extraído dependendo de `core`, `cache` e `privacy`, **Then** `web` compila isoladamente, `@Cacheable` funciona nas anotações `ScosRequestGET/POST/PUT/DELETE`, e os testes migrados permanecem verdes.

## Tasks / Subtasks

- [x] Task 1: Criar o módulo e mover as classes listadas no AC
  - [x] Criar módulo Maven `scos-foundation-web`, pacote raiz `br.com.sawcunhaos.foundation.web`, dependendo de `core` (Story 1.7), `cache` (Story 1.10), `privacy` (já existe), `spring-boot-starter-web`, `spring-data-commons` (+ `spring-cloud-context`, `jackson-dataformat-xml`, `lombok`, `spring-test` de teste — ver Debug Log)
  - [x] Mover: `annotation/ScosController.java`, `utils/IpAddressExtractor.java`, `ScosResponseUtils.java`, `PaginationUtils.java`, `JacksonXmlUtils.java`, `configuration/rest/filter/MultiReadHttpServletRequest.java`, `configuration/rest/ScosJacksonConfig.java`, `configuration/rest/filter/LoggingInitialFilter.java`, `LoggingFinalFilter.java`
  - [x] Mover também as anotações de rota (`annotation/request/ScosRequestMapping.java`, `ScosRequestGET.java`, `ScosRequestPOST.java`, `ScosRequestPUT.java`, `ScosRequestDELETE.java`, `ScosRequestPATCH.java`) — necessárias para o AC "`@Cacheable` funciona nas anotações `ScosRequestGET/POST/PUT/DELETE`" fazer sentido; `ScosRequestPATCH` não está citada no texto do AC mas pertence à mesma família e precisa mover junto para o módulo compilar (mesma divergência de contagem já registrada na Story 1.5) — **pacote real é `web.annotation` (flat), não `web.annotation.request`**: conferido contra o inventário congelado da Story 1.1 (linhas 20-26), que atribui todas as 6 anotações a `br.com.sawcunhaos.foundation.web.annotation`, junto com `ScosController`
  - [x] Mover os DTOs de suporte usados por `ScosResponseUtils`/`PaginationUtils`: `dto/request/ScosPaginationFilterDTO.java`, `dto/response/ScosPaginatedDTO.java`, `ScosResponseDTO.java` — não citados no texto do AC, mas exigidos para essas classes compilarem (comportamento end-to-end, não escopo novo)
  - [x] Mover `configuration/rest/filter/properties/ScosFilterProperties.java` (propriedades dos filtros de logging movidos) — **pacote real é `web.filter` (flat), não `web.filter.properties`**: conferido contra o inventário congelado (linha 31)
  - [x] Mover testes correspondentes: `configuration/rest/filter/LoggingFilterMaskingE2ETest.java`, `LoggingFinalFilterTest.java`, `LoggingInitialFilterTest.java`, `utils/PaginationUtilsTest.java`
  - [x] Commit isolado de "mover" separado de qualquer ajuste de comportamento (NFR2/NFR4, mesmo padrão das stories anteriores de extração — o AC desta story não repete a exigência de 2 commits textualmente, mas a convenção do épico (NFR2) se aplica igual)
- [x] Task 2: Confirmar `@Cacheable` funcionando (AC: #1)
  - [x] `web` depende diretamente de `cache` (decisão já tomada na arquitetura — aresta `web → cache` no grafo de dependência, resolvendo a Decisão D1 do plano de origem pela opção "web depende de cache")
  - [x] Confirmar que `nameCache()` com `@AliasFor` continua resolvendo `@Cacheable` corretamente após a migração de pacote — **novo teste `ScosRequestAnnotationCachingTest`** (não existia nenhum antes, nem em `utils`) verifica via `AnnotatedElementUtils.findMergedAnnotation` que as 5 anotações (`@ScosRequestGET`/`POST`/`PUT`/`DELETE`/`PATCH`) resolvem `@Cacheable`/`@CacheEvict` com os atributos corretos (`nameCache`, `keyGenerator`, `condition`), incluindo o bean `"ScosCacheKeyGenerator"` (nome explícito via `@Bean("ScosCacheKeyGenerator")` em `cache/ScosCacheConfiguration`, independente de pacote Java)
- [x] Task 3: Confirmar a aresta `web → privacy` (AC: #1)
  - [x] `LoggingInitialFilter`/`LoggingFinalFilter` importam `jakarta.servlet.*` **e** `SanitizationBodyComponent`/`SanitizationHeadersComponent` de `privacy` — essa combinação é a razão real dessas duas classes pertencerem a `web` e não a `spring` (aresta documentada como real, não hipotética, na arquitetura) — confirmado nos imports após a migração, sem alteração
- [x] Task 4: Confirmar testes verdes (AC: #1) — 17/17 testes de `web` verdes (4 suítes movidas + `ScosRequestAnnotationCachingTest` novo, 6 casos); reactor inteiro (incluindo `audit`) verde após corrigir uma regressão real em `exception` (ver Debug Log)

## Dev Notes

- Depende das Stories 1.7 (`core`) e 1.10 (`cache`) já concluídas; `privacy` já existe no reactor sem mudança.
- **Decisão D1 do plano de origem já resolvida pela arquitetura**: `web` depende de `cache` diretamente (opção "a" das três apresentadas) — não reabrir essa decisão nesta story.
- `web` é o módulo mais acoplado entre os módulos folha — depende de `core` + `cache` + `privacy` simultaneamente. É o último da ordem de extração da Fase 4 (`spring` → `validation` → `cache` → `jpa` → `web`).
- Feign (`JacksonEncoderCustom`/`JacksonDecoderCustom`) **não** entra nesta story — vai para o módulo `feign` próprio na Story 1.13 (Decisão D3 do plano de origem: módulo dedicado, não dependência dentro de `web`).

### Project Structure Notes

- Módulo Maven novo: `web/` — depende de `core`, `cache`, `privacy`, `spring-boot-starter-web`, `spring-data-commons` (+ `spring-cloud-context`, `jackson-dataformat-xml`, `lombok`; ver Debug Log).
- `utils/` perde as classes de `annotation/`, `annotation/request/`, `configuration/rest/*`, `dto/*`, e os utilitários `IpAddressExtractor`/`ScosResponseUtils`/`PaginationUtils`/`JacksonXmlUtils` — e, no ajuste, as dependências `spring-boot-starter-web`/`spring-data-commons`/`spring-cloud-starter`/`spring-boot-starter-cache`/`jackson-dataformat-xml`/`scos-foundation-privacy`, órfãs após a extração (ver Debug Log). `utils` fica com só 4 classes (2 Feign, `ValueType`, `LocaleService`) e zero testes.
- `pom.xml` raiz ganha `<module>web</module>` (logo após `jpa`, antes de `privacy`) + `dependencyManagement` para `scos-foundation-web`.
- `exception/pom.xml` ganha `spring-boot-starter-web` explícito (regressão real corrigida — ver Debug Log).

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#scos-foundation-web]
- [Source: etc/doc/plano/plano-decomposicao-utils.md#7-decisões-que-preciso-que-você-tome] (Decisão D1)
- [Source: _bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/ARCHITECTURE-SPINE.md#ad-1--fronteira-e-direção-de-dependência-entre-módulos-adopted] (aresta `web → privacy`)
- [Source: _bmad-output/implementation-artifacts/1-5-criar-módulos-api-e-mover-as-anotações-de-contrato.md] (divergência de contagem `ScosRequestPATCH`)
- [Source: _bmad-output/planning-artifacts/epics.md#story-112-extrair-o-módulo-web]
- [Source: _bmad-output/implementation-artifacts/inventario-classe-modulo.md#L45-L63] (pacotes reais das 18 classes)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- **Nota de processo**: o subagente de implementação (dispatch padrão do workflow) falhou por limite de sessão da conta na Story 1.11, antes desta story começar. A partir da 1.11 (inclusive), toda implementação passou a ser feita diretamente pela sessão principal, sem subagente, para não repetir o mesmo limite. Esta story (1.12) seguiu o mesmo modo.
- **2 desvios de pacote em relação ao texto do Task 1, corrigidos contra o inventário congelado**: o texto da story sugere `annotation/request/*` → `web.annotation.request` e `filter/properties/ScosFilterProperties` → `web.filter.properties`, espelhando a estrutura de pacotes de `utils`. O inventário congelado da Story 1.1 (fonte única de verdade para destino de pacote, conforme seu próprio preâmbulo) diz o contrário: as 6 anotações vão todas para `web.annotation` (flat, junto com `ScosController`), e `ScosFilterProperties` vai para `web.filter` (flat, junto com os 2 filtros). Movidas inicialmente para os pacotes "óbvios" (espelhando `utils`), depois corrigidas para bater com o inventário antes do commit — nenhum código chegou a ser commitado no destino errado.
- **Dependências de `web/pom.xml` além de `core`/`cache`/`privacy`/`spring-boot-starter-web`/`spring-data-commons` citadas no Dev Notes**: 3 adicionais, nenhuma viola AC #1:
  - `org.springframework.cloud:spring-cloud-context` — `ScosFilterProperties` usa `@RefreshScope`; mesma dependência estreita que `cache`/`jpa` já usam para o mesmo padrão.
  - `tools.jackson.dataformat:jackson-dataformat-xml` — `JacksonXmlUtils` constrói um `XmlMapper` (Jackson 3) diretamente; traz `jackson-databind` transitivamente (mesmo padrão do `cache/pom.xml` para `jackson-dataformat-smile`).
  - `org.projectlombok:lombok` (`optional`) — `@Data`/`@Builder`/`@RequiredArgsConstructor`/`@NoArgsConstructor`/`@AllArgsConstructor`/`@Slf4j` nas classes movidas.
  - Teste: `org.springframework:spring-test` — `LoggingFilterMaskingE2ETest` dirige os filtros via `MockMvc` standalone.
- **`ScosCacheKeyGenerator` (bean referenciado por `keyGenerator = "ScosCacheKeyGenerator"` em `@ScosRequestGET`) confirmado resiliente à migração**: `cache/ScosCacheConfiguration` registra o bean com `@Bean("ScosCacheKeyGenerator")` — nome de bean Spring é uma string independente do pacote Java da classe, então a migração de `web` não quebra essa resolução. Confirmado por leitura direta do código-fonte, não só por inferência.
- **Limpeza de dependências órfãs em `utils/pom.xml` — critério aplicado: só remover o que ESTA story orfanizou diretamente** (não dívida pré-existente de stories anteriores): `spring-boot-starter-web` (único consumidor era `ScosController`/filtros/`ScosJacksonConfig`, todos movidos), `spring-data-commons` (único consumidor era `PaginationUtils`), `spring-cloud-starter` (único consumidor era `ScosFilterProperties`), `spring-boot-starter-cache` (a justificativa da Story 1.10 — `ScosRequestGET/POST/etc` usarem `@Cacheable` — deixou de existir porque essas próprias classes migraram agora), `scos-foundation-privacy` (único consumidor era `LoggingInitialFilter`/`LoggingFinalFilter`), `jackson-dataformat-xml` (único consumidor era `JacksonXmlUtils`; substituída por `tools.jackson.core:jackson-databind` explícito, necessário para os codecs Feign que restaram), `spring-boot-test`/`spring-test` (as 4 suítes de teste que restavam em `utils` — as únicas que os usavam — migraram todas para `web`; `utils/src/test` ficou vazio). **Deliberadamente NÃO removidas** (órfãs há mais tempo, não atribuíveis a esta story): `spring-boot-starter-validation`, `spring-boot-starter-actuator`, `spring-boot-starter-logging`, `lombok`, `commons-lang3`, `junit-jupiter`/`mockito-*` (mantidos como scaffolding padrão, mesmo padrão de `cache`/`jpa`/`validation`, que também declaram esses testes mesmo sem teste próprio ainda) — confirmado por `grep` que nenhum dos 4 arquivos restantes de `utils` (`JacksonEncoderCustom`, `JacksonDecoderCustom`, `ValueType`, `LocaleService`) os usa, mas a causa raiz do desuso não é esta story (rastrear e remover é trabalho para quem tocar `utils` depois — provavelmente Story 1.14, que já vai remover `utils` do reactor inteiramente).
- **Regressão real encontrada pelos testes, não pela compilação de `mvn compile`**: `exception/pom.xml` dependia de `scos-foundation-utils` mas nunca declarou `spring-boot-starter-web` diretamente — `ExceptionsHandler.java` (main) usa `jakarta.servlet.http.HttpServletRequest`/`@ExceptionHandler`/`ResponseEntity` há muito tempo, sempre pegando `spring-boot-starter-web` de graça via `utils`. `mvn compile` (só main) não detectou o problema porque `ExceptionsHandler.java` também compilava antes por essa mesma transitividade — o problema só aparece na descoberta de testes do JUnit5 (`NoClassDefFoundError: jakarta/servlet/http/HttpServletRequest` ao escanear `ExceptionsHandlerInternalErrorTest`), quando o classpath de teste já não tinha mais o servlet-api. Corrigido adicionando `spring-boot-starter-web` explícito a `exception/pom.xml`. **Auditoria sistemática rodada em seguida**: todos os outros consumidores de `scos-foundation-utils` (`audit`, `archtest`, `jdempotent`) foram verificados via `grep` por uso de servlet/spring-web/spring-data/spring-cloud/cache/privacy sem declaração própria — `audit` e `jdempotent` já tinham suas próprias dependências explícitas (confirmado via `mvn test-compile`, verde antes de qualquer correção); só `exception` estava exposto.
- **Nenhum teste prévio existia para a resolução de `@Cacheable`/`@CacheEvict` via `@ScosRequestGET`/`POST`/`PUT`/`DELETE`/`PATCH`** (nem em `utils`, antes desta story) — a AC #1 exige confirmar esse comportamento explicitamente, então foi escrito `ScosRequestAnnotationCachingTest` (novo, 6 casos — cobrindo as 5 anotações, GET com atributos default e customizados) usando `AnnotatedElementUtils.findMergedAnnotation` para verificar a resolução de `@AliasFor` sem precisar de um contexto Spring completo. **Escopo consciente**: o teste verifica a resolução de metadados (a única coisa que uma migração de pacote poderia quebrar), não o comportamento de cache em runtime com `CacheManager` real — ver Deferred Work.
- **Verificação**: `mvn -o -pl web -am compile` → verde, 19 fontes (18 do AC + o pacote de anotações flat). `mvn -o compile` (reactor inteiro) → verde. `mvn -o -pl web -am test` → 17/17 verdes (11 migrados + `ScosRequestAnnotationCachingTest`, 6 casos). `mvn -o test-compile -pl audit,jdempotent -am` → verde (confirma que a limpeza de `utils/pom.xml` não afetou esses dois consumidores). `mvn -o test -pl '!jdempotent,!audit' -am` (reactor completo exceto Docker) → verde após a correção de `exception/pom.xml`. `mvn -o -pl audit -am test` → `BUILD SUCCESS` (54/54, ~5min).

### Completion Notes List

- AC #1: `scos-foundation-web` criado, depende de `core` + `cache` + `privacy` + `spring-boot-starter-web` + `spring-data-commons` (+ 3 dependências adicionais inevitáveis, ver Debug Log); compila isoladamente e via reactor completo. `@Cacheable`/`@CacheEvict` confirmados resolvendo corretamente via `@AliasFor` após a migração (teste novo, `ScosRequestAnnotationCachingTest`, cobrindo as 5 anotações — GET×2, POST, PUT, DELETE, PATCH —, 6/6 verdes). Testes migrados: 11/11 verdes (5 `LoggingInitialFilterTest` + 2 `LoggingFinalFilterTest` + 3 `PaginationUtilsTest` + 1 E2E de masking); total do módulo `web`: 17/17 (11 migrados + 6 novos).
- **2 desvios de pacote corrigidos contra o inventário congelado** (não contra o texto literal do Task 1): anotações de rota em `web.annotation` (flat), `ScosFilterProperties` em `web.filter` (flat). Ver Debug Log.
- **Regressão real em módulo consumidor (`exception`), não prevista pelo AC, encontrada e corrigida**: `spring-boot-starter-web` estava sendo consumido transitivamente de `utils` sem declaração própria; a limpeza de dependências órfãs de `utils/pom.xml` (parte do "ajustar" desta story) expôs isso. Ver Debug Log para a investigação completa e a auditoria dos demais consumidores de `utils`.
- `utils` fica reduzido a 4 classes (2 codecs Feign para a Story 1.13, `ValueType` e `LocaleService` — ambas já com destino `core` congelado desde a Story 1.1, nunca migradas, fora do escopo desta story) e zero testes — extremamente próximo do que a Story 1.14 (remover `utils` do reactor) vai precisar.
- `archtest` não ganhou dependência em `scos-foundation-web` — mesmo padrão das Stories 1.8-1.11, fora do escopo desta story de extração de um único módulo.
- Nenhuma regra ArchUnit local foi criada em `web` — mesmo precedente de `validation`/`cache`/`jpa` (Stories 1.9-1.11), que também não têm.

### File List

- `pom.xml` (raiz) — `<module>web</module>` adicionado (logo após `jpa`) + `dependencyManagement` para `scos-foundation-web` + comentário sobre ordem de extração dos módulos-folha
- `web/pom.xml` (novo) — deps `scos-foundation-core`, `scos-foundation-cache`, `scos-foundation-privacy`, `spring-boot-starter-web`, `spring-data-commons`, `spring-cloud-context`, `jackson-dataformat-xml`, `lombok` (optional); test-scope `archunit-junit5`/`junit-jupiter`/`mockito-*`/`spring-test`
- `web/src/main/java/br/com/sawcunhaos/foundation/web/annotation/{ScosController,ScosRequestMapping,ScosRequestGET,ScosRequestPOST,ScosRequestPUT,ScosRequestDELETE,ScosRequestPATCH}.java` (movidos de `utils`, pacote flat conforme inventário — sem alteração de lógica)
- `web/src/main/java/br/com/sawcunhaos/foundation/web/{IpAddressExtractor,ScosResponseUtils,PaginationUtils,JacksonXmlUtils,ScosJacksonConfig}.java` (movidos, idem)
- `web/src/main/java/br/com/sawcunhaos/foundation/web/filter/{MultiReadHttpServletRequest,LoggingInitialFilter,LoggingFinalFilter,ScosFilterProperties}.java` (movidos, pacote flat conforme inventário)
- `web/src/main/java/br/com/sawcunhaos/foundation/web/dto/request/ScosPaginationFilterDTO.java`, `dto/response/{ScosPaginatedDTO,ScosResponseDTO}.java` (movidos)
- `web/src/test/java/br/com/sawcunhaos/foundation/web/filter/{LoggingFilterMaskingE2ETest,LoggingFinalFilterTest,LoggingInitialFilterTest}.java`, `web/PaginationUtilsTest.java` (movidos de `utils`, sem alteração de asserção)
- `web/src/test/java/br/com/sawcunhaos/foundation/web/annotation/ScosRequestAnnotationCachingTest.java` (novo) — regressão do AC #1 (`@Cacheable`/`@CacheEvict` via `@AliasFor`)
- `utils/src/main/java/.../{annotation/**, utils/IpAddressExtractor, utils/ScosResponseUtils, utils/PaginationUtils, utils/JacksonXmlUtils, configuration/rest/**, dto/**}.java` (removidos — movidos para `web`)
- `utils/src/test/java/.../{configuration/rest/filter/**, utils/PaginationUtilsTest}.java` (removidos — movidos; `utils/src/test` fica vazio)
- `utils/pom.xml` — 7 dependências órfãs removidas (`spring-boot-starter-web`, `spring-data-commons`, `spring-cloud-starter`, `spring-boot-starter-cache`, `scos-foundation-privacy`, `jackson-dataformat-xml`, `spring-boot-test`/`spring-test`); `tools.jackson.core:jackson-databind` adicionado explícito (necessário para os codecs Feign restantes, antes vinha transitivo via `jackson-dataformat-xml`); comentário adicionado marcando as dependências órfãs pré-existentes deliberadamente não removidas (fora do escopo desta story)
- `exception/pom.xml` — `spring-boot-starter-web` adicionado explícito (regressão real corrigida, ver Debug Log)

## Suggested Review Order

**A regressão real: dependência transitiva perdida por um consumidor não previsto**

- Ponto de entrada: `exception` nunca declarou `spring-boot-starter-web` — sempre veio de graça via `utils`, que perdeu essa dependência na limpeza desta story.
  [`exception/pom.xml:97`](../../exception/pom.xml#L97)

**O requisito central do AC: `@Cacheable` sobrevive à migração de pacote**

- Novo teste prova a resolução de `@AliasFor` via `AnnotatedElementUtils`, cobrindo as 5 anotações — não existia nenhum teste assim antes, nem em `utils`.
  [`ScosRequestAnnotationCachingTest.java:38`](../../web/src/test/java/br/com/sawcunhaos/foundation/web/annotation/ScosRequestAnnotationCachingTest.java#L38)

**A aresta `web → privacy`, confirmada real (Task 3)**

- `LoggingInitialFilter` importa `privacy` diretamente — motivo real de `web` (não `spring`) hospedar os filtros de logging.
  [`LoggingInitialFilter.java:17`](../../web/src/main/java/br/com/sawcunhaos/foundation/web/filter/LoggingInitialFilter.java#L17)

**Limpeza de dependências: só o que esta story orfanizou**

- Comentário documenta o critério aplicado (e o que foi deliberadamente deixado para trás) na limpeza de `utils/pom.xml`.
  [`utils/pom.xml:90`](../../utils/pom.xml#L90)

**Fiação do reactor**

- `web` entra no reactor logo após `jpa`, o último módulo-folha da Fase 4.
  [`pom.xml:114`](../../pom.xml#L114)
