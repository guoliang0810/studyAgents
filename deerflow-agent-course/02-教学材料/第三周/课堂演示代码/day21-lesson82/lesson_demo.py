#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest配置与夹具 - 演示代码

本模块展示Pytest配置和夹具的使用。
包含：conftest.py、fixture、参数化测试。

作者: DeerFlow架构师训练营
"""

import pytest
from typing import Dict, Any, List


# ============================================================================
# 第一部分：Pytest配置
# ============================================================================

def pytest_configure(config):
    """Pytest配置钩子"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "e2e: 端到端测试")


# ============================================================================
# 第二部分：Fixture定义
# ============================================================================

@pytest.fixture
def sample_agent_config():
    """示例Agent配置fixture"""
    return {
        "name": "test_agent",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000
    }


@pytest.fixture
def sample_state():
    """示例状态fixture"""
    return {
        "messages": [],
        "context": {},
        "metadata": {}
    }


@pytest.fixture
def mock_llm_response():
    """模拟LLM响应fixture"""
    return {
        "content": "这是一个测试响应",
        "usage": {"total_tokens": 50},
        "model": "gpt-4"
    }


@pytest.fixture
def agent_with_config(sample_agent_config):
    """带配置的Agent fixture"""
    class MockAgent:
        def __init__(self, config):
            self.config = config
            self.name = config["name"]
        
        def run(self, input_text):
            return f"处理: {input_text}"
    
    return MockAgent(sample_agent_config)


# ============================================================================
# 第三部分：参数化测试
# ============================================================================

@pytest.mark.parametrize("input,expected", [
    ("hello", "处理: hello"),
    ("test", "处理: test"),
    ("deerflow", "处理: deerflow"),
])
def test_agent_basic(agent_with_config, input, expected):
    """测试Agent基本功能"""
    result = agent_with_config.run(input)
    assert result == expected


@pytest.mark.parametrize("temperature,expected_range", [
    (0.0, (0.0, 0.2)),
    (0.5, (0.3, 0.7)),
    (1.0, (0.8, 1.0)),
])
def test_temperature_range(temperature, expected_range):
    """测试温度参数范围"""
    assert expected_range[0] <= temperature <= expected_range[1]


# ============================================================================
# 第四部分：测试夹具示例
# ============================================================================

class TestFixtures:
    """测试夹具使用示例"""
    
    def test_agent_config(self, sample_agent_config):
        """测试配置fixture"""
        assert sample_agent_config["name"] == "test_agent"
        assert sample_agent_config["model"] == "gpt-4"
    
    def test_state_initialization(self, sample_state):
        """测试状态初始化"""
        assert sample_state["messages"] == []
        assert sample_state["context"] == {}
    
    def test_agent_with_mock(self, agent_with_config, mock_llm_response):
        """测试Agent与mock响应"""
        result = agent_with_config.run("test")
        assert "处理" in result
        assert mock_llm_response["content"]


# ============================================================================
# 第五部分：会话级别fixture
# ============================================================================

@pytest.fixture(scope="session")
def test_session_config():
    """会话级别配置"""
    return {
        "session_id": "test_session_001",
        "timeout": 300
    }


@pytest.fixture(scope="module")
def test_module_state():
    """模块级别状态"""
    state = {"counter": 0}
    yield state
    state.clear()


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
