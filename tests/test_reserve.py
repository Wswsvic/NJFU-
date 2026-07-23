"""
预约功能单元测试 - 使用 devId: 100455369
账户密码从 .env 中读取
"""
import sys
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from src.bot.core import LibraryBot

DEV_ID = 100455369


def main():
    username = os.getenv("LIBRARY_USERNAME")
    password = os.getenv("LIBRARY_PASSWORD")

    if not username or not password:
        print("请先设置 .env 文件中的 LIBRARY_USERNAME 和 LIBRARY_PASSWORD")
        sys.exit(1)

    print("=" * 60)
    print("Reserve 功能单元测试")
    print("=" * 60)
    print(f"  devId: {DEV_ID}")
    print(f"  username: {username}")
    print()

    bot = LibraryBot(
        username=username,
        password_plain=password,
        headless=True,
    )

    try:
        bot.login()
    except Exception as e:
        print(f"登录失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not bot.reserve_manager:
        print("reserve_manager 未初始化")
        sys.exit(1)

    tomorrow = datetime.now() + timedelta(days=1)
    begin_time = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
    end_time = tomorrow.replace(hour=12, minute=0, second=0, microsecond=0)

    print(f"预约时间: {begin_time} ~ {end_time}")
    print(f"预约时间段: {begin_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%H:%M')}")
    print()

    print("执行预约...")
    try:
        result = bot.reserve(DEV_ID, begin_time, end_time)
        print(f"响应: {result}")

        if isinstance(result, dict):
            code = result.get("code")
            if code == 0:
                print(f"预约成功! resvId: {result.get('data', {}).get('resvId', 'N/A')}")
            else:
                print(f"预约失败, code={code}, message={result.get('message', 'N/A')}")
        else:
            print(f"非预期响应类型: {type(result)}")
    except Exception as e:
        print(f"预约异常: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    main()
