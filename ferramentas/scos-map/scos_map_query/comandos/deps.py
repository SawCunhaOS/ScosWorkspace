"""deps: dependencias diretas e transitivas de um modulo (ou de todos)."""

from ..filtros import contem
from ..modelo import Resultado, Secao

NOME = "deps"
PERGUNTA = "o modulo usa a biblioteca X, em que versao e de onde vem"
ESCOPO = "modulo"
FLAGS = [(["--ga"], {"help": "substring da coordenada groupId:artifactId"}),
         (["--todos-modulos"], {"action": "store_true",
                                "help": "todos os modulos do projeto (sem modulo posicional)"})]
EXEMPLO = (
    "## dependencias (2 de 2)\tga\tversao\tscope\torigem\tmarca\n"
    "br.com.scos:web\t1.2.0\tcompile\teffective-pom\n"
    "io.jsonwebtoken:jjwt-api\t0.12.6\tcompile\tdependency:tree\t[transitiva]\n"
    "## transitivas (1 de 1)\tga\tversao\tscope\tmarca\n"
    "org.jspecify:jspecify\t1.0.1\tcompile\t[transitiva]")
AJUDA = (
    "deps <projeto> <modulo> [--ga S] | deps <projeto> --todos-modulos [--ga S]\n"
    "Diretas e transitivas do modulo: ga, versao, scope, origem; marca\n"
    "[transitiva]. A secao 'transitivas' e o fecho comum a todos os modulos\n"
    "(_transitivas_comuns.tsv): NAO repete em dependencias. Nunca conclua 'nao\n"
    "usa X' lendo so uma das duas. origem=effective-pom: veio do pom efetivo.\n"
    "--todos-modulos acrescenta a coluna modulo e percorre o projeto inteiro.\n"
    "Exemplo:\n" + EXEMPLO + "\n")


def consultar(args, mapa):
    todos = args.todos_modulos
    modulos = mapa.modulos_com_deps() if todos else [args.modulo]
    colunas = ["ga", "versao", "scope", "origem", "marca"]
    diretas, comuns = [], []
    for m in modulos:
        corpo, c = mapa.deps(m)
        comuns = comuns or c
        for r in corpo:
            if contem(r.get("ga"), args.ga):
                linha = [r.get("ga"), r.get("versao", "-"), r.get("scope", "-"),
                         r.get("origem", "-"),
                         "[transitiva]" if r.get("tipo") == "transitiva" else ""]
                diretas.append(([m] if todos else []) + linha)
    trans = [[r.get("ga"), r.get("versao", "-"), r.get("scope", "-"), "[transitiva]"]
             for r in comuns if contem(r.get("ga"), args.ga)]
    return Resultado([
        Secao("dependencias", (["modulo"] if todos else []) + colunas, diretas,
              len(diretas)),
        Secao("transitivas", ["ga", "versao", "scope", "marca"], trans, len(trans))])
