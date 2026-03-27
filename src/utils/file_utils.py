"""
文件处理工具模块
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional
import hashlib


class FileUtils:
    """
    文件处理工具类
    提供常用的文件操作方法
    """

    @staticmethod
    def ensure_dir(path: str) -> Path:
        """
        确保目录存在，不存在则创建

        Args:
            path: 目录路径

        Returns:
            Path: 目录路径对象
        """
        dir_path = Path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        获取文件大小（字节）

        Args:
            file_path: 文件路径

        Returns:
            int: 文件大小
        """
        return Path(file_path).stat().st_size

    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """
        获取文件扩展名

        Args:
            file_path: 文件路径

        Returns:
            str: 扩展名（包含点号）
        """
        return Path(file_path).suffix.lower()

    @staticmethod
    def get_file_name(file_path: str, with_extension: bool = True) -> str:
        """
        获取文件名

        Args:
            file_path: 文件路径
            with_extension: 是否包含扩展名

        Returns:
            str: 文件名
        """
        path = Path(file_path)
        if with_extension:
            return path.name
        return path.stem

    @staticmethod
    def copy_file(src: str, dst: str, overwrite: bool = False) -> bool:
        """
        复制文件

        Args:
            src: 源文件路径
            dst: 目标文件路径
            overwrite: 是否覆盖已存在的文件

        Returns:
            bool: 是否成功
        """
        dst_path = Path(dst)

        if dst_path.exists() and not overwrite:
            return False

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True

    @staticmethod
    def move_file(src: str, dst: str, overwrite: bool = False) -> bool:
        """
        移动文件

        Args:
            src: 源文件路径
            dst: 目标文件路径
            overwrite: 是否覆盖已存在的文件

        Returns:
            bool: 是否成功
        """
        dst_path = Path(dst)

        if dst_path.exists() and not overwrite:
            return False

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
        return True

    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        删除文件

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否成功
        """
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        return False

    @staticmethod
    def list_files(
        directory: str,
        extensions: Optional[List[str]] = None,
        recursive: bool = False
    ) -> List[str]:
        """
        列出目录下的文件

        Args:
            directory: 目录路径
            extensions: 文件扩展名列表（可选）
            recursive: 是否递归搜索子目录

        Returns:
            List[str]: 文件路径列表
        """
        dir_path = Path(directory)
        files = []

        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"

        for item in dir_path.glob(pattern):
            if item.is_file():
                if extensions is None or item.suffix.lower() in extensions:
                    files.append(str(item.absolute()))

        return files

    @staticmethod
    def calculate_md5(file_path: str) -> str:
        """
        计算文件的MD5值

        Args:
            file_path: 文件路径

        Returns:
            str: MD5哈希值
        """
        md5_hash = hashlib.md5()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)

        return md5_hash.hexdigest()

    @staticmethod
    def clean_temp_files(directory: str, extensions: Optional[List[str]] = None):
        """
        清理临时文件

        Args:
            directory: 目录路径
            extensions: 要删除的文件扩展名列表
        """
        files = FileUtils.list_files(directory, extensions=extensions, recursive=True)
        for file_path in files:
            try:
                FileUtils.delete_file(file_path)
            except Exception:
                pass
