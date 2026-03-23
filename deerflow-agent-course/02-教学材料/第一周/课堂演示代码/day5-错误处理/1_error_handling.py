"""
Day 5 - 错误处理中间件
演示DeerFlow风格的错误处理机制
"""

from typing import Callable, Any, Type, Optional
import traceback
from enum import Enum


class ErrorCode(Enum):
    """错误代码"""
    TOOL_NOT_FOUND = "TOOL_001"
    TOOL_EXECUTION_FAILED = "TOOL_002"
    INVALID_PARAMETERS = "TOOL_003"
    TIMEOUT = "TOOL_004"
    SANDBOX_ERROR = "SANDBOX_001"
    AUTH_ERROR = "AUTH_001"


class AgentError(Exception):
    """Agent基础异常"""
    
    def __init__(self, code: ErrorCode, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ToolNotFoundError(AgentError):
    """工具未找到"""
    def __init__(self, tool_name: str):
        super().__init__(
            ErrorCode.TOOL_NOT_FOUND,
            f"工具 '{tool_name}' 未找到",
            {"tool_name": tool_name}
        )


class ToolExecutionError(AgentError):
    """工具执行失败"""
    def __init__(self, tool_name: str, reason: str):
        super().__init__(
            ErrorCode.TOOL_EXECUTION_FAILED,
            f"工具 '{tool_name}' 执行失败: {reason}",
            {"tool_name": tool_name, "reason": reason}
        )


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.handlers: dict[Type[Exception], Callable] = {}
    
    def register(self, exception_type: Type[Exception], handler: Callable):
        """注册错误处理器"""
        self.handlers[exception_type] = handler
    
    def handle(self, error: Exception) -> str:
        """处理错误"""
        error_type = type(error)
        
        for exc_type, handler in self.handlers.items():
            if isinstance(error, exc_type):
                return handler(error)
        
        return self._default_handler(error)
    
    def _default_handler(self, error: Exception) -> str:
        """默认错误处理"""
        return f"未知错误: {str(error)}"


class RetryStrategy:
    """重试策略"""
    
    def __init__(self, max_retries: int = 3, backoff: float = 1.0):
        self.max_retries = max_retries
        self.backoff = backoff
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """带重试的执行"""
        import time
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff * (2 ** attempt)
                    print(f"重试 {attempt + 1}/{self.max_retries}, 等待 {wait_time}秒...")
                    time.sleep(wait_time)
        
        raise last_error


def handle_tool_not_found(error: ToolNotFoundError) -> str:
    """处理工具未找到错误"""
    return f"抱歉，工具 '{error.details['tool_name']}' 不可用。请尝试其他工具。"


def handle_tool_execution(error: ToolExecutionError) -> str:
    """处理工具执行错误"""
    return f"工具执行遇到问题: {error.message}. 请检查参数后重试。"


def demonstrate_error_handling():
    """演示错误处理"""
    print("=" * 50)
    print("错误处理示例")
    print("=" * 50)
    
    handler = ErrorHandler()
    handler.register(ToolNotFoundError, handle_tool_not_found)
    handler.register(ToolExecutionError, handle_tool_execution)
    
    # 测试
    errors = [
        ToolNotFoundError("web_search"),
        ToolExecutionError("calculator", "除数不能为零")
    ]
    
    for error in errors:
        response = handler.handle(error)
        print(f"\n错误: {error.code.value}")
        print(f"响应: {response}")


if __name__ == "__main__":
    demonstrate_error_handling()
