#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 10 Lesson 37: SubagentExecutor架构 (SubagentExecutor Architecture)

本文件演示子代理系统的完整实现，包括：
1. BaseSubagent抽象基类 - 定义子代理的标准接口和生命周期管理
2. SubagentConfig数据模型 - 定义子代理配置参数和验证规则
3. SubagentResult数据模型 - 定义子代理执行结果和状态信息
4. SubagentExecutor执行引擎 - 管理子代理注册、任务调度、执行监控
5. 专用子代理实现 - 代码专家、数学专家、数据分析等子代理示例

使用示例:
    python subagent_demo.py          # 运行基本演示
    python subagent_demo.py --test   # 运行测试套件
    python subagent_demo.py --demo   # 运行完整演示
    python subagent_demo.py --help   # 显示帮助信息
"""

import os
import sys
import json
import time
import asyncio
import argparse
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================

class SubagentStatus(Enum):
    """子代理状态枚举"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 执行成功
    FAILED = "failed"        # 执行失败
    CANCELLED = "cancelled"  # 已取消
    TIMEOUT = "timeout"      # 执行超时

class SubagentType(Enum):
    """子代理类型枚举"""
    CODE_EXPERT = "code_expert"          # 代码专家子代理
    DATA_ANALYSIS = "data_analysis"      # 数据分析子代理
    MATH_EXPERT = "math_expert"          # 数学专家子代理
    SECURITY_AUDITOR = "security_auditor"  # 安全审计子代理
    DOCUMENT_GENERATOR = "document_generator"  # 文档生成子代理

@dataclass
class SubagentConfig:
    """子代理配置数据类"""
    subagent_id: str                          # 子代理实例ID（唯一）
    subagent_type: SubagentType               # 子代理类型
    priority: int = 50                        # 优先级（0-100，越大越优先）
    max_execution_time: float = 30.0          # 最大执行时间（秒）
    memory_limit_mb: int = 512                # 内存限制（MB）
    cpu_shares: int = 512                     # CPU份额
    description: str = ""                     # 子代理描述
    parameters: Dict[str, Any] = field(default_factory=dict)  # 自定义参数
    created_at: float = field(default_factory=time.time)      # 创建时间
    
    def validate(self) -> Tuple[bool, str]:
        """验证配置参数"""
        if not self.subagent_id:
            return False, "subagent_id不能为空"
        if not isinstance(self.subagent_type, SubagentType):
            return False, f"无效的subagent_type: {self.subagent_type}"
        if self.priority < 0 or self.priority > 100:
            return False, f"priority必须在0-100之间: {self.priority}"
        if self.max_execution_time <= 0:
            return False, f"max_execution_time必须大于0: {self.max_execution_time}"
        if self.memory_limit_mb <= 0:
            return False, f"memory_limit_mb必须大于0: {self.memory_limit_mb}"
        return True, "配置验证通过"
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['subagent_type'] = self.subagent_type.value
        data['created_at_datetime'] = datetime.fromtimestamp(self.created_at).isoformat()
        return data

@dataclass
class SubagentResult:
    """子代理执行结果数据类"""
    subagent_id: str                          # 子代理实例ID
    task_id: str                              # 任务ID
    status: SubagentStatus                    # 执行状态
    result_data: Optional[Dict[str, Any]] = None  # 结果数据
    error_message: Optional[str] = None       # 错误信息
    error_traceback: Optional[str] = None     # 错误堆栈
    start_time: Optional[float] = None        # 开始时间
    end_time: Optional[float] = None          # 结束时间
    execution_time: Optional[float] = None    # 执行时长（秒）
    memory_usage_mb: Optional[float] = None   # 内存使用（MB）
    cpu_usage_percent: Optional[float] = None # CPU使用率（%）
    created_at: float = field(default_factory=time.time)      # 结果创建时间
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['start_time_datetime'] = datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None
        data['end_time_datetime'] = datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None
        data['created_at_datetime'] = datetime.fromtimestamp(self.created_at).isoformat()
        return data
    
    @classmethod
    def create_success_result(cls, subagent_id: str, task_id: str, 
                            result_data: Dict[str, Any],
                            start_time: float, end_time: float,
                            memory_usage_mb: float = None,
                            cpu_usage_percent: float = None) -> 'SubagentResult':
        """创建成功结果"""
        return cls(
            subagent_id=subagent_id,
            task_id=task_id,
            status=SubagentStatus.COMPLETED,
            result_data=result_data,
            start_time=start_time,
            end_time=end_time,
            execution_time=end_time - start_time,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent
        )
    
    @classmethod
    def create_error_result(cls, subagent_id: str, task_id: str,
                          error_message: str, error_traceback: str = None,
                          start_time: float = None, end_time: float = None) -> 'SubagentResult':
        """创建错误结果"""
        return cls(
            subagent_id=subagent_id,
            task_id=task_id,
            status=SubagentStatus.FAILED,
            error_message=error_message,
            error_traceback=error_traceback,
            start_time=start_time,
            end_time=end_time,
            execution_time=end_time - start_time if start_time and end_time else None
        )

# ============================================================================
# 第二部分：接口与协议实现
# ============================================================================

class SubagentError(Exception):
    """子代理基础异常"""
    pass

class ConfigurationError(SubagentError):
    """配置错误"""
    pass

class ExecutionError(SubagentError):
    """执行错误"""
    pass

class TimeoutError(SubagentError):
    """超时错误"""
    pass

class ResourceLimitError(SubagentError):
    """资源限制错误"""
    pass

class BaseSubagent(ABC):
    """子代理抽象基类"""
    
    def __init__(self, config: SubagentConfig):
        self.config = config
        self._status = SubagentStatus.PENDING
        self._start_time = None
        self._end_time = None
        self._result = None
        self._logger = logging.getLogger(f"Subagent-{config.subagent_id}")
        
        # 验证配置
        is_valid, message = config.validate()
        if not is_valid:
            raise ConfigurationError(f"配置验证失败: {message}")
    
    @property
    def status(self) -> SubagentStatus:
        """获取子代理状态"""
        return self._status
    
    @property
    def subagent_id(self) -> str:
        """获取子代理ID"""
        return self.config.subagent_id
    
    @property
    def subagent_type(self) -> SubagentType:
        """获取子代理类型"""
        return self.config.subagent_type
    
    @abstractmethod
    async def execute(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行子代理任务（抽象方法，必须由子类实现）
        
        Args:
            task_params: 任务参数
            
        Returns:
            Dict[str, Any]: 执行结果数据
            
        Raises:
            ExecutionError: 执行过程中发生错误
        """
        pass
    
    def validate_config(self) -> Tuple[bool, str]:
        """
        验证子代理配置
        
        Returns:
            Tuple[bool, str]: (是否有效, 验证消息)
        """
        # 基础配置验证
        return self.config.validate()
    
    async def cleanup(self) -> None:
        """
        清理子代理资源（可由子类重写）
        """
        self._logger.debug(f"清理子代理资源: {self.subagent_id}")
    
    async def run_task(self, task_id: str, task_params: Dict[str, Any]) -> SubagentResult:
        """
        运行子代理任务（完整生命周期）
        
        Args:
            task_id: 任务ID
            task_params: 任务参数
            
        Returns:
            SubagentResult: 执行结果
        """
        self._status = SubagentStatus.RUNNING
        self._start_time = time.time()
        
        try:
            # 执行前验证
            is_valid, message = self.validate_config()
            if not is_valid:
                raise ConfigurationError(f"配置验证失败: {message}")
            
            self._logger.info(f"开始执行任务: {task_id}")
            
            # 执行任务
            result_data = await asyncio.wait_for(
                self.execute(task_params),
                timeout=self.config.max_execution_time
            )
            
            # 执行成功
            self._end_time = time.time()
            self._status = SubagentStatus.COMPLETED
            
            result = SubagentResult.create_success_result(
                subagent_id=self.subagent_id,
                task_id=task_id,
                result_data=result_data,
                start_time=self._start_time,
                end_time=self._end_time
            )
            
            self._logger.info(f"任务执行成功: {task_id}, 耗时: {result.execution_time:.3f}秒")
            return result
            
        except asyncio.TimeoutError:
            # 超时处理
            self._end_time = time.time()
            self._status = SubagentStatus.TIMEOUT
            
            error_msg = f"任务执行超时（>{self.config.max_execution_time}秒）"
            self._logger.error(error_msg)
            
            return SubagentResult.create_error_result(
                subagent_id=self.subagent_id,
                task_id=task_id,
                error_message=error_msg,
                start_time=self._start_time,
                end_time=self._end_time
            )
            
        except Exception as e:
            # 其他异常处理
            self._end_time = time.time()
            self._status = SubagentStatus.FAILED
            
            import traceback
            error_traceback = traceback.format_exc()
            
            error_msg = f"任务执行失败: {str(e)}"
            self._logger.error(f"{error_msg}\n{error_traceback}")
            
            return SubagentResult.create_error_result(
                subagent_id=self.subagent_id,
                task_id=task_id,
                error_message=error_msg,
                error_traceback=error_traceback,
                start_time=self._start_time,
                end_time=self._end_time
            )
            
        finally:
            # 清理资源
            await self.cleanup()

# ============================================================================
# 第三部分：核心功能实现
# ============================================================================

class CodeExpertSubagent(BaseSubagent):
    """代码专家子代理"""
    
    async def execute(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """执行代码分析任务"""
        code = task_params.get("code", "")
        language = task_params.get("language", "python")
        analysis_type = task_params.get("analysis_type", "quality")
        
        if not code:
            raise ExecutionError("代码内容不能为空")
        
        # 模拟代码分析（实际应用中可以集成静态分析工具）
        await asyncio.sleep(0.5)
        
        # 生成分析结果
        result = {
            "language": language,
            "analysis_type": analysis_type,
            "lines_of_code": len(code.splitlines()),
            "complexity_score": self._calculate_complexity(code),
            "suggestions": self._generate_suggestions(code, language),
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def _calculate_complexity(self, code: str) -> int:
        """计算代码复杂度（简化示例）"""
        complexity = 0
        lines = code.splitlines()
        
        for line in lines:
            line = line.strip()
            if line.startswith("def ") or line.startswith("class "):
                complexity += 1
            elif "if " in line or "for " in line or "while " in line:
                complexity += 1
            elif "try:" in line or "except" in line:
                complexity += 1
        
        return complexity
    
    def _generate_suggestions(self, code: str, language: str) -> List[str]:
        """生成代码改进建议（简化示例）"""
        suggestions = []
        lines = code.splitlines()
        
        if len(lines) > 50:
            suggestions.append("函数过长，建议拆分为更小的函数")
        
        if "TODO" in code or "FIXME" in code:
            suggestions.append("代码中包含TODO/FIXME，建议完成或移除")
        
        if "import *" in code:
            suggestions.append("避免使用from module import *，建议显式导入")
        
        if not any(line.strip().startswith("#") for line in lines):
            suggestions.append("建议添加适当的注释")
        
        return suggestions

class MathExpertSubagent(BaseSubagent):
    """数学专家子代理"""
    
    async def execute(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """执行数学计算任务"""
        operation = task_params.get("operation", "add")
        operands = task_params.get("operands", [])
        
        if not operands:
            raise ExecutionError("操作数不能为空")
        
        # 模拟计算耗时
        await asyncio.sleep(0.1)
        
        result = {
            "operation": operation,
            "operands": operands,
            "result": self._perform_operation(operation, operands),
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def _perform_operation(self, operation: str, operands: List[float]) -> float:
        """执行数学运算"""
        if operation == "add":
            return sum(operands)
        elif operation == "multiply":
            result = 1
            for num in operands:
                result *= num
            return result
        elif operation == "power" and len(operands) == 2:
            return operands[0] ** operands[1]
        elif operation == "factorial" and len(operands) == 1:
            n = int(operands[0])
            if n < 0:
                raise ExecutionError("负数没有阶乘")
            result = 1
            for i in range(1, n + 1):
                result *= i
            return result
        else:
            raise ExecutionError(f"不支持的运算: {operation}")

class DataAnalysisSubagent(BaseSubagent):
    """数据分析子代理"""
    
    async def execute(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据分析任务"""
        data = task_params.get("data", [])
        analysis_type = task_params.get("analysis_type", "statistics")
        
        if not data:
            raise ExecutionError("数据不能为空")
        
        # 模拟分析耗时
        await asyncio.sleep(0.3)
        
        result = {
            "data_size": len(data),
            "analysis_type": analysis_type,
            "results": self._perform_analysis(data, analysis_type),
            "timestamp": datetime.now().isoformat()
        }
        
        return result
    
    def _perform_analysis(self, data: List[float], analysis_type: str) -> Dict[str, Any]:
        """执行数据分析"""
        if analysis_type == "statistics":
            return {
                "mean": sum(data) / len(data),
                "min": min(data),
                "max": max(data),
                "range": max(data) - min(data)
            }
        elif analysis_type == "outlier":
            # 简单的异常值检测
            mean = sum(data) / len(data)
            std_dev = (sum((x - mean) ** 2 for x in data) / len(data)) ** 0.5
            outliers = [x for x in data if abs(x - mean) > 2 * std_dev]
            return {
                "outliers": outliers,
                "outlier_count": len(outliers),
                "mean": mean,
                "std_dev": std_dev
            }
        else:
            raise ExecutionError(f"不支持的分析类型: {analysis_type}")

# ============================================================================
# 第四部分：执行引擎实现
# ============================================================================

class SubagentExecutor:
    """子代理执行引擎"""
    
    def __init__(self, max_concurrent_tasks: int = 10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self._subagent_registry: Dict[SubagentType, type] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._completed_tasks: Dict[str, SubagentResult] = {}
        self._task_counter = 0
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger("SubagentExecutor")
        
        # 注册内置子代理
        self.register_subagent(SubagentType.CODE_EXPERT, CodeExpertSubagent)
        self.register_subagent(SubagentType.MATH_EXPERT, MathExpertSubagent)
        self.register_subagent(SubagentType.DATA_ANALYSIS, DataAnalysisSubagent)
    
    def register_subagent(self, subagent_type: SubagentType, subagent_class: type) -> bool:
        """
        注册子代理类型
        
        Args:
            subagent_type: 子代理类型
            subagent_class: 子代理类（必须继承自BaseSubagent）
            
        Returns:
            bool: 是否注册成功
        """
        if not issubclass(subagent_class, BaseSubagent):
            self._logger.error(f"子代理类必须继承自BaseSubagent: {subagent_class}")
            return False
        
        self._subagent_registry[subagent_type] = subagent_class
        self._logger.info(f"注册子代理类型: {subagent_type.value} -> {subagent_class.__name__}")
        return True
    
    def list_registered_subagents(self) -> List[Dict[str, Any]]:
        """列出已注册的子代理类型"""
        return [
            {
                "type": subagent_type.value,
                "class": subagent_class.__name__,
                "module": subagent_class.__module__
            }
            for subagent_type, subagent_class in self._subagent_registry.items()
        ]
    
    async def execute_task(self, config: SubagentConfig, 
                          task_params: Dict[str, Any] = None) -> SubagentResult:
        """
        执行子代理任务
        
        Args:
            config: 子代理配置
            task_params: 任务参数
            
        Returns:
            SubagentResult: 执行结果
        """
        if task_params is None:
            task_params = {}
        
        # 检查并发限制
        async with self._lock:
            if len(self._running_tasks) >= self.max_concurrent_tasks:
                return SubagentResult.create_error_result(
                    subagent_id=config.subagent_id,
                    task_id=f"task_{self._task_counter}",
                    error_message=f"达到最大并发任务数限制: {self.max_concurrent_tasks}"
                )
        
        # 生成任务ID
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"
        
        # 查找子代理类
        subagent_class = self._subagent_registry.get(config.subagent_type)
        if not subagent_class:
            return SubagentResult.create_error_result(
                subagent_id=config.subagent_id,
                task_id=task_id,
                error_message=f"未注册的子代理类型: {config.subagent_type.value}"
            )
        
        # 创建子代理实例
        try:
            subagent = subagent_class(config)
        except Exception as e:
            return SubagentResult.create_error_result(
                subagent_id=config.subagent_id,
                task_id=task_id,
                error_message=f"创建子代理实例失败: {str(e)}"
            )
        
        # 执行任务
        self._logger.info(f"开始执行任务: {task_id} (子代理: {config.subagent_id})")
        
        try:
            result = await subagent.run_task(task_id, task_params)
            
            # 存储结果
            self._completed_tasks[task_id] = result
            
            self._logger.info(f"任务执行完成: {task_id}, 状态: {result.status.value}")
            return result
            
        except Exception as e:
            self._logger.error(f"任务执行异常: {task_id}, 错误: {str(e)}")
            
            return SubagentResult.create_error_result(
                subagent_id=config.subagent_id,
                task_id=task_id,
                error_message=f"任务执行异常: {str(e)}"
            )
    
    async def execute_multiple_tasks(self, tasks: List[Tuple[SubagentConfig, Dict[str, Any]]]) -> List[SubagentResult]:
        """
        并发执行多个子代理任务
        
        Args:
            tasks: 任务列表，每个元素为 (config, task_params)
            
        Returns:
            List[SubagentResult]: 执行结果列表
        """
        # 创建任务列表
        task_coroutines = [
            self.execute_task(config, params)
            for config, params in tasks
        ]
        
        # 并发执行
        results = await asyncio.gather(*task_coroutines, return_exceptions=True)
        
        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                config, _ = tasks[i]
                error_result = SubagentResult.create_error_result(
                    subagent_id=config.subagent_id,
                    task_id=f"batch_task_{i}",
                    error_message=f"任务执行异常: {str(result)}"
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        total_tasks = len(self._completed_tasks)
        completed_tasks = sum(1 for r in self._completed_tasks.values() 
                             if r.status == SubagentStatus.COMPLETED)
        failed_tasks = sum(1 for r in self._completed_tasks.values() 
                          if r.status == SubagentStatus.FAILED)
        timeout_tasks = sum(1 for r in self._completed_tasks.values() 
                           if r.status == SubagentStatus.TIMEOUT)
        
        avg_execution_time = 0
        if completed_tasks > 0:
            total_time = sum(r.execution_time for r in self._completed_tasks.values() 
                           if r.execution_time is not None)
            avg_execution_time = total_time / completed_tasks
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "timeout_tasks": timeout_tasks,
            "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
            "average_execution_time": avg_execution_time,
            "registered_subagents": len(self._subagent_registry)
        }
    
    def clear_completed_tasks(self) -> int:
        """清除已完成的任务记录"""
        count = len(self._completed_tasks)
        self._completed_tasks.clear()
        return count

# ============================================================================
# 第五部分：测试与演示
# ============================================================================

class SubagentTestSuite:
    """子代理测试套件"""
    
    def __init__(self):
        self.executor = SubagentExecutor()
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_subagent_registration", self.test_subagent_registration),
            ("test_config_validation", self.test_config_validation),
            ("test_code_expert_subagent", self.test_code_expert_subagent),
            ("test_math_expert_subagent", self.test_math_expert_subagent),
            ("test_data_analysis_subagent", self.test_data_analysis_subagent),
            ("test_concurrent_execution", self.test_concurrent_execution),
            ("test_error_handling", self.test_error_handling),
        ]
    
    async def test_subagent_registration(self) -> Tuple[bool, str]:
        """测试子代理注册"""
        # 检查内置子代理是否已注册
        registered = self.executor.list_registered_subagents()
        registered_types = [item["type"] for item in registered]
        
        required_types = ["code_expert", "math_expert", "data_analysis"]
        for req_type in required_types:
            if req_type not in registered_types:
                return False, f"子代理类型未注册: {req_type}"
        
        return True, f"子代理注册测试通过，已注册{len(registered)}种类型"
    
    async def test_config_validation(self) -> Tuple[bool, str]:
        """测试配置验证"""
        # 测试有效配置
        valid_config = SubagentConfig(
            subagent_id="test_config_001",
            subagent_type=SubagentType.CODE_EXPERT,
            priority=80,
            max_execution_time=10.0
        )
        
        is_valid, message = valid_config.validate()
        if not is_valid:
            return False, f"有效配置验证失败: {message}"
        
        # 测试无效配置
        invalid_config = SubagentConfig(
            subagent_id="",  # 空ID
            subagent_type=SubagentType.CODE_EXPERT
        )
        
        is_valid, message = invalid_config.validate()
        if is_valid:
            return False, "无效配置应验证失败但通过了"
        
        return True, "配置验证测试通过"
    
    async def test_code_expert_subagent(self) -> Tuple[bool, str]:
        """测试代码专家子代理"""
        config = SubagentConfig(
            subagent_id="code_expert_001",
            subagent_type=SubagentType.CODE_EXPERT,
            max_execution_time=5.0
        )
        
        task_params = {
            "code": "def hello():\n    print('Hello World')\n    return True",
            "language": "python",
            "analysis_type": "quality"
        }
        
        result = await self.executor.execute_task(config, task_params)
        
        if result.status != SubagentStatus.COMPLETED:
            return False, f"代码专家子代理执行失败: {result.error_message}"
        
        if "lines_of_code" not in result.result_data:
            return False, "结果缺少lines_of_code字段"
        
        return True, f"代码专家子代理测试通过，分析了{result.result_data['lines_of_code']}行代码"
    
    async def test_math_expert_subagent(self) -> Tuple[bool, str]:
        """测试数学专家子代理"""
        config = SubagentConfig(
            subagent_id="math_expert_001",
            subagent_type=SubagentType.MATH_EXPERT,
            max_execution_time=5.0
        )
        
        task_params = {
            "operation": "add",
            "operands": [1, 2, 3, 4, 5]
        }
        
        result = await self.executor.execute_task(config, task_params)
        
        if result.status != SubagentStatus.COMPLETED:
            return False, f"数学专家子代理执行失败: {result.error_message}"
        
        if result.result_data.get("result") != 15:
            return False, f"数学计算结果错误: {result.result_data.get('result')}"
        
        return True, "数学专家子代理测试通过"
    
    async def test_data_analysis_subagent(self) -> Tuple[bool, str]:
        """测试数据分析子代理"""
        config = SubagentConfig(
            subagent_id="data_analysis_001",
            subagent_type=SubagentType.DATA_ANALYSIS,
            max_execution_time=5.0
        )
        
        task_params = {
            "data": [1.0, 2.0, 3.0, 4.0, 5.0, 100.0],  # 包含一个异常值
            "analysis_type": "statistics"
        }
        
        result = await self.executor.execute_task(config, task_params)
        
        if result.status != SubagentStatus.COMPLETED:
            return False, f"数据分析子代理执行失败: {result.error_message}"
        
        if "mean" not in result.result_data.get("results", {}):
            return False, "统计结果缺少mean字段"
        
        return True, "数据分析子代理测试通过"
    
    async def test_concurrent_execution(self) -> Tuple[bool, str]:
        """测试并发执行"""
        tasks = []
        
        # 创建5个并发任务
        for i in range(5):
            config = SubagentConfig(
                subagent_id=f"concurrent_{i}",
                subagent_type=SubagentType.MATH_EXPERT,
                max_execution_time=5.0
            )
            
            task_params = {
                "operation": "add",
                "operands": [i, i+1, i+2]
            }
            
            tasks.append((config, task_params))
        
        # 并发执行
        start_time = time.time()
        results = await self.executor.execute_multiple_tasks(tasks)
        elapsed = time.time() - start_time
        
        # 检查结果
        successful = sum(1 for r in results if r.status == SubagentStatus.COMPLETED)
        
        if successful != len(tasks):
            return False, f"并发执行失败: {successful}/{len(tasks)}成功"
        
        return True, f"并发执行测试通过，{len(tasks)}个任务在{elapsed:.3f}秒内完成"
    
    async def test_error_handling(self) -> Tuple[bool, str]:
        """测试错误处理"""
        config = SubagentConfig(
            subagent_id="error_test_001",
            subagent_type=SubagentType.MATH_EXPERT,
            max_execution_time=5.0
        )
        
        # 测试无效操作
        task_params = {
            "operation": "invalid_operation",
            "operands": [1, 2, 3]
        }
        
        result = await self.executor.execute_task(config, task_params)
        
        if result.status != SubagentStatus.FAILED:
            return False, "错误处理测试失败: 应该失败但成功了"
        
        if not result.error_message:
            return False, "错误处理测试失败: 缺少错误信息"
        
        return True, f"错误处理测试通过: {result.error_message}"
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行子代理测试套件...")
        print("=" * 60)
        
        passed = 0
        failed = 0
        results = {}
        
        for test_name, test_func in self.tests:
            print(f"📋 运行测试: {test_name}...")
            try:
                success, message = await test_func()
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
    print("🎓 Day 10 Lesson 37: SubagentExecutor架构演示")
    print("=" * 60)
    
    # 创建执行引擎
    executor = SubagentExecutor(max_concurrent_tasks=5)
    
    print("\n1. 已注册的子代理类型:")
    registered = executor.list_registered_subagents()
    for subagent in registered:
        print(f"   - {subagent['type']}: {subagent['class']}")
    
    print("\n2. 代码专家子代理演示:")
    code_config = SubagentConfig(
        subagent_id="demo_code_expert",
        subagent_type=SubagentType.CODE_EXPERT,
        priority=80,
        max_execution_time=10.0
    )
    
    code_params = {
        "code": """
def fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    else:
        fib = [0, 1]
        for i in range(2, n):
            fib.append(fib[i-1] + fib[i-2])
        return fib

# TODO: 添加错误处理
result = fibonacci(10)
print(f"Fibonacci序列: {result}")
""",
        "language": "python",
        "analysis_type": "quality"
    }
    
    code_result = await executor.execute_task(code_config, code_params)
    if code_result.status == SubagentStatus.COMPLETED:
        print(f"   ✅ 代码分析成功")
        print(f"   代码行数: {code_result.result_data.get('lines_of_code')}")
        print(f"   复杂度评分: {code_result.result_data.get('complexity_score')}")
        suggestions = code_result.result_data.get('suggestions', [])
        if suggestions:
            print(f"   改进建议:")
            for suggestion in suggestions[:3]:  # 只显示前3个建议
                print(f"     - {suggestion}")
    else:
        print(f"   ❌ 代码分析失败: {code_result.error_message}")
    
    print("\n3. 数学专家子代理演示:")
    math_config = SubagentConfig(
        subagent_id="demo_math_expert",
        subagent_type=SubagentType.MATH_EXPERT,
        priority=90,
        max_execution_time=5.0
    )
    
    math_params = {
        "operation": "factorial",
        "operands": [10]
    }
    
    math_result = await executor.execute_task(math_config, math_params)
    if math_result.status == SubagentStatus.COMPLETED:
        print(f"   ✅ 数学计算成功")
        print(f"   运算: {math_params['operation']}")
        print(f"   操作数: {math_params['operands']}")
        print(f"   结果: {math_result.result_data.get('result')}")
        print(f"   执行时间: {math_result.execution_time:.3f}秒")
    else:
        print(f"   ❌ 数学计算失败: {math_result.error_message}")
    
    print("\n4. 并发执行演示:")
    tasks = []
    for i in range(3):
        config = SubagentConfig(
            subagent_id=f"concurrent_demo_{i}",
            subagent_type=SubagentType.DATA_ANALYSIS,
            max_execution_time=5.0
        )
        
        params = {
            "data": [i*10, i*10+1, i*10+2, i*10+3, i*10+4],
            "analysis_type": "statistics"
        }
        
        tasks.append((config, params))
    
    start_time = time.time()
    results = await executor.execute_multiple_tasks(tasks)
    elapsed = time.time() - start_time
    
    successful = sum(1 for r in results if r.status == SubagentStatus.COMPLETED)
    print(f"   ✅ 并发执行完成: {successful}/{len(tasks)}个任务成功")
    print(f"   总耗时: {elapsed:.3f}秒")
    
    for i, result in enumerate(results):
        if result.status == SubagentStatus.COMPLETED:
            mean = result.result_data.get('results', {}).get('mean', 0)
            print(f"   任务{i}: 成功, 平均值={mean:.2f}")
        else:
            print(f"   任务{i}: 失败")
    
    print("\n5. 任务统计信息:")
    stats = executor.get_task_statistics()
    print(f"   总任务数: {stats['total_tasks']}")
    print(f"   成功任务: {stats['completed_tasks']}")
    print(f"   失败任务: {stats['failed_tasks']}")
    print(f"   成功率: {stats['success_rate']*100:.1f}%")
    print(f"   平均执行时间: {stats['average_execution_time']:.3f}秒")
    print(f"   注册子代理数: {stats['registered_subagents']}")

async def run_tests():
    """运行测试套件"""
    test_suite = SubagentTestSuite()
    report = await test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 测试套件验证通过，子代理系统实现基本正确")
        return True
    else:
        print("\n⚠️  有测试失败，请检查实现代码")
        return False

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Day 10 Lesson 37: SubagentExecutor架构演示")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行完整演示")
    parser.add_argument("--version", action="version", version="1.0.0")
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.test:
        await run_tests()
    elif args.demo:
        await main_demo()
    else:
        # 默认运行基本演示
        await main_demo()

if __name__ == "__main__":
    asyncio.run(main())