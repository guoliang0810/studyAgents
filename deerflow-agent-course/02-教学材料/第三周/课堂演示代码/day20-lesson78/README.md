# 🎓 Day 20 第78节课：检查点提供者 - 课堂演示代码

## 📚 课程概述

本课程深入讲解检查点提供者（Checkpoint Provider）的设计与实现。通过完整的代码演示，学生将掌握Provider抽象接口、多种存储后端实现（文件系统、数据库、内存）以及数据完整性和一致性的保证机制。

## 🎯 学习目标

### 知识目标
1. 理解检查点提供者抽象接口的设计原则
2. 掌握文件系统提供者的实现细节
3. 掌握数据库提供者的实现机制
4. 了解不同存储后端的适用场景和权衡

### 技能目标
1. 实现基于文件系统的检查点存储和加载
2. 实现基于数据库（SQLAlchemy/SQLite）的检查点持久化
3. 设计检查点数据的序列化和反序列化策略
4. 处理检查点数据的完整性和一致性保证

## 📁 文件结构

```
day20-lesson78/
├── checkpoint_provider_demo.py     # 主演示代码文件
├── README.md                       # 本文件
└── requirements.txt                # Python依赖包列表
```

## 🛠️ 技术栈

- **Python 3.12+**: 异步编程，类型提示，数据类
- **存储后端**: 文件系统（JSON）、SQLite数据库、内存
- **设计模式**: 抽象工厂、策略模式、LRU缓存
- **数据完整性**: SHA256校验和

## 🔧 核心组件

### 1. CheckpointProvider - 抽象基类
```python
class CheckpointProvider(ABC):
    @abstractmethod
    async def save(self, checkpoint): pass
    @abstractmethod
    async def load(self, checkpoint_id): pass
    @abstractmethod
    async def delete(self, checkpoint_id): pass
    @abstractmethod
    async def list(self): pass
    @abstractmethod
    async def exists(self, checkpoint_id): pass
```

### 2. FileSystemCheckpointProvider
- 目录结构：base_dir/checkpoint_id/{state.json, metadata.json, checkpoint.json}
- 支持数据完整性校验（SHA256）
- 便于调试和查看

### 3. DatabaseCheckpointProvider
- 使用SQLite存储
- 支持SQL查询
- 适合大规模检查点管理

### 4. InMemoryCheckpointProvider
- 内存存储， fastest
- 支持LRU淘汰策略
- 适合测试或临时存储

## 🧪 测试与演示

```bash
python checkpoint_provider_demo.py --test
python checkpoint_provider_demo.py --bench
```

---

**课程设计**: DeerFlow Python Agent架构师训练营  
**版本**: v1.0.0  
**教师**: 张老师
