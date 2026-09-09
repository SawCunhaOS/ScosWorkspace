# Inventário classe → módulo (destino congelado)

> **Fonte congelada — Fase 0, Story 1.1.** Este arquivo é a referência única de destino para todas as classes de `scos-foundation-utils`. Stories 1.5–1.13 apontam para este arquivo em vez de recitar a tabela.
>
> Fontes de origem:
> - [Source: etc/doc/plano/plano-decomposicao-utils.md#3-módulos-alvo]
> - [Source: etc/doc/plano/plano-decomposicao-utils.md#todas-as-anotações-por-destino]
> - [Source: _bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/addendum.md#mapeamento-classe--módulo-inventário-de-referência]

## Reconciliação de contagem (Task 1)

`find utils/src/main/java -name "*.java" | wc -l` retorna **72**, não 71 como registrado na Seção 1 do plano de origem (`etc/doc/plano/plano-decomposicao-utils.md`).

Divergência identificada e resolvida: a tabela "Todas as anotações, por destino" (Seção 3 do plano) lista `ScosRequestMapping`/`GET`/`POST`/`PUT`/`DELETE` mas **omite `ScosRequestPATCH`**, que existe em `annotation/request/` no código atual e é uma anotação irmã das demais (mesmo padrão `@ScosRequest*`, decisão D1). Essa omissão no plano de origem explica os 71→72. `ScosRequestPATCH` é congelado abaixo com o mesmo destino de suas irmãs (`web`).

O restante da contagem do plano bate exatamente com a árvore atual (conferido pacote a pacote contra o levantamento das Dev Notes da story).

## Nota sobre classes sem migração (Gson → Jackson, Story 1.3)

Quatro classes não recebem módulo de destino porque são **removidas**, não migradas — decisão já registrada na Seção 6.1 do plano de origem (a stack JSON vira 100% Jackson; os adapters existem só porque o Gson não trata `java.time` nativamente). Para que nenhuma classe fique sem um destino *listado* (conforme a Seção 8, Fase 0, do plano: "nenhuma das 71 classes pode ficar sem destino"), cada uma delas recebe a disposição explícita `REMOVIDO — Story 1.3` na tabela abaixo, em vez de ficar ausente.

## Tabela classe → módulo → pacote

| # | Classe (FQN atual, prefixo `br.com.sawcunhaos.foundation.utils.`) | Módulo destino | Pacote destino |
|---|---|---|---|
| 1 | `exception.ScosException` | `core` | `br.com.sawcunhaos.foundation.core.exception` |
| 2 | `specification.ExceptionCode` | `core` | `br.com.sawcunhaos.foundation.core.specification` |
| 3 | `specification.LocaleService` | `core` | `br.com.sawcunhaos.foundation.core.specification` |
| 4 | `specification.ScosBaseUseCase` | `core` | `br.com.sawcunhaos.foundation.core.specification` |
| 5 | `specification.ScosStartupListener` | `core` | `br.com.sawcunhaos.foundation.core.specification` |
| 6 | `specification.ScosUserAuthentication` | `core` | `br.com.sawcunhaos.foundation.core.specification` |
| 7 | `enums.ScosExceptionCode` | `core` | `br.com.sawcunhaos.foundation.core.enums` |
| 8 | `enums.ValueType` | `core` | `br.com.sawcunhaos.foundation.core.enums` |
| 9 | `enums.SpecificationFunction` | `core` | `br.com.sawcunhaos.foundation.core.enums` |
| 10 | `enums.StringTransformRule` | `core` | `br.com.sawcunhaos.foundation.core.enums` |
| 11 | `utils.DateUtils` | `core` | `br.com.sawcunhaos.foundation.core` |
| 12 | `utils.HashUtils` | `core` | `br.com.sawcunhaos.foundation.core` |
| 13 | `utils.StringFieldUtils` | `core` | `br.com.sawcunhaos.foundation.core` |
| 14 | `sort.PropertiesOrder` | `core` | `br.com.sawcunhaos.foundation.core.sort` |
| 15 | `annotation.rules.ScosRule` | `spring` | `br.com.sawcunhaos.foundation.spring` |
| 16 | `annotation.rules.ScosRuleService` | `spring` | `br.com.sawcunhaos.foundation.spring` |
| 17 | `annotation.normalizestrings.NormalizeStrings` | `spring` | `br.com.sawcunhaos.foundation.spring` |
| 18 | `aspect.StringProcessingAspect` | `spring` | `br.com.sawcunhaos.foundation.spring` |
| 19 | `listener.ScosOnStartupListener` | `spring` | `br.com.sawcunhaos.foundation.spring` |
| 20 | `annotation.ScosController` | `web` | `br.com.sawcunhaos.foundation.web.annotation` |
| 21 | `annotation.request.ScosRequestMapping` | `web` | `br.com.sawcunhaos.foundation.web.annotation` |
| 22 | `annotation.request.ScosRequestGET` | `web` | `br.com.sawcunhaos.foundation.web.annotation` |
| 23 | `annotation.request.ScosRequestPOST` | `web` | `br.com.sawcunhaos.foundation.web.annotation` |
| 24 | `annotation.request.ScosRequestPUT` | `web` | `br.com.sawcunhaos.foundation.web.annotation` |
| 25 | `annotation.request.ScosRequestDELETE` | `web` | `br.com.sawcunhaos.foundation.web.annotation` |
| 26 | `annotation.request.ScosRequestPATCH` *(reconciliado — ver seção acima)* | `web` | `br.com.sawcunhaos.foundation.web.annotation` |
| 27 | `configuration.rest.ScosJacksonConfig` | `web` | `br.com.sawcunhaos.foundation.web` |
| 28 | `configuration.rest.filter.LoggingFinalFilter` | `web` | `br.com.sawcunhaos.foundation.web.filter` |
| 29 | `configuration.rest.filter.LoggingInitialFilter` | `web` | `br.com.sawcunhaos.foundation.web.filter` |
| 30 | `configuration.rest.filter.MultiReadHttpServletRequest` | `web` | `br.com.sawcunhaos.foundation.web.filter` |
| 31 | `configuration.rest.filter.properties.ScosFilterProperties` | `web` | `br.com.sawcunhaos.foundation.web.filter` |
| 32 | `dto.request.ScosPaginationFilterDTO` | `web` | `br.com.sawcunhaos.foundation.web.dto.request` |
| 33 | `dto.response.ScosPaginatedDTO` | `web` | `br.com.sawcunhaos.foundation.web.dto.response` |
| 34 | `dto.response.ScosResponseDTO` | `web` | `br.com.sawcunhaos.foundation.web.dto.response` |
| 35 | `utils.IpAddressExtractor` | `web` | `br.com.sawcunhaos.foundation.web` |
| 36 | `utils.ScosResponseUtils` | `web` | `br.com.sawcunhaos.foundation.web` |
| 37 | `utils.PaginationUtils` | `web` | `br.com.sawcunhaos.foundation.web` |
| 38 | `utils.JacksonXmlUtils` | `web` | `br.com.sawcunhaos.foundation.web` |
| 39 | `configuration.cache.PolymorphicRedisSerializer` | `cache` | `br.com.sawcunhaos.foundation.cache` |
| 40 | `configuration.cache.ScosCacheConfiguration` | `cache` | `br.com.sawcunhaos.foundation.cache` |
| 41 | `configuration.cache.ScosCacheKeyGenerator` | `cache` | `br.com.sawcunhaos.foundation.cache` |
| 42 | `configuration.cache.properties.ScosCacheModel` | `cache` | `br.com.sawcunhaos.foundation.cache.properties` |
| 43 | `configuration.cache.properties.ScosCacheProperties` | `cache` | `br.com.sawcunhaos.foundation.cache.properties` |
| 44 | `entity.BaseEntity` | `jpa` | `br.com.sawcunhaos.foundation.jpa.entity` |
| 45 | `configuration.hibernate.JacksonCustomJsonFormatMapper` | `jpa` | `br.com.sawcunhaos.foundation.jpa.hibernate` |
| 46 | `configuration.liquibase.BaseLiquibaseProperties` | `jpa` | `br.com.sawcunhaos.foundation.jpa.liquibase` |
| 47 | `utils.SpecificationRepository` | `jpa` | `br.com.sawcunhaos.foundation.jpa` |
| 48 | `validation.taxIdentifier.constraint.CnpjValidator` | `validation` | `br.com.sawcunhaos.foundation.validation.taxidentifier.constraint` |
| 49 | `validation.taxIdentifier.constraint.CpfValidator` | `validation` | `br.com.sawcunhaos.foundation.validation.taxidentifier.constraint` |
| 50 | `validation.taxIdentifier.constraint.TaxIdentifierValidator` | `validation` | `br.com.sawcunhaos.foundation.validation.taxidentifier.constraint` |
| 51 | `validation.zipcode.constraint.ZipCodeValidator` | `validation` | `br.com.sawcunhaos.foundation.validation.zipcode.constraint` |
| 52 | `valueobjects.Cpf` *(D2: fica em `validation`, `jakarta.persistence-api` provided)* | `validation` | `br.com.sawcunhaos.foundation.validation.valueobjects` |
| 53 | `valueobjects.Cnpj` *(D2)* | `validation` | `br.com.sawcunhaos.foundation.validation.valueobjects` |
| 54 | `valueobjects.Email` *(D2)* | `validation` | `br.com.sawcunhaos.foundation.validation.valueobjects` |
| 55 | `valueobjects.TaxIdentifier` *(D2)* | `validation` | `br.com.sawcunhaos.foundation.validation.valueobjects` |
| 56 | `validation.taxIdentifier.CNPJ` (anotação) | `validation-api` | `br.com.sawcunhaos.foundation.validation.api` |
| 57 | `validation.taxIdentifier.CPF` (anotação) | `validation-api` | `br.com.sawcunhaos.foundation.validation.api` |
| 58 | `validation.taxIdentifier.TaxIdentifier` (anotação) | `validation-api` | `br.com.sawcunhaos.foundation.validation.api` |
| 59 | `validation.zipcode.ZipCode` (anotação) | `validation-api` | `br.com.sawcunhaos.foundation.validation.api` |
| 60 | `annotation.audit.Auditable` | `audit-api` | `br.com.sawcunhaos.foundation.audit.api` |
| 61 | `annotation.audit.AuditAction` | `audit-api` | `br.com.sawcunhaos.foundation.audit.api` |
| 62 | `annotation.jdempotent.JdempotentId` | `jdempotent-api` | `br.com.sawcunhaos.foundation.jdempotent.api` |
| 63 | `annotation.jdempotent.JdempotentIgnore` | `jdempotent-api` | `br.com.sawcunhaos.foundation.jdempotent.api` |
| 64 | `annotation.jdempotent.JdempotentProperty` | `jdempotent-api` | `br.com.sawcunhaos.foundation.jdempotent.api` |
| 65 | `annotation.jdempotent.JdempotentRequestPayload` | `jdempotent-api` | `br.com.sawcunhaos.foundation.jdempotent.api` |
| 66 | `annotation.jdempotent.JdempotentResource` | `jdempotent-api` | `br.com.sawcunhaos.foundation.jdempotent.api` |
| 67 | `configuration.feign.JacksonEncoderCustom` *(D3: módulo próprio)* | `feign` | `br.com.sawcunhaos.foundation.feign` |
| 68 | `configuration.feign.JacksonDecoderCustom` *(D3)* | `feign` | `br.com.sawcunhaos.foundation.feign` |
| 69 | `adapter.LocalDateAdapter` | `REMOVIDO — Story 1.3` | — (apagado, não migrado) |
| 70 | `adapter.LocalDateTimeAdapter` | `REMOVIDO — Story 1.3` | — (apagado, não migrado) |
| 71 | `adapter.LocalTimeAdapter` | `REMOVIDO — Story 1.3` | — (apagado, não migrado) |
| 72 | `utils.GsonUtils` | `REMOVIDO — Story 1.3` | — (apagado, não migrado) |

**Total: 72 classes, todas com destino explícito.** Nenhum destino usa pacote genérico `util`/`common`/`utils.utils` (Task 3).

## Pontos de lacuna resolvidos na Fase 0 (confirmação explícita)

- `annotation/rules/*` (`ScosRule`, `ScosRuleService`) → `spring` (linhas 15–16).
- `listener/ScosOnStartupListener` → `spring` (linha 19). A interface `ScosStartupListener` permanece em `core` (linha 5).
