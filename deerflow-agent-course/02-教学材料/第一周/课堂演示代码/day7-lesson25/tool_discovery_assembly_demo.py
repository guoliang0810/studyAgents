#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 7 Lesson 25: 工具发现与装配系统 - 课堂演示代码

本文件演示DeerFlow工具系统的完整发现与装配机制，采用四部分结构：
第一部分：概念与设计原则 - 定义核心接口和设计模式
第二部分：工具发现实现 - 实现动态路径扫描和模块导入
第三部分：工具装配系统 - 实现工具加载、实例化和注册
第四部分：测试与演示 - 提供完整的测试套件和演示程序

核心功能：
1. 动态工具发现：扫描指定路径，自动发现工具模块和类
2. 安全模块导入：使用importlib动态导入，支持错误隔离
3. 工具装配：实例化工具类，配置参数，注册到系统
4. 统一接口：所有工具实现BaseTool接口，支持统一调用
5. 配置管理：支持工具过滤、优先级配置、依赖解析

使用场景：
- 插件化系统：动态加载用户开发的工具插件
- 模块化架构：按需加载功能模块，减少内存占用
- 热插拔：运行时添加或移除工具，无需重启系统
- 沙箱环境：安全执行第三方工具，防止系统破坏

学习目标：
1. 掌握Python动态导入机制（importlib）
2. 理解插件化架构设计模式
3. 实现安全的类扫描和实例化
4. 设计可扩展的工具管理系统
"""

import asyncio
import importlib
import inspect
import logging
import pkgutil
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================


class ToolDesignPrinciple(Enum):
    """工具系统五大设计原则枚举"""

    DYNAMIC_DISCOVERY = "dynamic_discovery"  # 动态发现：运行时扫描和加载
    UNIFIED_INTERFACE = "unified_interface"  # 统一接口：标准工具接口
    SAFE_SANDBOX = "safe_sandbox"  # 安全沙箱：受限执行环境
    CONFIGURABILITY = "configurability"  # 可配置性：灵活配置选项
    ERROR_ISOLATION = "error_isolation"  # 错误隔离：失败不影响系统


class ToolCategory(Enum):
    """工具类别枚举，用于分类和组织工具"""

    UTILITY = "utility"  # 实用工具：文件操作、字符串处理等
    NETWORK = "network"  # 网络工具：HTTP请求、API调用等
    DATABASE = "database"  # 数据库工具：查询、事务等
    AI_MODEL = "ai_model"  # AI模型工具：LLM调用、推理等
    SYSTEM = "system"  # 系统工具：进程管理、监控等
    CUSTOM = "custom"  # 自定义工具：用户特定需求


@dataclass
class ToolMetadata:
    """工具元数据，描述工具的基本信息和能力"""

    name: str  # 工具名称（唯一标识）
    description: str  # 工具描述
    version: str = "1.0.0"  # 工具版本
    author: str = "unknown"  # 作者信息
    category: ToolCategory = ToolCategory.UTILITY  # 工具类别
    tags: List[str] = field(default_factory=list)  # 标签，用于搜索和过滤
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他工具
    required_parameters: List[str] = field(default_factory=list)  # 必需参数
    optional_parameters: List[str] = field(default_factory=list)  # 可选参数
    return_type: str = "Any"  # 返回值类型描述
    timeout_seconds: int = 30  # 超时时间（秒）
    memory_limit_mb: int = 100  # 内存限制（MB）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "category": self.category.value,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "required_parameters": self.required_parameters,
            "optional_parameters": self.optional_parameters,
            "return_type": self.return_type,
            "timeout_seconds": self.timeout_seconds,
            "memory_limit_mb": self.memory_limit_mb,
        }


class BaseTool(ABC):
    """工具基类，所有工具必须继承此基类

    设计原则：统一接口 (UNIFIED_INTERFACE)
    所有工具提供统一的调用接口，便于系统管理和调用。
    """

    # 类属性：工具元数据
    metadata: ToolMetadata

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化工具

        Args:
            config: 工具配置字典，可以包含工具所需的参数
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"tool.{self.metadata.name}")
        self._initialized = False

    async def initialize(self) -> None:
        """初始化工具，执行必要的准备工作

        设计原则：错误隔离 (ERROR_ISOLATION)
        初始化失败不影响其他工具，系统可以继续使用其他工具。
        """
        try:
            await self._initialize_impl()
            self._initialized = True
            self.logger.info(f"工具 {self.metadata.name} 初始化成功")
        except Exception as e:
            self.logger.error(f"工具 {self.metadata.name} 初始化失败: {e}")
            raise

    @abstractmethod
    async def _initialize_impl(self) -> None:
        """工具特定的初始化实现，子类必须实现"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """执行工具的主要功能

        Args:
            **kwargs: 工具执行参数

        Returns:
            Any: 工具执行结果

        Raises:
            ToolExecutionError: 工具执行失败时抛出
        """
        pass

    async def cleanup(self) -> None:
        """清理工具资源

        设计原则：安全沙箱 (SAFE_SANDBOX)
        确保工具执行后清理所有资源，防止资源泄漏。
        """
        try:
            await self._cleanup_impl()
            self.logger.info(f"工具 {self.metadata.name} 清理完成")
        except Exception as e:
            self.logger.error(f"工具 {self.metadata.name} 清理失败: {e}")

    async def _cleanup_impl(self) -> None:
        """工具特定的清理实现，子类可以重写"""
        pass

    def is_initialized(self) -> bool:
        """检查工具是否已初始化"""
        return self._initialized

    def validate_parameters(self, **kwargs) -> Tuple[bool, List[str]]:
        """验证参数是否满足工具要求

        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误消息列表)
        """
        errors = []

        # 检查必需参数
        for param in self.metadata.required_parameters:
            if param not in kwargs:
                errors.append(f"缺少必需参数: {param}")

        # 检查参数类型（简化版本，实际可以更复杂）
        # 这里只是示例，实际实现可以根据metadata中的类型信息验证

        return len(errors) == 0, errors


class ToolExecutionError(Exception):
    """工具执行异常"""

    def __init__(
        self, tool_name: str, message: str, original_error: Optional[Exception] = None
    ):
        self.tool_name = tool_name
        self.message = message
        self.original_error = original_error
        super().__init__(f"工具 {tool_name} 执行失败: {message}")


# ============================================================================
# 第二部分：工具发现实现
# ============================================================================


class DiscoveryStrategy(Enum):
    """工具发现策略枚举"""

    PATH_SCAN = "path_scan"  # 路径扫描：扫描指定目录
    MODULE_SCAN = "module_scan"  # 模块扫描：扫描已安装模块
    HYBRID = "hybrid"  # 混合策略：结合路径和模块扫描
    CACHED = "cached"  # 缓存发现：使用缓存结果，提高性能


@dataclass
class DiscoveryConfig:
    """工具发现配置"""

    strategy: DiscoveryStrategy = DiscoveryStrategy.PATH_SCAN
    scan_paths: List[str] = field(default_factory=lambda: ["."])  # 扫描路径
    recursive: bool = True  # 是否递归扫描
    include_patterns: List[str] = field(default_factory=lambda: ["*.py"])  # 包含模式
    exclude_patterns: List[str] = field(
        default_factory=lambda: ["test_*.py", "*_test.py"]
    )  # 排除模式
    follow_symlinks: bool = False  # 是否跟踪符号链接
    max_depth: int = 5  # 最大扫描深度
    cache_enabled: bool = True  # 是否启用缓存
    cache_ttl_seconds: int = 3600  # 缓存有效期（秒）

    def validate(self) -> Tuple[bool, List[str]]:
        """验证配置有效性"""
        errors = []

        if not self.scan_paths:
            errors.append("扫描路径不能为空")

        for path in self.scan_paths:
            if not Path(path).exists():
                errors.append(f"路径不存在: {path}")

        if self.max_depth < 1:
            errors.append(f"最大深度必须大于0: {self.max_depth}")

        if self.cache_ttl_seconds < 0:
            errors.append(f"缓存TTL不能为负数: {self.cache_ttl_seconds}")

        return len(errors) == 0, errors


class ToolDiscovery:
    """工具发现器，负责扫描路径发现工具类

    设计原则：动态发现 (DYNAMIC_DISCOVERY)
    运行时扫描指定路径，自动发现和加载工具类，支持热插拔。
    """

    def __init__(self, config: Optional[DiscoveryConfig] = None):
        """初始化工具发现器

        Args:
            config: 发现配置，如果为None则使用默认配置
        """
        self.config = config or DiscoveryConfig()
        self.logger = logging.getLogger("discovery")
        self._discovered_tools: Dict[str, Type[BaseTool]] = {}
        self._discovery_cache: Dict[
            str, Tuple[float, List[Type[BaseTool]]]
        ] = {}  # 缓存：路径 -> (时间戳, 工具列表)
        self._validate_config()

    def _validate_config(self) -> None:
        """验证配置"""
        is_valid, errors = self.config.validate()
        if not is_valid:
            error_msg = "发现配置无效: " + "; ".join(errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)

    def discover_tools(self) -> List[Type[BaseTool]]:
        """发现工具类

        根据配置策略发现工具类，返回发现的所有工具类。

        Returns:
            List[Type[BaseTool]]: 发现的工具类列表

        Raises:
            DiscoveryError: 发现过程失败时抛出
        """
        start_time = time.time()
        self.logger.info(f"开始工具发现，策略: {self.config.strategy.value}")

        discovered = []

        try:
            if self.config.strategy == DiscoveryStrategy.PATH_SCAN:
                discovered = self._discover_by_path_scan()
            elif self.config.strategy == DiscoveryStrategy.MODULE_SCAN:
                discovered = self._discover_by_module_scan()
            elif self.config.strategy == DiscoveryStrategy.HYBRID:
                discovered = self._discover_hybrid()
            elif self.config.strategy == DiscoveryStrategy.CACHED:
                discovered = self._discover_cached()
            else:
                raise ValueError(f"不支持的发现策略: {self.config.strategy}")

            # 更新缓存
            if self.config.cache_enabled:
                cache_key = self._get_cache_key()
                self._discovery_cache[cache_key] = (time.time(), discovered)

            # 更新内部状态
            for tool_class in discovered:
                self._discovered_tools[tool_class.metadata.name] = tool_class

            elapsed = time.time() - start_time
            self.logger.info(
                f"工具发现完成，发现 {len(discovered)} 个工具，耗时 {elapsed:.2f} 秒"
            )

            return discovered

        except Exception as e:
            self.logger.error(f"工具发现失败: {e}")
            raise DiscoveryError(f"工具发现失败: {e}")

    def _discover_by_path_scan(self) -> List[Type[BaseTool]]:
        """通过路径扫描发现工具"""
        discovered = []

        for scan_path in self.config.scan_paths:
            path_obj = Path(scan_path).resolve()

            if not path_obj.exists():
                self.logger.warning(f"扫描路径不存在，跳过: {scan_path}")
                continue

            if path_obj.is_file():
                # 单个文件
                tools = self._scan_file(path_obj)
                discovered.extend(tools)
            else:
                # 目录
                tools = self._scan_directory(path_obj)
                discovered.extend(tools)

        return discovered

    def _scan_directory(self, directory: Path) -> List[Type[BaseTool]]:
        """扫描目录发现工具"""
        discovered = []

        # 构建文件列表
        files = []

        if self.config.recursive:
            # 递归扫描
            for pattern in self.config.include_patterns:
                for file_path in directory.rglob(pattern):
                    # 检查排除模式
                    if self._should_exclude(file_path):
                        continue

                    # 检查深度限制
                    if self.config.max_depth > 0:
                        depth = len(file_path.relative_to(directory).parts)
                        if depth > self.config.max_depth:
                            continue

                    files.append(file_path)
        else:
            # 非递归扫描
            for pattern in self.config.include_patterns:
                for file_path in directory.glob(pattern):
                    if self._should_exclude(file_path):
                        continue
                    files.append(file_path)

        # 扫描每个文件
        for file_path in files:
            try:
                tools = self._scan_file(file_path)
                discovered.extend(tools)
            except Exception as e:
                self.logger.warning(f"扫描文件失败 {file_path}: {e}")
                continue

        return discovered

    def _should_exclude(self, file_path: Path) -> bool:
        """检查文件是否应该被排除"""
        filename = file_path.name

        for exclude_pattern in self.config.exclude_patterns:
            # 简单的通配符匹配（实际可以使用fnmatch）
            if exclude_pattern.startswith("*") and exclude_pattern.endswith("*"):
                pattern = exclude_pattern[1:-1]
                if pattern in filename:
                    return True
            elif exclude_pattern.startswith("*"):
                if filename.endswith(exclude_pattern[1:]):
                    return True
            elif exclude_pattern.endswith("*"):
                if filename.startswith(exclude_pattern[:-1]):
                    return True
            else:
                if filename == exclude_pattern:
                    return True

        return False

    def _scan_file(self, file_path: Path) -> List[Type[BaseTool]]:
        """扫描单个文件发现工具类"""
        # 检查文件扩展名
        if file_path.suffix != ".py":
            return []

        # 转换为模块名
        try:
            module_name = self._path_to_module_name(file_path)
        except ValueError as e:
            self.logger.warning(f"无法转换路径为模块名 {file_path}: {e}")
            return []

        # 动态导入模块
        try:
            module = self._import_module(module_name)
        except ImportError as e:
            self.logger.warning(f"导入模块失败 {module_name}: {e}")
            return []

        # 扫描模块中的工具类
        tools = self._find_tool_classes_in_module(module)

        if tools:
            self.logger.debug(f"在模块 {module_name} 中发现 {len(tools)} 个工具类")

        return tools

    def _path_to_module_name(self, file_path: Path) -> str:
        """将文件路径转换为模块名

        这是本节课的重点方法，学生需要实现此方法。
        将文件系统路径转换为Python可以导入的模块名。

        Args:
            file_path: 文件路径

        Returns:
            str: 模块名

        Raises:
            ValueError: 路径无法转换为模块名时抛出
        """
        try:
            # 获取绝对路径
            abs_path = file_path.resolve()

            # 获取当前工作目录
            cwd = Path.cwd().resolve()

            try:
                # 计算相对于工作目录的路径
                relative_path = abs_path.relative_to(cwd)
            except ValueError:
                # 如果文件不在工作目录下，使用绝对路径
                # 但需要转换为合法的模块名格式
                # 这里简化处理，实际可能需要更复杂的转换
                relative_path = abs_path

            # 转换为字符串并替换路径分隔符
            path_str = str(relative_path)

            # 处理不同操作系统的路径分隔符
            path_str = path_str.replace("\\", "/")

            # 移除.py扩展名
            if path_str.endswith(".py"):
                path_str = path_str[:-3]

            # 替换路径分隔符为点号
            module_name = path_str.replace("/", ".")

            # 移除开头的点号（如果有）
            if module_name.startswith("."):
                module_name = module_name[1:]

            # 确保模块名不为空
            if not module_name:
                raise ValueError("转换后的模块名为空")

            # 检查模块名是否包含非法字符
            # Python模块名只能包含字母、数字、下划线，且不能以数字开头
            # 这里简化检查，实际需要更严格的验证
            if module_name[0].isdigit():
                raise ValueError(f"模块名不能以数字开头: {module_name}")

            return module_name

        except Exception as e:
            raise ValueError(f"路径转换失败 {file_path}: {e}")

    def _import_module(self, module_name: str):
        """动态导入模块

        使用importlib动态导入模块，支持错误处理和重试。

        Args:
            module_name: 模块名

        Returns:
            module: 导入的模块

        Raises:
            ImportError: 导入失败时抛出
        """
        try:
            # 尝试导入模块
            module = importlib.import_module(module_name)
            return module
        except ImportError as e:
            # 如果是由于缺少依赖导致的导入失败，记录日志但不抛出
            # 实际可以根据错误信息判断是否重试
            self.logger.debug(f"导入模块失败 {module_name}: {e}")
            raise

    def _find_tool_classes_in_module(self, module) -> List[Type[BaseTool]]:
        """在模块中查找工具类

        扫描模块的所有成员，找到继承自BaseTool的类。

        Args:
            module: Python模块对象

        Returns:
            List[Type[BaseTool]]: 找到的工具类列表
        """
        tools = []

        # 获取模块的所有成员
        for name, obj in inspect.getmembers(module):
            # 检查是否是类
            if not inspect.isclass(obj):
                continue

            # 检查是否继承自BaseTool（排除BaseTool自身）
            if not issubclass(obj, BaseTool):
                continue

            if obj == BaseTool:
                continue

            # 检查是否有metadata属性
            if not hasattr(obj, "metadata"):
                self.logger.warning(f"工具类 {name} 缺少metadata属性")
                continue

            # 检查metadata是否是ToolMetadata实例
            if not isinstance(obj.metadata, ToolMetadata):
                self.logger.warning(f"工具类 {name} 的metadata属性类型错误")
                continue

            # 验证工具名称
            if not obj.metadata.name or not obj.metadata.name.strip():
                self.logger.warning(f"工具类 {name} 的名称无效")
                continue

            tools.append(obj)

        return tools

    def _discover_by_module_scan(self) -> List[Type[BaseTool]]:
        """通过模块扫描发现工具"""
        discovered = []

        # 扫描已安装的包和模块
        # 这里简化实现，实际可以扫描sys.path中的所有模块
        for module_info in pkgutil.iter_modules():
            try:
                module = importlib.import_module(module_info.name)
                tools = self._find_tool_classes_in_module(module)
                discovered.extend(tools)
            except ImportError:
                continue
            except Exception as e:
                self.logger.debug(f"扫描模块失败 {module_info.name}: {e}")
                continue

        return discovered

    def _discover_hybrid(self) -> List[Type[BaseTool]]:
        """混合发现：结合路径扫描和模块扫描"""
        path_tools = self._discover_by_path_scan()
        module_tools = self._discover_by_module_scan()

        # 合并结果，去重
        all_tools = {}

        for tool in path_tools + module_tools:
            all_tools[tool.metadata.name] = tool

        return list(all_tools.values())

    def _discover_cached(self) -> List[Type[BaseTool]]:
        """使用缓存发现工具"""
        cache_key = self._get_cache_key()

        if cache_key in self._discovery_cache:
            timestamp, tools = self._discovery_cache[cache_key]

            # 检查缓存是否过期
            if time.time() - timestamp < self.config.cache_ttl_seconds:
                self.logger.info(f"使用缓存发现工具，缓存中有 {len(tools)} 个工具")
                return tools

        # 缓存不存在或已过期，执行路径扫描
        self.logger.info("缓存无效或不存在，执行路径扫描")
        tools = self._discover_by_path_scan()

        # 更新缓存
        self._discovery_cache[cache_key] = (time.time(), tools)

        return tools

    def _get_cache_key(self) -> str:
        """生成缓存键"""
        # 基于配置生成唯一键
        config_str = f"{self.config.strategy.value}:{sorted(self.config.scan_paths)}:{self.config.recursive}"
        return str(hash(config_str))

    def get_discovered_tools(self) -> Dict[str, Type[BaseTool]]:
        """获取已发现的工具类"""
        return self._discovered_tools.copy()

    def clear_cache(self) -> None:
        """清空发现缓存"""
        self._discovery_cache.clear()
        self.logger.info("发现缓存已清空")


class DiscoveryError(Exception):
    """工具发现异常"""

    pass


# ============================================================================
# 第三部分：工具装配系统
# ============================================================================


class AssemblyStrategy(Enum):
    """工具装配策略枚举"""

    LAZY = "lazy"  # 懒加载：使用时才实例化
    EAGER = "eager"  # 急加载：发现后立即实例化
    ON_DEMAND = "on_demand"  # 按需加载：根据请求动态加载


@dataclass
class AssemblyConfig:
    """工具装配配置"""

    strategy: AssemblyStrategy = AssemblyStrategy.LAZY
    auto_initialize: bool = True  # 是否自动初始化工具
    initialization_timeout: int = 30  # 初始化超时时间（秒）
    max_concurrent_init: int = 5  # 最大并发初始化数
    tool_configs: Dict[str, Dict[str, Any]] = field(
        default_factory=dict
    )  # 工具特定配置
    dependency_check: bool = True  # 是否检查工具依赖
    validate_parameters: bool = True  # 是否验证工具参数


class ToolAssembly:
    """工具装配系统，负责加载和实例化工具

    设计原则：可配置性 (CONFIGURABILITY)
    支持多种装配策略和配置选项，适应不同场景需求。
    """

    def __init__(
        self, discovery: ToolDiscovery, config: Optional[AssemblyConfig] = None
    ):
        """初始化工具装配系统

        Args:
            discovery: 工具发现器实例
            config: 装配配置，如果为None则使用默认配置
        """
        self.discovery = discovery
        self.config = config or AssemblyConfig()
        self.logger = logging.getLogger("assembly")

        # 工具实例缓存：工具名 -> 工具实例
        self._tool_instances: Dict[str, BaseTool] = {}

        # 工具初始化状态：工具名 -> 是否已初始化
        self._initialization_status: Dict[str, bool] = {}

        # 工具依赖关系图：工具名 -> 依赖的工具名列表
        self._dependency_graph: Dict[str, List[str]] = {}

    async def assemble_tools(
        self, tool_names: Optional[List[str]] = None
    ) -> Dict[str, BaseTool]:
        """装配工具

        根据配置策略装配指定工具，返回工具实例字典。

        Args:
            tool_names: 要装配的工具名称列表，如果为None则装配所有发现的工具

        Returns:
            Dict[str, BaseTool]: 工具名称到工具实例的映射

        Raises:
            AssemblyError: 装配过程失败时抛出
        """
        start_time = time.time()

        # 获取要装配的工具类
        if tool_names is None:
            # 装配所有发现的工具
            tool_classes = self.discovery.get_discovered_tools()
        else:
            # 装配指定的工具
            tool_classes = {}
            discovered = self.discovery.get_discovered_tools()

            for name in tool_names:
                if name in discovered:
                    tool_classes[name] = discovered[name]
                else:
                    self.logger.warning(f"工具未发现，跳过: {name}")

        self.logger.info(
            f"开始装配 {len(tool_classes)} 个工具，策略: {self.config.strategy.value}"
        )

        try:
            if self.config.strategy == AssemblyStrategy.LAZY:
                # 懒加载：只创建实例，不初始化
                assembled = await self._assemble_lazy(tool_classes)
            elif self.config.strategy == AssemblyStrategy.EAGER:
                # 急加载：创建实例并立即初始化
                assembled = await self._assemble_eager(tool_classes)
            elif self.config.strategy == AssemblyStrategy.ON_DEMAND:
                # 按需加载：根据请求动态加载
                assembled = await self._assemble_on_demand(tool_classes)
            else:
                raise ValueError(f"不支持的装配策略: {self.config.strategy}")

            elapsed = time.time() - start_time
            self.logger.info(
                f"工具装配完成，成功装配 {len(assembled)} 个工具，耗时 {elapsed:.2f} 秒"
            )

            return assembled

        except Exception as e:
            self.logger.error(f"工具装配失败: {e}")
            raise AssemblyError(f"工具装配失败: {e}")

    async def _assemble_lazy(
        self, tool_classes: Dict[str, Type[BaseTool]]
    ) -> Dict[str, BaseTool]:
        """懒加载装配"""
        assembled = {}

        for name, tool_class in tool_classes.items():
            try:
                # 创建工具实例
                tool_config = self.config.tool_configs.get(name, {})
                tool_instance = tool_class(config=tool_config)

                # 缓存实例
                self._tool_instances[name] = tool_instance
                self._initialization_status[name] = False

                # 构建依赖关系
                self._build_dependency_graph(name, tool_class)

                assembled[name] = tool_instance

                self.logger.debug(f"懒加载工具: {name}")

            except Exception as e:
                self.logger.error(f"创建工具实例失败 {name}: {e}")
                # 继续处理其他工具，错误隔离

        return assembled

    async def _assemble_eager(
        self, tool_classes: Dict[str, Type[BaseTool]]
    ) -> Dict[str, BaseTool]:
        """急加载装配"""
        assembled = {}

        # 先创建所有实例
        for name, tool_class in tool_classes.items():
            try:
                tool_config = self.config.tool_configs.get(name, {})
                tool_instance = tool_class(config=tool_config)

                self._tool_instances[name] = tool_instance
                self._initialization_status[name] = False
                self._build_dependency_graph(name, tool_class)

                assembled[name] = tool_instance

            except Exception as e:
                self.logger.error(f"创建工具实例失败 {name}: {e}")
                # 继续处理其他工具

        # 然后初始化所有工具（考虑依赖关系）
        await self._initialize_tools(set(tool_classes.keys()))

        return assembled

    async def _assemble_on_demand(
        self, tool_classes: Dict[str, Type[BaseTool]]
    ) -> Dict[str, BaseTool]:
        """按需加载装配"""
        # 按需加载模式下，只创建空的实例字典
        # 实际使用时再创建和初始化
        assembled = {}

        for name, tool_class in tool_classes.items():
            # 只注册工具类，不创建实例
            self._tool_instances[name] = None  # 占位符
            self._initialization_status[name] = False
            self._build_dependency_graph(name, tool_class)

            # 创建代理实例，实际使用时再加载
            assembled[name] = ToolProxy(name, tool_class, self)

        return assembled

    def _build_dependency_graph(
        self, tool_name: str, tool_class: Type[BaseTool]
    ) -> None:
        """构建依赖关系图"""
        if self.config.dependency_check:
            dependencies = tool_class.metadata.dependencies
            self._dependency_graph[tool_name] = dependencies.copy()
        else:
            self._dependency_graph[tool_name] = []

    async def _initialize_tools(self, tool_names: Set[str]) -> None:
        """初始化工具

        考虑依赖关系，按照依赖顺序初始化工具。

        Args:
            tool_names: 要初始化的工具名称集合
        """
        if not self.config.auto_initialize:
            return

        # 过滤出需要初始化的工具
        tools_to_init = []
        for name in tool_names:
            if name in self._tool_instances and not self._initialization_status.get(
                name, False
            ):
                tools_to_init.append(name)

        if not tools_to_init:
            return

        self.logger.info(f"开始初始化 {len(tools_to_init)} 个工具")

        # 按照依赖顺序排序
        sorted_tools = self._topological_sort(tools_to_init)

        # 并发初始化（有限并发数）
        semaphore = asyncio.Semaphore(self.config.max_concurrent_init)

        async def initialize_with_semaphore(tool_name: str):
            async with semaphore:
                await self._initialize_single_tool(tool_name)

        # 并发执行初始化
        tasks = [initialize_with_semaphore(name) for name in sorted_tools]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _initialize_single_tool(self, tool_name: str) -> None:
        """初始化单个工具"""
        if tool_name not in self._tool_instances:
            self.logger.warning(f"工具实例不存在，无法初始化: {tool_name}")
            return

        tool_instance = self._tool_instances[tool_name]

        if tool_instance is None:
            # 按需加载模式下的代理，跳过初始化
            return

        if self._initialization_status.get(tool_name, False):
            # 已经初始化
            return

        try:
            # 检查依赖是否满足
            if not self._check_dependencies(tool_name):
                self.logger.warning(f"工具依赖不满足，跳过初始化: {tool_name}")
                return

            # 执行初始化
            self.logger.debug(f"开始初始化工具: {tool_name}")

            # 设置超时
            try:
                await asyncio.wait_for(
                    tool_instance.initialize(),
                    timeout=self.config.initialization_timeout,
                )
            except asyncio.TimeoutError:
                self.logger.error(f"工具初始化超时: {tool_name}")
                raise

            # 更新状态
            self._initialization_status[tool_name] = True
            self.logger.info(f"工具初始化成功: {tool_name}")

        except Exception as e:
            self.logger.error(f"工具初始化失败 {tool_name}: {e}")
            # 不抛出异常，错误隔离

    def _check_dependencies(self, tool_name: str) -> bool:
        """检查工具依赖是否满足"""
        if not self.config.dependency_check:
            return True

        dependencies = self._dependency_graph.get(tool_name, [])

        for dep_name in dependencies:
            # 检查依赖工具是否存在
            if dep_name not in self._tool_instances:
                self.logger.warning(f"依赖工具不存在: {tool_name} -> {dep_name}")
                return False

            # 检查依赖工具是否已初始化（如果需要）
            if self.config.auto_initialize:
                if not self._initialization_status.get(dep_name, False):
                    self.logger.warning(f"依赖工具未初始化: {tool_name} -> {dep_name}")
                    return False

        return True

    def _topological_sort(self, tool_names: List[str]) -> List[str]:
        """拓扑排序，返回工具初始化顺序

        考虑工具依赖关系，确保依赖的工具先初始化。

        Args:
            tool_names: 要排序的工具名称列表

        Returns:
            List[str]: 排序后的工具名称列表
        """
        # 构建入度表
        in_degree = {name: 0 for name in tool_names}
        graph = {name: [] for name in tool_names}

        # 构建图
        for name in tool_names:
            dependencies = self._dependency_graph.get(name, [])
            for dep in dependencies:
                if dep in tool_names:  # 只考虑在当前集合中的依赖
                    graph[dep].append(name)
                    in_degree[name] += 1

        # Kahn算法拓扑排序
        result = []
        queue = [name for name in tool_names if in_degree[name] == 0]

        while queue:
            current = queue.pop(0)
            result.append(current)

            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 检查是否有环
        if len(result) != len(tool_names):
            self.logger.warning("工具依赖图中检测到环，可能无法正确初始化所有工具")
            # 返回原始顺序作为后备
            return tool_names

        return result

    async def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具实例

        如果工具尚未装配，按需装配和初始化。

        Args:
            tool_name: 工具名称

        Returns:
            Optional[BaseTool]: 工具实例，如果不存在返回None
        """
        if tool_name not in self._tool_instances:
            # 工具未发现
            return None

        tool_instance = self._tool_instances[tool_name]

        if tool_instance is None:
            # 按需加载模式：创建实际实例
            discovered = self.discovery.get_discovered_tools()
            if tool_name not in discovered:
                return None

            tool_class = discovered[tool_name]
            tool_config = self.config.tool_configs.get(tool_name, {})
            tool_instance = tool_class(config=tool_config)

            # 缓存实例
            self._tool_instances[tool_name] = tool_instance

            # 初始化（如果需要）
            if self.config.auto_initialize:
                await self._initialize_single_tool(tool_name)

        elif (
            not self._initialization_status.get(tool_name, False)
            and self.config.auto_initialize
        ):
            # 实例存在但未初始化，且需要自动初始化
            await self._initialize_single_tool(tool_name)

        return tool_instance

    def get_initialization_status(self) -> Dict[str, bool]:
        """获取工具初始化状态"""
        return self._initialization_status.copy()

    async def cleanup_all(self) -> None:
        """清理所有工具资源"""
        self.logger.info("开始清理所有工具资源")

        cleanup_tasks = []

        for name, tool_instance in self._tool_instances.items():
            if tool_instance is not None and self._initialization_status.get(
                name, False
            ):
                cleanup_tasks.append(tool_instance.cleanup())

        # 并发执行清理
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        # 重置状态
        self._initialization_status.clear()
        self.logger.info("所有工具资源清理完成")


class ToolProxy:
    """工具代理，用于按需加载模式

    设计模式：代理模式 (Proxy Pattern)
    延迟实际工具实例的创建和初始化，直到实际使用时。
    """

    def __init__(
        self, tool_name: str, tool_class: Type[BaseTool], assembly: ToolAssembly
    ):
        self.tool_name = tool_name
        self.tool_class = tool_class
        self.assembly = assembly
        self._real_tool: Optional[BaseTool] = None

    async def __call__(self, **kwargs) -> Any:
        """调用工具"""
        # 确保工具已加载
        await self._ensure_loaded()

        if self._real_tool is None:
            raise AssemblyError(f"无法加载工具: {self.tool_name}")

        # 验证参数（如果需要）
        if self.assembly.config.validate_parameters:
            is_valid, errors = self._real_tool.validate_parameters(**kwargs)
            if not is_valid:
                raise ToolExecutionError(
                    self.tool_name, f"参数验证失败: {', '.join(errors)}"
                )

        # 执行工具
        return await self._real_tool.execute(**kwargs)

    async def _ensure_loaded(self) -> None:
        """确保工具已加载和初始化"""
        if self._real_tool is not None and self._real_tool.is_initialized():
            return

        # 从装配系统获取工具实例
        tool_instance = await self.assembly.get_tool(self.tool_name)

        if tool_instance is None:
            raise AssemblyError(f"无法获取工具实例: {self.tool_name}")

        self._real_tool = tool_instance


class AssemblyError(Exception):
    """工具装配异常"""

    pass


# ============================================================================
# 示例工具实现（用于演示）
# ============================================================================


class CalculatorTool(BaseTool):
    """计算器工具示例"""

    # 类属性：工具元数据
    metadata = ToolMetadata(
        name="calculator",
        description="简单的数学计算器工具，支持加减乘除",
        version="1.0.0",
        author="DeerFlow Team",
        category=ToolCategory.UTILITY,
        tags=["math", "calculator", "utility"],
        dependencies=[],
        required_parameters=["operation", "a", "b"],
        optional_parameters=["precision"],
        return_type="float",
        timeout_seconds=5,
        memory_limit_mb=10,
    )

    async def _initialize_impl(self) -> None:
        """初始化计算器工具"""
        # 这里可以执行一些初始化操作，比如加载预计算数据
        # 对于简单的计算器，可能不需要复杂的初始化
        self.logger.info("计算器工具初始化完成")

    async def execute(self, **kwargs) -> float:
        """执行计算

        Args:
            operation: 操作类型，支持 "add", "subtract", "multiply", "divide"
            a: 第一个操作数
            b: 第二个操作数
            precision: 结果精度（小数位数）

        Returns:
            float: 计算结果
        """
        operation = kwargs["operation"]
        a = float(kwargs["a"])
        b = float(kwargs["b"])
        precision = kwargs.get("precision", 2)

        self.logger.info(f"执行计算: {a} {operation} {b}")

        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                raise ToolExecutionError(
                    self.metadata.name, "除数不能为零", ValueError("Division by zero")
                )
            result = a / b
        else:
            raise ToolExecutionError(
                self.metadata.name,
                f"不支持的操作: {operation}",
                ValueError(f"Unknown operation: {operation}"),
            )

        # 应用精度
        result = round(result, precision)

        return result

    async def _cleanup_impl(self) -> None:
        """清理计算器工具资源"""
        self.logger.info("计算器工具清理完成")


class FileReaderTool(BaseTool):
    """文件读取工具示例"""

    metadata = ToolMetadata(
        name="file_reader",
        description="读取文本文件内容",
        version="1.0.0",
        author="DeerFlow Team",
        category=ToolCategory.UTILITY,
        tags=["file", "io", "utility"],
        dependencies=[],
        required_parameters=["file_path"],
        optional_parameters=["encoding", "max_size"],
        return_type="str",
        timeout_seconds=10,
        memory_limit_mb=50,
    )

    async def _initialize_impl(self) -> None:
        """初始化文件读取工具"""
        # 检查配置
        self.default_encoding = self.config.get("encoding", "utf-8")
        self.default_max_size = self.config.get("max_size", 1024 * 1024)  # 1MB
        self.logger.info(f"文件读取工具初始化完成，默认编码: {self.default_encoding}")

    async def execute(self, **kwargs) -> str:
        """读取文件内容

        Args:
            file_path: 文件路径
            encoding: 文件编码（可选，默认utf-8）
            max_size: 最大文件大小（字节，可选，默认1MB）

        Returns:
            str: 文件内容
        """
        file_path = kwargs["file_path"]
        encoding = kwargs.get("encoding", self.default_encoding)
        max_size = kwargs.get("max_size", self.default_max_size)

        self.logger.info(f"读取文件: {file_path}")

        # 检查文件是否存在
        path = Path(file_path)
        if not path.exists():
            raise ToolExecutionError(
                self.metadata.name,
                f"文件不存在: {file_path}",
                FileNotFoundError(f"File not found: {file_path}"),
            )

        # 检查文件大小
        file_size = path.stat().st_size
        if file_size > max_size:
            raise ToolExecutionError(
                self.metadata.name,
                f"文件太大: {file_size}字节 > {max_size}字节",
                ValueError(f"File too large: {file_size} > {max_size}"),
            )

        # 读取文件
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
        except UnicodeDecodeError as e:
            raise ToolExecutionError(self.metadata.name, f"文件编码错误: {encoding}", e)
        except Exception as e:
            raise ToolExecutionError(
                self.metadata.name, f"读取文件失败: {file_path}", e
            )

        return content

    async def _cleanup_impl(self) -> None:
        """清理文件读取工具资源"""
        self.logger.info("文件读取工具清理完成")


class WebFetcherTool(BaseTool):
    """网页抓取工具示例（模拟）"""

    metadata = ToolMetadata(
        name="web_fetcher",
        description="抓取网页内容（模拟实现）",
        version="1.0.0",
        author="DeerFlow Team",
        category=ToolCategory.NETWORK,
        tags=["web", "http", "network"],
        dependencies=[],
        required_parameters=["url"],
        optional_parameters=["timeout", "user_agent"],
        return_type="str",
        timeout_seconds=30,
        memory_limit_mb=100,
    )

    async def _initialize_impl(self) -> None:
        """初始化网页抓取工具"""
        self.default_timeout = self.config.get("timeout", 10)
        self.default_user_agent = self.config.get("user_agent", "DeerFlow Tool/1.0")
        self.logger.info(f"网页抓取工具初始化完成，默认超时: {self.default_timeout}秒")

    async def execute(self, **kwargs) -> str:
        """抓取网页内容（模拟）

        注意：这是模拟实现，实际项目应该使用真正的HTTP客户端。

        Args:
            url: 网页URL
            timeout: 超时时间（秒，可选）
            user_agent: User-Agent头（可选）

        Returns:
            str: 模拟的网页内容
        """
        url = kwargs["url"]
        timeout = kwargs.get("timeout", self.default_timeout)
        user_agent = kwargs.get("user_agent", self.default_user_agent)

        self.logger.info(f"抓取网页: {url} (User-Agent: {user_agent})")

        # 模拟网络延迟
        await asyncio.sleep(0.5)

        # 模拟不同的响应
        if "example.com" in url:
            return f"<html><body>模拟示例网页内容: {url}</body></html>"
        elif "error" in url:
            raise ToolExecutionError(
                self.metadata.name,
                f"模拟HTTP错误: {url}",
                ConnectionError(f"模拟连接错误: {url}"),
            )
        else:
            return f"<html><body>模拟网页内容: {url}<p>抓取时间: {time.time()}</p></body></html>"

    async def _cleanup_impl(self) -> None:
        """清理网页抓取工具资源"""
        self.logger.info("网页抓取工具清理完成")


# ============================================================================
# 第四部分：测试与演示
# ============================================================================


class ToolDiscoveryAssemblyTestSuite:
    """工具发现与装配系统测试套件"""

    def __init__(self):
        self.logger = logging.getLogger("test_suite")
        self.test_results = []

    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        self.logger.info("开始运行工具发现与装配系统测试套件")

        # 创建临时目录用于测试
        import tempfile
        import shutil

        self.temp_dir = tempfile.mkdtemp(prefix="tool_test_")

        try:
            # 创建测试工具模块
            self._create_test_tools()

            # 运行测试
            await self.test_discovery_basic()
            await self.test_discovery_path_scan()
            await self.test_discovery_cached()
            await self.test_assembly_lazy()
            await self.test_assembly_eager()
            await self.test_assembly_on_demand()
            await self.test_tool_execution()
            await self.test_error_handling()
            await self.test_performance()

            # 生成测试报告
            report = self._generate_test_report()

            return report

        finally:
            # 清理临时目录
            if hasattr(self, "temp_dir"):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self.logger.info(f"清理临时目录: {self.temp_dir}")

    def _create_test_tools(self):
        """创建测试工具模块"""
        # 在临时目录中创建工具模块
        tools_dir = Path(self.temp_dir) / "tools"
        tools_dir.mkdir(exist_ok=True)

        # 创建__init__.py
        (tools_dir / "__init__.py").write_text("# 工具包初始化文件\n")

        # 创建测试工具模块
        test_tool_content = '''
from typing import Any, Dict
import asyncio
from tool_discovery_assembly_demo import BaseTool, ToolMetadata, ToolCategory, ToolExecutionError

class TestTool1(BaseTool):
    """测试工具1"""
    
    metadata = ToolMetadata(
        name="test_tool_1",
        description="第一个测试工具",
        version="1.0.0",
        author="Test Author",
        category=ToolCategory.UTILITY,
        tags=["test", "demo"],
        dependencies=[],
        required_parameters=["input"],
        optional_parameters=[],
        return_type="str",
        timeout_seconds=5,
        memory_limit_mb=10
    )
    
    async def _initialize_impl(self) -> None:
        await asyncio.sleep(0.1)  # 模拟初始化延迟
    
    async def execute(self, **kwargs) -> Any:
        input_data = kwargs["input"]
        return f"Processed: {input_data}"
    
    async def _cleanup_impl(self) -> None:
        pass

class TestTool2(BaseTool):
    """测试工具2"""
    
    metadata = ToolMetadata(
        name="test_tool_2",
        description="第二个测试工具",
        version="1.0.0",
        author="Test Author",
        category=ToolCategory.UTILITY,
        tags=["test", "demo"],
        dependencies=["test_tool_1"],  # 依赖第一个工具
        required_parameters=["value"],
        optional_parameters=["multiplier"],
        return_type="float",
        timeout_seconds=5,
        memory_limit_mb=10
    )
    
    async def _initialize_impl(self) -> None:
        await asyncio.sleep(0.1)
    
    async def execute(self, **kwargs) -> Any:
        value = float(kwargs["value"])
        multiplier = float(kwargs.get("multiplier", 2.0))
        return value * multiplier
    
    async def _cleanup_impl(self) -> None:
        pass

class BrokenTool(BaseTool):
    """有问题的工具（用于测试错误处理）"""
    
    metadata = ToolMetadata(
        name="broken_tool",
        description="有问题的测试工具",
        version="1.0.0",
        author="Test Author",
        category=ToolCategory.UTILITY,
        tags=["test", "broken"],
        dependencies=[],
        required_parameters=[],
        optional_parameters=[],
        return_type="str",
        timeout_seconds=5,
        memory_limit_mb=10
    )
    
    async def _initialize_impl(self) -> None:
        raise RuntimeError("模拟初始化失败")
    
    async def execute(self, **kwargs) -> Any:
        raise RuntimeError("模拟执行失败")
    
    async def _cleanup_impl(self) -> None:
        pass
'''

        (tools_dir / "test_tools.py").write_text(test_tool_content)

        # 创建另一个工具模块
        another_tool_content = '''
from tool_discovery_assembly_demo import BaseTool, ToolMetadata, ToolCategory

class AnotherTool(BaseTool):
    """另一个测试工具"""
    
    metadata = ToolMetadata(
        name="another_tool",
        description="另一个测试工具",
        version="1.0.0",
        author="Test Author",
        category=ToolCategory.NETWORK,
        tags=["test", "network"],
        dependencies=[],
        required_parameters=["url"],
        optional_parameters=[],
        return_type="str",
        timeout_seconds=10,
        memory_limit_mb=20
    )
    
    async def _initialize_impl(self) -> None:
        pass
    
    async def execute(self, **kwargs) -> Any:
        url = kwargs["url"]
        return f"Fetched: {url}"
    
    async def _cleanup_impl(self) -> None:
        pass
'''

        (tools_dir / "another_tool.py").write_text(another_tool_content)

        self.logger.info(f"创建测试工具模块在: {tools_dir}")

    async def test_discovery_basic(self):
        """测试基础发现功能"""
        test_name = "test_discovery_basic"
        start_time = time.time()

        try:
            # 创建发现器
            config = DiscoveryConfig(
                scan_paths=[str(Path(self.temp_dir) / "tools")], recursive=False
            )
            discovery = ToolDiscovery(config)

            # 执行发现
            tools = discovery.discover_tools()

            # 验证结果
            tool_names = [tool.metadata.name for tool in tools]
            expected_tools = {
                "test_tool_1",
                "test_tool_2",
                "broken_tool",
                "another_tool",
            }

            missing = expected_tools - set(tool_names)
            extra = set(tool_names) - expected_tools

            if missing or extra:
                raise AssertionError(
                    f"工具发现结果不符合预期: 缺少{missing}, 多余{extra}"
                )

            elapsed = time.time() - start_time
            self._record_test_result(
                test_name, True, elapsed, f"发现 {len(tools)} 个工具"
            )

        except Exception as e:
            elapsed = time.time() - start_time
            self._record_test_result(test_name, False, elapsed, str(e))

    async def test_discovery_path_scan(self):
        """测试路径扫描发现"""
        test_name = "test_discovery_path_scan"
        start_time = time.time()

        try:
            config = DiscoveryConfig(
                strategy=DiscoveryStrategy.PATH_SCAN,
                scan_paths=[self.temp_dir],
                recursive=True,
                max_depth=3,
            )
            discovery = ToolDiscovery(config)

            tools = discovery.discover_tools()

            # 至少应该找到4个工具
            if len(tools) < 4:
                raise AssertionError(f"期望至少4个工具，实际找到 {len(tools)} 个")

            elapsed = time.time() - start_time
            self._record_test_result(
                test_name, True, elapsed, f"路径扫描发现 {len(tools)} 个工具"
            )

        except Exception as e:
            elapsed = time.time() - start_time
            self._record_test_result(test_name, False, elapsed, str(e))

    async def test_discovery_cached(self):
        """测试缓存发现"""
        test_name = "test_discovery_cached"
        start_time = time.time()

        try:
            config = DiscoveryConfig(
                strategy=DiscoveryStrategy.CACHED,
                scan_paths=[str(Path(self.temp_dir) / "tools")],
                cache_enabled=True,
                cache_ttl_seconds=60,
            )
            discovery = ToolDiscovery(config)

            # 第一次发现（会缓存）
            tools1 = discovery.discover_tools()

            # 第二次发现（应该使用缓存）
            tools2 = discovery.discover_tools()

            # 检查缓存是否工作
            if len(tools1) != len(tools2):
                raise AssertionError("缓存发现结果不一致")

            # 清空缓存
            discovery.clear_cache()

            elapsed = time.time() - start_time
            self._record_test_result(test_name, True, elapsed, "缓存发现测试通过")

        except Exception as e:
            elapsed = time.time() - start_time
            self._record_test_result(test_name, False, elapsed, str(e))

    async def test_assembly_lazy(self):
        """测试懒加载装配"""
        test_name = "test_assembly_lazy"
        start_time = time.time()

        try:
            # 创建发现器
            discovery_config = DiscoveryConfig(
                scan_paths=[str(Path(self.temp_dir) / "tools")]
            )
            discovery = ToolDiscovery(discovery_config)

            # 创建装配器（懒加载模式）
            assembly_config = AssemblyConfig(strategy=AssemblyStrategy.LAZY)
            assembly = ToolAssembly(discovery, assembly_config)

            # 装配工具
            tools = await assembly.assemble_tools()

            # 检查装配结果
            if len(tools) < 3:  # 至少应该有3个工具（排除有问题的工具可能被跳过）
                raise AssertionError(f"期望至少3个工具，实际装配 {len(tools)} 个")

            # 检查初始化状态（懒加载模式下应该未初始化）
            status = assembly.get_initialization_status()
            initialized_count = sum(1 for v in status.values() if v)

            if initialized_count > 0:
                raise AssertionError(
                    f"懒加载模式下不应该有已初始化的工具，实际有 {initialized_count} 个"
                )

            elapsed = time.time() - start_time
            self._record_test_result(
                test_name, True, elapsed, f"懒加载装配 {len(tools)} 个工具"
            )

        except Exception as e:
            elapsed = time.time() - start_time
            self._record_test_result(test_name, False, elapsed, str(e))

    async def test_assembly_eager(self):
        """测试急加载装配"""
        test_name = "test_assembly_eager"
        start_time = time.time()

        try:
            discovery_config = DiscoveryConfig(
                scan_paths=[str(Path(self.temp_dir) / "tools")]
            )
            discovery = ToolDiscovery(discovery_config)

            assembly_config = AssemblyConfig(strategy=AssemblyStrategy.EAGER)
            assembly = ToolAssembly(discovery, assembly_config)

            # 装配工具
            tools = await assembly.assemble_tools()

            # 检查初始化状态（急加载模式下应该已初始化）
            status = assembly.get_initialization_status()
            initialized_count = sum(1 for v in status.values() if v)

            # 注意：broken_tool可能初始化失败，所以不一定是所有工具都初始化
            if initialized_count < 2:  # 至少应该有2个工具成功初始化
                raise AssertionError(
                    f"急加载模式下期望至少2个工具已初始化，实际 {initialized_count} 个"
                )

            elapsed = time.time() - start_time
            self._record_test_result(
                test_name,
                True,
                elapsed,
                f"急加载装配 {len(tools)} 个工具，{initialized_count} 个已初始化",
            )

        except Exception as e:
            elapsed = time.time() - start_time
            self._record_test_result(test_name, False, elapsed, str(e))

    async def test_assembly_on_demand(self):
        """测试按需加载装配"""
        test_name = "test_assembly_on_demand"
        start_time = time.time()

        try:
            discovery_config = DiscoveryConfig(
                scan_paths=[str(Path(self.temp_dir) / "tools")]
            )
            discovery = ToolDiscovery(discovery_config)

            assembly_config = AssemblyConfig(strategy=AssemblyStrategy.ON_DEMAND)
            assembly = ToolAssembly(discovery, assembly_config)

            # 装配工具（按需模式下只创建代理）
            tools = await assembly.assemble_tools()

            # 获取一个工具并执行
            tool = await assembly.get_tool("test_tool_1")
            if tool is None:
                raise AssertionError("无法获取test_tool_1")

            # 执行工具
            result = await tool.execute(input="test")

            if "Processed: test" not in str(result):
                raise AssertionError(f"工具执行结果不符合预期: {result}")

            elapsed = time.time() - start_time
            self._record_test_result(test_name, True, elapsed, "按需加载装配测试通过")

        except Exception as e:
            elapsed = time.time() - start_time
            self._record_test_result(test_name, False, elapsed, str(e))

    async def test_tool_execution(self):
        """测试工具执行"""
        test_name = "test_tool_execution"
        start_time = time.time()

        try:
            # 使用内置的示例工具
            calculator = CalculatorTool()
            await calculator.initialize()

            # 测试加法
            result = await calculator.execute(operation="add", a=10, b=20)
            if result != 30:
                raise AssertionError(f"加法计算错误: 10 + 20 = {result}")

            # 测试除法
            result = await calculator.execute(
                operation="divide", a=10, b=2, precision=1
            )
            if result != 5.0:
                raise AssertionError(f"除法计算错误: 10 / 2 = {result}")

            # 测试错误处理（除以零）
            try:
                await calculator.execute(operation="divide", a=10, b=0)
                raise AssertionError("除以零应该抛出异常")
            except ToolExecutionError:
                pass  # 期望的异常

            await calculator.cleanup()

            elapsed = time.time() - start_time
            self._record_test_result(test_name, True, elapsed, "工具执行测试通过")

        except Exception as e:
            elapsed = time.time() - start_time
            self._record_test_result(test_name, False, elapsed, str(e))

    async def test_error_handling(self):
        """测试错误处理"""
        test_name = "test_error_handling"
        start_time = time.time()

        try:
            # 测试有问题的工具
            discovery_config = DiscoveryConfig(
                scan_paths=[str(Path(self.temp_dir) / "tools")]
            )
            discovery = ToolDiscovery(discovery_config)

            assembly_config = AssemblyConfig(strategy=AssemblyStrategy.EAGER)
            assembly = ToolAssembly(discovery, assembly_config)

            # 装配所有工具（包括有问题的工具）
            tools = await assembly.assemble_tools()

            # 有问题的工具可能被跳过或初始化失败
            # 但系统不应该崩溃
            if "broken_tool" in tools:
                # 尝试执行有问题的工具
                try:
                    tool = await assembly.get_tool("broken_tool")
                    if tool is not None:
                        await tool.execute()
                        # 如果执行到这里，说明错误处理有问题
                        raise AssertionError("有问题的工具应该抛出异常")
                except (ToolExecutionError, AssemblyError):
                    pass  # 期望的异常

            elapsed = time.time() - start_time
            self._record_test_result(test_name, True, elapsed, "错误处理测试通过")

        except Exception as e:
            elapsed = time.time() - start_time
            self._record_test_result(test_name, False, elapsed, str(e))

    async def test_performance(self):
        """测试性能"""
        test_name = "test_performance"
        start_time = time.time()

        try:
            # 测试并发装配性能
            discovery_config = DiscoveryConfig(
                scan_paths=[str(Path(self.temp_dir) / "tools")], cache_enabled=False
            )
            discovery = ToolDiscovery(discovery_config)

            assembly_config = AssemblyConfig(
                strategy=AssemblyStrategy.EAGER, max_concurrent_init=10
            )
            assembly = ToolAssembly(discovery, assembly_config)

            # 多次装配，测试性能
            iterations = 3
            total_tools = 0

            for i in range(iterations):
                tools = await assembly.assemble_tools()
                total_tools += len(tools)

                # 清理，准备下一次
                await assembly.cleanup_all()

            avg_tools = total_tools / iterations

            elapsed = time.time() - start_time
            avg_time = elapsed / iterations

            self._record_test_result(
                test_name,
                True,
                elapsed,
                f"性能测试: {iterations}次迭代，平均 {avg_tools:.1f} 个工具，平均耗时 {avg_time:.2f} 秒",
            )

        except Exception as e:
            elapsed = time.time() - start_time
            self._record_test_result(test_name, False, elapsed, str(e))

    def _record_test_result(
        self, test_name: str, passed: bool, duration: float, message: str
    ):
        """记录测试结果"""
        result = {
            "name": test_name,
            "passed": passed,
            "duration": duration,
            "message": message,
            "timestamp": time.time(),
        }
        self.test_results.append(result)

        status = "✅ 通过" if passed else "❌ 失败"
        self.logger.info(f"{status} {test_name}: {message} ({duration:.2f}s)")

    def _generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed
        total_duration = sum(r["duration"] for r in self.test_results)

        report = {
            "summary": {
                "total_tests": total,
                "passed_tests": passed,
                "failed_tests": failed,
                "success_rate": (passed / total * 100) if total > 0 else 0,
                "total_duration": total_duration,
            },
            "details": self.test_results,
            "timestamp": time.time(),
        }

        # 打印摘要
        self.logger.info("\n" + "=" * 60)
        self.logger.info("测试报告摘要")
        self.logger.info("=" * 60)
        self.logger.info(f"总计测试: {total}")
        self.logger.info(f"通过测试: {passed}")
        self.logger.info(f"失败测试: {failed}")
        self.logger.info(f"成功率: {report['summary']['success_rate']:.1f}%")
        self.logger.info(f"总耗时: {total_duration:.2f}秒")

        # 打印失败的测试
        if failed > 0:
            self.logger.info("\n失败测试详情:")
            for result in self.test_results:
                if not result["passed"]:
                    self.logger.info(f"  - {result['name']}: {result['message']}")

        return report


async def main_demo():
    """主演示函数"""
    import sys

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("tool_discovery_demo.log"),
        ],
    )

    logger = logging.getLogger("main")
    logger.info("=" * 60)
    logger.info("工具发现与装配系统演示")
    logger.info("=" * 60)

    # 演示1：基本工具发现
    logger.info("\n1. 基本工具发现演示")
    logger.info("-" * 40)

    # 创建发现器（扫描当前目录）
    discovery_config = DiscoveryConfig(scan_paths=["."], recursive=False, max_depth=2)

    discovery = ToolDiscovery(discovery_config)

    try:
        tools = discovery.discover_tools()
        logger.info(f"发现 {len(tools)} 个工具:")
        for tool in tools:
            logger.info(f"  - {tool.metadata.name}: {tool.metadata.description}")
    except Exception as e:
        logger.error(f"工具发现失败: {e}")

    # 演示2：工具装配和执行
    logger.info("\n2. 工具装配和执行演示")
    logger.info("-" * 40)

    # 使用内置的示例工具
    logger.info("创建示例工具...")

    calculator = CalculatorTool()
    file_reader = FileReaderTool()
    web_fetcher = WebFetcherTool()

    # 初始化工具
    logger.info("初始化工具...")
    try:
        await calculator.initialize()
        await file_reader.initialize()
        await web_fetcher.initialize()
        logger.info("所有工具初始化成功")
    except Exception as e:
        logger.error(f"工具初始化失败: {e}")

    # 执行工具
    logger.info("\n执行工具演示:")

    # 计算器工具
    try:
        result = await calculator.execute(operation="add", a=15, b=25)
        logger.info(f"计算器工具: 15 + 25 = {result}")
    except ToolExecutionError as e:
        logger.error(f"计算器执行失败: {e}")

    # 文件读取工具（模拟）
    try:
        # 创建一个临时文件用于演示
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("这是一个测试文件内容\n第二行内容")
            temp_file = f.name

        result = await file_reader.execute(file_path=temp_file, encoding="utf-8")
        logger.info(f"文件读取工具: 读取到 {len(result)} 个字符")

        import os

        os.unlink(temp_file)
    except ToolExecutionError as e:
        logger.error(f"文件读取失败: {e}")
    except Exception as e:
        logger.error(f"文件操作失败: {e}")

    # 网页抓取工具
    try:
        result = await web_fetcher.execute(url="https://example.com")
        logger.info(f"网页抓取工具: 抓取到 {len(result)} 个字符的HTML")
    except ToolExecutionError as e:
        logger.error(f"网页抓取失败: {e}")

    # 清理工具
    logger.info("\n清理工具资源...")
    await calculator.cleanup()
    await file_reader.cleanup()
    await web_fetcher.cleanup()

    # 演示3：测试套件
    logger.info("\n3. 运行测试套件")
    logger.info("-" * 40)

    test_suite = ToolDiscoveryAssemblyTestSuite()
    report = await test_suite.run_all_tests()

    # 演示4：完整工作流
    logger.info("\n4. 完整工作流演示")
    logger.info("-" * 40)

    logger.info("步骤1: 创建工具发现器")
    discovery = ToolDiscovery(DiscoveryConfig(scan_paths=["."]))

    logger.info("步骤2: 发现工具")
    tools = discovery.discover_tools()
    logger.info(f"发现 {len(tools)} 个工具类")

    logger.info("步骤3: 创建工具装配系统")
    assembly = ToolAssembly(discovery, AssemblyConfig(strategy=AssemblyStrategy.EAGER))

    logger.info("步骤4: 装配工具")
    assembled = await assembly.assemble_tools()
    logger.info(f"成功装配 {len(assembled)} 个工具实例")

    logger.info("步骤5: 获取并使用工具")
    if "calculator" in assembled:
        calc = assembled["calculator"]
        try:
            result = await calc.execute(operation="multiply", a=7, b=8)
            logger.info(f"使用装配的工具: 7 * 8 = {result}")
        except Exception as e:
            logger.error(f"工具执行失败: {e}")

    logger.info("步骤6: 清理所有资源")
    await assembly.cleanup_all()

    logger.info("\n" + "=" * 60)
    logger.info("演示完成!")
    logger.info("=" * 60)


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main_demo())
