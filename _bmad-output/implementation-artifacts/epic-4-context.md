# Epic 4 Context: Skills finas e roteamento para o CLI

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

O agente passa a usar o CLI `scos-map-query` por padrão: a skill `scos-query` traz a tabela única de roteamento (13 linhas), `scos-map` vira ponteiro curto, `AGENTS.md` e `scos-map-build` apontam para ela, e nenhuma regra do `SKILL.md` antigo (218 linhas / 10,6KB) se perde. Fecha o MVP: o custo de contexto cai e as regras de alto risco continuam entregues ao agente.

## Stories

- Story 4.1: `--help` geral e `--help confianca`
- Story 4.2: Skill `scos-query` com a tabela única de roteamento
- Story 4.3: `scos-map` como ponteiro e teste de destino das regras
- Story 4.4: Referências em `AGENTS.md` e `scos-map-build`, e métrica de sessão

## Requirements & Constraints

- Limites com teste de contagem, para `.claude/skills/scos-query/SKILL.md` e `.claude/skills/scos-map/SKILL.md`: descrição ≤ 300 caracteres; corpo (sem frontmatter) ≤ 30 linhas e ≤ 2.000 caracteres. `--help` de cada subcomando ≤ 1.500 B; `--help confianca` ≤ 2.500 B.
- `scos-query` contém só: regra de chamar o CLI direto, comando literal (`python3 ferramentas/scos-map/scos-map-query.py <subcomando> ...`), tabela de roteamento, aviso de `--all` e uma linha para perguntas abertas (ler `index.json`, `_reactor.json` e o `layout.json` dos maiores módulos). Formato, exemplos e legenda de confiança ficam em `--help`, não na skill.
- A tabela traz o aviso do tamanho dos fatos grandes (ex.: `config.json` ≈ 142KB) e o fallback `grep`/`awk` para TSV, nunca `Read` do TSV inteiro; `Read` de fato bruto só como último recurso e só para JSON.
- `--help confianca` cobre `confianca`, `estado` (incluindo `desconhecido`), `completude`, `desvios`, `base` e `nao_aplicavel` como resultado legítimo.
- `scos-map` aponta para `scos-query` e cita `status` do `scos-map.py`.
- `AGENTS.md`: a tabela de roteamento sai, entra uma linha apontando para `scos-query`, sem outras mudanças. `scos-map-build`: só a referência na descrição muda (passa a apontar `scos-query` como skill de leitura).
- SM-C2 (métrica de sessão): sessão de Q1, Q5, Q6, Q7 e Q9 (skill carregada uma vez, `--help` usados, todas as saídas) ≤ 10% do total da mesma sessão via `Read`, contando as 10,6KB do `SKILL.md` antigo no lado do `Read`. Total contra `grep` só registrado, sem meta.
- SM-2 (pós-adoção, não executável no Epic): toda linha da tabela tem subcomando (checagem estática) e, em 20 perguntas de navegação em 5 sessões, verificadas por quem revisa (não por quem implementou), >= 90% respondidas sem `Read` de fato bruto; linha de base contada retroativamente nas 5 sessões anteriores. A story 4.4 só documenta o procedimento.

## Technical Decisions

- AD-8: `PERGUNTA` de cada módulo de `comandos/` é a única fonte do roteamento. O registro é a lista dos módulos de `comandos/` (menos `_*.py`), sem dispatch escrito à mão, e alimenta o `--help` geral (13 subcomandos, `arestas` separada de `bytecode`). A tabela de 13 linhas vive só em `scos-query`; teste exige exatamente os `NOME` e `PERGUNTA` do registro (divergência falha a suíte). Linha sem subcomando só vale como exceção motivada na própria tabela; fato novo sem subcomando entra como exceção.
- Inventário do `SKILL.md` antigo (addendum): cada seção tem destino (CLI, `--help`, `scos-query`, `scos-map-build` ou descartada com motivo). Destinos principais: Passo 0 (comando, `status`, não ler todos os fatos) -> `scos-query` + ponteiro `scos-map`; Contrato `schema_versao 2.1` -> checagem do CLI; envelope -> cabeçalho/`# limitacao:`/`--help confianca`; roteamento -> tabela única; TSV/`awk` e `deps.tsv` incompleto -> `--help` por subcomando, `deps` une `deps.tsv` + `_transitivas_comuns.tsv` e rodapé lista fontes; Regra 1 obsoleto -> envelope; Regra 2 `metodos_sem_chamador` != código morto -> `callgraph --sem-chamador` + `--help callgraph`; Regra 3 `nao_aplicavel` legítimo -> envelope + `--help confianca`; Regra 4 doc antiga ao lado de código recente -> `# aviso:` de `docs`; Regra 5 histórico de arquivo ausente -> `# aviso:` de `arquivos`; Regra 6 `bytecode_edges.tsv` vazio -> rodapé `motivo_vazio` em `arestas`; quatro baldes de `bytecode.json` -> `bytecode`; testes (três coisas que nunca se afirma) -> `tests` com `[heuristica]`; documentação (subtipos, frontmatter literal) -> `docs`; fato cruzado do workspace -> `--help conflitos`; SNAPSHOT local vs fonte (`jar_atual` != "contém o último commit") -> `--help snapshots`; perguntas abertas -> uma linha em `scos-query`.
- Testes exigidos: (a) inventário cobre todas as seções do `SKILL.md` antigo e cada regra de "Regras que evitam conclusão errada" tem destino; (b) cada `--help` de `docs`, `arquivos`, `deps`, `conflitos`, `snapshots`, `tests`, `bytecode`, `callgraph` cobre as regras que o inventário lhe atribui; (c) tamanhos acima.
- Regras de alto risco (evitam concluir "não usa X", "está testada", "está obsoleto"): constar só no `--help` não basta; devem aparecer na saída do subcomando (`# aviso:` ou `# limitacao:`) ou em uma das duas skills. Em especial: `deps` sem uso != "não usa X" (transitivas, bytecode vazio com `motivo_vazio`), `tests` nunca "X está testada", fato `obsoleto` sinalizado no envelope, `callgraph` ausência de aresta != ausência de chamada.
- `scos-map-build` e `scos-map.py` (geração) permanecem inalterados; o CLI não escreve em `.scos-map/`.

## Cross-Story Dependencies

- Depende dos Epics 1 a 3: os 13 subcomandos precisam estar no registro, com `PERGUNTA`, `AJUDA` e `# aviso:`/`# limitacao:` prontos (o teste de destino da 4.3 e a tabela da 4.2 leem esse registro). O Epic só fecha com todos presentes.
- 4.1 antes de 4.2 e 4.3: as skills assumem `--help` geral e `--help confianca`; o teste de inventário da 4.3 referencia os `--help` da 4.1.
- 4.2 e 4.3 são acopladas (o conteúdo removido de `scos-map` precisa ter destino em `scos-query` ou no CLI); 4.4 vem por último, pois a métrica SM-C2 mede skill, `--help` e saídas finais.
