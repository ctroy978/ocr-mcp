# edmcp Email System Documentation

## Overview

The edmcp email system is designed to be **job-based** and **decoupled** from grading. It can be used for any task that needs to email students, not just grading feedback.

## Critical Requirement: job_id

**The email system requires a `job_id` to function.** This is the central identifier that ties everything together.

### What job_id Does:

1. **Identifies the batch of students** - Links to essays in the database
2. **Locates PDF reports** - Either from database or filesystem
3. **Tracks email history** - Via `email_log.jsonl` in the job's report directory
4. **Prevents duplicates** - Won't re-send to students who already received emails

## Email Tool Interface

```python
@mcp.tool
async def send_student_feedback_emails(
    job_id: str,                          # REQUIRED - The graded job ID
    subject: Optional[str] = None,        # Optional custom subject
    template_name: Optional[str] = None,  # Template name (default: "default_feedback")
    dry_run: bool = False,                # Preview mode
    filter_students: Optional[Any] = None # Send to specific students only
) -> dict
```

### Parameters Explained:

**`job_id`** (REQUIRED)
- Must be a valid job that has been:
  - Processed (`batch_process_documents`)
  - Graded (`evaluate_job`)
  - Had reports generated (`generate_student_feedback`)
- Format: `job_YYYYMMDD_HHMMSS_<hash>` (e.g., `job_20260102_182026_b3955e7d`)
- **This is the handoff point** - If job_id is lost or wrong, emails fail

**`subject`** (Optional)
- Custom email subject line
- Default: `"Your Assignment Feedback - {assignment_name}"`
- The `assignment_name` comes from the job's `name` field in the database

**`template_name`** (Optional)
- Name of the Jinja2 template in `edmcp/data/email_templates/`
- Default: `"default_feedback"` (uses `default_feedback.html.j2` and `default_feedback.txt.j2`)
- Can create custom templates for different use cases

**`dry_run`** (Optional)
- If `True`, validates everything but doesn't send
- Returns what WOULD be sent
- Useful for verification before mass emailing

**`filter_students`** (Optional)
- JSON list of student names: `["John Doe", "Jane Smith"]`
- If provided, only emails these specific students
- Useful for resending to students who had issues

## Complete Workflow

### 1. Grading Pipeline (Creates the job_id)
```
batch_process_documents(directory_path)
  → Returns: { "job_id": "job_20260102_..." }

scrub_processed_job(job_id)
  → Removes PII

evaluate_job(job_id, rubric, context_material)
  → Grades essays, stores in database

generate_student_feedback(job_id)
  → Creates PDFs, stores in database AND filesystem
  → Returns: { "job_id": "...", "zip_path": "..." }
```

### 2. Email Sending (Uses the job_id)
```
# Optional: Check for problems first
identify_email_problems(job_id)
  → Returns list of students with missing emails or PDFs

# Preview before sending
send_student_feedback_emails(job_id, dry_run=True)
  → Shows who would receive emails

# Actually send
send_student_feedback_emails(job_id)
  → Sends emails to all students with valid email addresses
```

## How job_id is Used Internally

When you call `send_student_feedback_emails(job_id)`, here's what happens:

### Step 1: Load Essays from Database
```python
essays = DB_MANAGER.get_job_essays(job_id)
```
- Queries: `SELECT * FROM essays WHERE job_id = ?`
- Gets student names, essay IDs, grades

### Step 2: For Each Essay:

**A. Look up student email**
```python
email = STUDENT_ROSTER.get_email_for_student(student_name)
```
- Looks in: `edmcp/data/names/school_names.csv`
- Format: `id,first_name,last_name,grade,email`

**B. Get PDF from database**
```python
pdf_content = DB_MANAGER.get_student_pdf(essay_id)
```
- Queries: `SELECT content FROM reports WHERE essay_id = ? AND report_type = 'student_pdf'`
- Returns: Binary PDF content

**C. Create temp file**
```python
temp_pdf = tempfile.NamedTemporaryFile(...)
temp_pdf.write(pdf_content)
```

**D. Send email with attachment**
```python
await EMAIL_SENDER.send_email(
    to_email=email,
    subject=subject,
    body_html=html_body,
    body_plain=plain_body,
    attachments=[temp_pdf_path]
)
```

**E. Log the result**
```python
# Writes to: data/reports/{job_id}/email_log.jsonl
{
    "student_name": "John Doe",
    "email": "john@example.com",
    "status": "SENT",
    "timestamp": "2026-01-02T18:30:00"
}
```

**F. Clean up temp file**
```python
temp_pdf.unlink()  # Delete temp file
```

## Dependencies

The email system requires:

1. **Database has graded essays**
   - Table: `essays` with `job_id`, `student_name`, `grade`, `evaluation`

2. **Database has PDF reports**
   - Table: `reports` with `essay_id`, `report_type='student_pdf'`, `content` (BLOB)

3. **Student roster CSV has emails**
   - File: `edmcp/data/names/school_names.csv`
   - Required columns: `first_name`, `last_name`, `email`

4. **SMTP credentials configured**
   - `.env` file with: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, `FROM_EMAIL`

5. **Email templates exist**
   - Files: `edmcp/data/email_templates/{template_name}.html.j2` and `.txt.j2`

## Common Issues

### ❌ "No essays found for job"
**Cause:** Invalid or wrong job_id
**Solution:** Verify job_id from grading pipeline output

### ❌ "PDF not found"
**Cause:** `generate_student_feedback(job_id)` wasn't called, or PDFs weren't stored in database
**Solution:** Always call `generate_student_feedback` before emailing

### ❌ "No email address in roster"
**Cause:** Student name from PDF doesn't match roster, or email column is empty
**Solution:** Use `identify_email_problems(job_id)` to find mismatches

### ❌ "SMTP send failed"
**Cause:** Invalid SMTP credentials or network issue
**Solution:** Test with `dry_run=True` first, check `.env` configuration

## Using Email Service for Other Tasks

The email system is **job-based**, so to use it for non-grading tasks:

### Option 1: Create a "job" for your task
```python
# Create a minimal job
job_id = DB_MANAGER.create_job(job_name="Announcement Email")

# Add "essays" (really just student records)
for student in students:
    DB_MANAGER.add_essay(
        job_id=job_id,
        student_name=student['name'],
        raw_text="",  # Not used for emails
        metadata={}
    )

# Store PDFs in database (if attaching files)
for student, pdf_bytes in student_files:
    DB_MANAGER.store_report(
        job_id=job_id,
        report_type='student_pdf',
        filename=f"{student['name']}_announcement.pdf",
        content=pdf_bytes,
        essay_id=student['essay_id']
    )

# Send emails
send_student_feedback_emails(job_id, subject="Class Announcement")
```

### Option 2: Use EmailSender directly (bypasses job system)
```python
from edmcp.core.email_sender import EmailSender

sender = EmailSender(...)
await sender.send_email(
    to_email="student@example.com",
    subject="Announcement",
    body_html="<p>Hello!</p>",
    body_plain="Hello!",
    attachments=[]
)
```

## Return Value

The tool returns a detailed summary:

```python
{
    "status": "success",  # or "warning" if some failed
    "job_id": "job_20260102_182026_b3955e7d",
    "sent_count": 18,
    "failed_count": 2,
    "skipped_count": 3,
    "sent": [
        {"student": "John Doe", "email": "john@example.com"}
    ],
    "failed": [
        {"student": "Jane Smith", "email": "jane@example.com", "error": "SMTP timeout"}
    ],
    "skipped": [
        {"student": "Bob Johnson", "reason": "Email already sent previously"}
    ],
    "log_file": "/home/tcoop/Work/edmcp/data/reports/job_xxx/email_log.jsonl"
}
```

## Idempotency

The email system is **idempotent** - you can safely re-run it:

- Checks `email_log.jsonl` before sending
- Skips students who already received emails
- Only sends to new students or those who failed previously

This is controlled by the email log:
```
data/reports/{job_id}/email_log.jsonl
```

Each line is a JSON record:
```json
{"student_name": "John Doe", "email": "john@example.com", "status": "SENT", "timestamp": "..."}
{"student_name": "Jane Smith", "email": "jane@example.com", "status": "FAILED", "error": "..."}
```

## Key Takeaway for Handoff

**The job_id is the contract between grading and email.**

1. Grading creates a job_id and stores everything in the database
2. Email tool takes the job_id and looks up everything it needs
3. If job_id is wrong, lost, or not passed correctly, emails fail

**Verify the handoff:**
- After grading: Save job_id
- Before emailing: Pass the same job_id
- The job_id should be in every tool response from the grading pipeline

Example response from `generate_student_feedback`:
```json
{
    "status": "success",
    "job_id": "job_20260102_182026_b3955e7d",  ← This is what you need!
    "zip_path": "/absolute/path/to/file.zip"
}
```
