#!/usr/bin/env python3
# 第115节课：可解释性与透明度
from typing import Dict, Any, List

class DecisionLog:
    def __init__(self):
        self.decisions: List[Dict] = []
    
    def log(self, decision: str, reason: str, confidence: float):
        self.decisions.append({"decision": decision, "reason": reason, "confidence": confidence})
    
    def get_explanation(self, index: int) -> Dict:
        if 0 <= index < len(self.decisions):
            return self.decisions[index]
        return {}

class BiasDetector:
    def __init__(self):
        self.biases: List[Dict] = []
    
    def detect(self, data: List[Dict]) -> List[Dict]:
        return []
    
    def report(self) -> Dict:
        return {"total_biases": len(self.biases), "severity": "low"}

def run_demo():
    print("可解释性演示")
    log = DecisionLog()
    log.log("批准贷款", "信用评分>700", 0.95)
    print(f"决策: {log.get_explanation(0)}")

def run_tests():
    print("测试: 决策日志")
    l = DecisionLog()
    l.log("d1", "r1", 0.9)
    assert l.get_explanation(0)["decision"] == "d1"
    print("✓ 决策日志测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
