import json
import os
import sqlite3
import threading
import uuid

from config.logger import get_logger

logger = get_logger("offline_outbox")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTBOX_DB = os.path.join(BASE_DIR, "logs", "offline_outbox.db")


class OfflineOutbox:
    """
    Hang doi ben vung luu tren dia bang SQLite (P0-4 + P0+ REV-05).
    - Khi mat mang hoac khoi dong lai may, su kien khong bi mat va co event_id UUID chong trung.
    - Phan biet loi tam thoi (RETRY) va loi vinh vien 4xx / qua gioi han retry (DEAD_LETTER).
    """

    def __init__(self, db_path=DEFAULT_OUTBOX_DB, max_rows=5000):
        self.db_path = db_path
        self.max_rows = max(1, int(max_rows))
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def _init_db(self):
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS outbox_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    task_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    retries INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'PENDING',
                    last_error TEXT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cols = {row[1] for row in conn.execute("PRAGMA table_info(outbox_events)").fetchall()}
            if "status" not in cols:
                conn.execute("ALTER TABLE outbox_events ADD COLUMN status TEXT DEFAULT 'PENDING'")
            if "last_error" not in cols:
                conn.execute("ALTER TABLE outbox_events ADD COLUMN last_error TEXT NULL")
            conn.commit()

    def enqueue(self, task_type, payload, event_id=None):
        eid = event_id or str(uuid.uuid4())
        body = dict(payload or {})
        body.setdefault("event_id", eid)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO outbox_events (event_id, task_type, payload_json, status)
                VALUES (?, ?, ?, 'PENDING')
                """,
                (eid, task_type, json.dumps(body, ensure_ascii=False)),
            )
            # AI-04: Gioi han dung luong toi da de chong tran o dia (uu tien xoa DEAD_LETTER truoc, roi den ban ghi cu nhat)
            total = int(conn.execute("SELECT COUNT(*) FROM outbox_events").fetchone()[0])
            excess = total - self.max_rows
            if excess > 0:
                conn.execute(
                    """
                    DELETE FROM outbox_events
                    WHERE id IN (
                        SELECT id FROM outbox_events
                        ORDER BY CASE WHEN status = 'DEAD_LETTER' THEN 0 ELSE 1 END, id ASC
                        LIMIT ?
                    )
                    """,
                    (excess,),
                )
            conn.commit()
        return eid

    def count_pending(self):
        with self._lock, self._connect() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM outbox_events WHERE status = 'PENDING'")
            return int(cur.fetchone()[0])

    def count_dead_letter(self):
        with self._lock, self._connect() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM outbox_events WHERE status = 'DEAD_LETTER'")
            return int(cur.fetchone()[0])

    def flush(self, handlers, max_batch=30, max_retries=20):
        """
        Doc toi da max_batch ban ghi PENDING cu nhat va goi handler tuong ung.
        Ket qua handler:
        - True / "OK" -> xoa khoi outbox
        - "DEAD_LETTER" -> danh dau DEAD_LETTER (loi 4xx vinh vien, khong retry vo han)
        - False / "RETRY" -> tang retries (chuyen DEAD_LETTER neu dat max_retries)
        """
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, event_id, task_type, payload_json, retries
                FROM outbox_events
                WHERE status = 'PENDING'
                ORDER BY id ASC
                LIMIT ?
                """,
                (max_batch,),
            ).fetchall()

        synced = 0
        for row_id, event_id, task_type, payload_json, retries in rows:
            handler = handlers.get(task_type)
            if handler is None:
                continue
            try:
                payload = json.loads(payload_json)
                result = handler(payload)
                if result is True or result == "OK":
                    with self._lock, self._connect() as conn:
                        conn.execute("DELETE FROM outbox_events WHERE id=?", (row_id,))
                        conn.commit()
                    synced += 1
                elif result == "DEAD_LETTER":
                    with self._lock, self._connect() as conn:
                        conn.execute(
                            """
                            UPDATE outbox_events
                            SET status = 'DEAD_LETTER',
                                retries = retries + 1,
                                last_error = 'Permanent 4xx rejection from server'
                            WHERE id = ?
                            """,
                            (row_id,),
                        )
                        conn.commit()
                else:
                    next_retries = int(retries or 0) + 1
                    new_status = "DEAD_LETTER" if next_retries >= max_retries else "PENDING"
                    err_msg = "Exceeded max_retries" if new_status == "DEAD_LETTER" else "Transient retry"
                    with self._lock, self._connect() as conn:
                        conn.execute(
                            """
                            UPDATE outbox_events
                            SET retries = ?, status = ?, last_error = ?
                            WHERE id = ?
                            """,
                            (next_retries, new_status, err_msg, row_id),
                        )
                        conn.commit()
            except Exception as e:
                logger.warning("Outbox flush failed for %s (%s): %s", task_type, event_id, e)
        return synced


offline_outbox = OfflineOutbox()
