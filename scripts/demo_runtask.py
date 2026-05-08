import sys
import os
from datetime import datetime, timedelta

# 加入系统路径以正确导入包
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web import data
from web.scheduler import _run_and_log

def run_demo():
    now = datetime.now()
    # 根据我们重构的逻辑，系统实际上是要预约“明天”的票
    tomorrow = now + timedelta(days=1)
    target_weekday = str(tomorrow.isoweekday())
    target_date = tomorrow.strftime("%Y-%m-%d")

    print("==================================================")
    print(f"[*] 立即强制拉起测试跑批程序，忽略 07:30 时间限制...")
    print(f"[*] 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[*] 目标预约日期: {target_date} (星期{target_weekday})")
    print("==================================================\n")

    plans = data.get_active_plans()
    if not plans:
        print("[-] 系统中没有找到激活状态的预约计划。请先在 Web 页面添加一个可用的计划。")
        return

    print(f"[*] 扫描到 {len(plans)} 个激活的计划，准备逐一开始执行验证...\n")

    for plan in plans:
        is_friday = (target_weekday == "5")

        # 重新生成时间边界
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

        # 封装执行参数
        plan_to_run = dict(plan)
        plan_to_run["_target_begin"] = target_begin
        plan_to_run["_target_end"] = target_end

        print(f"[>] 正在尝试执行 计划 ID: {plan['id']} (用户ID: {plan['user_id']})")
        print(f"    - 目标房间: {plan['room_id']}, 目标座位: {plan.get('seat_name', '自动分配空闲座位')}")
        print(f"    - 截取时间: {target_begin} ~ {target_end}")
        
        # 阻塞执行并记录日志，方便在控制台直接看结果
        _run_and_log(plan_to_run, target_date)
        
        # 从本地文件中抽取出刚刚写进去的最新的记录
        logs = data.get_logs()
        sys_log = None
        for l in reversed(logs):
            if l['plan_id'] == plan['id'] and l['target_date'] == target_date:
                sys_log = l
                break
        
        if sys_log:
            if sys_log['status'] == 'success':
                print(f"    [√ 返回状态]: {sys_log['status']}")
            else:
                print(f"    [x 返回状态]: {sys_log['status']}")
            print(f"    [i 返回信息]: {sys_log['message']}\n")
        else:
            print("    [!] 没有找到相关日志，执行过程可能被拦截或异常中断。\n")

    print("[*] 所有可测试的激活计划已执行完毕，测试工具已退出。")

if __name__ == "__main__":
    run_demo()

