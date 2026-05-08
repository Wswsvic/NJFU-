"""
调度器：每分钟扫描一次，触发预约任务
"""
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from . import data
from .bot_runner import execute_reservation

scheduler = BackgroundScheduler()


def scan_and_execute():
    """扫描所有激活计划，执行到时间的预约"""
    from datetime import timedelta
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    
    # 因为在 T 日(今天) 抢 T+1 日(明天) 的座位，所有的规则对比都应基于"明天"
    tomorrow = now + timedelta(days=1)
    target_weekday = str(tomorrow.isoweekday())
    target_date = tomorrow.strftime("%Y-%m-%d")

    # 限定全局唯一放票触发时间：每天的 07:30 准时启动
    # 为了防止因为秒级误差可能导致错过，如果是整点触发工具，直接卡点
    if current_time != "07:30":
        return

    plans = data.get_active_plans()
    for plan in plans:
        is_friday = (target_weekday == "5")

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

        # 向后兼容老数据
        if "begin_time" in plan and "is_full_day" not in plan:
            target_begin = plan["begin_time"]
            target_end = plan["end_time"]

        # 1. 星期/重复规则匹配
        repeat_type = plan.get("repeat_type", "custom")
        if repeat_type == "custom" or ("days_of_week" in plan and "is_full_day" not in plan):
            allowed_days = plan.get("days_of_week", "").split(",")
            if target_weekday not in allowed_days:
                continue
        elif repeat_type == "everyday":
            pass # 每天都触发
        elif repeat_type == "once":
            pass # 单次也会进入下一步触发判断

        # 2. 时间匹配由外层 `current_time != "07:30"` 接管，此处可以废弃旧的 user 时间判定 
        # (因为目标抢的是明天的票，只要匹配了明天的星期和日期要求，就在今天早上统一冲)

        # 3. 日期范围：对比目标将要入座的日期(明天)是否生效
        start = plan.get("start_date")
        end = plan.get("end_date")
        if start and target_date < start:
            continue
        if end and target_date > end:
            continue

        # 4. 去重
        existing = data.get_log_by_plan_and_date(plan["id"], target_date)
        if existing:
            continue

        # 封装运行时所需数据供 bot_runner 使用
        plan_to_run = dict(plan)
        plan_to_run["_target_begin"] = target_begin
        plan_to_run["_target_end"] = target_end

        # 5. 异步执行
        import threading
        t = threading.Thread(target=_run_and_log, args=(plan_to_run, target_date))
        t.start()


def _run_and_log(plan, target_date):
    """执行预约并记录日志"""
    # 如果是"只订一次"模式，触发后即将其置为未激活
    if plan.get("repeat_type") == "once":
        plan["active"] = False
        data.update_plan(plan)

    from .bot_runner import execute_reservation
    success, message = execute_reservation(plan)
    log = {
        "plan_id": plan["id"],
        "user_id": plan["user_id"],
        "target_date": target_date,
        "status": "success" if success else "fail",
        "message": message,
        "created_at": datetime.now().isoformat(),
    }
    data.add_log(log)


def start_scheduler():
    """启动调度器"""
    scheduler.add_job(scan_and_execute, "interval", minutes=1, id="seat_scan")
    scheduler.start()
