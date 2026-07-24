"""
Scheduler 功能测试 - 手动触发 scan_and_execute 执行预约计划
服务器 plans.json 中已有两条 active:true 的 plan，预约明天的座位
"""
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from web.scheduler import scan_and_execute, _executor


def main():
    print("=" * 60)
    print("Scheduler 功能测试 - 手动触发 scan_and_execute")
    print("=" * 60)
    print()

    start_time = datetime.now().isoformat()

    print("[Test] 调用 scan_and_execute() ...")
    scan_and_execute()
    print("[Test] scan_and_execute 返回，等待线程池执行完毕...")
    print()

    _executor.shutdown(wait=True)
    print("[Test] 所有预约任务执行完毕")
    print()

    from web import config
    logs_path = config.LOGS_FILE

    print("=" * 60)
    print(f"执行结果 (仅展示 {start_time} 之后的日志)")
    print("=" * 60)

    if os.path.exists(logs_path):
        with open(logs_path, "r", encoding="utf-8") as f:
            logs = json.load(f)

        new_logs = [l for l in logs if l.get("created_at", "") >= start_time]

        if new_logs:
            for log in new_logs:
                status_icon = "PASS" if log.get("status") == "success" else "FAIL"
                print(f"  [{status_icon}] plan_id={log.get('plan_id')}  "
                      f"user_id={log.get('user_id')}  "
                      f"date={log.get('target_date')}  "
                      f"message={log.get('message')}")
        else:
            print("  (本次执行未产生新日志)")
    else:
        print(f"  日志文件不存在: {logs_path}")

    print()
    print("=" * 60)
    print("测试结束")
    print("=" * 60)


if __name__ == "__main__":
    main()
