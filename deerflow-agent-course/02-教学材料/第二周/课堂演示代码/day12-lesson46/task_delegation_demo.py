#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 12 Lesson 46: 任务委派决策 (Task Delegation Decision)

本文件演示任务委派决策系统的设计和实现，包括：
1. 决策因素 - 任务类型、能力匹配、负载均衡、历史性能
2. 委派策略 - 工具、子代理、多子代理并行、混合模式
3. 智能委派器 - 综合多因素的智能决策引擎
4. 决策解释 - 提供决策原因和置信度

使用示例:
    python task_delegation_demo.py          # 运行基本演示
    python task_delegation_demo.py --test   # 运行测试套件
    python task_delegation_demo.py --demo   # 运行完整演示
    python task_delegation_demo.py --help   # 显示帮助信息
"""

import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import random
import uuid


class TaskType(Enum):
    """任务类型枚举"""
    CODE = "code"            # 代码相关任务
    DATA = "data"            # 数据分析任务
    SYSTEM = "system"        # 系统操作任务
    NETWORK = "network"      # 网络请求任务
    TEXT = "text"             # 文本处理任务
    GENERAL = "general"      # 通用任务


class DelegationStrategy(Enum):
    """委派策略枚举"""
    TOOL = "tool"                    # 使用工具
    SUBAGENT = "subagent"            # 使用子代理
    MULTI_SUBAGENT = "multi"         # 多子代理并行
    HYBRID = "hybrid"                # 混合模式


class AgentType(Enum):
    """代理类型枚举"""
    GENERIC = "generic"              # 通用代理
    BASH = "bash"                    # Bash代理
    PYTHON = "python"                # Python代理
    SQL = "sql"                      # SQL代理
    WEB = "web"                      # Web代理


@dataclass
class AgentCapability:
    """代理能力定义"""
    agent_type: AgentType            # 代理类型
    capabilities: List[str]          # 能力列表
    max_concurrent: int = 5          # 最大并发数
    avg_response_time: float = 1.0   # 平均响应时间（秒）


@dataclass
class AgentInfo:
    """代理信息"""
    name: str                        # 代理名称
    agent_type: AgentType            # 代理类型
    capabilities: List[str]          # 能力列表
    current_load: int = 0            # 当前负载
    max_load: int = 10               # 最大负载
    success_count: int = 0           # 成功次数
    failure_count: int = 0           # 失败次数
    total_response_time: float = 0.0 # 总响应时间
    is_available: bool = True        # 是否可用
    
    def get_load_percentage(self) -> float:
        """获取负载百分比"""
        return (self.current_load / self.max_load * 100) if self.max_load > 0 else 0
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total > 0 else 0
    
    def get_avg_response_time(self) -> float:
        """获取平均响应时间"""
        return (self.total_response_time / self.success_count) if self.success_count > 0 else float('inf')
    
    def get_capability_score(self, required_capabilities: List[str]) -> float:
        """获取能力匹配分数"""
        if not required_capabilities:
            return 1.0
        matched = len(set(required_capabilities) & set(self.capabilities))
        return matched / len(required_capabilities)


@dataclass
class Task:
    """任务定义"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""            # 任务描述
    task_type: TaskType = TaskType.GENERAL  # 任务类型
    required_capabilities: List[str] = field(default_factory=list)  # 所需能力
    priority: int = 1                # 优先级（1-5）
    estimated_complexity: float = 1.0  # 估计复杂度
    timeout: float = 300.0           # 超时时间


@dataclass
class DelegationDecision:
    """委派决策结果"""
    task_id: str                     # 任务ID
    selected_agent: str              # 选中的代理名称
    strategy: DelegationStrategy     # 委派策略
    confidence: float                # 决策置信度（0-1）
    reasons: List[str] = field(default_factory=list)  # 决策原因
    alternatives: List[str] = field(default_factory=list)  # 替代方案
    estimated_time: float = 0.0      # 预估执行时间
    decision_time: float = 0.0       # 决策耗时
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "selected_agent": self.selected_agent,
            "strategy": self.strategy.value,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "alternatives": self.alternatives,
            "estimated_time": self.estimated_time,
            "decision_time": self.decision_time
        }


class TaskClassifier:
    """任务分类器"""
    
    # 关键词到任务类型的映射
    KEYWORD_MAPPING: Dict[str, TaskType] = {
        # 代码相关
        "代码": TaskType.CODE, "编程": TaskType.CODE, "开发": TaskType.CODE,
        "函数": TaskType.CODE, "类": TaskType.CODE, "调试": TaskType.CODE,
        "code": TaskType.CODE, "program": TaskType.CODE, "develop": TaskType.CODE,
        
        # 数据相关
        "数据": TaskType.DATA, "分析": TaskType.DATA, "统计": TaskType.DATA,
        "图表": TaskType.DATA, "计算": TaskType.DATA, "查询": TaskType.DATA,
        "data": TaskType.DATA, "analyze": TaskType.DATA, "statistics": TaskType.DATA,
        
        # 系统相关
        "文件": TaskType.SYSTEM, "目录": TaskType.SYSTEM, "系统": TaskType.SYSTEM,
        "进程": TaskType.SYSTEM, "服务": TaskType.SYSTEM, "权限": TaskType.SYSTEM,
        "file": TaskType.SYSTEM, "directory": TaskType.SYSTEM, "system": TaskType.SYSTEM,
        
        # 网络相关
        "网络": TaskType.NETWORK, "请求": TaskType.NETWORK, "API": TaskType.NETWORK,
        "HTTP": TaskType.NETWORK, "URL": TaskType.NETWORK, "抓取": TaskType.NETWORK,
        "network": TaskType.NETWORK, "request": TaskType.NETWORK, "api": TaskType.NETWORK,
        
        # 文本相关
        "文本": TaskType.TEXT, "字符串": TaskType.TEXT, "格式": TaskType.TEXT,
        "转换": TaskType.TEXT, "解析": TaskType.TEXT, "提取": TaskType.TEXT,
        "text": TaskType.TEXT, "string": TaskType.TEXT, "format": TaskType.TEXT,
    }
    
    # 能力关键词映射
    CAPABILITY_MAPPING: Dict[str, List[str]] = {
        TaskType.CODE.value: ["code_execution", "debugging", "python"],
        TaskType.DATA.value: ["data_analysis", "statistics", "query"],
        TaskType.SYSTEM.value: ["shell_execution", "file_operations"],
        TaskType.NETWORK.value: ["web_scraping", "api_calling", "http"],
        TaskType.TEXT.value: ["text_processing", "parsing", "formatting"],
        TaskType.GENERAL.value: ["general"],
    }
    
    @classmethod
    def classify(cls, description: str) -> Tuple[TaskType, List[str], float]:
        """
        分类任务
        
        返回: (任务类型, 所需能力, 复杂度估计)
        """
        description_lower = description.lower()
        
        # 统计各类型的关键词匹配数
        type_scores: Dict[TaskType, int] = {}
        for keyword, task_type in cls.KEYWORD_MAPPING.items():
            if keyword in description_lower:
                type_scores[task_type] = type_scores.get(task_type, 0) + 1
        
        # 选择匹配最多的类型
        if type_scores:
            task_type = max(type_scores, key=type_scores.get)
        else:
            task_type = TaskType.GENERAL
        
        # 获取所需能力
        capabilities = cls.CAPABILITY_MAPPING.get(task_type.value, ["general"])
        
        # 估计复杂度（基于描述长度和关键词数量）
        word_count = len(description.split())
        complexity = min(5.0, 1.0 + word_count * 0.1 + type_scores.get(task_type, 0) * 0.5)
        
        return task_type, capabilities, complexity


class DelegationDecisionEngine:
    """委派决策引擎"""
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.decision_history: List[DelegationDecision] = []
        
        # 决策权重配置
        self.weights = {
            "capability_match": 0.40,    # 能力匹配权重
            "load_balance": 0.25,        # 负载均衡权重
            "success_rate": 0.20,        # 成功率权重
            "response_time": 0.15,       # 响应时间权重
        }
    
    def register_agent(self, agent: AgentInfo):
        """注册代理"""
        self.agents[agent.name] = agent
        logging.info(f"代理已注册: {agent.name} ({agent.agent_type.value})")
    
    def unregister_agent(self, agent_name: str):
        """注销代理"""
        if agent_name in self.agents:
            del self.agents[agent_name]
            logging.info(f"代理已注销: {agent_name}")
    
    def decide(self, task: Task) -> DelegationDecision:
        """
        做出委派决策
        
        Args:
            task: 任务定义
            
        Returns:
            DelegationDecision: 委派决策结果
        """
        start_time = datetime.now()
        reasons = []
        
        # 获取可用代理
        available_agents = [a for a in self.agents.values() if a.is_available]
        
        if not available_agents:
            return DelegationDecision(
                task_id=task.task_id,
                selected_agent="none",
                strategy=DelegationStrategy.TOOL,
                confidence=0.0,
                reasons=["没有可用的代理"],
                decision_time=(datetime.now() - start_time).total_seconds()
            )
        
        # 分析任务
        task_type, required_capabilities, complexity = TaskClassifier.classify(task.description)
        task.task_type = task_type
        task.required_capabilities = required_capabilities
        task.estimated_complexity = complexity
        
        reasons.append(f"任务类型: {task_type.value}")
        reasons.append(f"所需能力: {', '.join(required_capabilities)}")
        
        # 计算每个代理的得分
        agent_scores: Dict[str, float] = {}
        for agent in available_agents:
            score, score_reasons = self._calculate_agent_score(agent, task)
            agent_scores[agent.name] = score
        
        # 选择得分最高的代理
        if agent_scores:
            selected_agent_name = max(agent_scores, key=agent_scores.get)
            selected_agent = self.agents[selected_agent_name]
            confidence = agent_scores[selected_agent_name]
            
            reasons.append(f"选中代理: {selected_agent_name}")
            reasons.append(f"综合得分: {confidence:.2f}")
            
            # 获取替代方案
            sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
            alternatives = [name for name, score in sorted_agents[1:3] if score > 0.3]
            
            # 确定策略
            strategy = self._determine_strategy(task, selected_agent, complexity)
            
            # 估计执行时间
            estimated_time = selected_agent.get_avg_response_time() * complexity
            
        else:
            selected_agent_name = "generic"
            confidence = 0.3
            strategy = DelegationStrategy.TOOL
            alternatives = []
            estimated_time = 30.0
            reasons.append("无匹配代理，使用默认")
        
        decision_time = (datetime.now() - start_time).total_seconds()
        
        decision = DelegationDecision(
            task_id=task.task_id,
            selected_agent=selected_agent_name,
            strategy=strategy,
            confidence=min(1.0, confidence),
            reasons=reasons,
            alternatives=alternatives,
            estimated_time=estimated_time,
            decision_time=decision_time
        )
        
        # 记录决策历史
        self.decision_history.append(decision)
        
        return decision
    
    def _calculate_agent_score(self, agent: AgentInfo, task: Task) -> Tuple[float, List[str]]:
        """
        计算代理得分
        
        返回: (得分, 评分明细)
        """
        reasons = []
        
        # 1. 能力匹配得分
        capability_score = agent.get_capability_score(task.required_capabilities)
        reasons.append(f"能力匹配: {capability_score:.2f}")
        
        # 2. 负载均衡得分（负载越低得分越高）
        load_percentage = agent.get_load_percentage()
        load_score = max(0, 1.0 - load_percentage / 100)
        reasons.append(f"负载得分: {load_score:.2f} (负载: {load_percentage:.0f}%)")
        
        # 3. 成功率得分
        success_rate = agent.get_success_rate()
        success_score = success_rate / 100 if success_rate > 0 else 0.5
        reasons.append(f"成功率得分: {success_score:.2f} (成功率: {success_rate:.0f}%)")
        
        # 4. 响应时间得分（时间越短得分越高）
        avg_response = agent.get_avg_response_time()
        response_score = max(0, 1.0 - min(avg_response, 10) / 10) if avg_response < float('inf') else 0.5
        reasons.append(f"响应时间得分: {response_score:.2f}")
        
        # 加权总分
        total_score = (
            self.weights["capability_match"] * capability_score +
            self.weights["load_balance"] * load_score +
            self.weights["success_rate"] * success_score +
            self.weights["response_time"] * response_score
        )
        
        return total_score, reasons
    
    def _determine_strategy(self, task: Task, agent: AgentInfo, complexity: float) -> DelegationStrategy:
        """确定委派策略"""
        # 复杂任务可能需要混合模式
        if complexity > 3.0:
            return DelegationStrategy.HYBRID
        
        # 高并发任务可能需要多代理并行
        if task.priority >= 4:
            return DelegationStrategy.MULTI_SUBAGENT
        
        # 根据代理类型决定
        if agent.agent_type == AgentType.GENERIC:
            return DelegationStrategy.SUBAGENT
        
        return DelegationStrategy.TOOL
    
    def update_agent_result(self, agent_name: str, success: bool, response_time: float):
        """更新代理执行结果"""
        if agent_name in self.agents:
            agent = self.agents[agent_name]
            if success:
                agent.success_count += 1
            else:
                agent.failure_count += 1
            agent.total_response_time += response_time
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_decisions = len(self.decision_history)
        if total_decisions == 0:
            return {"total_decisions": 0}
        
        # 统计各代理被选中的次数
        agent_selections: Dict[str, int] = {}
        for decision in self.decision_history:
            agent_selections[decision.selected_agent] = agent_selections.get(decision.selected_agent, 0) + 1
        
        # 统计策略分布
        strategy_distribution: Dict[str, int] = {}
        for decision in self.decision_history:
            strategy_distribution[decision.strategy.value] = strategy_distribution.get(decision.strategy.value, 0) + 1
        
        # 平均置信度
        avg_confidence = sum(d.confidence for d in self.decision_history) / total_decisions
        
        return {
            "total_decisions": total_decisions,
            "avg_confidence": avg_confidence,
            "agent_selections": agent_selections,
            "strategy_distribution": strategy_distribution,
            "agents_registered": len(self.agents)
        }


class DelegationTestSuite:
    """委派决策测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_task_classification", self.test_task_classification),
            ("test_agent_registration", self.test_agent_registration),
            ("test_basic_delegation", self.test_basic_delegation),
            ("test_load_balancing", self.test_load_balancing),
            ("test_capability_matching", self.test_capability_matching),
        ]
    
    def test_task_classification(self) -> tuple:
        """测试任务分类"""
        try:
            # 测试代码任务
            task_type, capabilities, complexity = TaskClassifier.classify("编写一个Python函数")
            if task_type != TaskType.CODE:
                return False, f"代码任务分类失败: {task_type}"
            
            # 测试数据任务
            task_type, capabilities, complexity = TaskClassifier.classify("分析销售数据统计")
            if task_type != TaskType.DATA:
                return False, f"数据任务分类失败: {task_type}"
            
            # 测试系统任务
            task_type, capabilities, complexity = TaskClassifier.classify("查看文件目录内容")
            if task_type != TaskType.SYSTEM:
                return False, f"系统任务分类失败: {task_type}"
            
            # 测试网络任务
            task_type, capabilities, complexity = TaskClassifier.classify("调用API获取网络数据")
            if task_type != TaskType.NETWORK:
                return False, f"网络任务分类失败: {task_type}"
            
            return True, "任务分类测试通过"
        except Exception as e:
            return False, f"任务分类异常: {e}"
    
    def test_agent_registration(self) -> tuple:
        """测试代理注册"""
        try:
            engine = DelegationDecisionEngine()
            
            # 注册代理
            agent1 = AgentInfo(
                name="python_agent",
                agent_type=AgentType.PYTHON,
                capabilities=["code_execution", "debugging", "python"]
            )
            agent2 = AgentInfo(
                name="bash_agent",
                agent_type=AgentType.BASH,
                capabilities=["shell_execution", "file_operations"]
            )
            
            engine.register_agent(agent1)
            engine.register_agent(agent2)
            
            if len(engine.agents) != 2:
                return False, f"注册数量不正确: {len(engine.agents)}"
            
            # 测试注销
            engine.unregister_agent("python_agent")
            if len(engine.agents) != 1:
                return False, "注销失败"
            
            return True, "代理注册测试通过"
        except Exception as e:
            return False, f"代理注册异常: {e}"
    
    def test_basic_delegation(self) -> tuple:
        """测试基本委派决策"""
        try:
            engine = DelegationDecisionEngine()
            
            # 注册代理
            engine.register_agent(AgentInfo(
                name="python_agent",
                agent_type=AgentType.PYTHON,
                capabilities=["code_execution", "debugging", "python"]
            ))
            engine.register_agent(AgentInfo(
                name="data_agent",
                agent_type=AgentType.GENERIC,
                capabilities=["data_analysis", "statistics"]
            ))
            
            # 测试代码任务委派
            task = Task(description="编写一个排序算法")
            decision = engine.decide(task)
            
            if decision.selected_agent != "python_agent":
                return False, f"委派决策失败: {decision.selected_agent}"
            
            if decision.confidence < 0.5:
                return False, f"置信度过低: {decision.confidence}"
            
            # 测试数据任务委派
            task = Task(description="分析销售数据")
            decision = engine.decide(task)
            
            if decision.selected_agent != "data_agent":
                return False, f"数据任务委派失败: {decision.selected_agent}"
            
            return True, "基本委派决策测试通过"
        except Exception as e:
            return False, f"基本委派异常: {e}"
    
    def test_load_balancing(self) -> tuple:
        """测试负载均衡"""
        try:
            engine = DelegationDecisionEngine()
            
            # 注册两个相同能力的代理，不同负载
            agent1 = AgentInfo(
                name="agent1",
                agent_type=AgentType.GENERIC,
                capabilities=["code_execution"],
                current_load=8,
                max_load=10
            )
            agent2 = AgentInfo(
                name="agent2",
                agent_type=AgentType.GENERIC,
                capabilities=["code_execution"],
                current_load=2,
                max_load=10
            )
            
            engine.register_agent(agent1)
            engine.register_agent(agent2)
            
            # 委派任务
            task = Task(description="执行代码")
            decision = engine.decide(task)
            
            # 应该选择负载较低的agent2
            if decision.selected_agent != "agent2":
                return False, f"负载均衡失败: 选中了{decision.selected_agent}，期望agent2"
            
            return True, "负载均衡测试通过"
        except Exception as e:
            return False, f"负载均衡异常: {e}"
    
    def test_capability_matching(self) -> tuple:
        """测试能力匹配"""
        try:
            engine = DelegationDecisionEngine()
            
            # 注册代理
            engine.register_agent(AgentInfo(
                name="bash_agent",
                agent_type=AgentType.BASH,
                capabilities=["shell_execution", "file_operations"]
            ))
            engine.register_agent(AgentInfo(
                name="python_agent",
                agent_type=AgentType.PYTHON,
                capabilities=["code_execution", "debugging"]
            ))
            
            # 测试Bash任务
            task = Task(description="执行ls命令")
            decision = engine.decide(task)
            
            # 系统任务应该委派给bash_agent
            task_type, caps, _ = TaskClassifier.classify(task.description)
            if task_type == TaskType.SYSTEM and decision.selected_agent != "bash_agent":
                return False, f"能力匹配失败: {decision.selected_agent}"
            
            return True, "能力匹配测试通过"
        except Exception as e:
            return False, f"能力匹配异常: {e}"
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行任务委派决策测试套件...")
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
    print("🎓 Day 12 Lesson 46: 任务委派决策演示")
    print("=" * 60)
    
    # 1. 创建决策引擎
    engine = DelegationDecisionEngine()
    
    # 2. 注册代理
    print("\n1. 注册代理:")
    agents = [
        AgentInfo("python_expert", AgentType.PYTHON, ["code_execution", "debugging", "python"], 
                  current_load=2, success_count=100, failure_count=10, total_response_time=50),
        AgentInfo("bash_expert", AgentType.BASH, ["shell_execution", "file_operations"],
                  current_load=5, success_count=80, failure_count=5, total_response_time=30),
        AgentInfo("data_expert", AgentType.GENERIC, ["data_analysis", "statistics", "query"],
                  current_load=1, success_count=60, failure_count=3, total_response_time=20),
        AgentInfo("web_expert", AgentType.WEB, ["web_scraping", "api_calling", "http"],
                  current_load=3, success_count=50, failure_count=8, total_response_time=40),
    ]
    
    for agent in agents:
        engine.register_agent(agent)
        print(f"   ✅ {agent.name}: 能力={agent.capabilities}, 负载={agent.current_load}/{agent.max_load}")
    
    # 3. 测试任务委派
    print("\n2. 任务委派演示:")
    
    test_tasks = [
        Task(description="编写一个Python排序函数"),
        Task(description="执行ls -la命令查看目录"),
        Task(description="分析销售数据并生成统计报告"),
        Task(description="调用REST API获取天气数据"),
        Task(description="解析JSON格式的配置文件"),
    ]
    
    for task in test_tasks:
        decision = engine.decide(task)
        print(f"\n   📋 任务: {task.description}")
        print(f"      选中: {decision.selected_agent}")
        print(f"      策略: {decision.strategy.value}")
        print(f"      置信度: {decision.confidence:.2f}")
        print(f"      原因: {'; '.join(decision.reasons[:2])}")
        if decision.alternatives:
            print(f"      替代: {', '.join(decision.alternatives)}")
    
    # 4. 负载均衡演示
    print("\n3. 负载均衡演示:")
    
    # 模拟python_agent高负载
    engine.agents["python_expert"].current_load = 9
    
    task = Task(description="开发一个API接口")
    decision = engine.decide(task)
    print(f"   任务: {task.description}")
    print(f"   python_expert负载: 9/10")
    print(f"   选中: {decision.selected_agent}")
    print(f"   原因: {decision.reasons[-1]}")
    
    # 5. 统计信息
    print("\n4. 统计信息:")
    stats = engine.get_statistics()
    print(f"   总决策数: {stats['total_decisions']}")
    print(f"   平均置信度: {stats['avg_confidence']:.2f}")
    print(f"   代理选择分布: {stats['agent_selections']}")
    print(f"   策略分布: {stats['strategy_distribution']}")
    
    print("\n演示完成!")


def run_tests():
    """运行测试套件"""
    test_suite = DelegationTestSuite()
    report = test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 任务委派决策测试套件验证通过")
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
