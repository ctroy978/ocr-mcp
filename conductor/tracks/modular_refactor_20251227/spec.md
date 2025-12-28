# Track Spec: Refactor for Modularity and Implement OCR & Cleanup Tools

## Overview
The goal is to transition from a monolithic FastMCP server to a modular, multi-tool pipeline. Each tool (OCR, Cleanup, etc.) will be a discrete component that handles a single task. Data handoff and state management will be handled by an embedded SQLite database, replacing file-based JSONL passing.

## Architecture
- **Database:** SQLite (`edmcp.db`) stores job state, student records, and essay text.
- **Job Management:** Tools operate on Job IDs passed by the agent.
- **Modular Tools:**
  - **Framework:** Common logic for database access and job management.
  - **OCR Tool:** Processes PDFs, extracts text/names, and saves raw results to DB.
  - **Scrubber Tool:** Reads raw text from DB, applies regex scrubbing, and updates DB.
  - **Cleanup Tool:** Reads scrubbed text from DB, uses xAI for text normalization (typo fixing), and updates DB.

## Technical Details
- **Schema (Provisional):**
  - `jobs`: id, created_at, status
  - `essays`: id, job_id, student_name (detected), raw_text, scrubbed_text, normalized_text, status
- **OCR Tool:** Input: File paths. Output: DB records.
- **Scrubber Tool:** Input: Job ID. Output: Updates `scrubbed_text` in DB.
- **Cleanup Tool:** Input: Job ID. Output: Updates `normalized_text` in DB.
