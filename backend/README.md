# CropScope backend

Start locally:

```powershell
cd backend
docker compose up --build -d
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

Core endpoints: `GET /health/live`, `GET /health/ready`, `GET /api/v1/models`, `POST /api/v1/predictions`, and chat sessions under `/api/v1/chat/sessions`.

Prediction request example:

```powershell
curl.exe -F "model_id=chilli_disease_v1" -F "image=@C:\path\leaf.jpg" http://127.0.0.1:8000/api/v1/predictions
```

Set `GEMINI_ENABLED=true` and `GEMINI_API_KEY` in `.env` to enable live Gemini. The present fallback never sends crop photographs to Gemini.
