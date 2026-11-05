# Inspection API report

`POST /api/v1/inspections` is synchronous and persists an inspection plus its local prediction. It validates JPEG/PNG/WEBP, stores uploads in the Docker upload volume, and routes only ready leaf classifiers from `model_registry.yaml`.

Verified Docker tests: Tomato leaf → Tomato model → Early blight; Chilli leaf → Chilli model → Bacterial Spot; no hint → `needs_crop_confirmation`; fruit hint → `unsupported_plant_part`. Frontend production build passed.

Gemini is disabled locally because no key is configured. Consequently visual routing is unavailable and manual crop selection is required; no photograph was sent externally.
