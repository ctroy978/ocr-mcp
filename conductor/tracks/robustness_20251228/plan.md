# Track Plan: Robustness & Error Handling

## Phase 1: Utilities & Parsing
- [x] Task: Create `edmcp/core/utils.py`.
- [x] Task: Implement `extract_json_from_text` (Regex-based cleaner).
- [x] Task: Add unit tests for JSON extraction (handling fences, plain text, etc.).

## Phase 2: Retry Logic
- [x] Task: Verify `tenacity` is installed/available.
- [x] Task: Implement `@retry_with_backoff` decorator in `edmcp/core/utils.py`.
- [x] Task: Apply decorator to `_evaluate_job_core`, `ocr_image_with_qwen`, and RAG ingestion/query methods.

## Phase 3: Integration & Validation
- [x] Task: Update `server.py` (evaluate_job) to use `extract_json_from_text`.
- [x] Task: Add schema validation check (raise error if `overall_score` missing).
- [x] Task: Verify with a test script simulating malformed JSON.