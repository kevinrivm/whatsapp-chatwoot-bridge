import re
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from app.config import settings
from app.chatwoot_api import find_or_create_contact, find_or_create_conversation, send_incoming_message

router = APIRouter()

_BSUID_RE = re.compile(r"^[A-Z]{2}\.[A-Za-z0-9+/=_-]{10,}$")


def _is_bsuid(value: str) -> bool:
    return bool(_BSUID_RE.match(value or ""))


def _normalize(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    # Mexico: 52 + 10 digits without the trunk 1 → insert it
    if digits.startswith("52") and not digits.startswith("521") and len(digits) == 12:
        return "521" + digits[2:]
    return digits


@router.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge", "")
    if mode == "subscribe" and token == settings.meta_verify_token:
        return PlainTextResponse(challenge)
    return PlainTextResponse("forbidden", status_code=403)


@router.post("/webhook")
async def receive(request: Request):
    try:
        body = await request.json()

        if body.get("object") != "whatsapp_business_account":
            return {"status": "ignored"}

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                if not messages:
                    continue

                message = messages[0]
                if message.get("type") != "text":
                    continue

                text = message.get("text", {}).get("body", "")
                from_number = message.get("from", "")
                wa_id = contacts[0].get("wa_id", "") if contacts else ""
                contact_name = (
                    contacts[0].get("profile", {}).get("name", "") if contacts else ""
                )

                # When Meta sends a BSUID in wa_id, fall back to the `from` field
                phone = _normalize(from_number if _is_bsuid(wa_id) else (wa_id or from_number))

                contact = await find_or_create_contact(phone, contact_name)
                conversation = await find_or_create_conversation(contact["id"])
                await send_incoming_message(conversation["id"], text)

    except Exception as e:
        print(f"[webhook] error: {e}")

    # Always return 200 so Meta does not retry
    return {"status": "ok"}
