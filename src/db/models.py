"""会话和消息相关的数据类型定义"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SessionMode(str, Enum):
    DEFAULT_CONVERSATION = "default_conversation"
    DOCUMENT_UNDERSTANDING = "document_understanding"
    DOCUMENT_EDITING = "document_editing"
    ENTITY_EXTRACTION = "entity_extraction"
    TABLE_FILLING = "table_filling"


@dataclass
class SessionRow:
    """会话数据行"""
    id: int
    session_id: str
    title: str
    current_mode: str
    created_at: datetime
    updated_at: datetime


@dataclass
class MessageRow:
    """消息数据行"""
    id: int
    session_id: int
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FileRow:
    """会话文件数据行"""
    id: int
    session_id: int
    file_name: str
    file_type: str  # "data" 或 "template"
    file_path: str
    file_size: int
    is_selected: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SessionWithMessages:
    """会话及其消息列表"""
    session: SessionRow
    messages: List[MessageRow]


@dataclass
class SessionListItem:
    """会话列表项（简化版）"""
    session_id: str
    title: str
    current_mode: str
    message_count: int
    updated_at: str
