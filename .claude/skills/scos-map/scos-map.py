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
from datetime import datetime, timezone
from pathlib import Path

VERSION = "1.0"
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


def sha_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:7]


def read_text(path: Path, limit: int = 4_000_000):
    try:
        if path.stat().st_size > limit:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return None


def tsv_clean(v) -> str:
    if v is None:
        return ""
    return str(v).replace("\t", " ").replace("\n", " ").replace("\r", "")


def write_tsv(path: Path, header, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(header) + "\n")
        for r in rows:
            fh.write("\t".join(tsv_clean(c) for c in r) + "\n")
    return path.stat().st_size


def write_json(path: Path, obj) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return path.stat().st_size


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


class GitInfo:
    """Metadados por arquivo extraidos do git numa unica varredura."""

    def __init__(self, root: Path):
        self.root = root
        self.available = False
        self.head = None
        self.branch = None
        self.dirty = False
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
        self.head = out.strip()[:7] if rc == 0 and out.strip() else None
        rc, out, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=self.root)
        self.branch = out.strip() if rc == 0 else None
        rc, out, _ = run(["git", "status", "--porcelain"], cwd=self.root)
        self.dirty = bool(out.strip()) if rc == 0 else False

        rc, out, _ = run(["git", "ls-files", "-s"], cwd=self.root)
        if rc == 0:
            for line in out.splitlines():
                if "\t" not in line:
                    continue
                meta, path = line.split("\t", 1)
                parts = meta.split()
                if len(parts) >= 2:
                    self.blobs[path] = parts[1][:7]

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
                    sha = s[:7]
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
            self.blobs[path] = h[:7]
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


def fact_envelope(nome, modulo, fonte, confianca, derivado_de, extra=None):
    env = {
        "fato": nome,
        "modulo": modulo,
        "fonte": fonte,
        "confianca": confianca,
        "gerado_em": now_iso(),
        "derivado_de": derivado_de,
    }
    if extra:
        env.update(extra)
    return env


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

    itens, derivado = [], {}
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
            item["chaves"] = yaml_keys(t)[:300]
        elif f["ext"] in {".properties", ".conf"} or nome.startswith(".env"):
            item["chaves"] = props_keys(t)[:300]

        # perfis: por sufixo de nome e por declaracao interna
        perfis = []
        m = re.match(r"^application[-_]([\w-]+)\.(ya?ml|properties)$", nome, re.I)
        if m:
            perfis.append(m.group(1))
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
    return fact_envelope(
        "config", mid, "leitura de chaves (valores omitidos por seguranca)",
        "alta", derivado,
        {"aviso": "apenas nomes de chave e placeholders; nenhum valor foi lido",
         "perfis_detectados": todos_perfis,
         "arquivos": itens},
    )


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


def parse_dependency_tree(texto, self_ga=None):
    """Parseia a saida textual do dependency:tree.

    Aceita tanto o arquivo puro quanto o stdout com prefixo [INFO].
    A primeira linha e o proprio artefato e nao entra na lista.
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
        parts = s.split(":")
        if len(parts) < 4 or not re.match(r"^[\w.\-]+$", parts[0]):
            continue
        ga = "%s:%s" % (parts[0], parts[1])
        if not raiz_vista:
            raiz_vista = True
            if self_ga is None or ga == self_ga:
                continue        # o proprio modulo
        versao = parts[3] if len(parts) > 3 else None
        scope = parts[4].split()[0] if len(parts) > 4 else None
        deps.append({"ga": ga, "versao_resolvida": versao, "scope": scope})
    return deps


def _maven_resolved(root: Path, module, offline=True, timeout=240):
    """mvn dependency:tree. NAO compila - so resolve o grafo."""
    if not have("mvn"):
        return None, "mvn nao encontrado no PATH"
    mod_dir = root / module["path"] if module["path"] else root
    self_ga = None
    if module.get("_pom"):
        self_ga = "%s:%s" % (module["_pom"].get("groupId"),
                             module["_pom"].get("artifactId"))

    # a propriedade do dependency:tree e outputFile (mdep.outputFile e do
    # build-classpath); com -q e sem arquivo a arvore nao sai em lugar nenhum.
    alvo = mod_dir / "target" / ".scos-map-tree.txt"
    alvo.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["mvn", "-B", "-q", "dependency:tree", "-DoutputType=text",
           "-DoutputFile=%s" % alvo]
    if offline:
        cmd.insert(1, "-o")
    rc, out, err = run(cmd, cwd=mod_dir, timeout=timeout)

    texto = read_text(alvo) if alvo.exists() else None
    deps = parse_dependency_tree(texto, self_ga) if texto else []

    if not deps:
        # fallback: sem -q e sem arquivo, lendo a arvore do stdout
        cmd2 = ["mvn", "-B", "dependency:tree", "-DoutputType=text"]
        if offline:
            cmd2.insert(1, "-o")
        rc2, out2, err2 = run(cmd2, cwd=mod_dir, timeout=timeout)
        deps = parse_dependency_tree(out2, self_ga)
        if not deps:
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

    if "maven" in eco and module.get("_pom"):
        declaradas += _maven_declared(module["_pom"])
        fonte.append("pom.xml")
        p = module["_pom_path"]
        derivado[p] = next((f["blob"] for f in files if f["path"] == p), None)
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

    if not declaradas and resolvidas is None:
        return None

    res_map = {}
    for d in (resolvidas or []):
        res_map.setdefault(d["ga"], d["versao_resolvida"])

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
        {"ga": g, "versao_resolvida": v}
        for g, v in sorted(res_map.items()) if g not in declared_ga
    ]

    confianca = "resolvida" if resolvidas is not None else "declarada"
    env = fact_envelope("deps", module["id"], " + ".join(fonte) or "n/d",
                        confianca, derivado, {
                            "diretas": itens,
                            "divergencias": divergencias,
                            "transitivas": transitivas[:500],
                            "transitivas_total": len(transitivas),
                        })
    if resolvidas is None and motivo:
        env["resolucao_indisponivel"] = motivo
    return env


# ---------------------------------------------------------------------------
# Fato: docs (indice navegavel, nunca o conteudo)
# ---------------------------------------------------------------------------

MD_HEADER_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.M)
PROTO_SVC_RE = re.compile(r"^\s*service\s+(\w+)", re.M)
PROTO_RPC_RE = re.compile(r"^\s*rpc\s+(\w+)\s*\(", re.M)


def fact_docs(module, files, all_module_ids):
    mid = module["id"]
    mine = [f for f in files if f["module"] == mid
            and f["kind"] in {"doc", "contrato"}]
    if not mine:
        return None

    itens, derivado = [], {}
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

    return fact_envelope(
        "docs", mid, "cabecalhos markdown / declaracoes proto", "alta", derivado,
        {"aviso": "indice apenas - abra o arquivo pelo caminho para ler o conteudo",
         "itens": itens},
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


def jar_para_artefato(jarname):
    """spring-data-redis-4.1.1.jar -> spring-data-redis"""
    base = jarname.split("/")[-1]
    if base.endswith(".jar"):
        base = base[:-4]
    return re.sub(r"-\d[\w.\-]*$", "", base)


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
                  internos_reator=None):
    mid = module["id"]
    eco = module["ecossistema"]
    if "maven" not in eco and "gradle" not in eco:
        return fact_envelope("bytecode", mid, "n/d", "ausente", {}, {
            "estado": "nao_aplicavel",
            "motivo": "ecossistema %s nao produz bytecode JVM" % eco,
        })
    if module.get("tipo") == "pom":
        return fact_envelope("bytecode", mid, "n/d", "ausente", {}, {
            "estado": "nao_aplicavel",
            "motivo": "modulo agregador (packaging=pom) nao tem codigo",
        })
    if not have("jdeps"):
        return fact_envelope("bytecode", mid, "jdeps", "ausente", {}, {
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
            return fact_envelope("bytecode", mid, "jdeps", "ausente", {}, {
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
                        falhou = "compilou mas nao achou classes"
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
        return fact_envelope("bytecode", mid, "jdeps", "ausente", {}, {
            "estado": "indisponivel",
            "motivo": "jdeps abortou: %s" % erros[0][:200],
            "tentativas": tentativas,
            "comando_sugerido":
                "jdeps -verbose --multi-release base -cp <classpath> %s" % cdir})
    if rc != 0 and not out.strip():
        return fact_envelope("bytecode", mid, "jdeps", "ausente", {}, {
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
    usados_art = {jar_para_artefato(j) for j in jars}
    refs_por_art = {}
    for j, n in jars.items():
        a = jar_para_artefato(j)
        refs_por_art[a] = refs_por_art.get(a, 0) + n
    # so da para afirmar "ausente do pom" se as TRANSITIVAS foram mesmo
    # resolvidas; senao tudo que vem de starter viraria falso alarme.
    transitivas_confiaveis = bool(
        deps_fato and deps_fato.get("confianca") == "resolvida"
        and (deps_fato.get("transitivas_total") or 0) > 0)
    resolvidas_art = set()
    if transitivas_confiaveis:
        for d in (deps_fato.get("diretas") or []) + \
                 (deps_fato.get("transitivas") or []):
            resolvidas_art.add(d["ga"].split(":")[-1])
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
        "jdeps %s%s" % (" ".join(["-verbose"] + extra),
                        " com classpath" if cp else " sem classpath"),
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
        return fact_envelope("callgraph", mid, "n/d", "ausente", {}, {
            "estado": "nao_aplicavel",
            "motivo": "sem equivalente de bytecode para %s; grafo de chamada "
                      "so seria heuristico" % module["ecossistema"]})

    jar = find_callgraph_jar(jar_path)
    cdir = classes_dir(root, module)
    if jar is None:
        return fact_envelope("callgraph", mid, "java-callgraph", "ausente", {}, {
            "estado": "indisponivel",
            "motivo": "java-callgraph.jar nao encontrado",
            "comando_sugerido": "baixe o jar e passe --callgraph-jar <caminho> "
                                "ou coloque em ~/.scos-map/java-callgraph.jar",
            "lacunas_conhecidas": lacunas[:200],
            "entrypoints": entrypoints[:200]})
    if cdir is None:
        return fact_envelope("callgraph", mid, "java-callgraph", "ausente", {}, {
            "estado": "ausente", "motivo": "bytecode nao disponivel",
            "lacunas_conhecidas": lacunas[:200],
            "entrypoints": entrypoints[:200]})

    jars = sorted(str(p) for p in cdir.rglob("*.jar"))
    target = str(cdir)
    rc, out, err = run(["java", "-jar", str(jar), target], cwd=root, timeout=600)
    if rc != 0 and not out.strip():
        return fact_envelope("callgraph", mid, "java-callgraph", "ausente", {}, {
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


def build_index(root, modules, ecos, files, facts, git, tiers, sizes):
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

    return {
        "scos_map_versao": VERSION,
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
        "tier_executado": tiers,
        "arquivos": {"total": len(files), "por_tipo": kinds,
                     "tsv": "files.tsv"},
        "modulos": mods_idx,
        "reactor": "facts/_reactor.json",
        "tamanho_bytes": sizes,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


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

    sizes = {}
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
        ):
            fato = fn()
            if fato is not None:
                facts[mid][nome] = fato
                sizes["facts/%s/%s.json" % (mid, nome)] = write_json(
                    out_dir / "facts" / mid / ("%s.json" % nome), fato)
        deps_por_modulo[mid] = facts[mid].get("deps")

    reactor = fact_reactor(root, modules, files, deps_por_modulo)
    sizes["facts/_reactor.json"] = write_json(
        out_dir / "facts" / "_reactor.json", reactor)

    if args.tier >= 2:
        log("[5/5] tier 2 (bytecode)...")
        auto = True if args.compile else (False if args.no_compile else None)
        internos_reator = {m["_pom"].get("artifactId") for m in modules
                           if m.get("_pom") and m["_pom"].get("artifactId")}
        for m in modules:
            fato = fact_bytecode(root, m, files, out_dir, auto_compile=auto,
                                 offline=not args.online,
                                 deps_fato=facts.get(m["id"], {}).get("deps"),
                                 internos_reator=internos_reator)
            facts[m["id"]]["bytecode"] = fato
            sizes["facts/%s/bytecode.json" % m["id"]] = write_json(
                out_dir / "facts" / m["id"] / "bytecode.json", fato)

    if args.tier >= 3:
        log("      tier 3 (callgraph)...")
        for m in modules:
            fato = fact_callgraph(root, m, files, out_dir, args.callgraph_jar)
            facts[m["id"]]["callgraph"] = fato
            sizes["facts/%s/callgraph.json" % m["id"]] = write_json(
                out_dir / "facts" / m["id"] / "callgraph.json", fato)

    index = build_index(root, modules, ecos, files, facts, git, args.tier, sizes)
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


def discover_projects(root: Path, max_depth=3):
    """Acha os projetos de um workspace.

    Um diretorio e projeto se tem manifesto de build ou .git na raiz dele.
    Ao encontrar um, NAO desce mais: monorepo multi-modulo continua sendo
    UM projeto - a divisao interna em modulos e problema do scan_one.
    """
    found = []

    def walk(d: Path, depth: int):
        if depth > max_depth:
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


def collect_versions(proj_root: Path):
    """Le os deps.json de um projeto ja mapeado -> {ga: {versao: [modulos]}}."""
    out = {}
    facts_dir = proj_root / OUT_DIR / "facts"
    if not facts_dir.is_dir():
        return out
    for dj in facts_dir.glob("*/deps.json"):
        try:
            d = json.loads(dj.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        mod = d.get("modulo")
        for dep in d.get("diretas", []) + d.get("transitivas", []):
            v = dep.get("versao_resolvida") or dep.get("versao_declarada")
            if not v or str(v).startswith("${"):
                continue
            out.setdefault(dep["ga"], {}).setdefault(str(v), []).append(mod)
    return out


def collect_destaques(proj_root: Path, rel: str):
    """Le os fatos gravados e extrai o que um humano quer ver sem abrir JSON."""
    d = {"ciclos": [], "deps_nao_declaradas": [], "deps_nao_usadas": [],
         "divergencias": 0, "entrypoints": 0, "lacunas": 0,
         "tier2_indisponivel": [], "tier3_indisponivel": []}
    facts_dir = proj_root / OUT_DIR / "facts"
    if not facts_dir.is_dir():
        return d
    for fj in sorted(facts_dir.glob("*/*.json")):
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


def print_destaques(dz, obsoletos, conflitos):
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


def cmd_workspace(args):
    root = Path(args.root).resolve()
    if not root.is_dir():
        log("erro: %s nao e uma pasta" % root)
        return 1

    resolve_all(args)
    projetos = discover_projects(root)
    if len(projetos) == 1 and projetos[0] == root:
        log("%s parece ser um projeto unico, nao um workspace." % root.name)
        log("rodando 'scan' normal...")
        return cmd_scan(args)
    if not projetos:
        log("nenhum projeto encontrado em %s" % root)
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

    ws = {
        "scos_map_versao": VERSION,
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
        "totais": {
            "projetos": len(resumo),
            "arquivos": sum(p["arquivos"] for p in resumo),
            "ecossistemas": sorted({e for p in resumo for e in p["ecossistemas"]}),
            "fatos_obsoletos": sum(len(p["fatos_obsoletos"]) for p in resumo),
        },
        "conflitos_de_versao_cruzados": conflitos_cruzados,
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
    print_destaques(destaques_ws, todos_obsoletos, conflitos_cruzados)
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
        total_obs = 0
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
    w.add_argument("--all", action="store_true",
                   help="faz tudo: tier 3 + compila sem perguntar + maven online")
    w.add_argument("--only", default=None,
                   help="reprocessa so estes projetos (nomes separados por virgula)")
    w.add_argument("--compile", action="store_true")
    w.add_argument("--no-compile", action="store_true")
    w.add_argument("--online", action="store_true")
    w.add_argument("--callgraph-jar", default=None)
    w.set_defaults(func=cmd_workspace)

    t = sub.add_parser("status", help="mostra o frescor de cada fato")
    t.add_argument("root", nargs="?", default=".")
    t.set_defaults(func=cmd_status)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())