from datetime import datetime
from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=6)


class LoginIn(RegisterIn):
    pass


class TokenOut(BaseModel):
    access_token: str


class WeekendCreate(BaseModel):
    name: str
    season: int
    round: int
    has_sprint: bool = False
    prediction_open_at: datetime
    prediction_close_at: datetime
    weekend_end_at: datetime


class PredictionIn(BaseModel):
    red_flag: bool
    safety_car_or_vsc: bool
    wet_tyres: bool
    top2_same_constructor: bool
    poleman_wins: bool
    over_2_dnf_dns: bool
    constructors_2_top10: int = Field(ge=0, le=5)


class CaptainIn(BaseModel):
    driver_id: str


class PoopPredictionIn(BaseModel):
    bucket: str = Field(pattern="^(LE40|MID80|GT80)$")
