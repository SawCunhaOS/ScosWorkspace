---
id: SPEC-SawCunhaOS-Foundation
companions:
  - ../../planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/prd.md
  - ../../planning-artifacts/prds/prd-SawCunhaOS-Foundation-2026-08-18/addendum.md
  - ../../planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/ARCHITECTURE-SPINE.md
  - ../../planning-artifacts/architecture/architecture-SawCunhaOS-Foundation-2026-08-19/GUIA-DE-IMPLEMENTACAO.md
sources: []
---

> **Canonical contract.** Este SPEC e os arquivos em `companions:` são o contrato completo, validado por preservação, do que construir, testar e validar. O PRD companion carrega o detalhe FR-a-FR (FR-1 a FR-34, NFR-1 a NFR-7, OQ-1 a OQ-9); a spine companion carrega os invariantes de arquitetura (AD-1 a AD-5) e o grafo de dependência; o guia companion carrega o raciocínio e comandos de verificação. Consulte-os para o "como"; este SPEC é o "o quê".

# SawCunhaOS-Foundation 1.2.0

## Why

A release 1.2.0 corrige defeitos reais já identificados em produção — classificação errada de erro de autorização (403 relatado como 500) e colisão/concorrência não-atômica na idempotência — e aproveita a janela em que o versionamento ainda é SNAPSHOT e a base de consumidores é piloto/restrita para sanar a dívida estrutural que causou esses defeitos (módulo `utils` monolítico, acoplamento invertido entre `utils` e `exception`). É pain a resolver (bugs reais já catalogados) e mandato a cumprir (a janela de correção sem custo de breaking change se fecha quando a lib for adotada mais amplamente). Adicionalmente, a consolidação da arquitetura introduziu um piso de documentação obrigatório para todo o repositório, não apenas para o código tocado neste ciclo.

## Capabilities

- **CAP-1** — Confiabilidade de idempotência
  - **intent:** O módulo `jdempotent` garante aquisição de lock atômica, detecta colisão de payload sob a mesma chave, aceita `Idempotency-Key` como fonte de chave, e nunca bloqueia o negócio quando o Redis está indisponível (fail-open).
  - **success:** chamada concorrente com a mesma chave responde `409 IN_PROGRESS` (nunca `null` silencioso); mesma chave com payload divergente responde `422 PAYLOAD_MISMATCH`; indisponibilidade do Redis nunca bloqueia a requisição de negócio, e a constraint `UNIQUE` do banco segura a não-duplicidade nesse cenário.

- **CAP-2** — Correção do tratamento de erros HTTP
  - **intent:** A aplicação classifica e responde erros corretamente — negação de autorização real vira `403`, violação em parâmetro simples vira `400`, e o formato de erro é uniforme mesmo nos casos hoje tratados nativamente pelo Spring.
  - **success:** `org.springframework.security.access.AccessDeniedException` responde `403` (não mais `500` via captura errada de `java.nio.file.AccessDeniedException`); violação em `@RequestParam` responde `400` sem `IndexOutOfBoundsException`; `MethodNotImplementedException` responde `501`; todo erro, incluindo `404` de rota inexistente, sai no mesmo formato `ScosProblemDetails`.

- **CAP-3** — Decomposição modular do `utils`
  - **intent:** O módulo monolítico `utils` (71 classes, 18 pacotes) é dividido em módulos de responsabilidade única, com direção de dependência imposta mecanicamente, para que um consumidor de um utilitário simples não carregue JPA/Redis/Feign transitivamente.
  - **success:** `utils` sai do reactor Maven ao final da decomposição; o build falha (ArchUnit) se `core` importar Spring/JPA/Servlet, se um módulo `*-api` carregar lógica ou dependência de runtime além de `jakarta.validation-api`, ou se qualquer módulo além de uma aplicação consumidora depender de `web`.

- **CAP-4** — Piso de documentação obrigatório
  - **intent:** Todo módulo do repositório — inclusive `audit` e `privacy`, que este ciclo não toca funcionalmente — expõe Javadoc em API pública, comentário onde a lógica não é óbvia, diagrama de fluxo de uso em Mermaid no README, e README, antes do release da 1.2.0.
  - **success:** nenhum módulo publica sem README com diagrama Mermaid; Checkstyle falha o build para API pública sem Javadoc uma vez confirmado o gate mecânico (ver OQ-9 no PRD companion) — até lá, checagem manual bloqueia o release do mesmo jeito.

## Constraints

- Ordem de execução entre F1/F2/F3 é fixa pela tabela de Sequenciamento do PRD companion — nenhuma fase pode ser adiantada em relação à sua dependência.
- Nenhuma mudança de comportamento além do declarado durante mover/renomear — cada extração de módulo é 2 commits separados (mover vs. ajustar comportamento), build verde a cada um.
- Cobertura mínima de 80% (jacoco) nas áreas tocadas pela Fase 0 do F1; todo bug corrigido no F2 exige teste que reproduza o bug e falhe antes do fix.
- `jdempotent` nunca é a única barreira de não-duplicidade — constraint `UNIQUE` no banco é pré-requisito, não recomendação, onde a chave de idempotência é natural.
- `key` de idempotência é sempre resolvida por um único `IdempotencyKeyResolver`, nunca derivada ad-hoc por entrypoint (HTTP vs. mensageria); `ttl` do `Lease` é sempre `java.time.Duration`.
- Circuit breaker de fail-open usa `io.github.resilience4j:resilience4j-spring-boot4:2.4.0` — não `-spring-boot3` (Spring Boot real do projeto é 4.1.0) — e essa versão precisa ser fixada explicitamente no `pom.xml` do `jdempotent`, pois nenhum BOM do projeto a gerencia.
- Regras ArchUnit que citam mais de um módulo vivem no módulo de teste dedicado `archtest`, nunca duplicadas dentro de um módulo de implementação.
- Sem guia de migração formal nem aviso direto a consumidores piloto — o CHANGELOG é a única superfície de comunicação, e cada frente registra sua própria entrada no momento em que seus commits sobem.

## Non-goals

- Guia de migração formal ou aviso direto a consumidores piloto do `utils` monolítico.
- Dimensionamento de timeout/`slow-call-duration-threshold` do circuit breaker por ambiente de consumo — decisão de cada time consumidor, não deste ciclo.
- Compatibilidade retroativa de import para quem consome o `utils` monolítico hoje — a decomposição é breaking by design nesta janela SNAPSHOT.
- Portal de documentação centralizado além do README + diagrama Mermaid por módulo.
- Versionamento ou cadência de release após a 1.2.0.

## Success signal

A 1.2.0 é publicada com zero ocorrência de erro de autorização mal classificado e zero duplicidade de processamento de idempotência em operação normal (Redis disponível) em produção. Todo consumidor que só precisa de um utilitário simples (ex.: `DateUtils`) deixa de carregar JPA/Redis/Feign transitivamente. ArchUnit e Checkstyle bloqueiam localmente, antes do merge, qualquer violação de fronteira de módulo ou lacuna de documentação.
