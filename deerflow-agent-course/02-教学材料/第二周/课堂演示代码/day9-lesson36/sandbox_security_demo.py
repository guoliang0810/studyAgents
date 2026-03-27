#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 9 Lesson 36: 沙箱安全机制

本文件演示沙箱安全机制的完整实现，包括：
1. 多层防御体系 - 文件系统隔离、网络隔离、进程隔离
2. 权限控制机制 - 能力限制、系统调用过滤
3. 安全审计系统 - 审计日志、异常检测
4. 威胁检测与响应 - 入侵检测、自动响应

使用示例:
    python sandbox_security_demo.py          # 运行基本演示
    python sandbox_security_demo.py --test   # 运行测试套件
    python sandbox_security_demo.py --demo   # 运行完整演示
    python sandbox_security_demo.py --help   # 显示帮助信息
"""

import os
import sys
import json
import time
import argparse
import hashlib
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import threading

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================

class SecurityLevel(Enum):
    """安全级别枚举"""
    MINIMAL = "最小安全"      # 基本隔离
    STANDARD = "标准安全"     # 标准隔离+资源限制
    ENHANCED = "增强安全"     # 全面防护
    PARANOID = "偏执安全"     # 最大安全（性能牺牲）

class ThreatLevel(Enum):
    """威胁级别枚举"""
    INFO = "信息"
    LOW = "低"
    MEDIUM = "中"
    HIGH = "高"
    CRITICAL = "严重"

class SecurityEventType(Enum):
    """安全事件类型枚举"""
    ACCESS_DENIED = "访问被拒绝"
    RESOURCE_LIMIT = "资源限制触发"
    SYSCALL_BLOCKED = "系统调用被阻止"
    PATH_TRAVERSAL = "路径遍历攻击"
    PRIVILEGE_ESCALATION = "权限提升尝试"
    SUSPICIOUS_ACTIVITY = "可疑活动"

@dataclass
class SecurityEvent:
    """安全事件"""
    event_type: SecurityEventType
    threat_level: ThreatLevel
    message: str
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
    sandbox_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "event_type": self.event_type.value,
            "threat_level": self.threat_level.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "details": self.details,
            "sandbox_id": self.sandbox_id,
        }

@dataclass
class SandboxSecurityConfig:
    """沙箱安全配置"""
    security_level: SecurityLevel = SecurityLevel.STANDARD
    # 资源限制
    max_memory_mb: int = 512          # 最大内存（MB）
    max_cpu_percent: int = 50         # 最大CPU使用率
    max_processes: int = 10           # 最大进程数
    max_open_files: int = 1024        # 最大打开文件数
    # 权限控制
    allow_network: bool = False       # 是否允许网络访问
    allow_file_write: bool = True     # 是否允许文件写入
    allow_exec: bool = False          # 是否允许执行外部程序
    allowed_syscalls: List[str] = field(default_factory=lambda: ["read", "write", "open", "close"])
    # 路径限制
    allowed_paths: List[str] = field(default_factory=list)  # 允许访问的路径
    forbidden_paths: List[str] = field(default_factory=lambda: ["/etc/shadow", "/proc/sys"])
    
    def to_dict(self) -> Dict:
        return asdict(self)

# ============================================================================
# 第二部分：核心功能实现
# ============================================================================

class SecurityError(Exception):
    """安全错误"""
    pass

class ResourceLimitError(SecurityError):
    """资源限制错误"""
    pass

class PermissionDeniedError(SecurityError):
    """权限拒绝错误"""
    pass

class SecurityAuditor:
    """安全审计器"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.events: List[SecurityEvent] = []
        self.log_file = log_file
        self.lock = threading.Lock()
        self.logger = logging.getLogger("SecurityAuditor")
        
        # 威胁统计
        self.threat_counts: Dict[ThreatLevel, int] = {
            level: 0 for level in ThreatLevel
        }
    
    def log_event(self, event: SecurityEvent) -> None:
        """记录安全事件"""
        with self.lock:
            self.events.append(event)
            self.threat_counts[event.threat_level] += 1
        
        # 记录到日志
        log_level = {
            ThreatLevel.INFO: logging.INFO,
            ThreatLevel.LOW: logging.WARNING,
            ThreatLevel.MEDIUM: logging.WARNING,
            ThreatLevel.HIGH: logging.ERROR,
            ThreatLevel.CRITICAL: logging.CRITICAL,
        }.get(event.threat_level, logging.INFO)
        
        self.logger.log(log_level, f"[{event.threat_level.value}] {event.message}")
        
        # 写入文件
        if self.log_file:
            self._write_to_file(event)
    
    def _write_to_file(self, event: SecurityEvent) -> None:
        """写入审计日志文件"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"写入审计日志失败: {e}")
    
    def get_events(self, 
                   event_type: Optional[SecurityEventType] = None,
                   threat_level: Optional[ThreatLevel] = None,
                   limit: int = 100) -> List[SecurityEvent]:
        """获取安全事件"""
        with self.lock:
            filtered = self.events
            
            if event_type:
                filtered = [e for e in filtered if e.event_type == event_type]
            
            if threat_level:
                filtered = [e for e in filtered if e.threat_level == threat_level]
            
            return filtered[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取安全统计"""
        with self.lock:
            return {
                "total_events": len(self.events),
                "threat_counts": {k.value: v for k, v in self.threat_counts.items()},
                "recent_events": [e.to_dict() for e in self.events[-10:]],
            }
    
    def clear(self) -> None:
        """清空事件记录"""
        with self.lock:
            self.events.clear()
            self.threat_counts = {level: 0 for level in ThreatLevel}

class ResourceLimiter:
    """资源限制器"""
    
    def __init__(self, config: SandboxSecurityConfig):
        self.config = config
        self.current_memory_mb = 0
        self.current_processes = 0
        self.current_open_files = 0
        self.lock = threading.Lock()
        self.logger = logging.getLogger("ResourceLimiter")
    
    def check_memory(self, required_mb: float) -> bool:
        """检查内存限制"""
        with self.lock:
            if self.current_memory_mb + required_mb > self.config.max_memory_mb:
                return False
            self.current_memory_mb += required_mb
            return True
    
    def release_memory(self, released_mb: float) -> None:
        """释放内存"""
        with self.lock:
            self.current_memory_mb = max(0, self.current_memory_mb - released_mb)
    
    def check_process(self) -> bool:
        """检查进程数限制"""
        with self.lock:
            if self.current_processes >= self.config.max_processes:
                return False
            self.current_processes += 1
            return True
    
    def release_process(self) -> None:
        """释放进程数"""
        with self.lock:
            self.current_processes = max(0, self.current_processes - 1)
    
    def get_usage(self) -> Dict[str, Any]:
        """获取资源使用情况"""
        with self.lock:
            return {
                "memory": {
                    "used_mb": self.current_memory_mb,
                    "max_mb": self.config.max_memory_mb,
                    "usage_percent": (self.current_memory_mb / self.config.max_memory_mb * 100) if self.config.max_memory_mb > 0 else 0,
                },
                "processes": {
                    "used": self.current_processes,
                    "max": self.config.max_processes,
                    "usage_percent": (self.current_processes / self.config.max_processes * 100) if self.config.max_processes > 0 else 0,
                },
            }

class PermissionController:
    """权限控制器"""
    
    def __init__(self, config: SandboxSecurityConfig):
        self.config = config
        self.logger = logging.getLogger("PermissionController")
    
    def check_network_access(self) -> Tuple[bool, str]:
        """检查网络访问权限"""
        if not self.config.allow_network:
            return False, "网络访问被禁止"
        return True, "允许网络访问"
    
    def check_file_access(self, path: str, operation: str = "read") -> Tuple[bool, str]:
        """检查文件访问权限"""
        # 检查禁止路径
        for forbidden in self.config.forbidden_paths:
            if path.startswith(forbidden):
                return False, f"访问被禁止的路径: {forbidden}"
        
        # 检查写入权限
        if operation == "write" and not self.config.allow_file_write:
            return False, "文件写入被禁止"
        
        # 检查允许路径
        if self.config.allowed_paths:
            allowed = False
            for allowed_path in self.config.allowed_paths:
                if path.startswith(allowed_path):
                    allowed = True
                    break
            if not allowed:
                return False, f"路径不在允许列表中: {path}"
        
        return True, f"允许{operation}操作: {path}"
    
    def check_syscall(self, syscall_name: str) -> Tuple[bool, str]:
        """检查系统调用权限"""
        if syscall_name not in self.config.allowed_syscalls:
            return False, f"系统调用被禁止: {syscall_name}"
        return True, f"允许系统调用: {syscall_name}"
    
    def check_exec_permission(self, program: str) -> Tuple[bool, str]:
        """检查执行权限"""
        if not self.config.allow_exec:
            return False, f"程序执行被禁止: {program}"
        return True, f"允许执行程序: {program}"

class ThreatDetector:
    """威胁检测器"""
    
    def __init__(self, auditor: SecurityAuditor):
        self.auditor = auditor
        self.logger = logging.getLogger("ThreatDetector")
        
        # 可疑模式
        self.suspicious_patterns = [
            r'\.\./',           # 路径遍历
            r'/etc/passwd',     # 敏感文件访问
            r'/etc/shadow',     # 敏感文件访问
            r'/proc/sys',       # 内核参数访问
            r'rm\s+-rf\s+/',    # 危险删除命令
            r'chmod\s+777',     # 危险权限修改
        ]
    
    def analyze_path(self, path: str, sandbox_id: Optional[str] = None) -> bool:
        """分析路径是否可疑"""
        import re
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, path):
                event = SecurityEvent(
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                    threat_level=ThreatLevel.MEDIUM,
                    message=f"检测到可疑路径: {path}",
                    details={"path": path, "pattern": pattern},
                    sandbox_id=sandbox_id,
                )
                self.auditor.log_event(event)
                return True
        return False
    
    def analyze_command(self, command: str, sandbox_id: Optional[str] = None) -> bool:
        """分析命令是否可疑"""
        import re
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                event = SecurityEvent(
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                    threat_level=ThreatLevel.HIGH,
                    message=f"检测到可疑命令: {command}",
                    details={"command": command, "pattern": pattern},
                    sandbox_id=sandbox_id,
                )
                self.auditor.log_event(event)
                return True
        return False

class SandboxSecurityManager:
    """沙箱安全管理器"""
    
    def __init__(self, config: SandboxSecurityConfig, sandbox_id: str = "default"):
        self.config = config
        self.sandbox_id = sandbox_id
        self.auditor = SecurityAuditor()
        self.resource_limiter = ResourceLimiter(config)
        self.permission_controller = PermissionController(config)
        self.threat_detector = ThreatDetector(self.auditor)
        self.logger = logging.getLogger("SandboxSecurityManager")
        
        # 记录初始化事件
        self.auditor.log_event(SecurityEvent(
            event_type=SecurityEventType.ACCESS_DENIED,
            threat_level=ThreatLevel.INFO,
            message=f"沙箱安全初始化: {config.security_level.value}",
            details={"config": config.to_dict()},
            sandbox_id=sandbox_id,
        ))
    
    def check_access(self, path: str, operation: str = "read") -> Tuple[bool, str]:
        """检查访问权限（综合检查）"""
        # 威胁检测
        is_suspicious = self.threat_detector.analyze_path(path, self.sandbox_id)
        
        # 权限检查
        allowed, message = self.permission_controller.check_file_access(path, operation)
        
        if not allowed:
            # 记录安全事件
            event = SecurityEvent(
                event_type=SecurityEventType.ACCESS_DENIED,
                threat_level=ThreatLevel.MEDIUM if is_suspicious else ThreatLevel.LOW,
                message=message,
                details={"path": path, "operation": operation, "suspicious": is_suspicious},
                sandbox_id=self.sandbox_id,
            )
            self.auditor.log_event(event)
        
        return allowed, message
    
    def allocate_resource(self, resource_type: str, amount: float) -> Tuple[bool, str]:
        """分配资源"""
        if resource_type == "memory":
            success = self.resource_limiter.check_memory(amount)
            if not success:
                event = SecurityEvent(
                    event_type=SecurityEventType.RESOURCE_LIMIT,
                    threat_level=ThreatLevel.MEDIUM,
                    message=f"内存限制: 请求 {amount}MB 超过限制",
                    details={"resource": "memory", "requested": amount},
                    sandbox_id=self.sandbox_id,
                )
                self.auditor.log_event(event)
                return False, f"内存不足: 请求 {amount}MB"
            return True, f"分配内存 {amount}MB"
        
        elif resource_type == "process":
            success = self.resource_limiter.check_process()
            if not success:
                event = SecurityEvent(
                    event_type=SecurityEventType.RESOURCE_LIMIT,
                    threat_level=ThreatLevel.MEDIUM,
                    message="进程数达到上限",
                    details={"resource": "process"},
                    sandbox_id=self.sandbox_id,
                )
                self.auditor.log_event(event)
                return False, "进程数达到上限"
            return True, "分配进程槽位"
        
        return False, f"未知资源类型: {resource_type}"
    
    def get_security_report(self) -> Dict[str, Any]:
        """获取安全报告"""
        return {
            "sandbox_id": self.sandbox_id,
            "security_level": self.config.security_level.value,
            "statistics": self.auditor.get_statistics(),
            "resource_usage": self.resource_limiter.get_usage(),
            "config": self.config.to_dict(),
        }

# ============================================================================
# 第三部分：演示与测试
# ============================================================================

class SandboxSecurityTestSuite:
    """沙箱安全测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        self.tests.append(("test_security_config", self.test_security_config))
        self.tests.append(("test_access_control", self.test_access_control))
        self.tests.append(("test_resource_limiting", self.test_resource_limiting))
        self.tests.append(("test_threat_detection", self.test_threat_detection))
        self.tests.append(("test_audit_logging", self.test_audit_logging))
    
    def test_security_config(self) -> Tuple[bool, str]:
        config = SandboxSecurityConfig(security_level=SecurityLevel.ENHANCED)
        if config.security_level != SecurityLevel.ENHANCED:
            return False, f"安全级别设置错误: {config.security_level}"
        if config.max_memory_mb != 512:
            return False, f"默认内存限制错误: {config.max_memory_mb}"
        return True, "安全配置测试通过"
    
    def test_access_control(self) -> Tuple[bool, str]:
        config = SandboxSecurityConfig()
        controller = PermissionController(config)
        
        # 测试禁止网络访问
        allowed, msg = controller.check_network_access()
        if allowed:
            return False, "默认应禁止网络访问"
        
        # 测试允许的文件访问
        config.allowed_paths = ["/tmp"]
        controller = PermissionController(config)
        allowed, msg = controller.check_file_access("/tmp/file.txt")
        if not allowed:
            return False, f"允许路径应被允许: {msg}"
        
        # 测试禁止的路径
        allowed, msg = controller.check_file_access("/etc/shadow")
        if allowed:
            return False, f"禁止路径应被阻止: {msg}"
        
        return True, "访问控制测试通过"
    
    def test_resource_limiting(self) -> Tuple[bool, str]:
        config = SandboxSecurityConfig(max_memory_mb=100, max_processes=2)
        limiter = ResourceLimiter(config)
        
        # 测试内存分配
        if not limiter.check_memory(50):
            return False, "50MB内存分配应成功"
        
        if not limiter.check_memory(40):
            return False, "40MB内存分配应成功"
        
        if limiter.check_memory(20):
            return False, "20MB内存分配应失败（超限）"
        
        # 测试进程限制
        if not limiter.check_process():
            return False, "第一个进程应成功"
        
        if not limiter.check_process():
            return False, "第二个进程应成功"
        
        if limiter.check_process():
            return False, "第三个进程应失败（超限）"
        
        return True, "资源限制测试通过"
    
    def test_threat_detection(self) -> Tuple[bool, str]:
        auditor = SecurityAuditor()
        detector = ThreatDetector(auditor)
        
        # 测试路径遍历检测
        if not detector.analyze_path("../../../etc/passwd"):
            return False, "路径遍历应被检测"
        
        # 测试敏感文件检测
        if not detector.analyze_path("/etc/shadow"):
            return False, "敏感文件访问应被检测"
        
        # 测试正常路径
        if detector.analyze_path("/tmp/normal/file.txt"):
            return False, "正常路径不应被检测"
        
        return True, "威胁检测测试通过"
    
    def test_audit_logging(self) -> Tuple[bool, str]:
        auditor = SecurityAuditor()
        
        # 记录事件
        for i in range(5):
            event = SecurityEvent(
                event_type=SecurityEventType.ACCESS_DENIED,
                threat_level=ThreatLevel.LOW,
                message=f"测试事件 {i}",
            )
            auditor.log_event(event)
        
        # 检查统计
        stats = auditor.get_statistics()
        if stats["total_events"] != 5:
            return False, f"事件数量错误: {stats['total_events']}"
        
        # 检查过滤
        events = auditor.get_events(threat_level=ThreatLevel.LOW)
        if len(events) != 5:
            return False, f"过滤结果错误: {len(events)}"
        
        return True, "审计日志测试通过"
    
    def run_all_tests(self) -> Dict[str, Any]:
        print("🚀 开始运行沙箱安全测试套件...")
        print("=" * 60)
        
        passed = 0
        failed = 0
        results = {}
        
        for test_name, test_func in self.tests:
            print(f"📋 运行测试: {test_name}...")
            try:
                success, message = test_func()
                if success:
                    print(f"   ✅ 通过: {message}")
                    passed += 1
                    results[test_name] = {"passed": True, "message": message}
                else:
                    print(f"   ❌ 失败: {message}")
                    failed += 1
                    results[test_name] = {"passed": False, "message": message}
            except Exception as e:
                print(f"   💥 异常: {e}")
                failed += 1
                results[test_name] = {"passed": False, "error": str(e)}
        
        print("=" * 60)
        print(f"📊 测试摘要: 总数={len(self.tests)}, 通过={passed}, 失败={failed}")
        
        return {
            "summary": {
                "total": len(self.tests),
                "passed": passed,
                "failed": failed,
                "success_rate": passed / len(self.tests) if self.tests else 0.0
            },
            "details": results
        }

def main_demo() -> None:
    """主演示函数"""
    print("=" * 80)
    print("🎓 Day 9 Lesson 36: 沙箱安全机制演示")
    print("=" * 80)
    
    # 创建安全配置
    config = SandboxSecurityConfig(
        security_level=SecurityLevel.ENHANCED,
        max_memory_mb=256,
        max_processes=5,
        allow_network=False,
        allow_file_write=True,
        allow_exec=False,
        allowed_paths=["/tmp", "/home/user"],
        forbidden_paths=["/etc/shadow", "/proc/sys", "/root"],
    )
    
    print("\n1. 安全配置...")
    print(f"   安全级别: {config.security_level.value}")
    print(f"   内存限制: {config.max_memory_mb}MB")
    print(f"   进程限制: {config.max_processes}")
    print(f"   网络访问: {'允许' if config.allow_network else '禁止'}")
    print(f"   允许路径: {config.allowed_paths}")
    print(f"   禁止路径: {config.forbidden_paths}")
    
    # 创建安全管理器
    security_mgr = SandboxSecurityManager(config, sandbox_id="demo-sandbox-001")
    
    print("\n2. 访问控制演示...")
    test_accesses = [
        ("/tmp/file.txt", "read", "正常访问"),
        ("/tmp/output.txt", "write", "正常写入"),
        ("/etc/passwd", "read", "敏感文件"),
        ("/etc/shadow", "read", "禁止路径"),
        ("/home/user/data.txt", "read", "允许路径"),
        ("/root/.ssh/id_rsa", "read", "禁止路径"),
    ]
    
    for path, op, desc in test_accesses:
        allowed, message = security_mgr.check_access(path, op)
        status = "✅" if allowed else "❌"
        print(f"   {status} {desc}: {path} ({op})")
        if not allowed:
            print(f"      原因: {message}")
    
    print("\n3. 资源限制演示...")
    resource_tests = [
        ("memory", 100, "分配100MB内存"),
        ("memory", 100, "再分配100MB内存"),
        ("memory", 100, "再分配100MB内存（超限）"),
        ("process", 1, "分配进程槽位"),
        ("process", 1, "再分配进程槽位"),
        ("process", 1, "再分配进程槽位（超限）"),
    ]
    
    for res_type, amount, desc in resource_tests:
        success, message = security_mgr.allocate_resource(res_type, amount)
        status = "✅" if success else "❌"
        print(f"   {status} {desc}")
        if not success:
            print(f"      原因: {message}")
    
    print("\n4. 威胁检测演示...")
    suspicious_inputs = [
        "../../../etc/passwd",
        "/etc/shadow",
        "/proc/sys/kernel/randomize_va_space",
        "rm -rf /",
        "chmod 777 /etc/passwd",
        "/tmp/normal/file.txt",
    ]
    
    for path in suspicious_inputs:
        is_suspicious = security_mgr.threat_detector.analyze_path(path)
        status = "⚠️" if is_suspicious else "✅"
        print(f"   {status} {path}")
    
    print("\n5. 安全报告...")
    report = security_mgr.get_security_report()
    print(f"   沙箱ID: {report['sandbox_id']}")
    print(f"   安全级别: {report['security_level']}")
    print(f"   安全事件总数: {report['statistics']['total_events']}")
    print(f"   威胁分布:")
    for level, count in report['statistics']['threat_counts'].items():
        if count > 0:
            print(f"     {level}: {count}")
    
    print("\n6. 运行测试套件...")
    test_suite = SandboxSecurityTestSuite()
    report = test_suite.run_all_tests()
    
    print(f"\n📊 测试报告: 成功率={report['summary']['success_rate']:.1%}")
    
    print("\n" + "=" * 80)
    print("🎉 沙箱安全机制演示完成！")
    print("=" * 80)

def run_tests() -> None:
    """运行测试套件"""
    test_suite = SandboxSecurityTestSuite()
    report = test_suite.run_all_tests()
    
    if report["summary"]["success_rate"] >= 1.0:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 有测试失败，请检查实现。")

def main() -> None:
    parser = argparse.ArgumentParser(description="沙箱安全机制演示程序")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行完整演示")
    
    args = parser.parse_args()
    
    if args.test:
        run_tests()
    elif args.demo:
        main_demo()
    else:
        print("沙箱安全机制演示程序")
        print("使用 --help 查看选项")
        print("\n示例:")
        print("  python sandbox_security_demo.py --demo  # 运行完整演示")
        print("  python sandbox_security_demo.py --test  # 运行测试套件")

if __name__ == "__main__":
    main()
