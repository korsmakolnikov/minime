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
  a `common/` vale per tutti e due i lati: va provata su entrambi.

## Da fare sull'altro PC

```sh
cd ~/code/minime && git pull && make copilot-install
```

(`make update` solo se quella macchina non ha ancora fatto la migrazione dei
vecchi nomi.) Senza l'installazione gli agenti restano al formato vecchio e
`signal-check` non è nel `PATH`.

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
