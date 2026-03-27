"""
Agent_B: 实体提取Agent
负责从非结构化文档中提取数据为JSON格式
"""
from typing import Any, Dict, Optional
from .base_agent import BaseAgent, AgentResponse
from config import SystemConfig, get_config
from core.orchestrator.task_spec import TaskSpec


class AgentB(BaseAgent):
    """
    Agent_B: 实体提取

    能力：
    - 理解自然语言
    - 根据用户要求和表格模板（可选）
    - 从非结构化数据中提取所需数据为JSON格式
    - 支持格式: word, md, txt
    """

    def __init__(self, config: Optional[SystemConfig] = None):
        super().__init__(config)
        self.name = "Agent_B"
        self.agent_type = "extraction"
        self.llm = None  # TODO: 由各小组实现LLM初始化

    def execute(self, task_spec: TaskSpec, **kwargs) -> AgentResponse:
        """
        执行实体提取任务
        """
        # 验证输入
        is_valid, error_msg = self.validate_input(task_spec)
        if not is_valid:
            return AgentResponse(success=False, message=error_msg)

        try:
            return self._extract_entities(task_spec)
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"提取失败: {str(e)}"
            )

    def _extract_entities(self, task_spec: TaskSpec) -> AgentResponse:
        """
        提取实体数据
        TODO: 由各小组实现具体逻辑
        """
        # TODO: 实现实体提取逻辑
        return AgentResponse(
            success=True,
            message="实体提取功能待实现",
            data={"status": "pending_implementation"}
        )

    def validate_input(self, task_spec: TaskSpec) -> tuple[bool, str]:
        """验证输入"""
        if not task_spec.source_files:
            return False, "缺少源文件"

        # 检查是否有模板文件
        if not task_spec.template_file:
            return False, "实体提取模式需要提供Excel模板文件"

        return True, ""

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return get_config().agent.get_prompt(self.agent_type)
