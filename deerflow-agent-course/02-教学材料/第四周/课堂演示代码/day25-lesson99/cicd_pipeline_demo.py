#!/usr/bin/env python3
# 第99节课：CI/CD流水线
import os, json, time, subprocess
from typing import Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

class StageType(Enum): 
    BUILD = "build" 
    TEST = "test" 
    DEPLOY = "deploy"

@dataclass
class PipelineStage:
    name: str
    stage_type: StageType
    commands: List[str]
    enabled: bool = True

class PipelineConfig:
    def __init__(self, name: str):
        self.name = name
        self.stages: List[PipelineStage] = []
        self.env: Dict[str, str] = {}
    def add_stage(self, stage: PipelineStage) -> None:
        self.stages.append(stage)
    def add_env(self, key: str, value: str) -> None:
        self.env[key] = value

class GitHubActionsGenerator:
    def __init__(self, pipeline: PipelineConfig):
        self.pipeline = pipeline
    def generate(self) -> str:
        lines = [
            f"name: {self.pipeline.name}",
            "on: [push, pull_request]",
            "env:",
        ]
        for k, v in self.pipeline.env.items():
            lines.append(f"  {k}: {v}")
        lines.append("jobs:")
        lines.append("  build:")
        lines.append("    runs-on: ubuntu-latest")
        lines.append("    steps:")
        for stage in self.pipeline.stages:
            if not stage.enabled: continue
            lines.append(f"      - name: {stage.name}")
            lines.append("        run: |")
            for cmd in stage.commands:
                lines.append(f"          {cmd}")
        return "\n".join(lines)

class BuildRunner:
    def __init__(self): self.artifacts = {}
    def build_docker(self, name: str, tag: str = "latest") -> bool:
        print(f"Building Docker image {name}:{tag}...")
        time.sleep(0.1)
        self.artifacts[name] = f"{name}:{tag}"
        return True
    def build_python(self, requirements: List[str]) -> bool:
        print(f"Installing {len(requirements)} dependencies...")
        time.sleep(0.1)
        return True
    def get_artifacts(self) -> Dict[str, str]:
        return self.artifacts

class TestRunner:
    def __init__(self): self.results = []
    def run_tests(self, test_files: List[str]) -> Dict[str, Any]:
        print(f"Running {len(test_files)} test files...")
        time.sleep(0.1)
        return {"passed": len(test_files), "failed": 0, "skipped": 0}
    def run_lint(self, tool: str = "ruff") -> bool:
        print(f"Running {tool} linter...")
        time.sleep(0.1)
        return True

def run_demo():
    print("CI/CD流水线演示")
    pipeline = PipelineConfig("DeerFlow CI")
    pipeline.add_env("PYTHON_VERSION", "3.12")
    pipeline.add_stage(PipelineStage("Install dependencies", StageType.BUILD, ["pip install -r requirements.txt"]))
    pipeline.add_stage(PipelineStage("Run tests", StageType.TEST, ["pytest tests/"]))
    pipeline.add_stage(PipelineStage("Build Docker", StageType.DEPLOY, ["docker build -t deerflow ."]))
    gen = GitHubActionsGenerator(pipeline)
    print(gen.generate())

def run_tests():
    print("测试: Pipeline配置")
    p = PipelineConfig("test")
    p.add_stage(PipelineStage("build", StageType.BUILD, ["echo hello"]))
    assert len(p.stages) == 1
    print("✓ Pipeline测试通过")
    
    print("测试: GitHub Actions生成")
    gen = GitHubActionsGenerator(p)
    yaml = gen.generate()
    assert "name: test" in yaml
    assert "build" in yaml
    print("✓ Actions生成测试通过")
    
    print("测试: Build运行")
    runner = BuildRunner()
    assert runner.build_docker("test")
    assert "test" in runner.get_artifacts()
    print("✓ Build测试通过")
    
    print("测试: Test运行")
    test_runner = TestRunner()
    result = test_runner.run_tests(["test1.py", "test2.py"])
    assert result["passed"] == 2
    print("✓ Test运行测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
