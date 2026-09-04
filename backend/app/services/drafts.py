import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditLog, ChangeDraft, Person, Relationship
from ..schemas import AgentIntent
from ..security import utcnow


class DraftError(Exception):
    pass


class DraftNotFound(DraftError):
    pass


class DraftConflict(DraftError):
    pass


class DraftService:
    def __init__(self, db: Session, user_id: str, model_name: str | None = None):
        self.db = db
        self.user_id = user_id
        self.model_name = model_name

    def create(self, raw_input: str, intent: AgentIntent) -> ChangeDraft:
        payload = self._validated_payload(intent)
        now = utcnow()
        draft = ChangeDraft(
            user_id=self.user_id,
            status="pending",
            raw_input=raw_input,
            payload_json=json.dumps(payload, ensure_ascii=False),
            prompt_version="v1",
            model_name=self.model_name,
            created_at=now,
            updated_at=now,
        )
        self.db.add(draft)
        self.db.commit()
        return draft

    def _validated_payload(self, intent: AgentIntent) -> dict:
        existing = self.db.scalars(
            select(Person).where(Person.name == intent.person_name)
        ).all()
        if existing:
            raise DraftConflict("同名人物已存在，请先核对")
        payload = {
            "operation": intent.kind,
            "person": {"name": intent.person_name, "gender": intent.gender},
        }
        if intent.kind == "create_child":
            parents = self.db.scalars(
                select(Person).where(Person.name == intent.parent_name)
            ).all()
            if not parents:
                raise DraftNotFound("未找到草稿中的父母人物")
            if len(parents) > 1:
                raise DraftConflict("父母姓名存在重名，请先选择具体人物")
            payload["parent_id"] = parents[0].id
            payload["parent_name"] = parents[0].name
        return payload

    def get(self, draft_id: str) -> ChangeDraft:
        draft = self.db.get(ChangeDraft, draft_id)
        if draft is None:
            raise DraftNotFound("变更草稿不存在")
        return draft

    def confirm(self, draft_id: str) -> ChangeDraft:
        draft = self.get(draft_id)
        if draft.status != "pending":
            raise DraftConflict("该草稿已处理，不能重复确认")
        payload = json.loads(draft.payload_json)
        if self.db.scalar(
            select(Person).where(Person.name == payload["person"]["name"])
        ):
            raise DraftConflict("同名人物已存在，草稿需要重新核对")
        if payload["operation"] == "create_child" and self.db.get(
            Person, payload["parent_id"]
        ) is None:
            raise DraftConflict("父母人物已不存在，草稿需要重新核对")

        now = utcnow()
        person = Person(
            name=payload["person"]["name"],
            gender=payload["person"]["gender"],
            verification_status="unverified",
            created_at=now,
            updated_at=now,
        )
        self.db.add(person)
        self.db.flush()
        if payload["operation"] == "create_child":
            self.db.add(
                Relationship(
                    kind="parent",
                    person_id=person.id,
                    relative_id=payload["parent_id"],
                    verification_status="unverified",
                    created_at=now,
                )
            )
        draft.status = "confirmed"
        draft.updated_at = now
        draft.confirmed_at = now
        self.db.add(
            AuditLog(
                user_id=self.user_id,
                action="draft.confirmed",
                entity_type="change_draft",
                entity_id=draft.id,
                summary=f"确认新增人物：{person.name}",
                created_at=now,
            )
        )
        self.db.commit()
        return draft

    def reject(self, draft_id: str) -> ChangeDraft:
        draft = self.get(draft_id)
        if draft.status != "pending":
            raise DraftConflict("该草稿已处理")
        draft.status = "rejected"
        draft.updated_at = utcnow()
        self.db.add(
            AuditLog(
                user_id=self.user_id,
                action="draft.rejected",
                entity_type="change_draft",
                entity_id=draft.id,
                summary="拒绝智能体变更草稿",
                created_at=draft.updated_at,
            )
        )
        self.db.commit()
        return draft


def draft_payload(draft: ChangeDraft) -> dict:
    return json.loads(draft.payload_json)
