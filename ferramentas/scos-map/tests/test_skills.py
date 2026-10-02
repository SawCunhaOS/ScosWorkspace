"""Skills finas (Epic 4): tamanho, tabela unica de roteamento e destino das regras."""

import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SKILLS = RAIZ.parents[1] / ".claude" / "skills"
sys.path.insert(0, str(RAIZ))

from scos_map_query import ajuda, render  # noqa: E402
from scos_map_query.cli import _registro  # noqa: E402
from scos_map_query.comandos import arquivos, docs  # noqa: E402
from test_scos_map_query import TEM_GIT, BaseMapa, consultar  # noqa: E402


def _skill(nome):
    t = (SKILLS / nome / "SKILL.md").read_text(encoding="utf-8")
    _, fm, corpo = t.split("---\n", 2)
    desc = re.search(r"^description: (.*)$", fm, re.M).group(1)
    return desc, corpo.strip("\n")


class TestTamanho(unittest.TestCase):
    def test_skills_de_leitura_sao_curtas(self):
        for nome in ("scos-query", "scos-map"):
            desc, corpo = _skill(nome)
            self.assertLessEqual(len(desc), 300, nome)
            self.assertLessEqual(len(corpo.splitlines()), 30, nome)
            self.assertLessEqual(len(corpo), 2000, nome)

    def test_scos_map_aponta_para_query_e_status(self):
        desc, corpo = _skill("scos-map")
        self.assertIn("scos-query", desc + corpo)
        self.assertIn("scos-map.py status", corpo)


class TestRoteamento(unittest.TestCase):
    def test_tabela_tem_nome_e_pergunta_do_registro(self):
        _, corpo = _skill("scos-query")
        linhas = [l for l in corpo.splitlines()
                  if l.startswith("| `")]
        esperado = ["| `%s` | %s |" % (n, m.PERGUNTA) for n, m in _registro().items()]
        self.assertEqual(len(linhas), 13)
        self.assertEqual(linhas, esperado)

    def test_conteudo_obrigatorio(self):
        _, corpo = _skill("scos-query")
        for t in ("python3 ferramentas/scos-map/scos-map-query.py <subcomando>",
                  "--all", "142KB", "grep", "awk", "index.json", "_reactor.json",
                  "layout.json"):
            self.assertIn(t, corpo)

    def test_agents_md_e_build_apontam_para_query(self):
        agents = (RAIZ.parents[1] / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("scos-query", agents)
        self.assertNotIn("| Pergunta é sobre | Abra |", agents)
        desc, _ = _skill("scos-map-build")
        self.assertIn("scos-query", desc)
        self.assertNotIn("skill `scos-map`", desc)


# secoes do SKILL.md antigo (218 linhas), congeladas -> destino.
SECOES_ANTIGAS = {
    "Introducao (indice, nao substituto)", "Passo 0", "Contrato", "Envelope de fato",
    "Roteamento", "Tabelas (TSV)", "deps.tsv incompleto", "Como interpretar a confianca",
    "Regras que evitam conclusao errada", "Dependencias no bytecode.json", "Testes",
    "Documentacao", "O fato cruzado do workspace", "SNAPSHOT local vs fonte",
    "Perguntas abertas", "Gerar o mapa"}
INVENTARIO = {
    "Passo 0": "scos-query", "Contrato": "CLI", "Envelope de fato": "--help",
    "Roteamento": "scos-query", "Tabelas (TSV)": "CLI",
    "deps.tsv incompleto": "scos-query", "Como interpretar a confianca": "--help",
    "Regras que evitam conclusao errada": "CLI",
    "Dependencias no bytecode.json": "CLI", "Testes": "CLI",
    "Documentacao": "CLI", "O fato cruzado do workspace": "CLI",
    "SNAPSHOT local vs fonte": "CLI", "Perguntas abertas": "scos-query",
    "Introducao (indice, nao substituto)": "scos-map",
    "Gerar o mapa": "scos-map-build",
}
DESTINOS = {"CLI", "--help", "scos-query", "scos-map", "scos-map-build"}


class TestDestino(unittest.TestCase):
    def test_inventario_cobre_todas_as_secoes_antigas(self):
        self.assertEqual(set(INVENTARIO), SECOES_ANTIGAS)
        for secao, d in INVENTARIO.items():
            self.assertIn(d, DESTINOS, secao)

    def test_regras_de_skill_no_corpo(self):
        _, corpo = _skill("scos-query")
        for t in ('"nao usa X"', '"esta testada"', "_transitivas_comuns.tsv", "2.1"):
            self.assertIn(t, corpo)


@unittest.skipUnless(TEM_GIT, "git indisponivel")
class TestRegrasNaSaida(BaseMapa):
    """Regras de alto risco: estar so no --help nao basta; tem que sair no stdout."""

    def test_docs_aviso(self):
        _, out, _ = consultar(self.mapa(), "docs", "proj", "app")
        self.assertIn("# aviso: " + docs.AVISO, out)
        self.assertIn("defasado", out)
        self.assertLessEqual(len(docs.AVISO), 100)

    def test_arquivos_aviso(self):
        _, out, _ = consultar(self.mapa(), "arquivos", "proj")
        self.assertIn("# aviso: " + arquivos.AVISO, out)

    def test_obsoleto_no_cabecalho(self):
        _, out, _ = consultar(self.mapa(head="0" * 12), "layout", "proj", "app")
        self.assertIn("estado=obsoleto", out)

    def test_estado_nao_aplicavel_existe_no_vocabulario_e_na_legenda(self):
        self.assertIn("nao_aplicavel", render._ESTADO)
        self.assertIn("nao_aplicavel", ajuda.CONFIANCA)
    # codigo morto (callgraph), arestas vazias e bytecode: ver TestCallgraph/TestArestas/TestBytecode


if __name__ == "__main__":
    unittest.main()
