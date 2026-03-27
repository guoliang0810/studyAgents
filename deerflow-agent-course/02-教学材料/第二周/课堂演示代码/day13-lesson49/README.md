# Day 13 - 第49节课：记忆系统架构设计

## 📚 课程概述

本节课深入讲解Agent记忆系统的三层架构设计，包括Fact数据模型、MemoryStore抽象接口和记忆生命周期管理。

## 🎯 学习目标

1. **理解三层架构**：掌握短期记忆、长期记忆、工作记忆的职责划分
2. **掌握Fact模型**：理解事实数据模型的核心字段设计（id、content、source、confidence）
3. **设计抽象接口**：学会设计MemoryStore抽象接口，支持多种存储后端
4. **管理记忆生命周期**：了解不同记忆类型的生命周期管理策略

## 📁 文件结构

```
day13-lesson49/
├── memory_architecture_demo.py    # 主演示代码
└── README.md                       # 本文件
```

## 🚀 运行方式

### 运行演示
```bash
python memory_architecture_demo.py
```

### 运行测试
```bash
python memory_architecture_demo.py --test
```

## 📖 核心概念

### 1. 三层记忆架构

| 记忆类型 | 特点 | 生命周期 | 适用场景 |
|---------|------|---------|---------|
| 短期记忆(ShortTerm) | 基于会话，有容量限制 | 会话期间 | 对话历史、临时缓存 |
| 长期记忆(LongTerm) | 持久化存储，支持置信度过滤 | 跨会话保留 | 用户画像、重要知识 |
| 工作记忆(Working) | 任务上下文，相关性评分 | 任务期间 | 步骤状态、中间结果 |

### 2. Fact数据模型

```python
@dataclass
class Fact:
    id: str              # 唯一标识符
    content: str         # 事实内容
    source: str          # 来源: "user"/"system"/"tool"
    confidence: float    # 置信度: 0.0-1.0
    memory_type: MemoryType  # 记忆类型
    created_at: float    # 创建时间戳
    updated_at: float    # 更新时间戳
    metadata: Dict       # 扩展元数据
    tags: Set[str]       # 标签集合
    access_count: int    # 访问次数
    status: MemoryStatus # 状态
```

### 3. MemoryStore抽象接口

```python
class MemoryStore(ABC):
    @abstractmethod
    def add(self, fact: Fact) -> str: ...
    
    @abstractmethod
    def search(self, query: str, limit: int, min_confidence: float) -> List[Fact]: ...
    
    @abstractmethod
    def get(self, fact_id: str) -> Optional[Fact]: ...
    
    @abstractmethod
    def update(self, fact_id: str, **kwargs) -> bool: ...
    
    @abstractmethod
    def delete(self, fact_id: str) -> bool: ...
```

## 🔧 核心类说明

### Fact

事实数据模型，表示Agent记忆系统中的一条事实知识。

```python
fact = Fact(
    content="用户是Python开发者",
    source="user",
    confidence=0.95,
    memory_type=MemoryType.LONG_TERM
)
fact.add_tag("user_profile")
fact.update(confidence=1.0)
```

### InMemoryStore

基于字典的内存存储实现，适合开发测试。

```python
store = InMemoryStore()
store.add(fact)
results = store.search("Python", limit=5, min_confidence=0.5)
```

### ShortTermMemory

短期记忆，基于会话的临时存储，有容量限制。

```python
memory = ShortTermMemory(max_size=100)
memory.add_fact("用户说了你好", source="user")
recent = memory.get_recent(count=10)
```

### LongTermMemory

长期记忆，持久化的知识存储，支持置信度过滤。

```python
memory = LongTermMemory()
memory.add_fact("用户偏好", confidence=0.9, tags={"profile"})
results = memory.search("偏好", min_confidence=0.5)
```

### WorkingMemory

工作记忆，当前任务上下文。

```python
working = WorkingMemory(task_id="task_001")
working.add_context("正在处理请求", relevance=1.0)
context = working.get_context()
```

### MemorySystem

完整的记忆系统，整合三层记忆。

```python
system = MemorySystem()
system.add_to_short_term("对话内容")
system.add_to_long_term("重要知识", tags={"knowledge"})
system.search_all("关键词")  # 跨层搜索
```

## 📊 测试用例

| 测试 | 说明 | 预期结果 |
|------|------|---------|
| 测试1 | Fact数据模型基本功能 | 字段验证、更新、访问计数正常 |
| 测试2 | Fact序列化和反序列化 | to_dict/from_dict正确转换 |
| 测试3 | InMemoryStore基本操作 | 增删改查和搜索正常 |
| 测试4 | ShortTermMemory容量限制 | 超出容量时清理最旧记忆 |
| 测试5 | LongTermMemory置信度过滤 | 搜索时过滤低置信度结果 |
| 测试6 | WorkingMemory上下文管理 | 上下文添加、获取、清理正常 |
| 测试7 | MemorySystem完整流程 | 三层记忆整合流程正常 |

## 💡 设计要点

### 置信度(Confidence)的作用
- **用户明确陈述**：confidence=1.0（用户说"我喜欢Python"）
- **系统推断**：confidence=0.5-0.8（用户经常问Python问题→推断喜欢Python）
- **工具提取**：confidence=0.7-0.9（工具解析的结构化数据）

### 记忆生命周期
```
创建 → 活跃(ACTIVE) → 归档(ARCHIVED) → 过期(EXPIRED) → 删除(DELETED)
  │         │              │               │
  │         └─ 正在使用    └─ 不再主动使用  └─ 等待清理
  └─ 刚创建
```

### 抽象接口的优势
1. **可替换实现**：内存→数据库→向量存储，接口不变
2. **测试友好**：可使用Mock实现进行单元测试
3. **扩展性**：新增存储类型只需实现接口

## 📝 课后练习

1. 实现一个基于SQLite的MemoryStore
2. 为Fact添加embedding字段，支持向量检索
3. 实现记忆重要性动态调整算法
4. 设计完整的记忆系统UML架构图

## 🔗 扩展阅读

- 《设计模式》接口模式部分
- LangChain Memory模块实现
- DeerFlow官方文档记忆系统部分
