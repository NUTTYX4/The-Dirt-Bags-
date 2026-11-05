# AI provider migration

## Implemented

- Active inspection and chat paths use `app.ai_provider.AIProvider` rather than the legacy Gemini bridge.
- OpenRouter is configured only through ignored backend environment variables.
- The configured model is configuration, not a hard-coded business decision. Reasoning-model crop routing has a separately configurable 1,536-token cap so it can emit a final structured answer; general conversation remains at the configured 512-token cap.
- Image requests use an OpenAI-compatible chat-completions data URL and request strictly crop/plant-part routing JSON.
- Pydantic validates allowed crop, plant-part, certainty, quality, and confirmation values before local routing.
- PostgreSQL-backed minute/day counters protect all external AI calls. Successful visual routing is cached by image SHA-256. Provider `429` responses create a persistent Retry-After cooldown; the OpenAI client has automatic retries disabled.
- Tomato and Chilli disease labels and numeric confidence always come from local ONNX inference.

## Operational status

Live OpenRouter Tomato and Chilli image-routing checks passed on 5 November 2026. A missing, invalid, unavailable, malformed, or quota-limited provider still leaves the new chat open and returns the local manual Tomato/Chilli fallback.
