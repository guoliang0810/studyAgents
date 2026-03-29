#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型配置体系演示代码 - DeerFlow Python Agent 架构师训练营
第58节课：模型配置体系

本模块演示现代AI Agent系统中的模型配置体系，包括：
1. 模型配置结构：提供者、模型名称、参数、能力标签、成本配置
2. 模型工厂模式：基于提供者抽象的模型实例创建机制
3. 多模型支持：OpenAI、Anthropic、本地模型等不同提供者的统一接口
4. 模型能力标签系统：根据任务需求自动选择合适模型
5. 成本计算和管理：模型使用成本实时计算和预算控制
6. 错误处理和降级策略：模型不可用时的优雅降级机制

使用说明：
1. 直接运行：python model_config_system_demo.py
2. 运行测试：python model_config_system_demo.py --test
3. 查看帮助：python model_config_system_demo.py --help
"""

import os
import sys
import json
import yaml
import argparse
import copy
import re
import time
import hashlib
import base64
import uuid
from typing import Any, Dict, List, Optional, Union, Callable, Set, Tuple, Type
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
import logging
from abc import ABC, abstractmethod
import random
from datetime import datetime, timedelta

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ModelConfigError(Exception):
    """模型配置错误基类"""
    pass


class ModelProviderError(ModelConfigError):
    """模型提供者错误"""
    pass


class ModelCreationError(ModelConfigError):
    """模型创建错误"""
    pass


class ModelCapabilityError(ModelConfigError):
    """模型能力错误"""
    pass


class ModelCostError(ModelConfigError):
    """模型成本错误"""
    pass


# ============================================================================
# 模型能力标签系统
# ============================================================================

class ModelCapability(Enum):
    """模型能力标签枚举
    
    用于标记模型支持的能力，支持根据任务需求选择合适模型
    """
    TEXT_GENERATION = auto()          # 文本生成
    CODE_GENERATION = auto()          # 代码生成
    TEXT_EMBEDDING = auto()          # 文本向量化
    IMAGE_GENERATION = auto()         # 图像生成
    IMAGE_UNDERSTANDING = auto()      # 图像理解
    AUDIO_GENERATION = auto()         # 音频生成
    AUDIO_TRANSCRIPTION = auto()      # 语音转文字
    REASONING = auto()                # 逻辑推理
    MATH = auto()                     # 数学计算
    TRANSLATION = auto()             # 翻译
    SUMMARIZATION = auto()           # 摘要
    SENTIMENT_ANALYSIS = auto()      # 情感分析
    NAMED_ENTITY_RECOGNITION = auto() # 命名实体识别
    QUESTION_ANSWERING = auto()      # 问答
    CHAT = auto()                    # 对话
    FUNCTION_CALLING = auto()        # 函数调用
    LONG_CONTEXT = auto()            # 长上下文支持
    LOW_LATENCY = auto()             # 低延迟
    LOW_COST = auto()                # 低成本
    HIGH_ACCURACY = auto()           # 高精度
    
    @classmethod
    def from_string(cls, capability_str: str) -> "ModelCapability":
        """从字符串转换为能力枚举"""
        try:
            return cls[capability_str.upper()]
        except KeyError:
            raise ModelCapabilityError(f"未知的能力标签: {capability_str}")


class ModelCostConfig:
    """模型成本配置
    
    配置模型使用成本，支持按token、按请求、按时间的计费方式
    """
    
    def __init__(
        self,
        input_cost_per_token: float = 0.0,
        output_cost_per_token: float = 0.0,
        request_cost: float = 0.0,
        monthly_fee: float = 0.0,
        currency: str = "USD"
    ):
        self.input_cost_per_token = input_cost_per_token
        self.output_cost_per_token = output_cost_per_token
        self.request_cost = request_cost
        self.monthly_fee = monthly_fee
        self.currency = currency
    
    def calculate_cost(self, input_tokens: int = 0, output_tokens: int = 0, requests: int = 0) -> float:
        """计算总成本
        
        Args:
            input_tokens: 输入token数
            output_tokens: 输出token数
            requests: 请求次数
            
        Returns:
            总成本（货币单位）
        """
        token_cost = (input_tokens * self.input_cost_per_token + 
                     output_tokens * self.output_cost_per_token)
        request_cost = requests * self.request_cost
        return token_cost + request_cost
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "input_cost_per_token": self.input_cost_per_token,
            "output_cost_per_token": self.output_cost_per_token,
            "request_cost": self.request_cost,
            "monthly_fee": self.monthly_fee,
            "currency": self.currency
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelCostConfig":
        """从字典创建"""
        return cls(
            input_cost_per_token=data.get("input_cost_per_token", 0.0),
            output_cost_per_token=data.get("output_cost_per_token", 0.0),
            request_cost=data.get("request_cost", 0.0),
            monthly_fee=data.get("monthly_fee", 0.0),
            currency=data.get("currency", "USD")
        )
    
    def __repr__(self) -> str:
        return f"ModelCostConfig(input={self.input_cost_per_token}, output={self.output_cost_per_token}, request={self.request_cost}, monthly={self.monthly_fee}, currency={self.currency})"


@dataclass
class ModelConfig:
    """模型配置
    
    定义单个模型的完整配置信息，包括提供者、模型名称、参数、能力和成本
    """
    provider: str                     # 提供者名称，如 "openai", "anthropic", "local"
    model_name: str                  # 模型名称，如 "gpt-4", "claude-3-opus", "llama-3-70b"
    api_key: Optional[str] = None    # API密钥（可选，支持环境变量引用）
    base_url: Optional[str] = None   # 基础URL（可选，用于自定义端点）
    timeout: float = 30.0            # 请求超时时间（秒）
    max_retries: int = 3             # 最大重试次数
    temperature: float = 0.7         # 温度参数
    max_tokens: Optional[int] = None # 最大输出token数
    capabilities: Set[ModelCapability] = field(default_factory=set)  # 模型能力标签
    cost_config: ModelCostConfig = field(default_factory=ModelCostConfig)  # 成本配置
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于YAML序列化）"""
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "capabilities": [cap.name for cap in self.capabilities],
            "cost_config": self.cost_config.to_dict(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        """从字典创建"""
        capabilities = set()
        for cap_str in data.get("capabilities", []):
            capabilities.add(ModelCapability.from_string(cap_str))
        
        cost_config_data = data.get("cost_config", {})
        cost_config = ModelCostConfig.from_dict(cost_config_data)
        
        return cls(
            provider=data["provider"],
            model_name=data["model_name"],
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            timeout=data.get("timeout", 30.0),
            max_retries=data.get("max_retries", 3),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens"),
            capabilities=capabilities,
            cost_config=cost_config,
            metadata=data.get("metadata", {})
        )
    
    def has_capability(self, capability: ModelCapability) -> bool:
        """检查是否支持特定能力"""
        return capability in self.capabilities
    
    def matches_capabilities(self, required_capabilities: Set[ModelCapability]) -> bool:
        """检查是否满足所有必需能力"""
        return required_capabilities.issubset(self.capabilities)
    
    def get_cost_estimate(self, input_tokens: int = 1000, output_tokens: int = 500) -> float:
        """获取成本估算"""
        return self.cost_config.calculate_cost(input_tokens, output_tokens)


@dataclass
class ModelRegistry:
    """模型注册表
    
    管理所有可用模型配置，支持按提供者、能力、成本等条件查找模型
    """
    models: Dict[str, ModelConfig] = field(default_factory=dict)  # 模型ID -> 模型配置
    
    def register(self, model_id: str, config: ModelConfig) -> None:
        """注册模型配置"""
        if model_id in self.models:
            raise ModelConfigError(f"模型ID已存在: {model_id}")
        self.models[model_id] = config
    
    def get(self, model_id: str) -> ModelConfig:
        """获取模型配置"""
        if model_id not in self.models:
            raise ModelConfigError(f"模型ID不存在: {model_id}")
        return self.models[model_id]
    
    def find_by_capabilities(self, required_capabilities: Set[ModelCapability]) -> List[Tuple[str, ModelConfig]]:
        """根据能力要求查找模型"""
        results = []
        for model_id, config in self.models.items():
            if config.matches_capabilities(required_capabilities):
                results.append((model_id, config))
        return results
    
    def find_by_provider(self, provider: str) -> List[Tuple[str, ModelConfig]]:
        """根据提供者查找模型"""
        results = []
        for model_id, config in self.models.items():
            if config.provider == provider:
                results.append((model_id, config))
        return results
    
    def find_lowest_cost(self, required_capabilities: Set[ModelCapability], 
                        input_tokens: int = 1000, output_tokens: int = 500) -> Optional[Tuple[str, ModelConfig]]:
        """根据能力和成本查找最低成本模型"""
        candidates = self.find_by_capabilities(required_capabilities)
        if not candidates:
            return None
        
        # 计算每个候选模型的成本并排序
        candidates_with_cost = []
        for model_id, config in candidates:
            cost = config.get_cost_estimate(input_tokens, output_tokens)
            candidates_with_cost.append((cost, model_id, config))
        
        # 按成本升序排序
        candidates_with_cost.sort(key=lambda x: x[0])
        
        if candidates_with_cost:
            _, model_id, config = candidates_with_cost[0]
            return (model_id, config)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "models": {model_id: config.to_dict() for model_id, config in self.models.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelRegistry":
        """从字典创建"""
        registry = cls()
        for model_id, model_data in data.get("models", {}).items():
            config = ModelConfig.from_dict(model_data)
            registry.register(model_id, config)
        return registry
    
    def save_to_yaml(self, filepath: str) -> None:
        """保存为YAML文件"""
        data = self.to_dict()
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    @classmethod
    def load_from_yaml(cls, filepath: str) -> "ModelRegistry":
        """从YAML文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


# ============================================================================
# 模型工厂和提供者抽象
# ============================================================================

class BaseModel(ABC):
    """模型基类
    
    定义所有模型的统一接口，支持文本生成、聊天、嵌入等操作
    """
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0
        self.total_cost = 0.0
    
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天对话"""
        pass
    
    @abstractmethod
    def create_embedding(self, text: str) -> List[float]:
        """创建文本嵌入向量"""
        pass
    
    def record_usage(self, input_tokens: int, output_tokens: int, requests: int = 1) -> float:
        """记录使用量并计算成本"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_requests += requests
        
        cost = self.config.cost_config.calculate_cost(
            input_tokens, output_tokens, requests
        )
        self.total_cost += cost
        return cost
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_requests": self.total_requests,
            "total_cost": self.total_cost,
            "config": self.config.to_dict()
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.config.provider}, model={self.config.model_name})"


class ModelProvider(ABC):
    """模型提供者基类
    
    定义提供者接口，每个提供者负责创建特定类型的模型实例
    """
    
    @abstractmethod
    def create_model(self, config: ModelConfig) -> BaseModel:
        """创建模型实例"""
        pass
    
    @abstractmethod
    def validate_config(self, config: ModelConfig) -> bool:
        """验证配置是否有效"""
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        pass


class OpenAIModel(BaseModel):
    """OpenAI模型实现
    
    OpenAI API的模型实现，支持GPT系列模型
    """
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        # 模拟OpenAI客户端初始化
        self.client_initialized = True
        logger.info(f"初始化OpenAI模型: {config.model_name}")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本（模拟实现）"""
        # 在实际实现中，这里会调用OpenAI API
        input_tokens = len(prompt) // 4  # 简单估算
        output_tokens = 100  # 模拟输出token数
        
        # 记录使用量
        self.record_usage(input_tokens, output_tokens)
        
        # 模拟生成文本
        return f"OpenAI模型 '{self.config.model_name}' 生成的文本（模拟）: {prompt[:50]}..."
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天对话（模拟实现）"""
        # 计算输入token数
        total_text = " ".join([msg.get("content", "") for msg in messages])
        input_tokens = len(total_text) // 4
        output_tokens = 150
        
        # 记录使用量
        self.record_usage(input_tokens, output_tokens)
        
        # 模拟回复
        return f"OpenAI模型 '{self.config.model_name}' 的回复（模拟）: 我已收到您的消息。"
    
    def create_embedding(self, text: str) -> List[float]:
        """创建文本嵌入向量（模拟实现）"""
        input_tokens = len(text) // 4
        self.record_usage(input_tokens, 0)
        
        # 模拟生成嵌入向量（1536维，类似text-embedding-ada-002）
        dimension = 1536
        return [random.uniform(-1, 1) for _ in range(dimension)]


class OpenAIProvider(ModelProvider):
    """OpenAI提供者
    
    创建和管理OpenAI模型实例
    """
    
    def create_model(self, config: ModelConfig) -> BaseModel:
        """创建OpenAI模型实例"""
        if not self.validate_config(config):
            raise ModelCreationError(f"OpenAI配置无效: {config}")
        
        return OpenAIModel(config)
    
    def validate_config(self, config: ModelConfig) -> bool:
        """验证OpenAI配置"""
        if config.provider != "openai":
            return False
        
        # 检查必需的API密钥
        if not config.api_key and "OPENAI_API_KEY" not in os.environ:
            logger.warning("OpenAI API密钥未设置")
            # 在实际实现中，这里会抛出错误
            # 为了演示目的，我们允许继续
        
        # 检查支持的模型
        supported_models = self.get_supported_models()
        if config.model_name not in supported_models:
            logger.warning(f"OpenAI可能不支持模型: {config.model_name}")
        
        return True
    
    def get_supported_models(self) -> List[str]:
        """获取支持的OpenAI模型列表"""
        return [
            "gpt-4", "gpt-4-turbo", "gpt-4o", 
            "gpt-3.5-turbo", "gpt-3.5-turbo-instruct",
            "text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"
        ]


class AnthropicModel(BaseModel):
    """Anthropic模型实现
    
    Claude系列模型的实现
    """
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client_initialized = True
        logger.info(f"初始化Anthropic模型: {config.model_name}")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本（模拟实现）"""
        input_tokens = len(prompt) // 4
        output_tokens = 120
        
        self.record_usage(input_tokens, output_tokens)
        
        return f"Anthropic模型 '{self.config.model_name}' 生成的文本（模拟）: {prompt[:50]}..."
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天对话（模拟实现）"""
        total_text = " ".join([msg.get("content", "") for msg in messages])
        input_tokens = len(total_text) // 4
        output_tokens = 180
        
        self.record_usage(input_tokens, output_tokens)
        
        return f"Anthropic模型 '{self.config.model_name}' 的回复（模拟）: 我已理解您的请求。"
    
    def create_embedding(self, text: str) -> List[float]:
        """Anthropic模型不支持嵌入，返回空列表"""
        logger.warning(f"Anthropic模型 {self.config.model_name} 不支持嵌入功能")
        return []


class AnthropicProvider(ModelProvider):
    """Anthropic提供者"""
    
    def create_model(self, config: ModelConfig) -> BaseModel:
        if not self.validate_config(config):
            raise ModelCreationError(f"Anthropic配置无效: {config}")
        
        return AnthropicModel(config)
    
    def validate_config(self, config: ModelConfig) -> bool:
        if config.provider != "anthropic":
            return False
        
        if not config.api_key and "ANTHROPIC_API_KEY" not in os.environ:
            logger.warning("Anthropic API密钥未设置")
        
        supported_models = self.get_supported_models()
        if config.model_name not in supported_models:
            logger.warning(f"Anthropic可能不支持模型: {config.model_name}")
        
        return True
    
    def get_supported_models(self) -> List[str]:
        return [
            "claude-3-opus", "claude-3-sonnet", "claude-3-haiku",
            "claude-2.1", "claude-2.0", "claude-instant-1.2"
        ]


class LocalModel(BaseModel):
    """本地模型实现
    
    本地部署的模型，如Llama、Mistral等
    """
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.model_loaded = True
        logger.info(f"初始化本地模型: {config.model_name}")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本（模拟实现）"""
        input_tokens = len(prompt) // 4
        output_tokens = 80
        
        self.record_usage(input_tokens, output_tokens)
        
        return f"本地模型 '{self.config.model_name}' 生成的文本（模拟）: {prompt[:50]}..."
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天对话（模拟实现）"""
        total_text = " ".join([msg.get("content", "") for msg in messages])
        input_tokens = len(total_text) // 4
        output_tokens = 100
        
        self.record_usage(input_tokens, output_tokens)
        
        return f"本地模型 '{self.config.model_name}' 的回复（模拟）: 这是本地模型的响应。"
    
    def create_embedding(self, text: str) -> List[float]:
        """创建文本嵌入向量（模拟实现）"""
        input_tokens = len(text) // 4
        self.record_usage(input_tokens, 0)
        
        # 本地模型通常有较小的嵌入维度
        dimension = 768
        return [random.uniform(-1, 1) for _ in range(dimension)]


class LocalProvider(ModelProvider):
    """本地模型提供者"""
    
    def create_model(self, config: ModelConfig) -> BaseModel:
        if not self.validate_config(config):
            raise ModelCreationError(f"本地模型配置无效: {config}")
        
        return LocalModel(config)
    
    def validate_config(self, config: ModelConfig) -> bool:
        if config.provider != "local":
            return False
        
        # 本地模型需要base_url或本地路径
        if not config.base_url and "LOCAL_MODEL_PATH" not in os.environ:
            logger.warning("本地模型路径未设置")
        
        return True
    
    def get_supported_models(self) -> List[str]:
        return [
            "llama-3-70b", "llama-3-8b", "llama-2-70b",
            "mistral-7b", "mistral-8x7b",
            "codellama-34b", "codellama-13b",
            "vicuna-33b", "vicuna-13b"
        ]


# ============================================================================
# 模型工厂
# ============================================================================

class ModelFactory:
    """模型工厂
    
    基于提供者模式创建模型实例，支持动态注册新的提供者
    """
    
    def __init__(self):
        self.providers: Dict[str, ModelProvider] = {}
        self.default_provider = "openai"
        self._register_default_providers()
    
    def _register_default_providers(self) -> None:
        """注册默认提供者"""
        self.register_provider("openai", OpenAIProvider())
        self.register_provider("anthropic", AnthropicProvider())
        self.register_provider("local", LocalProvider())
    
    def register_provider(self, provider_name: str, provider: ModelProvider) -> None:
        """注册新的模型提供者"""
        if provider_name in self.providers:
            logger.warning(f"提供者 '{provider_name}' 已存在，将被覆盖")
        self.providers[provider_name] = provider
    
    def create_model(self, config: ModelConfig) -> BaseModel:
        """创建模型实例
        
        Args:
            config: 模型配置
            
        Returns:
            模型实例
            
        Raises:
            ModelCreationError: 模型创建失败
        """
        provider_name = config.provider
        
        if provider_name not in self.providers:
            raise ModelCreationError(f"未知的提供者: {provider_name}")
        
        provider = self.providers[provider_name]
        
        try:
            model = provider.create_model(config)
            logger.info(f"成功创建模型: {provider_name}/{config.model_name}")
            return model
        except Exception as e:
            raise ModelCreationError(f"创建模型失败: {provider_name}/{config.model_name}: {str(e)}")
    
    def create_model_from_id(self, registry: ModelRegistry, model_id: str) -> BaseModel:
        """从注册表中的模型ID创建模型实例"""
        config = registry.get(model_id)
        return self.create_model(config)
    
    def create_model_by_capabilities(self, 
                                   registry: ModelRegistry,
                                   required_capabilities: Set[ModelCapability],
                                   provider_preference: Optional[str] = None) -> Optional[BaseModel]:
        """根据能力要求创建模型实例
        
        从注册表中选择满足能力要求的模型，优先使用偏好提供者
        """
        # 首先尝试偏好提供者
        if provider_preference:
            provider_models = registry.find_by_provider(provider_preference)
            capability_models = [(model_id, config) for model_id, config in provider_models 
                               if config.matches_capabilities(required_capabilities)]
            if capability_models:
                model_id, config = capability_models[0]
                return self.create_model(config)
        
        # 查找最低成本模型
        result = registry.find_lowest_cost(required_capabilities)
        if result:
            model_id, config = result
            return self.create_model(config)
        
        # 查找任何满足能力的模型
        all_capability_models = registry.find_by_capabilities(required_capabilities)
        if all_capability_models:
            model_id, config = all_capability_models[0]
            return self.create_model(config)
        
        logger.warning(f"未找到满足能力要求的模型: {required_capabilities}")
        return None
    
    def get_available_providers(self) -> List[str]:
        """获取可用的提供者列表"""
        return list(self.providers.keys())
    
    def validate_config(self, config: ModelConfig) -> bool:
        """验证配置是否有效"""
        if config.provider not in self.providers:
            return False
        
        provider = self.providers[config.provider]
        return provider.validate_config(config)
    
    def get_supported_models(self, provider_name: Optional[str] = None) -> Dict[str, List[str]]:
        """获取支持的模型列表
        
        Args:
            provider_name: 可选的提供者名称，如果为None则返回所有提供者的模型
            
        Returns:
            提供者名称 -> 模型列表的映射
        """
        if provider_name:
            if provider_name not in self.providers:
                return {}
            provider = self.providers[provider_name]
            return {provider_name: provider.get_supported_models()}
        
        result = {}
        for name, provider in self.providers.items():
            result[name] = provider.get_supported_models()
        return result


# ============================================================================
# 示例配置和演示
# ============================================================================

def create_sample_registry() -> ModelRegistry:
    """创建示例模型注册表"""
    registry = ModelRegistry()
    
    # OpenAI模型配置
    openai_gpt4_config = ModelConfig(
        provider="openai",
        model_name="gpt-4",
        api_key="${OPENAI_API_KEY}",
        timeout=60.0,
        max_retries=3,
        temperature=0.7,
        max_tokens=4096,
        capabilities={
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.CHAT,
            ModelCapability.REASONING,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.LONG_CONTEXT
        },
        cost_config=ModelCostConfig(
            input_cost_per_token=0.03 / 1000,  # $0.03 per 1K tokens
            output_cost_per_token=0.06 / 1000,  # $0.06 per 1K tokens
            currency="USD"
        )
    )
    
    openai_gpt35_config = ModelConfig(
        provider="openai",
        model_name="gpt-3.5-turbo",
        api_key="${OPENAI_API_KEY}",
        timeout=30.0,
        max_retries=3,
        temperature=0.7,
        max_tokens=2048,
        capabilities={
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CHAT,
            ModelCapability.CODE_GENERATION,
            ModelCapability.LOW_COST
        },
        cost_config=ModelCostConfig(
            input_cost_per_token=0.0015 / 1000,
            output_cost_per_token=0.002 / 1000,
            currency="USD"
        )
    )
    
    # Anthropic模型配置
    anthropic_claude_config = ModelConfig(
        provider="anthropic",
        model_name="claude-3-opus",
        api_key="${ANTHROPIC_API_KEY}",
        timeout=90.0,
        max_retries=2,
        temperature=0.8,
        max_tokens=4096,
        capabilities={
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CHAT,
            ModelCapability.REASONING,
            ModelCapability.MATH,
            ModelCapability.LONG_CONTEXT,
            ModelCapability.HIGH_ACCURACY
        },
        cost_config=ModelCostConfig(
            input_cost_per_token=0.015 / 1000,
            output_cost_per_token=0.075 / 1000,
            currency="USD"
        )
    )
    
    # 本地模型配置
    local_llama_config = ModelConfig(
        provider="local",
        model_name="llama-3-70b",
        base_url="http://localhost:8000/v1",
        timeout=120.0,
        max_retries=1,
        temperature=0.8,
        max_tokens=2048,
        capabilities={
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.CHAT,
            ModelCapability.LOW_COST
        },
        cost_config=ModelCostConfig(
            monthly_fee=0.0,  # 本地部署，无API成本
            currency="USD"
        )
    )
    
    # 注册模型
    registry.register("openai-gpt-4", openai_gpt4_config)
    registry.register("openai-gpt-3.5-turbo", openai_gpt35_config)
    registry.register("anthropic-claude-3-opus", anthropic_claude_config)
    registry.register("local-llama-3-70b", local_llama_config)
    
    return registry


def demo_basic_usage() -> None:
    """演示基本用法"""
    print("=" * 60)
    print("模型配置体系演示 - 基本用法")
    print("=" * 60)
    
    # 1. 创建模型注册表
    registry = create_sample_registry()
    print("✓ 创建模型注册表，包含4个模型配置")
    
    # 2. 创建模型工厂
    factory = ModelFactory()
    print(f"✓ 创建模型工厂，支持提供者: {factory.get_available_providers()}")
    
    # 3. 根据ID创建模型
    try:
        model = factory.create_model_from_id(registry, "openai-gpt-4")
        print(f"✓ 创建模型: {model}")
        
        # 4. 使用模型
        response = model.generate_text("请解释人工智能的基本原理")
        print(f"✓ 模型生成文本: {response[:80]}...")
        
        # 5. 查看使用统计
        stats = model.get_usage_stats()
        print(f"✓ 使用统计: {stats['total_input_tokens']} 输入tokens, {stats['total_output_tokens']} 输出tokens, 成本: ${stats['total_cost']:.6f}")
    
    except ModelCreationError as e:
        print(f"✗ 模型创建失败: {e}")
    
    print()
    
    # 6. 根据能力查找模型
    print("根据能力查找模型演示:")
    required_capabilities = {ModelCapability.CODE_GENERATION, ModelCapability.LOW_COST}
    model = factory.create_model_by_capabilities(registry, required_capabilities)
    if model:
        print(f"✓ 找到满足能力的模型: {model}")
        response = model.generate_text("写一个Python快速排序函数")
        print(f"✓ 代码生成: {response[:80]}...")
    else:
        print("✗ 未找到满足能力的模型")
    
    print()
    
    # 7. 保存和加载注册表
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        registry.save_to_yaml(f.name)
        print(f"✓ 保存注册表到YAML文件: {f.name}")
        
        # 重新加载
        loaded_registry = ModelRegistry.load_from_yaml(f.name)
        print(f"✓ 从YAML文件加载注册表，包含 {len(loaded_registry.models)} 个模型")
    
    print()


def demo_advanced_features() -> None:
    """演示高级功能"""
    print("=" * 60)
    print("模型配置体系演示 - 高级功能")
    print("=" * 60)
    
    # 1. 创建自定义模型配置
    custom_config = ModelConfig(
        provider="openai",
        model_name="gpt-4-turbo",
        capabilities={
            ModelCapability.TEXT_GENERATION,
            ModelCapability.IMAGE_UNDERSTANDING,
            ModelCapability.LONG_CONTEXT
        },
        cost_config=ModelCostConfig(
            input_cost_per_token=0.01 / 1000,
            output_cost_per_token=0.03 / 1000
        )
    )
    
    print("✓ 创建自定义模型配置:")
    print(f"  提供者: {custom_config.provider}")
    print(f"  模型: {custom_config.model_name}")
    print(f"  能力: {[c.name for c in custom_config.capabilities]}")
    print(f"  成本配置: {custom_config.cost_config}")
    
    # 2. 验证配置
    factory = ModelFactory()
    is_valid = factory.validate_config(custom_config)
    print(f"✓ 配置验证: {'通过' if is_valid else '失败'}")
    
    # 3. 成本计算演示
    print("\n成本计算演示:")
    cost = custom_config.get_cost_estimate(input_tokens=1500, output_tokens=800)
    print(f"  1500输入tokens + 800输出tokens ≈ ${cost:.6f}")
    
    # 4. 模型能力匹配
    print("\n模型能力匹配演示:")
    task_requirements = {ModelCapability.TEXT_GENERATION, ModelCapability.IMAGE_UNDERSTANDING}
    has_capabilities = custom_config.matches_capabilities(task_requirements)
    print(f"  任务需求: {[c.name for c in task_requirements]}")
    print(f"  模型支持: {has_capabilities}")
    
    # 5. 支持模型列表
    print("\n支持模型列表:")
    supported_models = factory.get_supported_models()
    for provider, models in supported_models.items():
        print(f"  {provider}: {', '.join(models[:3])}..." if len(models) > 3 else f"  {provider}: {', '.join(models)}")
    
    print()


def run_tests() -> bool:
    """运行测试用例"""
    print("=" * 60)
    print("运行测试用例")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # 测试1: 模型配置创建和序列化
    try:
        config = ModelConfig(
            provider="test",
            model_name="test-model",
            capabilities={ModelCapability.TEXT_GENERATION},
            cost_config=ModelCostConfig(input_cost_per_token=0.001)
        )
        
        # 序列化和反序列化
        config_dict = config.to_dict()
        config_from_dict = ModelConfig.from_dict(config_dict)
        
        assert config_from_dict.provider == "test"
        assert config_from_dict.model_name == "test-model"
        assert ModelCapability.TEXT_GENERATION in config_from_dict.capabilities
        assert config_from_dict.cost_config.input_cost_per_token == 0.001
        
        print("✓ 测试1通过: 模型配置创建和序列化")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试1失败: {e}")
        tests_failed += 1
    
    # 测试2: 模型注册表操作
    try:
        registry = ModelRegistry()
        config = ModelConfig(provider="test", model_name="test-model")
        registry.register("test-model", config)
        
        retrieved_config = registry.get("test-model")
        assert retrieved_config.provider == "test"
        assert retrieved_config.model_name == "test-model"
        
        # 测试查找功能
        config.capabilities.add(ModelCapability.CODE_GENERATION)
        results = registry.find_by_capabilities({ModelCapability.CODE_GENERATION})
        assert len(results) == 1
        assert results[0][0] == "test-model"
        
        print("✓ 测试2通过: 模型注册表操作")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试2失败: {e}")
        tests_failed += 1
    
    # 测试3: 模型工厂创建模型
    try:
        factory = ModelFactory()
        config = ModelConfig(
            provider="openai",
            model_name="gpt-4",
            capabilities={ModelCapability.TEXT_GENERATION}
        )
        
        # 验证配置
        assert factory.validate_config(config) == True
        
        # 创建模型（模拟）
        model = factory.create_model(config)
        assert model is not None
        assert model.config.provider == "openai"
        
        # 测试模型方法
        response = model.generate_text("test")
        assert "OpenAI模型" in response
        
        print("✓ 测试3通过: 模型工厂创建模型")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试3失败: {e}")
        tests_failed += 1
    
    # 测试4: 成本计算
    try:
        cost_config = ModelCostConfig(
            input_cost_per_token=0.01,
            output_cost_per_token=0.02,
            request_cost=0.1
        )
        
        cost = cost_config.calculate_cost(
            input_tokens=100,
            output_tokens=50,
            requests=2
        )
        
        expected_cost = 100 * 0.01 + 50 * 0.02 + 2 * 0.1
        assert abs(cost - expected_cost) < 0.0001
        
        print("✓ 测试4通过: 成本计算")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试4失败: {e}")
        tests_failed += 1
    
    # 测试5: 能力标签系统
    try:
        # 测试能力枚举
        capability = ModelCapability.from_string("TEXT_GENERATION")
        assert capability == ModelCapability.TEXT_GENERATION
        
        # 测试能力匹配
        config = ModelConfig(
            provider="test",
            model_name="test",
            capabilities={ModelCapability.TEXT_GENERATION, ModelCapability.CODE_GENERATION}
        )
        
        assert config.has_capability(ModelCapability.TEXT_GENERATION) == True
        assert config.has_capability(ModelCapability.IMAGE_GENERATION) == False
        assert config.matches_capabilities({ModelCapability.TEXT_GENERATION}) == True
        assert config.matches_capabilities({ModelCapability.IMAGE_GENERATION}) == False
        
        print("✓ 测试5通过: 能力标签系统")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试5失败: {e}")
        tests_failed += 1
    
    # 测试6: YAML序列化
    try:
        import tempfile
        import os
        
        registry = create_sample_registry()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            registry.save_to_yaml(temp_path)
            assert os.path.exists(temp_path)
            
            loaded_registry = ModelRegistry.load_from_yaml(temp_path)
            assert len(loaded_registry.models) == len(registry.models)
            
            print("✓ 测试6通过: YAML序列化")
            tests_passed += 1
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except Exception as e:
        print(f"✗ 测试6失败: {e}")
        tests_failed += 1
    
    # 测试7: 多提供者支持
    try:
        factory = ModelFactory()
        providers = factory.get_available_providers()
        
        assert "openai" in providers
        assert "anthropic" in providers
        assert "local" in providers
        
        # 测试不同提供者的配置验证
        openai_config = ModelConfig(provider="openai", model_name="gpt-4")
        assert factory.validate_config(openai_config) == True
        
        anthropic_config = ModelConfig(provider="anthropic", model_name="claude-3-opus")
        assert factory.validate_config(anthropic_config) == True
        
        local_config = ModelConfig(provider="local", model_name="llama-3-70b")
        assert factory.validate_config(local_config) == True
        
        print("✓ 测试7通过: 多提供者支持")
        tests_passed += 1
    except Exception as e:
        print(f"✗ 测试7失败: {e}")
        tests_failed += 1
    
    # 测试8: 模型使用统计
    try:
        config = ModelConfig(
            provider="openai",
            model_name="test",
            cost_config=ModelCostConfig(input_cost_per_token=0.001, output_cost_per_token=0.002)
        )
        
        # 使用模拟模型
        factory = ModelFactory()
        model = factory.create_model(config)
        
        # 记录使用量
        cost1 = model.record_usage(100, 50)
        assert abs(cost1 - (100 * 0.001 + 50 * 0.002)) < 0.0001
        
        cost2 = model.record_usage(200, 100)
        total_cost = cost1 + cost2
        
        stats = model.get_usage_stats()
        assert stats["total_input_tokens"] == 300
        assert stats["total_output_tokens"] == 150
        assert abs(stats["total_cost"] - total_cost) < 0.0001
        
        print("✓ 测试8通过: 模型使用统计")
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


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description="模型配置体系演示")
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
        demo_advanced_features()
        
        print("=" * 60)
        print("演示完成！")
        print("=" * 60)


if __name__ == "__main__":
    main()