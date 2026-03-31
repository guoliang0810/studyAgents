#!/usr/bin/env python3
# 第110节课：企业认证集成
import hashlib, secrets
from typing import Dict, Any, Optional, List

class SSOProvider:
    def __init__(self, provider_type: str):
        self.provider_type = provider_type
        self.users: Dict[str, Dict] = {}
    
    def authenticate(self, token: str) -> Optional[Dict]:
        for user in self.users.values():
            if user.get("token") == token:
                return user
        return None
    
    def add_user(self, user_id: str, email: str, groups: List[str]):
        self.users[user_id] = {"email": email, "groups": groups, "token": secrets.token_urlsafe(32)}

class LDAPConnector:
    def __init__(self, server: str, port: int = 389):
        self.server = server
        self.port = port
        self.connected = False
    
    def connect(self) -> bool:
        self.connected = True
        return True
    
    def authenticate(self, username: str, password: str) -> bool:
        return self.connected

class APIKeyManager:
    def __init__(self):
        self.keys: Dict[str, Dict] = {}
    
    def create_key(self, name: str, permissions: List[str], expires_in: int = None) -> str:
        key = secrets.token_urlsafe(32)
        self.keys[key] = {"name": name, "permissions": permissions, "expires_in": expires_in}
        return key
    
    def validate_key(self, key: str) -> bool:
        if key in self.keys:
            return True
        return False

def run_demo():
    print("企业认证集成演示")
    sso = SSOProvider("saml")
    sso.add_user("u1", "user@example.com", ["admin", "users"])
    print(f"SSO用户: {sso.users}")
    mgr = APIKeyManager()
    key = mgr.create_key("test-key", ["read", "write"])
    print(f"API Key: {key}")

def run_tests():
    print("测试: SSO")
    sso = SSOProvider("oidc")
    sso.add_user("1", "test@test.com", ["users"])
    assert sso.authenticate(sso.users["1"]["token"]) is not None
    print("✓ SSO测试通过")
    print("测试: API Key")
    mgr = APIKeyManager()
    key = mgr.create_key("test", ["read"])
    assert mgr.validate_key(key)
    print("✓ API Key测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
