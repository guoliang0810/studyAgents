#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeerFlow Python Agent架构师训练营 - 第76节课：错误信息优化 演示代码

本文件演示了错误信息优化（Error Message Optimization）的完整实现，包括：
1. UserFriendlyError类：用户友好的错误基类，支持错误上下文和建议
2. 专用错误类体系：ConfigError、DependencyError、ValidationError等
3. ErrorHandlingMiddleware类：错误处理中间件，实现错误转换和日志记录
4. ErrorContext类：错误上下文信息管理
5. 完整测试套件：验证错误处理和转换功能

学习目标：
- 掌握用户友好错误信息的设计原则
- 理解错误处理中间件的工作机制
- 实现错误类型转换和自动建议生成
- 提升开发者体验（DX）的错误设计

使用方式：
python error_message_demo.py          # 运行演示
python error_message_demo.py --test   # 运行测试套件
python error_message_demo.py --bench  # 运行性能基准测试
"""

import asyncio
import sys
import logging
import time
import json
import traceback
import re
from typing import Dict, List, Optional, Any, Set, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import copy

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 枚举类型定义
# ============================================================================

class ErrorSeverity(Enum):
    """错误严重级别"""
    DEBUG = "debug"           # 调试信息
    INFO = "info"             # 一般信息
    WARNING = "warning"        # 警告
    ERROR = "error"           # 错误
    CRITICAL = "critical"     # 严重错误


class ErrorCategory(Enum):
    """错误类别"""
    CONFIGURATION = "configuration"    # 配置错误
    DEPENDENCY = "dependency"        # 依赖错误
    VALIDATION = "validation"         # 验证错误
    AUTHENTICATION = "authentication" # 认证错误
    AUTHORIZATION = "authorization"    # 授权错误
    NETWORK = "network"             # 网络错误
    DATABASE = "database"           # 数据库错误
    RUNTIME = "runtime"             # 运行时错误
    UNKNOWN = "unknown"             # 未知错误


class ErrorCode(Enum):
    """错误代码枚举"""
    # 配置错误码 (1000-1999)
    CONFIG_NOT_FOUND = 1001
    CONFIG_PARSE_ERROR = 1002
    CONFIG_INVALID_FORMAT = 1003
    CONFIG_MISSING_FIELD = 1004
    
    # 依赖错误码 (2000-2999)
    DEPENDENCY_NOT_FOUND = 2001
    DEPENDENCY_CYCLE_DETECTED = 2002
    DEPENDENCY_VERSION_MISMATCH = 2003
    DEPENDENCY_LOAD_FAILED = 2004
    
    # 验证错误码 (3000-3999)
    VALIDATION_FAILED = 3001
    VALIDATION_TYPE_ERROR = 3002
    VALIDATION_RANGE_ERROR = 3003
    VALIDATION_FORMAT_ERROR = 3004
    
    # 通用错误码 (9000-9999)
    UNKNOWN_ERROR = 9001
    INTERNAL_ERROR = 9002
    NOT_IMPLEMENTED = 9003


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class ErrorSuggestion:
    """错误建议数据类"""
    message: str                      # 建议消息
    action: str                        # 建议操作
    documentation_url: Optional[str] = None  # 文档链接
    priority: int = 1                  # 优先级（1-5，1最高）
    
    def __str__(self) -> str:
        return f"[{self.priority}] {self.message} → {self.action}"


@dataclass
class ErrorContext:
    """错误上下文数据类"""
    timestamp: datetime = field(default_factory=datetime.now)  # 错误发生时间
    module: Optional[str] = None       # 错误发生模块
    function: Optional[str] = None     # 错误发生函数
    line_number: Optional[int] = None # 错误发生行号
    file_path: Optional[str] = None   # 错误发生文件
    stack_trace: Optional[str] = None # 堆栈跟踪
    environment: Dict[str, str] = field(default_factory=dict)  # 环境信息
    request_id: Optional[str] = None   # 请求ID
    user_id: Optional[str] = None     # 用户ID
    additional_data: Dict[str, Any] = field(default_factory=dict)  # 额外数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "module": self.module,
            "function": self.function,
            "line_number": self.line_number,
            "file_path": self.file_path,
            "stack_trace": self.stack_trace,
            "environment": self.environment,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "additional_data": self.additional_data
        }


@dataclass
class UserFriendlyError(Exception):
    """
    用户友好错误基类
    
    特性：
    - 清晰的错误消息
    - 具体的错误上下文
    - 可操作的修复建议
    - 错误代码和类别
    - 多语言支持基础
    """
    message: str                                    # 错误消息
    code: ErrorCode = ErrorCode.UNKNOWN_ERROR        # 错误代码
    category: ErrorCategory = ErrorCategory.UNKNOWN  # 错误类别
    severity: ErrorSeverity = ErrorSeverity.ERROR   # 严重级别
    suggestions: List[ErrorSuggestion] = field(default_factory=list)  # 建议列表
    context: ErrorContext = field(default_factory=ErrorContext)  # 错误上下文
    original_exception: Optional[Exception] = None   # 原始异常
    details: Dict[str, Any] = field(default_factory=dict)  # 额外详情
    
    def __init__(self, 
                 message: str,
                 code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 suggestions: Optional[List[ErrorSuggestion]] = None,
                 context: Optional[ErrorContext] = None,
                 original_exception: Optional[Exception] = None,
                 **kwargs):
        """
        初始化用户友好错误
        
        Args:
            message: 错误消息
            code: 错误代码
            category: 错误类别
            severity: 严重级别
            suggestions: 建议列表
            context: 错误上下文
            original_exception: 原始异常
            **kwargs: 额外详情
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.severity = severity
        self.suggestions = suggestions or []
        self.context = context or ErrorContext()
        self.original_exception = original_exception
        self.details = kwargs
    
    def add_suggestion(self, 
                      message: str, 
                      action: str,
                      documentation_url: Optional[str] = None,
                      priority: int = 1) -> 'UserFriendlyError':
        """添加建议"""
        suggestion = ErrorSuggestion(
            message=message,
            action=action,
            documentation_url=documentation_url,
            priority=priority
        )
        self.suggestions.append(suggestion)
        self.suggestions.sort(key=lambda s: s.priority)
        return self
    
    def set_context(self, 
                   module: Optional[str] = None,
                   function: Optional[str] = None,
                   **kwargs) -> 'UserFriendlyError':
        """设置错误上下文"""
        if module:
            self.context.module = module
        if function:
            self.context.function = function
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（适合JSON序列化）"""
        return {
            "error": {
                "message": self.message,
                "code": self.code.value,
                "category": self.category.value,
                "severity": self.severity.value,
                "suggestions": [
                    {
                        "message": s.message,
                        "action": s.action,
                        "documentation_url": s.documentation_url,
                        "priority": s.priority
                    }
                    for s in self.suggestions
                ],
                "context": self.context.to_dict(),
                "details": self.details
            }
        }
    
    def to_user_string(self) -> str:
        """转换为用户友好的字符串"""
        lines = [
            f"❌ {self.category.value.upper()} Error [{self.code.value}]: {self.message}",
            ""
        ]
        
        # 添加上下文信息
        if self.context.module or self.context.function:
            location = []
            if self.context.module:
                location.append(self.context.module)
            if self.context.function:
                location.append(self.context.function)
            if self.context.line_number:
                location.append(f"line {self.context.line_number}")
            lines.append(f"📍 Location: {'.'.join(location)}")
        
        # 添加建议
        if self.suggestions:
            lines.append("")
            lines.append("💡 Suggestions:")
            for i, suggestion in enumerate(self.suggestions[:3], 1):  # 最多显示3条
                lines.append(f"  {i}. {suggestion.message}")
                if suggestion.action:
                    lines.append(f"     → {suggestion.action}")
        
        # 添加详细信息（如果有）
        if self.details:
            lines.append("")
            lines.append("📋 Details:")
            for key, value in self.details.items():
                lines.append(f"  • {key}: {value}")
        
        return "\n".join(lines)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"[{self.code.value}] {self.message}"
    
    def __repr__(self) -> str:
        """调试表示"""
        return f"UserFriendlyError(code={self.code.value}, category={self.category.value}, message='{self.message}')"


# ============================================================================
# 专用错误类
# ============================================================================

class ConfigError(UserFriendlyError):
    """配置错误"""
    
    def __init__(self, 
                 message: str,
                 config_path: Optional[str] = None,
                 config_value: Any = None,
                 **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.CONFIG_NOT_FOUND if "not found" in message.lower() 
                 else ErrorCode.CONFIG_PARSE_ERROR,
            category=ErrorCategory.CONFIGURATION,
            **kwargs
        )
        self.config_path = config_path
        self.config_value = config_value
        
        # 添加通用配置错误建议
        if config_path:
            self.add_suggestion(
                message=f"配置文件路径 '{config_path}' 未找到或无效",
                action=f"请检查配置文件是否存在，路径是否正确",
                documentation_url="https://docs.example.com/config",
                priority=1
            )


class DependencyError(UserFriendlyError):
    """依赖错误"""
    
    def __init__(self,
                 message: str,
                 dependency_name: Optional[str] = None,
                 dependency_version: Optional[str] = None,
                 **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.DEPENDENCY_NOT_FOUND if "not found" in message.lower()
                 else ErrorCode.DEPENDENCY_LOAD_FAILED,
            category=ErrorCategory.DEPENDENCY,
            **kwargs
        )
        self.dependency_name = dependency_name
        self.dependency_version = dependency_version
        
        # 添加依赖错误建议
        if dependency_name:
            self.add_suggestion(
                message=f"依赖 '{dependency_name}' 无法加载",
                action=f"请运行 'pip install {dependency_name}' 安装依赖",
                documentation_url="https://docs.example.com/dependencies",
                priority=1
            )
        
        if "cycle" in message.lower():
            self.code = ErrorCode.DEPENDENCY_CYCLE_DETECTED
            self.add_suggestion(
                message="检测到循环依赖",
                action="请检查组件依赖关系，确保没有循环引用",
                documentation_url="https://docs.example.com/dependency-cycle",
                priority=1
            )


class ValidationError(UserFriendlyError):
    """验证错误"""
    
    def __init__(self,
                 message: str,
                 field_name: Optional[str] = None,
                 field_value: Any = None,
                 expected_type: Optional[str] = None,
                 **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_FAILED,
            category=ErrorCategory.VALIDATION,
            **kwargs
        )
        self.field_name = field_name
        self.field_value = field_value
        self.expected_type = expected_type
        
        # 添加验证错误建议
        if field_name:
            self.add_suggestion(
                message=f"字段 '{field_name}' 验证失败",
                action=f"请检查字段值是否符合预期格式",
                documentation_url="https://docs.example.com/validation",
                priority=1
            )
        
        if expected_type:
            self.add_suggestion(
                message=f"期望类型: {expected_type}",
                action=f"请确保字段值类型正确",
                priority=2
            )


class NetworkError(UserFriendlyError):
    """网络错误"""
    
    def __init__(self,
                 message: str,
                 url: Optional[str] = None,
                 status_code: Optional[int] = None,
                 **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.RUNTIME_ERROR,
            category=ErrorCategory.NETWORK,
            **kwargs
        )
        self.url = url
        self.status_code = status_code
        
        # 添加网络错误建议
        if url:
            self.add_suggestion(
                message=f"无法连接到 {url}",
                action="请检查网络连接和URL是否正确",
                documentation_url="https://docs.example.com/network",
                priority=1
            )
        
        if status_code:
            if status_code == 404:
                self.add_suggestion(
                    message="资源未找到 (404)",
                    action="请检查URL是否正确，资源是否存在",
                    priority=2
                )
            elif status_code >= 500:
                self.add_suggestion(
                    message="服务器错误",
                    action="请稍后重试或联系管理员",
                    priority=2
                )


# ============================================================================
# 错误转换器
# ============================================================================

class ErrorTransformer:
    """
    错误转换器 - 将原始异常转换为用户友好错误
    
    功能：
    - 自动分析原始异常
    - 生成上下文信息
    - 提供修复建议
    - 支持自定义转换规则
    """
    
    # 异常到错误类别的映射
    EXCEPTION_CATEGORY_MAP: Dict[Type[Exception], ErrorCategory] = {
        ImportError: ErrorCategory.DEPENDENCY,
        ModuleNotFoundError: ErrorCategory.DEPENDENCY,
        FileNotFoundError: ErrorCategory.CONFIGURATION,
        PermissionError: ErrorCategory.AUTHORIZATION,
        ValueError: ErrorCategory.VALIDATION,
        TypeError: ErrorCategory.VALIDATION,
        KeyError: ErrorCategory.VALIDATION,
        TimeoutError: ErrorCategory.NETWORK,
        ConnectionError: ErrorCategory.NETWORK,
    }
    
    # 错误消息模式和建议映射
    ERROR_PATTERN_SUGGESTIONS = [
        # ModuleNotFoundError
        (
            r"No module named ['\"]([^'\"]+)['\"]",
            lambda m: ErrorSuggestion(
                message=f"缺少模块: {m.group(1)}",
                action=f"运行 'pip install {m.group(1)}' 安装模块",
                documentation_url=f"https://pypi.org/project/{m.group(1)}/",
                priority=1
            )
        ),
        # FileNotFoundError
        (
            r"\[Errno 2\] No such file or directory: ['\"]([^'\"]+)['\"]",
            lambda m: ErrorSuggestion(
                message=f"文件未找到: {m.group(1)}",
                action="请检查文件路径是否正确，文件是否存在",
                priority=1
            )
        ),
        # ValueError
        (
            r"invalid literal for int\(\): ['\"]([^'\"]+)['\"]",
            lambda m: ErrorSuggestion(
                message=f"无法将 '{m.group(1)}' 转换为整数",
                action="请确保输入的值是有效的整数格式",
                priority=1
            )
        ),
        # JSONDecodeError
        (
            r"Expecting value: line (\d+) column (\d+)",
            lambda m: ErrorSuggestion(
                message=f"JSON解析错误在第 {m.group(1)} 行",
                action="请检查JSON格式是否正确，是否有逗号、引号等语法错误",
                priority=1
            )
        ),
    ]
    
    def __init__(self, 
                 include_stack_trace: bool = True,
                 max_suggestions: int = 3):
        """
        初始化错误转换器
        
        Args:
            include_stack_trace: 是否包含堆栈跟踪
            max_suggestions: 最大建议数量
        """
        self.include_stack_trace = include_stack_trace
        self.max_suggestions = max_suggestions
        self.custom_transformers: Dict[Type[Exception], Callable[[Exception], UserFriendlyError]] = {}
    
    def register_transformer(self, 
                            exception_type: Type[Exception],
                            transformer: Callable[[Exception], UserFriendlyError]) -> None:
        """注册自定义转换器"""
        self.custom_transformers[exception_type] = transformer
    
    def transform(self, 
                 exception: Exception,
                 default_message: Optional[str] = None,
                 **context_kwargs) -> UserFriendlyError:
        """
        将异常转换为用户友好错误
        
        Args:
            exception: 原始异常
            default_message: 默认错误消息
            **context_kwargs: 额外上下文信息
        
        Returns:
            用户友好错误
        """
        # 检查是否有自定义转换器
        for exc_type, transformer in self.custom_transformers.items():
            if isinstance(exception, exc_type):
                return transformer(exception)
        
        # 确定错误类别
        category = ErrorCategory.UNKNOWN
        for exc_type, cat in self.EXCEPTION_CATEGORY_MAP.items():
            if isinstance(exception, exc_type):
                category = cat
                break
        
        # 生成错误消息
        message = default_message or str(exception)
        
        # 创建错误上下文
        context = self._create_error_context(exception, **context_kwargs)
        
        # 生成建议
        suggestions = self._generate_suggestions(exception)
        
        # 确定错误代码
        code = self._determine_error_code(exception, category)
        
        # 确定严重级别
        severity = self._determine_severity(exception)
        
        # 创建错误对象
        error = UserFriendlyError(
            message=message,
            code=code,
            category=category,
            severity=severity,
            suggestions=suggestions,
            context=context,
            original_exception=exception
        )
        
        # 添加原始异常详情
        if self.include_stack_trace:
            error.details["original_type"] = type(exception).__name__
            error.details["stack_trace"] = "".join(traceback.format_tb(exception.__traceback__))
        
        return error
    
    def _create_error_context(self, 
                            exception: Exception,
                            **kwargs) -> ErrorContext:
        """创建错误上下文"""
        context = ErrorContext()
        
        # 从堆栈跟踪获取信息
        if exception.__traceback__:
            tb = exception.__traceback__
            while tb.tb_next:
                tb = tb.tb_next
            
            context.file_path = tb.tb_frame.f_code.co_filename
            context.line_number = tb.tb_lineno
            context.function = tb.tb_frame.f_code.co_name
            context.module = tb.tb_frame.f_globals.get("__name__", "__main__")
        
        # 设置堆栈跟踪
        if self.include_stack_trace:
            context.stack_trace = traceback.format_exc()
        
        # 应用额外的上下文参数
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        return context
    
    def _generate_suggestions(self, exception: Exception) -> List[ErrorSuggestion]:
        """生成错误建议"""
        suggestions = []
        error_message = str(exception)
        
        # 尝试匹配错误模式
        for pattern, suggestion_fn in self.ERROR_PATTERN_SUGGESTIONS:
            match = re.search(pattern, error_message)
            if match:
                suggestion = suggestion_fn(match)
                suggestions.append(suggestion)
        
        # 根据异常类型添加通用建议
        if isinstance(exception, ImportError):
            suggestions.append(ErrorSuggestion(
                message="导入错误",
                action="请确保所有依赖已正确安装",
                priority=2
            ))
        
        if isinstance(exception, FileNotFoundError):
            suggestions.append(ErrorSuggestion(
                message="文件未找到",
                action="请检查文件路径是否正确",
                priority=2
            ))
        
        # 去重并限制数量
        unique_suggestions = []
        seen_messages = set()
        for s in suggestions:
            if s.message not in seen_messages:
                unique_suggestions.append(s)
                seen_messages.add(s.message)
        
        return unique_suggestions[:self.max_suggestions]
    
    def _determine_error_code(self, 
                              exception: Exception, 
                              category: ErrorCategory) -> ErrorCode:
        """确定错误代码"""
        error_str = str(exception).lower()
        
        if category == ErrorCategory.CONFIGURATION:
            if "not found" in error_str:
                return ErrorCode.CONFIG_NOT_FOUND
            if "parse" in error_str or "invalid" in error_str:
                return ErrorCode.CONFIG_INVALID_FORMAT
            return ErrorCode.CONFIG_PARSE_ERROR
        
        elif category == ErrorCategory.DEPENDENCY:
            if "not found" in error_str:
                return ErrorCode.DEPENDENCY_NOT_FOUND
            if "cycle" in error_str:
                return ErrorCode.DEPENDENCY_CYCLE_DETECTED
            return ErrorCode.DEPENDENCY_LOAD_FAILED
        
        elif category == ErrorCategory.VALIDATION:
            if "type" in error_str:
                return ErrorCode.VALIDATION_TYPE_ERROR
            if "range" in error_str:
                return ErrorCode.VALIDATION_RANGE_ERROR
            return ErrorCode.VALIDATION_FAILED
        
        return ErrorCode.UNKNOWN_ERROR
    
    def _determine_severity(self, exception: Exception) -> ErrorSeverity:
        """确定错误严重级别"""
        if isinstance(exception, (KeyboardInterrupt, SystemExit)):
            return ErrorSeverity.CRITICAL
        if isinstance(exception, MemoryError):
            return ErrorSeverity.CRITICAL
        if isinstance(exception, TimeoutError):
            return ErrorSeverity.WARNING
        return ErrorSeverity.ERROR


# ============================================================================
# 错误处理中间件
# ============================================================================

class ErrorHandlingMiddleware:
    """
    错误处理中间件
    
    功能：
    - 统一错误处理
    - 错误转换和增强
    - 错误日志记录
    - 错误统计和监控
    """
    
    def __init__(self, 
                 transformer: Optional[ErrorTransformer] = None,
                 log_errors: bool = True,
                 notify_callback: Optional[Callable[[UserFriendlyError], None]] = None):
        """
        初始化错误处理中间件
        
        Args:
            transformer: 错误转换器
            log_errors: 是否记录错误
            notify_callback: 错误通知回调
        """
        self.transformer = transformer or ErrorTransformer()
        self.log_errors = log_errors
        self.notify_callback = notify_callback
        
        # 错误统计
        self.stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "errors_by_code": {}
        }
        
        # 错误历史
        self.error_history: List[UserFriendlyError] = []
        self.max_history_size = 100
    
    async def handle(self, 
                    func: Callable,
                    *args,
                    default_message: Optional[str] = None,
                    context: Optional[Dict[str, Any]] = None,
                    **kwargs) -> Any:
        """
        执行函数并处理错误
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            default_message: 默认错误消息
            context: 错误上下文信息
            **kwargs: 函数关键字参数
        
        Returns:
            函数返回值
        
        Raises:
            UserFriendlyError: 处理后的友好错误
        """
        try:
            # 同步函数
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        except UserFriendlyError:
            # 已经是友好错误，直接重新抛出
            raise
        
        except Exception as e:
            # 转换异常
            friendly_error = self.transformer.transform(
                e,
                default_message=default_message,
                **(context or {})
            )
            
            # 更新统计
            self._update_stats(friendly_error)
            
            # 记录日志
            if self.log_errors:
                self._log_error(friendly_error)
            
            # 通知回调
            if self.notify_callback:
                try:
                    self.notify_callback(friendly_error)
                except Exception as notify_error:
                    logger.error(f"错误通知失败: {notify_error}")
            
            # 重新抛出友好错误
            raise friendly_error
    
    def _update_stats(self, error: UserFriendlyError) -> None:
        """更新错误统计"""
        self.stats["total_errors"] += 1
        
        # 按类别统计
        category = error.category.value
        self.stats["errors_by_category"][category] = \
            self.stats["errors_by_category"].get(category, 0) + 1
        
        # 按严重级别统计
        severity = error.severity.value
        self.stats["errors_by_severity"][severity] = \
            self.stats["errors_by_severity"].get(severity, 0) + 1
        
        # 按错误代码统计
        code = error.code.value
        self.stats["errors_by_code"][code] = \
            self.stats["errors_by_code"].get(code, 0) + 1
        
        # 添加到历史记录
        self.error_history.append(error)
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)
    
    def _log_error(self, error: UserFriendlyError) -> None:
        """记录错误日志"""
        log_level_map = {
            ErrorSeverity.DEBUG: logging.DEBUG,
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }
        
        log_level = log_level_map.get(error.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"[{error.code.value}] {error.category.value}: {error.message}",
            extra={
                "error_context": error.context.to_dict(),
                "error_suggestions": [s.message for s in error.suggestions]
            }
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return copy.deepcopy(self.stats)
    
    def get_recent_errors(self, limit: int = 10) -> List[UserFriendlyError]:
        """获取最近的错误"""
        return self.error_history[-limit:]
    
    def get_errors_by_category(self, category: ErrorCategory) -> List[UserFriendlyError]:
        """获取特定类别的错误"""
        return [e for e in self.error_history if e.category == category]
    
    def clear_history(self) -> None:
        """清除错误历史"""
        self.error_history.clear()


# ============================================================================
# 错误消息格式化器
# ============================================================================

class ErrorMessageFormatter:
    """
    错误消息格式化器
    
    支持多种输出格式：
    - 简单文本
    - JSON
    - ANSI彩色文本
    - HTML
    """
    
    @staticmethod
    def format_plain(error: UserFriendlyError) -> str:
        """格式化为纯文本"""
        lines = [
            f"Error [{error.code.value}]: {error.message}",
            f"Category: {error.category.value}",
            f"Severity: {error.severity.value}"
        ]
        
        if error.context.module:
            lines.append(f"Module: {error.context.module}")
        
        if error.context.function:
            lines.append(f"Function: {error.context.function}")
        
        if error.suggestions:
            lines.append("")
            lines.append("Suggestions:")
            for suggestion in error.suggestions:
                lines.append(f"  - {suggestion.message}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_json(error: UserFriendlyError, pretty: bool = False) -> str:
        """格式化为JSON"""
        indent = 2 if pretty else None
        return json.dumps(error.to_dict(), indent=indent, ensure_ascii=False)
    
    @staticmethod
    def format_ansi(error: UserFriendlyError) -> str:
        """格式化为ANSI彩色文本"""
        # ANSI颜色代码
        RESET = "\033[0m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        BLUE = "\033[94m"
        GREEN = "\033[92m"
        
        lines = [
            f"{RED}╔══════════════════════════════════════════════════════════════╗{RESET}",
            f"{RED}║{RESET} {RED}ERROR [{error.code.value}]{RESET}" + " " * (45 - len(str(error.code.value))) + f"{RED}║{RESET}",
            f"{RED}╚══════════════════════════════════════════════════════════════╝{RESET}",
            f"",
            f"{RED}❌ {error.message}{RESET}",
            f"",
            f"{BLUE}📂 Category:{RESET} {error.category.value}",
            f"{BLUE}⚠️  Severity:{RESET} {error.severity.value}"
        ]
        
        if error.context.module or error.context.function:
            location = []
            if error.context.module:
                location.append(error.context.module)
            if error.context.function:
                location.append(error.context.function)
            if error.context.line_number:
                location.append(f"line {error.context.line_number}")
            lines.append(f"{BLUE}📍 Location:{RESET} {'.'.join(location)}")
        
        if error.suggestions:
            lines.append("")
            lines.append(f"{GREEN}💡 Suggestions:{RESET}")
            for i, suggestion in enumerate(error.suggestions[:3], 1):
                lines.append(f"  {GREEN}{i}.{RESET} {suggestion.message}")
                if suggestion.action:
                    lines.append(f"     → {suggestion.action}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_html(error: UserFriendlyError) -> str:
        """格式化为HTML"""
        html = [
            '<div class="error-container">',
            f'  <div class="error-header">',
            f'    <span class="error-code">[{error.code.value}]</span>',
            f'    <span class="error-category">{error.category.value}</span>',
            f'  </div>',
            f'  <div class="error-message">{error.message}</div>'
        ]
        
        if error.suggestions:
            html.append('  <div class="error-suggestions">')
            html.append('    <h4>Suggestions:</h4>')
            html.append('    <ul>')
            for suggestion in error.suggestions:
                html.append(f'      <li><strong>{suggestion.message}</strong>')
                if suggestion.action:
                    html.append(f' → {suggestion.action}')
                html.append('      </li>')
            html.append('    </ul>')
            html.append('  </div>')
        
        html.append('</div>')
        return "\n".join(html)


# ============================================================================
# 错误构建器
# ============================================================================

class ErrorBuilder:
    """
    错误构建器 - 链式API创建友好错误
    """
    
    def __init__(self, message: str):
        self._message = message
        self._code = ErrorCode.UNKNOWN_ERROR
        self._category = ErrorCategory.UNKNOWN
        self._severity = ErrorSeverity.ERROR
        self._suggestions: List[ErrorSuggestion] = []
        self._context = ErrorContext()
        self._details: Dict[str, Any] = {}
    
    def with_code(self, code: ErrorCode) -> 'ErrorBuilder':
        """设置错误代码"""
        self._code = code
        return self
    
    def with_category(self, category: ErrorCategory) -> 'ErrorBuilder':
        """设置错误类别"""
        self._category = category
        return self
    
    def with_severity(self, severity: ErrorSeverity) -> 'ErrorBuilder':
        """设置严重级别"""
        self._severity = severity
        return self
    
    def with_suggestion(self, 
                       message: str, 
                       action: str,
                       priority: int = 1) -> 'ErrorBuilder':
        """添加建议"""
        self._suggestions.append(ErrorSuggestion(
            message=message,
            action=action,
            priority=priority
        ))
        return self
    
    def with_context(self, 
                   module: Optional[str] = None,
                   function: Optional[str] = None,
                   **kwargs) -> 'ErrorBuilder':
        """设置上下文"""
        if module:
            self._context.module = module
        if function:
            self._context.function = function
        for key, value in kwargs.items():
            if hasattr(self._context, key):
                setattr(self._context, key, value)
        return self
    
    def with_detail(self, key: str, value: Any) -> 'ErrorBuilder':
        """添加详情"""
        self._details[key] = value
        return self
    
    def build(self) -> UserFriendlyError:
        """构建错误对象"""
        return UserFriendlyError(
            message=self._message,
            code=self._code,
            category=self._category,
            severity=self._severity,
            suggestions=self._suggestions,
            context=self._context,
            **self._details
        )


# ============================================================================
# 测试套件
# ============================================================================

class TestErrorMessageOptimization:
    """错误信息优化测试套件"""
    
    @staticmethod
    def test_basic_error_creation() -> bool:
        """测试基本错误创建"""
        logger.info("开始测试基本错误创建")
        
        try:
            # 创建基本错误
            error = UserFriendlyError(
                message="测试错误",
                code=ErrorCode.UNKNOWN_ERROR,
                category=ErrorCategory.RUNTIME
            )
            
            assert error.message == "测试错误"
            assert error.code == ErrorCode.UNKNOWN_ERROR
            assert error.category == ErrorCategory.RUNTIME
            
            # 测试字符串表示
            assert str(error) == "[9001] 测试错误"
            
            # 测试字典转换
            error_dict = error.to_dict()
            assert "error" in error_dict
            assert error_dict["error"]["message"] == "测试错误"
            
            logger.info("基本错误创建测试通过")
            return True
            
        except Exception as e:
            logger.error(f"基本错误创建测试失败: {str(e)}")
            return False
    
    @staticmethod
    def test_specialized_errors() -> bool:
        """测试专用错误类"""
        logger.info("开始测试专用错误类")
        
        try:
            # 测试配置错误
            config_error = ConfigError(
                message="配置文件未找到",
                config_path="/path/to/config.yaml"
            )
            assert isinstance(config_error, UserFriendlyError)
            assert config_error.category == ErrorCategory.CONFIGURATION
            assert len(config_error.suggestions) > 0
            
            # 测试依赖错误
            dep_error = DependencyError(
                message="依赖加载失败",
                dependency_name="requests"
            )
            assert isinstance(dep_error, UserFriendlyError)
            assert dep_error.category == ErrorCategory.DEPENDENCY
            
            # 测试验证错误
            val_error = ValidationError(
                message="验证失败",
                field_name="username",
                expected_type="string"
            )
            assert isinstance(val_error, UserFriendlyError)
            assert val_error.category == ErrorCategory.VALIDATION
            
            # 测试网络错误
            net_error = NetworkError(
                message="连接失败",
                url="https://api.example.com",
                status_code=404
            )
            assert isinstance(net_error, UserFriendlyError)
            assert net_error.category == ErrorCategory.NETWORK
            
            logger.info("专用错误类测试通过")
            return True
            
        except Exception as e:
            logger.error(f"专用错误类测试失败: {str(e)}")
            return False
    
    @staticmethod
    def test_error_transformer() -> bool:
        """测试错误转换器"""
        logger.info("开始测试错误转换器")
        
        try:
            transformer = ErrorTransformer()
            
            # 测试ModuleNotFoundError转换
            original = ModuleNotFoundError("No module named 'requests'")
            friendly = transformer.transform(original)
            
            assert isinstance(friendly, UserFriendlyError)
            assert friendly.category == ErrorCategory.DEPENDENCY
            assert len(friendly.suggestions) > 0
            
            # 测试ValueError转换
            original2 = ValueError("invalid literal for int(): abc")
            friendly2 = transformer.transform(original2)
            
            assert isinstance(friendly2, UserFriendlyError)
            assert len(friendly2.suggestions) > 0
            
            # 测试FileNotFoundError转换
            original3 = FileNotFoundError("[Errno 2] No such file or directory: '/config.yaml'")
            friendly3 = transformer.transform(original3)
            
            assert isinstance(friendly3, UserFriendlyError)
            assert friendly3.category == ErrorCategory.CONFIGURATION
            
            logger.info("错误转换器测试通过")
            return True
            
        except Exception as e:
            logger.error(f"错误转换器测试失败: {str(e)}")
            return False
    
    @staticmethod
    def test_error_middleware() -> bool:
        """测试错误处理中间件"""
        logger.info("开始测试错误处理中间件")
        
        try:
            middleware = ErrorHandlingMiddleware()
            
            # 测试同步函数错误处理
            def failing_function():
                raise ValueError("test error")
            
            try:
                asyncio.run(middleware.handle(failing_function))
                assert False, "应该抛出错误"
            except UserFriendlyError as e:
                assert isinstance(e, UserFriendlyError)
                assert e.category == ErrorCategory.VALIDATION
            
            # 测试统计更新
            stats = middleware.get_stats()
            assert stats["total_errors"] > 0
            assert stats["errors_by_category"]["validation"] > 0
            
            logger.info("错误处理中间件测试通过")
            return True
            
        except Exception as e:
            logger.error(f"错误处理中间件测试失败: {str(e)}")
            return False
    
    @staticmethod
    def test_error_builder() -> bool:
        """测试错误构建器"""
        logger.info("开始测试错误构建器")
        
        try:
            # 链式构建错误
            error = (ErrorBuilder("配置加载失败")
                    .with_code(ErrorCode.CONFIG_NOT_FOUND)
                    .with_category(ErrorCategory.CONFIGURATION)
                    .with_severity(ErrorSeverity.ERROR)
                    .with_suggestion("检查配置文件路径", "确保文件存在且路径正确")
                    .with_context(module="config_loader", function="load_config")
                    .with_detail("file_path", "/config/app.yaml")
                    .build())
            
            assert error.message == "配置加载失败"
            assert error.code == ErrorCode.CONFIG_NOT_FOUND
            assert error.category == ErrorCategory.CONFIGURATION
            assert len(error.suggestions) == 1
            assert error.context.module == "config_loader"
            assert error.details["file_path"] == "/config/app.yaml"
            
            logger.info("错误构建器测试通过")
            return True
            
        except Exception as e:
            logger.error(f"错误构建器测试失败: {str(e)}")
            return False
    
    @staticmethod
    def test_error_formatters() -> bool:
        """测试错误格式化器"""
        logger.info("开始测试错误格式化器")
        
        try:
            error = UserFriendlyError(
                message="测试错误消息",
                code=ErrorCode.CONFIG_NOT_FOUND,
                category=ErrorCategory.CONFIGURATION,
                suggestions=[
                    ErrorSuggestion("建议1", "执行操作1"),
                    ErrorSuggestion("建议2", "执行操作2")
                ]
            )
            
            # 测试纯文本格式
            plain = ErrorMessageFormatter.format_plain(error)
            assert "ERROR [1001]" in plain
            assert "测试错误消息" in plain
            
            # 测试JSON格式
            json_str = ErrorMessageFormatter.format_json(error)
            assert "测试错误消息" in json_str
            
            # 测试字典转换
            error_dict = error.to_dict()
            assert error_dict["error"]["message"] == "测试错误消息"
            
            logger.info("错误格式化器测试通过")
            return True
            
        except Exception as e:
            logger.error(f"错误格式化器测试失败: {str(e)}")
            return False
    
    @staticmethod
    async def run_all_tests() -> Dict[str, bool]:
        """运行所有测试"""
        logger.info("开始运行错误信息优化测试套件")
        
        results = {
            "basic_error_creation": TestErrorMessageOptimization.test_basic_error_creation(),
            "specialized_errors": TestErrorMessageOptimization.test_specialized_errors(),
            "error_transformer": TestErrorMessageOptimization.test_error_transformer(),
            "error_middleware": TestErrorMessageOptimization.test_error_middleware(),
            "error_builder": TestErrorMessageOptimization.test_error_builder(),
            "error_formatters": TestErrorMessageOptimization.test_error_formatters()
        }
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        logger.info(f"测试套件完成: {passed}/{total} 通过")
        return results


# ============================================================================
# 演示函数
# ============================================================================

async def run_demo() -> None:
    """运行错误信息优化演示"""
    logger.info("开始错误信息优化演示")
    
    try:
        # 1. 演示基本错误创建
        logger.info("\n=== 1. 基本错误创建演示 ===")
        
        basic_error = UserFriendlyError(
            message="配置加载失败",
            code=ErrorCode.CONFIG_NOT_FOUND,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.ERROR
        )
        basic_error.add_suggestion(
            message="配置文件未找到",
            action="请检查配置文件路径是否正确",
            priority=1
        )
        
        print("\n--- 原始错误输出 ---")
        print(str(basic_error))
        
        print("\n--- 用户友好输出 ---")
        print(basic_error.to_user_string())
        
        print("\n--- JSON输出 ---")
        print(ErrorMessageFormatter.format_json(basic_error, pretty=True))
        
        # 2. 演示专用错误类
        logger.info("\n=== 2. 专用错误类演示 ===")
        
        config_error = ConfigError(
            message="配置文件格式错误",
            config_path="/app/config.yaml",
            config_value="{invalid json}"
        )
        
        print("\n--- ConfigError演示 ---")
        print(config_error.to_user_string())
        
        dep_error = DependencyError(
            message="循环依赖检测",
            dependency_name="service_a"
        )
        
        print("\n--- DependencyError演示 ---")
        print(dep_error.to_user_string())
        
        # 3. 演示错误转换
        logger.info("\n=== 3. 错误转换演示 ===")
        
        transformer = ErrorTransformer()
        
        # 模拟原始异常
        original_errors = [
            ModuleNotFoundError("No module named 'requests'"),
            ValueError("invalid literal for int(): abc"),
            FileNotFoundError("[Errno 2] No such file or directory: 'config.yaml'")
        ]
        
        for original in original_errors:
            print(f"\n--- 原始异常: {type(original).__name__} ---")
            print(f"原始消息: {str(original)}")
            
            friendly = transformer.transform(original)
            
            print(f"友好错误: {friendly.message}")
            print(f"类别: {friendly.category.value}")
            print(f"建议数量: {len(friendly.suggestions)}")
            if friendly.suggestions:
                print(f"第一条建议: {friendly.suggestions[0].message}")
        
        # 4. 演示错误处理中间件
        logger.info("\n=== 4. 错误处理中间件演示 ===")
        
        middleware = ErrorHandlingMiddleware()
        
        def failing_function():
            raise ImportError("No module named 'nonexistent_module'")
        
        try:
            await middleware.handle(failing_function, default_message="模块导入失败")
        except UserFriendlyError as e:
            print(f"\n--- 中间件捕获错误 ---")
            print(e.to_user_string())
        
        # 显示统计信息
        stats = middleware.get_stats()
        print(f"\n--- 错误统计 ---")
        print(f"总错误数: {stats['total_errors']}")
        print(f"按类别: {stats['errors_by_category']}")
        print(f"按严重级别: {stats['errors_by_severity']}")
        
        # 5. 演示错误构建器
        logger.info("\n=== 5. 错误构建器演示 ===")
        
        built_error = (ErrorBuilder("数据库连接失败")
                      .with_code(ErrorCode.DATABASE)
                      .with_category(ErrorCategory.DATABASE)
                      .with_severity(ErrorSeverity.ERROR)
                      .with_suggestion("检查数据库服务", "确保MySQL服务正在运行")
                      .with_suggestion("检查连接配置", "验证host、port、username、password")
                      .with_context(module="db_connector", function="connect")
                      .with_detail("host", "localhost")
                      .with_detail("port", 3306)
                      .build())
        
        print("\n--- 构建的错误 ---")
        print(built_error.to_user_string())
        
        logger.info("\n=== 演示完成 ===")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {str(e)}")
        raise


# ============================================================================
# 性能基准测试
# ============================================================================

async def run_benchmark() -> Dict[str, Any]:
    """运行性能基准测试"""
    logger.info("开始性能基准测试")
    
    results = {}
    
    try:
        # 1. 错误创建性能测试
        logger.info("1. 错误创建性能测试...")
        
        start = time.time()
        for i in range(1000):
            error = UserFriendlyError(
                message=f"测试错误 {i}",
                code=ErrorCode.UNKNOWN_ERROR,
                category=ErrorCategory.RUNTIME
            )
        duration = (time.time() - start) * 1000
        results["error_creation"] = {
            "iterations": 1000,
            "total_ms": duration,
            "avg_ms": duration / 1000
        }
        
        # 2. 错误转换性能测试
        logger.info("2. 错误转换性能测试...")
        
        transformer = ErrorTransformer()
        test_exceptions = [
            ModuleNotFoundError("No module named 'test'"),
            ValueError("invalid value"),
            FileNotFoundError("file not found")
        ]
        
        start = time.time()
        for i in range(500):
            for exc in test_exceptions:
                transformer.transform(exc)
        duration = (time.time() - start) * 1000
        results["error_transformation"] = {
            "iterations": 1500,
            "total_ms": duration,
            "avg_ms": duration / 1500
        }
        
        # 3. 错误格式化性能测试
        logger.info("3. 错误格式化性能测试...")
        
        error = UserFriendlyError(
            message="测试错误",
            code=ErrorCode.CONFIG_NOT_FOUND,
            category=ErrorCategory.CONFIGURATION,
            suggestions=[
                ErrorSuggestion("建议1", "操作1"),
                ErrorSuggestion("建议2", "操作2")
            ]
        )
        
        start = time.time()
        for i in range(1000):
            ErrorMessageFormatter.format_plain(error)
            ErrorMessageFormatter.format_json(error)
        duration = (time.time() - start) * 1000
        results["error_formatting"] = {
            "iterations": 2000,
            "total_ms": duration,
            "avg_ms": duration / 2000
        }
        
        # 4. 中间件性能测试
        logger.info("4. 中间件性能测试...")
        
        middleware = ErrorHandlingMiddleware()
        
        def simple_func():
            return "success"
        
        async def async_func():
            return "success"
        
        async def error_func():
            raise ValueError("test")
        
        start = time.time()
        for i in range(500):
            await middleware.handle(simple_func)
        duration = (time.time() - start) * 1000
        results["middleware_success"] = {
            "iterations": 500,
            "total_ms": duration,
            "avg_ms": duration / 500
        }
        
        start = time.time()
        for i in range(500):
            try:
                await middleware.handle(error_func)
            except UserFriendlyError:
                pass
        duration = (time.time() - start) * 1000
        results["middleware_error"] = {
            "iterations": 500,
            "total_ms": duration,
            "avg_ms": duration / 500
        }
        
        logger.info("性能基准测试完成")
        
        # 打印结果
        logger.info("\n性能基准测试结果:")
        for test_name, result in results.items():
            logger.info(f"  {test_name}: {result['avg_ms']:.4f}ms/次")
        
        return results
        
    except Exception as e:
        logger.error(f"性能基准测试失败: {str(e)}")
        raise


# ============================================================================
# 主函数
# ============================================================================

async def main() -> None:
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="错误信息优化演示程序")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--bench", action="store_true", help="运行性能基准测试")
    
    args = parser.parse_args()
    
    # 默认运行演示
    if not any([args.test, args.demo, args.bench]):
        args.demo = True
    
    try:
        if args.test:
            logger.info("运行测试套件...")
            results = await TestErrorMessageOptimization.run_all_tests()
            
            # 检查结果
            all_passed = all(results.values())
            if all_passed:
                logger.info("✅ 所有测试通过!")
                return 0
            else:
                logger.error("❌ 部分测试失败:")
                for test_name, passed in results.items():
                    status = "✅" if passed else "❌"
                    logger.error(f"  {status} {test_name}")
                return 1
        
        if args.demo:
            logger.info("运行演示...")
            await run_demo()
            logger.info("✅ 演示完成!")
            return 0
        
        if args.bench:
            logger.info("运行性能基准测试...")
            results = await run_benchmark()
            logger.info("✅ 性能基准测试完成!")
            return 0
    
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        return 130
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容）
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 运行主函数
    exit_code = asyncio.run(main())
    sys.exit(exit_code)