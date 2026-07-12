"""
Prometheus 指标定义 & 暴露
========================
用法：
  from src.bot.metrics import mark_login, mark_reservation, start_heartbeat

  # 登录成功/失败
  mark_login("bob", success=True)
  # 预约成功/失败
  mark_reservation("bob", success=False, msg="座位已满")

  # 在应用启动时调用一次
  start_heartbeat(interval=300)  # 每 5 分钟更新心跳
"""
import os
import threading
import time
from prometheus_client import Counter, Gauge, generate_latest, REGISTRY

# ── 指标定义 ─────────────────────────────────────────────
LOGIN_TOTAL = Counter(
    "njfu_seat_login_total",
    "登录尝试总次数",
    ["user_id", "status"],        # status: success | fail
)

RESERVATION_TOTAL = Counter(
    "njfu_seat_reservation_total",
    "预约尝试总次数",
    ["user_id", "status"],        # status: success | fail
)

LAST_SUCCESS_TIMESTAMP = Gauge(
    "njfu_seat_last_success_timestamp",
    "最近一次成功预约的 Unix 时间戳",
    ["user_id"],
)

HEARTBEAT_TIMESTAMP = Gauge(
    "njfu_seat_heartbeat_timestamp",
    "服务心跳时间戳（证明进程存活）",
)

# ── 业务埋点函数 ─────────────────────────────────────────

def mark_login(user_id: str, success: bool):
    """记录登录结果"""
    status = "success" if success else "fail"
    LOGIN_TOTAL.labels(user_id=user_id, status=status).inc()


def mark_reservation(user_id: str, success: bool, msg: str = ""):
    """记录预约结果"""
    status = "success" if success else "fail"
    RESERVATION_TOTAL.labels(user_id=user_id, status=status).inc()
    if success:
        LAST_SUCCESS_TIMESTAMP.labels(user_id=user_id).set_to_current_time()


# ── 心跳 ─────────────────────────────────────────────────

_heartbeat_thread = None


def _heartbeat_loop(interval: int):
    """心跳循环：定期更新心跳时间戳"""
    while True:
        HEARTBEAT_TIMESTAMP.set_to_current_time()
        time.sleep(interval)


def start_heartbeat(interval: int = 300):
    """启动心跳线程（默认 5 分钟更新一次）"""
    global _heartbeat_thread
    if _heartbeat_thread is not None:
        return
    _heartbeat_thread = threading.Thread(
        target=_heartbeat_loop,
        args=(interval,),
        daemon=True,
        name="metrics-heartbeat",
    )
    _heartbeat_thread.start()


# ── /metrics 响应函数 ────────────────────────────────────

def get_metrics() -> bytes:
    """返回 Prometheus 格式的指标数据"""
    return generate_latest(REGISTRY)
