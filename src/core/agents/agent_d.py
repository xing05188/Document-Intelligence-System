"""
Agent_D: 表格填表Agent
负责从Excel筛选数据并填入表格模板
"""
from typing import Any, Dict, Optional
from .base_agent import BaseAgent, AgentResponse
from config import SystemConfig, get_config
from core.orchestrator.task_spec import TaskSpec


class AgentD(BaseAgent):
    """
    Agent_D: 表格填表

    能力：
    - 根据模板从Excel中筛选数据
    - 将筛选结果填入表格模板
    - 支持Word和Excel表格模板
    """

    def __init__(self, config: Optional[SystemConfig] = None):
        super().__init__(config)
        self.name = "Agent_D"
        self.agent_type = "table"
        self.llm = None  # TODO: 由各小组实现LLM初始化

    def execute(self, task_spec: TaskSpec, **kwargs) -> AgentResponse:
        """
        执行表格填表任务
        """
        # 验证输入
        is_valid, error_msg = self.validate_input(task_spec)
        if not is_valid:
            return AgentResponse(success=False, message=error_msg)

        try:
            return self._fill_table(task_spec)
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"填表失败: {str(e)}"
            )

    def _fill_table(self, task_spec: TaskSpec) -> AgentResponse:
        """
        填表处理
        TODO: 由各小组实现具体逻辑
        """
        # TODO: 实现表格填表逻辑
        return AgentResponse(
            success=True,
            message="表格填表功能待实现",
            data={"status": "pending_implementation"}
        )

    def validate_input(self, task_spec: TaskSpec) -> tuple[bool, str]:
        """验证输入"""
        if not task_spec.source_files:
            return False, "缺少Excel数据源"

        if not task_spec.template_file:
            return False, "缺少表格模板文件"

        return True, ""

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return get_config().agent.get_prompt(self.agent_type)
