"""
Cookie & Token 存活时间测试
==========================
1. 用 .env 中的 USERNAME / password 通过浏览器登录
2. 登录后导航到座位系统（复用 auth.py 的 token 提取方式：浏览器内 XHR）
3. 同时提取 Cookie 和 Token
4. 之后每隔 N 分钟用 requests 分别探测：
   - seatMenu (仅需 Cookie，public)
   - userInfo (需 Cookie+Token，返回用户信息 = 验证 Token 有效性)

用法:
    python scripts/test_cookie_ttl.py
    python scripts/test_cookie_ttl.py -i 3 -d 30
"""

import os, sys, time, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
    override=True,
)

import requests
from DrissionPage import ChromiumPage, ChromiumOptions

# ==================== 配置（与项目保持一致） ====================
from config.settings import Settings as _S

WEBVPN_BASE = _S.WEBVPN_BASE
SEAT_PATH = _S.SEAT_PATH


def get_credentials():
    username = os.getenv("USERNAME", "")
    password = os.getenv("password", "")
    if not username or not password:
        raise RuntimeError(f"[ERROR] .env 缺少 USERNAME 或 password")
    return username, password


# ==================== 浏览器登录（复用 auth.py 方式） ====================

def browser_login_and_extract(username: str, password: str) -> tuple:
    """
    浏览器登录 + 提取 Cookie + Token
    复用 auth.py 中已验证的 page.run_js() XHR 方式获取 token
    返回: (cookie_dicts, token, app_acc_no)
    """
    print("\n" + "=" * 60)
    print("[浏览器登录]")
    print("=" * 60)

    co = ChromiumOptions()
    co.headless(True)
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-gpu")
    co.set_argument("--disable-dev-shm-usage")
    page = ChromiumPage(co)

    token = None
    app_acc_no = None

    try:
        # ── Step 1: WebVPN ──
        print("  [1] WebVPN portal...")
        page.get(WEBVPN_BASE)
        time.sleep(2)
        print(f"  [1] URL: {page.url[:120]}")

        # ── Step 2: CAS 登录 ──
        if "authserver" in page.url:
            print("  [2] CAS login...")
            u = page.ele("#username") or page.ele("@name=username")
            p = page.ele("#password") or page.ele("@name=password")
            if not u or not p:
                time.sleep(2)
                u = page.ele("#username") or page.ele("@name=username")
                p = page.ele("#password") or page.ele("@name=password")
            if not u or not p:
                raise Exception("找不到登录表单")

            u.clear(); u.input(username)
            p.clear(); p.input(password)
            print(f"  [2] 账号: {username}")

            btn = page.ele("#login-submit") or page.ele("tag:button@type=submit")
            if btn: btn.click()
            else: p.input("\n")

            for i in range(30):
                time.sleep(1)
                if "authserver" not in page.url:
                    print(f"  [2] 登录成功 ({i + 1}s)")
                    break
            else:
                raise Exception("CAS 登录超时(30s)")
        else:
            print("  [2] 已过 CAS")
        time.sleep(2)
        print(f"  [2] URL: {page.url[:120]}")

        # ── Step 3: 导航到座位系统 ──
        seat_connect = WEBVPN_BASE + "/rump_frontend/connect/?target=Library&id=12"
        print("  [3] 跳转座位系统...")
        page.get(seat_connect)
        time.sleep(2)

        if "rump_frontend" in page.url:
            link = page.ele("#url")
            if link:
                link.click()
                time.sleep(2)
                print(f"  [3] 重定向后: {page.url[:120]}")
        time.sleep(1)

        seat_btn = (
            page.ele(".group-item-img-2")
            or page.ele("text:座位预约")
            or page.ele("text:空间预约")
        )

        if seat_btn:
            print("  [3] 点击座位入口...")
            seat_btn.click()
            time.sleep(2)
            if page.tabs_count > 1:
                print(f"  [3] {page.tabs_count} 个标签, 切换到最新...")
                try:
                    page = page.get_tab(page.latest_tab)
                except Exception:
                    pass
                time.sleep(1)
            print(f"  [3] 座位系统: {page.url[:150]}")
            time.sleep(3)

        # ── Step 4: 提取 token (复用 auth.py 方式: 浏览器内同步 XHR) ──
        print("  [4] 提取 token (浏览器内 XHR)...")
        userinfo_url = WEBVPN_BASE + SEAT_PATH + "/ic-web/auth/userInfo"

        for attempt in range(2):
            print(f"  [4] Attempt {attempt + 1}/2...")
            result = page.run_js('''
                try {
                    var xhr = new XMLHttpRequest();
                    xhr.open("GET", arguments[0] + "?vpn-12-libseat.njfu.edu.cn", false);
                    xhr.send();
                    if (xhr.status === 200) {
                        var data = JSON.parse(xhr.responseText);
                        if (data.data) {
                            var token = data.data.token || null;
                            var accNo = data.data.accNo || data.data.appAccNo || null;
                            return JSON.stringify({token: token, accNo: accNo});
                        }
                    }
                } catch(e) {}
                return null;
            ''', userinfo_url)

            if result:
                try:
                    parsed = json.loads(result)
                    token = parsed.get("token")
                    app_acc_no = parsed.get("accNo")
                except Exception:
                    pass

            if token:
                print(f"  [4] Token: {str(token)[:20]}...")
                print(f"  [4] appAccNo: {app_acc_no}")
                break
            else:
                print(f"  [4] XHR 返回: {repr(result)[:100]}")
                if attempt == 0:
                    print("  [4] 等待 4s 重试...")
                    time.sleep(4)

        if not token:
            print("  [4] ⚠️ 未能提取 token")

        # ── Step 5: 提取 Cookie ──
        print("  [5] 提取 Cookie...")
        cookies_list = []
        for c in page.cookies():
            if isinstance(c, dict):
                cookies_list.append({
                    "name": c["name"], "value": c["value"],
                    "domain": c.get("domain", "."), "path": c.get("path", "/"),
                })
            else:
                cookies_list.append({
                    "name": getattr(c, "name", str(c)),
                    "value": getattr(c, "value", str(c)),
                    "domain": ".njfu.edu.cn", "path": "/",
                })

        print(f"  [5] {len(cookies_list)} 个 Cookie:")
        for c in cookies_list:
            val = c["value"]
            if len(val) > 60:
                val = val[:60] + "..."
            print(f"      {c['name']} = {val}")

        return cookies_list, token, app_acc_no

    finally:
        try: page.quit()
        except Exception: pass


# ==================== API 探测 ====================

def make_session(cookies_list: list[dict], token: str | None) -> requests.Session:
    """构建带 Cookie + Token 的 requests.Session"""
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    })
    for c in cookies_list:
        s.cookies.set(c["name"], c["value"], domain=c["domain"], path=c["path"])
    if token:
        s.headers["token"] = token
    return s


def probe(session: requests.Session, path: str, params: dict | None = None) -> dict:
    """通用 API 探测"""
    url = WEBVPN_BASE + SEAT_PATH + path
    qp = {"vpn-12-libseat.njfu.edu.cn": ""}
    if params:
        qp.update({str(k): str(v) for k, v in params.items()})

    t0 = time.time()
    try:
        r = session.get(url, params=qp, timeout=15)
        elapsed = round(time.time() - t0, 2)
        ct = r.headers.get("Content-Type", "")
        result = {
            "elapsed": elapsed, "status": r.status_code,
            "content_type": ct[:80], "is_json": "json" in ct.lower(),
            "body_preview": r.text[:300],
        }
        if result["is_json"]:
            try:
                data = r.json()
                result.update({
                    "code": data.get("code"), "message": data.get("message", ""),
                    "alive": data.get("code") == 0,
                })
            except Exception:
                result["alive"] = False
        else:
            result["alive"] = False
        return result
    except Exception as e:
        return {"elapsed": round(time.time() - t0, 2), "status": -1,
                "error": str(e)[:100], "alive": False}


# ==================== 主流程 ====================

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Cookie & Token 存活时间测试")
    ap.add_argument("-i", "--interval", type=int, default=5,
                    help="探测间隔(分钟), 默认5")
    ap.add_argument("-d", "--duration", type=int, default=0,
                    help="总时长(分钟), 0=跑到失效为止, 默认0")
    args = ap.parse_args()

    run_forever = (args.duration == 0)

    username, password = get_credentials()
    login_start = datetime.now()

    # ===== 阶段1: 浏览器登录 =====
    cookies, token, app_acc_no = browser_login_and_extract(username, password)
    if not cookies:
        print("\n[ERROR] 无 Cookie")
        return

    session = make_session(cookies, token)
    interval_s = args.interval * 60

    print("\n" + "=" * 60)
    print(f"Cookie & Token 存活探测开始")
    label = "跑到失效" if run_forever else f"最多 {args.duration} min"
    print(f"间隔: {args.interval} min | {label}")
    print(f"Token: {'有' if token else '无'} | appAccNo: {app_acc_no}")
    print(f"起始: {login_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    HEADER = f"{'#':>5} {'时间':>22} {'已过':>10} {'Cookie':>8} {'Token':>8}"
    print(f"\n{HEADER}")
    print("-" * 65)

    probe_count = 0
    while True:
        now = datetime.now()
        elapsed_min = round((now - login_start).total_seconds() / 60, 1)
        probe_count += 1

        r1 = probe(session, "/ic-web/seatMenu")           # Cookie 验证
        r2 = probe(session, "/ic-web/auth/userInfo")      # Token 验证

        def icon(r):
            if r["alive"]: return "✅"
            if r.get("code") == 300: return "🔐"
            if r.get("status") == -1: return "❌"
            return "❓"

        print(
            f"{probe_count:>5}  {now.strftime('%Y-%m-%d %H:%M:%S'):>22}  "
            f"{elapsed_min:>6}min  {icon(r1):>6}   {icon(r2):>6}"
        )

        cookie_dead = not r1["alive"]
        token_dead = not r2["alive"]

        if cookie_dead or token_dead:
            print(f"\n{'='*60}")
            if cookie_dead:
                print(f"💀 Cookie 失效 (seatMenu code={r1.get('code')})")
            if token_dead:
                print(f"💀 Token 失效 (userInfo code={r2.get('code')} "
                      f"{r2.get('message','')[:30]})")
            print(f"存活: {elapsed_min} min ({_fmt(elapsed_min)})")
            print(f"起: {login_start.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"止: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"共探测 {probe_count} 次")
            print("=" * 60)
            break

        if not run_forever:
            if (now - login_start).total_seconds() >= args.duration * 60:
                print(f"\n{'='*60}")
                print(f"🎉 {args.duration}min 内均存活！")
                print(f"共探测 {probe_count} 次")
                print("=" * 60)
                break

        if args.interval >= 2:
            progress = f"已过 {elapsed_min}min" + ("" if run_forever else f"/{args.duration}min")
            print(f"  -> 下次: {(now + timedelta(seconds=interval_s)).strftime('%H:%M:%S')}  "
                  f"({progress})")
        time.sleep(interval_s)


def _fmt(minutes: float) -> str:
    h = int(minutes // 60)
    m = round(minutes % 60)
    return f"{h}h{m}min" if h else f"{m}min"


if __name__ == "__main__":
    main()
