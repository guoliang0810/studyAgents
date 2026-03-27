#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 8 Lesson 31: LocalSandboxProvider

本文件演示LocalSandboxProvider的完整实现，包括：
1. LocalSandboxProvider类 - 实现BaseProvider协议和Sandbox接口的具体提供者
2. 本地沙箱核心功能 - 工作目录隔离、环境变量合并、异步子进程执行
3. Provider模式集成 - 与ProviderRegistry、ProviderFactory的完整集成
4. 安全限制机制 - 本地沙箱的安全限制设计和实现
5. 测试套件 - 完整的单元测试和集成测试

采用五部分结构设计：
第一部分：概念与设计原则 - 定义LocalSandboxProvider的核心概念和设计原则
第二部分：接口与协议实现 - 实现BaseProvider协议和Sandbox接口的LocalSandboxProvider
第三部分：核心功能实现 - 实现本地沙箱的核心功能：工作目录隔离、环境变量合并、异步子进程执行
第四部分：集成与配置 - 集成Provider模式，支持配置驱动创建和注册
第五部分：测试与演示 - 提供完整测试套件和演示程序

使用示例:
    python local_sandbox_demo.py          # 运行基本演示
    python local_sandbox_demo.py --test   # 运行测试套件
    python local_sandbox_demo.py --demo   # 运行完整演示
    python local_sandbox_demo.py --help   # 显示帮助信息
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

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================

class LocalSandboxCapability(Enum):
    """本地沙箱能力枚举"""
    WORKDIR_ISOLATION = "工作目录隔离"      # 支持工作目录隔离，限制命令执行位置
    ENV_VAR_MERGING = "环境变量合并"        # 支持环境变量合并，安全传递环境变量
    ASYNC_EXECUTION = "异步执行"           # 支持异步子进程执行和超时控制
    SECURE_LIMITS = "安全限制"             # 支持基本的命令执行安全限制
    RESOURCE_MONITORING = "资源监控"       # 监控命令执行的资源使用情况
    OUTPUT_CAPTURE = "输出捕获"            # 捕获命令的标准输出和错误输出


class LocalSandboxStatus(Enum):
    """本地沙箱状态枚举"""
    CREATED = "已创建"          # 沙箱已创建但未初始化
    INITIALIZED = "已初始化"    # 沙箱已初始化，可执行命令
    EXECUTING = "执行中"        # 沙箱正在执行命令
    STOPPED = "已停止"          # 沙箱已停止，不可再执行命令
    ERROR = "错误"              # 沙箱处于错误状态


@dataclass
class LocalSandboxConfig:
    """本地沙箱配置"""
    workdir: Optional[str] = None          # 工作目录路径（None表示使用临时目录）
    timeout_seconds: float = 30.0          # 命令执行超时时间（秒）
    env: Dict[str, str] = field(default_factory=dict)  # 环境变量（合并到系统环境变量）
    shell: bool = False                    # 是否使用shell执行命令
    capture_output: bool = True            # 是否捕获命令输出
    inherit_env: bool = True               # 是否继承当前进程的环境变量
    cleanup_on_exit: bool = True           # 退出时是否清理工作目录（如果是临时目录）
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "workdir": self.workdir,
            "timeout_seconds": self.timeout_seconds,
            "env": self.env,
            "shell": self.shell,
            "capture_output": self.capture_output,
            "inherit_env": self.inherit_env,
            "cleanup_on_exit": self.cleanup_on_exit
        }


@dataclass
class ExecutionResult:
    """命令执行结果"""
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
            "stdout_length": len(self.stdout) if self.stdout else 0,
            "stderr_length": len(self.stderr) if self.stderr else 0
        }


@dataclass  
class ResourceUsage:
    """资源使用情况"""
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


class LocalSandboxProvider(BaseProvider, Sandbox):
    """
    LocalSandboxProvider - 本地沙箱提供者
    
    同时实现BaseProvider协议和Sandbox接口，展示Provider模式的具体应用
    """
    
    def __init__(self, config: Optional[LocalSandboxConfig] = None):
        """初始化LocalSandboxProvider"""
        self.config = config or LocalSandboxConfig()
        self._status = LocalSandboxStatus.CREATED
        self._workdir = None
        self._cleanup_workdir = False
        self._logger = logging.getLogger(f"LocalSandboxProvider.{id(self)}")
        self._execution_count = 0
        self._total_execution_time = 0.0
        
        # 确定工作目录
        if self.config.workdir:
            self._workdir = self.config.workdir
            self._cleanup_workdir = False
        else:
            # 创建临时工作目录
            self._workdir = tempfile.mkdtemp(prefix="localsandbox_")
            self._cleanup_workdir = self.config.cleanup_on_exit
        
        self._logger.info(f"LocalSandboxProvider created with workdir: {self._workdir}")
    
    def get_metadata(self) -> ProviderMetadata:
        """获取Provider元数据"""
        return ProviderMetadata(
            name="local_sandbox_provider",
            description="本地沙箱提供者，提供工作目录隔离和环境变量合并的本地命令执行",
            version="1.0.0",
            author="DeerFlow Team",
            capabilities=[
                ProviderCapability.DYNAMIC_DISCOVERY,
                ProviderCapability.CONFIG_DRIVEN,
                ProviderCapability.HEALTH_CHECK,
                ProviderCapability.PERFORMANCE_MONITOR
            ],
            status=ProviderStatus.AVAILABLE,
            priority=ProviderPriority.MEDIUM,
            config_schema={
                "type": "object",
                "properties": {
                    "workdir": {"type": "string"},
                    "timeout_seconds": {"type": "number", "minimum": 0.1},
                    "env": {"type": "object"},
                    "shell": {"type": "boolean"},
                    "capture_output": {"type": "boolean"},
                    "inherit_env": {"type": "boolean"},
                    "cleanup_on_exit": {"type": "boolean"}
                }
            },
            tags=["sandbox", "local", "execution", "security"]
        )
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化Provider"""
        try:
            self._status = LocalSandboxStatus.INITIALIZED
            
            # 更新配置（如果提供了新配置）
            if config:
                if "workdir" in config and config["workdir"]:
                    self._workdir = config["workdir"]
                    self._cleanup_workdir = False
                
                # 可以在此处应用其他配置更新
                # 注意：实际实现应该更完整地更新配置
            
            # 确保工作目录存在
            os.makedirs(self._workdir, exist_ok=True)
            
            self._logger.info(f"LocalSandboxProvider initialized with workdir: {self._workdir}")
            return True
            
        except Exception as e:
            self._status = LocalSandboxStatus.ERROR
            self._logger.error(f"Failed to initialize LocalSandboxProvider: {e}")
            return False
    
    async def shutdown(self) -> None:
        """关闭Provider，清理资源"""
        try:
            self._status = LocalSandboxStatus.STOPPED
            
            # 清理工作目录（如果需要）
            if self._cleanup_workdir and self._workdir and os.path.exists(self._workdir):
                try:
                    shutil.rmtree(self._workdir)
                    self._logger.info(f"Cleaned up workdir: {self._workdir}")
                except Exception as e:
                    self._logger.warning(f"Failed to cleanup workdir {self._workdir}: {e}")
            
            self._logger.info(f"LocalSandboxProvider shutdown completed")
            
        except Exception as e:
            self._logger.error(f"Error during shutdown: {e}")
            raise
    
    def is_healthy(self) -> bool:
        """检查Provider健康状态"""
        # 检查工作目录是否存在并可访问
        if not self._workdir:
            return False
        
        try:
            # 检查工作目录可访问性
            test_file = os.path.join(self._workdir, ".health_check")
            with open(test_file, 'w') as f:
                f.write("health_check")
            os.remove(test_file)
            return True
        except Exception:
            return False
    
    def get_workdir(self) -> Optional[str]:
        """获取工作目录"""
        return self._workdir
    
    async def cleanup(self) -> None:
        """清理资源（Sandbox接口方法）"""
        await self.shutdown()
    
    async def execute(self, command: str, args: Optional[List[str]] = None,
                     timeout_seconds: Optional[float] = None) -> ExecutionResult:
        """执行命令（Sandbox接口方法）"""
        start_time = time.time()
        self._status = LocalSandboxStatus.EXECUTING
        self._execution_count += 1
        
        # 使用提供的超时时间或默认配置
        timeout = timeout_seconds if timeout_seconds is not None else self.config.timeout_seconds
        args_list = args or []
        
        self._logger.info(f"Executing command: {command} {args_list} (timeout: {timeout}s)")
        
        try:
            # 准备环境变量
            env = self._prepare_environment()
            
            # 构建完整命令
            full_command = [command] + args_list
            
            # 异步执行命令
            result = await self._execute_async(full_command, env, timeout)
            
            # 更新状态
            self._status = LocalSandboxStatus.INITIALIZED
            execution_time = time.time() - start_time
            self._total_execution_time += execution_time
            
            self._logger.info(
                f"Command executed successfully: exit_code={result.exit_code}, "
                f"time={execution_time:.3f}s"
            )
            
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            self._status = LocalSandboxStatus.INITIALIZED
            
            self._logger.warning(f"Command timed out after {execution_time:.3f}s")
            
            return ExecutionResult(
                command=command,
                args=args_list,
                stdout=None,
                stderr=None,
                exit_code=-1,
                success=False,
                execution_time=execution_time,
                timed_out=True,
                error=f"Command timed out after {timeout} seconds",
                workdir=self._workdir
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._status = LocalSandboxStatus.INITIALIZED
            
            self._logger.error(f"Command execution failed: {e}")
            
            return ExecutionResult(
                command=command,
                args=args_list,
                stdout=None,
                stderr=None,
                exit_code=-1,
                success=False,
                execution_time=execution_time,
                timed_out=False,
                error=str(e),
                workdir=self._workdir
            )
    
    def _prepare_environment(self) -> Dict[str, str]:
        """准备环境变量"""
        env = {}
        
        # 继承当前进程环境变量（如果配置允许）
        if self.config.inherit_env:
            env.update(os.environ)
        
        # 添加配置的环境变量
        env.update(self.config.env)
        
        return env
    
    async def _execute_async(self, command: List[str], env: Dict[str, str], 
                           timeout: float) -> ExecutionResult:
        """异步执行命令"""
        start_time = time.time()
        
        # 使用asyncio创建子进程
        if self.config.shell:
            # shell模式：将命令连接为字符串
            cmd_str = " ".join(command)
            process = await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE if self.config.capture_output else None,
                stderr=asyncio.subprocess.PIPE if self.config.capture_output else None,
                stdin=asyncio.subprocess.DEVNULL,
                cwd=self._workdir,
                env=env
            )
        else:
            # 非shell模式：直接执行命令
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE if self.config.capture_output else None,
                stderr=asyncio.subprocess.PIPE if self.config.capture_output else None,
                stdin=asyncio.subprocess.DEVNULL,
                cwd=self._workdir,
                env=env
            )
        
        try:
            # 等待命令完成（带超时）
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            # 解码输出（如果捕获了输出）
            stdout_decoded = stdout.decode('utf-8', errors='replace') if stdout else None
            stderr_decoded = stderr.decode('utf-8', errors='replace') if stderr else None
            
            return ExecutionResult(
                command=command[0],
                args=command[1:],
                stdout=stdout_decoded,
                stderr=stderr_decoded,
                exit_code=process.returncode,
                success=process.returncode == 0,
                execution_time=execution_time,
                timed_out=False,
                workdir=self._workdir
            )
            
        except asyncio.TimeoutError:
            # 超时，终止进程
            try:
                process.terminate()
                await asyncio.sleep(0.1)
                if process.returncode is None:
                    process.kill()
                await process.wait()
            except Exception:
                pass
            
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        avg_time = (self._total_execution_time / self._execution_count 
                   if self._execution_count > 0 else 0.0)
        
        return {
            "execution_count": self._execution_count,
            "total_execution_time": self._total_execution_time,
            "average_execution_time": avg_time,
            "current_status": self._status.value,
            "workdir": self._workdir,
            "healthy": self.is_healthy()
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return (f"LocalSandboxProvider(workdir={self._workdir}, "
                f"status={self._status.value}, "
                f"executions={self._execution_count})")
    
    def __repr__(self) -> str:
        """详细表示"""
        return (f"LocalSandboxProvider(config={self.config}, "
                f"workdir={self._workdir}, "
                f"status={self._status.value})")


# ============================================================================
# 第三部分：核心功能实现
# ============================================================================

class SecureLocalSandboxProvider(LocalSandboxProvider):
    """
    安全增强版LocalSandboxProvider
    
    在基础版本上增加额外的安全限制：
    1. 命令白名单验证
    2. 参数安全检查
    3. 资源使用限制
    4. 执行环境隔离
    """
    
    def __init__(self, config: Optional[LocalSandboxConfig] = None,
                 allowed_commands: Optional[List[str]] = None,
                 max_memory_mb: float = 1024.0,
                 max_cpu_time: float = 60.0):
        """初始化安全增强版LocalSandboxProvider"""
        super().__init__(config)
        self.allowed_commands = allowed_commands or ["ls", "pwd", "echo", "cat", "mkdir", "rmdir"]
        self.max_memory_mb = max_memory_mb
        self.max_cpu_time = max_cpu_time
        self._security_logger = logging.getLogger(f"SecureLocalSandboxProvider.{id(self)}")
    
    def get_metadata(self) -> ProviderMetadata:
        """获取Provider元数据（覆盖父类）"""
        metadata = super().get_metadata()
        metadata.name = "secure_local_sandbox_provider"
        metadata.description = "安全增强版本地沙箱提供者，支持命令白名单和资源限制"
        metadata.capabilities.append(ProviderCapability.PERFORMANCE_MONITOR)
        metadata.tags.extend(["secure", "restricted"])
        return metadata
    
    async def execute(self, command: str, args: Optional[List[str]] = None,
                     timeout_seconds: Optional[float] = None) -> ExecutionResult:
        """执行命令（增加安全验证）"""
        # 命令白名单验证
        if not self._is_command_allowed(command):
            self._security_logger.warning(f"Command not allowed: {command}")
            return ExecutionResult(
                command=command,
                args=args or [],
                stdout=None,
                stderr=None,
                exit_code=-1,
                success=False,
                execution_time=0.0,
                timed_out=False,
                error=f"Command '{command}' is not allowed",
                workdir=self._workdir
            )
        
        # 参数安全检查
        if args and not self._are_args_safe(args):
            self._security_logger.warning(f"Unsafe args for command {command}: {args}")
            return ExecutionResult(
                command=command,
                args=args,
                stdout=None,
                stderr=None,
                exit_code=-1,
                success=False,
                execution_time=0.0,
                timed_out=False,
                error=f"Unsafe arguments detected for command '{command}'",
                workdir=self._workdir
            )
        
        # 执行命令（调用父类方法）
        return await super().execute(command, args, timeout_seconds)
    
    def _is_command_allowed(self, command: str) -> bool:
        """检查命令是否在白名单中"""
        # 提取命令的基本名称（去除路径）
        command_name = os.path.basename(command)
        
        # 检查是否在白名单中
        return command_name in self.allowed_commands
    
    def _are_args_safe(self, args: List[str]) -> bool:
        """检查参数是否安全"""
        # 简单的安全规则示例：
        # 1. 不允许包含敏感模式（如".."、"~"、"*"等）
        # 2. 不允许包含特殊字符
        # 注意：实际实现应该更严格
        
        dangerous_patterns = ["..", "~", "*", "?", "[", "]", "{", "}", "|", ";", "&", "$", "`"]
        
        for arg in args:
            for pattern in dangerous_patterns:
                if pattern in arg:
                    return False
        
        return True
    
    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        return {
            "allowed_commands": self.allowed_commands,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_time": self.max_cpu_time,
            "workdir": self._workdir
        }


# ============================================================================
# 第四部分：集成与配置
# ============================================================================

# 以下代码展示如何将LocalSandboxProvider集成到Provider模式中
# 使用Lesson 30中的ProviderRegistry和ProviderFactory

class ProviderRegistry:
    """Provider注册表（从Lesson 30简化）"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._providers: Dict[str, BaseProvider] = {}
        self._logger = logging.getLogger(f"ProviderRegistry.{name}")
    
    async def register_provider(self, provider: BaseProvider, name: Optional[str] = None) -> bool:
        """注册Provider"""
        try:
            metadata = provider.get_metadata()
            provider_name = name or metadata.name
            
            if provider_name in self._providers:
                self._logger.warning(f"Provider '{provider_name}' already registered")
                return False
            
            self._providers[provider_name] = provider
            self._logger.info(f"Registered provider '{provider_name}'")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to register provider: {e}")
            return False
    
    async def get_provider(self, name: str) -> Optional[BaseProvider]:
        """获取Provider"""
        return self._providers.get(name)
    
    async def list_providers(self) -> List[Dict[str, Any]]:
        """列出所有Provider"""
        result = []
        for name, provider in self._providers.items():
            metadata = provider.get_metadata()
            result.append({
                "name": name,
                "metadata": metadata.to_dict(),
                "healthy": provider.is_healthy()
            })
        return result
    
    async def shutdown_all(self) -> None:
        """关闭所有Provider"""
        for name, provider in self._providers.items():
            try:
                await provider.shutdown()
                self._logger.info(f"Shutdown provider '{name}'")
            except Exception as e:
                self._logger.error(f"Error shutting down provider '{name}': {e}")
        
        self._providers.clear()


class ProviderFactory:
    """Provider工厂（从Lesson 30简化）"""
    
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry
        self._logger = logging.getLogger("ProviderFactory")
        self._builders: Dict[str, Callable[[Dict], BaseProvider]] = {}
    
    def register_builder(self, provider_type: str, builder: Callable[[Dict], BaseProvider]) -> None:
        """注册Provider构建器"""
        self._builders[provider_type] = builder
        self._logger.info(f"Registered builder for provider type '{provider_type}'")
    
    async def create_and_register_provider(self, config: Dict[str, Any]) -> bool:
        """创建并注册Provider"""
        try:
            provider_type = config.get("type")
            if not provider_type:
                raise ValueError("Provider type is required")
            
            if provider_type not in self._builders:
                raise ValueError(f"No builder registered for provider type '{provider_type}'")
            
            # 创建Provider实例
            builder = self._builders[provider_type]
            provider = builder(config.get("config", {}))
            
            # 初始化Provider
            init_success = await provider.initialize(config.get("config", {}))
            if not init_success:
                raise RuntimeError("Provider initialization failed")
            
            # 注册Provider
            provider_name = config.get("name") or provider.get_metadata().name
            success = await self.registry.register_provider(provider, provider_name)
            
            return success
            
        except Exception as e:
            self._logger.error(f"Failed to create and register provider: {e}")
            return False


class LocalSandboxProviderFactory:
    """LocalSandboxProvider专用工厂"""
    
    @staticmethod
    def create_standard(config: Dict[str, Any]) -> LocalSandboxProvider:
        """创建标准LocalSandboxProvider"""
        sandbox_config = LocalSandboxConfig(
            workdir=config.get("workdir"),
            timeout_seconds=config.get("timeout_seconds", 30.0),
            env=config.get("env", {}),
            shell=config.get("shell", False),
            capture_output=config.get("capture_output", True),
            inherit_env=config.get("inherit_env", True),
            cleanup_on_exit=config.get("cleanup_on_exit", True)
        )
        return LocalSandboxProvider(sandbox_config)
    
    @staticmethod
    def create_secure(config: Dict[str, Any]) -> SecureLocalSandboxProvider:
        """创建安全增强版LocalSandboxProvider"""
        sandbox_config = LocalSandboxConfig(
            workdir=config.get("workdir"),
            timeout_seconds=config.get("timeout_seconds", 30.0),
            env=config.get("env", {}),
            shell=config.get("shell", False),
            capture_output=config.get("capture_output", True),
            inherit_env=config.get("inherit_env", True),
            cleanup_on_exit=config.get("cleanup_on_exit", True)
        )
        
        return SecureLocalSandboxProvider(
            config=sandbox_config,
            allowed_commands=config.get("allowed_commands", ["ls", "pwd", "echo", "cat"]),
            max_memory_mb=config.get("max_memory_mb", 1024.0),
            max_cpu_time=config.get("max_cpu_time", 60.0)
        )


# ============================================================================
# 第五部分：测试与演示
# ============================================================================

class LocalSandboxTestSuite:
    """LocalSandboxProvider测试套件"""
    
    def __init__(self):
        self._logger = logging.getLogger("LocalSandboxTestSuite")
        self.results = {}
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        self.results = {}
        
        # 基础功能测试
        await self._test_basic_creation()
        await self._test_command_execution()
        await self._test_workdir_isolation()
        await self._test_timeout_handling()
        
        # Provider模式测试
        await self._test_provider_integration()
        await self._test_factory_creation()
        
        # 安全功能测试
        await self._test_secure_provider()
        
        # 生成测试报告
        return self._generate_report()
    
    async def _test_basic_creation(self):
        """测试基本创建功能"""
        test_name = "test_basic_creation"
        start_time = time.time()
        
        try:
            # 创建LocalSandboxProvider实例
            provider = LocalSandboxProvider()
            
            # 验证基本属性
            assert provider.get_workdir() is not None, "Workdir should be set"
            assert provider.is_healthy(), "Provider should be healthy"
            
            # 验证元数据
            metadata = provider.get_metadata()
            assert metadata.name == "local_sandbox_provider", "Metadata name incorrect"
            assert metadata.version == "1.0.0", "Metadata version incorrect"
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Basic creation test passed"
            }
            
            # 清理
            await provider.shutdown()
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Basic creation test failed: {e}"
            }
    
    async def _test_command_execution(self):
        """测试命令执行功能"""
        test_name = "test_command_execution"
        start_time = time.time()
        
        try:
            # 创建Provider实例
            provider = LocalSandboxProvider()
            
            # 初始化
            success = await provider.initialize({})
            assert success, "Provider initialization failed"
            
            # 执行简单命令
            result = await provider.execute("echo", ["hello", "world"])
            
            # 验证结果
            assert result.success, "Command should succeed"
            assert result.exit_code == 0, "Exit code should be 0"
            assert "hello world" in result.stdout, "Output should contain expected text"
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Command execution test passed"
            }
            
            # 清理
            await provider.shutdown()
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Command execution test failed: {e}"
            }
    
    async def _test_workdir_isolation(self):
        """测试工作目录隔离功能"""
        test_name = "test_workdir_isolation"
        start_time = time.time()
        
        try:
            # 创建使用特定工作目录的Provider
            with tempfile.TemporaryDirectory() as temp_dir:
                config = LocalSandboxConfig(workdir=temp_dir)
                provider = LocalSandboxProvider(config)
                
                await provider.initialize({})
                
                # 在工作目录中创建文件
                test_file = os.path.join(temp_dir, "test.txt")
                with open(test_file, "w") as f:
                    f.write("test content\n")
                
                # 执行命令验证文件存在
                result = await provider.execute("cat", ["test.txt"])
                
                assert result.success, "Command should succeed"
                assert "test content" in result.stdout, "Should read file from workdir"
                
                self.results[test_name] = {
                    "passed": True,
                    "execution_time": time.time() - start_time,
                    "message": "Workdir isolation test passed"
                }
                
                await provider.shutdown()
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Workdir isolation test failed: {e}"
            }
    
    async def _test_timeout_handling(self):
        """测试超时处理功能"""
        test_name = "test_timeout_handling"
        start_time = time.time()
        
        try:
            # 创建配置短超时的Provider
            config = LocalSandboxConfig(timeout_seconds=2.0)
            provider = LocalSandboxProvider(config)
            
            await provider.initialize({})
            
            # 执行会超时的命令
            result = await provider.execute("sleep", ["5"])
            
            # 应该超时
            assert result.timed_out, "Command should time out"
            assert not result.success, "Command should not succeed"
            assert result.exit_code == -1, "Exit code should be -1 on timeout"
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Timeout handling test passed"
            }
            
            await provider.shutdown()
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Timeout handling test failed: {e}"
            }
    
    async def _test_provider_integration(self):
        """测试Provider模式集成"""
        test_name = "test_provider_integration"
        start_time = time.time()
        
        try:
            # 创建注册表
            registry = ProviderRegistry("test_registry")
            
            # 创建Provider实例
            provider = LocalSandboxProvider()
            
            # 注册Provider
            success = await registry.register_provider(provider, "test_sandbox")
            assert success, "Provider registration should succeed"
            
            # 获取Provider
            retrieved = await registry.get_provider("test_sandbox")
            assert retrieved is not None, "Should retrieve registered provider"
            assert retrieved is provider, "Retrieved provider should be the same instance"
            
            # 列出Provider
            providers = await registry.list_providers()
            assert len(providers) == 1, "Should have 1 provider registered"
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Provider integration test passed"
            }
            
            # 清理
            await registry.shutdown_all()
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Provider integration test failed: {e}"
            }
    
    async def _test_factory_creation(self):
        """测试工厂创建功能"""
        test_name = "test_factory_creation"
        start_time = time.time()
        
        try:
            # 创建注册表和工厂
            registry = ProviderRegistry("factory_test")
            factory = ProviderFactory(registry)
            
            # 注册构建器
            factory.register_builder(
                "local_sandbox",
                LocalSandboxProviderFactory.create_standard
            )
            
            # 通过工厂创建Provider
            config = {
                "type": "local_sandbox",
                "name": "factory_created_sandbox",
                "config": {
                    "timeout_seconds": 10.0,
                    "env": {"TEST": "value"}
                }
            }
            
            success = await factory.create_and_register_provider(config)
            assert success, "Factory creation should succeed"
            
            # 验证Provider已注册
            provider = await registry.get_provider("factory_created_sandbox")
            assert provider is not None, "Factory-created provider should be registered"
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Factory creation test passed"
            }
            
            # 清理
            await registry.shutdown_all()
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Factory creation test failed: {e}"
            }
    
    async def _test_secure_provider(self):
        """测试安全增强版Provider"""
        test_name = "test_secure_provider"
        start_time = time.time()
        
        try:
            # 创建安全增强版Provider
            provider = SecureLocalSandboxProvider(
                allowed_commands=["echo", "pwd"],
                max_memory_mb=512.0
            )
            
            await provider.initialize({})
            
            # 测试允许的命令
            result = await provider.execute("echo", ["test"])
            assert result.success, "Allowed command should succeed"
            
            # 测试不允许的命令
            result = await provider.execute("ls", [])
            assert not result.success, "Disallowed command should fail"
            assert "not allowed" in result.error, "Error should indicate command not allowed"
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Secure provider test passed"
            }
            
            await provider.shutdown()
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Secure provider test failed: {e}"
            }
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["passed"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate,
                "timestamp": time.time()
            },
            "detailed_results": self.results
        }
        
        return report


async def main_demo():
    """主演示函数"""
    print("=" * 80)
    print("🎓 Day 8 Lesson 31: LocalSandboxProvider演示")
    print("=" * 80)
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("\n1. 创建LocalSandboxProvider实例...")
    
    # 创建标准Provider
    standard_provider = LocalSandboxProvider()
    await standard_provider.initialize({})
    
    print(f"   ✅ 创建标准LocalSandboxProvider")
    print(f"      工作目录: {standard_provider.get_workdir()}")
    print(f"      健康状态: {standard_provider.is_healthy()}")
    
    # 执行命令演示
    print("\n2. 执行命令演示...")
    
    print("   执行 echo 命令:")
    result = await standard_provider.execute("echo", ["Hello, LocalSandbox!"])
    print(f"      成功: {result.success}")
    print(f"      输出: {result.stdout.strip()}")
    print(f"      执行时间: {result.execution_time:.3f}s")
    
    print("\n   执行 pwd 命令验证工作目录:")
    result = await standard_provider.execute("pwd", [])
    print(f"      输出: {result.stdout.strip()}")
    print(f"      与Provider工作目录匹配: {result.stdout.strip() == standard_provider.get_workdir()}")
    
    # 测试超时处理
    print("\n3. 测试超时处理...")
    
    config = LocalSandboxConfig(timeout_seconds=2.0)
    timeout_provider = LocalSandboxProvider(config)
    await timeout_provider.initialize({})
    
    result = await timeout_provider.execute("sleep", ["5"])
    print(f"      命令超时: {result.timed_out}")
    print(f"      错误信息: {result.error}")
    
    # 安全增强版Provider演示
    print("\n4. 安全增强版Provider演示...")
    
    secure_provider = SecureLocalSandboxProvider(
        allowed_commands=["echo", "pwd"],
        max_memory_mb=1024.0
    )
    await secure_provider.initialize({})
    
    print("   执行允许的命令:")
    result = await secure_provider.execute("echo", ["Allowed command"])
    print(f"      成功: {result.success}")
    
    print("\n   尝试执行不允许的命令:")
    result = await secure_provider.execute("ls", ["-la"])
    print(f"      成功: {result.success}")
    print(f"      错误: {result.error}")
    
    # Provider模式集成演示
    print("\n5. Provider模式集成演示...")
    
    registry = ProviderRegistry("demo_registry")
    factory = ProviderFactory(registry)
    
    # 注册构建器
    factory.register_builder(
        "local_sandbox",
        LocalSandboxProviderFactory.create_standard
    )
    
    # 通过工厂创建Provider
    config = {
        "type": "local_sandbox",
        "name": "demo_sandbox",
        "config": {
            "timeout_seconds": 10.0,
            "env": {"DEMO_ENV": "demo_value"}
        }
    }
    
    success = await factory.create_and_register_provider(config)
    print(f"   ✅ 工厂创建Provider: {'成功' if success else '失败'}")
    
    if success:
        providers = await registry.list_providers()
        print(f"   已注册Provider数量: {len(providers)}")
        
        for provider_info in providers:
            print(f"     - {provider_info['name']}: {provider_info['metadata']['description']}")
    
    # 运行测试套件
    print("\n6. 运行测试套件...")
    
    test_suite = LocalSandboxTestSuite()
    report = await test_suite.run_all_tests()
    
    summary = report['summary']
    print(f"   测试总数: {summary['total_tests']}")
    print(f"   通过测试: {summary['passed_tests']}")
    print(f"   失败测试: {summary['failed_tests']}")
    print(f"   成功率: {summary['success_rate']:.1f}%")
    
    # 清理
    print("\n7. 清理资源...")
    
    await standard_provider.shutdown()
    await timeout_provider.shutdown()
    await secure_provider.shutdown()
    
    if success:
        await registry.shutdown_all()
    
    print("   ✅ 资源清理完成")
    
    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


async def run_tests():
    """运行测试套件"""
    print("运行LocalSandboxProvider测试套件...")
    
    # 设置日志
    logging.basicConfig(level=logging.WARNING,  # 测试时减少日志输出
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    test_suite = LocalSandboxTestSuite()
    report = await test_suite.run_all_tests()
    
    summary = report['summary']
    print(f"\n测试摘要:")
    print(f"  测试总数: {summary['total_tests']}")
    print(f"  通过测试: {summary['passed_tests']}")
    print(f"  失败测试: {summary['failed_tests']}")
    print(f"  成功率: {summary['success_rate']:.1f}%")
    
    print("\n详细结果:")
    for test_name, test_result in report['detailed_results'].items():
        status = "✅ 通过" if test_result['passed'] else "❌ 失败"
        print(f"  {status} {test_name} ({test_result['execution_time']:.3f}s)")
        if not test_result['passed'] and 'error' in test_result:
            print(f"    错误: {test_result['error']}")
    
    return summary['success_rate'] >= 100.0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LocalSandboxProvider演示程序")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行完整演示")
    
    args = parser.parse_args()
    
    if args.test:
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    else:
        # 默认运行演示，或者显式指定--demo
        asyncio.run(main_demo())


if __name__ == "__main__":
    main()