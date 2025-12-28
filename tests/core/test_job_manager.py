import shutil
from pathlib import Path
import pytest
from edmcp.core.job_manager import JobManager
from edmcp.core.db import DatabaseManager

@pytest.fixture
def temp_workspace(tmp_path):
    workspace = tmp_path / "jobs"
    workspace.mkdir()
    yield workspace
    shutil.rmtree(workspace)

@pytest.fixture
def db_manager():
    return DatabaseManager(":memory:")

@pytest.fixture
def job_manager(temp_workspace, db_manager):
    return JobManager(temp_workspace, db_manager)

def test_create_job(job_manager):
    """Test creating a job (DB record + Directory)."""
    job_id = job_manager.create_job()
    
    # Check Directory
    job_dir = job_manager.get_job_directory(job_id)
    assert job_dir.exists()
    assert job_dir.is_dir()
    
    # Check DB
    cursor = job_manager.db.conn.cursor()
    cursor.execute("SELECT id FROM jobs WHERE id=?", (job_id,))
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == job_id

def test_get_job_directory(job_manager):
    """Test retrieving a job directory path."""
    job_id = "test_job_123" # Manually construct path, though job might not exist in DB for this specific test
    expected_path = job_manager.base_path / job_id
    
    path = job_manager.get_job_directory(job_id)
    assert path == expected_path
