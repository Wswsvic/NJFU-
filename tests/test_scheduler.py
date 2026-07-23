"""
Scheduler 功能测试 - 手动触发 scan_and_execute 执行预约计划
服务器 plans.json 中已有两条 active:true 的 plan，预约明天的座位
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from web.scheduler import scan_and_execute, _executor


def main():
    print("=" * 60)
    print("Scheduler 功能测试 - 手动触发 scan_and_execute")
    print("=" * 60)
    print()

    print("[Test] 调用 scan_and_execute() ...")
    scan_and_execute()
    print("[Test] scan_and_execute 返回，等待线程池执行完毕...")
    print()

    _executor.shutdown(wait=True)
    print("[Test] 所有预约任务执行完毕")
    print()

    print("=" * 60)
    print("执行结果")
    print("=" * 60)

    from web import config
    logs_path = config.LOGS_FILE

    if os.path.exists(logs_path):
        import json
        with open(logs_path, "r", encoding="utf-8") as f:
            logs = json.load(f)

        if logs:
            for log in logs:
                status_icon = "PASS" if log.get("status") == "success" else "FAIL"
                print(f"  [{status_icon}] plan_id={log.get('plan_id')}  "
                      f"user_id={log.get('user_id')}  "
                      f"date={log.get('target_date')}  "
                      f"message={log.get('message')}")
        else:
            print("  (无日志记录)")
    else:
        print(f"  日志文件不存在: {logs_path}")

    print()
    print("=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    main()
