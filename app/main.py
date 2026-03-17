from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session
from pathlib import Path

from app.auth import get_current_user, hash_password, issue_token, require_admin, verify_password
from app.db import Base, engine, get_db
from app import models, schemas
from app.services.recompute import preflight, recompute_weekend, weekend_status

app = FastAPI(title="FantaF1 API")
Base.metadata.create_all(bind=engine)
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def home_page():
    return FileResponse(static_dir / "index.html")


@app.get("/app", include_in_schema=False)
def dashboard_page():
    return FileResponse(static_dir / "dashboard.html")


@app.post("/auth/register", response_model=schemas.TokenOut)
def register(payload: schemas.RegisterIn, db: Session = Depends(get_db)):
    if db.query(models.User).filter_by(email=payload.email).first():
        raise HTTPException(400, "Email already exists")
    is_first = db.query(models.User).count() == 0
    u = models.User(email=payload.email, password_hash=hash_password(payload.password), is_admin=is_first)
    db.add(u)
    db.commit()
    db.refresh(u)
    return schemas.TokenOut(access_token=issue_token(u.id))


@app.post("/auth/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    u = db.query(models.User).filter_by(email=payload.email).first()
    if not u or not verify_password(payload.password, u.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return schemas.TokenOut(access_token=issue_token(u.id))


@app.post("/admin/weekends")
def create_weekend(payload: schemas.WeekendCreate, _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    if not (payload.prediction_open_at < payload.prediction_close_at < payload.weekend_end_at):
        raise HTTPException(400, "Invalid timeline")
    w = models.Weekend(**payload.model_dump())
    db.add(w)
    db.commit()
    return {"id": w.id}


@app.post("/teams/{team_id}/drivers/{driver_id}")
def add_driver_to_team(team_id: str, driver_id: str, _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    count = db.query(func.count()).select_from(models.FantasyTeamDriver).filter_by(fantasy_team_id=team_id).scalar() or 0
    if count >= 5:
        raise HTTPException(400, "Team already has 5 drivers")
    if db.query(models.FantasyTeamDriver).filter_by(fantasy_team_id=team_id, driver_id=driver_id).first():
        return {"ok": True}
    db.add(models.FantasyTeamDriver(fantasy_team_id=team_id, driver_id=driver_id))
    db.commit()
    return {"ok": True}


@app.post("/claim/{team_id}")
def claim_team(team_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(models.TeamClaim, user.id):
        raise HTTPException(400, "User already claimed a team")
    if db.query(models.TeamClaim).filter_by(fantasy_team_id=team_id).first():
        raise HTTPException(400, "Team already claimed")
    db.add(models.TeamClaim(user_id=user.id, fantasy_team_id=team_id))
    db.commit()
    return {"ok": True}


@app.get("/me")
def me(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    claim = db.get(models.TeamClaim, user.id)
    team = db.get(models.FantasyTeam, claim.fantasy_team_id) if claim else None
    team_drivers = []
    if claim:
        drivers = (
            db.query(models.Driver)
            .join(models.FantasyTeamDriver, models.FantasyTeamDriver.driver_id == models.Driver.id)
            .filter(models.FantasyTeamDriver.fantasy_team_id == claim.fantasy_team_id)
            .all()
        )
        team_drivers = [{"id": d.id, "name": f"{d.given_name} {d.family_name}", "code": d.code} for d in drivers]

    return {
        "id": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
        "claimed_team": {"id": team.id, "name": team.name} if team else None,
        "team_drivers": team_drivers,
    }


@app.get("/me/stats")
def me_stats(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    claim = db.get(models.TeamClaim, user.id)
    if not claim:
        return {"season_points": 0.0, "poop_points": 0, "weekends_played": 0}

    season_points = (
        db.query(func.sum(models.TeamWeekendPoints.total_points))
        .join(models.Weekend, models.Weekend.id == models.TeamWeekendPoints.weekend_id)
        .filter(models.TeamWeekendPoints.fantasy_team_id == claim.fantasy_team_id)
        .filter(models.Weekend.is_finalized.is_(True))
        .scalar()
        or 0
    )

    weekends_played = (
        db.query(func.count(models.TeamWeekendPoints.weekend_id))
        .filter(models.TeamWeekendPoints.fantasy_team_id == claim.fantasy_team_id)
        .scalar()
        or 0
    )

    poop_points = (
        db.query(func.sum(models.PoopPoint.points))
        .filter(models.PoopPoint.user_id == user.id)
        .scalar()
        or 0
    )

    return {
        "season_points": float(season_points),
        "poop_points": int(poop_points),
        "weekends_played": int(weekends_played),
    }


@app.get("/drivers")
def list_drivers(db: Session = Depends(get_db)):
    rows = db.query(models.Driver).all()
    return [
        {
            "id": d.id,
            "code": d.code,
            "given_name": d.given_name,
            "family_name": d.family_name,
            "constructor_id": d.constructor_id,
            "is_active": d.is_active,
        }
        for d in rows
    ]


@app.get("/constructors")
def list_constructors(db: Session = Depends(get_db)):
    rows = db.query(models.Constructor).all()
    return [{"id": c.id, "code": c.code, "name": c.name} for c in rows]


@app.get("/fantasy-teams")
def list_fantasy_teams(db: Session = Depends(get_db)):
    rows = db.query(models.FantasyTeam).all()
    claims = {c.fantasy_team_id: c.user_id for c in db.query(models.TeamClaim).all()}
    tds = db.query(models.FantasyTeamDriver).all()
    count_by_team: dict[str, int] = {}
    for td in tds:
        count_by_team[td.fantasy_team_id] = count_by_team.get(td.fantasy_team_id, 0) + 1
    return [
        {
            "id": t.id,
            "name": t.name,
            "is_claimed": t.id in claims,
            "drivers_count": count_by_team.get(t.id, 0),
        }
        for t in rows
    ]


@app.get("/weekends")
def list_weekends(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    rows = db.query(models.Weekend).order_by(models.Weekend.season.desc(), models.Weekend.round.desc()).all()
    return [
        {
            "id": w.id,
            "name": w.name,
            "season": w.season,
            "round": w.round,
            "has_sprint": w.has_sprint,
            "is_finalized": w.is_finalized,
            "status": weekend_status(w, now),
            "prediction_open_at": w.prediction_open_at,
            "prediction_close_at": w.prediction_close_at,
            "weekend_end_at": w.weekend_end_at,
        }
        for w in rows
    ]


def _assert_open(db: Session, weekend_id: str):
    w = db.get(models.Weekend, weekend_id)
    if not w:
        raise HTTPException(404, "Weekend not found")
    if weekend_status(w, datetime.utcnow()) != "open_predictions":
        raise HTTPException(400, "Predictions are locked")


@app.put("/weekends/{weekend_id}/predictions")
def upsert_prediction(weekend_id: str, payload: schemas.PredictionIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _assert_open(db, weekend_id)
    pred = db.query(models.Prediction).filter_by(user_id=user.id, weekend_id=weekend_id).first()
    if not pred:
        pred = models.Prediction(user_id=user.id, weekend_id=weekend_id, **payload.model_dump())
        db.add(pred)
    else:
        for k, v in payload.model_dump().items():
            setattr(pred, k, v)
    db.commit()
    return {"ok": True}


@app.delete("/weekends/{weekend_id}/predictions")
def delete_prediction(weekend_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _assert_open(db, weekend_id)
    db.query(models.Prediction).filter_by(user_id=user.id, weekend_id=weekend_id).delete()
    db.commit()
    return {"ok": True}


@app.put("/weekends/{weekend_id}/captain")
def set_captain(weekend_id: str, payload: schemas.CaptainIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _assert_open(db, weekend_id)
    claim = db.get(models.TeamClaim, user.id)
    if not claim:
        raise HTTPException(400, "Claim a team first")
    owns = db.query(models.FantasyTeamDriver).filter_by(fantasy_team_id=claim.fantasy_team_id, driver_id=payload.driver_id).first()
    if not owns:
        raise HTTPException(400, "Captain must be in your fantasy team")
    row = db.query(models.CaptainChoice).filter_by(user_id=user.id, weekend_id=weekend_id).first()
    if not row:
        db.add(models.CaptainChoice(user_id=user.id, weekend_id=weekend_id, driver_id=payload.driver_id))
    else:
        row.driver_id = payload.driver_id
    db.commit()
    return {"ok": True}


@app.put("/weekends/{weekend_id}/poop-prediction")
def upsert_poop_prediction(weekend_id: str, payload: schemas.PoopPredictionIn, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    _assert_open(db, weekend_id)
    row = db.query(models.PoopPrediction).filter_by(user_id=user.id, weekend_id=weekend_id).first()
    if not row:
        db.add(models.PoopPrediction(user_id=user.id, weekend_id=weekend_id, bucket=payload.bucket))
    else:
        row.bucket = payload.bucket
    db.commit()
    return {"ok": True}


@app.post("/admin/weekends/{weekend_id}/preflight")
def preflight_endpoint(weekend_id: str, _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    return {"errors": preflight(db, weekend_id)}


@app.post("/admin/weekends/{weekend_id}/recompute")
def recompute_endpoint(weekend_id: str, _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    return recompute_weekend(db, weekend_id)


@app.post("/admin/weekends/{weekend_id}/finalize")
def finalize_weekend(weekend_id: str, _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    result = recompute_weekend(db, weekend_id)
    if not result["ok"]:
        raise HTTPException(400, result)
    w = db.get(models.Weekend, weekend_id)
    w.is_finalized = True
    db.commit()
    return {"ok": True}


@app.post("/admin/constructors")
def upsert_constructor(payload: dict, _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(models.Constructor).filter_by(code=payload["code"]).first()
    if not row:
        row = models.Constructor(code=payload["code"], name=payload["name"])
        db.add(row)
    else:
        row.name = payload["name"]
    db.commit()
    return {"id": row.id}


@app.post("/admin/drivers")
def upsert_driver(payload: dict, _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(models.Driver).filter_by(code=payload["code"]).first()
    if not row:
        row = models.Driver(**payload)
        db.add(row)
    else:
        for k, v in payload.items():
            setattr(row, k, v)
    db.commit()
    return {"id": row.id}


@app.post("/admin/fantasy-teams")
def create_team(payload: dict, _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(models.FantasyTeam).filter_by(name=payload["name"]).first()
    if row:
        return {"id": row.id}
    row = models.FantasyTeam(name=payload["name"])
    db.add(row)
    db.commit()
    return {"id": row.id}


@app.post("/admin/weekends/{weekend_id}/qualification")
def upsert_qualification(weekend_id: str, payload: list[dict], _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    for item in payload:
        row = db.query(models.QualificationResult).filter_by(weekend_id=weekend_id, driver_id=item["driver_id"]).first()
        if not row:
            db.add(models.QualificationResult(weekend_id=weekend_id, **item))
        else:
            row.position = item["position"]
    db.commit()
    return {"ok": True}


@app.post("/admin/weekends/{weekend_id}/sprint")
def upsert_sprint(weekend_id: str, payload: list[dict], _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    for item in payload:
        row = db.query(models.SprintResult).filter_by(weekend_id=weekend_id, driver_id=item["driver_id"]).first()
        if not row:
            db.add(models.SprintResult(weekend_id=weekend_id, **item))
        else:
            row.position = item["position"]
    db.commit()
    return {"ok": True}


@app.post("/admin/weekends/{weekend_id}/race")
def upsert_race(weekend_id: str, payload: list[dict], _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    for item in payload:
        row = db.query(models.RaceResult).filter_by(weekend_id=weekend_id, driver_id=item["driver_id"]).first()
        if not row:
            db.add(models.RaceResult(weekend_id=weekend_id, **item))
        else:
            for k, v in item.items():
                setattr(row, k, v)
    db.commit()
    return {"ok": True}


@app.post("/admin/weekends/{weekend_id}/events")
def upsert_events(weekend_id: str, payload: dict, _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.get(models.WeekendEvent, weekend_id)
    if not row:
        row = models.WeekendEvent(weekend_id=weekend_id, **payload)
        db.add(row)
    else:
        for k, v in payload.items():
            setattr(row, k, v)
    db.commit()
    return {"ok": True}


@app.post("/admin/weekends/{weekend_id}/poop-mini-team")
def set_poop_mini_team(weekend_id: str, payload: list[str], _: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    if len(payload) != 5 or len(set(payload)) != 5:
        raise HTTPException(400, "Exactly 5 unique drivers required")
    db.query(models.PoopMiniTeam).filter_by(weekend_id=weekend_id).delete()
    for d in payload:
        db.add(models.PoopMiniTeam(weekend_id=weekend_id, driver_id=d))
    db.commit()
    return {"ok": True}


@app.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    rows = (
        db.query(models.FantasyTeam.name, func.sum(models.TeamWeekendPoints.total_points).label("pts"))
        .join(models.Weekend, models.Weekend.id == models.TeamWeekendPoints.weekend_id)
        .join(models.FantasyTeam, models.FantasyTeam.id == models.TeamWeekendPoints.fantasy_team_id)
        .filter(models.Weekend.is_finalized.is_(True))
        .group_by(models.FantasyTeam.name)
        .order_by(func.sum(models.TeamWeekendPoints.total_points).desc())
        .all()
    )
    poop = (
        db.query(models.User.email, func.sum(models.PoopPoint.points).label("poop"))
        .group_by(models.User.email)
        .join(models.PoopPoint, models.PoopPoint.user_id == models.User.id)
        .all()
    )
    return {
        "fantasy": [{"team": r[0], "points": float(r[1] or 0)} for r in rows],
        "poop": [{"user": r[0], "points": int(r[1] or 0)} for r in poop],
    }
