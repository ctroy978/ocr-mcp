import sqlite3
import pytest
from pathlib import Path
from edmcp.core.db import DatabaseManager

@pytest.fixture
def db_manager():
    # Use in-memory DB for testing
    return DatabaseManager(":memory:")

def test_init_creates_tables(db_manager):
    # Verify tables exist
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    assert "jobs" in tables
    assert "essays" in tables

def test_create_job(db_manager):
    job_id = db_manager.create_job()
    assert job_id is not None
    
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT id, status FROM jobs WHERE id=?", (job_id,))
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == job_id
    assert row[1] == "PENDING"

def test_add_essay(db_manager):
    job_id = db_manager.create_job()
    essay_id = db_manager.add_essay(job_id, "John Doe", "Raw Text content", {"pages": 1})
    
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT student_name, raw_text, status FROM essays WHERE id=?", (essay_id,))
    row = cursor.fetchone()
    assert row[0] == "John Doe"
    assert row[1] == "Raw Text content"
    assert row[2] == "PENDING"

def test_update_essay_scrubbed(db_manager):
    job_id = db_manager.create_job()
    essay_id = db_manager.add_essay(job_id, "John Doe", "Raw Text content")
    
    db_manager.update_essay_scrubbed(essay_id, "Scrubbed content")
    
    cursor = db_manager.conn.cursor()
    cursor.execute("SELECT scrubbed_text, status FROM essays WHERE id=?", (essay_id,))
    row = cursor.fetchone()
    assert row[0] == "Scrubbed content"
    assert row[1] == "SCRUBBED"

def test_get_job_essays(db_manager):
    job_id = db_manager.create_job()
    db_manager.add_essay(job_id, "Student 1", "Text 1")
    db_manager.add_essay(job_id, "Student 2", "Text 2")
    
    essays = db_manager.get_job_essays(job_id)
    assert len(essays) == 2
    assert essays[0]['student_name'] == "Student 1"
    assert essays[1]['student_name'] == "Student 2"
