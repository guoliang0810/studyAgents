#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 12 Lesson 45: task工具实现 (Task Tool Implementation)

本文件演示任务工具的设计和实现，包括：
1. 工具装饰器 - @tool装饰器定义工具函数
2. 参数验证 - Pydantic模型验证参数
3. 任务创建 - 从工具参数创建任务对象
4. 异步执行 - 任务提交到执行器异步执行

使用示例:
    python task_tool_demo.py          # 运行基本演示
    python task_tool_demo.py --test   # 运行测试套件
    python task_tool_demo.py --demo   # 运行完整演示
    python task_tool_demo.py --help   # 显示帮助信息
"""

import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Type
from datetime import datetime
import uuid
from functools import wraps
import inspect


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"        # 等待中
    RUNNING = "running"        # 运行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    TIMEOUT = "timeout"        # 超时


class SubagentType(Enum):
    """子代理类型枚举"""
    GENERIC = "generic"        # 通用子代理
    BASH = "bash"              # Bash子代理
    PYTHON = "python"          # Python子代理
    SQL = "sql"                # SQL子代理
    WEB = "web"                # Web子代理


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str                                      # 参数名称
    type: Type                                     # 参数类型
    description: str                               # 参数描述
    default: Any = None                            # 默认值
    required: bool = True                          # 是否必填
    choices: Optional[List[Any]] = None            # 可选值列表
    
    def validate(self, value: Any) -> tuple:
        """验证参数值"""
        # 检查必填
        if value is None and self.required:
            return False, f"参数 {self.name} 是必填的"
        
        # 检查类型
        if value is not None:
            if not isinstance(value, self.type):
                try:
                    # 尝试类型转换
                    value = self.type(value)
                except (ValueError, TypeError):
                    return False, f"参数 {self.name} 类型错误，期望 {self.type.__name__}"
        
        # 检查可选值
        if self.choices and value not in self.choices:
            return False, f"参数 {self.name} 值不在允许范围内: {self.choices}"
        
        return True, value


@dataclass
class TaskDefinition:
    """任务定义"""
    name: str                                      # 任务名称
    description: str                               # 任务描述
    parameters: List[ToolParameter]                # 参数列表
    handler: Callable                              # 处理函数
    return_type: Type = str                        # 返回类型
    is_async: bool = False                         # 是否异步
    timeout: float = 300.0                         # 默认超时时间
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """获取参数模式（JSON Schema格式）"""
        properties = {}
        required = []
        
        for param in self.parameters:
            param_schema = {
                "type": self._python_type_to_json(param.type),
                "description": param.description
            }
            
            if param.default is not None:
                param_schema["default"] = param.default
            if param.choices:
                param_schema["enum"] = param.choices
            
            properties[param.name] = param_schema
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def _python_type_to_json(self, py_type: Type) -> str:
        """Python类型转JSON Schema类型"""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object"
        }
        return type_map.get(py_type, "string")


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str                                   # 任务ID
    status: TaskStatus                             # 执行状态
    result: Any = None                             # 执行结果
    error: Optional[str] = None                    # 错误信息
    execution_time: float = 0.0                    # 执行时间（秒）
    tool_name: Optional[str] = None                # 工具名称
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
            "tool_name": self.tool_name,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    def __str__(self) -> str:
        if self.status == TaskStatus.COMPLETED:
            return f"✅ 任务完成: {self.result}"
        else:
            return f"❌ 任务失败: {self.error}"


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, TaskDefinition] = {}
    
    def register(self, tool_def: TaskDefinition):
        """注册工具"""
        self._tools[tool_def.name] = tool_def
        logging.info(f"工具已注册: {tool_def.name}")
    
    def get(self, name: str) -> Optional[TaskDefinition]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_all(self) -> List[TaskDefinition]:
        """列出所有工具"""
        return list(self._tools.values())
    
    def list_names(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())
    
    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get_schemas(self) -> Dict[str, Any]:
        """获取所有工具的模式"""
        schemas = {}
        for name, tool_def in self._tools.items():
            schemas[name] = {
                "description": tool_def.description,
                "parameters": tool_def.get_parameter_schema()
            }
        return schemas


# 全局工具注册表
_global_registry = ToolRegistry()


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    timeout: float = 300.0
):
    """
    工具装饰器
    
    用于将函数注册为可调用的工具
    
    Args:
        name: 工具名称（默认使用函数名）
        description: 工具描述（默认使用函数文档字符串）
        timeout: 默认超时时间
    """
    def decorator(func: Callable) -> Callable:
        # 获取工具名称
        tool_name = name or func.__name__
        
        # 获取工具描述
        tool_desc = description or func.__doc__ or f"Tool: {tool_name}"
        
        # 解析参数
        sig = inspect.signature(func)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            # 跳过self参数
            if param_name == "self":
                continue
            
            # 获取参数类型
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            
            # 获取默认值
            default = param.default if param.default != inspect.Parameter.empty else None
            required = default is None and param.default == inspect.Parameter.empty
            
            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                description=f"Parameter: {param_name}",
                default=default,
                required=required
            ))
        
        # 创建任务定义
        tool_def = TaskDefinition(
            name=tool_name,
            description=tool_desc.strip(),
            parameters=parameters,
            handler=func,
            is_async=asyncio.iscoroutinefunction(func),
            timeout=timeout
        )
        
        # 注册工具
        _global_registry.register(tool_def)
        
        # 包装函数
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await execute_tool(tool_name, *args, **kwargs)
        
        # 添加工具元数据
        wrapper._tool_definition = tool_def
        wrapper._tool_registry = _global_registry
        
        return wrapper
    
    return decorator


async def execute_tool(tool_name: str, *args, **kwargs) -> TaskResult:
    """
    执行工具
    
    Args:
        tool_name: 工具名称
        *args, **kwargs: 工具参数
        
    Returns:
        TaskResult: 执行结果
    """
    start_time = datetime.now()
    task_id = str(uuid.uuid4())
    
    # 获取工具定义
    tool_def = _global_registry.get(tool_name)
    if not tool_def:
        return TaskResult(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=f"工具未找到: {tool_name}",
            started_at=start_time,
            completed_at=datetime.now()
        )
    
    # 验证参数
    validated_args = []
    validated_kwargs = {}
    
    try:
        # 绑定参数
        sig = inspect.signature(tool_def.handler)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        
        # 验证每个参数
        for param_def in tool_def.parameters:
            if param_def.name in bound.arguments:
                value = bound.arguments[param_def.name]
                is_valid, result = param_def.validate(value)
                
                if not is_valid:
                    return TaskResult(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        error=result,
                        tool_name=tool_name,
                        started_at=start_time,
                        completed_at=datetime.now()
                    )
                
                bound.arguments[param_def.name] = result
        
        # 执行工具
        try:
            if tool_def.is_async:
                result = await asyncio.wait_for(
                    tool_def.handler(**bound.arguments),
                    timeout=tool_def.timeout
                )
            else:
                # 同步函数在事件循环中执行
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: tool_def.handler(**bound.arguments)
                )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                tool_name=tool_name,
                started_at=start_time,
                completed_at=datetime.now()
            )
            
        except asyncio.TimeoutError:
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.TIMEOUT,
                error=f"工具执行超时: {tool_def.timeout}秒",
                execution_time=tool_def.timeout,
                tool_name=tool_name,
                started_at=start_time,
                completed_at=datetime.now()
            )
            
    except Exception as e:
        return TaskResult(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=str(e),
            tool_name=tool_name,
            started_at=start_time,
            completed_at=datetime.now()
        )


# ============ 示例工具定义 ============

@tool(name="execute_code", description="执行Python代码并返回结果", timeout=60.0)
async def execute_code(code: str, language: str = "python") -> str:
    """执行代码工具"""
    await asyncio.sleep(0.1)  # 模拟执行
    return f"代码执行完成: {code[:50]}..."


@tool(name="bash_command", description="执行Bash命令并返回输出", timeout=30.0)
async def bash_command(command: str, working_dir: str = "/tmp") -> str:
    """执行Bash命令工具"""
    await asyncio.sleep(0.05)
    return f"命令输出: {command}"


@tool(name="analyze_data", description="分析数据并返回统计信息", timeout=120.0)
async def analyze_data(data: List[float], method: str = "summary") -> Dict[str, Any]:
    """分析数据工具"""
    if not data:
        return {"error": "数据为空"}
    
    if method == "summary":
        return {
            "count": len(data),
            "mean": sum(data) / len(data),
            "min": min(data),
            "max": max(data),
            "sum": sum(data)
        }
    elif method == "statistics":
        import statistics
        return {
            "count": len(data),
            "mean": statistics.mean(data),
            "median": statistics.median(data),
            "stdev": statistics.stdev(data) if len(data) > 1 else 0
        }
    else:
        return {"error": f"未知的分析方法: {method}"}


@tool(name="search_web", description="搜索网页并返回结果", timeout=30.0)
async def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """搜索网页工具"""
    await asyncio.sleep(0.2)
    return [
        {"title": f"Result {i+1}", "url": f"https://example.com/{i+1}", "snippet": f"About {query}"}
        for i in range(max_results)
    ]


@tool(name="generate_report", description="生成报告文件", timeout=60.0)
def generate_report(title: str, content: str, format: str = "markdown") -> str:
    """生成报告工具（同步）"""
    return f"报告已生成: {title}.{format}"


# ============ 测试套件 ============

class TaskToolTestSuite:
    """任务工具测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_tool_registration", self.test_tool_registration),
            ("test_parameter_validation", self.test_parameter_validation),
            ("test_tool_execution", self.test_tool_execution),
            ("test_tool_schema", self.test_tool_schema),
            ("test_error_handling", self.test_error_handling),
        ]
    
    def test_tool_registration(self) -> tuple:
        """测试工具注册"""
        try:
            # 检查工具是否已注册
            tool_names = _global_registry.list_names()
            
            if "execute_code" not in tool_names:
                return False, "execute_code工具未注册"
            
            if "bash_command" not in tool_names:
                return False, "bash_command工具未注册"
            
            if "analyze_data" not in tool_names:
                return False, "analyze_data工具未注册"
            
            # 检查工具定义
            execute_code_tool = _global_registry.get("execute_code")
            if not execute_code_tool:
                return False, "无法获取execute_code工具"
            
            if len(execute_code_tool.parameters) != 2:
                return False, f"execute_code参数数量不正确: {len(execute_code_tool.parameters)}"
            
            return True, f"工具注册测试通过，已注册{len(tool_names)}个工具"
        except Exception as e:
            return False, f"工具注册异常: {e}"
    
    def test_parameter_validation(self) -> tuple:
        """测试参数验证"""
        try:
            # 测试必填参数验证
            param = ToolParameter(
                name="test_param",
                type=str,
                description="测试参数",
                required=True
            )
            
            # 缺少必填参数
            is_valid, result = param.validate(None)
            if is_valid:
                return False, "必填参数验证应该失败"
            
            # 正确的参数
            is_valid, result = param.validate("test_value")
            if not is_valid:
                return False, f"参数验证失败: {result}"
            
            # 测试类型转换
            int_param = ToolParameter(
                name="int_param",
                type=int,
                description="整数参数"
            )
            
            is_valid, result = int_param.validate("123")
            if not is_valid or result != 123:
                return False, f"类型转换失败: {result}"
            
            # 测试可选值验证
            choice_param = ToolParameter(
                name="choice_param",
                type=str,
                description="选择参数",
                choices=["a", "b", "c"]
            )
            
            is_valid, result = choice_param.validate("a")
            if not is_valid:
                return False, "可选值验证失败"
            
            is_valid, result = choice_param.validate("d")
            if is_valid:
                return False, "可选值验证应该失败"
            
            return True, "参数验证测试通过"
        except Exception as e:
            return False, f"参数验证异常: {e}"
    
    def test_tool_execution(self) -> tuple:
        """测试工具执行"""
        async def run_test():
            # 测试异步工具
            result = await execute_tool("execute_code", code="print('hello')")
            if result.status != TaskStatus.COMPLETED:
                return False, f"工具执行失败: {result.error}"
            
            if "代码执行完成" not in str(result.result):
                return False, f"执行结果不正确: {result.result}"
            
            # 测试带默认参数的工具
            result = await execute_tool("bash_command", command="ls -la")
            if result.status != TaskStatus.COMPLETED:
                return False, f"bash_command执行失败: {result.error}"
            
            # 测试同步工具
            result = await execute_tool("generate_report", title="Test", content="Content")
            if result.status != TaskStatus.COMPLETED:
                return False, f"generate_report执行失败: {result.error}"
            
            return True, "工具执行测试通过"
        
        return asyncio.run(run_test())
    
    def test_tool_schema(self) -> tuple:
        """测试工具模式生成"""
        try:
            schemas = _global_registry.get_schemas()
            
            if "execute_code" not in schemas:
                return False, "execute_code模式未生成"
            
            schema = schemas["execute_code"]
            
            if "description" not in schema:
                return False, "模式缺少description"
            
            if "parameters" not in schema:
                return False, "模式缺少parameters"
            
            params = schema["parameters"]
            
            if "properties" not in params:
                return False, "参数模式缺少properties"
            
            if "code" not in params["properties"]:
                return False, "缺少code参数"
            
            return True, "工具模式生成测试通过"
        except Exception as e:
            return False, f"模式生成异常: {e}"
    
    def test_error_handling(self) -> tuple:
        """测试错误处理"""
        async def run_test():
            # 测试不存在的工具
            result = await execute_tool("nonexistent_tool")
            if result.status != TaskStatus.FAILED:
                return False, "不存在的工具应该返回失败"
            
            if "工具未找到" not in str(result.error):
                return False, f"错误信息不正确: {result.error}"
            
            # 测试参数验证失败
            result = await execute_tool("execute_code")  # 缺少必填参数code
            if result.status != TaskStatus.FAILED:
                return False, "缺少必填参数应该返回失败"
            
            return True, "错误处理测试通过"
        
        return asyncio.run(run_test())
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行task工具测试套件...")
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
    print("🎓 Day 12 Lesson 45: task工具实现演示")
    print("=" * 60)
    
    # 1. 列出已注册的工具
    print("\n1. 已注册的工具:")
    tool_names = _global_registry.list_names()
    for name in tool_names:
        tool_def = _global_registry.get(name)
        print(f"   🔧 {name}: {tool_def.description[:50]}...")
    
    # 2. 执行代码执行工具
    print("\n2. 执行代码执行工具:")
    result = await execute_tool("execute_code", code="print('Hello World')", language="python")
    print(f"   状态: {result.status.value}")
    print(f"   结果: {result.result}")
    print(f"   执行时间: {result.execution_time:.3f}秒")
    
    # 3. 执行Bash命令工具
    print("\n3. 执行Bash命令工具:")
    result = await execute_tool("bash_command", command="ls -la /tmp")
    print(f"   状态: {result.status.value}")
    print(f"   结果: {result.result}")
    
    # 4. 执行数据分析工具
    print("\n4. 执行数据分析工具:")
    result = await execute_tool("analyze_data", data=[1, 2, 3, 4, 5], method="summary")
    print(f"   状态: {result.status.value}")
    print(f"   结果: {result.result}")
    
    # 5. 执行搜索工具
    print("\n5. 执行搜索工具:")
    result = await execute_tool("search_web", query="Python Agent", max_results=3)
    print(f"   状态: {result.status.value}")
    for item in result.result[:2]:
        print(f"   - {item['title']}")
    
    # 6. 查看工具模式
    print("\n6. 工具模式示例 (execute_code):")
    schemas = _global_registry.get_schemas()
    import json
    print(json.dumps(schemas["execute_code"], indent=2, ensure_ascii=False))
    
    # 7. 错误处理演示
    print("\n7. 错误处理演示:")
    
    # 不存在的工具
    result = await execute_tool("unknown_tool")
    print(f"   不存在的工具: {result.status.value} - {result.error}")
    
    # 缺少必填参数
    result = await execute_tool("execute_code")
    print(f"   缺少参数: {result.status.value} - {result.error}")
    
    print("\n演示完成!")


def run_tests():
    """运行测试套件"""
    test_suite = TaskToolTestSuite()
    report = test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 task工具测试套件验证通过")
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
