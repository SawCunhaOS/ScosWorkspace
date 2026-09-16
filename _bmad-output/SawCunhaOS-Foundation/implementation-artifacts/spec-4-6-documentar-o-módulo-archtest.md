---
title: 'Documentar o módulo archtest'
type: 'chore'
created: '2026-09-15'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/SawCunhaOS-Foundation/implementation-artifacts/4-6-documentar-o-módulo-archtest.md', '{project-root}/SawCunhaOS-Foundation/archtest/README.md', '{project-root}/SawCunhaOS-Foundation/archtest/AGENTS.md', '{project-root}/SawCunhaOS-Foundation/archtest/src/test/java/br/com/sawcunhaos/foundation/archtest/ArchitectureTest.java', '{project-root}/SawCunhaOS-Foundation/archtest/pom.xml']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `archtest/README.md` já explica o propósito do módulo (regras ArchUnit cross-módulo, sem código de produção) e já lista as 2 regras existentes (`nothingDependsOnWeb`, `noCyclesBetweenModules`), satisfazendo a AC1 — mas nunca declara explicitamente que o módulo é `scope=test` (sem `src/main/java`) e por isso fora do gate de Javadoc/Checkstyle (AC2, confirmado pelo `pom.xml` raiz: `maven-checkstyle-plugin` varre só `compileSourceRoots`). Além disso, `archtest/AGENTS.md` registra um "known pitfall" desatualizado ("README diz 'Nenhuma [regra] ainda'"), quando o README atual já lista as 2 regras corretamente.

**Approach:** Adicionar ao `README.md` uma frase curta declarando que o módulo é `scope=test`, sem `src/main/java`, e por isso fora do escopo do Checkstyle/Javadoc obrigatório — mesma isenção que módulos de teste normalmente têm. Corrigir a nota "Known pitfalls" do `AGENTS.md` do módulo para refletir que o README já lista as regras corretamente. Não alterar a explicação de propósito nem a lista de regras já presentes no README, nem tocar em `ArchitectureTest.java`/`pom.xml` — só documentação.

</frozen-after-approval>

## Implementation Notes

- Confirmado por leitura direta: `archtest/README.md` já explicava o propósito e já listava as 2 regras existentes antes desta story — a Task 2 da story original (4.6) estava desatualizada ao pedir para "criar" o README. Só faltava a declaração explícita da isenção de Javadoc (AC2).
- Adicionada seção "## Gate de Javadoc" ao `README.md`, citando o fato verificável (perfil `analyze` do `pom.xml` raiz configura `maven-checkstyle-plugin` sem `includeTestSourceDirectory`, então só varre `compileSourceRoots`; `archtest` não tem `src/main/java`).
- Corrigida a nota "Known pitfalls" de `archtest/AGENTS.md`: a nota antiga dizia que o README estava desatualizado citando "Nenhuma [regra] ainda", mas o README já lista as 2 regras corretamente — a nota antiga é que estava obsoleta. Substituída por uma advertência prospectiva (manter README e `ArchitectureTest.java` sincronizados ao adicionar regra nova).
- Nenhuma alteração de código (`ArchitectureTest.java`, `pom.xml`) — só documentação, conforme o Approach.

## Review Triage Log

Camada rodada: blind-hunter (4 achados, piso N=1 para ~0,93kB de conteúdo alterado). Iteração de review: 1.

1. **[blind-hunter] A seção "Gate de Javadoc" justifica a isenção de forma mecânica (`scope=test`, sem `src/main/java`), enquanto `epics.md`/`epic-4-context.md` justificam a mesma isenção como "sem API pública de produção" — o README não liga as duas justificativas.** Verdict: `low` — rejeitado. As duas justificativas descrevem o mesmo fato (este módulo sem `src/main/java` é exatamente o módulo sem API pública de produção); não há contradição real que confunda o leitor, e a justificativa mecânica é, se algo, mais verificável que a da épica. Emendar não corrige nenhuma imprecisão, só infla o texto.
2. **[blind-hunter] A seção nova cobre só o Checkstyle; o perfil `analyze` também liga JaCoCo (cobertura mínima 0.80), SpotBugs e OWASP dependency-check, sem dizer se essas checagens também são moot para um módulo sem `src/main/java`.** Verdict: `medium`, mas fora de escopo — AC2 desta story cobre só o gate de Javadoc. → `defer` (`deferred-work.md`).
3. **[blind-hunter] A nota "Known pitfalls" do `AGENTS.md`, revisada por esta story, avisa só sobre sincronizar a lista de regras; não avisa que a nova alegação de isenção de Javadoc também depende de um fato externo frágil (config do Checkstyle no `pom.xml` raiz) que pode mudar.** Verdict: `medium` — introduzido por esta própria story (a alegação de isenção é nova). → `patch`: frase adicionada à mesma nota do `AGENTS.md` cobrindo a dependência do `pom.xml` raiz.
4. **[blind-hunter] A seção nova fica no fim do README sem referência de volta ao texto de propósito do topo (que já explica a natureza `scope=test`/AD-5 do módulo).** Verdict: `low` — rejeitado. Reorganização estrutural sem ganho de correção; o texto de propósito e a nova seção já são consistentes entre si sem precisar de referência cruzada explícita.

