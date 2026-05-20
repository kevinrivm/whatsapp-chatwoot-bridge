import httpx
from app.config import settings

_BASE = f"{settings.chatwoot_base_url}/api/v1/accounts/{settings.chatwoot_account_id}"
_HEADERS = {"api_access_token": settings.chatwoot_api_token, "Content-Type": "application/json"}


def _payload(data) -> list | dict:
    """Unwrap Chatwoot payload — some endpoints return the data directly, others wrap it."""
    if isinstance(data, list):
        return data
    return data.get("payload", data)


async def find_or_create_contact(phone: str, name: str = "") -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{_BASE}/contacts/search",
            params={"q": phone, "include_contacts": True},
            headers=_HEADERS,
        )
        search_data = r.json()
        print(f"[chatwoot_api] search {phone} → {r.status_code} {str(search_data)[:200]}")
        raw = search_data if isinstance(search_data, dict) else {}
        contacts = raw.get("payload", {}).get("contacts", []) if isinstance(raw.get("payload"), dict) else []
        for c in contacts:
            stored = (c.get("phone_number") or "").replace("+", "").replace(" ", "")
            if phone in stored or stored in phone:
                print(f"[chatwoot_api] found existing contact id={c.get('id')}")
                return c

        r = await client.post(
            f"{_BASE}/contacts",
            json={"name": name or phone, "phone_number": f"+{phone}"},
            headers=_HEADERS,
        )
        data = r.json()
        print(f"[chatwoot_api] create contact → {r.status_code} {str(data)[:200]}")
        result = _payload(data)
        if isinstance(result, list):
            result = result[0] if result else {}
        return result


async def find_or_create_conversation(contact_id: int) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{_BASE}/contacts/{contact_id}/conversations", headers=_HEADERS)
        data = r.json()
        print(f"[chatwoot_api] conversations for contact {contact_id} → {r.status_code} {str(data)[:200]}")
        conversations = data if isinstance(data, list) else data.get("payload", [])
        for conv in conversations:
            if (
                conv.get("inbox_id") == settings.chatwoot_inbox_id
                and conv.get("status") in ("open", "pending")
            ):
                print(f"[chatwoot_api] reusing conversation id={conv.get('id')}")
                return conv

        r = await client.post(
            f"{_BASE}/conversations",
            json={"contact_id": contact_id, "inbox_id": settings.chatwoot_inbox_id},
            headers=_HEADERS,
        )
        data = r.json()
        print(f"[chatwoot_api] create conversation → {r.status_code} {str(data)[:200]}")
        return data


async def send_incoming_message(conversation_id: int, text: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{_BASE}/conversations/{conversation_id}/messages",
            json={"content": text, "message_type": "incoming", "private": False},
            headers=_HEADERS,
        )
        data = r.json()
        print(f"[chatwoot_api] send message to conv {conversation_id} → {r.status_code} {str(data)[:200]}")
        return data
