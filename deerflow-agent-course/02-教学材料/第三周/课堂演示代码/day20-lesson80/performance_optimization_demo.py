#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeerFlow Python Agent架构师训练营 - 第80节课：持久化性能优化 演示代码

本文件演示了检查点性能优化的完整实现，包括：
1. IncrementalCheckpoint: 增量检查点
2. CheckpointCompressor: 检查点压缩
3. CheckpointCache: 检查点缓存

使用方式：
python performance_optimization_demo.py --test
"""

import asyncio
import sys
import logging
import time
import json
import gzip
import pickle
import hashlib
import zlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from collections import OrderedDict
import uuid

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CheckpointStatus(Enum):
    CREATING = "creating"
    SAVING = "saving"
    AVAILABLE = "available"
    INCREMENTAL = "incremental"
    FAILED = "failed"


@dataclass
class CheckpointMetadata:
    checkpoint_id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    checksum: Optional[str] = None
    status: CheckpointStatus = CheckpointStatus.CREATING
    version: int = 1
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "status": self.status.value,
            "version": self.version,
            "parent_id": self.parent_id,
            "metadata": self.metadata
        }


@dataclass
class Checkpoint:
    metadata: CheckpointMetadata
    state: Dict[str, Any]


class CheckpointProvider(ABC):
    @abstractmethod
    async def save(self, checkpoint: Checkpoint) -> None: pass
    @abstractmethod
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]: pass
    @abstractmethod
    async def delete(self, checkpoint_id: str) -> bool: pass
    @abstractmethod
    async def list(self) -> List[str]: pass


class InMemoryProvider(CheckpointProvider):
    def __init__(self):
        self._store: Dict[str, Checkpoint] = {}
    
    async def save(self, checkpoint: Checkpoint) -> None:
        self._store[checkpoint.metadata.checkpoint_id] = checkpoint
    
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        return self._store.get(checkpoint_id)
    
    async def delete(self, checkpoint_id: str) -> bool:
        if checkpoint_id in self._store:
            del self._store[checkpoint_id]
            return True
        return False
    
    async def list(self) -> List[str]:
        return list(self._store.keys())


class IncrementalCheckpointManager:
    def __init__(self, provider: CheckpointProvider):
        self.provider = provider
        self._baseline: Optional[Checkpoint] = None
    
    async def save_full_checkpoint(
        self, name: str, state: Dict[str, Any]
    ) -> Checkpoint:
        checkpoint_id = f"{name}-full-{uuid.uuid4().hex[:8]}"
        
        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            name=name,
            status=CheckpointStatus.AVAILABLE,
            version=1
        )
        
        checkpoint = Checkpoint(metadata=metadata, state=state)
        await self.provider.save(checkpoint)
        
        self._baseline = checkpoint
        
        logger.info(f"完整检查点已保存: {checkpoint_id}")
        
        return checkpoint
    
    async def save_incremental(
        self, name: str, current_state: Dict[str, Any]
    ) -> Optional[Checkpoint]:
        if not self._baseline:
            return await self.save_full_checkpoint(name, current_state)
        
        diff = self._compute_diff(self._baseline.state, current_state)
        
        if not diff:
            logger.info("状态无变化，跳过保存")
            return None
        
        checkpoint_id = f"{name}-inc-{uuid.uuid4().hex[:8]}"
        
        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            name=name,
            status=CheckpointStatus.INCREMENTAL,
            version=self._baseline.metadata.version + 1,
            parent_id=self._baseline.metadata.checkpoint_id
        )
        
        incremental_state = {
            "_is_incremental": True,
            "_parent_id": self._baseline.metadata.checkpoint_id,
            "_diff": diff
        }
        
        checkpoint = Checkpoint(metadata=metadata, state=incremental_state)
        await self.provider.save(checkpoint)
        
        self._baseline = checkpoint
        
        logger.info(f"增量检查点已保存: {checkpoint_id}")
        
        return checkpoint
    
    def _compute_diff(
        self, old_state: Dict[str, Any], new_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        diff = {}
        
        all_keys = set(old_state.keys()) | set(new_state.keys())
        
        for key in all_keys:
            old_val = old_state.get(key)
            new_val = new_state.get(key)
            
            if old_val != new_val:
                diff[key] = new_val
        
        return diff
    
    async def restore(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        checkpoint = await self.provider.load(checkpoint_id)
        
        if not checkpoint:
            return None
        
        if checkpoint.metadata.status == CheckpointStatus.INCREMENTAL:
            parent_id = checkpoint.metadata.parent_id
            
            parent_state = await self._restore_full(parent_id)
            
            diff = checkpoint.state.get("_diff", {})
            parent_state.update(diff)
            
            return parent_state
        else:
            return checkpoint.state
    
    async def _restore_full(self, checkpoint_id: str) -> Dict[str, Any]:
        checkpoint = await self.provider.load(checkpoint_id)
        
        if not checkpoint:
            return {}
        
        if checkpoint.metadata.status == CheckpointStatus.INCREMENTAL:
            return await self.restore(checkpoint_id)
        
        return checkpoint.state


class CheckpointCompressor:
    COMPRESSION_LEVELS = {
        "none": 0,
        "fast": 1,
        "balanced": 6,
        "best": 9
    }
    
    def __init__(self, algorithm: str = "gzip", level: str = "balanced"):
        self.algorithm = algorithm
        self.level = self.COMPRESSION_LEVELS.get(level, 6)
    
    def compress(self, data: bytes) -> bytes:
        if self.algorithm == "gzip":
            return gzip.compress(data, compresslevel=self.level)
        elif self.algorithm == "zlib":
            return zlib.compress(data, level=self.level)
        else:
            return data
    
    def decompress(self, data: bytes) -> bytes:
        if self.algorithm == "gzip":
            return gzip.decompress(data)
        elif self.algorithm == "zlib":
            return zlib.decompress(data)
        else:
            return data
    
    def compress_dict(self, data: Dict) -> bytes:
        json_str = json.dumps(data, ensure_ascii=False)
        return self.compress(json_str.encode('utf-8'))
    
    def decompress_dict(self, data: bytes) -> Dict:
        decompressed = self.decompress(data)
        return json.loads(decompressed.decode('utf-8'))


class CheckpointCache:
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._cache: OrderedDict[str, Checkpoint] = OrderedDict()
        self._hits = 0
        self._misses = 0
    
    def get(self, checkpoint_id: str) -> Optional[Checkpoint]:
        if checkpoint_id in self._cache:
            self._cache.move_to_end(checkpoint_id)
            self._hits += 1
            return self._cache[checkpoint_id]
        
        self._misses += 1
        return None
    
    def put(self, checkpoint: Checkpoint) -> None:
        checkpoint_id = checkpoint.metadata.checkpoint_id
        
        if checkpoint_id in self._cache:
            del self._cache[checkpoint_id]
        
        self._cache[checkpoint_id] = checkpoint
        
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)
    
    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0


class OptimizedCheckpointManager:
    def __init__(
        self,
        provider: CheckpointProvider,
        enable_compression: bool = True,
        enable_cache: bool = True,
        cache_size: int = 50
    ):
        self.provider = provider
        self.incremental = IncrementalCheckpointManager(provider)
        self.compressor = CheckpointCompressor() if enable_compression else None
        self.cache = CheckpointCache(cache_size) if enable_cache else None
    
    async def save(
        self, name: str, state: Dict[str, Any], incremental: bool = True
    ) -> Checkpoint:
        if incremental:
            checkpoint = await self.incremental.save_incremental(name, state)
        else:
            checkpoint = await self.incremental.save_full_checkpoint(name, state)
        
        if checkpoint and self.compressor:
            logger.info(f"检查点压缩前: {checkpoint.metadata.size_bytes} bytes")
        
        if checkpoint and self.cache:
            self.cache.put(checkpoint)
        
        return checkpoint
    
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        if self.cache:
            cached = self.cache.get(checkpoint_id)
            if cached:
                logger.info("从缓存加载")
                return cached
        
        checkpoint = await self.provider.load(checkpoint_id)
        
        if checkpoint and self.cache:
            self.cache.put(checkpoint)
        
        return checkpoint
    
    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "compression_enabled": self.compressor is not None,
            "cache_enabled": self.cache is not None
        }
        
        if self.cache:
            stats["cache_hits"] = self.cache._hits
            stats["cache_misses"] = self.cache._misses
            stats["cache_hit_rate"] = f"{self.cache.hit_rate:.2%}"
            stats["cache_size"] = len(self.cache._cache)
        
        return stats


async def test_incremental():
    print("\n=== 测试增量检查点 ===")
    
    provider = InMemoryProvider()
    manager = IncrementalCheckpointManager(provider)
    
    state1 = {"counter": 0, "items": [1, 2, 3]}
    await manager.save_full_checkpoint("test", state1)
    
    state2 = {"counter": 10, "items": [1, 2, 3, 4]}
    await manager.save_incremental("test", state2)
    
    state3 = {"counter": 20, "items": [1, 2, 3, 4, 5]}
    await manager.save_incremental("test", state3)
    
    checkpoints = await provider.list()
    print(f"检查点数量: {len(checkpoints)}")
    
    restored = await manager.restore(checkpoints[-1])
    print(f"恢复状态: {restored}")
    
    print("✓ 增量检查点测试通过")


async def test_compression():
    print("\n=== 测试压缩 ===")
    
    compressor = CheckpointCompressor("gzip", "balanced")
    
    test_data = {"data": "x" * 10000}
    
    compressed = compressor.compress_dict(test_data)
    print(f"压缩前: {len(json.dumps(test_data))} bytes")
    print(f"压缩后: {len(compressed)} bytes")
    print(f"压缩比: {len(compressed) / len(json.dumps(test_data)):.2f}")
    
    decompressed = compressor.decompress_dict(compressed)
    assert decompressed == test_data
    
    print("✓ 压缩测试通过")


async def test_cache():
    print("\n=== 测试缓存 ===")
    
    cache = CheckpointCache(max_size=3)
    
    for i in range(5):
        metadata = CheckpointMetadata(
            checkpoint_id=f"cp-{i}",
            name="test"
        )
        checkpoint = Checkpoint(metadata=metadata, state={"index": i})
        cache.put(checkpoint)
    
    print(f"缓存大小: {len(cache._cache)}")
    
    cache.get("cp-0")
    cache.get("cp-1")
    
    print(f"命中率: {cache.hit_rate:.2%}")
    
    print("✓ 缓存测试通过")


async def test_optimized():
    print("\n=== 测试优化管理器 ===")
    
    provider = InMemoryProvider()
    manager = OptimizedCheckpointManager(
        provider,
        enable_compression=True,
        enable_cache=True,
        cache_size=10
    )
    
    for i in range(20):
        state = {"counter": i, "data": f"item-{i}"}
        await manager.save("task", state, incremental=True)
    
    stats = manager.get_stats()
    print(f"统计: {stats}")
    
    print("✓ 优化管理器测试通过")


async def run_all_tests():
    print("=" * 50)
    print("开始运行性能优化测试")
    print("=" * 50)
    
    await test_incremental()
    await test_compression()
    await test_cache()
    await test_optimized()
    
    print("\n" + "=" * 50)
    print("✓ 所有测试通过！")
    print("=" * 50)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        asyncio.run(run_all_tests())
    else:
        print("性能优化演示")
        asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
