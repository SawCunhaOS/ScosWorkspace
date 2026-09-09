# Story 3.17: Substituir construtores telescópicos por builder e documentar o princípio de design

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como consumidor configurando o módulo `jdempotent`,
Eu quero uma API fluente (builder) e um README claro sobre a garantia real,
Para não instanciar construtores longos nem confiar só no Redis como barreira.

## Acceptance Criteria

1. **Given** os construtores telescópicos atuais, **When** são substituídos por builder, **Then** a configuração do módulo passa a usar a API fluente.
2. **And** o README do módulo documenta o princípio "cache é fast-path, não garantia" e a obrigatoriedade da constraint `UNIQUE` no banco para chaves naturais.
3. **And** o README documenta a relação recomendada entre os três timeouts independentes do módulo (`ttl` do lease > `slow-call-duration-threshold` do circuit breaker > `spring.data.redis.timeout`, com margem) — dimensionamento fica a cargo do time consumidor (OQ-3 do PRD), mas a invariante de ordem relativa é registrada para evitar ambiguidade sobre quem é o dono real do lock quando um timeout expira antes do outro.

## Tasks / Subtasks

- [ ] Task 1: Confirmar os construtores telescópicos atuais (contexto) (AC: #1)
  - [ ] **Confirmado por leitura direta**: `IdempotentAspect.java` (linhas 109-153) tem **7 construtores sobrepostos** combinando `IdempotentRepository`, `ErrorConditionalCallback` e `DefaultKeyGenerator` em todas as combinações possíveis — o exemplo clássico de construtor telescópico que o AC pede para eliminar
- [ ] Task 2: Introduzir builder para `IdempotentAspect` (AC: #1)
  - [ ] Criar um builder fluente (`IdempotentAspect.builder()` ou classe `IdempotentAspectBuilder` dedicada) que substitui as 7 combinações de construtores por métodos encadeáveis (`.repository(...)`, `.errorCallback(...)`, `.keyGenerator(...)`, `.build()`), com os mesmos defaults dos construtores atuais (`InMemoryIdempotentRepository`/`DefaultKeyGenerator` quando não especificados)
  - [ ] Atualizar `ScosJdempotentConfig` (Story 3.4, já corrigida para `@ConditionalOnMissingBean`) para usar o builder em vez de invocar construtores diretamente
  - [ ] Manter os construtores antigos **obsoletos** (`@Deprecated`) em vez de removê-los imediatamente, se houver preocupação de compatibilidade com consumidores externos que já instanciam `IdempotentAspect` diretamente — decidir conforme a política de versionamento do projeto (SNAPSHOT permite quebra, conforme ADD-5); documentar a decisão nas Completion Notes
- [ ] Task 3: Documentar "cache é fast-path, não garantia" no README (AC: #2)
  - [ ] Atualizar (ou criar, se não existir) o README do módulo `jdempotent` com uma seção explícita afirmando que o Redis/cache de idempotência é um mecanismo de **fast-path para evitar reprocessamento**, não a garantia final contra duplicidade — a garantia real é a constraint `UNIQUE` do banco de dados na chave de negócio (NFR6), que deve existir **antes** de habilitar `jdempotent` para qualquer método com chave de idempotência natural
  - [ ] Referenciar explicitamente o cenário de split-brain documentado na Story 3.7 (Redis cai durante o processamento, resposta não fica cacheada, retry reexecuta) como exemplo concreto de por que a constraint `UNIQUE` é obrigatória, não opcional
- [ ] Task 4: Documentar a relação entre os três timeouts (AC: #3)
  - [ ] No README, registrar a invariante de ordem relativa: **`ttl` do lease (Story 3.5) > `slow-call-duration-threshold` do circuit breaker (Story 3.7) > `spring.data.redis.timeout`**, cada um com margem sobre o anterior
  - [ ] Explicar o raciocínio: se `spring.data.redis.timeout` for maior que o `slow-call-duration-threshold`, o circuit breaker nunca detecta lentidão antes do timeout de rede já ter estourado (perde o propósito do fail-fast); se o `ttl` do lease for menor ou igual ao `slow-call-duration-threshold` combinado com o tempo de processamento real, o lease pode expirar antes do método protegido terminar (cenário já catalogado como risco aceito na Story 3.5 AC #4) — a ordem correta minimiza (não elimina) esse risco
  - [ ] Deixar explícito que o **dimensionamento exato** de cada valor é responsabilidade do time consumidor (depende do perfil de latência de cada aplicação, OQ-3 do PRD) — o README documenta a ordem relativa obrigatória, não valores numéricos prescritivos

## Dev Notes

- Esta story é naturalmente a última do epic — o README que ela produz referencia comportamentos e riscos documentados por praticamente todas as stories anteriores (3.5 lease/TTL, 3.7 circuit breaker/split-brain, NFR6 constraint UNIQUE). Implementar por último, depois que os mecanismos que ela documenta já existirem, para não escrever documentação de um comportamento que ainda vai mudar.
- **NFR7** (Epic 4): esta story já entrega parte do piso de documentação do módulo `jdempotent` que a Story 4.13 (Epic 4) espera encontrar parcialmente pronto — a Story 4.13 completa com Javadoc de API pública e diagrama de sequência Mermaid; esta story (3.17) entrega o conteúdo textual do princípio de design e a relação de timeouts.
- **Ponytail**: o builder deve cobrir exatamente as combinações que os 7 construtores atuais cobrem — não adicionar métodos de configuração especulativos que os construtores atuais não suportam (ex.: não inventar um parâmetro novo só porque "um builder poderia ter"). Escopo do builder = paridade com os construtores existentes, não expansão.

### Project Structure Notes

- Arquivo modificado: `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (builder), `ScosJdempotentConfig.java` (uso do builder).
- Arquivo modificado/criado: README do módulo `jdempotent` (`jdempotent/README.md`, confirmar se já existe antes de criar).

### References

- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java#L109-L153]
- [Source: jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfig.java]
- [Source: _bmad-output/implementation-artifacts/3-5-tornar-a-aquisição-do-lock-atômica-tryacquire-lease.md]
- [Source: _bmad-output/implementation-artifacts/3-7-garantir-fail-open-com-circuit-breaker-quando-o-redis-está-i.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-317-substituir-construtores-telescópicos-por-builder-e-documentar-o-princípio-de-design]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
