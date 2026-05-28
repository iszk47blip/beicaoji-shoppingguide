from pathlib import Path
from pydantic_settings import BaseSettings

_DB_PATH = Path(__file__).parent.parent.parent / "beicaoji.db"


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{_DB_PATH.as_posix()}"
    redis_url: str = "redis://localhost:6379/0"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/anthropic"
    llm_model: str = "deepseek-chat"
    secret_key: str = "change-me-in-production"
    admin_username: str = "beicaoji"
    admin_password: str = "beicaoji666"
    admin_token_expire_hours: int = 24
    auto_review_enabled: bool = True
    auto_review_interval_hours: int = 24
    wechat_appid: str = ""
    wechat_secret: str = ""
    youzan_client_id: str = ""
    youzan_client_secret: str = ""
    youzan_access_token: str = ""
    youzan_shop_id: str = ""

    model_config = {
        "env_file": str(Path(__file__).parent.parent / ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()