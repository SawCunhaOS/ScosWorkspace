# Sprint Change Proposal — Adequação dos artefatos BMAD ao workspace SCOS

- **Data:** 2026-09-11
- **Solicitante:** SawCunhaOS (via `bmad-correct-course`)
- **Modo:** Batch
- **Escopo:** Minor — sem mudança de regra de negócio, PRD, arquitetura, épicos ou acceptance criteria.

> Este documento cita de propósito os caminhos **antigos** (`_bmad-output/planning-artifacts/...`) nos blocos OLD — ele fica fora do sed da edição A2.

> **Status:** aprovada em 2026-09-11, com uma revisão do solicitante — *o workspace é quem tem a instalação e os artefatos BMAD (subpasta por projeto permitida); os repos de produto não podem ter artefatos BMAD*. A revisão trocou D1 (tirar o BMAD dos `AGENTS.md` em vez de editar o bloco gerenciado) e acrescentou D3/D4. Aprovados: A1–A4, A3-H, B1–B5, C1–C2, D1–D4. Não aprovado: E1.

---

## 1. Resumo do problema

Em 2026-09-09 a instalação BMAD e os artefatos saíram de dentro de cada repositório e foram para o workspace `SCOS/` (repo `SawCunhaOS/ScosWorkspace`), para que os agentes enxerguem os três repos do ecossistema lado a lado:

- **Foundation** `ec2a66c` removeu `_bmad/`, `.claude/` e `_bmad-output/` (87 arquivos). Os 87 chegaram **idênticos** (mesma lista de arquivos) em `SCOS/_bmad-output/`.
- **Flow** `e56929b` removeu `_bmad/`, `.claude/` e `_bmad-output/` (39 arquivos: PRD/Architecture/epics da Organization, 23 stories, sprint-status, project-context). **Decisão (2026-09-11):** esses artefatos ficam só no histórico git do Flow.
- O workspace passou a ter `project_name: SawCunhaOS-Workspace` e `{project-root}` = `SCOS/`.

O conteúdo dos artefatos ainda assume o layout antigo (`{project-root}` = `SawCunhaOS-Foundation/`), e o workspace não tem convenção para mais de um projeto em `_bmad-output/`.

### Evidências

| # | Onde | Problema |
|---|---|---|
| E1 | `implementation-artifacts/sprint-status.yaml:36-37` | `story_location` absoluto aponta para `SawCunhaOS-Foundation/_bmad-output/implementation-artifacts`, que não existe mais |
| E2 | `SawCunhaOS-Foundation/AGENTS.md:18` | Aponta para `_bmad-output/planning-artifacts/` dentro da Foundation — não existe mais |
| E3 | `SawCunhaOS-Flow/README.md:40,84` | Aponta para `_bmad-output/` dentro do Flow — removido em `e56929b` |
| E4 | stories e `epics.md` | Caminhos de código (`web/src/...`, `pom.xml`, `mvn -pl <módulo>`) são relativos à raiz da Foundation, sem nada no workspace dizendo isso |
| E5 | `_bmad/{bmm,tea,core,render}/config.yaml` e `_bmad/config.toml` | `_bmad-output/` plano: não comporta um segundo projeto sem colisão de `epics.md`/`sprint-status.yaml` |
| E6 | 39 stories done/review | ~260 links `](../../<módulo>/...)` relativos à posição antiga do arquivo não resolvem mais no clique |

### Achados paralelos (não estruturais)

| # | Onde | Problema |
|---|---|---|
| H1 | `sprint-status.yaml:78-79` | 3-8 tem valor inválido `'review ready-for-dev'` (quebra de linha no YAML); o arquivo da story diz `Status: done` |
| H2 | `sprint-status.yaml` | 3-18 (`done`), 3-19 (`done`) e 3-20 (`ready-for-dev`) têm arquivo em `implementation-artifacts/` mas não estão no yaml — o dev-story não enxerga a 3-20 |
| H3 | `epics.md` | Também não tem as Stories 3.18–3.20 — é conteúdo, fica como follow-up fora desta proposta |

---

## 2. Análise de impacto

### Checklist

| Item | Status | Nota |
|---|---|---|
| 1.1 Story gatilho | [x] | Nenhuma — o gatilho é a reestruturação do workspace (`ec2a66c`, `e56929b`, `cd6cda6`/`1fb2c30`/`d676db7`) |
| 1.2 Problema | [x] | Restrição técnica de ferramental — realocação, não requisito |
| 1.3 Evidências | [x] | E1–E6 |
| 2.1–2.5 Épicos | [N/A] | Nenhum épico muda escopo, AC, ordem ou prioridade |
| 3.1 PRD | [N/A] | Sem conflito |
| 3.2 Architecture | [N/A] | Sem conflito — o spine descreve código, não onde ficam os artefatos |
| 3.3 UX | [N/A] | Não há documento de UX (biblioteca) |
| 3.4 Outros artefatos | [!] | Config BMAD, sprint-status, epics.md, CLAUDE.md/README do workspace, AGENTS.md da Foundation, README do Flow |
| 4.1 Ajuste direto | Viável | Esforço baixo, risco baixo |
| 4.2 Rollback | Não viável | Seria devolver o BMAD para cada repo — o oposto do objetivo |
| 4.3 Revisão de MVP | [N/A] | — |
| 4.4 Caminho | [x] | Opção 1 — Ajuste direto |

### Impacto

- **Épicos/Stories:** nenhum impacto de conteúdo. Stories `ready-for-dev` (3-16, 3-17, 3-20, 4-1…4-16) ganham a convenção de caminho explícita.
- **PRD / Architecture / UX / SPEC:** sem conflito.
- **Técnico:** caminhos do config BMAD — 35 skills leem `bmm/config.yaml`, 18 leem `tea/config.yaml`, 4 leem `core/config.yaml`, 6 usam `resolve_config.py` (camadas TOML). Nenhum código de produto muda. O `scos-map` casa `_bmad-output` por segmento de caminho (`BMAD_DIR_RE`) e continua classificando os docs.

---

## 3. Abordagem recomendada

**Ajuste direto**, com as decisões de 2026-09-11:

1. **Subpasta por projeto** — `_bmad-output/<projeto>/` (hoje só `SawCunhaOS-Foundation/`); o config BMAD aponta para o projeto ativo.
2. **Artefatos do Flow só no histórico** — os READMEs apontam para `e56929b^`.
3. **Nota de convenção** em vez de reescrever caminhos de código — stories done/review ficam intactas (registro histórico).

**Esforço:** baixo (mecânico). **Risco:** baixo — refs internas reescritas por sed idempotente e verificadas automaticamente (todo caminho citado precisa existir). **Cronograma:** sem impacto.

### Limites conhecidos

- **L1** — Reinstalar o BMAD regrava `_bmad/*/config.yaml` com as respostas do instalador: responda com os caminhos por projeto ou reaplique B1–B4. O `_bmad/custom/config.toml` (B5) sobrevive à reinstalação, mas só vale para os skills que usam `resolve_config.py`.
- **L2** — O glob `{project-root}/**/project-context.md` dos workflows carrega o `project-context.md` de **todos** os projetos: se um projeto ganhar o seu, ele vaza para os demais. Hoje nenhum tem.
- **L3** — Links de E6 continuam quebrados no clique (decisão: não reescrever histórico); a nota de convenção diz como ler.
- **L4** — Trocar de projeto ativo = editar `output_folder` / `*_artifacts` em B1–B5.

---

## 4. Propostas de edição

### A. Artefatos (repo ScosWorkspace)

**A1 — Mover para a subpasta do projeto**

```bash
mkdir -p _bmad-output/SawCunhaOS-Foundation
git mv _bmad-output/planning-artifacts _bmad-output/implementation-artifacts \
       _bmad-output/specs _bmad-output/test-artifacts _bmad-output/SawCunhaOS-Foundation/
```

87 arquivos rastreados, histórico preservado. Links `../../planning-artifacts/...` do `SPEC.md` continuam válidos (a subárvore move junto).

**A2 — Reescrever refs internas** (271 ocorrências em 71 arquivos; idempotente)

```
OLD: _bmad-output/(planning-artifacts|implementation-artifacts|specs|test-artifacts)
NEW: _bmad-output/SawCunhaOS-Foundation/\1
```

Cobre também `{project-root}/_bmad-output/...` (frontmatter de 3-18/3-19), `inputDocuments` do `epics.md`, `.memlog.md` e os `ref:` do sprint-status. **Este documento fica fora do sed.**

**A3 — `implementation-artifacts/sprint-status.yaml`**

Metadados:

```yaml
# OLD
last_updated: 09-08-2026
...
story_location: 
  /home/sawcunha/Projetos/SCOS/SawCunhaOS-Foundation/_bmad-output/implementation-artifacts

# NEW
last_updated: 09-11-2026
...
story_location: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts
```

Nota acrescentada ao fim de `# WORKFLOW NOTES`:

```yaml
# WORKSPACE (desde 2026-09-09 — ver planning-artifacts/sprint-change-proposal-2026-09-11.md):
# - Estes artefatos moram no repo ScosWorkspace (SCOS/_bmad-output/SawCunhaOS-Foundation/),
#   fora do repo da Foundation.
# - Caminhos de código citados nas stories (web/src/..., pom.xml, mvn -pl <módulo>) são
#   relativos a SCOS/SawCunhaOS-Foundation/; comandos mvn rodam de dentro desse diretório.
# - Links ](../../<módulo>/...) de stories anteriores a 2026-09-09 usam o layout antigo e
#   não resolvem no clique; leia como SawCunhaOS-Foundation/<módulo>/...
```

Rationale: E1 e E4. Formato relativo, igual aos `ref:` do próprio arquivo — sem `/home/...` fixo. `story_location` é informativo (validado pelo sprint-status); o dev-story usa `{implementation_artifacts}` e lê o yaml inteiro, então vê a nota.

**A3-H (opcional — achados H1/H2)**

```yaml
# OLD
  3-8-tornar-a-política-de-falha-por-exceção-de-negócio-declarável: review
    ready-for-dev
...
  3-17-substituir-construtores-telescópicos-por-builder-e-documenta: 
    ready-for-dev
  epic-3-retrospective: optional

# NEW
  3-8-tornar-a-política-de-falha-por-exceção-de-negócio-declarável: done
...
  3-17-substituir-construtores-telescópicos-por-builder-e-documenta: ready-for-dev
  3-18-qualidade-de-teste-do-jdempotent-redis: done
  3-19-topologia-redis-parametrizada-concorrencia-e-throughput: done
  3-20-corrigir-heranca-do-jdempotentid-e-ampliar-cobertura-de-anotacoes: ready-for-dev
  epic-3-retrospective: optional
```

Status tirados do próprio arquivo de cada story. A 3-17 só perde a quebra de linha (mesmo valor).

**A4 — `planning-artifacts/epics.md`** — nota logo após o parágrafo de Overview:

```markdown
> **Localização (workspace SCOS, desde 2026-09-09):** este documento e as stories vivem em
> `SCOS/_bmad-output/SawCunhaOS-Foundation/` (repo `ScosWorkspace`), não mais no repo da
> Foundation. Caminhos de código citados aqui e nas stories são relativos a
> `SawCunhaOS-Foundation/`; comandos `mvn` rodam de dentro desse diretório.
```

Rationale: E4 — fica no caminho de quem gera (create-story) e implementa as próximas stories.

### B. Config BMAD (repo ScosWorkspace)

Em todos: `_bmad-output` → `_bmad-output/SawCunhaOS-Foundation`.

| # | Arquivo | Chaves |
|---|---|---|
| B1 | `_bmad/bmm/config.yaml` | `planning_artifacts`, `implementation_artifacts`, `output_folder` |
| B2 | `_bmad/tea/config.yaml` | `test_artifacts`, `test_design_output`, `test_review_output`, `trace_output`, `output_folder` |
| B3 | `_bmad/core/config.yaml` | `output_folder` |
| B4 | `_bmad/render/config.yaml` | `output_folder` (gitignored — só consistência local) |
| B5 | `_bmad/custom/config.toml` | bloco abaixo (camada 3 do `resolve_config.py`, versionada, nunca tocada pelo instalador) |

```toml
# Projeto BMAD ativo no workspace SCOS: SawCunhaOS-Foundation.
# Trocar de projeto = editar este bloco + _bmad/{bmm,tea,core}/config.yaml.
[core]
output_folder = "{project-root}/_bmad-output/SawCunhaOS-Foundation"

[modules.bmm]
planning_artifacts = "{project-root}/_bmad-output/SawCunhaOS-Foundation/planning-artifacts"
implementation_artifacts = "{project-root}/_bmad-output/SawCunhaOS-Foundation/implementation-artifacts"

[modules.tea]
test_artifacts = "{project-root}/_bmad-output/SawCunhaOS-Foundation/test-artifacts"
test_design_output = "_bmad-output/SawCunhaOS-Foundation/test-artifacts/test-design"
test_review_output = "_bmad-output/SawCunhaOS-Foundation/test-artifacts/test-reviews"
trace_output = "_bmad-output/SawCunhaOS-Foundation/test-artifacts/traceability"
```

`_bmad/config.toml` **não** é tocado (installer-owned; `custom/` tem precedência). Rationale: E5.

### C. Docs do workspace (repo ScosWorkspace)

**C1 — `CLAUDE.md`**, após o parágrafo "Ordem de dependência de build" (o arquivo já tem mudanças não commitadas; o bloco só acrescenta):

```markdown
**Artefatos BMAD**: uma subpasta por projeto em `_bmad-output/<projeto>/` (hoje só
`SawCunhaOS-Foundation/`). O projeto ativo é definido pelos caminhos em
`_bmad/{bmm,tea,core}/config.yaml` e `_bmad/custom/config.toml` — trocar de projeto é editar esses
caminhos; reinstalar o BMAD regrava os `*.yaml` (responda com os caminhos por projeto). Caminhos de
código citados nas stories são relativos à raiz do repo do projeto. Os artefatos BMAD antigos do Flow
(Organization) estão só no histórico dele: `git -C SawCunhaOS-Flow show e56929b^:_bmad-output/<arquivo>`.
```

**C2 — `README.md`**

- L37 (mermaid): `artefatos gerados: planning, specs,<br/>implementation, test` → `artefatos gerados, uma subpasta<br/>por projeto (hoje: SawCunhaOS-Foundation/)`
- L63 (tabela): `Artefatos gerados pelo BMAD ao longo do trabalho: planning-artifacts/, specs/, implementation-artifacts/, test-artifacts/` → `Artefatos gerados pelo BMAD, uma subpasta por projeto (<projeto>/planning-artifacts/, specs/, implementation-artifacts/, test-artifacts/) — hoje só SawCunhaOS-Foundation/`
- L91–94: acrescentar "organizada por projeto (`_bmad-output/<projeto>/`)" e "os artefatos antigos do Flow estão no histórico git dele (`e56929b^`)".

### D. Repos filhos (um commit por repo, só com autorização)

**D1 — `SawCunhaOS-Foundation/AGENTS.md:18`** (branch `release/1.2.0`)

```
OLD: - Especificação da release 1.2.0 (PRD, Architecture Spine, Epics/Stories): `_bmad-output/planning-artifacts/` — `prds/prd-SawCunhaOS-Foundation-2026-08-18/prd.md`, `architecture/architecture-SawCunhaOS-Foundation-2026-08-19/ARCHITECTURE-SPINE.md`, `epics.md`.
NEW: - Especificação da release 1.2.0 (PRD, Architecture Spine, Epics/Stories): fora deste repo, no workspace SCOS (repo `ScosWorkspace`), em `../_bmad-output/SawCunhaOS-Foundation/planning-artifacts/` — `prds/prd-SawCunhaOS-Foundation-2026-08-18/prd.md`, `architecture/architecture-SawCunhaOS-Foundation-2026-08-19/ARCHITECTURE-SPINE.md`, `epics.md`. Estado do sprint: `../_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/sprint-status.yaml`.
```

**Revisão:** os 5 `AGENTS.md` da Foundation (raiz, `archtest/`, `audit/`, `privacy/`, `web/`) eram 100% bloco `bmad:context` gerenciado pelo `bmad-project-context` — artefato BMAD dentro do repo. Decisão: manter o conteúdo (conhecimento do repo) e remover os marcadores `<!-- bmad:context -->`, `<!-- /bmad:context -->` e a linha "Managed by bmad-project-context"; viram doc comum do repo, mantido à mão. O `CLAUDE.md` do workspace deixa de citá-los como "fonte: bmad-project-context".

**D2 — `SawCunhaOS-Flow/README.md`** (branch `develop`)

```
OLD (L40): O projeto é conduzido pelo método **BMAD** (épicos/stories em `_bmad-output/`). Estado do sprint em `_bmad-output/implementation-artifacts/sprint-status.yaml`.
NEW (L40): O projeto é conduzido pelo método **BMAD**. A instalação BMAD mora no workspace SCOS (repo `ScosWorkspace`); os artefatos desta rodada de planejamento (PRD, Architecture, épicos/stories, sprint-status) foram arquivados e estão no histórico git deste repo — ex.: `git show e56929b^:_bmad-output/implementation-artifacts/sprint-status.yaml`.

OLD (L84): > Detalhe completo de cada épico/story (contexto, acceptance criteria, dev notes): `_bmad-output/planning-artifacts/epics.md` e `_bmad-output/implementation-artifacts/*.md`.
NEW (L84): > Detalhe completo de cada épico/story (contexto, acceptance criteria, dev notes): no histórico git — `git show e56929b^:_bmad-output/planning-artifacts/epics.md` e `git ls-tree -r --name-only e56929b^ -- _bmad-output/implementation-artifacts`.
```

**D3 — `SawCunhaOS-Flow/etc/architecture/etapa-1-diagramas.md:3`** (branch `develop`)

```
OLD: Companion visual de `_bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Organization-2026-07-18/ARCHITECTURE-SPINE.md`.
NEW: Companion visual do Architecture Spine da Organization (2026-07-18), arquivado no histórico git deste repo: `git show e56929b^:_bmad-output/planning-artifacts/architecture/architecture-SawCunhaOS-Organization-2026-07-18/ARCHITECTURE-SPINE.md`.
```

**D4 — Foundation `jdempotent/pom.xml:292` e `ScosJdempotentRedisConfigurationTest.java:89`** (branch `release/1.2.0`)

Comentário XML e javadoc citavam o spine 2026-08-29 pelo caminho antigo; passam a citar `_bmad-output/SawCunhaOS-Foundation/planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-29/` com "no workspace SCOS, fora deste repo". Só comentário — sem efeito no build. No teste, a referência ocupa 2 linhas para não exceder o comprimento da linha original (131 colunas).

### E. Limpeza local (opcional, fora do git) — não aprovado

**E1** — `rm -rf _bmad/render/bmad-build/`: cache renderizado do skill `bmad-build` (removido em `1fb2c30`), com caminhos absolutos do layout antigo; nenhum skill lê; gitignored. Não quebra nada ficar — só evita confusão.

---

## 5. Handoff de implementação

- **Classificação:** Minor — implementação direta pelo agente Dev, nesta sessão, após aprovação.
- **Ordem:** A1 → A2 → A3 (+A3-H) → A4 → B1–B5 → C1–C2 → D1–D2 → (E1) → verificação.
- **Commits:** nenhum sem autorização explícita. Quando autorizado, três commits separados:
  - ScosWorkspace/`develop` → `refactor(bmad): ...`
  - Foundation/`release/1.2.0` → `docs: ...`
  - Flow/`develop` → `docs: ...`
  - Nunca `git add -A` na raiz do workspace.
- **Pós-passo:** `python3 ferramentas/scos-map/scos-map.py status .` — o `workspace.json` cita 3 caminhos antigos `_bmad-output/planning-artifacts/...`; regenerar quando conveniente.

### Critérios de sucesso (verificação automática)

1. Zero refs na forma antiga `_bmad-output/(planning-artifacts|implementation-artifacts|specs|test-artifacts)` nos artefatos (fora deste documento).
2. Todo caminho `_bmad-output/SawCunhaOS-Foundation/...` citado nos artefatos existe em disco (ignorando `#âncora` e `:linha`).
3. `sprint-status.yaml` faz parse, todos os status são válidos, `story_location` existe e toda story listada tem arquivo.
4. `resolve_config.py --key core` / `--key modules` e os três `config.yaml` apontam para `_bmad-output/SawCunhaOS-Foundation/...`.
5. Nenhum artefato BMAD nos repos de produto: zero diretórios `_bmad*`/`.claude` e zero blocos `bmad:context`.

### Follow-ups fora do escopo

- **H3** — incluir as Stories 3.18–3.20 no `epics.md` (conteúdo → PO/SM).
- `README.md` do workspace L204–207 ainda cita `.claude/skills/scos-map/scos-map.py` (movido para `ferramentas/scos-map/` no refactor em andamento).
