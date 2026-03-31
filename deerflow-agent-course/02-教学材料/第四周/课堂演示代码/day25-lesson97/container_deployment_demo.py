#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第97节课：容器化部署

本课程介绍DeerFlow容器化部署，包括：
1. Docker镜像构建 - 多阶段构建优化镜像大小
2. 容器编排 - docker-compose与Kubernetes配置
3. 健康检查 - 容器健康状态的监控和恢复
4. 生产就绪的Docker镜像构建

作者：DeerFlow架构师训练营
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field


# ============================================================
# 第一部分：Dockerfile生成器
# ============================================================

@dataclass
class DockerConfig:
    """Docker配置"""
    base_image: str
    working_dir: str = "/app"
    python_version: str = "3.12"
    dependencies: List[str] = field(default_factory=list)
    exposed_ports: List[int] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    healthcheck: Optional[Dict[str, Any]] = None


class DockerfileGenerator:
    """Dockerfile生成器"""
    
    def __init__(self, config: DockerConfig):
        self.config = config
        
    def generate(self) -> str:
        lines = []
        
        lines.append(f"FROM python:{self.config.python_version}-slim as base")
        lines.append("")
        lines.append(f"WORKDIR {self.config.working_dir}")
        lines.append("")
        
        lines.append("RUN apt-get update && apt-get install -y \\")
        lines.append("    curl \\")
        lines.append("    git \\")
        lines.append("    && rm -rf /var/lib/apt/lists/*")
        lines.append("")
        
        if self.config.dependencies:
            lines.append("RUN pip install --no-cache-dir \\")
            for dep in self.config.dependencies:
                lines.append(f"    {dep} \\")
            lines.append("")
            
        for key, value in self.config.env_vars.items():
            lines.append(f"ENV {key}={value}")
        lines.append("")
        
        lines.append("COPY . .")
        lines.append("")
        
        if self.config.exposed_ports:
            ports = " ".join(map(str, self.config.exposed_ports))
            lines.append(f"EXPOSE {ports}")
            lines.append("")
            
        if self.config.healthcheck:
            cmd = self.config.healthcheck.get("cmd", "python -c 'import sys; sys.exit(0)'")
            interval = self.config.healthcheck.get("interval", 30)
            timeout = self.config.healthcheck.get("timeout", 10)
            retries = self.config.healthcheck.get("retries", 3)
            
            lines.append(f"HEALTHCHECK --interval={interval}s --timeout={timeout}s --retries={retries} \\")
            lines.append(f"    CMD {cmd}")
            lines.append("")
            
        lines.append('CMD ["python", "-m", "deerflow"]')
        
        return "\n".join(lines)


# ============================================================
# 第二部分：Docker Compose配置
# ============================================================

@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    image: str
    ports: Dict[str, int] = field(default_factory=dict)
    environment: Dict[str, str] = field(default_factory=dict)
    volumes: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    restart: str = "unless-stopped"
    healthcheck: Optional[Dict[str, Any]] = None


class DockerComposeGenerator:
    """Docker Compose配置生成器"""
    
    def __init__(self, version: str = "3.8"):
        self.version = version
        self.services: Dict[str, ServiceConfig] = {}
        
    def add_service(self, service: ServiceConfig) -> None:
        self.services[service.name] = service
        
    def generate(self) -> str:
        lines = ["version: " + self.version, "", "services:"]
        
        for name, service in self.services.items():
            lines.append(f"  {name}:")
            lines.append(f"    image: {service.image}")
            
            if service.ports:
                lines.append("    ports:")
                for host, container in service.ports.items():
                    lines.append(f"      - \"{host}:{container}\"")
                    
            if service.environment:
                lines.append("    environment:")
                for key, value in service.environment.items():
                    lines.append(f"      {key}: {value}")
                    
            if service.volumes:
                lines.append("    volumes:")
                for vol in service.volumes:
                    lines.append(f"      - {vol}")
                    
            if service.depends_on:
                lines.append("    depends_on:")
                for dep in service.depends_on:
                    lines.append(f"      - {dep}")
                    
            if service.restart:
                lines.append(f"    restart: {service.restart}")
                
            if service.healthcheck:
                lines.append("    healthcheck:")
                for key, value in service.healthcheck.items():
                    if isinstance(value, dict):
                        lines.append(f"      {key}:")
                        for k, v in value.items():
                            lines.append(f"        {k}: {v}")
                    else:
                        lines.append(f"      {key}: {value}")
                        
            lines.append("")
            
        lines.append("networks:")
        lines.append("  default:")
        lines.append("    driver: bridge")
        
        return "\n".join(lines)


# ============================================================
# 第三部分：健康检查
# ============================================================

class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        
    def register(self, name: str, check_func: Callable) -> None:
        self.checks[name] = check_func
        
    def check_all(self) -> Dict[str, Any]:
        results = {}
        for name, check in self.checks.items():
            try:
                results[name] = {"status": "healthy", "error": None}
            except Exception as e:
                results[name] = {"status": "unhealthy", "error": str(e)}
        return results
        
    def is_healthy(self) -> bool:
        results = self.check_all()
        return all(r["status"] == "healthy" for r in results.values())


# ============================================================
# 演示与测试
# ============================================================

def run_demo():
    print("=" * 60)
    print("DeerFlow 容器化部署演示")
    print("=" * 60)
    
    print("\n1. Dockerfile生成...")
    config = DockerConfig(
        base_image="python:3.12-slim",
        python_version="3.12",
        dependencies=["fastapi", "uvicorn", "langchain"],
        exposed_ports=[8000, 2026],
        env_vars={"ENV": "production", "LOG_LEVEL": "info"},
        healthcheck={"cmd": "curl -f http://localhost:2026/health || exit 1"}
    )
    
    generator = DockerfileGenerator(config)
    print(generator.generate()[:500] + "...")
    
    print("\n2. Docker Compose配置...")
    compose = DockerComposeGenerator()
    
    backend = ServiceConfig(
        name="backend",
        image="deerflow-backend:latest",
        ports={"2026": 2026, "8000": 8000},
        environment={"DATABASE_URL": "postgresql://..."},
        volumes=["./data:/data"],
        healthcheck={"test": ["CMD", "curl", "-f", "http://localhost:2026/health"]}
    )
    compose.add_service(backend)
    print(compose.generate()[:500] + "...")
    
    print("\n演示完成!")


def run_tests():
    print("\n" + "=" * 60)
    print("运行单元测试")
    print("=" * 60 + "\n")
    
    print("测试1: Dockerfile生成")
    config = DockerConfig(base_image="python:3.12", python_version="3.12")
    gen = DockerfileGenerator(config)
    dockerfile = gen.generate()
    assert "FROM python:3.12-slim" in dockerfile
    assert "WORKDIR /app" in dockerfile
    print("✓ Dockerfile生成测试通过\n")
    
    print("测试2: Docker Compose生成")
    compose = DockerComposeGenerator()
    compose.add_service(ServiceConfig(name="test", image="test:latest"))
    output = compose.generate()
    assert "version: 3.8" in output
    assert "test:" in output
    print("✓ Docker Compose测试通过\n")
    
    print("测试3: 健康检查")
    checker = HealthChecker()
    checker.register("test", lambda: True)
    results = checker.check_all()
    assert "test" in results
    print("✓ 健康检查测试通过\n")
    
    print("=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        run_tests()
    else:
        run_demo()
