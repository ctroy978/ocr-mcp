import csv
import pytest
from pathlib import Path
from edmcp.core.name_loader import NameLoader

@pytest.fixture
def temp_names_dir(tmp_path):
    d = tmp_path / "names"
    d.mkdir()
    
    # Create school_names.csv
    school_file = d / "school_names.csv"
    with open(school_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "first_name", "last_name", "grade"])
        writer.writerow(["1", "John", "Doe", "10"])
        writer.writerow(["2", "Jane", "Smith", "11"])
        
    # Create common_names.csv
    common_file = d / "common_names.csv"
    with open(common_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "frequency"])
        writer.writerow(["Michael", "100"])
        writer.writerow(["Sarah", "50"])
        
    return d

def test_load_all_names(temp_names_dir):
    loader = NameLoader(temp_names_dir)
    names = loader.load_all_names()
    
    # Check that we got a set of lowercase names
    expected = {"john", "doe", "jane", "smith", "michael", "sarah"}
    assert names == expected

def test_load_school_names_columns(temp_names_dir):
    loader = NameLoader(temp_names_dir)
    names = loader._load_school_names(temp_names_dir / "school_names.csv")
    assert "john" in names
    assert "doe" in names

def test_load_common_names_column(temp_names_dir):
    loader = NameLoader(temp_names_dir)
    names = loader._load_common_names(temp_names_dir / "common_names.csv")
    assert "michael" in names
    assert "sarah" in names

def test_ignore_short_names(temp_names_dir):
    # Add a short name to school file
    with open(temp_names_dir / "school_names.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["3", "Al", "B", "12"]) # "Al" is length 2, "B" is 1
        
    loader = NameLoader(temp_names_dir, min_length=3)
    names = loader.load_all_names()
    
    assert "al" not in names
    assert "b" not in names
    assert "john" in names
