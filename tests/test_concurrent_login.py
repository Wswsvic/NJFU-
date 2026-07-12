"""
顺序登录测试：模拟两个用户依次执行预约计划的登录阶段
只测试到 auto_reserve 之前，不进行实际预约
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 必须在导入 web.config 前加载 .env
from dotenv import load_dotenv
load_dotenv()

from web.config import decrypt_password
from src.bot.core import LibraryBot

# ==================== 配置 ====================
USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "users.json")
TEST_USER_COUNT = 2


def load_users(filepath: str) -> list[dict]:
    """从本地 data/users.json 加载用户列表"""
    if not os.path.exists(filepath):
        print(f"[ERROR] users.json not found: {filepath}")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("[ERROR] users.json is not a list")
        return []

    return data


def login_one_user(user: dict, idx: int) -> dict:
    """单个用户的登录"""
    username = user["username"]
    enc_pwd = user["encrypted_password"]
    result = {
        "username": username,
        "id": user.get("id"),
    }

    print(f"\n{'=' * 60}")
    print(f"[User-{idx}] {username}")
    print(f"{'=' * 60}")

    try:
        password = decrypt_password(enc_pwd)
    except Exception as e:
        result["success"] = False
        result["error"] = f"密码解密失败: {e}"
        return result

    bot = LibraryBot(
        username=username,
        password_plain=password,
        headless=True,
    )

    try:
        bot.login()
        result["success"] = True
        result["token"] = bot.token[:20] + "..." if bot.token else "N/A"
        result["appAccNo"] = (bot.reserve_manager.app_acc_no
                              if bot.reserve_manager else "N/A")
    except Exception as e:
        import traceback
        traceback.print_exc()
        result["success"] = False
        result["error"] = str(e)

    return result


def main():
    users = load_users(USERS_FILE)
    if not users:
        print("[ERROR] No users loaded, abort.")
        return

    print(f"Loaded {len(users)} user(s) from {USERS_FILE}")
    for u in users:
        print(f"  - id={u['id']}: {u['username']}")

    test_users = users[:TEST_USER_COUNT]

    print(f"\n{'=' * 60}")
    print(f"Running {len(test_users)} login(s) sequentially...")
    print(f"{'=' * 60}")

    start_time = time.time()
    results = []

    for i, user in enumerate(test_users, start=1):
        res = login_one_user(user, i)
        results.append(res)

    elapsed = time.time() - start_time

    # ==================== 结果汇总 ====================
    print(f"\n{'=' * 60}")
    print(f"Test Results (elapsed: {elapsed:.1f}s)")
    print(f"{'=' * 60}")

    all_ok = True
    for r in results:
        status = "PASS" if r["success"] else "FAIL"
        print(f"  [{status}]  {r['username']}  ", end="")
        if r["success"]:
            print(f"token={r.get('token', '?')}  appAccNo={r.get('appAccNo', '?')}")
        else:
            print(f"error={r.get('error', '?')}")
            all_ok = False

    print(f"\n{'=' * 60}")
    if all_ok:
        print("All logins passed!")
    else:
        print("Some logins failed — check errors above")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
