# Story 3.20: Corrigir herança do `@JdempotentId` e ampliar cobertura de anotações do `jdempotent`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero que as anotações de contrato (`@JdempotentId`, `@JdempotentProperty`, `@JdempotentIgnore`, `@JdempotentResource`) funcionem corretamente em herança e tenham cobertura de teste para as combinações reais de uso,
Para eliminar falhas silenciosas e reduzir o risco de regressão nesse contrato.

## Acceptance Criteria

1. **Given** um campo anotado com `@JdempotentId` declarado numa superclasse, **When** `IdempotentAspect.setJdempotentId()` roda após a execução do método protegido, **Then** o campo recebe o valor gerado (bug conhecido, hoje falha silenciosamente sem exceção).
2. **Given** um payload com 2+ campos anotados com `@JdempotentId`, **When** o aspecto roda, **Then** todos os campos recebem o valor.
3. **Given** um objeto com campos anotados simultaneamente com `@JdempotentIgnore` e `@JdempotentProperty` (campos diferentes), **When** a chave de idempotência é composta via `IdempotentAspect` fim a fim, **Then** o hash reflete corretamente a combinação (campo ignorado fora do hash, propriedade com o nome customizado).
4. **Given** `@JdempotentProperty` sem `value()` explícito (default `""`), **When** o campo é processado pela chain, **Then** o comportamento resultante (usa nome do campo? usa string vazia como chave?) é documentado por teste.
5. **Given** um método anotado com `@JdempotentResource` sobrescrito por uma subclasse sem repetir a anotação, **When** a subclasse é chamada, **Then** o comportamento (aspecto ativa ou não) é coberto por teste.
6. **Given** `@JdempotentResource` sem `cachePrefix` explícito (default `""`), **When** a chave final é composta, **Then** um teste confirma o efeito do prefixo vazio na chave gerada.

## Tasks / Subtasks

- [ ] Task 1: Corrigir o bug de herança do `@JdempotentId` (AC: #1)
  - [ ] `IdempotentAspect.setJdempotentId()` (`jdempotent/src/main/java/.../core/aspect/IdempotentAspect.java`, ~linha 267-280) usa `arg.getClass().getDeclaredFields()` — trocar para percorrer a hierarquia completa de campos, mesmo padrão já usado por `getAllFieldsInHierarchy` (usado por `getIdempotentNonIgnorableWrapper`, ~linha 282-330)
  - [ ] Bug já documentado em `deferred-work.md` (origem: Story 3.3 — "resolver campos anotados em toda a hierarquia de classes" — que resolveu a leitura da hierarquia para composição de chave, mas não para a escrita de volta do `@JdempotentId`)
- [ ] Task 2: Testes de combinação/herança (AC: #2, #3, #5)
  - [ ] Payload com múltiplos campos `@JdempotentId` simultâneos — todos recebem o valor
  - [ ] Herança combinada com `@JdempotentId`/`@JdempotentProperty`/`@JdempotentIgnore` (campo anotado na superclasse, não só na classe folha)
  - [ ] `@JdempotentIgnore` + `@JdempotentProperty` no mesmo objeto, hash final validado via `IdempotentAspect` fim a fim (não só via chain isolada, como os testes de `JdempotentIgnoreAnnotationChainTest`/`JdempotentPropertyAnnotationChainTest` já fazem separadamente)
  - [ ] `@JdempotentResource` em método sobrescrito por subclasse sem repetir a anotação
- [ ] Task 3: Testes de valores default (AC: #4, #6)
  - [ ] `@JdempotentProperty` com `value()` default (`""`)
  - [ ] `cachePrefix` default (`""`) fim a fim — o único teste hoje com prefixo default (`idempotentMethod`) não verifica o efeito na chave gerada

## Dev Notes

- Origem: investigação de cobertura de anotações feita durante a review da Story 3.19 (2026-08-30) + bug já conhecido registrado em `deferred-work.md` (origem: Story 3.3, já com status `review`/fechada — a Task 2 daquela story já documentava a lacuna explicitamente e condicionou a extensão do escopo a uma confirmação que não ocorreu naquela execução).
- **Ponytail**: não introduzir suporte a comportamento novo para múltiplos `@JdempotentId` — o código já itera todos os campos declarados, só precisa de teste cobrindo herança + múltiplos campos. Não inventar semântica não pedida para `value()` vazio — só documentar via teste o comportamento atual da chain.
- Distinto da Story 3.15 (`corrigir-ttl-e-equals-hashcode.md`): aquela cobre o TTL ignorado pelo `InMemoryIdempotentRepository` e o bug de `equals`/`hashCode`; esta story é especificamente sobre as anotações de contrato (`@JdempotentId`/`@JdempotentProperty`/`@JdempotentIgnore`/`@JdempotentResource`) e sua cobertura de teste.

### Project Structure Notes

- Arquivo modificado: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (Task 1).
- Arquivos de teste estendidos: `jdempotent/src/test/java/.../core/aspect/IdempotentAspectTest.java`, `IdempotentAspectUTTest.java`.

### References

- [Source: _bmad-output/implementation-artifacts/deferred-work.md — bug de herança do `@JdempotentId` em `setJdempotentId()`, origem Story 3.3]
- [Source: _bmad-output/implementation-artifacts/3-19-topologia-redis-parametrizada-concorrencia-e-throughput.md — investigação de cobertura das anotações do jdempotent, 2026-08-30]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
