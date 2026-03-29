#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
思考模式支持演示代码
Day 17 - 第66节课：思考模式支持

本演示代码展示了DeerFlow Agent系统中思考模式支持的核心实现，包括：
1. ThinkingConfig数据类：定义思考模式配置和验证
2. ThinkingModeSelector：基于规则的智能模式选择器
3. 思考模式参数配置：YAML配置解析和验证
4. 任务特征分析：类型、复杂度、紧急度等多维度分析
5. 模式应用器：将思考模式应用到模型调用

学习目标：
- 掌握思考模式的概念和应用场景
- 理解不同思考模式（快速、平衡、深度、创意）的参数配置
- 能够实现基于规则的智能模式选择器
- 能够分析任务特征并动态选择合适思考模式
- 能够设计和扩展新的思考模式配置
"""

import os
import sys
import time
import json
import yaml
import asyncio
import logging
from typing import Dict, List, Optional, Any, Type, Tuple, Union, Callable
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from functools import lru_cache
from enum import Enum
import random
from collections import defaultdict

# ============================================================================
# 数据类和枚举定义
# ============================================================================

class ThinkingMode(str, Enum):
    """思考模式枚举"""
    FAST = "fast"          # 快速模式：低temperature，浅层推理，快速响应
    BALANCED = "balanced"  # 平衡模式：适中参数，平衡速度和质量
    DEEP = "deep"          # 深度模式：高temperature，深度推理，允许反思
    CREATIVE = "creative"  # 创意模式：高temperature，高随机性，创意生成
    
    def description(self) -> str:
        """获取模式描述"""
        descriptions = {
            ThinkingMode.FAST: "快速响应模式，适用于简单查询和快速回答",
            ThinkingMode.BALANCED: "平衡模式，适用于大多数日常任务",
            ThinkingMode.DEEP: "深度思考模式，适用于复杂问题和需要推理的任务",
            ThinkingMode.CREATIVE: "创意生成模式，适用于写作、创意和发散性思考"
        }
        return descriptions.get(self, "未知模式")


class TaskType(str, Enum):
    """任务类型枚举"""
    CODE_GENERATION = "code_generation"      # 代码生成
    DEBUGGING = "debugging"                  # 调试
    CREATIVE_WRITING = "creative_writing"    # 创意写作
    DATA_ANALYSIS = "data_analysis"          # 数据分析
    QUICK_ANSWER = "quick_answer"            # 快速回答
    RESEARCH = "research"                    # 研究
    PLANNING = "planning"                    # 规划
    TRANSLATION = "translation"              # 翻译
    SUMMARIZATION = "summarization"          # 摘要


class ReasoningDepth(str, Enum):
    """推理深度枚举"""
    SHALLOW = "shallow"      # 浅层推理：简单直接的回答
    MEDIUM = "medium"        # 中等推理：适度分析和解释
    DEEP = "deep"            # 深度推理：深入分析和多角度思考


@dataclass
class TaskFeatures:
    """任务特征
    
    Attributes:
        task_type: 任务类型
        complexity: 复杂度评分 (0.0-1.0)
        urgency: 紧急程度评分 (0.0-1.0)
        domain: 领域/上下文
        constraints: 额外约束条件
    """
    task_type: TaskType
    complexity: float = 0.5
    urgency: float = 0.5
    domain: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """验证任务特征有效性"""
        errors = []
        
        if not 0.0 <= self.complexity <= 1.0:
            errors.append(f"复杂度必须在0.0-1.0之间，当前值: {self.complexity}")
        
        if not 0.0 <= self.urgency <= 1.0:
            errors.append(f"紧急度必须在0.0-1.0之间，当前值: {self.urgency}")
        
        return errors


@dataclass
class ThinkingConfig:
    """思考模式配置
    
    Attributes:
        modes: 思考模式配置字典
    """
    modes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ThinkingConfig":
        """从YAML内容创建配置
        
        Args:
            yaml_content: YAML格式的配置内容
            
        Returns:
            ThinkingConfig实例
        """
        try:
            data = yaml.safe_load(yaml_content)
            if data is None:
                return cls()
            
            # 支持不同的YAML结构
            if "thinking" in data:
                modes = data.get("thinking", {}).get("modes", {})
            else:
                modes = data.get("modes", {})
            
            return cls(modes=modes)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML解析失败: {e}")
    
    @classmethod
    def from_file(cls, file_path: str) -> "ThinkingConfig":
        """从YAML文件创建配置
        
        Args:
            file_path: YAML文件路径
            
        Returns:
            ThinkingConfig实例
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return cls.from_yaml(f.read())
        except (IOError, OSError) as e:
            raise ValueError(f"文件读取失败: {e}")
    
    def validate(self) -> List[str]:
        """验证配置有效性
        
        Returns:
            错误消息列表，空列表表示配置有效
        """
        errors = []
        
        if not self.modes:
            errors.append("配置中未定义任何思考模式")
            return errors
        
        # 定义必需参数
        required_params = {"temperature", "max_tokens", "reasoning_depth"}
        
        for mode_name, mode_config in self.modes.items():
            # 检查必需参数
            for param in required_params:
                if param not in mode_config:
                    errors.append(f"模式 '{mode_name}' 缺少必需参数 '{param}'")
            
            # 验证temperature范围 (0.0-2.0)
            temp = mode_config.get("temperature")
            if temp is not None:
                if not isinstance(temp, (int, float)):
                    errors.append(f"模式 '{mode_name}' temperature参数类型错误: {type(temp)}")
                elif not 0.0 <= temp <= 2.0:
                    errors.append(f"模式 '{mode_name}' temperature参数超出范围 (0.0-2.0): {temp}")
            
            # 验证max_tokens为正整数
            tokens = mode_config.get("max_tokens")
            if tokens is not None:
                if not isinstance(tokens, int):
                    errors.append(f"模式 '{mode_name}' max_tokens参数类型错误: {type(tokens)}")
                elif tokens <= 0:
                    errors.append(f"模式 '{mode_name}' max_tokens参数必须为正整数: {tokens}")
            
            # 验证reasoning_depth有效值
            depth = mode_config.get("reasoning_depth")
            if depth is not None:
                valid_depths = ["shallow", "medium", "deep"]
                if isinstance(depth, str) and depth.lower() not in valid_depths:
                    errors.append(f"模式 '{mode_name}' reasoning_depth参数无效值: {depth}，有效值: {valid_depths}")
            
            # 验证可选参数
            if "top_p" in mode_config:
                top_p = mode_config.get("top_p")
                if not 0.0 <= top_p <= 1.0:
                    errors.append(f"模式 '{mode_name}' top_p参数超出范围 (0.0-1.0): {top_p}")
            
            if "frequency_penalty" in mode_config:
                penalty = mode_config.get("frequency_penalty")
                if not -2.0 <= penalty <= 2.0:
                    errors.append(f"模式 '{mode_name}' frequency_penalty参数超出范围 (-2.0-2.0): {penalty}")
            
            if "presence_penalty" in mode_config:
                penalty = mode_config.get("presence_penalty")
                if not -2.0 <= penalty <= 2.0:
                    errors.append(f"模式 '{mode_name}' presence_penalty参数超出范围 (-2.0-2.0): {penalty}")
        
        return errors
    
    def get_mode_config(self, mode_name: str) -> Dict[str, Any]:
        """获取指定模式的配置
        
        Args:
            mode_name: 模式名称
            
        Returns:
            模式配置字典
            
        Raises:
            ValueError: 模式不存在
        """
        if mode_name not in self.modes:
            raise ValueError(f"思考模式 '{mode_name}' 不存在")
        
        return self.modes[mode_name].copy()
    
    def add_mode(self, mode_name: str, config: Dict[str, Any]) -> None:
        """添加新的思考模式
        
        Args:
            mode_name: 模式名称
            config: 模式配置
        """
        self.modes[mode_name] = config.copy()
    
    def remove_mode(self, mode_name: str) -> bool:
        """移除思考模式
        
        Args:
            mode_name: 模式名称
            
        Returns:
            是否成功移除
        """
        if mode_name in self.modes:
            del self.modes[mode_name]
            return True
        return False
    
    def to_yaml(self) -> str:
        """将配置转换为YAML格式
        
        Returns:
            YAML格式字符串
        """
        data = {"thinking": {"modes": self.modes}}
        return yaml.dump(data, allow_unicode=True, sort_keys=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典
        
        Returns:
            配置字典
        """
        return {"modes": self.modes.copy()}


# ============================================================================
# 思考模式选择器
# ============================================================================

class ThinkingModeSelector:
    """思考模式选择器
    
    根据任务特征智能选择最合适的思考模式，支持：
    1. 基于任务类型的模式映射
    2. 基于复杂度的模式选择
    3. 基于紧急度的模式覆盖
    4. 自定义规则扩展
    """
    
    def __init__(self, config: ThinkingConfig):
        """初始化选择器
        
        Args:
            config: 思考模式配置
        """
        self.config = config
        
        # 默认任务类型映射
        self._type_to_mode = {
            TaskType.CODE_GENERATION: ThinkingMode.BALANCED,
            TaskType.DEBUGGING: ThinkingMode.DEEP,
            TaskType.CREATIVE_WRITING: ThinkingMode.CREATIVE,
            TaskType.DATA_ANALYSIS: ThinkingMode.BALANCED,
            TaskType.QUICK_ANSWER: ThinkingMode.FAST,
            TaskType.RESEARCH: ThinkingMode.DEEP,
            TaskType.PLANNING: ThinkingMode.DEEP,
            TaskType.TRANSLATION: ThinkingMode.BALANCED,
            TaskType.SUMMARIZATION: ThinkingMode.FAST,
        }
        
        # 自定义规则列表
        self._custom_rules: List[Callable[[TaskFeatures], Optional[str]]] = []
    
    def add_type_mapping(self, task_type: TaskType, mode: ThinkingMode) -> None:
        """添加或更新任务类型映射
        
        Args:
            task_type: 任务类型
            mode: 对应的思考模式
        """
        self._type_to_mode[task_type] = mode
    
    def add_custom_rule(self, rule_func: Callable[[TaskFeatures], Optional[str]]) -> None:
        """添加自定义规则
        
        Args:
            rule_func: 规则函数，接收TaskFeatures返回模式名称或None
        """
        self._custom_rules.append(rule_func)
    
    def select_mode(self, features: TaskFeatures) -> str:
        """选择思考模式
        
        Args:
            features: 任务特征
            
        Returns:
            选择的思考模式名称
            
        Raises:
            ValueError: 任务特征无效或无法选择模式
        """
        # 验证任务特征
        errors = features.validate()
        if errors:
            raise ValueError(f"任务特征无效: {', '.join(errors)}")
        
        # 应用自定义规则（优先级最高）
        for rule in self._custom_rules:
            result = rule(features)
            if result is not None:
                if result in self.config.modes:
                    return result
                else:
                    logging.warning(f"自定义规则返回了不存在的模式: {result}")
        
        # 规则1: 基于紧急程度（最高优先级）
        if features.urgency > 0.8:
            return ThinkingMode.FAST.value
        
        # 规则2: 基于任务类型
        if features.task_type in self._type_to_mode:
            mode = self._type_to_mode[features.task_type]
            return mode.value
        
        # 规则3: 基于复杂度
        if features.complexity > 0.7:
            return ThinkingMode.DEEP.value
        elif features.complexity > 0.3:
            return ThinkingMode.BALANCED.value
        else:
            return ThinkingMode.FAST.value
        
        # 默认返回平衡模式（理论上不会执行到这里）
        return ThinkingMode.BALANCED.value
    
    def select_mode_with_confidence(self, features: TaskFeatures) -> Tuple[str, float]:
        """选择思考模式并返回置信度
        
        Args:
            features: 任务特征
            
        Returns:
            (模式名称, 置信度) 元组
        """
        try:
            # 获取基本模式选择
            mode_name = self.select_mode(features)
            
            # 计算置信度
            confidence = self._calculate_confidence(features, mode_name)
            
            return mode_name, confidence
        except Exception as e:
            # 发生错误时返回默认模式和低置信度
            logging.error(f"模式选择失败: {e}")
            return ThinkingMode.BALANCED.value, 0.3
    
    def _calculate_confidence(self, features: TaskFeatures, selected_mode: str) -> float:
        """计算模式选择置信度
        
        Args:
            features: 任务特征
            selected_mode: 选择的模式
            
        Returns:
            置信度分数 (0.0-1.0)
        """
        confidence = 0.5  # 基础置信度
        
        # 基于紧急度的置信度调整
        if features.urgency > 0.8 and selected_mode == ThinkingMode.FAST.value:
            confidence += 0.3
        elif features.urgency <= 0.8 and selected_mode == ThinkingMode.FAST.value:
            confidence -= 0.2
        
        # 基于任务类型匹配的置信度调整
        if features.task_type in self._type_to_mode:
            expected_mode = self._type_to_mode[features.task_type].value
            if selected_mode == expected_mode:
                confidence += 0.2
            else:
                confidence -= 0.1
        
        # 基于复杂度的置信度调整
        if features.complexity > 0.7 and selected_mode == ThinkingMode.DEEP.value:
            confidence += 0.2
        elif features.complexity < 0.3 and selected_mode == ThinkingMode.FAST.value:
            confidence += 0.1
        
        # 确保置信度在合理范围内
        confidence = max(0.1, min(1.0, confidence))
        
        return round(confidence, 2)
    
    def get_available_modes(self) -> List[str]:
        """获取所有可用思考模式
        
        Returns:
            模式名称列表
        """
        return list(self.config.modes.keys())
    
    def get_mode_description(self, mode_name: str) -> str:
        """获取模式描述
        
        Args:
            mode_name: 模式名称
            
        Returns:
            模式描述文本
        """
        try:
            mode_enum = ThinkingMode(mode_name)
            return mode_enum.description()
        except ValueError:
            return f"自定义模式: {mode_name}"
    
    def explain_selection(self, features: TaskFeatures) -> Dict[str, Any]:
        """解释模式选择过程
        
        Args:
            features: 任务特征
            
        Returns:
            选择解释字典
        """
        explanation = {
            "task_features": asdict(features),
            "applied_rules": [],
            "considered_modes": [],
            "final_selection": None,
            "confidence": 0.0
        }
        
        try:
            # 获取选择结果
            mode_name, confidence = self.select_mode_with_confidence(features)
            explanation["final_selection"] = mode_name
            explanation["confidence"] = confidence
            
            # 记录应用的自定义规则
            for i, rule in enumerate(self._custom_rules):
                result = rule(features)
                if result is not None:
                    explanation["applied_rules"].append({
                        "rule_type": "custom",
                        "rule_index": i,
                        "suggested_mode": result
                    })
            
            # 记录任务类型映射
            if features.task_type in self._type_to_mode:
                explanation["applied_rules"].append({
                    "rule_type": "task_type_mapping",
                    "task_type": features.task_type.value,
                    "mapped_mode": self._type_to_mode[features.task_type].value
                })
            
            # 记录紧急度规则
            if features.urgency > 0.8:
                explanation["applied_rules"].append({
                    "rule_type": "urgency_override",
                    "urgency": features.urgency,
                    "reason": "高紧急度强制使用快速模式"
                })
            
            # 记录复杂度规则
            if features.complexity > 0.7:
                explanation["applied_rules"].append({
                    "rule_type": "complexity_based",
                    "complexity": features.complexity,
                    "reason": "高复杂度推荐深度模式"
                })
            elif features.complexity > 0.3:
                explanation["applied_rules"].append({
                    "rule_type": "complexity_based",
                    "complexity": features.complexity,
                    "reason": "中等复杂度推荐平衡模式"
                })
            else:
                explanation["applied_rules"].append({
                    "rule_type": "complexity_based",
                    "complexity": features.complexity,
                    "reason": "低复杂度推荐快速模式"
                })
            
            # 记录考虑的模式
            explanation["considered_modes"] = self.get_available_modes()
            
        except Exception as e:
            explanation["error"] = str(e)
        
        return explanation


# ============================================================================
# 思考模式应用器
# ============================================================================

class ThinkingModeApplicator:
    """思考模式应用器
    
    将思考模式配置应用到实际的模型调用中，支持：
    1. 参数提取和验证
    2. 特殊模式特性处理（如反思迭代）
    3. 缓存管理
    4. 效果跟踪和评估
    """
    
    def __init__(self, config: ThinkingConfig):
        """初始化应用器
        
        Args:
            config: 思考模式配置
        """
        self.config = config
        self._cache: Dict[str, Any] = {}
        self._performance_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "call_count": 0,
            "total_time": 0.0,
            "success_count": 0,
            "error_count": 0
        })
    
    def apply_to_model_call(self, mode_name: str, model_call_func: Callable, 
                           prompt: str, **kwargs) -> Any:
        """将思考模式应用到模型调用
        
        Args:
            mode_name: 思考模式名称
            model_call_func: 模型调用函数
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            模型调用结果
            
        Raises:
            ValueError: 模式不存在或配置无效
        """
        start_time = time.time()
        
        try:
            # 获取模式配置
            mode_config = self.config.get_mode_config(mode_name)
            
            # 提取和验证参数
            call_kwargs = self._extract_call_parameters(mode_config, kwargs)
            
            # 检查缓存
            cache_key = self._generate_cache_key(mode_name, prompt, call_kwargs)
            if mode_config.get("use_cache", True) and cache_key in self._cache:
                logging.debug(f"缓存命中: {cache_key}")
                result = self._cache[cache_key]
                
                # 更新性能统计
                self._update_stats(mode_name, True, time.time() - start_time, True)
                
                return result
            
            # 应用特殊模式特性
            if mode_config.get("allow_reflection", False):
                # 启用反思迭代
                result = self._apply_with_reflection(model_call_func, prompt, call_kwargs, 
                                                    mode_config.get("max_iterations", 1))
            else:
                # 普通调用
                result = model_call_func(prompt, **call_kwargs)
            
            # 缓存结果
            if mode_config.get("use_cache", True):
                self._cache[cache_key] = result
            
            # 更新性能统计
            self._update_stats(mode_name, True, time.time() - start_time, False)
            
            return result
            
        except Exception as e:
            # 更新错误统计
            self._update_stats(mode_name, False, time.time() - start_time, False)
            raise e
    
    async def apply_to_model_call_async(self, mode_name: str, model_call_func: Callable,
                                       prompt: str, **kwargs) -> Any:
        """异步应用思考模式到模型调用
        
        Args:
            mode_name: 思考模式名称
            model_call_func: 异步模型调用函数
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            模型调用结果
        """
        start_time = time.time()
        
        try:
            # 获取模式配置
            mode_config = self.config.get_mode_config(mode_name)
            
            # 提取和验证参数
            call_kwargs = self._extract_call_parameters(mode_config, kwargs)
            
            # 检查缓存
            cache_key = self._generate_cache_key(mode_name, prompt, call_kwargs)
            if mode_config.get("use_cache", True) and cache_key in self._cache:
                logging.debug(f"缓存命中: {cache_key}")
                result = self._cache[cache_key]
                
                # 更新性能统计
                self._update_stats(mode_name, True, time.time() - start_time, True)
                
                return result
            
            # 应用特殊模式特性
            if mode_config.get("allow_reflection", False):
                # 启用反思迭代（异步版本）
                result = await self._apply_with_reflection_async(
                    model_call_func, prompt, call_kwargs, 
                    mode_config.get("max_iterations", 1)
                )
            else:
                # 普通异步调用
                result = await model_call_func(prompt, **call_kwargs)
            
            # 缓存结果
            if mode_config.get("use_cache", True):
                self._cache[cache_key] = result
            
            # 更新性能统计
            self._update_stats(mode_name, True, time.time() - start_time, False)
            
            return result
            
        except Exception as e:
            # 更新错误统计
            self._update_stats(mode_name, False, time.time() - start_time, False)
            raise e
    
    def _extract_call_parameters(self, mode_config: Dict[str, Any], 
                                user_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """提取模型调用参数
        
        Args:
            mode_config: 模式配置
            user_kwargs: 用户提供的参数
            
        Returns:
            合并后的调用参数
        """
        # 基础参数映射
        param_mapping = {
            "temperature": "temperature",
            "max_tokens": "max_tokens",
            "top_p": "top_p",
            "frequency_penalty": "frequency_penalty",
            "presence_penalty": "presence_penalty",
            "stop": "stop",
            "best_of": "best_of",
            "n": "n"
        }
        
        call_kwargs = {}
        
        # 从模式配置中提取参数
        for config_key, call_key in param_mapping.items():
            if config_key in mode_config:
                call_kwargs[call_key] = mode_config[config_key]
        
        # 用户提供的参数覆盖模式配置
        for key, value in user_kwargs.items():
            call_kwargs[key] = value
        
        return call_kwargs
    
    def _generate_cache_key(self, mode_name: str, prompt: str, 
                           call_kwargs: Dict[str, Any]) -> str:
        """生成缓存键
        
        Args:
            mode_name: 模式名称
            prompt: 输入提示
            call_kwargs: 调用参数
            
        Returns:
            缓存键字符串
        """
        import hashlib
        
        # 创建可哈希的字典表示
        cache_dict = {
            "mode": mode_name,
            "prompt": prompt,
            "kwargs": tuple(sorted(call_kwargs.items()))
        }
        
        # 使用SHA256生成哈希
        cache_str = json.dumps(cache_dict, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(cache_str.encode('utf-8')).hexdigest()
    
    def _apply_with_reflection(self, model_call_func: Callable, prompt: str,
                              call_kwargs: Dict[str, Any], iterations: int) -> Any:
        """应用反思迭代
        
        Args:
            model_call_func: 模型调用函数
            prompt: 输入提示
            call_kwargs: 调用参数
            iterations: 迭代次数
            
        Returns:
            反思后的结果
        """
        current_result = model_call_func(prompt, **call_kwargs)
        
        for i in range(iterations - 1):  # 第一次已经执行了
            reflection_prompt = (
                f"请对以下内容进行第{i+1}次反思和改进:\n\n"
                f"原始提示: {prompt}\n\n"
                f"当前结果: {current_result}\n\n"
                f"请提供改进后的版本:"
            )
            
            current_result = model_call_func(reflection_prompt, **call_kwargs)
        
        return current_result
    
    async def _apply_with_reflection_async(self, model_call_func: Callable, prompt: str,
                                          call_kwargs: Dict[str, Any], iterations: int) -> Any:
        """异步应用反思迭代
        
        Args:
            model_call_func: 异步模型调用函数
            prompt: 输入提示
            call_kwargs: 调用参数
            iterations: 迭代次数
            
        Returns:
            反思后的结果
        """
        current_result = await model_call_func(prompt, **call_kwargs)
        
        for i in range(iterations - 1):  # 第一次已经执行了
            reflection_prompt = (
                f"请对以下内容进行第{i+1}次反思和改进:\n\n"
                f"原始提示: {prompt}\n\n"
                f"当前结果: {current_result}\n\n"
                f"请提供改进后的版本:"
            )
            
            current_result = await model_call_func(reflection_prompt, **call_kwargs)
        
        return current_result
    
    def _update_stats(self, mode_name: str, success: bool, 
                     duration: float, cached: bool) -> None:
        """更新性能统计
        
        Args:
            mode_name: 模式名称
            success: 是否成功
            duration: 调用时长
            cached: 是否来自缓存
        """
        stats = self._performance_stats[mode_name]
        stats["call_count"] += 1
        stats["total_time"] += duration
        
        if success:
            stats["success_count"] += 1
        else:
            stats["error_count"] += 1
        
        if cached:
            stats["cache_hits"] = stats.get("cache_hits", 0) + 1
    
    def get_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取性能统计
        
        Returns:
            性能统计字典
        """
        # 计算衍生指标
        result = {}
        for mode_name, stats in self._performance_stats.items():
            mode_stats = stats.copy()
            
            call_count = mode_stats["call_count"]
            if call_count > 0:
                mode_stats["average_time"] = mode_stats["total_time"] / call_count
                mode_stats["success_rate"] = mode_stats["success_count"] / call_count
                mode_stats["error_rate"] = mode_stats["error_count"] / call_count
                
                cache_hits = mode_stats.get("cache_hits", 0)
                mode_stats["cache_hit_rate"] = cache_hits / call_count if call_count > 0 else 0.0
            else:
                mode_stats["average_time"] = 0.0
                mode_stats["success_rate"] = 0.0
                mode_stats["error_rate"] = 0.0
                mode_stats["cache_hit_rate"] = 0.0
            
            result[mode_name] = mode_stats
        
        return result
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logging.info("思考模式缓存已清空")
    
    def reset_stats(self) -> None:
        """重置性能统计"""
        self._performance_stats.clear()
        logging.info("性能统计已重置")


# ============================================================================
# 工厂函数和工具函数
# ============================================================================

def create_default_thinking_config() -> ThinkingConfig:
    """创建默认思考模式配置
    
    Returns:
        包含默认思考模式的配置
    """
    yaml_content = """
thinking:
  modes:
    fast:
      temperature: 0.3
      max_tokens: 500
      reasoning_depth: "shallow"
      use_cache: true
      description: "快速响应模式，适用于简单查询"
    
    balanced:
      temperature: 0.7
      max_tokens: 1000
      reasoning_depth: "medium"
      use_cache: true
      description: "平衡模式，适用于大多数任务"
    
    deep:
      temperature: 0.9
      max_tokens: 2000
      reasoning_depth: "deep"
      use_cache: false
      allow_reflection: true
      max_iterations: 3
      description: "深度思考模式，适用于复杂问题"
    
    creative:
      temperature: 1.2
      max_tokens: 1500
      reasoning_depth: "medium"
      top_p: 0.95
      frequency_penalty: 0.5
      use_cache: false
      description: "创意生成模式，适用于写作和创意"
"""
    return ThinkingConfig.from_yaml(yaml_content)


def analyze_task_from_text(text: str) -> TaskFeatures:
    """从文本分析任务特征
    
    Args:
        text: 任务描述文本
        
    Returns:
        任务特征
    """
    # 简单的关键词匹配（实际应用中可以使用更复杂的NLP）
    text_lower = text.lower()
    
    # 检测任务类型
    task_type = TaskType.QUICK_ANSWER  # 默认
    
    if any(word in text_lower for word in ["代码", "编程", "函数", "类", "def ", "class "]):
        task_type = TaskType.CODE_GENERATION
    elif any(word in text_lower for word in ["错误", "bug", "调试", "修复", "问题"]):
        task_type = TaskType.DEBUGGING
    elif any(word in text_lower for word in ["写作", "故事", "创意", "诗歌", "文章"]):
        task_type = TaskType.CREATIVE_WRITING
    elif any(word in text_lower for word in ["数据", "分析", "统计", "图表", "报告"]):
        task_type = TaskType.DATA_ANALYSIS
    elif any(word in text_lower for word in ["研究", "调查", "探索", "深入"]):
        task_type = TaskType.RESEARCH
    elif any(word in text_lower for word in ["计划", "规划", "安排", "日程"]):
        task_type = TaskType.PLANNING
    
    # 估算复杂度（基于文本长度和关键词）
    complexity = 0.5
    if len(text) > 500:
        complexity = 0.8
    elif len(text) > 200:
        complexity = 0.6
    elif len(text) < 50:
        complexity = 0.3
    
    # 检测紧急度关键词
    urgency = 0.5
    if any(word in text_lower for word in ["紧急", "尽快", "马上", "立刻", "急", "urgent"]):
        urgency = 0.9
    elif any(word in text_lower for word in ["不急", "慢慢", "有空", "不着急"]):
        urgency = 0.2
    
    return TaskFeatures(
        task_type=task_type,
        complexity=complexity,
        urgency=urgency,
        domain="general"
    )


def create_thinking_mode_system(config_yaml: Optional[str] = None) -> Tuple[ThinkingConfig, ThinkingModeSelector, ThinkingModeApplicator]:
    """创建完整的思考模式系统
    
    Args:
        config_yaml: 可选的自定义YAML配置
        
    Returns:
        (配置, 选择器, 应用器) 三元组
    """
    # 创建配置
    if config_yaml:
        config = ThinkingConfig.from_yaml(config_yaml)
    else:
        config = create_default_thinking_config()
    
    # 验证配置
    errors = config.validate()
    if errors:
        raise ValueError(f"配置验证失败: {', '.join(errors)}")
    
    # 创建选择器和应用器
    selector = ThinkingModeSelector(config)
    applicator = ThinkingModeApplicator(config)
    
    return config, selector, applicator


# ============================================================================
# 模拟模型实现（用于演示）
# ============================================================================

class MockModel:
    """模拟AI模型，用于演示"""
    
    def __init__(self, name: str = "mock-model"):
        self.name = name
        self.call_count = 0
    
    def generate(self, prompt: str, **kwargs) -> str:
        """同步生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 模型参数
            
        Returns:
            生成的文本
        """
        self.call_count += 1
        
        # 模拟处理时间（基于temperature等参数）
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1000)
        
        time.sleep(0.05 * temperature)  # 模拟处理延迟
        
        # 基于参数生成不同的响应
        if temperature < 0.5:
            # 低temperature：确定性的响应
            response = f"[确定性响应] 这是一个针对提示的确定回答。温度: {temperature}, 最大token数: {max_tokens}"
        elif temperature < 1.0:
            # 中等temperature：平衡的响应
            response = f"[平衡响应] 这是对您提示的平衡回答。我考虑了多个角度。温度: {temperature}, 最大token数: {max_tokens}"
        else:
            # 高temperature：创造性的响应
            response = f"[创意响应] 基于您的提示，我有一个创造性的想法！温度: {temperature} 让我更有创造力。最大token数: {max_tokens}"
        
        # 根据max_tokens截断（模拟）
        if len(response) > max_tokens:
            response = response[:max_tokens] + "...[截断]"
        
        return f"模型 '{self.name}' 的响应 (调用#{self.call_count}):\n{response}"
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        """异步生成文本
        
        Args:
            prompt: 输入提示
            **kwargs: 模型参数
            
        Returns:
            生成的文本
        """
        # 模拟异步延迟
        await asyncio.sleep(0.03)
        return self.generate(prompt, **kwargs)


# ============================================================================
# 演示函数
# ============================================================================

def demo_basic_configuration():
    """演示基本配置功能"""
    print("=" * 80)
    print("演示1: 基本配置功能")
    print("=" * 80)
    
    # 创建默认配置
    config = create_default_thinking_config()
    
    print("1. 默认思考模式配置:")
    print(config.to_yaml())
    
    print("\n2. 配置验证:")
    errors = config.validate()
    if errors:
        print(f"  发现错误: {errors}")
    else:
        print("  配置验证通过!")
    
    print("\n3. 获取模式配置示例:")
    for mode_name in config.modes.keys():
        mode_config = config.get_mode_config(mode_name)
        print(f"  - {mode_name}: temperature={mode_config.get('temperature')}, "
              f"max_tokens={mode_config.get('max_tokens')}")
    
    return config


def demo_task_analysis():
    """演示任务分析功能"""
    print("\n" + "=" * 80)
    print("演示2: 任务分析功能")
    print("=" * 80)
    
    # 测试任务文本
    test_tasks = [
        "帮我写一个Python函数，计算斐波那契数列",
        "紧急！系统出现错误，需要立刻调试",
        "写一个关于人工智能的短篇故事",
        "分析一下最近三个月的销售数据",
        "什么是机器学习？简单解释一下"
    ]
    
    for i, task_text in enumerate(test_tasks, 1):
        features = analyze_task_from_text(task_text)
        print(f"\n任务{i}: '{task_text[:50]}...'")
        print(f"  任务类型: {features.task_type.value}")
        print(f"  复杂度: {features.complexity:.2f}")
        print(f"  紧急度: {features.urgency:.2f}")
        
        # 验证
        errors = features.validate()
        if errors:
            print(f"  验证错误: {errors}")


def demo_mode_selection():
    """演示模式选择功能"""
    print("\n" + "=" * 80)
    print("演示3: 模式选择功能")
    print("=" * 80)
    
    # 创建完整系统
    config, selector, applicator = create_thinking_mode_system()
    
    # 测试任务
    test_features = [
        TaskFeatures(TaskType.CODE_GENERATION, complexity=0.6, urgency=0.3),
        TaskFeatures(TaskType.DEBUGGING, complexity=0.8, urgency=0.9),
        TaskFeatures(TaskType.CREATIVE_WRITING, complexity=0.5, urgency=0.4),
        TaskFeatures(TaskType.QUICK_ANSWER, complexity=0.2, urgency=0.7),
    ]
    
    for i, features in enumerate(test_features, 1):
        print(f"\n任务{i}特征:")
        print(f"  类型: {features.task_type.value}, 复杂度: {features.complexity:.2f}, 紧急度: {features.urgency:.2f}")
        
        # 选择模式
        try:
            mode_name = selector.select_mode(features)
            mode_name_conf, confidence = selector.select_mode_with_confidence(features)
            
            print(f"  选择模式: {mode_name}")
            print(f"  带置信度: {mode_name_conf} (置信度: {confidence:.2f})")
            print(f"  模式描述: {selector.get_mode_description(mode_name)}")
            
            # 解释选择过程
            explanation = selector.explain_selection(features)
            print(f"  应用规则数: {len(explanation['applied_rules'])}")
            
        except Exception as e:
            print(f"  模式选择失败: {e}")


def demo_mode_application():
    """演示模式应用功能"""
    print("\n" + "=" * 80)
    print("演示4: 模式应用功能")
    print("=" * 80)
    
    # 创建完整系统
    config, selector, applicator = create_thinking_mode_system()
    
    # 创建模拟模型
    mock_model = MockModel("demo-model")
    
    # 测试任务
    task_text = "请解释一下什么是深度学习"
    features = analyze_task_from_text(task_text)
    
    print(f"任务: {task_text}")
    print(f"分析特征: 类型={features.task_type.value}, 复杂度={features.complexity:.2f}, 紧急度={features.urgency:.2f}")
    
    # 选择模式
    mode_name = selector.select_mode(features)
    print(f"选择模式: {mode_name}")
    
    # 应用模式到模型调用
    print("\n应用思考模式到模型调用:")
    try:
        result = applicator.apply_to_model_call(
            mode_name=mode_name,
            model_call_func=mock_model.generate,
            prompt=task_text
        )
        print(f"结果: {result[:100]}...")
    except Exception as e:
        print(f"应用失败: {e}")
    
    # 测试多次调用以展示缓存
    print("\n测试缓存功能（相同调用第二次）:")
    try:
        result2 = applicator.apply_to_model_call(
            mode_name=mode_name,
            model_call_func=mock_model.generate,
            prompt=task_text
        )
        print(f"结果: {result2[:100]}...")
        print(f"模型调用次数: {mock_model.call_count} (如果缓存生效，应该只有1次)")
    except Exception as e:
        print(f"应用失败: {e}")
    
    # 显示性能统计
    print("\n性能统计:")
    stats = applicator.get_performance_stats()
    for mode_name, mode_stats in stats.items():
        if mode_stats["call_count"] > 0:
            print(f"  {mode_name}: 调用次数={mode_stats['call_count']}, "
                  f"平均时间={mode_stats.get('average_time', 0):.4f}s, "
                  f"成功率={mode_stats.get('success_rate', 0):.2%}")


async def demo_async_application():
    """演示异步模式应用功能"""
    print("\n" + "=" * 80)
    print("演示5: 异步模式应用功能")
    print("=" * 80)
    
    # 创建完整系统
    config, selector, applicator = create_thinking_mode_system()
    
    # 创建模拟模型
    mock_model = MockModel("async-model")
    
    # 测试任务
    task_text = "异步请求：请写一个Python异步函数示例"
    features = analyze_task_from_text(task_text)
    
    print(f"异步任务: {task_text}")
    print(f"分析特征: 类型={features.task_type.value}, 复杂度={features.complexity:.2f}, 紧急度={features.urgency:.2f}")
    
    # 选择模式
    mode_name = selector.select_mode(features)
    print(f"选择模式: {mode_name}")
    
    # 异步应用模式
    print("\n异步应用思考模式:")
    try:
        result = await applicator.apply_to_model_call_async(
            mode_name=mode_name,
            model_call_func=mock_model.generate_async,
            prompt=task_text
        )
        print(f"异步结果: {result[:100]}...")
    except Exception as e:
        print(f"异步应用失败: {e}")


def demo_custom_rules():
    """演示自定义规则功能"""
    print("\n" + "=" * 80)
    print("演示6: 自定义规则功能")
    print("=" * 80)
    
    # 创建完整系统
    config, selector, applicator = create_thinking_mode_system()
    
    # 添加自定义规则：基于特定领域选择模式
    def domain_specific_rule(features: TaskFeatures) -> Optional[str]:
        """基于领域的自定义规则"""
        if features.domain == "scientific":
            # 科学领域任务使用深度模式
            return "deep"
        elif features.domain == "creative":
            # 创意领域任务使用创意模式
            return "creative"
        return None
    
    selector.add_custom_rule(domain_specific_rule)
    
    # 添加自定义规则：基于时间选择模式
    def time_based_rule(features: TaskFeatures) -> Optional[str]:
        """基于时间的自定义规则（模拟）"""
        current_hour = time.localtime().tm_hour
        if 0 <= current_hour < 6:  # 凌晨
            # 凌晨时段使用快速模式（假设用户需要快速回答）
            return "fast"
        return None
    
    selector.add_custom_rule(time_based_rule)
    
    # 测试自定义规则
    test_features = TaskFeatures(
        task_type=TaskType.RESEARCH,
        complexity=0.6,
        urgency=0.5,
        domain="scientific"  # 触发领域规则
    )
    
    print("测试自定义规则:")
    print(f"任务特征: 领域={test_features.domain}, 类型={test_features.task_type.value}")
    
    # 解释选择过程
    explanation = selector.explain_selection(test_features)
    print(f"\n选择解释:")
    print(f"  最终选择: {explanation['final_selection']}")
    print(f"  置信度: {explanation['confidence']}")
    print(f"  应用规则:")
    
    for rule in explanation['applied_rules']:
        rule_type = rule['rule_type']
        if rule_type == 'custom':
            print(f"    - 自定义规则: 建议模式={rule.get('suggested_mode', 'N/A')}")
        else:
            print(f"    - {rule_type}: {rule.get('reason', 'N/A')}")


def demo_extended_configuration():
    """演示扩展配置功能"""
    print("\n" + "=" * 80)
    print("演示7: 扩展配置功能")
    print("=" * 80)
    
    # 创建自定义YAML配置
    custom_yaml = """
thinking:
  modes:
    ultra_fast:
      temperature: 0.1
      max_tokens: 300
      reasoning_depth: "shallow"
      use_cache: true
      description: "超快速模式，极低延迟"
    
    analytical:
      temperature: 0.5
      max_tokens: 1500
      reasoning_depth: "deep"
      top_p: 0.9
      frequency_penalty: 0.1
      allow_reflection: true
      max_iterations: 2
      description: "分析模式，适合逻辑分析"
    
    storytelling:
      temperature: 1.5
      max_tokens: 2000
      reasoning_depth: "medium"
      top_p: 0.98
      frequency_penalty: 0.3
      presence_penalty: 0.2
      description: "讲故事模式，适合叙事创作"
"""
    
    print("自定义YAML配置:")
    print(custom_yaml)
    
    # 从自定义YAML创建配置
    config = ThinkingConfig.from_yaml(custom_yaml)
    
    print("\n配置验证:")
    errors = config.validate()
    if errors:
        print(f"  发现错误: {errors}")
    else:
        print("  配置验证通过!")
    
    print("\n可用模式:")
    for mode_name in config.modes.keys():
        mode_config = config.get_mode_config(mode_name)
        desc = mode_config.get('description', '无描述')
        print(f"  - {mode_name}: {desc}")
    
    # 测试新配置
    selector = ThinkingModeSelector(config)
    
    # 添加新的任务类型映射
    selector.add_type_mapping(TaskType.CODE_GENERATION, ThinkingMode("analytical"))
    
    # 测试选择
    features = TaskFeatures(TaskType.CODE_GENERATION, complexity=0.7, urgency=0.3)
    mode_name = selector.select_mode(features)
    
    print(f"\n测试新配置选择:")
    print(f"  任务: {features.task_type.value}, 复杂度: {features.complexity}")
    print(f"  选择模式: {mode_name}")
    print(f"  模式描述: {selector.get_mode_description(mode_name)}")


# ============================================================================
# 测试函数
# ============================================================================

def run_tests():
    """运行单元测试"""
    import unittest
    
    class TestThinkingPatternSupport(unittest.TestCase):
        """思考模式支持测试类"""
        
        def test_thinking_config_creation(self):
            """测试思考模式配置创建"""
            config = create_default_thinking_config()
            self.assertIsInstance(config, ThinkingConfig)
            self.assertIn("fast", config.modes)
            self.assertIn("balanced", config.modes)
            self.assertIn("deep", config.modes)
            self.assertIn("creative", config.modes)
        
        def test_config_validation(self):
            """测试配置验证"""
            config = create_default_thinking_config()
            errors = config.validate()
            self.assertEqual(len(errors), 0)
        
        def test_invalid_config_validation(self):
            """测试无效配置验证"""
            invalid_yaml = """
thinking:
  modes:
    invalid_mode:
      temperature: 2.5  # 超出范围
      max_tokens: -100  # 负数
            """
            
            config = ThinkingConfig.from_yaml(invalid_yaml)
            errors = config.validate()
            self.assertGreater(len(errors), 0)
        
        def test_task_features_validation(self):
            """测试任务特征验证"""
            # 有效特征
            features = TaskFeatures(TaskType.CODE_GENERATION, complexity=0.5, urgency=0.5)
            errors = features.validate()
            self.assertEqual(len(errors), 0)
            
            # 无效特征（复杂度超出范围）
            features_invalid = TaskFeatures(TaskType.CODE_GENERATION, complexity=1.5, urgency=0.5)
            errors = features_invalid.validate()
            self.assertGreater(len(errors), 0)
        
        def test_mode_selection(self):
            """测试模式选择"""
            config = create_default_thinking_config()
            selector = ThinkingModeSelector(config)
            
            # 测试基于任务类型的选择
            features = TaskFeatures(TaskType.DEBUGGING, complexity=0.5, urgency=0.5)
            mode_name = selector.select_mode(features)
            self.assertEqual(mode_name, "deep")
            
            # 测试基于紧急度的覆盖
            features_urgent = TaskFeatures(TaskType.DEBUGGING, complexity=0.5, urgency=0.9)
            mode_name_urgent = selector.select_mode(features_urgent)
            self.assertEqual(mode_name_urgent, "fast")
        
        def test_mode_selection_with_confidence(self):
            """测试带置信度的模式选择"""
            config = create_default_thinking_config()
            selector = ThinkingModeSelector(config)
            
            features = TaskFeatures(TaskType.CODE_GENERATION, complexity=0.5, urgency=0.5)
            mode_name, confidence = selector.select_mode_with_confidence(features)
            
            self.assertIsInstance(mode_name, str)
            self.assertIsInstance(confidence, float)
            self.assertGreaterEqual(confidence, 0.1)
            self.assertLessEqual(confidence, 1.0)
        
        def test_explain_selection(self):
            """测试选择解释"""
            config = create_default_thinking_config()
            selector = ThinkingModeSelector(config)
            
            features = TaskFeatures(TaskType.CREATIVE_WRITING, complexity=0.6, urgency=0.3)
            explanation = selector.explain_selection(features)
            
            self.assertIn("task_features", explanation)
            self.assertIn("final_selection", explanation)
            self.assertIn("applied_rules", explanation)
            self.assertIn("confidence", explanation)
        
        def test_thinking_mode_applicator(self):
            """测试思考模式应用器"""
            config = create_default_thinking_config()
            applicator = ThinkingModeApplicator(config)
            
            # 模拟模型函数
            def mock_model(prompt: str, **kwargs):
                return f"模拟响应: {prompt[:20]}..."
            
            # 测试应用
            result = applicator.apply_to_model_call(
                mode_name="fast",
                model_call_func=mock_model,
                prompt="测试提示"
            )
            
            self.assertIsInstance(result, str)
            self.assertIn("模拟响应", result)
        
        def test_performance_stats(self):
            """测试性能统计"""
            config = create_default_thinking_config()
            applicator = ThinkingModeApplicator(config)
            
            # 模拟几次调用
            def mock_model(prompt: str, **kwargs):
                return "响应"
            
            for _ in range(3):
                try:
                    applicator.apply_to_model_call(
                        mode_name="balanced",
                        model_call_func=mock_model,
                        prompt="测试"
                    )
                except:
                    pass
            
            stats = applicator.get_performance_stats()
            self.assertIn("balanced", stats)
            self.assertGreaterEqual(stats["balanced"]["call_count"], 0)
        
        def test_analyze_task_from_text(self):
            """测试从文本分析任务"""
            features = analyze_task_from_text("写一个Python函数")
            self.assertIsInstance(features, TaskFeatures)
            self.assertEqual(features.task_type, TaskType.CODE_GENERATION)
        
        def test_create_thinking_mode_system(self):
            """测试创建完整思考模式系统"""
            config, selector, applicator = create_thinking_mode_system()
            
            self.assertIsInstance(config, ThinkingConfig)
            self.assertIsInstance(selector, ThinkingModeSelector)
            self.assertIsInstance(applicator, ThinkingModeApplicator)
    
    # 运行测试
    print("=" * 80)
    print("运行单元测试")
    print("=" * 80)
    
    # 创建测试套件
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestThinkingPatternSupport)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    print("=" * 80)
    print("思考模式支持演示代码")
    print("=" * 80)
    print()
    
    # 运行演示
    config = demo_basic_configuration()
    demo_task_analysis()
    demo_mode_selection()
    demo_mode_application()
    await demo_async_application()
    demo_custom_rules()
    demo_extended_configuration()
    
    print("\n" + "=" * 80)
    print("演示完成!")
    print("=" * 80)
    
    # 询问是否运行测试
    response = input("\n是否运行单元测试? (y/n): ").strip().lower()
    if response == 'y':
        test_result = run_tests()
        
        # 统计测试结果
        print("\n" + "=" * 80)
        print("测试结果统计")
        print("=" * 80)
        print(f"运行测试数: {test_result.testsRun}")
        print(f"通过测试数: {test_result.testsRun - len(test_result.failures) - len(test_result.errors)}")
        print(f"失败测试数: {len(test_result.failures)}")
        print(f"错误测试数: {len(test_result.errors)}")
        
        if test_result.wasSuccessful():
            print("\n🎉 所有测试通过!")
        else:
            print("\n⚠️  有测试失败或错误")
            
            if test_result.failures:
                print("\n失败详情:")
                for test, traceback in test_result.failures[:3]:  # 显示前3个失败
                    print(f"- {test}: {traceback.splitlines()[-1]}")
            
            if test_result.errors:
                print("\n错误详情:")
                for test, traceback in test_result.errors[:3]:  # 显示前3个错误
                    print(f"- {test}: {traceback.splitlines()[-1]}")
    else:
        print("跳过单元测试")
    
    print("\n" + "=" * 80)
    print("思考模式支持演示代码执行完成")
    print("=" * 80)


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行主函数
    asyncio.run(main())