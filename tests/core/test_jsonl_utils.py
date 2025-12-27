import json
from pathlib import Path
import pytest
from edmcp.core.jsonl_utils import read_jsonl, write_jsonl

@pytest.fixture
def temp_file(tmp_path):
    return tmp_path / "test.jsonl"

def test_write_and_read_jsonl(temp_file):
    """Test writing and reading JSONL data."""
    data = [
        {"id": 1, "text": "hello"},
        {"id": 2, "text": "world"}
    ]
    
    write_jsonl(temp_file, data)
    
    assert temp_file.exists()
    
    read_data = list(read_jsonl(temp_file))
    assert read_data == data

def test_append_jsonl(temp_file):
    """Test appending to an existing JSONL file."""
    initial_data = [{"id": 1}]
    write_jsonl(temp_file, initial_data)
    
    new_data = [{"id": 2}]
    write_jsonl(temp_file, new_data, append=True)
    
    read_data = list(read_jsonl(temp_file))
    assert read_data == [{"id": 1}, {"id": 2}]

def test_read_empty_jsonl(temp_file):
    """Test reading an empty file."""
    temp_file.touch()
    assert list(read_jsonl(temp_file)) == []

def test_write_non_serializable_raises(temp_file):
    """Test that writing non-serializable data raises TypeError."""
    data = [{"obj": object()}]
    with pytest.raises(TypeError):
        write_jsonl(temp_file, data)

def test_read_malformed_jsonl(temp_file):
    """Test reading a file with malformed JSON."""
    temp_file.write_text('{"id": 1}\n{broken json\n', encoding='utf-8')
    
    gen = read_jsonl(temp_file)
    assert next(gen) == {"id": 1}
    
    with pytest.raises(json.JSONDecodeError):
        next(gen)
