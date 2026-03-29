#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeerFlow Python Agent 架构师训练营 - 第69节课演示代码
主题: MCP客户端架构 (MCP Client Architecture)

本文件演示MCP（Model Context Protocol）客户端架构的实现，包括：
1. MCP协议基础：JSON-RPC 2.0消息格式
2. 传输层抽象：stdio/HTTP/WebSocket传输实现
3. 客户端核心：连接管理、工具发现、调用机制
4. 异步通信：asyncio子进程管理和HTTP客户端

作者: DeerFlow教学团队
版本: v1.0.0
日期: 2024-04-11
"""

import asyncio
import json
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List, Union, Callable, Awaitable
import aiohttp
from aiohttp import ClientSession, ClientTimeout
import websockets
from enum import Enum


# ============================================================================
# 第一部分：MCP协议消息定义
# ============================================================================

class MessageType(Enum):
    """MCP消息类型枚举"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPMessage:
    """MCP消息基类（遵循JSON-RPC 2.0规范）"""
    jsonrpc: str = "2.0"
    
    @property
    def type(self) -> MessageType:
        """获取消息类型（由子类实现）"""
        raise NotImplementedError


@dataclass
class MCPRequest(MCPMessage):
    """MCP请求消息
    
    属性:
        method: 请求方法名（如"tools/list", "tools/call"）
        params: 请求参数字典
        id: 请求ID（用于匹配响应）
    """
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    
    @property
    def type(self) -> MessageType:
        return MessageType.REQUEST
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        return {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params,
            "id": self.id
        }


@dataclass
class MCPResponse(MCPMessage):
    """MCP响应消息
    
    属性:
        result: 响应结果（成功时）
        error: 错误信息（失败时）
        id: 响应ID（匹配请求ID）
    """
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: str = ""
    
    @property
    def type(self) -> MessageType:
        return MessageType.RESPONSE
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        response = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        
        if self.error:
            response["error"] = self.error
        else:
            response["result"] = self.result
            
        return response
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPResponse":
        """从字典创建响应对象"""
        if "error" in data:
            return cls(error=data["error"], id=data.get("id", ""))
        else:
            return cls(result=data.get("result"), id=data.get("id", ""))
    
    @property
    def is_error(self) -> bool:
        """判断是否为错误响应"""
        return self.error is not None


@dataclass
class MCPNotification(MCPMessage):
    """MCP通知消息（无响应的单向消息）"""
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def type(self) -> MessageType:
        return MessageType.NOTIFICATION
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params
        }


@dataclass
class ToolInfo:
    """MCP工具信息
    
    属性:
        name: 工具名称
        description: 工具描述
        input_schema: 输入参数JSON Schema
    """
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 第二部分：传输层抽象
# ============================================================================

class TransportError(Exception):
    """传输层异常基类"""
    pass


class ConnectionError(TransportError):
    """连接异常"""
    pass


class TimeoutError(TransportError):
    """超时异常"""
    pass


class Transport(ABC):
    """传输层抽象基类
    
    所有传输层实现（stdio/HTTP/WebSocket）都需要继承此类，
    提供统一的连接、通信和断开接口。
    """
    
    def __init__(self):
        self._connected = False
        self._request_counter = 0
    
    @property
    def connected(self) -> bool:
        """检查是否已连接"""
        return self._connected
    
    @abstractmethod
    async def connect(self) -> None:
        """建立连接"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    async def send_request(self, request: MCPRequest) -> MCPResponse:
        """发送请求并获取响应"""
        pass
    
    async def call(self, method: str, params: Dict[str, Any]) -> Any:
        """调用远程方法（高级接口）"""
        request = MCPRequest(method=method, params=params)
        response = await self.send_request(request)
        
        if response.is_error:
            error_msg = response.error.get("message", "Unknown error")
            raise TransportError(f"MCP调用失败: {error_msg}")
            
        return response.result
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()


# ============================================================================
# 第三部分：具体传输层实现
# ============================================================================

class StdioTransport(Transport):
    """stdio传输层实现
    
    通过标准输入输出与子进程通信，适用于本地MCP服务器。
    这是MCP协议最常见的传输方式，适合本地工具集成。
    """
    
    def __init__(
        self,
        command: str,
        args: List[str] = None,
        env: Dict[str, str] = None,
        timeout: float = 30.0
    ):
        super().__init__()
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.timeout = timeout
        
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """启动子进程并建立stdio连接"""
        if self._connected:
            return
        
        try:
            # 合并环境变量
            merged_env = {**os.environ, **self.env}
            
            # 创建子进程
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                env=merged_env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self._connected = True
            print(f"✅ StdioTransport: 已启动MCP服务器进程 '{self.command}'")
            
        except Exception as e:
            raise ConnectionError(f"启动MCP服务器失败: {e}")
    
    async def send_request(self, request: MCPRequest) -> MCPResponse:
        """通过stdio发送JSON-RPC请求"""
        if not self._connected or not self.process:
            raise ConnectionError("传输层未连接")
        
        async with self._request_lock:
            try:
                # 序列化请求
                request_json = json.dumps(request.to_dict()) + "\n"
                
                # 发送请求
                self.process.stdin.write(request_json.encode())
                await self.process.stdin.drain()
                
                # 设置超时读取响应
                try:
                    line = await asyncio.wait_for(
                        self.process.stdout.readline(),
                        timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(f"读取响应超时 ({self.timeout}s)")
                
                if not line:
                    raise TransportError("服务器连接已关闭")
                
                # 解析响应
                try:
                    response_data = json.loads(line.decode())
                except json.JSONDecodeError as e:
                    raise TransportError(f"响应JSON解析失败: {e}")
                
                return MCPResponse.from_dict(response_data)
                
            except Exception as e:
                if isinstance(e, TransportError):
                    raise
                raise TransportError(f"请求发送失败: {e}")
    
    async def disconnect(self) -> None:
        """断开连接并终止子进程"""
        if not self._connected or not self.process:
            return
        
        try:
            # 优雅终止
            self.process.terminate()
            await asyncio.wait_for(self.process.wait(), timeout=5.0)
            
        except (asyncio.TimeoutError, ProcessLookupError):
            # 强制终止
            if self.process:
                self.process.kill()
                
        finally:
            self._connected = False
            self.process = None
            print("👋 StdioTransport: 已断开MCP服务器连接")


class HTTPTransport(Transport):
    """HTTP传输层实现
    
    通过HTTP POST请求与远程MCP服务器通信，适用于分布式部署。
    支持HTTP/HTTPS协议，可以配置自定义请求头。
    """
    
    def __init__(
        self,
        url: str,
        headers: Dict[str, str] = None,
        timeout: float = 30.0,
        session: ClientSession = None
    ):
        super().__init__()
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self._session = session
        self._own_session = session is None
    
    async def connect(self) -> None:
        """建立HTTP连接（创建会话）"""
        if self._connected:
            return
        
        if self._own_session:
            timeout = ClientTimeout(total=self.timeout)
            self._session = ClientSession(
                timeout=timeout,
                headers=self.headers
            )
        
        self._connected = True
        print(f"✅ HTTPTransport: 已连接到MCP服务器 '{self.url}'")
    
    async def send_request(self, request: MCPRequest) -> MCPResponse:
        """通过HTTP发送JSON-RPC请求"""
        if not self._connected or not self._session:
            raise ConnectionError("HTTP会话未建立")
        
        try:
            # 准备请求数据
            request_data = request.to_dict()
            
            # 发送HTTP POST请求
            async with self._session.post(
                self.url,
                json=request_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                # 检查HTTP状态码
                if response.status != 200:
                    raise TransportError(f"HTTP请求失败: {response.status}")
                
                # 读取响应数据
                response_data = await response.json()
                
                return MCPResponse.from_dict(response_data)
                
        except aiohttp.ClientError as e:
            raise TransportError(f"HTTP客户端错误: {e}")
        except json.JSONDecodeError as e:
            raise TransportError(f"响应JSON解析失败: {e}")
        except Exception as e:
            raise TransportError(f"HTTP请求失败: {e}")
    
    async def disconnect(self) -> None:
        """断开HTTP连接（关闭会话）"""
        if not self._connected:
            return
        
        if self._session and self._own_session:
            await self._session.close()
            self._session = None
        
        self._connected = False
        print("👋 HTTPTransport: 已断开MCP服务器连接")


class WebSocketTransport(Transport):
    """WebSocket传输层实现
    
    通过WebSocket双向通信与MCP服务器交互，支持实时通知。
    适用于需要长连接和双向通信的场景。
    """
    
    def __init__(
        self,
        url: str,
        timeout: float = 30.0
    ):
        super().__init__()
        self.url = url
        self.timeout = timeout
        self._websocket = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._receive_task = None
    
    async def connect(self) -> None:
        """建立WebSocket连接"""
        if self._connected:
            return
        
        try:
            self._websocket = await websockets.connect(self.url)
            self._connected = True
            
            # 启动接收任务
            self._receive_task = asyncio.create_task(self._receive_messages())
            
            print(f"✅ WebSocketTransport: 已连接到MCP服务器 '{self.url}'")
            
        except Exception as e:
            raise ConnectionError(f"WebSocket连接失败: {e}")
    
    async def _receive_messages(self) -> None:
        """接收消息任务（处理响应和通知）"""
        try:
            async for message in self._websocket:
                try:
                    data = json.loads(message)
                    
                    # 处理响应（有ID）
                    if "id" in data:
                        request_id = data["id"]
                        if request_id in self._pending_requests:
                            future = self._pending_requests.pop(request_id)
                            
                            if "error" in data:
                                future.set_exception(TransportError(data["error"]["message"]))
                            else:
                                future.set_result(MCPResponse.from_dict(data))
                    
                    # 处理通知（无ID）
                    else:
                        await self._handle_notification(data)
                        
                except json.JSONDecodeError:
                    print(f"⚠️  WebSocket: 收到无效JSON消息: {message}")
                except Exception as e:
                    print(f"⚠️  WebSocket: 消息处理失败: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("⚠️  WebSocket: 连接已关闭")
            self._connected = False
        except Exception as e:
            print(f"⚠️  WebSocket: 接收任务异常: {e}")
            self._connected = False
    
    async def _handle_notification(self, data: Dict[str, Any]) -> None:
        """处理通知消息"""
        method = data.get("method", "")
        params = data.get("params", {})
        
        print(f"📢 WebSocket通知: {method} {params}")
        # 在这里可以添加自定义通知处理逻辑
    
    async def send_request(self, request: MCPRequest) -> MCPResponse:
        """通过WebSocket发送JSON-RPC请求"""
        if not self._connected or not self._websocket:
            raise ConnectionError("WebSocket未连接")
        
        # 创建Future用于等待响应
        future = asyncio.Future()
        self._pending_requests[request.id] = future
        
        try:
            # 发送请求
            request_json = json.dumps(request.to_dict())
            await self._websocket.send(request_json)
            
            # 等待响应（带超时）
            return await asyncio.wait_for(future, timeout=self.timeout)
            
        except asyncio.TimeoutError:
            self._pending_requests.pop(request.id, None)
            raise TimeoutError(f"WebSocket响应超时 ({self.timeout}s)")
        except Exception as e:
            self._pending_requests.pop(request.id, None)
            raise TransportError(f"WebSocket发送失败: {e}")
    
    async def disconnect(self) -> None:
        """断开WebSocket连接"""
        if not self._connected:
            return
        
        # 取消接收任务
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        # 关闭WebSocket连接
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        
        # 清理未完成的请求
        for future in self._pending_requests.values():
            future.cancel()
        self._pending_requests.clear()
        
        self._connected = False
        print("👋 WebSocketTransport: 已断开MCP服务器连接")


# ============================================================================
# 第四部分：MCP客户端核心
# ============================================================================

class MCPClient:
    """MCP客户端核心类
    
    提供完整的MCP客户端功能：
    1. 传输层管理（自动选择和管理传输层）
    2. 工具发现和注册
    3. 工具调用接口
    4. 会话管理和错误处理
    """
    
    def __init__(self, server_config: Dict[str, Any]):
        """初始化MCP客户端
        
        参数:
            server_config: 服务器配置字典，包含：
                - transport: 传输类型（stdio/http/websocket）
                - 根据传输类型的不同配置：
                    * stdio: command, args, env
                    * http: url, headers
                    * websocket: url
        """
        self.server_config = server_config
        self.transport = self._create_transport(server_config)
        self.tools: Dict[str, ToolInfo] = {}
        self._session_initialized = False
    
    def _create_transport(self, config: Dict[str, Any]) -> Transport:
        """根据配置创建传输层实例"""
        transport_type = config.get("transport", "stdio")
        
        if transport_type == "stdio":
            return StdioTransport(
                command=config["command"],
                args=config.get("args", []),
                env=config.get("env", {}),
                timeout=config.get("timeout", 30.0)
            )
            
        elif transport_type == "http":
            return HTTPTransport(
                url=config["url"],
                headers=config.get("headers", {}),
                timeout=config.get("timeout", 30.0)
            )
            
        elif transport_type == "websocket":
            return WebSocketTransport(
                url=config["url"],
                timeout=config.get("timeout", 30.0)
            )
            
        else:
            raise ValueError(f"不支持的传输类型: {transport_type}")
    
    async def connect(self) -> None:
        """连接到MCP服务器"""
        if self.transport.connected:
            return
        
        await self.transport.connect()
        await self._initialize_session()
        await self.discover_tools()
        
        print("🎉 MCP客户端连接成功，工具已就绪")
    
    async def _initialize_session(self) -> None:
        """初始化MCP会话"""
        try:
            # 发送初始化请求
            response = await self.transport.call("initialize", {
                "protocolVersion": "2024-11-07",
                "capabilities": {},
                "clientInfo": {
                    "name": "DeerFlow MCP Client",
                    "version": "1.0.0"
                }
            })
            
            self._session_initialized = True
            print("📋 MCP会话初始化成功")
            
        except Exception as e:
            print(f"⚠️  MCP会话初始化失败: {e}")
            # 继续执行，某些服务器可能不需要初始化
    
    async def discover_tools(self) -> List[ToolInfo]:
        """发现MCP服务器提供的工具"""
        try:
            response = await self.transport.call("tools/list", {})
            
            tools = response.get("tools", [])
            self.tools.clear()
            
            for tool_data in tools:
                tool = ToolInfo(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {})
                )
                self.tools[tool.name] = tool
                print(f"🔧 发现工具: {tool.name} - {tool.description}")
            
            return list(self.tools.values())
            
        except Exception as e:
            print(f"⚠️  工具发现失败: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用MCP工具
        
        参数:
            tool_name: 工具名称
            arguments: 工具参数
            
        返回:
            工具调用结果
        """
        if not self.transport.connected:
            await self.connect()
        
        if tool_name not in self.tools:
            # 尝试重新发现工具
            await self.discover_tools()
            
            if tool_name not in self.tools:
                raise ValueError(f"工具不存在: {tool_name}")
        
        try:
            result = await self.transport.call(f"tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            print(f"✅ 工具调用成功: {tool_name}")
            return result
            
        except TransportError as e:
            print(f"❌ 工具调用失败: {tool_name} - {e}")
            raise
    
    async def disconnect(self) -> None:
        """断开MCP连接"""
        await self.transport.disconnect()
        self._session_initialized = False
        self.tools.clear()
        print("👋 MCP客户端已断开连接")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()


# ============================================================================
# 第五部分：演示用例和测试
# ============================================================================

async def demo_stdio_transport() -> None:
    """演示StdioTransport的基本用法"""
    print("\n" + "="*60)
    print("演示1: StdioTransport基本用法")
    print("="*60)
    
    # 配置一个简单的MCP服务器（使用Python脚本模拟）
    config = {
        "transport": "stdio",
        "command": "python",
        "args": ["-c", """
import sys
import json
import time

# 简单的MCP服务器模拟
while True:
    try:
        line = sys.stdin.readline()
        if not line:
            break
            
        request = json.loads(line)
        
        # 模拟处理工具列表请求
        if request["method"] == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "tools": [
                        {
                            "name": "get_weather",
                            "description": "获取天气信息",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "city": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "calculate",
                            "description": "计算器",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "expression": {"type": "string"}
                                }
                            }
                        }
                    ]
                }
            }
            
        # 模拟处理工具调用
        elif request["method"] == "tools/call":
            tool_name = request["params"]["name"]
            
            if tool_name == "get_weather":
                result = {"temperature": 25, "condition": "sunny"}
            elif tool_name == "calculate":
                result = {"result": 42}
            else:
                result = {"error": "Tool not found"}
            
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": result
            }
            
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {"message": "Method not found"}
            }
        
        print(json.dumps(response))
        sys.stdout.flush()
        
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "id": request.get("id", "unknown"),
            "error": {"message": str(e)}
        }
        print(json.dumps(error_response))
        sys.stdout.flush()
        """],
        "timeout": 10.0
    }
    
    # 创建并运行客户端
    client = MCPClient(config)
    
    try:
        # 连接服务器
        await client.connect()
        
        # 显示发现的工具
        print(f"📋 发现 {len(client.tools)} 个工具:")
        for tool_name, tool in client.tools.items():
            print(f"  • {tool_name}: {tool.description}")
        
        # 调用工具
        print("\n🔧 调用工具测试:")
        
        # 测试天气工具
        weather_result = await client.call_tool("get_weather", {"city": "Beijing"})
        print(f"  天气查询结果: {weather_result}")
        
        # 测试计算器工具
        calc_result = await client.call_tool("calculate", {"expression": "6 * 7"})
        print(f"  计算器结果: {calc_result}")
        
    finally:
        # 断开连接
        await client.disconnect()


async def demo_http_transport() -> None:
    """演示HTTPTransport的基本用法"""
    print("\n" + "="*60)
    print("演示2: HTTPTransport基本用法")
    print("="*60)
    
    # 注意：这里需要一个真实的HTTP MCP服务器
    # 为了演示，我们使用一个模拟的配置
    config = {
        "transport": "http",
        "url": "http://localhost:8080/mcp",
        "timeout": 10.0
    }
    
    print("📝 HTTPTransport配置:")
    print(f"  服务器URL: {config['url']}")
    print(f"  超时时间: {config['timeout']}秒")
    
    print("\n⚠️  注意：需要运行真实的HTTP MCP服务器才能测试")
    print("   可以使用以下命令启动测试服务器:")
    print("   $ python -m http.server 8080 --directory /path/to/mcp-server")
    
    # 创建客户端（但不实际连接）
    client = MCPClient(config)
    
    print("\n✅ HTTPTransport客户端创建成功")
    print("   实际使用时，取消注释以下代码:")
    print("""
    try:
        await client.connect()
        tools = await client.discover_tools()
        print(f"发现 {len(tools)} 个工具")
    finally:
        await client.disconnect()
    """)


async def demo_websocket_transport() -> None:
    """演示WebSocketTransport的基本用法"""
    print("\n" + "="*60)
    print("演示3: WebSocketTransport基本用法")
    print("="*60)
    
    # WebSocket MCP服务器配置
    config = {
        "transport": "websocket",
        "url": "ws://localhost:8081/mcp",
        "timeout": 10.0
    }
    
    print("📝 WebSocketTransport配置:")
    print(f"  服务器URL: {config['url']}")
    print(f"  超时时间: {config['timeout']}秒")
    
    print("\n⚠️  注意：需要运行真实的WebSocket MCP服务器才能测试")
    print("   可以使用以下命令启动测试服务器:")
    print("   $ python -m websockets.serve mcp_server 0.0.0.0 8081")
    
    # 创建客户端（但不实际连接）
    client = MCPClient(config)
    
    print("\n✅ WebSocketTransport客户端创建成功")
    print("   实际使用时，取消注释以下代码:")
    print("""
    try:
        await client.connect()
        tools = await client.discover_tools()
        print(f"发现 {len(tools)} 个工具")
        
        # WebSocket特有的实时通知示例
        print("等待服务器通知...")
        await asyncio.sleep(5)
        
    finally:
        await client.disconnect()
    """)


async def demo_mcp_client_lifecycle() -> None:
    """演示完整的MCP客户端生命周期"""
    print("\n" + "="*60)
    print("演示4: MCP客户端完整生命周期")
    print("="*60)
    
    # 使用上下文管理器确保资源正确清理
    config = {
        "transport": "stdio",
        "command": "python",
        "args": ["-c", """
import sys
import json

# 最简单的MCP服务器回应
while True:
    line = sys.stdin.readline()
    if not line:
        break
    
    request = json.loads(line)
    
    # 总是返回同样的响应
    response = {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {"message": "Hello from MCP server!"}
    }
    
    print(json.dumps(response))
    sys.stdout.flush()
        """],
        "timeout": 5.0
    }
    
    print("使用上下文管理器自动管理连接:")
    
    async with MCPClient(config) as client:
        print("✅ 客户端已连接（自动连接）")
        
        # 发现工具
        tools = await client.discover_tools()
        print(f"📋 发现 {len(tools)} 个工具")
        
        # 尝试调用工具
        try:
            result = await client.call_tool("test_tool", {"param": "value"})
            print(f"🔧 工具调用结果: {result}")
        except Exception as e:
            print(f"⚠️  工具调用失败（预期中）: {e}")
    
    print("👋 客户端已断开（自动断开）")


async def demo_error_handling() -> None:
    """演示错误处理机制"""
    print("\n" + "="*60)
    print("演示5: 错误处理机制")
    print("="*60)
    
    print("1. 连接失败处理:")
    try:
        config = {
            "transport": "stdio",
            "command": "non_existent_command",
            "args": []
        }
        
        client = MCPClient(config)
        await client.connect()
        
    except ConnectionError as e:
        print(f"   ✅ 预期错误捕获: {e}")
    
    print("\n2. 超时处理:")
    try:
        config = {
            "transport": "stdio",
            "command": "python",
            "args": ["-c", "import time; time.sleep(10)"],  # 长时间运行
            "timeout": 1.0  # 短超时
        }
        
        client = MCPClient(config)
        await client.connect()
        
    except TimeoutError as e:
        print(f"   ✅ 超时错误捕获: {e}")
    
    print("\n3. JSON解析错误处理:")
    try:
        config = {
            "transport": "stdio",
            "command": "python",
            "args": ["-c", "print('invalid json')"]  # 无效JSON
        }
        
        client = MCPClient(config)
        await client.connect()
        await client.discover_tools()
        
    except TransportError as e:
        print(f"   ✅ JSON解析错误捕获: {e}")
    
    print("\n✅ 所有错误处理演示完成")


# ============================================================================
# 第六部分：单元测试
# ============================================================================

import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMCPClient(unittest.TestCase):
    """MCP客户端单元测试"""
    
    def setUp(self):
        """测试前准备"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """测试后清理"""
        self.loop.close()
    
    def test_mcp_request_creation(self):
        """测试MCP请求创建"""
        request = MCPRequest(method="tools/list", params={"limit": 10})
        
        self.assertEqual(request.method, "tools/list")
        self.assertEqual(request.params, {"limit": 10})
        self.assertEqual(request.type.value, "request")
        self.assertTrue(len(request.id) > 0)
    
    def test_mcp_response_creation(self):
        """测试MCP响应创建"""
        # 成功响应
        success_response = MCPResponse(result={"tools": []}, id="123")
        self.assertFalse(success_response.is_error)
        self.assertEqual(success_response.result, {"tools": []})
        
        # 错误响应
        error_response = MCPResponse(
            error={"code": -32601, "message": "Method not found"},
            id="456"
        )
        self.assertTrue(error_response.is_error)
        self.assertEqual(error_response.error["code"], -32601)
    
    @patch('asyncio.create_subprocess_exec')
    def test_stdio_transport_connect(self, mock_create_subprocess):
        """测试StdioTransport连接"""
        mock_process = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_create_subprocess.return_value = mock_process
        
        transport = StdioTransport("python", ["-c", "print('test')"])
        
        # 运行连接测试
        async def test():
            await transport.connect()
            self.assertTrue(transport.connected)
        
        self.loop.run_until_complete(test())
        mock_create_subprocess.assert_called_once()
    
    def test_transport_factory(self):
        """测试传输层工厂方法"""
        # stdio配置
        stdio_config = {
            "transport": "stdio",
            "command": "python",
            "args": ["-c", "print('test')"]
        }
        
        client = MCPClient(stdio_config)
        self.assertIsInstance(client.transport, StdioTransport)
        
        # http配置
        http_config = {
            "transport": "http",
            "url": "http://localhost:8080"
        }
        
        client = MCPClient(http_config)
        self.assertIsInstance(client.transport, HTTPTransport)
        
        # websocket配置
        ws_config = {
            "transport": "websocket",
            "url": "ws://localhost:8081"
        }
        
        client = MCPClient(ws_config)
        self.assertIsInstance(client.transport, WebSocketTransport)
        
        # 无效配置
        invalid_config = {
            "transport": "invalid"
        }
        
        with self.assertRaises(ValueError):
            MCPClient(invalid_config)


class AsyncTestCase(unittest.TestCase):
    """异步测试基类"""
    
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        self.loop.close()
    
    def run_async(self, coro):
        """运行异步协程"""
        return self.loop.run_until_complete(coro)


class TestMCPClientAsync(AsyncTestCase):
    """MCP客户端异步测试"""
    
    async def test_client_connect_disconnect(self):
        """测试客户端连接和断开"""
        config = {
            "transport": "stdio",
            "command": "python",
            "args": ["-c", "print('test')"]
        }
        
        with patch('asyncio.create_subprocess_exec') as mock_create:
            mock_process = AsyncMock()
            mock_process.stdin = AsyncMock()
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()
            mock_process.terminate = AsyncMock()
            mock_process.wait = AsyncMock()
            mock_create.return_value = mock_process
            
            client = MCPClient(config)
            
            # 测试连接
            await client.connect()
            self.assertTrue(client.transport.connected)
            
            # 测试断开
            await client.disconnect()
            self.assertFalse(client.transport.connected)
    
    async def test_tool_discovery(self):
        """测试工具发现"""
        config = {
            "transport": "stdio",
            "command": "python",
            "args": ["-c", ""]
        }
        
        with patch('asyncio.create_subprocess_exec'):
            client = MCPClient(config)
            
            # Mock传输层的call方法
            mock_response = {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "测试工具",
                        "inputSchema": {}
                    }
                ]
            }
            
            client.transport.call = AsyncMock(return_value=mock_response)
            
            # 测试工具发现
            tools = await client.discover_tools()
            
            self.assertEqual(len(tools), 1)
            self.assertEqual(tools[0].name, "test_tool")
            self.assertEqual(len(client.tools), 1)
            
            await client.disconnect()


# ============================================================================
# 第七部分：主程序入口
# ============================================================================

async def main():
    """主演示函数"""
    print("\n" + "="*80)
    print("DeerFlow Python Agent 架构师训练营 - 第69节课")
    print("MCP客户端架构演示程序")
    print("="*80)
    
    # 运行所有演示
    await demo_stdio_transport()
    await demo_http_transport()
    await demo_websocket_transport()
    await demo_mcp_client_lifecycle()
    await demo_error_handling()
    
    print("\n" + "="*80)
    print("演示完成！")
    print("="*80)


if __name__ == "__main__":
    # 运行主演示
    asyncio.run(main())
    
    # 运行单元测试（可选）
    print("\n" + "="*80)
    print("运行单元测试...")
    print("="*80)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMCPClient))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPClientAsync))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n测试结果: {result.testsRun} 个测试运行")
    print(f"失败: {len(result.failures)}, 错误: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ 所有测试通过！")
    else:
        print("❌ 测试失败，请检查代码")
    
    print("\n" + "="*80)
    print("课程演示结束，感谢学习！")
    print("="*80)