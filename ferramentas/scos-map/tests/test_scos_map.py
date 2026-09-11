"""Suite do scos-map. Roda com: python -m unittest discover -s tests

Cada teste amarra um comportamento que ja quebrou uma vez ou que a skill de
consulta depende para nao afirmar demais. Sem rede, sem Maven, sem pip.
"""

import importlib.util
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
SCRIPT = RAIZ / "scos-map.py"


def carregar_modulo():
    spec = importlib.util.spec_from_file_location("scos_map", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sm = carregar_modulo()
TEM_GIT = shutil.which("git") is not None
TEM_JAVAC = shutil.which("javac") is not None


def rodar(args, cwd, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    # sem mvn, como o README promete: com ele a suite depende do ~/.m2 local
    env["PATH"] = os.pathsep.join(
        d for d in env.get("PATH", "").split(os.pathsep)
        if not os.path.exists(os.path.join(d, "mvn")))
    p = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=str(cwd),
                       capture_output=True, text=True, env=env, timeout=300)
    return p.returncode, p.stdout + p.stderr


def ler_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def ler_tsv(p):
    linhas = [l for l in Path(p).read_text(encoding="utf-8").splitlines() if l]
    cab = linhas[0].split("\t")
    return cab, [dict(zip(cab, l.split("\t"))) for l in linhas[1:]]


class BaseFixture(unittest.TestCase):
    """Cria a fixture num diretorio temporario proprio."""

    construir = None

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="scosmap-"))
        self.base = self.tmp / "repo"
        self.base.mkdir()
        if self.construir:
            type(self).construir.__func__(self.base) \
                if hasattr(type(self).construir, "__func__") \
                else self.construir(self.base)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scan(self, *args):
        rc, out = rodar(["scan", ".", *args], self.base)
        self.assertEqual(rc, 0, out)
        return out

    def fato(self, modulo, nome):
        return ler_json(self.base / ".scos-map/facts" / modulo /
                        ("%s.json" % nome))

    def indice(self):
        return ler_json(self.base / ".scos-map/index.json")


# ---------------------------------------------------------------------------
# Formato e contrato (schema 2.0)
# ---------------------------------------------------------------------------

class TestContrato(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.maven_simples(self.base)
        self.scan()

    def test_indice_declara_schema_e_gerador(self):
        idx = self.indice()
        self.assertEqual(idx["schema_versao"], sm.SCHEMA_VERSAO)
        self.assertIn("gerador_versao", idx)

    def test_gerado_em_so_no_indice(self):
        self.assertIn("gerado_em", self.indice())
        for nome in ("layout", "deps", "config"):
            p = self.base / ".scos-map/facts/_raiz" / ("%s.json" % nome)
            if p.exists():
                self.assertNotIn("gerado_em", ler_json(p),
                                 "%s nao deve carimbar tempo" % nome)

    def test_json_e_compacto_e_sem_campo_vazio(self):
        bruto = (self.base / ".scos-map/facts/_raiz/layout.json").read_text()
        self.assertNotIn('": ', bruto, "JSON deveria estar compacto")
        self.assertNotIn("[]", bruto, "lista vazia deveria ser podada")

    def test_sha_tem_12_caracteres(self):
        _cab, linhas = ler_tsv(self.base / ".scos-map/files.tsv")
        for l in linhas:
            if l["blob"]:
                self.assertEqual(len(l["blob"]), 12, l["path"])

    def test_segundo_scan_nao_reescreve_nada(self):
        out = self.scan()
        self.assertIn("nenhum fato mudou", out)

    def test_tabelas_declaram_colunas(self):
        tabelas = self.indice()["tabelas"]
        self.assertIn("files.tsv", tabelas)
        for rel, meta in tabelas.items():
            self.assertTrue(meta["colunas"], rel)
            cab, _ = ler_tsv(self.base / ".scos-map" / rel)
            self.assertEqual(cab, meta["colunas"],
                             "cabecalho de %s diverge do indice" % rel)


class TestEnvelope(unittest.TestCase):
    def test_confianca_fora_do_vocabulario_e_rejeitada(self):
        with self.assertRaises(ValueError):
            sm.fact_envelope("x", "m", "b", "excelente", {})

    def test_confianca_nula_e_permitida_para_fato_sem_dado(self):
        env = sm.fact_envelope("x", "m", "n/d", None, {},
                               {"estado": "nao_aplicavel"})
        self.assertIsNone(env["confianca"])

    def test_desvio_exige_confianca_valida(self):
        with self.assertRaises(ValueError):
            sm.desvio("ga", "a:b", "meia-boca", "motivo")

    def test_poda_preserva_false_e_zero(self):
        d = sm.podar({"a": [], "b": None, "c": "", "d": False, "e": 0,
                      "f": {"g": []}})
        self.assertEqual(d, {"d": False, "e": 0})


# ---------------------------------------------------------------------------
# Config: a confianca acompanha o parser realmente usado
# ---------------------------------------------------------------------------

class TestYamlComplexo(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.yaml_complexo(self.base)

    def test_varredor_perde_chave_de_merge_key(self):
        texto = fx.YAML_COMPLEXO
        regex = sm.yaml_keys(texto)
        real = sm.yaml_keys_pyyaml(texto)
        perdidas = [k for k in real if k not in regex]
        self.assertIn("cliente.timeout", perdidas,
                      "a fixture precisa exercitar ancora/merge key")

    def test_com_pyyaml_confianca_alta(self):
        self.scan()
        f = self.fato("_raiz", "config")
        self.assertEqual(f["confianca"], "alta")
        self.assertIn("PyYAML", f["base"])
        self.assertNotIn("completude", f)

    def test_sem_pyyaml_rebaixa_e_lista_limitacoes(self):
        stub = self.tmp / "stub"
        stub.mkdir()
        (stub / "yaml.py").write_text('raise ImportError("sem PyYAML")\n')
        rc, out = rodar(["scan", "."], self.base,
                        {"PYTHONPATH": str(stub)})
        self.assertEqual(rc, 0, out)
        f = self.fato("_raiz", "config")
        self.assertEqual(f["confianca"], "media")
        self.assertEqual(f["completude"]["nivel"], "parcial")
        self.assertTrue(f["completude"]["limitacoes"])

    def test_perfil_de_documento_secundario(self):
        self.scan()
        self.assertIn("prod", self.fato("_raiz", "config")["perfis_detectados"])

    def test_nenhum_valor_de_config_e_gravado(self):
        self.scan()
        bruto = (self.base / ".scos-map/facts/_raiz/config.json").read_text()
        self.assertNotIn("http://a", bruto)
        self.assertNotIn("WARN", bruto)


class TestProperties(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.properties_simples(self.base)
        self.scan()

    def test_chaves_sem_valores(self):
        f = self.fato("_raiz", "config")
        arq = f["arquivos"][0]
        self.assertIn("spring.datasource.url", arq["chaves"])
        self.assertNotIn("8080", json.dumps(arq))

    def test_placeholders_de_ambiente(self):
        arq = self.fato("_raiz", "config")["arquivos"][0]
        self.assertIn("DB_URL", arq["placeholders"])


# ---------------------------------------------------------------------------
# Maven: precedencia e conflito
# ---------------------------------------------------------------------------

class TestBomImport(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.maven_bom_import(self.base)
        self.scan()

    def test_versao_do_bom_vem_do_effective_pom(self):
        _cab, linhas = ler_tsv(
            self.base / ".scos-map/facts/consumidor/deps.tsv")
        jjwt = [l for l in linhas if "jjwt-api" in l["ga"]][0]
        self.assertEqual(jjwt["versao"], "0.12.6")
        self.assertEqual(jjwt["origem"], "effective-pom")

    def test_conflito_vira_desvio_com_os_dois_valores(self):
        f = self.fato("consumidor", "deps")
        confs = [d for d in f.get("desvios", [])
                 if d["confianca"] == "conflito"]
        self.assertEqual(len(confs), 1, f.get("desvios"))
        d = confs[0]
        self.assertEqual(d["versao_parse_pom"], "2.0.9")
        self.assertEqual(d["versao_effective_pom"], "2.0.18")

    def test_maven_ganha_o_valor_gravado(self):
        _cab, linhas = ler_tsv(
            self.base / ".scos-map/facts/consumidor/deps.tsv")
        slf = [l for l in linhas if "slf4j-api" in l["ga"]][0]
        self.assertEqual(slf["versao"], "2.0.18")

    def test_sem_effective_pom_declara_completude_parcial(self):
        os.remove(self.base / "consumidor/target/.scos-map-effective.xml")
        shutil.rmtree(self.base / ".scos-map")
        self.scan()
        f = self.fato("consumidor", "deps")
        self.assertEqual(f["completude"]["nivel"], "parcial")
        self.assertTrue(any("effective-pom" in l
                            for l in f["completude"]["limitacoes"]))


class TestParentProperty(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.maven_parent_property(self.base)
        self.scan()

    def test_property_do_parent_e_resolvida(self):
        _cab, linhas = ler_tsv(self.base / ".scos-map/facts/filho/deps.tsv")
        jack = [l for l in linhas if "jackson-databind" in l["ga"]][0]
        self.assertEqual(jack["versao"], "2.17.0")


class TestMultimodulo(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.maven_multimodulo(self.base)
        self.scan()

    def test_reator_lista_os_modulos(self):
        r = ler_json(self.base / ".scos-map/facts/_reactor.json")
        ids = {m["id"] for m in r["modulos"]}
        self.assertLessEqual({"alpha", "beta"}, ids)

    def test_conflito_de_versao_entre_modulos(self):
        r = ler_json(self.base / ".scos-map/facts/_reactor.json")
        gas = {c["ga"] for c in r.get("conflitos_de_versao", [])}
        self.assertIn("com.fasterxml.jackson.core:jackson-databind", gas)

    def test_aresta_interna_entre_modulos(self):
        r = ler_json(self.base / ".scos-map/facts/_reactor.json")
        pares = {(a["de"], a["para"]) for a in r.get("arestas_internas", [])}
        self.assertIn(("beta", "alpha"), pares)


class TestArvoreDeDependencias(unittest.TestCase):
    """None = nao ha arvore deste modulo; [] = arvore sem dependencias."""

    def test_classifier_nao_vira_versao(self):
        texto = fx.arvore_tree("br.com.sawcunhaos:svc:jar:1.0", [
            "+- io.github.openfeign.querydsl:querydsl-apt:jar:jpa:7.6:provided",
            "\\- org.slf4j:slf4j-api:jar:2.0.18:compile (optional)"])
        self.assertEqual(
            sm.parse_dependency_tree(texto, "br.com.sawcunhaos:svc"), [
                {"ga": "io.github.openfeign.querydsl:querydsl-apt",
                 "versao_resolvida": "7.6", "scope": "provided"},
                {"ga": "org.slf4j:slf4j-api",
                 "versao_resolvida": "2.0.18", "scope": "compile"}])

    def test_arvore_de_outro_modulo_e_rejeitada(self):
        texto = fx.arvore_tree("br.com.sawcunhaos:filho:jar:1.0",
                               ["+- org.x:lib:jar:1.0:compile"])
        self.assertIsNone(
            sm.parse_dependency_tree(texto, "br.com.sawcunhaos:flow"))

    def test_zero_dependencias_e_fato_nao_ausencia(self):
        self.assertEqual(sm.parse_dependency_tree(
            "br.com.sawcunhaos:flow:pom:1.0\n", "br.com.sawcunhaos:flow"), [])
        self.assertIsNone(
            sm.parse_dependency_tree("", "br.com.sawcunhaos:flow"))


class TestAgregador(BaseFixture):
    def test_agregador_nao_herda_a_arvore_do_filho(self):
        fx.agregador_com_arvore_de_filho(self.base)
        self.scan()
        tsv = self.base / ".scos-map/facts/_raiz/deps.tsv"
        gas = {l["ga"] for l in ler_tsv(tsv)[1]} if tsv.exists() else set()
        self.assertNotIn("org.apache.httpcomponents:httpclient", gas)
        self.assertNotIn("br.com.sawcunhaos:m0", gas)


# ---------------------------------------------------------------------------
# Fecho transitivo comum
# ---------------------------------------------------------------------------

class TestFechoTransitivo(BaseFixture):
    def setUp(self):
        super().setUp()
        _b, self.comuns = fx.fecho_transitivo(self.base, n_modulos=4,
                                              n_comuns=12)
        self.scan()

    def test_fecho_gravado_uma_vez(self):
        p = self.base / ".scos-map/facts/_transitivas_comuns.tsv"
        self.assertTrue(p.exists())
        _cab, linhas = ler_tsv(p)
        # 12 comuns menos a que diverge no ultimo modulo
        self.assertEqual(len(linhas), 11)

    def test_divergente_volta_para_o_modulo(self):
        _cab, l0 = ler_tsv(self.base / ".scos-map/facts/m0/deps.tsv")
        _cab, l3 = ler_tsv(self.base / ".scos-map/facts/m3/deps.tsv")
        v0 = [l["versao"] for l in l0 if l["ga"].endswith("spring-lib00")]
        v3 = [l["versao"] for l in l3 if l["ga"].endswith("spring-lib00")]
        self.assertEqual(v0, ["7.0.0"])
        self.assertEqual(v3, ["6.0.0"])

    def test_envelope_avisa_que_a_lista_esta_dividida(self):
        f = self.fato("m0", "deps")
        self.assertTrue(f["transitivas_no_fecho_comum"] > 0)
        self.assertIn("_transitivas_comuns.tsv", f["aviso_fecho"])

    def test_fecho_nao_esconde_lib_ausente_em_um_modulo(self):
        """Interseccao estrita: presente em todos, com a mesma versao."""
        _cab, fecho = ler_tsv(
            self.base / ".scos-map/facts/_transitivas_comuns.tsv")
        gas = {l["ga"] for l in fecho}
        self.assertNotIn("org.springframework:spring-lib00", gas)


# ---------------------------------------------------------------------------
# Frescor
# ---------------------------------------------------------------------------

@unittest.skipUnless(TEM_GIT, "git indisponivel")
class TestFrescor(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.maven_simples(self.base)
        self.scan()

    def status(self):
        rc, out = rodar(["status", "."], self.base)
        return out

    def test_limpo_fica_fresco(self):
        self.assertIn("0 fato(s) obsoleto(s)", self.status())

    def test_alteracao_nao_commitada_invalida(self):
        alvo = self.base / "src/main/java/br/com/scos/OrgService.java"
        alvo.write_text(alvo.read_text() + "// muda\n")
        out = self.status()
        self.assertIn("obsoleto", out)
        self.assertIn("OrgService.java", out)

    def test_artefato_do_proprio_mapa_nao_conta_como_sujeira(self):
        g = sm.GitInfo(self.base)
        self.assertFalse(g.dirty,
                         "o .scos-map recem-gerado nao pode sujar a arvore")


@unittest.skipUnless(TEM_JAVAC and TEM_GIT, "javac/git indisponiveis")
class TestFrescorBytecode(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.maven_simples(self.base)
        classes = self.base / "target/classes"
        classes.mkdir(parents=True)
        subprocess.run(
            ["javac", "-d", str(classes),
             str(self.base / "src/main/java/br/com/scos/OrgService.java")],
            capture_output=True)
        self.scan("--tier", "2", "--no-compile")

    def test_assinatura_das_classes_gravada(self):
        f = self.fato("_raiz", "bytecode")
        self.assertIn("assinatura_classes", f)
        self.assertEqual(f["assinatura_classes"]["classes"], 1)

    def test_recompilacao_de_codigo_gerado_invalida(self):
        """Fonte fora de src/main (gerado) muda o bytecode: tem que pegar."""
        gerado = self.base / "target/generated-sources/g/G.java"
        gerado.parent.mkdir(parents=True, exist_ok=True)
        gerado.write_text("package g;\npublic class G {}\n")
        subprocess.run(["javac", "-d", str(self.base / "target/classes"),
                        str(gerado)], capture_output=True)
        rc, out = rodar(["status", "."], self.base)
        self.assertIn("bytecode recompilado", out)

    def test_teste_nao_invalida_o_bytecode(self):
        t = self.base / "src/test/java/br/com/scos/OrgServiceTest.java"
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_text("package br.com.scos;\npublic class OrgServiceTest {}\n")
        rc, out = rodar(["status", "."], self.base)
        linha = [l for l in out.splitlines() if "_raiz/bytecode" in l]
        self.assertTrue(linha and "fresco" in linha[0], out)


# ---------------------------------------------------------------------------
# Testes (fato tests)
# ---------------------------------------------------------------------------

class TestFatoTests(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.testes_multiplas_raizes(self.base)
        self.scan()

    def test_classifica_por_tipo(self):
        f = self.fato("_raiz", "tests")
        self.assertEqual(f["por_tipo"].get("unit"), 1)
        self.assertEqual(f["por_tipo"].get("integration"), 1)
        self.assertEqual(f["por_tipo"].get("architecture"), 1)

    def test_framework_declarado_tem_procedencia_melhor(self):
        f = self.fato("_raiz", "tests")
        por_nome = {x["nome"]: x for x in f["frameworks"]}
        self.assertEqual(por_nome["JUnit 5"]["origem"], "declarada")
        self.assertEqual(por_nome["ArchUnit"]["origem"], "declarada")

    def test_regras_archunit_nomeadas(self):
        f = self.fato("_raiz", "tests")
        regras = {r["regra"] for r in f["regras_arquiteturais"]}
        self.assertIn("dominioNaoDependeDeInfra", regras)

    def test_cobertura_nunca_e_afirmada(self):
        f = self.fato("_raiz", "tests")
        self.assertEqual(f["cobertura"]["estado"], "nao_analisado")

    def test_alvo_e_declarado_heuristico(self):
        f = self.fato("_raiz", "tests")
        self.assertIn("alvo_heuristico", f["corpo_colunas"])
        self.assertTrue(any("heuristica" in l
                            for l in f["completude"]["limitacoes"]))

    def test_ausencia_e_redigida_como_nao_identificado(self):
        f = self.fato("vazio", "tests")
        self.assertEqual(f["classes"], 0)
        self.assertIn("nenhum arquivo de teste identificado",
                      f["observacao_ausencia"])
        self.assertTrue(f["raizes"], "precisa citar as raizes varridas")

    def test_archtest_fora_da_raiz_maven_e_capturado(self):
        _cab, linhas = ler_tsv(self.base / ".scos-map/facts/_raiz/tests.tsv")
        paths = {l["path"] for l in linhas}
        self.assertTrue(any("archtest/" in p for p in paths), paths)


# ---------------------------------------------------------------------------
# Diagnostico do bytecode
# ---------------------------------------------------------------------------

@unittest.skipUnless(TEM_GIT, "git indisponivel")
class TestBytecodeDiagnostico(BaseFixture):
    def test_sem_aresta_explica_o_motivo(self):
        binpath = fx.bytecode_sem_aresta(self.base)
        rc, out = rodar(["scan", ".", "--tier", "2", "--no-compile"],
                        self.base,
                        {"PATH": "%s:%s" % (binpath, os.environ["PATH"])})
        self.assertEqual(rc, 0, out)
        f = self.fato("_raiz", "bytecode")
        self.assertEqual(f["arestas_total"], 0)
        self.assertTrue(f["motivo_vazio"],
                        "TSV vazio nunca pode ficar sem explicacao")
        self.assertTrue(f["amostra_saida"],
                        "precisa guardar a saida crua para diagnostico")
        self.assertIn("diagnostico", f)

    def test_dep_usada_e_ausente_do_pom_e_destacada(self):
        binpath = fx.dep_usada_ausente_do_pom(self.base)
        rc, out = rodar(["scan", ".", "--tier", "2", "--no-compile"],
                        self.base,
                        {"PATH": "%s:%s" % (binpath, os.environ["PATH"])})
        self.assertEqual(rc, 0, out)
        f = self.fato("_raiz", "bytecode")
        ausentes = [x["artefato"]
                    for x in f.get("deps_usadas_ausentes_do_pom", [])]
        self.assertIn("guava", ausentes, f.get("jars_usados"))

    def test_artifactid_terminado_em_numero_nao_vira_dep_ausente(self):
        binpath = fx.dep_com_sufixo_numerico(self.base)
        rc, out = rodar(["scan", ".", "--tier", "2", "--no-compile"],
                        self.base,
                        {"PATH": "%s:%s" % (binpath, os.environ["PATH"])})
        self.assertEqual(rc, 0, out)
        _cab, arestas = ler_tsv(
            self.base / ".scos-map/facts/_raiz/bytecode_edges.tsv")
        self.assertIn("hypersistence-utils-hibernate-71-3.15.5.jar",
                      {a["origem"] for a in arestas})
        f = self.fato("_raiz", "bytecode")
        self.assertEqual(f.get("deps_usadas_ausentes_do_pom", []), [])
        self.assertNotIn("hypersistence-utils-hibernate-71",
                         [x["artefato"]
                          for x in f.get("deps_declaradas_sem_uso", [])])

    def _scan_tier2(self, binpath, m2):
        rc, out = rodar(["scan", ".", "--tier", "2", "--no-compile"],
                        self.base,
                        {"PATH": "%s:%s" % (binpath, os.environ["PATH"]),
                         "SCOS_MAP_M2": str(m2)})
        self.assertEqual(rc, 0, out)
        return self.fato("_raiz", "bytecode")

    def test_classe_citada_so_em_anotacao_conta_como_uso(self):
        m2 = self.tmp / "m2"
        f = self._scan_tier2(fx.dep_so_em_anotacao(self.base, m2), m2)
        self.assertEqual(f.get("usadas_fora_do_jdeps"),
                         {"hypersistence-utils-hibernate-71": 1})
        self.assertNotIn("hypersistence-utils-hibernate-71",
                         [x["artefato"]
                          for x in f.get("deps_declaradas_sem_uso", [])])
        self.assertIn("lombok",
                      [x["artefato"]
                       for x in f.get("deps_ignoradas_na_analise", [])])

    def test_sem_o_jar_no_m2_nao_afirma_uso(self):
        m2 = self.tmp / "m2"
        f = self._scan_tier2(
            fx.dep_so_em_anotacao(self.base, m2, com_jar=False), m2)
        self.assertNotIn("usadas_fora_do_jdeps", f)
        self.assertIn("hypersistence-utils-hibernate-71",
                      [x["artefato"]
                       for x in f.get("deps_declaradas_sem_uso", [])])


class TestJarParaArtefato(unittest.TestCase):
    def test_artefato_conhecido_terminado_em_numero(self):
        self.assertEqual(sm.jar_para_artefato(
            "hypersistence-utils-hibernate-71-3.15.5.jar",
            {"hypersistence-utils-hibernate-71", "hypersistence-tsid"}),
            "hypersistence-utils-hibernate-71")

    def test_sem_artefato_conhecido_cai_na_regex(self):
        self.assertEqual(sm.jar_para_artefato("spring-data-redis-4.1.1.jar"),
                         "spring-data-redis")


# ---------------------------------------------------------------------------
# Incremental
# ---------------------------------------------------------------------------

@unittest.skipUnless(TEM_GIT, "git indisponivel")
class TestIncremental(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.maven_multimodulo(self.base)
        self.scan()

    def test_segundo_scan_reaproveita_fatos_intactos(self):
        out = self.scan()
        self.assertIn("reaproveitados do disco", out)

    def test_full_ignora_o_cache(self):
        out = self.scan("--full")
        self.assertNotIn("reaproveitados do disco", out)

    def test_alteracao_regenera_apenas_o_modulo_afetado(self):
        alvo = self.base / "alpha/src/main/java/a/A.java"
        alvo.write_text(alvo.read_text() + "// muda\n")
        out = self.scan()
        self.assertIn("alpha/layout", out)
        self.assertNotIn("beta/layout", out)

    def test_reuso_nao_altera_o_conteudo_do_fato(self):
        antes = self.fato("alpha", "layout")
        self.scan()
        self.assertEqual(antes, self.fato("alpha", "layout"))

    def test_deps_nunca_e_reaproveitado(self):
        """O envelope em disco ja teve as listas movidas para o TSV."""
        self.scan()
        f = self.fato("alpha", "deps")
        self.assertEqual(f["corpo"], "deps.tsv")
        self.assertGreater(f["diretas_total"], 0,
                           "reuso teria zerado as contagens")


# ---------------------------------------------------------------------------
# Docs: subtipos
# ---------------------------------------------------------------------------

class TestDocsSubtipos(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.docs_subtipos(self.base)
        self.scan()
        self.f = self.fato("_raiz", "docs")
        self.por_path = {i["path"]: i for i in self.f["itens"]}

    def test_subtipo_por_caminho(self):
        self.assertEqual(self.por_path["docs/adr/003-pgmq-vs-kafka.md"]
                         ["subtipo"], "adr")
        self.assertEqual(self.por_path["docs/runbooks/rollback.md"]
                         ["subtipo"], "runbook")

    def test_subtipo_por_titulo_quando_o_caminho_nao_diz(self):
        item = self.por_path["docs/sem-convencao/decisao-antiga.md"]
        self.assertEqual(item["subtipo"], "adr")
        self.assertEqual(item["subtipo_por"], "titulo")

    def test_documento_fora_de_convencao_cai_em_outro(self):
        self.assertEqual(self.por_path["docs/nota-solta.md"]["subtipo"],
                         "outro")

    def test_bmad_marcado_e_contado(self):
        self.assertEqual(self.f["gerados_por_bmad"], 2)
        self.assertEqual(
            self.por_path["_bmad-output/prd/prd-organization.md"]
            ["gerado_por"], "bmad")

    def test_frontmatter_lido_sem_inventar(self):
        prd = self.por_path["_bmad-output/prd/prd-organization.md"]
        self.assertEqual(prd["status"], "aprovado")
        self.assertEqual(prd["owner"], "saw")
        story = self.por_path["_bmad-output/stories/us-014-cadastro.md"]
        self.assertEqual(story["epic"], "organization-cadastro")
        # sem frontmatter, nenhum status e atribuido
        self.assertNotIn("status", self.por_path["docs/nota-solta.md"])

    def test_limitacoes_declaradas(self):
        lims = self.f["completude"]["limitacoes"]
        self.assertTrue(any("subtipo" in l for l in lims))
        self.assertTrue(any("status" in l for l in lims))


# ---------------------------------------------------------------------------
# TSV: robustez
# ---------------------------------------------------------------------------

class TestTsvRobusto(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.tsv_campo_com_tab(self.base)
        self.scan()

    def test_nenhuma_linha_ganha_coluna_extra(self):
        for tsv in (self.base / ".scos-map").rglob("*.tsv"):
            cab, _ = ler_tsv(tsv)
            for i, linha in enumerate(
                    tsv.read_text(encoding="utf-8").splitlines()):
                if not linha:
                    continue
                self.assertEqual(len(linha.split("\t")), len(cab),
                                 "%s linha %d" % (tsv.name, i))

    def test_tsv_clean_neutraliza_separadores(self):
        self.assertEqual(sm.tsv_clean("a\tb\nc\rd"), "a b c d")


# ---------------------------------------------------------------------------
# npm
# ---------------------------------------------------------------------------

class TestNpmWorkspaces(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.npm_workspaces(self.base)
        self.scan()

    def test_modulo_do_workspace_e_descoberto(self):
        self.assertIn("apps/portal", self.indice()["modulos"])

    def test_delta_declarada_versus_lockfile(self):
        _cab, linhas = ler_tsv(
            self.base / ".scos-map/facts/apps/portal/deps.tsv")
        react = [l for l in linhas if l["ga"] == "react"][0]
        # declarado ^19.1.0, lockfile 19.1.4: o resolvido ganha e a
        # divergencia fica marcada
        self.assertEqual(react["versao"], "19.1.4")
        self.assertEqual(react["divergente"], "1")

    def test_caminho_do_fato_espelha_o_caminho_do_modulo(self):
        self.assertTrue(
            (self.base / ".scos-map/facts/apps/portal/deps.json").exists())


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

@unittest.skipUnless(TEM_GIT, "git indisponivel")
class TestWorkspace(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.workspace_3_projetos(self.base)
        rc, out = rodar(["workspace", "."], self.base)
        self.assertEqual(rc, 0, out)

    def ws(self):
        return ler_json(self.base / ".scos-map/workspace.json")

    def test_cada_projeto_tem_mapa_proprio(self):
        for p in ("proj-a", "proj-b", "proj-c"):
            self.assertTrue(
                (self.base / p / ".scos-map/index.json").exists(), p)

    def test_conflito_cruzado_detectado(self):
        itens = self.ws()["conflitos_de_versao_cruzados"]["itens"]
        gas = {c["ga"] for c in itens}
        self.assertIn("com.fasterxml.jackson.core:jackson-databind", gas)

    def test_fato_cruzado_declara_derivado_de(self):
        c = self.ws()["conflitos_de_versao_cruzados"]
        self.assertTrue(c["derivado_de"])
        for _proj, ref in c["derivado_de"].items():
            self.assertIn("head", ref)
            self.assertIn("deps_sha", ref)

    def test_projeto_que_avanca_deixa_o_cruzado_obsoleto(self):
        alvo = self.base / "proj-a/src/main/java/a/A.java"
        alvo.write_text(alvo.read_text() + "// muda\n")
        subprocess.run(["git", "add", "-A"], cwd=str(self.base / "proj-a"),
                       capture_output=True)
        subprocess.run(["git", "commit", "-qm", "avanca"],
                       cwd=str(self.base / "proj-a"), capture_output=True)
        rc, out = rodar(["status", "."], self.base)
        self.assertIn("obsoleto", out)
        self.assertIn("proj-a moveu", out)

    def test_only_preserva_os_demais_projetos_no_indice(self):
        rc, out = rodar(["workspace", ".", "--only", "proj-b"], self.base)
        self.assertEqual(rc, 0, out)
        projetos = {p["projeto"] for p in self.ws()["projetos"]}
        self.assertEqual(projetos, {"proj-a", "proj-b", "proj-c"})
        self.assertIn("cache", out)


@unittest.skipUnless(TEM_GIT, "git indisponivel")
class TestWorkspaceProfundo(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.workspace_profundo(self.base)

    def test_default_encontra_projetos_em_tres_niveis(self):
        rc, out = rodar(["workspace", "."], self.base)
        self.assertEqual(rc, 0, out)
        self.assertIn("2 projeto(s)", out)

    def test_poda_e_reportada_mesmo_sem_achar_projeto(self):
        rc, out = rodar(["workspace", ".", "--max-depth", "2"], self.base)
        self.assertIn("nao visitados", out)
        self.assertIn("--max-depth", out)


@unittest.skipUnless(TEM_GIT, "git indisponivel")
class TestSnapshotLocal(BaseFixture):
    def setUp(self):
        super().setUp()
        self.m2 = self.tmp / "m2"
        _b, self.jar = fx.snapshot_local(self.base, self.m2)
        rc, out = rodar(["workspace", "."], self.base,
                        {"SCOS_MAP_M2": str(self.m2)})
        self.assertEqual(rc, 0, out)
        self.saida = out

    def snaps(self):
        return ler_json(
            self.base / ".scos-map/workspace.json")["snapshots_locais"]

    def test_jar_antigo_e_marcado_desatualizado(self):
        itens = self.snaps()["itens"]
        self.assertEqual(len(itens), 1, itens)
        self.assertEqual(itens[0]["estado"], "jar_desatualizado")
        self.assertEqual(itens[0]["produzido_por"], "Foundation")

    def test_acao_sugerida_nomeia_o_produtor(self):
        self.assertIn("mvn clean install em Foundation",
                      self.snaps()["itens"][0]["acao"])

    def test_aparece_nos_achados(self):
        self.assertIn("SNAPSHOT do", self.saida)

    def test_confianca_media_e_limitacao_de_mtime(self):
        s = self.snaps()
        self.assertEqual(s["confianca"], "media")
        self.assertTrue(any("mtime" in l
                            for l in s["completude"]["limitacoes"]))

    def test_jar_reinstalado_vira_atual(self):
        agora = os.path.getmtime(self.base / "Foundation/pom.xml") + 3600
        os.utime(self.jar, (agora, agora))
        shutil.rmtree(self.base / ".scos-map")
        rodar(["workspace", "."], self.base, {"SCOS_MAP_M2": str(self.m2)})
        self.assertEqual(self.snaps()["itens"][0]["estado"], "jar_atual")

    def test_jar_ausente_e_reportado(self):
        os.remove(self.jar)
        shutil.rmtree(self.base / ".scos-map")
        rodar(["workspace", "."], self.base, {"SCOS_MAP_M2": str(self.m2)})
        self.assertEqual(self.snaps()["itens"][0]["estado"], "jar_ausente")


@unittest.skipUnless(TEM_GIT, "git indisponivel")
class TestWorkspaceModulosAninhados(BaseFixture):
    """Modulo aninhado mora em facts/<a>/<b>/: nao pode sumir do workspace."""

    BOOT = "Flow/organization/flow-organization-boot"

    def setUp(self):
        super().setUp()
        self.env = {"SCOS_MAP_M2": str(self.tmp / "m2")}
        fx.workspace_modulos_aninhados(self.base, self.tmp / "m2")
        rc, out = rodar(["workspace", "."], self.base, self.env)
        self.assertEqual(rc, 0, out)

    def ws(self):
        return ler_json(self.base / ".scos-map/workspace.json")

    def test_conflito_cruzado_enxerga_modulo_aninhado(self):
        itens = {c["ga"]: c["versoes"] for c in
                 self.ws()["conflitos_de_versao_cruzados"]["itens"]}
        self.assertIn(self.BOOT, itens.get("org.jetbrains:annotations", {})
                      .get("13.0", []), itens)

    def test_snapshot_consumido_por_modulo_aninhado(self):
        itens = self.ws()["snapshots_locais"]["itens"]
        self.assertEqual([(i["ga"], i["consumido_por"]) for i in itens],
                         [("br.com.sawcunhaos:scos-foundation-core",
                           ["Flow"])])

    def test_deps_de_modulo_aninhado_entram_no_frescor_do_cruzado(self):
        arvore = self.base / self.BOOT / "target/.scos-map-tree.txt"
        arvore.write_text(arvore.read_text().replace(":13.0:", ":13.1:"))
        rc, out = rodar(["scan", "."], self.base / "Flow", self.env)
        self.assertEqual(rc, 0, out)
        rc, out = rodar(["status", "."], self.base)
        self.assertIn("estado: obsoleto", out)


class TestModuloSemCodigo(BaseFixture):
    def test_so_resources_e_nao_aplicavel_e_so_proto_nao(self):
        fx.modulos_sem_codigo(self.base)
        self.scan("--tier", "2", "--no-compile")
        self.assertEqual(self.fato("recursos", "bytecode")["estado"],
                         "nao_aplicavel")
        self.assertNotEqual(self.fato("contrato", "bytecode")["estado"],
                            "nao_aplicavel")


class TestTierEfetivo(BaseFixture):
    def test_tier_pedido_sem_dado_nao_vira_tier_executado(self):
        fx.maven_simples(self.base)
        self.scan("--tier", "3", "--no-compile")
        idx = self.indice()
        self.assertEqual(idx["tier_pedido"], 3)
        self.assertEqual(idx["tier_executado"], 1)


@unittest.skipUnless(TEM_GIT, "git indisponivel")
class TestWorkspaceScopeEBom(BaseFixture):
    def setUp(self):
        super().setUp()
        fx.workspace_scope_e_bom(self.base)
        rc, out = rodar(["workspace", "."], self.base)
        self.assertEqual(rc, 0, out)
        self.itens = {c["ga"]: c["versoes"] for c in ler_json(
            self.base / ".scos-map/workspace.json"
        )["conflitos_de_versao_cruzados"]["itens"]}

    def test_divergencia_so_em_teste_fica_fora_do_cruzado(self):
        self.assertNotIn("org.y:so-teste", self.itens)

    def test_versao_da_bom_entra_no_cruzado_como_gerenciada(self):
        self.assertEqual(self.itens.get("org.x:lib"),
                         {"1.0": ["a/_raiz", "b/_raiz"],
                          "2.0": ["bom/_raiz (gerenciada)"]})

    def test_bom_registra_o_dependency_management(self):
        _cab, linhas = ler_tsv(
            self.base / "bom/.scos-map/facts/_raiz/gerenciadas.tsv")
        self.assertEqual([(l["ga"], l["versao"], l["origem"]) for l in linhas],
                         [("org.x:lib", "2.0", "propriedade:lib.version"),
                          ("org.z:interno", "1.0",
                           "propriedade:project.version")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
