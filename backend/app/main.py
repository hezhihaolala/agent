from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import select

from .api.auth import router as auth_router
from .config import Settings
from .database import Base, create_database
from .models import AdminUser
from .security import hash_password, utcnow


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings()
    engine, session_factory = create_database(app_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if app_settings.database_url.startswith("sqlite"):
            database_path = app_settings.database_url.removeprefix("sqlite:///")
            if database_path != ":memory:":
                from pathlib import Path

                Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        app_settings.archive_dir.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(engine)
        with session_factory() as session:
            user = session.scalar(
                select(AdminUser).where(
                    AdminUser.username == app_settings.admin_username
                )
            )
            if user is None:
                session.add(
                    AdminUser(
                        username=app_settings.admin_username,
                        password_hash=hash_password(app_settings.admin_password),
                        created_at=utcnow(),
                    )
                )
                session.commit()
        yield
        engine.dispose()

    app = FastAPI(title="归源族谱智能体", lifespan=lifespan)
    app.state.settings = app_settings
    app.state.session_factory = session_factory
    app.include_router(auth_router)

    @app.get("/api/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
