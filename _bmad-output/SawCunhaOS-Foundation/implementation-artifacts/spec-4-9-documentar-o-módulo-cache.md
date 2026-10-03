---
title: 'Documentar o módulo cache'
type: 'chore'
created: '2026-10-02'
status: 'done'
route: 'oneshot'
baseline_revision: '228ab40282886e41da030e5ccbbd4d292c05a4f4'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/4-9-documentar-o-módulo-cache.md']
---

<intent-contract>

## Intent

**Problem:** O módulo `cache` (Story 1.10, `done`; a nota "ainda não existe" da story está desatualizada) tem 5 classes sem Javadoc de API, o Javadoc da allowlist (Story 3.16, já implementada) está pendurado numa constante privada em vez da classe, e não há README nem diagrama.

**Approach:** Javadoc nas classes/métodos públicos, comentários inline onde a lógica não é óbvia e `cache/README.md` com diagrama Mermaid. Só documentação: nenhum comportamento, assinatura ou nome é alterado.

## Boundaries & Constraints

**Always:** documentar o contrato real, inclusive o contrato de segurança da allowlist (`br.com.sawcunhaos.`, `java.math./time./util.`, `java.lang.String`, arrays, extras via construtor) e as lacunas reais (propriedades declaradas mas não usadas).
**Never:** alterar código, assinaturas, `pom.xml` ou o índice do README raiz.

</intent-contract>

## Code Map

- `cache/src/main/java/.../cache/PolymorphicRedisSerializer.java` -- allowlist (3.16), `Payload`, `elementType`
- `.../cache/ScosCacheConfiguration.java` -- topologia, `CacheManager` com fallback `NoOpCacheManager`, `CacheErrorHandler`
- `.../cache/ScosCacheKeyGenerator.java` -- `Classe::método::params`, filtro de sensíveis
- `.../cache/properties/ScosCacheProperties.java`, `ScosCacheModel.java` -- prefixo `scos.cache`
- `validation/README.md` -- modelo de estilo

## Tasks & Acceptance

**Execution:**
- 5 classes de `cache` -- Javadoc + comentários inline
- `cache/README.md` -- novo, com diagrama Mermaid

**Acceptance Criteria:**
- Given o módulo `cache`, when a documentação é adicionada, then toda API pública tem Javadoc, decisões não óbvias têm comentário inline e o README traz diagrama Mermaid.

## Verification

- `mvn -pl cache -am test` -- verde
- checkstyle do perfil `analyze` -- sem violações de Javadoc

## Review Triage Log

Revisão adversarial feita inline (sem subagentes), conferindo cada afirmação do Javadoc/README contra o código:
1. Javadoc da allowlist estava pendurado numa constante privada; movido para a classe (comentário de bloco, sem `/**`) -- `patch`, feito.
2. Propriedades `enableCompression`/`compressionThreshold`/`allowNullValues`/`maxSize`/`description` não são lidas -- documentado; implementar/remover -- `defer`.
3. Filtro de sensíveis por substring descarta o parâmetro da chave (colisão de chaves) e `hashCode` colide -- documentado; `defer`.
4. Fallback para `NoOpCacheManager` só no startup; `ping` não fecha a conexão; `evict` com erro é engolido -- documentado; `defer`.
5. `ScosCacheConfiguration` não permite allowlist extra (usa construtor sem argumentos) -- documentado; `defer`.

## Auto Run Result

Status: done. `mvn -pl cache -am test` verde; checkstyle `analyze` em `cache`: 0 violações.
