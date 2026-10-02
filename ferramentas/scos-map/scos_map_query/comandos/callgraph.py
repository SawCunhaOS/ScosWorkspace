"""callgraph: grafo de chamadas estatico de um modulo (callgraph.json + callgraph_edges.tsv)."""

from ..modelo import Resultado, Secao

NOME = "callgraph"
PERGUNTA = "quem chama o metodo X (callgraph estatico do modulo)"
ESCOPO = "modulo"
FLAGS = [(["--de"], {"help": "Classe#metodo ou prefixo de origem"}),
         (["--para"], {"help": "Classe#metodo ou prefixo de destino"}),
         (["--entrypoints"], {"action": "store_true",
                              "help": "arestas saindo de classes de entrypoint"}),
         (["--lacunas"], {"action": "store_true", "help": "lacunas conhecidas"}),
         (["--sem-chamador"], {"action": "store_true",
                               "help": "metodos sem chamador no bytecode"})]
EXEMPLO = (
    "## arestas (2 de 2)\tde\tpara\tinvoke\tcerteza\n"
    "br.com.scos.app.FooBean#all\tbr.com.scos.app.Repo#find\tinvokeinterface\tambigua\n"
    "br.com.scos.app.FooBean#all\tbr.com.scos.app.Util#fmt\tinvokestatic\tresolvida")
AJUDA = (
    "callgraph <projeto> <modulo> [--de M] [--para M] [--entrypoints] [--lacunas]\n"
    "           [--sem-chamador]\n"
    "Sem flag: resumo (arestas_total, arestas_ambiguas, entrypoints, lacunas,\n"
    "sem_chamador). --de/--para casam Classe#metodo ou prefixo; --entrypoints: arestas\n"
    "de classes de entrypoint; --lacunas: tipo, path, anotacao, motivo; --sem-chamador:\n"
    "metodo, aviso (nao e lista de codigo morto). Fato indisponivel: motivo e\n"
    "comando_sugerido, exit 0 (nada e gerado). Ausencia de aresta nao prova ausencia\n"
    "de chamada.\n"
    "Exemplo:\n" + EXEMPLO + "\n")
AVISO = "ausencia de aresta nao prova ausencia de chamada"
LIM_MORTO = ("nao e lista de codigo morto: endpoints HTTP, @Scheduled e @EventListener "
             "nao tem chamador no bytecode")
COLS_ARESTA = ["de", "para", "invoke", "certeza"]


def _classe_simples(metodo):
    return metodo.split("#")[0].split("$")[0].split(".")[-1]


def consultar(args, mapa):
    dados = mapa.callgraph(args.modulo)
    if dados.get("estado") != "disponivel":
        resumo = [["estado", dados.get("estado") or mapa.lidos[-1].estado or "-"],
                  ["motivo", dados.get("motivo") or mapa.lidos[-1].motivo or "-"],
                  ["comando_sugerido", dados.get("comando_sugerido", "-")]]
        return Resultado([Secao("resumo", ["campo", "valor"], resumo, len(resumo),
                                tipo="resumo")], avisos=[AVISO])
    lacunas = dados.get("lacunas_conhecidas") or []
    sem_ch = dados.get("metodos_sem_chamador") or []
    entry = dados.get("entrypoints") or []
    resumo = [["arestas_total", dados.get("arestas_total", "-")],
              ["arestas_ambiguas", dados.get("arestas_ambiguas", "-")],
              ["entrypoints", len(entry)], ["lacunas", len(lacunas)],
              ["sem_chamador", len(sem_ch)]]
    secoes = [Secao("resumo", ["campo", "valor"], resumo, len(resumo), tipo="resumo")]
    lim = [dados["aviso"]] if dados.get("aviso") else []
    if args.lacunas:
        linhas = [[l.get("tipo", "-"), l.get("path", "-"),
                   l.get("anotacao", l.get("alvo", "-")), l.get("motivo", "-")]
                  for l in lacunas]
        secoes.append(Secao("lacunas", ["tipo", "path", "anotacao", "motivo"],
                            linhas, len(linhas)))
    if args.sem_chamador:
        linhas = [[m.get("metodo", "-"), m.get("aviso", "-")] for m in sem_ch]
        secoes.append(Secao("sem_chamador", ["metodo", "aviso"], linhas, len(linhas)))
        lim.append(LIM_MORTO)
    if args.de or args.para or args.entrypoints:
        nomes = {p["path"].rsplit("/", 1)[-1].removesuffix(".java")
                 for p in entry if p.get("path")}
        linhas = []
        for r in mapa.callgraph_arestas(args.modulo, dados):
            de, para = r.get("de", ""), r.get("para", "")
            if (args.de and not de.startswith(args.de)) \
                    or (args.para and not para.startswith(args.para)) \
                    or (args.entrypoints and _classe_simples(de) not in nomes):
                continue
            linhas.append([de, para, r.get("invoke", "-"), r.get("certeza", "-")])
        secoes.append(Secao("arestas", COLS_ARESTA, linhas, len(linhas),
                            fonte=mapa.lidos[-1].arquivo))
    return Resultado(secoes, avisos=[AVISO], limitacoes=lim,
                     refinar=["--de <metodo>", "--para <metodo>"])
