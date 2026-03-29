#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeerFlow Python Agent 架构师训练营 - 第70节课演示代码
主题: 延迟加载策略 (Lazy Loading Strategy)

本文件演示延迟加载策略的实现，包括：
1. 延迟加载管理器：LazyLoadingManager类，支持急切加载/延迟加载模式
2. 智能预加载器：SmartPreloader类，基于马尔可夫模型预测组件使用
3. 性能优化：缓存管理、异步加载协调、预测算法优化
4. 应用场景：MCP工具加载优化、大型系统资源管理

延迟加载（Lazy Loading）是性能优化的重要技术，通过按需加载资源减少初始加载时间，
智能预加载（Smart Preloading）则基于使用模式预测提前加载可能需要的资源，
两者结合实现最优的用户体验和系统性能。

作者: DeerFlow教学团队
版本: v1.0.0
日期: 2024-04-11
"""

import asyncio
import time
import logging
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Set, Tuple, Callable, Awaitable, Union
from collections import defaultdict, Counter, deque
import random
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import pickle


# ============================================================================
# 第一部分：配置和基础类型定义
# ============================================================================

class LoadingStrategy(Enum):
    """加载策略枚举"""
    EAGER = "eager"      # 急切加载：立即加载所有组件
    LAZY = "lazy"        # 延迟加载：按需加载组件
    SMART = "smart"      # 智能预加载：基于预测加载


class ComponentType(Enum):
    """组件类型枚举"""
    MCP_TOOL = "mcp_tool"        # MCP工具
    MODEL = "model"              # AI模型
    DATABASE = "database"        # 数据库连接
    API_CLIENT = "api_client"    # API客户端
    UTILITY = "utility"          # 工具函数库
    CACHE = "cache"              # 缓存组件


@dataclass
class ComponentInfo:
    """组件信息"""
    name: str                          # 组件名称
    component_type: ComponentType      # 组件类型
    description: str = ""              # 组件描述
    size_bytes: int = 0                # 组件大小（字节）
    load_time_ms: int = 100            # 加载时间（毫秒）
    memory_usage_mb: int = 10          # 内存使用量（MB）
    dependencies: List[str] = field(default_factory=list)  # 依赖组件


@dataclass
class LazyLoadingConfig:
    """延迟加载配置"""
    loading_strategy: LoadingStrategy = LoadingStrategy.LAZY  # 加载策略
    max_cache_size: int = 100           # 最大缓存组件数量
    background_load_enabled: bool = True  # 是否启用后台加载
    preload_enabled: bool = True        # 是否启用预加载
    smart_preload_enabled: bool = False # 是否启用智能预加载
    prediction_model_path: Optional[str] = None  # 预测模型路径
    max_loading_threads: int = 4        # 最大加载线程数
    timeout_seconds: float = 30.0       # 加载超时时间（秒）
    enable_monitoring: bool = True      # 是否启用性能监控


@dataclass  
class LoadingStats:
    """加载统计信息"""
    total_requests: int = 0              # 总请求数
    cache_hits: int = 0                  # 缓存命中数
    eager_loads: int = 0                 # 急切加载数
    lazy_loads: int = 0                  # 延迟加载数
    preloads: int = 0                    # 预加载数
    smart_preloads: int = 0              # 智能预加载数
    total_load_time_ms: float = 0.0      # 总加载时间（毫秒）
    average_load_time_ms: float = 0.0    # 平均加载时间（毫秒）
    cache_hit_rate: float = 0.0          # 缓存命中率
    memory_usage_mb: float = 0.0         # 内存使用量（MB）
    
    def update_cache_hit(self, hit: bool):
        """更新缓存命中统计"""
        self.total_requests += 1
        if hit:
            self.cache_hits += 1
        self.cache_hit_rate = self.cache_hits / self.total_requests if self.total_requests > 0 else 0.0
    
    def add_load_time(self, load_time_ms: float, load_type: str):
        """添加加载时间统计"""
        self.total_load_time_ms += load_time_ms
        self.average_load_time_ms = self.total_load_time_ms / self.total_requests if self.total_requests > 0 else 0.0
        
        if load_type == "eager":
            self.eager_loads += 1
        elif load_type == "lazy":
            self.lazy_loads += 1
        elif load_type == "preload":
            self.preloads += 1
        elif load_type == "smart_preload":
            self.smart_preloads += 1
    
    def __str__(self) -> str:
        """统计信息字符串表示"""
        return (
            f"加载统计: 总请求={self.total_requests}, "
            f"缓存命中={self.cache_hits}({self.cache_hit_rate:.1%}), "
            f"急切加载={self.eager_loads}, 延迟加载={self.lazy_loads}, "
            f"预加载={self.preloads}, 智能预加载={self.smart_preloads}, "
            f"平均加载时间={self.average_load_time_ms:.2f}ms"
        )


# ============================================================================
# 第二部分：延迟加载管理器核心实现
# ============================================================================

class ComponentLoader(ABC):
    """组件加载器抽象基类"""
    
    @abstractmethod
    async def load_component(self, component_name: str) -> Any:
        """加载组件（抽象方法）"""
        pass
    
    @abstractmethod
    def unload_component(self, component_name: str) -> bool:
        """卸载组件（抽象方法）"""
        pass


class MockComponentLoader(ComponentLoader):
    """模拟组件加载器（用于演示）"""
    
    def __init__(self, components: Dict[str, ComponentInfo]):
        self.components = components
    
    async def load_component(self, component_name: str) -> Any:
        """模拟加载组件"""
        if component_name not in self.components:
            raise ValueError(f"组件不存在: {component_name}")
        
        component_info = self.components[component_name]
        
        # 模拟加载延迟
        load_time = component_info.load_time_ms / 1000.0
        await asyncio.sleep(load_time)
        
        # 模拟组件对象
        component = {
            "name": component_name,
            "type": component_info.component_type.value,
            "description": component_info.description,
            "size": component_info.size_bytes,
            "loaded_at": time.time(),
            "memory_usage": component_info.memory_usage_mb
        }
        
        logging.debug(f"模拟加载组件: {component_name} (耗时: {load_time:.3f}s)")
        return component
    
    def unload_component(self, component_name: str) -> bool:
        """模拟卸载组件"""
        if component_name in self.components:
            logging.debug(f"模拟卸载组件: {component_name}")
            return True
        return False


class LazyLoadingManager:
    """延迟加载管理器"""
    
    def __init__(
        self,
        config: LazyLoadingConfig,
        component_loader: ComponentLoader,
        component_registry: Dict[str, ComponentInfo]
    ):
        """
        初始化延迟加载管理器
        
        Args:
            config: 延迟加载配置
            component_loader: 组件加载器
            component_registry: 组件注册表（名称->信息）
        """
        self.config = config
        self.component_loader = component_loader
        self.component_registry = component_registry
        
        # 缓存管理
        self.loaded_components: Dict[str, Any] = {}          # 已加载组件
        self.loading_tasks: Dict[str, asyncio.Task] = {}     # 正在加载的任务
        self.loading_queue = asyncio.Queue()                 # 加载队列
        self.cache_order = deque()                           # 缓存访问顺序（LRU）
        
        # 统计和监控
        self.stats = LoadingStats()
        self.start_time = time.time()
        
        # 后台加载任务
        self.background_tasks: List[asyncio.Task] = []
        self._stop_background = asyncio.Event()
        
        # 初始化后台加载器
        if self.config.background_load_enabled:
            self._start_background_loader()
        
        logging.info(f"延迟加载管理器初始化完成，策略: {config.loading_strategy.value}")
    
    def _start_background_loader(self):
        """启动后台加载器"""
        async def background_loader():
            """后台加载器主循环"""
            while not self._stop_background.is_set():
                try:
                    # 从队列获取加载任务（非阻塞）
                    component_name = await asyncio.wait_for(
                        self.loading_queue.get(),
                        timeout=1.0
                    )
                    
                    try:
                        # 执行后台加载
                        await self._background_load_component(component_name)
                    finally:
                        self.loading_queue.task_done()
                        
                except asyncio.TimeoutError:
                    # 队列为空，继续等待
                    continue
                except Exception as e:
                    logging.error(f"后台加载器错误: {e}")
        
        # 启动后台任务
        task = asyncio.create_task(background_loader())
        self.background_tasks.append(task)
        logging.debug("后台加载器已启动")
    
    async def _background_load_component(self, component_name: str):
        """后台加载组件"""
        if component_name in self.loaded_components:
            return  # 已经加载
        
        if component_name in self.loading_tasks:
            return  # 正在加载
        
        # 创建加载任务
        task = asyncio.create_task(
            self._load_and_cache_component(component_name, "background")
        )
        self.loading_tasks[component_name] = task
        
        try:
            await task
        except Exception as e:
            logging.error(f"后台加载组件失败 {component_name}: {e}")
        finally:
            self.loading_tasks.pop(component_name, None)
    
    async def get(self, component_name: str, force_reload: bool = False) -> Any:
        """
        获取组件（支持延迟加载）
        
        Args:
            component_name: 组件名称
            force_reload: 是否强制重新加载
            
        Returns:
            组件对象
            
        Raises:
            ValueError: 组件不存在
            TimeoutError: 加载超时
        """
        # 检查组件是否存在
        if component_name not in self.component_registry:
            raise ValueError(f"组件不存在: {component_name}")
        
        # 更新统计
        self.stats.update_cache_hit(False)
        
        # 检查缓存（如果不需要强制重新加载）
        if not force_reload and component_name in self.loaded_components:
            self.stats.update_cache_hit(True)
            self._update_cache_order(component_name)
            logging.debug(f"缓存命中: {component_name}")
            return self.loaded_components[component_name]
        
        # 检查是否正在加载
        if component_name in self.loading_tasks:
            logging.debug(f"组件正在加载: {component_name}，等待完成")
            try:
                # 等待现有加载任务完成
                component = await asyncio.wait_for(
                    self.loading_tasks[component_name],
                    timeout=self.config.timeout_seconds
                )
                self.loaded_components[component_name] = component
                self._update_cache_order(component_name)
                return component
            except asyncio.TimeoutError:
                raise TimeoutError(f"组件加载超时: {component_name}")
        
        # 根据策略决定加载方式
        if self.config.loading_strategy == LoadingStrategy.EAGER:
            # 急切加载：同步加载并返回
            logging.info(f"急切加载组件: {component_name}")
            start_time = time.time()
            component = await self._load_and_cache_component(component_name, "eager")
            load_time = (time.time() - start_time) * 1000
            self.stats.add_load_time(load_time, "eager")
            return component
        
        elif self.config.loading_strategy == LoadingStrategy.LAZY:
            # 延迟加载：同步加载，但可触发后台预加载
            logging.info(f"延迟加载组件: {component_name}")
            start_time = time.time()
            component = await self._load_and_cache_component(component_name, "lazy")
            load_time = (time.time() - start_time) * 1000
            self.stats.add_load_time(load_time, "lazy")
            
            # 触发依赖组件的后台预加载
            if self.config.preload_enabled:
                await self._preload_dependencies(component_name)
            
            return component
        
        else:  # SMART策略
            # 智能预加载：同步加载，并触发智能预加载
            logging.info(f"智能预加载策略加载组件: {component_name}")
            start_time = time.time()
            component = await self._load_and_cache_component(component_name, "smart")
            load_time = (time.time() - start_time) * 1000
            self.stats.add_load_time(load_time, "smart_preload")
            
            # 触发智能预加载
            if self.config.smart_preload_enabled:
                await self._trigger_smart_preload(component_name)
            
            return component
    
    async def _load_and_cache_component(
        self, 
        component_name: str, 
        load_type: str = "lazy"
    ) -> Any:
        """加载并缓存组件"""
        try:
            # 加载组件
            component = await self.component_loader.load_component(component_name)
            
            # 缓存组件（检查缓存大小限制）
            self._cache_component(component_name, component)
            
            # 更新加载任务状态
            self.loading_tasks.pop(component_name, None)
            
            return component
            
        except Exception as e:
            # 清理加载任务
            self.loading_tasks.pop(component_name, None)
            raise e
    
    def _cache_component(self, component_name: str, component: Any):
        """缓存组件（实现LRU缓存策略）"""
        # 检查缓存大小限制
        if len(self.loaded_components) >= self.config.max_cache_size:
            # 移除最近最少使用的组件
            lru_component = self.cache_order.popleft()
            if lru_component in self.loaded_components:
                removed = self.loaded_components.pop(lru_component)
                logging.debug(f"缓存已满，移除LRU组件: {lru_component}")
                
                # 可选：触发组件卸载
                self.component_loader.unload_component(lru_component)
        
        # 添加新组件到缓存
        self.loaded_components[component_name] = component
        self._update_cache_order(component_name)
        
        # 更新内存使用统计
        component_info = self.component_registry.get(component_name)
        if component_info:
            self.stats.memory_usage_mb += component_info.memory_usage_mb
    
    def _update_cache_order(self, component_name: str):
        """更新缓存访问顺序（LRU策略）"""
        # 移除旧位置（如果存在）
        if component_name in self.cache_order:
            self.cache_order.remove(component_name)
        
        # 添加到末尾（最近使用）
        self.cache_order.append(component_name)
    
    async def _preload_dependencies(self, component_name: str):
        """预加载组件的依赖"""
        if component_name not in self.component_registry:
            return
        
        component_info = self.component_registry[component_name]
        dependencies = component_info.dependencies
        
        for dep_name in dependencies:
            # 检查是否已加载或正在加载
            if (dep_name not in self.loaded_components and 
                dep_name not in self.loading_tasks):
                
                # 添加到后台加载队列
                await self.loading_queue.put(dep_name)
                logging.debug(f"触发依赖预加载: {dep_name}")
    
    async def _trigger_smart_preload(self, component_name: str):
        """触发智能预加载（由子类实现）"""
        # 基类中为空实现，子类SmartLazyLoadingManager会重写
        pass
    
    async def preload(self, component_names: List[str]):
        """预加载指定组件列表"""
        if not self.config.preload_enabled:
            logging.warning("预加载功能未启用")
            return
        
        tasks = []
        for name in component_names:
            if (name not in self.loaded_components and 
                name not in self.loading_tasks):
                
                # 创建预加载任务
                task = asyncio.create_task(
                    self._load_and_cache_component(name, "preload")
                )
                tasks.append(task)
                self.stats.preloads += 1
                logging.info(f"预加载组件: {name}")
        
        # 等待所有预加载完成
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 记录失败的预加载
            failed = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed += 1
                    logging.warning(f"预加载失败 {component_names[i]}: {result}")
            
            logging.info(f"预加载完成: 成功{len(tasks)-failed}/{len(tasks)}个组件")
    
    async def unload(self, component_name: str) -> bool:
        """卸载指定组件"""
        if component_name not in self.loaded_components:
            return False
        
        # 从缓存中移除
        component = self.loaded_components.pop(component_name)
        
        # 从访问顺序中移除
        if component_name in self.cache_order:
            self.cache_order.remove(component_name)
        
        # 调用加载器卸载组件
        success = self.component_loader.unload_component(component_name)
        
        # 更新内存统计
        component_info = self.component_registry.get(component_name)
        if component_info:
            self.stats.memory_usage_mb -= component_info.memory_usage_mb
        
        logging.info(f"卸载组件: {component_name} (成功: {success})")
        return success
    
    def clear_cache(self):
        """清空所有缓存组件"""
        cleared = 0
        for component_name in list(self.loaded_components.keys()):
            if self.unload(component_name):
                cleared += 1
        
        logging.info(f"缓存已清空，移除 {cleared} 个组件")
        return cleared
    
    def get_stats(self) -> LoadingStats:
        """获取加载统计信息"""
        return self.stats
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            "loaded_count": len(self.loaded_components),
            "loading_count": len(self.loading_tasks),
            "cache_order": list(self.cache_order),
            "queue_size": self.loading_queue.qsize(),
            "memory_usage_mb": self.stats.memory_usage_mb
        }
    
    async def shutdown(self):
        """关闭管理器，清理资源"""
        logging.info("关闭延迟加载管理器...")
        
        # 停止后台加载器
        self._stop_background.set()
        
        # 取消所有加载任务
        for task_name, task in self.loading_tasks.items():
            task.cancel()
            logging.debug(f"取消加载任务: {task_name}")
        
        # 等待后台任务完成
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # 清空缓存
        self.clear_cache()
        
        logging.info("延迟加载管理器已关闭")


# ============================================================================
# 第三部分：智能预加载器实现
# ============================================================================

class PredictionModel(ABC):
    """预测模型抽象基类"""
    
    @abstractmethod
    def train(self, usage_sequences: List[List[str]]) -> None:
        """训练预测模型"""
        pass
    
    @abstractmethod
    def predict_next(self, current_components: List[str], top_k: int = 3) -> List[str]:
        """预测接下来可能使用的组件"""
        pass
    
    @abstractmethod
    def save(self, filepath: str) -> bool:
        """保存模型到文件"""
        pass
    
    @abstractmethod
    def load(self, filepath: str) -> bool:
        """从文件加载模型"""
        pass


class MarkovPredictionModel(PredictionModel):
    """马尔可夫预测模型（一阶）"""
    
    def __init__(self):
        self.transition_probs: Dict[str, Dict[str, float]] = {}
        self.component_counts: Dict[str, int] = {}
        self.total_transitions = 0
    
    def train(self, usage_sequences: List[List[str]]) -> None:
        """训练马尔可夫模型"""
        # 重置模型
        self.transition_probs.clear()
        self.component_counts.clear()
        self.total_transitions = 0
        
        # 统计转移次数
        transition_counts = defaultdict(Counter)
        
        for sequence in usage_sequences:
            for i in range(len(sequence) - 1):
                current = sequence[i]
                next_comp = sequence[i + 1]
                
                transition_counts[current][next_comp] += 1
                self.component_counts[current] = self.component_counts.get(current, 0) + 1
                self.total_transitions += 1
        
        # 计算转移概率
        for current, counts in transition_counts.items():
            total = sum(counts.values())
            self.transition_probs[current] = {
                next_comp: count / total
                for next_comp, count in counts.items()
            }
        
        logging.info(f"马尔可夫模型训练完成: {len(self.transition_probs)}个状态, {self.total_transitions}次转移")
    
    def predict_next(self, current_components: List[str], top_k: int = 3) -> List[str]:
        """预测接下来可能使用的组件"""
        if not current_components or not self.transition_probs:
            return []
        
        # 收集所有可能的下一组件及其概率
        predictions = defaultdict(float)
        
        for current in current_components:
            if current in self.transition_probs:
                for next_comp, prob in self.transition_probs[current].items():
                    predictions[next_comp] += prob
        
        # 按概率排序并返回top_k
        sorted_predictions = sorted(
            predictions.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [comp for comp, prob in sorted_predictions[:top_k]]
    
    def get_transition_probability(self, from_component: str, to_component: str) -> float:
        """获取转移概率"""
        if from_component in self.transition_probs:
            return self.transition_probs[from_component].get(to_component, 0.0)
        return 0.0
    
    def save(self, filepath: str) -> bool:
        """保存模型到文件"""
        try:
            model_data = {
                "transition_probs": self.transition_probs,
                "component_counts": self.component_counts,
                "total_transitions": self.total_transitions
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            logging.info(f"模型已保存到: {filepath}")
            return True
            
        except Exception as e:
            logging.error(f"保存模型失败: {e}")
            return False
    
    def load(self, filepath: str) -> bool:
        """从文件加载模型"""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.transition_probs = model_data["transition_probs"]
            self.component_counts = model_data["component_counts"]
            self.total_transitions = model_data["total_transitions"]
            
            logging.info(f"模型已加载: {filepath}")
            return True
            
        except Exception as e:
            logging.error(f"加载模型失败: {e}")
            return False


class UsageTracker:
    """组件使用跟踪器"""
    
    def __init__(self, max_sequence_length: int = 100):
        self.max_sequence_length = max_sequence_length
        self.current_session: List[str] = []
        self.history_sessions: List[List[str]] = []
        self.component_usage_times: Dict[str, List[float]] = defaultdict(list)
    
    def record_usage(self, component_name: str):
        """记录组件使用"""
        # 添加到当前会话
        self.current_session.append(component_name)
        
        # 记录使用时间
        self.component_usage_times[component_name].append(time.time())
        
        # 如果会话过长，截断
        if len(self.current_session) > self.max_sequence_length:
            self.current_session = self.current_session[-self.max_sequence_length:]
    
    def end_session(self):
        """结束当前会话，保存到历史"""
        if len(self.current_session) >= 2:  # 至少需要2个组件才能形成转移
            self.history_sessions.append(self.current_session.copy())
            logging.debug(f"会话结束，保存{len(self.current_session)}个组件使用记录")
        
        self.current_session.clear()
    
    def get_usage_sequences(self) -> List[List[str]]:
        """获取所有使用序列（历史+当前）"""
        sequences = self.history_sessions.copy()
        if self.current_session:
            sequences.append(self.current_session)
        return sequences
    
    def get_component_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取组件使用统计"""
        stats = {}
        for component, timestamps in self.component_usage_times.items():
            if timestamps:
                stats[component] = {
                    "usage_count": len(timestamps),
                    "first_used": min(timestamps),
                    "last_used": max(timestamps),
                    "avg_interval": (
                        (max(timestamps) - min(timestamps)) / len(timestamps)
                        if len(timestamps) > 1 else 0
                    )
                }
        return stats
    
    def save_to_file(self, filepath: str):
        """保存使用数据到文件"""
        data = {
            "history_sessions": self.history_sessions,
            "component_usage_times": dict(self.component_usage_times),
            "max_sequence_length": self.max_sequence_length
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, filepath: str):
        """从文件加载使用数据"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.history_sessions = data["history_sessions"]
        self.component_usage_times = defaultdict(list, data["component_usage_times"])
        self.max_sequence_length = data.get("max_sequence_length", 100)


class SmartPreloader:
    """智能预加载器"""
    
    def __init__(
        self,
        prediction_model: PredictionModel,
        usage_tracker: UsageTracker,
        confidence_threshold: float = 0.3
    ):
        self.prediction_model = prediction_model
        self.usage_tracker = usage_tracker
        self.confidence_threshold = confidence_threshold
        self.prediction_history: List[Tuple[List[str], List[str], float]] = []
    
    def train_model(self, usage_sequences: List[List[str]]):
        """训练预测模型"""
        self.prediction_model.train(usage_sequences)
        logging.info(f"智能预加载器模型训练完成，使用{len(usage_sequences)}个序列")
    
    def update_from_usage(self):
        """根据使用记录更新模型"""
        sequences = self.usage_tracker.get_usage_sequences()
        if len(sequences) >= 2:  # 有足够数据时重新训练
            self.train_model(sequences)
    
    def predict_and_preload(
        self,
        current_components: List[str],
        lazy_loading_manager: LazyLoadingManager,
        max_predictions: int = 5
    ) -> List[str]:
        """预测并触发预加载"""
        if not current_components:
            return []
        
        # 获取预测结果
        predictions = self.prediction_model.predict_next(
            current_components,
            top_k=max_predictions
        )
        
        if not predictions:
            return []
        
        # 计算预测置信度（平均转移概率）
        total_prob = 0.0
        valid_predictions = 0
        
        for current in current_components:
            for pred in predictions:
                if isinstance(self.prediction_model, MarkovPredictionModel):
                    prob = self.prediction_model.get_transition_probability(current, pred)
                    if prob > 0:
                        total_prob += prob
                        valid_predictions += 1
        
        avg_confidence = total_prob / valid_predictions if valid_predictions > 0 else 0.0
        
        # 保存预测历史
        self.prediction_history.append((current_components, predictions, avg_confidence))
        
        # 如果置信度超过阈值，触发预加载
        if avg_confidence >= self.confidence_threshold:
            # 过滤掉已经加载的组件
            cache_info = lazy_loading_manager.get_cache_info()
            loaded_components = set(cache_info.get("loaded_components", []))
            
            to_preload = [p for p in predictions if p not in loaded_components]
            
            if to_preload:
                # 异步触发预加载（不等待完成）
                asyncio.create_task(lazy_loading_manager.preload(to_preload))
                logging.info(
                    f"智能预加载触发: {to_preload} "
                    f"(置信度: {avg_confidence:.2f})"
                )
            
            return predictions
        
        return []
    
    def get_prediction_accuracy(self) -> float:
        """计算预测准确率（基于历史记录）"""
        if not self.prediction_history:
            return 0.0
        
        correct_predictions = 0
        total_predictions = 0
        
        # 简化的准确率计算：检查下一组件是否在预测列表中
        # 实际实现需要更复杂的评估逻辑
        for i in range(len(self.prediction_history) - 1):
            _, predicted, _ = self.prediction_history[i]
            next_actual = self.prediction_history[i + 1][0][0] if self.prediction_history[i + 1][0] else None
            
            if next_actual and next_actual in predicted:
                correct_predictions += 1
            total_predictions += 1
        
        return correct_predictions / total_predictions if total_predictions > 0 else 0.0
    
    def get_prediction_stats(self) -> Dict[str, Any]:
        """获取预测统计信息"""
        return {
            "total_predictions": len(self.prediction_history),
            "avg_confidence": (
                sum(h[2] for h in self.prediction_history) / len(self.prediction_history)
                if self.prediction_history else 0.0
            ),
            "accuracy": self.get_prediction_accuracy(),
            "recent_predictions": self.prediction_history[-10:] if self.prediction_history else []
        }


class SmartLazyLoadingManager(LazyLoadingManager):
    """智能延迟加载管理器（集成预加载器）"""
    
    def __init__(
        self,
        config: LazyLoadingConfig,
        component_loader: ComponentLoader,
        component_registry: Dict[str, ComponentInfo],
        smart_preloader: Optional[SmartPreloader] = None
    ):
        super().__init__(config, component_loader, component_registry)
        
        # 智能预加载器
        self.smart_preloader = smart_preloader
        
        # 使用跟踪器
        self.usage_tracker = UsageTracker()
        
        logging.info("智能延迟加载管理器初始化完成")
    
    async def get(self, component_name: str, force_reload: bool = False) -> Any:
        """获取组件（增加使用跟踪）"""
        # 记录组件使用
        self.usage_tracker.record_usage(component_name)
        
        # 调用父类方法获取组件
        component = await super().get(component_name, force_reload)
        
        # 触发智能预加载
        if (self.smart_preloader and 
            self.config.smart_preload_enabled):
            
            # 使用最近使用的组件作为上下文
            recent_components = self.usage_tracker.current_session[-3:]  # 最近3个
            self.smart_preloader.predict_and_preload(
                recent_components,
                self,
                max_predictions=3
            )
        
        return component
    
    async def _trigger_smart_preload(self, component_name: str):
        """触发智能预加载（重写父类方法）"""
        if self.smart_preloader:
            # 使用当前会话作为上下文
            recent_components = self.usage_tracker.current_session[-3:]
            self.smart_preloader.predict_and_preload(
                recent_components,
                self,
                max_predictions=3
            )
    
    def end_session(self):
        """结束当前使用会话"""
        self.usage_tracker.end_session()
        
        # 更新预测模型
        if self.smart_preloader:
            self.smart_preloader.update_from_usage()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        return self.usage_tracker.get_component_stats()


# ============================================================================
# 第四部分：演示和测试代码
# ============================================================================

class DemoComponents:
    """演示用组件生成器"""
    
    @staticmethod
    def create_component_registry(count: int = 20) -> Dict[str, ComponentInfo]:
        """创建演示用组件注册表"""
        registry = {}
        component_types = list(ComponentType)
        
        for i in range(count):
            component_type = random.choice(component_types)
            name = f"{component_type.value}_{i:03d}"
            
            # 创建组件信息
            info = ComponentInfo(
                name=name,
                component_type=component_type,
                description=f"演示用{component_type.value}组件 #{i}",
                size_bytes=random.randint(1024, 1024 * 1024),  # 1KB-1MB
                load_time_ms=random.randint(50, 500),  # 50-500ms
                memory_usage_mb=random.randint(5, 50),  # 5-50MB
                dependencies=[]
            )
            
            # 添加随机依赖（10%概率）
            if i > 0 and random.random() < 0.1:
                possible_deps = list(registry.keys())
                if possible_deps:
                    num_deps = random.randint(1, min(3, len(possible_deps)))
                    info.dependencies = random.sample(possible_deps, num_deps)
            
            registry[name] = info
        
        return registry
    
    @staticmethod
    def generate_usage_sequences(
        registry: Dict[str, ComponentInfo],
        num_sessions: int = 10,
        session_length: int = 20
    ) -> List[List[str]]:
        """生成模拟使用序列"""
        sequences = []
        component_names = list(registry.keys())
        
        for _ in range(num_sessions):
            session = []
            # 创建有模式的使用序列（模拟实际使用模式）
            start_component = random.choice(component_names)
            session.append(start_component)
            
            for _ in range(session_length - 1):
                # 70%概率继续使用相关组件，30%概率随机切换
                if random.random() < 0.7 and len(session) >= 2:
                    # 模拟模式：A->B->A->C等
                    prev = session[-1]
                    prev2 = session[-2] if len(session) >= 2 else None
                    
                    # 简单模式：有时返回上上一个组件
                    if prev2 and random.random() < 0.3:
                        next_comp = prev2
                    else:
                        # 选择依赖组件或随机组件
                        current_info = registry.get(prev)
                        if current_info and current_info.dependencies and random.random() < 0.5:
                            next_comp = random.choice(current_info.dependencies)
                        else:
                            next_comp = random.choice(component_names)
                else:
                    next_comp = random.choice(component_names)
                
                session.append(next_component)
            
            sequences.append(session)
        
        return sequences


async def demonstrate_basic_lazy_loading():
    """演示基本延迟加载功能"""
    print("=" * 60)
    print("演示1: 基本延迟加载功能")
    print("=" * 60)
    
    # 创建组件注册表
    registry = DemoComponents.create_component_registry(10)
    print(f"创建了 {len(registry)} 个演示组件")
    
    # 创建配置（延迟加载模式）
    config = LazyLoadingConfig(
        loading_strategy=LoadingStrategy.LAZY,
        max_cache_size=5,
        background_load_enabled=True,
        preload_enabled=True
    )
    
    # 创建组件加载器
    loader = MockComponentLoader(registry)
    
    # 创建延迟加载管理器
    manager = LazyLoadingManager(config, loader, registry)
    
    try:
        # 测试1: 首次加载组件（应触发延迟加载）
        print("\n1. 首次加载组件 'mcp_tool_001'")
        start_time = time.time()
        component1 = await manager.get("mcp_tool_001")
        load_time = (time.time() - start_time) * 1000
        print(f"   加载完成，耗时: {load_time:.2f}ms")
        print(f"   组件信息: {component1['name']}, 类型: {component1['type']}")
        
        # 测试2: 再次加载同一组件（应命中缓存）
        print("\n2. 再次加载同一组件（测试缓存）")
        start_time = time.time()
        component2 = await manager.get("mcp_tool_001")
        load_time = (time.time() - start_time) * 1000
        print(f"   缓存命中，耗时: {load_time:.2f}ms")
        print(f"   是否为同一对象: {component1 is component2}")
        
        # 测试3: 预加载多个组件
        print("\n3. 预加载多个组件")
        await manager.preload(["model_002", "database_003", "api_client_004"])
        
        # 测试4: 检查缓存信息
        print("\n4. 缓存状态")
        cache_info = manager.get_cache_info()
        print(f"   已加载组件数: {cache_info['loaded_count']}")
        print(f"   正在加载数: {cache_info['loading_count']}")
        print(f"   缓存顺序: {cache_info['cache_order']}")
        
        # 测试5: 获取统计信息
        print("\n5. 加载统计")
        stats = manager.get_stats()
        print(f"   {stats}")
        
        # 测试6: 卸载组件
        print("\n6. 卸载组件测试")
        success = await manager.unload("mcp_tool_001")
        print(f"   卸载结果: {success}")
        
        # 测试缓存状态
        cache_info = manager.get_cache_info()
        print(f"   卸载后已加载组件数: {cache_info['loaded_count']}")
        
    finally:
        # 关闭管理器
        await manager.shutdown()
    
    print("\n基本延迟加载演示完成！")


async def demonstrate_smart_preloading():
    """演示智能预加载功能"""
    print("\n" + "=" * 60)
    print("演示2: 智能预加载功能")
    print("=" * 60)
    
    # 创建组件注册表和使用序列
    registry = DemoComponents.create_component_registry(15)
    usage_sequences = DemoComponents.generate_usage_sequences(
        registry, num_sessions=5, session_length=15
    )
    
    print(f"创建了 {len(registry)} 个演示组件")
    print(f"生成了 {len(usage_sequences)} 个使用序列")
    
    # 创建马尔可夫预测模型
    prediction_model = MarkovPredictionModel()
    prediction_model.train(usage_sequences)
    
    # 创建使用跟踪器
    usage_tracker = UsageTracker()
    
    # 创建智能预加载器
    smart_preloader = SmartPreloader(prediction_model, usage_tracker, confidence_threshold=0.2)
    
    # 创建配置（智能预加载模式）
    config = LazyLoadingConfig(
        loading_strategy=LoadingStrategy.SMART,
        smart_preload_enabled=True,
        max_cache_size=8
    )
    
    # 创建组件加载器
    loader = MockComponentLoader(registry)
    
    # 创建智能延迟加载管理器
    manager = SmartLazyLoadingManager(
        config, loader, registry, smart_preloader
    )
    
    try:
        print("\n模拟用户使用场景...")
        
        # 模拟用户使用流程
        components_to_use = []
        for seq in usage_sequences[:2]:  # 使用前两个序列
            components_to_use.extend(seq[:5])  # 每个序列取前5个组件
        
        for i, comp_name in enumerate(components_to_use):
            print(f"\n步骤 {i+1}: 使用组件 '{comp_name}'")
            
            # 获取组件（会触发使用记录和智能预加载）
            component = await manager.get(comp_name)
            print(f"   组件加载: {component['name']}")
            
            # 获取预测统计
            if i % 3 == 0 and i > 0:  # 每3步显示一次预测信息
                pred_stats = smart_preloader.get_prediction_stats()
                print(f"   预测准确率: {pred_stats['accuracy']:.2%}")
                print(f"   平均置信度: {pred_stats['avg_confidence']:.2f}")
        
        # 结束会话并更新模型
        manager.end_session()
        
        # 显示最终统计
        print("\n最终统计:")
        stats = manager.get_stats()
        print(f"   {stats}")
        
        # 显示预测统计
        pred_stats = smart_preloader.get_prediction_stats()
        print(f"   总预测次数: {pred_stats['total_predictions']}")
        print(f"   预测准确率: {pred_stats['accuracy']:.2%}")
        
        # 显示使用统计
        usage_stats = manager.get_usage_stats()
        top_used = sorted(
            usage_stats.items(),
            key=lambda x: x[1]['usage_count'],
            reverse=True
        )[:5]
        
        print("\n最常使用的5个组件:")
        for comp, stat in top_used:
            print(f"   {comp}: 使用{stat['usage_count']}次")
        
    finally:
        # 关闭管理器
        await manager.shutdown()
    
    print("\n智能预加载演示完成！")


async def demonstrate_performance_comparison():
    """演示性能对比（急切加载 vs 延迟加载 vs 智能预加载）"""
    print("\n" + "=" * 60)
    print("演示3: 性能对比（急切加载 vs 延迟加载 vs 智能预加载）")
    print("=" * 60)
    
    # 创建较大的组件注册表
    registry = DemoComponents.create_component_registry(50)
    print(f"创建了 {len(registry)} 个演示组件用于性能测试")
    
    # 定义要测试的组件子集
    test_components = list(registry.keys())[:20]  # 前20个组件
    
    # 测试急切加载策略
    print("\n1. 测试急切加载策略...")
    eager_config = LazyLoadingConfig(
        loading_strategy=LoadingStrategy.EAGER,
        max_cache_size=50
    )
    
    eager_loader = MockComponentLoader(registry)
    eager_manager = LazyLoadingManager(eager_config, eager_loader, registry)
    
    eager_start = time.time()
    for comp_name in test_components:
        await eager_manager.get(comp_name)
    eager_time = time.time() - eager_start
    
    eager_stats = eager_manager.get_stats()
    print(f"   总时间: {eager_time:.2f}s")
    print(f"   平均加载时间: {eager_stats.average_load_time_ms:.2f}ms")
    
    await eager_manager.shutdown()
    
    # 测试延迟加载策略
    print("\n2. 测试延迟加载策略...")
    lazy_config = LazyLoadingConfig(
        loading_strategy=LoadingStrategy.LAZY,
        max_cache_size=20,
        background_load_enabled=True
    )
    
    lazy_loader = MockComponentLoader(registry)
    lazy_manager = LazyLoadingManager(lazy_config, lazy_loader, registry)
    
    lazy_start = time.time()
    for comp_name in test_components:
        await lazy_manager.get(comp_name)
    lazy_time = time.time() - lazy_start
    
    lazy_stats = lazy_manager.get_stats()
    print(f"   总时间: {lazy_time:.2f}s")
    print(f"   平均加载时间: {lazy_stats.average_load_time_ms:.2f}ms")
    print(f"   缓存命中率: {lazy_stats.cache_hit_rate:.1%}")
    
    await lazy_manager.shutdown()
    
    # 测试智能预加载策略（需要训练数据）
    print("\n3. 测试智能预加载策略...")
    
    # 生成训练数据
    usage_sequences = DemoComponents.generate_usage_sequences(
        registry, num_sessions=3, session_length=10
    )
    
    # 创建预测模型
    prediction_model = MarkovPredictionModel()
    prediction_model.train(usage_sequences)
    
    # 创建智能预加载器
    usage_tracker = UsageTracker()
    smart_preloader = SmartPreloader(prediction_model, usage_tracker)
    
    smart_config = LazyLoadingConfig(
        loading_strategy=LoadingStrategy.SMART,
        smart_preload_enabled=True,
        max_cache_size=20
    )
    
    smart_loader = MockComponentLoader(registry)
    smart_manager = SmartLazyLoadingManager(
        smart_config, smart_loader, registry, smart_preloader
    )
    
    smart_start = time.time()
    for comp_name in test_components:
        await smart_manager.get(comp_name)
    smart_time = time.time() - smart_start
    
    smart_stats = smart_manager.get_stats()
    print(f"   总时间: {smart_time:.2f}s")
    print(f"   平均加载时间: {smart_stats.average_load_time_ms:.2f}ms")
    print(f"   缓存命中率: {smart_stats.cache_hit_rate:.1%}")
    print(f"   智能预加载次数: {smart_stats.smart_preloads}")
    
    await smart_manager.shutdown()
    
    # 性能对比总结
    print("\n" + "=" * 60)
    print("性能对比总结:")
    print("=" * 60)
    
    print(f"{'策略':<15} {'总时间(s)':<12} {'平均加载时间(ms)':<20} {'缓存命中率':<15}")
    print("-" * 60)
    print(f"{'急切加载':<15} {eager_time:<12.2f} {eager_stats.average_load_time_ms:<20.2f} {'N/A':<15}")
    print(f"{'延迟加载':<15} {lazy_time:<12.2f} {lazy_stats.average_load_time_ms:<20.2f} {lazy_stats.cache_hit_rate:<15.1%}")
    print(f"{'智能预加载':<15} {smart_time:<12.2f} {smart_stats.average_load_time_ms:<20.2f} {smart_stats.cache_hit_rate:<15.1%}")
    
    # 计算性能提升
    if eager_time > 0:
        lazy_improvement = (eager_time - lazy_time) / eager_time * 100
        smart_improvement = (eager_time - smart_time) / eager_time * 100
        
        print(f"\n性能提升（相比急切加载）:")
        print(f"  延迟加载: {lazy_improvement:.1f}% 更快")
        print(f"  智能预加载: {smart_improvement:.1f}% 更快")
    
    print("\n性能对比演示完成！")


async def demonstrate_real_world_scenario():
    """演示真实场景应用（MCP工具加载优化）"""
    print("\n" + "=" * 60)
    print("演示4: 真实场景应用 - MCP工具加载优化")
    print("=" * 60)
    
    # 模拟MCP工具组件
    mcp_tools = {
        "weather_tool": ComponentInfo(
            name="weather_tool",
            component_type=ComponentType.MCP_TOOL,
            description="获取天气信息的MCP工具",
            load_time_ms=200,
            memory_usage_mb=15
        ),
        "calculator_tool": ComponentInfo(
            name="calculator_tool", 
            component_type=ComponentType.MCP_TOOL,
            description="数学计算MCP工具",
            load_time_ms=100,
            memory_usage_mb=8
        ),
        "file_reader_tool": ComponentInfo(
            name="file_reader_tool",
            component_type=ComponentType.MCP_TOOL,
            description="文件读取MCP工具",
            load_time_ms=150,
            memory_usage_mb=12
        ),
        "web_search_tool": ComponentInfo(
            name="web_search_tool",
            component_type=ComponentType.MCP_TOOL,
            description="网络搜索MCP工具",
            load_time_ms=300,
            memory_usage_mb=20
        ),
        "database_query_tool": ComponentInfo(
            name="database_query_tool",
            component_type=ComponentType.MCP_TOOL,
            description="数据库查询MCP工具",
            load_time_ms=250,
            memory_usage_mb=18
        ),
        "image_processor_tool": ComponentInfo(
            name="image_processor_tool",
            component_type=ComponentType.MCP_TOOL,
            description="图像处理MCP工具",
            load_time_ms=400,
            memory_usage_mb=25
        )
    }
    
    # 创建典型的MCP工具使用模式
    usage_patterns = [
        # 天气查询会话
        ["weather_tool", "web_search_tool", "weather_tool"],
        # 数据分析会话
        ["file_reader_tool", "calculator_tool", "database_query_tool", "calculator_tool"],
        # 研究会话
        ["web_search_tool", "file_reader_tool", "calculator_tool", "web_search_tool"]
    ]
    
    print("模拟MCP工具场景:")
    print(f"  工具数量: {len(mcp_tools)}")
    print(f"  典型使用模式: {len(usage_patterns)}种")
    
    # 训练预测模型
    prediction_model = MarkovPredictionModel()
    prediction_model.train(usage_patterns)
    
    # 创建智能预加载配置
    config = LazyLoadingConfig(
        loading_strategy=LoadingStrategy.SMART,
        smart_preload_enabled=True,
        max_cache_size=4,  # 限制缓存大小，模拟内存受限环境
        background_load_enabled=True
    )
    
    # 创建MCP工具加载器
    loader = MockComponentLoader(mcp_tools)
    
    # 创建智能预加载器
    usage_tracker = UsageTracker()
    smart_preloader = SmartPreloader(prediction_model, usage_tracker, confidence_threshold=0.25)
    
    # 创建智能延迟加载管理器
    manager = SmartLazyLoadingManager(
        config, loader, mcp_tools, smart_preloader
    )
    
    try:
        print("\n模拟用户交互流程:")
        
        # 模拟用户执行多个任务
        scenarios = [
            ("查询天气", ["weather_tool", "web_search_tool"]),
            ("分析数据", ["file_reader_tool", "calculator_tool", "database_query_tool"]),
            ("进行研究", ["web_search_tool", "file_reader_tool", "calculator_tool"])
        ]
        
        total_start = time.time()
        
        for scenario_name, tools_needed in scenarios:
            print(f"\n任务: {scenario_name}")
            print(f"  需要工具: {tools_needed}")
            
            task_start = time.time()
            
            for tool_name in tools_needed:
                # 获取工具（可能触发智能预加载）
                tool = await manager.get(tool_name)
                print(f"    ✓ 加载工具: {tool['name']} ({tool['description']})")
            
            task_time = time.time() - task_start
            print(f"  任务完成时间: {task_time:.2f}s")
            
            # 结束当前会话
            manager.end_session()
        
        total_time = time.time() - total_start
        
        # 显示性能统计
        print("\n" + "-" * 40)
        print("性能统计:")
        print("-" * 40)
        
        stats = manager.get_stats()
        print(f"总任务时间: {total_time:.2f}s")
        print(f"缓存命中率: {stats.cache_hit_rate:.1%}")
        print(f"智能预加载次数: {stats.smart_preloads}")
        
        # 显示预测效果
        pred_stats = smart_preloader.get_prediction_stats()
        print(f"预测准确率: {pred_stats['accuracy']:.2%}")
        
        # 显示缓存效率
        cache_info = manager.get_cache_info()
        print(f"缓存使用: {cache_info['loaded_count']}/{config.max_cache_size}")
        print(f"内存使用: {cache_info['memory_usage_mb']:.1f}MB")
        
        # 如果没有延迟加载会怎样？
        print("\n" + "-" * 40)
        print("对比分析: 如果没有延迟加载...")
        print("-" * 40)
        
        # 计算所有工具的总加载时间
        total_load_time = sum(tool.load_time_ms for tool in mcp_tools.values()) / 1000
        print(f"所有工具急切加载总时间: {total_load_time:.2f}s")
        print(f"延迟加载节省时间: {(total_load_time - total_time):.2f}s ({((total_load_time - total_time)/total_load_time*100):.1f}%)")
        print(f"内存节省: 仅加载需要工具，而不是全部{len(mcp_tools)}个")
    
    finally:
        await manager.shutdown()
    
    print("\n真实场景演示完成！")


# ============================================================================
# 第五部分：单元测试
# ============================================================================

import unittest
import asynctest


class TestLazyLoadingConfig(unittest.TestCase):
    """测试延迟加载配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = LazyLoadingConfig()
        self.assertEqual(config.loading_strategy, LoadingStrategy.LAZY)
        self.assertEqual(config.max_cache_size, 100)
        self.assertTrue(config.background_load_enabled)
        self.assertTrue(config.preload_enabled)
        self.assertFalse(config.smart_preload_enabled)
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = LazyLoadingConfig(
            loading_strategy=LoadingStrategy.EAGER,
            max_cache_size=50,
            smart_preload_enabled=True,
            timeout_seconds=60.0
        )
        self.assertEqual(config.loading_strategy, LoadingStrategy.EAGER)
        self.assertEqual(config.max_cache_size, 50)
        self.assertTrue(config.smart_preload_enabled)
        self.assertEqual(config.timeout_seconds, 60.0)


class TestLoadingStats(unittest.TestCase):
    """测试加载统计"""
    
    def test_stats_update(self):
        """测试统计更新"""
        stats = LoadingStats()
        
        # 测试缓存命中
        stats.update_cache_hit(True)
        self.assertEqual(stats.total_requests, 1)
        self.assertEqual(stats.cache_hits, 1)
        self.assertEqual(stats.cache_hit_rate, 1.0)
        
        stats.update_cache_hit(False)
        self.assertEqual(stats.total_requests, 2)
        self.assertEqual(stats.cache_hits, 1)
        self.assertEqual(stats.cache_hit_rate, 0.5)
    
    def test_load_time_tracking(self):
        """测试加载时间跟踪"""
        stats = LoadingStats()
        stats.total_requests = 2  # 模拟已有请求
        
        stats.add_load_time(100.0, "eager")
        self.assertEqual(stats.eager_loads, 1)
        self.assertEqual(stats.total_load_time_ms, 100.0)
        self.assertEqual(stats.average_load_time_ms, 50.0)
        
        stats.add_load_time(50.0, "lazy")
        self.assertEqual(stats.lazy_loads, 1)
        self.assertEqual(stats.total_load_time_ms, 150.0)
        self.assertEqual(stats.average_load_time_ms, 50.0)


class TestComponentInfo(unittest.TestCase):
    """测试组件信息"""
    
    def test_component_info_creation(self):
        """测试组件信息创建"""
        info = ComponentInfo(
            name="test_component",
            component_type=ComponentType.MCP_TOOL,
            description="测试组件",
            size_bytes=1024,
            load_time_ms=100,
            memory_usage_mb=10,
            dependencies=["dep1", "dep2"]
        )
        
        self.assertEqual(info.name, "test_component")
        self.assertEqual(info.component_type, ComponentType.MCP_TOOL)
        self.assertEqual(info.description, "测试组件")
        self.assertEqual(info.size_bytes, 1024)
        self.assertEqual(info.load_time_ms, 100)
        self.assertEqual(info.memory_usage_mb, 10)
        self.assertEqual(info.dependencies, ["dep1", "dep2"])


class AsyncLazyLoadingTestCase(asynctest.TestCase):
    """异步延迟加载测试用例"""
    
    async def setUp(self):
        """测试前设置"""
        # 创建测试组件注册表
        self.registry = {
            "comp_a": ComponentInfo(
                name="comp_a",
                component_type=ComponentType.UTILITY,
                load_time_ms=50,
                memory_usage_mb=5
            ),
            "comp_b": ComponentInfo(
                name="comp_b",
                component_type=ComponentType.MODEL,
                load_time_ms=100,
                memory_usage_mb=20
            ),
            "comp_c": ComponentInfo(
                name="comp_c",
                component_type=ComponentType.DATABASE,
                load_time_ms=150,
                memory_usage_mb=15
            )
        }
        
        # 创建模拟加载器
        self.loader = MockComponentLoader(self.registry)
        
        # 创建配置
        self.config = LazyLoadingConfig(
            loading_strategy=LoadingStrategy.LAZY,
            max_cache_size=2
        )
    
    async def test_lazy_loading_basic(self):
        """测试基本延迟加载"""
        manager = LazyLoadingManager(self.config, self.loader, self.registry)
        
        try:
            # 首次加载
            comp = await manager.get("comp_a")
            self.assertEqual(comp["name"], "comp_a")
            
            # 再次加载应命中缓存
            comp2 = await manager.get("comp_a")
            self.assertIs(comp, comp2)  # 应为同一对象
            
            # 统计检查
            stats = manager.get_stats()
            self.assertEqual(stats.total_requests, 2)
            self.assertEqual(stats.cache_hits, 1)
            self.assertEqual(stats.cache_hit_rate, 0.5)
            
        finally:
            await manager.shutdown()
    
    async def test_cache_eviction(self):
        """测试缓存淘汰（LRU）"""
        manager = LazyLoadingManager(self.config, self.loader, self.registry)
        
        try:
            # 加载两个组件（缓存容量为2）
            await manager.get("comp_a")
            await manager.get("comp_b")
            
            # 检查缓存
            cache_info = manager.get_cache_info()
            self.assertEqual(cache_info["loaded_count"], 2)
            
            # 加载第三个组件，应触发缓存淘汰
            await manager.get("comp_c")
            
            # 检查缓存状态
            cache_info = manager.get_cache_info()
            self.assertEqual(cache_info["loaded_count"], 2)  # 应保持最大容量
            
            # comp_a 应该被淘汰（最先加载，最少最近使用）
            # 注意：实际淘汰策略可能因实现而异
            
        finally:
            await manager.shutdown()
    
    async def test_preload_functionality(self):
        """测试预加载功能"""
        manager = LazyLoadingManager(self.config, self.loader, self.registry)
        
        try:
            # 预加载组件
            await manager.preload(["comp_a", "comp_b"])
            
            # 检查缓存
            cache_info = manager.get_cache_info()
            self.assertEqual(cache_info["loaded_count"], 2)
            
            # 获取应命中缓存
            comp = await manager.get("comp_a")
            self.assertEqual(comp["name"], "comp_a")
            
            # 统计检查
            stats = manager.get_stats()
            self.assertEqual(stats.preloads, 2)
            
        finally:
            await manager.shutdown()
    
    async def test_unload_functionality(self):
        """测试卸载功能"""
        manager = LazyLoadingManager(self.config, self.loader, self.registry)
        
        try:
            # 加载组件
            await manager.get("comp_a")
            
            # 检查缓存
            cache_info = manager.get_cache_info()
            self.assertEqual(cache_info["loaded_count"], 1)
            
            # 卸载组件
            success = await manager.unload("comp_a")
            self.assertTrue(success)
            
            # 再次检查缓存
            cache_info = manager.get_cache_info()
            self.assertEqual(cache_info["loaded_count"], 0)
            
            # 卸载不存在的组件
            success = await manager.unload("nonexistent")
            self.assertFalse(success)
            
        finally:
            await manager.shutdown()


class TestMarkovPredictionModel(unittest.TestCase):
    """测试马尔可夫预测模型"""
    
    def setUp(self):
        self.model = MarkovPredictionModel()
        
        # 训练数据
        self.sequences = [
            ["A", "B", "C", "A", "B"],  # A->B, B->C, C->A, A->B
            ["A", "B", "D", "E"],        # A->B, B->D, D->E
            ["B", "C", "A", "F"]         # B->C, C->A, A->F
        ]
    
    def test_model_training(self):
        """测试模型训练"""
        self.model.train(self.sequences)
        
        # 检查转移概率
        self.assertIn("A", self.model.transition_probs)
        self.assertIn("B", self.model.transition_probs)
        
        # A的转移：在序列中，A后接B(2次)，后接F(1次)
        # 总转移次数: 3
        a_probs = self.model.transition_probs["A"]
        self.assertAlmostEqual(a_probs.get("B", 0), 2/3, places=2)
        self.assertAlmostEqual(a_probs.get("F", 0), 1/3, places=2)
    
    def test_prediction(self):
        """测试预测"""
        self.model.train(self.sequences)
        
        # 测试预测
        predictions = self.model.predict_next(["A"], top_k=2)
        
        # B的概率最高(2/3)，F次之(1/3)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0], "B")  # 概率最高
        self.assertEqual(predictions[1], "F")  # 概率次高
    
    def test_save_load(self):
        """测试模型保存和加载"""
        import tempfile
        import os
        
        self.model.train(self.sequences)
        
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            temp_path = f.name
        
        try:
            # 保存模型
            success = self.model.save(temp_path)
            self.assertTrue(success)
            
            # 创建新模型并加载
            new_model = MarkovPredictionModel()
            success = new_model.load(temp_path)
            self.assertTrue(success)
            
            # 检查加载的模型是否相同
            self.assertEqual(
                self.model.transition_probs.keys(),
                new_model.transition_probs.keys()
            )
            
            # 测试预测是否一致
            predictions1 = self.model.predict_next(["A"])
            predictions2 = new_model.predict_next(["A"])
            self.assertEqual(predictions1, predictions2)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestSmartPreloader(unittest.TestCase):
    """测试智能预加载器"""
    
    def setUp(self):
        # 创建预测模型
        self.model = MarkovPredictionModel()
        sequences = [["A", "B", "C"], ["A", "B", "D"], ["B", "C", "A"]]
        self.model.train(sequences)
        
        # 创建使用跟踪器
        self.tracker = UsageTracker()
        
        # 创建智能预加载器
        self.preloader = SmartPreloader(self.model, self.tracker, confidence_threshold=0.2)
    
    def test_prediction_with_confidence(self):
        """测试带置信度的预测"""
        # 模拟管理器（mock）
        class MockManager:
            def __init__(self):
                self.cache_info = {"loaded_components": []}
            
            def get_cache_info(self):
                return self.cache_info
            
            async def preload(self, components):
                pass  # 模拟方法
        
        manager = MockManager()
        
        # 测试预测
        predictions = self.preloader.predict_and_preload(
            ["A"], manager, max_predictions=2
        )
        
        # 应返回预测结果
        self.assertIn("B", predictions)  # A后最可能是B
        
        # 检查预测历史
        self.assertEqual(len(self.preloader.prediction_history), 1)
        
        # 检查置信度
        _, _, confidence = self.preloader.prediction_history[0]
        self.assertGreater(confidence, 0)


# ============================================================================
# 第六部分：主函数和演示执行
# ============================================================================

async def main_demo():
    """主演示函数"""
    print("🚀 DeerFlow Python Agent 架构师训练营 - 第70节课演示")
    print("主题: 延迟加载策略 (Lazy Loading Strategy)")
    print("=" * 70)
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # 执行演示
        await demonstrate_basic_lazy_loading()
        await demonstrate_smart_preloading()
        await demonstrate_performance_comparison()
        await demonstrate_real_world_scenario()
        
        print("\n" + "=" * 70)
        print("✅ 所有演示完成！")
        print("=" * 70)
        
        # 运行单元测试
        print("\n🔧 运行单元测试...")
        
        # 创建测试套件
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # 添加同步测试
        suite.addTests(loader.loadTestsFromTestCase(TestLazyLoadingConfig))
        suite.addTests(loader.loadTestsFromTestCase(TestLoadingStats))
        suite.addTests(loader.loadTestsFromTestCase(TestComponentInfo))
        suite.addTests(loader.loadTestsFromTestCase(TestMarkovPredictionModel))
        suite.addTests(loader.loadTestsFromTestCase(TestSmartPreloader))
        
        # 运行同步测试
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        print(f"\n单元测试结果: {result.testsRun}个测试，{len(result.failures)}失败，{len(result.errors)}错误")
        
        if result.wasSuccessful():
            print("✅ 所有测试通过！")
        else:
            print("⚠️  有测试失败，请检查实现")
        
    except Exception as e:
        print(f"\n❌ 演示执行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    # 运行主演示
    exit_code = asyncio.run(main_demo())
    exit(exit_code)