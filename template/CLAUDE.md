# WhatsApp-Chatwoot Bridge — Instalación asistida

Este proyecto instala el microservicio **whatsapp-chatwoot-bridge** en Coolify.
El bridge conecta uno o varios números de WhatsApp (Cloud API o Coexistence) con sus
respectivas bandejas de entrada en Chatwoot.

---

## Instrucciones para Claude

### Antes de empezar

Leer el archivo `.env` de este directorio. Contiene todas las credenciales necesarias
para la instalación. Si algún valor crítico está vacío o es un placeholder, preguntar
al usuario antes de continuar.

Variables críticas (sin estas no se puede instalar):
- `META_ACCESS_TOKEN` — no debe ser placeholder
- `CHATWOOT_BASE_URL` — debe ser una URL real
- `CHATWOOT_API_TOKEN` — no debe ser placeholder
- `PHONE_ROUTING` — debe tener al menos una entrada con valores reales
- `BRIDGE_DOMAIN` — subdominio donde quedará el bridge (ej. `wa-bridge.sudominio.com`)

Si `COOLIFY_API_TOKEN` o `COOLIFY_BASE_URL` están vacíos, el MCP de Coolify no
funcionará. Indicar al usuario que los configure en `.mcp.json`.

---

### Flujo de instalación

Cuando el usuario diga que quiere instalar o deployar el bridge, seguir este orden exacto.

#### 1. Crear la aplicación en Coolify (via MCP)

Usar las herramientas de Coolify MCP disponibles para crear una nueva Application:
- **Fuente**: Public Repository (sin GitHub App)
- **URL del repo**: `https://github.com/kevinrivm/whatsapp-chatwoot-bridge`
- **Branch**: `main`
- **Build pack**: Dockerfile (auto-detectado)
- **Puerto**: `8000`
- **Dominio**: el valor de `BRIDGE_DOMAIN` del `.env` (con `https://`)
- **Health check**: type `http`, path `/health`, port `8000`

#### 2. Configurar las variables de entorno en Coolify (via MCP)

Leer el `.env` y enviar las siguientes variables a la aplicación en Coolify:

```
META_VERIFY_TOKEN
META_ACCESS_TOKEN
META_API_VERSION
CHATWOOT_BASE_URL
CHATWOOT_API_TOKEN
CHATWOOT_ACCOUNT_ID
PHONE_ROUTING
CHATWOOT_WEBHOOK_SECRET   ← enviar vacío por ahora
```

NO enviar `BRIDGE_DOMAIN`, `COOLIFY_BASE_URL` ni `COOLIFY_API_TOKEN` — son solo
para este archivo de configuración local, no son variables del bridge.

#### 3. Deploy

Iniciar el deploy via MCP. Esperar hasta que el status sea `running:healthy`.

Verificar:
```
GET https://{BRIDGE_DOMAIN}/health → {"status": "ok"}
GET https://{BRIDGE_DOMAIN}/webhook?hub.mode=subscribe&hub.verify_token={META_VERIFY_TOKEN}&hub.challenge=test → test
```

Si el healthcheck falla: revisar logs en Coolify. El error más común es que
`python:3.11-slim` no incluye `curl` — el Dockerfile ya lo instala, pero si hay
algún problema de build, verificar que el Dockerfile del repo lo tiene.

#### 4. Override en Meta (REQUIERE APROBACIÓN EXPLÍCITA)

Mostrar al usuario el siguiente comando antes de ejecutarlo y esperar confirmación.
Este paso redirige los webhooks del número de WhatsApp al bridge — afecta producción.

```bash
# Ejecutar por cada phone_number_id en PHONE_ROUTING:
curl -X POST "https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/subscribed_apps" \
  -H "Authorization: Bearer {META_ACCESS_TOKEN}" \
  --data-urlencode "override_callback_uri=https://{BRIDGE_DOMAIN}/webhook" \
  --data-urlencode "verify_token={META_VERIFY_TOKEN}"
# → {"success": true}
```

Si hay múltiples entradas en `PHONE_ROUTING`, ejecutar el curl una vez por cada
`phone_number_id` distinto.

#### 5. Webhook de Chatwoot (flujo de salida)

Guiar al usuario para que en Chatwoot:
1. Settings → Integrations → Webhooks → Add new webhook
2. URL: `https://{BRIDGE_DOMAIN}/chatwoot-events`
3. Eventos: solo `message_created`
4. Save → copiar el HMAC Secret que aparece

Luego via MCP actualizar la variable `CHATWOOT_WEBHOOK_SECRET` con ese valor
y hacer redeploy.

#### 6. Verificación end-to-end

Pedir al usuario que:
1. Envíe "hola" desde un celular al número registrado
2. Espere 5 segundos → debe aparecer en Chatwoot
3. Responda desde Chatwoot → debe llegar al celular

Si no aparece en Chatwoot después de 5s, revisar la sección de debugging.

---

### Gotchas críticos (leer antes de debuggear)

**G1 — `display_phone_number` con dígito troncal → drop silencioso**
Meta envía `display_phone_number: "5214623749518"` (con troncal). El inbox de Chatwoot
está registrado como `"524623749518"` (sin troncal). Chatwoot descarta el mensaje
silenciosamente devolviendo HTTP 200. El bridge ya corrige esto sobreescribiendo
`display_phone_number` con el valor de `chatwoot_phone` del routing.

Si el campo `chatwoot_phone` en `PHONE_ROUTING` no coincide EXACTAMENTE con el
número registrado en el inbox de Chatwoot → mensajes reales no llegan, tests manuales sí.

**G2 — BSUID en `wa_id` → contacto no se crea**
En modo Coexistence, `contacts[0].wa_id` puede ser `MX.Ab1Cd2...`. El bridge lo
reemplaza con `messages[0].from`. No requiere acción — ya está implementado.

**G3 — REST API rechaza mensajes entrantes en inboxes WhatsApp**
`POST /api/v1/.../messages` con `message_type: incoming` devuelve 422. Usar el
endpoint webhook nativo: `POST /webhooks/whatsapp/+{phone}`. El bridge ya lo hace.

**G4 — Chatwoot retorna 200 siempre (async)**
Sidekiq procesa el job ~2-5 segundos después del 200. Un 200 no confirma que el
mensaje fue creado. Esperar antes de verificar.

**G5 — `PHONE_ROUTING` como JSON en una línea**
pydantic-settings parsea el env var como string JSON. Debe ser un array JSON válido
en una sola línea sin saltos de línea dentro del valor.

---

### Agregar un número nuevo al bridge existente

Si el bridge ya está deployado y el usuario quiere añadir un número:

1. Pedir los nuevos valores: `phone_number_id`, `chatwoot_phone` (del inbox nuevo), `inbox_id`
2. Via MCP, actualizar `PHONE_ROUTING` en las env vars de la aplicación en Coolify
   añadiendo el nuevo objeto al array
3. Redeploy
4. Aplicar override de Meta para el nuevo `phone_number_id` (Paso 4 de instalación)

El webhook de Chatwoot ya está configurado — no hace falta tocarlo.

---

### Debugging

**Mensaje llega al bridge pero no aparece en Chatwoot:**
Revisar logs del bridge. Si aparece `chatwoot response: 200` → casi siempre G1.
Comparar `chatwoot_phone` del routing con el número del inbox dígito a dígito.

**`no route for phone_number_id` en logs:**
El `phone_number_id` del payload no está en `PHONE_ROUTING`. Verificar que el valor
en el routing coincide con el `phone_number_id` de Meta Developers.

**Respuestas de agentes no llegan:**
Buscar `[chatwoot-events]` en logs. Si no aparece → el webhook de Chatwoot no está
creado o el HMAC secret no coincide. Re-copiar el secret y redeploy.
