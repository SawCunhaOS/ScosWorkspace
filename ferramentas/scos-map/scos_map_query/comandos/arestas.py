"""arestas: arestas de bytecode (quem usa quem) de um modulo, de bytecode_edges.tsv."""

from ..modelo import Resultado, Secao

NOME = "arestas"
PERGUNTA = "quem usa a classe X (arestas de bytecode do modulo)"
ESCOPO = "modulo"
FLAGS = [(["--de"], {"help": "classe ou prefixo de origem"}),
         (["--para"], {"help": "classe ou prefixo de destino"}),
         (["--pacote"], {"help": "de OU para dentro deste pacote"})]
EXEMPLO = (
    "## arestas (2 de 2)\tde\tpara\ttipo\torigem\n"
    "br.com.scos.app.A\tbr.com.scos.lib.Core\texterno\tclasses\n"
    "br.com.scos.app.B\tbr.com.scos.lib.Core\texterno\tclasses")
AJUDA = (
    "arestas <projeto> <modulo> [--de C] [--para C] [--pacote P]\n"
    "Arestas de bytecode (jdeps): de, para, tipo, origem. --de/--para casam classe\n"
    "ou prefixo (sensivel a caixa); --pacote casa de OU para dentro de P.\n"
    "Sem bytecode_edges.tsv: erro 3 com o build --tier 2/3 (nada e gerado).\n"
    "Arestas vazias nao provam que o modulo nao tem dependencias.\n"
    "Exemplo:\n" + EXEMPLO + "\n")
NAO_PROVA = "arestas vazias nao provam que o modulo nao tem dependencias"


def _plano(d):
    if isinstance(d, dict):
        return ", ".join("%s=%s" % kv for kv in d.items()) or "-"
    return d if d is not None else "-"


def consultar(args, mapa):
    dados, tabela = mapa.arestas(args.modulo)
    fonte = mapa.lidos[-1].arquivo
    pac = args.pacote + "." if args.pacote else None
    linhas = []
    for r in tabela:
        de, para = r.get("de", ""), r.get("para", "")
        if (args.de and not de.startswith(args.de)) \
                or (args.para and not para.startswith(args.para)) \
                or (pac and not (de.startswith(pac) or para.startswith(pac))):
            continue
        linhas.append([de, para, r.get("tipo", "-"), r.get("origem", "-")])
    lim = []
    if dados.get("estado") == "disponivel" and not tabela:
        lim = ["motivo_vazio: %s" % dados.get("motivo_vazio", "-"),
               "diagnostico: %s" % _plano(dados.get("diagnostico")), NAO_PROVA]
    return Resultado([Secao("arestas", ["de", "para", "tipo", "origem"], linhas,
                            len(linhas), fonte=fonte)],
                     limitacoes=lim,
                     refinar=["--de <classe>", "--para <classe>", "--pacote <pacote>"])
