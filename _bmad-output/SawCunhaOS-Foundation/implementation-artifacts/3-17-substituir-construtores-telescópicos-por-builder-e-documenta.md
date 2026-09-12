# Story 3.17: Substituir construtores telescópicos por builder e documentar o princípio de design

Status: review

<!-- baseline_commit: 2b809871658516f8063abb0a6b9ed33aa6555312 -->

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

- [x] Task 1: Confirmar os construtores telescópicos atuais (contexto) (AC: #1)
  - [x] **Confirmado por leitura direta**: `IdempotentAspect.java` (linhas 109-153) tem **7 construtores sobrepostos** combinando `IdempotentRepository`, `ErrorConditionalCallback` e `DefaultKeyGenerator` em todas as combinações possíveis — o exemplo clássico de construtor telescópico que o AC pede para eliminar
- [x] Task 2: Introduzir builder para `IdempotentAspect` (AC: #1)
  - [x] Criar um builder fluente (`IdempotentAspect.builder()` ou classe `IdempotentAspectBuilder` dedicada) que substitui as 7 combinações de construtores por métodos encadeáveis (`.repository(...)`, `.errorCallback(...)`, `.keyGenerator(...)`, `.build()`), com os mesmos defaults dos construtores atuais (`InMemoryIdempotentRepository`/`DefaultKeyGenerator` quando não especificados)
  - [x] Atualizar `ScosJdempotentConfig` (Story 3.4, já corrigida para `@ConditionalOnMissingBean`) para usar o builder em vez de invocar construtores diretamente
  - [x] Manter os construtores antigos **obsoletos** (`@Deprecated`) em vez de removê-los imediatamente, se houver preocupação de compatibilidade com consumidores externos que já instanciam `IdempotentAspect` diretamente — decidir conforme a política de versionamento do projeto (SNAPSHOT permite quebra, conforme ADD-5); documentar a decisão nas Completion Notes. **Decisão: removidos, não depreciados** — sem consumidor externo encontrado e ADD-5/PRD já elegem não manter agregador de transição neste ciclo; ver Completion Notes.
- [x] Task 3: Documentar "cache é fast-path, não garantia" no README (AC: #2)
  - [x] Atualizar (ou criar, se não existir) o README do módulo `jdempotent` com uma seção explícita afirmando que o Redis/cache de idempotência é um mecanismo de **fast-path para evitar reprocessamento**, não a garantia final contra duplicidade — a garantia real é a constraint `UNIQUE` do banco de dados na chave de negócio (NFR6), que deve existir **antes** de habilitar `jdempotent` para qualquer método com chave de idempotência natural
  - [x] Referenciar explicitamente o cenário de split-brain documentado na Story 3.7 (Redis cai durante o processamento, resposta não fica cacheada, retry reexecuta) como exemplo concreto de por que a constraint `UNIQUE` é obrigatória, não opcional
- [x] Task 4: Documentar a relação entre os três timeouts (AC: #3)
  - [x] No README, registrar a invariante de ordem relativa: **`ttl` do lease (Story 3.5) > `slow-call-duration-threshold` do circuit breaker (Story 3.7) > `spring.data.redis.timeout`**, cada um com margem sobre o anterior
  - [x] Explicar o raciocínio: se `spring.data.redis.timeout` for maior que o `slow-call-duration-threshold`, o circuit breaker nunca detecta lentidão antes do timeout de rede já ter estourado (perde o propósito do fail-fast); se o `ttl` do lease for menor ou igual ao `slow-call-duration-threshold` combinado com o tempo de processamento real, o lease pode expirar antes do método protegido terminar (cenário já catalogado como risco aceito na Story 3.5 AC #4) — a ordem correta minimiza (não elimina) esse risco
  - [x] Deixar explícito que o **dimensionamento exato** de cada valor é responsabilidade do time consumidor (depende do perfil de latência de cada aplicação, OQ-3 do PRD) — o README documenta a ordem relativa obrigatória, não valores numéricos prescritivos

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
- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/3-5-tornar-a-aquisição-do-lock-atômica-tryacquire-lease.md]
- [Source: _bmad-output/SawCunhaOS-Foundation/implementation-artifacts/3-7-garantir-fail-open-com-circuit-breaker-quando-o-redis-está-i.md]
- [Source: _bmad-output/SawCunhaOS-Foundation/planning-artifacts/epics.md#story-317-substituir-construtores-telescópicos-por-builder-e-documentar-o-princípio-de-design]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `mvn -pl jdempotent -am compile test-compile`: clean, no errors.
- `mvn -pl jdempotent -am test`: 125 unit tests, 1 pre-existing failure unrelated to this story
  (`InMemoryIdempotentRepositoryTtlTest#given_setResponse_repeatedly_refreshes_the_ttl_while_contains_races_the_expiry_check_then_the_entry_is_never_incorrectly_evicted`,
  a timing-sensitive TTL-race test from Story 3.15's area). Confirmed pre-existing by stashing this
  story's changes and re-running the same test in isolation: it fails identically on the unmodified
  baseline. Not touched by this story (out of the File List) and not re-run under `verify`
  (Testcontainers) since Dev Notes scope this story's verification to the module's own build.

### Completion Notes List

- **Construtores telescópicos removidos, não depreciados (Task 2, 3ª bullet)**: decisão tomada —
  os 7 construtores de `IdempotentAspect` foram **removidos** (não mantidos `@Deprecated`) e
  substituídos por um único construtor privado usado só pelo novo `IdempotentAspect.Builder`.
  Razões, na política de versionamento do projeto: (1) ADD-5 permite quebra explicitamente em
  módulos `SNAPSHOT` (este módulo está em `1.2.0-SNAPSHOT`); (2) a seção "Comunicação e Migração"
  do PRD já declara, para este mesmo ciclo, que "compatibilidade com consumidores não é restrição
  neste ciclo", elegendo de propósito não manter agregador de transição/depreciação — mesmo
  precedente já aplicado nesta story a `EnvironmentVariableUtils`/`ConfigUtility` (ver CHANGELOG);
  (3) busca completa por `new IdempotentAspect(` no repositório e no repo irmão `SawCunhaOS-Flow`
  não encontrou nenhum consumidor externo instanciando a classe diretamente — só
  `ScosJdempotentConfig` (interno) e testes deste próprio módulo; (4) manter as 7 sobrecargas
  paralelas ao builder reintroduziria exatamente a superfície telescópica que o AC pede para
  eliminar, sem ganho real de compatibilidade. Todos os 7 call sites afetados (1 em
  `ScosJdempotentConfig`, 6 em testes) foram migrados para `IdempotentAspect.builder()...build()`
  neste mesmo commit — ver File List. Registrado também como entrada `**BREAKING**` no
  `CHANGELOG.md`.
- **Builder — escopo congelado (Ponytail, Dev Notes)**: `IdempotentAspect.Builder` expõe só
  `.repository(IdempotentRepository)`, `.errorCallback(ErrorConditionalCallback)`,
  `.keyGenerator(DefaultKeyGenerator)` e `.build()` — exatamente os três parâmetros que os 7
  construtores antigos combinavam, com os mesmos defaults (`InMemoryIdempotentRepository`/
  `DefaultKeyGenerator` quando não chamados, nenhum error callback por padrão). Nenhuma opção nova
  foi adicionada.
- **`IdempotentAspectUTTest` não precisou de nenhuma mudança**: o teste usa
  `@InjectMocks private IdempotentAspect idempotentAspect;` com mocks de
  `IdempotentRepository`/`DefaultKeyGenerator`/`ErrorConditionalCallback` — a estratégia de
  injeção por construtor do Mockito já escolhia o construtor de 3 argumentos (o "maior" entre os 7
  antigos); com um único construtor privado de 3 argumentos, o comportamento observado é idêntico
  (Mockito torna construtores privados acessíveis via reflection). Confirmado rodando a suíte
  completa do módulo.
- **README novo do módulo** (`jdempotent/README.md` não existia antes desta story): criado com
  4 seções — "Como configurar" (aponta para o builder, já que não há mais construtores públicos),
  "Cache é fast-path, não garantia" (AC #2, referencia o split-brain da Story 3.7 e a constraint
  `UNIQUE`/NFR6), e "Relação entre os três timeouts" (AC #3, invariante de ordem relativa com o
  raciocínio de cada lado, e a ressalva de que o dimensionamento numérico é do time consumidor,
  OQ-3 do PRD). Terminologia (NFR6, OQ-3) conferida contra o PRD (`prd.md`) para não parafrasear
  errado.
- **Falha pré-existente não corrigida**: `InMemoryIdempotentRepositoryTtlTest` tem um teste de
  concorrência (TTL) que falha de forma consistente também na baseline sem esta story (confirmado
  via `git stash`) — fora do File List desta story (não mexe em `IdempotentAspect`/builder/README),
  não corrigido aqui; sinalizado para quem tocar `InMemoryIdempotentRepository`/Story 3.15 em
  seguida.

### File List

- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspect.java` (modificado) — 7 construtores telescópicos removidos; construtor privado único + `Builder`/`builder()` novos.
- `jdempotent/src/main/java/br/com/sawcunhaos/foundation/jdempotent/redis/configuration/ScosJdempotentConfig.java` (modificado) — os 2 pontos de construção de `IdempotentAspect` usam o builder.
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/TestAopContext.java` (modificado) — usa o builder.
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/TestAopTransactionalContext.java` (modificado) — usa o builder.
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/aspect/IdempotentAspectTest.java` (modificado) — usa o builder.
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/callback/TestAopWithErrorCallbackContext.java` (modificado) — usa o builder.
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolverTest.java` (modificado) — usa o builder.
- `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/core/generator/IdempotencyKeyResolverHeaderSourceTest.java` (modificado) — usa o builder.
- `jdempotent/README.md` (novo) — princípio "cache é fast-path, não garantia" (AC #2) e relação entre os três timeouts (AC #3).
- `CHANGELOG.md` (modificado) — nova entrada `**BREAKING**` sob a seção `scos-foundation-jdempotent` documentando a remoção dos construtores telescópicos.
