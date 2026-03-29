#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock策略 - 演示代码

本模块展示测试中的Mock策略。
包含：单元Mock、集成Mock、异步Mock。

作者: DeerFlow架构师训练营
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Any, Dict
import asyncio


# ============================================================================
# 第一部分：基础Mock
# ============================================================================

class TestBasicMock:
    """基础Mock测试"""
    
    def test_mock_function(self):
        """测试Mock函数"""
        mock = Mock(return_value="测试结果")
        result = mock("参数")
        
        assert result == "测试结果"
        mock.assert_called_once_with("参数")
    
    def test_mock_attribute(self):
        """测试Mock属性"""
        mock = Mock()
        mock.name = "测试名称"
        mock.value = 123
        
        assert mock.name == "测试名称"
        assert mock.value == 123


# ============================================================================
# 第二部分：Patch使用
# ============================================================================

class TestPatching:
    """Patch测试"""
    
    def test_patch_function(self):
        """测试函数Patch"""
        with patch('os.path.exists', return_value=True):
            from os.path import exists
            assert exists("/fake/path") is True
    
    def test_patch_class(self):
        """测试类Patch"""
        with patch('lesson_demo.LLMAgent') as MockAgent:
            mock_instance = MockAgent.return_value
            mock_instance.generate.return_value = "Mock响应"
            
            agent = LLMAgent("gpt-4")
            response = agent.generate("你好")
            
            assert response == "Mock响应"


# ============================================================================
# 第三部分：异步Mock
# ============================================================================

class TestAsyncMock:
    """异步Mock测试"""
    
    async def test_async_mock(self):
        """测试异步Mock"""
        async def async_func():
            await asyncio.sleep(0.1)
            return "异步结果"
        
        mock = AsyncMock(return_value="Mock异步结果")
        result = await mock()
        
        assert result == "Mock异步结果"
    
    async def test_async_context_manager(self):
        """测试异步上下文管理器"""
        mock = AsyncMock()
        mock.__aenter__ = AsyncMock(return_value="entered")
        mock.__aexit__ = AsyncMock(return_value=None)
        
        async with mock as value:
            assert value == "entered"


# ============================================================================
# 第四部分：Mock LLM调用
# ============================================================================

class LLMAgent:
    """LLM Agent模拟类"""
    
    def __init__(self, model: str):
        self.model = model
    
    def generate(self, prompt: str) -> str:
        """生成响应"""
        return f"响应: {prompt}"


@pytest.fixture
def mock_llm_response():
    """Mock LLM响应"""
    return {
        "content": "这是Mock的响应",
        "usage": {"total_tokens": 50},
        "model": "gpt-4"
    }


class TestLLMMocking:
    """LLM Mock测试"""
    
    def test_generate_with_mock(self, mock_llm_response):
        """测试LLM生成（使用Mock）"""
        with patch.object(LLMAgent, 'generate', return_value=mock_llm_response["content"]):
            agent = LLMAgent("gpt-4")
            result = agent.generate("测试提示")
            
            assert result == "这是Mock的响应"
    
    def test_generate_with_side_effect(self):
        """测试Mock的side_effect"""
        def side_effect(prompt):
            if "你好" in prompt:
                return "你好！"
            elif "天气" in prompt:
                return "今天晴天。"
            return "默认响应"
        
        with patch.object(LLMAgent, 'generate', side_effect=side_effect):
            agent = LLMAgent("gpt-4")
            
            assert agent.generate("你好") == "你好！"
            assert agent.generate("天气如何") == "今天晴天。"
            assert agent.generate("其他") == "默认响应"


# ============================================================================
# 第五部分：Spy使用
# ============================================================================

class TestSpy:
    """Spy测试"""
    
    def test_spy_on_method(self):
        """测试方法监控"""
        original = LLMAgent.generate
        
        with patch.object(LLMAgent, 'generate', wraps=original):
            agent = LLMAgent("gpt-4")
            agent.generate("测试")
            
            agent.generate.assert_called_once()


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
