#!/usr/bin/env python3
# 教育代码说明：本文件为AI Agent架构师训练营课堂演示代码，包含详细注释用于教学目的
# Educational code note: This file contains detailed comments for teaching purposes in AI Agent Architect Training Camp
"""
Day 2 Lesson 7: RunnableConfig运行时配置 - 课堂演示代码

本文件演示运行时配置系统的完整设计与实现，包含四个部分：
1. 配置系统架构模拟 - 三层配置结构模拟和优先级演示
2. 配置合并状态机实现 - 配置合并逻辑和边界处理
3. 可配置Agent模块化设计 - 配置驱动的Agent行为控制
4. 配置系统架构分析 - 设计模式和架构决策分析

学习目标：
- 掌握运行时配置的三层继承结构（全局→会话→请求）
- 理解配置合并的优先级规则和None值处理
- 实现配置验证、安全回退和默认值应用
- 设计配置驱动的系统架构

版本: 1.0
作者: DeerFlow架构师训练营
日期: 2024年3月26日
"""

import json
import time
from typing import TypedDict, Optional, List, Dict, Any, TypeVar, Union
from enum import Enum
from dataclasses import dataclass
from functools import wraps
import argparse

# ============================================================================
# 第一部分：配置系统架构模拟
# ============================================================================

print("=" * 60)
print("第一部分：配置系统架构模拟")
print("=" * 60)
print()


class ModelType(Enum):
    """模型类型枚举"""

    GPT4 = "gpt-4"
    GPT35 = "gpt-3.5-turbo"
    CLAUDE = "claude-3"
    LOCAL = "local"


# 定义三层配置结构
class ExecutionConfig(TypedDict, total=False):
    """执行控制配置"""

    max_concurrency: Optional[int]  # 最大并发数
    timeout: Optional[float]  # 超时时间(秒)
    retry_count: Optional[int]  # 重试次数
    retry_delay: Optional[float]  # 重试延迟(秒)


class ModelConfig(TypedDict, total=False):
    """模型配置"""

    model_type: Optional[ModelType]  # 模型类型
    temperature: Optional[float]  # 温度参数(0.0-2.0)
    max_tokens: Optional[int]  # 最大token数
    top_p: Optional[float]  # Top-p采样
    frequency_penalty: Optional[float]  # 频率惩罚


class ToolsConfig(TypedDict, total=False):
    """工具配置"""

    allowed_tools: Optional[List[str]]  # 允许的工具列表
    tool_timeout: Optional[float]  # 工具超时时间
    sandbox_enabled: Optional[bool]  # 沙箱是否启用
    max_file_size: Optional[int]  # 最大文件大小(字节)


class DebugConfig(TypedDict, total=False):
    """调试配置"""

    verbose: Optional[bool]  # 详细日志
    callbacks: Optional[List]  # 回调函数列表
    log_level: Optional[str]  # 日志级别
    trace_id: Optional[str]  # 跟踪ID


class RunnableConfig(TypedDict, total=False):
    """运行时配置模板 - 三层配置结构"""

    # 1. 执行控制配置
    execution: Optional[ExecutionConfig]

    # 2. 模型配置
    model: Optional[ModelConfig]

    # 3. 工具配置
    tools: Optional[ToolsConfig]

    # 4. 调试配置
    debug: Optional[DebugConfig]

    # 5. 业务特定配置
    business: Optional[Dict[str, Any]]


def simulate_three_layer_config_system():
    """模拟三层配置系统架构"""
    print("🎯 模拟三层配置系统架构")
    print()

    # 1. 全局配置 - 应用默认值，安全基线
    global_config: RunnableConfig = {
        "execution": {"timeout": 30, "retry_count": 3},
        "model": {"temperature": 0.7, "model_type": ModelType.GPT35},
        "debug": {"verbose": False, "log_level": "INFO"},
        "business": {"max_documents": 10},
    }

    print("1. 全局配置 (Global Config) - 应用默认值，安全基线")
    print(f"   {json.dumps(global_config, indent=2, default=str)}")
    print()

    # 2. 会话配置 - 用户偏好，环境设置
    session_config: RunnableConfig = {
        "execution": {"timeout": 60},  # 覆盖全局timeout
        "model": {"model_type": ModelType.GPT4},  # 升级模型
        "debug": None,  # 不覆盖debug配置
        "business": {"user_preference": "high_quality"},
    }

    print("2. 会话配置 (Session Config) - 用户偏好，环境设置")
    print(f"   {json.dumps(session_config, indent=2, default=str)}")
    print()

    # 3. 请求配置 - 具体任务参数，临时调整
    request_config: RunnableConfig = {
        "model": {"temperature": 1.2},  # 提高创造力
        "debug": {"verbose": True, "trace_id": "req_123"},  # 添加trace_id
        "business": {"urgent": True},
    }

    print("3. 请求配置 (Request Config) - 具体任务参数，临时调整")
    print(f"   {json.dumps(request_config, indent=2, default=str)}")
    print()

    # 4. 配置优先级规则演示
    print("📊 配置优先级规则演示: 请求 > 会话 > 全局")
    print()

    # 预期合并结果：
    # - execution.timeout: 60 (会话覆盖全局)
    # - model.temperature: 1.2 (请求覆盖全局的0.7)
    # - model.model_type: GPT4 (会话覆盖全局的GPT35)
    # - debug.verbose: True (请求添加，会话为None不覆盖)
    # - debug.log_level: INFO (全局值保留)
    # - debug.trace_id: "req_123" (请求添加)
    # - business.max_documents: 10 (全局值保留)
    # - business.user_preference: "high_quality" (会话添加)
    # - business.urgent: True (请求添加)

    print("预期合并结果:")
    print("  - execution.timeout: 60 (会话覆盖全局的30)")
    print("  - model.temperature: 1.2 (请求覆盖全局的0.7)")
    print("  - model.model_type: GPT4 (会话覆盖全局的GPT35)")
    print("  - debug.verbose: True (请求添加，会话为None不覆盖)")
    print("  - debug.log_level: INFO (全局值保留)")
    print("  - debug.trace_id: 'req_123' (请求添加)")
    print("  - business.max_documents: 10 (全局值保留)")
    print("  - business.user_preference: 'high_quality' (会话添加)")
    print("  - business.urgent: True (请求添加)")
    print()

    return global_config, session_config, request_config


# ============================================================================
# 第二部分：配置合并状态机实现
# ============================================================================

print("=" * 60)
print("第二部分：配置合并状态机实现")
print("=" * 60)
print()

T = TypeVar("T")


class ConfigMergeState:
    """配置合并状态机状态"""

    INITIAL = "initial"
    MERGING = "merging"
    VALIDATING = "validating"
    APPLYING_DEFAULTS = "applying_defaults"
    COMPLETED = "completed"
    ERROR = "error"


class ConfigMergeError(Exception):
    """配置合并错误"""

    pass


def merge_configs(base: T, override: T) -> T:
    """
    合并配置，override覆盖base，None值不覆盖

    状态机逻辑：
    1. 检查输入状态
    2. 递归合并字典
    3. 处理None值特殊规则
    4. 返回合并结果
    """
    # 状态转移: INITIAL -> MERGING
    current_state = ConfigMergeState.MERGING

    try:
        # 边界情况处理
        if base is None:
            return override

        if override is None:
            return base

        # 处理字典类型配置 - 递归合并
        if isinstance(base, dict) and isinstance(override, dict):
            result = base.copy()

            for key, value in override.items():
                # 关键规则: None值不覆盖
                if value is not None:
                    if (
                        key in result
                        and isinstance(result[key], dict)
                        and isinstance(value, dict)
                    ):
                        # 递归合并嵌套字典
                        result[key] = merge_configs(result[key], value)
                    else:
                        result[key] = value
            return result

        # 处理其他类型
        return override if override is not None else base

    except Exception as e:
        # 状态转移: MERGING -> ERROR
        raise ConfigMergeError(f"配置合并失败: {str(e)}") from e


def merge_multiple_configs(*configs: T) -> T:
    """
    合并多个配置，优先级从左到右递增

    参数:
        *configs: 多个配置，优先级从左到右递增（最左最低，最右最高）

    返回:
        合并后的配置
    """
    print("🔄 合并多个配置（优先级从左到右递增）")

    if not configs:
        return None

    result = None
    for i, config in enumerate(configs):
        if config is not None:
            print(
                f"  第{i + 1}层配置: {json.dumps(config, indent=2, default=str)[:100]}..."
            )
            result = merge_configs(result, config)

    print(f"  最终合并结果: {json.dumps(result, indent=2, default=str)[:150]}...")
    print()
    return result


def demonstrate_config_merge_state_machine():
    """演示配置合并状态机"""
    print("🎯 演示配置合并状态机")
    print()

    # 创建测试配置
    config_a = {
        "execution": {"timeout": 30, "retry_count": 3},
        "model": {"temperature": 0.7},
        "debug": {"verbose": False},
    }

    config_b = {
        "execution": {"timeout": 60},  # 覆盖timeout
        "model": None,  # None值不覆盖
        "debug": {"verbose": True, "log_level": "DEBUG"},  # 添加log_level
    }

    config_c = {
        "model": {
            "temperature": 1.2,
            "max_tokens": 2000,
        },  # 覆盖temperature，添加max_tokens
        "business": {"urgent": True},
    }

    print("配置A (基础配置):")
    print(f"  {json.dumps(config_a, indent=2)}")
    print()

    print("配置B (覆盖配置):")
    print(f"  {json.dumps(config_b, indent=2)}")
    print()

    print("配置C (最高优先级配置):")
    print(f"  {json.dumps(config_c, indent=2)}")
    print()

    # 演示合并过程
    print("合并过程分析:")
    print("  1. config_a作为基础")
    print("  2. config_b覆盖config_a:")
    print("     - execution.timeout: 60 (覆盖30)")
    print("     - model: None (不覆盖，保留config_a的model)")
    print("     - debug.verbose: True (覆盖False)")
    print("     - debug.log_level: DEBUG (新增)")
    print("  3. config_c覆盖前两者:")
    print("     - model.temperature: 1.2 (覆盖0.7)")
    print("     - model.max_tokens: 2000 (新增)")
    print("     - business.urgent: True (新增)")
    print()

    # 执行合并
    merged = merge_multiple_configs(config_a, config_b, config_c)

    print("📋 合并结果验证:")
    expected = {
        "execution": {"timeout": 60, "retry_count": 3},
        "model": {"temperature": 1.2, "max_tokens": 2000},
        "debug": {"verbose": True, "log_level": "DEBUG"},
        "business": {"urgent": True},
    }

    print(f"  预期结果: {json.dumps(expected, indent=2)}")
    print(f"  实际结果: {json.dumps(merged, indent=2)}")
    print(f"  匹配结果: {merged == expected}")
    print()

    # 演示边界情况
    print("🚨 边界情况演示:")

    # 情况1: None值不覆盖
    base = {"key": "value"}
    override = {"key": None}
    result = merge_configs(base, override)
    print(f"  1. None值不覆盖: merge({{'key': 'value'}}, {{'key': None}}) = {result}")

    # 情况2: 嵌套字典递归合并
    base = {"nested": {"a": 1, "b": 2}}
    override = {"nested": {"b": 20, "c": 3}}
    result = merge_configs(base, override)
    print(
        f"  2. 嵌套字典递归合并: merge({{'nested': {{'a':1, 'b':2}}}}, {{'nested': {{'b':20, 'c':3}}}})"
    )
    print(f"     结果: {result}")

    # 情况3: 类型不一致覆盖
    base = {"key": {"nested": "value"}}
    override = {"key": "string_value"}
    result = merge_configs(base, override)
    print(
        f"  3. 类型不一致覆盖: merge({{'key': {{'nested':'value'}}}}, {{'key': 'string_value'}})"
    )
    print(f"     结果: {result}")
    print()


# ============================================================================
# 第三部分：可配置Agent模块化设计
# ============================================================================

print("=" * 60)
print("第三部分：可配置Agent模块化设计")
print("=" * 60)
print()


class ConfigValidationError(Exception):
    """配置验证错误"""

    pass


def validate_config(config: RunnableConfig) -> tuple[bool, Optional[str]]:
    """
    验证配置合法性

    验证规则:
    1. 执行配置: timeout在1-3600秒之间, retry_count在0-10之间
    2. 模型配置: temperature在0.0-2.0之间, max_tokens在1-100000之间
    3. 工具配置: max_file_size在0-100MB之间
    """
    try:
        # 1. 验证执行配置
        if execution := config.get("execution"):
            if timeout := execution.get("timeout"):
                if not 0 < timeout <= 3600:  # 1秒到1小时
                    raise ConfigValidationError(
                        f"超时时间必须在1-3600秒之间: {timeout}"
                    )

            if retry_count := execution.get("retry_count"):
                if retry_count < 0 or retry_count > 10:
                    raise ConfigValidationError(
                        f"重试次数必须在0-10之间: {retry_count}"
                    )

        # 2. 验证模型配置
        if model := config.get("model"):
            if temperature := model.get("temperature"):
                if not 0.0 <= temperature <= 2.0:
                    raise ConfigValidationError(
                        f"温度参数必须在0.0-2.0之间: {temperature}"
                    )

            if max_tokens := model.get("max_tokens"):
                if max_tokens < 1 or max_tokens > 100000:
                    raise ConfigValidationError(
                        f"最大token数必须在1-100000之间: {max_tokens}"
                    )

        # 3. 验证工具配置
        if tools := config.get("tools"):
            if max_file_size := tools.get("max_file_size"):
                if max_file_size < 0 or max_file_size > 100 * 1024 * 1024:  # 100MB
                    raise ConfigValidationError(
                        f"最大文件大小必须在0-100MB之间: {max_file_size}"
                    )

        return True, None

    except ConfigValidationError as e:
        return False, str(e)


class ConfigResolver:
    """配置解析器 - 负责配置合并、验证和默认值应用"""

    def __init__(self, global_config: RunnableConfig):
        self.global_config = global_config
        self._defaults = self._build_defaults()

    def _build_defaults(self) -> RunnableConfig:
        """构建默认配置"""
        return {
            "execution": {"timeout": 30, "retry_count": 3},
            "model": {"temperature": 0.7, "model_type": ModelType.GPT35},
            "debug": {"verbose": False, "log_level": "INFO"},
        }

    def resolve(
        self,
        session_config: Optional[RunnableConfig] = None,
        request_config: Optional[RunnableConfig] = None,
    ) -> RunnableConfig:
        """
        解析最终配置

        流程:
        1. 合并三层配置（全局→会话→请求）
        2. 验证配置合法性
        3. 安全回退到全局默认值（验证失败时）
        4. 应用默认值（填充缺失的必需字段）
        """
        print("🔧 配置解析流程:")
        print(
            f"  1. 全局配置: {json.dumps(self.global_config, indent=2, default=str)[:80]}..."
        )
        print(
            f"  2. 会话配置: {json.dumps(session_config, indent=2, default=str)[:80] if session_config else 'None'}"
        )
        print(
            f"  3. 请求配置: {json.dumps(request_config, indent=2, default=str)[:80] if request_config else 'None'}"
        )
        print()

        # 1. 合并配置
        config = merge_multiple_configs(
            self.global_config, session_config or {}, request_config or {}
        )

        print(f"  合并后配置: {json.dumps(config, indent=2, default=str)[:100]}...")
        print()

        # 2. 验证配置
        is_valid, error = validate_config(config)
        if not is_valid:
            print(f"  ⚠️  配置验证失败: {error}")
            print("  🛡️  安全回退到全局默认值")

            # 安全回退：使用全局默认值
            config = self.global_config.copy()

            # 记录错误但不中断
            if "debug" not in config:
                config["debug"] = {}
            config["debug"]["last_error"] = error

        # 3. 应用默认值
        config = merge_multiple_configs(self._defaults, config)

        print(f"  ✅ 最终配置: {json.dumps(config, indent=2, default=str)[:150]}...")
        print()

        return config


class ConfigurableAgent:
    """可配置Agent - 演示配置驱动的系统设计"""

    def __init__(self, name: str, config_resolver: ConfigResolver):
        self.name = name
        self.config_resolver = config_resolver
        self.current_config: Optional[RunnableConfig] = None

    def execute(
        self, task: str, request_config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """
        执行任务，应用运行时配置

        配置驱动行为:
        1. 根据verbose控制日志输出
        2. 根据timeout控制执行时间
        3. 根据model_type选择模型
        4. 根据temperature调整创造性
        """
        # 解析配置
        self.current_config = self.config_resolver.resolve(
            request_config=request_config
        )

        print(f"🤖 Agent '{self.name}' 开始执行任务: {task}")
        print(
            f"   应用配置: {json.dumps(self.current_config, indent=2, default=str)[:100]}..."
        )
        print()

        # 应用配置控制行为
        execution_timeout = self._get_execution_timeout()
        model_type = self._get_model_type()
        temperature = self._get_temperature()
        verbose = self._get_verbose()

        if verbose:
            print(f"  🔍 详细日志:")
            print(f"     - 执行超时: {execution_timeout}秒")
            print(f"     - 模型类型: {model_type}")
            print(f"     - 温度参数: {temperature}")
            print(f"     - 任务内容: {task}")
            print()

        # 模拟任务执行
        result = self._simulate_task_execution(task, execution_timeout)

        if verbose:
            print(f"  ✅ 任务完成: {result}")
            print()

        return result

    def _get_execution_timeout(self) -> float:
        """从配置获取执行超时"""
        if self.current_config and "execution" in self.current_config:
            return self.current_config["execution"].get("timeout", 30)
        return 30

    def _get_model_type(self) -> ModelType:
        """从配置获取模型类型"""
        if self.current_config and "model" in self.current_config:
            model_type = self.current_config["model"].get("model_type")
            if model_type:
                return model_type
        return ModelType.GPT35

    def _get_temperature(self) -> float:
        """从配置获取温度参数"""
        if self.current_config and "model" in self.current_config:
            return self.current_config["model"].get("temperature", 0.7)
        return 0.7

    def _get_verbose(self) -> bool:
        """从配置获取详细日志标志"""
        if self.current_config and "debug" in self.current_config:
            return self.current_config["debug"].get("verbose", False)
        return False

    def _simulate_task_execution(self, task: str, timeout: float) -> Dict[str, Any]:
        """模拟任务执行"""
        import random

        # 模拟执行时间
        execution_time = min(timeout, random.uniform(0.5, timeout * 0.8))
        time.sleep(0.1)  # 模拟短暂延迟

        # 模拟结果（受温度参数影响）
        temperature = self._get_temperature()

        # 温度越高，结果越有创造性（更多变体）
        if temperature < 0.5:
            response = f"标准回答: {task}"
        elif temperature < 1.0:
            response = f"平衡回答: {task} (温度: {temperature})"
        elif temperature < 1.5:
            response = f"创造性回答: {task} (温度: {temperature})"
        else:
            response = f"高度创造性回答: {task} (温度: {temperature})"

        return {
            "success": True,
            "response": response,
            "execution_time": execution_time,
            "model": self._get_model_type().value,
            "temperature": temperature,
        }


def demonstrate_configurable_agent():
    """演示可配置Agent系统"""
    print("🎯 演示可配置Agent系统")
    print()

    # 创建全局配置
    global_config: RunnableConfig = {
        "execution": {"timeout": 30, "retry_count": 3},
        "model": {"temperature": 0.7, "model_type": ModelType.GPT35},
        "debug": {"verbose": False, "log_level": "INFO"},
    }

    # 创建配置解析器
    resolver = ConfigResolver(global_config)

    # 创建可配置Agent
    agent = ConfigurableAgent("翻译助手", resolver)

    # 场景1: 使用默认配置
    print("场景1: 使用默认配置执行任务")
    result1 = agent.execute("将'Hello World'翻译成中文")
    print(f"结果: {json.dumps(result1, indent=2, default=str)}")
    print()

    # 场景2: 使用请求配置（提高温度，启用详细日志）
    print("场景2: 使用请求配置（提高温度，启用详细日志）")
    request_config: RunnableConfig = {
        "model": {"temperature": 1.5},
        "debug": {"verbose": True},
    }
    result2 = agent.execute("将'AI is changing the world'翻译成中文", request_config)
    print(f"结果: {json.dumps(result2, indent=2, default=str)}")
    print()

    # 场景3: 使用无效配置（验证失败，安全回退）
    print("场景3: 使用无效配置（验证失败，安全回退）")
    invalid_config: RunnableConfig = {
        "execution": {"timeout": -1},  # 无效的超时时间
        "model": {"temperature": 3.0},  # 无效的温度参数
    }
    result3 = agent.execute("将'Configuration is important'翻译成中文", invalid_config)
    print(f"结果: {json.dumps(result3, indent=2, default=str)}")
    print()

    # 场景4: 完整三层配置示例
    print("场景4: 完整三层配置示例")

    # 全局配置（已设置）
    # 会话配置（用户偏好）
    session_config: RunnableConfig = {
        "execution": {"timeout": 60},
        "model": {"model_type": ModelType.GPT4},
    }

    # 请求配置（具体任务）
    request_config2: RunnableConfig = {
        "model": {"temperature": 0.9},
        "debug": {"verbose": True, "trace_id": "translation_001"},
    }

    # 创建新的解析器（包含会话配置）
    resolver2 = ConfigResolver(global_config)
    agent2 = ConfigurableAgent("高级翻译助手", resolver2)

    # 模拟配置解析过程
    print("  配置解析过程:")
    final_config = resolver2.resolve(session_config, request_config2)

    # 执行任务
    result4 = agent2.execute(
        "将'Three-layer configuration system'翻译成中文", request_config2
    )
    print(f"结果: {json.dumps(result4, indent=2, default=str)}")
    print()


# ============================================================================
# 第四部分：配置系统架构分析
# ============================================================================

print("=" * 60)
print("第四部分：配置系统架构分析")
print("=" * 60)
print()


def analyze_configuration_architecture():
    """分析配置系统架构"""
    print("🎯 配置系统架构分析")
    print()

    # 1. 设计模式分析
    print("1. 📐 设计模式分析:")
    print()

    patterns = [
        {
            "pattern": "策略模式 (Strategy Pattern)",
            "description": "通过配置选择不同的算法或行为",
            "example": "根据temperature配置选择不同的回答策略",
            "benefit": "行为可配置，无需修改代码",
        },
        {
            "pattern": "工厂模式 (Factory Pattern)",
            "description": "通过配置创建不同类型的对象",
            "example": "根据model_type配置创建不同的模型客户端",
            "benefit": "对象创建可配置，支持热插拔",
        },
        {
            "pattern": "装饰器模式 (Decorator Pattern)",
            "description": "通过配置动态添加功能",
            "example": "根据verbose配置添加日志装饰器",
            "benefit": "功能可配置组合，避免继承爆炸",
        },
        {
            "pattern": "责任链模式 (Chain of Responsibility)",
            "description": "配置在不同层级间传递和覆盖",
            "example": "全局→会话→请求三层配置继承",
            "benefit": "关注点分离，配置粒度可控",
        },
    ]

    for i, p in enumerate(patterns, 1):
        print(f"  {i}. {p['pattern']}")
        print(f"     描述: {p['description']}")
        print(f"     示例: {p['example']}")
        print(f"     优势: {p['benefit']}")
        print()

    # 2. 架构决策分析
    print("2. 🏗️  架构决策分析:")
    print()

    decisions = [
        {
            "decision": "三层配置结构 vs 扁平配置",
            "choice": "三层配置结构（全局→会话→请求）",
            "reason": "支持不同粒度的配置覆盖，符合现实世界的权限模型",
            "tradeoff": "增加了配置合并的复杂性，但提供了更大的灵活性",
        },
        {
            "decision": "None值不覆盖规则",
            "choice": "None值不覆盖已有配置",
            "reason": "允许显式清除配置，同时防止意外覆盖",
            "tradeoff": "需要开发者理解特殊规则，但提供了更精确的控制",
        },
        {
            "decision": "配置验证时机",
            "choice": "合并后验证，失败时安全回退",
            "reason": "确保最终配置始终有效，防止运行时崩溃",
            "tradeoff": "可能掩盖配置错误，但提高了系统健壮性",
        },
        {
            "decision": "配置存储格式",
            "choice": "类型化的字典结构（TypedDict）",
            "reason": "提供类型提示和IDE支持，同时保持灵活性",
            "tradeoff": "需要Python 3.8+，但提高了代码可维护性",
        },
    ]

    for i, d in enumerate(decisions, 1):
        print(f"  {i}. {d['decision']}")
        print(f"     选择: {d['choice']}")
        print(f"     理由: {d['reason']}")
        print(f"     权衡: {d['tradeoff']}")
        print()

    # 3. 性能、安全性和可维护性权衡
    print("3. ⚖️  性能、安全性和可维护性权衡:")
    print()

    tradeoffs = [
        {
            "aspect": "性能",
            "considerations": [
                "配置合并需要递归遍历字典 - O(n)复杂度",
                "配置验证需要检查每个字段 - 额外开销",
                "配置缓存可以优化重复解析",
            ],
            "optimization": "懒加载配置，缓存解析结果，批量验证",
        },
        {
            "aspect": "安全性",
            "considerations": [
                "配置注入攻击风险",
                "敏感配置（如API密钥）需要加密",
                "配置权限控制（谁可以修改什么配置）",
            ],
            "optimization": "配置验证和清理，加密存储，权限审计",
        },
        {
            "aspect": "可维护性",
            "considerations": ["配置项爆炸问题", "配置版本兼容性", "配置文档和示例"],
            "optimization": "配置分组和命名空间，版本迁移工具，自动文档生成",
        },
    ]

    for t in tradeoffs:
        print(f"  📊 {t['aspect']}:")
        for c in t["considerations"]:
            print(f"     • {c}")
        print(f"     💡 优化策略: {t['optimization']}")
        print()

    # 4. 配置反模式和最佳实践对比
    print("4. ⚠️  配置反模式 vs ✅ 最佳实践:")
    print()

    comparisons = [
        {
            "antipattern": "硬编码魔法数字",
            "example": "timeout = 30  # 为什么是30？",
            "best_practice": "提取为配置常量，并添加注释说明原因",
            "example_bp": "TIMEOUT = 30  # 基于网络延迟统计的合理超时",
        },
        {
            "antipattern": "配置项爆炸（扁平化长字典）",
            "example": '{"timeout":30,"retry":3,"model":"gpt4",...}',
            "best_practice": "分层分组配置",
            "example_bp": '{"execution":{"timeout":30,"retry":3},"model":{"type":"gpt4"}}',
        },
        {
            "antipattern": "缺乏验证和回退",
            "example": "直接使用未验证的配置值",
            "best_practice": "验证配置并安全回退到默认值",
            "example_bp": "if timeout <= 0: timeout = DEFAULT_TIMEOUT",
        },
        {
            "antipattern": "配置与代码逻辑耦合",
            "example": "配置检查分散在代码各处",
            "best_practice": "配置集中管理，使用策略模式",
            "example_bp": "AlgorithmFactory根据配置创建算法实例",
        },
    ]

    for i, c in enumerate(comparisons, 1):
        print(f"  {i}. ⚠️  反模式: {c['antipattern']}")
        print(f"       例子: {c['example']}")
        print(f"     ✅ 最佳实践: {c['best_practice']}")
        print(f"       例子: {c['example_bp']}")
        print()


# ============================================================================
# 主程序入口
# ============================================================================


def main():
    """主程序"""
    parser = argparse.ArgumentParser(description="运行时配置系统演示")
    parser.add_argument(
        "--part",
        type=int,
        choices=[1, 2, 3, 4],
        help="运行特定部分 (1=架构模拟, 2=状态机, 3=模块化设计, 4=架构分析)",
    )
    args = parser.parse_args()

    if args.part:
        # 运行特定部分
        parts = {
            1: lambda: (
                simulate_three_layer_config_system(),
                print("\n第一部分完成\n"),
            ),
            2: lambda: (
                demonstrate_config_merge_state_machine(),
                print("\n第二部分完成\n"),
            ),
            3: lambda: (demonstrate_configurable_agent(), print("\n第三部分完成\n")),
            4: lambda: (
                analyze_configuration_architecture(),
                print("\n第四部分完成\n"),
            ),
        }
        parts[args.part]()
    else:
        # 运行全部四个部分
        print("🚀 开始运行时配置系统完整演示")
        print()

        # 第一部分：配置系统架构模拟
        simulate_three_layer_config_system()
        print("\n" + "=" * 60 + "\n")

        # 第二部分：配置合并状态机实现
        demonstrate_config_merge_state_machine()
        print("\n" + "=" * 60 + "\n")

        # 第三部分：可配置Agent模块化设计
        demonstrate_configurable_agent()
        print("\n" + "=" * 60 + "\n")

        # 第四部分：配置系统架构分析
        analyze_configuration_architecture()

        print("=" * 60)
        print("🎉 运行时配置系统演示完成!")
        print("=" * 60)


if __name__ == "__main__":
    main()
