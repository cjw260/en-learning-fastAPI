import hashlib

from fastapi import Request
from redis.exceptions import RedisError

from en_learning.api.dependencies import core_resources
from en_learning.common.config import Settings
from en_learning.common.errors import AppError

RATE_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


async def enforce_tracker_rate_limit(request: Request) -> None:
    settings: Settings = request.app.state.settings
    client_host = request.client.host if request.client else "unknown"
    subject = hashlib.sha256(
        f"{client_host}\0{request.url.path}".encode(),
    ).hexdigest()
    key = f"tracker:rate:{subject}"
    try:
        current = int(
            await core_resources(request).redis.eval(
                RATE_SCRIPT,
                1,
                key,
                settings.tracker_rate_window_seconds,
            )
        )
    except RedisError as exception:
        raise AppError("埋点服务暂时不可用", status_code=503) from exception
    if current > settings.tracker_rate_limit:
        raise AppError("埋点请求过于频繁", status_code=429)
