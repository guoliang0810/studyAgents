# Day25 第98节课：Kubernetes部署 - 课后练习

## 练习概述
- 主题：使用Kubernetes部署Agent集群
- 建议完成时间：60分钟

## 练习目标
1. 理解K8s核心概念
2. 编写K8s配置
3. 实现弹性伸缩

## 概念理解题

### 练习1：K8s核心资源
**题目**: 解释Pod、Deployment、Service。

### 练习2：HPA
**题目**: 解释水平Pod自动伸缩器。

## 代码实现题

### 练习3：Deployment配置
**题目**: 编写Agent的Deployment配置。

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent
  template:
    metadata:
      labels:
        app: agent
    spec:
      containers:
      - name: agent
        image: agent:latest
        ports:
        - containerPort: 8000
```

### 练习4：Service配置
**题目**: 编写Service暴露Agent服务。

## 实战应用题

### 练习5：K8s监控
**题目**: 配置K8s监控和告警。

## 思考与分析题

### 练习6：K8s成本优化
**题目**: 如何优化K8s成本？
