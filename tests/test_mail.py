"""简单测试邮件通知"""
import os
import sys

# 确保能加载 .env 和 inform 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from inform.inform import inform

result = inform(
    title="座位预约成功",
    content="测试邮件通知 — 您的座位已预约成功！",
    token=None,  # 跳过 PushPlus，直接走邮件
    email="3299085059@qq.com",
)

print(f"\n发送结果: {'成功 ✅' if result else '失败 ❌'}")
