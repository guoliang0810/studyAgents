#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeerFlow Python Agent架构师训练营 - 第78节课：检查点提供者 演示代码

本文件演示了检查点提供者（Checkpoint Provider）的完整实现，包括：
1. CheckpointProvider抽象基类：定义存储接口
2. FileSystemCheckpointProvider：文件系统存储实现
3. DatabaseCheckpointProvider：数据库存储实现（SQLAlchemy）
4. InMemoryCheckpointProvider：内存存储实现
5. 完整测试套件：验证所有提供者功能

学习目标：
- 掌握CheckpointProvider抽象接口的设计原则
- 实现基于文件系统的检查点存储和加载
- 实现基于数据库的检查点持久化
- 设计检查点数据的序列化和反序列化策略
- 处理检查点数据的完整性和一致性保证

使用方式：
python checkpoint_provider_demo.py          # 运行演示
python checkpoint_provider_demo.py --test   # 运行测试套件
python checkpoint_provider_demo.py --bench  # 运行性能基准测试
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
from collections import OrderedDict
import copy
import base64
import shutil
import tempfile
import sqlite3
from pathlib import Path

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
    RESTORING = "restoring"   # 恢复中
    FAILED = "failed"         # 失败
    DELETED = "deleted"       # 已删除


class StorageBackend(Enum):
    """存储后端类型"""
    MEMORY = "memory"         # 内存存储
    FILE = "file"             # 文件存储
    DATABASE = "database"     # 数据库存储
    REDIS = "redis"           # Redis存储


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class CheckpointMetadata:
    """检查点元数据"""
    checkpoint_id: str                        # 检查点ID
    name: str                                 # 检查点名称
    description: Optional[str] = None          # 描述
    tags: List[str] = field(default_factory=list)  # 标签
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间
    size_bytes: int = 0                        # 大小（字节）
    checksum: Optional[str] = None             # 校验和
    status: CheckpointStatus = CheckpointStatus.CREATING  # 状态
    version: int = 1                          # 版本号
    parent_id: Optional[str] = None            # 父检查点ID
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
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
        """从字典创建"""
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
    """检查点"""
    metadata: CheckpointMetadata
    state: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "metadata": self.metadata.to_dict(),
            "state": self.state
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """从字典创建"""
        return cls(
            metadata=CheckpointMetadata.from_dict(data["metadata"]),
            state=data["state"]
        )


# ============================================================================
# CheckpointProvider抽象基类
# ============================================================================

class CheckpointProvider(ABC):
    """检查点提供者抽象基类
    
    定义检查点存储的抽象接口，支持多种存储后端实现。
    子类需要实现save、load、delete、list、exists方法。
    """
    
    @abstractmethod
    async def save(self, checkpoint: Checkpoint) -> None:
        """保存检查点
        
        Args:
            checkpoint: 要保存的检查点对象
        """
        pass
    
    @abstractmethod
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """加载检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            加载的检查点对象，如果不存在则返回None
        """
        pass
    
    @abstractmethod
    async def delete(self, checkpoint_id: str) -> bool:
        """删除检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            是否成功删除
        """
        pass
    
    @abstractmethod
    async def list(self) -> List[str]:
        """列出所有检查点ID
        
        Returns:
            检查点ID列表
        """
        pass
    
    @abstractmethod
    async def exists(self, checkpoint_id: str) -> bool:
        """检查检查点是否存在
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            是否存在
        """
        pass


# ============================================================================
# 文件系统检查点提供者
# ============================================================================

class FileSystemCheckpointProvider(CheckpointProvider):
    """文件系统检查点提供者
    
    使用文件系统存储检查点，目录结构：
    base_dir/
        checkpoint_id/
            state.json      # 状态数据
            metadata.json   # 元数据
            checkpoint.json # 检查点信息（含校验和）
    """
    
    def __init__(self, base_dir: str = "checkpoints"):
        """初始化文件系统提供者
        
        Args:
            base_dir: 检查点存储根目录
        """
        self.base_dir = Path(base_dir)
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """确保存储目录存在"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_checkpoint_dir(self, checkpoint_id: str) -> Path:
        """获取检查点目录"""
        return self.base_dir / checkpoint_id
    
    def _compute_checksum(self, data: bytes) -> str:
        """计算数据校验和"""
        return hashlib.sha256(data).hexdigest()
    
    async def save(self, checkpoint: Checkpoint) -> None:
        """保存检查点到文件系统
        
        Args:
            checkpoint: 要保存的检查点
        """
        checkpoint_dir = self._get_checkpoint_dir(checkpoint.metadata.checkpoint_id)
        
        # 创建检查点目录
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # 序列化状态数据
        state_json = json.dumps(checkpoint.state, ensure_ascii=False, indent=2)
        state_bytes = state_json.encode('utf-8')
        
        # 计算校验和
        checksum = self._compute_checksum(state_bytes)
        checkpoint.metadata.checksum = checksum
        checkpoint.metadata.size_bytes = len(state_bytes)
        
        # 序列化元数据
        metadata_json = json.dumps(
            checkpoint.metadata.to_dict(), 
            ensure_ascii=False, 
            indent=2
        )
        
        # 保存三个文件
        # 1. 状态文件
        state_file = checkpoint_dir / "state.json"
        state_file.write_text(state_json, encoding='utf-8')
        
        # 2. 元数据文件
        metadata_file = checkpoint_dir / "metadata.json"
        metadata_file.write_text(metadata_json, encoding='utf-8')
        
        # 3. 检查点信息文件（包含校验和）
        checkpoint_info = {
            "checkpoint_id": checkpoint.metadata.checkpoint_id,
            "name": checkpoint.metadata.name,
            "checksum": checksum,
            "size_bytes": len(state_bytes),
            "created_at": checkpoint.metadata.created_at.isoformat(),
            "version": checkpoint.metadata.version
        }
        checkpoint_file = checkpoint_dir / "checkpoint.json"
        checkpoint_file.write_text(
            json.dumps(checkpoint_info, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        
        checkpoint.metadata.status = CheckpointStatus.AVAILABLE
        checkpoint.metadata.updated_at = datetime.now()
        
        logger.info(f"检查点已保存: {checkpoint.metadata.checkpoint_id}")
    
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """从文件系统加载检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            加载的检查点对象
        """
        checkpoint_dir = self._get_checkpoint_dir(checkpoint_id)
        
        if not checkpoint_dir.exists():
            logger.warning(f"检查点目录不存在: {checkpoint_id}")
            return None
        
        try:
            # 读取检查点信息
            checkpoint_file = checkpoint_dir / "checkpoint.json"
            if not checkpoint_file.exists():
                logger.error(f"检查点信息文件不存在: {checkpoint_file}")
                return None
            
            checkpoint_info = json.loads(checkpoint_file.read_text(encoding='utf-8'))
            
            # 验证校验和
            state_file = checkpoint_dir / "state.json"
            state_bytes = state_file.read_bytes()
            actual_checksum = self._compute_checksum(state_bytes)
            
            if actual_checksum != checkpoint_info.get("checksum"):
                logger.error(f"检查点校验失败: {checkpoint_id}")
                raise ValueError(f"检查点数据损坏: {checkpoint_id}")
            
            # 加载状态
            state = json.loads(state_file.read_text(encoding='utf-8'))
            
            # 加载元数据
            metadata_file = checkpoint_dir / "metadata.json"
            metadata = CheckpointMetadata.from_dict(
                json.loads(metadata_file.read_text(encoding='utf-8'))
            )
            
            logger.info(f"检查点已加载: {checkpoint_id}")
            return Checkpoint(metadata=metadata, state=state)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {checkpoint_id}, {e}")
            return None
        except Exception as e:
            logger.error(f"加载检查点失败: {checkpoint_id}, {e}")
            return None
    
    async def delete(self, checkpoint_id: str) -> bool:
        """从文件系统删除检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            是否成功删除
        """
        checkpoint_dir = self._get_checkpoint_dir(checkpoint_id)
        
        if not checkpoint_dir.exists():
            logger.warning(f"检查点目录不存在: {checkpoint_id}")
            return False
        
        try:
            shutil.rmtree(checkpoint_dir)
            logger.info(f"检查点已删除: {checkpoint_id}")
            return True
        except Exception as e:
            logger.error(f"删除检查点失败: {checkpoint_id}, {e}")
            return False
    
    async def list(self) -> List[str]:
        """列出所有检查点ID
        
        Returns:
            检查点ID列表
        """
        if not self.base_dir.exists():
            return []
        
        checkpoint_ids = []
        for item in self.base_dir.iterdir():
            if item.is_dir():
                # 检查是否是有效的检查点目录
                if (item / "checkpoint.json").exists():
                    checkpoint_ids.append(item.name)
        
        # 按创建时间排序
        checkpoint_ids.sort(
            key=lambda x: self._get_checkpoint_dir(x).stat().st_mtime,
            reverse=True
        )
        
        return checkpoint_ids
    
    async def exists(self, checkpoint_id: str) -> bool:
        """检查检查点是否存在
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            是否存在
        """
        checkpoint_dir = self._get_checkpoint_dir(checkpoint_id)
        return checkpoint_dir.exists() and (checkpoint_dir / "checkpoint.json").exists()


# ============================================================================
# 数据库检查点提供者
# ============================================================================

class DatabaseCheckpointProvider(CheckpointProvider):
    """数据库检查点提供者
    
    使用SQLite数据库存储检查点，支持完整的SQL查询能力。
    """
    
    def __init__(self, db_path: str = "checkpoints.db"):
        """初始化数据库提供者
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self) -> None:
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建检查点表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                state_data TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                size_bytes INTEGER DEFAULT 0,
                checksum TEXT,
                status TEXT DEFAULT 'available',
                version INTEGER DEFAULT 1,
                parent_id TEXT,
                extra_metadata TEXT
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoints_name 
            ON checkpoints(name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoints_created 
            ON checkpoints(created_at)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"数据库初始化完成: {self.db_path}")
    
    def _compute_checksum(self, data: str) -> str:
        """计算数据校验和"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
    
    async def save(self, checkpoint: Checkpoint) -> None:
        """保存检查点到数据库
        
        Args:
            checkpoint: 要保存的检查点
        """
        # 序列化状态数据
        state_json = json.dumps(checkpoint.state, ensure_ascii=False)
        checkpoint.metadata.size_bytes = len(state_json)
        checkpoint.metadata.checksum = self._compute_checksum(state_json)
        
        # 序列化元数据
        metadata_json = json.dumps(checkpoint.metadata.to_dict(), ensure_ascii=False)
        
        # 序列化标签
        tags_json = json.dumps(checkpoint.metadata.tags)
        
        # 序列化额外元数据
        extra_metadata_json = json.dumps(checkpoint.metadata.metadata)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO checkpoints 
            (checkpoint_id, name, description, tags, state_data, metadata_json,
             created_at, updated_at, size_bytes, checksum, status, version,
             parent_id, extra_metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            checkpoint.metadata.checkpoint_id,
            checkpoint.metadata.name,
            checkpoint.metadata.description,
            tags_json,
            state_json,
            metadata_json,
            checkpoint.metadata.created_at.isoformat(),
            datetime.now().isoformat(),
            checkpoint.metadata.size_bytes,
            checkpoint.metadata.checksum,
            checkpoint.metadata.status.value,
            checkpoint.metadata.version,
            checkpoint.metadata.parent_id,
            extra_metadata_json
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"检查点已保存到数据库: {checkpoint.metadata.checkpoint_id}")
    
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """从数据库加载检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            加载的检查点对象
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT state_data, metadata_json, checksum
            FROM checkpoints 
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            logger.warning(f"检查点不存在: {checkpoint_id}")
            return None
        
        state_json, metadata_json, stored_checksum = row
        
        # 验证校验和
        actual_checksum = self._compute_checksum(state_json)
        if actual_checksum != stored_checksum:
            logger.error(f"检查点校验失败: {checkpoint_id}")
            raise ValueError(f"检查点数据损坏: {checkpoint_id}")
        
        # 反序列化
        state = json.loads(state_json)
        metadata = CheckpointMetadata.from_dict(json.loads(metadata_json))
        
        logger.info(f"检查点已从数据库加载: {checkpoint_id}")
        return Checkpoint(metadata=metadata, state=state)
    
    async def delete(self, checkpoint_id: str) -> bool:
        """从数据库删除检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            是否成功删除
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM checkpoints 
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if deleted:
            logger.info(f"检查点已从数据库删除: {checkpoint_id}")
        else:
            logger.warning(f"检查点不存在，无法删除: {checkpoint_id}")
        
        return deleted
    
    async def list(self) -> List[str]:
        """列出所有检查点ID
        
        Returns:
            检查点ID列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT checkpoint_id FROM checkpoints 
            ORDER BY created_at DESC
        """)
        
        ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return ids
    
    async def exists(self, checkpoint_id: str) -> bool:
        """检查检查点是否存在
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            是否存在
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 1 FROM checkpoints 
            WHERE checkpoint_id = ? LIMIT 1
        """, (checkpoint_id,))
        
        exists = cursor.fetchone() is not None
        conn.close()
        
        return exists
    
    async def list_by_name(self, name: str) -> List[str]:
        """根据名称列出检查点
        
        Args:
            name: 检查点名称
            
        Returns:
            检查点ID列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT checkpoint_id FROM checkpoints 
            WHERE name = ?
            ORDER BY version DESC
        """, (name,))
        
        ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return ids


# ============================================================================
# 内存检查点提供者
# ============================================================================

class InMemoryCheckpointProvider(CheckpointProvider):
    """内存检查点提供者
    
    使用内存存储检查点，支持LRU缓存淘汰策略。
    适用于临时存储或测试环境。
    """
    
    def __init__(self, max_size: int = 100):
        """初始化内存提供者
        
        Args:
            max_size: 最大检查点数量
        """
        self.max_size = max_size
        self._checkpoints: OrderedDict[str, Checkpoint] = OrderedDict()
    
    async def save(self, checkpoint: Checkpoint) -> None:
        """保存检查点到内存
        
        Args:
            checkpoint: 要保存的检查点
        """
        checkpoint_id = checkpoint.metadata.checkpoint_id
        
        # 如果已存在，移除旧的
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
        
        # 添加新的检查点
        self._checkpoints[checkpoint_id] = checkpoint
        
        # LRU淘汰：如果超过最大数量，移除最早的
        while len(self._checkpoints) > self.max_size:
            oldest_id = next(iter(self._checkpoints))
            del self._checkpoints[oldest_id]
            logger.debug(f"LRU淘汰检查点: {oldest_id}")
        
        # 更新元数据
        checkpoint.metadata.status = CheckpointStatus.AVAILABLE
        checkpoint.metadata.updated_at = datetime.now()
        
        logger.info(f"检查点已保存到内存: {checkpoint_id}")
    
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """从内存加载检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            加载的检查点对象
        """
        if checkpoint_id not in self._checkpoints:
            logger.warning(f"检查点不存在: {checkpoint_id}")
            return None
        
        # LRU：移动到末尾表示最近使用
        checkpoint = self._checkpoints[checkpoint_id]
        self._checkpoints.move_to_end(checkpoint_id)
        
        logger.info(f"检查点已从内存加载: {checkpoint_id}")
        return checkpoint
    
    async def delete(self, checkpoint_id: str) -> bool:
        """从内存删除检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            是否成功删除
        """
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            logger.info(f"检查点已从内存删除: {checkpoint_id}")
            return True
        
        logger.warning(f"检查点不存在，无法删除: {checkpoint_id}")
        return False
    
    async def list(self) -> List[str]:
        """列出所有检查点ID
        
        Returns:
            检查点ID列表
        """
        # 返回最近使用的排在前面
        return list(reversed(list(self._checkpoints.keys())))
    
    async def exists(self, checkpoint_id: str) -> bool:
        """检查检查点是否存在
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            是否存在
        """
        return checkpoint_id in self._checkpoints
    
    def size(self) -> int:
        """获取当前存储的检查点数量
        
        Returns:
            检查点数量
        """
        return len(self._checkpoints)
    
    def clear(self) -> None:
        """清空所有检查点"""
        self._checkpoints.clear()
        logger.info("内存检查点已清空")


# ============================================================================
# 检查点管理器（整合所有提供者）
# ============================================================================

class CheckpointManager:
    """检查点管理器
    
    整合所有检查点提供者，提供统一的检查点管理接口。
    """
    
    def __init__(self, provider: CheckpointProvider):
        """初始化检查点管理器
        
        Args:
            provider: 检查点存储提供者
        """
        self.provider = provider
    
    async def create_checkpoint(
        self,
        name: str,
        state: Dict[str, Any],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Checkpoint:
        """创建新检查点
        
        Args:
            name: 检查点名称
            state: 状态数据
            description: 描述
            tags: 标签
            
        Returns:
            创建的检查点
        """
        # 生成唯一ID
        checkpoint_id = f"{name}-{uuid.uuid4().hex[:8]}"
        
        # 获取已有版本号
        existing = await self.provider.list()
        version = 1
        for existing_id in existing:
            if existing_id.startswith(f"{name}-"):
                version += 1
        
        # 创建元数据
        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            name=name,
            description=description,
            tags=tags or [],
            status=CheckpointStatus.CREATING,
            version=version
        )
        
        # 创建检查点
        checkpoint = Checkpoint(metadata=metadata, state=state)
        
        # 保存
        await self.save_checkpoint(checkpoint)
        
        return checkpoint
    
    async def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """保存检查点
        
        Args:
            checkpoint: 要保存的检查点
        """
        await self.provider.save(checkpoint)
    
    async def restore_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """恢复检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            恢复的检查点
        """
        checkpoint = await self.provider.load(checkpoint_id)
        
        if checkpoint:
            checkpoint.metadata.status = CheckpointStatus.AVAILABLE
            checkpoint.metadata.updated_at = datetime.now()
        
        return checkpoint
    
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """删除检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            是否成功删除
        """
        return await self.provider.delete(checkpoint_id)
    
    async def list_checkpoints(self) -> List[Checkpoint]:
        """列出所有检查点
        
        Returns:
            检查点列表
        """
        checkpoint_ids = await self.provider.list()
        checkpoints = []
        
        for checkpoint_id in checkpoint_ids:
            checkpoint = await self.provider.load(checkpoint_id)
            if checkpoint:
                checkpoints.append(checkpoint)
        
        return checkpoints
    
    async def get_checkpoint_info(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """获取检查点信息
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            检查点信息字典
        """
        checkpoint = await self.provider.load(checkpoint_id)
        
        if not checkpoint:
            return None
        
        return {
            "checkpoint_id": checkpoint.metadata.checkpoint_id,
            "name": checkpoint.metadata.name,
            "description": checkpoint.metadata.description,
            "tags": checkpoint.metadata.tags,
            "version": checkpoint.metadata.version,
            "created_at": checkpoint.metadata.created_at.isoformat(),
            "updated_at": checkpoint.metadata.updated_at.isoformat(),
            "size_bytes": checkpoint.metadata.size_bytes,
            "status": checkpoint.metadata.status.value,
            "checksum": checkpoint.metadata.checksum
        }


# ============================================================================
# 测试用例
# ============================================================================

async def test_filesystem_provider():
    """测试文件系统提供者"""
    print("\n=== 测试文件系统提供者 ===")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    provider = FileSystemCheckpointProvider(temp_dir)
    manager = CheckpointManager(provider)
    
    # 创建检查点
    checkpoint = await manager.create_checkpoint(
        name="test-fs",
        state={"counter": 42, "items": [1, 2, 3]},
        description="测试检查点",
        tags=["test"]
    )
    print(f"✓ 创建检查点: {checkpoint.metadata.checkpoint_id}")
    
    # 验证存在
    exists = await provider.exists(checkpoint.metadata.checkpoint_id)
    assert exists, "检查点应该存在"
    print(f"✓ 检查点存在验证通过")
    
    # 列出检查点
    ids = await provider.list()
    assert len(ids) == 1, "应该有1个检查点"
    print(f"✓ 列出检查点: {ids}")
    
    # 加载检查点
    loaded = await manager.restore_checkpoint(checkpoint.metadata.checkpoint_id)
    assert loaded is not None, "应该能加载检查点"
    assert loaded.state["counter"] == 42, "状态应该正确"
    print(f"✓ 加载检查点成功，状态: {loaded.state}")
    
    # 删除检查点
    deleted = await manager.delete_checkpoint(checkpoint.metadata.checkpoint_id)
    assert deleted, "应该成功删除"
    print(f"✓ 删除检查点成功")
    
    # 清理
    shutil.rmtree(temp_dir)
    print("✓ 文件系统提供者测试通过")


async def test_database_provider():
    """测试数据库提供者"""
    print("\n=== 测试数据库提供者 ===")
    
    # 创建临时数据库
    temp_db = tempfile.mktemp(suffix=".db")
    provider = DatabaseCheckpointProvider(temp_db)
    manager = CheckpointManager(provider)
    
    # 创建多个检查点
    for i in range(3):
        checkpoint = await manager.create_checkpoint(
            name="test-db",
            state={"index": i, "data": f"data-{i}"},
            description=f"测试检查点 {i}"
        )
        print(f"✓ 创建检查点 {i}: {checkpoint.metadata.checkpoint_id}")
    
    # 列出检查点
    ids = await provider.list()
    assert len(ids) == 3, "应该有3个检查点"
    print(f"✓ 列出所有检查点: {len(ids)} 个")
    
    # 按名称查询
    name_ids = await provider.list_by_name("test-db")
    assert len(name_ids) == 3, "名称查询应该返回3个"
    print(f"✓ 按名称查询: {len(name_ids)} 个")
    
    # 加载最新检查点
    loaded = await manager.restore_checkpoint(ids[0])
    assert loaded is not None, "应该能加载检查点"
    print(f"✓ 加载检查点: {loaded.state}")
    
    # 删除检查点
    deleted = await manager.delete_checkpoint(ids[0])
    assert deleted, "应该成功删除"
    
    ids = await provider.list()
    assert len(ids) == 2, "删除后应该有2个"
    print(f"✓ 删除后剩余: {len(ids)} 个")
    
    # 清理
    os.remove(temp_db)
    print("✓ 数据库提供者测试通过")


async def test_memory_provider():
    """测试内存提供者"""
    print("\n=== 测试内存提供者 ===")
    
    provider = InMemoryCheckpointProvider(max_size=3)
    manager = CheckpointManager(provider)
    
    # 创建多个检查点（超过max_size触发LRU）
    for i in range(5):
        checkpoint = await manager.create_checkpoint(
            name="test-memory",
            state={"index": i},
            description=f"检查点 {i}"
        )
        print(f"✓ 创建检查点 {i}: {checkpoint.metadata.checkpoint_id}")
    
    # 验证LRU淘汰
    ids = await provider.list()
    assert len(ids) == 3, "应该保留3个检查点（LRU淘汰）"
    print(f"✓ LRU保留检查点: {len(ids)} 个")
    
    # 验证最少使用的被淘汰
    first_checkpoint = await provider.load(ids[-1])
    print(f"✓ 加载检查点后，LRU顺序更新")
    
    # 清空
    provider.clear()
    ids = await provider.list()
    assert len(ids) == 0, "清空后应该没有检查点"
    print(f"✓ 清空检查点成功")
    
    print("✓ 内存提供者测试通过")


async def test_integration():
    """测试集成场景"""
    print("\n=== 测试集成场景 ===")
    
    # 使用内存提供者（快速）
    provider = InMemoryCheckpointProvider()
    manager = CheckpointManager(provider)
    
    # 场景：保存工作进度
    print("场景：保存工作进度")
    
    # 初始状态
    state = {
        "task": "数据分析",
        "progress": 0,
        "results": [],
        "errors": []
    }
    
    # 创建第一个检查点
    cp1 = await manager.create_checkpoint(
        name="work-progress",
        state=state,
        description="工作进度1"
    )
    print(f"✓ 创建初始检查点: {cp1.metadata.checkpoint_id}")
    
    # 模拟工作进度
    state["progress"] = 25
    state["results"] = ["step1 done"]
    
    cp2 = await manager.create_checkpoint(
        name="work-progress",
        state=state,
        description="工作进度2"
    )
    print(f"✓ 创建进度检查点: {cp2.metadata.checkpoint_id}")
    
    # 模拟工作进度
    state["progress"] = 50
    state["results"] = ["step1 done", "step2 done"]
    
    cp3 = await manager.create_checkpoint(
        name="work-progress",
        state=state,
        description="工作进度3"
    )
    print(f"✓ 创建进度检查点: {cp3.metadata.checkpoint_id}")
    
    # 列出所有检查点
    checkpoints = await manager.list_checkpoints()
    print(f"✓ 共创建 {len(checkpoints)} 个检查点")
    
    # 恢复到第二个检查点
    restored = await manager.restore_checkpoint(cp2.metadata.checkpoint_id)
    print(f"✓ 恢复到检查点2，进度: {restored.state['progress']}%")
    
    print("✓ 集成场景测试通过")


async def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("开始运行检查点提供者测试套件")
    print("=" * 50)
    
    try:
        await test_filesystem_provider()
        await test_database_provider()
        await test_memory_provider()
        await test_integration()
        
        print("\n" + "=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# 性能基准测试
# ============================================================================

async def benchmark_providers():
    """基准测试不同提供者"""
    print("\n" + "=" * 50)
    print("性能基准测试")
    print("=" * 50)
    
    test_state = {
        "data": list(range(10000)),
        "nested": {"key": "value" * 100},
        "items": [{"id": i, "name": f"item-{i}"} for i in range(100)]
    }
    
    # 测试内存提供者
    print("\n--- 内存提供者 ---")
    provider = InMemoryCheckpointProvider()
    manager = CheckpointManager(provider)
    
    start = time.time()
    for i in range(100):
        await manager.create_checkpoint("bench", test_state)
    memory_time = time.time() - start
    print(f"100次保存: {memory_time:.3f}秒")
    
    # 测试文件系统提供者
    print("\n--- 文件系统提供者 ---")
    temp_dir = tempfile.mkdtemp()
    provider = FileSystemCheckpointProvider(temp_dir)
    manager = CheckpointManager(provider)
    
    start = time.time()
    for i in range(100):
        await manager.create_checkpoint("bench", test_state)
    file_time = time.time() - start
    print(f"100次保存: {file_time:.3f}秒")
    
    # 测试数据库提供者
    print("\n--- 数据库提供者 ---")
    temp_db = tempfile.mktemp(suffix=".db")
    provider = DatabaseCheckpointProvider(temp_db)
    manager = CheckpointManager(provider)
    
    start = time.time()
    for i in range(100):
        await manager.create_checkpoint("bench", test_state)
    db_time = time.time() - start
    print(f"100次保存: {db_time:.3f}秒")
    
    # 总结
    print("\n--- 性能对比 ---")
    print(f"内存: {memory_time:.3f}秒")
    print(f"文件系统: {file_time:.3f}秒")
    print(f"数据库: {db_time:.3f}秒")
    print(f"内存 vs 文件: {file_time/memory_time:.1f}x 更快")
    print(f"内存 vs 数据库: {db_time/memory_time:.1f}x 更快")
    
    # 清理
    shutil.rmtree(temp_dir)
    os.remove(temp_db)


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            # 运行测试
            asyncio.run(run_all_tests())
        elif sys.argv[1] == "--bench":
            # 运行基准测试
            asyncio.run(benchmark_providers())
        else:
            print(f"未知参数: {sys.argv[1]}")
            print("用法:")
            print("  python checkpoint_provider_demo.py      # 运行演示")
            print("  python checkpoint_provider_demo.py --test   # 运行测试")
            print("  python checkpoint_provider_demo.py --bench  # 运行基准测试")
    else:
        # 运行演示
        print("检查点提供者演示")
        print("=" * 50)
        
        asyncio.run(run_all_tests())
        
        print("\n演示完成！")
        print("使用 --test 运行测试，--bench 运行基准测试")


if __name__ == "__main__":
    main()
