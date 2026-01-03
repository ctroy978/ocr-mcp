# Database Storage Implementation for Reports

## Summary

Student feedback PDFs are now stored in the SQLite database for persistence, solving the email sending issue where files were disappearing after being downloaded by the AI agent.

## Changes Made

### 1. Database Schema (`edmcp/core/db.py`)

**Added `reports` table:**
```sql
CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    report_type TEXT NOT NULL,  -- 'student_pdf', 'gradebook_csv', etc.
    essay_id INTEGER,            -- NULL for job-level reports
    filename TEXT,
    content BLOB,                -- Binary content of the file
    created_at TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs (id),
    FOREIGN KEY (essay_id) REFERENCES essays (id)
)
```

**Added new methods:**
- `store_report()` - Store a report (PDF/CSV) in the database
- `get_student_pdf()` - Retrieve PDF for a specific essay
- `get_report()` - Generic report retrieval
- `delete_job_reports()` - Delete all reports for a job
- Updated `delete_job()` - Now cascades to delete reports

### 2. Report Generator (`edmcp/core/report_generator.py`)

**Dual storage approach:**
- PDFs are **stored in database** (permanent, for email sending)
- PDFs are **written to filesystem** (temporary, for AI agent/teacher download)

**Changes:**
- Constructor accepts `db_manager` parameter
- `generate_student_feedback_pdfs()` now:
  1. Creates PDF on filesystem (as before)
  2. Reads PDF and stores in database (new)
  3. Returns filesystem path for AI agent download

### 3. Email Tool (`edmcp/tools/emailer.py`)

**Database-first PDF retrieval:**
- `_get_student_pdf_path()` now:
  1. Tries to get PDF from database first
  2. If found, writes to temp file
  3. Falls back to filesystem (backwards compatibility)
  4. Returns path (either temp or filesystem)

**Automatic cleanup:**
- Temp files are detected and cleaned up after email is sent
- Uses try-finally block to ensure cleanup even on errors

### 4. Server Configuration (`server.py`)

**Updated initialization:**
```python
REPORT_GENERATOR = ReportGenerator("data/reports", db_manager=DB_MANAGER)
```

## Architecture

### Workflow for Report Generation

```
generate_student_feedback(job_id)
  └─> For each essay:
      ├─> Create PDF on filesystem (data/reports/{job_id}/feedback_pdfs/)
      └─> Store PDF in database (reports table)
```

### Workflow for Email Sending

```
send_student_feedback_emails(job_id)
  └─> For each essay:
      ├─> Get PDF from database
      ├─> Write to temp file
      ├─> Send email with temp file as attachment
      └─> Delete temp file (cleanup)
```

## Benefits

1. **Persistence** - PDFs never disappear after AI agent downloads them
2. **Single source of truth** - Database is authoritative
3. **Backwards compatible** - Still writes to filesystem for existing workflows
4. **Automatic cleanup** - Temp files are cleaned up after emailing
5. **Job lifecycle** - Reports deleted when job is deleted
6. **No file path issues** - No dependency on filesystem paths during email sending

## Testing

The implementation has been tested:
- ✓ Reports table creation
- ✓ Database schema validation
- ✓ Python syntax validation
- ✓ Import checks

## Next Steps for Testing

To verify the complete pipeline works end-to-end:

1. **Process essays:**
   ```
   batch_process_documents(directory_path, job_name="Test Job")
   ```

2. **Evaluate essays:**
   ```
   evaluate_job(job_id, rubric, context_material)
   ```

3. **Generate reports:**
   ```
   generate_student_feedback(job_id)
   ```
   - Should see PDFs in filesystem: `data/reports/{job_id}/feedback_pdfs/`
   - Should see PDFs in database: `SELECT COUNT(*) FROM reports WHERE job_id = ?`

4. **Check database:**
   ```sql
   SELECT job_id, report_type, essay_id, filename, created_at
   FROM reports
   WHERE job_id = 'your_job_id';
   ```

5. **Send emails:**
   ```
   send_student_feedback_emails(job_id, dry_run=True)
   ```
   - Should retrieve PDFs from database
   - Should create temp files
   - Should clean up temp files after

6. **Verify cleanup:**
   - Check temp directory for leftover files (should be none)

## Notes

- **Gradebook CSV** is NOT stored in database (can be regenerated from evaluation data)
- **Filesystem copies** of PDFs can be deleted manually if needed - emails will still work
- **Backwards compatibility** maintained - falls back to filesystem if PDF not in database
- **Migration** is automatic - next server start will create the reports table
