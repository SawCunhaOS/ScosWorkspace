# Story 2.8: Mover o contrato de domínio do `exception` para o `core`

Status: done

<!-- baseline_commit: 1d2b8f60875704709f3cb5b3af9a0a4848c05698 -->

<!-- Correção pré-implementação (substancial): das 8 classes que a Task 1 pede para mover, 4 JÁ ESTÃO em `core` desde o Épico 1 (Stories 1.7/1.9) — `ScosException` (`core/.../exception/ScosException.java`), `ExceptionCode` (`core/.../specification/ExceptionCode.java`), `ScosExceptionCode` (`core/.../enums/ScosExceptionCode.java`), `LocaleService` (`core/.../specification/LocaleService.java`) — confirmado via `find`, e usadas extensivamente por todas as Stories 2.1-2.7 deste próprio épico. O módulo `utils` (origem que a story cita para essas 4) não existe mais — removido na Story 1.14 do Épico 1. A story parece ter sido escrita contra um inventário desatualizado, anterior à conclusão do Épico 1. **Escopo real restante desta story**: mover só as OUTRAS 4 classes, que de fato ainda estão em `exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/`: `ScosNoContentException`, `ScosNoRollbackException`, `ScosSecurityException`, `MethodNotImplementedException` — confirmadas Spring-free (nenhuma importa `org.springframework.*`/`jakarta.persistence.*`/`jakarta.servlet.*`). Referenciadas hoje só dentro do próprio módulo `exception` (`ExceptionsHandler.java` + 3 arquivos de teste) — confirmado via grep em todo o reactor, nenhum outro módulo as importa.

Quanto à Task 2 (repontar `audit`): `InsideAuditExampleService.java` já importa `br.com.sawcunhaos.foundation.core.exception.ScosException` (não `utils.exception.ScosException` como a story descreve) — já correto, nada a corrigir aí. Porém `audit/pom.xml` não tem dependência EXPLÍCITA em `scos-foundation-core` (só chega transitivamente via `scos-foundation-exception`/`scos-foundation-jpa`) — isso ainda precisa ser adicionado, pois a Story 2.9 vai esvaziar `exception` do reactor, quebrando esse caminho transitivo. Confirmado via grep que `audit/src` (main+test) não referencia NADA de `br.com.sawcunhaos.foundation.exception.*` diretamente — a dependência Maven `scos-foundation-exception` em `audit/pom.xml` já pode ser removida nesta própria story (não precisa esperar a 2.9), conforme a própria Task 2 antecipa como possibilidade.

Task 3 (regra ArchUnit zero-Spring em `core`): confirmado que `core/src/test/java/br/com/sawcunhaos/foundation/core/ArchitectureTest.java` já existe (`@AnalyzeClasses(packages = "br.com.sawcunhaos.foundation.core")`, proíbe `org.springframework..`/`jakarta.persistence..`/`jakarta.servlet..`) — cobre automaticamente qualquer pacote novo dentro de `core`, incluindo onde as 4 classes movidas caírem. Não precisa de regra nova, só confirmar que continua passando (`mvn -pl core -am test`) depois da Task 1. -->

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor do `scos-foundation`,
Eu quero que exceções de domínio não dependam de Spring,
Para que `core` continue sem essa dependência.

## Acceptance Criteria

1. **Given** `ScosException`, `ExceptionCode`, `ScosExceptionCode`, `LocaleService`, `ScosNoContentException`, `ScosNoRollbackException`, `ScosSecurityException`, `MethodNotImplementedException` já corrigidos nas stories anteriores, **When** essas classes são movidas para o módulo `core` (criado no Epic 1), **Then** `core` continua compilando sem `org.springframework` no classpath.
2. **And** o módulo `audit` é repontado para consumir `ScosException` do `core` em vez do `exception` antigo.
3. **And** a extração ocorre em commit de "mover", separado de qualquer ajuste de comportamento.

## Tasks / Subtasks

- [x] Task 1: Mover as 8 classes de domínio para `core` (AC: #1)
  - [x] Origem real confirmada de cada uma — ver comentário de correção pré-implementação: 4 já estavam em `core` desde o Épico 1; só as outras 4 (`ScosNoContentException`, `ScosNoRollbackException`, `ScosSecurityException`, `MethodNotImplementedException`) precisavam mover, e vinham de `exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/`
  - [x] As 4 classes movidas para `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/` (mesmo subpacote de `ScosException`, ao qual 3 delas já estendem — sem subpacote genérico `util`/`common`, conforme ADD-5)
  - [x] Confirmado (`diff` old vs. new ignorando a linha `package`): as 4 são movimentações puras — só a linha de pacote mudou, e o import (agora redundante, mesmo pacote) de `ScosException` foi removido em 3 delas; `MethodNotImplementedException` ficou byte-idêntica exceto o pacote. Nenhuma importa `org.springframework.*`/`jakarta.persistence.*`/`jakarta.servlet.*`
- [x] Task 2: Repontar `audit` para consumir do `core` (AC: #2)
  - [x] `audit/pom.xml`: dependência explícita em `scos-foundation-core` adicionada
  - [x] `InsideAuditExampleService.java` já importava `core.exception.ScosException` corretamente — nada a mudar aí (confirmado no comentário de correção pré-implementação)
  - [x] Confirmado que `audit/src` (main+test) não referencia nada de `br.com.sawcunhaos.foundation.exception.*` diretamente — dependência `scos-foundation-exception` removida de `audit/pom.xml` nesta própria story, sem esperar a 2.9. **Ressalva descoberta na revisão**: essa remoção quebrou a criação do bean `ObjectMapper`/`JsonMapper` (usado por `ScosAuditBatchConsumer`/`-DlqJob`/`-ServiceBean`), que `audit` recebia como efeito colateral do `spring-boot-starter-web` transitivo de `scos-foundation-exception` — ver Completion Notes para a correção
- [x] Task 3: Confirmar regra ArchUnit de zero-Spring em `core` (AC: #1)
  - [x] `core/src/test/java/br/com/sawcunhaos/foundation/core/ArchitectureTest.java` (já existente, cobertura ampla do pacote `br.com.sawcunhaos.foundation.core`) continua passando após a Task 1 — nenhuma regra nova criada
- [x] Task 4: Commit de mover separado (AC: #3)
  - [x] Commit único, mecânico: só as 4 movimentações de arquivo + os imports que as referenciam + as 2 mudanças de dependência do `audit/pom.xml` (mecânicas, decorrentes diretamente do mover) — nenhuma lógica de negócio tocada

## Dev Notes

- Esta story só pode rodar **depois** que `ScosException`/`ScosNoRollbackException`/`ScosExceptionCode`/`LocaleService` já estiverem com as correções das Stories 2.3 (novo `ScosExceptionCode.NOT_IMPLEMENTED`) e 2.6 (`LocaleService.getMessageOrDefault`) aplicadas — mover primeiro e corrigir depois duplicaria trabalho entre dois commits de módulos diferentes.
- **Confirmado**: as 8 classes já vivem sem dependência de Spring hoje (verificado nas stories 2.1–2.6) — esta story é puramente uma movimentação de pacote/módulo, não uma reescrita.
- `MethodNotImplementedException` muda de módulo mas não de forma (`RuntimeException` simples, sem `ExceptionCode`) — a decisão de integrá-la ou não ao padrão `ScosException` continua fora do escopo (mesma nota da Story 2.3).
- `ExceptionCode` é uma interface (`PROBLEM_TYPE_BASE_URI`, `getCode()`, `getType()` default, `getTitle()` default, `getHttpCode()` default) — mover junto com `ScosExceptionCode` (a única implementação hoje no repo) evita separar contrato e implementação entre módulos.

### Project Structure Notes

- Módulo `core` (Epic 1, Story 1.7) ganha 8 novas classes: `ScosException`, `ExceptionCode`, `ScosExceptionCode`, `LocaleService`, `ScosNoContentException`, `ScosNoRollbackException`, `ScosSecurityException`, `MethodNotImplementedException`.
- `utils` perde 4 classes (`ScosException`, `ExceptionCode`, `ScosExceptionCode`, `LocaleService`).
- `exception` perde 4 classes (`ScosNoContentException`, `ScosNoRollbackException`, `ScosSecurityException`, `MethodNotImplementedException`) — depois da Story 2.9 (que move o restante), o módulo `exception` fica vazio e sai do reactor.
- `audit/pom.xml` ganha dependência em `scos-foundation-core`.

### References

- [Source: utils/src/main/java/br/com/sawcunhaos/foundation/utils/exception/ScosException.java]
- [Source: utils/src/main/java/br/com/sawcunhaos/foundation/utils/specification/ExceptionCode.java]
- [Source: utils/src/main/java/br/com/sawcunhaos/foundation/utils/enums/ScosExceptionCode.java]
- [Source: utils/src/main/java/br/com/sawcunhaos/foundation/utils/specification/LocaleService.java]
- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/ScosNoContentException.java]
- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/ScosNoRollbackException.java]
- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/ScosSecurityException.java]
- [Source: exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/MethodNotImplementedException.java]
- [Source: audit/src/test/java/br/com/sawcunhaos/foundation/audit/service/InsideAuditExampleService.java]
- [Source: audit/pom.xml]
- [Source: _bmad-output/implementation-artifacts/1-7-extrair-o-módulo-core.md]
- [Source: _bmad-output/planning-artifacts/epics.md#story-28-mover-o-contrato-de-domínio-do-exception-para-o-core]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- `diff` (old `exception/.../error/*.java` vs. novo `core/.../exception/*.java`, ignorando a linha `package`) — confirmou movimentação limpa: `MethodNotImplementedException` byte-idêntica; as outras 3 só perderam o import (agora redundante) de `ScosException`, sem nenhuma outra mudança.
- `mvn -o -pl core,exception,audit -am -DskipITs test` (1ª rodada, antes da correção) → `BUILD FAILURE` em `audit`: as 13 classes de teste `@SpringBootTest` do módulo falharam com `NoSuchBeanDefinitionException: No qualifying bean of type 'tools.jackson.databind.ObjectMapper'`, propagado como `UnsatisfiedDependencyException` na criação de `ScosAuditBatchConsumer`. Causa raiz: remover `scos-foundation-exception` de `audit/pom.xml` também removeu o caminho transitivo até `spring-boot-starter-web`, que é quem de fato monta o bean `ObjectMapper`/`JsonMapper` a partir dos customizers do Jackson. A correção original do subagente (trocar por `spring-boot-starter-jackson`) não resolveu — confirmado lendo o fonte de `org.springframework.boot.jackson.autoconfigure.JacksonAutoConfiguration` (jar `-sources`, Spring Boot 4.1.1): essa classe só expõe beans de `JsonFactory`/mixin/customizer, nenhum `@Bean ObjectMapper`/`JsonMapper`.
- Corrigido: `audit/pom.xml` trocado de `spring-boot-starter-jackson` para `spring-boot-starter-web` (mesma dependência efetiva que `audit` já tinha transitivamente antes desta story, agora explícita).
- `mvn -o -pl audit -am -DskipITs test` (pós-correção) → `BUILD SUCCESS`, `Tests run: 56, Failures: 0, Errors: 0, Skipped: 0` — mesmo baseline confirmado em stories anteriores desta sessão.
- `mvn -o -pl core,exception,audit -am -DskipITs test` (rodada final, combinada) → `BUILD SUCCESS`. Contagens por módulo (via soma dos relatórios surefire em disco): `core` 26 testes, `exception` 41 testes, `audit` 56 testes — `0` falhas/erros em todos.

### Completion Notes List

- **Task 1**: as 4 classes que de fato precisavam mover (`ScosNoContentException`, `ScosNoRollbackException`, `ScosSecurityException`, `MethodNotImplementedException`) foram movidas de `exception/.../error/` para `core/.../exception/` — mesmo subpacote de `ScosException`, ao qual 3 delas já estendiam. As outras 4 citadas pela story (`ScosException`, `ExceptionCode`, `ScosExceptionCode`, `LocaleService`) já estavam em `core` desde o Épico 1 — confirmado no comentário de correção pré-implementação, nenhuma ação necessária.
- Referências atualizadas nos 4 arquivos que importavam as classes movidas pelo caminho antigo: `ExceptionsHandler.java`, `ExceptionsHandlerLogLevelTest.java`, `ExceptionsHandlerMethodNotImplementedTest.java`, `ExceptionsHandlerResolveTitleTest.java` — todos dentro do próprio módulo `exception`, confirmado via grep que nenhum outro módulo referenciava essas 4 classes pelo pacote antigo.
- **Task 2**: `audit/pom.xml` ganhou dependência explícita em `scos-foundation-core` e perdeu `scos-foundation-exception` (confirmado sem uso de nada em `br.com.sawcunhaos.foundation.exception.*` dentro de `audit/src`). **Achado real na revisão, não coberto pela story**: remover `scos-foundation-exception` também removeu, como efeito colateral, o caminho transitivo até um bean `ObjectMapper`/`JsonMapper` funcional, que `ScosAuditBatchConsumer`/`-DlqJob`/`-ServiceBean` precisam via `@Autowired`. A tentativa inicial de resolver isso com `spring-boot-starter-jackson` (Spring Boot 4.1.1) não funciona — essa starter não expõe um bean `ObjectMapper`/`JsonMapper`, só `JsonFactory`/customizers; quem de fato monta o mapper é a autoconfiguração de conversores HTTP do `spring-boot-starter-web`. Corrigido trocando para `spring-boot-starter-web` — dependência efetiva idêntica à que `audit` já tinha antes desta story (só deixou de ser transitiva via `exception`), não é escopo novo.
- **Task 3**: `core/src/test/java/br/com/sawcunhaos/foundation/core/ArchitectureTest.java` já cobria `br.com.sawcunhaos.foundation.core` de forma ampla — nenhuma regra nova necessária, só confirmado que continua passando.
- **Task 4**: mudança estruturada como um único commit mecânico de "mover" — nenhuma linha de lógica de negócio alterada nas 4 classes movidas; as mudanças em `audit/pom.xml` (incluindo a correção do `ObjectMapper`) são consequência direta e mecânica do mover, não uma mudança de comportamento independente.

### File List

- `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/MethodNotImplementedException.java` (novo, movido de `exception`)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/ScosNoContentException.java` (novo, movido de `exception`)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/ScosNoRollbackException.java` (novo, movido de `exception`)
- `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/ScosSecurityException.java` (novo, movido de `exception`)
- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/MethodNotImplementedException.java` (removido)
- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/ScosNoContentException.java` (removido)
- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/ScosNoRollbackException.java` (removido)
- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/error/ScosSecurityException.java` (removido)
- `exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java` (modificado — imports atualizados)
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerLogLevelTest.java` (modificado — imports atualizados)
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerMethodNotImplementedTest.java` (modificado — imports atualizados)
- `exception/src/test/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandlerResolveTitleTest.java` (modificado — imports atualizados)
- `audit/pom.xml` (modificado — `scos-foundation-exception` removido, `scos-foundation-core` + `spring-boot-starter-web` adicionados; comentário corrigido na revisão)

### Revisão de 3 camadas

Achados triados (blind-hunter, edge-case-hunter, verification-gap):

- **Patch**: o comentário novo em `audit/pom.xml` para a dependência `scos-foundation-core` dizia "previously only reached transitively via scos-foundation-exception/-jpa", mas `jpa` já depende de `core` diretamente (confirmado lendo `jpa/pom.xml`) — o caminho transitivo nunca esteve de fato quebrado só por causa da remoção de `scos-foundation-exception`. Comentário reescrito para deixar claro que o valor da dependência explícita é robustez (não depender implicitamente de um caminho transitivo que poderia mudar), não uma correção de algo que estava quebrado. Confirmado por blind-hunter.
- **Patch**: nenhum comentário explicava por que as 4 classes agora vivem em `core.exception`, o que a própria Story 2.9 (que esvazia o resto do módulo `exception`) vai precisar. Adicionado um comentário de uma linha em cada uma das 4 classes movidas, apontando para esta story. Confirmado por blind-hunter.
- **Rejeitado com evidência**: edge-case-hunter apontou risco de `audit` ainda referenciar outras classes de `scos-foundation-exception` além das 4 movidas, e de `ScosSecurityException` ter algum import não atualizado. Ambos verificados diretamente contra o repositório: `grep` em `audit/src` (main+test) por `br.com.sawcunhaos.foundation.exception.` não retorna nada, e a suíte completa (`core`+`exception`+`audit`) passa; `ScosSecurityException` não é referenciada em NENHUM outro arquivo do reactor além da sua própria declaração — nunca precisou de nenhum import atualizado, antes ou depois do mover.
- **Rejeitado com evidência**: blind-hunter apontou que adicionar `spring-boot-starter-web` a `audit/pom.xml` traz Tomcat/MVC completo a um módulo de biblioteca só para obter um bean `ObjectMapper`, sugerindo uma alternativa mais leve (um `@Bean ObjectMapper`/`JsonMapper` local, ou `jackson-databind` puro). Avaliado e rejeitado: `audit` já tinha exatamente essa mesma pegada de dependência de forma transitiva antes desta story (via `scos-foundation-exception`) — não é um risco novo, só deixou de ser transitivo. Mais importante: `audit` processa serialização de payloads de auditoria/hash-chain (área sensível a segurança/compliance) — trocar para um `ObjectMapper` montado manualmente arrisca uma diferença real de comportamento de serialização em relação ao que a autoconfiguração completa do Boot produzia, violando a AC #3 desta story (mover sem mudar comportamento). Manter o mesmo mecanismo de autoconfiguração (só explícito em vez de transitivo) garante comportamento idêntico, que é a escolha mais segura para uma story de "mover".
- **Rejeitado com evidência**: blind-hunter perguntou se o mover foi feito com `git mv` (preservando histórico) em vez de delete+add. A detecção de rename do Git é baseada em similaridade de conteúdo, não no comando usado — como o conteúdo dos 4 arquivos é idêntico ou quase idêntico (só a linha de pacote/um import mudou), o Git detecta automaticamente como rename ao rodar `git add`/`git commit`/`git log`, independente de `git mv` ter sido usado.
- **Rejeitado com evidência**: blind-hunter questionou se mover exceções com nomenclatura HTTP-adjacente (`ScosNoContentException`, `ScosSecurityException`) para `core.exception` borra a fronteira que motivou separar `exception` de `core`. Essa é exatamente a decisão de design que a própria story pede e justifica (Story/AC: "exceções de domínio não dependam de Spring... core continue sem essa dependência"; Dev Notes confirmam que as 8 classes são POJOs puros) — não é uma omissão, é o propósito declarado da story.
- **Rejeitado com evidência**: blind-hunter apontou que `scos-foundation-exception` continua declarada em `archtest/pom.xml`, sem uso direto de classes de `br.com.sawcunhaos.foundation.exception.*` em `archtest/src` (confirmado via grep). Verificado que o propósito é diferente do de `audit`: `archtest` roda regras ArchUnit de escaneamento amplo de classpath entre módulos — precisa de `exception` no classpath para a análise arquitetural funcionar, mesmo sem nenhuma linha de código Java importando uma classe específica. Não é paralelo à situação de `audit` (que usava classes concretas via import direto).
- **Adiado para `deferred-work.md`**: `ScosSecurityException` não é referenciada em nenhum lugar do reactor além da sua própria declaração — código morto movido, não introduzido, por esta story. Decisão sobre removê-la (ou não) fica fora do escopo de uma story de "mover". Encontrado pelo Blind Hunter.
- **Adiado para `deferred-work.md`**: nenhuma das 4 classes movidas tem teste unitário dedicado — `ScosSecurityException` em particular tem cobertura zero antes e depois do mover (consequência direta de ser código morto, achado acima). Encontrado pelo Blind Hunter.
- **Adiado para `deferred-work.md`**: a superfície de construtores é inconsistente entre as 4 classes (`MethodNotImplementedException` tem 5 sobrecargas incluindo uma `protected`; as outras têm 1-2) e `ScosSecurityException` tem 2 construtores que não delegam um ao outro (duplicação) — pré-existente, confirmado inalterado pelo `diff` old-vs-new. Encontrado pelo Blind Hunter.
- **Adiado para `deferred-work.md`**: indentação inconsistente entre as 4 classes (`ScosNoRollbackException`/`ScosSecurityException` usam tabs, `MethodNotImplementedException`/`ScosNoContentException` usam 4 espaços) — pré-existente, confirmado inalterado pelo `diff` old-vs-new; a Task 4 desta story exige "sem tocar em uma linha de lógica", então corrigir formatação também ficaria fora do escopo de um commit de mover puro. Encontrado pelo Blind Hunter.

## Suggested Review Order

**O achado real desta revisão (não coberto pela story original)**

- `audit/pom.xml`: remover `scos-foundation-exception` derrubou silenciosamente o bean `ObjectMapper`/`JsonMapper` que `ScosAuditBatchConsumer`/`-DlqJob`/`-ServiceBean` precisam (chegava como efeito colateral do `spring-boot-starter-web` transitivo). As 13 classes de teste `@SpringBootTest` de `audit` falharam na primeira rodada de verificação; corrigido trocando por `spring-boot-starter-web` explícito — mesma pegada de dependência que `audit` já tinha antes, agora explícita.
  [`audit/pom.xml`](../../audit/pom.xml)

**O mover em si (as 4 classes)**

- `core/src/main/java/br/com/sawcunhaos/foundation/core/exception/` — `ScosNoContentException`, `ScosNoRollbackException`, `ScosSecurityException`, `MethodNotImplementedException`, movidas de `exception/.../error/`. Movimentação limpa, confirmada via `diff` old-vs-new (só a linha de pacote + um import redundante mudaram).
  [`core/.../exception/`](../../core/src/main/java/br/com/sawcunhaos/foundation/core/exception/)

- Imports atualizados em `ExceptionsHandler.java` e nos 3 testes que o exercitam.
  [`ExceptionsHandler.java`](../../exception/src/main/java/br/com/sawcunhaos/foundation/exception/ExceptionsHandler.java)
