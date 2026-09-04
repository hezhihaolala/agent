from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models import Source
from ..schemas import (
    SourceDetailResponse,
    SourceLinkCreate,
    SourceLinkResponse,
    SourceResponse,
)
from ..services.archives import (
    ArchiveConflict,
    ArchiveNotFound,
    ArchiveService,
    ArchiveTooLarge,
    UnsupportedArchive,
)
from .auth import CurrentSession, DbSession, WriteSession


router = APIRouter(prefix="/api/sources", tags=["archives"])


def archive_service(
    request: Request, db: DbSession, current: WriteSession
) -> ArchiveService:
    return ArchiveService(db, request.app.state.settings, current.user_id)


@router.post("", response_model=SourceResponse, status_code=201)
async def upload_source(
    request: Request,
    db: DbSession,
    current: WriteSession,
    title: str = Form(min_length=1, max_length=200),
    source_type: str = Form(),
    era: str | None = Form(default=None),
    provenance: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    verification_status: str = Form(default="unverified"),
    file: UploadFile = File(),
):
    if source_type not in {"image", "document", "text"}:
        raise HTTPException(status_code=422, detail="资料类型无效")
    if verification_status not in {"verified", "unverified", "conflicting"}:
        raise HTTPException(status_code=422, detail="核实状态无效")
    content = await file.read(request.app.state.settings.max_upload_bytes + 1)
    service = ArchiveService(db, request.app.state.settings, current.user_id)
    try:
        return service.create_source(
            title=title,
            source_type=source_type,
            era=era,
            provenance=provenance,
            notes=notes,
            verification_status=verification_status,
            original_filename=file.filename or "unnamed",
            media_type=file.content_type or "application/octet-stream",
            content=content,
        )
    except UnsupportedArchive as error:
        raise HTTPException(status_code=415, detail=str(error)) from error
    except ArchiveTooLarge as error:
        raise HTTPException(status_code=413, detail=str(error)) from error


@router.get("", response_model=list[SourceResponse])
def list_sources(db: DbSession, _: CurrentSession):
    return db.scalars(select(Source).order_by(Source.created_at.desc())).all()


@router.get("/{source_id}", response_model=SourceDetailResponse)
def source_detail(source_id: str, db: DbSession, _: CurrentSession):
    source = db.scalar(
        select(Source)
        .where(Source.id == source_id)
        .options(selectinload(Source.links))
    )
    if source is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    return source


@router.get("/{source_id}/download")
def download_source(source_id: str, request: Request, db: DbSession, _: CurrentSession):
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    path = request.app.state.settings.archive_dir / source.storage_name
    if not path.is_file() or path.parent.resolve() != Path(
        request.app.state.settings.archive_dir
    ).resolve():
        raise HTTPException(status_code=404, detail="资料文件不存在")
    return FileResponse(
        path,
        media_type=source.media_type,
        filename=source.original_filename,
    )


@router.post("/{source_id}/links", response_model=SourceLinkResponse, status_code=201)
def link_source(
    source_id: str,
    payload: SourceLinkCreate,
    service: ArchiveService = Depends(archive_service),
):
    try:
        return service.add_link(source_id, payload)
    except ArchiveNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ArchiveConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
