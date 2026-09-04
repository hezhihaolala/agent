from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AdminSession, AdminUser
from ..schemas import AuthResponse, LoginRequest
from ..security import hash_token, is_expired, new_token, utcnow, verify_password


router = APIRouter(prefix="/api/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]


def get_current_session(
    db: DbSession,
    session_token: Annotated[str | None, Cookie(alias="guiyuan_session")] = None,
) -> AdminSession:
    if not session_token:
        raise HTTPException(status_code=401, detail="未登录")

    session = db.scalar(
        select(AdminSession).where(AdminSession.token_hash == hash_token(session_token))
    )
    if session is None or is_expired(session.expires_at):
        if session is not None:
            db.delete(session)
            db.commit()
        raise HTTPException(status_code=401, detail="登录已失效")
    return session


CurrentSession = Annotated[AdminSession, Depends(get_current_session)]


def require_csrf(
    current: CurrentSession,
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias="guiyuan_csrf")] = None,
) -> AdminSession:
    if (
        not csrf_header
        or not csrf_cookie
        or csrf_header != csrf_cookie
        or hash_token(csrf_header) != current.csrf_hash
    ):
        raise HTTPException(status_code=403, detail="CSRF 校验失败")
    return current


WriteSession = Annotated[AdminSession, Depends(require_csrf)]


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: DbSession):
    user = db.scalar(select(AdminUser).where(AdminUser.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    session_token = new_token()
    csrf_token = new_token()
    settings = request.app.state.settings
    db.add(
        AdminSession(
            user_id=user.id,
            token_hash=hash_token(session_token),
            csrf_hash=hash_token(csrf_token),
            created_at=utcnow(),
            expires_at=utcnow() + timedelta(hours=settings.session_ttl_hours),
        )
    )
    db.commit()

    cookie_options = {
        "secure": settings.session_cookie_secure,
        "samesite": "lax",
        "max_age": settings.session_ttl_hours * 3600,
        "path": "/",
    }
    response.set_cookie(
        "guiyuan_session",
        session_token,
        httponly=True,
        **cookie_options,
    )
    response.set_cookie("guiyuan_csrf", csrf_token, httponly=False, **cookie_options)
    return AuthResponse(username=user.username, csrf_token=csrf_token)


@router.get("/me", response_model=AuthResponse)
def current_user(
    current: CurrentSession,
    csrf_token: Annotated[str | None, Cookie(alias="guiyuan_csrf")] = None,
):
    if not csrf_token or hash_token(csrf_token) != current.csrf_hash:
        raise HTTPException(status_code=401, detail="登录已失效")
    return AuthResponse(username=current.user.username, csrf_token=csrf_token)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    db: DbSession,
    current: WriteSession,
):
    db.delete(current)
    db.commit()
    response.delete_cookie("guiyuan_session", path="/")
    response.delete_cookie("guiyuan_csrf", path="/")
