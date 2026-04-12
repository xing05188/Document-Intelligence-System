from __future__ import annotations

from pathlib import Path

import core.agents.agent_d as agent_d_mod


def test_run_agent_d_api_uses_llm_fallback_when_rule_split_fails(monkeypatch):
    captured = {}

    def _rule_fail(prompt: str):
        return []

    def _llm_success(prompt: str):
        return [
            {
                "name": "表一",
                "instruction": "监测时间：2025-11-25 09:00:00.0  城市：德州市",
                "template_sheet_name": "表一",
                "template_header_row": 1,
                "template_start_row": 2,
                "template_table_index": 0,
            },
            {
                "name": "表二",
                "instruction": "监测时间：2025-11-25 09:00:00.0  城市：潍坊市",
                "template_sheet_name": "表二",
                "template_header_row": 1,
                "template_start_row": 2,
                "template_table_index": 1,
            },
        ]

    class _FakeAgentD:
        def execute(self, task_spec):
            captured["task_spec"] = task_spec
            return agent_d_mod.AgentResponse(success=True, message="ok", data={"status": "completed"})

    monkeypatch.setattr(agent_d_mod, "_infer_table_targets_from_prompt", _rule_fail)
    monkeypatch.setattr(agent_d_mod, "_infer_table_targets_from_prompt_with_llm", _llm_success)
    monkeypatch.setattr(agent_d_mod, "AgentD", _FakeAgentD)

    result = agent_d_mod.run_agent_d_api(
        src="tests/data/1.xlsx",
        prompt="请按三个目标场景分别填写，不使用表一/表二这种标题。",
        template="tests/test_d/data2/template.docx",
        output_json="tests/test_d/data3/filtered_rows_data3.json",
        output_template="tests/test_d/data3/filled_template_data3.docx",
        allow_rule_fallback=True,
    )

    assert result["success"] is True
    assert "task_spec" in captured

    parameters = captured["task_spec"].parameters
    assert isinstance(parameters.get("table_targets"), list)
    assert len(parameters["table_targets"]) == 2
    assert parameters["table_targets"][0]["name"] == "表一"
    assert parameters["table_targets"][1]["template_table_index"] == 1

    resolved_input = result.get("resolved_input", {})
    assert Path(resolved_input.get("src", "")).name == "1.xlsx"
