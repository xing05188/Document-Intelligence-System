"""消息管理 API 路由"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from config import load_config
from db.session_repository import (
    add_message,
    get_messages,
    get_session_by_id,
)
from service.agent_service import AgentService, get_selected_session_files_payload

router = APIRouter(prefix="/api/messages", tags=["消息管理"])


class SendMessageRequest(BaseModel):
    content: str = Field(..., description="消息内容")
    mode: Optional[str] = Field(
        default=None,
        description="工作模式；不传则使用会话在库中的 current_mode",
    )
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


class MessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str


class SendMessageResponse(BaseModel):
    message_id: int
    content: str
    created_at: str


def _message_to_dict(m) -> Dict[str, Any]:
    return {
        "id": m.id,
        "session_id": str(m.session_id),
        "role": m.role,
        "content": m.content,
        "metadata": m.metadata,
        "created_at": m.created_at.isoformat() + "Z" if m.created_at else "",
    }


@router.get("/{session_id}", response_model=List[MessageResponse])
async def get_messages_api(session_id: str, limit: int = 100, offset: int = 0):
    """获取会话消息历史"""
    cfg = load_config()
    messages = get_messages(session_id, limit=limit, offset=offset, config=cfg)
    return [_message_to_dict(m) for m in messages]


@router.post("/{session_id}", response_model=SendMessageResponse)
async def send_message(session_id: str, request: SendMessageRequest):
    """
    发送消息并获取 AI 回复（非流式版本）
    用于简单场景或调试
    """
    cfg = load_config()
    
    # 检查会话是否存在
    session = get_session_by_id(session_id, config=cfg)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    effective_mode = (request.mode or session.current_mode or "default_conversation").strip()

    # 保存用户消息
    user_msg = add_message(
        session_id,
        "user",
        request.content,
        {**(request.metadata or {}), "mode": effective_mode},
        config=cfg,
    )

    db_data_files, db_template_files = get_selected_session_files_payload(session_id, cfg)

    # 调用 Agent 服务获取回复（必须与前端所选模式一致，否则恒走默认对话）
    agent_service = AgentService()
    response = await agent_service.chat(
        session_id,
        request.content,
        mode=effective_mode,
        files=db_data_files,
        template_files=db_template_files,
    )
    
    # 保存 AI 回复
    ai_msg = add_message(session_id, "assistant", response, config=cfg)
    
    return SendMessageResponse(
        message_id=ai_msg.id,
        content=ai_msg.content,
        created_at=ai_msg.created_at.isoformat() + "Z",
    )


# ============ WebSocket 流式聊天 ============

class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_text(self, session_id: str, text: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(text)
    
    async def send_json(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)


manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket 流式聊天
    前端连接后发送 JSON 消息：{"content": "...", "mode": "...", "files": [...], "template_files": [...]}
    后端流式返回：{"type": "chunk", "content": "..."} 或 {"type": "done", "content": "..."}
    """
    cfg = load_config()
    
    # 检查会话是否存在
    session = get_session_by_id(session_id, config=cfg)
    if not session:
        await websocket.close(code=4004, reason="会话不存在")
        return
    
    await manager.connect(websocket, session_id)
    
    try:
        # 保存用户消息
        data = await websocket.receive_json()
        user_content = data.get("content", "")
        # 显式 null/空串时回退到会话记录的模式，避免误走默认对话
        raw_mode = data.get("mode")
        mode = (raw_mode or session.current_mode or "default_conversation")
        if isinstance(mode, str):
            mode = mode.strip() or "default_conversation"
        client_files = data.get("files") or []
        client_templates = data.get("template_files") or []
        db_data_files, db_template_files = get_selected_session_files_payload(session_id, cfg)
        # 以库中勾选为准；无勾选时再允许客户端传入（兼容旧前端）
        files = db_data_files if db_data_files else client_files
        template_files = db_template_files if db_template_files else client_templates

        # 保存用户消息
        add_message(session_id, "user", user_content, {"mode": mode}, config=cfg)
        
        # 发送开始信号
        await manager.send_json(session_id, {"type": "start"})
        
        # 流式调用 Agent 服务（传递文件信息）
        agent_service = AgentService()
        full_response = ""
        
        async for chunk in agent_service.chat_stream(
            session_id, 
            user_content, 
            mode,
            files=files,
            template_files=template_files,
        ):
            full_response += chunk
            await manager.send_json(session_id, {"type": "chunk", "content": chunk})
        
        # 保存 AI 回复
        add_message(session_id, "assistant", full_response, {"mode": mode}, config=cfg)
        
        # 发送完成信号
        await manager.send_json(session_id, {"type": "done"})
        
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        await manager.send_json(session_id, {"type": "error", "message": str(e)})
    finally:
        manager.disconnect(session_id)
