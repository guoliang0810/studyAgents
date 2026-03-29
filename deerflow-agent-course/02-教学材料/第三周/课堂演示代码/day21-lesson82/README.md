# Pytest配置与夹具

## 课程概述

本节课介绍Pytest配置和夹具的使用。

## 学习目标

- 掌握Pytest配置
- 学会使用fixture
- 掌握参数化测试

## 课程内容

### Fixture类型

- function: 默认，每个函数调用
- class: 每个类
- module: 每个模块
- session: 整个测试会话

### 参数化测试

使用`@pytest.mark.parametrize`实现参数化测试。

## 使用方法

```bash
pytest lesson_demo.py -v
```
