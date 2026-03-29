# 📚 Day 20 第77节课：Checkpointing架构 - 课后练习

## 🎯 练习目标
通过本练习，你将掌握：
1. 检查点系统的核心概念和架构设计
2. CheckpointManager类的实现和工作原理
3. 多存储后端的检查点保存和恢复机制
4. 检查点元数据管理和标签系统
5. 检查点的去重、排序和查询功能

## ⏰ 预计用时
- 基础任务：90分钟
- 扩展挑战：180分钟
- 总计：4小时30分钟

## 🔧 环境准备
```bash
# 1. 激活虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 2. 安装可选依赖
pip install pytest>=8.0.0 pytest-asyncio>=0.23.0

# 3. 克隆演示代码
cp -r ../课堂演示代码/day20-lesson77/ ./work/
cd work

# 4. 验证环境
python -c "import asyncio; print('Python环境就绪')"
```

## 📝 练习任务

### 任务1：理解检查点系统架构（25分钟）
**目标**: 理解检查点系统的核心组件和设计原则

**步骤**:
1. 阅读`CheckpointManager`类和`CheckpointProvider`类的源代码
2. 回答以下问题：
   - 检查点系统的四大核心组件是什么？每个组件的作用是什么？
   - CheckpointProvider抽象基类定义了哪些方法？为什么需要抽象？
   - 检查点元数据包含哪些信息？每个字段的作用是什么？
   - 检查点状态机有哪些状态？状态之间的转换关系是什么？
3. 绘制检查点系统架构图

**思考题**:
- 为什么需要抽象检查点提供者而不是直接实现？
- 检查点元数据为什么需要版本号字段？

### 任务2：实现自定义检查点存储提供者（35分钟）
**目标**: 实现一个自定义的存储后端

**要求**:
1. 实现一个SQLite存储后端`SQLiteCheckpointProvider`
2. 实现以下方法：
   - `save(checkpoint)`: 保存检查点到SQLite
   - `load(checkpoint_id)`: 从SQLite加载检查点
   - `delete(checkpoint_id)`: 从SQLite删除检查点
   - `list()`: 列出所有检查点
   - `exists(checkpoint_id)`: 检查检查点是否存在
3. 实现检查点的压缩存储（使用gzip压缩）
4. 编写测试用例验证功能

**代码框架**:
```python
import sqlite3
import gzip
import json
from pathlib import Path

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
    
    async def save(self, checkpoint: Checkpoint) -> None:
        """保存检查点到SQLite"""
        # 序列化检查点数据
        data = pickle.dumps(checkpoint.state)
        
        # 压缩数据
        compressed_data = gzip.compress(data)
        
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
            return None
        
        name, compressed_data, metadata_json, checksum = row
        
        # 验证校验和
        actual_checksum = hashlib.sha256(compressed_data).hexdigest()
        if actual_checksum != checksum:
            raise ValueError(f"检查点校验失败: {checkpoint_id}")
        
        # 解压数据
        data = gzip.decompress(compressed_data)
        state = pickle.loads(data)
        
        # 重建元数据
        metadata = CheckpointMetadata.from_dict(json.loads(metadata_json))
        
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
```

**测试用例**:
```python
@pytest.mark.asyncio
async def test_sqlite_provider():
    """测试SQLite提供者"""
    provider = SQLiteCheckpointProvider(":memory:")
    
    # 创建测试检查点
    metadata = CheckpointMetadata(
        checkpoint_id="test-cp-001",
        name="test-checkpoint"
    )
    state = {"counter": 42, "items": [1, 2, 3]}
    checkpoint = Checkpoint(metadata=metadata, state=state)
    
    # 保存检查点
    await provider.save(checkpoint)
    
    # 验证存在
    assert await provider.exists("test-cp-001")
    
    # 加载检查点
    loaded = await provider.load("test-cp-001")
    assert loaded is not None
    assert loaded.metadata.name == "test-checkpoint"
    assert loaded.state["counter"] == 42
    
    # 删除检查点
    deleted = await provider.delete("test-cp-001")
    assert deleted
    assert not await provider.exists("test-cp-001")
```

### 任务3：实现检查点版本管理和回滚（30分钟）
**目标**: 实现检查点的版本控制和回滚功能

**要求**:
1. 扩展`CheckpointManager`类，添加版本管理功能
2. 实现以下功能：
   - 创建新版本检查点（保留历史版本）
   - 回滚到指定版本
   - 查看版本历史
   - 清理旧版本（保留N个最新版本）
3. 实现差异检查点（只存储与父版本的差异）
4. 编写测试用例验证版本管理

**代码框架**:
```python
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
            description=description,
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
        
        return checkpoint
    
    async def _cleanup_old_versions(self, name: str) -> None:
        """清理旧版本"""
        versions = self._version_history.get(name, [])
        
        if len(versions) <= self.max_versions:
            return
        
        # 保留最新版本
        to_keep = versions[-self.max_versions:]
        to_delete = versions[:-self.max_versions]
        
        # 删除旧版本
        for old_version in to_delete:
            await self.provider.delete(old_version.checkpoint_id)
        
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
            return None
        
        # 加载目标版本
        checkpoint = await self.provider.load(target.checkpoint_id)
        
        if checkpoint:
            # 更新当前版本标记
            checkpoint.metadata.metadata["rolled_back_from"] = checkpoint.metadata.checkpoint_id
            checkpoint.metadata.checkpoint_id = f"{name}-current"
            checkpoint.metadata.parent_id = target.checkpoint_id
            
            await self.save_checkpoint(checkpoint)
        
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
            metadata={"diff": True}
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
```

### 任务4：实现检查点自动保存和恢复（40分钟）
**目标**: 实现自动检查点功能，用于长时运行任务

**要求**:
1. 实现检查点自动保存器`CheckpointAutoSaver`
2. 实现以下功能：
   - 定时自动保存检查点
   - 基于条件触发保存（例如状态变化超过阈值）
   - 自动恢复最新检查点
   - 检查点过期自动清理
3. 实现检查点观察者模式，支持钩子函数
4. 编写测试用例验证自动保存

**代码框架**:
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
    
    def add_observer(self, observer: Callable) -> None:
        """添加观察者"""
        self._observers.append(observer)
    
    def remove_observer(self, observer: Callable) -> None:
        """移除观察者"""
        self._observers.remove(observer)
    
    async def start(
        self, 
        task_name: str, 
        initial_state: Dict
    ) -> None:
        """启动自动保存"""
        self._running = True
        
        # 尝试恢复最新检查点
        restored = await self._try_restore(task_name)
        
        if restored:
            self._last_state = restored
            logger.info(f"已恢复检查点: {task_name}")
        else:
            self._last_state = initial_state
            logger.info(f"未找到检查点，使用初始状态: {task_name}")
        
        # 启动定时保存任务
        self._task = asyncio.create_task(self._auto_save_loop(task_name))
    
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
            await self._save_final_checkpoint()
    
    async def update_state(self, state: Dict) -> None:
        """更新状态（触发条件检查）"""
        self._last_state = state
        
        # 检查保存条件
        if self.condition(state):
            await self._save_checkpoint()
    
    async def _auto_save_loop(self, task_name: str) -> None:
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
        
        checkpoint_name = getattr(self.manager, '_default_name', 'auto-save')
        
        try:
            checkpoint = await self.manager.create_checkpoint(
                checkpoint_name,
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
            
        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
    
    async def _try_restore(self, task_name: str) -> Optional[Dict]:
        """尝试恢复检查点"""
        try:
            checkpoints = await self.manager.list_checkpoints()
            
            if not checkpoints:
                return None
            
            # 获取最新的检查点
            latest = checkpoints[0]
            
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
            
            if len(checkpoints) <= self.max_checkpoints:
                return
            
            # 删除旧检查点
            for old_cp in checkpoints[self.max_checkpoints:]:
                await self.manager.delete_checkpoint(
                    old_cp.metadata.checkpoint_id
                )
                
        except Exception as e:
            logger.error(f"清理旧检查点失败: {e}")
    
    async def _save_final_checkpoint(self) -> None:
        """保存最终检查点"""
        # 实现最终保存逻辑
        pass
```

## 🏆 扩展挑战

### 挑战1：实现分布式检查点同步（高级）
**目标**: 支持多进程/多机器间的检查点同步

**要求**:
1. 实现Redis发布/订阅同步
2. 实现检查点锁机制
3. 支持检查点冲突解决
4. 编写测试用例

### 挑战2：实现检查点加密存储（高级）
**目标**: 安全存储敏感检查点数据

**要求**:
1. 实现AES加密存储
2. 支持密钥轮换
3. 实现安全删除（覆写）
4. 编写测试用例

### 挑战3：实现检查点可视化界面（专家级）
**目标**: Web界面管理检查点

**要求**:
1. 实现REST API接口
2. 实现版本对比功能
3. 实现状态可视化
4. 实现检查点导出/导入

## 📊 评估标准

### 基础任务评分（100分）
- **任务1（15分）**: 架构理解深度、问题回答准确性
- **任务2（25分）**: SQLite提供者功能完整性、压缩、测试
- **任务3（30分）**: 版本管理功能、回滚、差异检查点
- **任务4（30分）**: 自动保存、观察者模式、恢复功能

### 扩展挑战加分（每项25分）
- **挑战1**: 分布式同步、锁机制、冲突解决
- **挑战2**: 加密存储、密钥轮换、安全删除
- **挑战3**: REST API、版本对比、可视化

## 📝 提交要求

### 提交内容
1. **源代码**: 扩展的检查点提供者和管理器
2. **测试代码**: 单元测试和集成测试
3. **文档**: 设计文档和使用指南

### 截止时间
- **基础任务**: 课程结束后48小时内
- **扩展挑战**: 课程结束后7天内

---

**练习设计**: DeerFlow Python Agent架构师训练营  
**版本**: v1.0.0  
**最后更新**: 2024年4月12日  
**教师**: 张老师  
**助教支持**: 课程Discord频道
