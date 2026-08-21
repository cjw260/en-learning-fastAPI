from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass

import httpx

from en_learning.common.config import Settings


@dataclass(frozen=True, slots=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class LLMUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class LLMChunk:
    reasoning: str = ""
    content: str = ""
    usage: LLMUsage | None = None


class LLMFailure(Exception):
    def __init__(self, kind: str, *, retryable: bool = False) -> None:
        super().__init__(kind)
        self.kind = kind
        self.retryable = retryable


class DeepSeekClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    async def _stream_once(
        self,
        messages: Sequence[LLMMessage],
        *,
        deep_think: bool,
    ) -> AsyncGenerator[LLMChunk]:
        model = (
            self._settings.deepseek_reasoner_model
            if deep_think
            else self._settings.deepseek_chat_model
        )
        payload = {
            "model": model,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
            "temperature": 1.3,
            "max_tokens": 18_000 if deep_think else 4_396,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                if response.status_code != 200:
                    raise LLMFailure(
                        "upstream-status",
                        retryable=response.status_code == 429 or response.status_code >= 500,
                    )
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        event = json.loads(data)
                        choices = event.get("choices", [])
                        delta = choices[0].get("delta", {}) if choices else {}
                        reasoning = delta.get("reasoning_content") or ""
                        content = delta.get("content") or ""
                        raw_usage = event.get("usage")
                    except (
                        AttributeError,
                        IndexError,
                        TypeError,
                        json.JSONDecodeError,
                    ) as exception:
                        raise LLMFailure("upstream-protocol", retryable=False) from exception
                    if not isinstance(reasoning, str) or not isinstance(content, str):
                        raise LLMFailure("upstream-protocol", retryable=False)
                    usage = self._parse_usage(raw_usage)
                    if reasoning or content or usage is not None:
                        yield LLMChunk(reasoning=reasoning, content=content, usage=usage)
        except LLMFailure:
            raise
        except httpx.HTTPError as exception:
            raise LLMFailure("upstream-network", retryable=True) from exception

    @staticmethod
    def _parse_usage(raw_usage: object) -> LLMUsage | None:
        if raw_usage is None:
            return None
        if not isinstance(raw_usage, dict):
            raise LLMFailure("upstream-protocol", retryable=False)

        values: dict[str, int | None] = {}
        for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = raw_usage.get(field)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise LLMFailure("upstream-protocol", retryable=False)
            values[field] = value
        return LLMUsage(**values)

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        deep_think: bool,
    ) -> AsyncGenerator[LLMChunk]:
        attempts = self._settings.llm_max_retries + 1
        for attempt in range(attempts):
            iterator = self._stream_once(messages, deep_think=deep_think)
            emitted = False
            started = asyncio.get_running_loop().time()
            try:
                first_wait = min(
                    self._settings.llm_first_token_timeout_seconds,
                    self._settings.llm_total_timeout_seconds,
                )
                first = await asyncio.wait_for(iterator.__anext__(), timeout=first_wait)
                emitted = True
                yield first
                while True:
                    remaining = self._settings.llm_total_timeout_seconds - (
                        asyncio.get_running_loop().time() - started
                    )
                    if remaining <= 0:
                        raise TimeoutError
                    try:
                        chunk = await asyncio.wait_for(iterator.__anext__(), timeout=remaining)
                    except StopAsyncIteration:
                        return
                    yield chunk
            except StopAsyncIteration:
                failure = LLMFailure("empty-response", retryable=True)
            except TimeoutError as exception:
                failure = LLMFailure(
                    "first-token-timeout" if not emitted else "total-timeout",
                    retryable=not emitted,
                )
                failure.__cause__ = exception
            except LLMFailure as exception:
                failure = exception
            finally:
                await iterator.aclose()

            if emitted or not failure.retryable or attempt + 1 >= attempts:
                raise failure
