# Addendum — Detalhe Técnico de Implementação (F3, Decomposição do `utils`)

Conteúdo preservado dos planos de origem que não muda requisito nem critério de aceite do PRD, mas é referência útil para quem for implementar o FR-18/FR-19.

## Esquema de nomes de pacote

Decisão do plano de origem: os pacotes acompanham os módulos (`br.com.sawcunhaos.foundation.core`, `.spring`, `.web`, `.cache`, `.jpa`, `.validation`, etc.), sem agregador de transição nem período de depreciação — só é possível porque a `1.2.0` ainda é SNAPSHOT e nada foi publicado sob essa versão.

Justificativa do plano:
- Evita split package (mesmo pacote Java em módulos/JARs diferentes), que compromete a viabilidade futura de JPMS e native image.
- Elimina a necessidade de um agregador `deprecated` só para manter compatibilidade de import.
- O próprio nome `utils` é parte do problema: convida qualquer classe "sem casa" a entrar ali. Nomes de pacote alinhados a módulos de responsabilidade única removem esse convite.

## Mapeamento classe → módulo (inventário de referência)

Extraído da Fase 0 do plano (congelado como inventário de destino — nenhuma das 71 classes fica sem destino):

| Módulo | Classes (parcial, exemplos) |
|---|---|
| `core` | `DateUtils`, `HashUtils`, `StringFieldUtils`, `PropertiesOrder`, `ScosException`, `ExceptionCode`, `LocaleService`, `ScosBaseUseCase`, `ScosStartupListener`, `ScosUserAuthentication` |
| `spring` | `ScosRule`, `ScosRuleService`, `NormalizeStrings`, `StringProcessingAspect`, `ScosOnStartupListener` |
| `web` | `ScosController`, `IpAddressExtractor`, `ScosResponseUtils`, `PaginationUtils`, `JacksonXmlUtils`, `MultiReadHttpServletRequest`, `ScosJacksonConfig` |
| `jpa` | `SpecificationRepository`, `BaseEntity`, `JacksonCustomJsonFormatMapper`, `BaseLiquibaseProperties` |
| `cache` | `PolymorphicRedisSerializer` e demais `configuration/cache/*` |
| `feign` | `JacksonEncoderCustom`, `JacksonDecoderCustom` |

Dependências Maven declaradas por módulo (exemplos): `core` → `slf4j-api`, `lombok` (optional), `commons-lang3`; `spring` → `spring-context`, `spring-aop`; `jpa` → `spring-boot-starter-data-jpa`, `querydsl-jpa`, `liquibase-core` (optional); `cache` → `spring-boot-starter-cache`, `spring-boot-starter-data-redis`; `web` → `spring-boot-starter-web`, `spring-data-commons`, `feign-core` (optional, hoje — revisar após D3 criar módulo `feign` próprio).

Ver também a tabela completa de "todas as anotações, por destino" (18 anotações mapeadas individualmente) no plano original (`etc/doc/plano/plano-decomposicao-utils.md`, seção 3).

## Princípio: por que `web` e `spring` não ganham módulo `-api` companheiro

As anotações desses dois módulos (`@ScosController`, `@ScosRule`) marcam beans Spring que só existem onde já há Spring no classpath — não há cenário de "módulo de domínio puro" que precise delas sem o próprio Spring já presente. Criar `web-api`/`spring-api` multiplicaria artefato sem consumidor real. Esse é o critério para decidir, em iterações futuras, se uma nova anotação merece ou não um módulo `-api` companheiro: só vale a pena quando existe um consumidor plausível de domínio puro (como o módulo de domínio do SCOS-Flow, que motivou `audit-api`/`jdempotent-api`/`validation-api`).
