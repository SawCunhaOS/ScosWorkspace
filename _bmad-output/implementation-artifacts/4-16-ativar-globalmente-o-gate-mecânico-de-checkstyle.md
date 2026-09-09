# Story 4.16: Ativar globalmente o gate mecânico de Checkstyle

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero que o build do reactor inteiro falhe para qualquer API pública sem Javadoc,
Para que o piso de documentação seja garantido mecanicamente, não só por checagem manual, dali em diante.

## Acceptance Criteria

1. **Given** todos os módulos (Stories 4.2–4.15) já com Javadoc completo, e o diagnóstico da Story 4.1 sobre o estado real do `goal=check`, **When** o `failOnViolation=true` é ativado no `pluginManagement` do POM pai (corrigindo a amarração do `goal=check` primeiro, se o diagnóstico da Story 4.1 tiver apontado que não estava amarrado), **Then** `mvn -Panalyze verify` falha o build do reactor inteiro para qualquer método/tipo público sem Javadoc introduzido dali em diante.
2. **And** o build do reactor, rodado nesse ponto com todos os módulos já documentados, passa verde.

## Tasks / Subtasks

- [ ] Task 1: Pré-requisito bloqueante — confirmar que 4.2 a 4.15 estão `done` (AC: #1, #2)
  - [ ] Esta é a última story do epic e do plano de release inteiro (NFR7: "Bloqueia o release da 1.2.0") — não iniciar antes de todas as 14 stories de documentação (4.2-4.15) estarem concluídas; rodar o gate contra um reactor parcialmente documentado produziria falsos positivos em módulos que ainda não foram tratados
- [ ] Task 2: Aplicar a correção da amarração do `goal=check`, se necessária (AC: #1)
  - [ ] Consultar o resultado registrado na Story 4.1 (Completion Notes): se o diagnóstico confirmou que `maven-checkstyle-plugin` não tem `<goal>check</goal>` amarrado a nenhuma fase (achado já confirmado por leitura estática nesta mesma story-writing, ver Dev Notes — mas o diagnóstico empírico da 4.1 é a fonte de verdade final), adicionar a `<execution>` faltante ao `pluginManagement` do POM pai, dentro do `profile analyze` promovido pela Story 1.4
  - [ ] Se a Story 4.1 concluiu que já estava amarrado (via herança do `scos-bom`), pular esta sub-etapa e só ativar `failOnViolation`
- [ ] Task 3: Ativar `failOnViolation=true` no `pluginManagement` do POM pai (AC: #1)
  - [ ] Configurar `failOnViolation` (ou o equivalente `violationSeverity=error` + `failsOnError=true`, dependendo do que o diagnóstico da 4.1 indicar como necessário) no bloco `maven-checkstyle-plugin` dentro de `pluginManagement`, afetando todo módulo do reactor via herança (mesmo mecanismo que a Story 1.4 já promoveu para o profile inteiro)
- [ ] Task 4: Rodar o build completo e confirmar verde (AC: #2)
  - [ ] Rodar `mvn -Panalyze verify` no reactor inteiro
  - [ ] Se falhar por Javadoc faltante em algum módulo, **não é escopo desta story corrigir Javadoc** — isso indica que uma das Stories 4.2-4.15 ficou incompleta; voltar para a story correspondente, não tentar resolver aqui
  - [ ] Confirmar reactor verde antes de marcar esta story como concluída

## Dev Notes

- **Achado já confirmado por leitura estática (a Story 4.1 confirma empiricamente)**: hoje `maven-checkstyle-plugin` nos 4 módulos que já têm o profile `analyze` (`utils`, `exception`, `audit`, `jdempotent`) só configura `configLocation`, sem `<execution>`/`<goal>check</goal>` local — a amarração, se existir, vem do `pluginManagement` do parent `scos-bom:1.4.1` (artefato externo, não visível neste repositório). Esta story deve tratar o diagnóstico da Story 4.1 como a fonte de verdade final, não repetir a suposição.
- Esta é a story de maior blast radius do epic — afeta o build de **todo** o reactor, não um módulo isolado. Coordenar timing: rodar só depois que 4.2-4.15 estiverem realmente `done`, não `ready-for-dev`.
- NFR7 é explícito: "Bloqueia o release da 1.2.0" — esta story é o mecanismo que torna esse bloqueio real (antes dela, a checagem de Javadoc era só convenção/checagem manual).

### Project Structure Notes

- Arquivo modificado: `pom.xml` raiz (`pluginManagement`, dentro do profile `analyze` já promovido pela Story 1.4).
- Nenhum código de produção é alterado por esta story — só configuração de build.

### References

- [Source: pom.xml] (sem `maven-checkstyle-plugin` visível hoje, confirmado)
- [Source: audit/pom.xml#profile-analyze] (configuração atual por módulo, sem `goal=check` local)
- [Source: _bmad-output/implementation-artifacts/4-1-diagnosticar-o-gate-mecânico-de-javadoc-via-checkstyle.md] (diagnóstico que esta story consome como pré-requisito)
- [Source: _bmad-output/implementation-artifacts/1-4-promover-o-perfil-analyze-checkstyle-archunit-para-pluginman.md] (promoção do profile ao POM pai, pré-requisito estrutural)
- [Source: _bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/prd.md] (NFR7: bloqueia release 1.2.0)
- [Source: _bmad-output/planning-artifacts/epics.md#story-416-ativar-globalmente-o-gate-mecânico-de-checkstyle]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
