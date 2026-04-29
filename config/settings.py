import os


class Settings:
    """配置管理"""

    # WebVPN 基础地址
    WEBVPN_BASE = "https://webvpn.njfu.edu.cn"

    # 座位系统路径
    SEAT_PATH = (
        "/webvpn/LjIwMS4xNjkuMjE4LjE2OC4xNjc=/"
        "LjIwNS4xNTguMjAwLjE3MS4xNTMuMTUwLjIxNi45Ny4yMTEuMTU2LjE1OC4xNzMuMTQ4LjE1NS4xNTUuMjE3LjEwMC4xNTAuMTY1"
    )

    # 应用账号
    APP_ACC_NO = 78388

    # 请求头
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }