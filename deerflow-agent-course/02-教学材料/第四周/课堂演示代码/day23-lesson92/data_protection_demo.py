#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第92节课：数据保护

本课程介绍DeerFlow数据保护系统，包括：
1. 敏感数据过滤 - 日志和错误信息中的敏感信息脱敏
2. 加密存储 - 配置文件和内存数据的加密
3. 数据保留策略 - 自动清理过期数据
4. 数据保护最佳实践

作者：DeerFlow架构师训练营
"""

import re
import hashlib
import hmac
import base64
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import unittest.mock as unittest


# ============================================================
# 第一部分：敏感数据过滤
# ============================================================

class SensitiveDataType(Enum):
    """敏感数据类型"""
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    IP_ADDRESS = "ip_address"


@dataclass
class SensitivePattern:
    """敏感数据模式"""
    data_type: SensitiveDataType
    pattern: re.Pattern
    replacement: str
    
    @classmethod
    def get_default_patterns(cls) -> List['SensitivePattern']:
        """获取默认敏感数据模式"""
        return [
            SensitivePattern(
                data_type=SensitiveDataType.EMAIL,
                pattern=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                replacement="***@***.***"
            ),
            SensitivePattern(
                data_type=SensitiveDataType.PHONE,
                pattern=re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'),
                replacement="***-***-****"
            ),
            SensitivePattern(
                data_type=SensitiveDataType.CREDIT_CARD,
                pattern=re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
                replacement="****-****-****-****"
            ),
            SensitivePattern(
                data_type=SensitiveDataType.SSN,
                pattern=re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'),
                replacement="***-**-****"
            ),
            SensitivePattern(
                data_type=SensitiveDataType.PASSWORD,
                pattern=re.compile(r'(?i)(password|passwd|pwd)[=:\s]\S+', re.IGNORECASE),
                replacement="password=***"
            ),
            SensitivePattern(
                data_type=SensitiveDataType.API_KEY,
                pattern=re.compile(r'(?i)(api[_-]?key|apikey)[=:\s]\S+', re.IGNORECASE),
                replacement="api_key=***"
            ),
            SensitivePattern(
                data_type=SensitiveDataType.TOKEN,
                pattern=re.compile(r'(?i)(token|access_token|refresh_token)[=:\s][A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+', re.IGNORECASE),
                replacement="token=***"
            ),
            SensitivePattern(
                data_type=SensitiveDataType.IP_ADDRESS,
                pattern=re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
                replacement="***.***.***.***"
            ),
        ]


class SensitiveDataFilter:
    """
    敏感数据过滤器
    
    对日志和错误信息进行敏感信息脱敏处理。
    """
    
    def __init__(self, custom_patterns: Optional[List[SensitivePattern]] = None):
        """
        初始化敏感数据过滤器
        
        Args:
            custom_patterns: 自定义敏感数据模式
        """
        self.patterns = custom_patterns or SensitivePattern.get_default_patterns()
        
    def filter_text(self, text: str) -> str:
        """
        过滤文本中的敏感信息
        
        Args:
            text: 原始文本
            
        Returns:
            脱敏后的文本
        """
        result = text
        for pattern in self.patterns:
            result = pattern.pattern.sub(pattern.replacement, result)
        return result
        
    def filter_dict(self, data: Dict[str, Any], 
                   key_whitelist: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        过滤字典中的敏感信息
        
        Args:
            data: 原始字典
            key_whitelist: 键白名单（不进行过滤的键）
            
        Returns:
            脱敏后的字典
        """
        key_whitelist = key_whitelist or ["username", "name", "id"]
        result = {}
        
        for key, value in data.items():
            # 检查是否在白名单中
            if key.lower() in [k.lower() for k in key_whitelist]:
                result[key] = value
            elif isinstance(value, str):
                result[key] = self.filter_text(value)
            elif isinstance(value, dict):
                result[key] = self.filter_dict(value, key_whitelist)
            elif isinstance(value, list):
                result[key] = [
                    self.filter_dict(item, key_whitelist) if isinstance(item, dict)
                    else self.filter_text(str(item)) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
                
        return result
        
    def filter_log(self, level: str, message: str, 
                  extra: Optional[Dict] = None) -> Dict[str, Any]:
        """
        过滤日志
        
        Args:
            level: 日志级别
            message: 日志消息
            extra: 额外字段
            
        Returns:
            过滤后的日志字典
        """
        log = {
            "level": level,
            "message": self.filter_text(message),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if extra:
            log["extra"] = self.filter_dict(extra)
            
        return log


# ============================================================
# 第二部分：加密存储
# ============================================================

class EncryptionManager:
    """
    加密管理器
    
    提供对称加密功能，用于保护敏感数据。
    """
    
    def __init__(self, master_password: str, salt: Optional[bytes] = None):
        """
        初始化加密管理器
        
        Args:
            master_password: 主密码
            salt: 盐值
        """
        self.salt = salt or os.urandom(16)
        self.key = self._derive_key(master_password)
        self.cipher = Fernet(self.key)
        
    def _derive_key(self, password: str) -> bytes:
        """
        从密码派生密钥
        
        Args:
            password: 密码
            
        Returns:
            加密密钥
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
    def encrypt(self, data: str) -> str:
        """
        加密数据
        
        Args:
            data: 原始数据
            
        Returns:
            加密后的数据（Base64编码）
        """
        encrypted = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
        
    def decrypt(self, encrypted_data: str) -> str:
        """
        解密数据
        
        Args:
            encrypted_data: 加密后的数据
            
        Returns:
            原始数据
        """
        decoded = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = self.cipher.decrypt(decoded)
        return decrypted.decode()
        
    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> tuple:
        """
        哈希密码
        
        Args:
            password: 密码
            salt: 盐值
            
        Returns:
            (哈希值, 盐值)元组
        """
        salt = salt or os.urandom(32)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return base64.b64encode(hashed).decode(), base64.b64encode(salt).decode()
        
    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """
        验证密码
        
        Args:
            password: 密码
            hashed: 哈希值
            salt: 盐值
            
        Returns:
            是否匹配
        """
        salt_decoded = base64.b64decode(salt.encode())
        hashed_input = hashlib.pbkdf2_hmac('sha256', password.encode(), salt_decoded, 100000)
        return hmac.compare_digest(base64.b64encode(hashed_input).decode(), hashed)


class SecureConfig:
    """
    安全配置存储
    
    加密存储敏感配置信息。
    """
    
    def __init__(self, encryption_manager: EncryptionManager, storage_path: str):
        """
        初始化安全配置存储
        
        Args:
            encryption_manager: 加密管理器
            storage_path: 存储路径
        """
        self.encryption = encryption_manager
        self.storage_path = storage_path
        self._config: Dict[str, Any] = {}
        
    def set(self, key: str, value: Any, encrypt: bool = False) -> None:
        """
        设置配置
        
        Args:
            key: 配置键
            value: 配置值
            encrypt: 是否加密存储
        """
        if encrypt and isinstance(value, str):
            value = self.encryption.encrypt(value)
        self._config[key] = value
        
    def get(self, key: str, decrypt: bool = False) -> Any:
        """
        获取配置
        
        Args:
            key: 配置键
            decrypt: 是否解密
            
        Returns:
            配置值
        """
        value = self._config.get(key)
        if decrypt and isinstance(value, str):
            value = self.encryption.decrypt(value)
        return value
        
    def save(self) -> None:
        """保存配置到文件"""
        with open(self.storage_path, 'w') as f:
            json.dump(self._config, f)
            
    def load(self) -> None:
        """从文件加载配置"""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r') as f:
                self._config = json.load(f)


# ============================================================
# 第三部分：数据保留策略
# ============================================================

@dataclass
class RetentionPolicy:
    """数据保留策略"""
    name: str
    max_age_days: int
    max_size_mb: int
    cleanup_enabled: bool = True
    
    
class DataRetentionManager:
    """
    数据保留管理器
    
    管理数据的自动清理和归档。
    """
    
    DEFAULT_POLICIES = {
        "session": RetentionPolicy("session", max_age_days=30, max_size_mb=100),
        "logs": RetentionPolicy("logs", max_age_days=7, max_size_mb=500),
        "cache": RetentionPolicy("cache", max_age_days=1, max_size_mb=50),
        "backups": RetentionPolicy("backups", max_age_days=90, max_size_mb=10000),
    }
    
    def __init__(self, storage_root: str):
        """
        初始化数据保留管理器
        
        Args:
            storage_root: 存储根目录
        """
        self.storage_root = storage_root
        self.policies = self.DEFAULT_POLICIES.copy()
        
    def add_policy(self, policy: RetentionPolicy) -> None:
        """
        添加保留策略
        
        Args:
            policy: 保留策略
        """
        self.policies[policy.name] = policy
        
    def should_cleanup(self, data_type: str, file_path: str) -> tuple:
        """
        检查数据是否需要清理
        
        Args:
            data_type: 数据类型
            file_path: 文件路径
            
        Returns:
            (是否需要清理, 原因)元组
        """
        if data_type not in self.policies:
            return False, "no policy"
            
        policy = self.policies[data_type]
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return False, "file not found"
            
        # 检查修改时间
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        age_days = (datetime.now() - mtime).days
        
        if age_days > policy.max_age_days:
            return True, f"age {age_days} > {policy.max_age_days}"
            
        # 检查文件大小
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > policy.max_size_mb:
            return True, f"size {size_mb:.1f}MB > {policy.max_size_mb}MB"
            
        return False, "ok"
        
    def cleanup_data_type(self, data_type: str) -> Dict[str, Any]:
        """
        清理指定类型的数据
        
        Args:
            data_type: 数据类型
            
        Returns:
            清理结果统计
        """
        if data_type not in self.policies:
            return {"error": "unknown type", "cleaned": 0}
            
        policy = self.policies[data_type]
        data_dir = os.path.join(self.storage_root, data_type)
        
        if not os.path.exists(data_dir):
            return {"error": "directory not found", "cleaned": 0}
            
        cleaned_count = 0
        cleaned_size = 0
        
        for filename in os.listdir(data_dir):
            file_path = os.path.join(data_dir, filename)
            
            should_clean, reason = self.should_cleanup(data_type, file_path)
            
            if should_clean:
                size = os.path.getsize(file_path)
                try:
                    os.remove(file_path)
                    cleaned_count += 1
                    cleaned_size += size
                except Exception:
                    pass
                    
        return {
            "type": data_type,
            "cleaned_files": cleaned_count,
            "cleaned_size_mb": round(cleaned_size / (1024 * 1024), 2),
            "policy": {
                "max_age_days": policy.max_age_days,
                "max_size_mb": policy.max_size_mb
            }
        }
        
    def cleanup_all(self) -> List[Dict[str, Any]]:
        """
        清理所有类型的数据
        
        Returns:
            各类型清理结果列表
        """
        results = []
        for data_type in self.policies.keys():
            result = self.cleanup_data_type(data_type)
            results.append(result)
        return results


# ============================================================
# 第四部分：审计日志
# ============================================================

@dataclass
class AuditEvent:
    """审计事件"""
    id: str
    timestamp: datetime
    event_type: str
    user_id: str
    action: str
    resource: str
    result: str
    details: Optional[Dict] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "result": self.result,
            "details": self.details
        }


class AuditLogger:
    """
    审计日志记录器
    
    记录所有敏感操作的审计日志。
    """
    
    def __init__(self, log_path: str, retention_days: int = 90):
        """
        初始化审计日志记录器
        
        Args:
            log_path: 日志路径
            retention_days: 保留天数
        """
        self.log_path = log_path
        self.retention_days = retention_days
        self._ensure_log_directory()
        
    def _ensure_log_directory(self) -> None:
        """确保日志目录存在"""
        log_dir = os.path.dirname(self.log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
    def log(self, event_type: str, user_id: str, action: str,
            resource: str, result: str, 
            details: Optional[Dict] = None) -> None:
        """
        记录审计事件
        
        Args:
            event_type: 事件类型
            user_id: 用户ID
            action: 操作
            resource: 资源
            result: 结果
            details: 详细信息
        """
        import secrets
        
        event = AuditEvent(
            id=secrets.token_hex(8),
            timestamp=datetime.utcnow(),
            event_type=event_type,
            user_id=user_id,
            action=action,
            resource=resource,
            result=result,
            details=details
        )
        
        # 写入日志文件
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + '\n')
            
    def query(self, user_id: Optional[str] = None,
             event_type: Optional[str] = None,
             start_date: Optional[datetime] = None,
             end_date: Optional[datetime] = None,
             limit: int = 100) -> List[AuditEvent]:
        """
        查询审计日志
        
        Args:
            user_id: 用户ID过滤
            event_type: 事件类型过滤
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制
            
        Returns:
            审计事件列表
        """
        events = []
        
        if not os.path.exists(self.log_path):
            return events
            
        with open(self.log_path, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    
                    # 应用过滤器
                    if user_id and data.get("user_id") != user_id:
                        continue
                    if event_type and data.get("event_type") != event_type:
                        continue
                    if start_date:
                        event_time = datetime.fromisoformat(data["timestamp"])
                        if event_time < start_date:
                            continue
                    if end_date:
                        event_time = datetime.fromisoformat(data["timestamp"])
                        if event_time > end_date:
                            continue
                            
                    events.append(AuditEvent(
                        id=data["id"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        event_type=data["event_type"],
                        user_id=data["user_id"],
                        action=data["action"],
                        resource=data["resource"],
                        result=data["result"],
                        details=data.get("details")
                    ))
                    
                    if len(events) >= limit:
                        break
                        
                except Exception:
                    continue
                    
        return events


# ============================================================
# 第五部分：演示与测试
# ============================================================

def run_demo():
    """演示数据保护系统"""
    print("=" * 60)
    print("DeerFlow 数据保护系统演示")
    print("=" * 60)
    
    # 1. 敏感数据过滤
    print("\n1. 敏感数据过滤...")
    filter = SensitiveDataFilter()
    
    test_text = """
    用户信息: email=test@example.com, phone=123-456-7890
    密码: password=mysecretpass
    API密钥: api_key=sk_live_abc123
    信用卡: 1234-5678-9012-3456
    IP地址: 192.168.1.100
    """
    filtered = filter.filter_text(test_text)
    print(f"   原始: test@example.com")
    print(f"   过滤: {filtered.split('@')[0]}@***.***")
    
    # 2. 加密存储
    print("\n2. 加密存储...")
    enc = EncryptionManager("my-master-password")
    encrypted = enc.encrypt("sensitive-api-key-12345")
    decrypted = enc.decrypt(encrypted)
    print(f"   原文: sensitive-api-key-12345")
    print(f"   加密: {encrypted[:30]}...")
    print(f"   解密: {decrypted}")
    
    # 密码哈希
    hashed, salt = EncryptionManager.hash_password("mypassword")
    verified = EncryptionManager.verify_password("mypassword", hashed, salt)
    print(f"   密码验证: {'成功' if verified else '失败'}")
    
    # 3. 数据保留策略
    print("\n3. 数据保留策略...")
    retention = DataRetentionManager("/tmp/deerflow-test")
    
    policy = retention.policies["session"]
    print(f"   会话策略: 保留{policy.max_age_days}天, 最大{policy.max_size_mb}MB")
    
    # 4. 审计日志
    print("\n4. 审计日志...")
    audit = AuditLogger("/tmp/audit-test.log")
    
    audit.log(
        event_type="auth",
        user_id="user-001",
        action="login",
        resource="/api/auth/login",
        result="success",
        details={"ip": "192.168.1.1"}
    )
    audit.log(
        event_type="data",
        user_id="user-001",
        action="read",
        resource="/api/users",
        result="success"
    )
    
    events = audit.query(user_id="user-001")
    print(f"   查询到 {len(events)} 条审计记录")
    
    print("\n演示完成!")


def run_tests():
    """运行测试"""
    print("\n" + "=" * 60)
    print("运行单元测试")
    print("=" * 60 + "\n")
    
    # 测试1: 敏感数据过滤
    print("测试1: 敏感数据过滤")
    f = SensitiveDataFilter()
    
    text = "联系邮箱: test@example.com, 电话: 123-456-7890"
    filtered = f.filter_text(text)
    assert "***@***.***" in filtered
    assert "***-***-****" in filtered
    print(f"   原文: {text}")
    print(f"   过滤: {filtered}")
    print("✓ 敏感数据过滤测试通过\n")
    
    # 测试2: 字典过滤
    print("测试2: 字典数据过滤")
    data = {
        "username": "john",
        "email": "john@example.com",
        "password": "secret123"
    }
    filtered = f.filter_dict(data)
    assert filtered["username"] == "john"
    assert filtered["email"] == "***@***.***"
    print(f"   原始: {data}")
    print(f"   过滤: {filtered}")
    print("✓ 字典过滤测试通过\n")
    
    # 测试3: 加密解密
    print("测试3: 加密存储")
    enc = EncryptionManager("password123")
    original = "Secret API Key"
    encrypted = enc.encrypt(original)
    decrypted = enc.decrypt(encrypted)
    assert decrypted == original
    print(f"   原文: {original}")
    print(f"   密文: {encrypted[:30]}...")
    print("✓ 加密测试通过\n")
    
    # 测试4: 密码哈希
    print("测试4: 密码哈希")
    hashed, salt = EncryptionManager.hash_password("mypassword")
    assert EncryptionManager.verify_password("mypassword", hashed, salt)
    assert not EncryptionManager.verify_password("wrongpassword", hashed, salt)
    print("   密码验证成功")
    print("✓ 密码哈希测试通过\n")
    
    # 测试5: 数据保留策略
    print("测试5: 数据保留策略")
    retention = DataRetentionManager("/tmp/test")
    policy = retention.policies["logs"]
    assert policy.name == "logs"
    assert policy.max_age_days == 7
    print(f"   日志保留策略: {policy.max_age_days}天")
    print("✓ 数据保留策略测试通过\n")
    
    # 测试6: 审计日志
    print("测试6: 审计日志")
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        audit_log_path = tmp.name
        
    audit = AuditLogger(audit_log_path)
    audit.log("test", "user1", "action", "resource", "success")
    
    events = audit.query(user_id="user1")
    assert len(events) == 1
    assert events[0].user_id == "user1"
    print(f"   记录数: {len(events)}")
    
    os.unlink(audit_log_path)
    print("✓ 审计日志测试通过\n")
    
    print("=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        run_tests()
    else:
        run_demo()
