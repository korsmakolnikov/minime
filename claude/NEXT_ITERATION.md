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
   Esiste già `claude/skills/scaffold` (solo C: `scaffold.sh`, template
   CMake + Make, `make deps` per Arch e Ubuntu, CI GitHub; si invoca a mano
   con `/scaffold c`), da riusare. **Priorità: Python**, perché il primo
   progetto su cui proveremo il workflow è la versione LangGraph. Una skill per linguaggio
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

## Refactor dell'architettura degli agenti (decisioni del 16 ottobre)

Da fare sul lato Claude; Copilot lo applica dal suo `NEXT_ITERATION.md`.

1. **Tool al posto di bash.** Nessun agente lancia bash direttamente: un
   tool per ogni compito (test, controlli, commit, scaffolding, log…),
   l'agente resta agnostico su come si fa. Motivo: Copilot inventa ogni
   volta script nuovi per le stesse cose. In attesa della decisione
   sull'inventario dei comandi (lista per agente fatta in sessione); da
   capire la forma: server MCP, comandi in `common/bin` con un'allow-list
   esatta nel guard, o tool del grafo nella versione LangGraph.
2. **kent senza bash e senza conoscenza di dominio o architettura.**
   - `adl-reverse` passa a ford (ADL as-is nel ramo brownfield);
   - kent non lancia i test: li prova unclebob (precondizione);
   - shopping list con Write limitato a quel file;
   - `/tmp/kent-flow.log` scritto dagli hook, non dagli agenti;
   - spostamento delle cartelle legacy solo in `make update` (aggiungere
     `.shopping_lists/` → `.sources/shopping_lists/`);
   - kent detiene il workflow: sa quali passi avvengono; gli altri vedono
     solo il proprio scope.
3. **Scaffolding a kent, con skill e tool.** Una skill
   `<linguaggio>-scaffold` per linguaggio (prima **Python**: il primo
   progetto sarà la versione LangGraph; poi Elixir, C dalla skill
   esistente). Cartelle, toolchain, task runner, git, GHA e CI: compiti
   deterministici, quindi tool scritti in Python (più leggibile di bash)
   che la skill collega (`git init`, `make build`, …). ford scaffolda poi
   solo l'architettura.
4. **hughes prima di ford, solo dominio.** Legge la shopping list, non il
   codice; l'esito è la spec: entità, value object, segnali o eventi che si
   scambiano, relazioni, invarianti, vincoli di sistema, proprietà espresse
   sulle operazioni di dominio. Un passaggio solo; `adl-spec` tolta. Un
   segnale verso hughes quando il dominio cambia (simmetrico di
   `INTERFACE_CHANGE_REQUEST`).
5. **ford: architettura, interfacce e contratti.** Decide quali elementi
   sono interfacce (behaviour, protocol, classe astratta) e quali classi
   concrete, firme, errori, direzione delle dipendenze, e per ogni
   componente gli id della spec che realizza. `INTERFACE_CHANGE_REQUEST`
   torna solo a ford.
6. **Il modello comune tra hughes e ford.** Serve una lingua condivisa per
   il modello (entità, value object, segnali): hughes lo definisce, ford lo
   usa per il contenuto delle interfacce. L'ADL probabilmente non basta:
   valutare un formato YAML come la spec, o un'estensione della spec.
   **Id condivisi**: gli id della spec citati nell'ADL e nel codice (come
   commenti, anche temporanei fino alla PR) danno un piccolo database
   relazionale su file; un checker (`spec-check` esteso) verifica che ogni
   id sia realizzato da un componente e coperto da un test.
7. **unclebob e la mappa dei test.**
   - Il sapere legato al linguaggio (StreamData, Hypothesis, Mox,
     librerie di test) passa da `domain-spec` e dagli agenti alla
     `<linguaggio>-handbook`.
   - unclebob riceve l'elenco completo di componenti e interfacce: sa cosa
     può sostituire con un doppio (solo le interfacce dichiarate), da dove
     a dove testare, da dove cominciare.
   - L'ADL e le interfacce sono la mappa della struttura dei test; la spec
     è la mappa di vincoli e proprietà.
   - Ordine: per componente, dal particolare al generale. Unit test del
     componente, poi integrazione verso l'interfaccia più esterna, fino al
     test di integrazione completo. I test di integrazione verificano
     l'input e l'output alle interfacce (aderenza ai contratti), non di
     nuovo il comportamento; test di contratto condivisi tra doppio e
     implementazione reale; i vincoli di sistema della spec verificati nel
     test completo.
8. **minsky, nuovo agente**: scrive i file di istruzioni del progetto a
   fine workflow, al posto di kent. `AGENTS.md` sempre; `CLAUDE.md` solo
   quando il workflow gira su Claude Code. Riceve i fatti raccolti
   (shopping list, `open_points`, comandi che hanno funzionato), mostra il
   diff, committa `docs(agents)`. Nome: Marvin Minsky, *The Society of
   Mind* (la mente come società di agenti) e le K-line (la memoria che
   riattiva uno stato mentale: lo stato di partenza di un agente).

## Ricerche

- **Un DSL nostro per gli agenti**, che unisca modello di dominio, ADL e
  spec con un unico sistema di id; esistono DSL pensati per interagire con
  gli agenti, da studiare.
- **Copilot su questa macchina per i benchmark** Claude contro Copilot.
  Vincolo: l'account Copilot aziendale è legato all'account GitHub
  personale, i token aziendali non si possono usare da un computer diverso
  da quello aziendale, e lì non si può installare Claude Code. Da capire se
  esiste una strada praticabile (un piano Copilot personale?).
- **Ragionamenti di Opus**: nei transcript locali di Claude Code
  (`~/.claude/projects/*/*.jsonl`) i blocchi `thinking` sono salvati vuoti,
  con la sola firma; restano leggibili messaggi e chiamate ai tool. Da
  verificare cosa salva Copilot in `~/.copilot/session-state/<id>/`.

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
