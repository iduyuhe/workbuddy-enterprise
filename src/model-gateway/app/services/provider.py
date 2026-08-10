"""Provider abstraction + routing for model-gateway.

Each provider speaks the OpenAI-compatible /v1/chat/completions protocol
(vLLM, SGLang, and most OpenAI-compatible endpoints). Claude is optional.
When a real backend is unreachable and ENABLE_MOCK is on, we fall back to a
built-in mock SSE stream so the MVP loop runs without a GPU.
"""
from __future__ import annotations

import json
import time
import uuid

import httpx

from app.core.config import ENABLE_MOCK, MODEL_CATALOG


class ProviderError(Exception):
    pass


class BaseProvider:
    name: str = "base"

    async def chat_stream(self, payload: dict) -> "AsyncGenerator[str, None]":
        raise NotImplementedError

    async def chat(self, payload: dict) -> dict:
        raise NotImplementedError


class OpenAICompatibleProvider(BaseProvider):
    def __init__(self, name: str, base_url: str, api_key: str | None = None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def _post(self, payload: dict, stream: bool) -> httpx.Response:
        headers = {"Content-Type": "application/json"}
        # BYOK：外部端点需要鉴权；本地 vLLM/SGLang 通常不需要（api_key=None 时省略）。
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        # trust_env=False so localhost/vLLM endpoints are not routed through a system proxy.
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0), trust_env=False) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                params={"stream": "true"} if stream else None,
            )
            resp.raise_for_status()
            return resp

    async def chat_stream(self, payload: dict):
        try:
            resp = await self._post(dict(payload, stream=True), stream=True)
            async for chunk in resp.aiter_text():
                yield chunk
        except (httpx.HTTPError, ProviderError) as e:
            if ENABLE_MOCK:
                async for c in mock_stream(payload, cause=str(e)):
                    yield c
            else:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    async def chat(self, payload: dict) -> dict:
        # 真实云端 LLM 偶发 5xx（服务端限流/瞬时过载）或网络抖动：指数退避重试吸收，
        # 仍失败才抛错（绝不再静默回退 mock，避免「假成功」）。仅在「未配置任何真实
        # 后端」的纯本地 dev 场景才回退 mock（ENABLE_MOCK 且本地 localhost 不可达）。
        import asyncio

        last_err: Exception | None = None
        for attempt in range(5):
            try:
                resp = await self._post(dict(payload, stream=False), stream=False)
                return resp.json()
            except httpx.HTTPStatusError as e:
                last_err = ProviderError(
                    f"{self.name} backend returned {e.response.status_code}: {e.response.text[:300]}"
                )
                if attempt < 4:
                    await asyncio.sleep(2.0 * (attempt + 1))  # 2s,4s,6s,8s 退避
                    continue
                break
            except httpx.HTTPError as e:
                last_err = e
                if attempt < 4:
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                break
        # 重试用尽：仅纯本地 dev（localhost + 无 api_key + ENABLE_MOCK）回退 mock
        if ENABLE_MOCK and not self.api_key and "localhost" in self.base_url:
            return mock_chat(payload, cause=str(last_err))
        if isinstance(last_err, ProviderError):
            raise last_err
        if last_err is not None:
            raise ProviderError(str(last_err)) from last_err
        raise ProviderError("unknown error in chat")


class ClaudeProvider(BaseProvider):
    """Optional Claude backend (Bedrock / API). TODO: full adapter."""

    name = "claude"

    async def chat_stream(self, payload: dict):
        # TODO: implement Claude Messages API streaming adapter.
        async for c in mock_stream(payload, cause="claude provider not configured (TODO)"):
            yield c

    async def chat(self, payload: dict) -> dict:
        return mock_chat(payload, cause="claude provider not configured (TODO)")


# ---------- mock fallback ----------
def _sse(event_dict: dict) -> str:
    return f"data: {json.dumps(event_dict, ensure_ascii=False)}\n\n"


async def mock_stream(payload: dict, cause: str = ""):
    model = payload.get("model", "mock")
    rid = "chatcmpl-" + uuid.uuid4().hex[:12]
    prompt = ""
    for m in payload.get("messages", []):
        if m.get("role") == "user":
            prompt = m.get("content", "")
            break
    words = f"[mock] 未连接真实推理后端({cause})。回显你的问题：{prompt}".split()
    yield _sse({"id": rid, "object": "chat.completion.chunk", "model": model,
                "choices": [{"index": 0, "delta": {"role": "assistant"}}]})
    for w in words:
        yield _sse({"id": rid, "object": "chat.completion.chunk", "model": model,
                    "choices": [{"index": 0, "delta": {"content": w + " "}}]})
    yield _sse({"id": rid, "object": "chat.completion.chunk", "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
    yield _sse({"id": rid, "model": model, "usage": {"prompt_tokens": 0, "completion_tokens": len(words)}})
    yield "data: [DONE]\n\n"


def mock_chat(payload: dict, cause: str = "") -> dict:
    model = payload.get("model", "mock")
    rid = "chatcmpl-" + uuid.uuid4().hex[:12]
    prompt = ""
    for m in payload.get("messages", []):
        if m.get("role") == "user":
            prompt = m.get("content", "")
            break
    text = f"[mock] 未连接真实推理后端({cause})。回显你的问题：{prompt}"
    return {
        "id": rid,
        "object": "chat.completion",
        "model": model,
        "created": int(time.time()),
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": len(text)},
    }


# ---------- router ----------
class Router:
    def __init__(self):
        self.providers: dict[str, BaseProvider] = {}
        self.route_table: dict[str, dict] = {}  # project_id -> {prefer:[], fallback}

    def register(self, provider: BaseProvider):
        self.providers[provider.name] = provider

    def resolve(self, model: str | None) -> BaseProvider:
        # explicit model -> catalog provider
        if model and model in MODEL_CATALOG:
            pname = MODEL_CATALOG[model]["provider"]
            if pname in self.providers:
                return self.providers[pname]
        # prefix heuristic
        if model and model.startswith("qwen"):
            if "vllm" in self.providers:
                return self.providers["vllm"]
        if model and model.startswith("deepseek"):
            # 真实 DeepSeek 端点优先（deepseek-*）；未配置 Key 时退到本地 sglang/vLLM。
            if "deepseek" in self.providers:
                return self.providers["deepseek"]
            if "sglang" in self.providers:
                return self.providers["sglang"]
        if model and "claude" in model:
            if "claude" in self.providers:
                return self.providers["claude"]
        # first enabled / any（末级回退优先 external，保证配置 BYOK 端点时不被本地不可达的 vLLM 抢走）
        if self.providers:
            if "external" in self.providers:
                return self.providers["external"]
            return next(iter(self.providers.values()))
        # absolute fallback
        return ClaudeProvider()


# module-level singleton router
router = Router()


def build_default_providers():
    from app.core.config import (
        CLAUDE_API_BASE,
        DEEPSEEK_API_BASE,
        DEEPSEEK_API_KEY,
        LLM_API_BASE,
        LLM_API_KEY,
        LLM_MODEL,
        VLLM_API_BASE,
    )

    router.register(OpenAICompatibleProvider("vllm", VLLM_API_BASE))
    router.register(OpenAICompatibleProvider("sglang", DEEPSEEK_API_BASE))
    if CLAUDE_API_BASE:
        router.register(OpenAICompatibleProvider("claude", CLAUDE_API_BASE))
    else:
        router.register(ClaudeProvider())
    # 真实 DeepSeek 官方端点：配置 DEEPSEEK_API_KEY 后注册为 "deepseek" provider，
    # deepseek-* 模型名直达真实云端推理（支持 tool_calls）。与 external BYOK 互不冲突。
    if DEEPSEEK_API_KEY:
        router.register(OpenAICompatibleProvider("deepseek", "https://api.deepseek.com/v1", api_key=DEEPSEEK_API_KEY))
        MODEL_CATALOG["deepseek-chat"] = {"provider": "deepseek", "context_window": 64000}
        MODEL_CATALOG["deepseek-reasoner"] = {"provider": "deepseek", "context_window": 64000}
    # 外部通用 BYOK 端点：LLM_API_BASE 配置后注册为 "external" provider，
    # 并把 LLM_MODEL 注入路由表，使 agent 按该模型名命中任意 OpenAI 兼容云端 LLM。
    if LLM_API_BASE:
        router.register(OpenAICompatibleProvider("external", LLM_API_BASE, api_key=LLM_API_KEY or None))
        MODEL_CATALOG[LLM_MODEL] = {"provider": "external", "context_window": 128000}
