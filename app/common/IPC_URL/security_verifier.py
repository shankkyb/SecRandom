# ==================================================
# 安全验证器
# ==================================================
import hashlib
import time
from typing import Dict, Any, Optional
from loguru import logger
from PySide6.QtCore import QObject, Signal


# ==================================================
# 安全验证器基类
# ==================================================
class SecurityVerifier(QObject):
    """安全验证器基类
    
    提供基础的安全验证功能，包括：
    - 密码验证
    - 时间窗口验证
    - 尝试次数限制
    - 验证记录
    """
    
    verificationRequested = Signal(str, dict)  # 验证请求信号
    verificationCompleted = Signal(str, bool, dict)  # 验证完成信号
    
    def __init__(self):
        super().__init__()
        self.max_attempts = 3
        self.attempt_window = 300  # 5分钟
        self.verification_history = {}
        
    def verify(self, verification_data: Dict[str, Any]) -> bool:
        """执行验证
        
        Args:
            verification_data: 验证数据，包含密码等信息
            
        Returns:
            验证是否通过
        """
        try:
            command = verification_data.get('command', '')
            password = verification_data.get('password', '')
            
            # 检查尝试次数
            if not self._check_attempt_limit(command):
                logger.warning(f"验证尝试次数超限: {command}")
                return False
            
            # 执行具体验证逻辑
            result = self._perform_verification(password, verification_data)
            
            # 记录验证结果
            self._record_verification(command, result, verification_data)
            
            # 发送验证完成信号
            self.verificationCompleted.emit(command, result, verification_data)
            
            return result
            
        except Exception as e:
            logger.error(f"验证过程出错: {e}")
            return False
    
    def _check_attempt_limit(self, command: str) -> bool:
        """检查尝试次数限制"""
        current_time = time.time()
        key = f"attempts_{command}"
        
        if key not in self.verification_history:
            self.verification_history[key] = []
        
        # 清理过期记录
        self.verification_history[key] = [
            timestamp for timestamp in self.verification_history[key]
            if current_time - timestamp < self.attempt_window
        ]
        
        # 检查是否超过限制
        if len(self.verification_history[key]) >= self.max_attempts:
            return False
        
        return True
    
    def _perform_verification(self, password: str, verification_data: Dict[str, Any]) -> bool:
        """执行具体的验证逻辑（子类实现）"""
        raise NotImplementedError("子类必须实现此方法")
    
    def _record_verification(self, command: str, result: bool, verification_data: Dict[str, Any]):
        """记录验证结果"""
        current_time = time.time()
        
        # 记录尝试次数
        key = f"attempts_{command}"
        if key not in self.verification_history:
            self.verification_history[key] = []
        self.verification_history[key].append(current_time)
        
        # 记录验证结果
        result_key = f"result_{command}"
        self.verification_history[result_key] = {
            'result': result,
            'timestamp': current_time,
            'data': verification_data
        }
    
    def get_verification_status(self, command: str = '') -> Dict[str, Any]:
        """获取验证状态"""
        current_time = time.time()
        
        status = {
            'max_attempts': self.max_attempts,
            'attempt_window': self.attempt_window,
            'current_attempts': 0,
            'remaining_attempts': self.max_attempts,
            'last_verification': None,
            'can_verify': True
        }
        
        if command:
            key = f"attempts_{command}"
            if key in self.verification_history:
                valid_attempts = [
                    timestamp for timestamp in self.verification_history[key]
                    if current_time - timestamp < self.attempt_window
                ]
                status['current_attempts'] = len(valid_attempts)
                status['remaining_attempts'] = max(0, self.max_attempts - len(valid_attempts))
                status['can_verify'] = len(valid_attempts) < self.max_attempts
                
                result_key = f"result_{command}"
                if result_key in self.verification_history:
                    status['last_verification'] = self.verification_history[result_key]
        
        return status
    
    def reset_attempts(self, command: str = ''):
        """重置尝试次数"""
        if command:
            key = f"attempts_{command}"
            if key in self.verification_history:
                del self.verification_history[key]
            result_key = f"result_{command}"
            if result_key in self.verification_history:
                del self.verification_history[result_key]
        else:
            # 重置所有
            self.verification_history.clear()
        
        logger.info(f"验证尝试次数已重置: {command or 'all'}")


# ==================================================
# 简单密码验证器
# ==================================================
class SimplePasswordVerifier(SecurityVerifier):
    """简单密码验证器
    
    使用预设密码进行验证
    """
    
    def __init__(self, password: str = None):
        super().__init__()
        self.correct_password = password or "SecRandom2024"
        
        # 支持哈希密码
        if len(self.correct_password) == 64:  # SHA256哈希长度
            self.is_hashed = True
        else:
            self.is_hashed = False
            self.hashed_password = hashlib.sha256(self.correct_password.encode()).hexdigest()
    
    def _perform_verification(self, password: str, verification_data: Dict[str, Any]) -> bool:
        """执行密码验证"""
        if not password:
            logger.warning("未提供密码")
            return False
        
        # 如果输入的是明文密码，先哈希
        if len(password) != 64:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        else:
            password_hash = password
        
        # 比较哈希值
        expected_hash = self.correct_password if self.is_hashed else self.hashed_password
        result = password_hash == expected_hash
        
        if result:
            logger.info("密码验证成功")
        else:
            logger.warning("密码验证失败")
        
        return result
    
    def set_password(self, new_password: str):
        """设置新密码"""
        self.correct_password = new_password
        if len(new_password) == 64:
            self.is_hashed = True
        else:
            self.is_hashed = False
            self.hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
        logger.info("密码已更新")


# ==================================================
# 动态密码验证器
# ==================================================
class DynamicPasswordVerifier(SecurityVerifier):
    """动态密码验证器
    
    基于时间窗口生成动态密码
    """
    
    def __init__(self, secret: str = None, time_window: int = 30):
        super().__init__()
        self.secret = secret or "SecRandomSecretKey"
        self.time_window = time_window  # 时间窗口（秒）
    
    def _perform_verification(self, password: str, verification_data: Dict[str, Any]) -> bool:
        """执行动态密码验证"""
        if not password:
            logger.warning("未提供密码")
            return False
        
        current_time = int(time.time())
        
        # 检查当前时间窗口和前后各一个时间窗口
        for time_offset in [-1, 0, 1]:
            expected_password = self._generate_password(current_time + time_offset * self.time_window)
            if password == expected_password:
                logger.info("动态密码验证成功")
                return True
        
        logger.warning("动态密码验证失败")
        return False
    
    def _generate_password(self, timestamp: int) -> str:
        """生成指定时间戳的密码"""
        # 计算时间窗口
        time_window = timestamp // self.time_window
        
        # 组合密钥和时间窗口
        data = f"{self.secret}{time_window}"
        
        # 生成哈希
        password_hash = hashlib.sha256(data.encode()).hexdigest()
        
        # 取前6位作为密码
        return password_hash[:6]
    
    def get_current_password(self) -> str:
        """获取当前时间窗口的密码"""
        current_time = int(time.time())
        return self._generate_password(current_time)
    
    def set_secret(self, new_secret: str):
        """设置新密钥"""
        self.secret = new_secret
        logger.info("动态密码密钥已更新")


# ==================================================
# 组合验证器
# ==================================================
class CompositeVerifier(SecurityVerifier):
    """组合验证器
    
    组合多种验证方式
    """
    
    def __init__(self, verifiers: list = None):
        super().__init__()
        self.verifiers = verifiers or []
        self.require_all = True  # 是否需要所有验证都通过
    
    def add_verifier(self, verifier: SecurityVerifier):
        """添加验证器"""
        self.verifiers.append(verifier)
    
    def remove_verifier(self, verifier_type: type):
        """移除指定类型的验证器"""
        self.verifiers = [v for v in self.verifiers if not isinstance(v, verifier_type)]
    
    def _perform_verification(self, password: str, verification_data: Dict[str, Any]) -> bool:
        """执行组合验证"""
        if not self.verifiers:
            logger.warning("没有配置验证器")
            return False
        
        results = []
        for verifier in self.verifiers:
            try:
                result = verifier.verify(verification_data)
                results.append(result)
            except Exception as e:
                logger.error(f"验证器执行失败: {e}")
                results.append(False)
        
        if self.require_all:
            # 需要所有验证都通过
            return all(results)
        else:
            # 只需要任一验证通过
            return any(results)
    
    def set_require_all(self, require_all: bool):
        """设置是否需要所有验证都通过"""
        self.require_all = require_all
        logger.info(f"组合验证模式已更新: {'全部通过' if require_all else '任一通过'}")


# ==================================================
# 验证器工厂
# ==================================================
class SecurityVerifierFactory:
    """验证器工厂"""
    
    @staticmethod
    def create_verifier(verifier_type: str, **kwargs) -> SecurityVerifier:
        """创建验证器"""
        if verifier_type == 'simple':
            return SimplePasswordVerifier(**kwargs)
        elif verifier_type == 'dynamic':
            return DynamicPasswordVerifier(**kwargs)
        elif verifier_type == 'composite':
            return CompositeVerifier(**kwargs)
        else:
            raise ValueError(f"不支持的验证器类型: {verifier_type}")
    
    @staticmethod
    def get_available_types() -> list:
        """获取可用的验证器类型"""
        return ['simple', 'dynamic', 'composite']