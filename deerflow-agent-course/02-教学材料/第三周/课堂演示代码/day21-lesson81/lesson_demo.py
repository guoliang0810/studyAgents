#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试架构设计 - 演示代码

本模块展示DeerFlow测试架构设计和测试策略。
包含：测试金字塔、测试配置、环境管理。

作者: DeerFlow架构师训练营
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# 第一部分：测试金字塔
# ============================================================================

class TestType(Enum):
    """测试类型"""
    UNIT = "unit"           # 单元测试
    INTEGRATION = "integration"  # 集成测试
    E2E = "e2e"            # 端到端测试


@dataclass
class TestLevel:
    """测试层级"""
    test_type: TestType
    percentage: float  # 测试占比
    description: str
    examples: List[str]


class TestingPyramid:
    """测试金字塔模型
    
    定义不同层级测试的比例和关系
    """
    
    # 标准测试金字塔比例
    LEVELS = [
        TestLevel(
            test_type=TestType.UNIT,
            percentage=70.0,
            description="单元测试：测试最小可单元功能",
            examples=[
                "测试单个函数的输入输出",
                "测试工具类的正确性",
                "测试状态管理的边界"
            ]
        ),
        TestLevel(
            test_type=TestType.INTEGRATION,
            percentage=20.0,
            description="集成测试：测试组件交互",
            examples=[
                "测试Agent与工具的集成",
                "测试状态序列化",
                "测试配置加载"
            ]
        ),
        TestLevel(
            test_type=TestType.E2E,
            percentage=10.0,
            description="端到端测试：测试完整流程",
            examples=[
                "测试用户完整交互流程",
                "测试多Agent协作",
                "测试生产环境部署"
            ]
        )
    ]
    
    @classmethod
    def get_levels(cls) -> List[TestLevel]:
        """获取测试层级"""
        return cls.LEVELS
    
    @classmethod
    def get_recommendation(cls, total_tests: int) -> Dict[TestType, int]:
        """获取测试数量建议
        
        Args:
            total_tests: 总测试数量
            
        Returns:
            每种测试类型的建议数量
        """
        recommendations = {}
        for level in cls.LEVELS:
            recommendations[level.test_type] = int(
                total_tests * level.percentage / 100
            )
        return recommendations


# ============================================================================
# 第二部分：DeerFlow测试配置
# ============================================================================

@dataclass
class DeerFlowTestConfig:
    """DeerFlow测试配置"""
    test_type: TestType
    config: Dict[str, Any]


class TestConfigManager:
    """测试配置管理器
    
    管理DeerFlow各种测试配置
    """
    
    UNIT_TEST_CONFIG = {
        "pytest": {
            "testpaths": ["tests/unit"],
            "python_files": "test_*.py",
            "python_classes": "Test*",
            "python_functions": "test_*",
            "addopts": "-v --tb=short"
        },
        "coverage": {
            "source": ["deerflow"],
            "omit": ["*/tests/*", "*/migrations/*"]
        }
    }
    
    INTEGRATION_TEST_CONFIG = {
        "pytest": {
            "testpaths": ["tests/integration"],
            "python_files": "test_*.py",
            "addopts": "-v --tb=short --integration"
        },
        "services": {
            "required": ["redis", "postgres"],
            "optional": ["elasticsearch"]
        }
    }
    
    E2E_TEST_CONFIG = {
        "pytest": {
            "testpaths": ["tests/e2e"],
            "python_files": "test_*.py",
            "addopts": "-v --tb=short --e2e"
        },
        "environment": {
            "deerflow_url": "http://localhost:8000",
            "timeout": 300
        }
    }
    
    @classmethod
    def get_config(cls, test_type: TestType) -> Dict:
        """获取测试配置"""
        if test_type == TestType.UNIT:
            return cls.UNIT_TEST_CONFIG
        elif test_type == TestType.INTEGRATION:
            return cls.INTEGRATION_TEST_CONFIG
        elif test_type == TestType.E2E:
            return cls.E2E_TEST_CONFIG
        return {}
    
    @classmethod
    def generate_pytest_ini(cls, test_type: TestType) -> str:
        """生成pytest.ini配置"""
        config = cls.get_config(test_type)
        pytest_config = config.get("pytest", {})
        
        lines = ["[pytest]"]
        for key, value in pytest_config.items():
            if key == "addopts":
                lines.append(f"addopts = {value}")
            elif isinstance(value, list):
                lines.append(f"{key} = {','.join(value)}")
            elif key == "testpaths":
                lines.append(f"{key} = {value[0]}")
        
        return "\n".join(lines)


# ============================================================================
# 第三部分：测试环境管理
# ============================================================================

class TestEnvironmentManager:
    """测试环境管理器
    
    管理测试环境的启动、配置和清理
    """
    
    def __init__(self):
        self.services: Dict[str, bool] = {}
        self.resources: List[str] = []
    
    def start_service(self, service_name: str) -> bool:
        """启动服务"""
        print(f"启动服务: {service_name}")
        self.services[service_name] = True
        return True
    
    def stop_service(self, service_name: str) -> bool:
        """停止服务"""
        print(f"停止服务: {service_name}")
        self.services[service_name] = False
        return True
    
    def is_service_ready(self, service_name: str) -> bool:
        """检查服务是否就绪"""
        return self.services.get(service_name, False)
    
    def setup_environment(self, config: Dict[str, Any]) -> bool:
        """设置测试环境"""
        print("设置测试环境...")
        
        # 启动所需服务
        for service in config.get("required_services", []):
            self.start_service(service)
        
        # 分配资源
        self.resources = config.get("resources", [])
        
        return True
    
    def teardown_environment(self):
        """清理测试环境"""
        print("清理测试环境...")
        
        # 停止所有服务
        for service in self.services:
            self.stop_service(service)
        
        # 释放资源
        self.resources.clear()
    
    def get_status(self) -> Dict[str, Any]:
        """获取环境状态"""
        return {
            "services": self.services.copy(),
            "resources": self.resources.copy(),
            "ready": all(self.services.values())
        }


# ============================================================================
# 第四部分：测试策略
# ============================================================================

class TestStrategy:
    """测试策略
    
    定义项目的测试策略和执行计划
    """
    
    def __init__(self, project_name: str):
        self.project_name = project_name
        self.test_pyramid = TestingPyramid()
        self.config_manager = TestConfigManager()
    
    def generate_test_plan(self, total_tests: int = 100) -> str:
        """生成测试计划"""
        recommendations = self.test_pyramid.get_recommendation(total_tests)
        
        lines = [
            f"# {self.project_name} 测试计划",
            f"# 总测试数: {total_tests}",
            "",
            "## 测试金字塔分布"
        ]
        
        for test_type, count in recommendations.items():
            percentage = count / total_tests * 100
            lines.append(f"- {test_type.value}: {count} ({percentage:.1f}%)")
        
        return "\n".join(lines)
    
    def get_config_for_type(self, test_type: TestType) -> Dict:
        """获取指定类型的配置"""
        return self.config_manager.get_config(test_type)


# ============================================================================
# 测试代码
# ============================================================================

def test_pyramid():
    """测试金字塔"""
    print("=== 测试金字塔 ===\n")
    
    pyramid = TestingPyramid()
    for level in pyramid.get_levels():
        print(f"{level.test_type.value}: {level.percentage}%")
        print(f"  说明: {level.description}")
        print()
    
    recommendations = pyramid.get_recommendation(100)
    print("100个测试的建议分布:")
    for test_type, count in recommendations.items():
        print(f"  {test_type.value}: {count}")


def test_config():
    """测试配置"""
    print("\n=== 测试配置 ===\n")
    
    manager = TestConfigManager()
    
    print("单元测试配置:")
    config = manager.get_config(TestType.UNIT)
    print(f"  pytest: {config.get('pytest', {})}")
    
    print("\n生成pytest.ini:")
    ini = manager.generate_pytest_ini(TestType.UNIT)
    print(ini)


def test_environment():
    """测试环境管理"""
    print("\n=== 测试环境管理 ===\n")
    
    manager = TestEnvironmentManager()
    
    config = {
        "required_services": ["redis", "postgres"],
        "resources": ["memory:4g", "cpu:2"]
    }
    
    manager.setup_environment(config)
    print(f"环境状态: {manager.get_status()}")
    
    manager.teardown_environment()
    print(f"清理后状态: {manager.get_status()}")


def test_strategy():
    """测试策略"""
    print("\n=== 测试策略 ===\n")
    
    strategy = TestStrategy("MyAgentProject")
    plan = strategy.generate_test_plan(100)
    print(plan)


if __name__ == "__main__":
    test_pyramid()
    test_config()
    test_environment()
    test_strategy()
