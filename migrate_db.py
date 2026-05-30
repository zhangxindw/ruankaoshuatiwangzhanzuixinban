import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else 'instance/quiz_system.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if column exists
cursor.execute("PRAGMA table_info(wrong_questions)")
columns = [col[1] for col in cursor.fetchall()]

if 'reappearance_count' not in columns:
    cursor.execute('ALTER TABLE wrong_questions ADD COLUMN reappearance_count INTEGER DEFAULT 0')
    conn.commit()
    print('Column reappearance_count added successfully')
else:
    print('Column reappearance_count already exists')

conn.close()
