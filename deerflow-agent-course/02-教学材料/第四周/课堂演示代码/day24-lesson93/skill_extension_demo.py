#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能扩展架构 - 演示代码

本模块展示DeerFlow技能系统的扩展架构。
包含：技能定义、注册表、编排、生命周期管理。

本代码是DeerFlow架构师训练营第93节课的演示代码，
帮助学员掌握技能扩展的核心技能。

作者: DeerFlow架构师训练营
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json


# ============================================================================
# 第一部分：技能定义
# ============================================================================

class SkillCategory(Enum):
    """技能分类"""
    TOOL = "tool"               # 工具技能
    KNOWLEDGE = "knowledge"       # 知识技能
    ACTION = "action"            # 行动技能
    ANALYSIS = "analysis"        # 分析技能


@dataclass
class SkillMetadata:
    """技能元数据"""
    name: str
    category: SkillCategory
    description: str
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "dependencies": self.dependencies
        }


class Skill(ABC):
    """技能基类
    
    所有技能必须继承自此类并实现必要的方法
    """
    
    def __init__(self, metadata: SkillMetadata):
        self.metadata = metadata
        self._enabled = True
    
    @property
    def name(self) -> str:
        return self.metadata.name
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行技能
        
        Args:
            context: 执行上下文
            
        Returns:
            执行结果
        """
        pass
    
    @abstractmethod
    def validate_input(self, input_data: Any) -> bool:
        """验证输入
        
        Args:
            input_data: 输入数据
            
        Returns:
            是否有效
        """
        pass
    
    def enable(self):
        """启用技能"""
        self._enabled = True
    
    def disable(self):
        """禁用技能"""
        self._enabled = False


# ============================================================================
# 第二部分：技能实现示例
# ============================================================================

class CalculatorSkill(Skill):
    """计算器技能"""
    
    def __init__(self):
        super().__init__(SkillMetadata(
            name="calculator",
            category=SkillCategory.TOOL,
            description="执行数学计算",
            tags=["math", "calculator"]
        ))
    
    def validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, dict) and "expression" in input_data
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        expression = context.get("expression", "0")
        try:
            result = eval(expression)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


class SearchSkill(Skill):
    """搜索技能"""
    
    def __init__(self):
        super().__init__(SkillMetadata(
            name="search",
            category=SkillCategory.TOOL,
            description="搜索信息",
            tags=["search", "information"]
        ))
        self._mock_results = {
            "python": "Python是一种高级编程语言",
            "ai": "人工智能是计算机科学的一个分支",
        }
    
    def validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, dict) and "query" in input_data
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        query = context.get("query", "").lower()
        result = self._mock_results.get(query, "未找到相关信息")
        return {"success": True, "result": result, "query": query}


class AnalysisSkill(Skill):
    """分析技能"""
    
    def __init__(self):
        super().__init__(SkillMetadata(
            name="analysis",
            category=SkillCategory.ANALYSIS,
            description="分析数据并提供洞察",
            tags=["analysis", "insight"]
        ))
    
    def validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, dict) and "data" in input_data
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        data = context.get("data", [])
        
        if not isinstance(data, list):
            data = [data]
        
        # 简单分析
        analysis = {
            "count": len(data),
            "type": type(data[0]).__name__ if data else "empty",
            "insights": [
                "数据量适中",
                "建议进行更深入的分析"
            ]
        }
        
        return {"success": True, "analysis": analysis}


# ============================================================================
# 第三部分：技能注册表
# ============================================================================

class SkillRegistry:
    """技能注册表
    
    管理所有可用技能的注册和发现
    
    使用示例:
        registry = SkillRegistry()
        registry.register(CalculatorSkill())
        skill = registry.get("calculator")
    """
    
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._categories: Dict[SkillCategory, List[str]] = {}
    
    def register(self, skill: Skill) -> None:
        """注册技能
        
        Args:
            skill: 技能实例
        """
        if skill.name in self._skills:
            raise ValueError(f"技能 {skill.name} 已存在")
        
        self._skills[skill.name] = skill
        
        # 更新分类索引
        category = skill.metadata.category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(skill.name)
    
    def unregister(self, name: str) -> bool:
        """注销技能
        
        Args:
            name: 技能名称
            
        Returns:
            是否成功
        """
        if name not in self._skills:
            return False
        
        skill = self._skills[name]
        category = skill.metadata.category
        
        del self._skills[name]
        self._categories[category].remove(name)
        
        return True
    
    def get(self, name: str) -> Optional[Skill]:
        """获取技能
        
        Args:
            name: 技能名称
            
        Returns:
            技能实例，不存在返回None
        """
        return self._skills.get(name)
    
    def get_by_category(self, category: SkillCategory) -> List[Skill]:
        """按分类获取技能
        
        Args:
            category: 技能分类
            
        Returns:
            技能列表
        """
        names = self._categories.get(category, [])
        return [self._skills[name] for name in names]
    
    def list_all(self) -> List[str]:
        """列出所有技能
        
        Returns:
            技能名称列表
        """
        return list(self._skills.keys())
    
    def search(self, tag: str) -> List[Skill]:
        """按标签搜索
        
        Args:
            tag: 标签
            
        Returns:
            匹配的技能列表
        """
        results = []
        for skill in self._skills.values():
            if tag in skill.metadata.tags:
                results.append(skill)
        return results


# ============================================================================
# 第四部分：技能编排器
# ============================================================================

class SkillOrchestrator:
    """技能编排器
    
    协调多个技能的执行
    
    使用示例:
        orchestrator = SkillOrchestrator(registry)
        result = await orchestrator.execute_skill("calculator", {"expression": "1+1"})
    """
    
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.execution_history: List[Dict] = []
    
    async def execute_skill(
        self,
        skill_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行单个技能
        
        Args:
            skill_name: 技能名称
            context: 执行上下文
            
        Returns:
            执行结果
        """
        skill = self.registry.get(skill_name)
        
        if not skill:
            return {"success": False, "error": f"技能 {skill_name} 不存在"}
        
        if not skill.enabled:
            return {"success": False, "error": f"技能 {skill_name} 已禁用"}
        
        # 验证输入
        if not skill.validate_input(context):
            return {"success": False, "error": "输入验证失败"}
        
        # 执行
        try:
            result = await skill.execute(context)
            self.execution_history.append({
                "skill": skill_name,
                "context": context,
                "result": result
            })
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_chain(
        self,
        chain: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """执行技能链
        
        Args:
            chain: 技能链配置
            
        Returns:
            结果列表
        """
        results = []
        context = {}
        
        for step in chain:
            skill_name = step.get("skill")
            input_data = step.get("input", {})
            
            # 合并上下文
            context.update(input_data)
            
            # 执行
            result = await self.execute_skill(skill_name, context)
            results.append(result)
            
            # 检查是否需要停止
            if not result.get("success", False):
                break
        
        return results
    
    def get_execution_history(self) -> List[Dict]:
        """获取执行历史"""
        return self.execution_history.copy()


# ============================================================================
# 第五部分：技能生命周期管理
# ============================================================================

class SkillLifecycleManager:
    """技能生命周期管理器
    
    管理技能的安装、卸载、启用、禁用等生命周期
    """
    
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self._install_callbacks: List[Callable] = []
        self._uninstall_callbacks: List[Callable] = []
    
    def on_install(self, callback: Callable):
        """注册安装回调"""
        self._install_callbacks.append(callback)
    
    def on_uninstall(self, callback: Callable):
        """注册卸载回调"""
        self._uninstall_callbacks.append(callback)
    
    async def install_skill(self, skill: Skill) -> bool:
        """安装技能
        
        Args:
            skill: 技能实例
            
        Returns:
            是否成功
        """
        try:
            # 检查依赖
            for dep in skill.metadata.dependencies:
                if not self.registry.get(dep):
                    raise ValueError(f"缺少依赖: {dep}")
            
            # 注册技能
            self.registry.register(skill)
            
            # 触发回调
            for callback in self._install_callbacks:
                await callback(skill)
            
            return True
        except Exception as e:
            print(f"安装技能失败: {e}")
            return False
    
    async def uninstall_skill(self, name: str) -> bool:
        """卸载技能
        
        Args:
            name: 技能名称
            
        Returns:
            是否成功
        """
        skill = self.registry.get(name)
        if not skill:
            return False
        
        # 注销
        success = self.registry.unregister(name)
        
        if success:
            # 触发回调
            for callback in self._uninstall_callbacks:
                await callback(skill)
        
        return success


# ============================================================================
# 演示代码
# ============================================================================

async def run_skill_demo():
    """运行技能演示"""
    print("=" * 70)
    print("DeerFlow技能扩展架构演示")
    print("=" * 70)
    
    # 1. 创建注册表
    print("\n### 1. 创建技能注册表")
    registry = SkillRegistry()
    
    # 2. 注册技能
    print("\n### 2. 注册技能")
    calculator = CalculatorSkill()
    search = SearchSkill()
    analysis = AnalysisSkill()
    
    registry.register(calculator)
    registry.register(search)
    registry.register(analysis)
    
    print(f"已注册技能: {registry.list_all()}")
    
    # 3. 获取技能
    print("\n### 3. 获取技能")
    skill = registry.get("calculator")
    print(f"获取计算器: {skill.name if skill else 'None'}")
    
    # 4. 按分类获取
    print("\n### 4. 按分类获取")
    tools = registry.get_by_category(SkillCategory.TOOL)
    print(f"工具类技能: {[s.name for s in tools]}")
    
    # 5. 技能编排
    print("\n### 5. 技能编排")
    orchestrator = SkillOrchestrator(registry)
    
    result = await orchestrator.execute_skill(
        "calculator",
        {"expression": "1+2*3"}
    )
    print(f"计算结果: {result}")
    
    # 6. 技能链
    print("\n### 6. 执行技能链")
    chain = [
        {"skill": "search", "input": {"query": "python"}},
        {"skill": "analysis", "input": {"data": ["test"]}},
    ]
    chain_results = await orchestrator.execute_chain(chain)
    print(f"技能链结果: {chain_results}")
    
    # 7. 生命周期管理
    print("\n### 7. 生命周期管理")
    lifecycle = SkillLifecycleManager(registry)
    
    async def on_install(skill):
        print(f"技能已安装: {skill.name}")
    
    lifecycle.on_install(on_install)
    
    # 8. 搜索
    print("\n### 8. 技能搜索")
    results = registry.search("math")
    print(f"搜索'math'标签: {[s.name for s in results]}")
    
    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_skill_demo())
