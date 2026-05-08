import requests
import os


def inform(title: str, content: str, token: str | None = None) -> bool:
    """
    通过 PushPlus 发送通知

    Args:
        title:   通知标题
        content: 通知内容
        token:   PushPlus token，不传则从环境变量 PUSHPLUS_TOKEN 读取

    Returns:
        True 表示发送成功，False 表示失败
    """
    if token is None:
        token = os.getenv("PUSHPLUS_TOKEN", "")

    if not token:
        print("[inform] 未提供 PushPlus token，请设置环境变量 PUSHPLUS_TOKEN 或传入 token")
        return False

    url = "http://www.pushplus.plus/send"
    payload = {
    "token": token,
    "title": title,
        "content": content,
}

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            print("[inform] 推送成功")
            return True
        else:
            print(f"[inform] 推送失败: {result}")
            return False
    except requests.RequestException as e:
        print(f"[inform] 请求异常: {e}")
        return False


if __name__ == "__main__":
    # 直接运行时的测试
    import config  # 自动加载 .env
    inform(
        title="test",
        content="XYK testing",
        token=os.getenv("PUSHPLUS_TOKEN", "5515d729ceaf4b31b2c19df0c875eb2b")
    )
