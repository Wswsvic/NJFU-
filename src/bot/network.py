import requests
from typing import Dict, Any, Optional
from config.settings import Settings


class NetworkManager:
    """网络请求管理"""

    def __init__(self, session: requests.Session):
        self.session = session
        self.base = Settings.WEBVPN_BASE
        self.seat_path = Settings.SEAT_PATH

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """发送 GET 请求"""
        url = self.base + self.seat_path + path
        qp = {"vpn-12-libseat.njfu.edu.cn": ""}
        if params:
            qp.update({str(k): str(v) for k, v in params.items()})

        r = self.session.get(url, params=qp)
        ct = r.headers.get("Content-Type", "")
        if "json" not in ct:
            print("  [WARN] GET %s: %d %s" % (path, r.status_code, ct))
            print("  Body: %s" % r.text[:300])
        return r.json()

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发送 POST 请求"""
        url = self.base + self.seat_path + path
        qp = {"vpn-12-libseat.njfu.edu.cn": ""}

        r = self.session.post(
            url,
            params=qp,
            json=payload,
            headers={"Content-Type": "application/json;charset=UTF-8"},
        )
        ct = r.headers.get("Content-Type", "")
        if "json" not in ct:
            print("  [WARN] POST %s: %d %s" % (path, r.status_code, ct))
            print("  Body: %s" % r.text[:300])
        return r.json()