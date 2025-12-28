import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add project root
sys.path.append(str(Path(__file__).parent.parent))

# Import server (where we will add the cleanup tool)
try:
    import server
except ImportError:
    server = None

class TestCleanupTool(unittest.TestCase):
    
    def setUp(self):
        if server is None:
            self.skipTest("Server module not found")

    @patch('server.DB_MANAGER')
    @patch('server.get_openai_client')
    def test_normalize_processed_job(self, mock_get_client, mock_db):
        # Setup DB return values
        mock_db.get_job_essays.return_value = [
            {"id": 1, "scrubbed_text": "Tne quiclc brown fox.", "status": "SCRUBBED"},
            {"id": 2, "scrubbed_text": "Another esssy.", "status": "SCRUBBED"}
        ]
        
        # Setup Mock AI Client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock AI responses
        mock_response1 = MagicMock()
        mock_response1.choices[0].message.content = "The quick brown fox."
        
        mock_response2 = MagicMock()
        mock_response2.choices[0].message.content = "Another essay."
        
        mock_client.chat.completions.create.side_effect = [mock_response1, mock_response2]
        
        # Check if function exists
        if not hasattr(server, '_normalize_processed_job_core'):
             self.fail("_normalize_processed_job_core not implemented in server")

        # Call the tool
        result = server._normalize_processed_job_core("job_123")
        
        # Verify
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['normalized_count'], 2)
        
        # Check DB updates
        mock_db.update_essay_normalized.assert_any_call(1, "The quick brown fox.")
        mock_db.update_essay_normalized.assert_any_call(2, "Another essay.")
        
        # Verify AI prompt contains the text
        args, kwargs = mock_client.chat.completions.create.call_args_list[0]
        messages = kwargs['messages']
        self.assertIn("Tne quiclc brown fox.", messages[1]['content'])

if __name__ == '__main__':
    unittest.main()
