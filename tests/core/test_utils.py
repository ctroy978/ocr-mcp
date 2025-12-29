
import pytest
from edmcp.core.utils import extract_json_from_text, retry_with_backoff
from unittest.mock import MagicMock

def test_extract_clean_json():
    text = '{"key": "value"}'
    result = extract_json_from_text(text)
    assert result == {"key": "value"}

def test_extract_json_with_markdown_fences():
    text = "Here is the result:\n```json\n{\"score\": 95, \"comment\": \"Great!\"}\n```\nHope this helps."
    result = extract_json_from_text(text)
    assert result == {"score": 95, "comment": "Great!"}

def test_extract_json_with_generic_fences():
    text = "```\n{\"a\": 1}\n```"
    result = extract_json_from_text(text)
    assert result == {"a": 1}

def test_extract_json_with_surrounding_text():
    text = "The data is { \"id\": 123 } and that is all."
    result = extract_json_from_text(text)
    assert result == {"id": 123}

def test_extract_nested_json():
    text = 'Some text {"outer": {"inner": [1, 2, 3]}} trailing text'
    result = extract_json_from_text(text)
    assert result == {"outer": {"inner": [1, 2, 3]}}

def test_invalid_json():
    text = "This is not json { at all"
    assert extract_json_from_text(text) is None

def test_trailing_comma_fix():
    # Simple trailing comma case
    text = '{"a": 1, "b": 2,}'
    result = extract_json_from_text(text)
    assert result == {"a": 1, "b": 2}

def test_empty_input():
    assert extract_json_from_text("") is None
    assert extract_json_from_text(None) is None

def test_retry_with_backoff_success():
    mock_func = MagicMock()
    mock_func.side_effect = [ValueError("Fail"), ValueError("Fail"), "Success"]
    
    @retry_with_backoff(retries=3, backoff_in_seconds=0.01, exceptions=ValueError)
    def test_func():
        return mock_func()
    
    result = test_func()
    assert result == "Success"
    assert mock_func.call_count == 3

def test_retry_with_backoff_failure():
    mock_func = MagicMock()
    mock_func.side_effect = ValueError("Permanent Fail")
    
    @retry_with_backoff(retries=2, backoff_in_seconds=0.01, exceptions=ValueError)
    def test_func():
        return mock_func()
    
    with pytest.raises(ValueError):
        test_func()
    assert mock_func.call_count == 2
