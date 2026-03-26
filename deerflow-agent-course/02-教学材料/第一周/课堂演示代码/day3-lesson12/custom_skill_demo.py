#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 3 Lesson 12: 实战创建自定义技能 (Practical: Creating Custom Skills)
课堂演示代码 - 自定义技能开发与工程化实践

本文件展示了完整的自定义技能开发方案，包含四个部分：
1. 技能缓存机制实现 - 展示缓存设计模式、失效策略、性能优化
2. 技能编排器状态机实现 - 实现技能链执行、错误处理、数据传递
3. 组合技能模块化设计演示 - 展示组合模式、技能协作、复杂功能构建
4. 技能工程化分析与最佳实践 - 分析设计模式、性能监控、生产级优化

教学目标：
- 理解完整技能开发的生命周期和最佳实践
- 掌握技能缓存机制的设计和实现原理
- 了解技能编排器(SkillOrchestrator)的工作机制
- 理解组合技能(Composite Skill)的设计模式

作者：张老师（10年AI系统架构经验，DeerFlow核心贡献者）
版本：v1.0
创建日期：2024年3月27日
"""

import asyncio
import time
import hashlib
import json
import logging
import random
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import OrderedDict
from functools import wraps
import inspect

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("custom_skill.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 第一部分：技能缓存机制实现
# ============================================================================


class CachePolicy(Enum):
    """缓存策略枚举"""

    NO_CACHE = auto()  # 无缓存
    TTL = auto()  # 生存时间
    LRU = auto()  # 最近最少使用
    LFU = auto()  # 最不经常使用
    SIZE_BASED = auto()  # 基于大小


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: Optional[float] = None  # 生存时间（秒），None表示永不过期

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def access(self):
        """访问缓存条目"""
        self.last_accessed = time.time()
        self.access_count += 1

    def get_age(self) -> float:
        """获取条目年龄（秒）"""
        return time.time() - self.created_at


class SkillCache:
    """技能缓存 - 提供统一的缓存管理"""

    def __init__(
        self,
        max_size: int = 1000,
        policy: CachePolicy = CachePolicy.LRU,
        default_ttl: Optional[float] = 300.0,
    ):  # 默认5分钟
        self.max_size = max_size
        self.policy = policy
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lru_order: List[str] = []  # 用于LRU策略
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        logger.info(
            f"技能缓存初始化: max_size={max_size}, policy={policy.name}, default_ttl={default_ttl}"
        )

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]

        # 检查是否过期
        if entry.is_expired():
            self._evict(key)
            self._misses += 1
            return None

        # 更新访问信息
        entry.access()
        self._hits += 1

        # 更新LRU顺序
        if self.policy == CachePolicy.LRU:
            self._update_lru_order(key)

        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None使用默认值

        Returns:
            是否设置成功
        """
        # 检查缓存大小，如果超过限制则清理
        if len(self._cache) >= self.max_size:
            self._evict_according_to_policy()

        # 创建缓存条目
        ttl_to_use = ttl if ttl is not None else self.default_ttl
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl=ttl_to_use,
        )

        self._cache[key] = entry

        # 更新LRU顺序
        if self.policy == CachePolicy.LRU:
            self._update_lru_order(key, is_new=True)

        logger.debug(f"缓存设置: key={key}, ttl={ttl_to_use}")
        return True

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        if key in self._cache:
            del self._cache[key]

            # 从LRU顺序中移除
            if self.policy == CachePolicy.LRU and key in self._lru_order:
                self._lru_order.remove(key)

            logger.debug(f"缓存删除: key={key}")
            return True
        return False

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._lru_order.clear()
        logger.info("缓存已清空")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0

        # 计算过期条目数量
        expired_count = 0
        current_time = time.time()
        for entry in self._cache.values():
            if entry.ttl is not None and current_time - entry.created_at > entry.ttl:
                expired_count += 1

        return {
            "total_entries": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "evictions": self._evictions,
            "expired_entries": expired_count,
            "policy": self.policy.name,
        }

    def _update_lru_order(self, key: str, is_new: bool = False):
        """更新LRU顺序"""
        if key in self._lru_order:
            self._lru_order.remove(key)
        self._lru_order.append(key)

    def _evict_according_to_policy(self):
        """根据策略淘汰缓存条目"""
        if self.policy == CachePolicy.LRU:
            self._evict_lru()
        elif self.policy == CachePolicy.TTL:
            self._evict_expired()
        elif self.policy == CachePolicy.LFU:
            self._evict_lfu()
        elif self.policy == CachePolicy.SIZE_BASED:
            self._evict_oldest()
        else:
            # 默认淘汰最老的条目
            self._evict_oldest()

    def _evict_lru(self):
        """淘汰最近最少使用的条目"""
        if not self._lru_order:
            return

        # 淘汰最久未访问的条目
        lru_key = self._lru_order.pop(0)
        if lru_key in self._cache:
            del self._cache[lru_key]
            self._evictions += 1
            logger.debug(f"LRU淘汰: key={lru_key}")

    def _evict_expired(self):
        """淘汰过期条目"""
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            self._evict(key)

    def _evict_lfu(self):
        """淘汰最不经常使用的条目"""
        if not self._cache:
            return

        # 找到访问次数最少的条目
        lfu_key = min(self._cache.items(), key=lambda x: x[1].access_count)[0]
        self._evict(lfu_key)
        logger.debug(f"LFU淘汰: key={lfu_key}")

    def _evict_oldest(self):
        """淘汰最老的条目"""
        if not self._cache:
            return

        # 找到创建时间最早的条目
        oldest_key = min(self._cache.items(), key=lambda x: x[1].created_at)[0]
        self._evict(oldest_key)
        logger.debug(f"淘汰最老条目: key={oldest_key}")

    def _evict(self, key: str):
        """淘汰指定键的条目"""
        if key in self._cache:
            del self._cache[key]
            if key in self._lru_order:
                self._lru_order.remove(key)
            self._evictions += 1


def cached(
    cache: SkillCache, ttl: Optional[float] = None, key_func: Optional[callable] = None
):
    """
    缓存装饰器 - 为技能方法添加缓存功能

    Args:
        cache: 缓存实例
        ttl: 缓存生存时间
        key_func: 自定义缓存键生成函数
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认使用函数名和参数哈希
                key_parts = [func.__name__, str(args), str(kwargs)]
                cache_key = hashlib.md5(
                    json.dumps(key_parts, sort_keys=True).encode()
                ).hexdigest()

            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {func.__name__}, key={cache_key}")
                return cached_result

            # 执行函数
            result = await func(*args, **kwargs)

            # 缓存结果
            cache.set(cache_key, result, ttl=ttl)
            logger.debug(f"缓存设置: {func.__name__}, key={cache_key}")

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 默认使用函数名和参数哈希
                key_parts = [func.__name__, str(args), str(kwargs)]
                cache_key = hashlib.md5(
                    json.dumps(key_parts, sort_keys=True).encode()
                ).hexdigest()

            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {func.__name__}, key={cache_key}")
                return cached_result

            # 执行函数
            result = func(*args, **kwargs)

            # 缓存结果
            cache.set(cache_key, result, ttl=ttl)
            logger.debug(f"缓存设置: {func.__name__}, key={cache_key}")

            return result

        # 根据函数类型返回相应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# 第二部分：技能编排器状态机实现
# ============================================================================


class SkillExecutionStatus(Enum):
    """技能执行状态枚举"""

    PENDING = auto()  # 等待执行
    RUNNING = auto()  # 执行中
    SUCCESS = auto()  # 执行成功
    FAILED = auto()  # 执行失败
    CANCELLED = auto()  # 已取消
    TIMEOUT = auto()  # 超时


@dataclass
class SkillExecutionContext:
    """技能执行上下文"""

    skill_name: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    status: SkillExecutionStatus = SkillExecutionStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_execution_time(self) -> Optional[float]:
        """获取执行时间（秒）"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "skill_name": self.skill_name,
            "status": self.status.name,
            "execution_time": self.get_execution_time(),
            "success": self.status == SkillExecutionStatus.SUCCESS,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class SkillOrchestrator:
    """技能编排器 - 管理多个技能的协作执行"""

    def __init__(self, registry: Any, max_retries: int = 3, timeout: float = 30.0):
        self.registry = registry
        self.max_retries = max_retries
        self.timeout = timeout
        self.execution_history: List[SkillExecutionContext] = []
        self.current_executions: Dict[str, SkillExecutionContext] = {}
        self.skill_dependencies: Dict[str, List[str]] = {}
        logger.info(f"技能编排器初始化: max_retries={max_retries}, timeout={timeout}")

    async def execute_skill_chain(
        self,
        skill_chain: List[Tuple[str, Dict[str, Any]]],
        execution_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行技能链

        Args:
            skill_chain: 技能链列表，每个元素为(技能名称, 输入数据)
            execution_id: 执行ID，用于跟踪

        Returns:
            执行结果
        """
        if not execution_id:
            execution_id = f"exec_{int(time.time())}_{hashlib.md5(str(skill_chain).encode()).hexdigest()[:8]}"

        logger.info(f"开始执行技能链: id={execution_id}, 技能数量={len(skill_chain)}")

        execution_contexts = []
        final_output = {}

        try:
            for i, (skill_name, input_data) in enumerate(skill_chain):
                # 创建执行上下文
                context = SkillExecutionContext(
                    skill_name=skill_name,
                    input_data=input_data,
                    metadata={
                        "chain_position": i,
                        "total_skills": len(skill_chain),
                        "execution_id": execution_id,
                    },
                )

                execution_contexts.append(context)
                self.current_executions[skill_name] = context

                # 检查技能依赖
                dependencies = self.skill_dependencies.get(skill_name, [])
                for dep_skill in dependencies:
                    if dep_skill not in [
                        ctx.skill_name
                        for ctx in execution_contexts
                        if ctx.status == SkillExecutionStatus.SUCCESS
                    ]:
                        error_msg = (
                            f"技能 '{skill_name}' 依赖的技能 '{dep_skill}' 未成功执行"
                        )
                        logger.error(error_msg)
                        context.status = SkillExecutionStatus.FAILED
                        context.error_message = error_msg
                        context.end_time = time.time()
                        raise ValueError(error_msg)

                # 执行技能（带重试机制）
                success = False
                last_error = None

                for retry in range(self.max_retries + 1):  # 包括首次尝试
                    try:
                        context.start_time = time.time()
                        context.status = SkillExecutionStatus.RUNNING

                        logger.info(
                            f"执行技能: {skill_name} (尝试 {retry + 1}/{self.max_retries + 1})"
                        )

                        # 获取技能实例
                        skill_instance = self.registry.get_skill(skill_name)
                        if not skill_instance:
                            raise ValueError(f"技能 '{skill_name}' 未找到")

                        # 执行技能（支持异步和同步）
                        if asyncio.iscoroutinefunction(skill_instance.execute):
                            result = await asyncio.wait_for(
                                skill_instance.execute(**input_data),
                                timeout=self.timeout,
                            )
                        else:
                            # 同步函数在线程池中执行以避免阻塞
                            loop = asyncio.get_event_loop()
                            result = await loop.run_in_executor(
                                None, lambda: skill_instance.execute(**input_data)
                            )

                        # 检查执行结果
                        if not result.success:
                            raise ValueError(f"技能执行失败: {result.error_message}")

                        # 记录成功
                        context.status = SkillExecutionStatus.SUCCESS
                        context.output_data = result.output
                        context.end_time = time.time()

                        # 将输出传递给下一个技能（如果需要）
                        if i < len(skill_chain) - 1:
                            next_skill_name, next_input = skill_chain[i + 1]
                            # 自动将当前技能输出合并到下一个技能的输入中
                            if isinstance(result.output, dict):
                                next_input.update(result.output)

                        success = True
                        logger.info(
                            f"技能执行成功: {skill_name}, 用时: {context.get_execution_time():.2f}秒"
                        )
                        break

                    except asyncio.TimeoutError:
                        last_error = f"技能执行超时: {skill_name}"
                        logger.warning(f"{last_error} (尝试 {retry + 1})")
                        context.error_message = last_error
                        context.status = SkillExecutionStatus.TIMEOUT

                    except Exception as e:
                        last_error = f"技能执行错误: {str(e)}"
                        logger.warning(f"{last_error} (尝试 {retry + 1})")
                        context.error_message = str(e)
                        context.status = SkillExecutionStatus.FAILED

                if not success:
                    context.end_time = time.time()
                    # 所有重试都失败，抛出异常
                    raise ValueError(f"技能 '{skill_name}' 执行失败: {last_error}")

                # 记录执行历史
                self.execution_history.append(context)
                final_output[skill_name] = {
                    "success": True,
                    "output": context.output_data,
                    "execution_time": context.get_execution_time(),
                }

            # 所有技能执行成功
            logger.info(
                f"技能链执行完成: id={execution_id}, 总用时: {time.time() - execution_contexts[0].start_time:.2f}秒"
            )

            return {
                "success": True,
                "execution_id": execution_id,
                "skill_results": final_output,
                "total_execution_time": sum(
                    ctx.get_execution_time() or 0 for ctx in execution_contexts
                ),
                "total_skills": len(skill_chain),
                "failed_skills": 0,
            }

        except Exception as e:
            logger.error(f"技能链执行失败: {str(e)}")

            # 收集已执行技能的结果
            executed_results = {}
            for ctx in execution_contexts:
                if ctx.status == SkillExecutionStatus.SUCCESS:
                    executed_results[ctx.skill_name] = {
                        "success": True,
                        "output": ctx.output_data,
                        "execution_time": ctx.get_execution_time(),
                    }

            return {
                "success": False,
                "execution_id": execution_id,
                "error": str(e),
                "executed_skills": executed_results,
                "failed_skill": skill_name if "skill_name" in locals() else None,
                "total_executed": len(executed_results),
            }

    def add_dependency(self, skill_name: str, depends_on: List[str]):
        """添加技能依赖关系"""
        if skill_name not in self.skill_dependencies:
            self.skill_dependencies[skill_name] = []

        for dep in depends_on:
            if dep not in self.skill_dependencies[skill_name]:
                self.skill_dependencies[skill_name].append(dep)

        logger.debug(f"添加依赖: {skill_name} -> {depends_on}")

    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        total_executions = len(self.execution_history)
        if total_executions == 0:
            return {"total_executions": 0, "success_rate": 0, "avg_execution_time": 0}

        successful = sum(
            1
            for ctx in self.execution_history
            if ctx.status == SkillExecutionStatus.SUCCESS
        )
        success_rate = successful / total_executions

        execution_times = [
            ctx.get_execution_time()
            for ctx in self.execution_history
            if ctx.get_execution_time() is not None
        ]
        avg_execution_time = (
            sum(execution_times) / len(execution_times) if execution_times else 0
        )

        # 按技能统计
        skill_stats = {}
        for ctx in self.execution_history:
            if ctx.skill_name not in skill_stats:
                skill_stats[ctx.skill_name] = {
                    "total": 0,
                    "successful": 0,
                    "total_time": 0,
                }

            skill_stats[ctx.skill_name]["total"] += 1
            if ctx.status == SkillExecutionStatus.SUCCESS:
                skill_stats[ctx.skill_name]["successful"] += 1
            if ctx.get_execution_time():
                skill_stats[ctx.skill_name]["total_time"] += ctx.get_execution_time()

        # 计算每个技能的平均时间和成功率
        for skill_name, stats in skill_stats.items():
            stats["success_rate"] = (
                stats["successful"] / stats["total"] if stats["total"] > 0 else 0
            )
            stats["avg_time"] = (
                stats["total_time"] / stats["successful"]
                if stats["successful"] > 0
                else 0
            )

        return {
            "total_executions": total_executions,
            "successful_executions": successful,
            "success_rate": success_rate,
            "avg_execution_time": avg_execution_time,
            "skill_stats": skill_stats,
        }

    def clear_history(self):
        """清空执行历史"""
        self.execution_history.clear()
        self.current_executions.clear()
        logger.info("执行历史已清空")


# ============================================================================
# 第三部分：组合技能模块化设计演示
# ============================================================================

# 首先定义一些基础技能（复用之前的技能系统）
from typing import List, Dict, Any, Optional


# 为了演示，我们简化技能基类的定义
class Skill(ABC):
    """技能基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        pass


class CompositeSkill(Skill):
    """组合技能 - 将多个简单技能组合成复杂功能"""

    def __init__(
        self,
        name: str,
        description: str,
        component_skills: List[Skill],
        orchestrator: Optional[SkillOrchestrator] = None,
    ):
        super().__init__(name, description)
        self.component_skills = component_skills
        self.orchestrator = orchestrator

        # 构建技能链
        self.skill_chain = []
        for skill in component_skills:
            self.skill_chain.append((skill.name, {}))

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行组合技能"""
        if not self.orchestrator:
            raise ValueError("组合技能需要编排器实例")

        # 准备技能链输入
        skill_chain_with_input = []
        for skill_name, _ in self.skill_chain:
            # 为每个技能准备输入数据
            # 这里简单地将所有输入传递给第一个技能，后续技能使用前一个技能的输出
            skill_input = kwargs.copy()
            skill_chain_with_input.append((skill_name, skill_input))

        # 执行技能链
        result = await self.orchestrator.execute_skill_chain(skill_chain_with_input)

        # 提取最终输出
        if result["success"]:
            # 返回最后一个技能的输出
            last_skill_name = self.skill_chain[-1][0]
            last_result = result["skill_results"].get(last_skill_name, {})
            return {
                "success": True,
                "output": last_result.get("output", {}),
                "execution_details": result,
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "未知错误"),
                "partial_results": result.get("executed_skills", {}),
            }

    def add_skill(self, skill: Skill, position: Optional[int] = None):
        """添加子技能"""
        if position is None:
            self.component_skills.append(skill)
            self.skill_chain.append((skill.name, {}))
        else:
            self.component_skills.insert(position, skill)
            self.skill_chain.insert(position, (skill.name, {}))

    def remove_skill(self, skill_name: str) -> bool:
        """移除子技能"""
        for i, skill in enumerate(self.component_skills):
            if skill.name == skill_name:
                self.component_skills.pop(i)
                # 从技能链中移除
                for j, (name, _) in enumerate(self.skill_chain):
                    if name == skill_name:
                        self.skill_chain.pop(j)
                        break
                return True
        return False

    def get_skill_info(self) -> Dict[str, Any]:
        """获取技能信息"""
        return {
            "name": self.name,
            "description": self.description,
            "component_count": len(self.component_skills),
            "component_skills": [skill.name for skill in self.component_skills],
            "skill_chain": self.skill_chain,
        }


# 示例技能1：天气查询技能（带缓存）
class WeatherQuerySkill(Skill):
    """天气查询技能 - 演示带缓存的实用技能"""

    def __init__(self):
        super().__init__("weather_query", "查询城市天气信息")
        self.cache = SkillCache(
            max_size=100, policy=CachePolicy.TTL, default_ttl=3600
        )  # 1小时缓存
        self.api_base_url = "https://api.weather.example.com"  # 模拟API

    async def _fetch_weather_from_api(self, city: str) -> Dict[str, Any]:
        """从API获取天气数据（模拟实现）"""
        # 模拟API延迟
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # 模拟天气数据
        weather_conditions = [
            "晴",
            "多云",
            "阴",
            "小雨",
            "中雨",
            "大雨",
            "雷阵雨",
            "雪",
        ]
        temperatures = {
            "北京": (15, 25),
            "上海": (18, 28),
            "广州": (22, 32),
            "深圳": (23, 33),
            "成都": (16, 26),
        }

        if city not in temperatures:
            raise ValueError(f"不支持的城市: {city}")

        temp_range = temperatures[city]
        current_temp = random.randint(temp_range[0], temp_range[1])
        condition = random.choice(weather_conditions)
        humidity = random.randint(40, 90)

        return {
            "city": city,
            "temperature": current_temp,
            "condition": condition,
            "humidity": humidity,
            "unit": "℃",
            "timestamp": time.time(),
            "forecast": [
                {
                    "day": "今天",
                    "high": current_temp + 2,
                    "low": current_temp - 2,
                    "condition": condition,
                },
                {
                    "day": "明天",
                    "high": current_temp + 1,
                    "low": current_temp - 3,
                    "condition": random.choice(weather_conditions),
                },
                {
                    "day": "后天",
                    "high": current_temp,
                    "low": current_temp - 4,
                    "condition": random.choice(weather_conditions),
                },
            ],
        }

    @cached(key_func=lambda self, city: f"weather:{city}")
    async def get_weather(self, city: str) -> Dict[str, Any]:
        """获取天气信息（带缓存）"""
        logger.info(f"查询天气: {city}")
        return await self._fetch_weather_from_api(city)

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行天气查询"""
        city = kwargs.get("city")
        if not city:
            return {"success": False, "error": "缺少城市参数"}

        try:
            weather_data = await self.get_weather(city)

            # 获取缓存统计
            cache_stats = self.cache.get_stats()

            return {
                "success": True,
                "output": weather_data,
                "metadata": {
                    "cached": cache_stats["hits"] > 0,
                    "cache_hit_rate": cache_stats["hit_rate"],
                    "response_time": random.uniform(0.1, 0.5),  # 模拟响应时间
                },
            }
        except Exception as e:
            return {"success": False, "error": f"天气查询失败: {str(e)}"}


# 示例技能2：旅行建议技能
class TravelSuggestionSkill(Skill):
    """旅行建议技能 - 基于天气提供旅行建议"""

    def __init__(self):
        super().__init__("travel_suggestion", "基于天气提供旅行建议")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行旅行建议"""
        weather_data = kwargs.get("weather_data")
        if not weather_data:
            return {"success": False, "error": "缺少天气数据"}

        city = weather_data.get("city")
        condition = weather_data.get("condition")
        temperature = weather_data.get("temperature")

        # 根据天气条件提供建议
        suggestions = []

        if condition in ["晴", "多云"]:
            suggestions.append(
                f"{city}天气{condition}，温度{temperature}℃，适合户外活动"
            )
            suggestions.append("建议：公园散步、郊游、骑行")
        elif condition in ["小雨", "中雨"]:
            suggestions.append(f"{city}有{condition}，温度{temperature}℃，建议室内活动")
            suggestions.append("建议：博物馆、咖啡馆、商场购物")
        elif condition in ["大雨", "雷阵雨"]:
            suggestions.append(f"{city}有{condition}，温度{temperature}℃，不建议外出")
            suggestions.append("建议：居家休息、看电影、读书")
        elif condition == "雪":
            suggestions.append(f"{city}下雪，温度{temperature}℃，适合雪景观赏")
            suggestions.append("建议：赏雪、滑雪、温泉")
        else:
            suggestions.append(f"{city}天气{condition}，温度{temperature}℃")
            suggestions.append("建议：根据个人喜好安排活动")

        # 添加穿衣建议
        if temperature >= 28:
            clothing = "轻便夏装，注意防晒"
        elif temperature >= 20:
            clothing = "春秋装，舒适为主"
        elif temperature >= 10:
            clothing = "外套，注意保暖"
        else:
            clothing = "厚外套或羽绒服，注意防寒"

        suggestions.append(f"穿衣建议: {clothing}")

        return {
            "success": True,
            "output": {
                "city": city,
                "weather_condition": condition,
                "temperature": temperature,
                "suggestions": suggestions,
                "clothing_advice": clothing,
            },
        }


# 示例技能3：路线规划技能
class RoutePlanningSkill(Skill):
    """路线规划技能 - 规划旅行路线"""

    def __init__(self):
        super().__init__("route_planning", "规划旅行路线")
        self.popular_spots = {
            "北京": ["天安门", "故宫", "长城", "颐和园", "鸟巢"],
            "上海": ["外滩", "东方明珠", "南京路", "豫园", "迪士尼"],
            "广州": ["广州塔", "白云山", "越秀公园", "陈家祠", "沙面"],
            "深圳": ["世界之窗", "欢乐谷", "大梅沙", "深圳湾公园", "华强北"],
            "成都": ["宽窄巷子", "锦里", "武侯祠", "大熊猫基地", "都江堰"],
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行路线规划"""
        city = kwargs.get("city")
        weather_condition = kwargs.get("weather_condition")
        if not city:
            return {"success": False, "error": "缺少城市参数"}

        # 获取热门景点
        spots = self.popular_spots.get(
            city, ["市中心", "当地特色街区", "博物馆", "公园"]
        )

        # 根据天气调整路线
        if weather_condition in ["大雨", "雷阵雨"]:
            # 雨天推荐室内景点
            indoor_spots = [
                spot
                for spot in spots
                if any(word in spot for word in ["博物馆", "馆", "祠", "园内"])
            ]
            if indoor_spots:
                spots = indoor_spots
            else:
                spots = spots[:2]  # 只推荐少量景点

        # 生成路线
        route = []
        for i, spot in enumerate(spots[:4]):  # 最多4个景点
            route.append(
                {
                    "order": i + 1,
                    "spot": spot,
                    "recommended_time": f"{i + 1}:00-{i + 2}:00",
                    "activity": self._get_activity_for_spot(spot, weather_condition),
                }
            )

        return {
            "success": True,
            "output": {
                "city": city,
                "weather_consideration": weather_condition,
                "total_spots": len(route),
                "route": route,
                "total_time": f"{len(route)}小时",
                "recommendation": self._get_overall_recommendation(weather_condition),
            },
        }

    def _get_activity_for_spot(self, spot: str, weather: str) -> str:
        """根据景点和天气推荐活动"""
        if "博物馆" in spot or "馆" in spot:
            return "参观展览"
        elif "公园" in spot or "山" in spot:
            if weather in ["晴", "多云"]:
                return "散步观光"
            else:
                return "快速游览"
        elif "街" in spot or "巷" in spot:
            return "逛街购物"
        elif "塔" in spot or "城" in spot:
            return "观光拍照"
        else:
            return "游览参观"

    def _get_overall_recommendation(self, weather: str) -> str:
        """获取整体推荐"""
        if weather in ["晴", "多云"]:
            return "天气良好，建议按计划游览所有景点"
        elif weather in ["小雨", "中雨"]:
            return "有雨，建议携带雨具，适当调整行程"
        elif weather in ["大雨", "雷阵雨"]:
            return "雨势较大，建议减少户外活动，选择室内景点"
        else:
            return "根据实际情况调整行程"


# 组合技能：旅行规划技能
class TravelPlanningSkill(CompositeSkill):
    """旅行规划组合技能 - 组合天气查询、旅行建议、路线规划"""

    def __init__(self, orchestrator: SkillOrchestrator):
        # 创建组件技能
        weather_skill = WeatherQuerySkill()
        suggestion_skill = TravelSuggestionSkill()
        route_skill = RoutePlanningSkill()

        # 初始化组合技能
        super().__init__(
            name="travel_planning",
            description="完整的旅行规划服务，包括天气查询、旅行建议和路线规划",
            component_skills=[weather_skill, suggestion_skill, route_skill],
            orchestrator=orchestrator,
        )

        # 设置技能依赖
        orchestrator.add_dependency(suggestion_skill.name, [weather_skill.name])
        orchestrator.add_dependency(route_skill.name, [suggestion_skill.name])

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行旅行规划"""
        # 准备技能链输入
        city = kwargs.get("city")
        if not city:
            return {"success": False, "error": "缺少城市参数"}

        # 构建技能链
        skill_chain = [
            (self.component_skills[0].name, {"city": city}),  # 天气查询
            (self.component_skills[1].name, {}),  # 旅行建议（自动获取天气数据）
            (
                self.component_skills[2].name,
                {},
            ),  # 路线规划（自动获取天气和旅行建议数据）
        ]

        # 执行技能链
        result = await self.orchestrator.execute_skill_chain(skill_chain)

        if result["success"]:
            # 整合所有结果
            weather_result = result["skill_results"].get(
                self.component_skills[0].name, {}
            )
            suggestion_result = result["skill_results"].get(
                self.component_skills[1].name, {}
            )
            route_result = result["skill_results"].get(
                self.component_skills[2].name, {}
            )

            return {
                "success": True,
                "output": {
                    "city": city,
                    "weather": weather_result.get("output", {}),
                    "suggestions": suggestion_result.get("output", {}),
                    "route_plan": route_result.get("output", {}),
                    "execution_summary": {
                        "total_time": result["total_execution_time"],
                        "skills_executed": result["total_skills"],
                    },
                },
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "旅行规划失败"),
                "partial_results": result.get("executed_skills", {}),
            }


# ============================================================================
# 第四部分：技能工程化分析与最佳实践
# ============================================================================


class SkillEngineeringAnalyzer:
    """技能工程化分析器 - 分析技能的设计质量和工程化水平"""

    def __init__(self):
        self.metrics = {}

    def analyze_skill(self, skill: Skill) -> Dict[str, Any]:
        """分析单个技能"""
        analysis = {
            "name": skill.name,
            "description": skill.description,
            "design_quality": {},
            "performance_metrics": {},
            "error_handling": {},
            "maintainability": {},
            "recommendations": [],
        }

        # 分析设计质量
        analysis["design_quality"] = self._analyze_design_quality(skill)

        # 分析性能指标
        analysis["performance_metrics"] = self._analyze_performance_metrics(skill)

        # 分析错误处理
        analysis["error_handling"] = self._analyze_error_handling(skill)

        # 分析可维护性
        analysis["maintainability"] = self._analyze_maintainability(skill)

        # 生成建议
        analysis["recommendations"] = self._generate_recommendations(analysis)

        return analysis

    def _analyze_design_quality(self, skill: Skill) -> Dict[str, Any]:
        """分析设计质量"""
        quality = {
            "single_responsibility": False,
            "interface_clarity": False,
            "dependency_management": False,
            "configurability": False,
            "issues": [],
        }

        # 检查单一职责
        method_count = len(
            [
                m
                for m in dir(skill)
                if not m.startswith("_") and callable(getattr(skill, m))
            ]
        )
        if method_count <= 10:  # 合理的方法数量
            quality["single_responsibility"] = True
        else:
            quality["issues"].append("方法数量过多，可能违反单一职责原则")

        # 检查接口清晰度
        execute_method = getattr(skill, "execute", None)
        if (
            execute_method
            and hasattr(execute_method, "__doc__")
            and execute_method.__doc__
        ):
            quality["interface_clarity"] = True
        else:
            quality["issues"].append("execute方法缺少文档，接口不够清晰")

        # 检查依赖管理
        init_method = skill.__init__
        init_params = inspect.signature(init_method).parameters
        if len(init_params) <= 5:  # 合理的参数数量
            quality["dependency_management"] = True
        else:
            quality["issues"].append("构造函数参数过多，依赖管理可能有问题")

        # 检查可配置性
        if hasattr(skill, "config") or hasattr(skill, "settings"):
            quality["configurability"] = True
        else:
            quality["issues"].append("缺少配置支持，可配置性较差")

        return quality

    def _analyze_performance_metrics(self, skill: Skill) -> Dict[str, Any]:
        """分析性能指标"""
        metrics = {
            "has_caching": False,
            "is_async": False,
            "timeout_handling": False,
            "resource_management": False,
            "suggestions": [],
        }

        # 检查是否有缓存
        if hasattr(skill, "cache") or any(
            "cache" in name.lower() for name in dir(skill)
        ):
            metrics["has_caching"] = True
        else:
            metrics["suggestions"].append("考虑添加缓存机制提高性能")

        # 检查是否支持异步
        execute_method = getattr(skill, "execute", None)
        if execute_method and asyncio.iscoroutinefunction(execute_method):
            metrics["is_async"] = True
        else:
            metrics["suggestions"].append("考虑支持异步执行提高并发能力")

        # 检查超时处理
        execute_code = inspect.getsource(execute_method) if execute_method else ""
        if "timeout" in execute_code.lower() or "asyncio.wait_for" in execute_code:
            metrics["timeout_handling"] = True
        else:
            metrics["suggestions"].append("考虑添加超时处理防止长时间阻塞")

        # 检查资源管理
        if hasattr(skill, "__enter__") and hasattr(skill, "__exit__"):
            metrics["resource_management"] = True
        elif hasattr(skill, "close") or hasattr(skill, "cleanup"):
            metrics["resource_management"] = True
        else:
            metrics["suggestions"].append("考虑添加资源管理机制")

        return metrics

    def _analyze_error_handling(self, skill: Skill) -> Dict[str, Any]:
        """分析错误处理"""
        error_handling = {
            "input_validation": False,
            "exception_handling": False,
            "error_recovery": False,
            "logging": False,
            "improvements": [],
        }

        execute_method = getattr(skill, "execute", None)
        if not execute_method:
            return error_handling

        execute_code = inspect.getsource(execute_method)

        # 检查输入验证
        if "validate" in execute_code.lower() or "check" in execute_code.lower():
            error_handling["input_validation"] = True
        else:
            error_handling["improvements"].append("建议添加输入验证逻辑")

        # 检查异常处理
        if "try:" in execute_code and "except" in execute_code:
            error_handling["exception_handling"] = True
        else:
            error_handling["improvements"].append("建议添加异常处理机制")

        # 检查错误恢复
        if "retry" in execute_code.lower() or "recover" in execute_code.lower():
            error_handling["error_recovery"] = True
        else:
            error_handling["improvements"].append("考虑添加错误恢复机制")

        # 检查日志记录
        if "log" in execute_code.lower() or "logger" in execute_code.lower():
            error_handling["logging"] = True
        else:
            error_handling["improvements"].append("建议添加日志记录")

        return error_handling

    def _analyze_maintainability(self, skill: Skill) -> Dict[str, Any]:
        """分析可维护性"""
        maintainability = {
            "code_complexity": "low",
            "test_coverage": "unknown",
            "documentation": "partial",
            "modularity": "medium",
            "suggestions": [],
        }

        # 估算代码复杂度（简化版）
        execute_method = getattr(skill, "execute", None)
        if execute_method:
            try:
                source = inspect.getsource(execute_method)
                lines = source.count("\n")
                if lines < 50:
                    maintainability["code_complexity"] = "low"
                elif lines < 100:
                    maintainability["code_complexity"] = "medium"
                else:
                    maintainability["code_complexity"] = "high"
                    maintainability["suggestions"].append("execute方法过长，考虑拆分")
            except:
                pass

        # 检查文档
        if skill.__doc__:
            maintainability["documentation"] = "good"
        elif hasattr(execute_method, "__doc__") and execute_method.__doc__:
            maintainability["documentation"] = "partial"
        else:
            maintainability["documentation"] = "poor"
            maintainability["suggestions"].append("建议添加详细文档")

        # 检查模块化
        method_names = [
            m
            for m in dir(skill)
            if not m.startswith("_") and callable(getattr(skill, m))
        ]
        if len(method_names) > 5 and any(name.startswith("_") for name in dir(skill)):
            maintainability["modularity"] = "good"
        else:
            maintainability["suggestions"].append("考虑进一步模块化设计")

        return maintainability

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于设计质量
        design_quality = analysis["design_quality"]
        if not design_quality["single_responsibility"]:
            recommendations.append("重构技能，确保单一职责")
        if not design_quality["interface_clarity"]:
            recommendations.append("完善接口文档，提高使用清晰度")

        # 基于性能指标
        performance = analysis["performance_metrics"]
        for suggestion in performance.get("suggestions", []):
            recommendations.append(suggestion)

        # 基于错误处理
        error_handling = analysis["error_handling"]
        for improvement in error_handling.get("improvements", []):
            recommendations.append(improvement)

        # 基于可维护性
        maintainability = analysis["maintainability"]
        for suggestion in maintainability.get("suggestions", []):
            recommendations.append(suggestion)

        return recommendations

    def generate_report(self, skill: Skill) -> str:
        """生成分析报告"""
        analysis = self.analyze_skill(skill)

        report_lines = [
            "=" * 60,
            f"技能工程化分析报告 - {skill.name}",
            "=" * 60,
            f"描述: {skill.description}",
            f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "1. 设计质量评估:",
        ]

        quality = analysis["design_quality"]
        report_lines.append(
            f"   单一职责: {'✓' if quality['single_responsibility'] else '✗'}"
        )
        report_lines.append(
            f"   接口清晰: {'✓' if quality['interface_clarity'] else '✗'}"
        )
        report_lines.append(
            f"   依赖管理: {'✓' if quality['dependency_management'] else '✗'}"
        )
        report_lines.append(
            f"   可配置性: {'✓' if quality['configurability'] else '✗'}"
        )

        if quality["issues"]:
            report_lines.append("   设计问题:")
            for issue in quality["issues"]:
                report_lines.append(f"     - {issue}")

        report_lines.extend(
            [
                "",
                "2. 性能指标评估:",
            ]
        )

        performance = analysis["performance_metrics"]
        report_lines.append(
            f"   缓存机制: {'✓' if performance['has_caching'] else '✗'}"
        )
        report_lines.append(f"   异步支持: {'✓' if performance['is_async'] else '✗'}")
        report_lines.append(
            f"   超时处理: {'✓' if performance['timeout_handling'] else '✗'}"
        )
        report_lines.append(
            f"   资源管理: {'✓' if performance['resource_management'] else '✗'}"
        )

        if performance["suggestions"]:
            report_lines.append("   性能优化建议:")
            for suggestion in performance["suggestions"]:
                report_lines.append(f"     - {suggestion}")

        report_lines.extend(
            [
                "",
                "3. 错误处理评估:",
            ]
        )

        error = analysis["error_handling"]
        report_lines.append(f"   输入验证: {'✓' if error['input_validation'] else '✗'}")
        report_lines.append(
            f"   异常处理: {'✓' if error['exception_handling'] else '✗'}"
        )
        report_lines.append(f"   错误恢复: {'✓' if error['error_recovery'] else '✗'}")
        report_lines.append(f"   日志记录: {'✓' if error['logging'] else '✗'}")

        if error["improvements"]:
            report_lines.append("   错误处理改进建议:")
            for improvement in error["improvements"]:
                report_lines.append(f"     - {improvement}")

        report_lines.extend(
            [
                "",
                "4. 可维护性评估:",
            ]
        )

        maintain = analysis["maintainability"]
        report_lines.append(f"   代码复杂度: {maintain['code_complexity'].upper()}")
        report_lines.append(f"   文档完整性: {maintain['documentation'].upper()}")
        report_lines.append(f"   模块化程度: {maintain['modularity'].upper()}")

        if maintain["suggestions"]:
            report_lines.append("   可维护性改进建议:")
            for suggestion in maintain["suggestions"]:
                report_lines.append(f"     - {suggestion}")

        report_lines.extend(
            [
                "",
                "5. 总体建议:",
            ]
        )

        for i, recommendation in enumerate(analysis["recommendations"], 1):
            report_lines.append(f"   {i}. {recommendation}")

        report_lines.extend(["", "=" * 60, "报告结束", "=" * 60])

        return "\n".join(report_lines)


class SkillEngineeringBestPractices:
    """技能工程化最佳实践指南"""

    @staticmethod
    def get_cache_best_practices() -> List[str]:
        """获取缓存最佳实践"""
        return [
            "1. 选择合适的缓存策略：根据数据访问模式选择TTL、LRU、LFU等策略",
            "2. 设置合理的缓存大小：根据内存限制和业务需求设置最大缓存大小",
            "3. 实现缓存穿透保护：对于不存在的键，避免频繁查询后端系统",
            "4. 考虑缓存雪崩：设置不同的过期时间，避免大量缓存同时失效",
            "5. 监控缓存命中率：定期监控缓存性能，优化缓存策略",
            "6. 支持缓存预热：系统启动时预加载常用数据到缓存",
            "7. 实现缓存清理机制：定期清理过期和无效的缓存条目",
        ]

    @staticmethod
    def get_orchestration_best_practices() -> List[str]:
        """获取编排最佳实践"""
        return [
            "1. 明确定义技能依赖：清晰定义技能间的依赖关系，避免循环依赖",
            "2. 实现错误传播机制：合理处理技能链中的错误，支持部分成功",
            "3. 支持超时控制：为每个技能设置合理的超时时间",
            "4. 实现重试机制：对于暂时性错误，支持自动重试",
            "5. 设计数据传递机制：优雅地在技能间传递数据和状态",
            "6. 支持并行执行：对于无依赖的技能，支持并行执行提高性能",
            "7. 提供执行监控：监控技能链执行状态和性能指标",
        ]

    @staticmethod
    def get_composite_skill_best_practices() -> List[str]:
        """获取组合技能最佳实践"""
        return [
            "1. 遵循组合设计模式：通过组合简单技能构建复杂功能",
            "2. 保持技能独立性：组合技能中的子技能应保持独立和可复用",
            "3. 设计清晰的接口：组合技能应该有清晰统一的接口",
            "4. 支持动态配置：允许运行时调整组合技能的子技能和参数",
            "5. 实现错误隔离：子技能错误不应导致整个组合技能崩溃",
            "6. 提供组合技能市场：支持组合技能的发布、分享和复用",
            "7. 支持可视化编排：提供图形化界面设计组合技能流程",
        ]

    @staticmethod
    def get_error_handling_best_practices() -> List[str]:
        """获取错误处理最佳实践"""
        return [
            "1. 输入验证先行：在执行前验证所有输入参数的合法性",
            "2. 异常分类处理：区分业务异常和系统异常，分别处理",
            "3. 优雅降级：核心功能失败时，尝试使用备用方案或返回简化结果",
            "4. 错误信息友好：提供对用户友好的错误信息，同时记录详细日志",
            "5. 重试策略合理：根据错误类型设置合理的重试次数和间隔",
            "6. 超时控制：设置合理的超时时间，避免长时间阻塞",
            "7. 错误监控告警：监控错误频率和类型，及时告警",
        ]

    @staticmethod
    def get_performance_best_practices() -> List[str]:
        """获取性能最佳实践"""
        return [
            "1. 异步执行：对于I/O密集型操作，使用异步执行提高并发能力",
            "2. 缓存优化：合理使用缓存，减少重复计算和外部调用",
            "3. 批量处理：支持批量操作，减少频繁调用的开销",
            "4. 资源池：对于昂贵资源（如数据库连接），使用连接池",
            "5. 懒加载：延迟加载非必要资源，减少启动时间",
            "6. 性能监控：监控技能执行时间、资源使用等关键指标",
            "7. 负载均衡：对于高负载技能，支持多实例负载均衡",
        ]


# ============================================================================
# 主演示函数
# ============================================================================


async def main_demo():
    """主演示函数 - 展示自定义技能的完整功能"""
    print("=" * 60)
    print("自定义技能开发演示")
    print("=" * 60)

    # 创建技能缓存
    print("\n1. 创建技能缓存...")
    cache = SkillCache(max_size=50, policy=CachePolicy.TTL, default_ttl=300)
    print(f"   缓存策略: {cache.policy.name}")
    print(f"   缓存大小: {cache.max_size}")
    print(f"   默认TTL: {cache.default_ttl}秒")

    # 演示缓存功能
    print("\n2. 演示缓存功能...")
    cache.set("test_key", "test_value", ttl=10)
    cached_value = cache.get("test_key")
    print(f"   缓存设置: test_key -> test_value")
    print(f"   缓存获取: {cached_value}")

    stats = cache.get_stats()
    print(f"   缓存统计: {stats}")

    # 创建技能编排器
    print("\n3. 创建技能编排器...")

    # 简化注册表实现
    class SimpleRegistry:
        def __init__(self):
            self.skills = {}

        def register_skill(self, skill):
            self.skills[skill.name] = skill

        def get_skill(self, name):
            return self.skills.get(name)

    registry = SimpleRegistry()
    orchestrator = SkillOrchestrator(registry, max_retries=2, timeout=10)

    # 创建并注册基础技能
    print("\n4. 创建基础技能...")
    weather_skill = WeatherQuerySkill()
    suggestion_skill = TravelSuggestionSkill()
    route_skill = RoutePlanningSkill()

    registry.register_skill(weather_skill)
    registry.register_skill(suggestion_skill)
    registry.register_skill(route_skill)

    print(f"   已注册技能: {list(registry.skills.keys())}")

    # 演示技能编排
    print("\n5. 演示技能编排...")

    # 设置技能依赖
    orchestrator.add_dependency(suggestion_skill.name, [weather_skill.name])
    orchestrator.add_dependency(route_skill.name, [suggestion_skill.name])

    # 执行技能链
    skill_chain = [
        (weather_skill.name, {"city": "北京"}),
        (suggestion_skill.name, {}),
        (route_skill.name, {}),
    ]

    print(f"   执行技能链: {[name for name, _ in skill_chain]}")

    try:
        result = await orchestrator.execute_skill_chain(skill_chain)

        if result["success"]:
            print(f"   技能链执行成功!")
            print(f"   总执行时间: {result['total_execution_time']:.2f}秒")
            print(f"   执行技能数: {result['total_skills']}")

            # 显示执行统计
            stats = orchestrator.get_execution_stats()
            print(f"   执行统计: 成功率 {stats['success_rate'] * 100:.1f}%")
        else:
            print(f"   技能链执行失败: {result.get('error')}")

    except Exception as e:
        print(f"   技能链执行异常: {str(e)}")

    # 创建组合技能
    print("\n6. 创建组合技能...")
    travel_planning_skill = TravelPlanningSkill(orchestrator)
    registry.register_skill(travel_planning_skill)

    print(f"   组合技能: {travel_planning_skill.name}")
    print(f"   描述: {travel_planning_skill.description}")
    print(f"   子技能数: {len(travel_planning_skill.component_skills)}")

    # 执行组合技能
    print("\n7. 执行组合技能...")
    try:
        travel_result = await travel_planning_skill.execute(city="上海")

        if travel_result["success"]:
            print(f"   旅行规划成功!")
            output = travel_result["output"]

            print(f"   城市: {output.get('city')}")

            weather = output.get("weather", {})
            if weather:
                print(
                    f"   天气: {weather.get('condition')}, {weather.get('temperature')}℃"
                )

            suggestions = output.get("suggestions", {}).get("suggestions", [])
            if suggestions:
                print(f"   旅行建议: {suggestions[0]}")

            route = output.get("route_plan", {}).get("route", [])
            if route:
                print(f"   路线规划: {len(route)}个景点")

            summary = output.get("execution_summary", {})
            print(
                f"   执行摘要: {summary.get('skills_executed')}个技能, {summary.get('total_time'):.2f}秒"
            )
        else:
            print(f"   旅行规划失败: {travel_result.get('error')}")

    except Exception as e:
        print(f"   组合技能执行异常: {str(e)}")

    # 技能工程化分析
    print("\n8. 技能工程化分析...")
    analyzer = SkillEngineeringAnalyzer()

    print(f"   分析技能: {weather_skill.name}")
    analysis = analyzer.analyze_skill(weather_skill)

    # 显示关键指标
    quality = analysis["design_quality"]
    print(
        f"   设计质量: 单一职责={quality['single_responsibility']}, 接口清晰={quality['interface_clarity']}"
    )

    performance = analysis["performance_metrics"]
    print(
        f"   性能指标: 缓存={performance['has_caching']}, 异步={performance['is_async']}"
    )

    # 生成报告
    report = analyzer.generate_report(weather_skill)
    print(f"   报告长度: {len(report)} 字符")

    # 保存报告
    report_file = "skill_engineering_analysis.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"   报告已保存到: {report_file}")

    # 显示最佳实践
    print("\n9. 技能工程化最佳实践:")
    practices = SkillEngineeringBestPractices()

    cache_practices = practices.get_cache_best_practices()
    print(f"   缓存最佳实践 ({len(cache_practices)}条):")
    for i, practice in enumerate(cache_practices[:3], 1):
        print(f"     {i}. {practice}")
    print(f"     ... (共{len(cache_practices)}条)")

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    print("开始运行自定义技能开发演示...")
    try:
        asyncio.run(main_demo())
    except Exception as e:
        print(f"演示运行失败: {str(e)}")
        import traceback

        traceback.print_exc()
