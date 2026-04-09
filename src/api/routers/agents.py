"""Agent 编排 API 路由"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/agents", tags=["Agent编排"])

# ============ Agent 能力定义 ============

MODES = [
    {
        "id": "default_conversation",
        "name": "默认对话",
        "description": "自由对话，通用问答",
        "requires_data": False,
        "requires_template": False,
    },
    {
        "id": "document_understanding",
        "name": "文档理解",
        "description": "上传文档后可交互式提问",
        "requires_data": True,
        "requires_template": False,
    },
    {
        "id": "document_editing",
        "name": "文档编辑",
        "description": "自然语言编辑Word/Excel/文本",
        "requires_data": True,
        "requires_template": False,
    },
    {
        "id": "entity_extraction",
        "name": "实体提取",
        "description": "从文档提取结构化数据",
        "requires_data": True,
        "requires_template": None,  # 可选
    },
    {
        "id": "table_filling",
        "name": "表格填表",
        "description": "条件筛选并填入模板",
        "requires_data": True,
        "requires_template": True,
    },
]


class TaskSpec(BaseModel):
    mode: str = Field(..., description="模式: default_conversation, document_understanding, etc.")
    content: str = Field(..., description="任务内容")
    session_id: str = Field(..., description="会话ID")
    files: List[Dict[str, Any]] = Field(default_factory=list, description="关联文件列表")


class AgentCapabilitiesResponse(BaseModel):
    modes: List[Dict[str, Any]]


@router.get("/capabilities", response_model=AgentCapabilitiesResponse)
async def get_capabilities():
    """获取所有 Agent 能力"""
    return AgentCapabilitiesResponse(modes=MODES)


@router.post("/execute")
async def execute_task(task: TaskSpec):
    """
    直接执行 Agent 任务
    此端点用于前端直接调用 Agent，不走 WebSocket
    """
    from service.agent_service import AgentService
    
    agent_service = AgentService()
    result = await agent_service.execute_task(
        session_id=task.session_id,
        mode=task.mode,
        content=task.content,
        files=task.files,
    )
    return result
