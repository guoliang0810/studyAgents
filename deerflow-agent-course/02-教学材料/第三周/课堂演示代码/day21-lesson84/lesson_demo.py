#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
边界测试 - 演示代码

本模块展示边界测试策略。
包含：边界值分析、等价类划分、异常处理测试。

作者: DeerFlow架构师训练营
"""

import pytest
from typing import Any, List, Optional


# ============================================================================
# 第一部分：边界值分析
# ============================================================================

def process_input(text: str, max_length: int = 100) -> str:
    """处理输入文本"""
    if not text:
        raise ValueError("输入不能为空")
    if len(text) > max_length:
        raise ValueError(f"输入长度不能超过{max_length}")
    return text.strip()


class TestBoundaryValues:
    """边界值测试"""
    
    def test_empty_input(self):
        """测试空输入"""
        with pytest.raises(ValueError, match="不能为空"):
            process_input("")
    
    def test_max_length(self):
        """测试最大长度"""
        text = "a" * 100
        result = process_input(text, max_length=100)
        assert len(result) == 100
    
    def test_over_max_length(self):
        """测试超过最大长度"""
        text = "a" * 101
        with pytest.raises(ValueError, match="不能超过"):
            process_input(text, max_length=100)
    
    def test_whitespace_only(self):
        """测试仅空白字符"""
        result = process_input("   ")
        assert result == ""


# ============================================================================
# 第二部分：等价类划分
# ============================================================================

class TestEquivalenceClasses:
    """等价类测试"""
    
    def test_valid_integer(self):
        """测试有效整数"""
        def validate_age(age: int) -> bool:
            return 0 <= age <= 150
        
        assert validate_age(25) is True
        assert validate_age(0) is True
        assert validate_age(150) is True
    
    def test_invalid_integer(self):
        """测试无效整数"""
        def validate_age(age: int) -> bool:
            return 0 <= age <= 150
        
        assert validate_age(-1) is False
        assert validate_age(151) is False


# ============================================================================
# 第三部分：异常处理测试
# ============================================================================

def safe_divide(a: float, b: float) -> float:
    """安全除法"""
    if b == 0:
        raise ZeroDivisionError("除数不能为零")
    return a / b


class TestExceptionHandling:
    """异常处理测试"""
    
    def test_normal_division(self):
        """测试正常除法"""
        assert safe_divide(10, 2) == 5.0
    
    def test_division_by_zero(self):
        """测试除零异常"""
        with pytest.raises(ZeroDivisionError):
            safe_divide(10, 0)
    
    def test_exception_message(self):
        """测试异常消息"""
        with pytest.raises(ZeroDivisionError, match="不能为零"):
            safe_divide(10, 0)
    
    def test_exception_type(self):
        """测试异常类型"""
        with pytest.raises(ZeroDivisionError):
            safe_divide("10", 0)


# ============================================================================
# 第四部分：Agent边界测试
# ============================================================================

class AgentConfig:
    """Agent配置"""
    
    def __init__(
        self,
        name: str,
        max_retries: int = 3,
        timeout: int = 30
    ):
        if not name or not name.strip():
            raise ValueError("名称不能为空")
        if max_retries < 0:
            raise ValueError("重试次数不能为负")
        if timeout <= 0:
            raise ValueError("超时时间必须为正")
        
        self.name = name
        self.max_retries = max_retries
        self.timeout = timeout


class TestAgentBoundary:
    """Agent边界测试"""
    
    def test_empty_name(self):
        """测试空名称"""
        with pytest.raises(ValueError, match="不能为空"):
            AgentConfig("")
    
    def test_whitespace_name(self):
        """测试空白名称"""
        with pytest.raises(ValueError, match="不能为空"):
            AgentConfig("   ")
    
    def test_negative_retries(self):
        """测试负重试次数"""
        with pytest.raises(ValueError, match="不能为负"):
            AgentConfig("test", max_retries=-1)
    
    def test_zero_timeout(self):
        """测试零超时"""
        with pytest.raises(ValueError, match="必须为正"):
            AgentConfig("test", timeout=0)
    
    def test_valid_config(self):
        """测试有效配置"""
        config = AgentConfig("test_agent", max_retries=5, timeout=60)
        assert config.name == "test_agent"
        assert config.max_retries == 5
        assert config.timeout == 60


# ============================================================================
# 第五部分：性能边界测试
# ============================================================================

import time

def timed_operation(data: List) -> int:
    """计时操作"""
    if len(data) > 10000:
        raise ValueError("数据量过大")
    return len(data)


class TestPerformanceBoundary:
    """性能边界测试"""
    
    def test_normal_size(self):
        """测试正常大小"""
        data = list(range(100))
        assert timed_operation(data) == 100
    
    def test_max_size(self):
        """测试最大大小"""
        data = list(range(10000))
        assert timed_operation(data) == 10000
    
    def test_over_max_size(self):
        """测试超过最大大小"""
        data = list(range(10001))
        with pytest.raises(ValueError, match="过大"):
            timed_operation(data)


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
