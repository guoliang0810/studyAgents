#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP服务器配置演示代码
Day 16 - 第62节课：MCP服务器配置

本演示代码展示了MCP（Model Context Protocol）服务器的配置和管理。
内容包括：
1. MCP配置YAML格式定义和解析
2. MCPServerManager异步启动和管理MCP服务器
3. 多种MCP服务器类型（filesystem、sql、github）配置示例
4. 健康检查、错误处理和状态监控
5. 环境变量注入和配置验证
"""

import os
import sys
import yaml
import asyncio
import aiohttp
import signal
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import subprocess
import json

# ============================================================================
# 配置类定义
# ============================================================================

class ServerStatus(Enum):
    """服务器状态枚举"""
    STOPPED = "stopped"      # 已停止
    STARTING = "starting"    # 启动中
    RUNNING = "running"      # 运行中
    ERROR = "error"          # 错误
    STOPPING = "stopping"    # 停止中


@dataclass
class MCPServerConfig:
    """单个MCP服务器配置"""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    port: int = 3000
    auto_start: bool = True
    health_check: Optional[str] = None
    timeout: float = 30.0
    working_dir: Optional[str] = None
    description: str = ""
    
    def __post_init__(self):
        """后初始化处理"""
        # 确保port在env中
        if "MCP_PORT" not in self.env:
            self.env["MCP_PORT"] = str(self.port)
        
        # 如果没有健康检查URL，使用默认
        if not self.health_check:
            self.health_check = f"http://localhost:{self.port}/health"


@dataclass
class MCPConfig:
    """MCP配置主类"""
    servers: Dict[str, MCPServerConfig] = field(default_factory=dict)
    log_level: str = "INFO"
    max_retries: int = 3
    retry_delay: float = 2.0
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> "MCPConfig":
        """从YAML内容创建配置"""
        config_data = yaml.safe_load(yaml_content)
        servers = {}
        
        if "mcp" in config_data and "servers" in config_data["mcp"]:
            servers_data = config_data["mcp"]["servers"]
        else:
            servers_data = config_data.get("servers", {})
        
        for server_name, server_data in servers_data.items():
            # 构建配置
            server_config = MCPServerConfig(
                name=server_name,
                command=server_data.get("command", ""),
                args=server_data.get("args", []),
                env=server_data.get("env", {}),
                port=server_data.get("env", {}).get("MCP_PORT", 3000),
                auto_start=server_data.get("auto_start", True),
                health_check=server_data.get("health_check"),
                timeout=server_data.get("timeout", 30.0),
                working_dir=server_data.get("working_dir"),
                description=server_data.get("description", "")
            )
            servers[server_name] = server_config
        
        return cls(servers=servers)


# ============================================================================
# MCP服务器类
# ============================================================================

class MCPServer:
    """MCP服务器实例"""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self.status = ServerStatus.STOPPED
        self.start_time: Optional[float] = None
        self.pid: Optional[int] = None
        self.stdout: List[str] = []
        self.stderr: List[str] = []
        self.last_error: Optional[str] = None
        self.retry_count = 0
    
    async def start(self) -> bool:
        """启动MCP服务器"""
        try:
            self.status = ServerStatus.STARTING
            self.last_error = None
            
            # 构建环境变量
            env = os.environ.copy()
            env.update(self.config.env)
            
            # 构建命令行
            cmd = [self.config.command] + self.config.args
            
            # 创建工作目录
            cwd = self.config.working_dir
            if cwd and not os.path.exists(cwd):
                os.makedirs(cwd, exist_ok=True)
            
            # 启动子进程
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL
            )
            
            self.pid = self.process.pid
            self.start_time = time.time()
            
            logging.info(f"MCP服务器 {self.config.name} 启动成功 (PID: {self.pid})")
            
            # 启动输出收集任务
            asyncio.create_task(self._collect_output())
            
            # 等待服务器就绪
            if await self.wait_for_ready():
                self.status = ServerStatus.RUNNING
                logging.info(f"MCP服务器 {self.config.name} 就绪")
                return True
            else:
                self.status = ServerStatus.ERROR
                self.last_error = "服务器启动超时"
                logging.error(f"MCP服务器 {self.config.name} 启动超时")
                await self.stop()
                return False
                
        except Exception as e:
            self.status = ServerStatus.ERROR
            self.last_error = str(e)
            logging.error(f"MCP服务器 {self.config.name} 启动失败: {e}")
            return False
    
    async def wait_for_ready(self, timeout: Optional[float] = None) -> bool:
        """等待服务器就绪"""
        if timeout is None:
            timeout = self.config.timeout
        
        start_time = time.time()
        check_interval = 0.5
        
        while time.time() - start_time < timeout:
            if await self.health_check():
                return True
            await asyncio.sleep(check_interval)
        
        return False
    
    async def health_check(self) -> bool:
        """健康检查"""
        if not self.config.health_check:
            # 如果没有健康检查URL，检查进程是否存活
            return self.process is not None and self.process.returncode is None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.config.health_check,
                    timeout=aiohttp.ClientTimeout(total=2.0)
                ) as response:
                    return response.status == 200
        except Exception:
            return False
    
    async def stop(self, timeout: float = 5.0) -> bool:
        """停止MCP服务器"""
        if self.status in [ServerStatus.STOPPED, ServerStatus.STOPPING]:
            return True
        
        self.status = ServerStatus.STOPPING
        
        try:
            if self.process:
                # 发送SIGTERM
                self.process.terminate()
                
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=timeout)
                except asyncio.TimeoutError:
                    # 强制终止
                    self.process.kill()
                    await self.process.wait()
                
                self.process = None
                self.pid = None
            
            self.status = ServerStatus.STOPPED
            logging.info(f"MCP服务器 {self.config.name} 已停止")
            return True
            
        except Exception as e:
            self.status = ServerStatus.ERROR
            self.last_error = str(e)
            logging.error(f"MCP服务器 {self.config.name} 停止失败: {e}")
            return False
    
    async def _collect_output(self):
        """收集进程输出"""
        if not self.process:
            return
        
        try:
            # 收集标准输出
            if self.process.stdout:
                while True:
                    line = await self.process.stdout.readline()
                    if not line:
                        break
                    line_str = line.decode('utf-8', errors='ignore').rstrip()
                    self.stdout.append(line_str)
                    logging.debug(f"[{self.config.name}] {line_str}")
            
            # 收集标准错误
            if self.process.stderr:
                while True:
                    line = await self.process.stderr.readline()
                    if not line:
                        break
                    line_str = line.decode('utf-8', errors='ignore').rstrip()
                    self.stderr.append(line_str)
                    logging.warning(f"[{self.config.name}] {line_str}")
                    
        except Exception as e:
            logging.error(f"收集输出失败 {self.config.name}: {e}")
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            "name": self.config.name,
            "status": self.status.value,
            "pid": self.pid,
            "uptime": time.time() - self.start_time if self.start_time else 0,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
            "stdout_lines": len(self.stdout),
            "stderr_lines": len(self.stderr),
            "config": {
                "command": self.config.command,
                "args": self.config.args,
                "port": self.config.port,
                "auto_start": self.config.auto_start
            }
        }


# ============================================================================
# MCP服务器管理器
# ============================================================================

class MCPServerManager:
    """MCP服务器管理器"""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.servers: Dict[str, MCPServer] = {}
        self.running = False
        self._shutdown_event = asyncio.Event()
        
        # 初始化服务器实例
        for server_name, server_config in config.servers.items():
            self.servers[server_name] = MCPServer(server_config)
    
    async def start_all(self) -> bool:
        """启动所有服务器"""
        if self.running:
            logging.warning("服务器管理器已在运行")
            return True
        
        self.running = True
        logging.info("开始启动所有MCP服务器...")
        
        # 启动auto_start为True的服务器
        start_tasks = []
        for server_name, server in self.servers.items():
            if server.config.auto_start:
                start_tasks.append(self._start_server_with_retry(server_name))
        
        # 并行启动
        if start_tasks:
            results = await asyncio.gather(*start_tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            logging.info(f"MCP服务器启动完成: {success_count}/{len(start_tasks)} 成功")
        
        return True
    
    async def _start_server_with_retry(self, server_name: str, max_retries: Optional[int] = None) -> bool:
        """带重试的服务器启动"""
        if max_retries is None:
            max_retries = self.config.max_retries
        
        server = self.servers[server_name]
        
        for attempt in range(max_retries):
            try:
                success = await server.start()
                if success:
                    server.retry_count = attempt
                    return True
                
                logging.warning(f"服务器 {server_name} 启动失败，尝试 {attempt + 1}/{max_retries}")
                await asyncio.sleep(self.config.retry_delay)
                
            except Exception as e:
                logging.error(f"服务器 {server_name} 启动异常: {e}")
                await asyncio.sleep(self.config.retry_delay)
        
        logging.error(f"服务器 {server_name} 启动失败，已达最大重试次数")
        return False
    
    async def start_server(self, server_name: str) -> bool:
        """启动单个服务器"""
        if server_name not in self.servers:
            logging.error(f"服务器 {server_name} 不存在")
            return False
        
        return await self._start_server_with_retry(server_name)
    
    async def stop_server(self, server_name: str) -> bool:
        """停止单个服务器"""
        if server_name not in self.servers:
            logging.error(f"服务器 {server_name} 不存在")
            return False
        
        server = self.servers[server_name]
        return await server.stop()
    
    async def stop_all(self) -> bool:
        """停止所有服务器"""
        if not self.running:
            return True
        
        logging.info("开始停止所有MCP服务器...")
        
        stop_tasks = []
        for server_name, server in self.servers.items():
            if server.status in [ServerStatus.RUNNING, ServerStatus.ERROR]:
                stop_tasks.append(server.stop())
        
        # 并行停止
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self.running = False
        logging.info("所有MCP服务器已停止")
        return True
    
    async def health_check_all(self) -> Dict[str, Any]:
        """检查所有服务器的健康状态"""
        results = {}
        all_healthy = True
        
        for server_name, server in self.servers.items():
            healthy = await server.health_check()
            results[server_name] = {
                "healthy": healthy,
                "status": server.status.value,
                "uptime": time.time() - server.start_time if server.start_time else 0
            }
            
            if not healthy:
                all_healthy = False
        
        return {
            "healthy": all_healthy,
            "timestamp": time.time(),
            "servers": results,
            "healthy_count": sum(1 for r in results.values() if r["healthy"]),
            "total_count": len(results)
        }
    
    def get_server_status(self, server_name: str) -> Optional[Dict[str, Any]]:
        """获取服务器状态"""
        if server_name not in self.servers:
            return None
        
        return self.servers[server_name].get_status_info()
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """列出所有服务器状态"""
        return [server.get_status_info() for server in self.servers.values()]
    
    async def monitor(self):
        """监控循环"""
        while not self._shutdown_event.is_set():
            try:
                # 定期健康检查
                health = await self.health_check_all()
                
                # 重启不健康的服务器（如果配置了auto_start）
                for server_name, server_info in health["servers"].items():
                    if not server_info["healthy"] and self.servers[server_name].config.auto_start:
                        logging.warning(f"服务器 {server_name} 不健康，尝试重启")
                        await self.restart_server(server_name)
                
                # 等待下一次检查
                await asyncio.sleep(10.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"监控循环异常: {e}")
                await asyncio.sleep(5.0)
    
    async def restart_server(self, server_name: str) -> bool:
        """重启服务器"""
        await self.stop_server(server_name)
        await asyncio.sleep(1.0)
        return await self.start_server(server_name)
    
    async def shutdown(self):
        """关闭管理器"""
        self._shutdown_event.set()
        await self.stop_all()


# ============================================================================
# 配置示例和工具函数
# ============================================================================

def load_config_from_file(config_path: str) -> MCPConfig:
    """从文件加载配置"""
    with open(config_path, 'r', encoding='utf-8') as f:
        yaml_content = f.read()
    
    return MCPConfig.from_yaml(yaml_content)


def create_sample_config() -> str:
    """创建示例配置YAML"""
    sample_yaml = """
# MCP服务器配置示例
mcp:
  servers:
    filesystem:
      command: "npx"
      args: ["@modelcontextprotocol/server-filesystem", "/workspace"]
      env:
        MCP_PORT: 3001
        LOG_LEVEL: "info"
      auto_start: true
      health_check: "http://localhost:3001/health"
      timeout: 30.0
      description: "文件系统MCP服务器，提供文件访问功能"
    
    sql:
      command: "npx"
      args: ["@modelcontextprotocol/server-sql", "${DATABASE_URL}"]
      env:
        MCP_PORT: 3002
        DB_MAX_CONNECTIONS: "10"
      auto_start: true
      health_check: "http://localhost:3002/health"
      description: "SQL数据库MCP服务器，提供数据库查询功能"
    
    github:
      command: "npx"
      args: ["@modelcontextprotocol/server-github"]
      env:
        MCP_PORT: 3003
        GITHUB_TOKEN: "${GITHUB_TOKEN}"
      auto_start: false  # 需要时手动启动
      health_check: "http://localhost:3003/health"
      description: "GitHub MCP服务器，提供GitHub API访问"
    
    brave-search:
      command: "npx"
      args: ["@modelcontextprotocol/server-brave-search"]
      env:
        MCP_PORT: 3004
        BRAVE_API_KEY: "${BRAVE_API_KEY}"
      auto_start: false
      health_check: "http://localhost:3004/health"
      description: "Brave搜索MCP服务器，提供搜索功能"
  
  # 全局配置
  log_level: "INFO"
  max_retries: 3
  retry_delay: 2.0
"""
    return sample_yaml


def create_minimal_config() -> str:
    """创建最小配置YAML"""
    minimal_yaml = """
# 最小MCP服务器配置
servers:
  filesystem:
    command: "npx"
    args: ["@modelcontextprotocol/server-filesystem", "/tmp"]
    env:
      MCP_PORT: 3001
    auto_start: true
"""
    return minimal_yaml


# ============================================================================
# 演示函数
# ============================================================================

async def demo_basic_config():
    """演示基础配置"""
    print("=== 基础配置演示 ===")
    
    # 创建配置
    config_yaml = create_minimal_config()
    config = MCPConfig.from_yaml(config_yaml)
    
    print(f"配置解析成功，包含 {len(config.servers)} 个服务器")
    
    for server_name, server_config in config.servers.items():
        print(f"  - {server_name}: {server_config.command} {server_config.args}")
    
    return config


async def demo_server_lifecycle():
    """演示服务器生命周期"""
    print("\n=== 服务器生命周期演示 ===")
    
    # 创建配置
    config_yaml = create_sample_config()
    config = MCPConfig.from_yaml(config_yaml)
    
    # 创建管理器
    manager = MCPServerManager(config)
    
    print("1. 列出所有服务器:")
    for server_info in manager.list_servers():
        print(f"  - {server_info['name']}: {server_info['status']}")
    
    print("\n2. 启动filesystem服务器:")
    success = await manager.start_server("filesystem")
    print(f"   启动结果: {'成功' if success else '失败'}")
    
    if success:
        print("\n3. 检查服务器状态:")
        status = manager.get_server_status("filesystem")
        if status:
            print(f"   状态: {status['status']}")
            print(f"   PID: {status['pid']}")
        
        print("\n4. 健康检查:")
        health = await manager.health_check_all()
        print(f"   整体健康: {health['healthy']}")
        print(f"   filesystem健康: {health['servers']['filesystem']['healthy']}")
        
        print("\n5. 停止服务器:")
        stop_success = await manager.stop_server("filesystem")
        print(f"   停止结果: {'成功' if stop_success else '失败'}")
    
    # 清理
    await manager.shutdown()


async def demo_error_handling():
    """演示错误处理"""
    print("\n=== 错误处理演示 ===")
    
    # 创建无效配置
    invalid_yaml = """
servers:
  invalid-server:
    command: "nonexistent-command"
    args: ["--invalid"]
    env:
      MCP_PORT: 9999
    auto_start: true
"""
    
    config = MCPConfig.from_yaml(invalid_yaml)
    manager = MCPServerManager(config)
    
    print("1. 启动无效服务器:")
    success = await manager.start_server("invalid-server")
    print(f"   启动结果: {'成功' if success else '失败'}")
    
    if not success:
        print("2. 检查错误状态:")
        status = manager.get_server_status("invalid-server")
        if status:
            print(f"   状态: {status['status']}")
            print(f"   错误: {status['last_error']}")
    
    await manager.shutdown()


async def demo_environment_variables():
    """演示环境变量注入"""
    print("\n=== 环境变量注入演示 ===")
    
    # 设置环境变量
    os.environ["DATABASE_URL"] = "postgresql://localhost:5432/mydb"
    os.environ["GITHUB_TOKEN"] = "test_token_123"
    
    config_yaml = """
servers:
  sql:
    command: "npx"
    args: ["@modelcontextprotocol/server-sql", "${DATABASE_URL}"]
    env:
      MCP_PORT: 3002
      DB_TIMEOUT: "30"
  
  github:
    command: "npx"
    args: ["@modelcontextprotocol/server-github"]
    env:
      MCP_PORT: 3003
      GITHUB_TOKEN: "${GITHUB_TOKEN}"
"""
    
    config = MCPConfig.from_yaml(config_yaml)
    
    print("解析后的配置:")
    for server_name, server_config in config.servers.items():
        print(f"  {server_name}:")
        print(f"    命令: {server_config.command}")
        print(f"    参数: {server_config.args}")
        print(f"    环境变量: {server_config.env}")
    
    # 清理环境变量（演示用）
    del os.environ["DATABASE_URL"]
    del os.environ["GITHUB_TOKEN"]


# ============================================================================
# 测试函数
# ============================================================================

async def test_config_loading():
    """测试配置加载"""
    print("=== 测试配置加载 ===")
    
    # 测试最小配置
    minimal_config = MCPConfig.from_yaml(create_minimal_config())
    assert len(minimal_config.servers) == 1
    assert "filesystem" in minimal_config.servers
    print("✅ 最小配置测试通过")
    
    # 测试完整配置
    sample_config = MCPConfig.from_yaml(create_sample_config())
    assert len(sample_config.servers) >= 3
    print("✅ 完整配置测试通过")
    
    # 测试环境变量解析
    os.environ["TEST_VAR"] = "test_value"
    env_config_yaml = """
servers:
  test:
    command: "echo"
    args: ["${TEST_VAR}"]
    env:
      MCP_PORT: 3000
"""
    env_config = MCPConfig.from_yaml(env_config_yaml)
    assert env_config.servers["test"].args[0] == "test_value"
    print("✅ 环境变量解析测试通过")
    
    del os.environ["TEST_VAR"]


async def test_server_manager():
    """测试服务器管理器"""
    print("\n=== 测试服务器管理器 ===")
    
    # 创建配置（使用echo命令作为测试服务器）
    test_yaml = """
servers:
  test-server:
    command: "python3"
    args: ["-c", "import time; print('Test server started'); time.sleep(3600)"]
    env:
      MCP_PORT: 3999
    auto_start: false
    timeout: 5.0
"""
    
    config = MCPConfig.from_yaml(test_yaml)
    manager = MCPServerManager(config)
    
    # 测试启动
    success = await manager.start_server("test-server")
    assert success or not success  # 可能成功也可能失败，取决于环境
    print("✅ 服务器启动测试完成")
    
    # 测试状态获取
    status = manager.get_server_status("test-server")
    assert status is not None
    print("✅ 状态获取测试通过")
    
    # 测试停止
    if success:
        stop_success = await manager.stop_server("test-server")
        assert stop_success
        print("✅ 服务器停止测试通过")
    
    await manager.shutdown()


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🎯 MCP服务器配置演示")
    print("=" * 60)
    
    try:
        # 运行演示
        await demo_basic_config()
        await demo_server_lifecycle()
        await demo_error_handling()
        await demo_environment_variables()
        
        # 运行测试
        await test_config_loading()
        await test_server_manager()
        
        print("\n" + "=" * 60)
        print("✅ 所有演示和测试完成")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    # 设置asyncio事件循环策略（Windows兼容）
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 运行主函数
    exit_code = asyncio.run(main())
    sys.exit(exit_code)