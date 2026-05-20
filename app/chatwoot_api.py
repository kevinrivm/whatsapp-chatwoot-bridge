import httpx
from app.config import settings

_BASE = f"{settings.chatwoot_base_url}/api/v1/accounts/{settings.chatwoot_account_id}"
_HEADERS = {"api_access_token": settings.chatwoot_api_token, "Content-Type": "application/json"}


async def find_or_create_contact(phone: str, name: str = "") -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{_BASE}/contacts/search",
            params={"q": phone, "include_contacts": True},
            headers=_HEADERS,
        )
        for c in r.json().get("payload", {}).get("contacts", []):
            stored = (c.get("phone_number") or "").replace("+", "").replace(" ", "")
            if phone in stored or stored in phone:
                return c

        r = await client.post(
            f"{_BASE}/contacts",
            json={"name": name or phone, "phone_number": f"+{phone}"},
            headers=_HEADERS,
        )
        data = r.json()
        return data.get("payload", data)


async def find_or_create_conversation(contact_id: int) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{_BASE}/contacts/{contact_id}/conversations", headers=_HEADERS)
        for conv in r.json().get("payload", []):
            if (
                conv.get("inbox_id") == settings.chatwoot_inbox_id
                and conv.get("status") in ("open", "pending")
            ):
                return conv

        r = await client.post(
            f"{_BASE}/conversations",
            json={"contact_id": contact_id, "inbox_id": settings.chatwoot_inbox_id},
            headers=_HEADERS,
        )
        return r.json()


async def send_incoming_message(conversation_id: int, text: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{_BASE}/conversations/{conversation_id}/messages",
            json={"content": text, "message_type": "incoming", "private": False},
            headers=_HEADERS,
        )
        return r.json()
