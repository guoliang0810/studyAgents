#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置版本控制演示代码
Day 16 - 第64节课：配置版本控制

本演示代码展示了DeerFlow Agent系统中配置版本控制的核心实现，包括：
1. ConfigVersion数据类：定义配置版本的元数据
2. ConfigVersionManager：基于Git的配置版本管理器
3. ConfigMigrationTool：配置迁移工具，支持版本升级和回滚
4. 配置差异比较算法：递归比较配置变更
5. 版本审计和回滚机制：安全地管理配置变更历史

学习目标：
- 掌握基于Git的配置版本管理实现
- 理解配置迁移工具的设计和实现
- 能够实现配置差异比较算法
- 能够设计版本回滚和安全审计机制
- 能够构建完整的配置版本控制系统
"""

import os
import sys
import json
import yaml
import time
import shutil
import tempfile
import hashlib
import asyncio
import logging
import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
from collections import defaultdict
import difflib

# 尝试导入gitpython，如果未安装则提供备用方案
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    print("警告: gitpython未安装，部分Git功能将不可用")
    print("安装命令: pip install gitpython")

# ============================================================================
# 枚举和常量定义
# ============================================================================

class VersionChangeType(Enum):
    """版本变更类型"""
    ADDED = "added"        # 添加新配置项
    REMOVED = "removed"    # 删除配置项
    MODIFIED = "modified"  # 修改配置项
    RENAMED = "renamed"    # 重命名配置项
    MOVED = "moved"        # 移动配置项


class MigrationStatus(Enum):
    """迁移状态"""
    PENDING = "pending"    # 等待迁移
    SUCCESS = "success"    # 迁移成功
    FAILED = "failed"      # 迁移失败
    ROLLED_BACK = "rolled_back"  # 已回滚


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class ConfigVersion:
    """配置版本数据类
    
    Attributes:
        version_id: 版本ID（Git commit hash或自定义ID）
        version_name: 版本名称（如v1.2.3）
        config_data: 配置数据字典
        created_at: 创建时间戳
        created_by: 创建者
        comment: 版本注释
        tags: 版本标签
        parent_version: 父版本ID
    """
    version_id: str
    version_name: str
    config_data: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    created_by: str = "system"
    comment: str = ""
    tags: List[str] = field(default_factory=list)
    parent_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        data = asdict(self)
        # 添加格式化时间
        data['created_at_formatted'] = datetime.datetime.fromtimestamp(
            self.created_at).isoformat()
        return data
    
    @property
    def config_hash(self) -> str:
        """计算配置数据的哈希值（用于检测变更）"""
        config_str = json.dumps(self.config_data, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]


@dataclass
class VersionChange:
    """版本变更记录
    
    Attributes:
        change_type: 变更类型
        path: 配置项路径（如 'database.host'）
        old_value: 旧值（如果存在）
        new_value: 新值（如果存在）
        change_level: 变更级别（'info', 'warning', 'danger'）
        description: 变更描述
    """
    change_type: VersionChangeType
    path: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    change_level: str = "info"
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.change_type.value,
            "path": self.path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "level": self.change_level,
            "description": self.description
        }


@dataclass
class MigrationRecord:
    """迁移记录
    
    Attributes:
        migration_id: 迁移ID
        source_version: 源版本
        target_version: 目标版本
        status: 迁移状态
        started_at: 开始时间
        completed_at: 完成时间
        changes_applied: 应用的变更列表
        error_message: 错误信息（如果有）
        rollback_version: 回滚版本（如果回滚）
    """
    migration_id: str
    source_version: str
    target_version: str
    status: MigrationStatus
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    changes_applied: List[VersionChange] = field(default_factory=list)
    error_message: Optional[str] = None
    rollback_version: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """迁移耗时（秒）"""
        if self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def mark_completed(self, success: bool = True, error: Optional[str] = None):
        """标记迁移完成"""
        self.completed_at = time.time()
        self.status = MigrationStatus.SUCCESS if success else MigrationStatus.FAILED
        self.error_message = error
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['status'] = self.status.value
        data['changes_applied'] = [c.to_dict() for c in self.changes_applied]
        data['duration'] = self.duration
        return data


# ============================================================================
# 配置差异比较算法
# ============================================================================

class ConfigDiffCalculator:
    """配置差异计算器
    
    递归比较两个配置字典，识别所有变更。
    """
    
    @staticmethod
    def compare_dicts(
        dict1: Dict[str, Any],
        dict2: Dict[str, Any],
        path: str = ""
    ) -> List[VersionChange]:
        """递归比较两个字典，返回变更列表
        
        Args:
            dict1: 第一个字典（旧版本）
            dict2: 第二个字典（新版本）
            path: 当前路径（用于递归）
            
        Returns:
            List[VersionChange]: 变更列表
        """
        changes = []
        
        # 获取所有键的并集
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        for key in sorted(all_keys):
            current_path = f"{path}.{key}" if path else key
            value1 = dict1.get(key)
            value2 = dict2.get(key)
            
            # 处理键不存在的情况
            if key not in dict1:
                # 新添加的键
                changes.append(VersionChange(
                    change_type=VersionChangeType.ADDED,
                    path=current_path,
                    old_value=None,
                    new_value=value2,
                    description=f"添加新配置项: {current_path}"
                ))
            elif key not in dict2:
                # 删除的键
                changes.append(VersionChange(
                    change_type=VersionChangeType.REMOVED,
                    path=current_path,
                    old_value=value1,
                    new_value=None,
                    change_level="warning",
                    description=f"删除配置项: {current_path}"
                ))
            else:
                # 键都存在，比较值
                changes.extend(ConfigDiffCalculator._compare_values(
                    value1, value2, current_path
                ))
        
        return changes
    
    @staticmethod
    def _compare_values(
        value1: Any,
        value2: Any,
        path: str
    ) -> List[VersionChange]:
        """比较两个值，递归处理字典和列表
        
        Args:
            value1: 第一个值
            value2: 第二个值
            path: 当前路径
            
        Returns:
            List[VersionChange]: 变更列表
        """
        changes = []
        
        # 类型检查
        type1 = type(value1).__name__
        type2 = type(value2).__name__
        
        if type1 != type2:
            # 类型变更
            changes.append(VersionChange(
                change_type=VersionChangeType.MODIFIED,
                path=path,
                old_value=f"{value1} ({type1})",
                new_value=f"{value2} ({type2})",
                change_level="warning",
                description=f"类型变更: {type1} -> {type2}"
            ))
        elif isinstance(value1, dict) and isinstance(value2, dict):
            # 递归比较字典
            changes.extend(ConfigDiffCalculator.compare_dicts(
                value1, value2, path
            ))
        elif isinstance(value1, list) and isinstance(value2, list):
            # 比较列表（简化处理）
            if value1 != value2:
                changes.append(VersionChange(
                    change_type=VersionChangeType.MODIFIED,
                    path=path,
                    old_value=value1,
                    new_value=value2,
                    description=f"列表内容变更: 长度 {len(value1)} -> {len(value2)}"
                ))
        else:
            # 简单值比较
            if value1 != value2:
                changes.append(VersionChange(
                    change_type=VersionChangeType.MODIFIED,
                    path=path,
                    old_value=value1,
                    new_value=value2,
                    description=f"值变更: {value1} -> {value2}"
                ))
        
        return changes
    
    @staticmethod
    def get_change_summary(changes: List[VersionChange]) -> Dict[str, Any]:
        """获取变更摘要
        
        Args:
            changes: 变更列表
            
        Returns:
            Dict[str, Any]: 变更摘要
        """
        summary = {
            "total_changes": len(changes),
            "by_type": defaultdict(int),
            "by_level": defaultdict(int),
            "dangerous_changes": [],
            "breaking_changes": []
        }
        
        for change in changes:
            # 统计类型
            summary["by_type"][change.change_type.value] += 1
            
            # 统计级别
            summary["by_level"][change.change_level] += 1
            
            # 识别危险变更
            if change.change_type == VersionChangeType.REMOVED:
                summary["dangerous_changes"].append(change.to_dict())
            
            if change.change_level == "danger":
                summary["breaking_changes"].append(change.to_dict())
        
        return summary


# ============================================================================
# 基于Git的配置版本管理器
# ============================================================================

class ConfigVersionManager:
    """基于Git的配置版本管理器
    
    使用Git仓库管理配置版本，提供版本创建、获取、比较和回滚功能。
    """
    
    def __init__(self, repo_path: str, auto_init: bool = True):
        """初始化版本管理器
        
        Args:
            repo_path: Git仓库路径
            auto_init: 如果仓库不存在则自动初始化
        """
        self.repo_path = Path(repo_path).absolute()
        self.config_file = self.repo_path / "config.yaml"
        
        if not GIT_AVAILABLE:
            raise ImportError("gitpython未安装，请运行: pip install gitpython")
        
        # 初始化Git仓库
        if auto_init and not self.repo_path.exists():
            self._init_repository()
        
        # 打开或初始化Git仓库
        try:
            self.repo = git.Repo(self.repo_path)
        except git.exc.InvalidGitRepositoryError:
            if auto_init:
                self._init_repository()
                self.repo = git.Repo(self.repo_path)
            else:
                raise
        
        # 确保主分支存在
        if not self.repo.heads:
            self.repo.git.checkout('-b', 'main')
    
    def _init_repository(self):
        """初始化Git仓库"""
        self.repo_path.mkdir(parents=True, exist_ok=True)
        self.repo = git.Repo.init(self.repo_path)
        
        # 创建初始提交
        self.config_file.write_text("# DeerFlow Agent配置\nversion: 1.0.0\n")
        self.repo.index.add([str(self.config_file)])
        self.repo.index.commit("初始配置版本")
        
        print(f"✅ 初始化Git仓库: {self.repo_path}")
    
    def create_version(
        self,
        config: Dict[str, Any],
        version_name: str,
        comment: str = "",
        author: str = "system",
        tags: List[str] = None
    ) -> ConfigVersion:
        """创建新配置版本
        
        Args:
            config: 配置数据
            version_name: 版本名称（如v1.2.3）
            comment: 版本注释
            author: 作者
            tags: 版本标签
            
        Returns:
            ConfigVersion: 创建的版本对象
        """
        # 写入配置文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        # 添加到Git暂存区
        self.repo.index.add([str(self.config_file)])
        
        # 创建提交
        commit_message = f"{version_name}\n\n{comment}".strip()
        commit = self.repo.index.commit(
            commit_message,
            author=git.Actor(author, f"{author}@deerflow.tech"),
            committer=git.Actor(author, f"{author}@deerflow.tech")
        )
        
        # 添加标签（如果版本名称是语义化版本）
        if version_name.startswith('v'):
            try:
                self.repo.create_tag(version_name, commit.hexsha)
            except git.exc.GitCommandError:
                pass  # 标签已存在
        
        # 创建版本对象
        version = ConfigVersion(
            version_id=commit.hexsha,
            version_name=version_name,
            config_data=config.copy(),
            created_at=commit.committed_date,
            created_by=author,
            comment=comment,
            tags=tags or [],
            parent_version=self._get_parent_commit_hash(commit)
        )
        
        print(f"✅ 创建配置版本: {version_name} ({commit.hexsha[:8]})")
        return version
    
    def get_version(self, version_ref: str) -> Optional[ConfigVersion]:
        """获取指定版本的配置
        
        Args:
            version_ref: 版本引用（commit hash、标签、分支名）
            
        Returns:
            Optional[ConfigVersion]: 版本对象，如果不存在则返回None
        """
        try:
            # 解析版本引用
            commit = self.repo.commit(version_ref)
            
            # 切换到该版本
            self.repo.git.checkout(commit.hexsha)
            
            # 读取配置
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # 切换回主分支
            self.repo.git.checkout('main')
            
            # 获取版本名称（优先使用标签，否则使用commit hash）
            version_name = version_ref
            for tag in self.repo.tags:
                if tag.commit.hexsha == commit.hexsha:
                    version_name = tag.name
                    break
            
            # 创建版本对象
            return ConfigVersion(
                version_id=commit.hexsha,
                version_name=version_name,
                config_data=config,
                created_at=commit.committed_date,
                created_by=commit.author.name,
                comment=commit.message.split('\n\n', 1)[-1] if '\n\n' in commit.message else "",
                parent_version=self._get_parent_commit_hash(commit)
            )
            
        except (git.exc.GitCommandError, KeyError, ValueError):
            return None
    
    def list_versions(
        self,
        limit: int = 50,
        include_tags: bool = True
    ) -> List[ConfigVersion]:
        """列出所有配置版本
        
        Args:
            limit: 返回版本数量限制
            include_tags: 是否包含标签版本
            
        Returns:
            List[ConfigVersion]: 版本列表
        """
        versions = []
        
        # 获取提交历史
        commits = list(self.repo.iter_commits('main', max_count=limit))
        
        for commit in commits:
            # 获取该版本的配置
            self.repo.git.checkout(commit.hexsha)
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # 获取版本名称
            version_name = commit.hexsha[:8]
            if include_tags:
                for tag in self.repo.tags:
                    if tag.commit.hexsha == commit.hexsha:
                        version_name = tag.name
                        break
            
            # 创建版本对象
            version = ConfigVersion(
                version_id=commit.hexsha,
                version_name=version_name,
                config_data=config,
                created_at=commit.committed_date,
                created_by=commit.author.name,
                comment=commit.message.split('\n\n', 1)[-1] if '\n\n' in commit.message else "",
                parent_version=self._get_parent_commit_hash(commit)
            )
            versions.append(version)
        
        # 切换回主分支
        self.repo.git.checkout('main')
        
        return versions
    
    def compare_versions(
        self,
        version1_ref: str,
        version2_ref: str
    ) -> List[VersionChange]:
        """比较两个版本的配置差异
        
        Args:
            version1_ref: 第一个版本引用
            version2_ref: 第二个版本引用
            
        Returns:
            List[VersionChange]: 差异列表
        """
        # 获取两个版本的配置
        version1 = self.get_version(version1_ref)
        version2 = self.get_version(version2_ref)
        
        if not version1 or not version2:
            raise ValueError("版本不存在")
        
        # 比较配置
        return ConfigDiffCalculator.compare_dicts(
            version1.config_data,
            version2.config_data
        )
    
    def rollback_to_version(self, target_version_ref: str) -> ConfigVersion:
        """回滚到指定版本
        
        Args:
            target_version_ref: 目标版本引用
            
        Returns:
            ConfigVersion: 回滚后的新版本
        """
        # 获取当前版本
        current_version = self.get_version('HEAD')
        if not current_version:
            raise ValueError("无法获取当前版本")
        
        # 获取目标版本
        target_version = self.get_version(target_version_ref)
        if not target_version:
            raise ValueError(f"目标版本不存在: {target_version_ref}")
        
        # 比较差异
        changes = self.compare_versions(
            current_version.version_id,
            target_version.version_id
        )
        
        # 创建回滚版本
        rollback_version_name = f"rollback-to-{target_version.version_name}"
        rollback_comment = f"回滚到版本 {target_version.version_name}\n\n"
        rollback_comment += f"原因: 从 {current_version.version_name} 回滚\n"
        rollback_comment += f"变更数量: {len(changes)}"
        
        # 创建新版本（使用目标版本的配置）
        rollback_version = self.create_version(
            config=target_version.config_data.copy(),
            version_name=rollback_version_name,
            comment=rollback_comment,
            author="system",
            tags=["rollback"]
        )
        
        print(f"✅ 回滚完成: {current_version.version_name} -> {target_version.version_name}")
        return rollback_version
    
    def get_version_tree(self) -> Dict[str, Any]:
        """获取版本树结构
        
        Returns:
            Dict[str, Any]: 版本树
        """
        tree = {
            "root": None,
            "versions": {},
            "branches": ["main"],
            "tags": []
        }
        
        # 收集所有版本
        versions = self.list_versions(limit=1000, include_tags=True)
        
        for version in versions:
            tree["versions"][version.version_id] = {
                "name": version.version_name,
                "parent": version.parent_version,
                "created_at": version.created_at,
                "author": version.created_by,
                "is_tag": version.version_name.startswith('v')
            }
            
            if version.version_name.startswith('v'):
                tree["tags"].append(version.version_name)
        
        # 找到根版本（没有父版本的版本）
        for version_id, info in tree["versions"].items():
            if info["parent"] is None or info["parent"] not in tree["versions"]:
                tree["root"] = version_id
                break
        
        return tree
    
    def _get_parent_commit_hash(self, commit: git.Commit) -> Optional[str]:
        """获取父提交的哈希值
        
        Args:
            commit: Git提交对象
            
        Returns:
            Optional[str]: 父提交哈希，如果没有则返回None
        """
        if commit.parents:
            return commit.parents[0].hexsha
        return None


# ============================================================================
# 配置迁移工具
# ============================================================================

class ConfigMigrationTool:
    """配置迁移工具
    
    负责将配置从一个版本迁移到另一个版本，支持升级和回滚操作。
    """
    
    def __init__(self):
        """初始化迁移工具"""
        self.migrations: Dict[str, Callable] = {}  # version -> migration_func
        self.migration_records: List[MigrationRecord] = []
        self._migration_lock = asyncio.Lock()
    
    def register_migration(
        self,
        source_version: str,
        target_version: str,
        migration_func: Callable[[Dict[str, Any]], Dict[str, Any]]
    ):
        """注册迁移函数
        
        Args:
            source_version: 源版本
            target_version: 目标版本
            migration_func: 迁移函数，接收旧配置，返回新配置
        """
        migration_key = f"{source_version}->{target_version}"
        self.migrations[migration_key] = migration_func
        print(f"✅ 注册迁移: {migration_key}")
    
    def register_migration_chain(
        self,
        version_chain: List[str],
        migration_funcs: List[Callable]
    ):
        """注册迁移链
        
        Args:
            version_chain: 版本链，如 ['v1.0.0', 'v1.1.0', 'v2.0.0']
            migration_funcs: 对应的迁移函数列表
        """
        if len(version_chain) != len(migration_funcs) + 1:
            raise ValueError("版本链长度应比迁移函数数量多1")
        
        for i in range(len(migration_funcs)):
            source = version_chain[i]
            target = version_chain[i + 1]
            self.register_migration(source, target, migration_funcs[i])
    
    async def migrate(
        self,
        config: Dict[str, Any],
        source_version: str,
        target_version: str,
        dry_run: bool = False
    ) -> Tuple[Dict[str, Any], MigrationRecord]:
        """执行配置迁移
        
        Args:
            config: 源配置
            source_version: 源版本
            target_version: 目标版本
            dry_run: 是否干运行（只计算变更，不实际应用）
            
        Returns:
            Tuple[Dict[str, Any], MigrationRecord]: 迁移后的配置和迁移记录
        """
        async with self._migration_lock:
            # 创建迁移记录
            migration_id = hashlib.sha256(
                f"{source_version}-{target_version}-{time.time()}".encode()
            ).hexdigest()[:16]
            
            record = MigrationRecord(
                migration_id=migration_id,
                source_version=source_version,
                target_version=target_version,
                status=MigrationStatus.PENDING
            )
            
            try:
                # 查找迁移路径
                migration_path = self._find_migration_path(
                    source_version, target_version
                )
                
                if not migration_path:
                    raise ValueError(f"找不到从 {source_version} 到 {target_version} 的迁移路径")
                
                # 执行迁移
                current_config = config.copy()
                changes_applied = []
                
                for step in migration_path:
                    migration_key = f"{step['source']}->{step['target']}"
                    migration_func = self.migrations.get(migration_key)
                    
                    if not migration_func:
                        raise ValueError(f"迁移函数未注册: {migration_key}")
                    
                    # 计算迁移前配置
                    old_config = current_config.copy()
                    
                    # 执行迁移（如果是干运行，只计算变更）
                    if not dry_run:
                        current_config = migration_func(current_config)
                    
                    # 更新版本号
                    current_config['version'] = step['target']
                    
                    # 计算变更
                    step_changes = ConfigDiffCalculator.compare_dicts(
                        old_config, current_config
                    )
                    changes_applied.extend(step_changes)
                    
                    print(f"  🔄 迁移步骤: {step['source']} -> {step['target']} "
                          f"({len(step_changes)} 个变更)")
                
                # 更新迁移记录
                record.changes_applied = changes_applied
                record.mark_completed(success=True)
                
                if dry_run:
                    print(f"✅ 迁移干运行完成: {source_version} -> {target_version} "
                          f"({len(changes_applied)} 个变更)")
                else:
                    print(f"✅ 迁移完成: {source_version} -> {target_version}")
                
                return current_config, record
                
            except Exception as e:
                # 迁移失败
                error_msg = str(e)
                record.mark_completed(success=False, error=error_msg)
                print(f"❌ 迁移失败: {error_msg}")
                
                # 如果是干运行，返回原配置
                if dry_run:
                    return config, record
                else:
                    raise
    
    async def rollback(
        self,
        config: Dict[str, Any],
        target_version: str,
        migration_record_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], MigrationRecord]:
        """回滚配置到指定版本
        
        Args:
            config: 当前配置
            target_version: 目标版本
            migration_record_id: 要回滚的迁移记录ID（可选）
            
        Returns:
            Tuple[Dict[str, Any], MigrationRecord]: 回滚后的配置和迁移记录
        """
        # 获取当前版本
        current_version = config.get('version', 'unknown')
        
        # 创建回滚记录
        rollback_id = hashlib.sha256(
            f"rollback-{current_version}-{target_version}-{time.time()}".encode()
        ).hexdigest()[:16]
        
        record = MigrationRecord(
            migration_id=rollback_id,
            source_version=current_version,
            target_version=target_version,
            status=MigrationStatus.PENDING
        )
        
        try:
            # 查找回滚路径（反向迁移）
            rollback_path = self._find_migration_path(
                current_version, target_version
            )
            
            if not rollback_path:
                raise ValueError(f"找不到从 {current_version} 到 {target_version} 的回滚路径")
            
            # 反转路径（从目标版本到当前版本）
            reverse_path = []
            for step in reversed(rollback_path):
                reverse_path.append({
                    'source': step['target'],
                    'target': step['source']
                })
            
            # 执行反向迁移
            current_config = config.copy()
            changes_applied = []
            
            for step in reverse_path:
                migration_key = f"{step['source']}->{step['target']}"
                migration_func = self.migrations.get(migration_key)
                
                if not migration_func:
                    # 尝试查找反向迁移函数
                    reverse_key = f"{step['target']}->{step['source']}"
                    migration_func = self.migrations.get(reverse_key)
                    
                    if not migration_func:
                        raise ValueError(f"回滚函数未注册: {migration_key}")
                
                # 计算回滚前配置
                old_config = current_config.copy()
                
                # 执行回滚
                current_config = migration_func(current_config)
                
                # 更新版本号
                current_config['version'] = step['target']
                
                # 计算变更
                step_changes = ConfigDiffCalculator.compare_dicts(
                    old_config, current_config
                )
                changes_applied.extend(step_changes)
                
                print(f"  ↩️ 回滚步骤: {step['source']} -> {step['target']} "
                      f"({len(step_changes)} 个变更)")
            
            # 更新迁移记录
            record.changes_applied = changes_applied
            record.rollback_version = target_version
            record.mark_completed(success=True)
            
            print(f"✅ 回滚完成: {current_version} -> {target_version}")
            return current_config, record
            
        except Exception as e:
            error_msg = str(e)
            record.mark_completed(success=False, error=error_msg)
            print(f"❌ 回滚失败: {error_msg}")
            raise
    
    def _find_migration_path(
        self,
        source_version: str,
        target_version: str
    ) -> List[Dict[str, str]]:
        """查找迁移路径（简化版本，实际应使用图搜索算法）
        
        Args:
            source_version: 源版本
            target_version: 目标版本
            
        Returns:
            List[Dict[str, str]]: 迁移路径，每个元素为 {'source': 'v1', 'target': 'v2'}
        """
        # 简化实现：假设版本是线性递增的
        # 实际项目中应使用更复杂的版本图搜索算法
        
        # 提取版本号中的数字
        def parse_version(ver: str) -> List[int]:
            # 移除'v'前缀，按点分割
            ver = ver.lstrip('v')
            parts = ver.split('.')
            return [int(p) for p in parts if p.isdigit()]
        
        try:
            source_parts = parse_version(source_version)
            target_parts = parse_version(target_version)
        except (ValueError, IndexError):
            # 版本解析失败，返回空路径
            return []
        
        # 简单比较：如果目标版本大于源版本，需要升级
        if source_parts < target_parts:
            # 需要查找升级路径
            # 这里简化处理，只返回直接路径
            return [{'source': source_version, 'target': target_version}]
        elif source_parts > target_parts:
            # 需要降级（回滚）
            return [{'source': source_version, 'target': target_version}]
        else:
            # 版本相同，无需迁移
            return []
    
    def get_migration_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取迁移历史
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            List[Dict[str, Any]]: 迁移历史记录
        """
        sorted_records = sorted(
            self.migration_records,
            key=lambda r: r.started_at,
            reverse=True
        )[:limit]
        
        return [record.to_dict() for record in sorted_records]
    
    def get_migration_stats(self) -> Dict[str, Any]:
        """获取迁移统计
        
        Returns:
            Dict[str, Any]: 迁移统计数据
        """
        stats = {
            "total_migrations": len(self.migration_records),
            "successful": 0,
            "failed": 0,
            "rolled_back": 0,
            "by_source_version": defaultdict(int),
            "by_target_version": defaultdict(int)
        }
        
        for record in self.migration_records:
            if record.status == MigrationStatus.SUCCESS:
                stats["successful"] += 1
            elif record.status == MigrationStatus.FAILED:
                stats["failed"] += 1
            elif record.status == MigrationStatus.ROLLED_BACK:
                stats["rolled_back"] += 1
            
            stats["by_source_version"][record.source_version] += 1
            stats["by_target_version"][record.target_version] += 1
        
        return stats


# ============================================================================
# 配置审计工具
# ============================================================================

class ConfigAuditTool:
    """配置审计工具
    
    分析配置变更历史，检测异常模式和潜在问题。
    """
    
    def __init__(self, version_manager: ConfigVersionManager):
        """初始化审计工具
        
        Args:
            version_manager: 配置版本管理器
        """
        self.version_manager = version_manager
    
    def analyze_change_frequency(
        self,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """分析配置变更频率
        
        Args:
            days_back: 回溯天数
            
        Returns:
            Dict[str, Any]: 变更频率分析结果
        """
        # 获取所有版本
        versions = self.version_manager.list_versions(limit=1000)
        
        # 按日期分组
        changes_by_day = defaultdict(int)
        changes_by_author = defaultdict(int)
        changes_by_type = defaultdict(int)
        
        cutoff_time = time.time() - (days_back * 24 * 3600)
        
        for i in range(1, len(versions)):
            version = versions[i]
            
            # 只分析指定时间范围内的变更
            if version.created_at < cutoff_time:
                continue
            
            # 获取与前一个版本的差异
            prev_version = versions[i - 1]
            changes = self.version_manager.compare_versions(
                prev_version.version_id,
                version.version_id
            )
            
            # 统计
            date_str = datetime.datetime.fromtimestamp(
                version.created_at
            ).strftime('%Y-%m-%d')
            
            changes_by_day[date_str] += len(changes)
            changes_by_author[version.created_by] += len(changes)
            
            for change in changes:
                changes_by_type[change.change_type.value] += 1
        
        # 计算趋势
        sorted_days = sorted(changes_by_day.items())
        if len(sorted_days) >= 2:
            trend = "上升" if sorted_days[-1][1] > sorted_days[0][1] else "下降"
        else:
            trend = "稳定"
        
        return {
            "analysis_period_days": days_back,
            "total_changes": sum(changes_by_day.values()),
            "changes_by_day": dict(changes_by_day),
            "changes_by_author": dict(changes_by_author),
            "changes_by_type": dict(changes_by_type),
            "trend": trend,
            "most_active_day": max(changes_by_day.items(), key=lambda x: x[1])[0] if changes_by_day else None,
            "most_active_author": max(changes_by_author.items(), key=lambda x: x[1])[0] if changes_by_author else None
        }
    
    def detect_risky_changes(
        self,
        versions_to_check: int = 20
    ) -> List[Dict[str, Any]]:
        """检测高风险变更
        
        Args:
            versions_to_check: 检查的版本数量
            
        Returns:
            List[Dict[str, Any]]: 高风险变更列表
        """
        risky_changes = []
        versions = self.version_manager.list_versions(limit=versions_to_check)
        
        for i in range(1, len(versions)):
            version = versions[i]
            prev_version = versions[i - 1]
            
            # 比较版本
            changes = self.version_manager.compare_versions(
                prev_version.version_id,
                version.version_id
            )
            
            # 检测高风险变更
            for change in changes:
                risk_level = self._assess_change_risk(change, prev_version, version)
                
                if risk_level in ["high", "critical"]:
                    risky_changes.append({
                        "version": version.version_name,
                        "version_id": version.version_id,
                        "created_at": version.created_at,
                        "author": version.created_by,
                        "change": change.to_dict(),
                        "risk_level": risk_level,
                        "description": self._get_risk_description(change, risk_level)
                    })
        
        return risky_changes
    
    def _assess_change_risk(
        self,
        change: VersionChange,
        prev_version: ConfigVersion,
        current_version: ConfigVersion
    ) -> str:
        """评估变更风险等级
        
        Args:
            change: 变更记录
            prev_version: 前一版本
            current_version: 当前版本
            
        Returns:
            str: 风险等级（'low', 'medium', 'high', 'critical'）
        """
        # 基于变更类型和路径评估风险
        if change.change_type == VersionChangeType.REMOVED:
            # 删除操作通常高风险
            if "password" in change.path.lower() or "secret" in change.path.lower():
                return "critical"
            elif "url" in change.path.lower() or "host" in change.path.lower():
                return "high"
            else:
                return "medium"
        
        elif change.change_type == VersionChangeType.MODIFIED:
            # 修改操作风险取决于路径和值变化
            if "timeout" in change.path.lower() and change.new_value < change.old_value:
                # 减少超时时间可能高风险
                return "high"
            elif "retry" in change.path.lower() and change.new_value > change.old_value:
                # 增加重试次数可能中等风险
                return "medium"
            else:
                return "low"
        
        elif change.change_type == VersionChangeType.ADDED:
            # 新增操作通常低风险
            return "low"
        
        else:
            return "low"
    
    def _get_risk_description(
        self,
        change: VersionChange,
        risk_level: str
    ) -> str:
        """获取风险描述
        
        Args:
            change: 变更记录
            risk_level: 风险等级
            
        Returns:
            str: 风险描述
        """
        descriptions = {
            "critical": f"关键风险: {change.path} 的变更可能影响系统安全或稳定性",
            "high": f"高风险: {change.path} 的变更可能影响系统功能",
            "medium": f"中等风险: {change.path} 的变更可能影响性能或可用性",
            "low": f"低风险: {change.path} 的变更影响较小"
        }
        
        return descriptions.get(risk_level, "未知风险")
    
    def generate_audit_report(
        self,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """生成审计报告
        
        Args:
            days_back: 回溯天数
            
        Returns:
            Dict[str, Any]: 完整的审计报告
        """
        report = {
            "generated_at": time.time(),
            "generated_at_formatted": datetime.datetime.now().isoformat(),
            "analysis_period": f"最近{days_back}天",
            "change_frequency": self.analyze_change_frequency(days_back),
            "risky_changes": self.detect_risky_changes(),
            "recommendations": []
        }
        
        # 生成建议
        freq_analysis = report["change_frequency"]
        
        if freq_analysis["total_changes"] > 100:
            report["recommendations"].append(
                "变更频繁，建议实施变更审批流程"
            )
        
        if len(freq_analysis["changes_by_author"]) == 1:
            report["recommendations"].append(
                "所有变更由单一作者完成，建议增加代码审查"
            )
        
        if report["risky_changes"]:
            high_risk_count = sum(
                1 for rc in report["risky_changes"] 
                if rc["risk_level"] in ["high", "critical"]
            )
            
            if high_risk_count > 0:
                report["recommendations"].append(
                    f"检测到 {high_risk_count} 个高风险变更，建议立即审查"
                )
        
        return report


# ============================================================================
# 示例迁移函数
# ============================================================================

def create_example_migrations() -> ConfigMigrationTool:
    """创建示例迁移函数
    
    Returns:
        ConfigMigrationTool: 配置好的迁移工具
    """
    migration_tool = ConfigMigrationTool()
    
    # v1.0.0 -> v1.1.0 迁移：添加新功能
    def migrate_v1_0_to_v1_1(config: Dict[str, Any]) -> Dict[str, Any]:
        """从v1.0.0迁移到v1.1.0"""
        new_config = config.copy()
        
        # 添加日志配置
        if 'logging' not in new_config:
            new_config['logging'] = {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        
        # 添加监控配置
        if 'monitoring' not in new_config:
            new_config['monitoring'] = {
                'enabled': True,
                'interval': 60,
                'metrics_port': 9090
            }
        
        return new_config
    
    # v1.1.0 -> v1.2.0 迁移：重构数据库配置
    def migrate_v1_1_to_v1_2(config: Dict[str, Any]) -> Dict[str, Any]:
        """从v1.1.0迁移到v1.2.0"""
        new_config = config.copy()
        
        # 重构数据库配置结构
        if 'database' in new_config:
            db_config = new_config['database']
            
            # 旧格式: database: {host: ..., port: ..., name: ...}
            # 新格式: database: {connection: {host: ..., port: ...}, name: ...}
            if 'host' in db_config or 'port' in db_config:
                connection = {}
                
                if 'host' in db_config:
                    connection['host'] = db_config.pop('host')
                if 'port' in db_config:
                    connection['port'] = db_config.pop('port')
                
                db_config['connection'] = connection
        
        return new_config
    
    # v1.2.0 -> v2.0.0 迁移：重大变更
    def migrate_v1_2_to_v2_0(config: Dict[str, Any]) -> Dict[str, Any]:
        """从v1.2.0迁移到v2.0.0"""
        new_config = config.copy()
        
        # 重命名顶级配置项
        if 'api_server' in new_config:
            new_config['http_server'] = new_config.pop('api_server')
        
        # 添加安全配置
        if 'security' not in new_config:
            new_config['security'] = {
                'cors_enabled': True,
                'rate_limit': {
                    'enabled': True,
                    'requests_per_minute': 100
                }
            }
        
        return new_config
    
    # 注册迁移函数
    migration_tool.register_migration('v1.0.0', 'v1.1.0', migrate_v1_0_to_v1_1)
    migration_tool.register_migration('v1.1.0', 'v1.2.0', migrate_v1_1_to_v1_2)
    migration_tool.register_migration('v1.2.0', 'v2.0.0', migrate_v1_2_to_v2_0)
    
    return migration_tool


# ============================================================================
# 演示函数
# ============================================================================

def demo_basic_version_control():
    """演示基础版本控制功能"""
    print("\n" + "="*60)
    print("演示: 基础版本控制功能")
    print("="*60)
    
    # 创建临时目录作为Git仓库
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"临时目录: {temp_dir}")
        
        # 初始化版本管理器
        manager = ConfigVersionManager(temp_dir, auto_init=True)
        
        # 创建初始版本
        config_v1 = {
            "version": "v1.0.0",
            "app": {
                "name": "DeerFlow Agent",
                "environment": "development"
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "deerflow_dev"
            }
        }
        
        version1 = manager.create_version(
            config_v1,
            version_name="v1.0.0",
            comment="初始版本配置",
            author="admin"
        )
        
        # 创建第二个版本
        config_v2 = config_v1.copy()
        config_v2["version"] = "v1.1.0"
        config_v2["database"]["pool_size"] = 10
        config_v2["logging"] = {"level": "DEBUG"}
        
        version2 = manager.create_version(
            config_v2,
            version_name="v1.1.0",
            comment="添加连接池和日志配置",
            author="developer"
        )
        
        # 创建第三个版本
        config_v3 = config_v2.copy()
        config_v3["version"] = "v1.2.0"
        config_v3["cache"] = {"enabled": True, "ttl": 3600}
        config_v3["database"]["host"] = "db.example.com"
        
        version3 = manager.create_version(
            config_v3,
            version_name="v1.2.0",
            comment="添加缓存配置并更新数据库主机",
            author="devops"
        )
        
        # 列出所有版本
        print("\n📚 所有配置版本:")
        versions = manager.list_versions(limit=10)
        for v in versions:
            print(f"  • {v.version_name} ({v.version_id[:8]}) - "
                  f"{datetime.datetime.fromtimestamp(v.created_at).strftime('%Y-%m-%d %H:%M')} - "
                  f"{v.created_by}")
        
        # 比较版本
        print("\n🔍 版本比较 (v1.0.0 vs v1.2.0):")
        changes = manager.compare_versions("v1.0.0", "v1.2.0")
        
        for change in changes:
            print(f"  [{change.change_type.value.upper()}] {change.path}: "
                  f"{change.old_value} -> {change.new_value}")
        
        # 获取变更摘要
        summary = ConfigDiffCalculator.get_change_summary(changes)
        print(f"\n📊 变更摘要:")
        print(f"  总变更数: {summary['total_changes']}")
        print(f"  按类型: {dict(summary['by_type'])}")
        print(f"  危险变更: {len(summary['dangerous_changes'])}")
        
        # 回滚演示
        print("\n↩️ 回滚演示 (回滚到 v1.1.0):")
        rollback_version = manager.rollback_to_version("v1.1.0")
        print(f"  创建回滚版本: {rollback_version.version_name}")
        
        # 获取版本树
        tree = manager.get_version_tree()
        print(f"\n🌳 版本树:")
        print(f"  根版本: {tree['root'][:8] if tree['root'] else 'None'}")
        print(f"  版本数量: {len(tree['versions'])}")
        print(f"  标签: {', '.join(tree['tags'])}")


async def demo_migration_tool():
    """演示配置迁移工具"""
    print("\n" + "="*60)
    print("演示: 配置迁移工具")
    print("="*60)
    
    # 创建迁移工具
    migration_tool = create_example_migrations()
    
    # 初始配置 (v1.0.0)
    config_v1 = {
        "version": "v1.0.0",
        "app": {"name": "Demo App"},
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "demo_db"
        }
    }
    
    print(f"初始配置版本: {config_v1['version']}")
    print(f"数据库主机: {config_v1['database']['host']}")
    
    # 执行迁移 (v1.0.0 -> v2.0.0)
    print("\n🔄 执行迁移: v1.0.0 -> v2.0.0")
    
    migrated_config, migration_record = await migration_tool.migrate(
        config_v1,
        source_version="v1.0.0",
        target_version="v2.0.0",
        dry_run=False
    )
    
    print(f"迁移后版本: {migrated_config['version']}")
    print(f"新增配置项:")
    print(f"  • logging: {'logging' in migrated_config}")
    print(f"  • monitoring: {'monitoring' in migrated_config}")
    print(f"  • security: {'security' in migrated_config}")
    
    # 显示迁移记录
    print(f"\n📝 迁移记录:")
    record_dict = migration_record.to_dict()
    print(f"  迁移ID: {record_dict['migration_id']}")
    print(f"  状态: {record_dict['status']}")
    print(f"  变更数量: {len(record_dict['changes_applied'])}")
    print(f"  耗时: {record_dict['duration']:.2f}秒")
    
    # 执行回滚 (v2.0.0 -> v1.0.0)
    print("\n↩️ 执行回滚: v2.0.0 -> v1.0.0")
    
    rolled_back_config, rollback_record = await migration_tool.rollback(
        migrated_config,
        target_version="v1.0.0"
    )
    
    print(f"回滚后版本: {rolled_back_config['version']}")
    print(f"security配置是否存在: {'security' in rolled_back_config}")
    
    # 显示迁移历史
    print(f"\n📚 迁移历史:")
    history = migration_tool.get_migration_history()
    for record in history:
        print(f"  • {record['source_version']} -> {record['target_version']} "
              f"({record['status']})")
    
    # 显示迁移统计
    stats = migration_tool.get_migration_stats()
    print(f"\n📊 迁移统计:")
    print(f"  总迁移次数: {stats['total_migrations']}")
    print(f"  成功: {stats['successful']}")
    print(f"  失败: {stats['failed']}")
    print(f"  回滚: {stats['rolled_back']}")


def demo_audit_tool():
    """演示配置审计工具"""
    print("\n" + "="*60)
    print("演示: 配置审计工具")
    print("="*60)
    
    # 创建临时目录和版本管理器
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ConfigVersionManager(temp_dir, auto_init=True)
        
        # 创建一些示例版本
        configs = [
            {
                "version": "v1.0.0",
                "app": {"name": "App v1"},
                "database": {"host": "localhost", "password": "secret123"}
            },
            {
                "version": "v1.1.0",
                "app": {"name": "App v1.1"},
                "database": {"host": "localhost", "password": "newsecret456"}
            },
            {
                "version": "v1.2.0",
                "app": {"name": "App v1.2"},
                "database": {"host": "db.example.com", "password": "newsecret456"},
                "timeout": 30
            },
            {
                "version": "v1.3.0",
                "app": {"name": "App v1.3"},
                "database": {"host": "db.example.com"},
                "timeout": 10  # 减少超时时间
            }
        ]
        
        authors = ["admin", "developer", "devops", "admin"]
        comments = [
            "初始版本",
            "更新密码",
            "迁移到云数据库",
            "优化超时设置"
        ]
        
        for i, config in enumerate(configs):
            manager.create_version(
                config,
                version_name=config["version"],
                comment=comments[i],
                author=authors[i]
            )
        
        # 创建审计工具
        audit_tool = ConfigAuditTool(manager)
        
        # 分析变更频率
        print("\n📈 变更频率分析 (最近30天):")
        freq_analysis = audit_tool.analyze_change_frequency(days_back=30)
        
        print(f"  总变更数: {freq_analysis['total_changes']}")
        print(f"  趋势: {freq_analysis['trend']}")
        print(f"  最活跃日期: {freq_analysis['most_active_day']}")
        print(f"  最活跃作者: {freq_analysis['most_active_author']}")
        print(f"  变更类型分布: {freq_analysis['changes_by_type']}")
        
        # 检测高风险变更
        print("\n⚠️ 高风险变更检测:")
        risky_changes = audit_tool.detect_risky_changes()
        
        if risky_changes:
            for rc in risky_changes:
                print(f"  • 版本: {rc['version']}")
                print(f"    风险等级: {rc['risk_level']}")
                print(f"    变更: {rc['change']['path']}")
                print(f"    描述: {rc['description']}")
                print()
        else:
            print("  ✅ 未检测到高风险变更")
        
        # 生成审计报告
        print("\n📄 生成审计报告:")
        report = audit_tool.generate_audit_report(days_back=30)
        
        print(f"  生成时间: {report['generated_at_formatted']}")
        print(f"  分析周期: {report['analysis_period']}")
        print(f"  建议数量: {len(report['recommendations'])}")
        
        if report['recommendations']:
            print("  建议:")
            for rec in report['recommendations']:
                print(f"    • {rec}")


def demo_integration():
    """演示完整集成流程"""
    print("\n" + "="*60)
    print("演示: 完整集成流程")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"工作目录: {temp_dir}")
        
        # 1. 初始化版本管理器
        print("\n1. 📦 初始化版本管理器")
        manager = ConfigVersionManager(temp_dir, auto_init=True)
        
        # 2. 创建初始配置版本
        print("\n2. 🚀 创建初始配置版本")
        base_config = {
            "version": "v1.0.0",
            "application": {
                "name": "DeerFlow Agent System",
                "environment": "production",
                "debug": False
            },
            "services": {
                "api": {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "workers": 4
                },
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "deerflow_prod",
                    "user": "deerflow_user"
                }
            }
        }
        
        v1 = manager.create_version(
            base_config,
            version_name="v1.0.0",
            comment="生产环境初始配置",
            author="deployer",
            tags=["production", "initial"]
        )
        
        # 3. 创建更新版本
        print("\n3. 🔄 创建更新版本")
        updated_config = base_config.copy()
        updated_config["version"] = "v1.1.0"
        updated_config["services"]["cache"] = {
            "enabled": True,
            "redis_host": "redis.local",
            "redis_port": 6379
        }
        updated_config["services"]["api"]["timeout"] = 30
        
        v2 = manager.create_version(
            updated_config,
            version_name="v1.1.0",
            comment="添加缓存支持和API超时",
            author="architect",
            tags=["production", "enhancement"]
        )
        
        # 4. 比较版本差异
        print("\n4. 🔍 比较版本差异")
        changes = manager.compare_versions("v1.0.0", "v1.1.0")
        
        print(f"  发现 {len(changes)} 个变更:")
        for change in changes[:3]:  # 只显示前3个
            print(f"    • {change.change_type.value}: {change.path}")
        
        # 5. 创建迁移工具
        print("\n5. 🛠️ 创建迁移工具")
        migration_tool = create_example_migrations()
        
        # 6. 模拟迁移
        print("\n6. 🚚 模拟配置迁移")
        
        async def run_migration():
            migrated_config, record = await migration_tool.migrate(
                base_config,
                source_version="v1.0.0",
                target_version="v2.0.0",
                dry_run=True
            )
            
            print(f"  迁移状态: {record.status.value}")
            print(f"  应用变更数: {len(record.changes_applied)}")
            print(f"  新版本: {migrated_config.get('version')}")
            print(f"  新增安全配置: {'security' in migrated_config}")
        
        asyncio.run(run_migration())
        
        # 7. 创建审计工具
        print("\n7. 📊 创建审计工具")
        audit_tool = ConfigAuditTool(manager)
        
        # 8. 生成审计报告
        print("\n8. 📄 生成审计报告")
        report = audit_tool.generate_audit_report(days_back=7)
        
        print(f"  总变更数: {report['change_frequency']['total_changes']}")
        print(f"  高风险变更: {len(report['risky_changes'])}")
        print(f"  建议: {len(report['recommendations'])}")
        
        # 9. 演示回滚
        print("\n9. ↩️ 演示版本回滚")
        rollback_version = manager.rollback_to_version("v1.0.0")
        
        print(f"  回滚版本: {rollback_version.version_name}")
        print(f"  回滚注释: {rollback_version.comment[:50]}...")
        
        # 10. 总结
        print("\n10. ✅ 集成流程完成")
        versions = manager.list_versions()
        print(f"  总版本数: {len(versions)}")
        print(f"  最新版本: {versions[0].version_name if versions else '无'}")
        print(f"  所有标签: {', '.join(set(tag for v in versions for tag in v.tags))}")


# ============================================================================
# 测试函数
# ============================================================================

def run_tests():
    """运行测试"""
    print("\n" + "="*60)
    print("测试: 配置版本控制功能")
    print("="*60)
    
    test_results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    def assert_test(condition: bool, name: str, message: str = ""):
        """断言测试"""
        if condition:
            test_results["passed"] += 1
            test_results["tests"].append({"name": name, "status": "✅", "message": message})
            print(f"  ✅ {name}: {message}")
        else:
            test_results["failed"] += 1
            test_results["tests"].append({"name": name, "status": "❌", "message": message})
            print(f"  ❌ {name}: {message}")
    
    # 测试1: 配置差异计算
    print("\n1. 测试配置差异计算")
    dict1 = {"a": 1, "b": {"c": 2}}
    dict2 = {"a": 2, "b": {"c": 3}, "d": 4}
    
    changes = ConfigDiffCalculator.compare_dicts(dict1, dict2)
    assert_test(len(changes) == 3, "差异检测", f"检测到 {len(changes)} 个变更")
    
    change_types = {c.change_type for c in changes}
    assert_test(VersionChangeType.MODIFIED in change_types, "修改检测")
    assert_test(VersionChangeType.ADDED in change_types, "添加检测")
    
    # 测试2: 版本管理器基础功能
    print("\n2. 测试版本管理器基础功能")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ConfigVersionManager(temp_dir, auto_init=True)
        
        # 创建版本
        config = {"test": "data", "version": "v1.0.0"}
        version = manager.create_version(config, "v1.0.0", "测试版本")
        assert_test(version is not None, "版本创建")
        assert_test(version.version_name == "v1.0.0", "版本名称")
        
        # 获取版本
        retrieved = manager.get_version("v1.0.0")
        assert_test(retrieved is not None, "版本获取")
        assert_test(retrieved.config_data["test"] == "data", "配置数据")
        
        # 列出版本
        versions = manager.list_versions()
        assert_test(len(versions) >= 1, "版本列表", f"找到 {len(versions)} 个版本")
        
        # 比较版本
        changes = manager.compare_versions("HEAD~1", "HEAD")
        assert_test(isinstance(changes, list), "版本比较")
    
    # 测试3: 迁移工具
    print("\n3. 测试迁移工具")
    
    migration_tool = create_example_migrations()
    assert_test(len(migration_tool.migrations) == 3, "迁移函数注册", f"注册了 {len(migration_tool.migrations)} 个迁移")
    
    # 测试4: 审计工具
    print("\n4. 测试审计工具")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = ConfigVersionManager(temp_dir, auto_init=True)
        audit_tool = ConfigAuditTool(manager)
        
        report = audit_tool.generate_audit_report(days_back=7)
        assert_test(isinstance(report, dict), "审计报告生成")
        assert_test("change_frequency" in report, "变更频率分析")
        assert_test("risky_changes" in report, "高风险变更检测")
    
    # 测试结果汇总
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    print(f"✅ 通过: {test_results['passed']}")
    print(f"❌ 失败: {test_results['failed']}")
    print(f"📊 总计: {test_results['passed'] + test_results['failed']}")
    
    if test_results['failed'] == 0:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  {test_results['failed']} 个测试失败")
    
    return test_results


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("🦌 DeerFlow Agent 配置版本控制演示")
    print("="*60)
    
    # 检查依赖
    if not GIT_AVAILABLE:
        print("⚠️  警告: gitpython未安装，部分功能受限")
        print("   安装命令: pip install gitpython")
        print("   继续演示基础功能...")
    
    # 运行演示
    try:
        # 演示基础版本控制
        demo_basic_version_control()
        
        # 演示迁移工具
        asyncio.run(demo_migration_tool())
        
        # 演示审计工具
        demo_audit_tool()
        
        # 演示完整集成
        demo_integration()
        
        # 运行测试
        test_results = run_tests()
        
        # 总结
        print("\n" + "="*60)
        print("演示完成!")
        print("="*60)
        print("\n🎓 学习要点总结:")
        print("  1. 基于Git的配置版本管理实现")
        print("  2. 配置差异比较算法和变更检测")
        print("  3. 配置迁移工具和版本升级/回滚")
        print("  4. 配置审计和风险分析")
        print("  5. 完整的配置版本控制工作流")
        
        if test_results['failed'] > 0:
            print(f"\n⚠️  注意: {test_results['failed']} 个测试失败，请检查实现")
        else:
            print("\n✅ 所有功能正常，测试全部通过!")
        
        print("\n📚 下一步:")
        print("  • 在实际项目中应用配置版本控制")
        print("  • 集成到CI/CD流水线")
        print("  • 实现配置版本可视化界面")
        print("  • 研究分布式配置版本管理")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行主函数
    sys.exit(main())