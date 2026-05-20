"""文件存储适配层 - 根据配置自动选择后端。"""

from pathlib import Path
from typing import Optional, BinaryIO
import re

from config import SystemConfig, get_config


def _sanitize_filename(name: str) -> str:
    # 仅保留字母、数字、点、连字符和下划线，其他字符替换为下划线
    name = Path(name).name
    safe = re.sub(r"[^A-Za-z0-9.\-_]", "_", name)
    # 合并连续下划线为单个
    safe = re.sub(r"_+", "_", safe)
    return safe or "file"


def build_blob_name(session_id: str, file_name: str, prefix: str = "sessions") -> str:
    raw_name = Path(file_name).name
    safe_name = _sanitize_filename(raw_name)
    safe_session = str(session_id).strip().strip("/")
    safe_prefix = str(prefix).strip().strip("/") or "sessions"
    return f"{safe_prefix}/{safe_session}/{safe_name}"


def get_storage_prefix(config: Optional[SystemConfig] = None) -> str:
    cfg = config or get_config()
    if cfg.storage.provider == "supabase":
        return cfg.storage.supabase_storage_prefix
    return cfg.storage.azure_blob_prefix


def _get_backend(config: Optional[SystemConfig] = None):
    cfg = config or get_config()
    provider = cfg.storage.provider

    if provider == "supabase":
        from .supabase_storage import SupabaseStorage
        return SupabaseStorage(config=cfg)
    elif provider == "azure_blob":
        from .azure_blob_storage import AzureBlobStorage
        return AzureBlobStorage(config=cfg)
    return None


def get_storage_backend(config: Optional[SystemConfig] = None):
    return _get_backend(config)


def upload_file_to_storage(
    local_path: str | Path,
    config: Optional[SystemConfig] = None,
    blob_name: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Optional[str]:
    cfg = config or get_config()
    if cfg.storage.provider == "supabase":
        from .supabase_storage import upload_file_to_storage as _upload
        return _upload(local_path, config=config, blob_name=blob_name, content_type=content_type)
    elif cfg.storage.provider == "azure_blob":
        from .azure_blob_storage import upload_file_to_storage as _upload
        return _upload(local_path, config=config, blob_name=blob_name, content_type=content_type)
    return None


def upload_stream_to_storage(
    stream: BinaryIO,
    config: Optional[SystemConfig] = None,
    blob_name: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Optional[str]:
    cfg = config or get_config()
    if cfg.storage.provider == "supabase":
        from .supabase_storage import upload_stream_to_storage as _upload
        return _upload(stream, config=config, blob_name=blob_name, content_type=content_type)
    elif cfg.storage.provider == "azure_blob":
        from .azure_blob_storage import upload_stream_to_storage as _upload
        return _upload(stream, config=config, blob_name=blob_name, content_type=content_type)
    return None


def download_file_to_local(
    blob_name: str,
    destination: str | Path,
    config: Optional[SystemConfig] = None,
) -> Path:
    cfg = config or get_config()
    if cfg.storage.provider == "supabase":
        from .supabase_storage import download_file_to_local as _download
        return _download(blob_name, destination, config=config)
    elif cfg.storage.provider == "azure_blob":
        from .azure_blob_storage import download_file_to_local as _download
        return _download(blob_name, destination, config=config)
    raise RuntimeError(f"不支持的存储后端: {cfg.storage.provider}")


def delete_file_from_storage(blob_name: Optional[str], config: Optional[SystemConfig] = None) -> bool:
    if not blob_name:
        return False
    cfg = config or get_config()
    if cfg.storage.provider == "supabase":
        from .supabase_storage import delete_file_from_storage as _delete
        return _delete(blob_name, config=config)
    elif cfg.storage.provider == "azure_blob":
        from .azure_blob_storage import delete_file_from_storage as _delete
        return _delete(blob_name, config=config)
    return False


__all__ = [
    "build_blob_name",
    "get_storage_prefix",
    "get_storage_backend",
    "upload_file_to_storage",
    "upload_stream_to_storage",
    "download_file_to_local",
    "delete_file_from_storage",
]