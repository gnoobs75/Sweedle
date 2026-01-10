# /db-maintenance

Run database maintenance tasks.

## Usage
```
/db-maintenance [vacuum|check|stats|backup|repair]
```

## Options
- `vacuum`: Reclaim disk space and optimize database
- `check`: Verify database integrity
- `stats`: Show database statistics
- `backup`: Create a backup of the database
- `repair`: Attempt to repair database issues

## Instructions

### Database Location
```
C:\Claude\Sweedle\backend\data\sweedle.db
```

### Command: stats
Show database statistics:
```python
import sqlite3
from pathlib import Path

db_path = Path("C:/Claude/Sweedle/backend/data/sweedle.db")
db_size = db_path.stat().st_size / 1e6

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Asset counts
cursor.execute("SELECT COUNT(*) FROM assets")
total_assets = cursor.fetchone()[0]

cursor.execute("SELECT status, COUNT(*) FROM assets GROUP BY status")
assets_by_status = dict(cursor.fetchall())

# Job counts
cursor.execute("SELECT COUNT(*) FROM jobs")
total_jobs = cursor.fetchone()[0]

cursor.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
jobs_by_status = dict(cursor.fetchall())

# Tag counts
cursor.execute("SELECT COUNT(DISTINCT tag) FROM asset_tags")
unique_tags = cursor.fetchone()[0]

# Recent activity
cursor.execute("SELECT MAX(created_at) FROM assets")
last_asset = cursor.fetchone()[0]

cursor.execute("SELECT MAX(created_at) FROM jobs")
last_job = cursor.fetchone()[0]

conn.close()

print(f"""
Database Statistics
===================
File: {db_path}
Size: {db_size:.2f} MB

Assets
------
Total: {total_assets}
By Status: {assets_by_status}

Jobs
----
Total: {total_jobs}
By Status: {jobs_by_status}

Tags
----
Unique Tags: {unique_tags}

Recent Activity
---------------
Last Asset: {last_asset}
Last Job: {last_job}
""")
```

### Command: check
Verify database integrity:
```python
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# SQLite integrity check
cursor.execute("PRAGMA integrity_check")
result = cursor.fetchone()[0]

if result == "ok":
    print("Database integrity: OK")
else:
    print(f"Database integrity issues: {result}")

# Check foreign key violations
cursor.execute("PRAGMA foreign_key_check")
fk_issues = cursor.fetchall()
if fk_issues:
    print(f"Foreign key violations: {len(fk_issues)}")
    for issue in fk_issues[:10]:
        print(f"  {issue}")
else:
    print("Foreign keys: OK")

# Check for orphaned records
cursor.execute("""
    SELECT COUNT(*) FROM jobs
    WHERE asset_id NOT IN (SELECT id FROM assets)
""")
orphaned_jobs = cursor.fetchone()[0]
print(f"Orphaned jobs: {orphaned_jobs}")

conn.close()
```

### Command: vacuum
Reclaim disk space:
```python
import shutil

# Get size before
size_before = db_path.stat().st_size

# Vacuum
conn = sqlite3.connect(db_path)
conn.execute("VACUUM")
conn.close()

# Get size after
size_after = db_path.stat().st_size
freed = size_before - size_after

print(f"Size before: {size_before / 1e6:.2f} MB")
print(f"Size after: {size_after / 1e6:.2f} MB")
print(f"Freed: {freed / 1e6:.2f} MB")
```

### Command: backup
Create database backup:
```python
from datetime import datetime
import shutil

backup_name = f"sweedle_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
backup_path = db_path.parent / backup_name

shutil.copy(db_path, backup_path)
print(f"Backup created: {backup_path}")
print(f"Size: {backup_path.stat().st_size / 1e6:.2f} MB")
```

### Command: repair
Attempt to repair database:
```python
# Create backup first
backup_path = db_path.with_suffix('.backup.db')
shutil.copy(db_path, backup_path)
print(f"Backup created: {backup_path}")

# Attempt repair by dumping and restoring
conn = sqlite3.connect(db_path)

# Export to SQL
with open('dump.sql', 'w') as f:
    for line in conn.iterdump():
        f.write(f'{line}\n')
conn.close()

# Remove corrupted database
db_path.unlink()

# Recreate from dump
conn = sqlite3.connect(db_path)
with open('dump.sql', 'r') as f:
    conn.executescript(f.read())
conn.close()

# Cleanup
Path('dump.sql').unlink()

print("Database repaired from dump")
```

### Report Format
```
Database Maintenance
====================
Command: <command>
Database: C:\Claude\Sweedle\backend\data\sweedle.db

[stats output / check output / vacuum output / etc.]

Recommendations
---------------
- If size > 100MB: Run vacuum
- If orphaned records: Run /cleanup-assets
- If integrity issues: Run repair (creates backup first)
```
