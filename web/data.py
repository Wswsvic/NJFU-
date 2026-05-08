"""
数据层：线程安全的 JSON 文件读写
"""
import json
import threading
from typing import Any
from . import config

_lock = threading.Lock()


def _read_json(filepath: str, default: list[Any]) -> list[Any]:
    """安全读取 JSON 文件"""
    with _lock:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    # 文件损坏，重建
                    raise ValueError("data is not a list")
                return data
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
            return default


def _write_json(filepath: str, data: list[Any]) -> None:
    """安全写入 JSON 文件"""
    with _lock:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ========== 用户操作 ==========


def get_users() -> list[dict]:
    return _read_json(config.USERS_FILE, [])


def save_users(users: list[dict]) -> None:
    _write_json(config.USERS_FILE, users)


def add_user(user: dict) -> dict:
    users = get_users()
    user["id"] = max((u["id"] for u in users), default=0) + 1
    users.append(user)
    save_users(users)
    return user


def get_user_by_username(username: str) -> dict | None:
    users = get_users()
    for u in users:
        if u["username"] == username:
            return u
    return None


def get_user_by_id(user_id: int) -> dict | None:
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
    plans = get_plans()
    plan["id"] = max((p["id"] for p in plans), default=0) + 1
    plans.append(plan)
    save_plans(plans)
    return plan


def get_plans_by_user(user_id: int) -> list[dict]:
    return [p for p in get_plans() if p["user_id"] == user_id]


def get_active_plans() -> list[dict]:
    return [p for p in get_plans() if p.get("active", True)]


def update_plan(plan: dict) -> bool:
    plans = get_plans()
    for i, p in enumerate(plans):
        if p["id"] == plan["id"]:
            plans[i] = plan
            save_plans(plans)
            return True
    return False


def delete_plan(plan_id: int) -> bool:
    plans = get_plans()
    new_plans = [p for p in plans if p["id"] != plan_id]
    if len(new_plans) == len(plans):
        return False
    save_plans(new_plans)
    return True


# ========== 执行日志操作 ==========


def get_logs() -> list[dict]:
    return _read_json(config.LOGS_FILE, [])


def save_logs(logs: list[dict]) -> None:
    _write_json(config.LOGS_FILE, logs)


def add_log(log: dict) -> dict:
    logs = get_logs()
    log["id"] = max((l["id"] for l in logs), default=0) + 1
    logs.append(log)
    save_logs(logs)
    return log


def get_log_by_plan_and_date(plan_id: int, target_date: str) -> dict | None:
    logs = get_logs()
    for l in logs:
        if l["plan_id"] == plan_id and l["target_date"] == target_date:
            return l
    return None
