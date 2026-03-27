#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 9 Lesson 35: 技能路径处理

本文件演示技能路径处理的完整实现，包括：
1. 技能目录结构规范 - 标准化的技能目录设计和验证
2. 动态加载机制 - 使用importlib动态加载技能模块
3. 技能注册系统 - 技能的注册、查找、卸载管理
4. 路径安全处理 - 技能路径的安全检查和隔离
5. 技能生命周期管理 - 技能的初始化、运行、清理全流程

使用示例:
    python skill_path_demo.py          # 运行基本演示
    python skill_path_demo.py --test   # 运行测试套件
    python skill_path_demo.py --demo   # 运行完整演示
    python skill_path_demo.py --help   # 显示帮助信息
"""

import os
import sys
import json
import time
import importlib.util
import importlib
import argparse
import tempfile
import shutil
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import logging

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================

class SkillStatus(Enum):
    """技能状态枚举"""
    CREATED = "已创建"
    LOADED = "已加载"
    INITIALIZED = "已初始化"
    ACTIVE = "活跃"
    ERROR = "错误"
    UNLOADED = "已卸载"

class SkillType(Enum):
    """技能类型枚举"""
    TOOL = "工具技能"
    COMMAND = "命令技能"
    WORKFLOW = "工作流技能"
    AGENT = "代理技能"

@dataclass
class SkillMetadata:
    """技能元数据"""
    name: str                           # 技能名称
    version: str                        # 技能版本
    description: str                    # 技能描述
    author: str = ""                    # 作者
    skill_type: SkillType = SkillType.TOOL  # 技能类型
    dependencies: List[str] = field(default_factory=list)  # 依赖
    entry_point: str = "main.py"        # 入口文件
    config_file: str = "config.json"    # 配置文件
    status: SkillStatus = SkillStatus.CREATED  # 状态
    loaded_at: Optional[float] = None   # 加载时间
    skill_path: str = ""                # 技能路径
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SkillMetadata":
        data["skill_type"] = SkillType(data.get("skill_type", "工具技能"))
        data["status"] = SkillStatus(data.get("status", "已创建"))
        return cls(**data)

@dataclass
class SkillResult:
    """技能执行结果"""
    skill_name: str                     # 技能名称
    success: bool                       # 是否成功
    output: Any = None                  # 输出结果
    error: Optional[str] = None         # 错误信息
    execution_time: float = 0.0         # 执行时间
    metadata: Optional[SkillMetadata] = None  # 技能元数据

# ============================================================================
# 第二部分：核心功能实现
# ============================================================================

class SkillPathError(Exception):
    """技能路径错误"""
    pass

class SkillLoadError(SkillPathError):
    """技能加载错误"""
    pass

class SkillPathValidator:
    """技能路径验证器"""
    
    # 标准技能目录结构
    REQUIRED_FILES = ["__init__.py", "main.py"]
    RECOMMENDED_FILES = ["config.json", "README.md", "requirements.txt"]
    
    def __init__(self, base_dir: str = "/skills"):
        self.base_dir = base_dir
    
    def validate_skill_path(self, skill_path: str) -> Tuple[bool, List[str]]:
        """验证技能路径是否有效"""
        errors = []
        
        # 检查路径是否在基础目录下
        if not skill_path.startswith(self.base_dir):
            errors.append(f"技能路径不在基础目录下: {skill_path}")
            return False, errors
        
        # 检查目录是否存在
        if not os.path.exists(skill_path):
            errors.append(f"技能目录不存在: {skill_path}")
            return False, errors
        
        # 检查必需文件
        for req_file in self.REQUIRED_FILES:
            file_path = os.path.join(skill_path, req_file)
            if not os.path.exists(file_path):
                errors.append(f"缺少必需文件: {req_file}")
        
        return len(errors) == 0, errors
    
    def validate_skill_name(self, name: str) -> bool:
        """验证技能名称是否合法"""
        # 技能名称只能包含字母、数字、下划线、连字符
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))
    
    def get_skill_structure(self) -> Dict[str, Any]:
        """获取标准技能目录结构"""
        return {
            "required": self.REQUIRED_FILES,
            "recommended": self.RECOMMENDED_FILES,
            "optional": ["tests/", "docs/", "assets/"],
            "example": {
                "__init__.py": "# 技能初始化文件\n__version__ = '1.0.0'\n",
                "main.py": "# 技能主入口\n\ndef run(context):\n    return {'success': True}\n",
                "config.json": '{"name": "example", "version": "1.0.0"}',
                "README.md": "# 技能说明\n\n本技能的功能说明。\n",
            }
        }

class SkillLoader:
    """技能加载器"""
    
    def __init__(self, skills_dir: str = "/skills"):
        self.skills_dir = skills_dir
        self.loaded_modules: Dict[str, Any] = {}
        self.logger = logging.getLogger("SkillLoader")
    
    def load_skill(self, skill_name: str) -> Tuple[bool, Optional[Any], List[str]]:
        """动态加载技能模块"""
        errors = []
        
        # 构建技能路径
        skill_path = os.path.join(self.skills_dir, skill_name)
        
        # 验证技能路径
        validator = SkillPathValidator(self.skills_dir)
        is_valid, validation_errors = validator.validate_skill_path(skill_path)
        if not is_valid:
            return False, None, validation_errors
        
        # 检查是否已加载
        if skill_name in self.loaded_modules:
            return True, self.loaded_modules[skill_name], ["技能已加载"]
        
        try:
            # 动态加载主模块
            main_path = os.path.join(skill_path, "main.py")
            spec = importlib.util.spec_from_file_location(f"skill_{skill_name}", main_path)
            if spec is None or spec.loader is None:
                return False, None, ["无法加载模块规格"]
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"skill_{skill_name}"] = module
            spec.loader.exec_module(module)
            
            self.loaded_modules[skill_name] = module
            self.logger.info(f"成功加载技能: {skill_name}")
            return True, module, []
            
        except Exception as e:
            error_msg = f"加载技能失败: {e}"
            self.logger.error(error_msg)
            return False, None, [error_msg]
    
    def unload_skill(self, skill_name: str) -> bool:
        """卸载技能"""
        if skill_name in self.loaded_modules:
            module_name = f"skill_{skill_name}"
            if module_name in sys.modules:
                del sys.modules[module_name]
            del self.loaded_modules[skill_name]
            self.logger.info(f"成功卸载技能: {skill_name}")
            return True
        return False
    
    def get_skill_function(self, skill_name: str, function_name: str = "run") -> Optional[Callable]:
        """获取技能函数"""
        if skill_name not in self.loaded_modules:
            return None
        
        module = self.loaded_modules[skill_name]
        return getattr(module, function_name, None)

class SkillRegistry:
    """技能注册表"""
    
    def __init__(self, skills_dir: str = "/skills"):
        self.skills_dir = skills_dir
        self.skills: Dict[str, SkillMetadata] = {}
        self.loader = SkillLoader(skills_dir)
        self.validator = SkillPathValidator(skills_dir)
        self.logger = logging.getLogger("SkillRegistry")
    
    def register_skill(self, skill_path: str) -> Tuple[bool, Optional[SkillMetadata], List[str]]:
        """注册技能"""
        errors = []
        
        # 验证路径
        is_valid, validation_errors = self.validator.validate_skill_path(skill_path)
        if not is_valid:
            return False, None, validation_errors
        
        # 读取技能元数据
        config_path = os.path.join(skill_path, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                config = {}
                errors.append(f"读取配置文件失败: {e}")
        else:
            config = {}
            errors.append("配置文件不存在，使用默认元数据")
        
        # 创建技能元数据
        skill_name = os.path.basename(skill_path)
        # 获取技能类型，支持多种格式
        skill_type_str = config.get("skill_type") or config.get("type", "TOOL")
        try:
            skill_type = SkillType[skill_type_str.upper()] if skill_type_str.upper() in SkillType.__members__ else SkillType.TOOL
        except:
            skill_type = SkillType.TOOL
        
        metadata = SkillMetadata(
            name=skill_name,
            version=config.get("version", "1.0.0"),
            description=config.get("description", f"技能: {skill_name}"),
            author=config.get("author", ""),
            skill_type=skill_type,
            dependencies=config.get("dependencies", []),
            entry_point=config.get("entry_point", "main.py"),
            config_file=config.get("config_file", "config.json"),
            skill_path=skill_path,
            loaded_at=time.time()
        )
        
        # 加载技能
        success, module, load_errors = self.loader.load_skill(skill_name)
        if success:
            metadata.status = SkillStatus.LOADED
        else:
            metadata.status = SkillStatus.ERROR
            errors.extend(load_errors)
        
        # 注册到表
        self.skills[skill_name] = metadata
        self.logger.info(f"注册技能: {skill_name} (状态: {metadata.status.value})")
        
        return len(errors) == 0 or success, metadata, errors
    
    def unregister_skill(self, skill_name: str) -> bool:
        """注销技能"""
        if skill_name in self.skills:
            self.loader.unload_skill(skill_name)
            del self.skills[skill_name]
            self.logger.info(f"注销技能: {skill_name}")
            return True
        return False
    
    def get_skill(self, skill_name: str) -> Optional[SkillMetadata]:
        """获取技能元数据"""
        return self.skills.get(skill_name)
    
    def list_skills(self, status: Optional[SkillStatus] = None) -> List[SkillMetadata]:
        """列出所有技能"""
        if status:
            return [s for s in self.skills.values() if s.status == status]
        return list(self.skills.values())
    
    def execute_skill(self, skill_name: str, context: Dict[str, Any] = None) -> SkillResult:
        """执行技能"""
        start_time = time.perf_counter()
        
        metadata = self.get_skill(skill_name)
        if not metadata:
            return SkillResult(
                skill_name=skill_name,
                success=False,
                error="技能未注册",
                execution_time=time.perf_counter() - start_time
            )
        
        # 获取技能函数
        run_func = self.loader.get_skill_function(skill_name, "run")
        if not run_func:
            return SkillResult(
                skill_name=skill_name,
                success=False,
                error="技能没有run函数",
                metadata=metadata,
                execution_time=time.perf_counter() - start_time
            )
        
        try:
            # 执行技能
            result = run_func(context or {})
            return SkillResult(
                skill_name=skill_name,
                success=True,
                output=result,
                metadata=metadata,
                execution_time=time.perf_counter() - start_time
            )
        except Exception as e:
            return SkillResult(
                skill_name=skill_name,
                success=False,
                error=str(e),
                metadata=metadata,
                execution_time=time.perf_counter() - start_time
            )
    
    def scan_skills(self) -> List[str]:
        """扫描技能目录，发现所有可用技能"""
        discovered = []
        
        if not os.path.exists(self.skills_dir):
            return discovered
        
        for item in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, item)
            if os.path.isdir(skill_path):
                is_valid, _ = self.validator.validate_skill_path(skill_path)
                if is_valid:
                    discovered.append(item)
        
        return discovered

# ============================================================================
# 第三部分：演示与测试
# ============================================================================

def create_test_skill(skill_dir: str, skill_name: str) -> str:
    """创建测试用技能目录"""
    skill_path = os.path.join(skill_dir, skill_name)
    os.makedirs(skill_path, exist_ok=True)
    
    # 创建__init__.py
    init_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{skill_name} 技能模块
版本: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Test Author"
'''
    with open(os.path.join(skill_path, "__init__.py"), 'w', encoding='utf-8') as f:
        f.write(init_content)
    
    # 创建main.py
    main_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{skill_name} 技能主入口
"""

import time

def run(context: dict) -> dict:
    """
    执行技能
    
    Args:
        context: 执行上下文，包含输入参数
        
    Returns:
        执行结果字典
    """
    # 获取输入参数
    input_data = context.get("input", "默认输入")
    
    # 执行技能逻辑
    result = {{
        "skill": "{skill_name}",
        "input": input_data,
        "output": f"技能 {skill_name} 处理结果: {{input_data}}",
        "timestamp": time.time()
    }}
    
    return result

def validate(context: dict) -> bool:
    """验证输入参数"""
    return "input" in context or True  # 允许空输入
'''
    with open(os.path.join(skill_path, "main.py"), 'w', encoding='utf-8') as f:
        f.write(main_content)
    
    # 创建config.json
    config = {
        "name": skill_name,
        "version": "1.0.0",
        "description": f"测试技能: {skill_name}",
        "author": "Test Author",
        "type": "tool",
        "skill_type": "TOOL",
        "dependencies": [],
        "entry_point": "main.py"
    }
    with open(os.path.join(skill_path, "config.json"), 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    # 创建README.md
    readme_content = f'''# {skill_name} 技能

## 概述
这是一个测试技能，用于演示技能路径处理功能。

## 使用方法
```python
from skill_path_demo import SkillRegistry

registry = SkillRegistry("/path/to/skills")
registry.register_skill("/path/to/skills/{skill_name}")
result = registry.execute_skill("{skill_name}", {{"input": "测试输入"}})
print(result)
```

## 配置
编辑 `config.json` 修改技能配置。
'''
    with open(os.path.join(skill_path, "README.md"), 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    return skill_path

class SkillPathTestSuite:
    """技能路径测试套件"""
    
    def __init__(self):
        self.test_dir = None
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        self.tests.append(("test_skill_validation", self.test_skill_validation))
        self.tests.append(("test_skill_loading", self.test_skill_loading))
        self.tests.append(("test_skill_registry", self.test_skill_registry))
        self.tests.append(("test_skill_execution", self.test_skill_execution))
        self.tests.append(("test_skill_scan", self.test_skill_scan))
    
    def setup(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp(prefix="skill_test_")
        skills_dir = os.path.join(self.test_dir, "skills")
        os.makedirs(skills_dir, exist_ok=True)
        return skills_dir
    
    def teardown(self):
        """清理测试环境"""
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_skill_validation(self) -> Tuple[bool, str]:
        skills_dir = self.setup()
        try:
            validator = SkillPathValidator(skills_dir)
            
            # 创建有效的技能目录
            valid_skill = create_test_skill(skills_dir, "valid_skill")
            is_valid, errors = validator.validate_skill_path(valid_skill)
            if not is_valid:
                return False, f"有效技能验证失败: {errors}"
            
            # 测试技能名称验证
            if not validator.validate_skill_name("my-skill_123"):
                return False, "合法技能名称验证失败"
            
            if validator.validate_skill_name("../invalid"):
                return False, "非法技能名称应被拒绝"
            
            return True, "技能验证测试通过"
        finally:
            self.teardown()
    
    def test_skill_loading(self) -> Tuple[bool, str]:
        skills_dir = self.setup()
        try:
            # 创建测试技能
            create_test_skill(skills_dir, "test_skill")
            
            loader = SkillLoader(skills_dir)
            success, module, errors = loader.load_skill("test_skill")
            
            if not success:
                return False, f"技能加载失败: {errors}"
            
            if module is None:
                return False, "加载的模块为None"
            
            # 检查模块是否有run函数
            run_func = loader.get_skill_function("test_skill", "run")
            if not run_func:
                return False, "技能没有run函数"
            
            return True, "技能加载测试通过"
        finally:
            self.teardown()
    
    def test_skill_registry(self) -> Tuple[bool, str]:
        skills_dir = self.setup()
        try:
            create_test_skill(skills_dir, "registry_test")
            
            registry = SkillRegistry(skills_dir)
            success, metadata, errors = registry.register_skill(
                os.path.join(skills_dir, "registry_test")
            )
            
            if not success:
                return False, f"技能注册失败: {errors}"
            
            if metadata is None:
                return False, "注册返回的metadata为None"
            
            # 检查技能是否在注册表中
            skill = registry.get_skill("registry_test")
            if not skill:
                return False, "技能未在注册表中找到"
            
            return True, "技能注册测试通过"
        finally:
            self.teardown()
    
    def test_skill_execution(self) -> Tuple[bool, str]:
        skills_dir = self.setup()
        try:
            create_test_skill(skills_dir, "exec_test")
            
            registry = SkillRegistry(skills_dir)
            registry.register_skill(os.path.join(skills_dir, "exec_test"))
            
            result = registry.execute_skill("exec_test", {"input": "测试输入"})
            
            if not result.success:
                return False, f"技能执行失败: {result.error}"
            
            if result.output is None:
                return False, "技能执行输出为空"
            
            return True, "技能执行测试通过"
        finally:
            self.teardown()
    
    def test_skill_scan(self) -> Tuple[bool, str]:
        skills_dir = self.setup()
        try:
            # 创建多个技能
            create_test_skill(skills_dir, "skill_a")
            create_test_skill(skills_dir, "skill_b")
            create_test_skill(skills_dir, "skill_c")
            
            registry = SkillRegistry(skills_dir)
            discovered = registry.scan_skills()
            
            if len(discovered) != 3:
                return False, f"扫描发现技能数量错误: {len(discovered)}"
            
            expected = {"skill_a", "skill_b", "skill_c"}
            if set(discovered) != expected:
                return False, f"发现的技能不匹配: {discovered}"
            
            return True, "技能扫描测试通过"
        finally:
            self.teardown()
    
    def run_all_tests(self) -> Dict[str, Any]:
        print("🚀 开始运行技能路径测试套件...")
        print("=" * 60)
        
        passed = 0
        failed = 0
        results = {}
        
        for test_name, test_func in self.tests:
            print(f"📋 运行测试: {test_name}...")
            try:
                success, message = test_func()
                if success:
                    print(f"   ✅ 通过: {message}")
                    passed += 1
                    results[test_name] = {"passed": True, "message": message}
                else:
                    print(f"   ❌ 失败: {message}")
                    failed += 1
                    results[test_name] = {"passed": False, "message": message}
            except Exception as e:
                print(f"   💥 异常: {e}")
                failed += 1
                results[test_name] = {"passed": False, "error": str(e)}
        
        print("=" * 60)
        print(f"📊 测试摘要: 总数={len(self.tests)}, 通过={passed}, 失败={failed}")
        
        return {
            "summary": {
                "total": len(self.tests),
                "passed": passed,
                "failed": failed,
                "success_rate": passed / len(self.tests) if self.tests else 0.0
            },
            "details": results
        }

def main_demo() -> None:
    """主演示函数"""
    print("=" * 80)
    print("🎓 Day 9 Lesson 35: 技能路径处理演示")
    print("=" * 80)
    
    # 创建临时技能目录
    temp_dir = tempfile.mkdtemp(prefix="skill_demo_")
    skills_dir = os.path.join(temp_dir, "skills")
    os.makedirs(skills_dir, exist_ok=True)
    
    try:
        print("\n1. 创建测试技能...")
        weather_skill = create_test_skill(skills_dir, "weather")
        calculator_skill = create_test_skill(skills_dir, "calculator")
        print(f"   ✅ 创建技能: weather")
        print(f"   ✅ 创建技能: calculator")
        
        print("\n2. 技能目录结构验证...")
        validator = SkillPathValidator(skills_dir)
        is_valid, errors = validator.validate_skill_path(weather_skill)
        print(f"   weather技能验证: {'✅通过' if is_valid else '❌失败'}")
        if errors:
            for error in errors:
                print(f"      ⚠️ {error}")
        
        print("\n   标准技能目录结构:")
        structure = validator.get_skill_structure()
        print(f"   必需文件: {structure['required']}")
        print(f"   推荐文件: {structure['recommended']}")
        
        print("\n3. 技能扫描与发现...")
        registry = SkillRegistry(skills_dir)
        discovered = registry.scan_skills()
        print(f"   发现 {len(discovered)} 个技能: {discovered}")
        
        print("\n4. 技能注册与加载...")
        for skill_name in discovered:
            skill_path = os.path.join(skills_dir, skill_name)
            success, metadata, errors = registry.register_skill(skill_path)
            if success:
                print(f"   ✅ {skill_name}: {metadata.status.value}")
                print(f"      版本: {metadata.version}, 描述: {metadata.description}")
            else:
                print(f"   ❌ {skill_name}: {errors}")
        
        print("\n5. 技能执行演示...")
        # 执行天气技能
        result1 = registry.execute_skill("weather", {"input": "北京天气"})
        print(f"   执行 weather:")
        print(f"      成功: {result1.success}")
        print(f"      输出: {result1.output}")
        print(f"      耗时: {result1.execution_time:.6f}s")
        
        # 执行计算器技能
        result2 = registry.execute_skill("calculator", {"input": "1+1"})
        print(f"   执行 calculator:")
        print(f"      成功: {result2.success}")
        print(f"      输出: {result2.output}")
        print(f"      耗时: {result2.execution_time:.6f}s")
        
        print("\n6. 技能列表查看...")
        all_skills = registry.list_skills()
        for skill in all_skills:
            print(f"   {skill.name}: {skill.status.value} (v{skill.version})")
        
        print("\n7. 运行测试套件...")
        test_suite = SkillPathTestSuite()
        report = test_suite.run_all_tests()
        
        print(f"\n📊 测试报告: 成功率={report['summary']['success_rate']:.1%}")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
        print(f"\n8. 清理完成")
    
    print("\n" + "=" * 80)
    print("🎉 技能路径处理演示完成！")
    print("=" * 80)

def run_tests() -> None:
    """运行测试套件"""
    test_suite = SkillPathTestSuite()
    report = test_suite.run_all_tests()
    
    if report["summary"]["success_rate"] >= 1.0:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 有测试失败，请检查实现。")

def main() -> None:
    parser = argparse.ArgumentParser(description="技能路径处理演示程序")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行完整演示")
    
    args = parser.parse_args()
    
    if args.test:
        run_tests()
    elif args.demo:
        main_demo()
    else:
        print("技能路径处理演示程序")
        print("使用 --help 查看选项")
        print("\n示例:")
        print("  python skill_path_demo.py --demo  # 运行完整演示")
        print("  python skill_path_demo.py --test  # 运行测试套件")

if __name__ == "__main__":
    main()
