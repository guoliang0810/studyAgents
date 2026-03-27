#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 9 Lesson 33: 虚拟路径架构 (Virtual Path System Architecture)

本模块提供虚拟路径系统架构的完整教学演示，包括：
1. VirtualPathSystem类 - 实现虚拟路径到实际路径的安全转换和映射
2. 路径映射管理 - 前缀映射、正则匹配、优先级管理等高级功能
3. 安全机制 - 路径遍历攻击检测、标准化处理、边界检查
4. 性能优化 - 路径翻译缓存、LRU策略、并发安全设计
5. 系统集成 - 与沙箱系统、技能系统、文件系统的集成方案

主要功能:
- 虚拟路径翻译: 将用户提供的虚拟路径安全转换为实际文件系统路径
- 映射规则管理: 支持多种映射规则（前缀匹配、正则匹配、精确匹配）
- 安全检测: 自动检测和阻止路径遍历攻击（如../跨目录访问）
- 跨平台兼容: 正确处理不同操作系统（Windows/Linux/macOS）的路径格式
- 缓存优化: LRU缓存加速频繁翻译的路径，提高系统性能
- 监控统计: 收集路径翻译统计信息，支持性能分析和问题诊断

使用示例:
    from virtual_path_demo import VirtualPathSystem
    
    # 创建虚拟路径系统
    vps = VirtualPathSystem(base_dir="/tmp/sandbox")
    
    # 添加映射规则
    vps.add_mapping("/workspace", "/tmp/workspace")
    
    # 翻译路径
    real_path = vps.translate("/workspace/project/file.txt")
    # 返回: /tmp/workspace/project/file.txt

学习目标:
1. 理解虚拟路径系统在沙箱环境中的重要性和设计原则
2. 掌握路径映射的基本原理和实现方式
3. 学习路径遍历攻击的检测和防范机制
4. 掌握虚拟路径系统的性能优化技巧
5. 理解虚拟路径系统与沙箱系统的集成方式

适用场景:
- 沙箱环境中的文件访问隔离
- 多租户系统的路径隔离
- 容器化环境中的路径虚拟化
- 安全敏感应用的文件访问控制
- 开发测试环境的路径重定向

版本: 1.0
作者: DeerFlow认证架构师讲师
日期: 2024年3月26日
"""

__version__ = "1.0.0"
__author__ = "DeerFlow认证架构师讲师"
__license__ = "CC BY-NC-SA 4.0"

# 导出主要类和函数
__all__ = [
    "VirtualPathSystem",
    "PathMappingRule",
    "PathSecurityCheck",
    "PathTranslationCache",
    "VirtualPathError",
    "PathTraversalError",
    "MappingNotFoundError",
    "PathNormalizer",
    "main_demo",
    "run_tests"
]

# 导入核心模块，确保正确的导入顺序
try:
    from .virtual_path_demo import (
        VirtualPathSystem,
        PathMappingRule,
        PathSecurityCheck,
        PathTranslationCache,
        VirtualPathError,
        PathTraversalError,
        MappingNotFoundError,
        PathNormalizer,
        main_demo,
        run_tests
    )
except ImportError:
    # 如果在virtual_path_demo.py完成前导入，提供占位符
    pass

print(f"✅ 加载虚拟路径架构演示模块 (版本 {__version__})")
print("📚 学习目标: 理解虚拟路径系统设计、路径映射原理、安全检测机制")
print("🚀 使用方法: python virtual_path_demo.py [--test|--demo|--help]")
print("💡 提示: 查看virtual_path_demo.py中的五部分结构代码示例\n")