#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存策略优化 - 演示代码

本模块展示AI Agent系统中的缓存策略优化。
包含：多级缓存、TTL缓存、Redis集成、缓存策略。

本代码是DeerFlow架构师训练营第86节课的演示代码，
帮助学员掌握缓存优化的核心技能。

作者: DeerFlow架构师训练营
"""

import time
import hashlib
import json
from typing import Any, Optional, Dict, List, Callable
from dataclasses import dataclass
from collections import OrderedDict
from enum import Enum
from contextlib import contextmanager
import threading
import asyncio


# ============================================================================
# 第一部分：缓存策略类型
# ============================================================================

class CacheStrategy(Enum):
    """缓存策略类型"""
    LRU = "lru"           # 最近最少使用
    LFU = "lfu"           # 最不经常使用
    FIFO = "fifo"         # 先进先出
    TTL = "ttl"           # 时间过期
    WRITE_THROUGH = "write_through"  # 写穿透
    WRITE_BACK = "write_back"        # 写回


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "hit_rate": f"{self.hit_rate*100:.2f}%"
        }


# ============================================================================
# 第二部分：LRU缓存实现
# ============================================================================

class LRUCache:
    """最近最少使用缓存
    
    使用OrderedDict实现高效的LRU缓存
    
    使用示例:
        cache = LRUCache(capacity=100)
        cache.put("key", "value")
        value = cache.get("key")
    """
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache: OrderedDict = OrderedDict()
        self.stats = CacheStats()
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，不存在返回None
        """
        with self._lock:
            if key not in self.cache:
                self.stats.misses += 1
                return None
            
            # 移动到末尾（最近使用）
            self.cache.move_to_end(key)
            self.stats.hits += 1
            return self.cache[key]
    
    def put(self, key: str, value: Any) -> None:
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            if key in self.cache:
                # 更新已存在的键
                self.cache.move_to_end(key)
                self.cache[key] = value
            else:
                # 添加新键
                if len(self.cache) >= self.capacity:
                    # 移除最旧的项
                    self.cache.popitem(last=False)
                    self.stats.evictions += 1
                
                self.cache[key] = value
                self.stats.size = len(self.cache)
    
    def delete(self, key: str) -> bool:
        """删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.stats.size = len(self.cache)
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.stats = CacheStats()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            return self.stats.to_dict()


# ============================================================================
# 第三部分：TTL缓存实现
# ============================================================================

class CacheEntry:
    """缓存条目"""
    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.expire_time = time.time() + ttl
    
    def is_expired(self) -> bool:
        return time.time() > self.expire_time


class TTLCache:
    """带过期时间的缓存
    
    使用示例:
        cache = TTLCache(default_ttl=300)
        cache.set("key", "value", ttl=60)
        value = cache.get("key")
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()
        self._lock = threading.Lock()
    
    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，不存在或过期返回None
        """
        with self._lock:
            entry = self.cache.get(key)
            if entry is None:
                self.stats.misses += 1
                return None
            
            if entry.is_expired():
                del self.cache[key]
                self.stats.misses += 1
                return None
            
            self.stats.hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值
        """
        with self._lock:
            ttl = ttl if ttl is not None else self.default_ttl
            
            # 如果缓存已满，清理过期项
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._cleanup_expired()
            
            self.cache[key] = CacheEntry(value, ttl)
            self.stats.size = len(self.cache)
    
    def _cleanup_expired(self) -> None:
        """清理过期缓存项"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self.cache[key]
            self.stats.evictions += 1
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.stats.size = len(self.cache)
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.stats = CacheStats()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            return self.stats.to_dict()


# ============================================================================
# 第四部分：多级缓存
# ============================================================================

class MultiLevelCache:
    """多级缓存管理器
    
    支持L1（内存）和L2（Redis）多级缓存
    
    使用示例:
        cache = MultiLevelCache()
        cache.set_l1_cache(LRUCache(100))
        cache.set("key", "value")
    """
    
    def __init__(self):
        self.l1_cache: Optional[TTLCache] = None
        self.l2_cache: Optional[Any] = None  # 可接入Redis
        self.stats = CacheStats()
        self._lock = threading.Lock()
    
    def set_l1_cache(self, cache: TTLCache):
        """设置L1缓存"""
        self.l1_cache = cache
    
    def set_l2_cache(self, cache: Any):
        """设置L2缓存"""
        self.l2_cache = cache
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值
        
        查找顺序: L1 -> L2 -> 返回None
        """
        with self._lock:
            # 尝试L1缓存
            if self.l1_cache:
                value = self.l1_cache.get(key)
                if value is not None:
                    self.stats.hits += 1
                    return value
            
            # 尝试L2缓存
            if self.l2_cache:
                value = self.l2_cache.get(key)
                if value is not None:
                    # 回填L1缓存
                    if self.l1_cache:
                        self.l1_cache.set(key, value)
                    self.stats.hits += 1
                    return value
            
            self.stats.misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存值"""
        with self._lock:
            # 设置L1缓存
            if self.l1_cache:
                self.l1_cache.set(key, value, ttl)
            
            # 设置L2缓存
            if self.l2_cache:
                self.l2_cache.set(key, value, ttl)
    
    def delete(self, key: str) -> None:
        """删除缓存项"""
        with self._lock:
            if self.l1_cache:
                self.l1_cache.delete(key)
            if self.l2_cache:
                self.l2_cache.delete(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            stats = self.stats.to_dict()
            if self.l1_cache:
                stats["l1_cache"] = self.l1_cache.get_stats()
            if self.l2_cache:
                stats["l2_cache"] = "Redis connected"
            return stats


# ============================================================================
# 第五部分：缓存装饰器
# ============================================================================

def cached(cache: TTLCache, key_func: Optional[Callable] = None):
    """缓存装饰器
    
    使用示例:
        @cached(my_cache)
        def expensive_function(arg1, arg2):
            return compute_result(arg1, arg2)
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache.set(cache_key, result)
            
            return result
        return wrapper
    return decorator


# ============================================================================
# 第六部分：缓存策略优化
# ============================================================================

class CacheOptimizer:
    """缓存优化器
    
    提供缓存优化的策略和建议
    """
    
    # AI Agent系统推荐缓存的数据类型
    RECOMMENDED_CACHE = {
        "llm_response": {
            "description": "LLM响应缓存",
            "ttl": 3600,
            "strategy": CacheStrategy.TTL,
            "reason": "LLM调用成本高，相同prompt可复用"
        },
        "embedding": {
            "description": "向量嵌入缓存",
            "ttl": 86400,
            "strategy": CacheStrategy.LRU,
            "reason": "嵌入计算密集，结果可重复使用"
        },
        "tool_result": {
            "description": "工具执行结果缓存",
            "ttl": 300,
            "strategy": CacheStrategy.TTL,
            "reason": "幂等工具结果可缓存"
        },
        "user_session": {
            "description": "用户会话缓存",
            "ttl": 1800,
            "strategy": CacheStrategy.TTL,
            "reason": "会话信息短期有效"
        },
        "system_config": {
            "description": "系统配置缓存",
            "ttl": 3600,
            "strategy": CacheStrategy.TTL,
            "reason": "配置变更不频繁"
        }
    }
    
    # 不推荐缓存的数据类型
    NOT_RECOMMENDED_CACHE = {
        "user_input": "用户输入需要实时处理",
        "non_idempotent": "非幂等操作结果",
        "sensitive_data": "敏感数据不应缓存",
        "large_context": "大上下文缓存成本高"
    }
    
    @classmethod
    def get_recommended_strategy(cls, data_type: str) -> Optional[Dict]:
        """获取推荐缓存策略"""
        return cls.RECOMMENDED_CACHE.get(data_type)
    
    @classmethod
    def analyze_cache_effectiveness(
        cls,
        cache_stats: CacheStats,
        avg_response_time_ms: float,
        llm_cost_per_1k_tokens: float = 0.01
    ) -> Dict[str, Any]:
        """分析缓存有效性
        
        Args:
            cache_stats: 缓存统计
            avg_response_time_ms: 平均响应时间（毫秒）
            llm_cost_per_1k_tokens: LLM每1000 token成本
            
        Returns:
            分析报告
        """
        hit_rate = cache_stats.hit_rate
        total_requests = cache_stats.hits + cache_stats.misses
        
        # 估算节省的成本（假设每次LLM调用成本0.01美元）
        # 简化计算：每次缓存命中节省一次LLM调用
        cost_saved = cache_stats.hits * llm_cost_per_1k_tokens
        
        # 估算节省的时间
        # 假设每次LLM调用需要1秒
        time_saved_seconds = cache_stats.hits * 1.0
        
        return {
            "cache_hit_rate": f"{hit_rate*100:.2f}%",
            "total_requests": total_requests,
            "cache_hits": cache_stats.hits,
            "cost_saved_usd": f"${cost_saved:.2f}",
            "time_saved_seconds": f"{time_saved_seconds:.2f}s",
            "recommendation": "增加缓存命中率" if hit_rate < 0.5 else "缓存效果良好"
        }


# ============================================================================
# 演示代码
# ============================================================================

def run_cache_demo():
    """运行缓存演示"""
    print("=" * 70)
    print("DeerFlow缓存策略优化演示")
    print("=" * 70)
    
    # 1. LRU缓存演示
    print("\n### 1. LRU缓存演示")
    lru_cache = LRUCache(capacity=3)
    lru_cache.put("a", 1)
    lru_cache.put("b", 2)
    lru_cache.put("c", 3)
    print(f"初始缓存: a=1, b=2, c=3")
    print(f"获取a: {lru_cache.get('a')}")
    lru_cache.put("d", 4)
    print(f"添加d后获取b: {lru_cache.get('b')}")
    print(f"缓存统计: {lru_cache.get_stats()}")
    
    # 2. TTL缓存演示
    print("\n### 2. TTL缓存演示")
    ttl_cache = TTLCache(default_ttl=1)  # 1秒过期
    ttl_cache.set("key1", "value1")
    print(f"立即获取: {ttl_cache.get('key1')}")
    time.sleep(1.5)
    print(f"1.5秒后获取: {ttl_cache.get('key1')}")
    
    # 3. 缓存装饰器演示
    print("\n### 3. 缓存装饰器演示")
    cache = TTLCache(default_ttl=60)
    call_count = [0]
    
    @cached(cache)
    def expensive_operation(x: int) -> int:
        call_count[0] += 1
        return x * x
    
    print(f"第一次调用: {expensive_operation(5)}")
    print(f"第二次调用: {expensive_operation(5)}")
    print(f"函数调用次数: {call_count[0]}")
    print(f"缓存统计: {cache.get_stats()}")
    
    # 4. 缓存策略推荐
    print("\n### 4. 缓存策略推荐")
    optimizer = CacheOptimizer()
    for data_type, info in CacheOptimizer.RECOMMENDED_CACHE.items():
        print(f"\n{data_type}:")
        print(f"  描述: {info['description']}")
        print(f"  TTL: {info['ttl']}秒")
        print(f"  策略: {info['strategy'].value}")
        print(f"  原因: {info['reason']}")
    
    # 5. 缓存有效性分析
    print("\n### 5. 缓存有效性分析")
    stats = CacheStats(hits=80, misses=20, evictions=5, size=95)
    analysis = CacheOptimizer.analyze_cache_effectiveness(stats, 100)
    print(f"分析结果:")
    for key, value in analysis.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)


if __name__ == "__main__":
    run_cache_demo()
