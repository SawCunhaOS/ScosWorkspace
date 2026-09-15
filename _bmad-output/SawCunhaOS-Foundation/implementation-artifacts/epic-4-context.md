# Epic 4 Context: Piso de Documentação Obrigatório em Todo o Repositório

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Garantir que, antes do release da 1.2.0, todo módulo do repositório `scos-foundation` — novo (criado pelos Epics 1–3) ou existente (`audit`, `privacy`), tocado funcionalmente neste ciclo ou não — tenha: Javadoc completo em toda API pública, comentário inline onde a lógica não é óbvia, um diagrama de fluxo de uso em Mermaid inline no README, e README obrigatório. Isso elimina o cenário atual em que um consumidor precisa ler a implementação para entender o contrato de um módulo, e fecha a lacuna deixada pela decomposição do Epic 1 (vários módulos novos nascem sem nenhuma documentação). Este piso é uma decisão explícita do usuário tomada na consolidação da arquitetura — não deriva de nenhum FR do PRD original — e **bloqueia o release da 1.2.0** independentemente de o gate mecânico (Checkstyle) estar de fato amarrado ou não.

## Stories

- Story 4.1: Diagnosticar o gate mecânico de Javadoc via Checkstyle
- Story 4.2: Documentar o módulo `core`
- Story 4.3: Documentar o módulo `audit-api`
- Story 4.4: Documentar o módulo `jdempotent-api`
- Story 4.5: Documentar o módulo `validation-api`
- Story 4.6: Documentar o módulo `archtest`
- Story 4.7: Documentar o módulo `spring`
- Story 4.8: Documentar o módulo `validation`
- Story 4.9: Documentar o módulo `cache`
- Story 4.10: Documentar o módulo `jpa`
- Story 4.11: Documentar o módulo `web`
- Story 4.12: Documentar o módulo `feign`
- Story 4.13: Documentar o módulo `jdempotent`
- Story 4.14: Documentar o módulo `audit`
- Story 4.15: Documentar o módulo `privacy`
- Story 4.16: Ativar globalmente o gate mecânico de Checkstyle

## Requirements & Constraints

- Piso de documentação por módulo, sem exceção: Javadoc em toda API pública (métodos com visibilidade `public`/`protected` ou mais aberta, e métodos com 2+ linhas), comentário inline em lógica não-óbvia, diagrama Mermaid de fluxo de uso inline no README, e README obrigatório.
- Módulos `*-api` (`audit-api`, `jdempotent-api`, `validation-api`) têm regra própria: o README deve abrir com a frase "este artefato não executa nada; a implementação é `scos-foundation-<x>`" — eles não têm lógica de runtime, então não se cobra log de inicialização nem diagrama de sequência de execução, só o diagrama de fluxo de uso.
- `archtest` é exceção ao gate de Javadoc (não tem API pública de produção); seu README deve explicar o propósito do módulo e listar as regras ArchUnit existentes.
- `jdempotent` exige diagrama de **sequência** (não só fluxo genérico) cobrindo `tryAcquire` → `Lease` → fail-open, para tornar visível a garantia real sob falha do Redis.
- `audit` e `privacy` não são tocados funcionalmente por este ciclo, mas entram no mesmo piso: `audit` só precisa do diagrama (README já existe); `privacy` só precisa da documentação — já herda o profile `analyze` automaticamente da raiz (confirmado na Story 4.1: todo módulo do reactor herda via `<parent>`, nenhum precisa "ligar" nada individualmente).
- O gate mecânico de Javadoc via Checkstyle (`MissingJavadocMethod`/`MissingJavadocType`) existe configurado (`configLocation`) no profile `analyze` da raiz, herdado por todo módulo. **Diagnosticado pela Story 4.1**: o CI já roda `checkstyle:check` direto em todo PR, mas não falha hoje por Javadoc ausente porque a severidade global do `checkstyle.xml` é `warning` e o limiar padrão do goal é `error` — não por falta de amarração ao `verify`. A correção da severidade (e a decisão de como fasear, já que isso destrava ~345 violações pré-existentes só em `core`) acontece só na Story 4.16, depois que todo módulo já estiver documentado — evita quebrar o build do reactor prematuramente.
- O bloqueio de release por falta de documentação vale por **checagem manual** até a severidade do gate mecânico ser corrigida — a decisão de bloquear não depende do gate estar automatizado.
- Comentário inline para lógica não-óbvia é cobrado em revisão (checklist de PR), não tem gate mecânico. Diagrama Mermaid e README também são cobrados via checklist de revisão, não mecanicamente.
- Não há NFR nem estimativa de esforço para este piso no PRD original — foi decisão tomada na consolidação da arquitetura, adicionada depois.

## Technical Decisions

- O perfil `analyze` (Checkstyle configurado em `etc/devops/checkstyle/checkstyle.xml`) foi centralizado no `pom.xml` raiz já no Epic 1 (Story 1.4) como um `<profile id="analyze">` herdado por todo módulo via `<parent>` (herança padrão do Maven, não `pluginManagement`) — cobrindo 100% dos módulos existentes e futuros pelo mesmo veículo, sem que nenhum precise declará-lo individualmente. `failOnViolation` continua desligado até este epic; Story 4.16 é quem liga isso de fato.
- **CI real** (`.github/workflows/build.yml`, job `security-check`) já roda `mvn -Panalyze checkstyle:check` diretamente em todo PR, sem `continue-on-error` — não depende de `mvn verify`. Confirmado na Story 4.1: hoje esse passo não falha por violação de severidade `warning` (só a global do `checkstyle.xml`) porque o `violationSeverity` padrão do goal é `error` — esse descasamento de severidade, não a amarração a `verify`, é o que bloqueia o gate de fato.
- Cada história de documentação de módulo depende do módulo já existir (extraído pelo Epic 1) e, quando aplicável, já ter recebido as correções de comportamento dos Epics 2/3 antes de documentar (ex.: `core` depende de Epic 1/Story 1.7 e Epic 2/Story 2.8; `web` depende de Epic 1/Story 1.12 e Epic 2/Story 2.9; `jdempotent` depende de todo o Epic 3 e do README parcial já escrito na Story 3.17).
- Story 4.1 é só diagnóstico: roda `mvn -Panalyze verify`/`checkstyle:check` num módulo de teste com um método público sem Javadoc introduzido de propósito, e documenta se o build falha ou não — nenhuma configuração é alterada nessa story.

## Cross-Story Dependencies

- Epic 4 depende dos Epics 1, 2 e 3 (precisa que os módulos novos existam antes de documentá-los). As stories de documentação de `privacy` e `audit` (4.14, 4.15) são independentes das demais e entre si, já que esses módulos não são tocados funcionalmente por nenhum outro epic.
- Story 4.16 (ativação global do gate) depende de todas as demais stories de documentação (4.2–4.15) estarem concluídas, e do diagnóstico da Story 4.1 (para saber se precisa corrigir a amarração do `goal=check` antes de ligar `failOnViolation`).
- Story 4.13 (`jdempotent`) depende do README parcial já produzido na Story 3.17 do Epic 3 (princípio "cache é fast-path, não garantia").
- Story 4.11 (`web`) e Story 4.14 (`audit`) dependem de correções feitas no Epic 2 (Story 2.9 move `ExceptionsHandler` para `web`; Story 2.8 reponta `audit` para consumir `ScosException` do `core`).
