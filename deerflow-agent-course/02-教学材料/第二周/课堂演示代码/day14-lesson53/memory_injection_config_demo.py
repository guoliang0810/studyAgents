#!/usr/bin/env python3
"""
Day 14 - 第53节课：记忆注入与配置
==================================

本演示代码实现记忆注入与配置系统，包括：
1. MemoryInjectionMiddleware - 记忆注入中间件
2. MemoryConfig - 内存配置管理类
3. FactLifecycleManager - 事实生命周期管理器

运行方式:
    python memory_injection_config_demo.py          # 运行演示
    python memory_injection_config_demo.py --test   # 运行测试
"""

import time
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import sys
import yaml
import os
from collections import deque


# ============================================================================
# 第一部分：数据模型和枚举定义
# ============================================================================

class MemoryType(Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working"


class FactStatus(Enum):
    """事实状态枚举"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    EXPIRED = "expired"


class InjectionStrategy(Enum):
    """注入策略枚举"""
    EXACT_MATCH = "exact_match"      # 精确匹配
    SEMANTIC_MATCH = "semantic_match"  # 语义匹配
    CONTEXTUAL = "contextual"        # 上下文匹配
    ADAPTIVE = "adaptive"           # 自适应匹配


class ConfigSource(Enum):
    """配置来源枚举"""
    ENV = "env"          # 环境变量
    FILE = "file"        # 配置文件
    DATABASE = "db"      # 数据库
    API = "api"          # API接口
    DEFAULT = "default"  # 默认值


@dataclass
class Fact:
    """事实数据模型"""
    content: str
    source: str
    confidence: float = 1.0
    memory_type: MemoryType = MemoryType.LONG_TERM
    status: FactStatus = FactStatus.ACTIVE
    id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    expires_at: Optional[float] = None
    
    def __post_init__(self):
        if self.id is None:
            import uuid
            self.id = str(uuid.uuid4())
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"置信度必须在0.0-1.0之间")
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


# ============================================================================
# 第二部分：配置管理系统
# ============================================================================

@dataclass
class ConfigValue:
    """配置值包装器"""
    value: Any
    source: ConfigSource
    priority: int  # 优先级数字，越小优先级越高
    timestamp: float = field(default_factory=time.time)


class MemoryConfig:
    """内存配置管理类"""
    
    def __init__(self):
        self._configs: Dict[str, ConfigValue] = {}
        self._config_sources: Dict[ConfigSource, Callable[[], Dict[str, Any]]] = {}
        self._defaults: Dict[str, Any] = {
            "injection.max_facts": 10,
            "injection.strategy": "semantic_match",
            "injection.cache_ttl": 3600,
            "injection.min_confidence": 0.5,
            "lifecycle.max_age_days": 30,
            "lifecycle.archive_threshold": 0.3,
            "lifecycle.check_interval": 3600,
            "performance.cache_size": 1000,
            "performance.enable_async": True,
            "performance.timeout_seconds": 30,
        }
    
    def register_source(self, source: ConfigSource, loader: Callable[[], Dict[str, Any]]):
        """注册配置源"""
        self._config_sources[source] = loader
    
    def load_all(self):
        """加载所有配置源"""
        # 按优先级顺序加载
        sources_order = [
            ConfigSource.ENV,     # 环境变量优先级最高
            ConfigSource.API,     # API次之
            ConfigSource.DATABASE, # 数据库
            ConfigSource.FILE,    # 配置文件
            ConfigSource.DEFAULT, # 默认值优先级最低
        ]
        
        for source in sources_order:
            if source in self._config_sources:
                try:
                    configs = self._config_sources[source]()
                    for key, value in configs.items():
                        # 根据来源设置优先级
                        priority = self._get_priority(source)
                        self._configs[key] = ConfigValue(value, source, priority)
                except Exception as e:
                    print(f"加载配置源 {source} 失败: {e}")
    
    def _get_priority(self, source: ConfigSource) -> int:
        """获取配置源优先级"""
        priorities = {
            ConfigSource.ENV: 1,
            ConfigSource.API: 2,
            ConfigSource.DATABASE: 3,
            ConfigSource.FILE: 4,
            ConfigSource.DEFAULT: 100,
        }
        return priorities.get(source, 100)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if key in self._configs:
            return self._configs[key].value
        elif key in self._defaults:
            return self._defaults[key]
        return default
    
    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.ENV):
        """动态设置配置值"""
        priority = self._get_priority(source)
        # 只在高优先级时覆盖（数字越小优先级越高）
        if key not in self._configs or priority < self._configs[key].priority:
            self._configs[key] = ConfigValue(value, source, priority)
    
    def get_with_source(self, key: str) -> Dict[str, Any]:
        """获取配置值及其来源信息"""
        if key in self._configs:
            cv = self._configs[key]
            return {"value": cv.value, "source": cv.source.value, "priority": cv.priority}
        elif key in self._defaults:
            return {"value": self._defaults[key], "source": "default", "priority": 100}
        return {"value": None, "source": "not_found", "priority": 0}
    
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置"""
        result = {}
        # 合并默认值和配置值
        all_keys = set(self._defaults.keys()) | set(self._configs.keys())
        for key in all_keys:
            result[key] = self.get_with_source(key)
        return result
    
    def reload(self, source: Optional[ConfigSource] = None):
        """重新加载配置"""
        if source is None:
            self.load_all()
        elif source in self._config_sources:
            try:
                configs = self._config_sources[source]()
                for key, value in configs.items():
                    priority = self._get_priority(source)
                    self._configs[key] = ConfigValue(value, source, priority)
            except Exception as e:
                print(f"重新加载配置源 {source} 失败: {e}")


# ============================================================================
# 第三部分：事实生命周期管理器
# ============================================================================

class FactLifecycleManager:
    """事实生命周期管理器"""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        self._facts: Dict[str, Fact] = {}
        self._lifecycle_log: List[Dict] = []
        self._last_check_time = time.time()
    
    def add_fact(self, fact: Fact):
        """添加事实"""
        self._facts[fact.id] = fact
        self._log_lifecycle(fact.id, "created", fact.status.value)
    
    def update_status(self, fact_id: str, new_status: FactStatus, reason: str = ""):
        """更新状态"""
        if fact_id not in self._facts:
            raise ValueError(f"事实 {fact_id} 不存在")
        
        fact = self._facts[fact_id]
        old_status = fact.status
        fact.status = new_status
        fact.updated_at = time.time()
        
        self._log_lifecycle(fact_id, "status_changed", new_status.value, 
                           {"old_status": old_status.value, "reason": reason})
    
    def check_expired(self):
        """检查过期事实"""
        now = time.time()
        expired = []
        
        for fact_id, fact in self._facts.items():
            if fact.is_expired() and fact.status == FactStatus.ACTIVE:
                self.update_status(fact_id, FactStatus.EXPIRED, "过期")
                expired.append(fact_id)
        
        return expired
    
    def archive_old_facts(self):
        """归档旧事实"""
        max_age = self.config.get("lifecycle.max_age_days", 30) * 24 * 3600
        threshold = self.config.get("lifecycle.archive_threshold", 0.3)
        now = time.time()
        archived = []
        
        for fact_id, fact in self._facts.items():
            if fact.status == FactStatus.ACTIVE and (now - fact.created_at) > max_age:
                # 根据置信度决定是否归档
                if fact.confidence < threshold:
                    self.update_status(fact_id, FactStatus.ARCHIVED, "置信度过低自动归档")
                    archived.append(fact_id)
        
        return archived
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total": len(self._facts),
            "active": 0,
            "archived": 0,
            "deleted": 0,
            "expired": 0,
        }
        
        for fact in self._facts.values():
            stats[fact.status.value] = stats.get(fact.status.value, 0) + 1
        
        return stats
    
    def get_lifecycle_log(self, limit: int = 100) -> List[Dict]:
        """获取生命周期日志"""
        return self._lifecycle_log[-limit:] if self._lifecycle_log else []
    
    def _log_lifecycle(self, fact_id: str, action: str, new_state: str, 
                      metadata: Dict[str, Any] = None):
        """记录生命周期事件"""
        log_entry = {
            "timestamp": time.time(),
            "fact_id": fact_id,
            "action": action,
            "new_state": new_state,
            "metadata": metadata or {}
        }
        self._lifecycle_log.append(log_entry)
    
    def run_maintenance(self):
        """运行维护任务"""
        now = time.time()
        check_interval = self.config.get("lifecycle.check_interval", 3600)
        
        if now - self._last_check_time > check_interval:
            expired = self.check_expired()
            archived = self.archive_old_facts()
            self._last_check_time = now
            
            return {
                "expired": len(expired),
                "archived": len(archived),
                "next_check": now + check_interval
            }
        
        return {"expired": 0, "archived": 0, "next_check": self._last_check_time + check_interval}


# ============================================================================
# 第四部分：记忆注入中间件
# ============================================================================

class MemoryInjectionMiddleware:
    """记忆注入中间件"""
    
    def __init__(self, config: MemoryConfig, lifecycle_manager: FactLifecycleManager):
        self.config = config
        self.lifecycle_manager = lifecycle_manager
        self._cache: Dict[str, Dict] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._injection_stats = {
            "total_injections": 0,
            "successful_injections": 0,
            "cache_hits": 0,
            "failed_injections": 0
        }
    
    def inject(self, query: str, context: Dict[str, Any] = None) -> str:
        """注入记忆到查询"""
        self._injection_stats["total_injections"] += 1
        
        # 检查缓存
        cache_key = self._generate_cache_key(query, context)
        cache_ttl = self.config.get("injection.cache_ttl", 3600)
        
        if cache_key in self._cache:
            if time.time() - self._cache_timestamps[cache_key] < cache_ttl:
                self._injection_stats["cache_hits"] += 1
                return self._cache[cache_key]["enhanced_query"]
        
        try:
            # 步骤1：提取相关记忆
            relevant_facts = self._extract_relevant_facts(query, context)
            
            # 步骤2：筛选高质量记忆
            filtered_facts = self._filter_facts(relevant_facts)
            
            # 步骤3：构建增强查询
            enhanced_query = self._build_enhanced_query(query, filtered_facts, context)
            
            # 步骤4：更新缓存
            self._cache[cache_key] = {
                "enhanced_query": enhanced_query,
                "fact_count": len(filtered_facts),
                "timestamp": time.time()
            }
            self._cache_timestamps[cache_key] = time.time()
            
            # 清理旧缓存
            self._cleanup_cache()
            
            self._injection_stats["successful_injections"] += 1
            return enhanced_query
            
        except Exception as e:
            self._injection_stats["failed_injections"] += 1
            print(f"记忆注入失败: {e}")
            return query  # 失败时返回原查询
    
    def _generate_cache_key(self, query: str, context: Dict[str, Any]) -> str:
        """生成缓存键"""
        import hashlib
        key_data = query + (json.dumps(context, sort_keys=True) if context else "")
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _extract_relevant_facts(self, query: str, context: Dict[str, Any]) -> List[Fact]:
        """提取相关事实"""
        # 模拟事实数据库
        # 在实际应用中，这里会连接实际的内存系统
        strategy = self.config.get("injection.strategy", "semantic_match")
        max_facts = self.config.get("injection.max_facts", 10)
        min_confidence = self.config.get("injection.min_confidence", 0.5)
        
        # 获取所有活跃事实
        all_facts = list(self.lifecycle_manager._facts.values())
        active_facts = [f for f in all_facts if f.status == FactStatus.ACTIVE and not f.is_expired()]
        
        # 根据策略筛选
        if strategy == "exact_match":
            relevant = [f for f in active_facts if query.lower() in f.content.lower()]
        elif strategy == "semantic_match":
            # 简化的语义匹配（实际需要嵌入模型）
            relevant = [f for f in active_facts if 
                       any(word in f.content.lower() for word in query.lower().split()[:3])]
        else:
            relevant = active_facts[:max_facts]
        
        # 按置信度排序
        relevant.sort(key=lambda f: f.confidence, reverse=True)
        
        return relevant[:max_facts]
    
    def _filter_facts(self, facts: List[Fact]) -> List[Fact]:
        """筛选高质量事实"""
        min_confidence = self.config.get("injection.min_confidence", 0.5)
        filtered = [f for f in facts if f.confidence >= min_confidence]
        return filtered
    
    def _build_enhanced_query(self, query: str, facts: List[Fact], context: Dict[str, Any]) -> str:
        """构建增强查询"""
        if not facts:
            return query
        
        # 构建上下文信息
        context_lines = []
        for i, fact in enumerate(facts[:5], 1):
            context_lines.append(f"[记忆{i}] {fact.content} (来源: {fact.source}, 置信度: {fact.confidence:.2f})")
        
        # 添加原始上下文
        if context and "previous_messages" in context:
            prev_msgs = context["previous_messages"][-3:]  # 最近3条消息
            for msg in prev_msgs:
                context_lines.append(f"[对话] {msg}")
        
        # 组合查询
        context_str = "\n".join(context_lines)
        enhanced = f"""基于以下上下文信息：

{context_str}

请回答：{query}"""
        
        return enhanced
    
    def _cleanup_cache(self):
        """清理缓存"""
        cache_size = self.config.get("performance.cache_size", 1000)
        if len(self._cache) > cache_size:
            # 移除最旧的缓存项
            sorted_keys = sorted(self._cache_timestamps.items(), key=lambda x: x[1])
            keys_to_remove = [k for k, _ in sorted_keys[:len(self._cache) - cache_size]]
            for key in keys_to_remove:
                self._cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._injection_stats,
            "cache_size": len(self._cache),
            "cache_hit_rate": (
                self._injection_stats["cache_hits"] / self._injection_stats["total_injections"]
                if self._injection_stats["total_injections"] > 0 else 0
            )
        }
    
    def clear_cache(self):
        """清理缓存"""
        self._cache.clear()
        self._cache_timestamps.clear()


# ============================================================================
# 第五部分：测试套件
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("🧪 运行记忆注入与配置测试套件")
    print("=" * 60)
    
    passed, total = 0, 8
    
    # 测试1: MemoryConfig基本功能
    print("\n📊 测试1: MemoryConfig基本功能")
    try:
        config = MemoryConfig()
        config.set("test.key", "value", ConfigSource.ENV)
        assert config.get("test.key") == "value"
        assert config.get("injection.max_facts") == 10  # 默认值
        print("   ✅ MemoryConfig基本功能正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试2: 配置优先级
    print("\n📊 测试2: 配置优先级")
    try:
        config = MemoryConfig()
        config.set("test.key", "env_value", ConfigSource.ENV)
        config.set("test.key", "file_value", ConfigSource.FILE)
        assert config.get("test.key") == "env_value"  # ENV优先级更高
        print("   ✅ 配置优先级正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试3: FactLifecycleManager状态管理
    print("\n📊 测试3: FactLifecycleManager状态管理")
    try:
        config = MemoryConfig()
        mgr = FactLifecycleManager(config)
        fact = Fact("测试事实", "test")
        mgr.add_fact(fact)
        mgr.update_status(fact.id, FactStatus.ARCHIVED, "测试归档")
        assert mgr._facts[fact.id].status == FactStatus.ARCHIVED
        print("   ✅ 状态管理正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试4: 过期检查
    print("\n📊 测试4: 过期检查")
    try:
        config = MemoryConfig()
        mgr = FactLifecycleManager(config)
        fact = Fact("测试事实", "test", expires_at=time.time() - 1)  # 已过期
        mgr.add_fact(fact)
        expired = mgr.check_expired()
        assert fact.id in expired
        assert mgr._facts[fact.id].status == FactStatus.EXPIRED
        print("   ✅ 过期检查正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试5: 归档功能
    print("\n📊 测试5: 归档功能")
    try:
        config = MemoryConfig()
        config.set("lifecycle.archive_threshold", 0.5, ConfigSource.ENV)
        mgr = FactLifecycleManager(config)
        
        # 添加低置信度事实
        fact = Fact("测试事实", "test", confidence=0.2, created_at=time.time() - 40*24*3600)
        mgr.add_fact(fact)
        
        archived = mgr.archive_old_facts()
        assert fact.id in archived
        print("   ✅ 归档功能正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试6: MemoryInjectionMiddleware基础注入
    print("\n📊 测试6: MemoryInjectionMiddleware基础注入")
    try:
        config = MemoryConfig()
        mgr = FactLifecycleManager(config)
        middleware = MemoryInjectionMiddleware(config, mgr)
        
        # 添加测试事实
        fact = Fact("Python编程", "test", confidence=0.9)
        mgr.add_fact(fact)
        
        enhanced = middleware.inject("Python")
        assert "Python编程" in enhanced
        print("   ✅ 基础注入正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试7: 缓存功能
    print("\n📊 测试7: 缓存功能")
    try:
        config = MemoryConfig()
        config.set("injection.cache_ttl", 10, ConfigSource.ENV)
        mgr = FactLifecycleManager(config)
        middleware = MemoryInjectionMiddleware(config, mgr)
        
        fact = Fact("缓存测试", "test")
        mgr.add_fact(fact)
        
        result1 = middleware.inject("测试查询")
        result2 = middleware.inject("测试查询")
        assert result1 == result2  # 缓存命中
        assert middleware._injection_stats["cache_hits"] > 0
        print("   ✅ 缓存功能正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试8: 统计功能
    print("\n📊 测试8: 统计功能")
    try:
        config = MemoryConfig()
        mgr = FactLifecycleManager(config)
        middleware = MemoryInjectionMiddleware(config, mgr)
        
        middleware.inject("查询1")
        middleware.inject("查询2")
        
        stats = middleware.get_stats()
        assert stats["total_injections"] == 2
        assert "cache_hit_rate" in stats
        print("   ✅ 统计功能正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    if passed == total:
        print("🎉 所有测试通过！")
    return passed == total


# ============================================================================
# 第六部分：演示主程序
# ============================================================================

def run_demo():
    """运行演示"""
    print("⚙️ Day 14 - 第53节课：记忆注入与配置演示")
    print("=" * 60)
    
    print("\n📝 演示1: 配置管理系统")
    config = MemoryConfig()
    
    # 注册配置源
    def load_env_config():
        return {"injection.max_facts": 5}
    
    def load_file_config():
        return {"lifecycle.max_age_days": 15}
    
    config.register_source(ConfigSource.ENV, load_env_config)
    config.register_source(ConfigSource.FILE, load_file_config)
    config.load_all()
    
    print(f"injection.max_facts: {config.get('injection.max_facts')}")
    print(f"lifecycle.max_age_days: {config.get('lifecycle.max_age_days')}")
    print(f"配置来源信息: {config.get_with_source('injection.max_facts')}")
    
    print("\n\n📝 演示2: 事实生命周期管理")
    mgr = FactLifecycleManager(config)
    
    # 添加测试事实
    facts = [
        Fact("用户喜欢Python编程", "user", confidence=0.9),
        Fact("用户使用VS Code编辑器", "user", confidence=0.8),
        Fact("用户是后端开发者", "user", confidence=0.7),
        Fact("临时信息", "system", confidence=0.3, expires_at=time.time() + 5),
    ]
    
    for fact in facts:
        mgr.add_fact(fact)
    
    print(f"事实统计: {mgr.get_stats()}")
    
    # 运行维护
    maintenance_result = mgr.run_maintenance()
    print(f"维护结果: {maintenance_result}")
    
    print("\n\n📝 演示3: 记忆注入")
    middleware = MemoryInjectionMiddleware(config, mgr)
    
    # 测试注入
    queries = [
        "推荐一个编辑器",
        "如何学习编程",
        "Python有什么优势",
    ]
    
    for query in queries:
        enhanced = middleware.inject(query, {"previous_messages": ["你好", "我想学习编程"]})
        print(f"\n查询: {query}")
        print(f"增强后: {enhanced[:150]}...")
    
    print("\n\n📝 演示4: 性能统计")
    print(f"注入统计: {middleware.get_stats()}")
    print(f"缓存大小: {len(middleware._cache)}")
    
    print("\n" + "=" * 60)
    print("✅ 演示完成！")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(0 if run_tests() else 1)
    else:
        run_demo()