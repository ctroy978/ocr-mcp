#!/usr/bin/env python3
"""
Quick test script to verify email workflow without running full grading pipeline.
Tests the get_job() method and email sending with an existing job_id.
"""

import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
print(f"[INIT] Loaded environment from: {env_path}")

# Add edmcp to path
sys.path.insert(0, str(Path(__file__).parent))

from edmcp.core.db import DatabaseManager
from edmcp.core.report_generator import ReportGenerator
from edmcp.core.student_roster import StudentRoster
from edmcp.core.email_sender import EmailSender
from edmcp.tools.emailer import EmailerTool


async def test_email_workflow(job_id: str):
    """Test the complete email workflow with an existing job_id"""

    print(f"[TEST] Testing email workflow for job_id: {job_id}")
    print("=" * 80)

    # 1. Initialize DatabaseManager
    print("\n[1] Initializing DatabaseManager...")
    db_path = Path(__file__).parent / "edmcp.db"  # Database is in root, not data/
    db = DatabaseManager(db_path)
    print(f"    ✓ Database loaded from: {db_path}")

    # 2. Test get_job()
    print(f"\n[2] Testing get_job('{job_id}')...")
    job_info = db.get_job(job_id)

    if job_info:
        print(f"    ✓ Job found!")
        print(f"      - ID: {job_info.get('id')}")
        print(f"      - Name: {job_info.get('name')}")
        print(f"      - Created: {job_info.get('created_at')}")
        print(f"      - Status: {job_info.get('status')}")
    else:
        print(f"    ✗ Job NOT found in database!")
        print(f"      Check if job_id exists in jobs table")
        return

    # 3. Get essays for this job
    print(f"\n[3] Getting essays for job...")
    essays = db.get_job_essays(job_id)
    print(f"    ✓ Found {len(essays)} essays")

    if essays:
        print(f"    Sample students:")
        for i, essay in enumerate(essays[:3], 1):
            print(f"      {i}. {essay.get('student_name')} (ID: {essay.get('id')}, Grade: {essay.get('grade')})")
        if len(essays) > 3:
            print(f"      ... and {len(essays) - 3} more")

    # 4. Initialize email components
    print(f"\n[4] Initializing email components...")

    # Check if SMTP is configured (look for environment variables)
    import os
    smtp_configured = all([
        os.getenv("SMTP_HOST"),
        os.getenv("SMTP_PORT"),
        os.getenv("SMTP_USER"),
        os.getenv("SMTP_PASS"),
        os.getenv("FROM_EMAIL")
    ])

    if not smtp_configured:
        print(f"    ⚠ SMTP credentials NOT configured in environment!")
        print(f"      Missing: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, FROM_EMAIL")
        print(f"      Will attempt to initialize with dummy values (emails will fail)")

        # Use dummy values for testing the flow
        email_sender = EmailSender(
            smtp_host=os.getenv("SMTP_HOST", "smtp.example.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER", "user@example.com"),
            smtp_pass=os.getenv("SMTP_PASS", "password"),
            from_email=os.getenv("FROM_EMAIL", "noreply@example.com"),
            from_name="Grade Reports (TEST MODE)"
        )
    else:
        print(f"    ✓ SMTP credentials found in environment")
        email_sender = EmailSender(
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT")),
            smtp_user=os.getenv("SMTP_USER"),
            smtp_pass=os.getenv("SMTP_PASS"),
            from_email=os.getenv("FROM_EMAIL"),
            from_name=os.getenv("FROM_NAME", "Grade Reports")
        )

    # Initialize other components
    names_dir = Path(__file__).parent / "edmcp" / "data" / "names"  # Package data, not root data
    student_roster = StudentRoster(names_dir)

    print(f"    ✓ Student roster loaded from: {names_dir}")
    roster_students = student_roster.get_all_students()
    print(f"    ✓ Found {len(roster_students)} students in roster")

    reports_dir = Path(__file__).parent / "edmcp" / "data" / "reports"  # Package data
    report_generator = ReportGenerator(output_base_dir=str(reports_dir), db_manager=db)
    print(f"    ✓ ReportGenerator initialized")

    # 5. Initialize EmailerTool
    print(f"\n[5] Initializing EmailerTool...")
    emailer = EmailerTool(db, report_generator, student_roster, email_sender)
    print(f"    ✓ EmailerTool ready")

    # 6. Test email sending (REAL SEND)
    print(f"\n[6] Running email workflow - SENDING REAL EMAILS...")
    print(f"    🚀 This will actually send emails via SMTP!")

    try:
        result = await emailer.send_feedback_emails(
            job_id=job_id,
            dry_run=False  # Actually send!
        )

        print(f"\n[RESULT] Email workflow completed!")
        print(f"  Status: {result.get('status')}")
        print(f"  Total students: {result.get('total_students')}")
        print(f"  Emails sent: {result.get('emails_sent')} ✅ REAL EMAILS SENT!")
        print(f"  Emails failed: {result.get('emails_failed')}")
        print(f"  Emails skipped: {result.get('emails_skipped')}")

        # Show details
        details = result.get('details', {})

        if details.get('sent'):
            print(f"\n  ✓ Would send to:")
            for item in details['sent']:
                print(f"    - {item['student']} ({item['email']})")

        if details.get('skipped'):
            print(f"\n  ⚠ Skipped:")
            for item in details['skipped']:
                print(f"    - {item['student']}: {item['reason']}")

        if details.get('failed'):
            print(f"\n  ✗ Failed:")
            for item in details['failed']:
                print(f"    - {item['student']}: {item.get('error', 'Unknown error')}")

        print(f"\n[7] Check your email!")
        print(f"    📧 Check ctroy978@gmail.com for the feedback emails")
        print(f"    📊 Check the log file: {result.get('log_file')}")

    except Exception as e:
        print(f"\n[ERROR] Email workflow failed!")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Use the job_id from the previous test
    job_id = "job_20260103_182412_99612336"

    # Allow override from command line
    if len(sys.argv) > 1:
        job_id = sys.argv[1]

    asyncio.run(test_email_workflow(job_id))
