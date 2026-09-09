---
baseline_commit: 3e99221db78565ca0a8a6b7b2a8cd70ece24938c
---

# Story 1.1: Congelar o inventário classe→módulo

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero um inventário congelado de destino para cada uma das 71 classes de `utils`,
Para que nenhuma migração posterior deixe uma classe sem módulo de destino.

## Acceptance Criteria

1. **Given** as 71 classes atuais de `scos-foundation-utils`, **When** o inventário de destino é revisado, **Then** cada classe tem exatamente um módulo-alvo listado.
2. **And** nenhum destino é `utils.utils` ou pacote genérico equivalente.
3. **And** o inventário está documentado e acessível como referência única para as demais stories deste epic.

## Tasks / Subtasks

- [x] Task 1: Confirmar a contagem real de classes em `utils/src/main/java` bate com 71 (AC: #1)
  - [x] Rodar `find utils/src/main/java -name "*.java" | wc -l` e reconciliar qualquer divergência com a tabela da Seção 3 do plano de origem antes de congelar
- [x] Task 2: Consolidar o inventário classe→módulo num artefato único e citável (AC: #1, #3)
  - [x] Criar `_bmad-output/implementation-artifacts/inventario-classe-modulo.md` com uma tabela `classe completa (FQN atual) → módulo destino → pacote destino`, cobrindo as 71 classes sem omissão
  - [x] Basear a tabela nas Seções 3 e "Todas as anotações, por destino" de `etc/doc/plano/plano-decomposicao-utils.md` (já congela `core`, `spring`, `web`, `cache`, `jpa`, `validation`, `audit-api`, `jdempotent-api`, `validation-api`) e na tabela de exemplos do addendum do PRD
  - [x] Confirmar explicitamente os dois pontos que o plano original registra como lacuna resolvida na Fase 0: `annotation/rules/*` (`ScosRule`, `ScosRuleService`) → `spring`; `listener/ScosOnStartupListener` → `spring` (a interface `ScosStartupListener` fica em `core`)
- [x] Task 3: Validar que nenhum destino usa nome genérico (AC: #2)
  - [x] Checar que nenhuma linha da tabela aponta para um sub-pacote `util`/`common`/`utils.utils` dentro de `core` ou de qualquer módulo novo
- [x] Task 4: Tornar o inventário referência única (AC: #3)
  - [x] Adicionar ao topo do arquivo uma nota "fonte congelada — Fase 0, Story 1.1" e linkar de volta para o plano de origem e o addendum, para que Stories 1.5–1.13 apontem para este arquivo único em vez de recitarem a tabela

## Dev Notes

- Esta story **não move nenhum arquivo Java** — é só o congelamento documental do destino. Nenhum código muda.
- Fonte primária já existente com a decomposição completa das 71 classes: `etc/doc/plano/plano-decomposicao-utils.md` (Seção 3 "Módulos-alvo" e Seção "Todas as anotações, por destino"). Não redigitar do zero — extrair e formalizar como tabela única.
- Fonte secundária (exemplos, não exaustiva): `_bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/addendum.md`.
- Levantamento already-done da árvore atual (para conferência, não repetir a exploração): pacotes de `utils/src/main/java/br/com/sawcunhaos/foundation/utils/` — `adapter` (3), `annotation` (1 + `audit`:2, `jdempotent`:5, `normalizestrings`:1, `request`:6, `rules`:2), `aspect` (1), `configuration/cache` (5), `configuration/feign` (2), `configuration/hibernate` (1), `configuration/liquibase` (1), `configuration/rest` (1 + `filter`:4), `dto` (1+2), `entity` (1), `enums` (4), `exception` (1), `listener` (1), `sort` (1), `specification` (5), `utils` (9, inclui `GsonUtils` que será removido na Story 1.3, não migrado), `validation` (`taxIdentifier`:6, `zipcode`:2), `valueobjects` (4).
- **NFR4** (escopo de mudança): esta story é puramente documental — nenhuma alteração de comportamento, nenhum arquivo Java tocado.

### Project Structure Notes

- Novo artefato: `_bmad-output/implementation-artifacts/inventario-classe-modulo.md` (não é código de produção, é o registro de referência do épico).
- Nenhum módulo Maven é criado ou alterado nesta story.

### References

- [Source: etc/doc/plano/plano-decomposicao-utils.md#3-módulos-alvo]
- [Source: etc/doc/plano/plano-decomposicao-utils.md#todas-as-anotações-por-destino]
- [Source: _bmad-output/planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/addendum.md#mapeamento-classe--módulo-inventário-de-referência]
- [Source: _bmad-output/planning-artifacts/epics.md#story-11-congelar-o-inventário-classemódulo]
- [Source: _bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/ARCHITECTURE-SPINE.md#ad-1--fronteira-e-direção-de-dependência-entre-módulos-adopted]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `find utils/src/main/java -name "*.java" | wc -l` → 72 (não 71). Divergência reconciliada: o plano de origem (Seção 3, "Todas as anotações, por destino") omite `ScosRequestPATCH`, que existe no código atual como irmã de `ScosRequestGET/POST/PUT/DELETE/Mapping`. Congelada com o mesmo destino delas (`web`).
- **Revisão retroativa (fechamento do Épico 1, 2026-08-23)**: esta story nunca tinha passado pela etapa de revisão adversarial do workflow. Rodada agora, cobrindo as Stories 1.1-1.4 juntas. Achado real: a linha 71 desta Completion Notes ("`DateUtils` → `br.com.sawcunhaos.foundation.core`") está desatualizada — a classe real hoje vive em `br.com.sawcunhaos.foundation.core.utils`, não na raiz do pacote `core`, junto com `HashUtils`/`StringFieldUtils`. Mesma categoria de divergência já registrada em `deferred-work.md` desde a Story 1.8 para `ScosStartupListener`/`StringTransformRule` — agora ampliada com mais 3 classes, e uma entrada nova adicionada em `deferred-work.md` especificamente para esta story. Não é um erro desta story em si (o inventário foi congelado corretamente para o estado da época); é o inventário divergindo da implementação real ao longo de stories posteriores, sem mecanismo de imposição que os mantenha sincronizados.

### Completion Notes List

- Inventário criado em `_bmad-output/implementation-artifacts/inventario-classe-modulo.md` cobrindo as 72 classes reais de `utils/src/main/java` (71 do plano de origem + `ScosRequestPATCH`, reconciliada — ver Debug Log).
- Nenhuma classe ficou sem disposição explícita: as 4 classes que a Story 1.3 vai remover (3 adapters `java.time` do Gson + `GsonUtils`) recebem a disposição explícita `REMOVIDO — Story 1.3` em vez de ficarem ausentes da tabela, preservando a garantia de "nenhuma classe sem destino" da Fase 0 do plano de origem.
- Validado que nenhuma linha da tabela usa pacote genérico `util`/`common`/`utils.utils`: classes antes soltas em `utils.utils` foram realocadas para a raiz do pacote do módulo destino (ex.: `DateUtils` → `br.com.sawcunhaos.foundation.core`) em vez de recriar um pacote-saco.
- Story puramente documental, conforme NFR4 e Dev Notes: nenhum arquivo Java foi movido ou alterado.

### File List

- `_bmad-output/implementation-artifacts/inventario-classe-modulo.md` (novo)

## Suggested Review Order

**O achado da revisão retroativa**

- Divergência real entre o inventário congelado e a implementação atual (`DateUtils`/`HashUtils`/`StringFieldUtils` em `core.utils`, não `core`).
  [`inventario-classe-modulo.md`](../../_bmad-output/implementation-artifacts/inventario-classe-modulo.md)
  [`core/src/main/java/br/com/sawcunhaos/foundation/core/utils/DateUtils.java`](../../core/src/main/java/br/com/sawcunhaos/foundation/core/utils/DateUtils.java)
