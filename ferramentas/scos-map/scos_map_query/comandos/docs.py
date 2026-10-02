"""docs: indice de documentos do modulo (path, titulo, subtipo)."""

from ..modelo import Resultado, Secao

NOME = "docs"
PERGUNTA = "que documentacao existe sobre um assunto no modulo"
ESCOPO = "modulo"
FLAGS = [(["--texto"], {"help": "termo em path ou titulo, sem diferenciar maiusculas"}),
         (["--prefixo"], {"help": "so paths com este prefixo"})]
AVISO = "doc antigo pode estar defasado; frontmatter literal: sem status nao e rascunho"
EXEMPLO = (
    "## documentos (2 de 2)\tpath\ttitulo\tsubtipo\n"
    "docs/adr/0001-cache.md\tADR 1: cache\tadr\n"
    "README.md\tMeu modulo\treadme")
AJUDA = (
    "docs <projeto> <modulo> [--texto T] [--prefixo P]\n"
    "Indice de documentos: path, titulo, subtipo. --texto busca em path ou\n"
    "titulo (sem diferenciar maiusculas); --prefixo filtra por prefixo de path.\n"
    "Subtipos (do caminho ou titulo): adr prd epic story spec runbook\n"
    "arquitetura changelog readme contrato; fora de convencao = outro.\n"
    "Documento antigo ao lado de codigo recente pode estar desatualizado:\n"
    "confira a data antes de confiar. Frontmatter e lido literalmente: sem\n"
    "status nao significa rascunho nem aprovado. Abra o arquivo para ler.\n"
    "Exemplo:\n" + EXEMPLO + "\n")


def consultar(args, mapa):
    fato = mapa.docs(args.modulo)
    pref = args.prefixo or ""
    termo = (args.texto or "").lower()
    linhas = []
    for d in fato.get("itens") or []:
        path, titulo = d.get("path") or "", d.get("titulo") or ""
        if path.startswith(pref) and (
                not termo or termo in path.lower() or termo in titulo.lower()):
            linhas.append([path, titulo or "-", d.get("subtipo", "-")])
    return Resultado([Secao("documentos", ["path", "titulo", "subtipo"], linhas,
                            len(linhas), fonte=mapa.lidos[-1].arquivo)],
                     avisos=[AVISO])
