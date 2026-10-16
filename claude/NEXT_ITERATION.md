# Il workflow su Claude Code

Piano e stato del porting, iniziato il 16 ottobre 2026. Il lato Copilot
(`copilot/`) lo porta avanti Copilot, con il suo `copilot/NEXT_ITERATION.md`;
quello che serve a tutti e due sta in `common/` (comandi, schemi dei segnali,
skill generiche).

## Decisioni

Le stesse figure del workflow Copilot (kent, hughes, ford, unclebob, martin,
simon, joshua, argyris, linus), con il contenuto degli agenti Copilot: girano
su Opus anche lì, quindi le regole restano valide. Cambia il modo di farle
rispettare, perché Claude Code ha hook con payload strutturato.

- **Agenti utente** in `~/.claude/agents/` (`make install`): il workflow
  gira in qualunque progetto, senza toccare `~/.claude/settings.json`.
- **kent come thread principale**: `claude --agent kent`. Gli altri sono
  subagent in background; kent li riprende con `SendMessage` (stesso ruolo
  di `write_agent`/`read_agent` su Copilot).
- **Le domande passano ancora da kent.** `AskUserQuestion` è tolto a tutti i
  subagent: restano i blocchi `ASK_USER` e la relay di kent.
- **Hook nel frontmatter di ogni agente**, attivi solo mentre l'agente gira
  (installati in `~/.claude/minime/hooks/`):
  - `Stop` (che diventa `SubagentStop`) → `signal_stop.py --expect …`:
    valida l'ultimo messaggio con `signal-check` e, se non passa, blocca e
    rimanda all'agente i problemi come istruzione successiva. **Validazione
    deterministica dei segnali**, senza orchestratore in codice: il punto 2
    del piano Copilot chiuso davvero. Ogni fine turno va in
    `/tmp/kent-events.jsonl` (agente, id, transcript, segnale, esito): è la
    lista degli eventi da verificare per joshua, al posto di `events.jsonl`
    e dei messaggi `LAUNCHED`/`REPORTED` di kent.
  - `PreToolUse` → `guard.py <agente>`: le regole che il codice sa
    controllare. Niente `git push`, rete o cluster; nessuna scrittura git
    fuori dal comando `linus`; i sottocomandi `linus` di ciascuno (martin
    solo `squash`, unclebob e ford i propri commit, gli altri solo lettura);
    i file che ciascuno può scrivere, con Edit/Write o dalla shell. Ogni
    rifiuto va in `/tmp/kent-guard.jsonl`. È una rete di sicurezza: ciò che
    non riconosce passa al controllo normale dei permessi, e joshua verifica
    il resto.
- **joshua si alleggerisce**: i segnali e le regole meccaniche (push, git,
  linus, percorsi) li fanno rispettare gli hook. Restano a lui le regole di
  giudizio: il contenuto dei cicli TDD, le domande inoltrate parola per
  parola, le affermazioni dei report confrontate con le prove (transcript in
  `agent_transcript_path`, commit, log).
- **Comandi**: `linus`, `spec-check`, `signal-check` in `common/bin`, uguali
  per i due lati; linus mette il trailer `Co-Authored-By: Claude (<model>)`
  quando gira dentro Claude Code (`CLAUDECODE=1`) o con
  `LINUS_COAUTHOR=claude`. Gli agenti passano `--model <id>`.
- **Lanciatori**: `unclebob` (modo interattivo). kent, argyris e linus si
  avviano con `claude --agent <nome>`; nessun lanciatore con lo stesso nome
  di quelli Copilot in `~/.local/bin`.

## unclebob: Copilot e Claude a confronto

Il vecchio `claude/agents/unclebob.md` e `copilot/agents/unclebob.agent.md`
condividono le tre leggi e poco altro.

| Tema | Claude (prima) | Copilot | Nuovo unclebob |
|---|---|---|---|
| Chi progetta i test | l'utente, sempre; l'agente non suggerisce mai cosa testare | l'agente, dalla spec e dalle interfacce | interattivo: l'utente; workflow: l'agente |
| Conferme | dopo red, dopo green, su ogni proposta di refactor | nessuna per passo; commit nel prompt dei permessi | interattivo: come prima; workflow: nessuna |
| Fake it | esplicito e severo (il valore fisso è l'unica implementazione ammessa) | terza legge + triangolazione | comune: fake it severo **e** triangolazione |
| Codice vietato | elenco (validazione, errori, default, docstring, log, type hint) | — | comune |
| Budget di tentativi | un solo tentativo di correzione per passo | — | solo interattivo |
| Refactor | sei sotto-passi proposti uno a uno (SOLID, complessità, idiomaticità, produzione, test, suite) | SOLID, produzione, test, `elixir-style`, controlli statici, refactor vuoto con il verdetto | i due moduli del ciclo per intero (helper privati del test compresi), mai il materiale di test condiviso (lo rivede martin); interattivo: cinque sotto-passi (4a–4e) e un refactor vuoto se nessuno committa |
| Commit | `git commit` diretto, `test:`/`feat:`/`refactor:` senza scope | comando `linus`, fasi, scope, `check-message`, amend del red, regression, characterisation, fixup | `linus` in tutti e due i modi; lo scope si chiede in STEP 0 nel modo interattivo |
| Test e controlli statici | suite in 4f | suite dopo ogni green e refactor; formatter prima di red e green; controlli a ogni ciclo; dialyzer a fine unità | mai la suite completa (la CI); dopo ogni commit i test che includono i file del commit; ai punti di chiusura (fine unità, fine correzione, STEP 5 interattivo) i test correlati al branch e i controlli della skill `<linguaggio>-static-checks` |
| Precondizione "i test devono girare" | STEP 0 non lancia nulla | rifiuto categorico se non girano | comune: STEP 0 ora fa una prova |
| Red che passa subito | STOP e chiede | characterisation (rompere l'asserzione, poi green vuoto) | interattivo: STOP; workflow: characterisation |
| Solo Copilot | — | activity log, analisi statica a fine unità, sessioni di correzione, harness da kent, spec e PBT, interfacce come contratto, segnali | solo workflow |
| Solo Claude | interpretazione letterale, deviazioni richieste dall'utente | — | interpretazione comune; deviazioni solo interattivo |

Nel modo workflow unclebob riceve il lavoro da kent: un componente, il flusso
funzionale, o (sessione di correzione) le modifiche di review registrate da
martin, che kent gli inoltra. Che martin parli a unclebob direttamente è
possibile (i subagent possono lanciarne altri) ma le domande all'utente
finirebbero a martin invece che a kent: per ora no.

## Fatto

- `common/`: comandi, schemi e skill condivisi; `make common-install`.
- linus con il trailer per CLI.
- `claude/hooks/signal_stop.py` e `claude/hooks/guard.py`, provati con
  payload finti (28 casi del guard).
- `claude/agents/unclebob.md` a due modi, comando `unclebob`.
- `make install` installa agenti, skill (Claude e comuni), hook e comandi.

- unclebob: test e controlli statici fuori dai cicli, confine del refactor
  sui due moduli del ciclo; tolta la tabella "Large systems".
- Skill comune `elixir-handbook` (campi `projects` e `tools`): toolchain,
  build, test (uno, quelli che includono un file, quelli del branch),
  controlli statici e regole di stile; sostituisce `elixir-style`. Una
  `<linguaggio>-handbook` per linguaggio: le peculiarità di un ecosistema
  stanno lì, gli agenti dicono solo cosa lanciare e quando.
- `make clean` (lista esplicita `INSTALLED` di tutto ciò che i target
  installano, nomi vecchi compresi; i percorsi mancanti si saltano) e
  `make clean-check`, che fallisce se la lista non copre qualcosa;
  `install-copilot` come alias di `copilot-install`. Provato in una HOME
  finta: dopo `install`, `copilot-install` e `clean` resta solo
  `~/.bash_copilot`, voluto.
- Diagrammi ASCII dell'architettura nel README ("Architecture"): vanno
  aggiornati con ogni cambio di struttura, insieme a `INSTALLED`.
- kent mantiene `AGENTS.md` e `CLAUDE.md` del progetto (scritto in
  `copilot/agents/kent.agent.md`, "The project's agent instructions"): il
  guard glielo permette (`name:AGENTS.md`, `linus stage`/`commit`) e lo
  vieta a ford e unclebob, che segnalano in `open_points`.

## Da fare

1. Gli altri agenti, dal contenuto Copilot, con hook nel frontmatter e
   strumenti di Claude Code (`Agent`, `SendMessage`, `AskUserQuestion`,
   `Edit`/`Write`, `Bash` con `run_in_background`):
   - **kent** (thread principale): relay con `AskUserQuestion`, lancio in
     background, `SendMessage`, `SIGNAL_INVALID` non serve più (lo fa
     l'hook); niente eventi a joshua, che legge `/tmp/kent-events.jsonl`.
   - **hughes**, **ford**, **martin**, **simon**: port quasi diretto; tolta
     la parte "controlla il blocco con signal-check" (lo fa l'hook).
   - **kent**: portare anche "The project's agent instructions".
   - **martin**: rivede esplicitamente il materiale di test condiviso
     (support, factory, harness) dell'unità, che unclebob non tocca nei
     cicli; valutare se lancia lui i controlli statici
     (`<linguaggio>-static-checks`) in review e li registra come modifiche.
   - **joshua**: audit sui transcript e su `/tmp/kent-events.jsonl` e
     `/tmp/kent-guard.jsonl`; checklist ridotta alle regole di giudizio.
   - **argyris** (`claude --agent argyris`) e una skill `minime-sync` per
     `~/.claude` → `claude/` e `common/`.
   - **linus** (`claude --agent linus`) per i commit fuori dal workflow.
2. Permessi: equivalente di `auto_approve.py` per non far rispondere
   l'utente a ogni comando (regole `allow`/`deny` nel frontmatter non
   esistono: `permissionMode` per agente, o un hook `PermissionRequest`).
3. README: sezione del workflow Claude Code.
4. **Scaffolding di un progetto nuovo.** kent oggi non sa crearne uno.
   Esiste già `claude/skills/scaffold` (solo C: CMake + Make, template,
   `make deps` per Arch e Ubuntu), da riusare. Una skill per linguaggio
   (Elixir, Python, C), probabilmente parte della
   `<linguaggio>-handbook` o accanto a lei: layout, build (C: CMake + Make),
   test runner e libreria property-based, formatter, linter, type checker,
   `AGENTS.md` iniziale, `.gitignore`. Da decidere chi lo esegue (ford,
   dopo l'ADL?) e come si inserisce nel ramo greenfield di kent.
5. **simon da rivedere.** Il workspace Structurizr DSL (`workspace.dsl`, C4)
   è giusto; accanto però scrive un altro file, non ancora identificato, e
   non scrive `architecture.md`, il markdown con i sequence diagram Mermaid
   delle iterazioni esplorate, costruite o corrette e i class diagram, che
   pure le sue istruzioni chiedono. Da approfondire su una
   `.documentation/<branch>/` vera prima del porting.
6. **Makefile: installazione delle CLI.** Un target per installare Claude
   Code e uno per Copilot CLI, solo Arch Linux e Ubuntu, come il resto.
7. **Versione LangGraph.** Un orchestratore in LangGraph, per imparare il
   framework e per misurare se serve: le due versioni girano in parallelo
   sugli stessi progetti e si confrontano i risultati (quanto è limitata
   quella a soli agenti, quanto sbaglia quella in codice). Servono metriche
   comuni da definire prima: violazioni di joshua, segnali invalidi,
   rifiuti del guard, cicli e commit per unità, tempo, token, correzioni di
   review.

## Da verificare

- Se gli hook nel frontmatter valgono anche per l'agente lanciato come
  thread principale (`claude --agent kent`): la documentazione lo dice solo
  per i subagent. Se no, kent ha bisogno dei suoi hook in un altro modo.
- Se il frontmatter accetta `Stop` per un agente utente (in
  `~/.claude/agents/`) senza la finestra di fiducia, che la documentazione
  chiede solo per gli agenti di progetto.
- Il limite di 8 blocchi consecutivi degli Stop hook
  (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`) vale anche per `SubagentStop`?
- Un `SendMessage` a un subagent ancora al lavoro: messo in coda o
  rifiutato?
- unclebob interattivo: che il guard (attivo anche lì) e linus non
  intralcino la procedura passo per passo.
