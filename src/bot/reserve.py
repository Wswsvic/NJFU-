from typing import Dict, Any, Optional
from datetime import datetime
import threading
from config.constants import SeatConstants
from .network import NetworkManager


class ReserveManager:
    """预约管理"""

    def __init__(self, network: NetworkManager, app_acc_no: int):
        self.network = network
        self.app_acc_no = app_acc_no

    def reserve(self, dev_id: int, begin_time, end_time) -> Dict[str, Any]:
        """预约座位

        Args:
            dev_id: 座位 ID
            begin_time: datetime 对象或毫秒时间戳
            end_time: datetime 对象或毫秒时间戳
        """
        if isinstance(begin_time, int):
            bt = begin_time
        else:
            bt = int(begin_time.timestamp() * 1000)
        if isinstance(end_time, int):
            et = end_time
        else:
            et = int(end_time.timestamp() * 1000)

        payload = {
            "sysKind": SeatConstants.SYS_KIND,
            "appAccNo": self.app_acc_no,
            "memberKind": SeatConstants.MEMBER_KIND,
            "resvMember": [self.app_acc_no],
            "resvBeginTime": bt,
            "resvEndTime": et,
            "resvDev": [dev_id],
            "resvProperty": SeatConstants.RESV_PROPERTY,
            "captcha": "",
            "memo": "",
            "testName": "",
        }
        return self.network._post("/ic-web/reserve", payload)

    def auto_reserve(
        self,
        room_id: int,
        begin_time,
        end_time,
        seat_manager,
        prefer_seat: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """自动预约

        Args:
            room_id: 房间 ID
            begin_time: datetime 对象
            end_time: datetime 对象
            seat_manager: SeatManager 实例
            prefer_seat: 优先选择的座位名称
        """
        tag = threading.current_thread().name
        print("")
        print(f"[{tag}] Auto-reserve: %s ~ %s" % (begin_time, end_time))

        date_str = begin_time.strftime("%Y-%m-%d")[:10].replace("-", "")
        available = seat_manager.get_available_seats(room_id, date_str)

        if not available:
            print(f"[{tag}] No available seats")
            return None

        target = None
        if prefer_seat:
            for s in available:
                if prefer_seat in s["devName"]:
                    target = s
                    break

        if not target:
            target = available[0]

        print(f"[{tag}] Selected: %s" % target["devName"])
        result = self.reserve(target["devId"], begin_time, end_time)

        if isinstance(result, dict) and result.get("code") == 0:
            print(f"[{tag}] Success! ID: %s" % result["data"]["resvId"])
            return result
        else:
            print(f"[{tag}] Failed: %s" % result.get("message", result))
            return None