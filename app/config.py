import json

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    meta_verify_token: str
    meta_access_token: str
    meta_api_version: str = "v21.0"

    chatwoot_base_url: str
    chatwoot_api_token: str
    chatwoot_account_id: int
    chatwoot_webhook_secret: str = ""

    # JSON routing table — one entry per WhatsApp number.
    # phone_number_id : Meta Phone Number ID (metadata.phone_number_id in webhook payload)
    # chatwoot_phone  : digits only, no +, exactly as registered in the Chatwoot inbox
    # inbox_id        : Chatwoot inbox ID (Settings → Inboxes → URL)
    #
    # Example (single number):
    # PHONE_ROUTING=[{"phone_number_id":"761549910376296","chatwoot_phone":"524623749518","inbox_id":1}]
    #
    # Example (multi-number):
    # PHONE_ROUTING=[{"phone_number_id":"111...","chatwoot_phone":"524623749518","inbox_id":1},{"phone_number_id":"222...","chatwoot_phone":"521XXXXXXXXXX","inbox_id":2}]
    phone_routing: list = []

    @field_validator("phone_routing", mode="before")
    @classmethod
    def parse_routing(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    def route_by_phone_number_id(self, phone_number_id: str) -> dict | None:
        for route in self.phone_routing:
            if route.get("phone_number_id") == phone_number_id:
                return route
        return None

    def route_by_inbox_id(self, inbox_id: int) -> dict | None:
        for route in self.phone_routing:
            if route.get("inbox_id") == inbox_id:
                return route
        return None

    class Config:
        env_file = ".env"


settings = Settings()
