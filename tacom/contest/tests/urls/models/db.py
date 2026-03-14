import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import Config


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS test_run (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    label             TEXT,
    started_at        TEXT NOT NULL,
    finished_at       TEXT,
    total_discovered  INTEGER,
    total_excluded    INTEGER,
    total_anonymous   INTEGER,
    total_logged_in   INTEGER,
    total_by_capability INTEGER,
    total_by_group    INTEGER,
    total_parked      INTEGER,
    total_missed      INTEGER,
    total_visits      INTEGER,
    avg_response_ms   REAL
);

CREATE TABLE IF NOT EXISTS run_url_category (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER NOT NULL REFERENCES test_run(id),
    full_name   TEXT NOT NULL,
    url_pattern TEXT NOT NULL,
    view_module TEXT NOT NULL,
    view_name   TEXT NOT NULL,
    category    TEXT NOT NULL,
    subcategory TEXT,
    methods     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS visit (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           INTEGER NOT NULL REFERENCES test_run(id),
    url_full_name    TEXT NOT NULL,
    method           TEXT NOT NULL,
    user_type        TEXT NOT NULL,
    status_code      INTEGER NOT NULL,
    response_time_ms REAL NOT NULL,
    followed_redirects INTEGER NOT NULL,
    redirect_chain   TEXT,
    timestamp        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_run_url_category_run ON run_url_category(run_id);
CREATE INDEX IF NOT EXISTS idx_run_url_category_cat ON run_url_category(category);
CREATE INDEX IF NOT EXISTS idx_visit_run ON visit(run_id);
CREATE INDEX IF NOT EXISTS idx_visit_url ON visit(url_full_name);
"""

CLEANUP_SQL = """
DELETE FROM visit;
DELETE FROM run_url_category;
DELETE FROM test_run;
"""

_DEFAULT_DB_NAME = "urlmanager_runs.db"
_CONFIG_DIR = Path(__file__).parent.parent


class UrlManagerDb:
    def __init__(self, config: Config):
        self.config = config
        if config.stats.db_path:
            self.db_path = Path(config.stats.db_path)
        else:
            self.db_path = _CONFIG_DIR / _DEFAULT_DB_NAME

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    def cleanup(self) -> None:
        with self._connect() as conn:
            conn.executescript(CLEANUP_SQL)

    def persist_run(self, url_manager, run_label: str | None = None) -> int:
        self.init_schema()

        if self.config.stats.cleanup_on_start:
            self.cleanup()

        summary = url_manager.get_summary()
        stats = url_manager.get_stats_summary()

        now = datetime.now(timezone.utc).isoformat()
        avg_ms = stats.get("avg_response_time_ms", 0.0)

        by_cap_total = sum(summary.get("by_capability", {}).values())
        by_group_total = sum(summary.get("by_group", {}).values())

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO test_run
                    (label, started_at, finished_at,
                     total_discovered, total_excluded,
                     total_anonymous, total_logged_in,
                     total_by_capability, total_by_group,
                     total_parked, total_missed,
                     total_visits, avg_response_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_label,
                    now,
                    now,
                    summary["total_discovered"],
                    summary["excluded"],
                    summary["anonymous"],
                    summary["logged_in"],
                    by_cap_total,
                    by_group_total,
                    summary["parked"],
                    summary["missed"],
                    stats.get("total_visits", 0),
                    avg_ms,
                ),
            )
            run_id = cur.lastrowid

            # Snapshot all discovered URLs
            all_urls = list(url_manager._discovered) + list(url_manager._excluded)
            for url in all_urls:
                entry = url_manager._category_map.get(url.full_name)
                if entry:
                    category, subcategory, _ = entry
                elif url.full_name in url_manager._parked_names:
                    category, subcategory = "parked", None
                elif url in url_manager._excluded:
                    category, subcategory = "excluded", None
                else:
                    category, subcategory = "missed", None

                cur.execute(
                    """
                    INSERT INTO run_url_category
                        (run_id, full_name, url_pattern, view_module,
                         view_name, category, subcategory, methods)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        url.full_name,
                        url.url_pattern,
                        url.view_module,
                        url.view_name,
                        category,
                        subcategory,
                        ",".join(m.value for m in url.supported_methods),
                    ),
                )

            # Persist visit records
            for visit in url_manager._visits:
                cur.execute(
                    """
                    INSERT INTO visit
                        (run_id, url_full_name, method, user_type,
                         status_code, response_time_ms, followed_redirects,
                         redirect_chain, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        visit.url_full_name,
                        visit.method.value,
                        visit.user_type,
                        visit.status_code,
                        visit.response_time_ms,
                        1 if visit.followed_redirects else 0,
                        json.dumps(visit.redirect_chain),
                        visit.timestamp.isoformat(),
                    ),
                )

        return run_id
