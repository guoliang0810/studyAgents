"""
Day 7 Lesson 25: 工具发现与装配 (Tool Discovery and Assembly)

本模块包含工具发现与装配系统的完整实现，演示DeerFlow工具系统的五大设计原则：
1. 动态发现 - 运行时扫描和加载工具
2. 统一接口 - 所有工具实现标准接口
3. 安全沙箱 - 工具在受限环境中执行
4. 可配置性 - 支持多种发现策略和配置
5. 错误隔离 - 工具加载失败不影响系统

核心组件:
- ToolDiscovery: 动态工具发现器，扫描路径发现工具类
- ToolAssembly: 工具装配系统，加载和实例化工具
- ToolConfig: 工具配置管理，支持过滤和验证
- ToolRegistry: 工具注册表，管理已加载的工具
"""

__version__ = "1.0.0"
__author__ = "DeerFlow Python Agent架构师训练营"
__description__ = "工具发现与装配系统 - 课堂演示代码"
