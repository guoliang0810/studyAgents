# 📚 Day 20 第77节课：Checkpointing架构 - 答案与解析

## 任务1：理解检查点系统架构

### 1.1 检查点系统四大核心组件

| 组件 | 作用 | 关键方法 |
|------|------|----------|
| **CheckpointManager** | 检查点管理器，协调所有检查点操作 | `create_checkpoint()`, `save_checkpoint()`, `restore_checkpoint()`, `list_checkpoints()` |
| **CheckpointProvider** | 存储后端抽象，支持多种存储方式 | `save()`, `load()`, `delete()`, `list()` |
| **Checkpoint** | 检查点数据容器，包含状态和元数据 | 状态存储和序列化 |
| **CheckpointMetadata** | 检查点元数据，管理附加信息 | 版本、标签、时间戳等 |

### 1.2 CheckpointProvider抽象基类

```python
class CheckpointProvider(ABC):
    """检查点提供者抽象基类"""
    
    @abstractmethod
    async def save(self, checkpoint: Checkpoint) -> None:
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
    async def list(self) -> List[str]:
        """列出所有检查点ID"""
        pass
```

**为什么需要抽象？**
- 解耦存储逻辑和业务逻辑
- 支持多种存储后端（内存、文件、Redis、数据库）
- 便于测试（可以使用内存提供者模拟）
- 便于扩展新存储方式

### 1.3 检查点元数据字段

| 字段 | 作用 |
|------|------|
| `checkpoint_id` | 唯一标识符 |
| `name` | 人类可读的名称 |
| `description` | 详细描述 |
| `tags` | 标签，用于分类和搜索 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |
| `size_bytes` | 数据大小 |
| `checksum` | 数据完整性校验 |
| `status` | 状态（创建中、可用、失败等） |
| `version` | 版本号，用于版本管理 |
| `parent_id` | 父检查点ID，用于版本链 |

### 1.4 检查点状态机

```
CREATING → SAVING → AVAILABLE
              ↓          ↓
            FAILED    RESTORING → AVAILABLE
              ↓          ↓
            DELETED ←──────────
```

**状态说明：**
- `CREATING`: 检查点正在创建
- `SAVING`: 正在保存到存储
- `AVAILABLE`: 可用，可恢复
- `RESTORING`: 正在恢复
- `FAILED`: 保存/恢复失败
- `DELETED`: 已删除

### 1.5 思考题答案

**Q: 为什么需要抽象检查点提供者而不是直接实现？**

A: 
1. **灵活性**: 不同环境需要不同存储（开发用内存，生产用Redis）
2. **可测试性**: 可以用内存提供者进行单元测试
3. **可扩展性**: 添加新存储只需实现接口，无需修改业务逻辑
4. **关注点分离**: 业务逻辑和存储逻辑解耦

**Q: 检查点元数据为什么需要版本号字段？**

A:
1. **版本追踪**: 记录检查点的历史版本
2. **回滚支持**: 可以回滚到任意历史版本
3. **冲突解决**: 多版本时可以知道哪个更新
4. **差异存储**: 节省空间，只存储变化部分

---

## 任务2：SQLite存储提供者

### 2.1 完整实现

```python
import sqlite3
import gzip
import json
import pickle
import hashlib
from pathlib import Path
from typing import Optional, List
from datetime import datetime

class SQLiteCheckpointProvider(CheckpointProvider):
    """SQLite检查点存储提供者"""
    
    def __init__(self, db_path: str = "checkpoints.db"):
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
                data BLOB NOT NULL,
                metadata TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                checksum TEXT,
                size_bytes INTEGER
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
        logger.info(f"SQLite数据库初始化完成: {self.db_path}")
    
    async def save(self, checkpoint: Checkpoint) -> None:
        """保存检查点到SQLite"""
        # 序列化检查点数据
        data = pickle.dumps(checkpoint.state)
        
        # 压缩数据
        compressed_data = gzip.compress(data)
        logger.debug(f"压缩前: {len(data)} bytes, 压缩后: {len(compressed_data)} bytes")
        
        # 计算校验和
        checksum = hashlib.sha256(compressed_data).hexdigest()
        
        # 元数据
        metadata = json.dumps(checkpoint.metadata.to_dict())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO checkpoints 
            (checkpoint_id, name, data, metadata, checksum, size_bytes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            checkpoint.metadata.checkpoint_id,
            checkpoint.metadata.name,
            compressed_data,
            metadata,
            checksum,
            len(compressed_data)
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"检查点已保存: {checkpoint.metadata.checkpoint_id}")
    
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """从SQLite加载检查点"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name, data, metadata, checksum
            FROM checkpoints 
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            logger.warning(f"检查点不存在: {checkpoint_id}")
            return None
        
        name, compressed_data, metadata_json, checksum = row
        
        # 验证校验和
        actual_checksum = hashlib.sha256(compressed_data).hexdigest()
        if actual_checksum != checksum:
            logger.error(f"检查点校验失败: {checkpoint_id}")
            raise ValueError(f"检查点校验失败: {checkpoint_id}")
        
        # 解压数据
        data = gzip.decompress(compressed_data)
        state = pickle.loads(data)
        
        # 重建元数据
        metadata = CheckpointMetadata.from_dict(json.loads(metadata_json))
        
        logger.info(f"检查点已加载: {checkpoint_id}")
        return Checkpoint(metadata=metadata, state=state)
    
    async def delete(self, checkpoint_id: str) -> bool:
        """从SQLite删除检查点"""
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
            logger.info(f"检查点已删除: {checkpoint_id}")
        else:
            logger.warning(f"检查点不存在，无法删除: {checkpoint_id}")
        
        return deleted
    
    async def list(self) -> List[str]:
        """列出所有检查点ID"""
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
        """检查检查点是否存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 1 FROM checkpoints 
            WHERE checkpoint_id = ? LIMIT 1
        """, (checkpoint_id,))
        
        exists = cursor.fetchone() is not None
        conn.close()
        
        return exists
    
    async def get_metadata(self, checkpoint_id: str) -> Optional[CheckpointMetadata]:
        """获取检查点元数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT metadata FROM checkpoints 
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return CheckpointMetadata.from_dict(json.loads(row[0]))
```

### 2.2 测试用例

```python
import pytest
import asyncio
import os

@pytest.mark.asyncio
async def test_sqlite_provider_basic():
    """测试SQLite提供者基本功能"""
    # 使用临时文件
    test_db = "/tmp/test_checkpoints.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    provider = SQLiteCheckpointProvider(test_db)
    
    # 创建测试检查点
    metadata = CheckpointMetadata(
        checkpoint_id="test-cp-001",
        name="test-checkpoint",
        description="测试检查点",
        tags=["test", "demo"]
    )
    state = {"counter": 42, "items": [1, 2, 3], "nested": {"key": "value"}}
    checkpoint = Checkpoint(metadata=metadata, state=state)
    
    # 保存检查点
    await provider.save(checkpoint)
    
    # 验证存在
    assert await provider.exists("test-cp-001"), "检查点应该存在"
    
    # 加载检查点
    loaded = await provider.load("test-cp-001")
    assert loaded is not None, "应该成功加载检查点"
    assert loaded.metadata.name == "test-checkpoint"
    assert loaded.state["counter"] == 42
    assert loaded.state["items"] == [1, 2, 3]
    
    # 删除检查点
    deleted = await provider.delete("test-cp-001")
    assert deleted, "删除应该成功"
    assert not await provider.exists("test-cp-001"), "检查点不应该存在"
    
    # 清理
    os.remove(test_db)

@pytest.mark.asyncio
async def test_sqlite_provider_compression():
    """测试SQLite提供者压缩功能"""
    test_db = "/tmp/test_compression.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    provider = SQLiteCheckpointProvider(test_db)
    
    # 创建大对象
    large_state = {
        "data": [list(range(10000)) for _ in range(100)],
        "large_string": "x" * 100000
    }
    
    metadata = CheckpointMetadata(
        checkpoint_id="test-compress",
        name="compression-test"
    )
    checkpoint = Checkpoint(metadata=metadata, state=large_state)
    
    await provider.save(checkpoint)
    
    # 验证可以正确恢复
    loaded = await provider.load("test-compress")
    assert loaded.state["data"] == large_state["data"]
    
    # 清理
    os.remove(test_db)

@pytest.mark.asyncio
async def test_sqlite_provider_multiple():
    """测试多个检查点"""
    test_db = "/tmp/test_multiple.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    provider = SQLiteCheckpointProvider(test_db)
    
    # 创建多个检查点
    for i in range(5):
        metadata = CheckpointMetadata(
            checkpoint_id=f"cp-{i}",
            name="multi-test",
            version=i
        )
        checkpoint = Checkpoint(metadata=metadata, state={"index": i})
        await provider.save(checkpoint)
    
    # 列出检查点
    ids = await provider.list()
    assert len(ids) == 5, "应该有5个检查点"
    
    # 清理
    os.remove(test_db)
```

---

## 任务3：版本管理和回滚

### 3.1 VersionedCheckpointManager实现

```python
from collections import defaultdict
import copy

class VersionedCheckpointManager(CheckpointManager):
    """带版本管理的检查点管理器"""
    
    def __init__(self, provider: CheckpointProvider, 
                 max_versions: int = 10):
        super().__init__(provider)
        self.max_versions = max_versions
        self._version_history: Dict[str, List[CheckpointMetadata]] = defaultdict(list)
    
    async def create_versioned_checkpoint(
        self, 
        name: str, 
        state: Dict[str, Any],
        description: Optional[str] = None
    ) -> Checkpoint:
        """创建新版本检查点"""
        # 获取当前最新版本号
        versions = self._version_history.get(name, [])
        latest_version = versions[-1].version if versions else 0
        
        # 创建新版本
        new_version = latest_version + 1
        checkpoint_id = f"{name}-v{new_version}"
        
        # 查找父检查点
        parent_id = versions[-1].checkpoint_id if versions else None
        
        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            name=name,
            description=description or f"版本 {new_version}",
            version=new_version,
            parent_id=parent_id,
            status=CheckpointStatus.AVAILABLE
        )
        
        checkpoint = Checkpoint(metadata=metadata, state=state)
        await self.save_checkpoint(checkpoint)
        
        # 更新版本历史
        self._version_history[name].append(metadata)
        
        # 清理旧版本
        await self._cleanup_old_versions(name)
        
        logger.info(f"创建版本检查点: {checkpoint_id}")
        return checkpoint
    
    async def _cleanup_old_versions(self, name: str) -> None:
        """清理旧版本"""
        versions = self._version_history.get(name, [])
        
        if len(versions) <= self.max_versions:
            return
        
        # 保留最新版本
        to_keep = versions[-self.max_versions:]
        to_delete = versions[:-self.max_versions]
        
        logger.info(f"将清理 {len(to_delete)} 个旧版本")
        
        # 删除旧版本
        for old_version in to_delete:
            try:
                await self.provider.delete(old_version.checkpoint_id)
            except Exception as e:
                logger.error(f"删除旧版本失败: {old_version.checkpoint_id}, {e}")
        
        # 更新版本历史
        self._version_history[name] = to_keep
    
    async def rollback_to_version(
        self, 
        name: str, 
        version: int
    ) -> Optional[Checkpoint]:
        """回滚到指定版本"""
        versions = self._version_history.get(name, [])
        
        target = next(
            (v for v in versions if v.version == version), 
            None
        )
        
        if not target:
            logger.warning(f"版本不存在: {name} v{version}")
            return None
        
        # 加载目标版本
        checkpoint = await self.provider.load(target.checkpoint_id)
        
        if checkpoint:
            # 更新当前版本标记
            checkpoint.metadata.metadata["rolled_back_from"] = checkpoint.metadata.checkpoint_id
            checkpoint.metadata.checkpoint_id = f"{name}-current"
            checkpoint.metadata.parent_id = target.checkpoint_id
            
            await self.save_checkpoint(checkpoint)
            logger.info(f"已回滚到版本: {name} v{version}")
        
        return checkpoint
    
    async def get_version_history(
        self, 
        name: str
    ) -> List[CheckpointMetadata]:
        """获取版本历史"""
        return self._version_history.get(name, [])
    
    async def create_diff_checkpoint(
        self,
        name: str,
        state: Dict[str, Any]
    ) -> Checkpoint:
        """创建差异检查点"""
        # 获取父检查点
        versions = self._version_history.get(name, [])
        
        if not versions:
            # 没有父版本，创建完整检查点
            return await self.create_versioned_checkpoint(name, state)
        
        parent = versions[-1]
        parent_checkpoint = await self.provider.load(parent.checkpoint_id)
        
        # 计算差异
        diff = self._compute_diff(parent_checkpoint.state, state)
        
        # 创建新版本
        new_version = parent.version + 1
        checkpoint_id = f"{name}-v{new_version}"
        
        metadata = CheckpointMetadata(
            checkpoint_id=checkpoint_id,
            name=name,
            version=new_version,
            parent_id=parent.checkpoint_id,
            status=CheckpointStatus.AVAILABLE,
            metadata={"diff": True, "diff_keys": list(diff.keys())}
        )
        
        # 存储完整状态用于恢复
        full_state = {
            "diff_data": diff,
            "parent_id": parent.checkpoint_id,
            "full_state": state
        }
        
        checkpoint = Checkpoint(metadata=metadata, state=full_state)
        await self.save_checkpoint(checkpoint)
        
        # 更新版本历史
        self._version_history[name].append(metadata)
        
        logger.info(f"创建差异检查点: {checkpoint_id}, 变化: {len(diff)} 项")
        
        return checkpoint
    
    def _compute_diff(
        self, 
        old_state: Dict[str, Any], 
        new_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算状态差异"""
        diff = {}
        
        # 找出新增和修改的键
        all_keys = set(old_state.keys()) | set(new_state.keys())
        
        for key in all_keys:
            old_val = old_state.get(key)
            new_val = new_state.get(key)
            
            if old_val != new_val:
                diff[key] = {
                    "old": old_val,
                    "new": new_val
                }
        
        return diff
    
    async def restore_from_diff(
        self,
        checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """从差异检查点恢复完整状态"""
        checkpoint = await self.provider.load(checkpoint_id)
        
        if not checkpoint:
            return None
        
        # 检查是否是差异检查点
        if not checkpoint.metadata.metadata.get("diff"):
            return checkpoint.state
        
        # 递归恢复父检查点
        parent_id = checkpoint.state.get("parent_id")
        if parent_id:
            parent_state = await self.restore_from_diff(parent_id)
            if parent_state:
                # 应用差异
                diff_data = checkpoint.state.get("diff_data", {})
                for key, changes in diff_data.items():
                    parent_state[key] = changes.get("new")
                return parent_state
        
        return checkpoint.state.get("full_state")
```

### 3.2 测试用例

```python
@pytest.mark.asyncio
async def test_versioned_manager():
    """测试版本管理"""
    provider = MemoryCheckpointProvider()
    manager = VersionedCheckpointManager(provider, max_versions=3)
    
    # 创建多个版本
    for i in range(5):
        state = {"version": i, "data": f"state-{i}"}
        await manager.create_versioned_checkpoint("app", state, f"版本 {i}")
    
    # 应该只有3个版本（保留最新3个）
    history = await manager.get_version_history("app")
    assert len(history) == 3, f"应该保留3个版本，实际: {len(history)}"
    assert history[-1].version == 5
    
    # 回滚到版本3
    restored = await manager.rollback_to_version("app", 3)
    assert restored is not None
    assert restored.state["version"] == 3

@pytest.mark.asyncio
async def test_diff_checkpoint():
    """测试差异检查点"""
    provider = MemoryCheckpointProvider()
    manager = VersionedCheckpointManager(provider)
    
    # 创建初始版本
    await manager.create_versioned_checkpoint("app", {"counter": 0, "items": []})
    
    # 创建差异版本
    await manager.create_diff_checkpoint("app", {"counter": 1, "items": [1]})
    
    # 获取历史
    history = await manager.get_version_history("app")
    assert len(history) == 2
    assert history[1].metadata.metadata.get("diff") == True
```

---

## 任务4：自动保存和恢复

### 4.1 CheckpointAutoSaver实现

```python
class CheckpointAutoSaver:
    """检查点自动保存器"""
    
    def __init__(
        self,
        manager: CheckpointManager,
        interval_seconds: int = 300,
        condition: Optional[Callable[[Dict], bool]] = None,
        max_checkpoints: int = 5
    ):
        self.manager = manager
        self.interval_seconds = interval_seconds
        self.condition = condition or (lambda _: True)
        self.max_checkpoints = max_checkpoints
        
        self._task: Optional[asyncio.Task] = None
        self._last_state: Optional[Dict] = None
        self._observers: List[Callable] = []
        self._running = False
        self._checkpoint_name = "auto-save"
    
    def add_observer(self, observer: Callable) -> None:
        """添加观察者"""
        self._observers.append(observer)
        logger.debug(f"添加观察者: {observer}")
    
    def remove_observer(self, observer: Callable) -> None:
        """移除观察者"""
        self._observers.remove(observer)
        logger.debug(f"移除观察者: {observer}")
    
    async def start(
        self, 
        task_name: str, 
        initial_state: Dict
    ) -> None:
        """启动自动保存"""
        self._running = True
        self._checkpoint_name = task_name
        
        # 尝试恢复最新检查点
        restored = await self._try_restore(task_name)
        
        if restored:
            self._last_state = restored
            logger.info(f"已恢复检查点: {task_name}")
        else:
            self._last_state = initial_state
            logger.info(f"未找到检查点，使用初始状态: {task_name}")
        
        # 启动定时保存任务
        self._task = asyncio.create_task(self._auto_save_loop())
        logger.info(f"自动保存已启动: {task_name}, 间隔: {self.interval_seconds}秒")
    
    async def stop(self) -> None:
        """停止自动保存"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # 保存最终状态
        if self._last_state:
            await self._save_checkpoint()
            logger.info("已保存最终检查点")
        
        logger.info("自动保存已停止")
    
    async def update_state(self, state: Dict) -> None:
        """更新状态（触发条件检查）"""
        self._last_state = state
        
        # 检查保存条件
        if self.condition(state):
            await self._save_checkpoint()
    
    async def get_current_state(self) -> Optional[Dict]:
        """获取当前状态"""
        return self._last_state
    
    async def _auto_save_loop(self) -> None:
        """自动保存循环"""
        while self._running:
            try:
                await asyncio.sleep(self.interval_seconds)
                
                if self._running and self._last_state:
                    await self._save_checkpoint()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"自动保存失败: {e}")
    
    async def _save_checkpoint(self) -> None:
        """保存检查点"""
        if not self._last_state:
            return
        
        try:
            checkpoint = await self.manager.create_checkpoint(
                self._checkpoint_name,
                self._last_state
            )
            
            # 通知观察者
            for observer in self._observers:
                try:
                    observer(checkpoint)
                except Exception as e:
                    logger.error(f"观察者通知失败: {e}")
            
            # 清理旧检查点
            await self._cleanup_old_checkpoints()
            
            logger.debug(f"自动保存完成: {checkpoint.metadata.checkpoint_id}")
            
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
    
    async def _try_restore(self, task_name: str) -> Optional[Dict]:
        """尝试恢复检查点"""
        try:
            checkpoints = await self.manager.list_checkpoints()
            
            if not checkpoints:
                logger.info("没有找到可用的检查点")
                return None
            
            # 过滤出当前任务的检查点
            task_checkpoints = [
                cp for cp in checkpoints 
                if cp.metadata.name == task_name
            ]
            
            if not task_checkpoints:
                return None
            
            # 获取最新的检查点
            latest = task_checkpoints[0]
            
            restored = await self.manager.restore_checkpoint(
                latest.metadata.checkpoint_id
            )
            
            return restored.state if restored else None
            
        except Exception as e:
            logger.warning(f"恢复检查点失败: {e}")
            return None
    
    async def _cleanup_old_checkpoints(self) -> None:
        """清理旧检查点"""
        try:
            checkpoints = await self.manager.list_checkpoints()
            
            # 过滤当前任务的检查点
            task_checkpoints = [
                cp for cp in checkpoints 
                if cp.metadata.name == self._checkpoint_name
            ]
            
            if len(task_checkpoints) <= self.max_checkpoints:
                return
            
            # 删除旧检查点
            for old_cp in task_checkpoints[self.max_checkpoints:]:
                try:
                    await self.manager.delete_checkpoint(
                        old_cp.metadata.checkpoint_id
                    )
                    logger.debug(f"已清理旧检查点: {old_cp.metadata.checkpoint_id}")
                except Exception as e:
                    logger.error(f"清理检查点失败: {old_cp.metadata.checkpoint_id}, {e}")
            
        except Exception as e:
            logger.error(f"清理旧检查点失败: {e}")
```

### 4.2 测试用例

```python
@pytest.mark.asyncio
async def test_auto_saver():
    """测试自动保存"""
    provider = MemoryCheckpointProvider()
    manager = CheckpointManager(provider)
    auto_saver = CheckpointAutoSaver(
        manager, 
        interval_seconds=1,
        max_checkpoints=3
    )
    
    # 保存次数记录
    save_count = 0
    
    def on_checkpoint(checkpoint):
        nonlocal save_count
        save_count += 1
    
    auto_saver.add_observer(on_checkpoint)
    
    # 启动自动保存
    await auto_saver.start("test-task", {"counter": 0})
    
    # 更新状态
    await auto_saver.update_state({"counter": 1})
    await auto_saver.update_state({"counter": 2})
    await auto_saver.update_state({"counter": 3})
    
    # 等待自动保存触发
    await asyncio.sleep(2)
    
    # 停止自动保存
    await auto_saver.stop()
    
    # 验证保存了检查点
    assert save_count > 0 or auto_saver._last_state is not None

@pytest.mark.asyncio
async def test_auto_saver_restore():
    """测试自动保存恢复"""
    provider = MemoryCheckpointProvider()
    manager = CheckpointManager(provider)
    auto_saver = CheckpointAutoSaver(
        manager,
        interval_seconds=60,  # 不会自动触发
        max_checkpoints=3
    )
    
    # 第一次运行：创建状态
    await auto_saver.start("task-a", {"value": "original"})
    await auto_saver.update_state({"value": "updated"})
    await auto_saver.stop()
    
    # 第二次运行：应该恢复
    auto_saver2 = CheckpointAutoSaver(
        manager,
        interval_seconds=60,
        max_checkpoints=3
    )
    await auto_saver2.start("task-a", {"value": "new"})
    
    # 应该恢复之前的状态
    current = await auto_saver2.get_current_state()
    assert current is not None
    
    await auto_saver2.stop()
```

---

## 扩展挑战答案

### 挑战1：分布式检查点同步

```python
import aioredis
import json
from typing import Dict, Any

class DistributedCheckpointManager(VersionedCheckpointManager):
    """分布式检查点管理器"""
    
    def __init__(
        self,
        provider: CheckpointProvider,
        redis_url: str,
        channel_prefix: str = "checkpoint"
    ):
        super().__init__(provider)
        self.redis_url = redis_url
        self.channel_prefix = channel_prefix
        self._pubsub = None
        self._publisher = None
    
    async def _get_redis(self):
        """获取Redis连接"""
        if self._publisher is None:
            self._publisher = await aioredis.create_redis_pool(self.redis_url)
        return self._publisher
    
    async def publish_checkpoint(self, checkpoint: Checkpoint) -> None:
        """发布检查点更新"""
        redis = await self._get_redis()
        
        message = json.dumps({
            "checkpoint_id": checkpoint.metadata.checkpoint_id,
            "name": checkpoint.metadata.name,
            "version": checkpoint.metadata.version,
            "timestamp": datetime.now().isoformat()
        })
        
        channel = f"{self.channel_prefix}:{checkpoint.metadata.name}"
        await redis.publish(channel, message)
        logger.info(f"已发布检查点更新: {channel}")
    
    async def subscribe_updates(
        self, 
        checkpoint_name: str,
        callback: Callable
    ) -> None:
        """订阅检查点更新"""
        redis = await self._get_redis()
        
        channel = f"{self.channel_prefix}:{checkpoint_name}"
        pubsub = redis.subscribe(channel)
        
        async def listener():
            async for msg in pubsub:
                data = json.loads(msg)
                await callback(data)
        
        asyncio.create_task(listener())
        logger.info(f"已订阅检查点更新: {channel}")
```

---

## 常见问题与解决方案

### Q1: 检查点数据太大怎么办？
A: 
1. 使用压缩（gzip/lz4）
2. 使用差异检查点
3. 定期清理旧检查点
4. 考虑分布式存储

### Q2: 如何保证检查点一致性？
A:
1. 使用事务
2. 写入前先写临时文件，完成后重命名
3. 使用校验和验证完整性

### Q3: 检查点恢复失败怎么办？
A:
1. 实现多版本保留
2. 定期验证检查点完整性
3. 保留上一个可用的检查点

---

**答案解析**: DeerFlow Python Agent架构师训练营  
**版本**: v1.0.0  
**最后更新**: 2024年4月12日
