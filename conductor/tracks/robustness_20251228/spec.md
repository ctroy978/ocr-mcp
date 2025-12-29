# Track Spec: Robustness & Error Handling

## Overview
Harden the MCP server tools, particularly `evaluate_job` and AI integrations, against common runtime failures. This ensures the system is resilient to API flakes, malformed LLM outputs, and unexpected data.

## Goals
1.  **Resilient Parsing:** The system must gracefully handle "messy" JSON from LLMs (e.g., Markdown fences, trailing commas).
2.  **Fault Tolerance:** Transient API errors (timeouts, rate limits) should trigger automatic retries.
3.  **Schema Validation:** Ensure AI outputs meet the expected structure before being saved to the database.

## Technical Approach

### 1. JSON Cleaning Utility
- Create `edmcp/core/utils.py`.
- Implement `extract_json_from_text(text: str) -> dict`.
  - Strip ```json ... ``` fences.
  - Handle common syntax errors (if possible/safe).

### 2. Retry Logic
- Use the `tenacity` library (already a dependency of llama-index, but we should add it explicitly if needed).
- Create a reusable `@retry_api_call` decorator for `server.py` or core logic functions.
- specific handling for `openai.RateLimitError` and `openai.APIConnectionError`.

### 3. Schema Validation
- Update `evaluate_job` to validate that the parsed JSON contains `criteria` and `overall_score`.
- If validation fails, retry the generation (or fail gracefully with a descriptive error).

## Impacted Files
- `server.py`
- `edmcp/core/prompts.py` (Maybe refine prompt for stricter JSON)
- `edmcp/core/utils.py` (New)
