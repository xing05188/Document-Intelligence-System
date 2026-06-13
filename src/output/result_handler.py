"""结果处理器模块"""

import json
from pathlib import Path
from typing import Any, Dict


class ResultHandler:
    """结果处理器，负责保存工作流执行结果"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, data: Any, filename: str) -> str:
        """将数据保存为 JSON 文件

        Args:
            data: 要保存的数据
            filename: 文件名

        Returns:
            保存文件的绝对路径
        """
        file_path = self.output_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        return str(file_path.resolve())