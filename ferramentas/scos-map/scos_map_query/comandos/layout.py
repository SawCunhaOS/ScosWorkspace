"""layout: pacote base, areas e entry points de um modulo."""

from ..modelo import Resultado, Secao

NOME = "layout"
PERGUNTA = "onde mora o que no modulo: pacote base, areas e entry points"
ESCOPO = "modulo"
FLAGS = []
EXEMPLO = (
    "## pacote_base (1 de 1)\tpacote_base\n"
    "br.com.scos.app\n"
    "## areas (2 de 2)\tcaminho\tpapel\tarquivos\n"
    "app/src/main/java/br/com/scos/config\tconfig\t8")
AJUDA = (
    "layout <projeto> <modulo>\n"
    "Pacote base, areas (caminho, papel, arquivos) e entry points (path, tipo, rota)\n"
    "do modulo. Saida: cabecalho '# confianca=... estado=... gerado=...', uma secao\n"
    "'## nome (m de t)' por tipo de dado e rodape '# n de M linhas casam | fontes: ...'.\n"
    "Exemplo:\n" + EXEMPLO + "\n")


def consultar(args, mapa):
    fato = mapa.layout(args.modulo)
    base = fato.get("pacote_base")
    areas = [[a.get("caminho"), a.get("papel"), a.get("arquivos")]
             for a in fato.get("areas") or []]
    entradas = [[e.get("path"), e.get("tipo"), e.get("rota", "-")]
                for e in fato.get("entrypoints") or []]
    fonte = mapa.lidos[-1].arquivo
    return Resultado([
        Secao("pacote_base", ["pacote_base"], [[base]] if base else [],
              1 if base else 0, fonte=fonte),
        Secao("areas", ["caminho", "papel", "arquivos"], areas, len(areas),
              fonte=fonte),
        Secao("entrypoints", ["path", "tipo", "rota"], entradas, len(entradas),
              fonte=fonte),
    ])
