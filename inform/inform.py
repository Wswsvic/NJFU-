import requests
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


def inform(title: str, content: str, token: Optional[str] = None, email: Optional[str] = None) -> bool:
    """
    发送预约通知。优先级：PushPlus > QQ 邮箱 > 不通知

    Args:
        title:   通知标题
        content: 通知内容
        token:   PushPlus token（可选）
        email:   接收通知的邮箱地址（可选）
    """
    # ── 1. PushPlus ──
    token = token or os.getenv("PUSHPLUS_TOKEN", "")
    if token:
        ok = _pushplus(title, content, token)
        if ok:
            return True
        print("[inform] PushPlus 失败，尝试邮件...")

    # ── 2. QQ 邮箱 SMTP ──
    sender = os.getenv("MAIL_USER", "").strip()
    auth_code = os.getenv("MAIL_AUTH_CODE", "").strip()
    if sender and auth_code and email:
        ok = _send_mail(sender, auth_code, title, content, email)
        if ok:
            return True

    # ── 3. 无法通知 ──
    print("[inform] 无可用通知渠道，跳过")
    return False


def _pushplus(title: str, content: str, token: str) -> bool:
    try:
        resp = requests.post(
            "http://www.pushplus.plus/send",
            json={"token": token, "title": title, "content": content},
            timeout=10,
        )
        if resp.json().get("code") == 200:
            print("[inform] PushPlus 推送成功")
            return True
        print(f"[inform] PushPlus 返回: {resp.text[:200]}")
    except Exception as e:
        print(f"[inform] PushPlus 异常: {e}")
    return False


def _send_mail(sender: str, auth_code: str, title: str, content: str, receiver: str) -> bool:
    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = title
        msg.attach(MIMEText(content, "plain", "utf-8"))

        with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=10) as server:
            server.login(sender, auth_code)
            server.sendmail(sender, [receiver], msg.as_string())
        print(f"[inform] 邮件已发送至 {receiver}")
        return True
    except Exception as e:
        print(f"[inform] 邮件发送异常: {e}")
    return False


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    inform(title="测试通知", content="XYK 集成测试 - PushPlus > 邮件")
