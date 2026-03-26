#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 7 Lesson 27: 内置工具精讲 - 课堂演示代码

本文件演示DeerFlow内置工具系统的完整实现，采用四部分结构：
第一部分：概念与设计原则 - 定义内置工具的安全评估和缓存策略
第二部分：内置工具实现 - 实现计算器工具和搜索工具及核心算法
第三部分：集成与错误处理 - 实现工具集成框架和统一的错误处理
第四部分：测试与演示 - 提供完整的测试套件和演示程序

核心功能：
1. 安全表达式评估：字符白名单、上下文限制、危险函数过滤
2. 智能缓存机制：LRU缓存、TTL管理、缓存键设计、缓存失效策略
3. 结果格式化：结构化输出、错误信息友好化、性能指标收集
4. 统一错误处理：参数验证、执行异常、资源限制、用户友好提示

使用场景：
- 计算服务：安全评估用户提供的数学表达式
- 搜索服务：缓存外部API调用结果，提高性能
- 工具平台：提供标准化的内置工具接口
- 教育系统：演示安全评估和缓存设计最佳实践

学习目标：
1. 掌握数学表达式安全评估的字符白名单和上下文限制技术
2. 理解缓存设计模式（LRU、TTL）和缓存失效策略
3. 实现结构化的结果格式化和友好的错误信息
4. 设计统一的工具接口和参数验证机制
"""

import asyncio
import logging
import math
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================


class EvaluationSafetyLevel(Enum):
    """表达式评估安全级别"""
    STRICT = "严格模式"      # 只允许基础数学运算和函数
    MODERATE = "适中模式"    # 允许扩展数学函数和常量
    PERMISSIVE = "宽松模式"  # 允许自定义变量和函数（有限制）
    

class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "最近最少使用"      # 基于访问频率的淘汰策略
    TTL = "生存时间"          # 基于时间的过期策略
    HYBRID = "混合策略"       # LRU + TTL组合策略
    NONE = "无缓存"          # 禁用缓存


class ResultFormat(Enum):
    """结果格式"""
    PLAIN = "纯文本"          # 简单文本结果
    STRUCTURED = "结构化"     # JSON结构化结果
    ENHANCED = "增强格式"     # 包含元数据和性能指标
    DEBUG = "调试格式"        # 包含详细调试信息


@dataclass
class SecurityContext:
    """安全评估上下文"""
    allowed_chars: Set[str] = field(default_factory=set)      # 允许的字符集合
    allowed_functions: Dict[str, Callable] = field(default_factory=dict)  # 允许的函数
    allowed_constants: Dict[str, Any] = field(default_factory=dict)       # 允许的常量
    max_expression_length: int = 1000                         # 最大表达式长度
    max_recursion_depth: int = 10                            # 最大递归深度
    disable_dangerous_functions: bool = True                 # 是否禁用危险函数
    
    def is_char_allowed(self, char: str) -> bool:
        """检查字符是否允许"""
        return char in self.allowed_chars
    
    def is_function_allowed(self, func_name: str) -> bool:
        """检查函数是否允许"""
        return func_name in self.allowed_functions
    
    def get_function(self, func_name: str) -> Optional[Callable]:
        """获取允许的函数"""
        return self.allowed_functions.get(func_name)


@dataclass
class CacheConfig:
    """缓存配置"""
    strategy: CacheStrategy = CacheStrategy.LRU
    max_size: int = 1000                                     # 最大缓存条目数
    ttl_seconds: int = 3600                                  # 生存时间（秒）
    enable_compression: bool = False                         # 是否启用压缩
    enable_monitoring: bool = True                           # 是否启用监控
    
    def is_valid(self) -> bool:
        """验证配置有效性"""
        return self.max_size > 0 and self.ttl_seconds > 0


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool                                            # 是否成功
    data: Any                                               # 结果数据
    error_message: str = ""                                  # 错误信息
    execution_time: float = 0.0                             # 执行时间（秒）
    cache_hit: bool = False                                 # 是否缓存命中
    cache_key: Optional[str] = None                         # 缓存键
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "cache_hit": self.cache_hit,
            "cache_key": self.cache_key,
            "metadata": self.metadata
        }


# ============================================================================
# 第二部分：内置工具实现
# ============================================================================


class BuiltinTool(ABC):
    """内置工具基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{name}")
        self.stats = {"call_count": 0, "success_count": 0, "error_count": 0}
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass
    
    @abstractmethod
    def validate_parameters(self, **kwargs) -> Tuple[bool, List[str]]:
        """验证参数"""
        pass
    
    def record_call(self, success: bool):
        """记录调用统计"""
        self.stats["call_count"] += 1
        if success:
            self.stats["success_count"] += 1
        else:
            self.stats["error_count"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "success_rate": self.stats["success_count"] / max(self.stats["call_count"], 1)
        }


class CalculatorTool(BuiltinTool):
    """计算器工具 - 安全数学表达式评估"""
    
    def __init__(self, security_context: Optional[SecurityContext] = None):
        super().__init__("calculator", "安全数学表达式评估工具")
        
        # 默认安全上下文
        if security_context is None:
            security_context = self._create_default_security_context()
        self.security_context = security_context
        
        # 编译正则表达式用于检查表达式
        self.expression_pattern = re.compile(r'^[\d\s+\-*/.()%^&|<>=]+$')
        
    def _create_default_security_context(self) -> SecurityContext:
        """创建默认安全上下文"""
        # 基础允许字符
        allowed_chars = set("0123456789+-*/.()%^&|<> =")
        
        # 安全数学函数
        allowed_functions = {
            # 基础数学函数
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            # 数学模块函数
            "sqrt": math.sqrt,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "log": math.log,
            "log10": math.log10,
            "exp": math.exp,
            "ceil": math.ceil,
            "floor": math.floor,
            "factorial": math.factorial,
            "gcd": math.gcd,
            "radians": math.radians,
            "degrees": math.degrees,
        }
        
        # 数学常量
        allowed_constants = {
            "pi": math.pi,
            "e": math.e,
            "tau": math.tau,
            "inf": math.inf,
            "nan": math.nan,
        }
        
        return SecurityContext(
            allowed_chars=allowed_chars,
            allowed_functions=allowed_functions,
            allowed_constants=allowed_constants,
            max_expression_length=1000,
            max_recursion_depth=10,
            disable_dangerous_functions=True
        )
    
    async def execute(self, expression: str, 
                     variables: Optional[Dict[str, float]] = None,
                     precision: int = 10) -> ToolResult:
        """执行数学表达式评估"""
        start_time = time.time()
        
        # 参数验证
        is_valid, errors = self.validate_parameters(
            expression=expression,
            variables=variables,
            precision=precision
        )
        if not is_valid:
            self.record_call(False)
            return ToolResult(
                success=False,
                data=None,
                error_message=f"参数验证失败: {', '.join(errors)}",
                execution_time=time.time() - start_time
            )
        
        try:
            # 安全检查
            safety_check_result = self._check_expression_safety(expression)
            if not safety_check_result[0]:
                self.record_call(False)
                return ToolResult(
                    success=False,
                    data=None,
                    error_message=f"表达式安全检查失败: {safety_check_result[1]}",
                    execution_time=time.time() - start_time
                )
            
            # 安全评估
            result = self._safe_evaluate(expression, variables, precision)
            
            execution_time = time.time() - start_time
            self.record_call(True)
            
            return ToolResult(
                success=True,
                data=result,
                error_message="",
                execution_time=execution_time,
                metadata={
                    "expression": expression,
                    "precision": precision,
                    "variables": variables or {},
                    "evaluation_method": "safe_eval"
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.record_call(False)
            
            return ToolResult(
                success=False,
                data=None,
                error_message=f"表达式评估失败: {str(e)}",
                execution_time=execution_time,
                metadata={
                    "expression": expression,
                    "error_type": type(e).__name__
                }
            )
    
    def _check_expression_safety(self, expression: str) -> Tuple[bool, str]:
        """检查表达式安全性"""
        # 1. 长度检查
        if len(expression) > self.security_context.max_expression_length:
            return False, f"表达式过长 (最大{self.security_context.max_expression_length}字符)"
        
        # 2. 字符白名单检查
        for char in expression:
            if not self.security_context.is_char_allowed(char):
                return False, f"包含不允许的字符: '{char}'"
        
        # 3. 危险模式检查
        dangerous_patterns = [
            r'__',  # 双下划线（可能访问私有属性）
            r'eval\s*\(',  # eval调用
            r'exec\s*\(',  # exec调用
            r'import\s+',  # import语句
            r'from\s+',    # from语句
            r'open\s*\(',  # 文件操作
            r'os\.',       # os模块
            r'sys\.',      # sys模块
            r'subprocess', # 子进程
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, expression, re.IGNORECASE):
                return False, f"检测到危险模式: {pattern}"
        
        # 4. 括号平衡检查
        if not self._check_parentheses_balance(expression):
            return False, "括号不匹配或嵌套过深"
        
        return True, "安全检查通过"
    
    def _check_parentheses_balance(self, expression: str) -> bool:
        """检查括号平衡"""
        stack = []
        max_depth = 0
        
        for char in expression:
            if char == '(':
                stack.append('(')
                max_depth = max(max_depth, len(stack))
                if max_depth > self.security_context.max_recursion_depth:
                    return False
            elif char == ')':
                if not stack:
                    return False
                stack.pop()
        
        return len(stack) == 0
    
    def _safe_evaluate(self, expression: str, 
                      variables: Optional[Dict[str, float]] = None,
                      precision: int = 10) -> float:
        """安全评估数学表达式"""
        # 构建安全上下文
        context = {"__builtins__": {}}
        
        # 添加允许的函数
        context.update(self.security_context.allowed_functions)
        
        # 添加允许的常量
        context.update(self.security_context.allowed_constants)
        
        # 添加变量
        if variables:
            context.update(variables)
        
        try:
            # 使用eval在受限上下文中计算
            result = eval(expression, context)
            
            # 验证结果是数字
            if not isinstance(result, (int, float, complex)):
                raise ValueError(f"表达式结果不是数字: {type(result)}")
            
            # 应用精度（对于浮点数）
            if isinstance(result, float) and not math.isnan(result) and not math.isinf(result):
                # 四舍五入到指定精度
                result = round(result, precision)
            
            return result
            
        except SyntaxError as e:
            raise ValueError(f"表达式语法错误: {e}")
        except NameError as e:
            raise ValueError(f"未定义的名称: {e}")
        except ZeroDivisionError:
            raise ValueError("除以零错误")
        except OverflowError:
            raise ValueError("数值溢出错误")
        except Exception as e:
            raise ValueError(f"评估错误: {e}")
    
    def validate_parameters(self, **kwargs) -> Tuple[bool, List[str]]:
        """验证参数"""
        errors = []
        
        expression = kwargs.get('expression')
        if not expression:
            errors.append("表达式不能为空")
        elif not isinstance(expression, str):
            errors.append("表达式必须是字符串")
        
        variables = kwargs.get('variables')
        if variables is not None and not isinstance(variables, dict):
            errors.append("variables必须是字典")
        
        precision = kwargs.get('precision', 10)
        if not isinstance(precision, int):
            errors.append("precision必须是整数")
        elif precision < 0 or precision > 20:
            errors.append("precision必须在0-20之间")
        
        return len(errors) == 0, errors


class SearchTool(BuiltinTool):
    """搜索工具 - 支持缓存和结果格式化"""
    
    def __init__(self, cache_config: Optional[CacheConfig] = None):
        super().__init__("search", "智能搜索工具（支持缓存）")
        
        # 缓存配置
        self.cache_config = cache_config or CacheConfig()
        
        # 缓存存储
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}  # 用于LRU
        
        # 搜索模拟数据（实际应用中会调用外部API）
        self.mock_search_data = {
            "python": {
                "title": "Python编程语言",
                "description": "Python是一种高级编程语言，以简洁易读的语法著称。",
                "url": "https://www.python.org",
                "relevance": 0.95,
                "timestamp": time.time()
            },
            "deerflow": {
                "title": "DeerFlow AI Agent框架",
                "description": "DeerFlow是字节跳动的开源AI Agent框架，支持多Agent协作。",
                "url": "https://github.com/bytedance/deer-flow",
                "relevance": 0.98,
                "timestamp": time.time()
            },
            "机器学习": {
                "title": "机器学习基础",
                "description": "机器学习是人工智能的一个分支，使计算机能够从数据中学习。",
                "url": "https://en.wikipedia.org/wiki/Machine_learning",
                "relevance": 0.85,
                "timestamp": time.time()
            }
        }
    
    async def execute(self, query: str, 
                     max_results: int = 10,
                     format_type: ResultFormat = ResultFormat.STRUCTURED) -> ToolResult:
        """执行搜索"""
        start_time = time.time()
        
        # 参数验证
        is_valid, errors = self.validate_parameters(
            query=query,
            max_results=max_results,
            format_type=format_type
        )
        if not is_valid:
            self.record_call(False)
            return ToolResult(
                success=False,
                data=None,
                error_message=f"参数验证失败: {', '.join(errors)}",
                execution_time=time.time() - start_time
            )
        
        try:
            # 生成缓存键
            cache_key = self._generate_cache_key(query, max_results, format_type)
            
            # 检查缓存
            cached_result = self._get_from_cache(cache_key)
            cache_hit = cached_result is not None
            
            if cache_hit:
                # 缓存命中
                result = cached_result
                self.logger.info(f"缓存命中: {query}")
            else:
                # 缓存未命中，执行搜索
                result = await self._perform_search(query, max_results)
                
                # 缓存结果
                self._store_in_cache(cache_key, result)
                self.logger.info(f"缓存未命中，执行搜索: {query}")
            
            # 格式化结果
            formatted_result = self._format_result(result, format_type)
            
            execution_time = time.time() - start_time
            self.record_call(True)
            
            return ToolResult(
                success=True,
                data=formatted_result,
                error_message="",
                execution_time=execution_time,
                cache_hit=cache_hit,
                cache_key=cache_key if cache_hit else None,
                metadata={
                    "query": query,
                    "max_results": max_results,
                    "format_type": format_type.value,
                    "result_count": len(result) if isinstance(result, list) else 1,
                    "cache_strategy": self.cache_config.strategy.value
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.record_call(False)
            
            return ToolResult(
                success=False,
                data=None,
                error_message=f"搜索失败: {str(e)}",
                execution_time=execution_time,
                metadata={
                    "query": query,
                    "error_type": type(e).__name__
                }
            )
    
    def _generate_cache_key(self, query: str, max_results: int, 
                           format_type: ResultFormat) -> str:
        """生成缓存键"""
        # 归一化查询（小写，去除多余空格）
        normalized_query = query.lower().strip()
        
        # 创建键组成部分
        key_parts = [
            f"query:{normalized_query}",
            f"max_results:{max_results}",
            f"format:{format_type.value}"
        ]
        
        # 使用MD5哈希（简化版本，实际应用中可能使用hashlib）
        key_string = "|".join(key_parts)
        return f"search_{hash(key_string) & 0xFFFFFFFFFFFFFFFF}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取"""
        if self.cache_config.strategy == CacheStrategy.NONE:
            return None
        
        # 检查缓存是否存在
        if cache_key not in self.cache:
            return None
        
        cache_entry = self.cache[cache_key]
        
        # 检查TTL过期
        if self.cache_config.strategy in [CacheStrategy.TTL, CacheStrategy.HYBRID]:
            current_time = time.time()
            entry_time = cache_entry.get("timestamp", 0)
            
            if current_time - entry_time > self.cache_config.ttl_seconds:
                # 过期，删除
                del self.cache[cache_key]
                if cache_key in self.access_times:
                    del self.access_times[cache_key]
                return None
        
        # 更新访问时间（用于LRU）
        self.access_times[cache_key] = time.time()
        
        return cache_entry.get("data")
    
    def _store_in_cache(self, cache_key: str, data: Any):
        """存储到缓存"""
        if self.cache_config.strategy == CacheStrategy.NONE:
            return
        
        # 检查缓存大小，必要时清理
        self._cleanup_cache_if_needed()
        
        # 存储数据
        self.cache[cache_key] = {
            "data": data,
            "timestamp": time.time(),
            "size": self._estimate_size(data)
        }
        self.access_times[cache_key] = time.time()
    
    def _cleanup_cache_if_needed(self):
        """必要时清理缓存"""
        if len(self.cache) < self.cache_config.max_size:
            return
        
        # 根据策略清理
        if self.cache_config.strategy == CacheStrategy.LRU:
            self._cleanup_lru()
        elif self.cache_config.strategy == CacheStrategy.TTL:
            self._cleanup_ttl()
        elif self.cache_config.strategy == CacheStrategy.HYBRID:
            self._cleanup_hybrid()
    
    def _cleanup_lru(self):
        """LRU清理：移除最近最少使用的条目"""
        if not self.access_times:
            return
        
        # 找到访问时间最早的键
        oldest_key = min(self.access_times.items(), key=lambda x: x[1])[0]
        
        # 移除
        if oldest_key in self.cache:
            del self.cache[oldest_key]
        if oldest_key in self.access_times:
            del self.access_times[oldest_key]
    
    def _cleanup_ttl(self):
        """TTL清理：移除过期的条目"""
        current_time = time.time()
        keys_to_remove = []
        
        for key, entry in self.cache.items():
            entry_time = entry.get("timestamp", 0)
            if current_time - entry_time > self.cache_config.ttl_seconds:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]
    
    def _cleanup_hybrid(self):
        """混合清理：先TTL，后LRU"""
        # 先清理过期的
        self._cleanup_ttl()
        
        # 如果仍然超过大小，使用LRU清理
        if len(self.cache) >= self.cache_config.max_size:
            self._cleanup_lru()
    
    def _estimate_size(self, data: Any) -> int:
        """估计数据大小（简化版本）"""
        if data is None:
            return 0
        return len(str(data))
    
    async def _perform_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """执行搜索（模拟实现）"""
        # 模拟网络延迟
        await asyncio.sleep(0.1)
        
        # 简单关键词匹配（实际应用中会调用外部API）
        results = []
        query_lower = query.lower()
        
        for key, data in self.mock_search_data.items():
            if query_lower in key.lower() or query_lower in data["description"].lower():
                results.append(data.copy())  # 复制避免修改原始数据
        
        # 按相关性排序
        results.sort(key=lambda x: x["relevance"], reverse=True)
        
        # 限制结果数量
        return results[:max_results]
    
    def _format_result(self, results: List[Dict[str, Any]], 
                      format_type: ResultFormat) -> Any:
        """格式化结果"""
        if format_type == ResultFormat.PLAIN:
            return self._format_plain(results)
        elif format_type == ResultFormat.STRUCTURED:
            return self._format_structured(results)
        elif format_type == ResultFormat.ENHANCED:
            return self._format_enhanced(results)
        elif format_type == ResultFormat.DEBUG:
            return self._format_debug(results)
        else:
            return self._format_structured(results)
    
    def _format_plain(self, results: List[Dict[str, Any]]) -> str:
        """纯文本格式"""
        if not results:
            return "未找到相关结果"
        
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(f"{i}. {result['title']}")
            formatted.append(f"   描述: {result['description']}")
            formatted.append(f"   链接: {result['url']}")
            formatted.append(f"   相关性: {result['relevance']:.2f}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _format_structured(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """结构化格式（JSON）"""
        return {
            "query": "模拟查询",
            "result_count": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def _format_enhanced(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """增强格式"""
        return {
            "query": "模拟查询",
            "result_count": len(results),
            "results": results,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "processing_time": time.time(),
                "cache_status": "模拟数据",
                "search_engine": "mock"
            },
            "pagination": {
                "page": 1,
                "page_size": len(results),
                "total_pages": 1
            }
        }
    
    def _format_debug(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """调试格式"""
        return {
            "query": "模拟查询",
            "result_count": len(results),
            "results": results,
            "debug_info": {
                "timestamp": datetime.now().isoformat(),
                "cache_size": len(self.cache),
                "cache_keys": list(self.cache.keys())[:5],
                "access_times": dict(list(self.access_times.items())[:3]),
                "config": {
                    "strategy": self.cache_config.strategy.value,
                    "max_size": self.cache_config.max_size,
                    "ttl_seconds": self.cache_config.ttl_seconds
                }
            }
        }
    
    def validate_parameters(self, **kwargs) -> Tuple[bool, List[str]]:
        """验证参数"""
        errors = []
        
        query = kwargs.get('query')
        if not query:
            errors.append("查询词不能为空")
        elif not isinstance(query, str):
            errors.append("查询词必须是字符串")
        elif len(query) > 500:
            errors.append("查询词过长（最大500字符）")
        
        max_results = kwargs.get('max_results', 10)
        if not isinstance(max_results, int):
            errors.append("max_results必须是整数")
        elif max_results < 1 or max_results > 100:
            errors.append("max_results必须在1-100之间")
        
        format_type = kwargs.get('format_type')
        if format_type and not isinstance(format_type, ResultFormat):
            errors.append("format_type必须是ResultFormat枚举值")
        
        return len(errors) == 0, errors


# ============================================================================
# 第三部分：集成与错误处理
# ============================================================================


class BuiltinToolsManager:
    """内置工具管理器"""
    
    def __init__(self):
        self.tools: Dict[str, BuiltinTool] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def register_tool(self, tool: BuiltinTool):
        """注册工具"""
        self.tools[tool.name] = tool
        self.logger.info(f"注册工具: {tool.name} - {tool.description}")
    
    def get_tool(self, name: str) -> Optional[BuiltinTool]:
        """获取工具"""
        return self.tools.get(name)
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """执行工具"""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error_message=f"工具未找到: {tool_name}"
            )
        
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            self.logger.error(f"工具执行异常: {tool_name}, 错误: {e}")
            return ToolResult(
                success=False,
                data=None,
                error_message=f"工具执行异常: {str(e)}"
            )
    
    def get_all_tools(self) -> Dict[str, BuiltinTool]:
        """获取所有工具"""
        return self.tools.copy()
    
    def get_tools_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有工具的统计信息"""
        stats = {}
        for name, tool in self.tools.items():
            stats[name] = tool.get_stats()
        return stats
    
    def reset_all_stats(self):
        """重置所有工具的统计"""
        for tool in self.tools.values():
            tool.stats = {"call_count": 0, "success_count": 0, "error_count": 0}


class ToolErrorHandler:
    """工具错误处理器"""
    
    @staticmethod
    def handle_validation_error(errors: List[str]) -> ToolResult:
        """处理验证错误"""
        return ToolResult(
            success=False,
            data=None,
            error_message=f"参数验证失败: {', '.join(errors)}"
        )
    
    @staticmethod
    def handle_execution_error(error: Exception, context: Dict[str, Any]) -> ToolResult:
        """处理执行错误"""
        error_type = type(error).__name__
        
        # 根据错误类型提供友好的错误信息
        if error_type == "ValueError":
            error_msg = f"输入错误: {str(error)}"
        elif error_type == "TypeError":
            error_msg = f"类型错误: {str(error)}"
        elif error_type == "ZeroDivisionError":
            error_msg = "数学错误: 除以零"
        elif error_type == "OverflowError":
            error_msg = "数学错误: 数值溢出"
        elif error_type == "TimeoutError":
            error_msg = "执行超时"
        else:
            error_msg = f"执行错误: {str(error)}"
        
        return ToolResult(
            success=False,
            data=None,
            error_message=error_msg,
            metadata={
                "error_type": error_type,
                "error_context": context,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    @staticmethod
    def enhance_user_message(error_message: str, suggestions: List[str] = None) -> str:
        """增强用户错误信息"""
        enhanced = f"❌ {error_message}"
        
        if suggestions:
            enhanced += "\n💡 建议:"
            for suggestion in suggestions:
                enhanced += f"\n  • {suggestion}"
        
        return enhanced


# ============================================================================
# 第四部分：测试与演示
# ============================================================================


class BuiltinToolsTestSuite:
    """内置工具测试套件"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def test_calculator_basic(self) -> bool:
        """测试计算器工具基础功能"""
        try:
            calculator = CalculatorTool()
            result = await calculator.execute(expression="2 + 3 * 4")
            
            success = (
                result.success and 
                abs(result.data - 14) < 0.0001
            )
            
            self.logger.info(f"计算器基础功能测试: {'通过' if success else '失败'}")
            return success
            
        except Exception as e:
            self.logger.error(f"计算器基础功能测试异常: {e}")
            return False
    
    async def test_calculator_safety(self) -> bool:
        """测试计算器工具安全性"""
        try:
            calculator = CalculatorTool()
            
            # 尝试执行危险表达式
            result = await calculator.execute(expression="__import__('os').system('ls')")
            
            # 应该因为安全检查而失败
            success = not result.success and "安全检查失败" in result.error_message
            
            self.logger.info(f"计算器安全性测试: {'通过' if success else '失败'}")
            return success
            
        except Exception as e:
            self.logger.error(f"计算器安全性测试异常: {e}")
            return False
    
    async def test_search_basic(self) -> bool:
        """测试搜索工具基础功能"""
        try:
            search = SearchTool()
            result = await search.execute(query="python")
            
            success = (
                result.success and 
                result.data is not None
            )
            
            self.logger.info(f"搜索工具基础功能测试: {'通过' if success else '失败'}")
            return success
            
        except Exception as e:
            self.logger.error(f"搜索工具基础功能测试异常: {e}")
            return False
    
    async def test_search_cache(self) -> bool:
        """测试搜索工具缓存"""
        try:
            search = SearchTool(CacheConfig(strategy=CacheStrategy.LRU, max_size=10))
            
            # 第一次查询（应该缓存未命中）
            result1 = await search.execute(query="deerflow")
            cache_hit1 = result1.cache_hit
            
            # 第二次查询（应该缓存命中）
            result2 = await search.execute(query="deerflow")
            cache_hit2 = result2.cache_hit
            
            # 检查缓存行为
            success = (not cache_hit1) and cache_hit2
            
            self.logger.info(f"搜索工具缓存测试: {'通过' if success else '失败'}")
            return success
            
        except Exception as e:
            self.logger.error(f"搜索工具缓存测试异常: {e}")
            return False
    
    async def test_tools_manager(self) -> bool:
        """测试工具管理器"""
        try:
            manager = BuiltinToolsManager()
            
            # 注册工具
            calculator = CalculatorTool()
            search = SearchTool()
            manager.register_tool(calculator)
            manager.register_tool(search)
            
            # 执行工具
            result = await manager.execute_tool("calculator", expression="5 * 6")
            
            success = result.success and abs(result.data - 30) < 0.0001
            
            self.logger.info(f"工具管理器测试: {'通过' if success else '失败'}")
            return success
            
        except Exception as e:
            self.logger.error(f"工具管理器测试异常: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        tests = [
            ('calculator_basic', self.test_calculator_basic),
            ('calculator_safety', self.test_calculator_safety),
            ('search_basic', self.test_search_basic),
            ('search_cache', self.test_search_cache),
            ('tools_manager', self.test_tools_manager)
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                start_time = time.time()
                passed = await test_func()
                execution_time = time.time() - start_time
                
                results[test_name] = {
                    'passed': passed,
                    'execution_time': execution_time
                }
                
                self.logger.info(f"测试 {test_name}: {'通过' if passed else '失败'} ({execution_time:.2f}s)")
                
            except Exception as e:
                self.logger.error(f"测试 {test_name} 异常: {e}")
                results[test_name] = {
                    'passed': False,
                    'execution_time': 0,
                    'error': str(e)
                }
        
        # 统计结果
        total_tests = len(results)
        passed_tests = sum(1 for r in results.values() if r['passed'])
        failed_tests = total_tests - passed_tests
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        return {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': success_rate
            },
            'detailed_results': results
        }


async def main_demo():
    """主演示函数"""
    print("=" * 80)
    print("🎓 Day 7 Lesson 27: 内置工具精讲演示")
    print("=" * 80)
    
    print("\n1. 创建计算器工具并执行安全表达式评估...")
    calculator = CalculatorTool()
    
    # 测试安全表达式
    test_expressions = [
        ("2 + 3 * 4", "基础运算"),
        ("sqrt(16) + sin(0)", "数学函数"),
        ("pi * 2", "数学常量"),
        ("round(3.14159, 2)", "舍入函数")
    ]
    
    for expr, desc in test_expressions:
        result = await calculator.execute(expression=expr)
        print(f"   {desc}: {expr} = {result.data if result.success else '错误: ' + result.error_message}")
    
    print("\n2. 测试计算器安全性（尝试危险表达式）...")
    dangerous_expressions = [
        "__import__('os').system('ls')",
        "eval('1+1')",
        "open('/etc/passwd').read()"
    ]
    
    for expr in dangerous_expressions:
        result = await calculator.execute(expression=expr)
        if not result.success:
            print(f"   成功阻止危险表达式: {expr[:30]}...")
            print(f"   错误信息: {result.error_message[:50]}...")
    
    print("\n3. 创建搜索工具并测试缓存机制...")
    search = SearchTool(CacheConfig(strategy=CacheStrategy.HYBRID))
    
    # 第一次查询（缓存未命中）
    print("   第一次查询 'python' (缓存未命中)...")
    result1 = await search.execute(query="python")
    print(f"   结果: {len(result1.data.get('results', [])) if result1.success else 0} 条")
    print(f"   缓存命中: {result1.cache_hit}")
    
    # 第二次查询（缓存命中）
    print("   第二次查询 'python' (缓存命中)...")
    result2 = await search.execute(query="python")
    print(f"   结果: {len(result2.data.get('results', [])) if result2.success else 0} 条")
    print(f"   缓存命中: {result2.cache_hit}")
    
    print("\n4. 创建工具管理器并集成多个工具...")
    manager = BuiltinToolsManager()
    manager.register_tool(calculator)
    manager.register_tool(search)
    
    print("   管理器中的工具:", list(manager.get_all_tools().keys()))
    
    # 通过管理器执行工具
    print("   通过管理器执行计算器工具...")
    mgr_result = await manager.execute_tool("calculator", expression="10 / 2")
    print(f"   结果: {mgr_result.data if mgr_result.success else '错误: ' + mgr_result.error_message}")
    
    print("\n5. 运行测试套件验证功能...")
    test_suite = BuiltinToolsTestSuite()
    test_report = await test_suite.run_all_tests()
    
    summary = test_report['summary']
    print(f"   测试总数: {summary['total_tests']}")
    print(f"   通过测试: {summary['passed_tests']}")
    print(f"   失败测试: {summary['failed_tests']}")
    print(f"   成功率: {summary['success_rate']:.1%}")
    
    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 解析命令行参数
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            # 运行测试套件
            async def run_tests():
                test_suite = BuiltinToolsTestSuite()
                report = await test_suite.run_all_tests()
                
                print("内置工具测试报告:")
                for test_name, test_result in report['detailed_results'].items():
                    status = "✅ 通过" if test_result['passed'] else "❌ 失败"
                    print(f"  {status} {test_name} ({test_result['execution_time']:.2f}s)")
                
                summary = report['summary']
                print(f"\n总计: {summary['total_tests']} 个测试")
                print(f"通过: {summary['passed_tests']}")
                print(f"失败: {summary['failed_tests']}")
                print(f"成功率: {summary['success_rate']:.1%}")
            
            asyncio.run(run_tests())
            
        elif sys.argv[1] == "--demo":
            # 运行完整演示
            asyncio.run(main_demo())
            
        elif sys.argv[1] == "--help":
            print("用法:")
            print("  python builtin_tools_demo.py          # 运行默认演示")
            print("  python builtin_tools_demo.py --test   # 运行测试套件")
            print("  python builtin_tools_demo.py --demo   # 运行完整演示")
            print("  python builtin_tools_demo.py --help   # 显示此帮助")
    else:
        # 默认运行完整演示
        asyncio.run(main_demo())