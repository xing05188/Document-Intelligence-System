"""pytest 公共配置：src 在路径中、加载 .env。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
_SRC = ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

load_dotenv(ROOT / ".env")


@pytest.fixture
def api_client():
    """FastAPI TestClient。"""
    from fastapi.testclient import TestClient
    from api.main import app

    return TestClient(app)
