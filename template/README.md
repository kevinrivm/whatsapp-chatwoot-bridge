# Starter — WhatsApp-Chatwoot Bridge

Carpeta de inicio para instalar el bridge con ayuda de Claude.

## Requisitos previos

- [Claude Code](https://claude.ai/code) instalado
- Coolify corriendo en tu VPS con un subdominio apuntando a él
- Chatwoot deployado con al menos un inbox WhatsApp configurado
- System User Token permanente de Meta Business Manager

## 3 pasos para instalar

### 1. Copiar y rellenar el .env

```bash
cp .env.example .env
```

Abrir `.env` y completar **todos** los valores. Los más importantes:
- `META_ACCESS_TOKEN` — tu System User Token de Meta
- `CHATWOOT_BASE_URL` y `CHATWOOT_API_TOKEN` — de tu Chatwoot
- `PHONE_ROUTING` — los IDs de tus números y bandejas de entrada
- `BRIDGE_DOMAIN` — el subdominio donde quedará el bridge
- `COOLIFY_BASE_URL` y `COOLIFY_API_TOKEN` — de tu Coolify

### 2. Configurar el MCP de Coolify

```bash
cp .mcp.json.example .mcp.json
```

Abrir `.mcp.json` y reemplazar:
- `https://coolify.tudominio.com/` → URL real de tu Coolify (con slash final)
- `TU_API_TOKEN_DE_COOLIFY` → tu API Token de Coolify

**Dónde encontrar el API Token de Coolify:**
Coolify → icono de perfil (arriba derecha) → Keys & Tokens → API tokens → + Create

### 3. Abrir Claude Code y pedir la instalación

```bash
claude
```

Escribir en Claude:

> Instala el whatsapp-chatwoot-bridge en mi Coolify

Claude leerá el `.env`, usará el MCP de Coolify para crear la aplicación,
configurar las variables, hacer el deploy, y guiarte paso a paso hasta
verificar el end-to-end.

---

## Notas

- El `.env` contiene credenciales — añadirlo a `.gitignore` si usas git en esta carpeta
- El `.mcp.json` también contiene tu API token de Coolify — tratarlo igual
- El bridge se deploya desde el repo público `github.com/kevinrivm/whatsapp-chatwoot-bridge`
  — no necesitas clonar ni modificar ese repo
