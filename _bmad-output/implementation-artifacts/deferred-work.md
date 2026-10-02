- source_spec: `_bmad-output/implementation-artifacts/spec-1-2-teto-de-saida-e-flags-comuns.md`
  summary: Documentar `--limit/--bytes/--all/--base` no `--help` dos subcomandos.
  evidence: `--help` imprime só o `AJUDA` literal do comando; o agente não descobre as flags comuns nem a exclusão de `--all`.

## Deferred from: code review (2026-10-02, Epic 4 stories 4.1–4.4, sem spec)

- `AGENTS.md` (parágrafo de "Índice estrutural", ~l. 50–60) ainda descreve `scos-map` como a skill que "só consulta o mapa" e não cita `scos-query`. Fora do escopo da 4.4 ("sem outras mudanças de conteúdo"); atualizar com autorização explícita, pois é arquivo de contexto de agente.
