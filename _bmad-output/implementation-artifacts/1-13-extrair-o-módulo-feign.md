# Story 1.13: Extrair o módulo `feign`

Status: done

<!-- baseline_commit: 5b76698950a9a67dcf46f723e70fe999c1b4adf3 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como time consumidor que integra via Feign,
Eu quero um módulo `feign` dedicado,
Para não herdar essa dependência ao usar só `web` ou `core`.

## Acceptance Criteria

1. **Given** `JacksonEncoderCustom`, `JacksonDecoderCustom` do inventário, **When** o módulo `feign` é extraído dependendo apenas de `core`, **Then** `feign` compila isoladamente e os testes migrados permanecem verdes.
2. **And** a extração ocorre em 2 commits separados.

## Tasks / Subtasks

- [x] Task 1: Commit 1 — mover as 2 classes (AC: #1)
  - [x] Criar módulo Maven `scos-foundation-feign`, pacote raiz `br.com.sawcunhaos.foundation.feign`, dependendo só de `core` (Story 1.7) + `io.github.openfeign:feign-core` (+ `tools.jackson.core:jackson-databind`, dependência descoberta — ver Debug Log)
  - [x] Mover: `utils/src/main/java/.../configuration/feign/JacksonEncoderCustom.java`, `JacksonDecoderCustom.java`
  - [x] Mover testes correspondentes, se existentes — **nenhum existia**: busca no repo inteiro antes da migração não encontrou teste próprio para nenhuma das 2 classes
  - [x] Commit isolado: só mover/renomear pacote
- [x] Task 2: Commit 2 — ajustar o que precisar (AC: #2)
  - [x] Aplicar separadamente qualquer ajuste de comportamento necessário; documentar se não houver nenhum — **nenhum ajuste de comportamento no código movido**; o único ajuste é limpeza de dependências órfãs em `utils/pom.xml` (`feign-core`, `tools.jackson.core:jackson-databind`)

## Dev Notes

- Depende só da Story 1.7 (`core`) — módulo mais simples entre os folhas, 2 classes.
- **Decisão D3 do plano de origem já resolvida pelo AC**: módulo `feign` próprio, não dependência `optional` dentro de `web` com `@ConditionalOnClass` — "não vale um artefato para dois encoders" foi a inclinação do plano, mas o AC desta story (e a arquitetura, que lista `feign` como módulo folha independente dependendo só de `core`) fixa a opção do módulo dedicado como decisão final.
- Independente da ordem de `web` (Story 1.12) — pode rodar em paralelo ou antes/depois, já que não depende de `web` nem `cache`.

### Project Structure Notes

- Módulo Maven novo: `feign/` — depende só de `core`, `feign-core` e `tools.jackson.core:jackson-databind` (ver Debug Log).
- `utils/` perde `JacksonEncoderCustom.java`, `JacksonDecoderCustom.java` e, no ajuste, as dependências `feign-core`/`jackson-databind`, órfãs após a extração. `utils` fica com só 2 classes (`ValueType`, `LocaleService`, ambas já com destino `core` congelado desde a Story 1.1, nunca migradas) e zero testes.
- `pom.xml` raiz ganha `<module>feign</module>` (após `web`, já que é independente da sequência da Fase 4) + `dependencyManagement` para `scos-foundation-feign`.

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#scos-foundation-feign]
- [Source: etc/doc/plano/plano-decomposicao-utils.md#7-decisões-que-preciso-que-você-tome] (Decisão D3)
- [Source: _bmad-output/planning-artifacts/epics.md#story-113-extrair-o-módulo-feign]
- [Source: _bmad-output/implementation-artifacts/inventario-classe-modulo.md#L92-L93] (pacote flat `br.com.sawcunhaos.foundation.feign`)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- **Nota de processo**: implementação feita diretamente pela sessão principal, sem subagente (mesmo modo usado desde a Story 1.11, após o subagente original ter falhado por limite de sessão da conta).
- **Dependência `tools.jackson.core:jackson-databind` não listada no Dev Notes**: `JacksonEncoderCustom`/`JacksonDecoderCustom` usam `tools.jackson.databind.ObjectMapper`/`JavaType` e `tools.jackson.core.JacksonException` diretamente — não vêm transitivamente de `feign-core` nem de `scos-foundation-core`. Mesma categoria de "dependência descoberta" documentada em toda story de extração anterior.
- **Story mais simples do épico**: zero desvio de pacote (inventário confirma `br.com.sawcunhaos.foundation.feign`, flat, batendo com o texto da própria story), zero teste migrado (nenhum existia), zero consumidor externo dentro do repo (confirmado por `grep` — nem código, nem referência em string YAML/properties), zero ajuste de comportamento.
- **Verificação**: `mvn -o -pl feign -am compile` → verde. `mvn -o compile` (reactor inteiro) → verde. `mvn -o test-compile` (reactor inteiro, todos os módulos incl. `audit`/`jdempotent`) → verde — checagem extra deliberada após a regressão de test-discovery pega na Story 1.12 (`exception`), para garantir que a limpeza de `utils/pom.xml` não quebrou nenhum consumidor silencioso desta vez. `mvn -o test -pl '!jdempotent,!audit' -am` → verde. `mvn -o -pl audit -am test` → `BUILD SUCCESS` (54/54, ~5min).

### Completion Notes List

- AC #1: `scos-foundation-feign` criado, depende de `core` + `feign-core` (+ `jackson-databind`, dependência descoberta); compila isoladamente e via reactor completo. Nenhum teste existia para as 2 classes migradas (confirmado por busca antes da migração) — "testes migrados permanecem verdes" vale trivialmente.
- AC #2: extração em exatamente 2 commits git — **Commit 1** (`parte 1 - mover`): novo módulo `feign` + as 2 classes + `pom.xml` raiz; **Commit 2** (`parte 2 - ajustes`): limpeza de `feign-core`/`jackson-databind` órfãos em `utils/pom.xml`.
- `utils` fica reduzido a 2 classes (`ValueType`, `LocaleService`, ambas com destino `core` congelado desde a Story 1.1, nunca migradas, fora do escopo desta story) e zero testes — o suficiente para a Story 1.14 (impor regras ArchUnit cross-módulo e remover `utils` do reactor) resolver o resto.
- `archtest` não ganhou dependência em `scos-foundation-feign` — mesmo padrão das Stories 1.8-1.12, fora do escopo desta story de extração de um único módulo.
- Nenhuma regra ArchUnit local foi criada em `feign` — mesmo precedente de `validation`/`cache`/`jpa`/`web` (Stories 1.9-1.12), que também não têm.
- **Correção pós-revisão**: nenhum teste existia para `JacksonEncoderCustom`/`JacksonDecoderCustom` antes desta story (nem em `utils`) — como são as únicas 2 classes do módulo e têm lógica real (encode/decode JSON, curto-circuito 404/204, truque mark/reset para distinguir corpo vazio de corpo com conteúdo), 2 suítes novas (`JacksonEncoderCustomTest`, `JacksonDecoderCustomTest`, 6 casos) foram adicionadas — não migração, cobertura nova para uma lacuna pré-existente que ficaria óbvia demais para ignorar num módulo de só 2 classes.
- **Aviso explícito para a Story 1.14**: `ValueType` e `LocaleService` (últimas 2 classes de `utils`) já têm destino `core` congelado desde a Story 1.1, nunca migrado por nenhuma das Stories 1.7-1.13. Como a Story 1.14 remove `utils` do reactor inteiramente, mover essas 2 classes deixa de ser "candidato a limpeza" e passa a ser **pré-requisito obrigatório** dessa story — não pode ficar pendurado de novo.

### File List

- `pom.xml` (raiz) — `<module>feign</module>` adicionado (após `web`) + `dependencyManagement` para `scos-foundation-feign` + comentário explicando que `feign` é independente da sequência da Fase 4
- `feign/pom.xml` (novo) — deps `scos-foundation-core`, `feign-core`, `jackson-databind`; test-scope `archunit-junit5`/`junit-jupiter`/`mockito-*`
- `feign/src/main/java/br/com/sawcunhaos/foundation/feign/{JacksonEncoderCustom,JacksonDecoderCustom}.java` (movidos de `utils`, sem alteração de lógica)
- `feign/src/test/java/br/com/sawcunhaos/foundation/feign/{JacksonEncoderCustomTest,JacksonDecoderCustomTest}.java` (novos, pós-revisão) — cobertura que nunca existiu, ver Completion Notes
- `utils/src/main/java/br/com/sawcunhaos/foundation/utils/configuration/feign/{JacksonEncoderCustom,JacksonDecoderCustom}.java` (removidos — movidos para `feign`)
- `utils/pom.xml` — dependências `feign-core`, `tools.jackson.core:jackson-databind` removidas (órfãs após a extração); comentário sobre dependências pré-existentes não removidas atualizado (2 classes restantes, não mais 4)

## Suggested Review Order

**Cobertura nova para lógica que nunca teve teste**

- `decode()` tem 3 ramos reais (404/204, corpo nulo/vazio, corpo com conteúdo) — o novo teste cobre os 5 casos.
  [`JacksonDecoderCustom.java:37`](../../feign/src/main/java/br/com/sawcunhaos/foundation/feign/JacksonDecoderCustom.java#L37)

- Suíte nova, 5 casos.
  [`JacksonDecoderCustomTest.java:37`](../../feign/src/test/java/br/com/sawcunhaos/foundation/feign/JacksonDecoderCustomTest.java#L37)

**Fiação do reactor**

- `feign` entra no reactor logo após `web`, independente da sequência da Fase 4.
  [`pom.xml:120`](../../pom.xml#L120)
