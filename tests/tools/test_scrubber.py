import pytest
import json
from pathlib import Path
from edmcp.tools.scrubber import Scrubber, ScrubberTool
from edmcp.core.jsonl_utils import write_jsonl

def test_scrub_text_basic():
    names = {"john", "doe"}
    scrubber = Scrubber(names)
    text = "Name: John Doe\nThis is an essay by John."
    expected = "Name: [STUDENT_NAME] [STUDENT_NAME]\nThis is an essay by [STUDENT_NAME]."
    assert scrubber.scrub_text(text) == expected

def test_scrub_text_case_insensitive():
    names = {"john"}
    scrubber = Scrubber(names)
    text = "john wrote JOHN while John watched."
    expected = "[STUDENT_NAME] wrote [STUDENT_NAME] while [STUDENT_NAME] watched."
    assert scrubber.scrub_text(text) == expected

def test_scrub_text_20_line_limit():
    names = {"john"}
    scrubber = Scrubber(names)
    # Create 25 lines
    lines = [f"Line {i}: john" for i in range(1, 26)]
    text = "\n".join(lines)
    
    result = scrubber.scrub_text(text)
    result_lines = result.splitlines()
    
    # First 20 should be scrubbed
    assert "[STUDENT_NAME]" in result_lines[0]
    assert "[STUDENT_NAME]" in result_lines[19]
    # Line 21 onwards should NOT be scrubbed
    assert "john" in result_lines[20]
    assert "john" in result_lines[24]

def test_scrub_text_atomic_matching():
    names = {"john", "doe"}
    scrubber = Scrubber(names)
    text = "John is here. Doe is there. John Doe is everywhere."
    expected = "[STUDENT_NAME] is here. [STUDENT_NAME] is there. [STUDENT_NAME] [STUDENT_NAME] is everywhere."
    assert scrubber.scrub_text(text) == expected

def test_scrub_text_avoids_partial_matches():
    names = {"john"}
    scrubber = Scrubber(names)
    # "johnson" contains "john" but shouldn't be scrubbed if we use word boundaries
    text = "John and Johnson went to the park."
    expected = "[STUDENT_NAME] and Johnson went to the park."
    assert scrubber.scrub_text(text) == expected

@pytest.fixture
def temp_job_dir(tmp_path):
    job_dir = tmp_path / "job_456"
    job_dir.mkdir()
    return job_dir

@pytest.fixture
def temp_names_dir(tmp_path):
    names_dir = tmp_path / "names"
    names_dir.mkdir()
    
    # Create school_names.csv
    school_file = names_dir / "school_names.csv"
    with open(school_file, "w") as f:
        f.write("first_name,last_name\nJohn,Doe\nJane,Smith\n")
        
    return names_dir

def test_scrubber_tool_scrub_job(temp_job_dir, temp_names_dir):
    """Test that ScrubberTool correctly scrubs a JSONL file in a job directory."""
    # Create dummy ocr_results.jsonl
    ocr_results = [
        {
            "job_id": "job_456",
            "student_name": "John Doe",
            "text": "Name: John Doe\nI like to code.",
            "metadata": {"source": "test.pdf"}
        },
        {
            "job_id": "job_456",
            "student_name": "Jane Smith",
            "text": "Jane Smith reporting.\nSky is blue.",
            "metadata": {"source": "test.pdf"}
        }
    ]
    input_path = temp_job_dir / "ocr_results.jsonl"
    write_jsonl(input_path, ocr_results)
    
    # Initialize tool
    tool = ScrubberTool(job_dir=temp_job_dir, names_dir=temp_names_dir)
    output_path = tool.scrub_job()
    
    assert output_path.exists()
    assert output_path.name == "scrubbed_results.jsonl"
    
    # Verify content
    with open(output_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        
        record1 = json.loads(lines[0])
        assert "John Doe" not in record1["text"]
        assert "[STUDENT_NAME]" in record1["text"]
        # Student name field should remain (for re-identification in gradebook)
        assert record1["student_name"] == "John Doe"
        
        record2 = json.loads(lines[1])
        assert "Jane Smith" not in record2["text"]
        assert "[STUDENT_NAME]" in record2["text"]
