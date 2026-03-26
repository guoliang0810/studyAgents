#!/usr/bin/env python3
"""
DeerFlow 2.0 架构优势演示代码
Day 1 第3节课：课堂演示代码

本代码演示DeerFlow 2.0的四层架构设计、状态机管理和代码组织优势。
通过模拟实现，展示架构设计如何提高系统的模块化、可扩展性和可维护性。

主要演示内容：
1. 四层架构模拟：Lead Agent, Middleware Chain, Tool System, Subagents
2. LangGraph StateGraph 状态机实现
3. ThreadState 状态管理
4. 模块化设计和代码组织结构
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, TypedDict
from dataclasses import dataclass, field
from enum import Enum
import time
from datetime import datetime
import random

# ============================================================================
# 第一部分：四层架构模拟
# ============================================================================


class ArchitectureLayer(str, Enum):
    """四层架构枚举"""

    LEAD_AGENT = "Lead Agent"  # 领导代理层：项目经理角色
    MIDDLEWARE_CHAIN = "Middleware Chain"  # 中间件链层：秘书团队
    TOOL_SYSTEM = "Tool System"  # 工具系统层：专业工程师
    SUBAGENTS = "Subagents"  # 子代理层：外包团队


@dataclass
class Message:
    """消息类，用于层间通信"""

    id: str
    content: str
    sender: ArchitectureLayer
    receiver: ArchitectureLayer
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "sender": self.sender.value,
            "receiver": self.receiver.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class ToolSystem:
    """工具系统层：专业工程师团队"""

    def __init__(self):
        self.tools = {
            "calculator": self._calculator_tool,
            "web_search": self._web_search_tool,
            "data_analysis": self._data_analysis_tool,
            "file_processor": self._file_processor_tool,
        }
        self.tool_stats = {tool_name: 0 for tool_name in self.tools}

    async def _calculator_tool(self, expression: str) -> Dict[str, Any]:
        """计算器工具"""
        await asyncio.sleep(0.1)  # 模拟处理时间
        try:
            # 安全评估表达式
            result = eval(expression, {"__builtins__": None}, {})
            return {"success": True, "result": result, "tool_used": "calculator"}
        except Exception as e:
            return {"success": False, "error": str(e), "tool_used": "calculator"}

    async def _web_search_tool(self, query: str) -> Dict[str, Any]:
        """网络搜索工具"""
        await asyncio.sleep(0.3)  # 模拟网络延迟
        return {
            "success": True,
            "results": [
                {"title": f"关于 {query} 的搜索结果 1", "url": "https://example.com/1"},
                {"title": f"关于 {query} 的搜索结果 2", "url": "https://example.com/2"},
            ],
            "tool_used": "web_search",
        }

    async def _data_analysis_tool(self, data: List[Any]) -> Dict[str, Any]:
        """数据分析工具"""
        await asyncio.sleep(0.2)
        if not data:
            return {"success": False, "error": "数据为空", "tool_used": "data_analysis"}

        analysis = {
            "count": len(data),
            "sum": sum(data)
            if all(isinstance(x, (int, float)) for x in data)
            else None,
            "average": sum(data) / len(data)
            if all(isinstance(x, (int, float)) for x in data)
            else None,
            "min": min(data) if data else None,
            "max": max(data) if data else None,
        }

        return {"success": True, "analysis": analysis, "tool_used": "data_analysis"}

    async def _file_processor_tool(
        self, filename: str, operation: str
    ) -> Dict[str, Any]:
        """文件处理工具"""
        await asyncio.sleep(0.15)
        operations = {
            "read": f"读取文件 {filename} 成功",
            "write": f"写入文件 {filename} 成功",
            "delete": f"删除文件 {filename} 成功",
            "list": f"列出目录内容成功，找到5个文件",
        }

        if operation not in operations:
            return {
                "success": False,
                "error": f"不支持的操作: {operation}",
                "tool_used": "file_processor",
            }

        return {
            "success": True,
            "message": operations[operation],
            "tool_used": "file_processor",
        }

    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"未知工具: {tool_name}",
                "available_tools": list(self.tools.keys()),
            }

        self.tool_stats[tool_name] += 1
        result = await self.tools[tool_name](**kwargs)
        result["execution_time"] = datetime.now().isoformat()
        return result


class MiddlewareChain:
    """中间件链层：秘书团队，负责请求处理和增强"""

    def __init__(self):
        self.middlewares = []
        self._setup_default_middlewares()

    def _setup_default_middlewares(self):
        """设置默认中间件"""
        self.add_middleware(self._logging_middleware)
        self.add_middleware(self._authentication_middleware)
        self.add_middleware(self._rate_limiting_middleware)
        self.add_middleware(self._validation_middleware)
        self.add_middleware(self._caching_middleware)

    def add_middleware(self, middleware_func: Callable):
        """添加中间件"""
        self.middlewares.append(middleware_func)

    async def _logging_middleware(
        self, request: Dict[str, Any], next_fn: Callable
    ) -> Dict[str, Any]:
        """日志中间件"""
        start_time = time.time()
        print(f"[Middleware-Logging] 开始处理请求: {request.get('action', 'unknown')}")

        # 调用下一个中间件或处理函数
        response = await next_fn(request)

        elapsed = time.time() - start_time
        print(f"[Middleware-Logging] 请求处理完成，耗时: {elapsed:.3f}秒")
        return response

    async def _authentication_middleware(
        self, request: Dict[str, Any], next_fn: Callable
    ) -> Dict[str, Any]:
        """认证中间件"""
        token = request.get("headers", {}).get("Authorization")
        if not token:
            return {"success": False, "error": "未提供认证令牌"}

        # 简单模拟认证检查
        if token != "Bearer valid-token-123":
            return {"success": False, "error": "认证失败"}

        print(f"[Middleware-Auth] 用户认证成功")
        return await next_fn(request)

    async def _rate_limiting_middleware(
        self, request: Dict[str, Any], next_fn: Callable
    ) -> Dict[str, Any]:
        """限流中间件"""
        user_id = request.get("user_id", "anonymous")
        # 简单模拟限流检查
        if random.random() < 0.05:  # 5%概率触发限流
            return {"success": False, "error": "请求过于频繁，请稍后重试"}

        print(f"[Middleware-RateLimit] 用户 {user_id} 通过限流检查")
        return await next_fn(request)

    async def _validation_middleware(
        self, request: Dict[str, Any], next_fn: Callable
    ) -> Dict[str, Any]:
        """验证中间件"""
        action = request.get("action")
        if not action:
            return {"success": False, "error": "未指定操作类型"}

        required_fields = {
            "calculate": ["expression"],
            "search": ["query"],
            "analyze": ["data"],
            "process_file": ["filename", "operation"],
        }

        if action in required_fields:
            for field in required_fields[action]:
                if field not in request:
                    return {"success": False, "error": f"缺少必要字段: {field}"}

        print(f"[Middleware-Validation] 请求验证通过")
        return await next_fn(request)

    async def _caching_middleware(
        self, request: Dict[str, Any], next_fn: Callable
    ) -> Dict[str, Any]:
        """缓存中间件"""
        cache_key = json.dumps(request, sort_keys=True)

        # 简单模拟缓存
        cache = getattr(self, "_cache", {})
        if cache_key in cache:
            print(f"[Middleware-Cache] 缓存命中，直接返回结果")
            return cache[cache_key]

        response = await next_fn(request)

        # 缓存成功结果
        if response.get("success"):
            cache[cache_key] = response
            self._cache = cache

        return response

    async def process_request(
        self, request: Dict[str, Any], handler: Callable
    ) -> Dict[str, Any]:
        """处理请求，通过中间件链"""

        # 构建中间件链
        async def chain(index: int):
            if index >= len(self.middlewares):
                # 所有中间件执行完毕，调用最终处理函数
                return await handler(request)

            middleware = self.middlewares[index]

            async def next_fn(req):
                return await chain(index + 1)

            return await middleware(request, next_fn)

        return await chain(0)


class Subagents:
    """子代理层：外包团队，负责特定任务"""

    def __init__(self):
        self.subagents = {
            "data_collector": self._data_collector_agent,
            "content_summarizer": self._content_summarizer_agent,
            "quality_checker": self._quality_checker_agent,
            "report_generator": self._report_generator_agent,
        }

    async def _data_collector_agent(self, topic: str, count: int = 3) -> Dict[str, Any]:
        """数据收集子代理"""
        await asyncio.sleep(0.5)
        return {
            "success": True,
            "data": [
                {
                    "id": i,
                    "content": f"关于 {topic} 的数据点 {i}",
                    "source": f"source_{i}",
                }
                for i in range(1, count + 1)
            ],
            "agent": "data_collector",
        }

    async def _content_summarizer_agent(
        self, content: str, max_length: int = 100
    ) -> Dict[str, Any]:
        """内容总结子代理"""
        await asyncio.sleep(0.3)
        words = content.split()
        summary = " ".join(words[: min(len(words), 20)]) + "..."

        return {
            "success": True,
            "original_length": len(content),
            "summary_length": len(summary),
            "summary": summary,
            "agent": "content_summarizer",
        }

    async def _quality_checker_agent(
        self, data: Any, criteria: List[str]
    ) -> Dict[str, Any]:
        """质量检查子代理"""
        await asyncio.sleep(0.4)
        checks = {}
        for criterion in criteria:
            if criterion == "completeness":
                checks["completeness"] = random.randint(70, 100)
            elif criterion == "accuracy":
                checks["accuracy"] = random.randint(80, 100)
            elif criterion == "timeliness":
                checks["timeliness"] = random.randint(60, 100)
            else:
                checks[criterion] = random.randint(50, 100)

        overall_score = sum(checks.values()) / len(checks)

        return {
            "success": True,
            "checks": checks,
            "overall_score": overall_score,
            "agent": "quality_checker",
        }

    async def _report_generator_agent(
        self, data: Dict[str, Any], format: str = "markdown"
    ) -> Dict[str, Any]:
        """报告生成子代理"""
        await asyncio.sleep(0.6)

        if format == "markdown":
            report = f"""# 分析报告
                
## 概览
- 生成时间: {datetime.now().isoformat()}
- 数据条目: {len(data.get("items", []))}
- 分析结果: {data.get("result", "N/A")}

## 详细分析
{json.dumps(data, indent=2, ensure_ascii=False)}

## 结论
基于分析，建议采取相应行动。
"""
        elif format == "json":
            report = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            report = str(data)

        return {
            "success": True,
            "report": report,
            "format": format,
            "agent": "report_generator",
        }

    async def execute_subagent(self, agent_name: str, **kwargs) -> Dict[str, Any]:
        """执行子代理"""
        if agent_name not in self.subagents:
            return {
                "success": False,
                "error": f"未知子代理: {agent_name}",
                "available_agents": list(self.subagents.keys()),
            }

        return await self.subagents[agent_name](**kwargs)


class LeadAgent:
    """领导代理层：项目经理角色，协调整个系统"""

    def __init__(
        self,
        tool_system: ToolSystem,
        middleware_chain: MiddlewareChain,
        subagents: Subagents,
    ):
        self.tool_system = tool_system
        self.middleware_chain = middleware_chain
        self.subagents = subagents
        self.request_count = 0
        self.success_count = 0

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求 - 领导代理的入口点"""
        self.request_count += 1

        # 构建标准化的请求对象
        standardized_request = {
            **request,
            "request_id": f"req_{self.request_count:06d}",
            "timestamp": datetime.now().isoformat(),
            "headers": request.get("headers", {}),
        }

        print(f"\n{'=' * 60}")
        print(
            f"[LeadAgent] 收到请求 #{self.request_count}: {request.get('action', 'unknown')}"
        )
        print(f"{'=' * 60}")

        # 通过中间件链处理请求
        async def request_handler(req: Dict[str, Any]) -> Dict[str, Any]:
            """实际请求处理函数"""
            return await self._process_core_request(req)

        # 通过中间件链
        response = await self.middleware_chain.process_request(
            standardized_request, request_handler
        )

        if response.get("success"):
            self.success_count += 1

        # 添加系统统计信息
        response["system_stats"] = {
            "request_id": standardized_request["request_id"],
            "total_requests": self.request_count,
            "success_rate": self.success_count / self.request_count
            if self.request_count > 0
            else 0,
            "processing_time": datetime.now().isoformat(),
        }

        print(
            f"[LeadAgent] 请求处理完成，结果: {'成功' if response.get('success') else '失败'}"
        )
        return response

    async def _process_core_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """核心请求处理逻辑"""
        action = request.get("action")

        if action == "calculate":
            return await self.tool_system.execute_tool(
                "calculator", expression=request["expression"]
            )
        elif action == "search":
            return await self.tool_system.execute_tool(
                "web_search", query=request["query"]
            )
        elif action == "analyze":
            return await self.tool_system.execute_tool(
                "data_analysis", data=request["data"]
            )
        elif action == "process_file":
            return await self.tool_system.execute_tool(
                "file_processor",
                filename=request["filename"],
                operation=request["operation"],
            )
        elif action == "collect_data":
            # 使用子代理收集数据
            return await self.subagents.execute_subagent(
                "data_collector", topic=request["topic"], count=request.get("count", 3)
            )
        elif action == "generate_report":
            # 复杂任务：收集数据 -> 质量检查 -> 生成报告
            data_result = await self.subagents.execute_subagent(
                "data_collector", topic=request["topic"], count=5
            )

            if not data_result.get("success"):
                return data_result

            quality_result = await self.subagents.execute_subagent(
                "quality_checker",
                data=data_result["data"],
                criteria=["completeness", "accuracy"],
            )

            report_result = await self.subagents.execute_subagent(
                "report_generator",
                data={"items": data_result["data"], "quality": quality_result},
                format=request.get("format", "markdown"),
            )

            return {
                "success": True,
                "action": "complex_workflow",
                "data_collection": data_result,
                "quality_check": quality_result,
                "report_generation": report_result,
                "message": "复杂工作流执行完成",
            }
        else:
            return {
                "success": False,
                "error": f"不支持的操作: {action}",
                "available_actions": [
                    "calculate",
                    "search",
                    "analyze",
                    "process_file",
                    "collect_data",
                    "generate_report",
                ],
            }


# ============================================================================
# 第二部分：LangGraph StateGraph 状态机模拟
# ============================================================================


class AgentState(str, Enum):
    """Agent状态枚举"""

    INITIALIZED = "initialized"  # 已初始化
    PLANNING = "planning"  # 规划中
    EXECUTING = "executing"  # 执行中
    REVIEWING = "reviewing"  # 评审中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败


@dataclass
class ThreadState(TypedDict):
    """线程状态类 - 模拟LangGraph的ThreadState"""

    messages: List[Dict[str, Any]]  # 消息历史
    current_state: AgentState  # 当前状态
    next_action: Optional[str]  # 下一步动作
    result: Optional[Dict[str, Any]]  # 执行结果
    error: Optional[str]  # 错误信息
    metadata: Dict[str, Any]  # 元数据


class StateGraph:
    """状态图类 - 模拟LangGraph的StateGraph"""

    def __init__(self):
        self.nodes = {}  # 状态节点
        self.edges = {}  # 状态转移边
        self._setup_default_graph()

    def _setup_default_graph(self):
        """设置默认状态图"""
        # 添加节点
        self.add_node(AgentState.INITIALIZED, self._initialized_state)
        self.add_node(AgentState.PLANNING, self._planning_state)
        self.add_node(AgentState.EXECUTING, self._executing_state)
        self.add_node(AgentState.REVIEWING, self._reviewing_state)
        self.add_node(AgentState.COMPLETED, self._completed_state)
        self.add_node(AgentState.FAILED, self._failed_state)

        # 添加转移边
        self.add_edge(AgentState.INITIALIZED, AgentState.PLANNING)
        self.add_edge(AgentState.PLANNING, AgentState.EXECUTING)
        self.add_edge(AgentState.EXECUTING, AgentState.REVIEWING)
        self.add_edge(AgentState.REVIEWING, AgentState.COMPLETED)
        self.add_edge(AgentState.REVIEWING, AgentState.FAILED)
        self.add_edge(AgentState.FAILED, AgentState.PLANNING)  # 失败后重新规划

    def add_node(self, state: AgentState, handler: Callable):
        """添加状态节点"""
        self.nodes[state] = handler

    def add_edge(self, from_state: AgentState, to_state: AgentState):
        """添加状态转移边"""
        if from_state not in self.edges:
            self.edges[from_state] = []
        self.edges[from_state].append(to_state)

    async def _initialized_state(self, thread_state: ThreadState) -> ThreadState:
        """初始化状态处理"""
        print(f"[StateGraph] 状态: {AgentState.INITIALIZED.value} - 系统初始化")
        thread_state["current_state"] = AgentState.PLANNING
        thread_state["messages"].append(
            {
                "role": "system",
                "content": "系统初始化完成，开始规划任务",
                "timestamp": datetime.now().isoformat(),
            }
        )
        return thread_state

    async def _planning_state(self, thread_state: ThreadState) -> ThreadState:
        """规划状态处理"""
        print(f"[StateGraph] 状态: {AgentState.PLANNING.value} - 任务规划中")

        # 模拟规划过程
        await asyncio.sleep(0.2)

        # 根据消息历史确定下一步动作
        last_message = (
            thread_state["messages"][-1]["content"] if thread_state["messages"] else ""
        )

        if "计算" in last_message or "calculate" in last_message:
            thread_state["next_action"] = "calculate"
        elif "搜索" in last_message or "search" in last_message:
            thread_state["next_action"] = "search"
        elif "分析" in last_message or "analyze" in last_message:
            thread_state["next_action"] = "analyze"
        else:
            thread_state["next_action"] = "search"  # 默认搜索

        thread_state["current_state"] = AgentState.EXECUTING
        thread_state["messages"].append(
            {
                "role": "planner",
                "content": f"规划完成，下一步执行: {thread_state['next_action']}",
                "timestamp": datetime.now().isoformat(),
            }
        )

        return thread_state

    async def _executing_state(self, thread_state: ThreadState) -> ThreadState:
        """执行状态处理"""
        print(f"[StateGraph] 状态: {AgentState.EXECUTING.value} - 执行任务")

        # 这里可以集成实际的LeadAgent执行
        # 简单模拟执行
        await asyncio.sleep(0.3)

        thread_state["result"] = {
            "success": True,
            "action": thread_state["next_action"],
            "data": f"{thread_state['next_action']} 执行完成",
            "timestamp": datetime.now().isoformat(),
        }

        thread_state["current_state"] = AgentState.REVIEWING
        thread_state["messages"].append(
            {
                "role": "executor",
                "content": f"执行完成: {thread_state['next_action']}",
                "timestamp": datetime.now().isoformat(),
            }
        )

        return thread_state

    async def _reviewing_state(self, thread_state: ThreadState) -> ThreadState:
        """评审状态处理"""
        print(f"[StateGraph] 状态: {AgentState.REVIEWING.value} - 评审结果")

        await asyncio.sleep(0.2)

        # 模拟评审逻辑
        if thread_state["result"] and thread_state["result"].get("success"):
            thread_state["current_state"] = AgentState.COMPLETED
            thread_state["messages"].append(
                {
                    "role": "reviewer",
                    "content": "评审通过，任务完成",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            thread_state["current_state"] = AgentState.FAILED
            thread_state["error"] = "评审未通过"
            thread_state["messages"].append(
                {
                    "role": "reviewer",
                    "content": "评审未通过，任务失败",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        return thread_state

    async def _completed_state(self, thread_state: ThreadState) -> ThreadState:
        """完成状态处理"""
        print(f"[StateGraph] 状态: {AgentState.COMPLETED.value} - 任务完成")

        thread_state["messages"].append(
            {
                "role": "system",
                "content": f"任务流程执行完成，最终状态: {thread_state['current_state'].value}",
                "timestamp": datetime.now().isoformat(),
            }
        )

        return thread_state

    async def _failed_state(self, thread_state: ThreadState) -> ThreadState:
        """失败状态处理"""
        print(f"[StateGraph] 状态: {AgentState.FAILED.value} - 任务失败")

        thread_state["messages"].append(
            {
                "role": "system",
                "content": f"任务失败，错误: {thread_state.get('error', '未知错误')}",
                "timestamp": datetime.now().isoformat(),
            }
        )

        return thread_state

    async def execute(self, initial_state: ThreadState) -> ThreadState:
        """执行状态图"""
        current_state = initial_state["current_state"]

        while current_state not in [AgentState.COMPLETED, AgentState.FAILED]:
            if current_state not in self.nodes:
                raise ValueError(f"未知状态: {current_state}")

            # 执行当前状态处理
            handler = self.nodes[current_state]
            initial_state = await handler(initial_state)

            # 获取下一个状态
            current_state = initial_state["current_state"]

            # 检查是否有合法的转移
            if current_state not in self.edges.get(initial_state["current_state"], []):
                print(
                    f"[StateGraph] 警告: 非法的状态转移 {initial_state['current_state']} -> {current_state}"
                )

        return initial_state


# ============================================================================
# 第三部分：模块化架构演示
# ============================================================================


class DeerFlowArchitectureDemo:
    """DeerFlow架构演示主类"""

    def __init__(self):
        # 初始化四层架构组件
        self.tool_system = ToolSystem()
        self.middleware_chain = MiddlewareChain()
        self.subagents = Subagents()
        self.lead_agent = LeadAgent(
            self.tool_system, self.middleware_chain, self.subagents
        )

        # 初始化状态图
        self.state_graph = StateGraph()

        # 演示统计
        self.demo_stats = {
            "requests_processed": 0,
            "successful_requests": 0,
            "state_transitions": 0,
            "tools_used": {},
            "subagents_called": {},
        }

    async def demonstrate_four_layer_architecture(self):
        """演示四层架构"""
        print("\n" + "=" * 60)
        print("演示1: 四层架构工作流程")
        print("=" * 60)

        # 测试请求
        test_requests = [
            {
                "action": "calculate",
                "expression": "3 * 7 + 5",
                "user_id": "user_001",
                "headers": {"Authorization": "Bearer valid-token-123"},
            },
            {
                "action": "search",
                "query": "AI Agent 发展趋势",
                "user_id": "user_002",
                "headers": {"Authorization": "Bearer valid-token-123"},
            },
            {
                "action": "analyze",
                "data": [10, 20, 30, 40, 50],
                "user_id": "user_003",
                "headers": {"Authorization": "Bearer valid-token-123"},
            },
            {
                "action": "generate_report",
                "topic": "机器学习",
                "format": "markdown",
                "user_id": "user_004",
                "headers": {"Authorization": "Bearer valid-token-123"},
            },
        ]

        for i, request in enumerate(test_requests, 1):
            print(f"\n--- 测试请求 {i} ---")
            result = await self.lead_agent.handle_request(request)

            self.demo_stats["requests_processed"] += 1
            if result.get("success"):
                self.demo_stats["successful_requests"] += 1

            # 更新工具使用统计
            if result.get("tool_used"):
                tool = result["tool_used"]
                self.demo_stats["tools_used"][tool] = (
                    self.demo_stats["tools_used"].get(tool, 0) + 1
                )

            # 打印结果摘要
            print(f"结果: {result.get('success', False)}")
            if result.get("error"):
                print(f"错误: {result['error']}")

        print("\n四层架构演示完成!")
        self._print_demo_stats()

    async def demonstrate_state_graph(self):
        """演示状态图"""
        print("\n" + "=" * 60)
        print("演示2: 状态图 (StateGraph) 工作流程")
        print("=" * 60)

        # 初始化线程状态
        initial_thread_state: ThreadState = {
            "messages": [
                {
                    "role": "user",
                    "content": "请帮我计算一下25乘以4的结果",
                    "timestamp": datetime.now().isoformat(),
                }
            ],
            "current_state": AgentState.INITIALIZED,
            "next_action": None,
            "result": None,
            "error": None,
            "metadata": {"user_id": "demo_user"},
        }

        print("初始状态:")
        print(json.dumps(initial_thread_state, indent=2, ensure_ascii=False))

        # 执行状态图
        print("\n开始状态转移...")
        final_state = await self.state_graph.execute(initial_thread_state)

        # 统计状态转移
        states_visited = [
            msg["content"]
            for msg in final_state["messages"]
            if "状态:" in msg.get("content", "")
        ]
        self.demo_stats["state_transitions"] = len(states_visited)

        print("\n最终状态:")
        print(json.dumps(final_state, indent=2, ensure_ascii=False))

        print(
            f"\n状态转移路径: {initial_thread_state['current_state'].value} -> {final_state['current_state'].value}"
        )
        print("消息历史:")
        for msg in final_state["messages"]:
            print(f"  [{msg['role']}] {msg['content']}")

    async def demonstrate_modular_design(self):
        """演示模块化设计优势"""
        print("\n" + "=" * 60)
        print("演示3: 模块化设计优势")
        print("=" * 60)

        # 演示动态添加中间件
        print("1. 动态添加自定义中间件:")

        async def custom_middleware(
            request: Dict[str, Any], next_fn: Callable
        ) -> Dict[str, Any]:
            """自定义中间件示例"""
            print(f"[Custom-Middleware] 处理请求: {request.get('action')}")
            # 添加自定义逻辑
            request["custom_field"] = "custom_value"
            response = await next_fn(request)
            response["processed_by_custom_middleware"] = True
            return response

        self.middleware_chain.add_middleware(custom_middleware)
        print("  已成功添加自定义中间件")

        # 演示动态添加工具
        print("\n2. 动态添加自定义工具:")

        async def custom_tool(query: str) -> Dict[str, Any]:
            """自定义工具示例"""
            return {
                "success": True,
                "result": f"自定义工具处理: {query}",
                "tool_used": "custom_tool",
            }

        self.tool_system.tools["custom_tool"] = custom_tool
        print("  已成功添加自定义工具")

        # 测试扩展后的系统
        print("\n3. 测试扩展后的系统:")
        test_request = {
            "action": "search",
            "query": "测试自定义扩展",
            "user_id": "test_user",
            "headers": {"Authorization": "Bearer valid-token-123"},
        }

        result = await self.lead_agent.handle_request(test_request)
        print(f"  扩展测试结果: {result.get('success', False)}")
        print(
            f"  是否经过自定义中间件: {result.get('processed_by_custom_middleware', False)}"
        )

    def demonstrate_code_organization(self):
        """演示代码组织结构"""
        print("\n" + "=" * 60)
        print("演示4: 代码组织结构")
        print("=" * 60)

        # 模拟DeerFlow代码结构
        code_structure = {
            "deerflow/": {
                "agents/": {
                    "lead_agent/": ["agent.py", "state_manager.py", "config.py"],
                    "subagents/": [
                        "data_collector.py",
                        "quality_checker.py",
                        "report_generator.py",
                    ],
                },
                "tools/": {
                    "core_tools/": [
                        "calculator.py",
                        "web_search.py",
                        "data_analysis.py",
                    ],
                    "custom_tools/": ["__init__.py", "example_tool.py"],
                },
                "middleware/": {
                    "core/": [
                        "logging.py",
                        "auth.py",
                        "rate_limit.py",
                        "validation.py",
                    ],
                    "custom/": ["__init__.py", "example_middleware.py"],
                },
                "state/": {
                    "graph/": ["state_graph.py", "thread_state.py", "transitions.py"],
                    "persistence/": ["storage.py", "cache.py"],
                },
                "config/": ["settings.py", "validation.py", "loader.py"],
                "utils/": ["logging.py", "exceptions.py", "helpers.py"],
            }
        }

        def print_structure(structure: Dict[str, Any], indent: int = 0):
            for key, value in structure.items():
                if isinstance(value, dict):
                    print("  " * indent + f"📁 {key}")
                    print_structure(value, indent + 1)
                elif isinstance(value, list):
                    for item in value:
                        print("  " * (indent + 1) + f"📄 {item}")

        print("DeerFlow 代码结构模拟:")
        print_structure(code_structure)

        print("\n架构对应关系:")
        print("  📁 agents/lead_agent/     → Lead Agent层")
        print("  📁 middleware/           → Middleware Chain层")
        print("  📁 tools/                → Tool System层")
        print("  📁 agents/subagents/     → Subagents层")
        print("  📁 state/                → 状态管理模块")

    def _print_demo_stats(self):
        """打印演示统计"""
        print("\n" + "=" * 60)
        print("演示统计")
        print("=" * 60)

        stats = self.demo_stats
        print(f"总请求数: {stats['requests_processed']}")
        print(f"成功请求数: {stats['successful_requests']}")
        print(
            f"成功率: {stats['successful_requests'] / stats['requests_processed'] * 100:.1f}%"
        )
        print(f"状态转移次数: {stats['state_transitions']}")

        if stats["tools_used"]:
            print("\n工具使用统计:")
            for tool, count in stats["tools_used"].items():
                print(f"  {tool}: {count}次")

        if stats["subagents_called"]:
            print("\n子代理调用统计:")
            for agent, count in stats["subagents_called"].items():
                print(f"  {agent}: {count}次")

    async def run_full_demo(self):
        """运行完整演示"""
        print("🚀 DeerFlow 2.0 架构优势演示")
        print("=" * 60)

        try:
            await self.demonstrate_four_layer_architecture()
            await asyncio.sleep(1)

            await self.demonstrate_state_graph()
            await asyncio.sleep(1)

            await self.demonstrate_modular_design()
            await asyncio.sleep(1)

            self.demonstrate_code_organization()

            print("\n" + "=" * 60)
            print("🎉 演示完成!")
            print("=" * 60)
            print("\n架构优势总结:")
            print("  1. ✅ 四层架构清晰分离职责")
            print("  2. ✅ 状态机管理复杂工作流")
            print("  3. ✅ 模块化设计易于扩展")
            print("  4. ✅ 代码组织结构清晰")
            print("  5. ✅ 中间件链提供灵活处理")
            print("  6. ✅ 工具和子代理系统可插拔")

        except Exception as e:
            print(f"\n❌ 演示过程中出现错误: {e}")
            import traceback

            traceback.print_exc()


# ============================================================================
# 第四部分：架构优势分析
# ============================================================================


def analyze_architecture_advantages():
    """分析架构优势"""
    print("\n" + "=" * 60)
    print("DeerFlow 2.0 架构优势分析")
    print("=" * 60)

    advantages = {
        "模块化设计": {
            "描述": "四层架构清晰分离职责，每层专注特定功能",
            "好处": [
                "降低系统复杂度",
                "便于团队分工协作",
                "简化测试和维护",
                "支持独立升级和替换",
            ],
            "代码体现": "LeadAgent, MiddlewareChain, ToolSystem, Subagents类的分离",
        },
        "状态机管理": {
            "描述": "基于LangGraph StateGraph的状态机管理复杂工作流",
            "好处": [
                "可视化工作流状态",
                "支持复杂状态转移",
                "便于调试和监控",
                "提高系统可靠性",
            ],
            "代码体现": "StateGraph类和ThreadState数据结构的实现",
        },
        "可扩展性": {
            "描述": "模块化设计支持动态添加组件",
            "好处": [
                "轻松添加新工具和中间件",
                "支持自定义业务逻辑",
                "便于集成第三方服务",
                "适应不断变化的需求",
            ],
            "代码体现": "add_middleware(), add_tool()等方法",
        },
        "代码组织": {
            "描述": "清晰的目录结构和模块划分",
            "好处": [
                "提高代码可读性",
                "降低新人学习成本",
                "便于代码审查",
                "支持大规模团队协作",
            ],
            "代码体现": "模拟的deerflow/目录结构",
        },
        "中间件链": {
            "描述": "灵活的中间件链处理请求",
            "好处": [
                "支持横切关注点（日志、认证、限流）",
                "可配置的处理流程",
                "便于添加业务逻辑",
                "提高代码复用性",
            ],
            "代码体现": "MiddlewareChain类和中间件注册机制",
        },
    }

    for i, (advantage_name, details) in enumerate(advantages.items(), 1):
        print(f"\n{i}. {advantage_name}")
        print(f"   描述: {details['描述']}")
        print(f"   好处: {', '.join(details['好处'])}")
        print(f"   代码体现: {details['代码体现']}")

    print("\n" + "=" * 60)
    print("架构设计原则体现:")
    print("=" * 60)

    principles = [
        ("单一职责原则", "每个类/模块只负责一个特定功能"),
        ("开闭原则", "对扩展开放，对修改封闭"),
        ("依赖倒置原则", "高层模块不依赖低层模块，都依赖抽象"),
        ("接口隔离原则", "客户端不应依赖它不需要的接口"),
        ("迪米特法则", "一个对象应尽可能少了解其他对象"),
    ]

    for principle, description in principles:
        print(f"  ✅ {principle}: {description}")


# ============================================================================
# 主函数
# ============================================================================


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🏛️  DeerFlow 2.0 架构优势 - 课堂演示代码")
    print("=" * 60)
    print("课程: Day 1 第3节课 - DeerFlow 2.0架构优势")
    print("教师: 张老师")
    print("日期: 2024年3月25日")
    print("=" * 60)

    # 创建演示实例
    demo = DeerFlowArchitectureDemo()

    # 运行完整演示
    await demo.run_full_demo()

    # 分析架构优势
    analyze_architecture_advantages()

    print("\n" + "=" * 60)
    print("📚 课堂总结")
    print("=" * 60)
    print("""
本节课通过代码演示了DeerFlow 2.0的架构优势：

1. **四层架构设计**: Lead Agent, Middleware Chain, Tool System, Subagents
   - 清晰职责分离，降低系统复杂度
   - 支持模块化开发和团队协作

2. **状态机管理**: 基于LangGraph StateGraph
   - 可视化工作流状态
   - 支持复杂状态转移和错误恢复

3. **模块化与可扩展性**:
   - 动态添加中间件和工具
   - 灵活的插件系统
   - 易于集成和定制

4. **代码组织结构**:
   - 清晰的目录结构
   - 合理的模块划分
   - 便于维护和扩展

这些架构优势使得DeerFlow能够：
- ✅ 快速响应业务需求变化
- ✅ 支持大规模团队协作开发  
- ✅ 保证系统稳定性和可靠性
- ✅ 降低长期维护成本
- ✅ 适应不同规模和复杂度的项目
    """)

    print("\n🎯 课后思考:")
    print("  1. 四层架构适合哪些类型的项目？不适合哪些？")
    print("  2. 状态机设计如何提高系统的可靠性和可维护性？")
    print("  3. 如何根据具体项目需求调整架构层次？")
    print("  4. 模块化设计在团队协作中的价值是什么？")


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
