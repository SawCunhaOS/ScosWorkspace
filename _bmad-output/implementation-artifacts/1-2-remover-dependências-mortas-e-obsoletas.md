---
baseline_commit: 9c022adf4766e410c4943aada62b3d92d5d73cb3
---

# Story 1.2: Remover dependências mortas e obsoletas

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero remover bibliotecas sem uso real e substituir as com uso mínimo,
Para reduzir a superfície de dependências transitivas antes de mover qualquer classe.

## Acceptance Criteria

1. **Given** o POM atual do `utils`, **When** o build é executado após a limpeza, **Then** `bouncycastle`, `snakeyaml` e `mapstruct` não aparecem mais como dependências.
2. **And** `guava` foi substituído por `commons-lang3` no único ponto de uso.
3. **And** a avaliação de substituição de `commons-io` por `java.nio` e da necessidade de `spring-cloud-starter` está documentada com a decisão tomada.

## Tasks / Subtasks

- [x] Task 1: Remover as 3 dependências com zero uso real (AC: #1)
  - [x] Remover `<dependency>org.bouncycastle:bcprov-jdk18on</dependency>` de `utils/pom.xml` (linhas 162-165) — 0 classes usam
  - [x] Remover `<dependency>org.yaml:snakeyaml</dependency>` (linhas 158-161) — 0 classes usam
  - [x] Remover `<dependency>org.mapstruct:mapstruct</dependency>` (linhas 142-145) — 0 classes usam
  - [x] Um commit por dependência removida, cada um com build verde (NFR2) — não agrupar as 3 num único commit — sequência e verificação feitas (ver Debug Log); commits em si ficam para o usuário aplicar, conforme o padrão já usado na Story 1.1
- [x] Task 2: Substituir guava por commons-lang3 (AC: #2)
  - [x] Localizar o único ponto de uso: `utils/src/main/java/.../enums/StringTransformRule.java`
  - [x] Substituir a chamada Guava pelo equivalente em `org.apache.commons.lang3` já presente no POM (já é dependência declarada — não é lib nova) ou por código próprio de uma linha, o que for mais curto
  - [x] Remover `<dependency>com.google.guava:guava</dependency>` (linhas 154-157) após confirmar zero uso restante
- [x] Task 3: Avaliar e documentar `commons-io` e `spring-cloud-starter` (AC: #3)
  - [x] Grep pelo único ponto de uso de `commons-io` no módulo; avaliar se `java.nio.file.Files`/`java.nio.file.Path` cobre o caso com uma troca de 1 linha; se cobrir, trocar e remover a dependência; se não, documentar por que não
  - [x] Grep pelos 3 pontos de uso de `spring-cloud-starter`; confirmar se são reais (import ativo) ou herdados sem uso; documentar a decisão (manter ou remover) com a justificativa
  - [x] Registrar as duas decisões (mesmo que a decisão seja "manter") em `utils/README.md` ou nas Completion Notes desta story — o AC exige documentação da avaliação, não necessariamente a remoção

## Dev Notes

- Tabela de diagnóstico já levantada no plano de origem (fonte primária, não re-investigar do zero): `bcprov-jdk18on` → 0 usos → remover; `snakeyaml` → 0 → remover; `mapstruct` → 0 → remover; `guava` → 1 uso (`StringTransformRule`) → substituir; `commons-io` → 1 uso → avaliar `java.nio`; `spring-cloud-starter` → 3 usos → verificar necessidade real.
- `commons-lang3` **já é dependência declarada** em `utils/pom.xml` (linha 176) — não adicionar dependência nova, só usar o que já existe.
- **Fora de escopo desta story**: `gson` (Story 1.3), `jackson-dataformat-smile` (vai para `cache` na Story 1.10, não é dependência morta).
- **NFR2** (build verde a cada commit) é o requisito de processo mais importante aqui: a Fase 1 do plano de origem prescreve "um commit por dependência removida, cada um verde" — não faça squash das remoções num commit único.
- Esta é a Fase 1 ("Limpeza") do plano de origem — roda **antes** da extração de qualquer módulo novo, para não carregar peso morto para eles.
- Rodar `mvn dependency:analyze` no módulo `utils` antes de remover, para confirmar que as libs realmente não aparecem no bytecode compilado (não só ausência de `import` textual).

### Project Structure Notes

- Único arquivo tocado: `utils/pom.xml` (remoção de `<dependency>`) e `utils/src/main/java/br/com/sawcunhaos/foundation/utils/enums/StringTransformRule.java` (troca de chamada Guava).
- Nenhum módulo novo é criado nesta story.

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#6-limpeza-prévia]
- [Source: etc/doc/plano/plano-decomposicao-utils.md#fase-1--limpeza-1-dia]
- [Source: utils/pom.xml#L142-L177]
- [Source: _bmad-output/planning-artifacts/epics.md#story-12-remover-dependências-mortas-e-obsoletas]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- Linha de base (`HEAD` = `9c022adf...`, sem alterações) já falhava `mvn -pl utils -am clean install` — não por erro de compilação, mas pela regra `RequireUpperBoundDeps` do `maven-enforcer-plugin`. Rodar com `-Denforcer.skip=true` (só diagnóstico) confirmou que compilação/testes passam limpos; o problema era isolado ao enforcer.
- Duas causas distintas identificadas por bisseção manual (removendo `guava` temporariamente, revertendo em seguida):
  1. `com.google.guava:guava:33.7.1-jre` declara `org.jspecify:jspecify:1.0.1` e `com.google.errorprone:error_prone_annotations:2.50.0`, conflitando com o que `gson`/`spring-framework-bom` gerenciam (`1.0.0` / `2.48.0`). **Resolvido pela própria Task 2** (remoção do `guava`).
  2. `io.github.openfeign.querydsl:querydsl-jpa` (via `querydsl-core`) pede `reactor-core:3.8.6`, enquanto `spring-boot-starter-data-redis` (via `lettuce-core`) pede `reactor-core:3.6.6`; o BOM gerenciava `3.8.5`, abaixo dos dois. **Sem relação com nenhuma dependência desta story** — pré-existente, causado por `querydsl-jpa` vs `spring-boot-starter-data-redis`.
- Decisão tomada com o usuário (pergunta explícita, resposta: "investigar e propor correção agora"): fixar `reactor-core` em `3.8.6` (a mais alta das duas versões conflitantes) via override em `dependencyManagement` do `pom.xml` raiz. Validado isoladamente (pin sozinho ainda falha por causa do guava; guava removido sozinho ainda falha por causa do reactor-core; os dois juntos ficam verdes) antes de aplicar em definitivo.
- `mvn -pl utils -am clean test-compile` verificado verde após cada remoção individual (guava+pin, bouncycastle, snakeyaml, mapstruct, commons-io) e `mvn clean install -DskipTests` verde para o reactor inteiro ao final.
- **Achado à parte, corrigido a pedido do usuário:** `mvn test` reportava `Tests run: 0` em todos os módulos, inclusive `privacy` (não tocado pelo resto desta story). Causa raiz: nem este repositório nem o `scos-bom` fixam versão do `maven-surefire-plugin`; sem isso, o Maven usa o binding implícito embutido no próprio `maven-core` (`META-INF/plexus/default-bindings.xml`), que pina `maven-surefire-plugin:2.17` — anterior ao suporte a JUnit 5 (adicionado no surefire 2.22), então nenhum teste (novo ou existente) era descoberto, e o build reportava sucesso mesmo assim. Corrigido fixando `maven-surefire-plugin:3.5.4` em `<pluginManagement>` no `pom.xml` raiz (propaga por herança aos 5 módulos, nenhum precisou de mudança própria). Após o fix: `utils` = 211 testes (incluindo os 5 do `StringTransformRuleTest`, antes invisíveis), `privacy` = 42 testes, todos verdes.

### Completion Notes List

- Removidas `bouncycastle` (`bcprov-jdk18on`), `snakeyaml` e `mapstruct` de `utils/pom.xml` — confirmado via `grep` que nenhuma classe do módulo as importa (0 usos).
- `guava` removido; único ponto de uso (`StringTransformRule.CAMEL_CASE`) trocado para `org.apache.commons.lang3.StringUtils.uncapitalize(value.toLowerCase())`. Comportamento preservado byte a byte: a chamada original (`CaseFormat.UPPER_CAMEL.to(CaseFormat.LOWER_CAMEL, value.toLowerCase())`) já era, para qualquer entrada, equivalente a "primeira letra em minúsculo" sobre uma string já totalmente minúscula — ou seja, um no-op sobre `value.toLowerCase()`. `uncapitalize` reproduz exatamente esse no-op. **Observação fora de escopo:** o efeito prático de `CAMEL_CASE.apply(...)` hoje é idêntico a `LOWER_CASE.apply(...)`; se isso é intencional ou um bug de lógica pré-existente não foi investigado — não é uma dependência morta, é comportamento de negócio, e mexer nisso está fora do que esta story pede (ver NFR4-equivalente de escopo do épico).
- `commons-io` removido; único uso (`IOUtils.copy(InputStream, OutputStream)` em `MultiReadHttpServletRequest`) trocado por `InputStream#transferTo` (stdlib desde Java 9, cobre o caso de stream-to-stream; `java.nio.file.Files` não se aplica por não ser uma operação de arquivo).
- `spring-cloud-starter` **mantido** — uso real e ativo de `@RefreshScope` (`org.springframework.cloud.context.config.annotation.RefreshScope`) em `ScosCacheProperties`, `ScosCacheModel` e `ScosFilterProperties`; não é dependência herdada sem uso.
- **Fix adicional, fora do escopo literal das ACs mas necessário para a NFR2 ("build verde a cada commit"):** pin de `io.projectreactor:reactor-core` em `3.8.6` no `dependencyManagement` do `pom.xml` raiz, para resolver um conflito de `RequireUpperBoundDeps` pré-existente e independente das dependências desta story (`querydsl-jpa` vs `spring-boot-starter-data-redis`). Sem esse pin, nenhum commit desta story (nem mesmo a remoção isolada de `bouncycastle`) teria build verde, porque o enforcer já falhava no `HEAD` antes de qualquer mudança. Confirmado com o usuário antes de aplicar.
- Teste novo `StringTransformRuleTest` cobre as 4 regras de `StringTransformRule`; roda e passa (5/5) após o fix do surefire.
- **Fix adicional #2, a pedido explícito do usuário:** `maven-surefire-plugin` fixado em `3.5.4` via `<pluginManagement>` no `pom.xml` raiz — corrige o binding implícito `2.17` (pré-JUnit5) que fazia `mvn test` reportar sucesso sem rodar nenhum teste em nenhum dos 5 módulos. Ver Debug Log para a causa raiz.
- Build completo do reactor com testes (`mvn clean install`) executado ao final: `privacy` 42/42, `utils` 211/211, `exception` 10/10, `audit` 49/49 — todos verdes. `jdempotent` teve 3 erros, mas são falhas de infraestrutura Docker/Testcontainers (`port is already allocated` na 6379, `Container startup failed for image alpine/socat`) no ambiente local, não relacionadas a nenhuma mudança desta story — módulo não tocado. Não investiguei/corrigi (fora de escopo; provável conflito de porta com container remanescente de execução anterior).
- **Não commitei nada** (só `git commit` quando pedido explicitamente, conforme instrução do projeto) — as mudanças estão na working tree, prontas para os commits granulares que a NFR2 descreve (sugestão de sequência nas Debug Log References).
- **Revisão retroativa (fechamento do Épico 1, 2026-08-23)**: esta story nunca tinha passado pela etapa de revisão adversarial do workflow. Rodada agora. Achado do Blind Hunter: a Task 1 pedia "um commit por dependência removida", e quando o commit desta story acabou sendo feito (fora desta sessão, ver `git log` — commit único `3b440bb feat: Implementacao Story 1.2`), não seguiu a sequência granular sugerida acima nas Debug Log References — tudo foi para um commit só. Isso já estava disclosed no próprio texto desta nota ("prontas para os commits granulares... quando pedido"), não é uma omissão nova; registrado aqui só para deixar explícito que o checkbox `[x]` da Task 1 se refere à remoção técnica das dependências (feita e verificada), não à granularidade de commit pedida pela NFR2 (não seguida). Não corrigido — reescrever o histórico do git de um commit já mesclado é uma operação destrutiva fora do escopo de decidir sozinho nesta revisão.

### File List

- `pom.xml` (raiz) — pin de `reactor-core:3.8.6` em `dependencyManagement`; pin de `maven-surefire-plugin:3.5.4` em `pluginManagement` (corrige JUnit 5 não sendo descoberto em nenhum dos 5 módulos)
- `utils/pom.xml` — remoção de `bcprov-jdk18on`, `snakeyaml`, `mapstruct`, `guava`, `commons-io`
- `utils/src/main/java/br/com/sawcunhaos/foundation/utils/enums/StringTransformRule.java` — troca de `guava` por `commons-lang3`
- `utils/src/main/java/br/com/sawcunhaos/foundation/utils/configuration/rest/filter/MultiReadHttpServletRequest.java` — troca de `commons-io` por `InputStream#transferTo`
- `utils/src/test/java/br/com/sawcunhaos/foundation/utils/enums/StringTransformRuleTest.java` (novo)

## Suggested Review Order

**Os dois fixes fora do escopo literal, necessários para build verde**

- Pin de `reactor-core:3.8.6` (compatibilidade reativa com Lettuce nunca exercitada especificamente — ver `deferred-work.md`).
  [`pom.xml`](../../pom.xml)
- Pin de `maven-surefire-plugin:3.5.4` (achado crítico: 0 testes descobertos em todo o reactor antes deste fix).
  [`pom.xml`](../../pom.xml)

**A troca de dependência com comportamento pré-existente preservado (incluindo um bug conhecido)**

- `StringTransformRule.CAMEL_CASE` — `uncapitalize` reproduz um no-op pré-existente do Guava, não corrigido (fora de escopo).
  [`StringTransformRuleTest.java`](../../utils/src/test/java/br/com/sawcunhaos/foundation/utils/enums/StringTransformRuleTest.java)
