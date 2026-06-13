import time
from datetime import datetime
from typing import List, Tuple, Optional
from config.settings import Settings


class AuthManager:
    """登录认证管理"""

    def __init__(self, username: str, password_plain: str, headless: bool = True):
        self.username = username
        self.password_plain = password_plain
        self.headless = headless

    def browser_login(self) -> Tuple[List[Tuple[str, str, str, str]], Optional[str]]:
        """通过 WebVPN 门户登录并提取 token"""
        from DrissionPage import ChromiumPage, ChromiumOptions
        import os

        # 获取项目根目录并确保 debug 文件夹存在
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        debug_dir = os.path.join(base_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)
        log_path = os.path.join(debug_dir, "chrome_debug.log")

        co = ChromiumOptions()
        # Linux 容器: 手动指定 Chromium 路径 (DrissionPage 不读 CHROME_BIN 环境变量)
        chrome_bin = os.environ.get("CHROME_BIN", "")
        if chrome_bin and os.path.exists(chrome_bin):
            co.set_browser_path(chrome_bin)
        if self.headless:
            co.headless(True)
        co.set_argument("--no-sandbox")
        co.set_argument("--disable-gpu")
        co.set_argument("--disable-dev-shm-usage")
        co.set_argument("--enable-logging")
        co.set_argument("--v=1")
        co.set_argument(f"--log-path={log_path}")
        page = ChromiumPage(co)

        try:
            # Step 1: 打开 WebVPN 门户
            print("  [1] Opening WebVPN portal...")
            page.get(Settings.WEBVPN_BASE)
            time.sleep(2)
            print("  [1] URL: %s" % page.url[:120])

            # Step 2: CAS 登录
            if "authserver" in page.url:
                print("  [2] CAS login...")
                uname_el = page.ele("#username") or page.ele("@name=username")
                pwd_el = page.ele("#password") or page.ele("@name=password")
                if not uname_el or not pwd_el:
                    time.sleep(2)
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

            # Step 3: 导航到座位系统（通过图书馆页面）
            seat_connect = Settings.WEBVPN_BASE + "/rump_frontend/connect/?target=Library&id=12"
            print("  [3] Navigating to seat system...")
            page.get(seat_connect)
            time.sleep(3)
            print("  [3] URL: %s" % page.url[:120])

            # 处理 rump_frontend 重定向（可能在上一个 connect 页面或当前页面）
            for _ in range(2):
                if "rump_frontend/connect" not in page.url:
                    break
                link = page.ele("#url")
                if link:
                    print("  [3] Clicking redirect link...")
                    link.click()
                    time.sleep(3)
                    print("  [3] Redirected to: %s" % page.url[:120])
                else:
                    print("  [3] No #url link found, trying alternative...")
                    # 备选：直接访问图书馆首页
                    page.get(Settings.WEBVPN_BASE + "/rump_frontend/nav/")
                    time.sleep(2)
                    # 再试一次 connect
                    page.get(seat_connect)
                    time.sleep(3)

            # Step 3.5: 在图书馆页面点击座位预约入口
            time.sleep(1)
            current_title = page.title or ""
            print("  [3] Checking library page title: %s" % current_title)
            
            seat_btn = (
                page.ele(".group-item-img-2")
                or page.ele("tag:span@class=group-item-img group-item-img-2")
                or page.ele("text:座位预约")
                or page.ele("text:空间预约")
                or page.ele("tag:a@href:seat")
            )

            token = None
            
            if seat_btn:
                print("  [3] On library page, clicking seat entry...")
                seat_btn.click()
                time.sleep(1)
                
                # 切换到最新标签页
                if page.tabs_count > 1:
                    print(f"  [3] Detected {page.tabs_count} tabs, switching to the latest one...")
                    page.get_tab(page.latest_tab).set.activate()
                    time.sleep(1)
                
                print("  [3] Clicked seat entry, now: %s" % page.url[:200])
                
                # 等待 SPA 初始化
                print("  [3] Waiting for SPA to initialize...")
                time.sleep(3)

            # Step 4: 提取 token（带重试）
            print("  [4] Extracting token...")
            from config.settings import Settings as _Settings
            userinfo_api = _Settings.WEBVPN_BASE + _Settings.SEAT_PATH + "/ic-web/auth/userInfo"
            
            token = None
            app_acc_no = None
            
            for attempt in range(2):
                print("  [4] Attempt %d/2..." % (attempt + 1))
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
                ''', userinfo_api)
                
                if result:
                    import json
                    try:
                        parsed = json.loads(result)
                        token = parsed["token"]
                        app_acc_no = parsed.get("accNo")
                    except Exception:
                        pass
                
                if token:
                    print("  [4] Token: %s..." % str(token)[:20])
                    if app_acc_no:
                        print("  [4] appAccNo: %s" % app_acc_no)
                    break
                else:
                    if attempt == 0:
                        print("  [4] Attempt 1 failed, retrying in 4s...")
                        time.sleep(4)
                    else:
                        print("  [4] WARNING: Could not extract token after 2 attempts!")

            cookies = self._get_all_cookies(page)
            return cookies, token, app_acc_no

        except Exception as e:
            import traceback
            traceback.print_exc()
            # 异常时截图保存，带时间戳防止覆盖
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                page.get_screenshot(path=os.path.join(debug_dir, f"error_{ts}.png"))
            except:
                pass
            return [], None, None
        finally:
            try:
                page.quit()
            except Exception as e:
                print(f"  [WARN] Failed to quit ChromiumPage gracefully: {e}")
                # 兜底：尝试强制终止 Chrome/Chromium 进程
                import subprocess, platform
                try:
                    if platform.system() == "Windows":
                        subprocess.run(
                            ["taskkill", "/F", "/IM", "chrome.exe", "/T"],
                            capture_output=True, timeout=5,
                        )
                    else:
                        # Linux/Docker 容器中
                        subprocess.run(
                            ["pkill", "-f", "chromium|chrome"],
                            capture_output=True, timeout=5,
                        )
                except Exception:
                    pass

    @staticmethod
    def _get_all_cookies(page) -> List[Tuple[str, str, str, str]]:
        """提取所有 cookies"""
        result = []
        try:
            for c in page.cookies():
                if isinstance(c, dict):
                    result.append((
                        c["name"],
                        c["value"],
                        c.get("domain", ".njfu.edu.cn"),
                        c.get("path", "/"),
                    ))
                else:
                    result.append((
                        getattr(c, "name", str(c)),
                        getattr(c, "value", str(c)),
                        ".njfu.edu.cn",
                        "/",
                    ))
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
        except Exception:
            pass

        return result

