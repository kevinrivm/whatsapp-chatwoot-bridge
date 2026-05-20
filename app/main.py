from fastapi import FastAPI
from app.webhook import router as webhook_router
from app.chatwoot import router as chatwoot_router

app = FastAPI(title="WhatsApp-Chatwoot Bridge")

app.include_router(webhook_router)
app.include_router(chatwoot_router)


@app.get("/health")
def health():
    return {"status": "ok"}
