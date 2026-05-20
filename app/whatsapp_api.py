import httpx
from app.config import settings


async def send_text_message(to: str, text: str) -> dict:
    url = f"https://graph.facebook.com/{settings.meta_api_version}/{settings.meta_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.meta_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload, headers=headers)
        return r.json()
