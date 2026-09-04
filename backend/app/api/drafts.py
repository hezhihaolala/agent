from fastapi import APIRouter, HTTPException

from ..schemas import DraftResponse
from ..services.drafts import (
    DraftConflict,
    DraftNotFound,
    DraftService,
    draft_payload,
)
from .auth import CurrentSession, DbSession, WriteSession


router = APIRouter(prefix="/api/change-drafts", tags=["drafts"])


def response_for(draft) -> DraftResponse:
    return DraftResponse(
        id=draft.id,
        status=draft.status,
        raw_input=draft.raw_input,
        payload=draft_payload(draft),
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        confirmed_at=draft.confirmed_at,
    )


@router.get("/{draft_id}", response_model=DraftResponse)
def get_draft(draft_id: str, db: DbSession, current: CurrentSession):
    try:
        return response_for(DraftService(db, current.user_id).get(draft_id))
    except DraftNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{draft_id}/confirm", response_model=DraftResponse)
def confirm_draft(draft_id: str, db: DbSession, current: WriteSession):
    try:
        return response_for(DraftService(db, current.user_id).confirm(draft_id))
    except DraftNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DraftConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{draft_id}/reject", response_model=DraftResponse)
def reject_draft(draft_id: str, db: DbSession, current: WriteSession):
    try:
        return response_for(DraftService(db, current.user_id).reject(draft_id))
    except DraftNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DraftConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
