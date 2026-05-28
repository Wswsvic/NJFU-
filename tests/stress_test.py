"""
服务器负载压力测试 - 真实 Chromium + CAS 登录
运行方式: python tests/stress_test.py
使用测试账号进行登录和查询，不实际预约。
"""
import sys, os, time, threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ═══════════════════════════════════════════════════════════
# 测试配置 - 改这里
# ═══════════════════════════════════════════════════════════
TEST_USERNAME = ""    # 测试账号
TEST_PASSWORD = ""
TEST_ROOM_ID  = 100455346              # 随便一个房间
PLAN_COUNT    = 20                     # 模拟 plan 数量
MAX_WORKERS   = 2                      # 线程池大小
HEADLESS      = True
# ═══════════════════════════════════════════════════════════

_results = []
_lock = threading.Lock()


def one_full_cycle(plan_id: int) -> tuple:
    """完整一次预约流程：Chromium 登录 + API 查询（不提交预约）"""
    import requests
    from DrissionPage import ChromiumPage, ChromiumOptions

    tag = f"Plan#{plan_id}"
    start = time.time()

    try:
        # ── Chromium 登录 ──
        co = ChromiumOptions()
        if HEADLESS: co.headless(True)
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-gpu")
        co.set_argument("--disable-dev-shm-usage")
        page = ChromiumPage(co)

        page.get("https://webvpn.njfu.edu.cn"); time.sleep(2)

        if "authserver" in page.url:
            u = page.ele("#username") or page.ele("@name=username")
            p = page.ele("#password") or page.ele("@name=password")
            if not u or not p: time.sleep(2)
            u.clear(); u.input(TEST_USERNAME)
            p.clear(); p.input(TEST_PASSWORD)
            btn = page.ele("#login-submit") or page.ele("tag:button@type=submit")
            btn.click() if btn else p.input("\n")
            for _ in range(20):
                time.sleep(1)
                if "authserver" not in page.url: break

        login_ok = "authserver" not in page.url
        page.quit()

        if not login_ok:
            elapsed = time.time() - start
            with _lock: print(f"  [{tag}] LOGIN FAIL ({elapsed:.1f}s)")
            return (False, elapsed, "login_fail")

        # ── API 查询（模拟 seats 查询，不实际预约）──
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
        })
        # 简单测试：请求一个公开页面看是否可达
        seat_url = (
            "https://webvpn.njfu.edu.cn"
            "/webvpn/LjIwMS4xNjkuMjE4LjE2OC4xNjc=/"
            "LjIwNS4xNTguMjAwLjE3MS4xNTMuMTUwLjIxNi45Ny4yMTEuMTU2LjE1OC4xNzMuMTQ4LjE1NS4xNTUuMjE3LjEwMC4xNTAuMTY1"
        )
        r = session.get(seat_url, timeout=10)
        api_ok = r.status_code == 200

        elapsed = time.time() - start
        status = "OK" if api_ok else "API_FAIL"
        with _lock: print(f"  [{tag}] {status} ({elapsed:.1f}s)")
        return (api_ok, elapsed, status)

    except Exception as e:
        elapsed = time.time() - start
        with _lock: print(f"  [{tag}] ERROR: {str(e)[:60]} ({elapsed:.1f}s)")
        return (False, elapsed, str(e)[:30])


def run_stress_test():
    print(f"\n{'='*60}")
    print(f"  服务器负载测试: {PLAN_COUNT} plans, {MAX_WORKERS} workers")
    print(f"  账号: {TEST_USERNAME}  房间: {TEST_ROOM_ID}")
    print(f"  Headless: {HEADLESS}")
    print(f"{'='*60}\n")

    ok, fail = 0, 0
    times = []
    start = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(one_full_cycle, i + 1) for i in range(PLAN_COUNT)]
        for f in futures:
            success, elapsed, _ = f.result()
            times.append(elapsed)
            if success: ok += 1
            else: fail += 1

    total = time.time() - start
    avg = sum(times) / len(times)
    print(f"\n{'='*60}")
    print(f"  结果: {ok} 成功, {fail} 失败")
    print(f"  总耗时: {total:.1f}s ({total/60:.1f} min)")
    print(f"  平均单次: {avg:.1f}s  最快: {min(times):.1f}s  最慢: {max(times):.1f}s")
    print(f"{'='*60}")
    print(f"\n  测试时请在另一终端运行:")
    print(f"    docker stats njfu_seat_reserve")
    print(f"    free -h")


if __name__ == "__main__":
    run_stress_test()
