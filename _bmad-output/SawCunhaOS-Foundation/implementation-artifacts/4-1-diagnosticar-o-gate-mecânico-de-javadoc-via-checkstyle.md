# Story 4.1: Diagnosticar o gate mecânico de Javadoc via Checkstyle

Status: review

<!-- baseline_commit: 1986d6110d5c0495ec1a995176ede9dfe3414f47 -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero confirmar, sem ativar nada globalmente ainda, se o Checkstyle realmente falharia o build para API pública sem Javadoc,
Para saber se a Story 4.16 (ativação final) vai precisar corrigir a amarração do `goal=check` ou só ligar o `failOnViolation`.

## Acceptance Criteria

1. **Given** o perfil `analyze` já promovido a `pluginManagement` do POM pai (Epic 1, Story 1.4), sem `failOnViolation` global ativo, **When** `mvn -Panalyze verify` é executado isoladamente num módulo de teste/scratch com um método público sem Javadoc introduzido de propósito, **Then** o resultado (build falha ou não) é documentado como diagnóstico.
2. **And** nenhuma configuração é alterada nesta story — se o `goal=check` não estiver amarrado, isso fica registrado como item de entrada para a Story 4.16, não corrigido aqui.

## Tasks / Subtasks

- [x] Task 1: Levantar o estado atual real do `maven-checkstyle-plugin` antes de rodar qualquer teste (AC: #1)
  - [x] **Estado mudou desde o rascunho desta story (drift confirmado em 2026-09-14)**: a Story 1.4 já centralizou o profile `analyze` — hoje ele vive só na raiz (`pom.xml` do próprio `scos-foundation`, não no `scos-bom` externo), como um `<profile id="analyze">` herdado por todo módulo via `<parent>`. Nenhum módulo (`core`, `audit`, `jdempotent`, etc.) declara mais seu próprio profile local — `grep -rl "<id>analyze</id>" --include=pom.xml .` só retorna o `pom.xml` raiz.
  - [x] O bloco `<profile id="analyze">` (raiz, dentro de `<build><plugins>`) declara `maven-checkstyle-plugin` só com `<configLocation>${maven.multiModuleProjectDirectory}/etc/devops/checkstyle/checkstyle.xml</configLocation>` — **sem nenhuma `<execution>`/`<goal>check</goal>`**, ao contrário do `jacoco-maven-plugin` (execution `jacoco-check`) e do `dependency-check-maven` (`<goal>check</goal>` explícito), ambos no mesmo bloco.
  - [x] Achado adicional por leitura estática, não previsto no rascunho original: `etc/devops/checkstyle/checkstyle.xml` define `<property name="severity" value="warning"/>` no nível raiz, e nenhuma regra de Javadoc (`MissingJavadocMethod`, `MissingJavadocType`, etc.) sobrescreve essa severidade para `error`. Isso é relevante mesmo que o `goal=check` venha a ser amarrado, porque o `violationSeverity` padrão do goal `check` do `maven-checkstyle-plugin` é `error` — violações `warning` não contam para falha por padrão.
- [x] Task 2: Criar módulo scratch/teste isolado com violação proposital (AC: #1)
  - [x] Criado `zzz-scratch-story-4-1/` (fora do `<modules>` da raiz, nunca registrado em nenhum `pom.xml`) com `UndocumentedPublicClass` (classe pública + método público de 2 linhas, ambos sem Javadoc), `<parent>` apontando para o `pom.xml` raiz real via `relativePath` (herda o profile `analyze` de verdade, sem copiar/duplicar configuração).
  - [x] Rodado `mvn -Panalyze verify` isolado nele (ver Completion Notes para o resultado e para os testes complementares que isolaram a causa).
- [x] Task 3: Documentar o resultado (AC: #1, #2)
  - [x] Resultado registrado nas Completion Notes abaixo.
  - [x] Confirmado por que `goal=check` não amarrado é insuficiente sozinho como explicação — a severidade `warning` é uma segunda causa independente; ambas registradas como pré-requisito da Story 4.16.
  - [x] Nenhum `pom.xml` do reactor principal foi alterado — confirmado via `git status` (clean) ao final.
  - [x] Módulo scratch e o arquivo de teste temporário copiado para dentro de `core/` (ver Completion Notes) foram removidos; `git status` limpo ao final confirma que nada do reactor real ficou modificado.

## Dev Notes

- Esta story é puramente diagnóstica — nenhuma mudança de comportamento no reactor real. O scratch module existe só para o experimento e deve ser removido ao final.
- **Achado já confirmado por leitura estática (ponto de partida para o diagnóstico empírico)**: o checkstyle.xml em `etc/devops/checkstyle/checkstyle.xml` já contém as regras de Javadoc esperadas (`MissingJavadocMethod`, `MissingJavadocType`, `JavadocMethod`, `SummaryJavadoc`, etc. — confirmado via `grep -n Javadoc etc/devops/checkstyle/checkstyle.xml`), então a regra em si existe; a dúvida real é só se o `goal=check` está amarrado a alguma fase do build e se `failOnViolation` (ou o equivalente `violationSeverity`/`failsOnError`) está configurado para quebrar o build.
- **Correção à AC #1 (redigida antes da Story 1.4 ser implementada)**: a AC descreve o profile `analyze` como "promovido a `pluginManagement` do POM pai". Na implementação real da Story 1.4, ele virou um `<profile id="analyze">` comum com `<build><plugins>` direto, herdado por todo módulo via `<parent>` (herança padrão do Maven) — não um bloco `<pluginManagement>`. Funcionalmente equivalente para efeito deste diagnóstico (cada módulo recebe a mesma configuração automaticamente), mas os mecanismos de override/merge diferem; `epic-4-context.md` foi corrigido para não repetir o termo `pluginManagement`.
- **CI real usa `checkstyle:check` diretamente, não `mvn verify`** — ver Completion Notes para os achados corrigidos após a revisão; `AGENTS.md` (`## Running and verifying`) já documentava isso.
- Não confundir com o `maven-javadoc-plugin` do profile `release` do `pom.xml` raiz (linhas ~188-205), que gera o Javadoc JAR para publicação e já usa `-Xdoclint:none` (desabilita verificação de Javadoc malformado nesse plugin específico) — são dois mecanismos independentes; esta story trata só do Checkstyle.

### Project Structure Notes

- Nenhum arquivo de produção do reactor principal foi deixado alterado (confirmado via `git status` limpo ao final). Durante a execução, além do módulo scratch (`zzz-scratch-story-4-1/`, fora de `<modules>`), uma cópia temporária da classe de teste também foi colocada dentro de `core/src/main/java/.../zzzscratch/` para validar o `configLocation` resolvendo como o CI resolve (a partir da raiz) — ambos removidos ao final; ver "Metodologia" nas Completion Notes.

### References

- [Source: pom.xml] (parent `scos-bom:1.4.4-SNAPSHOT`; `maven-checkstyle-plugin` visível no profile `analyze` da raiz, linhas ~413-421, sem `<execution>`/`goal=check`)
- [Source: etc/devops/checkstyle/checkstyle.xml] (regras de Javadoc já presentes; `severity=warning` global na raiz do arquivo)
- [Source: .github/workflows/build.yml#security-check] (CI real: `mvn -B -Panalyze checkstyle:check` direto, sem `continue-on-error`, linhas 121-122 — não via `mvn verify`)
- [Source: AGENTS.md#running-and-verifying] (já documentava a invocação real do CI antes desta story)
- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/1-4-promover-o-perfil-analyze-checkstyle-archunit-para-pluginman.md] (pré-requisito: centralização do profile `analyze` no POM pai — implementado como `<profile>` herdado, não `pluginManagement`; ver Dev Notes)
- [Source: _bmad-output/SawCunhaOS-Foundation/planning-artifacts/epics.md#story-41-diagnosticar-o-gate-mecânico-de-javadoc-via-checkstyle]

Nota: `audit/pom.xml` não tem mais nenhuma referência a Checkstyle/profile `analyze` — foi centralizado na raiz pela Story 1.4 (drift confirmado nesta story; ver Task 1).

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

### Completion Notes List

- **Achado mais importante, descoberto só na revisão (blind-hunter) e confirmado por leitura direta**: o CI real (`.github/workflows/build.yml`, job `security-check`, linhas 121-122) roda `mvn -B -Panalyze checkstyle:check` **diretamente**, sem `continue-on-error` — não via `mvn -Panalyze verify`. Isso já estava documentado em `AGENTS.md` (`## Running and verifying`: "CI usa o profile `analyze` (`mvn -Panalyze checkstyle:check`, `spotbugs:check`, `dependency-check:check`, `jacoco:report`)"), carregado automaticamente nesta mesma sessão, e não foi cruzado com o desenho do experimento a tempo. Isso muda a leitura dos três achados abaixo: o Achado 1 (`goal=check` não amarrado ao `verify`) é irrelevante para o CI real, que nunca depende dessa amarração — importa só para quem roda `mvn -Panalyze verify` manualmente esperando feedback de Javadoc. O **Achado 2 (severidade) é o único motivo, hoje, pelo qual o CI não falha por Javadoc ausente** — e como o CI roda a partir da raiz do reactor, o Achado 3 (configLocation) não afeta o CI, só builds locais de módulo único.
- **Resultado do diagnóstico, na ordem de relevância real para o CI:**
  1. **Severidade global `warning` — a causa raiz do gate não funcionar mesmo quando invocado corretamente (CI ou não).** Invocando `checkstyle:check` diretamente (`default-cli`) no módulo `core` real (a partir da raiz do reactor — a mesma forma que o CI invoca) com a violação injetada, o resultado foi `"You have 0 Checkstyle violations."` / `BUILD SUCCESS`, idêntico ao passo real do CI hoje. Só ao forçar `-Dcheckstyle.violationSeverity=warning` (equiparando o limiar do goal à severidade real configurada em `checkstyle.xml`) o build falhou: `"You have 345 Checkstyle violations."`, incluindo `MissingJavadocType` na classe injetada (`core/.../zzzscratch/UndocumentedPublicClass.java:[3,1] (javadoc) MissingJavadocType: Falta o comentário Javadoc.`). Ou seja: o `violationSeverity` padrão do goal (`error`) nunca bate com a severidade `warning` do `checkstyle.xml` — **345 violações reais já existem em `core` hoje, silenciosamente não contabilizadas pelo passo de CI que já roda em todo PR**, a maioria (`indentation`, `LineLength`) não relacionada a Javadoc.
     - Método `buildGreeting` (público, 2 linhas, sem Javadoc) não foi sinalizado por `MissingJavadocMethod` nesse mesmo run, só `MissingJavadocType` na classe. Explicação provável (semântica documentada do Checkstyle, não testada isoladamente aqui): `minLineCount="2"` em `MissingJavadocMethod` exige *mais* que 2 linhas no corpo para exigir Javadoc — um corpo de exatamente 2 linhas fica isento. Vale confirmar com um corpo de 3+ linhas ao escrever os testes de Javadoc de método na Story 4.16; não muda a conclusão (o mecanismo já foi provado via `MissingJavadocType`).
  2. **`goal=check` não amarrado ao `verify`** — real, mas só relevante para desenvolvimento local. Rodando `mvn -Panalyze verify` isolado no módulo scratch (`UndocumentedPublicClass`, sem Javadoc), o log completo não contém nenhuma linha `checkstyle:*` — o plugin nunca é invocado durante esse ciclo de vida. Build terminou `SUCCESS` em 0.56s. `findbugs-maven-plugin` (declarado no mesmo profile, zero `<execution>`) está na mesma situação — mas isso também não representa o CI: o job real usa `spotbugs:check` (plugin `spotbugs-maven-plugin`, invocado diretamente, linha 125), um artefato Maven diferente do `findbugs-maven-plugin` declarado no profile `analyze`.
  3. **`configLocation` frágil a invocação isolada** — real, mas não afeta o CI (que sempre roda a partir da raiz). `<configLocation>${maven.multiModuleProjectDirectory}/etc/devops/checkstyle/checkstyle.xml</configLocation>` só resolve para a raiz real do reactor quando o build começa a partir dela (nenhum `.mvn/` existe no repo para ancorar a busca). Rodando `checkstyle:check` de dentro de um módulo isolado (scratch OU o `core` real, via `cd core && mvn -Panalyze checkstyle:check`) falha com `Unable to find configuration file at location: .../core/etc/devops/checkstyle/checkstyle.xml`. Isso significa que **um desenvolvedor que rodar `mvn -Panalyze verify`/`checkstyle:check` de dentro de um módulo (fluxo local comum) quebraria com um erro de configuração ausente, não com feedback de Javadoc** — vale corrigir (ex.: `.mvn/` na raiz, ou `${session.executionRootDirectory}`) para não confundir quem testa localmente, mesmo não bloqueando o CI.
     - Confirmado que builds a partir da raiz (`mvn ... -pl core`) resolvem corretamente — o problema é específico de invocação isolada, não do `configLocation` em si.
- **Metodologia**: nenhum `pom.xml` do reactor foi editado. Módulo scratch `zzz-scratch-story-4-1/` criado fora de `<modules>`, com `<parent><relativePath>../pom.xml</relativePath></parent>` (herda o profile real, sem copiar configuração). Para testar contra um `configLocation` que resolvesse corretamente (a mesma forma que o CI roda), a mesma classe foi temporariamente copiada para dentro de `core/src/main/java/.../zzzscratch/` (pacote descartável), testada via `-pl core` a partir da raiz, e removida em seguida — `-Dcheckstyle.configLocation=...` e `-Dcheckstyle.sourceDirectories=...` via CLI não sobrescrevem o valor declarado no POM nesta versão do plugin (3.6.0), por isso a cópia temporária foi o único jeito confiável de testar contra o `configLocation` real sem alterar POMs. `git status` limpo ao final confirma remoção completa de ambos os artefatos temporários.
- **Para a Story 4.16**, em ordem de prioridade real: (1) **decidir e ajustar a severidade** — é o único bloqueio que impede o CI de falhar hoje (elevar as regras de Javadoc para `error` no `checkstyle.xml`, ou setar `violationSeverity=warning` no plugin — sabendo que isso aciona 345 violações pré-existentes só em `core`, a maioria não é Javadoc, então a ativação pode quebrar builds de forma ampla se não for faseada); (2) amarrar `<goal>check</goal>` ao `maven-checkstyle-plugin` no profile `analyze` só se também se quiser que `mvn verify` local reflita o gate do CI (o CI em si não precisa disso); (3) tornar `configLocation` resiliente a build de módulo único, por ergonomia de desenvolvimento local (não bloqueia o CI).

### File List

Nenhum arquivo de produção foi criado ou alterado (diagnóstico puro, conforme AC #2). Alterados apenas os artefatos de tracking do BMAD:

- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/4-1-diagnosticar-o-gate-mecânico-de-javadoc-via-checkstyle.md` (este arquivo — Completion Notes, File List, tasks, status)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/sprint-status.yaml` (status da story)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/epic-4-context.md` (novo — contexto compilado da Epic 4, reutilizável pelas próximas stories 4.x)
- `_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/spec-4-1-diagnosticar-o-gate-mecânico-de-javadoc-via-checkstyle.md` (novo — spec do bmad-build para esta execução, rota `oneshot`)

## Review Triage Log

Camada rodada: blind-hunter (8 achados, piso N=5 para ~21,5kB de conteúdo alterado). Iteração de review: 1.

1. **[blind-hunter] CI real roda `checkstyle:check` direto (não via `verify`), tornando o Achado 1 (goal=check) irrelevante para o CI e o Achado 2 (severidade) o único bloqueio de fato.** Verdict: `high`. Evidência: `.github/workflows/build.yml:121-122` confirmado por leitura direta (`mvn -B -Panalyze checkstyle:check`, sem `continue-on-error`, diferente do passo `dependency-check` logo acima que tem `continue-on-error: true`). → `patch` (Completion Notes reescritas para liderar com essa leitura).
2. **[blind-hunter] `AGENTS.md`, já carregado no contexto desta sessão, documentava a invocação real do CI e não foi citado.** Verdict: `high` (mesma causa raiz do achado 1 — falha de processo em cruzar contexto já disponível). Evidência: `AGENTS.md:23` confirmado, idêntico ao citado pelo revisor. → `patch` (citado em References e Completion Notes).
3. **[blind-hunter] References desatualizadas (`scos-bom:1.4.1`, `audit/pom.xml#profile-analyze`) contradizem os próprios achados da story.** Verdict: `medium`. Evidência: `pom.xml:23` mostra `scos-bom:1.4.4-SNAPSHOT`; `grep checkstyle audit/pom.xml` não retorna nada. → `patch` (References reescritas).
4. **[blind-hunter] AC #1/`epic-4-context.md` descrevem "promovido a `pluginManagement`", mas a implementação real é um `<profile>` herdado, não `pluginManagement`.** Verdict: `medium`. Evidência: `pom.xml:355-421` confirmado (bloco `<profile><build><plugins>`, sem `<pluginManagement>`). → `patch` (nota em Dev Notes; `epic-4-context.md` corrigido; AC #1 preservada como está, por ser texto histórico da story).
5. **[blind-hunter] `epic-4-context.md` afirma que `privacy` "precisa ligar" o perfil `analyze`, mas ele já herda automaticamente.** Verdict: `medium` (risco de a Story 4.15 fazer trabalho desnecessário/incorreto). Evidência: `privacy/pom.xml` sem nenhuma menção a `checkstyle`/`analyze`; `privacy` é `<module>` declarado na raiz (herda via `<parent>` como qualquer outro). → `patch` (`epic-4-context.md` corrigido).
6. **[blind-hunter] Project Structure Notes ("só um módulo scratch") inconsistente com as Completion Notes (também copiou um arquivo para dentro de `core/`).** Verdict: `low`. Evidência: texto original da story vs. Completion Notes escritas nesta execução. → `patch` (Project Structure Notes atualizado).
7. **[blind-hunter] `buildGreeting` não foi sinalizado por `MissingJavadocMethod` e a story deixou isso sem explicação.** Verdict: `low` (não muda a conclusão, que já se apoia em `MissingJavadocType`). Evidência: `checkstyle.xml:344` (`minLineCount="2"`) é consistente com a semântica documentada do Checkstyle de exigir *mais* que o mínimo — explicação plausível, não testada isoladamente. → `patch` (uma frase de esclarecimento adicionada).
8. **[blind-hunter] `spec-4-1-...md` (frontmatter `status: in-progress`) e a story (`Status: review`) estavam dessincronizados no momento da revisão.** Verdict: `low` (estado transitório esperado do workflow oneshot — resolve-se no Finalize Spec, que roda logo em seguida). → `patch` (spec finalizado com `status: done` nesta mesma etapa).
9. **[blind-hunter, nota adicional] Comparação com `findbugs-maven-plugin` como analogia ignora que o CI real usa `spotbugs:check` (plugin diferente).** Verdict: `low` (mesma causa raiz dos achados 1/2). Evidência: `build.yml:124-126` usa `mvn -B -Panalyze spotbugs:check`, plugin `spotbugs-maven-plugin`, não `findbugs-maven-plugin`. → `patch` (nota adicionada nas Completion Notes).
