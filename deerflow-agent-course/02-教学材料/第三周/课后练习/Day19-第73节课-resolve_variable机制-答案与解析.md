# 📚 Day 19 第73节课：resolve_variable机制 - 答案与解析

## 🎯 答案解析概览
本文档提供课后练习的参考答案、详细解析和最佳实践建议。每个任务包含多种实现方案，并解释设计决策和性能考虑。

## 📁 文件结构
```
答案与解析/
├── task1_architecture_understanding/    # 任务1：变量解析架构理解
├── task2_variable_resolver/             # 任务2：VariableResolver实现
├── task3_environment_resolver/          # 任务3：环境变量解析器实现
├── task4_cache_mechanism/               # 任务4：缓存机制实现
├── task5_composite_expressions/         # 任务5：复合表达式解析器
├── challenge1_security_sandbox/         # 扩展挑战1：安全沙箱
├── challenge2_distributed_cache/        # 扩展挑战2：分布式缓存
├── challenge3_expression_language/      # 扩展挑战3：表达式语言
├── common_issues/                       # 常见问题解答
└── performance_optimization/            # 性能优化指南
```

## 🔧 任务1：理解变量解析架构

### 问题答案

1. **变量解析支持哪些表达式类型？每种类型的语法是什么？**

   **变量解析支持四种主要表达式类型**：

   | 类型 | 语法示例 | 描述 | 用途 |
   |------|----------|------|------|
   | **变量引用** | `${variable.path}` | 引用上下文中的变量 | 访问配置、状态、数据 |
   | **函数调用** | `$(function_name arg1 arg2)` | 调用函数并获取返回值 | 动态计算、数据转换 |
   | **类型转换** | `type:value` 或 `type:${variable}` | 将值转换为指定类型 | 类型安全、数据格式化 |
   | **字面值** | `"string"`、`123`、`true` | 直接值，无需解析 | 常量、默认值 |

   **详细语法规则**：
   ```python
   # 变量引用：支持嵌套路径
   ${database.host}           # 简单变量
   ${config.database.host}    # 嵌套路径
   
   # 函数调用：支持参数传递
   $(get_current_time)                   # 无参数
   $(add 1 2)                           # 位置参数
   
   # 类型转换：支持多种类型
   int:${PORT}              # 转换为整数
   bool:${DEBUG}            # 转换为布尔值
   list:${ITEMS}            # 转换为列表
   
   # 字面值：直接使用
   "localhost"              # 字符串
   5432                     # 整数
   true                     # 布尔值
   ```

2. **嵌套路径解析（如`${database.connection.host}`）是如何实现的？**

   **嵌套路径解析的核心算法**：
   ```python
   async def resolve_nested_path(self, path: str, context: Dict[str, Any]) -> Any:
       """解析嵌套路径，如'database.connection.host'"""
       if not path:
           raise ValueError("路径不能为空")
       
       parts = path.split('.')
       current = context
       
       for i, part in enumerate(parts):
           if not hasattr(current, '__getitem__') and not hasattr(current, '__getattr__'):
               raise ValueError(f"路径'{'.'.join(parts[:i+1])}'不可访问")
           
           try:
               # 优先尝试字典式访问
               if isinstance(current, dict):
                   current = current[part]
               # 尝试属性访问
               elif hasattr(current, part):
                   current = getattr(current, part)
               # 尝试索引访问（如列表、元组）
               elif isinstance(current, (list, tuple)) and part.isdigit():
                   current = current[int(part)]
               else:
                   raise KeyError(f"路径'{part}'不存在")
           except (KeyError, AttributeError, IndexError, ValueError) as e:
               # 提供更详细的错误信息
               available = self._get_available_keys(current)
               raise ValueError(
                   f"无法解析路径'{'.'.join(parts[:i+1])}'。"
                   f"当前位置: {type(current).__name__}, "
                   f"可用键: {available}"
               ) from e
       
       return current
   
   def _get_available_keys(self, obj: Any) -> List[str]:
       """获取对象的可用键/属性"""
       if isinstance(obj, dict):
           return list(obj.keys())
       elif hasattr(obj, '__dict__'):
           return list(obj.__dict__.keys())
       elif hasattr(obj, '__slots__'):
           return list(obj.__slots__)
       else:
           return []
   ```

   **路径解析的优化策略**：
   - **缓存解析结果**：相同路径的解析结果可缓存
   - **懒加载**：对于昂贵的对象，延迟加载直到真正访问
   - **路径预编译**：将路径编译为访问函数，提升性能
   - **安全访问**：限制访问深度，防止无限递归

3. **缓存机制如何提升解析性能？LRU缓存的实现原理是什么？**

   **缓存性能提升原理**：
   - **减少重复计算**：相同表达式的解析结果被缓存，避免重复解析
   - **降低I/O开销**：环境变量、文件读取等I/O操作结果被缓存
   - **减少反射开销**：Python反射操作相对昂贵，缓存可显著提升性能

   **LRU缓存实现原理**：
   ```python
   class LRUCache:
       """LRU（最近最少使用）缓存实现"""
       def __init__(self, max_size: int = 128):
           self.cache = OrderedDict()  # 保持插入顺序
           self.max_size = max_size
           self.hits = 0
           self.misses = 0
       
       def get(self, key: str) -> Optional[Any]:
           """获取缓存值，更新访问顺序"""
           if key not in self.cache:
               self.misses += 1
               return None
           
           # 移动到末尾（表示最近使用）
           value = self.cache.pop(key)
           self.cache[key] = value
           self.hits += 1
           return value
       
       def set(self, key: str, value: Any):
           """设置缓存值，维护缓存大小"""
           if key in self.cache:
               # 更新现有值
               self.cache.pop(key)
           elif len(self.cache) >= self.max_size:
               # 淘汰最久未使用的项
               self.cache.popitem(last=False)
           
           self.cache[key] = value
       
       def stats(self) -> Dict[str, Any]:
           """返回缓存统计信息"""
           total = self.hits + self.misses
           return {
               'size': len(self.cache),
               'hits': self.hits,
               'misses': self.misses,
               'hit_rate': self.hits / total if total > 0 else 0.0,
               'max_size': self.max_size
           }
   ```

   **LRU算法特点**：
   - **时间局部性**：最近访问的数据很可能再次被访问
   - **空间效率**：固定大小，避免内存无限增长
   - **实现简单**：使用有序字典即可实现
   - **适应性强**：适用于大多数访问模式

4. **环境变量解析器如何支持嵌套环境变量（如`${ENV_${NESTED}}`）？**

   **嵌套环境变量解析策略**：
   ```python
   async def resolve_nested_env(self, expression: str) -> Optional[str]:
       """解析嵌套环境变量，如${ENV_${NESTED}}"""
       # 提取内部表达式
       inner_match = re.search(r'\$\{([^}]+)\}', expression)
       if not inner_match:
           # 简单环境变量
           return self._get_simple_env(expression)
       
       # 递归解析内部变量
       inner_expr = inner_match.group(1)
       inner_value = await self.resolve_nested_env(inner_expr)
       if inner_value is None:
           return None
       
       # 构建外层变量名
       outer_var_name = expression.replace(
           f"${{{inner_expr}}}",
           inner_value
       )
       
       # 解析外层变量
       return self._get_simple_env(outer_var_name)
   
   def _get_simple_env(self, var_name: str) -> Optional[str]:
       """获取简单环境变量值"""
       # 支持默认值语法：${VAR:default}
       if ':' in var_name:
           var_part, default_part = var_name.split(':', 1)
           value = os.environ.get(var_part)
           return value if value is not None else default_part
       
       return os.environ.get(var_name)
   ```

   **嵌套解析的挑战与解决方案**：
   - **循环引用检测**：维护解析栈，检测并避免无限递归
   - **性能优化**：缓存嵌套解析结果，避免重复计算
   - **错误处理**：提供清晰的错误信息，指出嵌套解析失败的位置
   - **安全性**：限制嵌套深度，防止DoS攻击

### 架构图与解析流程

**变量解析架构图**：
```
┌─────────────────────────────────────────────────────────────┐
│                    VariableResolver                         │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│  解析器      │  缓存层      │  安全层      │  监控层            │
│ Resolvers   │ Cache Layer │ Security    │ Monitoring       │
├─────────────┼─────────────┼─────────────┼───────────────────┤
│ • 变量引用    │ • LRU缓存    │ • 白名单     │ • 性能统计         │
│ • 函数调用    │ • TTL管理    │ • 资源限制   │ • 审计日志         │
│ • 类型转换    │ • 序列化     │ • 沙箱环境   │ • 健康检查         │
│ • 字面值      │ • 分布式缓存  │ • 输入验证   │ • 报警机制         │
└─────────────┴─────────────┴─────────────┴───────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      表达式解析流程                           │
├─────────────────────────────────────────────────────────────┤
│ 1. 表达式分类 → 2. 语法解析 → 3. 上下文查询 → 4. 函数执行 →     │
│ 5. 类型转换 → 6. 结果缓存 → 7. 返回结果                       │
└─────────────────────────────────────────────────────────────┘
```

**解析流程详细说明**：
1. **表达式分类**：根据前缀（`${`、`$(`、`type:`）识别表达式类型
2. **语法解析**：解析表达式内部结构，提取变量路径、函数名、参数等
3. **上下文查询**：在上下文字典或环境中查找变量值
4. **函数执行**：动态导入并调用函数，传递参数
5. **类型转换**：将结果转换为指定类型，处理转换错误
6. **结果缓存**：缓存解析结果，提升后续性能
7. **返回结果**：返回解析后的值，处理错误情况

### 思考题答案

1. **如果解析的表达式包含恶意代码（如`${__import__('os').system('rm -rf /')}`），如何防范？**

   **多层防护策略**：
   ```python
   class SecureVariableResolver(VariableResolver):
       """安全变量解析器"""
       def __init__(self):
           super().__init__()
           self.allowed_modules = {'math', 'datetime', 'json', 're'}
           self.allowed_functions = {'len', 'str', 'int', 'float', 'bool'}
           self.max_execution_time = 1.0  # 最大执行时间（秒）
       
       async def resolve_function(self, func_name: str, args: List, kwargs: Dict) -> Any:
           """安全函数解析"""
           # 1. 函数白名单检查
           if func_name not in self.allowed_functions:
               raise SecurityError(f"函数'{func_name}'不在白名单中")
           
           # 2. 模块导入限制
           if '.' in func_name:
               module_name = func_name.split('.')[0]
               if module_name not in self.allowed_modules:
                   raise SecurityError(f"模块'{module_name}'不允许导入")
           
           # 3. 执行时间限制
           try:
               result = await asyncio.wait_for(
                   super().resolve_function(func_name, args, kwargs),
                   timeout=self.max_execution_time
               )
               return result
           except asyncio.TimeoutError:
               raise SecurityError(f"函数'{func_name}'执行超时")
           
           # 4. 资源使用限制（可选）
           # 可以使用resource模块限制内存和CPU使用
   ```

   **额外安全措施**：
   - **表达式白名单**：只允许预定义的表达式模式
   - **沙箱环境**：在隔离环境中执行不受信任的代码
   - **输入验证**：严格验证表达式语法，拒绝可疑模式
   - **审计日志**：记录所有解析操作，便于安全审计
   - **深度限制**：限制嵌套解析深度，防止栈溢出

2. **缓存机制可能导致什么问题？如何设计缓存失效策略？**

   **缓存可能的问题**：
   - **数据不一致**：源数据变化，缓存未更新
   - **内存泄漏**：缓存无限增长，耗尽内存
   - **缓存穿透**：大量请求不存在的键，绕过缓存
   - **缓存雪崩**：大量缓存同时失效，导致数据库压力激增

   **缓存失效策略**：
   ```python
   class SmartCache(LRUCache):
       """智能缓存，支持多种失效策略"""
       def __init__(self, max_size: int = 128):
           super().__init__(max_size)
           self.ttl_map = {}  # 键 -> 过期时间
           self.access_count = defaultdict(int)  # 访问次数统计
       
       def set_with_ttl(self, key: str, value: Any, ttl: int = 300):
           """设置带TTL的缓存值"""
           super().set(key, value)
           self.ttl_map[key] = time.time() + ttl
       
       def get(self, key: str) -> Optional[Any]:
           """获取缓存值，检查TTL"""
           # 检查是否过期
           if key in self.ttl_map and time.time() > self.ttl_map[key]:
               self.cache.pop(key, None)
               self.ttl_map.pop(key, None)
               return None
           
           self.access_count[key] += 1
           return super().get(key)
       
       def invalidate_pattern(self, pattern: str):
           """根据模式失效缓存（如'database.*'）"""
           import fnmatch
           keys_to_remove = [
               key for key in self.cache.keys()
               if fnmatch.fnmatch(key, pattern)
           ]
           for key in keys_to_remove:
               self.cache.pop(key, None)
               self.ttl_map.pop(key, None)
   ```

   **缓存失效策略组合**：
   - **TTL（生存时间）**：固定时间后失效
   - **主动失效**：数据变化时主动清除相关缓存
   - **版本控制**：缓存键包含版本号，版本变化自动失效
   - **事件驱动**：监听数据变化事件，实时更新缓存
   - **自适应策略**：根据访问模式动态调整失效策略

3. **异步函数解析器如何处理并发调用和资源清理？**

   **并发调用处理**：
   ```python
   class AsyncFunctionResolver:
       """异步函数解析器，支持并发调用"""
       def __init__(self, max_concurrent: int = 10):
           self.semaphore = asyncio.Semaphore(max_concurrent)
           self.active_tasks = set()
           self.task_results = {}
       
       async def resolve_concurrent(self, func_calls: List[Dict]) -> List[Any]:
           """并发解析多个函数调用"""
           tasks = []
           for call in func_calls:
               task = asyncio.create_task(
                   self._resolve_single_with_semaphore(call)
               )
               self.active_tasks.add(task)
               task.add_done_callback(self.active_tasks.discard)
               tasks.append(task)
           
           results = await asyncio.gather(*tasks, return_exceptions=True)
           
           # 处理异常结果
           processed_results = []
           for result in results:
               if isinstance(result, Exception):
                   processed_results.append(self._handle_error(result))
               else:
                   processed_results.append(result)
           
           return processed_results
       
       async def _resolve_single_with_semaphore(self, func_call: Dict) -> Any:
           """使用信号量控制并发"""
           async with self.semaphore:
               return await self._resolve_single(func_call)
   ```

   **资源清理策略**：
   ```python
   class ResourceAwareFunctionResolver(AsyncFunctionResolver):
       """资源感知的函数解析器"""
       def __init__(self, max_memory_mb: int = 100):
           super().__init__()
           self.max_memory_mb = max_memory_mb
           self.resource_monitor = ResourceMonitor()
           self.cleanup_tasks = []
       
       async def resolve_with_cleanup(self, func_call: Dict) -> Any:
           """带资源清理的函数解析"""
           # 检查资源使用
           if self.resource_monitor.memory_usage_mb() > self.max_memory_mb:
               await self._perform_cleanup()
           
           try:
               result = await self._resolve_single(func_call)
               return result
           finally:
               # 确保资源清理
               self._schedule_cleanup()
   ```

   **最佳实践**：
   - **连接池管理**：对于数据库/网络连接，使用连接池
   - **内存监控**：定期监控内存使用，预防泄漏
   - **超时控制**：为每个函数调用设置超时，避免死锁
   - **优雅降级**：资源不足时，降级到简化模式或返回缓存结果
   - **监控告警**：实现资源使用监控和告警机制

## 🔧 任务2：实现基础VariableResolver

### 核心代码实现

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VariableResolver核心实现
包含嵌套路径解析、错误处理、类型转换等核心功能
"""

import asyncio
import re
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ExpressionType(Enum):
    """表达式类型枚举"""
    VARIABLE = "variable"      # ${var}
    FUNCTION = "function"      # $(func)
    TYPE_CONVERSION = "type"   # type:value
    LITERAL = "literal"        # 字面值
    COMPOSITE = "composite"    # 复合表达式


@dataclass
class ParsedExpression:
    """解析后的表达式信息"""
    type: ExpressionType
    raw: str
    value: Any = None
    parts: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class VariableResolver:
    """变量解析器核心类"""
    
    def __init__(self, cache_size: int = 128, default_context: Dict[str, Any] = None):
        """
        初始化变量解析器
        
        Args:
            cache_size: 缓存大小，默认128
            default_context: 默认上下文，所有解析共享
        """
        self.cache = OrderedDict()
        self.cache_size = cache_size
        self.default_context = default_context or {}
        self.hits = 0
        self.misses = 0
        
        # 正则表达式预编译
        self.var_pattern = re.compile(r'\$\{([^}]+)\}')
        self.func_pattern = re.compile(r'\$\(([^)]+)\)')
        self.type_pattern = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*):(.+)$')
    
    async def resolve(self, expression: str, context: Dict[str, Any] = None) -> Any:
        """
        解析表达式，返回解析后的值
        
        Args:
            expression: 要解析的表达式
            context: 变量上下文，默认为None时使用默认上下文
            
        Returns:
            解析后的值
            
        Raises:
            ValueError: 表达式解析失败
            KeyError: 变量不存在且无默认值
        """
        # 生成缓存键
        cache_key = self._generate_cache_key(expression, context)
        
        # 检查缓存
        if cache_key in self.cache:
            self.hits += 1
            return self.cache[cache_key]
        
        self.misses += 1
        
        # 合并上下文
        merged_context = self._merge_contexts(context)
        
        # 解析表达式
        parsed = self._parse_expression(expression)
        
        # 根据类型解析
        if parsed.type == ExpressionType.VARIABLE:
            result = await self._resolve_variable(parsed, merged_context)
        elif parsed.type == ExpressionType.FUNCTION:
            result = await self._resolve_function(parsed, merged_context)
        elif parsed.type == ExpressionType.TYPE_CONVERSION:
            result = await self._resolve_type_conversion(parsed, merged_context)
        elif parsed.type == ExpressionType.LITERAL:
            result = parsed.value
        elif parsed.type == ExpressionType.COMPOSITE:
            result = await self._resolve_composite(parsed, merged_context)
        else:
            raise ValueError(f"未知表达式类型: {parsed.type}")
        
        # 更新缓存
        self._update_cache(cache_key, result)
        
        return result
    
    def _parse_expression(self, expression: str) -> ParsedExpression:
        """解析表达式，识别类型和结构"""
        expression = expression.strip()
        
        # 检查变量引用
        var_match = self.var_pattern.match(expression)
        if var_match:
            return ParsedExpression(
                type=ExpressionType.VARIABLE,
                raw=expression,
                parts=self._extract_path_parts(var_match.group(1))
            )
        
        # 检查函数调用
        func_match = self.func_pattern.match(expression)
        if func_match:
            return self._parse_function_expression(func_match.group(1))
        
        # 检查类型转换
        type_match = self.type_pattern.match(expression)
        if type_match:
            type_name, value = type_match.groups()
            return ParsedExpression(
                type=ExpressionType.TYPE_CONVERSION,
                raw=expression,
                metadata={'type': type_name, 'value': value}
            )
        
        # 检查复合表达式（包含多个变量引用）
        if self.var_pattern.search(expression):
            return ParsedExpression(
                type=ExpressionType.COMPOSITE,
                raw=expression,
                parts=self._extract_composite_parts(expression)
            )
        
        # 默认视为字面值
        return ParsedExpression(
            type=ExpressionType.LITERAL,
            raw=expression,
            value=self._parse_literal(expression)
        )
    
    async def _resolve_variable(self, parsed: ParsedExpression, context: Dict[str, Any]) -> Any:
        """解析变量引用"""
        if not parsed.parts:
            raise ValueError("变量路径不能为空")
        
        # 支持默认值语法：${var:default}
        if ':' in parsed.parts[-1]:
            path_parts = parsed.parts[:-1]
            default_part = parsed.parts[-1]
            var_path, default_value = default_part.split(':', 1)
            path_parts.append(var_path)
        else:
            path_parts = parsed.parts
            default_value = None
        
        try:
            # 解析路径
            value = self._resolve_path(path_parts, context)
            return value
        except (KeyError, AttributeError, IndexError) as e:
            if default_value is not None:
                return self._parse_literal(default_value)
            raise ValueError(
                f"变量'{'.'.join(parsed.parts)}'不存在。"
                f"可用变量: {list(context.keys())}"
            ) from e
    
    def _resolve_path(self, path_parts: List[str], context: Dict[str, Any]) -> Any:
        """解析嵌套路径"""
        current = context
        
        for i, part in enumerate(path_parts):
            # 尝试字典访问
            if isinstance(current, dict) and part in current:
                current = current[part]
            # 尝试属性访问
            elif hasattr(current, part):
                current = getattr(current, part)
            # 尝试索引访问（如列表、元组）
            elif isinstance(current, (list, tuple)) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    raise IndexError(f"索引{idx}超出范围")
            else:
                # 尝试其他访问方式
                try:
                    current = current[part]
                except (TypeError, KeyError, IndexError):
                    available = self._get_available_keys(current)
                    raise KeyError(
                        f"路径'{'.'.join(path_parts[:i+1])}'不存在。"
                        f"当前位置: {type(current).__name__}, "
                        f"可用键: {available}"
                    )
        
        return current
    
    def _extract_path_parts(self, path: str) -> List[str]:
        """提取路径各部分，支持默认值语法"""
        if ':' in path:
            # 处理默认值：${var:default}
            main_part, default_part = path.split(':', 1)
            parts = main_part.split('.')
            parts.append(f":{default_part}")
        else:
            parts = path.split('.')
        
        return [p.strip() for p in parts if p.strip()]
    
    def _parse_function_expression(self, expr: str) -> ParsedExpression:
        """解析函数表达式"""
        # 简单实现：假设函数名为第一个词，参数为空格分隔
        parts = expr.strip().split()
        if not parts:
            raise ValueError("函数表达式不能为空")
        
        func_name = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        return ParsedExpression(
            type=ExpressionType.FUNCTION,
            raw=expr,
            metadata={'func_name': func_name, 'args': args}
        )
    
    async def _resolve_function(self, parsed: ParsedExpression, context: Dict[str, Any]) -> Any:
        """解析函数调用"""
        func_name = parsed.metadata['func_name']
        args = parsed.metadata['args']
        
        # 在上下文中查找函数
        if func_name in context and callable(context[func_name]):
            func = context[func_name]
        else:
            # 尝试导入模块（简化版，生产环境需要更安全）
            try:
                module_name, func_name_short = self._parse_function_name(func_name)
                import importlib
                module = importlib.import_module(module_name)
                func = getattr(module, func_name_short)
            except (ImportError, AttributeError) as e:
                raise ValueError(f"函数'{func_name}'未找到") from e
        
        # 解析参数
        resolved_args = []
        for arg in args:
            # 参数可能也是表达式，递归解析
            if arg.startswith('${') or arg.startswith('$('):
                resolved_arg = await self.resolve(arg, context)
            else:
                resolved_arg = self._parse_literal(arg)
            resolved_args.append(resolved_arg)
        
        # 调用函数
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*resolved_args)
            else:
                result = func(*resolved_args)
            return result
        except Exception as e:
            raise ValueError(f"函数'{func_name}'调用失败: {str(e)}") from e
    
    async def _resolve_type_conversion(self, parsed: ParsedExpression, context: Dict[str, Any]) -> Any:
        """解析类型转换"""
        target_type = parsed.metadata['type']
        value_expr = parsed.metadata['value']
        
        # 解析值表达式
        if value_expr.startswith('${') or value_expr.startswith('$('):
            value = await self.resolve(value_expr, context)
        else:
            value = self._parse_literal(value_expr)
        
        # 类型转换
        try:
            if target_type == 'int':
                return int(value)
            elif target_type == 'float':
                return float(value)
            elif target_type == 'bool':
                if isinstance(value, str):
                    return value.lower() in ('true', 'yes', '1', 'on')
                return bool(value)
            elif target_type == 'str':
                return str(value)
            elif target_type == 'list':
                if isinstance(value, str):
                    # 尝试解析字符串为列表
                    import ast
                    return ast.literal_eval(value)
                elif isinstance(value, (list, tuple)):
                    return list(value)
                else:
                    return [value]
            elif target_type == 'dict':
                if isinstance(value, str):
                    import ast
                    return ast.literal_eval(value)
                elif isinstance(value, dict):
                    return dict(value)
                else:
                    raise ValueError(f"无法将{type(value)}转换为字典")
            else:
                raise ValueError(f"不支持的类型转换: {target_type}")
        except (ValueError, TypeError, SyntaxError) as e:
            raise ValueError(
                f"类型转换失败: {value_expr} -> {target_type}. "
                f"错误: {str(e)}"
            ) from e
    
    async def _resolve_composite(self, parsed: ParsedExpression, context: Dict[str, Any]) -> Any:
        """解析复合表达式"""
        result = parsed.raw
        
        # 查找所有变量引用
        var_matches = list(self.var_pattern.finditer(parsed.raw))
        
        # 按位置从后向前替换，避免位置变化
        for match in reversed(var_matches):
            var_expr = match.group(0)  # 完整的${...}
            var_path = match.group(1)  # ...部分
            
            # 解析变量
            try:
                var_value = await self._resolve_variable(
                    ParsedExpression(
                        type=ExpressionType.VARIABLE,
                        raw=var_expr,
                        parts=self._extract_path_parts(var_path)
                    ),
                    context
                )
                # 转换为字符串
                var_str = str(var_value)
            except (ValueError, KeyError) as e:
                # 变量解析失败，保留原表达式
                var_str = var_expr
            
            # 替换
            start, end = match.span()
            result = result[:start] + var_str + result[end:]
        
        return result
    
    def _parse_literal(self, value: str) -> Any:
        """解析字面值"""
        value = value.strip()
        
        # 布尔值
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 整数
        if value.isdigit() or (value[0] == '-' and value[1:].isdigit()):
            return int(value)
        
        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass
        
        # 字符串（移除引号）
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        
        # 默认返回原字符串
        return value
    
    def _extract_composite_parts(self, expression: str) -> List[str]:
        """提取复合表达式的各部分"""
        parts = []
        var_matches = self.var_pattern.finditer(expression)
        
        for match in var_matches:
            var_path = match.group(1)
            parts.extend(self._extract_path_parts(var_path))
        
        return parts
    
    def _get_available_keys(self, obj: Any) -> List[str]:
        """获取对象的可用键/属性"""
        if obj is None:
            return []
        
        try:
            if isinstance(obj, dict):
                return list(obj.keys())
            elif hasattr(obj, '__dict__'):
                return list(obj.__dict__.keys())
            elif hasattr(obj, '__slots__'):
                return list(obj.__slots__)
            elif isinstance(obj, (list, tuple)):
                return [str(i) for i in range(len(obj))]
            else:
                return dir(obj)
        except:
            return []
    
    def _generate_cache_key(self, expression: str, context: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 简化实现：使用表达式和上下文哈希
        import json
        context_str = json.dumps(context, sort_keys=True) if context else ""
        return f"{expression}:{hash(context_str)}"
    
    def _update_cache(self, key: str, value: Any):
        """更新缓存，维护LRU顺序"""
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.cache_size:
            self.cache.popitem(last=False)
        
        self.cache[key] = value
    
    def _merge_contexts(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """合并默认上下文和传入上下文"""
        if context is None:
            return self.default_context.copy()
        
        merged = self.default_context.copy()
        merged.update(context)
        return merged
    
    def _parse_function_name(self, func_name: str) -> Tuple[str, str]:
        """解析函数名，返回模块名和函数名"""
        if '.' in func_name:
            parts = func_name.split('.')
            module_name = '.'.join(parts[:-1])
            func_name_short = parts[-1]
        else:
            module_name = '__main__'
            func_name_short = func_name
        
        return module_name, func_name_short
    
    def cache_stats(self) -> Dict[str, Any]:
        """返回缓存统计信息"""
        total = self.hits + self.misses
        return {
            'size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': self.hits / total if total > 0 else 0.0,
            'max_size': self.cache_size
        }
```

### 测试用例

```python
import pytest
import asyncio

class TestVariableResolver:
    """VariableResolver测试类"""
    
    @pytest.fixture
    def resolver(self):
        """创建解析器实例"""
        return VariableResolver(cache_size=10)
    
    @pytest.fixture
    def context(self):
        """创建测试上下文"""
        return {
            'database': {'host': 'localhost', 'port': 5432},
            'app': {'name': 'test', 'version': '1.0.0'},
            'numbers': [1, 2, 3, 4, 5],
            'add': lambda x, y: x + y,
            'get_host': lambda: 'localhost'
        }
    
    @pytest.mark.asyncio
    async def test_simple_variable(self, resolver, context):
        """测试简单变量解析"""
        result = await resolver.resolve('${database.host}', context)
        assert result == 'localhost'
    
    @pytest.mark.asyncio
    async def test_nested_path(self, resolver, context):
        """测试嵌套路径解析"""
        context['deep'] = {'level1': {'level2': {'level3': 'value'}}}
        result = await resolver.resolve('${deep.level1.level2.level3}', context)
        assert result == 'value'
    
    @pytest.mark.asyncio
    async def test_default_value(self, resolver, context):
        """测试默认值支持"""
        result = await resolver.resolve('${non.existent:default}', context)
        assert result == 'default'
    
    @pytest.mark.asyncio
    async def test_type_conversion(self, resolver, context):
        """测试类型转换"""
        result = await resolver.resolve('int:${database.port}', context)
        assert result == 5432
        assert isinstance(result, int)
    
    @pytest.mark.asyncio
    async def test_function_call(self, resolver, context):
        """测试函数调用"""
        result = await resolver.resolve('$(add 10 20)', context)
        assert result == 30
    
    @pytest.mark.asyncio
    async def test_composite_expression(self, resolver, context):
        """测试复合表达式"""
        result = await resolver.resolve('服务器:${database.host}:${database.port}', context)
        assert result == '服务器:localhost:5432'
    
    @pytest.mark.asyncio
    async def test_cache_mechanism(self, resolver, context):
        """测试缓存机制"""
        # 第一次解析，应该缓存未命中
        stats_before = resolver.cache_stats()
        await resolver.resolve('${database.host}', context)
        stats_after = resolver.cache_stats()
        assert stats_after['misses'] == stats_before['misses'] + 1
        
        # 第二次解析，应该缓存命中
        await resolver.resolve('${database.host}', context)
        stats_final = resolver.cache_stats()
        assert stats_final['hits'] == stats_after['hits'] + 1
    
    @pytest.mark.asyncio
    async def test_error_handling(self, resolver, context):
        """测试错误处理"""
        with pytest.raises(ValueError) as exc_info:
            await resolver.resolve('${non.existent}', context)
        assert '不存在' in str(exc_info.value)
```

## 🔧 任务3：实现环境变量解析器

### 核心代码实现

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EnvironmentVariableResolver核心实现
支持嵌套环境变量、默认值、类型转换等功能
"""

import os
import re
import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum


class EnvExpressionType(Enum):
    """环境变量表达式类型"""
    SIMPLE = "simple"           # ${VAR}
    WITH_DEFAULT = "default"    # ${VAR:default}
    WITH_TYPE = "type"          # ${VAR:type}
    NESTED = "nested"           # ${VAR_${NESTED}}
    COMPLEX = "complex"         # 复合类型


@dataclass
class ParsedEnvExpression:
    """解析后的环境变量表达式信息"""
    type: EnvExpressionType
    raw: str
    var_name: str = ""
    default_value: Optional[str] = None
    target_type: Optional[str] = None
    nested_expr: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnvironmentVariableResolver:
    """环境变量解析器"""
    
    def __init__(self, env_files: List[str] = None, enable_nesting: bool = True):
        """
        初始化环境变量解析器
        
        Args:
            env_files: .env文件路径列表
            enable_nesting: 是否启用嵌套环境变量解析
        """
        self.env_files = env_files or []
        self.enable_nesting = enable_nesting
        self.loaded_env = {}
        self.cache = {}
        self.max_nesting_depth = 5
        
        # 加载.env文件
        self._load_env_files()
        
        # 正则表达式预编译
        self.env_pattern = re.compile(r'\$\{([^}]+)\}')
        self.nested_pattern = re.compile(r'\$\{[^}]*\$\{[^}]*\}[^}]*\}')
    
    def _load_env_files(self):
        """加载.env文件"""
        for env_file in self.env_files:
            if os.path.exists(env_file):
                try:
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            
                            # 解析KEY=VALUE
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                
                                # 移除引号
                                if (value.startswith('"') and value.endswith('"')) or \
                                   (value.startswith("'") and value.endswith("'")):
                                    value = value[1:-1]
                                
                                self.loaded_env[key] = value
                except Exception as e:
                    print(f"警告：无法加载环境文件 {env_file}: {e}")
    
    async def resolve(self, expression: str) -> Any:
        """
        解析环境变量表达式
        
        Args:
            expression: 环境变量表达式，如${DATABASE_HOST}
            
        Returns:
            解析后的值
            
        Raises:
            ValueError: 表达式解析失败
            KeyError: 环境变量不存在且无默认值
        """
        # 检查缓存
        if expression in self.cache:
            return self.cache[expression]
        
        # 解析表达式
        parsed = self._parse_env_expression(expression)
        
        # 根据类型解析
        if parsed.type == EnvExpressionType.SIMPLE:
            result = self._resolve_simple(parsed)
        elif parsed.type == EnvExpressionType.WITH_DEFAULT:
            result = self._resolve_with_default(parsed)
        elif parsed.type == EnvExpressionType.WITH_TYPE:
            result = await self._resolve_with_type(parsed)
        elif parsed.type == EnvExpressionType.NESTED:
            result = await self._resolve_nested(parsed)
        elif parsed.type == EnvExpressionType.COMPLEX:
            result = await self._resolve_complex(parsed)
        else:
            raise ValueError(f"未知环境变量表达式类型: {parsed.type}")
        
        # 更新缓存
        self.cache[expression] = result
        
        return result
    
    def _parse_env_expression(self, expression: str) -> ParsedEnvExpression:
        """解析环境变量表达式"""
        expression = expression.strip()
        
        # 检查是否包含环境变量语法
        if not expression.startswith('${') or not expression.endswith('}'):
            # 如果不是环境变量表达式，视为字面值
            return ParsedEnvExpression(
                type=EnvExpressionType.SIMPLE,
                raw=expression,
                var_name=expression
            )
        
        # 提取内部内容
        inner = expression[2:-1].strip()
        
        # 检查嵌套环境变量
        if self.enable_nesting and self.nested_pattern.match(expression):
            return self._parse_nested_expression(expression, inner)
        
        # 检查类型转换或默认值
        if ':' in inner and not inner.startswith(':'):
            # 可能是类型转换或默认值
            parts = inner.split(':', 1)
            var_name = parts[0].strip()
            suffix = parts[1].strip()
            
            # 判断是类型转换还是默认值
            if suffix and suffix[0].isalpha() and ':' not in suffix:
                # 可能是类型名
                return ParsedEnvExpression(
                    type=EnvExpressionType.WITH_TYPE,
                    raw=expression,
                    var_name=var_name,
                    target_type=suffix
                )
            else:
                # 默认值
                return ParsedEnvExpression(
                    type=EnvExpressionType.WITH_DEFAULT,
                    raw=expression,
                    var_name=var_name,
                    default_value=suffix
                )
        
        # 简单环境变量
        return ParsedEnvExpression(
            type=EnvExpressionType.SIMPLE,
            raw=expression,
            var_name=inner
        )
    
    def _parse_nested_expression(self, expression: str, inner: str) -> ParsedEnvExpression:
        """解析嵌套环境变量表达式"""
        # 查找最内层的环境变量
        inner_match = self.env_pattern.search(inner)
        if not inner_match:
            # 不应该发生，因为已经检测到嵌套
            return ParsedEnvExpression(
                type=EnvExpressionType.COMPLEX,
                raw=expression,
                var_name=inner
            )
        
        inner_expr = inner_match.group(0)  # 完整的${...}
        inner_content = inner_match.group(1)  # ...部分
        
        # 构建外层变量名模式
        outer_pattern = inner.replace(inner_expr, '(.*)')
        
        return ParsedEnvExpression(
            type=EnvExpressionType.NESTED,
            raw=expression,
            var_name=outer_pattern,
            nested_expr=inner_content,
            metadata={'inner_expr': inner_expr, 'inner_content': inner_content}
        )
    
    def _resolve_simple(self, parsed: ParsedEnvExpression) -> Any:
        """解析简单环境变量"""
        value = self._get_env_value(parsed.var_name)
        if value is None:
            raise KeyError(f"环境变量'{parsed.var_name}'不存在")
        return value
    
    def _resolve_with_default(self, parsed: ParsedEnvExpression) -> Any:
        """解析带默认值的环境变量"""
        value = self._get_env_value(parsed.var_name)
        if value is not None:
            return value
        
        # 使用默认值
        if parsed.default_value is not None:
            return self._parse_value(parsed.default_value)
        
        raise KeyError(f"环境变量'{parsed.var_name}'不存在且无默认值")
    
    async def _resolve_with_type(self, parsed: ParsedEnvExpression) -> Any:
        """解析带类型转换的环境变量"""
        value = self._get_env_value(parsed.var_name)
        if value is None:
            # 如果没有值，尝试使用空值的类型转换
            value = ""
        
        # 类型转换
        return self._convert_type(value, parsed.target_type)
    
    async def _resolve_nested(self, parsed: ParsedEnvExpression, depth: int = 0) -> Any:
        """解析嵌套环境变量"""
        if depth > self.max_nesting_depth:
            raise ValueError(f"嵌套深度超过限制: {self.max_nesting_depth}")
        
        # 解析内部表达式
        inner_value = await self.resolve(parsed.metadata['inner_expr'])
        
        # 构建外层变量名
        outer_var_name = parsed.var_name.replace('(.*)', inner_value)
        
        # 解析外层变量
        outer_parsed = ParsedEnvExpression(
            type=EnvExpressionType.SIMPLE,
            raw=parsed.raw,
            var_name=outer_var_name
        )
        
        return self._resolve_simple(outer_parsed)
    
    async def _resolve_complex(self, parsed: ParsedEnvExpression) -> Any:
        """解析复杂环境变量表达式"""
        # 查找所有环境变量引用
        env_matches = list(self.env_pattern.finditer(parsed.raw))
        
        if not env_matches:
            return parsed.raw
        
        # 从内到外解析
        result = parsed.raw
        
        # 按嵌套深度排序，最深的先解析
        sorted_matches = sorted(
            env_matches,
            key=lambda m: m.group(0).count('${'),
            reverse=True
        )
        
        for match in sorted_matches:
            env_expr = match.group(0)
            env_content = match.group(1)
            
            # 解析这个环境变量
            try:
                env_value = await self.resolve(env_expr)
                env_str = str(env_value)
            except (KeyError, ValueError) as e:
                # 解析失败，保留原表达式
                env_str = env_expr
            
            # 替换
            start, end = match.span()
            result = result[:start] + env_str + result[end:]
        
        return result
    
    def _get_env_value(self, var_name: str) -> Optional[str]:
        """
        获取环境变量值，考虑优先级
        
        优先级：系统环境变量 > .env文件 > 已加载的环境变量
        """
        # 1. 系统环境变量（最高优先级）
        value = os.environ.get(var_name)
        if value is not None:
            return value
        
        # 2. .env文件
        if var_name in self.loaded_env:
            return self.loaded_env[var_name]
        
        # 3. 特殊环境变量
        # 可以添加自定义环境变量源
        
        return None
    
    def _parse_value(self, value: str) -> Any:
        """解析字符串值，尝试转换为合适类型"""
        value = value.strip()
        
        # 布尔值
        if value.lower() in ('true', 'false', 'yes', 'no', 'on', 'off'):
            return value.lower() in ('true', 'yes', 'on')
        
        # 整数
        if value.isdigit() or (value[0] == '-' and value[1:].isdigit()):
            return int(value)
        
        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass
        
        # 列表（逗号分隔）
        if ',' in value and not (value.startswith('[') and value.endswith(']')):
            parts = [p.strip() for p in value.split(',')]
            return [self._parse_value(p) for p in parts]
        
        # JSON格式（列表或字典）
        if (value.startswith('[') and value.endswith(']')) or \
           (value.startswith('{') and value.endswith('}')):
            try:
                import json
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # 默认返回字符串
        return value
    
    def _convert_type(self, value: str, target_type: str) -> Any:
        """将值转换为指定类型"""
        if not target_type:
            return self._parse_value(value)
        
        target_type = target_type.lower()
        
        try:
            if target_type == 'int':
                return int(value)
            elif target_type == 'float':
                return float(value)
            elif target_type == 'bool':
                if isinstance(value, str):
                    return value.lower() in ('true', 'yes', '1', 'on', 'y')
                return bool(value)
            elif target_type == 'str':
                return str(value)
            elif target_type == 'list':
                if isinstance(value, str):
                    if value.startswith('[') and value.endswith(']'):
                        import json
                        return json.loads(value)
                    elif ',' in value:
                        return [v.strip() for v in value.split(',')]
                    else:
                        return [value]
                elif isinstance(value, (list, tuple)):
                    return list(value)
                else:
                    return [value]
            elif target_type == 'dict':
                if isinstance(value, str):
                    if value.startswith('{') and value.endswith('}'):
                        import json
                        return json.loads(value)
                    else:
                        raise ValueError(f"无法将字符串'{value}'转换为字典")
                elif isinstance(value, dict):
                    return dict(value)
                else:
                    raise ValueError(f"无法将{type(value)}转换为字典")
            elif target_type == 'json':
                import json
                return json.loads(value)
            else:
                raise ValueError(f"不支持的类型转换: {target_type}")
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"类型转换失败: '{value}' -> {target_type}. "
                f"错误: {str(e)}"
            ) from e
    
    def set_env_value(self, var_name: str, value: str, priority: str = 'custom'):
        """
        设置环境变量值
        
        Args:
            var_name: 变量名
            value: 值
            priority: 优先级 ('system', 'env_file', 'custom')
        """
        if priority == 'system':
            os.environ[var_name] = value
        elif priority == 'env_file':
            self.loaded_env[var_name] = value
        else:
            # 自定义优先级，存储在单独字典中
            if not hasattr(self, 'custom_env'):
                self.custom_env = {}
            self.custom_env[var_name] = value
        
        # 清除缓存
        self._clear_cache_for(var_name)
    
    def _clear_cache_for(self, var_name: str):
        """清除包含指定变量的缓存项"""
        keys_to_remove = []
        for key in self.cache.keys():
            if var_name in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.cache.pop(key, None)
    
    def get_all_env(self) -> Dict[str, str]:
        """获取所有环境变量（合并所有来源）"""
        all_env = {}
        
        # 自定义环境变量（最低优先级）
        if hasattr(self, 'custom_env'):
            all_env.update(self.custom_env)
        
        # .env文件
        all_env.update(self.loaded_env)
        
        # 系统环境变量（最高优先级）
        all_env.update(os.environ)
        
        return all_env
```

### 测试用例

```python
import pytest
import asyncio
import tempfile
import os

class TestEnvironmentVariableResolver:
    """EnvironmentVariableResolver测试类"""
    
    @pytest.fixture
    def env_file(self):
        """创建临时.env文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("""
            DB_HOST=localhost
            DB_PORT=5432
            FEATURE_FLAGS=enabled,beta,newui
            NESTED_KEY=PORT
            JSON_CONFIG={"host": "localhost", "port": 5432}
            """)
            env_path = f.name
        
        yield env_path
        
        # 清理
        os.unlink(env_path)
    
    @pytest.fixture
    def resolver(self, env_file):
        """创建解析器实例"""
        # 设置测试环境变量
        os.environ['APP_ENV'] = 'test'
        os.environ['DEBUG'] = 'true'
        os.environ['MAX_CONNECTIONS'] = '50'
        
        resolver = EnvironmentVariableResolver(
            env_files=[env_file],
            enable_nesting=True
        )
        
        yield resolver
        
        # 清理环境变量
        os.environ.pop('APP_ENV', None)
        os.environ.pop('DEBUG', None)
        os.environ.pop('MAX_CONNECTIONS', None)
    
    @pytest.mark.asyncio
    async def test_simple_env_var(self, resolver):
        """测试简单环境变量"""
        result = await resolver.resolve('${APP_ENV}')
        assert result == 'test'
    
    @pytest.mark.asyncio
    async def test_env_file_var(self, resolver):
        """测试.env文件变量"""
        result = await resolver.resolve('${DB_HOST}')
        assert result == 'localhost'
    
    @pytest.mark.asyncio
    async def test_default_value(self, resolver):
        """测试默认值"""
        result = await resolver.resolve('${NON_EXISTENT:default}')
        assert result == 'default'
    
    @pytest.mark.asyncio
    async def test_type_conversion_int(self, resolver):
        """测试整数类型转换"""
        result = await resolver.resolve('${MAX_CONNECTIONS:int}')
        assert result == 50
        assert isinstance(result, int)
    
    @pytest.mark.asyncio
    async def test_type_conversion_bool(self, resolver):
        """测试布尔类型转换"""
        result = await resolver.resolve('${DEBUG:bool}')
        assert result is True
    
    @pytest.mark.asyncio
    async def test_type_conversion_list(self, resolver):
        """测试列表类型转换"""
        result = await resolver.resolve('${FEATURE_FLAGS:list}')
        assert isinstance(result, list)
        assert len(result) == 3
        assert 'enabled' in result
    
    @pytest.mark.asyncio
    async def test_nested_env_var(self, resolver):
        """测试嵌套环境变量"""
        result = await resolver.resolve('${DB_${NESTED_KEY}}')
        assert result == '5432'
    
    @pytest.mark.asyncio
    async def test_json_parsing(self, resolver):
        """测试JSON解析"""
        result = await resolver.resolve('${JSON_CONFIG:json}')
        assert isinstance(result, dict)
        assert result['host'] == 'localhost'
        assert result['port'] == 5432
    
    @pytest.mark.asyncio
    async def test_complex_expression(self, resolver):
        """测试复合表达式"""
        result = await resolver.resolve('连接:${DB_HOST}:${DB_PORT}')
        assert result == '连接:localhost:5432'
    
    @pytest.mark.asyncio
    async def test_cache_mechanism(self, resolver):
        """测试缓存机制"""
        # 第一次解析
        await resolver.resolve('${APP_ENV}')
        cache_size_before = len(resolver.cache)
        
        # 第二次解析，应该使用缓存
        await resolver.resolve('${APP_ENV}')
        cache_size_after = len(resolver.cache)
        
        assert cache_size_after == cache_size_before, "缓存应该已存在"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, resolver):
        """测试错误处理"""
        with pytest.raises(KeyError):
            await resolver.resolve('${NON_EXISTENT}')
```

## 🔧 任务4：实现缓存机制

### 核心代码实现

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能缓存实现
支持LRU、TTL、多种淘汰策略
"""

import time
import threading
from collections import OrderedDict, defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import random


class CacheEvictionPolicy(Enum):
    """缓存淘汰策略"""
    LRU = "lru"          # 最近最少使用
    LFU = "lfu"          # 最不经常使用
    FIFO = "fifo"        # 先进先出
    RANDOM = "random"    # 随机淘汰


@dataclass
class CacheEntry:
    """缓存条目"""
    
    def __init__(self, key: str, value: Any, ttl: int = None):
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.last_access = self.created_at
        self.access_count = 0
        self.ttl = ttl  # 生存时间（秒），None表示永不过期
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl
    
    def access(self) -> None:
        """记录访问"""
        self.last_access = time.time()
        self.access_count += 1
    
    def __repr__(self) -> str:
        return f"CacheEntry(key={self.key}, value={type(self.value).__name__}, " \
               f"age={time.time() - self.created_at:.1f}s, accesses={self.access_count})"


class SmartCache:
    """智能缓存，支持多种淘汰策略和高级功能"""
    
    def __init__(self, 
                 max_size: int = 1000,
                 eviction_policy: CacheEvictionPolicy = CacheEvictionPolicy.LRU,
                 default_ttl: int = 300,  # 默认5分钟
                 enable_stats: bool = True):
        """
        初始化智能缓存
        
        Args:
            max_size: 最大缓存条目数
            eviction_policy: 淘汰策略
            default_ttl: 默认生存时间（秒）
            enable_stats: 是否启用统计
        """
        self.max_size = max_size
        self.eviction_policy = eviction_policy
        self.default_ttl = default_ttl
        self.enable_stats = enable_stats
        
        # 存储
        self._store: Dict[str, CacheEntry] = {}
        
        # 索引（根据淘汰策略）
        self._lru_list = OrderedDict()  # 用于LRU
        self._lfu_counter = defaultdict(int)  # 用于LFU
        self._fifo_queue = []  # 用于FIFO
        
        # 锁，确保线程安全
        self._lock = threading.RLock()
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0,
            'size': 0,
            'memory_usage': 0  # 估算的内存使用（字节）
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或过期则返回None
        """
        with self._lock:
            if key not in self._store:
                self._record_miss()
                return None
            
            entry = self._store[key]
            
            # 检查是否过期
            if entry.is_expired:
                self._remove_entry(key)
                self._record_expired()
                return None
            
            # 更新访问信息
            entry.access()
            self._update_indices(key, entry)
            
            self._record_hit()
            return entry.value
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None使用默认值
        """
        with self._lock:
            # 如果已存在，先移除
            if key in self._store:
                self._remove_entry(key)
            
            # 检查是否需要淘汰
            if len(self._store) >= self.max_size:
                self._evict_one()
            
            # 创建新条目
            entry_ttl = ttl if ttl is not None else self.default_ttl
            entry = CacheEntry(key, value, entry_ttl)
            
            # 存储
            self._store[key] = entry
            
            # 更新索引
            self._add_to_indices(key, entry)
            
            # 更新统计
            self._update_stats()
    
    def delete(self, key: str) -> bool:
        """
        删除缓存条目
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._store:
                self._remove_entry(key)
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._store.clear()
            self._lru_list.clear()
            self._lfu_counter.clear()
            self._fifo_queue.clear()
            self._reset_stats()
    
    def keys(self) -> List[str]:
        """获取所有缓存键"""
        with self._lock:
            return list(self._store.keys())
    
    def values(self) -> List[Any]:
        """获取所有缓存值"""
        with self._lock:
            return [entry.value for entry in self._store.values() if not entry.is_expired]
    
    def items(self) -> List[Tuple[str, Any]]:
        """获取所有缓存键值对"""
        with self._lock:
            return [(k, entry.value) for k, entry in self._store.items() if not entry.is_expired]
    
    def _remove_entry(self, key: str) -> None:
        """移除缓存条目"""
        if key in self._store:
            # 从存储中移除
            self._store.pop(key)
            
            # 从索引中移除
            if key in self._lru_list:
                self._lru_list.pop(key)
            if key in self._lfu_counter:
                self._lfu_counter.pop(key)
            if key in self._fifo_queue:
                self._fifo_queue.remove(key)
    
    def _add_to_indices(self, key: str, entry: CacheEntry) -> None:
        """添加到索引"""
        if self.eviction_policy == CacheEvictionPolicy.LRU:
            self._lru_list[key] = entry
        elif self.eviction_policy == CacheEvictionPolicy.LFU:
            self._lfu_counter[key] = entry.access_count
        elif self.eviction_policy == CacheEvictionPolicy.FIFO:
            self._fifo_queue.append(key)
        # RANDOM策略不需要特殊索引
    
    def _update_indices(self, key: str, entry: CacheEntry) -> None:
        """更新索引"""
        if self.eviction_policy == CacheEvictionPolicy.LRU:
            # 移动到末尾（表示最近使用）
            if key in self._lru_list:
                self._lru_list.pop(key)
                self._lru_list[key] = entry
        elif self.eviction_policy == CacheEvictionPolicy.LFU:
            self._lfu_counter[key] = entry.access_count
    
    def _evict_one(self) -> None:
        """淘汰一个条目"""
        if not self._store:
            return
        
        key_to_evict = None
        
        if self.eviction_policy == CacheEvictionPolicy.LRU:
            # 淘汰最久未使用的（第一个）
            if self._lru_list:
                key_to_evict = next(iter(self._lru_list.keys()))
        elif self.eviction_policy == CacheEvictionPolicy.LFU:
            # 淘汰访问次数最少的
            if self._lfu_counter:
                key_to_evict = min(self._lfu_counter.items(), key=lambda x: x[1])[0]
        elif self.eviction_policy == CacheEvictionPolicy.FIFO:
            # 淘汰最先进入的
            if self._fifo_queue:
                key_to_evict = self._fifo_queue[0]
        elif self.eviction_policy == CacheEvictionPolicy.RANDOM:
            # 随机淘汰
            key_to_evict = random.choice(list(self._store.keys()))
        
        if key_to_evict:
            self._remove_entry(key_to_evict)
            self.stats['evictions'] += 1
    
    def _record_hit(self) -> None:
        """记录缓存命中"""
        if self.enable_stats:
            self.stats['hits'] += 1
    
    def _record_miss(self) -> None:
        """记录缓存未命中"""
        if self.enable_stats:
            self.stats['misses'] += 1
    
    def _record_expired(self) -> None:
        """记录过期"""
        if self.enable_stats:
            self.stats['expired'] += 1
    
    def _reset_stats(self) -> None:
        """重置统计"""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0,
            'size': 0,
            'memory_usage': 0
        }
    
    def _update_stats(self) -> None:
        """更新统计信息"""
        if self.enable_stats:
            self.stats['size'] = len(self._store)
            # 估算内存使用（简化版）
            self.stats['memory_usage'] = sum(
                len(str(k)) + len(str(entry.value))
                for k, entry in self._store.items()
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            stats = self.stats.copy()
            total = stats['hits'] + stats['misses']
            stats['hit_rate'] = stats['hits'] / total if total > 0 else 0.0
            stats['eviction_rate'] = stats['evictions'] / max(stats['size'], 1)
            stats['policy'] = self.eviction_policy.value
            stats['max_size'] = self.max_size
            stats['current_size'] = len(self._store)
            return stats
```

### 测试用例

```python
import pytest
import time

class TestSmartCache:
    """SmartCache测试类"""
    
    @pytest.fixture(params=[
        CacheEvictionPolicy.LRU,
        CacheEvictionPolicy.LFU,
        CacheEvictionPolicy.FIFO,
        CacheEvictionPolicy.RANDOM
    ])
    def cache(self, request):
        """创建缓存实例（不同策略）"""
        return SmartCache(max_size=3, eviction_policy=request.param)
    
    def test_basic_operations(self, cache):
        """测试基本操作"""
        # 设置和获取
        cache.set('key1', 'value1')
        assert cache.get('key1') == 'value1'
        
        # 更新
        cache.set('key1', 'updated')
        assert cache.get('key1') == 'updated'
        
        # 删除
        cache.delete('key1')
        assert cache.get('key1') is None
    
    def test_ttl_expiration(self, cache):
        """测试TTL过期"""
        cache.set('key1', 'value1', ttl=1)
        assert cache.get('key1') == 'value1'
        
        time.sleep(1.1)
        assert cache.get('key1') is None
    
    def test_eviction(self, cache):
        """测试淘汰策略"""
        # 填充缓存
        cache.set('a', 1)
        cache.set('b', 2)
        cache.set('c', 3)
        
        # 添加第四个，应该淘汰一个
        cache.set('d', 4)
        
        # 检查大小
        assert len(cache.keys()) == 3
    
    def test_stats(self, cache):
        """测试统计信息"""
        # 一些操作
        cache.set('key1', 'value1')
        cache.get('key1')  # 命中
        cache.get('non_existent')  # 未命中
        
        stats = cache.get_stats()
        assert stats['hits'] >= 1
        assert stats['misses'] >= 1
        assert 0 <= stats['hit_rate'] <= 1
    
    def test_thread_safety(self):
        """测试线程安全"""
        import threading
        
        cache = SmartCache(max_size=1000)
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(1000):
                    key = f'key_{thread_id}_{i}'
                    cache.set(key, f'value_{i}')
                    cache.get(key)
            except Exception as e:
                errors.append(e)
        
        # 启动多个线程
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 验证没有错误
        assert len(errors) == 0, f"线程安全测试失败: {errors}"
        
        # 验证缓存状态
        stats = cache.get_stats()
        assert stats['size'] <= 1000
```

## 🔧 任务5：实现复合表达式解析器

### 核心代码实现

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复合表达式解析器核心实现
支持字符串插值、表达式拼接、条件表达式等
"""

import re
import ast
import asyncio
import operator
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import math


class NodeType(Enum):
    """AST节点类型"""
    LITERAL = "literal"          # 字面值
    VARIABLE = "variable"        # 变量引用
    BINARY_OP = "binary_op"      # 二元操作
    UNARY_OP = "unary_op"        # 一元操作
    FUNCTION = "function"        # 函数调用
    CONDITIONAL = "conditional"  # 条件表达式
    CONCAT = "concat"            # 字符串连接
    INTERPOLATION = "interpolation"  # 字符串插值


@dataclass
class ASTNode:
    """抽象语法树节点"""
    type: NodeType
    value: Any = None
    children: List['ASTNode'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        if self.children:
            children_str = ', '.join(str(c) for c in self.children)
            return f"{self.type.value}({children_str})"
        else:
            return f"{self.type.value}({self.value})"


class CompositeExpressionParser:
    """复合表达式解析器"""
    
    def __init__(self, variable_resolver=None, function_resolver=None):
        """
        初始化复合表达式解析器
        
        Args:
            variable_resolver: 变量解析器实例
            function_resolver: 函数解析器实例
        """
        self.variable_resolver = variable_resolver
        self.function_resolver = function_resolver
        
        # 运算符优先级
        self.operator_precedence = {
            'or': 1,
            'and': 2,
            'not': 3,
            'in': 4, 'not in': 4, 'is': 4, 'is not': 4,
            '<': 5, '<=': 5, '>': 5, '>=': 5, '!=': 5, '==': 5,
            '|': 6,
            '^': 7,
            '&': 8,
            '<<': 9, '>>': 9,
            '+': 10, '-': 10,
            '*': 11, '/': 11, '//': 11, '%': 11,
            '**': 12,
            '+u': 13, '-u': 13, '~': 13,  # 一元运算符
        }
        
        # 运算符函数映射
        self.operator_functions = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.truediv,
            '//': operator.floordiv,
            '%': operator.mod,
            '**': operator.pow,
            '==': operator.eq,
            '!=': operator.ne,
            '<': operator.lt,
            '<=': operator.le,
            '>': operator.gt,
            '>=': operator.ge,
            'and': lambda x, y: x and y,
            'or': lambda x, y: x or y,
            'in': lambda x, y: x in y,
            'not in': lambda x, y: x not in y,
            'is': operator.is_,
            'is not': operator.is_not,
            '|': operator.or_,
            '&': operator.and_,
            '^': operator.xor,
            '<<': operator.lshift,
            '>>': operator.rshift,
        }
        
        # 一元运算符函数映射
        self.unary_operator_functions = {
            '+': operator.pos,
            '-': operator.neg,
            '~': operator.invert,
            'not': operator.not_,
        }
        
        # 内置函数
        self.builtin_functions = {
            'abs': abs,
            'len': len,
            'max': max,
            'min': min,
            'sum': sum,
            'round': round,
            'int': int,
            'float': float,
            'str': str,
            'bool': bool,
            'list': list,
            'dict': dict,
            'sqrt': math.sqrt,
            'pow': math.pow,
            'log': math.log,
            'exp': math.exp,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
        }
    
    async def parse_and_evaluate(self, expression: str, context: Dict[str, Any] = None) -> Any:
        """
        解析并计算表达式
        
        Args:
            expression: 表达式字符串
            context: 变量上下文
            
        Returns:
            计算结果
        """
        # 解析为AST
        ast_node = self._parse_expression(expression)
        
        # 计算AST
        result = await self._evaluate_ast(ast_node, context or {})
        
        return result
    
    def _parse_expression(self, expression: str) -> ASTNode:
        """解析表达式为AST"""
        expression = expression.strip()
        
        # 检查是否为空
        if not expression:
            return ASTNode(type=NodeType.LITERAL, value='')
        
        # 检查字符串插值
        if self._contains_interpolation(expression):
            return self._parse_interpolation(expression)
        
        # 检查条件表达式
        if '?' in expression and ':' in expression:
            # 找到最外层的?和:
            question_pos = expression.find('?')
            colon_pos = expression.rfind(':')
            if question_pos < colon_pos:
                return self._parse_conditional(expression)
        
        # 检查括号表达式
        if expression.startswith('(') and expression.endswith(')'):
            # 可能是括号包裹的表达式
            inner = expression[1:-1]
            if self._is_balanced(inner):
                return self._parse_expression(inner)
        
        # 解析为普通表达式
        return self._parse_binary_expression(expression)
    
    def _contains_interpolation(self, expression: str) -> bool:
        """检查是否包含字符串插值"""
        # 检查${...}模式
        return '${' in expression and '}' in expression
    
    def _parse_interpolation(self, expression: str) -> ASTNode:
        """解析字符串插值表达式"""
        parts = []
        current_pos = 0
        
        while current_pos < len(expression):
            # 查找下一个${
            start_pos = expression.find('${', current_pos)
            if start_pos == -1:
                # 没有更多插值，添加剩余部分
                if current_pos < len(expression):
                    parts.append(ASTNode(
                        type=NodeType.LITERAL,
                        value=expression[current_pos:]
                    ))
                break
            
            # 添加${之前的部分
            if start_pos > current_pos:
                parts.append(ASTNode(
                    type=NodeType.LITERAL,
                    value=expression[current_pos:start_pos]
                ))
            
            # 查找对应的}
            depth = 1
            end_pos = start_pos + 2
            
            while end_pos < len(expression) and depth > 0:
                if expression[end_pos:end_pos+2] == '${':
                    depth += 1
                    end_pos += 2
                elif expression[end_pos] == '}':
                    depth -= 1
                    end_pos += 1
                else:
                    end_pos += 1
            
            if depth > 0:
                # 没有找到匹配的}，视为字面值
                parts.append(ASTNode(
                    type=NodeType.LITERAL,
                    value=expression[start_pos:]
                ))
                break
            
            # 提取变量表达式
            var_expr = expression[start_pos+2:end_pos-1]
            parts.append(ASTNode(
                type=NodeType.VARIABLE,
                value=var_expr
            ))
            
            current_pos = end_pos
        
        # 如果只有一个部分，直接返回
        if len(parts) == 1:
            return parts[0]
        
        # 否则返回连接节点
        return ASTNode(
            type=NodeType.CONCAT,
            children=parts
        )
    
    def _parse_conditional(self, expression: str) -> ASTNode:
        """解析条件表达式（三元运算符）"""
        # 找到最外层的?和:
        question_pos = expression.find('?')
        colon_pos = expression.rfind(':')
        
        condition = expression[:question_pos].strip()
        true_expr = expression[question_pos+1:colon_pos].strip()
        false_expr = expression[colon_pos+1:].strip()
        
        # 递归解析各部分
        condition_node = self._parse_expression(condition)
        true_node = self._parse_expression(true_expr)
        false_node = self._parse_expression(false_expr)
        
        return ASTNode(
            type=NodeType.CONDITIONAL,
            children=[condition_node, true_node, false_node]
        )
    
    def _parse_binary_expression(self, expression: str) -> ASTNode:
        """解析二元表达式"""
        # 分割为标记
        tokens = self._tokenize(expression)
        
        # 转换为逆波兰表达式
        rpn_tokens = self._shunting_yard(tokens)
        
        # 构建AST
        return self._build_ast_from_rpn(rpn_tokens)
    
    def _tokenize(self, expression: str) -> List[Tuple[str, str]]:
        """词法分析：将表达式分割为标记"""
        tokens = []
        i = 0
        
        while i < len(expression):
            char = expression[i]
            
            # 跳过空格
            if char.isspace():
                i += 1
                continue
            
            # 数字
            if char.isdigit() or (char == '.' and i+1 < len(expression) and expression[i+1].isdigit()):
                start = i
                i += 1
                while i < len(expression) and (expression[i].isdigit() or expression[i] == '.'):
                    i += 1
                # 检查科学计数法
                if i < len(expression) and expression[i].lower() == 'e':
                    i += 1
                    if i < len(expression) and (expression[i] == '+' or expression[i] == '-'):
                        i += 1
                    while i < len(expression) and expression[i].isdigit():
                        i += 1
                token_value = expression[start:i]
                tokens.append(('NUMBER', token_value))
                continue
            
            # 字符串字面值
            if char == '\"' or char == "'":
                start = i
                i += 1
                while i < len(expression) and expression[i] != char:
                    if expression[i] == '\\':  # 转义字符
                        i += 1
                    i += 1
                if i < len(expression):
                    i += 1
                token_value = expression[start:i]
                tokens.append(('STRING', token_value))
                continue
            
            # 变量或函数名
            if char.isalpha() or char == '_':
                start = i
                i += 1
                while i < len(expression) and (expression[i].isalnum() or expression[i] == '_'):
                    i += 1
                token_value = expression[start:i]
                tokens.append(('IDENTIFIER', token_value))
                continue
            
            # 运算符
            if char in '+-*/%^&|<>!=~':
                # 检查多字符运算符
                if i+1 < len(expression):
                    two_char = expression[i:i+2]
                    if two_char in ('==', '!=', '<=', '>=', '**', '//', '<<', '>>', 'in', 'is'):
                        # 检查'not in'和'is not'
                        if two_char == 'in' and i >= 3 and expression[i-3:i] == 'not':
                            # 'not in'运算符
                            tokens.pop()  # 移除'not'
                            tokens.append(('OPERATOR', 'not in'))
                            i += 2
                            continue
                        elif two_char == 'is' and i+3 < len(expression) and expression[i+2:i+5] == 'not':
                            # 'is not'运算符
                            tokens.append(('OPERATOR', 'is not'))
                            i += 5
                            continue
                        else:
                            tokens.append(('OPERATOR', two_char))
                            i += 2
                            continue
                
                tokens.append(('OPERATOR', char))
                i += 1
                continue
            
            # 括号
            if char == '(':
                tokens.append(('LPAREN', '('))
                i += 1
                continue
            if char == ')':
                tokens.append(('RPAREN', ')'))
                i += 1
                continue
            
            # 逗号
            if char == ',':
                tokens.append(('COMMA', ','))
                i += 1
                continue
            
            # 未知字符，视为字面值
            tokens.append(('LITERAL', char))
            i += 1
        
        return tokens
    
    def _shunting_yard(self, tokens: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """调度场算法：转换为逆波兰表达式"""
        output = []
        stack = []
        
        for token_type, token_value in tokens:
            if token_type == 'NUMBER' or token_type == 'STRING' or token_type == 'IDENTIFIER':
                output.append((token_type, token_value))
            
            elif token_type == 'OPERATOR':
                # 处理运算符优先级
                while stack and stack[-1][0] == 'OPERATOR':
                    top_op = stack[-1][1]
                    if (self.operator_precedence.get(top_op, 0) > self.operator_precedence.get(token_value, 0) or
                        (self.operator_precedence.get(top_op, 0) == self.operator_precedence.get(token_value, 0) and
                         token_value != '**')):  # 右结合性处理
                        output.append(stack.pop())
                    else:
                        break
                stack.append((token_type, token_value))
            
            elif token_type == 'LPAREN':
                stack.append((token_type, token_value))
            
            elif token_type == 'RPAREN':
                # 弹出直到左括号
                while stack and stack[-1][0] != 'LPAREN':
                    output.append(stack.pop())
                if stack and stack[-1][0] == 'LPAREN':
                    stack.pop()  # 丢弃左括号
                else:
                    raise ValueError("括号不匹配")
            
            elif token_type == 'COMMA':
                # 逗号分隔函数参数
                while stack and stack[-1][0] != 'LPAREN':
                    output.append(stack.pop())
                if not stack:
                    raise ValueError("逗号不在函数调用中")
        
        # 弹出剩余运算符
        while stack:
            if stack[-1][0] == 'LPAREN':
                raise ValueError("括号不匹配")
            output.append(stack.pop())
        
        return output
    
    def _build_ast_from_rpn(self, rpn_tokens: List[Tuple[str, str]]) -> ASTNode:
        """从逆波兰表达式构建AST"""
        stack = []
        
        for token_type, token_value in rpn_tokens:
            if token_type in ('NUMBER', 'STRING', 'IDENTIFIER'):
                # 字面值或标识符
                if token_type == 'NUMBER':
                    # 解析数字
                    try:
                        value = int(token_value)
                    except ValueError:
                        value = float(token_value)
                    node = ASTNode(type=NodeType.LITERAL, value=value)
                elif token_type == 'STRING':
                    # 解析字符串（移除引号）
                    value = token_value[1:-1]
                    node = ASTNode(type=NodeType.LITERAL, value=value)
                else:
                    # 标识符（变量或函数名）
                    node = ASTNode(type=NodeType.VARIABLE, value=token_value)
                stack.append(node)
            
            elif token_type == 'OPERATOR':
                # 运算符
                if token_value in ('+u', '-u', '~', 'not'):
                    # 一元运算符
                    if not stack:
                        raise ValueError(f"缺少一元运算符'{token_value}'的操作数")
                    operand = stack.pop()
                    node = ASTNode(
                        type=NodeType.UNARY_OP,
                        value=token_value,
                        children=[operand]
                    )
                else:
                    # 二元运算符
                    if len(stack) < 2:
                        raise ValueError(f"缺少二元运算符'{token_value}'的操作数")
                    right = stack.pop()
                    left = stack.pop()
                    node = ASTNode(
                        type=NodeType.BINARY_OP,
                        value=token_value,
                        children=[left, right]
                    )
                stack.append(node)
        
        if len(stack) != 1:
            raise ValueError(f"表达式解析错误，栈中剩余{len(stack)}个元素")
        
        return stack[0]
    
    async def _evaluate_ast(self, node: ASTNode, context: Dict[str, Any]) -> Any:
        """计算AST节点的值"""
        if node.type == NodeType.LITERAL:
            return node.value
        
        elif node.type == NodeType.VARIABLE:
            # 使用变量解析器
            if self.variable_resolver:
                return await self.variable_resolver.resolve(node.value, context)
            else:
                # 简单上下文查找
                parts = node.value.split('.')
                current = context
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    elif hasattr(current, part):
                        current = getattr(current, part)
                    else:
                        raise KeyError(f"变量'{node.value}'不存在")
                return current
        
        elif node.type == NodeType.BINARY_OP:
            left = await self._evaluate_ast(node.children[0], context)
            right = await self._evaluate_ast(node.children[1], context)
            
            operator_func = self.operator_functions.get(node.value)
            if operator_func:
                return operator_func(left, right)
            else:
                raise ValueError(f"未知运算符: {node.value}")
        
        elif node.type == NodeType.UNARY_OP:
            operand = await self._evaluate_ast(node.children[0], context)
            
            operator_func = self.unary_operator_functions.get(node.value)
            if operator_func:
                return operator_func(operand)
            else:
                raise ValueError(f"未知一元运算符: {node.value}")
        
        elif node.type == NodeType.FUNCTION:
            # 函数调用
            func_name = node.value
            args = []
            for child in node.children:
                arg_value = await self._evaluate_ast(child, context)
                args.append(arg_value)
            
            # 查找函数
            if func_name in self.builtin_functions:
                func = self.builtin_functions[func_name]
            elif self.function_resolver:
                return await self.function_resolver.resolve_function(func_name, args, {})
            elif func_name in context and callable(context[func_name]):
                func = context[func_name]
            else:
                raise ValueError(f"函数'{func_name}'未找到")
            
            # 调用函数
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args)
                else:
                    return func(*args)
            except Exception as e:
                raise ValueError(f"函数'{func_name}'调用失败: {str(e)}") from e
        
        elif node.type == NodeType.CONDITIONAL:
            # 条件表达式
            condition = await self._evaluate_ast(node.children[0], context)
            if condition:
                return await self._evaluate_ast(node.children[1], context)
            else:
                return await self._evaluate_ast(node.children[2], context)
        
        elif node.type == NodeType.CONCAT:
            # 字符串连接
            result = ""
            for child in node.children:
                part = await self._evaluate_ast(child, context)
                result += str(part)
            return result
        
        elif node.type == NodeType.INTERPOLATION:
            # 字符串插值（已由_parse_interpolation处理为CONCAT）
            # 这里不应该到达
            raise ValueError("INTERPOLATION节点应由CONCAT节点处理")
        
        else:
            raise ValueError(f"未知节点类型: {node.type}")
```

### 测试用例

```python
import pytest
import asyncio

class TestCompositeExpressionParser:
    """CompositeExpressionParser测试类"""
    
    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return CompositeExpressionParser()
    
    @pytest.fixture
    def context(self):
        """创建测试上下文"""
        return {
            'x': 10,
            'y': 20,
            'name': 'Alice',
            'items': [1, 2, 3, 4, 5],
            'add': lambda a, b: a + b,
            'get_greeting': lambda name: f"Hello, {name}"
        }
    
    @pytest.mark.asyncio
    async def test_literal(self, parser, context):
        """测试字面值"""
        result = await parser.parse_and_evaluate('123', context)
        assert result == 123
    
    @pytest.mark.asyncio
    async def test_variable(self, parser, context):
        """测试变量"""
        result = await parser.parse_and_evaluate('x', context)
        assert result == 10
    
    @pytest.mark.asyncio
    async def test_binary_operation(self, parser, context):
        """测试二元运算"""
        result = await parser.parse_and_evaluate('x + y', context)
        assert result == 30
    
    @pytest.mark.asyncio
    async def test_function_call(self, parser, context):
        """测试函数调用"""
        result = await parser.parse_and_evaluate('add(x, y)', context)
        assert result == 30
    
    @pytest.mark.asyncio
    async def test_builtin_function(self, parser, context):
        """测试内置函数"""
        result = await parser.parse_and_evaluate('len(items)', context)
        assert result == 5
    
    @pytest.mark.asyncio
    async def test_conditional(self, parser, context):
        """测试条件表达式"""
        result = await parser.parse_and_evaluate('x > 5 ? "big" : "small"', context)
        assert result == 'big'
    
    @pytest.mark.asyncio
    async def test_string_interpolation(self, parser, context):
        """测试字符串插值"""
        result = await parser.parse_and_evaluate('"Value: ${x}"', context)
        assert result == 'Value: 10'
    
    @pytest.mark.asyncio
    async def test_complex_expression(self, parser, context):
        """测试复杂表达式"""
        result = await parser.parse_and_evaluate('(x + y) * 2 - len(items)', context)
        assert result == (10 + 20) * 2 - 5
    
    @pytest.mark.asyncio
    async def test_nested_interpolation(self, parser, context):
        """测试嵌套插值"""
        result = await parser.parse_and_evaluate('"${name} has ${len(items)} items"', context)
        assert result == 'Alice has 5 items'
    
    @pytest.mark.asyncio
    async def test_error_handling(self, parser, context):
        """测试错误处理"""
        with pytest.raises(ValueError):
            await parser.parse_and_evaluate('undefined_function()', context)
```

## 📊 扩展挑战

### 挑战1：安全沙箱实现

**核心代码**：
```python
class SecuritySandbox:
    """安全沙箱，限制代码执行"""
    
    def __init__(self):
        self.allowed_modules = {
            'math', 'datetime', 'json', 're', 'random',
            'string', 'collections', 'itertools', 'functools'
        }
        self.allowed_functions = {
            'abs', 'len', 'max', 'min', 'sum', 'round',
            'int', 'float', 'str', 'bool', 'list', 'dict',
            'tuple', 'set', 'sorted', 'reversed', 'enumerate',
            'zip', 'map', 'filter', 'range', 'slice'
        }
        self.max_execution_time = 1.0
        self.max_memory_mb = 50
        self.max_recursion_depth = 10
    
    async def evaluate_safely(self, code: str, context: Dict[str, Any]) -> Any:
        """安全执行代码"""
        # 1. 语法检查
        self._validate_syntax(code)
        
        # 2. 危险模式检测
        self._detect_dangerous_patterns(code)
        
        # 3. 资源限制执行
        try:
            result = await asyncio.wait_for(
                self._execute_with_limits(code, context),
                timeout=self.max_execution_time
            )
            return result
        except asyncio.TimeoutError:
            raise SecurityError("执行超时")
        except MemoryError:
            raise SecurityError("内存使用超限")
        except RecursionError:
            raise SecurityError("递归深度超限")
```

### 挑战2：分布式缓存集成

**核心代码**：
```python
class RedisBackedCache:
    """Redis后端缓存"""
    
    def __init__(self, redis_url: str, local_cache_size: int = 1000):
        self.redis = redis.Redis.from_url(redis_url)
        self.local_cache = SmartCache(max_size=local_cache_size)
        self.prefix = "cache:"
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        # 1. 检查本地缓存
        local_value = self.local_cache.get(key)
        if local_value is not None:
            return local_value
        
        # 2. 检查Redis
        redis_key = self.prefix + key
        try:
            redis_value = self.redis.get(redis_key)
            if redis_value is not None:
                # 反序列化
                value = pickle.loads(redis_value)
                # 存入本地缓存
                self.local_cache.set(key, value)
                return value
        except Exception as e:
            logger.warning(f"Redis获取失败: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存值"""
        # 1. 更新本地缓存
        self.local_cache.set(key, value, ttl)
        
        # 2. 更新Redis
        redis_key = self.prefix + key
        try:
            serialized = pickle.dumps(value)
            if ttl:
                self.redis.setex(redis_key, ttl, serialized)
            else:
                self.redis.set(redis_key, serialized)
        except Exception as e:
            logger.warning(f"Redis设置失败: {e}")
```

### 挑战3：表达式语言设计

**核心代码**：
```python
class ExpressionLanguage:
    """表达式语言解释器"""
    
    def __init__(self):
        self.grammar = """
            program     : expr*
            expr        : conditional | logical_or
            conditional : logical_or '?' expr ':' expr
            logical_or  : logical_and ('or' logical_and)*
            logical_and : equality ('and' equality)*
            equality    : comparison (('==' | '!=') comparison)*
            comparison  : term (('<' | '<=' | '>' | '>=') term)*
            term        : factor (('+' | '-') factor)*
            factor      : unary (('*' | '/' | '%' | '//') unary)*
            unary       : ('+' | '-' | 'not') unary | power
            power       : primary ('**' unary)*
            primary     : literal | variable | '(' expr ')' | function_call
            literal     : NUMBER | STRING | BOOL | NULL
            variable    : IDENTIFIER ('.' IDENTIFIER)*
            function_call : IDENTIFIER '(' arguments? ')'
            arguments   : expr (',' expr)*
        """
        self.parser = Lark(self.grammar, start='program')
    
    async def evaluate(self, code: str, context: Dict[str, Any]) -> Any:
        """解析并执行表达式语言代码"""
        # 解析为语法树
        tree = self.parser.parse(code)
        
        # 遍历语法树并计算
        return await self._visit(tree, context)
    
    async def _visit(self, node, context):
        """遍历语法树节点"""
        if node.data == 'program':
            results = []
            for child in node.children:
                result = await self._visit(child, context)
                results.append(result)
            return results[-1] if results else None
        
        elif node.data == 'conditional':
            condition = await self._visit(node.children[0], context)
            if condition:
                return await self._visit(node.children[1], context)
            else:
                return await self._visit(node.children[2], context)
        
        # 其他节点处理...
```

## 📝 常见问题解答

### Q1：变量解析与模板引擎有什么区别？

**A**：变量解析更轻量，专注于变量替换；模板引擎通常包含更复杂的逻辑控制结构（如循环、条件判断）。变量解析可以作为模板引擎的基础组件，但本身不提供完整的模板功能。

### Q2：如何处理循环引用的变量？

**A**：需要检测循环引用并优雅处理。可以维护解析栈，检测到循环时抛出明确异常。实现方案：
```python
class CycleSafeVariableResolver(VariableResolver):
    def __init__(self):
        super().__init__()
        self.resolution_stack = set()
    
    async def resolve(self, expression: str, context: Dict = None) -> Any:
        cache_key = self._generate_cache_key(expression, context)
        
        # 检查循环引用
        if cache_key in self.resolution_stack:
            raise ValueError(f"循环引用检测到: {expression}")
        
        self.resolution_stack.add(cache_key)
        try:
            return await super().resolve(expression, context)
        finally:
            self.resolution_stack.remove(cache_key)
```

### Q3：如何支持数组索引和切片？

**A**：扩展路径解析器支持数组语法：
```python
def _resolve_path(self, path_parts: List[str], context: Dict[str, Any]) -> Any:
    current = context
    
    for part in path_parts:
        # 检查数组索引语法：array[0] 或 array[1:3]
        if '[' in part and part.endswith(']'):
            var_name, index_expr = part.split('[', 1)
            index_expr = index_expr[:-1]  # 移除']'
            
            # 获取数组
            if isinstance(current, dict) and var_name in current:
                current = current[var_name]
            elif hasattr(current, var_name):
                current = getattr(current, var_name)
            else:
                raise KeyError(f"变量'{var_name}'不存在")
            
            # 解析索引
            if ':' in index_expr:
                # 切片
                slice_parts = index_expr.split(':')
                if len(slice_parts) == 2:
                    start = int(slice_parts[0]) if slice_parts[0] else None
                    stop = int(slice_parts[1]) if slice_parts[1] else None
                    current = current[start:stop]
                elif len(slice_parts) == 3:
                    start = int(slice_parts[0]) if slice_parts[0] else None
                    stop = int(slice_parts[1]) if slice_parts[1] else None
                    step = int(slice_parts[2]) if slice_parts[2] else None
                    current = current[start:stop:step]
                else:
                    raise ValueError(f"无效的切片表达式: {index_expr}")
            else:
                # 单个索引
                idx = int(index_expr)
                current = current[idx]
        else:
            # 常规路径解析
            current = self._access_object(current, part)
    
    return current
```

## 🚀 性能优化指南

### 1. 缓存优化策略

**多级缓存架构**：
```python
class MultiLevelCache:
    """多级缓存（L1 + L2）"""
    def __init__(self, l1_size: int = 100, l2_size: int = 1000):
        self.l1 = SmartCache(max_size=l1_size)  # 快速缓存
        self.l2 = SmartCache(max_size=l2_size)  # 大容量缓存
        self.stats = {'l1_hits': 0, 'l2_hits': 0, 'misses': 0}
    
    async def get(self, key: str) -> Optional[Any]:
        # 检查L1
        value = self.l1.get(key)
        if value is not None:
            self.stats['l1_hits'] += 1
            return value
        
        # 检查L2
        value = self.l2.get(key)
        if value is not None:
            self.stats['l2_hits'] += 1
            # 提升到L1
            self.l1.set(key, value)
            return value
        
        self.stats['misses'] += 1
        return None
```

### 2. 并发优化

**连接池管理**：
```python
class ConnectionPool:
    """数据库/网络连接池"""
    def __init__(self, max_connections: int = 10):
        self.semaphore = asyncio.Semaphore(max_connections)
        self.connections = []
    
    async def get_connection(self):
        """获取连接"""
        async with self.semaphore:
            if self.connections:
                return self.connections.pop()
            else:
                return await self._create_connection()
    
    async def release_connection(self, conn):
        """释放连接"""
        self.connections.append(conn)
```

### 3. 内存优化

**对象池**：
```python
class ObjectPool:
    """对象池，减少内存分配"""
    def __init__(self, create_func, max_size: int = 100):
        self.create_func = create_func
        self.max_size = max_size
        self.pool = []
    
    async def acquire(self):
        """获取对象"""
        if self.pool:
            return self.pool.pop()
        else:
            return await self.create_func()
    
    async def release(self, obj):
        """释放对象"""
        if len(self.pool) < self.max_size:
            self.pool.append(obj)
        # 否则让对象被垃圾回收
```

### 4. 性能监控

**性能分析装饰器**：
```python
def profile_performance(func):
    """性能分析装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss
            
            duration = end_time - start_time
            memory_used = (end_memory - start_memory) / 1024 / 1024  # MB
            
            logger.info(
                f"{func.__name__} - 耗时: {duration:.3f}s, "
                f"内存使用: {memory_used:.1f}MB"
            )
    
    return wrapper
```

---

**课程设计**: DeerFlow Python Agent架构师训练营  
**版本**: v1.0.0  
**最后更新**: 2024年4月12日  
**教师**: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）  
**版权所有**: © 2024 DeerFlow Team. 保留所有权利。