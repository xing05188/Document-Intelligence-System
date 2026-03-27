"""
Agent_C: 数据库Agent（可选）
负责将JSON数据存入数据库
"""
from typing import Any, Dict, Optional
from .base_agent import BaseAgent, AgentResponse
from config import SystemConfig, get_config
from core.orchestrator.task_spec import TaskSpec


class AgentC(BaseAgent):
    """
    Agent_C: 数据库存储

    能力：
    - 将JSON数据存入数据库
    - 支持自动建表
    - 推荐使用PostgreSQL
    """

    def __init__(self, config: Optional[SystemConfig] = None):
        super().__init__(config)
        self.name = "Agent_C"
        self.agent_type = "database"
        self.db_connection = None  # TODO: 由各小组实现数据库连接

    def execute(self, task_spec: TaskSpec, **kwargs) -> AgentResponse:
        """
        执行数据库存储任务
        """
        if not self.config.database.enabled:
            return AgentResponse(
                success=False,
                message="数据库功能未启用"
            )

        try:
            return self._store_to_database(task_spec)
        except Exception as e:
            return AgentResponse(
                success=False,
                message=f"存储失败: {str(e)}"
            )

    def _store_to_database(self, task_spec: TaskSpec) -> AgentResponse:
        """
        存储数据到数据库
        TODO: 由各小组实现具体逻辑
        """
        # TODO: 实现数据库存储逻辑
        return AgentResponse(
            success=True,
            message="数据库存储功能待实现",
            data={"status": "pending_implementation"}
        )

    def validate_input(self, task_spec: TaskSpec) -> tuple[bool, str]:
        """验证输入"""
        if not task_spec.parameters.get("data"):
            return False, "缺少要存储的数据"
        return True, ""

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return get_config().agent.get_prompt(self.agent_type)
