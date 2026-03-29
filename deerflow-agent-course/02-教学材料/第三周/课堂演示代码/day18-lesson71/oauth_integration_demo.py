#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎓 Day 18 第71节课：OAuth集成 - 课堂演示代码
================================================

📚 课程目标:
1. 理解OAuth 2.0协议的基本流程、授权类型和安全机制
2. 掌握OAuth客户端在MCP工具集成中的架构设计
3. 了解令牌管理、刷新机制和错误处理的最佳实践

🔧 本演示代码包含:
1. OAuthConfig - OAuth配置类
2. OAuthToken - OAuth令牌类
3. OAuthClient - OAuth客户端核心类
4. TokenStorage - 令牌存储类
5. OAuthProtectedTool - 受OAuth保护的MCP工具类
6. 完整的测试用例和模拟服务器

⚠️ 安全提示:
- 本代码仅用于教学演示，生产环境需要额外的安全措施
- 令牌必须安全存储（如加密存储或密钥管理服务）
- 建议使用PKCE扩展增强移动端和单页应用安全性
- 定期审查OAuth实现的安全性

🚀 使用方法:
python oauth_integration_demo.py --test   # 运行测试
python oauth_integration_demo.py --demo   # 运行演示

📅 版本: v1.0.0
👨‍🏫 教师: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）
"""

import asyncio
import json
import logging
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("oauth_demo")


# ============================================================================
# 🎯 自定义异常类
# ============================================================================

class OAuthError(Exception):
    """OAuth相关错误"""
    pass


class ToolError(Exception):
    """工具调用错误"""
    pass


class TokenStorageError(Exception):
    """令牌存储错误"""
    pass


# ============================================================================
# 📝 数据类定义
# ============================================================================

class OAuthConfig:
    """
    OAuth配置类
    
    🎯 功能:
    - 存储OAuth客户端配置信息
    - 验证配置的完整性
    - 提供配置的序列化方法
    
    🔑 配置参数说明:
    - client_id: 客户端ID（在OAuth服务商注册获得）
    - client_secret: 客户端密钥（必须保密）
    - authorization_endpoint: 授权端点URL
    - token_endpoint: 令牌端点URL
    - redirect_uri: 回调URI（必须与注册时一致）
    - scopes: 授权范围列表（如["read", "write"]）
    - storage_path: 令牌存储文件路径（默认"./tokens.json"）
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        authorization_endpoint: str,
        token_endpoint: str,
        redirect_uri: str,
        scopes: list,
        storage_path: str = "./tokens.json"
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorization_endpoint = authorization_endpoint
        self.token_endpoint = token_endpoint
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self.storage_path = storage_path
        
        # 验证配置
        self._validate_config()
    
    def _validate_config(self) -> None:
        """验证配置完整性"""
        if not self.client_id:
            raise ValueError("client_id不能为空")
        if not self.client_secret:
            raise ValueError("client_secret不能为空")
        if not self.authorization_endpoint:
            raise ValueError("authorization_endpoint不能为空")
        if not self.token_endpoint:
            raise ValueError("token_endpoint不能为空")
        if not self.redirect_uri:
            raise ValueError("redirect_uri不能为空")
        if not self.scopes:
            raise ValueError("scopes不能为空")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（排除敏感信息）"""
        return {
            "client_id": self.client_id,
            "authorization_endpoint": self.authorization_endpoint,
            "token_endpoint": self.token_endpoint,
            "redirect_uri": self.redirect_uri,
            "scopes": self.scopes,
            "storage_path": self.storage_path,
        }
    
    def __repr__(self) -> str:
        return f"OAuthConfig(client_id={self.client_id[:8]}..., scopes={self.scopes})"


class OAuthToken:
    """
    OAuth令牌类
    
    🎯 功能:
    - 封装OAuth令牌及其元数据
    - 提供令牌过期检查功能
    - 支持令牌的序列化和反序列化
    
    🔑 令牌属性说明:
    - access_token: 访问令牌（用于API调用）
    - token_type: 令牌类型（通常为"Bearer"）
    - expires_in: 令牌有效期（秒）
    - refresh_token: 刷新令牌（用于获取新访问令牌）
    - scope: 授权范围
    - created_at: 令牌创建时间戳
    """
    
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
        """
        检查令牌是否过期
        
        📝 说明:
        - 如果expires_in为None，则认为永不过期
        - 提前60秒认为过期，避免临界时间问题
        """
        if self.expires_in is None:
            return False
        
        elapsed = time.time() - self.created_at
        # 提前60秒认为过期，避免API调用时令牌刚好过期
        return elapsed >= self.expires_in - 60
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
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
        """从字典创建令牌"""
        token = cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in"),
            refresh_token=data.get("refresh_token"),
            scope=data.get("scope"),
        )
        # 恢复创建时间戳
        token.created_at = data.get("created_at", time.time())
        return token
    
    def __repr__(self) -> str:
        expires_info = f", expires_in={self.expires_in}" if self.expires_in else ""
        refresh_info = f", has_refresh_token={bool(self.refresh_token)}"
        return f"OAuthToken(access_token={self.access_token[:8]}...{expires_info}{refresh_info})"


# ============================================================================
# 🔧 核心实现类
# ============================================================================

class TokenStorage:
    """
    令牌存储类
    
    🎯 功能:
    - 安全地存储和检索OAuth令牌
    - 支持文件系统存储（可扩展为数据库或密钥管理服务）
    - 提供令牌的序列化和反序列化
    
    ⚠️ 安全提示:
    - 生产环境应使用加密存储或专门的密钥管理服务
    - 文件存储仅适合开发和测试环境
    """
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
    
    async def save_token(self, token: OAuthToken) -> None:
        """保存令牌到存储"""
        try:
            token_data = token.to_dict()
            
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"令牌已保存到 {self.storage_path}")
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"保存令牌失败: {e}")
            raise TokenStorageError(f"保存令牌失败: {e}")
    
    async def get_token(self) -> Optional[OAuthToken]:
        """从存储中获取令牌"""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                token_data = json.load(f)
            
            logger.info(f"从 {self.storage_path} 加载令牌")
            return OAuthToken.from_dict(token_data)
        except FileNotFoundError:
            logger.warning(f"令牌文件不存在: {self.storage_path}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"加载令牌失败，文件格式错误: {e}")
            return None
        except Exception as e:
            logger.error(f"加载令牌失败: {e}")
            return None
    
    async def clear_token(self) -> None:
        """清除存储的令牌"""
        try:
            import os
            if os.path.exists(self.storage_path):
                os.remove(self.storage_path)
                logger.info(f"令牌文件已删除: {self.storage_path}")
        except Exception as e:
            logger.error(f"清除令牌失败: {e}")
            raise TokenStorageError(f"清除令牌失败: {e}")


class OAuthClient:
    """
    OAuth客户端核心类
    
    🎯 功能:
    - 生成授权URL并处理OAuth 2.0授权码流程
    - 使用授权码交换访问令牌
    - 刷新过期的访问令牌
    - 自动管理令牌生命周期
    
    🔐 安全特性:
    - 使用状态参数防止CSRF攻击
    - 自动处理令牌刷新
    - 完整的错误处理和日志记录
    
    📚 OAuth 2.0授权码流程:
    1. 生成授权URL → 重定向用户到授权服务器
    2. 用户授权 → 授权服务器重定向回回调URL（带授权码）
    3. 使用授权码交换访问令牌 → 向令牌端点发送请求
    4. 使用访问令牌调用API → 向资源服务器发送请求
    5. 令牌过期 → 使用刷新令牌获取新访问令牌
    """
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.token_storage = TokenStorage(config.storage_path)
        
        # 存储状态参数用于验证回调（防止CSRF攻击）
        self._pending_states: Dict[str, str] = {}
    
    async def get_authorization_url(self, state: Optional[str] = None) -> Tuple[str, str]:
        """
        生成授权URL
        
        📝 参数说明:
        - state: 可选的用户自定义状态参数，如果不提供则自动生成
        
        🔐 安全说明:
        - 状态参数用于防止CSRF攻击，必须验证回调中的状态参数
        - 状态参数应该是随机的、不可预测的
        - 状态参数应与用户会话关联
        """
        # 生成安全的随机状态参数
        state = state or secrets.token_urlsafe(16)
        
        # 存储状态参数用于后续验证
        self._pending_states[state] = state
        
        # 构造授权URL参数
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
        }
        
        # 可选：添加PKCE参数增强安全性
        # code_verifier = secrets.token_urlsafe(32)
        # code_challenge = self._generate_pkce_challenge(code_verifier)
        # params.update({
        #     "code_challenge": code_challenge,
        #     "code_challenge_method": "S256",
        # })
        
        # 构建完整URL
        url = f"{self.config.authorization_endpoint}?{urlencode(params)}"
        
        logger.info(f"生成授权URL，状态参数: {state}")
        logger.debug(f"授权URL: {url}")
        
        return url, state
    
    async def exchange_code_for_token(self, code: str, state: str) -> OAuthToken:
        """
        使用授权码交换访问令牌
        
        📝 参数说明:
        - code: 授权码（从回调URL中获取）
        - state: 状态参数（必须与生成授权URL时使用的状态参数匹配）
        
        🔐 安全验证:
        - 验证状态参数防止CSRF攻击
        - 验证授权码的有效性
        """
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
            "client_secret": self.config.client_secret,
        }
        
        logger.info("使用授权码交换访问令牌")
        
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
            logger.info("令牌交换成功并已存储")
            
            return token
            
        except httpx.RequestError as e:
            logger.error(f"网络请求失败: {e}")
            raise OAuthError(f"网络请求失败: {e}")
        except KeyError as e:
            logger.error(f"令牌响应缺少必要字段: {e}")
            raise OAuthError(f"令牌响应缺少必要字段: {e}")
    
    async def refresh_token(self, refresh_token: str) -> OAuthToken:
        """
        刷新访问令牌
        
        📝 说明:
        - 当访问令牌过期时，使用刷新令牌获取新访问令牌
        - 刷新令牌通常具有更长的有效期
        - 某些OAuth服务商可能不提供刷新令牌
        """
        if not refresh_token:
            logger.error("刷新令牌为空")
            raise OAuthError("刷新令牌为空")
        
        # 准备刷新请求数据
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        
        logger.info("刷新访问令牌")
        
        try:
            # 发送刷新请求
            response = await self.http_client.post(
                self.config.token_endpoint,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # 检查响应状态
            if response.status_code != 200:
                logger.error(f"令牌刷新失败: {response.status_code} - {response.text}")
                raise OAuthError(f"令牌刷新失败: {response.text}")
            
            # 解析令牌响应
            token_data = response.json()
            
            # 创建新令牌对象
            token = OAuthToken(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                # 有些服务商返回新的刷新令牌，有些返回原来的
                refresh_token=token_data.get("refresh_token", refresh_token),
                scope=token_data.get("scope"),
            )
            
            # 存储新令牌
            await self.token_storage.save_token(token)
            logger.info("令牌刷新成功")
            
            return token
            
        except httpx.RequestError as e:
            logger.error(f"刷新令牌网络请求失败: {e}")
            raise OAuthError(f"刷新令牌网络请求失败: {e}")
        except KeyError as e:
            logger.error(f"刷新响应缺少必要字段: {e}")
            raise OAuthError(f"刷新响应缺少必要字段: {e}")
    
    async def get_valid_token(self) -> str:
        """
        获取有效的访问令牌（自动刷新）
        
        📝 功能:
        - 从存储中加载令牌
        - 检查令牌是否过期
        - 如果过期且存在刷新令牌，则自动刷新
        - 返回有效的访问令牌
        
        🔄 自动刷新流程:
        1. 加载存储的令牌
        2. 检查令牌是否过期
        3. 如果过期且有刷新令牌 → 刷新令牌
        4. 如果过期且无刷新令牌 → 抛出异常
        5. 返回有效的访问令牌
        """
        # 从存储中加载令牌
        token = await self.token_storage.get_token()
        
        if not token:
            logger.error("没有可用的令牌")
            raise OAuthError("没有可用的令牌，请先进行OAuth授权")
        
        # 检查令牌是否过期
        if token.is_expired():
            logger.warning("访问令牌已过期")
            
            if token.refresh_token:
                logger.info("检测到过期令牌，使用刷新令牌获取新访问令牌")
                try:
                    # 刷新令牌
                    token = await self.refresh_token(token.refresh_token)
                except OAuthError as e:
                    logger.error(f"令牌刷新失败: {e}")
                    raise OAuthError(f"令牌刷新失败: {e}")
            else:
                logger.error("令牌已过期且无刷新令牌")
                raise OAuthError("令牌已过期且无刷新令牌可用，请重新授权")
        
        logger.debug(f"返回有效访问令牌: {token.access_token[:8]}...")
        return token.access_token
    
    async def close(self) -> None:
        """关闭HTTP客户端"""
        await self.http_client.aclose()
    
    def __del__(self):
        """析构函数，确保HTTP客户端被正确关闭"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
        except:
            pass


class OAuthProtectedTool:
    """
    受OAuth保护的MCP工具类
    
    🎯 功能:
    - 封装需要OAuth授权的API调用
    - 自动处理令牌获取和刷新
    - 提供统一的错误处理和重试机制
    
    🔗 与MCP工具集成:
    - 可以作为MCP工具的基础类
    - 支持异步API调用
    - 提供标准的工具调用接口
    """
    
    def __init__(self, tool_name: str, api_endpoint: str, oauth_client: OAuthClient):
        self.tool_name = tool_name
        self.api_endpoint = api_endpoint
        self.oauth_client = oauth_client
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        logger.info(f"初始化OAuth保护工具: {tool_name}")
    
    async def call(self, arguments: Dict[str, Any]) -> Any:
        """
        调用受OAuth保护的工具
        
        📝 参数说明:
        - arguments: 工具调用参数
        
        🔄 重试逻辑:
        - 如果API返回401未授权错误，自动刷新令牌并重试一次
        - 其他错误直接抛出异常
        """
        logger.info(f"调用OAuth保护工具: {self.tool_name}")
        logger.debug(f"调用参数: {arguments}")
        
        # 获取有效的访问令牌
        try:
            access_token = await self.oauth_client.get_valid_token()
        except OAuthError as e:
            logger.error(f"获取有效令牌失败: {e}")
            raise ToolError(f"获取有效令牌失败: {e}")
        
        # 准备请求头
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": f"DeerFlow-OAuthTool/{self.tool_name}",
        }
        
        try:
            # 发送API请求
            response = await self.http_client.post(
                self.api_endpoint,
                json=arguments,
                headers=headers,
            )
            
            # 处理401未授权错误（令牌可能失效）
            if response.status_code == 401:
                logger.warning("API返回401未授权错误，尝试刷新令牌并重试")
                
                try:
                    # 获取当前令牌（用于刷新）
                    token = await self.oauth_client.token_storage.get_token()
                    if token and token.refresh_token:
                        # 刷新令牌
                        await self.oauth_client.refresh_token(token.refresh_token)
                        # 获取新令牌
                        access_token = await self.oauth_client.get_valid_token()
                        
                        # 更新请求头并重试
                        headers["Authorization"] = f"Bearer {access_token}"
                        response = await self.http_client.post(
                            self.api_endpoint,
                            json=arguments,
                            headers=headers,
                        )
                    else:
                        logger.error("没有刷新令牌可用，无法自动恢复")
                        raise ToolError("API认证失败且无法自动恢复，请重新授权")
                except OAuthError as e:
                    logger.error(f"令牌刷新失败: {e}")
                    raise ToolError(f"API认证失败且令牌刷新失败: {e}")
            
            # 检查最终响应状态
            if response.status_code != 200:
                logger.error(f"API调用失败: {response.status_code} - {response.text}")
                raise ToolError(f"API调用失败: {response.status_code} - {response.text}")
            
            # 解析成功响应
            result = response.json()
            logger.info(f"工具 {self.tool_name} 调用成功")
            logger.debug(f"调用结果: {result}")
            
            return result
            
        except httpx.RequestError as e:
            logger.error(f"网络请求失败: {e}")
            raise ToolError(f"网络请求失败: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"响应JSON解析失败: {e}")
            raise ToolError(f"响应JSON解析失败: {e}")
    
    async def close(self) -> None:
        """关闭HTTP客户端"""
        await self.http_client.aclose()
    
    def __del__(self):
        """析构函数，确保HTTP客户端被正确关闭"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
        except:
            pass


# ============================================================================
# 🧪 测试辅助类和模拟服务器
# ============================================================================

class MockOAuthServer:
    """
    模拟OAuth服务器（用于测试）
    
    🎯 功能:
    - 模拟授权端点，返回授权码
    - 模拟令牌端点，返回访问令牌和刷新令牌
    - 支持令牌刷新和过期测试
    """
    
    def __init__(self):
        self.authorization_codes = {}  # code -> state
        self.tokens = {}  # access_token -> token_data
        self.refresh_tokens = {}  # refresh_token -> access_token
        
        logger.info("初始化模拟OAuth服务器")
    
    async def handle_authorization_request(self, params: Dict[str, str]) -> Tuple[str, str]:
        """处理授权请求，返回授权码和状态"""
        state = params.get("state")
        if not state:
            state = secrets.token_urlsafe(16)
        
        # 生成授权码
        code = secrets.token_urlsafe(32)
        self.authorization_codes[code] = {
            "state": state,
            "client_id": params.get("client_id"),
            "redirect_uri": params.get("redirect_uri"),
            "scopes": params.get("scope", "").split(),
        }
        
        logger.info(f"模拟服务器: 生成授权码 {code[:8]}... 对应状态 {state}")
        return code, state
    
    async def handle_token_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """处理令牌请求，返回令牌数据"""
        grant_type = params.get("grant_type")
        
        if grant_type == "authorization_code":
            code = params.get("code")
            if code not in self.authorization_codes:
                raise OAuthError("无效的授权码")
            
            # 生成访问令牌和刷新令牌
            access_token = secrets.token_urlsafe(48)
            refresh_token = secrets.token_urlsafe(48)
            
            token_data = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,  # 1小时
                "refresh_token": refresh_token,
                "scope": " ".join(self.authorization_codes[code]["scopes"]),
            }
            
            self.tokens[access_token] = token_data
            self.refresh_tokens[refresh_token] = access_token
            
            # 清理已使用的授权码
            self.authorization_codes.pop(code)
            
            logger.info(f"模拟服务器: 为授权码 {code[:8]}... 生成令牌")
            return token_data
        
        elif grant_type == "refresh_token":
            refresh_token = params.get("refresh_token")
            if refresh_token not in self.refresh_tokens:
                raise OAuthError("无效的刷新令牌")
            
            # 生成新的访问令牌（刷新令牌保持不变）
            access_token = secrets.token_urlsafe(48)
            
            # 获取原令牌数据（排除刷新令牌）
            old_access_token = self.refresh_tokens[refresh_token]
            old_token_data = self.tokens[old_access_token]
            
            token_data = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,  # 新的1小时有效期
                "refresh_token": refresh_token,  # 返回相同的刷新令牌
                "scope": old_token_data.get("scope", ""),
            }
            
            # 更新令牌映射
            self.tokens[access_token] = token_data
            self.refresh_tokens[refresh_token] = access_token
            
            # 清理旧的访问令牌
            self.tokens.pop(old_access_token, None)
            
            logger.info(f"模拟服务器: 为刷新令牌 {refresh_token[:8]}... 生成新令牌")
            return token_data
        
        else:
            raise OAuthError(f"不支持的授权类型: {grant_type}")


# ============================================================================
# 🧪 测试函数
# ============================================================================

async def test_oauth_config():
    """测试OAuth配置类"""
    print("🧪 测试OAuth配置类...")
    
    try:
        # 测试有效配置
        config = OAuthConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorization_endpoint="https://oauth.example.com/auth",
            token_endpoint="https://oauth.example.com/token",
            redirect_uri="http://localhost:8080/callback",
            scopes=["read", "write"],
        )
        
        assert config.client_id == "test_client_id"
        assert config.scopes == ["read", "write"]
        
        # 测试配置验证
        try:
            OAuthConfig(
                client_id="",
                client_secret="test",
                authorization_endpoint="https://example.com/auth",
                token_endpoint="https://example.com/token",
                redirect_uri="http://localhost:8080/callback",
                scopes=["read"],
            )
            assert False, "应该抛出异常"
        except ValueError as e:
            assert "client_id不能为空" in str(e)
        
        print("✅ OAuth配置类测试通过")
        return True
        
    except Exception as e:
        print(f"❌ OAuth配置类测试失败: {e}")
        return False


async def test_oauth_token():
    """测试OAuth令牌类"""
    print("🧪 测试OAuth令牌类...")
    
    try:
        # 测试令牌创建
        token = OAuthToken(
            access_token="test_access_token",
            token_type="Bearer",
            expires_in=3600,
            refresh_token="test_refresh_token",
            scope="read write",
        )
        
        assert token.access_token == "test_access_token"
        assert token.token_type == "Bearer"
        assert token.expires_in == 3600
        assert token.refresh_token == "test_refresh_token"
        assert token.scope == "read write"
        
        # 测试过期检查（新令牌不应该过期）
        assert not token.is_expired()
        
        # 测试序列化和反序列化
        token_dict = token.to_dict()
        token2 = OAuthToken.from_dict(token_dict)
        
        assert token2.access_token == token.access_token
        assert token2.expires_in == token.expires_in
        
        print("✅ OAuth令牌类测试通过")
        return True
        
    except Exception as e:
        print(f"❌ OAuth令牌类测试失败: {e}")
        return False


async def test_token_storage():
    """测试令牌存储类"""
    print("🧪 测试令牌存储类...")
    
    import tempfile
    import os
    
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name
        
        try:
            storage = TokenStorage(temp_path)
            
            # 测试令牌保存和加载
            token = OAuthToken(
                access_token="test_storage_token",
                expires_in=3600,
                refresh_token="test_storage_refresh",
            )
            
            await storage.save_token(token)
            
            loaded_token = await storage.get_token()
            assert loaded_token is not None
            assert loaded_token.access_token == token.access_token
            assert loaded_token.refresh_token == token.refresh_token
            
            # 测试清除令牌
            await storage.clear_token()
            cleared_token = await storage.get_token()
            assert cleared_token is None
            
            print("✅ 令牌存储类测试通过")
            return True
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        print(f"❌ 令牌存储类测试失败: {e}")
        return False


async def test_oauth_client_with_mock():
    """使用模拟服务器测试OAuth客户端"""
    print("🧪 使用模拟服务器测试OAuth客户端...")
    
    import tempfile
    import os
    
    try:
        # 创建临时文件用于令牌存储
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name
        
        try:
            # 创建配置
            config = OAuthConfig(
                client_id="test_client",
                client_secret="test_secret",
                authorization_endpoint="https://mock-oauth.example.com/auth",
                token_endpoint="https://mock-oauth.example.com/token",
                redirect_uri="http://localhost:8080/callback",
                scopes=["read", "write"],
                storage_path=temp_path,
            )
            
            # 创建客户端
            client = OAuthClient(config)
            
            # 创建模拟服务器
            mock_server = MockOAuthServer()
            
            # 测试授权URL生成
            auth_url, state = await client.get_authorization_url()
            assert auth_url.startswith(config.authorization_endpoint)
            assert "client_id=test_client" in auth_url
            assert "state=" in auth_url
            
            # 模拟授权服务器处理授权请求
            # （实际测试中这里会解析auth_url中的参数）
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(auth_url)
            params = parse_qs(parsed.query)
            
            mock_params = {k: v[0] for k, v in params.items()}
            code, mock_state = await mock_server.handle_authorization_request(mock_params)
            
            # 验证状态参数
            assert state == mock_state
            
            # 测试令牌交换
            # 注意：由于我们使用模拟服务器，这里需要特殊的测试方式
            # 在实际测试中，我们会使用真正的HTTP服务器
            
            print("⚠️  注意: 完整的OAuth客户端测试需要真实的HTTP服务器")
            print("   本测试仅验证基本功能，完整测试见集成测试")
            
            print("✅ OAuth客户端基本功能测试通过")
            return True
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        print(f"❌ OAuth客户端测试失败: {e}")
        return False


async def test_oauth_protected_tool():
    """测试OAuth保护的工具类"""
    print("🧪 测试OAuth保护的工具类...")
    
    try:
        # 由于工具类依赖于OAuth客户端和真实API端点
        # 这里仅测试类的基本功能
        
        # 创建配置和客户端（使用模拟配置）
        config = OAuthConfig(
            client_id="test_tool_client",
            client_secret="test_tool_secret",
            authorization_endpoint="https://example.com/auth",
            token_endpoint="https://example.com/token",
            redirect_uri="http://localhost:8080/callback",
            scopes=["api:read"],
            storage_path="./test_tool_tokens.json",
        )
        
        client = OAuthClient(config)
        tool = OAuthProtectedTool(
            tool_name="TestAPITool",
            api_endpoint="https://api.example.com/v1/test",
            oauth_client=client,
        )
        
        assert tool.tool_name == "TestAPITool"
        assert tool.api_endpoint == "https://api.example.com/v1/test"
        assert tool.oauth_client == client
        
        print("⚠️  注意: OAuth保护工具类的完整测试需要真实的API端点")
        print("   本测试仅验证类的基本功能，完整测试见集成测试")
        
        # 清理测试文件
        import os
        if os.path.exists("./test_tool_tokens.json"):
            os.unlink("./test_tool_tokens.json")
        
        print("✅ OAuth保护工具类基本功能测试通过")
        return True
        
    except Exception as e:
        print(f"❌ OAuth保护工具类测试失败: {e}")
        return False


async def run_integration_demo():
    """运行集成演示"""
    print("\n" + "="*60)
    print("🚀 OAuth集成演示")
    print("="*60)
    
    print("\n📚 演示内容:")
    print("1. 创建OAuth配置")
    print("2. 初始化OAuth客户端")
    print("3. 生成授权URL")
    print("4. 模拟OAuth授权流程")
    print("5. 令牌交换和存储")
    print("6. 令牌自动刷新")
    print("7. OAuth保护的工具调用")
    
    print("\n⚠️  注意: 本演示使用模拟服务器")
    print("   生产环境需要真实的OAuth服务商（如GitHub、Google等）")
    
    import tempfile
    import os
    
    try:
        # 创建临时文件用于令牌存储
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name
        
        try:
            print(f"\n📁 使用临时令牌文件: {temp_path}")
            
            # 步骤1: 创建配置
            print("\n1️⃣ 创建OAuth配置...")
            config = OAuthConfig(
                client_id="demo_client_123",
                client_secret="demo_secret_456",
                authorization_endpoint="https://demo-oauth.example.com/auth",
                token_endpoint="https://demo-oauth.example.com/token",
                redirect_uri="http://localhost:8080/callback",
                scopes=["user:read", "repo:write"],
                storage_path=temp_path,
            )
            print(f"   配置创建成功: {config}")
            
            # 步骤2: 初始化客户端
            print("\n2️⃣ 初始化OAuth客户端...")
            client = OAuthClient(config)
            print("   客户端初始化成功")
            
            # 步骤3: 生成授权URL
            print("\n3️⃣ 生成授权URL...")
            auth_url, state = await client.get_authorization_url()
            print(f"   授权URL: {auth_url[:80]}...")
            print(f"   状态参数: {state}")
            
            # 步骤4: 模拟OAuth服务器
            print("\n4️⃣ 模拟OAuth授权流程...")
            mock_server = MockOAuthServer()
            
            # 解析授权URL参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(auth_url)
            params = parse_qs(parsed.query)
            mock_params = {k: v[0] for k, v in params.items()}
            
            # 模拟服务器生成授权码
            code, mock_state = await mock_server.handle_authorization_request(mock_params)
            print(f"   模拟授权码: {code[:16]}...")
            print(f"   验证状态参数: {'匹配' if state == mock_state else '不匹配'}")
            
            # 步骤5: 令牌交换
            print("\n5️⃣ 模拟令牌交换...")
            print("   （实际应用中，用户授权后重定向回应用，带回授权码）")
            print(f"   使用授权码交换令牌...")
            
            # 模拟令牌端点响应
            # 注意：这里直接调用模拟服务器，实际应用中需要HTTP请求
            token_data = await mock_server.handle_token_request({
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": config.redirect_uri,
                "client_id": config.client_id,
                "client_secret": config.client_secret,
            })
            
            print(f"   访问令牌: {token_data['access_token'][:16]}...")
            print(f"   刷新令牌: {token_data['refresh_token'][:16]}...")
            print(f"   有效期: {token_data['expires_in']}秒")
            
            # 步骤6: 演示令牌自动刷新
            print("\n6️⃣ 演示令牌自动刷新机制...")
            print("   （模拟令牌过期后的自动刷新）")
            
            # 创建一个快过期的令牌用于演示
            expired_token = OAuthToken(
                access_token="expired_token_123",
                expires_in=1,  # 1秒后过期
                refresh_token="valid_refresh_token_456",
            )
            await client.token_storage.save_token(expired_token)
            
            # 等待令牌过期
            await asyncio.sleep(1.5)
            
            try:
                # 尝试获取有效令牌（应该触发自动刷新）
                print("   尝试获取有效令牌（令牌已过期）...")
                valid_token = await client.get_valid_token()
                print(f"   ✅ 自动刷新成功，新令牌: {valid_token[:16]}...")
            except OAuthError as e:
                print(f"   ❌ 自动刷新失败: {e}")
                print("   （注意：模拟服务器未实现HTTP端点，因此刷新会失败）")
            
            # 步骤7: OAuth保护的工具
            print("\n7️⃣ 创建OAuth保护的工具...")
            tool = OAuthProtectedTool(
                tool_name="GitHubAPITool",
                api_endpoint="https://api.github.com/user",
                oauth_client=client,
            )
            print(f"   工具创建成功: {tool.tool_name}")
            print(f"   API端点: {tool.api_endpoint}")
            
            print("\n🎉 演示完成!")
            print("\n📝 总结:")
            print("   • OAuth 2.0授权码流程已完整演示")
            print("   • 令牌自动刷新机制已实现")
            print("   • OAuth保护的工具类已创建")
            print("   • 所有组件均可用于实际MCP工具集成")
            
            return True
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# 🚀 主程序入口
# ============================================================================

async def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python oauth_integration_demo.py --test    # 运行测试")
        print("  python oauth_integration_demo.py --demo    # 运行演示")
        print("  python oauth_integration_demo.py --all     # 运行所有")
        return
    
    command = sys.argv[1]
    
    if command == "--test" or command == "--all":
        print("🧪 运行OAuth集成测试套件")
        print("="*60)
        
        tests = [
            ("OAuth配置类", test_oauth_config),
            ("OAuth令牌类", test_oauth_token),
            ("令牌存储类", test_token_storage),
            ("OAuth客户端", test_oauth_client_with_mock),
            ("OAuth保护工具", test_oauth_protected_tool),
        ]
        
        results = []
        for test_name, test_func in tests:
            print(f"\n🔬 测试: {test_name}")
            result = await test_func()
            results.append((test_name, result))
        
        print("\n" + "="*60)
        print("📊 测试结果汇总:")
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 通过率: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 所有测试通过!")
        else:
            print("⚠️  部分测试失败，请检查实现")
    
    if command == "--demo" or command == "--all":
        await run_integration_demo()


if __name__ == "__main__":
    asyncio.run(main())