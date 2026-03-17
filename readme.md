# FantaF1

Implementazione completa (MVP robusto) di backend API + frontend web per fantasy Formula 1.

## Stack
- FastAPI
- SQLAlchemy
- SQLite (default, facilmente sostituibile)
- JWT auth
- Frontend vanilla HTML/CSS/JS servito da FastAPI

## Avvio
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed_demo.py   # facoltativo
uvicorn app.main:app --reload
```

Poi apri:
- Login: `http://127.0.0.1:8000/`
- Dashboard: `http://127.0.0.1:8000/app`
- Swagger: `http://127.0.0.1:8000/docs`

## Funzionalità implementate
- Anagrafica costruttori, piloti, team fantasy
- Claim 1:1 utente-team
- Team fantasy da 5 piloti (vincolo server-side)
- Weekend con timeline predizioni e finalizzazione
- Predizioni utente + capitano weekend
- Minigioco poop trophy con bucket
- Import risultati (via API admin CRUD dati raw) + eventi manuali
- Preflight checks
- Recompute weekend (punti pilota, team, poop)
- Leaderboard fantasy (solo weekend finalizzati) + poop separata
- Frontend a 2 pagine: login separato + dashboard con sezioni collassabili
- Sezioni admin visibili solo a utenti admin

## Endpoint principali
- `POST /auth/register`
- `POST /auth/login`
- `GET /me`
- `GET /me/stats`
- `GET /drivers`
- `GET /constructors`
- `GET /fantasy-teams`
- `GET /weekends`
- `POST /claim/{team_id}`
- `PUT /weekends/{weekend_id}/predictions`
- `PUT /weekends/{weekend_id}/captain`
- `PUT /weekends/{weekend_id}/poop-prediction`
- `POST /admin/weekends`
- `POST /admin/weekends/{weekend_id}/preflight`
- `POST /admin/weekends/{weekend_id}/recompute`
- `POST /admin/weekends/{weekend_id}/finalize`
- `GET /leaderboard`

## Note
- Il pannello web copre i flussi principali utente/admin; per operazioni admin avanzate (upload risultati massivi e finalizzazione) resta disponibile `/docs`.
- Repository pronto per estensioni (importer Jolpica, Postgres/Supabase, ruoli avanzati).
