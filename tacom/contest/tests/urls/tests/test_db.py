import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest

from contest.tests.urls.models.config import (
    Config,
    DiscoveredUrl,
    ExcludeConfig,
    HttpMethod,
    StatsConfig,
    VisitRecord,
)
from contest.tests.urls.models.db import UrlManagerDb
from contest.tests.urls.models.url_manager import UrlManager


def make_config(db_path=None, cleanup_on_start=False):
    return Config(
        exclude=ExcludeConfig(),
        stats=StatsConfig(
            enabled=True,
            db_path=str(db_path) if db_path else None,
            cleanup_on_start=cleanup_on_start,
        ),
    )


def make_url_manager(config, urls=None, visits=None):
    mgr = UrlManager(config=config)
    if urls:
        mgr._discovered = urls
        mgr._url_map = {u.full_name: u for u in urls}
    if visits:
        mgr._visits = visits
    mgr.categorize()
    return mgr


def make_url(name="home", namespace=""):
    return DiscoveredUrl(
        name=name,
        namespace=namespace,
        url_pattern=f"/{name}/",
        view_module="views",
        view_name="View",
        supported_methods=[HttpMethod.GET],
    )


def make_visit(url_full_name="home"):
    return VisitRecord(
        url_full_name=url_full_name,
        method=HttpMethod.GET,
        user_type="anonymous",
        status_code=200,
        response_time_ms=42.0,
        followed_redirects=False,
        timestamp=datetime.now(timezone.utc),
    )


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_runs.db"


class TestSchema:
    def test_schema_created(self, tmp_db):
        config = make_config(db_path=tmp_db)
        db = UrlManagerDb(config=config)
        db.init_schema()

        conn = sqlite3.connect(str(tmp_db))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        conn.close()

        assert "test_run" in tables
        assert "run_url_category" in tables
        assert "visit" in tables

    def test_schema_idempotent(self, tmp_db):
        config = make_config(db_path=tmp_db)
        db = UrlManagerDb(config=config)
        db.init_schema()
        db.init_schema()  # Should not raise


class TestPersistRun:
    def test_persist_run_creates_record(self, tmp_db):
        config = make_config(db_path=tmp_db)
        url = make_url()
        mgr = make_url_manager(config, urls=[url])

        db = UrlManagerDb(config=config)
        run_id = db.persist_run(mgr, run_label="test-run")

        conn = sqlite3.connect(str(tmp_db))
        cur = conn.cursor()
        cur.execute("SELECT label, total_missed FROM test_run WHERE id = ?", (run_id,))
        row = cur.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "test-run"

    def test_run_label_stored(self, tmp_db):
        config = make_config(db_path=tmp_db)
        mgr = make_url_manager(config)

        db = UrlManagerDb(config=config)
        run_id = db.persist_run(mgr, run_label="my-label")

        conn = sqlite3.connect(str(tmp_db))
        cur = conn.cursor()
        cur.execute("SELECT label FROM test_run WHERE id = ?", (run_id,))
        row = cur.fetchone()
        conn.close()

        assert row[0] == "my-label"

    def test_visit_records_saved(self, tmp_db):
        config = make_config(db_path=tmp_db)
        url = make_url()
        visit = make_visit()
        mgr = make_url_manager(config, urls=[url], visits=[visit])

        db = UrlManagerDb(config=config)
        run_id = db.persist_run(mgr)

        conn = sqlite3.connect(str(tmp_db))
        cur = conn.cursor()
        cur.execute("SELECT url_full_name, status_code FROM visit WHERE run_id = ?", (run_id,))
        rows = cur.fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0][0] == "home"
        assert rows[0][1] == 200

    def test_category_snapshot_saved(self, tmp_db):
        from contest.tests.urls.models.config import RoutePolicy, RoutePack

        config = Config(
            exclude=ExcludeConfig(),
            anonymous=[RoutePolicy(routes=[RoutePack(names=["home"])])],
            stats=StatsConfig(enabled=True, db_path=str(tmp_db)),
        )
        url = make_url()
        mgr = make_url_manager(config, urls=[url])

        db = UrlManagerDb(config=config)
        run_id = db.persist_run(mgr)

        conn = sqlite3.connect(str(tmp_db))
        cur = conn.cursor()
        cur.execute(
            "SELECT full_name, category FROM run_url_category WHERE run_id = ?",
            (run_id,)
        )
        rows = cur.fetchall()
        conn.close()

        assert len(rows) > 0
        categories = {row[1] for row in rows}
        assert "anonymous" in categories

    def test_multiple_runs_tracked(self, tmp_db):
        config = make_config(db_path=tmp_db)
        mgr = make_url_manager(config)

        db = UrlManagerDb(config=config)
        id1 = db.persist_run(mgr, run_label="run-1")
        id2 = db.persist_run(mgr, run_label="run-2")

        assert id1 != id2

        conn = sqlite3.connect(str(tmp_db))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM test_run")
        count = cur.fetchone()[0]
        conn.close()

        assert count == 2

    def test_cleanup_on_start_truncates(self, tmp_db):
        config = make_config(db_path=tmp_db)
        mgr = make_url_manager(config)
        db = UrlManagerDb(config=config)
        db.persist_run(mgr, run_label="old-run")

        # Now persist with cleanup
        config_clean = make_config(db_path=tmp_db, cleanup_on_start=True)
        db2 = UrlManagerDb(config=config_clean)
        db2.persist_run(mgr, run_label="new-run")

        conn = sqlite3.connect(str(tmp_db))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM test_run")
        count = cur.fetchone()[0]
        conn.close()

        assert count == 1

    def test_append_mode_preserves(self, tmp_db):
        config = make_config(db_path=tmp_db, cleanup_on_start=False)
        mgr = make_url_manager(config)
        db = UrlManagerDb(config=config)
        db.persist_run(mgr, run_label="run-1")
        db.persist_run(mgr, run_label="run-2")

        conn = sqlite3.connect(str(tmp_db))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM test_run")
        count = cur.fetchone()[0]
        conn.close()

        assert count == 2

    def test_custom_db_path(self, tmp_path):
        custom_path = tmp_path / "custom" / "runs.db"
        custom_path.parent.mkdir(parents=True, exist_ok=True)

        config = make_config(db_path=custom_path)
        mgr = make_url_manager(config)
        db = UrlManagerDb(config=config)
        db.persist_run(mgr)

        assert custom_path.exists()

    def test_redirect_chain_serialized(self, tmp_db):
        config = make_config(db_path=tmp_db)
        visit = VisitRecord(
            url_full_name="home",
            method=HttpMethod.GET,
            user_type="anonymous",
            status_code=200,
            response_time_ms=42.0,
            followed_redirects=True,
            redirect_chain=["/redirect1/", "/redirect2/"],
            timestamp=datetime.now(timezone.utc),
        )
        mgr = make_url_manager(config, visits=[visit])

        db = UrlManagerDb(config=config)
        run_id = db.persist_run(mgr)

        conn = sqlite3.connect(str(tmp_db))
        cur = conn.cursor()
        cur.execute("SELECT redirect_chain FROM visit WHERE run_id = ?", (run_id,))
        row = cur.fetchone()
        conn.close()

        chain = json.loads(row[0])
        assert chain == ["/redirect1/", "/redirect2/"]
