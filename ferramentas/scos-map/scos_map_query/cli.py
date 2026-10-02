"""Entrada: argparse, resolver() e main() (AD-5). Unico ponto que le o ambiente."""

import argparse
import importlib
import os
import pkgutil
import sys
import traceback
from pathlib import Path

from . import comandos, fatos, render
from .modelo import ErroConsulta, Opcoes

ACAO_AJUDA = "python3 ferramentas/scos-map/scos-map-query.py --help"


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ErroConsulta(2, message, ACAO_AJUDA)


def _positivo(v):
    n = int(v)
    if n < 1:
        raise argparse.ArgumentTypeError("deve ser >= 1: %s" % v)
    return n


def _registro():
    reg = {}
    for info in pkgutil.iter_modules(comandos.__path__):
        if not info.name.startswith("_"):
            m = importlib.import_module("%s.%s" % (comandos.__name__, info.name))
            reg[m.NOME] = m
    return reg


def encontrar_raiz(cwd):
    for d in [cwd, *cwd.parents]:
        if (d / ".scos-map" / "workspace.json").is_file():
            return d
    raise ErroConsulta(3, "workspace.json nao encontrado em nenhum ancestral",
                       fatos.ACAO_GERAR)


def resolver(ws, escopo, projeto, modulo):
    """Unica funcao que conhece a arvore do mapa: (entrada do projeto, modulo)."""
    projetos = ws.get("projetos") or []
    projeto = projeto.rstrip("/")
    entrada = next((p for p in projetos if p.get("projeto") == projeto), None)
    if entrada is None:
        raise ErroConsulta(3, "projeto inexistente: %s (existentes: %s)" % (
            projeto, ", ".join(p.get("projeto", "?") for p in projetos)),
            ACAO_AJUDA)
    if escopo != "modulo":
        if modulo is not None:
            raise ErroConsulta(2, "este subcomando nao recebe modulo", ACAO_AJUDA)
        return entrada, None
    if modulo is None:
        raise ErroConsulta(2, "modulo obrigatorio", ACAO_AJUDA)
    modulos = entrada.get("modulos") or []
    modulo = modulo.strip("/")
    if modulo.startswith("./"):
        modulo = modulo[2:]
    if modulo == ".":
        modulo = ""
    if not modulo:
        raise ErroConsulta(2, "modulo obrigatorio", ACAO_AJUDA)
    if modulo in modulos:
        return entrada, modulo
    achados = [m for m in modulos if m.rsplit("/", 1)[-1] == modulo]
    if len(achados) == 1:
        return entrada, achados[0]
    if achados:
        raise ErroConsulta(2, "modulo ambiguo: %s (opcoes: %s)"
                           % (modulo, ", ".join(achados)), ACAO_AJUDA)
    raise ErroConsulta(3, "modulo inexistente em %s: %s" % (projeto, modulo),
                       ACAO_AJUDA)


def _executar(argv, cwd, lidos, ctx):
    reg = _registro()
    try:
        ctx["raiz"] = encontrar_raiz(cwd)
    except ErroConsulta:
        pass
    if argv and argv[0] in reg:
        ctx["sub"] = argv[0]
    if any(a in ("-h", "--help") for a in argv):
        if argv and argv[0] in reg:
            return reg[argv[0]].AJUDA.rstrip("\n")
        return "\n".join("%s\t%s" % (n, m.PERGUNTA) for n, m in reg.items())
    parser = _Parser(prog="scos-map-query", add_help=False)
    sub = parser.add_subparsers(dest="subcomando", required=True)
    for nome, m in reg.items():
        p = sub.add_parser(nome, add_help=False)
        p.add_argument("projeto")
        p.add_argument("modulo", nargs="?")
        p.add_argument("--limit", type=_positivo)
        p.add_argument("--bytes", type=_positivo)
        p.add_argument("--all", dest="todos", action="store_true")
        p.add_argument("--base", action="store_true")
        for flag_args, flag_kw in m.FLAGS:
            p.add_argument(*flag_args, **flag_kw)
    args = parser.parse_args(argv)
    if args.todos and (args.limit or args.bytes):
        raise ErroConsulta(2, "--all nao combina com --limit/--bytes", ACAO_AJUDA)
    op = Opcoes(args.limit, args.bytes, args.todos, args.base)
    cmd = reg[args.subcomando]
    raiz = encontrar_raiz(cwd)
    ctx.update(projeto=args.projeto)
    ws, avisos = fatos.abrir_workspace(raiz)
    # ponytail: so escopos projeto/modulo; ESCOPO=workspace chega no Epic 2
    entrada, args.modulo = resolver(
        ws, "projeto" if getattr(args, "todos_modulos", False) else cmd.ESCOPO,
        args.projeto, args.modulo)
    ctx.update(projeto=entrada["projeto"], modulo=args.modulo)
    mapa = fatos.Mapa(raiz, entrada, avisos, lidos)
    return render.montar(cmd.consultar(args, mapa), lidos, op)


def _log(ctx, lidos, codigo):
    raiz = ctx.get("raiz")
    if raiz is None:
        return None
    caminho = os.environ.get("SCOS_MAP_QUERY_LOG") or raiz / ".scos-map-query.log"
    schema = lidos[0].schema_versao if lidos else None
    return caminho, [ctx.get("sub"), ctx.get("projeto"), ctx.get("modulo"),
                     codigo, schema]


def main(argv=None, cwd=None):
    argv = sys.argv[1:] if argv is None else argv
    cwd = Path(cwd) if cwd else Path.cwd()
    lidos = []
    ctx = {}
    codigo = 0
    try:
        texto = _executar(argv, cwd, lidos, ctx)
    except ErroConsulta as e:
        texto, codigo = render.erro(e.mensagem, e.acao, lidos), e.codigo
    except Exception:
        extra = traceback.format_exc().rstrip() \
            if os.environ.get("SCOS_MAP_QUERY_DEBUG") == "1" else ""
        texto, codigo = render.erro("interno", "-", lidos, extra), 1
    render.emitir(texto, _log(ctx, lidos, codigo))
    return codigo
