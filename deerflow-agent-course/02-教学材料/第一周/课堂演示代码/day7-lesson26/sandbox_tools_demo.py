#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 7 Lesson 26: Sandbox工具集 - 课堂演示代码

本文件演示DeerFlow沙箱工具集的完整实现，采用四部分结构：
第一部分：概念与安全设计原则 - 定义沙箱安全目标和防护策略
第二部分：沙箱提供者实现 - 实现基础沙箱和容器化沙箱
第三部分：工具实现与安全检查 - 实现BashTool和PythonTool及安全检测
第四部分：测试与演示 - 提供完整的测试套件和演示程序

核心功能：
1. 沙箱安全设计：四大防护目标，多层防御策略
2. 沙箱提供者模式：基础沙箱（进程隔离）和容器沙箱（Docker）
3. 安全检查机制：命令注入防护、代码导入白名单、资源限制
4. 工具实现：BashTool（安全执行shell命令）、PythonTool（安全执行Python代码）
5. 异常处理：资源超时、权限拒绝、执行失败的优雅处理

使用场景：
- 代码执行平台：安全执行用户提交的代码
- 插件系统：运行第三方插件，防止恶意操作
- CI/CD系统：安全执行构建脚本和测试代码
- 计算服务：隔离用户计算任务，防止资源滥用

学习目标：
1. 掌握沙箱安全设计原则和防护策略
2. 理解进程隔离和容器化隔离技术
3. 实现命令注入防护和代码安全检查
4. 设计资源限制和异常处理机制
"""

import asyncio
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# ============================================================================
# 第一部分：概念与安全设计原则
# ============================================================================


class SandboxSecurityGoal(Enum):
    """沙箱安全防护目标"""
    PREVENT_SYSTEM_DAMAGE = "防止系统破坏"      # 防止工具破坏宿主系统
    PREVENT_DATA_LEAKAGE = "防止数据泄露"       # 防止敏感数据泄露
    PREVENT_RESOURCE_ABUSE = "防止资源滥用"     # 防止CPU/内存/磁盘滥用
    PREVENT_MALICIOUS_CODE = "防止恶意代码"     # 防止执行恶意代码


class SandboxIsolationLevel(Enum):
    """沙箱隔离级别"""
    PROCESS = "进程隔离"        # 子进程隔离，使用资源限制
    CONTAINER = "容器隔离"      # Docker容器隔离，更高安全性
    VM = "虚拟机隔离"          # 虚拟机隔离，最高安全性但性能差


class ResourceLimit(Enum):
    """资源限制类型"""
    CPU_TIME = "CPU时间限制"    # 最大CPU时间（秒）
    MEMORY = "内存限制"         # 最大内存使用（MB）
    DISK = "磁盘限制"          # 最大磁盘使用（MB）
    PROCESSES = "进程数限制"    # 最大子进程数
    NETWORK = "网络限制"       # 网络访问限制
    FILE_SIZE = "文件大小限制"  # 最大文件大小（MB）


@dataclass
class SecurityPolicy:
    """安全策略配置"""
    isolation_level: SandboxIsolationLevel = SandboxIsolationLevel.PROCESS
    allowed_commands: List[str] = field(default_factory=list)      # 允许的命令列表
    allowed_modules: List[str] = field(default_factory=list)       # 允许的Python模块
    max_cpu_seconds: int = 30                                     # 最大CPU时间
    max_memory_mb: int = 256                                      # 最大内存（MB）
    max_disk_mb: int = 100                                        # 最大磁盘使用（MB）
    max_processes: int = 10                                       # 最大子进程数
    network_access: bool = False                                  # 是否允许网络访问
    read_only_fs: bool = True                                     # 是否只读文件系统
    allowed_paths: List[str] = field(default_factory=list)        # 允许访问的路径
    
    def is_command_allowed(self, command: str) -> bool:
        """检查命令是否允许"""
        if not self.allowed_commands:
            return True
        return command in self.allowed_commands
    
    def is_module_allowed(self, module: str) -> bool:
        """检查模块是否允许"""
        if not self.allowed_modules:
            return True
        return module in self.allowed_modules


@dataclass 
class SandboxResult:
    """沙箱执行结果"""
    success: bool                     # 是否成功执行
    output: str                       # 标准输出
    error: str                        # 标准错误
    exit_code: int                    # 退出代码
    execution_time: float             # 执行时间（秒）
    resource_usage: Dict[str, Any]   # 资源使用情况
    security_violations: List[str]    # 安全违规记录


# ============================================================================
# 第二部分：沙箱提供者实现
# ============================================================================


class SandboxProvider(ABC):
    """沙箱提供者抽象基类"""
    
    @abstractmethod
    async def execute(self, command: List[str], 
                     stdin: Optional[str] = None,
                     timeout: Optional[int] = None) -> SandboxResult:
        """在沙箱中执行命令"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """清理沙箱资源"""
        pass
    
    @abstractmethod
    def get_resource_usage(self) -> Dict[str, Any]:
        """获取资源使用情况"""
        pass


class ProcessSandboxProvider(SandboxProvider):
    """进程沙箱提供者（基于subprocess和资源限制）"""
    
    def __init__(self, security_policy: SecurityPolicy, workdir: Optional[str] = None):
        self.security_policy = security_policy
        self.workdir = workdir or tempfile.mkdtemp(prefix="sandbox_")
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[float] = None
        self.resource_usage: Dict[str, Any] = {}
        
        # 创建工作目录
        os.makedirs(self.workdir, exist_ok=True)
        
    async def execute(self, command: List[str], 
                     stdin: Optional[str] = None,
                     timeout: Optional[int] = None) -> SandboxResult:
        """在沙箱进程中执行命令"""
        self.start_time = time.time()
        
        # 安全检查：命令注入防护
        if not self._validate_command(command):
            return SandboxResult(
                success=False,
                output="",
                error="命令安全检查失败",
                exit_code=-1,
                execution_time=0,
                resource_usage={},
                security_violations=["命令包含潜在危险字符"]
            )
        
        try:
            # 构建执行环境
            env = self._create_environment()
            
            # 执行命令
            self.process = subprocess.Popen(
                command,
                cwd=self.workdir,
                env=env,
                stdin=subprocess.PIPE if stdin else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=self._set_resource_limits
            )
            
            # 通信
            stdout, stderr = self.process.communicate(
                input=stdin,
                timeout=timeout or self.security_policy.max_cpu_seconds
            )
            
            execution_time = time.time() - self.start_time
            
            # 收集资源使用
            self.resource_usage = self._collect_resource_usage(execution_time)
            
            return SandboxResult(
                success=self.process.returncode == 0,
                output=stdout,
                error=stderr,
                exit_code=self.process.returncode,
                execution_time=execution_time,
                resource_usage=self.resource_usage,
                security_violations=[]
            )
            
        except subprocess.TimeoutExpired:
            # 超时处理
            if self.process:
                self.process.kill()
                stdout, stderr = self.process.communicate()
            
            execution_time = time.time() - self.start_time
            
            return SandboxResult(
                success=False,
                output="",
                error="执行超时",
                exit_code=-2,
                execution_time=execution_time,
                resource_usage=self.resource_usage,
                security_violations=["执行超时"]
            )
            
        except Exception as e:
            execution_time = time.time() - self.start_time
            
            return SandboxResult(
                success=False,
                output="",
                error=f"执行异常: {e}",
                exit_code=-3,
                execution_time=execution_time,
                resource_usage={},
                security_violations=[f"执行异常: {e}"]
            )
    
    def _validate_command(self, command: List[str]) -> bool:
        """验证命令安全性"""
        dangerous_patterns = [
            r'&', r'\|', r';', r'`', r'\$\(', r'\{', r'\}',
            r'>>', r'>', r'<', r'2>&1', r'exec', r'sudo'
        ]
        
        for cmd_part in command:
            for pattern in dangerous_patterns:
                if re.search(pattern, cmd_part):
                    return False
        
        return True
    
    def _set_resource_limits(self):
        """设置资源限制（在子进程中调用）"""
        import resource
        
        # CPU时间限制
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (self.security_policy.max_cpu_seconds, 
             self.security_policy.max_cpu_seconds)
        )
        
        # 内存限制
        memory_limit = self.security_policy.max_memory_mb * 1024 * 1024
        resource.setrlimit(
            resource.RLIMIT_AS,
            (memory_limit, memory_limit)
        )
        
        # 进程数限制
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (self.security_policy.max_processes, 
             self.security_policy.max_processes)
        )
        
        # 文件大小限制
        file_size_limit = self.security_policy.max_disk_mb * 1024 * 1024
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (file_size_limit, file_size_limit)
        )
    
    def _create_environment(self) -> Dict[str, str]:
        """创建安全的执行环境"""
        env = os.environ.copy()
        
        # 限制环境变量
        allowed_env_vars = [
            'PATH', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR', 'TEMP', 'TMP'
        ]
        
        # 创建最小化环境
        new_env = {}
        for var in allowed_env_vars:
            if var in env:
                new_env[var] = env[var]
        
        # 添加安全路径
        new_env['PATH'] = '/usr/local/bin:/usr/bin:/bin'
        
        return new_env
    
    def _collect_resource_usage(self, execution_time: float) -> Dict[str, Any]:
        """收集资源使用情况"""
        import psutil
        
        if not self.process:
            return {}
        
        try:
            process = psutil.Process(self.process.pid)
            memory_info = process.memory_info()
            
            return {
                'cpu_time': execution_time,
                'memory_used_mb': memory_info.rss / 1024 / 1024,
                'cpu_percent': process.cpu_percent(),
                'num_threads': process.num_threads(),
                'num_fds': process.num_fds()
            }
        except:
            return {}
    
    async def cleanup(self):
        """清理沙箱资源"""
        if self.process and self.process.poll() is None:
            self.process.kill()
            self.process.wait()
        
        # 清理工作目录
        import shutil
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir, ignore_errors=True)
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """获取资源使用情况"""
        return self.resource_usage.copy()


class DockerSandboxProvider(SandboxProvider):
    """Docker容器沙箱提供者（更高安全性）"""
    
    def __init__(self, security_policy: SecurityPolicy, 
                 image: str = "python:3.12-slim"):
        self.security_policy = security_policy
        self.image = image
        self.container_id: Optional[str] = None
        self.resource_usage: Dict[str, Any] = {}
        
    async def execute(self, command: List[str], 
                     stdin: Optional[str] = None,
                     timeout: Optional[int] = None) -> SandboxResult:
        """在Docker容器中执行命令"""
        self.start_time = time.time()
        
        # 生成容器名称
        container_name = f"sandbox_{uuid.uuid4().hex[:8]}"
        
        try:
            # 构建Docker命令
            docker_cmd = [
                'docker', 'run',
                '--rm',
                '--name', container_name,
                '--network', 'none' if not self.security_policy.network_access else 'bridge',
                '--memory', f'{self.security_policy.max_memory_mb}m',
                '--cpus', '1.0',
                '--read-only' if self.security_policy.read_only_fs else '',
                '-v', f'{self.security_policy.allowed_paths[0] if self.security_policy.allowed_paths else "/tmp"}:/data:ro'
            ]
            
            # 移除空参数
            docker_cmd = [c for c in docker_cmd if c]
            
            # 添加镜像和命令
            docker_cmd.extend([self.image] + command)
            
            # 执行Docker命令
            result = subprocess.run(
                docker_cmd,
                input=stdin,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout or self.security_policy.max_cpu_seconds
            )
            
            execution_time = time.time() - self.start_time
            
            self.container_id = container_name
            
            return SandboxResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                exit_code=result.returncode,
                execution_time=execution_time,
                resource_usage=self._collect_docker_stats(container_name),
                security_violations=[]
            )
            
        except subprocess.TimeoutExpired:
            # 超时处理
            subprocess.run(['docker', 'kill', container_name], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            execution_time = time.time() - self.start_time
            
            return SandboxResult(
                success=False,
                output="",
                error="Docker执行超时",
                exit_code=-2,
                execution_time=execution_time,
                resource_usage={},
                security_violations=["执行超时"]
            )
            
        except Exception as e:
            execution_time = time.time() - self.start_time
            
            return SandboxResult(
                success=False,
                output="",
                error=f"Docker执行异常: {e}",
                exit_code=-3,
                execution_time=execution_time,
                resource_usage={},
                security_violations=[f"执行异常: {e}"]
            )
    
    def _collect_docker_stats(self, container_name: str) -> Dict[str, Any]:
        """收集Docker容器统计信息"""
        try:
            result = subprocess.run(
                ['docker', 'stats', container_name, '--no-stream', '--format', '{{.MemUsage}},{{.CPUPerc}}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )
            
            if result.returncode == 0:
                mem_usage, cpu_percent = result.stdout.strip().split(',')
                return {
                    'memory_usage': mem_usage,
                    'cpu_percent': cpu_percent
                }
        except:
            pass
        
        return {}
    
    async def cleanup(self):
        """清理Docker容器"""
        if self.container_id:
            subprocess.run(['docker', 'kill', self.container_id], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """获取资源使用情况"""
        return self.resource_usage.copy()


# ============================================================================
# 第三部分：工具实现与安全检查
# ============================================================================


class BaseSandboxTool(ABC):
    """沙箱工具基类"""
    
    def __init__(self, security_policy: SecurityPolicy):
        self.security_policy = security_policy
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sandbox_provider: Optional[SandboxProvider] = None
        
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具"""
        pass
    
    @abstractmethod
    def validate_parameters(self, **kwargs) -> Tuple[bool, List[str]]:
        """验证参数"""
        pass
    
    def _create_sandbox_provider(self) -> SandboxProvider:
        """创建沙箱提供者"""
        if self.security_policy.isolation_level == SandboxIsolationLevel.PROCESS:
            return ProcessSandboxProvider(self.security_policy)
        elif self.security_policy.isolation_level == SandboxIsolationLevel.CONTAINER:
            return DockerSandboxProvider(self.security_policy)
        else:
            raise ValueError(f"不支持的隔离级别: {self.security_policy.isolation_level}")
    
    async def _execute_in_sandbox(self, command: List[str], 
                                stdin: Optional[str] = None) -> SandboxResult:
        """在沙箱中执行命令"""
        if not self.sandbox_provider:
            self.sandbox_provider = self._create_sandbox_provider()
        
        try:
            result = await self.sandbox_provider.execute(command, stdin)
            return result
        finally:
            if self.sandbox_provider:
                await self.sandbox_provider.cleanup()
                self.sandbox_provider = None


class BashTool(BaseSandboxTool):
    """Bash命令执行工具"""
    
    def __init__(self, security_policy: Optional[SecurityPolicy] = None):
        if security_policy is None:
            security_policy = SecurityPolicy(
                allowed_commands=['ls', 'cat', 'grep', 'echo', 'pwd', 'wc'],
                max_cpu_seconds=10,
                max_memory_mb=128,
                max_processes=5
            )
        super().__init__(security_policy)
    
    async def execute(self, command: str, 
                     args: Optional[List[str]] = None,
                     stdin: Optional[str] = None) -> Dict[str, Any]:
        """执行Bash命令"""
        # 参数验证
        is_valid, errors = self.validate_parameters(command=command, args=args)
        if not is_valid:
            raise ValueError(f"参数验证失败: {', '.join(errors)}")
        
        # 构建命令
        cmd_list = [command]
        if args:
            cmd_list.extend(args)
        
        self.logger.info(f"执行Bash命令: {cmd_list}")
        
        # 在沙箱中执行
        result = await self._execute_in_sandbox(cmd_list, stdin)
        
        return {
            'success': result.success,
            'output': result.output,
            'error': result.error,
            'exit_code': result.exit_code,
            'execution_time': result.execution_time,
            'resource_usage': result.resource_usage,
            'security_violations': result.security_violations
        }
    
    def validate_parameters(self, **kwargs) -> Tuple[bool, List[str]]:
        """验证参数"""
        errors = []
        
        command = kwargs.get('command')
        if not command:
            errors.append("命令不能为空")
        
        if command and not self.security_policy.is_command_allowed(command):
            errors.append(f"命令 '{command}' 不在允许列表中")
        
        args = kwargs.get('args', [])
        if args and not isinstance(args, list):
            errors.append("参数必须是列表")
        
        return len(errors) == 0, errors


class PythonTool(BaseSandboxTool):
    """Python代码执行工具"""
    
    def __init__(self, security_policy: Optional[SecurityPolicy] = None):
        if security_policy is None:
            security_policy = SecurityPolicy(
                allowed_modules=['math', 'datetime', 'json', 're', 'random'],
                max_cpu_seconds=30,
                max_memory_mb=256,
                max_processes=1
            )
        super().__init__(security_policy)
        
        # 编译正则表达式用于导入检查
        self.import_pattern = re.compile(
            r'^\s*(?:import\s+(\w+(?:\s*,\s*\w+)*)|from\s+(\w+)\s+import)',
            re.MULTILINE
        )
    
    async def execute(self, code: str, 
                     globals_dict: Optional[Dict[str, Any]] = None,
                     locals_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行Python代码"""
        # 安全检查
        is_safe, violations = self._check_code_safety(code)
        if not is_safe:
            return {
                'success': False,
                'output': '',
                'error': f"代码安全检查失败: {', '.join(violations)}",
                'execution_time': 0,
                'security_violations': violations
            }
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # 在沙箱中执行Python代码
            command = ['python', temp_file]
            result = await self._execute_in_sandbox(command)
            
            # 清理临时文件
            os.unlink(temp_file)
            
            return {
                'success': result.success,
                'output': result.output,
                'error': result.error,
                'exit_code': result.exit_code,
                'execution_time': result.execution_time,
                'resource_usage': result.resource_usage,
                'security_violations': result.security_violations
            }
            
        except Exception as e:
            # 确保清理临时文件
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            
            raise
    
    def _check_code_safety(self, code: str) -> Tuple[bool, List[str]]:
        """检查代码安全性"""
        violations = []
        
        # 1. 检查导入
        import_violations = self._check_imports(code)
        violations.extend(import_violations)
        
        # 2. 检查危险函数
        dangerous_functions = ['exec', 'eval', '__import__', 'compile', 'open']
        for func in dangerous_functions:
            if func in code:
                violations.append(f"代码包含危险函数: {func}")
        
        # 3. 检查系统调用
        system_patterns = [
            r'os\.system', r'subprocess\.', r'__builtins__',
            r'\.__globals__', r'\.__code__', r'\.__dict__'
        ]
        for pattern in system_patterns:
            if re.search(pattern, code):
                violations.append(f"代码包含系统调用: {pattern}")
        
        return len(violations) == 0, violations
    
    def _check_imports(self, code: str) -> List[str]:
        """检查导入语句"""
        violations = []
        
        # 查找所有导入语句
        matches = self.import_pattern.findall(code)
        
        for match in matches:
            import_modules = match[0]  # import module1, module2
            from_module = match[1]     # from module import ...
            
            if import_modules:
                # 处理多个模块导入：import a, b, c
                modules = [m.strip() for m in import_modules.split(',')]
                for module in modules:
                    if not self.security_policy.is_module_allowed(module):
                        violations.append(f"不允许导入模块: {module}")
            
            if from_module:
                if not self.security_policy.is_module_allowed(from_module):
                    violations.append(f"不允许从模块导入: {from_module}")
        
        return violations
    
    def validate_parameters(self, **kwargs) -> Tuple[bool, List[str]]:
        """验证参数"""
        errors = []
        
        code = kwargs.get('code')
        if not code:
            errors.append("代码不能为空")
        
        if code and len(code) > 10000:
            errors.append("代码长度不能超过10000字符")
        
        return len(errors) == 0, errors


# ============================================================================
# 第四部分：测试与演示
# ============================================================================


class SandboxToolsTestSuite:
    """沙箱工具测试套件"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def test_bash_tool_basic(self) -> bool:
        """测试BashTool基本功能"""
        try:
            tool = BashTool()
            result = await tool.execute(command='echo', args=['Hello, Sandbox!'])
            
            success = (
                result['success'] and 
                'Hello, Sandbox!' in result['output']
            )
            
            self.logger.info(f"BashTool基本功能测试: {'通过' if success else '失败'}")
            return success
            
        except Exception as e:
            self.logger.error(f"BashTool基本功能测试异常: {e}")
            return False
    
    async def test_bash_tool_security(self) -> bool:
        """测试BashTool安全性"""
        try:
            # 尝试执行不允许的命令
            security_policy = SecurityPolicy(
                allowed_commands=['echo'],  # 只允许echo
                max_cpu_seconds=5
            )
            tool = BashTool(security_policy)
            
            # 应该因为命令不允许而失败
            result = await tool.execute(command='ls', args=['/'])
            
            # 应该失败或者被阻止
            success = not result['success'] or len(result['security_violations']) > 0
            
            self.logger.info(f"BashTool安全性测试: {'通过' if success else '失败'}")
            return success
            
        except Exception as e:
            self.logger.error(f"BashTool安全性测试异常: {e}")
            return False
    
    async def test_python_tool_basic(self) -> bool:
        """测试PythonTool基本功能"""
        try:
            tool = PythonTool()
            code = """
import math
result = math.sqrt(16)
print(f"平方根: {result}")
"""
            result = await tool.execute(code=code)
            
            success = (
                result['success'] and 
                '平方根: 4.0' in result['output']
            )
            
            self.logger.info(f"PythonTool基本功能测试: {'通过' if success else '失败'}")
            return success
            
        except Exception as e:
            self.logger.error(f"PythonTool基本功能测试异常: {e}")
            return False
    
    async def test_python_tool_security(self) -> bool:
        """测试PythonTool安全性"""
        try:
            tool = PythonTool()
            
            # 尝试导入不允许的模块
            code = """
import os
print(os.listdir('/'))
"""
            result = await tool.execute(code=code)
            
            # 应该因为安全检查而失败
            success = (
                not result['success'] and 
                any('不允许导入模块' in msg for msg in result.get('security_violations', []))
            )
            
            self.logger.info(f"PythonTool安全性测试: {'通过' if success else '失败'}")
            return success
            
        except Exception as e:
            self.logger.error(f"PythonTool安全性测试异常: {e}")
            return False
    
    async def test_resource_limits(self) -> bool:
        """测试资源限制"""
        try:
            security_policy = SecurityPolicy(
                max_cpu_seconds=1,  # 1秒超时
                max_memory_mb=10    # 10MB内存限制
            )
            tool = BashTool(security_policy)
            
            # 执行一个会超时的命令
            result = await tool.execute(command='sleep', args=['2'])
            
            # 应该因为超时而失败
            success = (
                not result['success'] and 
                ('超时' in result['error'] or result['exit_code'] == -2)
            )
            
            self.logger.info(f"资源限制测试: {'通过' if success else '失败'}")
            return success
            
        except Exception as e:
            self.logger.error(f"资源限制测试异常: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        tests = [
            ('bash_tool_basic', self.test_bash_tool_basic),
            ('bash_tool_security', self.test_bash_tool_security),
            ('python_tool_basic', self.test_python_tool_basic),
            ('python_tool_security', self.test_python_tool_security),
            ('resource_limits', self.test_resource_limits)
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                start_time = time.time()
                passed = await test_func()
                execution_time = time.time() - start_time
                
                results[test_name] = {
                    'passed': passed,
                    'execution_time': execution_time
                }
                
                self.logger.info(f"测试 {test_name}: {'通过' if passed else '失败'} ({execution_time:.2f}s)")
                
            except Exception as e:
                self.logger.error(f"测试 {test_name} 异常: {e}")
                results[test_name] = {
                    'passed': False,
                    'execution_time': 0,
                    'error': str(e)
                }
        
        # 统计结果
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r['passed'])
        failed_tests = total_tests - passed_tests
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        return {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': success_rate
            },
            'detailed_results': results
        }


async def main_demo():
    """主演示函数"""
    print("=" * 80)
    print("🎓 Day 7 Lesson 26: Sandbox工具集演示")
    print("=" * 80)
    
    print("\n1. 创建BashTool实例并执行安全命令...")
    bash_tool = BashTool()
    result = await bash_tool.execute(command='echo', args=['Hello from sandbox!'])
    print(f"   命令: echo Hello from sandbox!")
    print(f"   结果: {result['output'].strip()}")
    print(f"   成功: {result['success']}")
    print(f"   执行时间: {result['execution_time']:.2f}s")
    
    print("\n2. 创建PythonTool实例并执行安全代码...")
    python_tool = PythonTool()
    code = """
import math
import json

# 计算圆周率近似值
pi_approx = math.pi
print(f"圆周率近似值: {pi_approx:.10f}")

# 创建JSON数据
data = {"name": "Sandbox", "value": 42}
json_str = json.dumps(data, indent=2)
print(f"JSON数据:\\n{json_str}")
"""
    result = await python_tool.execute(code=code)
    print(f"   代码执行成功: {result['success']}")
    print(f"   输出:\\n{result['output']}")
    
    print("\n3. 测试安全限制（尝试导入不允许的模块）...")
    security_policy = SecurityPolicy(
        allowed_modules=['math'],  # 只允许math模块
        max_cpu_seconds=5
    )
    restricted_tool = PythonTool(security_policy)
    
    dangerous_code = """
import os
print("这行不应该执行")
"""
    result = await restricted_tool.execute(code=dangerous_code)
    print(f"   安全检查结果: {'阻止' if not result['success'] else '允许'}")
    if result.get('security_violations'):
        print(f"   安全违规: {result['security_violations']}")
    
    print("\n4. 运行测试套件验证功能...")
    test_suite = SandboxToolsTestSuite()
    test_report = await test_suite.run_all_tests()
    
    summary = test_report['summary']
    print(f"   测试总数: {summary['total_tests']}")
    print(f"   通过测试: {summary['passed_tests']}")
    print(f"   失败测试: {summary['failed_tests']}")
    print(f"   成功率: {summary['success_rate']:.1%}")
    
    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            # 运行测试套件
            async def run_tests():
                test_suite = SandboxToolsTestSuite()
                report = await test_suite.run_all_tests()
                
                print("测试报告:")
                for test_name, test_result in report['detailed_results'].items():
                    status = "✅ 通过" if test_result['passed'] else "❌ 失败"
                    print(f"  {status} {test_name} ({test_result['execution_time']:.2f}s)")
                
                summary = report['summary']
                print(f"\n总计: {summary['total_tests']} 个测试")
                print(f"通过: {summary['passed_tests']}")
                print(f"失败: {summary['failed_tests']}")
                print(f"成功率: {summary['success_rate']:.1%}")
            
            asyncio.run(run_tests())
            
        elif sys.argv[1] == "--demo":
            # 运行完整演示
            asyncio.run(main_demo())
            
        elif sys.argv[1] == "--help":
            print("用法:")
            print("  python sandbox_tools_demo.py          # 运行默认演示")
            print("  python sandbox_tools_demo.py --test   # 运行测试套件")
            print("  python sandbox_tools_demo.py --demo   # 运行完整演示")
            print("  python sandbox_tools_demo.py --help   # 显示此帮助")
    else:
        # 默认运行完整演示
        asyncio.run(main_demo())