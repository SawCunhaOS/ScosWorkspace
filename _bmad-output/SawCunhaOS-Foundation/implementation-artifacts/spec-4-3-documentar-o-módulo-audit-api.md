---
title: 'Documentar o módulo audit-api'
type: 'chore'
created: '2026-09-15'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/4-3-documentar-o-módulo-audit-api.md', '{project-root}/SawCunhaOS-Foundation/core/README.md', '{project-root}/SawCunhaOS-Foundation/audit-api/README.md', '{project-root}/SawCunhaOS-Foundation/audit-api/src/main/java/br/com/sawcunhaos/foundation/audit/api/Auditable.java', '{project-root}/SawCunhaOS-Foundation/audit-api/src/main/java/br/com/sawcunhaos/foundation/audit/api/AuditAction.java']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** O módulo `audit-api` (Story 1.5, `done`) já existe e seu `README.md` já abre com a frase exigida ("este artefato não executa nada; a implementação é `scos-foundation-audit`") e traz uma tabela de conteúdo, mas falta o diagrama Mermaid do fluxo típico de uso exigido pela AC1. Além disso, o `@interface Auditable` (tipo) e o `enum AuditAction` (tipo e suas 4 constantes) não têm nenhum Javadoc de contrato — só os 4 atributos de `Auditable` já têm — violando a AC2 ("toda anotação pública tem Javadoc").

**Approach:** Adicionar Javadoc de tipo em `Auditable` (o que a anotação sinaliza — auditoria automática de C/U/D via Hibernate listener em entidade, ou auditoria manual de leitura em método — sem descrever a implementação, que não está neste módulo). Adicionar Javadoc de tipo e de cada constante em `AuditAction`. Adicionar ao `audit-api/README.md` uma seção "Fluxo típico de uso" com diagrama Mermaid (`flowchart LR`, mesmo padrão de `core/README.md`) mostrando: aplicação consumidora anota entidade/método com `@Auditable` (vindo de `audit-api`) → precisa de `scos-foundation-audit` no classpath para a anotação ter efeito → listener Hibernate/aspecto processa a anotação. Não alterar a frase de abertura, a tabela "Conteúdo" nem a seção "Regra de fronteira" já existentes; não alterar nenhum atributo, valor ou assinatura — só adição de documentação.

</frozen-after-approval>

## Implementation Notes

- Pré-requisito confirmado por leitura direta: `audit-api` já existe (Story 1.5, `done`), com `Auditable.java`, `AuditAction.java`, `ArchitectureTest.java` e um `README.md` que já trazia a frase de abertura exigida e a tabela "Conteúdo" — só faltavam o diagrama Mermaid (AC1) e o Javadoc de tipo (AC2).
- Javadoc de tipo adicionado em `Auditable` e `AuditAction`, sem tocar nos 4 atributos de `Auditable` que já tinham Javadoc. Seção "Fluxo típico de uso" com diagrama Mermaid (`flowchart LR`) adicionada ao `README.md`, no padrão de `core/README.md`.
- Desvio do Approach original: não foi adicionado Javadoc por constante em `AuditAction` (`INSERT`/`UPDATE`/`DELETE`/`READ`) — a primeira versão só restabelecia o nome da constante em prosa (zero informação nova) e a única forma de agregar valor real exigiria citar `ActionType.SELECT`, uma entidade de persistência do módulo `audit` (implementação), o que contradiz a própria Approach ("sem descrever a implementação, que não está neste módulo"). Mantido só o Javadoc de tipo do enum, que já cobre o contrato com `Auditable#action()`/`auditRead()`.
- `mvn -pl audit-api -am test` verde (2 testes do `ArchitectureTest`, incluindo a regra local `onlyAnnotationsAndEnums`) antes e depois dos patches de revisão.
- Revisão (blind-hunter) aplicada: 3 grupos de achados corrigidos (ver Review Triage Log) e 1 achado real, mas fora de escopo, adiado para `deferred-work.md` — o caminho de leitura via `@Auditable(action = AuditAction.READ)` não é processado por nada em tempo de execução no módulo `audit` (implementação), só o `auditRead()` de tipo está de fato ligado ao `ScosHibernateAuditListener`. `mvn -pl audit-api -am test` reexecutado após os patches, verde.

## Review Triage Log

Camada rodada: blind-hunter (6 achados, piso N=2 para ~2,54kB de conteúdo alterado). Iteração de review: 1.

1. **[blind-hunter] O novo Javadoc de tipo de `Auditable` afirmava que o uso em método é "triggered after the method returns successfully" — uma auto-invocação que não existe: não há `@Aspect`/`JoinPoint` no módulo `audit`, e o único uso de `@Auditable(action=READ)` do repositório (`CountryReadService`, só em teste) nunca é chamado. O mesmo Javadoc dizia "manual" e "triggered" na mesma frase, uma contradição interna. O diagrama novo só mostrava esse caminho (método → `AuditAction` → listener), omitindo o único caminho de leitura de fato automático (`auditRead()` de tipo, verificado sem condição em `ScosHibernateAuditListener.onPostLoad`).** Verdict: `medium` (documentação nova, central ao propósito da story, descrevendo um comportamento inexistente). → `patch`: Javadoc de `Auditable` reescrito para não afirmar disparo automático no nível de método ("how the annotation is invoked at this level is defined by the implementation module, not by this contract") e para citar `auditRead()` no nível de tipo; diagrama redesenhado com dois nós de implementação (listener automático de C/U/D+`auditRead()` vs. invocação de leitura por método definida pela implementação).
2. **[blind-hunter] O diagrama nomeava a classe concreta `ScosHibernateAuditListener`, implementação que não está neste módulo.** Verdict: `medium`, mas parcial: o próprio texto da story (Task 2) pede explicitamente um nó "listener Hibernate/aspecto" no diagrama — só o nome da classe concreta era específico demais. → `patch`: nó do diagrama trocado para a descrição genérica já pedida pela story ("listener Hibernate"), sem nomear a classe.
3. **[blind-hunter] O parágrafo adicionado logo após o diagrama ("Sem `scos-foundation-audit` no classpath, a anotação compila e não faz nada — nenhum erro, nenhum aviso") repetia quase literalmente o parágrafo de abertura já existente (linhas 9-11).** Verdict: `low` (cosmético, sem risco). → `patch`: parágrafo duplicado removido.
4. **[blind-hunter] Os 4 Javadocs de constante de `AuditAction` só reafirmavam o nome da constante ("A new entity was created." etc.), sem nenhuma informação além do próprio identificador.** Verdict: `medium` (Javadoc sem valor é pior que ausência de Javadoc — mascara como documentação algo que não documenta nada). → `patch`: Javadocs de constante removidos; mantido só o Javadoc de tipo do enum. Ver Implementation Notes para por que a alternativa sugerida pelo revisor (citar `ActionType.SELECT`) foi rejeitada — violaria a própria regra de não descrever implementação.
