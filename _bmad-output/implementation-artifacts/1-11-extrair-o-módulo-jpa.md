# Story 1.11: Extrair o módulo `jpa`

Status: done

<!-- baseline_commit: 85f9e0b3da2e993def4ff0c942f4d61542b42234 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como time consumidor que usa JPA,
Eu quero um módulo `jpa` isolado,
Para não herdar Redis/Feign ao habilitar apenas persistência.

## Acceptance Criteria

1. **Given** `SpecificationRepository`, `BaseEntity`, `JacksonCustomJsonFormatMapper`, `BaseLiquibaseProperties` do inventário (**+ `SpecificationFunction`, 5ª classe migrada por necessidade técnica não prevista nesta lista original; ver Debug Log Reference**), **When** o módulo `jpa` é extraído dependendo de `core` e `validation`, **Then** `jpa` compila isoladamente e os testes migrados permanecem verdes.
2. **And** a extração ocorre em 2 commits separados.

## Tasks / Subtasks

- [x] Task 1: Commit 1 — mover as 4 classes (AC: #1)
  - [x] Criar módulo Maven `scos-foundation-jpa`, pacote raiz `br.com.sawcunhaos.foundation.jpa`, dependendo de `core` (Story 1.7), `validation` (Story 1.9), `spring-boot-starter-data-jpa`, `querydsl-jpa`, `liquibase-core` (optional) (+ `tools.jackson.core:jackson-databind`, dependência descoberta não listada no AC — ver Debug Log)
  - [x] Mover: `utils/src/main/java/.../entity/BaseEntity.java`, `configuration/hibernate/JacksonCustomJsonFormatMapper.java`, `configuration/liquibase/BaseLiquibaseProperties.java`, `utils/SpecificationRepository.java` — **+ `enums/SpecificationFunction.java`, 5ª classe migrada por necessidade técnica não prevista neste bullet**: `SpecificationRepository` importa `SpecificationFunction`, cujo destino já era `core` no inventário congelado da Story 1.1 (nunca migrado pela Story 1.7); movida para `core/enums` agora para não recriar dependência de `jpa`→`utils`. Ver Debug Log.
  - [x] `QBaseEntity.java` (`utils/target/generated-sources/`) é artefato gerado pelo `apt-maven-plugin`/QueryDSL — **não mover manualmente**, será regenerado no novo módulo pela mesma configuração de annotation processor (replicar o plugin `com.mysema.maven:apt-maven-plugin` do `utils/pom.xml` no `jpa/pom.xml`) — confirmado: `mvn -pl jpa -am compile` gera `jpa/target/generated-sources/java/.../jpa/entity/QBaseEntity.java`
  - [x] Mover testes correspondentes, se existentes — **nenhum existia**: busca no repo inteiro antes da migração não encontrou teste próprio para nenhuma das 4 classes do AC nem para `SpecificationFunction`
  - [x] Commit isolado: só mover/renomear pacote — **com um ajuste mecânico obrigatório no mesmo commit**: `audit`'s `ScosAuditLiquibaseProperties` estende `BaseLiquibaseProperties` — import repontado e `scos-foundation-jpa` adicionado a `audit/pom.xml` (dependência nova, não troca, pois `audit` ainda usa `utils` em testes). Ver Debug Log.
- [x] Task 2: Commit 2 — ajustar o que precisar (AC: #2)
  - [x] Aplicar separadamente qualquer ajuste de comportamento necessário; documentar se não houver nenhum — **nenhum ajuste de comportamento no código movido**; os ajustes desta task são limpeza de dependências órfãs em `utils/pom.xml` (`spring-data-jpa`, `spring-boot-starter-data-jpa`, `querydsl-jpa`, bloco `apt-maven-plugin`) + uma regressão real de string-FQN encontrada pelos testes (ver Debug Log)

## Dev Notes

- Depende das Stories 1.7 (`core`) e 1.9 (`validation`) já concluídas — `jpa` é o primeiro módulo folha com dependência em outro módulo folha (`validation`), não só em `core`.
- Replicar a configuração do `apt-maven-plugin` (annotation processor QueryDSL) de `utils/pom.xml` para `jpa/pom.xml` — sem isso, `QBaseEntity` não é gerado e o build quebra silenciosamente em quem consome `Specification`/QueryDSL.
- Fase 4 do plano de origem: `jpa` é o quarto módulo folha a sair (depois de `spring`, `validation`, `cache`), antes de `web`.

### Project Structure Notes

- Módulo Maven novo: `jpa/` — depende de `core`, `validation`, `spring-boot-starter-data-jpa`, `querydsl-jpa`, `liquibase-core` (optional), `tools.jackson.core:jackson-databind` (ver Debug Log); replica o plugin `apt-maven-plugin` para geração de Q-classes.
- `utils/` perde `BaseEntity`, `JacksonCustomJsonFormatMapper`, `BaseLiquibaseProperties`, `SpecificationRepository` **+ `SpecificationFunction`** (5ª classe, não listada no AC — ver Debug Log) e as dependências `spring-data-jpa`/`spring-boot-starter-data-jpa`/`querydsl-jpa`/apt-maven-plugin, órfãs após a extração.
- `pom.xml` raiz ganha `<module>jpa</module>` (logo após `cache`, antes de `privacy`/`utils`) + `dependencyManagement` para `scos-foundation-jpa`.
- `core/enums` ganha `SpecificationFunction` (movida de `utils`, destino já previsto pelo inventário congelado da Story 1.1 mas nunca executado pela Story 1.7).
- `audit` ganha dependência em `scos-foundation-jpa` (soma, não troca — `scos-foundation-utils` continua em uso em testes de `audit`).

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#scos-foundation-jpa]
- [Source: utils/pom.xml#L233-L255] (config do `apt-maven-plugin` a replicar)
- [Source: _bmad-output/planning-artifacts/epics.md#story-111-extrair-o-módulo-jpa]
- [Source: _bmad-output/implementation-artifacts/inventario-classe-modulo.md#L34] (`SpecificationFunction` → `core`, atribuição pré-existente nunca executada pela Story 1.7)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- **Nota de processo**: o subagente de implementação inicial (dispatch padrão do workflow) falhou por atingir o limite de sessão da conta antes de produzir qualquer alteração de código (nenhum trabalho perdido — falhou durante a fase de leitura/investigação). A implementação foi retomada e concluída diretamente pela sessão principal, sem novo subagente, para não repetir o mesmo limite.
- **Premissa da story incompleta, descoberta ao ler `SpecificationRepository.java` antes de mover**: a classe importa `br.com.sawcunhaos.foundation.utils.enums.SpecificationFunction`, não listada nas 4 classes do AC. Conferido contra o inventário congelado da Story 1.1: `SpecificationFunction` já tinha destino `core` (linha 34), mas a Story 1.7 (extração de `core`) nunca a migrou — gap pré-existente, não causado por esta story, mas que esta story precisa resolver porque `jpa` não pode depender de `utils` (reintroduziria Redis/Feign, o problema que a story existe para resolver) nem de `validation` para algo que já tem destino definido em `core`. `SpecificationFunction` não tem nenhum import externo (enum puro, só lombok) — mover para `core/enums` é mecânico, zero risco, e completa uma atribuição já congelada em vez de inventar uma nova.
- **Dependência `tools.jackson.core:jackson-databind` não listada no Dev Notes**: `JacksonCustomJsonFormatMapper` implementa `org.hibernate.type.format.AbstractJsonFormatMapper` (Hibernate 7) usando `tools.jackson.core.JsonGenerator`/`JsonParser` e `tools.jackson.databind.ObjectMapper` diretamente — não vem transitivamente de `spring-boot-starter-data-jpa` (que fica só nos tipos Hibernate/JPA). Adicionada em escopo `compile` (não `test`, como `validation/pom.xml` fez para seu próprio caso — ali é só para teste de serialização; aqui é uso de produção).
- **Ajuste mecânico obrigatório dentro do próprio Commit 1**: `audit/src/main/java/.../ScosAuditLiquibaseProperties.java` estende `BaseLiquibaseProperties` — único uso desta classe em todo o repo (confirmado por busca). Import repontado para `br.com.sawcunhaos.foundation.jpa.liquibase` e `scos-foundation-jpa` adicionado como dependência **nova** (soma) em `audit/pom.xml` — diferente do caso `jdempotent`/`cache` da Story 1.10 (troca), porque `audit` continua usando `scos-foundation-utils` para outras coisas (confirmado: `LocaleUtilsBean`/`AuditTestApplication` em testes).
- **Regressão real encontrada pelos testes, não capturável por grep de import Java**: `audit/src/test/resources/application-postgres.yml` e `README.md` (documentação para consumidores externos) referenciam `JacksonCustomJsonFormatMapper` como **string literal** na propriedade Hibernate `spring.jpa.properties.hibernate.type.json_format_mapper` — Hibernate resolve essa string via `Class.forName` em tempo de bootstrap, não em tempo de compilação Java, então mover o pacote não gera nenhum erro de compilação, só falha em runtime (`StrategySelectionException`/`ClassNotFoundException`) ao subir o `EntityManagerFactory`. Confirmado rodando `mvn -pl audit -am test` **antes** da correção: 49 de 54 testes de `audit` falhavam com esse erro (não é fragilidade de Testcontainers/Docker como as falhas anteriormente documentadas em `deferred-work.md` — é uma regressão real desta story). Corrigido em ambos os arquivos (`br.com.sawcunhaos.foundation.utils.configuration.hibernate.JacksonCustomJsonFormatMapper` → `br.com.sawcunhaos.foundation.jpa.hibernate.JacksonCustomJsonFormatMapper`). Verificado: `mvn -pl audit -am test` → 54/54 verdes após a correção. **Risco residual para o Suggested Review Order**: nenhuma outra ocorrência desse padrão (FQN em string YAML/properties) foi encontrada no repo (`grep` confirmou), mas o padrão em si (Hibernate resolvendo `FormatMapper`/dialect/naming-strategy customizado por FQN string) pode se repetir em configs de aplicações consumidoras reais fora deste repositório, fora do alcance de qualquer grep neste repo.
- **Erro de processo próprio, corrigido no Commit 2**: o primeiro `git add` do Commit 1 falhou parcialmente por um pathspec inválido num dos arquivos (efeito colateral do `git mv` já ter movido o arquivo fisicamente antes da edição de pacote), abortando o comando inteiro sem staged nenhum arquivo daquela chamada — um `git add` de acompanhamento, mais restrito, cobriu o restante mas **não recapturou** a edição do pacote de `SpecificationFunction.java` (só a rename automática do `git mv`, com o conteúdo ainda antigo). Resultado: o Commit 1 (`677387c`) ficou com `core/enums/SpecificationFunction.java` declarando `package br.com.sawcunhaos.foundation.utils.enums;` — o import em `SpecificationRepository.java` não resolveria, quebrando a compilação do Commit 1 isolado. Detectado ao conferir `git status` antes do Commit 2 (o arquivo aparecia modificado de novo). Corrigido no Commit 2 (`parte 2 - ajustes`) — não é uma nova decisão de design, é a correção de um erro de staging.
- **Verificação**: `mvn -o -pl jpa -am compile` → verde, `QBaseEntity` gerado em `jpa/target/generated-sources/java/.../jpa/entity/QBaseEntity.java`. `mvn -o compile` (reactor inteiro) → verde. `mvn -o -pl jpa,core,utils,audit -am test` → verde após a correção da regressão do YAML (audit: 54/54; demais módulos sem regressão). `mvn -o -pl audit -am test` isolado, antes e depois da correção, confirma a causa raiz isolada (49 falhas → 0).

### Completion Notes List

- AC #1: `scos-foundation-jpa` criado, depende de `core` + `validation` + `spring-boot-starter-data-jpa`/`querydsl-jpa`/`liquibase-core` (optional) (+ `jackson-databind`, dependência descoberta); compila isoladamente e via reactor completo. Testes migrados: nenhum existia para as 4 classes do AC nem para `SpecificationFunction` (confirmado por busca antes da migração) — "testes migrados permanecem verdes" vale trivialmente.
- AC #2: extração em exatamente 2 commits git — **Commit 1** (`parte 1 - mover`): novo módulo `jpa` + as 4 classes do AC + `SpecificationFunction` (5ª classe, movida para `core`, ver Debug Log) + `pom.xml` raiz + ajuste mecânico em `audit` (import/dependência nova); **Commit 2** (`parte 2 - ajustes`): limpeza de dependências órfãs em `utils/pom.xml` + correção da regressão real de FQN-em-string em `audit/src/test/resources/application-postgres.yml` e `README.md`.
- **Desvio de escopo, documentado e não escondido**: `SpecificationFunction` migrou junto das 4 classes do AC por ser dependência direta de `SpecificationRepository` e já ter destino `core` congelado desde a Story 1.1 (nunca executado pela Story 1.7). Justificativa completa no Debug Log.
- `archtest` não ganhou dependência em `scos-foundation-jpa` — mesmo padrão das Stories 1.8-1.10, fora do escopo desta story de extração de um único módulo.
- Nenhuma regra ArchUnit local foi criada em `jpa` — mesmo precedente de `validation`/`cache` (Stories 1.9/1.10), que também não têm.

### File List

- `pom.xml` (raiz) — `<module>jpa</module>` adicionado (logo após `cache`) + `dependencyManagement` para `scos-foundation-jpa` + comentário sobre ordem de extração dos módulos-folha
- `jpa/pom.xml` (novo) — deps `scos-foundation-core`, `scos-foundation-validation`, `spring-boot-starter-data-jpa`, `querydsl-jpa`, `liquibase-core` (optional), `jackson-databind`, `lombok` (optional); test-scope `archunit-junit5`/`junit-jupiter`/`mockito-*`; plugin `apt-maven-plugin` (Q-class generation)
- `jpa/src/main/java/br/com/sawcunhaos/foundation/jpa/entity/BaseEntity.java` (movido de `utils`, sem alteração de lógica)
- `jpa/src/main/java/br/com/sawcunhaos/foundation/jpa/hibernate/JacksonCustomJsonFormatMapper.java` (movido, idem)
- `jpa/src/main/java/br/com/sawcunhaos/foundation/jpa/liquibase/BaseLiquibaseProperties.java` (movido, idem)
- `jpa/src/main/java/br/com/sawcunhaos/foundation/jpa/SpecificationRepository.java` (movido; import de `SpecificationFunction` repontado para `core.enums`)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/enums/SpecificationFunction.java` (movido de `utils` — 5ª classe, ver Debug Log — sem alteração de lógica)
- `audit/pom.xml` — dependência `scos-foundation-jpa` adicionada (soma, não troca)
- `audit/src/main/java/br/com/sawcunhaos/foundation/audit/configuration/properties/ScosAuditLiquibaseProperties.java` — import de `BaseLiquibaseProperties` repontado para `br.com.sawcunhaos.foundation.jpa.liquibase`
- `audit/src/test/resources/application-postgres.yml` — FQN string de `JacksonCustomJsonFormatMapper` corrigido (regressão real, ver Debug Log)
- `README.md` — mesmo FQN string corrigido na documentação de configuração para consumidores externos
- `utils/src/main/java/.../{entity/BaseEntity, configuration/hibernate/JacksonCustomJsonFormatMapper, configuration/liquibase/BaseLiquibaseProperties, utils/SpecificationRepository, enums/SpecificationFunction}.java` (removidos — movidos para `jpa`/`core`)
- `utils/pom.xml` — dependências `spring-data-jpa`, `spring-boot-starter-data-jpa`, `querydsl-jpa` e o bloco `build/plugins/apt-maven-plugin` removidos (órfãos após a extração)

## Suggested Review Order

**A regressão real: FQN em string de config (não em import Java)**

- Ponto de entrada: `json_format_mapper` aponta para o pacote novo — quebrava em runtime (`Class.forName` do Hibernate), não em compilação.
  [`application-postgres.yml:45`](../../audit/src/test/resources/application-postgres.yml#L45)

- Mesma correção na documentação para consumidores externos — se não fosse corrigida aqui, todo app externo que copiasse este trecho do README quebraria ao atualizar a lib.
  [`README.md:416`](../../README.md#L416)

**Desvio de escopo: 5ª classe (`SpecificationFunction`)**

- Import força a escolha: `SpecificationRepository` depende de um enum cujo destino já estava congelado em `core` desde a Story 1.1, mas nunca migrado.
  [`SpecificationRepository.java:14`](../../jpa/src/main/java/br/com/sawcunhaos/foundation/jpa/SpecificationRepository.java#L14)

- Enum movido para `core/enums` sem nenhuma mudança de lógica — só lombok, zero risco.
  [`SpecificationFunction.java:21`](../../core/src/main/java/br/com/sawcunhaos/foundation/core/enums/SpecificationFunction.java#L21)

**As 4 classes do AC (zero mudança de lógica)**

- `BaseEntity` — `@QueryEmbeddable` confirma que `apt-maven-plugin` precisa ser replicado para `QBaseEntity` continuar sendo gerado.
  [`BaseEntity.java:33`](../../jpa/src/main/java/br/com/sawcunhaos/foundation/jpa/entity/BaseEntity.java#L33)

**Fiação do reactor**

- `jpa` entra no reactor logo após `cache`; `audit` ganha dependência nova (soma, não troca — ainda usa `utils` em testes).
  [`pom.xml:110`](../../pom.xml#L110)
  [`audit/pom.xml:114`](../../audit/pom.xml#L114)
