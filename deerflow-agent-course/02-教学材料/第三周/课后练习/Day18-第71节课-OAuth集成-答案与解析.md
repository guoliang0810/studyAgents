# 📚 Day 18 第71节课：OAuth集成 - 答案与解析

## 🎯 答案解析概览
本文档提供课后练习的参考答案、详细解析和最佳实践建议。每个任务包含多种实现方案，并解释设计决策和安全考虑。

## 📁 文件结构
```
答案与解析/
├── task1_oauth_config/          # 任务1答案
├── task2_oauth_token/           # 任务2答案  
├── task3_encrypted_storage/     # 任务3答案
├── task4_pkce_support/          # 任务4答案
├── task5_github_tool/           # 任务5答案
├── task6_error_handling/        # 任务6答案
└── common_issues/               # 常见问题解答
```

## 🔧 任务1：理解OAuth配置类

### 问题答案
1. **为什么需要验证配置的完整性？**
   - **安全性**: 缺少关键配置可能导致运行时错误或安全漏洞
   - **早期失败**: 在初始化阶段发现问题，避免在OAuth流程中失败
   - **调试友好**: 明确的错误信息帮助快速定位配置问题
   - **合规性**: 确保配置符合OAuth 2.0规范要求

2. **`client_secret`为什么不能为空？**
   - **身份验证**: client_secret用于证明客户端身份，防止冒充攻击
   - **令牌安全**: 保护令牌交换过程，只有合法客户端能获取令牌
   - **协议要求**: OAuth 2.0规范要求客户端认证
   - **例外情况**: 公共客户端（如移动应用）可能不使用client_secret，但需要其他安全措施（如PKCE）

3. **`redirect_uri`在OAuth流程中的作用是什么？**
   - **安全重定向**: 确保授权码只发送到预先注册的URI，防止重定向攻击
   - **状态恢复**: 应用在回调中恢复授权流程状态
   - **用户体验**: 用户授权后无缝返回应用
   - **协议强制**: OAuth服务商严格验证redirect_uri，必须完全匹配

### 测试代码实现
```python
import pytest

def test_oauth_config_validation():
    """测试OAuth配置验证"""
    
    # 测试有效配置
    config = OAuthConfig(
        client_id="valid_client",
        client_secret="valid_secret",
        authorization_endpoint="https://example.com/auth",
        token_endpoint="https://example.com/token",
        redirect_uri="http://localhost:8080/callback",
        scopes=["read", "write"],
    )
    assert config.client_id == "valid_client"
    
    # 测试空客户端ID
    with pytest.raises(ValueError, match="client_id不能为空"):
        OAuthConfig(
            client_id="",
            client_secret="test",
            authorization_endpoint="https://example.com/auth",
            token_endpoint="https://example.com/token",
            redirect_uri="http://localhost:8080/callback",
            scopes=["read"],
        )
    
    # 测试空作用域
    with pytest.raises(ValueError, match="scopes不能为空"):
        OAuthConfig(
            client_id="test",
            client_secret="test",
            authorization_endpoint="https://example.com/auth",
            token_endpoint="https://example.com/token",
            redirect_uri="http://localhost:8080/callback",
            scopes=[],
        )
    
    print("✅ 所有配置验证测试通过")

# 运行测试
if __name__ == "__main__":
    test_oauth_config_validation()
```

### 最佳实践
1. **配置来源**: 从环境变量或配置文件加载敏感信息，避免硬编码
2. **验证时机**: 在类初始化时验证，而不是在方法调用时
3. **错误信息**: 提供具体、可操作的错误信息
4. **默认值**: 为可选参数提供合理的默认值

---

## 🔧 任务2：实现OAuthToken类的方法

### 完整实现
```python
import json
import time
from typing import Optional, Dict, Any

class OAuthToken:
    """OAuth令牌类（增强版）"""
    
    def __init__(
        self,
        access_token: str,
        token_type: str = "Bearer",
        expires_in: Optional[int] = None,
        refresh_token: Optional[str] = None,
        scope: Optional[str] = None
    ):
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.refresh_token = refresh_token
        self.scope = scope
        self.created_at = time.time()
    
    def is_expired(self) -> bool:
        """检查令牌是否过期"""
        if self.expires_in is None:
            return False
        
        elapsed = time.time() - self.created_at
        # 提前60秒认为过期，避免临界时间问题
        return elapsed >= self.expires_in - 60
    
    def time_until_expiry(self) -> Optional[float]:
        """
        返回距离令牌过期的剩余时间（秒）
        
        返回:
            - 正数: 剩余秒数
            - 0或负数: 已过期
            - None: 永不过期
        """
        if self.expires_in is None:
            return None
        
        elapsed = time.time() - self.created_at
        remaining = self.expires_in - elapsed
        
        # 提前60秒缓冲
        return remaining - 60 if remaining > 60 else 0
    
    def to_json(self) -> str:
        """将令牌转换为JSON字符串"""
        token_dict = {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
            "created_at": self.created_at,
        }
        
        # 过滤None值，使JSON更简洁
        filtered_dict = {k: v for k, v in token_dict.items() if v is not None}
        return json.dumps(filtered_dict, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "OAuthToken":
        """从JSON字符串创建令牌"""
        try:
            token_data = json.loads(json_str)
            
            # 确保必要字段存在
            if "access_token" not in token_data:
                raise ValueError("JSON缺少access_token字段")
            
            token = cls(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                refresh_token=token_data.get("refresh_token"),
                scope=token_data.get("scope"),
            )
            
            # 恢复创建时间戳（如果存在）
            if "created_at" in token_data:
                token.created_at = token_data["created_at"]
            
            return token
            
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}")
        except Exception as e:
            raise ValueError(f"创建令牌失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（兼容原有方法）"""
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "scope": self.scope,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthToken":
        """从字典创建令牌（兼容原有方法）"""
        token = cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in"),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
        )
        token.created_at = data.get("created_at", time.time())
        return token
    
    def __repr__(self) -> str:
        expires_info = f", expires_in={self.expires_in}" if self.expires_in else ""
        refresh_info = f", has_refresh_token={bool(self.refresh_token)}"
        remaining = self.time_until_expiry()
        remaining_info = f", remaining={remaining:.1f}s" if remaining is not None else ""
        
        return f"OAuthToken(access_token={self.access_token[:8]}...{expires_info}{refresh_info}{remaining_info})"
```

### 单元测试
```python
import pytest
import asyncio

async def test_enhanced_oauth_token():
    """测试增强的OAuthToken类"""
    
    print("🧪 测试OAuthToken增强功能...")
    
    # 测试令牌创建和基本属性
    token = OAuthToken(
        access_token="test_access_token_123",
        token_type="Bearer",
        expires_in=3600,
        refresh_token="test_refresh_token_456",
        scope="user:read repo:write",
    )
    
    assert token.access_token == "test_access_token_123"
    assert token.token_type == "Bearer"
    assert token.expires_in == 3600
    assert token.refresh_token == "test_refresh_token_456"
    assert token.scope == "user:read repo:write"
    
    # 测试过期检查（新令牌不应该过期）
    assert not token.is_expired()
    
    # 测试剩余时间计算
    remaining = token.time_until_expiry()
    assert remaining is not None
    # 新令牌剩余时间应该接近3600-60=3540秒
    assert 3530 < remaining < 3550
    
    # 测试JSON序列化
    json_str = token.to_json()
    assert "access_token" in json_str
    assert "test_access_token_123" in json_str
    
    # 测试JSON反序列化
    token2 = OAuthToken.from_json(json_str)
    assert token2.access_token == token.access_token
    assert token2.expires_in == token.expires_in
    assert token2.refresh_token == token.refresh_token
    
    # 测试永不过期令牌
    permanent_token = OAuthToken(
        access_token="permanent_token",
        expires_in=None,  # 永不过期
    )
    assert not permanent_token.is_expired()
    assert permanent_token.time_until_expiry() is None
    
    # 测试已过期令牌
    expired_token = OAuthToken(
        access_token="expired_token",
        expires_in=1,  # 1秒后过期
    )
    await asyncio.sleep(1.5)  # 等待令牌过期
    assert expired_token.is_expired()
    remaining = expired_token.time_until_expiry()
    assert remaining == 0  # 已过期
    
    # 测试错误处理
    invalid_json = "{invalid json}"
    try:
        OAuthToken.from_json(invalid_json)
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "JSON解析失败" in str(e)
    
    # 测试缺少必要字段
    incomplete_json = '{"token_type": "Bearer"}'
    try:
        OAuthToken.from_json(incomplete_json)
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "缺少access_token字段" in str(e)
    
    print("✅ OAuthToken增强功能测试通过")
    return True

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_enhanced_oauth_token())
```

### 设计要点
1. **时间缓冲**: 提前60秒认为过期，避免API调用时令牌刚好过期
2. **None处理**: 明确区分"永不过期"和"未知有效期"
3. **JSON兼容**: 保持与原有to_dict/from_dict方法的兼容性
4. **错误恢复**: 提供清晰的错误信息，便于调试

---

## 🔧 任务3：实现TokenStorage的加密存储

### 完整实现（使用cryptography库）
```python
import json
import base64
import os
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class EncryptedTokenStorage(TokenStorage):
    """
    加密的令牌存储
    
    使用Fernet对称加密保护令牌数据，密钥从用户提供的密码派生。
    生产环境应考虑使用硬件安全模块或云密钥管理服务。
    """
    
    def __init__(self, storage_path: str, password: str, salt: bytes = None):
        """
        初始化加密存储
        
        参数:
            storage_path: 存储文件路径
            password: 加密密码（应足够复杂）
            salt: 加密盐（可选，不提供则自动生成）
        """
        super().__init__(storage_path)
        
        # 生成或使用提供的盐
        self.salt = salt or os.urandom(16)
        
        # 从密码派生加密密钥
        self.fernet = self._derive_fernet_key(password)
        
        # 保存盐到文件头（如果提供了新盐）
        if salt is None:
            self._save_salt()
    
    def _derive_fernet_key(self, password: str) -> Fernet:
        """从密码派生Fernet密钥"""
        # 使用PBKDF2派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def _save_salt(self) -> None:
        """保存盐到文件（单独文件或组合文件）"""
        salt_file = self.storage_path + ".salt"
        with open(salt_file, "wb") as f:
            f.write(self.salt)
    
    def _load_salt(self) -> Optional[bytes]:
        """从文件加载盐"""
        salt_file = self.storage_path + ".salt"
        try:
            with open(salt_file, "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None
    
    async def save_token(self, token: OAuthToken) -> None:
        """加密后保存令牌"""
        try:
            # 将令牌转换为JSON
            token_dict = token.to_dict()
            token_json = json.dumps(token_dict, ensure_ascii=False)
            
            # 加密JSON数据
            encrypted_data = self.fernet.encrypt(token_json.encode())
            
            # 保存加密数据（Base64编码便于存储）
            encoded_data = base64.b64encode(encrypted_data).decode()
            
            with open(self.storage_path, "w", encoding="utf-8") as f:
                f.write(encoded_data)
            
            logger.info(f"令牌已加密保存到 {self.storage_path}")
            
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"保存加密令牌失败: {e}")
            raise TokenStorageError(f"保存加密令牌失败: {e}")
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise TokenStorageError(f"加密失败: {e}")
    
    async def get_token(self) -> Optional[OAuthToken]:
        """解密后加载令牌"""
        try:
            # 检查文件是否存在
            if not os.path.exists(self.storage_path):
                logger.warning(f"加密令牌文件不存在: {self.storage_path}")
                return None
            
            # 读取加密数据
            with open(self.storage_path, "r", encoding="utf-8") as f:
                encoded_data = f.read()
            
            # Base64解码
            encrypted_data = base64.b64decode(encoded_data)
            
            # 解密数据
            decrypted_json = self.fernet.decrypt(encrypted_data).decode()
            
            # 解析JSON
            token_dict = json.loads(decrypted_json)
            
            # 创建令牌对象
            token = OAuthToken.from_dict(token_dict)
            
            logger.info(f"从 {self.storage_path} 解密并加载令牌")
            return token
            
        except FileNotFoundError:
            logger.warning(f"加密令牌文件不存在: {self.storage_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"解密后JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"解密失败: {e}")
            # 安全考虑：解密失败时删除可能损坏的文件
            try:
                os.remove(self.storage_path)
                logger.warning(f"删除损坏的加密文件: {self.storage_path}")
            except:
                pass
            return None
    
    async def clear_token(self) -> None:
        """清除存储的令牌和盐文件"""
        try:
            # 删除主文件
            if os.path.exists(self.storage_path):
                os.remove(self.storage_path)
                logger.info(f"加密令牌文件已删除: {self.storage_path}")
            
            # 删除盐文件
            salt_file = self.storage_path + ".salt"
            if os.path.exists(salt_file):
                os.remove(salt_file)
                logger.info(f"盐文件已删除: {salt_file}")
                
        except Exception as e:
            logger.error(f"清除加密令牌失败: {e}")
            raise TokenStorageError(f"清除加密令牌失败: {e}")
```

### 简化实现（使用简单加密）
```python
import base64
import hashlib
from Crypto.Cipher import AES  # 需要安装pycryptodome
from Crypto.Util.Padding import pad, unpad

class SimpleEncryptedTokenStorage(TokenStorage):
    """简单的AES加密存储（用于理解加密原理）"""
    
    def __init__(self, storage_path: str, encryption_key: str):
        super().__init__(storage_path)
        
        # 从密钥生成固定长度的AES密钥
        key_hash = hashlib.sha256(encryption_key.encode()).digest()
        self.key = key_hash[:16]  # AES-128使用16字节密钥
        
        # 固定IV（简化示例，生产环境应使用随机IV）
        self.iv = b"0123456789abcdef"
    
    def _encrypt(self, data: str) -> str:
        """AES加密数据"""
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded_data = pad(data.encode(), AES.block_size)
        encrypted = cipher.encrypt(padded_data)
        return base64.b64encode(encrypted).decode()
    
    def _decrypt(self, encrypted_data: str) -> str:
        """AES解密数据"""
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted_padded = cipher.decrypt(encrypted_bytes)
        decrypted = unpad(decrypted_padded, AES.block_size)
        return decrypted.decode()
    
    async def save_token(self, token: OAuthToken) -> None:
        """加密后保存令牌"""
        token_json = token.to_json()
        encrypted_json = self._encrypt(token_json)
        
        with open(self.storage_path, "w", encoding="utf-8") as f:
            f.write(encrypted_json)
        
        logger.info(f"令牌已简单加密保存到 {self.storage_path}")
    
    async def get_token(self) -> Optional[OAuthToken]:
        """解密后加载令牌"""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                encrypted_json = f.read()
            
            decrypted_json = self._decrypt(encrypted_json)
            token = OAuthToken.from_json(decrypted_json)
            
            logger.info(f"从 {self.storage_path} 解密并加载令牌")
            return token
            
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"简单解密失败: {e}")
            return None
```

### 测试代码
```python
import tempfile
import os

async def test_encrypted_token_storage():
    """测试加密令牌存储"""
    print("🧪 测试加密令牌存储...")
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    
    try:
        # 测试Fernet加密存储
        password = "strong_password_123!@#"
        storage = EncryptedTokenStorage(temp_path, password)
        
        # 创建测试令牌
        token = OAuthToken(
            access_token="encrypted_test_token",
            expires_in=3600,
            refresh_token="encrypted_refresh_token",
        )
        
        # 保存加密令牌
        await storage.save_token(token)
        
        # 验证文件已加密（不是明文JSON）
        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查内容不是明文JSON
        assert "encrypted_test_token" not in content
        assert "access_token" not in content
        
        # 加载并解密令牌
        loaded_token = await storage.get_token()
        assert loaded_token is not None
        assert loaded_token.access_token == token.access_token
        assert loaded_token.refresh_token == token.refresh_token
        
        # 测试清除
        await storage.clear_token()
        assert not os.path.exists(temp_path)
        
        print("✅ 加密令牌存储测试通过")
        return True
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        salt_file = temp_path + ".salt"
        if os.path.exists(salt_file):
            os.unlink(salt_file)

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_encrypted_token_storage())
```

### 安全建议
1. **密钥管理**: 生产环境使用密钥管理服务（KMS），不要硬编码密码
2. **密钥轮换**: 定期更换加密密钥，支持多版本密钥解密
3. **盐值存储**: 盐值应安全存储，可与加密数据分开存储
4. **算法选择**: 使用行业标准算法（AES-256-GCM，ChaCha20-Poly1305）
5. **完整性验证**: 添加HMAC验证，防止加密数据被篡改

---

## 🔧 任务4：完善OAuthClient的PKCE支持

### 完整实现
```python
import hashlib
import base64
import secrets

class OAuthClientWithPKCE(OAuthClient):
    """支持PKCE的OAuth客户端"""
    
    def __init__(self, config: OAuthConfig, use_pkce: bool = True):
        super().__init__(config)
        self.use_pkce = use_pkce
        self.code_verifier = None
        self.code_challenge = None
        
        if use_pkce:
            logger.info("OAuth客户端启用PKCE支持")
    
    async def get_authorization_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """生成授权URL（支持PKCE）"""
        # 生成安全的随机状态参数
        state = state or secrets.token_urlsafe(16)
        self._pending_states[state] = state
        
        # 构造授权URL参数
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
        }
        
        # 添加PKCE参数
        if self.use_pkce:
            # 生成code_verifier（43-128字符的随机字符串）
            self.code_verifier = self._generate_code_verifier()
            
            # 生成code_challenge
            self.code_challenge = self._generate_code_challenge(self.code_verifier)
            
            params.update({
                "code_challenge": self.code_challenge,
                "code_challenge_method": "S256",  # SHA-256
            })
            
            logger.info(f"PKCE: 生成code_verifier和code_challenge")
        
        # 构建完整URL
        url = f"{self.config.authorization_endpoint}?{urlencode(params)}"
        
        logger.info(f"生成授权URL，状态参数: {state}, PKCE: {self.use_pkce}")
        return url, state
    
    def _generate_code_verifier(self) -> str:
        """
        生成PKCE code_verifier
        
        RFC 7636要求:
        - 长度: 43-128字符
        - 字符集: [A-Z]/[a-z]/[0-9]/"-"/"."/"_"/"~"
        """
        # 生成43字符的随机字符串（符合最小要求）
        return secrets.token_urlsafe(32)  # 32字节 = 43字符Base64URL
    
    def _generate_code_challenge(self, code_verifier: str) -> str:
        """
        生成PKCE code_challenge
        
        流程:
        1. 计算SHA256哈希: digest = SHA256(code_verifier)
        2. Base64URL编码: challenge = base64url(digest)
        3. 移除填充: challenge = challenge.replace("=", "")
        """
        # 计算SHA256哈希
        digest = hashlib.sha256(code_verifier.encode()).digest()
        
        # Base64URL编码（无填充）
        challenge = base64.urlsafe_b64encode(digest).decode()
        challenge = challenge.replace("=", "")  # 移除填充字符
        
        return challenge
    
    async def exchange_code_for_token(self, code: str, state: str) -> OAuthToken:
        """使用授权码交换令牌（支持PKCE）"""
        # 验证状态参数
        if state not in self._pending_states:
            logger.error(f"无效的状态参数: {state}")
            raise OAuthError("无效的状态参数，可能遭受CSRF攻击")
        
        # 移除已验证的状态参数
        self._pending_states.pop(state)
        
        # 准备令牌请求数据
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
        }
        
        # 添加客户端认证（如果使用）
        if self.config.client_secret:
            data["client_secret"] = self.config.client_secret
        
        # 添加PKCE参数
        if self.use_pkce:
            if not self.code_verifier:
                logger.error("PKCE: code_verifier未生成")
                raise OAuthError("PKCE code_verifier未生成")
            
            data["code_verifier"] = self.code_verifier
            logger.info("PKCE: 添加code_verifier到令牌请求")
        
        logger.info("使用授权码交换访问令牌" + ("（PKCE）" if self.use_pkce else ""))
        
        try:
            # 发送令牌请求
            response = await self.http_client.post(
                self.config.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # 检查响应状态
            if response.status_code != 200:
                logger.error(f"令牌交换失败: {response.status_code} - {response.text}")
                raise OAuthError(f"令牌交换失败: {response.text}")
            
            # 解析令牌响应
            token_data = response.json()
            
            # 创建令牌对象
            token = OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                refresh_token=token_data.get("refresh_token"),
                scope=token_data.get("scope"),
            )
            
            # 存储令牌
            await self.token_storage.save_token(token)
            
            # 清除PKCE验证器（一次性使用）
            if self.use_pkce:
                self.code_verifier = None
                self.code_challenge = None
            
            logger.info("令牌交换成功并已存储" + ("（PKCE）" if self.use_pkce else ""))
            
            return token
            
        except httpx.RequestError as e:
            logger.error(f"网络请求失败: {e}")
            raise OAuthError(f"网络请求失败: {e}")
        except KeyError as e:
            logger.error(f"令牌响应缺少必要字段: {e}")
            raise OAuthError(f"令牌响应缺少必要字段: {e}")
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """刷新访问令牌（PKCE不影响刷新流程）"""
        # PKCE仅用于授权码流程，不影响刷新令牌流程
        return await super().refresh_token(refresh_token)
```

### PKCE测试
```python
async def test_pkce_flow():
    """测试PKCE流程"""
    print("🧪 测试PKCE OAuth流程...")
    
    import tempfile
    import os
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    
    try:
        # 创建配置
        config = OAuthConfig(
            client_id="pkce_test_client",
            client_secret="",  # PKCE通常用于公共客户端，无需client_secret
            authorization_endpoint="https://pkce.example.com/auth",
            token_endpoint="https://pkce.example.com/token",
            redirect_uri="http://localhost:8080/callback",
            scopes=["openid", "profile"],
            storage_path=temp_path,
        )
        
        # 创建PKCE客户端
        client = OAuthClientWithPKCE(config, use_pkce=True)
        
        # 测试授权URL生成
        auth_url, state = await client.get_authorization_url()
        
        # 验证PKCE参数
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url
        
        # 验证code_verifier已生成
        assert client.code_verifier is not None
        assert len(client.code_verifier) >= 43  # RFC 7636最小长度
        
        # 验证code_challenge已生成
        assert client.code_challenge is not None
        
        # 验证code_challenge是code_verifier的SHA256哈希
        expected_challenge = client._generate_code_challenge(client.code_verifier)
        assert client.code_challenge == expected_challenge
        
        print("✅ PKCE授权URL生成测试通过")
        
        # 注意：完整的PKCE流程测试需要真实的OAuth服务器
        # 这里仅验证客户端逻辑
        
        return True
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_pkce_flow())
```

### PKCE优势
1. **增强安全性**: 防止授权码拦截攻击
2. **公共客户端**: 适用于无法安全存储client_secret的客户端（移动应用、单页应用）
3. **向后兼容**: 服务商可同时支持传统OAuth和PKCE
4. **标准化**: RFC 7636标准，广泛支持

---

## 🔧 任务5：创建GitHub OAuth工具

### 完整实现
```python
from typing import Dict, Any, List, Optional

class GitHubOAuthTool(OAuthProtectedTool):
    """
    GitHub API OAuth工具
    
    支持GitHub REST API v3，提供常用的GitHub操作封装。
    需要GitHub OAuth App的适当授权范围。
    """
    
    def __init__(self, oauth_client: OAuthClient, api_version: str = "2022-11-28"):
        """
        初始化GitHub OAuth工具
        
        参数:
            oauth_client: OAuth客户端实例
            api_version: GitHub API版本（默认使用稳定版本）
        """
        super().__init__(
            tool_name="GitHubAPITool",
            api_endpoint="https://api.github.com",
            oauth_client=oauth_client,
        )
        
        self.api_version = api_version
        self.default_headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": api_version,
            "User-Agent": "DeerFlow-GitHubTool/1.0.0",
        }
    
    async def _make_request(self, method: str, endpoint: str, 
                           data: Optional[Dict] = None,
                           params: Optional[Dict] = None) -> Any:
        """
        发送GitHub API请求（内部方法）
        
        参数:
            method: HTTP方法（GET, POST, PUT, DELETE等）
            endpoint: API端点（如"/user"）
            data: 请求体数据（用于POST/PUT/PATCH）
            params: 查询参数
        
        返回:
            API响应数据
        """
        # 获取有效的访问令牌
        access_token = await self.oauth_client.get_valid_token()
        
        # 准备请求头
        headers = {
            **self.default_headers,
            "Authorization": f"Bearer {access_token}",
        }
        
        # 构建完整URL
        url = f"{self.api_endpoint}{endpoint}"
        
        try:
            # 发送请求
            response = await self.http_client.request(
                method=method,
                url=url,
                headers=headers,
                json=data if data else None,
                params=params if params else None,
                timeout=30.0,
            )
            
            # 处理401未授权错误（自动刷新令牌重试）
            if response.status_code == 401:
                logger.warning("GitHub API返回401，尝试刷新令牌并重试")
                
                # 获取当前令牌用于刷新
                token = await self.oauth_client.token_storage.get_token()
                if token and token.refresh_token:
                    # 刷新令牌（GitHub不支持刷新令牌，这里演示通用流程）
                    await self.oauth_client.refresh_token(token.refresh_token)
                    
                    # 获取新令牌并重试
                    access_token = await self.oauth_client.get_valid_token()
                    headers["Authorization"] = f"Bearer {access_token}"
                    
                    response = await self.http_client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        json=data if data else None,
                        params=params if params else None,
                        timeout=30.0,
                    )
                else:
                    logger.error("没有刷新令牌可用，需要重新授权")
                    raise ToolError("GitHub认证失败，请重新授权")
            
            # 检查最终响应状态
            if response.status_code not in (200, 201, 204):
                error_msg = f"GitHub API错误: {response.status_code}"
                if response.text:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('message', response.text)}"
                
                logger.error(error_msg)
                raise ToolError(error_msg)
            
            # 处理空响应（如204 No Content）
            if response.status_code == 204:
                return None
            
            # 解析成功响应
            result = response.json()
            logger.debug(f"GitHub API调用成功: {method} {endpoint}")
            
            # 处理分页响应（Link头）
            if "Link" in response.headers:
                result = {
                    "data": result,
                    "pagination": self._parse_link_header(response.headers["Link"]),
                }
            
            return result
            
        except httpx.RequestError as e:
            logger.error(f"GitHub API网络请求失败: {e}")
            raise ToolError(f"GitHub API网络请求失败: {e}")
    
    def _parse_link_header(self, link_header: str) -> Dict[str, str]:
        """解析GitHub分页Link头"""
        links = {}
        
        for part in link_header.split(","):
            section = part.split(";")
            if len(section) < 2:
                continue
            
            url = section[0].strip()[1:-1]  # 移除尖括号
            rel = section[1].strip().replace('rel="', "").replace('"', "")
            links[rel] = url
        
        return links
    
    # ========== 用户相关API ==========
    
    async def get_user_info(self, username: str = None) -> Dict[str, Any]:
        """
        获取用户信息
        
        参数:
            username: 用户名（None表示当前认证用户）
        
        返回:
            用户信息字典
        """
        endpoint = f"/users/{username}" if username else "/user"
        return await self._make_request("GET", endpoint)
    
    async def list_user_repos(self, username: str = None, 
                             per_page: int = 30, page: int = 1) -> List[Dict]:
        """
        列出用户仓库
        
        参数:
            username: 用户名（None表示当前认证用户）
            per_page: 每页数量（1-100）
            page: 页码
        
        返回:
            仓库列表
        """
        if username:
            endpoint = f"/users/{username}/repos"
        else:
            endpoint = "/user/repos"
        
        params = {
            "per_page": min(max(per_page, 1), 100),
            "page": max(page, 1),
            "sort": "updated",
            "direction": "desc",
        }
        
        return await self._make_request("GET", endpoint, params=params)
    
    async def create_repo(self, name: str, description: str = "",
                         private: bool = False, auto_init: bool = True) -> Dict:
        """
        创建仓库
        
        参数:
            name: 仓库名称
            description: 仓库描述
            private: 是否私有
            auto_init: 是否自动初始化README
        
        返回:
            创建的仓库信息
        """
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": auto_init,
        }
        
        return await self._make_request("POST", "/user/repos", data=data)
    
    # ========== Issue相关API ==========
    
    async def list_repo_issues(self, repo: str, state: str = "open",
                              per_page: int = 30, page: int = 1) -> List[Dict]:
        """
        列出仓库Issue
        
        参数:
            repo: 仓库全名（owner/repo）
            state: Issue状态（open, closed, all）
            per_page: 每页数量
            page: 页码
        
        返回:
            Issue列表
        """
        endpoint = f"/repos/{repo}/issues"
        
        params = {
            "state": state if state in ("open", "closed", "all") else "open",
            "per_page": min(max(per_page, 1), 100),
            "page": max(page, 1),
        }
        
        return await self._make_request("GET", endpoint, params=params)
    
    async def create_issue(self, repo: str, title: str, 
                          body: str = "", labels: List[str] = None) -> Dict:
        """
        创建Issue
        
        参数:
            repo: 仓库全名（owner/repo）
            title: Issue标题
            body: Issue正文
            labels: 标签列表
        
        返回:
            创建的Issue信息
        """
        data = {
            "title": title,
            "body": body,
        }
        
        if labels:
            data["labels"] = labels
        
        endpoint = f"/repos/{repo}/issues"
        return await self._make_request("POST", endpoint, data=data)
    
    async def update_issue(self, repo: str, issue_number: int,
                          title: str = None, body: str = None,
                          state: str = None, labels: List[str] = None) -> Dict:
        """
        更新Issue
        
        参数:
            repo: 仓库全名（owner/repo）
            issue_number: Issue编号
            title: 新标题（None表示不修改）
            body: 新正文（None表示不修改）
            state: 新状态（open, closed）
            labels: 新标签列表（None表示不修改）
        
        返回:
            更新的Issue信息
        """
        data = {}
        
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body
        if state is not None and state in ("open", "closed"):
            data["state"] = state
        if labels is not None:
            data["labels"] = labels
        
        endpoint = f"/repos/{repo}/issues/{issue_number}"
        return await self._make_request("PATCH", endpoint, data=data)
    
    # ========== Gist相关API ==========
    
    async def create_gist(self, description: str, files: Dict[str, Dict],
                         public: bool = False) -> Dict:
        """
        创建Gist
        
        参数:
            description: Gist描述
            files: 文件字典 {filename: {"content": file_content}}
            public: 是否公开
        
        返回:
            创建的Gist信息
        """
        data = {
            "description": description,
            "public": public,
            "files": files,
        }
        
        return await self._make_request("POST", "/gists", data=data)
    
    async def get_gist(self, gist_id: str) -> Dict:
        """获取Gist详情"""
        return await self._make_request("GET", f"/gists/{gist_id}")
    
    # ========== 搜索相关API ==========
    
    async def search_repos(self, query: str, sort: str = "stars",
                          order: str = "desc", per_page: int = 30) -> Dict:
        """
        搜索仓库
        
        参数:
            query: 搜索查询（如"python language:python stars:>100"）
            sort: 排序字段（stars, forks, updated）
            order: 排序方向（asc, desc）
            per_page: 每页数量
        
        返回:
            搜索结果
        """
        params = {
            "q": query,
            "sort": sort if sort in ("stars", "forks", "updated") else "stars",
            "order": order if order in ("asc", "desc") else "desc",
            "per_page": min(max(per_page, 1), 100),
        }
        
        return await self._make_request("GET", "/search/repositories", params=params)
    
    async def search_code(self, query: str, per_page: int = 30) -> Dict:
        """搜索代码"""
        params = {
            "q": query,
            "per_page": min(max(per_page, 1), 100),
        }
        
        return await self._make_request("GET", "/search/code", params=params)
    
    # ========== 工具方法 ==========
    
    async def test_connection(self) -> bool:
        """测试连接和认证"""
        try:
            user_info = await self.get_user_info()
            if user_info and "login" in user_info:
                logger.info(f"GitHub连接测试成功，用户: {user_info['login']}")
                return True
            return False
        except Exception as e:
            logger.error(f"GitHub连接测试失败: {e}")
            return False
    
    async def get_rate_limit(self) -> Dict:
        """获取API速率限制信息"""
        return await self._make_request("GET", "/rate_limit")
```

### GitHub OAuth配置指南
```python
def create_github_oauth_config():
    """
    创建GitHub OAuth配置
    
    步骤:
    1. 访问 https://github.com/settings/developers
    2. 点击 "New OAuth App"
    3. 填写应用信息:
       - Application name: Your App Name
       - Homepage URL: http://localhost:8080
       - Authorization callback URL: http://localhost:8080/callback
    4. 点击 "Register application"
    5. 获取Client ID和Client Secret
    """
    config = OAuthConfig(
        client_id="YOUR_GITHUB_CLIENT_ID",  # 替换为实际ID
        client_secret="YOUR_GITHUB_CLIENT_SECRET",  # 替换为实际密钥
        authorization_endpoint="https://github.com/login/oauth/authorize",
        token_endpoint="https://github.com/login/oauth/access_token",
        redirect_uri="http://localhost:8080/callback",
        scopes=["user", "repo", "gist"],  # 需要的授权范围
        storage_path="./github_tokens.json",
    )
    
    return config
```

### 使用示例
```python
async def github_oauth_example():
    """GitHub OAuth工具使用示例"""
    
    # 创建配置（使用环境变量更安全）
    import os
    config = OAuthConfig(
        client_id=os.getenv("GITHUB_CLIENT_ID"),
        client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
        authorization_endpoint="https://github.com/login/oauth/authorize",
        token_endpoint="https://github.com/login/oauth/access_token",
        redirect_uri="http://localhost:8080/callback",
        scopes=["user:read", "repo"],
        storage_path="./github_tokens.json",
    )
    
    # 创建OAuth客户端
    client = OAuthClient(config)
    
    # 创建GitHub工具
    github_tool = GitHubOAuthTool(client)
    
    # 测试连接
    if not await github_tool.test_connection():
        print("❌ GitHub连接失败，请先完成OAuth授权")
        
        # 生成授权URL
        auth_url, state = await client.get_authorization_url()
        print(f"请访问以下URL授权: {auth_url}")
        
        # 在实际应用中，这里需要启动HTTP服务器接收回调
        # 获取授权码后调用client.exchange_code_for_token()
        
        return
    
    # 获取当前用户信息
    user_info = await github_tool.get_user_info()
    print(f"👤 当前用户: {user_info.get('login')}")
    print(f"📧 邮箱: {user_info.get('email')}")
    print(f"📊 仓库数: {user_info.get('public_repos')}")
    
    # 列出用户仓库
    repos = await github_tool.list_user_repos(per_page=5)
    print(f"\n📁 最近更新的仓库:")
    for repo in repos[:5]:
        print(f"  - {repo['full_name']}: {repo['description'] or '无描述'}")
    
    # 获取速率限制
    rate_limit = await github_tool.get_rate_limit()
    core_limit = rate_limit.get('resources', {}).get('core', {})
    print(f"\n⏱️  API速率限制: {core_limit.get('remaining')}/{core_limit.get('limit')}")
    
    # 创建测试Issue（需要repo权限）
    # issue = await github_tool.create_issue(
    #     repo="your-username/test-repo",
    #     title="测试Issue",
    #     body="这是一个测试Issue",
    #     labels=["bug", "test"]
    # )
    # print(f"✅ 创建Issue: {issue.get('html_url')}")

# 运行示例
if __name__ == "__main__":
    asyncio.run(github_oauth_example())
```

### 注意事项
1. **GitHub OAuth限制**: GitHub不支持刷新令牌，访问令牌有效期很长（通常几个月）
2. **速率限制**: 认证用户每小时5000次请求，注意合理使用
3. **作用域最小化**: 只请求必要的作用域（如不需要写权限就不要请求repo作用域）
4. **Web应用流**: GitHub推荐使用Web应用流，需要client_secret
5. **设备流**: 对于无浏览器设备，GitHub支持设备流

---

## 🔧 任务6：错误处理增强

### 完整实现
```python
from enum import Enum
from typing import Optional, Dict, Any

class OAuthErrorType(Enum):
    """OAuth 2.0标准错误类型（RFC 6749 Section 5.2）"""
    
    # 标准错误
    INVALID_REQUEST = "invalid_request"
    INVALID_CLIENT = "invalid_client"
    INVALID_GRANT = "invalid_grant"
    UNAUTHORIZED_CLIENT = "unauthorized_client"
    UNSUPPORTED_GRANT_TYPE = "unsupported_grant_type"
    INVALID_SCOPE = "invalid_scope"
    
    # 扩展错误
    ACCESS_DENIED = "access_denied"
    UNSUPPORTED_RESPONSE_TYPE = "unsupported_response_type"
    SERVER_ERROR = "server_error"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    
    # 客户端错误
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    PARSE_ERROR = "parse_error"
    STATE_MISMATCH = "state_mismatch"


class OAuthError(Exception):
    """增强的OAuth错误类"""
    
    def __init__(
        self,
        error_type: OAuthErrorType,
        description: str = "",
        error_uri: Optional[str] = None,
        state: Optional[str] = None,
        original_exception: Optional[Exception] = None,
    ):
        self.error_type = error_type
        self.description = description
        self.error_uri = error_uri
        self.state = state
        self.original_exception = original_exception
        
        # 构建错误消息
        message = f"OAuth错误: {error_type.value}"
        if description:
            message += f" - {description}"
        if error_uri:
            message += f" (详情: {error_uri})"
        
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为OAuth标准错误响应格式"""
        error_dict = {
            "error": self.error_type.value,
        }
        
        if self.description:
            error_dict["error_description"] = self.description
        if self.error_uri:
            error_dict["error_uri"] = self.error_uri
        if self.state:
            error_dict["state"] = self.state
        
        return error_dict
    
    @classmethod
    def from_response(cls, response_json: Dict[str, Any], state: Optional[str] = None) -> "OAuthError":
        """从OAuth错误响应创建错误对象"""
        error_value = response_json.get("error", "server_error")
        
        try:
            error_type = OAuthErrorType(error_value)
        except ValueError:
            # 未知错误类型，默认为服务器错误
            error_type = OAuthErrorType.SERVER_ERROR
        
        return cls(
            error_type=error_type,
            description=response_json.get("error_description", ""),
            error_uri=response_json.get("error_uri"),
            state=state or response_json.get("state"),
        )
    
    def should_retry(self) -> bool:
        """检查错误是否可重试"""
        retryable_errors = {
            OAuthErrorType.NETWORK_ERROR,
            OAuthErrorType.TIMEOUT_ERROR,
            OAuthErrorType.SERVER_ERROR,
            OAuthErrorType.TEMPORARILY_UNAVAILABLE,
        }
        
        return self.error_type in retryable_errors
    
    def requires_reauthorization(self) -> bool:
        """检查错误是否需要重新授权"""
        reauth_errors = {
            OAuthErrorType.INVALID_GRANT,
            OAuthErrorType.INVALID_CLIENT,
            OAuthErrorType.UNAUTHORIZED_CLIENT,
            OAuthErrorType.ACCESS_DENIED,
        }
        
        return self.error_type in reauth_errors


class EnhancedOAuthClient(OAuthClient):
    """增强错误处理的OAuth客户端"""
    
    def __init__(self, config: OAuthConfig, max_retries: int = 3):
        super().__init__(config)
        self.max_retries = max_retries
    
    async def exchange_code_for_token(self, code: str, state: str) -> OAuthToken:
        """使用授权码交换令牌（增强错误处理）"""
        # 验证状态参数
        if state not in self._pending_states:
            logger.error(f"无效的状态参数: {state}")
            raise OAuthError(
                error_type=OAuthErrorType.STATE_MISMATCH,
                description="状态参数不匹配，可能遭受CSRF攻击",
                state=state,
            )
        
        # 移除已验证的状态参数
        self._pending_states.pop(state)
        
        # 准备令牌请求数据
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        
        logger.info("使用授权码交换访问令牌")
        
        # 带重试的请求
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # 发送令牌请求
                response = await self.http_client.post(
                    self.config.token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )
                
                # 处理错误响应
                if response.status_code != 200:
                    try:
                        error_data = response.json()
                        oauth_error = OAuthError.from_response(error_data, state)
                        
                        logger.error(f"令牌交换失败 ({attempt+1}/{self.max_retries}): {oauth_error}")
                        
                        # 检查是否需要重新授权
                        if oauth_error.requires_reauthorization():
                            logger.warning("需要重新授权，清除存储的令牌")
                            await self.token_storage.clear_token()
                        
                        last_error = oauth_error
                        
                        # 检查是否可重试
                        if oauth_error.should_retry() and attempt < self.max_retries - 1:
                            # 指数退避重试
                            delay = 2 ** attempt
                            logger.info(f"等待 {delay} 秒后重试...")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise oauth_error
                            
                    except (json.JSONDecodeError, KeyError):
                        # 非标准错误响应
                        raise OAuthError(
                            error_type=OAuthErrorType.SERVER_ERROR,
                            description=f"服务器返回错误: {response.status_code}",
                            state=state,
                        )
                
                # 解析成功响应
                token_data = response.json()
                
                # 验证必要字段
                if "access_token" not in token_data:
                    raise OAuthError(
                        error_type=OAuthErrorType.INVALID_REQUEST,
                        description="令牌响应缺少access_token字段",
                        state=state,
                    )
                
                # 创建令牌对象
                token = OAuthToken(
                    access_token=token_data["access_token"],
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in"),
                    refresh_token=token_data.get("refresh_token"),
                    scope=token_data.get("scope"),
                )
                
                # 存储令牌
                await self.token_storage.save_token(token)
                logger.info("令牌交换成功并已存储")
                
                return token
                
            except httpx.RequestError as e:
                # 网络错误
                network_error = OAuthError(
                    error_type=OAuthErrorType.NETWORK_ERROR,
                    description=f"网络请求失败: {e}",
                    state=state,
                    original_exception=e,
                )
                
                logger.error(f"网络请求失败 ({attempt+1}/{self.max_retries}): {e}")
                last_error = network_error
                
                # 网络错误可重试
                if attempt < self.max_retries - 1:
                    delay = 2 ** attempt
                    logger.info(f"等待 {delay} 秒后重试...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise network_error
                    
            except OAuthError:
                # 已处理的OAuth错误，直接抛出
                raise
                
            except Exception as e:
                # 未知错误
                unknown_error = OAuthError(
                    error_type=OAuthErrorType.SERVER_ERROR,
                    description=f"未知错误: {e}",
                    state=state,
                    original_exception=e,
                )
                
                logger.error(f"未知错误 ({attempt+1}/{self.max_retries}): {e}")
                last_error = unknown_error
                
                if attempt < self.max_retries - 1:
                    delay = 2 ** attempt
                    logger.info(f"等待 {delay} 秒后重试...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise unknown_error
        
        # 所有重试都失败
        if last_error:
            raise last_error
        else:
            raise OAuthError(
                error_type=OAuthErrorType.SERVER_ERROR,
                description="令牌交换失败，未知错误",
                state=state,
            )
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """刷新访问令牌（增强错误处理）"""
        if not refresh_token:
            raise OAuthError(
                error_type=OAuthErrorType.INVALID_REQUEST,
                description="刷新令牌为空",
            )
        
        # 准备刷新请求数据
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        
        logger.info("刷新访问令牌")
        
        # 带重试的请求（类似exchange_code_for_token）
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await self.http_client.post(
                    self.config.token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    try:
                        error_data = response.json()
                        oauth_error = OAuthError.from_response(error_data)
                        
                        logger.error(f"令牌刷新失败 ({attempt+1}/{self.max_retries}): {oauth_error}")
                        
                        # 刷新令牌无效，需要重新授权
                        if oauth_error.error_type == OAuthErrorType.INVALID_GRANT:
                            logger.warning("刷新令牌无效，需要重新授权")
                            await self.token_storage.clear_token()
                        
                        last_error = oauth_error
                        
                        if oauth_error.should_retry() and attempt < self.max_retries - 1:
                            delay = 2 ** attempt
                            logger.info(f"等待 {delay} 秒后重试...")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            raise oauth_error
                            
                    except (json.JSONDecodeError, KeyError):
                        raise OAuthError(
                            error_type=OAuthErrorType.SERVER_ERROR,
                            description=f"服务器返回错误: {response.status_code}",
                        )
                
                # 解析成功响应
                token_data = response.json()
                
                if "access_token" not in token_data:
                    raise OAuthError(
                        error_type=OAuthErrorType.INVALID_REQUEST,
                        description="刷新响应缺少access_token字段",
                    )
                
                token = OAuthToken(
                    access_token=token_data["access_token"],
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_in=token_data.get("expires_in"),
                    refresh_token=token_data.get("refresh_token", refresh_token),
                    scope=token_data.get("scope"),
                )
                
                await self.token_storage.save_token(token)
                logger.info("令牌刷新成功")
                
                return token
                
            except httpx.RequestError as e:
                network_error = OAuthError(
                    error_type=OAuthErrorType.NETWORK_ERROR,
                    description=f"网络请求失败: {e}",
                    original_exception=e,
                )
                
                logger.error(f"网络请求失败 ({attempt+1}/{self.max_retries}): {e}")
                last_error = network_error
                
                if attempt < self.max_retries - 1:
                    delay = 2 ** attempt
                    logger.info(f"等待 {delay} 秒后重试...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise network_error
                    
            except OAuthError:
                raise
                
            except Exception as e:
                unknown_error = OAuthError(
                    error_type=OAuthErrorType.SERVER_ERROR,
                    description=f"未知错误: {e}",
                    original_exception=e,
                )
                
                logger.error(f"未知错误 ({attempt+1}/{self.max_retries}): {e}")
                last_error = unknown_error
                
                if attempt < self.max_retries - 1:
                    delay = 2 ** attempt
                    logger.info(f"等待 {delay} 秒后重试...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise unknown_error
        
        if last_error:
            raise last_error
        else:
            raise OAuthError(
                error_type=OAuthErrorType.SERVER_ERROR,
                description="令牌刷新失败，未知错误",
            )
    
    async def get_valid_token(self) -> str:
        """获取有效的访问令牌（增强错误处理）"""
        try:
            return await super().get_valid_token()
        except OAuthError as e:
            # 记录详细错误信息
            logger.error(f"获取有效令牌失败: {e}")
            
            # 检查是否需要重新授权
            if e.requires_reauthorization():
                logger.warning("需要重新授权，请调用get_authorization_url()开始新授权流程")
            
            raise
```

### 错误处理测试
```python
async def test_enhanced_error_handling():
    """测试增强错误处理"""
    print("🧪 测试增强错误处理...")
    
    import tempfile
    import os
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = f.name
    
    try:
        # 创建配置
        config = OAuthConfig(
            client_id="error_test_client",
            client_secret="error_test_secret",
            authorization_endpoint="https://error.example.com/auth",
            token_endpoint="https://error.example.com/token",
            redirect_uri="http://localhost:8080/callback",
            scopes=["test"],
            storage_path=temp_path,
        )
        
        # 创建增强客户端
        client = EnhancedOAuthClient(config, max_retries=2)
        
        # 测试状态参数不匹配错误
        try:
            await client.exchange_code_for_token("test_code", "invalid_state")
            assert False, "应该抛出状态参数不匹配错误"
        except OAuthError as e:
            assert e.error_type == OAuthErrorType.STATE_MISMATCH
            assert "状态参数不匹配" in str(e)
        
        # 测试网络错误重试（模拟不存在的端点）
        invalid_config = OAuthConfig(
            client_id="test",
            client_secret="test",
            authorization_endpoint="https://nonexistent.example.com/auth",
            token_endpoint="https://nonexistent.example.com/token",
            redirect_uri="http://localhost:8080/callback",
            scopes=["test"],
            storage_path=temp_path,
        )
        
        invalid_client = EnhancedOAuthClient(invalid_config, max_retries=2)
        
        # 生成有效的授权URL和状态
        auth_url, state = await invalid_client.get_authorization_url()
        
        # 尝试交换令牌（应该触发网络错误重试）
        try:
            await invalid_client.exchange_code_for_token("test_code", state)
            assert False, "应该抛出网络错误"
        except OAuthError as e:
            # 应该尝试了2次重试（总共3次请求）
            assert e.error_type == OAuthErrorType.NETWORK_ERROR
            # 注意：实际重试次数取决于网络超时时间
        
        print("✅ 增强错误处理测试通过")
        return True
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_enhanced_error_handling())
```

### 错误处理最佳实践
1. **分类处理**: 根据错误类型采取不同策略（重试、重新授权、用户提示）
2. **安全日志**: 记录错误但不泄露敏感信息（如令牌、密码）
3. **用户友好**: 将技术错误转换为用户可理解的消息
4. **重试策略**: 使用指数退避重试，避免加重服务器负担
5. **状态恢复**: 错误后清理状态，避免不一致状态

---

## 📚 常见问题解答

### Q1: OAuth 2.0和OAuth 1.0有什么区别？
**A**: OAuth 2.0是完全重设计的新协议，主要区别：
- 简化流程，移除复杂的签名机制
- 支持多种授权类型（授权码、客户端凭证、密码、隐式）
- 使用Bearer令牌，无需每次请求签名
- 更好的移动端和单页应用支持
- 更灵活的可扩展性

### Q2: 什么情况下应该使用PKCE？
**A**: PKCE（Proof Key for Code Exchange）应该用于：
- 移动端原生应用（无法安全存储client_secret）
- 单页应用（SPA，在浏览器中运行）
- 桌面应用（用户可能检查文件系统）
- 任何无法保证client_secret安全的场景

### Q3: 刷新令牌泄露了怎么办？
**A**: 采取以下措施：
1. **立即撤销**: 调用OAuth服务商的令牌撤销端点
2. **清除本地存储**: 删除所有存储的令牌
3. **重新授权**: 引导用户重新进行OAuth授权
4. **监控异常**: 监控异常令牌使用模式
5. **预防措施**: 使用短期刷新令牌，定期轮换

### Q4: 如何选择OAuth授权范围？
**A**: 遵循最小权限原则：
1. **只请求必要权限**: 不要请求不需要的作用域
2. **增量授权**: 开始时请求基本权限，需要时再请求更多
3. **用户教育**: 向用户解释每个作用域的用途
4. **定期审查**: 定期审查应用实际需要的权限

### Q5: OAuth 2.1有什么重要变化？
**A**: OAuth 2.1主要安全增强：
1. **PKCE强制**: 授权码流程必须使用PKCE
2. **移除隐式授权**: 不再允许隐式授权流程（response_type=token）
3. **刷新令牌绑定**: 刷新令牌与客户端绑定，防止令牌滥用
4. **Bearer令牌用法**: 明确Bearer令牌的使用规范

---

## 🎓 学习总结

### 关键知识点
1. **OAuth 2.0流程**: 理解授权码流程的完整步骤和安全考虑
2. **客户端实现**: 掌握OAuth客户端的架构设计和安全实现
3. **令牌管理**: 了解令牌的生命周期管理、刷新和存储安全
4. **错误处理**: 学习OAuth标准错误处理和恢复策略
5. **PKCE扩展**: 掌握PKCE增强安全性的原理和实现

### 实践技能
1. **安全编码**: 实现安全的OAuth客户端，防止常见攻击
2. **API集成**: 集成OAuth保护的第三方API（如GitHub API）
3. **测试策略**: 编写全面的OAuth流程测试
4. **故障排除**: 诊断和解决OAuth集成问题

### 下一步学习建议
1. **深入安全**: 学习OAuth安全最佳实践和漏洞防范
2. **扩展协议**: 学习OpenID Connect（在OAuth上构建的身份层）
3. **企业集成**: 学习SAML、LDAP等企业身份集成
4. **生产部署**: 学习OAuth在生产环境的最佳实践和监控

---

**答案解析完成时间**: 2024年4月11日  
**教师**: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）  
**版本**: v1.0.0  
**版权所有**: © 2024 DeerFlow Team. 保留所有权利。