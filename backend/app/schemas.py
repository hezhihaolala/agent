from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class AuthResponse(BaseModel):
    username: str
    csrf_token: str


VerificationStatus = Literal["verified", "unverified", "conflicting"]
Gender = Literal["male", "female", "unknown"]
RelativeType = Literal[
    "parents",
    "father",
    "mother",
    "children",
    "spouses",
    "siblings",
    "paternal_cousins",
]


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
    kind: Literal["parent", "spouse", "sibling", "paternal_cousin"]
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


class SourceLinkCreate(BaseModel):
    entity_type: Literal["person", "relationship"]
    entity_id: str
    field_name: str | None = None


class SourceLinkResponse(SourceLinkCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    created_at: datetime


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source_type: Literal["image", "document", "text"]
    era: str | None
    provenance: str | None
    notes: str | None
    verification_status: VerificationStatus
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    created_at: datetime


class SourceDetailResponse(SourceResponse):
    links: list[SourceLinkResponse]


class AgentIntent(BaseModel):
    kind: Literal[
        "relationship_query", "relative_lookup", "create_person", "create_child"
    ]
    source_name: str | None = None
    target_name: str | None = None
    relation_type: RelativeType | None = None
    parent_name: str | None = None
    person_name: str | None = None
    gender: Gender = "unknown"

    @model_validator(mode="after")
    def validate_required_fields(self) -> "AgentIntent":
        required = {
            "relationship_query": ("source_name", "target_name"),
            "relative_lookup": ("source_name", "relation_type"),
            "create_person": ("person_name",),
            "create_child": ("parent_name", "person_name"),
        }[self.kind]
        if any(not getattr(self, field) for field in required):
            raise ValueError(f"{self.kind} 缺少必要字段")
        return self


class AgentQuery(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class SourceCitation(BaseModel):
    id: str
    title: str
    verification_status: VerificationStatus


class AgentAnswer(BaseModel):
    type: Literal["answer"] = "answer"
    answer: str
    relationship: KinshipResponse
    sources: list[SourceCitation]
    verification_status: VerificationStatus


class RelativeListAnswer(BaseModel):
    type: Literal["relative_list"] = "relative_list"
    answer: str
    relation_type: RelativeType
    relationships: list[KinshipResponse]
    sources: list[SourceCitation]
    verification_status: VerificationStatus


class DraftPreview(BaseModel):
    type: Literal["draft"] = "draft"
    draft_id: str
    status: Literal["pending"] = "pending"
    summary: str
    payload: dict


class DraftResponse(BaseModel):
    id: str
    status: Literal["pending", "confirmed", "rejected"]
    raw_input: str
    payload: dict
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None
