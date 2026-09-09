# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estrutura do workspace

Este diretório **não é um repositório git** — é um workspace que agrupa três repositórios Git
independentes do ecossistema SCOS (SawCunha Open System), cada um com seu próprio remote, branch e
histórico:

| Diretório | Repo GitHub | O que é |
|---|---|---|
| `sawcunha-open-system-bom/` | `SawCunhaOS/sawcunha-open-system-bom` | BOM (`packaging=pom`, sem código) — versões de dependência e convenções de build (enforcer, compiler, profile `analyze`) para todo o ecossistema |
| `SawCunhaOS-Foundation/` | `SawCunhaOS/SawCunhaOS-Foundation` | Biblioteca fundacional Java (auditoria, privacidade/masking LGPD, tratamento de exceção RFC 9457, idempotência, cache, utils) consumida pelos demais projetos |
| `SawCunhaOS-Organization/` | `SawCunhaOS/SawCunhaOS-Flow` (artifactId `flow`) | O produto: motor de identidade/organização/governança de acesso de um ISP. Único módulo com trabalho ativo hoje é `organization` |

Ordem de dependência de build: **bom → Foundation → Organization** (Organization importa
`scos-foundation` como BOM e consome seus artefatos como `-SNAPSHOT`, resolvidos do `~/.m2` local —
rode `mvn clean install` na Foundation antes de builds na Organization que precisem de uma mudança
recente dela).

Cada repo já tem sua própria documentação detalhada — **prefira consultá-la a re-derivar do código**:

- `sawcunha-open-system-bom/README.md` — como consumir o BOM (parent vs. import), branching/release, enforcer, profile `analyze`.
- `SawCunhaOS-Foundation/README.md` — um módulo por seção, exemplos de uso de cada lib.
- `SawCunhaOS-Foundation/AGENTS.md` (fonte: `bmad-project-context`) — políticas do repo (nunca commitar/dar push sem autorização explícita), onde ficam PRD/arquitetura/skills, convenção de commit por scope, pegadinha real de auto-configuração via `AutoConfiguration.imports` (não `@ComponentScan`).
- `SawCunhaOS-Foundation/etc/doc/commit-convention.md` — Conventional Commits com scope = módulo Maven.
- `SawCunhaOS-Organization/README.md` — visão geral completa: estado do sprint (BMAD), arquitetura DDD em camadas com diagrama de dependência, padrões reais de código (specification+Bean, Use Case, Delegate), convenções de nomenclatura de banco/permissão/erro, como rodar (Docker Compose em `etc/infra/`).
- Módulos com `AGENTS.md` próprio na Foundation: `audit/`, `privacy/`, `web/`, `archtest/`.

Ferramenta utilitária na raiz: `etc/aimap.py` — gera um índice estrutural (`.aimap/`) de layout,
config, deps e docs por repo, pensado para consumo por IA (stdlib only, `python etc/aimap.py scan <repo>`).
Se `graphify-out/` existir dentro de um dos repos, prefira `graphify query/path/explain` a ele e ao
grep bruto (ver `~/.claude/CLAUDE.md`).

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
  scopes em `SawCunhaOS-Foundation/etc/doc/commit-convention.md`. `SawCunhaOS-Organization` e a BOM
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

## Arquitetura — SawCunhaOS-Organization (produto "Flow")

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
`SawCunhaOS-Organization/README.md`.

`notification/` e `geotemporal/` são módulos-esqueleto (reserva para fases futuras) — não têm código
ainda. Em aberto (não decidido): qual módulo é o deployável real de produção, `server-fat` ou
`flow-organization-boot` standalone — os dois coexistem hoje.
