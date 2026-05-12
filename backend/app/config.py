from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///beicaoji.db"
    redis_url: str = "redis://localhost:6379/0"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.minimaxi.com/anthropic"
    llm_model: str = "MiniMax-M2.7"
    secret_key: str = "change-me-in-production"
    wechat_appid: str = ""
    wechat_secret: str = ""
    youzan_client_id: str = ""
    youzan_client_secret: str = ""
    youzan_access_token: str = ""
    youzan_shop_id: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()