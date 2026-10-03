---
title: 'Ativar globalmente o gate mecânico de Checkstyle'
type: 'chore'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
baseline_revision: '228ab40282886e41da030e5ccbbd4d292c05a4f4'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/4-16-ativar-globalmente-o-gate-mecânico-de-checkstyle.md']
---

<intent-contract>

## Intent

**Problem:** O diagnóstico da 4.1 mostrou duas causas independentes para o Checkstyle não barrar Javadoc ausente: `goal=check` não amarrado ao `verify` no perfil `analyze` e severidade global `warning` no `checkstyle.xml` (o goal só falha em `error`). Ligar `failOnViolation` com o conjunto completo de regras quebraria o reactor com milhares de avisos de estilo (indentação, linha longa, imports).

**Approach:** Amarrar `check` à fase `verify` no perfil `analyze` (`failOnViolation=true`, `violationSeverity=error`) e elevar para `error` apenas `MissingJavadocMethod` e `MissingJavadocType`. O restante do estilo segue `warning` (reportado, não bloqueia; registrado em deferred-work.md).

## Boundaries & Constraints

**Always:** reactor verde com `mvn -Panalyze verify`; qualquer API pública sem Javadoc futura quebra o build.
**Never:** refatorar formatação em massa; alterar comportamento ou assinaturas.

</intent-contract>

## Code Map

- `pom.xml` (perfil `analyze`, `maven-checkstyle-plugin`) -- execution `checkstyle-javadoc-gate` (fase `verify`, goal `check`) + `failOnViolation`/`violationSeverity=error`
- `etc/devops/checkstyle/checkstyle.xml` -- `severity=error` em `MissingJavadocMethod`/`MissingJavadocType`
- `web/.../annotation/ScosRequest{GET,POST,PUT,PATCH,DELETE}.java` -- 21 atributos de anotação sem Javadoc (lacuna residual da 4.11, revelada pelo gate) documentados
- CI (`.github/workflows/build.yml:122`, `mvn -Panalyze checkstyle:check`) passa a falhar por Javadoc ausente sem alteração

## Tasks & Acceptance

**Execution:**
- `pom.xml` + `checkstyle.xml` -- ativar gate -- feito
- `web` -- Javadoc dos atributos das meta-anotações -- feito

**Acceptance Criteria:**
- Given o gate ativado, when `mvn -Panalyze checkstyle:check` roda antes do ajuste em `web`, then falha com 21 `MissingJavadocMethod` (prova de que o gate barra).
- Given os módulos documentados, when `mvn -o -Panalyze -DskipTests verify` roda no reactor, then BUILD SUCCESS com `checkstyle:check` executado em todos os 16 módulos.

## Verification

**Commands:**
- `mvn -o -Panalyze checkstyle:check` -- esperado: sem violações error
- `mvn -o -Panalyze -DskipTests verify` -- esperado: BUILD SUCCESS
- `mvn -o clean install` -- esperado: BUILD SUCCESS

## Auto Run Result

Ver Completion Notes da story. Revisão adversarial feita inline (subagentes não lançados).
