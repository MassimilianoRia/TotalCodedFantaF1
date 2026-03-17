from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal
from app.models import Constructor, Driver, FantasyTeam, Weekend


db = SessionLocal()
if not db.query(Constructor).first():
    ferrari = Constructor(code="FER", name="Ferrari")
    mcl = Constructor(code="MCL", name="McLaren")
    db.add_all([ferrari, mcl])
    db.commit()
    db.refresh(ferrari)
    db.refresh(mcl)
    db.add_all([
        Driver(code="LEC", given_name="Charles", family_name="Leclerc", constructor_id=ferrari.id),
        Driver(code="HAM", given_name="Lewis", family_name="Hamilton", constructor_id=ferrari.id),
        Driver(code="NOR", given_name="Lando", family_name="Norris", constructor_id=mcl.id),
        Driver(code="PIA", given_name="Oscar", family_name="Piastri", constructor_id=mcl.id),
    ])
    db.add_all([FantasyTeam(name="Team A"), FantasyTeam(name="Team B"), FantasyTeam(name="Team C"), FantasyTeam(name="Team D")])
    now = datetime.utcnow()
    db.add(Weekend(
        name="Demo GP",
        season=2026,
        round=1,
        has_sprint=False,
        prediction_open_at=now - timedelta(days=2),
        prediction_close_at=now + timedelta(days=2),
        weekend_end_at=now + timedelta(days=4),
    ))
    db.commit()
print('seed complete')
