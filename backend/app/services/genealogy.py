from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from ..models import AuditLog, Person, Relationship
from ..schemas import PersonCreate, PersonUpdate, RelationshipCreate
from ..security import utcnow


class GenealogyError(Exception):
    pass


class RelationshipConflict(GenealogyError):
    pass


class EntityNotFound(GenealogyError):
    pass


class GenealogyService:
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    def _audit(self, action: str, entity_type: str, entity_id: str, summary: str):
        self.db.add(
            AuditLog(
                user_id=self.user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                summary=summary,
                created_at=utcnow(),
            )
        )

    def create_person(self, payload: PersonCreate) -> Person:
        now = utcnow()
        person = Person(**payload.model_dump(), created_at=now, updated_at=now)
        self.db.add(person)
        self.db.flush()
        self._audit("person.created", "person", person.id, f"新增人物：{person.name}")
        self.db.commit()
        return person

    def update_person(self, person_id: str, payload: PersonUpdate) -> Person:
        person = self.db.get(Person, person_id)
        if person is None:
            raise EntityNotFound("人物不存在")
        for name, value in payload.model_dump(exclude_unset=True).items():
            setattr(person, name, value)
        person.updated_at = utcnow()
        self._audit("person.updated", "person", person.id, f"更新人物：{person.name}")
        self.db.commit()
        return person

    def delete_person(self, person_id: str) -> None:
        person = self.db.get(Person, person_id)
        if person is None:
            raise EntityNotFound("人物不存在")
        self.db.execute(
            delete(Relationship).where(
                or_(
                    Relationship.person_id == person_id,
                    Relationship.relative_id == person_id,
                )
            )
        )
        self.db.delete(person)
        self._audit("person.deleted", "person", person_id, f"删除人物：{person.name}")
        self.db.commit()

    def add_relationship(self, payload: RelationshipCreate) -> Relationship:
        if payload.person_id == payload.relative_id:
            raise RelationshipConflict("不能与自己建立关系")
        if self.db.get(Person, payload.person_id) is None or self.db.get(
            Person, payload.relative_id
        ) is None:
            raise EntityNotFound("人物不存在")

        conditions = [
            Relationship.kind == payload.kind,
            Relationship.person_id == payload.person_id,
            Relationship.relative_id == payload.relative_id,
        ]
        if payload.kind == "spouse":
            duplicate = self.db.scalar(
                select(Relationship).where(
                    Relationship.kind == "spouse",
                    or_(
                        (
                            (Relationship.person_id == payload.person_id)
                            & (Relationship.relative_id == payload.relative_id)
                        ),
                        (
                            (Relationship.person_id == payload.relative_id)
                            & (Relationship.relative_id == payload.person_id)
                        ),
                    ),
                )
            )
        else:
            duplicate = self.db.scalar(select(Relationship).where(*conditions))
        if duplicate is not None:
            raise RelationshipConflict("关系已存在")
        if payload.kind == "parent" and self._creates_parent_cycle(
            payload.person_id, payload.relative_id
        ):
            raise RelationshipConflict("该父母关系会形成祖先循环")

        relationship = Relationship(
            **payload.model_dump(),
            created_at=utcnow(),
        )
        self.db.add(relationship)
        self.db.flush()
        self._audit(
            "relationship.created",
            "relationship",
            relationship.id,
            f"新增{relationship.kind}关系",
        )
        self.db.commit()
        return relationship

    def _creates_parent_cycle(self, child_id: str, parent_id: str) -> bool:
        relationships = self.db.scalars(
            select(Relationship).where(Relationship.kind == "parent")
        ).all()
        parents: dict[str, list[str]] = {}
        for relationship in relationships:
            parents.setdefault(relationship.person_id, []).append(
                relationship.relative_id
            )
        pending = [parent_id]
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current == child_id:
                return True
            if current not in visited:
                visited.add(current)
                pending.extend(parents.get(current, []))
        return False

    def delete_relationship(self, relationship_id: str) -> None:
        relationship = self.db.get(Relationship, relationship_id)
        if relationship is None:
            raise EntityNotFound("关系不存在")
        self.db.delete(relationship)
        self._audit(
            "relationship.deleted",
            "relationship",
            relationship_id,
            "删除亲属关系",
        )
        self.db.commit()
