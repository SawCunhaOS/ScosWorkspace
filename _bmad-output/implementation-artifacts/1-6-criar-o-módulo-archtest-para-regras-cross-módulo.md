---
baseline_commit: 637f22c66b71094e4dc9099145a6522a2bc58b8f
---

# Story 1.6: Criar o módulo `archtest` para regras cross-módulo

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero um módulo de teste dedicado para regras ArchUnit que citam mais de um módulo,
Para que nenhuma regra cross-módulo fique duplicada ou ausente.

## Acceptance Criteria

1. **Given** que nenhum módulo de implementação enxerga o classpath inteiro sozinho, **When** o módulo `archtest` é criado (`scope=test`, sem código de produção, dependendo de todos os outros só para teste), **Then** ele compila e roda no perfil `analyze` do build do reactor.
2. **And** o módulo está pronto para receber a primeira regra cross-módulo nas stories seguintes.

## Tasks / Subtasks

- [x] Task 1: Criar o módulo Maven `scos-foundation-archtest` (AC: #1)
  - [x] `scope=test` — nenhuma classe de produção, só `src/test/java`
  - [x] Depender, em escopo `test`, de todos os módulos já existentes no reactor neste ponto (`privacy`, `utils`, `exception`, `audit`, `jdempotent`, `audit-api`, `jdempotent-api`, `validation-api`): só assim consegue enxergar o classpath inteiro para checar regras cross-módulo
  - [x] Usar a dependência `com.tngtech.archunit:archunit-junit5:1.5.0` já gerenciada em `pluginManagement`/`dependencyManagement` do pai (Story 1.4) — declarada sem versão
  - [x] Perfil `analyze` herdado do pai (Story 1.4) — não precisa de ativação/declaração extra no módulo, já roda para todo módulo do reactor
- [x] Task 2: README do módulo (AC: #2)
  - [x] Explica o propósito: hospedar regras ArchUnit que citam mais de um módulo (ex.: "nada depende de `web`", "nenhum ciclo entre módulos") — regras que dizem respeito a um módulo só continuam nascendo dentro do próprio módulo
  - [x] Seção "Regras existentes" vazia/placeholder mínima — a primeira regra real chega só na Story 1.14
- [x] Task 3: Adicionar `archtest` em `<modules>` do `pom.xml` raiz (AC: #1)

## Dev Notes

- Este módulo nasce **vazio de regras** — só a estrutura. As regras cross-módulo (ex.: "nenhum módulo além de aplicações depende de `web`", "sem ciclo entre módulos") são escopo da Story 1.14, depois que os módulos folha existirem. Não antecipar regras aqui — a AC #2 pede só que o módulo esteja "pronto para receber", não que já receba.
- Regras que citam um módulo só (ex.: "`core` não importa Spring") **não** entram aqui — nascem dentro do próprio módulo protegido, no mesmo commit que o cria (AD-5). `archtest` é exclusivamente para regras que nenhum módulo individual consegue verificar sozinho.
- Depende da Story 1.4 (perfil `analyze` e ArchUnit já gerenciados no pai) estar concluída antes.
- Sem dependência circular: `archtest` depende de tudo (escopo teste), nada depende de `archtest`.

### Project Structure Notes

- Módulo Maven novo: `archtest/` — `pom.xml`, `README.md`, `src/test/java/` vazio (estrutura pronta, sem classe de teste real ainda).
- `pom.xml` raiz ganha `<module>archtest</module>`.

### References

- [Source: _bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/ARCHITECTURE-SPINE.md#ad-5--archunit-como-mecanismo-de-imposição-das-regras-de-módulo-adopted]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/GUIA-DE-IMPLEMENTACAO.md#3-archtest--o-módulo-novo-que-a-spine-adicionou]
- [Source: _bmad-output/planning-artifacts/epics.md#story-16-criar-o-módulo-archtest-para-regras-cross-módulo]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -pl archtest -Panalyze -Ddependency-check.skip=true verify` (deps já instaladas em `~/.m2` de sessões anteriores) → `BUILD SUCCESS`. `-Ddependency-check.skip` só porque a API pública do NVD respondeu 429 (rate limit) neste ambiente — nada a ver com o módulo novo.
- `mvn -pl archtest -am -Panalyze -Ddependency-check.skip=true verify` (rebuild de todos os módulos a partir do zero) falha no `jacoco-check` de `scos-foundation-audit-api` (cobertura abaixo de 80%). Confirmado pré-existente: mesma falha reproduzida isolando `mvn -pl audit-api -am -Panalyze verify` após `git stash` (sem nenhuma mudança desta story) — não é regressão introduzida aqui.
- `mvn -q validate` no reactor completo (com `archtest` já em `<modules>`) → sucesso, confirma grafo de dependências sem ciclo.
- **Revisão (3 camadas) — 1 achado `patch` aplicado, 1 `defer` (atualização de item já existente), restante `reject`**:
  - **Corrigido**: comentário em `pom.xml:98` sugeria que a ordem de listagem em `<modules>` determina a ordem de build do Maven — impreciso (Maven ordena por topologia real de dependências, não por posição na lista). Reformulado para deixar isso explícito.
  - **Gap de verificação real, fechado nesta revisão**: a verificação original do implementador (`mvn -pl archtest -Panalyze verify`, sem `-am`) resolve as 8 dependências só via cache `.m2` local, nunca contra o código-fonte atual dos módulos irmãos no mesmo reactor — não prova que `archtest` builda corretamente dentro de um build real do reactor (AC #1). Toda tentativa de rodar o caminho real (`-am`, ou o comando literal do CI `mvn -B -Panalyze test`) falha *antes* de alcançar `archtest`, por dois bloqueios pré-existentes não relacionados a esta story: `jacoco-check` com 0% de cobertura em `audit-api` (Story 1.5) e erro de Testcontainers/Docker em `jdempotent` (ambiente sem Docker). Ambos já registrados em `deferred-work.md`. Fechei o gap rodando `mvn -o -Panalyze -am -pl archtest verify -Djacoco.skip=true -DskipTests=true -Ddependency-check.skip=true` — contorna só os dois bloqueios já conhecidos, mantém tudo mais real (recompila todos os módulos irmãos do código-fonte, não do cache). Resultado: reactor summary mostra `SCOS Foundation Archtest ... SUCCESS`, confirmando que a AC #1 se sustenta — o wiring de dependências de `archtest` contra o reactor real está correto.
  - **Rejeitado** (sem ação): ausência de classe ArchUnit/smoke test (intencional — spec explicitamente proíbe antecipar regras, primeira chega na Story 1.14); dependências não conferíveis a partir do diff parcial mostrado ao revisor (conferidas por mim lendo o `pom.xml` completo — todas as 8 registradas e versionadas via `dependencyManagement` do pai); ausência de `maven.deploy.skip`/`install.skip` para módulo test-only (especulativo, sem exigência da story, módulo ganha conteúdo real na Story 1.14); plugins surefire/compiler sem versão/config (herdados do `pluginManagement` do pai, mesmo padrão dos módulos `*-api` da Story 1.5); redeclaração de `maven.compiler.source/target=25` no filho (mesmo padrão já aceito nos módulos irmãos); `jacoco-check` com zero classes (confirmado que pula graciosamente, não falha); README sem guia prático para a Story 1.14 (fora do escopo desta story — Task 2 pede só propósito + placeholder vazio); ausência de `.gitkeep` em `src/test/java` (mesmo precedente de `validation-api`, spec pede não antecipar estrutura); risco especulativo de conflito de versão transitiva entre as 8 dependências (`RequireUpperBoundDeps` do enforcer passou, confirmado em múltiplas execuções).

### Completion Notes List

- Módulo `archtest` criado como `scope=test` puro: sem `src/main/java`, dependência de todos os 8 módulos existentes do reactor (`privacy`, `utils`, `exception`, `audit`, `jdempotent`, `audit-api`, `jdempotent-api`, `validation-api`) declarada com `<scope>test</scope>`, sem versão explícita para nenhuma delas (gerenciadas pelo `dependencyManagement` do pai).
- `src/test/java` não foi criado fisicamente (git não versiona diretório vazio) — mesmo padrão já usado em `validation-api`, que também não tem `src/test` hoje e builda normalmente. Estrutura "pronta para receber" não exige o diretório existir antes da primeira classe de teste (Story 1.14).
- Perfil `analyze` não precisou de declaração adicional no `pom.xml` do módulo: é herdado automaticamente por todo módulo do reactor via o pai (Story 1.4), confirmado rodando `mvn -pl archtest -Panalyze verify` sem nenhum plugin do perfil declarado no módulo.
- README segue o mesmo formato dos demais módulos de contrato (`audit-api`/`jdempotent-api`): propósito, regra de fronteira (o que entra vs. o que não entra) e seção "Regras existentes" como placeholder vazio.

### File List

- `archtest/pom.xml` (novo)
- `archtest/README.md` (novo)
- `pom.xml` (raiz — `<module>archtest</module>` adicionado ao final de `<modules>`)

## Suggested Review Order

- Ponto de entrada: o módulo novo entra como última folha do reactor, depois de tudo que ele testa.
  [`pom.xml:98`](../../pom.xml#L98)

- Módulo Maven `scope=test`: 8 dependências versionless (geridas pelo pai), sem `src/main/java`.
  [`archtest/pom.xml:87`](../../archtest/pom.xml#L87)

- Fronteira do módulo: regras cross-módulo entram aqui; regras de um módulo só nascem no próprio módulo.
  [`README.md:12`](../../archtest/README.md#L12)
