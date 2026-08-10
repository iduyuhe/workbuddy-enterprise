"""Agent 运行时：LangGraph StateGraph 编排 ReAct 循环。

两种 LLM 后端（同一套图，靠 call_llm 切换）：
- 真实模式（AGENT_ENABLE_MOCK_LLM=false）：call_llm 打 model-gateway /v1/chat（透传 vLLM/SGLang
  的 OpenAI 工具调用），由模型自主决定 search_kb / use_skill / call_mcp_tool。
- Mock 模式（默认，无 GPU 环境）：call_llm 返回确定性规则路由的工具调用，
  用于验证「图编排 + 工具真实执行」全链路。

状态里 messages 始终为 OpenAI 格式 dict 列表，避免在 LangGraph 中混用 LangChain
消息对象带来的序列化复杂度。
"""
from __future__ import annotations

import json
from typing import Annotated, Any, TypedDict

import httpx
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from app.core.config import (
    AGENT_DEFAULT_KB_ID,
    AGENT_DEFAULT_MCP_SERVER_ID,
    AGENT_DEFAULT_MCP_TOOL,
    AGENT_DEFAULT_SKILL_ID,
    AGENT_MAX_STEPS,
    ENABLE_MOCK_LLM,
    MODEL_GATEWAY_URL,
)
from app.services.catalog import build_agent_tools
from app.services.tool_adapters import call_mcp_tool, search_kb, use_skill

TOOLS = build_agent_tools()


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    steps: list
    model: str
    user_id: str
    project_id: str
    http: httpx.AsyncClient


def _msg_role(m) -> str:
    """统一取出消息角色：dict 用 role，LangChain 消息对象用 type（human/ai/tool）。

    归一化 LangChain 的命名：ai->assistant, human->user, tool->tool。
    """
    if isinstance(m, dict):
        r = m.get("role") or ""
    else:
        r = getattr(m, "type", None) or getattr(m, "role", None) or ""
    return {"ai": "assistant", "human": "user", "tool": "tool", "system": "system"}.get(r, r)


def _last_user_text(messages: list) -> str:
    for m in reversed(messages):
        if _msg_role(m) in ("user", "human"):
            c = m.get("content") if isinstance(m, dict) else getattr(m, "content", "")
            return c if isinstance(c, str) else ""
    return ""


# ---------- LLM 节点 ----------
async def llm_node(state: AgentState) -> dict:
    http: httpx.AsyncClient = state["http"]
    if ENABLE_MOCK_LLM:
        ai = mock_llm(state["messages"])
    else:
        ai = await real_llm(http, state["messages"], state["model"])
    return {"messages": [ai], "steps": state["steps"]}


def mock_llm(messages: list) -> dict:
    """确定性规则路由：按关键词选择工具，便于无 GPU 环境验证全链路。

    已存在工具结果时直接作答，避免 mock 在「命中关键词」时无限循环调同一工具。
    """
    if any(_msg_role(m) == "tool" for m in messages):
        # 结合工具返回结果作答（mock 阶段：直接回显工具内容摘要）
        tool_text = ""
        for m in reversed(messages):
            if _msg_role(m) == "tool":
                c = m.get("content") if isinstance(m, dict) else getattr(m, "content", "")
                tool_text = c if isinstance(c, str) else ""
                break
        return {"role": "assistant", "content": f"[mock-agent] 根据工具返回结果：{tool_text[:200]}"}
    text = _last_user_text(messages)
    if any(k in text for k in ("知识库", "检索", "文档", "查询资料", "kb", "知识", "资料")):
        args = {"kb_id": AGENT_DEFAULT_KB_ID or "default-kb", "query": text, "top_k": 3}
        return _ai_with_tool("search_kb", args)
    if any(k in text for k in ("技能", "skill", "流程")):
        args = {"skill_id": AGENT_DEFAULT_SKILL_ID or "default-skill", "args": {}}
        return _ai_with_tool("use_skill", args)
    if any(k in text for k in ("mcp", "工具", "调用", "执行动作")):
        args = {
            "server_id": AGENT_DEFAULT_MCP_SERVER_ID or "default-srv",
            "tool_name": AGENT_DEFAULT_MCP_TOOL or "echo",
            "arguments": {"input": text},
        }
        return _ai_with_tool("call_mcp_tool", args)
    return {"role": "assistant", "content": f"[mock-agent] 已收到：{text}（未匹配到工具，直接作答）"}


def _ai_with_tool(name: str, args: dict) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_" + name,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)},
            }
        ],
    }


async def real_llm(http: httpx.AsyncClient, messages: list, model: str) -> dict:
    """真实 LLM：打 model-gateway（OpenAI 工具调用协议），解析 tool_calls。

    关键：TOOLS schema 里 kb_id / skill_id / server_id 是必填且无默认值，真实 LLM
    无法凭空得知应使用哪个资源。因此在消息头注入 system 提示，把默认资源 ID 与
    可用 MCP 工具名告诉模型，使真实工具调用「开箱即用」。
    """
    system_prompt = (
        "你是一个企业级智能体，可调用 search_kb / use_skill / call_mcp_tool 完成任务。\n"
        f"- search_kb：默认知识库 ID = {AGENT_DEFAULT_KB_ID or 'default-kb'}\n"
        f"- use_skill：默认技能 ID = {AGENT_DEFAULT_SKILL_ID or 'default-skill'}\n"
        f"- call_mcp_tool：默认 MCP 服务器 ID = {AGENT_DEFAULT_MCP_SERVER_ID or 'default-srv'}，"
        f"可用工具名 = {AGENT_DEFAULT_MCP_TOOL or 'echo'}\n"
        "请根据用户意图选择工具，并使用上述默认 ID（除非用户明确指定其他 ID）。"
    )
    oai_messages = [{"role": "system", "content": system_prompt}] + _to_openai(messages)
    payload = {
        "model": model,
        "messages": oai_messages,
        "tools": TOOLS,
        "tool_choice": "auto",
    }
    r = await http.post(f"{MODEL_GATEWAY_URL}/v1/chat", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    msg = data["choices"][0]["message"]
    tcs = msg.get("tool_calls")
    if tcs:
        tool_calls = [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"].get("arguments") or "{}",
                },
            }
            for tc in tcs
        ]
        return {"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls}
    return {"role": "assistant", "content": msg.get("content") or ""}


def _extract_tc(tc: Any) -> tuple[str, str, dict]:
    """统一解析 tool_call（兼容 LangChain ToolCall 对象与多种 dict 形态）。"""
    if isinstance(tc, dict):
        if "function" in tc:
            fn = tc["function"] or {}
            return tc.get("id"), fn.get("name"), json.loads(fn.get("arguments") or "{}")
        return tc.get("id"), tc.get("name"), tc.get("args") or {}
    # LangChain ToolCall / 类似对象
    return getattr(tc, "id", None), getattr(tc, "name", ""), getattr(tc, "args", None) or {}


def _to_openai(messages: list) -> list:
    """把 LangGraph 消息对象或 dict 统一成 OpenAI dict。

    注意：LangGraph 的 add_messages 会把入参 dict 转换成 LangChain 消息对象存进
    state，这些对象没有 .role 属性（只有 .type: human/ai/tool/system）。必须用
    _msg_role() 正确映射 human->user / ai->assistant，否则用户消息会被误标成
    assistant，真实 LLM 看不到用户问题。
    """
    out = []
    for m in messages:
        if isinstance(m, dict):
            out.append(m)
            continue
        role = _msg_role(m)
        if role == "tool":
            out.append({"role": "tool", "tool_call_id": getattr(m, "tool_call_id", ""), "content": getattr(m, "content", "")})
        elif role == "assistant":
            tcs = getattr(m, "tool_calls", None)
            if tcs:
                out.append(
                    {
                        "role": "assistant",
                        "content": getattr(m, "content", None) or "",
                        "tool_calls": [
                            {
                                "id": tc.get("id") if isinstance(tc, dict) else tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.get("name") if isinstance(tc, dict) else tc.name,
                                    "arguments": tc.get("args") if isinstance(tc, dict) else (tc.args or {}),
                                },
                            }
                            for tc in tcs
                        ],
                    }
                )
            else:
                out.append({"role": "assistant", "content": getattr(m, "content", "") or ""})
        else:
            out.append({"role": role, "content": getattr(m, "content", "")})
    return out


# ---------- Tools 节点 ----------
async def tools_node(state: AgentState) -> dict:
    http: httpx.AsyncClient = state["http"]
    last = state["messages"][-1]
    raw_tcs = last.get("tool_calls") if isinstance(last, dict) else getattr(last, "tool_calls", None)
    if not raw_tcs:
        return {"messages": [], "steps": state["steps"]}

    steps = list(state["steps"])
    new_msgs: list[dict] = []
    for tc in raw_tcs:
        tc_id, name, args = _extract_tc(tc)
        step: dict[str, Any] = {"tool": name, "args": args}
        try:
            if name == "search_kb":
                res = await search_kb(http, args["kb_id"], args["query"], args.get("top_k", 3),
                                      state["user_id"], state["project_id"])
            elif name == "use_skill":
                res = await use_skill(http, args["skill_id"], args.get("args"),
                                      state["user_id"], state["project_id"])
            elif name == "call_mcp_tool":
                res = await call_mcp_tool(http, args["server_id"], args["tool_name"], args.get("arguments"),
                                          state["user_id"], state["project_id"])
            else:
                res = {"error": f"unknown tool {name}"}
            step["result"] = res
        except Exception as e:  # 工具失败不中断图，交给 LLM 决定下一步
            step["error"] = str(e)
            res = {"error": str(e)}

        steps.append(step)
        new_msgs.append(
            {"role": "tool", "tool_call_id": tc_id, "content": json.dumps(res, ensure_ascii=False)[:4000]}
        )
    return {"messages": new_msgs, "steps": steps}


def should_continue(state: AgentState) -> str:
    if len(state.get("steps", [])) >= AGENT_MAX_STEPS:
        return END
    last = state["messages"][-1]
    tcs = last.get("tool_calls") if isinstance(last, dict) else getattr(last, "tool_calls", None)
    return "tools" if tcs else END


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("llm", llm_node)
    g.add_node("tools", tools_node)
    g.add_edge("__start__", "llm")
    g.add_conditional_edges("llm", should_continue, {"tools": "tools", END: END})
    g.add_edge("tools", "llm")
    return g.compile()


_GRAPH = build_graph()


async def run_agent(
    messages: list,
    model: str,
    user_id: str,
    project_id: str,
    http: httpx.AsyncClient,
) -> tuple[str, list]:
    """执行 agent，返回 (最终答案文本, 工具调用轨迹)。"""
    state = await _GRAPH.ainvoke(
        {
            "messages": messages,
            "steps": [],
            "model": model,
            "user_id": user_id,
            "project_id": project_id,
            "http": http,
        }
    )
    steps = state.get("steps", [])
    # 取最后一条 assistant 消息（无 tool_calls）作为答案
    answer = ""
    for m in reversed(state["messages"]):
        if _msg_role(m) == "assistant" and not getattr(m, "tool_calls", None):
            c = m.get("content") if isinstance(m, dict) else getattr(m, "content", "")
            answer = c if isinstance(c, str) else ""
            break
    return answer, steps
