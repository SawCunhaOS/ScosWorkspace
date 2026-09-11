#!/usr/bin/env python3
"""
scos-map - indice estrutural de repositorios do ecossistema SCOS (SawCunhaOS).

Feito para o workspace SCOS: monorepos Maven multi-modulo, front-ends npm e
projetos irmaos lado a lado, mapeados para consumo por IA.

Filosofia: o mapa e um INDICE, nunca um substituto do codigo.
Ele diz onde achar, com que confianca e quao fresco esta o dado.

Tiers:
  1  barato, sempre roda    layout, config, deps (declaradas + resolvidas), docs
  2  exige bytecode         grafo de referencia entre tipos (jdeps), ciclos
  3  opt-in explicito       grafo de chamada entre metodos (java-callgraph)

Saida em .scos-map/ - JSON para dado heterogeneo, TSV para dado tabular.
Sem dependencias pip: apenas stdlib.

Uso:
    python scos-map.py scan .
    python scos-map.py scan . --tier 2
    python scos-map.py scan . --tier 3 --callgraph-jar ~/java-callgraph.jar
    python scos-map.py status .
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSAO = "2.1"     # contrato de formato lido pela skill de consulta
GERADOR_VERSAO = "2.1.0"  # implementacao; muda sem quebrar o contrato
OUT_DIR = ".scos-map"

# ---------------------------------------------------------------------------
# Constantes de classificacao
# ---------------------------------------------------------------------------

IGNORE_DIRS = {
    ".git", ".svn", ".hg", ".idea", ".vscode", "__pycache__", ".pytest_cache",
    "node_modules", "target", "build", "dist", "out", ".gradle", ".m2",
    "venv", ".venv", ".mypy_cache", ".ruff_cache", "coverage", OUT_DIR,
    ".next", ".nuxt", "vendor", ".terraform", "bin", "obj",
}

BINARY_EXT = {
    ".class", ".jar", ".war", ".ear", ".pyc", ".so", ".dll", ".dylib", ".exe",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".pdf",
    ".woff", ".woff2", ".ttf", ".eot", ".otf", ".mp3", ".mp4", ".avi", ".svg",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".db", ".sqlite", ".bin",
}

CODE_EXT = {
    ".java", ".kt", ".scala", ".groovy", ".py", ".js", ".jsx", ".ts", ".tsx",
    ".go", ".rs", ".rb", ".php", ".cs", ".c", ".h", ".cpp", ".hpp", ".swift",
    ".sql", ".sh", ".bash", ".vue", ".svelte",
}

DOC_EXT = {".md", ".markdown", ".rst", ".adoc", ".txt"}

CONFIG_NAME_RE = re.compile(
    r"^(application|bootstrap|logback|log4j2?|persistence|ehcache|liquibase)"
    r"([-_][\w-]+)?\.(ya?ml|properties|xml|conf)$", re.I)

CONFIG_EXTRA = {
    "docker-compose.yml", "docker-compose.yaml", "Dockerfile", "nginx.conf",
    "vite.config.ts", "vite.config.js", "next.config.js", "tsconfig.json",
    "webpack.config.js", "tailwind.config.js", "compose.yaml",
}

TEMPLATE_EXT = {".html", ".htm", ".ftl", ".vm", ".mustache", ".hbs", ".jsp", ".ejs"}
STYLE_EXT = {".css", ".scss", ".sass", ".less", ".styl"}

BUILD_NAMES = {
    "mvnw", "mvnw.cmd", "gradlew", "gradlew.bat", "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    "settings.gradle.kts", "package.json", "package-lock.json", "yarn.lock",
    "pnpm-lock.yaml", "Cargo.toml", "go.mod", "pyproject.toml",
    "requirements.txt", "Makefile",
}

ROLE_HINTS = {
    "controller": "controller", "controllers": "controller", "resource": "controller",
    "rest": "controller", "web": "controller", "api": "api",
    "service": "service", "services": "service", "usecase": "usecase",
    "usecases": "usecase",
    "repository": "repositorio", "repositories": "repositorio", "dao": "repositorio",
    "persistence": "repositorio", "infra": "infraestrutura",
    "infrastructure": "infraestrutura", "adapter": "adaptador",
    "domain": "dominio", "model": "dominio", "models": "dominio",
    "entity": "dominio", "entities": "dominio",
    "dto": "dto", "dtos": "dto", "request": "dto", "response": "dto",
    "mapper": "mapper", "mappers": "mapper", "converter": "mapper",
    "config": "config", "configuration": "config", "configs": "config",
    "exception": "excecao", "exceptions": "excecao", "handler": "handler",
    "util": "util", "utils": "util", "helper": "util", "common": "comum",
    "security": "seguranca", "auth": "seguranca",
    "event": "evento", "events": "evento", "listener": "evento",
    "client": "cliente", "clients": "cliente", "gateway": "gateway",
    "validator": "validacao", "validation": "validacao",
    "components": "componentes", "component": "componentes",
    "pages": "paginas", "page": "paginas", "views": "paginas",
    "hooks": "hooks", "store": "estado", "stores": "estado",
    "context": "estado", "contexts": "estado",
    "routes": "rotas", "router": "rotas", "layouts": "layout",
    "styles": "estilo", "assets": "assets", "public": "assets",
    "test": "teste", "tests": "teste", "__tests__": "teste", "spec": "teste",
}

# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def ts_to_date(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def run(cmd, cwd=None, timeout: int = 300):
    """Executa comando. Retorna (returncode, stdout, stderr). Nunca levanta."""
    try:
        p = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None, capture_output=True,
            text=True, timeout=timeout, errors="replace",
        )
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", "comando nao encontrado: %s" % cmd[0]
    except subprocess.TimeoutExpired:
        return 124, "", "timeout apos %ss" % timeout
    except Exception as e:  # noqa: BLE001
        return 1, "", str(e)


def have(tool: str) -> bool:
    from shutil import which
    return which(tool) is not None


SHA_LEN = 12  # 48 bits: folgado para dezenas de milhares de arquivos


def sha_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:SHA_LEN]


def read_text(path: Path, limit: int = 4_000_000):
    try:
        if path.stat().st_size > limit:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return None


TSV_SEP_RE = re.compile(r"[\t\r\n]+")


def tsv_clean(v) -> str:
    """Neutraliza separadores. Trocar por espaco, nunca remover: remover
    \r cola palavras ("c\rd" -> "cd") e corrompe o dado em silencio.
    """
    if v is None:
        return ""
    return TSV_SEP_RE.sub(" ", str(v))


def write_tsv(path: Path, header, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(header) + "\n")
        for r in rows:
            fh.write("\t".join(tsv_clean(c) for c in r) + "\n")
    return path.stat().st_size


def podar(obj):
    """Remove chave com valor vazio (None, [], {}, "").

    Campo vazio gravado e byte no disco e token no contexto sem informacao:
    'divergencias: []' nao diz nada que a ausencia da chave nao diga.
    False e 0 sao valores legitimos e ficam.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            v = podar(v)
            if v is None or v == [] or v == {} or v == "":
                continue
            out[k] = v
        return out
    if isinstance(obj, list):
        return [podar(v) for v in obj]
    return obj


def write_json(path: Path, obj, compacto=True) -> int:
    """JSON sem indentacao: o ganho e em contexto, nao so em disco.

    Quem precisar ler com olho humano abre numa IDE, que formata.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    sep = (",", ":") if compacto else (", ", ": ")
    path.write_text(
        json.dumps(podar(obj), ensure_ascii=False, separators=sep,
                   sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return path.stat().st_size


def write_json_se_mudou(path: Path, obj) -> tuple:
    """Nao reescreve fato inalterado.

    .scos-map/ e versionado; carimbo de tempo em fato que nao mudou produz
    diff toda regeracao e treina o leitor a ignorar o diff justamente onde
    ele e a informacao. Retorna (bytes, mudou).
    """
    novo = json.dumps(podar(obj), ensure_ascii=False,
                      separators=(",", ":"), sort_keys=False) + "\n"
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == novo:
                return path.stat().st_size, False
        except OSError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(novo, encoding="utf-8")
    return path.stat().st_size, True


def ask(question: str, default: bool, auto):
    """Pergunta ao usuario. auto=True/False pula a pergunta."""
    if auto is not None:
        return auto
    if not sys.stdin.isatty():
        return default
    try:
        r = input("%s [s/N] " % question).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    return r in {"s", "sim", "y", "yes"}


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------


def _ruido_do_mapa(caminho: str) -> bool:
    """Artefatos do proprio scos-map, que nao contam como arvore suja."""
    return (caminho.startswith(OUT_DIR + "/") or caminho == OUT_DIR
            or "/%s/" % OUT_DIR in caminho
            or caminho.endswith(".scos-map-cp.txt")
            or caminho.endswith(".scos-map-tree.txt")
            or "/target/" in caminho or caminho.startswith("target/"))


class GitInfo:
    """Metadados por arquivo extraidos do git numa unica varredura."""

    def __init__(self, root: Path):
        self.root = root
        self.available = False
        self.head = None
        self.branch = None
        self.dirty = False
        self.dirty_amostra = []
        self.blobs = {}
        self.last = {}
        self.churn = {}
        self.dirty_paths = set()
        self._load()

    def _load(self):
        rc, _, _ = run(["git", "rev-parse", "--git-dir"], cwd=self.root)
        if rc != 0:
            return
        self.available = True

        rc, out, _ = run(["git", "rev-parse", "HEAD"], cwd=self.root)
        self.head = out.strip()[:SHA_LEN] if rc == 0 and out.strip() else None
        rc, out, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.root)
        self.branch = out.strip() if rc == 0 else None
        # o proprio mapa (e os caches que ele gera em target/) nao sao codigo:
        # se contassem como sujeira, gerar o mapa degradaria o fato que o
        # mapa acabou de produzir.
        rc, out, _ = run(["git", "status", "--porcelain"], cwd=self.root)
        if rc == 0:
            reais = [l for l in out.splitlines()
                     if l[3:].strip() and not _ruido_do_mapa(l[3:].strip())]
            self.dirty = bool(reais)
            self.dirty_amostra = [l[3:].strip() for l in reais[:5]]
        else:
            self.dirty = False
            self.dirty_amostra = []

        rc, out, _ = run(["git", "ls-files", "-s"], cwd=self.root)
        if rc == 0:
            for line in out.splitlines():
                if "\t" not in line:
                    continue
                meta, path = line.split("\t", 1)
                parts = meta.split()
                if len(parts) >= 2:
                    self.blobs[path] = parts[1][:SHA_LEN]

        # ls-files devolve o blob do INDEX. Arquivo alterado no working tree
        # tem conteudo diferente e precisa de hash recalculado, senao o mapa
        # se declara fresco sobre codigo que ja mudou.
        rc, out, _ = run(["git", "status", "--porcelain", "-z"], cwd=self.root)
        if rc == 0 and out:
            sujos = []
            for entry in out.split("\0"):
                if len(entry) > 3:
                    sujos.append(entry[3:])
            sujos = [p for p in sujos if (self.root / p).is_file()]
            if sujos:
                self._rehash(sujos)

        cutoff = int(time.time()) - 90 * 86400
        rc, out, _ = run(
            ["git", "log", "--no-merges", "--format=\x01%H|%at|%an", "--name-only"],
            cwd=self.root, timeout=180,
        )
        if rc != 0:
            return
        sha = ts = author = None
        for line in out.splitlines():
            if line.startswith("\x01"):
                try:
                    s, ts_s, author = line[1:].split("|", 2)
                    ts = int(ts_s)
                    sha = s[:SHA_LEN]
                except ValueError:
                    sha = ts = author = None
                continue
            path = line.strip()
            if not path or sha is None:
                continue
            if path not in self.last:
                self.last[path] = (sha, ts, author)
            if ts >= cutoff:
                self.churn[path] = self.churn.get(path, 0) + 1

    def _rehash(self, paths):
        """git hash-object em lote: mantem o mesmo espaco de hash do git."""
        try:
            p = subprocess.run(
                ["git", "hash-object", "--stdin-paths"], cwd=str(self.root),
                input="\n".join(paths) + "\n", capture_output=True,
                text=True, timeout=120, errors="replace")
        except Exception:  # noqa: BLE001
            return
        if p.returncode != 0:
            return
        hashes = p.stdout.split()
        for path, h in zip(paths, hashes):
            self.blobs[path] = h[:SHA_LEN]
            self.dirty_paths.add(path)

    def meta(self, rel: str) -> dict:
        sha, ts, author = self.last.get(rel, (None, None, None))
        return {
            "blob": self.blobs.get(rel),
            "last_commit": sha,
            "last_modified": ts_to_date(ts) if ts else None,
            "author": author,
            "commits_90d": self.churn.get(rel, 0),
            "tracked": rel in self.blobs,
            "working_tree_sujo": rel in self.dirty_paths,
        }


# ---------------------------------------------------------------------------
# Multi-git: workspace com varios repositorios independentes
# ---------------------------------------------------------------------------


def find_git_roots(root: Path):
    """Acha todo repo git dentro do workspace, incluindo a propria raiz se
    for um. Necessario porque um workspace de varios projetos normalmente
    NAO e git em si - cada projeto (Flow, Foundation, Organization...) e."""
    roots = []
    if (root / ".git").exists():
        roots.append(root)
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        p = Path(dirpath)
        if p == root:
            continue
        if (p / ".git").exists():
            roots.append(p)
    return sorted(set(roots), key=lambda x: -len(str(x)))


def _empty_git_meta():
    return {"blob": None, "last_commit": None, "last_modified": None,
            "author": None, "commits_90d": 0, "tracked": False,
            "working_tree_sujo": False, "repo": None}


class MultiGit:
    """Agrega um GitInfo por repositorio encontrado no workspace. Arquivo
    fora de qualquer repo cai no fallback de hash calculado (ver scan_files).
    """

    def __init__(self, root: Path):
        self.root = root
        self._roots = find_git_roots(root)
        self._infos = {r: GitInfo(r) for r in self._roots}
        self.available = any(gi.available for gi in self._infos.values())
        top = self._infos.get(root)
        self.head = top.head if top else None
        self.branch = top.branch if top else None
        self.dirty = top.dirty if top else None
        self.multi_repo = len(self._roots) > 1 or (
            len(self._roots) == 1 and self._roots[0] != root)

    def _owner(self, abs_path: Path):
        for r in self._roots:
            try:
                abs_path.relative_to(r)
                return r
            except ValueError:
                continue
        return None

    def meta(self, rel_path: str, abs_path: Path):
        r = self._owner(abs_path)
        if r is None:
            return _empty_git_meta()
        gi = self._infos[r]
        if not gi.available:
            return _empty_git_meta()
        sub_rel = str(abs_path.relative_to(r)).replace(os.sep, "/")
        m = gi.meta(sub_rel)
        m["repo"] = str(r.relative_to(self.root)) if r != self.root else "_raiz"
        return m

    def repos_summary(self):
        out = []
        for r in self._roots:
            gi = self._infos[r]
            out.append({
                "path": str(r.relative_to(self.root)) if r != self.root else "",
                "head": gi.head, "branch": gi.branch, "dirty": gi.dirty,
            })
        return out


# ---------------------------------------------------------------------------
# Deteccao de ecossistemas e modulos
# ---------------------------------------------------------------------------


def parse_pom(path: Path):
    import xml.etree.ElementTree as ET
    text = read_text(path)
    if text is None:
        return None
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None

    def find(node, name):
        if node is None:
            return None
        for c in node:
            if strip_ns(c.tag) == name:
                return c
        return None

    def txt(node, name, default=None):
        c = find(node, name)
        return c.text.strip() if c is not None and c.text else default

    parent = find(root, "parent")
    data = {
        "groupId": txt(root, "groupId") or txt(parent, "groupId"),
        "artifactId": txt(root, "artifactId"),
        "version": txt(root, "version") or txt(parent, "version"),
        "packaging": txt(root, "packaging", "jar"),
        "parent": None,
        "modules": [],
        "properties": {},
        "dependencies": [],
        "managed": [],
    }
    if parent is not None:
        data["parent"] = {
            "groupId": txt(parent, "groupId"),
            "artifactId": txt(parent, "artifactId"),
            "version": txt(parent, "version"),
        }
    mods = find(root, "modules")
    if mods is not None:
        data["modules"] = [c.text.strip() for c in mods if c.text and c.text.strip()]
    props = find(root, "properties")
    if props is not None:
        for c in props:
            data["properties"][strip_ns(c.tag)] = (c.text or "").strip()

    def collect_deps(container):
        out = []
        deps = find(container, "dependencies")
        if deps is None:
            return out
        for d in deps:
            if strip_ns(d.tag) != "dependency":
                continue
            out.append({
                "groupId": txt(d, "groupId"),
                "artifactId": txt(d, "artifactId"),
                "version": txt(d, "version"),
                "scope": txt(d, "scope", "compile"),
                "type": txt(d, "type", "jar"),
            })
        return out

    data["dependencies"] = collect_deps(root)
    data["managed"] = collect_deps(find(root, "dependencyManagement"))
    return data


def _npm_workspaces(pkg: dict):
    ws = pkg.get("workspaces")
    if isinstance(ws, dict):
        ws = ws.get("packages", [])
    return ws if isinstance(ws, list) else []


def detect_modules(root: Path):
    """Descobre modulos e ecossistemas. Sempre inclui o pseudo-modulo _raiz."""
    modules = []
    ecos = set()

    seen = set()

    def walk_maven(pom_path: Path, rel: str, herdadas=None, geridas=None):
            if rel in seen:
                return
            seen.add(rel)
            pom = parse_pom(pom_path)
            if pom is None:
                return
            # properties e dependencyManagement descem do pai para os filhos
            props_ef = dict(herdadas or {})
            props_ef.update(pom.get("properties", {}))
            pom["_props_efetivas"] = props_ef
            ger_ef = dict(geridas or {})
            for d in pom.get("managed", []):
                ger_ef["%s:%s" % (d["groupId"], d["artifactId"])] = d.get("version")
            pom["_geridas_efetivas"] = ger_ef
            modules.append({
                "id": rel if rel else "_raiz",
                "path": rel,
                "ecossistema": "maven",
                "tipo": pom.get("packaging") or "jar",
                "artefato": "%s:%s" % (pom.get("groupId"), pom.get("artifactId")),
                "_pom": pom,
                "_pom_path": (rel + "/pom.xml") if rel else "pom.xml",
            })
            for m in pom.get("modules", []):
                child_rel = ("%s/%s" % (rel, m)).strip("/") if rel else m
                child_pom = root / child_rel / "pom.xml"
                if child_pom.exists():
                    walk_maven(child_pom, child_rel, props_ef, ger_ef)

    ecos_maven_visto = False
    root_pom = root / "pom.xml"
    if root_pom.exists():
        ecos.add("maven")
        ecos_maven_visto = True
        walk_maven(root_pom, "")

    # projetos maven IRMAOS (sem pai comum): cada pom.xml fora da arvore
    # ja percorrida vira um modulo proprio. E o caso de workspace com
    # varios repos independentes (ex.: Flow, Foundation, Organization).
    for pom_path in sorted(root.rglob("pom.xml")):
        parts = pom_path.relative_to(root).parts
        if any(p in IGNORE_DIRS for p in parts):
            continue
        rel = str(pom_path.parent.relative_to(root)).replace(os.sep, "/")
        rel = "" if rel == "." else rel
        if rel in seen:
            continue
        ecos.add("maven")
        walk_maven(pom_path, rel)

    def npm_module(pkg_path: Path, rel: str):
        text = read_text(pkg_path)
        if text is None:
            return
        try:
            pkg = json.loads(text)
        except json.JSONDecodeError:
            return
        ecos.add("npm")
        mid = rel if rel else "_raiz"
        existing = next((m for m in modules if m["id"] == mid), None)
        pkg_rel = (rel + "/package.json") if rel else "package.json"
        if existing:
            existing["ecossistema"] = existing["ecossistema"] + "+npm"
            existing["_pkg"] = pkg
            existing["_pkg_path"] = pkg_rel
        else:
            modules.append({
                "id": mid, "path": rel, "ecossistema": "npm",
                "tipo": "workspace" if pkg.get("workspaces") else "package",
                "artefato": pkg.get("name"),
                "_pkg": pkg, "_pkg_path": pkg_rel,
            })
        base = root / rel if rel else root
        for ws in _npm_workspaces(pkg):
            for child in sorted(base.glob(ws)):
                cp = child / "package.json"
                if cp.exists():
                    npm_module(cp, str(child.relative_to(root)).replace(os.sep, "/"))

    root_pkg = root / "package.json"
    if root_pkg.exists():
        npm_module(root_pkg, "")

    for pkg_path in sorted(root.rglob("package.json")):
        parts = pkg_path.relative_to(root).parts
        if any(p in IGNORE_DIRS for p in parts):
            continue
        rel = str(pkg_path.parent.relative_to(root)).replace(os.sep, "/")
        rel = "" if rel == "." else rel
        if not any(m["path"] == rel and "npm" in m["ecossistema"] for m in modules):
            npm_module(pkg_path, rel)

    if not modules:
        ecos.add("desconhecido")
    if not any(m["id"] == "_raiz" for m in modules):
        modules.insert(0, {
            "id": "_raiz", "path": "", "ecossistema": "desconhecido",
            "tipo": "nao_classificado", "artefato": None,
        })

    return modules, sorted(ecos)


def assign_module(rel_path: str, modules) -> str:
    """Modulo com o prefixo de caminho mais longo."""
    best, best_len = "_raiz", -1
    for m in modules:
        p = m["path"]
        if not p:
            continue
        if rel_path == p or rel_path.startswith(p + "/"):
            if len(p) > best_len:
                best, best_len = m["id"], len(p)
    return best


CONFIG_EXT = {".yml", ".yaml", ".properties", ".tf", ".tfvars", ".ini",
              ".conf", ".toml", ".xml"}
CONFIG_DOTFILES = {".gitignore", ".gitattributes", ".editorconfig",
                   ".dockerignore", ".npmrc", ".nvmrc", ".prettierrc"}


def classify(path: Path, name: str, ext: str) -> str:
    if name in BUILD_NAMES:
        return "build"
    if ext in BINARY_EXT:
        return "binario"
    if ext in DOC_EXT:
        return "doc"
    if ext == ".proto":
        return "contrato"
    if ext in TEMPLATE_EXT:
        return "template"
    if ext in STYLE_EXT:
        return "estilo"
    if (CONFIG_NAME_RE.match(name) or name in CONFIG_EXTRA
            or name in CONFIG_DOTFILES or name.startswith(".env")):
        return "config"
    if ext in CODE_EXT:
        return "codigo"
    if ext in CONFIG_EXT:
        return "config"
    return "nao_classificado"

# ---------------------------------------------------------------------------
# Varredura de arquivos
# ---------------------------------------------------------------------------


def scan_files(root: Path, modules, git: GitInfo):
    """Percorre o repo. Retorna lista de registros por arquivo."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in IGNORE_DIRS and not (d.startswith(".") and d != ".github")
        )
        for fname in sorted(filenames):
            p = Path(dirpath) / fname
            rel = str(p.relative_to(root)).replace(os.sep, "/")
            try:
                st = p.stat()
            except OSError:
                continue
            ext = p.suffix.lower()
            kind = classify(p, fname, ext)

            lines = None
            if kind != "binario" and st.st_size < 4_000_000:
                t = read_text(p)
                if t is not None:
                    lines = t.count("\n") + 1

            meta = git.meta(rel, p)
            if not meta["blob"]:
                # untracked: hash calculado, mtime do disco
                t = read_text(p) if kind != "binario" else None
                meta["blob"] = sha_text(t) if t is not None else None
                meta["last_modified"] = ts_to_date(int(st.st_mtime))
                meta["last_commit"] = None

            files.append({
                "path": rel, "abs": p, "bytes": st.st_size, "lines": lines,
                "ext": ext, "kind": kind,
                "module": assign_module(rel, modules),
                **meta,
            })
    return files


def files_tsv_rows(files):
    header = ["path", "blob", "bytes", "lines", "module", "kind",
              "last_commit", "last_modified", "author", "commits_90d", "tracked"]
    rows = []
    for f in files:
        rows.append([
            f["path"], f["blob"], f["bytes"], f["lines"], f["module"], f["kind"],
            f["last_commit"], f["last_modified"], f["author"], f["commits_90d"],
            "1" if f["tracked"] else "0",
        ])
    return header, rows


# vocabulario fechado de confianca (o mesmo no envelope e no desvio)
CONFIANCAS = {"alta", "resolvida", "declarada", "media", "parcial",
              "heuristica", "conflito"}


def fact_envelope(nome, modulo, base, confianca, derivado_de, extra=None,
                  completude=None, limitacoes=None, desvios=None, corpo=None):
    """Envelope de um fato.

    A confianca vale para o CASO COMUM e e declarada uma vez. Item que foge
    dela entra em `desvios` com a sua propria confianca e o motivo; item sem
    desvio herda o envelope. Nada mais e anotado - e o que mantem o mapa
    menor que o codigo que ele indexa.

    `gerado_em` NAO entra aqui: fica so no indice. Fato inalterado nao deve
    produzir diff (ver write_json_se_mudou).
    """
    # confianca None = fato SEM DADO (ausente/indisponivel/nao_aplicavel).
    # Nesse caso quem carrega a informacao e `estado`, dimensao separada:
    # nao ha nada sobre o que declarar confianca.
    if confianca is not None and confianca not in CONFIANCAS:
        raise ValueError("confianca invalida: %r" % confianca)
    env = {
        "fato": nome,
        "modulo": modulo,
        "base": base,
        "confianca": confianca,
        "derivado_de": derivado_de,
    }
    if completude or limitacoes:
        env["completude"] = {
            "nivel": completude or ("parcial" if limitacoes else "total"),
            "limitacoes": limitacoes or [],
        }
    if corpo:
        env["corpo"] = corpo
    if desvios:
        env["desvios"] = desvios
    if extra:
        env.update(extra)
    return env


def desvio(chave, valor, confianca, motivo, **extra):
    """Item que nao segue a confianca do envelope."""
    if confianca not in CONFIANCAS:
        raise ValueError("confianca invalida: %r" % confianca)
    d = {chave: valor, "confianca": confianca, "motivo": motivo}
    d.update(extra)
    return d


# ---------------------------------------------------------------------------
# Fato: layout
# ---------------------------------------------------------------------------

SPRING_ENTRY_RE = re.compile(
    r"@(SpringBootApplication|RestController|Controller|GrpcService|"
    r"Scheduled|EventListener|KafkaListener|RabbitListener)\b")
MAPPING_RE = re.compile(
    r'@(Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*)?"([^"]*)"')
PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.M)


def fact_layout(root: Path, module, files):
    mid = module["id"]
    mine = [f for f in files if f["module"] == mid]
    if not mine:
        return None

    base = module["path"]
    by_ext = {}
    for f in mine:
        by_ext[f["ext"] or "(sem)"] = by_ext.get(f["ext"] or "(sem)", 0) + 1

    # raizes de fonte
    roots = []
    for cand in ["src/main/java", "src/main/kotlin", "src/test/java",
                 "src/main/resources", "src/test/resources", "src", "app", "lib"]:
        p = (root / base / cand) if base else (root / cand)
        if p.is_dir():
            roots.append(cand)

    # pacote base = prefixo comum dos packages Java
    packages = []
    for f in mine:
        if f["ext"] == ".java":
            t = read_text(f["abs"])
            if t:
                m = PACKAGE_RE.search(t)
                if m:
                    packages.append(m.group(1))
    pacote_base = None
    if packages:
        parts = [p.split(".") for p in packages]
        common = []
        for i in range(min(len(p) for p in parts)):
            seg = {p[i] for p in parts}
            if len(seg) == 1:
                common.append(seg.pop())
            else:
                break
        pacote_base = ".".join(common) if common else None

    # areas: diretorios com papel inferido
    dir_counts = {}
    for f in mine:
        d = "/".join(f["path"].split("/")[:-1])
        dir_counts[d] = dir_counts.get(d, 0) + 1
    areas = []
    for d, n in sorted(dir_counts.items()):
        last = d.split("/")[-1].lower() if d else ""
        papel = ROLE_HINTS.get(last)
        if papel:
            areas.append({"caminho": d, "papel": papel, "arquivos": n})

    # entrypoints
    entry = []
    for f in mine:
        if f["ext"] not in {".java", ".kt", ".ts", ".tsx", ".js", ".jsx"}:
            continue
        t = read_text(f["abs"])
        if not t:
            continue
        if f["ext"] in {".java", ".kt"}:
            for m in SPRING_ENTRY_RE.finditer(t):
                kinds = {"SpringBootApplication": "app", "RestController": "http",
                         "Controller": "http", "GrpcService": "grpc",
                         "Scheduled": "agendado", "EventListener": "evento",
                         "KafkaListener": "mensageria", "RabbitListener": "mensageria"}
                e = {"path": f["path"], "tipo": kinds.get(m.group(1), "outro")}
                if e not in entry:
                    entry.append(e)
            for m in MAPPING_RE.finditer(t):
                e = {"path": f["path"], "tipo": "rota",
                     "rota": "%s %s" % (m.group(1).upper(), m.group(2))}
                if e not in entry:
                    entry.append(e)
        else:
            nm = f["path"].split("/")[-1]
            if nm in {"main.tsx", "main.ts", "index.tsx", "App.tsx", "App.jsx",
                      "main.jsx", "index.jsx", "page.tsx", "layout.tsx"}:
                entry.append({"path": f["path"], "tipo": "front_entry"})

    derivado = {f["path"]: f["blob"] for f in mine if f["kind"] == "codigo"}
    return fact_envelope(
        "layout", mid, "varredura de diretorio + regex de anotacao",
        "alta" if module["ecossistema"] != "desconhecido" else "heuristica",
        derivado,
        {
            "raizes_fonte": roots,
            "pacote_base": pacote_base,
            "arquivos": len(mine),
            "por_extensao": dict(sorted(by_ext.items(), key=lambda kv: -kv[1])),
            "por_tipo": _count(mine, "kind"),
            "areas": areas,
            "entrypoints": entry[:200],
        },
    )


def _count(items, key):
    out = {}
    for i in items:
        out[i[key]] = out.get(i[key], 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


# ---------------------------------------------------------------------------
# Fato: config (chaves e perfis, NUNCA valores)
# ---------------------------------------------------------------------------

PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][\w.\-]*)(?::[^}]*)?\}")
ENV_REF_RE = re.compile(r"\$\{?([A-Z][A-Z0-9_]{2,})\}?")
PROFILE_KEY_RE = re.compile(
    r"^\s*(?:spring\.config\.activate\.)?on-profile\s*:\s*(.+)$", re.M)
YAML_KEY_RE = re.compile(r"^([A-Za-z0-9_.\-]+)\s*:")


try:
    import yaml as _pyyaml           # dependencia OPCIONAL
except Exception:                    # noqa: BLE001
    _pyyaml = None


YAML_LIMITACOES = [
    "listas, ancoras, aliases e blocos multi-documento nao interpretados",
    "chave dentro de item de lista pode ser perdida ou aninhada errado",
]


def yaml_keys_pyyaml(text, max_depth=4):
    """Chaves via parser YAML de verdade. So os NOMES; valor nunca sai daqui."""
    docs = list(_pyyaml.safe_load_all(text))
    keys = []

    def walk(node, prefixo, nivel):
        if nivel > max_depth or not isinstance(node, dict):
            return
        for k, v in node.items():
            k = str(k)
            caminho = "%s.%s" % (prefixo, k) if prefixo else k
            if caminho not in keys:
                keys.append(caminho)
            if isinstance(v, dict):
                walk(v, caminho, nivel + 1)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        walk(item, caminho + "[]", nivel + 1)

    for d in docs:
        if isinstance(d, dict):
            walk(d, "", 1)
    return keys


def yaml_perfis_pyyaml(text):
    perfis = []
    for d in _pyyaml.safe_load_all(text):
        if not isinstance(d, dict):
            continue
        alvo = (((d.get("spring") or {}).get("config") or {})
                .get("activate") or {}).get("on-profile")
        if alvo is None:
            alvo = (d.get("spring") or {}).get("profiles")
        if isinstance(alvo, str):
            for pv in re.split(r"[,\s|]+", alvo.strip()):
                if pv and pv not in perfis:
                    perfis.append(pv)
        elif isinstance(alvo, list):
            for pv in alvo:
                if isinstance(pv, str) and pv not in perfis:
                    perfis.append(pv)
    return perfis


def yaml_keys(text, max_depth=4):
    keys, stack = [], []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.strip() == "---":
            stack = []
            continue
        indent = len(raw) - len(raw.lstrip())
        m = YAML_KEY_RE.match(raw.strip())
        if not m:
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, m.group(1)))
        if len(stack) <= max_depth:
            k = ".".join(x[1] for x in stack)
            if k not in keys:
                keys.append(k)
    return keys


def props_keys(text):
    keys = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or s.startswith("!"):
            continue
        if "=" in s:
            k = s.split("=", 1)[0].strip()
        elif ":" in s:
            k = s.split(":", 1)[0].strip()
        else:
            continue
        if k and k not in keys:
            keys.append(k)
    return keys


def fact_config(module, files):
    mid = module["id"]
    mine = [f for f in files if f["module"] == mid and f["kind"] == "config"]
    if not mine:
        return None

    itens, derivado, desvios = [], {}, []
    yaml_lidos = 0
    for f in mine:
        derivado[f["path"]] = f["blob"]
        nome = f["path"].split("/")[-1]
        t = read_text(f["abs"])
        item = {"path": nome and f["path"], "bytes": f["bytes"],
                "last_modified": f["last_modified"]}
        if t is None:
            item["nota"] = "ilegivel"
            itens.append(item)
            continue

        if f["ext"] in {".yml", ".yaml"}:
            if _pyyaml is not None:
                try:
                    item["chaves"] = yaml_keys_pyyaml(t)[:300]
                except Exception as e:  # noqa: BLE001
                    # YAML invalido ou recurso exotico: cai no varredor e
                    # registra o desvio deste arquivo, nao do fato inteiro
                    item["chaves"] = yaml_keys(t)[:300]
                    desvios.append(desvio(
                        "path", f["path"], "media",
                        "safe_load falhou (%s); chaves vieram da varredura "
                        "de indentacao" % str(e)[:80]))
            else:
                item["chaves"] = yaml_keys(t)[:300]
            yaml_lidos += 1
        elif f["ext"] in {".properties", ".conf"} or nome.startswith(".env"):
            item["chaves"] = props_keys(t)[:300]

        # perfis: por sufixo de nome e por declaracao interna
        perfis = []
        m = re.match(r"^application[-_]([\w-]+)\.(ya?ml|properties)$", nome, re.I)
        if m:
            perfis.append(m.group(1))
        if _pyyaml is not None and f["ext"] in {".yml", ".yaml"}:
            try:
                for pv in yaml_perfis_pyyaml(t):
                    if pv not in perfis:
                        perfis.append(pv)
            except Exception:  # noqa: BLE001
                pass
        for pm in PROFILE_KEY_RE.finditer(t):
            for pv in re.split(r"[,\s|]+", pm.group(1).strip().strip("\"'")):
                if pv and pv not in perfis:
                    perfis.append(pv)
        if perfis:
            item["perfis"] = perfis

        envs = sorted({m.group(1) for m in PLACEHOLDER_RE.finditer(t)})
        if envs:
            item["placeholders"] = envs[:100]
        itens.append(item)

    todos_perfis = sorted({p for i in itens for p in i.get("perfis", [])})

    # A confianca acompanha o analisador de fato usado. O varredor de
    # indentacao nao entende lista, ancora, alias nem multi-documento -
    # chamar isso de "alta" seria a etiqueta mais forte no parser mais fraco.
    if yaml_lidos == 0:
        conf = "alta"
        base = "leitura de chaves .properties (valores omitidos)"
        limitacoes = []
    elif _pyyaml is not None:
        conf = "alta"
        base = "PyYAML safe_load (valores omitidos)"
        limitacoes = []
    else:
        conf = "media"
        base = "varredura de indentacao (sem parser YAML; valores omitidos)"
        limitacoes = list(YAML_LIMITACOES)

    return fact_envelope(
        "config", mid, base, conf, derivado,
        extra={"aviso": "apenas nomes de chave e placeholders; "
                        "nenhum valor foi lido",
               "perfis_detectados": todos_perfis,
               "arquivos_yaml": yaml_lidos,
               "arquivos": itens},
        limitacoes=limitacoes,
        desvios=desvios,
    )


# ---------------------------------------------------------------------------
# Fato: tests
# ---------------------------------------------------------------------------

TEST_ROOTS = ["src/test/java", "src/test/kotlin", "src/test/resources",
              "src/integrationTest/java", "src/it/java", "src/testFixtures/java",
              "src/e2e", "src/test", "__tests__", "test", "tests"]

TEST_FILE_RE = re.compile(
    r"(Test|Tests|IT|ITCase|Spec)\.(java|kt)$|"
    r"\.(spec|test)\.(ts|tsx|js|jsx)$", re.I)

# framework -> (artefato no pom/package.json, import no fonte)
FRAMEWORKS = [
    ("JUnit 5", r"junit-jupiter", r"org\.junit\.jupiter"),
    ("JUnit 4", r"^junit$", r"org\.junit\.Test"),
    ("ArchUnit", r"archunit", r"com\.tngtech\.archunit"),
    ("Testcontainers", r"testcontainers", r"org\.testcontainers"),
    ("Mockito", r"mockito", r"org\.mockito"),
    ("AssertJ", r"assertj", r"org\.assertj"),
    ("WireMock", r"wiremock", r"com\.github\.tomakehurst|wiremock"),
    ("RestAssured", r"rest-assured", r"io\.restassured"),
    ("Spring Boot Test", r"spring-boot-starter-test", r"org\.springframework\.boot\.test"),
    ("Cucumber", r"cucumber", r"io\.cucumber"),
    ("Jest", r"^jest$", r"@jest|from ['\"]jest"),
    ("Vitest", r"^vitest$", r"from ['\"]vitest"),
    ("Testing Library", r"@testing-library", r"@testing-library"),
    ("Playwright", r"playwright", r"@playwright"),
]

ARCHUNIT_RULE_RE = re.compile(
    r"@ArchTest\b|ArchRuleDefinition|ArchRule\s+\w+|classes\(\)\s*\.that\(|"
    r"noClasses\(\)|layeredArchitecture\(|onionArchitecture\(", re.I)


def _tipo_de_teste(path, texto):
    """unit / integration / architecture / e2e - por caminho e conteudo."""
    p = path.lower()
    if "archtest" in p or "architecture" in p or (
            texto and ARCHUNIT_RULE_RE.search(texto)):
        return "architecture"
    if "/e2e" in p or ".e2e." in p:
        return "e2e"
    if ("integrationtest" in p or "/it/" in p or p.endswith("it.java")
            or "integration" in p
            or (texto and ("@SpringBootTest" in texto
                           or "Testcontainers" in texto))):
        return "integration"
    return "unit"


def fact_tests(root: Path, module, files, deps_fato=None):
    mid = module["id"]
    base_path = module["path"]

    raizes = []
    for cand in TEST_ROOTS:
        d = (root / base_path / cand) if base_path else (root / cand)
        if d.is_dir():
            raizes.append(cand)

    prefixos = tuple(("%s/%s/" % (base_path, r)) if base_path else (r + "/")
                     for r in raizes)
    # arquivo de teste conta por estar numa raiz conhecida OU por nome
    # (ex.: archtest/ da Foundation, que nao e raiz padrao do Maven)
    mine = [f for f in files
            if f["module"] == mid
            and ((prefixos and f["path"].startswith(prefixos))
                 or TEST_FILE_RE.search(f["path"].split("/")[-1]))]
    if not raizes and not mine:
        return None

    linhas, derivado, tipos = [], {}, {}
    frameworks_vistos, regras_arch = {}, []
    classes = 0
    for f in sorted(mine, key=lambda x: x["path"]):
        if f["kind"] == "binario":
            continue
        derivado[f["path"]] = f["blob"]
        texto = read_text(f["abs"]) if f["ext"] in {
            ".java", ".kt", ".ts", ".tsx", ".js", ".jsx"} else None
        nome = f["path"].split("/")[-1]
        eh_teste = bool(TEST_FILE_RE.search(nome))
        if eh_teste:
            classes += 1
        tipo = _tipo_de_teste(f["path"], texto) if eh_teste else "recurso"
        tipos[tipo] = tipos.get(tipo, 0) + 1

        alvo = ""
        if eh_teste:
            # relacao producao->teste e SEMPRE heuristica: casamento de nome
            # nunca vira certeza (ver limitacoes no envelope)
            alvo = re.sub(r"(Test|Tests|IT|ITCase|Spec)\.(java|kt)$", "", nome)
            alvo = re.sub(r"\.(spec|test)\.(ts|tsx|js|jsx)$", "", alvo)

        if texto:
            for fw, _art, imp in FRAMEWORKS:
                if re.search(imp, texto):
                    frameworks_vistos.setdefault(fw, "inferida")
            if tipo == "architecture" and ARCHUNIT_RULE_RE.search(texto):
                for m in re.finditer(r"(?:@ArchTest[\s\S]{0,200}?)?"
                                     r"(?:static\s+)?(?:final\s+)?"
                                     r"ArchRule\s+(\w+)", texto):
                    regras_arch.append({"path": f["path"], "regra": m.group(1)})

        linhas.append([f["path"], tipo, alvo, f["lines"] or "",
                       f["last_modified"] or "", f["commits_90d"]])

    # frameworks declarados no manifesto tem procedencia melhor que import
    if deps_fato:
        for d in deps_fato.get("diretas", []):
            art = d["ga"].split(":")[-1]
            for fw, art_re, _imp in FRAMEWORKS:
                if re.search(art_re, art):
                    frameworks_vistos[fw] = "declarada"

    frameworks = [
        {"nome": fw, "origem": org,
         "base": "pom.xml/package.json" if org == "declarada"
                 else "import no fonte"}
        for fw, org in sorted(frameworks_vistos.items())
    ]

    env = fact_envelope(
        "tests", mid, "varredura das raizes de teste do modulo", "alta",
        derivado,
        extra={
            "raizes": raizes,
            "arquivos": len(linhas),
            "classes": classes,
            "frameworks": frameworks,
            "por_tipo": tipos,
            "regras_arquiteturais": regras_arch[:100],
            "cobertura": {"estado": "nao_analisado",
                          "motivo": "nenhum relatorio JaCoCo/lcov foi lido"},
            "observacao_ausencia":
                "nenhum arquivo de teste identificado nas raizes analisadas"
                if classes == 0 else None,
        },
        completude="parcial",
        limitacoes=["apenas as raizes listadas foram varridas",
                    "a coluna 'alvo' e casamento de nome: relacao "
                    "producao->teste e heuristica, nunca confirmada",
                    "cobertura nao foi analisada - ausencia de teste aqui "
                    "nao significa codigo nao coberto"],
    )
    env["_linhas_tsv"] = linhas
    return env


# ---------------------------------------------------------------------------
# Fato: deps (declaradas + resolvidas, com delta)
# ---------------------------------------------------------------------------


def _maven_declared(pom):
    out = []
    managed = pom.get("_geridas_efetivas") or {}
    props = pom.get("_props_efetivas") or pom.get("properties", {})
    for d in pom.get("dependencies", []):
        ga = "%s:%s" % (d["groupId"], d["artifactId"])
        v = d.get("version")
        if v is None:
            if managed.get(ga):
                origem, v = "gerenciada:dependencyManagement", managed[ga]
            elif pom.get("parent"):
                origem = "herdada:parent/%s" % pom["parent"].get("artifactId")
            else:
                origem = "bom"
        elif v.startswith("${") and v.endswith("}"):
            prop = v[2:-1]
            resolvida = props.get(prop)
            origem = ("propriedade:%s" % prop) if resolvida else \
                     ("propriedade_nao_resolvida:%s" % prop)
            v = resolvida or v
        else:
            origem = "propria"
        out.append({"ga": ga, "versao_declarada": v, "origem": origem,
                    "scope": d.get("scope")})
    return out


def _maven_managed(pom):
    """dependencyManagement do proprio pom (BOM): versao fixada, nao uso."""
    props = dict(pom.get("_props_efetivas") or pom.get("properties", {}))
    props.setdefault("project.version", pom.get("version"))
    out = []
    for d in pom.get("managed", []):
        v, origem = d.get("version"), "propria"
        if v and v.startswith("${") and v.endswith("}"):
            prop = v[2:-1]
            origem = ("propriedade:%s" % prop) if props.get(prop) else \
                     ("propriedade_nao_resolvida:%s" % prop)
            v = props.get(prop) or v
        out.append({"ga": "%s:%s" % (d["groupId"], d["artifactId"]),
                    "versao": v, "origem": origem, "scope": d.get("scope")})
    return out


def parse_dependency_tree(texto, self_ga=None):
    """Parseia a saida textual do dependency:tree.

    Aceita tanto o arquivo puro quanto o stdout com prefixo [INFO].
    A primeira linha e o proprio artefato e nao entra na lista.
    None = nao ha arvore deste modulo; [] = arvore sem dependencias.
    """
    deps, raiz_vista = [], False
    for line in (texto or "").splitlines():
        s = line.strip()
        if s.startswith("[INFO]"):
            s = s[6:].strip()
        elif s.startswith("[WARNING]") or s.startswith("[ERROR]"):
            continue
        s = re.sub(r"^[\s|+\\`-]*", "", s).strip()
        if not s or " " in s.split(":")[0]:
            continue
        # g:a:tipo:versao[:scope] ou g:a:tipo:classifier:versao:scope
        parts = s.split()[0].split(":")
        if len(parts) < 4 or not re.match(r"^[\w.\-]+$", parts[0]):
            continue
        if not raiz_vista:
            raiz_vista = True
            # agregador rodado sem -N deixa no arquivo a arvore de um filho
            if self_ga and parts[1] != self_ga.split(":")[-1]:
                return None
            continue
        if len(parts) >= 6:
            versao, scope = parts[4], parts[5]
        else:
            versao, scope = parts[3], (parts[4] if len(parts) > 4 else None)
        deps.append({"ga": "%s:%s" % (parts[0], parts[1]),
                     "versao_resolvida": versao, "scope": scope})
    return deps if raiz_vista else None


def parse_effective_pom(texto):
    """Le o XML do help:effective-pom -> {ga: {versao, scope}}.

    O effective-pom ja traz heranca de parent, properties e
    dependencyManagement (inclusive de BOM importado) resolvidos pelo
    proprio Maven - e o caminho que parse_pom reimplementa e pode errar em
    silencio.
    """
    import xml.etree.ElementTree as ET
    try:
        raiz = ET.fromstring(texto)
    except ET.ParseError:
        return None

    def filhos(node, nome):
        return [c for c in node if strip_ns(c.tag) == nome]

    def txt(node, nome, default=None):
        for c in node:
            if strip_ns(c.tag) == nome:
                return (c.text or "").strip() or default
        return default

    # 'mvn help:effective-pom' na raiz de um reator emite <projects> com
    # varios <project>; por modulo emite um so.
    projetos = ([raiz] if strip_ns(raiz.tag) == "project"
                else filhos(raiz, "project"))
    out = {}
    for proj in projetos:
        for deps in filhos(proj, "dependencies"):
            for d in filhos(deps, "dependency"):
                g, a = txt(d, "groupId"), txt(d, "artifactId")
                if not g or not a:
                    continue
                out["%s:%s" % (g, a)] = {
                    "versao": txt(d, "version"),
                    "scope": txt(d, "scope", "compile"),
                }
    return out


def _maven_effective(root: Path, module, offline=True, timeout=240):
    """Fonte primaria das versoes diretas quando o mvn existe."""
    mod_dir = root / module["path"] if module["path"] else root
    alvo = mod_dir / "target" / ".scos-map-effective.xml"
    pom_f = mod_dir / "pom.xml"

    if alvo.exists() and pom_f.exists():
        try:
            if alvo.stat().st_mtime >= pom_f.stat().st_mtime:
                d = parse_effective_pom(read_text(alvo) or "")
                if d:
                    return d, None
        except OSError:
            pass

    if not have("mvn"):
        return None, "mvn nao encontrado e sem effective-pom em cache"
    alvo.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["mvn", "-B", "-q", "help:effective-pom", "-Doutput=%s" % alvo]
    if offline:
        cmd.insert(1, "-o")
    rc, out, err = run(cmd, cwd=mod_dir, timeout=timeout)
    if not alvo.exists():
        return None, "help:effective-pom nao gerou saida (rc=%s)" % rc
    d = parse_effective_pom(read_text(alvo) or "")
    if not d:
        return None, "effective-pom ilegivel"
    return d, None


def _maven_resolved(root: Path, module, offline=True, timeout=240):
    """mvn dependency:tree. NAO compila - so resolve o grafo."""
    mod_dir = root / module["path"] if module["path"] else root
    self_ga = None
    if module.get("_pom"):
        self_ga = "%s:%s" % (module["_pom"].get("groupId"),
                             module["_pom"].get("artifactId"))

    # a propriedade do dependency:tree e outputFile (mdep.outputFile e do
    # build-classpath); com -q e sem arquivo a arvore nao sai em lugar nenhum.
    alvo = mod_dir / "target" / ".scos-map-tree.txt"
    alvo.parent.mkdir(parents=True, exist_ok=True)

    # arvore ja resolvida e mais nova que o pom: reaproveita em vez de
    # pagar outro dependency:tree. Pom mais novo invalida o cache.
    pom_f = mod_dir / "pom.xml"
    if alvo.exists() and pom_f.exists():
        try:
            if alvo.stat().st_mtime >= pom_f.stat().st_mtime:
                deps = parse_dependency_tree(read_text(alvo), self_ga)
                if deps is not None:
                    return deps, None
        except OSError:
            pass
    if not have("mvn"):
        return None, "mvn nao encontrado no PATH e sem arvore em cache"
    # -N: num agregador, cada filho do sub-reator sobrescreveria o outputFile
    cmd = ["mvn", "-B", "-q", "-N", "dependency:tree", "-DoutputType=text",
           "-DoutputFile=%s" % alvo]
    if offline:
        cmd.insert(1, "-o")
    rc, out, err = run(cmd, cwd=mod_dir, timeout=timeout)

    texto = read_text(alvo) if alvo.exists() else None
    deps = parse_dependency_tree(texto, self_ga)

    if deps is None:
        # fallback: sem -q e sem arquivo, lendo a arvore do stdout
        cmd2 = ["mvn", "-B", "-N", "dependency:tree", "-DoutputType=text"]
        if offline:
            cmd2.insert(1, "-o")
        rc2, out2, err2 = run(cmd2, cwd=mod_dir, timeout=timeout)
        deps = parse_dependency_tree(out2, self_ga)
        if deps is None:
            motivo = "dependency:tree nao produziu arvore (rc=%s/%s)" % (rc, rc2)
            if offline:
                motivo += "; se o ~/.m2 estiver incompleto tente --online"
            return None, motivo
    return deps, None


def _npm_declared(pkg):
    out = []
    for campo, escopo in (("dependencies", "prod"), ("devDependencies", "dev"),
                          ("peerDependencies", "peer")):
        for nome, spec in (pkg.get(campo) or {}).items():
            out.append({"ga": nome, "versao_declarada": spec,
                        "origem": "propria", "scope": escopo})
    return out


def _npm_resolved(root: Path, module):
    base = root / module["path"] if module["path"] else root
    lock = base / "package-lock.json"
    if not lock.exists():
        lock = root / "package-lock.json"
    if not lock.exists():
        return None, "package-lock.json nao encontrado"
    t = read_text(lock)
    if t is None:
        return None, "lockfile ilegivel"
    try:
        data = json.loads(t)
    except json.JSONDecodeError:
        return None, "lockfile invalido"
    deps = []
    for path, info in (data.get("packages") or {}).items():
        if not path.startswith("node_modules/"):
            continue
        nome = path.split("node_modules/")[-1]
        deps.append({"ga": nome, "versao_resolvida": info.get("version"),
                     "scope": "dev" if info.get("dev") else "prod"})
    if not deps:
        for nome, info in (data.get("dependencies") or {}).items():
            deps.append({"ga": nome, "versao_resolvida": info.get("version"),
                         "scope": "dev" if info.get("dev") else "prod"})
    return deps, None


def fact_deps(root: Path, module, files, offline=True):
    eco = module["ecossistema"]
    declaradas, resolvidas, motivo, fonte, derivado = [], None, None, [], {}
    desvios, limitacoes, gerenciadas = [], [], []

    if "maven" in eco and module.get("_pom"):
        declaradas += _maven_declared(module["_pom"])
        gerenciadas = _maven_managed(module["_pom"])
        fonte.append("pom.xml")
        p = module["_pom_path"]
        derivado[p] = next((f["blob"] for f in files if f["path"] == p), None)

        # Precedencia: effective-pom > dependency:tree > parse_pom.
        # parse_pom reimplementa heranca, properties e BOM importado; o
        # effective-pom e o proprio Maven respondendo. Divergencia entre os
        # dois NAO e resolvida em silencio - vira desvio de conflito.
        efetivas, motivo_ef = _maven_effective(root, module, offline=offline)
        if efetivas:
            fonte.insert(0, "mvn help:effective-pom")
            for d in declaradas:
                ef = efetivas.get(d["ga"])
                if not ef or not ef.get("versao"):
                    continue
                minha = d.get("versao_declarada")
                bateu = (minha is not None
                         and not str(minha).startswith("${")
                         and str(minha) == str(ef["versao"]))
                if minha and not str(minha).startswith("${") and not bateu:
                    desvios.append(desvio(
                        "ga", d["ga"], "conflito",
                        "parse_pom deduziu %s; effective-pom diz %s"
                        % (minha, ef["versao"]),
                        versao_parse_pom=minha,
                        versao_effective_pom=ef["versao"]))
                # o Maven ganha: e ele quem constroi.
                d["versao_declarada"] = ef["versao"]
                # o effective-pom confirma a VERSAO, nao a origem que o
                # parse_pom supos - manter "confirmada" so quando bateram.
                base_origem = (d.get("origem") or "").split(" (")[0]
                d["origem"] = ("%s (confirmada por effective-pom)" % base_origem
                               if bateu and base_origem else "effective-pom")
        elif motivo_ef:
            limitacoes.append(
                "versoes diretas vieram de parse_pom, nao do effective-pom "
                "(%s): heranca, properties e BOM importado foram deduzidos "
                "e podem divergir do que o Maven resolve" % motivo_ef)

        resolvidas, motivo = _maven_resolved(root, module, offline=offline)
        if resolvidas is not None:
            fonte.append("mvn dependency:tree")
    if "npm" in eco and module.get("_pkg"):
        declaradas += _npm_declared(module["_pkg"])
        fonte.append("package.json")
        p = module["_pkg_path"]
        derivado[p] = next((f["blob"] for f in files if f["path"] == p), None)
        r, m2 = _npm_resolved(root, module)
        if r is not None:
            resolvidas = (resolvidas or []) + r
            fonte.append("package-lock.json")
            lock_rel = ((module["path"] + "/") if module["path"] else "") + \
                "package-lock.json"
            lock_blob = next((f["blob"] for f in files
                              if f["path"] == lock_rel), None)
            if lock_blob is None:
                lock_rel = "package-lock.json"
                lock_blob = next((f["blob"] for f in files
                                  if f["path"] == lock_rel), None)
            if lock_blob:
                derivado[lock_rel] = lock_blob
        else:
            motivo = motivo or m2

    if not declaradas and not gerenciadas and resolvidas is None:
        return None

    res_map, scope_map = {}, {}
    for d in (resolvidas or []):
        res_map.setdefault(d["ga"], d["versao_resolvida"])
        scope_map.setdefault(d["ga"], d.get("scope"))

    itens, divergencias = [], []
    for d in declaradas:
        rv = res_map.get(d["ga"])
        item = dict(d)
        item["versao_resolvida"] = rv
        dv = d.get("versao_declarada")
        if rv and dv and dv != rv and not dv.startswith("${"):
            item["divergente"] = True
            divergencias.append({"ga": d["ga"], "declarada": dv, "resolvida": rv})
        itens.append(item)

    declared_ga = {d["ga"] for d in declaradas}
    transitivas = [
        {"ga": g, "versao_resolvida": v, "scope": scope_map.get(g)}
        for g, v in sorted(res_map.items()) if g not in declared_ga
    ]

    confianca = "resolvida" if resolvidas is not None else "declarada"
    env = fact_envelope("deps", module["id"], " + ".join(fonte) or "n/d",
                        confianca, derivado,
                        extra={
                            "diretas": itens,
                            "divergencias": divergencias,
                            "transitivas": transitivas[:500],
                            "transitivas_total": len(transitivas),
                            "gerenciadas": gerenciadas,
                        },
                        completude="parcial" if limitacoes else "total",
                        limitacoes=limitacoes,
                        desvios=desvios)
    if resolvidas is None and motivo:
        env["resolucao_indisponivel"] = motivo
    return env


# ---------------------------------------------------------------------------
# Fato: docs (indice navegavel, nunca o conteudo)
# ---------------------------------------------------------------------------

MD_HEADER_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.M)
PROTO_SVC_RE = re.compile(r"^\s*service\s+(\w+)", re.M)
PROTO_RPC_RE = re.compile(r"^\s*rpc\s+(\w+)\s*\(", re.M)


# subtipo -> (regex de caminho, regex do titulo/conteudo)
DOC_SUBTIPOS = [
    ("adr",       r"(^|/)(adr|decisions?|architecture-decisions?)(/|$)|(^|/)\d{3,4}[-_]",
                  r"^#\s*ADR[\s-]|^##?\s*(Decis[aã]o|Decision)\b"),
    ("prd",       r"(^|/)prd(s)?(/|$)|prd[-_.]",
                  r"^#\s*PRD\b|^##?\s*(Requisitos|Requirements)\b"),
    ("epic",      r"(^|/)epics?(/|$)|epic[-_.]", r"^#\s*[EÉ]pico\b|^#\s*Epic\b"),
    ("story",     r"(^|/)stories(/|$)|(^|/)story[-_.]|(^|/)us[-_]\d+",
                  r"^#\s*(User\s+)?Stor(y|ia)\b|^##?\s*Crit[eé]rios de aceite"),
    ("spec",      r"(^|/)specs?(/|$)|spec[-_.]|(^|/)openapi|swagger",
                  r"^#\s*(Spec|Especifica)"),
    ("runbook",   r"(^|/)runbooks?(/|$)|runbook[-_.]|(^|/)ops(/|$)",
                  r"^#\s*Runbook\b|^##?\s*(Procedimento|Rollback)\b"),
    ("arquitetura", r"(^|/)arch(itecture)?(/|$)|arquitetura",
                   r"^#\s*Arquitetura\b|^#\s*Architecture\b"),
    ("changelog", r"(^|/)CHANGELOG", r"^#\s*Changelog\b"),
    ("readme",    r"(^|/)README", None),
    ("contrato",  r"\.proto$", None),
]

BMAD_DIR_RE = re.compile(r"(^|/)_bmad-output(/|$)", re.I)
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
STATUS_RE = re.compile(
    r"^\s*(?:status|situacao|situa[cç][aã]o)\s*:\s*(.+?)\s*$", re.M | re.I)


def classificar_doc(path, texto):
    """Subtipo do documento por caminho e por titulo.

    Caminho tem precedencia: quem organiza em docs/adr/ ja declarou a
    intencao. O conteudo so decide quando o caminho nao diz nada.
    """
    for nome, path_re, _ in DOC_SUBTIPOS:
        if path_re and re.search(path_re, path, re.I):
            return nome, "caminho"
    if texto:
        cabeca = "\n".join(texto.splitlines()[:40])
        for nome, _p, cont_re in DOC_SUBTIPOS:
            if cont_re and re.search(cont_re, cabeca, re.M | re.I):
                return nome, "titulo"
    return "outro", None


def doc_frontmatter(texto):
    """Le status/owner do frontmatter YAML, se houver. Nunca inventa."""
    if not texto:
        return {}
    m = FRONTMATTER_RE.match(texto)
    if not m:
        return {}
    bloco = m.group(1)
    out = {}
    st = STATUS_RE.search(bloco)
    if st:
        out["status"] = st.group(1).strip().strip("\"'")
    for chave in ("owner", "epic", "epico", "story", "versao", "version"):
        mm = re.search(r"^\s*%s\s*:\s*(.+?)\s*$" % chave, bloco,
                       re.M | re.I)
        if mm:
            out[chave.replace("epico", "epic")] = mm.group(1).strip().strip("\"'")
    return out


def fact_docs(module, files, all_module_ids):
    mid = module["id"]
    mine = [f for f in files if f["module"] == mid
            and f["kind"] in {"doc", "contrato"}]
    if not mine:
        return None

    itens, derivado, subtipos = [], {}, {}
    for f in mine:
        derivado[f["path"]] = f["blob"]
        t = read_text(f["abs"])
        item = {
            "path": f["path"], "bytes": f["bytes"],
            "last_modified": f["last_modified"],
            "last_commit": f["last_commit"],
            "commits_90d": f["commits_90d"],
        }
        if t is None:
            itens.append(item)
            continue

        if f["ext"] in DOC_EXT:
            headers = MD_HEADER_RE.findall(t)
            if headers:
                item["titulo"] = headers[0][1]
                item["secoes"] = [h[1] for h in headers[1:]][:40]
            subtipo, por = classificar_doc(f["path"], t)
            item["subtipo"] = subtipo
            if por:
                item["subtipo_por"] = por
            item.update(doc_frontmatter(t))
            if BMAD_DIR_RE.search(f["path"]):
                item["gerado_por"] = "bmad"
            subtipos[subtipo] = subtipos.get(subtipo, 0) + 1
            citados = sorted({
                m for m in all_module_ids
                if m not in {"_raiz"} and re.search(
                    r"\b%s\b" % re.escape(m.split("/")[-1]), t, re.I)
            })
            if citados:
                item["modulos_citados"] = citados
        elif f["ext"] == ".proto":
            item["services"] = PROTO_SVC_RE.findall(t)
            item["rpcs"] = PROTO_RPC_RE.findall(t)[:60]
        itens.append(item)

    bmad = [i for i in itens if i.get("gerado_por") == "bmad"]
    return fact_envelope(
        "docs", mid, "cabecalhos markdown / frontmatter / declaracoes proto",
        "alta", derivado,
        extra={"aviso": "indice apenas - abra o arquivo pelo caminho para "
                        "ler o conteudo",
               "por_subtipo": dict(sorted(subtipos.items(),
                                          key=lambda kv: -kv[1])),
               "gerados_por_bmad": len(bmad),
               "itens": itens},
        completude="parcial",
        limitacoes=["subtipo vem do caminho ou do titulo, nao de leitura "
                    "semantica: documento fora de convencao cai em 'outro'",
                    "`status` so aparece quando existe no frontmatter - "
                    "ausencia nao significa rascunho nem aprovado"],
    )

# ---------------------------------------------------------------------------
# Tier 2: bytecode (jdeps)
# ---------------------------------------------------------------------------


def classes_dir(root: Path, module):
    base = root / module["path"] if module["path"] else root
    for cand in ["target/classes", "build/classes/java/main", "out/production/classes"]:
        p = base / cand
        if p.is_dir() and any(p.rglob("*.class")):
            return p
    return None


def bytecode_freshness(root: Path, module, cdir: Path):
    """Compara mtime do bytecode com o do fonte."""
    base = root / module["path"] if module["path"] else root
    src = base / "src/main/java"
    if not src.is_dir():
        src = base / "src"
    newest_src = 0.0
    for f in src.rglob("*.java") if src.is_dir() else []:
        try:
            newest_src = max(newest_src, f.stat().st_mtime)
        except OSError:
            pass
    newest_cls = 0.0
    for f in cdir.rglob("*.class"):
        try:
            newest_cls = max(newest_cls, f.stat().st_mtime)
        except OSError:
            pass
    if newest_cls == 0:
        return "ausente", None
    estado = "obsoleto" if newest_src > newest_cls else "fresco"
    return estado, datetime.fromtimestamp(newest_cls, timezone.utc).isoformat(
        timespec="seconds").replace("+00:00", "Z")


def assinatura_classes(cdir: Path):
    """Impressao digital do bytecode compilado.

    O hash dos fontes de src/main nao cobre codigo GERADO (OpenAPI, MapStruct,
    protobuf), que nasce em target/generated-sources e nunca entra na
    varredura. Sem isso, regerar o spec muda as classes e o mapa continua se
    declarando fresco.
    """
    itens = []
    for cf in sorted(cdir.rglob("*.class")):
        try:
            itens.append("%s:%d" % (cf.relative_to(cdir), cf.stat().st_size))
        except OSError:
            continue
    return {"classes": len(itens), "sha": sha_text("\n".join(itens))}


def bytecode_major(cdir: Path):
    for f in cdir.rglob("*.class"):
        try:
            with f.open("rb") as fh:
                head = fh.read(8)
            if len(head) >= 8 and head[:4] == b"\xca\xfe\xba\xbe":
                return int.from_bytes(head[6:8], "big")
        except OSError:
            continue
    return None


def maven_classpath(root: Path, module, offline=True, timeout=240):
    mod_dir0 = root / module["path"] if module["path"] else root
    cache = mod_dir0 / "target" / ".scos-map-cp.txt"
    if cache.exists():
        # reaproveita o classpath ja resolvido numa execucao anterior
        txt = (read_text(cache) or "").strip()
        if txt:
            return txt, None
    if not have("mvn"):
        return None, "mvn nao encontrado"
    mod_dir = root / module["path"] if module["path"] else root
    out_file = mod_dir / "target" / ".scos-map-cp.txt"
    cmd = ["mvn", "-q", "-B", "dependency:build-classpath",
           "-Dmdep.outputFile=%s" % out_file]
    if offline:
        cmd.insert(1, "-o")
    rc, _, err = run(cmd, cwd=mod_dir, timeout=timeout)
    if rc != 0 or not out_file.exists():
        return None, "build-classpath falhou (rc=%s)" % rc
    cp = read_text(out_file) or ""
    return cp.strip(), None


JDEPS_EDGE_RE = re.compile(r"^\s+(\S+)\s+->\s+(\S+)\s*(.*)$")
JDEPS_ERR_RE = re.compile(r"^\s*Error:\s*(.+)$", re.M)


def jdeps_errors(out, err):
    """jdeps aborta com 'Error:' no STDOUT e rc!=0, sem emitir aresta."""
    return [m.group(1).strip()
            for m in JDEPS_ERR_RE.finditer((out or "") + "\n" + (err or ""))]


# artefatos que por natureza NAO deixam rastro no bytecode do modulo
AGREGADORES_RE = re.compile(
    r"(^|-)(starter|starters|bom|dependencies|parent)(-|$)", re.I)
PROCESSADORES = {
    "lombok", "mapstruct-processor", "auto-service", "immutables",
    "dagger-compiler", "micronaut-inject-java", "spring-boot-configuration-processor",
    "querydsl-apt", "jakarta.annotation-api",
}
SCOPES_FORA_DO_MAIN = {"test", "provided", "system"}

# bibliotecas que atuam em runtime por configuracao, nao por chamada no codigo
RUNTIME_POR_NATUREZA_RE = re.compile(
    r"(logback|logstash|log4j|slf4j-simple|jul-to-slf4j|"
    r"postgresql|mysql-connector|mariadb-java-client|ojdbc|mssql-jdbc|h2|"
    r"flyway|liquibase|micrometer-registry|opentelemetry-exporter|"
    r"caffeine|hibernate-validator|jaxb-runtime|jakarta\.el)", re.I)


def jar_para_artefato(jarname, conhecidos=()):
    """spring-data-redis-4.1.1.jar -> spring-data-redis

    Artefato conhecido vence a regex: hypersistence-utils-hibernate-71-3.15.5.jar.
    """
    base = jarname.split("/")[-1]
    if base.endswith(".jar"):
        base = base[:-4]
    casados = [a for a in conhecidos
               if base.startswith(a + "-") and base[len(a) + 1:][:1].isdigit()]
    if casados:
        return max(casados, key=len)
    return re.sub(r"-\d[\w.\-]*$", "", base)


DESCRITOR_RE = re.compile(rb"L([A-Za-z_$][\w$]*(?:/[\w$]+)+);")


def deps_em_descritores(cdir, candidatas, m2):
    """{artefato: refs} das (ga, versao) candidatas citadas so em descritor.

    jdeps nao reporta classe citada dentro de anotacao (repositoryBaseClass =
    X.class): no .class ela e so um Utf8 do constant pool.
    """
    citadas = {}
    for cf in cdir.rglob("*.class"):
        try:
            for nome in set(DESCRITOR_RE.findall(cf.read_bytes())):
                citadas[nome] = citadas.get(nome, 0) + 1
        except OSError:
            continue
    out = {}
    for ga, versao in candidatas:
        jar, _mt = _jar_do_snapshot(m2, ga, str(versao or ""))
        if jar is None:
            continue
        try:
            with zipfile.ZipFile(jar) as z:
                n = sum(citadas.get(e[:-6].encode(), 0)
                        for e in z.namelist() if e.endswith(".class"))
        except (OSError, zipfile.BadZipFile):
            continue
        if n:
            out[ga.split(":")[-1]] = n
    return out


GERA_CODIGO_RE = re.compile(r"generat|protoc|xjc|wsdl2java", re.I)


def gera_classes(root, module, files):
    """Fonte JVM de producao, .proto ou plugin gerador de codigo no pom."""
    if any(f["module"] == module["id"] and f["ext"] in {".java", ".kt", ".proto"}
           and not TEST_PATH_RE.search(f["path"]) for f in files):
        return True
    pom = read_text(root / module["_pom_path"]) if module.get("_pom_path") else None
    return bool(GERA_CODIGO_RE.search(pom or ""))


def classificar_deps(declaradas, usados_art, resolvidas_art, refs=None,
                     internos_reator=None, modulo_de_boot=False):
    """Separa sinal de ruido na comparacao declarado x usado.

    O heuristico ingenuo (declarado menos usado) gera quase so falso
    positivo em projeto Spring: starter nao tem classe propria, dependencia
    de teste nao entra em target/classes, e processador de anotacao some
    depois de compilar.
    """
    via_transitiva, ausentes_do_pom = [], []
    sem_uso, ignoradas = [], []

    decl_art = {}
    for d in declaradas:
        art = d["ga"].split(":")[-1]
        decl_art[art] = d

    refs = refs or {}
    for art in sorted(usados_art):
        if art in decl_art:
            continue
        item = {"artefato": art, "referencias": refs.get(art, 0)}
        if resolvidas_art is None:
            via_transitiva.append(item)
        elif art in resolvidas_art:
            via_transitiva.append(item)
        else:
            ausentes_do_pom.append(item)
    # quem o codigo mais usa e quem mais dói se a transitiva sumir
    via_transitiva.sort(key=lambda x: -x["referencias"])
    ausentes_do_pom.sort(key=lambda x: -x["referencias"])

    for art, d in sorted(decl_art.items()):
        if art in usados_art:
            continue
        scope = (d.get("scope") or "compile").lower()
        if scope in SCOPES_FORA_DO_MAIN:
            ignoradas.append({"artefato": art, "motivo": "scope %s" % scope})
        elif art in PROCESSADORES:
            ignoradas.append({"artefato": art,
                              "motivo": "processador de anotacao: nao aparece "
                                        "no bytecode por design"})
        elif AGREGADORES_RE.search(art):
            ignoradas.append({"artefato": art,
                              "motivo": "agregador (starter/bom): nao tem "
                                        "classes proprias"})
        else:
            item = {"artefato": art, "scope": scope}
            if art in (internos_reator or set()):
                item["nota"] = ("modulo interno do reator: em app Spring Boot "
                                "costuma ser agregado por component scan / "
                                "autoconfiguracao, sem referencia no bytecode")
                item["provavel_falso_positivo"] = True
            elif RUNTIME_POR_NATUREZA_RE.search(art):
                item["nota"] = ("atua em runtime por configuracao (log, driver, "
                                "migracao): nao aparece no bytecode")
                item["provavel_falso_positivo"] = True
            elif modulo_de_boot:
                # contexto, nao absolvicao: um modulo de boot ainda pode ter
                # dependencia genuinamente morta, entao nao marca como
                # falso positivo - so registra a possibilidade.
                item["nota"] = ("modulo de boot: pode ser carregada por "
                                "autoconfiguracao, mas confirme - nem toda dep "
                                "de modulo boot e usada")
            sem_uso.append(item)

    return {
        "usadas_via_transitiva": via_transitiva,
        "usadas_ausentes_do_pom": ausentes_do_pom,
        "declaradas_sem_uso": sem_uso,
        "ignoradas_na_analise": ignoradas,
    }


def jdk_release():
    rc, out, err = run(["jdeps", "--version"], timeout=30)
    m = re.match(r"(\d+)", (out or err or "").strip())
    return int(m.group(1)) if m else None


def tarjan_cycles(graph):
    """SCCs com mais de um no = ciclos."""
    index, stack, on, idx, low, out = {}, [], set(), {}, {}, []
    counter = [0]
    for start in list(graph):
        if start in index:
            continue
        work = [(start, iter(graph.get(start, ())))]
        index[start] = low[start] = counter[0]; counter[0] += 1
        stack.append(start); on.add(start)
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if nxt not in index:
                    index[nxt] = low[nxt] = counter[0]; counter[0] += 1
                    stack.append(nxt); on.add(nxt)
                    work.append((nxt, iter(graph.get(nxt, ()))))
                    advanced = True
                    break
                if nxt in on:
                    low[node] = min(low[node], index[nxt])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                comp = []
                while True:
                    w = stack.pop(); on.discard(w); comp.append(w)
                    if w == node:
                        break
                if len(comp) > 1:
                    out.append(sorted(comp))
    return out


def fact_bytecode(root: Path, module, files, out_dir: Path,
                  auto_compile=None, offline=True, deps_fato=None,
                  internos_reator=None, m2_path=None):
    mid = module["id"]
    eco = module["ecossistema"]
    if "maven" not in eco and "gradle" not in eco:
        return fact_envelope("bytecode", mid, "n/d", None, {}, {
            "estado": "nao_aplicavel",
            "motivo": "ecossistema %s nao produz bytecode JVM" % eco,
        })
    if module.get("tipo") == "pom":
        return fact_envelope("bytecode", mid, "n/d", None, {}, {
            "estado": "nao_aplicavel",
            "motivo": "modulo agregador (packaging=pom) nao tem codigo",
        })
    if classes_dir(root, module) is None and not gera_classes(root, module, files):
        return fact_envelope("bytecode", mid, "n/d", None, {}, {
            "estado": "nao_aplicavel",
            "motivo": "modulo sem codigo-fonte JVM de producao "
                      "(so resources/testes)",
        })
    if not have("jdeps"):
        return fact_envelope("bytecode", mid, "jdeps", None, {}, {
            "estado": "indisponivel",
            "motivo": "jdeps nao encontrado; instale um JDK (nao apenas JRE)",
        })

    cdir = classes_dir(root, module)
    estado, compiled_at = ("ausente", None) if cdir is None else \
        bytecode_freshness(root, module, cdir)
    nota_compilacao = None

    if estado in {"ausente", "obsoleto"}:
        pergunta = ("Modulo %s: bytecode %s. Compilar agora com 'mvn compile'?"
                    % (mid, estado))
        def desistir(motivo):
            """Sem bytecode nenhum nao ha o que analisar. Mas se existe
            bytecode OBSOLETO, analisar e rotular vale mais que nao entregar
            nada - o consumidor decide se confia."""
            if cdir is not None:
                return None  # segue a analise; frescor fica 'obsoleto'
            return fact_envelope("bytecode", mid, "jdeps", None, {}, {
                "estado": "ausente", "motivo": motivo,
                "comando_sugerido": "cd %s && mvn compile"
                                    % (module["path"] or "."),
            })

        if ask(pergunta, default=False, auto=auto_compile):
            falhou = None
            if not have("mvn"):
                falhou = "mvn nao encontrado"
            else:
                mod_dir = root / module["path"] if module["path"] else root
                cmd = ["mvn", "-q", "-B", "compile"]
                if offline:
                    cmd.insert(1, "-o")
                rc, _, err = run(cmd, cwd=mod_dir, timeout=900)
                if rc != 0:
                    falhou = "compilacao falhou (rc=%s)" % rc
                else:
                    cdir = classes_dir(root, module)
                    if cdir is None:
                        return fact_envelope(
                            "bytecode", mid, "mvn compile", None, {}, {
                                "estado": "nao_aplicavel",
                                "motivo": "compilou e o modulo nao gera "
                                          "classes (so resources/testes)",
                            })
                    else:
                        estado, compiled_at = bytecode_freshness(
                            root, module, cdir)
            if falhou:
                r = desistir(falhou)
                if r is not None:
                    return r
                nota_compilacao = falhou
        else:
            r = desistir("bytecode %s e compilacao nao autorizada" % estado)
            if r is not None:
                return r
            nota_compilacao = "compilacao nao autorizada"

    cp, cp_motivo = maven_classpath(root, module, offline=offline)

    def exec_jdeps(extra):
        # -verbose (e nao -verbose:class): -verbose:class OMITE dependencias
        # dentro do mesmo pacote, o que zera o grafo em pacote unico.
        cmd = ["jdeps", "-verbose"] + extra
        if cp:
            cmd += ["-cp", cp]
        cmd.append(str(cdir))
        return run(cmd, cwd=root, timeout=300)

    tentativas, extra = [], []
    rc, out, err = exec_jdeps(extra)
    erros = jdeps_errors(out, err)
    tentativas.append({"args": list(extra), "rc": rc, "erros": erros[:3] or None})

    # Um unico jar multi-release no classpath aborta o jdeps inteiro e ele
    # nao emite aresta nenhuma. Reexecuta pedindo a release explicitamente.
    if erros and any("multi-release" in e.lower() for e in erros):
        candidatos = []
        maj = bytecode_major(cdir)
        if maj and maj >= 53:
            candidatos.append(str(maj - 44))
        j = jdk_release()
        if j and str(j) not in candidatos:
            candidatos.append(str(j))
        candidatos.append("base")
        for mr in candidatos:
            extra = ["--multi-release", mr]
            rc, out, err = exec_jdeps(extra)
            erros = jdeps_errors(out, err)
            tentativas.append({"args": list(extra), "rc": rc,
                               "erros": erros[:3] or None})
            if not erros:
                break

    if erros and not [l for l in out.splitlines() if "->" in l]:
        return fact_envelope("bytecode", mid, "jdeps", None, {}, {
            "estado": "indisponivel",
            "motivo": "jdeps abortou: %s" % erros[0][:200],
            "tentativas": tentativas,
            "comando_sugerido":
                "jdeps -verbose --multi-release base -cp <classpath> %s" % cdir})
    if rc != 0 and not out.strip():
        return fact_envelope("bytecode", mid, "jdeps", None, {}, {
            "estado": "indisponivel",
            "motivo": "jdeps falhou (rc=%s): %s" % (rc, err.strip()[:200]),
            "tentativas": tentativas})

    # conjunto real de classes deste modulo: e o que define "interno"
    internas = set()
    for cf in cdir.rglob("*.class"):
        rel = cf.relative_to(cdir).with_suffix("")
        internas.add(str(rel).replace(os.sep, "."))

    edges, pkg_graph, jars = [], {}, {}
    diag = {"linhas_saida": 0, "com_seta": 0, "casaram_regex": 0,
            "descartadas_origem_externa": 0, "auto_referencia": 0}
    for line in out.splitlines():
        diag["linhas_saida"] += 1
        if "->" not in line:
            continue
        diag["com_seta"] += 1
        m = JDEPS_EDGE_RE.match(line)
        if not m:
            continue
        diag["casaram_regex"] += 1
        de, para, origem = m.group(1), m.group(2), m.group(3).strip()
        if de == para:
            diag["auto_referencia"] += 1
            continue
        if de not in internas:
            diag["descartadas_origem_externa"] += 1
            continue
        if para in internas:
            tipo = "interno"
        elif origem.startswith("java.") or origem.startswith("jdk.") or \
                para.startswith("java.") or para.startswith("jdk."):
            tipo = "jdk"
        else:
            tipo = "externo"
            if origem and origem != "not found":
                jars[origem] = jars.get(origem, 0) + 1
            else:
                diag["nao_resolvidas"] = diag.get("nao_resolvidas", 0) + 1
        edges.append([de, para, tipo, origem or ""])
        if tipo == "interno":
            pde, ppara = de.rsplit(".", 1)[0], para.rsplit(".", 1)[0]
            if pde != ppara:
                pkg_graph.setdefault(pde, set()).add(ppara)

    ciclos = tarjan_cycles({k: sorted(v) for k, v in pkg_graph.items()})

    edges_path = out_dir / "facts" / mid / "bytecode_edges.tsv"
    write_tsv(edges_path, ["de", "para", "tipo", "origem"], edges)

    # declarado x usado, com escopo e agregadores levados em conta
    declaradas = _maven_declared(module["_pom"]) if module.get("_pom") else []
    conhecidos = {d["ga"].split(":")[-1] for d in declaradas}
    for campo in ("diretas", "transitivas"):
        conhecidos |= {d["ga"].split(":")[-1]
                       for d in (deps_fato or {}).get(campo) or []}
    usados_art = {jar_para_artefato(j, conhecidos) for j in jars}
    refs_por_art = {}
    for j, n in jars.items():
        a = jar_para_artefato(j, conhecidos)
        refs_por_art[a] = refs_por_art.get(a, 0) + n
    # so da para afirmar "ausente do pom" se as TRANSITIVAS foram mesmo
    # resolvidas; senao tudo que vem de starter viraria falso alarme.
    # o que torna a arvore confiavel e ela ter sido RESOLVIDA, nao ter
    # transitivas: modulo sem transitiva e um fato, nao falta de dado.
    transitivas_confiaveis = bool(
        deps_fato and deps_fato.get("confianca") == "resolvida")
    resolvidas_art = set()
    if transitivas_confiaveis:
        for d in (deps_fato.get("diretas") or []) + \
                 (deps_fato.get("transitivas") or []):
            resolvidas_art.add(d["ga"].split(":")[-1])
    versoes = {d["ga"]: d.get("versao_resolvida") or d.get("versao_declarada")
               for d in (deps_fato or {}).get("diretas") or []}
    candidatas = []
    for d in declaradas:
        art = d["ga"].split(":")[-1]
        # so quem cairia em deps_declaradas_sem_uso; o resto ja tem balde proprio
        if art in usados_art or art in PROCESSADORES or AGREGADORES_RE.search(art) \
                or (d.get("scope") or "compile").lower() in SCOPES_FORA_DO_MAIN:
            continue
        candidatas.append((d["ga"], versoes.get(d["ga"]) or d.get("versao_declarada")))
    fora_do_jdeps = deps_em_descritores(cdir, candidatas, m2_repo(m2_path))
    for art, n in fora_do_jdeps.items():
        usados_art.add(art)
        refs_por_art[art] = refs_por_art.get(art, 0) + n
    eh_boot = False
    for f in files:
        if f["module"] == mid and f["ext"] == ".java" and \
                not TEST_PATH_RE.search(f["path"]):
            t = read_text(f["abs"])
            if t and "@SpringBootApplication" in t:
                eh_boot = True
                break
    cls = classificar_deps(declaradas, usados_art,
                           resolvidas_art if transitivas_confiaveis else None,
                           refs_por_art, internos_reator=internos_reator,
                           modulo_de_boot=eh_boot)

    derivado = {module.get("_pom_path", ""):
                next((f["blob"] for f in files
                      if f["path"] == module.get("_pom_path")), None)}
    derivado = {k: v for k, v in derivado.items() if k}
    return fact_envelope(
        "bytecode", mid,
        "jdeps %s%s%s" % (" ".join(["-verbose"] + extra),
                          " com classpath" if cp else " sem classpath",
                          " + descritores do constant pool"
                          if fora_do_jdeps else ""),
        ("media" if (estado == "obsoleto" or not cp
                     or diag.get("nao_resolvidas")) else "alta"),
        derivado, {
            "estado": "disponivel",
            "resolucao": "tipo",
            "derivado_de_agregado": agregado_fontes(
                files, mid, {".java", ".kt"}, apenas_main=True),
            "frescor": {
                "estado": estado, "compilado_em": compiled_at,
                "nota": nota_compilacao,
                "aviso": ("analisado sobre bytecode OBSOLETO: o fonte mudou "
                          "depois da ultima compilacao, entao arestas novas "
                          "podem faltar e arestas removidas podem aparecer")
                         if estado == "obsoleto" else None,
            },
            "classes_dir": str(cdir.relative_to(root)),
            "bytecode_major": bytecode_major(cdir),
            "classpath_resolvido": bool(cp),
            "classpath_motivo": cp_motivo,
            "jdeps_args": ["-verbose"] + extra,
            "jdeps_tentativas": tentativas if len(tentativas) > 1 else None,
            "arestas_arquivo": "facts/%s/bytecode_edges.tsv" % mid,
            "arestas_total": len(edges),
            "arestas_internas": sum(1 for e in edges if e[2] == "interno"),
            "diagnostico": diag,
            "usadas_fora_do_jdeps": fora_do_jdeps or None,
            "aviso_nao_resolvidas": (
                "%d referencia(s) externa(s) ficaram 'not found': o classpath "
                "esta incompleto, entao deps_nao_declaradas pode estar furado"
                % diag["nao_resolvidas"]) if diag.get("nao_resolvidas") else None,
            "motivo_vazio": (
                None if edges else
                "jdeps rodou mas nenhuma aresta foi extraida. "
                + ("saida vazia: verifique se %s tem .class" % cdir.name
                   if diag["linhas_saida"] == 0 else
                   "nenhuma linha casou o parser - veja amostra_saida"
                   if diag["casaram_regex"] == 0 else
                   "todas as origens ficaram fora do conjunto de classes "
                   "internas (%d classes conhecidas)" % len(internas))),
            "amostra_saida": (
                None if edges else out.splitlines()[:15]),
            "classes_conhecidas": len(internas),
            "assinatura_classes": assinatura_classes(cdir),
            # pacotes vem das classes compiladas, nao do grafo: modulo sem
            # aresta interna (um boot, por exemplo) tem pacote mesmo assim
            "pacotes": sorted({c.rsplit(".", 1)[0] for c in internas
                               if "." in c}),
            # origens E destinos: so as origens fariam um pacote folha
            # (config, dto) parecer isolado do grafo
            "pacotes_com_aresta_interna": sorted(
                set(pkg_graph) | {d for v in pkg_graph.values() for d in v}),
            "ciclos": ciclos,
            "jars_usados": dict(sorted(jars.items(), key=lambda kv: -kv[1])[:80]),
            "deps_usadas_via_transitiva": cls["usadas_via_transitiva"],
            "deps_usadas_ausentes_do_pom": cls["usadas_ausentes_do_pom"],
            "deps_declaradas_sem_uso": cls["declaradas_sem_uso"],
            "deps_ignoradas_na_analise": cls["ignoradas_na_analise"],
            "modulo_de_boot": eh_boot,
            "transitivas_resolvidas": transitivas_confiaveis,
            "aviso_sem_transitivas": None if transitivas_confiaveis else
                "sem arvore de dependencia resolvida (mvn indisponivel ou "
                "offline): nao da para separar 'veio por transitiva' de "
                "'ausente do pom'. Tudo foi classificado como transitiva.",
            "como_ler_deps": {
                "usadas_via_transitiva": "o codigo usa, o pom nao declara, mas "
                    "veio resolvida (tipico de starter Spring Boot). Risco: "
                    "quebra se o intermediario parar de trazer. Ordenado por "
                    "'referencias' - quanto maior, mais o codigo depende dela "
                    "e mais vale declarar explicitamente.",
                "usadas_ausentes_do_pom": "usada e NEM resolvida - o caso que "
                    "merece atencao imediata.",
                "declaradas_sem_uso": "sem referencia no bytecode. Confirme "
                    "antes de remover: uso por reflexao, SPI ou so em runtime "
                    "nao aparece aqui.",
                "ignoradas_na_analise": "fora da comparacao de proposito - "
                    "veja o motivo de cada uma.",
            },
        })


# ---------------------------------------------------------------------------
# Tier 3: callgraph (java-callgraph)
# ---------------------------------------------------------------------------

PROXY_RE = re.compile(r"@(Transactional|Cacheable|CacheEvict|Async|Retryable|"
                      r"PreAuthorize|Validated)\b")
SPRING_DATA_RE = re.compile(r"interface\s+(\w+)\s+extends\s+[\w<>,\s]*"
                            r"(JpaRepository|CrudRepository|PagingAndSortingRepository|"
                            r"ReactiveCrudRepository|MongoRepository)")
REFLECTION_RE = re.compile(r"(Class\.forName|getDeclaredMethod|\.invoke\(|"
                           r"@EventListener|ApplicationEventPublisher)")
CG_LINE_RE = re.compile(r"^M:([^:]+):([^\s]+)\s+\((\w)\)([^:]+):(.+)$")


def find_callgraph_jar(explicit):
    cands = []
    if explicit:
        cands.append(Path(explicit).expanduser())
    cands += [Path.home() / ".scos-map" / "java-callgraph.jar",
              Path.home() / ".aimap" / "java-callgraph.jar",   # caminho antigo
              Path.home() / "java-callgraph.jar"]
    for c in cands:
        if c.exists():
            return c
    return None


def scan_lacunas(root: Path, module, files):
    """Lacunas conhecidas do grafo estatico, detectadas no fonte."""
    lacunas, entrypoints = [], []
    mine = [f for f in files if f["module"] == module["id"] and f["ext"] == ".java"]
    for f in mine:
        t = read_text(f["abs"])
        if not t:
            continue
        for m in PROXY_RE.finditer(t):
            lacunas.append({
                "tipo": "proxy_spring", "path": f["path"], "anotacao": m.group(1),
                "motivo": "@%s gera proxy em runtime; a chamada real nao aparece "
                          "no bytecode compilado" % m.group(1)})
        for m in SPRING_DATA_RE.finditer(t):
            lacunas.append({
                "tipo": "implementacao_em_runtime", "path": f["path"],
                "alvo": m.group(1),
                "motivo": "repositorio %s implementado por Spring Data em runtime"
                          % m.group(2)})
        if REFLECTION_RE.search(t):
            lacunas.append({
                "tipo": "reflexao_ou_evento", "path": f["path"],
                "motivo": "reflexao ou publicacao de evento: alvo resolvido em runtime"})
        for m in SPRING_ENTRY_RE.finditer(t):
            entrypoints.append({"path": f["path"], "anotacao": m.group(1),
                                "nota": "ponto de entrada - ausencia de chamador "
                                        "NAO significa codigo morto"})
    # dedup
    seen, uniq = set(), []
    for l in lacunas:
        k = (l["tipo"], l["path"], l.get("alvo"), l.get("anotacao"))
        if k not in seen:
            seen.add(k)
            uniq.append(l)
    return uniq, entrypoints


def fact_callgraph(root: Path, module, files, out_dir: Path, jar_path):
    mid = module["id"]
    lacunas, entrypoints = scan_lacunas(root, module, files)

    if "maven" not in module["ecossistema"]:
        return fact_envelope("callgraph", mid, "n/d", None, {}, {
            "estado": "nao_aplicavel",
            "motivo": "sem equivalente de bytecode para %s; grafo de chamada "
                      "so seria heuristico" % module["ecossistema"]})

    jar = find_callgraph_jar(jar_path)
    cdir = classes_dir(root, module)
    if jar is None:
        return fact_envelope("callgraph", mid, "java-callgraph", None, {}, {
            "estado": "indisponivel",
            "motivo": "java-callgraph.jar nao encontrado",
            "comando_sugerido": "baixe o jar e passe --callgraph-jar <caminho> "
                                "ou coloque em ~/.scos-map/java-callgraph.jar",
            "lacunas_conhecidas": lacunas[:200],
            "entrypoints": entrypoints[:200]})
    if cdir is None:
        return fact_envelope("callgraph", mid, "java-callgraph", None, {}, {
            "estado": "ausente", "motivo": "bytecode nao disponivel",
            "lacunas_conhecidas": lacunas[:200],
            "entrypoints": entrypoints[:200]})

    jars = sorted(str(p) for p in cdir.rglob("*.jar"))
    target = str(cdir)
    rc, out, err = run(["java", "-jar", str(jar), target], cwd=root, timeout=600)
    if rc != 0 and not out.strip():
        return fact_envelope("callgraph", mid, "java-callgraph", None, {}, {
            "estado": "indisponivel",
            "motivo": "java-callgraph falhou (rc=%s): %s" % (rc, err.strip()[:200]),
            "lacunas_conhecidas": lacunas[:200],
            "entrypoints": entrypoints[:200]})

    invoke_map = {"M": "virtual", "I": "interface", "S": "static",
                  "O": "special", "D": "dynamic"}
    edges, chamados = [], set()
    for line in out.splitlines():
        m = CG_LINE_RE.match(line.strip())
        if not m:
            continue
        de_cls, de_m, inv, para_cls, para_m = m.groups()
        inv_nome = invoke_map.get(inv, inv)
        certeza = "ambigua" if inv in {"I", "D"} else "resolvida"
        edges.append(["%s#%s" % (de_cls, de_m), "%s#%s" % (para_cls, para_m),
                      inv_nome, certeza])
        chamados.add("%s#%s" % (para_cls, para_m))

    edges_path = out_dir / "facts" / mid / "callgraph_edges.tsv"
    write_tsv(edges_path, ["de", "para", "invoke", "certeza"], edges)

    chamadores = {e[0] for e in edges}
    sem_chamador = sorted(chamadores - chamados)[:200]
    entry_paths = {e["path"].split("/")[-1].replace(".java", "")
                   for e in entrypoints}
    sem_chamador_anotado = [
        {"metodo": m,
         "aviso": "ponto de entrada - nao e codigo morto"
                  if m.split("#")[0].split(".")[-1] in entry_paths else
                  "sem chamador conhecido; confira as lacunas antes de concluir "
                  "que e codigo morto"}
        for m in sem_chamador
    ]

    return fact_envelope(
        "callgraph", mid, "java-callgraph sobre %s" % cdir.relative_to(root),
        "parcial", {}, {
            "estado": "disponivel",
            "resolucao": "metodo",
            "derivado_de_agregado": agregado_fontes(
                files, mid, {".java", ".kt"}, apenas_main=True),
            "aviso": "grafo estatico: proxies, reflexao e implementacoes geradas "
                     "em runtime NAO aparecem. Veja lacunas_conhecidas.",
            "arestas_arquivo": "facts/%s/callgraph_edges.tsv" % mid,
            "arestas_total": len(edges),
            "arestas_ambiguas": sum(1 for e in edges if e[3] == "ambigua"),
            "lacunas_conhecidas": lacunas[:200],
            "entrypoints": entrypoints[:200],
            "metodos_sem_chamador": sem_chamador_anotado,
        })


# ---------------------------------------------------------------------------
# Fato de fronteira: _reactor
# ---------------------------------------------------------------------------


DEPS_TSV_COLS = ["tipo", "ga", "versao", "origem", "scope", "divergente"]
GERENCIADAS_TSV_COLS = ["ga", "versao", "origem", "scope"]
TESTS_TSV_COLS = ["path", "tipo", "alvo_heuristico", "linhas",
                  "last_modified", "commits_90d"]
FECHO_TSV_COLS = ["ga", "versao", "scope"]


def calcular_fecho_comum(facts):
    """(ga, versao, scope) presente igual em TODOS os modulos que
    resolveram transitivas.

    Intersecao estrita de proposito: so assim o consumidor pode afirmar
    "todo modulo tem isto" sem checar modulo a modulo. Qualquer divergencia
    de versao tira a lib do fecho e ela volta para o TSV do modulo - errar
    para o lado de repetir e barato; errar para o lado de afirmar nao e.
    """
    conjuntos = []
    for mid, fs in facts.items():
        d = fs.get("deps")
        if not d or not d.get("transitivas"):
            continue
        conjuntos.append({
            (x["ga"], str(x.get("versao_resolvida") or ""), x.get("scope") or "")
            for x in d["transitivas"]
        })
    if len(conjuntos) < 2:
        return set()
    fecho = set(conjuntos[0])
    for c in conjuntos[1:]:
        fecho &= c
    return fecho


def emitir_deps(out_dir: Path, facts, sizes, reescritos):
    """Grava deps como envelope JSON + corpo TSV, sem repetir o fecho comum.

    Num reator Spring Boot o fecho transitivo dos modulos e quase identico;
    grava-lo por modulo e a maior redundancia do mapa.
    """
    fecho = calcular_fecho_comum(facts)
    declarados = {}

    if fecho:
        linhas = [list(k) for k in sorted(fecho)]
        cam = out_dir / "facts" / "_transitivas_comuns.tsv"
        sizes["facts/_transitivas_comuns.tsv"] = write_tsv(
            cam, FECHO_TSV_COLS, linhas)
        declarados["facts/_transitivas_comuns.tsv"] = {
            "colunas": FECHO_TSV_COLS,
            "descricao": "transitivas presentes com a mesma versao e scope em TODOS "
                         "os modulos que resolveram: nao se repetem nos "
                         "deps.tsv de cada modulo",
            "linhas": len(linhas),
        }

    for mid, fs in facts.items():
        d = fs.get("deps")
        if not d:
            continue
        linhas, no_fecho = [], 0
        for x in d.get("diretas", []):
            v = x.get("versao_resolvida") or x.get("versao_declarada")
            linhas.append(["direta", x["ga"], v, x.get("origem"),
                           x.get("scope"), "1" if x.get("divergente") else ""])
        for x in d.get("transitivas", []):
            chave = (x["ga"], str(x.get("versao_resolvida") or ""),
                     x.get("scope") or "")
            if chave in fecho:
                no_fecho += 1
                continue
            linhas.append(["transitiva", x["ga"], x.get("versao_resolvida"),
                           "transitiva", x.get("scope"), ""])

        rel = "facts/%s/deps.tsv" % mid
        sizes[rel] = write_tsv(out_dir / rel, DEPS_TSV_COLS, linhas)
        declarados[rel] = {"colunas": DEPS_TSV_COLS, "linhas": len(linhas)}

        env = {k: v for k, v in d.items()
               if k not in ("diretas", "transitivas", "gerenciadas")}
        env["corpo"] = "deps.tsv"
        env["corpo_colunas"] = DEPS_TSV_COLS
        env["diretas_total"] = len(d.get("diretas", []))
        env["transitivas_total"] = len(d.get("transitivas", []))
        if d.get("gerenciadas"):
            rel_g = "facts/%s/gerenciadas.tsv" % mid
            linhas_g = [[x["ga"], x["versao"], x["origem"], x.get("scope")]
                        for x in d["gerenciadas"]]
            sizes[rel_g] = write_tsv(out_dir / rel_g, GERENCIADAS_TSV_COLS,
                                     linhas_g)
            declarados[rel_g] = {"colunas": GERENCIADAS_TSV_COLS,
                                 "linhas": len(linhas_g)}
            env["gerenciadas_total"] = len(linhas_g)
            env["gerenciadas_corpo"] = "gerenciadas.tsv"
        if no_fecho:
            env["transitivas_no_fecho_comum"] = no_fecho
            env["fecho_comum_arquivo"] = "../_transitivas_comuns.tsv"
            env["aviso_fecho"] = (
                "as %d transitivas do fecho comum NAO estao em deps.tsv - "
                "a lista completa deste modulo e deps.tsv + "
                "_transitivas_comuns.tsv" % no_fecho)
        sz, mudou = write_json_se_mudou(
            out_dir / "facts" / mid / "deps.json", env)
        sizes["facts/%s/deps.json" % mid] = sz
        if mudou:
            reescritos.append("%s/deps" % mid)

    return declarados


def fact_reactor(root: Path, modules, files, deps_por_modulo):
    internos = {}
    for m in modules:
        if m.get("_pom"):
            internos[m["_pom"].get("artifactId")] = m["id"]
        if m.get("_pkg") and m["_pkg"].get("name"):
            internos[m["_pkg"]["name"]] = m["id"]

    arestas = []
    for mid, fato in deps_por_modulo.items():
        if not fato:
            continue
        for d in fato.get("diretas", []):
            nome = d["ga"].split(":")[-1]
            alvo = internos.get(nome) or internos.get(d["ga"])
            if alvo and alvo != mid:
                arestas.append({"de": mid, "para": alvo, "scope": d.get("scope")})

    # versoes divergentes entre modulos
    versoes = {}
    for mid, fato in deps_por_modulo.items():
        if not fato:
            continue
        for d in fato.get("diretas", []) + fato.get("transitivas", []):
            v = d.get("versao_resolvida") or d.get("versao_declarada")
            if v and not str(v).startswith("${"):
                versoes.setdefault(d["ga"], {}).setdefault(str(v), []).append(mid)
    conflitos = [
        {"ga": ga, "versoes": {v: sorted(set(mods)) for v, mods in vs.items()}}
        for ga, vs in sorted(versoes.items()) if len(vs) > 1
    ]

    parents = {}
    for m in modules:
        if m.get("_pom") and m["_pom"].get("parent"):
            parents[m["id"]] = m["_pom"]["parent"].get("artifactId")

    derivado = {}
    for m in modules:
        p = m.get("_pom_path") or m.get("_pkg_path")
        if p:
            derivado[p] = next((f["blob"] for f in files if f["path"] == p), None)

    return fact_envelope("reactor", "_reactor", "poms e manifests do repo",
                         "alta", derivado, {
                             "modulos": [
                                 {"id": m["id"], "path": m["path"],
                                  "tipo": m["tipo"],
                                  "ecossistema": m["ecossistema"],
                                  "artefato": m.get("artefato")}
                                 for m in modules],
                             "arestas_internas": arestas,
                             "parents": parents,
                             "conflitos_de_versao": conflitos,
                         })


# ---------------------------------------------------------------------------
# Indice e frescor
# ---------------------------------------------------------------------------


TEST_PATH_RE = re.compile(r"(^|/)src/test/|(^|/)test/|Test\.java$|Tests\.java$|IT\.java$")


def agregado_fontes(files, mid, exts, apenas_main=False):
    """Hash unico dos fontes de um modulo.

    Listar 500 arquivos em derivado_de inflaria o fato; o agregado da a
    mesma deteccao de mudanca em uma linha.

    apenas_main: fonte de teste nao vira classe em target/classes, entao
    incluir teste no hash marcaria o bytecode como obsoleto sem que o
    bytecode tenha mudado.
    """
    sel = [f for f in files
           if f["module"] == mid and f["ext"] in exts and f["blob"]]
    if apenas_main:
        sel = [f for f in sel if not TEST_PATH_RE.search(f["path"])]
    blobs = sorted("%s:%s" % (f["path"], f["blob"]) for f in sel)
    return {
        "escopo": "fontes %s%s do modulo %s" % (
            "/".join(sorted(exts)), " (apenas main)" if apenas_main else "", mid),
        "arquivos": len(blobs),
        "sha": sha_text("\n".join(blobs)),
    }


def fact_state(fato, files_by_path, files=None, root=None):
    """Compara derivado_de (e o agregado de fontes) com o estado atual."""
    if fato is None:
        return {"estado": "ausente", "motivo": "nao gerado"}
    if fato.get("estado") in {"ausente", "indisponivel", "nao_aplicavel",
                              "obsoleto"}:
        return {"estado": fato["estado"], "motivo": fato.get("motivo")}
    mudou = [
        p for p, blob in (fato.get("derivado_de") or {}).items()
        if p and files_by_path.get(p) != blob
    ]
    agg = fato.get("derivado_de_agregado")
    if agg and files is not None:
        atual = agregado_fontes(
            files, fato.get("modulo"), {".java", ".kt"},
            apenas_main="apenas main" in (agg.get("escopo") or ""))
        if atual["sha"] != agg.get("sha"):
            mudou.append("%s (%d arquivo(s))" % (agg.get("escopo"), atual["arquivos"]))
    ass = fato.get("assinatura_classes")
    if ass and root is not None and fato.get("classes_dir"):
        cdir = Path(root) / fato["classes_dir"]
        if cdir.is_dir():
            atual = assinatura_classes(cdir)
            if atual["sha"] != ass.get("sha"):
                mudou.append("bytecode recompilado (%d classes agora, %d antes)"
                             % (atual["classes"], ass.get("classes", 0)))
    if mudou:
        return {"estado": "obsoleto", "mudou": mudou[:20]}
    return {"estado": "fresco"}


FILES_TSV_COLS = ["path", "blob", "bytes", "lines", "module", "kind",
                  "last_commit", "last_modified", "author", "commits_90d",
                  "tracked"]
BYTECODE_TSV_COLS = ["de", "para", "tipo", "origem"]
CALLGRAPH_TSV_COLS = ["de", "para", "invoke", "certeza"]


def tier_efetivo(facts):
    """Maior tier que produziu dado: pedir tier 3 sem o jar nao e ter tier 3."""
    def rodou(nome):
        return any((fs.get(nome) or {}).get("estado") == "disponivel"
                   for fs in facts.values())
    return 3 if rodou("callgraph") else 2 if rodou("bytecode") else 1


def build_index(root, modules, ecos, files, facts, git, tiers, sizes,
                tsvs=None):
    files_by_path = {f["path"]: f["blob"] for f in files}
    mods_idx = {}
    for m in modules:
        mid = m["id"]
        f_states = {}
        for nome in ("layout", "config", "deps", "docs", "bytecode", "callgraph"):
            fato = facts.get(mid, {}).get(nome)
            if fato is None and nome in ("bytecode", "callgraph") and \
                    tiers < (2 if nome == "bytecode" else 3):
                f_states[nome] = {"estado": "ausente",
                                  "motivo": "tier %s nao solicitado"
                                            % (2 if nome == "bytecode" else 3)}
            elif fato is None:
                continue
            else:
                f_states[nome] = fact_state(fato, files_by_path, files, root)
                f_states[nome]["arquivo"] = "facts/%s/%s.json" % (mid, nome)
        mods_idx[mid] = {
            "path": m["path"], "tipo": m["tipo"],
            "ecossistema": m["ecossistema"], "artefato": m.get("artefato"),
            "arquivos": sum(1 for f in files if f["module"] == mid),
            "fatos": f_states,
        }

    kinds = {}
    for f in files:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1

    tabelas = {"files.tsv": {"colunas": FILES_TSV_COLS, "linhas": len(files)}}
    tabelas.update(tsvs or {})
    for mid, fs in facts.items():
        b = fs.get("bytecode") or {}
        if b.get("arestas_arquivo"):
            tabelas[b["arestas_arquivo"]] = {
                "colunas": BYTECODE_TSV_COLS,
                "linhas": b.get("arestas_total", 0)}
        c = fs.get("callgraph") or {}
        if c.get("arestas_arquivo"):
            tabelas[c["arestas_arquivo"]] = {
                "colunas": CALLGRAPH_TSV_COLS,
                "linhas": c.get("arestas_total", 0)}

    return {
        "schema_versao": SCHEMA_VERSAO,
        "gerador_versao": GERADOR_VERSAO,
        "gerado_em": now_iso(),
        "raiz": root.name,
        "como_usar": [
            "Este arquivo e o unico que precisa ser lido sempre.",
            "Escolha os fatos relevantes em modulos[].fatos e abra so aqueles.",
            "Fato com estado 'obsoleto' foi gerado antes de mudancas nas fontes "
            "listadas em 'mudou'; regenere antes de confiar.",
            "O mapa e um indice: para ler conteudo, abra o arquivo pelo caminho.",
        ],
        "git": {
            "disponivel": git.available, "head": git.head,
            "branch": git.branch, "dirty": git.dirty,
            "workspace_multi_repo": git.multi_repo,
            "repositorios": git.repos_summary() if git.multi_repo else None,
            "nota_rename": "historico sem --follow: arquivo renomeado aparece "
                           "com a data do rename",
        },
        "ecossistemas": ecos,
        "tier_executado": tier_efetivo(facts),
        "tier_pedido": tiers,
        "arquivos": {"total": len(files), "por_tipo": kinds,
                     "tsv": "files.tsv"},
        # todo TSV declarado com suas colunas: a skill de consulta monta o
        # awk sem precisar abrir o arquivo para descobrir o cabecalho
        "tabelas": tabelas,
        "modulos": mods_idx,
        "reactor": "facts/_reactor.json",
        "tamanho_bytes": sizes,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def fato_em_disco_ainda_vale(out_dir: Path, mid, nome, files_by_path, files,
                             root):
    """Le o fato gravado e devolve-o se as fontes dele nao mudaram.

    Regenerar um fato cujas fontes estao intactas gasta tempo (jdeps, mvn,
    varredura de fonte) para produzir exatamente o mesmo conteudo.
    """
    p = out_dir / "facts" / mid / ("%s.json" % nome)
    if not p.exists():
        return None
    try:
        fato = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if not fato.get("derivado_de") and not fato.get("derivado_de_agregado"):
        return None          # sem procedencia nao da para afirmar frescor
    if fact_state(fato, files_by_path, files, root).get("estado") != "fresco":
        return None
    return fato


def scan_one(root: Path, args, prefixo=""):
    """Pipeline completo sobre UM projeto. Retorna (index, out_dir)."""
    out_dir = root / OUT_DIR
    t0 = time.time()

    def log(msg):
        print(prefixo + msg, file=sys.stderr)

    log("[1/5] git...")
    git = MultiGit(root)
    if git.multi_repo:
        log("      %d repositorio(s) git detectados no workspace"
            % len(git.repos_summary()))
    log("[2/5] detectando modulos...")
    modules, ecos = detect_modules(root)
    log("      %d modulo(s), ecossistemas: %s" % (len(modules), ", ".join(ecos)))
    log("[3/5] varrendo arquivos...")
    files = scan_files(root, modules, git)
    log("      %d arquivo(s)" % len(files))

    sizes, reescritos, tsvs_extra, reaproveitados = {}, [], {}, []
    incremental = not getattr(args, "full", False)
    files_by_path = {f["path"]: f["blob"] for f in files}
    header, rows = files_tsv_rows(files)
    sizes["files.tsv"] = write_tsv(out_dir / "files.tsv", header, rows)

    log("[4/5] tier 1...")
    facts, deps_por_modulo = {}, {}
    all_ids = [m["id"] for m in modules]
    for m in modules:
        mid = m["id"]
        facts[mid] = {}
        for nome, fn in (
            ("layout", lambda: fact_layout(root, m, files)),
            ("config", lambda: fact_config(m, files)),
            ("deps", lambda: fact_deps(root, m, files, offline=not args.online)),
            ("docs", lambda: fact_docs(m, files, all_ids)),
            ("tests", lambda: fact_tests(root, m, files,
                                         facts[mid].get("deps"))),
        ):
            fato = None
            # deps NUNCA e reaproveitado: o envelope em disco ja teve as
            # listas movidas para o TSV, e o fecho comum depende de TODOS os
            # modulos - reusar um so produziria um fecho errado.
            if incremental and nome != "deps":
                fato = fato_em_disco_ainda_vale(
                    out_dir, mid, nome, files_by_path, files, root)
                if fato is not None:
                    reaproveitados.append("%s/%s" % (mid, nome))
            if fato is None:
                fato = fn()
            if fato is None:
                continue
            facts[mid][nome] = fato
            # deps e escrito depois: o fecho transitivo comum so e conhecido
            # quando todos os modulos ja foram lidos (ver emitir_deps).
            if nome == "deps":
                continue
            if nome == "tests":
                if "_linhas_tsv" not in fato:
                    # veio do disco: o TSV ja esta la, nada a reescrever
                    rel = "facts/%s/tests.tsv" % mid
                    alvo = out_dir / rel
                    if alvo.exists():
                        sizes[rel] = alvo.stat().st_size
                        tsvs_extra[rel] = {
                            "colunas": TESTS_TSV_COLS,
                            "linhas": max(0, len(
                                alvo.read_text(encoding="utf-8")
                                .splitlines()) - 1)}
                        continue
                    fato = fact_tests(root, m, files, facts[mid].get("deps"))
                    facts[mid][nome] = fato
                linhas = fato.pop("_linhas_tsv", [])
                rel = "facts/%s/tests.tsv" % mid
                sizes[rel] = write_tsv(out_dir / rel, TESTS_TSV_COLS, linhas)
                tsvs_extra[rel] = {"colunas": TESTS_TSV_COLS,
                                   "linhas": len(linhas)}
                fato["corpo"] = "tests.tsv"
                fato["corpo_colunas"] = TESTS_TSV_COLS
            sz, mudou_f = write_json_se_mudou(
                out_dir / "facts" / mid / ("%s.json" % nome), fato)
            sizes["facts/%s/%s.json" % (mid, nome)] = sz
            if mudou_f:
                reescritos.append("%s/%s" % (mid, nome))
        deps_por_modulo[mid] = facts[mid].get("deps")

    tsvs = emitir_deps(out_dir, facts, sizes, reescritos)
    tsvs.update(tsvs_extra)

    reactor = fact_reactor(root, modules, files, deps_por_modulo)
    sizes["facts/_reactor.json"], mudou_r = write_json_se_mudou(
        out_dir / "facts" / "_reactor.json", reactor)
    if mudou_r:
        reescritos.append("_reactor")

    if args.tier >= 2:
        log("[5/5] tier 2 (bytecode)...")
        auto = True if args.compile else (False if args.no_compile else None)
        internos_reator = {m["_pom"].get("artifactId") for m in modules
                           if m.get("_pom") and m["_pom"].get("artifactId")}
        for m in modules:
            fato = None
            if incremental:
                fato = fato_em_disco_ainda_vale(
                    out_dir, m["id"], "bytecode", files_by_path, files, root)
                if fato is not None:
                    reaproveitados.append("%s/bytecode" % m["id"])
            if fato is None:
                fato = fact_bytecode(
                    root, m, files, out_dir, auto_compile=auto,
                    offline=not args.online,
                    deps_fato=facts.get(m["id"], {}).get("deps"),
                    internos_reator=internos_reator,
                    m2_path=getattr(args, "m2_repo", None))
            facts[m["id"]]["bytecode"] = fato
            sizes["facts/%s/bytecode.json" % m["id"]], mb = \
                write_json_se_mudou(
                    out_dir / "facts" / m["id"] / "bytecode.json", fato)
            if mb:
                reescritos.append("%s/bytecode" % m["id"])

    if args.tier >= 3:
        log("      tier 3 (callgraph)...")
        for m in modules:
            fato = fact_callgraph(root, m, files, out_dir, args.callgraph_jar)
            facts[m["id"]]["callgraph"] = fato
            sizes["facts/%s/callgraph.json" % m["id"]], mc = \
                write_json_se_mudou(
                    out_dir / "facts" / m["id"] / "callgraph.json", fato)
            if mc:
                reescritos.append("%s/callgraph" % m["id"])

    index = build_index(root, modules, ecos, files, facts, git, args.tier,
                        sizes, tsvs)
    idx_size = write_json(out_dir / "index.json", index)

    total = sum(sizes.values()) + idx_size
    src = sum(f["bytes"] for f in files)
    index["_metricas"] = {
        "mapa_bytes": total, "fontes_bytes": src,
        "reducao": round(src / total, 1) if total else 0,
        "segundos": round(time.time() - t0, 1),
    }
    write_json(out_dir / "index.json", index)
    log("    %d arquivos, mapa %.1f KB vs fontes %.1f KB (%.1fx), %.1fs"
        % (len(files), total / 1024, src / 1024,
           (src / total) if total else 0, time.time() - t0))
    if reaproveitados:
        log("    %d fato(s) reaproveitados do disco (fontes intactas)"
            % len(reaproveitados))
    if reescritos:
        log("    %d fato(s) reescritos: %s" % (
            len(reescritos), ", ".join(reescritos[:6])
            + (" ..." if len(reescritos) > 6 else "")))
    else:
        log("    nenhum fato mudou (nada reescrito)")
    return index, out_dir


def resolve_all(args):
    """--all liga o pipeline inteiro. Flags explicitas continuam ganhando."""
    if getattr(args, "all", False):
        if getattr(args, "tier", None) is None:
            args.tier = 3
        if not args.no_compile:
            args.compile = True
        args.online = True
    if getattr(args, "tier", None) is None:
        args.tier = 1
    return args


def preflight(args, projetos=None):
    """Diz o que vai rodar e o que vai custar, antes de gastar o tempo."""
    linhas = ["plano: tier %d" % args.tier]
    if args.tier >= 2:
        linhas.append("  tier 2 (jdeps): %s" % (
            "compila sem perguntar" if args.compile else
            "nao compila" if args.no_compile else "pergunta antes de compilar"))
        if not have("jdeps"):
            linhas.append("  ! jdeps ausente - instale um JDK (nao so JRE)")
        if not have("mvn"):
            linhas.append("  ! mvn ausente - deps ficam so 'declaradas'")
    if args.tier >= 3:
        jar = find_callgraph_jar(getattr(args, "callgraph_jar", None))
        linhas.append("  tier 3 (callgraph): %s" % (
            "jar em %s" % jar if jar else
            "jar ausente - so as lacunas serao reportadas"))
    linhas.append("  maven: %s" % ("online" if args.online else "offline (-o)"))
    if projetos:
        linhas.append("  %d projeto(s)" % len(projetos))
    for l in linhas:
        log(l)
    log("")


def cmd_scan(args):
    root = Path(args.root).resolve()
    if not root.is_dir():
        log("erro: %s nao e uma pasta" % root)
        return 1
    resolve_all(args)
    preflight(args)
    index, out_dir = scan_one(root, args)
    log("")
    log("ok  %s" % out_dir)
    log("    index.json e o unico arquivo de leitura obrigatoria")
    dz = collect_destaques(root, root.name)
    obsoletos = [
        "%s/%s" % (mid, fname)
        for mid, m in index.get("modulos", {}).items()
        for fname, st in m.get("fatos", {}).items()
        if st.get("estado") == "obsoleto"
    ]
    print_destaques(dz, obsoletos, [])
    return 0


PROJECT_MARKERS = {"pom.xml", "package.json", "build.gradle", "build.gradle.kts",
                   "go.mod", "Cargo.toml", "pyproject.toml", "requirements.txt",
                   "composer.json", "Gemfile"}


def discover_projects(root: Path, max_depth=3, podas=None):
    """Acha os projetos de um workspace.

    Um diretorio e projeto se tem manifesto de build ou .git na raiz dele.
    Ao encontrar um, NAO desce mais: monorepo multi-modulo continua sendo
    UM projeto - a divisao interna em modulos e problema do scan_one.

    `podas` coleta os diretorios cortados por profundidade. Projeto nao
    descoberto nao gera erro - simplesmente nao existe no mapa, que e o pior
    modo de falha de um indice. Zero podas e a prova de que o default bastou.
    """
    found = []

    def walk(d: Path, depth: int):
        if depth > max_depth:
            if podas is not None:
                podas.append(str(d.relative_to(root)).replace(os.sep, "/"))
            return
        try:
            entries = sorted(x for x in d.iterdir() if x.is_dir())
        except OSError:
            return
        nomes = {x.name for x in d.iterdir()} if d.exists() else set()
        if d != root and (nomes & PROJECT_MARKERS or (d / ".git").exists()):
            found.append(d)
            return
        for sub in entries:
            if sub.name in IGNORE_DIRS or sub.name.startswith("."):
                continue
            walk(sub, depth + 1)

    nomes_raiz = {x.name for x in root.iterdir()} if root.is_dir() else set()
    if nomes_raiz & PROJECT_MARKERS:
        # a propria raiz e um projeto: nao e workspace
        return [root]
    walk(root, 0)
    return found


def avisar_podas(podas, max_depth):
    """Diretorio nao visitado nunca pode passar em silencio."""
    if not podas:
        return
    log("! %d diretorio(s) nao visitados por --max-depth=%d: %s"
        % (len(podas), max_depth,
           ", ".join(podas[:5]) + (" ..." if len(podas) > 5 else "")))
    log("  se algum contiver projeto, rode com --max-depth maior")


def collect_versions(proj_root: Path):
    """Le os deps.json de um projeto ja mapeado -> {ga: {versao: [modulos]}}."""
    out = {}
    facts_dir = proj_root / OUT_DIR / "facts"
    if not facts_dir.is_dir():
        return out
    # o corpo das deps vive em deps.tsv desde o schema 2.0; o fecho comum
    # vale para todos os modulos e entra uma vez por projeto
    fecho = []
    fecho_tsv = facts_dir / "_transitivas_comuns.tsv"
    if fecho_tsv.exists():
        for i, linha in enumerate(
                (read_text(fecho_tsv) or "").splitlines()):
            if i == 0 or not linha.strip():
                continue
            col = linha.split("\t") + [""]
            if col[1] and col[2] != "test":
                fecho.append((col[0], col[1]))

    for dj in sorted(facts_dir.rglob("deps.json")):
        try:
            d = json.loads(dj.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        mod = d.get("modulo")
        tsv = dj.parent / "deps.tsv"
        for i, linha in enumerate((read_text(tsv) or "").splitlines()):
            if i == 0 or not linha.strip():
                continue
            col = linha.split("\t")
            # scope test fica fora: divergencia so de teste nao chega ao runtime
            if len(col) < 3 or (len(col) > 4 and col[4] == "test"):
                continue
            ga, v = col[1], col[2]
            if not v or v.startswith("${"):
                continue
            out.setdefault(ga, {}).setdefault(v, []).append(mod)
        if d.get("transitivas_no_fecho_comum"):
            for ga, v in fecho:
                out.setdefault(ga, {}).setdefault(v, []).append(mod)
        gtsv = dj.parent / "gerenciadas.tsv"
        linhas_g = (read_text(gtsv) or "").splitlines() if gtsv.exists() else []
        for i, linha in enumerate(linhas_g):
            col = linha.split("\t")
            if i == 0 or len(col) < 2 or not col[1] or col[1].startswith("${"):
                continue
            out.setdefault(col[0], {}).setdefault(col[1], []).append(
                "%s (gerenciada)" % mod)
    return out


def collect_destaques(proj_root: Path, rel: str):
    """Le os fatos gravados e extrai o que um humano quer ver sem abrir JSON."""
    d = {"ciclos": [], "deps_nao_declaradas": [], "deps_nao_usadas": [],
         "divergencias": 0, "entrypoints": 0, "lacunas": 0,
         "tier2_indisponivel": [], "tier3_indisponivel": []}
    facts_dir = proj_root / OUT_DIR / "facts"
    if not facts_dir.is_dir():
        return d
    for fj in sorted(facts_dir.rglob("*.json")):
        try:
            f = json.loads(fj.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        mod, nome = f.get("modulo"), f.get("fato")
        alvo = "%s/%s" % (rel, mod)
        if nome == "deps":
            d["divergencias"] += len(f.get("divergencias") or [])
        elif nome == "layout":
            d["entrypoints"] += len(f.get("entrypoints") or [])
        elif nome == "tests":
            d["testes_classes"] = d.get("testes_classes", 0) + (
                f.get("classes") or 0)
            for r in f.get("regras_arquiteturais") or []:
                d.setdefault("regras_arch", []).append(
                    {"modulo": alvo, **r})
            if (f.get("classes") or 0) == 0 and f.get("raizes"):
                d.setdefault("modulos_sem_teste", []).append(
                    {"modulo": alvo, "raizes": f["raizes"]})
        elif nome == "bytecode":
            if f.get("estado") == "disponivel":
                for c in f.get("ciclos") or []:
                    d["ciclos"].append({"modulo": alvo, "pacotes": c})
                for x in f.get("deps_usadas_ausentes_do_pom") or []:
                    d["deps_nao_declaradas"].append(
                        {"modulo": alvo,
                         "dep": "%s (%d refs)" % (x["artefato"],
                                                  x.get("referencias", 0))})
                for x in f.get("deps_declaradas_sem_uso") or []:
                    if x.get("provavel_falso_positivo"):
                        continue
                    d["deps_nao_usadas"].append(
                        {"modulo": alvo, "dep": x["artefato"]})
            elif f.get("estado") in {"ausente", "indisponivel"}:
                d["tier2_indisponivel"].append(
                    {"modulo": alvo, "motivo": f.get("motivo")})
        elif nome == "callgraph":
            d["lacunas"] += len(f.get("lacunas_conhecidas") or [])
            if f.get("estado") in {"ausente", "indisponivel"}:
                d["tier3_indisponivel"].append(
                    {"modulo": alvo, "motivo": f.get("motivo")})
    return d


def merge_destaques(a, b):
    for k, v in b.items():
        if isinstance(v, list):
            a.setdefault(k, []).extend(v)
        else:
            a[k] = a.get(k, 0) + v
    return a


def print_destaques(dz, obsoletos, conflitos, snapshots=None):
    """Resumo acionavel no terminal - o JSON continua sendo a fonte."""
    log("")
    log("=" * 62)
    log("ACHADOS")
    log("=" * 62)
    vazio = True
    if conflitos:
        vazio = False
        log("")
        log("versoes divergentes entre projetos (%d):" % len(conflitos))
        for c in conflitos[:8]:
            versoes = ", ".join(
                "%s em %s" % (v, ",".join(m)) for v, m in c["versoes"].items())
            log("  %s" % c["ga"])
            log("      %s" % versoes[:100])
    desatualizados = [i for i in (snapshots or [])
                      if i.get("estado") in ("jar_desatualizado", "jar_ausente")]
    if desatualizados:
        vazio = False
        log("")
        log("SNAPSHOT do ~/.m2 atras do fonte ao lado (%d):"
            % len(desatualizados))
        for i in desatualizados[:6]:
            atraso = (" (%d dia(s) atras)" % i["atraso_dias"]
                      if i.get("atraso_dias") else "")
            log("  %s %s%s" % (i["ga"], i["estado"], atraso))
            log("      consumido por %s | %s"
                % (", ".join(i["consumido_por"]), i.get("acao", "")))
    if dz.get("ciclos"):
        vazio = False
        log("")
        log("ciclos entre pacotes (%d):" % len(dz["ciclos"]))
        for c in dz["ciclos"][:8]:
            log("  %s: %s" % (c["modulo"], " <-> ".join(
                p.split(".")[-1] for p in c["pacotes"])))
    if dz.get("deps_nao_declaradas"):
        vazio = False
        log("")
        log("usadas e AUSENTES do pom (%d) - nem declaradas nem resolvidas:"
            % len(dz["deps_nao_declaradas"]))
        for x in dz["deps_nao_declaradas"][:8]:
            log("  %s: %s" % (x["modulo"], x["dep"]))
    if dz.get("regras_arch"):
        vazio = False
        log("")
        log("regras de arquitetura (ArchUnit) - %d:" % len(dz["regras_arch"]))
        for r in dz["regras_arch"][:8]:
            log("  %s: %s (%s)" % (r["modulo"], r["regra"],
                                   r["path"].split("/")[-1]))
    if dz.get("modulos_sem_teste"):
        vazio = False
        log("")
        log("raiz de teste existe mas nenhum teste identificado (%d):"
            % len(dz["modulos_sem_teste"]))
        for m_ in dz["modulos_sem_teste"][:8]:
            log("  %s (%s)" % (m_["modulo"], ", ".join(m_["raizes"])))
    if dz.get("deps_nao_usadas"):
        vazio = False
        log("")
        log("declaradas sem uso no bytecode (%d) - confirme antes de remover:"
            % len(dz["deps_nao_usadas"]))
        for x in dz["deps_nao_usadas"][:8]:
            log("  %s: %s" % (x["modulo"], x["dep"]))
    if obsoletos:
        vazio = False
        log("")
        log("fatos obsoletos (%d) - fontes mudaram apos o mapa" % len(obsoletos))
    if vazio:
        log("")
        log("  nada a reportar nos tiers executados")

    ind2, ind3 = dz.get("tier2_indisponivel"), dz.get("tier3_indisponivel")
    if ind2 or ind3:
        log("")
        log("nao analisado:")
        motivos = {}
        for x in (ind2 or []) + (ind3 or []):
            motivos.setdefault(x.get("motivo") or "?", []).append(x["modulo"])
        for motivo, mods in list(motivos.items())[:6]:
            log("  %s" % motivo)
            log("      %s" % ", ".join(mods[:5]))
    log("")


def deps_assinatura(proj_root: Path) -> str:
    """Impressao digital das deps de um projeto, para o fato cruzado.

    O fato cruzado e montado lendo o mapa em cache dos outros projetos; sem
    isso, `workspace --only X` remonta os conflitos com deps velhas dos
    demais e o status jura que esta fresco.
    """
    facts = proj_root / OUT_DIR / "facts"
    if not facts.is_dir():
        return ""
    partes = []
    alvos = sorted([*facts.rglob("deps.tsv"), *facts.rglob("gerenciadas.tsv")])
    comum = facts / "_transitivas_comuns.tsv"
    if comum.exists():
        alvos.append(comum)
    for f in alvos:
        rel = str(f.relative_to(facts)).replace(os.sep, "/")
        partes.append("%s:%s" % (rel, sha_text(read_text(f) or "")))
    return sha_text("\n".join(partes))


def git_head_atual(proj_root: Path):
    rc, out, _ = run(["git", "rev-parse", "HEAD"], cwd=proj_root)
    return out.strip()[:SHA_LEN] if rc == 0 and out.strip() else None


def avaliar_fato_cruzado(root: Path, fato):
    """Recomputa o frescor do fato cruzado contra o disco de agora."""
    if not fato or not isinstance(fato, dict):
        return {"estado": "ausente"}
    mudou = []
    for proj, ref in (fato.get("derivado_de") or {}).items():
        proj_root = root / proj
        if not proj_root.is_dir():
            mudou.append("%s nao existe mais no workspace" % proj)
            continue
        head_agora = git_head_atual(proj_root)
        if ref.get("head") and head_agora and head_agora != ref["head"]:
            mudou.append("%s moveu de %s para %s"
                         % (proj, ref["head"], head_agora))
            continue
        sha_agora = deps_assinatura(proj_root)
        if ref.get("deps_sha") and sha_agora and sha_agora != ref["deps_sha"]:
            mudou.append("%s teve as deps regeradas" % proj)
    if mudou:
        return {"estado": "obsoleto", "mudou": mudou}
    return {"estado": "fresco"}


def m2_repo(explicito=None):
    if explicito:
        return Path(explicito).expanduser()
    env = os.environ.get("SCOS_MAP_M2") or os.environ.get("M2_REPO")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".m2" / "repository"


def _jar_do_snapshot(m2: Path, ga: str, versao: str):
    """Acha o jar instalado e devolve (path, mtime). Pega o mais recente."""
    try:
        grupo, artefato = ga.split(":", 1)
    except ValueError:
        return None, None
    d = m2.joinpath(*grupo.split(".")) / artefato / versao
    if not d.is_dir():
        return None, None
    melhor, melhor_mt = None, 0.0
    for j in d.glob("*.jar"):
        if j.name.endswith("-sources.jar") or j.name.endswith("-javadoc.jar"):
            continue
        try:
            mt = j.stat().st_mtime
        except OSError:
            continue
        if mt > melhor_mt:
            melhor, melhor_mt = j, mt
    return melhor, melhor_mt or None


def _ultimo_commit(proj_root: Path):
    rc, out, _ = run(["git", "log", "-1", "--format=%H|%at"], cwd=proj_root)
    if rc != 0 or "|" not in out:
        return None, None
    sha, ts = out.strip().split("|", 1)
    try:
        return sha[:SHA_LEN], int(ts)
    except ValueError:
        return sha[:SHA_LEN], None


def fact_snapshots_locais(root: Path, resumo, m2_path=None):
    """SNAPSHOT resolvido do ~/.m2 versus o fonte que esta ao lado.

    O consumidor resolve o jar instalado; o repositorio produtor pode estar
    a frente. Quem le o fonte do produtor e conclui sobre o consumidor
    conclui sobre codigo que nao esta rodando.
    """
    m2 = m2_repo(m2_path)

    # quem PRODUZ cada artefato dentro deste workspace
    produtores = {}
    for p_ in resumo:
        idx = root / p_["projeto"] / OUT_DIR / "index.json"
        if not idx.exists():
            continue
        try:
            data = json.loads(idx.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for _mid, m in (data.get("modulos") or {}).items():
            if m.get("artefato") and ":" in str(m["artefato"]):
                produtores[m["artefato"]] = p_["projeto"]

    # quem CONSOME snapshot
    consumo = {}
    for p_ in resumo:
        facts = root / p_["projeto"] / OUT_DIR / "facts"
        if not facts.is_dir():
            continue
        for tsv in list(facts.rglob("deps.tsv")) + \
                ([facts / "_transitivas_comuns.tsv"]
                 if (facts / "_transitivas_comuns.tsv").exists() else []):
            for i, linha in enumerate((read_text(tsv) or "").splitlines()):
                if i == 0 or not linha.strip():
                    continue
                col = linha.split("\t")
                if tsv.name == "_transitivas_comuns.tsv":
                    ga, versao = (col + ["", ""])[0], (col + ["", ""])[1]
                elif len(col) >= 3:
                    ga, versao = col[1], col[2]
                else:
                    continue
                if not versao or not versao.endswith("-SNAPSHOT"):
                    continue
                chave = (ga, versao)
                consumo.setdefault(chave, set()).add(p_["projeto"])

    itens = []
    for (ga, versao), projetos in sorted(consumo.items()):
        produtor = produtores.get(ga)
        # so interessa o snapshot cujo fonte esta NESTE workspace
        if not produtor or produtor in projetos and len(projetos) == 1:
            if not produtor:
                continue
        jar, mt = _jar_do_snapshot(m2, ga, versao)
        consumidores = sorted(projetos - {produtor})
        if not consumidores:
            continue
        item = {"ga": ga, "versao": versao, "consumido_por": consumidores,
                "produzido_por": produtor}
        head, ts_commit = _ultimo_commit(root / produtor)
        item["repo_local"] = {"head": head,
                              "ultimo_commit": ts_to_date(ts_commit)
                              if ts_commit else None}
        if jar is None:
            item["estado"] = "jar_ausente"
            item["acao"] = "mvn clean install em %s" % produtor
        else:
            item["jar_em_m2"] = {
                "path": str(jar).replace(str(Path.home()), "~"),
                "instalado_em": ts_to_date(int(mt)),
            }
            if ts_commit and mt < ts_commit:
                item["estado"] = "jar_desatualizado"
                item["acao"] = "mvn clean install em %s" % produtor
                item["atraso_dias"] = int((ts_commit - mt) // 86400)
            else:
                item["estado"] = "jar_atual"
        itens.append(item)

    return fact_envelope(
        "snapshots_locais", "_workspace",
        "mtime do jar em %s vs ultimo commit do repo produtor"
        % str(m2).replace(str(Path.home()), "~"),
        "media", {},
        extra={"itens": itens, "total": len(itens),
               "m2": str(m2).replace(str(Path.home()), "~")},
        completude="parcial",
        limitacoes=["mtime do jar nao e prova de conteudo: reinstalar sem "
                    "mudar codigo tambem atualiza o mtime",
                    "commit nao empurrado ou stash nao sao considerados"],
    )


def cmd_workspace(args):
    root = Path(args.root).resolve()
    if not root.is_dir():
        log("erro: %s nao e uma pasta" % root)
        return 1

    resolve_all(args)
    podas = []
    projetos = discover_projects(root, getattr(args, "max_depth", 3), podas)
    if len(projetos) == 1 and projetos[0] == root:
        log("%s parece ser um projeto unico, nao um workspace." % root.name)
        log("rodando 'scan' normal...")
        return cmd_scan(args)
    if not projetos:
        log("nenhum projeto encontrado em %s" % root)
        avisar_podas(podas, getattr(args, "max_depth", 3))
        return 1

    todos = list(projetos)
    if args.only:
        alvos = {a.strip() for a in args.only.split(",")}
        projetos = [p for p in projetos if p.name in alvos
                    or str(p.relative_to(root)) in alvos]
        if not projetos:
            log("nenhum projeto casa com --only %s" % args.only)
            return 1

    log("workspace: %s" % root)
    log("%d projeto(s): %s" % (len(projetos),
                               ", ".join(p.name for p in projetos)))
    avisar_podas(podas, getattr(args, "max_depth", 3))
    log("")
    preflight(args, projetos)

    t0 = time.time()
    resumo, falhas, versoes_ws = [], [], {}
    destaques_ws = {}
    for i, proj in enumerate(projetos, 1):
        rel = str(proj.relative_to(root))
        log("[%d/%d] %s" % (i, len(projetos), rel))
        try:
            index, _ = scan_one(proj, args, prefixo="        ")
        except Exception as e:  # noqa: BLE001
            log("        FALHOU: %s" % e)
            falhas.append({"projeto": rel, "erro": str(e)})
            continue

        obsoletos = [
            "%s/%s" % (mid, fname)
            for mid, m in index.get("modulos", {}).items()
            for fname, st in m.get("fatos", {}).items()
            if st.get("estado") == "obsoleto"
        ]
        met = index.get("_metricas", {})
        resumo.append({
            "projeto": rel,
            "index": "%s/%s/index.json" % (rel, OUT_DIR),
            "ecossistemas": index.get("ecossistemas", []),
            "modulos": list(index.get("modulos", {})),
            "arquivos": index.get("arquivos", {}).get("total", 0),
            "por_tipo": index.get("arquivos", {}).get("por_tipo", {}),
            "git": {k: index.get("git", {}).get(k)
                    for k in ("head", "branch", "dirty")},
            "tier_executado": index.get("tier_executado"),
            "fatos_obsoletos": obsoletos,
            "metricas": met,
        })

        for ga, vs in collect_versions(proj).items():
            for v, mods in vs.items():
                versoes_ws.setdefault(ga, {}).setdefault(v, []).extend(
                    "%s/%s" % (rel, m) for m in mods)
        merge_destaques(destaques_ws, collect_destaques(proj, rel))

    # --only reprocessa parte do workspace, mas o indice tem que continuar
    # descrevendo o TODO: reaproveita o mapa em disco dos nao processados.
    processados = {p["projeto"] for p in resumo}
    for proj in todos:
        rel = str(proj.relative_to(root))
        if rel in processados:
            continue
        idx = proj / OUT_DIR / "index.json"
        if not idx.exists():
            continue
        try:
            index = json.loads(idx.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        resumo.append({
            "projeto": rel,
            "index": "%s/%s/index.json" % (rel, OUT_DIR),
            "ecossistemas": index.get("ecossistemas", []),
            "modulos": list(index.get("modulos", {})),
            "arquivos": index.get("arquivos", {}).get("total", 0),
            "por_tipo": index.get("arquivos", {}).get("por_tipo", {}),
            "git": {k: index.get("git", {}).get(k)
                    for k in ("head", "branch", "dirty")},
            "tier_executado": index.get("tier_executado"),
            "fatos_obsoletos": [],
            "metricas": index.get("_metricas", {}),
            "nao_reprocessado_nesta_execucao": True,
        })
        for ga, vs in collect_versions(proj).items():
            for v, mods in vs.items():
                versoes_ws.setdefault(ga, {}).setdefault(v, []).extend(
                    "%s/%s" % (rel, m) for m in mods)
        merge_destaques(destaques_ws, collect_destaques(proj, rel))
    resumo.sort(key=lambda p: p["projeto"])

    conflitos = [
        {"ga": ga, "versoes": {v: sorted(set(m)) for v, m in vs.items()}}
        for ga, vs in sorted(versoes_ws.items()) if len(vs) > 1
    ]
    # so interessa conflito que cruza projeto, nao interno a um so
    conflitos_cruzados = [
        c for c in conflitos
        if len({m.split("/")[0] for vs in c["versoes"].values() for m in vs}) > 1
    ]

    # o fato cruzado e o unico que nenhum mapa individual enxerga - e era o
    # menos protegido: sem derivado_de, --only o remontava com cache velho
    derivado_cruzado, sujos, resolvidas_todas = {}, [], True
    for p_ in resumo:
        proj_root = root / p_["projeto"]
        derivado_cruzado[p_["projeto"]] = {
            "head": p_["git"].get("head"),
            "deps_sha": deps_assinatura(proj_root),
        }
        if p_["git"].get("dirty"):
            sujos.append(p_["projeto"])
    for p_ in resumo:
        idx = root / p_["projeto"] / OUT_DIR / "facts"
        for dj in idx.rglob("deps.json") if idx.is_dir() else []:
            try:
                if json.loads(dj.read_text(encoding="utf-8")).get(
                        "confianca") != "resolvida":
                    resolvidas_todas = False
            except Exception:  # noqa: BLE001
                resolvidas_todas = False

    limitacoes_cruzado = []
    if sujos:
        limitacoes_cruzado.append(
            "arvore suja em %s: o fato nao corresponde a nenhum commit"
            % ", ".join(sujos))
    if not resolvidas_todas:
        limitacoes_cruzado.append(
            "algum projeto ficou so com deps declaradas (mvn indisponivel)")

    fato_cruzado = fact_envelope(
        "conflitos_de_versao_cruzados", "_workspace",
        "deps.tsv + _transitivas_comuns.tsv + gerenciadas.tsv de cada "
        "projeto, sem scope test",
        "resolvida" if resolvidas_todas else "declarada",
        derivado_cruzado,
        extra={"itens": conflitos_cruzados, "total": len(conflitos_cruzados)},
        completude="parcial" if limitacoes_cruzado else "total",
        limitacoes=limitacoes_cruzado,
    )

    snaps = fact_snapshots_locais(root, resumo,
                                  getattr(args, "m2_repo", None))

    ws = {
        "schema_versao": SCHEMA_VERSAO,
        "gerador_versao": GERADOR_VERSAO,
        "tipo": "workspace",
        "gerado_em": now_iso(),
        "raiz": root.name,
        "como_usar": [
            "Cada projeto tem seu proprio mapa em <projeto>/.scos-map/index.json.",
            "Comece por 'projetos' aqui, escolha o projeto, e abra o index dele.",
            "conflitos_de_versao_cruzados compara bibliotecas ENTRE projetos - "
            "e o unico fato que nenhum mapa individual consegue enxergar.",
            "Reprocesse um projeto so com: workspace --only <nome>",
        ],
        "projetos": resumo,
        "descoberta": {
            "max_depth": getattr(args, "max_depth", 3),
            "podados_por_profundidade": podas,
        },
        "totais": {
            "projetos": len(resumo),
            "arquivos": sum(p["arquivos"] for p in resumo),
            "ecossistemas": sorted({e for p in resumo for e in p["ecossistemas"]}),
            "fatos_obsoletos": sum(len(p["fatos_obsoletos"]) for p in resumo),
        },
        "conflitos_de_versao_cruzados": fato_cruzado,
        "snapshots_locais": snaps,
        "achados": destaques_ws,
        "falhas": falhas,
    }
    ws_path = root / OUT_DIR / "workspace.json"
    size = write_json(ws_path, ws)

    log("")
    log("%-24s %-12s %-7s %s" % ("PROJETO", "ECOSSISTEMA", "ARQS", "REDUCAO"))
    for p in resumo:
        marca = " (cache)" if p.get("nao_reprocessado_nesta_execucao") else ""
        log("%-24s %-12s %-7s %sx%s" % (
            p["projeto"][:24], ",".join(p["ecossistemas"])[:12],
            p["arquivos"], p["metricas"].get("reducao", "-"), marca))
    log("")
    log("ok  %s  (%.1f KB)" % (ws_path, size / 1024))
    if falhas:
        log("    %d projeto(s) falharam" % len(falhas))
    log("    %.1fs no total" % (time.time() - t0))

    todos_obsoletos = [o for p in resumo for o in p["fatos_obsoletos"]]
    if limitacoes_cruzado:
        log("    fato cruzado com completude parcial: %s"
            % "; ".join(limitacoes_cruzado))
    print_destaques(destaques_ws, todos_obsoletos, conflitos_cruzados,
                    snaps.get("itens"))
    return 0


def cmd_status(args):
    root = Path(args.root).resolve()
    ws_path = root / OUT_DIR / "workspace.json"
    idx_path = root / OUT_DIR / "index.json"

    # workspace: delega o status para cada projeto
    if ws_path.exists() and not idx_path.exists():
        ws = json.loads(ws_path.read_text(encoding="utf-8"))
        print("workspace %s - mapeado em %s"
              % (ws.get("raiz"), ws.get("gerado_em")))
        cruzado = ws.get("conflitos_de_versao_cruzados")
        est = avaliar_fato_cruzado(root, cruzado)
        print("\n### _workspace/conflitos_de_versao_cruzados")
        print("  estado: %s" % est["estado"])
        for m in est.get("mudou", []):
            print("    - %s" % m)
        if est["estado"] == "obsoleto":
            print("    regenere o fato cruzado: scos-map workspace .")
        comp = (cruzado or {}).get("completude")
        if comp and comp.get("nivel") == "parcial":
            for l in comp.get("limitacoes", []):
                print("    ! %s" % l)

        total_obs = 1 if est["estado"] == "obsoleto" else 0
        for p in ws.get("projetos", []):
            proj_root = root / p["projeto"]
            sub = argparse.Namespace(root=str(proj_root))
            print("\n### %s" % p["projeto"])
            if not (proj_root / OUT_DIR / "index.json").exists():
                print("  sem mapa")
                continue
            total_obs += cmd_status_one(proj_root, indent="  ")
        print("\n%d fato(s) obsoleto(s) no workspace" % total_obs)
        if total_obs:
            print("regenere so o que mudou: scos-map workspace . --only <projeto>")
        return 0

    if not idx_path.exists():
        legado = root / ".aimap"
        if legado.exists():
            log("encontrei um mapa antigo em %s (a ferramenta se chamava "
                "aimap). O diretorio agora e %s - rode 'scan' de novo para "
                "regerar; o antigo pode ser apagado." % (legado, root / OUT_DIR))
        else:
            log("nenhum mapa em %s - rode 'scan' (ou 'workspace') primeiro"
                % (root / OUT_DIR))
        return 1
    print("mapa gerado em %s (tier %s)"
          % (json.loads(idx_path.read_text(encoding="utf-8")).get("gerado_em"),
             json.loads(idx_path.read_text(encoding="utf-8")).get("tier_executado")))
    cmd_status_one(root)
    return 0


def cmd_status_one(root: Path, indent=""):
    idx_path = root / OUT_DIR / "index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8"))

    git = MultiGit(root)
    modules, _ = detect_modules(root)
    files = scan_files(root, modules, git)
    by_path = {f["path"]: f["blob"] for f in files}

    print("%s%-28s %-11s %s" % (indent, "MODULO/FATO", "ESTADO", "DETALHE"))
    stale = 0
    for mid, m in index.get("modulos", {}).items():
        for nome, st in m.get("fatos", {}).items():
            arq = root / OUT_DIR / (st.get("arquivo") or "")
            estado, detalhe = st.get("estado"), ""
            if st.get("arquivo") and arq.exists():
                try:
                    fato = json.loads(arq.read_text(encoding="utf-8"))
                    novo = fact_state(fato, by_path, files, root)
                    estado = novo["estado"]
                    if novo.get("mudou"):
                        detalhe = "mudou: " + ", ".join(novo["mudou"][:3])
                    elif novo.get("motivo"):
                        detalhe = novo["motivo"][:60]
                except Exception:  # noqa: BLE001
                    pass
            elif st.get("motivo"):
                detalhe = st["motivo"][:60]
            if estado == "obsoleto":
                stale += 1
            print("%s%-28s %-11s %s"
                  % (indent, "%s/%s" % (mid, nome), estado, detalhe))
    if not indent:
        print("\n%d fato(s) obsoleto(s)" % stale)
    return stale


def main():
    ap = argparse.ArgumentParser(
        prog="scos-map",
        description="scos-map - indice estrutural dos repositorios SCOS "
                    "para consumo por IA")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="gera o mapa")
    s.add_argument("root", nargs="?", default=".")
    s.add_argument("--tier", type=int, default=None, choices=[1, 2, 3],
                   help="1=barato (padrao), 2=bytecode/jdeps, 3=callgraph")
    s.add_argument("--full", action="store_true",
                   help="regenera todos os fatos, ignorando o cache em disco")
    s.add_argument("--all", action="store_true",
                   help="faz tudo: tier 3 + compila sem perguntar + maven online")
    s.add_argument("--compile", action="store_true",
                   help="autoriza 'mvn compile' sem perguntar")
    s.add_argument("--no-compile", action="store_true",
                   help="nunca compila; reporta indisponivel")
    s.add_argument("--online", action="store_true",
                   help="permite que o maven baixe artefatos (padrao: -o)")
    s.add_argument("--callgraph-jar", default=None,
                   help="caminho do java-callgraph.jar (tier 3)")
    s.set_defaults(func=cmd_scan)

    w = sub.add_parser("workspace",
                       help="varre um workspace: mapeia CADA projeto e agrega")
    w.add_argument("root", nargs="?", default=".")
    w.add_argument("--tier", type=int, default=None, choices=[1, 2, 3])
    w.add_argument("--full", action="store_true",
                   help="regenera todos os fatos, ignorando o cache em disco")
    w.add_argument("--all", action="store_true",
                   help="faz tudo: tier 3 + compila sem perguntar + maven online")
    w.add_argument("--only", default=None,
                   help="reprocessa so estes projetos (nomes separados por virgula)")
    w.add_argument("--compile", action="store_true")
    w.add_argument("--no-compile", action="store_true")
    w.add_argument("--online", action="store_true")
    w.add_argument("--callgraph-jar", default=None)
    w.add_argument("--max-depth", type=int, default=3,
                   help="profundidade maxima na busca por projetos (default 3)")
    w.add_argument("--m2-repo", default=None,
                   help="repositorio local do Maven (default ~/.m2/repository)")
    w.set_defaults(func=cmd_workspace)

    t = sub.add_parser("status", help="mostra o frescor de cada fato")
    t.add_argument("root", nargs="?", default=".")
    t.set_defaults(func=cmd_status)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
