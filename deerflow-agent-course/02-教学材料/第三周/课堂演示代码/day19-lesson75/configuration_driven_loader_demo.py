#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeerFlow Python Agent架构师训练营 - 第75节课：配置驱动加载 演示代码

本文件演示了配置驱动加载（Configuration Driven Loading）的完整实现，包括：
1. ConfigurationDrivenLoader类：配置驱动的组件加载器，支持变量解析、组件加载、依赖注入
2. DependencyContainer类：依赖注入容器，支持构造函数注入、属性注入、循环依赖检测
3. 完整测试套件：验证配置加载、变量解析、依赖注入、错误处理等核心功能

学习目标：
- 掌握配置驱动加载的设计哲学和架构模式
- 理解依赖注入容器的实现原理和最佳实践
- 实现配置变量的解析和替换机制
- 掌握组件依赖关系的自动发现和装配技术

使用方式：
python configuration_driven_loader_demo.py          # 运行演示
python configuration_driven_loader_demo.py --test   # 运行测试套件
python configuration_driven_loader_demo.py --bench  # 运行性能基准测试
"""

import asyncio
import importlib
import sys
import logging
import time
import json
import yaml
import os
import re
import inspect
from typing import Dict, List, Optional, Any, Type, Union, Callable, Set
from types import ModuleType
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict, deque
from contextlib import contextmanager
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

class ConfigFormat(Enum):
    """配置文件格式枚举"""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    INI = "ini"


class VariableSource(Enum):
    """变量来源枚举"""
    ENVIRONMENT = "environment"      # 环境变量
    CONFIG_FILE = "config_file"      # 配置文件
    COMMAND_LINE = "command_line"    # 命令行参数
    SECRET_MANAGER = "secret_manager"  # 密钥管理器
    DEFAULT = "default"              # 默认值


class DependencyType(Enum):
    """依赖类型枚举"""
    CONSTRUCTOR = "constructor"      # 构造函数注入
    PROPERTY = "property"            # 属性注入
    METHOD = "method"                # 方法注入
    SETTER = "setter"                # Setter方法注入


class ComponentScope(Enum):
    """组件作用域枚举"""
    SINGLETON = "singleton"          # 单例作用域
    PROTOTYPE = "prototype"          # 原型作用域（每次获取新实例）
    REQUEST = "request"              # 请求作用域
    SESSION = "session"              # 会话作用域


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class ComponentConfig:
    """组件配置数据类"""
    name: str                        # 组件名称
    class_path: str                  # 类路径，格式：module:Class
    enabled: bool = True             # 是否启用
    scope: ComponentScope = ComponentScope.SINGLETON  # 作用域
    lazy: bool = False               # 是否延迟加载
    init_method: Optional[str] = None  # 初始化方法名
    destroy_method: Optional[str] = None  # 销毁方法名
    args: Dict[str, Any] = field(default_factory=dict)  # 构造函数参数
    properties: Dict[str, Any] = field(default_factory=dict)  # 属性注入
    dependencies: List[str] = field(default_factory=list)  # 依赖的组件名
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def __str__(self) -> str:
        return (f"ComponentConfig(name='{self.name}', "
                f"class_path='{self.class_path}', "
                f"enabled={self.enabled}, scope={self.scope})")


@dataclass
class DependencyInfo:
    """依赖信息数据类"""
    name: str                        # 依赖名称
    target_name: str                 # 目标组件名
    dependency_type: DependencyType  # 依赖类型
    required: bool = True            # 是否必需
    qualifier: Optional[str] = None  # 限定符（用于区分相同类型的不同实现）
    
    def __str__(self) -> str:
        return (f"DependencyInfo(name='{self.name}', "
                f"target='{self.target_name}', "
                f"type={self.dependency_type})")


@dataclass
class ResolutionResult:
    """解析结果数据类"""
    success: bool                    # 是否成功
    value: Optional[Any] = None      # 解析得到的值
    source: Optional[VariableSource] = None  # 变量来源
    duration_ms: float = 0.0         # 解析耗时（毫秒）
    error: Optional[str] = None      # 错误信息
    
    def __str__(self) -> str:
        if self.success:
            return (f"ResolutionResult(success=True, "
                    f"value={self.value}, "
                    f"source={self.source}, "
                    f"duration={self.duration_ms:.2f}ms)")
        else:
            return (f"ResolutionResult(success=False, "
                    f"error='{self.error}', "
                    f"duration={self.duration_ms:.2f}ms)")


@dataclass
class ContainerStats:
    """容器统计信息数据类"""
    total_components: int = 0
    loaded_components: int = 0
    failed_components: int = 0
    dependency_injections: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_load_time_ms: float = 0.0
    avg_load_time_ms: float = 0.0
    
    def __str__(self) -> str:
        return (f"ContainerStats(components={self.loaded_components}/{self.total_components}, "
                f"dependencies={self.dependency_injections}, "
                f"cache={self.cache_hits}/{self.cache_hits+self.cache_misses}, "
                f"avg_time={self.avg_load_time_ms:.2f}ms)")


# ============================================================================
# 变量解析器
# ============================================================================

class VariableResolver:
    """
    变量解析器 - 支持配置中的变量引用解析
    
    支持变量格式：
    1. ${variable}                    # 简单变量
    2. ${ENV:VAR_NAME}               # 环境变量
    3. ${CONFIG:section.key}         # 配置文件变量
    4. ${SECRET:secret_name}         # 密钥变量
    5. ${DEFAULT:value}              # 默认值
    6. ${REF:component_name}         # 组件引用
    
    设计模式：策略模式 + 责任链模式
    """
    
    # 变量匹配正则表达式
    VARIABLE_PATTERN = r'\$\{([^}]+)\}'
    
    def __init__(self, 
                 environment_vars: Optional[Dict[str, str]] = None,
                 config_vars: Optional[Dict[str, Any]] = None,
                 secret_provider: Optional[Callable[[str], str]] = None):
        """
        初始化变量解析器
        
        Args:
            environment_vars: 环境变量映射（默认使用os.environ）
            config_vars: 配置变量映射
            secret_provider: 密钥提供者函数
        """
        self.environment_vars = environment_vars or dict(os.environ)
        self.config_vars = config_vars or {}
        self.secret_provider = secret_provider
        self.resolution_cache: Dict[str, ResolutionResult] = {}
        
        # 注册解析策略
        self.resolution_strategies = {
            "ENV": self._resolve_environment_variable,
            "CONFIG": self._resolve_config_variable,
            "SECRET": self._resolve_secret_variable,
            "DEFAULT": self._resolve_default_value,
            "REF": self._resolve_component_reference,
        }
        
        logger.info(f"初始化VariableResolver: "
                   f"env_vars={len(self.environment_vars)}, "
                   f"config_vars={len(self.config_vars)}")
    
    def resolve(self, value: Any, context: Optional[Dict[str, Any]] = None) -> Any:
        """
        解析值中的变量引用
        
        Args:
            value: 需要解析的值（字符串、字典、列表等）
            context: 解析上下文（用于组件引用等）
        
        Returns:
            解析后的值
        """
        if context is None:
            context = {}
        
        start_time = time.time()
        
        try:
            result = self._resolve_recursive(value, context)
            duration = (time.time() - start_time) * 1000
            
            logger.debug(f"变量解析完成: value={value} -> {result}, "
                        f"duration={duration:.2f}ms")
            return result
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"变量解析失败: value={value}, error={str(e)}, "
                        f"duration={duration:.2f}ms")
            raise ValueError(f"变量解析失败: {str(e)}") from e
    
    def _resolve_recursive(self, value: Any, context: Dict[str, Any]) -> Any:
        """递归解析变量"""
        if isinstance(value, str):
            return self._resolve_string(value, context)
        elif isinstance(value, dict):
            return {k: self._resolve_recursive(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_recursive(item, context) for item in value]
        else:
            return value
    
    def _resolve_string(self, value: str, context: Dict[str, Any]) -> str:
        """解析字符串中的变量引用"""
        if not value or '${' not in value:
            return value
        
        # 查找所有变量引用
        matches = list(re.finditer(self.VARIABLE_PATTERN, value))
        if not matches:
            return value
        
        # 如果整个字符串就是一个变量引用，直接解析
        if len(matches) == 1 and matches[0].group(0) == value:
            variable_content = matches[0].group(1)
            resolved = self._resolve_variable(variable_content, context)
            return str(resolved)
        
        # 替换字符串中的变量引用
        result = value
        for match in matches:
            variable_content = match.group(1)
            try:
                resolved = self._resolve_variable(variable_content, context)
                result = result.replace(match.group(0), str(resolved))
            except Exception as e:
                logger.warning(f"变量解析失败，保持原样: {variable_content}, error={str(e)}")
                # 解析失败时保持原样
        
        return result
    
    def _resolve_variable(self, variable_content: str, context: Dict[str, Any]) -> Any:
        """解析单个变量"""
        # 检查缓存
        cache_key = f"{variable_content}:{str(context.get('component', ''))}"
        if cache_key in self.resolution_cache:
            cached = self.resolution_cache[cache_key]
            if cached.success:
                logger.debug(f"变量缓存命中: {variable_content}")
                return cached.value
        
        start_time = time.time()
        
        try:
            # 解析变量类型和值
            if ':' in variable_content:
                var_type, var_value = variable_content.split(':', 1)
                var_type = var_type.upper()
                
                if var_type in self.resolution_strategies:
                    result = self.resolution_strategies[var_type](var_value, context)
                else:
                    raise ValueError(f"不支持的变量类型: {var_type}")
            else:
                # 简单变量，先从上下文查找，然后从配置变量查找
                var_name = variable_content
                if var_name in context:
                    result = context[var_name]
                elif var_name in self.config_vars:
                    result = self.config_vars[var_name]
                else:
                    raise ValueError(f"变量未定义: {var_name}")
            
            duration = (time.time() - start_time) * 1000
            
            # 缓存结果
            resolution_result = ResolutionResult(
                success=True,
                value=result,
                source=VariableSource.CONFIG_FILE if ':' not in variable_content else None,
                duration_ms=duration
            )
            self.resolution_cache[cache_key] = resolution_result
            
            logger.debug(f"变量解析成功: {variable_content} -> {result}, "
                        f"duration={duration:.2f}ms")
            return result
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            resolution_result = ResolutionResult(
                success=False,
                error=str(e),
                duration_ms=duration
            )
            self.resolution_cache[cache_key] = resolution_result
            raise
    
    def _resolve_environment_variable(self, var_name: str, context: Dict[str, Any]) -> str:
        """解析环境变量"""
        if var_name not in self.environment_vars:
            raise ValueError(f"环境变量未定义: {var_name}")
        return self.environment_vars[var_name]
    
    def _resolve_config_variable(self, var_path: str, context: Dict[str, Any]) -> Any:
        """解析配置变量"""
        # 支持点分隔的路径，如: section.key.subkey
        parts = var_path.split('.')
        current = self.config_vars
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise ValueError(f"配置变量路径不存在: {var_path}")
        
        return current
    
    def _resolve_secret_variable(self, secret_name: str, context: Dict[str, Any]) -> str:
        """解析密钥变量"""
        if not self.secret_provider:
            raise ValueError("未配置密钥提供者")
        
        try:
            return self.secret_provider(secret_name)
        except Exception as e:
            raise ValueError(f"获取密钥失败: {secret_name}, error={str(e)}") from e
    
    def _resolve_default_value(self, default_value: str, context: Dict[str, Any]) -> str:
        """解析默认值"""
        return default_value
    
    def _resolve_component_reference(self, component_name: str, context: Dict[str, Any]) -> Any:
        """解析组件引用"""
        # 组件引用在依赖注入阶段处理，这里只做验证
        if 'container' not in context:
            raise ValueError("组件引用需要容器上下文")
        
        container = context['container']
        if not hasattr(container, 'get_component'):
            raise ValueError("容器不支持组件获取")
        
        # 返回一个特殊的引用对象，在依赖注入阶段解析
        return {"$ref": component_name}
    
    def clear_cache(self) -> None:
        """清空解析缓存"""
        self.resolution_cache.clear()
        logger.info("变量解析缓存已清空")


# ============================================================================
# 依赖注入容器
# ============================================================================

class DependencyContainer:
    """
    依赖注入容器 - 管理组件依赖关系并自动装配
    
    核心功能：
    1. 组件注册和管理（单例、原型作用域）
    2. 依赖自动发现和注入（构造函数、属性、方法注入）
    3. 循环依赖检测和解决
    4. 组件生命周期管理（初始化、销毁）
    5. 条件装配和Profile支持
    
    设计模式：容器模式 + 依赖注入模式 + 工厂模式
    """
    
    def __init__(self, 
                 enable_cycle_detection: bool = True,
                 enable_lazy_loading: bool = False):
        """
        初始化依赖注入容器
        
        Args:
            enable_cycle_detection: 是否启用循环依赖检测
            enable_lazy_loading: 是否启用延迟加载
        """
        self.enable_cycle_detection = enable_cycle_detection
        self.enable_lazy_loading = enable_lazy_loading
        
        # 组件注册表
        self.registry: Dict[str, ComponentConfig] = {}
        
        # 组件实例缓存（按作用域管理）
        self.singleton_cache: Dict[str, Any] = {}
        self.prototype_cache: Dict[str, List[Any]] = defaultdict(list)
        
        # 依赖关系图
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        
        # 统计信息
        self.stats = ContainerStats()
        self.initialization_time = time.time()
        
        # 状态标志
        self._initialized = False
        self._initializing = False
        self._destroyed = False
        
        logger.info(f"初始化DependencyContainer: "
                   f"cycle_detection={enable_cycle_detection}, "
                   f"lazy_loading={enable_lazy_loading}")
    
    def register_component(self, config: ComponentConfig) -> None:
        """
        注册组件配置
        
        Args:
            config: 组件配置
        
        Raises:
            ValueError: 组件名已存在或配置无效
        """
        if self._initialized:
            raise RuntimeError("容器已初始化，不能再注册组件")
        
        if config.name in self.registry:
            raise ValueError(f"组件名已存在: {config.name}")
        
        # 验证配置
        self._validate_component_config(config)
        
        # 注册组件
        self.registry[config.name] = config
        self.stats.total_components += 1
        
        # 建立依赖关系
        for dep_name in config.dependencies:
            self.dependency_graph[config.name].add(dep_name)
            self.reverse_dependency_graph[dep_name].add(config.name)
        
        logger.debug(f"注册组件: {config}")
    
    def _validate_component_config(self, config: ComponentConfig) -> None:
        """验证组件配置"""
        if not config.name or not config.name.strip():
            raise ValueError("组件名不能为空")
        
        if not config.class_path or ':' not in config.class_path:
            raise ValueError(f"无效的类路径格式: {config.class_path}")
        
        # 检查依赖是否存在（如果容器已包含该依赖）
        for dep_name in config.dependencies:
            if dep_name in self.registry:
                # 检查循环依赖
                if self.enable_cycle_detection:
                    self._check_cycle(config.name, dep_name)
    
    def _check_cycle(self, new_component: str, dependency: str) -> None:
        """检查循环依赖"""
        # 使用DFS检测循环
        visited = set()
        stack = [dependency]
        
        while stack:
            current = stack.pop()
            if current == new_component:
                raise ValueError(f"检测到循环依赖: {new_component} -> {dependency} -> ... -> {new_component}")
            
            if current in visited:
                continue
            
            visited.add(current)
            
            if current in self.dependency_graph:
                for next_dep in self.dependency_graph[current]:
                    stack.append(next_dep)
    
    async def initialize(self) -> None:
        """
        初始化容器，加载所有组件
        
        Raises:
            RuntimeError: 容器已初始化或正在初始化
        """
        if self._initialized:
            logger.warning("容器已初始化")
            return
        
        if self._initializing:
            raise RuntimeError("容器正在初始化")
        
        self._initializing = True
        start_time = time.time()
        
        try:
            logger.info(f"开始初始化容器，组件数: {len(self.registry)}")
            
            # 1. 检测循环依赖
            if self.enable_cycle_detection:
                self._detect_all_cycles()
            
            # 2. 拓扑排序确定加载顺序
            load_order = self._get_load_order()
            
            # 3. 按顺序加载组件
            for component_name in load_order:
                await self._load_component(component_name)
            
            # 4. 初始化延迟加载的组件（如果需要）
            if not self.enable_lazy_loading:
                for config in self.registry.values():
                    if config.lazy and config.enabled:
                        await self.get_component(config.name)
            
            self._initialized = True
            self._initializing = False
            
            duration = (time.time() - start_time) * 1000
            self.stats.total_load_time_ms = duration
            self.stats.avg_load_time_ms = duration / max(1, self.stats.loaded_components)
            
            logger.info(f"容器初始化完成: {self.stats}, duration={duration:.2f}ms")
            
        except Exception as e:
            self._initializing = False
            logger.error(f"容器初始化失败: {str(e)}")
            raise
    
    def _detect_all_cycles(self) -> None:
        """检测所有循环依赖"""
        visited = set()
        recursion_stack = set()
        
        def dfs(node: str) -> None:
            if node in visited:
                return
            
            visited.add(node)
            recursion_stack.add(node)
            
            for neighbor in self.dependency_graph.get(node, []):
                if neighbor in recursion_stack:
                    raise ValueError(f"检测到循环依赖: {node} -> {neighbor}")
                if neighbor not in visited:
                    dfs(neighbor)
            
            recursion_stack.remove(node)
        
        for component in self.registry.keys():
            if component not in visited:
                dfs(component)
    
    def _get_load_order(self) -> List[str]:
        """获取拓扑排序的加载顺序"""
        # Kahn算法进行拓扑排序
        in_degree = {name: 0 for name in self.registry}
        
        # 计算入度
        for name in self.registry:
            for dep in self.dependency_graph.get(name, []):
                if dep in self.registry:
                    in_degree[dep] += 1
        
        # 初始化队列（入度为0的节点）
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for dep in self.dependency_graph.get(node, []):
                if dep in self.registry:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)
        
        # 检查是否有环（剩余节点）
        if len(result) != len(self.registry):
            remaining = [name for name in self.registry if name not in result]
            raise ValueError(f"存在循环依赖或未解析的依赖: {remaining}")
        
        return result
    
    async def _load_component(self, component_name: str) -> None:
        """加载单个组件"""
        config = self.registry[component_name]
        
        if not config.enabled:
            logger.debug(f"组件已禁用，跳过加载: {component_name}")
            return
        
        start_time = time.time()
        
        try:
            logger.debug(f"开始加载组件: {component_name}")
            
            # 1. 解析类路径，获取类对象
            class_obj = await self._resolve_class(config.class_path)
            
            # 2. 准备构造函数参数
            constructor_args = await self._prepare_constructor_args(config, component_name)
            
            # 3. 创建实例
            instance = class_obj(**constructor_args)
            
            # 4. 属性注入
            await self._inject_properties(instance, config, component_name)
            
            # 5. 调用初始化方法
            if config.init_method and hasattr(instance, config.init_method):
                init_method = getattr(instance, config.init_method)
                if asyncio.iscoroutinefunction(init_method):
                    await init_method()
                else:
                    init_method()
            
            # 6. 缓存实例（根据作用域）
            if config.scope == ComponentScope.SINGLETON:
                self.singleton_cache[component_name] = instance
            
            self.stats.loaded_components += 1
            self.stats.dependency_injections += len(constructor_args) + len(config.properties)
            
            duration = (time.time() - start_time) * 1000
            logger.info(f"组件加载成功: {component_name}, duration={duration:.2f}ms")
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.stats.failed_components += 1
            logger.error(f"组件加载失败: {component_name}, error={str(e)}, "
                        f"duration={duration:.2f}ms")
            raise ValueError(f"加载组件失败: {component_name}, error={str(e)}") from e
    
    async def _resolve_class(self, class_path: str) -> Type:
        """解析类路径为类对象"""
        # 简单实现，实际应该使用ClassResolver
        if ':' not in class_path:
            raise ValueError(f"无效的类路径格式: {class_path}")
        
        module_name, class_name = class_path.split(':', 1)
        
        try:
            module = importlib.import_module(module_name)
            class_obj = getattr(module, class_name)
            
            if not inspect.isclass(class_obj):
                raise ValueError(f"{class_path} 不是类")
            
            return class_obj
            
        except ImportError as e:
            raise ValueError(f"模块未找到: {module_name}") from e
        except AttributeError as e:
            raise ValueError(f"类未找到: {class_name} 在模块 {module_name} 中") from e
    
    async def _prepare_constructor_args(self, config: ComponentConfig, component_name: str) -> Dict[str, Any]:
        """准备构造函数参数"""
        args = {}
        
        for param_name, param_value in config.args.items():
            # 解析参数值（可能包含变量引用）
            resolved_value = await self._resolve_parameter_value(param_value, component_name, param_name)
            args[param_name] = resolved_value
        
        return args
    
    async def _resolve_parameter_value(self, value: Any, component_name: str, param_name: str) -> Any:
        """解析参数值"""
        # 如果是组件引用，获取组件实例
        if isinstance(value, dict) and '$ref' in value:
            ref_component = value['$ref']
            return await self.get_component(ref_component)
        
        # 如果是变量引用，需要变量解析器（在ConfigurationDrivenLoader中处理）
        # 这里简单返回原值
        return value
    
    async def _inject_properties(self, instance: Any, config: ComponentConfig, component_name: str) -> None:
        """注入属性"""
        for prop_name, prop_value in config.properties.items():
            # 解析属性值
            resolved_value = await self._resolve_parameter_value(prop_value, component_name, prop_name)
            
            # 设置属性
            if hasattr(instance, prop_name):
                setattr(instance, prop_name, resolved_value)
            else:
                logger.warning(f"组件 {component_name} 没有属性 {prop_name}，跳过注入")
    
    async def get_component(self, component_name: str) -> Any:
        """
        获取组件实例
        
        Args:
            component_name: 组件名称
        
        Returns:
            组件实例
        
        Raises:
            ValueError: 组件未找到或加载失败
            RuntimeError: 容器未初始化
        """
        if not self._initialized:
            raise RuntimeError("容器未初始化，请先调用initialize()")
        
        if component_name not in self.registry:
            raise ValueError(f"组件未注册: {component_name}")
        
        config = self.registry[component_name]
        
        # 检查缓存
        if config.scope == ComponentScope.SINGLETON:
            if component_name in self.singleton_cache:
                self.stats.cache_hits += 1
                return self.singleton_cache[component_name]
            self.stats.cache_misses += 1
        
        # 如果是原型作用域，创建新实例
        if config.scope == ComponentScope.PROTOTYPE:
            # 重新加载组件（原型作用域每次都创建新实例）
            return await self._create_prototype_instance(config, component_name)
        
        # 单例但不在缓存中，重新加载
        instance = await self._load_component_direct(config, component_name)
        self.singleton_cache[component_name] = instance
        return instance
    
    async def _create_prototype_instance(self, config: ComponentConfig, component_name: str) -> Any:
        """创建原型作用域的实例"""
        # 简化实现，实际应该复用加载逻辑
        class_obj = await self._resolve_class(config.class_path)
        constructor_args = await self._prepare_constructor_args(config, component_name)
        instance = class_obj(**constructor_args)
        await self._inject_properties(instance, config, component_name)
        
        # 记录原型实例
        self.prototype_cache[component_name].append(instance)
        
        return instance
    
    async def _load_component_direct(self, config: ComponentConfig, component_name: str) -> Any:
        """直接加载组件（简化版本）"""
        class_obj = await self._resolve_class(config.class_path)
        constructor_args = await self._prepare_constructor_args(config, component_name)
        instance = class_obj(**constructor_args)
        await self._inject_properties(instance, config, component_name)
        
        if config.init_method and hasattr(instance, config.init_method):
            init_method = getattr(instance, config.init_method)
            if asyncio.iscoroutinefunction(init_method):
                await init_method()
            else:
                init_method()
        
        return instance
    
    async def destroy(self) -> None:
        """销毁容器，调用所有组件的销毁方法"""
        if self._destroyed:
            return
        
        logger.info("开始销毁容器")
        
        # 逆序销毁组件（依赖者先销毁）
        destroy_order = self._get_load_order()
        destroy_order.reverse()
        
        for component_name in destroy_order:
            await self._destroy_component(component_name)
        
        self._destroyed = True
        logger.info("容器销毁完成")
    
    async def _destroy_component(self, component_name: str) -> None:
        """销毁单个组件"""
        config = self.registry.get(component_name)
        if not config or not config.enabled:
            return
        
        # 查找组件实例
        instances = []
        
        if component_name in self.singleton_cache:
            instances.append(self.singleton_cache[component_name])
        
        if component_name in self.prototype_cache:
            instances.extend(self.prototype_cache[component_name])
        
        # 调用销毁方法
        for instance in instances:
            if config.destroy_method and hasattr(instance, config.destroy_method):
                try:
                    destroy_method = getattr(instance, config.destroy_method)
                    if asyncio.iscoroutinefunction(destroy_method):
                        await destroy_method()
                    else:
                        destroy_method()
                    logger.debug(f"组件销毁方法调用成功: {component_name}")
                except Exception as e:
                    logger.warning(f"组件销毁方法调用失败: {component_name}, error={str(e)}")
        
        # 清理缓存
        self.singleton_cache.pop(component_name, None)
        self.prototype_cache.pop(component_name, None)
    
    def get_stats(self) -> ContainerStats:
        """获取容器统计信息"""
        return copy.deepcopy(self.stats)
    
    def get_registered_components(self) -> List[str]:
        """获取所有已注册的组件名"""
        return list(self.registry.keys())
    
    def has_component(self, component_name: str) -> bool:
        """检查组件是否已注册"""
        return component_name in self.registry
    
    def is_initialized(self) -> bool:
        """检查容器是否已初始化"""
        return self._initialized


# ============================================================================
# 配置驱动加载器
# ============================================================================

class ConfigurationDrivenLoader:
    """
    配置驱动加载器 - 基于配置文件的组件加载系统
    
    核心功能：
    1. 加载和解析配置文件（JSON/YAML/TOML）
    2. 变量解析和替换（环境变量、配置变量、组件引用）
    3. 组件配置验证和转换
    4. 依赖注入容器集成
    5. 配置热重载支持
    
    设计模式：建造者模式 + 策略模式 + 观察者模式
    """
    
    def __init__(self, 
                 config_format: ConfigFormat = ConfigFormat.YAML,
                 variable_resolver: Optional[VariableResolver] = None,
                 dependency_container: Optional[DependencyContainer] = None):
        """
        初始化配置驱动加载器
        
        Args:
            config_format: 配置文件格式
            variable_resolver: 变量解析器（默认创建新的）
            dependency_container: 依赖注入容器（默认创建新的）
        """
        self.config_format = config_format
        self.variable_resolver = variable_resolver or VariableResolver()
        self.dependency_container = dependency_container or DependencyContainer()
        
        # 配置缓存
        self.config_cache: Dict[str, Dict[str, Any]] = {}
        self.last_modified: Dict[str, float] = {}
        
        # 文件监视器（用于热重载）
        self.watched_files: Set[str] = set()
        
        # 统计信息
        self.stats = {
            "configs_loaded": 0,
            "components_loaded": 0,
            "variables_resolved": 0,
            "errors": 0,
            "total_load_time_ms": 0.0
        }
        
        logger.info(f"初始化ConfigurationDrivenLoader: format={config_format}")
    
    async def load_from_file(self, file_path: str, 
                            watch_for_changes: bool = False) -> DependencyContainer:
        """
        从文件加载配置并初始化容器
        
        Args:
            file_path: 配置文件路径
            watch_for_changes: 是否监视文件变化（热重载）
        
        Returns:
            初始化后的依赖注入容器
        
        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置解析失败
        """
        start_time = time.time()
        
        try:
            # 1. 加载和解析配置文件
            config_data = self._load_config_file(file_path)
            
            # 2. 解析变量（第一轮）
            resolved_config = self._resolve_variables(config_data, {"config_file": file_path})
            
            # 3. 提取组件配置
            component_configs = self._extract_component_configs(resolved_config)
            
            # 4. 注册组件到容器
            for config in component_configs:
                self.dependency_container.register_component(config)
            
            # 5. 初始化容器
            await self.dependency_container.initialize()
            
            # 6. 设置文件监视（如果需要）
            if watch_for_changes:
                self._watch_file(file_path)
            
            duration = (time.time() - start_time) * 1000
            self.stats["total_load_time_ms"] += duration
            self.stats["configs_loaded"] += 1
            self.stats["components_loaded"] += len(component_configs)
            
            logger.info(f"配置加载完成: file={file_path}, "
                       f"components={len(component_configs)}, "
                       f"duration={duration:.2f}ms")
            
            return self.dependency_container
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.stats["errors"] += 1
            logger.error(f"配置加载失败: file={file_path}, error={str(e)}, "
                        f"duration={duration:.2f}ms")
            raise
    
    def _load_config_file(self, file_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        # 检查缓存
        file_mtime = os.path.getmtime(file_path)
        if file_path in self.config_cache and file_path in self.last_modified:
            if self.last_modified[file_path] >= file_mtime:
                logger.debug(f"使用缓存配置: {file_path}")
                return copy.deepcopy(self.config_cache[file_path])
        
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 根据格式解析
        try:
            if self.config_format == ConfigFormat.JSON:
                config_data = json.loads(content)
            elif self.config_format == ConfigFormat.YAML:
                config_data = yaml.safe_load(content)
            else:
                # 简化处理，实际应支持更多格式
                raise ValueError(f"不支持的配置文件格式: {self.config_format}")
            
            # 验证配置结构
            self._validate_config_structure(config_data)
            
            # 更新缓存
            self.config_cache[file_path] = copy.deepcopy(config_data)
            self.last_modified[file_path] = file_mtime
            
            logger.debug(f"配置文件加载成功: {file_path}")
            return config_data
            
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValueError(f"配置文件解析失败: {file_path}, error={str(e)}") from e
    
    def _validate_config_structure(self, config_data: Dict[str, Any]) -> None:
        """验证配置结构"""
        if not isinstance(config_data, dict):
            raise ValueError("配置文件必须是字典格式")
        
        # 检查必需的顶级字段
        if "application" not in config_data:
            logger.warning("配置缺少'application'字段")
        
        if "components" not in config_data:
            raise ValueError("配置必须包含'components'字段")
        
        if not isinstance(config_data["components"], dict):
            raise ValueError("'components'字段必须是字典格式")
    
    def _resolve_variables(self, config_data: Any, context: Dict[str, Any]) -> Any:
        """解析配置中的变量引用"""
        # 使用变量解析器递归解析
        context.update({"resolver": self.variable_resolver})
        return self.variable_resolver.resolve(config_data, context)
    
    def _extract_component_configs(self, config_data: Dict[str, Any]) -> List[ComponentConfig]:
        """从配置数据提取组件配置"""
        components_section = config_data.get("components", {})
        component_configs = []
        
        for name, component_data in components_section.items():
            try:
                config = self._create_component_config(name, component_data)
                component_configs.append(config)
            except Exception as e:
                logger.error(f"创建组件配置失败: {name}, error={str(e)}")
                if component_data.get("required", True):
                    raise
        
        return component_configs
    
    def _create_component_config(self, name: str, data: Dict[str, Any]) -> ComponentConfig:
        """从字典数据创建ComponentConfig"""
        # 解析作用域
        scope_str = data.get("scope", "singleton").upper()
        try:
            scope = ComponentScope[scope_str]
        except KeyError:
            logger.warning(f"未知的作用域: {scope_str}，使用默认值SINGLETON")
            scope = ComponentScope.SINGLETON
        
        # 解析依赖列表
        dependencies = data.get("dependencies", [])
        if isinstance(dependencies, str):
            dependencies = [dependencies]
        
        # 创建配置对象
        config = ComponentConfig(
            name=name,
            class_path=data["class"],
            enabled=data.get("enabled", True),
            scope=scope,
            lazy=data.get("lazy", False),
            init_method=data.get("init_method"),
            destroy_method=data.get("destroy_method"),
            args=data.get("args", {}),
            properties=data.get("properties", {}),
            dependencies=dependencies,
            metadata=data.get("metadata", {})
        )
        
        return config
    
    def _watch_file(self, file_path: str) -> None:
        """监视文件变化（简化实现）"""
        self.watched_files.add(file_path)
        logger.info(f"开始监视文件变化: {file_path}")
        # 实际实现应该使用watchdog等库
    
    async def reload_if_changed(self) -> bool:
        """重新加载已更改的配置文件"""
        changed = False
        
        for file_path in self.watched_files:
            if not os.path.exists(file_path):
                continue
            
            file_mtime = os.path.getmtime(file_path)
            if file_path in self.last_modified and file_mtime > self.last_modified[file_path]:
                logger.info(f"检测到配置文件变化: {file_path}")
                try:
                    # 重新加载配置
                    await self.load_from_file(file_path, watch_for_changes=True)
                    changed = True
                except Exception as e:
                    logger.error(f"配置文件热重载失败: {file_path}, error={str(e)}")
        
        return changed
    
    def get_stats(self) -> Dict[str, Any]:
        """获取加载器统计信息"""
        return copy.deepcopy(self.stats)
    
    def clear_cache(self) -> None:
        """清空配置缓存"""
        self.config_cache.clear()
        self.last_modified.clear()
        self.variable_resolver.clear_cache()
        logger.info("配置缓存已清空")


# ============================================================================
# 示例组件（用于演示）
# ============================================================================

class DatabaseConnector:
    """数据库连接器示例组件"""
    
    def __init__(self, host: str = "localhost", port: int = 5432, 
                 database: str = "test", username: str = "admin", 
                 password: str = "secret"):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.connection = None
        self.connected = False
    
    async def initialize(self):
        """初始化方法（模拟异步连接）"""
        logger.info(f"数据库连接器初始化: {self.host}:{self.port}/{self.database}")
        # 模拟连接过程
        await asyncio.sleep(0.1)
        self.connection = f"Connection to {self.host}:{self.port}"
        self.connected = True
        logger.info("数据库连接器初始化完成")
    
    async def query(self, sql: str) -> List[Dict[str, Any]]:
        """执行查询（模拟）"""
        if not self.connected:
            raise RuntimeError("数据库未连接")
        
        logger.debug(f"执行查询: {sql}")
        await asyncio.sleep(0.05)
        return [{"result": "data"}]
    
    async def close(self):
        """关闭连接"""
        if self.connection:
            logger.info("关闭数据库连接")
            self.connection = None
            self.connected = False


class CacheService:
    """缓存服务示例组件"""
    
    def __init__(self, host: str = "localhost", port: int = 6379,
                 max_size: int = 1000, ttl: int = 3600):
        self.host = host
        self.port = port
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Any] = {}
        self.hit_count = 0
        self.miss_count = 0
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        actual_ttl = ttl or self.ttl
        self.cache[key] = {
            "value": value,
            "expires": time.time() + actual_ttl
        }
        
        # 限制缓存大小
        if len(self.cache) > self.max_size:
            self._evict_oldest()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self.cache:
            self.miss_count += 1
            return None
        
        entry = self.cache[key]
        if entry["expires"] < time.time():
            # 过期
            del self.cache[key]
            self.miss_count += 1
            return None
        
        self.hit_count += 1
        return entry["value"]
    
    def _evict_oldest(self) -> None:
        """驱逐最老的缓存项"""
        if not self.cache:
            return
        
        oldest_key = min(self.cache.keys(), 
                        key=lambda k: self.cache[k]["expires"])
        del self.cache[oldest_key]
        logger.debug(f"缓存项被驱逐: {oldest_key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "max_size": self.max_size
        }


class UserService:
    """用户服务示例组件（依赖数据库和缓存）"""
    
    def __init__(self, db: Optional[DatabaseConnector] = None,
                 cache: Optional[CacheService] = None):
        self.db = db
        self.cache = cache
        self.user_cache_ttl = 300  # 5分钟
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息（使用缓存）"""
        if self.cache:
            cached = self.cache.get(f"user:{user_id}")
            if cached is not None:
                logger.debug(f"缓存命中: user:{user_id}")
                return cached
        
        # 从数据库查询
        if self.db:
            try:
                results = await self.db.query(f"SELECT * FROM users WHERE id = '{user_id}'")
                if results:
                    user_data = results[0]
                    
                    # 写入缓存
                    if self.cache:
                        self.cache.set(f"user:{user_id}", user_data, self.user_cache_ttl)
                    
                    return user_data
            except Exception as e:
                logger.error(f"查询用户失败: {user_id}, error={str(e)}")
        
        return None
    
    async def update_user(self, user_id: str, data: Dict[str, Any]) -> bool:
        """更新用户信息（清除缓存）"""
        if self.db:
            try:
                # 模拟更新操作
                await self.db.query(f"UPDATE users SET ... WHERE id = '{user_id}'")
                
                # 清除缓存
                if self.cache:
                    self.cache.set(f"user:{user_id}", None, 0)  # 立即过期
                
                logger.info(f"用户信息已更新: {user_id}")
                return True
            except Exception as e:
                logger.error(f"更新用户失败: {user_id}, error={str(e)}")
        
        return False


# ============================================================================
# 测试套件
# ============================================================================

class TestConfigurationDrivenLoader:
    """配置驱动加载器测试套件"""
    
    @staticmethod
    async def test_variable_resolver() -> bool:
        """测试变量解析器"""
        logger.info("开始测试变量解析器")
        
        try:
            # 创建解析器
            resolver = VariableResolver(
                environment_vars={"TEST_ENV_VAR": "env_value"},
                config_vars={"database": {"host": "db.local", "port": 5432}}
            )
            
            # 测试简单变量
            result = resolver.resolve("${database.host}", {})
            assert result == "db.local", f"期望 'db.local'，实际 '{result}'"
            
            # 测试环境变量
            result = resolver.resolve("${ENV:TEST_ENV_VAR}", {})
            assert result == "env_value", f"期望 'env_value'，实际 '{result}'"
            
            # 测试默认值
            result = resolver.resolve("${DEFAULT:default_value}", {})
            assert result == "default_value", f"期望 'default_value'，实际 '{result}'"
            
            # 测试嵌套结构
            config = {
                "host": "${database.host}",
                "port": "${database.port}",
                "url": "http://${database.host}:${database.port}"
            }
            resolved = resolver.resolve(config, {})
            assert resolved["host"] == "db.local"
            assert resolved["port"] == 5432
            assert resolved["url"] == "http://db.local:5432"
            
            logger.info("变量解析器测试通过")
            return True
            
        except Exception as e:
            logger.error(f"变量解析器测试失败: {str(e)}")
            return False
    
    @staticmethod
    async def test_dependency_container() -> bool:
        """测试依赖注入容器"""
        logger.info("开始测试依赖注入容器")
        
        try:
            # 创建容器
            container = DependencyContainer(enable_cycle_detection=True)
            
            # 注册组件
            db_config = ComponentConfig(
                name="database",
                class_path="__main__:DatabaseConnector",
                args={"host": "localhost", "port": 5432, "database": "test"}
            )
            
            cache_config = ComponentConfig(
                name="cache",
                class_path="__main__:CacheService",
                args={"host": "cache.local", "port": 6379, "max_size": 1000},
                dependencies=["database"]  # 依赖数据库
            )
            
            container.register_component(db_config)
            container.register_component(cache_config)
            
            # 初始化容器
            await container.initialize()
            
            # 获取组件
            db = await container.get_component("database")
            assert isinstance(db, DatabaseConnector)
            assert db.host == "localhost"
            
            cache = await container.get_component("cache")
            assert isinstance(cache, CacheService)
            assert cache.host == "cache.local"
            
            # 检查统计信息
            stats = container.get_stats()
            assert stats.loaded_components == 2
            
            # 销毁容器
            await container.destroy()
            
            logger.info("依赖注入容器测试通过")
            return True
            
        except Exception as e:
            logger.error(f"依赖注入容器测试失败: {str(e)}")
            return False
    
    @staticmethod
    async def test_configuration_loader() -> bool:
        """测试配置驱动加载器"""
        logger.info("开始测试配置驱动加载器")
        
        try:
            # 创建临时配置文件
            import tempfile
            
            config_content = """
application: "测试应用"
components:
  database:
    class: "__main__:DatabaseConnector"
    enabled: true
    scope: singleton
    args:
      host: "localhost"
      port: 5432
      database: "testdb"
      username: "admin"
      password: "${DEFAULT:secret123}"
    init_method: "initialize"
    
  cache:
    class: "__main__:CacheService"
    enabled: true
    scope: singleton
    args:
      host: "cache.local"
      port: 6379
      max_size: 1000
      ttl: 3600
    dependencies:
      - database
    lazy: false
"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(config_content)
                temp_file = f.name
            
            try:
                # 创建加载器
                loader = ConfigurationDrivenLoader(config_format=ConfigFormat.YAML)
                
                # 加载配置
                container = await loader.load_from_file(temp_file)
                
                # 验证组件加载
                assert container.has_component("database")
                assert container.has_component("cache")
                
                # 获取组件
                db = await container.get_component("database")
                assert isinstance(db, DatabaseConnector)
                
                cache = await container.get_component("cache")
                assert isinstance(cache, CacheService)
                
                # 检查统计信息
                stats = loader.get_stats()
                assert stats["components_loaded"] == 2
                
                logger.info("配置驱动加载器测试通过")
                return True
                
            finally:
                # 清理临时文件
                os.unlink(temp_file)
            
        except Exception as e:
            logger.error(f"配置驱动加载器测试失败: {str(e)}")
            return False
    
    @staticmethod
    async def run_all_tests() -> Dict[str, bool]:
        """运行所有测试"""
        logger.info("开始运行配置驱动加载器测试套件")
        
        results = {
            "variable_resolver": await TestConfigurationDrivenLoader.test_variable_resolver(),
            "dependency_container": await TestConfigurationDrivenLoader.test_dependency_container(),
            "configuration_loader": await TestConfigurationDrivenLoader.test_configuration_loader()
        }
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        logger.info(f"测试套件完成: {passed}/{total} 通过")
        return results


# ============================================================================
# 演示函数
# ============================================================================

async def run_demo() -> None:
    """运行配置驱动加载演示"""
    logger.info("开始配置驱动加载演示")
    
    try:
        # 1. 演示变量解析器
        logger.info("=== 1. 变量解析器演示 ===")
        resolver = VariableResolver(
            environment_vars={"APP_ENV": "production", "DB_HOST": "prod-db.local"},
            config_vars={
                "app": {"name": "DeerFlow", "version": "2.0.0"},
                "database": {"host": "${DB_HOST}", "port": 5432, "name": "deerflow_db"},
                "cache": {"host": "redis.local", "port": 6379}
            }
        )
        
        # 解析复杂配置
        complex_config = {
            "app_name": "${app.name}",
            "app_version": "${app.version}",
            "database_url": "postgresql://${database.host}:${database.port}/${database.name}",
            "environment": "${ENV:APP_ENV}"
        }
        
        resolved = resolver.resolve(complex_config, {})
        logger.info(f"变量解析结果: {json.dumps(resolved, indent=2, ensure_ascii=False)}")
        
        # 2. 演示依赖注入容器
        logger.info("\n=== 2. 依赖注入容器演示 ===")
        container = DependencyContainer()
        
        # 注册组件
        container.register_component(ComponentConfig(
            name="db",
            class_path="__main__:DatabaseConnector",
            args={"host": "demo-db.local", "port": 5432, "database": "demo"}
        ))
        
        container.register_component(ComponentConfig(
            name="cache",
            class_path="__main__:CacheService",
            args={"host": "demo-cache.local", "port": 6379, "max_size": 500}
        ))
        
        container.register_component(ComponentConfig(
            name="user_service",
            class_path="__main__:UserService",
            dependencies=["db", "cache"],
            properties={"user_cache_ttl": 600}
        ))
        
        # 初始化容器
        await container.initialize()
        
        # 使用组件
        user_service = await container.get_component("user_service")
        assert isinstance(user_service, UserService)
        assert user_service.db is not None
        assert user_service.cache is not None
        
        logger.info(f"依赖注入成功: UserService注入了Database和Cache")
        
        # 3. 演示配置驱动加载器
        logger.info("\n=== 3. 配置驱动加载器演示 ===")
        
        # 创建示例配置文件
        config_yaml = """
application: "微服务演示系统"
environment: "development"

variables:
  db_host: "config-db.local"
  cache_host: "config-cache.local"

components:
  primary_db:
    class: "__main__:DatabaseConnector"
    enabled: true
    scope: singleton
    args:
      host: "${db_host}"
      port: 5432
      database: "primary"
      username: "admin"
      password: "${ENV:DB_PASSWORD}"
    init_method: "initialize"
    destroy_method: "close"
    
  redis_cache:
    class: "__main__:CacheService"
    enabled: true
    scope: singleton
    args:
      host: "${cache_host}"
      port: 6379
      max_size: 1000
      ttl: 1800
    dependencies: []
    lazy: false
    
  user_service:
    class: "__main__:UserService"
    enabled: true
    scope: singleton
    args: {}
    properties:
      user_cache_ttl: 300
    dependencies:
      - primary_db
      - redis_cache
"""
        
        # 写入临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_file = f.name
        
        try:
            # 设置环境变量用于演示
            os.environ["DB_PASSWORD"] = "secure_password_123"
            
            # 创建加载器
            loader = ConfigurationDrivenLoader(config_format=ConfigFormat.YAML)
            
            # 加载配置
            demo_container = await loader.load_from_file(config_file)
            
            # 验证加载结果
            logger.info(f"配置加载完成，组件数: {len(demo_container.get_registered_components())}")
            
            # 获取用户服务
            demo_user_service = await demo_container.get_component("user_service")
            
            # 演示用户服务功能
            logger.info("演示用户服务功能...")
            
            # 模拟获取用户
            user = await demo_user_service.get_user("user123")
            logger.info(f"获取用户结果: {user}")
            
            # 获取缓存统计
            cache_stats = demo_user_service.cache.get_stats()
            logger.info(f"缓存统计: {cache_stats}")
            
            # 显示加载器统计
            loader_stats = loader.get_stats()
            logger.info(f"加载器统计: {loader_stats}")
            
            # 显示容器统计
            container_stats = demo_container.get_stats()
            logger.info(f"容器统计: {container_stats}")
            
        finally:
            # 清理临时文件
            os.unlink(config_file)
            if "DB_PASSWORD" in os.environ:
                del os.environ["DB_PASSWORD"]
        
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
    start_total = time.time()
    
    try:
        # 1. 变量解析器性能测试
        logger.info("1. 变量解析器性能测试...")
        resolver = VariableResolver(
            config_vars={"test": {"nested": {"value": "test_value"}}}
        )
        
        # 测试简单解析
        start = time.time()
        for i in range(1000):
            resolver.resolve("${test.nested.value}", {})
        duration = (time.time() - start) * 1000
        results["variable_resolver_simple"] = {
            "iterations": 1000,
            "total_ms": duration,
            "avg_ms": duration / 1000
        }
        
        # 测试复杂解析
        complex_value = {
            "var1": "${test.nested.value}",
            "var2": "${DEFAULT:default}",
            "nested": {
                "list": ["${test.nested.value}", "static", "${DEFAULT:test}"]
            }
        }
        
        start = time.time()
        for i in range(100):
            resolver.resolve(complex_value, {})
        duration = (time.time() - start) * 1000
        results["variable_resolver_complex"] = {
            "iterations": 100,
            "total_ms": duration,
            "avg_ms": duration / 100
        }
        
        # 2. 依赖注入容器性能测试
        logger.info("2. 依赖注入容器性能测试...")
        
        # 创建包含多个组件的容器
        container = DependencyContainer()
        
        # 注册多个组件
        for i in range(50):
            config = ComponentConfig(
                name=f"component_{i}",
                class_path="__main__:CacheService",  # 使用简单组件
                args={"max_size": i * 10, "ttl": 3600},
                dependencies=[f"component_{j}" for j in range(max(0, i-3), i)]  # 依赖前3个组件
            )
            container.register_component(config)
        
        # 测试初始化性能
        start = time.time()
        await container.initialize()
        duration = (time.time() - start) * 1000
        results["container_initialization"] = {
            "components": 50,
            "total_ms": duration,
            "avg_ms_per_component": duration / 50
        }
        
        # 测试获取组件性能
        start = time.time()
        for i in range(100):
            await container.get_component(f"component_{i % 50}")
        duration = (time.time() - start) * 1000
        results["component_retrieval"] = {
            "iterations": 100,
            "total_ms": duration,
            "avg_ms": duration / 100
        }
        
        # 3. 配置加载器性能测试
        logger.info("3. 配置加载器性能测试...")
        
        # 创建大型配置文件
        import tempfile
        config_content = "application: '性能测试'\ncomponents:\n"
        
        for i in range(20):
            config_content += f"  component_{i}:\n"
            config_content += f"    class: '__main__:CacheService'\n"
            config_content += f"    args:\n"
            config_content += f"      max_size: {i * 100}\n"
            config_content += f"      ttl: 3600\n"
            if i > 0:
                config_content += f"    dependencies:\n"
                config_content += f"      - component_{i-1}\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            bench_file = f.name
        
        try:
            loader = ConfigurationDrivenLoader()
            
            start = time.time()
            await loader.load_from_file(bench_file)
            duration = (time.time() - start) * 1000
            results["config_loading"] = {
                "components": 20,
                "total_ms": duration,
                "avg_ms_per_component": duration / 20
            }
            
        finally:
            os.unlink(bench_file)
        
        # 总耗时
        total_duration = (time.time() - start_total) * 1000
        results["total"] = {
            "total_ms": total_duration,
            "tests": len(results)
        }
        
        logger.info(f"性能基准测试完成，总耗时: {total_duration:.2f}ms")
        
        # 打印结果
        logger.info("\n性能基准测试结果:")
        for test_name, test_result in results.items():
            if "total_ms" in test_result:
                logger.info(f"  {test_name}: {test_result['total_ms']:.2f}ms")
        
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
    
    parser = argparse.ArgumentParser(description="配置驱动加载演示程序")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--bench", action="store_true", help="运行性能基准测试")
    parser.add_argument("--config", type=str, help="加载指定配置文件")
    
    args = parser.parse_args()
    
    # 默认运行演示
    if not any([args.test, args.demo, args.bench, args.config]):
        args.demo = True
    
    try:
        if args.test:
            logger.info("运行测试套件...")
            results = await TestConfigurationDrivenLoader.run_all_tests()
            
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
        
        if args.config:
            logger.info(f"加载配置文件: {args.config}")
            
            if not os.path.exists(args.config):
                logger.error(f"配置文件不存在: {args.config}")
                return 1
            
            # 根据文件扩展名确定格式
            ext = os.path.splitext(args.config)[1].lower()
            if ext in ['.json']:
                config_format = ConfigFormat.JSON
            elif ext in ['.yaml', '.yml']:
                config_format = ConfigFormat.YAML
            else:
                logger.warning(f"未知的文件扩展名: {ext}，默认使用YAML格式")
                config_format = ConfigFormat.YAML
            
            loader = ConfigurationDrivenLoader(config_format=config_format)
            container = await loader.load_from_file(args.config)
            
            logger.info(f"✅ 配置加载成功!")
            logger.info(f"   组件数: {len(container.get_registered_components())}")
            logger.info(f"   加载耗时: {loader.get_stats()['total_load_time_ms']:.2f}ms")
            
            # 显示加载的组件
            logger.info("   加载的组件:")
            for component in container.get_registered_components():
                config = container.registry[component]
                status = "✅" if config.enabled else "❌"
                logger.info(f"     {status} {component} ({config.class_path})")
            
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