# Track Spec: Refactor for Modularity and Implement OCR & Cleanup Tools

## Overview
The goal is to transition from a monolithic FastMCP server to a modular, multi-tool pipeline. Each tool (OCR, Cleanup, etc.) will be a discrete component that handles a single task and hands off data via JSONL files in uniquely identified job directories.

## Architecture
- **Job Directory:** A unique directory (UUID or timestamp-based) for each batch job.
- **JSONL Handoff:** Tools read from an input JSONL and write to an output JSONL.
- **Modular Tools:**
  - **Framework:** Common logic for managing job IDs, directories, and JSONL I/O.
  - **OCR Tool:** Ported from existing logic, uses Qwen-VL to process images/PDFs.
  - **Cleanup Tool:** New tool using xAI to scrub PII (names) and normalize OCR output.

## Technical Details
- **Handoff Format:**
  ```jsonl
  {"job_id": "job_123", "student_id": "std_001", "text": "...", "metadata": {...}}
  ```
- **OCR Tool:** Input: File paths. Output: Extracted text in JSONL.
- **Cleanup Tool:** Input: JSONL from OCR. Output: Normalized text with PII removed.
