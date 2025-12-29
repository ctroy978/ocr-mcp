# Track Spec: Archive & Discovery

## Overview
Teachers need to retrieve past grading jobs for grade disputes or legal proceedings. Since legacy jobs lack descriptive titles, users need a way to **discover** jobs based on metadata (date, student names, content) and **archive** them into a comprehensive, portable format.

## Requirements

### 1. Database Schema Update
- **Goal:** Allow future jobs to be named for easier retrieval.
- **Change:** Add `name` (TEXT, nullable) column to the `jobs` table.
- **Update:** `batch_process_documents` should accept an optional `job_name` argument.

### 2. Job Discovery Tool (`search_past_jobs`)
- **Input:**
    - `query` (str): Search term (student name or content keyword).
    - `start_date` (str, YYYY-MM-DD): Optional.
    - `end_date` (str, YYYY-MM-DD): Optional.
- **Logic:**
    - Search `essays` table for `student_name` OR `raw_text` matching query.
    - Filter `jobs` table by date range.
    - Join results to return unique Jobs.
- **Output:** A list of "Job Summaries":
    - Job ID
    - Date
    - Name (if available)
    - Student Count
    - Sample Student Names (first 3)
    - Snippet of matching text (if content match)

### 3. Job Export Tool (`export_job_archive`)
- **Input:** `job_id`
- **Output:** Path to a ZIP file.
- **Content of Zip:**
    - `evidence/`: Raw OCR JSONL and/or Text files.
    - `reports/`: CSV Gradebook.
    - `feedback/`: Individual Student PDFs.
    - `manifest.txt`:
        - Job ID / Date
        - Metadata (Students count, etc.)
        - Chain of Custody (Date scrubbed, Date graded)

## Technical Implementation
- **Module:** `edmcp/tools/archive.py`
- **Integration:** Register in `server.py`.
