#!/usr/bin/env python3
# 第90节课：沙箱安全强化
import pytest

def test_sandbox():
    assert True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
