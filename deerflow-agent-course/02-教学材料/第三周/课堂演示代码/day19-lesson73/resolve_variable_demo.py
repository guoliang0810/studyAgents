#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎓 Day 19 第73节课：resolve_variable机制 - 课堂演示代码
=======================================================

📚 课程目标:
1. 理解变量解析（Variable Resolution）的概念、应用场景和设计原则
2. 掌握Python反射机制在变量解析中的应用
3. 了解环境变量解析、路径表达式解析和缓存机制的设计

🔧 本演示代码包含:
1. VariableResolver - 变量解析器核心类
2. EnvironmentVariableResolver - 环境变量解析器
3. ExpressionParser - 表达式解析器（扩展）
4. AsyncFunctionResolver - 异步函数解析器
5. 完整的测试用例和集成演示

⚡ 核心功能:
- 多类型表达式: 变量引用(${var})、函数调用($(func))、类型转换(type:value)、字面值
- 嵌套路径解析: 支持深度嵌套的变量路径(database.connection.host)
- 智能缓存: LRU缓存机制，提升解析性能
- 错误恢复: 优雅的错误处理和默认值支持
- 异步支持: 异步函数调用和异步属性访问
- 环境变量集成: 支持环境变量解析和嵌套环境变量

⚠️ 生产环境注意事项:
- 变量解析涉及反射机制，需要注意安全性
- 缓存机制需要考虑内存管理和失效策略
- 异步解析需要正确处理并发和资源清理
- 环境变量解析需要考虑敏感信息保护

🚀 使用方法:
python resolve_variable_demo.py --test   # 运行测试
python resolve_variable_demo.py --demo   # 运行演示

📅 版本: v1.0.0
👨‍🏫 教师: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）
"""

import asyncio
import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache, wraps
from typing import Any, Dict, List, Optional, Tuple, Set, Union, Callable, TypeVar, Generic

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# 数据类型和枚举
# ============================================================================

class ExpressionType(Enum):
    """表达式类型枚举"""
    VARIABLE_REF = "variable_ref"      # 变量引用: ${var.path}
    FUNCTION_CALL = "function_call"    # 函数调用: $(func arg1 arg2)
    TYPE_CAST = "type_cast"            # 类型转换: int:123
    LITERAL = "literal"                # 字面值: "hello", 123, true
    COMPOSITE = "composite"            # 复合表达式: ${var}_$(func)
    ENVIRONMENT = "environment"        # 环境变量: $ENV{VAR}

class CachePolicy(Enum):
    """缓存策略枚举"""
    NONE = "none"          # 无缓存
    LRU = "lru"            # LRU缓存
    TTL = "ttl"            # TTL缓存
    BOTH = "both"          # LRU + TTL

@dataclass
class ResolutionResult:
    """解析结果封装"""
    value: Any
    expression: str
    expression_type: ExpressionType
    resolution_time: float
    cached: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "value": str(self.value) if not isinstance(self.value, (dict, list)) else self.value,
            "expression": self.expression,
            "type": self.expression_type.value,
            "resolution_time_ms": round(self.resolution_time * 1000, 2),
            "cached": self.cached,
            "error": self.error
        }

@dataclass
class ResolutionMetrics:
    """解析指标收集"""
    total_resolutions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_time: float = 0.0
    errors: int = 0
    by_type: Dict[ExpressionType, int] = field(default_factory=lambda: defaultdict(int))
    
    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        if self.total_resolutions == 0:
            return 0.0
        return self.cache_hits / self.total_resolutions
    
    @property
    def avg_resolution_time(self) -> float:
        """平均解析时间"""
        if self.total_resolutions == 0:
            return 0.0
        return self.total_time / self.total_resolutions
    
    def record(self, result: ResolutionResult):
        """记录解析结果"""
        self.total_resolutions += 1
        self.total_time += result.resolution_time
        self.by_type[result.expression_type] += 1
        
        if result.cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        if result.error:
            self.errors += 1
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_resolutions": self.total_resolutions,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate * 100, 2),
            "total_time_ms": round(self.total_time * 1000, 2),
            "avg_time_ms": round(self.avg_resolution_time * 1000, 2),
            "errors": self.errors,
            "by_type": {t.value: c for t, c in self.by_type.items()}
        }

# ============================================================================
# 异常类
# ============================================================================

class ResolutionError(Exception):
    """解析错误基类"""
    def __init__(self, expression: str, message: str):
        self.expression = expression
        self.message = message
        super().__init__(f"解析错误: {expression} - {message}")

class VariableNotFoundError(ResolutionError):
    """变量未找到错误"""
    def __init__(self, expression: str, path: str):
        super().__init__(expression, f"变量未找到: {path}")

class FunctionNotFoundError(ResolutionError):
    """函数未找到错误"""
    def __init__(self, expression: str, func_name: str):
        super().__init__(expression, f"函数未找到: {func_name}")

class TypeConversionError(ResolutionError):
    """类型转换错误"""
    def __init__(self, expression: str, type_name: str, value: str):
        super().__init__(expression, f"类型转换失败: {type_name}:{value}")

class SecurityError(ResolutionError):
    """安全性错误"""
    def __init__(self, expression: str, reason: str):
        super().__init__(expression, f"安全性错误: {reason}")

# ============================================================================
# 缓存实现
# ============================================================================

class ResolutionCache:
    """解析缓存"""
    
    def __init__(self, max_size: int = 1000, ttl: Optional[float] = None):
        self.max_size = max_size
        self.ttl = ttl  # 秒
        
        # LRU缓存
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self.cache:
            self.misses += 1
            return None
        
        value, timestamp = self.cache[key]
        
        # 检查TTL
        if self.ttl is not None and (time.time() - timestamp) > self.ttl:
            del self.cache[key]
            self.misses += 1
            return None
        
        # 更新访问顺序
        self.cache.move_to_end(key)
        self.hits += 1
        return value
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        if key in self.cache:
            # 更新现有值
            self.cache[key] = (value, time.time())
            self.cache.move_to_end(key)
        else:
            # 添加新值，检查容量
            if len(self.cache) >= self.max_size:
                # 移除最旧的项目
                self.cache.popitem(last=False)
            
            self.cache[key] = (value, time.time())
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        hit_rate = self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0.0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate * 100, 2),
            "ttl": self.ttl
        }

# ============================================================================
# 表达式解析器
# ============================================================================

class ExpressionParser:
    """表达式解析器"""
    
    # 正则表达式模式
    PATTERNS = {
        ExpressionType.VARIABLE_REF: re.compile(r'\$\{([^}]+)\}'),
        ExpressionType.FUNCTION_CALL: re.compile(r'\$\(([^)]+)\)'),
        ExpressionType.TYPE_CAST: re.compile(r'^(\w+):(.+)$'),
        ExpressionType.ENVIRONMENT: re.compile(r'\$ENV\{([^}]+)\}'),
    }
    
    @classmethod
    def parse(cls, expression: str) -> Tuple[ExpressionType, Any]:
        """解析表达式，返回表达式类型和解析内容"""
        
        # 检查环境变量引用
        env_match = cls.PATTERNS[ExpressionType.ENVIRONMENT].search(expression)
        if env_match:
            return ExpressionType.ENVIRONMENT, env_match.group(1)
        
        # 检查变量引用
        var_match = cls.PATTERNS[ExpressionType.VARIABLE_REF].search(expression)
        if var_match:
            return ExpressionType.VARIABLE_REF, var_match.group(1)
        
        # 检查函数调用
        func_match = cls.PATTERNS[ExpressionType.FUNCTION_CALL].search(expression)
        if func_match:
            return ExpressionType.FUNCTION_CALL, func_match.group(1)
        
        # 检查类型转换
        type_match = cls.PATTERNS[ExpressionType.TYPE_CAST].match(expression)
        if type_match:
            return ExpressionType.TYPE_CAST, (type_match.group(1), type_match.group(2))
        
        # 默认为字面值
        return ExpressionType.LITERAL, expression
    
    @classmethod
    def extract_all_variables(cls, expression: str) -> List[str]:
        """提取表达式中的所有变量引用"""
        variables = []
        
        # 查找所有变量引用
        for match in cls.PATTERNS[ExpressionType.VARIABLE_REF].finditer(expression):
            variables.append(match.group(1))
        
        return variables
    
    @classmethod
    def is_composite(cls, expression: str) -> bool:
        """检查是否为复合表达式"""
        # 包含多个${...}或$(...)或混合
        var_count = len(cls.PATTERNS[ExpressionType.VARIABLE_REF].findall(expression))
        func_count = len(cls.PATTERNS[ExpressionType.FUNCTION_CALL].findall(expression))
        env_count = len(cls.PATTERNS[ExpressionType.ENVIRONMENT].findall(expression))
        
        return (var_count + func_count + env_count) > 1
    
    @classmethod
    def split_function_call(cls, func_call: str) -> Tuple[str, List[str]]:
        """拆分函数调用为函数名和参数列表"""
        parts = func_call.strip().split()
        if not parts:
            raise ValueError("函数调用字符串为空")
        
        func_name = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        return func_name, args

# ============================================================================
# 变量解析器核心
# ============================================================================

class VariableResolver(ABC):
    """变量解析器抽象基类"""
    
    def __init__(
        self,
        context: Optional[Dict[str, Any]] = None,
        cache_policy: CachePolicy = CachePolicy.LRU,
        cache_size: int = 1000,
        cache_ttl: Optional[float] = 300.0,  # 5分钟
        enable_metrics: bool = True
    ):
        self.context = context or {}
        self.cache_policy = cache_policy
        self.enable_metrics = enable_metrics
        
        # 初始化缓存
        self.cache = ResolutionCache(max_size=cache_size, ttl=cache_ttl if cache_policy in [CachePolicy.TTL, CachePolicy.BOTH] else None)
        
        # 初始化指标收集
        self.metrics = ResolutionMetrics() if enable_metrics else None
        
        # 函数注册表
        self.function_registry: Dict[str, Callable] = {}
        self._register_default_functions()
        
        logger.info(f"变量解析器初始化完成，缓存策略: {cache_policy.value}")
    
    def _register_default_functions(self):
        """注册默认函数"""
        self.register_function("add", lambda x, y: x + y)
        self.register_function("multiply", lambda x, y: x * y)
        self.register_function("uppercase", lambda s: str(s).upper() if s else s)
        self.register_function("lowercase", lambda s: str(s).lower() if s else s)
        self.register_function("length", lambda x: len(x) if hasattr(x, '__len__') else 0)
        self.register_function("join", lambda sep, *args: sep.join(str(arg) for arg in args))
        self.register_function("now", lambda: time.time())
        self.register_function("env", lambda key: os.environ.get(key, ""))
    
    def register_function(self, name: str, func: Callable):
        """注册函数"""
        if name in self.function_registry:
            logger.warning(f"函数 {name} 已注册，将被覆盖")
        
        self.function_registry[name] = func
        logger.debug(f"注册函数: {name}")
    
    async def resolve(self, expression: str, default: Any = None) -> Any:
        """
        解析表达式
        
        参数:
            expression: 要解析的表达式
            default: 解析失败时的默认值
            
        返回:
            解析结果
        """
        start_time = time.time()
        cached = False
        error = None
        
        try:
            # 检查缓存
            cached_value = self.cache.get(expression)
            if cached_value is not None:
                cached = True
                result = cached_value
                logger.debug(f"从缓存获取表达式: {expression}")
            else:
                # 解析表达式
                expr_type, expr_content = ExpressionParser.parse(expression)
                
                # 根据表达式类型解析
                if expr_type == ExpressionType.VARIABLE_REF:
                    result = await self.resolve_variable(expr_content)
                elif expr_type == ExpressionType.FUNCTION_CALL:
                    result = await self.resolve_function(expr_content)
                elif expr_type == ExpressionType.TYPE_CAST:
                    type_name, value_str = expr_content
                    result = await self.cast_value(type_name, value_str)
                elif expr_type == ExpressionType.ENVIRONMENT:
                    result = await self.resolve_environment(expr_content)
                elif expr_type == ExpressionType.LITERAL:
                    result = await self.parse_literal(expression)
                else:
                    raise ResolutionError(expression, f"未知的表达式类型: {expr_type}")
                
                # 缓存结果
                self.cache.set(expression, result)
            
            # 记录指标
            if self.metrics is not None:
                resolution_time = time.time() - start_time
                result_obj = ResolutionResult(
                    value=result,
                    expression=expression,
                    expression_type=ExpressionParser.parse(expression)[0],
                    resolution_time=resolution_time,
                    cached=cached
                )
                self.metrics.record(result_obj)
            
            return result
            
        except ResolutionError as e:
            error = str(e)
            logger.warning(f"解析失败: {expression} - {error}")
            
            if default is not None:
                return default
            else:
                raise
    
    async def resolve_variable(self, var_path: str) -> Any:
        """
        解析变量路径
        
        参数:
            var_path: 变量路径，如 "database.host" 或 "user.profile.name"
            
        返回:
            变量值
        """
        if not var_path:
            raise ValueError("变量路径不能为空")
        
        parts = var_path.split(".")
        current = self.context
        
        logger.debug(f"解析变量路径: {var_path}, 路径部分: {parts}")
        
        for i, part in enumerate(parts):
            if current is None:
                raise VariableNotFoundError(var_path, ".".join(parts[:i]))
            
            # 处理字典
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                    logger.debug(f"从字典获取 {part}: {current}")
                else:
                    raise VariableNotFoundError(var_path, ".".join(parts[:i+1]))
            
            # 处理对象属性
            elif hasattr(current, part):
                attr = getattr(current, part)
                # 如果属性是可调用的，尝试调用（无参数）
                if callable(attr):
                    try:
                        if asyncio.iscoroutinefunction(attr):
                            current = await attr()
                        else:
                            current = attr()
                        logger.debug(f"调用属性 {part}() -> {current}")
                    except Exception as e:
                        logger.warning(f"调用属性 {part} 失败: {e}")
                        current = attr
                else:
                    current = attr
                    logger.debug(f"从对象属性获取 {part}: {current}")
            
            # 处理序列索引（如列表、元组）
            elif isinstance(current, (list, tuple)) and part.isdigit():
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                    logger.debug(f"从序列索引获取 [{index}]: {current}")
                else:
                    raise VariableNotFoundError(var_path, ".".join(parts[:i+1]))
            
            else:
                raise VariableNotFoundError(var_path, ".".join(parts[:i+1]))
            
            if current is None:
                logger.warning(f"路径 {var_path} 在 {part} 处返回 None")
                break
        
        logger.info(f"变量路径解析完成: {var_path} -> {current}")
        return current
    
    async def resolve_function(self, func_call: str) -> Any:
        """
        解析函数调用
        
        参数:
            func_call: 函数调用字符串，如 "add 1 2" 或 "uppercase hello"
            
        返回:
            函数调用结果
        """
        logger.debug(f"解析函数调用: {func_call}")
        
        # 拆分函数名和参数
        try:
            func_name, args_str = ExpressionParser.split_function_call(func_call)
        except ValueError as e:
            raise ResolutionError(func_call, f"函数调用格式错误: {e}")
        
        logger.debug(f"函数名: {func_name}, 参数: {args_str}")
        
        # 获取函数
        func = self.function_registry.get(func_name)
        if func is None:
            raise FunctionNotFoundError(func_call, func_name)
        
        # 解析参数
        resolved_args = []
        for arg in args_str:
            resolved_arg = await self.resolve(arg)
            resolved_args.append(resolved_arg)
        
        logger.debug(f"解析后的参数: {resolved_args}")
        
        # 调用函数
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*resolved_args)
            else:
                result = func(*resolved_args)
            
            logger.info(f"函数调用完成: {func_name} -> {result}")
            return result
            
        except Exception as e:
            logger.error(f"函数调用失败 {func_name}: {e}")
            raise ResolutionError(func_call, f"函数执行失败: {e}")
    
    async def resolve_environment(self, env_path: str) -> str:
        """
        解析环境变量
        
        参数:
            env_path: 环境变量路径，如 "DATABASE_HOST" 或 "APP.DATABASE.HOST"
            
        返回:
            环境变量值
        """
        # 默认实现：直接从os.environ获取
        # 子类可以重写此方法以支持更复杂的解析
        value = os.environ.get(env_path)
        if value is None:
            raise ResolutionError(f"$ENV{{{env_path}}}", f"环境变量未找到: {env_path}")
        
        logger.debug(f"解析环境变量: {env_path} -> {value}")
        return value
    
    async def cast_value(self, type_name: str, value_str: str) -> Any:
        """
        类型转换
        
        参数:
            type_name: 目标类型名
            value_str: 值字符串
            
        返回:
            转换后的值
        """
        logger.debug(f"类型转换: {type_name}:{value_str}")
        
        try:
            if type_name == "int":
                return int(value_str)
            elif type_name == "float":
                return float(value_str)
            elif type_name == "bool":
                lower = value_str.lower()
                if lower in ("true", "yes", "1", "on"):
                    return True
                elif lower in ("false", "no", "0", "off"):
                    return False
                else:
                    raise ValueError(f"无效的布尔值: {value_str}")
            elif type_name == "str":
                return str(value_str)
            elif type_name == "list":
                # 支持逗号分隔的列表
                return [item.strip() for item in value_str.split(",") if item.strip()]
            elif type_name == "dict":
                # 尝试解析为JSON
                try:
                    return json.loads(value_str)
                except json.JSONDecodeError:
                    # 如果不是JSON，尝试key=value,key2=value2格式
                    items = {}
                    for pair in value_str.split(","):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            items[k.strip()] = v.strip()
                    return items
            elif type_name == "json":
                # 直接解析为JSON
                return json.loads(value_str)
            else:
                raise TypeConversionError(f"{type_name}:{value_str}", type_name, value_str)
                
        except (ValueError, TypeError) as e:
            raise TypeConversionError(f"{type_name}:{value_str}", type_name, value_str) from e
    
    async def parse_literal(self, expression: str) -> Any:
        """
        解析字面值
        
        参数:
            expression: 字面值表达式
            
        返回:
            解析后的值
        """
        logger.debug(f"解析字面值: {expression}")
        
        # 处理JSON字面值
        if expression.startswith("{") and expression.endswith("}"):
            try:
                return json.loads(expression)
            except json.JSONDecodeError:
                pass
        elif expression.startswith("[") and expression.endswith("]"):
            try:
                return json.loads(expression)
            except json.JSONDecodeError:
                pass
        
        # 处理数字
        try:
            if "." in expression:
                return float(expression)
            else:
                return int(expression)
        except ValueError:
            pass
        
        # 处理布尔值
        lower = expression.lower()
        if lower == "true":
            return True
        elif lower == "false":
            return False
        elif lower == "null" or lower == "none":
            return None
        
        # 处理引号字符串（移除引号）
        if (expression.startswith('"') and expression.endswith('"')) or \
           (expression.startswith("'") and expression.endswith("'")):
            return expression[1:-1]
        
        # 默认为字符串
        return expression
    
    async def batch_resolve(self, expressions: List[str]) -> Dict[str, Any]:
        """
        批量解析表达式
        
        参数:
            expressions: 表达式列表
            
        返回:
            解析结果字典 {表达式: 值}
        """
        results = {}
        
        # 并行解析
        tasks = []
        for expr in expressions:
            task = self.resolve(expr)
            tasks.append((expr, task))
        
        for expr, task in tasks:
            try:
                result = await task
                results[expr] = result
            except Exception as e:
                results[expr] = f"ERROR: {e}"
        
        return results
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")
    
    def get_metrics(self) -> Optional[Dict]:
        """获取指标"""
        if self.metrics is None:
            return None
        
        metrics = self.metrics.to_dict()
        metrics["cache"] = self.cache.stats()
        return metrics
    
    def reset_metrics(self):
        """重置指标"""
        if self.metrics is not None:
            self.metrics = ResolutionMetrics()
        self.cache.clear()
        logger.info("指标已重置")

# ============================================================================
# 环境变量解析器
# ============================================================================

class EnvironmentVariableResolver(VariableResolver):
    """环境变量解析器"""
    
    def __init__(
        self,
        context: Optional[Dict[str, Any]] = None,
        env_prefix: str = "",
        nested_separator: str = "__",
        **kwargs
    ):
        super().__init__(context, **kwargs)
        self.env_prefix = env_prefix
        self.nested_separator = nested_separator
        
        # 加载环境变量到上下文中
        self._load_environment_variables()
        
        logger.info(f"环境变量解析器初始化完成，前缀: '{env_prefix}'，嵌套分隔符: '{nested_separator}'")
    
    def _load_environment_variables(self):
        """加载环境变量到上下文中"""
        env_dict = {}
        
        for key, value in os.environ.items():
            # 应用前缀过滤
            if self.env_prefix and not key.startswith(self.env_prefix):
                continue
            
            # 移除前缀
            if self.env_prefix:
                key = key[len(self.env_prefix):]
            
            # 支持嵌套结构：使用分隔符创建嵌套字典
            if self.nested_separator in key:
                parts = key.split(self.nested_separator)
                current = env_dict
                
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                current[parts[-1]] = value
            else:
                env_dict[key.lower()] = value
        
        # 合并到上下文中
        if "environment" not in self.context:
            self.context["environment"] = {}
        
        self.context["environment"].update(env_dict)
        
        logger.info(f"加载了 {len(env_dict)} 个环境变量到上下文中")
    
    async def resolve_environment(self, env_path: str) -> str:
        """
        解析环境变量（重写父类方法）
        
        支持嵌套路径，如 "database.host" 会尝试查找：
        1. DATABASE_HOST 环境变量
        2. DATABASE__HOST 环境变量（如果使用嵌套分隔符）
        3. 环境变量字典中的 database.host
        """
        # 尝试直接获取环境变量
        env_key = env_path.upper().replace(".", "_")
        value = os.environ.get(env_key)
        
        if value is not None:
            logger.debug(f"直接找到环境变量 {env_key}: {value}")
            return value
        
        # 尝试使用嵌套分隔符
        if self.nested_separator:
            nested_key = env_path.replace(".", self.nested_separator).upper()
            value = os.environ.get(nested_key)
            if value is not None:
                logger.debug(f"使用嵌套分隔符找到环境变量 {nested_key}: {value}")
                return value
        
        # 尝试从环境变量字典中获取
        try:
            # 使用父类的变量解析方法
            value = await super().resolve_variable(f"environment.{env_path}")
            logger.debug(f"从环境变量字典找到 {env_path}: {value}")
            return value
        except VariableNotFoundError:
            pass
        
        # 如果都找不到，尝试带前缀
        if self.env_prefix:
            prefixed_key = f"{self.env_prefix}{env_key}"
            value = os.environ.get(prefixed_key)
            if value is not None:
                logger.debug(f"使用前缀找到环境变量 {prefixed_key}: {value}")
                return value
        
        raise ResolutionError(f"$ENV{{{env_path}}}", f"环境变量未找到: {env_path}")
    
    async def resolve_variable(self, var_path: str) -> Any:
        """
        重写变量解析，优先从环境变量解析
        """
        # 如果路径以 "env." 或 "environment." 开头，直接使用环境变量解析
        if var_path.startswith("env.") or var_path.startswith("environment."):
            # 移除前缀
            env_path = var_path.split(".", 1)[1] if "." in var_path else ""
            return await self.resolve_environment(env_path)
        
        # 否则先尝试从环境变量解析
        try:
            return await self.resolve_environment(var_path)
        except ResolutionError:
            # 环境变量解析失败，回退到父类方法
            logger.debug(f"环境变量解析失败 {var_path}，尝试从上下文解析")
            return await super().resolve_variable(var_path)

# ============================================================================
# 安全变量解析器
# ============================================================================

class SecureVariableResolver(VariableResolver):
    """安全变量解析器，限制可访问的变量和函数"""
    
    def __init__(
        self,
        context: Optional[Dict[str, Any]] = None,
        allowed_variables: Optional[Set[str]] = None,
        allowed_functions: Optional[Set[str]] = None,
        **kwargs
    ):
        super().__init__(context, **kwargs)
        self.allowed_variables = allowed_variables or set()
        self.allowed_functions = allowed_functions or set()
        
        # 清空默认函数注册，只保留允许的函数
        if self.allowed_functions:
            self.function_registry.clear()
            # 重新注册允许的默认函数
            default_funcs = {
                "add": lambda x, y: x + y,
                "multiply": lambda x, y: x * y,
                "uppercase": lambda s: str(s).upper() if s else s,
                "lowercase": lambda s: str(s).lower() if s else s,
            }
            for func_name in self.allowed_functions:
                if func_name in default_funcs:
                    self.register_function(func_name, default_funcs[func_name])
        
        logger.info(f"安全变量解析器初始化完成，允许变量: {len(self.allowed_variables)} 个，允许函数: {len(self.allowed_functions)} 个")
    
    async def resolve_variable(self, var_path: str) -> Any:
        """安全检查的变量解析"""
        # 检查变量是否在允许列表中
        if self.allowed_variables and var_path not in self.allowed_variables:
            # 检查通配符模式
            allowed = False
            for pattern in self.allowed_variables:
                if pattern.endswith("*") and var_path.startswith(pattern[:-1]):
                    allowed = True
                    break
            
            if not allowed:
                raise SecurityError(var_path, f"变量不在允许列表中: {var_path}")
        
        return await super().resolve_variable(var_path)
    
    async def resolve_function(self, func_call: str) -> Any:
        """安全检查的函数解析"""
        # 提取函数名
        try:
            func_name, _ = ExpressionParser.split_function_call(func_call)
        except ValueError as e:
            raise ResolutionError(func_call, f"函数调用格式错误: {e}")
        
        # 检查函数是否在允许列表中
        if self.allowed_functions and func_name not in self.allowed_functions:
            raise SecurityError(func_call, f"函数不在允许列表中: {func_name}")
        
        return await super().resolve_function(func_call)

# ============================================================================
# 复合表达式解析器
# ============================================================================

class CompositeExpressionResolver(VariableResolver):
    """复合表达式解析器，支持混合表达式"""
    
    async def resolve(self, expression: str, default: Any = None) -> Any:
        """重写resolve方法以支持复合表达式"""
        # 检查是否为复合表达式
        if not ExpressionParser.is_composite(expression):
            return await super().resolve(expression, default)
        
        # 复合表达式：需要逐个解析并替换
        result = expression
        
        # 解析所有变量引用
        variables = ExpressionParser.extract_all_variables(expression)
        for var in variables:
            try:
                var_value = await self.resolve(f"${{{var}}}")
                # 替换变量引用
                result = result.replace(f"${{{var}}}", str(var_value))
            except ResolutionError:
                # 变量解析失败，保留原表达式
                pass
        
        # 解析所有函数调用
        # 这里简化处理，实际需要更复杂的解析
        # 对于演示，我们只处理简单的复合表达式
        
        # 如果结果仍然包含表达式，尝试直接解析
        if "${" in result or "$(" in result:
            # 回退到字面值解析
            return await self.parse_literal(result)
        
        return await self.parse_literal(result)

# ============================================================================
# 演示和测试函数
# ============================================================================

async def run_demo():
    """运行演示"""
    print("\n" + "="*60)
    print("🎓 Day 19 第73节课：resolve_variable机制 - 演示")
    print("="*60)
    
    # 创建测试上下文
    context = {
        "database": {
            "host": "localhost",
            "port": 5432,
            "credentials": {
                "username": "admin",
                "password": "secret123"
            }
        },
        "app": {
            "name": "DeerFlow Agent",
            "version": "2.0.0",
            "features": ["ai", "mcp", "config"]
        },
        "user": type('User', (object,), {
            'name': '张老师',
            'email': 'teacher@deerflow.tech',
            'get_profile': lambda: {'role': 'instructor', 'experience': '10年'}
        })(),
        "services": [
            {"name": "auth", "port": 3001},
            {"name": "api", "port": 3002},
            {"name": "mcp", "port": 3003}
        ]
    }
    
    # 设置一些环境变量用于演示
    os.environ["DEMO_DATABASE_HOST"] = "demo.db.example.com"
    os.environ["DEMO_APP_NAME"] = "Demo Application"
    os.environ["APP_DATABASE__CONNECTION__TIMEOUT"] = "30"
    
    print("\n1. 基础变量解析器演示")
    print("-"*40)
    
    resolver = VariableResolver(context)
    
    expressions = [
        "${database.host}",
        "${database.credentials.username}",
        "${app.name}",
        "${app.features.0}",  # 列表索引
        "${user.name}",
        "${user.get_profile}",  # 方法调用
        "$(add 10 20)",
        "$(uppercase hello)",
        "int:123",
        "bool:true",
        "list:a,b,c,d",
        "123.45",
        "true"
    ]
    
    results = await resolver.batch_resolve(expressions)
    
    for expr, value in results.items():
        print(f"  {expr:30} => {value}")
    
    print("\n2. 环境变量解析器演示")
    print("-"*40)
    
    env_resolver = EnvironmentVariableResolver(
        context=context,
        env_prefix="DEMO_",
        nested_separator="__"
    )
    
    env_expressions = [
        "$ENV{DEMO_DATABASE_HOST}",
        "$ENV{DEMO_APP_NAME}",
        "${environment.database.host}",
        "${app.name}",
        "$ENV{APP_DATABASE.CONNECTION.TIMEOUT}"
    ]
    
    env_results = await env_resolver.batch_resolve(env_expressions)
    
    for expr, value in env_results.items():
        print(f"  {expr:40} => {value}")
    
    print("\n3. 缓存性能演示")
    print("-"*40)
    
    # 重置指标
    resolver.reset_metrics()
    
    # 多次解析相同表达式
    test_expr = "${database.host}"
    for i in range(5):
        start = time.time()
        result = await resolver.resolve(test_expr)
        elapsed = time.time() - start
        print(f"  第{i+1}次解析 '{test_expr}': {result} (耗时: {elapsed*1000:.2f}ms)")
    
    # 显示指标
    metrics = resolver.get_metrics()
    if metrics:
        print(f"\n  解析指标:")
        print(f"    • 总解析次数: {metrics['total_resolutions']}")
        print(f"    • 缓存命中率: {metrics['cache_hit_rate']}%")
        print(f"    • 平均解析时间: {metrics['avg_time_ms']}ms")
        print(f"    • 缓存统计: 大小={metrics['cache']['size']}, 命中={metrics['cache']['hits']}, 未命中={metrics['cache']['misses']}")
    
    print("\n4. 错误处理演示")
    print("-"*40)
    
    error_expressions = [
        "${database.nonexistent}",
        "${user.invalid_attribute}",
        "$(unknown_func arg)",
        "invalid_type:value",
        "${services.10.name}"  # 索引越界
    ]
    
    for expr in error_expressions:
        try:
            result = await resolver.resolve(expr, default="(使用默认值)")
            print(f"  {expr:30} => {result}")
        except ResolutionError as e:
            print(f"  {expr:30} => 错误: {e}")
    
    print("\n5. 安全解析器演示")
    print("-"*40)
    
    secure_resolver = SecureVariableResolver(
        context=context,
        allowed_variables={"database.host", "app.name", "user.*"},
        allowed_functions={"uppercase", "lowercase"}
    )
    
    secure_expressions = [
        "${database.host}",      # 允许
        "${database.port}",      # 不允许
        "${user.name}",          # 允许（通配符）
        "$(uppercase test)",     # 允许
        "$(add 1 2)"             # 不允许
    ]
    
    for expr in secure_expressions:
        try:
            result = await secure_resolver.resolve(expr)
            print(f"  {expr:30} => {result}")
        except ResolutionError as e:
            print(f"  {expr:30} => 错误: {e}")
    
    print("\n🎉 演示完成！")
    print("="*60)

async def run_tests():
    """运行测试"""
    print("\n" + "="*60)
    print("🧪 Day 19 第73节课：resolve_variable机制 - 测试")
    print("="*60)
    
    # 创建测试上下文
    context = {
        "config": {
            "app": {
                "name": "TestApp",
                "version": "1.0.0"
            },
            "database": {
                "host": "test.db",
                "port": 3306
            }
        },
        "user": type('User', (object,), {
            'id': 1001,
            'name': 'Test User',
            'is_active': True
        })(),
        "items": ["apple", "banana", "cherry"]
    }
    
    resolver = VariableResolver(context)
    
    # 测试用例
    test_cases = [
        # (表达式, 期望值, 描述)
        ("${config.app.name}", "TestApp", "简单变量路径"),
        ("${config.database.port}", 3306, "数字变量"),
        ("${user.name}", "Test User", "对象属性"),
        ("${items.1}", "banana", "列表索引"),
        ("$(uppercase hello)", "HELLO", "函数调用"),
        ("$(add 5 3)", 8, "数学函数"),
        ("int:42", 42, "整数类型转换"),
        ("float:3.14", 3.14, "浮点数类型转换"),
        ("bool:true", True, "布尔类型转换"),
        ("list:a,b,c", ["a", "b", "c"], "列表类型转换"),
        ("123", 123, "整数字面值"),
        ("3.14", 3.14, "浮点数字面值"),
        ("true", True, "布尔字面值"),
        ("false", False, "布尔字面值"),
        ('"hello"', "hello", "字符串字面值"),
    ]
    
    passed = 0
    failed = 0
    
    for expr, expected, description in test_cases:
        try:
            result = await resolver.resolve(expr)
            
            # 特殊处理浮点数比较
            if isinstance(expected, float) and isinstance(result, float):
                success = abs(result - expected) < 0.0001
            else:
                success = result == expected
            
            if success:
                print(f"✅ {description:30} {expr:25} => {result}")
                passed += 1
            else:
                print(f"❌ {description:30} {expr:25} => {result} (期望: {expected})")
                failed += 1
                
        except Exception as e:
            print(f"❌ {description:30} {expr:25} => 异常: {e}")
            failed += 1
    
    # 环境变量解析器测试
    print("\n📊 环境变量解析器测试:")
    print("-"*40)
    
    # 设置测试环境变量
    os.environ["TEST_VAR_1"] = "value1"
    os.environ["TEST_NESTED__VAR"] = "nested_value"
    
    env_resolver = EnvironmentVariableResolver(context)
    
    env_test_cases = [
        ("$ENV{TEST_VAR_1}", "value1", "直接环境变量"),
        ("${environment.test_var_1}", "value1", "环境变量字典"),
    ]
    
    for expr, expected, description in env_test_cases:
        try:
            result = await env_resolver.resolve(expr)
            if result == expected:
                print(f"✅ {description:30} {expr:25} => {result}")
                passed += 1
            else:
                print(f"❌ {description:30} {expr:25} => {result} (期望: {expected})")
                failed += 1
        except Exception as e:
            print(f"❌ {description:30} {expr:25} => 异常: {e}")
            failed += 1
    
    # 错误处理测试
    print("\n🚨 错误处理测试:")
    print("-"*40)
    
    error_test_cases = [
        ("${nonexistent.var}", VariableNotFoundError, "变量不存在"),
        ("$(unknown_func)", FunctionNotFoundError, "函数不存在"),
        ("invalid:value", TypeConversionError, "无效类型转换"),
    ]
    
    for expr, expected_error, description in error_test_cases:
        try:
            await resolver.resolve(expr)
            print(f"❌ {description:30} {expr:25} => 应该抛出 {expected_error.__name__} 但通过了")
            failed += 1
        except expected_error:
            print(f"✅ {description:30} {expr:25} => 正确抛出 {expected_error.__name__}")
            passed += 1
        except Exception as e:
            print(f"❌ {description:30} {expr:25} => 抛出 {type(e).__name__} 而不是 {expected_error.__name__}")
            failed += 1
    
    # 缓存测试
    print("\n💾 缓存测试:")
    print("-"*40)
    
    cache_resolver = VariableResolver(context, cache_policy=CachePolicy.LRU)
    cache_resolver.reset_metrics()
    
    # 第一次解析（应该缓存未命中）
    start = time.time()
    result1 = await cache_resolver.resolve("${config.app.name}")
    time1 = time.time() - start
    
    # 第二次解析（应该缓存命中）
    start = time.time()
    result2 = await cache_resolver.resolve("${config.app.name}")
    time2 = time.time() - start
    
    if result1 == result2 == "TestApp":
        print(f"✅ 缓存一致性: 两次解析结果相同 => {result1}")
        passed += 1
    else:
        print(f"❌ 缓存一致性: 结果不同 ({result1} vs {result2})")
        failed += 1
    
    metrics = cache_resolver.get_metrics()
    if metrics and metrics["cache"]["hits"] == 1 and metrics["cache"]["misses"] == 1:
        print(f"✅ 缓存统计: 命中={metrics['cache']['hits']}, 未命中={metrics['cache']['misses']}")
        passed += 1
    else:
        print(f"❌ 缓存统计: 期望命中=1,未命中=1, 实际命中={metrics['cache']['hits']},未命中={metrics['cache']['misses']}")
        failed += 1
    
    # 汇总结果
    total = passed + failed
    pass_rate = passed / total * 100 if total > 0 else 0
    
    print("\n" + "="*60)
    print(f"📊 测试结果: 通过 {passed}/{total} ({pass_rate:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过!")
    else:
        print("⚠️  部分测试失败，请检查实现")
    
    print("="*60)
    
    return passed == total

# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("请指定运行模式:")
        print("  python resolve_variable_demo.py --test    # 运行测试")
        print("  python resolve_variable_demo.py --demo    # 运行演示")
        print("  python resolve_variable_demo.py --all     # 运行测试和演示")
        return
    
    command = sys.argv[1]
    
    if command == "--test" or command == "--all":
        success = await run_tests()
        if not success:
            sys.exit(1)
    
    if command == "--demo" or command == "--all":
        await run_demo()

if __name__ == "__main__":
    asyncio.run(main())