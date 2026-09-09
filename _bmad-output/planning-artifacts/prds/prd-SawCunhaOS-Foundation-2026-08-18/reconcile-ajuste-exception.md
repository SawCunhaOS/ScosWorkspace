# Reconciliação — plano-ajuste-exception.md vs PRD

Nota de numeração: o plano original não tem uma "seção 9". A sequência entre os
3 planos está na **seção 6** ("Ordem entre os três planos") e a sequência de
commits está na **seção 8** ("Sequência de commits"). A análise abaixo cobre
essas duas seções (mapeadas para "## Sequenciamento e Fases" no PRD), além do
restante do documento.

## Gaps encontrados

1. **Bug 3.7 (`resolveTitle` como controle de fluxo / `getMessageOrDefault`) está totalmente ausente do PRD.**
   O plano descreve um bug concreto: `resolveTitle` usa `try/catch` para testar
   existência de chave no bundle de mensagens, mascarando falhas reais do
   `LocaleService` e devolvendo um literal em inglês ("Business Error") numa
   API localizada. A correção proposta é específica: `LocaleService` ganha um
   método `getMessageOrDefault(code, default)`, com o default vindo de
   `ExceptionCode.getTitle()`. Esse item some completamente das FRs — a seção
   "F2" do PRD pula de FR-16 (3.4, log) para FR-17 (3.8, constante MDC), sem
   nenhuma FR para 3.7. A tabela de sequenciamento também derruba a menção: o
   plano original lista explicitamente "`LocaleService.getMessageOrDefault`
   (3.7) e a constante de MDC (3.8) entram no `core` neste momento" na Fase 3,
   mas o PRD só carrega a constante de MDC (FR-17) — o método
   `getMessageOrDefault` não aparece em nenhuma FR nem na tabela.

2. **A seção 8 (sequência de commits) não foi transposta para o PRD em nenhuma forma.**
   O plano define uma ordem atômica de 11 commits (teste-primeiro, depois
   fixes de comportamento na ordem 3.1→3.2→3.6, depois a reestruturação
   `handleExceptionInternal`, extração de duplicação, regex, log, e só então
   as duas movimentações de pacote e a remoção do módulo do reactor). O PRD
   captura o princípio geral ("build verde a cada commit", "2 commits
   separados mover vs. comportamento" em NFR-2) mas não preserva a ordem
   interna específica dentro da Fase 0–2 do F2. Em particular, a prática de
   TDD explícita do plano — "Fase 0: teste que prova o bug, deve falhar antes
   da correção" para os bugs 3.1, 3.2 e para o contrato de formato do 404 —
   não vira nenhum NFR para o F2. O NFR-3 do PRD só exige cobertura de teste
   para a Fase 0 do **F1** (jdempotent); a exigência equivalente de
   "teste que falha antes do fix" para os bugs do F2 (exception) desaparece.

3. **"Repontar `audit` para o `core`" (ação concreta da Fase 3 do plano) não aparece em nenhuma FR.**
   A seção 2 do plano justifica a decomposição com um ganho de acoplamento
   concreto: hoje o `audit` depende de `exception` (que traz `spring-web` e
   `spring-security-core`) só para usar `ScosException`; depois da mudança,
   depende apenas do `core`. A seção 5 (Fase 3) lista isso como item de
   trabalho explícito: "Repontar `audit` para o `core`". O PRD (FR-11 e a
   linha 5 da tabela de sequenciamento) descreve a divisão
   contrato-de-domínio/tradução-HTTP, mas não menciona a necessidade de
   repontar o `audit` como consumidor. Também não vira métrica de sucesso —
   a métrica de redução de dependências transitivas do PRD fala só de
   consumidores do `utils` (ex. `DateUtils`), não do ganho de acoplamento do
   `audit` em relação a `exception`.

4. **Dois dos cinco riscos da seção 7 do plano não aparecem nas OQs do PRD.**
   - O plano separa dois riscos distintos de "Alta probabilidade, é o
     objetivo": (a) mudança de status HTTP pelo 3.1/3.2/3.6, e (b) o
     `handleExceptionInternal` alterar o **corpo/formato** de erros hoje
     tratados pela superclasse do Spring (404, método não suportado, media
     type inválido). O PRD's OQ-1 cobre só o risco (a) (mudança de status
     code); o risco (b) — que o formato de resposta de erros antes
     "nativos do Spring" muda para o formato SCOS — não tem OQ correspondente,
     apesar de ser um risco que o próprio plano classifica como "Alta — é o
     objetivo" (mesmo nível do OQ-1).
   - O risco "Regex do 3.3 já estar quebrado em Jackson 3 sem ninguém ter
     notado" (probabilidade Média, mitigado pelo teste da Fase 0) não tem OQ
     equivalente no PRD.
   - Menor: o risco "Baixa" de a fusão no `web` obrigar quem só quer as
     exceções a trazer `spring-web` também não vira OQ (aceitável, já que é
     endereçado estruturalmente pela própria decisão de design, mas é uma
     omissão total, não uma reafirmação implícita clara).

5. **Nuances de comportamento de handler perdidas na condensação para FR-9 e FR-16:**
   - FR-9 diz apenas "corrigir o handler... restaurando o 403". O plano é
     mais específico: "trocar o import e **manter os dois handlers**, um
     para cada tipo do Spring Security" (i.e., o handler para
     `AuthorizationDeniedException` que já existe continua junto do handler
     corrigido para `AccessDeniedException` — não é uma substituição de um
     pelo outro). Essa instrução de não remover o handler irmão pode se
     perder na implementação se só a FR for lida.
   - FR-16 não carrega a frase do plano "o único que merece `ERROR`
     incondicional é o handler genérico" — a FR fala em regra 4xx/5xx mas
     não deixa explícito que o handler genérico é a exceção que sempre loga
     `ERROR` independente de status.

## Cobertura confirmada

- Os bugs 3.1, 3.2, 3.3, 3.5, 3.6 e 3.8 estão corretamente mapeados em FRs
  específicas (FR-9, FR-10, FR-14, FR-13, FR-15, FR-17), com nomes de classe,
  método e assinatura preservados (`AccessDeniedException` do Spring Security
  vs. NIO, `getBeanResults()`/`getValueResults()`, `handleExceptionInternal`,
  `InvalidFormatException`/`MismatchedInputException.getPath()`).
- A inversão estrutural (seção 2) e a decisão de fundir a tradução HTTP no
  `web` em vez de manter artefato separado — incluindo
  `@ConditionalOnProperty(scos.web.error-handler.enabled, matchIfMissing=true)`
  e `@Order(Ordered.LOWEST_PRECEDENCE)` — está fielmente reproduzida em FR-11
  e FR-12, com os oito nomes de classe do contrato de domínio e os quatro da
  tradução HTTP intactos.
- A tabela da seção 6 (ordem entre os três planos) foi transposta quase
  linha a linha para "## Sequenciamento e Fases" do PRD, inclusive o
  princípio-chave "corrigir comportamento com o arquivo/módulo parado; mover
  depois" (reforçado por NFR-1 e NFR-2) e a dependência cruzada entre a Fase 3
  do `exception` e a Fase 3 do `utils` (linha 5).
  Nenhuma linha foi reordenada ou omitida.
- O risco "Alta — é o objetivo" sobre mudança de status HTTP (3.1/3.2/3.6) e
  o risco "Média" de corrigir-e-mover no mesmo commit estão presentes,
  respectivamente, em OQ-1 e em NFR-2/OQ-5.
