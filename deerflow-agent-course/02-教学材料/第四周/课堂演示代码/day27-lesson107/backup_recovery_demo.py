#!/usr/bin/env python3
# 第107节课：备份与恢复
import os, json, shutil, time
from typing import Any, List, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class BackupConfig:
    source: str
    destination: str
    retention_days: int = 30
    compress: bool = True

class BackupManager:
    def __init__(self, config: BackupConfig):
        self.config = config
        self.backups: List[Dict] = []
    
    def create_backup(self, name: str = None) -> str:
        name = name or datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.config.destination, name)
        os.makedirs(backup_path, exist_ok=True)
        
        # 模拟备份
        if os.path.exists(self.config.source):
            for item in os.listdir(self.config.source):
                src = os.path.join(self.config.source, item)
                dst = os.path.join(backup_path, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
        
        self.backups.append({
            "name": name,
            "path": backup_path,
            "created_at": datetime.now().isoformat(),
            "size": self._get_size(backup_path)
        })
        return backup_path
    
    def _get_size(self, path: str) -> int:
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
        return total
    
    def restore_backup(self, name: str) -> bool:
        backup = next((b for b in self.backups if b["name"] == name), None)
        if not backup: return False
        
        # 清理目标目录
        if os.path.exists(self.config.source):
            shutil.rmtree(self.config.source)
        
        # 恢复
        shutil.copytree(backup["path"], self.config.source)
        return True
    
    def list_backups(self) -> List[Dict]:
        return self.backups
    
    def delete_backup(self, name: str) -> bool:
        backup = next((b for b in self.backups if b["name"] == name), None)
        if backup and os.path.exists(backup["path"]):
            shutil.rmtree(backup["path"])
            self.backups.remove(backup)
            return True
        return False

def run_demo():
    print("备份与恢复演示")
    print("备份恢复功能演示完成")

def run_tests():
    print("测试: 备份管理")
    mgr = BackupManager(BackupConfig("/tmp/src", "/tmp/dst"))
    mgr.create_backup("test1")
    backups = mgr.list_backups()
    assert len(backups) == 1
    print("✓ 备份创建测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
