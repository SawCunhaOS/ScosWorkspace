"""conflitos: bibliotecas com versoes diferentes entre os repos do workspace."""

from ..modelo import Resultado, Secao

NOME = "conflitos"
PERGUNTA = "quais bibliotecas tem versoes divergentes entre os repos"
ESCOPO = "workspace"
FLAGS = []
EXEMPLO = (
    "## conflitos (1 de 1)\tga\tversoes\n"
    "org.x:y\t1.0:repoA | 2.0:repoB (gerenciada)")
AJUDA = (
    "conflitos\n"
    "Conflitos de versao entre os repos (workspace.json), um por biblioteca:\n"
    "ga e `versao:repos | ...`; `(gerenciada)` marca versao fixada por BOM.\n"
    "Sem scope test. Estado = pior caso dos HEADs; arvore suja vira limitacao.\n"
    "Nao recebe projeto nem modulo (exit 2).\n"
    "Exemplo:\n" + EXEMPLO + "\n")


def _repos(mods):
    vistos = []
    for m in mods:
        r = m.split("/", 1)[0] + (" (gerenciada)" if m.endswith("(gerenciada)") else "")
        if r not in vistos:
            vistos.append(r)
    return ",".join(vistos)


def consultar(args, ws):
    fato = ws.conflitos()
    linhas = [[i.get("ga"), " | ".join("%s:%s" % (v, _repos(ms))
                                       for v, ms in (i.get("versoes") or {}).items())]
              for i in fato.get("itens") or []]
    return Resultado([Secao("conflitos", ["ga", "versoes"], linhas, len(linhas),
                            fonte="workspace.json")])
