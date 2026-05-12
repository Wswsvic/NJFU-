"""
调度器：每天早上 07:30 触发，扫描并执行预约任务
"""
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from . import data
from .bot_runner import execute_reservation

scheduler = BackgroundScheduler()


def scan_and_execute():
    """扫描所有激活计划，执行到时间的预约"""
    now = datetime.now()

    # 在 T 日(今天) 抢 T+1 日(明天) 的座位
    tomorrow = now + timedelta(days=1)
    target_weekday = str(tomorrow.isoweekday())
    target_date = tomorrow.strftime("%Y-%m-%d")

    print(f"[Scheduler] {now.strftime('%Y-%m-%d %H:%M:%S')} — scanning for {target_date} (weekday={target_weekday})")

    plans = data.get_active_plans()
    if not plans:
        print("[Scheduler] No active plans found.")
        return

    for plan in plans:
        is_friday = (target_weekday == "5")

        # 1. 星期/重复规则匹配
        repeat_type = plan.get("repeat_type", "custom")
        if repeat_type == "custom":
            allowed_days = plan.get("days_of_week", "")
            if allowed_days:
                allowed_days = allowed_days.split(",")
                if target_weekday not in allowed_days:
                    continue
        elif repeat_type == "everyday":
            pass
        elif repeat_type == "once":
            pass

        # 2. 日期范围：目标入座日期(明天)是否在有效期内
        start = plan.get("start_date")
        end = plan.get("end_date")
        if start and target_date < start:
            continue
        if end and target_date > end:
            continue

        # 3. 计算目标时间段
        if plan.get("is_full_day", False):
            target_begin = "07:30"
            target_end = "20:00" if is_friday else "22:00"
        else:
            if is_friday:
                target_begin = plan.get("friday_begin_time", plan.get("begin_time", "07:30"))
                target_end = plan.get("friday_end_time", plan.get("end_time", "20:00"))
            else:
                target_begin = plan.get("normal_begin_time", plan.get("begin_time", "07:30"))
                target_end = plan.get("normal_end_time", plan.get("end_time", "22:00"))

        # 向后兼容老数据（无 is_full_day 字段）
        if "begin_time" in plan and "is_full_day" not in plan:
            target_begin = plan["begin_time"]
            target_end = plan["end_time"]

        # 封装运行时参数
        plan_to_run = dict(plan)
        plan_to_run["_target_begin"] = target_begin
        plan_to_run["_target_end"] = target_end

        # 5. 异步执行
        print(f"  [EXEC] Plan #{plan['id']}: room={plan['room_id']}, time={target_begin}~{target_end}")
        import threading
        t = threading.Thread(
            target=_run_and_log,
            args=(plan_to_run, target_date),
            daemon=True,
        )
        t.start()


def _run_and_log(plan: dict, target_date: str):
    """执行预约并记录日志"""
    plan_id = plan["id"]

    # 执行预约
    success, message = execute_reservation(plan)

    # 记录日志
    log = {
        "plan_id": plan_id,
        "user_id": plan["user_id"],
        "target_date": target_date,
        "status": "success" if success else "fail",
        "message": message,
        "created_at": datetime.now().isoformat(),
    }
    data.add_log(log)

    # 只在成功后才停用 "once" 计划
    if success and plan.get("repeat_type") == "once":
        plan["active"] = False
        data.update_plan(plan)
        print(f"  [ONCE] Plan #{plan_id}: deactivated after successful execution.")


def start_scheduler():
    """启动调度器（每天 07:30 触发预约，22:00 归档日志）"""
    scheduler.add_job(
        scan_and_execute,
        CronTrigger(hour=7, minute=30),
        id="seat_scan",
        name="Daily seat reservation scan",
    )

    # 每晚 22:00 压缩 debug/ 中的操作日志，保留最近 3 天
    import os
    from src.bot.operating_logger import OperatingLogger as _OpLog
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _DEBUG_DIR = os.path.join(_BASE_DIR, "debug")

    scheduler.add_job(
        _OpLog.archive_and_cleanup,
        CronTrigger(hour=22, minute=0),
        args=(_DEBUG_DIR,),
        id="log_archive",
        name="Daily operating log archive",
    )

    scheduler.start()
    print("[Scheduler] Started. Will trigger daily at 07:30 and 22:00.")

    # 部署/重启后立即执行一次（方便验证）
    import threading as _threading
    _threading.Thread(target=scan_and_execute, daemon=True).start()

    # 部署/重启后立即执行一次（方便测试）
    print("[Scheduler] Running initial scan immediately for testing...")
    scan_and_execute()
