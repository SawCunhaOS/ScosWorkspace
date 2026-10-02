"""`--help confianca`: legenda do envelope `# confianca=... estado=...` (FR-5)."""

CONFIANCA = """\
Legenda do cabecalho `# confianca=C estado=E [completude=P] gerado=T`
(com varios fatos lidos, vale o pior caso entre eles).
confianca (pior -> melhor):
  conflito   parse_pom deduziu uma versao e o effective-pom deu outra; vale a do effective-pom
  heuristica inferencia por convencao de nome: confirme antes de afirmar
  parcial    so o callgraph: leia as lacunas (proxy, Spring Data, reflexao)
  media      config sem PyYAML (lista, ancora, alias nao lidos) ou bytecode sem classpath
             completo/obsoleto: orienta, nao afirma
  declarada  so o manifesto foi lido; a versao real pode diferir
  resolvida  lockfile ou dependency:tree
  alta       bytecode ou manifesto: pode afirmar
estado:
  fresco/disponivel, obsoleto (fonte mudou depois do fato: regenere ou avise),
  desconhecido (arvore suja ou HEAD ilegivel: nao da para comparar),
  ausente, indisponivel, nao_aplicavel.
  nao_aplicavel e resultado LEGITIMO, nao erro (modulo pom sem codigo; React sem bytecode).
completude: total ou parcial; parcial vem com `# limitacao:` do que ficou de fora.
desvios: itens que nao seguem a confianca do envelope; a linha traz a marca propria.
base: de onde o dado saiu (`--base` imprime `# base:`); nao afirme o que a base nao cobre.
"""
