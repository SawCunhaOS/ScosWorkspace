---
title: 'Story 1.4: Consulta de config e docs'
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

**Problem:** achar onde mora a configuração ou a documentação de um módulo exige abrir `config.json` (≈142KB) ou `docs.json` inteiros.

**Approach:** subcomandos `config <projeto> <módulo> [--prefixo]` (`path`, `bytes`; valores nunca aparecem) e `docs <projeto> <módulo> [--texto] [--prefixo]` (`path`, `título`, `subtipo`; `--texto` sem diferenciar maiúsculas em path ou título), com `# aviso:` ≤ 100 B em `docs`, `# limitacao:` pela `completude` parcial, `--help` com `EXEMPLO` de 3–5 linhas (e subtipos e regra de documento antigo em `docs`), sem resultado = cabeçalho + zero linhas + rodapé, filtro inválido = uma linha de erro.

</frozen-after-approval>

## Implementation Notes

- Novos: `comandos/config.py`, `comandos/docs.py`; `Mapa.config`/`Mapa.docs` em `fatos.py`; fixtures `CONFIG_APP`/`DOCS_APP`; goldens `config.txt`/`docs.txt`. Suíte: 144 testes OK; smoke no mapa real (`flow-organization-boot` tem `config`, não tem `docs` → erro 3 por AD-12).
- `total` da seção = linhas que casam com o filtro (AD-2), então com `--prefixo`/`--texto` o cabeçalho mostra `(m de m)`.

## Review Triage Log

- medium (corrigido): `EXEMPLO` mostrava `(2 de 3)`/`(2 de 4)`, incompatível com AD-2 — exemplos ajustados.
- medium (corrigido): `--texto "-"` casava o placeholder de título ausente — filtro agora usa o título cru.
- low (corrigido): cópia inútil da lista em `config.py`.
- false: TSV quebrado por tab/newline no título — `render.montar` aplica `tsv_clean` a toda célula.
- false: regra de documento antigo sem dados — AC pede só que o `--help` a explique.
- low (rejeitado): `fonte=mapa.lidos[-1]` frágil, subtipos copiados à mão, testes extras de caminhos de falha e `completude` em `config`, prefixo sensível a caixa e relativo à raiz do repo — sem caso real hoje.
