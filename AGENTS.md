<!-- bmad:context -->
<!-- Verificado em 2026-09-14 contra bc2be1e. Gerenciado por bmad-project-context; edições dentro deste bloco são substituídas no refresh. Guarde o que quiser preservar fora dos marcadores. -->

## ScosWorkspace

Este diretório **é** um repositório git próprio (`SawCunhaOS/ScosWorkspace`, branch `develop`) — mas
só versiona os artefatos de workspace (`.claude/` com as skills, `_bmad/`, `_bmad-output/`,
`.scos-map/workspace.json`, este `AGENTS.md`). Ele **agrupa** três repositórios Git independentes do
ecossistema SCOS (SawCunha Open System) como diretórios comuns (não são submodules — por isso
aparecem como *untracked* no `git status` da raiz), cada um com seu próprio remote, branch e
histórico (tabela em Where things are). Ordem de dependência de build: **bom → Foundation →
Organization** (Organization importa `scos-foundation` como BOM e consome seus artefatos como
`-SNAPSHOT`, resolvidos do `~/.m2` local — rode `mvn clean install` na Foundation antes de builds na
Organization que precisem de uma mudança recente dela).

## Policy

- **Nunca rode `git add -A`/`git add .` na raiz do workspace.** Como esses três diretórios têm `.git`
  próprio mas não são submodules declarados (sem `.gitmodules`), o git os transformaria em *gitlinks*
  fantasmas apontando pro commit atual de cada um — silenciosamente, sem versionar o conteúdo real.
  Estão listados no `.gitignore` da raiz por segurança; se precisar commitar algo de um desses repos,
  sempre `cd` para dentro dele primeiro.
- **Nunca commitar ou dar push em nenhum dos três repos sem autorização explícita do humano** (regra
  explícita da Foundation, aplicada aqui a todos os três por segurança).

## Where things are

| Diretório | Repo GitHub | O que é |
|---|---|---|
| `sawcunha-open-system-bom/` | `SawCunhaOS/sawcunha-open-system-bom` | BOM (`packaging=pom`, sem código) — versões de dependência e convenções de build (enforcer, compiler, profile `analyze`) para todo o ecossistema |
| `SawCunhaOS-Foundation/` | `SawCunhaOS/SawCunhaOS-Foundation` | Biblioteca fundacional Java (auditoria, privacidade/masking LGPD, tratamento de exceção RFC 9457, idempotência, cache, utils) consumida pelos demais projetos |
| `SawCunhaOS-Flow/` | `SawCunhaOS/SawCunhaOS-Flow` (artifactId `flow`) | O produto: motor de identidade/organização/governança de acesso de um ISP. Módulos com código real: `organization` (principal), `security`, `audit`, `infrastructure`; `notification` e `geotemporal` são esqueleto |

**Artefatos BMAD — só no workspace.** A instalação (`_bmad/`, skills em `.claude/`) e os artefatos
(`_bmad-output/`) moram só aqui; os três repos **não** guardam artefato BMAD (sem `_bmad*`, sem blocos
gerenciados pelo BMAD). Uma subpasta por projeto em `_bmad-output/<projeto>/` (hoje só
`SawCunhaOS-Foundation/`); o projeto ativo é definido pelos caminhos em `_bmad/{bmm,tea,core}/config.yaml`
e `_bmad/custom/config.toml` — trocar de projeto é editar esses caminhos; reinstalar o BMAD regrava os
`*.yaml` (responda com os caminhos por projeto). Caminhos de código citados nas stories são relativos à
raiz do repo do projeto. Os artefatos BMAD antigos do Flow (Organization) estão só no histórico dele:
`git -C SawCunhaOS-Flow show e56929b^:_bmad-output/<arquivo>`.

Cada repo já tem sua própria documentação detalhada — **prefira consultá-la a re-derivar do código**:

- `sawcunha-open-system-bom/README.md` — como consumir o BOM (parent vs. import), branching/release, enforcer, profile `analyze`.
- `SawCunhaOS-Foundation/README.md` — um módulo por seção, exemplos de uso de cada lib.
- `SawCunhaOS-Flow/README.md` — visão geral completa: estado do sprint (BMAD), arquitetura DDD em camadas com diagrama de dependência, padrões reais de código (specification+Bean, Use Case, Delegate), convenções de nomenclatura de banco/permissão/erro, como rodar (Docker Compose em `etc/infra/`).
- Cada um dos três repos tem seu próprio `AGENTS.md` (política, comandos, convenções, pitfalls específicos) — carregado automaticamente ao trabalhar dentro dele. A Foundation também tem `AGENTS.md` por módulo: `audit/`, `privacy/`, `web/`, `archtest/`.

Índice estrutural preferencial: **scos-map** (skill local, ver abaixo) — já mapeado em `.scos-map/` na
raiz e em cada um dos três repos. Use-o antes de `graphify query/path/explain` (se `graphify-out/`
existir num repo — ver `~/.claude/CLAUDE.md`): scos-map é o único que enxerga divergência de versão
de dependência ENTRE os três repos.

### Índice estrutural (scos-map)

Duas skills locais (não são a skill global `graphify`): `scos-map` (`.claude/skills/scos-map/`) só
consulta o mapa; `scos-map-build` (`.claude/skills/scos-map-build/`) gera e mantém. O gerador é
`ferramentas/scos-map/scos-map.py` (testes em `ferramentas/scos-map/tests/`). Para perguntas sobre
**organização de código** — onde mora o quê, dependências e versões, configs, docs, fronteiras entre
módulos — e não sobre o conteúdo de um arquivo específico já conhecido, consulte o índice em vez de
grep bruto ou de reler tudo.

```bash
python3 ferramentas/scos-map/scos-map.py status .                      # existe mapa? o que está obsoleto?
python3 ferramentas/scos-map/scos-map.py workspace .                   # (re)gera o mapa dos 3 repos
python3 ferramentas/scos-map/scos-map.py workspace . --only <projeto>  # reprocessa só um projeto
```

Leitura: comece por `.scos-map/workspace.json` na raiz — lista os projetos e aponta o `index.json` de
cada um; `conflitos_de_versao_cruzados` é o único fato que compara bibliotecas entre os repos. Dentro
de um projeto, leia **apenas** `<repo>/.scos-map/index.json` e abra só os fatos que a pergunta exige:

| Pergunta é sobre | Abra |
|---|---|
| onde mora o quê, ponto de entrada, convenção de pacote | `facts/<mod>/layout.json` |
| configs, chaves, perfis | `facts/<mod>/config.json` |
| dependências, versões declaradas x resolvidas | `facts/<mod>/deps.json` + `deps.tsv` |
| versões que a BOM fixa (`dependencyManagement`) | `facts/<mod>/gerenciadas.tsv` |
| documentação existente sobre X | `facts/<mod>/docs.json` |
| fronteiras entre módulos, conflito de versão | `facts/_reactor.json` |
| listar/filtrar arquivos, churn | `files.tsv` (grep/awk — não carregar inteiro) |

Tier 1 (`scan`/`workspace` sem flag) cobre a maioria das perguntas de navegação, em segundos, sem
build — é o suficiente para uso rotineiro. Só escale para `--tier 2` (exige `target/classes`; o
script nunca compila sozinho sem autorização) ou `--tier 3 --callgraph-jar <path>` quando a pergunta
for de qualidade arquitetural (ciclos entre pacotes, dependência não declarada) ou de grafo de
chamada — e só com pedido explícito. `--all` roda tudo de uma vez e imprime um plano antes e um
resumo de achados no fim.

Respeite o campo `confianca`/`estado` de cada fato antes de afirmar algo ao usuário: `obsoleto`
significa que o fonte mudou depois do fato ser gerado (regenere ou avise); `heuristica` é inferência
por convenção de nome, confirme antes de afirmar. Detalhe completo: `.claude/skills/scos-map/SKILL.md`
(consulta) e `.claude/skills/scos-map-build/SKILL.md` (geração).

## Running and verifying

Todos os comandos abaixo rodam **de dentro do repo** relevante (`cd SawCunhaOS-Foundation` etc.), não
na raiz do workspace — não há `pom.xml` agregador na raiz do SCOS.

```bash
# Build e instala no ~/.m2 (necessário antes de builds em repos que dependem deste)
mvn clean install

# Só testes unitários (não roda checkstyle/spotbugs/dependency-check)
mvn test

# Um teste/método específico, num módulo específico
mvn test -pl <modulo> -Dtest=NomeDaClasse#nomeDoMetodo

# + testes de integração (Testcontainers — Foundation: audit e jdempotent;
# Organization: *ControllerTest em flow-organization-boot). Precisa do Docker rodando.
mvn verify

# Análise estática completa (perfil não incluso em test/verify por padrão)
mvn -Panalyze verify

# Organization: subir a app REST (ver application.yml em flow-organization-boot para as env vars ${SCOS_*} exigidas)
docker compose -f etc/infra/docker-compose-database.yml up -d
docker compose -f etc/infra/docker-compose-redis.yml up -d
docker compose -f etc/infra/docker-compose-keycloak.yml up -d
mvn spring-boot:run -pl organization/flow-organization-boot
```

## Conventions that differ from defaults

- **Conventional Commits** (`type(scope): descrição`), scope = módulo Maven afetado — ver tabela de
  scopes em `SawCunhaOS-Foundation/etc/doc/commit-convention.md`. `SawCunhaOS-Flow` e a BOM
  seguem o mesmo padrão de tipos (`feat`/`fix`/`docs`/`refactor`/`test`/`chore`/`ci`/`build`).
- **Branching**: `develop` (integração, próxima major em `-SNAPSHOT`) → `release/x.y.z` (minor em
  estabilização) → `fix/x.y.z` (patch). PRs para a Foundation são validados por
  `scripts/validate-pr-target.sh` no CI.
- Java 25 + Maven 3.9+ em todos; Spring Boot 4.x / Spring Framework 7 gerenciados pela BOM.

<!-- /bmad:context -->
