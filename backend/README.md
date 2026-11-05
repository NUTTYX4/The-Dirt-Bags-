# CropScope backend

CropScope is a local FastAPI and PostgreSQL service. Ready Tomato and Chilli ONNX models perform disease classification locally. An optional configured AI provider performs crop and plant-part routing only after the farmer explicitly consents to an external request.

## Start

```powershell
cd backend
docker compose up --build -d
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

The API is at `http://127.0.0.1:8000`; OpenAPI is at `/docs`.

## AI routing configuration

Copy non-secret values from `.env.example` into the ignored `backend/.env`, then set a real `OPENROUTER_API_KEY` locally:

```dotenv
AI_PROVIDER=openrouter
AI_ENABLED=true
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=nvidia/nemotron-3.5-super-vl:free
AI_MAX_REQUESTS_PER_MINUTE=5
AI_MAX_REQUESTS_PER_DAY=40
AI_MAX_OUTPUT_TOKENS=512
AI_ROUTING_MAX_OUTPUT_TOKENS=1536
AI_TIMEOUT_SECONDS=25
```

The key is never returned by the API, placed in the frontend, or committed. PostgreSQL counters cover both visual routing and chat explanations. Repeated successful routing of the same image uses a SHA-256 cache. If the provider is unavailable, quota-limited, malformed, or not configured, the saved conversation stays open and the farmer can choose Tomato or Chilli for local inference.

## Inspection API

`POST /api/v1/inspections` accepts multipart form data:

- `image` — required JPEG, PNG, or WEBP;
- `session_id` — optional existing chat session;
- `crop_hint`, `plant_part_hint` — manual local fallback;
- `gemini_image_routing_consent` — compatibility field name; when `true`, it authorizes the configured external AI-routing request.

For automatic routing, omit `crop_hint`, submit a leaf image, and set consent to `true`. For manual local routing, use `crop_hint=tomato` or `crop_hint=chilli`, `plant_part_hint=leaf`, and set consent to `false`. Only ready leaf models are selected. Direct prediction, model registry, inspections, and persistent chat-session endpoints remain available.

```powershell
curl.exe -F "model_id=chilli_disease_v1" -F "image=@C:\path\leaf.jpg" http://127.0.0.1:8000/api/v1/predictions
```

Disease predictions are preliminary image-based guidance; routing output is never treated as a disease diagnosis or numeric disease confidence.
