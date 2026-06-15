"""文档库 API 路由"""
from __future__ import annotations

import hashlib
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import load_config
from core.storage import (
    build_blob_name,
    delete_file_from_storage,
    download_file_to_local,
    get_storage_prefix,
    upload_stream_to_storage,
)
from db.auth_repository import resolve_user_from_authorization
from db.library_repository import (
    LibraryDocRow,
    LibrarySpaceRow,
    add_library_doc,
    create_library_space,
    delete_library_doc,
    delete_library_space,
    get_library_doc_by_id,
    get_library_docs,
    get_library_space_by_id,
    get_library_spaces,
)

from utils.document_reader import read_document

from uuid import uuid4


router = APIRouter(prefix="/api/library", tags=["文档库管理"])

# 文档库文件上传目录
LIBRARY_UPLOAD_DIR = Path("workspace/library")
LIBRARY_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 响应模型
# ---------------------------------------------------------------------------

class SpaceItem(BaseModel):
    id: str
    name: str
    icon: str
    description: Optional[str] = None
    doc_count: int
    created_at: str
    updated_at: str


class SpaceListResponse(BaseModel):
    spaces: List[SpaceItem]


class DocItem(BaseModel):
    id: str
    space_id: str
    file_name: str
    file_size: int
    mime_type: Optional[str] = None
    file_extension: Optional[str] = None
    storage_key: Optional[str] = None
    blob_url: Optional[str] = None
    created_at: str
    updated_at: str


class DocListResponse(BaseModel):
    docs: List[DocItem]
    total: int


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _resolve_user(authorization: Optional[str], cfg):
    if not authorization:
        if cfg.auth.require_auth:
            raise HTTPException(status_code=401, detail="需要登录后访问")
        return None
    try:
        return resolve_user_from_authorization(authorization, cfg, required=True)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


def _space_to_dict(s: LibrarySpaceRow) -> Dict[str, Any]:
    def _fmt(dt):
        if not dt:
            return ""
        iso = dt.isoformat()
        return iso if iso.endswith("Z") else iso.replace("+00:00", "Z")

    return {
        "id": s.id,
        "name": s.name,
        "icon": s.icon,
        "description": s.description,
        "doc_count": s.doc_count,
        "created_at": _fmt(s.created_at),
        "updated_at": _fmt(s.updated_at),
    }


def _doc_to_dict(d: LibraryDocRow) -> Dict[str, Any]:
    def _fmt(dt):
        if not dt:
            return ""
        iso = dt.isoformat()
        return iso if iso.endswith("Z") else iso.replace("+00:00", "Z")

    return {
        "id": d.id,
        "space_id": d.space_id,
        "file_name": d.file_name,
        "file_size": d.file_size,
        "mime_type": d.mime_type,
        "file_extension": d.file_extension,
        "storage_key": d.storage_key,
        "blob_url": d.blob_url,
        "created_at": _fmt(d.created_at),
        "updated_at": _fmt(d.updated_at),
    }


def _compute_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:16]


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    else:
        return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"


# ---------------------------------------------------------------------------
# 空间管理
# ---------------------------------------------------------------------------

@router.get("/spaces", response_model=SpaceListResponse)
async def list_spaces(authorization: Optional[str] = Header(default=None)):
    """获取所有文档空间列表"""
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    spaces = get_library_spaces(config=cfg, user_id=user.id if user else None)
    return SpaceListResponse(spaces=[_space_to_dict(s) for s in spaces])


@router.post("/spaces", response_model=SpaceItem)
async def create_space(
    body: Dict[str, Any],
    authorization: Optional[str] = Header(default=None),
):
    """创建新文档空间"""
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="空间名称不能为空")

    icon = body.get("icon", "📁")
    description = body.get("description")

    space = create_library_space(
        name=name,
        icon=icon,
        description=description,
        config=cfg,
        user_id=user.id if user else None,
    )
    return _space_to_dict(space)


@router.put("/spaces/{space_id}", response_model=SpaceItem)
async def update_space(
    space_id: str,
    body: Dict[str, Any],
    authorization: Optional[str] = Header(default=None),
):
    """更新文档空间"""
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    space = get_library_space_by_id(space_id, config=cfg, user_id=user.id if user else None)
    if not space:
        raise HTTPException(status_code=404, detail="空间不存在")

    from db.library_repository import update_library_space
    result = update_library_space(
        space_id=space_id,
        name=body.get("name"),
        icon=body.get("icon"),
        description=body.get("description"),
        config=cfg,
        user_id=user.id if user else None,
    )
    if not result:
        raise HTTPException(status_code=404, detail="空间不存在")
    return _space_to_dict(result)


@router.delete("/spaces/{space_id}")
async def delete_space(
    space_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """删除文档空间（同时删除空间下所有文档）"""
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    space = get_library_space_by_id(space_id, config=cfg, user_id=user.id if user else None)
    if not space:
        raise HTTPException(status_code=404, detail="空间不存在")

    # 删除空间下所有文档的 Blob 文件
    docs = get_library_docs(space_id, config=cfg, user_id=user.id if user else None)
    for doc in docs:
        if doc.storage_key:
            delete_file_from_storage(doc.storage_key, config=cfg)

    success = delete_library_space(space_id, config=cfg, user_id=user.id if user else None)
    return {"success": success}


# ---------------------------------------------------------------------------
# 文档管理
# ---------------------------------------------------------------------------

@router.get("/spaces/{space_id}/docs", response_model=DocListResponse)
async def list_docs(
    space_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """获取空间下所有文档"""
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    space = get_library_space_by_id(space_id, config=cfg, user_id=user.id if user else None)
    if not space:
        raise HTTPException(status_code=404, detail="空间不存在")

    docs = get_library_docs(space_id, config=cfg, user_id=user.id if user else None)
    return DocListResponse(
        docs=[_doc_to_dict(d) for d in docs],
        total=len(docs),
    )


@router.post("/spaces/{space_id}/docs", response_model=DocItem)
async def upload_doc(
    space_id: str,
    file: UploadFile,
    authorization: Optional[str] = Header(default=None),
):
    """上传文档到指定空间"""
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    space = get_library_space_by_id(space_id, config=cfg, user_id=user.id if user else None)
    if not space:
        raise HTTPException(status_code=404, detail="空间不存在")

    file_name = file.filename or "unnamed"
    content = await file.read()
    file_size = len(content)

    # 读取内容用于计算 hash
    file_hash = _compute_file_hash(content)

    storage_key = None
    if cfg.storage.enabled:
        blob_prefix = get_storage_prefix(cfg)
        # 使用不可读的唯一名作为 blob 名，避免在对象键中包含原始文件名导致的非法字符问题
        ext = Path(file_name).suffix or ""
        unique_name = f"{file_hash}_{uuid4().hex}{ext}"
        blob_name = build_blob_name(space_id, unique_name, prefix=blob_prefix)
        storage_key = upload_stream_to_storage(
            BytesIO(content),
            config=cfg,
            blob_name=blob_name,
            content_type=file.content_type,
        )
        if not storage_key:
            raise HTTPException(status_code=502, detail="云存储上传失败")
    else:
        # 本地存储
        safe_name = f"{file_hash}_{file_name}"
        file_path = LIBRARY_UPLOAD_DIR / space_id / safe_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(content)
        storage_key = str(file_path)

    doc = add_library_doc(
        space_id=space_id,
        file_name=file_name,
        file_size=file_size,
        config=cfg,
        user_id=user.id if user else None,
        mime_type=file.content_type,
        storage_key=storage_key,
        blob_url=storage_key,
    )
    return _doc_to_dict(doc)


@router.delete("/docs/{doc_id}")
async def delete_doc(
    doc_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """删除文档"""
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    doc = get_library_doc_by_id(doc_id, config=cfg, user_id=user.id if user else None)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除 Blob 文件
    if doc.storage_key:
        delete_file_from_storage(doc.storage_key, config=cfg)

    success = delete_library_doc(doc_id, config=cfg, user_id=user.id if user else None)
    return {"success": success}


@router.post("/docs/delete-batch")
async def delete_docs_batch(
    body: Dict[str, Any],
    authorization: Optional[str] = Header(default=None),
):
    """批量删除文档"""
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    doc_ids: List[str] = body.get("doc_ids", [])
    if not doc_ids:
        raise HTTPException(status_code=400, detail="doc_ids 不能为空")

    results = []
    for doc_id in doc_ids:
        doc = get_library_doc_by_id(doc_id, config=cfg, user_id=user.id if user else None)
        if doc and doc.storage_key:
            delete_file_from_storage(doc.storage_key, config=cfg)
        success = delete_library_doc(doc_id, config=cfg, user_id=user.id if user else None)
        results.append({"doc_id": doc_id, "success": success})

    return {"results": results}


class SaveGeneratedRequest(BaseModel):
    """保存生成文件到文档库请求"""
    space_id: str
    file_path: str
    file_name: str


@router.post("/save-generated")
async def save_generated_file(
    body: SaveGeneratedRequest,
    authorization: Optional[str] = Header(default=None),
):
    """将生成的文件保存到文档库"""
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    # 验证空间是否存在
    space = get_library_space_by_id(body.space_id, config=cfg, user_id=user.id if user else None)
    if not space:
        raise HTTPException(status_code=404, detail="空间不存在")

    # 解析文件路径
    src_path = Path(body.file_path)
    if not src_path.exists():
        # 尝试相对于工作目录
        src_path = Path("workspace") / body.file_path
    if not src_path.exists():
        raise HTTPException(status_code=404, detail="源文件不存在")

    file_name = body.file_name or src_path.name
    file_size = src_path.stat().st_size

    # 读取文件内容
    content = src_path.read_bytes()
    file_hash = hashlib.md5(content).hexdigest()

    storage_key = None
    if cfg.storage.enabled:
        blob_prefix = get_storage_prefix(cfg)
        ext = Path(file_name).suffix or ""
        unique_name = f"{file_hash}_{uuid4().hex}{ext}"
        blob_name = build_blob_name(body.space_id, unique_name, prefix=blob_prefix)
        storage_key = upload_stream_to_storage(
            BytesIO(content),
            config=cfg,
            blob_name=blob_name,
            content_type="application/octet-stream",
        )
        if not storage_key:
            raise HTTPException(status_code=502, detail="云存储上传失败")
    else:
        safe_name = f"{file_hash}_{file_name}"
        file_path = LIBRARY_UPLOAD_DIR / body.space_id / safe_name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        storage_key = str(file_path)

    doc = add_library_doc(
        space_id=body.space_id,
        file_name=file_name,
        file_size=file_size,
        config=cfg,
        user_id=user.id if user else None,
        mime_type="application/octet-stream",
        storage_key=storage_key,
        blob_url=storage_key,
    )
    return _doc_to_dict(doc)


@router.get("/docs/{doc_id}/download")
async def download_doc(
    doc_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """下载文档"""
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    doc = get_library_doc_by_id(doc_id, config=cfg, user_id=user.id if user else None)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    storage_key = doc.storage_key
    blob_url = doc.blob_url
    file_name = doc.file_name
    mime_type = doc.mime_type or "application/octet-stream"

    file_path = None

    # 优先用 storage_key 从云存储下载
    if storage_key and cfg.storage.enabled:
        cache_path = Path(cfg.temp_dir) / "azure_blob_cache" / storage_key
        try:
            file_path = download_file_to_local(storage_key, cache_path, config=cfg)
        except Exception as exc:
            raise HTTPException(status_code=404, detail=f"文件不存在: {exc}")

    # 其次尝试 blob_url 作为本地路径
    if not file_path and blob_url:
        local_path = Path(blob_url)
        if local_path.exists():
            file_path = local_path

    # 最后尝试 storage_key 作为本地绝对路径
    if not file_path and storage_key:
        local_path = Path(storage_key)
        if local_path.exists():
            file_path = local_path

    if not file_path:
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=str(file_path),
        filename=file_name,
        media_type=mime_type,
    )


IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico'}
# 可被 LibreOffice 转换为 PDF 的格式
CONVERTIBLE_EXTENSIONS = {'.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.odt', '.ods', '.odp'}


def convert_to_pdf(input_path: str) -> str:
    """使用 LibreOffice 将文档转换为 PDF，返回 PDF 路径"""
    import subprocess
    import tempfile

    output_dir = tempfile.mkdtemp(prefix="pdfconv_")
    result = subprocess.run(
        ['libreoffice', '--headless', '--convert-to', 'pdf',
         '--outdir', output_dir, input_path],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"文档转 PDF 失败: {result.stderr}")
    pdf_name = Path(input_path).stem + '.pdf'
    pdf_path = str(Path(output_dir) / pdf_name)
    if not Path(pdf_path).exists():
        raise RuntimeError(f"转换后未找到 PDF 文件: {pdf_path}")
    return pdf_path


def _resolve_file_path(doc, cfg) -> Path:
    """解析文档的本地文件路径（统一路径解析逻辑）"""
    storage_key = doc.storage_key
    blob_url = doc.blob_url
    file_path = None

    if storage_key and cfg.storage.enabled:
        cache_path = Path(cfg.temp_dir) / "azure_blob_cache" / storage_key
        try:
            file_path = download_file_to_local(storage_key, cache_path, config=cfg)
        except Exception:
            pass
    if not file_path and blob_url:
        local_path = Path(blob_url)
        if local_path.exists():
            file_path = local_path
    if not file_path and storage_key:
        local_path = Path(storage_key)
        if local_path.exists():
            file_path = local_path
    if not file_path:
        raise HTTPException(status_code=404, detail="文件不存在")
    return file_path


@router.get("/docs/{doc_id}/preview-pdf")
async def preview_doc_as_pdf(
    doc_id: str,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(default=None),
):
    """预览文档 — 返回 PDF 文件流

    对 PDF 文件直接返回；对 docx/xlsx 等先用 LibreOffice 转换为 PDF 再返回。
    前端可用 <embed> 浏览器原生渲染。
    """
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    doc = get_library_doc_by_id(doc_id, config=cfg, user_id=user.id if user else None)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = _resolve_file_path(doc, cfg)
    file_ext = Path(doc.file_name).suffix.lower()
    file_name = doc.file_name

    # 已 PDF → 直接返回
    if file_ext == '.pdf':
        return FileResponse(
            path=str(file_path),
            filename=file_name,
            media_type='application/pdf',
        )

    # 可转换格式 → 转为 PDF
    if file_ext in CONVERTIBLE_EXTENSIONS:
        pdf_path = convert_to_pdf(str(file_path))
        # 响应完成后清理临时目录
        temp_dir = str(Path(pdf_path).parent)
        background_tasks.add_task(lambda: (
            Path(pdf_path).unlink(missing_ok=True),
            Path(temp_dir).rmdir() if Path(temp_dir).exists() else None,
        ))
        return FileResponse(
            path=pdf_path,
            filename=Path(file_name).stem + '.pdf',
            media_type='application/pdf',
        )

    raise HTTPException(status_code=400, detail=f"不支持的文档格式: {file_ext}")


@router.get("/docs/{doc_id}/preview")
async def preview_doc(
    doc_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """预览文档内容（文本提取预览）"""
    cfg = load_config()
    user = _resolve_user(authorization, cfg)

    doc = get_library_doc_by_id(doc_id, config=cfg, user_id=user.id if user else None)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    storage_key = doc.storage_key
    blob_url = doc.blob_url
    file_name = doc.file_name
    file_ext = Path(file_name).suffix.lower()

    # 解析文件路径（同 download 逻辑）
    file_path = None
    if storage_key and cfg.storage.enabled:
        cache_path = Path(cfg.temp_dir) / "azure_blob_cache" / storage_key
        try:
            file_path = download_file_to_local(storage_key, cache_path, config=cfg)
        except Exception:
            pass
    if not file_path and blob_url:
        local_path = Path(blob_url)
        if local_path.exists():
            file_path = local_path
    if not file_path and storage_key:
        local_path = Path(storage_key)
        if local_path.exists():
            file_path = local_path
    if not file_path:
        raise HTTPException(status_code=404, detail="文件不存在")

    # 图片类型 → 返回类型信息，前端用 download URL 展示
    if file_ext in IMAGE_EXTENSIONS:
        return {
            "id": doc_id,
            "file_name": file_name,
            "file_extension": file_ext,
            "type": "image",
        }

    # 其他文档类型 → 提取文本
    content = read_document(str(file_path))
    return {
        "id": doc_id,
        "file_name": file_name,
        "file_extension": file_ext,
        "type": "text",
        "content": content,
    }
