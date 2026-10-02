"""bytecode: higiene de dependencias vista pelo bytecode (baldes de bytecode.json)."""

from ..modelo import ErroConsulta, Resultado, Secao

NOME = "bytecode"
PERGUNTA = "quais dependencias o bytecode usa sem declarar (risco x higiene)"
ESCOPO = "modulo"
BALDES = [("deps_usadas_ausentes_do_pom", "risco imediato"),
          ("deps_usadas_via_transitiva", "higiene"),
          ("deps_declaradas_sem_uso", "higiene"),
          ("deps_ignoradas_na_analise", "informativo")]
FLAGS = [(["--balde"], {"help": "lista um balde: " + ", ".join(b for b, _ in BALDES)})]
EXEMPLO = (
    "## resumo (6 de 6)\tcampo\tvalor\tleitura\n"
    "deps_usadas_ausentes_do_pom\t1\trisco imediato\n"
    "deps_usadas_via_transitiva\t2\thigiene\n"
    "deps_declaradas_sem_uso\t1\thigiene\n"
    "deps_ignoradas_na_analise\tnao calculado\tinformativo")
AJUDA = (
    "bytecode <projeto> <modulo> [--balde NOME]\n"
    "Resumo por balde (contagem), frescor e transitivas_resolvidas. Baldes:\n"
    "deps_usadas_ausentes_do_pom (unico risco imediato), deps_usadas_via_transitiva e\n"
    "deps_declaradas_sem_uso (higiene), deps_ignoradas_na_analise (informativo).\n"
    "Balde que o fato nao traz = 'nao calculado', nunca 0. --balde lista artefato,\n"
    "referencias, nota, marca ([provavel_falso_positivo]). transitivas_resolvidas\n"
    "falso: a divisao dos dois primeiros baldes nao e confiavel (# limitacao).\n"
    "Exemplo:\n" + EXEMPLO + "\n")
AVISO = "so deps_usadas_ausentes_do_pom e risco; demais baldes sao higiene"
LIMITACAO = ("transitivas_resolvidas falso: a divisao entre deps_usadas_ausentes_do_pom "
             "e deps_usadas_via_transitiva nao e confiavel")


def consultar(args, mapa):
    nomes = [b for b, _ in BALDES]
    if args.balde and args.balde not in nomes:
        raise ErroConsulta(2, "balde invalido: %s; validos: %s"
                           % (args.balde, ", ".join(nomes)),
                           "bytecode <projeto> <modulo> --balde <nome>")
    dados = mapa.bytecode(args.modulo)
    estado = mapa.lidos[-1].estado
    if dados.get("estado") != "disponivel" or estado in ("indisponivel", "nao_aplicavel"):
        resumo = [["estado", dados.get("estado") or estado or "-", "-"]]
        return Resultado([Secao("resumo", ["campo", "valor", "leitura"], resumo,
                                len(resumo), tipo="resumo")], avisos=[AVISO])
    resumo = [[b, len(dados[b]) if isinstance(dados.get(b), list) else "nao calculado", leitura]
              for b, leitura in BALDES]
    fr = dados.get("frescor") or {}
    resumo.append(["frescor", "%s (compilado_em %s)" % (fr.get("estado", "-"),
                                                       fr.get("compilado_em", "-")), "-"])
    resumo.append(["transitivas_resolvidas", dados.get("transitivas_resolvidas", "-"), "-"])
    secoes = [Secao("resumo", ["campo", "valor", "leitura"], resumo, len(resumo),
                    tipo="resumo")]
    if args.balde:
        linhas = []
        for r in dados.get(args.balde) or []:
            nota = r.get("nota") or r.get("motivo") or r.get("scope") or "-"
            linhas.append([r.get("artefato", "-"), r.get("referencias", "-"), nota,
                           "[provavel_falso_positivo]" if r.get("provavel_falso_positivo")
                           else ""])
        secoes.append(Secao("itens", ["artefato", "referencias", "nota", "marca"],
                            linhas, len(linhas)))
    lim = [LIMITACAO] if dados.get("transitivas_resolvidas") is False else []
    if args.balde and not isinstance(dados.get(args.balde), list):
        lim.append("%s: nao calculado (0 itens listados nao significa balde vazio)"
                   % args.balde)
    return Resultado(secoes, avisos=[AVISO], limitacoes=lim,
                     refinar=["--balde <nome>"])
