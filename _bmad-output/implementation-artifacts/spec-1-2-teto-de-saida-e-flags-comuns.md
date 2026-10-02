---
title: 'Story 1.2: Teto de saída e flags comuns'
type: 'feature'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-scos-map-query-2026-10-02/ARCHITECTURE-SPINE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** qualquer consulta pode devolver centenas de linhas e consumir o contexto do agente; não há como pedir mais ou menos de forma explícita.

**Approach:** `cli.py` registra `--limit N`, `--bytes N`, `--all`, `--base` em todo subparser e entrega `Opcoes` ao `render.py`, que aplica o teto (AD-6, AD-11). O comando não declara nem vê essas flags. Estende `layout` só por herança (nenhuma mudança no comando).

- Teto padrão: 50 linhas e 6.000 B (UTF-8, contando `\n`) de dados, **global**, consumido na ordem das seções `dados`, sem reordenar; cabeçalho, limitação, títulos e rodapé não contam.
- Seção cortada continua visível (`## areas (0 de 40)`); com corte, linha `# truncado: use <flag>` antes do rodapé — flag de `Resultado.refinar` ou, se vazia, `--limit`/`--bytes` calculado para caber tudo, nunca `--all` primeiro; rodapé `n de M` conta as linhas mostradas.
- Linha > 240 caracteres (após `tsv_clean`) vira 240 com `…`, preservando a coluna `marca` quando for a última; `--all` não desliga isso.
- `--limit`/`--bytes` sobrescrevem o respectivo teto (inteiro ≥ 1); `--all` remove os dois; `--all` com `--limit` ou `--bytes` → código 2.
- `--base` acrescenta `# base: <Meta.base>` ao envelope de cada fato que tem `base`.
- Seção `resumo` sai inteira (até 20 linhas), fora do teto e de `n`/`M`.
- Goldens cobrem corte por linhas, por bytes, linha longa e `--base`; teste varre que nenhuma saída sem `--all` excede os tetos.

</frozen-after-approval>

## Implementation Notes

- Implementado direto em `render.py` (`_linha`, `_cortar`, `_refinar`, `montar`), `cli.py` (flags comuns, `--all` x `--limit/--bytes` → 2) e `modelo.py` (`Opcoes`, constantes). `layout` não mudou. Suíte: 129 testes OK; golden `layout_truncado.txt`.

## Review Triage Log

- low (rejeitado): `_linha` com `marca` ≥ 239 chars ou coluna única — nenhum comando tem `marca` ainda; revisitar com o primeiro que tiver.
- low (rejeitado): `Opcoes(limit=0)` direto cai no padrão — o CLI rejeita 0.
- low (rejeitado): `_refinar` recalcula linhas; sem impacto de custo mensurável.
- low (rejeitado): colisão de flag de comando com flag comum — nenhum comando declara; falharia alto.
- medium (corrigido): faltava teste de teto consumido entre seções e contagem em bytes UTF-8 — adicionado.
- medium (deferido): `--help` por comando não lista as flags comuns (`AJUDA` é literal) — ver deferred-work.md.
