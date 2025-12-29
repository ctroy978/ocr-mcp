import sys
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root
sys.path.append(str(Path(__file__).parent))

import server

def verify_end_to_end():
    print("Verifying End-to-End Pipeline (OCR -> Scrub -> Evaluate)...")
    
    # 1. Setup Mocks for OCR (Mocking dependencies inside the tools)
    with patch('edmcp.tools.ocr.convert_from_path') as mock_convert, \
         patch('edmcp.tools.ocr.OCRTool.ocr_image') as mock_ocr, \
         patch('server.get_openai_client') as mock_get_client, \
         patch('os.path.exists') as mock_exists:
        
        # Mocking filesystem and external services
        mock_exists.return_value = True
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock PDF -> Image -> Text
        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]
        
        # Original OCR Text
        raw_ocr_text = "Name: John Doe\nThe Raven is a poem by Edgar Allan Poe."
        # mock_ocr is now mocking the method on the class instance, so we configure return value directly
        mock_ocr.return_value = raw_ocr_text
        
        # Mock AI Response for Evaluation (server.py uses standard client for this)
        eval_data = {
            "criteria": [
                {
                    "name": "Accuracy",
                    "score": "95/100",
                    "feedback": {
                        "examples": ["Correct details."],
                        "advice": "None.",
                        "rewritten_example": "N/A"
                    }
                }
            ],
            "overall_score": "95/100",
            "summary": "Great job."
        }
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(eval_data)
        mock_client.chat.completions.create.return_value = mock_response

        # --- STEP 1: OCR BATCH ---
        print("\n[STEP 1] Running batch_process_documents...")
        # Create a temp dir for backup jsonl
        backup_dir = "data/test_backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        # We need a dummy directory with a .pdf file
        dummy_in_dir = "data/test_input"
        os.makedirs(dummy_in_dir, exist_ok=True)
        Path(f"{dummy_in_dir}/test.pdf").touch()
        
        # We need to ensure OCRTool finds the dummy file when iterating
        # batch_process_documents glob logic is real, so the file must exist
        # But convert_from_path is mocked, so it won't actually read it.
        
        batch_result = server._batch_process_documents_core(dummy_in_dir)
        print(f"Batch Result: {batch_result}")
        
        if batch_result['status'] != 'success' or batch_result['summary'].startswith("Processed 0"):
             print(f"FAILURE: Batch processing failed or found 0 files. Errors: {batch_result.get('errors')}")
             sys.exit(1)

        job_id = batch_result['job_id']
        
        # Verify Raw Data in DB
        essays = server.DB_MANAGER.get_job_essays(job_id)
        if not essays or essays[0]['student_name'] != "John Doe":
            print(f"FAILURE: OCR Step failed. Data: {essays}")
            sys.exit(1)
        print("OCR Step SUCCESS.")

        # --- STEP 2: SCRUB ---
        print("\n[STEP 2] Running scrub_processed_job...")
        scrub_result = server._scrub_processed_job_core(job_id)
        print(f"Scrub Result: {scrub_result}")
        
        # Verify Scrubbed Data in DB
        essays = server.DB_MANAGER.get_job_essays(job_id)
        if "[STUDENT_NAME]" not in essays[0]['scrubbed_text']:
            print(f"FAILURE: Scrub Step failed. Text: {essays[0]['scrubbed_text']}")
            sys.exit(1)
        print("Scrub Step SUCCESS.")

        # --- STEP 3: EVALUATE ---
        print("\n[STEP 3] Running evaluate_job...")
        eval_result = server._evaluate_job_core(
            job_id=job_id,
            rubric="Check for accuracy.",
            context_material="Poe's works"
        )
        print(f"Eval Result: {eval_result}")
        
        # Verify Final Data in DB
        essays = server.DB_MANAGER.get_job_essays(job_id)
        final_essay = essays[0]
        if final_essay['status'] != 'GRADED' or final_essay['grade'] != "95/100":
            print(f"FAILURE: Evaluation Step failed. Status: {final_essay['status']}, Grade: {final_essay['grade']}")
            sys.exit(1)
        print("Evaluation Step SUCCESS.")

    print("\n========================================")
    print("SUCCESS: Full Pipeline verified end-to-end.")
    print("========================================")
    sys.exit(0)

if __name__ == "__main__":
    verify_end_to_end()
