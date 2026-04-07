# AI Gateway

Gateway centralizado para todas las llamadas a LLMs. Usa LiteLLM Proxy para proveer cost tracking, rate limiting, fallbacks y virtual keys por proyecto. La API key real de OpenAI vive solo aqui.

## Setup rapido

1. Copiar `.env.example` a `.env` y llenar `OPENAI_API_KEY` y `LITELLM_MASTER_KEY`
2. `docker compose up -d`
3. Verificar: `curl http://localhost:4000/health`

## Endpoints

| Endpoint | Descripcion |
|----------|-------------|
| `http://localhost:4000` | Proxy (entrada para proyectos consumidores) |
| `http://localhost:4000/ui` | Dashboard de metricas y logs |
| `GET http://localhost:4000/health` | Health check |

## Agregar un proyecto consumidor

1. Agregar una nueva virtual key en `config.yaml` bajo `key_management.keys`
2. Reiniciar: `docker compose restart litellm`
3. En el proyecto consumidor, setear en `.env`:
   ```
   OPENAI_API_KEY=sk-nueva-virtual-key
   OPENAI_BASE_URL=http://localhost:4000
   ```

## Rotar virtual keys

1. Cambiar el `key_name` en `config.yaml`
2. `docker compose restart litellm`
3. Actualizar `OPENAI_API_KEY` en el `.env` del proyecto consumidor

## Bypass para desarrollo

Si el Gateway no esta levantado, comentar `OPENAI_BASE_URL` en el `.env` del proyecto. El OpenAI SDK apuntara directo a `api.openai.com`. Solo para desarrollo local.

## Portabilidad

Para usar este Gateway en otro proyecto: copiar `gateway/docker-compose.yml`, `gateway/config.yaml`, y `gateway/.env.example`. Ajustar virtual keys y budgets. Levantar con `docker compose up`.
