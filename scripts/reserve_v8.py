import importlib, requests, re, json, base64, random, time
from datetime import datetime
from urllib.parse import quote, unquote, urlencode, urljoin

try:
    AES = importlib.import_module("Crypto.Cipher.AES")
    pad = importlib.import_module("Crypto.Util.Padding").pad
except ModuleNotFoundError:
    AES = importlib.import_module("Cryptodome.Cipher.AES")
    pad = importlib.import_module("Cryptodome.Util.Padding").pad


class LibraryBot:
    CHARS = "ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678"

    def __init__(self, username, password_plain, headless=True):
        self.username = username
        self.password_plain = password_plain
        self.headless = headless
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        })
        self.webvpn_base = "https://webvpn.njfu.edu.cn"
        self.seat_path = "/webvpn/LjIwMS4xNjkuMjE4LjE2OC4xNjc=/LjIwNS4xNTguMjAwLjE3MS4xNTMuMTUwLjIxNi45Ny4yMTEuMTU2LjE1OC4xNzMuMTQ4LjE1NS4xNTUuMjE3LjEwMC4xNTAuMTY1"
        self.app_acc_no = 78388
        self.token = None

    @staticmethod
    def _rds(n):
        return "".join(random.choice(LibraryBot.CHARS) for _ in range(n))

    @staticmethod
    def encrypt_password(plain, salt):
        prefix = LibraryBot._rds(64)
        iv = LibraryBot._rds(16)
        data = (prefix + plain).encode()
        cipher = AES.new(salt.encode(), AES.MODE_CBC, iv.encode())
        ct = cipher.encrypt(pad(data, AES.block_size))
        return base64.b64encode(ct).decode()

    def login(self):
        print("=" * 60)
        print("Login")
        print("=" * 60)
        print("")
        print("[1/2] Browser login (portal approach)...")
        cookies, token = self._browser_login()
        if not cookies:
            raise Exception("Browser login failed")
        for name, value, domain, path in cookies:
            self.session.cookies.set(name, value, domain=domain, path=path)
        print("  Got %d cookies" % len(cookies))
        for name, value, _, _ in cookies:
            print("    %s = %s..." % (name, value[:20]))
        if token:
            self.session.headers["token"] = token
            self.token = token
            print("  Token: %s..." % token[:20])
        else:
            print("  WARNING: no token!")
        print("")
        print("[2/2] Verifying...")
        try:
            result = self.get_floor_overview()
            if result:
                print("  Floors OK - %d" % len(result))
        except Exception as e:
            print("  Floor verify: %s" % e)
        print("")
        print("Done!")
        return True

    # ==================== BROWSER LOGIN ====================

    def _browser_login(self):
        """Login via WebVPN portal, navigate to seat system, extract token."""
        from DrissionPage import ChromiumPage, ChromiumOptions
        co = ChromiumOptions()
        if self.headless:
            co.headless(True)
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-gpu")
        co.set_argument("--disable-dev-shm-usage")
        page = ChromiumPage(co)
        try:
            # Step 1: Go to WebVPN portal
            print("  [1] Opening WebVPN portal...")
            page.get(self.webvpn_base)
            time.sleep(3)
            print("  [1] URL: %s" % page.url[:120])

            # Step 2: CAS login if needed
            if "authserver" in page.url:
                print("  [2] CAS login...")
                uname_el = page.ele("#username") or page.ele("@name=username")
                pwd_el = page.ele("#password") or page.ele("@name=password")
                if not uname_el or not pwd_el:
                    time.sleep(3)
                    uname_el = page.ele("#username") or page.ele("@name=username")
                    pwd_el = page.ele("#password") or page.ele("@name=password")
                if not uname_el or not pwd_el:
                    print("  [2] Cannot find form!")
                    return [], None
                uname_el.clear()
                uname_el.input(self.username)
                pwd_el.clear()
                pwd_el.input(self.password_plain)
                print("  [2] Filled: %s" % self.username)
                btn = page.ele("#login-submit") or page.ele("tag:button@type=submit")
                if btn:
                    btn.click()
                else:
                    pwd_el.input("\n")
                for i in range(20):
                    time.sleep(1)
                    if "authserver" not in page.url:
                        print("  [2] Portal loaded after %ds" % (i + 1))
                        break
                else:
                    print("  [2] CAS login timeout!")
                    return [], None
            else:
                print("  [2] Already past CAS")

            time.sleep(2)
            print("  [2] Current URL: %s" % page.url[:120])

            # Step 3: Navigate to seat system via portal connect URL
            seat_connect = self.webvpn_base + "/rump_frontend/connect/?target=Library&id=12"
            print("  [3] Navigating to seat system...")
            page.get(seat_connect)
            time.sleep(3)
            print("  [3] URL: %s" % page.url[:120])

            # Handle rump_frontend redirect page
            if "rump_frontend" in page.url:
                link = page.ele("#url")
                if link:
                    link.click()
                    time.sleep(3)
                    print("  [3] Clicked redirect, now: %s" % page.url[:120])

            # Step 3.5: Click seat reservation entry on library page
            time.sleep(3)
            if "南京林业大学图书馆" in (page.title or ""):
                print("  [3] On library page, clicking seat entry...")
                seat_btn = (
                        page.ele(".group-item-img-2") or
                        page.ele("tag:span@class=group-item-img group-item-img-2") or
                        page.ele("text:座位预约") or
                        page.ele("text:空间预约") or
                        page.ele("tag:a@href:seat")
                )
                if seat_btn:
                    seat_btn.click()
                    time.sleep(3)
                    print("  [3] Clicked seat entry, now: %s" % page.url[:120])
                else:
                    print("  [3] Cannot find seat entry, dumping spans...")
                    try:
                        spans = page.eles("tag:span")
                        print("  [3] Found %d spans:" % len(spans))
                        for s in spans[:20]:
                            cls = s.attr("class") or ""
                            txt = (s.text or "")[:30]
                            print("  [3]   class='%s' text='%s'" % (cls, txt))
                    except:
                        pass
            else:
                print("  [3] Not on library page, title: %s" % (page.title or ""))

            # Step 4: Wait for token (up to 60 seconds)
            # print("  [4] Waiting for token (up to 60s)...")
            # for i in range(60):
            #     time.sleep(0.1)
            #     token = self._extract_token(page)
            #     if token:
            #         print("  [4] Token found after %ds!" % (i + 1))
            #         time.sleep(1)
            #         cookies = self._get_all_cookies(page)
            #         return cookies, token
            #     if (i + 1) % 10 == 0:
            #         print("  [4] ...(%ds) URL: %s" % (i + 1, page.url[:120]))
            #         try:
            #             print("  [4] ...(%ds) Title: %s" % (i + 1, (page.title or "")[:80]))
            #         except:
            #             pass
            #
            # print("  [4] Token not found after 60s!")

            cookies = self._get_all_cookies(page)
            return cookies, None
        finally:
            try:
                page.quit()
            except:
                pass

    def _extract_token(self, page):
        """Extract token from sessionStorage vuex.userInfo.token."""
        try:
            js = 'try{var v=JSON.parse(sessionStorage.getItem("vuex")||"{}");return (v&&v.userInfo&&v.userInfo.token)?v.userInfo.token:null;}catch(e){return null;}'
            token = page.run_js(js)
            if token and len(str(token)) > 10:
                return str(token)
        except:
            pass
        # Also try direct sessionStorage keys
        try:
            js2 = 'for(var i=0;i<sessionStorage.length;i++){var k=sessionStorage.key(i);if(k.indexOf("token")>=0||k.indexOf("Token")>=0){var v=sessionStorage.getItem(k);if(v&&v.length>10)return v;}}return null;'
            token = page.run_js(js2)
            if token and len(str(token)) > 10:
                return str(token)
        except:
            pass
        return None

    def _get_all_cookies(self, page):
        result = []
        try:
            for c in page.cookies():
                if isinstance(c, dict):
                    result.append((c["name"], c["value"], c.get("domain", ".njfu.edu.cn"), c.get("path", "/")))
                else:
                    result.append((getattr(c, "name", str(c)), getattr(c, "value", str(c)), ".njfu.edu.cn", "/"))
        except Exception as e:
            print("  cookies() err: %s" % e)
        try:
            dc = page.run_js("return document.cookie;")
            if dc:
                for part in dc.split(";"):
                    part = part.strip()
                    if "=" in part:
                        name, value = part.split("=", 1)
                        name = name.strip()
                        value = value.strip()
                        if not any(n == name for n, _, _, _ in result):
                            result.append((name, value, ".njfu.edu.cn", "/"))
        except:
            pass
        return result

    # ==================== API ====================

    def _get(self, path, params=None):
        url = self.webvpn_base + self.seat_path + path
        qp = {"vpn-12-libseat.njfu.edu.cn": ""}
        if params:
            qp.update({str(k): str(v) for k, v in params.items()})
        r = self.session.get(url, params=qp)
        ct = r.headers.get("Content-Type", "")
        if "json" not in ct:
            print("  [WARN] GET %s: %d %s" % (path, r.status_code, ct))
            print("  Body: %s" % r.text[:300])
        return r.json()

    def _post(self, path, payload):
        url = self.webvpn_base + self.seat_path + path
        qp = {"vpn-12-libseat.njfu.edu.cn": ""}
        r = self.session.post(url, params=qp, json=payload,
                              headers={"Content-Type": "application/json;charset=UTF-8"})
        ct = r.headers.get("Content-Type", "")
        if "json" not in ct:
            print("  [WARN] POST %s: %d %s" % (path, r.status_code, ct))
            print("  Body: %s" % r.text[:300])
        return r.json()

    # ==================== BUSINESS ====================

    def get_floor_overview(self):
        result = self._get("/ic-web/seatMenu")
        if isinstance(result, dict) and result.get("code") == 0:
            return result["data"]
        raise Exception("seatMenu failed: " + str(result))

    def print_floor_info(self):
        floors = self.get_floor_overview()
        print("")
        print("Floor Overview:")
        print("-" * 60)
        for f in floors:
            print("")
            print("%s (total:%d, free:%d)" % (f["name"], f["totalCount"], f["remainCount"]))
            for a in f.get("children", []):
                print("  - %s (ID:%d, total:%d, free:%d)" % (a["name"], a["id"], a["totalCount"], a["remainCount"]))

    def get_seats_by_room(self, room_id, reserve_date=None):
        if reserve_date is None:
            reserve_date = datetime.now().strftime("%Y%m%d")
        result = self._get("/ic-web/reserve", {"roomIds": room_id, "resvDates": reserve_date, "sysKind": 8})
        if isinstance(result, dict) and result.get("code") == 0:
            return result["data"]
        raise Exception("get_seats failed: " + str(result))

    def get_available_seats(self, room_id, reserve_date=None):
        return [s for s in self.get_seats_by_room(room_id, reserve_date) if s["devStatus"] == 0]

    def reserve(self, dev_id, begin_time, end_time):
        """begin_time/end_time 接受 datetime 对象或毫秒时间戳"""
        if isinstance(begin_time, int):
            bt = begin_time
        else:
            bt = int(begin_time.timestamp() * 1000)
        if isinstance(end_time, int):
            et = end_time
        else:
            et = int(end_time.timestamp() * 1000)
        payload = {"sysKind": 8, "appAccNo": self.app_acc_no, "memberKind": 1,
                   "resvMember": [self.app_acc_no], "resvBeginTime": bt,
                   "resvEndTime": et, "resvDev": [dev_id], "resvProperty": 0,
                   "captcha": "", "memo": "", "testName": ""}
        return self._post("/ic-web/reserve", payload)

    def auto_reserve(self, room_id, begin_time, end_time, prefer_seat=None):
        print("")
        print("Auto-reserve: %s ~ %s" % (begin_time, end_time))
        available = self.get_available_seats(room_id, begin_time[:10].replace("-", ""))
        if not available:
            print("No available seats")
            return None
        target = None
        if prefer_seat:
            for s in available:
                if prefer_seat in s["devName"]:
                    target = s
                    break
        if not target:
            target = available[0]
        print("Selected: %s" % target["devName"])
        result = self.reserve(target["devId"], begin_time, end_time)
        if isinstance(result, dict) and result.get("code") == 0:
            print("Success! ID: %s" % result["data"]["resvId"])
            return result
        else:
            print("Failed: %s" % result.get("message", result))
            return None


if __name__ == "__main__":
    bot = LibraryBot(username="2310801123", password_plain="njfuXYK264516!", headless=False)
    try:
        bot.login()

        # 1. 三楼夹层 3FA-011
        room_id = 111488386
        dev_id = 111488503
        date_str = "20260429"

        print("\n" + "=" * 60)
        print("查找 3FA-011")
        print("=" * 60)
        seats = bot.get_seats_by_room(room_id, date_str)
        target = None
        for s in seats:
            if "3FA-011" in s["devName"]:
                target = s
                break
        if not target:
            print("未找到 3FA-011!")
            raise Exception("Seat not found")
        print("  名称: %s" % target["devName"])
        print("  ID:   %s" % target["devId"])
        print("  状态: %s" % target["devStatus"])
        print("  营业: %s - %s" % (target["openStart"], target["openEnd"]))
        print("  已约: %s" % target["resvInfo"])

        # 2. 计算时间戳 (毫秒)
        from datetime import datetime
        begin = datetime(2026, 4, 29, 8, 0, 0)
        end = datetime(2026, 4, 29, 22, 0, 0)
        begin_ms = int(begin.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        print("\n  预约时间: %s ~ %s" % (begin, end))
        print("  时间戳:   %d ~ %d" % (begin_ms, end_ms))

        # 3. 尝试预约 (用时间戳)
        print("\n" + "=" * 60)
        print("预约中...")
        print("=" * 60)
        payload = {
            "sysKind": 8,
            "appAccNo": bot.app_acc_no,
            "memberKind": 1,
            "resvMember": [bot.app_acc_no],
            "resvBeginTime": begin_ms,
            "resvEndTime": end_ms,
            "resvDev": [dev_id],
            "resvProperty": 0,
            "captcha": "",
            "memo": "",
            "testName": ""
        }
        print("  payload: %s" % json.dumps(payload, indent=2))
        result = bot._post("/ic-web/reserve", payload)
        print("  结果: %s" % json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        print("Error: %s" % e)
        import traceback
        traceback.print_exc()

