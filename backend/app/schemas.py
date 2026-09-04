from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    username: str
    csrf_token: str


VerificationStatus = Literal["verified", "unverified", "conflicting"]
Gender = Literal["male", "female", "unknown"]


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    gender: Gender = "unknown"
    birth_date: str | None = None
    death_date: str | None = None
    native_place: str | None = None
    biography: str | None = None
    verification_status: VerificationStatus = "unverified"


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    gender: Gender | None = None
    birth_date: str | None = None
    death_date: str | None = None
    native_place: str | None = None
    biography: str | None = None
    verification_status: VerificationStatus | None = None


class PersonResponse(PersonCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class RelationshipCreate(BaseModel):
    kind: Literal["parent", "spouse"]
    person_id: str
    relative_id: str
    verification_status: VerificationStatus = "unverified"


class RelationshipResponse(RelationshipCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class KinshipStepResponse(BaseModel):
    person_id: str
    person_name: str


class KinshipResponse(BaseModel):
    label: str
    steps: list[KinshipStepResponse]


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action: str
    entity_type: str
    entity_id: str
    summary: str
    created_at: datetime
