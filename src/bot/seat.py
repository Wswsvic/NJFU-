from typing import List, Dict, Any
from datetime import datetime
from .network import NetworkManager


class SeatManager:
    """座位管理"""

    def __init__(self, network: NetworkManager):
        self.network = network

    def get_floor_overview(self) -> List[Dict[str, Any]]:
        """获取楼层概览"""
        result = self.network._get("/ic-web/seatMenu")
        if isinstance(result, dict) and result.get("code") == 0:
            return result["data"]
        raise Exception("seatMenu failed: " + str(result))

    def get_seats_by_room(self, room_id: int, reserve_date: str = None) -> List[Dict[str, Any]]:
        """获取指定房间的座位列表"""
        if reserve_date is None:
            reserve_date = datetime.now().strftime("%Y%m%d")
        result = self.network._get(
            "/ic-web/reserve",
            {"roomIds": room_id, "resvDates": reserve_date, "sysKind": 8},
        )
        if isinstance(result, dict) and result.get("code") == 0:
            return result["data"]
        raise Exception("get_seats failed: " + str(result))

    def get_available_seats(self, room_id: int, reserve_date: str = None) -> List[Dict[str, Any]]:
        """获取可用座位"""
        return [
            s
            for s in self.get_seats_by_room(room_id, reserve_date)
            if s["devStatus"] == 0
        ]

    def print_floor_info(self):
        """打印楼层信息"""
        floors = self.get_floor_overview()
        print("")
        print("Floor Overview:")
        print("-" * 60)
        for f in floors:
            print("")
            print(
                "%s (total:%d, free:%d)"
                % (f["name"], f["totalCount"], f["remainCount"])
            )
            for a in f.get("children", []):
                print(
                    "  - %s (ID:%d, total:%d, free:%d)"
                    % (a["name"], a["id"], a["totalCount"], a["remainCount"])
                )