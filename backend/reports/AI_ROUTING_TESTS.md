# AI routing tests

## Automated/local checks — 5 November 2026

- Docker image rebuilt successfully with the OpenAI-compatible SDK; API and PostgreSQL are healthy.
- Frontend production build passed after the photo-first chat update.
- A real local Tomato test image completed through a fresh chat session using `tomato_disease_plantvillage_v1`: `Early blight`.
- A real local Chilli test image completed through the same persistence path using `chilli_disease_v1`: `Bacterial Spot`.
- An automatic attempt without a configured key returned `identification_failed` and `ai_not_configured`, with no prediction and an in-chat manual fallback.
- A Tomato fruit request returned `unsupported_plant_part` with a null prediction.
- Chat follow-up, session listing, message persistence, and inspection retrieval passed. With no configured key, the saved local result is returned with an honest unavailable-explanation message.

## Live-provider test gate

## Live-provider checks — 5 November 2026

- Image routing succeeded against the configured provider after allocating the reasoning model a dedicated 1,536-token routing budget.
- An original PlantVillage Tomato leaf was identified as `tomato` / `leaf` with medium routing certainty; the ready local Tomato ONNX model produced `Early blight` at 1.0 confidence.
- An original CH-001 Chilli leaf was identified as `chilli` / `leaf` with medium routing certainty; the ready local Chilli ONNX model produced `Bacterial Spot` at 0.997841477394104 confidence.
- Both inspection chats persisted the upload, local prediction card, and provider explanation (three messages each).
- Earlier low-token tests correctly fell back without guessing; they established that the selected reasoning model needs more than 512 tokens to emit its structured final response.
- A no-consent image request returned `needs_crop_confirmation`, no prediction, a `select_crop` next action, and did not record an external-routing request.

Remaining targeted tests:

1. provider `429` cooldown behavior using a safe mocked response rather than consuming the live quota.
