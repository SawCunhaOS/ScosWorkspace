# Story 4.15: Documentar o módulo `privacy`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor usando sanitização de dados,
Eu quero o perfil `analyze` ligado e um diagrama de fluxo de uso,
Para ter o mesmo piso de qualidade dos demais módulos.

## Acceptance Criteria

1. **Given** o módulo `privacy` (não tocado funcionalmente neste ciclo, README já existente, sem perfil `analyze` hoje), **When** o perfil `analyze` é ligado e o diagrama Mermaid é adicionado ao README, **Then** o Checkstyle passa a cobrir `privacy` e o README tem o diagrama do fluxo típico de uso.

## Tasks / Subtasks

- [ ] Task 1: Confirmar o estado real antes de mexer (AC: #1)
  - [ ] **Confirmado por leitura direta**: `privacy/pom.xml` **não tem** o profile `analyze` hoje (`grep -n analyze privacy/pom.xml` não retorna nada, diferente de `audit`/`jdempotent`/`utils`/`exception`, que já têm — `privacy` é de fato o 5º módulo do reactor atual sem o profile, confirmando a contagem "4 de 5" citada na Story 1.4 do Epic 1)
  - [ ] **Confirmado por leitura direta**: `privacy/README.md` já existe e é extenso (347 linhas) — cobre regras de masking, estratégias, integração Logback, uso standalone, criptografia at-rest e performance — mas **não tem nenhum diagrama** (nem ASCII, nem Mermaid) hoje; é puramente texto/tabelas/exemplos de código
- [ ] Task 2: Ligar o profile `analyze` em `privacy/pom.xml` (AC: #1)
  - [ ] Copiar a estrutura do profile `analyze` já usada em `audit/pom.xml` (Jacoco com `COVEREDRATIO` mínimo 0.80, Checkstyle com `configLocation` apontando para `etc/devops/checkstyle/checkstyle.xml`) para `privacy/pom.xml`, ajustando os `excludes` do Jacoco para os pacotes específicos de `privacy` (não copiar os excludes de `audit` literalmente — são pacotes de outro módulo)
  - [ ] **Não ativar `failOnViolation` global** — isso é escopo da Story 4.16, não desta; esta story só liga o profile em `privacy`, do mesmo jeito que os outros 4 módulos já têm
  - [ ] Confirmar que `mvn -Panalyze verify` roda em `privacy` sem erro de configuração (mecanismo disponível, não necessariamente bloqueante ainda — mesma cautela da Story 1.4)
- [ ] Task 3: Adicionar diagrama Mermaid do fluxo típico de uso (AC: #1)
  - [ ] Criar um `flowchart` Mermaid cobrindo a tabela "Which rule fires where" já existente no README (linhas 98-110): as 4 superfícies de PII (`headers`, `body`, `log-patterns`, `audit-encrypt-fields`) e onde cada uma é consumida (filtro HTTP de log, conversor Logback `%mask`, cifra de campo do audit trail)
  - [ ] Preservar todo o conteúdo textual já existente — esta story só adiciona o diagrama e liga o profile `analyze`, não reescreve o README

## Dev Notes

- Junto da Story 4.14, é uma das duas stories deste epic que documenta um módulo já existente e não tocado estruturalmente pelo ciclo 1.2.0 — mudança aditiva (profile + diagrama), não documentação do zero.
- `privacy` está na base do grafo de dependência (`utils`/`audit`/`web` dependem dele, ele não depende de `utils` — carrega seu próprio Gson, confirmado no README linha 15) — isso é relevante para o diagrama: `privacy` não é tocado pela migração Gson→Jackson da Story 1.3 (que é só de `utils`/`audit`/`privacy`... conferir: a Story 1.3 já lista `JsonMasker` de `privacy` como um dos alvos da migração — então, se a Story 1.3 já tiver rodado quando esta story for feita, o README de `privacy` deve refletir Jackson, não mais Gson próprio; ajustar a frase "carrega seu próprio Gson" se já migrado).

### Project Structure Notes

- Arquivo modificado: `privacy/pom.xml` (profile `analyze` adicionado).
- Arquivo modificado: `privacy/README.md` (diagrama Mermaid adicionado; conteúdo textual existente preservado; frase sobre Gson revisada se a Story 1.3 já tiver migrado o `JsonMasker`).

### References

- [Source: privacy/pom.xml] (sem profile `analyze` hoje, confirmado)
- [Source: audit/pom.xml#profile-analyze] (modelo a seguir para o profile)
- [Source: privacy/README.md] (README existente, 347 linhas, sem diagrama hoje)
- [Source: _bmad-output/implementation-artifacts/1-4-promover-o-perfil-analyze-checkstyle-archunit-para-pluginman.md] (contexto "4 de 5 módulos", confirma `privacy` como o 5º)
- [Source: _bmad-output/implementation-artifacts/1-3-migrar-serialização-json-de-gson-para-jackson.md] (dependência cruzada condicional sobre o texto do README)
- [Source: _bmad-output/planning-artifacts/epics.md#story-415-documentar-o-módulo-privacy]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
