# FantaF1

Implementazione completa (MVP robusto) di backend API per fantasy Formula 1.

## Stack
- FastAPI
- SQLAlchemy
- SQLite (default, facilmente sostituibile)
- JWT auth

## Avvio
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

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

## Endpoint principali
- `POST /auth/register`
- `POST /auth/login`
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
Questo repository è pronto per estensioni (UI, importer Jolpica, Postgres/Supabase, RLS).
