"""arquivos: files.tsv filtrado por modulo, tipo e commits (suite awk congelada)."""

from ..modelo import Resultado, Secao

NOME = "arquivos"
PERGUNTA = "que arquivos existem num modulo ou quais sao os mais mexidos"
ESCOPO = "projeto"
AVISO = "historico de arquivo nao esta no mapa"
FLAGS = [(["--em-modulo"], {"help": "coluna module igual a este valor"}),
         (["--kind"], {"help": "coluna kind igual a este valor"}),
         (["--commits-90d-min"], {"type": int, "dest": "commits_min",
                                  "help": "commits_90d maior ou igual a N"})]
EXEMPLO = (
    "## arquivos (2 de 2)\tpath\tkind\tmodule\tcommits_90d\n"
    "organization/pom.xml\tbuild\torganization\t7\n"
    "organization/README.md\tdoc\torganization\t6")
AJUDA = (
    "arquivos <projeto> [--em-modulo M] [--kind K] [--commits-90d-min N]\n"
    "Arquivos do mapa: path, kind, module, commits_90d. --em-modulo e --kind\n"
    "comparam a coluna por igualdade; --commits-90d-min filtra numericamente.\n"
    "Equivale aos awk de files.tsv: $5==M && $6==K e $10>=N.\n"
    "Exemplo:\n" + EXEMPLO + "\n")


def _commits(r):
    try:
        return int(r.get("commits_90d", ""))
    except ValueError:
        return None


def consultar(args, mapa):
    linhas = []
    for r in mapa.arquivos():
        if args.em_modulo is not None and r.get("module") != args.em_modulo:
            continue
        if args.kind is not None and r.get("kind") != args.kind:
            continue
        if args.commits_min is not None and (
                _commits(r) is None or _commits(r) < args.commits_min):
            continue
        linhas.append([r.get("path"), r.get("kind", "-"), r.get("module", "-"),
                       r.get("commits_90d", "-")])
    return Resultado([Secao("arquivos", ["path", "kind", "module", "commits_90d"],
                            linhas, len(linhas), fonte=mapa.lidos[-1].arquivo)],
                     avisos=[AVISO])
