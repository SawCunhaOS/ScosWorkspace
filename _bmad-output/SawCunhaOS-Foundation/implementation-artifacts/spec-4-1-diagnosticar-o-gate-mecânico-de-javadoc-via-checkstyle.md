---
title: 'Diagnosticar o gate mecânico de Javadoc via Checkstyle'
type: 'chore'
created: '2026-09-14'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/4-1-diagnosticar-o-gate-mecânico-de-javadoc-via-checkstyle.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Não está confirmado se o Checkstyle falha o build hoje: o profile `analyze` (raiz do `pom.xml`, herdado por todo módulo do reactor) declara o `maven-checkstyle-plugin` com as regras de Javadoc já ativas (`MissingJavadocMethod`, `MissingJavadocType`, escopo `public`, `minLineCount=2`), mas sem nenhuma `<execution>` com `<goal>check</goal>` amarrada — e a severidade global do `checkstyle.xml` é `warning`, não `error`. A Story 4.16 (ativação final do gate) precisa saber, antes de ligar tudo globalmente, exatamente o que falta corrigir.

**Approach:** Criar um módulo Maven scratch fora do reactor principal (sem editar nenhum `pom.xml` existente), com um método público de 2+ linhas sem Javadoc, herdando o profile `analyze` real da raiz via `<parent><relativePath>`; rodar `mvn -Panalyze verify` isoladamente nele; registrar o resultado (build falhou ou passou, e por quê — incluindo o achado de severidade `warning`) nas Completion Notes e no File List da própria story `4-1-diagnosticar-o-gate-mecânico-de-javadoc-via-checkstyle.md`, marcar suas tasks/status e sincronizar `sprint-status.yaml`; remover o módulo scratch ao final. Nenhuma configuração real do reactor é alterada.

</frozen-after-approval>

## Implementation Notes

- Resultado empírico: `mvn -Panalyze verify` isolado no módulo scratch terminou `BUILD SUCCESS` — Checkstyle nunca é invocado (nenhuma linha `checkstyle:*` no log), confirmando a ausência de `goal=check`.
- Achado adicional (não estava no plano inicial): mesmo forçando a invocação direta de `checkstyle:check` sobre código com violação real, o resultado é `"0 Checkstyle violations"` a menos que `-Dcheckstyle.violationSeverity=warning` seja passado — porque `checkstyle.xml` define severidade global `warning` e o padrão do goal é `error`. Com o limiar corrigido, `core` sozinho já acumula 345 violações reais (a maioria não é Javadoc).
- Achado adicional 2: `configLocation` (`${maven.multiModuleProjectDirectory}/...`) só resolve corretamente quando o build roda a partir da raiz do reactor; invocado de dentro de um módulo isolado (scratch ou `core` real), falha com "Unable to find configuration file" — sem `.mvn/` na raiz para ancorar a resolução. Testado tanto no módulo scratch quanto no `core` real para confirmar que não é artefato do scratch.
- `-Dcheckstyle.configLocation` e `-Dcheckstyle.sourceDirectories` via CLI não sobrescrevem a configuração do POM nesta versão do plugin (3.6.0) — por isso o teste da violação real foi feito copiando temporariamente a classe para dentro de `core/` (removida ao final) em vez de via override de linha de comando.
- Todos os três achados (goal ausente, severidade, resolução de `configLocation`) foram registrados como pré-requisitos da Story 4.16 nas Completion Notes da story 4.1. Nenhum `pom.xml` do reactor foi alterado; `git status` limpo ao final.
