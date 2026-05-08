"""
登录测试 - 需要浏览器支持
"""
import sys
import os
from dotenv import load_dotenv  # 新增导入

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载 .env 文件
load_dotenv()  # 新增这行

from src.bot.core import LibraryBot

# 从环境变量读取
username = os.getenv("LIBRARY_USERNAME")
password = os.getenv("LIBRARY_PASSWORD")

if not username or not password:
    print("❌ 请先设置 .env 文件中的 LIBRARY_USERNAME 和 LIBRARY_PASSWORD")
    sys.exit(1)

# 先使用有头模式测试，确认能正常打开浏览器
print("创建 LibraryBot (有头模式)...")
bot = LibraryBot(
    username=username,
    password_plain=password,
    headless=False,  # 有头模式，方便观察
)

print("\n开始登录...")
try:
    bot.login()
    print("\n✅ 登录成功！")
    print("\n现在可以查看楼层信息...")
    bot.print_floor_info()
except Exception as e:
    print(f"\n❌ 登录失败: {e}")
    import traceback
    traceback.print_exc()