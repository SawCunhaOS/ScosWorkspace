"""Saida unica: envelope, secoes e rodape (AD-4, AD-6). Nao interpreta fato."""

import os
import re
import sys
from datetime import datetime, timezone

from .modelo import MAX_LINHA, TETO_BYTES, TETO_LINHAS, Opcoes, Resultado

_CONFIANCA = ["conflito", "heuristica", "parcial", "media", "declarada",
              "resolvida", "alta"]  # pior -> melhor
_ESTADO = ["obsoleto", "desconhecido", "ausente", "indisponivel",
           "nao_aplicavel", "disponivel", "fresco"]
_COMPLETUDE = ["parcial", "total"]


def tsv_clean(v):
    return re.sub(r"[\t\r\n]+", " ", str(v))


def _pior(valores, ordem):
    vals = [v for v in valores if v]
    if not vals:
        return None
    return min(vals, key=lambda v: ordem.index(v) if v in ordem else -1)


def _commits(lidos):
    repos = {}
    for m in lidos:
        for repo in m.heads:
            n = m.commits_desde.get(repo)
            if n is not None:
                repos.setdefault(repo, n)
    if len(repos) == 1:
        return " commits_desde_o_mapa=%d" % next(iter(repos.values()))
    if repos:
        return " commits_desde_o_mapa=" + ",".join(
            "%s:%d" % kv for kv in repos.items())
    return ""


MAX_FONTES = 12


def _grupos(lidos):
    """[(nome, confianca, estado)] por nome-base do arquivo; `\u00d7n` quando ha varios."""
    por = {}
    for m in lidos:
        por.setdefault(m.arquivo.rsplit("/", 1)[-1], []).append(m)
    grupos = []
    for base, ms in por.items():
        pior = lambda ordem, vals: _pior(vals, ordem) or "-"
        grupos.append((base if len(ms) == 1 else "%s\u00d7%d" % (base, len(ms)),
                       pior(_CONFIANCA, [m.confianca for m in ms]),
                       pior(_ESTADO, [m.estado for m in ms])))
    return grupos


def _envelope(lidos, res, op=None):
    comp = _pior([m.completude for m in lidos], _COMPLETUDE)
    gerados = [m.gerado for m in lidos if m.gerado]
    linhas = ["# confianca=%s estado=%s%s gerado=%s%s" % (
        _pior([m.confianca for m in lidos], _CONFIANCA) or "-",
        _pior([m.estado for m in lidos], _ESTADO) or "-",
        " completude=" + comp if comp else "",
        min(gerados) if gerados else "-",
        _commits(lidos))]
    for m in lidos:
        if m.motivo:
            linhas.append("# motivo: " + tsv_clean(m.motivo))
    if op and op.base:
        linhas += ["# base: " + tsv_clean(b) for b in dict.fromkeys(
            m.base for m in lidos if m.base)]
    if len(lidos) > 1:
        grupos = _grupos(lidos)
        linhas += ["# fontes: %s(%s,%s)" % g for g in grupos[:MAX_FONTES]]
        if len(grupos) > MAX_FONTES:
            linhas.append("# fontes: \u2026 +%d fontes" % (len(grupos) - MAX_FONTES))
    avisos = []
    for a in [x for m in lidos for x in m.avisos] + list(res.avisos):
        if a not in avisos:
            avisos.append(a)
    linhas += ["# aviso: " + tsv_clean(a) for a in avisos]
    if comp == "parcial":
        linhas += ["# limitacao: " + tsv_clean(x) for x in dict.fromkeys(
            x for m in lidos for x in m.limitacoes)]
    linhas += ["# limitacao: " + tsv_clean(x) for x in res.limitacoes]
    return linhas


def _linha(secao, celulas):
    """Linha TSV truncada em MAX_LINHA; a coluna marca (ultima) nunca e cortada."""
    texto = "\t".join(tsv_clean(c) for c in celulas)
    if len(texto) <= MAX_LINHA:
        return texto
    cauda = ""
    if secao.colunas and secao.colunas[-1] == "marca":
        cauda = "\t" + tsv_clean(celulas[-1])
        texto = "\t".join(tsv_clean(c) for c in celulas[:-1])
    return texto[:max(MAX_LINHA - len(cauda) - 1, 0)] + "\u2026" + cauda


def _cortar(secoes, op):
    """Consome o teto global na ordem das secoes dados -> [(secao, linhas)]."""
    max_l = None if op.todos else op.limit or TETO_LINHAS
    max_b = None if op.todos else op.bytes or TETO_BYTES
    cheio = False
    usado_l = usado_b = 0
    saida = []
    for s in secoes:
        linhas = [_linha(s, c) for c in s.linhas]
        if s.tipo != "dados":
            saida.append((s, linhas))
            continue
        mostradas = []
        for l in linhas:
            tam = len(l.encode("utf-8")) + 1
            if cheio or (max_l is not None and usado_l + 1 > max_l) \
                    or (max_b is not None and usado_b + tam > max_b):
                cheio = True
                break
            mostradas.append(l)
            usado_l += 1
            usado_b += tam
        saida.append((s, mostradas))
    return saida, cheio


def _refinar(res, cortadas, op):
    if res.refinar:
        flags = list(res.refinar)
    else:
        todas = [l for s, ls in cortadas if s.tipo == "dados"
                 for l in ([_linha(s, c) for c in s.linhas])]
        flags = []
        if len(todas) > (op.limit or TETO_LINHAS):
            flags.append("--limit %d" % len(todas))
        if sum(len(l.encode("utf-8")) + 1 for l in todas) > (
                op.bytes or TETO_BYTES):
            flags.append("--bytes %d" % sum(len(l.encode("utf-8")) + 1
                                           for l in todas))
    return " ou ".join(flags + ["--all"])


def _rodape(secoes, lidos, mostradas=None):
    dados = [(s, n) for s, n in (mostradas or [(s, len(s.linhas)) for s in secoes])
             if s.tipo == "dados"]
    fontes = [g[0] for g in _grupos(lidos)] if len(lidos) > 1 else \
        list(dict.fromkeys(m.arquivo for m in lidos))
    return "# %d de %d linhas casam | fontes: %s" % (
        sum(n for _, n in dados), sum(s.total for s, _ in dados),
        ",".join(fontes) or "-")


def montar(res, lidos, op=None):
    op = op or Opcoes()
    saida = _envelope(lidos, res, op) if lidos else []
    cortadas, cheio = _cortar(res.secoes, op)
    for s, linhas in cortadas:
        saida.append("## %s (%d de %d)%s" % (
            s.nome, len(linhas), s.total,
            "".join("\t" + c for c in s.colunas)))
        saida += linhas
    if cheio:
        saida.append("# truncado: use " + _refinar(res, cortadas, op))
    saida.append(_rodape(res.secoes, lidos,
                         [(s, len(ls)) for s, ls in cortadas]))
    return "\n".join(saida)


def erro(msg, acao, lidos, extra=""):
    saida = []
    if lidos:
        saida += _envelope(lidos, Resultado([]))
    saida.append("# erro: %s | acao: %s" % (tsv_clean(msg), tsv_clean(acao)))
    if extra:
        saida.append(extra)
    if lidos:
        saida.append(_rodape([], lidos))
    return "\n".join(saida)


def _registrar(texto, log):
    """Um registro TSV por chamada, um unico write em append (AD-9); nunca falha."""
    try:
        caminho, campos = log
        campos = ["-" if c in (None, "") else tsv_clean(c) for c in campos]
        n = len((texto + "\n").encode("utf-8"))
        campos[3:3] = [str(n), str(texto.count("\n") + 1)]
        campos.insert(0, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        linha = ("\t".join(campos) + "\n").encode("utf-8")
        fd = os.open(caminho, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, linha)
        finally:
            os.close(fd)
    except Exception:
        pass


def emitir(texto, log=None):
    """Escreve stdout e o log juntos; log = (caminho, [sub, projeto, modulo, codigo, schema])."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        sys.stdout.write(texto + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        # leitor fechou o pipe (ex.: `| head -1`); o log ainda e gravado. O dup2 evita
        # o "Exception ignored" do flush no encerramento do interpretador.
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass
    if log:
        _registrar(texto, log)
