"""
Offline Queue — SQLite-based resilience queue for the Windows agent.
When the backend is unreachable (offline mode), queued operations
are persisted locally and retried automatically when connectivity returns.
"""
import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import agent_logger


class OfflineQueue:
    """
    SQLite-backed offline queue for video ingestion payloads and
    other operations that need to survive connectivity loss.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path(settings.root_path) / "agent_queue.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create the queue table if it doesn't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS offline_queue (
                    id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING',
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 5,
                    created_at REAL NOT NULL,
                    last_attempted_at REAL,
                    error_message TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_queue_status
                ON offline_queue(status)
            """)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=10)

    def enqueue(self, operation: str, payload: Dict[str, Any], max_retries: int = 5) -> str:
        """
        Add an operation to the offline queue.
        
        Args:
            operation: Type of operation (e.g., 'notify_new_video', 'update_status')
            payload: JSON-serializable data for the operation
            max_retries: Maximum number of retry attempts
            
        Returns:
            Queue item ID
        """
        item_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO offline_queue 
                   (id, operation, payload, status, max_retries, created_at)
                   VALUES (?, ?, ?, 'PENDING', ?, ?)""",
                (item_id, operation, json.dumps(payload), max_retries, time.time())
            )
            conn.commit()
        agent_logger.info(f"Queued offline operation: {operation} (id={item_id[:8]}...)")
        return item_id

    def get_pending(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get pending items from the queue, oldest first."""
        with self._connect() as conn:
            cursor = conn.execute(
                """SELECT id, operation, payload, retry_count, max_retries, created_at
                   FROM offline_queue
                   WHERE status = 'PENDING'
                   ORDER BY created_at ASC
                   LIMIT ?""",
                (limit,)
            )
            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "operation": row[1],
                "payload": json.loads(row[2]),
                "retry_count": row[3],
                "max_retries": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]

    def mark_completed(self, item_id: str):
        """Mark a queue item as successfully processed."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE offline_queue SET status = 'COMPLETED', last_attempted_at = ? WHERE id = ?",
                (time.time(), item_id)
            )
            conn.commit()
        agent_logger.debug(f"Queue item completed: {item_id[:8]}...")

    def mark_failed(self, item_id: str, error_message: str):
        """
        Record a failure. If retries are exhausted, mark as DEAD_LETTER;
        otherwise keep as PENDING for the next retry cycle.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT retry_count, max_retries FROM offline_queue WHERE id = ?",
                (item_id,)
            )
            row = cursor.fetchone()
            if not row:
                return

            retry_count, max_retries = row
            new_count = retry_count + 1

            if new_count >= max_retries:
                status = "DEAD_LETTER"
                agent_logger.warning(
                    f"Queue item exhausted retries ({new_count}/{max_retries}): {item_id[:8]}..."
                )
            else:
                status = "PENDING"
                agent_logger.debug(
                    f"Queue item retry {new_count}/{max_retries}: {item_id[:8]}..."
                )

            conn.execute(
                """UPDATE offline_queue 
                   SET status = ?, retry_count = ?, last_attempted_at = ?, error_message = ?
                   WHERE id = ?""",
                (status, new_count, time.time(), error_message, item_id)
            )
            conn.commit()

    def get_dead_letters(self) -> List[Dict[str, Any]]:
        """Get items that have exhausted all retries."""
        with self._connect() as conn:
            cursor = conn.execute(
                """SELECT id, operation, payload, retry_count, error_message, created_at
                   FROM offline_queue
                   WHERE status = 'DEAD_LETTER'
                   ORDER BY created_at DESC"""
            )
            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "operation": row[1],
                "payload": json.loads(row[2]),
                "retry_count": row[3],
                "error_message": row[4],
                "created_at": row[5],
            }
            for row in rows
        ]

    def retry_dead_letter(self, item_id: str):
        """Reset a dead-letter item back to PENDING for another attempt."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE offline_queue 
                   SET status = 'PENDING', retry_count = 0, error_message = NULL
                   WHERE id = ? AND status = 'DEAD_LETTER'""",
                (item_id,)
            )
            conn.commit()
        agent_logger.info(f"Dead-letter item reset to PENDING: {item_id[:8]}...")

    def purge_completed(self, older_than_hours: float = 24.0):
        """Remove completed items older than the specified hours."""
        cutoff = time.time() - (older_than_hours * 3600)
        with self._connect() as conn:
            result = conn.execute(
                "DELETE FROM offline_queue WHERE status = 'COMPLETED' AND created_at < ?",
                (cutoff,)
            )
            conn.commit()
            count = result.rowcount
        if count > 0:
            agent_logger.info(f"Purged {count} completed queue items older than {older_than_hours}h")

    def queue_stats(self) -> Dict[str, int]:
        """Return counts by status."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT status, COUNT(*) FROM offline_queue GROUP BY status"
            )
            return dict(cursor.fetchall())


# Singleton
offline_queue = OfflineQueue()
