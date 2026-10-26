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

- **Il workflow Claude completo** (16 ottobre, sera), secondo le decisioni
  della sezione "Refactor":
  - tool in `common/bin` su una libreria Python comune (`common/lib/minime`):
    `toolchain` (driver Elixir e Python, `toolchain.yaml`), `git-read`,
    `shopping-list`, `session-state`, `flow-log`, `audit-log`,
    `events-query`, `minime-migrate`, `adl-graph`, `scaffold` (template
    Python e C); `linus hunks` e `stage-hunks`; `spec-check` con la spec
    versione 2, `realization` e `coverage`;
  - guard: in Bash solo i tool dell'agente, niente sostituzioni di comando
    né heredoc non quotate, letture limitate per hughes, approvazione senza
    prompt dei tool di sola lettura (commit, scaffold, migrazioni e
    `check --fix` chiedono ancora); hook `flow_hook.py` per il log;
  - agenti: kent, hughes, ford, unclebob, martin, simon, joshua, argyris,
    marvin, linus;
  - skill: `domain-model` (spec v2 e mappa dei componenti), `python-handbook`,
    `elixir-handbook` riscritta sui tool, `python-scaffold`, `c-scaffold`
    (al posto di `claude/skills/scaffold`), `workflow-files`; `adl-reverse`
    usa `adl-graph`;
  - segnali nuovi: `DOMAIN_CHANGE_REQUEST`, `FORD_AS_IS`, `MARVIN_DONE`,
    `AUDIT_OK`; `FORD_DONE` con campi facoltativi per la mappa;
  - Makefile: libreria in `~/.local/share/minime/lib`, `make test`,
    `structurizr-install`, `claude-cli`, `copilot-cli`; `make update` usa
    `minime-migrate`;
  - `tests/`: 21 test su guard e tool, tutti verdi.

## Decisione del 17 ottobre: i file del flusso si versionano su Claude Code

Su Copilot `.sources/`, `.documentation/` e `toolchain.yaml` restano fuori
da git (codice aziendale condiviso con colleghi ignari dell'esperimento). Su
Claude Code, dove ci saranno solo strumenti personali e per lo più open
source, si versionano:

- kent li committa (`docs(workflow): …`, fase `other`) solo tra un'unità e
  l'altra: prima del primo unclebob, dopo ogni `MARTIN_DONE`, alla fine; il
  guard gli permette `linus stage/commit` solo su quei percorsi;
- `linus` li rifiuta solo su Copilot; `linus squash` ignora le loro
  modifiche non in stage;
- `minime-migrate` tocca il gitignore globale solo con
  `--ignore-workflow-files` (lo passa `make update`, lato Copilot);
- marvin può indicarli in `AGENTS.md`.
- La versione LangGraph deciderà a runtime, con un flag.

## Da fare

### Fatto il 21-22 ottobre (quattro sessioni di prova in `/tmp/minime-py`)

Un progetto Python `metrics-server` in una cartella di un repository
fittizio, guidato da qui con la skill `kent-loop`. Corretto strada facendo:

- **Ruoli.** kent è analista e orchestratore: chiede all'utente solo il
  perimetro (con l'health check fisso per un servizio) e lascia il dominio a
  hughes e la tecnologia a ford, come domande aperte con proprietario nella
  shopping list. Ogni scaffold è di ford (`<linguaggio>-scaffold`,
  `scaffold verify`/`commit`, poi `container-scaffold` dopo `adl-scaffold`);
  kent lancia solo `scaffold init` in una cartella vuota. Ogni riga di
  codice è di unclebob, **harness dei test compreso**: test-first, un pezzo
  entra con il primo red che ne ha bisogno; ford scrive solo le fitness
  function.
- **martin**: audit, squash, revisione tecnica, rapporto dei findings in
  `MARTIN_DONE`; nessuna domanda sui findings, nessuna revisione guidata.
  L'utente rivede da solo, dà a kent le correzioni (fixup tramite
  unclebob, ford o hughes) e chiude l'unità con un comando esplicito.
- **Tool.** `scaffold init` e `scaffold commit`; CI di un progetto in
  cartella alla radice, con `working-directory` e filtro `paths`;
  `toolchain.yaml` alla radice con `project: <cartella>` (la Q9: `toolchain`
  e `adl-graph` lavorano sulla cartella dalla radice); ogni `toolchain.yaml`
  è un file del flusso.
- **Guard.** `ls` e `cat` a kent, `date` a simon, `toolchain check` a ford.
- **Agenti.** La risposta inoltrata da kent è dell'utente; una delega a
  parole ("per il resto accetto le tue raccomandazioni") conferma i passi
  che nomina, e l'agente riporta quali scelte sono sue; simon parte dopo la
  shopping list; joshua non registra i rifiuti del guard già superati né le
  deleghe.
- **Copilot**: la revisione guidata dall'utente, la divisione delle domande,
  l'ordine di simon e la fiducia nella relay sono in #17 (mergiata).

L'ultima sessione è arrivata a fine ford: scaffold, container, interfacce e
mappa verificati (build, ruff, mypy strict, test, `docker build`).

### Quinta sessione (22 ottobre, `kent-loop-sandbox`, interrotta)

Greenfield `metrics-server` in una cartella (FastAPI, psycopg, Postgres,
testcontainers), con la delega sulle raccomandazioni fin dal primo messaggio.

- **Andato bene**: shopping list con le domande divise tra hughes (5) e
  ford (5); hughes in un turno; ford con scaffold `--dir` (CI alla radice
  filtrata, `toolchain.yaml` alla radice più quello della cartella, voluto),
  8 commit di architettura (quattro componenti: `samples`, `storage`,
  `http`, `app`), fitness function e `spec-check` ok; kent committa i file
  del flusso (`docs(workflow)`) prima di unclebob; unclebob su `samples`:
  75 commit rosso/verde/refactor, 25 test quasi tutti property-based, tre
  caratterizzazioni fatte bene, 34/34 verdi, ruff e mypy strict puliti.
  Nessun segnale `ok: false` in tutta la sessione.
- **Da guardare**:
  - ford ha cercato `GITHUB_REPO` su tutto il disco (`rg … /`, rifiutato):
    `python-scaffold` non dice da dove viene il valore;
  - ford non sapeva la versione di uv installata e ha fissato a caso il
    tag dell'immagine (`0.9`, qui c'è la 0.13): un `toolchain`/`scaffold`
    che la stampi;
  - l'interfaccia `SampleStore` sta nel package di `samples`, non in
    quello di `storage`: da rivedere nella mappa;
  - hughes ha scelto di sovrascrivere i duplicati (nome e timestamp
    uguali) invece di rifiutarli, sotto delega: una scelta di dominio
    rilevante passata senza che l'utente la vedesse;
  - unclebob prevede di spostare le strategie Hypothesis in
    `tests/support/` per `storage`: il caso del punto 2 qui sotto.
- **Costo e limiti**: l'unità `samples` da sola è costata circa 8 dollari
  (88 mila token di output di unclebob in 23 minuti, 1491 righe di
  transcript), 15,7 dollari la sessione fino a martin. Il limite di
  sessione dell'abbonamento è scattato due volte (12:57, reset 13:30;
  14:34, reset 19:00), la seconda un minuto dopo il lancio di martin: kent
  e i suoi sei subagent Opus (joshua e simon sempre attivi) consumano la
  stessa quota della sessione interattiva che li guida. Ridurre: unità più
  piccole, joshua e simon meno chiacchieroni, un modello più leggero per
  joshua e simon.
- **Analisi dei costi** (dai transcript, token per categoria pesati 1 input,
  1,25 scrittura in cache, 0,1 lettura dalla cache, 5 output; joshua gira
  già su Sonnet, quindi la sua quota è sovrastimata): unclebob 50%, joshua
  20%, ford 13%, kent 9%, simon 6%, martin e hughes 3%. Per categoria:
  letture dalla cache 58%, scritture in cache 24%, output 18%.
  - unclebob: 231 chiamate, circa 9 per ciclo, ognuna rilegge tutto il
    contesto (da 27 mila a 178 mila token, mediana 109 mila): le sole
    letture dalla cache di unclebob sono circa il 40% della sessione. Leve:
    un unclebob nuovo ogni gruppo di cicli (il contesto resta piccolo);
    `linus check-message` prima di ogni commit (75 chiamate) è ridondante
    quando i commit non chiedono conferma, perché `linus commit` valida già
    il messaggio; 19 refactor su 25 erano commit vuoti con il verdetto (due
    chiamate ciascuno).
  - joshua: 534 mila token scritti in cache in 59 chiamate. Tra un AUDIT e
    l'altro la cache scade (5 minuti) e ogni ripresa riscrive tutto il
    contesto. Leve: audit per unità invece che per turno, o un joshua nuovo
    per audit.
- **Persa al riavvio**: il repository di prova era in `/tmp/kent-loop`;
  restano solo i transcript in
  `~/.claude/projects/-tmp-kent-loop-kent-loop-sandbox/`. Spostare il
  default di `KENT_LOOP` fuori da `/tmp` (per esempio `~/.cache/kent-loop`).

### Il nuovo flusso delle unità (23 ottobre, implementato, mai provato)

Deciso dopo l'analisi dei costi della quinta sessione. L'ipotesi
dell'esperimento: problemi piccoli e iterazioni obbligate danno codice
migliore a costo minore; il refactor però vuole la conoscenza del
componente e del flusso intero, quindi lo fa un agente a sé, una volta per
unità.

- **unclebob** (workflow): cicli di un `test:` e un `feat:`, niente
  refactor. Il `test:` non è mai vuoto; il `feat:` vuoto è una
  caratterizzazione (il test passava già: la saturazione dei casi), provata
  rompendo l'asserzione, registrata con `flow-log` e riportata in
  `UNCLEBOB_DONE` (`characterisations`). Niente più sessioni di correzione.
- **unclebob-pair** (interattivo, il comando `unclebob`): rosso, verde, blu;
  il blu misura come martin e fa due commit, `refactor(test)` e
  `refactor(<scope>)`; mostra a schermo ogni riga che aggiunge o cambia;
  `check-message` resta.
- **martin** (Martin Fowler, *Refactoring*), riscritto: `unit-audit order`
  e le violazioni TDD in `audit-log` (ID `M-`); il tempo zero (complessità in
  tempo e spazio, SOLID, idiomaticità, leggibilità, righe di produzione,
  test e harness, durata dei test lanciati due volte per i flaky); il
  refactor dei test e di tutto l'harness che tocca il componente con il
  codice fermo, e se righe dell'harness o durate peggiorano chiede
  all'utente con i numeri; il refactor del codice con i test come punto
  stabile, la complessità uguale o migliore (benchmark temporanei in
  `benchmarks/`, committati come `benchmark(<scope>)`, e se peggiora chiede);
  subito dopo, nello stesso turno, `linus squash` dell'unità (i commit di
  unclebob e i suoi; i `benchmark` scartati) e `UNIT_SQUASHED`, che porta
  anche il report (misure, violazioni, findings). `REFACTOR_DONE` non c'è
  più (26 ottobre).
- **kent**: unclebob → martin (refactor e squash) → stop. **Niente revisione
  con l'utente in sessione** (26 ottobre: costa token, l'utente la fa a
  mano): kent mostra il report di martin e passa il controllo; l'utente
  rivede il commit squashato da solo, con i suoi fixup, e dice a kent di
  andare avanti. Il flusso funzionale va allo stesso modo, alla fine, poi
  marvin. I fixup dell'utente restano fino al push (conservano il segnale
  di cosa sbagliano gli agenti).
- **linus** fa solo i commit su Claude Code: `--phase` facoltativa e solo
  registrata, nessun controllo di ordine né di file per fase, `test:` mai
  vuoto, tipo `benchmark`, `squash` che accetta `refactor(test)` e scarta i
  `benchmark`. Su Copilot tutto come prima (ramo su `COAUTHOR`).
- **Tool**: `unit-audit` (`order`, `lines`), `toolchain test --durations`,
  `toolchain bench`.
- **Log**: in `~/.local/state/minime/<repository>/` su Claude Code
  (`MINIME_STATE_DIR` per spostarli; Copilot resta su `/tmp`), pulizia una
  volta al giorno all'avvio (30 giorni, 100 MB in tutto). Due file:
  `kent-events.jsonl` (ogni turno con segnale, uso del modello per turno:
  chiamate, token di input, cache e output, modello; e cosa serve a
  rieseguirlo: branch, HEAD, sessione, prompt di lancio, transcript) e
  `kent-errors.jsonl` (rifiuti del guard, segnali falliti, violazioni di
  joshua e martin, `handled` di argyris). `joshua.log` e `kent-guard.jsonl`
  non ci sono più (`audit-log` migra il vecchio log). `kent-loop` in
  `~/.cache/kent-loop`.
- **`/save-session`** (`claude/skills/save-session`): kent scrive il suo
  stato con `session-state` prima di un'interruzione.
- **argyris e i log per repository**: argyris gira in `~/code/minime`, i
  log di un progetto stanno nella cartella di quel progetto. `audit-log
  repos` elenca i repository con violazioni aperte; `--repo <nome>` (o il
  percorso di una cartella, come quella di kent-loop) su `audit-log` ed
  `events-query` sceglie quale leggere. argyris resta il correttore delle
  sessioni vere (i progetti personali, il flusso deterministico, Copilot);
  kent-loop quello delle prove. Proposta aperta: kent-loop registra con
  `audit-log append` i problemi che trova e li chiude con `handled`, così il
  registro è uno solo.
- simon su Sonnet; `check-message` tolto dal modo workflow di unclebob.

### Prossimi passi

1. **Niente più sessioni di prova con `kent-loop`** (decisione del 26
   ottobre): il flusso nuovo si prova nelle sessioni vere, e argyris
   corregge dalle violazioni registrate. I costi si confrontano con la
   quinta sessione dalle righe `usage` di `kent-events.jsonl`.
2. **Da verificare nella prima sessione vera**: che `/save-session` si
   invochi dentro la sessione di kent; che il payload di `SubagentStop`
   porti `cwd` e `session_id`; che `toolchain test --durations` funzioni con
   i comandi personalizzati di `toolchain.yaml` (le opzioni passano come
   percorsi); che martin faccia lo squash nello stesso turno del refactor.
3. **`kent-loop` come modalità di lavoro**: l'agente principale guida kent
   headless e corregge minime da sé, un argyris migliorato. Per ora un
   esperimento; decidere se diventa il default e cosa resta ad argyris.
4. **Copilot, punto 19** del suo `NEXT_ITERATION.md` (harness a unclebob,
   deleghe, una correzione per turno): una PR a parte quando l'utente lo
   chiede. Lo scaffold a ford e `toolchain` con `project:` aspettano che il
   kent di Copilot scaffoldi.
5. **Riprendere la sessione su `deterministic-workflow`**: il progetto va in
   `deterministic-kent/`; la sezione "Who" della shopping list ora segue i
   ruoli nuovi (hughes, poi ford scaffolda con `scaffold python --dir
   deterministic-kent`, che scrive il `toolchain.yaml` alla radice con
   `project:` e la CI alla radice). Il gitignore globale di questa macchina
   non esclude più `.sources/`, `.documentation/` e `toolchain.yaml`: la
   shopping list è committata.
6. **Fatto (22 ottobre)**: `tests/test_signal_stop.py`, handback e
   `last_assistant_message`, blocco, thread principale. Dopo un handback
   rifiutato l'hook registra due righe con lo stesso `agent_id` (`ok:
   false`, poi `ok: true`): joshua le audita come un turno solo.
7. **`structurizr-cli`**: kent passa all'utente `make structurizr-install`
   quando simon non lo trova; decidere se va bene così.
8. **Fatto (22 ottobre)**: `python-handbook` copre `minime` (la skill guarda
   il nome del repository, non la cartella del progetto) e
   `kent-loop-sandbox`, il nuovo nome del repository di prova di
   `kent-loop`, che prima nessuna handbook copriva.
9. **PATH**: `make install` avverte che `~/.local/bin` non è nel PATH della
   shell di `make`; controllare sull'altro PC.
10. **C**: un driver C per `toolchain` (CMake + Make) e una `c-handbook`.
11. **Le citazioni `spec:` nel codice di produzione**: chi le toglie prima
    della PR (martin in review? un tool?).
12. **Autonomia dei commit**: oggi chiedono conferma (in `kent-loop` li
    approva l'allowlist). Se serve, un livello configurabile, come
    `AUTONOMY_LINUS` su Copilot.
13. **Versione LangGraph**, con metriche comuni per il confronto.

## Refactor dell'architettura degli agenti (decisioni del 16 ottobre)

Da fare sul lato Claude; Copilot lo applica dal suo `NEXT_ITERATION.md`.

1. **Tool al posto di bash.** Nessun agente lancia bash liberamente: un
   tool per ogni compito, l'agente resta agnostico su come si fa. Motivi:
   Copilot inventa ogni volta script nuovi per le stesse cose, e un tool
   stabile è un livello di sicurezza in più. Forma decisa: comandi in
   `common/bin` (Python, condivisi con Copilot) e il guard che in Bash
   permette solo quelli, per agente (un server MCP eventualmente dopo).
   Ricerca e lettura con i tool nativi (Read, Grep, Glob: già su ripgrep).
   Tool approvati:
   - `flow-log`: una riga nel log delle attività (lo usano anche gli hook);
   - `shopping-list`: legge e scrive la shopping list del branch;
   - `minime-migrate`: porta file e cartelle legacy alla struttura attuale
     (sostituisce il passo di kent e la parte progetti di `make update`;
     ogni cambio futuro di struttura si aggiunge lì);
   - `tests` (un test, file, file del commit, branch), `build`,
     `static-checks`: i comandi del linguaggio stanno nelle handbook e nei
     loro driver, non negli agenti;
   - `git-read` (log, show, diff, blame, status) e `linus` con un
     sottocomando per lo stage di parte di un file (niente patch a mano);
   - `spec-check`, `adl-graph` (gli script di `adl-reverse`);
   - `structurizr-cli` installata da un target make, non dal container;
   - `scaffold <linguaggio>` e i suoi passi (`git init`, build, CI…);
   - `session-state` per la ripresa di kent;
   - `events-query` per joshua;
   - `audit-log`: joshua aggiunge, argyris segna `HANDLED` e archivia
     (niente `rm`);
   - `signal-check` resta negli hook (`SubagentStop`), non è un tool.
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
     implementazione reale (in Elixir lo fa già Hammox; altrove va
     costruito); ogni proprietà della spec testata nello strato più piccolo
     della cipolla in cui può funzionare, spesso ma non sempre il flusso
     completo.
8. **marvin, nuovo agente**: scrive i file di istruzioni del progetto a
   fine workflow, al posto di kent. `AGENTS.md` sempre; `CLAUDE.md` solo
   quando il workflow gira su Claude Code. Riceve i fatti raccolti
   (shopping list, `open_points`, comandi che hanno funzionato), mostra il
   diff, committa `docs(agents)`. Nome: marvin, da Marvin Minsky, *The Society of
   Mind* (la mente come società di agenti) e le K-line (la memoria che
   riattiva uno stato mentale: lo stato di partenza di un agente).

9. **`toolchain.yaml`** nella radice del progetto: linguaggio, prefisso del
   container, comandi personalizzati; lo leggono i tool `toolchain`. Non
   versionato (gitignore globale, come `.sources/` e `.documentation/`):
   marvin non lo cita mai in `AGENTS.md`. Documentato nel README.
10. **Skill sui file di supporto del flusso** (`.sources/`,
    `.documentation/`, `toolchain.yaml`, i log in `/tmp`): chi scrive cosa,
    perché non sono versionati (su Copilot è obbligato: il flusso è un
    esperimento personale su codice aziendale; avrebbe senso versionarli
    solo se altri adottassero lo strumento).

## Ricerche

- **Il DSL del modello di dominio.** Provvisorio: la spec versione 2
  (`domain-model`: entità e value object, eventi, relazioni, operazioni,
  proprietà, con id condivisi). Da confrontare con DSL esistenti: CML di
  Context Mapper (DDD: bounded context, aggregate, entity, value object,
  domain event), LinkML (schema in YAML).
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

## Verificato (16 ottobre, Claude Code 2.1.301, `claude -p --agent kent` su un progetto di prova)

- Gli hook nel frontmatter valgono anche per l'agente lanciato come thread
  principale: il guard di kent ha rifiutato `git`, `cat`, `toolchain test`,
  la sostituzione di comando, `linus commit` e una Write sul codice, e ha
  lasciato passare i suoi tool.
- **Ma gli hook del thread principale scattano anche sulle chiamate dei suoi
  subagent** (nel log comparivano righe `[kent] [hughes] …`): il guard di
  kent avrebbe bloccato i commit di unclebob. Corretto: guard e log
  ignorano le chiamate di un altro agente (`agent_type` nel payload).
  Riprovato: hughes scrive `.sources/spec.yaml` senza interferenze.
- `Stop` nel frontmatter di un agente utente funziona come `SubagentStop`,
  senza finestra di fiducia: hughes ha chiuso senza segnale, l'hook gli ha
  rimandato il turno e ha richiuso con un `ASK_USER` valido
  (`/tmp/kent-events.jsonl`: `ok: false`, poi `ok: true`).
- Il guard di hughes blocca la lettura del codice (Read su `src/`) e `rg`.
- **In questa versione non esistono i tool Grep e Glob**, nemmeno in una
  sessione normale: la ricerca passa da `rg` (aggiunto ai tool comuni, senza
  `--pre` e `--search-zip`).
- In `claude -p` non c'è AskUserQuestion e le Write chiedono un permesso che
  nessuno può dare (serve `--permission-mode acceptEdits`).

## Da verificare

- Una sessione interattiva vera: la relay con AskUserQuestion e
  SendMessage, i prompt dei permessi sui commit.
- Se `skills:` nel frontmatter precarica davvero le skill.
- Il limite di 8 blocchi consecutivi degli Stop hook vale per
  `SubagentStop`?
- `SendMessage` a un subagent ancora al lavoro: in coda o rifiutato? E a uno
  la cui sessione è finita da tempo (ford per un `INTERFACE_CHANGE_REQUEST`)?
- I transcript dei subagent: il formato che `events-query transcript` legge
  (righe con `message.content`) va confermato su un transcript vero.
- `mix test` con percorsi dalla radice di un'umbrella (si interrompe con un errore).
- Il guard nel modo interattivo di unclebob: che i soli tool bastino.
- simon su Copilot: il file "in un altro DSL" che l'utente non riconosce
  potrebbe essere `workspace.json`, che Structurizr Lite genera accanto a
  `workspace.dsl` quando lo si apre. Il nuovo simon scrive solo i suoi due
  file e mette `architecture.md` per primo.
