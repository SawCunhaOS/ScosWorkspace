"""snapshots: os -SNAPSHOT do ~/.m2 estao atras do repo produtor?"""

from ..modelo import Resultado, Secao

NOME = "snapshots"
PERGUNTA = "os jars SNAPSHOT do ~/.m2 estao atrasados em relacao ao repo produtor"
ESCOPO = "workspace"
FLAGS = [(["--detalhe"], {"action": "store_true"})]
EXEMPLO = (
    "## snapshots (1 de 1)\tprodutor\tjars\testados\tmax_atraso_dias\tacao\n"
    "repoA\t2 jar(s)\tjar_atual:1,jar_desatualizado:1\t5\tmvn clean install em repoA")
AJUDA = (
    "snapshots [--detalhe]\n"
    "Jars -SNAPSHOT consumidos entre repos, um por produtor (workspace.json);\n"
    "--detalhe: um por coordenada (ga, versao, estado, acao, atraso_dias).\n"
    "Estados misturados aparecem juntos em `estados`. Cabecalho estado=obsoleto\n"
    "quando o HEAD do produtor mudou desde o mapa; desconhecido se o mapa foi\n"
    "gerado com arvore suja ou o HEAD e ilegivel.\n"
    "ATENCAO: jar_atual so quer dizer mtime do jar >= ultimo commit; NAO garante\n"
    "que o jar contem o ultimo commit. Commit so de docs tambem marca atraso;\n"
    "alteracao nao commitada e stash nao contam. Nao le ~/.m2.\n"
    "Nao recebe projeto nem modulo (exit 2).\n"
    "Exemplo:\n" + EXEMPLO + "\n")
LIMITACOES = [
    "mtime != conteudo: jar_atual nao prova que o jar contem o ultimo commit",
    "commit so de docs marca atraso; alteracao nao commitada e stash nao contam"]


def consultar(args, ws):
    itens = ws.snapshots().get("itens") or []
    if args.detalhe:
        cols = ["ga", "versao", "estado", "acao", "atraso_dias"]
        linhas = [[i.get("ga"), i.get("versao"), i.get("estado"),
                   i.get("acao") or "-", i.get("atraso_dias", "-")] for i in itens]
    else:
        cols = ["produtor", "jars", "estados", "max_atraso_dias", "acao"]
        por = {}
        for i in itens:
            por.setdefault(i.get("produzido_por"), []).append(i)
        linhas = []
        for prod, g in por.items():
            est = {}
            for i in g:
                e = i.get("estado") or "desconhecido"
                est[e] = est.get(e, 0) + 1
            atrasos = [i["atraso_dias"] for i in g if "atraso_dias" in i]
            linhas.append([prod, "%d jar(s)" % len(g),
                           ",".join("%s:%d" % kv for kv in sorted(est.items())),
                           max(atrasos) if atrasos else "-",
                           next((i["acao"] for i in g if i.get("acao")), "-")])
    return Resultado([Secao("snapshots", cols, linhas, len(linhas),
                            fonte="workspace.json")], limitacoes=LIMITACOES)
