import sqlite3
import sys
from pathlib import Path

def verify():
    db_path = "edmcp.db"
    print(f"Verifying schema of {db_path}...")
    
    if not Path(db_path).exists():
        print(f"File {db_path} does not exist yet. Run the server or a job first.")
        # We'll create it via DatabaseManager to force the check
        from edmcp.core.db import DatabaseManager
        db = DatabaseManager(db_path)
        db.close()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(essays)")
    columns = {row[1] for row in cursor.fetchall()}
    
    required = ["evaluation", "grade"]
    missing = [c for c in required if c not in columns]
    
    if not missing:
        print("SUCCESS: 'evaluation' and 'grade' columns are present in 'essays' table.")
        sys.exit(0)
    else:
        print(f"FAILURE: Missing columns: {missing}")
        sys.exit(1)

if __name__ == "__main__":
    verify()
