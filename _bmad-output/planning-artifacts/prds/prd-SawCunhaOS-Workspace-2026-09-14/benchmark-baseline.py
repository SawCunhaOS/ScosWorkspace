#!/usr/bin/env python3
"""Benchmark canônico do scos-map-query (SM-1). Estimativa com PROXY do CLI: recorte mínimo
extraído do fato + envelope/rodapé de FR-5 + tetos de FR-9. Troque `cli_*` pelo CLI real quando existir.
Raiz do workspace: $SCOS_ROOT ou o ancestral mais próximo que contém .scos-map/workspace.json.
Requisitos: python3, jq e grep no PATH. Imprime os `gerado_em` dos mapas usados."""
import json, os, subprocess, time
from pathlib import Path
def _raiz():
    if os.environ.get("SCOS_ROOT"): return Path(os.environ["SCOS_ROOT"])
    for p in Path(__file__).resolve().parents:
        if (p / ".scos-map" / "workspace.json").exists(): return p
    raise SystemExit("raiz do workspace não encontrada (defina SCOS_ROOT)")
R = _raiz(); os.chdir(R)
import importlib.util
_s = importlib.util.spec_from_file_location("pf", Path(__file__).with_name("prototipo-frescor.py")); pf = importlib.util.module_from_spec(_s); _s.loader.exec_module(pf)
FL = "SawCunhaOS-Flow/.scos-map/facts/"
CAP_L, CAP_B, CUT = 50, 6000, 240

def sz(*ps): return sum(os.path.getsize(p) for p in ps)
def sh(c):
    t = time.perf_counter(); o = subprocess.run(c, shell=True, capture_output=True, text=True).stdout
    return len(o.encode()), (time.perf_counter() - t) * 1000, o
def gerado(repo): return json.load(open(f"{repo}/.scos-map/index.json"))["gerado_em"]
def estado_real(repo):
    idx = json.load(open(f"{repo}/.scos-map/index.json")); return pf.estado(repo, idx["git"]["head"], idx["git"]["dirty"])
REPO = {"flow": "SawCunhaOS-Flow", "bom": "sawcunha-open-system-bom"}
def hdr(fato, gerado_em, fontes=None, estado="obsoleto"):
    c = fato.get("confianca", "alta"); comp = (fato.get("completude") or {}).get("nivel")
    h = f"# confianca={c} estado={estado}" + (f" completude={comp}" if comp else "") + f" gerado={gerado_em}\n"
    if comp == "parcial": h += "# limitacao: " + "; ".join(fato["completude"]["limitacoes"])[:160] + "\n"
    return h
def cli(fato, g, lines, fontes):
    out, used = [], 0
    for l in lines:
        l = l[:CUT] + ("…" if len(l) > CUT else "")
        if len(out) >= CAP_L or used + len(l) + 1 > CAP_B: break
        out.append(l); used += len(l) + 1
    o = hdr(fato, g) + "\n".join(out) + ("\n" if out else "")
    o += f"# {len(out)} de {len(lines)} linhas casam | fontes: {fontes}\n"
    return o
def tsv(p, pred): return [r for r in open(p, encoding="utf-8").read().splitlines()[1:] if pred(r)]
def jq(f, expr): b, ms, _ = sh(f"jq -c '{expr}' {f}"); return b, ms
Q = []
def contar(cmd): return int(subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip() or 0)
def add(nome, read, grep, o, esperado, jqcmd=None, t_ms=0, n_esperado=None):
    assert esperado in o, f"{nome}: resposta do proxy não contém {esperado!r}"
    if n_esperado is not None:   # contagem independente (grep -c / jq length) das linhas de dados que casam
        m = [l for l in o.splitlines() if l.startswith("# ") and " linhas casam" in l][-1]
        assert m.split()[3] == str(n_esperado), f"{nome}: rodapé diz {m.split()[3]} linhas, contagem independente {n_esperado}"
    Q.append((nome, read, grep, len(o.encode()), jqcmd, t_ms))
def timed(fn):
    t = time.perf_counter(); r = fn(); return r, (time.perf_counter() - t) * 1000

# Q1 layout usecase
f1 = FL + "organization/flow-organization-usecase/layout.json"
(lay, t) = timed(lambda: json.load(open(f1)))
L = ["pacote_base=" + lay["pacote_base"]] + [f"{a['caminho'].split('/src/')[-1]}\t{a['papel']}\t{a['arquivos']}" for a in lay["areas"]]
add("Q1 pacote base e áreas do usecase", sz(f1), "grep -rh '^package ' --include=*.java SawCunhaOS-Flow/organization/flow-organization-usecase/src/main | sort -u",
    cli(lay, gerado("SawCunhaOS-Flow"), L, "layout.json"), "pacote_base", (f1, "{pacote_base,areas:[.areas[]|[.caminho,.papel]]}"), t, contar(f"jq '.areas|length+1' {f1}"))
# Q2 config
f2 = FL + "_raiz/config.json"; cfg, t = timed(lambda: json.load(open(f2)))
L = [a["path"] for a in cfg["arquivos"] if a["path"].startswith("etc/api/organization")]
add("Q2 arquivos de config em etc/api/organization", sz(f2), "find SawCunhaOS-Flow/etc/api/organization -name '*.y*ml'",
    cli(cfg, gerado("SawCunhaOS-Flow"), L, "config.json"), "etc/api/organization", (f2, '[.arquivos[]|.path|select(startswith("etc/api/organization"))]'), t,
    contar(f"jq '[.arquivos[]|.path|select(startswith(\"etc/api/organization\"))]|length' {f2}"))
# Q3 deps jackson (deps.tsv + transitivas + deps.json)
d = FL + "organization/flow-organization-usecase/"; tr = FL + "_transitivas_comuns.tsv"
L = tsv(d + "deps.tsv", lambda r: "jackson" in r.lower()) + tsv(tr, lambda r: "jackson" in r.lower())
add("Q3 dependências jackson do usecase (deps.tsv + transitivas)", sz(d + "deps.json", d + "deps.tsv", tr),
    f"grep -i jackson {d}deps.tsv {tr}", cli({"confianca": "resolvida"}, gerado("SawCunhaOS-Flow"), L, "deps.tsv, _transitivas_comuns.tsv"), "jackson", None, 0,
    contar(f"grep -ic jackson {d}deps.tsv") + contar(f"grep -ic jackson {tr}"))
assert L, "Q3: nenhuma linha de jackson — a pergunta não exercita nada"
# Q4 gerenciadas BOM
g = "sawcunha-open-system-bom/.scos-map/facts/_raiz/gerenciadas.tsv"
L = tsv(g, lambda r: "jackson" in r.lower())
add("Q4 versão de jackson gerenciada pela BOM", sz(g), "grep -n -i -A1 jackson sawcunha-open-system-bom/pom.xml",
    cli({"confianca": "resolvida"}, gerado("sawcunha-open-system-bom"), L, "gerenciadas.tsv"), "jackson")
# Q5 docs
f5 = FL + "_raiz/docs.json"; docs, t = timed(lambda: json.load(open(f5)))
L = [f"{i['path']}\t{i.get('titulo','')}\t{i['subtipo']}" for i in docs["itens"] if "nomenclatura" in (i["path"] + i.get("titulo", "")).lower()]
AVISO_DOCS = "# aviso: frontmatter lido literalmente; sem status não é rascunho; doc antiga + código recente = defasagem\n"
add("Q5 docs sobre nomenclatura (path/título)", sz(f5), "grep -ril nomenclatura --include=*.md SawCunhaOS-Flow --exclude-dir=node_modules --exclude-dir=.scos-map",
    AVISO_DOCS + cli(docs, gerado("SawCunhaOS-Flow"), L, "docs.json"), "NOMENCLATURA",
    (f5, '[.itens[]|select((.path+(.titulo//""))|ascii_downcase|contains("nomenclatura"))|[.path,.titulo]]'), t,
    contar(f"jq '[.itens[]|select((.path+(.titulo//\"\"))|ascii_downcase|contains(\"nomenclatura\"))]|length' {f5}"))
# Q6 reactor
f6 = FL + "_reactor.json"; rc, t = timed(lambda: json.load(open(f6)))
L = [f"{a['de']} -> {a['para']} ({a['scope']})" for a in rc["arestas_internas"] if a["de"].endswith("flow-organization-domain")]
add("Q6 dependências internas do flow-organization-domain", sz(f6), "grep -n 'flow-\\|scos-' SawCunhaOS-Flow/organization/flow-organization-domain/pom.xml",
    cli(rc, gerado("SawCunhaOS-Flow"), L, "_reactor.json"), "domain", (f6, '[.arestas_internas[]|select(.de|endswith("flow-organization-domain"))]'), t)
# Q7 conflitos (compacto: ga + versões -> repositórios)
w = json.load(open(".scos-map/workspace.json")); c = w["conflitos_de_versao_cruzados"]
L = [i["ga"] + "\t" + " | ".join(f"{v}:{','.join(sorted({m.split('/')[0] for m in ms}))}" for v, ms in i["versoes"].items()) for i in c["itens"]]
add("Q7 conflitos de versão cruzados", sz(".scos-map/workspace.json"), None, cli(c, w["gerado_em"], L, "workspace.json"), "annotations",
    (".scos-map/workspace.json", ".conflitos_de_versao_cruzados.itens|map({ga,v:(.versoes|keys)})"))
# Q8 snapshots agrupados por produtor (default) — todos os 10 já estão jar_desatualizado (caso sem mistura: ver limitação)
sn = w["snapshots_locais"]; grp = {}
for i in sn["itens"]: grp.setdefault(i["produzido_por"], []).append(i)
L = [f"{p}\t{len(v)} jar(s)\t{','.join(sorted({x['estado'] for x in v}))}\tmax_atraso={max(x['atraso_dias'] for x in v)}d\t{v[0]['acao']}" for p, v in grp.items()]
add("Q8 SNAPSHOTs locais (agrupado por produtor)", sz(".scos-map/workspace.json"), None, cli(sn, w["gerado_em"], L, "workspace.json"), "Foundation",
    (".scos-map/workspace.json", ".snapshots_locais.itens|group_by(.produzido_por)|map({p:.[0].produzido_por,n:length})"))
# Q11 testes do usecase (resumo: frameworks, tipos, cobertura) e arquivos de teste de um alvo
f11 = d + "tests.json"; tj, t = timed(lambda: json.load(open(f11)))
L = ["raizes=" + ",".join(tj["raizes"]), f"arquivos={tj['arquivos']} por_tipo={json.dumps(tj['por_tipo'])}",
     "frameworks=" + ",".join(f"{x['nome']}({x['origem']})" for x in tj["frameworks"]), "cobertura=" + tj["cobertura"]["estado"]]
add("Q11 frameworks e tipos de teste do usecase", sz(f11),
    "grep -rhE '^import (org.assertj|org.junit|org.mockito)' SawCunhaOS-Flow/organization/flow-organization-usecase/src/test | sort -u",
    cli(tj, gerado("SawCunhaOS-Flow"), L, "tests.json"), "cobertura=nao_analisado", (f11, "{raizes,por_tipo,frameworks:[.frameworks[]|.nome],cobertura:.cobertura.estado}"), t)
# Q12 bytecode: dependências usadas via transitiva
f12 = d + "bytecode.json"; bj, t = timed(lambda: json.load(open(f12)))
L = [f"{x['artefato']}\t{x['referencias']}" for x in bj["deps_usadas_via_transitiva"]]
add("Q12 deps usadas via transitiva (bytecode.json)", sz(f12), None,
    cli(bj, gerado("SawCunhaOS-Flow"), L, "bytecode.json"), "jackson-annotations", (f12, ".deps_usadas_via_transitiva|map(.artefato)"), t)
# Q9 e Q10 arestas (Q10 = pergunta quente: 107 arestas)
e = FL + "organization/flow-organization-usecase/bytecode_edges.tsv"
for nome, pat in (("Q9 arestas de ValidateAuthorityUseCase", "ValidateAuthorityUseCase"), ("Q10 arestas com ScosPaginated (pergunta quente)", "ScosPaginated")):
    L = tsv(e, lambda r: pat in r)
    o = cli({"confianca": "alta"}, gerado("SawCunhaOS-Flow"), L, "bytecode_edges.tsv")
    add(nome, sz(e), f"grep {pat} {e}", o, pat, None, 0, contar(f"grep -c {pat} {e}"))
    if "Q10" in nome:
        todas = hdr({"confianca": "alta"}, gerado("SawCunhaOS-Flow")) + "\n".join(L) + f"\n# {len(L)} de {len(L)} linhas casam | fontes: bytecode_edges.tsv\n"
        print(f"  (Q10: {len(L)} linhas casam; CLI padrão = {len(o.encode())} B truncado; com --all = {len(todas.encode())} B, contra {sh(f'grep {pat} {e}')[0]} B do grep)")
print("mapas usados (gerado_em):", {r: gerado(r) for r in ("SawCunhaOS-Flow", "SawCunhaOS-Foundation", "sawcunha-open-system-bom")}, "| workspace:", w["gerado_em"])
print("%-60s %8s %7s %6s %6s | %7s %7s %s" % ("pergunta", "Read", "grep", "jq", "CLI", "CLI/Rd", "CLI/gr", "ok"))
for n, rd, gc, cl, jqc, t_ms in Q:
    gb = sh(gc)[0] if gc else None
    jb = jq(*jqc)[0] if jqc else None
    ok = (cl <= 0.10 * rd) and (gb is None or cl <= max(gb + 64, 1.1 * gb))
    print("%-60s %8d %7s %6s %6d | %6.1f%% %7s %s" % (n, rd, gb if gb is not None else "n/a", jb if jb is not None else "n/a", cl, 100 * cl / rd, ("%.2fx" % (cl / gb) if gb else "n/a"), "✔" if ok else "✘"))

tm = max(q[5] for q in Q); t0 = time.perf_counter(); subprocess.run(["python3", "-c", "pass"]); st = (time.perf_counter() - t0) * 1000
print(f"latência (proxy): maior carga de JSON = {tm:.0f} ms; partida do Python = {st:.0f} ms; jq por chamada = {jq(f2, '.fato')[1]:.0f} ms")
