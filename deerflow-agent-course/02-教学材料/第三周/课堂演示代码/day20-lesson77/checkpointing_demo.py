#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeerFlow Python Agent架构师训练营 - 第77节课：Checkpointing架构 演示代码

本文件演示了检查点系统（Checkpointing Architecture）的完整实现，包括：
1. CheckpointManager类：检查点管理器，支持创建、保存、恢复、查询检查点
2. CheckpointProvider抽象：多存储后端支持（内存、文件、Redis）
3. CheckpointMetadata类：检查点元数据管理
4. 完整测试套件：验证检查点功能

学习目标：
- 掌握检查点系统的核心概念和应用价值
- 理解CheckpointManager的架构设计和工作原理
- 实现多存储后端的检查点保存和恢复机制
- 掌握检查点元数据系统和标签管理

使用方式：
python checkpointing_demo.py          # 运行演示
python checkpointing_demo.py --test   # 运行测试套件
python checkpointing_demo.py --bench  # 运行性能基准测试
"""

import asyncio
import sys
import logging
import time
import json
import os
import pickle
import hashlib
import uuid
from typing import Dict, List, Optional, Any, Set, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from collections import defaultdict
import copy
import base64

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 枚举类型定义
# ============================================================================

class CheckpointStatus(Enum):
    """检查点状态"""
    CREATING = "creating"     # 创建中
    SAVING = "saving"         # 保存中
    AVAILABLE = "available"   # 可用
    RESTORING = "restoring"  # 恢复中
    FAILED = "failed"        # 失败
    DELETED = "deleted"      # 已删除


class StorageBackend(Enum):
    """存储后端类型"""
    MEMORY = "memory"        # 内存存储
    FILE = "file"           # 文件存储
    REDIS = "redis"          # Redis存储
    DATABASE = "database"     # 数据库存储


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class CheckpointMetadata:
    """检查点元数据"""
    checkpoint_id: str                       # 检查点ID
    name: str                                # 检查点名称
    description: Optional[str] = None        # 描述
    tags: List[str] = field(default_factory=list)  # 标签
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间
    size_bytes: int = 0                      # 大小（字节）
    checksum: Optional[str] = None           # 校验和
    status: CheckpointStatus = CheckpointStatus.CREATING  # 状态
    version: int = 1                         # 版本号
    parent_id: Optional[str] = None         # 父检查点ID
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    
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
    """检查点数据"""
    metadata: CheckpointMetadata
    state: Dict[str, Any]                      # 状态数据
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "state": self.state
        }


# ============================================================================
# 检查点提供者抽象基类
# ============================================================================

class CheckpointProvider(ABC):
    """检查点提供者抽象基类"""
    
    @property
    @abstractmethod
    def backend_type(self) -> StorageBackend:
        """返回存储后端类型"""
        pass
    
    @abstractmethod
    async def save(self, checkpoint: Checkpoint) -> bool:
        """保存检查点"""
        pass
    
    @abstractmethod
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """加载检查点"""
        pass
    
    @abstractmethod
    async def delete(self, checkpoint_id: str) -> bool:
        """删除检查点"""
        pass
    
    @abstractmethod
    async def exists(self, checkpoint_id: str) -> bool:
        """检查检查点是否存在"""
        pass
    
    @abstractmethod
    async def list_all(self) -> List[str]:
        """列出所有检查点ID"""
        pass
    
    @abstractmethod
    async def get_metadata(self, checkpoint_id: str) -> Optional[CheckpointMetadata]:
        """获取检查点元数据"""
        pass


class MemoryProvider(CheckpointProvider):
    """内存存储提供者"""
    
    def __init__(self):
        self._checkpoints: Dict[str, Checkpoint] = {}
    
    @property
    def backend_type(self) -> StorageBackend:
        return StorageBackend.MEMORY
    
    async def save(self, checkpoint: Checkpoint) -> bool:
        self._checkpoints[checkpoint.metadata.checkpoint_id] = checkpoint
        return True
    
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        return self._checkpoints.get(checkpoint_id)
    
    async def delete(self, checkpoint_id: str) -> bool:
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            return True
        return False
    
    async def exists(self, checkpoint_id: str) -> bool:
        return checkpoint_id in self._checkpoints
    
    async def list_all(self) -> List[str]:
        return list(self._checkpoints.keys())
    
    async def get_metadata(self, checkpoint_id: str) -> Optional[CheckpointMetadata]:
        checkpoint = self._checkpoints.get(checkpoint_id)
        return checkpoint.metadata if checkpoint else None


class FileProvider(CheckpointProvider):
    """文件存储提供者"""
    
    def __init__(self, base_path: str = "./checkpoints"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._metadata_file = self.base_path / "metadata.json"
        self._load_metadata_index()
    
    def _load_metadata_index(self):
        """加载元数据索引"""
        if self._metadata_file.exists():
            with open(self._metadata_file, 'r') as f:
                self._metadata_index = json.load(f)
        else:
            self._metadata_index = {}
    
    def _save_metadata_index(self):
        """保存元数据索引"""
        with open(self._metadata_file, 'w') as f:
            json.dump(self._metadata_index, f, indent=2)
    
    @property
    def backend_type(self) -> StorageBackend:
        return StorageBackend.FILE
    
    async def save(self, checkpoint: Checkpoint) -> bool:
        checkpoint_id = checkpoint.metadata.checkpoint_id
        checkpoint_dir = self.base_path / checkpoint_id
        checkpoint_dir.mkdir(exist_ok=True)
        
        # 保存元数据
        metadata_file = checkpoint_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(checkpoint.metadata.to_dict(), f, indent=2, default=str)
        
        # 保存状态
        state_file = checkpoint_dir / "state.json"
        with open(state_file, 'w') as f:
            json.dump(checkpoint.state, f, indent=2, default=str)
        
        # 更新索引
        self._metadata_index[checkpoint_id] = {
            "name": checkpoint.metadata.name,
            "created_at": checkpoint.metadata.created_at.isoformat()
        }
        self._save_metadata_index()
        
        return True
    
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        checkpoint_dir = self.base_path / checkpoint_id
        if not checkpoint_dir.exists():
            return None
        
        # 加载元数据
        metadata_file = checkpoint_dir / "metadata.json"
        with open(metadata_file, 'r') as f:
            metadata_dict = json.load(f)
        
        # 加载状态
        state_file = checkpoint_dir / "state.json"
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        # 重建对象
        metadata = CheckpointMetadata(**metadata_dict)
        return Checkpoint(metadata=metadata, state=state)
    
    async def delete(self, checkpoint_id: str) -> bool:
        checkpoint_dir = self.base_path / checkpoint_id
        if checkpoint_dir.exists():
            import shutil
            shutil.rmtree(checkpoint_dir)
            
            # 更新索引
            if checkpoint_id in self._metadata_index:
                del self._metadata_index[checkpoint_id]
                self._save_metadata_index()
            
            return True
        return False
    
    async def exists(self, checkpoint_id: str) -> bool:
        return (self.base_path / checkpoint_id).exists()
    
    async def list_all(self) -> List[str]:
        return list(self._metadata_index.keys())
    
    async def get_metadata(self, checkpoint_id: str) -> Optional[CheckpointMetadata]:
        if checkpoint_id not in self._metadata_index:
            return None
        
        metadata_file = self.base_path / checkpoint_id / "metadata.json"
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, 'r') as f:
            metadata_dict = json.load(f)
        
        return CheckpointMetadata(**metadata_dict)


class RedisProvider(CheckpointProvider):
    """Redis存储提供者（模拟实现）"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, 
                 prefix: str = "checkpoint:"):
        self.host = host
        self.port = port
        self.prefix = prefix
        self._cache: Dict[str, Checkpoint] = {}
        logger.info(f"RedisProvider初始化（模拟模式）: {host}:{port}")
    
    @property
    def backend_type(self) -> StorageBackend:
        return StorageBackend.REDIS
    
    async def save(self, checkpoint: Checkpoint) -> bool:
        key = f"{self.prefix}{checkpoint.metadata.checkpoint_id}"
        self._cache[key] = checkpoint
        logger.debug(f"保存检查点到Redis（模拟）: {key}")
        return True
    
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        key = f"{self.prefix}{checkpoint_id}"
        return self._cache.get(key)
    
    async def delete(self, checkpoint_id: str) -> bool:
        key = f"{self.prefix}{checkpoint_id}"
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def exists(self, checkpoint_id: str) -> bool:
        key = f"{self.prefix}{checkpoint_id}"
        return key in self._cache
    
    async def list_all(self) -> List[str]:
        prefix_len = len(self.prefix)
        return [k[prefix_len:] for k in self._cache.keys() if k.startswith(self.prefix)]
    
    async def get_metadata(self, checkpoint_id: str) -> Optional[CheckpointMetadata]:
        checkpoint = await self.load(checkpoint_id)
        return checkpoint.metadata if checkpoint else None


# ============================================================================
# 检查点管理器
# ============================================================================

class CheckpointManager:
    """
    检查点管理器
    
    功能：
    - 检查点创建、保存、恢复、删除
    - 多存储后端支持
    - 检查点去重和版本管理
    - 检查点查询和过滤
    - 异步并发保存
    """
    
    def __init__(self, 
                 providers: Optional[List[CheckpointProvider]] = None,
                 enable_deduplication: bool = True,
                 max_checkpoints: int = 100):
        """
        初始化检查点管理器
        
        Args:
            providers: 检查点提供者列表
            enable_deduplication: 是否启用去重
            max_checkpoints: 最大检查点数量
        """
        self.providers = providers or [MemoryProvider()]
        self.enable_deduplication = enable_deduplication
        self.max_checkpoints = max_checkpoints
        
        # 检查点缓存
        self._checkpoint_cache: Dict[str, Checkpoint] = {}
        
        # 统计信息
        self.stats = {
            "total_checkpoints": 0,
            "checkpoints_created": 0,
            "checkpoints_restored": 0,
            "checkpoints_failed": 0,
            "deduplications": 0,
            "total_save_time_ms": 0.0,
            "total_restore_time_ms": 0.0
        }
        
        logger.info(f"初始化CheckpointManager: providers={len(self.providers)}, "
                   f"deduplication={enable_deduplication}")
    
    def add_provider(self, provider: CheckpointProvider) -> None:
        """添加检查点提供者"""
        self.providers.append(provider)
        logger.info(f"添加检查点提供者: {provider.backend_type.value}")
    
    async def create_checkpoint(self,
                               name: str,
                               state: Dict[str, Any],
                               description: Optional[str] = None,
                               tags: Optional[List[str]] = None,
                               parent_id: Optional[str] = None,
                               metadata: Optional[Dict[str, Any]] = None) -> Checkpoint:
        """
        创建检查点
        
        Args:
            name: 检查点名称
            state: 状态数据
            description: 描述
            tags: 标签
            parent_id: 父检查点ID
            metadata: 额外元数据
        
        Returns:
            检查点对象
        """
        # 生成检查点ID
        checkpoint_id = self._generate_checkpoint_id(name, state)
        
        # 检查去重
        if self.enable_deduplication:
            existing = await self._find_duplicate(checkpoint_id)
            if existing:
                logger.info(f"检测到重复检查点: {checkpoint_id}")
                self.stats["deduplications"] += 1
                return existing
        
        # 创建元数据
        metadata_obj = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            name=name,
            description=description,
            tags=tags or [],
            parent_id=parent_id,
            metadata=metadata or {},
            status=CheckpointStatus.CREATING
        )
        
        # 创建检查点对象
        checkpoint = Checkpoint(
            metadata=metadata_obj,
            state=state
        )
        
        # 计算校验和
        checkpoint.metadata.checksum = self._calculate_checksum(state)
        checkpoint.metadata.size_bytes = len(json.dumps(state, default=str))
        
        # 缓存检查点
        self._checkpoint_cache[checkpoint_id] = checkpoint
        self.stats["checkpoints_created"] += 1
        self.stats["total_checkpoints"] += 1
        
        logger.info(f"创建检查点: {checkpoint_id} - {name}")
        
        return checkpoint
    
    async def save_checkpoint(self, checkpoint: Checkpoint) -> bool:
        """
        保存检查点到所有提供者
        
        Args:
            checkpoint: 检查点对象
        
        Returns:
            是否保存成功
        """
        start_time = time.time()
        
        checkpoint.metadata.status = CheckpointStatus.SAVING
        
        # 并发保存到所有提供者
        tasks = []
        for provider in self.providers:
            task = asyncio.create_task(self._save_to_provider(provider, checkpoint))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        duration = (time.time() - start_time) * 1000
        self.stats["total_save_time_ms"] += duration
        
        # 检查结果
        success = all(r is True for r in results if not isinstance(r, Exception))
        
        if success:
            checkpoint.metadata.status = CheckpointStatus.AVAILABLE
            checkpoint.metadata.updated_at = datetime.now()
            logger.info(f"检查点保存成功: {checkpoint.metadata.checkpoint_id}, "
                       f"duration={duration:.2f}ms")
        else:
            checkpoint.metadata.status = CheckpointStatus.FAILED
            self.stats["checkpoints_failed"] += 1
            logger.error(f"检查点保存失败: {checkpoint.metadata.checkpoint_id}")
        
        # 清理超过限制的旧检查点
        if self.stats["total_checkpoints"] > self.max_checkpoints:
            await self._cleanup_oldest()
        
        return success
    
    async def _save_to_provider(self, provider: CheckpointProvider, 
                                checkpoint: Checkpoint) -> bool:
        """保存检查点到单个提供者"""
        try:
            result = await provider.save(checkpoint)
            logger.debug(f"保存到 {provider.backend_type.value}: {result}")
            return result
        except Exception as e:
            logger.error(f"保存到提供者失败: {provider.backend_type.value}, error={str(e)}")
            return False
    
    async def restore_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        恢复检查点
        
        Args:
            checkpoint_id: 检查点ID
        
        Returns:
            检查点对象，如果不存在则返回None
        """
        start_time = time.time()
        
        # 尝试从缓存获取
        if checkpoint_id in self._checkpoint_cache:
            checkpoint = self._checkpoint_cache[checkpoint_id]
            checkpoint.metadata.status = CheckpointStatus.RESTORING
            self.stats["checkpoints_restored"] += 1
            logger.info(f"从缓存恢复检查点: {checkpoint_id}")
            return checkpoint
        
        # 尝试从提供者加载
        for provider in self.providers:
            checkpoint = await provider.load(checkpoint_id)
            if checkpoint:
                checkpoint.metadata.status = CheckpointStatus.RESTORING
                self._checkpoint_cache[checkpoint_id] = checkpoint
                self.stats["checkpoints_restored"] += 1
                
                duration = (time.time() - start_time) * 1000
                self.stats["total_restore_time_ms"] += duration
                
                logger.info(f"从 {provider.backend_type.value} 恢复检查点: {checkpoint_id}, "
                           f"duration={duration:.2f}ms")
                return checkpoint
        
        logger.warning(f"检查点不存在: {checkpoint_id}")
        return None
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        删除检查点
        
        Args:
            checkpoint_id: 检查点ID
        
        Returns:
            是否删除成功
        """
        # 从缓存删除
        if checkpoint_id in self._checkpoint_cache:
            del self._checkpoint_cache[checkpoint_id]
        
        # 从提供者删除
        success = True
        for provider in self.providers:
            result = await provider.delete(checkpoint_id)
            success = success and result
        
        if success:
            self.stats["total_checkpoints"] -= 1
            logger.info(f"删除检查点: {checkpoint_id}")
        
        return success
    
    async def list_checkpoints(self,
                              tag: Optional[str] = None,
                              name_pattern: Optional[str] = None,
                              limit: int = 100) -> List[CheckpointMetadata]:
        """
        列出检查点
        
        Args:
            tag: 标签过滤
            name_pattern: 名称模式匹配
            limit: 返回数量限制
        
        Returns:
            检查点元数据列表
        """
        all_checkpoints = []
        
        # 从所有提供者获取
        for provider in self.providers:
            checkpoint_ids = await provider.list_all()
            for checkpoint_id in checkpoint_ids:
                metadata = await provider.get_metadata(checkpoint_id)
                if metadata:
                    all_checkpoints.append(metadata)
        
        # 去重（基于ID）
        seen = set()
        unique_checkpoints = []
        for cp in all_checkpoints:
            if cp.checkpoint_id not in seen:
                seen.add(cp.checkpoint_id)
                unique_checkpoints.append(cp)
        
        # 过滤
        filtered = unique_checkpoints
        
        if tag:
            filtered = [cp for cp in filtered if tag in cp.tags]
        
        if name_pattern:
            import re
            pattern = re.compile(name_pattern)
            filtered = [cp for cp in filtered if pattern.match(cp.name)]
        
        # 按时间排序
        filtered.sort(key=lambda cp: cp.created_at, reverse=True)
        
        # 限制数量
        return filtered[:limit]
    
    async def get_checkpoint_info(self, checkpoint_id: str) -> Optional[CheckpointMetadata]:
        """获取检查点信息"""
        # 先检查缓存
        if checkpoint_id in self._checkpoint_cache:
            return self._checkpoint_cache[checkpoint_id].metadata
        
        # 从提供者获取
        for provider in self.providers:
            metadata = await provider.get_metadata(checkpoint_id)
            if metadata:
                return metadata
        
        return None
    
    def _generate_checkpoint_id(self, name: str, state: Dict[str, Any]) -> str:
        """生成检查点ID"""
        content = f"{name}:{json.dumps(state, sort_keys=True, default=str)}"
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"chk_{int(time.time())}_{hash_value}"
    
    def _calculate_checksum(self, state: Dict[str, Any]) -> str:
        """计算校验和"""
        content = json.dumps(state, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def _find_duplicate(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """查找重复检查点"""
        # 检查缓存
        if checkpoint_id in self._checkpoint_cache:
            return self._checkpoint_cache[checkpoint_id]
        
        # 检查提供者
        for provider in self.providers:
            if await provider.exists(checkpoint_id):
                return await provider.load(checkpoint_id)
        
        return None
    
    async def _cleanup_oldest(self) -> None:
        """清理最旧的检查点"""
        checkpoints = await self.list_checkpoints(limit=self.max_checkpoints)
        
        if len(checkpoints) > self.max_checkpoints:
            to_delete = checkpoints[self.max_checkpoints:]
            
            for cp in to_delete:
                await self.delete_checkpoint(cp.checkpoint_id)
                logger.info(f"清理旧检查点: {cp.checkpoint_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return copy.deepcopy(self.stats)


# ============================================================================
# 检查点管理器测试
# ============================================================================

class TestCheckpointing:
    """检查点系统测试套件"""
    
    @staticmethod
    async def test_basic_checkpoint() -> bool:
        """测试基本检查点功能"""
        logger.info("开始测试基本检查点")
        
        try:
            manager = CheckpointManager(providers=[MemoryProvider()])
            
            # 创建检查点
            state = {"counter": 42, "items": [1, 2, 3], "name": "test"}
            checkpoint = await manager.create_checkpoint(
                name="test_checkpoint",
                state=state,
                tags=["test", "demo"]
            )
            
            assert checkpoint.metadata.name == "test_checkpoint"
            assert checkpoint.state["counter"] == 42
            
            # 保存检查点
            success = await manager.save_checkpoint(checkpoint)
            assert success
            
            # 恢复检查点
            restored = await manager.restore_checkpoint(checkpoint.metadata.checkpoint_id)
            assert restored is not None
            assert restored.state["counter"] == 42
            
            logger.info("基本检查点测试通过")
            return True
            
        except Exception as e:
            logger.error(f"基本检查点测试失败: {str(e)}")
            return False
    
    @staticmethod
    async def test_multi_provider() -> bool:
        """测试多提供者"""
        logger.info("开始测试多提供者")
        
        try:
            providers = [
                MemoryProvider(),
                FileProvider("./test_checkpoints")
            ]
            manager = CheckpointManager(providers=providers)
            
            # 创建并保存
            state = {"value": 100, "data": {"key": "value"}}
            checkpoint = await manager.create_checkpoint(
                name="multi_provider_test",
                state=state
            )
            
            success = await manager.save_checkpoint(checkpoint)
            assert success
            
            # 恢复
            restored = await manager.restore_checkpoint(checkpoint.metadata.checkpoint_id)
            assert restored is not None
            assert restored.state["value"] == 100
            
            # 清理
            await manager.delete_checkpoint(checkpoint.metadata.checkpoint_id)
            
            logger.info("多提供者测试通过")
            return True
            
        except Exception as e:
            logger.error(f"多提供者测试失败: {str(e)}")
            return False
    
    @staticmethod
    async def test_checkpoint_deduplication() -> bool:
        """测试检查点去重"""
        logger.info("开始测试检查点去重")
        
        try:
            manager = CheckpointManager(enable_deduplication=True)
            
            # 创建相同状态的检查点
            state = {"counter": 999}
            
            checkpoint1 = await manager.create_checkpoint(name="dup_test", state=state)
            checkpoint2 = await manager.create_checkpoint(name="dup_test", state=state)
            
            # ID应该相同
            assert checkpoint1.metadata.checkpoint_id == checkpoint2.metadata.checkpoint_id
            
            stats = manager.get_stats()
            assert stats["deduplications"] >= 1
            
            logger.info("检查点去重测试通过")
            return True
            
        except Exception as e:
            logger.error(f"检查点去重测试失败: {str(e)}")
            return False
    
    @staticmethod
    async def test_checkpoint_listing() -> bool:
        """测试检查点列表"""
        logger.info("开始测试检查点列表")
        
        try:
            manager = CheckpointManager(providers=[MemoryProvider()])
            
            # 创建多个检查点
            for i in range(5):
                checkpoint = await manager.create_checkpoint(
                    name=f"checkpoint_{i}",
                    state={"index": i},
                    tags=["test"] if i % 2 == 0 else ["other"]
                )
                await manager.save_checkpoint(checkpoint)
            
            # 列出所有
            all_checkpoints = await manager.list_checkpoints()
            assert len(all_checkpoints) == 5
            
            # 按标签过滤
            tagged = await manager.list_checkpoints(tag="test")
            assert len(tagged) == 3
            
            logger.info("检查点列表测试通过")
            return True
            
        except Exception as e:
            logger.error(f"检查点列表测试失败: {str(e)}")
            return False
    
    @staticmethod
    async def run_all_tests() -> Dict[str, bool]:
        """运行所有测试"""
        logger.info("开始运行检查点系统测试套件")
        
        results = {
            "basic_checkpoint": await TestCheckpointing.test_basic_checkpoint(),
            "multi_provider": await TestCheckpointing.test_multi_provider(),
            "checkpoint_deduplication": await TestCheckpointing.test_checkpoint_deduplication(),
            "checkpoint_listing": await TestCheckpointing.test_checkpoint_listing()
        }
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        logger.info(f"测试套件完成: {passed}/{total} 通过")
        return results


# ============================================================================
# 演示函数
# ============================================================================

async def run_demo() -> None:
    """运行检查点系统演示"""
    logger.info("开始检查点系统演示")
    
    try:
        # 1. 创建检查点管理器
        logger.info("\n=== 1. 创建检查点管理器 ===")
        providers = [
            MemoryProvider(),
            FileProvider("./demo_checkpoints")
        ]
        manager = CheckpointManager(
            providers=providers,
            enable_deduplication=True,
            max_checkpoints=50
        )
        
        # 2. 创建检查点
        logger.info("\n=== 2. 创建检查点 ===")
        
        # Agent状态示例
        agent_state = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            "context": {
                "task_id": "task_123",
                "step": 5,
                "variables": {"name": "Alice", "age": 30}
            },
            "memory": ["item1", "item2", "item3"]
        }
        
        checkpoint = await manager.create_checkpoint(
            name="agent_session_001",
            state=agent_state,
            description="Agent会话状态快照",
            tags=["agent", "session", "demo"]
        )
        
        print(f"创建检查点: {checkpoint.metadata.checkpoint_id}")
        print(f"检查点名称: {checkpoint.metadata.name}")
        print(f"标签: {checkpoint.metadata.tags}")
        
        # 3. 保存检查点
        logger.info("\n=== 3. 保存检查点 ===")
        success = await manager.save_checkpoint(checkpoint)
        print(f"保存结果: {'成功' if success else '失败'}")
        
        # 4. 恢复检查点
        logger.info("\n=== 4. 恢复检查点 ===")
        restored = await manager.restore_checkpoint(checkpoint.metadata.checkpoint_id)
        
        if restored:
            print(f"恢复成功!")
            print(f"恢复的状态 - messages: {len(restored.state['messages'])}")
            print(f"恢复的状态 - context: {restored.state['context']}")
        
        # 5. 列出检查点
        logger.info("\n=== 5. 列出检查点 ===")
        all_checkpoints = await manager.list_checkpoints()
        print(f"总检查点数: {len(all_checkpoints)}")
        
        for cp in all_checkpoints:
            print(f"  - {cp.name} ({cp.checkpoint_id}) - {cp.status.value}")
        
        # 6. 统计信息
        logger.info("\n=== 6. 统计信息 ===")
        stats = manager.get_stats()
        print(f"创建检查点数: {stats['checkpoints_created']}")
        print(f"恢复检查点数: {stats['checkpoints_restored']}")
        print(f"去重次数: {stats['deduplications']}")
        print(f"总保存时间: {stats['total_save_time_ms']:.2f}ms")
        
        # 7. 多提供者演示
        logger.info("\n=== 7. 多提供者演示 ===")
        
        # 添加Redis提供者
        redis_provider = RedisProvider(host="redis.local", port=6379)
        manager.add_provider(redis_provider)
        
        # 保存到所有提供者
        checkpoint2 = await manager.create_checkpoint(
            name="redis_demo",
            state={"test": "data"}
        )
        await manager.save_checkpoint(checkpoint2)
        
        print(f"检查点已保存到多个提供者")
        
        # 8. 清理演示
        logger.info("\n=== 8. 清理演示 ===")
        await manager.delete_checkpoint(checkpoint.metadata.checkpoint_id)
        print(f"检查点已删除")
        
        # 再次列出
        remaining = await manager.list_checkpoints()
        print(f"剩余检查点数: {len(remaining)}")
        
        logger.info("\n=== 演示完成 ===")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {str(e)}")
        raise


# ============================================================================
# 性能基准测试
# ============================================================================

async def run_benchmark() -> Dict[str, Any]:
    """运行性能基准测试"""
    logger.info("开始性能基准测试")
    
    results = {}
    
    try:
        # 1. 检查点创建性能测试
        logger.info("1. 检查点创建性能测试...")
        
        manager = CheckpointManager(providers=[MemoryProvider()])
        
        start = time.time()
        for i in range(100):
            state = {"index": i, "data": "x" * 100}
            checkpoint = await manager.create_checkpoint(
                name=f"bench_{i}",
                state=state
            )
            await manager.save_checkpoint(checkpoint)
        
        duration = (time.time() - start) * 1000
        results["checkpoint_creation"] = {
            "iterations": 100,
            "total_ms": duration,
            "avg_ms": duration / 100
        }
        
        # 2. 检查点恢复性能测试
        logger.info("2. 检查点恢复性能测试...")
        
        checkpoints = await manager.list_checkpoints(limit=50)
        
        start = time.time()
        for cp in checkpoints:
            await manager.restore_checkpoint(cp.checkpoint_id)
        
        duration = (time.time() - start) * 1000
        results["checkpoint_restore"] = {
            "iterations": len(checkpoints),
            "total_ms": duration,
            "avg_ms": duration / len(checkpoints) if checkpoints else 0
        }
        
        # 3. 检查点列表性能测试
        logger.info("3. 检查点列表性能测试...")
        
        start = time.time()
        for _ in range(50):
            await manager.list_checkpoints()
        
        duration = (time.time() - start) * 1000
        results["checkpoint_listing"] = {
            "iterations": 50,
            "total_ms": duration,
            "avg_ms": duration / 50
        }
        
        logger.info("性能基准测试完成")
        
        # 打印结果
        logger.info("\n性能基准测试结果:")
        for test_name, result in results.items():
            logger.info(f"  {test_name}: {result['avg_ms']:.4f}ms/次")
        
        return results
        
    except Exception as e:
        logger.error(f"性能基准测试失败: {str(e)}")
        raise


# ============================================================================
# 主函数
# ============================================================================

async def main() -> None:
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="检查点系统演示程序")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--bench", action="store_true", help="运行性能基准测试")
    
    args = parser.parse_args()
    
    if not any([args.test, args.demo, args.bench]):
        args.demo = True
    
    try:
        if args.test:
            logger.info("运行测试套件...")
            results = await TestCheckpointing.run_all_tests()
            
            all_passed = all(results.values())
            if all_passed:
                logger.info("✅ 所有测试通过!")
                return 0
            else:
                logger.error("❌ 部分测试失败:")
                for test_name, passed in results.items():
                    status = "✅" if passed else "❌"
                    logger.error(f"  {status} {test_name}")
                return 1
        
        if args.demo:
            logger.info("运行演示...")
            await run_demo()
            logger.info("✅ 演示完成!")
            return 0
        
        if args.bench:
            logger.info("运行性能基准测试...")
            results = await run_benchmark()
            logger.info("✅ 性能基准测试完成!")
            return 0
    
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        return 130
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)