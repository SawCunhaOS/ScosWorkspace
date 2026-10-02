"""Arvores sinteticas para a suite do scos-map.

Cada fixture reproduz um caso que ja quebrou o script ou que ele precisa
sustentar. Nenhuma depende de rede, de Maven ou de um repositorio real.
"""

import json
import os
import subprocess
import zipfile
from pathlib import Path

POM_NS = 'xmlns="http://maven.apache.org/POM/4.0.0"'


def escrever(base: Path, arquivos: dict):
    for rel, conteudo in arquivos.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(conteudo, encoding="utf-8")
    return base


def git_init(base: Path, commit=True):
    def g(*args):
        subprocess.run(["git", *args], cwd=str(base), capture_output=True)
    g("init", "-q")
    g("config", "user.email", "suite@scos.test")
    g("config", "user.name", "suite")
    g("config", "commit.gpgsign", "false")
    if commit:
        g("add", "-A")
        g("commit", "-qm", "fixture")
    return base


def pom(artifact, group="br.com.sawcunhaos", version="1.0",
        parent=None, packaging=None, modules=(), deps=(), props=None,
        dep_mgmt=(), profiles=""):
    partes = ['<project %s><modelVersion>4.0.0</modelVersion>' % POM_NS]
    if parent:
        partes.append(
            "<parent><groupId>%s</groupId><artifactId>%s</artifactId>"
            "<version>%s</version></parent>" % (group, parent, version))
    else:
        partes.append("<groupId>%s</groupId>" % group)
    partes.append("<artifactId>%s</artifactId>" % artifact)
    if not parent:
        partes.append("<version>%s</version>" % version)
    if packaging:
        partes.append("<packaging>%s</packaging>" % packaging)
    if props:
        partes.append("<properties>%s</properties>" % "".join(
            "<%s>%s</%s>" % (k, v, k) for k, v in props.items()))
    if profiles:
        partes.append(profiles)
    if modules:
        partes.append("<modules>%s</modules>" % "".join(
            "<module>%s</module>" % m for m in modules))
    if dep_mgmt:
        partes.append("<dependencyManagement><dependencies>%s</dependencies>"
                      "</dependencyManagement>" % "".join(dep_mgmt))
    if deps:
        partes.append("<dependencies>%s</dependencies>" % "".join(deps))
    partes.append("</project>")
    return "".join(partes)


def dep(group, artifact, version=None, scope=None, tipo=None, imp=False):
    s = "<dependency><groupId>%s</groupId><artifactId>%s</artifactId>" % (
        group, artifact)
    if version:
        s += "<version>%s</version>" % version
    if tipo:
        s += "<type>%s</type>" % tipo
    if imp:
        s += "<scope>import</scope>"
    elif scope:
        s += "<scope>%s</scope>" % scope
    return s + "</dependency>"


def arvore_tree(self_ga, linhas):
    """Conteudo de um dependency:tree em formato texto."""
    return "\n".join([self_ga] + list(linhas)) + "\n"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def maven_simples(base: Path):
    escrever(base, {
        "pom.xml": pom("svc", deps=[
            dep("org.apache.commons", "commons-lang3", "3.14.0"),
            dep("org.junit.jupiter", "junit-jupiter", "5.11.0", scope="test"),
        ]),
        "src/main/java/br/com/scos/OrgService.java":
            "package br.com.scos;\npublic class OrgService {}\n",
        "src/main/java/br/com/scos/controller/OrgController.java":
            "package br.com.scos.controller;\n"
            "@RestController\n@RequestMapping(\"/orgs\")\n"
            "public class OrgController {}\n",
    })
    return git_init(base)


def maven_multimodulo(base: Path):
    escrever(base, {
        "pom.xml": pom("flow", packaging="pom", modules=["alpha", "beta"]),
        "alpha/pom.xml": pom("alpha", parent="flow", deps=[
            dep("com.fasterxml.jackson.core", "jackson-databind", "2.17.0")]),
        "beta/pom.xml": pom("beta", parent="flow", deps=[
            dep("com.fasterxml.jackson.core", "jackson-databind", "2.15.2"),
            dep("br.com.sawcunhaos", "alpha", "1.0")]),
        "alpha/src/main/java/a/A.java": "package a;\npublic class A {}\n",
        "beta/src/main/java/b/B.java": "package b;\npublic class B {}\n",
    })
    return git_init(base)


def maven_bom_import(base: Path):
    """BOM importado + property sobrescrita por profile.

    parse_pom nao sabe a versao do jjwt (vem do BOM) e deduz a property
    errada para o slf4j; o effective-pom responde as duas.
    """
    perfil = ("<profiles><profile><id>ci</id>"
              "<activation><activeByDefault>true</activeByDefault></activation>"
              "<properties><slf4j.version>2.0.18</slf4j.version></properties>"
              "</profile></profiles>")
    escrever(base, {
        "pom.xml": pom("raiz", packaging="pom", modules=["consumidor"],
                       props={"slf4j.version": "2.0.9"}, profiles=perfil),
        "consumidor/pom.xml": pom(
            "consumidor", parent="raiz",
            dep_mgmt=[dep("br.com.sawcunhaos", "sawcunha-open-system-bom",
                          "1.2.0", tipo="pom", imp=True)],
            deps=[dep("io.jsonwebtoken", "jjwt-api"),
                  dep("org.slf4j", "slf4j-api", "${slf4j.version}")]),
        "consumidor/src/main/java/c/C.java": "package c;\npublic class C {}\n",
        "consumidor/target/.scos-map-effective.xml":
            '<?xml version="1.0"?>\n<project %s>'
            "<groupId>br.com.sawcunhaos</groupId>"
            "<artifactId>consumidor</artifactId><version>1.0</version>"
            "<dependencies>"
            "<dependency><groupId>io.jsonwebtoken</groupId>"
            "<artifactId>jjwt-api</artifactId><version>0.12.6</version>"
            "<scope>compile</scope></dependency>"
            "<dependency><groupId>org.slf4j</groupId>"
            "<artifactId>slf4j-api</artifactId><version>2.0.18</version>"
            "<scope>compile</scope></dependency>"
            "</dependencies></project>\n" % POM_NS,
    })
    git_init(base)
    _tocar_depois(base / "consumidor/target/.scos-map-effective.xml",
                  base / "consumidor/pom.xml")
    return base


def maven_parent_property(base: Path):
    escrever(base, {
        "pom.xml": pom("raiz", packaging="pom", modules=["filho"],
                       props={"jackson.version": "2.17.0"}),
        "filho/pom.xml": pom("filho", parent="raiz", deps=[
            dep("com.fasterxml.jackson.core", "jackson-databind",
                "${jackson.version}")]),
        "filho/src/main/java/f/F.java": "package f;\npublic class F {}\n",
    })
    return git_init(base)


YAML_COMPLEXO = """defaults: &base
  timeout: 30
  retries: 3

spring:
  application:
    name: scos
  cloud:
    gateway:
      routes:
        - id: rota-a
          uri: http://a
        - id: rota-b
          uri: http://b
cliente:
  <<: *base
  endpoint: ${EP}
descricao: >
  bloco de texto
  que continua
---
spring:
  config:
    activate:
      on-profile: prod
logging:
  level:
    root: WARN
"""


def yaml_complexo(base: Path):
    escrever(base, {
        "pom.xml": pom("ycx"),
        "src/main/resources/application.yml": YAML_COMPLEXO,
        "src/main/java/y/Y.java": "package y;\npublic class Y {}\n",
    })
    return git_init(base)


def properties_simples(base: Path):
    escrever(base, {
        "pom.xml": pom("props"),
        "src/main/resources/application.properties":
            "# comentario\n"
            "spring.datasource.url=${DB_URL}\n"
            "spring.datasource.username=${DB_USER}\n"
            "server.port=8080\n"
            "scos.audit.enabled=true\n",
        "src/main/java/p/P.java": "package p;\npublic class P {}\n",
    })
    return git_init(base)


def npm_workspaces(base: Path):
    escrever(base, {
        "package.json": '{"name":"raiz","workspaces":["apps/*"]}',
        "apps/portal/package.json":
            '{"name":"portal","dependencies":{"react":"^19.1.0",'
            '"axios":"^1.7.2"}}',
        "apps/portal/package-lock.json":
            '{"name":"portal","lockfileVersion":3,"packages":{'
            '"node_modules/react":{"version":"19.1.4"},'
            '"node_modules/axios":{"version":"1.7.9"}}}',
        "apps/portal/src/main.tsx": "export default 1;\n",
    })
    return git_init(base)


def tsv_campo_com_tab(base: Path):
    """Nome de arquivo e conteudo com tab e quebra de linha."""
    escrever(base, {
        "pom.xml": pom("tabs"),
        "src/main/resources/application.yml":
            "chave:\n  com\tespaco: 1\n",
        "src/main/java/t/T.java": "package t;\npublic class T {}\n",
        "docs/nota\tcom tab.md": "# titulo\tcom tab\n\n## secao\n",
    })
    return git_init(base)


def testes_multiplas_raizes(base: Path):
    escrever(base, {
        "pom.xml": pom("svc", deps=[
            dep("org.junit.jupiter", "junit-jupiter", "5.11.0", scope="test"),
            dep("com.tngtech.archunit", "archunit-junit5", "1.3.0",
                scope="test"),
            dep("org.testcontainers", "testcontainers", "1.20.1",
                scope="test")]),
        "src/main/java/s/OrgService.java":
            "package s;\npublic class OrgService {}\n",
        "src/test/java/s/OrgServiceTest.java":
            "package s;\nimport org.junit.jupiter.api.Test;\n"
            "public class OrgServiceTest { @Test void ok(){} }\n",
        "src/integrationTest/java/s/OrgFlowIT.java":
            "package s;\nimport org.testcontainers.containers.GenericContainer;\n"
            "public class OrgFlowIT {}\n",
        "archtest/src/test/java/s/arch/LayerTest.java":
            "package s.arch;\nimport com.tngtech.archunit.lang.ArchRule;\n"
            "public class LayerTest {\n"
            "  static final ArchRule dominioNaoDependeDeInfra = null;\n"
            "  static final ArchRule controllerSoChamaUsecase = null;\n}\n",
        "vazio/pom.xml": pom("vazio"),
        "vazio/src/test/java/.gitkeep": "",
    })
    return git_init(base)


def workspace_3_projetos(base: Path):
    a = base / "proj-a"
    b = base / "proj-b"
    c = base / "proj-c"
    escrever(a, {"pom.xml": pom("proj-a", deps=[
        dep("com.fasterxml.jackson.core", "jackson-databind", "2.17.0")]),
        "src/main/java/a/A.java": "package a;\npublic class A {}\n"})
    escrever(b, {"pom.xml": pom("proj-b", deps=[
        dep("com.fasterxml.jackson.core", "jackson-databind", "2.13.0")]),
        "src/main/java/b/B.java": "package b;\npublic class B {}\n"})
    escrever(c, {"package.json":
                 '{"name":"proj-c","dependencies":{"react":"^19.0.0"}}',
                 "src/main.ts": "export default 1;\n"})
    for d in (a, b, c):
        git_init(d)
    return base


def workspace_profundo(base: Path):
    p = base / "java/backend/servico-a"
    escrever(p, {"pom.xml": pom("servico-a"),
                 "src/main/java/x/X.java": "package x;\npublic class X {}\n"})
    git_init(p)
    q = base / "front/apps/portal"
    escrever(q, {"package.json": '{"name":"portal","dependencies":{}}',
                 "src/main.ts": "export default 1;\n"})
    git_init(q)
    return base


def snapshot_local(base: Path, m2: Path):
    """Produtor no workspace, consumidor resolvendo o jar do ~/.m2."""
    prod = base / "Foundation"
    cons = base / "Flow"
    escrever(prod, {
        "pom.xml": pom("scos-foundation", version="1.2.0-SNAPSHOT",
                       packaging="pom", modules=["core"]),
        "core/pom.xml": pom("scos-foundation-core", parent="scos-foundation",
                            version="1.2.0-SNAPSHOT"),
        "core/src/main/java/f/F.java": "package f;\npublic class F {}\n"})
    escrever(cons, {
        "pom.xml": pom("flow", version="1.0.0-SNAPSHOT", packaging="pom",
                       modules=["organization"]),
        "organization/pom.xml": pom(
            "flow-organization", parent="flow", version="1.0.0-SNAPSHOT",
            deps=[dep("br.com.sawcunhaos", "scos-foundation-core",
                      "1.2.0-SNAPSHOT")]),
        "organization/src/main/java/o/O.java": "package o;\npublic class O {}\n",
        "organization/target/.scos-map-tree.txt": arvore_tree(
            "br.com.sawcunhaos:flow-organization:jar:1.0.0-SNAPSHOT",
            ["\\- br.com.sawcunhaos:scos-foundation-core:jar:"
             "1.2.0-SNAPSHOT:compile"])})
    jar_dir = (m2 / "br/com/sawcunhaos/scos-foundation-core/1.2.0-SNAPSHOT")
    jar_dir.mkdir(parents=True, exist_ok=True)
    jar = jar_dir / "scos-foundation-core-1.2.0-SNAPSHOT.jar"
    jar.write_text("jar antigo", encoding="utf-8")
    for d in (prod, cons):
        git_init(d)
    # jar instalado ANTES do ultimo commit do produtor
    antigo = os.path.getmtime(prod / "pom.xml") - 5 * 86400
    os.utime(jar, (antigo, antigo))
    _tocar_depois(cons / "organization/target/.scos-map-tree.txt",
                  cons / "organization/pom.xml")
    return base, jar


def fecho_transitivo(base: Path, n_modulos=4, n_comuns=12):
    """Reator onde o fecho transitivo e quase identico entre modulos."""
    mods = ["m%d" % i for i in range(n_modulos)]
    arquivos = {"pom.xml": pom("flow", packaging="pom", modules=mods)}
    comuns = [("org.springframework:spring-lib%02d" % i, "7.0.%d" % i)
              for i in range(n_comuns)]
    for idx, m in enumerate(mods):
        arquivos["%s/pom.xml" % m] = pom(m, parent="flow", deps=[
            dep("org.springframework.boot", "spring-boot-starter", "4.1.1")])
        arquivos["%s/src/main/java/%s/C.java" % (m, m)] = (
            "package %s;\npublic class C {}\n" % m)
        linhas = ["+- org.springframework.boot:spring-boot-starter:jar:"
                  "4.1.1:compile"]
        for ga, v in comuns:
            g, a = ga.split(":")
            # o ultimo modulo diverge numa lib: ela sai do fecho comum
            if idx == len(mods) - 1 and a == "spring-lib00":
                v = "6.0.0"
            linhas.append("|  +- %s:%s:jar:%s:compile" % (g, a, v))
        arquivos["%s/target/.scos-map-tree.txt" % m] = arvore_tree(
            "br.com.sawcunhaos:%s:jar:1.0" % m, linhas)
    escrever(base, arquivos)
    git_init(base)
    for m in mods:
        _tocar_depois(base / m / "target/.scos-map-tree.txt",
                      base / m / "pom.xml")
    return base, comuns


def _tocar_depois(alvo: Path, referencia: Path):
    """Garante que `alvo` seja mais novo que `referencia` (cache valido)."""
    ts = os.path.getmtime(referencia) + 10
    os.utime(alvo, (ts, ts))


def docs_subtipos(base: Path):
    """Docs organizados por convencao + saida do BMAD com frontmatter."""
    escrever(base, {
        "pom.xml": pom("doc"),
        "src/main/java/d/D.java": "package d;\npublic class D {}\n",
        "README.md": "# SCOS Doc\n## Build\n",
        "docs/adr/003-pgmq-vs-kafka.md":
            "# ADR 003 - PGMQ vs Kafka\n## Contexto\n## Decisao\n",
        "docs/runbooks/rollback.md":
            "# Runbook - Rollback\n## Procedimento\n",
        "docs/nota-solta.md": "# Anotacoes diversas\n",
        "_bmad-output/prd/prd-organization.md":
            "---\nstatus: aprovado\nowner: saw\n---\n"
            "# PRD - Organization\n## Requisitos\n",
        "_bmad-output/stories/us-014-cadastro.md":
            "---\nstatus: em andamento\nepic: organization-cadastro\n---\n"
            "# User Story - Cadastro\n## Criterios de aceite\n",
        "docs/sem-convencao/decisao-antiga.md":
            "# ADR - decisao fora do diretorio padrao\n## Decisao\n",
    })
    return git_init(base)


def jdeps_falso(base: Path, saida=""):
    """Cria um `jdeps` no PATH que devolve a saida dada.

    Permite exercitar o caminho de diagnostico (saida sem aresta, erro de
    multi-release) sem depender do JDK real.
    """
    binpath = base / "fakebin"
    binpath.mkdir(parents=True, exist_ok=True)
    script = binpath / "jdeps"
    script.write_text("#!/bin/sh\ncat <<'FIM'\n%s\nFIM\n" % saida)
    script.chmod(0o755)
    return binpath


def bytecode_sem_aresta(base: Path):
    """Modulo compilado cujo jdeps (falso) nao emite aresta nenhuma."""
    escrever(base, {
        "pom.xml": pom("vazio"),
        "src/main/java/v/V.java": "package v;\npublic class V {}\n",
        "target/classes/v/V.class": "fake",
    })
    git_init(base)
    return jdeps_falso(base, "classes -> java.base")


def dep_usada_ausente_do_pom(base: Path):
    """Bytecode usa uma lib que nao esta declarada NEM resolvida."""
    escrever(base, {
        "pom.xml": pom("svc", deps=[
            dep("org.slf4j", "slf4j-api", "2.0.18")]),
        "src/main/java/s/S.java": "package s;\npublic class S {}\n",
        "target/classes/s/S.class": "fake",
        "target/.scos-map-tree.txt": arvore_tree(
            "br.com.sawcunhaos:svc:jar:1.0",
            ["+- org.slf4j:slf4j-api:jar:2.0.18:compile"]),
    })
    git_init(base)
    _tocar_depois(base / "target/.scos-map-tree.txt", base / "pom.xml")
    # jdeps informa uso de uma lib que a arvore nao conhece
    return jdeps_falso(base, "classes -> /tmp/x/guava-33.0.jar\n"
                             "   s.S -> com.google.common.base.Strings"
                             "   guava-33.0.jar")


def dep_com_sufixo_numerico(base: Path):
    """artifactId terminado em numero: a regex do nome do jar o corta."""
    jar = "hypersistence-utils-hibernate-71-3.15.5.jar"
    escrever(base, {
        "pom.xml": pom("svc", deps=[
            dep("io.hypersistence", "hypersistence-utils-hibernate-71",
                "3.15.5")]),
        "src/main/java/s/S.java": "package s;\npublic class S {}\n",
        "target/classes/s/S.class": "fake",
        "target/.scos-map-tree.txt": arvore_tree(
            "br.com.sawcunhaos:svc:jar:1.0",
            ["+- io.hypersistence:hypersistence-utils-hibernate-71:jar:"
             "3.15.5:compile"]),
    })
    git_init(base)
    _tocar_depois(base / "target/.scos-map-tree.txt", base / "pom.xml")
    return jdeps_falso(base, "classes -> /tmp/x/%s\n"
                             "   s.S -> io.hypersistence.utils.hibernate.type."
                             "json.JsonType   %s" % (jar, jar))


def agregador_com_arvore_de_filho(base: Path):
    """Cache do agregador com a arvore de um filho (dependency:tree sem -N)."""
    escrever(base, {
        "pom.xml": pom("flow", packaging="pom", modules=["m0"]),
        "m0/pom.xml": pom("m0", parent="flow"),
        "m0/src/main/java/m0/C.java": "package m0;\npublic class C {}\n",
        "target/.scos-map-tree.txt": arvore_tree(
            "br.com.sawcunhaos:m0:jar:1.0",
            ["+- org.apache.httpcomponents:httpclient:jar:4.5.3:compile"]),
    })
    git_init(base)
    _tocar_depois(base / "target/.scos-map-tree.txt", base / "pom.xml")
    return base


def workspace_modulos_aninhados(base: Path, m2: Path):
    """Consumidor com modulo aninhado: seus fatos moram em facts/<a>/<b>/."""
    prod, cons = base / "Foundation", base / "Flow"
    boot = "organization/flow-organization-boot"
    escrever(prod, {
        "pom.xml": pom("scos-foundation", version="1.2.0-SNAPSHOT",
                       packaging="pom", modules=["core"]),
        "core/pom.xml": pom("scos-foundation-core", parent="scos-foundation",
                            version="1.2.0-SNAPSHOT"),
        "core/src/main/java/f/F.java": "package f;\npublic class F {}\n",
        "core/target/.scos-map-tree.txt": arvore_tree(
            "br.com.sawcunhaos:scos-foundation-core:jar:1.2.0-SNAPSHOT",
            ["\\- org.jetbrains:annotations:jar:17.0.0:compile"])})
    escrever(cons, {
        "pom.xml": pom("flow", version="1.0.0-SNAPSHOT", packaging="pom",
                       modules=["organization"]),
        "organization/pom.xml": pom(
            "organization", parent="flow", version="1.0.0-SNAPSHOT",
            packaging="pom", modules=["flow-organization-boot"]),
        boot + "/pom.xml": pom(
            "flow-organization-boot", parent="organization",
            version="1.0.0-SNAPSHOT",
            deps=[dep("br.com.sawcunhaos", "scos-foundation-core",
                      "1.2.0-SNAPSHOT")]),
        boot + "/src/main/java/o/O.java": "package o;\npublic class O {}\n",
        boot + "/target/.scos-map-tree.txt": arvore_tree(
            "br.com.sawcunhaos:flow-organization-boot:jar:1.0.0-SNAPSHOT",
            ["+- br.com.sawcunhaos:scos-foundation-core:jar:"
             "1.2.0-SNAPSHOT:compile",
             "\\- org.jetbrains:annotations:jar:13.0:runtime"])})
    jar_dir = m2 / "br/com/sawcunhaos/scos-foundation-core/1.2.0-SNAPSHOT"
    jar_dir.mkdir(parents=True, exist_ok=True)
    (jar_dir / "scos-foundation-core-1.2.0-SNAPSHOT.jar").write_text(
        "jar", encoding="utf-8")
    for d in (prod, cons):
        git_init(d)
    _tocar_depois(prod / "core/target/.scos-map-tree.txt",
                  prod / "core/pom.xml")
    _tocar_depois(cons / boot / "target/.scos-map-tree.txt",
                  cons / boot / "pom.xml")
    return base


def dep_so_em_anotacao(base: Path, m2: Path, com_jar=True):
    """Classes citadas so em anotacao (jdeps nao ve); lombok e processador."""
    escrever(base, {
        "pom.xml": pom("svc", deps=[
            dep("io.hypersistence", "hypersistence-utils-hibernate-71",
                "3.15.5"),
            dep("org.projectlombok", "lombok", "1.18.38")]),
        "src/main/java/s/Cfg.java": "package s;\npublic class Cfg {}\n",
        "target/.scos-map-tree.txt": arvore_tree(
            "br.com.sawcunhaos:svc:jar:1.0",
            ["+- io.hypersistence:hypersistence-utils-hibernate-71:jar:"
             "3.15.5:compile",
             "\\- org.projectlombok:lombok:jar:1.18.38:compile"]),
    })
    classe = base / "target/classes/s/Cfg.class"
    classe.parent.mkdir(parents=True, exist_ok=True)
    classe.write_bytes(b"\xca\xfe\xba\xbe\x00\x00\x00\x45"
                       b"Lio/hypersistence/utils/spring/repository/"
                       b"BaseJpaRepositoryImpl;Llombok/Generated;")
    git_init(base)
    _tocar_depois(base / "target/.scos-map-tree.txt", base / "pom.xml")
    jars = {"io/hypersistence/hypersistence-utils-hibernate-71/3.15.5/"
            "hypersistence-utils-hibernate-71-3.15.5.jar":
                "io/hypersistence/utils/spring/repository/"
                "BaseJpaRepositoryImpl.class",
            "org/projectlombok/lombok/1.18.38/lombok-1.18.38.jar":
                "lombok/Generated.class"}
    for rel, classe_no_jar in (jars.items() if com_jar else ()):
        (m2 / rel).parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(m2 / rel, "w") as z:
            z.writestr(classe_no_jar, b"x")
    return jdeps_falso(base, "classes -> java.base\n"
                             "   s.Cfg -> java.lang.Object   java.base")


def modulos_sem_codigo(base: Path):
    """Modulo so de resources e modulo so de .proto (este gera classes)."""
    escrever(base, {
        "pom.xml": pom("flow", packaging="pom",
                       modules=["recursos", "contrato"]),
        "recursos/pom.xml": pom("recursos", parent="flow"),
        "recursos/src/main/resources/db/changelog.xml": "<databaseChangeLog/>\n",
        "contrato/pom.xml": pom("contrato", parent="flow"),
        "contrato/src/main/proto/org.proto": 'syntax = "proto3";\n',
    })
    return git_init(base)


def workspace_scope_e_bom(base: Path):
    """Divergencia so em scope test + BOM com dependencyManagement."""
    escrever(base / "bom", {"pom.xml": pom(
        "scos-bom", packaging="pom", props={"lib.version": "2.0"},
        dep_mgmt=[dep("org.x", "lib", "${lib.version}"),
                  dep("org.z", "interno", "${project.version}")])})
    git_init(base / "bom")
    for nome, v_teste in (("a", "1.0"), ("b", "2.0")):
        p = base / nome
        escrever(p, {
            "pom.xml": pom(nome, deps=[
                dep("org.x", "lib", "1.0"),
                dep("org.y", "so-teste", v_teste, scope="test")]),
            "src/main/java/%s/C.java" % nome:
                "package %s;\npublic class C {}\n" % nome,
            "target/.scos-map-tree.txt": arvore_tree(
                "br.com.sawcunhaos:%s:jar:1.0" % nome,
                ["+- org.x:lib:jar:1.0:compile",
                 "\\- org.y:so-teste:jar:%s:test" % v_teste])})
        git_init(p)
        _tocar_depois(p / "target/.scos-map-tree.txt", p / "pom.xml")
    return base


# ---------------------------------------------------------------------------
# Mapa sintetico para o scos-map-query (escrito a mao, sem rodar o gerador)
# ---------------------------------------------------------------------------

GERADO_FIXO = "2026-09-15T00:32:06Z"
LAYOUT_APP = {
    "fato": "layout", "modulo": "app", "confianca": "alta",
    "base": "varredura de diretorio + regex de anotacao",
    "pacote_base": "br.com.scos.app", "arquivos": 12,
    "derivado_de": {"app/A.java": "0123456789ab"},
    "areas": [
        {"caminho": "app/src/main/java/br/com/scos/config",
         "papel": "config", "arquivos": 8},
        {"caminho": "app/src/main/java/br/com/scos/util",
         "papel": "util", "arquivos": 1}],
    "entrypoints": [
        {"path": "app/src/main/java/br/com/scos/Api.java", "tipo": "http"},
        {"path": "app/src/main/java/br/com/scos/Api.java", "tipo": "rota",
         "rota": "REQUEST /api"}],
}
CONFIG_APP = {
    "fato": "config", "modulo": "app", "confianca": "alta",
    "base": "PyYAML safe_load (valores omitidos)",
    "arquivos": [
        {"path": "app/src/main/resources/application.yml", "bytes": 1200,
         "chaves": ["SEGREDO_NUNCA_MOSTRAR"]},
        {"path": "app/src/main/resources/application-dev.yml", "bytes": 340},
        {"path": "app/pom.xml", "bytes": 900}],
}
DOCS_APP = {
    "fato": "docs", "modulo": "app", "confianca": "alta",
    "completude": {"nivel": "parcial", "limitacoes": ["subtipo vem do caminho"]},
    "itens": [
        {"path": "app/docs/adr/0001-cache.md", "titulo": "ADR 1: Cache",
         "subtipo": "adr"},
        {"path": "app/README.md", "titulo": "App do SCOS", "subtipo": "readme"},
        {"path": "app/docs/guia.md", "titulo": "Guia", "subtipo": "outro"}],
}
REACTOR = {
    "fato": "reactor", "modulo": "_reactor", "confianca": "alta",
    "base": "poms", "derivado_de": {},
    "modulos": [{"id": "_raiz", "tipo": "pom"}, {"id": "app", "tipo": "jar"},
                {"id": "lib/core", "tipo": "jar"}],
    "arestas_internas": [{"de": "app", "para": "lib/core", "scope": "compile"}],
}
GERENCIADAS_APP = (
    "ga\tversao\torigem\tscope\n"
    "org.springframework.kafka:spring-kafka-bom\t4.1.1\tpropria\timport\n"
    "com.google.errorprone:error_prone_annotations\t2.48.0\tpropria\tcompile\n")
FILES_TSV = (
    "path\tblob\tbytes\tlines\tmodule\tkind\tlast_commit\tlast_modified\tauthor"
    "\tcommits_90d\ttracked\n"
    "app/A.java\tb1\t10\t1\tapp\tcodigo\tc\t2026-01-01\tx\t7\t1\n"
    "app/B.java\tb2\t10\t1\tapp\tcodigo\tc\t2026-01-01\tx\t5\t1\n"
    "app/README.md\tb3\t10\t1\tapp\tdoc\tc\t2026-01-01\tx\t9\t1\n"
    "lib/core/C.java\tb4\t10\t1\tlib/core\tcodigo\tc\t2026-01-01\tx\t6\t1\n")
# colunas fora de ordem de proposito: o acesso e por nome (AD-3)
DEPS_APP = (
    "origem\ttipo\tga\tversao\tscope\tdivergente\n"
    "effective-pom\tdireta\tio.jsonwebtoken:jjwt-api\t0.12.6\tcompile\t\n"
    "transitiva\ttransitiva\tcom.x:y\t1.0\truntime\t\n")
DEPS_LIB = (
    "origem\ttipo\tga\tversao\tscope\tdivergente\n"
    "effective-pom\tdireta\tio.jsonwebtoken:jjwt-impl\t0.12.6\tcompile\t\n")
TRANSITIVAS = "ga\tversao\tscope\norg.jspecify:jspecify\t1.0.1\tcompile\n"
MODULOS_MAPA = ["_raiz", "app", "app/core", "lib/core"]


def mapa_sintetico(base: Path, projeto="proj", head=None, schema="2.1",
                   estado="fresco", layout=None, schema_indice=None, docs=None):
    """Workspace com um projeto (repo git real) e o fato layout do modulo app.

    head=None grava o HEAD real do repo (mapa fresco); passe outro valor para
    simular repo que andou depois do mapa.
    """
    repo = base / projeto
    escrever(repo, {"pom.xml": "<project/>\n"})
    git_init(repo)
    real = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo),
                          capture_output=True, text=True).stdout.strip()
    head_mapa = head or real[:12]
    layout = LAYOUT_APP if layout is None else layout
    fatos = {"app": {n: {"estado": estado, "arquivo": "facts/app/%s.json" % n}
                     for n in ("layout", "config", "docs", "deps")},
             "lib/core": {"deps": {"estado": estado,
                                   "arquivo": "facts/lib/core/deps.json"}}}
    mapa = repo / ".scos-map"
    escrever(mapa, {
        "index.json": json.dumps({
            "schema_versao": schema_indice or schema,
            "gerado_em": GERADO_FIXO, "git": {"head": head_mapa},
            "reactor": "facts/_reactor.json",
            "arquivos": {"tsv": "files.tsv"},
            "tabelas": {"facts/app/gerenciadas.tsv": {}},
            "modulos": {m: {"fatos": fatos.get(m, {})} for m in MODULOS_MAPA}}),
        "facts/_reactor.json": json.dumps(REACTOR),
        "facts/app/gerenciadas.tsv": GERENCIADAS_APP,
        "files.tsv": FILES_TSV,
        "facts/_transitivas_comuns.tsv": TRANSITIVAS,
        "facts/app/deps.tsv": DEPS_APP,
        "facts/lib/core/deps.tsv": DEPS_LIB,
        **{"facts/%s/deps.json" % m: json.dumps({
            "fato": "deps", "modulo": m, "confianca": "resolvida",
            "completude": {"nivel": "total"}, "corpo": "deps.tsv",
            "fecho_comum_arquivo": "../_transitivas_comuns.tsv"})
           for m in ("app", "lib/core")},
        "facts/app/layout.json": json.dumps(layout),
        "facts/app/config.json": json.dumps(CONFIG_APP),
        "facts/app/docs.json": json.dumps(DOCS_APP if docs is None else docs),
    })
    escrever(base / ".scos-map", {"workspace.json": json.dumps({
        "schema_versao": schema, "tipo": "workspace", "gerado_em": GERADO_FIXO,
        "projetos": [{"projeto": projeto,
                      "index": "%s/.scos-map/index.json" % projeto,
                      "modulos": MODULOS_MAPA}]})})
    return base
