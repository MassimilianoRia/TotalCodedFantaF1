import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def u4() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=u4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Constructor(Base):
    __tablename__ = "constructors"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=u4)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class Driver(Base):
    __tablename__ = "drivers"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=u4)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    given_name: Mapped[str] = mapped_column(String, nullable=False)
    family_name: Mapped[str] = mapped_column(String, nullable=False)
    constructor_id: Mapped[str] = mapped_column(ForeignKey("constructors.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FantasyTeam(Base):
    __tablename__ = "fantasy_teams"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=u4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FantasyTeamDriver(Base):
    __tablename__ = "fantasy_team_drivers"
    fantasy_team_id: Mapped[str] = mapped_column(ForeignKey("fantasy_teams.id"), primary_key=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TeamClaim(Base):
    __tablename__ = "team_claims"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    fantasy_team_id: Mapped[str] = mapped_column(ForeignKey("fantasy_teams.id"), unique=True, nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Weekend(Base):
    __tablename__ = "weekends"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=u4)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    has_sprint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    prediction_open_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    prediction_close_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    weekend_end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    __table_args__ = (UniqueConstraint("season", "round", name="uq_season_round"),)


class QualificationResult(Base):
    __tablename__ = "qualification_results"
    weekend_id: Mapped[str] = mapped_column(ForeignKey("weekends.id"), primary_key=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class SprintResult(Base):
    __tablename__ = "sprint_results"
    weekend_id: Mapped[str] = mapped_column(ForeignKey("weekends.id"), primary_key=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class RaceResult(Base):
    __tablename__ = "race_results"
    weekend_id: Mapped[str] = mapped_column(ForeignKey("weekends.id"), primary_key=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), primary_key=True)
    start_position: Mapped[int] = mapped_column(Integer, nullable=False)
    finish_position: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, nullable=False)  # classified, dnf, dns, dsq
    has_race_penalty: Mapped[bool] = mapped_column(Boolean, default=False)


class WeekendEvent(Base):
    __tablename__ = "weekend_events"
    weekend_id: Mapped[str] = mapped_column(ForeignKey("weekends.id"), primary_key=True)
    red_flag: Mapped[bool | None] = mapped_column(Boolean)
    safety_car_or_vsc: Mapped[bool | None] = mapped_column(Boolean)
    wet_tyres: Mapped[bool | None] = mapped_column(Boolean)
    driver_of_the_day_id: Mapped[str | None] = mapped_column(ForeignKey("drivers.id"))


class Prediction(Base):
    __tablename__ = "predictions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    weekend_id: Mapped[str] = mapped_column(ForeignKey("weekends.id"), primary_key=True)
    red_flag: Mapped[bool] = mapped_column(Boolean, nullable=False)
    safety_car_or_vsc: Mapped[bool] = mapped_column(Boolean, nullable=False)
    wet_tyres: Mapped[bool] = mapped_column(Boolean, nullable=False)
    top2_same_constructor: Mapped[bool] = mapped_column(Boolean, nullable=False)
    poleman_wins: Mapped[bool] = mapped_column(Boolean, nullable=False)
    over_2_dnf_dns: Mapped[bool] = mapped_column(Boolean, nullable=False)
    constructors_2_top10: Mapped[int] = mapped_column(Integer, nullable=False)


class CaptainChoice(Base):
    __tablename__ = "captain_choices"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    weekend_id: Mapped[str] = mapped_column(ForeignKey("weekends.id"), primary_key=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), nullable=False)


class DriverWeekendPoints(Base):
    __tablename__ = "driver_weekend_points"
    weekend_id: Mapped[str] = mapped_column(ForeignKey("weekends.id"), primary_key=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), primary_key=True)
    race_points: Mapped[float] = mapped_column(Float, default=0)
    sprint_points: Mapped[float] = mapped_column(Float, default=0)
    quali_points: Mapped[float] = mapped_column(Float, default=0)
    delta_points: Mapped[float] = mapped_column(Float, default=0)
    teammate_points: Mapped[float] = mapped_column(Float, default=0)
    penalty_points: Mapped[float] = mapped_column(Float, default=0)
    status_points: Mapped[float] = mapped_column(Float, default=0)
    dotd_points: Mapped[float] = mapped_column(Float, default=0)
    tail_bonus_points: Mapped[float] = mapped_column(Float, default=0)
    total_points: Mapped[float] = mapped_column(Float, default=0)


class TeamWeekendPoints(Base):
    __tablename__ = "team_weekend_points"
    weekend_id: Mapped[str] = mapped_column(ForeignKey("weekends.id"), primary_key=True)
    fantasy_team_id: Mapped[str] = mapped_column(ForeignKey("fantasy_teams.id"), primary_key=True)
    drivers_points: Mapped[float] = mapped_column(Float, default=0)
    predictions_points: Mapped[float] = mapped_column(Float, default=0)
    total_points: Mapped[float] = mapped_column(Float, default=0)


class PoopMiniTeam(Base):
    __tablename__ = "poop_mini_teams"
    weekend_id: Mapped[str] = mapped_column(ForeignKey("weekends.id"), primary_key=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey("drivers.id"), primary_key=True)


class PoopPrediction(Base):
    __tablename__ = "poop_predictions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    weekend_id: Mapped[str] = mapped_column(ForeignKey("weekends.id"), primary_key=True)
    bucket: Mapped[str] = mapped_column(String, nullable=False)  # LE40 MID80 GT80


class PoopPoint(Base):
    __tablename__ = "poop_points"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    weekend_id: Mapped[str] = mapped_column(ForeignKey("weekends.id"), primary_key=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
