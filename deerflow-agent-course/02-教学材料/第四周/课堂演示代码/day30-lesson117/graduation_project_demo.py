#!/usr/bin/env python3
# 第117节课：毕业项目设计
from typing import Dict, Any, List

class Project:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.milestones: List[Dict] = []
        self.tasks: List[Dict] = []
    
    def add_milestone(self, name: str, due_date: str):
        self.milestones.append({"name": name, "due_date": due_date, "completed": False})
    
    def add_task(self, title: str, assignee: str, effort_hours: int):
        self.tasks.append({"title": title, "assignee": assignee, "effort_hours": effort_hours, "status": "pending"})
    
    def get_plan(self) -> Dict:
        return {"name": self.name, "milestones": self.milestones, "tasks": self.tasks, "total_hours": sum(t["effort_hours"] for t in self.tasks)}

class ArchitectureDesign:
    def __init__(self):
        self.components: List[Dict] = []
    
    def add_component(self, name: str, responsibility: str):
        self.components.append({"name": name, "responsibility": responsibility})
    
    def to_dict(self) -> Dict:
        return {"components": self.components}

def run_demo():
    print("毕业项目设计演示")
    proj = Project("DeerFlow企业助手", "企业级AI助手系统")
    proj.add_milestone("需求分析", "Week 1")
    proj.add_task("设计数据库", "张三", 40)
    print(f"项目计划: {proj.get_plan()}")

def run_tests():
    print("测试: 项目管理")
    p = Project("Test", "Test project")
    p.add_milestone("M1", "2024-01")
    p.add_task("T1", "A", 10)
    assert len(p.milestones) == 1
    assert p.get_plan()["total_hours"] == 10
    print("✓ 项目测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
