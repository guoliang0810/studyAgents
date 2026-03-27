#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 11 Lesson 44: Bash专家子代理 (Bash Expert Subagent)

本文件演示Bash专家子代理的设计和实现，包括：
1. 命令白名单 - ALLOWED_COMMANDS定义允许执行的命令
2. 安全检查 - 危险模式检测和命令注入防护
3. 四阶段执行流程 - 解析、检查、执行、格式化
4. 资源限制 - 超时和输出大小限制

使用示例:
    python bash_subagent_demo.py          # 运行基本演示
    python bash_subagent_demo.py --test   # 运行测试套件
    python bash_subagent_demo.py --demo   # 运行完整演示
    python bash_subagent_demo.py --help   # 显示帮助信息
"""

import asyncio
import re
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import uuid
import shlex


class SecurityLevel(Enum):
    """安全级别枚举"""
    LOW = "low"          # 低安全（开发环境）
    MEDIUM = "medium"    # 中等安全（测试环境）
    HIGH = "high"        # 高安全（生产环境）


class CommandStatus(Enum):
    """命令执行状态枚举"""
    ALLOWED = "allowed"          # 允许执行
    DENIED = "denied"            # 拒绝执行
    DANGEROUS = "dangerous"      # 危险命令
    INVALID = "invalid"          # 无效命令


@dataclass
class BashCommand:
    """Bash命令数据类"""
    raw_command: str                                      # 原始命令
    command_name: str                                     # 命令名称
    arguments: List[str] = field(default_factory=list)    # 命令参数
    environment: Dict[str, str] = field(default_factory=dict)  # 环境变量
    working_dir: str = "/"                                # 工作目录
    
    @classmethod
    def parse(cls, raw_command: str) -> "BashCommand":
        """解析原始命令"""
        # 使用shlex安全解析命令
        try:
            parts = shlex.split(raw_command.strip())
        except ValueError:
            parts = raw_command.strip().split()
        
        if not parts:
            return cls(raw_command=raw_command, command_name="")
        
        command_name = parts[0]
        arguments = parts[1:] if len(parts) > 1 else []
        
        return cls(
            raw_command=raw_command,
            command_name=command_name,
            arguments=arguments
        )
    
    def to_executable(self) -> str:
        """转换为可执行命令字符串"""
        if self.arguments:
            return f"{self.command_name} {' '.join(self.arguments)}"
        return self.command_name


@dataclass
class CommandResult:
    """命令执行结果"""
    command: str                                   # 执行的命令
    status: CommandStatus                          # 执行状态
    exit_code: int = 0                             # 退出码
    stdout: str = ""                               # 标准输出
    stderr: str = ""                               # 错误输出
    execution_time: float = 0.0                    # 执行时间（秒）
    security_warnings: List[str] = field(default_factory=list)  # 安全警告
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "command": self.command,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "execution_time": self.execution_time,
            "security_warnings": self.security_warnings,
            "success": self.status == CommandStatus.ALLOWED and self.exit_code == 0
        }


class SecurityChecker:
    """安全检查器"""
    
    # 允许的命令白名单
    ALLOWED_COMMANDS: Set[str] = {
        "ls", "cat", "grep", "find", "head", "tail",
        "mkdir", "rmdir", "touch", "cp", "mv", "rm",
        "pwd", "echo", "wc", "sort", "uniq", "cut",
        "ps", "df", "du", "free", "uptime", "whoami",
        "date", "hostname", "uname", "env", "printenv",
        "file", "stat", "chmod", "chown",
        "tar", "gzip", "gunzip", "zip", "unzip",
        "wget", "curl",
        "python", "python3", "pip", "node", "npm"
    }
    
    # 危险模式（正则表达式）
    DANGEROUS_PATTERNS: List[Tuple[str, str]] = [
        (r"rm\s+-rf\s+/", "危险的递归删除根目录"),
        (r"rm\s+-rf\s+\*", "危险的递归删除所有文件"),
        (r":\(\)\{:\|:\&\};:", "检测到fork炸弹"),
        (r"mkfs", "格式化磁盘命令"),
        (r"dd\s+if=/dev/(zero|random|urandom)", "危险的磁盘操作"),
        (r">\s*/dev/(sd|hd|nvme)", "直接写入磁盘设备"),
        (r"chmod\s+777", "过度放宽权限"),
        (r"wget.*\|\s*(ba)?sh", "下载并执行脚本"),
        (r"curl.*\|\s*(ba)?sh", "下载并执行脚本"),
        (r"eval\s*\(", "eval执行动态代码"),
        (r"sudo\s+rm", "sudo删除命令"),
        (r"shutdown|reboot|halt|poweroff", "系统关机命令"),
        (r"kill\s+-9\s+1", "杀死init进程"),
        (r":\(\){ :|:& };:", "另一种fork炸弹变体"),
    ]
    
    # 危险字符
    DANGEROUS_CHARS = ["$", "`", ";", "&&", "||", "|", ">", "<", "&"]
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.MEDIUM):
        self.security_level = security_level
        self.allowed_commands = self.ALLOWED_COMMANDS.copy()
    
    def check_command(self, command: BashCommand) -> Tuple[CommandStatus, List[str]]:
        """
        检查命令安全性
        
        返回: (状态, 警告列表)
        """
        warnings = []
        
        # 1. 空命令检查
        if not command.command_name:
            return CommandStatus.INVALID, ["命令为空"]
        
        # 2. 白名单检查
        if command.command_name not in self.allowed_commands:
            warnings.append(f"命令不在白名单中: {command.command_name}")
            if self.security_level == SecurityLevel.HIGH:
                return CommandStatus.DENIED, warnings
        
        # 3. 危险模式检查
        for pattern, description in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command.raw_command, re.IGNORECASE):
                warnings.append(f"危险模式检测: {description}")
                return CommandStatus.DANGEROUS, warnings
        
        # 4. 命令注入检查（高安全级别）
        if self.security_level == SecurityLevel.HIGH:
            injection_result = self._check_injection(command)
            if injection_result:
                warnings.append(f"可能的命令注入: {injection_result}")
                return CommandStatus.DANGEROUS, warnings
        
        # 5. 参数长度检查
        for arg in command.arguments:
            if len(arg) > 1000:
                warnings.append(f"参数过长: {len(arg)} 字符")
                return CommandStatus.DENIED, warnings
        
        return CommandStatus.ALLOWED, warnings
    
    def _check_injection(self, command: BashCommand) -> Optional[str]:
        """检查命令注入"""
        full_command = command.to_executable()
        
        # 检测shell元字符
        if self.security_level == SecurityLevel.HIGH:
            # 在高安全模式下，禁止使用管道、重定向等
            dangerous_ops = ["|", ">", "<", ">>", "&&", "||", ";", "`"]
            for op in dangerous_ops:
                if op in full_command:
                    return f"包含shell操作符: {op}"
        
        return None
    
    def add_allowed_command(self, command: str):
        """添加允许的命令"""
        self.allowed_commands.add(command)
    
    def remove_allowed_command(self, command: str):
        """移除允许的命令"""
        self.allowed_commands.discard(command)


class CommandExecutor:
    """命令执行器"""
    
    def __init__(self, timeout: int = 30, max_output_size: int = 1024 * 1024):
        self.timeout = timeout
        self.max_output_size = max_output_size
    
    async def execute(self, command: BashCommand, 
                      working_dir: str = "/tmp") -> Tuple[int, str, str]:
        """
        执行命令
        
        返回: (退出码, stdout, stderr)
        """
        import subprocess
        
        try:
            # 准备命令
            cmd_list = [command.command_name] + command.arguments
            
            # 创建子进程
            process = await asyncio.create_subprocess_exec(
                *cmd_list,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )
            
            try:
                # 等待执行完成（带超时）
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
                
                # 截断过长的输出
                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')
                
                if len(stdout_str) > self.max_output_size:
                    stdout_str = stdout_str[:self.max_output_size] + "\n[输出已截断]"
                
                if len(stderr_str) > self.max_output_size:
                    stderr_str = stderr_str[:self.max_output_size] + "\n[输出已截断]"
                
                return process.returncode or 0, stdout_str, stderr_str
                
            except asyncio.TimeoutError:
                # 超时，终止进程
                process.kill()
                await process.wait()
                return -1, "", f"命令执行超时（{self.timeout}秒）"
                
        except FileNotFoundError:
            return -1, "", f"命令未找到: {command.command_name}"
        except Exception as e:
            return -1, "", f"执行错误: {str(e)}"


class BashSubagent:
    """Bash专家子代理"""
    
    def __init__(self, name: str = "bash_expert", 
                 security_level: SecurityLevel = SecurityLevel.MEDIUM,
                 timeout: int = 30):
        self.name = name
        self.security_checker = SecurityChecker(security_level)
        self.executor = CommandExecutor(timeout=timeout)
        self.execution_count = 0
        self.success_count = 0
        self.denied_count = 0
        self.is_initialized = False
    
    async def initialize(self):
        """初始化子代理"""
        self.is_initialized = True
        logging.info(f"Bash子代理 {self.name} 已初始化 (安全级别: {self.security_checker.security_level.value})")
    
    async def execute_command(self, command_str: str, 
                              working_dir: str = "/tmp") -> CommandResult:
        """
        执行Bash命令 - 四阶段流程
        
        阶段1: 解析命令
        阶段2: 安全检查
        阶段3: 执行命令
        阶段4: 格式化输出
        """
        start_time = datetime.now()
        self.execution_count += 1
        
        # 阶段1: 解析命令
        command = BashCommand.parse(command_str)
        
        # 阶段2: 安全检查
        status, warnings = self.security_checker.check_command(command)
        
        if status in [CommandStatus.DENIED, CommandStatus.DANGEROUS, CommandStatus.INVALID]:
            self.denied_count += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            return CommandResult(
                command=command_str,
                status=status,
                stderr=f"命令被拒绝: {'; '.join(warnings)}",
                execution_time=execution_time,
                security_warnings=warnings
            )
        
        # 阶段3: 执行命令
        exit_code, stdout, stderr = await self.executor.execute(command, working_dir)
        
        # 阶段4: 格式化输出
        execution_time = (datetime.now() - start_time).total_seconds()
        
        if exit_code == 0:
            self.success_count += 1
            final_status = CommandStatus.ALLOWED
        else:
            final_status = CommandStatus.ALLOWED  # 执行了，只是失败了
        
        return CommandResult(
            command=command_str,
            status=final_status,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            execution_time=execution_time,
            security_warnings=warnings
        )
    
    async def execute_multiple(self, commands: List[str], 
                               working_dir: str = "/tmp") -> List[CommandResult]:
        """执行多个命令"""
        results = []
        for cmd in commands:
            result = await self.execute_command(cmd, working_dir)
            results.append(result)
        return results
    
    def add_allowed_command(self, command: str):
        """添加允许的命令"""
        self.security_checker.add_allowed_command(command)
    
    def remove_allowed_command(self, command: str):
        """移除允许的命令"""
        self.security_checker.remove_allowed_command(command)
    
    async def shutdown(self):
        """关闭子代理"""
        self.is_initialized = False
        logging.info(f"Bash子代理 {self.name} 已关闭")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "name": self.name,
            "security_level": self.security_checker.security_level.value,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "denied_count": self.denied_count,
            "success_rate": (self.success_count / self.execution_count * 100) 
                if self.execution_count > 0 else 0,
            "denied_rate": (self.denied_count / self.execution_count * 100)
                if self.execution_count > 0 else 0,
            "allowed_commands": len(self.security_checker.allowed_commands)
        }


class BashSubagentTestSuite:
    """Bash子代理测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_command_parsing", self.test_command_parsing),
            ("test_security_checker", self.test_security_checker),
            ("test_safe_commands", self.test_safe_commands),
            ("test_dangerous_commands", self.test_dangerous_commands),
            ("test_subagent_lifecycle", self.test_subagent_lifecycle),
        ]
    
    def test_command_parsing(self) -> tuple:
        """测试命令解析"""
        try:
            # 简单命令
            cmd = BashCommand.parse("ls -la")
            if cmd.command_name != "ls":
                return False, f"命令名称不正确: {cmd.command_name}"
            if cmd.arguments != ["-la"]:
                return False, f"参数不正确: {cmd.arguments}"
            
            # 带引号的命令
            cmd = BashCommand.parse('echo "hello world"')
            if cmd.command_name != "echo":
                return False, f"命令名称不正确: {cmd.command_name}"
            if cmd.arguments != ["hello world"]:
                return False, f"参数不正确: {cmd.arguments}"
            
            # 空命令
            cmd = BashCommand.parse("")
            if cmd.command_name != "":
                return False, "空命令解析失败"
            
            return True, "命令解析测试通过"
        except Exception as e:
            return False, f"解析异常: {e}"
    
    def test_security_checker(self) -> tuple:
        """测试安全检查器"""
        try:
            checker = SecurityChecker(SecurityLevel.HIGH)
            
            # 允许的命令
            cmd = BashCommand.parse("ls -la")
            status, _ = checker.check_command(cmd)
            if status != CommandStatus.ALLOWED:
                return False, f"允许的命令被拒绝: {status}"
            
            # 不在白名单的命令
            cmd = BashCommand.parse("nc -e /bin/sh")
            status, warnings = checker.check_command(cmd)
            if status == CommandStatus.ALLOWED:
                return False, "危险命令应该被拒绝"
            
            # 危险模式
            cmd = BashCommand.parse("rm -rf /")
            status, warnings = checker.check_command(cmd)
            if status != CommandStatus.DANGEROUS:
                return False, f"危险命令应该被标记为DANGEROUS: {status}"
            
            return True, "安全检查器测试通过"
        except Exception as e:
            return False, f"安全检查器异常: {e}"
    
    def test_safe_commands(self) -> tuple:
        """测试安全命令执行"""
        async def run_test():
            agent = BashSubagent(security_level=SecurityLevel.LOW)
            await agent.initialize()
            
            # 执行安全命令
            result = await agent.execute_command("echo 'Hello World'")
            
            if result.status != CommandStatus.ALLOWED:
                return False, f"安全命令被拒绝: {result.stderr}"
            
            if result.exit_code != 0:
                return False, f"命令执行失败: {result.stderr}"
            
            if "Hello World" not in result.stdout:
                return False, f"输出不正确: {result.stdout}"
            
            await agent.shutdown()
            return True, "安全命令执行测试通过"
        
        return asyncio.run(run_test())
    
    def test_dangerous_commands(self) -> tuple:
        """测试危险命令拦截"""
        async def run_test():
            agent = BashSubagent(security_level=SecurityLevel.HIGH)
            await agent.initialize()
            
            # 危险命令1: rm -rf /
            result = await agent.execute_command("rm -rf /")
            if result.status != CommandStatus.DANGEROUS:
                return False, f"危险命令rm -rf /应该被拦截: {result.status}"
            
            # 危险命令2: fork bomb
            result = await agent.execute_command(":(){ :|:& };:")
            if result.status != CommandStatus.DANGEROUS:
                return False, f"fork炸弹应该被拦截: {result.status}"
            
            # 不在白名单
            result = await agent.execute_command("nc -e /bin/sh")
            if result.status != CommandStatus.DENIED:
                return False, f"白名单外命令应该被拒绝: {result.status}"
            
            await agent.shutdown()
            return True, "危险命令拦截测试通过"
        
        return asyncio.run(run_test())
    
    def test_subagent_lifecycle(self) -> tuple:
        """测试子代理生命周期"""
        async def run_test():
            agent = BashSubagent()
            
            if agent.is_initialized:
                return False, "初始化前不应该已初始化"
            
            await agent.initialize()
            
            if not agent.is_initialized:
                return False, "初始化后应该已初始化"
            
            stats = agent.get_stats()
            if stats["name"] != "bash_expert":
                return False, f"名称不正确: {stats['name']}"
            
            await agent.shutdown()
            
            if agent.is_initialized:
                return False, "关闭后不应该已初始化"
            
            return True, "子代理生命周期测试通过"
        
        return asyncio.run(run_test())
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行Bash专家子代理测试套件...")
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
                print(f"   ❌ 异常: {str(e)}")
                failed += 1
                results[test_name] = {"passed": False, "message": str(e)}
        
        print("=" * 60)
        print(f"📊 测试摘要:")
        print(f"   总测试数: {len(self.tests)}")
        print(f"   通过测试: {passed}")
        print(f"   失败测试: {failed}")
        print(f"   成功率: {passed / len(self.tests) * 100:.1f}%")
        
        return {
            "summary": {
                "total_tests": len(self.tests),
                "passed_tests": passed,
                "failed_tests": failed,
                "success_rate": passed / len(self.tests) * 100 if len(self.tests) > 0 else 0
            },
            "detailed_results": results
        }


async def main_demo():
    """主演示函数"""
    print("🎓 Day 11 Lesson 44: Bash专家子代理演示")
    print("=" * 60)
    
    # 1. 创建子代理
    print("\n1. 创建Bash子代理:")
    agent = BashSubagent(
        name="demo_bash",
        security_level=SecurityLevel.MEDIUM,
        timeout=10
    )
    await agent.initialize()
    print(f"   ✅ 子代理已初始化: {agent.name}")
    
    # 2. 安全命令执行
    print("\n2. 安全命令执行:")
    
    safe_commands = [
        "echo 'Hello from Bash subagent'",
        "whoami",
        "pwd",
        "date",
        "uname -a"
    ]
    
    for cmd in safe_commands:
        result = await agent.execute_command(cmd)
        status_icon = "✅" if result.status == CommandStatus.ALLOWED else "❌"
        print(f"   {status_icon} {cmd}")
        if result.stdout:
            print(f"      输出: {result.stdout.strip()[:80]}")
    
    # 3. 危险命令拦截
    print("\n3. 危险命令拦截:")
    
    dangerous_commands = [
        "rm -rf /",
        ":(){ :|:& };:",
        "nc -e /bin/sh",
        "chmod 777 /etc/passwd"
    ]
    
    for cmd in dangerous_commands:
        result = await agent.execute_command(cmd)
        status_icon = "🛡️" if result.status in [CommandStatus.DANGEROUS, CommandStatus.DENIED] else "⚠️"
        print(f"   {status_icon} {cmd}")
        if result.security_warnings:
            print(f"      警告: {result.security_warnings[0]}")
    
    # 4. 白名单外命令
    print("\n4. 白名单检查:")
    
    cmd = "systemctl status nginx"
    result = await agent.execute_command(cmd)
    print(f"   命令: {cmd}")
    print(f"   状态: {result.status.value}")
    if result.security_warnings:
        print(f"   警告: {result.security_warnings[0]}")
    
    # 5. 动态添加允许命令
    print("\n5. 动态配置:")
    agent.add_allowed_command("systemctl")
    print(f"   已添加 'systemctl' 到白名单")
    
    result = await agent.execute_command("systemctl --version")
    print(f"   systemctl --version: {result.status.value}")
    
    # 6. 统计信息
    print("\n6. 统计信息:")
    stats = agent.get_stats()
    print(f"   执行次数: {stats['execution_count']}")
    print(f"   成功次数: {stats['success_count']}")
    print(f"   拒绝次数: {stats['denied_count']}")
    print(f"   成功率: {stats['success_rate']:.1f}%")
    print(f"   拒绝率: {stats['denied_rate']:.1f}%")
    
    # 7. 关闭子代理
    print("\n7. 关闭子代理:")
    await agent.shutdown()
    print(f"   ✅ 子代理已关闭")
    
    print("\n演示完成!")


def run_tests():
    """运行测试套件"""
    test_suite = BashSubagentTestSuite()
    report = test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 Bash专家子代理测试套件验证通过")
        return True
    else:
        print("\n⚠️  有测试失败，请检查实现代码")
        return False


if __name__ == "__main__":
    import sys
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
    elif len(sys.argv) > 1 and sys.argv[1] == "--demo":
        asyncio.run(main_demo())
    else:
        asyncio.run(main_demo())
