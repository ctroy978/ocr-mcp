import sys
import sqlite3
from pathlib import Path

# Add project root
sys.path.append(str(Path(__file__).parent))

import server
from edmcp.core.db import DatabaseManager
from edmcp.core.job_manager import JobManager

def verify():
    print("Verifying DB Pipeline...")
    
    # 1. Simulate Job Creation
    job_id = server.JOB_MANAGER.create_job()
    print(f"Created Job: {job_id}")
    
    # 2. Simulate OCR Result (Add to DB)
    # Note: server.DB_MANAGER is initialized in server.py
    server.DB_MANAGER.add_essay(job_id, "John Doe", "My name is John Doe.", {"pages": 1})
    print("Added essay to DB.")
    
    # 3. Verify PENDING status
    essays = server.DB_MANAGER.get_job_essays(job_id)
    if not essays or essays[0]['status'] != 'PENDING':
        print(f"FAILURE: Essay not found or not PENDING. Status: {essays[0]['status'] if essays else 'None'}")
        sys.exit(1)
        
    # 4. Run Scrubber Tool (Core Logic)
    result = server._scrub_processed_job_core(job_id)
    print(f"Scrubber Result: {result}")
    
    # 5. Verify SCRUBBED status and content
    essays = server.DB_MANAGER.get_job_essays(job_id)
    essay = essays[0]
    
    if essay['status'] != 'SCRUBBED':
        print(f"FAILURE: Status is {essay['status']}, expected SCRUBBED")
        sys.exit(1)
        
    if "[STUDENT_NAME]" not in essay['scrubbed_text']:
         print(f"FAILURE: Scrubbing didn't happen. Text: {essay['scrubbed_text']}")
         sys.exit(1)
         
    print("SUCCESS: Pipeline verified.")
    sys.exit(0)

if __name__ == "__main__":
    verify()
