# Gemini visual-routing status

Checked on 2026-11-05 (local Windows/Docker environment).

- Docker API configuration: `GEMINI_ENABLED=true`; API key present (not logged); model configured as `gemini-3.5-flash`; `google-genai` installed.
- The automatic inspection path passes the uploaded bytes and MIME type through the local host bridge to the official Google Gen AI SDK, requests crop/plant-part JSON only, and validates it with Pydantic before routing a local model.
- The frontend exposes explicit Automatic and Manual modes. Automatic mode requires consent; Manual mode sends `crop_hint` with consent disabled and does not call Gemini.
- Current live automatic test result: `identification_failed` with `gemini_quota_exhausted`. Google returned `429 RESOURCE_EXHAUSTED` for the project free-tier generate-content quota. No local disease model was selected.
- The local Gemini bridge now enforces a persistent five-second request gap and a configurable 15-request daily ceiling across both image-routing and explanation calls. An immediate repeat was verified to return `gemini_rate_limited` with a retry-after value before making another provider request.
- Manual Tomato test: completed with `tomato_disease_plantvillage_v1`, prediction `Early blight`.
- Manual Chilli regression: completed with `chilli_disease_v1`, prediction `Bacterial Spot`.
- Existing API acceptance checks, persistence checks, and frontend production build passed.

When quota is available again, automatic mode can be retested without a code change. The expected successful path is: consented image -> validated Gemini crop/leaf routing -> ready Tomato or Chilli ONNX model -> persisted prediction.
