"""
操作日志：记录 bot 浏览器操作的详细过程，按天输出到 debug/
每晚 22:00 压缩当天日志，保留最近 3 天
"""
import os
import sys
import zipfile
import threading
from datetime import datetime, timedelta
from contextlib import contextmanager
from typing import Optional


class OperatingLogger:
    """操作日志管理器（线程安全单例）"""

    _instance: Optional["OperatingLogger"] = None
    _lock = threading.Lock()

    def __init__(self, debug_dir: str):
        self.debug_dir = debug_dir
        os.makedirs(debug_dir, exist_ok=True)
        self._current_date = None
        self._file_path = None

    def _today_str(self) -> str:
        return datetime.now().strftime("%Y%m%d")

    def _get_log_path(self) -> str:
        date_str = self._today_str()
        if date_str != self._current_date:
            self._current_date = date_str
            self._file_path = os.path.join(
                self.debug_dir, f"{date_str}_operating.log"
            )
        return self._file_path

    def start_session(self, plan_id: int, username: str, room_id, seat_name: str):
        """开始一次预约的操作日志会话"""
        with self._lock:
            path = self._get_log_path()
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            separator = "=" * 60
            header = (
                f"\n{separator}\n"
                f"  Session Start : {ts}\n"
                f"  Plan ID       : {plan_id}\n"
                f"  Username      : {username}\n"
                f"  Room ID       : {room_id}\n"
                f"  Seat          : {seat_name or '(auto)'}\n"
                f"{separator}\n"
            )
            with open(path, "a", encoding="utf-8") as f:
                f.write(header)

    def write(self, message: str):
        """追加一条操作日志"""
        line = message.strip()
        if not line:
            return
        with self._lock:
            ts = datetime.now().strftime("%H:%M:%S")
            with open(self._get_log_path(), "a", encoding="utf-8") as f:
                f.write(f"{ts}  {line}\n")

    # ── stdout 重定向 ──────────────────────────────────────────

    @contextmanager
    def capture_stdout(self):
        """临时将 sys.stdout 重定向到操作日志（同时保留控制台输出）"""
        old_stdout = sys.stdout

        class _Tee:
            def __init__(self, logger, original):
                self._logger = logger
                self._original = original

            def write(self, s):
                self._original.write(s)
                self._original.flush()
                if s.strip():
                    self._logger.write(s.rstrip("\n"))

            def flush(self):
                self._original.flush()

        sys.stdout = _Tee(self, old_stdout)  # type: ignore[assignment]
        try:
            yield
        finally:
            sys.stdout = old_stdout

    # ── 归档 & 清理 ────────────────────────────────────────────

    @staticmethod
    def archive_and_cleanup(debug_dir: str) -> int:
        """压缩当天的 .log 文件为 .zip，删除 3 天前的包。返回清理数量"""
        today = datetime.now().strftime("%Y%m%d")
        removed = 0

        # 压缩当天所有 operating log
        for filename in os.listdir(debug_dir):
            if not filename.endswith("_operating.log"):
                continue
            full = os.path.join(debug_dir, filename)
            if not os.path.isfile(full):
                continue
            # 提取日期：YYYYMMDD_operating.log
            date_str = filename[:8]
            zip_name = f"operating_logs_{date_str}.zip"
            zip_path = os.path.join(debug_dir, zip_name)

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(full, filename)
            os.remove(full)
            print(f"[Archive] {filename} → {zip_name}")

        # 清理 3 天前的 zip
        cutoff = datetime.now() - timedelta(days=3)
        for filename in os.listdir(debug_dir):
            if not filename.startswith("operating_logs_") or not filename.endswith(".zip"):
                continue
            try:
                date_str = filename.replace("operating_logs_", "").replace(".zip", "")
                file_date = datetime.strptime(date_str, "%Y%m%d")
                if file_date < cutoff:
                    os.remove(os.path.join(debug_dir, filename))
                    removed += 1
                    print(f"[Cleanup] Removed: {filename}")
            except ValueError:
                pass

        return removed
