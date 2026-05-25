import copy
import json as _json
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
    """Strip non-digits and fix missing trunk digit for Mexican numbers.

    Mexico: 52XXXXXXXXXX (12 digits, no trunk) → 521XXXXXXXXXX (13 digits).
    Extend here for other countries that have the same trunk-digit issue (e.g. Argentina 549...).
    """
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

        # Extract phone_number_id from the first change to find the routing entry.
        # All changes in a single webhook payload come from the same phone number.
        phone_number_id = None
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                phone_number_id = change.get("value", {}).get("metadata", {}).get("phone_number_id", "")
                if phone_number_id:
                    break
            if phone_number_id:
                break

        route = settings.route_by_phone_number_id(phone_number_id) if phone_number_id else None
        if not route:
            print(f"[webhook] no route for phone_number_id={phone_number_id!r} — check PHONE_ROUTING")
            return {"status": "ok"}

        target_phone = route["chatwoot_phone"]

        # Normalize contacts in every change:
        # 1. Replace BSUID in wa_id with the real phone from `from` field.
        # 2. Normalize trunk digit (e.g. Mexico 52XXXXXXXXXX → 521XXXXXXXXXX).
        # 3. Overwrite display_phone_number with target_phone so Chatwoot's
        #    internal inbox lookup matches (real Meta payloads include trunk digit
        #    in display_phone_number but inboxes are registered without it).
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                contacts = value.get("contacts", [])
                messages = value.get("messages", [])

                if messages and contacts:
                    wa_id = contacts[0].get("wa_id", "")
                    from_number = messages[0].get("from", "")

                    if _is_bsuid(wa_id):
                        normalized = _normalize(from_number)
                        contacts[0]["wa_id"] = normalized
                        print(f"[webhook] BSUID {wa_id} → {normalized}")
                    else:
                        normalized = _normalize(wa_id or from_number)
                        if normalized != wa_id:
                            contacts[0]["wa_id"] = normalized
                            print(f"[webhook] normalized {wa_id} → {normalized}")

                meta = value.get("metadata", {})
                if meta:
                    meta["display_phone_number"] = target_phone

        chatwoot_url = f"{settings.chatwoot_base_url}/webhooks/whatsapp/+{target_phone}"
        print(f"[webhook] phone_number_id={phone_number_id} → inbox phone={target_phone}")
        print(f"[webhook] forwarding to {chatwoot_url}")
        print(f"[webhook] payload: {_json.dumps(payload)[:600]}")

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(chatwoot_url, json=payload)
            print(f"[webhook] chatwoot response: {r.status_code} {r.text[:300]}")

    except Exception as e:
        print(f"[webhook] error: {e}\n{traceback.format_exc()}")

    return {"status": "ok"}
