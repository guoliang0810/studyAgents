#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 9 Lesson 35: 技能路径处理 (Skill Path Handling)

本模块提供技能路径处理的完整教学演示，包括：
1. 技能目录结构规范 - 标准化的技能目录设计和验证
2. 动态加载机制 - 使用importlib动态加载技能模块
3. 技能注册系统 - 技能的注册、查找、卸载管理
4. 路径安全处理 - 技能路径的安全检查和隔离
5. 技能生命周期管理 - 技能的初始化、运行、清理全流程

学习目标:
1. 理解技能目录结构的标准化设计原则
2. 掌握动态加载技能的核心机制和实现原理
3. 学习技能注册与系统集成的工作流程

版本: 1.0
作者: DeerFlow认证架构师讲师
日期: 2024年4月2日
"""

__version__ = "1.0.0"
__author__ = "DeerFlow认证架构师讲师"
__license__ = "CC BY-NC-SA 4.0"

__all__ = [
    "SkillMetadata",
    "SkillLoader",
    "SkillRegistry",
    "SkillPathValidator",
    "main_demo",
    "run_tests"
]

print(f"✅ 加载技能路径处理演示模块 (版本 {__version__})")
print("📚 学习目标: 掌握技能目录结构、动态加载、注册系统、安全处理")
print("🚀 使用方法: python skill_path_demo.py [--test|--demo|--help]\n")
