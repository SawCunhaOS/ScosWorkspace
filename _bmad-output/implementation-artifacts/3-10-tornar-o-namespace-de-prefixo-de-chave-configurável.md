---
baseline_commit: d03c9cdea672a47fd96da7c8eb835b5fe74660b1
---

# Story 3.10: Tornar o namespace de prefixo de chave configurável

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como time consumidor compartilhando a mesma instância de Redis entre aplicações,
Eu quero configurar o namespace via propriedade Spring,
Para não colidir chaves entre aplicações diferentes.

## Acceptance Criteria

1. **Given** a leitura atual via `System.getenv(APP_NAME)` (silenciosamente vazia quando ausente), **When** o namespace passa a ser obrigatório e configurável via propriedade Spring, **Then** a aplicação falha de forma explícita (não silenciosa) se o namespace não for configurado.

## Tasks / Subtasks

- [x] Task 1: Confirmar o comportamento atual (contexto) (AC: #1)
  - [x] **Confirmado por leitura direta**: `DefaultKeyGenerator` (linha 33) — `appName = System.getenv(EnvironmentVariableUtils.APP_NAME)`, onde `APP_NAME = "APP_NAME"` (`EnvironmentVariableUtils.java`). Se a variável de ambiente `APP_NAME` não estiver definida, `appName` fica `null`, e `generateIdempotentKey()` (linha 50) faz `if (!StringUtils.isBlank(appName)) { builder.append(appName)... }` — ou seja, **silenciosamente pula o prefixo** sem erro nem aviso. Duas aplicações diferentes rodando sem `APP_NAME` configurado, contra o mesmo Redis, podem colidir chaves de idempotência sem nenhum sinal de que isso está acontecendo
- [x] Task 2: Introduzir a propriedade Spring obrigatória (AC: #1)
  - [x] Adicionada `ScosJdempotentProperties` (`@ConfigurationProperties(prefix = "scos.jdempotent")`), classe isolada — Story 3.14 (`ready-for-dev`, não implementada ainda) absorverá/reorganizará depois; ver Completion Notes.
  - [x] `@NotBlank` + `@Validated` no campo `namespace`: contexto Spring falha na inicialização (`BindValidationException` embrulhada em `ConfigurationPropertiesBindException`/`UnsatisfiedDependencyException`) se a propriedade não estiver configurada — mensagem clara citando `scos.jdempotent.namespace`.
- [x] Task 3: Substituir o uso de `System.getenv(APP_NAME)` (AC: #1)
  - [x] `DefaultKeyGenerator` não lê mais `System.getenv`; novo construtor `DefaultKeyGenerator(String namespace)` recebe o namespace já resolvido. `ScosJdempotentConfig` (agora com `@EnableConfigurationProperties(ScosJdempotentProperties.class)`) injeta `ScosJdempotentProperties` e constrói o `DefaultKeyGenerator` com `jdempotentProperties.getNamespace()` para os dois beans `IdempotentAspect`. `EnvironmentVariableUtils`/`APP_NAME` removidos (não tinham mais nenhum uso).
- [x] Task 4: Testes (AC: #1)
  - [x] `ScosJdempotentPropertiesTest.falhaDeFormaExplicitaQuandoNamespaceNaoEstaConfigurado`: contexto Spring sem a propriedade → `hasFailed()` + stacktrace citando `scos.jdempotent.namespace` e `NotBlank`.
  - [x] `ScosJdempotentPropertiesTest.aplicaOPrefixoDeNamespaceConfiguradoNaChaveGerada`: contexto Spring com a propriedade configurada → `ScosJdempotentProperties` resolve o valor, e a chave gerada por `DefaultKeyGenerator` com esse valor começa com `"<namespace>-listener-"`.

## Dev Notes

- Esta story tem sobreposição direta com a Story 3.14 (migração `@Value` → `@ConfigurationProperties`) — decidir na implementação se o namespace entra como parte da mesma classe de propriedades criada pela 3.14 ou como uma propriedade isolada introduzida aqui. Documentar a decisão nas Completion Notes para não duplicar trabalho entre as duas stories.
- **Mudança de comportamento visível ao consumidor**: hoje uma aplicação sem `APP_NAME` sobe normalmente (com risco silencioso de colisão); depois desta story, a mesma aplicação **não sobe** sem a propriedade configurada. Isto é uma mudança de comportamento breaking, intencional e exigida pelo AC — documentar no CHANGELOG do módulo como mudança que requer ação do consumidor antes de atualizar a versão.
- Não implementar fallback automático para `System.getenv(APP_NAME)` como forma de manter compatibilidade — o AC pede explicitamente que a ausência de configuração **falhe**, não que degrade silenciosamente para o comportamento antigo.
- Escopo de verificação: não é necessário rodar os testes do módulo `audit` para esta story — rodar apenas os testes relevantes ao módulo `jdempotent`.

### Project Structure Notes

- Arquivo modificado: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGenerator.java`.
- Arquivo novo ou modificado: classe de propriedades Spring (local final depende da coordenação com a Story 3.14).
- **Decisão de implementação (coordenação com a Story 3.14)**: a Story 3.14 ainda estava
  `ready-for-dev` (não implementada) no momento desta story. Conforme a Dev Note acima, o namespace
  entrou como uma classe de propriedades **isolada**, `ScosJdempotentProperties`
  (`jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentProperties.java`,
  prefix `scos.jdempotent`, campo único `namespace` com `@NotBlank` + `@Validated`), em vez de
  entrar na classe geral que a 3.14 criará. Quando a 3.14 for implementada, ela pode absorver este
  campo na classe de propriedades geral do módulo (ou manter esta classe separada) — decisão dela,
  não desta story.

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGenerator.java#L28-L34]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/constant/EnvironmentVariableUtils.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-310-tornar-o-namespace-de-prefixo-de-chave-configurável]

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- `mvn -pl jdempotent test` — 76 testes unitários, 0 falhas (rodada inicial).
- `mvn -pl jdempotent verify` — 76 unitários + 16 de integração (Testcontainers/Sentinel), 0 falhas
  (rodada inicial). Não rodados os testes do módulo `audit` (fora de escopo desta story, conforme
  Dev Notes).
- **Rodada pós-revisão adversarial** (patches #1-#4 abaixo aplicados): `mvn -pl jdempotent test` —
  77 testes unitários (76 + 1 novo), 0 falhas. `mvn -pl jdempotent verify` — 77 unitários + 16 de
  integração, 0 falhas. Módulo `audit` novamente não rodado (fora de escopo).

### Completion Notes List

- **Revisão adversarial (blind-hunter / edge-case-hunter / verification-gap) — patches aplicados**:
  1. `ScosJdempotentProperties` ganhou um `@PostConstruct` (`validateNamespace()`) que lança
     `IllegalStateException` se `namespace` estiver em branco, independente de haver um provider
     JSR-380 no classpath do consumidor — o `@NotBlank`/`@Validated` existente (que depende de
     `hibernate-validator`, só em `test` scope neste módulo) foi mantido como camada adicional, não
     substituído; a falha explícita da AC #1 agora é incondicional.
  2. Novo teste `ScosJdempotentPropertiesTest.aplicaOPrefixoDeNamespaceNoBeanComErrorConditionalCallback`
     cobre especificamente o bean `getIdempotentAspectOnErrorConditionalCallback` (registra um
     `ErrorConditionalCallback` mock, extrai o `keyGenerator` privado do `IdempotentAspect` via
     `ReflectionTestUtils` e confirma o prefixo do namespace na chave gerada) — antes, uma regressão
     nesse bean específico não seria detectada por nenhum teste.
  3. `ScosJdempotentConfig` ganhou um método privado `keyGenerator()` para eliminar a duplicação de
     `new DefaultKeyGenerator(jdempotentProperties.getNamespace())` nos dois métodos `@Bean`.
  4. `CHANGELOG.md`: bullet "Added" e seção "BREAKING" consolidados (o "Added" agora só aponta o
     mecanismo e remete à seção BREAKING para a narrativa de comportamento); a seção BREAKING agora
     deixa explícito que a falha de inicialização é do caminho de autoconfiguração Spring
     (`ScosJdempotentConfig`) — construtores públicos de `IdempotentAspect`/`DefaultKeyGenerator`
     usados fora dessa autoconfiguração continuam funcionando sem namespace, comportamento
     inalterado e fora do escopo desta story.

- Namespace introduzido como classe de propriedades **isolada** (`ScosJdempotentProperties`), não
  absorvida pela Story 3.14 (ainda `ready-for-dev`, não implementada) — ver Project Structure Notes
  para o racional completo.
- `DefaultKeyGenerator` manteve seu construtor sem argumentos (agora sem ler `System.getenv`; passa
  a não aplicar nenhum prefixo) para não quebrar `IdempotentAspect`'s construtores públicos
  existentes (`new DefaultKeyGenerator()` interno) nem os contextos de teste que registram
  `DefaultKeyGenerator.class` diretamente — `IdempotentAspect` não está listado como arquivo
  modificado nas Project Structure Notes, e alterar sua API pública estaria fora do escopo desta
  story. O caminho de autoconfiguração Spring (`ScosJdempotentConfig`), que é onde a AC se aplica,
  passa a usar exclusivamente o novo construtor `DefaultKeyGenerator(String namespace)` com o valor
  resolvido de `ScosJdempotentProperties`.
- `EnvironmentVariableUtils` (e sua constante `APP_NAME`) removida — ficou sem nenhum uso após a
  mudança; confirmado via busca em todo o repositório antes de remover.
- Efeito colateral necessário para manter o `mvn verify` verde: `jdempotent/src/test/resources/application.yml`
  ganhou `scos.jdempotent.namespace: jdempotent-it` (os testes `@SpringBootTest` do módulo sobem via
  esse arquivo e passam a exigir a propriedade); o hash de chave hardcoded em
  `PrimeNumbersJdempotentEnableITTest` (`KEY_DEFAULT_PRIME_NUMBER`) ganhou o prefixo
  `"jdempotent-it-"` correspondente (o sufixo SHA-256 não muda — o namespace só afeta o prefixo).
- Mudança documentada como **BREAKING** no `CHANGELOG.md` (seção `scos-foundation-jdempotent`).
- Risco/pendência: a Story 3.14, quando implementada, deve decidir se absorve
  `ScosJdempotentProperties` na classe de propriedades geral do módulo — não é uma ação desta
  story, mas fica registrado aqui para quem pegar a 3.14 depois.

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGenerator.java` (modificado)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/constant/EnvironmentVariableUtils.java` (removido)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentProperties.java` (novo)
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfig.java` (modificado)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfigTest.java` (modificado)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentPropertiesTest.java` (novo)
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/test/PrimeNumbersJdempotentEnableITTest.java` (modificado)
- `jdempotent/src/test/resources/application.yml` (modificado)
- `CHANGELOG.md` (modificado)

## Suggested Review Order

**Propriedade obrigatória e falha explícita**

- Ponto de entrada: nova classe de propriedades, com validação em duas camadas (`@NotBlank` opcional + `@PostConstruct` incondicional).
  [`ScosJdempotentProperties.java:41`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentProperties.java#L41)

- Checagem incondicional adicionada após a revisão: garante falha mesmo sem validador Bean Validation no classpath do consumidor.
  [`ScosJdempotentProperties.java:50`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentProperties.java#L50)

**Geração de chave com namespace resolvido**

- `DefaultKeyGenerator` para de ler `System.getenv` e passa a receber o namespace já resolvido; construtor sem argumentos preservado sem prefixo, para não quebrar callers programáticos.
  [`DefaultKeyGenerator.java:39`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/DefaultKeyGenerator.java#L39)

**Fiação Spring**

- `ScosJdempotentConfig` injeta `ScosJdempotentProperties` e concentra a construção do `DefaultKeyGenerator` num único método privado, usado pelos dois beans `IdempotentAspect`.
  [`ScosJdempotentConfig.java:61`](../../jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfig.java#L61)

**Testes**

- Cobre o cenário de falha explícita (sem propriedade) e o de prefixo correto (com propriedade), incluindo o bean `ErrorConditionalCallback` adicionado na revisão.
  [`ScosJdempotentPropertiesTest.java`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentPropertiesTest.java)

- Hash de chave hardcoded do teste de integração ajustado para o novo prefixo de namespace.
  [`PrimeNumbersJdempotentEnableITTest.java:100`](../../jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/redis/test/PrimeNumbersJdempotentEnableITTest.java#L100)

**Peripherals**

- Propriedade obrigatória adicionada ao `application.yml` de teste do módulo.
  [`application.yml:24`](../../jdempotent/src/test/resources/application.yml#L24)

- Documentação da mudança breaking e do mecanismo de segurança incondicional.
  [`CHANGELOG.md`](../../CHANGELOG.md)
