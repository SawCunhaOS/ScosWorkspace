"""reactor: modulos do projeto e arestas internas entre eles."""

from ..filtros import contem
from ..modelo import Resultado, Secao

NOME = "reactor"
PERGUNTA = "quais modulos o projeto tem e quem depende de quem"
ESCOPO = "projeto"
FLAGS = [(["--id"], {"help": "substring do id do modulo (modulos) ou de `de` (arestas)"})]
EXEMPLO = (
    "## modulos (2 de 2)\tid\ttipo\n"
    "app\tjar\n"
    "lib/core\tjar\n"
    "## arestas (1 de 1)\tde\tpara\tscope\n"
    "app\tlib/core\tcompile")
AJUDA = (
    "reactor <projeto> [--id S]\n"
    "Fronteiras do projeto: modulos (id, tipo) e arestas internas (de, para,\n"
    "scope) na ordem do fato. --id filtra por substring do id (e do `de`).\n"
    "Nao recebe modulo.\n"
    "Exemplo:\n" + EXEMPLO + "\n")


def consultar(args, mapa):
    fato = mapa.reactor()
    fonte = mapa.lidos[-1].arquivo
    mods = [[m.get("id"), m.get("tipo", "-")] for m in fato.get("modulos") or []
            if contem(m.get("id"), args.id)]
    arestas = [[a.get("de"), a.get("para"), a.get("scope", "-")]
               for a in fato.get("arestas_internas") or []
               if contem(a.get("de"), args.id)]
    return Resultado([
        Secao("modulos", ["id", "tipo"], mods, len(mods), fonte=fonte),
        Secao("arestas", ["de", "para", "scope"], arestas, len(arestas),
              fonte=fonte)])
