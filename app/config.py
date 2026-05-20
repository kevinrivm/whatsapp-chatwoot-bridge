from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    meta_verify_token: str
    meta_access_token: str
    meta_phone_number_id: str
    meta_api_version: str = "v21.0"

    chatwoot_base_url: str
    chatwoot_api_token: str
    chatwoot_account_id: int
    chatwoot_inbox_id: int
    chatwoot_webhook_secret: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
