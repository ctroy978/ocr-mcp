import shutil
from pathlib import Path
import pytest
from edmcp.core.job_manager import JobManager

@pytest.fixture
def temp_workspace(tmp_path):
    workspace = tmp_path / "jobs"
    workspace.mkdir()
    yield workspace
    shutil.rmtree(workspace)

def test_create_job_id_is_unique():
    """Test that generated job IDs are unique."""
    id1 = JobManager.generate_job_id()
    id2 = JobManager.generate_job_id()
    assert id1 != id2
    assert isinstance(id1, str)
    assert len(id1) > 0

def test_create_job_directory(temp_workspace):
    """Test creating a job directory."""
    job_id = "test_job_123"
    job_dir = JobManager.create_job_directory(job_id, temp_workspace)
    
    assert job_dir.exists()
    assert job_dir.is_dir()
    assert job_dir.name == job_id
    assert job_dir.parent == temp_workspace

def test_create_job_directory_creates_parents(temp_workspace):
    """Test that parent directories are created if they don't exist."""
    nested_workspace = temp_workspace / "nested" / "storage"
    job_id = "nested_job"
    
    # workspace doesn't fully exist yet
    job_dir = JobManager.create_job_directory(job_id, nested_workspace)
    
    assert job_dir.exists()
    assert nested_workspace.exists()

def test_get_job_directory(temp_workspace):
    """Test retrieving a job directory path."""
    job_id = "existing_job"
    expected_path = temp_workspace / job_id
    
    path = JobManager.get_job_directory(job_id, temp_workspace)
    assert path == expected_path
    # Does not necessarily check existence, just path construction
