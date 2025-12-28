import sys
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root
sys.path.append(str(Path(__file__).parent))

import server
from edmcp.core.db import DatabaseManager
from edmcp.core.job_manager import JobManager

def verify():
    print("Verifying Normalization Tool Pipeline...")
    
    # 1. Simulate Job Creation
    job_id = server.JOB_MANAGER.create_job()
    print(f"Created Job: {job_id}")
    
    # 2. Add essay with "Bad OCR"
    bad_text = "Tne qulck br0wn f0x."
    server.DB_MANAGER.add_essay(job_id, "Student X", "Raw ignored", {"pages": 1})
    
    # We need to manually set scrubbed_text because normalizer prefers it
    # Fetch the ID
    essays = server.DB_MANAGER.get_job_essays(job_id)
    essay_id = essays[0]['id']
    server.DB_MANAGER.update_essay_scrubbed(essay_id, bad_text)
    
    print(f"Added essay with text: {bad_text}")
    
    # 3. Mock the AI Client to avoid needing real keys/credits for this verify script
    # We want to verify the TOOL logic (DB read -> AI Call -> DB Write)
    with patch('server.get_openai_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "The quick brown fox."
        mock_client.chat.completions.create.return_value = mock_response
        
        # 4. Run Normalization Tool
        # We call the core function directly to avoid tool wrapper issues in script
        print("Running Normalization Tool...")
        result = server._normalize_processed_job_core(job_id)
        print(f"Result: {result}")

    # 5. Verify NORMALIZED status and content
    essays = server.DB_MANAGER.get_job_essays(job_id)
    essay = essays[0]
    
    if essay['status'] != 'NORMALIZED':
        print(f"FAILURE: Status is {essay['status']}, expected NORMALIZED")
        sys.exit(1)
        
    if essay['normalized_text'] != "The quick brown fox.":
         print(f"FAILURE: Normalization didn't match. Text: {essay['normalized_text']}")
         sys.exit(1)
         
    print("SUCCESS: Normalization Tool Verified (with mocked AI).")
    sys.exit(0)

if __name__ == "__main__":
    verify()
