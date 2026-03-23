"""
Day 7 - 工具系统架构
演示工具发现、注册和执行机制
"""

from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass
from pydantic import BaseModel, Field


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: Type[BaseModel]
    handler: Callable


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._aliases: Dict[str, str] = {}
    
    def register(
        self,
        name: str,
        description: str,
        parameters: Type[BaseModel],
        handler: Callable,
        alias: Optional[str] = None
    ):
        """注册工具"""
        tool = ToolDefinition(name, description, parameters, handler)
        self._tools[name] = tool
        
        if alias:
            self._aliases[alias] = name
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        """获取工具"""
        real_name = self._aliases.get(name, name)
        return self._tools.get(real_name)
    
    def list_all(self) -> List[str]:
        """列出所有工具"""
        return list(self._tools.keys())
    
    def search(self, keyword: str) -> List[ToolDefinition]:
        """搜索工具"""
        results = []
        keyword = keyword.lower()
        for tool in self._tools.values():
            if keyword in tool.name.lower() or keyword in tool.description.lower():
                results.append(tool)
        return results


class ToolExecutor:
    """工具执行器"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
    
    def execute(self, name: str, params: dict) -> ToolResult:
        """执行工具"""
        tool = self.registry.get(name)
        
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error=f"工具 '{name}' 未找到"
            )
        
        try:
            validated_params = tool.parameters(**params)
            result = tool.handler(validated_params)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))


class CalculatorParams(BaseModel):
    """计算器参数"""
    expression: str = Field(description="数学表达式")


class SearchParams(BaseModel):
    """搜索参数"""
    query: str = Field(description="搜索关键词")
    max_results: int = Field(default=5, description="最大结果数")


# 创建全局注册表
_tool_registry = ToolRegistry()


def calculator_handler(params: CalculatorParams) -> str:
    """计算器处理器"""
    try:
        result = eval(params.expression)
        return f"结果: {result}"
    except Exception as e:
        raise ValueError(f"计算错误: {e}")


def search_handler(params: SearchParams) -> List[str]:
    """搜索处理器"""
    results = [f"结果{i}: {params.query}相关内容" for i in range(1, params.max_results + 1)]
    return results


# 注册工具
_tool_registry.register(
    "calculator",
    "执行数学计算",
    CalculatorParams,
    calculator_handler
)

_tool_registry.register(
    "search",
    "搜索网络信息",
    SearchParams,
    search_handler,
    alias="web_search"
)


def demonstrate_tool_system():
    """演示工具系统"""
    print("=" * 50)
    print("工具系统架构示例")
    print("=" * 50)
    
    executor = ToolExecutor(_tool_registry)
    
    # 列出工具
    print("\n已注册工具:")
    for name in _tool_registry.list_all():
        tool = _tool_registry.get(name)
        print(f"  - {name}: {tool.description}")
    
    # 搜索工具
    print("\n搜索'计算':")
    results = _tool_registry.search("计算")
    for tool in results:
        print(f"  - {tool.name}")
    
    # 执行工具
    print("\n执行计算器:")
    result = executor.execute("calculator", {"expression": "2 + 3 * 4"})
    print(f"  成功: {result.success}")
    print(f"  结果: {result.data}")


if __name__ == "__main__":
    demonstrate_tool_system()
