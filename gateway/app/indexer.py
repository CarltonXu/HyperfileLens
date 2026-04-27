"""
File indexing functionality for search
"""
import os
import json
import sqlite3
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class IndexedFile:
    """Represents an indexed file"""
    path: str
    name: str
    size: int
    modified_time: str
    extension: str
    directory: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FileIndexer:
    """Index files from mounted Kopia repository"""
    
    def __init__(self):
        self.mount_path = Path(settings.KOPIA_MOUNT_PATH)
        self.db_path = Path(settings.INDEX_DB_PATH)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for file index"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                name TEXT,
                size INTEGER,
                modified_time TEXT,
                extension TEXT,
                directory TEXT,
                indexed_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_name ON files(name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)
        """)
        
        conn.commit()
        conn.close()
    
    async def scan_and_index(self, base_path: Optional[str] = None) -> Dict[str, Any]:
        """Scan mounted repository and index all files"""
        scan_path = Path(base_path) if base_path else self.mount_path
        
        if not scan_path.exists():
            return {"status": "error", "message": "Mount path does not exist"}
        
        indexed_count = 0
        error_count = 0
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Clear existing index
        cursor.execute("DELETE FROM files")
        
        # Walk through all files
        for root, dirs, files in os.walk(str(scan_path)):
            for filename in files:
                try:
                    file_path = os.path.join(root, filename)
                    
                    # Get file stats
                    stat = os.stat(file_path)
                    
                    # Extract extension
                    _, ext = os.path.splitext(filename)
                    ext = ext.lower()
                    
                    # Create indexed file
                    indexed_file = IndexedFile(
                        path=file_path,
                        name=filename,
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        extension=ext,
                        directory=root
                    )
                    
                    # Insert into database
                    cursor.execute("""
                        INSERT OR REPLACE INTO files 
                        (path, name, size, modified_time, extension, directory, indexed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        indexed_file.path,
                        indexed_file.name,
                        indexed_file.size,
                        indexed_file.modified_time,
                        indexed_file.extension,
                        indexed_file.directory,
                        datetime.utcnow().isoformat()
                    ))
                    
                    indexed_count += 1
                    
                    # Yield control every 100 files
                    if indexed_count % 100 == 0:
                        await asyncio.sleep(0)
                        
                except Exception as e:
                    logger.error(f"Error indexing {filename}: {e}")
                    error_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"Indexing complete: {indexed_count} files indexed, {error_count} errors")
        
        return {
            "status": "completed",
            "indexed_count": indexed_count,
            "error_count": error_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def search(
        self,
        query: str,
        extension: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search indexed files"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        sql = """
            SELECT path, name, size, modified_time, extension, directory 
            FROM files 
            WHERE name LIKE ?
        """
        params = [f"%{query}%"]
        
        if extension:
            sql += " AND extension = ?"
            params.append(extension.lower())
        
        sql += " ORDER BY name LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(sql, params)
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "path": row[0],
                "name": row[1],
                "size": row[2],
                "modified_time": row[3],
                "extension": row[4],
                "directory": row[5]
            }
            for row in results
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM files")
        total_files = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(size) FROM files")
        total_size = cursor.fetchone()[0] or 0
        
        cursor.execute("""
            SELECT extension, COUNT(*) as count 
            FROM files 
            WHERE extension != '' 
            GROUP BY extension 
            ORDER BY count DESC 
            LIMIT 10
        """)
        extensions = [{"extension": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "total_files": total_files,
            "total_size": total_size,
            "extensions": extensions
        }
    
    def clear_index(self) -> Dict[str, Any]:
        """Clear the file index"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return {"status": "cleared", "deleted_count": deleted}


# Global instance
file_indexer = FileIndexer()
