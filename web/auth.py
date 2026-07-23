"""
用户认证：简单的 uuid token 机制
"""
import uuid
from typing import Optional
from . import data

__all__ = ["create_token", "verify_token"]


def create_token(user_id: int) -> str:
    """为用户创建新的 token 并保存"""
    token = str(uuid.uuid4())
    user = data.get_user_by_id(user_id)
    if user:
        user["token"] = token
        data.update_user(user)
    return token


def verify_token(token: str) -> Optional[dict]:
    """验证 token，返回用户对象或 None"""
    if not token:
        return None
    users = data.get_users()
    for u in users:
        if u.get("token") == token:
            return u
    return None
