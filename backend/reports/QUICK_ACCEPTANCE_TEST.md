# Quick acceptance test

Result: **PASS** (live Docker API and PostgreSQL).

- Health and database readiness: pass.
- Ready models: `chilli_disease_v1`, `tomato_disease_plantvillage_v1`.
- Tomato inspection: completed; Tomato leaf model returned `Early blight` with confidence `0.993959`.
- Chilli inspection: completed; Chilli leaf model returned `Bacterial Spot` with confidence `0.653527`.
- Missing crop: `needs_crop_confirmation`, with no selected model or prediction.
- Fruit request: `unsupported_plant_part`, with no prediction.
- Invalid upload: `invalid_image`, with no prediction.
- Inspection retrieval and list persistence: pass.
- Existing direct prediction endpoint: pass.
- Frontend production build: pass (`npm ci`, then `npm run build`).

Browser automation was not installed; the manual browser acceptance checklist is: upload a leaf, select Tomato or Chilli, press Analyze, confirm the returned class/confidence, then check the unsupported-state message for a fruit image.

Gemini visual routing was not invoked by this test and no test photo was sent to Gemini. Manual crop selection is the tested MVP path.
