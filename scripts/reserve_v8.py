"""
独立座位预约脚本 - python reserve_v8.py
零项目依赖, 只改 main 底部的账号密码即可使用
"""
import requests, json, time, os
from datetime import datetime, date as date_cls, timedelta
from DrissionPage import ChromiumPage, ChromiumOptions

WEBVPN_BASE = "https://webvpn.njfu.edu.cn"
SEAT_PATH = (
    "/webvpn/LjIwMS4xNjkuMjE4LjE2OC4xNjc=/"
    "LjIwNS4xNTguMjAwLjE3MS4xNTMuMTUwLjIxNi45Ny4yMTEuMTU2LjE1OC4xNzMuMTQ4LjE1NS4xNTUuMjE3LjEwMC4xNTAuMTY1"
)
APP_ACC_NO = 78388
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}


# ==================== 浏览器登录 ====================

def browser_login(username: str, password: str, headless: bool = True):
    co = ChromiumOptions()
    if headless: co.headless(True)
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-gpu")
    co.set_argument("--disable-dev-shm-usage")
    page = ChromiumPage(co)
    try:
        print("  [1] Opening WebVPN portal...")
        page.get(WEBVPN_BASE); time.sleep(2)
        print("  [1] URL: %s" % page.url[:120])
        if "authserver" in page.url:
            print("  [2] CAS login...")
            u = page.ele("#username") or page.ele("@name=username")
            p = page.ele("#password") or page.ele("@name=password")
            if not u or not p:
                time.sleep(2)
                u = page.ele("#username") or page.ele("@name=username")
                p = page.ele("#password") or page.ele("@name=password")
            if not u or not p: print("  [2] Cannot find form!"); return [], None
            u.clear(); u.input(username)
            p.clear(); p.input(password)
            print("  [2] Filled: %s" % username)
            btn = page.ele("#login-submit") or page.ele("tag:button@type=submit")
            btn.click() if btn else p.input("\n")
            for i in range(20):
                time.sleep(1)
                if "authserver" not in page.url:
                    print("  [2] Portal loaded after %ds" % (i + 1)); break
            else: print("  [2] CAS login timeout!"); return [], None
        else: print("  [2] Already past CAS")
        time.sleep(2)
        print("  [2] Current URL: %s" % page.url[:120])
        seat_connect = WEBVPN_BASE + "/rump_frontend/connect/?target=Library&id=12"
        print("  [3] Navigating to seat system...")
        page.get(seat_connect); time.sleep(2)
        print("  [3] URL: %s" % page.url[:120])
        if "rump_frontend" in page.url:
            link = page.ele("#url")
            if link: link.click(); time.sleep(2)
            print("  [3] Clicked redirect, now: %s" % page.url[:120])
        time.sleep(1)
        seat_btn = (
            page.ele(".group-item-img-2")
            or page.ele("tag:span@class=group-item-img group-item-img-2")
            or page.ele("text:座位预约") or page.ele("text:空间预约")
            or page.ele("tag:a@href:seat")
        )
        token = None
        if seat_btn:
            print("  [3] On library page, clicking seat entry...")
            seat_btn.click(); time.sleep(1)
            if page.tabs_count > 1:
                print(f"  [3] Detected {page.tabs_count} tabs, switching...")
                page.get_tab(page.latest_tab).set.activate(); time.sleep(1)
            print("  [3] Clicked seat entry, now: %s" % page.url[:200])
            print("  [3] Waiting for SPA to initialize..."); time.sleep(3)
        print("  [4] Extracting token...")
        userinfo_api = WEBVPN_BASE + SEAT_PATH + "/ic-web/auth/userInfo"
        token = page.run_js(
            "try{var x=new XMLHttpRequest();x.open('GET',arguments[0]+'?vpn-12-libseat.njfu.edu.cn',false);"
            "x.send();if(x.status===200){var d=JSON.parse(x.responseText);"
            "return(d.data&&d.data.token)?d.data.token:null;}}catch(e){}return null;",
            userinfo_api)
        if token: print("  [4] Token: %s..." % str(token)[:20])
        else: print("  [4] WARNING: Could not extract token!")
        return get_cookies(page), token
    finally:
        try: page.quit()
        except Exception as e: print(f"  [WARN] ChromiumPage quit failed: {e}")


def get_cookies(page):
    result = []
    try:
        for c in page.cookies():
            if isinstance(c, dict):
                result.append((c["name"], c["value"], c.get("domain", ".njfu.edu.cn"), c.get("path", "/")))
            else:
                result.append((getattr(c, "name", str(c)), getattr(c, "value", str(c)), ".njfu.edu.cn", "/"))
    except Exception as e: print("  cookies() err: %s" % e)
    try:
        dc = page.run_js("return document.cookie;")
        if dc:
            for part in dc.split(";"):
                part = part.strip()
                if "=" in part:
                    n, v = part.split("=", 1); n = n.strip(); v = v.strip()
                    if not any(x[0] == n for x in result):
                        result.append((n, v, ".njfu.edu.cn", "/"))
    except: pass
    return result


# ==================== API 请求 ====================

class SeatAPI:
    def __init__(self, session: requests.Session):
        self.s = session

    def _get(self, path, params=None):
        url = WEBVPN_BASE + SEAT_PATH + path
        qp = {"vpn-12-libseat.njfu.edu.cn": ""}
        if params: qp.update({str(k): str(v) for k, v in params.items()})
        return self.s.get(url, params=qp).json()

    def _post(self, path, payload):
        url = WEBVPN_BASE + SEAT_PATH + path
        return self.s.post(url, params={"vpn-12-libseat.njfu.edu.cn": ""},
                           json=payload,
                           headers={"Content-Type": "application/json;charset=UTF-8"}).json()

    def get_floor_overview(self):
        r = self._get("/ic-web/seatMenu")
        if r.get("code") == 0: return r["data"]
        raise Exception("seatMenu failed: " + str(r))

    def get_seats_by_room(self, room_id, reserve_date=None):
        if reserve_date is None: reserve_date = datetime.now().strftime("%Y%m%d")
        r = self._get("/ic-web/reserve", {"roomIds": room_id, "resvDates": reserve_date, "sysKind": 8})
        if r.get("code") == 0: return r["data"]
        raise Exception("get_seats failed: " + str(r))

    def get_available_seats(self, room_id, reserve_date=None):
        return [s for s in self.get_seats_by_room(room_id, reserve_date) if s["devStatus"] == 0]

    def reserve(self, dev_id, begin_dt, end_dt):
        bt = int(begin_dt.timestamp() * 1000) if not isinstance(begin_dt, int) else begin_dt
        et = int(end_dt.timestamp() * 1000) if not isinstance(end_dt, int) else end_dt
        return self._post("/ic-web/reserve", {
            "sysKind": 8, "appAccNo": APP_ACC_NO, "memberKind": 1,
            "resvMember": [APP_ACC_NO], "resvBeginTime": bt, "resvEndTime": et,
            "resvDev": [dev_id], "resvProperty": 0,
            "captcha": "", "memo": "", "testName": "",
        })

    def auto_reserve(self, room_id, begin_dt, end_dt, prefer_seat=None):
        print(f"\nAuto-reserve: {begin_dt} ~ {end_dt}")
        date_str = begin_dt.strftime("%Y%m%d")
        available = self.get_available_seats(room_id, date_str)
        if not available: print("No available seats"); return None
        target = None
        if prefer_seat:
            for s in available:
                if prefer_seat in s["devName"]: target = s; break
        if not target: target = available[0]
        print(f"Selected: {target['devName']}")
        r = self.reserve(target["devId"], begin_dt, end_dt)
        if r.get("code") == 0: print(f"Success! ID: {r['data']['resvId']}")
        else: print(f"Failed: {r.get('message', r)}")
        return r


# ==================== 主入口 ====================

if __name__ == "__main__":
    # ---------- 配置区 ----------
    USERNAME    = "your_student_id"   # 学号
    PASSWORD    = "your_password"     # 密码
    ROOM_ID     = 100455346           # 楼层 ID
    PREFER_SEAT = "2F-B094"          # 优先座位 (None=自动选第一个空位)
    HEADLESS    = True
    # ---------------------------

    tomorrow = date_cls.today() + timedelta(days=1)
    begin_dt = datetime.combine(tomorrow, datetime.strptime("07:30", "%H:%M").time())
    end_dt   = datetime.combine(tomorrow, datetime.strptime("22:00", "%H:%M").time())

    print("=" * 60)
    print(f"用户: {USERNAME}  房间: {ROOM_ID}  座位: {PREFER_SEAT or '(自动)'}")
    print(f"时间: {begin_dt} ~ {end_dt}")
    print("=" * 60)

    session = requests.Session(); session.headers.update(HEADERS)
    cookies, token = browser_login(USERNAME, PASSWORD, HEADLESS)
    if not cookies: raise Exception("Browser login failed")
    for n, v, d, p in cookies: session.cookies.set(n, v, domain=d, path=p)
    print(f"  Got {len(cookies)} cookies")
    if token: session.headers["token"] = token; print(f"  Token: {token[:20]}...")
    else: print("  WARNING: no token!")

    api = SeatAPI(session)
    print(f"  Floors OK - {len(api.get_floor_overview())}")
    r = api.auto_reserve(ROOM_ID, begin_dt, end_dt, PREFER_SEAT)
    if r and r.get("code") == 0:
        print(f"\n 预约成功！编号: {r['data']['resvId']}")
    else:
        print(f"\n 预约失败: {r.get('message', '无可用座位') if r else '无可用座位'}")

