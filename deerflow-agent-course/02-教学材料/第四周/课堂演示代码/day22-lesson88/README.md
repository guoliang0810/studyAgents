# 第88节课：监控与指标

## 课程目标

本课程介绍DeerFlow Agent系统中的监控与指标系统，包括：
- 结构化日志系统 - 实现统一的日志格式和级别管理
- 性能指标收集 - Counter、Gauge、Histogram指标类型
- 健康检查机制 - 多层次服务可用性检测
- 告警系统 - 基于阈值的告警触发和通知

## 核心概念

### 1. 结构化日志
- JSON格式输出，便于日志收集和分析
- 上下文信息自动注入（请求ID、用户ID等）
- 线程安全设计

### 2. 指标类型
- **Counter**: 累计值，只能增加（请求数、错误数）
- **Gauge**: 瞬时值，可增可减（内存使用量、连接数）
- **Histogram**: 直方图，统计分布（响应时间）

### 3. 健康检查
- 依赖服务检查
- 资源使用检查（CPU、内存、磁盘）
- 整体状态聚合

### 4. 告警系统
- 规则定义和触发
- 冷却时间避免告警风暴
- 多级别告警（INFO、WARNING、ERROR、CRITICAL）

## 运行演示

```bash
python monitoring_demo.py
```

## 运行测试

```bash
python monitoring_demo.py --test
```

## 关键代码

### 创建监控系统
```python
monitor = DeerFlowMonitor()

# 记录请求
monitor.record_request(duration=0.5, is_error=False)

# 获取状态
status = monitor.get_status()
```

### 导出Prometheus格式
```python
print(monitor.metrics.export_prometheus())
```
