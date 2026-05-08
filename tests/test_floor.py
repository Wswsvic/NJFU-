"""
楼层信息查看测试 - 需要先登录成功
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载 .env 文件（config/__init__.py 会自动执行 load_dotenv）
import config

from src.bot.core import LibraryBot

username = os.getenv("LIBRARY_USERNAME")
password = os.getenv("LIBRARY_PASSWORD")

if not username or not password:
    print("❌ 请先设置 .env 文件")
    sys.exit(1)

print("登录中...")
bot = LibraryBot(
    username=username,
    password_plain=password,
    headless=True,  # 无头模式，更快
)

try:
    bot.login()
    print("\n获取楼层信息...")
    bot.print_floor_info()
    print("\n✅ 测试完成")
except Exception as e:
    print(f"\n❌ 失败: {e}")
    import traceback
    traceback.print_exc()