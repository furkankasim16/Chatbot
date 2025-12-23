
import sqlite3
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.core.config import settings

def migrate():
    # Attempt to locate the DB file from settings
    db_file = settings.QUESTIONS_DB_PATH
    
    print(f"Migrating database: {db_file}")
    
    conn = sqlite3.connect(str(db_file))
    c = conn.cursor()
    
    try:
        c.execute("ALTER TABLE questions ADD COLUMN source_context TEXT")
        print("Successfully added 'source_context' column.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("Column 'source_context' already exists.")
        else:
            print(f"Error adding column: {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
