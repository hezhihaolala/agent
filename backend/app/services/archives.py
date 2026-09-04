import hashlib
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from ..config import Settings
from ..models import AuditLog, Person, Relationship, Source, SourceLink
from ..schemas import SourceLinkCreate
from ..security import utcnow


ALLOWED_MEDIA_TYPES = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
}


class ArchiveError(Exception):
    pass


class UnsupportedArchive(ArchiveError):
    pass


class ArchiveTooLarge(ArchiveError):
    pass


class ArchiveNotFound(ArchiveError):
    pass


class ArchiveConflict(ArchiveError):
    pass


class ArchiveService:
    def __init__(self, db: Session, settings: Settings, user_id: str):
        self.db = db
        self.settings = settings
        self.user_id = user_id

    def create_source(
        self,
        *,
        title: str,
        source_type: str,
        era: str | None,
        provenance: str | None,
        notes: str | None,
        verification_status: str,
        original_filename: str,
        media_type: str,
        content: bytes,
    ) -> Source:
        suffix = Path(original_filename).suffix.lower()
        if suffix not in ALLOWED_MEDIA_TYPES or media_type not in ALLOWED_MEDIA_TYPES[suffix]:
            raise UnsupportedArchive("仅支持 PDF、图片和文字资料")
        if suffix == ".pdf" and not content.startswith(b"%PDF-"):
            raise UnsupportedArchive("PDF 文件内容无效")
        if len(content) > self.settings.max_upload_bytes:
            raise ArchiveTooLarge("文件超过上传大小限制")

        storage_name = f"{uuid4().hex}{suffix}"
        destination = self.settings.archive_dir / storage_name
        destination.write_bytes(content)
        source = Source(
            title=title,
            source_type=source_type,
            era=era,
            provenance=provenance,
            notes=notes,
            verification_status=verification_status,
            original_filename=Path(original_filename).name,
            storage_name=storage_name,
            media_type=media_type,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            created_at=utcnow(),
        )
        try:
            self.db.add(source)
            self.db.flush()
            self._audit("source.created", source.id, f"上传资料：{source.title}")
            self.db.commit()
        except Exception:
            destination.unlink(missing_ok=True)
            self.db.rollback()
            raise
        return source

    def add_link(self, source_id: str, payload: SourceLinkCreate) -> SourceLink:
        source = self.db.get(Source, source_id)
        if source is None:
            raise ArchiveNotFound("资料不存在")
        entity_model = Person if payload.entity_type == "person" else Relationship
        if self.db.get(entity_model, payload.entity_id) is None:
            raise ArchiveNotFound("关联对象不存在")
        for link in source.links:
            if (
                link.entity_type == payload.entity_type
                and link.entity_id == payload.entity_id
                and link.field_name == payload.field_name
            ):
                raise ArchiveConflict("证据关联已存在")

        link = SourceLink(
            source_id=source.id,
            **payload.model_dump(),
            created_at=utcnow(),
        )
        self.db.add(link)
        self.db.flush()
        self._audit("source.linked", source.id, f"关联{payload.entity_type}证据")
        self.db.commit()
        return link

    def _audit(self, action: str, entity_id: str, summary: str):
        self.db.add(
            AuditLog(
                user_id=self.user_id,
                action=action,
                entity_type="source",
                entity_id=entity_id,
                summary=summary,
                created_at=utcnow(),
            )
        )
