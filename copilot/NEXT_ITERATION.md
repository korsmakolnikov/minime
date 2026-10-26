# Prossima iterazione del workflow Copilot

Passaggio di consegne del 16 ottobre 2026. Il lato Copilot (`copilot/`) lo
porta avanti Copilot; il porting dello stesso workflow su Claude Code
procede a parte in `claude/` e non tocca questa cartella. Tenete separate le
due cartelle: una modifica a un agente qui non va replicata in `claude/`, e
viceversa.

## Stato attuale (su `master`)

- Agenti: `kent` (orchestratore), `hughes`, `ford`, `unclebob`, `martin`,
  `linus`, `joshua`, `argyris`, `simon`. Nomi e "perché" nel README.
- Input del workflow in `.sources/` (ADL, `spec.yaml`, `shopping_lists/`);
  output in `.documentation/<branch>/` (simon).
- Ogni agente committa da sé con il comando `linus` (FEATURE_DRIVEN,
  CODE_REVIEW_DRIVEN, STATIC_CODE_FIX_DRIVEN); l'agente linus resta per i
  commit fuori dal workflow. argyris gira in una sessione sua; kent non si
  riavvia e non aspetta joshua, che fa l'audit per blocchi.
- **Ultimo arrivato: segnali in JSON.** Ogni blocco che chiude un turno
  (`ASK_USER`, `HUGHES_DONE`, `FORD_DONE`, `INTERFACE_CHANGE_REQUEST`,
  `UNCLEBOB_DONE`, `TDD_VIOLATIONS`, `REVIEW_CHANGES`, `MARTIN_DONE`,
  `SIMON_UPDATED`, `AUDIT_VIOLATIONS`) ha le righe marcatore di sempre e un
  oggetto JSON in mezzo, con uno schema in `common/signals/`. Il comando
  `signal-check` (`common/bin/`, senza dipendenze) lo valida: sottoinsieme
  di JSON Schema, keyword sconosciute rifiutate, un solo blocco in fondo,
  niente segnaposto `<…>`. Gli agenti lo usano prima di chiudere il turno,
  joshua lo riusa su ogni blocco preso da `events.jsonl` (violazione
  `major`), kent risponde `SIGNAL_INVALID` a un blocco che non sa leggere.

- **Comandi comuni.** `linus`, `spec-check`, `signal-check` e gli schemi dei
  segnali stanno in `common/`, condivisi con il workflow Claude Code:
  `make common-install` (chiamato da `make copilot-install`) li installa in
  `~/.local/bin` e `~/.local/share/minime/signals`. linus sceglie il
  trailer da `LINUS_COAUTHOR` (`copilot` o `claude`); senza, usa `claude`
  dentro Claude Code (`CLAUDECODE=1`) e `copilot` altrimenti. Una modifica
  a `common/` vale per tutti e due i lati: va provata su entrambi. Lo
  stesso per le skill `adl-*`, `domain-spec` ed `elixir-style`, ora in
  `common/skills/`: argyris e `minime-sync` le rispecchiano lì.

## Da fare sull'altro PC

```sh
cd ~/code/minime && git pull && make copilot-install
```

(`make update` solo se quella macchina non ha ancora fatto la migrazione dei
vecchi nomi.) Senza l'installazione gli agenti restano al formato vecchio e
`signal-check` non è nel `PATH`.

Poi i **file di configurazione** (README, "Configuration"), che il repository
non contiene più: in `~/.config/minime/` scrivi a mano `large-systems.toml`
(il sistema grande e il suo percorso), `projects.toml` (`elixir = [...]`) e
`aliases.toml` (il wrapper dei container per `docker` e `docker compose`,
con il suo container come `context` e i suoi sottocomandi di sola lettura).
`~/.bash_copilot` non viene sovrascritto: `COPILOT_CONTAINERS` resta com'è.
Verifica con `minime-config large-system` nel repository del sistema e con
`minime-config aliases`.

## Da verificare nelle prime sessioni vere

Segnali (nuovi, mai provati):

- Che gli agenti chiamino davvero `signal-check --expect …` con il blocco in
  un heredoc citato prima di chiudere il turno, e che l'hook lo approvi.
- **Il comando `jq` di joshua.** Il file dice di prendere il messaggio finale
  di ogni agente da `events.jsonl` e passarlo a `signal-check` con `jq -r`,
  ma il percorso jq non è scritto da nessuna parte: ricavarlo dalla struttura
  vera di `events.jsonl` e scriverlo in `joshua.agent.md`.
- Che kent mappi `choices` e `default` del JSON sulle opzioni di `ask_user`.
- Quanto spesso serve `SIGNAL_INVALID`.
- Se l'hook `agentStop` di Copilot riceve il messaggio finale dell'agente e
  può rifiutare la fine del turno: sarebbe la validazione deterministica dei
  segnali senza orchestratore. Oggi `agentStop` manda solo la notifica.

Dalle iterazioni precedenti, ancora aperte:

- I prompt di unclebob: la regola "niente `cd` diretto" e `--add-dir` della
  root del repo bastano?
- I prompt di joshua: basta `--add-dir ~/.copilot`?
- `/tmp/copilot-hook-asks.jsonl`: ogni prompt passato dall'hook all'utente,
  con il motivo. Un prompt che lì non compare è un prompt di accesso ai
  percorsi.
- simon, l'audit di martin come checkpoint e le fixup dell'analisi statica
  non sono ancora stati provati in una sessione vera.
- argyris nella sua sessione: lettura di `/tmp/joshua.log`, righe `HANDLED`,
  archiviazione in `/tmp/joshua.log.prev`.
- joshua che registra da sé i propri prompt (da `events.jsonl`).
- Le fixup della review committate da unclebob e ford sul commit dell'unità;
  martin che le rivede all'iterazione successiva.
- ford e unclebob che committano con il comando (prompt e messaggi leggibili).
- Che Copilot CLI accetti `model: claude-sonnet-5.5` nel frontmatter.
- Che un `write_agent` a joshua occupato venga messo in coda e non rifiutato.

## Prossimi passi

1. Le verifiche sopra, a partire dal comando `jq` di joshua.
2. **Orchestratore in codice** (facoltativo per Copilot). L'anello più debole
   è kent: un modello che segue una procedura di quasi 400 righe. Una
   macchina a stati (Python, LangGraph o simili) che guida gli agenti in
   modalità non interattiva (`copilot -p`) renderebbe deterministici
   l'ordine delle fasi e la validazione dei segnali. Il porting su Claude
   Code segue un'altra strada (hook `SubagentStop`), quindi qui la scelta è
   libera.
3. **charity** (Datadog con `pup`), agente su richiesta e in sola lettura:
   - shopping list: errori, latenze e volumi dell'area toccata;
   - hughes: vincoli e proprietà dai dati veri;
   - martin: quali errori delle funzioni chiamate si verificano davvero.

   Cautele: nei trace possono esserci dati personali; `pup` va in rete e
   serve un elenco di sottocomandi di sola lettura approvati dall'hook, come
   la whitelist dei container. Riusare la skill
   `datadog-experiment-downloader`. Il ciclo con deploy e confronto resta
   fuori: il workflow si ferma al commit.
4. **Test e controlli statici fuori dai cicli** (fatto sul lato Claude, da
   allineare qui: `claude/agents/unclebob.md`). L'utente ha già una versione
   locale per il green su un branch dell'altra macchina: partire da quella.
   - Mai la suite completa (la lancia la CI), nemmeno sui sistemi grandi: la tabella
     "Large systems" sparisce. Dopo ogni commit di ciclo (green, regression,
     refactor) solo i test che includono i file del commit; a ogni punto di
     chiusura (fine unità, fine sessione di correzione) i test correlati al
     branch.
   - Formatter, linter e type checker (dialyzer) solo ai punti di chiusura,
     mai nel ciclo né prima di red e green, tramite la skill del linguaggio
     `common/skills/elixir-handbook` (campi `projects` e `tools`).
     Nella sessione di correzione, dopo l'ultima modifica di review.
   - Il refactor del ciclo copre i due moduli del ciclo per intero, helper
     privati del modulo di test compresi; il materiale di test condiviso
     (support, factory, harness) non si tocca nel ciclo: lo rivede martin
     con l'unità, e va detto esplicitamente in martin.
   - joshua: aggiornare le regole sui controlli a ogni ciclo e sulla suite.
   - Da decidere con l'utente: se i controlli statici li lancia martin in
     review invece di unclebob.
5. **`elixir-handbook` al posto di `elixir-style`** (fatto nei riferimenti di
   unclebob e martin). Toglierla dalla copia viva prima del prossimo
   `minime-sync`, che altrimenti la riporterebbe in `copilot/skills/`:
   `rm -rf ~/.copilot/skills/elixir-style && make copilot-install`. Il resto
   degli agenti può usare la handbook per test e controlli invece dei
   comandi scritti a mano.
6. **kent mantiene `AGENTS.md` e `CLAUDE.md`** (fatto, "The project's agent
   instructions"): li raccoglie nella shopping list, li propone a fine
   workflow, li committa con `linus commit --phase other`. Da verificare in
   una sessione vera; gli altri agenti segnalano invece di modificarli (da
   scrivere in ford, unclebob, martin).
7. **Scaffolding di un progetto nuovo**: kent non sa crearne uno. Skill per
   Elixir, Python e C (CMake + Make); dettagli in `claude/NEXT_ITERATION.md`.
8. **simon da rivedere**: il `workspace.dsl` (C4) è giusto, ma scrive anche
   un altro file non ancora identificato e non scrive `architecture.md`, con
   i sequence diagram Mermaid delle iterazioni e i class diagram, che le sue
   istruzioni già chiedono. Guardare una `.documentation/<branch>/` vera.
9. **`make clean`**: rimuove tutto ciò che i target installano (lista
   `INSTALLED` nel Makefile, da tenere aggiornata; `make clean-check` la
   verifica). `make clean && make install-copilot` riparte da zero, tenendo
   `~/.bash_copilot`. Sostituisce anche il `rm -rf` di `elixir-style` del
   punto 5.
10. **Refactor dell'architettura degli agenti** (decisioni del 16 ottobre,
    dettagli in `claude/NEXT_ITERATION.md`, "Refactor dell'architettura
    degli agenti"): applicarlo anche qui, dopo il lato Claude; Claude farà
    la review del lavoro. In breve:
    - nessun agente lancia bash: un tool per ogni compito (forma da
      decidere);
    - kent senza bash: `adl-reverse` a ford, niente test, shopping list
      con edit, log dagli hook, cartelle legacy in `make update`,
      scaffolding con le skill `<linguaggio>-scaffold` (prima Python);
    - hughes prima di ford, solo dominio, dalla shopping list e senza
      codice; ford decide interfacce, classi concrete e contratti e lega
      i componenti agli id della spec; un modello comune tra i due;
    - unclebob con l'elenco completo di componenti e interfacce, sapere
      del linguaggio nella handbook, test dal componente all'integrazione
      completa, integrazione su input e output alle interfacce;
    - nuovo agente **marvin** per `AGENTS.md` (sempre) e `CLAUDE.md` (solo
      su Claude Code), al posto di kent.
11. **Cosa c'è già in `common/` per il refactor** (fatto sul lato Claude,
    16 ottobre): i tool `toolchain`, `git-read`, `shopping-list`,
    `session-state`, `flow-log`, `audit-log`, `events-query`,
    `minime-migrate`, `adl-graph`, `scaffold`, `linus hunks`/`stage-hunks`,
    `spec-check` versione 2; le skill `domain-model`, `python-handbook`,
    `python-scaffold`, `c-scaffold`, `workflow-files`, `elixir-handbook`
    riscritta sui tool; i segnali `DOMAIN_CHANGE_REQUEST`, `FORD_AS_IS`,
    `MARVIN_DONE`, `AUDIT_OK`. Gli agenti Copilot non li usano ancora:
    `domain-spec` (spec versione 1) e i segnali di prima restano validi
    finché il refactor non è fatto. `audit-log` scrive le righe `HANDLED`
    nello stesso formato di argyris. Riferimento: `claude/agents/` e
    `claude/hooks/guard.py` (la tabella dei tool per agente).
12. **File del flusso** (17 ottobre): su Copilot restano non versionati;
    `linus` ora rifiuta anche `toolchain.yaml` quando gira lì, e `make
    update` aggiunge al gitignore globale anche `toolchain.yaml`
    (`minime-migrate --ignore-workflow-files`). Su Claude Code si versionano:
    non copiare quella parte nel refactor.
13. **`linus branch <name>`** (21 ottobre, lato Claude): passa al branch e lo
    crea da HEAD se non esiste; rifiuta `master`, `main` e i nomi non validi.
    Il kent di Claude lo lancia a inizio sessione quando è sul branch base,
    così l'utente non cambia branch a mano. Il kent di Copilot può fare lo
    stesso: va scritto nel suo file insieme al permesso nell'hook.

14. **`scaffold commit`** (21 ottobre, lato Claude): il comando comune
    `scaffold` committa lo scaffold con `linus` (`chore: scaffold the
    project`, con il lock file), dopo `scaffold verify` e sul branch di
    lavoro, e lascia fuori `.sources/`, `.documentation/` e
    `toolchain.yaml`: la regola di Copilot resta intatta. Le skill
    `python-scaffold` e `c-scaffold` lo dicono; quando il kent di Copilot
    scaffolderà (punto 7), lo lancia invece di lasciare il commit
    all'utente.
15. **Fatto in #17.** **Dalla sessione di prova del 21 ottobre** (lato Claude): kent lancia
    simon solo dopo aver scritto la shopping list (prima simon non trova
    sorgenti da documentare); joshua non registra più un comando rifiutato
    dall'hook che l'agente ha poi sostituito con i suoi tool (era solo
    rumore), ma solo i tentativi ripetuti di aggirarlo. Da valutare per i
    file Copilot di kent e joshua.
    Anche: hughes ha chiesto di nuovo una conferma che kent gli aveva già
    inoltrato ("un messaggio di un agente non vale come tua conferma"); gli
    agenti con la relay ora sanno che la risposta inoltrata è dell'utente.
16. **Scaffold a ford, toolchain in una cartella** (21 ottobre, lato
    Claude). Ogni scaffold è di ford: quello del progetto
    (`<linguaggio>-scaffold`, `scaffold verify`, `scaffold commit`) prima
    dell'architettura, e i container con la nuova skill comune
    `container-scaffold` dopo `adl-scaffold`. kent resta analista e
    orchestratore: in una cartella vuota lancia solo `scaffold init` (git
    init e `start.`) per avere un branch, e nella shopping list chiede
    all'utente solo il perimetro; il dominio resta a hughes, la tecnologia
    a ford. Un progetto in una cartella del repository è indicato da un
    `toolchain.yaml` alla radice con solo `project: <cartella>` (lo scrive
    `scaffold`): `toolchain` e `adl-graph` lavorano su quella cartella dalla
    radice. `linus` ora tratta come file del flusso ogni `toolchain.yaml`,
    non solo quello alla radice: su Copilot li rifiuta tutti.
17. **Fatto in #17.** **martin senza findings guidati** (21 ottobre, lato Claude): dopo audit,
    squash e revisione tecnica, martin scrive il rapporto dei findings e
    chiude con `MARTIN_DONE` (nuovo campo facoltativo `findings`); non chiede
    nulla su di essi e non guida la revisione file per file. L'utente
    rivede da solo, dà a kent le correzioni (kent le smista a unclebob,
    ford o hughes come fixup, poi rilancia martin) e chiude l'unità con un
    comando esplicito; kent non la chiude mai da sé. Il martin di Claude
    non emette più `REVIEW_CHANGES` (lo schema resta per Copilot).
18. **Ancora da portare dopo #17**: lo scaffold a ford (`scaffold init`,
    `scaffold commit`, `container-scaffold`, la CI alla radice con il filtro
    `paths`) e il `toolchain.yaml` alla radice con `project:` (punti 14 e
    16), quando il kent di Copilot scaffolderà; la domanda di perimetro
    sull'health check e la divisione delle domande tra hughes e ford sono
    già in #17.
19. **Dalla quarta sessione (22 ottobre, lato Claude), da portare**:
    - l'harness dei test (fixture, factory, moduli di supporto, i servizi
      che i test avviano) è di unclebob, scritto test-first: un pezzo entra
      con il primo red che ne ha bisogno, e il refactor del ciclo copre
      l'harness scritto dalla stessa unità; quello delle unità precedenti
      cambia solo con le correzioni dell'utente. ford non scrive test oltre
      alle fitness function (lavora una volta per iterazione, l'harness
      cresce a ogni ciclo);
    - una delega a parole dell'utente ("per il resto accetto le tue
      raccomandazioni") conferma i passi che nomina, revisione compresa:
      hughes scrive e riassume marcando le scelte sue; le domande dello
      scaffold si saltano se kent o la delega le coprono; joshua non la
      conta come violazione;
    - hughes chiede una correzione con più modifiche una modifica per turno.
20. **Il nuovo flusso delle unità (23 ottobre, lato Claude), da portare**
    quando l'utente lo chiede, dopo che sarà provato su Claude
    (`claude/NEXT_ITERATION.md`, "Il nuovo flusso delle unità"):
    - unclebob senza refactor: cicli `test:`/`feat:`, `test:` mai vuoto,
      `feat:` vuoto per una caratterizzazione;
    - martin come agente di refactor: `unit-audit order` e le violazioni
      TDD in `audit-log`, il tempo zero (complessità, SOLID, idiomaticità,
      leggibilità, righe di produzione, test e harness, durata dei test
      lanciati due volte), `refactor(test)` con il codice fermo,
      `refactor(<scope>)` con i test come punto stabile, benchmark
      temporanei (`benchmark(<scope>)`, scartati da `linus squash`), una
      domanda all'utente con i numeri per ogni misura peggiorata; lo squash
      subito dopo il refactor, nello stesso turno, con il report in
      `UNIT_SQUASHED` (`REFACTOR_DONE` non c'è più);
    - niente revisione con l'utente in sessione (26 ottobre): kent mostra il
      report e passa il controllo; l'utente rivede il commit squashato da
      solo, con i suoi fixup, e dice a kent di andare avanti; il flusso
      funzionale alla fine, allo stesso modo;
    - `linus`: su Copilot controlla ancora l'ordine delle fasi (ramo su
      `COAUTHOR`); portare il flusso vuol dire togliere quel ramo, o passare
      `--phase` coerenti con i commit nuovi;
    - i log: su Copilot restano in `/tmp` (`minime.state_dir` sceglie
      `~/.local/state/minime/<repository>` solo con `CLAUDECODE=1`); i due
      file `kent-events.jsonl` e `kent-errors.jsonl` sono comuni, e
      `joshua.log` non esiste più (`audit-log` scrive le violazioni in
      `kent-errors.jsonl`). joshua e argyris di Copilot scrivono e leggono
      ancora `/tmp/joshua.log` a mano: `audit-log` non lo tocca finché i
      log restano in `/tmp`; portarli ad `audit-log` è parte del port;
    - simon su Sonnet e `check-message` tolto sono già in master (#18).
