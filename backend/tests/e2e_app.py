import re
from pathlib import Path

from backend.app.config import Settings
from backend.app.main import create_app


class BrowserTestModel:
    def parse_request(self, text: str) -> dict:
        if text.startswith("新增"):
            return {
                "kind": "create_person",
                "person_name": text.removeprefix("新增").strip(),
                "gender": "unknown",
            }
        match = re.fullmatch(r"(.+?)[与和](.+?)是什么关系[？?]?", text.strip())
        if match:
            return {
                "kind": "relationship_query",
                "source_name": match.group(1),
                "target_name": match.group(2),
            }
        return {"kind": "unexpected"}


data_dir = Path("data/e2e")
settings = Settings(
    environment="test",
    database_url=f"sqlite:///{data_dir / 'guiyuan-e2e.db'}",
    archive_dir=data_dir / "archives",
    admin_username="admin",
    admin_password="e2e-password",
    model_name="browser-test-model",
)
app = create_app(settings, model_client=BrowserTestModel())
