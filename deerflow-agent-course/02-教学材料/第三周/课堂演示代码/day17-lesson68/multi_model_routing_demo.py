#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模型路由演示代码
Day 17 - 第68节课：多模型路由

本演示代码展示了DeerFlow Agent系统中多模型路由的核心实现，包括：
1. RoutingDecision数据类：定义路由决策结果
2. RouterConfig配置类：管理路由器配置和YAML解析
3. ModelRouter类：基础模型路由器和智能模型选择
4. RoutingStrategy抽象基类：定义路由策略接口
5. 具体路由策略实现：成本优化、性能优化、平衡策略、学习型策略
6. SmartRouter类：策略管理和自适应路由
7. UsageTracker类：模型使用情况跟踪和性能评分
8. 完整的测试套件：验证路由逻辑和策略选择

学习目标：
- 掌握多模型路由的核心概念和应用价值
- 理解基于任务特征的模型选择决策逻辑
- 能够设计和实现多种路由策略（成本优化、性能优化、平衡）
- 了解模型路由中的评分系统和权重分配方法
- 能够实现自适应路由和策略选择
"""

import os
import sys
import time
import json
import yaml
import asyncio
import logging
import random
from typing import Dict, List, Optional, Any, Type, Tuple, Union, Callable
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from functools import lru_cache
from enum import Enum
from collections import defaultdict
from datetime import datetime

# ============================================================================
# 数据类和枚举定义
# ============================================================================

@dataclass
class ModelCapabilities:
    """模型能力定义"""
    supports_vision: bool = False
    supports_function_calling: bool = False
    supports_long_context: bool = False
    max_context_length: int = 4096
    reasoning_depth: str = "medium"  # shallow, medium, deep
    
    def has_capability(self, capability: str) -> bool:
        """检查是否支持特定能力"""
        capability_map = {
            "vision": self.supports_vision,
            "function_calling": self.supports_function_calling,
            "long_context": self.supports_long_context
        }
        return capability_map.get(capability, False)

@dataclass
class ModelConfig:
    """模型配置"""
    provider: str
    model_name: str
    capabilities: ModelCapabilities
    cost_per_token: float
    config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """验证配置"""
        if self.cost_per_token < 0:
            raise ValueError("cost_per_token不能为负数")
        if not isinstance(self.capabilities, ModelCapabilities):
            # 尝试从字典转换
            if isinstance(self.capabilities, dict):
                self.capabilities = ModelCapabilities(**self.capabilities)

@dataclass
class RoutingDecision:
    """路由决策结果"""
    model_name: str
    strategy: str
    confidence: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def __str__(self) -> str:
        """字符串表示"""
        return (f"RoutingDecision(model={self.model_name}, "
                f"strategy={self.strategy}, confidence={self.confidence:.2f}, "
                f"reason='{self.reason}')")

@dataclass
class RouterConfig:
    """路由器配置"""
    model_config: Any
    default_model: str
    task_routing: Dict[str, List[str]]
    models: Dict[str, ModelConfig]
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> "RouterConfig":
        """从YAML创建配置"""
        try:
            import yaml
            data = yaml.safe_load(yaml_content)
        except ImportError:
            # 如果yaml不可用，使用JSON格式
            import json
            data = json.loads(yaml_content)
        
        # 转换模型配置
        models = {}
        for model_name, model_data in data.get("models", {}).items():
            capabilities_data = model_data.get("capabilities", {})
            capabilities = ModelCapabilities(
                supports_vision=capabilities_data.get("supports_vision", False),
                supports_function_calling=capabilities_data.get("supports_function_calling", False),
                supports_long_context=capabilities_data.get("supports_long_context", False),
                max_context_length=capabilities_data.get("max_context_length", 4096),
                reasoning_depth=capabilities_data.get("reasoning_depth", "medium")
            )
            
            models[model_name] = ModelConfig(
                provider=model_data.get("provider", "unknown"),
                model_name=model_data.get("model_name", model_name),
                capabilities=capabilities,
                cost_per_token=model_data.get("cost_per_token", 0.001),
                config=model_data.get("config", {})
            )
        
        return cls(
            model_config=data.get("model_config", {}),
            default_model=data.get("default_model", "gpt-3.5-turbo"),
            task_routing=data.get("task_routing", {}),
            models=models
        )
    
    def to_yaml(self) -> str:
        """转换为YAML"""
        try:
            import yaml
            return yaml.dump(asdict(self), allow_unicode=True)
        except ImportError:
            import json
            return json.dumps(asdict(self), indent=2, ensure_ascii=False)

@dataclass
class TaskFeatures:
    """任务特征"""
    task_type: Optional[str] = None
    complexity: float = 0.5  # 0-1，表示任务复杂程度
    urgency: float = 0.0     # 0-1，表示紧急程度
    budget: Optional[float] = None
    latency_requirement: Optional[float] = None  # 最大延迟（秒）
    required_capabilities: List[str] = field(default_factory=list)
    
    def validate(self) -> List[str]:
        """验证任务特征，返回错误列表"""
        errors = []
        if self.complexity < 0 or self.complexity > 1:
            errors.append(f"复杂度必须在0-1之间，当前值: {self.complexity}")
        if self.urgency < 0 or self.urgency > 1:
            errors.append(f"紧急度必须在0-1之间，当前值: {self.urgency}")
        if self.budget is not None and self.budget < 0:
            errors.append(f"预算不能为负数，当前值: {self.budget}")
        if self.latency_requirement is not None and self.latency_requirement <= 0:
            errors.append(f"延迟要求必须大于0，当前值: {self.latency_requirement}")
        return errors

# ============================================================================
# 模型使用情况跟踪器
# ============================================================================

class UsageTracker:
    """使用情况跟踪器"""
    
    def __init__(self):
        self.usage_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "call_count": 0,
            "total_tokens": 0,
            "success_count": 0,
            "total_response_time": 0.0,
            "last_used": None
        })
        self.performance_scores: Dict[str, float] = {}
    
    def record_usage(self, model_name: str, tokens_used: int = 0, 
                     success: bool = True, response_time: float = 0.0):
        """记录模型使用情况"""
        stats = self.usage_stats[model_name]
        stats["call_count"] += 1
        stats["total_tokens"] += tokens_used
        if success:
            stats["success_count"] += 1
        stats["total_response_time"] += response_time
        stats["last_used"] = datetime.now()
        
        # 更新性能得分
        self._update_performance_score(model_name)
    
    def get_performance_score(self, model_name: str) -> float:
        """获取模型性能得分"""
        # 如果已有计算好的得分，直接返回
        if model_name in self.performance_scores:
            return self.performance_scores[model_name]
        
        # 否则计算性能得分
        stats = self.usage_stats.get(model_name)
        if not stats or stats["call_count"] == 0:
            # 默认性能得分
            default_scores = {
                "gpt-4": 0.9,
                "gpt-3.5-turbo": 0.7,
                "claude-3": 0.85,
                "gemini-pro": 0.8
            }
            return default_scores.get(model_name, 0.5)
        
        # 基于成功率和平均响应时间计算性能得分
        success_rate = stats["success_count"] / stats["call_count"]
        
        if stats["call_count"] > 0:
            avg_response_time = stats["total_response_time"] / stats["call_count"]
            # 响应时间越短得分越高（假设理想响应时间为1秒）
            time_score = max(0, 1 - min(avg_response_time, 5) / 5)
        else:
            time_score = 0.5
        
        # 综合得分：成功率60%，响应时间40%
        performance_score = success_rate * 0.6 + time_score * 0.4
        self.performance_scores[model_name] = performance_score
        
        return performance_score
    
    def _update_performance_score(self, model_name: str):
        """更新性能得分"""
        # 清空缓存，下次调用时会重新计算
        if model_name in self.performance_scores:
            del self.performance_scores[model_name]
    
    def get_usage_summary(self) -> Dict[str, Dict[str, Any]]:
        """获取使用情况摘要"""
        summary = {}
        for model_name, stats in self.usage_stats.items():
            if stats["call_count"] > 0:
                summary[model_name] = {
                    "call_count": stats["call_count"],
                    "success_rate": stats["success_count"] / stats["call_count"],
                    "avg_tokens": stats["total_tokens"] / stats["call_count"],
                    "avg_response_time": stats["total_response_time"] / stats["call_count"],
                    "last_used": stats["last_used"]
                }
        return summary

# ============================================================================
# 路由策略抽象基类和具体实现
# ============================================================================

class RoutingStrategy(ABC):
    """路由策略基类"""
    
    @abstractmethod
    async def route(self, prompt: str, context: Dict[str, Any]) -> RoutingDecision:
        """执行路由决策"""
        pass
    
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        return self.__class__.__name__

class CostOptimizedStrategy(RoutingStrategy):
    """成本优化策略"""
    
    async def route(self, prompt: str, context: Dict[str, Any]) -> RoutingDecision:
        """选择成本最低的可用模型"""
        models = context.get("available_models", [])
        if not models:
            raise ValueError("没有可用的模型")
        
        # 找到成本最低的模型
        cheapest = min(models, key=lambda m: m.cost_per_token)
        
        return RoutingDecision(
            model_name=cheapest.model_name,
            strategy="cost_optimized",
            confidence=0.8,
            reason="选择成本最低的模型"
        )

class PerformanceOptimizedStrategy(RoutingStrategy):
    """性能优化策略"""
    
    def __init__(self, usage_tracker: Optional[UsageTracker] = None):
        self.usage_tracker = usage_tracker or UsageTracker()
    
    async def route(self, prompt: str, context: Dict[str, Any]) -> RoutingDecision:
        """选择性能最好的可用模型"""
        models = context.get("available_models", [])
        if not models:
            raise ValueError("没有可用的模型")
        
        # 获取性能得分
        performance_scores = {}
        for model in models:
            score = self.usage_tracker.get_performance_score(model.model_name)
            performance_scores[model.model_name] = score
        
        # 找到性能最好的模型
        best_model_name = max(performance_scores.items(), key=lambda x: x[1])[0]
        best_model = next(m for m in models if m.model_name == best_model_name)
        
        return RoutingDecision(
            model_name=best_model.model_name,
            strategy="performance_optimized",
            confidence=performance_scores[best_model_name],
            reason=f"选择性能最好的模型（得分: {performance_scores[best_model_name]:.2f}）"
        )

class BalancedStrategy(RoutingStrategy):
    """平衡策略"""
    
    def __init__(self, usage_tracker: Optional[UsageTracker] = None):
        self.usage_tracker = usage_tracker or UsageTracker()
    
    async def route(self, prompt: str, context: Dict[str, Any]) -> RoutingDecision:
        """平衡成本和性能的选择"""
        models = context.get("available_models", [])
        if not models:
            raise ValueError("没有可用的模型")
        
        # 计算综合得分
        best_score = -1
        best_model = None
        
        for model in models:
            # 成本得分（越便宜得分越高）
            cost_score = 1 - min(model.cost_per_token * 1000, 1.0)
            
            # 性能得分
            perf_score = self.usage_tracker.get_performance_score(model.model_name)
            
            # 平衡权重：成本40%，性能60%
            total_score = cost_score * 0.4 + perf_score * 0.6
            
            if total_score > best_score:
                best_score = total_score
                best_model = model
        
        return RoutingDecision(
            model_name=best_model.model_name,
            strategy="balanced",
            confidence=best_score,
            reason=f"平衡选择：综合得分{best_score:.2f}（成本{best_model.cost_per_token:.5f}/token，性能{self.usage_tracker.get_performance_score(best_model.model_name):.2f}）"
        )

class LearningBasedStrategy(RoutingStrategy):
    """学习型策略"""
    
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.success_rates: Dict[str, float] = {}
    
    async def route(self, prompt: str, context: Dict[str, Any]) -> RoutingDecision:
        """基于历史学习的选择"""
        models = context.get("available_models", [])
        if not models:
            raise ValueError("没有可用的模型")
        
        # 计算各模型的历史成功率
        self._update_success_rates()
        
        # 找到成功率最高的模型
        best_model_name = max(self.success_rates.items(), key=lambda x: x[1])[0]
        best_model = next((m for m in models if m.model_name == best_model_name), None)
        
        # 如果找不到，选择第一个模型
        if not best_model:
            best_model = models[0]
            best_model_name = best_model.model_name
        
        confidence = self.success_rates.get(best_model_name, 0.5)
        
        return RoutingDecision(
            model_name=best_model_name,
            strategy="learning_based",
            confidence=confidence,
            reason=f"历史成功率：{confidence:.1%}"
        )
    
    def record_result(self, model_name: str, success: bool):
        """记录模型使用结果"""
        self.history.append({
            "model": model_name,
            "success": success,
            "timestamp": datetime.now()
        })
        # 清空成功率缓存
        if model_name in self.success_rates:
            del self.success_rates[model_name]
    
    def _update_success_rates(self):
        """更新成功率缓存"""
        # 只重新计算缺失的模型
        for record in self.history:
            model_name = record["model"]
            if model_name in self.success_rates:
                continue
            
            model_history = [h for h in self.history if h["model"] == model_name]
            if model_history:
                successes = sum(1 for h in model_history if h["success"])
                self.success_rates[model_name] = successes / len(model_history)
            else:
                self.success_rates[model_name] = 0.5  # 默认值

# ============================================================================
# 模型路由器
# ============================================================================

class ModelRouter:
    """模型路由器"""
    
    def __init__(self, config: RouterConfig):
        self.config = config
        self.usage_tracker = UsageTracker()
        self.model_registry: Dict[str, Any] = {}
    
    def register_model(self, name: str, model: Any):
        """注册模型实例"""
        self.model_registry[name] = model
    
    async def route(
        self, 
        prompt: str, 
        task_type: str = None,
        budget: float = None,
        latency_requirement: float = None
    ) -> Any:
        """路由到合适的模型"""
        
        # 获取候选模型
        candidates = self._get_candidate_models(task_type)
        
        # 应用过滤规则
        filtered = self._filter_models(candidates, budget, latency_requirement)
        
        if not filtered:
            # 回退到默认模型
            default_model = self.model_registry.get(self.config.default_model)
            if not default_model:
                raise ValueError(f"默认模型 '{self.config.default_model}' 未注册")
            return default_model
        
        # 选择最佳模型
        best_model_name = self._select_best_model(filtered, prompt)
        
        # 获取模型实例
        best_model = self.model_registry.get(best_model_name)
        if not best_model:
            raise ValueError(f"模型 '{best_model_name}' 未注册")
        
        # 记录使用情况
        self.usage_tracker.record_usage(best_model_name)
        
        return best_model
    
    def _get_candidate_models(self, task_type: str) -> List[str]:
        """获取候选模型列表"""
        # 基于任务类型选择
        if task_type:
            task_models = self.config.task_routing.get(task_type, [])
            if task_models:
                return task_models
        
        # 返回所有模型
        return list(self.config.models.keys())
    
    def _filter_models(self, candidates: List[str], budget: float = None, 
                      latency_requirement: float = None) -> List[str]:
        """过滤模型"""
        filtered = []
        
        for model_name in candidates:
            model_config = self.config.models.get(model_name)
            if not model_config:
                continue
            
            # 预算过滤
            if budget is not None and model_config.cost_per_token > budget / 1000:
                continue
            
            # 这里可以添加更多过滤条件，如延迟要求等
            
            filtered.append(model_name)
        
        return filtered
    
    def _select_best_model(self, candidates: List[str], prompt: str) -> str:
        """选择最佳模型"""
        scores = {}
        
        for model_name in candidates:
            score = 0.0
            
            # 1. 性能得分（基于历史数据）
            perf_score = self.usage_tracker.get_performance_score(model_name)
            score += perf_score * 0.4
            
            # 2. 成本得分（越便宜得分越高）
            model_config = self.config.models[model_name]
            cost = model_config.cost_per_token
            cost_score = max(0, 1 - cost * 1000)  # 归一化
            score += cost_score * 0.3
            
            # 3. 适合度得分（基于提示长度和复杂度）
            fit_score = self._calculate_fit_score(model_name, prompt)
            score += fit_score * 0.3
            
            scores[model_name] = score
        
        # 返回得分最高的模型
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _calculate_fit_score(self, model_name: str, prompt: str) -> float:
        """计算模型适合度得分"""
        # 简单启发式：基于提示长度和复杂度
        model_config = self.config.models.get(model_name)
        if not model_config:
            return 0.5
        
        prompt_length = len(prompt)
        
        # 检查提示是否包含特定关键词
        complexity_indicators = ["分析", "解释", "比较", "设计", "实现", "复杂", "困难"]
        complexity = sum(1 for word in complexity_indicators if word in prompt) / len(complexity_indicators)
        
        # 长提示适合长上下文模型
        if model_config.capabilities.supports_long_context and prompt_length > 2000:
            length_score = 0.8
        elif prompt_length < 500:
            length_score = 0.9
        else:
            length_score = 0.7
        
        # 复杂任务适合深度推理模型
        if model_config.capabilities.reasoning_depth == "deep" and complexity > 0.5:
            complexity_score = 0.9
        elif model_config.capabilities.reasoning_depth == "shallow" and complexity < 0.3:
            complexity_score = 0.9
        else:
            complexity_score = 0.6
        
        # 综合得分
        return (length_score + complexity_score) / 2
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return self.usage_tracker.get_usage_summary()

# ============================================================================
# 智能路由器
# ============================================================================

class SmartRouter:
    """智能路由器"""
    
    def __init__(self):
        self.routing_strategies: Dict[str, RoutingStrategy] = {
            "cost_optimized": CostOptimizedStrategy(),
            "performance_optimized": PerformanceOptimizedStrategy(),
            "balanced": BalancedStrategy(),
            "learning_based": LearningBasedStrategy(),
        }
        self.usage_tracker = UsageTracker()
    
    async def route_with_strategy(
        self,
        strategy: str,
        prompt: str,
        context: Dict[str, Any]
    ) -> RoutingDecision:
        """使用指定策略进行路由"""
        if strategy not in self.routing_strategies:
            raise ValueError(f"未知的路由策略: {strategy}")
        
        router = self.routing_strategies[strategy]
        return await router.route(prompt, context)
    
    async def adaptive_route(self, prompt: str, context: Dict[str, Any]) -> RoutingDecision:
        """自适应路由（自动选择最佳策略）"""
        
        # 分析请求特征
        features = self._extract_features(prompt, context)
        
        # 选择最适合的策略
        strategy = self._select_strategy_for_features(features)
        
        # 使用选定的策略进行路由
        return await self.route_with_strategy(strategy, prompt, context)
    
    def _extract_features(self, prompt: str, context: Dict[str, Any]) -> Dict[str, float]:
        """提取路由特征"""
        features = {}
        
        # 提示长度特征
        features["prompt_length"] = len(prompt) / 1000  # 归一化
        
        # 复杂度特征（简单启发式）
        complexity_indicators = ["分析", "解释", "比较", "设计", "实现"]
        features["complexity"] = sum(1 for word in complexity_indicators if word in prompt) / 5
        
        # 紧急程度特征
        urgency_indicators = ["尽快", "紧急", "马上", "立即"]
        features["urgency"] = sum(1 for word in urgency_indicators if word in prompt) / 4
        
        # 成本敏感度特征
        features["cost_sensitive"] = context.get("budget", 10.0) < 5.0
        
        return features
    
    def _select_strategy_for_features(self, features: Dict[str, float]) -> str:
        """根据特征选择策略"""
        prompt_length = features.get("prompt_length", 0)
        complexity = features.get("complexity", 0)
        urgency = features.get("urgency", 0)
        cost_sensitive = features.get("cost_sensitive", False)
        
        # 决策逻辑
        if cost_sensitive:
            return "cost_optimized"
        elif urgency > 0.7:
            return "performance_optimized"
        elif complexity > 0.6:
            return "balanced"
        else:
            # 默认使用平衡策略
            return "balanced"
    
    def add_strategy(self, name: str, strategy: RoutingStrategy):
        """添加自定义策略"""
        self.routing_strategies[name] = strategy
    
    def remove_strategy(self, name: str):
        """移除策略"""
        if name in self.routing_strategies:
            del self.routing_strategies[name]
    
    def list_strategies(self) -> List[str]:
        """列出所有可用策略"""
        return list(self.routing_strategies.keys())

# ============================================================================
# 辅助函数和工具
# ============================================================================

def create_sample_router_config() -> RouterConfig:
    """创建示例路由器配置"""
    
    # 定义模型能力
    gpt4_capabilities = ModelCapabilities(
        supports_vision=False,
        supports_function_calling=True,
        supports_long_context=True,
        max_context_length=8192,
        reasoning_depth="deep"
    )
    
    gpt35_capabilities = ModelCapabilities(
        supports_vision=False,
        supports_function_calling=True,
        supports_long_context=False,
        max_context_length=4096,
        reasoning_depth="medium"
    )
    
    claude_capabilities = ModelCapabilities(
        supports_vision=False,
        supports_function_calling=True,
        supports_long_context=True,
        max_context_length=100000,
        reasoning_depth="deep"
    )
    
    gemini_capabilities = ModelCapabilities(
        supports_vision=True,
        supports_function_calling=True,
        supports_long_context=True,
        max_context_length=32768,
        reasoning_depth="medium"
    )
    
    # 创建模型配置
    models = {
        "gpt-4": ModelConfig(
            provider="openai",
            model_name="gpt-4",
            capabilities=gpt4_capabilities,
            cost_per_token=0.00003,
            config={"temperature": 0.7, "max_tokens": 2000}
        ),
        "gpt-3.5-turbo": ModelConfig(
            provider="openai",
            model_name="gpt-3.5-turbo",
            capabilities=gpt35_capabilities,
            cost_per_token=0.0000015,
            config={"temperature": 0.7, "max_tokens": 1000}
        ),
        "claude-3": ModelConfig(
            provider="anthropic",
            model_name="claude-3-opus",
            capabilities=claude_capabilities,
            cost_per_token=0.00015,
            config={"temperature": 0.7, "max_tokens": 4000}
        ),
        "gemini-pro": ModelConfig(
            provider="google",
            model_name="gemini-pro",
            capabilities=gemini_capabilities,
            cost_per_token=0.000001,
            config={"temperature": 0.7, "max_tokens": 1500}
        )
    }
    
    # 定义任务路由
    task_routing = {
        "code_generation": ["gpt-4", "claude-3"],
        "text_analysis": ["gpt-4", "gemini-pro"],
        "quick_answer": ["gpt-3.5-turbo"],
        "creative_writing": ["claude-3", "gpt-4"],
        "vision_analysis": ["gemini-pro"]
    }
    
    return RouterConfig(
        model_config={},
        default_model="gpt-3.5-turbo",
        task_routing=task_routing,
        models=models
    )

def analyze_task_from_text(text: str) -> TaskFeatures:
    """从文本分析任务特征"""
    features = TaskFeatures()
    
    # 简单启发式分析
    text_lower = text.lower()
    
    # 任务类型识别
    if any(word in text_lower for word in ["代码", "编程", "函数", "类", "算法"]):
        features.task_type = "code_generation"
    elif any(word in text_lower for word in ["分析", "解释", "总结", "理解"]):
        features.task_type = "text_analysis"
    elif any(word in text_lower for word in ["写", "创作", "故事", "文章", "邮件"]):
        features.task_type = "creative_writing"
    elif any(word in text_lower for word in ["图片", "图像", "照片", "视觉", "识别"]):
        features.task_type = "vision_analysis"
    else:
        features.task_type = "quick_answer"
    
    # 复杂度分析（基于关键词）
    complexity_keywords = ["复杂", "困难", "深入", "详细", "分析", "设计", "实现"]
    features.complexity = sum(1 for word in complexity_keywords if word in text) / len(complexity_keywords)
    
    # 紧急度分析
    urgency_keywords = ["尽快", "紧急", "马上", "立即", "赶快", "快点"]
    features.urgency = sum(1 for word in urgency_keywords if word in text) / len(urgency_keywords)
    
    # 能力要求
    if "图片" in text or "图像" in text:
        features.required_capabilities.append("vision")
    
    if "函数调用" in text or "工具调用" in text:
        features.required_capabilities.append("function_calling")
    
    if len(text) > 2000:
        features.required_capabilities.append("long_context")
    
    return features

# ============================================================================
# 演示主函数
# ============================================================================

async def demonstrate_basic_routing():
    """演示基础路由功能"""
    print("=" * 60)
    print("演示1: 基础模型路由")
    print("=" * 60)
    
    # 创建配置和路由器
    config = create_sample_router_config()
    router = ModelRouter(config)
    
    # 模拟注册模型（实际应用中会注册真实的模型实例）
    for model_name in config.models:
        router.register_model(model_name, f"模拟模型实例: {model_name}")
    
    # 测试不同任务的路由
    test_tasks = [
        ("写一个Python函数计算斐波那契数列", "code_generation"),
        ("分析这篇技术文章的主要观点", "text_analysis"),
        ("帮我写一封请假邮件", "creative_writing"),
        ("描述这张图片中的内容", "vision_analysis"),
        ("今天天气怎么样？", "quick_answer")
    ]
    
    for prompt, task_type in test_tasks:
        print(f"\n任务: {prompt}")
        print(f"任务类型: {task_type}")
        
        try:
            # 执行路由
            model = await router.route(prompt, task_type=task_type)
            print(f"选择的模型: {model}")
            
            # 获取使用统计
            stats = router.get_usage_stats()
            print(f"使用统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"路由失败: {e}")

async def demonstrate_strategy_routing():
    """演示策略路由功能"""
    print("\n" + "=" * 60)
    print("演示2: 策略路由")
    print("=" * 60)
    
    # 创建智能路由器
    smart_router = SmartRouter()
    
    # 创建模拟模型列表
    class MockModel:
        def __init__(self, name: str, cost: float):
            self.model_name = name
            self.cost_per_token = cost
    
    models = [
        MockModel("gpt-4", 0.00003),
        MockModel("gpt-3.5-turbo", 0.0000015),
        MockModel("claude-3", 0.00015),
        MockModel("gemini-pro", 0.000001)
    ]
    
    # 测试不同策略
    test_prompts = [
        ("帮我写一个简单的Python脚本", {"budget": 2.0}),
        ("紧急！系统出现故障需要立即分析", {"budget": 10.0}),
        ("分析这个复杂的算法问题", {"budget": 5.0}),
        ("基于历史数据选择最佳模型", {"budget": 3.0})
    ]
    
    strategies = ["cost_optimized", "performance_optimized", "balanced", "learning_based"]
    
    for prompt, context in test_prompts:
        print(f"\n提示: {prompt}")
        print(f"上下文: {context}")
        
        # 添加上下文中的可用模型
        context["available_models"] = models
        
        for strategy in strategies:
            try:
                decision = await smart_router.route_with_strategy(strategy, prompt, context)
                print(f"  {strategy}: {decision.model_name} (置信度: {decision.confidence:.2f}, 理由: {decision.reason})")
            except Exception as e:
                print(f"  {strategy}: 失败 - {e}")

async def demonstrate_adaptive_routing():
    """演示自适应路由功能"""
    print("\n" + "=" * 60)
    print("演示3: 自适应路由")
    print("=" * 60)
    
    # 创建智能路由器
    smart_router = SmartRouter()
    
    # 创建模拟模型列表
    class MockModel:
        def __init__(self, name: str, cost: float):
            self.model_name = name
            self.cost_per_token = cost
    
    models = [
        MockModel("gpt-4", 0.00003),
        MockModel("gpt-3.5-turbo", 0.0000015),
        MockModel("claude-3", 0.00015),
        MockModel("gemini-pro", 0.000001)
    ]
    
    # 测试自适应路由
    test_cases = [
        ("预算有限，帮我写个简单的脚本", {"budget": 1.0}),
        ("紧急情况！系统崩溃需要立即分析日志", {"budget": 10.0}),
        ("分析这个复杂的机器学习算法，需要深入思考", {"budget": 5.0}),
        ("描述这张图片的内容", {"budget": 3.0})
    ]
    
    for prompt, context in test_cases:
        print(f"\n提示: {prompt}")
        print(f"上下文: {context}")
        
        # 添加上下文中的可用模型
        context["available_models"] = models
        
        try:
            decision = await smart_router.adaptive_route(prompt, context)
            print(f"自适应选择: {decision.model_name}")
            print(f"  使用的策略: {decision.strategy}")
            print(f"  置信度: {decision.confidence:.2f}")
            print(f"  理由: {decision.reason}")
        except Exception as e:
            print(f"自适应路由失败: {e}")

# ============================================================================
# 测试套件
# ============================================================================

def run_tests():
    """运行测试"""
    print("\n" + "=" * 60)
    print("测试套件")
    print("=" * 60)
    
    tests_passed = 0
    tests_failed = 0
    
    # 测试1: 配置加载
    try:
        config = create_sample_router_config()
        assert config.default_model == "gpt-3.5-turbo"
        assert len(config.models) == 4
        assert "gpt-4" in config.models
        print("✅ 测试1通过: 配置创建")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ 测试1失败: {e}")
        tests_failed += 1
    
    # 测试2: 任务特征分析
    try:
        features = analyze_task_from_text("写一个复杂的Python算法")
        assert features.task_type == "code_generation"
        assert features.complexity > 0
        print("✅ 测试2通过: 任务特征分析")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ 测试2失败: {e}")
        tests_failed += 1
    
    # 测试3: 使用跟踪器
    try:
        tracker = UsageTracker()
        tracker.record_usage("gpt-4", tokens_used=100, success=True, response_time=1.5)
        score = tracker.get_performance_score("gpt-4")
        assert 0 <= score <= 1
        print("✅ 测试3通过: 使用跟踪器")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ 测试3失败: {e}")
        tests_failed += 1
    
    # 测试4: 路由策略
    try:
        strategy = CostOptimizedStrategy()
        assert isinstance(strategy, RoutingStrategy)
        print("✅ 测试4通过: 路由策略基类")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ 测试4失败: {e}")
        tests_failed += 1
    
    # 测试5: 模型路由器
    try:
        config = create_sample_router_config()
        router = ModelRouter(config)
        assert router.config == config
        print("✅ 测试5通过: 模型路由器")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ 测试5失败: {e}")
        tests_failed += 1
    
    # 测试6: 智能路由器
    try:
        smart_router = SmartRouter()
        strategies = smart_router.list_strategies()
        assert len(strategies) >= 4
        print("✅ 测试6通过: 智能路由器")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ 测试6失败: {e}")
        tests_failed += 1
    
    # 测试7: 路由决策序列化
    try:
        decision = RoutingDecision(
            model_name="gpt-4",
            strategy="balanced",
            confidence=0.85,
            reason="测试决策"
        )
        decision_dict = decision.to_dict()
        assert decision_dict["model_name"] == "gpt-4"
        assert decision_dict["confidence"] == 0.85
        print("✅ 测试7通过: 路由决策序列化")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ 测试7失败: {e}")
        tests_failed += 1
    
    # 测试8: 配置YAML序列化
    try:
        config = create_sample_router_config()
        yaml_str = config.to_yaml()
        # 尝试重新解析
        if "yaml" in sys.modules:
            parsed = yaml.safe_load(yaml_str)
            assert parsed is not None
        print("✅ 测试8通过: 配置YAML序列化")
        tests_passed += 1
    except Exception as e:
        print(f"❌ 测试8失败: {e}")
        tests_failed += 1
    
    # 总结
    print(f"\n测试总结: 通过 {tests_passed}/8, 失败 {tests_failed}/8")
    
    if tests_failed == 0:
        print("🎉 所有测试通过！")
        return True
    else:
        print("⚠️  部分测试失败，请检查实现")
        return False

# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    print("多模型路由系统演示")
    print("=" * 60)
    
    # 运行测试
    if not run_tests():
        print("\n测试失败，停止演示")
        return
    
    # 运行演示
    await demonstrate_basic_routing()
    await demonstrate_strategy_routing()
    await demonstrate_adaptive_routing()
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)

if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 运行主函数
    asyncio.run(main())