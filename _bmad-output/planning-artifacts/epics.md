---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/prd.md
  - _bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/addendum.md
  - _bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/GUIA-DE-IMPLEMENTACAO.md
  - _bmad-output/specs/spec-SawCunhaOS-Foundation/SPEC.md
---

# SawCunhaOS-Foundation 1.2.0 - Epic Breakdown

## Overview

Este documento decompõe os requisitos do PRD 1.2.0, da Architecture Spine e do SPEC canônico do `SawCunhaOS-Foundation` em Epics e Stories implementáveis. Não há documento de UX (biblioteca Java sem interface visual).

## Requirements Inventory

### Functional Requirements

**F1 — Confiabilidade de Idempotência**

FR1: Detectar colisão de chave entre fontes independentes com payloads diferentes (mesma chave, hash de payload distinto) e responder `422 PAYLOAD_MISMATCH` em vez de compartilhar a resposta cacheada.
FR2: Tornar a aquisição do lock de idempotência atômica via novo contrato `tryAcquire(key, payloadHash, ttl) → Lease`, substituindo o fluxo não-atômico `contains → store → setResponse`. Chamada concorrente com a mesma chave responde `409 IN_PROGRESS`. TTL do lease configurável por método; métrica `idempotency.in_progress` monitorada para detectar lease expirando antes do método terminar.
FR3: Suportar header `Idempotency-Key` como fonte de chave via `@JdempotentResource(keySource=HEADER_THEN_FIELDS, headerName="Idempotency-Key", onMismatch=CONFLICT)`, com precedência header → campos anotados → hash. Não reutilizar `X-Request-ID`. O resolver de chave deve devolver `null` de forma limpa (nunca lançar exceção) quando não há contexto web disponível (ex.: mensageria).
FR4: Garantir fail-open quando o Redis está indisponível (nunca `FAIL_CLOSED`), com circuit breaker (Resilience4j, `optional=true`) detectando lentidão via `slow-call-duration-threshold`, respeitando `spring.data.redis.timeout`.
FR5: Migrar hashing de MD5 para SHA-256 (via enum `CryptographyAlgorithm`) e a formatação hex de `Integer.toHexString` para `HexFormat.of().formatHex()`.
FR6: Resolver campos anotados para composição de chave percorrendo toda a hierarquia de classes (não apenas `getDeclaredFields()`).
FR7: Expor métricas de idempotência via interface própria `IdempotencyMetrics` (no-op por padrão, Micrometer condicional), incluindo `idempotency.acquired`, `.hit`, `.in_progress`, `.mismatch`, `.backend_error`, `.degraded` (gauge 0/1) e `.degraded.transitions` (counter).
FR8: Introduzir `IdempotencyKeyResolver` e `@JdempotentProperty` como seletor explícito de campos, com serialização canônica (`TreeMap`) na composição de chave; `@JdempotentId` deixa de compor a chave.
FR25: Corrigir a inicialização com `RedisConnectionFactory` do Spring Boot em vez de montar `RedisSentinelConfiguration` própria e hardcoded (hoje causa NPE em Redis standalone/cluster).
FR26: Tornar a política de falha por exceção de negócio declarável por método — `RELEASE` (default, remove a chave) ou `KEEP_FAILED` (grava o erro como resultado).
FR27: Posicionar o `@Order` do aspecto de idempotência fora do escopo do `@Transactional`, para que um rollback de transação não deixe a chave órfã no Redis.
FR28: Tornar obrigatório e configurável via propriedade Spring o namespace de prefixo de chave (hoje lido de `System.getenv(APP_NAME)`, silenciosamente vazio quando ausente).
FR29: Registrar `IdempotentAspect` com `@ConditionalOnMissingBean` e remover o uso de `ThreadLocal` para `MessageDigest`.
FR30: Migrar a configuração de `@Value` para `@ConfigurationProperties`, remover propriedades mortas, e corrigir o `EnvironmentPostProcessor` (hoje declarado incorretamente em `AutoConfiguration.imports`).
FR31: Respeitar o TTL configurado em todos os construtores do `InMemoryIdempotentRepository` (hoje ignorado em 4 dos 7) e corrigir `equals`/`hashCode` do `IdempotentRequestWrapper` (hoje não-reflexivo e não-simétrico).
FR32: Adicionar allowlist de tipos permitidos no `PolymorphicRedisSerializer` antes do `Class.forName` sobre valor vindo do Redis (achado de segurança).
FR33: Substituir construtores telescópicos por builder no módulo `jdempotent`; documentar no README o princípio "cache é fast-path, não garantia" e a obrigatoriedade da constraint `UNIQUE` no banco.

**F2 — Correção e Simplificação do Tratamento de Erros**

FR9: Corrigir o handler de acesso negado para capturar `org.springframework.security.access.AccessDeniedException` (não `java.nio.file.AccessDeniedException`), restaurando o `403`. Manter os dois handlers lado a lado (o de `AuthorizationDeniedException` e o corrigido).
FR10: Corrigir o handler de validação para não lançar `IndexOutOfBoundsException` quando a violação ocorre em parâmetro simples em vez de bean — iterar sobre `getBeanResults()` e `getValueResults()`.
FR11: Extinguir `scos-foundation-exception`, dividindo em contrato de domínio no `core` (`ScosException`, `ExceptionCode`, `ScosExceptionCode`, `LocaleService`, `ScosNoContentException`, `ScosNoRollbackException`, `ScosSecurityException`, `MethodNotImplementedException`) e tradução HTTP em `scos-foundation-web` (`ExceptionsHandler`, `ScosProblemDetails`, `ScosFieldError`, `ExceptionUtils`). Repontar `audit` para consumir `ScosException` do `core`.
FR12: Registrar `ExceptionsHandler` via `AutoConfiguration.imports`, com `@ConditionalOnProperty(scos.web.error-handler.enabled, matchIfMissing=true)` e `@Order(Ordered.LOWEST_PRECEDENCE)`.
FR13: Sobrescrever `handleExceptionInternal` para unificar o formato de erro em todos os casos, incluindo 404 / rota inexistente.
FR14: Substituir o parsing por regex em `resolveTitle` por navegação de causa (`InvalidFormatException`/`MismatchedInputException.getPath()`), compatível com Jackson 3.
FR15: Retornar `501` para `MethodNotImplementedException` (hoje `500` genérico).
FR16: Padronizar log por faixa de status — `4xx` em `WARN` sem stack trace, `5xx` em `ERROR` com stack trace, `ScosNoContentException` (204) em `DEBUG` — e padronizar uso de `@Slf4j` (remover Log4j2 direto).
FR17: Consolidar a constante `MDC_REQUEST_ID`, hoje duplicada entre `ScosProblemDetails` e `LoggingInitialFilter`, no módulo `core`.
FR34: Corrigir `resolveTitle`, que hoje usa `try/catch` como controle de fluxo para testar existência de chave no bundle de mensagens — `LocaleService` ganha `getMessageOrDefault(code, default)`, com default vindo de `ExceptionCode.getTitle()`.

**F3 — Decomposição Modular do `utils`**

FR18: Dividir `scos-foundation-utils` nos módulos `core`, `spring`, `web`, `cache`, `jpa`, `validation`, `audit-api`, `jdempotent-api`, `validation-api` e `feign`. `web` mantém `@Cacheable` embutido e aceita dependência formal de `cache`. Value objects (`Cpf`, `Cnpj`, `Email`, `TaxIdentifier`) ficam em `validation` (com `jakarta.persistence-api` provided). Ordem: passo 3 cria `*-api`; passo 4 extrai `core`; passo 6 extrai `spring`, `validation`, `cache`, `jpa`, `web`, `feign`.
FR19: Impor por regra estrutural: `core` não importa `org.springframework`/`jakarta.persistence`/`jakarta.servlet`; `spring` não importa `jakarta.servlet`/`jakarta.persistence`/`spring.data`; módulos `*-api` contêm apenas `@interface`/`enum`; nenhum módulo depende de `web` exceto aplicações; sem ciclos entre módulos; proibida a criação de pacote `utils.utils` ou equivalente.
FR20: Impor as regras do FR19 via testes ArchUnit no perfil `analyze`, promovido para `pluginManagement` do POM pai (100% dos módulos). Cada regra entra no mesmo commit que cria o módulo que ela protege.
FR21: Migrar serialização JSON de Gson para Jackson em toda a base — remover `GsonUtils` e os 3 adapters de `java.time`; migrar `JsonMasker` (módulo `privacy`) e os 4 pontos de uso em `audit` — preservando a política de nulos (`@JsonInclude`) e a característica O(n) do caminho quente do `JsonMasker`.
FR22: Remover dependências mortas (`bouncycastle`, `snakeyaml`, `mapstruct`), substituir `guava` por `commons-lang3`, avaliar substituição de `commons-io` por `java.nio`, e avaliar a necessidade real de `spring-cloud-starter`.
FR23: Congelar, na Fase 0, o inventário de destino módulo-a-módulo das 71 classes atuais — nenhuma classe pode ficar sem destino.
FR24: Emitir log `INFO` na inicialização de cada módulo de implementação (não `*-api`) contando quantas classes anotadas foram encontradas na aplicação consumidora. Cada README de módulo `-api` abre com a frase "este artefato não executa nada; a implementação é `scos-foundation-<x>`".

### NonFunctional Requirements

NFR1 (ordem de execução): seguir a tabela de Sequenciamento e Fases do PRD — nenhuma fase pode ser adiantada em relação à sua dependência.
NFR2 (segurança de refatoração): build verde a cada commit/módulo extraído; cada extração de módulo em 2 commits separados (mover/renomear vs. ajustar comportamento) — nunca misturados.
NFR3 (cobertura de teste): `jacoco:check` com mínimo de 80% nas áreas tocadas pela Fase 0 do F1 (testes de concorrência, colisão de hex, duplo `IdempotentAspect`, indisponibilidade de Redis via Testcontainers).
NFR4 (escopo de mudança): nenhuma alteração de comportamento além do declarado durante mover/renomear.
NFR5 (TDD no F2): cada correção de bug do F2 (FR9, FR10, FR34, contrato 404 do FR13) exige um teste que reproduza o bug e falhe antes do fix.
NFR6 (garantia de dados sob fail-open): todo método com chave de idempotência natural deve ter constraint `UNIQUE` no banco antes de habilitar o `jdempotent` — pré-requisito, não recomendação.
NFR7 (piso de documentação, repo inteiro): todo módulo — novo ou existente, incluindo `audit` e `privacy` — exige Javadoc em API pública (Checkstyle, promovido a `pluginManagement`), comentário inline onde a lógica não é óbvia, diagrama de fluxo Mermaid inline no README, e README obrigatório por módulo. **Bloqueia o release da 1.2.0.**

### Additional Requirements

- **ADD-1** (AD-1): Grafo de dependência entre módulos fixado — direção sempre de fora para dentro (`auditapi/jdempapi/validationapi/spring/validation/cache/jpa/web/feign → core`; `jdempotent → core, jdempapi, cache, privacy`; `audit → core, auditapi, jpa, privacy`; `web → core, cache, privacy`). Nenhum módulo além de aplicações consumidoras depende de `web`. Aresta `web → privacy` é real (`LoggingInitialFilter`/`LoggingFinalFilter` usam sanitização de `privacy`).
- **ADD-2** (AD-5 / Stack): Criar módulo novo `archtest` (scope=test, sem código de produção) na Fase 2, para hospedar regras ArchUnit que citam mais de um módulo (ex.: "nada depende de `web`") — regras cross-módulo nunca duplicadas dentro de um módulo de implementação individual. Dependência nova: `com.tngtech.archunit:archunit-junit5:1.5.0`.
- **ADD-3** (AD-2 / Stack): Circuit breaker de fail-open usa `io.github.resilience4j:resilience4j-spring-boot4:2.4.0` (não `-spring-boot3`) fixado explicitamente no `pom.xml` do `jdempotent` — não gerenciado por nenhum BOM do projeto.
- **ADD-4** (AD-2): `key` de idempotência sempre resolvida por um único `IdempotencyKeyResolver` compartilhado entre o path HTTP (aspecto) e o path de mensageria (listener) — nunca reimplementada por entrypoint. `ttl` do `Lease` é sempre `java.time.Duration`, nunca `long` cru.
- **ADD-5** (Consistency Conventions): Nomes de pacote raiz seguem `br.com.sawcunhaos.foundation.<módulo>`, sem agregador de transição/depreciação (SNAPSHOT permite). Sub-pacote interno segue exatamente o inventário classe→módulo congelado na Fase 0 (addendum do PRD); proibido sub-pacote genérico `util`/`common` dentro de `core`.
- **ADD-6** (Stack): Versões fixadas via `scos-bom:1.3.1` — Java 25, Spring Boot `4.1.0`, Jackson `jackson-bom:3.2.1`, Checkstyle e Jacoco já presentes no perfil `analyze`.
- **ADD-7** (Structural Seed): Estrutura final de módulos do reactor: `privacy`, `archtest` (novo), `core` (novo), `audit-api` (novo), `jdempotent-api` (novo), `validation-api` (novo), `spring` (novo), `validation` (novo), `cache` (novo), `jpa` (novo), `web` (novo), `feign` (novo), `audit`, `jdempotent`. `utils` e `exception` saem do reactor ao final.
- **ADD-8** (SPEC.md — Constraints/Success signal): Sem guia de migração formal nem aviso direto a consumidores piloto — CHANGELOG é a única superfície de comunicação, cada frente registra sua entrada no momento em que seus commits sobem. Sucesso mensurável: zero erro de autorização mal classificado e zero duplicidade de idempotência em operação normal em produção pós-release.

### UX Design Requirements

Não aplicável — não há documento de UX para este projeto (biblioteca Java sem interface visual/consumidor final direto).

### FR Coverage Map

FR1: Epic 3 - Colisão de payload sob mesma chave (422 PAYLOAD_MISMATCH)
FR2: Epic 3 - `tryAcquire(key, payloadHash, ttl) → Lease` atômico, 409 IN_PROGRESS
FR3: Epic 3 - Header `Idempotency-Key` como fonte de chave
FR4: Epic 3 - Fail-open com circuit breaker quando Redis indisponível
FR5: Epic 3 - Hashing SHA-256 + `HexFormat`
FR6: Epic 3 - Resolução de campos anotados em toda a hierarquia de classes
FR7: Epic 3 - Métricas de idempotência (`IdempotencyMetrics`)
FR8: Epic 3 - `IdempotencyKeyResolver` + `@JdempotentProperty`, chave canônica (TreeMap)
FR9: Epic 2 - Handler de `AccessDeniedException` do Spring Security (403 correto)
FR10: Epic 2 - Handler de validação sem `IndexOutOfBoundsException` (400 correto)
FR11: Epic 2 - Extinção do módulo `exception`, split `core`/`web`
FR12: Epic 2 - Registro do `ExceptionsHandler` via `AutoConfiguration.imports`
FR13: Epic 2 - `handleExceptionInternal` unificado (incl. 404 nativo)
FR14: Epic 2 - `resolveTitle` por navegação de causa (compat. Jackson 3)
FR15: Epic 2 - `MethodNotImplementedException` → 501
FR16: Epic 2 - Log padronizado por faixa de status + `@Slf4j`
FR17: Epic 2 - Consolidação de `MDC_REQUEST_ID` no `core`
FR18: Epic 1 - Divisão do `utils` em 10 módulos de responsabilidade única
FR19: Epic 1 - Regras estruturais de dependência entre módulos
FR20: Epic 1 - Regras FR19 impostas via ArchUnit no perfil `analyze`
FR21: Epic 1 - Migração Gson → Jackson
FR22: Epic 1 - Remoção de dependências mortas / substituição de libs
FR23: Epic 1 - Inventário congelado classe→módulo (Fase 0)
FR24: Epic 1 - Log de inicialização por módulo de implementação
FR25: Epic 3 - Correção da inicialização com `RedisConnectionFactory`
FR26: Epic 3 - Política de falha declarável por método (`RELEASE`/`KEEP_FAILED`)
FR27: Epic 3 - `@Order` do aspecto fora do escopo do `@Transactional`
FR28: Epic 3 - Namespace de prefixo de chave configurável via Spring
FR29: Epic 3 - `@ConditionalOnMissingBean` + remoção de `ThreadLocal`
FR30: Epic 3 - Migração `@Value` → `@ConfigurationProperties` + fix `EnvironmentPostProcessor`
FR31: Epic 3 - TTL respeitado em todos os construtores + fix `equals`/`hashCode`
FR32: Epic 3 - Allowlist de tipos no `PolymorphicRedisSerializer`
FR33: Epic 3 - Builder no `jdempotent` + README "cache é fast-path"
FR34: Epic 2 - `resolveTitle` sem try/catch como controle de fluxo

NFR1: Todos os Epics - ordem de execução (Sequenciamento e Fases do PRD)
NFR2: Todos os Epics - build verde a cada commit, 2 commits por extração de módulo
NFR3: Epic 3 - cobertura 80% (Fase 0 F1)
NFR4: Todos os Epics - nenhuma mudança de comportamento além do declarado
NFR5: Epic 2 - TDD para cada correção de bug
NFR6: Epic 3 - constraint UNIQUE como pré-requisito sob fail-open
NFR7: Epic 4 - piso de documentação obrigatório (bloqueia release)

## Epic List

### Epic 1: Modularização e Fronteiras Estruturais do `utils`

Consumidores da lib passam a importar apenas os módulos de que precisam (ex.: `core` para `DateUtils`) sem arrastar JPA/Redis/Feign transitivamente; o build recusa automaticamente qualquer violação de fronteira entre módulos.

**FRs covered:** FR18, FR19, FR20, FR21, FR22, FR23, FR24
**NFRs covered:** NFR1, NFR2, NFR4
**Additional:** ADD-1, ADD-2, ADD-5, ADD-6, ADD-7

### Epic 2: Classificação e Formato Corretos de Erros HTTP

Consumidores da API recebem sempre o status HTTP correto (403 em negação de autorização, 400 em parâmetro inválido, 501 em não-implementado) em formato único e previsível (RFC 7807), inclusive em casos hoje tratados nativamente pelo Spring.

**FRs covered:** FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR34
**NFRs covered:** NFR5
**Depende de:** Epic 1 (FR11/FR34 movem a hierarquia de exceção para o `core`)

### Epic 3: Confiabilidade de Idempotência sob Concorrência e Falha do Redis

Chamadas concorrentes com a mesma chave nunca duplicam efeito de negócio (lock atômico, 409 em concorrência, 422 em colisão de payload); indisponibilidade do Redis nunca bloqueia o negócio (fail-open + circuit breaker), com a constraint `UNIQUE` do banco como garantia real.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR25, FR26, FR27, FR28, FR29, FR30, FR31, FR32, FR33
**NFRs covered:** NFR3, NFR6
**Additional:** ADD-3, ADD-4
**Depende de:** Epic 1 (usa o `jdempotent-api` criado na Fase 2 do F3)

### Epic 4: Piso de Documentação Obrigatório em Todo o Repositório

Todo módulo do repositório — novo ou existente, tocado ou não por este ciclo — expõe Javadoc em API pública, comentário onde a lógica não é óbvia, diagrama Mermaid de fluxo de uso e README, antes do release da 1.2.0.

**FRs covered:** nenhum diretamente (movido por NFR7)
**NFRs covered:** NFR7
**Additional:** ADD-8
**Depende de:** Epics 1–3 (para documentar os módulos novos que eles criam; stories sobre `privacy`/`audit` são independentes entre si)

---

## Epic 1: Modularização e Fronteiras Estruturais do `utils`

Consumidores da lib passam a importar apenas os módulos de que precisam (ex.: `core` para `DateUtils`) sem arrastar JPA/Redis/Feign transitivamente; o build recusa automaticamente qualquer violação de fronteira entre módulos.

### Story 1.1: Congelar o inventário classe→módulo

**Requisitos:** FR23

Como mantenedor do `scos-foundation`,
Eu quero um inventário congelado de destino para cada uma das 71 classes de `utils`,
Para que nenhuma migração posterior deixe uma classe sem módulo de destino.

**Acceptance Criteria:**

**Given** as 71 classes atuais de `scos-foundation-utils`
**When** o inventário de destino é revisado
**Then** cada classe tem exatamente um módulo-alvo listado
**And** nenhum destino é `utils.utils` ou pacote genérico equivalente
**And** o inventário está documentado e acessível como referência única para as demais stories deste epic

### Story 1.2: Remover dependências mortas e obsoletas

**Requisitos:** FR22

Como mantenedor do `scos-foundation`,
Eu quero remover bibliotecas sem uso real e substituir as com uso mínimo,
Para reduzir a superfície de dependências transitivas antes de mover qualquer classe.

**Acceptance Criteria:**

**Given** o POM atual do `utils`
**When** o build é executado após a limpeza
**Then** `bouncycastle`, `snakeyaml` e `mapstruct` não aparecem mais como dependências
**And** `guava` foi substituído por `commons-lang3` no único ponto de uso
**And** a avaliação de substituição de `commons-io` por `java.nio` e da necessidade de `spring-cloud-starter` está documentada com a decisão tomada

### Story 1.3: Migrar serialização JSON de Gson para Jackson

**Requisitos:** FR21

Como mantenedor do `scos-foundation`,
Eu quero que toda a base use Jackson em vez de Gson,
Para eliminar duplicidade de serializadores antes da decomposição modular.

**Acceptance Criteria:**

**Given** `GsonUtils` e os 3 adapters de `java.time` hoje em uso
**When** a migração é concluída
**Then** `GsonUtils` e os adapters são removidos
**And** `JsonMasker` (módulo `privacy`) e os 4 pontos de uso em `audit` passam a usar Jackson
**And** a política de nulos é preservada via `@JsonInclude` documentado
**And** revisão manual confirma que `JsonMasker` continua um único loop O(n)
**And** antes da migração, é verificado se existe hash-chain persistida em ambiente piloto no `audit` (OQ-4 do PRD) — a migração muda o hash calculado sobre o JSON serializado, invalidando cadeias existentes se não forem removidas/reprocessadas antes
**And** o inventário de classes com serialização customizada (`TypeAdapter` Gson próprio) é levantado além dos 3 adapters de `java.time` já conhecidos — incluindo os value objects `Cpf`/`Cnpj`/`Email`/`TaxIdentifier` (ainda em `utils` neste ponto, migram para `validation` só na Story 1.9) — e cada um migrado tem teste confirmando que não serializa como `{}` vazio (Jackson exige getter/anotação onde Gson refletia campo privado direto)
**And** um teste de determinismo garante que a serialização usada pelo hash-chain do `audit` produz o mesmo resultado entre execuções (ordem de campos, formatação de número) — não só no corte pontual do OQ-4, mas como invariante contínua, para não quebrar de novo se alguma configuração de `ObjectMapper` mudar no futuro
**And** o caminho de travessia genérica de JSON do `JsonMasker` (`Map<String,Object>`) é testado quanto a tipos numéricos (`Integer`/`Long`/`BigDecimal` do Jackson vs. `Double`/`LazilyParsedNumber` do Gson) para garantir que nenhuma checagem de tipo dependa do comportamento antigo
**And** os 4 pontos de uso em `audit` (`ScosAuditHashService`, `ScosAuditServiceBean`, `ScosAuditBatchConsumer`, `ScosAuditDlqJob`) têm seu tratamento de exceção revisado — `catch` de `JsonSyntaxException` (Gson, unchecked) é substituído pelo equivalente Jackson (`JsonProcessingException`, checked), preservando o comportamento de fallback/retry existente
**And** a mudança de formato de data (Jackson `jackson-datatype-jsr310` vs. os 3 adapters customizados removidos) é registrada no CHANGELOG como mudança de formato de wire, não só como detalhe interno do hash-chain

### Story 1.4: Promover o perfil `analyze` (Checkstyle + ArchUnit) para `pluginManagement` do POM pai

**Requisitos:** FR20, ADD-2

Como mantenedor do `scos-foundation`,
Eu quero que o perfil `analyze` cubra 100% dos módulos a partir do POM pai,
Para que nenhum módulo novo nasça sem o gate mecânico.

**Acceptance Criteria:**

**Given** o perfil `analyze` hoje presente em 4 de 5 módulos
**When** ele é promovido a `pluginManagement` do POM pai
**Then** todo módulo do reactor (existente e futuro) herda o perfil sem precisar declará-lo individualmente
**And** a dependência `com.tngtech.archunit:archunit-junit5:1.5.0` (escopo `test`) é adicionada ao gerenciamento de dependências do POM pai
**And** o `failOnViolation` do Checkstyle **não** é ativado globalmente nesta story — o mecanismo fica disponível, mas bloquear o build do reactor inteiro só acontece na Story 4.16, depois que todo módulo já tiver Javadoc (evita quebrar o build de `privacy`/`audit`/`jdempotent`/`utils`/`exception`, hoje com Javadoc só informal, antes do Epic 4 documentá-los)

### Story 1.5: Criar módulos `*-api` e mover as anotações de contrato

**Requisitos:** FR18, FR19, FR20

Como time consumidor de domínio puro (ex.: SCOS-Flow),
Eu quero anotações `@Auditable`/`@Jdempotent*`/de validação disponíveis sem depender de implementação,
Para poder anotar meu domínio sem carregar Spring/JPA.

**Acceptance Criteria:**

**Given** as anotações hoje presas aos módulos de implementação
**When** `audit-api`, `jdempotent-api` e `validation-api` são criados
**Then** cada um contém apenas `@interface`/`enum`, sem dependência além de `jakarta.validation-api`
**And** uma regra ArchUnit local em cada módulo `*-api` falha o build se qualquer classe de lógica ou dependência de runtime além de `jakarta.validation-api` for adicionada

### Story 1.6: Criar o módulo `archtest` para regras cross-módulo

**Requisitos:** ADD-2

Como mantenedor do `scos-foundation`,
Eu quero um módulo de teste dedicado para regras ArchUnit que citam mais de um módulo,
Para que nenhuma regra cross-módulo fique duplicada ou ausente.

**Acceptance Criteria:**

**Given** que nenhum módulo de implementação enxerga o classpath inteiro sozinho
**When** o módulo `archtest` é criado (`scope=test`, sem código de produção, dependendo de todos os outros só para teste)
**Then** ele compila e roda no perfil `analyze` do build do reactor
**And** o módulo está pronto para receber a primeira regra cross-módulo nas stories seguintes

### Story 1.7: Extrair o módulo `core`

**Requisitos:** FR18, FR19, FR20, NFR2, NFR4

Como time consumidor que só precisa de utilitários simples,
Eu quero um módulo `core` sem dependência de Spring/JPA/Servlet,
Para importar `DateUtils`/`HashUtils` sem carregar o resto da stack.

**Acceptance Criteria:**

**Given** as classes do inventário (Story 1.1) destinadas a `core` (`DateUtils`, `HashUtils`, `StringFieldUtils`, `PropertiesOrder`, `ScosBaseUseCase`, `ScosUserAuthentication`)
**When** o módulo é extraído em 2 commits separados (mover vs. ajustar comportamento)
**Then** `core` compila sem `org.springframework`, `jakarta.persistence` ou `jakarta.servlet` no classpath
**And** uma regra ArchUnit local em `core` falha o build se qualquer um desses pacotes for importado
**And** os testes existentes das classes migradas continuam verdes sem alteração de comportamento
**And** `ScosStartupListener` **não** entra nesta lista apesar de listado como `core` no addendum do PRD — sua assinatura (`onStartupSystem(ApplicationReadyEvent event)`) importa `org.springframework.boot.context.event.ApplicationReadyEvent`, violando a regra de zero-Spring do `core`; ele é migrado na Story 1.8 (`spring`), junto de `ScosOnStartupListener`, que já o consome via `List<ScosStartupListener>`

### Story 1.8: Extrair o módulo `spring`

**Requisitos:** FR18, FR19, FR20, NFR2, NFR4

Como time consumidor que usa aspectos genéricos do Spring,
Eu quero um módulo `spring` isolado,
Para não herdar JPA/Servlet ao usar `ScosRule`.

**Acceptance Criteria:**

**Given** as classes do inventário destinadas a `spring` (`ScosRule`, `ScosRuleService`, `NormalizeStrings`, `StringProcessingAspect`, `ScosOnStartupListener`, `ScosStartupListener`)
**When** o módulo é extraído em 2 commits separados
**Then** `spring` depende de `core` mas não importa `jakarta.servlet`, `jakarta.persistence` nem `spring.data`
**And** uma regra ArchUnit local em `spring` impõe essa restrição
**And** os testes migrados permanecem verdes

### Story 1.9: Extrair o módulo `validation`

**Requisitos:** FR18, NFR2, NFR4

Como time consumidor que usa value objects brasileiros (CPF/CNPJ),
Eu quero um módulo `validation` próprio,
Para não carregar JPA completo só para validar um documento.

**Acceptance Criteria:**

**Given** `Cpf`, `Cnpj`, `Email`, `TaxIdentifier` e o restante do inventário destinado a `validation`
**When** o módulo é extraído dependendo de `core` e `validation-api`, com `jakarta.persistence-api` como `provided`
**Then** `validation` compila e os testes dos value objects permanecem verdes
**And** a extração ocorre em 2 commits separados (mover vs. ajustar comportamento)

### Story 1.10: Extrair o módulo `cache`

**Requisitos:** FR18, NFR2, NFR4

Como time consumidor que usa cache Redis,
Eu quero um módulo `cache` isolado,
Para não herdar JPA ao habilitar apenas cache.

**Acceptance Criteria:**

**Given** `PolymorphicRedisSerializer` e demais classes de `configuration/cache/*` do inventário
**When** o módulo `cache` é extraído dependendo apenas de `core`
**Then** `cache` compila isoladamente e os testes migrados permanecem verdes
**And** a extração ocorre em 2 commits separados

### Story 1.11: Extrair o módulo `jpa`

**Requisitos:** FR18, NFR2, NFR4

Como time consumidor que usa JPA,
Eu quero um módulo `jpa` isolado,
Para não herdar Redis/Feign ao habilitar apenas persistência.

**Acceptance Criteria:**

**Given** `SpecificationRepository`, `BaseEntity`, `JacksonCustomJsonFormatMapper`, `BaseLiquibaseProperties` do inventário
**When** o módulo `jpa` é extraído dependendo de `core` e `validation`
**Then** `jpa` compila isoladamente e os testes migrados permanecem verdes
**And** a extração ocorre em 2 commits separados

### Story 1.12: Extrair o módulo `web`

**Requisitos:** FR18, ADD-1, NFR2, NFR4

Como time consumidor de endpoints REST,
Eu quero um módulo `web` com `@Cacheable` embutido,
Para ligar controllers sem montar a integração manualmente.

**Acceptance Criteria:**

**Given** `ScosController`, `IpAddressExtractor`, `ScosResponseUtils`, `PaginationUtils`, `JacksonXmlUtils`, `MultiReadHttpServletRequest`, `ScosJacksonConfig`, `LoggingInitialFilter`/`LoggingFinalFilter` do inventário
**When** o módulo `web` é extraído dependendo de `core`, `cache` e `privacy`
**Then** `web` compila isoladamente, `@Cacheable` funciona nas anotações `ScosRequestGET/POST/PUT/DELETE`, e os testes migrados permanecem verdes

### Story 1.13: Extrair o módulo `feign`

**Requisitos:** FR18, NFR2, NFR4

Como time consumidor que integra via Feign,
Eu quero um módulo `feign` dedicado,
Para não herdar essa dependência ao usar só `web` ou `core`.

**Acceptance Criteria:**

**Given** `JacksonEncoderCustom`, `JacksonDecoderCustom` do inventário
**When** o módulo `feign` é extraído dependendo apenas de `core`
**Then** `feign` compila isoladamente e os testes migrados permanecem verdes
**And** a extração ocorre em 2 commits separados

### Story 1.14: Impor regras ArchUnit cross-módulo e remover `utils` do reactor

**Requisitos:** FR18, FR19, FR20, ADD-1

Como mantenedor do `scos-foundation`,
Eu quero que o build falhe automaticamente se qualquer módulo violar a fronteira de dependência global,
Para que a decomposição não regrida silenciosamente.

**Acceptance Criteria:**

**Given** o módulo `archtest` (Story 1.6) e todos os módulos extraídos (Stories 1.5–1.13)
**When** as regras cross-módulo são adicionadas
**Then** o build falha se algum módulo além de uma aplicação consumidora depender de `web`
**And** o build falha se houver ciclo entre quaisquer dois módulos do reactor
**And** após a última classe migrada, `scos-foundation-utils` é removido do reactor Maven
**And** **pendência conhecida, não bloqueante desta story**: FR-19/AD-1 definem regras negativas explícitas só para `core`, `spring`, `*-api` e a proibição genérica de depender de `web` — não há regra declarada especificamente para o que `cache`/`jpa`/`feign`/`audit-api` **não podem** importar. A cobertura "100%" de FR-20 é satisfeita aqui pelas regras cross-módulo (ciclo, dependência de `web`) mais o próprio grafo de dependência Maven (um módulo só carrega o que declara); se uma regra negativa específica para esses módulos for necessária, isso deve ser levantado com quem mantém o PRD/Architecture antes da implementação, não decidido ad-hoc nesta story

### Story 1.15: Emitir log de inicialização por módulo de implementação

**Requisitos:** FR24

Como mantenedor operando em produção,
Eu quero um log `INFO` na subida de cada módulo de implementação informando quantas classes anotadas foram encontradas,
Para detectar um módulo `-api` usado sem a implementação correspondente no classpath.

**Acceptance Criteria:**

**Given** uma aplicação consumidora com anotações de `jdempotent-api`/`audit-api`/`validation-api` no classpath
**When** a aplicação sobe com o módulo de implementação correspondente presente
**Then** um log `INFO` é emitido contando quantas classes anotadas foram encontradas
**And** módulos `*-api` não emitem esse log (não têm lógica de runtime)
**And** cada README de módulo `-api` abre com a frase "este artefato não executa nada; a implementação é `scos-foundation-<x>`"

---

## Epic 2: Classificação e Formato Corretos de Erros HTTP

Consumidores da API recebem sempre o status HTTP correto (403 em negação de autorização, 400 em parâmetro inválido, 501 em não-implementado) em formato único e previsível (RFC 7807), inclusive em casos hoje tratados nativamente pelo Spring.

### Story 2.1: Corrigir o handler de acesso negado (403)

**Requisitos:** FR9, NFR5

Como consumidor da API protegida por Spring Security,
Eu quero que uma negação de autorização real responda `403`,
Para não receber `500` num erro que na verdade é de permissão.

**Acceptance Criteria:**

**Given** um teste que reproduz o bug (chamada negada por `org.springframework.security.access.AccessDeniedException` hoje capturada como `500`)
**When** o teste é escrito e falha antes da correção
**Then** o handler passa a capturar `AccessDeniedException` e responde `403`
**And** o handler existente para `AuthorizationDeniedException` continua lado a lado, sem substituição

### Story 2.2: Corrigir o handler de validação para parâmetro simples (400)

**Requisitos:** FR10, NFR5

Como consumidor da API,
Eu quero que uma violação em `@RequestParam @Min(1) int page` responda `400`,
Para não receber `500` por uma exceção não tratada.

**Acceptance Criteria:**

**Given** um teste que reproduz o `IndexOutOfBoundsException` hoje lançado em `getBeanResults().get(0)` para parâmetro simples
**When** o teste é escrito e falha antes da correção
**Then** o handler passa a iterar sobre `getBeanResults()` e `getValueResults()` e responde `400`

### Story 2.3: Retornar 501 para funcionalidade não implementada

**Requisitos:** FR15

Como consumidor da API,
Eu quero que uma rota marcada como não implementada responda `501`,
Para distinguir isso de um erro genérico de servidor.

**Acceptance Criteria:**

**Given** uma chamada que lança `MethodNotImplementedException`
**When** o handler processa a exceção
**Then** a resposta é `501` em vez do `500` genérico atual

### Story 2.4: Padronizar log por faixa de status HTTP

**Requisitos:** FR16

Como operador monitorando a aplicação,
Eu quero que erros `4xx` logem em `WARN` sem stack trace e `5xx` em `ERROR` com stack trace,
Para não poluir alertas com ruído de erro de cliente.

**Acceptance Criteria:**

**Given** exceções mapeadas para diferentes faixas de status
**When** cada uma é tratada pelo handler
**Then** `4xx` loga em `WARN` sem stack trace, `5xx` em `ERROR` com stack trace, e `ScosNoContentException` (204) em `DEBUG`
**And** o handler genérico (fallback sem tipo específico) é o único que loga `ERROR` incondicionalmente
**And** todo uso de Log4j2 direto é substituído por `@Slf4j`

### Story 2.5: Corrigir a resolução de título de erro para Jackson 3

**Requisitos:** FR14

Como consumidor da API recebendo erros de deserialização,
Eu quero uma mensagem de erro correta mesmo com Jackson 3,
Para não receber um título genérico ou quebrado.

**Acceptance Criteria:**

**Given** um teste que confirma se o regex atual de `resolveTitle` ainda casa com as mensagens do Jackson 3
**When** o teste falha (regex desatualizado) ou passa
**Then** `resolveTitle` passa a navegar a causa (`InvalidFormatException`/`MismatchedInputException.getPath()`) em vez de usar regex

### Story 2.6: Corrigir `resolveTitle` para não usar try/catch como controle de fluxo

**Requisitos:** FR34, NFR5

Como consumidor da API localizada,
Eu quero receber o título de erro traduzido mesmo quando o `LocaleService` falha,
Para não ver um literal em inglês ("Business Error") numa API em PT-BR.

**Acceptance Criteria:**

**Given** um teste que reproduz o mascaramento de falha real do `LocaleService` pelo try/catch atual
**When** o teste é escrito e falha antes da correção
**Then** `LocaleService` ganha `getMessageOrDefault(code, default)`, com o default vindo de `ExceptionCode.getTitle()`
**And** `resolveTitle` usa esse método em vez de try/catch

### Story 2.7: Unificar o formato de erro em `handleExceptionInternal`, incluindo 404 nativo

**Requisitos:** FR13, NFR5

Como consumidor da API,
Eu quero receber o mesmo formato de erro (`ScosProblemDetails`) em qualquer situação, inclusive rota inexistente,
Para não precisar tratar dois formatos diferentes.

**Acceptance Criteria:**

**Given** um teste que reproduz o formato nativo do Spring hoje devolvido para 404/método não suportado/media type inválido
**When** o teste é escrito e falha antes da correção
**Then** `handleExceptionInternal` é sobrescrito para unificar o formato em todos os casos, incluindo 404 de rota inexistente

### Story 2.8: Mover o contrato de domínio do `exception` para o `core`

**Requisitos:** FR11, NFR2

Como mantenedor do `scos-foundation`,
Eu quero que exceções de domínio não dependam de Spring,
Para que `core` continue sem essa dependência.

**Acceptance Criteria:**

**Given** `ScosException`, `ExceptionCode`, `ScosExceptionCode`, `LocaleService`, `ScosNoContentException`, `ScosNoRollbackException`, `ScosSecurityException`, `MethodNotImplementedException` já corrigidos nas stories anteriores
**When** essas classes são movidas para o módulo `core` (criado no Epic 1)
**Then** `core` continua compilando sem `org.springframework` no classpath
**And** o módulo `audit` é repontado para consumir `ScosException` do `core` em vez do `exception` antigo
**And** a extração ocorre em commit de "mover", separado de qualquer ajuste de comportamento

### Story 2.9: Mover a tradução HTTP do `exception` para o `web` e registrar via autoconfiguração

**Requisitos:** FR11, FR12, NFR2

Como consumidor da API,
Eu quero que o tratamento de erro HTTP seja ativado automaticamente ao importar o módulo `web`,
Para não precisar de código de integração manual.

**Acceptance Criteria:**

**Given** `ExceptionsHandler`, `ScosProblemDetails`, `ScosFieldError`, `ExceptionUtils` já corrigidos e testados
**When** são movidos para o módulo `web` (criado no Epic 1) e registrados via `AutoConfiguration.imports`
**Then** o handler é ativado por padrão via `@ConditionalOnProperty(scos.web.error-handler.enabled, matchIfMissing=true)` e ordenado com `@Order(Ordered.LOWEST_PRECEDENCE)`
**And** `scos-foundation-exception` deixa de existir como módulo e sai do reactor Maven

### Story 2.10: Consolidar a constante `MDC_REQUEST_ID` no `core`

**Requisitos:** FR17

Como mantenedor do `scos-foundation`,
Eu quero uma única fonte para a constante de correlação de log,
Para eliminar duplicidade entre `web` e `core`.

**Acceptance Criteria:**

**Given** `MDC_REQUEST_ID` hoje duplicada entre `ScosProblemDetails` (agora em `web`, Story 2.9) e `LoggingInitialFilter` (em `web`, Epic 1 Story 1.12)
**When** a constante é consolidada em um único ponto no módulo `core`
**Then** ambas as classes em `web` referenciam a mesma constante do `core`, sem duplicação

---

## Epic 3: Confiabilidade de Idempotência sob Concorrência e Falha do Redis

Chamadas concorrentes com a mesma chave nunca duplicam efeito de negócio (lock atômico, 409 em concorrência, 422 em colisão de payload); indisponibilidade do Redis nunca bloqueia o negócio (fail-open + circuit breaker), com a constraint `UNIQUE` do banco como garantia real.

### Story 3.1: Corrigir a inicialização do `RedisConnectionFactory`

**Requisitos:** FR25

Como time consumidor com Redis standalone ou cluster,
Eu quero que o módulo inicialize sem NPE,
Para poder habilitar `jdempotent` sem workaround.

**Acceptance Criteria:**

**Given** uma aplicação com Redis standalone/cluster (não Sentinel)
**When** o módulo inicializa usando `RedisConnectionFactory` do Spring Boot em vez de montar `RedisSentinelConfiguration` hardcoded
**Then** a inicialização não lança NPE em `getSentinel()`

### Story 3.2: Migrar hashing de MD5 para SHA-256

**Requisitos:** FR5, NFR3

Como mantenedor do `scos-foundation`,
Eu quero hashing criptograficamente mais forte,
Para reduzir risco de colisão de hex.

**Acceptance Criteria:**

**Given** o hashing atual via MD5 e `Integer.toHexString`
**When** a migração é concluída
**Then** o hashing usa SHA-256 via enum `CryptographyAlgorithm` e a formatação hex usa `HexFormat.of().formatHex()`
**And** um teste de colisão de hex (payloads escolhidos para produzir hashes diferentes) cobre a nova implementação

### Story 3.3: Resolver campos anotados em toda a hierarquia de classes

**Requisitos:** FR6

Como consumidor com hierarquia de herança nos DTOs,
Eu quero que todos os campos anotados componham a chave,
Para não ter colisão por campo herdado ignorado.

**Acceptance Criteria:**

**Given** uma classe com campos anotados herdados de uma superclasse
**When** a chave é composta
**Then** a resolução percorre toda a hierarquia (não apenas `getDeclaredFields()`)

### Story 3.4: Registrar `IdempotentAspect` sem duplicidade e sem `ThreadLocal`

**Requisitos:** FR29, NFR3

Como mantenedor do `scos-foundation`,
Eu quero que o aspecto não duplique bean quando há mais de um ponto de registro, e não use `ThreadLocal` para `MessageDigest`,
Para evitar NPE latente sob carga com virtual threads.

**Acceptance Criteria:**

**Given** mais de um ponto de registro do aspecto no contexto Spring
**When** `IdempotentAspect` é registrado com `@ConditionalOnMissingBean`
**Then** apenas um bean existe
**And** o uso de `ThreadLocal` para `MessageDigest` é removido
**And** um teste cobre o cenário de "duplo `IdempotentAspect`"

### Story 3.5: Tornar a aquisição do lock atômica (`tryAcquire`/`Lease`)

**Requisitos:** FR2, NFR3, ADD-4

Como consumidor fazendo chamadas concorrentes com a mesma chave,
Eu quero que a segunda chamada responda `409 IN_PROGRESS` em vez de `null` silencioso,
Para saber que já existe processamento em curso.

**Acceptance Criteria:**

**Given** duas chamadas concorrentes com a mesma chave
**When** a aquisição do lock passa a usar `tryAcquire(key, payloadHash, ttl) → Lease` atômico (Lua script), substituindo `contains → store → setResponse`
**Then** a segunda chamada responde `409 IN_PROGRESS`
**And** o TTL do lease é configurável por método (não fixo) e o tipo de `ttl` é sempre `java.time.Duration`
**And** um teste de concorrência real (não simulado) cobre esse cenário
**And** um teste cobre o cenário do lease expirar antes do método protegido terminar (risco catalogado no plano de origem, probabilidade média): o comportamento observável é documentado e a métrica `idempotency.in_progress` (FR7) permite detectar esse caso em produção

### Story 3.6: Detectar colisão de payload sob a mesma chave

**Requisitos:** FR1

Como consumidor,
Eu quero que duas requisições distintas com a mesma chave mas payload diferente respondam `422 PAYLOAD_MISMATCH`,
Para não receber por engano a resposta cacheada de outra requisição.

**Acceptance Criteria:**

**Given** duas requisições com a mesma chave e hash de payload distinto
**When** a segunda chega
**Then** a resposta é `422 PAYLOAD_MISMATCH` em vez da resposta cacheada compartilhada
**And** quando as duas condições coincidem na mesma janela de corrida (mesma chave, payload diferente, primeira ainda em processamento), a checagem de mismatch de payload tem precedência sobre o `409 IN_PROGRESS` — a segunda requisição recebe `422 PAYLOAD_MISMATCH`, não `409`, porque o mismatch é semanticamente o erro mais específico

### Story 3.7: Garantir fail-open com circuit breaker quando o Redis está indisponível

**Requisitos:** FR4, NFR3, ADD-3

Como consumidor,
Eu quero que a indisponibilidade do Redis nunca bloqueie minha requisição de negócio,
Para não sofrer indisponibilidade em cascata por causa do cache de idempotência.

**Acceptance Criteria:**

**Given** o Redis indisponível ou lento
**When** o circuit breaker (`io.github.resilience4j:resilience4j-spring-boot4:2.4.0`, `optional=true`) detecta via `slow-call-duration-threshold` respeitando `spring.data.redis.timeout`
**Then** a requisição de negócio prossegue sem bloqueio (nunca `FAIL_CLOSED`)
**And** um teste com Testcontainers simulando indisponibilidade do Redis cobre esse cenário
**And** um teste cobre o cenário de split-brain: lock adquirido com sucesso (Redis up), Redis cai durante o processamento, `setResponse` falha — a requisição ainda retorna sucesso ao cliente (fail-open), mas o comportamento (resposta não fica cacheada, retry subsequente reexecuta) é documentado explicitamente como risco aceito, não como bug
**And** um teste cobre a janela de transição `OPEN → HALF_OPEN` do circuit breaker: duas chamadas concorrentes com a mesma chave nessa janela não podem ambas contornar o lock (uma via chamada de teste ao Redis real, outra via fail-open preventivo)

### Story 3.8: Tornar a política de falha por exceção de negócio declarável por método

**Requisitos:** FR26

Como consumidor cujo endpoint pode falhar por regra de negócio,
Eu quero escolher entre `RELEASE` (permite retry) e `KEEP_FAILED` (evita duplicar efeito colateral),
Para adequar o comportamento ao meu caso de uso.

**Acceptance Criteria:**

**Given** um método anotado com a política `KEEP_FAILED`
**When** a execução lança exceção de negócio
**Then** o erro é gravado como resultado (chave não é removida)
**And** o comportamento padrão (`RELEASE`, remove a chave) é mantido para métodos sem a anotação explícita

### Story 3.9: Posicionar o aspecto de idempotência fora do escopo transacional

**Requisitos:** FR27

Como consumidor usando `@Transactional`,
Eu quero que um rollback de transação não deixe a chave de idempotência órfã no Redis,
Para não bloquear indevidamente uma nova tentativa legítima.

**Acceptance Criteria:**

**Given** um método anotado com `@Jdempotent*` e `@Transactional` que sofre rollback
**When** o `@Order` do aspecto está fora do escopo do `@Transactional`
**Then** a chave não fica presa no Redis após o rollback

### Story 3.10: Tornar o namespace de prefixo de chave configurável

**Requisitos:** FR28

Como time consumidor compartilhando a mesma instância de Redis entre aplicações,
Eu quero configurar o namespace via propriedade Spring,
Para não colidir chaves entre aplicações diferentes.

**Acceptance Criteria:**

**Given** a leitura atual via `System.getenv(APP_NAME)` (silenciosamente vazia quando ausente)
**When** o namespace passa a ser obrigatório e configurável via propriedade Spring
**Then** a aplicação falha de forma explícita (não silenciosa) se o namespace não for configurado

### Story 3.11: Expor métricas de idempotência

**Requisitos:** FR7

Como operador monitorando idempotência em produção,
Eu quero métricas de acerto/colisão/degradação,
Para detectar problemas como cliente gerando chave dentro do laço de retry.

**Acceptance Criteria:**

**Given** operações de idempotência ocorrendo (acquire, hit, colisão, erro de backend, degradação)
**When** `IdempotencyMetrics` é implementado (no-op por padrão, Micrometer condicional)
**Then** as métricas `idempotency.acquired`, `.hit`, `.in_progress`, `.mismatch`, `.backend_error`, `.degraded` (gauge 0/1) e `.degraded.transitions` (counter) são expostas corretamente

### Story 3.12: Introduzir `IdempotencyKeyResolver` com composição de chave declarativa

**Requisitos:** FR8, ADD-4

Como consumidor definindo minha chave de idempotência,
Eu quero selecionar explicitamente os campos via `@JdempotentProperty`, com serialização canônica,
Para ter uma chave determinística independente da ordem dos campos.

**Acceptance Criteria:**

**Given** uma classe anotada com múltiplos `@JdempotentProperty`
**When** a chave é composta via `IdempotencyKeyResolver` usando serialização canônica (`TreeMap`)
**Then** a chave resultante é determinística e `@JdempotentId` deixa de compor a chave
**And** o mesmo `IdempotencyKeyResolver` é o único ponto de composição de chave, reutilizável por qualquer entrypoint futuro (HTTP ou mensageria)

### Story 3.13: Suportar header `Idempotency-Key` como fonte de chave

**Requisitos:** FR3

Como consumidor da API,
Eu quero enviar minha própria chave de idempotência via header,
Para controlar a chave sem depender só dos campos do corpo.

**Acceptance Criteria:**

**Given** uma requisição HTTP com o header `Idempotency-Key`
**When** `@JdempotentResource(keySource=HEADER_THEN_FIELDS, headerName="Idempotency-Key", onMismatch=CONFLICT)` está configurado
**Then** a precedência é header → campos anotados → hash, e `X-Request-ID` nunca é reutilizado para esse fim
**And** para contexto de mensageria (sem contexto web), o resolver de chave devolve `null` de forma limpa, nunca lança exceção

### Story 3.14: Migrar configuração para `@ConfigurationProperties`

**Requisitos:** FR30

Como time consumidor configurando o módulo,
Eu quero propriedades tipadas e centralizadas,
Para não depender de `@Value` solto nem de propriedades mortas.

**Acceptance Criteria:**

**Given** a configuração atual via `@Value` e um `EnvironmentPostProcessor` declarado incorretamente em `AutoConfiguration.imports` (nunca executa)
**When** a migração para `@ConfigurationProperties` é concluída
**Then** propriedades mortas são removidas e o `EnvironmentPostProcessor` passa a executar corretamente

### Story 3.15: Corrigir TTL e `equals`/`hashCode`

**Requisitos:** FR31

Como mantenedor do `scos-foundation`,
Eu quero que o TTL configurado seja sempre respeitado e que os objetos de requisição tenham `equals`/`hashCode` corretos,
Para eliminar comportamento inconsistente entre construtores.

**Acceptance Criteria:**

**Given** os 7 construtores de `InMemoryIdempotentRepository` (hoje 4 ignoram o TTL configurado)
**When** a correção é aplicada
**Then** todos os construtores respeitam o TTL
**And** `equals`/`hashCode` de `IdempotentRequestWrapper` passam a ser reflexivos e simétricos

### Story 3.16: Adicionar allowlist de tipos no `PolymorphicRedisSerializer`

**Requisitos:** FR32

Como mantenedor preocupado com segurança,
Eu quero que apenas tipos permitidos sejam desserializados do Redis,
Para eliminar o risco de desserialização de tipo arbitrário.

**Acceptance Criteria:**

**Given** um valor vindo do Redis antes de `Class.forName`
**When** a allowlist de tipos permitidos é aplicada
**Then** tipos fora da allowlist são rejeitados antes da desserialização

### Story 3.17: Substituir construtores telescópicos por builder e documentar o princípio de design

**Requisitos:** FR33, NFR6

Como consumidor configurando o módulo `jdempotent`,
Eu quero uma API fluente (builder) e um README claro sobre a garantia real,
Para não instanciar construtores longos nem confiar só no Redis como barreira.

**Acceptance Criteria:**

**Given** os construtores telescópicos atuais
**When** são substituídos por builder
**Then** a configuração do módulo passa a usar a API fluente
**And** o README do módulo documenta o princípio "cache é fast-path, não garantia" e a obrigatoriedade da constraint `UNIQUE` no banco para chaves naturais
**And** o README documenta a relação recomendada entre os três timeouts independentes do módulo (`ttl` do lease > `slow-call-duration-threshold` do circuit breaker > `spring.data.redis.timeout`, com margem) — dimensionamento fica a cargo do time consumidor (OQ-3 do PRD), mas a invariante de ordem relativa é registrada para evitar ambiguidade sobre quem é o dono real do lock quando um timeout expira antes do outro

---

## Epic 4: Piso de Documentação Obrigatório em Todo o Repositório

Todo módulo do repositório — novo ou existente, tocado ou não por este ciclo — expõe Javadoc em API pública, comentário onde a lógica não é óbvia, diagrama Mermaid de fluxo de uso e README, antes do release da 1.2.0.

### Story 4.1: Diagnosticar o gate mecânico de Javadoc via Checkstyle

**Requisitos:** NFR7

Como mantenedor do `scos-foundation`,
Eu quero confirmar, sem ativar nada globalmente ainda, se o Checkstyle realmente falharia o build para API pública sem Javadoc,
Para saber se a Story 4.16 (ativação final) vai precisar corrigir a amarração do `goal=check` ou só ligar o `failOnViolation`.

**Acceptance Criteria:**

**Given** o perfil `analyze` já promovido a `pluginManagement`, sem `failOnViolation` global ativo (Epic 1, Story 1.4)
**When** `mvn -Panalyze verify` é executado isoladamente num módulo de teste/scratch com um método público sem Javadoc introduzido de propósito
**Then** o resultado (build falha ou não) é documentado como diagnóstico
**And** nenhuma configuração é alterada nesta story — se o `goal=check` não estiver amarrado, isso fica registrado como item de entrada para a Story 4.16, não corrigido aqui

### Story 4.2: Documentar o módulo `core`

**Requisitos:** NFR7

Como consumidor avaliando o `core` antes de importar,
Eu quero Javadoc completo, comentários onde a lógica não é óbvia, README e diagrama de fluxo,
Para entender o contrato sem ler a implementação.

**Acceptance Criteria:**

**Given** o módulo `core` (Epic 1, Story 1.7; Epic 2, Story 2.8)
**When** a documentação é adicionada
**Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso

### Story 4.3: Documentar o módulo `audit-api`

**Requisitos:** NFR7

Como consumidor de domínio puro,
Eu quero saber pelo README que este artefato não executa nada sozinho,
Para não integrá-lo sem a implementação correspondente.

**Acceptance Criteria:**

**Given** o módulo `audit-api` (Epic 1, Story 1.5)
**When** a documentação é adicionada
**Then** o README abre com "este artefato não executa nada; a implementação é `scos-foundation-audit`" e traz diagrama Mermaid do fluxo típico de uso
**And** toda anotação pública tem Javadoc

### Story 4.4: Documentar o módulo `jdempotent-api`

**Requisitos:** NFR7

Como consumidor de domínio puro,
Eu quero saber pelo README que este artefato não executa nada sozinho,
Para não integrá-lo sem a implementação correspondente.

**Acceptance Criteria:**

**Given** o módulo `jdempotent-api` (Epic 1, Story 1.5)
**When** a documentação é adicionada
**Then** o README abre com "este artefato não executa nada; a implementação é `scos-foundation-jdempotent`" e traz diagrama Mermaid do fluxo típico de uso
**And** toda anotação pública tem Javadoc

### Story 4.5: Documentar o módulo `validation-api`

**Requisitos:** NFR7

Como consumidor de domínio puro,
Eu quero saber pelo README que este artefato não executa nada sozinho,
Para não integrá-lo sem a implementação correspondente.

**Acceptance Criteria:**

**Given** o módulo `validation-api` (Epic 1, Story 1.5)
**When** a documentação é adicionada
**Then** o README abre com "este artefato não executa nada; a implementação é `scos-foundation-validation`" e traz diagrama Mermaid do fluxo típico de uso
**And** toda anotação pública tem Javadoc

### Story 4.6: Documentar o módulo `archtest`

**Requisitos:** NFR7

Como mantenedor entendendo a suíte de regras cross-módulo,
Eu quero um README explicando o propósito do módulo,
Para saber onde adicionar uma nova regra ArchUnit cross-módulo.

**Acceptance Criteria:**

**Given** o módulo `archtest` (Epic 1, Story 1.6)
**When** a documentação é adicionada
**Then** o README explica o propósito (regras ArchUnit cross-módulo, sem código de produção) e lista as regras existentes
**And** não se aplica gate de Javadoc (módulo sem API pública de produção)

### Story 4.7: Documentar o módulo `spring`

**Requisitos:** NFR7

Como consumidor usando aspectos genéricos do Spring,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender como `ScosRule` se integra à minha aplicação.

**Acceptance Criteria:**

**Given** o módulo `spring` (Epic 1, Story 1.8)
**When** a documentação é adicionada
**Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso

### Story 4.8: Documentar o módulo `validation`

**Requisitos:** NFR7

Como consumidor usando value objects brasileiros,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender o contrato de `Cpf`/`Cnpj`/`Email`/`TaxIdentifier`.

**Acceptance Criteria:**

**Given** o módulo `validation` (Epic 1, Story 1.9)
**When** a documentação é adicionada
**Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso

### Story 4.9: Documentar o módulo `cache`

**Requisitos:** NFR7

Como consumidor usando cache Redis,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender a configuração de `PolymorphicRedisSerializer`.

**Acceptance Criteria:**

**Given** o módulo `cache` (Epic 1, Story 1.10)
**When** a documentação é adicionada
**Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso

### Story 4.10: Documentar o módulo `jpa`

**Requisitos:** NFR7

Como consumidor usando persistência,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender `SpecificationRepository`/`BaseEntity`.

**Acceptance Criteria:**

**Given** o módulo `jpa` (Epic 1, Story 1.11)
**When** a documentação é adicionada
**Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso

### Story 4.11: Documentar o módulo `web`

**Requisitos:** NFR7

Como consumidor de endpoints REST,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender como `ScosController` e o tratamento de erro se conectam.

**Acceptance Criteria:**

**Given** o módulo `web` (Epic 1, Story 1.12; Epic 2, Story 2.9)
**When** a documentação é adicionada
**Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso

### Story 4.12: Documentar o módulo `feign`

**Requisitos:** NFR7

Como consumidor integrando via Feign,
Eu quero Javadoc, README e diagrama de fluxo,
Para entender `JacksonEncoderCustom`/`DecoderCustom`.

**Acceptance Criteria:**

**Given** o módulo `feign` (Epic 1, Story 1.13)
**When** a documentação é adicionada
**Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama Mermaid do fluxo típico de uso

### Story 4.13: Documentar o módulo `jdempotent`

**Requisitos:** NFR7

Como consumidor habilitando idempotência,
Eu quero Javadoc, README e diagrama de sequência do fluxo de aquisição de lock,
Para entender a garantia real sob fail-open.

**Acceptance Criteria:**

**Given** o módulo `jdempotent` já com Checkstyle ativo e o README parcial da Story 3.17 (princípio "cache é fast-path")
**When** a documentação é completada
**Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama de sequência Mermaid do fluxo `tryAcquire` → `Lease` → fail-open

### Story 4.14: Documentar o módulo `audit`

**Requisitos:** NFR7

Como consumidor usando auditoria,
Eu quero um diagrama de fluxo de uso,
Para entender o fluxo sem ler o código.

**Acceptance Criteria:**

**Given** o módulo `audit` (README já existente, repontado para `core` na Story 2.8)
**When** o diagrama Mermaid é adicionado ao README
**Then** o README passa a ter o diagrama do fluxo típico de uso
**And** toda API pública mantém Javadoc (gate já ativo)

### Story 4.15: Documentar o módulo `privacy`

**Requisitos:** NFR7

Como consumidor usando sanitização de dados,
Eu quero o perfil `analyze` ligado e um diagrama de fluxo de uso,
Para ter o mesmo piso de qualidade dos demais módulos.

**Acceptance Criteria:**

**Given** o módulo `privacy` (não tocado funcionalmente neste ciclo, README já existente, sem perfil `analyze` hoje)
**When** o perfil `analyze` é ligado e o diagrama Mermaid é adicionado ao README
**Then** o Checkstyle passa a cobrir `privacy` e o README tem o diagrama do fluxo típico de uso

### Story 4.16: Ativar globalmente o gate mecânico de Checkstyle

**Requisitos:** NFR7

Como mantenedor do `scos-foundation`,
Eu quero que o build do reactor inteiro falhe para qualquer API pública sem Javadoc,
Para que o piso de documentação seja garantido mecanicamente, não só por checagem manual, dali em diante.

**Acceptance Criteria:**

**Given** todos os módulos (Stories 4.2–4.15) já com Javadoc completo, e o diagnóstico da Story 4.1 sobre o estado real do `goal=check`
**When** o `failOnViolation=true` é ativado no `pluginManagement` do POM pai (corrigindo a amarração do `goal=check` primeiro, se o diagnóstico da Story 4.1 tiver apontado que não estava amarrado)
**Then** `mvn -Panalyze verify` falha o build do reactor inteiro para qualquer método/tipo público sem Javadoc introduzido dali em diante
**And** o build do reactor, rodado nesse ponto com todos os módulos já documentados, passa verde
