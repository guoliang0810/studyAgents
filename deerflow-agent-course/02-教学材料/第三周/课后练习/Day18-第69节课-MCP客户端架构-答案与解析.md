# Day 18 - 第69节课：MCP客户端架构 - 答案与解析

## 📋 答案解析概述

本文档提供课后练习的参考答案和详细解析，帮助你理解和掌握MCP客户端架构的实现。每个任务都包含：
- **参考答案**：完整的代码实现
- **实现要点**：关键设计决策和实现细节
- **常见问题**：可能遇到的问题和解决方案
- **扩展思考**：进一步优化和扩展的思路

**注意**：这些答案仅供参考，实际实现可能有多种正确方式。鼓励你在理解的基础上进行创新和改进。

## 🎯 学习目标回顾

完成本练习后，你应该能够：
- ✅ 设计并实现完整的MCP协议消息类（请求、响应、通知）
- ✅ 实现传输层抽象基类和多种具体传输层（Stdio/HTTP/WebSocket）
- ✅ 设计和实现完整的MCPClient类，支持连接管理、工具发现和调用
- ✅ 实现可靠的错误处理机制和连接状态管理
- ✅ 掌握异步编程在MCP通信中的应用
- ✅ 扩展和自定义MCP客户端功能

## 📁 参考答案文件结构

```
课后练习参考答案/
├── mcp_messages.py               # MCP协议消息类
├── transport_base.py             # 传输层抽象基类
├── stdio_transport.py            # Stdio传输层实现
├── http_transport.py             # HTTP传输层实现
├── websocket_transport.py        # WebSocket传输层实现
├── mcp_client.py                 # MCP客户端核心类
├── mcp_demo.py                   # 完整MCP系统演示脚本
├── test_mcp_system.py            # 测试脚本
└── configs/
    ├── stdio_server_config.yaml  # Stdio服务器配置
    ├── http_server_config.yaml   # HTTP服务器配置
    ├── websocket_server_config.yaml # WebSocket服务器配置
    └── client_config.yaml        # 客户端配置
```

## 📝 任务1：MCP协议消息类设计

### 参考答案

#### mcp_messages.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP协议消息类实现（遵循JSON-RPC 2.0规范）
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from enum import Enum
import json
import uuid


class MessageType(Enum):
    """MCP消息类型枚举"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


@dataclass
class MCPMessage:
    """MCP消息基类"""
    
    jsonrpc: str = "2.0"
    
    @property
    def type(self) -> MessageType:
        """获取消息类型（由子类实现）"""
        raise NotImplementedError


@dataclass
class MCPRequest(MCPMessage):
    """MCP请求消息"""
    
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    
    def __post_init__(self):
        """验证请求参数"""
        if not self.method:
            raise ValueError("method不能为空")
    
    @property
    def type(self) -> MessageType:
        return MessageType.REQUEST
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于JSON序列化"""
        return {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params,
            "id": self.id
        }


@dataclass
class MCPResponse(MCPMessage):
    """MCP响应消息"""
    
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: str = ""
    
    def __post_init__(self):
        """验证响应参数"""
        if self.result is not None and self.error is not None:
            raise ValueError("result和error不能同时存在")
    
    @property
    def type(self) -> MessageType:
        return MessageType.RESPONSE
    
    @property
    def is_error(self) -> bool:
        """判断是否为错误响应"""
        return self.error is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于JSON序列化"""
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


@dataclass
class MCPNotification(MCPMessage):
    """MCP通知消息（无响应的单向消息）"""
    
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """验证通知参数"""
        if not self.method:
            raise ValueError("method不能为空")
    
    @property
    def type(self) -> MessageType:
        return MessageType.NOTIFICATION
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于JSON序列化"""
        return {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params
        }


@dataclass
class ToolInfo:
    """MCP工具信息"""
    
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """验证工具信息"""
        if not self.name:
            raise ValueError("name不能为空")
```

### 实现要点

1. **JSON-RPC 2.0规范遵循**：
   - 请求必须有id字段，响应必须有匹配的id
   - 通知没有id字段
   - 错误响应格式符合规范（包含code、message、可选的data）

2. **类型安全**：
   - 使用Python数据类和类型提示
   - 在`__post_init__`中进行参数验证
   - 防止result和error同时存在

3. **序列化/反序列化**：
   - `to_dict()`方法用于序列化
   - `from_dict()`工厂方法用于反序列化
   - 支持嵌套结构的序列化

4. **ID生成策略**：
   - 使用UUID生成唯一请求ID
   - 也可以使用递增计数器（需要线程安全）

### 常见问题

**Q1：如何处理JSON序列化中的特殊类型？**
A：JSON只能序列化基本类型（str, int, float, bool, list, dict, None）。对于自定义类型，需要在to_dict()中进行适当转换，或实现自定义JSON编码器。

**Q2：错误响应的格式应该是什么？**
A：JSON-RPC 2.0规范定义的错误格式：
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": {"additional": "info"}
  },
  "id": "request-id"
}
```

**Q3：通知消息和请求消息的区别？**
A：通知消息没有id字段，服务器收到后不发送响应。请求消息有id字段，服务器必须发送响应。

### 扩展思考

1. **批量请求支持**：扩展支持JSON-RPC 2.0的批量请求，多个请求在一个JSON数组中
2. **自定义序列化**：支持MessagePack、CBOR等二进制序列化格式
3. **协议版本协商**：添加协议版本字段，支持多版本兼容

## 📝 任务2：传输层抽象基类设计

### 参考答案

#### transport_base.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传输层抽象基类定义
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio
from mcp_messages import MCPRequest, MCPResponse


class TransportError(Exception):
    """传输层异常基类"""
    pass


class ConnectionError(TransportError):
    """连接异常"""
    pass


class TimeoutError(TransportError):
    """超时异常"""
    pass


class ProtocolError(TransportError):
    """协议错误（如JSON解析失败）"""
    pass


class Transport(ABC):
    """传输层抽象基类"""
    
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
        # 创建请求
        request = MCPRequest(method=method, params=params)
        
        # 发送请求并获取响应
        response = await self.send_request(request)
        
        # 检查错误
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
```

### 实现要点

1. **抽象基类设计**：
   - 使用Python的abc模块定义抽象接口
   - 强制子类实现connect、disconnect、send_request方法
   - 提供connected属性检查连接状态

2. **异常层次结构**：
   - 定义清晰的异常类层次
   - 区分连接错误、超时错误、协议错误
   - 便于上层代码针对不同类型错误进行不同处理

3. **高级接口**：
   - `call()`方法封装了请求创建和错误检查
   - 简化常用场景的使用方式
   - 保持send_request方法的灵活性

4. **异步上下文管理器**：
   - 支持`async with`语法自动管理连接
   - 确保连接正确关闭，避免资源泄漏
   - 简化客户端代码

### 常见问题

**Q1：为什么需要call()方法？send_request()不够用吗？**
A：call()方法提供了更简洁的API，自动处理请求创建和错误检查。send_request()提供了更底层的控制，适用于需要自定义请求处理的情况。

**Q2：如何处理并发请求？**
A：传输层应该支持并发请求。具体实现方式取决于传输协议：
- HTTP：可以使用连接池
- WebSocket：可以在一个连接上并发发送多个请求，使用请求ID匹配响应
- Stdio：需要确保请求-响应顺序，或使用多个子进程

**Q3：如何实现超时控制？**
A：可以在send_request()方法中实现超时控制，使用asyncio.wait_for()包装异步操作。超时时间可以配置在传输层实例中。

### 扩展思考

1. **连接池支持**：在抽象基类中添加连接池管理接口
2. **重试机制**：在call()方法中实现自动重试逻辑
3. **监控指标**：添加请求计数、成功率、延迟等监控指标收集

## 📝 任务3：Stdio传输层实现

### 参考答案

#### stdio_transport.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stdio传输层实现（通过标准输入输出与本地MCP服务器通信）
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from transport_base import Transport, TransportError, ConnectionError, TimeoutError
from mcp_messages import MCPRequest, MCPResponse


class StdioTransport(Transport):
    """Stdio传输层实现"""
    
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
            
            # 验证子进程启动成功
            if self.process.returncode is not None:
                stderr_output = await self.process.stderr.read()
                raise ConnectionError(
                    f"子进程立即退出，返回码: {self.process.returncode}, "
                    f"错误: {stderr_output.decode()}"
                )
            
            self._connected = True
            
        except FileNotFoundError as e:
            raise ConnectionError(f"命令不存在: {self.command}") from e
        except Exception as e:
            raise ConnectionError(f"启动子进程失败: {e}") from e
    
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
                
                # 读取响应（带超时）
                try:
                    line = await asyncio.wait_for(
                        self.process.stdout.readline(),
                        timeout=self.timeout
                    )
                except asyncio.TimeoutError as e:
                    raise TimeoutError(f"读取响应超时 ({self.timeout}s)") from e
                
                if not line:
                    raise TransportError("服务器连接已关闭")
                
                # 解析响应
                try:
                    response_data = json.loads(line.decode())
                except json.JSONDecodeError as e:
                    raise TransportError(f"响应JSON解析失败: {e}") from e
                
                return MCPResponse.from_dict(response_data)
                
            except (BrokenPipeError, ConnectionResetError) as e:
                self._connected = False
                raise ConnectionError("连接已断开") from e
            except Exception as e:
                if isinstance(e, TransportError):
                    raise
                raise TransportError(f"请求发送失败: {e}") from e
    
    async def disconnect(self) -> None:
        """断开连接并终止子进程"""
        if not self._connected or not self.process:
            return
        
        try:
            # 优雅终止
            if self.process.returncode is None:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # 强制终止
                    self.process.kill()
                    await self.process.wait()
        
        except ProcessLookupError:
            # 进程已经结束
            pass
        
        finally:
            self._connected = False
            self.process = None
```

### 实现要点

1. **子进程管理**：
   - 使用`asyncio.create_subprocess_exec`创建子进程
   - 重定向stdin、stdout、stderr到管道
   - 验证子进程启动成功（检查returncode）

2. **请求-响应协议**：
   - 使用换行符作为消息分隔符
   - 每条消息独占一行，方便读取
   - 支持并发请求（使用锁保护）

3. **超时控制**：
   - 使用`asyncio.wait_for`包装读取操作
   - 可配置的超时时间
   - 超时后抛出TimeoutError

4. **错误处理**：
   - 区分连接错误、超时错误、协议错误
   - 子进程异常退出时清理资源
   - 连接断开时更新连接状态

### 常见问题

**Q1：如何处理子进程的标准错误输出？**
A：可以读取stderr管道获取错误信息，在连接失败或请求失败时包含在错误消息中。也可以将stderr重定向到日志文件。

**Q2：为什么需要请求锁？**
A：Stdio管道是顺序的，多个并发请求可能会混淆响应。使用锁确保请求-响应顺序，或实现更复杂的请求ID匹配机制。

**Q3：如何支持长时间运行的服务器？**
A：子进程应该持续运行，处理多个请求。客户端应正确管理连接生命周期，在不再需要时终止子进程。

### 扩展思考

1. **性能优化**：实现请求批处理，多个请求一次发送
2. **健康检查**：定期检查子进程状态，自动重启故障进程
3. **资源限制**：为子进程设置资源限制（CPU、内存）

## 📝 任务4：HTTP传输层实现

### 参考答案

#### http_transport.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP传输层实现（通过HTTP POST请求与远程MCP服务器通信）
"""

import json
from typing import Dict, Any, Optional
import aiohttp
from aiohttp import ClientSession, ClientTimeout
from transport_base import Transport, TransportError, ConnectionError
from mcp_messages import MCPRequest, MCPResponse


class HTTPTransport(Transport):
    """HTTP传输层实现"""
    
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
                    error_text = await response.text()
                    raise TransportError(
                        f"HTTP请求失败: {response.status}, 响应: {error_text}"
                    )
                
                # 读取响应数据
                response_data = await response.json()
                
                return MCPResponse.from_dict(response_data)
                
        except aiohttp.ClientError as e:
            raise TransportError(f"HTTP客户端错误: {e}") from e
        except json.JSONDecodeError as e:
            raise TransportError(f"响应JSON解析失败: {e}") from e
        except Exception as e:
            raise TransportError(f"HTTP请求失败: {e}") from e
    
    async def disconnect(self) -> None:
        """断开HTTP连接（关闭会话）"""
        if not self._connected:
            return
        
        if self._session and self._own_session:
            await self._session.close()
            self._session = None
        
        self._connected = False
```

### 实现要点

1. **HTTP会话管理**：
   - 支持传入已有ClientSession，便于会话复用
   - 自动管理会话生命周期（创建和关闭）
   - 配置超时时间和请求头

2. **请求发送**：
   - 使用HTTP POST方法发送JSON-RPC请求
   - Content-Type设置为application/json
   - 支持自定义请求头（如认证信息）

3. **响应处理**：
   - 检查HTTP状态码，非200状态码抛出异常
   - 解析JSON响应，转换为MCPResponse对象
   - 包含详细的错误信息（HTTP状态码和响应体）

4. **错误处理**：
   - 区分网络错误、HTTP错误、JSON解析错误
   - 提供详细的错误消息，便于调试
   - 确保资源正确释放

### 常见问题

**Q1：如何支持HTTPS和SSL证书验证？**
A：aiohttp ClientSession支持SSL配置，可以通过ssl参数配置证书验证。例如：
```python
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
session = ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context))
```

**Q2：如何实现连接池？**
A：aiohttp内置连接池，可以通过TCPConnector配置连接池大小：
```python
connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
session = ClientSession(connector=connector)
```

**Q3：如何处理长时间空闲连接？**
A：可以配置keep-alive超时时间，或定期发送心跳请求保持连接活跃。

### 扩展思考

1. **认证支持**：扩展支持OAuth、API Key、JWT等多种认证方式
2. **重试机制**：实现指数退避重试，处理临时性网络故障
3. **监控指标**：收集请求延迟、成功率、HTTP状态码分布等指标

## 📝 任务5：WebSocket传输层实现

### 参考答案

#### websocket_transport.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket传输层实现（通过WebSocket双向通信与MCP服务器交互）
"""

import json
import asyncio
from typing import Dict, Any, Optional
import websockets
from websockets.exceptions import ConnectionClosed
from transport_base import Transport, TransportError, ConnectionError, TimeoutError
from mcp_messages import MCPRequest, MCPResponse


class WebSocketTransport(Transport):
    """WebSocket传输层实现"""
    
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
            
        except Exception as e:
            raise ConnectionError(f"WebSocket连接失败: {e}") from e
    
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
                                error_msg = data["error"].get("message", "Unknown error")
                                future.set_exception(TransportError(f"MCP错误: {error_msg}"))
                            else:
                                future.set_result(MCPResponse.from_dict(data))
                    
                    # 处理通知（无ID）
                    else:
                        await self._handle_notification(data)
                        
                except json.JSONDecodeError as e:
                    # 记录警告，继续处理其他消息
                    print(f"警告: 收到无效JSON消息: {e}")
                except Exception as e:
                    print(f"警告: 消息处理失败: {e}")
                    
        except ConnectionClosed:
            # 连接正常关闭
            self._connected = False
        except Exception as e:
            print(f"接收任务异常: {e}")
            self._connected = False
    
    async def _handle_notification(self, data: Dict[str, Any]) -> None:
        """处理通知消息"""
        method = data.get("method", "")
        params = data.get("params", {})
        
        # 可以在这里添加自定义通知处理逻辑
        # 例如：print(f"收到通知: {method} {params}")
        pass
    
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
            try:
                return await asyncio.wait_for(future, timeout=self.timeout)
            except asyncio.TimeoutError:
                self._pending_requests.pop(request.id, None)
                raise TimeoutError(f"WebSocket响应超时 ({self.timeout}s)")
                
        except Exception as e:
            self._pending_requests.pop(request.id, None)
            raise TransportError(f"WebSocket发送失败: {e}") from e
    
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
            if not future.done():
                future.cancel()
        self._pending_requests.clear()
        
        self._connected = False
```

### 实现要点

1. **双向通信**：
   - WebSocket支持全双工通信
   - 客户端可以发送请求，服务器可以主动推送通知
   - 需要独立的接收任务处理服务器消息

2. **请求-响应匹配**：
   - 使用请求ID匹配请求和响应
   - 维护`_pending_requests`字典，映射请求ID到Future
   - 接收任务根据ID找到对应的Future并设置结果

3. **通知处理**：
   - 通知消息没有ID字段
   - 可以自定义通知处理逻辑
   - 支持扩展各种事件通知

4. **连接管理**：
   - 启动独立的接收任务处理消息
   - 连接断开时清理所有未完成的请求
   - 确保资源正确释放

### 常见问题

**Q1：如何处理并发请求？**
A：WebSocket支持并发请求，多个请求可以同时发送，响应可以按任意顺序返回。使用请求ID匹配机制确保正确性。

**Q2：如何保持连接活跃？**
A：可以定期发送ping消息，或配置WebSocket的keepalive参数。服务器也可能发送ping消息，客户端需要响应pong。

**Q3：如何处理连接断开和重连？**
A：检测连接断开事件，实现自动重连逻辑。重连后需要重新发送未完成的请求。

### 扩展思考

1. **自动重连**：实现连接断开时的自动重连机制
2. **消息压缩**：支持WebSocket消息压缩，减少网络流量
3. **连接复用**：多个客户端共享WebSocket连接，减少连接数

## 📝 任务6：MCP客户端核心类设计

### 参考答案

#### mcp_client.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP客户端核心类
"""

from typing import Dict, Any, List, Optional
from mcp_messages import MCPRequest, MCPResponse, ToolInfo
from transport_base import Transport
from stdio_transport import StdioTransport
from http_transport import HTTPTransport
from websocket_transport import WebSocketTransport


class MCPClient:
    """MCP客户端核心类"""
    
    def __init__(self, server_config: Dict[str, Any]):
        """初始化MCP客户端
        
        参数:
            server_config: 服务器配置字典，包含：
                - transport: 传输类型（stdio/http/websocket）
                - 根据传输类型的不同配置：
                    * stdio: command, args, env, timeout
                    * http: url, headers, timeout
                    * websocket: url, timeout
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
    
    async def _initialize_session(self) -> None:
        """初始化MCP会话"""
        try:
            # 发送初始化请求
            response = await self.transport.call("initialize", {
                "protocolVersion": "2024-11-07",
                "capabilities": {},
                "clientInfo": {
                    "name": "MCP Python Client",
                    "version": "1.0.0"
                }
            })
            
            self._session_initialized = True
            
        except Exception as e:
            # 某些服务器可能不需要初始化，继续执行
            print(f"警告: 会话初始化失败，继续执行: {e}")
    
    async def discover_tools(self) -> List[ToolInfo]:
        """发现MCP服务器提供的工具"""
        try:
            response = await self.transport.call("tools/list", {})
            
            tools_data = response.get("tools", [])
            self.tools.clear()
            
            for tool_data in tools_data:
                tool = ToolInfo(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {})
                )
                self.tools[tool.name] = tool
            
            return list(self.tools.values())
            
        except Exception as e:
            print(f"警告: 工具发现失败: {e}")
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
            result = await self.transport.call("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"工具调用失败: {e}") from e
    
    async def disconnect(self) -> None:
        """断开MCP连接"""
        await self.transport.disconnect()
        self._session_initialized = False
        self.tools.clear()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
```

### 实现要点

1. **传输层工厂**：
   - 根据配置自动创建合适的传输层实例
   - 支持多种传输类型，易于扩展新的传输层
   - 提供统一的配置接口

2. **连接管理**：
   - 自动连接、初始化会话、发现工具
   - 支持重连和工具重新发现
   - 异步上下文管理器简化生命周期管理

3. **工具管理**：
   - 自动发现服务器提供的工具
   - 缓存工具信息，提高调用效率
   - 工具不存在时自动重新发现

4. **错误处理**：
   - 区分连接错误、工具不存在错误、调用错误
   - 提供有意义的错误消息
   - 容错处理（如会话初始化失败）

### 常见问题

**Q1：如何处理服务器不支持initialize方法？**
A：某些MCP服务器可能不需要初始化。客户端应该容错处理，初始化失败时继续执行，不影响后续操作。

**Q2：工具信息发生变化怎么办？**
A：可以在每次调用工具前检查工具是否存在，如果不存在则重新发现。也可以定期刷新工具列表。

**Q3：如何支持多个MCP服务器？**
A：可以创建多个MCPClient实例，每个实例连接到一个服务器。也可以扩展MCPClient支持多服务器路由。

### 扩展思考

1. **连接池**：实现传输层连接池，支持多个并发连接
2. **工具缓存**：缓存工具信息到本地文件，减少发现次数
3. **监控指标**：收集客户端使用指标，如连接次数、工具调用次数、成功率等

## 📝 任务7：配置文件和演示脚本

### 参考答案

#### configs/client_config.yaml
```yaml
# 基础配置
transport: "stdio"
command: "python"
args: 
  - "-c"
  - |
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
                arguments = request["params"]["arguments"]
                
                if tool_name == "get_weather":
                    result = {"temperature": 25, "condition": "sunny", "city": arguments.get("city", "unknown")}
                elif tool_name == "calculate":
                    # 简单计算器
                    expression = arguments.get("expression", "0")
                    try:
                        result_value = eval(expression)
                        result = {"result": result_value}
                    except:
                        result = {"error": "计算失败"}
                else:
                    result = {"error": f"工具不存在: {tool_name}"}
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": result
                }
            
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "error": {"code": -32601, "message": "Method not found"}
                }
            
            print(json.dumps(response))
            sys.stdout.flush()
            
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id", "unknown"),
                "error": {"code": -32603, "message": str(e)}
            }
            print(json.dumps(error_response))
            sys.stdout.flush()
env: {}
timeout: 10.0
```

#### mcp_demo.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP客户端演示脚本
"""

import asyncio
import yaml
from mcp_client import MCPClient


async def demo_stdio_transport():
    """演示StdioTransport"""
    print("\n=== 演示1: StdioTransport基本使用 ===")
    
    # 加载配置
    with open("configs/client_config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # 创建客户端
    client = MCPClient(config)
    
    try:
        # 连接服务器
        await client.connect()
        print("✅ 连接成功")
        
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
        print("👋 连接已断开")


async def demo_http_transport():
    """演示HTTPTransport"""
    print("\n=== 演示2: HTTPTransport配置演示 ===")
    
    # HTTP配置示例
    config = {
        "transport": "http",
        "url": "http://localhost:8080/mcp",
        "headers": {
            "Authorization": "Bearer test-token"
        },
        "timeout": 30.0
    }
    
    print("📝 HTTP配置示例:")
    print(f"  服务器URL: {config['url']}")
    print(f"  超时时间: {config['timeout']}秒")
    
    print("\n⚠️  注意：需要运行真实的HTTP MCP服务器才能测试")


async def demo_websocket_transport():
    """演示WebSocketTransport"""
    print("\n=== 演示3: WebSocketTransport配置演示 ===")
    
    # WebSocket配置示例
    config = {
        "transport": "websocket",
        "url": "ws://localhost:8081/mcp",
        "timeout": 30.0
    }
    
    print("📝 WebSocket配置示例:")
    print(f"  服务器URL: {config['url']}")
    print(f"  超时时间: {config['timeout']}秒")
    
    print("\n⚠️  注意：需要运行真实的WebSocket MCP服务器才能测试")


async def demo_client_lifecycle():
    """演示客户端完整生命周期"""
    print("\n=== 演示4: MCP客户端完整生命周期 ===")
    
    # 使用上下文管理器
    config = {
        "transport": "stdio",
        "command": "python",
        "args": ["-c", """
import sys
import json
while True:
    line = sys.stdin.readline()
    if not line:
        break
    request = json.loads(line)
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
    
    print("使用异步上下文管理器自动管理连接:")
    
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


async def main():
    """主演示函数"""
    print("=" * 60)
    print("MCP客户端架构演示程序")
    print("=" * 60)
    
    # 运行所有演示
    await demo_stdio_transport()
    await demo_http_transport()
    await demo_websocket_transport()
    await demo_client_lifecycle()
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

#### test_mcp_system.py
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP系统测试脚本
"""

import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_messages import MCPRequest, MCPResponse, MCPNotification, ToolInfo
from transport_base import Transport


class TestMCPMessages(unittest.TestCase):
    """MCP消息类测试"""
    
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
    
    def test_mcp_notification_creation(self):
        """测试MCP通知创建"""
        notification = MCPNotification(method="notify", params={"data": "test"})
        
        self.assertEqual(notification.method, "notify")
        self.assertEqual(notification.params, {"data": "test"})
        self.assertEqual(notification.type.value, "notification")
    
    def test_tool_info_creation(self):
        """测试工具信息创建"""
        tool = ToolInfo(
            name="test_tool",
            description="测试工具",
            input_schema={"type": "object"}
        )
        
        self.assertEqual(tool.name, "test_tool")
        self.assertEqual(tool.description, "测试工具")
        self.assertEqual(tool.input_schema, {"type": "object"})


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


class TestTransportBase(AsyncTestCase):
    """传输层基类测试"""
    
    def test_abstract_methods(self):
        """测试抽象方法"""
        # 创建抽象基类实例应该失败
        with self.assertRaises(TypeError):
            Transport()
    
    @patch.multiple(Transport, __abstractmethods__=set())
    def test_concrete_methods(self):
        """测试具体方法"""
        # 创建模拟传输层
        mock_transport = Transport()
        
        # 测试属性
        self.assertFalse(mock_transport.connected)
        
        # 测试上下文管理器
        async def test_context():
            async with mock_transport:
                pass
        
        self.run_async(test_context())


if __name__ == "__main__":
    unittest.main()
```

### 实现要点

1. **配置文件**：
   - 使用YAML格式，易于阅读和修改
   - 提供完整的配置示例，包含注释
   - 支持环境变量替换（可选）

2. **演示脚本**：
   - 覆盖所有主要功能点
   - 提供清晰的输出和说明
   - 包含错误处理和资源清理

3. **测试脚本**：
   - 单元测试覆盖核心功能
   - 使用unittest.mock模拟依赖
   - 支持异步测试

### 常见问题

**Q1：配置文件应该放在哪里？**
A：配置文件应该放在单独的configs目录中，与代码分离。可以使用环境变量指定配置文件路径，支持不同环境（开发、测试、生产）的不同配置。

**Q2：如何测试异步代码？**
A：使用unittest的异步测试支持，或使用pytest-asyncio插件。创建异步测试基类，管理事件循环。

**Q3：演示脚本应该包含哪些内容？**
A：演示脚本应该展示主要使用场景，包括正常流程和错误处理。提供清晰的输出，便于理解。

### 扩展思考

1. **配置验证**：实现配置验证工具，检查配置文件的完整性和正确性
2. **性能测试**：添加性能测试脚本，测量请求延迟、吞吐量等指标
3. **集成测试**：创建端到端集成测试，验证完整工作流程

## 🏆 练习评估

### 完成度检查

| 任务 | 完成要求 | 检查点 |
|------|----------|--------|
| 任务1 | MCP协议消息类 | ✅ 请求、响应、通知类完整实现<br>✅ 序列化/反序列化正确<br>✅ 类型提示和验证完整 |
| 任务2 | 传输层抽象基类 | ✅ 抽象基类定义完整<br>✅ 异常层次合理<br>✅ 异步上下文管理器正确 |
| 任务3 | Stdio传输层 | ✅ 子进程管理正确<br>✅ 请求-响应协议实现<br>✅ 超时和错误处理完整 |
| 任务4 | HTTP传输层 | ✅ HTTP会话管理正确<br>✅ 请求发送和响应处理<br>✅ 错误处理完善 |
| 任务5 | WebSocket传输层 | ✅ 双向通信实现<br>✅ 请求ID匹配机制<br>✅ 通知处理支持 |
| 任务6 | MCP客户端核心 | ✅ 传输层工厂实现<br>✅ 连接和工具管理<br>✅ 异步上下文管理器 |
| 任务7 | 配置和演示 | ✅ 配置文件完整<br>✅ 演示脚本覆盖全面<br>✅ 测试脚本可用 |

### 代码质量评估

1. **代码规范**：代码符合PEP 8规范，命名清晰，注释完整
2. **类型安全**：使用类型提示，参数验证充分
3. **错误处理**：异常处理全面，提供有意义的错误消息
4. **资源管理**：正确管理连接、会话、子进程等资源
5. **测试覆盖**：单元测试覆盖核心功能，演示脚本可运行

### 扩展能力评估

1. **可扩展性**：设计支持扩展新的传输层和协议功能
2. **可配置性**：支持灵活的配置，适应不同使用场景
3. **可维护性**：代码结构清晰，模块化程度高，易于维护
4. **性能表现**：异步设计支持高并发，资源使用高效

## 📚 进一步学习

### 深入学习方向

1. **MCP协议高级特性**：
   - 学习MCP协议的扩展功能和高级特性
   - 了解协议版本管理和兼容性处理
   - 研究安全性和权限控制机制

2. **异步编程深入**：
   - 深入学习asyncio高级特性
   - 掌握异步编程模式和最佳实践
   - 学习异步性能优化技术

3. **网络协议深入**：
   - 深入研究HTTP/2、HTTP/3协议
   - 学习WebSocket协议细节和优化
   - 了解其他RPC协议（gRPC、Thrift等）

4. **系统架构设计**：
   - 学习分布式系统设计原则
   - 掌握高可用和可扩展架构设计
   - 研究微服务架构和通信模式

### 实际项目应用

1. **工具集成平台**：基于MCP构建统一的AI工具集成平台
2. **智能助手系统**：扩展智能助手的外部能力集成
3. **开发工具链**：为开发者提供标准化的工具接口
4. **企业服务集成**：集成企业内部服务和外部API

### 开源贡献

1. **MCP生态贡献**：参与MCP官方项目，贡献代码和文档
2. **DeerFlow集成**：改进DeerFlow的MCP插件和集成
3. **工具开发**：开发新的MCP工具和服务器实现
4. **社区建设**：参与社区讨论，分享经验和最佳实践

---

**恭喜你完成MCP客户端架构的学习和练习！**

通过本练习，你已经掌握了MCP客户端架构的核心概念和实践技能。这些知识和技能将帮助你在实际项目中设计和实现可靠的MCP客户端，为AI系统提供强大的外部工具集成能力。

*"标准化的协议是系统集成的基石，清晰的架构是可靠实现的关键。"* - 技术实践原则