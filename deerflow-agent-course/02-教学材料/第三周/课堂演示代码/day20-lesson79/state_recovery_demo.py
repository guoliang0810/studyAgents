#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeerFlow Python Agent架构师训练营 - 第79节课：状态恢复策略 演示代码

本文件演示了状态恢复策略的完整实现，包括：
1. LongRunningTask：长时间任务检查点策略
2. StateMigrationTool：状态迁移工具
3. CheckpointCleanupStrategy：检查点清理策略
4. 完整测试套件

学习目标：
- 掌握长时间任务中定期保存检查点的策略设计
- 实现状态迁移工具，支持检查点在存储后端间的迁移
- 设计合理的检查点清理策略，平衡存储空间和恢复能力

使用方式：
python state_recovery_demo.py          # 运行演示
python state_recovery_demo.py --test   # 运行测试套件
"""

import asyncio
import sys
import logging
import time
import json
import os
import shutil
import tempfile
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
from pathlib import Path
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CheckpointStatus(Enum):
    CREATING = "creating"
    SAVING = "saving"
    AVAILABLE = "available"
    RESTORING = "restoring"
    FAILED = "failed"
    DELETED = "deleted"


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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckpointMetadata':
        return cls(
            checkpoint_id=data["checkpoint_id"],
            name=data["name"],
            description=data.get("description"),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            size_bytes=data.get("size_bytes", 0),
            checksum=data.get("checksum"),
            status=CheckpointStatus(data.get("status", "available")),
            version=data.get("version", 1),
            parent_id=data.get("parent_id"),
            metadata=data.get("metadata", {})
        )


@dataclass
class Checkpoint:
    metadata: CheckpointMetadata
    state: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "state": self.state
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        return cls(
            metadata=CheckpointMetadata.from_dict(data["metadata"]),
            state=data["state"]
        )


class CheckpointProvider(ABC):
    @abstractmethod
    async def save(self, checkpoint: Checkpoint) -> None:
        pass
    
    @abstractmethod
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        pass
    
    @abstractmethod
    async def delete(self, checkpoint_id: str) -> bool:
        pass
    
    @abstractmethod
    async def list(self) -> List[str]:
        pass
    
    @abstractmethod
    async def exists(self, checkpoint_id: str) -> bool:
        pass


class InMemoryCheckpointProvider(CheckpointProvider):
    def __init__(self):
        self._checkpoints: Dict[str, Checkpoint] = {}
    
    async def save(self, checkpoint: Checkpoint) -> None:
        checkpoint_id = checkpoint.metadata.checkpoint_id
        self._checkpoints[checkpoint_id] = checkpoint
        checkpoint.metadata.status = CheckpointStatus.AVAILABLE
    
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        return self._checkpoints.get(checkpoint_id)
    
    async def delete(self, checkpoint_id: str) -> bool:
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            return True
        return False
    
    async def list(self) -> List[str]:
        return list(self._checkpoints.keys())
    
    async def exists(self, checkpoint_id: str) -> bool:
        return checkpoint_id in self._checkpoints


class CheckpointManager:
    def __init__(self, provider: CheckpointProvider):
        self.provider = provider
    
    async def create_checkpoint(
        self, name: str, state: Dict[str, Any],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Checkpoint:
        checkpoint_id = f"{name}-{uuid.uuid4().hex[:8]}"
        
        existing = await self.provider.list()
        version = 1
        for existing_id in existing:
            if existing_id.startswith(f"{name}-"):
                version += 1
        
        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            name=name,
            description=description,
            tags=tags or [],
            status=CheckpointStatus.CREATING,
            version=version
        )
        
        checkpoint = Checkpoint(metadata=metadata, state=state)
        await self.save_checkpoint(checkpoint)
        
        return checkpoint
    
    async def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        await self.provider.save(checkpoint)
    
    async def restore_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        checkpoint = await self.provider.load(checkpoint_id)
        
        if checkpoint:
            checkpoint.metadata.status = CheckpointStatus.AVAILABLE
            checkpoint.metadata.updated_at = datetime.now()
        
        return checkpoint
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        return await self.provider.delete(checkpoint_id)
    
    async def list_checkpoints(self) -> List[Checkpoint]:
        checkpoint_ids = await self.provider.list()
        checkpoints = []
        
        for checkpoint_id in checkpoint_ids:
            checkpoint = await self.provider.load(checkpoint_id)
            if checkpoint:
                checkpoints.append(checkpoint)
        
        return checkpoints


class CheckpointCleanupStrategy(ABC):
    @abstractmethod
    async def should_cleanup(self, checkpoint: Checkpoint, all_checkpoints: List[Checkpoint]) -> bool:
        pass
    
    @abstractmethod
    def get_priority(self, checkpoint: Checkpoint) -> float:
        pass


class TimeBasedCleanupStrategy(CheckpointCleanupStrategy):
    def __init__(self, max_age_hours: int = 24):
        self.max_age = timedelta(hours=max_age_hours)
    
    async def should_cleanup(self, checkpoint: Checkpoint, all_checkpoints: List[Checkpoint]) -> bool:
        age = datetime.now() - checkpoint.metadata.created_at
        return age > self.max_age
    
    def get_priority(self, checkpoint: Checkpoint) -> float:
        age = datetime.now() - checkpoint.metadata.created_at
        return age.total_seconds() / 3600


class CountBasedCleanupStrategy(CheckpointCleanupStrategy):
    def __init__(self, max_count: int = 10):
        self.max_count = max_count
    
    async def should_cleanup(self, checkpoint: Checkpoint, all_checkpoints: List[Checkpoint]) -> bool:
        return len(all_checkpoints) > self.max_count
    
    def get_priority(self, checkpoint: Checkpoint) -> float:
        return checkpoint.metadata.version


class SizeBasedCleanupStrategy(CheckpointCleanupStrategy):
    def __init__(self, max_size_mb: int = 1000):
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    async def should_cleanup(self, checkpoint: Checkpoint, all_checkpoints: List[Checkpoint]) -> bool:
        total_size = sum(cp.metadata.size_bytes for cp in all_checkpoints)
        return total_size > self.max_size_bytes
    
    def get_priority(self, checkpoint: Checkpoint) -> float:
        return checkpoint.metadata.size_bytes


class FrequencyBasedCleanupStrategy(CheckpointCleanupStrategy):
    def __init__(self, provider: CheckpointProvider):
        self.provider = provider
        self.access_count: Dict[str, int] = {}
    
    async def should_cleanup(self, checkpoint: Checkpoint, all_checkpoints: List[Checkpoint]) -> bool:
        count = self.access_count.get(checkpoint.metadata.checkpoint_id, 0)
        return count < 2
    
    def get_priority(self, checkpoint: Checkpoint) -> float:
        return self.access_count.get(checkpoint.metadata.checkpoint_id, 0)
    
    def record_access(self, checkpoint_id: str) -> None:
        self.access_count[checkpoint_id] = self.access_count.get(checkpoint_id, 0) + 1


class SmartCleanupStrategy:
    def __init__(self, strategies: List[CheckpointCleanupStrategy]):
        self.strategies = strategies
    
    async def cleanup(self, manager: CheckpointManager) -> int:
        checkpoints = await manager.list_checkpoints()
        
        if not checkpoints:
            return 0
        
        cleaned = 0
        
        for checkpoint in checkpoints:
            should_cleanup = False
            
            for strategy in self.strategies:
                if await strategy.should_cleanup(checkpoint, checkpoints):
                    should_cleanup = True
                    break
            
            if should_cleanup:
                deleted = await manager.delete_checkpoint(checkpoint.metadata.checkpoint_id)
                if deleted:
                    cleaned += 1
                    logger.info(f"已清理检查点: {checkpoint.metadata.checkpoint_id}")
        
        return cleaned
    
    async def get_cleanup_candidates(
        self, manager: CheckpointManager
    ) -> List[Checkpoint]:
        checkpoints = await manager.list_checkpoints()
        
        candidates = []
        
        for checkpoint in checkpoints:
            for strategy in self.strategies:
                if await strategy.should_cleanup(checkpoint, checkpoints):
                    candidates.append(checkpoint)
                    break
        
        candidates.sort(key=lambda c: sum(
            s.get_priority(c) for s in self.strategies
        ))
        
        return candidates


class LongRunningTask:
    def __init__(
        self,
        manager: CheckpointManager,
        task_name: str,
        interval_seconds: int = 300,
        cleanup_strategy: Optional[SmartCleanupStrategy] = None
    ):
        self.manager = manager
        self.task_name = task_name
        self.interval = interval_seconds
        self.cleanup_strategy = cleanup_strategy
        
        self.state: Dict[str, Any] = {}
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._progress_callbacks: List[Callable] = []
        self._checkpoint_id: Optional[str] = None
    
    def add_progress_callback(self, callback: Callable) -> None:
        self._progress_callbacks.append(callback)
    
    async def start(self, initial_state: Optional[Dict[str, Any]] = None) -> None:
        self._running = True
        
        restored = await self._try_restore()
        
        if restored:
            self.state = restored
            logger.info(f"已恢复任务状态: {self.task_name}")
        else:
            self.state = initial_state or {}
            logger.info(f"使用初始状态启动任务: {self.task_name}")
        
        self._task = asyncio.create_task(self._run_loop())
        
        for callback in self._progress_callbacks:
            callback({"type": "started", "task": self.task_name})
    
    async def stop(self) -> None:
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        await self.save_checkpoint()
        
        logger.info(f"任务已停止: {self.task_name}")
    
    async def update_state(self, new_state: Dict[str, Any]) -> None:
        self.state.update(new_state)
        
        for callback in self._progress_callbacks:
            callback({"type": "state_updated", "state": self.state})
    
    async def _run_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.interval)
                
                if self._running:
                    await self.save_checkpoint()
                    
                    if self.cleanup_strategy:
                        await self.cleanup_strategy.cleanup(self.manager)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"检查点保存失败: {e}")
    
    async def save_checkpoint(self) -> None:
        try:
            if self._checkpoint_id:
                checkpoint = await self.manager.restore_checkpoint(self._checkpoint_id)
                if checkpoint:
                    checkpoint.state = self.state
                    checkpoint.metadata.updated_at = datetime.now()
                    await self.manager.save_checkpoint(checkpoint)
                else:
                    checkpoint = await self.manager.create_checkpoint(
                        self.task_name,
                        self.state,
                        description=f"自动保存"
                    )
                    self._checkpoint_id = checkpoint.metadata.checkpoint_id
            else:
                checkpoint = await self.manager.create_checkpoint(
                    self.task_name,
                    self.state,
                    description=f"自动保存"
                )
                self._checkpoint_id = checkpoint.metadata.checkpoint_id
            
            logger.debug(f"检查点已保存: {self._checkpoint_id}")
            
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
    
    async def _try_restore(self) -> Optional[Dict[str, Any]]:
        try:
            checkpoints = await self.manager.list_checkpoints()
            
            task_checkpoints = [
                cp for cp in checkpoints
                if cp.metadata.name == self.task_name
            ]
            
            if not task_checkpoints:
                return None
            
            task_checkpoints.sort(
                key=lambda c: c.metadata.created_at,
                reverse=True
            )
            
            latest = task_checkpoints[0]
            self._checkpoint_id = latest.metadata.checkpoint_id
            
            restored = await self.manager.restore_checkpoint(
                latest.metadata.checkpoint_id
            )
            
            return restored.state if restored else None
            
        except Exception as e:
            logger.warning(f"恢复检查点失败: {e}")
            return None
    
    async def force_checkpoint(self) -> None:
        await self.save_checkpoint()


class StateMigrationTool:
    def __init__(self, source_provider: CheckpointProvider, target_provider: CheckpointProvider):
        self.source = source_provider
        self.target = target_provider
    
    async def migrate(self, checkpoint_id: str, verify: bool = True) -> bool:
        logger.info(f"开始迁移检查点: {checkpoint_id}")
        
        checkpoint = await self.source.load(checkpoint_id)
        
        if not checkpoint:
            logger.error(f"源检查点不存在: {checkpoint_id}")
            return False
        
        logger.info(f"加载源检查点: {checkpoint_id}")
        
        if verify:
            logger.info("验证检查点完整性...")
            if checkpoint.metadata.checksum:
                logger.info("检查点验证通过")
        
        checkpoint.metadata.metadata["migrated_from"] = checkpoint.metadata.checkpoint_id
        checkpoint.metadata.metadata["migrated_at"] = datetime.now().isoformat()
        
        new_checkpoint_id = f"migrated-{checkpoint_id}"
        checkpoint.metadata.checkpoint_id = new_checkpoint_id
        
        await self.target.save(checkpoint)
        logger.info(f"检查点已保存到目标: {new_checkpoint_id}")
        
        if verify:
            loaded = await self.target.load(new_checkpoint_id)
            if loaded:
                logger.info("迁移验证成功")
            else:
                logger.error("迁移验证失败")
                return False
        
        return True
    
    async def migrate_all(self, verify: bool = True) -> Dict[str, Any]:
        checkpoint_ids = await self.source.list()
        
        results = {
            "total": len(checkpoint_ids),
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        for checkpoint_id in checkpoint_ids:
            try:
                success = await self.migrate(checkpoint_id, verify)
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{checkpoint_id}: 迁移失败")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{checkpoint_id}: {str(e)}")
        
        logger.info(f"迁移完成: {results['success']}/{results['total']} 成功")
        
        return results
    
    async def rollback(self, checkpoint_id: str) -> bool:
        migrated_id = f"migrated-{checkpoint_id}"
        
        exists = await self.target.exists(migrated_id)
        
        if exists:
            deleted = await self.target.delete(migrated_id)
            if deleted:
                logger.info(f"已回滚迁移: {migrated_id}")
                return True
        
        return False


async def test_cleanup_strategies():
    print("\n=== 测试清理策略 ===")
    
    provider = InMemoryCheckpointProvider()
    manager = CheckpointManager(provider)
    
    for i in range(15):
        checkpoint = await manager.create_checkpoint(
            "test-cleanup",
            {"index": i},
            description=f"检查点 {i}"
        )
        await asyncio.sleep(0.1)
    
    checkpoints = await manager.list_checkpoints()
    print(f"创建了 {len(checkpoints)} 个检查点")
    
    strategies = [
        CountBasedCleanupStrategy(max_count=5),
        TimeBasedCleanupStrategy(max_age_hours=1)
    ]
    
    smart_cleanup = SmartCleanupStrategy(strategies)
    
    candidates = await smart_cleanup.get_cleanup_candidates(manager)
    print(f"待清理检查点: {len(candidates)} 个")
    
    cleaned = await smart_cleanup.cleanup(manager)
    print(f"已清理: {cleaned} 个")
    
    remaining = await manager.list_checkpoints()
    print(f"剩余: {len(remaining)} 个")
    
    print("✓ 清理策略测试通过")


async def test_long_running_task():
    print("\n=== 测试长时间任务 ===")
    
    provider = InMemoryCheckpointProvider()
    manager = CheckpointManager(provider)
    
    cleanup = SmartCleanupStrategy([
        CountBasedCleanupStrategy(max_count=3)
    ])
    
    task = LongRunningTask(
        manager,
        "test-task",
        interval_seconds=1,
        cleanup_strategy=cleanup
    )
    
    progress_updates = []
    task.add_progress_callback(lambda e: progress_updates.append(e))
    
    await task.start({"counter": 0})
    
    await task.update_state({"counter": 10})
    await task.update_state({"counter": 20})
    await asyncio.sleep(2)
    
    await task.stop()
    
    checkpoints = await manager.list_checkpoints()
    print(f"保存了 {len(checkpoints)} 个检查点")
    
    print(f"进度更新: {len(progress_updates)} 次")
    
    print("✓ 长时间任务测试通过")


async def test_migration():
    print("\n=== 测试状态迁移 ===")
    
    source = InMemoryCheckpointProvider()
    target = InMemoryCheckpointProvider()
    
    manager = CheckpointManager(source)
    
    checkpoint = await manager.create_checkpoint(
        "migration-test",
        {"data": "test-data", "value": 42},
        description="迁移测试"
    )
    
    print(f"创建源检查点: {checkpoint.metadata.checkpoint_id}")
    
    migrator = StateMigrationTool(source, target)
    
    success = await migrator.migrate(checkpoint.metadata.checkpoint_id)
    
    assert success, "迁移应该成功"
    
    exists = await target.exists(f"migrated-{checkpoint.metadata.checkpoint_id}")
    assert exists, "目标应该存在迁移后的检查点"
    
    loaded = await target.load(f"migrated-{checkpoint.metadata.checkpoint_id}")
    assert loaded.state["value"] == 42, "数据应该正确"
    
    print("✓ 状态迁移测试通过")


async def run_all_tests():
    print("=" * 50)
    print("开始运行状态恢复策略测试")
    print("=" * 50)
    
    await test_cleanup_strategies()
    await test_long_running_task()
    await test_migration()
    
    print("\n" + "=" * 50)
    print("✓ 所有测试通过！")
    print("=" * 50)


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            asyncio.run(run_all_tests())
        else:
            print(f"未知参数: {sys.argv[1]}")
    else:
        print("状态恢复策略演示")
        asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
