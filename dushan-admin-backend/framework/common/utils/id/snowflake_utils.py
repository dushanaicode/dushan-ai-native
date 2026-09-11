import threading
import time
from datetime import UTC, datetime

SNOWFLAKE_EPOCH_MS = 1609459200000
MACHINE_ID_BITS = 10
SEQUENCE_BITS = 12
MAX_MACHINE_ID = (1 << MACHINE_ID_BITS) - 1
MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1
TIMESTAMP_SHIFT = MACHINE_ID_BITS + SEQUENCE_BITS
MAX_ELAPSED_MS = (1 << 41) - 1


class SnowflakeUtils:
    """生成固定 2021 UTC 纪元的 41/10/12 位雪花 ID。

    必须显式分配机器号；同一机器号同时只允许一个生成器拥有者。
    多进程和多服务器的机器号协调由部署或数据库组件负责，本类不自动分配。
    """

    def __init__(self, machine_id: int):
        """保存明确分配的机器号及线程锁，不采用隐含机器号零。"""
        if type(machine_id) is not int or not 0 <= machine_id <= MAX_MACHINE_ID:
            raise ValueError(f"机器号必须是 0～{MAX_MACHINE_ID} 的整数")
        self._machine_id = machine_id
        self._last_timestamp_ms = -1
        self._sequence = 0
        self._lock = threading.Lock()

    @staticmethod
    def _current_timestamp_ms() -> int:
        """读取当前 Unix 毫秒时间戳。"""
        return time.time_ns() // 1_000_000

    def get_id(self) -> int:
        """在锁内生成 ID，时钟回退或单毫秒容量用完即报错，不忙等。"""
        with self._lock:
            timestamp = self._current_timestamp_ms()
            elapsed = timestamp - SNOWFLAKE_EPOCH_MS
            if not 0 <= elapsed <= MAX_ELAPSED_MS:
                raise RuntimeError("当前时间超出雪花 ID 的纪元范围")
            if timestamp < self._last_timestamp_ms:
                raise RuntimeError("系统时钟回退，拒绝生成雪花 ID")
            sequence = self._sequence + 1 if timestamp == self._last_timestamp_ms else 0
            if sequence > MAX_SEQUENCE:
                raise RuntimeError("当前毫秒的雪花 ID 序列已用完")
            identifier = (
                (elapsed << TIMESTAMP_SHIFT) | (self._machine_id << SEQUENCE_BITS) | sequence
            )
            if identifier == 0:
                raise RuntimeError("纪元起点不能产生零 ID")
            self._last_timestamp_ms, self._sequence = timestamp, sequence
            return identifier

    @staticmethod
    def parse_id(snowflake_id: int) -> dict[str, object]:
        """解析正有符号 64 位 ID，日期结果明确采用 UTC。"""
        if type(snowflake_id) is not int or not 0 < snowflake_id < 1 << 63:
            raise ValueError("雪花 ID 必须是正有符号 64 位整数")
        timestamp = (snowflake_id >> TIMESTAMP_SHIFT) + SNOWFLAKE_EPOCH_MS
        return {
            "timestamp_ms": timestamp,
            "machine_id": (snowflake_id >> SEQUENCE_BITS) & MAX_MACHINE_ID,
            "sequence": snowflake_id & MAX_SEQUENCE,
            "datetime": datetime.fromtimestamp(timestamp / 1000, UTC),
        }

    def batch_ids(self, count: int) -> list[int]:
        """按指定数量生成 ID；失败时已消费的序列不会回退。"""
        if type(count) is not int or count < 0:
            raise ValueError("数量必须是非负整数")
        return [self.get_id() for _ in range(count)]
