#!/usr/bin/env python3
# 第109节课：多租户架构
from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Tenant:
    id: str
    name: str
    quota: Dict[str, int] = field(default_factory=lambda: {"requests": 1000, "storage_mb": 100})
    is_active: bool = True

class TenantManager:
    def __init__(self):
        self.tenants: Dict[str, Tenant] = {}
    
    def create_tenant(self, id: str, name: str, quota: Dict[str, int] = None) -> Tenant:
        tenant = Tenant(id=id, name=name, quota=quota or {})
        self.tenants[id] = tenant
        return tenant
    
    def get_tenant(self, id: str) -> Tenant:
        return self.tenants.get(id)
    
    def update_quota(self, id: str, quota: Dict[str, int]) -> bool:
        tenant = self.get_tenant(id)
        if tenant:
            tenant.quota = quota
            return True
        return False
    
    def check_quota(self, id: str, resource: str, amount: int) -> bool:
        tenant = self.get_tenant(id)
        if not tenant or not tenant.is_active:
            return False
        return tenant.quota.get(resource, float('inf')) >= amount

class DataIsolation:
    def __init__(self):
        self.isolation_level = "logical"  # or "physical"
    
    def get_data_scope(self, tenant_id: str) -> Dict[str, str]:
        if self.isolation_level == "logical":
            return {"table": "data", "filter": f"tenant_id = '{tenant_id}'"}
        return {"table": f"tenant_{tenant_id}", "filter": None}

def run_demo():
    print("多租户架构演示")
    mgr = TenantManager()
    t = mgr.create_tenant("t1", "Company A", {"requests": 5000, "storage_mb": 500})
    print(f"租户: {t.name}, 配额: {t.quota}")
    print(f"配额检查: {mgr.check_quota('t1', 'requests', 1000)}")
    iso = DataIsolation()
    print(f"数据隔离: {iso.get_data_scope('t1')}")

def run_tests():
    print("测试: 租户管理")
    mgr = TenantManager()
    t = mgr.create_tenant("t1", "Test")
    assert mgr.get_tenant("t1").name == "Test"
    assert mgr.check_quota("t1", "requests", 500)
    print("✓ 租户管理测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
