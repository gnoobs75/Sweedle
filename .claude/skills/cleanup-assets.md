# /cleanup-assets

Remove orphaned files and failed generations.

## Usage
```
/cleanup-assets [--dry-run] [--include-failed] [--include-orphaned] [--older-than <days>]
```

## Options
- `--dry-run`: Show what would be deleted without actually deleting
- `--include-failed`: Remove failed generation attempts
- `--include-orphaned`: Remove files not linked to any database asset
- `--older-than <days>`: Only clean assets older than N days

## Instructions

### 1. Analyze Current State
```python
import sqlite3
from pathlib import Path
import os

# Database path
db_path = Path("C:/Claude/Sweedle/backend/data/sweedle.db")
storage_root = Path("C:/Claude/Sweedle/backend/storage")

# Get assets from database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count by status
cursor.execute("SELECT status, COUNT(*) FROM assets GROUP BY status")
status_counts = dict(cursor.fetchall())
print("Assets by status:")
for status, count in status_counts.items():
    print(f"  {status}: {count}")

# Get failed jobs
cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'failed'")
failed_jobs = cursor.fetchone()[0]
print(f"Failed jobs: {failed_jobs}")

conn.close()
```

### 2. Find Orphaned Files
Files in storage not linked to any asset:
```python
# Get all asset paths from database
cursor.execute("SELECT mesh_path, thumbnail_path, original_image_path FROM assets")
db_paths = set()
for row in cursor.fetchall():
    for path in row:
        if path:
            db_paths.add(path.replace('\\', '/').lower())

# Find all files in storage/generated
generated_dir = storage_root / "generated"
orphaned_files = []
for file_path in generated_dir.rglob("*"):
    if file_path.is_file():
        rel_path = str(file_path.relative_to(storage_root)).replace('\\', '/').lower()
        if rel_path not in db_paths:
            orphaned_files.append(file_path)

print(f"Orphaned files: {len(orphaned_files)}")
```

### 3. Find Failed Assets
```python
cursor.execute("""
    SELECT id, name, mesh_path, thumbnail_path, original_image_path
    FROM assets
    WHERE status = 'failed'
""")
failed_assets = cursor.fetchall()
print(f"Failed assets: {len(failed_assets)}")
```

### 4. Calculate Space to Free
```python
def get_size(path):
    if path and Path(path).exists():
        return Path(path).stat().st_size
    return 0

orphaned_size = sum(f.stat().st_size for f in orphaned_files)
failed_size = sum(get_size(storage_root / p) for asset in failed_assets for p in asset[2:] if p)

print(f"\nSpace to free:")
print(f"  Orphaned files: {orphaned_size / 1e6:.2f} MB")
print(f"  Failed assets: {failed_size / 1e6:.2f} MB")
print(f"  Total: {(orphaned_size + failed_size) / 1e6:.2f} MB")
```

### 5. Perform Cleanup (if not --dry-run)
```python
if not dry_run:
    deleted_count = 0
    freed_bytes = 0

    # Delete orphaned files
    if include_orphaned:
        for file_path in orphaned_files:
            try:
                size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                freed_bytes += size
            except Exception as e:
                print(f"  Error deleting {file_path}: {e}")

    # Delete failed assets
    if include_failed:
        for asset in failed_assets:
            asset_id = asset[0]
            for path in asset[2:]:
                if path:
                    full_path = storage_root / path
                    if full_path.exists():
                        try:
                            size = full_path.stat().st_size
                            full_path.unlink()
                            deleted_count += 1
                            freed_bytes += size
                        except Exception as e:
                            print(f"  Error: {e}")

            # Remove from database
            cursor.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
            cursor.execute("DELETE FROM jobs WHERE asset_id = ?", (asset_id,))

        conn.commit()

    print(f"\nDeleted {deleted_count} files, freed {freed_bytes / 1e6:.2f} MB")
```

### 6. Clean Empty Directories
```python
# Remove empty directories in generated/
for dir_path in sorted(generated_dir.rglob("*"), reverse=True):
    if dir_path.is_dir() and not any(dir_path.iterdir()):
        dir_path.rmdir()
        print(f"  Removed empty directory: {dir_path}")
```

### 7. Report Format
```
Asset Cleanup Report
====================
Mode: [Dry Run / Live]

Current State
-------------
Total Assets: XX
- Completed: XX
- Failed: XX
- Processing: XX

Failed Jobs: XX
Orphaned Files: XX

Cleanup Actions
---------------
[DRY RUN] Would delete:
  - XX orphaned files (XX.X MB)
  - XX failed assets (XX.X MB)

[LIVE] Deleted:
  - XX files
  - XX database records
  - Freed XX.X MB

Remaining
---------
Total Assets: XX
Storage Used: XX.X MB
```
