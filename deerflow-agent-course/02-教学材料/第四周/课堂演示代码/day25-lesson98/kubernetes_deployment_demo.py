#!/usr/bin/env python3
# 第98节课：Kubernetes部署
import os, json, time
from typing import Dict, Any, List
from dataclasses import dataclass, field

@dataclass
class K8sResource:
    kind: str
    name: str
    spec: Dict[str, Any] = field(default_factory=dict)

class K8sManifestGenerator:
    def __init__(self): self.resources = []
    def add_deployment(self, name: str, replicas: int = 3) -> None:
        self.resources.append({
            "kind": "Deployment",
            "metadata": {"name": name},
            "spec": {
                "replicas": replicas,
                "selector": {"matchLabels": {"app": name}},
                "template": {
                    "metadata": {"labels": {"app": name}},
                    "spec": {"containers": [{"name": name, "image": f"{name}:latest"}]}
                }
            }
        })
    def add_service(self, name: str, port: int) -> None:
        self.resources.append({
            "kind": "Service",
            "metadata": {"name": name},
            "spec": {"selector": {"app": name}, "ports": [{"port": port}]}
        })
    def add_ingress(self, name: str, host: str) -> None:
        self.resources.append({
            "kind": "Ingress",
            "metadata": {"name": name},
            "spec": {"rules": [{"host": host, "http": {"paths": [{"path": "/", "backend": {"service": {"name": name, "port": {"number": 80}}}}]}}]}
        })
    def generate(self) -> str:
        return "\n---\n".join(json.dumps(r, indent=2) for r in self.resources)

class HPAConfig:
    def __init__(self, name: str):
        self.name = name
        self.min_replicas = 1
        self.max_replicas = 10
        self.target_cpu_percent = 70
    def to_dict(self) -> Dict:
        return {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {"name": self.name},
            "spec": {
                "scaleTargetRef": {"apiVersion": "apps/v1", "kind": "Deployment", "name": self.name},
                "minReplicas": self.min_replicas,
                "maxReplicas": self.max_replicas,
                "metrics": [{"type": "Resource", "resource": {"name": "cpu", "target": {"type": "Utilization", "utilizationValue": self.target_cpu_percent}}}]
            }
        }

def run_demo():
    print("K8s Manifest生成演示")
    gen = K8sManifestGenerator()
    gen.add_deployment("deerflow", replicas=3)
    gen.add_service("deerflow", port=2026)
    gen.add_ingress("deerflow", "deerflow.example.com")
    print(gen.generate())
    print("\nHPA配置:")
    hpa = HPAConfig("deerflow")
    print(json.dumps(hpa.to_dict(), indent=2))

def run_tests():
    print("测试: K8s Manifest生成")
    gen = K8sManifestGenerator()
    gen.add_deployment("test", replicas=2)
    assert len(gen.resources) == 1
    gen.add_service("test", 80)
    assert len(gen.resources) == 2
    assert gen.resources[0]["spec"]["replicas"] == 2
    print("✓ K8s测试通过")
    
    print("测试: HPA配置")
    hpa = HPAConfig("test")
    hpa.min_replicas = 2
    hpa.max_replicas = 5
    config = hpa.to_dict()
    assert config["spec"]["minReplicas"] == 2
    assert config["spec"]["maxReplicas"] == 5
    print("✓ HPA测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
