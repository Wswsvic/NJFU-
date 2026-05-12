# encoding: utf-8
"""
Web 系统配置：加密工具、文件路径常量
"""
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

ENCRYPT_KEY = os.getenv('ENCRYPT_KEY', '')
if not ENCRYPT_KEY:
    raise RuntimeError('请设置 ENCRYPT_KEY')
_cipher = Fernet(ENCRYPT_KEY.encode())

def encrypt_password(plain: str) -> str:
    return _cipher.encrypt(plain.encode()).decode()

def decrypt_password(token: str) -> str:
    return _cipher.decrypt(token.encode()).decode()

DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DEBUG_DIR = os.path.join(BASE_DIR, 'debug')
os.makedirs(DEBUG_DIR, exist_ok=True)
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
PLANS_FILE = os.path.join(DATA_DIR, 'plans.json')
LOGS_FILE = os.path.join(DATA_DIR, 'logs.json')
