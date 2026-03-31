#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第91节课：认证与授权

本课程介绍DeerFlow认证与授权系统，包括：
1. API认证 - JWT、OAuth2.0的实现
2. 权限模型 - 基于角色的访问控制(RBAC)
3. 会话安全 - 会话令牌的管理和刷新
4. 为DeerFlow添加认证层

作者：DeerFlow架构师训练营
"""

import time
import hashlib
import hmac
import secrets
import base64
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import unittest.mock as unittest


# ============================================================
# 第一部分：JWT认证系统
# ============================================================

class JWTError(Exception):
    """JWT相关错误的基类"""
    pass


class TokenType(Enum):
    """令牌类型"""
    ACCESS = "access"      # 访问令牌
    REFRESH = "refresh"   # 刷新令牌


@dataclass
class TokenPayload:
    """JWT令牌载荷"""
    sub: str              # 用户ID
    exp: int             # 过期时间戳
    iat: int              # 签发时间戳
    type: str            # 令牌类型
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sub": self.sub,
            "exp": self.exp,
            "iat": self.iat,
            "type": self.type,
            "roles": self.roles,
            "permissions": self.permissions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TokenPayload':
        return cls(
            sub=data["sub"],
            exp=data["exp"],
            iat=data["iat"],
            type=data["type"],
            roles=data.get("roles", []),
            permissions=data.get("permissions", [])
        )


class JWTManager:
    """
    JWT令牌管理器
    
    提供JWT令牌的生成、验证和刷新功能。
    """
    
    def __init__(self, secret_key: str, algorithm: str = "HS256",
                 access_token_expire: int = 3600, refresh_token_expire: int = 604800):
        """
        初始化JWT管理器
        
        Args:
            secret_key: JWT签名密钥
            algorithm: 签名算法
            access_token_expire: 访问令牌过期时间（秒）
            refresh_token_expire: 刷新令牌过期时间（秒）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = access_token_expire
        self.refresh_token_expire = refresh_token_expire
        
    def _base64url_encode(self, data: bytes) -> str:
        """Base64 URL安全编码"""
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
        
    def _base64url_decode(self, data: str) -> bytes:
        """Base64 URL安全解码"""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)
        
    def _sign(self, data: str) -> str:
        """HMAC签名"""
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return self._base64url_encode(signature)
        
    def _verify(self, data: str, signature: str) -> bool:
        """验证HMAC签名"""
        expected = self._sign(data)
        return hmac.compare_digest(expected, signature)
        
    def create_token(self, user_id: str, token_type: TokenType = TokenType.ACCESS,
                    roles: Optional[List[str]] = None,
                    permissions: Optional[List[str]] = None) -> str:
        """
        创建JWT令牌
        
        Args:
            user_id: 用户ID
            token_type: 令牌类型
            roles: 用户角色列表
            permissions: 用户权限列表
            
        Returns:
            JWT令牌字符串
        """
        now = int(time.time())
        
        if token_type == TokenType.ACCESS:
            expire = now + self.access_token_expire
        else:
            expire = now + self.refresh_token_expire
            
        payload = TokenPayload(
            sub=user_id,
            exp=expire,
            iat=now,
            type=token_type.value,
            roles=roles or [],
            permissions=permissions or []
        )
        
        # 构建JWT
        header = {"alg": self.algorithm, "typ": "JWT"}
        header_b64 = self._base64url_encode(json.dumps(header).encode('utf-8'))
        payload_b64 = self._base64url_encode(json.dumps(payload.to_dict()).encode('utf-8'))
        
        # 签名
        message = f"{header_b64}.{payload_b64}"
        signature = self._sign(message)
        
        return f"{message}.{signature}"
        
    def verify_token(self, token: str) -> TokenPayload:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌字符串
            
        Returns:
            TokenPayload实例
            
        Raises:
            JWTError: 验证失败
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                raise JWTError("无效的令牌格式")
                
            header_b64, payload_b64, signature = parts
            
            # 验证签名
            message = f"{header_b64}.{payload_b64}"
            if not self._verify(message, signature):
                raise JWTError("签名验证失败")
                
            # 解析载荷
            payload_data = json.loads(self._base64url_decode(payload_b64))
            payload = TokenPayload.from_dict(payload_data)
            
            # 检查过期
            now = int(time.time())
            if payload.exp < now:
                raise JWTError("令牌已过期")
                
            return payload
                
        except JWTError:
            raise
        except Exception as e:
            raise JWTError(f"令牌验证失败: {str(e)}")
            
    def refresh_access_token(self, refresh_token: str) -> str:
        """
        使用刷新令牌获取新的访问令牌
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            新的访问令牌
        """
        payload = self.verify_token(refresh_token)
        
        if payload.type != TokenType.REFRESH.value:
            raise JWTError("无效的刷新令牌")
            
        return self.create_token(
            user_id=payload.sub,
            token_type=TokenType.ACCESS,
            roles=payload.roles,
            permissions=payload.permissions
        )


# ============================================================
# 第二部分：基于角色的访问控制(RBAC)
# ============================================================

class Permission(Enum):
    """系统权限"""
    # 用户管理
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Agent管理
    AGENT_READ = "agent:read"
    AGENT_CREATE = "agent:create"
    AGENT_EXECUTE = "agent:execute"
    
    # 工具管理
    TOOL_READ = "tool:read"
    TOOL_CREATE = "tool:create"
    TOOL_DELETE = "tool:delete"
    
    # 会话管理
    SESSION_READ = "session:read"
    SESSION_CREATE = "session:create"
    SESSION_DELETE = "session:delete"
    
    # 管理员
    ADMIN = "admin:*"


# 角色定义
ROLE_PERMISSIONS = {
    "guest": [
        Permission.AGENT_READ,
        Permission.TOOL_READ,
    ],
    "user": [
        Permission.USER_READ,
        Permission.AGENT_READ,
        Permission.AGENT_EXECUTE,
        Permission.TOOL_READ,
        Permission.SESSION_READ,
        Permission.SESSION_CREATE,
    ],
    "developer": [
        Permission.USER_READ,
        Permission.AGENT_READ,
        Permission.AGENT_CREATE,
        Permission.AGENT_EXECUTE,
        Permission.TOOL_READ,
        Permission.TOOL_CREATE,
        Permission.SESSION_READ,
        Permission.SESSION_CREATE,
        Permission.SESSION_DELETE,
    ],
    "admin": [p for p in Permission],  # 所有权限
}


class Role(Enum):
    """系统角色"""
    GUEST = "guest"
    USER = "user"
    DEVELOPER = "developer"
    ADMIN = "admin"


@dataclass
class User:
    """用户"""
    id: str
    username: str
    email: str
    roles: List[str]
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None


class RBACManager:
    """
    基于角色的访问控制管理器
    
    管理用户、角色和权限的映射关系。
    """
    
    def __init__(self):
        """初始化RBAC管理器"""
        self._users: Dict[str, User] = {}
        self._role_permissions: Dict[str, List[Permission]] = ROLE_PERMISSIONS.copy()
        
    def add_user(self, user: User) -> None:
        """
        添加用户
        
        Args:
            user: User实例
        """
        self._users[user.id] = user
        
    def get_user(self, user_id: str) -> Optional[User]:
        """
        获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            User实例或None
        """
        return self._users.get(user_id)
        
    def get_user_permissions(self, user_id: str) -> List[str]:
        """
        获取用户的所有权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            权限列表
        """
        user = self.get_user(user_id)
        if not user or not user.is_active:
            return []
            
        permissions = set()
        for role in user.roles:
            if role in self._role_permissions:
                permissions.update(self._role_permissions[role])
                
        return [p.value for p in permissions]
        
    def has_permission(self, user_id: str, permission: str) -> bool:
        """
        检查用户是否有指定权限
        
        Args:
            user_id: 用户ID
            permission: 权限字符串
            
        Returns:
            是否有权限
        """
        user_perms = self.get_user_permissions(user_id)
        
        # 检查具体权限
        if permission in user_perms:
            return True
            
        # 检查通配符权限
        for perm in user_perms:
            if perm.endswith(":*"):
                prefix = perm[:-1]
                if permission.startswith(prefix):
                    return True
                    
        return False
        
    def assign_role(self, user_id: str, role: str) -> bool:
        """
        为用户分配角色
        
        Args:
            user_id: 用户ID
            role: 角色名称
            
        Returns:
            是否成功
        """
        user = self.get_user(user_id)
        if not user:
            return False
            
        if role not in self._role_permissions:
            return False
            
        if role not in user.roles:
            user.roles.append(role)
            
        return True
        
    def revoke_role(self, user_id: str, role: str) -> bool:
        """
        撤销用户角色
        
        Args:
            user_id: 用户ID
            role: 角色名称
            
        Returns:
            是否成功
        """
        user = self.get_user(user_id)
        if not user:
            return False
            
        if role in user.roles:
            user.roles.remove(role)
            return True
            
        return False


def require_permission(permission: str):
    """
    权限检查装饰器
    
    Args:
        permission: 需要的权限
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, user_id: str, *args, **kwargs):
            rbac = getattr(self, 'rbac', None)
            if not rbac:
                raise RuntimeError("RBAC管理器未初始化")
                
            if not rbac.has_permission(user_id, permission):
                raise PermissionError(f"权限不足: 需要 {permission}")
                
            return func(self, user_id, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# 第三部分：会话管理
# ============================================================

@dataclass
class Session:
    """用户会话"""
    id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_accessed: datetime
    ip_address: str
    user_agent: str
    is_valid: bool = True
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.utcnow() > self.expires_at
        
    def touch(self) -> None:
        """更新最后访问时间"""
        self.last_accessed = datetime.utcnow()


class SessionManager:
    """
    会话管理器
    
    管理用户会话的创建、验证和销毁。
    """
    
    def __init__(self, session_expire_seconds: int = 86400):
        """
        初始化会话管理器
        
        Args:
            session_expire_seconds: 会话过期时间（秒）
        """
        self.session_expire_seconds = session_expire_seconds
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()
        
    def create_session(self, user_id: str, ip_address: str = "",
                      user_agent: str = "") -> Session:
        """
        创建新会话
        
        Args:
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            Session实例
        """
        session_id = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        
        session = Session(
            id=session_id,
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(seconds=self.session_expire_seconds),
            last_accessed=now,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        with self._lock:
            self._sessions[session_id] = session
            
        return session
        
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            Session实例或None
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
        if not session:
            return None
            
        # 检查过期
        if session.is_expired():
            self.invalidate_session(session_id)
            return None
            
        return session
        
    def validate_session(self, session_id: str) -> bool:
        """
        验证会话是否有效
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否有效
        """
        session = self.get_session(session_id)
        return session is not None and session.is_valid
        
    def touch_session(self, session_id: str) -> bool:
        """
        更新会话访问时间
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.is_valid and not session.is_expired():
                session.touch()
                return True
        return False
        
    def invalidate_session(self, session_id: str) -> bool:
        """
        使会话失效
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.is_valid = False
                return True
        return False
        
    def invalidate_user_sessions(self, user_id: str) -> int:
        """
        使用户所有会话失效
        
        Args:
            user_id: 用户ID
            
        Returns:
            失效的会话数量
        """
        count = 0
        with self._lock:
            for session in self._sessions.values():
                if session.user_id == user_id and session.is_valid:
                    session.is_valid = False
                    count += 1
        return count
        
    def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话
        
        Returns:
            清理的会话数量
        """
        count = 0
        with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired()
            ]
            for sid in expired:
                del self._sessions[sid]
                count += 1
        return count


import threading


# ============================================================
# 第四部分：认证服务集成
# ============================================================

class AuthService:
    """
    认证服务
    
    整合JWT、RBAC和会话管理的完整认证服务。
    """
    
    def __init__(self, secret_key: str):
        """
        初始化认证服务
        
        Args:
            secret_key: JWT签名密钥
        """
        self.jwt_manager = JWTManager(secret_key)
        self.rbac_manager = RBACManager()
        self.session_manager = SessionManager()
        
    def register_user(self, user_id: str, username: str, email: str,
                    roles: Optional[List[str]] = None) -> User:
        """
        注册用户
        
        Args:
            user_id: 用户ID
            username: 用户名
            email: 邮箱
            roles: 角色列表
            
        Returns:
            User实例
        """
        user = User(
            id=user_id,
            username=username,
            email=email,
            roles=roles or ["user"]
        )
        self.rbac_manager.add_user(user)
        return user
        
    def authenticate(self, user_id: str, ip_address: str = "",
                   user_agent: str = "") -> Dict[str, str]:
        """
        用户认证
        
        Args:
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            包含access_token、refresh_token、session_id的字典
        """
        user = self.rbac_manager.get_user(user_id)
        if not user or not user.is_active:
            raise ValueError("用户不存在或已禁用")
            
        # 创建令牌
        access_token = self.jwt_manager.create_token(
            user_id=user_id,
            token_type=TokenType.ACCESS,
            roles=user.roles,
            permissions=self.rbac_manager.get_user_permissions(user_id)
        )
        
        refresh_token = self.jwt_manager.create_token(
            user_id=user_id,
            token_type=TokenType.REFRESH,
            roles=user.roles
        )
        
        # 创建会话
        session = self.session_manager.create_session(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # 更新最后登录
        user.last_login = datetime.utcnow()
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": session.id,
            "token_type": "Bearer",
            "expires_in": self.jwt_manager.access_token_expire
        }
        
    def verify_access_token(self, token: str) -> TokenPayload:
        """
        验证访问令牌
        
        Args:
            token: 访问令牌
            
        Returns:
            TokenPayload实例
        """
        return self.jwt_manager.verify_token(token)
        
    def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """
        刷新令牌
        
        Args:
            refresh_token: 刷新令牌
            
        Returns:
            新的令牌信息
        """
        # 验证刷新令牌
        payload = self.jwt_manager.verify_token(refresh_token)
        
        # 获取新访问令牌
        new_access_token = self.jwt_manager.refresh_access_token(refresh_token)
        
        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": self.jwt_manager.access_token_expire
        }
        
    def logout(self, session_id: str) -> bool:
        """
        登出
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功
        """
        return self.session_manager.invalidate_session(session_id)
        
    def check_permission(self, user_id: str, permission: str) -> bool:
        """
        检查权限
        
        Args:
            user_id: 用户ID
            permission: 权限
            
        Returns:
            是否有权限
        """
        return self.rbac_manager.has_permission(user_id, permission)


# ============================================================
# 第五部分：DeerFlow认证中间件
# ============================================================

class AuthMiddleware:
    """
    认证中间件
    
    用于DeerFlow的HTTP认证中间件。
    """
    
    def __init__(self, auth_service: AuthService):
        """
        初始化认证中间件
        
        Args:
            auth_service: AuthService实例
        """
        self.auth_service = auth_service
        
    def extract_token(self, authorization: str) -> Optional[str]:
        """
        从Authorization头提取令牌
        
        Args:
            Authorization头的值
            
        Returns:
            令牌字符串或None
        """
        if not authorization:
            return None
            
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return None
            
        return parts[1]
        
    def authenticate_request(self, authorization: str, 
                           session_id: str) -> Optional[Dict[str, Any]]:
        """
        认证请求
        
        Args:
            Authorization头
            session_id: 会话ID
            
        Returns:
            认证信息字典或None
        """
        # 优先使用Bearer令牌
        token = self.extract_token(authorization)
        if token:
            try:
                payload = self.auth_service.verify_access_token(token)
                return {
                    "authenticated": True,
                    "user_id": payload.sub,
                    "roles": payload.roles,
                    "permissions": payload.permissions
                }
            except JWTError:
                pass
                
        # 备选使用会话ID
        if session_id:
            session = self.auth_service.session_manager.get_session(session_id)
            if session:
                user = self.auth_service.rbac_manager.get_user(session.user_id)
                if user and user.is_active:
                    return {
                        "authenticated": True,
                        "user_id": session.user_id,
                        "roles": user.roles,
                        "permissions": self.auth_service.rbac_manager.get_user_permissions(
                            session.user_id
                        )
                    }
                    
        return None
        
    def require_auth(self, handler: Callable) -> Callable:
        """
        要求认证的装饰器
        
        Args:
            handler: 请求处理函数
            
        Returns:
            包装后的函数
        """
        @wraps(handler)
        def wrapper(request, *args, **kwargs):
            auth_info = self.authenticate_request(
                request.get("authorization", ""),
                request.get("session_id", "")
            )
            
            if not auth_info or not auth_info.get("authenticated"):
                return {
                    "error": "未认证",
                    "status": 401
                }
                
            request["auth"] = auth_info
            return handler(request, *args, **kwargs)
            
        return wrapper


# ============================================================
# 第六部分：演示与测试
# ============================================================

def run_demo():
    """演示认证授权系统"""
    print("=" * 60)
    print("DeerFlow 认证与授权系统演示")
    print("=" * 60)
    
    # 创建认证服务
    print("\n1. 创建认证服务...")
    auth_service = AuthService(secret_key="deerflow-secret-key-12345")
    
    # 注册用户
    print("\n2. 注册用户...")
    user1 = auth_service.register_user(
        user_id="user-001",
        username="alice",
        email="alice@example.com",
        roles=["user"]
    )
    user2 = auth_service.register_user(
        user_id="user-002",
        username="bob",
        email="bob@example.com",
        roles=["developer"]
    )
    admin = auth_service.register_user(
        user_id="admin-001",
        username="admin",
        email="admin@example.com",
        roles=["admin"]
    )
    print(f"   用户1: {user1.username} ({', '.join(user1.roles)})")
    print(f"   用户2: {user2.username} ({', '.join(user2.roles)})")
    print(f"   管理员: {admin.username} ({', '.join(admin.roles)})")
    
    # 用户认证
    print("\n3. 用户认证...")
    auth_result = auth_service.authenticate(
        user_id="user-001",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0"
    )
    print(f"   访问令牌: {auth_result['access_token'][:50]}...")
    print(f"   刷新令牌: {auth_result['refresh_token'][:50]}...")
    print(f"   会话ID: {auth_result['session_id'][:20]}...")
    
    # 验证令牌
    print("\n4. 验证令牌...")
    payload = auth_service.verify_access_token(auth_result['access_token'])
    print(f"   用户ID: {payload.sub}")
    print(f"   角色: {', '.join(payload.roles)}")
    print(f"   权限: {', '.join(payload.permissions)}")
    
    # 权限检查
    print("\n5. 权限检查...")
    tests = [
        ("user-001", Permission.AGENT_EXECUTE.value, True),
        ("user-001", Permission.TOOL_CREATE.value, False),
        ("user-002", Permission.TOOL_CREATE.value, True),
        ("admin-001", Permission.ADMIN.value, True),
    ]
    for user_id, perm, expected in tests:
        result = auth_service.check_permission(user_id, perm)
        status = "✓" if result == expected else "✗"
        print(f"   {status} {user_id} -> {perm}: {result} (期望: {expected})")
    
    # 令牌刷新
    print("\n6. 令牌刷新...")
    new_tokens = auth_service.refresh_token(auth_result['refresh_token'])
    print(f"   新访问令牌: {new_tokens['access_token'][:50]}...")
    
    # 登出
    print("\n7. 登出...")
    logout_result = auth_service.logout(auth_result['session_id'])
    print(f"   登出结果: {'成功' if logout_result else '失败'}")
    
    print("\n演示完成!")


def run_tests():
    """运行测试"""
    print("\n" + "=" * 60)
    print("运行单元测试")
    print("=" * 60 + "\n")
    
    # 测试JWT管理器
    print("测试1: JWT令牌管理")
    jwt = JWTManager(secret_key="test-secret")
    
    # 创建和验证访问令牌
    token = jwt.create_token(
        user_id="user-001",
        token_type=TokenType.ACCESS,
        roles=["user", "developer"],
        permissions=["read", "write"]
    )
    payload = jwt.verify_token(token)
    assert payload.sub == "user-001"
    assert payload.roles == ["user", "developer"]
    print(f"   创建令牌成功: {token[:30]}...")
    print(f"   验证成功: user={payload.sub}, roles={payload.roles}")
    
    # 刷新令牌
    refresh_token = jwt.create_token(
        user_id="user-001",
        token_type=TokenType.REFRESH
    )
    new_access = jwt.refresh_access_token(refresh_token)
    assert new_access != token
    print("   刷新令牌成功")
    print("✓ JWT测试通过\n")
    
    # 测试RBAC
    print("测试2: RBAC权限管理")
    rbac = RBACManager()
    
    user = User(
        id="test-user",
        username="testuser",
        email="test@test.com",
        roles=["user"]
    )
    rbac.add_user(user)
    
    # 检查权限
    assert rbac.has_permission("test-user", "agent:read")
    assert rbac.has_permission("test-user", "session:create")
    assert not rbac.has_permission("test-user", "admin:*")
    print(f"   用户权限: {rbac.get_user_permissions('test-user')}")
    
    # 分配角色
    rbac.assign_role("test-user", "developer")
    assert "developer" in rbac.get_user("test-user").roles
    assert rbac.has_permission("test-user", "tool:create")
    print("   分配developer角色成功")
    print("✓ RBAC测试通过\n")
    
    # 测试会话管理
    print("测试3: 会话管理")
    session_mgr = SessionManager(session_expire_seconds=3600)
    
    session = session_mgr.create_session(
        user_id="user-001",
        ip_address="127.0.0.1"
    )
    assert session_mgr.validate_session(session.id)
    print(f"   创建会话: {session.id[:20]}...")
    
    session_mgr.invalidate_session(session.id)
    assert not session_mgr.validate_session(session.id)
    print("   会话失效成功")
    print("✓ 会话测试通过\n")
    
    # 测试认证服务
    print("测试4: 认证服务集成")
    auth = AuthService(secret_key="test-key")
    
    auth.register_user("user1", "user1", "user1@test.com", ["user"])
    result = auth.authenticate("user1")
    
    assert "access_token" in result
    assert "refresh_token" in result
    assert "session_id" in result
    print(f"   认证成功: token={result['access_token'][:20]}...")
    
    payload = auth.verify_access_token(result['access_token'])
    assert payload.sub == "user1"
    print("   令牌验证成功")
    print("✓ 认证服务测试通过\n")
    
    # 测试认证中间件
    print("测试5: 认证中间件")
    middleware = AuthMiddleware(auth)
    
    # 带有效令牌
    auth_info = middleware.authenticate_request(
        authorization=f"Bearer {result['access_token']}",
        session_id=""
    )
    assert auth_info is not None
    assert auth_info["authenticated"] == True
    assert auth_info["user_id"] == "user1"
    print("   有效令牌认证成功")
    
    # 无认证信息
    auth_info = middleware.authenticate_request("", "")
    assert auth_info is None
    print("   无认证信息返回None")
    print("✓ 认证中间件测试通过\n")
    
    print("=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        run_tests()
    else:
        run_demo()
