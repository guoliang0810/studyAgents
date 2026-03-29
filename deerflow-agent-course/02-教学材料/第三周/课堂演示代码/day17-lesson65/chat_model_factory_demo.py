#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_chat_model工厂演示代码
Day 17 - 第65节课：create_chat_model工厂

本演示代码展示了DeerFlow Agent系统中模型工厂的核心实现，包括：
1. ModelConfig数据类：定义模型配置和能力
2. ChatModelFactory：基于工厂模式的模型创建系统
3. 模型提供商抽象层：统一不同AI模型提供商接口
4. 模型实例缓存机制：提高性能和资源利用率
5. 配置模糊匹配和友好错误提示：提升开发者体验

学习目标：
- 掌握工厂模式在AI模型管理中的应用
- 理解模型配置数据类的设计和解析方法
- 能够实现模型实例缓存机制
- 能够设计多模型提供商的统一接口
- 能够构建完整的模型工厂系统
"""

import os
import sys
import time
import hashlib
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Type, Tuple, Union
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from functools import lru_cache
from collections import defaultdict
import difflib

# ============================================================================
# 数据类和枚举定义
# ============================================================================

@dataclass
class ModelCapabilities:
    """模型能力定义
    
    Attributes:
        supports_function_calling: 是否支持函数调用
        supports_vision: 是否支持视觉输入
        supports_streaming: 是否支持流式输出
        max_tokens: 最大token数限制
        supports_json_mode: 是否支持JSON模式输出
        supports_tool_use: 是否支持工具使用
        supports_parallel_tool_calls: 是否支持并行工具调用
    """
    supports_function_calling: bool = False
    supports_vision: bool = False
    supports_streaming: bool = True
    max_tokens: int = 4096
    supports_json_mode: bool = False
    supports_tool_use: bool = False
    supports_parallel_tool_calls: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelCapabilities":
        """从字典创建"""
        return cls(**data)


class ModelProviderType(Enum):
    """模型提供商类型枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    LOCAL = "local"
    AZURE = "azure"
    BEDROCK = "bedrock"


@dataclass
class ModelConfig:
    """模型配置数据类
    
    Attributes:
        provider: 模型提供商（如openai、anthropic）
        model_name: 模型名称（如gpt-4-turbo、claude-3-opus）
        config: 模型配置字典（API密钥、端点等）
        capabilities: 模型能力列表
        cost_per_token: 每token成本（美元）
        max_batch_size: 最大批处理大小
        rate_limit_rpm: 速率限制（每分钟请求数）
        timeout_seconds: 超时时间（秒）
        description: 模型描述
        version: 模型版本
    """
    provider: str
    model_name: str
    config: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    cost_per_token: float = 0.0
    max_batch_size: int = 1
    rate_limit_rpm: int = 60
    timeout_seconds: float = 30.0
    description: str = ""
    version: str = "1.0.0"
    
    def __post_init__(self):
        """后初始化处理"""
        # 确保配置字典不为None
        if self.config is None:
            self.config = {}
        # 确保能力列表不为None
        if self.capabilities is None:
            self.capabilities = []
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        """从字典创建配置
        
        Args:
            data: 配置字典
            
        Returns:
            ModelConfig: 配置对象
        """
        return cls(
            provider=data.get("provider", ""),
            model_name=data.get("model_name", ""),
            config=data.get("config", {}),
            capabilities=data.get("capabilities", []),
            cost_per_token=data.get("cost_per_token", 0.0),
            max_batch_size=data.get("max_batch_size", 1),
            rate_limit_rpm=data.get("rate_limit_rpm", 60),
            timeout_seconds=data.get("timeout_seconds", 30.0),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0")
        )
    
    def has_capability(self, capability: str) -> bool:
        """检查是否支持某个能力
        
        Args:
            capability: 能力名称
            
        Returns:
            bool: 是否支持
        """
        return capability.lower() in [c.lower() for c in self.capabilities]
    
    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """估算使用成本
        
        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数
            
        Returns:
            float: 估算成本（美元）
        """
        total_tokens = input_tokens + output_tokens
        return total_tokens * self.cost_per_token
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @property
    def cache_key(self) -> str:
        """生成缓存键"""
        config_str = json.dumps(self.config, sort_keys=True)
        key_data = f"{self.provider}:{self.model_name}:{config_str}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]


# ============================================================================
# 模型基类和提供商抽象
# ============================================================================

class BaseChatModel(ABC):
    """聊天模型基类
    
    定义所有聊天模型必须实现的接口。
    """
    
    def __init__(self, config: ModelConfig):
        """初始化模型
        
        Args:
            config: 模型配置
        """
        self.config = config
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    @property
    @abstractmethod
    def name(self) -> str:
        """模型名称"""
        pass
    
    @property
    @abstractmethod
    def provider(self) -> str:
        """模型提供商"""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> ModelCapabilities:
        """模型能力"""
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            str: 生成的文本
        """
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        **kwargs
    ):
        """流式生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
            
        Yields:
            str: 生成的文本片段
        """
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """聊天对话
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Returns:
            Dict[str, Any]: 聊天响应
        """
        pass
    
    def validate_config(self) -> bool:
        """验证配置
        
        Returns:
            bool: 配置是否有效
        """
        required_fields = ["api_key", "endpoint"]
        for field in required_fields:
            if field in self.config.config and not self.config.config[field]:
                self.logger.warning(f"缺少必需字段: {field}")
                return False
        return True


class OpenAIProvider(BaseChatModel):
    """OpenAI模型提供商"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        # 实际项目中这里会初始化OpenAI客户端
        self._client = None
    
    @property
    def name(self) -> str:
        return self.config.model_name
    
    @property
    def provider(self) -> str:
        return "openai"
    
    @property
    def capabilities(self) -> ModelCapabilities:
        # 根据模型名称返回不同的能力
        model_name = self.config.model_name.lower()
        
        if "gpt-4" in model_name:
            return ModelCapabilities(
                supports_function_calling=True,
                supports_vision="vision" in model_name,
                supports_streaming=True,
                max_tokens=8192 if "32k" in model_name else 4096,
                supports_json_mode=True,
                supports_tool_use=True,
                supports_parallel_tool_calls=True
            )
        elif "gpt-3.5" in model_name:
            return ModelCapabilities(
                supports_function_calling=True,
                supports_vision=False,
                supports_streaming=True,
                max_tokens=4096,
                supports_json_mode=True,
                supports_tool_use=True,
                supports_parallel_tool_calls=False
            )
        else:
            return ModelCapabilities()
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本（模拟实现）"""
        self.logger.info(f"OpenAI生成请求: {self.name}")
        
        # 模拟API调用延迟
        await asyncio.sleep(0.1)
        
        # 返回模拟响应
        return f"OpenAI响应({self.name}): 这是对'{prompt[:30]}...'的模拟响应"
    
    async def generate_stream(self, prompt: str, **kwargs):
        """流式生成文本（模拟实现）"""
        self.logger.info(f"OpenAI流式生成: {self.name}")
        
        words = prompt.split()[:10]
        for i, word in enumerate(words):
            await asyncio.sleep(0.05)
            yield f"{word} "
        
        yield "[流式生成完成]"
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """聊天对话（模拟实现）"""
        self.logger.info(f"OpenAI聊天: {self.name}")
        
        await asyncio.sleep(0.1)
        
        return {
            "role": "assistant",
            "content": f"OpenAI聊天响应({self.name}): 收到了{len(messages)}条消息",
            "model": self.name,
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }


class AnthropicProvider(BaseChatModel):
    """Anthropic模型提供商"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
    
    @property
    def name(self) -> str:
        return self.config.model_name
    
    @property
    def provider(self) -> str:
        return "anthropic"
    
    @property
    def capabilities(self) -> ModelCapabilities:
        model_name = self.config.model_name.lower()
        
        if "claude-3" in model_name:
            return ModelCapabilities(
                supports_function_calling=True,
                supports_vision=True,
                supports_streaming=True,
                max_tokens=8192 if "200k" in model_name else 4096,
                supports_json_mode=False,
                supports_tool_use=True,
                supports_parallel_tool_calls=True
            )
        else:
            return ModelCapabilities()
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本（模拟实现）"""
        self.logger.info(f"Anthropic生成请求: {self.name}")
        
        await asyncio.sleep(0.15)
        
        return f"Anthropic响应({self.name}): 这是对'{prompt[:30]}...'的模拟响应"
    
    async def generate_stream(self, prompt: str, **kwargs):
        """流式生成文本（模拟实现）"""
        self.logger.info(f"Anthropic流式生成: {self.name}")
        
        words = prompt.split()[:8]
        for i, word in enumerate(words):
            await asyncio.sleep(0.06)
            yield f"{word} "
        
        yield "[流式生成完成]"
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """聊天对话（模拟实现）"""
        self.logger.info(f"Anthropic聊天: {self.name}")
        
        await asyncio.sleep(0.15)
        
        return {
            "role": "assistant",
            "content": f"Anthropic聊天响应({self.name}): 收到了{len(messages)}条消息",
            "model": self.name,
            "usage": {"prompt_tokens": 120, "completion_tokens": 60}
        }


class LocalProvider(BaseChatModel):
    """本地模型提供商"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
    
    @property
    def name(self) -> str:
        return self.config.model_name
    
    @property
    def provider(self) -> str:
        return "local"
    
    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_function_calling=False,
            supports_vision=False,
            supports_streaming=False,
            max_tokens=2048,
            supports_json_mode=False,
            supports_tool_use=False,
            supports_parallel_tool_calls=False
        )
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本（模拟实现）"""
        self.logger.info(f"本地模型生成请求: {self.name}")
        
        await asyncio.sleep(0.05)
        
        return f"本地模型响应({self.name}): 这是对'{prompt[:30]}...'的模拟响应"
    
    async def generate_stream(self, prompt: str, **kwargs):
        """流式生成文本（模拟实现）"""
        self.logger.info(f"本地模型流式生成: {self.name}")
        
        words = prompt.split()[:5]
        for i, word in enumerate(words):
            await asyncio.sleep(0.1)
            yield f"{word} "
        
        yield "[流式生成完成]"
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """聊天对话（模拟实现）"""
        self.logger.info(f"本地模型聊天: {self.name}")
        
        await asyncio.sleep(0.05)
        
        return {
            "role": "assistant",
            "content": f"本地模型聊天响应({self.name}): 收到了{len(messages)}条消息",
            "model": self.name,
            "usage": {"prompt_tokens": 80, "completion_tokens": 40}
        }


# ============================================================================
# 模型工厂核心实现
# ============================================================================

class ChatModelFactory:
    """聊天模型工厂
    
    基于工厂模式创建和管理聊天模型实例。
    """
    
    # 提供商映射表
    PROVIDERS: Dict[str, Type[BaseChatModel]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "local": LocalProvider
    }
    
    def __init__(self, configs: Dict[str, ModelConfig]):
        """初始化模型工厂
        
        Args:
            configs: 模型配置字典，键为模型名称，值为ModelConfig对象
        """
        self.configs = configs
        self.cache: Dict[str, BaseChatModel] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._creation_times: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger("ChatModelFactory")
        
        # 验证所有配置
        self._validate_configs()
    
    def _validate_configs(self):
        """验证所有模型配置"""
        for model_name, config in self.configs.items():
            if not config.provider or not config.model_name:
                raise ValueError(f"模型配置无效: {model_name} - 缺少provider或model_name")
            
            if config.provider not in self.PROVIDERS:
                self.logger.warning(f"未知的模型提供商: {config.provider}，模型: {model_name}")
    
    def register_provider(self, name: str, provider_class: Type[BaseChatModel]):
        """注册新的模型提供商
        
        Args:
            name: 提供商名称
            provider_class: 提供商类
        """
        self.PROVIDERS[name] = provider_class
        self.logger.info(f"注册模型提供商: {name}")
    
    async def create(
        self,
        model_name: str,
        use_cache: bool = True,
        **runtime_params
    ) -> BaseChatModel:
        """创建模型实例
        
        Args:
            model_name: 模型名称
            use_cache: 是否使用缓存
            **runtime_params: 运行时参数（覆盖配置）
            
        Returns:
            BaseChatModel: 模型实例
            
        Raises:
            ValueError: 模型未找到或创建失败
        """
        start_time = time.time()
        
        async with self._lock:
            # 生成缓存键
            cache_key = self._generate_cache_key(model_name, runtime_params)
            
            # 检查缓存
            if use_cache and cache_key in self.cache:
                self._cache_hits += 1
                self.logger.debug(f"缓存命中: {model_name} ({cache_key})")
                return self.cache[cache_key]
            
            self._cache_misses += 1
            
            try:
                # 获取模型配置
                model_config = self.get_model_config(model_name)
                
                # 合并运行时参数
                merged_config = self._merge_configs(model_config, runtime_params)
                
                # 获取提供商类
                provider_class = self.PROVIDERS.get(merged_config.provider)
                if not provider_class:
                    # 尝试查找相似的提供商
                    similar = self._find_similar_provider(merged_config.provider)
                    if similar:
                        raise ValueError(
                            f"未知的模型提供商: {merged_config.provider}，您是指 {similar} 吗？"
                        )
                    raise ValueError(f"未知的模型提供商: {merged_config.provider}")
                
                # 创建模型实例
                model = provider_class(merged_config)
                
                # 验证模型配置
                if not model.validate_config():
                    self.logger.warning(f"模型配置验证失败: {model_name}")
                
                # 缓存模型实例
                if use_cache:
                    self.cache[cache_key] = model
                    self.logger.debug(f"缓存模型: {model_name} ({cache_key})")
                
                # 记录创建时间
                creation_time = time.time() - start_time
                self._creation_times[model_name].append(creation_time)
                
                self.logger.info(f"创建模型: {model_name} (耗时: {creation_time:.3f}s)")
                
                return model
                
            except Exception as e:
                self.logger.error(f"创建模型失败: {model_name} - {str(e)}")
                raise
    
    def get_model_config(self, model_name: str) -> ModelConfig:
        """获取模型配置
        
        Args:
            model_name: 模型名称
            
        Returns:
            ModelConfig: 模型配置
            
        Raises:
            ValueError: 模型未找到
        """
        config = self.configs.get(model_name)
        if not config:
            # 尝试模糊匹配
            similar = self._find_similar_model(model_name)
            if similar:
                raise ValueError(
                    f"模型 '{model_name}' 未找到，您是指 '{similar}' 吗？"
                )
            raise ValueError(f"模型 '{model_name}' 未找到")
        
        return config
    
    def _generate_cache_key(self, model_name: str, runtime_params: Dict[str, Any]) -> str:
        """生成缓存键
        
        Args:
            model_name: 模型名称
            runtime_params: 运行时参数
            
        Returns:
            str: 缓存键
        """
        # 获取模型配置
        config = self.get_model_config(model_name)
        
        # 合并参数
        params = {**config.config, **runtime_params}
        
        # 排序参数以确保一致性
        sorted_params = json.dumps(params, sort_keys=True)
        
        # 生成哈希
        key_data = f"{config.provider}:{config.model_name}:{sorted_params}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    def _merge_configs(
        self,
        base_config: ModelConfig,
        runtime_params: Dict[str, Any]
    ) -> ModelConfig:
        """合并基础配置和运行时参数
        
        Args:
            base_config: 基础配置
            runtime_params: 运行时参数
            
        Returns:
            ModelConfig: 合并后的配置
        """
        # 创建配置副本
        merged_config = ModelConfig.from_dict(base_config.to_dict())
        
        # 合并配置参数
        merged_config.config = {**merged_config.config, **runtime_params}
        
        return merged_config
    
    def _find_similar_model(self, model_name: str, threshold: float = 0.6) -> Optional[str]:
        """查找相似的模型名称
        
        Args:
            model_name: 目标模型名称
            threshold: 相似度阈值
            
        Returns:
            Optional[str]: 相似的模型名称，如果没有则返回None
        """
        if not self.configs:
            return None
        
        # 计算字符串相似度
        model_names = list(self.configs.keys())
        matches = difflib.get_close_matches(model_name, model_names, n=1, cutoff=threshold)
        
        return matches[0] if matches else None
    
    def _find_similar_provider(self, provider_name: str, threshold: float = 0.6) -> Optional[str]:
        """查找相似的提供商名称
        
        Args:
            provider_name: 目标提供商名称
            threshold: 相似度阈值
            
        Returns:
            Optional[str]: 相似的提供商名称，如果没有则返回None
        """
        provider_names = list(self.PROVIDERS.keys())
        matches = difflib.get_close_matches(provider_name, provider_names, n=1, cutoff=threshold)
        
        return matches[0] if matches else None
    
    def clear_cache(self):
        """清空模型缓存"""
        cache_size = len(self.cache)
        self.cache.clear()
        self.logger.info(f"清空模型缓存，释放了 {cache_size} 个模型实例")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计
        """
        return {
            "cache_size": len(self.cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": (
                self._cache_hits / (self._cache_hits + self._cache_misses)
                if (self._cache_hits + self._cache_misses) > 0 else 0
            ),
            "average_creation_time": {
                model: sum(times) / len(times) if times else 0
                for model, times in self._creation_times.items()
            }
        }
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型信息
        
        Args:
            model_name: 模型名称
            
        Returns:
            Dict[str, Any]: 模型信息
        """
        config = self.get_model_config(model_name)
        
        return {
            "name": model_name,
            "provider": config.provider,
            "description": config.description,
            "version": config.version,
            "capabilities": config.capabilities,
            "cost_per_token": config.cost_per_token,
            "max_batch_size": config.max_batch_size,
            "rate_limit_rpm": config.rate_limit_rpm,
            "timeout_seconds": config.timeout_seconds
        }
    
    def list_models(self) -> List[Dict[str, Any]]:
        """列出所有可用模型
        
        Returns:
            List[Dict[str, Any]]: 模型列表
        """
        models = []
        for model_name, config in self.configs.items():
            models.append({
                "name": model_name,
                "provider": config.provider,
                "description": config.description,
                "capabilities": config.capabilities[:3]  # 只显示前3个能力
            })
        
        return models


# ============================================================================
# 高级功能：动态注册和插件系统
# ============================================================================

class ModelFactoryRegistry:
    """模型工厂注册表
    
    支持动态注册和发现模型提供商。
    """
    
    def __init__(self):
        self._providers: Dict[str, Type[BaseChatModel]] = {}
        self._plugins: Dict[str, Any] = {}
        self._initialized = False
    
    def register_provider(self, name: str, provider_class: Type[BaseChatModel]):
        """注册模型提供商
        
        Args:
            name: 提供商名称
            provider_class: 提供商类
        """
        if not issubclass(provider_class, BaseChatModel):
            raise TypeError(f"提供商类必须继承自 BaseChatModel: {provider_class}")
        
        self._providers[name] = provider_class
        logging.info(f"注册模型提供商: {name} -> {provider_class.__name__}")
    
    def register_plugin(self, name: str, plugin: Any):
        """注册插件
        
        Args:
            name: 插件名称
            plugin: 插件对象
        """
        self._plugins[name] = plugin
        logging.info(f"注册插件: {name}")
    
    def get_provider(self, name: str) -> Optional[Type[BaseChatModel]]:
        """获取提供商类
        
        Args:
            name: 提供商名称
            
        Returns:
            Optional[Type[BaseChatModel]]: 提供商类，如果未找到则返回None
        """
        return self._providers.get(name)
    
    def get_providers(self) -> Dict[str, Type[BaseChatModel]]:
        """获取所有提供商
        
        Returns:
            Dict[str, Type[BaseChatModel]]: 提供商字典
        """
        return self._providers.copy()
    
    def discover_plugins(self, plugin_dir: str):
        """发现并加载插件
        
        Args:
            plugin_dir: 插件目录路径
        """
        if not os.path.exists(plugin_dir):
            logging.warning(f"插件目录不存在: {plugin_dir}")
            return
        
        # 简化实现：实际项目中会动态导入Python模块
        logging.info(f"发现插件目录: {plugin_dir}")
    
    def initialize(self):
        """初始化注册表"""
        if self._initialized:
            return
        
        # 注册内置提供商
        self.register_provider("openai", OpenAIProvider)
        self.register_provider("anthropic", AnthropicProvider)
        self.register_provider("local", LocalProvider)
        
        self._initialized = True
        logging.info("模型工厂注册表初始化完成")


# ============================================================================
# 演示函数
# ============================================================================

def create_sample_configs() -> Dict[str, ModelConfig]:
    """创建示例模型配置
    
    Returns:
        Dict[str, ModelConfig]: 模型配置字典
    """
    configs = {}
    
    # OpenAI模型配置
    configs["gpt-4-turbo"] = ModelConfig(
        provider="openai",
        model_name="gpt-4-turbo-preview",
        config={
            "api_key": "sk-...",
            "endpoint": "https://api.openai.com/v1",
            "temperature": 0.7,
            "max_tokens": 4096
        },
        capabilities=["function_calling", "json_mode", "streaming", "vision"],
        cost_per_token=0.00001,
        max_batch_size=10,
        rate_limit_rpm=1000,
        timeout_seconds=30.0,
        description="OpenAI GPT-4 Turbo模型，支持函数调用和视觉",
        version="2024-01-01"
    )
    
    configs["gpt-3.5-turbo"] = ModelConfig(
        provider="openai",
        model_name="gpt-3.5-turbo",
        config={
            "api_key": "sk-...",
            "endpoint": "https://api.openai.com/v1",
            "temperature": 0.7,
            "max_tokens": 4096
        },
        capabilities=["function_calling", "json_mode", "streaming"],
        cost_per_token=0.000001,
        max_batch_size=20,
        rate_limit_rpm=2000,
        timeout_seconds=30.0,
        description="OpenAI GPT-3.5 Turbo模型，性价比高",
        version="2024-01-01"
    )
    
    # Anthropic模型配置
    configs["claude-3-opus"] = ModelConfig(
        provider="anthropic",
        model_name="claude-3-opus-20240229",
        config={
            "api_key": "sk-ant-...",
            "endpoint": "https://api.anthropic.com",
            "temperature": 0.7,
            "max_tokens": 4096
        },
        capabilities=["function_calling", "vision", "streaming", "tool_use"],
        cost_per_token=0.000015,
        max_batch_size=5,
        rate_limit_rpm=500,
        timeout_seconds=60.0,
        description="Anthropic Claude 3 Opus模型，性能强大",
        version="2024-02-29"
    )
    
    configs["claude-3-sonnet"] = ModelConfig(
        provider="anthropic",
        model_name="claude-3-sonnet-20240229",
        config={
            "api_key": "sk-ant-...",
            "endpoint": "https://api.anthropic.com",
            "temperature": 0.7,
            "max_tokens": 4096
        },
        capabilities=["function_calling", "vision", "streaming", "tool_use"],
        cost_per_token=0.000003,
        max_batch_size=10,
        rate_limit_rpm=1000,
        timeout_seconds=30.0,
        description="Anthropic Claude 3 Sonnet模型，平衡性能与成本",
        version="2024-02-29"
    )
    
    # 本地模型配置
    configs["llama-2-7b"] = ModelConfig(
        provider="local",
        model_name="llama-2-7b-chat",
        config={
            "model_path": "/models/llama-2-7b",
            "device": "cuda",
            "quantization": "int8"
        },
        capabilities=["text_generation"],
        cost_per_token=0.0,
        max_batch_size=2,
        rate_limit_rpm=100,
        timeout_seconds=120.0,
        description="本地部署的Llama 2 7B模型",
        version="2.0.0"
    )
    
    return configs


async def demo_basic_factory_operations():
    """演示基础工厂操作"""
    print("\n" + "="*60)
    print("演示: 基础工厂操作")
    print("="*60)
    
    # 创建模型配置
    configs = create_sample_configs()
    
    # 创建模型工厂
    factory = ChatModelFactory(configs)
    
    print("📋 可用模型:")
    models = factory.list_models()
    for model in models:
        print(f"  • {model['name']} ({model['provider']}) - {model['description']}")
    
    # 创建模型实例
    print("\n🔄 创建模型实例:")
    
    try:
        # 创建GPT-4模型
        gpt4_model = await factory.create("gpt-4-turbo")
        print(f"  ✅ 创建模型: {gpt4_model.name} ({gpt4_model.provider})")
        
        # 测试模型生成
        response = await gpt4_model.generate("你好，请介绍一下你自己")
        print(f"  💬 模型响应: {response}")
        
        # 创建Claude模型
        claude_model = await factory.create("claude-3-sonnet")
        print(f"  ✅ 创建模型: {claude_model.name} ({claude_model.provider})")
        
        # 测试流式生成
        print("  🌊 测试流式生成:")
        async for chunk in claude_model.generate_stream("请生成一个简短的故事"):
            print(f"    {chunk}", end="", flush=True)
        print()
        
        # 测试缓存
        print("\n💾 测试缓存机制:")
        start_time = time.time()
        cached_model = await factory.create("gpt-4-turbo", use_cache=True)
        cache_time = time.time() - start_time
        print(f"  ⚡ 缓存命中，创建时间: {cache_time:.3f}s")
        
        # 获取缓存统计
        stats = factory.get_cache_stats()
        print(f"  📊 缓存统计: 命中率 {stats['hit_rate']:.2%}, 缓存大小 {stats['cache_size']}")
        
        # 测试模糊匹配
        print("\n🔍 测试模糊匹配:")
        try:
            # 故意使用错误的模型名称
            await factory.create("gpt4-turbo")
        except ValueError as e:
            print(f"  🎯 模糊匹配错误: {e}")
        
        # 测试模型信息
        print("\n📄 测试模型信息:")
        info = factory.get_model_info("gpt-3.5-turbo")
        print(f"  📋 模型信息: {info['name']} - {info['description']}")
        print(f"    能力: {', '.join(info['capabilities'][:3])}")
        print(f"    成本: ${info['cost_per_token']}/token")
        
    except Exception as e:
        print(f"  ❌ 错误: {e}")


async def demo_advanced_features():
    """演示高级功能"""
    print("\n" + "="*60)
    print("演示: 高级功能")
    print("="*60)
    
    # 创建模型配置
    configs = create_sample_configs()
    
    # 创建模型工厂
    factory = ChatModelFactory(configs)
    
    # 动态注册新提供商
    print("🔧 动态注册新提供商:")
    
    # 定义一个新的提供商类
    class MockProvider(BaseChatModel):
        def __init__(self, config: ModelConfig):
            super().__init__(config)
        
        @property
        def name(self) -> str:
            return self.config.model_name
        
        @property
        def provider(self) -> str:
            return "mock"
        
        @property
        def capabilities(self) -> ModelCapabilities:
            return ModelCapabilities()
        
        async def generate(self, prompt: str, **kwargs) -> str:
            return f"Mock响应: {prompt}"
        
        async def generate_stream(self, prompt: str, **kwargs):
            yield "Mock "
            yield "流式 "
            yield "响应"
        
        async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
            return {"role": "assistant", "content": "Mock聊天响应"}
    
    # 注册新提供商
    factory.register_provider("mock", MockProvider)
    
    # 添加新的模型配置
    mock_config = ModelConfig(
        provider="mock",
        model_name="mock-model-v1",
        config={"mock": True},
        description="模拟模型，用于测试"
    )
    
    # 注意：需要更新工厂的配置字典
    # 实际项目中会有更好的方式动态添加配置
    factory.configs["mock-model"] = mock_config
    
    print("  ✅ 注册Mock提供商和模型配置")
    
    # 创建模拟模型
    try:
        mock_model = await factory.create("mock-model")
        print(f"  ✅ 创建模拟模型: {mock_model.name}")
        
        response = await mock_model.generate("测试消息")
        print(f"  💬 模拟响应: {response}")
    except Exception as e:
        print(f"  ❌ 创建模拟模型失败: {e}")
    
    # 演示批量创建
    print("\n🚀 演示批量创建:")
    
    models_to_create = ["gpt-3.5-turbo", "claude-3-sonnet", "llama-2-7b"]
    
    start_time = time.time()
    tasks = [factory.create(model_name) for model_name in models_to_create]
    created_models = await asyncio.gather(*tasks, return_exceptions=True)
    
    batch_time = time.time() - start_time
    
    for i, (model_name, result) in enumerate(zip(models_to_create, created_models)):
        if isinstance(result, Exception):
            print(f"  ❌ 创建失败 {model_name}: {result}")
        else:
            print(f"  ✅ 创建成功 {model_name}: {result.name}")
    
    print(f"  ⏱️  批量创建耗时: {batch_time:.3f}s")
    
    # 清空缓存
    print("\n🗑️  清空缓存:")
    cache_size_before = factory.get_cache_stats()["cache_size"]
    factory.clear_cache()
    cache_size_after = factory.get_cache_stats()["cache_size"]
    print(f"  缓存大小: {cache_size_before} -> {cache_size_after}")


def demo_config_parsing():
    """演示配置解析"""
    print("\n" + "="*60)
    print("演示: 配置解析")
    print("="*60)
    
    # 从字典创建配置
    config_dict = {
        "provider": "openai",
        "model_name": "gpt-4",
        "config": {
            "api_key": "sk-...",
            "temperature": 0.7
        },
        "capabilities": ["function_calling", "streaming"],
        "cost_per_token": 0.00001,
        "description": "测试配置"
    }
    
    config = ModelConfig.from_dict(config_dict)
    
    print("📄 从字典创建配置:")
    print(f"  提供商: {config.provider}")
    print(f"  模型名称: {config.model_name}")
    print(f"  能力: {', '.join(config.capabilities)}")
    print(f"  成本: ${config.cost_per_token}/token")
    
    # 测试能力检查
    print("\n🔍 测试能力检查:")
    test_capabilities = ["function_calling", "vision", "unknown"]
    for capability in test_capabilities:
        has_cap = config.has_capability(capability)
        print(f"  {capability}: {'✅' if has_cap else '❌'}")
    
    # 测试成本估算
    print("\n💰 测试成本估算:")
    input_tokens = 1000
    output_tokens = 500
    cost = config.get_cost_estimate(input_tokens, output_tokens)
    print(f"  输入: {input_tokens} tokens, 输出: {output_tokens} tokens")
    print(f"  估算成本: ${cost:.6f}")
    
    # 测试缓存键生成
    print("\n🔑 测试缓存键生成:")
    cache_key = config.cache_key
    print(f"  缓存键: {cache_key}")
    
    # 转换为字典
    print("\n📋 配置转字典:")
    config_dict_back = config.to_dict()
    print(f"  配置字典键: {list(config_dict_back.keys())}")


async def demo_performance_testing():
    """演示性能测试"""
    print("\n" + "="*60)
    print("演示: 性能测试")
    print("="*60)
    
    # 创建模型配置
    configs = create_sample_configs()
    
    # 创建模型工厂（禁用缓存以测试创建性能）
    factory = ChatModelFactory(configs)
    
    # 测试重复创建性能
    test_model = "gpt-3.5-turbo"
    iterations = 5
    
    print(f"🔄 测试重复创建性能 ({iterations} 次迭代):")
    
    times = []
    for i in range(iterations):
        start_time = time.time()
        model = await factory.create(test_model, use_cache=False)
        end_time = time.time()
        
        creation_time = end_time - start_time
        times.append(creation_time)
        
        print(f"  迭代 {i+1}: {creation_time:.3f}s")
    
    avg_time = sum(times) / len(times)
    print(f"  📊 平均创建时间: {avg_time:.3f}s")
    
    # 测试缓存性能
    print(f"\n💾 测试缓存性能 ({iterations} 次迭代):")
    
    # 先创建一次并缓存
    await factory.create(test_model, use_cache=True)
    
    cache_times = []
    for i in range(iterations):
        start_time = time.time()
        model = await factory.create(test_model, use_cache=True)
        end_time = time.time()
        
        cache_time = end_time - start_time
        cache_times.append(cache_time)
        
        print(f"  迭代 {i+1}: {cache_time:.3f}s")
    
    avg_cache_time = sum(cache_times) / len(cache_times)
    print(f"  📊 平均缓存访问时间: {avg_cache_time:.3f}s")
    print(f"  🚀 性能提升: {avg_time/avg_cache_time:.1f}x")
    
    # 获取性能统计
    stats = factory.get_cache_stats()
    print(f"\n📈 性能统计:")
    print(f"  缓存命中率: {stats['hit_rate']:.2%}")
    print(f"  缓存大小: {stats['cache_size']}")
    
    if test_model in stats["average_creation_time"]:
        print(f"  {test_model} 平均创建时间: {stats['average_creation_time'][test_model]:.3f}s")


# ============================================================================
# 测试函数
# ============================================================================

def run_tests():
    """运行单元测试"""
    print("\n" + "="*60)
    print("测试: 模型工厂功能")
    print("="*60)
    
    # 测试配置类
    print("🧪 测试ModelConfig类:")
    
    # 测试创建和属性
    config = ModelConfig(
        provider="test",
        model_name="test-model",
        config={"key": "value"},
        capabilities=["cap1", "cap2"],
        cost_per_token=0.001
    )
    
    assert config.provider == "test"
    assert config.model_name == "test-model"
    assert config.config["key"] == "value"
    assert "cap1" in config.capabilities
    assert config.cost_per_token == 0.001
    print("  ✅ 基础属性测试通过")
    
    # 测试能力检查
    assert config.has_capability("cap1") == True
    assert config.has_capability("cap3") == False
    print("  ✅ 能力检查测试通过")
    
    # 测试成本估算
    cost = config.get_cost_estimate(100, 50)
    expected_cost = 150 * 0.001
    assert abs(cost - expected_cost) < 0.000001
    print("  ✅ 成本估算测试通过")
    
    # 测试从字典创建
    config_dict = {
        "provider": "dict-test",
        "model_name": "dict-model",
        "config": {"test": True},
        "capabilities": ["test"]
    }
    
    config_from_dict = ModelConfig.from_dict(config_dict)
    assert config_from_dict.provider == "dict-test"
    assert config_from_dict.model_name == "dict-model"
    print("  ✅ 从字典创建测试通过")
    
    # 测试工厂类
    print("\n🧪 测试ChatModelFactory类:")
    
    configs = {
        "test-model-1": ModelConfig(
            provider="openai",
            model_name="gpt-test",
            config={"test": True}
        ),
        "test-model-2": ModelConfig(
            provider="anthropic",
            model_name="claude-test",
            config={"test": True}
        )
    }
    
    factory = ChatModelFactory(configs)
    
    # 测试模型列表
    models = factory.list_models()
    assert len(models) == 2
    print("  ✅ 模型列表测试通过")
    
    # 测试模型信息
    info = factory.get_model_info("test-model-1")
    assert info["name"] == "test-model-1"
    assert info["provider"] == "openai"
    print("  ✅ 模型信息测试通过")
    
    # 测试模糊匹配
    similar = factory._find_similar_model("test-model", threshold=0.5)
    assert similar is not None
    print("  ✅ 模糊匹配测试通过")
    
    print("\n🎉 所有测试通过!")


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    print("🚀 DeerFlow Chat Model Factory 演示")
    print("="*60)
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        # 运行测试
        run_tests()
        
        # 演示基础操作
        await demo_basic_factory_operations()
        
        # 演示配置解析
        demo_config_parsing()
        
        # 演示高级功能
        await demo_advanced_features()
        
        # 演示性能测试
        await demo_performance_testing()
        
        print("\n" + "="*60)
        print("✅ 演示完成!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    asyncio.run(main())