#!/usr/bin/env python3
"""Protótipo do frescor barato (FR-5): lê .git/HEAD sem subprocesso. Retorna os 12 primeiros caracteres
do commit ou None (ilegível => estado `desconhecido`). Trata HEAD destacado, `.git` como arquivo
(worktree), `commondir` e `packed-refs`. Nunca levanta exceção."""
import json, sys, time
from pathlib import Path

def head_atual(repo):
    try:
        g = Path(repo) / ".git"
        if g.is_file():                                   # worktree/submodule: "gitdir: <caminho>"
            g = Path(g.read_text().split(":", 1)[1].strip())
            if not g.is_absolute(): g = (Path(repo) / g).resolve()
        h = (g / "HEAD").read_text().strip()
        if not h.startswith("ref:"): return h[:12]        # HEAD destacado
        ref = h.split(None, 1)[1]
        common = g
        if (g / "commondir").exists():                    # worktree: refs vivem no repositório comum
            common = (g / (g / "commondir").read_text().strip()).resolve()
        for base in (g, common):
            p = base / ref
            if p.is_file(): return p.read_text().strip()[:12]
        for base in (g, common):
            pr = base / "packed-refs"
            if pr.is_file():
                for l in pr.read_text().splitlines():
                    if l.endswith(" " + ref): return l.split()[0][:12]
        return None
    except (OSError, IndexError, ValueError):
        return None

def estado(repo, gravado, dirty_na_geracao):
    """Regra de FR-5: head diferente => obsoleto; igual com mapa gerado sujo => desconhecido; igual e limpo => fresco."""
    a = head_atual(repo)
    if a is None: return "desconhecido"
    if a != gravado[:12]: return "obsoleto"
    return "desconhecido" if dirty_na_geracao else "fresco"

if __name__ == "__main__":
    repo = sys.argv[1]; idx = json.load(open(f"{repo}/.scos-map/index.json"))
    t = time.perf_counter(); e = estado(repo, idx["git"]["head"], idx["git"]["dirty"])
    print(e, f"{(time.perf_counter()-t)*1000:.2f}ms")
