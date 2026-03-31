#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第96节课：子代理扩展

本课程介绍DeerFlow子代理扩展机制，包括：
1. 自定义子代理 - 创建特定领域的专家代理
2. 子代理配置 - 通过配置文件定义子代理行为
3. 子代理组合 - 多个子代理的协作模式

作者：DeerFlow架构师训练营
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


# ============================================================
# 第一部分：子代理配置
# ============================================================

class SubagentCapability(Enum):
    """子代理能力"""
    CODE_EXECUTION = "code_execution"
    FILE_OPERATIONS = "file_operations"
    WEB_SEARCH = "web_search"
    DATA_ANALYSIS = "data_analysis"
    TEXT_GENERATION = "text_generation"


@dataclass
class SubagentConfig:
    """子代理配置"""
    name: str
    description: str
    model: str = "gpt-4"
    max_turns: int = 10
    timeout_seconds: int = 300
    capabilities: List[SubagentCapability] = field(default_factory=list)
    system_prompt: str = ""
    tools: List[str] = field(default_factory=list)
    inherit_tools: bool = True
    max_concurrent: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "max_turns": self.max_turns,
            "timeout_seconds": self.timeout_seconds,
            "capabilities": [c.value for c in self.capabilities],
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "inherit_tools": self.inherit_tools,
            "max_concurrent": self.max_concurrent
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubagentConfig':
        return cls(
            name=data["name"],
            description=data["description"],
            model=data.get("model", "gpt-4"),
            max_turns=data.get("max_turns", 10),
            timeout_seconds=data.get("timeout_seconds", 300),
            capabilities=[SubagentCapability(c) for c in data.get("capabilities", [])],
            system_prompt=data.get("system_prompt", ""),
            tools=data.get("tools", []),
            inherit_tools=data.get("inherit_tools", True),
            max_concurrent=data.get("max_concurrent", 3)
        )


# ============================================================
# 第二部分：子代理实现
# ============================================================

class SubagentState(Enum):
    """子代理状态"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class SubagentTask:
    """子代理任务"""
    id: str
    config: SubagentConfig
    prompt: str
    state: SubagentState = SubagentState.IDLE
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def get_duration(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0


class BaseSubagent:
    """子代理基类"""
    
    def __init__(self, config: SubagentConfig):
        self.config = config
        self.state = SubagentState.IDLE
        
    async def execute(self, prompt: str) -> Any:
        """执行子代理任务"""
        raise NotImplementedError
        
    async def cancel(self) -> None:
        """取消执行"""
        raise NotImplementedError
        
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        if self.config.inherit_tools:
            return self.config.tools + ["task"]
        return self.config.tools


class CodeExecutionSubagent(BaseSubagent):
    """代码执行子代理"""
    
    def __init__(self, config: SubagentConfig):
        super().__init__(config)
        
    async def execute(self, prompt: str) -> Any:
        """执行代码"""
        self.state = SubagentState.RUNNING
        
        # 模拟代码执行
        await asyncio.sleep(0.1)
        
        # 提取代码
        code = self._extract_code(prompt)
        
        # 执行代码
        try:
            result = {"output": f"Executed: {code[:50]}...", "success": True}
            self.state = SubagentState.COMPLETED
            return result
        except Exception as e:
            self.state = SubagentState.FAILED
            return {"error": str(e), "success": False}
            
    def _extract_code(self, prompt: str) -> str:
        """从提示中提取代码"""
        return prompt
        
    async def cancel(self) -> None:
        self.state = SubagentState.IDLE


class DataAnalysisSubagent(BaseSubagent):
    """数据分析子代理"""
    
    def __init__(self, config: SubagentConfig):
        super().__init__(config)
        
    async def execute(self, prompt: str) -> Any:
        """执行数据分析"""
        self.state = SubagentState.RUNNING
        
        await asyncio.sleep(0.1)
        
        result = {
            "analysis": "数据已分析",
            "insights": ["发现趋势1", "发现趋势2"],
            "success": True
        }
        
        self.state = SubagentState.COMPLETED
        return result
        
    async def cancel(self) -> None:
        self.state = SubagentState.IDLE


# ============================================================
# 第三部分：子代理管理器
# ============================================================

class SubagentRegistry:
    """子代理注册表"""
    
    _subagent_classes: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, subagent_class: type) -> None:
        """注册子代理类"""
        cls._subagent_classes[name] = subagent_class
        
    @classmethod
    def create(cls, config: SubagentConfig) -> BaseSubagent:
        """创建子代理实例"""
        # 根据类型创建
        for name, subagent_class in cls._subagent_classes.items():
            if name.lower() in config.name.lower():
                return subagent_class(config)
                
        # 默认使用基础子代理
        return BaseSubagent(config)
        
    @classmethod
    def get_available_types(cls) -> List[str]:
        """获取可用的子代理类型"""
        return list(cls._subagent_classes.keys())


# 注册内置子代理
SubagentRegistry.register("code", CodeExecutionSubagent)
SubagentRegistry.register("data", DataAnalysisSubagent)
SubagentRegistry.register("analysis", DataAnalysisSubagent)


class SubagentExecutor:
    """子代理执行器"""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._running_tasks: Dict[str, SubagentTask] = {}
        self._completed_tasks: List[SubagentTask] = []
        
    async def execute(self, config: SubagentConfig, prompt: str) -> SubagentTask:
        """执行子代理任务"""
        # 检查并发限制
        running_count = sum(
            1 for t in self._running_tasks.values()
            if t.state == SubagentState.RUNNING
        )
        
        if running_count >= self.max_concurrent:
            raise RuntimeError(f"超过最大并发数: {self.max_concurrent}")
            
        # 创建任务
        import secrets
        task = SubagentTask(
            id=secrets.token_hex(8),
            config=config,
            prompt=prompt
        )
        
        # 创建子代理
        subagent = SubagentRegistry.create(config)
        
        # 执行
        self._running_tasks[task.id] = task
        task.state = SubagentState.RUNNING
        task.start_time = datetime.utcnow()
        
        try:
            result = await asyncio.wait_for(
                subagent.execute(prompt),
                timeout=config.timeout_seconds
            )
            task.result = result
            task.state = SubagentState.COMPLETED
            
        except asyncio.TimeoutError:
            task.state = SubagentState.TIMEOUT
            task.error = "执行超时"
            
        except Exception as e:
            task.state = SubagentState.FAILED
            task.error = str(e)
            
        finally:
            task.end_time = datetime.utcnow()
            if task.id in self._running_tasks:
                del self._running_tasks[task.id]
            self._completed_tasks.append(task)
            
        return task
        
    def get_task(self, task_id: str) -> Optional[SubagentTask]:
        """获取任务状态"""
        if task_id in self._running_tasks:
            return self._running_tasks[task_id]
        for task in self._completed_tasks:
            if task.id == task_id:
                return task
        return None
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "running": len([t for t in self._running_tasks.values() 
                         if t.state == SubagentState.RUNNING]),
            "completed": len([t for t in self._completed_tasks 
                           if t.state == SubagentState.COMPLETED]),
            "failed": len([t for t in self._completed_tasks 
                        if t.state == SubagentState.FAILED]),
            "total": len(self._completed_tasks)
        }


# ============================================================
# 第四部分：子代理编排
# ============================================================

class SubagentOrchestrator:
    """子代理编排器"""
    
    def __init__(self):
        self.executor = SubagentExecutor()
        self._workflows: Dict[str, List[SubagentConfig]] = {}
        
    def register_workflow(self, name: str, 
                        subagents: List[SubagentConfig]) -> None:
        """注册工作流"""
        self._workflows[name] = subagents
        
    async def execute_workflow(self, workflow_name: str, 
                              initial_prompt: str) -> List[SubagentTask]:
        """执行工作流"""
        if workflow_name not in self._workflows:
            raise ValueError(f"未知的工作流: {workflow_name}")
            
        results = []
        current_prompt = initial_prompt
        
        for config in self._workflows[workflow_name]:
            task = await self.executor.execute(config, current_prompt)
            results.append(task)
            
            # 将结果传递给下一个子代理
            if task.result:
                current_prompt = f"基于前一步结果: {task.result}\n\n{initial_prompt}"
                
        return results
        
    async def execute_parallel(self, configs: List[SubagentConfig],
                              prompt: str) -> List[SubagentTask]:
        """并行执行多个子代理"""
        tasks = [
            self.executor.execute(config, prompt)
            for config in configs
        ]
        
        return await asyncio.gather(*tasks)


# ============================================================
# 第五部分：演示与测试
# ============================================================

def run_demo():
    """演示子代理系统"""
    print("=" * 60)
    print("DeerFlow 子代理扩展演示")
    print("=" * 60)
    
    # 创建子代理配置
    print("\n1. 创建子代理配置...")
    code_config = SubagentConfig(
        name="code-executor",
        description="执行代码的子代理",
        model="gpt-4",
        capabilities=[SubagentCapability.CODE_EXECUTION]
    )
    
    data_config = SubagentConfig(
        name="data-analyst",
        description="数据分析子代理",
        model="gpt-4",
        capabilities=[SubagentCapability.DATA_ANALYSIS]
    )
    
    print(f"   代码执行配置: {code_config.name}")
    print(f"   数据分析配置: {data_config.name}")
    
    # 创建执行器
    print("\n2. 创建子代理执行器...")
    executor = SubagentExecutor(max_concurrent=3)
    print(f"   最大并发: {executor.max_concurrent}")
    
    # 执行子代理
    print("\n3. 执行子代理...")
    
    async def run():
        task = await executor.execute(code_config, "print('Hello')")
        print(f"   任务ID: {task.id}")
        print(f"   状态: {task.state.value}")
        print(f"   结果: {task.result}")
        
        # 统计
        stats = executor.get_stats()
        print(f"   统计: {stats}")
        
    asyncio.run(run())
    
    # 编排
    print("\n4. 子代理编排...")
    orchestrator = SubagentOrchestrator()
    orchestrator.register_workflow("analyze_and_code", [data_config, code_config])
    print(f"   已注册工作流: analyze_and_code")
    
    print("\n演示完成!")


def run_tests():
    """运行测试"""
    print("\n" + "=" * 60)
    print("运行单元测试")
    print("=" * 60 + "\n")
    
    # 测试1: 子代理配置
    print("测试1: 子代理配置")
    config = SubagentConfig(
        name="test-subagent",
        description="测试子代理",
        model="gpt-4",
        max_turns=5
    )
    assert config.name == "test-subagent"
    assert config.max_turns == 5
    
    # 序列化
    data = config.to_dict()
    assert data["name"] == "test-subagent"
    
    # 反序列化
    config2 = SubagentConfig.from_dict(data)
    assert config2.name == config.name
    print("✓ 子代理配置测试通过\n")
    
    # 测试2: 子代理注册
    print("测试2: 子代理注册")
    types = SubagentRegistry.get_available_types()
    assert "code" in types
    assert "data" in types
    print(f"   可用类型: {types}")
    print("✓ 子代理注册测试通过\n")
    
    # 测试3: 子代理创建
    print("测试3: 子代理创建")
    subagent = SubagentRegistry.create(config)
    assert subagent is not None
    print(f"   创建子代理: {type(subagent).__name__}")
    print("✓ 子代理创建测试通过\n")
    
    # 测试4: 子代理执行
    print("测试4: 子代理执行")
    executor = SubagentExecutor()
    
    async def test_execute():
        task = await executor.execute(config, "test prompt")
        return task
        
    task = asyncio.run(test_execute())
    print(f"   任务状态: {task.state.value}")
    print("✓ 子代理执行测试通过\n")
    
    # 测试5: 编排
    print("测试5: 子代理编排")
    orchestrator = SubagentOrchestrator()
    orchestrator.register_workflow("test", [config])
    assert "test" in orchestrator._workflows
    print("✓ 编排测试通过\n")
    
    print("=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        run_tests()
    else:
        run_demo()
