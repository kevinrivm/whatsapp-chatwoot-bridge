import copy
import re
import traceback

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.config import settings

router = APIRouter()

_BSUID_RE = re.compile(r"^[A-Z]{2}\.[A-Za-z0-9+/=_-]{10,}$")


def _is_bsuid(value: str) -> bool:
    return bool(_BSUID_RE.match(value or ""))


def _normalize(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
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

        payload = copy.deepcopy(body)
        phone_number = None

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                if not phone_number:
                    phone_number = value.get("metadata", {}).get("display_phone_number", "")

                contacts = value.get("contacts", [])
                messages = value.get("messages", [])
                if not messages or not contacts:
                    continue

                wa_id = contacts[0].get("wa_id", "")
                from_number = messages[0].get("from", "")

                if _is_bsuid(wa_id):
                    normalized = _normalize(from_number)
                    contacts[0]["wa_id"] = normalized
                    print(f"[webhook] BSUID {wa_id} → {normalized}")
                else:
                    # Normalize even regular numbers (e.g. missing trunk digit)
                    normalized = _normalize(wa_id or from_number)
                    if normalized != wa_id:
                        contacts[0]["wa_id"] = normalized
                        print(f"[webhook] normalized {wa_id} → {normalized}")

        # Use configured phone number if set (avoids trunk-digit mismatch with Meta's display_phone_number)
        target_phone = settings.chatwoot_whatsapp_phone or phone_number
        if not target_phone:
            print("[webhook] no phone number available, cannot forward")
            return {"status": "ok"}

        # Overwrite display_phone_number in every change value so Chatwoot's inbox lookup matches
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                meta = change.get("value", {}).get("metadata", {})
                if meta:
                    meta["display_phone_number"] = target_phone

        chatwoot_url = f"{settings.chatwoot_base_url}/webhooks/whatsapp/+{target_phone}"
        import json as _json
        print(f"[webhook] forwarding to {chatwoot_url}")
        print(f"[webhook] payload: {_json.dumps(payload)[:600]}")
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(chatwoot_url, json=payload)
            print(f"[webhook] chatwoot response: {r.status_code} {r.text[:300]}")

    except Exception as e:
        print(f"[webhook] error: {e}\n{traceback.format_exc()}")

    return {"status": "ok"}
