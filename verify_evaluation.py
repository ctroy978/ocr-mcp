import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root
sys.path.append(str(Path(__file__).parent))

import server

def verify():
    print("Verifying Evaluation Tool Pipeline...")
    
    # 1. Simulate Job Creation
    job_id = server.JOB_MANAGER.create_job()
    print(f"Created Job: {job_id}")
    
    # 2. Add essay to DB
    essay_text = "The Raven is a poem about loss."
    server.DB_MANAGER.add_essay(job_id, "Student Y", essay_text, {"pages": 1})
    print("Added essay to DB.")
    
    # 3. Mock the AI Client
    with patch('server.get_openai_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        eval_data = {
            "score": "B+",
            "comments": "Good focus on the theme of loss.",
            "summary": "Solid understanding."
        }
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(eval_data)
        mock_client.chat.completions.create.return_value = mock_response
        
        # 4. Run Evaluation Tool
        print("Running Evaluation Tool...")
        result = server._evaluate_job_core(
            job_id=job_id,
            rubric="Check for theme analysis.",
            context_material="The Raven by Poe"
        )
        print(f"Result: {result}")

    # 5. Verify GRADED status and content
    essays = server.DB_MANAGER.get_job_essays(job_id)
    essay = essays[0]
    
    if essay['status'] != 'GRADED':
        print(f"FAILURE: Status is {essay['status']}, expected GRADED")
        sys.exit(1)
        
    if essay['grade'] != "B+":
         print(f"FAILURE: Grade didn't match. Extracted: {essay['grade']}")
         sys.exit(1)
         
    print("SUCCESS: Evaluation Tool Verified (with mocked AI).")
    sys.exit(0)

if __name__ == "__main__":
    verify()
