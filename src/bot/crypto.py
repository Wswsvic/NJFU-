import base64
import random
from config.constants import SeatConstants

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
except ModuleNotFoundError:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad


class CryptoUtils:
    """加密工具类"""

    @staticmethod
    def _rds(n: int) -> str:
        """生成 n 位随机字符串"""
        return "".join(random.choice(SeatConstants.CHARS) for _ in range(n))

    @staticmethod
    def encrypt_password(plain: str, salt: str) -> str:
        """AES-CBC 加密密码"""
        prefix = CryptoUtils._rds(64)
        iv = CryptoUtils._rds(16)
        data = (prefix + plain).encode()
        cipher = AES.new(salt.encode(), AES.MODE_CBC, iv.encode())
        ct = cipher.encrypt(pad(data, AES.block_size))
        return base64.b64encode(ct).decode()