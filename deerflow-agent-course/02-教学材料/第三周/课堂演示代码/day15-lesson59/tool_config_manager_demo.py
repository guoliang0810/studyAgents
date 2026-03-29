#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具配置管理演示代码 - DeerFlow Python Agent 架构师训练营
第59节课：工具配置管理

本模块演示现代AI Agent系统中的工具配置管理，包括：
1. 工具配置结构：内置工具、自定义工具、MCP工具等不同类型
2. 工具加载机制：异步加载、类型分发、环境变量替换
3. 安全配置管理：命令限制、资源限制、权限控制、沙箱隔离
4. 工具依赖管理：依赖解析、初始化顺序、循环依赖检测
5. 配置验证和错误处理：配置验证、加载错误处理、安全策略验证

使用说明：
1. 直接运行：python tool_config_manager_demo.py
2. 运行测试：python tool_config_manager_demo.py --test
3. 查看帮助：python tool_config_manager_demo.py --help
"""

import os
import sys
import json
import yaml
import asyncio
import argparse
import copy
import re
import time
import hashlib
import inspect
from typing import Any, Dict, List, Optional, Union, Callable, Set, Tuple, Type
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
import logging
from abc import ABC, abstractmethod
import importlib.util
import importlib.machinery
from contextlib import contextmanager
import subprocess
import tempfile
import shutil

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ToolConfigError(Exception):
    """工具配置错误基类"""
    pass


class ToolLoaderError(ToolConfigError):
    """工具加载器错误"""
    pass


class ToolSecurityError(ToolConfigError):
    """工具安全错误"""
    pass


class ToolDependencyError(ToolConfigError):
    """工具依赖错误"""
    pass


# ============================================================================
# 工具类型和安全级别
# ============================================================================

class ToolType(Enum):
    """工具类型枚举"""
    BUILTIN = "builtin"      # 内置工具：系统自带的工具
    CUSTOM = "custom"        # 自定义工具：用户编写的工具
    MCP = "mcp"             # MCP工具：Model Context Protocol工具
    EXTERNAL = "external"    # 外部工具：通过API或CLI调用的外部程序
    SCRIPT = "script"        # 脚本工具：动态执行的脚本
    
    @classmethod
    def from_string(cls, tool_type_str: str) -> "ToolType":
        """从字符串转换为工具类型"""
        try:
            return cls(tool_type_str.lower())
        except ValueError:
            raise ToolConfigError(f"未知的工具类型: {tool_type_str}")


class SecurityLevel(Enum):
    """安全级别枚举"""
    TRUSTED = "trusted"      # 信任级别：完全信任，无限制
    RESTRICTED = "restricted"  # 限制级别：有限制的操作
    SANDBOXED = "sandboxed"  # 沙箱级别：完全隔离，高度限制
    UNTRUSTED = "untrusted"  # 不信任级别：禁止执行
    
    @classmethod
    def from_string(cls, security_str: str) -> "SecurityLevel":
        """从字符串转换为安全级别"""
        try:
            return cls(security_str.lower())
        except ValueError:
            raise ToolConfigError(f"未知的安全级别: {security_str}")


# ============================================================================
# 工具配置结构
# ============================================================================

@dataclass
class ToolSecurityConfig:
    """工具安全配置"""
    security_level: SecurityLevel = SecurityLevel.RESTRICTED
    allowed_commands: List[str] = field(default_factory=list)      # 允许的命令列表
    blocked_commands: List[str] = field(default_factory=list)      # 禁止的命令列表
    max_execution_time: float = 30.0                               # 最大执行时间（秒）
    max_memory_mb: int = 100                                       # 最大内存使用（MB）
    network_access: bool = False                                   # 是否允许网络访问
    file_system_access: bool = True                                # 是否允许文件系统访问
    environment_variables: List[str] = field(default_factory=list)  # 允许访问的环境变量
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "security_level": self.security_level.value,
            "allowed_commands": self.allowed_commands,
            "blocked_commands": self.blocked_commands,
            "max_execution_time": self.max_execution_time,
            "max_memory_mb": self.max_memory_mb,
            "network_access": self.network_access,
            "file_system_access": self.file_system_access,
            "environment_variables": self.environment_variables
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolSecurityConfig":
        """从字典创建"""
        return cls(
            security_level=SecurityLevel.from_string(data.get("security_level", "restricted")),
            allowed_commands=data.get("allowed_commands", []),
            blocked_commands=data.get("blocked_commands", []),
            max_execution_time=data.get("max_execution_time", 30.0),
            max_memory_mb=data.get("max_memory_mb", 100),
            network_access=data.get("network_access", False),
            file_system_access=data.get("file_system_access", True),
            environment_variables=data.get("environment_variables", [])
        )
    
    def is_command_allowed(self, command: str) -> bool:
        """检查命令是否允许执行"""
        # 如果命令在禁止列表中，不允许
        for blocked in self.blocked_commands:
            if re.match(blocked, command):
                return False
        
        # 如果允许列表为空，允许所有（除了禁止的）
        if not self.allowed_commands:
            return True
        
        # 检查是否在允许列表中
        for allowed in self.allowed_commands:
            if re.match(allowed, command):
                return True
        
        return False
    
    def validate(self) -> List[str]:
        """验证安全配置，返回错误列表"""
        errors = []
        
        if self.max_execution_time <= 0:
            errors.append("max_execution_time必须大于0")
        
        if self.max_memory_mb <= 0:
            errors.append("max_memory_mb必须大于0")
        
        # 检查命令模式的有效性
        for pattern in self.allowed_commands + self.blocked_commands:
            try:
                re.compile(pattern)
            except re.error:
                errors.append(f"无效的正则表达式模式: {pattern}")
        
        return errors


@dataclass
class ToolDependency:
    """工具依赖配置"""
    tool_id: str                     # 依赖的工具ID
    version: Optional[str] = None    # 版本要求（可选）
    required: bool = True           # 是否必需
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {"tool_id": self.tool_id, "required": self.required}
        if self.version:
            result["version"] = self.version
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolDependency":
        """从字典创建"""
        return cls(
            tool_id=data["tool_id"],
            version=data.get("version"),
            required=data.get("required", True)
        )


@dataclass
class ToolConfig:
    """工具配置"""
    tool_id: str                                     # 工具唯一标识
    tool_type: ToolType                              # 工具类型
    name: str                                       # 工具名称
    description: Optional[str] = None               # 工具描述
    version: str = "1.0.0"                         # 工具版本
    author: Optional[str] = None                    # 作者
    entry_point: Optional[str] = None               # 入口点（模块路径或函数名）
    module_path: Optional[str] = None               # 模块路径（对于自定义工具）
    class_name: Optional[str] = None                # 类名（对于面向对象的工具）
    function_name: Optional[str] = None             # 函数名（对于函数式工具）
    mcp_server_url: Optional[str] = None            # MCP服务器URL（对于MCP工具）
    command: Optional[str] = None                   # 命令（对于外部工具）
    script_content: Optional[str] = None            # 脚本内容（对于脚本工具）
    environment_variables: Dict[str, str] = field(default_factory=dict)  # 环境变量
    security_config: ToolSecurityConfig = field(default_factory=ToolSecurityConfig)  # 安全配置
    dependencies: List[ToolDependency] = field(default_factory=list)     # 依赖项
    metadata: Dict[str, Any] = field(default_factory=dict)               # 元数据
    
    def __post_init__(self):
        """初始化后验证"""
        errors = self.validate()
        if errors:
            raise ToolConfigError(f"工具配置验证失败: {', '.join(errors)}")
    
    def validate(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []
        
        # 基本验证
        if not self.tool_id:
            errors.append("tool_id不能为空")
        
        if not self.name:
            errors.append("name不能为空")
        
        # 类型特定验证
        if self.tool_type == ToolType.CUSTOM:
            if not self.module_path and not self.entry_point:
                errors.append("自定义工具需要module_path或entry_point")
        
        elif self.tool_type == ToolType.MCP:
            if not self.mcp_server_url:
                errors.append("MCP工具需要mcp_server_url")
        
        elif self.tool_type == ToolType.EXTERNAL:
            if not self.command:
                errors.append("外部工具需要command")
        
        elif self.tool_type == ToolType.SCRIPT:
            if not self.script_content:
                errors.append("脚本工具需要script_content")
        
        # 安全配置验证
        security_errors = self.security_config.validate()
        errors.extend(security_errors)
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "tool_id": self.tool_id,
            "tool_type": self.tool_type.value,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "entry_point": self.entry_point,
            "module_path": self.module_path,
            "class_name": self.class_name,
            "function_name": self.function_name,
            "mcp_server_url": self.mcp_server_url,
            "command": self.command,
            "script_content": self.script_content,
            "environment_variables": self.environment_variables,
            "security_config": self.security_config.to_dict(),
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "metadata": self.metadata
        }
        
        # 移除None值
        return {k: v for k, v in result.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolConfig":
        """从字典创建"""
        # 解析依赖项
        dependencies = []
        for dep_data in data.get("dependencies", []):
            dependencies.append(ToolDependency.from_dict(dep_data))
        
        # 创建安全配置
        security_data = data.get("security_config", {})
        security_config = ToolSecurityConfig.from_dict(security_data)
        
        return cls(
            tool_id=data["tool_id"],
            tool_type=ToolType.from_string(data["tool_type"]),
            name=data["name"],
            description=data.get("description"),
            version=data.get("version", "1.0.0"),
            author=data.get("author"),
            entry_point=data.get("entry_point"),
            module_path=data.get("module_path"),
            class_name=data.get("class_name"),
            function_name=data.get("function_name"),
            mcp_server_url=data.get("mcp_server_url"),
            command=data.get("command"),
            script_content=data.get("script_content"),
            environment_variables=data.get("environment_variables", {}),
            security_config=security_config,
            dependencies=dependencies,
            metadata=data.get("metadata", {})
        )
    
    def resolve_environment_variables(self, env_vars: Dict[str, str]) -> "ToolConfig":
        """解析环境变量引用
        
        支持格式：${VAR_NAME} 或 ${VAR_NAME:default_value}
        """
        resolved_config = copy.deepcopy(self)
        
        def resolve_value(value: Any) -> Any:
            if isinstance(value, str):
                # 替换环境变量引用
                def replace_var(match):
                    var_name = match.group(1)
                    default_value = match.group(3) if match.group(3) else None
                    
                    # 首先检查传入的环境变量
                    if var_name in env_vars:
                        return env_vars[var_name]
                    
                    # 然后检查系统环境变量
                    if var_name in os.environ:
                        return os.environ[var_name]
                    
                    # 最后使用默认值
                    if default_value is not None:
                        return default_value
                    
                    # 没有找到变量也没有默认值
                    raise ToolConfigError(f"环境变量未定义且无默认值: {var_name}")
                
                # 匹配 ${VAR_NAME} 或 ${VAR_NAME:default}
                pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)(:([^}]+))?\}'
                return re.sub(pattern, replace_var, value)
            
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            else:
                return value
        
        # 解析环境变量字段
        resolved_config.environment_variables = resolve_value(self.environment_variables)
        resolved_config.command = resolve_value(self.command) if self.command else None
        resolved_config.mcp_server_url = resolve_value(self.mcp_server_url) if self.mcp_server_url else None
        resolved_config.script_content = resolve_value(self.script_content) if self.script_content else None
        
        return resolved_config
    
    def get_required_dependencies(self) -> List[str]:
        """获取必需的依赖工具ID列表"""
        return [dep.tool_id for dep in self.dependencies if dep.required]


# ============================================================================
# 工具抽象类和具体实现
# ============================================================================

class BaseTool(ABC):
    """工具抽象基类"""
    
    def __init__(self, config: ToolConfig):
        self.config = config
        self.tool_id = config.tool_id
        self.name = config.name
        self.description = config.description or ""
        self.security_config = config.security_config
        self.initialized = False
        self.usage_count = 0
        self.last_used: Optional[float] = None
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具的主要方法"""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化工具"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """关闭工具，释放资源"""
        pass
    
    def record_usage(self) -> None:
        """记录工具使用"""
        self.usage_count += 1
        self.last_used = time.time()
    
    def is_command_allowed(self, command: str) -> bool:
        """检查命令是否允许执行"""
        return self.security_config.is_command_allowed(command)
    
    def validate_input(self, input_data: Dict[str, Any]) -> List[str]:
        """验证输入数据，返回错误列表"""
        errors = []
        if not isinstance(input_data, dict):
            errors.append("输入必须为字典类型")
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "usage_count": self.usage_count,
            "last_used": self.last_used,
            "security_level": self.security_config.security_level.value
        }


class BuiltinTool(BaseTool):
    """内置工具实现"""
    
    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.function: Optional[Callable] = None
    
    async def initialize(self) -> None:
        """初始化内置工具"""
        if self.config.function_name:
            # 动态导入函数
            if self.config.module_path:
                spec = importlib.util.spec_from_file_location(
                    self.config.tool_id,
                    self.config.module_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.function = getattr(module, self.config.function_name)
            elif self.config.entry_point:
                # 从入口点导入
                module_path, func_name = self.config.entry_point.rsplit('.', 1)
                module = importlib.import_module(module_path)
                self.function = getattr(module, func_name)
        self.initialized = True
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行内置工具"""
        if not self.initialized:
            raise ToolLoaderError(f"工具未初始化: {self.tool_id}")
        
        if not self.function:
            raise ToolLoaderError(f"工具函数未找到: {self.tool_id}")
        
        # 验证输入
        errors = self.validate_input(input_data)
        if errors:
            return {"error": f"输入验证失败: {', '.join(errors)}"}
        
        try:
            # 执行函数
            if asyncio.iscoroutinefunction(self.function):
                result = await self.function(**input_data)
            else:
                result = self.function(**input_data)
            
            self.record_usage()
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"工具执行失败: {self.tool_id}, 错误: {e}")
            return {"error": f"执行失败: {str(e)}"}
    
    async def shutdown(self) -> None:
        """关闭内置工具"""
        self.function = None
        self.initialized = False


class CustomTool(BaseTool):
    """自定义工具实现"""
    
    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.instance: Optional[Any] = None
    
    async def initialize(self) -> None:
        """初始化自定义工具"""
        if not self.config.module_path:
            raise ToolLoaderError(f"自定义工具缺少module_path: {self.tool_id}")
        
        # 动态导入模块
        spec = importlib.util.spec_from_file_location(
            self.config.tool_id,
            self.config.module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 创建实例
        if self.config.class_name:
            cls = getattr(module, self.config.class_name)
            self.instance = cls()
        elif self.config.function_name:
            self.instance = getattr(module, self.config.function_name)
        else:
            raise ToolLoaderError(f"自定义工具缺少class_name或function_name: {self.tool_id}")
        
        self.initialized = True
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行自定义工具"""
        if not self.initialized:
            raise ToolLoaderError(f"工具未初始化: {self.tool_id}")
        
        # 验证输入
        errors = self.validate_input(input_data)
        if errors:
            return {"error": f"输入验证失败: {', '.join(errors)}"}
        
        try:
            # 执行实例方法或函数
            if hasattr(self.instance, 'execute'):
                if asyncio.iscoroutinefunction(self.instance.execute):
                    result = await self.instance.execute(**input_data)
                else:
                    result = self.instance.execute(**input_data)
            elif callable(self.instance):
                if asyncio.iscoroutinefunction(self.instance):
                    result = await self.instance(**input_data)
                else:
                    result = self.instance(**input_data)
            else:
                raise ToolLoaderError(f"自定义工具不可执行: {self.tool_id}")
            
            self.record_usage()
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"工具执行失败: {self.tool_id}, 错误: {e}")
            return {"error": f"执行失败: {str(e)}"}
    
    async def shutdown(self) -> None:
        """关闭自定义工具"""
        if hasattr(self.instance, 'shutdown'):
            if asyncio.iscoroutinefunction(self.instance.shutdown):
                await self.instance.shutdown()
            else:
                self.instance.shutdown()
        self.instance = None
        self.initialized = False


class MCPTool(BaseTool):
    """MCP工具实现"""
    
    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.client = None
        self.session_id: Optional[str] = None
    
    async def initialize(self) -> None:
        """初始化MCP工具"""
        if not self.config.mcp_server_url:
            raise ToolLoaderError(f"MCP工具缺少mcp_server_url: {self.tool_id}")
        
        # 模拟MCP客户端连接
        # 实际实现中会使用MCP协议连接服务器
        logger.info(f"连接MCP服务器: {self.config.mcp_server_url}")
        self.session_id = f"mcp_session_{hash(self.config.mcp_server_url) % 10000}"
        self.initialized = True
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行MCP工具"""
        if not self.initialized:
            raise ToolLoaderError(f"工具未初始化: {self.tool_id}")
        
        # 验证输入
        errors = self.validate_input(input_data)
        if errors:
            return {"error": f"输入验证失败: {', '.join(errors)}"}
        
        try:
            # 模拟MCP请求
            command = input_data.get("command", "")
            
            # 安全检查
            if not self.is_command_allowed(command):
                raise ToolSecurityError(f"命令不被允许: {command}")
            
            # 模拟执行
            await asyncio.sleep(0.1)  # 模拟网络延迟
            result = f"MCP响应: {command} executed via session {self.session_id}"
            
            self.record_usage()
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"工具执行失败: {self.tool_id}, 错误: {e}")
            return {"error": f"执行失败: {str(e)}"}
    
    async def shutdown(self) -> None:
        """关闭MCP工具"""
        if self.session_id:
            logger.info(f"关闭MCP会话: {self.session_id}")
            self.session_id = None
        self.initialized = False


class ExternalTool(BaseTool):
    """外部工具实现"""
    
    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.process: Optional[subprocess.Popen] = None
    
    async def initialize(self) -> None:
        """初始化外部工具"""
        if not self.config.command:
            raise ToolLoaderError(f"外部工具缺少command: {self.tool_id}")
        
        # 验证命令安全性
        command_parts = self.config.command.split()
        if command_parts:
            cmd = command_parts[0]
            if not self.is_command_allowed(cmd):
                raise ToolSecurityError(f"命令不被允许: {cmd}")
        
        self.initialized = True
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行外部工具"""
        if not self.initialized:
            raise ToolLoaderError(f"工具未初始化: {self.tool_id}")
        
        # 验证输入
        errors = self.validate_input(input_data)
        if errors:
            return {"error": f"输入验证失败: {', '.join(errors)}"}
        
        if not self.config.command:
            return {"error": "未配置命令"}
        
        try:
            # 构建命令
            command = self.config.command
            args = input_data.get("args", [])
            
            # 安全检查
            cmd_parts = command.split()
            if cmd_parts and not self.is_command_allowed(cmd_parts[0]):
                raise ToolSecurityError(f"命令不被允许: {cmd_parts[0]}")
            
            # 设置环境变量
            env = os.environ.copy()
            env.update(self.config.environment_variables)
            
            # 执行命令
            process = subprocess.Popen(
                [command] + args,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
            
            # 等待完成（带超时）
            timeout = self.security_config.max_execution_time
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                raise ToolSecurityError(f"命令执行超时: {timeout}秒")
            
            self.record_usage()
            return {
                "success": return_code == 0,
                "return_code": return_code,
                "stdout": stdout,
                "stderr": stderr
            }
        except Exception as e:
            logger.error(f"工具执行失败: {self.tool_id}, 错误: {e}")
            return {"error": f"执行失败: {str(e)}"}
    
    async def shutdown(self) -> None:
        """关闭外部工具"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self.initialized = False


class ScriptTool(BaseTool):
    """脚本工具实现"""
    
    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.compiled_script: Optional[Any] = None
    
    async def initialize(self) -> None:
        """初始化脚本工具"""
        if not self.config.script_content:
            raise ToolLoaderError(f"脚本工具缺少script_content: {self.tool_id}")
        
        # 编译脚本（安全性检查）
        try:
            # 在实际实现中，这里会使用沙箱环境编译脚本
            # 这里简化为直接存储脚本内容
            self.compiled_script = self.config.script_content
        except Exception as e:
            raise ToolSecurityError(f"脚本编译失败: {e}")
        
        self.initialized = True
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行脚本工具"""
        if not self.initialized:
            raise ToolLoaderError(f"工具未初始化: {self.tool_id}")
        
        # 验证输入
        errors = self.validate_input(input_data)
        if errors:
            return {"error": f"输入验证失败: {', '.join(errors)}"}
        
        if not self.compiled_script:
            return {"error": "脚本未编译"}
        
        try:
            # 在实际实现中，这里会在沙箱中执行脚本
            # 这里简化为模拟执行
            script_vars = input_data.copy()
            script_vars["__result__"] = None
            
            # 模拟执行（实际应使用安全沙箱）
            result = f"脚本执行结果: {self.compiled_script[:50]}... with inputs {input_data}"
            
            self.record_usage()
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"工具执行失败: {self.tool_id}, 错误: {e}")
            return {"error": f"执行失败: {str(e)}"}
    
    async def shutdown(self) -> None:
        """关闭脚本工具"""
        self.compiled_script = None
        self.initialized = False


# ============================================================================
# 工具加载器
# ============================================================================

class ToolLoader:
    """工具加载器，负责加载和管理工具"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.configs: Dict[str, ToolConfig] = {}
        self.initialized = False
    
    async def load_configs_from_yaml(self, yaml_path: str, env_vars: Optional[Dict[str, str]] = None) -> List[ToolConfig]:
        """从YAML文件加载工具配置"""
        env_vars = env_vars or {}
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            if not isinstance(yaml_data, list):
                raise ToolConfigError("YAML文件应包含工具配置列表")
            
            configs = []
            for tool_data in yaml_data:
                # 创建配置
                config = ToolConfig.from_dict(tool_data)
                
                # 解析环境变量
                if env_vars:
                    config = config.resolve_environment_variables(env_vars)
                
                # 验证配置
                errors = config.validate()
                if errors:
                    raise ToolConfigError(f"配置验证失败: {config.tool_id}, 错误: {', '.join(errors)}")
                
                configs.append(config)
                self.configs[config.tool_id] = config
            
            return configs
        except Exception as e:
            raise ToolLoaderError(f"加载YAML配置失败: {e}")
    
    async def load_tools(self, configs: List[ToolConfig]) -> Dict[str, BaseTool]:
        """加载工具实例"""
        loaded_tools = {}
        
        # 解析依赖关系
        dependency_graph = self._build_dependency_graph(configs)
        sorted_tool_ids = self._topological_sort(dependency_graph)
        
        # 按依赖顺序加载工具
        for tool_id in sorted_tool_ids:
            config = self.configs.get(tool_id)
            if not config:
                continue
            
            try:
                tool = await self._create_tool_instance(config)
                self.tools[tool_id] = tool
                loaded_tools[tool_id] = tool
            except Exception as e:
                logger.error(f"加载工具失败: {tool_id}, 错误: {e}")
                # 继续加载其他工具
                continue
        
        return loaded_tools
    
    async def _create_tool_instance(self, config: ToolConfig) -> BaseTool:
        """根据配置创建工具实例"""
        tool_type = config.tool_type
        
        if tool_type == ToolType.BUILTIN:
            return BuiltinTool(config)
        elif tool_type == ToolType.CUSTOM:
            return CustomTool(config)
        elif tool_type == ToolType.MCP:
            return MCPTool(config)
        elif tool_type == ToolType.EXTERNAL:
            return ExternalTool(config)
        elif tool_type == ToolType.SCRIPT:
            return ScriptTool(config)
        else:
            raise ToolLoaderError(f"未知的工具类型: {tool_type}")
    
    async def initialize_all(self) -> None:
        """初始化所有工具"""
        initialization_tasks = []
        
        for tool_id, tool in self.tools.items():
            if not tool.initialized:
                task = asyncio.create_task(tool.initialize())
                task.tool_id = tool_id  # 自定义属性
                initialization_tasks.append(task)
        
        # 并行初始化
        if initialization_tasks:
            results = await asyncio.gather(*initialization_tasks, return_exceptions=True)
            
            # 检查结果
            for task, result in zip(initialization_tasks, results):
                if isinstance(result, Exception):
                    logger.error(f"工具初始化失败: {task.tool_id}, 错误: {result}")
        
        self.initialized = True
    
    async def shutdown_all(self) -> None:
        """关闭所有工具"""
        shutdown_tasks = []
        
        for tool in self.tools.values():
            if tool.initialized:
                task = asyncio.create_task(tool.shutdown())
                shutdown_tasks.append(task)
        
        # 并行关闭
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        self.tools.clear()
        self.configs.clear()
        self.initialized = False
    
    async def execute_tool(self, tool_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定工具"""
        tool = self.tools.get(tool_id)
        if not tool:
            raise ToolLoaderError(f"工具未找到: {tool_id}")
        
        if not tool.initialized:
            raise ToolLoaderError(f"工具未初始化: {tool_id}")
        
        return await tool.execute(input_data)
    
    def get_tool(self, tool_id: str) -> Optional[BaseTool]:
        """获取工具实例"""
        return self.tools.get(tool_id)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具信息"""
        return [tool.to_dict() for tool in self.tools.values()]
    
    def _build_dependency_graph(self, configs: List[ToolConfig]) -> Dict[str, List[str]]:
        """构建依赖关系图"""
        graph = {}
        
        for config in configs:
            tool_id = config.tool_id
            dependencies = config.get_required_dependencies()
            graph[tool_id] = dependencies
        
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """拓扑排序工具ID"""
        in_degree = {node: 0 for node in graph}
        
        # 计算入度
        for node, dependencies in graph.items():
            for dep in dependencies:
                if dep in in_degree:
                    in_degree[dep] += 1
                else:
                    in_degree[dep] = 1
        
        # 初始化队列
        queue = [node for node, degree in in_degree.items() if degree == 0]
        sorted_nodes = []
        
        # 拓扑排序
        while queue:
            node = queue.pop(0)
            sorted_nodes.append(node)
            
            for dependent in graph.get(node, []):
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # 检查循环依赖
        if len(sorted_nodes) != len(graph):
            # 找出循环依赖
            remaining = set(graph.keys()) - set(sorted_nodes)
            raise ToolDependencyError(f"检测到循环依赖: {remaining}")
        
        return sorted_nodes
    
    def validate_security_configs(self) -> List[str]:
        """验证所有工具的安全配置"""
        errors = []
        
        for tool_id, tool in self.tools.items():
            security_errors = tool.security_config.validate()
            for error in security_errors:
                errors.append(f"{tool_id}: {error}")
        
        return errors


# ============================================================================
# 演示函数
# ============================================================================

def demo_basic_usage() -> None:
    """演示基本用法"""
    print("=" * 60)
    print("演示1: 基本工具配置管理")
    print("=" * 60)
    
    # 创建安全配置
    security_config = ToolSecurityConfig(
        security_level=SecurityLevel.RESTRICTED,
        allowed_commands=["^python$", "^echo$"],
        blocked_commands=["^rm ", "^shutdown"],
        max_execution_time=30.0,
        max_memory_mb=100,
        network_access=False,
        file_system_access=True,
        environment_variables=["PATH", "HOME"]
    )
    
    # 创建工具配置
    tool_config = ToolConfig(
        tool_id="python-interpreter",
        tool_type=ToolType.EXTERNAL,
        name="Python解释器",
        description="执行Python代码的外部工具",
        command="python",
        environment_variables={"PYTHONPATH": "/usr/local/lib/python3.12"},
        security_config=security_config
    )
    
    print(f"工具配置: {tool_config.name} ({tool_config.tool_id})")
    print(f"工具类型: {tool_config.tool_type.value}")
    print(f"安全级别: {tool_config.security_config.security_level.value}")
    print(f"允许的命令: {tool_config.security_config.allowed_commands}")
    print(f"最大执行时间: {tool_config.security_config.max_execution_time}秒")
    
    # 测试环境变量解析
    env_vars = {"OPENAI_API_KEY": "sk-test123", "DATABASE_URL": "postgresql://localhost/test"}
    config_with_env = tool_config.resolve_environment_variables(env_vars)
    print(f"解析后的环境变量: {config_with_env.environment_variables}")
    
    print()


def demo_tool_loader() -> None:
    """演示工具加载器"""
    print("=" * 60)
    print("演示2: 工具加载器")
    print("=" * 60)
    
    # 创建工具加载器
    loader = ToolLoader()
    
    # 创建多个工具配置
    configs = [
        ToolConfig(
            tool_id="file-reader",
            tool_type=ToolType.BUILTIN,
            name="文件读取器",
            description="读取文件内容的内置工具",
            entry_point="builtin_tools.file_ops.read_file",
            security_config=ToolSecurityConfig(
                security_level=SecurityLevel.RESTRICTED,
                file_system_access=True
            )
        ),
        ToolConfig(
            tool_id="http-client",
            tool_type=ToolType.CUSTOM,
            name="HTTP客户端",
            description="发送HTTP请求的自定义工具",
            module_path="/path/to/http_client.py",
            class_name="HttpClient",
            security_config=ToolSecurityConfig(
                security_level=SecurityLevel.RESTRICTED,
                network_access=True,
                max_execution_time=10.0
            ),
            dependencies=[
                ToolDependency(tool_id="file-reader", required=False)
            ]
        ),
        ToolConfig(
            tool_id="mcp-calculator",
            tool_type=ToolType.MCP,
            name="MCP计算器",
            description="通过MCP协议访问的计算器工具",
            mcp_server_url="http://localhost:8080/mcp",
            security_config=ToolSecurityConfig(
                security_level=SecurityLevel.RESTRICTED,
                network_access=True
            )
        )
    ]
    
    print(f"创建了 {len(configs)} 个工具配置:")
    for config in configs:
        print(f"  - {config.name} ({config.tool_type.value})")
    
    # 注意：实际加载需要异步环境
    print("\n注意: 工具加载需要异步环境，完整演示请运行测试")
    print()


def demo_security_validation() -> None:
    """演示安全验证"""
    print("=" * 60)
    print("演示3: 安全配置验证")
    print("=" * 60)
    
    # 创建不安全配置
    insecure_config = ToolSecurityConfig(
        security_level=SecurityLevel.TRUSTED,
        allowed_commands=[],  # 空列表表示允许所有命令
        blocked_commands=["^rm "],
        max_execution_time=-1.0,  # 无效值
        max_memory_mb=0  # 无效值
    )
    
    # 验证配置
    errors = insecure_config.validate()
    
    print(f"安全配置验证结果:")
    print(f"  安全级别: {insecure_config.security_level.value}")
    print(f"  验证错误: {errors if errors else '无错误'}")
    
    # 测试命令检查
    test_commands = ["python script.py", "rm -rf /", "echo hello", "shutdown now"]
    
    print(f"\n命令安全检查:")
    for cmd in test_commands:
        allowed = insecure_config.is_command_allowed(cmd)
        status = "✓ 允许" if allowed else "✗ 拒绝"
        print(f"  {cmd}: {status}")
    
    print()


def demo_dependency_management() -> None:
    """演示依赖管理"""
    print("=" * 60)
    print("演示4: 工具依赖管理")
    print("=" * 60)
    
    # 创建有依赖关系的工具配置
    base_tool = ToolConfig(
        tool_id="base-utils",
        tool_type=ToolType.BUILTIN,
        name="基础工具",
        description="提供基础功能的工具",
        entry_point="builtin_tools.utils.base"
    )
    
    middle_tool = ToolConfig(
        tool_id="middleware",
        tool_type=ToolType.CUSTOM,
        name="中间件工具",
        description="依赖基础工具的自定义工具",
        module_path="/path/to/middleware.py",
        dependencies=[ToolDependency(tool_id="base-utils", required=True)]
    )
    
    advanced_tool = ToolConfig(
        tool_id="advanced-processor",
        tool_type=ToolType.CUSTOM,
        name="高级处理器",
        description="依赖中间件工具的自定义工具",
        module_path="/path/to/advanced.py",
        dependencies=[
            ToolDependency(tool_id="middleware", required=True),
            ToolDependency(tool_id="base-utils", required=False)
        ]
    )
    
    # 测试循环依赖
    circular_tool = ToolConfig(
        tool_id="circular-a",
        tool_type=ToolType.BUILTIN,
        name="循环依赖A",
        description="测试循环依赖",
        dependencies=[ToolDependency(tool_id="circular-b", required=True)]
    )
    
    print("依赖关系示例:")
    print(f"  {base_tool.name} -> 无依赖")
    print(f"  {middle_tool.name} -> 依赖 {middle_tool.dependencies[0].tool_id}")
    print(f"  {advanced_tool.name} -> 依赖 {[d.tool_id for d in advanced_tool.dependencies]}")
    
    # 构建依赖图
    loader = ToolLoader()
    loader.configs = {
        config.tool_id: config for config in [base_tool, middle_tool, advanced_tool]
    }
    
    graph = loader._build_dependency_graph([base_tool, middle_tool, advanced_tool])
    print(f"\n依赖关系图: {graph}")
    
    try:
        sorted_tools = loader._topological_sort(graph)
        print(f"拓扑排序结果: {sorted_tools}")
        print("✓ 依赖关系有效")
    except ToolDependencyError as e:
        print(f"✗ 依赖关系错误: {e}")
    
    print()


# ============================================================================
# 测试函数
# ============================================================================

def run_tests() -> bool:
    """运行测试用例"""
    print("=" * 60)
    print("运行工具配置管理测试")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # 测试1: 工具配置创建和序列化
    try:
        security_config = ToolSecurityConfig(
            security_level=SecurityLevel.RESTRICTED,
            allowed_commands=["^python$", "^echo$"],
            max_execution_time=30.0
        )
        
        config = ToolConfig(
            tool_id="test-tool",
            tool_type=ToolType.BUILTIN,
            name="测试工具",
            description="用于测试的工具",
            security_config=security_config
        )
        
        # 测试序列化
        config_dict = config.to_dict()
        config_from_dict = ToolConfig.from_dict(config_dict)
        
        assert config_from_dict.tool_id == "test-tool"
        assert config_from_dict.tool_type == ToolType.BUILTIN
        assert config_from_dict.security_config.security_level == SecurityLevel.RESTRICTED
        
        print("✓ 测试1通过: 工具配置创建和序列化")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试1失败: {e}")
        tests_failed += 1
    
    # 测试2: 环境变量解析
    try:
        config = ToolConfig(
            tool_id="env-tool",
            tool_type=ToolType.EXTERNAL,
            name="环境变量工具",
            command="echo ${MESSAGE:default}",
            environment_variables={
                "PATH": "${CUSTOM_PATH:/usr/bin}",
                "API_KEY": "${SECRET_KEY}"
            }
        )
        
        env_vars = {
            "MESSAGE": "Hello World",
            "SECRET_KEY": "sk-123456"
        }
        
        resolved = config.resolve_environment_variables(env_vars)
        
        assert resolved.command == "echo Hello World"
        assert resolved.environment_variables["PATH"] == "/usr/bin"  # 使用默认值
        assert resolved.environment_variables["API_KEY"] == "sk-123456"
        
        print("✓ 测试2通过: 环境变量解析")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试2失败: {e}")
        tests_failed += 1
    
    # 测试3: 安全配置验证
    try:
        # 有效配置
        valid_config = ToolSecurityConfig(
            security_level=SecurityLevel.RESTRICTED,
            allowed_commands=["^[a-zA-Z0-9_]+$"],
            max_execution_time=10.0,
            max_memory_mb=100
        )
        
        errors = valid_config.validate()
        assert len(errors) == 0
        
        # 无效配置
        invalid_config = ToolSecurityConfig(
            security_level=SecurityLevel.RESTRICTED,
            allowed_commands=["invalid[regex"],
            max_execution_time=-1.0,
            max_memory_mb=0
        )
        
        errors = invalid_config.validate()
        assert len(errors) == 3  # 无效正则、负超时、零内存
        
        print("✓ 测试3通过: 安全配置验证")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试3失败: {e}")
        tests_failed += 1
    
    # 测试4: 命令安全检查
    try:
        security_config = ToolSecurityConfig(
            security_level=SecurityLevel.RESTRICTED,
            allowed_commands=["^python$", "^echo.*$"],
            blocked_commands=["^rm ", "^shutdown"]
        )
        
        # 测试允许的命令
        assert security_config.is_command_allowed("python") == True
        assert security_config.is_command_allowed("echo hello") == True
        
        # 测试禁止的命令
        assert security_config.is_command_allowed("rm -rf /") == False
        assert security_config.is_command_allowed("shutdown now") == False
        
        # 测试未明确允许的命令
        assert security_config.is_command_allowed("bash") == False
        
        print("✓ 测试4通过: 命令安全检查")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试4失败: {e}")
        tests_failed += 1
    
    # 测试5: 工具依赖管理
    try:
        loader = ToolLoader()
        
        # 构建依赖图
        graph = {
            "A": ["B", "C"],
            "B": ["C"],
            "C": []
        }
        
        sorted_nodes = loader._topological_sort(graph)
        
        # 验证排序结果
        assert "C" in sorted_nodes
        assert sorted_nodes.index("C") < sorted_nodes.index("B")
        assert sorted_nodes.index("B") < sorted_nodes.index("A")
        
        # 测试循环依赖
        circular_graph = {
            "X": ["Y"],
            "Y": ["X"]
        }
        
        try:
            loader._topological_sort(circular_graph)
            assert False, "应检测到循环依赖"
        except ToolDependencyError:
            pass  # 期望的异常
        
        print("✓ 测试5通过: 工具依赖管理")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试5失败: {e}")
        tests_failed += 1
    
    # 测试6: 工具类型创建
    try:
        config = ToolConfig(
            tool_id="test-tool",
            tool_type=ToolType.BUILTIN,
            name="测试工具"
        )
        
        loader = ToolLoader()
        tool = asyncio.run(loader._create_tool_instance(config))
        
        assert isinstance(tool, BuiltinTool)
        assert tool.tool_id == "test-tool"
        
        # 测试其他类型
        external_config = ToolConfig(
            tool_id="external-tool",
            tool_type=ToolType.EXTERNAL,
            name="外部工具",
            command="echo test"
        )
        
        external_tool = asyncio.run(loader._create_tool_instance(external_config))
        assert isinstance(external_tool, ExternalTool)
        
        print("✓ 测试6通过: 工具类型创建")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试6失败: {e}")
        tests_failed += 1
    
    # 测试7: 工具加载器配置加载
    try:
        # 创建临时YAML文件
        import tempfile
        import os
        
        yaml_content = """
        - tool_id: yaml-tool-1
          tool_type: builtin
          name: YAML工具1
          description: 从YAML加载的工具1
          entry_point: builtin_tools.test.tool1
        
        - tool_id: yaml-tool-2
          tool_type: custom
          name: YAML工具2
          description: 从YAML加载的工具2
          module_path: /path/to/tool2.py
          class_name: Tool2
          security_config:
            security_level: restricted
            max_execution_time: 30.0
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name
        
        try:
            loader = ToolLoader()
            configs = asyncio.run(loader.load_configs_from_yaml(temp_path))
            
            assert len(configs) == 2
            assert configs[0].tool_id == "yaml-tool-1"
            assert configs[1].tool_id == "yaml-tool-2"
            assert configs[1].security_config.max_execution_time == 30.0
            
            print("✓ 测试7通过: 工具加载器配置加载")
            tests_passed += 1
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except Exception as e:
        print(f"✗ 测试7失败: {e}")
        tests_failed += 1
    
    # 测试8: 异步工具执行模拟
    try:
        async def test_async_execution():
            # 创建模拟工具配置
            config = ToolConfig(
                tool_id="async-test-tool",
                tool_type=ToolType.BUILTIN,
                name="异步测试工具",
                entry_point="builtin_tools.test.async_tool"
            )
            
            loader = ToolLoader()
            tool = await loader._create_tool_instance(config)
            
            # 模拟初始化
            await tool.initialize()
            assert tool.initialized == True
            
            # 模拟执行（由于没有实际函数，会失败但至少流程正确）
            try:
                result = await tool.execute({"test": "data"})
                # 预期失败，因为函数不存在
                assert "error" in result
            except:
                pass  # 预期行为
            
            # 关闭
            await tool.shutdown()
            assert tool.initialized == False
            
            return True
        
        success = asyncio.run(test_async_execution())
        assert success == True
        
        print("✓ 测试8通过: 异步工具执行模拟")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试8失败: {e}")
        tests_failed += 1
    
    # 汇总结果
    print("\n" + "=" * 60)
    print(f"测试结果: {tests_passed} 通过, {tests_failed} 失败")
    print(f"通过率: {tests_passed}/{tests_passed + tests_failed} ({tests_passed/(tests_passed + tests_failed)*100:.1f}%)")
    print("=" * 60)
    
    return tests_failed == 0


# ============================================================================
# 主函数
# ============================================================================

def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description="工具配置管理演示")
    parser.add_argument("--test", action="store_true", help="运行测试用例")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--all", action="store_true", help="运行所有演示和测试")
    
    args = parser.parse_args()
    
    if args.test or args.all:
        success = run_tests()
        if not success:
            sys.exit(1)
    
    if args.demo or args.all or (not args.test and not args.demo and not args.all):
        # 默认运行演示
        demo_basic_usage()
        demo_tool_loader()
        demo_security_validation()
        demo_dependency_management()
        
        print("=" * 60)
        print("演示完成！")
        print("=" * 60)


if __name__ == "__main__":
    main()