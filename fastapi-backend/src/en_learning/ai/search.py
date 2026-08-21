# ruff: noqa: RUF001

from __future__ import annotations

import re
from typing import Any

import httpx

from en_learning.common.config import Settings
from en_learning.common.errors import AppError

CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class WebSearchClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    def _clean(self, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return CONTROL_CHARACTERS.sub("", value).strip()

    async def context_for(self, query: str) -> str:
        url = self._settings.bocha_search_url
        api_key = self._settings.bocha_api_key
        if url is None or api_key is None:
            raise AppError("联网搜索服务未配置", status_code=503)
        try:
            response = await self._client.post(
                str(url),
                headers={"Authorization": f"Bearer {api_key.get_secret_value()}"},
                json={
                    "query": query,
                    "count": self._settings.ai_search_result_limit,
                    "summary": True,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exception:
            raise AppError("联网搜索服务暂时不可用", status_code=503) from exception

        values: Any = (
            payload.get("data", {}).get("webPages", {}).get("value", [])
            if isinstance(payload, dict)
            else []
        )
        if not isinstance(values, list):
            values = []
        entries: list[str] = []
        for item in values[: self._settings.ai_search_result_limit]:
            if not isinstance(item, dict):
                continue
            entries.append(
                "\n".join(
                    (
                        f"标题：{self._clean(item.get('name'))}",
                        f"链接：{self._clean(item.get('url'))}",
                        f"摘要：{self._clean(item.get('summary'))}",
                        f"网站名称：{self._clean(item.get('siteName'))}",
                    )
                )
            )
        context = "\n\n".join(entries)
        return context[: self._settings.ai_search_context_characters]
