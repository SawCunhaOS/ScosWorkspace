"""Suite do scos-map-query (Story 1.1: layout ponta a ponta)."""

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fixtures as fx

RAIZ = Path(__file__).resolve().parent.parent
ENTRY = RAIZ / "scos-map-query.py"
PACOTE = RAIZ / "scos_map_query"
GOLDEN = Path(__file__).resolve().parent / "golden"
TEM_GIT = shutil.which("git") is not None
sys.path.insert(0, str(RAIZ))

from scos_map_query import fatos  # noqa: E402
from scos_map_query.cli import resolver  # noqa: E402
from scos_map_query.comandos import layout  # noqa: E402
from scos_map_query.modelo import ErroConsulta  # noqa: E402
from scos_map_query.render import tsv_clean  # noqa: E402


def consultar(cwd, *args, env_extra=None, sem_git=False):
    env = dict(os.environ)
    if sem_git:
        env["PATH"] = os.pathsep.join(
            d for d in env.get("PATH", "").split(os.pathsep)
            if not os.path.exists(os.path.join(d, "git")))
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, str(ENTRY), *args], cwd=str(cwd),
                       capture_output=True, text=True, env=env, timeout=60)
    return p.returncode, p.stdout, p.stderr


@unittest.skipUnless(TEM_GIT, "git indisponivel")
class BaseMapa(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)

    def mapa(self, **kw):
        fx.mapa_sintetico(self.base, **kw)
        return self.base / "proj"  # subpasta do workspace


class TestLayout(BaseMapa):
    def test_golden_de_subpasta_do_workspace(self):
        sub = self.mapa()
        rc, out, err = consultar(sub, "layout", "proj", "app")
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(out, (GOLDEN / "layout.txt").read_text(encoding="utf-8"))

    def test_exemplo_da_ajuda_e_saida_real(self):
        rc, out, _ = consultar(self.mapa(), "layout", "proj", "app")
        self.assertIn(layout.EXEMPLO, out)
        n = len(layout.EXEMPLO.splitlines())
        self.assertTrue(3 <= n <= 5)

    def test_help_e_ajuda_literal_sem_stderr(self):
        rc, out, err = consultar(self.mapa(), "layout", "--help")
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(out, layout.AJUDA)
        self.assertLessEqual(len(layout.AJUDA.encode()), 1500)

    def test_celula_com_tab_e_quebra_de_linha(self):
        lay = dict(fx.LAYOUT_APP, areas=[
            {"caminho": "a\tb\r\nc", "papel": "x\ty", "arquivos": 1}])
        _, out, _ = consultar(self.mapa(layout=lay), "layout", "proj", "app")
        self.assertIn("a b c\tx y\t1\n", out)
        self.assertEqual(tsv_clean("a\t\r\nb"), "a b")

    def test_sem_confianca_e_completude_parcial(self):
        lay = {k: v for k, v in fx.LAYOUT_APP.items() if k != "confianca"}
        lay["completude"] = {"nivel": "parcial", "limitacoes": ["so main"]}
        _, out, _ = consultar(self.mapa(layout=lay), "layout", "proj", "app")
        linhas = out.splitlines()
        self.assertTrue(linhas[0].startswith(
            "# confianca=- estado=fresco completude=parcial gerado="))
        self.assertEqual(linhas[1], "# limitacao: so main")


class TestEstado(BaseMapa):
    def test_head_diferente_nunca_fresco(self):
        _, out, _ = consultar(self.mapa(head="aaaaaaaaaaaa"), "layout", "proj", "app")
        self.assertIn("estado=obsoleto", out.splitlines()[0])
        self.assertNotIn("estado=fresco", out)

    def test_estado_obsoleto_do_indice_prevalece(self):
        _, out, _ = consultar(self.mapa(estado="obsoleto"), "layout", "proj", "app")
        self.assertIn("estado=obsoleto", out.splitlines()[0])

    def test_head_ilegivel_e_desconhecido(self):
        sub = self.mapa()
        shutil.rmtree(sub / ".git")
        _, out, _ = consultar(sub, "layout", "proj", "app")
        cab = out.splitlines()[0]
        self.assertIn("estado=desconhecido", cab)
        self.assertNotIn("commits_desde_o_mapa", cab)

    def test_packed_refs_continua_fresco(self):
        sub = self.mapa()
        subprocess.run(["git", "pack-refs", "--all"], cwd=str(sub), capture_output=True)
        _, out, _ = consultar(sub, "layout", "proj", "app")
        self.assertIn("estado=fresco", out.splitlines()[0])

    def test_barra_final_e_fato_malformado(self):
        sub = self.mapa()
        rc, _, _ = consultar(sub, "layout", "proj/", "app/")
        self.assertEqual(rc, 0)
        (sub / ".scos-map/facts/app/layout.json").write_text("[1]")
        rc, out, _ = consultar(sub, "layout", "proj", "app")
        self.assertEqual(rc, 3)
        self.assertIn("formato inesperado", out)

    def test_head_do_indice_invalido_nao_vira_opcao_do_git(self):
        _, out, _ = consultar(self.mapa(head="--output=x"), "layout", "proj", "app")
        self.assertNotIn("commits_desde_o_mapa", out.splitlines()[0])

    def test_commits_desde_com_hash_de_12_chars(self):
        sub = self.mapa()
        real = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(sub),
                              capture_output=True, text=True).stdout.strip()
        (sub / "novo.txt").write_text("x")
        for a in (["add", "-A"], ["commit", "-qm", "novo"]):
            subprocess.run(["git", *a], cwd=str(sub), capture_output=True)
        # o mapa gravou 12 chars do HEAD antigo: um commit depois
        self.assertEqual(len(real[:12]), 12)
        _, out, _ = consultar(sub, "layout", "proj", "app")
        cab = out.splitlines()[0]
        self.assertIn("estado=obsoleto", cab)
        self.assertTrue(cab.endswith("commits_desde_o_mapa=1"), cab)

    def test_sem_git_no_path_omite_commits_mas_mantem_estado(self):
        _, out, _ = consultar(self.mapa(), "layout", "proj", "app", sem_git=True)
        cab = out.splitlines()[0]
        self.assertIn("estado=fresco", cab)
        self.assertNotIn("commits_desde_o_mapa", cab)


class TestSchema(BaseMapa):
    def test_constante_unica(self):
        self.assertEqual(fatos.SCHEMA_TESTADO, (2, 1))
        achados = [p.name for p in PACOTE.rglob("*.py")
                   if "SCHEMA_TESTADO =" in p.read_text(encoding="utf-8")]
        self.assertEqual(achados, ["fatos.py"])

    def test_versoes(self):
        rc, out, _ = consultar(self.mapa(schema="2.0"), "layout", "proj", "app")
        self.assertEqual(rc, 0)
        self.assertNotIn("# aviso", out)

    def test_minor_mais_novo_avisa_e_nao_compara_string(self):
        rc, out, _ = consultar(self.mapa(schema="2.10"), "layout", "proj", "app")
        self.assertEqual(rc, 0)
        self.assertIn("# aviso: schema 2.10 mais novo que o testado (2.1)", out)

    def test_major_diferente_sai_com_4(self):
        rc, out, err = consultar(self.mapa(schema="3.0"), "layout", "proj", "app")
        self.assertEqual((rc, err), (4, ""))
        self.assertTrue(out.startswith("# erro: "), out)
        self.assertEqual(len(out.splitlines()), 1)

    def test_schema_do_indice_tambem_e_checado(self):
        rc, out, _ = consultar(self.mapa(schema_indice="1.0"), "layout", "proj", "app")
        self.assertEqual(rc, 4)


class TestErros(BaseMapa):
    def _erro(self, esperado, *args, sub=None):
        sub = sub or self.mapa()
        rc, out, err = consultar(sub, *args)
        self.assertEqual((rc, err), (esperado, ""), out)
        self.assertEqual(len(out.splitlines()), 1, out)
        self.assertRegex(out, r"^# erro: .+ \| acao: .+\n$")
        self.assertNotIn("Traceback", out)
        return out

    def test_sem_workspace_json(self):
        with tempfile.TemporaryDirectory() as d:
            out = self._erro(3, "layout", "proj", "app", sub=Path(d))
        self.assertIn("scos-map.py workspace", out)

    def test_projeto_e_modulo_inexistentes(self):
        self._erro(3, "layout", "nada", "app")
        self._erro(3, "layout", "proj", "nada")

    def test_uso_invalido(self):
        self._erro(2, "layout", "proj")  # modulo ausente em escopo modulo
        self._erro(2, "layout")  # projeto ausente
        self._erro(2, "inexistente", "proj")

    def test_basename_ambiguo_lista_opcoes(self):
        out = self._erro(2, "layout", "proj", "core")
        self.assertIn("app/core", out)
        self.assertIn("lib/core", out)

    def test_basename_unico_resolve(self):
        rc, out, _ = consultar(self.mapa(), "layout", "proj", "app")
        self.assertEqual(rc, 0)

    def test_resolver_modulo_em_escopo_de_projeto(self):
        ws = {"projetos": [{"projeto": "p", "modulos": ["a"]}]}
        with self.assertRaises(ErroConsulta) as c:
            resolver(ws, "projeto", "p", "a")
        self.assertEqual(c.exception.codigo, 2)
        self.assertEqual(resolver(ws, "projeto", "p", None)[1], None)

    def test_fato_ausente_sai_com_3(self):
        self._erro(3, "layout", "proj", "lib/core")  # modulo sem fato layout

    def test_erro_interno_e_debug(self):
        sub = self.mapa()
        (sub / ".scos-map" / "facts" / "app" / "layout.json").write_text(
            '{"areas": 7}')
        rc, out, err = consultar(sub, "layout", "proj", "app")
        self.assertEqual((rc, err), (1, ""))
        # fato ja lido: envelope + erro + rodape (AD-12); sem traceback
        self.assertIn("# erro: interno | acao: -\n", out)
        self.assertNotIn("Traceback", out)
        rc, out, err = consultar(sub, "layout", "proj", "app",
                                 env_extra={"SCOS_MAP_QUERY_DEBUG": "1"})
        self.assertEqual(rc, 1)
        self.assertIn("Traceback", out)


class TestTeto(BaseMapa):
    def _layout(self, n_areas=60, caminho="d"):
        return dict(fx.LAYOUT_APP, areas=[
            {"caminho": "%s%02d" % (caminho, i), "papel": "p", "arquivos": i}
            for i in range(n_areas)])

    def _dados(self, out):
        return [l for l in out.splitlines() if not l.startswith("#")
                and not l.startswith("## ")]

    def test_corte_por_linhas_golden(self):
        rc, out, err = consultar(self.mapa(layout=self._layout()), "layout",
                                 "proj", "app")
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(out, (GOLDEN / "layout_truncado.txt").read_text(
            encoding="utf-8"))
        self.assertLessEqual(len(self._dados(out)), 50)

    def test_secao_cortada_continua_visivel_sem_all_primeiro(self):
        _, out, _ = consultar(self.mapa(layout=self._layout()), "layout",
                              "proj", "app")
        self.assertIn("## entrypoints (0 de 2)\tpath\ttipo\trota", out)
        trunc = [l for l in out.splitlines() if l.startswith("# truncado:")]
        self.assertEqual(len(trunc), 1)
        self.assertTrue(trunc[0].startswith("# truncado: use --limit"), trunc)
        self.assertEqual(out.splitlines()[-2], trunc[0])

    def test_corte_por_bytes(self):
        lay = self._layout(10, "x" * 200)
        _, out, _ = consultar(self.mapa(layout=lay), "layout", "proj", "app",
                              "--bytes", "500")
        dados = self._dados(out)
        self.assertLessEqual(sum(len(l.encode()) + 1 for l in dados), 500)
        self.assertIn("# truncado: use --bytes", out)

    def test_limit_all_e_ordem_preservada(self):
        sub = self.mapa(layout=self._layout())
        _, out, _ = consultar(sub, "layout", "proj", "app", "--limit", "3")
        self.assertEqual([l.split("\t")[0] for l in self._dados(out)][1:],
                         ["d00", "d01"])
        _, out, _ = consultar(sub, "layout", "proj", "app", "--all")
        self.assertNotIn("# truncado", out)
        self.assertIn("# 63 de 63 linhas casam", out)

    def test_all_com_limit_ou_bytes_e_erro_2(self):
        sub = self.mapa()
        for extra in (["--limit", "5"], ["--bytes", "5"]):
            rc, out, err = consultar(sub, "layout", "proj", "app", "--all", *extra)
            self.assertEqual((rc, err), (2, ""))
            self.assertEqual(len(out.splitlines()), 1)
        rc, _, _ = consultar(sub, "layout", "proj", "app", "--limit", "0")
        self.assertEqual(rc, 2)

    def test_linha_longa_truncada_e_all_nao_desliga(self):
        lay = self._layout(1, "y" * 300)
        for flags in ([], ["--all"]):
            _, out, _ = consultar(self.mapa(layout=lay), "layout", "proj",
                                  "app", *flags)
            longas = [l for l in out.splitlines() if l.startswith("yyy")]
            self.assertEqual(len(longas), 1)
            self.assertEqual(len(longas[0]), 240)
            self.assertTrue(longas[0].endswith("\u2026"))

    def test_marca_nunca_cortada(self):
        from scos_map_query.modelo import Secao
        from scos_map_query.render import _linha
        sec = Secao("s", ["a", "marca"], [], 0)
        l = _linha(sec, ["z" * 300, "[heuristica]"])
        self.assertEqual(len(l), 240)
        self.assertTrue(l.endswith("\u2026\t[heuristica]"))

    def test_resumo_fora_do_teto(self):
        from scos_map_query.modelo import Resultado, Secao
        from scos_map_query.render import montar
        res = Resultado([
            Secao("resumo", ["k"], [["r%d" % i] for i in range(20)], 20,
                  tipo="resumo"),
            Secao("d", ["k"], [["x%d" % i] for i in range(60)], 60)])
        out = montar(res, [])
        self.assertIn("## resumo (20 de 20)", out)
        self.assertIn("## d (50 de 60)", out)
        self.assertTrue(out.endswith("# 50 de 60 linhas casam | fontes: -"))

    def test_teto_consumido_entre_secoes_e_bytes_utf8(self):
        from scos_map_query.modelo import Opcoes, Resultado, Secao
        from scos_map_query.render import montar
        res = Resultado([
            Secao("a", ["k"], [["x%d" % i] for i in range(3)], 3),
            Secao("b", ["k"], [["\u00e7\u00e7\u00e7"] for _ in range(5)], 5)])
        out = montar(res, [], Opcoes(limit=5))
        self.assertIn("## a (3 de 3)", out)
        self.assertIn("## b (2 de 5)", out)
        # 3 linhas "xN\n" = 9 B; "\u00e7\u00e7\u00e7\n" = 7 B em UTF-8: 9 + 7 cabe em 16, 23 nao
        out = montar(res, [], Opcoes(bytes=16))
        self.assertIn("## b (1 de 5)", out)

    def test_base_so_com_flag(self):
        sub = self.mapa()
        _, out, _ = consultar(sub, "layout", "proj", "app")
        self.assertNotIn("# base:", out)
        _, out, _ = consultar(sub, "layout", "proj", "app", "--base")
        self.assertIn("# base: %s\n" % fx.LAYOUT_APP["base"], out)


class TestLog(BaseMapa):
    def _registros(self, caminho):
        return [l.split("\t") for l in
                caminho.read_text(encoding="utf-8").splitlines()]

    def test_registro_de_sucesso_e_bytes_utf8(self):
        sub = self.mapa()
        rc, out, _ = consultar(sub, "layout", "proj", "app")
        (reg,) = self._registros(self.base / ".scos-map-query.log")
        self.assertRegex(reg[0], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(reg[1:4], ["layout", "proj", "app"])
        self.assertEqual(reg[4], str(len(out.encode("utf-8"))))
        self.assertEqual(reg[5], str(out.count("\n")))
        self.assertEqual(reg[6:], ["0", "2.1"])
        # de dentro do repo vale o mesmo: acrescenta no log da raiz
        consultar(sub, "layout", "proj", "app")
        self.assertEqual(len(self._registros(self.base / ".scos-map-query.log")), 2)

    def test_erros_1_e_2_gravam_com_codigo(self):
        sub = self.mapa()
        consultar(sub, "layout", "proj")  # uso invalido
        reg = self._registros(self.base / ".scos-map-query.log")[-1]
        self.assertEqual((reg[1], reg[2], reg[3], reg[6]), ("layout", "proj", "-", "2"))
        (sub / ".scos-map" / "facts" / "app" / "layout.json").write_text(
            '{"areas": 7}')
        consultar(sub, "layout", "proj", "app")
        self.assertEqual(self._registros(self.base / ".scos-map-query.log")[-1][6], "1")

    def test_sem_workspace_nao_grava(self):
        with tempfile.TemporaryDirectory() as d:
            rc, _, _ = consultar(Path(d), "layout", "proj", "app")
            self.assertEqual(rc, 3)
            self.assertEqual(os.listdir(d), [])

    def test_env_substitui_caminho(self):
        alt = self.base / "alt.log"
        consultar(self.mapa(), "layout", "proj", "app",
                  env_extra={"SCOS_MAP_QUERY_LOG": str(alt)})
        self.assertEqual(len(self._registros(alt)), 1)
        self.assertFalse((self.base / ".scos-map-query.log").exists())

    def test_log_nao_gravavel_nao_afeta_resposta(self):
        rc, out, err = consultar(self.mapa(), "layout", "proj", "app",
                                 env_extra={"SCOS_MAP_QUERY_LOG":
                                            str(self.base / "nada" / "x.log")})
        self.assertEqual((rc, err), (0, ""))
        self.assertTrue(out.startswith("# confianca="))

    def test_registrar_engole_qualquer_falha(self):
        from scos_map_query.render import _registrar
        _registrar("x", (str(self.base / "a.log"), ["layout", "p\udcff", "-", 0, "2.1"]))
        _registrar("x", None)  # nao levanta

    def test_gitignore_da_raiz_lista_o_log(self):
        gi = (RAIZ.parent.parent / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/.scos-map-query.log", gi.splitlines())


class TestConfigDocs(BaseMapa):
    def _ok(self, *args):
        rc, out, err = consultar(self.mapa(), *args)
        self.assertEqual((rc, err), (0, ""), out)
        return out

    def test_config_golden_e_valores_nunca_aparecem(self):
        out = self._ok("config", "proj", "app")
        self.assertEqual(out, (GOLDEN / "config.txt").read_text(encoding="utf-8"))
        self.assertNotIn("SEGREDO_NUNCA_MOSTRAR", out)

    def test_config_prefixo(self):
        out = self._ok("config", "proj", "app", "--prefixo",
                       "app/src/main/resources/application-")
        self.assertIn("## arquivos (1 de 1)", out)
        self.assertIn("application-dev.yml\t340", out)

    def test_docs_golden_aviso_e_limitacao(self):
        out = self._ok("docs", "proj", "app")
        self.assertEqual(out, (GOLDEN / "docs.txt").read_text(encoding="utf-8"))
        aviso = [l for l in out.splitlines() if l.startswith("# aviso:")]
        self.assertEqual(len(aviso), 1)
        self.assertLessEqual(len(aviso[0].split(": ", 1)[1].encode()), 100)

    def test_docs_texto_sem_caixa_em_path_ou_titulo(self):
        self.assertIn("## documentos (1 de 1)",
                      self._ok("docs", "proj", "app", "--texto", "CACHE"))
        self.assertIn("## documentos (1 de 1)",
                      self._ok("docs", "proj", "app", "--texto", "readme"))
        self.assertIn("## documentos (1 de 1)",
                      self._ok("docs", "proj", "app", "--prefixo", "app/docs/adr"))

    def test_sem_resultado_traz_cabecalho_zero_linhas_e_rodape(self):
        out = self._ok("docs", "proj", "app", "--texto", "zzz")
        self.assertTrue(out.startswith("# confianca="))
        self.assertIn("## documentos (0 de 0)", out)
        self.assertRegex(out, r"# 0 de 0 linhas casam \| fontes: .*docs\.json\n$")

    def test_texto_nao_casa_o_placeholder_de_titulo_ausente(self):
        docs = dict(fx.DOCS_APP, itens=[{"path": "a.md", "subtipo": "outro"}])
        _, out, _ = consultar(self.mapa(docs=docs), "docs", "proj", "app",
                              "--texto", "-")
        self.assertIn("## documentos (0 de 0)", out)

    def test_flag_invalida_e_uma_linha_de_erro(self):
        rc, out, err = consultar(self.mapa(), "docs", "proj", "app", "--nada", "x")
        self.assertEqual((rc, err), (2, ""))
        self.assertEqual(len(out.splitlines()), 1)

    def test_exemplos_da_ajuda_sao_saida_real_de_3_a_5_linhas(self):
        from scos_map_query.comandos import config, docs
        for m in (config, docs):
            self.assertTrue(3 <= len(m.EXEMPLO.splitlines()) <= 5, m.NOME)
            self.assertLessEqual(len(m.AJUDA.encode()), 1500, m.NOME)
            rc, out, err = consultar(self.mapa(), m.NOME, "--help")
            self.assertEqual((rc, out, err), (0, m.AJUDA, ""))


class TestPacote(unittest.TestCase):
    PERMITIDOS = {"modelo", "filtros", "re", "typing", "dataclasses", "collections"}
    PROIBIDOS = {"open", "print", "input"}

    def _arquivos(self, sub=""):
        return sorted((PACOTE / sub).rglob("*.py"))

    def test_comandos_so_importam_lista_branca_e_sem_io(self):
        comandos = [p for p in self._arquivos("comandos") if p.stem != "__init__"]
        self.assertTrue(comandos)
        for p in comandos:
            for no in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if isinstance(no, ast.Import):
                    mods = [a.name.split(".")[0] for a in no.names]
                elif isinstance(no, ast.ImportFrom):
                    mods = [(no.module or "").split(".")[0]]
                else:
                    mods = []
                for m in mods:
                    self.assertIn(m, self.PERMITIDOS, "%s importa %s" % (p.name, m))
                if isinstance(no, ast.Name):
                    self.assertNotIn(no.id, self.PROIBIDOS, p.name)
                if isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name):
                    self.assertNotIn((no.value.id, no.attr),
                                     {("sys", "stdout"), ("os", "environ")}, p.name)

    def test_so_stdlib_e_nao_importa_o_gerador(self):
        for p in self._arquivos():
            for no in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if isinstance(no, ast.Import):
                    mods = [a.name for a in no.names]
                elif isinstance(no, ast.ImportFrom) and not no.level:
                    mods = [no.module]
                else:
                    continue
                for m in mods:
                    self.assertIn(m.split(".")[0], sys.stdlib_module_names, p.name)
                    self.assertNotIn("scos-map", m)
                    self.assertNotIn("scos_map.", m + ".")

    def test_environ_so_em_cli_e_render(self):
        for p in self._arquivos():
            if p.name not in ("cli.py", "render.py"):
                self.assertNotIn("environ", p.read_text(encoding="utf-8"), p.name)

    def test_nenhum_arquivo_casa_test_asterisco(self):
        self.assertEqual([p for p in self._arquivos() if p.name.startswith("test")], [])

    def test_python_3_10(self):
        proibidos = {"tomllib", "UTC", "StrEnum", "Self", "ExceptionGroup"}
        for p in self._arquivos():
            arvore = ast.parse(p.read_text(encoding="utf-8"),
                               feature_version=(3, 10))
            for no in ast.walk(arvore):
                self.assertNotIsInstance(no, getattr(ast, "TryStar", ()), p.name)
                nome = (no.id if isinstance(no, ast.Name)
                        else no.attr if isinstance(no, ast.Attribute)
                        else getattr(no, "module", None))
                self.assertNotIn(nome, proibidos, p.name)

    def test_entry_nao_importa_o_gerador(self):
        self.assertNotIn("scos_map\n", ENTRY.read_text(encoding="utf-8"))



class TestTabelasEReactor(BaseMapa):
    def _ok(self, *args):
        rc, out, err = consultar(self.mapa(), *args)
        self.assertEqual((rc, err), (0, ""), out)
        return out

    def test_reactor_secoes_na_ordem_do_fato(self):
        out = self._ok("reactor", "proj").splitlines()
        self.assertIn("## modulos (3 de 3)\tid\ttipo", out)
        self.assertIn("## arestas (1 de 1)\tde\tpara\tscope", out)
        self.assertIn("app\tlib/core\tcompile", out)
        self.assertEqual(out[-1], "# 4 de 4 linhas casam | fontes: "
                         "proj/.scos-map/facts/_reactor.json")

    def test_goldens(self):
        casos = {"reactor": ["reactor", "proj"],
                 "gerenciadas": ["gerenciadas", "proj", "app"],
                 "arquivos": ["arquivos", "proj", "--em-modulo", "app"],
                 "deps": ["deps", "proj", "app"]}
        sub = self.mapa()
        for nome, args in casos.items():
            _, out, _ = consultar(sub, *args)
            self.assertEqual(out, (GOLDEN / (nome + ".txt")).read_text(
                encoding="utf-8"), nome)

    def test_projeto_rejeita_modulo_posicional(self):
        rc, out, _ = consultar(self.mapa(), "reactor", "proj", "app")
        self.assertEqual(rc, 2)

    def test_gerenciadas_e_filtro_ga(self):
        out = self._ok("gerenciadas", "proj", "app", "--ga", "KAFKA")
        self.assertIn("## gerenciadas (1 de 1)\tga\tversao\torigem\tscope", out)
        self.assertIn("spring-kafka-bom\t4.1.1\tpropria\timport", out)
        self.assertNotIn("errorprone", out)

    def test_gerenciadas_ausente_e_erro_3(self):
        rc, out, _ = consultar(self.mapa(), "gerenciadas", "proj", "lib/core")
        self.assertEqual(rc, 3)

    def test_arquivos_equivale_aos_awk_congelados(self):
        base = [l.split("\t") for l in fx.FILES_TSV.splitlines()[1:]]
        out = self._ok("arquivos", "proj", "--em-modulo", "app", "--kind", "codigo")
        esperado = [l[0] for l in base if l[4] == "app" and l[5] == "codigo"]
        achado = [l.split("\t")[0] for l in out.splitlines() if l.startswith("app/")]
        self.assertEqual(achado, esperado)
        out = self._ok("arquivos", "proj", "--commits-90d-min", "6")
        esperado = [l[0] for l in base if int(l[9]) > 5]
        achado = [l.split("\t")[0] for l in out.splitlines()
                  if "\t" in l and not l.startswith("##")]
        self.assertEqual(achado, esperado)
        self.assertIn("# aviso: historico de arquivo nao esta no mapa", out)

    def test_arquivos_filtro_invalido_e_uma_linha(self):
        rc, out, err = consultar(self.mapa(), "arquivos", "proj",
                                 "--commits-90d-min", "muitos")
        self.assertEqual((rc, err), (2, ""))
        self.assertEqual(len(out.splitlines()), 1)

    def test_deps_une_diretas_e_transitivas(self):
        out = self._ok("deps", "proj", "app")
        self.assertIn("io.jsonwebtoken:jjwt-api\t0.12.6\tcompile\teffective-pom\t",
                      out)
        self.assertIn("com.x:y\t1.0\truntime\ttransitiva\t[transitiva]", out)
        self.assertIn("## transitivas (1 de 1)\tga\tversao\tscope\tmarca", out)
        self.assertIn("org.jspecify:jspecify\t1.0.1\tcompile\t[transitiva]", out)
        self.assertEqual(out.count("_transitivas_comuns.tsv("), 1)
        self.assertIn("# fontes: ", out)

    def test_deps_todos_modulos_agrupa_fontes(self):
        out = self._ok("deps", "proj", "--todos-modulos", "--ga", "jjwt")
        self.assertIn("# fontes: deps.json\u00d72(resolvida,fresco)", out)
        self.assertIn("# fontes: deps.tsv\u00d72(resolvida,fresco)", out)
        self.assertIn("lib/core\tio.jsonwebtoken:jjwt-impl\t0.12.6", out)
        self.assertIn("app\tio.jsonwebtoken:jjwt-api\t0.12.6", out)
        self.assertNotIn("com.x:y", out)
        self.assertEqual(out.count("_transitivas_comuns.tsv"), 2)  # fonte + rodape

    def test_limitacao_repetida_sai_uma_vez(self):
        sub = self.mapa()
        for m in ("app", "lib/core"):
            f = sub / (".scos-map/facts/%s/deps.json" % m)
            d = json.loads(f.read_text())
            d["completude"] = {"nivel": "parcial", "limitacoes": ["so pom"]}
            f.write_text(json.dumps(d))
        _, out, _ = consultar(sub, "deps", "proj", "--todos-modulos")
        self.assertEqual(out.count("# limitacao: so pom"), 1)

    def test_deps_indisponivel_e_resultado_normal_com_estado(self):
        rc, out, _ = consultar(self.mapa(estado="indisponivel"), "deps", "proj", "app")
        self.assertEqual(rc, 0)
        self.assertIn("estado=indisponivel", out.splitlines()[0])
        self.assertIn("## dependencias (0 de 0)", out)

    def test_pipe_fechado_nao_escreve_em_stderr(self):
        sub = self.mapa()
        err = sub / "err.txt"
        subprocess.run("%s %s reactor proj 2>%s | head -c1" % (
            sys.executable, ENTRY, err), shell=True, cwd=str(sub),
            capture_output=True)
        self.assertEqual(err.read_text(), "")

    def test_modulo_vazio_apos_normalizar_e_uso_invalido(self):
        rc, _, _ = consultar(self.mapa(), "layout", "proj", "./")
        self.assertEqual(rc, 2)

    def test_todos_modulos_so_existe_em_deps(self):
        rc, _, _ = consultar(self.mapa(), "gerenciadas", "proj", "--todos-modulos")
        self.assertEqual(rc, 2)

    def test_deps_com_tsv_ausente_e_erro_3_citando_o_arquivo(self):
        sub = self.mapa()
        (sub / ".scos-map/facts/lib/core/deps.tsv").unlink()
        rc, out, _ = consultar(sub, "deps", "proj", "--todos-modulos")
        self.assertEqual(rc, 3)
        self.assertIn("lib/core/deps.tsv ausente", out)

    def test_help_de_cada_novo_subcomando(self):
        for nome in ("reactor", "gerenciadas", "arquivos", "deps"):
            rc, out, err = consultar(self.mapa(), nome, "--help")
            self.assertEqual((rc, err), (0, ""))
            self.assertLessEqual(len(out.encode()), 1500, nome)
            n = len(out.split("Exemplo:\n")[1].strip().splitlines())
            self.assertTrue(3 <= n <= 5, nome)


if __name__ == "__main__":
    unittest.main()
