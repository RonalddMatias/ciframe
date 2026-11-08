# AGENTS.md

deciframe is a song-discovery tool for musicians: search by title/artist,
genre, chords you already know, or a famous chord sequence, and it finds
similar songs. Full description: [README.md](README.md).

## Stack

- Backend: Python 3.9, Flask 3.1, gunicorn. Single file (`main.py`) that
  loads `data/top/dataset_final.csv` into memory once at startup — there is
  no database.
- Frontend: AngularJS 1.4.9 + jQuery, loaded from CDN in `static/index.html`,
  no build step. Legacy, and there's no plan to modernize the stack itself —
  but touching it is no longer off-limits when a task needs it; see
  [docs/adr/0003-lift-frontend-freeze.md](docs/adr/0003-lift-frontend-freeze.md).
- Deploy: local-only via Docker for now. No cloud target has been chosen.

## Run locally

Docker (matches how the app actually ships):

```
docker build -t ciframe .
docker run -p 8080:8080 ciframe
```

Or a plain virtualenv:

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py        # serves on :5000 instead of :8080
```

## Verify it's up

```
curl http://localhost:8080/generos
```

Done when this returns a JSON array of genre names (e.g. `["Rock", "Samba", ...]`), not an error page. If it hangs on startup, it's still parsing the CSV — give it a few seconds.

## Gotchas

- Editing `data/top/*.csv` requires a restart: it's read once at import time, not per-request.
- Every endpoint returns `json.dumps(...)` as a plain string, not `jsonify` — responses come back `Content-Type: text/html`. This is intentional legacy behavior; changing it is a real API change, not a cleanup.
- Check `docs/adr/` before changing the deploy setup — it has a documented reason for its current state.

## RePPIT workflow: one phase per session

The "Sequências de Acordes Customizadas" exercise
([docs/features/sequencias-customizadas/](docs/features/sequencias-customizadas/))
runs the RePPIT framework in five phases, in order: **pesquisa → proposta →
plano → implementação → testes**.

- **One phase per session.** Each opencode session runs exactly one RePPIT
  command (`pesquisa`, `proposta`, `plano`, `implementar`, `testes`) and then
  stops.
- **A new session only starts once the previous phase is settled**: its file
  in `docs/features/sequencias-customizadas/` is filled in, with the
  instruction blockquote removed.
- **The user triggers every command.** The agent never starts or advances a
  phase on its own; it waits to be told.
- **State lives in the phase files, not in chat.** To find where we are,
  read `01-research.md`, `02-proposal.md`, `03-plan.md`, `04-test-report.md`
  and see which is still an untouched template.
- If a decision changes later, the earlier phase document is updated before
  moving on — the plan never stays stale.
- **Export the session at the end of every phase.** The delivery requires the
  session file, and each phase is its own session, so nothing else carries it
  over. Do it before closing the session:

  ```
  opencode session list                       # newest first, copy the ses_ id
  opencode session export <ses_id> \
    > docs/features/sequencias-customizadas/sessions/<NN>-<fase>.json
  ```

  (`opencode session export` needs an explicit ID when there's no TTY; in the
  TUI, `/export` does the same.) Committing the `sessions/` files is part of
  the deliverable, not scratch output.
