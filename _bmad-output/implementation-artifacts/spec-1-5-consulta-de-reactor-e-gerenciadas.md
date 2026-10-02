---
title: 'Story 1.5: Consulta de reactor e gerenciadas'
type: 'feature'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
followup_review_recommended: false
---

# Story 1.5: Consulta de reactor e gerenciadas

Intent: ver Story 1.5 em `../planning-artifacts/epics.md`.

## Implementation Notes

`comandos/reactor.py` (+ `--id` para Q6), `comandos/gerenciadas.py`, `filtros.py`, `Mapa.reactor/gerenciadas/_tabela` (TSV por nome de coluna, AD-3), goldens e testes. Smoke no mapa real OK.

## Review Triage Log

### 2026-10-02 — Review pass única (1.5–1.8, 3 camadas)
- patch: `comuns` de `deps --todos-modulos` sobrescrito a cada módulo; BrokenPipe com `dup2`; módulo vazio após normalizar → exit 2; projeto normalizado no log; Q3 filtrava a linha inteira; testes de limitação duplicada, deps indisponível, pipe fechado, latência.
- false: `deps` indisponível devia dar erro 3 — AD-12 manda resultado normal com `motivo`; `fecho_comum_arquivo` como caminho — não resolve no mapa real (verificado).
- defer: `reactor --id` só casa `de`; `arquivos` valor de filtro sem correspondência não avisa; colunas ausentes em `_tabela`; teto de 1.500 B de `# fontes:`; mediana SM-1.
- reject: ordenar `arquivos` por commits, caminhos fora de `.scos-map/`, acoplamento a `lidos[-1]`, estilo.

## Auto Run Result

Verificação: `python3 -m unittest discover -s tests -t tests` → 171 testes OK. Sem commit (política: commit por epic).
