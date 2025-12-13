"""Decorators for role-based checks (placeholders)."""
from functools import wraps


def role_required(role: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Implement role check in real code
            return await func(*args, **kwargs)

        return wrapper

    return decorator
