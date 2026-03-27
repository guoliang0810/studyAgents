#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 11 Lesson 43: 通用目的子代理 (Generic Purpose Subagent)

本文件演示通用目的子代理的设计和实现，包括：
1. 子代理基类 - Subagent抽象基类定义
2. 通用子代理 - GenericSubagent实现三阶段执行流程
3. 任务类型 - 支持代码执行、数据分析、API调用等多种任务
4. 执行上下文 - 执行环境管理和资源清理

使用示例:
    python generic_subagent_demo.py          # 运行基本演示
    python generic_subagent_demo.py --test   # 运行测试套件
    python generic_subagent_demo.py --demo   # 运行完整演示
    python generic_subagent_demo.py --help   # 显示帮助信息
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import uuid


class TaskType(Enum):
    """任务类型枚举"""
    CODE_EXECUTION = "code_execution"      # 代码执行
    DATA_ANALYSIS = "data_analysis"        # 数据分析
    API_CALL = "api_call"                  # API调用
    FILE_OPERATION = "file_operation"      # 文件操作
    TEXT_PROCESSING = "text_processing"    # 文本处理


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"        # 等待中
    RUNNING = "running"        # 运行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消


class SandboxStatus(Enum):
    """沙箱状态枚举"""
    CREATED = "created"        # 已创建
    INITIALIZED = "initialized"  # 已初始化
    RUNNING = "running"        # 运行中
    CLEANED = "cleaned"        # 已清理


@dataclass
class Task:
    """任务数据类"""
    task_type: TaskType                            # 任务类型
    payload: Dict[str, Any]                        # 任务负载
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 任务ID
    timeout: int = 300                             # 超时时间（秒）
    priority: int = 1                              # 优先级
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间


@dataclass
class TaskResult:
    """任务结果数据类"""
    task_id: str                                   # 任务ID
    status: TaskStatus                             # 任务状态
    result: Optional[Any] = None                   # 执行结果
    error: Optional[str] = None                    # 错误信息
    execution_time: float = 0.0                    # 执行时间（秒）
    started_at: Optional[datetime] = None          # 开始时间
    completed_at: Optional[datetime] = None        # 完成时间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class ExecutionContext:
    """执行上下文"""
    task_id: str                                   # 任务ID
    variables: Dict[str, Any] = field(default_factory=dict)  # 变量存储
    resources: List[str] = field(default_factory=list)       # 资源列表
    logs: List[str] = field(default_factory=list)            # 执行日志
    
    def set_variable(self, key: str, value: Any):
        """设置变量"""
        self.variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(key, default)
    
    def add_log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().isoformat()
        self.logs.append(f"[{timestamp}] {message}")
    
    def add_resource(self, resource: str):
        """添加资源"""
        self.resources.append(resource)


class Sandbox:
    """沙箱环境"""
    
    def __init__(self, sandbox_id: str, config: Dict[str, Any] = None):
        self.sandbox_id = sandbox_id
        self.config = config or {}
        self.status = SandboxStatus.CREATED
        self.files: Dict[str, str] = {}
    
    async def initialize(self):
        """初始化沙箱"""
        self.status = SandboxStatus.INITIALIZED
        logging.info(f"沙箱 {self.sandbox_id} 已初始化")
    
    async def execute_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """执行代码"""
        self.status = SandboxStatus.RUNNING
        # 模拟代码执行
        await asyncio.sleep(0.1)
        return {
            "success": True,
            "output": f"代码执行完成: {code[:50]}...",
            "exit_code": 0
        }
    
    async def write_file(self, path: str, content: str):
        """写入文件"""
        self.files[path] = content
    
    async def read_file(self, path: str) -> Optional[str]:
        """读取文件"""
        return self.files.get(path)
    
    async def cleanup(self):
        """清理沙箱"""
        self.files.clear()
        self.status = SandboxStatus.CLEANED
        logging.info(f"沙箱 {self.sandbox_id} 已清理")


class Memory:
    """内存管理"""
    
    def __init__(self):
        self._storage: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []
    
    async def store(self, key: str, value: Any):
        """存储数据"""
        self._storage[key] = value
        self._history.append({
            "key": key,
            "timestamp": datetime.now().isoformat(),
            "action": "store"
        })
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """检索数据"""
        return self._storage.get(key)
    
    async def delete(self, key: str) -> bool:
        """删除数据"""
        if key in self._storage:
            del self._storage[key]
            self._history.append({
                "key": key,
                "timestamp": datetime.now().isoformat(),
                "action": "delete"
            })
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_stored": len(self._storage),
            "total_operations": len(self._history)
        }


class Subagent(ABC):
    """子代理抽象基类"""
    
    def __init__(self, name: str, subagent_type: str):
        self.name = name
        self.subagent_type = subagent_type
        self.is_initialized = False
    
    @abstractmethod
    async def initialize(self):
        """初始化子代理"""
        pass
    
    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """执行任务"""
        pass
    
    @abstractmethod
    async def shutdown(self):
        """关闭子代理"""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """获取子代理信息"""
        return {
            "name": self.name,
            "type": self.subagent_type,
            "initialized": self.is_initialized
        }


class GenericSubagent(Subagent):
    """通用目的子代理"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, "generic")
        self.config = config or {}
        self.sandbox: Optional[Sandbox] = None
        self.memory: Memory = Memory()
        self.context: Optional[ExecutionContext] = None
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        
        # 任务处理器映射
        self._task_handlers: Dict[TaskType, Callable] = {
            TaskType.CODE_EXECUTION: self._handle_code_execution,
            TaskType.DATA_ANALYSIS: self._handle_data_analysis,
            TaskType.API_CALL: self._handle_api_call,
            TaskType.FILE_OPERATION: self._handle_file_operation,
            TaskType.TEXT_PROCESSING: self._handle_text_processing,
        }
    
    async def initialize(self):
        """初始化子代理 - 创建沙箱和内存"""
        sandbox_id = f"sandbox_{self.name}_{uuid.uuid4().hex[:8]}"
        self.sandbox = Sandbox(sandbox_id, self.config.get("sandbox_config", {}))
        await self.sandbox.initialize()
        self.is_initialized = True
        logging.info(f"通用子代理 {self.name} 已初始化")
    
    async def execute(self, task: Task) -> TaskResult:
        """
        执行任务 - 三阶段流程
        
        阶段1: 准备执行环境
        阶段2: 执行主要逻辑
        阶段3: 清理资源
        """
        start_time = datetime.now()
        
        try:
            # 阶段1: 准备执行环境
            self.context = await self._prepare_environment(task)
            
            # 阶段2: 执行主要逻辑
            result = await self._execute_main(task)
            
            # 阶段3: 清理资源
            await self._cleanup(task)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self.execution_count += 1
            self.success_count += 1
            
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                started_at=start_time,
                completed_at=datetime.now()
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.execution_count += 1
            self.failure_count += 1
            
            # 确保清理资源
            try:
                await self._cleanup(task)
            except Exception:
                pass
            
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error=str(e),
                execution_time=execution_time,
                started_at=start_time,
                completed_at=datetime.now()
            )
    
    async def _prepare_environment(self, task: Task) -> ExecutionContext:
        """阶段1: 准备执行环境"""
        context = ExecutionContext(task_id=task.task_id)
        
        # 1. 初始化沙箱（如果未初始化）
        if not self.sandbox or self.sandbox.status == SandboxStatus.CLEANED:
            await self.initialize()
        
        # 2. 加载任务负载到上下文
        context.set_variable("payload", task.payload)
        context.set_variable("timeout", task.timeout)
        
        # 3. 记录日志
        context.add_log(f"开始准备执行环境: {task.task_type.value}")
        context.add_log(f"任务ID: {task.task_id}")
        
        return context
    
    async def _execute_main(self, task: Task) -> Any:
        """阶段2: 执行主要逻辑"""
        handler = self._task_handlers.get(task.task_type)
        if not handler:
            raise ValueError(f"不支持的任务类型: {task.task_type}")
        
        self.context.add_log(f"开始执行任务: {task.task_type.value}")
        result = await handler(task)
        self.context.add_log(f"任务执行完成")
        
        return result
    
    async def _cleanup(self, task: Task):
        """阶段3: 清理资源"""
        # 1. 保存执行结果到内存
        if self.context:
            await self.memory.store(f"result_{task.task_id}", {
                "context": self.context.variables,
                "logs": self.context.logs
            })
        
        # 2. 清理沙箱
        if self.sandbox:
            await self.sandbox.cleanup()
        
        if self.context:
            self.context.add_log("资源清理完成")
    
    async def _handle_code_execution(self, task: Task) -> Dict[str, Any]:
        """处理代码执行任务"""
        code = task.payload.get("code", "")
        language = task.payload.get("language", "python")
        
        result = await self.sandbox.execute_code(code, language)
        self.context.set_variable("execution_result", result)
        
        return {
            "type": "code_execution",
            "success": result["success"],
            "output": result["output"],
            "exit_code": result["exit_code"]
        }
    
    async def _handle_data_analysis(self, task: Task) -> Dict[str, Any]:
        """处理数据分析任务"""
        data = task.payload.get("data", [])
        analysis_type = task.payload.get("analysis_type", "summary")
        
        # 模拟数据分析
        await asyncio.sleep(0.05)
        
        result = {
            "type": "data_analysis",
            "analysis_type": analysis_type,
            "data_points": len(data),
            "summary": {
                "count": len(data),
                "mean": sum(data) / len(data) if data else 0,
                "min": min(data) if data else None,
                "max": max(data) if data else None
            }
        }
        
        self.context.set_variable("analysis_result", result)
        return result
    
    async def _handle_api_call(self, task: Task) -> Dict[str, Any]:
        """处理API调用任务"""
        url = task.payload.get("url", "")
        method = task.payload.get("method", "GET")
        headers = task.payload.get("headers", {})
        
        # 模拟API调用
        await asyncio.sleep(0.1)
        
        result = {
            "type": "api_call",
            "url": url,
            "method": method,
            "status_code": 200,
            "response": {"message": "模拟响应"}
        }
        
        self.context.set_variable("api_result", result)
        return result
    
    async def _handle_file_operation(self, task: Task) -> Dict[str, Any]:
        """处理文件操作任务"""
        operation = task.payload.get("operation", "read")
        path = task.payload.get("path", "")
        content = task.payload.get("content", "")
        
        if operation == "write":
            await self.sandbox.write_file(path, content)
            result = {"type": "file_operation", "operation": "write", "path": path, "success": True}
        elif operation == "read":
            file_content = await self.sandbox.read_file(path)
            result = {"type": "file_operation", "operation": "read", "path": path, "content": file_content}
        else:
            result = {"type": "file_operation", "operation": operation, "error": "未知操作"}
        
        self.context.set_variable("file_result", result)
        return result
    
    async def _handle_text_processing(self, task: Task) -> Dict[str, Any]:
        """处理文本处理任务"""
        text = task.payload.get("text", "")
        operation = task.payload.get("operation", "length")
        
        if operation == "length":
            result_value = len(text)
        elif operation == "uppercase":
            result_value = text.upper()
        elif operation == "lowercase":
            result_value = text.lower()
        elif operation == "word_count":
            result_value = len(text.split())
        else:
            result_value = None
        
        result = {
            "type": "text_processing",
            "operation": operation,
            "input_length": len(text),
            "result": result_value
        }
        
        self.context.set_variable("text_result", result)
        return result
    
    async def shutdown(self):
        """关闭子代理"""
        if self.sandbox:
            await self.sandbox.cleanup()
        self.is_initialized = False
        logging.info(f"通用子代理 {self.name} 已关闭")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取子代理统计信息"""
        return {
            "name": self.name,
            "type": self.subagent_type,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": (self.success_count / self.execution_count * 100) 
                if self.execution_count > 0 else 0,
            "memory_stats": self.memory.get_stats()
        }


class SubagentTestSuite:
    """通用子代理测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_subagent_initialization", self.test_subagent_initialization),
            ("test_code_execution", self.test_code_execution),
            ("test_data_analysis", self.test_data_analysis),
            ("test_api_call", self.test_api_call),
            ("test_text_processing", self.test_text_processing),
        ]
    
    async def _async_test_subagent_initialization(self) -> tuple:
        """异步测试子代理初始化"""
        agent = GenericSubagent("test_agent")
        
        if agent.is_initialized:
            return False, "初始化前不应该已初始化"
        
        await agent.initialize()
        
        if not agent.is_initialized:
            return False, "初始化后应该已初始化"
        
        if agent.sandbox is None:
            return False, "沙箱应该已创建"
        
        info = agent.get_info()
        if info["name"] != "test_agent":
            return False, f"名称不正确: {info['name']}"
        
        await agent.shutdown()
        return True, "子代理初始化测试通过"
    
    def test_subagent_initialization(self) -> tuple:
        """测试子代理初始化"""
        return asyncio.run(self._async_test_subagent_initialization())
    
    async def _async_test_code_execution(self) -> tuple:
        """异步测试代码执行"""
        agent = GenericSubagent("code_agent")
        await agent.initialize()
        
        task = Task(
            task_type=TaskType.CODE_EXECUTION,
            payload={"code": "print('Hello World')", "language": "python"}
        )
        
        result = await agent.execute(task)
        
        if result.status != TaskStatus.COMPLETED:
            return False, f"任务状态不正确: {result.status}"
        
        if result.result is None:
            return False, "结果不应该为空"
        
        if result.result.get("type") != "code_execution":
            return False, f"结果类型不正确: {result.result.get('type')}"
        
        await agent.shutdown()
        return True, "代码执行测试通过"
    
    def test_code_execution(self) -> tuple:
        """测试代码执行"""
        return asyncio.run(self._async_test_code_execution())
    
    async def _async_test_data_analysis(self) -> tuple:
        """异步测试数据分析"""
        agent = GenericSubagent("data_agent")
        await agent.initialize()
        
        task = Task(
            task_type=TaskType.DATA_ANALYSIS,
            payload={"data": [1, 2, 3, 4, 5], "analysis_type": "summary"}
        )
        
        result = await agent.execute(task)
        
        if result.status != TaskStatus.COMPLETED:
            return False, f"任务状态不正确: {result.status}"
        
        if result.result.get("type") != "data_analysis":
            return False, f"结果类型不正确"
        
        if result.result.get("summary", {}).get("count") != 5:
            return False, "数据点数量不正确"
        
        await agent.shutdown()
        return True, "数据分析测试通过"
    
    def test_data_analysis(self) -> tuple:
        """测试数据分析"""
        return asyncio.run(self._async_test_data_analysis())
    
    async def _async_test_api_call(self) -> tuple:
        """异步测试API调用"""
        agent = GenericSubagent("api_agent")
        await agent.initialize()
        
        task = Task(
            task_type=TaskType.API_CALL,
            payload={"url": "https://api.example.com/data", "method": "GET"}
        )
        
        result = await agent.execute(task)
        
        if result.status != TaskStatus.COMPLETED:
            return False, f"任务状态不正确: {result.status}"
        
        if result.result.get("status_code") != 200:
            return False, "状态码不正确"
        
        await agent.shutdown()
        return True, "API调用测试通过"
    
    def test_api_call(self) -> tuple:
        """测试API调用"""
        return asyncio.run(self._async_test_api_call())
    
    async def _async_test_text_processing(self) -> tuple:
        """异步测试文本处理"""
        agent = GenericSubagent("text_agent")
        await agent.initialize()
        
        task = Task(
            task_type=TaskType.TEXT_PROCESSING,
            payload={"text": "Hello World", "operation": "uppercase"}
        )
        
        result = await agent.execute(task)
        
        if result.status != TaskStatus.COMPLETED:
            return False, f"任务状态不正确: {result.status}"
        
        if result.result.get("result") != "HELLO WORLD":
            return False, f"结果不正确: {result.result.get('result')}"
        
        await agent.shutdown()
        return True, "文本处理测试通过"
    
    def test_text_processing(self) -> tuple:
        """测试文本处理"""
        return asyncio.run(self._async_test_text_processing())
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行通用目的子代理测试套件...")
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
    print("🎓 Day 11 Lesson 43: 通用目的子代理演示")
    print("=" * 60)
    
    # 1. 创建并初始化子代理
    print("\n1. 创建通用子代理:")
    agent = GenericSubagent("demo_agent", {
        "sandbox_config": {"memory_limit": "1GB"},
        "timeout": 300
    })
    
    await agent.initialize()
    print(f"   ✅ 子代理已初始化: {agent.name}")
    
    # 2. 代码执行演示
    print("\n2. 代码执行任务:")
    code_task = Task(
        task_type=TaskType.CODE_EXECUTION,
        payload={"code": "print('Hello from subagent!')", "language": "python"}
    )
    
    result = await agent.execute(code_task)
    print(f"   任务状态: {result.status.value}")
    print(f"   执行时间: {result.execution_time:.3f}秒")
    print(f"   输出: {result.result.get('output')}")
    
    # 3. 数据分析演示
    print("\n3. 数据分析任务:")
    data_task = Task(
        task_type=TaskType.DATA_ANALYSIS,
        payload={"data": [10, 20, 30, 40, 50], "analysis_type": "summary"}
    )
    
    result = await agent.execute(data_task)
    print(f"   任务状态: {result.status.value}")
    print(f"   分析结果: {result.result.get('summary')}")
    
    # 4. API调用演示
    print("\n4. API调用任务:")
    api_task = Task(
        task_type=TaskType.API_CALL,
        payload={"url": "https://api.example.com/data", "method": "POST"}
    )
    
    result = await agent.execute(api_task)
    print(f"   任务状态: {result.status.value}")
    print(f"   状态码: {result.result.get('status_code')}")
    
    # 5. 文本处理演示
    print("\n5. 文本处理任务:")
    text_task = Task(
        task_type=TaskType.TEXT_PROCESSING,
        payload={"text": "hello world from subagent", "operation": "word_count"}
    )
    
    result = await agent.execute(text_task)
    print(f"   任务状态: {result.status.value}")
    print(f"   单词数: {result.result.get('result')}")
    
    # 6. 统计信息
    print("\n6. 子代理统计:")
    stats = agent.get_stats()
    print(f"   执行次数: {stats['execution_count']}")
    print(f"   成功次数: {stats['success_count']}")
    print(f"   失败次数: {stats['failure_count']}")
    print(f"   成功率: {stats['success_rate']:.1f}%")
    print(f"   内存统计: {stats['memory_stats']}")
    
    # 7. 关闭子代理
    print("\n7. 关闭子代理:")
    await agent.shutdown()
    print(f"   ✅ 子代理已关闭")
    
    print("\n演示完成!")


def run_tests():
    """运行测试套件"""
    test_suite = SubagentTestSuite()
    report = test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 通用目的子代理测试套件验证通过")
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
