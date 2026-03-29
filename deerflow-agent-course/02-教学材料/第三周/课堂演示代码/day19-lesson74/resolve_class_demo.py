#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeerFlow Python Agent架构师训练营 - 第74节课：resolve_class机制 演示代码

本文件演示了类解析（Class Resolution）机制的完整实现，包括：
1. ClassResolver类：支持动态类加载、模块导入、缓存机制
2. ConfigDrivenLoader类：配置驱动的组件加载和依赖注入
3. 完整测试套件：验证类解析和组件加载功能

学习目标：
- 掌握Python动态导入机制
- 理解类解析器设计模式
- 实现配置驱动的组件加载
- 掌握模块缓存和搜索路径管理

使用方式：
python resolve_class_demo.py          # 运行演示
python resolve_class_demo.py --test   # 运行测试套件
python resolve_class_demo.py --bench  # 运行性能基准测试
"""

import asyncio
import importlib
import sys
import logging
import time
from typing import Dict, List, Optional, Any, Type, Union
from types import ModuleType
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImportStrategy(Enum):
    """导入策略枚举"""
    STANDARD = "standard"      # 标准导入
    RELATIVE = "relative"      # 相对导入
    ABSOLUTE = "absolute"      # 绝对导入
    CACHED = "cached"          # 缓存导入


@dataclass
class ClassResolutionResult:
    """类解析结果"""
    success: bool
    cls: Optional[Type] = None
    module: Optional[ModuleType] = None
    class_path: str = ""
    duration_ms: float = 0.0
    cache_hit: bool = False
    error: Optional[str] = None
    
    def __str__(self) -> str:
        if self.success:
            return (f"ClassResolutionResult(success=True, "
                   f"class_path='{self.class_path}', "
                   f"cls={self.cls.__name__ if self.cls else 'None'}, "
                   f"duration={self.duration_ms:.2f}ms, "
                   f"cache_hit={self.cache_hit})")
        else:
            return (f"ClassResolutionResult(success=False, "
                   f"class_path='{self.class_path}', "
                   f"error='{self.error}', "
                   f"duration={self.duration_ms:.2f}ms)")


class ClassResolver:
    """
    类解析器 - 支持动态类加载和模块导入
    
    核心功能：
    1. 支持两种类路径格式：'module:Class' 或 'module.submodule.Class'
    2. 模块缓存和类缓存机制提升性能
    3. 搜索路径管理，支持自定义模块目录
    4. 错误处理和日志记录
    
    设计模式：工厂模式 + 缓存模式 + 策略模式
    """
    
    def __init__(self, search_paths: Optional[List[str]] = None, 
                 enable_cache: bool = True,
                 import_strategy: ImportStrategy = ImportStrategy.STANDARD):
        """
        初始化类解析器
        
        Args:
            search_paths: 搜索路径列表，用于动态导入自定义模块
            enable_cache: 是否启用缓存机制
            import_strategy: 导入策略
        """
        self.search_paths = search_paths or []
        self.enable_cache = enable_cache
        self.import_strategy = import_strategy
        
        # 缓存机制
        self.class_cache: Dict[str, Type] = {}
        self.module_cache: Dict[str, ModuleType] = {}
        
        # 统计信息
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "import_success": 0,
            "import_failures": 0,
            "total_resolution_time": 0.0
        }
        
        logger.info(f"初始化ClassResolver: search_paths={self.search_paths}, "
                   f"enable_cache={enable_cache}, import_strategy={import_strategy}")
    
    async def resolve(self, class_path: str) -> Type:
        """
        解析类路径，返回类对象
        
        Args:
            class_path: 类路径字符串，格式为'module:Class'或'module.submodule.Class'
        
        Returns:
            解析得到的类对象
        
        Raises:
            ValueError: 类路径格式无效、模块未找到或类未找到
        """
        start_time = time.time()
        
        try:
            # 1. 检查缓存（如果启用）
            if self.enable_cache and class_path in self.class_cache:
                self.stats["cache_hits"] += 1
                logger.debug(f"缓存命中: {class_path}")
                result = ClassResolutionResult(
                    success=True,
                    cls=self.class_cache[class_path],
                    class_path=class_path,
                    duration_ms=(time.time() - start_time) * 1000,
                    cache_hit=True
                )
                logger.info(f"类解析成功（缓存）: {result}")
                return result.cls
            
            self.stats["cache_misses"] += 1
            logger.info(f"解析类路径: {class_path}")
            
            # 2. 解析模块路径和类名
            module_path, class_name = self._parse_class_path(class_path)
            logger.debug(f"解析结果 -> 模块: {module_path}, 类: {class_name}")
            
            # 3. 动态导入模块
            module = await self._import_module(module_path)
            
            # 4. 获取类对象
            cls = self._get_class_from_module(module, class_name, class_path)
            
            # 5. 验证类对象
            self._validate_class(cls, class_path)
            
            # 6. 缓存结果（如果启用）
            if self.enable_cache:
                self.class_cache[class_path] = cls
            
            # 记录统计信息
            duration = (time.time() - start_time) * 1000
            self.stats["total_resolution_time"] += duration
            self.stats["import_success"] += 1
            
            result = ClassResolutionResult(
                success=True,
                cls=cls,
                module=module,
                class_path=class_path,
                duration_ms=duration,
                cache_hit=False
            )
            logger.info(f"类解析成功: {result}")
            
            return cls
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.stats["import_failures"] += 1
            
            result = ClassResolutionResult(
                success=False,
                class_path=class_path,
                duration_ms=duration,
                error=str(e)
            )
            logger.error(f"类解析失败: {result}")
            raise
    
    def _parse_class_path(self, class_path: str) -> tuple[str, str]:
        """
        解析类路径，提取模块路径和类名
        
        支持两种格式：
        1. 'module:Class' - 使用冒号分隔符
        2. 'module.submodule.Class' - 使用点分隔符（最后一个点之前是模块路径）
        
        Args:
            class_path: 类路径字符串
        
        Returns:
            (module_path, class_name) 元组
        """
        if ":" in class_path:
            # 格式: module:Class
            module_path, class_name = class_path.split(":", 1)
            if not module_path or not class_name:
                raise ValueError(f"无效的类路径格式: {class_path}，模块路径或类名为空")
            return module_path, class_name
        
        elif "." in class_path:
            # 格式: module.submodule.Class
            parts = class_path.split(".")
            if len(parts) < 2:
                raise ValueError(f"无效的类路径格式: {class_path}，至少需要一个模块和一个类")
            module_path = ".".join(parts[:-1])
            class_name = parts[-1]
            return module_path, class_name
        
        else:
            raise ValueError(f"无效的类路径格式: {class_path}，不支持无分隔符的格式")
    
    async def _import_module(self, module_path: str) -> ModuleType:
        """
        动态导入模块，支持搜索路径管理
        
        Args:
            module_path: 模块路径
        
        Returns:
            导入的模块对象
        
        Raises:
            ValueError: 模块导入失败
        """
        # 检查模块缓存
        if self.enable_cache and module_path in self.module_cache:
            logger.debug(f"模块缓存命中: {module_path}")
            return self.module_cache[module_path]
        
        logger.info(f"导入模块: {module_path}")
        
        # 保存原始sys.path
        original_sys_path = sys.path.copy()
        
        # 添加搜索路径
        for search_path in self.search_paths:
            if search_path not in sys.path:
                sys.path.insert(0, search_path)
        
        try:
            # 根据导入策略选择导入方式
            if self.import_strategy == ImportStrategy.CACHED:
                # 尝试从缓存导入（这里简化实现，实际可能需要更复杂的缓存策略）
                module = importlib.import_module(module_path)
            else:
                module = importlib.import_module(module_path)
            
            # 缓存模块
            if self.enable_cache:
                self.module_cache[module_path] = module
            
            logger.info(f"模块导入成功: {module_path}")
            return module
            
        except ImportError as e:
            logger.error(f"模块导入失败 {module_path}: {e}")
            
            # 尝试处理相对导入
            if module_path.startswith("."):
                # 相对导入需要调用者上下文，这里提供简化处理
                raise ValueError(f"相对导入需要调用者上下文: {module_path}")
            else:
                # 检查是否是模块不存在或路径问题
                error_msg = f"模块 {module_path} 未找到"
                if self.search_paths:
                    error_msg += f"，搜索路径: {self.search_paths}"
                error_msg += f"，原始错误: {e}"
                raise ValueError(error_msg)
                
        finally:
            # 恢复sys.path
            sys.path = original_sys_path
            logger.debug("恢复sys.path")
    
    def _get_class_from_module(self, module: ModuleType, class_name: str, 
                              class_path: str) -> Type:
        """
        从模块中获取类对象
        
        Args:
            module: 模块对象
            class_name: 类名
            class_path: 原始类路径（用于错误信息）
        
        Returns:
            类对象
        
        Raises:
            ValueError: 类未找到
        """
        if not hasattr(module, class_name):
            # 尝试在子模块中查找
            module_parts = class_path.split(":")
            if len(module_parts) > 1:
                module_name = module_parts[0]
                raise ValueError(f"模块 {module_name} 中未找到类 {class_name}")
            else:
                raise ValueError(f"模块 {module.__name__} 中未找到类 {class_name}")
        
        cls = getattr(module, class_name)
        return cls
    
    def _validate_class(self, cls: Type, class_path: str) -> None:
        """
        验证获取的对象确实是类
        
        Args:
            cls: 待验证的对象
            class_path: 类路径（用于错误信息）
        
        Raises:
            ValueError: 对象不是类
        """
        if not isinstance(cls, type):
            raise ValueError(f"{class_path} 不是类（类型: {type(cls).__name__}）")
        
        # 可选：验证类是否可实例化（不是抽象类等）
        # 这里简化实现，实际可能需要更复杂的检查
    
    async def create_instance(self, class_path: str, *args, **kwargs) -> Any:
        """
        创建类的实例
        
        Args:
            class_path: 类路径
            *args: 构造函数位置参数
            **kwargs: 构造函数关键字参数
        
        Returns:
            类的实例
        """
        cls = await self.resolve(class_path)
        
        try:
            instance = cls(*args, **kwargs)
            logger.info(f"创建实例: {class_path} with args={args}, kwargs={kwargs}")
            return instance
        except Exception as e:
            logger.error(f"实例创建失败 {class_path}: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取解析器统计信息
        
        Returns:
            统计信息字典
        """
        stats = self.stats.copy()
        stats.update({
            "cache_size": len(self.class_cache),
            "module_cache_size": len(self.module_cache),
            "search_paths": self.search_paths.copy(),
            "enable_cache": self.enable_cache,
            "import_strategy": self.import_strategy.value
        })
        
        # 计算平均解析时间
        total_operations = (stats["cache_hits"] + stats["cache_misses"])
        if total_operations > 0:
            stats["avg_resolution_time_ms"] = (
                stats["total_resolution_time"] / total_operations
            )
        else:
            stats["avg_resolution_time_ms"] = 0.0
        
        return stats
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.class_cache.clear()
        self.module_cache.clear()
        logger.info("清空类解析器缓存")
    
    def add_search_path(self, path: str) -> None:
        """
        添加搜索路径
        
        Args:
            path: 路径字符串
        """
        if path not in self.search_paths:
            self.search_paths.append(path)
            logger.info(f"添加搜索路径: {path}")


@dataclass
class ComponentConfig:
    """组件配置"""
    name: str
    class_path: str
    enabled: bool = True
    args: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    init_method: Optional[str] = None
    lazy_load: bool = False
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ComponentConfig':
        """从字典创建配置"""
        return cls(
            name=config_dict.get("name", ""),
            class_path=config_dict["class"],
            enabled=config_dict.get("enabled", True),
            args=config_dict.get("args", {}),
            dependencies=config_dict.get("dependencies", []),
            init_method=config_dict.get("init_method"),
            lazy_load=config_dict.get("lazy_load", False)
        )


class ConfigDrivenLoader:
    """
    配置驱动的组件加载器
    
    支持功能：
    1. 基于JSON/YAML配置动态加载组件
    2. 依赖注入和循环依赖检测
    3. 延迟加载和预加载策略
    4. 组件生命周期管理
    """
    
    def __init__(self, config: Dict[str, Any], 
                 class_resolver: Optional[ClassResolver] = None):
        """
        初始化配置驱动加载器
        
        Args:
            config: 组件配置字典
            class_resolver: 类解析器实例，如果为None则创建默认实例
        """
        self.config = config
        self.resolver = class_resolver or ClassResolver()
        
        # 组件实例缓存
        self.instances: Dict[str, Any] = {}
        
        # 加载状态跟踪
        self.loaded_components: List[str] = []
        self.loading_stack: List[str] = []  # 用于循环依赖检测
        
        logger.info(f"初始化ConfigDrivenLoader，配置键: {list(config.keys())}")
    
    async def load_components(self) -> Dict[str, Any]:
        """
        加载所有配置的组件
        
        Returns:
            组件名称到实例的映射
        
        Raises:
            ValueError: 组件加载失败或循环依赖
        """
        components_config = self.config.get("components", {})
        logger.info(f"开始加载 {len(components_config)} 个组件")
        
        # 首先创建所有组件配置对象
        component_configs: Dict[str, ComponentConfig] = {}
        for name, config_dict in components_config.items():
            component_configs[name] = ComponentConfig.from_dict(
                {"name": name, **config_dict}
            )
        
        # 按依赖顺序排序（拓扑排序）
        sorted_components = self._topological_sort(component_configs)
        logger.debug(f"依赖排序结果: {sorted_components}")
        
        # 按顺序加载组件
        for component_name in sorted_components:
            config = component_configs[component_name]
            
            if not config.enabled:
                logger.debug(f"跳过禁用组件: {component_name}")
                continue
            
            if config.lazy_load and component_name not in self.loading_stack:
                # 延迟加载，跳过现在加载
                logger.debug(f"标记为延迟加载: {component_name}")
                continue
            
            logger.info(f"加载组件: {component_name}")
            instance = await self._load_component(config)
            self.instances[component_name] = instance
            self.loaded_components.append(component_name)
        
        logger.info(f"组件加载完成，共 {len(self.instances)} 个实例")
        return self.instances.copy()
    
    def _topological_sort(self, components: Dict[str, ComponentConfig]) -> List[str]:
        """
        拓扑排序，解决组件依赖关系
        
        Args:
            components: 组件配置字典
        
        Returns:
            排序后的组件名称列表
        
        Raises:
            ValueError: 检测到循环依赖
        """
        # 构建邻接表和入度表
        adjacency: Dict[str, List[str]] = {name: [] for name in components}
        in_degree: Dict[str, int] = {name: 0 for name in components}
        
        for name, config in components.items():
            for dep in config.dependencies:
                if dep in components:
                    adjacency[dep].append(name)  # dep -> name 表示依赖关系
                    in_degree[name] += 1
        
        # 拓扑排序（Kahn算法）
        result: List[str] = []
        queue = [name for name, degree in in_degree.items() if degree == 0]
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查循环依赖
        if len(result) != len(components):
            # 找到未处理的节点（循环依赖）
            remaining = set(components.keys()) - set(result)
            raise ValueError(f"检测到循环依赖: {remaining}")
        
        return result
    
    async def _load_component(self, config: ComponentConfig) -> Any:
        """
        加载单个组件
        
        Args:
            config: 组件配置
        
        Returns:
            组件实例
        
        Raises:
            ValueError: 组件加载失败
        """
        # 循环依赖检测
        if config.name in self.loading_stack:
            raise ValueError(f"检测到循环依赖: {' -> '.join(self.loading_stack + [config.name])}")
        
        self.loading_stack.append(config.name)
        
        try:
            # 解析类
            cls = await self.resolver.resolve(config.class_path)
            logger.debug(f"组件 {config.name} 类解析成功: {cls}")
            
            # 准备构造函数参数
            constructor_args = await self._prepare_constructor_args(config.args)
            logger.debug(f"组件 {config.name} 构造参数: {constructor_args}")
            
            # 创建实例
            instance = cls(**constructor_args)
            
            # 调用初始化方法
            await self._initialize_component(instance, config)
            
            logger.info(f"组件加载成功: {config.name}")
            return instance
            
        finally:
            self.loading_stack.pop()
    
    async def _prepare_constructor_args(self, args_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备构造函数参数，支持参数解析和组件引用
        
        Args:
            args_config: 参数配置字典
        
        Returns:
            处理后的参数字典
        """
        args: Dict[str, Any] = {}
        
        for arg_name, arg_value in args_config.items():
            logger.debug(f"处理参数 {arg_name}: {arg_value}")
            
            if isinstance(arg_value, str):
                # 字符串参数处理
                if arg_value.startswith("$"):
                    # 表达式参数（简化实现）
                    # 实际实现中会调用VariableResolver
                    args[arg_name] = arg_value[1:]  # 移除$符号
                    logger.debug(f"表达式参数 {arg_name} -> {args[arg_name]}")
                    
                elif arg_value.startswith("@"):
                    # 环境变量引用
                    env_var = arg_value[1:]
                    args[arg_name] = os.getenv(env_var, "")
                    logger.debug(f"环境变量参数 {arg_name} -> {args[arg_name]}")
                    
                else:
                    # 普通字符串
                    args[arg_name] = arg_value
                    logger.debug(f"字符串参数 {arg_name} -> {arg_value}")
                    
            elif isinstance(arg_value, dict):
                # 字典参数处理
                if "ref" in arg_value:
                    # 组件引用
                    ref_name = arg_value["ref"]
                    if ref_name in self.instances:
                        args[arg_name] = self.instances[ref_name]
                        logger.debug(f"组件引用参数 {arg_name} -> {ref_name}")
                    else:
                        # 尝试延迟加载
                        logger.debug(f"尝试延迟加载引用组件: {ref_name}")
                        # 这里简化实现，实际可能需要触发延迟加载
                        raise ValueError(f"组件引用 {ref_name} 未找到（可能尚未加载）")
                        
                elif "value" in arg_value:
                    # 显式值
                    args[arg_name] = arg_value["value"]
                    logger.debug(f"显式值参数 {arg_name} -> {args[arg_name]}")
                    
                else:
                    # 普通字典
                    args[arg_name] = arg_value
                    logger.debug(f"字典参数 {arg_name} -> {arg_value}")
                    
            else:
                # 其他类型（数字、列表等）
                args[arg_name] = arg_value
                logger.debug(f"字面值参数 {arg_name} -> {arg_value}")
        
        return args
    
    async def _initialize_component(self, instance: Any, config: ComponentConfig) -> None:
        """
        初始化组件，调用初始化方法
        
        Args:
            instance: 组件实例
            config: 组件配置
        """
        init_method_name = config.init_method or "initialize"
        
        if hasattr(instance, init_method_name):
            init_method = getattr(instance, init_method_name)
            
            if asyncio.iscoroutinefunction(init_method):
                logger.debug(f"异步初始化组件: {config.name}")
                await init_method()
            else:
                logger.debug(f"同步初始化组件: {config.name}")
                init_method()
    
    async def get_component(self, name: str) -> Any:
        """
        获取已加载的组件
        
        Args:
            name: 组件名称
        
        Returns:
            组件实例
        
        Raises:
            KeyError: 组件未找到
        """
        if name not in self.instances:
            raise KeyError(f"组件 {name} 未加载")
        
        return self.instances[name]
    
    async def lazy_load_component(self, name: str) -> Any:
        """
        延迟加载组件
        
        Args:
            name: 组件名称
        
        Returns:
            组件实例
        """
        if name in self.instances:
            return self.instances[name]
        
        # 从配置中查找组件
        components_config = self.config.get("components", {})
        if name not in components_config:
            raise KeyError(f"组件 {name} 未在配置中定义")
        
        config_dict = components_config[name]
        config = ComponentConfig.from_dict({"name": name, **config_dict})
        
        logger.info(f"延迟加载组件: {name}")
        instance = await self._load_component(config)
        self.instances[name] = instance
        
        return instance
    
    def get_loading_status(self) -> Dict[str, Any]:
        """
        获取加载状态
        
        Returns:
            状态信息字典
        """
        return {
            "loaded_components": self.loaded_components.copy(),
            "total_instances": len(self.instances),
            "loading_stack": self.loading_stack.copy(),
            "config_keys": list(self.config.keys())
        }


# ============================================================================
# 示例组件类（用于演示）
# ============================================================================

class DatabaseConnector:
    """数据库连接器示例"""
    
    def __init__(self, host: str = "localhost", port: int = 5432, 
                 database: str = "mydb"):
        self.host = host
        self.port = port
        self.database = database
        self.connected = False
    
    async def initialize(self):
        """初始化连接"""
        logger.info(f"初始化数据库连接: {self.host}:{self.port}/{self.database}")
        # 模拟连接延迟
        await asyncio.sleep(0.1)
        self.connected = True
    
    def query(self, sql: str):
        """执行查询"""
        if not self.connected:
            raise RuntimeError("数据库未连接")
        logger.info(f"执行查询: {sql}")
        return {"result": "success"}


class CacheProvider:
    """缓存提供者示例"""
    
    def __init__(self, host: str = "localhost", port: int = 6379,
                 max_size: int = 1000):
        self.host = host
        self.port = port
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        if len(self.cache) >= self.max_size:
            # 简单LRU实现：移除第一个键
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        
        self.cache[key] = value
        logger.debug(f"设置缓存: {key} = {value}")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        return self.cache.get(key)


class MessageQueue:
    """消息队列示例"""
    
    def __init__(self, broker_url: str = "amqp://localhost",
                 queue_name: str = "default"):
        self.broker_url = broker_url
        self.queue_name = queue_name
        self.messages: List[Dict[str, Any]] = []
    
    async def publish(self, message: Dict[str, Any]):
        """发布消息"""
        self.messages.append(message)
        logger.info(f"发布消息到 {self.queue_name}: {message}")
        await asyncio.sleep(0.05)  # 模拟网络延迟
    
    async def consume(self) -> Optional[Dict[str, Any]]:
        """消费消息"""
        if self.messages:
            message = self.messages.pop(0)
            logger.info(f"消费消息: {message}")
            return message
        return None


# ============================================================================
# 测试套件
# ============================================================================

import unittest
from unittest.mock import Mock, patch, MagicMock


class TestClassResolver(unittest.TestCase):
    """ClassResolver测试类"""
    
    def setUp(self):
        self.resolver = ClassResolver(enable_cache=True)
    
    def test_parse_class_path_colon_format(self):
        """测试冒号格式解析"""
        module_path, class_name = self.resolver._parse_class_path("module:Class")
        self.assertEqual(module_path, "module")
        self.assertEqual(class_name, "Class")
    
    def test_parse_class_path_dot_format(self):
        """测试点格式解析"""
        module_path, class_name = self.resolver._parse_class_path("module.submodule.Class")
        self.assertEqual(module_path, "module.submodule")
        self.assertEqual(class_name, "Class")
    
    def test_parse_invalid_format(self):
        """测试无效格式"""
        with self.assertRaises(ValueError):
            self.resolver._parse_class_path("InvalidFormat")
    
    def test_parse_empty_parts(self):
        """测试空部分"""
        with self.assertRaises(ValueError):
            self.resolver._parse_class_path("module:")
    
    async def test_resolve_builtin_class(self):
        """测试解析内置类"""
        # 注意：这里使用asyncio.run包装异步测试
        cls = await self.resolver.resolve("datetime:datetime")
        self.assertTrue(isinstance(cls, type))
        self.assertEqual(cls.__name__, "datetime")
    
    async def test_resolve_with_cache(self):
        """测试缓存机制"""
        # 第一次解析（缓存未命中）
        cls1 = await self.resolver.resolve("datetime:datetime")
        stats1 = self.resolver.get_stats()
        self.assertEqual(stats1["cache_misses"], 1)
        
        # 第二次解析（缓存命中）
        cls2 = await self.resolver.resolve("datetime:datetime")
        stats2 = self.resolver.get_stats()
        self.assertEqual(stats2["cache_hits"], 1)
        
        # 确保是同一个类对象
        self.assertIs(cls1, cls2)
    
    async def test_resolve_nonexistent_class(self):
        """测试解析不存在的类"""
        with self.assertRaises(ValueError):
            await self.resolver.resolve("nonexistent.module:NonExistentClass")
    
    async def test_create_instance(self):
        """测试创建实例"""
        instance = await self.resolver.create_instance(
            "datetime:datetime", 2024, 4, 12
        )
        self.assertEqual(instance.year, 2024)
        self.assertEqual(instance.month, 4)
        self.assertEqual(instance.day, 12)
    
    def test_add_search_path(self):
        """测试添加搜索路径"""
        initial_count = len(self.resolver.search_paths)
        self.resolver.add_search_path("/custom/path")
        self.assertEqual(len(self.resolver.search_paths), initial_count + 1)
        self.assertIn("/custom/path", self.resolver.search_paths)


class TestConfigDrivenLoader(unittest.TestCase):
    """ConfigDrivenLoader测试类"""
    
    def setUp(self):
        # 创建测试配置
        self.config = {
            "components": {
                "database": {
                    "class": "resolve_class_demo:DatabaseConnector",
                    "args": {
                        "host": "localhost",
                        "port": 5432,
                        "database": "testdb"
                    }
                },
                "cache": {
                    "class": "resolve_class_demo:CacheProvider",
                    "args": {
                        "host": "redis.local",
                        "port": 6379,
                        "max_size": 500
                    },
                    "dependencies": ["database"]
                }
            }
        }
        
        self.resolver = ClassResolver()
        self.loader = ConfigDrivenLoader(self.config, self.resolver)
    
    async def test_load_components(self):
        """测试加载组件"""
        components = await self.loader.load_components()
        
        self.assertIn("database", components)
        self.assertIn("cache", components)
        
        # 验证组件类型
        self.assertIsInstance(components["database"], DatabaseConnector)
        self.assertIsInstance(components["cache"], CacheProvider)
        
        # 验证参数
        self.assertEqual(components["database"].host, "localhost")
        self.assertEqual(components["cache"].max_size, 500)
    
    async def test_get_component(self):
        """测试获取组件"""
        await self.loader.load_components()
        
        db = await self.loader.get_component("database")
        self.assertIsInstance(db, DatabaseConnector)
        
        # 测试获取不存在的组件
        with self.assertRaises(KeyError):
            await self.loader.get_component("nonexistent")
    
    async def test_component_dependencies(self):
        """测试组件依赖"""
        # 修改配置，添加依赖关系
        self.config["components"]["cache"]["dependencies"] = ["database"]
        
        components = await self.loader.load_components()
        
        # 验证依赖解析
        status = self.loader.get_loading_status()
        # database应该在cache之前加载
        db_index = status["loaded_components"].index("database")
        cache_index = status["loaded_components"].index("cache")
        self.assertLess(db_index, cache_index)
    
    async def test_circular_dependency_detection(self):
        """测试循环依赖检测"""
        # 创建循环依赖配置
        circular_config = {
            "components": {
                "service_a": {
                    "class": "resolve_class_demo:DatabaseConnector",
                    "dependencies": ["service_b"]
                },
                "service_b": {
                    "class": "resolve_class_demo:CacheProvider",
                    "dependencies": ["service_a"]  # 循环依赖
                }
            }
        }
        
        loader = ConfigDrivenLoader(circular_config)
        
        with self.assertRaises(ValueError) as context:
            await loader.load_components()
        
        self.assertIn("循环依赖", str(context.exception))
    
    async def test_lazy_load_component(self):
        """测试延迟加载"""
        # 设置组件为延迟加载
        self.config["components"]["database"]["lazy_load"] = True
        
        loader = ConfigDrivenLoader(self.config)
        
        # 初始状态下组件不应加载
        status = loader.get_loading_status()
        self.assertNotIn("database", status["loaded_components"])
        
        # 延迟加载
        db = await loader.lazy_load_component("database")
        self.assertIsInstance(db, DatabaseConnector)
        
        # 验证现在已加载
        status = loader.get_loading_status()
        self.assertIn("database", status["loaded_components"])


# ============================================================================
# 演示函数
# ============================================================================

async def demo_basic_resolution():
    """基本类解析演示"""
    print("=" * 60)
    print("基本类解析演示")
    print("=" * 60)
    
    resolver = ClassResolver(enable_cache=True)
    
    # 1. 解析内置类
    print("1. 解析内置类 (datetime:datetime)")
    datetime_cls = await resolver.resolve("datetime:datetime")
    print(f"   解析成功: {datetime_cls}")
    
    # 2. 创建实例
    print("\n2. 创建datetime实例")
    dt_instance = await resolver.create_instance("datetime:datetime", 2024, 4, 12)
    print(f"   实例创建成功: {dt_instance}")
    
    # 3. 缓存测试
    print("\n3. 缓存机制测试")
    start_time = time.time()
    await resolver.resolve("datetime:datetime")  # 第一次（缓存未命中）
    first_time = (time.time() - start_time) * 1000
    
    start_time = time.time()
    await resolver.resolve("datetime:datetime")  # 第二次（缓存命中）
    second_time = (time.time() - start_time) * 1000
    
    print(f"   第一次解析: {first_time:.2f}ms")
    print(f"   第二次解析: {second_time:.2f}ms")
    print(f"   性能提升: {(first_time - second_time) / first_time * 100:.1f}%")
    
    # 4. 显示统计信息
    print("\n4. 解析器统计信息:")
    stats = resolver.get_stats()
    for key, value in stats.items():
        if key not in ["search_paths"]:
            print(f"   {key}: {value}")
    
    print("\n演示完成!")


async def demo_config_driven_loading():
    """配置驱动加载演示"""
    print("\n" + "=" * 60)
    print("配置驱动加载演示")
    print("=" * 60)
    
    # 创建复杂配置
    config = {
        "application": "微服务示例",
        "version": "1.0.0",
        "components": {
            "database": {
                "enabled": True,
                "class": "resolve_class_demo:DatabaseConnector",
                "args": {
                    "host": "db.example.com",
                    "port": 5432,
                    "database": "production_db"
                },
                "init_method": "initialize"
            },
            "cache": {
                "enabled": True,
                "class": "resolve_class_demo:CacheProvider",
                "args": {
                    "host": "redis.example.com",
                    "port": 6379,
                    "max_size": 10000
                },
                "dependencies": ["database"]
            },
            "message_queue": {
                "enabled": True,
                "class": "resolve_class_demo:MessageQueue",
                "args": {
                    "broker_url": "amqp://mq.example.com",
                    "queue_name": "tasks"
                },
                "lazy_load": True
            }
        }
    }
    
    print("1. 创建配置驱动加载器")
    resolver = ClassResolver()
    loader = ConfigDrivenLoader(config, resolver)
    
    print("\n2. 加载所有组件")
    components = await loader.load_components()
    print(f"   已加载组件: {list(components.keys())}")
    
    print("\n3. 获取和验证组件")
    db = await loader.get_component("database")
    print(f"   数据库组件: {db.host}:{db.port}/{db.database}")
    print(f"   连接状态: {db.connected}")
    
    cache = await loader.get_component("cache")
    print(f"   缓存组件: {cache.host}:{db.port}")
    print(f"   缓存最大大小: {cache.max_size}")
    
    print("\n4. 延迟加载演示")
    print("   消息队列组件配置为延迟加载...")
    mq = await loader.lazy_load_component("message_queue")
    print(f"   消息队列组件: {mq.broker_url}")
    print(f"   队列名称: {mq.queue_name}")
    
    print("\n5. 加载状态")
    status = loader.get_loading_status()
    print(f"   已加载组件列表: {status['loaded_components']}")
    print(f"   总实例数: {status['total_instances']}")
    
    print("\n演示完成!")


async def demo_advanced_features():
    """高级功能演示"""
    print("\n" + "=" * 60)
    print("高级功能演示")
    print("=" * 60)
    
    # 1. 自定义搜索路径
    print("1. 自定义搜索路径演示")
    resolver = ClassResolver(search_paths=["./lib", "./plugins"])
    print(f"   搜索路径: {resolver.search_paths}")
    
    # 2. 不同导入策略
    print("\n2. 不同导入策略")
    strategies = [ImportStrategy.STANDARD, ImportStrategy.CACHED]
    
    for strategy in strategies:
        resolver = ClassResolver(import_strategy=strategy, enable_cache=True)
        start_time = time.time()
        
        try:
            await resolver.resolve("datetime:datetime")
            await resolver.resolve("json:JSONEncoder")
            duration = (time.time() - start_time) * 1000
            
            stats = resolver.get_stats()
            print(f"   策略 {strategy.value}: {duration:.2f}ms, "
                  f"缓存命中率: {stats['cache_hits']/(stats['cache_hits']+stats['cache_misses'])*100:.1f}%")
        except Exception as e:
            print(f"   策略 {strategy.value}: 错误 - {e}")
    
    # 3. 性能基准测试
    print("\n3. 性能基准测试")
    resolver = ClassResolver(enable_cache=True)
    
    test_paths = [
        "datetime:datetime",
        "json:JSONEncoder",
        "collections:defaultdict",
        "typing:Dict"
    ]
    
    print("   预热缓存...")
    for path in test_paths:
        try:
            await resolver.resolve(path)
        except:
            pass
    
    print("   基准测试开始...")
    iterations = 100
    start_time = time.time()
    
    for i in range(iterations):
        for path in test_paths:
            try:
                await resolver.resolve(path)
            except:
                pass
    
    total_time = (time.time() - start_time) * 1000
    avg_time = total_time / (iterations * len(test_paths))
    
    stats = resolver.get_stats()
    cache_hit_rate = stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses']) * 100
    
    print(f"   总时间: {total_time:.2f}ms")
    print(f"   平均每次解析: {avg_time:.2f}ms")
    print(f"   缓存命中率: {cache_hit_rate:.1f}%")
    
    print("\n演示完成!")


async def run_all_demos():
    """运行所有演示"""
    print("🚀 DeerFlow类解析机制演示开始")
    print("=" * 60)
    
    await demo_basic_resolution()
    await demo_config_driven_loading()
    await demo_advanced_features()
    
    print("\n" + "=" * 60)
    print("🎉 所有演示完成！")
    print("=" * 60)


# ============================================================================
# 命令行接口
# ============================================================================

async def run_tests():
    """运行测试套件"""
    print("运行测试套件...")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    
    # 添加测试类
    test_classes = [
        TestClassResolver,
        TestConfigDrivenLoader
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


async def run_benchmarks():
    """运行性能基准测试"""
    print("运行性能基准测试...")
    
    resolver = ClassResolver(enable_cache=True)
    
    # 测试数据
    test_cases = [
        ("简单解析", ["datetime:datetime", "json:JSONEncoder"]),
        ("多次解析", ["datetime:datetime"] * 10),
        ("混合解析", ["datetime:datetime", "json:JSONEncoder", "collections:defaultdict"] * 5)
    ]
    
    results = []
    
    for test_name, paths in test_cases:
        print(f"\n测试: {test_name}")
        
        # 清空缓存
        resolver.clear_cache()
        
        # 第一次运行（冷启动）
        start_time = time.time()
        for path in paths:
            try:
                await resolver.resolve(path)
            except:
                pass
        cold_time = (time.time() - start_time) * 1000
        
        # 第二次运行（热缓存）
        start_time = time.time()
        for path in paths:
            try:
                await resolver.resolve(path)
            except:
                pass
        hot_time = (time.time() - start_time) * 1000
        
        # 计算性能提升
        improvement = ((cold_time - hot_time) / cold_time * 100) if cold_time > 0 else 0
        
        results.append({
            "test": test_name,
            "cold_time_ms": cold_time,
            "hot_time_ms": hot_time,
            "improvement_percent": improvement,
            "cache_hits": resolver.get_stats()["cache_hits"]
        })
        
        print(f"  冷启动: {cold_time:.2f}ms")
        print(f"  热缓存: {hot_time:.2f}ms")
        print(f"  性能提升: {improvement:.1f}%")
        print(f"  缓存命中: {resolver.get_stats()['cache_hits']}")
    
    # 输出总结
    print("\n" + "=" * 60)
    print("性能基准测试总结")
    print("=" * 60)
    
    for result in results:
        print(f"{result['test']}:")
        print(f"  冷启动: {result['cold_time_ms']:.2f}ms")
        print(f"  热缓存: {result['hot_time_ms']:.2f}ms")
        print(f"  提升: {result['improvement_percent']:.1f}%")
    
    return True


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="DeerFlow类解析机制演示程序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s               # 运行所有演示
  %(prog)s --test        # 运行测试套件
  %(prog)s --bench       # 运行性能基准测试
  %(prog)s --demo basic  # 只运行基本演示
        """
    )
    
    parser.add_argument(
        "--test", 
        action="store_true",
        help="运行测试套件"
    )
    
    parser.add_argument(
        "--bench",
        action="store_true",
        help="运行性能基准测试"
    )
    
    parser.add_argument(
        "--demo",
        choices=["all", "basic", "config", "advanced"],
        default="all",
        help="选择要运行的演示 (默认: all)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="启用详细日志输出"
    )
    
    args = parser.parse_args()
    
    # 配置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    try:
        if args.test:
            # 运行测试
            success = asyncio.run(run_tests())
            sys.exit(0 if success else 1)
        
        elif args.bench:
            # 运行基准测试
            asyncio.run(run_benchmarks())
        
        else:
            # 运行演示
            if args.demo == "all":
                asyncio.run(run_all_demos())
            elif args.demo == "basic":
                asyncio.run(demo_basic_resolution())
            elif args.demo == "config":
                asyncio.run(demo_config_driven_loading())
            elif args.demo == "advanced":
                asyncio.run(demo_advanced_features())
    
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()