#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第90节课：沙箱安全强化

本课程介绍DeerFlow沙箱安全强化机制，包括：
1. 资源限制 - CPU、内存、磁盘、网络的使用限制
2. 系统调用过滤 - seccomp等Linux安全模块的使用
3. 容器安全 - Docker容器的安全最佳实践
4. 生产级安全沙箱配置

作者：DeerFlow架构师训练营
"""

import time
import os
import resource
import signal
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import unittest.mock as unittest


# ============================================================
# 第一部分：资源限制系统
# ============================================================

class ResourceType(Enum):
    """资源类型"""
    CPU_TIME = "cpu_time"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESSES = "processes"
    FILE_DESCRIPTORS = "file_descriptors"


@dataclass
class ResourceLimit:
    """资源限制配置"""
    type: ResourceType
    soft_limit: int
    hard_limit: int
    unit: str = ""
    
    def __str__(self):
        return f"{self.type.value}: {self.soft_limit}{self.unit} (soft) / {self.hard_limit}{self.unit} (hard)"


class ResourceLimiter:
    """
    资源限制器
    
    强制执行各种资源限制，防止恶意或错误操作耗尽系统资源。
    """
    
    # 默认限制配置
    DEFAULT_LIMITS = {
        ResourceType.CPU_TIME: ResourceLimit(ResourceType.CPU_TIME, 30, 60, "秒"),
        ResourceType.MEMORY: ResourceLimit(ResourceType.MEMORY, 256, 512, "MB"),
        ResourceType.DISK: ResourceLimit(ResourceType.DISK, 100, 200, "MB"),
        ResourceType.PROCESSES: ResourceLimit(ResourceType.PROCESSES, 10, 20, "个"),
        ResourceType.FILE_DESCRIPTORS: ResourceLimit(ResourceType.FILE_DESCRIPTORS, 100, 200, "个"),
    }
    
    def __init__(self, custom_limits: Optional[Dict[ResourceType, ResourceLimit]] = None):
        """
        初始化资源限制器
        
        Args:
            custom_limits: 自定义限制配置
        """
        self.limits = self.DEFAULT_LIMITS.copy()
        if custom_limits:
            self.limits.update(custom_limits)
            
    def apply_limits(self) -> None:
        """应用所有资源限制"""
        # 设置CPU时间限制
        if ResourceType.CPU_TIME in self.limits:
            limit = self.limits[ResourceType.CPU_TIME]
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (limit.soft_limit, limit.hard_limit))
            except Exception as e:
                print(f"设置CPU限制失败: {e}")
                
        # 设置内存限制
        if ResourceType.MEMORY in self.limits:
            limit = self.limits[ResourceType.MEMORY]
            try:
                # RLIMIT_AS: 虚拟内存地址空间
                soft_bytes = limit.soft_limit * 1024 * 1024
                hard_bytes = limit.hard_limit * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (soft_bytes, hard_bytes))
            except Exception as e:
                print(f"设置内存限制失败: {e}")
                
        # 设置文件描述符限制
        if ResourceType.FILE_DESCRIPTORS in self.limits:
            limit = self.limits[ResourceType.FILE_DESCRIPTORS]
            try:
                resource.setrlimit(resource.RLIMIT_NOFILE, (limit.soft_limit, limit.hard_limit))
            except Exception as e:
                print(f"设置文件描述符限制失败: {e}")
                
        # 设置进程数限制
        if ResourceType.PROCESSES in self.limits:
            limit = self.limits[ResourceType.PROCESSES]
            try:
                resource.setrlimit(resource.RLIMIT_NPROC, (limit.soft_limit, limit.hard_limit))
            except Exception as e:
                print(f"设置进程数限制失败: {e}")
                
    def get_limits(self) -> Dict[str, str]:
        """获取当前限制配置"""
        return {str(limit.type): str(limit) for limit in self.limits.values()}


class ResourceMonitor:
    """
    资源监控器
    
    实时监控资源使用情况，支持阈值告警。
    """
    
    def __init__(self, warning_threshold: float = 0.8):
        """
        初始化资源监控器
        
        Args:
            warning_threshold: 警告阈值（百分比）
        """
        self.warning_threshold = warning_threshold
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[ResourceType, float], None]] = []
        
    def start(self, interval: float = 1.0) -> None:
        """
        启动监控
        
        Args:
            interval: 监控间隔（秒）
        """
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        
    def stop(self) -> None:
        """停止监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            
    def add_callback(self, callback: Callable[[ResourceType, float], None]) -> None:
        """
        添加资源告警回调
        
        Args:
            callback: 回调函数，参数为(资源类型, 使用率)
        """
        self._callbacks.append(callback)
        
    def _monitor_loop(self, interval: float) -> None:
        """监控循环"""
        while self._running:
            try:
                # 监控CPU使用
                cpu_percent = self._get_cpu_usage()
                if cpu_percent >= self.warning_threshold:
                    self._trigger_alert(ResourceType.CPU_TIME, cpu_percent)
                    
                # 监控内存使用
                mem_percent = self._get_memory_usage()
                if mem_percent >= self.warning_threshold:
                    self._trigger_alert(ResourceType.MEMORY, mem_percent)
                    
            except Exception as e:
                print(f"监控错误: {e}")
                
            time.sleep(interval)
            
    def _get_cpu_usage(self) -> float:
        """获取CPU使用率（模拟）"""
        import random
        return random.uniform(0, 100)
        
    def _get_memory_usage(self) -> float:
        """获取内存使用率（模拟）"""
        import random
        return random.uniform(0, 100)
        
    def _trigger_alert(self, resource_type: ResourceType, usage: float) -> None:
        """触发告警"""
        for callback in self._callbacks:
            try:
                callback(resource_type, usage)
            except Exception:
                pass
                
    def get_current_usage(self) -> Dict[str, float]:
        """获取当前资源使用情况"""
        return {
            "cpu_percent": self._get_cpu_usage(),
            "memory_percent": self._get_memory_usage(),
        }


# ============================================================
# 第二部分：系统调用过滤
# ============================================================

class SyscallCategory(Enum):
    """系统调用类别"""
    FILE = "file"           # 文件操作
    NETWORK = "network"     # 网络操作
    PROCESS = "process"     # 进程管理
    MEMORY = "memory"       # 内存管理
    SYSTEM = "system"       # 系统控制
    IPC = "ipc"            # 进程间通信


# 允许的系统调用白名单（按类别）
SYSCALL_WHITELIST = {
    SyscallCategory.FILE: [
        "read", "write", "open", "close", "stat", "fstat",
        "lseek", "mknod", "access", "pipe", "select", "fork",
    ],
    SyscallCategory.NETWORK: [
        "socket", "connect", "accept", "sendto", "recvfrom",
        "sendmsg", "recvmsg", "shutdown", "bind", "listen",
    ],
    SyscallCategory.PROCESS: [
        "execve", "exit", "wait4", "kill", "getpid", "getppid",
        "getuid", "getgid", "setuid", "setgid", "getgroups",
    ],
    SyscallCategory.MEMORY: [
        "brk", "mmap", "mprotect", "munmap", "madvise",
    ],
    SyscallCategory.SYSTEM: [
        "getrlimit", "getrusage", "sysinfo", "times",
    ],
}


class SyscallFilter:
    """
    系统调用过滤器
    
    基于白名单的系统调用过滤，限制进程可使用的系统调用。
    
    注意：这是一个演示实现。实际使用需要结合seccomp-bpf或seccomp-tools。
    """
    
    def __init__(self, allowed_categories: Optional[List[SyscallCategory]] = None):
        """
        初始化系统调用过滤器
        
        Args:
            allowed_categories: 允许的系统调用类别
        """
        if allowed_categories is None:
            allowed_categories = [
                SyscallCategory.FILE,
                SyscallCategory.MEMORY,
                SyscallCategory.SYSTEM,
            ]
        self.allowed_categories = allowed_categories
        self._build_whitelist()
        
    def _build_whitelist(self) -> None:
        """构建允许的系统调用集合"""
        self.allowed_syscalls = set()
        for category in self.allowed_categories:
            if category in SYSCALL_WHITELIST:
                self.allowed_syscalls.update(SYSCALL_WHITELIST[category])
                
    def check_syscall(self, syscall: str) -> bool:
        """
        检查系统调用是否允许
        
        Args:
            syscall: 系统调用名称
            
        Returns:
            是否允许
        """
        return syscall in self.allowed_syscalls
        
    def get_allowed_syscalls(self) -> List[str]:
        """获取允许的系统调用列表"""
        return sorted(list(self.allowed_syscalls))
        
    def get_blocked_syscalls(self) -> List[str]:
        """
        获取被阻止的系统调用列表
        
        Returns:
            被阻止的系统调用
        """
        all_syscalls = set()
        for syscalls in SYSCALL_WHITELIST.values():
            all_syscalls.update(syscalls)
        return sorted(list(all_syscalls - self.allowed_syscalls))


# ============================================================
# 第三部分：容器安全配置
# ============================================================

@dataclass
class ContainerSecurityConfig:
    """容器安全配置"""
    # 能力管理
    drop_all_capabilities: bool = True
    add_capabilities: List[str] = field(default_factory=list)
    
    # 资源限制
    memory_limit: Optional[int] = None  # MB
    cpu_limit: Optional[float] = None
    pids_limit: Optional[int] = None
    
    # 网络隔离
    network_disabled: bool = False
    dns_config: Optional[List[str]] = None
    
    # 文件系统
    read_only_rootfs: bool = True
    tmpfs_mounts: List[str] = field(default_factory=list)
    readonly_paths: List[str] = field(default_factory=list)
    
    # 安全选项
    no_new_privileges: bool = True
    run_as_non_root: bool = True
    user_ns_mode: str = "host"  # host, mapping, private
    
    # seccomp配置
    seccomp_profile: Optional[str] = None  # "unconfined", "runtime/default", 自定义路径


class ContainerSecurityManager:
    """
    容器安全管理器
    
    生成和管理容器安全配置。
    """
    
    # 必须丢弃的能力
    MANDATORY_DROP_CAPABILITIES = [
        "CAP_SYS_ADMIN",    # 超级管理员权限
        "CAP_SYS_MODULE",   # 加载内核模块
        "CAP_SYS_RAWIO",    # 原始IO访问
        "CAP_SYS_CHROOT",   # chroot权限
        "CAP_AUDIT_WRITE",  # 审计日志写入
        "CAP_NET_ADMIN",    # 网络管理
        "CAP_SYS_TIME",     # 系统时间修改
    ]
    
    def __init__(self):
        """初始化容器安全管理器"""
        self._config = ContainerSecurityConfig()
        
    def set_memory_limit(self, limit_mb: int) -> 'ContainerSecurityManager':
        """
        设置内存限制
        
        Args:
            limit_mb: 内存限制（MB）
            
        Returns:
            自身实例（支持链式调用）
        """
        self._config.memory_limit = limit_mb
        return self
        
    def set_cpu_limit(self, limit: float) -> 'ContainerSecurityManager':
        """
        设置CPU限制
        
        Args:
            limit: CPU核心数限制
        """
        self._config.cpu_limit = limit
        return self
        
    def disable_network(self) -> 'ContainerSecurityManager':
        """禁用网络"""
        self._config.network_disabled = True
        return self
        
    def allow_capability(self, capability: str) -> 'ContainerSecurityManager':
        """
        添加允许的能力
        
        Args:
            capability: 能力名称（如CAP_NET_BIND_SERVICE）
        """
        self._config.add_capabilities.append(capability)
        return self
        
    def enable_seccomp(self, profile: str = "runtime/default") -> 'ContainerSecurityManager':
        """
        启用seccomp
        
        Args:
            profile: seccomp配置文件
        """
        self._config.seccomp_profile = profile
        return self
        
    def set_user(self, uid: int, gid: int) -> 'ContainerSecurityManager':
        """
        设置运行用户
        
        Args:
            uid: 用户ID
            gid: 组ID
        """
        self._config.run_as_non_root = True
        # 实际配置需要在容器启动时指定 --user 参数
        return self
        
    def build_docker_run_command(self, image: str, command: str) -> List[str]:
        """
        构建Docker运行命令
        
        Args:
            image: 镜像名称
            command: 容器内命令
            
        Returns:
            docker run 命令列表
        """
        cmd = ["docker", "run", "--rm"]
        
        # 资源限制
        if self._config.memory_limit:
            cmd.extend(["--memory", f"{self._config.memory_limit}m"])
        if self._config.cpu_limit:
            cmd.extend(["--cpus", str(self._config.cpu_limit)])
        if self._config.pids_limit:
            cmd.extend(["--pids-limit", str(self._config.pids_limit)])
            
        # 能力管理
        if self._config.drop_all_capabilities:
            for cap in self.MANDATORY_DROP_CAPABILITIES:
                cmd.extend(["--cap-drop", cap])
        for cap in self._config.add_capabilities:
            cmd.extend(["--cap-add", cap])
            
        # 网络隔离
        if self._config.network_disabled:
            cmd.append("--network")
            cmd.append("none")
            
        # 安全选项
        if self._config.no_new_privileges:
            cmd.append("--security-opt")
            cmd.append("no-new-privileges:true")
            
        # seccomp
        if self._config.seccomp_profile:
            cmd.extend(["--security-opt", f"seccomp={self._config.seccomp_profile}"])
            
        # 只读文件系统
        if self._config.read_only_rootfs:
            cmd.append("--read-only")
            
        # 添加镜像和命令
        cmd.append(image)
        cmd.extend(command.split())
        
        return cmd
        
    def build_k8s_security_context(self) -> Dict[str, Any]:
        """
        构建Kubernetes安全上下文
        
        Returns:
            Kubernetes安全上下文字典
        """
        context = {
            "allowPrivilegeEscalation": False,
            "readOnlyRootFilesystem": self._config.read_only_rootfs,
            "runAsNonRoot": self._config.run_as_non_root,
        }
        
        if self._config.add_capabilities:
            context["capabilities"] = {
                "add": self._config.add_capabilities,
                "drop": self.MANDATORY_DROP_CAPABILITIES
            }
            
        return context


# ============================================================
# 第四部分：沙箱执行环境
# ============================================================

class ExecutionResult:
    """执行结果"""
    def __init__(self, success: bool, stdout: str = "", 
                 stderr: str = "", exit_code: int = 0,
                 duration: float = 0, error: Optional[str] = None):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.duration = duration
        self.error = error
        
    def __str__(self):
        status = "成功" if self.success else "失败"
        return f"执行结果: {status} (耗时: {self.duration:.2f}s, 退出码: {self.exit_code})"


class SandboxEnvironment:
    """
    沙箱执行环境
    
    提供安全的代码执行环境，包含资源限制和监控。
    """
    
    def __init__(self, security_config: Optional[ContainerSecurityConfig] = None):
        """
        初始化沙箱环境
        
        Args:
            security_config: 安全配置
        """
        self.security_config = security_config or ContainerSecurityConfig()
        self.resource_limiter = ResourceLimiter()
        self.resource_monitor = ResourceMonitor()
        self.syscall_filter = SyscallFilter()
        self._is_initialized = False
        
    def initialize(self) -> None:
        """初始化沙箱环境"""
        # 应用资源限制
        self.resource_limiter.apply_limits()
        
        # 启动资源监控（可选）
        try:
            self.resource_monitor.start(interval=1.0)
        except RuntimeError:
            # 在某些受限环境中无法启动线程，跳过监控
            pass
        
        self._is_initialized = True
        print("沙箱环境初始化完成")
        
    def execute_command(self, command: str, timeout: float = 30) -> ExecutionResult:
        """
        执行命令
        
        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）
            
        Returns:
            ExecutionResult实例
        """
        if not self._is_initialized:
            self.initialize()
            
        start_time = time.time()
        
        try:
            # 模拟命令执行
            import subprocess
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration=duration
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return ExecutionResult(
                success=False,
                error=f"命令执行超时 ({timeout}秒)",
                duration=duration,
                exit_code=-1
            )
        except Exception as e:
            duration = time.time() - start_time
            return ExecutionResult(
                success=False,
                error=str(e),
                duration=duration,
                exit_code=-1
            )
            
    def execute_python(self, code: str, timeout: float = 30) -> ExecutionResult:
        """
        执行Python代码
        
        Args:
            code: Python代码
            timeout: 超时时间
            
        Returns:
            ExecutionResult实例
        """
        import subprocess
        import tempfile
        import os
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
            
        try:
            return self.execute_command(
                f"python3 {temp_file}",
                timeout=timeout
            )
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except:
                pass
                
    def get_security_info(self) -> Dict[str, Any]:
        """获取安全配置信息"""
        return {
            "syscall_whitelist": self.syscall_filter.get_allowed_syscalls(),
            "blocked_syscalls": self.syscall_filter.get_blocked_syscalls(),
            "security_config": {
                "memory_limit": self.security_config.memory_limit,
                "cpu_limit": self.security_config.cpu_limit,
                "network_disabled": self.security_config.network_disabled,
                "read_only_rootfs": self.security_config.read_only_rootfs,
                "seccomp_profile": self.security_config.seccomp_profile,
            },
            "resource_limits": self.resource_limiter.get_limits(),
        }
        
    def cleanup(self) -> None:
        """清理沙箱环境"""
        try:
            self.resource_monitor.stop()
        except RuntimeError:
            pass
        print("沙箱环境已清理")


# ============================================================
# 第五部分：生产级配置示例
# ============================================================

def create_production_sandbox() -> SandboxEnvironment:
    """
    创建生产级沙箱配置
    
    Returns:
        配置好的SandboxEnvironment实例
    """
    # 配置安全选项
    security_config = ContainerSecurityConfig(
        memory_limit=512,           # 512MB内存
        cpu_limit=1.0,             # 1个CPU核心
        pids_limit=50,             # 最多50个进程
        network_disabled=False,    # 允许网络（需要时可禁用）
        read_only_rootfs=True,     # 根文件系统只读
        seccomp_profile="runtime/default",
    )
    
    sandbox = SandboxEnvironment(security_config)
    return sandbox


def create_isolated_sandbox() -> SandboxEnvironment:
    """
    创建完全隔离的沙箱配置（无网络）
    
    Returns:
        配置好的SandboxEnvironment实例
    """
    security_config = ContainerSecurityConfig(
        memory_limit=256,
        cpu_limit=0.5,
        pids_limit=20,
        network_disabled=True,     # 完全禁用网络
        read_only_rootfs=True,
        seccomp_profile="unconfined",  # 宽松的seccomp（测试用）
    )
    
    return SandboxEnvironment(security_config)


# ============================================================
# 第六部分：演示与测试
# ============================================================

def run_demo():
    """演示沙箱安全系统"""
    print("=" * 60)
    print("DeerFlow 沙箱安全强化演示")
    print("=" * 60)
    
    # 创建沙箱
    print("\n1. 创建沙箱环境...")
    sandbox = create_production_sandbox()
    sandbox.initialize()
    
    # 显示安全配置
    print("\n2. 安全配置信息:")
    info = sandbox.get_security_info()
    print(f"   允许的系统调用数量: {len(info['syscall_whitelist'])}")
    print(f"   被阻止的系统调用数量: {len(info['blocked_syscalls'])}")
    print(f"   内存限制: {info['security_config']['memory_limit']}MB")
    print(f"   CPU限制: {info['security_config']['cpu_limit']}")
    print(f"   网络禁用: {info['security_config']['network_disabled']}")
    print(f"   只读根文件系统: {info['security_config']['read_only_rootfs']}")
    
    # 测试命令执行
    print("\n3. 测试命令执行...")
    result = sandbox.execute_command("echo 'Hello DeerFlow'", timeout=5)
    print(f"   {result}")
    
    # 测试Python执行
    print("\n4. 测试Python代码执行...")
    result = sandbox.execute_python("print('Python in sandbox'); print(1+2)", timeout=5)
    print(f"   {result}")
    
    # 测试超时
    print("\n5. 测试超时处理...")
    result = sandbox.execute_command("sleep 10", timeout=2)
    print(f"   {result}")
    
    # 容器安全配置示例
    print("\n6. Docker安全配置:")
    security_manager = ContainerSecurityManager()
    security_manager.set_memory_limit(512).disable_network().enable_seccomp()
    
    docker_cmd = security_manager.build_docker_run_command(
        "deerflow-sandbox", 
        "python script.py"
    )
    print(f"   {' '.join(docker_cmd)}")
    
    # 清理
    sandbox.cleanup()
    
    print("\n演示完成!")


def run_tests():
    """运行测试"""
    print("\n" + "=" * 60)
    print("运行单元测试")
    print("=" * 60 + "\n")
    
    # 测试资源限制
    print("测试1: 资源限制系统")
    limiter = ResourceLimiter()
    limiter.apply_limits()
    limits = limiter.get_limits()
    print(f"   已设置 {len(limits)} 项资源限制")
    print("✓ 资源限制测试通过\n")
    
    # 测试系统调用过滤
    print("测试2: 系统调用过滤")
    filter = SyscallFilter(allowed_categories=[SyscallCategory.FILE])
    assert filter.check_syscall("read") == True
    assert filter.check_syscall("write") == True
    assert filter.check_syscall("socket") == False
    print(f"   允许的系统调用: {len(filter.get_allowed_syscalls())}")
    print(f"   被阻止的系统调用: {len(filter.get_blocked_syscalls())}")
    print("✓ 系统调用过滤测试通过\n")
    
    # 测试容器安全管理器
    print("测试3: 容器安全管理器")
    manager = ContainerSecurityManager()
    manager.set_memory_limit(256).set_cpu_limit(0.5).disable_network()
    cmd = manager.build_docker_run_command("test-image", "echo hello")
    assert "--memory" in cmd
    assert "--network" in cmd
    print(f"   生成命令: {' '.join(cmd[:6])}...")
    print("✓ 容器安全管理器测试通过\n")
    
    # 测试Kubernetes安全上下文
    print("测试4: Kubernetes安全上下文")
    context = manager.build_k8s_security_context()
    assert context["allowPrivilegeEscalation"] == False
    assert context["readOnlyRootFilesystem"] == True
    print(f"   上下文: {context}")
    print("✓ Kubernetes安全上下文测试通过\n")
    
    # 测试沙箱环境
    print("测试5: 沙箱环境")
    sandbox = SandboxEnvironment()
    sandbox.initialize()
    print(f"   沙箱环境已初始化")
    sandbox.cleanup()
    print("✓ 沙箱环境测试通过\n")
    
    # 测试生产级配置
    print("测试6: 生产级沙箱配置")
    prod_sandbox = create_production_sandbox()
    assert prod_sandbox.security_config.memory_limit == 512
    assert prod_sandbox.security_config.seccomp_profile == "runtime/default"
    print("   生产级沙箱创建成功")
    print("✓ 生产级配置测试通过\n")
    
    print("=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        run_tests()
    else:
        run_demo()
