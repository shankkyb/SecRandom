import subprocess
import uuid
import hashlib
from loguru import logger

def get_hardware_uuid():
    """
    获取电脑的唯一硬件ID。
    尝试顺序：
    1. WMI 硬件 UUID (wmic csproduct get uuid)
    2. 如果失败，使用 uuid.getnode() (MAC地址) 的哈希值
    """
    try:
        # 尝试通过 wmic 获取 UUID
        cmd = ['wmic', 'csproduct', 'get', 'uuid']
        uuid_output = subprocess.check_output(cmd).decode().split('\n')
        if len(uuid_output) > 1:
            hw_uuid = uuid_output[1].strip()
            # 排除掉一些无效的UUID
            if hw_uuid and hw_uuid.upper() not in ["FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF", "00000000-0000-0000-0000-000000000000"]:
                return hw_uuid
    except Exception as e:
        logger.warning(f"无法通过WMI获取硬件UUID: {e}")

    # 备选方案：使用 uuid.getnode()
    try:
        node = uuid.getnode()
        # 将 node 转换为 16 进制字符串并进行哈希，确保格式统一且具有一定匿名性
        node_str = hex(node)
        return hashlib.sha256(node_str.encode()).hexdigest()[:32]
    except Exception as e:
        logger.error(f"无法获取uuid.getnode(): {e}")
        return "unknown-device"

if __name__ == "__main__":
    print(f"Hardware UUID: {get_hardware_uuid()}")
