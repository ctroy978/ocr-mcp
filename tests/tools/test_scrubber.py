import pytest
from edmcp.tools.scrubber import Scrubber

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
