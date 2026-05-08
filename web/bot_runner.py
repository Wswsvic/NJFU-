"""
预约执行器：调用 LibraryBot 执行预约任务
"""
import sys
import os
from datetime import datetime, date, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src.bot.core import LibraryBot
from inform.inform import inform
from . import data, config


def execute_reservation(plan: dict) -> tuple:
    """执行单个预约计划

    Returns:
        (success: bool, message: str)
    """
    user = data.get_user_by_id(plan["user_id"])
    if not user:
        return False, "用户不存在"

    try:
        password = config.decrypt_password(user["encrypted_password"])
    except Exception as e:
        return False, f"密码解密失败: {e}"

    room_id = plan["room_id"]
    seat_name = plan.get("seat_name", "")
    begin_time_str = plan.get("_target_begin", plan.get("begin_time", "07:30"))
    end_time_str = plan.get("_target_end", plan.get("end_time", "22:00"))
    from datetime import timedelta
    target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    bot = LibraryBot(
        username=user["username"],
        password_plain=password,
        headless=True,
    )

    try:
        bot.login()
    except Exception as e:
        return False, f"登录失败: {e}"

    try:
        from datetime import timedelta
        # 调度器在 T日 触发，我们要定的是 T+1 日的座位 (明天)
        tomorrow_date_obj = date.today() + timedelta(days=1)
        
        begin_parts = begin_time_str.split(":")
        end_parts = end_time_str.split(":")
        dt_begin = datetime.combine(tomorrow_date_obj, time(int(begin_parts[0]), int(begin_parts[1])))
        dt_end = datetime.combine(tomorrow_date_obj, time(int(end_parts[0]), int(end_parts[1])))

        result = bot.reserve_manager.auto_reserve(
            room_id=room_id,
            begin_time=dt_begin,
            end_time=dt_end,
            seat_manager=bot.seat,
            prefer_seat=seat_name if seat_name else None,
        )

        if result and result.get("code") == 0:
            resv_id = result["data"]["resvId"]
            if user.get("pushplus_token"):
                inform(
                    "座位预约成功",
                    f"日期: {target_date}\n时间: {begin_time_str}~{end_time_str}\n编号: {resv_id}",
                    token=user["pushplus_token"],
                )
            return True, f"预约成功，编号: {resv_id}"
        else:
            msg = result.get("message", str(result)) if result else "无可用座位"
            return False, msg
    except Exception as e:
        return False, str(e)
