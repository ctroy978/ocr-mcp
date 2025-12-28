import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

class DatabaseManager:
    """
    Manages the SQLite database for the OCR-MCP pipeline.
    Handles storage of jobs, essays, and their states.
    """
    
    def __init__(self, db_path: Union[str, Path] = "edmcp.db"):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        self._create_tables()

    def _create_tables(self):
        """Creates the necessary tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Jobs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING'
            )
        """)
        
        # Essays Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS essays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                student_name TEXT,
                raw_text TEXT,
                scrubbed_text TEXT,
                normalized_text TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                metadata TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
        """)
        
        self.conn.commit()

    def create_job(self) -> str:
        """Creates a new job and returns its ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_suffix = str(uuid.uuid4())[:8]
        job_id = f"job_{timestamp}_{unique_suffix}"
        
        created_at = datetime.now().isoformat()
        
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (id, created_at) VALUES (?, ?)",
            (job_id, created_at)
        )
        self.conn.commit()
        return job_id

    def add_essay(self, job_id: str, student_name: Optional[str], raw_text: str, metadata: Dict[str, Any] = None) -> int:
        """Adds a new essay record to a job."""
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO essays (job_id, student_name, raw_text, metadata)
            VALUES (?, ?, ?, ?)
            """,
            (job_id, student_name, raw_text, metadata_json)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_essay_scrubbed(self, essay_id: int, scrubbed_text: str):
        """Updates an essay with scrubbed text and sets status to SCRUBBED."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE essays 
            SET scrubbed_text = ?, status = 'SCRUBBED' 
            WHERE id = ?
            """,
            (scrubbed_text, essay_id)
        )
        self.conn.commit()

    def get_job_essays(self, job_id: str) -> List[Dict[str, Any]]:
        """Retrieves all essays for a specific job."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM essays WHERE job_id = ?", (job_id,))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            item = dict(row)
            if item['metadata']:
                try:
                    item['metadata'] = json.loads(item['metadata'])
                except json.JSONDecodeError:
                    pass
            results.append(item)
        return results

    def close(self):
        """Closes the database connection."""
        self.conn.close()
