# Day25 第99节课：CI/CD流水线 - 课后练习

## 练习概述
- 主题：构建CI/CD流水线
- 建议完成时间：60分钟

## 练习目标
1. 理解CI/CD概念
2. 设计流水线
3. 自动化部署

## 概念理解题

### 练习1：CI vs CD
**题目**: 解释CI和CD的区别。

### 练习2：蓝绿部署
**题目**: 解释蓝绿部署策略。

## 代码实现题

### 练习3：GitHub Actions
**题目**: 编写CI流水线配置。

```yaml
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: pytest
      - name: Build
        run: docker build .
```

### 练习4：CD流水线
**题目**: 编写CD部署配置。

## 实战应用题

### 练习5：回滚策略
**题目**: 设计自动回滚机制。

## 思考与分析题

### 练习6：流水线安全
**题目**: 分析流水线安全考虑。
