import unittest
from unittest.mock import MagicMock, patch
import sys
import json
from pathlib import Path

# Add project root
sys.path.append(str(Path(__file__).parent.parent))

try:
    import server
except ImportError:
    server = None

class TestEvaluationTool(unittest.TestCase):
    
    def setUp(self):
        if server is None:
            self.skipTest("Server module not found")

    @patch('server.DB_MANAGER')
    @patch('server.get_openai_client')
    def test_evaluate_processed_job(self, mock_get_client, mock_db):
        # Setup DB return values
        mock_db.get_job_essays.return_value = [
            {"id": 1, "scrubbed_text": "Essay one content.", "status": "SCRUBBED"},
            {"id": 2, "normalized_text": "Essay two content.", "status": "NORMALIZED"}
        ]
        
        # Setup Mock AI Client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock AI JSON response
        eval_data = {
            "score": "A",
            "comments": "Excellent analysis.",
            "summary": "High quality."
        }
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(eval_data)
        mock_client.chat.completions.create.return_value = mock_response
        
        # Check if function exists
        if not hasattr(server, '_evaluate_job_core'):
             self.fail("_evaluate_job_core not implemented in server")

        # Call the tool
        result = server._evaluate_job_core(
            job_id="job_123",
            rubric="Use points 1-10",
            context_material="Poem analysis"
        )
        
        # Verify
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['evaluated_count'], 2)
        
        # Check DB updates
        # Ensure it passed the JSON string and the extracted score
        mock_db.update_essay_evaluation.assert_any_call(1, json.dumps(eval_data), "A")
        mock_db.update_essay_evaluation.assert_any_call(2, json.dumps(eval_data), "A")
        
        # Verify AI prompt contains the rubric and context
        args, kwargs = mock_client.chat.completions.create.call_args_list[0]
        messages = kwargs['messages']
        full_content = messages[1]['content']
        self.assertIn("Use points 1-10", full_content)
        self.assertIn("Poem analysis", full_content)

if __name__ == '__main__':
    unittest.main()
