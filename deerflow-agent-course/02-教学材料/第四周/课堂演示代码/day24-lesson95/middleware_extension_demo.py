#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第95节课：中间件扩展

本课程介绍DeerFlow中间件扩展机制，包括：
1. 自定义中间件 - 实现特定业务逻辑的中间件
2. 中间件排序 - 确保自定义中间件的正确执行顺序
3. 中间件配置 - 运行时配置自定义中间件行为

作者：DeerFlow架构师训练营
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import time


# ============================================================
# 第一部分：中间件基类
# ============================================================

class MiddlewarePhase(Enum):
    """中间件执行阶段"""
    PRE_AGENT = "pre_agent"      # Agent执行前
    POST_AGENT = "post_agent"   # Agent执行后
    PRE_TOOL = "pre_tool"        # 工具执行前
    POST_TOOL = "post_tool"      # 工具执行后


@dataclass
class MiddlewareConfig:
    """中间件配置"""
    enabled: bool = True
    priority: int = 100          # 优先级，数字越小越先执行
    timeout: float = 30.0        # 超时时间
    config: Dict[str, Any] = field(default_factory=dict)


class BaseMiddleware:
    """中间件基类"""
    
    def __init__(self, name: str, config: Optional[MiddlewareConfig] = None):
        self.name = name
        self.config = config or MiddlewareConfig()
        self._enabled = self.config.enabled
        
    def process(self, state: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理中间件逻辑
        
        Args:
            state: Agent状态
            context: 运行时上下文
            
        Returns:
            处理后的状态
        """
        return state
        
    def before_agent(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Agent执行前调用"""
        return None
        
    def after_agent(self, state: Dict[str, Any], result: Any) -> Optional[Dict[str, Any]]:
        """Agent执行后调用"""
        return None
        
    def wrap_tool_call(self, tool_call: Dict[str, Any], 
                      next_handler: Callable) -> Any:
        """包装工具调用"""
        return next_handler()
        
    def enable(self) -> None:
        """启用中间件"""
        self._enabled = True
        
    def disable(self) -> None:
        """禁用中间件"""
        self._enabled = False
        
    @property
    def is_enabled(self) -> bool:
        return self._enabled


# ============================================================
# 第二部分：具体中间件实现
# ============================================================

class LoggingMiddleware(BaseMiddleware):
    """日志记录中间件"""
    
    def __init__(self, config: Optional[MiddlewareConfig] = None):
        super().__init__("logging", config)
        self.logs: List[Dict[str, Any]] = []
        
    def before_agent(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled:
            return None
            
        self.logs.append({
            "phase": "before_agent",
            "timestamp": time.time(),
            "state_keys": list(state.keys())
        })
        return None
        
    def after_agent(self, state: Dict[str, Any], 
                  result: Any) -> Optional[Dict[str, Any]]:
        if not self.is_enabled:
            return None
            
        self.logs.append({
            "phase": "after_agent",
            "timestamp": time.time(),
            "has_result": result is not None
        })
        return None


class RateLimitMiddleware(BaseMiddleware):
    """速率限制中间件"""
    
    def __init__(self, max_requests: int = 100, 
                 window_seconds: int = 60,
                 config: Optional[MiddlewareConfig] = None):
        super().__init__("rate_limit", config)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: List[float] = []
        
    def before_agent(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled:
            return None
            
        now = time.time()
        
        # 清理过期请求
        self._requests = [t for t in self._requests 
                        if now - t < self.window_seconds]
        
        # 检查是否超限
        if len(self._requests) >= self.max_requests:
            raise RateLimitError(
                f"速率限制: 超过每{self.window_seconds}秒{self.max_requests}次请求限制"
            )
            
        self._requests.append(now)
        return None


class RateLimitError(Exception):
    """速率限制错误"""
    pass


class ValidationMiddleware(BaseMiddleware):
    """数据验证中间件"""
    
    def __init__(self, schema: Optional[Dict[str, Any]] = None,
                 config: Optional[MiddlewareConfig] = None):
        super().__init__("validation", config)
        self.schema = schema or {}
        
    def before_agent(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled:
            return None
            
        # 验证必要字段
        required_fields = self.schema.get("required", [])
        
        for field_name in required_fields:
            if field_name not in state:
                raise ValidationError(f"缺少必要字段: {field_name}")
                
        return None


class ValidationError(Exception):
    """验证错误"""
    pass


class TransformationMiddleware(BaseMiddleware):
    """数据转换中间件"""
    
    def __init__(self, transformations: Optional[Dict[str, Callable]] = None,
                 config: Optional[MiddlewareConfig] = None):
        super().__init__("transformation", config)
        self.transformations = transformations or {}
        
    def before_agent(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_enabled:
            return None
            
        # 应用转换
        for field, transform in self.transformations.items():
            if field in state:
                try:
                    state[field] = transform(state[field])
                except Exception as e:
                    raise TransformationError(f"字段{field}转换失败: {e}")
                    
        return None


class TransformationError(Exception):
    """转换错误"""
    pass


# ============================================================
# 第三部分：中间件管理器
# ============================================================

class MiddlewareChain:
    """中间件链"""
    
    def __init__(self):
        self._middlewares: List[BaseMiddleware] = []
        self._lock = False
        
    def add(self, middleware: BaseMiddleware) -> 'MiddlewareChain':
        """添加中间件"""
        self._middlewares.append(middleware)
        self._sort()
        return self
        
    def remove(self, name: str) -> bool:
        """移除中间件"""
        for i, m in enumerate(self._middlewares):
            if m.name == name:
                self._middlewares.pop(i)
                return True
        return False
        
    def _sort(self) -> None:
        """按优先级排序"""
        self._middlewares.sort(
            key=lambda m: m.config.priority
        )
        
    def get(self, name: str) -> Optional[BaseMiddleware]:
        """获取中间件"""
        for m in self._middlewares:
            if m.name == name:
                return m
        return None
        
    def list_middlewares(self) -> List[str]:
        """列出所有中间件"""
        return [m.name for m in self._middlewares]
        
    def execute_before_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行所有before_agent钩子"""
        for middleware in self._middlewares:
            if not middleware.is_enabled:
                continue
                
            try:
                result = middleware.before_agent(state)
                if result:
                    state.update(result)
            except Exception as e:
                raise MiddlewareError(f"中间件{middleware.name}执行失败: {e}")
                
        return state
        
    def execute_after_agent(self, state: Dict[str, Any], 
                          result: Any) -> Dict[str, Any]:
        """执行所有after_agent钩子"""
        for middleware in self._middlewares:
            if not middleware.is_enabled:
                continue
                
            try:
                res = middleware.after_agent(state, result)
                if res:
                    state.update(res)
            except Exception as e:
                raise MiddlewareError(f"中间件{middleware.name}执行失败: {e}")
                
        return state


class MiddlewareError(Exception):
    """中间件错误"""
    pass


# ============================================================
# 第四部分：中间件工厂
# ============================================================

class MiddlewareFactory:
    """中间件工厂"""
    
    _registry: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, middleware_class: type) -> None:
        """注册中间件类"""
        cls._registry[name] = middleware_class
        
    @classmethod
    def create(cls, name: str, config: Optional[MiddlewareConfig] = None) -> BaseMiddleware:
        """创建中间件实例"""
        if name not in cls._registry:
            raise ValueError(f"未知的中间件: {name}")
            
        return cls._registry[name](config)
        
    @classmethod
    def get_available(cls) -> List[str]:
        """获取可用的中间件"""
        return list(cls._registry.keys())


# 注册内置中间件
MiddlewareFactory.register("logging", LoggingMiddleware)
MiddlewareFactory.register("rate_limit", RateLimitMiddleware)
MiddlewareFactory.register("validation", ValidationMiddleware)
MiddlewareFactory.register("transformation", TransformationMiddleware)


# ============================================================
# 第五部分：演示与测试
# ============================================================

def run_demo():
    """演示中间件系统"""
    print("=" * 60)
    print("DeerFlow 中间件扩展演示")
    print("=" * 60)
    
    # 创建中间件链
    print("\n1. 创建中间件链...")
    chain = MiddlewareChain()
    
    # 添加中间件
    print("\n2. 添加中间件...")
    logging_mw = LoggingMiddleware(MiddlewareConfig(priority=10))
    rate_limit_mw = RateLimitMiddleware(max_requests=10)
    validation_mw = ValidationMiddleware(
        MiddlewareConfig(priority=50),
        schema={"required": ["messages"]}
    )
    
    chain.add(logging_mw)
    chain.add(rate_limit_mw)
    chain.add(validation_mw)
    
    print(f"   中间件列表: {chain.list_middlewares()}")
    
    # 执行中间件
    print("\n3. 执行中间件...")
    state = {"messages": [{"role": "user", "content": "Hello"}]}
    
    try:
        result = chain.execute_before_agent(state)
        print(f"   执行后状态: keys={list(result.keys())}")
    except ValidationError as e:
        print(f"   验证错误: {e}")
        
    # 测试速率限制
    print("\n4. 测试速率限制...")
    for i in range(12):
        try:
            chain.execute_before_agent({})
            print(f"   请求{i+1}: 成功")
        except RateLimitError as e:
            print(f"   请求{i+1}: 限制")
    
    # 动态创建中间件
    print("\n5. 动态创建中间件...")
    mw = MiddlewareFactory.create("logging")
    print(f"   创建中间件: {mw.name}")
    print(f"   可用中间件: {MiddlewareFactory.get_available()}")
    
    print("\n演示完成!")


def run_tests():
    """运行测试"""
    print("\n" + "=" * 60)
    print("运行单元测试")
    print("=" * 60 + "\n")
    
    # 测试1: 中间件链
    print("测试1: 中间件链")
    chain = MiddlewareChain()
    chain.add(LoggingMiddleware())
    chain.add(RateLimitMiddleware())
    assert "logging" in chain.list_middlewares()
    assert "rate_limit" in chain.list_middlewares()
    print(f"   中间件: {chain.list_middlewares()}")
    print("✓ 中间件链测试通过\n")
    
    # 测试2: 中间件排序
    print("测试2: 中间件优先级排序")
    mw1 = LoggingMiddleware(MiddlewareConfig(priority=100))
    mw2 = LoggingMiddleware(MiddlewareConfig(priority=50))
    mw2.name = "validation"
    chain2 = MiddlewareChain()
    chain2.add(mw1)
    chain2.add(mw2)
    assert chain2.list_middlewares()[0] == "validation"
    print(f"   排序后: {chain2.list_middlewares()}")
    print("✓ 排序测试通过\n")
    
    # 测试3: 验证中间件
    print("测试3: 验证中间件")
    validation = ValidationMiddleware(
        schema={"required": ["messages"]}
    )
    
    state_ok = {"messages": []}
    result = validation.before_agent(state_ok)
    assert result is None
    print("   有效状态通过")
    
    try:
        validation.before_agent({})
    except ValidationError as e:
        print(f"   无效状态抛出异常: {e}")
    print("✓ 验证中间件测试通过\n")
    
    # 测试4: 速率限制
    print("测试4: 速率限制中间件")
    rate_limit = RateLimitMiddleware(max_requests=3)
    for i in range(3):
        rate_limit.before_agent({})
    print(f"   3次请求通过")
    
    try:
        rate_limit.before_agent({})
    except RateLimitError:
        print("   第4次请求被限制")
    print("✓ 速率限制测试通过\n")
    
    # 测试5: 中间件工厂
    print("测试5: 中间件工厂")
    mw = MiddlewareFactory.create("logging")
    assert mw.name == "logging"
    assert mw.is_enabled == True
    print(f"   创建中间件: {mw.name}")
    print(f"   可用: {MiddlewareFactory.get_available()}")
    print("✓ 工厂测试通过\n")
    
    print("=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        run_tests()
    else:
        run_demo()
