"""
Day 4 - 中间件模式
演示DeerFlow风格的中间件实现
"""

from typing import Callable, Any, Dict, List
from functools import wraps
import time
from datetime import datetime


class MiddlewareChain:
    """中间件链"""
    
    def __init__(self):
        self.middlewares: List[Callable] = []
    
    def add(self, middleware: Callable) -> "MiddlewareChain":
        self.middlewares.append(middleware)
        return self
    
    def execute(self, context: dict, handler: Callable) -> Any:
        """执行中间件链"""
        
        def next_handler(index: int = 0) -> Any:
            if index >= len(self.middlewares):
                return handler(context)
            
            middleware = self.middlewares[index]
            
            def wrapper():
                return middleware(context, lambda: next_handler(index + 1))
            
            return wrapper()
        
        return next_handler()


class BaseMiddleware:
    """中间件基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    def before(self, context: dict) -> dict:
        """前置处理"""
        return context
    
    def after(self, context: dict, result: Any) -> Any:
        """后置处理"""
        return result
    
    def __call__(self, context: dict, next_handler: Callable) -> Any:
        """中间件调用"""
        context = self.before(context)
        result = next_handler()
        return self.after(context, result)


class LoggingMiddleware(BaseMiddleware):
    """日志中间件"""
    
    def before(self, context: dict) -> dict:
        print(f"[{self.name}] 请求: {context.get('action', 'unknown')}")
        return context
    
    def after(self, context: dict, result: Any) -> Any:
        print(f"[{self.name}] 响应: {result}")
        return result


class TimingMiddleware(BaseMiddleware):
    """性能监控中间件"""
    
    def before(self, context: dict) -> dict:
        context["start_time"] = time.time()
        return context
    
    def after(self, context: dict, result: Any) -> Any:
        duration = time.time() - context.get("start_time", 0)
        print(f"[{self.name}] 耗时: {duration:.3f}秒")
        return result


class ValidationMiddleware(BaseMiddleware):
    """验证中间件"""
    
    def before(self, context: dict) -> dict:
        if "user_id" not in context:
            raise ValueError("缺少user_id参数")
        return context


class SandboxMiddleware(BaseMiddleware):
    """沙箱中间件"""
    
    def before(self, context: dict) -> dict:
        print(f"[{self.name}] 启用沙箱隔离")
        context["sandbox_enabled"] = True
        return context


def demo_handler(context: dict) -> str:
    """模拟业务处理器"""
    return f"处理完成: {context.get('user_id', 'unknown')}"


def demonstrate_middleware():
    """演示中间件链"""
    print("=" * 50)
    print("中间件模式示例")
    print("=" * 50)
    
    # 构建中间件链
    chain = MiddlewareChain()
    chain.add(LoggingMiddleware("Logger"))
    chain.add(TimingMiddleware("Timer"))
    chain.add(ValidationMiddleware("Validator"))
    chain.add(SandboxMiddleware("Sandbox"))
    
    # 执行
    context = {
        "action": "process_data",
        "user_id": "user_123"
    }
    
    print("\n执行中间件链:")
    result = chain.execute(context, lambda: demo_handler(context))
    print(f"\n最终结果: {result}")


if __name__ == "__main__":
    demonstrate_middleware()
