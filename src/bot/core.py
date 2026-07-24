import requests
import threading
from config.settings import Settings
from .auth import AuthManager
from .network import NetworkManager
from .seat import SeatManager
from .reserve import ReserveManager


class LibraryBot:
    """图书馆座位预约机器人 - 核心类"""

    def __init__(self, username: str, password_plain: str, headless: bool = True):
        self.username = username
        self.password_plain = password_plain
        self.headless = headless

        # 初始化 session
        self.session = requests.Session()
        self.session.headers.update(Settings.HEADERS)

        # 初始化各模块
        self.auth = AuthManager(username, password_plain, headless)
        self.network = NetworkManager(self.session)
        self.seat = SeatManager(self.network)
        self.reserve_manager = None  # login 时动态创建，需要 app_acc_no

        self.token = None

    def login(self) -> bool:
        """执行完整登录流程"""
        tag = threading.current_thread().name
        print("=" * 60)
        print(f"[{tag}] Login")
        print("=" * 60)
        print("")

        # [1/2] 浏览器登录
        print(f"[{tag}] [1/2] Browser login (portal approach)...")
        cookies, token, app_acc_no = self.auth.browser_login()
        if not cookies:
            raise Exception("Browser login failed")

        for name, value, domain, path in cookies:
            self.session.cookies.set(name, value, domain=domain, path=path)
        print(f"[{tag}]   Got %d cookies" % len(cookies))
        for name, value, _, _ in cookies:
            print(f"[{tag}]     %s = %s..." % (name, value[:20]))

        if token:
            self.session.headers["token"] = token
            self.token = token
            print(f"[{tag}]   Token: %s..." % token[:20])
        else:
            print(f"[{tag}]   WARNING: no token!")

        if app_acc_no:
            self.reserve_manager = ReserveManager(self.network, app_acc_no)
            print(f"[{tag}]   appAccNo: %s" % app_acc_no)
        else:
            raise Exception("Failed to get appAccNo from userInfo API")

        print("")

        # [2/2] 验证登录状态
        print(f"[{tag}] [2/2] Verifying...")
        try:
            result = self.seat.get_floor_overview()
            if result:
                print(f"[{tag}]   Floors OK - %d" % len(result))
        except Exception as e:
            print(f"[{tag}]   Floor verify: %s" % e)

        print("")
        print(f"[{tag}] Done!")
        return True

    # 兼容原版 API 的方法
    def get_floor_overview(self):
        return self.seat.get_floor_overview()

    def print_floor_info(self):
        self.seat.print_floor_info()

    def get_seats_by_room(self, room_id, reserve_date=None):
        return self.seat.get_seats_by_room(room_id, reserve_date)

    def get_available_seats(self, room_id, reserve_date=None):
        return self.seat.get_available_seats(room_id, reserve_date)

    def reserve(self, dev_id, begin_time, end_time):
        return self.reserve_manager.reserve(dev_id, begin_time, end_time)

    def auto_reserve(self, room_id, begin_time, end_time, prefer_seat=None):
        return self.reserve_manager.auto_reserve(
            room_id, begin_time, end_time, self.seat, prefer_seat
        )