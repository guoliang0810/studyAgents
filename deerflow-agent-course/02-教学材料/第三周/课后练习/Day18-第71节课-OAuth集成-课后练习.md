# 📚 Day 18 第71节课：OAuth集成 - 课后练习

## 🎯 练习目标
通过本练习，你将掌握：
1. OAuth 2.0授权码流程的实现
2. OAuth客户端的完整功能开发
3. 受OAuth保护的MCP工具创建
4. 令牌管理和安全最佳实践

## ⏰ 预计用时
- 基础任务：60分钟
- 扩展挑战：90分钟
- 总计：2.5小时

## 🔧 环境准备
```bash
# 1. 激活虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install httpx>=0.27.0

# 3. 克隆演示代码
cp -r ../课堂演示代码/day18-lesson71/ ./work/
cd work
```

## 📝 练习任务

### 任务1：理解OAuth配置类（10分钟）
**目标**: 理解OAuthConfig类的设计和验证机制

**步骤**:
1. 阅读`OAuthConfig`类的源代码
2. 回答以下问题：
   - 为什么需要验证配置的完整性？
   - `client_secret`为什么不能为空？
   - `redirect_uri`在OAuth流程中的作用是什么？
3. 编写测试代码验证配置验证功能：
   ```python
   # 测试无效配置应抛出异常
   try:
       config = OAuthConfig(
           client_id="",  # 空客户端ID
           client_secret="test",
           authorization_endpoint="https://example.com/auth",
           token_endpoint="https://example.com/token",
           redirect_uri="http://localhost:8080/callback",
           scopes=["read"],
       )
       print("❌ 测试失败：应该抛出异常")
   except ValueError as e:
       print(f"✅ 测试通过：{e}")
   ```

**提交物**: 回答问题文档和测试代码

---

### 任务2：实现OAuthToken类的方法（20分钟）
**目标**: 完善OAuth令牌类的功能

**步骤**:
1. 在`OAuthToken`类中添加以下方法：
   ```python
   def time_until_expiry(self) -> Optional[float]:
       """返回距离令牌过期的剩余时间（秒），如果永不过期返回None"""
       # 你的实现
       pass
   
   def to_json(self) -> str:
       """将令牌转换为JSON字符串"""
       # 你的实现
       pass
   
   @classmethod
   def from_json(cls, json_str: str) -> "OAuthToken":
       """从JSON字符串创建令牌"""
       # 你的实现
       pass
   ```
2. 编写单元测试验证新功能：
   ```python
   async def test_token_serialization():
       token = OAuthToken(
           access_token="test_token",
           expires_in=3600,
           refresh_token="test_refresh",
       )
       
       # 测试JSON序列化
       json_str = token.to_json()
       token2 = OAuthToken.from_json(json_str)
       assert token2.access_token == token.access_token
       
       # 测试剩余时间计算
       remaining = token.time_until_expiry()
       assert remaining is not None
       assert 3590 < remaining <= 3600  # 考虑创建时间开销
   ```

**提交物**: 完整的`OAuthToken`类实现和测试代码

---

### 任务3：实现TokenStorage的加密存储（30分钟）
**目标**: 增强令牌存储的安全性

**步骤**:
1. 创建`EncryptedTokenStorage`类，继承自`TokenStorage`：
   ```python
   class EncryptedTokenStorage(TokenStorage):
       """加密的令牌存储"""
       
       def __init__(self, storage_path: str, encryption_key: str):
           super().__init__(storage_path)
           self.encryption_key = encryption_key
       
       def _encrypt(self, data: str) -> str:
           """加密数据（使用简单示例，生产环境使用专业加密库）"""
           # 提示：可以使用cryptography库或简单的对称加密
           pass
       
       def _decrypt(self, encrypted_data: str) -> str:
           """解密数据"""
           pass
       
       async def save_token(self, token: OAuthToken) -> None:
           """加密后保存令牌"""
           # 你的实现
           pass
       
       async def get_token(self) -> Optional[OAuthToken]:
           """解密后加载令牌"""
           # 你的实现
           pass
   ```
2. 实现基本的加密功能（可以使用`cryptography`库或简单的Base64编码作为示例）
3. 编写测试验证加密存储功能

**可选扩展**: 实现密钥轮换机制，支持多版本密钥解密

**提交物**: `EncryptedTokenStorage`类实现和测试代码

---

### 任务4：完善OAuthClient的PKCE支持（40分钟）
**目标**: 实现OAuth 2.0 PKCE扩展，增强移动端和单页应用安全性

**PKCE流程**:
1. 客户端创建code_verifier（随机字符串）
2. 计算code_challenge = SHA256(code_verifier) → Base64URL编码
3. 授权请求包含code_challenge和code_challenge_method
4. 令牌请求包含code_verifier

**步骤**:
1. 在`OAuthClient`类中添加PKCE支持：
   ```python
   class OAuthClient:
       def __init__(self, config: OAuthConfig, use_pkce: bool = False):
           self.use_pkce = use_pkce
           self.code_verifier = None
       
       async def get_authorization_url(self, state: Optional[str] = None) -> Tuple[str, str]:
           """生成授权URL（支持PKCE）"""
           if self.use_pkce:
               # 生成code_verifier和code_challenge
               self.code_verifier = secrets.token_urlsafe(32)
               code_challenge = self._generate_pkce_challenge(self.code_verifier)
               # 添加PKCE参数到授权URL
           
           # 原有逻辑...
       
       async def exchange_code_for_token(self, code: str, state: str) -> OAuthToken:
           """使用授权码交换令牌（支持PKCE）"""
           if self.use_pkce:
               # 在令牌请求中添加code_verifier参数
           
           # 原有逻辑...
       
       def _generate_pkce_challenge(self, verifier: str) -> str:
           """生成PKCE code_challenge"""
           import hashlib
           import base64
           
           # SHA256哈希
           digest = hashlib.sha256(verifier.encode()).digest()
           # Base64URL编码（无填充，替换字符）
           challenge = base64.urlsafe_b64encode(digest).decode().replace("=", "")
           return challenge
   ```
2. 更新测试以支持PKCE流程测试
3. 验证PKCE流程的正确性

**提交物**: 支持PKCE的`OAuthClient`类实现和测试代码

---

### 任务5：创建GitHub OAuth工具（30分钟）
**目标**: 创建实际的GitHub API OAuth工具

**步骤**:
1. 在GitHub上创建OAuth App（或使用测试配置）：
   - 前往 https://github.com/settings/developers
   - 创建New OAuth App
   - 设置Authorization callback URL: `http://localhost:8080/callback`
2. 创建`GitHubOAuthTool`类：
   ```python
   class GitHubOAuthTool(OAuthProtectedTool):
       """GitHub API OAuth工具"""
       
       def __init__(self, oauth_client: OAuthClient):
           super().__init__(
               tool_name="GitHubAPITool",
               api_endpoint="https://api.github.com",
               oauth_client=oauth_client,
           )
       
       async def get_user_info(self) -> Dict[str, Any]:
           """获取当前用户信息"""
           return await self.call({
               "method": "GET",
               "endpoint": "/user",
           })
       
       async def list_user_repos(self, username: str = None) -> List[Dict]:
           """列出用户仓库"""
           endpoint = f"/users/{username}/repos" if username else "/user/repos"
           return await self.call({
               "method": "GET",
               "endpoint": endpoint,
               "params": {"sort": "updated", "per_page": 10},
           })
       
       async def create_issue(self, repo: str, title: str, body: str = "") -> Dict:
           """创建Issue"""
           return await self.call({
               "method": "POST",
               "endpoint": f"/repos/{repo}/issues",
               "data": {"title": title, "body": body},
           })
   ```
3. 编写完整的OAuth流程测试：
   ```python
   async def test_github_oauth_flow():
       # 使用GitHub OAuth配置
       config = OAuthConfig(
           client_id="your_client_id",
           client_secret="your_client_secret",
           authorization_endpoint="https://github.com/login/oauth/authorize",
           token_endpoint="https://github.com/login/oauth/access_token",
           redirect_uri="http://localhost:8080/callback",
           scopes=["user", "repo"],
       )
       
       client = OAuthClient(config)
       tool = GitHubOAuthTool(client)
       
       # 注意：实际测试需要用户交互，这里编写模拟测试
       print("请手动完成OAuth授权流程...")
   ```

**提交物**: `GitHubOAuthTool`类实现和测试说明

---

### 任务6：错误处理增强（20分钟）
**目标**: 完善OAuth客户端的错误处理机制

**步骤**:
1. 在`OAuthClient`类中添加以下错误处理：
   ```python
   class OAuthErrorType(Enum):
       NETWORK_ERROR = "network_error"
       INVALID_GRANT = "invalid_grant"
       INVALID_CLIENT = "invalid_client"
       INVALID_SCOPE = "invalid_scope"
       UNAUTHORIZED_CLIENT = "unauthorized_client"
       UNSUPPORTED_GRANT_TYPE = "unsupported_grant_type"
       INVALID_REQUEST = "invalid_request"
       SERVER_ERROR = "server_error"
   
   class OAuthError(Exception):
       def __init__(self, error_type: OAuthErrorType, description: str = ""):
           self.error_type = error_type
           self.description = description
           super().__init__(f"{error_type.value}: {description}")
   ```
2. 根据OAuth 2.0 RFC 6749规范，处理标准错误响应：
   ```python
   async def exchange_code_for_token(self, code: str, state: str) -> OAuthToken:
       try:
           response = await self.http_client.post(...)
           
           if response.status_code != 200:
               error_data = response.json()
               error_type = OAuthErrorType(error_data.get("error", "server_error"))
               error_desc = error_data.get("error_description", "")
               
               # 特殊处理：invalid_grant错误需要重新授权
               if error_type == OAuthErrorType.INVALID_GRANT:
                   logger.error("授权码无效或已过期，需要重新授权")
                   await self.token_storage.clear_token()
               
               raise OAuthError(error_type, error_desc)
           
           # 正常处理...
       except httpx.RequestError as e:
           raise OAuthError(OAuthErrorType.NETWORK_ERROR, str(e))
   ```
3. 编写测试验证各种错误场景的处理

**提交物**: 增强的错误处理实现和测试代码

---

## 🏆 扩展挑战（可选）

### 挑战1：多服务商OAuth客户端（高级）
创建支持多个OAuth服务商（GitHub、Google、Microsoft）的统一客户端。

**要求**:
1. 抽象OAuth服务商配置
2. 支持服务商特定的参数和扩展
3. 统一的令牌管理和API调用接口

### 挑战2：分布式令牌存储（高级）
实现基于Redis的分布式令牌存储，支持多实例部署。

**要求**:
1. Redis连接池管理
2. 令牌序列化和反序列化
3. 过期自动清理
4. 集群支持

### 挑战3：OAuth 2.1合规性（专家）
实现OAuth 2.1草案规范的所有安全要求。

**要求**:
1. PKCE强制要求
2. 禁止隐式授权流程
3. 增强的令牌安全性
4. 完整的规范测试套件

## 📋 提交要求

### 必须提交的内容
1. **源代码**: 所有实现的Python文件
2. **测试代码**: 完整的单元测试
3. **文档**: 
   - 实现说明文档（README.md格式）
   - API文档（使用docstring）
   - 部署和配置指南

### 代码质量要求
- ✅ 通过所有单元测试
- ✅ 代码符合PEP 8规范
- ✅ 有完整的类型注解
- ✅ 有适当的错误处理
- ✅ 有清晰的日志记录

### 安全性要求
- ✅ 无硬编码的敏感信息
- ✅ 使用安全的随机数生成
- ✅ 实现CSRF防护
- ✅ 令牌安全存储

## 📊 评分标准

### 基础分（70分）
- 任务1完成：10分
- 任务2完成：15分  
- 任务3完成：20分
- 任务4完成：25分

### 质量分（20分）
- 代码规范：5分
- 测试覆盖率：5分
- 错误处理：5分
- 文档完整：5分

### 扩展分（10分）
- 扩展挑战完成：最多10分

### 扣分项
- 安全漏洞：每次-5分
- 测试失败：每次-2分
- 代码重复：每次-2分

## 🆘 帮助资源

### 文档参考
1. [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
2. [OAuth 2.0 PKCE RFC 7636](https://tools.ietf.org/html/rfc7636)
3. [GitHub OAuth文档](https://docs.github.com/en/apps/oauth-apps)
4. [HTTPX文档](https://www.python-httpx.org/)

### 调试工具
1. **OAuth调试器**: https://oauthdebugger.com/
2. **JWT调试器**: https://jwt.io/
3. **HTTP流量分析**: 使用Burp Suite或Charles Proxy

### 常见问题解答
1. **Q**: 状态参数验证失败？
   **A**: 确保生成和验证使用相同的状态参数，检查会话管理

2. **Q**: 令牌交换返回invalid_grant？
   **A**: 授权码可能已过期或被使用，需要重新授权

3. **Q**: API调用返回401？
   **A**: 令牌可能已过期，检查自动刷新机制

## 📅 截止时间
- **提交截止**: 课程结束后48小时内
- **反馈时间**: 提交后24小时内
- **修改提交**: 收到反馈后24小时内

## 📧 提交方式
1. 将代码打包为ZIP文件
2. 文件名格式: `学号_姓名_第71节课_OAuth集成.zip`
3. 发送至: course-submit@deerflow.tech
4. 邮件主题: `[第71节课] OAuth集成作业 - 学号_姓名`

---

**祝您练习顺利！如有问题，请在课程群中提问或联系助教。**

*"安全不是功能，而是基础。" - OAuth设计原则*

---
**课程设计**: DeerFlow Python Agent架构师训练营  
**版本**: v1.0.0  
**最后更新**: 2024年4月11日  
**教师**: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）  
**版权所有**: © 2024 DeerFlow Team. 保留所有权利。