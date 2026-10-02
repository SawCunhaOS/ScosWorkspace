"""Leitura dos fatos de .scos-map/: unico modulo que conhece o formato (AD-3)."""

import json
import re
import shutil
import subprocess
from pathlib import Path

from .modelo import ErroConsulta, Meta

SCHEMA_TESTADO = (2, 1)
ACAO_GERAR = "python3 ferramentas/scos-map/scos-map.py workspace ."
_SO_DISPONIBILIDADE = ("indisponivel", "nao_aplicavel")


def _ler_json(caminho, rotulo):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ErroConsulta(3, "%s ausente" % rotulo, ACAO_GERAR)
    except (OSError, ValueError):
        raise ErroConsulta(3, "%s ilegivel" % rotulo, ACAO_GERAR)


def _checar_schema(doc, avisos):
    testado = "%d.%d" % SCHEMA_TESTADO
    bruto = doc.get("schema_versao")
    try:
        versao = tuple(int(x) for x in str(bruto).split("."))[:2]
        if len(versao) != 2:
            raise ValueError
    except ValueError:
        raise ErroConsulta(4, "schema_versao ausente ou ilegivel (testado %s)"
                           % testado, ACAO_GERAR)
    if versao[0] != SCHEMA_TESTADO[0]:
        raise ErroConsulta(4, "schema_versao %s incompativel com o testado %s"
                           % (bruto, testado), ACAO_GERAR)
    if versao > SCHEMA_TESTADO:
        avisos.append("schema %s mais novo que o testado (%s)" % (bruto, testado))


def abrir_workspace(raiz):
    avisos = []
    ws = _ler_json(raiz / ".scos-map" / "workspace.json", "workspace.json")
    _checar_schema(ws, avisos)
    return ws, avisos


def _head_atual(repo):
    """HEAD do repo lendo .git/HEAD, sem subprocesso. None se ilegivel."""
    git = repo / ".git"
    try:
        txt = (git / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not txt.startswith("ref: "):
        return txt or None
    ref = txt[5:]
    try:
        return (git / ref).read_text(encoding="utf-8").strip() or None
    except OSError:
        pass
    try:
        for linha in (git / "packed-refs").read_text(encoding="utf-8").splitlines():
            if linha.endswith(" " + ref):
                return linha.split()[0]
    except OSError:
        pass
    return None


def _commits_desde(repo, head):
    if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{4,40}", head) \
            or not shutil.which("git"):
        return None
    try:
        p = subprocess.run(
            ["git", "-C", str(repo), "rev-list", "--count", "%s..HEAD" % head],
            capture_output=True, text=True, timeout=10)
        return int(p.stdout) if p.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


class Mapa:
    """Mapa de um projeto. Cada fato aberto entra em `lidos` (AD-1)."""

    def __init__(self, raiz, entrada, avisos, lidos):
        self.projeto = entrada["projeto"]
        self.raiz = raiz
        self.lidos = lidos
        self.avisos = list(avisos)
        indice = _ler_json(raiz / entrada["index"], "index.json de %s" % self.projeto)
        _checar_schema(indice, self.avisos)
        self.indice = indice
        self.head_mapa = (indice.get("git") or {}).get("head")
        repo = raiz / self.projeto
        self.head_atual = _head_atual(repo)
        self._commits = _commits_desde(repo, self.head_mapa) \
            if self.head_atual else None

    def _estado(self, do_indice):
        # disponibilidade > frescor do fato > frescor barato por .git/HEAD
        if do_indice in ("ausente", "indisponivel", "nao_aplicavel", "obsoleto"):
            return do_indice
        if not self.head_mapa or not self.head_atual:
            return "desconhecido"
        if self.head_atual.startswith(self.head_mapa):
            return "fresco"
        return "obsoleto"

    def _fato(self, modulo, nome):
        entrada = ((self.indice.get("modulos") or {}).get(modulo) or {}) \
            .get("fatos", {}).get(nome)
        if entrada is None or entrada.get("estado") == "ausente":
            raise ErroConsulta(3, "fato %s ausente para %s em %s"
                               % (nome, modulo, self.projeto), ACAO_GERAR)
        return self._abrir(nome, entrada)

    def _abrir(self, nome, entrada):
        """Le o fato JSON apontado por `entrada` e registra a Meta em `lidos`."""
        rel = "%s/.scos-map/%s" % (self.projeto, entrada["arquivo"])
        try:
            dados = _ler_json(self.raiz / rel, rel)
        except ErroConsulta:
            if entrada.get("estado") not in _SO_DISPONIBILIDADE:
                raise
            dados = {}
        if not isinstance(dados, dict):
            raise ErroConsulta(3, "%s com formato inesperado" % rel, ACAO_GERAR)
        comp = dados.get("completude") or {}
        self._meta(rel, nome, entrada.get("estado"), dados.get("confianca"),
                   completude=comp.get("nivel"), base=dados.get("base"),
                   desvios=dados.get("desvios"),
                   limitacoes=[str(x) for x in comp.get("limitacoes") or []],
                   motivo=entrada.get("motivo"))
        return dados

    def _meta(self, rel, nome, estado, confianca, **kw):
        self.lidos.append(Meta(
            fato=nome, arquivo=rel, confianca=confianca,
            estado=self._estado(estado),
            heads={self.projeto: self.head_mapa},
            commits_desde={self.projeto: self._commits},
            schema_versao=self.indice.get("schema_versao"),
            gerado=self.indice.get("gerado_em"),
            avisos=list(self.avisos), **kw))

    def _tabela(self, rel_mapa, nome, estado=None, confianca=None):
        """TSV com acesso por nome de coluna (AD-3); ausente = erro 3 citando o arquivo."""
        rel = "%s/.scos-map/%s" % (self.projeto, rel_mapa)
        try:
            linhas = (self.raiz / rel).read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            raise ErroConsulta(3, "%s ausente" % rel, ACAO_GERAR)
        except (OSError, ValueError):
            raise ErroConsulta(3, "%s ilegivel" % rel, ACAO_GERAR)
        if not linhas:
            raise ErroConsulta(3, "%s sem cabecalho" % rel, ACAO_GERAR)
        cab = linhas[0].split("\t")
        self._meta(rel, nome, estado, confianca)
        return [dict(zip(cab, l.split("\t"))) for l in linhas[1:] if l]

    def layout(self, modulo):
        return self._fato(modulo, "layout")

    def config(self, modulo):
        return self._fato(modulo, "config")

    def docs(self, modulo):
        return self._fato(modulo, "docs")

    def reactor(self):
        rel = self.indice.get("reactor") or "facts/_reactor.json"
        return self._abrir("reactor", {"arquivo": rel})

    def gerenciadas(self, modulo):
        rel = "facts/%s/gerenciadas.tsv" % modulo
        if rel not in (self.indice.get("tabelas") or {}):
            raise ErroConsulta(3, "gerenciadas.tsv ausente para %s em %s"
                               % (modulo, self.projeto), ACAO_GERAR)
        return self._tabela(rel, "gerenciadas")

    def arquivos(self):
        rel = (self.indice.get("arquivos") or {}).get("tsv") or "files.tsv"
        return self._tabela(rel, "arquivos")

    def modulos_com_deps(self):
        return [m for m, v in (self.indice.get("modulos") or {}).items()
                if "deps" in (v.get("fatos") or {})]

    def deps(self, modulo):
        """(diretas+transitivas do modulo, transitivas comuns): uniao sem parcial (AD-12)."""
        dados = self._fato(modulo, "deps")
        if self.lidos[-1].estado in _SO_DISPONIBILIDADE:
            return [], []
        pasta = (self.indice["modulos"][modulo]["fatos"]["deps"]["arquivo"]
                 .rsplit("/", 1)[0])
        meta = self.lidos[-1]
        corpo = self._tabela("%s/%s" % (pasta, dados.get("corpo") or "deps.tsv"),
                             "deps", meta.estado, meta.confianca)
        return corpo, self._transitivas_comuns(dados)

    def _transitivas_comuns(self, dados):
        # `fecho_comum_arquivo` do gerador e relativo a um diretorio que nao bate
        # com o do modulo aninhado: o caminho do projeto e fixo (AD-3)
        if not dados.get("fecho_comum_arquivo"):
            return []
        if not hasattr(self, "_comuns"):  # lido uma vez por consulta (AD-3)
            meta = self.lidos[-1]
            self._comuns = self._tabela("facts/_transitivas_comuns.tsv",
                                        "transitivas_comuns", meta.estado,
                                        meta.confianca)
        return self._comuns


class Workspace:
    """Fatos do workspace.json (escopo workspace). Estado = pior caso dos heads."""

    def __init__(self, raiz, ws, avisos, lidos):
        self.raiz, self.ws, self.avisos, self.lidos = raiz, ws, list(avisos), lidos

    def _estado_de(self, derivado):
        sujos = {p.get("projeto") for p in self.ws.get("projetos") or []
                 if (p.get("git") or {}).get("dirty")}
        estados = [] if derivado else ["desconhecido"]  # sem evidencia != fresco
        for repo, d in derivado.items():
            head = (d or {}).get("head")
            atual = _head_atual(self.raiz / repo)
            if not head or not atual:
                estados.append("desconhecido")
            elif not atual.startswith(head):
                estados.append("obsoleto")
            else:
                estados.append("desconhecido" if repo in sujos else "fresco")
        for e in ("obsoleto", "desconhecido"):
            if e in estados:
                return e
        return "fresco"

    def _registrar(self, nome, chave, derivado):
        """Le o fato `chave` do workspace.json e registra a Meta (estado = pior head)."""
        fato = self.ws.get(chave)
        if not isinstance(fato, dict):
            raise ErroConsulta(3, "fato %s ausente em workspace.json" % chave,
                               ACAO_GERAR)
        der = {r: d for r, d in derivado(fato).items() if r}
        comp = fato.get("completude") or {}
        sujo = any((p.get("git") or {}).get("dirty") for p in self.ws.get("projetos") or []
                   if p.get("projeto") in der)
        self.lidos.append(Meta(
            fato=nome, arquivo="workspace.json",
            confianca=fato.get("confianca"), estado=self._estado_de(der),
            completude=comp.get("nivel"), base=fato.get("base"),
            heads={r: (d or {}).get("head") for r, d in der.items()},
            commits_desde={r: _commits_desde(self.raiz / r, (d or {}).get("head"))
                           for r, d in der.items()},
            limitacoes=[str(x) for x in comp.get("limitacoes") or []]
            + (["mapa gerado com alteracoes nao commitadas"] if sujo else []),
            schema_versao=self.ws.get("schema_versao"),
            gerado=self.ws.get("gerado_em"), avisos=list(self.avisos)))
        return fato

    def conflitos(self):
        return self._registrar("conflitos", "conflitos_de_versao_cruzados",
                               lambda f: f.get("derivado_de") or {})

    def snapshots(self):
        # ponytail: um head por produtor (o do ultimo item); heads distintos no mesmo
        # produtor nao sao comparados. O gerador grava um head por repo.
        return self._registrar("snapshots", "snapshots_locais", lambda f: {
            i.get("produzido_por"): i.get("repo_local")
            for i in f.get("itens") or []})
