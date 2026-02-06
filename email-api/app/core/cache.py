"""Redis cache utilities (optional)."""
from functools import wraps
from typing import Callable, Any
import json
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


def cache_result(ttl: int = 300):
    """Decorator to cache async function results. No-op if Redis unavailable."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from app.core.config import get_settings
            try:
                r = redis.from_url(get_settings().REDIS_URL, decode_responses=True)
            except Exception:
                return await func(*args, **kwargs)
            key_data = {"func": func.__name__, "args": str(args), "kwargs": str(kwargs)}
            cache_key = f"cache:{hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()}"
            try:
                cached = r.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
            result = await func(*args, **kwargs)
            try:
                r.setex(cache_key, ttl, json.dumps(result, default=str))
            except Exception:
                pass
            return result

        return wrapper
    return decorator
