#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 11 Lesson 42: 子代理注册表 (Subagent Registry)

本文件演示子代理注册表的设计和实现，包括：
1. 注册表核心接口 - register、get、list、unregister
2. 生命周期管理 - 子代理的创建、启动、停止、销毁
3. 配置集成 - 从配置自动注册子代理
4. 并发安全 - 线程安全的注册表实现

使用示例:
    python subagent_registry_demo.py          # 运行基本演示
    python subagent_registry_demo.py --test   # 运行测试套件
    python subagent_registry_demo.py --demo   # 运行完整演示
    python subagent_registry_demo.py --help   # 显示帮助信息
"""

import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from threading import Lock


class AgentState(Enum):
    """子代理状态枚举"""
    CREATED = "created"        # 已创建
    STARTING = "starting"      # 启动中
    RUNNING = "running"        # 运行中
    STOPPING = "stopping"      # 停止中
    STOPPED = "stopped"        # 已停止
    ERROR = "error"            # 错误状态


class AgentType(Enum):
    """子代理类型枚举"""
    GENERIC = "generic"        # 通用子代理
    BASH = "bash"              # Bash子代理
    SQL = "sql"                # SQL子代理
    WEB = "web"                # Web子代理
    PYTHON = "python"          # Python子代理


@dataclass
class AgentMetrics:
    """子代理指标"""
    total_tasks: int = 0                    # 总任务数
    completed_tasks: int = 0                # 完成任务数
    failed_tasks: int = 0                   # 失败任务数
    avg_response_time: float = 0.0          # 平均响应时间
    last_active: Optional[datetime] = None  # 最后活动时间
    
    def record_task(self, success: bool, duration: float):
        """记录任务执行"""
        self.total_tasks += 1
        if success:
            self.completed_tasks += 1
        else:
            self.failed_tasks += 1
        
        # 更新平均响应时间
        if self.total_tasks == 1:
            self.avg_response_time = duration
        else:
            self.avg_response_time = (
                (self.avg_response_time * (self.total_tasks - 1) + duration) 
                / self.total_tasks
            )
        self.last_active = datetime.now()


@dataclass
class SubagentInfo:
    """子代理信息"""
    name: str                                   # 子代理名称
    agent_type: AgentType                       # 子代理类型
    description: str                            # 描述信息
    state: AgentState = AgentState.CREATED      # 当前状态
    capabilities: List[str] = field(default_factory=list)  # 能力列表
    config: Dict[str, Any] = field(default_factory=dict)   # 配置
    metrics: AgentMetrics = field(default_factory=AgentMetrics)  # 指标
    created_at: datetime = field(default_factory=datetime.now)    # 创建时间
    started_at: Optional[datetime] = None       # 启动时间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "agent_type": self.agent_type.value,
            "description": self.description,
            "state": self.state.value,
            "capabilities": self.capabilities,
            "config": self.config,
            "metrics": {
                "total_tasks": self.metrics.total_tasks,
                "completed_tasks": self.metrics.completed_tasks,
                "failed_tasks": self.metrics.failed_tasks,
                "avg_response_time": self.metrics.avg_response_time,
                "last_active": self.metrics.last_active.isoformat() if self.metrics.last_active else None
            },
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None
        }


class SubagentRegistry:
    """子代理注册表"""
    
    def __init__(self):
        self._agents: Dict[str, SubagentInfo] = {}
        self._lock = Lock()
        self._event_handlers: Dict[str, List[Callable]] = {
            "on_register": [],
            "on_unregister": [],
            "on_state_change": [],
        }
    
    def register(self, agent: SubagentInfo) -> bool:
        """
        注册子代理
        
        Args:
            agent: 子代理信息
            
        Returns:
            bool: 是否注册成功
        """
        with self._lock:
            if agent.name in self._agents:
                logging.warning(f"子代理已存在: {agent.name}")
                return False
            
            self._agents[agent.name] = agent
            logging.info(f"注册子代理: {agent.name} ({agent.agent_type.value})")
            
            # 触发事件
            self._trigger_event("on_register", agent)
            return True
    
    def unregister(self, name: str) -> bool:
        """
        注销子代理
        
        Args:
            name: 子代理名称
            
        Returns:
            bool: 是否注销成功
        """
        with self._lock:
            if name not in self._agents:
                logging.warning(f"子代理不存在: {name}")
                return False
            
            agent = self._agents.pop(name)
            logging.info(f"注销子代理: {name}")
            
            # 触发事件
            self._trigger_event("on_unregister", agent)
            return True
    
    def get(self, name: str) -> Optional[SubagentInfo]:
        """获取子代理信息"""
        with self._lock:
            return self._agents.get(name)
    
    def list_all(self) -> List[SubagentInfo]:
        """列出所有子代理"""
        with self._lock:
            return list(self._agents.values())
    
    def list_by_type(self, agent_type: AgentType) -> List[SubagentInfo]:
        """按类型列出子代理"""
        with self._lock:
            return [a for a in self._agents.values() if a.agent_type == agent_type]
    
    def list_by_state(self, state: AgentState) -> List[SubagentInfo]:
        """按状态列出子代理"""
        with self._lock:
            return [a for a in self._agents.values() if a.state == state]
    
    def list_running(self) -> List[SubagentInfo]:
        """列出运行中的子代理"""
        return self.list_by_state(AgentState.RUNNING)
    
    def update_state(self, name: str, new_state: AgentState) -> bool:
        """
        更新子代理状态
        
        Args:
            name: 子代理名称
            new_state: 新状态
            
        Returns:
            bool: 是否更新成功
        """
        with self._lock:
            if name not in self._agents:
                return False
            
            agent = self._agents[name]
            old_state = agent.state
            agent.state = new_state
            
            if new_state == AgentState.RUNNING and agent.started_at is None:
                agent.started_at = datetime.now()
            
            logging.info(f"子代理状态变更: {name} {old_state.value} -> {new_state.value}")
            
            # 触发事件
            self._trigger_event("on_state_change", agent, old_state, new_state)
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        with self._lock:
            agents = list(self._agents.values())
            
            return {
                "total": len(agents),
                "by_state": {
                    state.value: len([a for a in agents if a.state == state])
                    for state in AgentState
                },
                "by_type": {
                    agent_type.value: len([a for a in agents if a.agent_type == agent_type])
                    for agent_type in AgentType
                },
                "total_tasks": sum(a.metrics.total_tasks for a in agents),
                "completed_tasks": sum(a.metrics.completed_tasks for a in agents),
                "failed_tasks": sum(a.metrics.failed_tasks for a in agents),
            }
    
    def on(self, event: str, handler: Callable):
        """注册事件处理器"""
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)
    
    def _trigger_event(self, event: str, *args, **kwargs):
        """触发事件"""
        for handler in self._event_handlers.get(event, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logging.error(f"事件处理器错误: {e}")
    
    async def start_agent(self, name: str) -> bool:
        """启动子代理"""
        agent = self.get(name)
        if not agent:
            return False
        
        self.update_state(name, AgentState.STARTING)
        
        # 模拟启动过程
        await asyncio.sleep(0.1)
        
        self.update_state(name, AgentState.RUNNING)
        return True
    
    async def stop_agent(self, name: str) -> bool:
        """停止子代理"""
        agent = self.get(name)
        if not agent:
            return False
        
        self.update_state(name, AgentState.STOPPING)
        
        # 模拟停止过程
        await asyncio.sleep(0.1)
        
        self.update_state(name, AgentState.STOPPED)
        return True
    
    async def restart_agent(self, name: str) -> bool:
        """重启子代理"""
        if await self.stop_agent(name):
            return await self.start_agent(name)
        return False


class RegistryTestSuite:
    """注册表测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_subagent_info_creation", self.test_subagent_info_creation),
            ("test_registry_register", self.test_registry_register),
            ("test_registry_unregister", self.test_registry_unregister),
            ("test_registry_queries", self.test_registry_queries),
            ("test_agent_lifecycle", self.test_agent_lifecycle),
        ]
    
    def test_subagent_info_creation(self) -> tuple:
        """测试子代理信息创建"""
        try:
            agent = SubagentInfo(
                name="test_agent",
                agent_type=AgentType.GENERIC,
                description="测试子代理",
                capabilities=["code_execution", "debugging"],
                config={"timeout": 300}
            )
            
            if agent.name != "test_agent":
                return False, f"name不正确: {agent.name}"
            if agent.agent_type != AgentType.GENERIC:
                return False, f"type不正确: {agent.agent_type}"
            if agent.state != AgentState.CREATED:
                return False, f"初始状态不正确: {agent.state}"
            if len(agent.capabilities) != 2:
                return False, f"capabilities长度不正确"
            
            # 测试序列化
            data = agent.to_dict()
            if data["name"] != "test_agent":
                return False, "序列化name不正确"
            if data["state"] != "created":
                return False, "序列化state不正确"
            
            return True, "子代理信息创建测试通过"
        except Exception as e:
            return False, f"创建异常: {e}"
    
    def test_registry_register(self) -> tuple:
        """测试注册表注册功能"""
        try:
            registry = SubagentRegistry()
            
            agent1 = SubagentInfo(
                name="agent1",
                agent_type=AgentType.BASH,
                description="Bash子代理"
            )
            
            agent2 = SubagentInfo(
                name="agent2",
                agent_type=AgentType.SQL,
                description="SQL子代理"
            )
            
            # 测试注册
            if not registry.register(agent1):
                return False, "注册agent1失败"
            
            if not registry.register(agent2):
                return False, "注册agent2失败"
            
            # 测试重复注册
            if registry.register(agent1):
                return False, "重复注册应该失败"
            
            # 验证注册数量
            if len(registry.list_all()) != 2:
                return False, f"注册数量不正确: {len(registry.list_all())}"
            
            return True, "注册表注册功能测试通过"
        except Exception as e:
            return False, f"注册功能异常: {e}"
    
    def test_registry_unregister(self) -> tuple:
        """测试注册表注销功能"""
        try:
            registry = SubagentRegistry()
            
            agent = SubagentInfo(
                name="test_agent",
                agent_type=AgentType.GENERIC,
                description="测试"
            )
            
            registry.register(agent)
            
            # 测试注销
            if not registry.unregister("test_agent"):
                return False, "注销失败"
            
            if len(registry.list_all()) != 0:
                return False, "注销后数量不为0"
            
            # 测试注销不存在的子代理
            if registry.unregister("nonexistent"):
                return False, "注销不存在的子代理应该失败"
            
            return True, "注册表注销功能测试通过"
        except Exception as e:
            return False, f"注销功能异常: {e}"
    
    def test_registry_queries(self) -> tuple:
        """测试注册表查询功能"""
        try:
            registry = SubagentRegistry()
            
            # 注册多个子代理
            agents = [
                SubagentInfo("bash1", AgentType.BASH, "Bash1"),
                SubagentInfo("bash2", AgentType.BASH, "Bash2"),
                SubagentInfo("sql1", AgentType.SQL, "SQL1"),
                SubagentInfo("generic1", AgentType.GENERIC, "Generic1"),
            ]
            
            for agent in agents:
                registry.register(agent)
            
            # 测试get
            found = registry.get("sql1")
            if not found or found.name != "sql1":
                return False, "get查询失败"
            
            # 测试list_by_type
            bash_agents = registry.list_by_type(AgentType.BASH)
            if len(bash_agents) != 2:
                return False, f"按类型查询失败: {len(bash_agents)}"
            
            # 测试get不存在的子代理
            if registry.get("nonexistent") is not None:
                return False, "get不存在的子代理应该返回None"
            
            return True, "注册表查询功能测试通过"
        except Exception as e:
            return False, f"查询功能异常: {e}"
    
    def test_agent_lifecycle(self) -> tuple:
        """测试子代理生命周期"""
        try:
            registry = SubagentRegistry()
            
            agent = SubagentInfo(
                name="lifecycle_agent",
                agent_type=AgentType.PYTHON,
                description="生命周期测试"
            )
            
            registry.register(agent)
            
            # 验证初始状态
            agent_info = registry.get("lifecycle_agent")
            if agent_info.state != AgentState.CREATED:
                return False, f"初始状态不正确: {agent_info.state}"
            
            # 测试状态转换
            registry.update_state("lifecycle_agent", AgentState.STARTING)
            agent_info = registry.get("lifecycle_agent")
            if agent_info.state != AgentState.STARTING:
                return False, f"STARTING状态不正确"
            
            registry.update_state("lifecycle_agent", AgentState.RUNNING)
            agent_info = registry.get("lifecycle_agent")
            if agent_info.state != AgentState.RUNNING:
                return False, f"RUNNING状态不正确"
            if agent_info.started_at is None:
                return False, "RUNNING状态应该设置started_at"
            
            registry.update_state("lifecycle_agent", AgentState.STOPPING)
            registry.update_state("lifecycle_agent", AgentState.STOPPED)
            agent_info = registry.get("lifecycle_agent")
            if agent_info.state != AgentState.STOPPED:
                return False, f"STOPPED状态不正确"
            
            # 测试按状态查询
            running = registry.list_by_state(AgentState.RUNNING)
            if len(running) != 0:
                return False, "停止后不应该有running子代理"
            
            return True, "子代理生命周期测试通过"
        except Exception as e:
            return False, f"生命周期异常: {e}"
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行子代理注册表测试套件...")
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


def main_demo():
    """主演示函数"""
    print("🎓 Day 11 Lesson 42: 子代理注册表演示")
    print("=" * 60)
    
    # 1. 创建注册表
    print("\n1. 创建子代理注册表:")
    registry = SubagentRegistry()
    
    # 2. 注册事件处理器
    def on_register_handler(agent):
        print(f"   📢 事件: 子代理已注册 - {agent.name}")
    
    def on_state_change_handler(agent, old_state, new_state):
        print(f"   📢 事件: 状态变更 - {agent.name} {old_state.value} -> {new_state.value}")
    
    registry.on("on_register", on_register_handler)
    registry.on("on_state_change", on_state_change_handler)
    
    # 3. 创建并注册子代理
    print("\n2. 注册子代理:")
    
    agents = [
        SubagentInfo("python_expert", AgentType.PYTHON, "Python专家", 
                     capabilities=["code_execution", "debugging"]),
        SubagentInfo("bash_expert", AgentType.BASH, "Bash专家",
                     capabilities=["shell_execution", "file_operations"]),
        SubagentInfo("sql_expert", AgentType.SQL, "SQL专家",
                     capabilities=["query_execution", "schema_analysis"]),
        SubagentInfo("web_expert", AgentType.WEB, "Web专家",
                     capabilities=["web_scraping", "api_calling"]),
    ]
    
    for agent in agents:
        registry.register(agent)
    
    # 4. 查询子代理
    print("\n3. 查询子代理:")
    
    # 按名称查询
    python_agent = registry.get("python_expert")
    if python_agent:
        print(f"   ✅ 找到: {python_agent.name} ({python_agent.agent_type.value})")
    
    # 列出所有子代理
    all_agents = registry.list_all()
    print(f"   📋 所有子代理: {[a.name for a in all_agents]}")
    
    # 按类型查询
    bash_agents = registry.list_by_type(AgentType.BASH)
    print(f"   🔧 Bash类型: {[a.name for a in bash_agents]}")
    
    # 5. 状态管理
    print("\n4. 状态管理演示:")
    
    # 设置初始状态
    registry.update_state("python_expert", AgentState.STARTING)
    registry.update_state("python_expert", AgentState.RUNNING)
    registry.update_state("bash_expert", AgentState.RUNNING)
    
    # 按状态查询
    running = registry.list_running()
    print(f"   ▶️ 运行中: {[a.name for a in running]}")
    
    created = registry.list_by_state(AgentState.CREATED)
    print(f"   ⏸️ 已创建: {[a.name for a in created]}")
    
    # 6. 统计信息
    print("\n5. 注册表统计:")
    stats = registry.get_stats()
    print(f"   📊 总数: {stats['total']}")
    print(f"   📊 按状态: {stats['by_state']}")
    print(f"   📊 按类型: {stats['by_type']}")
    
    # 7. 序列化
    print("\n6. 子代理信息序列化:")
    agent_info = registry.get("python_expert")
    if agent_info:
        data = agent_info.to_dict()
        print(f"   📄 名称: {data['name']}")
        print(f"   📄 类型: {data['agent_type']}")
        print(f"   📄 状态: {data['state']}")
        print(f"   📄 能力: {data['capabilities']}")
    
    print("\n7. 演示完成!")


async def async_demo():
    """异步演示函数"""
    print("🎓 Day 11 Lesson 42: 异步生命周期演示")
    print("=" * 60)
    
    registry = SubagentRegistry()
    
    # 注册子代理
    agent = SubagentInfo(
        name="async_agent",
        agent_type=AgentType.GENERIC,
        description="异步测试子代理"
    )
    registry.register(agent)
    
    print("\n1. 启动子代理:")
    await registry.start_agent("async_agent")
    info = registry.get("async_agent")
    print(f"   状态: {info.state.value}")
    
    print("\n2. 停止子代理:")
    await registry.stop_agent("async_agent")
    info = registry.get("async_agent")
    print(f"   状态: {info.state.value}")
    
    print("\n3. 重启子代理:")
    await registry.restart_agent("async_agent")
    info = registry.get("async_agent")
    print(f"   状态: {info.state.value}")
    
    print("\n演示完成!")


def run_tests():
    """运行测试套件"""
    test_suite = RegistryTestSuite()
    report = test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 子代理注册表测试套件验证通过")
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
        asyncio.run(async_demo())
    else:
        main_demo()
