#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 8 Lesson 30: Provider模式实现

本文件演示Provider设计模式的完整实现，包括：
1. Provider协议定义和类型检查
2. Provider注册表管理和动态发现
3. 配置驱动的Provider创建和选择
4. 完整的测试套件和演示程序

采用四部分结构设计：
第一部分：概念与设计原则 - 定义Provider模式的核心概念和设计原则
第二部分：协议与注册表实现 - 实现Provider协议和注册表管理系统
第三部分：配置驱动创建 - 实现基于配置的Provider创建和选择
第四部分：测试与演示 - 提供完整测试套件和演示程序

使用示例:
    python provider_demo.py          # 运行基本演示
    python provider_demo.py --test   # 运行测试套件
    python provider_demo.py --demo   # 运行完整演示
    python provider_demo.py --help   # 显示帮助信息
"""

import asyncio
import sys
import json
import time
import inspect
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable, Type, Protocol, runtime_checkable
from dataclasses import dataclass, field, asdict
import logging
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
import argparse

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================

class ProviderCapability(Enum):
    """Provider核心能力枚举"""
    DYNAMIC_DISCOVERY = "动态发现"        # 支持运行时动态发现和注册Provider
    CONFIG_DRIVEN = "配置驱动"           # 基于配置文件创建和选择Provider
    PLUGIN_SUPPORT = "插件支持"          # 支持插件化扩展，动态加载新Provider
    HEALTH_CHECK = "健康检查"            # 支持Provider健康状态检查和故障转移
    PERFORMANCE_MONITOR = "性能监控"     # 监控Provider性能指标，支持智能选择
    VERSION_MANAGEMENT = "版本管理"      # 管理Provider版本，支持多版本共存


class ProviderStatus(Enum):
    """Provider状态枚举"""
    AVAILABLE = "可用"           # Provider可用，可正常提供服务
    DEGRADED = "降级"           # Provider性能下降，但仍可用
    UNAVAILABLE = "不可用"       # Provider不可用，无法提供服务
    DEPRECATED = "已弃用"       # Provider已弃用，将被移除
    EXPERIMENTAL = "实验性"      # Provider处于实验阶段，稳定性未知


class ProviderPriority(Enum):
    """Provider优先级枚举"""
    CRITICAL = "关键"           # 最高优先级，系统核心功能依赖
    HIGH = "高"                # 高优先级，重要功能依赖
    MEDIUM = "中"              # 中等优先级，一般功能依赖
    LOW = "低"                 # 低优先级，辅助功能依赖
    BACKGROUND = "后台"         # 最低优先级，后台任务使用


@dataclass
class ProviderMetadata:
    """Provider元数据"""
    name: str                    # Provider名称（唯一标识）
    description: str             # Provider描述
    version: str                 # 版本号（语义化版本）
    author: str                  # 作者/维护者
    capabilities: List[ProviderCapability]  # 支持的能力
    status: ProviderStatus = ProviderStatus.AVAILABLE  # 当前状态
    priority: ProviderPriority = ProviderPriority.MEDIUM  # 优先级
    config_schema: Optional[Dict] = None  # 配置模式定义
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他Provider
    tags: List[str] = field(default_factory=list)  # 标签，用于分类和搜索
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "capabilities": [cap.value for cap in self.capabilities],
            "status": self.status.value,
            "priority": self.priority.value,
            "config_schema": self.config_schema,
            "dependencies": self.dependencies,
            "tags": self.tags
        }


@dataclass
class ProviderConfig:
    """Provider配置"""
    provider_type: str           # Provider类型标识
    config: Dict[str, Any]       # 具体配置参数
    priority: ProviderPriority = ProviderPriority.MEDIUM  # 配置优先级
    enabled: bool = True         # 是否启用
    metadata: Optional[Dict[str, Any]] = None  # 扩展元数据
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "provider_type": self.provider_type,
            "config": self.config,
            "priority": self.priority.value,
            "enabled": self.enabled,
            "metadata": self.metadata
        }


@dataclass
class ProviderSelectionResult:
    """Provider选择结果"""
    provider_name: str           # 选中的Provider名称
    provider_instance: Any       # Provider实例
    metadata: ProviderMetadata   # Provider元数据
    selection_reason: str        # 选择原因
    selection_time: float        # 选择耗时（秒）
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "provider_name": self.provider_name,
            "provider_metadata": self.metadata.to_dict(),
            "selection_reason": self.selection_reason,
            "selection_time": self.selection_time
        }


# ============================================================================
# 第二部分：协议与注册表实现
# ============================================================================

@runtime_checkable
class BaseProvider(Protocol):
    """Provider基础协议
    
    定义所有Provider必须实现的最小接口集合，使用Protocol支持鸭子类型
    """
    
    def get_metadata(self) -> ProviderMetadata:
        """获取Provider元数据"""
        ...
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化Provider
        
        Args:
            config: 配置参数
            
        Returns:
            初始化是否成功
        """
        ...
    
    async def shutdown(self) -> None:
        """关闭Provider，释放资源"""
        ...
    
    def is_healthy(self) -> bool:
        """检查Provider健康状态
        
        Returns:
            Provider是否健康可用
        """
        ...


class ProviderRegistry:
    """Provider注册表
    
    管理所有已注册的Provider，支持动态注册、发现和选择
    """
    
    def __init__(self, name: str = "default"):
        self.name = name
        self._providers: Dict[str, BaseProvider] = {}
        self._metadata_cache: Dict[str, ProviderMetadata] = {}
        self._logger = logging.getLogger(f"ProviderRegistry.{name}")
        self._lock = asyncio.Lock()
        
        # 统计信息
        self._stats = {
            "total_registrations": 0,
            "successful_selections": 0,
            "failed_selections": 0,
            "avg_selection_time": 0.0,
            "last_selection_time": 0.0
        }
    
    async def register_provider(self, provider: BaseProvider, 
                               metadata: Optional[ProviderMetadata] = None) -> bool:
        """注册Provider
        
        Args:
            provider: Provider实例
            metadata: 可选元数据，如果为None则从provider获取
            
        Returns:
            注册是否成功
        """
        async with self._lock:
            try:
                # 获取或验证元数据
                if metadata is None:
                    metadata = provider.get_metadata()
                else:
                    # 验证provider是否实现了get_metadata
                    if not hasattr(provider, 'get_metadata'):
                        raise ValueError("Provider must implement get_metadata()")
                
                provider_name = metadata.name
                
                # 检查是否已注册
                if provider_name in self._providers:
                    self._logger.warning(f"Provider '{provider_name}' already registered, replacing")
                
                # 注册provider
                self._providers[provider_name] = provider
                self._metadata_cache[provider_name] = metadata
                self._stats["total_registrations"] += 1
                
                self._logger.info(f"Registered provider '{provider_name}' v{metadata.version}")
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to register provider: {e}")
                return False
    
    async def unregister_provider(self, provider_name: str) -> bool:
        """取消注册Provider
        
        Args:
            provider_name: Provider名称
            
        Returns:
            取消注册是否成功
        """
        async with self._lock:
            if provider_name not in self._providers:
                self._logger.warning(f"Provider '{provider_name}' not found")
                return False
            
            try:
                provider = self._providers[provider_name]
                await provider.shutdown()
                
                del self._providers[provider_name]
                del self._metadata_cache[provider_name]
                
                self._logger.info(f"Unregistered provider '{provider_name}'")
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to unregister provider '{provider_name}': {e}")
                return False
    
    async def get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """获取Provider实例
        
        Args:
            provider_name: Provider名称
            
        Returns:
            Provider实例，如果不存在则返回None
        """
        async with self._lock:
            return self._providers.get(provider_name)
    
    async def list_providers(self, 
                            filter_status: Optional[ProviderStatus] = None,
                            filter_capability: Optional[ProviderCapability] = None,
                            filter_tag: Optional[str] = None) -> List[ProviderMetadata]:
        """列出所有Provider的元数据
        
        Args:
            filter_status: 按状态过滤
            filter_capability: 按能力过滤
            filter_tag: 按标签过滤
            
        Returns:
            符合条件的Provider元数据列表
        """
        result = []
        
        for metadata in self._metadata_cache.values():
            # 应用过滤器
            if filter_status and metadata.status != filter_status:
                continue
                
            if filter_capability and filter_capability not in metadata.capabilities:
                continue
                
            if filter_tag and filter_tag not in metadata.tags:
                continue
            
            result.append(metadata)
        
        return result
    
    async def select_provider(self, 
                             capability: ProviderCapability,
                             priority: ProviderPriority = ProviderPriority.MEDIUM) -> Optional[ProviderSelectionResult]:
        """根据能力和优先级选择合适的Provider
        
        Args:
            capability: 所需能力
            priority: 期望优先级
            
        Returns:
            Provider选择结果，如果找不到合适的则返回None
        """
        start_time = time.time()
        
        try:
            # 收集符合条件的Provider
            candidates = []
            for provider_name, metadata in self._metadata_cache.items():
                # 检查状态和能力
                if metadata.status != ProviderStatus.AVAILABLE:
                    continue
                    
                if capability not in metadata.capabilities:
                    continue
                
                # 计算匹配分数（基于优先级和状态）
                priority_score = self._calculate_priority_score(metadata.priority, priority)
                candidates.append((provider_name, metadata, priority_score))
            
            if not candidates:
                self._logger.warning(f"No provider found for capability '{capability.value}'")
                self._stats["failed_selections"] += 1
                return None
            
            # 按分数排序选择最佳Provider
            candidates.sort(key=lambda x: x[2], reverse=True)
            selected_name, selected_metadata, score = candidates[0]
            selected_provider = self._providers[selected_name]
            
            # 记录统计
            selection_time = time.time() - start_time
            self._stats["successful_selections"] += 1
            self._stats["avg_selection_time"] = (
                self._stats["avg_selection_time"] * (self._stats["successful_selections"] - 1) + selection_time
            ) / self._stats["successful_selections"]
            self._stats["last_selection_time"] = selection_time
            
            # 构建选择结果
            selection_reason = f"Best match: {selected_metadata.name} (score: {score:.2f})"
            
            return ProviderSelectionResult(
                provider_name=selected_name,
                provider_instance=selected_provider,
                metadata=selected_metadata,
                selection_reason=selection_reason,
                selection_time=selection_time
            )
            
        except Exception as e:
            self._logger.error(f"Error selecting provider: {e}")
            self._stats["failed_selections"] += 1
            return None
    
    def _calculate_priority_score(self, provider_priority: ProviderPriority, 
                                 requested_priority: ProviderPriority) -> float:
        """计算优先级匹配分数
        
        Args:
            provider_priority: Provider的实际优先级
            requested_priority: 请求的优先级
            
        Returns:
            匹配分数（0-1之间）
        """
        # 优先级映射到数值
        priority_values = {
            ProviderPriority.CRITICAL: 5,
            ProviderPriority.HIGH: 4,
            ProviderPriority.MEDIUM: 3,
            ProviderPriority.LOW: 2,
            ProviderPriority.BACKGROUND: 1
        }
        
        provider_value = priority_values[provider_priority]
        requested_value = priority_values[requested_priority]
        
        # 计算匹配度（越接近分数越高）
        diff = abs(provider_value - requested_value)
        score = 1.0 - (diff / 4.0)  # 4是最大可能差值
        
        return max(0.0, min(1.0, score))
    
    def get_registry_stats(self) -> Dict:
        """获取注册表统计信息"""
        return self._stats.copy()


class ProviderFactory:
    """Provider工厂
    
    根据配置创建和初始化Provider实例
    """
    
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry
        self._logger = logging.getLogger("ProviderFactory")
        self._provider_builders: Dict[str, Callable[[Dict], BaseProvider]] = {}
    
    def register_builder(self, provider_type: str, 
                        builder_func: Callable[[Dict], BaseProvider]) -> None:
        """注册Provider构建器
        
        Args:
            provider_type: Provider类型标识
            builder_func: 构建函数，接收配置字典返回Provider实例
        """
        self._provider_builders[provider_type] = builder_func
        self._logger.info(f"Registered builder for provider type '{provider_type}'")
    
    async def create_and_register_provider(self, config: ProviderConfig) -> bool:
        """根据配置创建并注册Provider
        
        Args:
            config: Provider配置
            
        Returns:
            创建和注册是否成功
        """
        try:
            # 检查构建器是否存在
            if config.provider_type not in self._provider_builders:
                self._logger.error(f"No builder found for provider type '{config.provider_type}'")
                return False
            
            # 创建Provider实例
            builder = self._provider_builders[config.provider_type]
            provider = builder(config.config)
            
            # 验证Provider是否符合协议
            if not isinstance(provider, BaseProvider):
                self._logger.error(f"Provider does not implement BaseProvider protocol")
                return False
            
            # 初始化Provider
            if hasattr(provider, 'initialize'):
                init_success = await provider.initialize(config.config)
                if not init_success:
                    self._logger.error(f"Provider initialization failed")
                    return False
            
            # 注册Provider
            metadata = provider.get_metadata()
            if config.metadata:
                # 合并配置中的元数据
                for key, value in config.metadata.items():
                    if hasattr(metadata, key):
                        setattr(metadata, key, value)
            
            # 应用配置优先级
            metadata.priority = config.priority
            
            # 注册到注册表
            success = await self.registry.register_provider(provider, metadata)
            return success
            
        except Exception as e:
            self._logger.error(f"Failed to create provider from config: {e}")
            return False
    
    async def create_providers_from_configs(self, configs: List[ProviderConfig]) -> Dict[str, bool]:
        """批量创建Provider
        
        Args:
            configs: Provider配置列表
            
        Returns:
            每个Provider的创建结果字典
        """
        results = {}
        
        for config in configs:
            if not config.enabled:
                self._logger.info(f"Skipping disabled provider: {config.provider_type}")
                results[config.provider_type] = False
                continue
            
            success = await self.create_and_register_provider(config)
            results[config.provider_type] = success
        
        return results


# ============================================================================
# 第三部分：配置驱动创建
# ============================================================================

class ConfigurationManager:
    """配置管理器
    
    加载、解析和管理Provider配置
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._configs: Dict[str, ProviderConfig] = {}
        self._logger = logging.getLogger("ConfigurationManager")
    
    def load_from_file(self, file_path: str) -> bool:
        """从文件加载配置
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            加载是否成功
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            return self.load_from_dict(config_data)
            
        except Exception as e:
            self._logger.error(f"Failed to load config from file '{file_path}': {e}")
            return False
    
    def load_from_dict(self, config_data: Dict) -> bool:
        """从字典加载配置
        
        Args:
            config_data: 配置字典
            
        Returns:
            加载是否成功
        """
        try:
            providers_config = config_data.get("providers", [])
            
            for provider_config in providers_config:
                config = self._parse_provider_config(provider_config)
                if config:
                    self._configs[config.provider_type] = config
                    self._logger.info(f"Loaded config for provider type '{config.provider_type}'")
            
            self._logger.info(f"Loaded {len(self._configs)} provider configurations")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to load config from dict: {e}")
            return False
    
    def _parse_provider_config(self, config_dict: Dict) -> Optional[ProviderConfig]:
        """解析单个Provider配置
        
        Args:
            config_dict: Provider配置字典
            
        Returns:
            ProviderConfig对象，如果解析失败则返回None
        """
        try:
            provider_type = config_dict.get("type")
            if not provider_type:
                raise ValueError("Provider type is required")
            
            # 解析优先级
            priority_str = config_dict.get("priority", "medium").upper()
            try:
                priority = ProviderPriority[priority_str]
            except KeyError:
                priority = ProviderPriority.MEDIUM
                self._logger.warning(f"Invalid priority '{priority_str}', using MEDIUM")
            
            config = ProviderConfig(
                provider_type=provider_type,
                config=config_dict.get("config", {}),
                priority=priority,
                enabled=config_dict.get("enabled", True),
                metadata=config_dict.get("metadata")
            )
            
            return config
            
        except Exception as e:
            self._logger.error(f"Failed to parse provider config: {e}")
            return None
    
    def get_config(self, provider_type: str) -> Optional[ProviderConfig]:
        """获取指定类型的配置
        
        Args:
            provider_type: Provider类型
            
        Returns:
            Provider配置，如果不存在则返回None
        """
        return self._configs.get(provider_type)
    
    def get_all_configs(self) -> List[ProviderConfig]:
        """获取所有配置"""
        return list(self._configs.values())
    
    def add_config(self, config: ProviderConfig) -> None:
        """添加配置
        
        Args:
            config: Provider配置
        """
        self._configs[config.provider_type] = config
    
    def remove_config(self, provider_type: str) -> bool:
        """移除配置
        
        Args:
            provider_type: Provider类型
            
        Returns:
            是否成功移除
        """
        if provider_type in self._configs:
            del self._configs[provider_type]
            return True
        return False
    
    def save_to_file(self, file_path: str) -> bool:
        """保存配置到文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            保存是否成功
        """
        try:
            config_data = {
                "providers": [config.to_dict() for config in self._configs.values()]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self._logger.info(f"Saved config to file '{file_path}'")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to save config to file '{file_path}': {e}")
            return False


class ProviderOrchestrator:
    """Provider协调器
    
    集成注册表、工厂和配置管理器，提供完整的Provider管理功能
    """
    
    def __init__(self, registry_name: str = "default"):
        self.registry = ProviderRegistry(registry_name)
        self.factory = ProviderFactory(self.registry)
        self.config_manager = ConfigurationManager()
        self._logger = logging.getLogger("ProviderOrchestrator")
    
    async def initialize_from_config(self, config_path: str) -> bool:
        """从配置文件初始化所有Provider
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            初始化是否成功
        """
        # 加载配置
        if not self.config_manager.load_from_file(config_path):
            self._logger.error("Failed to load configuration")
            return False
        
        # 创建所有Provider
        configs = self.config_manager.get_all_configs()
        results = await self.factory.create_providers_from_configs(configs)
        
        # 统计结果
        total = len(results)
        successful = sum(1 for success in results.values() if success)
        
        self._logger.info(f"Initialized {successful}/{total} providers from config")
        return successful > 0
    
    async def get_provider_for_capability(self, 
                                         capability: ProviderCapability,
                                         priority: ProviderPriority = ProviderPriority.MEDIUM) -> Optional[BaseProvider]:
        """获取具有指定能力的Provider
        
        Args:
            capability: 所需能力
            priority: 期望优先级
            
        Returns:
            Provider实例，如果找不到则返回None
        """
        selection_result = await self.registry.select_provider(capability, priority)
        if selection_result:
            return selection_result.provider_instance
        return None
    
    async def list_available_capabilities(self) -> List[ProviderCapability]:
        """列出所有可用的能力"""
        all_capabilities = set()
        
        for metadata in self.registry._metadata_cache.values():
            if metadata.status == ProviderStatus.AVAILABLE:
                all_capabilities.update(metadata.capabilities)
        
        return list(all_capabilities)
    
    async def shutdown_all(self) -> None:
        """关闭所有Provider"""
        provider_names = list(self.registry._providers.keys())
        
        for name in provider_names:
            try:
                await self.registry.unregister_provider(name)
            except Exception as e:
                self._logger.error(f"Error shutting down provider '{name}': {e}")
        
        self._logger.info(f"Shutdown {len(provider_names)} providers")


# ============================================================================
# 第四部分：测试与演示
# ============================================================================

# 示例Provider实现
class ExampleProvider:
    """示例Provider实现"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", "example_provider")
        self.healthy = True
    
    def get_metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name=self.name,
            description="示例Provider，用于演示Provider模式",
            version="1.0.0",
            author="DeerFlow Team",
            capabilities=[
                ProviderCapability.DYNAMIC_DISCOVERY,
                ProviderCapability.CONFIG_DRIVEN
            ],
            status=ProviderStatus.AVAILABLE,
            priority=ProviderPriority.MEDIUM,
            tags=["example", "demo"]
        )
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        self._logger = logging.getLogger(f"ExampleProvider.{self.name}")
        self._logger.info(f"Initializing with config: {config}")
        return True
    
    async def shutdown(self) -> None:
        self._logger.info("Shutting down")
        self.healthy = False
    
    def is_healthy(self) -> bool:
        return self.healthy
    
    async def perform_task(self, task_data: Dict) -> Dict:
        """执行示例任务"""
        return {
            "task": task_data.get("task", "unknown"),
            "result": "success",
            "provider": self.name,
            "timestamp": time.time()
        }


class HighPriorityProvider(ExampleProvider):
    """高优先级Provider示例"""
    
    def get_metadata(self) -> ProviderMetadata:
        metadata = super().get_metadata()
        metadata.name = "high_priority_provider"
        metadata.description = "高优先级示例Provider"
        metadata.priority = ProviderPriority.HIGH
        metadata.capabilities.append(ProviderCapability.PERFORMANCE_MONITOR)
        return metadata


class LowPriorityProvider(ExampleProvider):
    """低优先级Provider示例"""
    
    def get_metadata(self) -> ProviderMetadata:
        metadata = super().get_metadata()
        metadata.name = "low_priority_provider"
        metadata.description = "低优先级示例Provider"
        metadata.priority = ProviderPriority.LOW
        metadata.capabilities.append(ProviderCapability.HEALTH_CHECK)
        return metadata


class ProviderTestSuite:
    """Provider测试套件"""
    
    def __init__(self):
        self._logger = logging.getLogger("ProviderTestSuite")
        self.results = {}
    
    async def run_all_tests(self) -> Dict:
        """运行所有测试"""
        self.results = {}
        
        # 测试1：基本注册功能
        await self._test_basic_registration()
        
        # 测试2：Provider选择功能
        await self._test_provider_selection()
        
        # 测试3：配置驱动创建
        await self._test_config_driven_creation()
        
        # 测试4：优先级匹配
        await self._test_priority_matching()
        
        # 测试5：动态注册和注销
        await self._test_dynamic_registration()
        
        # 测试6：协调器集成测试
        await self._test_orchestrator_integration()
        
        # 生成测试报告
        report = self._generate_report()
        return report
    
    async def _test_basic_registration(self):
        """测试基本注册功能"""
        test_name = "test_basic_registration"
        start_time = time.time()
        
        try:
            registry = ProviderRegistry("test_basic")
            provider = ExampleProvider({"name": "test_provider"})
            
            # 测试注册
            success = await registry.register_provider(provider)
            assert success, "Provider registration failed"
            
            # 测试获取
            retrieved = await registry.get_provider("test_provider")
            assert retrieved is not None, "Failed to retrieve registered provider"
            
            # 测试列表
            providers = await registry.list_providers()
            assert len(providers) == 1, "Expected 1 provider in list"
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Basic registration test passed"
            }
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Basic registration test failed: {e}"
            }
    
    async def _test_provider_selection(self):
        """测试Provider选择功能"""
        test_name = "test_provider_selection"
        start_time = time.time()
        
        try:
            registry = ProviderRegistry("test_selection")
            
            # 注册多个Provider
            provider1 = ExampleProvider({"name": "provider1"})
            provider2 = ExampleProvider({"name": "provider2"})
            
            await registry.register_provider(provider1)
            await registry.register_provider(provider2)
            
            # 测试能力选择
            result = await registry.select_provider(ProviderCapability.DYNAMIC_DISCOVERY)
            assert result is not None, "Failed to select provider by capability"
            assert result.provider_name in ["provider1", "provider2"], "Selected wrong provider"
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Provider selection test passed"
            }
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Provider selection test failed: {e}"
            }
    
    async def _test_config_driven_creation(self):
        """测试配置驱动创建"""
        test_name = "test_config_driven_creation"
        start_time = time.time()
        
        try:
            registry = ProviderRegistry("test_config")
            factory = ProviderFactory(registry)
            
            # 注册构建器
            factory.register_builder("example", lambda config: ExampleProvider(config))
            
            # 创建配置
            config = ProviderConfig(
                provider_type="example",
                config={"name": "config_provider"},
                priority=ProviderPriority.MEDIUM
            )
            
            # 从配置创建Provider
            success = await factory.create_and_register_provider(config)
            assert success, "Failed to create provider from config"
            
            # 验证Provider已注册
            provider = await registry.get_provider("config_provider")
            assert provider is not None, "Provider not found after config creation"
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Config-driven creation test passed"
            }
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Config-driven creation test failed: {e}"
            }
    
    async def _test_priority_matching(self):
        """测试优先级匹配"""
        test_name = "test_priority_matching"
        start_time = time.time()
        
        try:
            registry = ProviderRegistry("test_priority")
            
            # 注册不同优先级的Provider
            high_provider = HighPriorityProvider({"name": "high_provider"})
            low_provider = LowPriorityProvider({"name": "low_provider"})
            
            await registry.register_provider(high_provider)
            await registry.register_provider(low_provider)
            
            # 测试高优先级选择
            result = await registry.select_provider(
                ProviderCapability.DYNAMIC_DISCOVERY,
                ProviderPriority.HIGH
            )
            assert result is not None, "Failed to select provider with HIGH priority"
            # 应该选择高优先级Provider（分数更高）
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Priority matching test passed"
            }
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Priority matching test failed: {e}"
            }
    
    async def _test_dynamic_registration(self):
        """测试动态注册和注销"""
        test_name = "test_dynamic_registration"
        start_time = time.time()
        
        try:
            registry = ProviderRegistry("test_dynamic")
            
            # 动态注册
            provider = ExampleProvider({"name": "dynamic_provider"})
            success = await registry.register_provider(provider)
            assert success, "Dynamic registration failed"
            
            # 验证已注册
            providers = await registry.list_providers()
            assert len(providers) == 1, "Expected 1 provider after registration"
            
            # 动态注销
            success = await registry.unregister_provider("dynamic_provider")
            assert success, "Dynamic unregistration failed"
            
            # 验证已注销
            providers = await registry.list_providers()
            assert len(providers) == 0, "Expected 0 providers after unregistration"
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Dynamic registration test passed"
            }
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Dynamic registration test failed: {e}"
            }
    
    async def _test_orchestrator_integration(self):
        """测试协调器集成"""
        test_name = "test_orchestrator_integration"
        start_time = time.time()
        
        try:
            orchestrator = ProviderOrchestrator("test_integration")
            
            # 手动注册构建器
            orchestrator.factory.register_builder("example", lambda config: ExampleProvider(config))
            
            # 创建测试配置
            test_config = {
                "providers": [
                    {
                        "type": "example",
                        "config": {"name": "orchestrator_provider"},
                        "priority": "medium",
                        "enabled": True
                    }
                ]
            }
            
            # 加载配置
            success = orchestrator.config_manager.load_from_dict(test_config)
            assert success, "Failed to load test configuration"
            
            # 创建Provider
            configs = orchestrator.config_manager.get_all_configs()
            results = await orchestrator.factory.create_providers_from_configs(configs)
            assert any(results.values()), "Failed to create any providers from config"
            
            # 测试能力查询
            capabilities = await orchestrator.list_available_capabilities()
            assert ProviderCapability.DYNAMIC_DISCOVERY in capabilities, "Expected capability not found"
            
            # 测试Provider选择
            provider = await orchestrator.get_provider_for_capability(
                ProviderCapability.DYNAMIC_DISCOVERY
            )
            assert provider is not None, "Failed to get provider by capability"
            
            # 清理
            await orchestrator.shutdown_all()
            
            self.results[test_name] = {
                "passed": True,
                "execution_time": time.time() - start_time,
                "message": "Orchestrator integration test passed"
            }
            
        except Exception as e:
            self.results[test_name] = {
                "passed": False,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "message": f"Orchestrator integration test failed: {e}"
            }
    
    def _generate_report(self) -> Dict:
        """生成测试报告"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["passed"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate,
                "timestamp": time.time()
            },
            "detailed_results": self.results
        }
        
        return report


async def main_demo():
    """主演示函数"""
    print("=" * 80)
    print("🎓 Day 8 Lesson 30: Provider模式实现演示")
    print("=" * 80)
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("\n1. 创建Provider注册表和工厂...")
    registry = ProviderRegistry("demo_registry")
    factory = ProviderFactory(registry)
    
    # 注册构建器
    factory.register_builder("example", lambda config: ExampleProvider(config))
    factory.register_builder("high_priority", lambda config: HighPriorityProvider(config))
    factory.register_builder("low_priority", lambda config: LowPriorityProvider(config))
    
    print("   ✅ 注册了3种Provider构建器")
    
    print("\n2. 从配置创建Provider...")
    configs = [
        ProviderConfig(
            provider_type="example",
            config={"name": "demo_provider_1"},
            priority=ProviderPriority.MEDIUM
        ),
        ProviderConfig(
            provider_type="high_priority",
            config={"name": "demo_provider_high"},
            priority=ProviderPriority.HIGH
        ),
        ProviderConfig(
            provider_type="low_priority",
            config={"name": "demo_provider_low"},
            priority=ProviderPriority.LOW
        )
    ]
    
    results = await factory.create_providers_from_configs(configs)
    created_count = sum(1 for success in results.values() if success)
    print(f"   ✅ 成功创建了 {created_count}/{len(configs)} 个Provider")
    
    print("\n3. 列出所有已注册的Provider...")
    providers = await registry.list_providers()
    for i, metadata in enumerate(providers, 1):
        print(f"   {i}. {metadata.name} (v{metadata.version}) - {metadata.description}")
        print(f"      能力: {', '.join([cap.value for cap in metadata.capabilities])}")
        print(f"      优先级: {metadata.priority.value}, 状态: {metadata.status.value}")
    
    print("\n4. 测试Provider选择功能...")
    print("   选择具有 DYNAMIC_DISCOVERY 能力的Provider:")
    result = await registry.select_provider(ProviderCapability.DYNAMIC_DISCOVERY)
    if result:
        print(f"   ✅ 选择: {result.provider_name}")
        print(f"      原因: {result.selection_reason}")
        print(f"      耗时: {result.selection_time:.3f}s")
        
        # 使用选中的Provider执行任务
        if hasattr(result.provider_instance, 'perform_task'):
            task_result = await result.provider_instance.perform_task({"task": "demo_task"})
            print(f"      任务结果: {task_result}")
    else:
        print("   ❌ 未找到合适的Provider")
    
    print("\n5. 测试优先级匹配...")
    print("   请求 HIGH 优先级的Provider:")
    result = await registry.select_provider(
        ProviderCapability.DYNAMIC_DISCOVERY,
        ProviderPriority.HIGH
    )
    if result:
        print(f"   ✅ 选择: {result.provider_name} (优先级: {result.metadata.priority.value})")
    
    print("\n6. 测试动态注册和注销...")
    dynamic_provider = ExampleProvider({"name": "dynamic_demo_provider"})
    success = await registry.register_provider(dynamic_provider)
    if success:
        print(f"   ✅ 动态注册成功: {dynamic_provider.get_metadata().name}")
        
        providers_after = await registry.list_providers()
        print(f"   注册后Provider数量: {len(providers_after)}")
        
        # 注销
        success = await registry.unregister_provider("dynamic_demo_provider")
        if success:
            print(f"   ✅ 动态注销成功")
    
    print("\n7. 测试协调器集成...")
    orchestrator = ProviderOrchestrator("demo_orchestrator")
    orchestrator.factory.register_builder("example", lambda config: ExampleProvider(config))
    
    # 创建测试配置
    test_config = {
        "providers": [
            {
                "type": "example",
                "config": {"name": "orchestrator_demo"},
                "priority": "medium",
                "enabled": True,
                "metadata": {
                    "tags": ["demo", "orchestrator"]
                }
            }
        ]
    }
    
    orchestrator.config_manager.load_from_dict(test_config)
    
    capabilities = await orchestrator.list_available_capabilities()
    print(f"   可用能力: {', '.join([cap.value for cap in capabilities])}")
    
    print("\n8. 运行测试套件...")
    test_suite = ProviderTestSuite()
    report = await test_suite.run_all_tests()
    
    summary = report['summary']
    print(f"   测试总数: {summary['total_tests']}")
    print(f"   通过测试: {summary['passed_tests']}")
    print(f"   失败测试: {summary['failed_tests']}")
    print(f"   成功率: {summary['success_rate']:.1f}%")
    
    print("\n9. 注册表统计信息:")
    stats = registry.get_registry_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.3f}")
        else:
            print(f"   {key}: {value}")
    
    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


async def run_tests():
    """运行测试套件"""
    print("运行Provider模式测试套件...")
    test_suite = ProviderTestSuite()
    report = await test_suite.run_all_tests()
    
    summary = report['summary']
    print(f"\n测试摘要:")
    print(f"  测试总数: {summary['total_tests']}")
    print(f"  通过测试: {summary['passed_tests']}")
    print(f"  失败测试: {summary['failed_tests']}")
    print(f"  成功率: {summary['success_rate']:.1f}%")
    
    print("\n详细结果:")
    for test_name, test_result in report['detailed_results'].items():
        status = "✅ 通过" if test_result['passed'] else "❌ 失败"
        print(f"  {status} {test_name} ({test_result['execution_time']:.3f}s)")
        if not test_result['passed'] and 'error' in test_result:
            print(f"    错误: {test_result['error']}")
    
    return summary['success_rate'] >= 100.0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Provider模式实现演示程序")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行完整演示")
    parser.add_argument("--help", action="store_true", help="显示帮助信息")
    
    args = parser.parse_args()
    
    if args.test:
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    elif args.demo or (not args.test and not args.demo):
        asyncio.run(main_demo())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()