# Suite do scos-map

```bash
cd scos-map/
python3 -m unittest discover -s tests -t tests          # tudo
python3 -m unittest discover -s tests -t tests -v       # verboso
python3 -m unittest tests.test_scos_map.TestBomImport -t tests   # um caso
```

Sem rede, sem Maven, sem pip. Cada fixture e uma arvore sintetica criada num
diretorio temporario e destruida no fim.

## O que cada fixture sustenta

| fixture | caso que ela trava |
|---|---|
| `maven_simples` | contrato do schema 2.0: compacto, sem campo vazio, sha 12, `gerado_em` so no indice, segundo scan nao reescreve |
| `maven_multimodulo` | reator, arestas internas, conflito de versao entre modulos |
| `maven_bom_import` | BOM importado + property sobrescrita por profile: `parse_pom` erra, `effective-pom` corrige, conflito vira desvio |
| `maven_parent_property` | property herdada do parent resolvida na versao declarada |
| `yaml_complexo` | ancora/merge key: sem PyYAML a confianca cai para `media` com limitacoes; com PyYAML sobe para `alta` |
| `properties_simples` | chaves e placeholders sem nenhum valor |
| `npm_workspaces` | delta declarado (`^19.1.0`) x lockfile (`19.1.4`) |
| `tsv_campo_com_tab` | tab e quebra de linha em nome de arquivo nao deslocam coluna |
| `testes_multiplas_raizes` | fato `tests`: tipos, frameworks com procedencia, ArchUnit, ausencia redigida corretamente |
| `fecho_transitivo` | fecho comum gravado uma vez; lib divergente volta para o modulo |
| `workspace_3_projetos` | mapa por projeto, conflito cruzado, `derivado_de`, `--only` preservando os demais |
| `workspace_profundo` | `--max-depth`: poda reportada mesmo quando nada e encontrado |
| `bytecode_sem_aresta` | TSV vazio precisa trazer `motivo_vazio` e `amostra_saida` (usa um `jdeps` falso no PATH) |
| `dep_usada_ausente_do_pom` | lib no bytecode que nao esta declarada nem resolvida |
| `docs_subtipos` | classificacao de doc por caminho e por titulo, frontmatter do BMAD, documento fora de convencao |
| `snapshot_local` | jar do `~/.m2` atras do fonte ao lado; os tres estados |
| `dep_com_sufixo_numerico` | artifactId terminado em numero (`-71`) nao vira dep ausente do pom |
| `agregador_com_arvore_de_filho` | agregador nao herda a arvore do ultimo filho (cache de `dependency:tree` sem `-N`) |
| `workspace_modulos_aninhados` | modulo em `facts/<a>/<b>/` entra no cruzado, nos snapshots e no frescor |
| `dep_so_em_anotacao` | classe citada so em anotacao conta como uso; sem o jar no `~/.m2`, nada se afirma |
| `modulos_sem_codigo` | modulo so de resources e `nao_aplicavel`; so de `.proto` nao |
| `workspace_scope_e_bom` | divergencia so em scope test fica fora do cruzado; versao da BOM entra como `(gerenciada)` |

O `TestIncremental` cobre o reuso de fato cujas fontes nao mudaram, e trava
a regra de que `deps` nunca e reaproveitado (o envelope em disco ja teve as
listas movidas para o TSV).

## Testes que pulam sozinhos

`TestFrescorBytecode` exige `javac`; os de workspace exigem `git`. Sem a
ferramenta, o caso e marcado como skip em vez de falhar.

## Bugs que a suite ja pegou

- `transitivas_confiaveis` exigia `transitivas_total > 0`, entao modulo sem
  transitiva nunca teria dependencia ausente detectada - ter zero transitivas
  e um fato, nao falta de dado.
- `tsv_clean` removia `\r` em vez de trocar por espaco, colando palavras
  (`"c\rd"` -> `"cd"`): corrupcao silenciosa de dado.
- Ao construir a suite, a validacao de vocabulario de `confianca` revelou dez
  chamadas passando `"ausente"` como confianca - que e `estado`, dimensao
  separada.

## Ao adicionar um caso

Se a mudanca cria campo novo no JSON, o teste deve verificar **como o campo se
comporta quando o dado nao existe**, nao so quando existe. A maioria dos erros
deste projeto foi afirmar demais na ausencia de dado, nao na presenca.
