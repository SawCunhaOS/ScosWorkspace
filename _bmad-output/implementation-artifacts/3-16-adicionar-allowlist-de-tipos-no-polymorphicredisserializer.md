# Story 3.16: Adicionar allowlist de tipos no `PolymorphicRedisSerializer`

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor preocupado com segurança,
Eu quero que apenas tipos permitidos sejam desserializados do Redis,
Para eliminar o risco de desserialização de tipo arbitrário.

## Acceptance Criteria

1. **Given** um valor vindo do Redis antes de `Class.forName`, **When** a allowlist de tipos permitidos é aplicada, **Then** tipos fora da allowlist são rejeitados antes da desserialização.
2. **Given** valores de tipos variados permitidos pela allowlist (`BigDecimal`, `LocalDate`/`LocalDateTime`/`Instant`, `enum`, array, `Optional<T>`, `Map`, `UUID`, coleção genericamente parametrizada como `List<T>`, objeto aninhado), **When** o round-trip serialize/deserialize do `PolymorphicRedisSerializer` é executado, **Then** o valor desserializado é igual ao original (sem perda de tipo/precisão) — achado da revisão da Story 3.19 (2026-08-30): hoje não existe nenhum teste unitário do `PolymorphicRedisSerializer` no módulo `cache`, nem para `String` simples.

## Tasks / Subtasks

- [ ] Task 1: Confirmar a vulnerabilidade atual (contexto) (AC: #1)
  - [ ] **Confirmado por leitura direta**: `PolymorphicRedisSerializer.deserialize()` (`utils/configuration/cache/PolymorphicRedisSerializer.java`, linhas 58-70) lê um `Payload(String type, JsonNode value)` do Redis e faz `Class<?> clazz = Class.forName(payload.type())` (linha 64) **sem nenhuma validação do nome da classe antes de resolvê-la** — qualquer string de nome de classe presente no Redis é resolvida e usada para desserialização polimórfica via `mapper.treeToValue(payload.value(), clazz)`. Se um atacante conseguir escrever no Redis usado por esta aplicação (ex.: Redis compartilhado, credencial vazada, ou mesmo um bug de outro consumidor gravando dados não confiáveis na mesma instância), pode forçar a desserialização de qualquer classe presente no classpath, incluindo classes com efeitos colaterais perigosos na construção/desserialização (gadget chains) — este é o achado de segurança citado no FR32
- [ ] Task 2: Implementar a allowlist (AC: #1)
  - [ ] Adicionar uma allowlist de tipos permitidos (via `Set<String>`/`Set<Class<?>>` configurável, ou por convenção de pacote — ex.: só permitir classes sob `br.com.sawcunhaos.foundation.*` mais os tipos conhecidos usados pelo módulo, como `IdempotentResponseWrapper`/`IdempotentRequestResponseWrapper`) verificada **antes** de `Class.forName(payload.type())` ser chamado
  - [ ] Se `payload.type()` não estiver na allowlist, `deserialize()` deve lançar `SerializationException` (mesmo tipo de exceção já usado pela classe no `catch` genérico) de forma explícita, sem tentar resolver a classe
  - [ ] A allowlist deve ser extensível pelo consumidor (este serializer é usado por qualquer módulo que precise cache Redis polimórfico, não só `jdempotent`) — permitir configuração da allowlist no construtor, mantendo um conjunto default razoável para não quebrar o uso atual sem configuração explícita
- [ ] Task 3: Testes (AC: #1)
  - [ ] Teste: payload com `type` de uma classe permitida → desserializa normalmente (sem regressão)
  - [ ] Teste: payload com `type` de uma classe fora da allowlist (ex.: uma classe arbitrária do JDK não relacionada ao domínio) → `deserialize()` rejeita com `SerializationException`, sem chamar `Class.forName` para o tipo não permitido
  - [ ] Teste: payload com `type` malformado/inexistente → comportamento de erro claro, sem vazar detalhes internos desnecessários na exceção
- [ ] Task 4: Cobertura de round-trip por tipo de valor (AC: #2) — achado da revisão da Story 3.19 (2026-08-30): módulo `cache` não tem nenhum teste unitário do `PolymorphicRedisSerializer` hoje
  - [ ] `String` simples e objeto customizado simples (baseline, garante que a Task 3 não regrediu o caminho feliz)
  - [ ] `BigDecimal`, `LocalDate`/`LocalDateTime`/`Instant`, `enum`, `UUID` — tipos "simples" fora de `CharSequence`/`Boolean`/`Number` que o `IdempotentAspect.isTypePrimitive` (jdempotent) não reconhece como primitivo; confirmar que o serializer em si lida bem com eles como campo de um objeto cacheado
  - [ ] Array (`int[]`, `String[]`) e `Map`
  - [ ] Coleção genericamente parametrizada (`List<T>` de objeto customizado) — risco concreto já identificado: `mapper.treeToValue(tree, clazz)` sem `TypeReference` pode perder o tipo genérico em runtime; teste deve provar que os elementos desserializados são da classe concreta esperada, não `LinkedHashMap`/tipo bruto
  - [ ] `Optional<T>` como campo
  - [ ] Objeto aninhado (campo customizado dentro de outro objeto customizado)
  - [ ] `null` como valor de resposta cacheada inteira (não só campo `null`) e `void`/`ResponseEntity<T>` se aplicável ao formato armazenado pelo `jdempotent`
  - [ ] Documentar (via teste ou nota, decisão do Dev) o comportamento com objeto muito grande e com referência circular — não necessariamente corrigir, só confirmar comportamento (falha clara vs. hang vs. `StackOverflowError`)

## Dev Notes

- `PolymorphicRedisSerializer` já migrou para o módulo `cache` na Epic 1 (Story 1.10) — confirmado pela revisão da Story 3.19 (2026-08-30): `cache/src/main/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializer.java`. O path `utils/...` desta nota estava desatualizado.
- Este é o único uso de `Class.forName` sobre dado vindo de fonte externa (Redis) encontrado no módulo — não há necessidade de generalizar a allowlist para outros serializers que não existem.
- **Ponytail**: não construir um sistema de allowlist plugável/configurável via arquivo externo (YAML de allowlist, etc.) — um `Set<String>` (ou `Set<Class<?>>`) passado no construtor, com um default sensato, cobre o AC sem introduzir infraestrutura de configuração não pedida.
- **Task 4 (origem)**: durante a review da Story 3.19 (topologia Redis do `jdempotent`), uma investigação de cobertura de tipos de valor identificou que o módulo `cache` não tem NENHUM teste unitário do `PolymorphicRedisSerializer` — nem para o caminho feliz de `String` simples. Como esta story já está prevista para tocar essa classe (a allowlist), o AC #2/Task 4 junta os dois trabalhos em vez de abrir uma story separada só para cobertura de tipos.

### Project Structure Notes

- Arquivo modificado: `cache/src/main/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializer.java`.
- Arquivo de teste novo (não existe hoje): `cache/src/test/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializerTest.java`.

### References

- [Source: cache/src/main/java/br/com/sawcunhaos/foundation/cache/PolymorphicRedisSerializer.java]
- [Source: _bmad-output/planning-artifacts/epics.md#story-316-adicionar-allowlist-de-tipos-no-polymorphicredisserializer]
- [Source: _bmad-output/implementation-artifacts/3-19-topologia-redis-parametrizada-concorrencia-e-throughput.md — investigação de cobertura de tipos de valor, 2026-08-30, origem do AC #2/Task 4]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
