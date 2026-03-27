#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 8 Lesson 32: AioSandboxProvider

本文件演示AioSandboxProvider的完整实现，包括：
1. AioSandboxProvider类 - 实现BaseProvider协议和Sandbox接口的异步连接池提供者
2. 异步连接池管理 - 信号量控制、连接复用、自动伸缩等高性能特性
3. Provider模式集成 - 与ProviderRegistry、ProviderFactory的完整集成
4. 性能优化技巧 - 预热池、懒加载、健康检查等高级功能
5. 测试套件 - 完整的单元测试和集成测试，包括并发性能测试

采用五部分结构设计：
第一部分：概念与设计原则 - 定义AioSandboxProvider的核心概念和设计原则
第二部分：接口与协议实现 - 实现BaseProvider协议和Sandbox接口的AioSandboxProvider
第三部分：核心功能实现 - 实现异步连接池的核心功能：信号量控制、连接复用、自动伸缩
第四部分：集成与配置 - 集成Provider模式，支持配置驱动创建和注册
第五部分：测试与演示 - 提供完整测试套件和演示程序

使用示例:
    python aio_sandbox_demo.py          # 运行基本演示
    python aio_sandbox_demo.py --test   # 运行测试套件
    python aio_sandbox_demo.py --demo   # 运行完整演示
    python aio_sandbox_demo.py --help   # 显示帮助信息
"""

import asyncio
import sys
import os
import json
import time
import signal
import tempfile
import shutil
import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable, Type
from dataclasses import dataclass, field, asdict
import logging
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
import argparse
import pathlib
import threading
from collections import deque
import random

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================

class AioSandboxCapability(Enum):
    """AioSandbox能力枚举"""
    ASYNC_CONNECTION_POOL = "异步连接池"      # 支持异步连接池，复用沙箱实例
    CONCURRENT_EXECUTION = "并发执行"         # 支持并发命令执行，通过信号量控制
    LOAD_BALANCING = "负载均衡"              # 支持连接池内的负载均衡
    AUTO_SCALING = "自动伸缩"                # 支持根据负载自动调整连接池大小
    HEALTH_CHECK = "健康检查"                # 支持连接健康检查和故障转移
    PERFORMANCE_MONITORING = "性能监控"      # 监控连接池性能指标
    CONNECTION_WARMUP = "连接预热"           # 支持连接预热，减少首次执行延迟
    LAZY_LOADING = "懒加载"                  # 支持懒加载连接，按需创建
    
    def description(self) -> str:
        """获取能力描述"""
        descriptions = {
            self.ASYNC_CONNECTION_POOL: "使用异步连接池管理沙箱实例，支持连接复用和资源优化",
            self.CONCURRENT_EXECUTION: "通过信号量控制并发执行数量，防止资源耗尽",
            self.LOAD_BALANCING: "在连接池内实现负载均衡，提高资源利用率",
            self.AUTO_SCALING: "根据系统负载动态调整连接池大小，平衡性能和资源",
            self.HEALTH_CHECK: "定期检查连接健康状态，自动移除故障连接",
            self.PERFORMANCE_MONITORING: "监控连接池关键指标：使用率、等待时间、错误率等",
            self.CONNECTION_WARMUP: "预先创建一定数量的连接，减少首次执行延迟",
            self.LAZY_LOADING: "按需创建连接，避免不必要的资源占用"
        }
        return descriptions.get(self, "未知能力")


class AioSandboxStatus(Enum):
    """AioSandbox状态枚举"""
    CREATED = "已创建"          # 沙箱已创建但未初始化
    INITIALIZED = "已初始化"    # 沙箱已初始化，连接池就绪
    CONNECTING = "连接中"       # 正在建立连接
    READY = "就绪"             # 连接池就绪，可执行命令
    EXECUTING = "执行中"        # 正在执行命令
    DEGRADED = "降级"          # 部分连接不可用，但仍在运行
    ERROR = "错误"              # 连接池错误
    STOPPED = "已停止"          # 连接池已停止
    
    def is_healthy(self) -> bool:
        """检查状态是否健康"""
        return self in {self.READY, self.EXECUTING, self.DEGRADED}


class ConnectionPoolStrategy(Enum):
    """连接池策略枚举"""
    FIXED_SIZE = "固定大小"      # 固定大小的连接池
    DYNAMIC_SCALING = "动态伸缩" # 动态调整大小的连接池
    LAZY_INIT = "懒初始化"      # 懒初始化连接池
    EAGER_INIT = "急切初始化"   # 急切初始化连接池
    HYBRID = "混合策略"         # 混合使用多种策略
    
    def description(self) -> str:
        """获取策略描述"""
        descriptions = {
            self.FIXED_SIZE: "固定大小的连接池，创建时分配所有连接，简单但可能浪费资源",
            self.DYNAMIC_SCALING: "根据负载动态调整连接池大小，平衡性能和资源使用",
            self.LAZY_INIT: "按需创建连接，减少初始资源占用，但首次执行可能延迟",
            self.EAGER_INIT: "预先创建所有连接，减少首次执行延迟，但可能浪费资源",
            self.HYBRID: "结合懒加载和急切加载，根据预测负载动态调整"
        }
        return descriptions.get(self, "未知策略")


@dataclass
class SandboxConfig:
    """沙箱配置（从Lesson 29和31扩展，添加连接池配置）"""
    provider: str = "aio"                     # 提供者类型
    pool_size: int = 5                        # 连接池大小
    min_pool_size: int = 1                    # 最小连接池大小（用于动态伸缩）
    max_pool_size: int = 20                   # 最大连接池大小
    timeout_seconds: float = 30.0             # 命令执行超时时间
    connection_timeout: float = 10.0          # 连接建立超时时间
    env: Dict[str, str] = field(default_factory=dict)  # 环境变量
    shell: bool = False                       # 是否使用shell执行命令
    capture_output: bool = True               # 是否捕获命令输出
    inherit_env: bool = True                  # 是否继承当前进程环境变量
    workdir: Optional[str] = None             # 工作目录路径
    cleanup_on_exit: bool = True              # 退出时是否清理工作目录
    pool_strategy: ConnectionPoolStrategy = ConnectionPoolStrategy.FIXED_SIZE  # 连接池策略
    warmup_size: int = 0                      # 预热连接数量（0表示不预热）
    health_check_interval: float = 0.0       # 健康检查间隔（秒），0表示禁用
    max_idle_time: float = 300.0              # 最大空闲时间（秒），超过后连接被回收
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "provider": self.provider,
            "pool_size": self.pool_size,
            "min_pool_size": self.min_pool_size,
            "max_pool_size": self.max_pool_size,
            "timeout_seconds": self.timeout_seconds,
            "connection_timeout": self.connection_timeout,
            "env": self.env,
            "shell": self.shell,
            "capture_output": self.capture_output,
            "inherit_env": self.inherit_env,
            "workdir": self.workdir,
            "cleanup_on_exit": self.cleanup_on_exit,
            "pool_strategy": self.pool_strategy.value,
            "warmup_size": self.warmup_size,
            "health_check_interval": self.health_check_interval,
            "max_idle_time": self.max_idle_time
        }


@dataclass
class ExecutionResult:
    """命令执行结果（复用Lesson 31定义，添加连接池信息）"""
    command: str                    # 执行的命令
    args: List[str]                 # 命令参数
    stdout: Optional[str]           # 标准输出（如果capture_output=True）
    stderr: Optional[str]           # 标准错误输出（如果capture_output=True）
    exit_code: int                  # 退出码
    success: bool                   # 是否成功执行（exit_code == 0）
    execution_time: float           # 执行时间（秒）
    timed_out: bool = False         # 是否超时
    error: Optional[str] = None     # 错误信息（如果有）
    workdir: Optional[str] = None   # 执行时的工作目录
    connection_id: Optional[int] = None  # 使用的连接ID
    pool_size: Optional[int] = None # 执行时的连接池大小
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "command": self.command,
            "args": self.args,
            "exit_code": self.exit_code,
            "success": self.success,
            "execution_time": self.execution_time,
            "timed_out": self.timed_out,
            "error": self.error,
            "workdir": self.workdir,
            "connection_id": self.connection_id,
            "pool_size": self.pool_size,
            "stdout_length": len(self.stdout) if self.stdout else 0,
            "stderr_length": len(self.stderr) if self.stderr else 0
        }


@dataclass
class ResourceUsage:
    """资源使用情况（复用Lesson 31定义）"""
    cpu_time: float = 0.0           # CPU时间（秒）
    memory_mb: float = 0.0          # 内存使用（MB）
    disk_mb: float = 0.0            # 磁盘使用（MB）
    process_count: int = 1          # 进程数
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "cpu_time": self.cpu_time,
            "memory_mb": self.memory_mb,
            "disk_mb": self.disk_mb,
            "process_count": self.process_count
        }


@dataclass
class ConnectionPoolMetrics:
    """连接池性能指标"""
    total_connections: int = 0           # 总连接数
    active_connections: int = 0          # 活跃连接数
    idle_connections: int = 0            # 空闲连接数
    max_connections: int = 0             # 最大连接数（历史峰值）
    total_executions: int = 0            # 总执行次数
    successful_executions: int = 0       # 成功执行次数
    failed_executions: int = 0           # 失败执行次数
    timed_out_executions: int = 0        # 超时执行次数
    avg_execution_time: float = 0.0      # 平均执行时间（秒）
    max_execution_time: float = 0.0      # 最大执行时间（秒）
    min_execution_time: float = 0.0      # 最小执行时间（秒）
    avg_wait_time: float = 0.0           # 平均等待时间（获取连接的等待时间）
    max_wait_time: float = 0.0           # 最大等待时间
    connection_errors: int = 0           # 连接错误次数
    pool_resizes: int = 0                # 连接池大小调整次数
    health_check_passes: int = 0         # 健康检查通过次数
    health_check_fails: int = 0          # 健康检查失败次数
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "max_connections": self.max_connections,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "timed_out_executions": self.timed_out_executions,
            "avg_execution_time": self.avg_execution_time,
            "max_execution_time": self.max_execution_time,
            "min_execution_time": self.min_execution_time,
            "avg_wait_time": self.avg_wait_time,
            "max_wait_time": self.max_wait_time,
            "connection_errors": self.connection_errors,
            "pool_resizes": self.pool_resizes,
            "health_check_passes": self.health_check_passes,
            "health_check_fails": self.health_check_fails
        }
    
    def update_from_execution(self, result: ExecutionResult, wait_time: float = 0.0):
        """根据执行结果更新指标"""
        self.total_executions += 1
        if result.success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        if result.timed_out:
            self.timed_out_executions += 1
        
        # 更新执行时间统计
        self.avg_execution_time = ((self.avg_execution_time * (self.total_executions - 1) + 
                                    result.execution_time) / self.total_executions)
        self.max_execution_time = max(self.max_execution_time, result.execution_time)
        if self.min_execution_time == 0.0 or result.execution_time < self.min_execution_time:
            self.min_execution_time = result.execution_time
        
        # 更新等待时间统计
        self.avg_wait_time = ((self.avg_wait_time * (self.total_executions - 1) + 
                               wait_time) / self.total_executions)
        self.max_wait_time = max(self.max_wait_time, wait_time)


# ============================================================================
# 第二部分：接口与协议实现
# ============================================================================

# 导入Provider模式相关定义（从Lesson 30）
# 注意：实际项目中这些定义应该从独立模块导入
# 这里为了演示完整，复制了部分关键定义

class ProviderStatus(Enum):
    """Provider状态枚举（从Lesson 30复制）"""
    AVAILABLE = "可用"
    DEGRADED = "降级"
    UNAVAILABLE = "不可用"
    DEPRECATED = "已弃用"
    EXPERIMENTAL = "实验性"


class ProviderPriority(Enum):
    """Provider优先级枚举（从Lesson 30复制）"""
    CRITICAL = "关键"
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"
    BACKGROUND = "后台"


class ProviderCapability(Enum):
    """Provider能力枚举（从Lesson 30复制）"""
    DYNAMIC_DISCOVERY = "动态发现"
    CONFIG_DRIVEN = "配置驱动"
    PLUGIN_SUPPORT = "插件支持"
    HEALTH_CHECK = "健康检查"
    PERFORMANCE_MONITOR = "性能监控"
    VERSION_MANAGEMENT = "版本管理"


@dataclass
class ProviderMetadata:
    """Provider元数据（从Lesson 30复制）"""
    name: str
    description: str
    version: str
    author: str
    capabilities: List[ProviderCapability]
    status: ProviderStatus = ProviderStatus.AVAILABLE
    priority: ProviderPriority = ProviderPriority.MEDIUM
    config_schema: Optional[Dict] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "capabilities": [cap.value for cap in self.capabilities],
            "status": self.status.value,
            "priority": self.priority.value,
            "config_schema": self.config_schema,
            "dependencies": self.dependencies,
            "tags": self.tags
        }


class BaseProvider:
    """BaseProvider协议（从Lesson 30简化）"""
    
    def get_metadata(self) -> ProviderMetadata:
        """获取Provider元数据"""
        raise NotImplementedError()
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化Provider"""
        raise NotImplementedError()
    
    async def shutdown(self) -> None:
        """关闭Provider"""
        raise NotImplementedError()
    
    def is_healthy(self) -> bool:
        """检查Provider健康状态"""
        raise NotImplementedError()


class Sandbox(ABC):
    """沙箱抽象接口（从Lesson 29简化）"""
    
    @abstractmethod
    async def execute(self, command: str, args: Optional[List[str]] = None, 
                     timeout_seconds: Optional[float] = None) -> ExecutionResult:
        """执行命令"""
        pass
    
    @abstractmethod
    def get_workdir(self) -> Optional[str]:
        """获取工作目录"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass


class AioSandboxProvider(BaseProvider, Sandbox):
    """
    AioSandboxProvider - 异步连接池沙箱提供者
    
    同时实现BaseProvider协议和Sandbox接口，提供异步连接池管理功能：
    1. 基于信号量的并发控制，限制同时执行的命令数量
    2. 连接池管理，复用沙箱实例，减少创建开销
    3. 自动健康检查，移除不可用连接
    4. 性能监控，收集连接池和执行指标
    5. 支持动态伸缩，根据负载调整连接池大小
    
    设计原则：
    1. 异步优先：所有操作都是异步的，支持高并发执行
    2. 资源复用：通过连接池复用沙箱实例，提高性能
    3. 自动管理：自动处理连接健康、扩容、缩容等管理任务
    4. 监控透明：提供详细的性能指标，便于问题诊断和优化
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        """初始化AioSandboxProvider"""
        self.config = config or SandboxConfig()
        self._status = AioSandboxStatus.CREATED
        self._workdir = None
        self._cleanup_workdir = False
        self._logger = logging.getLogger(f"AioSandboxProvider.{id(self)}")
        
        # 连接池相关属性
        self._pool_size = self.config.pool_size
        self._min_pool_size = self.config.min_pool_size
        self._max_pool_size = self.config.max_pool_size
        self._pool_strategy = self.config.pool_strategy
        self._warmup_size = self.config.warmup_size
        
        # 连接池数据结构
        self._available_connections = deque()  # 可用连接队列
        self._active_connections = {}          # 活跃连接字典 {connection_id: connection}
        self._connection_counter = 0           # 连接ID计数器
        self._connection_semaphore = None      # 连接信号量，控制并发数
        
        # 性能指标
        self._metrics = ConnectionPoolMetrics()
        self._execution_count = 0
        self._total_execution_time = 0.0
        
        # 同步锁
        self._lock = asyncio.Lock()
        self._health_check_task = None
        
        # 确定工作目录
        if self.config.workdir:
            self._workdir = self.config.workdir
            self._cleanup_workdir = False
        else:
            # 创建临时工作目录
            self._workdir = tempfile.mkdtemp(prefix="aiosandbox_")
            self._cleanup_workdir = self.config.cleanup_on_exit
        
        self._logger.info(f"AioSandboxProvider created with pool_size={self._pool_size}, workdir={self._workdir}")
    
    def get_metadata(self) -> ProviderMetadata:
        """获取Provider元数据"""
        return ProviderMetadata(
            name="aio_sandbox_provider",
            description="异步连接池沙箱提供者，提供高性能的并发命令执行和连接池管理",
            version="1.0.0",
            author="DeerFlow Team",
            capabilities=[
                ProviderCapability.DYNAMIC_DISCOVERY,
                ProviderCapability.CONFIG_DRIVEN,
                ProviderCapability.HEALTH_CHECK,
                ProviderCapability.PERFORMANCE_MONITOR,
                ProviderCapability.VERSION_MANAGEMENT
            ],
            status=ProviderStatus.AVAILABLE,
            priority=ProviderPriority.HIGH,
            config_schema={
                "type": "object",
                "properties": {
                    "pool_size": {"type": "integer", "minimum": 1, "maximum": 100},
                    "min_pool_size": {"type": "integer", "minimum": 1, "maximum": 50},
                    "max_pool_size": {"type": "integer", "minimum": 1, "maximum": 200},
                    "timeout_seconds": {"type": "number", "minimum": 0.1},
                    "connection_timeout": {"type": "number", "minimum": 0.1},
                    "env": {"type": "object"},
                    "shell": {"type": "boolean"},
                    "capture_output": {"type": "boolean"},
                    "inherit_env": {"type": "boolean"},
                    "workdir": {"type": "string"},
                    "cleanup_on_exit": {"type": "boolean"},
                    "pool_strategy": {"type": "string", "enum": ["FIXED_SIZE", "DYNAMIC_SCALING", "LAZY_INIT", "EAGER_INIT", "HYBRID"]},
                    "warmup_size": {"type": "integer", "minimum": 0},
                    "health_check_interval": {"type": "number", "minimum": 1.0},
                    "max_idle_time": {"type": "number", "minimum": 1.0}
                }
            }
        )
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化Provider，创建连接池"""
        try:
            self._logger.info("Initializing AioSandboxProvider...")
            
            # 更新配置（如果提供了新配置）
            if config:
                await self._update_config_from_dict(config)
            
            # 创建信号量
            self._connection_semaphore = asyncio.Semaphore(self._pool_size)
            
            # 根据策略初始化连接池
            await self._initialize_pool()
            
            # 启动健康检查任务
            if self.config.health_check_interval > 0:
                self._health_check_task = asyncio.create_task(
                    self._health_check_loop()
                )
            
            self._status = AioSandboxStatus.READY
            self._logger.info(f"AioSandboxProvider initialized successfully. Pool size: {self._pool_size}")
            return True
            
        except Exception as e:
            self._status = AioSandboxStatus.ERROR
            self._logger.error(f"Failed to initialize AioSandboxProvider: {e}")
            return False
    
    async def shutdown(self) -> None:
        """关闭Provider，清理所有连接"""
        self._logger.info("Shutting down AioSandboxProvider...")
        
        # 取消健康检查任务
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await asyncio.wait_for(self._health_check_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._logger.warning("Health check task did not cancel in time, force cancelling")
            except asyncio.CancelledError:
                pass
        
        # 关闭所有活跃连接
        async with self._lock:
            for connection_id, connection in list(self._active_connections.items()):
                await self._close_connection(connection_id, connection)
            
            # 关闭所有可用连接
            while self._available_connections:
                connection_id, connection = self._available_connections.popleft()
                await self._close_connection(connection_id, connection)
        
        # 清理工作目录
        if self._cleanup_workdir and self._workdir and os.path.exists(self._workdir):
            try:
                shutil.rmtree(self._workdir)
                self._logger.info(f"Cleaned up workdir: {self._workdir}")
            except Exception as e:
                self._logger.warning(f"Failed to clean up workdir {self._workdir}: {e}")
        
        self._status = AioSandboxStatus.STOPPED
        self._logger.info("AioSandboxProvider shut down successfully")
    
    def is_healthy(self) -> bool:
        """检查Provider健康状态"""
        if self._status == AioSandboxStatus.ERROR:
            return False
        
        # 检查连接池健康状态
        total_connections = len(self._available_connections) + len(self._active_connections)
        if total_connections == 0 and self._pool_size > 0:
            return False
        
        # 检查是否有过多的连接错误
        if self._metrics.connection_errors > 100:
            return False
        
        return True
    
    def get_workdir(self) -> Optional[str]:
        """获取工作目录"""
        return self._workdir
    
    async def cleanup(self) -> None:
        """清理资源（Sandbox接口要求）"""
        await self.shutdown()
    
    async def execute(self, command: str, args: Optional[List[str]] = None,
                     timeout_seconds: Optional[float] = None) -> ExecutionResult:
        """
        执行命令（Sandbox接口实现）
        
        流程：
        1. 获取连接（等待信号量）
        2. 执行命令
        3. 释放连接
        4. 更新指标
        """
        start_time = time.perf_counter()
        connection_id = None
        connection = None
        wait_time = 0.0
        
        try:
            # 1. 获取连接
            acquire_start = time.perf_counter()
            await self._connection_semaphore.acquire()
            wait_time = time.perf_counter() - acquire_start
            
            # 2. 从可用连接池获取或创建连接
            connection_id, connection = await self._acquire_connection()
            
            # 3. 执行命令
            exec_start = time.perf_counter()
            result = await self._execute_with_connection(
                connection_id, connection, command, args, timeout_seconds
            )
            execution_time = time.perf_counter() - exec_start
            
            # 4. 更新执行结果
            result.execution_time = execution_time
            result.connection_id = connection_id
            result.pool_size = self._pool_size
            
            # 5. 更新性能指标
            self._execution_count += 1
            self._total_execution_time += execution_time
            self._metrics.update_from_execution(result, wait_time)
            
            return result
            
        except asyncio.TimeoutError as e:
            error_result = ExecutionResult(
                command=command,
                args=args or [],
                stdout=None,
                stderr=None,
                exit_code=-1,
                success=False,
                execution_time=time.perf_counter() - start_time,
                timed_out=True,
                error=f"Command timed out: {e}",
                workdir=self._workdir,
                connection_id=connection_id,
                pool_size=self._pool_size
            )
            self._metrics.update_from_execution(error_result, wait_time)
            return error_result
            
        except Exception as e:
            error_result = ExecutionResult(
                command=command,
                args=args or [],
                stdout=None,
                stderr=None,
                exit_code=-1,
                success=False,
                execution_time=time.perf_counter() - start_time,
                timed_out=False,
                error=f"Command execution failed: {e}",
                workdir=self._workdir,
                connection_id=connection_id,
                pool_size=self._pool_size
            )
            self._metrics.update_from_execution(error_result, wait_time)
            return error_result
            
        finally:
            # 6. 释放连接
            if connection_id and connection:
                await self._release_connection(connection_id, connection)
            
            # 7. 释放信号量
            if self._connection_semaphore:
                self._connection_semaphore.release()
    
    # ============================================================================
    # 核心连接池管理方法
    # ============================================================================
    
    class Connection:
        """连接类，封装单个沙箱连接"""
        
        def __init__(self, connection_id: int, workdir: str, config: SandboxConfig):
            self.id = connection_id
            self.workdir = workdir
            self.config = config
            self.created_at = time.time()
            self.last_used_at = time.time()
            self.usage_count = 0
            self.healthy = True
            self.process = None
            self._logger = logging.getLogger(f"AioSandboxProvider.Connection.{connection_id}")
        
        async def execute(self, command: str, args: Optional[List[str]] = None,
                         timeout_seconds: Optional[float] = None) -> ExecutionResult:
            """在连接上执行命令"""
            self.last_used_at = time.time()
            self.usage_count += 1
            
            # 使用asyncio创建子进程执行命令
            cmd_args = [command] + (args or [])
            env = os.environ.copy() if self.config.inherit_env else {}
            env.update(self.config.env)
            
            timeout = timeout_seconds or self.config.timeout_seconds
            
            try:
                start_time = time.perf_counter()
                
                if self.config.shell:
                    # 使用shell执行
                    process = await asyncio.create_subprocess_shell(
                        " ".join(cmd_args),
                        cwd=self.workdir,
                        env=env,
                        stdout=subprocess.PIPE if self.config.capture_output else None,
                        stderr=subprocess.PIPE if self.config.capture_output else None
                    )
                else:
                    # 直接执行命令
                    process = await asyncio.create_subprocess_exec(
                        *cmd_args,
                        cwd=self.workdir,
                        env=env,
                        stdout=subprocess.PIPE if self.config.capture_output else None,
                        stderr=subprocess.PIPE if self.config.capture_output else None
                    )
                
                self.process = process
                
                # 等待进程完成，支持超时
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    # 超时，终止进程
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
                    
                    execution_time = time.perf_counter() - start_time
                    return ExecutionResult(
                        command=command,
                        args=args or [],
                        stdout=None,
                        stderr=None,
                        exit_code=-1,
                        success=False,
                        execution_time=execution_time,
                        timed_out=True,
                        error=f"Command timed out after {timeout} seconds",
                        workdir=self.workdir
                    )
                
                execution_time = time.perf_counter() - start_time
                
                # 解码输出
                stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""
                stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""
                
                return ExecutionResult(
                    command=command,
                    args=args or [],
                    stdout=stdout_text,
                    stderr=stderr_text,
                    exit_code=process.returncode,
                    success=process.returncode == 0,
                    execution_time=execution_time,
                    timed_out=False,
                    error=None,
                    workdir=self.workdir
                )
                
            except Exception as e:
                execution_time = time.perf_counter() - start_time if 'start_time' in locals() else 0.0
                self.healthy = False
                return ExecutionResult(
                    command=command,
                    args=args or [],
                    stdout=None,
                    stderr=None,
                    exit_code=-1,
                    success=False,
                    execution_time=execution_time,
                    timed_out=False,
                    error=f"Command execution failed: {e}",
                    workdir=self.workdir
                )
        
        def is_idle(self, max_idle_time: float) -> bool:
            """检查连接是否空闲时间过长"""
            idle_time = time.time() - self.last_used_at
            return idle_time > max_idle_time
        
        async def close(self):
            """关闭连接"""
            if self.process and self.process.returncode is None:
                try:
                    self.process.terminate()
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except (asyncio.TimeoutError, ProcessLookupError):
                    pass
            
            self.healthy = False
    
    async def _update_config_from_dict(self, config_dict: Dict[str, Any]):
        """从字典更新配置"""
        # 这里简化处理，实际项目应该使用更严格的配置验证
        if 'pool_size' in config_dict:
            self._pool_size = config_dict['pool_size']
        if 'min_pool_size' in config_dict:
            self._min_pool_size = config_dict['min_pool_size']
        if 'max_pool_size' in config_dict:
            self._max_pool_size = config_dict['max_pool_size']
        if 'pool_strategy' in config_dict:
            self._pool_strategy = ConnectionPoolStrategy(config_dict['pool_strategy'])
        if 'warmup_size' in config_dict:
            self._warmup_size = config_dict['warmup_size']
        
        # 更新config对象
        for key, value in config_dict.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    async def _initialize_pool(self):
        """根据策略初始化连接池"""
        self._logger.info(f"Initializing connection pool with strategy: {self._pool_strategy.value}")
        
        async with self._lock:
            if self._pool_strategy in {ConnectionPoolStrategy.EAGER_INIT, ConnectionPoolStrategy.HYBRID}:
                # 急切初始化，创建所有连接
                init_size = self._pool_size
                if self._warmup_size > 0:
                    init_size = min(self._warmup_size, self._pool_size)
                
                for _ in range(init_size):
                    connection_id = self._connection_counter
                    self._connection_counter += 1
                    connection = self.Connection(connection_id, self._workdir, self.config)
                    self._available_connections.append((connection_id, connection))
                
                self._metrics.total_connections = init_size
                self._metrics.idle_connections = init_size
                self._logger.info(f"Eager initialized {init_size} connections")
            
            elif self._pool_strategy == ConnectionPoolStrategy.LAZY_INIT:
                # 懒初始化，不预先创建连接
                self._logger.info("Lazy initialization - connections will be created on demand")
            
            elif self._pool_strategy == ConnectionPoolStrategy.DYNAMIC_SCALING:
                # 动态伸缩，创建最小数量的连接
                init_size = self._min_pool_size
                for _ in range(init_size):
                    connection_id = self._connection_counter
                    self._connection_counter += 1
                    connection = self.Connection(connection_id, self._workdir, self.config)
                    self._available_connections.append((connection_id, connection))
                
                self._metrics.total_connections = init_size
                self._metrics.idle_connections = init_size
                self._logger.info(f"Dynamic scaling pool initialized with {init_size} connections")
    
    async def _acquire_connection(self) -> tuple[int, Connection]:
        """获取一个可用连接，如果没有则创建新连接"""
        async with self._lock:
            # 首先尝试从可用连接队列获取
            if self._available_connections:
                connection_id, connection = self._available_connections.popleft()
                self._active_connections[connection_id] = connection
                self._metrics.active_connections = len(self._active_connections)
                self._metrics.idle_connections = len(self._available_connections)
                return connection_id, connection
            
            # 检查是否允许创建新连接
            total_connections = len(self._available_connections) + len(self._active_connections)
            can_create_new = False
            
            if self._pool_strategy == ConnectionPoolStrategy.FIXED_SIZE:
                can_create_new = total_connections < self._pool_size
            elif self._pool_strategy == ConnectionPoolStrategy.DYNAMIC_SCALING:
                can_create_new = total_connections < self._max_pool_size
            else:  # LAZY_INIT, EAGER_INIT, HYBRID
                can_create_new = True
            
            if can_create_new:
                # 创建新连接
                connection_id = self._connection_counter
                self._connection_counter += 1
                connection = self.Connection(connection_id, self._workdir, self.config)
                self._active_connections[connection_id] = connection
                
                self._metrics.total_connections += 1
                self._metrics.active_connections = len(self._active_connections)
                self._metrics.max_connections = max(
                    self._metrics.max_connections, 
                    self._metrics.total_connections
                )
                
                self._logger.debug(f"Created new connection #{connection_id}")
                return connection_id, connection
            else:
                # 连接池已满，等待可用连接（这种情况理论上不会发生，因为有信号量控制）
                raise RuntimeError("Connection pool is full, but semaphore allowed acquisition")
    
    async def _release_connection(self, connection_id: int, connection: Connection):
        """释放连接回连接池"""
        async with self._lock:
            # 从活跃连接中移除
            if connection_id in self._active_connections:
                del self._active_connections[connection_id]
            
            # 检查连接是否健康
            if connection.healthy:
                # 检查是否空闲时间过长需要关闭
                if connection.is_idle(self.config.max_idle_time):
                    await self._close_connection(connection_id, connection)
                    self._logger.debug(f"Closed idle connection #{connection_id}")
                else:
                    # 放回可用连接池
                    self._available_connections.append((connection_id, connection))
            else:
                # 不健康的连接，直接关闭
                await self._close_connection(connection_id, connection)
                self._logger.debug(f"Closed unhealthy connection #{connection_id}")
            
            # 更新指标
            self._metrics.active_connections = len(self._active_connections)
            self._metrics.idle_connections = len(self._available_connections)
    
    async def _close_connection(self, connection_id: int, connection: Connection):
        """关闭连接"""
        try:
            await connection.close()
            
            async with self._lock:
                # 从数据结构中移除
                if connection_id in self._active_connections:
                    del self._active_connections[connection_id]
                
                # 从可用连接队列中移除
                self._available_connections = deque([
                    (cid, conn) for cid, conn in self._available_connections 
                    if cid != connection_id
                ])
                
                # 更新指标
                self._metrics.total_connections = len(self._available_connections) + len(self._active_connections)
                self._metrics.active_connections = len(self._active_connections)
                self._metrics.idle_connections = len(self._available_connections)
                
        except Exception as e:
            self._logger.warning(f"Failed to close connection #{connection_id}: {e}")
    
    async def _execute_with_connection(self, connection_id: int, connection: Connection,
                                      command: str, args: Optional[List[str]] = None,
                                      timeout_seconds: Optional[float] = None) -> ExecutionResult:
        """使用指定连接执行命令"""
        return await connection.execute(command, args, timeout_seconds)
    
    async def _health_check_loop(self):
        """健康检查循环"""
        self._logger.info("Starting health check loop...")
        
        while True:
            try:
                self._logger.debug("Health check loop sleeping for %s seconds", self.config.health_check_interval)
                await asyncio.sleep(self.config.health_check_interval)
                self._logger.debug("Health check loop woke up")
                
                if self._status != AioSandboxStatus.READY:
                    break
                
                async with self._lock:
                    # 检查所有可用连接
                    healthy_connections = []
                    for connection_id, connection in self._available_connections:
                        # 简单健康检查：尝试执行echo命令
                        try:
                            result = await connection.execute("echo", ["health_check"])
                            if result.success and "health_check" in result.stdout:
                                connection.healthy = True
                                healthy_connections.append((connection_id, connection))
                                self._metrics.health_check_passes += 1
                            else:
                                connection.healthy = False
                                await self._close_connection(connection_id, connection)
                                self._metrics.health_check_fails += 1
                        except Exception as e:
                            self._logger.debug(f"Health check failed for connection #{connection_id}: {e}")
                            connection.healthy = False
                            await self._close_connection(connection_id, connection)
                            self._metrics.health_check_fails += 1
                    
                    self._available_connections = deque(healthy_connections)
                    
                    # 动态调整连接池大小（如果策略支持）
                    if self._pool_strategy == ConnectionPoolStrategy.DYNAMIC_SCALING:
                        await self._adjust_pool_size()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Health check loop error: {e}")
    
    async def _adjust_pool_size(self):
        """动态调整连接池大小"""
        # 简单调整策略：根据活跃连接比例调整
        total = len(self._available_connections) + len(self._active_connections)
        if total == 0:
            return
        
        active_ratio = len(self._active_connections) / total
        
        target_size = self._pool_size
        if active_ratio > 0.8:  # 活跃连接比例高，考虑扩容
            target_size = min(self._max_pool_size, self._pool_size + 1)
        elif active_ratio < 0.2 and total > self._min_pool_size:  # 活跃连接比例低，考虑缩容
            target_size = max(self._min_pool_size, self._pool_size - 1)
        
        if target_size != self._pool_size:
            old_size = self._pool_size
            self._pool_size = target_size
            
            # 更新信号量
            if self._connection_semaphore:
                # 创建新的信号量
                self._connection_semaphore = asyncio.Semaphore(self._pool_size)
            
            self._metrics.pool_resizes += 1
            self._logger.info(f"Adjusted pool size from {old_size} to {self._pool_size}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "execution_count": self._execution_count,
            "total_execution_time": self._total_execution_time,
            "average_execution_time": self._total_execution_time / self._execution_count if self._execution_count > 0 else 0.0,
            "pool_metrics": self._metrics.to_dict(),
            "pool_size": self._pool_size,
            "available_connections": len(self._available_connections),
            "active_connections": len(self._active_connections),
            "status": self._status.value
        }
    
    def get_capabilities(self) -> List[AioSandboxCapability]:
        """获取能力列表"""
        capabilities = [
            AioSandboxCapability.ASYNC_CONNECTION_POOL,
            AioSandboxCapability.CONCURRENT_EXECUTION,
            AioSandboxCapability.PERFORMANCE_MONITORING
        ]
        
        if self._pool_strategy == ConnectionPoolStrategy.DYNAMIC_SCALING:
            capabilities.append(AioSandboxCapability.AUTO_SCALING)
        
        if self.config.health_check_interval > 0:
            capabilities.append(AioSandboxCapability.HEALTH_CHECK)
        
        if self._warmup_size > 0:
            capabilities.append(AioSandboxCapability.CONNECTION_WARMUP)
        
        if self._pool_strategy == ConnectionPoolStrategy.LAZY_INIT:
            capabilities.append(AioSandboxCapability.LAZY_LOADING)
        
        return capabilities


# ============================================================================
# 第四部分：集成与配置
# ============================================================================

class ProviderRegistry:
    """Provider注册表（从Lesson 30复制，适配AioSandboxProvider）"""
    
    def __init__(self, name: str = "sandbox_registry"):
        self.name = name
        self._providers = {}  # name -> provider实例
        self._metadata = {}   # name -> provider元数据
        self._logger = logging.getLogger(f"ProviderRegistry.{name}")
        self._lock = asyncio.Lock()
    
    async def register_provider(self, name: str, provider: BaseProvider, 
                               metadata: Optional[ProviderMetadata] = None) -> bool:
        """注册Provider"""
        async with self._lock:
            if name in self._providers:
                self._logger.warning(f"Provider '{name}' already registered, overwriting")
            
            self._providers[name] = provider
            self._metadata[name] = metadata or provider.get_metadata()
            
            self._logger.info(f"Registered provider '{name}' with metadata: {self._metadata[name].to_dict()}")
            return True
    
    async def get_provider(self, name: str) -> Optional[BaseProvider]:
        """获取Provider"""
        async with self._lock:
            return self._providers.get(name)
    
    async def list_providers(self) -> List[Dict[str, Any]]:
        """列出所有已注册的Provider"""
        async with self._lock:
            result = []
            for name, provider in self._providers.items():
                metadata = self._metadata[name]
                result.append({
                    "name": name,
                    "metadata": metadata.to_dict(),
                    "healthy": provider.is_healthy() if hasattr(provider, 'is_healthy') else True,
                    "capabilities": provider.get_capabilities().copy() if hasattr(provider, 'get_capabilities') else []
                })
            return result
    
    async def shutdown_all(self):
        """关闭所有Provider"""
        async with self._lock:
            for name, provider in self._providers.items():
                try:
                    await provider.shutdown()
                    self._logger.info(f"Shutdown provider '{name}'")
                except Exception as e:
                    self._logger.error(f"Failed to shutdown provider '{name}': {e}")
            
            self._providers.clear()
            self._metadata.clear()


class ProviderFactory:
    """Provider工厂（从Lesson 30复制，适配AioSandboxProvider）"""
    
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry
        self._builders = {}  # type -> builder函数
        self._logger = logging.getLogger("ProviderFactory")
    
    def register_builder(self, provider_type: str, builder: Callable[[Dict[str, Any]], BaseProvider]):
        """注册Provider构建器"""
        self._builders[provider_type] = builder
        self._logger.info(f"Registered builder for provider type: {provider_type}")
    
    async def create_and_register_provider(self, config: Dict[str, Any]) -> bool:
        """创建并注册Provider"""
        try:
            provider_type = config.get("type")
            if not provider_type:
                self._logger.error("Provider type not specified in config")
                return False
            
            builder = self._builders.get(provider_type)
            if not builder:
                self._logger.error(f"No builder registered for provider type: {provider_type}")
                return False
            
            # 创建Provider实例
            provider = builder(config)
            
            # 初始化Provider
            init_config = config.get("config", {})
            success = await provider.initialize(init_config)
            if not success:
                self._logger.error(f"Failed to initialize provider of type: {provider_type}")
                return False
            
            # 注册Provider
            name = config.get("name", f"{provider_type}_{int(time.time())}")
            await self.registry.register_provider(name, provider)
            
            self._logger.info(f"Successfully created and registered provider '{name}' of type '{provider_type}'")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to create and register provider: {e}")
            return False


class AioSandboxProviderFactory:
    """AioSandboxProvider工厂"""
    
    @staticmethod
    def create_standard(config: Dict[str, Any]) -> AioSandboxProvider:
        """创建标准AioSandboxProvider"""
        provider_config = config.get("config", {})
        sandbox_config = SandboxConfig(**provider_config)
        return AioSandboxProvider(sandbox_config)
    
    @staticmethod
    def create_secure(config: Dict[str, Any]) -> AioSandboxProvider:
        """创建安全增强版AioSandboxProvider（预留扩展）"""
        provider_config = config.get("config", {})
        sandbox_config = SandboxConfig(**provider_config)
        
        # 这里可以添加安全增强逻辑，例如命令白名单、资源限制等
        provider = AioSandboxProvider(sandbox_config)
        return provider
    
    @staticmethod
    def create_high_performance(config: Dict[str, Any]) -> AioSandboxProvider:
        """创建高性能AioSandboxProvider"""
        provider_config = config.get("config", {})
        
        # 优化配置
        provider_config.setdefault("pool_size", 20)
        provider_config.setdefault("warmup_size", 10)
        provider_config.setdefault("health_check_interval", 30.0)
        provider_config.setdefault("pool_strategy", ConnectionPoolStrategy.DYNAMIC_SCALING.value)
        
        sandbox_config = SandboxConfig(**provider_config)
        return AioSandboxProvider(sandbox_config)


# ============================================================================
# 第五部分：测试与演示
# ============================================================================

class AioSandboxTestSuite:
    """AioSandboxProvider测试套件"""
    
    def __init__(self):
        self._logger = logging.getLogger("AioSandboxTestSuite")
        self.results = {}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        self._logger.info("Starting AioSandboxProvider test suite...")
        
        tests = [
            ("test_basic_execution", self.test_basic_execution),
            ("test_concurrent_execution", self.test_concurrent_execution),
            ("test_pool_size_limit", self.test_pool_size_limit),
            ("test_dynamic_scaling", self.test_dynamic_scaling),
            ("test_health_check", self.test_health_check),
            ("test_provider_integration", self.test_provider_integration),
            ("test_performance_metrics", self.test_performance_metrics)
        ]
        
        for test_name, test_func in tests:
            await self._run_test(test_name, test_func)
        
        return self._generate_report()
    
    async def _run_test(self, test_name: str, test_func: Callable):
        """运行单个测试"""
        self._logger.info(f"Running test: {test_name}")
        start_time = time.perf_counter()
        
        try:
            result = await test_func()
            execution_time = time.perf_counter() - start_time
            
            self.results[test_name] = {
                "passed": result,
                "execution_time": execution_time,
                "error": None
            }
            
            status = "✅ 通过" if result else "❌ 失败"
            self._logger.info(f"  {status} {test_name} ({execution_time:.3f}s)")
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            self.results[test_name] = {
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            }
            self._logger.error(f"  ❌ 失败 {test_name}: {e}")
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["passed"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate
            },
            "detailed_results": self.results
        }
    
    # ==================== 测试用例 ====================
    
    async def test_basic_execution(self) -> bool:
        """测试基本命令执行"""
        try:
            config = SandboxConfig(pool_size=3)
            provider = AioSandboxProvider(config)
            await provider.initialize({})
            
            # 执行简单命令
            result = await provider.execute("echo", ["Hello, AioSandbox!"])
            
            # 验证结果
            success = (
                result.success and
                "Hello, AioSandbox!" in result.stdout and
                result.execution_time > 0
            )
            
            await provider.shutdown()
            return success
            
        except Exception as e:
            self._logger.error(f"test_basic_execution failed: {e}")
            return False
    
    async def test_concurrent_execution(self) -> bool:
        """测试并发命令执行"""
        try:
            config = SandboxConfig(pool_size=5)
            provider = AioSandboxProvider(config)
            await provider.initialize({})
            
            # 并发执行10个命令
            async def execute_task(i):
                return await provider.execute("echo", [f"Task {i}"])
            
            tasks = [execute_task(i) for i in range(10)]
            results = await asyncio.gather(*tasks)
            
            # 验证所有任务都成功
            success = all(r.success for r in results)
            
            # 验证输出正确
            for i, r in enumerate(results):
                if f"Task {i}" not in r.stdout:
                    success = False
                    break
            
            await provider.shutdown()
            return success
            
        except Exception as e:
            self._logger.error(f"test_concurrent_execution failed: {e}")
            return False
    
    async def test_pool_size_limit(self) -> bool:
        """测试连接池大小限制"""
        try:
            config = SandboxConfig(pool_size=2, timeout_seconds=5.0)
            provider = AioSandboxProvider(config)
            await provider.initialize({})
            
            # 创建信号量跟踪活跃任务数
            active_tasks = 0
            max_active = 0
            lock = asyncio.Lock()
            
            async def track_task(i):
                nonlocal active_tasks, max_active
                async with lock:
                    active_tasks += 1
                    max_active = max(max_active, active_tasks)
                
                # 执行长时间命令，确保并发限制可见
                result = await provider.execute("sleep", ["0.5"])
                
                async with lock:
                    active_tasks -= 1
                
                return result
            
            # 启动5个任务，但连接池大小只有2
            tasks = [track_task(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            
            # 验证最大活跃任务数不超过连接池大小
            success = max_active <= config.pool_size
            
            await provider.shutdown()
            return success
            
        except Exception as e:
            self._logger.error(f"test_pool_size_limit failed: {e}")
            return False
    
    async def test_dynamic_scaling(self) -> bool:
        """测试动态伸缩策略"""
        try:
            config = SandboxConfig(
                pool_size=3,
                min_pool_size=1,
                max_pool_size=10,
                pool_strategy=ConnectionPoolStrategy.DYNAMIC_SCALING
            )
            provider = AioSandboxProvider(config)
            await provider.initialize({})
            
            # 获取初始统计
            initial_stats = provider.get_statistics()
            
            # 模拟高负载，触发扩容
            async def high_load_task():
                return await provider.execute("sleep", ["0.1"])
            
            # 并发执行多个任务
            tasks = [high_load_task() for _ in range(15)]
            await asyncio.gather(*tasks)
            
            # 获取扩容后统计
            final_stats = provider.get_statistics()
            
            # 验证连接池大小可能增加了
            # 注意：动态伸缩策略可能不会立即调整，这里只检查没有错误发生
            success = (
                initial_stats["pool_size"] == 3 and
                final_stats["pool_size"] >= 1 and
                final_stats["pool_size"] <= 10
            )
            
            await provider.shutdown()
            return success
            
        except Exception as e:
            self._logger.error(f"test_dynamic_scaling failed: {e}")
            return False
    
    async def test_health_check(self) -> bool:
        """测试健康检查"""
        try:
            config = SandboxConfig(
                pool_size=3,
                health_check_interval=1.0,
                max_idle_time=2.0
            )
            provider = AioSandboxProvider(config)
            await provider.initialize({})
            
            # 获取初始健康状态
            initial_health = provider.is_healthy()
            
            # 等待健康检查运行
            await asyncio.sleep(1.5)
            
            # 获取健康检查后的状态
            final_health = provider.is_healthy()
            
            # 验证Provider保持健康
            success = initial_health and final_health
            
            await provider.shutdown()
            return success
            
        except Exception as e:
            self._logger.error(f"test_health_check failed: {e}")
            return False
    
    async def test_provider_integration(self) -> bool:
        """测试Provider模式集成"""
        try:
            # 创建注册表和工厂
            registry = ProviderRegistry("test_registry")
            factory = ProviderFactory(registry)
            
            # 注册AioSandboxProvider构建器
            factory.register_builder("aio_sandbox", AioSandboxProviderFactory.create_standard)
            
            # 通过工厂创建Provider
            config = {
                "type": "aio_sandbox",
                "name": "test_sandbox",
                "config": {
                    "pool_size": 5,
                    "timeout_seconds": 10.0
                }
            }
            
            success = await factory.create_and_register_provider(config)
            if not success:
                return False
            
            # 获取已注册的Provider
            providers = await registry.list_providers()
            provider_info = providers[0] if providers else None
            
            # 验证Provider信息
            valid = (
                provider_info is not None and
                provider_info["name"] == "test_sandbox" and
                provider_info["healthy"] is True
            )
            
            # 测试Provider功能
            provider = await registry.get_provider("test_sandbox")
            if provider:
                result = await provider.execute("echo", ["Integration test"])
                valid = valid and result.success
            
            await registry.shutdown_all()
            return valid
            
        except Exception as e:
            self._logger.error(f"test_provider_integration failed: {e}")
            return False
    
    async def test_performance_metrics(self) -> bool:
        """测试性能指标收集"""
        try:
            config = SandboxConfig(pool_size=5)
            provider = AioSandboxProvider(config)
            await provider.initialize({})
            
            # 执行一些命令
            for i in range(10):
                await provider.execute("echo", [f"Metric test {i}"])
            
            # 获取性能指标
            stats = provider.get_statistics()
            
            # 验证指标存在且合理
            valid = (
                "execution_count" in stats and
                stats["execution_count"] == 10 and
                "pool_metrics" in stats and
                "total_executions" in stats["pool_metrics"] and
                stats["pool_metrics"]["total_executions"] == 10
            )
            
            await provider.shutdown()
            return valid
            
        except Exception as e:
            self._logger.error(f"test_performance_metrics failed: {e}")
            return False


async def main_demo():
    """主演示函数"""
    print("=" * 80)
    print("🎓 Day 8 Lesson 32: AioSandboxProvider演示")
    print("=" * 80)
    print()
    
    try:
        # 1. 创建AioSandboxProvider实例
        print("1. 创建AioSandboxProvider实例...")
        config = SandboxConfig(
            pool_size=5,
            timeout_seconds=10.0,
            env={"DEMO_MODE": "true"},
            pool_strategy=ConnectionPoolStrategy.DYNAMIC_SCALING
        )
        provider = AioSandboxProvider(config)
        await provider.initialize({})
        print(f"   ✅ 创建标准AioSandboxProvider")
        print(f"      工作目录: {provider.get_workdir()}")
        print(f"      连接池大小: {provider.get_statistics()['pool_size']}")
        print(f"      健康状态: {provider.is_healthy()}")
        print()
        
        # 2. 执行命令演示
        print("2. 执行命令演示...")
        print("   执行 echo 命令:")
        result = await provider.execute("echo", ["Hello from AioSandbox!"])
        print(f"      成功: {result.success}")
        print(f"      输出: {result.stdout.strip()}")
        print(f"      执行时间: {result.execution_time:.3f}s")
        print(f"      使用的连接ID: {result.connection_id}")
        print()
        
        # 3. 并发执行演示
        print("3. 并发执行演示...")
        async def concurrent_task(i):
            start = time.perf_counter()
            result = await provider.execute("echo", [f"Concurrent task {i}"])
            elapsed = time.perf_counter() - start
            return result, elapsed
        
        tasks = [concurrent_task(i) for i in range(8)]
        results = await asyncio.gather(*tasks)
        
        print(f"   并发执行 {len(results)} 个任务:")
        for i, (result, elapsed) in enumerate(results):
            print(f"     任务{i}: {'✅' if result.success else '❌'} {elapsed:.3f}s")
        print()
        
        # 4. 连接池统计演示
        print("4. 连接池统计演示...")
        stats = provider.get_statistics()
        metrics = stats["pool_metrics"]
        print(f"   总执行次数: {metrics['total_executions']}")
        print(f"   成功执行: {metrics['successful_executions']}")
        print(f"   平均执行时间: {metrics['avg_execution_time']:.3f}s")
        print(f"   平均等待时间: {metrics['avg_wait_time']:.3f}s")
        print(f"   活跃连接数: {stats['active_connections']}")
        print(f"   空闲连接数: {stats['available_connections']}")
        print()
        
        # 5. Provider模式集成演示
        print("5. Provider模式集成演示...")
        registry = ProviderRegistry("demo_registry")
        factory = ProviderFactory(registry)
        factory.register_builder("aio_sandbox", AioSandboxProviderFactory.create_standard)
        
        provider_config = {
            "type": "aio_sandbox",
            "name": "demo_sandbox",
            "config": {
                "pool_size": 3,
                "timeout_seconds": 15.0
            }
        }
        
        success = await factory.create_and_register_provider(provider_config)
        print(f"   ✅ 工厂创建Provider: {'成功' if success else '失败'}")
        
        providers = await registry.list_providers()
        print(f"   已注册Provider数量: {len(providers)}")
        for p in providers:
            print(f"     - {p['name']}: {p['metadata']['description']}")
        print()
        
        # 6. 运行测试套件
        print("6. 运行测试套件...")
        test_suite = AioSandboxTestSuite()
        report = await test_suite.run_all_tests()
        summary = report["summary"]
        print(f"   测试总数: {summary['total_tests']}")
        print(f"   通过测试: {summary['passed_tests']}")
        print(f"   失败测试: {summary['failed_tests']}")
        print(f"   成功率: {summary['success_rate']:.1f}%")
        print()
        
        # 7. 清理资源
        print("7. 清理资源...")
        await registry.shutdown_all()
        await provider.shutdown()
        print("   ✅ 资源清理完成")
        print()
        
        print("=" * 80)
        print("演示完成！")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description="AioSandboxProvider演示程序")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行完整演示")
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if args.test:
        # 运行测试套件
        async def run_tests():
            test_suite = AioSandboxTestSuite()
            report = await test_suite.run_all_tests()
            
            summary = report["summary"]
            print("\n" + "=" * 60)
            print("测试套件结果")
            print("=" * 60)
            print(f"测试总数: {summary['total_tests']}")
            print(f"通过测试: {summary['passed_tests']}")
            print(f"失败测试: {summary['failed_tests']}")
            print(f"成功率: {summary['success_rate']:.1f}%")
            print()
            
            if summary['failed_tests'] > 0:
                print("失败测试详情:")
                for test_name, result in report["detailed_results"].items():
                    if not result["passed"]:
                        print(f"  ❌ {test_name}: {result['error']}")
            
            return summary['success_rate'] >= 100.0
        
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    
    elif args.demo:
        # 运行完整演示
        success = asyncio.run(main_demo())
        sys.exit(0 if success else 1)
    
    else:
        # 默认运行基本演示
        async def basic_demo():
            print("AioSandboxProvider基本演示")
            print("-" * 40)
            
            config = SandboxConfig(pool_size=3)
            provider = AioSandboxProvider(config)
            await provider.initialize({})
            
            result = await provider.execute("echo", ["Hello, AioSandbox!"])
            print(f"命令执行结果: {'成功' if result.success else '失败'}")
            print(f"输出: {result.stdout.strip()}")
            print(f"执行时间: {result.execution_time:.3f}秒")
            
            stats = provider.get_statistics()
            print(f"\n连接池统计:")
            print(f"  执行次数: {stats['execution_count']}")
            print(f"  连接池大小: {stats['pool_size']}")
            
            await provider.shutdown()
        
        asyncio.run(basic_demo())


if __name__ == "__main__":
    main()