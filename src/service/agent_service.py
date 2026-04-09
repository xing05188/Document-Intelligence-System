"""Agent 服务层 - 封装现有 Agent 供 API 调用"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from config import SystemConfig, get_config
from core.llm import get_llm_service
from core.orchestrator.coordinator import WorkflowCoordinator
from core.orchestrator.task_spec import TaskSpec, TaskType, FileInfo, FileType
from db.session_repository import get_messages, get_session_files
from langchain_openai import ChatOpenAI


def get_selected_session_files_payload(
    session_id: str, config: SystemConfig
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    从会话存储读取已勾选的数据文件与模板，组装为 Agent 所需的字典列表。
    前端发消息时未带 file_path，须以库中勾选状态为准。
    """
    rows = get_session_files(session_id, config=config)
    data_files: List[Dict[str, Any]] = []
    template_files: List[Dict[str, Any]] = []
    for f in rows:
        if not getattr(f, "is_selected", False):
            continue
        entry = {
            "file_path": f.file_path,
            "file_name": f.file_name,
            "is_selected": True,
        }
        if f.file_type == "data":
            data_files.append(entry)
        elif f.file_type == "template":
            template_files.append(entry)
    return data_files, template_files


class AgentService:
    """Agent 服务封装 - 接入现有 Agent"""

    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or get_config()
        self.coordinator = WorkflowCoordinator(self.config)
        # 文档理解模式需要保持 agent 实例用于多轮对话
        self._document_agents: Dict[str, Any] = {}

    def _get_task_type(self, mode: str) -> TaskType:
        """将前端模式转换为 TaskType"""
        mapping = {
            "default_conversation": TaskType.DEFAULT_CONVERSATION,
            "document_understanding": TaskType.DOCUMENT_UNDERSTANDING,
            "document_editing": TaskType.DOCUMENT_EDITING,
            "entity_extraction": TaskType.ENTITY_EXTRACTION,
            "table_filling": TaskType.TABLE_FILLING,
        }
        return mapping.get(mode, TaskType.DEFAULT_CONVERSATION)

    def _get_file_type(self, file_name: str) -> FileType:
        """根据文件名判断文件类型"""
        ext = file_name.lower().split('.')[-1]
        mapping = {
            'pdf': FileType.PDF,
            'doc': FileType.DOCX,
            'docx': FileType.DOCX,
            'xls': FileType.XLSX,
            'xlsx': FileType.XLSX,
            'txt': FileType.TXT,
            'md': FileType.MD,
        }
        return mapping.get(ext, FileType.TXT)

    def _build_file_info(self, file_dict: Dict[str, Any]) -> FileInfo:
        """将文件字典转换为 FileInfo"""
        return FileInfo(
            path=file_dict.get('file_path', ''),
            file_type=self._get_file_type(file_dict.get('file_name', '')),
        )

    def _build_task_spec(
        self,
        session_id: str,
        mode: str,
        content: str,
        files: List[Dict[str, Any]],
        template_files: Optional[List[Dict[str, Any]]] = None,
    ) -> TaskSpec:
        """构建任务规格"""
        # 获取数据文件
        source_files = [self._build_file_info(f) for f in files if f.get('is_selected', True)]

        # 获取模板文件
        template_file = None
        if template_files:
            selected_templates = [f for f in template_files if f.get('is_selected', True)]
            if selected_templates:
                template_file = self._build_file_info(selected_templates[0])

        return TaskSpec(
            task_type=self._get_task_type(mode),
            instruction=content,
            source_files=source_files,
            template_file=template_file,
            session_id=session_id,
        )

    def _build_conversation_llm_messages(self, session_id: str) -> List[Dict[str, str]]:
        """默认对话：从会话历史构造发给 LLM 的消息列表（含刚写入的用户消息）。"""
        system_prompt = get_config().agent.get_prompt("conversation")
        rows = get_messages(session_id, limit=50, config=self.config)
        msgs: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for r in rows:
            if r.role in ("user", "assistant"):
                msgs.append({"role": r.role, "content": r.content})
        return msgs

    async def _stream_default_conversation(self, session_id: str) -> AsyncGenerator[str, None]:
        """默认对话：真实 LLM 流式输出，保留 Markdown 原文。"""
        llm = get_llm_service()
        if not llm.is_available():
            yield "LLM 服务不可用，请检查 API Key 配置。"
            return

        lc_messages = llm._convert_messages(self._build_conversation_llm_messages(session_id))
        client = ChatOpenAI(
            api_key=llm._get_api_key(),
            base_url=llm._get_base_url(),
            model=llm.config.model,
            temperature=llm.config.temperature,
            max_tokens=llm.config.max_tokens,
            streaming=True,
        )
        def _chunk_to_text(chunk) -> str:
            raw = getattr(chunk, "content", None) or ""
            if isinstance(raw, str):
                return raw
            if isinstance(raw, list):
                parts = []
                for block in raw:
                    if isinstance(block, str):
                        parts.append(block)
                    elif isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                return "".join(parts)
            return str(raw)

        stream_iter = client.stream(lc_messages)
        while True:
            chunk = await asyncio.to_thread(next, stream_iter, None)
            if chunk is None:
                break
            text = _chunk_to_text(chunk)
            if text:
                yield text

    async def chat(
        self,
        session_id: str,
        content: str,
        mode: str = "default_conversation",
        files: Optional[List[Dict[str, Any]]] = None,
        template_files: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        非流式聊天响应
        """
        if not mode or not str(mode).strip():
            mode = "default_conversation"
        else:
            mode = str(mode).strip()

        # 文档理解：协调器只负责挂载文档与创建 Agent，真实答复由 DocumentAgent 生成
        if mode == "document_understanding":
            if session_id in self._document_agents:
                return self._document_agents[session_id].chat(content)
            task_spec = self._build_task_spec(session_id, mode, content, files or [], template_files)
            result = self.coordinator.execute(task_spec)
            if result.interactive_agent:
                agent = result.interactive_agent
                self._document_agents[session_id] = agent
                return agent.chat(content)
            return result.message

        task_spec = self._build_task_spec(session_id, mode, content, files or [], template_files)
        result = self.coordinator.execute(task_spec)
        return result.message

    async def chat_stream(
        self,
        session_id: str,
        content: str,
        mode: str = "default_conversation",
        files: Optional[List[Dict[str, Any]]] = None,
        template_files: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天响应
        文档理解模式支持真正的多轮对话
        """
        if not mode or not str(mode).strip():
            mode = "default_conversation"
        else:
            mode = str(mode).strip()

        # 默认对话：直连 LLM 流式，前端负责 Markdown 渲染
        if mode == "default_conversation":
            async for part in self._stream_default_conversation(session_id):
                yield part
            return

        # 文档理解模式：使用交互式 chat
        if mode == "document_understanding":
            # 检查是否有已保存的 agent 实例
            if session_id in self._document_agents:
                agent = self._document_agents[session_id]
            else:
                # 首次调用，需要先设置文档
                task_spec = self._build_task_spec(session_id, mode, content, files or [], template_files)
                result = self.coordinator.execute(task_spec)
                if result.interactive_agent:
                    agent = result.interactive_agent
                    self._document_agents[session_id] = agent
                else:
                    # 首次对话返回结果
                    for char in result.message:
                        yield char
                    return

            # 多轮对话 - 流式输出
            for part in agent.stream_chat(content):
                yield part
            return

        # 其他模式：模拟流式输出
        task_spec = self._build_task_spec(session_id, mode, content, files or [], template_files)
        result = self.coordinator.execute(task_spec)

        # 简单的字符流模拟
        for char in result.message:
            yield char
            await asyncio.sleep(0.005)

    async def execute_task(
        self,
        session_id: str,
        mode: str,
        content: str,
        files: List[Dict[str, Any]],
        template_files: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        执行 Agent 任务
        """
        task_spec = self._build_task_spec(session_id, mode, content, files, template_files)
        result = self.coordinator.execute(task_spec)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
            "output_file": result.output_file,
        }
