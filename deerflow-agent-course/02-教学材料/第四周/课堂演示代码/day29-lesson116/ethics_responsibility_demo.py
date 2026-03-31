#!/usr/bin/env python3
# 第116节课：伦理与责任
from typing import Dict, Any, List

class SafetyGuardrail:
    def __init__(self):
        self.rules: List[Dict] = []
    
    def add_rule(self, name: str, pattern: str, action: str):
        self.rules.append({"name": name, "pattern": pattern, "action": action})
    
    def check(self, content: str) -> Dict:
        for rule in self.rules:
            if rule["pattern"].lower() in content.lower():
                return {"blocked": True, "rule": rule["name"]}
        return {"blocked": False}

class HumanOversight:
    def __init__(self):
        self.pending_reviews: List[Dict] = []
    
    def request_review(self, decision: Dict) -> str:
        review_id = f"review-{len(self.pending_reviews)}"
        self.pending_reviews.append({"id": review_id, "decision": decision, "status": "pending"})
        return review_id
    
    def approve(self, review_id: str) -> bool:
        for r in self.pending_reviews:
            if r["id"] == review_id:
                r["status"] = "approved"
                return True
        return False

def run_demo():
    print("伦理与责任演示")
    guard = SafetyGuardrail()
    guard.add_rule("violence", "violence", "block")
    result = guard.check("This contains violence")
    print(f"安全检查: {result}")

def run_tests():
    print("测试: 安全护栏")
    g = SafetyGuardrail()
    g.add_rule("test", "bad", "block")
    assert g.check("This is bad")["blocked"] == True
    assert g.check("This is good")["blocked"] == False
    print("✓ 安全护栏测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
