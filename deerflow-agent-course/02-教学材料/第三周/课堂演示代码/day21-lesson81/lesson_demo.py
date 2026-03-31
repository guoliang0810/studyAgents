#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试架构设计 - 演示代码

本模块展示DeerFlow测试架构设计和测试策略。
包含：测试金字塔、测试配置、环境管理。

本代码演示如何为AI Agent系统设计完整的测试架构，
包括测试分层策略、pytest配置、测试环境管理等核心内容。

作者: DeerFlow架构师训练营
"""

import pytest
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import yaml
import json


# ============================================================================
# 第一部分：测试金字塔模型
# ============================================================================

class TestType(Enum):
    """测试类型枚举
    
    定义AI Agent系统中常见的三种测试类型
    """
    UNIT = "unit"                    # 单元测试：测试最小可单元功能
    INTEGRATION = "integration"        # 集成测试：测试组件交互
    E2E = "e2e"                     # 端到端测试：测试完整流程


@dataclass
class TestLevel:
    """测试层级数据类
    
    存储每个测试层级的配置信息
    """
    test_type: TestType
    percentage: float                 # 测试占比
    description: str                 # 描述
    examples: List[str]              # 示例
    avg_execution_time: float        # 平均执行时间（秒）
    
    @property
    def test_count_estimate(self, total_tests: int = 100) -> int:
        """估算给定总测试数时该层级的测试数量"""
        return int(total_tests * self.percentage / 100)


class TestingPyramid:
    """测试金字塔模型
    
    测试金字塔是软件测试的基础架构原则，它定义了不同层级测试的
    比例关系。底层单元测试最多，顶层端到端测试最少。
    
    设计原理：
    - 单元测试：快速执行发现问题，修复成本低
    - 集成测试：验证组件交互，发现接口问题
    - E2E测试：验证完整流程，发现端到端问题
    """
    
    LEVELS = [
        TestLevel(
            test_type=TestType.UNIT,
            percentage=70.0,
            description="单元测试：测试最小可单元功能，如单个函数、工具类、状态管理等",
            examples=[
                "测试LangGraph节点的reduce函数",
                "测试中间件的process方法",
                "测试工具类的参数验证",
                "测试状态序列化/反序列化"
            ],
            avg_execution_time=0.1
        ),
        TestLevel(
            test_type=TestType.INTEGRATION,
            percentage=20.0,
            description="集成测试：测试组件交互，如Agent与工具集成、状态流、配置加载等",
            examples=[
                "测试Agent与工具的调用链",
                "测试多节点状态流转",
                "测试配置加载和合并",
                "测试沙箱与工具集成"
            ],
            avg_execution_time=1.0
        ),
        TestLevel(
            test_type=TestType.E2E,
            percentage=10.0,
            description="端到端测试：测试完整流程，如用户完整交互、多Agent协作等",
            examples=[
                "测试用户完整对话流程",
                "测试多Agent任务协作",
                "测试生产环境部署",
                "测试高并发场景"
            ],
            avg_execution_time=10.0
        )
    ]
    
    @classmethod
    def get_levels(cls) -> List[TestLevel]:
        """获取所有测试层级"""
        return cls.LEVELS
    
    @classmethod
    def get_level(cls, test_type: TestType) -> Optional[TestLevel]:
        """获取指定测试类型的信息"""
        for level in cls.LEVELS:
            if level.test_type == test_type:
                return level
        return None
    
    @classmethod
    def get_recommendation(cls, total_tests: int = 100) -> Dict[TestType, int]:
        """获取测试数量建议
        
        Args:
            total_tests: 总测试数量目标
            
        Returns:
            每种测试类型的建议数量字典
        """
        return {
            level.test_type: level.test_count_estimate(total_tests)
            for level in cls.LEVELS
        }
    
    @classmethod
    def estimate_execution_time(cls, test_counts: Dict[TestType, int]) -> float:
        """估算总执行时间
        
        Args:
            test_counts: 各类型测试数量
            
        Returns:
            预估总执行时间（秒）
        """
        total_time = 0.0
        for level in cls.LEVELS:
            count = test_counts.get(level.test_type, 0)
            total_time += count * level.avg_execution_time
        return total_time
    
    @classmethod
    def generate_report(cls, total_tests: int = 100) -> str:
        """生成测试金字塔报告
        
        Args:
            total_tests: 总测试数量目标
            
        Returns:
            格式化的报告字符串
        """
        recommendations = cls.get_recommendation(total_tests)
        execution_time = cls.estimate_execution_time(recommendations)
        
        lines = [
            "=" * 60,
            "测试金字塔分析报告",
            "=" * 60,
            f"目标总测试数: {total_tests}",
            f"预估执行时间: {execution_time:.1f}秒 ({execution_time/60:.1f}分钟)",
            "",
            "测试分布:",
            "-" * 40
        ]
        
        for level in cls.LEVELS:
            count = recommendations[level.test_type]
            percentage = level.percentage
            lines.append(
                f"{level.test_type.value.upper():12} | "
                f"{count:4}个 ({percentage:5.1f}%) | "
                f"平均{level.avg_execution_time:.1f}秒/个"
            )
        
        lines.append("=" * 60)
        return "\n".join(lines)


# ============================================================================
# 第二部分：DeerFlow测试配置
# ============================================================================

@dataclass
class DeerFlowTestConfig:
    """DeerFlow测试配置数据类"""
    test_type: TestType
    config: Dict[str, Any]
    required_services: List[str] = field(default_factory=list)
    optional_services: List[str] = field(default_factory=list)


class TestConfigManager:
    """测试配置管理器
    
    管理DeerFlow的各种测试配置，包括：
    - pytest配置
    - fixtures定义
    - 服务依赖
    - 覆盖率设置
    """
    
    UNIT_TEST_CONFIG = {
        "pytest": {
            "testpaths": ["tests/unit"],
            "python_files": "test_*.py",
            "python_classes": "Test*",
            "python_functions": "test_*",
            "addopts": "-v --tb=short --strict-markers",
            "markers": [
                "unit: 单元测试",
                "slow: 慢速测试"
            ]
        },
        "coverage": {
            "source": ["deerflow"],
            "omit": [
                "*/tests/*",
                "*/migrations/*",
                "*/__pycache__/*"
            ],
            "min_coverage": 80
        },
        "fixtures": [
            "sample_agent_config",
            "sample_state",
            "mock_llm"
        ]
    }
    
    INTEGRATION_TEST_CONFIG = {
        "pytest": {
            "testpaths": ["tests/integration"],
            "python_files": "test_*.py",
            "addopts": "-v --tb=short --integration --strict-markers",
            "markers": [
                "integration: 集成测试",
                "requires_service: 需要外部服务"
            ]
        },
        "services": {
            "required": ["redis", "postgres"],
            "optional": ["elasticsearch", "mock_llm_api"]
        },
        "fixtures": [
            "test_db",
            "test_redis",
            "agent_instance"
        ]
    }
    
    E2E_TEST_CONFIG = {
        "pytest": {
            "testpaths": ["tests/e2e"],
            "python_files": "test_*.py",
            "addopts": "-v --tb=short --e2e --strict-markers",
            "markers": [
                "e2e: 端到端测试",
                "requires_deployment: 需要部署环境"
            ]
        },
        "environment": {
            "deerflow_url": "http://localhost:8000",
            "timeout": 300,
            "retry_attempts": 3
        },
        "fixtures": [
            "deployed_agent",
            "test_user",
            "cleanup_after"
        ]
    }
    
    @classmethod
    def get_config(cls, test_type: TestType) -> Dict:
        """获取指定类型的测试配置"""
        config_map = {
            TestType.UNIT: cls.UNIT_TEST_CONFIG,
            TestType.INTEGRATION: cls.INTEGRATION_TEST_CONFIG,
            TestType.E2E: cls.E2E_TEST_CONFIG
        }
        return config_map.get(test_type, {})
    
    @classmethod
    def generate_pytest_ini(cls, test_type: TestType) -> str:
        """生成pytest.ini配置文件内容
        
        Args:
            test_type: 测试类型
            
        Returns:
            pytest.ini格式的配置字符串
        """
        config = cls.get_config(test_type)
        pytest_config = config.get("pytest", {})
        
        lines = ["[pytest]"]
        
        # 添加testpaths
        if "testpaths" in pytest_config:
            lines.append(f"testpaths = {', '.join(pytest_config['testpaths'])}")
        
        # 添加python配置
        if "python_files" in pytest_config:
            lines.append(f"python_files = {pytest_config['python_files']}")
        if "python_classes" in pytest_config:
            lines.append(f"python_classes = {pytest_config['python_classes']}")
        if "python_functions" in pytest_config:
            lines.append(f"python_functions = {pytest_config['python_functions']}")
        
        # 添加选项
        if "addopts" in pytest_config:
            lines.append(f"addopts = {pytest_config['addopts']}")
        
        # 添加markers
        if "markers" in pytest_config:
            for marker in pytest_config["markers"]:
                lines.append(f"markers = {marker}")
        
        return "\n".join(lines)
    
    @classmethod
    def generate_conftest_template(cls, test_type: TestType) -> str:
        """生成conftest.py模板
        
        Args:
            test_type: 测试类型
            
        Returns:
            conftest.py模板代码
        """
        fixtures = cls.get_config(test_type).get("fixtures", [])
        
        lines = [
            '"""pytest fixtures配置文件"""',
            "import pytest",
            "",
            ""
        ]
        
        for fixture_name in fixtures:
            lines.append(f"@pytest.fixture")
            lines.append(f"def {fixture_name}():")
            lines.append(f'    """{fixture_name} fixture"""')
            lines.append(f"    pass")
            lines.append("")
        
        return "\n".join(lines)
    
    @classmethod
    def generate_github_actions_workflow(cls) -> str:
        """生成GitHub Actions CI工作流配置"""
        return """name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        test-type: [unit, integration, e2e]
    
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          pytest tests/${{ matrix.test-type }}/ -v --cov
      - name: Upload coverage
        uses: codecov/codecov-action@v3
"""


# ============================================================================
# 第三部分：测试环境管理
# ============================================================================

class ServiceStatus(Enum):
    """服务状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    status: ServiceStatus = ServiceStatus.STOPPED
    port: Optional[int] = None
    health_check_url: Optional[str] = None
    start_timeout: int = 30
    stop_timeout: int = 10


class TestEnvironmentManager:
    """测试环境管理器
    
    管理测试环境的启动、配置和清理，支持：
    - 异步服务启动
    - 健康检查
    - 资源限制
    - 自动清理
    """
    
    def __init__(self):
        self.services: Dict[str, ServiceInfo] = {}
        self.resources: List[str] = []
        self._lock = asyncio.Lock()
    
    async def register_service(
        self,
        name: str,
        port: Optional[int] = None,
        health_check_url: Optional[str] = None
    ) -> ServiceInfo:
        """注册服务
        
        Args:
            name: 服务名称
            port: 服务端口
            health_check_url: 健康检查URL
            
        Returns:
            服务信息对象
        """
        async with self._lock:
            service = ServiceInfo(
                name=name,
                port=port,
                health_check_url=health_check_url
            )
            self.services[name] = service
            return service
    
    async def start_service(self, service_name: str) -> bool:
        """启动服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            是否启动成功
        """
        async with self._lock:
            service = self.services.get(service_name)
            if not service:
                raise ValueError(f"服务 {service_name} 未注册")
            
            if service.status == ServiceStatus.RUNNING:
                return True
            
            service.status = ServiceStatus.STARTING
            print(f"启动服务: {service_name}...")
            
            # 模拟服务启动
            await asyncio.sleep(0.5)
            
            service.status = ServiceStatus.RUNNING
            print(f"服务 {service_name} 已启动")
            return True
    
    async def stop_service(self, service_name: str) -> bool:
        """停止服务
        
        Args:
            service_name: 服务名称
            
        Returns:
            是否停止成功
        """
        async with self._lock:
            service = self.services.get(service_name)
            if not service:
                return False
            
            if service.status == ServiceStatus.STOPPED:
                return True
            
            service.status = ServiceStatus.STOPPING
            print(f"停止服务: {service_name}...")
            
            # 模拟服务停止
            await asyncio.sleep(0.3)
            
            service.status = ServiceStatus.STOPPED
            print(f"服务 {service_name} 已停止")
            return True
    
    async def start_all_required(
        self,
        required_services: List[str]
    ) -> Dict[str, bool]:
        """启动所有必需服务
        
        Args:
            required_services: 必需的服务列表
            
        Returns:
            各服务的启动结果
        """
        results = {}
        for service_name in required_services:
            try:
                await self.start_service(service_name)
                results[service_name] = True
            except Exception as e:
                print(f"启动服务 {service_name} 失败: {e}")
                results[service_name] = False
        
        return results
    
    async def stop_all(self):
        """停止所有服务"""
        service_names = list(self.services.keys())
        for service_name in service_names:
            await self.stop_service(service_name)
    
    async def get_status(self) -> Dict[str, Any]:
        """获取环境状态"""
        return {
            "services": {
                name: {
                    "status": service.status.value,
                    "port": service.port,
                    "health_check_url": service.health_check_url
                }
                for name, service in self.services.items()
            },
            "resources": self.resources.copy(),
            "ready": all(
                s.status == ServiceStatus.RUNNING
                for s in self.services.values()
            )
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
        """生成测试计划
        
        Args:
            total_tests: 目标总测试数
            
        Returns:
            格式化的测试计划
        """
        recommendations = self.test_pyramid.get_recommendation(total_tests)
        
        lines = [
            f"# {self.project_name} 测试计划",
            f"## 目标总测试数: {total_tests}",
            "",
            "## 测试金字塔分布",
            ""
        ]
        
        for level in self.test_pyramid.get_levels():
            test_type = level.test_type
            count = recommendations[test_type]
            percentage = level.percentage
            avg_time = level.avg_execution_time
            total_time = count * avg_time
            
            lines.append(f"### {test_type.value.upper()} 测试")
            lines.append(f"- 数量: {count}个")
            lines.append(f"- 占比: {percentage}%")
            lines.append(f"- 预估时间: {total_time:.1f}秒")
            lines.append(f"- 示例: {', '.join(level.examples[:2])}")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_config_for_type(self, test_type: TestType) -> Dict:
        """获取指定类型的配置"""
        return self.config_manager.get_config(test_type)


# ============================================================================
# 测试执行
# ============================================================================

def run_demo():
    """演示函数"""
    print("=" * 70)
    print("DeerFlow测试架构设计演示")
    print("=" * 70)
    
    # 1. 测试金字塔演示
    print("\n### 1. 测试金字塔分析")
    print(TestingPyramid.generate_report(100))
    
    # 2. 测试配置演示
    print("\n### 2. pytest配置生成")
    print("单元测试配置:")
    print(TestConfigManager.generate_pytest_ini(TestType.UNIT))
    
    # 3. 测试环境管理演示
    print("\n### 3. 测试环境管理")
    
    async def test_environment():
        manager = TestEnvironmentManager()
        
        # 注册服务
        await manager.register_service("redis", port=6379)
        await manager.register_service("postgres", port=5432)
        
        # 启动服务
        await manager.start_all_required(["redis", "postgres"])
        
        # 获取状态
        status = await manager.get_status()
        print(f"环境状态: {status['ready']}")
        
        # 停止服务
        await manager.stop_all()
        
        print("环境清理完成")
    
    asyncio.run(test_environment())
    
    # 4. 测试策略演示
    print("\n### 4. 测试策略生成")
    strategy = TestStrategy("MyAgentProject")
    print(strategy.generate_test_plan(50))
    
    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
