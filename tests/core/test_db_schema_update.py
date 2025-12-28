import sqlite3
import pytest
from pathlib import Path
from edmcp.core.db import DatabaseManager

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_eval.db"

def test_schema_includes_evaluation_columns(db_path):
    db = DatabaseManager(db_path)
    
    # Check columns in essays table
    cursor = db.conn.cursor()
    cursor.execute("PRAGMA table_info(essays)")
    columns = {row[1] for row in cursor.fetchall()}
    
    assert "evaluation" in columns
    assert "grade" in columns
    db.close()

def test_update_essay_evaluation(db_path):
    db = DatabaseManager(db_path)
    job_id = db.create_job()
    essay_id = db.add_essay(job_id, "Student", "Text")
    
    eval_json = '{"score": 85, "comments": "Good work"}'
    db.update_essay_evaluation(essay_id, eval_json, "85")
    
    cursor = db.conn.cursor()
    cursor.execute("SELECT evaluation, grade, status FROM essays WHERE id=?", (essay_id,))
    row = cursor.fetchone()
    
    assert row[0] == eval_json
    assert row[1] == "85"
    assert row[2] == "GRADED"
    db.close()
