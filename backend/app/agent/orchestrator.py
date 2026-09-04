import re

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
    RelativeListAnswer,
    SourceCitation,
)
from ..services.drafts import DraftService, draft_payload


class AgentRequestError(Exception):
    pass


class AmbiguousPerson(AgentRequestError):
    pass


class MissingRelationship(AgentRequestError):
    pass


LOOKUP_LABELS = {
    "父母": "parents",
    "父亲": "father",
    "母亲": "mother",
    "子女": "children",
    "配偶": "spouses",
    "兄弟姊妹": "siblings",
    "兄弟姐妹": "siblings",
    "堂兄弟姊妹": "paternal_cousins",
    "堂兄弟姐妹": "paternal_cousins",
}
LOOKUP_PATTERN = re.compile(
    rf"^\s*(?P<name>.+?)的(?P<label>{'|'.join(LOOKUP_LABELS)})(?:是|有)?谁[？?]?\s*$"
)
KINSHIP_LABELS = {
    "parents": {"父亲", "母亲", "父母"},
    "father": {"父亲"},
    "mother": {"母亲"},
    "children": {"儿子", "女儿", "子女"},
    "spouses": {"丈夫", "妻子", "配偶"},
    "siblings": {"兄弟", "姐妹", "兄弟姐妹", "兄弟姊妹"},
    "paternal_cousins": {"堂兄弟", "堂姐妹", "堂兄弟姊妹"},
}
RELATION_NAMES = {
    "parents": "父母",
    "father": "父亲",
    "mother": "母亲",
    "children": "子女",
    "spouses": "配偶",
    "siblings": "兄弟姊妹",
    "paternal_cousins": "堂兄弟姊妹",
}


def local_lookup_intent(message: str) -> AgentIntent | None:
    match = LOOKUP_PATTERN.fullmatch(message)
    if match is None:
        return None
    source_name = match.group("name").strip()
    if source_name.startswith(("请问", "请帮", "帮我", "我想", "麻烦")):
        return None
    return AgentIntent(
        kind="relative_lookup",
        source_name=source_name,
        relation_type=LOOKUP_LABELS[match.group("label")],
    )


class AgentOrchestrator:
    def __init__(self, db: Session, model_client, user_id: str, model_name: str | None):
        self.db = db
        self.model_client = model_client
        self.user_id = user_id
        self.model_name = model_name

    def query(self, message: str) -> AgentAnswer | RelativeListAnswer | DraftPreview:
        intent = local_lookup_intent(message)
        if intent is None:
            intent = AgentIntent.model_validate(self.model_client.parse_request(message))
        if intent.kind == "relationship_query":
            return self._relationship_answer(intent)
        if intent.kind == "relative_lookup":
            return self._relative_list_answer(intent)
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
        return self._answer_between(source_person, target_person)

    def _answer_between(self, source_person: Person, target_person: Person) -> AgentAnswer:
        people = self.db.scalars(select(Person)).all()
        relationships = self.db.scalars(select(Relationship)).all()
        result = find_relationship_path(
            people, relationships, source_person.id, target_person.id
        )
        if result is None:
            raise MissingRelationship("未找到可靠的亲属关系路径")

        path_ids = [step.person_id for step in result.steps]
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
                        & SourceLink.entity_id.in_(result.relationship_ids)
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

    def _relative_list_answer(self, intent: AgentIntent) -> RelativeListAnswer:
        source_person = self._one_person(intent.source_name or "")
        relation_type = intent.relation_type or "parents"
        people = self.db.scalars(
            select(Person).order_by(Person.created_at, Person.id)
        ).all()
        relationships = self.db.scalars(select(Relationship)).all()
        answers: list[AgentAnswer] = []
        for person in people:
            if person.id == source_person.id:
                continue
            result = find_relationship_path(
                people, relationships, source_person.id, person.id
            )
            if result is not None and result.label in KINSHIP_LABELS[relation_type]:
                answers.append(self._answer_between(source_person, person))
        relation_name = RELATION_NAMES[relation_type]
        if not answers:
            raise MissingRelationship(f"未找到{source_person.name}的{relation_name}记录")

        citations = {
            citation.id: citation
            for answer in answers
            for citation in answer.sources
        }
        statuses = {answer.verification_status for answer in answers}
        if "conflicting" in statuses:
            status = "conflicting"
            suffix = "关联资料存在冲突，结论待核实。"
        elif statuses == {"verified"}:
            status = "verified"
            suffix = "结论来自已核实资料。"
        else:
            status = "unverified"
            suffix = "当前来源不足，结论待核实。"
        names = "、".join(
            answer.relationship.steps[-1].person_name for answer in answers
        )
        return RelativeListAnswer(
            answer=f"{source_person.name}的{relation_name}是{names}。{suffix}",
            relation_type=relation_type,
            relationships=[answer.relationship for answer in answers],
            sources=list(citations.values()),
            verification_status=status,
        )
