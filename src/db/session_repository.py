"""会话和消息的数据库操作

当数据库未启用时，自动使用内存存储进行测试。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .models import FileRow, MessageRow, SessionListItem, SessionRow, SessionWithMessages
from .memory_store import (
    add_message,
    add_session_file,
    create_session,
    delete_session,
    delete_session_file,
    get_messages,
    get_session_by_id,
    get_session_files,
    get_session_with_messages,
    list_sessions,
    update_file_selection,
    update_session,
)

# 导出所有函数
__all__ = [
    'create_session',
    'get_session_by_id',
    'list_sessions',
    'update_session',
    'delete_session',
    'add_message',
    'get_messages',
    'get_session_with_messages',
    'add_session_file',
    'get_session_files',
    'update_file_selection',
    'delete_session_file',
]
