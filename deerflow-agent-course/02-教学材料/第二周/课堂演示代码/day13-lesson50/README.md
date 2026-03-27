# Day 13 - 第50节课：记忆提取流程实现

## 📚 课程概述

本节课深入讲解多级记忆提取算法的实现，包括相关性计算方法和五步提取流程。

## 🎯 学习目标

1. **掌握五步提取流程**：搜索→合并→去重→排序→截断
2. **理解相关性计算**：精确匹配、子串匹配、关键词匹配、TF-IDF
3. **学习提取策略配置**：优先级设置、阈值调整
4. **实践多级存储提取**：会话/短期/长期记忆的统一提取

## 📁 文件结构

```
day13-lesson50/
├── memory_extraction_demo.py    # 主演示代码
└── README.md                     # 本文件
```

## 🚀 运行方式

### 运行演示
```bash
python memory_extraction_demo.py
```

### 运行测试
```bash
python memory_extraction_demo.py --test
```

## 📖 核心概念

### 1. 五步提取流程

```
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│  搜索   │ → │  合并   │ → │  去重   │ → │  排序   │ → │  截断   │
│ Search  │   │ Merge   │   │ Dedup   │   │ Sort    │   │Truncate │
└─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

| 步骤 | 说明 |
|------|------|
| 搜索 | 从各存储层搜索候选记忆，计算相关性 |
| 合并 | 合并多层搜索结果，标记来源层 |
| 去重 | 基于内容相似度去除高度相似的记忆 |
| 排序 | 综合相关性、置信度、时间、访问次数排序 |
| 截断 | 截取top-k结果返回 |

### 2. 相关性计算方法

| 方法 | 原理 | 适用场景 |
|------|------|---------|
| 精确匹配 | 完全相同 | ID查询、精确查找 |
| 子串匹配 | 查询在内容中出现 | 短查询匹配 |
| 关键词匹配 | 关键词交集比例 | 多关键词查询 |
| TF-IDF | 词频×逆文档频率 | 长文本相关性 |
| 综合评分 | 加权组合 | 通用场景 |

### 3. 提取优先级

| 优先级 | 说明 | 权重分配 |
|--------|------|---------|
| RELEVANCE | 优先高相关性 | 相关性60%，置信度30%，时间10% |
| CONFIDENCE | 优先高置信度 | 置信度50%，相关性30%，时间20% |
| RECENCY | 优先最近创建 | 时间50%，相关性30%，置信度20% |
| ACCESS_COUNT | 优先常访问 | 访问40%，相关性40%，置信度20% |

## 🔧 核心类说明

### RelevanceCalculator

相关性计算器，实现多种匹配方法。

```python
calc = RelevanceCalculator()
score = calc.calculate_composite("Python编程", "用户是Python开发者")
# 返回 0.0-1.0 的相关性分数
```

### ExtractionStrategy

提取策略配置。

```python
strategy = ExtractionStrategy(
    max_results=10,           # 最大返回数
    min_relevance=0.1,        # 最小相关性
    priority=ExtractionPriority.RELEVANCE,
    enable_deduplication=True
)
```

### MemoryExtractor

记忆提取器，实现五步流程。

```python
extractor = MemoryExtractor(strategy)
result = extractor.extract("查询", {"long_term": facts})
print(result.facts)  # 提取的记忆列表
```

### MultiLevelExtractor

多级存储提取器。

```python
multi_extractor = MultiLevelExtractor()
result = multi_extractor.extract("查询", {
    "session": session_facts,
    "short_term": short_term_facts,
    "long_term": long_term_facts
})
```

## 📊 测试用例

| 测试 | 说明 | 预期结果 |
|------|------|---------|
| 测试1 | 精确匹配计算 | 相同返回1.0，不同返回0.0 |
| 测试2 | 子串匹配计算 | 完全包含返回1.0 |
| 测试3 | 关键词匹配计算 | 有交集返回>0 |
| 测试4 | 五步提取流程 | 正确提取并限制数量 |
| 测试5 | 去重功能 | 相似内容被合并 |
| 测试6 | 多级提取 | 从多层正确提取 |

## 💡 设计要点

### 去重策略
- 基于关键词相似度（Jaccard系数）
- 阈值可配置（默认0.8）
- 保留优先级更高的层的结果

### 时间衰减
```
时间分数 = exp(-衰减因子 × 时间差(秒))
```
- 衰化因子越大，衰减越快
- 会话记忆：0.01（快速衰减）
- 短期记忆：0.001（中等衰减）
- 长期记忆：0.0001（缓慢衰减）

### 多级优先级
```
会话记忆 > 短期记忆 > 长期记忆
```
当同一记忆出现在多层时，保留优先级更高的来源。

## 📝 课后练习

1. 实现基于向量相似度的相关性计算
2. 添加搜索结果缓存机制
3. 实现自适应阈值调整
4. 添加提取性能监控

## 🔗 扩展阅读

- TF-IDF算法详解
- 余弦相似度计算
- 向量检索技术（FAISS）
- DeerFlow官方文档记忆提取部分
