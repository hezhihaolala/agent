from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select

from ..domain.kinship import find_relationship_path
from ..models import AuditLog, Person, Relationship
from ..schemas import (
    AuditLogResponse,
    KinshipResponse,
    PersonCreate,
    PersonResponse,
    PersonUpdate,
    RelationshipCreate,
    RelationshipResponse,
)
from ..services.genealogy import (
    EntityNotFound,
    GenealogyService,
    RelationshipConflict,
)
from .auth import CurrentSession, DbSession, WriteSession


router = APIRouter(tags=["genealogy"])


def service(db: DbSession, current: WriteSession) -> GenealogyService:
    return GenealogyService(db, current.user_id)


def handle_error(error: Exception):
    if isinstance(error, RelationshipConflict):
        raise HTTPException(status_code=409, detail=str(error)) from error
    raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/api/persons", response_model=list[PersonResponse])
def list_people(db: DbSession, _: CurrentSession):
    return db.scalars(select(Person).order_by(Person.created_at)).all()


@router.post("/api/persons", response_model=PersonResponse, status_code=201)
def create_person(payload: PersonCreate, genealogy: GenealogyService = Depends(service)):
    return genealogy.create_person(payload)


@router.patch("/api/persons/{person_id}", response_model=PersonResponse)
def update_person(
    person_id: str,
    payload: PersonUpdate,
    genealogy: GenealogyService = Depends(service),
):
    try:
        return genealogy.update_person(person_id, payload)
    except EntityNotFound as error:
        handle_error(error)


@router.delete("/api/persons/{person_id}", status_code=204)
def delete_person(
    person_id: str,
    genealogy: GenealogyService = Depends(service),
):
    try:
        genealogy.delete_person(person_id)
    except EntityNotFound as error:
        handle_error(error)
    return Response(status_code=204)


@router.get("/api/relationships", response_model=list[RelationshipResponse])
def list_relationships(db: DbSession, _: CurrentSession):
    return db.scalars(select(Relationship).order_by(Relationship.created_at)).all()


@router.post(
    "/api/relationships",
    response_model=RelationshipResponse,
    status_code=201,
)
def create_relationship(
    payload: RelationshipCreate,
    genealogy: GenealogyService = Depends(service),
):
    try:
        return genealogy.add_relationship(payload)
    except (EntityNotFound, RelationshipConflict) as error:
        handle_error(error)


@router.delete("/api/relationships/{relationship_id}", status_code=204)
def delete_relationship(
    relationship_id: str,
    genealogy: GenealogyService = Depends(service),
):
    try:
        genealogy.delete_relationship(relationship_id)
    except EntityNotFound as error:
        handle_error(error)
    return Response(status_code=204)


@router.get("/api/relationships/path", response_model=KinshipResponse)
def relationship_path(source_id: str, target_id: str, db: DbSession, _: CurrentSession):
    people = db.scalars(select(Person)).all()
    relationships = db.scalars(select(Relationship)).all()
    result = find_relationship_path(people, relationships, source_id, target_id)
    if result is None:
        raise HTTPException(status_code=404, detail="未找到可靠的亲属关系路径")
    return result


@router.get("/api/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(db: DbSession, _: CurrentSession):
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc())).all()
