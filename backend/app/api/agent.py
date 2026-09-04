from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from ..agent.client import ModelOutputError, ModelUnavailable
from ..agent.orchestrator import AgentOrchestrator, AmbiguousPerson, MissingRelationship
from ..schemas import AgentAnswer, AgentQuery, DraftPreview
from ..services.drafts import DraftConflict, DraftNotFound
from .auth import DbSession, WriteSession


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/query", response_model=AgentAnswer | DraftPreview)
def query_agent(payload: AgentQuery, request: Request, db: DbSession, current: WriteSession):
    orchestrator = AgentOrchestrator(
        db,
        request.app.state.model_client,
        current.user_id,
        request.app.state.settings.model_name,
    )
    try:
        return orchestrator.query(payload.message)
    except (TimeoutError, ModelUnavailable) as error:
        raise HTTPException(status_code=503, detail="模型服务暂时不可用") from error
    except (ModelOutputError, ValidationError, ValueError) as error:
        raise HTTPException(status_code=502, detail="模型返回的结构化结果无效") from error
    except AmbiguousPerson as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (MissingRelationship, DraftNotFound) as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DraftConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
