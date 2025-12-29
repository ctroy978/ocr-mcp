# Track Spec: Reporting & Analytics

## Overview
Implement tools to aggregate and export data from the `edmcp.db`. This track transforms the internal database records (essays, grades, feedback) into structured reports that instructors can use for final grading and feedback distribution.

## Goals
1.  **CSV Gradebook:** Generate a single CSV file reuniting `student_name` with their `overall_score` and individual `criteria` scores.
2.  **Feedback Distribution:** Generate a folder containing individual PDF reports for each student (e.g., `First_Last.pdf`).
3.  **Privacy Re-association:** securely map the anonymous/scrubbed essay evaluations back to the original student identities stored in the database.

## Architecture

### New MCP Tools
- **`generate_gradebook(job_id)`**
  - **Output:** Path to a `.csv` file (e.g., `data/reports/{job_id}/gradebook.csv`).
  - **Columns:** `Student Name`, `Overall Score`, `Criterion 1`, `Criterion 2`, ...

- **`generate_student_feedback(job_id)`**
  - **Output:** Path to a directory (e.g., `data/reports/{job_id}/feedback_pdfs/`).
  - **Process:** 
    1.  Iterate through graded essays.
    2.  Format the JSON feedback (Feedback, Advice, Rewrites) into a clean layout.
    3.  Render as PDF named `{student_name}.pdf`.

## Dependencies
- `reportlab` (for robust PDF generation) or similar.

## User Workflow
1.  **Agent:** "Evaluation complete."
2.  **Tool:** Calls `generate_gradebook(job_id="123")` -> Returns CSV path.
3.  **Tool:** Calls `generate_student_feedback(job_id="123")` -> Returns folder path with 25 PDFs.
4.  **Agent:** "I've created the gradebook and a folder with all student PDF reports."
