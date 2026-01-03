import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from edmcp.tools.ocr import OCRTool

@pytest.fixture
def mock_openai():
    with patch("edmcp.tools.ocr.OpenAI") as mock:
        client = MagicMock()
        mock.return_value = client
        # Mock OCR response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Extracted OCR Text"))]
        client.chat.completions.create.return_value = mock_response
        yield mock

@pytest.fixture
def mock_pdf2image():
    with patch("edmcp.tools.ocr.convert_from_path") as mock:
        # Mock two pages
        page1 = MagicMock()
        page2 = MagicMock()
        mock.return_value = [page1, page2]
        yield mock

@pytest.fixture
def temp_job_dir(tmp_path):
    job_dir = tmp_path / "job_123"
    job_dir.mkdir()
    return job_dir

def test_ocr_tool_process_pdf(mock_openai, mock_pdf2image, temp_job_dir):
    """Test that the OCR tool processes a PDF and writes JSONL."""
    pdf_path = Path("test.pdf")

    tool = OCRTool(job_dir=temp_job_dir)
    result = tool.process_pdf(pdf_path)

    # Check return structure
    assert isinstance(result, dict)
    assert "output_path" in result
    assert "used_ocr" in result
    assert "student_count" in result

    result_path = result["output_path"]
    assert result_path.exists()
    assert result_path.name == "ocr_results.jsonl"
    assert result["used_ocr"] is True  # Mock uses OCR (no PDF extraction)
    assert result["student_count"] == 1

    # Read the JSONL and verify content
    with open(result_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1 # 1 aggregate result (for now, keeping existing aggregation logic)

        data = json.loads(lines[0])
        assert data["student_name"] == "Unknown Student 01"
        assert "Extracted OCR Text" in data["text"]
        assert data["metadata"]["page_count"] == 2

def test_ocr_tool_aggregation(mock_openai, mock_pdf2image, temp_job_dir):
    """Test name detection and aggregation logic."""
    # Custom mock to return different text for each page
    client = mock_openai.return_value

    # Page 1 has a name, Page 2 is a continuation
    resp1 = MagicMock()
    resp1.choices = [MagicMock(message=MagicMock(content="Name: John Doe\nEssay content..."))]

    resp2 = MagicMock()
    resp2.choices = [MagicMock(message=MagicMock(content="Continue: John Doe\nMore essay content..."))]

    client.chat.completions.create.side_effect = [resp1, resp2]

    tool = OCRTool(job_dir=temp_job_dir)
    result = tool.process_pdf(Path("test.pdf"))

    result_path = result["output_path"]
    assert result["student_count"] == 1

    with open(result_path, "r") as f:
        data = json.loads(f.readline())
        assert data["student_name"] == "John Doe"
        assert "Essay content..." in data["text"]
        assert "More essay content..." in data["text"]

def test_ocr_tool_initialization_no_env_raises():
    """Test that it raises error if API key is missing."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="environment variable is required"):
            OCRTool(job_dir=Path("/tmp"))
