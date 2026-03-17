from collections import Counter, defaultdict
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app import models
from app.services.scoring import RACE_POINTS, SPRINT_POINTS, TOP10_CONSTRUCTOR_EXACT, bucket_from_total, quali_points, status_points


def weekend_status(w: models.Weekend, now):
    if now < w.prediction_open_at:
        return "upcoming"
    if w.prediction_open_at <= now < w.prediction_close_at:
        return "open_predictions"
    if w.prediction_close_at <= now < w.weekend_end_at:
        return "locked"
    return "completed"


def preflight(db: Session, weekend_id: str) -> list[str]:
    errors: list[str] = []
    w = db.get(models.Weekend, weekend_id)
    if not w:
        return ["weekend_not_found"]

    active = db.query(models.Driver).filter(models.Driver.is_active.is_(True)).count()
    race = db.query(models.RaceResult).filter_by(weekend_id=weekend_id).all()
    if len(race) < max(1, active - 2):
        errors.append("race_results_incomplete")

    if w.has_sprint:
        sprint = db.query(models.SprintResult).filter_by(weekend_id=weekend_id).all()
        if not sprint:
            errors.append("missing_sprint_results")

    starts = [r.start_position for r in race]
    if len(starts) != len(set(starts)):
        errors.append("duplicate_start_positions")

    finishes = [r.finish_position for r in race if r.finish_position is not None]
    if len(finishes) != len(set(finishes)):
        errors.append("duplicate_finish_positions")

    for r in race:
        if r.status == "classified" and r.finish_position is None:
            errors.append(f"classified_without_finish:{r.driver_id}")
        if r.status in {"dnf", "dns", "dsq"} and r.finish_position is not None:
            errors.append(f"non_classified_with_finish:{r.driver_id}")

    return errors


def recompute_weekend(db: Session, weekend_id: str) -> dict:
    errors = preflight(db, weekend_id)
    if errors:
        return {"ok": False, "errors": errors}

    race_rows = db.query(models.RaceResult).filter_by(weekend_id=weekend_id).all()
    sprint_rows = {r.driver_id: r for r in db.query(models.SprintResult).filter_by(weekend_id=weekend_id).all()}
    quali_rows = {r.driver_id: r for r in db.query(models.QualificationResult).filter_by(weekend_id=weekend_id).all()}
    events = db.get(models.WeekendEvent, weekend_id)

    drivers = {d.id: d for d in db.query(models.Driver).all()}
    by_constructor = defaultdict(list)
    for d in drivers.values():
        by_constructor[d.constructor_id].append(d.id)

    classified = [r for r in race_rows if r.status == "classified" and r.finish_position is not None]
    classified.sort(key=lambda x: x.finish_position)
    tail_bonus = {}
    if classified:
        tail_bonus[classified[-1].driver_id] = 10
        if len(classified) > 1:
            tail_bonus[classified[-2].driver_id] = 5

    db.execute(delete(models.DriverWeekendPoints).where(models.DriverWeekendPoints.weekend_id == weekend_id))
    db.execute(delete(models.TeamWeekendPoints).where(models.TeamWeekendPoints.weekend_id == weekend_id))
    db.execute(delete(models.PoopPoint).where(models.PoopPoint.weekend_id == weekend_id))

    for rr in race_rows:
        dr = drivers[rr.driver_id]
        race_pts = RACE_POINTS.get(rr.finish_position, 0) if rr.status == "classified" and rr.finish_position else 0
        sprint_pts = SPRINT_POINTS.get(sprint_rows[rr.driver_id].position, 0) if rr.driver_id in sprint_rows else 0
        quali_pts = quali_points(quali_rows[rr.driver_id].position) if rr.driver_id in quali_rows else 0
        delta_pts = (rr.start_position - rr.finish_position) * 0.5 if rr.status == "classified" and rr.finish_position else 0

        teammates = [x for x in by_constructor[dr.constructor_id] if x != rr.driver_id]
        teammate_pts = 0
        if teammates and rr.status == "classified":
            mate = next((x for x in race_rows if x.driver_id == teammates[0]), None)
            if mate:
                if mate.status != "classified":
                    teammate_pts = 1
                elif rr.finish_position and mate.finish_position and rr.finish_position < mate.finish_position:
                    teammate_pts = 2
                else:
                    teammate_pts = -1

        pen_pts = -5 if rr.has_race_penalty else 0
        stat_pts = status_points(rr.status)
        dotd_pts = 3 if events and events.driver_of_the_day_id == rr.driver_id else 0
        tail_pts = tail_bonus.get(rr.driver_id, 0)
        total = race_pts + sprint_pts + quali_pts + delta_pts + teammate_pts + pen_pts + stat_pts + dotd_pts + tail_pts

        db.add(models.DriverWeekendPoints(
            weekend_id=weekend_id,
            driver_id=rr.driver_id,
            race_points=race_pts,
            sprint_points=sprint_pts,
            quali_points=quali_pts,
            delta_points=delta_pts,
            teammate_points=teammate_pts,
            penalty_points=pen_pts,
            status_points=stat_pts,
            dotd_points=dotd_pts,
            tail_bonus_points=tail_pts,
            total_points=total,
        ))

    driver_totals = {r.driver_id: r.total_points for r in db.query(models.DriverWeekendPoints).filter_by(weekend_id=weekend_id).all()}

    # predictions and team totals
    top2_same_constructor = False
    if len(classified) >= 2:
        d1 = drivers[classified[0].driver_id]
        d2 = drivers[classified[1].driver_id]
        top2_same_constructor = d1.constructor_id == d2.constructor_id
    pole_driver_id = next((d for d, q in quali_rows.items() if q.position == 1), None)
    winner_id = classified[0].driver_id if classified else None
    poleman_wins = pole_driver_id is not None and pole_driver_id == winner_id
    dnf_dns_over_2 = sum(1 for r in race_rows if r.status in {"dnf", "dns"}) > 2
    constructor_top10 = Counter()
    for r in classified:
        if r.finish_position <= 10:
            constructor_top10[drivers[r.driver_id].constructor_id] += 1
    constructors_2_top10 = sum(1 for _, cnt in constructor_top10.items() if cnt >= 2)

    teams = db.query(models.FantasyTeam).all()
    claims = {c.fantasy_team_id: c.user_id for c in db.query(models.TeamClaim).all()}
    team_driver_map = defaultdict(list)
    for tdr in db.query(models.FantasyTeamDriver).all():
        team_driver_map[tdr.fantasy_team_id].append(tdr.driver_id)
    captains = {(c.user_id, c.weekend_id): c.driver_id for c in db.query(models.CaptainChoice).filter_by(weekend_id=weekend_id).all()}
    preds = {(p.user_id, p.weekend_id): p for p in db.query(models.Prediction).filter_by(weekend_id=weekend_id).all()}

    for t in teams:
        base = 0.0
        user_id = claims.get(t.id)
        captain = captains.get((user_id, weekend_id)) if user_id else None
        for d_id in team_driver_map[t.id]:
            p = driver_totals.get(d_id, 0)
            base += p * (2 if captain == d_id else 1)

        pred_points = 0.0
        pred = preds.get((user_id, weekend_id)) if user_id else None
        if pred and events:
            if pred.red_flag == bool(events.red_flag):
                pred_points += 7 if pred.red_flag else 5
            if pred.safety_car_or_vsc == bool(events.safety_car_or_vsc):
                pred_points += 3
            if pred.wet_tyres == bool(events.wet_tyres):
                pred_points += 2
            if pred.top2_same_constructor == top2_same_constructor:
                pred_points += 4
            if pred.poleman_wins == poleman_wins:
                pred_points += 2 if pred.poleman_wins else 4
            if pred.over_2_dnf_dns == dnf_dns_over_2:
                pred_points += 5
            if pred.constructors_2_top10 == constructors_2_top10:
                pred_points += TOP10_CONSTRUCTOR_EXACT[pred.constructors_2_top10]

        db.add(models.TeamWeekendPoints(
            weekend_id=weekend_id,
            fantasy_team_id=t.id,
            drivers_points=base,
            predictions_points=pred_points,
            total_points=base + pred_points,
        ))

    # poop trophy
    mini = [m.driver_id for m in db.query(models.PoopMiniTeam).filter_by(weekend_id=weekend_id).all()]
    if len(mini) == 5:
        total = sum(driver_totals.get(d, 0) for d in mini)
        bucket = bucket_from_total(total)
        for pp in db.query(models.PoopPrediction).filter_by(weekend_id=weekend_id).all():
            db.add(models.PoopPoint(user_id=pp.user_id, weekend_id=weekend_id, points=1 if pp.bucket == bucket else 0))

    db.commit()
    return {"ok": True, "errors": []}
