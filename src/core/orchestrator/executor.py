"""
任务执行器
负责调用Agent执行具体任务
文档解析由各Agent自行处理（使用外部库如python-docx, pdfplumber等）
"""
from typing import Optional, List, Any, Dict
import importlib
from pathlib import Path
from types import SimpleNamespace

from config import SystemConfig, get_config
from core.storage import build_blob_name, upload_file_to_storage
from utils.logger import get_logger
from core.orchestrator.task_spec import FileInfo, TaskSpec


class TaskExecutor:
    """
    任务执行器
    封装Agent的调用逻辑
    注意：文档解析由各Agent自行处理，不使用统一的解析器
    """

    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or get_config()
        self.logger = get_logger(__name__)
        self._agents = {}
        self._file_cache: Dict[str, Any] = {}  # 缓存已解析的文件内容

    def get_file_content(self, file_info: FileInfo) -> Any:
        """
        获取文件内容
        由各Agent自行实现具体解析逻辑
        """
        if file_info.path in self._file_cache:
            return self._file_cache[file_info.path]

        self.logger.info(f"读取文件: {file_info.name}")
        # 具体解析逻辑由Agent实现，这里只返回文件路径
        return file_info.path

    def cache_file_content(self, file_path: str, content: Any):
        """缓存文件解析结果"""
        self._file_cache[file_path] = content

    def clear_cache(self):
        """清除文件缓存"""
        self._file_cache.clear()

    def parse_documents(self, source_files: List[FileInfo]) -> Dict[str, str]:
        """解析源文档，返回 file_path -> text 映射。"""
        from utils.document_reader import read_document

        parsed_content: Dict[str, str] = {}
        for file_info in source_files:
            if file_info.path in self._file_cache:
                parsed_content[file_info.path] = self._file_cache[file_info.path]
                continue

            content = read_document(file_info.path)
            parsed_content[file_info.path] = content
            self._file_cache[file_info.path] = content

        return parsed_content

    def execute_agent(
        self,
        agent_name: str,
        task_spec: TaskSpec,
        **kwargs
    ) -> Any:
        """
        执行Agent
        agent_name: agent_a, agent_b, agent_c, agent_d, conversation
        """
        agent = self._get_agent(agent_name)
        if not agent:
            self.logger.error(f"Agent不存在: {agent_name}")
            return None

        try:
            return agent.execute(task_spec, **kwargs)
        except Exception as e:
            self.logger.error(f"Agent执行失败 {agent_name}: {str(e)}")
            return None

    def fill_template(
        self,
        data: Any,
        template: FileInfo
    ) -> str:
        """
        填充模板
        将数据填入指定模板
        """
        self.logger.info(f"填充模板: {template.name}")
        payload = getattr(data, "data", {}) if data is not None else {}
        if not isinstance(payload, dict):
            return ""
        entities = payload.get("entities")
        if not isinstance(entities, list) or not entities:
            self.logger.warning("跳过模板填充：缺少 entities 数据")
            return ""

        try:
            from core.agents.agent_d import run_agent_d_fill_from_entities

            fill_result = run_agent_d_fill_from_entities(
                entities=entities,
                template=template.path,
            )
            if not isinstance(fill_result, dict) or not fill_result.get("success"):
                self.logger.warning(f"模板填充失败: {fill_result}")
                return ""
            result_data = fill_result.get("data", {})
            if isinstance(result_data, dict):
                return str(result_data.get("template_output") or "")
            return ""
        except Exception as exc:
            self.logger.error(f"模板填充异常: {exc}")
            return ""

    def execute_workflow_pipeline(self, task_spec: TaskSpec, progress_callback=None) -> Dict[str, Any]:
        """
        统一工作流节点流水线执行（由 coordinator 调用）。
        parameters:
            - workflow_nodes: List[dict]
            - output_config: Dict[str, Any]
            - execution_id: str (optional, for blob prefix)
        """
        source = task_spec.source_files[0] if task_spec.source_files else None
        if not source:
            return {"success": False, "message": "缺少源文件"}

        output_config = task_spec.parameters.get("output_config", {}) or {}
        workflow_nodes = task_spec.parameters.get("workflow_nodes", []) or []
        input_config = task_spec.parameters.get("input_config", {}) or {}
        execution_id = str(task_spec.parameters.get("execution_id") or "workflow")

        output_format = str(output_config.get("outputFormat") or "md").lower()
        if output_format not in ("md", "txt", "pdf"):
            output_format = "md"

        naming_rule = str(output_config.get("namingRule") or "{original_name}_out")
        save_path = str(output_config.get("savePath") or "").strip()
        out_name = naming_rule.replace("{original_name}", Path(source.path).stem)
        ext = f".{output_format}"
        if save_path:
            resolved_save = Path(save_path)
            if not resolved_save.is_absolute():
                resolved_save = Path(self.config.output_dir) / resolved_save
            if resolved_save.suffix:
                out_path = resolved_save
            else:
                if not out_name.endswith(ext):
                    out_name += ext
                out_path = resolved_save / out_name
        else:
            if not out_name.endswith(ext):
                out_name += ext
            out_path = Path(self.config.output_dir) / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)

        skip_existing = bool(input_config.get("skipExisting", False))
        if skip_existing and out_path.exists():
            return {
                "success": True,
                "message": "跳过已存在输出（skipExisting=true）",
                "output_file": str(out_path),
                "output": {
                    "name": out_path.name,
                    "path": str(out_path),
                    "blob_name": None,
                    "size": out_path.stat().st_size,
                    "source": source.name,
                },
            }

        parsed = self.parse_documents([source])
        content = parsed.get(source.path, "")
        if not content:
            return {"success": False, "message": f"无法读取文件内容: {source.name}"}

        processing_nodes = [n for n in workflow_nodes if str(n.get("type", "")).lower() not in ("input", "output")]
        result_content = content
        from api.routers.workflows_processors import _process_node
        for idx, node_dict in enumerate(processing_nodes, 1):
            node = SimpleNamespace(
                type=node_dict.get("type", ""),
                title=node_dict.get("title", ""),
                schemaKey=node_dict.get("schemaKey", ""),
                configValues=node_dict.get("configValues", {}) or {},
            )
            if progress_callback:
                progress_callback(idx, max(len(processing_nodes), 1), f"处理节点: {node.title or node.type}")
            result_content = _process_node(result_content, source.name, node, self.config, {})
            if not result_content:
                return {"success": False, "message": f"节点处理结果为空: {node.title or node.type}"}

        if output_format == "pdf":
            from utils.pdf_generator import text_to_pdf
            text_to_pdf(result_content, str(out_path), title=out_name)
            mime_type = "application/pdf"
        else:
            out_path.write_text(result_content, encoding="utf-8")
            mime_type = "text/markdown; charset=utf-8" if output_format == "md" else "text/plain; charset=utf-8"

        blob_name = None
        if self.config.storage.enabled and self.config.storage.provider == "azure_blob":
            try:
                blob_name = upload_file_to_storage(
                    out_path,
                    config=self.config,
                    blob_name=build_blob_name(execution_id, out_path.name, prefix=self.config.storage.azure_blob_prefix or "workflows"),
                    content_type=mime_type,
                )
            except Exception as exc:
                self.logger.warning(f"上传工作流产物到 Blob 失败: {exc}")

        return {
            "success": True,
            "message": "工作流处理完成",
            "output_file": str(out_path),
            "output": {
                "name": out_path.name,
                "path": str(out_path),
                "blob_name": blob_name,
                "size": out_path.stat().st_size,
                "source": source.name,
            },
        }

    def _get_parser(self, file_type: str):
        """
        获取对应的解析器
        注意：此方法已废弃，解析逻辑由各Agent自行处理
        """
        self.logger.warning(f"解析器已废弃，请使用各Agent自带的解析功能")
        return None

    def _get_agent(self, agent_name: str):
        """获取对应的Agent"""
        if agent_name in self._agents:
            return self._agents[agent_name]

        agent_map = {
            "agent_a": "core.agents.agent_a.AgentA",
            "agent_b": "core.agents.agent_b.AgentB",
            "agent_c": "core.agents.agent_c.AgentC",
            "agent_d": "core.agents.agent_d.AgentD",
            "conversation": "core.agents.conversation_agent.ConversationAgent",
            "document_understanding": "core.agents.document_understand_agent.DocumentAgent",
        }

        agent_config = agent_map.get(agent_name)
        if not agent_config:
            return None

        try:
            # 分离模块路径和类名
            module_path, class_name = agent_config.rsplit(".", 1)
            if agent_name == "conversation":
                class_name = "ConversationAgent"
            module = importlib.import_module(module_path)
            agent_class = getattr(module, class_name)
            agent = agent_class(self.config)
            self._agents[agent_name] = agent
            return agent
        except Exception as e:
            self.logger.error(f"加载Agent失败 {agent_name}: {str(e)}")
            return None
