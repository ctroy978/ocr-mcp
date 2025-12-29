# Track Spec: Evaluation Pipeline

## Overview
Implement the `evaluate_job` tool to enable AI-based grading of student essays. This tool allows the Agent to inject "Just-in-Time" context (rubrics, source material) directly at runtime, rather than pre-configuring assignments in the database.

## Architecture
- **Database:** Update `essays` table to include an `evaluation` column (JSON) and an `evaluation_status` column.
- **Evaluation Tool:** `evaluate_job`
  - **Inputs:** `job_id`, `rubric`, `context_material`, `system_prompt` (optional).
  - **Process:** Iterates through essays in a Job, constructs a prompt combining the Essay, Rubric, and Context, and calls the AI (xAI/Grok or OpenAI/Qwen).
  - **Output:** Updates the database with the AI's grading response (score, comments).

## Technical Details
- **Schema Update:**
  - `essays` table:
    - `evaluation` TEXT (JSON) - Stores the full grading response.
    - `grade` TEXT/REAL (Optional, extracted score).
    - `status` - Add `GRADED` state.
- **AI Integration:** Use `get_openai_client` (configured for xAI or Qwen).
- **Prompt Engineering:** Construct a robust prompt that forces structured output (e.g., JSON) for easy parsing.

## Workflow
1.  **Agent:** "Grade Job 123 using this rubric: [Rubric Text] and this poem: [Poem Text]."
2.  **Tool:** Queries DB for Job 123.
3.  **Tool:** For each essay:
    - Fetches `scrubbed_text` (or `normalized_text` if avail).
    - Sends to AI with Rubric + Context.
    - Saves result to `evaluation` column.
4.  **Tool:** Returns summary to Agent.
