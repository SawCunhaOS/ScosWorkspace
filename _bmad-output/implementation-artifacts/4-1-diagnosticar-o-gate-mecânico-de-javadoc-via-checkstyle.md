# Story 4.1: Diagnosticar o gate mecânico de Javadoc via Checkstyle

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero confirmar, sem ativar nada globalmente ainda, se o Checkstyle realmente falharia o build para API pública sem Javadoc,
Para saber se a Story 4.16 (ativação final) vai precisar corrigir a amarração do `goal=check` ou só ligar o `failOnViolation`.

## Acceptance Criteria

1. **Given** o perfil `analyze` já promovido a `pluginManagement` do POM pai (Epic 1, Story 1.4), sem `failOnViolation` global ativo, **When** `mvn -Panalyze verify` é executado isoladamente num módulo de teste/scratch com um método público sem Javadoc introduzido de propósito, **Then** o resultado (build falha ou não) é documentado como diagnóstico.
2. **And** nenhuma configuração é alterada nesta story — se o `goal=check` não estiver amarrado, isso fica registrado como item de entrada para a Story 4.16, não corrigido aqui.

## Tasks / Subtasks

- [ ] Task 1: Levantar o estado atual real do `maven-checkstyle-plugin` antes de rodar qualquer teste (AC: #1)
  - [ ] **Confirmado por leitura direta**: `pom.xml` raiz (parent `scos-bom:1.4.1`, resolvido via Maven, artefato externo não presente neste repositório) não declara `maven-checkstyle-plugin` em nenhum lugar visível — `grep -n checkstyle pom.xml` não retorna nada
  - [ ] Hoje, 4 dos 5 módulos do reactor (`utils`, `exception`, `audit`, `jdempotent` — confirmado via `grep -rl "<id>analyze</id>" --include=pom.xml .`) já têm um bloco `<profile id="analyze">` que configura `maven-checkstyle-plugin` apenas com `<configLocation>${project.parent.basedir}/etc/devops/checkstyle/checkstyle.xml</configLocation>` (ex.: `audit/pom.xml`, dentro do profile `analyze`) — **nenhuma `<execution>` com `<goal>check</goal>` está declarada localmente nesses módulos** para o `maven-checkstyle-plugin` especificamente (ao contrário do `jacoco-maven-plugin`, que tem `jacoco-check` explícito, e do `dependency-check-maven`, que tem `<goal>check</goal>` explícito, ambos no mesmo bloco de profile)
  - [ ] Isso significa que a amarração do `goal=check` do Checkstyle, se existir, **só pode vir do `pluginManagement` do parent `scos-bom`** (não visível neste repositório) — por isso esta story precisa rodar o build de verdade para descobrir empiricamente, não é possível confirmar só por leitura estática do código deste reactor
- [ ] Task 2: Criar módulo scratch/teste isolado com violação proposital (AC: #1)
  - [ ] Criar um módulo Maven temporário (fora do reactor principal, ou um submódulo descartável) com uma classe pública com um método público sem Javadoc
  - [ ] Aplicar o mesmo profile `analyze` (copiar a configuração de `configLocation` já usada em `audit/pom.xml`) e rodar `mvn -Panalyze verify`
- [ ] Task 3: Documentar o resultado (AC: #1, #2)
  - [ ] Registrar no arquivo de story (Completion Notes) se o build falhou (Checkstyle bloqueou) ou passou (Checkstyle rodou mas não bloqueou, ou nem rodou)
  - [ ] Se o `goal=check` não estiver amarrado, escrever explicitamente: "Story 4.16 precisa adicionar a execution `<goal>check</goal>` ao `maven-checkstyle-plugin` (hoje ausente neste reactor) antes de ligar `failOnViolation`"
  - [ ] Não alterar nenhum `pom.xml` do reactor principal nesta story — o diagnóstico é só leitura/teste isolado
  - [ ] Remover o módulo scratch/teste ao final (não deixar artefato de teste no reactor)

## Dev Notes

- Esta story é puramente diagnóstica — nenhuma mudança de comportamento no reactor real. O scratch module existe só para o experimento e deve ser removido ao final.
- **Achado já confirmado por leitura estática (ponto de partida para o diagnóstico empírico)**: o checkstyle.xml em `etc/devops/checkstyle/checkstyle.xml` já contém as regras de Javadoc esperadas (`MissingJavadocMethod`, `MissingJavadocType`, `JavadocMethod`, `SummaryJavadoc`, etc. — confirmado via `grep -n Javadoc etc/devops/checkstyle/checkstyle.xml`), então a regra em si existe; a dúvida real é só se o `goal=check` está amarrado a alguma fase do build (via `pluginManagement` do `scos-bom`, não visível neste repo) e se `failOnViolation` (ou o equivalente `violationSeverity`/`failsOnError`) está configurado para quebrar o build.
- Não confundir com o `maven-javadoc-plugin` do profile `release` do `pom.xml` raiz (linhas ~188-205), que gera o Javadoc JAR para publicação e já usa `-Xdoclint:none` (desabilita verificação de Javadoc malformado nesse plugin específico) — são dois mecanismos independentes; esta story trata só do Checkstyle.

### Project Structure Notes

- Nenhum arquivo de produção é criado ou alterado — só um módulo scratch temporário, removido ao final, e as Completion Notes desta story.

### References

- [Source: pom.xml] (parent `scos-bom:1.4.1`, sem `maven-checkstyle-plugin` visível)
- [Source: audit/pom.xml#profile-analyze] (configuração atual do Checkstyle, sem `goal=check` local)
- [Source: etc/devops/checkstyle/checkstyle.xml] (regras de Javadoc já presentes)
- [Source: _bmad-output/implementation-artifacts/1-4-promover-o-perfil-analyze-checkstyle-archunit-para-pluginman.md] (pré-requisito: promoção do profile `analyze` ao POM pai)
- [Source: _bmad-output/planning-artifacts/epics.md#story-41-diagnosticar-o-gate-mecânico-de-javadoc-via-checkstyle]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
