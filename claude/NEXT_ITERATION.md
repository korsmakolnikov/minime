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
| Refactor | sei sotto-passi proposti uno a uno (SOLID, complessità, idiomaticità, produzione, test, suite) | SOLID, produzione, test, `elixir-style`, controlli statici, refactor vuoto con il verdetto | interattivo: i sei sotto-passi, con i controlli statici in 4f e un refactor vuoto se nessuno committa; workflow: Copilot |
| Commit | `git commit` diretto, `test:`/`feat:`/`refactor:` senza scope | comando `linus`, fasi, scope, `check-message`, amend del red, regression, characterisation, fixup | `linus` in tutti e due i modi; lo scope si chiede in STEP 0 nel modo interattivo |
| Suite completa | solo in 4f | dopo ogni green e ogni refactor; sistemi grandi solo test correlati | interattivo: 4f; workflow: Copilot; sistemi grandi in entrambi |
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

## Da fare

1. Gli altri agenti, dal contenuto Copilot, con hook nel frontmatter e
   strumenti di Claude Code (`Agent`, `SendMessage`, `AskUserQuestion`,
   `Edit`/`Write`, `Bash` con `run_in_background`):
   - **kent** (thread principale): relay con `AskUserQuestion`, lancio in
     background, `SendMessage`, `SIGNAL_INVALID` non serve più (lo fa
     l'hook); niente eventi a joshua, che legge `/tmp/kent-events.jsonl`.
   - **hughes**, **ford**, **martin**, **simon**: port quasi diretto; tolta
     la parte "controlla il blocco con signal-check" (lo fa l'hook).
   - **joshua**: audit sui transcript e su `/tmp/kent-events.jsonl` e
     `/tmp/kent-guard.jsonl`; checklist ridotta alle regole di giudizio.
   - **argyris** (`claude --agent argyris`) e una skill `minime-sync` per
     `~/.claude` → `claude/` e `common/`.
   - **linus** (`claude --agent linus`) per i commit fuori dal workflow.
2. Permessi: equivalente di `auto_approve.py` per non far rispondere
   l'utente a ogni comando (regole `allow`/`deny` nel frontmatter non
   esistono: `permissionMode` per agente, o un hook `PermissionRequest`).
3. README: sezione del workflow Claude Code.

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
