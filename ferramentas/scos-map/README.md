# scos-map

Indice estrutural dos repositorios SCOS para consumo por IA.
Um indice, nao um substituto do codigo: diz onde achar, com que confianca e
quao fresco esta cada fato.

## Layout sugerido

```
<workspace>/
  .claude/
    skills/
      scos-map/SKILL.md          consulta  (caminho quente)
      scos-map-build/SKILL.md    geracao e manutencao
  ferramentas/scos-map/
    scos-map.py
    tests/
      fixtures.py
      test_scos_map.py
      README.md
```

Duas skills de proposito: consultar o mapa acontece em quase toda conversa;
gerar acontece raramente. Misturar as duas faz a instrucao de geracao
competir por atencao com a de leitura, no caminho onde ela nunca e usada.

## Instalar

```bash
mkdir -p .claude/skills ferramentas
cp -r skills/scos-map skills/scos-map-build .claude/skills/
cp -r scos-map.py tests ferramentas/scos-map/
echo ".scos-map/" >> .gitignore     # ou versione, se quiser revisar em PR
```

Se o `.gitignore` de algum repo ainda tiver `.aimap/`, troque por
`.scos-map/`.

### Versionar o mapa ou nao

Versionar deixa o mapa revisavel em PR e mostra em diff quando a estrutura
muda - o formato foi desenhado para isso (JSON compacto, sem carimbo de tempo
em fato, fato inalterado nao e reescrito). Ignorar evita ruido em repo com
muitos colaboradores. Os dois funcionam; escolha um e seja consistente.

## Trecho para o CLAUDE.md da raiz

```markdown
## Estrutura do codigo

Antes de procurar arquivo por nome ou abrir varios modulos para entender a
organizacao, consulte o mapa com a skill `scos-map`. Ele responde onde ficam
arquivos, configs, dependencias e versoes sem carregar o codigo.

Se o mapa nao existir ou o `status` acusar fatos obsoletos, gere com a skill
`scos-map-build`.

Ao consumir o mapa, respeite a `confianca` e a `completude` de cada fato:
`declarada` nao e `resolvida`, `parcial` nao e `total`, e fato sem
`confianca` e fato sem dado.
```

## Verificar a instalacao

```bash
cd ferramentas/scos-map && python3 -m unittest discover -s tests -t tests
cd <workspace> && python3 ferramentas/scos-map/scos-map.py workspace .
```

O primeiro `workspace` imprime um plano com o que falta no ambiente
(PyYAML, mvn, JDK) antes de gastar tempo. Nada e obrigatorio: o que faltar
degrada o fato correspondente com o motivo escrito.

## Verificação de adoção (SM-2, pós-adoção)

Feita por quem revisa, não por teste automático: 20 perguntas de organização de código distribuídas em
5 sessões novas (4 por sessão), com a skill `scos-query` disponível. Para cada pergunta registre se o
agente chamou o CLI antes de qualquer `Read` de fato bruto (confira em `.scos-map-query.log` e no
transcript). Quem mede é quem revisa, nunca quem implementou a mudança. O `.scos-map-query.log` (raiz do workspace,
ou `SCOS_MAP_QUERY_LOG`) registra uma linha TSV por chamada do CLI: use-o para ver a ordem das chamadas.
Baseline: as mesmas perguntas, nas 5 sessões anteriores à skill, contando quantas começaram por `Read`
de fato bruto ou `grep`. Meta: ≥ 90% (18 de 20) começam pelo CLI. Abaixo disso, revise a `description` da
`scos-query` e a tabela de roteamento (`PERGUNTA` dos módulos de `comandos/`).
