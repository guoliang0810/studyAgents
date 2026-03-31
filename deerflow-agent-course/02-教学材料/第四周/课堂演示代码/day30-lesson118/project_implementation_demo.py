#!/usr/bin/env python3
# 第118节课：项目实现指导
from typing import Dict, Any, List

class CodeStructure:
    def __init__(self):
        self.modules: List[str] = []
        self.tests: Dict[str, int] = {}
    
    def add_module(self, name: str) -> None:
        if name not in self.modules:
            self.modules.append(name)
    
    def add_test_coverage(self, module: str, coverage: int) -> None:
        self.tests[module] = coverage
    
    def get_quality_score(self) -> float:
        if not self.tests: return 0
        return sum(self.tests.values()) / len(self.tests)

class Documentation:
    def __init__(self):
        self.docs: Dict[str, str] = {}
    
    def add_doc(self, section: str, content: str) -> None:
        self.docs[section] = content
    
    def generate_readme(self) -> str:
        return "# Project Documentation\n\n" + "\n\n".join(f"## {k}\n{v}" for k, v in self.docs.items())

def run_demo():
    print("项目实现指导演示")
    structure = CodeStructure()
    structure.add_module("core")
    structure.add_module("api")
    structure.add_test_coverage("core", 90)
    structure.add_test_coverage("api", 85)
    print(f"质量分数: {structure.get_quality_score()}")

def run_tests():
    print("测试: 代码结构")
    s = CodeStructure()
    s.add_module("test")
    s.add_test_coverage("test", 80)
    assert s.get_quality_score() == 80
    print("✓ 代码结构测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
