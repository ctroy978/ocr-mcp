# Track Plan: Archive & Discovery

## Phase 1: Database Schema [checkpoint: 1.0]
- [x] Task: Update `DatabaseManager._migrate_schema` to add `name` column to `jobs` table.
- [x] Task: Update `DatabaseManager.create_job` to accept optional `job_name`.
- [x] Task: Update `batch_process_documents` in `server.py` to accept and pass `job_name`.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Database Schema' (Protocol in workflow.md)

## Phase 2: Discovery Tool (`search_past_jobs`) [checkpoint: 2.0]
- [x] Task: Create `edmcp/tools/archive.py`.
- [x] Task: Implement `search_jobs` method in `DatabaseManager` (SQL query logic).
- [x] Task: Implement `search_past_jobs` tool in `archive.py`.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Discovery Tool' (Protocol in workflow.md)

## Phase 3: Export Tool (`export_job_archive`) [checkpoint: 3.0]
- [x] Task: Implement `export_job_archive` tool in `archive.py`.
    - Reuse `ReportGenerator` for PDFs/CSV.
    - Copy JSONL from `data/jobs/{id}`.
    - Generate `manifest.txt`.
    - Zip everything.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Export Tool' (Protocol in workflow.md)

## Phase 4: Integration [checkpoint: 4.0]
- [x] Task: Register new tools in `server.py`.
- [x] Task: Verify end-to-end (Search -> Export).
- [x] Task: Conductor - User Manual Verification 'Phase 4: Integration' (Protocol in workflow.md)
