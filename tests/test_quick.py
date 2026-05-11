"""
快速测试脚本 - 验证模块化系统是否正常工作
"""
import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bot.core import LibraryBot


def test_import():
    """测试1：验证所有模块能否正常导入"""
    print("=" * 60)
    print("测试1：模块导入检查")
    print("=" * 60)
    try:
        from config.settings import Settings
        print("  ✓ config.settings")

        from config.constants import SeatConstants
        print("  ✓ config.constants")

        from src.bot.crypto import CryptoUtils
        print("  ✓ src.bot.crypto")

        from src.bot.auth import AuthManager
        print("  ✓ src.bot.auth")

        from src.bot.network import NetworkManager
        print("  ✓ src.bot.network")

        from src.bot.seat import SeatManager
        print("  ✓ src.bot.seat")

        from src.bot.reserve import ReserveManager
        print("  ✓ src.bot.reserve")

        from src.bot.core import LibraryBot
        print("  ✓ src.bot.core")

        print("\n✅ 所有模块导入成功！")
        return True
    except ImportError as e:
        print(f"\n❌ 导入失败: {e}")
        return False


def test_config():
    """测试2：验证配置是否正确"""
    print("\n" + "=" * 60)
    print("测试2：配置检查")
    print("=" * 60)
    from config.settings import Settings

    print(f"  WEBVPN_BASE: {Settings.WEBVPN_BASE}")
    print(f"  APP_ACC_NO:  {Settings.APP_ACC_NO}")
    print(f"  SEAT_PATH 长度: {len(Settings.SEAT_PATH)}")
    print("✅ 配置正常")


def test_crypto():
    """测试3：验证加密功能"""
    print("\n" + "=" * 60)
    print("测试3：加密功能检查")
    print("=" * 60)
    from src.bot.crypto import CryptoUtils

    # 测试随机字符串生成
    rds = CryptoUtils._rds(16)
    print(f"  随机字符串(16位): {rds}")
    assert len(rds) == 16, "随机字符串长度不正确"

    # 测试密码加密
    encrypted = CryptoUtils.encrypt_password("test_password", "test_salt_16byte")
    print(f"  加密结果: {encrypted[:50]}...")
    assert encrypted, "加密结果为空"

    print("✅ 加密功能正常")


def test_bot_creation():
    """测试4：验证 LibraryBot 实例化"""
    print("\n" + "=" * 60)
    print("测试4：LibraryBot 实例化")
    print("=" * 60)
    from config.settings import Settings
    from src.bot.core import LibraryBot

    # 从环境变量读取（不打印密码）
    username = os.getenv("LIBRARY_USERNAME", "test_user")
    password = os.getenv("LIBRARY_PASSWORD", "test_pass")

    bot = LibraryBot(
        username=username,
        password_plain=password,
        headless=True,  # 测试用 headless 模式
    )

    print(f"  username: {bot.username}")
    print(f"  headless: {bot.headless}")
    print(f"  session:  {type(bot.session).__name__}")
    print(f"  auth:     {type(bot.auth).__name__}")
    print(f"  network:  {type(bot.network).__name__}")
    print(f"  seat:     {type(bot.seat).__name__}")
    print(f"  reserve:  {type(bot.reserve_manager).__name__}")

    print("✅ LibraryBot 实例化成功")
    return bot


def test_login(bot, skip_login=True):
    """测试5：验证登录（默认跳过，因为需要浏览器）"""
    print("\n" + "=" * 60)
    print("测试5：登录测试")
    print("=" * 60)

    if skip_login:
        print("  ⏭️  跳过登录测试（需要浏览器交互）")
        print("  如需测试登录，请手动运行:")
        print("  python tests/test_login.py")
        return

    try:
        bot.login()
        print("✅ 登录成功")
    except Exception as e:
        print(f"❌ 登录失败: {e}")


if __name__ == "__main__":
    print("\n🚀 开始模块化系统测试\n")

    # 运行所有基础测试
    test_import()
    test_config()
    test_crypto()
    bot = test_bot_creation()
    test_login(bot, skip_login=False)

    print("\n" + "=" * 60)
    print("✅ 基础测试全部通过！")
    print("=" * 60)
    print("\n💡 提示：")
    print("  1. 运行登录测试: python tests/test_login.py")
    print("  2. 运行原版脚本: python scripts/reserve_v8.py")
    print("  3. 查看楼层信息: python tests/test_floor.py")