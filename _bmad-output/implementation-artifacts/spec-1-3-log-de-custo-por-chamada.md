---
title: 'Story 1.3: Log de custo por chamada'
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

**Problem:** não há como verificar, ao longo do tempo, a economia prometida pelo CLI.

**Approach:** `render.emitir(texto, log)` escreve stdout e acrescenta um registro TSV `ts_utc, subcomando, projeto, modulo, bytes_stdout_utf8, linhas_stdout, codigo, schema_versao` (`-` para o desconhecido) a `.scos-map-query.log` na raiz do workspace (ou `SCOS_MAP_QUERY_LOG`), em um único `write` em modo append (AD-9). Todo caminho de `main` passa por `emitir` (inclui códigos 1 e 2); sem `workspace.json` não grava; falha de gravação nunca afeta a resposta; `/.scos-map-query.log` entra no `.gitignore` da raiz; só `cli.py`/`render.py` leem `os.environ`.

</frozen-after-approval>

## Implementation Notes

- `cli.py`: `_executar` preenche `ctx` (raiz, subcomando, projeto, módulo); `_log` monta o destino. `render.py`: `_registrar` (um `os.write` com `O_APPEND`, qualquer exceção engolida). Suíte: 136 testes OK.

## Review Triage Log

- medium (corrigido): `_registrar` só capturava `OSError`; erro de encode escapava após o stdout — agora tudo dentro do `try`, com teste.
- low (rejeitado): `BrokenPipe` em stdout pula o log; `os.write` curto; `SCOS_MAP_QUERY_LOG` relativo/`~`; duração/pid/flags no registro; rotação do log; aviso de log morto; `_log` fora de guarda — fora do escopo das ACs, sem caso real alcançável.
- low (rejeitado): testes extras (`workspace.json` malformado, `--help`, concorrência) — comportamento coberto por construção; revisitar se o log virar fonte de métrica na 1.8.
