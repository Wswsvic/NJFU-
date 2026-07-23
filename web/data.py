"""
数据层：线程安全的 JSON 文件读写
"""
import json
import threading
from typing import Any, Optional
from . import config

_lock = threading.Lock()


def _read_json_raw(filepath: str, default: list[Any]) -> list[Any]:
    """读取 JSON（不加锁，由调用者持有锁）"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("data is not a list")
            return data
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default


def _write_json_raw(filepath: str, data: list[Any]) -> None:
    """写入 JSON（不加锁，由调用者持有锁）"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_json(filepath: str, default: list[Any]) -> list[Any]:
    """线程安全读取 JSON 文件"""
    with _lock:
        return _read_json_raw(filepath, default)


def _write_json(filepath: str, data: list[Any]) -> None:
    """线程安全写入 JSON 文件"""
    with _lock:
        _write_json_raw(filepath, data)


# ========== 用户操作 ==========


def get_users() -> list[dict]:
    return _read_json(config.USERS_FILE, [])


def save_users(users: list[dict]) -> None:
    _write_json(config.USERS_FILE, users)


def add_user(user: dict) -> dict:
    with _lock:
        users = _read_json_raw(config.USERS_FILE, [])
        user["id"] = max((u["id"] for u in users), default=0) + 1
        users.append(user)
        _write_json_raw(config.USERS_FILE, users)
    return user


def get_user_by_username(username: str) -> Optional[dict]:
    users = get_users()
    for u in users:
        if u["username"] == username:
            return u
    return None


def get_user_by_id(user_id: int) -> Optional[dict]:
    users = get_users()
    for u in users:
        if u["id"] == user_id:
            return u
    return None


def update_user(user: dict) -> bool:
    users = get_users()
    for i, u in enumerate(users):
        if u["id"] == user["id"]:
            users[i] = user
            save_users(users)
            return True
    return False


# ========== 预约计划操作 ==========


def get_plans() -> list[dict]:
    return _read_json(config.PLANS_FILE, [])


def save_plans(plans: list[dict]) -> None:
    _write_json(config.PLANS_FILE, plans)


def add_plan(plan: dict) -> dict:
    with _lock:
        plans = _read_json_raw(config.PLANS_FILE, [])
        plan["id"] = max((p["id"] for p in plans), default=0) + 1
        plans.append(plan)
        _write_json_raw(config.PLANS_FILE, plans)
    return plan


def get_plans_by_user(user_id: int) -> list[dict]:
    return [p for p in get_plans() if p["user_id"] == user_id]


def get_active_plans() -> list[dict]:
    return [p for p in get_plans() if p.get("active", True)]


def update_plan(plan: dict) -> bool:
    """线程安全地更新计划（锁覆盖整个读-改-写）"""
    with _lock:
        plans = _read_json_raw(config.PLANS_FILE, [])
        for i, p in enumerate(plans):
            if p["id"] == plan["id"]:
                plans[i] = plan
                _write_json_raw(config.PLANS_FILE, plans)
                return True
    return False


def delete_plan(plan_id: int) -> bool:
    """线程安全地删除计划（锁覆盖整个读-改-写）"""
    with _lock:
        plans = _read_json_raw(config.PLANS_FILE, [])
        new_plans = [p for p in plans if p["id"] != plan_id]
        if len(new_plans) == len(plans):
            return False
        _write_json_raw(config.PLANS_FILE, new_plans)
    return True


# ========== 执行日志操作 ==========


def get_logs() -> list[dict]:
    return _read_json(config.LOGS_FILE, [])


def save_logs(logs: list[dict]) -> None:
    _write_json(config.LOGS_FILE, logs)


def add_log(log: dict) -> dict:
    """线程安全地追加日志（锁覆盖整个读-改-写周期）"""
    with _lock:
        logs = _read_json_raw(config.LOGS_FILE, [])
        log["id"] = max((l["id"] for l in logs), default=0) + 1
        logs.append(log)
        _write_json_raw(config.LOGS_FILE, logs)
    # 同时追加到 debug/ 文本日志，方便调试
    _append_text_log(log)
    return log


def _append_text_log(log: dict):
    """追加一份易读的文本日志到 debug/operating.log"""
    import os as _os
    try:
        log_dir = _os.path.dirname(config.LOGS_FILE)
        txt_path = _os.path.join(log_dir, "operating.log")
        line = (
            f"[{log.get('created_at', '?')}] "
            f"plan={log.get('plan_id', '?')} "
            f"user={log.get('user_id', '?')} "
            f"date={log.get('target_date', '?')} "
            f"{'✅' if log.get('status') == 'success' else '❌'} "
            f"{log.get('message', '')}\n"
        )
        with open(txt_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass  # 文本日志写入失败不影响主流程


def get_log_by_plan_and_date(plan_id: int, target_date: str) -> Optional[dict]:
    logs = get_logs()
    for l in logs:
        if l["plan_id"] == plan_id and l["target_date"] == target_date:
            return l
    return None
