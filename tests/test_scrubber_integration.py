import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Add project root to sys.path to allow importing server
sys.path.append(str(Path(__file__).parent.parent))

import server
from edmcp.tools.scrubber import Scrubber

class TestScrubberIntegration(unittest.TestCase):
    def setUp(self):
        # Create a controlled Scrubber instance
        self.test_names = {"john", "doe", "smith"}
        self.test_scrubber = Scrubber(self.test_names)
        
        # Patch the global SCRUBBER in server module
        self.scrubber_patcher = patch('server.SCRUBBER', self.test_scrubber)
        self.mock_scrubber = self.scrubber_patcher.start()

    def tearDown(self):
        self.scrubber_patcher.stop()

    @patch('server.convert_from_path')
    @patch('server.ocr_image_with_qwen')
    @patch('server.get_openai_client')
    @patch('os.path.exists')
    def test_process_pdf_core_scrubbing(self, mock_exists, mock_get_client, mock_ocr, mock_convert):
        # Setup mocks
        mock_exists.return_value = True
        mock_get_client.return_value = MagicMock()
        
        # Mock PDF pages
        mock_image = MagicMock()
        mock_image.convert.return_value.save.return_value = None # simulate save
        mock_convert.return_value = [mock_image]
        
        # Mock OCR result with PII
        # "Name: John Doe" matches the NAME_HEADER_PATTERN regex in server.py
        # Pattern is: r"(?im)^\s*(?:name|id)\s*[:\-]\s*([\p{L}][\p{L}'-]*(?:\s+[\p{L}][\p{L}'-]*)?)"
        ocr_text = "Name: John Doe\nThis is an essay by John Smith.\nHe lives in New York."
        mock_ocr.return_value = ocr_text
        
        # Call the function under test
        # We need a dummy path
        result = server._process_pdf_core("dummy.pdf")
        
        # Verify results
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['results']), 1)
        
        record = result['results'][0]
        
        # 1. Verify Name Detection (should still work on original text)
        # The detected name should be extracted from "Name: John Doe"
        self.assertEqual(record['student_name'], 'John Doe')
        
        # 2. Verify Text Scrubbing
        # "John" and "Doe" and "Smith" should be replaced with [STUDENT_NAME]
        expected_scrubbed_text = "Name: [STUDENT_NAME] [STUDENT_NAME]\nThis is an essay by [STUDENT_NAME] [STUDENT_NAME].\nHe lives in New York."
        self.assertEqual(record['text'], expected_scrubbed_text)
        
        # Verify SCRUBBER was actually used
        # Since we patched server.SCRUBBER with our instance, we can't check 'called' on it directly if it's not a Mock object 
        # (it's a real Scrubber instance). But the result confirms it worked.

if __name__ == '__main__':
    unittest.main()
