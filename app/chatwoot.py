import re
from fastapi import APIRouter, Request
from app.whatsapp_api import send_text_message

router = APIRouter()


def _normalize_to_wa(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


@router.post("/chatwoot-events")
async def handle_chatwoot_event(request: Request):
    try:
        body = await request.json()

        if body.get("event") != "message_created":
            return {"status": "ignored"}

        if body.get("message_type") != "outgoing":
            return {"status": "ignored"}

        content = body.get("content", "")
        if not content:
            return {"status": "no_content"}

        phone = (
            body.get("conversation", {})
            .get("meta", {})
            .get("sender", {})
            .get("phone_number", "")
        )
        phone = _normalize_to_wa(phone)
        if not phone:
            return {"status": "no_phone"}

        await send_text_message(phone, content)
        return {"status": "sent"}

    except Exception as e:
        print(f"[chatwoot-events] error: {e}")
        return {"status": "error"}
