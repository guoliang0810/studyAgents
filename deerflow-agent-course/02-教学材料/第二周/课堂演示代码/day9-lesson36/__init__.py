#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 9 Lesson 36: 沙箱安全机制 (Sandbox Security Mechanism)

本模块提供沙箱安全机制的完整教学演示，包括：
1. 多层防御体系 - 文件系统隔离、网络隔离、进程隔离、资源限制
2. 权限控制机制 - 能力限制、系统调用过滤、访问控制列表
3. 安全审计系统 - 审计日志记录、异常检测、安全事件分析
4. 威胁检测与响应 - 入侵检测、自动响应、安全告警
5. 安全配置管理 - 安全策略配置、合规检查、安全加固

学习目标:
1. 理解沙箱安全的多层防御体系架构
2. 掌握资源限制和权限控制的实现方式
3. 了解安全审计和威胁检测的设计方法

版本: 1.0
作者: DeerFlow认证架构师讲师
日期: 2024年4月2日
"""

__version__ = "1.0.0"
__author__ = "DeerFlow认证架构师讲师"
__license__ = "CC BY-NC-SA 4.0"

__all__ = [
    "SecurityLevel",
    "SandboxSecurityConfig",
    "SecurityAuditor",
    "ResourceLimiter",
    "PermissionController",
    "ThreatDetector",
    "main_demo",
    "run_tests"
]

print(f"✅ 加载沙箱安全机制演示模块 (版本 {__version__})")
print("📚 学习目标: 掌握多层防御、权限控制、安全审计、威胁检测")
print("🚀 使用方法: python sandbox_security_demo.py [--test|--demo|--help]\n")
