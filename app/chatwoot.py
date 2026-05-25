import hashlib
import hmac
import json
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.whatsapp_api import send_text_message

router = APIRouter()


def _normalize_to_wa(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def _verify_signature(body: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.chatwoot_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/chatwoot-events")
async def handle_chatwoot_event(request: Request):
    try:
        raw = await request.body()

        if settings.chatwoot_webhook_secret:
            sig = request.headers.get("X-Chatwoot-Hmac-Sha256", "")
            if not sig or not _verify_signature(raw, sig):
                return JSONResponse({"status": "unauthorized"}, status_code=401)

        body = json.loads(raw)

        if body.get("event") != "message_created":
            return {"status": "ignored"}

        if body.get("message_type") != "outgoing":
            return {"status": "ignored"}

        content = body.get("content", "")
        if not content:
            return {"status": "no_content"}

        # Identify which inbox sent this reply to find the correct phone_number_id.
        inbox_id = body.get("inbox_id") or body.get("conversation", {}).get("inbox_id")
        if not inbox_id:
            print("[chatwoot-events] no inbox_id in payload")
            return {"status": "no_inbox"}

        route = settings.route_by_inbox_id(int(inbox_id))
        if not route:
            print(f"[chatwoot-events] no route for inbox_id={inbox_id} — check PHONE_ROUTING")
            return {"status": "no_route"}

        phone_number_id = route["phone_number_id"]

        phone = (
            body.get("conversation", {})
            .get("meta", {})
            .get("sender", {})
            .get("phone_number", "")
        )
        phone = _normalize_to_wa(phone)
        if not phone:
            return {"status": "no_phone"}

        await send_text_message(phone, content, phone_number_id)
        return {"status": "sent"}

    except Exception as e:
        print(f"[chatwoot-events] error: {e}")
        return {"status": "error"}
