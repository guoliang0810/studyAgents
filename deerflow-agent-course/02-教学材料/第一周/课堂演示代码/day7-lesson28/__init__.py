# Day 7 Lesson 28: 实战：创建自定义工具
# 自定义工具开发演示代码包

"""
Day 7 Lesson 28: 实战：创建自定义工具

本模块演示如何从零开始创建自定义工具，包括：
1. 需求分析和接口设计
2. 安全设计和错误处理
3. 异步API调用和缓存实现
4. 工具注册和集成测试
5. 完整的测试套件和演示程序

主要类:
- BaseCustomTool: 自定义工具基类，定义标准接口
- WeatherTool: 天气查询工具，演示API调用和缓存
- ExchangeRateTool: 汇率查询工具，演示错误处理和重试机制
- ToolRegistry: 工具注册表，管理工具实例
- CustomToolsTestSuite: 测试套件，验证工具功能

使用示例:
    python custom_tools_demo.py --demo
    python custom_tools_demo.py --test
"""

__version__ = "1.0.0"
__author__ = "DeerFlow Python Agent架构师训练营"
__all__ = [
    "BaseCustomTool",
    "WeatherTool", 
    "ExchangeRateTool",
    "ToolRegistry",
    "CustomToolsTestSuite",
    "main_demo"
]