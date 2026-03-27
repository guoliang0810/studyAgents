#!/usr/bin/env python3
"""
Day 13 - 第52节课：实战：记忆持久化
====================================

本演示代码实现记忆持久化系统，包括：
1. FactSerializer - Fact对象序列化器
2. SQLiteMemoryStore - 基于SQLite的持久化存储
3. MemoryBackupManager - 记忆备份管理器

运行方式:
    python memory_persistence_demo.py          # 运行演示
    python memory_persistence_demo.py --test   # 运行测试
"""

import time
import json
import sqlite3
import os
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import sys
import tempfile


# ============================================================================
# 第一部分：数据模型定义
# ============================================================================

class MemoryType(Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working"


class MemoryStatus(Enum):
    """记忆状态枚举"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class Fact:
    """事实数据模型"""
    content: str
    source: str
    confidence: float = 1.0
    memory_type: MemoryType = MemoryType.LONG_TERM
    id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    status: MemoryStatus = MemoryStatus.ACTIVE
    
    def __post_init__(self):
        if self.id is None:
            import uuid
            self.id = str(uuid.uuid4())
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"置信度必须在0.0-1.0之间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "memory_type": self.memory_type.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "tags": self.tags,
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Fact':
        """从字典创建"""
        return cls(
            id=data.get("id"),
            content=data["content"],
            source=data["source"],
            confidence=data.get("confidence", 1.0),
            memory_type=MemoryType(data.get("memory_type", "long_term")),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            status=MemoryStatus(data.get("status", "active"))
        )


# ============================================================================
# 第二部分：序列化器
# ============================================================================

class FactSerializer:
    """Fact对象序列化器"""
    
    @staticmethod
    def to_json(fact: Fact) -> str:
        """序列化为JSON字符串"""
        return json.dumps(fact.to_dict(), ensure_ascii=False, indent=2)
    
    @staticmethod
    def from_json(json_str: str) -> Fact:
        """从JSON字符串反序列化"""
        return Fact.from_dict(json.loads(json_str))
    
    @staticmethod
    def batch_to_json(facts: List[Fact]) -> str:
        """批量序列化"""
        return json.dumps([f.to_dict() for f in facts], ensure_ascii=False, indent=2)
    
    @staticmethod
    def batch_from_json(json_str: str) -> List[Fact]:
        """批量反序列化"""
        return [Fact.from_dict(d) for d in json.loads(json_str)]


# ============================================================================
# 第三部分：SQLite持久化存储
# ============================================================================

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    memory_type TEXT DEFAULT 'long_term',
    status TEXT DEFAULT 'active',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_tags (
    fact_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (fact_id, tag)
);

CREATE TABLE IF NOT EXISTS fact_metadata (
    fact_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (fact_id, key)
);

CREATE INDEX IF NOT EXISTS idx_facts_memory_type ON facts(memory_type);
CREATE INDEX IF NOT EXISTS idx_facts_status ON facts(status);
CREATE INDEX IF NOT EXISTS idx_facts_created_at ON facts(created_at);
"""


class SQLiteMemoryStore:
    """基于SQLite的记忆持久化存储"""
    
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        # 对于内存数据库，保持一个持久连接
        if db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(":memory:")
            self._persistent_conn.row_factory = sqlite3.Row
            self._persistent_conn.executescript(CREATE_TABLES_SQL)
            self._persistent_conn.commit()
        else:
            self._persistent_conn = None
            # 初始化表
            conn = sqlite3.connect(db_path)
            conn.executescript(CREATE_TABLES_SQL)
            conn.commit()
            conn.close()
    
    def _get_conn(self):
        """获取连接"""
        if self._persistent_conn:
            return self._persistent_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _close_conn(self, conn):
        """关闭连接（如果是临时连接）"""
        if conn is not self._persistent_conn:
            conn.close()
    
    def add(self, fact: Fact) -> str:
        """添加记忆"""
        conn = self._get_conn()
        try:
            conn.execute("""
                INSERT INTO facts (id, content, source, confidence, memory_type, 
                                   status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (fact.id, fact.content, fact.source, fact.confidence,
                  fact.memory_type.value, fact.status.value,
                  fact.created_at, fact.updated_at))
            
            for tag in fact.tags:
                conn.execute("INSERT INTO fact_tags (fact_id, tag) VALUES (?, ?)",
                           (fact.id, tag))
            
            for key, value in fact.metadata.items():
                conn.execute("INSERT INTO fact_metadata (fact_id, key, value) VALUES (?, ?, ?)",
                           (fact.id, key, json.dumps(value)))
            
            if not self._persistent_conn:
                conn.commit()
        finally:
            self._close_conn(conn)
        return fact.id
    
    def get(self, fact_id: str) -> Optional[Fact]:
        """获取记忆"""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM facts WHERE id = ?", (fact_id,)).fetchone()
            if not row:
                return None
            
            tags = [r["tag"] for r in conn.execute(
                "SELECT tag FROM fact_tags WHERE fact_id = ?", (fact_id,)).fetchall()]
            
            metadata = {}
            for r in conn.execute(
                "SELECT key, value FROM fact_metadata WHERE fact_id = ?", (fact_id,)).fetchall():
                metadata[r["key"]] = json.loads(r["value"])
            
            return Fact(
                id=row["id"], content=row["content"], source=row["source"],
                confidence=row["confidence"], memory_type=MemoryType(row["memory_type"]),
                status=MemoryStatus(row["status"]), created_at=row["created_at"],
                updated_at=row["updated_at"], tags=tags, metadata=metadata
            )
        finally:
            self._close_conn(conn)
    
    def search(self, query: str, limit: int = 10) -> List[Fact]:
        """搜索记忆"""
        conn = self._get_conn()
        try:
            rows = conn.execute("""
                SELECT id FROM facts WHERE content LIKE ? AND status = 'active'
                ORDER BY confidence DESC LIMIT ?
            """, (f"%{query}%", limit)).fetchall()
            
            return [self.get(r["id"]) for r in rows if self.get(r["id"])]
        finally:
            self._close_conn(conn)
    
    def update(self, fact_id: str, **kwargs) -> bool:
        """更新记忆"""
        conn = self._get_conn()
        try:
            existing = conn.execute("SELECT id FROM facts WHERE id = ?", (fact_id,)).fetchone()
            if not existing:
                return False
            
            updates, values = [], []
            if "content" in kwargs:
                updates.append("content = ?")
                values.append(kwargs["content"])
            if "confidence" in kwargs:
                updates.append("confidence = ?")
                values.append(kwargs["confidence"])
            if "status" in kwargs:
                updates.append("status = ?")
                values.append(kwargs["status"].value if isinstance(kwargs["status"], MemoryStatus) else kwargs["status"])
            
            updates.append("updated_at = ?")
            values.extend([time.time(), fact_id])
            
            conn.execute(f"UPDATE facts SET {', '.join(updates)} WHERE id = ?", values)
            if not self._persistent_conn:
                conn.commit()
            return True
        finally:
            self._close_conn(conn)
    
    def delete(self, fact_id: str) -> bool:
        """软删除"""
        return self.update(fact_id, status=MemoryStatus.DELETED)
    
    def count(self) -> int:
        """获取活跃记忆数量"""
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT COUNT(*) as cnt FROM facts WHERE status = 'active'").fetchone()
            return row["cnt"]
        finally:
            self._close_conn(conn)
    
    def get_all(self, limit: int = 100) -> List[Fact]:
        """获取所有活跃记忆"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT id FROM facts WHERE status = 'active' ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [self.get(r["id"]) for r in rows if self.get(r["id"])]
        finally:
            self._close_conn(conn)
    
    def export_to_json(self, filepath: str) -> int:
        """导出到JSON"""
        facts = self.get_all(limit=10000)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump([f.to_dict() for f in facts], f, ensure_ascii=False, indent=2)
        return len(facts)
    
    def import_from_json(self, filepath: str) -> int:
        """从JSON导入"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        count = 0
        for item in data:
            try:
                self.add(Fact.from_dict(item))
                count += 1
            except:
                continue
        return count


# ============================================================================
# 第四部分：备份管理器
# ============================================================================

class MemoryBackupManager:
    """记忆备份管理器"""
    
    def __init__(self, backup_dir: str):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_backup(self, store: SQLiteMemoryStore, name: Optional[str] = None) -> str:
        """创建备份"""
        name = name or f"backup_{int(time.time())}.json"
        path = os.path.join(self.backup_dir, name)
        count = store.export_to_json(path)
        
        checksum = self._checksum(path)
        meta = {"backup_name": name, "created_at": time.time(), 
                "fact_count": count, "checksum": checksum}
        with open(path.replace(".json", "_meta.json"), 'w') as f:
            json.dump(meta, f)
        return path
    
    def restore_backup(self, store: SQLiteMemoryStore, path: str) -> bool:
        """恢复备份"""
        if not os.path.exists(path):
            return False
        try:
            store.import_from_json(path)
            return True
        except:
            return False
    
    def _checksum(self, path: str) -> str:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                h.update(chunk)
        return h.hexdigest()
    
    def list_backups(self) -> List[Dict]:
        """列出备份"""
        backups = []
        for fn in os.listdir(self.backup_dir):
            if fn.endswith("_meta.json"):
                with open(os.path.join(self.backup_dir, fn), 'r') as f:
                    backups.append(json.load(f))
        return sorted(backups, key=lambda x: x.get("created_at", 0), reverse=True)


# ============================================================================
# 第五部分：测试套件
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("🧪 运行记忆持久化测试套件")
    print("=" * 60)
    
    passed, total = 0, 6
    
    # 测试1: 序列化
    print("\n📊 测试1: Fact序列化")
    try:
        fact = Fact("用户是Python开发者", "user", 0.95, tags=["python"])
        json_str = FactSerializer.to_json(fact)
        fact2 = FactSerializer.from_json(json_str)
        assert fact2.content == fact.content
        assert fact2.tags == fact.tags
        print("   ✅ 序列化正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试2: SQLite基本操作
    print("\n📊 测试2: SQLite基本操作")
    try:
        store = SQLiteMemoryStore(":memory:")
        fid = store.add(Fact("测试记忆", "test"))
        assert store.get(fid) is not None
        assert store.update(fid, confidence=0.5)
        assert store.delete(fid)
        print("   ✅ SQLite基本操作正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试3: 标签和元数据
    print("\n📊 测试3: 标签和元数据")
    try:
        store = SQLiteMemoryStore(":memory:")
        fid = store.add(Fact("带标签记忆", "test", tags=["t1"], metadata={"k": "v"}))
        f = store.get(fid)
        assert "t1" in f.tags
        assert f.metadata["k"] == "v"
        print("   ✅ 标签和元数据正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试4: 搜索
    print("\n📊 测试4: 搜索功能")
    try:
        store = SQLiteMemoryStore(":memory:")
        store.add(Fact("Python编程", "test"))
        store.add(Fact("Java编程", "test"))
        store.add(Fact("Python数据", "test"))
        results = store.search("Python")
        assert len(results) == 2
        print("   ✅ 搜索功能正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试5: 导出导入
    print("\n📊 测试5: 导出导入")
    try:
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        store1 = SQLiteMemoryStore(":memory:")
        store1.add(Fact("记忆1", "test"))
        store1.add(Fact("记忆2", "test"))
        count = store1.export_to_json(path)
        assert count == 2
        store2 = SQLiteMemoryStore(":memory:")
        assert store2.import_from_json(path) == 2
        os.unlink(path)
        print("   ✅ 导出导入正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试6: 备份管理
    print("\n📊 测试6: 备份管理")
    try:
        with tempfile.TemporaryDirectory() as d:
            store = SQLiteMemoryStore(":memory:")
            store.add(Fact("备份测试", "test"))
            mgr = MemoryBackupManager(d)
            path = mgr.create_backup(store)
            assert os.path.exists(path)
            assert len(mgr.list_backups()) == 1
            store2 = SQLiteMemoryStore(":memory:")
            assert mgr.restore_backup(store2, path)
            assert store2.count() == 1
        print("   ✅ 备份管理正常")
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
    print("💾 Day 13 - 第52节课：记忆持久化演示")
    print("=" * 60)
    
    print("\n📝 演示1: 序列化")
    fact = Fact("用户是Python开发者", "user", 0.95, tags=["python"], metadata={"exp": 5})
    json_str = FactSerializer.to_json(fact)
    print(f"JSON (前150字符): {json_str[:150]}...")
    
    print("\n\n📝 演示2: SQLite存储")
    store = SQLiteMemoryStore(":memory:")
    for content in ["Python编程", "后端开发", "VS Code使用"]:
        store.add(Fact(content, "test"))
    print(f"存储了 {store.count()} 条记忆")
    results = store.search("Python")
    print(f"搜索'Python'找到 {len(results)} 条")
    
    print("\n\n📝 演示3: 备份管理")
    with tempfile.TemporaryDirectory() as d:
        mgr = MemoryBackupManager(d)
        path = mgr.create_backup(store)
        print(f"备份路径: {path}")
        print(f"备份列表: {mgr.list_backups()}")
    
    print("\n" + "=" * 60)
    print("✅ 演示完成！")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(0 if run_tests() else 1)
    else:
        run_demo()
