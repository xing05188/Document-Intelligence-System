"""数据库集成测试（需真实 PostgreSQL）。"""
from __future__ import annotations

import os
import uuid

import pytest


def _db_configured() -> bool:
    if os.getenv("DB_ENABLED", "").lower() != "true":
        return False
    return bool(
        os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_DB_URL")
        or os.getenv("DB_URL")
    )


pytestmark = pytest.mark.skipif(
    not _db_configured(),
    reason="需要 DB_ENABLED=true 且 DATABASE_URL（或 SUPABASE_DB_URL）",
)


def test_save_extraction_roundtrip():
    from config import load_config, set_config
    import config as cfgmod

    cfgmod._config = None
    cfg = load_config()
    set_config(cfg)

    from core.orchestrator.task_spec import TaskType
    from db.repository import (
        get_latest_extraction_by_task_id,
        get_task_by_task_id,
        save_extraction_from_agent_payload_safe,
    )

    tid = f"pytest-{uuid.uuid4().hex[:8]}"
    payload = {
        "data": {
            "schema_version": "1.0.0",
            "task_id": tid,
            "fields": [{"key": "k", "value": "v"}],
        }
    }
    ok, out, err = save_extraction_from_agent_payload_safe(
        payload, TaskType.ENTITY_EXTRACTION.value, "pytest-session", cfg
    )
    assert ok, err
    assert out is not None
    t = get_task_by_task_id(tid, cfg)
    assert t is not None
    assert t.status == "succeeded"
    ex = get_latest_extraction_by_task_id(tid, cfg)
    assert ex is not None
    assert ex.payload.get("fields")


def test_timeline_contains_steps(api_client):
    from config import load_config, set_config
    import config as cfgmod

    cfgmod._config = None
    cfg = load_config()
    set_config(cfg)

    from db.repository import get_task_timeline, save_extraction_from_agent_payload_safe
    from core.orchestrator.task_spec import TaskType

    tid = f"pytest-tl-{uuid.uuid4().hex[:8]}"
    save_extraction_from_agent_payload_safe(
        {
            "data": {
                "schema_version": "1.0.0",
                "task_id": tid,
                "fields": [{"key": "a", "value": 1}],
            }
        },
        TaskType.ENTITY_EXTRACTION.value,
        None,
        cfg,
    )
    tl = get_task_timeline(tid, cfg)
    assert tl is not None
    assert len(tl["steps"]) >= 1

    r = api_client.get(f"/tasks/{tid}/timeline")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "steps" in body["data"]
