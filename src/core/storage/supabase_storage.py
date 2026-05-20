"""Supabase Storage 适配器。"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, BinaryIO

from config import SystemConfig, get_config

try:
    from supabase import create_client
except Exception:
    create_client = None


@dataclass(frozen=True)
class StoredFileResult:
    storage_key: str
    container_name: str


class SupabaseStorage:
    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or get_config()
        self._client = None
        self._bucket_name = None

    @property
    def enabled(self) -> bool:
        storage = self.config.storage
        return bool(
            storage.enabled
            and storage.provider == "supabase"
            and storage.supabase_url
            and storage.supabase_service_key
            and storage.supabase_bucket
        )

    def _get_client(self):
        if not self.enabled:
            return None
        if create_client is None:
            raise RuntimeError("未安装 supabase 依赖，无法启用 Supabase Storage")
        if self._client is not None:
            return self._client

        storage = self.config.storage
        self._client = create_client(storage.supabase_url, storage.supabase_service_key)
        self._bucket_name = storage.supabase_bucket
        try:
            self._client.storage.get_bucket(self._bucket_name)
        except Exception:
            try:
                self._client.storage.create_bucket(self._bucket_name, public=True)
            except Exception:
                pass
        return self._client

    def upload_file(self, local_path: Path, blob_name: str, content_type: Optional[str] = None) -> Optional[str]:
        if not self.enabled:
            return None

        client = self._get_client()
        file_data = local_path.read_bytes()
        options = {}
        if content_type:
            options["content-type"] = content_type
        # 使用传入的 blob_name（假定已由核心层清洗为安全名）
        client.storage.from_(self._bucket_name).upload(
            path=blob_name,
            file=file_data,
            file_options=options,
        )
        return blob_name

    def upload_stream(self, stream: BinaryIO, blob_name: str, content_type: Optional[str] = None) -> Optional[str]:
        if not self.enabled:
            return None

        client = self._get_client()
        file_data = stream.read()
        options = {}
        if content_type:
            options["content-type"] = content_type
        client.storage.from_(self._bucket_name).upload(
            path=blob_name,
            file=file_data,
            file_options=options,
        )
        return blob_name

    def download_to_path(self, blob_name: str, destination: Path) -> Path:
        if not self.enabled:
            raise RuntimeError("Supabase Storage 未启用")

        client = self._get_client()
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = client.storage.from_(self._bucket_name).download(blob_name)
        with destination.open("wb") as handle:
            handle.write(data)
        return destination

    def delete_file(self, blob_name: str) -> bool:
        if not self.enabled:
            return False

        client = self._get_client()
        try:
            client.storage.from_(self._bucket_name).remove([blob_name])
            return True
        except Exception:
            return False

    def get_public_url(self, blob_name: str) -> Optional[str]:
        if not self.enabled:
            return None
        client = self._get_client()
        try:
            return client.storage.from_(self._bucket_name).get_public_url(blob_name)
        except Exception:
            return None


def get_storage_backend(config: Optional[SystemConfig] = None) -> SupabaseStorage:
    return SupabaseStorage(config=config)


def upload_file_to_storage(
    local_path: str | Path,
    config: Optional[SystemConfig] = None,
    blob_name: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Optional[str]:
    path_obj = Path(local_path)
    storage = get_storage_backend(config)
    if not storage.enabled:
        return None
    resolved_blob_name = blob_name or path_obj.name
    return storage.upload_file(path_obj, resolved_blob_name, content_type=content_type)


def upload_stream_to_storage(
    stream: BinaryIO,
    config: Optional[SystemConfig] = None,
    blob_name: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Optional[str]:
    storage = get_storage_backend(config)
    if not storage.enabled:
        return None
    if not blob_name:
        raise ValueError("blob_name 不能为空")
    return storage.upload_stream(stream, blob_name, content_type=content_type)


def download_file_to_local(
    blob_name: str,
    destination: str | Path,
    config: Optional[SystemConfig] = None,
) -> Path:
    storage = get_storage_backend(config)
    return storage.download_to_path(blob_name, Path(destination))


def delete_file_from_storage(blob_name: Optional[str], config: Optional[SystemConfig] = None) -> bool:
    if not blob_name:
        return False
    storage = get_storage_backend(config)
    return storage.delete_file(blob_name)
