import asyncio
import json
from collections.abc import AsyncGenerator

import httpx
import pytest

from en_learning.ai.llm import DeepSeekClient, LLMChunk, LLMFailure, LLMMessage, LLMUsage
from en_learning.ai.service import with_heartbeats
from en_learning.common.config import Settings
from tests.conftest import settings_values


def stream_response(*events: dict[str, object]) -> httpx.Response:
    body = "".join(f"data: {json.dumps(event, ensure_ascii=False)}\n\n" for event in events)
    body += "data: [DONE]\n\n"
    return httpx.Response(200, content=body.encode())


@pytest.mark.asyncio
async def test_deepseek_stream_preserves_reasoning_then_chat_and_model_selection() -> None:
    requests: list[dict[str, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return stream_response(
            {"choices": [{"delta": {"reasoning_content": "分析"}}]},
            {"choices": [{"delta": {"content": "答案"}}]},
            {
                "choices": [],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 2,
                    "total_tokens": 12,
                },
            },
        )

    settings = Settings(_env_file=None, **settings_values())
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://deepseek.invalid",
    ) as client:
        chunks = [
            chunk
            async for chunk in DeepSeekClient(settings, client).stream(
                [LLMMessage(role="human", content="hello")],
                deep_think=True,
            )
        ]

    assert chunks == [
        LLMChunk(reasoning="分析"),
        LLMChunk(content="答案"),
        LLMChunk(usage=LLMUsage(prompt_tokens=10, completion_tokens=2, total_tokens=12)),
    ]
    assert requests[0]["model"] == "deepseek-reasoner"
    assert requests[0]["stream"] is True


@pytest.mark.asyncio
async def test_deepseek_retries_only_before_first_chunk() -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("test failure", request=request)
        return stream_response({"choices": [{"delta": {"content": "ok"}}]})

    settings = Settings(_env_file=None, **settings_values(llm_max_retries=1))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://deepseek.invalid",
    ) as client:
        chunks = [
            chunk
            async for chunk in DeepSeekClient(settings, client).stream(
                [LLMMessage(role="human", content="hello")],
                deep_think=False,
            )
        ]
    assert chunks == [LLMChunk(content="ok")]
    assert attempts == 2


class DelayedStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncGenerator[bytes]:
        await asyncio.sleep(0.1)
        yield b'data: {"choices":[{"delta":{"content":"late"}}]}\n\n'


class PartialThenBrokenStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncGenerator[bytes]:
        yield b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
        raise httpx.ReadError("stream interrupted")


class PartialThenDelayedStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncGenerator[bytes]:
        yield b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
        await asyncio.sleep(0.1)
        yield b'data: {"choices":[{"delta":{"content":"late"}}]}\n\n'


@pytest.mark.asyncio
async def test_first_token_timeout_is_bounded_and_generic() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=DelayedStream())

    settings = Settings(
        _env_file=None,
        **settings_values(
            llm_first_token_timeout_seconds=0.01,
            llm_total_timeout_seconds=0.02,
            llm_max_retries=0,
        ),
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://deepseek.invalid",
    ) as client:
        with pytest.raises(LLMFailure, match="first-token-timeout"):
            _ = [
                chunk
                async for chunk in DeepSeekClient(settings, client).stream(
                    [LLMMessage(role="human", content="hello")],
                    deep_think=False,
                )
            ]


@pytest.mark.asyncio
async def test_failure_after_first_chunk_is_not_retried_or_duplicated() -> None:
    attempts = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(200, stream=PartialThenBrokenStream())

    settings = Settings(_env_file=None, **settings_values(llm_max_retries=3))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://deepseek.invalid",
    ) as client:
        stream = DeepSeekClient(settings, client).stream(
            [LLMMessage(role="human", content="hello")],
            deep_think=False,
        )
        assert await stream.__anext__() == LLMChunk(content="partial")
        with pytest.raises(LLMFailure, match="upstream-network"):
            await stream.__anext__()
    assert attempts == 1


@pytest.mark.asyncio
async def test_total_timeout_after_first_chunk_is_not_retried() -> None:
    attempts = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(200, stream=PartialThenDelayedStream())

    settings = Settings(
        _env_file=None,
        **settings_values(
            llm_first_token_timeout_seconds=0.01,
            llm_total_timeout_seconds=0.02,
            llm_max_retries=3,
        ),
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://deepseek.invalid",
    ) as client:
        stream = DeepSeekClient(settings, client).stream(
            [LLMMessage(role="human", content="hello")],
            deep_think=False,
        )
        assert await stream.__anext__() == LLMChunk(content="partial")
        with pytest.raises(LLMFailure, match="total-timeout"):
            await stream.__anext__()
    assert attempts == 1


@pytest.mark.asyncio
async def test_heartbeat_wrapper_closes_upstream_on_consumer_disconnect() -> None:
    closed = asyncio.Event()

    async def slow_stream() -> AsyncGenerator[LLMChunk]:
        try:
            await asyncio.sleep(10)
            yield LLMChunk(content="never")
        finally:
            closed.set()

    wrapped = with_heartbeats(slow_stream(), heartbeat_seconds=0.01)
    assert await wrapped.__anext__() is None
    await wrapped.aclose()
    assert closed.is_set()
