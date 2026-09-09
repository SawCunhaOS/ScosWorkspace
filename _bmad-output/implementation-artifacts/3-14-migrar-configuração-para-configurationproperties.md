---
baseline_commit: e369e8adbec6919939492aeca7a65b69c3c58c28
---

# Story 3.14: Migrar configuração para `@ConfigurationProperties`

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como time consumidor configurando o módulo,
Eu quero propriedades tipadas e centralizadas,
Para não depender de `@Value` solto nem de propriedades mortas.

## Acceptance Criteria

1. **Given** a configuração atual via `@Value` e um `EnvironmentPostProcessor` declarado incorretamente em `AutoConfiguration.imports` (nunca executa), **When** a migração para `@ConfigurationProperties` é concluída, **Then** propriedades mortas são removidas e o `EnvironmentPostProcessor` passa a executar corretamente.

## Tasks / Subtasks

- [x] Task 1: Confirmar o registro incorreto do `EnvironmentPostProcessor` (contexto) (AC: #1)
  - [x] **Confirmado por leitura direta**: `jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` lista `ScosJdempotentRedisEnvironmentPostProcessor` junto com as demais classes `@AutoConfiguration` (`ScosJdempotentRedisProperties`, `ScosJdempotentRedisConfiguration`, `ScosJdempotentConfig`). O contrato `EnvironmentPostProcessor` do Spring Boot é carregado por um SPI **diferente e mais cedo** (executado por `SpringApplication` **antes** do `ApplicationContext` existir) — listar a classe em `AutoConfiguration.imports` só faz o Spring tentar instanciá-la como bean `@Configuration` durante o refresh do contexto, momento em que `postProcessEnvironment()` **nunca é chamado** por esse caminho. O efeito prático: `spring.data.redis.repositories.enabled=false` (a única coisa que este post-processor faz) **nunca é aplicado** hoje. Confirmado empiricamente por um teste que falha contra o registro antigo (ver Task 4).
- [x] Task 2: Registrar o `EnvironmentPostProcessor` no arquivo correto (AC: #1)
  - [x] **Desvio do mecanismo descrito nesta story, verificado empiricamente**: o Dev Notes original descreve `META-INF/spring/org.springframework.boot.env.EnvironmentPostProcessor.imports` como o SPI correto — mas isso não vale para a versão do Spring Boot realmente fixada neste projeto (4.1.x). Decompilando o jar `spring-boot-4.1.1.jar` (`EnvironmentPostProcessorsFactory.fromSpringFactories()` → `SpringFactoriesEnvironmentPostProcessorsFactory` → `SpringFactoriesLoader.forDefaultResourceLocation()`), confirmei que esse caminho lê exclusivamente `META-INF/spring.factories` com a chave `org.springframework.boot.EnvironmentPostProcessor` — não existe suporte a arquivo `.imports` nessa classe. O arquivo `.env.EnvironmentPostProcessor.imports` é um caminho de compatibilidade **separado e deprecated** que não se aplica à interface `org.springframework.boot.EnvironmentPostProcessor` (a que esta classe já implementava). Um teste com essa configuração (`.imports`) falhou (`expected: "false" but was: null`); trocando para `META-INF/spring.factories`, o mesmo teste passou. Criado `jdempotent/src/main/resources/META-INF/spring.factories` com `org.springframework.boot.EnvironmentPostProcessor=...ScosJdempotentRedisEnvironmentPostProcessor`.
  - [x] Removida a linha correspondente de `org.springframework.boot.autoconfigure.AutoConfiguration.imports`.
  - [x] Removida a anotação `@AutoConfiguration` e o `@ConditionalOnProperty` da classe; o check de "enabled" agora é `environment.getProperty("scos.jdempotent.enabled", Boolean.class, true)` direto dentro de `postProcessEnvironment()`, preservando a semântica `matchIfMissing = true` original.
- [x] Task 3: Migrar `@Value` para `@ConfigurationProperties` (AC: #1)
  - [x] `ScosJdempotentRedisProperties.java` convertida para `@ConfigurationProperties(prefix = "scos.jdempotent.cache.redis")`, mantendo `@AutoConfiguration`/`@ConditionalOnProperty`/`@RefreshScope` (não listados como arquivos a alterar nas Project Structure Notes, e removê-los exigiria tocar `ScosJdempotentConfig` para registrar `@EnableConfigurationProperties`, também fora da lista). O campo `enable` (`@Value("${scos.jdempotent.enabled:false}")`) foi removido: sem getter, nunca lido em nenhum lugar (confirmado por busca), e sua property key nunca pertenceu ao namespace `cache.redis` desta classe — mantê-lo teria silenciosamente trocado sua semântica de propriedade (viraria `scos.jdempotent.cache.redis.enable`, nunca configurada por ninguém), exatamente o tipo de propriedade morta que a AC pede para remover. Os demais campos mantêm o mesmo comportamento "sem default" que já tinham sob `@Value`.
  - [x] `ConfigUtility.java` removida inteiramente — busca em todo o repositório (`grep -r "ConfigUtility\|cryptography.algorithm"`) não encontrou nenhuma referência externa à classe ou à property key, então nenhuma nota de CHANGELOG de "referência externa" era necessária (documentada mesmo assim como remoção, ver CHANGELOG).
  - [x] `@RefreshScope` mantido sem alteração em `ScosJdempotentRedisProperties`/`ScosJdempotentConfig`, conforme instruído (não confirmável que nenhum consumidor depende de refresh dinâmico).
- [x] Task 4: Testes (AC: #1)
  - [x] `ScosJdempotentRedisEnvironmentPostProcessorRegistrationTest`: sobe um `SpringApplication` bare (sem `@EnableAutoConfiguration`, sem Redis) e confirma `spring.data.redis.repositories.enabled=false` no `Environment`. Falhou contra o registro antigo (`AutoConfiguration.imports`) e contra a primeira tentativa de correção (`.imports` file), passou após o registro via `META-INF/spring.factories`.
  - [x] `ScosJdempotentRedisPropertiesTest`: 3 testes — binding de valores customizados via `ApplicationContextRunner.withPropertyValues(...)`, default de `persistReqRes` quando ausente, e falha explícita quando `expirationTimeHour` não é configurado.

## Dev Notes

- Esta story tem sobreposição com a Story 3.10 (namespace configurável via propriedade Spring) — coordenar para não duplicar a criação da classe de propriedades. Ver Dev Notes da Story 3.10.
- **Achado adicional, fora do AC literal mas relevante para o dev-agent**: `ScosJdempotentRedisProperties` tem `@Value("${scos.jdempotent.cache.redis.expirationTimeHour}")` **sem valor default** — se a propriedade não for configurada, o binding falha na subida da aplicação (comportamento já "explícito" nesse campo específico, diferente do problema do namespace na Story 3.10, que é silencioso). Ao migrar para `@ConfigurationProperties`, preservar esse comportamento de obrigatoriedade (não introduzir um default silencioso onde hoje não existe).
- **NFR2**: separar em commits distintos — (1) mover o `EnvironmentPostProcessor` para o arquivo SPI correto, (2) migrar `@Value` → `@ConfigurationProperties`, (3) remover `ConfigUtility`/propriedades mortas — são três mudanças de comportamento/mecanismo diferentes, mesmo que relacionadas.

### Project Structure Notes

- Arquivos modificados: `jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`, `ScosJdempotentRedisEnvironmentPostProcessor.java`, `ScosJdempotentRedisProperties.java`.
- Arquivo novo: `jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.env.EnvironmentPostProcessor.imports`.
- Arquivo possivelmente removido: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/config/ConfigUtility.java` (propriedade morta).

### References

- [Source: jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisEnvironmentPostProcessor.java]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisProperties.java]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/config/ConfigUtility.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-314-migrar-configuração-para-configurationproperties]

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- `mvn -pl jdempotent -am test` — 109 testes unitários, 0 falhas (rodada pré-revisão).
- `mvn -pl jdempotent -am verify` — 109 unitários + 16 de integração (Testcontainers Redis/Sentinel),
  0 falhas (rodada pré-revisão).
- **Pós-revisão adversarial (4 patches aplicados, ver Completion Notes)**: `mvn -pl jdempotent -am test`
  — 111 testes unitários (109 + 2 novos), 0 falhas (1 falha intermediária durante o desenvolvimento
  do Patch 3, corrigida — ver Completion Notes). `mvn -pl jdempotent -am verify` — 111 unitários +
  16 de integração, 0 falhas.

### Completion Notes List

- **Desvio importante do mecanismo descrito na story, verificado empiricamente**: o AC/Dev Notes
  descrevem o SPI correto do `EnvironmentPostProcessor` como
  `META-INF/spring/org.springframework.boot.env.EnvironmentPostProcessor.imports` — isso está
  correto para o *conceito* Spring Boot em geral, mas não é o mecanismo realmente usado pela versão
  do Spring Boot fixada neste projeto (4.1.x, via `scos-bom`). Implementei primeiro exatamente como
  descrito na story e escrevi um teste (`ScosJdempotentRedisEnvironmentPostProcessorRegistrationTest`)
  que sobe um `SpringApplication` real para confirmar `spring.data.redis.repositories.enabled=false`
  — esse teste **falhou** (`expected: "false" but was: null`) mesmo com o arquivo `.imports`
  corretamente presente em `target/classes`. Decompilei `spring-boot-4.1.1.jar`
  (`javap` em `EnvironmentPostProcessorsFactory`, `SpringFactoriesEnvironmentPostProcessorsFactory`,
  `SpringFactoriesLoader`) e confirmei: `EnvironmentPostProcessorsFactory.fromSpringFactories()`
  usa `SpringFactoriesLoader.forDefaultResourceLocation()`, que só lê `META-INF/spring.factories`
  — sem nenhum suporte a arquivo `.imports`. A interface `org.springframework.boot.EnvironmentPostProcessor`
  (a que a classe já implementava, sem alteração) é carregada via essa chave em `spring.factories`;
  `org.springframework.boot.env.EnvironmentPostProcessor` (a do Dev Notes) é uma interface
  **separada e deprecated**, carregada por um caminho de compatibilidade diferente. Troquei para
  `META-INF/spring.factories` (chave `org.springframework.boot.EnvironmentPostProcessor`) e o
  mesmo teste passou. Deixei o achado documentado nos comentários do próprio `spring.factories`,
  no Javadoc da classe e do teste, e aqui, para quem revisar não precisar redescobrir isso.
- Campo `enable` removido de `ScosJdempotentRedisProperties` (não estava no AC literal, mas se
  qualifica como propriedade morta pela mesma definição usada para `ConfigUtility.algorithm`: sem
  getter, nunca lido em lugar nenhum do código, confirmado por busca) — ver Task 3 para o racional
  completo (a property key `scos.jdempotent.enabled` nunca pertenceu ao namespace `cache.redis`
  desta classe; manter o campo sob o novo prefixo teria trocado silenciosamente qual property key
  ele lê).
- `ScosJdempotentPropertiesTest`/`ScosJdempotentConfigTest` precisaram de um ajuste: como as duas
  classes de `@ConfigurationProperties` do módulo (`ScosJdempotentProperties` e
  `ScosJdempotentRedisProperties`) compartilham o mesmo `ConfigurationPropertiesBindingPostProcessor`
  no mesmo contexto de teste, `ScosJdempotentRedisProperties.expirationTimeHour` (agora obrigatório)
  passou a ser validado nesses testes também, mesmo eles não sendo sobre essa classe — adicionei
  `scos.jdempotent.cache.redis.expirationTimeHour=1` ao `ApplicationContextRunner` base de ambos
  para não interferir nas asserções sobre namespace que são o assunto real desses testes.
- `ScosJdempotentRedisPropertiesTest` precisou registrar `RefreshAutoConfiguration` explicitamente
  (`AutoConfigurations.of(...)`): `@RefreshScope` gera um proxy CGLIB cujo target só resolve com um
  `Scope` "refresh" registrado no `BeanFactory` — presente de verdade em produção via
  `spring-cloud-starter`, mas ausente por padrão num `ApplicationContextRunner` em branco. Sem isso,
  qualquer teste que chamasse um getter do bean (não só que verificasse sua existência) falhava com
  `IllegalStateException: No Scope registered for scope name 'refresh'` — um bug latente pré-existente
  no padrão de teste `.withBean(ScosJdempotentRedisProperties.class, ...)` já usado por
  `ScosJdempotentPropertiesTest`/`ScosJdempotentConfigTest`, mascarado porque nenhum teste existente
  chamava um getter através do proxy.
- `jdempotent/src/test/resources/application.yml`: removida a linha `spring.data.redis.repositories.enabled: false`
  — era um workaround manual para o mesmo bug que esta story corrige (o post-processor nunca rodava),
  e mascararia a asserção do novo teste de registro (essa property source tem prioridade maior que
  `defaultProperties`, onde o post-processor escreve). `JdempotentTestApplication` já exclui
  `DataRedisRepositoriesAutoConfiguration` diretamente na anotação, então nada nos testes do módulo
  dependia do valor dessa property em si — confirmado rodando `mvn -pl jdempotent -am verify`
  completo (16 testes de integração, 0 falhas) após a remoção.
- Não commitei as mudanças (não solicitado explicitamente) nem separei em commits distintos —
  NFR2 pede 3 commits separados ((1) SPI do EnvironmentPostProcessor, (2) `@Value` →
  `@ConfigurationProperties`, (3) remoção de `ConfigUtility`/propriedades mortas); quem for
  commitar deve seguir essa separação usando o File List abaixo como guia.

- **Revisão adversarial (Blind Hunter / Edge Case Hunter / Verification Gap) — 4 patches
  aplicados**:
  1. **Fail-fast perdido em 4 campos** (`dialTimeoutSecond`, `readTimeoutSecond`,
     `writeTimeoutSecond`, `maxRetryCount`): a primeira versão desta migração só aplicou o padrão
     de duas camadas (`@NotNull` + `@PostConstruct`) a `expirationTimeHour`, deixando os outros 4
     campos silenciosamente `null` quando ausentes — uma regressão real do comportamento que
     existia sob `@Value` sem default, e que contradizia a própria entrada do CHANGELOG. Corrigido
     aplicando `@NotNull` aos 4 campos e generalizando `validateExpirationTimeHour()` para
     `validateRequiredProperties()` (um helper `requireConfigured(Object, String)` evita duplicar
     a mensagem 5 vezes). Novo teste
     `falhaDeFormaExplicitaQuandoDialTimeoutSecondNaoEstaConfigurado`; `assumePersistReqResPadraoQuandoNaoConfigurado`
     também precisou passar a configurar os 4 campos (antes só configurava `expirationTimeHour` e
     por isso não detectava a regressão).
  2. **Guard de "enabled" não equivalente ao `@ConditionalOnProperty` removido**: a primeira versão
     usava `environment.getProperty("scos.jdempotent.enabled", Boolean.class, true)`, que lança
     `ConversionFailedException` (aborta o startup) para um valor não conversível (`"maybe"`) e
     aceita `"yes"/"on"/"1"` como `true` — diferente da semântica `havingValue = "true"` que os
     beans irmãos (`ScosJdempotentRedisProperties`/`ScosJdempotentConfig`) ainda usam, criando um
     cenário de "módulo meio habilitado". Trocado para comparação de string:
     `"true".equalsIgnoreCase(environment.getProperty("scos.jdempotent.enabled", "true"))`.
  3. **Caminho desabilitado sem cobertura**: nenhum teste confirmava o que o post-processor faz
     com `spring.data.redis.repositories.enabled` quando `scos.jdempotent.enabled=false` — o
     opt-out documentado no próprio CHANGELOG. Novo teste
     `naoForcaSpringDataRedisRepositoriesEnabledQuandoScosJdempotentEstaDesabilitado`. **Achado
     durante a escrita do teste**: a primeira tentativa usou
     `SpringApplicationBuilder.properties("scos.jdempotent.enabled=false")`, que define
     propriedades de **baixa** precedência (`defaultProperties`) — o `application.yml` de teste do
     módulo (`scos.jdempotent.enabled: true`, carregado normalmente do classpath) sobrescrevia
     esse valor, e o teste falhou (`expected: null but was: "false"`) porque o post-processor via
     `"true"` de qualquer forma. Corrigido passando a propriedade como argumento de linha de
     comando (`.run("--scos.jdempotent.enabled=false")`), que tem precedência mais alta que
     arquivos de configuração.
  4. **CHANGELOG**: a remoção de `ConfigUtility` (classe pública) e do campo `enable` de
     `ScosJdempotentRedisProperties` estava fora da seção **BREAKING**, e o texto afirmava que
     `enable` "não tinha getter" — falso, `@Data` do Lombok gera `isEnable()`/`setEnable(boolean)`
     públicos automaticamente. Movidas as duas menções para **BREAKING** num bullet próprio
     ("Public surface removed"), com o texto corrigido para dizer que a busca no repositório não
     encontrou nenhum consumidor desses acessores gerados (não que eles não existiam).
  - Reverificado após os 4 patches: `mvn -pl jdempotent -am verify` — 111 testes unitários + 16 de
    integração, 0 falhas.

### File List

- `jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` (modificado — removida a linha do `EnvironmentPostProcessor`)
- `jdempotent/src/main/resources/META-INF/spring.factories` (novo — registro correto do `EnvironmentPostProcessor`)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisEnvironmentPostProcessor.java` (modificado)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisProperties.java` (modificado)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/config/ConfigUtility.java` (removido)
- `jdempotent/src/test/resources/application.yml` (modificado — removido workaround manual)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisEnvironmentPostProcessorRegistrationTest.java` (novo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisPropertiesTest.java` (novo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentPropertiesTest.java` (modificado — property adicional no runner)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfigTest.java` (modificado — property adicional no runner)
- `CHANGELOG.md` (modificado)

## Suggested Review Order

**Registro do `EnvironmentPostProcessor` (causa raiz do bug)**

- Explica por que o SPI antigo nunca chamava `postProcessEnvironment` neste Spring Boot
  [`ScosJdempotentRedisEnvironmentPostProcessor.java:27`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisEnvironmentPostProcessor.java#L27)

- Guard de "enabled" trocado para string (patch pós-revisão): evita `ConversionFailedException` e split-brain com `@ConditionalOnProperty`
  [`ScosJdempotentRedisEnvironmentPostProcessor.java:66`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisEnvironmentPostProcessor.java#L66)

- Registro correto via SPI clássico (`spring.factories`), não via `.imports` (confirmado por decompilação)
  [`spring.factories:12`](../../jdempotent/src/main/resources/META-INF/spring.factories#L12)

- Remove a classe do SPI errado, onde nunca era efetivamente executada
  [`AutoConfiguration.imports:1`](../../jdempotent/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports#L1)

- Prova empírica: falha contra o registro antigo, passa após a correção
  [`ScosJdempotentRedisEnvironmentPostProcessorRegistrationTest.java:48`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisEnvironmentPostProcessorRegistrationTest.java#L48)

- Cobre o opt-out `scos.jdempotent.enabled=false` (patch pós-revisão; achado sem teste antes)
  [`ScosJdempotentRedisEnvironmentPostProcessorRegistrationTest.java:70`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisEnvironmentPostProcessorRegistrationTest.java#L70)

**Migração `@Value` → `@ConfigurationProperties` com fail-fast**

- Binding tipado e centralizado sob um único prefixo, substituindo seis `@Value` soltos
  [`ScosJdempotentRedisProperties.java:54`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisProperties.java#L54)

- Fail-fast estendido aos 5 campos obrigatórios (patch pós-revisão corrigiu regressão nos outros 4)
  [`ScosJdempotentRedisProperties.java:83`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisProperties.java#L83)

- Helper evita duplicar a mensagem de erro 5 vezes
  [`ScosJdempotentRedisProperties.java:91`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisProperties.java#L91)

- Binding de valores customizados via `ApplicationContextRunner`
  [`ScosJdempotentRedisPropertiesTest.java:49`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisPropertiesTest.java#L49)

- Confirma que os 5 campos obrigatórios falham explicitamente quando ausentes
  [`ScosJdempotentRedisPropertiesTest.java:85`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentRedisPropertiesTest.java#L85)

**Remoção de propriedades mortas**

- `ConfigUtility` (classe inteira) e o campo `enable` movidos para **BREAKING**: eliminam superfície pública sem consumidor confirmado no repositório
  [`CHANGELOG.md:145`](../../CHANGELOG.md#L145)

**Periféricos**

- Remove workaround manual que mascararia o novo teste de registro
  [`application.yml:20`](../../jdempotent/src/test/resources/application.yml#L20)
