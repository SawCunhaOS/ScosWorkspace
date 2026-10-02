# Epic 3 Context: Consultas profundas de bytecode, testes e callgraph (Tier 2 e 3)

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

O agente consulta arestas de bytecode, testes, higiene de dependências e callgraph de um módulo com o CLI `scos-map-query`, recebendo poucas linhas e os avisos que impedem conclusões erradas (ex.: "X está testada", "módulo não tem dependências", "método sem chamador é código morto"). São os quatro subcomandos de escopo módulo dos Tiers 2 e 3, independentes entre si, sobre a infra entregue no Epic 1.

## Stories

- Story 3.1: Consulta `arestas`
- Story 3.2: Consulta `tests`
- Story 3.3: Consulta `bytecode`
- Story 3.4: Consulta `callgraph`

## Requirements & Constraints

- Todos têm `ESCOPO=modulo` (`<projeto> <módulo>`), respeitam o envelope de confiança e o teto de saída (50 linhas / 6.000 B; nenhuma invocação sem `--all` excede), e nunca geram fatos, compilam ou escrevem em `.scos-map/`.
- Cada subcomando entrega golden e `--help` (formato + exemplo real de 3–5 linhas) em `ferramentas/scos-map/tests/`; o formato só muda junto com golden e `--help`. `# aviso:` ≤ 100 bytes obrigatório em `tests`, `bytecode` e `callgraph`.
- `arestas`: filtros `--de/--para/--pacote` (classe ou prefixo), colunas `de, para, tipo, origem`; sem `bytecode_edges.tsv` → erro 3 indicando build `--tier 2/3` (nunca dispara geração); arquivo vazio → rodapé com `motivo_vazio` e `diagnostico`, deixando claro que vazio não prova ausência de dependências. Maior fato do mapa (≈958KB): ≤ 300 ms. Benchmark Q9 (17 linhas) e Q10 (107 casam, truncada com aviso) dentro de SM-1.
- `tests`: resumo (raízes, arquivos, tipos, frameworks com `origem` declarada/inferida, `cobertura` sempre com o `estado` do fato); `--arquivos` lê `tests.tsv` (`path, tipo, alvo_heuristico, linhas, commits_90d`), `--alvo <classe>` restringe. `alvo_heuristico` sempre com `[heuristica]`; pode-se afirmar "existe um teste chamado XTest", nunca "X está testada" (explicar no `--help`). Zero arquivos para `--alvo` → "nenhum arquivo de teste identificado nas raízes analisadas: <raízes>". Aviso: alvo é heurística, não prova cobertura. Q11: conferida em conteúdo; `grep` menor é tolerado e a razão registrada.
- `bytecode`: resumo por balde (`deps_usadas_ausentes_do_pom`, `deps_usadas_via_transitiva`, `deps_declaradas_sem_uso`, `deps_ignoradas_na_analise`), `frescor`, `transitivas_resolvidas`; `--balde <nome>` lista `artefato, referencias`. Só `deps_usadas_ausentes_do_pom` é risco imediato; `provavel_falso_positivo: true` → `[provavel_falso_positivo]`; `deps_ignoradas_na_analise` nunca como problema. `transitivas_resolvidas` falso → `# limitacao:` (divisão dos dois primeiros baldes não confiável). Balde ausente = "não calculado", nunca "0". `estado` considera `frescor` próprio (`compilado_em`): bytecode anterior a mudanças nas fontes → `obsoleto`. Q12: conteúdo + CLI/`Read` ≤ 10%.
- `callgraph`: fato não `disponivel` → cabeçalho + `motivo` + `comando_sugerido`, código 0, nunca vazio. Disponível → resumo (`arestas_total`, `arestas_ambiguas`, `entrypoints`); `--de/--para/--entrypoints` leem `callgraph_edges.tsv` (`de, para, invoke, certeza`); `--lacunas` lista `lacunas_conhecidas`; `--sem-chamador` lista `metodos_sem_chamador` com a marca de que não é lista de código morto (endpoints HTTP, `@Scheduled`, `@EventListener` não têm chamador no bytecode). Advertência do fato (proxies, reflexão, implementações geradas em runtime) sempre em `# limitacao:`. Aviso: ausência de aresta não prova ausência de chamada.

## Technical Decisions

- Mesmo contrato do Epic 1/2: módulo em `scos_map_query/comandos/` com `NOME`, `PERGUNTA`, `ESCOPO`, `FLAGS`, `AJUDA` (≤ 1.500 B), `EXEMPLO`, `consultar(args, mapa) -> Resultado`; função pura (sem E/S/`print`/ambiente; imports só da lista branca: `modelo`, `filtros`, `re`, `typing`, `dataclasses`, `collections`), registrando fatos em `mapa.lidos`; o registro cresce sozinho.
- O comando filtra/agrupa e preenche `total`, `marca`, `refinar`; o render calcula envelope, teto, `n/M`, `# truncado:`. Seção `resumo` sai inteira (≤ 20 linhas), fora do teto e de `n/M`; seções declaradas mesmo vazias; marca = última coluna, só quando a confiança da linha difere da do fato (`[heuristica]` de `tests` sempre).
- Só `fatos.py` conhece o formato dos fatos e calcula `estado` (disponibilidade > `frescor` do fato > frescor barato via `.git/HEAD`). Estados de leitura: `ausente` → erro 3; `indisponivel`/`nao_aplicavel` → resultado normal com `motivo` no envelope; células passam por `tsv_clean`; linhas truncadas em 240 caracteres.
- Fixture novo exigido em `fixtures.py`: callgraph disponível (colunas do gerador). Se inviável, a Story 3.4 entrega só o caso `indisponivel` com o motivo registrado.

## Cross-Story Dependencies

- Depende da infra do Epic 1 (`modelo`, `fatos`, `render`, `cli`, envelope, teto, log, `resolver`) e dos fixtures de estado lá criados.
- As quatro stories são independentes entre si; a 3.4 depende do fixture de callgraph (produzido nela mesma).
- Os quatro `PERGUNTA` alimentam a tabela de 13 linhas do Epic 4 (`arestas` separada de `bytecode`); o Epic 4 só fecha com todos no registro.
