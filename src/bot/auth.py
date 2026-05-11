import time
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

            # Step 3: 导航到座位系统
            seat_connect = Settings.WEBVPN_BASE + "/rump_frontend/connect/?target=Library&id=12"
            print("  [3] Navigating to seat system...")
            page.get(seat_connect)
            time.sleep(2)
            print("  [3] URL: %s" % page.url[:120])

            # 处理 rump_frontend 重定向
            if "rump_frontend" in page.url:
                link = page.ele("#url")
                if link:
                    link.click()
                    time.sleep(2)
                    print("  [3] Clicked redirect, now: %s" % page.url[:120])

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
            
            if seat_btn:
                print("  [3] On library page, clicking seat entry...")
                seat_btn.click()
                time.sleep(3) # 给一点渲染时间
                print("  [3] Clicked seat entry, now: %s" % page.url[:120])
                
                # 有些系统需要点击后强制获取真正用来交互的 token
                token = page.local_storage("token") # 尝试获取 local_storage 中的 token
                if token:
                    print("  [3] Found token in localStorage: %s..." % str(token)[:10])
            else:
                print("  [3] Cannot find seat entry. (This may be the issue!)")
                page.get_screenshot(path=os.path.join(debug_dir, "error_snap_no_entry.png"))

            cookies = self._get_all_cookies(page)
            return cookies, None

        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                page.get_screenshot(path=os.path.join(debug_dir, "error_snap_exception.png"))
            except:
                pass
            return [], None
        finally:
            try:
                page.quit()
            except Exception as e:
                print(f"  [WARN] Failed to quit ChromiumPage gracefully: {e}")

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

