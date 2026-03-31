#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第94节课：工具扩展机制

本课程介绍DeerFlow工具扩展机制，包括：
1. 自定义工具开发 - 从简单函数到生产级工具
2. 工具打包 - 将工具集打包为可分发模块
3. 工具发现 - 自动发现和注册自定义工具

作者：DeerFlow架构师训练营
"""

import inspect
import importlib
import os
import json
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import unittest.mock as unittest


# ============================================================
# 第一部分：工具基类与装饰器
# ============================================================

class ToolCategory(Enum):
    """工具类别"""
    FILE = "file"
    NETWORK = "network"
    SYSTEM = "system"
    DATA = "data"
    AI = "ai"
    CUSTOM = "custom"


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    category: ToolCategory
    tags: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


class BaseTool:
    """工具基类"""
    
    def __init__(self, name: str, description: str, category: ToolCategory = ToolCategory.CUSTOM):
        self.metadata = ToolMetadata(
            name=name,
            description=description,
            category=category
        )
        
    def execute(self, **kwargs) -> Any:
        """执行工具"""
        raise NotImplementedError
        
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        return True
        
    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数模式"""
        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "parameters": self.metadata.parameters
        }


def tool(name: str, description: str, category: ToolCategory = ToolCategory.CUSTOM):
    """
    工具装饰器
    
    将函数转换为DeerFlow工具。
    """
    def decorator(func: Callable) -> Callable:
        # 创建工具包装类
        class FunctionTool(BaseTool):
            def __init__(self):
                super().__init__(name, description, category)
                self._func = func
                self.metadata.parameters = self._extract_parameters()
                
            def _extract_parameters(self) -> Dict[str, Any]:
                sig = inspect.signature(func)
                params = {}
                for param_name, param in sig.parameters.items():
                    params[param_name] = {
                        "type": param.annotation.__name__ if param.annotation != inspect.Parameter.empty else "any",
                        "default": param.default if param.default != inspect.Parameter.empty else None,
                        "required": param.default == inspect.Parameter.empty
                    }
                return params
                
            def execute(self, **kwargs) -> Any:
                return self._func(**kwargs)
                
        # 返回工具实例
        tool_instance = FunctionTool()
        tool_instance._original_func = func
        return tool_instance
        
    return decorator


# ============================================================
# 第二部分：工具注册与管理
# ============================================================

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {}
        
    def register(self, tool: BaseTool, name: Optional[str] = None) -> None:
        """注册工具"""
        tool_name = name or tool.metadata.name
        self._tools[tool_name] = tool
        
        # 更新类别索引
        category = tool.metadata.category
        if category not in self._categories:
            self._categories[category] = []
        if tool_name not in self._categories[category]:
            self._categories[category].append(tool_name)
            
    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name not in self._tools:
            return False
            
        tool = self._tools[name]
        category = tool.metadata.category
        
        if category in self._categories and name in self._categories[category]:
            self._categories[category].remove(name)
            
        del self._tools[name]
        return True
        
    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)
        
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[str]:
        """列出工具"""
        if category:
            return self._categories.get(category, []).copy()
        return list(self._tools.keys())
        
    def search(self, query: str) -> List[str]:
        """搜索工具"""
        query = query.lower()
        results = []
        
        for name, tool in self._tools.items():
            # 搜索名称和描述
            if query in name.lower():
                results.append(name)
            elif query in tool.metadata.description.lower():
                results.append(name)
            # 搜索标签
            elif any(query in tag.lower() for tag in tool.metadata.tags):
                results.append(name)
                
        return results
        
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具模式"""
        return [tool.get_schema() for tool in self._tools.values()]


# ============================================================
# 第三部分：工具发现与加载
# ============================================================

class ToolLoader:
    """工具加载器"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._discovered: Dict[str, str] = {}  # name -> module_path
        
    def discover_from_directory(self, directory: str, pattern: str = "*.py") -> int:
        """
        从目录发现工具
        
        Args:
            directory: 目录路径
            pattern: 文件模式
            
        Returns:
            发现的数量
        """
        import glob
        
        count = 0
        for filepath in glob.glob(os.path.join(directory, pattern)):
            if os.path.basename(filepath).startswith("_"):
                continue
                
            # 加载模块
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            try:
                # 添加到路径
                import sys
                if directory not in sys.path:
                    sys.path.insert(0, directory)
                    
                module = importlib.import_module(module_name)
                
                # 查找工具类或装饰器
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    
                    if isinstance(attr, BaseTool):
                        self.registry.register(attr)
                        self._discovered[attr.metadata.name] = filepath
                        count += 1
                        
            except Exception as e:
                print(f"加载工具失败 {filepath}: {e}")
                
        return count
        
    def load_tool_config(self, config_path: str) -> None:
        """从配置文件加载工具配置"""
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        for tool_config in config.get("tools", []):
            name = tool_config.get("name")
            enabled = tool_config.get("enabled", True)
            
            if not enabled:
                self.registry.unregister(name)


# ============================================================
# 第四部分：工具执行器
# ============================================================

class ToolExecutor:
    """工具执行器"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._execution_history: List[Dict[str, Any]] = []
        
    def execute(self, tool_name: str, params: Dict[str, Any],
                user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            params: 参数
            user_context: 用户上下文
            
        Returns:
            执行结果
        """
        start_time = __import__("time").time()
        
        tool = self.registry.get(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"工具不存在: {tool_name}"
            }
            
        # 验证参数
        if not tool.validate_params(params):
            return {
                "success": False,
                "error": "参数验证失败"
            }
            
        try:
            # 执行工具
            result = tool.execute(**params)
            
            duration = time.time() - start_time
            
            # 记录执行历史
            self._execution_history.append({
                "tool": tool_name,
                "params": params,
                "result": result,
                "duration": duration,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {
                "success": True,
                "result": result,
                "duration": duration
            }
            
        except Exception as e:
            duration = time.time() - start_time
            
            return {
                "success": False,
                "error": str(e),
                "duration": duration
            }
            
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self._execution_history[-limit:]


import time
from datetime import datetime


# ============================================================
# 第五部分：示例工具
# ============================================================

@tool(name="calculate", description="执行数学计算", category=ToolCategory.DATA)
def calculate_tool(expression: str) -> str:
    """计算数学表达式"""
    try:
        # 安全评估（仅用于演示）
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            raise ValueError("不允许的字符")
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {str(e)}"


@tool(name="text_reverse", description="反转文本", category=ToolCategory.DATA)
def reverse_text(text: str) -> str:
    """反转文本"""
    return text[::-1]


class FileSearchTool(BaseTool):
    """文件搜索工具"""
    
    def __init__(self):
        super().__init__(
            name="file_search",
            description="在目录中搜索文件",
            category=ToolCategory.FILE
        )
        self.metadata.tags = ["file", "search"]
        
    def execute(self, directory: str, pattern: str = "*", 
                recursive: bool = False) -> List[str]:
        import glob
        results = []
        
        if recursive:
            pattern = f"**/{pattern}"
            
        for match in glob.glob(os.path.join(directory, pattern), 
                             recursive=recursive):
            if os.path.isfile(match):
                results.append(match)
                
        return results


# ============================================================
# 第六部分：演示与测试
# ============================================================

def run_demo():
    """演示工具扩展系统"""
    print("=" * 60)
    print("DeerFlow 工具扩展机制演示")
    print("=" * 60)
    
    # 创建注册表
    print("\n1. 创建工具注册表...")
    registry = ToolRegistry()
    
    # 注册内置工具
    print("\n2. 注册工具...")
    registry.register(calculate_tool)
    registry.register(reverse_text)
    registry.register(FileSearchTool())
    
    print(f"   注册工具数量: {len(registry.list_tools())}")
    print(f"   工具列表: {registry.list_tools()}")
    
    # 执行工具
    print("\n3. 执行工具...")
    executor = ToolExecutor(registry)
    
    result = executor.execute("calculate", {"expression": "2 + 3 * 4"})
    print(f"   calculate(2 + 3 * 4) = {result}")
    
    result = executor.execute("text_reverse", {"text": "DeerFlow"})
    print(f"   text_reverse('DeerFlow') = {result}")
    
    # 搜索工具
    print("\n4. 搜索工具...")
    results = registry.search("text")
    print(f"   搜索'text'结果: {results}")
    
    # 获取模式
    print("\n5. 获取工具模式...")
    schemas = registry.get_all_schemas()
    print(f"   模式数量: {len(schemas)}")
    
    print("\n演示完成!")


def run_tests():
    """运行测试"""
    print("\n" + "=" * 60)
    print("运行单元测试")
    print("=" * 60 + "\n")
    
    # 测试1: 工具注册
    print("测试1: 工具注册")
    reg = ToolRegistry()
    reg.register(calculate_tool)
    reg.register(reverse_text)
    assert "calculate" in reg.list_tools()
    assert "text_reverse" in reg.list_tools()
    print(f"   注册工具: {reg.list_tools()}")
    print("✓ 工具注册测试通过\n")
    
    # 测试2: 工具获取
    print("测试2: 工具获取")
    tool = reg.get("calculate")
    assert tool is not None
    assert tool.metadata.name == "calculate"
    print("✓ 工具获取测试通过\n")
    
    # 测试3: 工具执行
    print("测试3: 工具执行")
    executor = ToolExecutor(reg)
    result = executor.execute("calculate", {"expression": "10 + 20"})
    assert result["success"] == True
    assert result["result"] == "30"
    print(f"   10 + 20 = {result['result']}")
    print("✓ 工具执行测试通过\n")
    
    # 测试4: 搜索工具
    print("测试4: 搜索工具")
    results = reg.search("calculate")
    assert "calculate" in results
    print(f"   搜索结果: {results}")
    print("✓ 搜索测试通过\n")
    
    # 测试5: 文件搜索工具
    print("测试5: 文件搜索工具")
    file_tool = FileSearchTool()
    schema = file_tool.get_schema()
    assert schema["name"] == "file_search"
    print(f"   工具模式: {schema['name']}")
    print("✓ 文件搜索工具测试通过\n")
    
    print("=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        run_tests()
    else:
        run_demo()
