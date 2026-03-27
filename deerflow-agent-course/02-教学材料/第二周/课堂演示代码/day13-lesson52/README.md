# Day 13 - 第52节课：实战：记忆持久化

## 📚 课程概述

本节课实战演练记忆持久化系统，包括SQLite存储、JSON序列化和备份管理。

## 🎯 学习目标

1. **设计数据库表**：SQLite表结构和索引优化
2. **实现序列化**：Fact对象的JSON序列化/反序列化
3. **实现持久化存储**：SQLiteMemoryStore的CRUD操作
4. **设计备份策略**：备份创建、恢复和完整性验证

## 📁 文件结构

```
day13-lesson52/
├── memory_persistence_demo.py    # 主演示代码
└── README.md                      # 本文件
```

## 🚀 运行方式

```bash
python memory_persistence_demo.py        # 运行演示
python memory_persistence_demo.py --test # 运行测试
```

## 📖 核心概念

### 1. 数据库表结构

```sql
-- 记忆主表
CREATE TABLE facts (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    memory_type TEXT DEFAULT 'long_term',
    status TEXT DEFAULT 'active',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

-- 标签关联表
CREATE TABLE fact_tags (
    fact_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (fact_id, tag)
);

-- 元数据表
CREATE TABLE fact_metadata (
    fact_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (fact_id, key)
);
```

### 2. 内存数据库注意事项

SQLite的`:memory:`数据库每个连接创建新的空数据库，需要保持持久连接。

## 🔧 核心类说明

### FactSerializer

JSON序列化器。

```python
serializer = FactSerializer()
json_str = serializer.to_json(fact)
fact2 = serializer.from_json(json_str)
```

### SQLiteMemoryStore

SQLite持久化存储。

```python
store = SQLiteMemoryStore(":memory:")  # 或文件路径
store.add(Fact("内容", "source"))
results = store.search("关键词")
store.export_to_json("backup.json")
```

### MemoryBackupManager

备份管理器。

```python
mgr = MemoryBackupManager("/backup/dir")
mgr.create_backup(store)  # 创建备份
mgr.restore_backup(store, path)  # 恢复备份
mgr.list_backups()  # 列出备份
```

## 📊 测试用例

| 测试 | 说明 | 结果 |
|------|------|------|
| 测试1 | Fact序列化 | ✅ |
| 测试2 | SQLite基本操作 | ✅ |
| 测试3 | 标签和元数据 | ✅ |
| 测试4 | 搜索功能 | ✅ |
| 测试5 | 导出导入 | ✅ |
| 测试6 | 备份管理 | ✅ |

## 📝 课后练习

1. 实现PostgreSQL存储后端
2. 添加向量字段支持
3. 实现增量备份
4. 添加备份加密

## 🔗 扩展阅读

- SQLite官方文档
- JSON序列化最佳实践
- 数据库备份策略
