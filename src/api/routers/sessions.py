"""会话管理 API 路由"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import load_config
from db.session_repository import (
    create_session,
    delete_session,
    get_session_by_id,
    list_sessions,
    update_session,
)

router = APIRouter(prefix="/api/sessions", tags=["会话管理"])


class CreateSessionRequest(BaseModel):
    title: str = Field(default="新会话", description="会话标题")
    current_mode: str = Field(default="default_conversation", description="当前模式")


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = Field(default=None, description="会话标题")
    current_mode: Optional[str] = Field(default=None, description="当前模式")


class SessionResponse(BaseModel):
    session_id: str
    title: str
    current_mode: str
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    items: list[SessionResponse]
    total: int


def _session_to_dict(s) -> Dict[str, Any]:
    return {
        "session_id": s.session_id,
        "title": s.title,
        "current_mode": s.current_mode,
        "created_at": s.created_at.isoformat() + "Z" if s.created_at else "",
        "updated_at": s.updated_at.isoformat() + "Z" if s.updated_at else "",
    }


@router.post("", response_model=SessionResponse)
async def create_session_api(request: CreateSessionRequest):
    """创建新会话"""
    cfg = load_config()
    try:
        session = create_session(
            title=request.title,
            current_mode=request.current_mode,
            config=cfg,
        )
        return _session_to_dict(session)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=SessionListResponse)
async def list_sessions_api(limit: int = 50, offset: int = 0):
    """获取会话列表"""
    cfg = load_config()
    try:
        items, total = list_sessions(limit=limit, offset=offset, config=cfg)
        return SessionListResponse(
            items=[_session_to_dict(s) for s in items],
            total=total,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_api(session_id: str):
    """获取单个会话详情"""
    cfg = load_config()
    session = get_session_by_id(session_id, config=cfg)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return _session_to_dict(session)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session_api(session_id: str, request: UpdateSessionRequest):
    """更新会话（标题或模式）"""
    cfg = load_config()
    session = update_session(
        session_id,
        title=request.title,
        current_mode=request.current_mode,
        config=cfg,
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return _session_to_dict(session)


@router.delete("/{session_id}")
async def delete_session_api(session_id: str):
    """删除会话"""
    cfg = load_config()
    success = delete_session(session_id, config=cfg)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True}
