"""config: arquivos de configuracao do modulo (so caminho e tamanho, nunca valores)."""

from ..modelo import Resultado, Secao

NOME = "config"
PERGUNTA = "quais arquivos de configuracao o modulo tem e onde moram"
ESCOPO = "modulo"
FLAGS = [(["--prefixo"], {"help": "so paths com este prefixo"})]
EXEMPLO = (
    "## arquivos (2 de 2)\tpath\tbytes\n"
    "app/src/main/resources/application.yml\t1200\n"
    "app/src/main/resources/application-dev.yml\t340")
AJUDA = (
    "config <projeto> <modulo> [--prefixo P]\n"
    "Arquivos de configuracao do modulo: path e bytes. Valores nunca aparecem;\n"
    "abra o arquivo pelo caminho. --prefixo filtra por prefixo de path.\n"
    "Saida: cabecalho '# confianca=... estado=... gerado=...', secao\n"
    "'## arquivos (m de t)' e rodape '# n de M linhas casam | fontes: ...'.\n"
    "Exemplo:\n" + EXEMPLO + "\n")


def consultar(args, mapa):
    fato = mapa.config(args.modulo)
    pref = args.prefixo or ""
    linhas = [[a.get("path"), a.get("bytes", "-")] for a in fato.get("arquivos") or []
              if (a.get("path") or "").startswith(pref)]
    return Resultado([Secao("arquivos", ["path", "bytes"], linhas, len(linhas),
                            fonte=mapa.lidos[-1].arquivo)])
