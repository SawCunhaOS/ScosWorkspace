# Story 4.13: Documentar o módulo `jdempotent`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor habilitando idempotência,
Eu quero Javadoc, README e diagrama de sequência do fluxo de aquisição de lock,
Para entender a garantia real sob fail-open.

## Acceptance Criteria

1. **Given** o módulo `jdempotent` já com Checkstyle ativo e o README parcial da Story 3.17 (princípio "cache é fast-path"), **When** a documentação é completada, **Then** toda API pública tem Javadoc, decisões não-óbvias têm comentário inline, e o README traz diagrama de sequência Mermaid do fluxo `tryAcquire` → `Lease` → fail-open.

## Tasks / Subtasks

- [ ] Task 1: Confirmar o estado real do módulo antes de começar (AC: #1)
  - [ ] **Confirmado por leitura direta**: diferente da maioria das stories deste epic, `jdempotent` **já existe** hoje no repositório (`jdempotent/pom.xml`, com o profile `analyze` já presente — confirmado via `grep -rl "<id>analyze</id>" --include=pom.xml .`) — não é um módulo novo do Epic 1
  - [ ] **Confirmado por leitura direta**: `jdempotent/README.md` **não existe** hoje (`find jdempotent -maxdepth 1 -iname "README*"` não retorna nada) — o "README parcial da Story 3.17" citado no AC só existirá depois que a Story 3.17 (última do Epic 3) rodar e criar/atualizar esse arquivo; antes disso não há README nenhum para completar
  - [ ] **Confirmado por leitura direta**: classes públicas centrais como `IdempotentAspect` não têm bloco de Javadoc de classe hoje (só o cabeçalho de copyright/licença) — confirma que o gate de Javadoc ainda não está sendo cumprido neste módulo, mesmo com o profile `analyze` já ativo
  - [ ] Esta story só deve rodar depois da Story 3.17 (Epic 3) ter criado o README base — se rodar antes, tratar a ausência de README como "criar do zero", não "completar", e migrar o conteúdo da Story 3.17 para cá quando ela terminar
- [ ] Task 2: Javadoc em toda API pública (AC: #1)
  - [ ] Cobrir as classes centrais do módulo: `IdempotentAspect`, `IdempotentRepository`/`AbstractIdempotentRepository`/`InMemoryIdempotentRepository`/`RedisIdempotentRepository`, `Lease` (nova, Story 3.5), `IdempotencyKeyResolver` (nova, Story 3.12), e as anotações se ainda não tiverem sido movidas para `jdempotent-api` (Story 1.5) no momento desta story
  - [ ] Documentar explicitamente no Javadoc de `IdempotentAspect`/`RedisIdempotentRepository` o comportamento fail-open (Story 3.7) e a política de falha declarável por método (`RELEASE`/`KEEP_FAILED`, Story 3.8)
- [ ] Task 3: Comentários inline onde a lógica não é óbvia (AC: #1)
  - [ ] Comentar o script Lua de `tryAcquire` (Story 3.5) explicando o que ele garante atomicamente (não é óbvio ler Lua embutido em Java sem contexto)
  - [ ] Comentar a lógica de allowlist do `PolymorphicRedisSerializer` (Story 3.16, módulo `cache`) só se referenciada aqui — a classe em si é documentada na Story 4.9
- [ ] Task 4: Diagrama de sequência Mermaid do fluxo `tryAcquire` → `Lease` → fail-open (AC: #1)
  - [ ] Adicionar ao `jdempotent/README.md` (criado/atualizado pela Story 3.17) um diagrama `sequenceDiagram` Mermaid cobrindo: aplicação chama método anotado → aspecto intercepta → `tryAcquire(key, payloadHash, ttl)` → Redis disponível: Lease adquirido ou 409/422 → Redis indisponível: circuit breaker abre → fail-open (negócio prossegue sem lock) → constraint `UNIQUE` do banco como garantia real
  - [ ] Este é o único diagrama do epic pedido como `sequenceDiagram` explicitamente (as demais stories pedem só "diagrama Mermaid do fluxo típico", mais genérico) — respeitar o tipo de diagrama pedido

## Dev Notes

- **Ordem obrigatória**: esta story depende de todo o Epic 3 estar substancialmente implementado (as classes que documenta — `Lease`, `tryAcquire`, allowlist, política de falha — só existem depois das Stories 3.5 a 3.17) e da Story 3.17 especificamente para o README base.
- Diferente de quase todas as outras stories deste epic (que documentam módulos que "nascem" no Epic 1), esta documenta um módulo que já existe e já está sendo modificado por outro epic inteiro (Epic 3) — o gate de Javadoc aqui é sobre o estado *final* pós-Epic 3, não o estado atual.

### Project Structure Notes

- Arquivo modificado: `jdempotent/README.md` (criado pela Story 3.17, complementado aqui com o diagrama de sequência e qualquer seção de uso ainda faltante).
- Javadoc adicionado às classes públicas de `jdempotent` (várias delas novas do Epic 3).

### References

- [Source: jdempotent/pom.xml#profile-analyze] (profile já ativo, confirmado)
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java] (sem Javadoc de classe hoje, confirmado)
- [Source: _bmad-output/implementation-artifacts/3-17-substituir-construtores-telescópicos-por-builder-e-documenta.md] (README base)
- [Source: _bmad-output/implementation-artifacts/3-5-tornar-a-aquisição-do-lock-atômica-tryacquire-lease.md]
- [Source: _bmad-output/implementation-artifacts/3-7-garantir-fail-open-com-circuit-breaker-quando-o-redis-está-i.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-413-documentar-o-módulo-jdempotent]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
