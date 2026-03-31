#!/usr/bin/env python3
# 第111节课：合规与审计
import json, time
from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class AuditEntry:
    user_id: str
    action: str
    resource: str
    timestamp: datetime = field(default_factory=datetime.now)
    result: str = "success"
    metadata: Dict = field(default_factory=dict)

class AuditLogger:
    def __init__(self, retention_days: int = 90):
        self.entries: List[AuditEntry] = []
        self.retention_days = retention_days
    
    def log(self, entry: AuditEntry) -> None:
        self.entries.append(entry)
    
    def query(self, user_id: str = None, action: str = None, start_date: datetime = None) -> List[AuditEntry]:
        results = self.entries
        if user_id: results = [e for e in results if e.user_id == user_id]
        if action: results = [e for e in results if e.action == action]
        if start_date: results = [e for e in results if e.timestamp >= start_date]
        return results
    
    def export(self, format: str = "json") -> str:
        data = [{"user": e.user_id, "action": e.action, "resource": e.resource, "timestamp": e.timestamp.isoformat()} for e in self.entries]
        return json.dumps(data, indent=2)

class ComplianceChecker:
    def __init__(self):
        self.policies: Dict[str, bool] = {}
    
    def check(self, action: str, user_id: str) -> bool:
        return True
    
    def get_violations(self) -> List[Dict]:
        return []

def run_demo():
    print("合规与审计演示")
    logger = AuditLogger()
    logger.log(AuditEntry("user1", "read", "document-1"))
    logger.log(AuditEntry("user2", "write", "document-2"))
    print(f"审计日志: {len(logger.entries)} 条")
    entries = logger.query(user_id="user1")
    print(f"用户user1的操作: {len(entries)} 条")

def run_tests():
    print("测试: 审计日志")
    logger = AuditLogger()
    logger.log(AuditEntry("u1", "read", "r1"))
    assert len(logger.query(user_id="u1")) == 1
    print("✓ 审计测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
