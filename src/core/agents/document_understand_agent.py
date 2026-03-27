"""
DocumentAgent - 文档理解 Agent
支持交互式对话和多文件处理
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

from .base_agent import BaseAgent, AgentResponse
from config import SystemConfig
from core.orchestrator.task_spec import TaskSpec, FileInfo
from core.llm.llm_service import LLMService, get_llm_service
from utils.document_reader import read_document


class DocumentAgent(BaseAgent):
    """
    文档理解 Agent
    支持：
    - 交互式多轮对话
    - 多文件处理
    - 自动从用户指令或预设文件中获取文档
    """

    def __init__(self, config: Optional[SystemConfig] = None):
        super().__init__(config)
        self.name = "DocumentAgent"
        self.agent_type = "document_understanding"
        self._llm_service: LLMService = get_llm_service()
        self._messages_history: List[Dict[str, str]] = []
        self._source_files: List[FileInfo] = []
        self._document_contents: Dict[str, str] = {}  # path -> content

        self._system_prompt = """你是一个智能文档助手，擅长分析和总结文档内容。
你有强大的理解能力，可以帮助用户解读各种类型的文档。
请用中文详细分析文档内容，回答用户问题。

重要提示：
1. 文档开头标有"【统计摘要】"的部分包含Excel/CSV表格的自动统计分析结果，你应该首先解读这些统计特征
2. 当文档包含【统计摘要】时，对于数值型列，重点关注：均值、中位数反映整体趋势；标准差和方差反映波动性；分位数反映分布形态；极值可能暗示异常
3. 当文档包含【统计摘要】时，对于文本型列，关注唯一值数量和最常见值的频率分布
4. 善于发现数据中的模式、异常和潜在问题
"""

    def execute(self, task_spec: TaskSpec, **kwargs) -> AgentResponse:
        """
        执行文档理解任务
        """
        is_valid, error_msg = self.validate_input(task_spec)
        if not is_valid:
            return AgentResponse(success=False, message=error_msg)

        try:
            # 获取 max_rows 参数（如果有）
            max_rows = kwargs.get('max_rows', 100)

            # 设置源文件
            if task_spec.source_files:
                self._source_files = task_spec.source_files
                self._load_documents(max_rows=max_rows)

            # 处理指令
            instruction = task_spec.instruction or ""

            # 如果有指令，处理一次对话
            if instruction:
                response = self._process_query(instruction)
                return AgentResponse(
                    success=True,
                    message="文档理解完成",
                    data={"response": response}
                )

            # 无指令时返回就绪状态
            return AgentResponse(
                success=True,
                message="文档理解 Agent 已就绪",
                data={"status": "ready", "files": [f.name for f in self._source_files]}
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"处理失败: {str(e)}"
            )

    def _load_documents(self, max_rows: int = 100):
        """加载所有文档内容

        :param max_rows: Excel 文件最大读取行数
        """
        for file_info in self._source_files:
            if file_info.path not in self._document_contents:
                try:
                    # 根据文件类型传递 max_rows 参数
                    ext = Path(file_info.path).suffix.lower()
                    if ext in ['.xlsx', '.xls']:
                        content = read_document(file_info.path, max_rows=max_rows)
                    else:
                        content = read_document(file_info.path)
                    self._document_contents[file_info.path] = content
                except Exception as e:
                    self._document_contents[file_info.path] = f"[错误] {str(e)}"

    def validate_input(self, task_spec: TaskSpec) -> tuple[bool, str]:
        """验证输入"""
        # 文档理解模式可以没有文件（用户可能通过指令提供）
        return True, ""

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self._system_prompt

    def set_documents(self, files: List[FileInfo], max_rows: int = 100):
        """设置要处理的文档列表

        :param files: 文件信息列表
        :param max_rows: Excel 文件最大读取行数
        """
        self._source_files = files
        self._load_documents(max_rows=max_rows)

    def set_document(self, file_path: str, max_rows: int = 100):
        """设置单个文档（兼容旧接口）

        :param file_path: 文件路径
        :param max_rows: Excel 文件最大读取行数
        """
        from core.orchestrator.task_spec import FileType

        ext = Path(file_path).suffix.lower().lstrip('.')
        file_type = FileType(ext) if ext in [e.value for e in FileType] else FileType.TXT

        file_info = FileInfo(
            path=file_path,
            file_type=file_type,
            name=Path(file_path).name
        )
        self._source_files = [file_info]
        self._load_documents(max_rows=max_rows)

    def get_document_content(self, file_path: Optional[str] = None) -> Optional[str]:
        """获取文档内容"""
        if file_path:
            return self._document_contents.get(file_path)
        if self._source_files:
            return self._document_contents.get(self._source_files[0].path)
        return None

    def get_excel_statistics(self, file_path: Optional[str] = None, max_rows: int = 10000) -> Dict[str, Any]:
        """
        获取Excel文件的统计信息（不含原始数据）

        对于大文件，使用此方法可以避免超出LLM上下文限制

        :param file_path: Excel文件路径，如果为None则使用第一个源文件
        :param max_rows: 最大分析行数
        :return: 统计信息字典
        """
        from utils.document_reader import get_excel_statistics as get_stats

        target_path = file_path or (self._source_files[0].path if self._source_files else None)
        if not target_path:
            return {"error": "没有指定文件"}

        return get_stats(target_path, max_rows=max_rows)

    def get_all_documents_summary(self) -> str:
        """获取所有文档的摘要信息"""
        if not self._document_contents:
            return ""

        summary_parts = []
        for file_info in self._source_files:
            content = self._document_contents.get(file_info.path, "")
            summary_parts.append(f"## {file_info.name}\n\n{content[:10000]}")

        return "\n\n---\n\n".join(summary_parts)

    def _extract_file_paths_from_text(self, text: str) -> List[str]:
        """从文本中提取文件路径"""
        paths = []

        # 模式1: 带引号或书名号的完整路径
        patterns = [
            r'["""\']([A-Za-z]:\\[^\n"""\'*?:]+|[/\w]+/[^\n"""\'*?:]+)["""\']',
            r'文件[：:]\s*([^\n\s]+)',
            r'path[：:]\s*([^\n\s]+)',
            r'读取[：:]\s*([^\n\s]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                path = match.strip()
                if os.path.isfile(path):
                    paths.append(path)

        # 模式2: 常见文档扩展名
        common_exts = ['.pdf', '.docx', '.txt', '.md', '.xlsx', '.csv', '.pptx', '.html']
        words = text.replace('\\', '/').split()
        for word in reversed(words):
            for ext in common_exts:
                if word.endswith(ext) and len(word) > 5:
                    clean_path = word.strip('.,;:!?\'"')
                    if os.path.isfile(clean_path) and clean_path not in paths:
                        paths.append(clean_path)

        return paths

    def _build_doc_context(self, file_paths: List[str] = None) -> str:
        """构建文档上下文"""
        if not self._document_contents:
            return ""

        context_parts = []
        paths_to_use = file_paths or [f.path for f in self._source_files]

        for path in paths_to_use:
            if path in self._document_contents:
                file_info = next((f for f in self._source_files if f.path == path), None)
                file_name = file_info.name if file_info else Path(path).name
                content = self._document_contents[path]

                # 截断过长的内容
                max_chars = 15000
                if len(content) > max_chars:
                    content = content[:max_chars] + f"\n\n[文档已截断，完整文档共 {len(content)} 字符]"

                context_parts.append(f"文档 ({file_name}):\n{content}")

        return "\n\n---\n\n".join(context_parts)

    def _process_query(self, query: str) -> str:
        """处理用户查询"""
        # 检查查询中是否包含新的文件路径
        new_file_paths = self._extract_file_paths_from_text(query)

        # 构建消息
        messages = [{"role": "system", "content": self._system_prompt}]
        messages.extend(self._messages_history)

        # 构建文档上下文
        doc_context = self._build_doc_context(new_file_paths)

        if doc_context or new_file_paths:
            # 有文档内容，增强查询
            enhanced_query = query
            if doc_context:
                enhanced_query = f"""请分析以下文档内容并回答用户问题：

{doc_context}

---

用户问题: {query}"""

            messages.append({"role": "user", "content": enhanced_query})
        else:
            # 无文档，普通对话
            messages.append({"role": "user", "content": query})

        # 调用 LLM
        try:
            response = self._llm_service.chat(
                messages=messages,
                model="deepseek-chat",
                temperature=0
            )
        except Exception as e:
            return f"[错误] LLM 调用失败: {str(e)}"

        # 保存对话历史
        self._messages_history.append({"role": "user", "content": query})
        self._messages_history.append({"role": "assistant", "content": response})

        # 清理 markdown（如果需要）
        # response = self._clean_markdown(response)

        return response

    def chat(self, user_input: str) -> str:
        """
        交互式对话接口（供 CLI 调用）
        """
        return self._process_query(user_input)

    def clear_history(self):
        """清除对话历史"""
        self._messages_history.clear()

    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self._messages_history.copy()

    def _clean_markdown(self, text: str) -> str:
        """清理 markdown 格式"""
        if '```' in text:
            cleaned = re.sub(r'```[\w]*\n', '', text, flags=re.DOTALL)
            cleaned = re.sub(r'```', '', cleaned, flags=re.DOTALL)
            cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)
            return cleaned
        return text


# 独立的聊天入口（用于直接运行测试）
def create_document_agent(config: Optional[SystemConfig] = None) -> DocumentAgent:
    """创建文档 Agent 实例"""
    return DocumentAgent(config)
