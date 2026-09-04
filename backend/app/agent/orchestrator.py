from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..domain.kinship import find_relationship_path
from ..models import Person, Relationship, Source, SourceLink
from ..schemas import (
    AgentAnswer,
    AgentIntent,
    DraftPreview,
    KinshipResponse,
    KinshipStepResponse,
    SourceCitation,
)
from ..services.drafts import DraftService, draft_payload


class AgentRequestError(Exception):
    pass


class AmbiguousPerson(AgentRequestError):
    pass


class MissingRelationship(AgentRequestError):
    pass


class AgentOrchestrator:
    def __init__(self, db: Session, model_client, user_id: str, model_name: str | None):
        self.db = db
        self.model_client = model_client
        self.user_id = user_id
        self.model_name = model_name

    def query(self, message: str) -> AgentAnswer | DraftPreview:
        intent = AgentIntent.model_validate(self.model_client.parse_request(message))
        if intent.kind == "relationship_query":
            return self._relationship_answer(intent)
        draft = DraftService(self.db, self.user_id, self.model_name).create(
            message, intent
        )
        payload = draft_payload(draft)
        action = "新增子女" if intent.kind == "create_child" else "新增人物"
        return DraftPreview(
            draft_id=draft.id,
            summary=f"{action}：{intent.person_name}",
            payload=payload,
        )

    def _one_person(self, name: str) -> Person:
        people = self.db.scalars(select(Person).where(Person.name == name)).all()
        if not people:
            raise MissingRelationship(f"未找到人物：{name}")
        if len(people) > 1:
            raise AmbiguousPerson(f"姓名“{name}”存在重名，请选择具体人物")
        return people[0]

    def _relationship_answer(self, intent: AgentIntent) -> AgentAnswer:
        source_person = self._one_person(intent.source_name or "")
        target_person = self._one_person(intent.target_name or "")
        people = self.db.scalars(select(Person)).all()
        relationships = self.db.scalars(select(Relationship)).all()
        result = find_relationship_path(
            people, relationships, source_person.id, target_person.id
        )
        if result is None:
            raise MissingRelationship("未找到可靠的亲属关系路径")

        path_ids = [step.person_id for step in result.steps]
        path_edges = {
            frozenset((path_ids[index], path_ids[index + 1]))
            for index in range(len(path_ids) - 1)
        }
        relationship_ids = [
            relationship.id
            for relationship in relationships
            if frozenset((relationship.person_id, relationship.relative_id))
            in path_edges
        ]
        linked_sources = self.db.scalars(
            select(Source)
            .join(SourceLink)
            .where(
                or_(
                    (
                        (SourceLink.entity_type == "person")
                        & SourceLink.entity_id.in_(path_ids)
                    ),
                    (
                        (SourceLink.entity_type == "relationship")
                        & SourceLink.entity_id.in_(relationship_ids)
                    ),
                )
            )
            .distinct()
        ).all()
        citations = [
            SourceCitation(
                id=source.id,
                title=source.title,
                verification_status=source.verification_status,
            )
            for source in linked_sources
        ]
        if any(source.verification_status == "conflicting" for source in linked_sources):
            status = "conflicting"
            suffix = "关联资料存在冲突，结论待核实。"
        elif linked_sources and all(
            source.verification_status == "verified" for source in linked_sources
        ):
            status = "verified"
            suffix = "结论来自已核实资料。"
        else:
            status = "unverified"
            suffix = "当前来源不足，结论待核实。"
        answer = (
            f"{target_person.name}是{source_person.name}的{result.label}。{suffix}"
        )
        return AgentAnswer(
            answer=answer,
            relationship=KinshipResponse(
                label=result.label,
                steps=[
                    KinshipStepResponse(
                        person_id=step.person_id,
                        person_name=step.person_name,
                    )
                    for step in result.steps
                ],
            ),
            sources=citations,
            verification_status=status,
        )
