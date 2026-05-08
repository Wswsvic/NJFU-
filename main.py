"""
图书馆座位预约系统 - 主入口
=========================
一键登录 → 自动预约 → 推送通知

用法：
    python main.py                 # 今天预约
    python main.py 2026-05-01      # 指定日期
    python main.py --dry-run       # 仅登录测试，不预约
"""
import sys
import os
from datetime import datetime, date, time, timedelta

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # 自动加载 .env
from src.bot.core import LibraryBot
from inform.inform import inform


def parse_date_arg() -> date:
    """解析命令行日期参数，默认今天"""
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        try:
            return datetime.strptime(args[0], "%Y-%m-%d").date()
        except ValueError:
            print(f"❌ 日期格式错误，应为 YYYY-MM-DD: {args[0]}")
            sys.exit(1)
    return date.today()


def is_dry_run() -> bool:
    return "--dry-run" in sys.argv


def time_from_env(key: str, default: str) -> time:
    """从环境变量读取时间，格式 HH:MM"""
    raw = os.getenv(key, default)
    try:
        parts = raw.strip().split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        print(f"❌ 环境变量 {key} 格式错误，应为 HH:MM，当前值: {raw}")
        sys.exit(1)


def main():
    # ========== 1. 读取配置 ==========

    username = os.getenv("LIBRARY_USERNAME")
    password = os.getenv("LIBRARY_PASSWORD")
    headless = os.getenv("HEADLESS", "true").lower() == "true"

    if not username or not password:
        print("❌ 请先设置 .env 文件中的 LIBRARY_USERNAME 和 LIBRARY_PASSWORD")
        sys.exit(1)

    room_id_str = os.getenv("DEFAULT_ROOM_ID")
    seat_name = os.getenv("DEFAULT_SEAT_NAME", "")
    reserve_date = parse_date_arg()
    begin_time = time_from_env("RESERVE_BEGIN_TIME", "08:00")
    end_time = time_from_env("RESERVE_END_TIME", "22:00")

    if not room_id_str:
        print("❌ 请设置 .env 中的 DEFAULT_ROOM_ID")
        sys.exit(1)
    room_id = int(room_id_str)

    # ========== 2. 登录 ==========

    print("=" * 60)
    print(f"  图书馆座位预约系统")
    print(f"  日期: {reserve_date}")
    print(f"  房间: {room_id}")
    print(f"  座位: {seat_name or '自动选择'}")
    print(f"  时间: {begin_time} ~ {end_time}")
    print("=" * 60)

    bot = LibraryBot(
        username=username,
        password_plain=password,
        headless=headless,
    )

    try:
        bot.login()
        print("\n✅ 登录成功！")
        inform("预约系统登录成功", f"日期: {reserve_date}\n座位: {seat_name or '自动'}")
    except Exception as e:
        err_msg = f"登录失败: {e}"
        print(f"\n❌ {err_msg}")
        inform("预约系统登录失败", err_msg)
        sys.exit(1)

    # ========== 3. 预约（非 dry-run） ==========

    if is_dry_run():
        print("\n🔍 仅测试模式（--dry-run），跳过预约")
        bot.print_floor_info()
        return

    dt_begin = datetime.combine(reserve_date, begin_time)
    dt_end = datetime.combine(reserve_date, end_time)

    print(f"\n📋 开始自动预约...")
    print(f"   时间: {dt_begin} ~ {dt_end}")

    try:
        result = bot.reserve_manager.auto_reserve(
            room_id=room_id,
            begin_time=dt_begin,
            end_time=dt_end,
            seat_manager=bot.seat,
            prefer_seat=seat_name if seat_name else None,
        )

        if result and result.get("code") == 0:
            resv_id = result["data"]["resvId"]
            print(f"\n✅ 预约成功！预约编号: {resv_id}")
            inform(
                "座位预约成功",
                f"日期: {reserve_date}\n"
                f"时间: {begin_time} ~ {end_time}\n"
                f"预约编号: {resv_id}",
            )
        else:
            msg = result.get("message", str(result)) if result else "无可用座位"
            print(f"\n❌ 预约失败: {msg}")
            inform("座位预约失败", msg)

    except Exception as e:
        err_msg = f"预约异常: {e}"
        print(f"\n❌ {err_msg}")
        inform("预约系统异常", err_msg)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()