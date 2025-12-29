# Track Plan: Reporting & Analytics

## Phase 1: Environment & Logic
- [x] Task: Add `reportlab` to `pyproject.toml` (for PDF generation).
- [x] Task: Create `edmcp/core/report_generator.py`.
- [x] Task: Implement `generate_csv_logic(job_id)`:
    - Query DB for original names and JSON evaluations.
    - flatten JSON criteria into columns.
- [x] Task: Implement `generate_pdf_logic(job_id)`:
    - Layout a professional feedback page (Student Name, Score, Criteria breakdown, Improvements).
- [x] Task: Implement Zipping logic for feedback directory.

## Phase 2: MCP Tool Integration
- [x] Task: Add `generate_gradebook` tool to `server.py`.
- [x] Task: Add `generate_student_feedback` tool to `server.py`.

## Phase 3: Verification
- [x] Task: Create a test script `verify_reporting.py`.
- [x] Task: Mock a graded job in the DB.
- [x] Task: Verify CSV contains correct columns and data.
- [x] Task: Verify PDF folder is created and PDFs are readable/formatted correctly.