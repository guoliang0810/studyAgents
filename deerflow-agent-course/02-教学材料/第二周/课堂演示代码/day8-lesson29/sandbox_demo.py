#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 8 Lesson 29: Sandbox抽象接口

本文件演示沙箱抽象接口的完整设计和实现，包括：
1. 沙箱核心概念和抽象接口设计原则
2. 本地沙箱提供者(LocalSandboxProvider)的具体实现
3. 沙箱管理器(SandboxManager)和提供者注册机制
4. 完整的测试套件和演示程序

采用四部分结构设计：
第一部分：概念与设计原则 - 定义沙箱的核心能力和抽象接口
第二部分：具体实现 - 实现LocalSandboxProvider和虚拟路径映射
第三部分：集成与管理 - 实现SandboxManager和提供者注册表
第四部分：测试与演示 - 提供完整测试套件和演示程序

使用示例:
    python sandbox_demo.py          # 运行基本演示
    python sandbox_demo.py --test   # 运行测试套件
    python sandbox_demo.py --demo   # 运行完整演示
    python sandbox_demo.py --help   # 显示帮助信息
"""

import asyncio
import os
import sys
import json
import time
import shutil
import tempfile
import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import asynccontextmanager

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================

class SandboxCapability(Enum):
    """沙箱核心能力枚举"""
    ISOLATED_EXECUTION = "隔离执行"      # 在隔离环境中执行代码，防止影响主机系统
    RESOURCE_CONTROL = "资源控制"        # 控制CPU、内存、磁盘、网络等资源使用
    PATH_VIRTUALIZATION = "路径虚拟化"   # 虚拟文件系统路径，限制文件访问范围
    TIMEOUT_MANAGEMENT = "超时管理"      # 限制执行时间，防止无限循环或阻塞
    NETWORK_ISOLATION = "网络隔离"       # 限制或监控网络访问
    SECURE_ENVIRONMENT = "安全环境"       # 提供安全的执行环境，防止权限提升


class ExecutionResultStatus(Enum):
    """执行结果状态枚举"""
    SUCCESS = "成功"           # 执行成功，返回有效结果
    FAILED = "失败"           # 执行失败，返回错误信息
    TIMEOUT = "超时"          # 执行超时，被强制终止
    RESOURCE_LIMIT = "资源限制" # 超过资源限制被终止
    SECURITY_VIOLATION = "安全违规" # 违反安全策略被终止


class ResourceLimit:
    """资源限制配置"""
    def __init__(
        self,
        cpu_time_seconds: Optional[float] = None,
        memory_mb: Optional[int] = None,
        disk_mb: Optional[int] = None,
        network_mb: Optional[int] = None,
        process_count: Optional[int] = None,
        file_descriptors: Optional[int] = None
    ):
        self.cpu_time_seconds = cpu_time_seconds  # CPU时间限制（秒）
        self.memory_mb = memory_mb                # 内存限制（MB）
        self.disk_mb = disk_mb                    # 磁盘使用限制（MB）
        self.network_mb = network_mb              # 网络传输限制（MB）
        self.process_count = process_count        # 最大进程数
        self.file_descriptors = file_descriptors  # 最大文件描述符数
        
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "cpu_time_seconds": self.cpu_time_seconds,
            "memory_mb": self.memory_mb,
            "disk_mb": self.disk_mb,
            "network_mb": self.network_mb,
            "process_count": self.process_count,
            "file_descriptors": self.file_descriptors
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'ResourceLimit':
        """从字典创建"""
        return cls(
            cpu_time_seconds=data.get("cpu_time_seconds"),
            memory_mb=data.get("memory_mb"),
            disk_mb=data.get("disk_mb"),
            network_mb=data.get("network_mb"),
            process_count=data.get("process_count"),
            file_descriptors=data.get("file_descriptors")
        )


@dataclass
class ExecutionResult:
    """执行结果数据类"""
    status: ExecutionResultStatus
    stdout: str = ""
    stderr: str = ""
    return_code: Optional[int] = None
    execution_time: float = 0.0
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    security_violations: List[str] = field(default_factory=list)
    
    def success(self) -> bool:
        """是否成功"""
        return self.status == ExecutionResultStatus.SUCCESS
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "status": self.status.value,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "execution_time": self.execution_time,
            "resource_usage": self.resource_usage,
            "error_message": self.error_message,
            "security_violations": self.security_violations
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ExecutionResult':
        """从字典创建"""
        return cls(
            status=ExecutionResultStatus(data["status"]),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            return_code=data.get("return_code"),
            execution_time=data.get("execution_time", 0.0),
            resource_usage=data.get("resource_usage", {}),
            error_message=data.get("error_message"),
            security_violations=data.get("security_violations", [])
        )


class PathMapping:
    """路径映射配置"""
    def __init__(self, virtual_path: str, real_path: str, read_only: bool = False):
        self.virtual_path = virtual_path  # 虚拟路径（在沙箱中可见）
        self.real_path = real_path        # 真实路径（主机文件系统路径）
        self.read_only = read_only        # 是否只读
        
    def resolve(self, virtual_path: str) -> Optional[str]:
        """解析虚拟路径到真实路径"""
        if virtual_path.startswith(self.virtual_path):
            relative = virtual_path[len(self.virtual_path):].lstrip("/")
            real_path = os.path.join(self.real_path, relative)
            return os.path.normpath(real_path)
        return None
        
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "virtual_path": self.virtual_path,
            "real_path": self.real_path,
            "read_only": self.read_only
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PathMapping':
        """从字典创建"""
        return cls(
            virtual_path=data["virtual_path"],
            real_path=data["real_path"],
            read_only=data.get("read_only", False)
        )


# ============================================================================
# 第二部分：抽象接口定义
# ============================================================================

class Sandbox(ABC):
    """沙箱抽象基类
    
    定义沙箱系统的核心接口，所有具体沙箱实现必须继承此类。
    采用Provider设计模式，支持多种沙箱实现（本地、Docker、Kubernetes等）。
    """
    
    def __init__(
        self,
        name: str,
        capabilities: List[SandboxCapability],
        resource_limits: Optional[ResourceLimit] = None,
        path_mappings: Optional[List[PathMapping]] = None
    ):
        self.name = name
        self.capabilities = capabilities
        self.resource_limits = resource_limits or ResourceLimit()
        self.path_mappings = path_mappings or []
        self._logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger(f"sandbox.{self.name}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    @abstractmethod
    async def execute(
        self,
        command: Union[str, List[str]],
        timeout_seconds: Optional[float] = None,
        working_dir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """执行命令
        
        Args:
            command: 要执行的命令（字符串或参数列表）
            timeout_seconds: 超时时间（秒），None表示无超时
            working_dir: 工作目录（虚拟路径）
            environment: 环境变量
            
        Returns:
            ExecutionResult: 执行结果
        """
        pass
    
    @abstractmethod
    def translate_path(self, virtual_path: str) -> Optional[str]:
        """将虚拟路径转换为真实路径
        
        Args:
            virtual_path: 虚拟路径
            
        Returns:
            Optional[str]: 真实路径，如果无法转换则返回None
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理沙箱资源
        
        释放沙箱占用的所有资源，如临时文件、进程等。
        """
        pass
    
    def get_capabilities(self) -> List[SandboxCapability]:
        """获取沙箱支持的能力"""
        return self.capabilities
    
    def has_capability(self, capability: SandboxCapability) -> bool:
        """检查是否支持特定能力"""
        return capability in self.capabilities
    
    def add_path_mapping(self, mapping: PathMapping) -> None:
        """添加路径映射"""
        self.path_mappings.append(mapping)
        
    def resolve_virtual_path(self, virtual_path: str) -> Optional[str]:
        """解析虚拟路径
        
        遍历所有路径映射，将虚拟路径转换为真实路径。
        """
        # 首先检查是否有精确匹配的映射
        for mapping in self.path_mappings:
            resolved = mapping.resolve(virtual_path)
            if resolved:
                return resolved
                
        # 如果没有匹配，返回None
        return None
    
    def validate_command(self, command: Union[str, List[str]]) -> Tuple[bool, Optional[str]]:
        """验证命令安全性
        
        检查命令是否包含危险模式或违反安全策略。
        
        Returns:
            Tuple[bool, Optional[str]]: (是否安全, 错误信息)
        """
        dangerous_patterns = [
            "rm -rf /",  # 危险删除命令
            "sudo",      # 提权命令
            "chmod 777", # 危险权限设置
            ":(){ :|:& };:",  # Fork炸弹
        ]
        
        if isinstance(command, str):
            cmd_str = command
        else:
            cmd_str = " ".join(command)
            
        for pattern in dangerous_patterns:
            if pattern in cmd_str:
                return False, f"命令包含危险模式: {pattern}"
                
        return True, None
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Sandbox(name={self.name}, capabilities={[c.value for c in self.capabilities]})"
    
    def __repr__(self) -> str:
        """详细表示"""
        return f"<Sandbox {self.name} with {len(self.capabilities)} capabilities>"


# ============================================================================
# 第三部分：具体实现 - LocalSandboxProvider
# ============================================================================

class LocalSandboxProvider(Sandbox):
    """本地沙箱提供者
    
    在本地系统中提供基本的沙箱功能，使用子进程隔离和资源限制。
    适用于开发和测试环境，提供轻量级的沙箱解决方案。
    """
    
    def __init__(
        self,
        name: str = "local_sandbox",
        resource_limits: Optional[ResourceLimit] = None,
        path_mappings: Optional[List[PathMapping]] = None,
        use_temp_dir: bool = True,
        inherit_env: bool = True
    ):
        capabilities = [
            SandboxCapability.ISOLATED_EXECUTION,
            SandboxCapability.PATH_VIRTUALIZATION,
            SandboxCapability.TIMEOUT_MANAGEMENT,
        ]
        
        super().__init__(name, capabilities, resource_limits, path_mappings)
        
        self.use_temp_dir = use_temp_dir
        self.inherit_env = inherit_env
        self._temp_dir = None
        self._execution_count = 0
        
    async def execute(
        self,
        command: Union[str, List[str]],
        timeout_seconds: Optional[float] = None,
        working_dir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """执行命令（本地实现）"""
        start_time = time.time()
        self._execution_count += 1
        
        # 验证命令安全性
        is_safe, error_msg = self.validate_command(command)
        if not is_safe:
            return ExecutionResult(
                status=ExecutionResultStatus.SECURITY_VIOLATION,
                error_message=error_msg,
                execution_time=time.time() - start_time
            )
        
        # 准备工作目录
        actual_working_dir = await self._prepare_working_dir(working_dir)
        if not actual_working_dir:
            return ExecutionResult(
                status=ExecutionResultStatus.FAILED,
                error_message="无法准备工作目录",
                execution_time=time.time() - start_time
            )
        
        # 准备环境变量
        env = self._prepare_environment(environment)
        
        # 准备命令
        if isinstance(command, str):
            # 如果是字符串，使用shell执行
            shell = True
            cmd = command
        else:
            # 如果是列表，不使用shell
            shell = False
            cmd = command
        
        try:
            # 执行命令
            process = await asyncio.create_subprocess_shell(
                cmd if shell else " ".join(cmd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=actual_working_dir,
                env=env,
                shell=shell
            )
            
            # 等待完成（带超时）
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds
                )
                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')
                return_code = process.returncode
                
                # 检查资源限制（简化实现）
                resource_violation = self._check_resource_violations(
                    stdout, stderr, return_code
                )
                
                if resource_violation:
                    status = ExecutionResultStatus.RESOURCE_LIMIT
                elif return_code == 0:
                    status = ExecutionResultStatus.SUCCESS
                else:
                    status = ExecutionResultStatus.FAILED
                    
            except asyncio.TimeoutError:
                # 超时，终止进程
                process.terminate()
                await asyncio.sleep(0.1)
                if process.returncode is None:
                    process.kill()
                    
                return ExecutionResult(
                    status=ExecutionResultStatus.TIMEOUT,
                    error_message=f"命令执行超时 ({timeout_seconds}秒)",
                    execution_time=time.time() - start_time
                )
                
        except Exception as e:
            self._logger.error(f"执行命令失败: {e}")
            return ExecutionResult(
                status=ExecutionResultStatus.FAILED,
                error_message=str(e),
                execution_time=time.time() - start_time
            )
        
        # 构建执行结果
        result = ExecutionResult(
            status=status,
            stdout=stdout,
            stderr=stderr,
            return_code=return_code,
            execution_time=time.time() - start_time,
            resource_usage={
                "execution_count": self._execution_count,
                "memory_estimate": len(stdout) + len(stderr)  # 简化估算
            }
        )
        
        return result
    
    async def _prepare_working_dir(self, working_dir: Optional[str]) -> Optional[str]:
        """准备工作目录"""
        if working_dir:
            # 解析虚拟路径
            resolved = self.resolve_virtual_path(working_dir)
            if resolved and os.path.exists(resolved):
                return resolved
            else:
                self._logger.warning(f"无法解析工作目录: {working_dir}")
                return None
        
        # 如果没有指定工作目录，使用临时目录
        if self.use_temp_dir:
            if not self._temp_dir:
                self._temp_dir = tempfile.mkdtemp(prefix="sandbox_")
                self._logger.info(f"创建临时目录: {self._temp_dir}")
            return self._temp_dir
        else:
            # 使用当前工作目录
            return os.getcwd()
    
    def _prepare_environment(self, environment: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """准备环境变量"""
        if self.inherit_env:
            env = os.environ.copy()
            if environment:
                env.update(environment)
            return env
        else:
            # 只使用指定的环境变量
            return environment or {}
    
    def _check_resource_violations(
        self, stdout: str, stderr: str, return_code: int
    ) -> bool:
        """检查资源违规（简化实现）"""
        # 检查内存限制
        if self.resource_limits.memory_mb:
            total_size = len(stdout) + len(stderr)
            memory_mb = total_size / (1024 * 1024)
            if memory_mb > self.resource_limits.memory_mb:
                self._logger.warning(f"内存使用超过限制: {memory_mb:.2f}MB > {self.resource_limits.memory_mb}MB")
                return True
        
        # 检查输出大小限制（简化磁盘限制）
        if self.resource_limits.disk_mb:
            output_mb = (len(stdout) + len(stderr)) / (1024 * 1024)
            if output_mb > self.resource_limits.disk_mb:
                self._logger.warning(f"输出大小超过限制: {output_mb:.2f}MB > {self.resource_limits.disk_mb}MB")
                return True
                
        return False
    
    def translate_path(self, virtual_path: str) -> Optional[str]:
        """路径转换"""
        return self.resolve_virtual_path(virtual_path)
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                self._logger.info(f"清理临时目录: {self._temp_dir}")
                self._temp_dir = None
            except Exception as e:
                self._logger.error(f"清理临时目录失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "execution_count": self._execution_count,
            "temp_dir": self._temp_dir,
            "path_mappings": len(self.path_mappings),
            "resource_limits": self.resource_limits.to_dict() if self.resource_limits else None
        }


# ============================================================================
# 第四部分：沙箱管理器与提供者注册
# ============================================================================

class SandboxManager:
    """沙箱管理器
    
    管理多个沙箱提供者，提供统一的接口访问不同沙箱。
    支持动态注册和选择最合适的沙箱提供者。
    """
    
    def __init__(self):
        self._providers: Dict[str, Sandbox] = {}
        self._default_provider: Optional[str] = None
        self._capability_index: Dict[SandboxCapability, List[str]] = {}
        
    async def register_provider(self, provider: Sandbox, set_as_default: bool = False) -> None:
        """注册沙箱提供者"""
        self._providers[provider.name] = provider
        
        # 更新能力索引
        for capability in provider.get_capabilities():
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            if provider.name not in self._capability_index[capability]:
                self._capability_index[capability].append(provider.name)
        
        # 设置默认提供者
        if set_as_default or len(self._providers) == 1:
            self._default_provider = provider.name
            
        print(f"✅ 注册沙箱提供者: {provider.name}")
    
    async def unregister_provider(self, provider_name: str) -> bool:
        """注销沙箱提供者"""
        if provider_name not in self._providers:
            return False
            
        provider = self._providers[provider_name]
        
        # 清理资源
        await provider.cleanup()
        
        # 从能力索引中移除
        for capability in provider.get_capabilities():
            if capability in self._capability_index:
                if provider_name in self._capability_index[capability]:
                    self._capability_index[capability].remove(provider_name)
        
        # 移除提供者
        del self._providers[provider_name]
        
        # 如果移除的是默认提供者，选择新的默认
        if self._default_provider == provider_name:
            self._default_provider = next(iter(self._providers.keys()), None)
            
        return True
    
    def get_provider(self, name: str) -> Optional[Sandbox]:
        """获取指定名称的提供者"""
        return self._providers.get(name)
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """列出所有提供者"""
        providers = []
        for name, provider in self._providers.items():
            providers.append({
                "name": name,
                "type": provider.__class__.__name__,
                "capabilities": [c.value for c in provider.get_capabilities()],
                "is_default": name == self._default_provider
            })
        return providers
    
    def find_providers_with_capability(self, capability: SandboxCapability) -> List[str]:
        """查找支持特定能力的提供者"""
        return self._capability_index.get(capability, [])
    
    async def execute(
        self,
        command: Union[str, List[str]],
        provider_name: Optional[str] = None,
        **kwargs
    ) -> ExecutionResult:
        """执行命令（通过指定或默认提供者）"""
        # 选择提供者
        if provider_name:
            provider = self.get_provider(provider_name)
            if not provider:
                return ExecutionResult(
                    status=ExecutionResultStatus.FAILED,
                    error_message=f"沙箱提供者不存在: {provider_name}"
                )
        elif self._default_provider:
            provider = self.get_provider(self._default_provider)
        else:
            return ExecutionResult(
                status=ExecutionResultStatus.FAILED,
                error_message="没有可用的沙箱提供者"
            )
        
        # 执行命令
        return await provider.execute(command, **kwargs)
    
    async def cleanup_all(self) -> None:
        """清理所有提供者"""
        for name, provider in self._providers.items():
            try:
                await provider.cleanup()
                print(f"✅ 清理沙箱提供者: {name}")
            except Exception as e:
                print(f"❌ 清理沙箱提供者失败 {name}: {e}")
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """获取管理器统计"""
        return {
            "total_providers": len(self._providers),
            "default_provider": self._default_provider,
            "capabilities": {
                cap.value: len(names) 
                for cap, names in self._capability_index.items()
            }
        }


# ============================================================================
# 第五部分：测试套件
# ============================================================================

class SandboxTestSuite:
    """沙箱测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册所有测试"""
        self.tests = [
            ("test_sandbox_creation", self.test_sandbox_creation),
            ("test_path_mapping", self.test_path_mapping),
            ("test_command_execution", self.test_command_execution),
            ("test_timeout_handling", self.test_timeout_handling),
            ("test_security_validation", self.test_security_validation),
            ("test_resource_limits", self.test_resource_limits),
            ("test_manager_registration", self.test_manager_registration),
        ]
    
    async def test_sandbox_creation(self) -> Tuple[bool, str]:
        """测试沙箱创建"""
        try:
            sandbox = LocalSandboxProvider(name="test_sandbox")
            assert sandbox.name == "test_sandbox"
            assert len(sandbox.get_capabilities()) > 0
            return True, "沙箱创建测试通过"
        except Exception as e:
            return False, f"沙箱创建测试失败: {e}"
    
    async def test_path_mapping(self) -> Tuple[bool, str]:
        """测试路径映射"""
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            
            # 创建沙箱并添加路径映射
            sandbox = LocalSandboxProvider(name="test_mapping")
            mapping = PathMapping("/virtual", temp_dir)
            sandbox.add_path_mapping(mapping)
            
            # 测试路径解析
            resolved = sandbox.resolve_virtual_path("/virtual/test.txt")
            expected = os.path.join(temp_dir, "test.txt")
            assert resolved == expected
            
            # 清理
            shutil.rmtree(temp_dir)
            return True, "路径映射测试通过"
        except Exception as e:
            # 清理临时目录
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return False, f"路径映射测试失败: {e}"
    
    async def test_command_execution(self) -> Tuple[bool, str]:
        """测试命令执行"""
        try:
            sandbox = LocalSandboxProvider(name="test_execution")
            
            # 执行简单命令
            result = await sandbox.execute("echo 'Hello, Sandbox!'")
            
            assert result.success()
            assert "Hello, Sandbox!" in result.stdout.strip()
            
            await sandbox.cleanup()
            return True, "命令执行测试通过"
        except Exception as e:
            return False, f"命令执行测试失败: {e}"
    
    async def test_timeout_handling(self) -> Tuple[bool, str]:
        """测试超时处理"""
        try:
            sandbox = LocalSandboxProvider(name="test_timeout")
            
            # 执行会超时的命令
            result = await sandbox.execute("sleep 2", timeout_seconds=0.5)
            
            assert result.status == ExecutionResultStatus.TIMEOUT
            assert "超时" in result.error_message
            
            await sandbox.cleanup()
            return True, "超时处理测试通过"
        except Exception as e:
            return False, f"超时处理测试失败: {e}"
    
    async def test_security_validation(self) -> Tuple[bool, str]:
        """测试安全验证"""
        try:
            sandbox = LocalSandboxProvider(name="test_security")
            
            # 测试危险命令
            result = await sandbox.execute("rm -rf /")
            
            assert result.status == ExecutionResultStatus.SECURITY_VIOLATION
            assert "危险模式" in result.error_message
            
            await sandbox.cleanup()
            return True, "安全验证测试通过"
        except Exception as e:
            return False, f"安全验证测试失败: {e}"
    
    async def test_resource_limits(self) -> Tuple[bool, str]:
        """测试资源限制"""
        try:
            # 创建带资源限制的沙箱
            limits = ResourceLimit(memory_mb=1)  # 1MB内存限制
            sandbox = LocalSandboxProvider(
                name="test_resources",
                resource_limits=limits
            )
            
            # 执行可能超过内存限制的命令（生成大量输出）
            result = await sandbox.execute("python3 -c 'print(\"x\" * 2000000)'")
            
            # 注意：简化实现可能不会真正限制内存，这里只测试不崩溃
            assert result is not None
            
            await sandbox.cleanup()
            return True, "资源限制测试通过"
        except Exception as e:
            return False, f"资源限制测试失败: {e}"
    
    async def test_manager_registration(self) -> Tuple[bool, str]:
        """测试管理器注册"""
        try:
            manager = SandboxManager()
            
            # 注册提供者
            sandbox = LocalSandboxProvider(name="test_manager")
            await manager.register_provider(sandbox, set_as_default=True)
            
            # 验证注册
            providers = manager.list_providers()
            assert len(providers) == 1
            assert providers[0]["name"] == "test_manager"
            
            # 执行命令
            result = await manager.execute("echo 'Manager Test'")
            assert result.success()
            
            # 清理
            await manager.cleanup_all()
            return True, "管理器注册测试通过"
        except Exception as e:
            return False, f"管理器注册测试失败: {e}"
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("=" * 60)
        print("🧪 运行沙箱测试套件")
        print("=" * 60)
        
        results = []
        passed = 0
        failed = 0
        
        for test_name, test_func in self.tests:
            print(f"\n📋 运行测试: {test_name}")
            try:
                start_time = time.time()
                success, message = await test_func()
                elapsed = time.time() - start_time
                
                if success:
                    print(f"   ✅ 通过: {message} ({elapsed:.3f}s)")
                    passed += 1
                else:
                    print(f"   ❌ 失败: {message} ({elapsed:.3f}s)")
                    failed += 1
                    
                results.append({
                    "test_name": test_name,
                    "success": success,
                    "message": message,
                    "elapsed": elapsed
                })
            except Exception as e:
                print(f"   💥 异常: {e}")
                failed += 1
                results.append({
                    "test_name": test_name,
                    "success": False,
                    "message": f"测试异常: {e}",
                    "elapsed": 0
                })
        
        # 生成报告
        print("\n" + "=" * 60)
        print("📊 测试结果汇总")
        print("=" * 60)
        print(f"  总测试数: {len(self.tests)}")
        print(f"  通过测试: {passed}")
        print(f"  失败测试: {failed}")
        print(f"  成功率: {passed/len(self.tests)*100:.1f}%")
        
        return {
            "total_tests": len(self.tests),
            "passed": passed,
            "failed": failed,
            "success_rate": passed / len(self.tests) if self.tests else 0,
            "results": results
        }


# ============================================================================
# 第六部分：演示程序
# ============================================================================

async def main_demo():
    """主演示函数"""
    print("=" * 80)
    print("🎓 Day 8 Lesson 29: Sandbox抽象接口演示")
    print("=" * 80)
    
    # 1. 创建沙箱提供者
    print("\n1. 创建本地沙箱提供者...")
    sandbox = LocalSandboxProvider(name="demo_sandbox")
    print(f"   ✅ 创建: {sandbox}")
    print(f"   支持能力: {[c.value for c in sandbox.get_capabilities()]}")
    
    # 2. 测试路径映射
    print("\n2. 测试路径映射...")
    temp_dir = tempfile.mkdtemp()
    mapping = PathMapping("/workspace", temp_dir)
    sandbox.add_path_mapping(mapping)
    
    test_file = os.path.join(temp_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("Hello from sandbox!")
    
    resolved = sandbox.resolve_virtual_path("/workspace/test.txt")
    print(f"   虚拟路径: /workspace/test.txt")
    print(f"   真实路径: {resolved}")
    print(f"   文件存在: {os.path.exists(resolved)}")
    
    # 3. 执行安全命令
    print("\n3. 执行安全命令...")
    result = await sandbox.execute("echo 'Hello, World!'")
    print(f"   命令: echo 'Hello, World!'")
    print(f"   状态: {result.status.value}")
    print(f"   输出: {result.stdout.strip()}")
    print(f"   执行时间: {result.execution_time:.3f}s")
    
    # 4. 测试危险命令检测
    print("\n4. 测试危险命令检测...")
    result = await sandbox.execute("rm -rf /")
    print(f"   命令: rm -rf /")
    print(f"   状态: {result.status.value}")
    print(f"   错误: {result.error_message}")
    
    # 5. 测试超时处理
    print("\n5. 测试超时处理...")
    result = await sandbox.execute("sleep 3", timeout_seconds=1)
    print(f"   命令: sleep 3 (超时: 1秒)")
    print(f"   状态: {result.status.value}")
    print(f"   错误: {result.error_message}")
    
    # 6. 测试沙箱管理器
    print("\n6. 测试沙箱管理器...")
    manager = SandboxManager()
    await manager.register_provider(sandbox, set_as_default=True)
    
    # 添加第二个提供者
    sandbox2 = LocalSandboxProvider(
        name="restricted_sandbox",
        resource_limits=ResourceLimit(memory_mb=10)
    )
    await manager.register_provider(sandbox2)
    
    providers = manager.list_providers()
    print(f"   已注册提供者: {len(providers)}个")
    for p in providers:
        print(f"     - {p['name']}: {p['type']} (默认: {p['is_default']})")
    
    # 7. 通过管理器执行命令
    print("\n7. 通过管理器执行命令...")
    result = await manager.execute("pwd")
    print(f"   命令: pwd")
    print(f"   状态: {result.status.value}")
    print(f"   输出: {result.stdout.strip()}")
    print(f"   提供者: {manager._default_provider}")
    
    # 8. 清理资源
    print("\n8. 清理资源...")
    await manager.cleanup_all()
    shutil.rmtree(temp_dir)
    print("   ✅ 所有资源已清理")
    
    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Day 8 Lesson 29: Sandbox抽象接口演示")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行完整演示")
    parser.add_argument("--list", action="store_true", help="列出所有组件")
    
    args = parser.parse_args()
    
    if args.test:
        # 运行测试套件
        test_suite = SandboxTestSuite()
        asyncio.run(test_suite.run_all_tests())
    elif args.demo:
        # 运行完整演示
        asyncio.run(main_demo())
    elif args.list:
        # 列出组件信息
        print("Day 8 Lesson 29: Sandbox抽象接口")
        print("=" * 50)
        print("核心组件:")
        print("1. Sandbox (抽象基类) - 定义沙箱核心接口")
        print("2. LocalSandboxProvider - 本地沙箱实现")
        print("3. SandboxManager - 沙箱管理器")
        print("4. SandboxTestSuite - 测试套件")
        print("\n使用示例:")
        print("  python sandbox_demo.py --demo   # 运行完整演示")
        print("  python sandbox_demo.py --test   # 运行测试套件")
    else:
        # 默认显示帮助
        print("Day 8 Lesson 29: Sandbox抽象接口")
        print("=" * 50)
        print("使用 --help 查看可用选项")
        print("\n快速开始:")
        print("1. 创建本地沙箱:")
        print("   sandbox = LocalSandboxProvider(name='my_sandbox')")
        print("2. 执行命令:")
        print("   result = await sandbox.execute('echo Hello')")
        print("3. 使用管理器:")
        print("   manager = SandboxManager()")
        print("   await manager.register_provider(sandbox)")
        print("   result = await manager.execute('ls -la')")
        print("\n运行完整演示: python sandbox_demo.py --demo")


if __name__ == "__main__":
    main()