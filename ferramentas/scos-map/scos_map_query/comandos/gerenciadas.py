"""gerenciadas: versoes que a BOM/dependencyManagement fixa para o modulo."""

from ..filtros import contem
from ..modelo import Resultado, Secao

NOME = "gerenciadas"
PERGUNTA = "que versao de dependencia a BOM fixa para o modulo"
ESCOPO = "modulo"
FLAGS = [(["--ga"], {"help": "substring da coordenada groupId:artifactId"})]
EXEMPLO = (
    "## gerenciadas (2 de 2)\tga\tversao\torigem\tscope\n"
    "org.springframework.kafka:spring-kafka-bom\t4.1.1\tpropria\timport\n"
    "com.google.errorprone:error_prone_annotations\t2.48.0\tpropria\tcompile")
AJUDA = (
    "gerenciadas <projeto> <modulo> [--ga SUBSTRING]\n"
    "Versoes gerenciadas (dependencyManagement): ga, versao, origem, scope.\n"
    "--ga filtra por substring da coordenada. Use antes de fixar uma versao.\n"
    "Exemplo:\n" + EXEMPLO + "\n")


def consultar(args, mapa):
    linhas = [[r.get("ga"), r.get("versao", "-"), r.get("origem", "-"),
               r.get("scope", "-")]
              for r in mapa.gerenciadas(args.modulo) if contem(r.get("ga"), args.ga)]
    return Resultado([Secao("gerenciadas", ["ga", "versao", "origem", "scope"],
                            linhas, len(linhas), fonte=mapa.lidos[-1].arquivo)])
