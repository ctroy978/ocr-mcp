import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add project root
sys.path.append(str(Path(__file__).parent.parent))

try:
    import server
except ImportError:
    server = None

class TestScrubberJob(unittest.TestCase):
    
    def setUp(self):
        if server is None:
            self.skipTest("Server module not found")

    @patch('server.DB_MANAGER')
    @patch('server.SCRUBBER')
    def test_scrub_processed_job(self, mock_scrubber, mock_db):
        # Setup DB return values
        # get_job_essays returns a list of dicts
        mock_db.get_job_essays.return_value = [
            {"id": 1, "raw_text": "My name is John Doe.", "student_name": "John Doe", "status": "PENDING"},
            {"id": 2, "raw_text": "No names here.", "student_name": "Unknown", "status": "PENDING"}
        ]
        
        # Setup Scrubber behavior
        mock_scrubber.scrub_text.side_effect = lambda x: x.replace("John Doe", "[STUDENT_NAME]")
        
        # Check if function exists
        if not hasattr(server, '_scrub_processed_job_core'):
             self.fail("_scrub_processed_job_core not implemented in server")

        # Call the tool
        result = server._scrub_processed_job_core("job_123")
        
        # Verify
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['scrubbed_count'], 2)
        
        # Check DB updates
        mock_db.update_essay_scrubbed.assert_any_call(1, "My name is [STUDENT_NAME].")
        mock_db.update_essay_scrubbed.assert_any_call(2, "No names here.")

if __name__ == '__main__':
    unittest.main()
