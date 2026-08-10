"""Agent 工具目录（OpenAI function-calling schema）。"""
from __future__ import annotations


def build_agent_tools() -> list[dict]:
    """返回 agent 可调用的工具清单（OpenAI tools 格式）。"""
    return [
        {
            "type": "function",
            "function": {
                "name": "search_kb",
                "description": "在企业私有知识库中检索相关文档片段，用于回答基于内部资料的问题。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "kb_id": {"type": "string", "description": "知识库 ID"},
                        "query": {"type": "string", "description": "检索问题"},
                        "top_k": {"type": "integer", "description": "返回片段数", "default": 3},
                    },
                    "required": ["kb_id", "query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "use_skill",
                "description": "调用一个已注册的企业技能（Anthropic Skills 规范），返回该技能的执行指引，由你按指引完成任务。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skill_id": {"type": "string", "description": "技能 ID"},
                        "args": {"type": "object", "description": "技能入参"},
                    },
                    "required": ["skill_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "call_mcp_tool",
                "description": "调用一个已接入的 MCP 工具（如日历、工单、数据库查询等）执行真实动作。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "server_id": {"type": "string", "description": "MCP 服务器 ID"},
                        "tool_name": {"type": "string", "description": "工具名"},
                        "arguments": {"type": "object", "description": "工具入参"},
                    },
                    "required": ["server_id", "tool_name"],
                },
            },
        },
    ]
