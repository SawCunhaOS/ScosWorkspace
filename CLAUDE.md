# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estrutura do workspace

Este diretório **é** um repositório git próprio (`SawCunhaOS/ScosWorkspace`, branch `develop`) — mas
só versiona os artefatos de workspace (`.claude/` com as skills, `_bmad/`, `_bmad-output/`,
`.scos-map/workspace.json`, este `CLAUDE.md`). Ele **agrupa** três repositórios Git independentes do
ecossistema SCOS (SawCunha Open System) como diretórios comuns (não são submodules — por isso
aparecem como *untracked* no `git status` da raiz), cada um com seu próprio remote, branch e
histórico:

| Diretório | Repo GitHub | O que é |
|---|---|---|
| `sawcunha-open-system-bom/` | `SawCunhaOS/sawcunha-open-system-bom` | BOM (`packaging=pom`, sem código) — versões de dependência e convenções de build (enforcer, compiler, profile `analyze`) para todo o ecossistema |
| `SawCunhaOS-Foundation/` | `SawCunhaOS/SawCunhaOS-Foundation` | Biblioteca fundacional Java (auditoria, privacidade/masking LGPD, tratamento de exceção RFC 9457, idempotência, cache, utils) consumida pelos demais projetos |
| `SawCunhaOS-Flow/` | `SawCunhaOS/SawCunhaOS-Flow` (artifactId `flow`) | O produto: motor de identidade/organização/governança de acesso de um ISP. Único módulo com trabalho ativo hoje é `organization` |

**Nunca rode `git add -A`/`git add .` na raiz do workspace.** Como esses três diretórios têm `.git`
próprio mas não são submodules declarados (sem `.gitmodules`), o git os transformaria em *gitlinks*
fantasmas apontando pro commit atual de cada um — silenciosamente, sem versionar o conteúdo real.
Estão listados no `.gitignore` da raiz por segurança; se precisar commitar algo de um desses repos,
sempre `cd` para dentro dele primeiro.

Ordem de dependência de build: **bom → Foundation → Organization** (Organization importa
`scos-foundation` como BOM e consome seus artefatos como `-SNAPSHOT`, resolvidos do `~/.m2` local —
rode `mvn clean install` na Foundation antes de builds na Organization que precisem de uma mudança
recente dela).

Cada repo já tem sua própria documentação detalhada — **prefira consultá-la a re-derivar do código**:

- `sawcunha-open-system-bom/README.md` — como consumir o BOM (parent vs. import), branching/release, enforcer, profile `analyze`.
- `SawCunhaOS-Foundation/README.md` — um módulo por seção, exemplos de uso de cada lib.
- `SawCunhaOS-Foundation/AGENTS.md` (fonte: `bmad-project-context`) — políticas do repo (nunca commitar/dar push sem autorização explícita), onde ficam PRD/arquitetura/skills, convenção de commit por scope, pegadinha real de auto-configuração via `AutoConfiguration.imports` (não `@ComponentScan`).
- `SawCunhaOS-Foundation/etc/doc/commit-convention.md` — Conventional Commits com scope = módulo Maven.
- `SawCunhaOS-Flow/README.md` — visão geral completa: estado do sprint (BMAD), arquitetura DDD em camadas com diagrama de dependência, padrões reais de código (specification+Bean, Use Case, Delegate), convenções de nomenclatura de banco/permissão/erro, como rodar (Docker Compose em `etc/infra/`).
- Módulos com `AGENTS.md` próprio na Foundation: `audit/`, `privacy/`, `web/`, `archtest/`.

Índice estrutural preferencial: **scos-map** (skill local, ver seção abaixo) — já mapeado em
`.scos-map/` na raiz e em cada um dos três repos. Use-o antes do `etc/aimap.py` legado (`.aimap/` por
repo, `python etc/aimap.py scan <repo>`) ou de `graphify query/path/explain` (se `graphify-out/`
existir num repo — ver `~/.claude/CLAUDE.md`): scos-map é o único que enxerga divergência de versão
de dependência ENTRE os três repos.

## Índice estrutural (scos-map)

Skill local em `.claude/skills/scos-map/` (não é a skill global `graphify`). Para perguntas sobre
**organização de código** — onde mora o quê, dependências e versões, configs, docs, fronteiras entre
módulos — e não sobre o conteúdo de um arquivo específico já conhecido, consulte o índice em vez de
grep bruto ou de reler tudo.

```bash
python3 .claude/skills/scos-map/scos-map.py status .                      # existe mapa? o que está obsoleto?
python3 .claude/skills/scos-map/scos-map.py workspace .                   # (re)gera o mapa dos 3 repos
python3 .claude/skills/scos-map/scos-map.py workspace . --only <projeto>  # reprocessa só um projeto
```

Leitura: comece por `.scos-map/workspace.json` na raiz — lista os projetos e aponta o `index.json` de
cada um; `conflitos_de_versao_cruzados` é o único fato que compara bibliotecas entre os repos. Dentro
de um projeto, leia **apenas** `<repo>/.scos-map/index.json` e abra só os fatos que a pergunta exige:

| Pergunta é sobre | Abra |
|---|---|
| onde mora o quê, ponto de entrada, convenção de pacote | `facts/<mod>/layout.json` |
| configs, chaves, perfis | `facts/<mod>/config.json` |
| dependências, versões declaradas x resolvidas | `facts/<mod>/deps.json` |
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
por convenção de nome, confirme antes de afirmar. Detalhe completo: `.claude/skills/scos-map/SKILL.md`.

## Comandos comuns

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

## Convenções que valem para os três repos

- **Conventional Commits** (`type(scope): descrição`), scope = módulo Maven afetado — ver tabela de
  scopes em `SawCunhaOS-Foundation/etc/doc/commit-convention.md`. `SawCunhaOS-Flow` e a BOM
  seguem o mesmo padrão de tipos (`feat`/`fix`/`docs`/`refactor`/`test`/`chore`/`ci`/`build`).
- **Branching**: `develop` (integração, próxima major em `-SNAPSHOT`) → `release/x.y.z` (minor em
  estabilização) → `fix/x.y.z` (patch). PRs para a Foundation são validados por
  `scripts/validate-pr-target.sh` no CI.
- **Nunca commitar ou dar push sem autorização explícita do humano** (regra explícita da Foundation,
  aplicada aqui a todos os três repos por segurança).
- Java 25 + Maven 3.9+ em todos; Spring Boot 4.x / Spring Framework 7 gerenciados pela BOM.

## Arquitetura — SawCunhaOS-Foundation

Multi-módulo Maven em camadas de dependência (não alfabético — a ordem em `pom.xml` documenta o
grafo real, com comentários por módulo explicando por quê):

```
audit-api, jdempotent-api, validation-api, codegen   (leaves — zero dependências de runtime)
core                                                  (utilitários zero-Spring)
spring          → core
privacy         → core                                (masking de PII, motor usável fora do Spring)
validation      → core + validation-api
cache           → core + spring-boot-starter-cache/data-redis
jpa             → core + validation + querydsl + liquibase (opcional)
web             → core + cache + privacy               (o mais acoplado dos leaves)
feign           → core
utils           → core + privacy + jpa*                (component-scan; consumidor final)
audit, jdempotent → módulos leaf correspondentes + suas *-api
```

Ativação em app consumidora: `utils` sobe por `@ComponentScan(basePackages="br.com.sawcunhaos")`;
`web`, `privacy`, `audit`, `jdempotent` por auto-configuração via
`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` — **um bean com
só `@Component` nesses módulos nunca é criado numa app real** (bug real pego em code review, Story 1.15).

## Arquitetura — SawCunhaOS-Flow (produto "Flow")

DDD tático em camadas, hexagonal-adjacente, já ratificado no código do módulo `organization`:

```
domain          → entidades JPA, domain services (interface pública + *ServiceBean package-private), repositórios
usecase         → orquestração: interface pública XxxUseCase + XxxUseCaseBean (@Service, package-private)
api             → XxxDelegate implements XxxApiDelegate (gerado do OpenAPI) — fino, sem regra de negócio
infrastructure  → cross-cutting (permissões, filtros, enums transversais)
boot / grpc-boot → composition roots (REST e gRPC)
```

Regra de dependência (nunca violar): `api → usecase → domain`; `api` **nunca** enxerga `domain`
diretamente. Contrato REST é OpenAPI-first (`etc/api/organization/*.yml` → `openapi-generator-maven-plugin`
gera o `XxxApiDelegate`); endpoint sem `@Override` no Delegate cai no `default` gerado, que lança
`MethodNotImplementedException` — sinal de rota ainda não implementada.

Convenções de código já em vigor (não reinventar por story): erro de domínio sempre via `ScosException`
+ `ExceptionCodeError` (nunca `RuntimeException` cru); `@Transactional(rollbackFor = ScosException.class)`
em todo Use Case de escrita; `Instant`↔`TIMESTAMPTZ` / `LocalDate`↔`DATE` / `LocalTime`↔`TIME` —
`LocalDateTime` e `.now()` estático são **proibidos no domínio** (Epic 0, `Clock` injetável); consulta
hierárquica/recursiva sempre via CTE `WITH RECURSIVE` no banco, nunca caminhada em memória. Detalhe
completo de cada padrão (com exemplo de código real) e do estado do sprint por épico:
`SawCunhaOS-Flow/README.md`.

`notification/` e `geotemporal/` são módulos-esqueleto (reserva para fases futuras) — não têm código
ainda. Em aberto (não decidido): qual módulo é o deployável real de produção, `server-fat` ou
`flow-organization-boot` standalone — os dois coexistem hoje.
