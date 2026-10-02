"""tests: arquivos de teste de um modulo (resumo de tests.json, lista de tests.tsv)."""

from ..filtros import contem
from ..modelo import Resultado, Secao

NOME = "tests"
PERGUNTA = "que testes existem para o modulo ou para a classe X (heuristica)"
ESCOPO = "modulo"
FLAGS = [(["--arquivos"], {"action": "store_true", "help": "lista os arquivos de teste"}),
         (["--alvo"], {"help": "substring do alvo heuristico (implica --arquivos)"})]
EXEMPLO = (
    "frameworks\tJUnit 5 (declarada), AssertJ (inferida)\n"
    "cobertura\tnao_analisado (nenhum relatorio JaCoCo lido)\n"
    "## arquivos (1 de 1)\tpath\ttipo\talvo_heuristico\tlinhas\tcommits_90d\tmarca\n"
    "app/src/test/java/FooBeanTest.java\tunit\tFooBean\t40\t3\t[heuristica]")
AJUDA = (
    "tests <projeto> <modulo> [--arquivos] [--alvo X]\n"
    "Resumo: raizes, arquivos, tipos, frameworks (declarada/inferida), cobertura\n"
    "com o estado do fato (nao_analisado NAO e 'sem cobertura'). --arquivos lista\n"
    "tests.tsv; --alvo X (substring, sem caixa) restringe e implica --arquivos.\n"
    "alvo_heuristico e casamento de nome [heuristica]: pode-se afirmar 'existe um\n"
    "teste chamado XTest', nunca 'X esta testada'. Zero achados = nenhum arquivo\n"
    "nas raizes analisadas, nao 'nao existe teste'.\n"
    "Exemplo:\n" + EXEMPLO + "\n")
AVISO = "alvo e heuristica; existe teste chamado XTest, nao prova cobertura"
COLUNAS = ["path", "tipo", "alvo_heuristico", "linhas", "commits_90d", "marca"]


def consultar(args, mapa):
    dados = mapa.tests(args.modulo)
    listar = args.arquivos or bool(args.alvo)
    vazio = dados.get("arquivos") == 0
    raizes = ", ".join(str(r) for r in dados.get("raizes") or []) or "-"
    linhas = []
    if listar and not vazio:
        for r in mapa.tests_arquivos(args.modulo, dados):
            if contem(r.get("alvo_heuristico"), args.alvo):
                linhas.append([r.get("path", "-"), r.get("tipo", "-"),
                               r.get("alvo_heuristico") or "-", r.get("linhas", "-"),
                               r.get("commits_90d", "-"), "[heuristica]"])
    cob = dados.get("cobertura") or {}
    resumo = [
        ["raizes", raizes],
        ["arquivos", dados.get("arquivos", "-")],
        ["tipos", ", ".join("%s:%s" % kv for kv in (dados.get("por_tipo") or {}).items()) or "-"],
        ["frameworks", ", ".join("%s (%s)" % (f.get("nome", "-"), f.get("origem", "-"))
                                 for f in dados.get("frameworks") or []) or "-"],
        ["cobertura", "%s (%s)" % (cob.get("estado", "-"), cob.get("motivo", "-"))
         if cob.get("motivo") else cob.get("estado", "-")]]
    if vazio or (listar and not linhas):
        resumo.append(["resultado", "nenhum arquivo de teste identificado nas raizes "
                       "analisadas: " + raizes])
    secoes = [Secao("resumo", ["campo", "valor"], resumo, len(resumo), tipo="resumo")]
    if listar:
        secoes.append(Secao("arquivos", COLUNAS, linhas, len(linhas)))
    return Resultado(secoes, avisos=[AVISO],
                     refinar=["--alvo <classe>"])
