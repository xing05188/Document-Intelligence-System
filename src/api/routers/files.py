"""文件管理 API 路由"""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from config import load_config
from db.session_repository import (
    add_session_file,
    delete_session_file,
    get_session_by_id,
    get_session_files,
    update_file_selection,
)

router = APIRouter(prefix="/api/sessions/{session_id}/files", tags=["文件管理"])

# 文件存储目录
UPLOAD_DIR = Path("workspace/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class FileResponse(BaseModel):
    id: int
    file_name: str
    file_type: str
    file_size: int
    is_selected: bool
    created_at: str


class FileListResponse(BaseModel):
    data_files: List[FileResponse]
    template_files: List[FileResponse]


class FileSelectionRequest(BaseModel):
    file_id: int
    is_selected: bool


def _file_to_dict(f) -> Dict[str, Any]:
    return {
        "id": f.id,
        "file_name": f.file_name,
        "file_type": f.file_type,
        "file_size": f.file_size,
        "is_selected": f.is_selected,
        "created_at": f.created_at.isoformat() + "Z" if f.created_at else "",
    }


@router.get("", response_model=FileListResponse)
async def list_files(session_id: str):
    """获取会话的所有文件（按类型分组）"""
    cfg = load_config()
    
    # 检查会话是否存在
    session = get_session_by_id(session_id, config=cfg)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    all_files = get_session_files(session_id, config=cfg)
    
    data_files = [_file_to_dict(f) for f in all_files if f.file_type == "data"]
    template_files = [_file_to_dict(f) for f in all_files if f.file_type == "template"]
    
    return FileListResponse(data_files=data_files, template_files=template_files)


@router.post("", response_model=FileResponse)
async def upload_file(
    session_id: str,
    file: UploadFile,
    file_type: str = Form(..., description="文件类型: data 或 template"),
):
    """
    上传文件到会话
    """
    cfg = load_config()
    
    # 检查会话是否存在
    session = get_session_by_id(session_id, config=cfg)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 验证文件类型
    if file_type not in ("data", "template"):
        raise HTTPException(status_code=400, detail="file_type 必须是 'data' 或 'template'")
    
    # 保存文件
    file_name = file.filename or "unnamed"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{timestamp}_{file_name}"
    file_path = UPLOAD_DIR / session_id / safe_name
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_size = 0
    with open(file_path, "wb") as buffer:
        while chunk := file.file.read(8192):
            buffer.write(chunk)
            file_size += len(chunk)
    
    # 保存到数据库
    session_file = add_session_file(
        session_id=session_id,
        file_name=file_name,
        file_type=file_type,
        file_path=str(file_path),
        file_size=file_size,
        config=cfg,
    )
    
    return _file_to_dict(session_file)


@router.patch("/selection")
async def update_file_selections(
    session_id: str,
    selections: List[FileSelectionRequest],
):
    """批量更新文件勾选状态"""
    cfg = load_config()
    
    # 检查会话是否存在
    session = get_session_by_id(session_id, config=cfg)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    results = []
    for sel in selections:
        success = update_file_selection(sel.file_id, sel.is_selected, config=cfg)
        results.append({"file_id": sel.file_id, "success": success})
    
    return {"results": results}


@router.delete("/{file_id}")
async def delete_file(session_id: str, file_id: int):
    """删除文件"""
    cfg = load_config()
    
    # 检查会话是否存在
    session = get_session_by_id(session_id, config=cfg)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    # 获取文件信息（用于删除物理文件）
    files = get_session_files(session_id, config=cfg)
    file_info = next((f for f in files if f.id == file_id), None)
    
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 删除物理文件
    file_path = Path(file_info.file_path)
    if file_path.exists():
        file_path.unlink()
    
    # 删除数据库记录
    success = delete_session_file(file_id, config=cfg)
    
    return {"success": success}


@router.get("/{file_id}/download")
async def download_file(session_id: str, file_id: int):
    """下载文件"""
    cfg = load_config()
    
    files = get_session_files(session_id, config=cfg)
    file_info = next((f for f in files if f.id == file_id), None)
    
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_path = Path(file_info.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(file_path),
        filename=file_info.file_name,
        media_type="application/octet-stream",
    )
