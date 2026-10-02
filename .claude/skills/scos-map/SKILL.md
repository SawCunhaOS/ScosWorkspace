---
name: scos-map
description: Ponteiro para a consulta da estrutura dos repos SCOS (.scos-map/). Para responder perguntas use a skill scos-query (CLI); para gerar ou regenerar o mapa use scos-map-build. O status do mapa vem de scos-map.py status.
---

# scos-map (ponteiro)

O mapa em `.scos-map/` e um indice, nao um substituto do codigo.

- **Perguntas** (layout, config, deps, versoes, testes, bytecode, callgraph): skill `scos-query`.
- **Gerar/regenerar**: skill `scos-map-build`.
- **Existe mapa? Ha fato obsoleto?** `python3 ferramentas/scos-map/scos-map.py status .`

Se `status` acusar mapa ausente ou fato obsoleto, avise o usuario ou peca a regeneracao antes de responder.
Se o `schema_versao` do indice nao for o testado pelo CLI, reporte a divergencia e pare.
Legenda de `confianca`/`estado`: `scos-map-query.py --help confianca`.
