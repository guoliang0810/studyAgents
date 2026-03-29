#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沙箱与技能配置演示代码 - DeerFlow Python Agent 架构师训练营
第60节课：沙箱与技能配置

本模块演示现代AI Agent系统中的沙箱和技能配置管理，包括：
1. 沙箱配置架构：提供者配置、资源限制、环境变量等多层结构设计
2. 技能配置体系：版本管理、依赖管理、启用状态、配置参数等完整设计
3. 安全配置原则：资源限制、网络隔离、权限控制等安全策略实现
4. 配置继承机制：默认配置与具体提供者配置的继承和覆盖关系

使用说明：
1. 直接运行：python sandbox_skill_config_demo.py
2. 运行测试：python sandbox_skill_config_demo.py --test
3. 查看帮助：python sandbox_skill_config_demo.py --help
"""

import os
import sys
import json
import yaml
import asyncio
import argparse
import copy
import re
import time
import hashlib
import inspect
from typing import Any, Dict, List, Optional, Union, Callable, Set, Tuple, Type
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
import logging
from abc import ABC, abstractmethod
import importlib.util
import importlib.machinery
from contextlib import contextmanager
import subprocess
import tempfile
import shutil
import random
import string
import uuid

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SandboxConfigError(Exception):
    """沙箱配置错误基类"""
    pass


class SkillConfigError(Exception):
    """技能配置错误基类"""
    pass


class SecurityConfigError(Exception):
    """安全配置错误基类"""
    pass


class ConfigValidationError(Exception):
    """配置验证错误"""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"配置验证失败: {errors}")


# ============================================================================
# 枚举定义
# ============================================================================

class SandboxProviderType(Enum):
    """沙箱提供者类型枚举"""
    LOCAL = "local"          # 本地进程沙箱（开发环境）
    AIO = "aio"             # 异步I/O沙箱（生产环境）
    DOCKER = "docker"       # Docker容器沙箱（隔离环境）
    WEBASSEMBLY = "wasm"    # WebAssembly沙箱（高安全环境）
    VM = "vm"              # 虚拟机沙箱（完全隔离环境）
    
    @classmethod
    def from_string(cls, value: str) -> 'SandboxProviderType':
        """从字符串转换为枚举"""
        value_lower = value.lower()
        for member in cls:
            if member.value == value_lower:
                return member
        raise ValueError(f"未知的沙箱提供者类型: {value}")


class SecurityLevel(Enum):
    """安全级别枚举"""
    TRUSTED = "trusted"      # 信任级别：完全信任，无限制
    RESTRICTED = "restricted"  # 限制级别：有限制的操作
    SANDBOXED = "sandboxed"   # 沙箱级别：完全隔离，高度限制
    UNTRUSTED = "untrusted"   # 不信任级别：禁止执行
    
    @classmethod
    def from_string(cls, value: str) -> 'SecurityLevel':
        """从字符串转换为枚举"""
        value_lower = value.lower()
        for member in cls:
            if member.value == value_lower:
                return member
        raise ValueError(f"未知的安全级别: {value}")


class SkillType(Enum):
    """技能类型枚举"""
    CALCULATOR = "calculator"        # 计算器技能：数学计算、统计
    FILE_CONVERTER = "file_converter" # 文件转换技能：格式转换
    WEB_SCRAPER = "web_scraper"      # 网络爬虫技能：数据抓取
    DATABASE = "database"           # 数据库技能：数据查询
    API_CLIENT = "api_client"       # API客户端技能：外部服务调用
    ML_MODEL = "ml_model"           # 机器学习技能：模型推理
    TEXT_PROCESSOR = "text_processor" # 文本处理技能：NLP处理
    IMAGE_PROCESSOR = "image_processor" # 图像处理技能：图像分析
    
    @classmethod
    def from_string(cls, value: str) -> 'SkillType':
        """从字符串转换为枚举"""
        value_lower = value.lower()
        for member in cls:
            if member.value == value_lower:
                return member
        raise ValueError(f"未知的技能类型: {value}")


class SkillStatus(Enum):
    """技能状态枚举"""
    ENABLED = "enabled"      # 已启用：可以正常使用
    DISABLED = "disabled"    # 已禁用：配置存在但不可用
    PENDING = "pending"      # 等待中：等待依赖或条件满足
    DEPRECATED = "deprecated" # 已弃用：不推荐使用，未来会移除
    
    @classmethod
    def from_string(cls, value: str) -> 'SkillStatus':
        """从字符串转换为枚举"""
        value_lower = value.lower()
        for member in cls:
            if member.value == value_lower:
                return member
        raise ValueError(f"未知的技能状态: {value}")


# ============================================================================
# 安全配置类
# ============================================================================

@dataclass
class SecurityConfig:
    """安全配置类"""
    security_level: SecurityLevel = SecurityLevel.RESTRICTED
    cpu_limit_percent: Optional[float] = None           # CPU限制百分比
    memory_limit_mb: Optional[float] = None            # 内存限制(MB)
    disk_limit_mb: Optional[float] = None              # 磁盘限制(MB)
    network_access: bool = False                       # 是否允许网络访问
    network_whitelist: List[str] = field(default_factory=list)  # 网络白名单
    network_blacklist: List[str] = field(default_factory=list)  # 网络黑名单
    file_system_access: bool = True                    # 是否允许文件系统访问
    read_only_paths: List[str] = field(default_factory=list)   # 只读路径列表
    writable_paths: List[str] = field(default_factory=list)    # 可写路径列表
    environment_variables_whitelist: List[str] = field(default_factory=list)  # 环境变量白名单
    max_execution_time_seconds: Optional[float] = None  # 最大执行时间（秒）
    max_process_count: Optional[int] = None            # 最大进程数
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "security_level": self.security_level.value,
            "cpu_limit_percent": self.cpu_limit_percent,
            "memory_limit_mb": self.memory_limit_mb,
            "disk_limit_mb": self.disk_limit_mb,
            "network_access": self.network_access,
            "network_whitelist": self.network_whitelist,
            "network_blacklist": self.network_blacklist,
            "file_system_access": self.file_system_access,
            "read_only_paths": self.read_only_paths,
            "writable_paths": self.writable_paths,
            "environment_variables_whitelist": self.environment_variables_whitelist,
            "max_execution_time_seconds": self.max_execution_time_seconds,
            "max_process_count": self.max_process_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecurityConfig':
        """从字典创建"""
        security_level = SecurityLevel.from_string(data.get("security_level", "restricted"))
        return cls(
            security_level=security_level,
            cpu_limit_percent=data.get("cpu_limit_percent"),
            memory_limit_mb=data.get("memory_limit_mb"),
            disk_limit_mb=data.get("disk_limit_mb"),
            network_access=data.get("network_access", False),
            network_whitelist=data.get("network_whitelist", []),
            network_blacklist=data.get("network_blacklist", []),
            file_system_access=data.get("file_system_access", True),
            read_only_paths=data.get("read_only_paths", []),
            writable_paths=data.get("writable_paths", []),
            environment_variables_whitelist=data.get("environment_variables_whitelist", []),
            max_execution_time_seconds=data.get("max_execution_time_seconds"),
            max_process_count=data.get("max_process_count"),
        )
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if self.cpu_limit_percent is not None:
            if not 0 < self.cpu_limit_percent <= 100:
                errors.append(f"CPU限制百分比必须在0-100之间，当前值: {self.cpu_limit_percent}")
        
        if self.memory_limit_mb is not None:
            if self.memory_limit_mb <= 0:
                errors.append(f"内存限制必须大于0，当前值: {self.memory_limit_mb}")
        
        if self.disk_limit_mb is not None:
            if self.disk_limit_mb <= 0:
                errors.append(f"磁盘限制必须大于0，当前值: {self.disk_limit_mb}")
        
        if self.max_execution_time_seconds is not None:
            if self.max_execution_time_seconds <= 0:
                errors.append(f"最大执行时间必须大于0，当前值: {self.max_execution_time_seconds}")
        
        if self.max_process_count is not None:
            if self.max_process_count <= 0:
                errors.append(f"最大进程数必须大于0，当前值: {self.max_process_count}")
        
        # 检查安全级别与配置的一致性
        if self.security_level == SecurityLevel.TRUSTED:
            if self.cpu_limit_percent is not None or self.memory_limit_mb is not None:
                errors.append("信任级别不应设置资源限制")
        
        elif self.security_level == SecurityLevel.SANDBOXED:
            if not self.network_access and self.network_whitelist:
                errors.append("沙箱级别不允许网络访问，不应设置网络白名单")
        
        return errors
    
    def is_network_allowed(self, host: str) -> bool:
        """检查是否允许访问指定主机"""
        if not self.network_access:
            return False
        
        # 检查黑名单
        for pattern in self.network_blacklist:
            if re.match(pattern, host):
                return False
        
        # 检查白名单
        if self.network_whitelist:
            for pattern in self.network_whitelist:
                if re.match(pattern, host):
                    return True
            return False
        
        return True  # 如果有网络访问权限且无白名单限制，则允许所有


# ============================================================================
# 沙箱提供者配置
# ============================================================================

@dataclass
class SandboxProviderConfig:
    """沙箱提供者配置基类"""
    provider_type: SandboxProviderType
    name: str
    description: str = ""
    enabled: bool = True
    security_config: Optional[SecurityConfig] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "provider_type": self.provider_type.value,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "security_config": self.security_config.to_dict() if self.security_config else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SandboxProviderConfig':
        """从字典创建"""
        provider_type = SandboxProviderType.from_string(data["provider_type"])
        security_data = data.get("security_config")
        security_config = SecurityConfig.from_dict(security_data) if security_data else None
        
        return cls(
            provider_type=provider_type,
            name=data["name"],
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            security_config=security_config,
        )
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if not self.name.strip():
            errors.append("提供者名称不能为空")
        
        if self.security_config:
            errors.extend(self.security_config.validate())
        
        return errors


@dataclass
class LocalProviderConfig(SandboxProviderConfig):
    """本地提供者配置"""
    work_dir: Optional[str] = None
    python_path: Optional[str] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "work_dir": self.work_dir,
            "python_path": self.python_path,
            "environment_variables": self.environment_variables,
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LocalProviderConfig':
        """从字典创建"""
        base_config = super().from_dict(data)
        
        return cls(
            provider_type=base_config.provider_type,
            name=base_config.name,
            description=base_config.description,
            enabled=base_config.enabled,
            security_config=base_config.security_config,
            work_dir=data.get("work_dir"),
            python_path=data.get("python_path"),
            environment_variables=data.get("environment_variables", {}),
        )


@dataclass
class DockerProviderConfig(SandboxProviderConfig):
    """Docker提供者配置"""
    image: str
    tag: str = "latest"
    volumes: List[Dict[str, str]] = field(default_factory=list)
    ports: List[Dict[str, Any]] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    network_mode: str = "bridge"
    privileged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "image": self.image,
            "tag": self.tag,
            "volumes": self.volumes,
            "ports": self.ports,
            "environment_variables": self.environment_variables,
            "network_mode": self.network_mode,
            "privileged": self.privileged,
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DockerProviderConfig':
        """从字典创建"""
        base_config = super().from_dict(data)
        
        return cls(
            provider_type=base_config.provider_type,
            name=base_config.name,
            description=base_config.description,
            enabled=base_config.enabled,
            security_config=base_config.security_config,
            image=data["image"],
            tag=data.get("tag", "latest"),
            volumes=data.get("volumes", []),
            ports=data.get("ports", []),
            environment_variables=data.get("environment_variables", {}),
            network_mode=data.get("network_mode", "bridge"),
            privileged=data.get("privileged", False),
        )
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = super().validate()
        
        if not self.image.strip():
            errors.append("Docker镜像名称不能为空")
        
        if self.privileged and self.security_config and self.security_config.security_level != SecurityLevel.TRUSTED:
            errors.append("特权模式只能用于信任级别的安全配置")
        
        return errors


@dataclass
class AIOProviderConfig(SandboxProviderConfig):
    """异步I/O提供者配置"""
    max_concurrent_tasks: int = 10
    task_timeout_seconds: float = 30.0
    retry_count: int = 3
    retry_delay_seconds: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "task_timeout_seconds": self.task_timeout_seconds,
            "retry_count": self.retry_count,
            "retry_delay_seconds": self.retry_delay_seconds,
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIOProviderConfig':
        """从字典创建"""
        base_config = super().from_dict(data)
        
        return cls(
            provider_type=base_config.provider_type,
            name=base_config.name,
            description=base_config.description,
            enabled=base_config.enabled,
            security_config=base_config.security_config,
            max_concurrent_tasks=data.get("max_concurrent_tasks", 10),
            task_timeout_seconds=data.get("task_timeout_seconds", 30.0),
            retry_count=data.get("retry_count", 3),
            retry_delay_seconds=data.get("retry_delay_seconds", 1.0),
        )
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = super().validate()
        
        if self.max_concurrent_tasks <= 0:
            errors.append(f"最大并发任务数必须大于0，当前值: {self.max_concurrent_tasks}")
        
        if self.task_timeout_seconds <= 0:
            errors.append(f"任务超时时间必须大于0，当前值: {self.task_timeout_seconds}")
        
        if self.retry_count < 0:
            errors.append(f"重试次数必须大于等于0，当前值: {self.retry_count}")
        
        if self.retry_delay_seconds < 0:
            errors.append(f"重试延迟必须大于等于0，当前值: {self.retry_delay_seconds}")
        
        return errors


# ============================================================================
# 沙箱配置
# ============================================================================

@dataclass
class SandboxConfig:
    """沙箱配置类"""
    default_provider: str = "local"  # 默认提供者名称
    providers: Dict[str, SandboxProviderConfig] = field(default_factory=dict)
    security_config: Optional[SecurityConfig] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "default_provider": self.default_provider,
            "providers": {name: provider.to_dict() for name, provider in self.providers.items()},
            "security_config": self.security_config.to_dict() if self.security_config else None,
            "environment_variables": self.environment_variables,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SandboxConfig':
        """从字典创建"""
        providers = {}
        providers_data = data.get("providers", {})
        
        for name, provider_data in providers_data.items():
            provider_type = SandboxProviderType.from_string(provider_data["provider_type"])
            
            if provider_type == SandboxProviderType.LOCAL:
                providers[name] = LocalProviderConfig.from_dict(provider_data)
            elif provider_type == SandboxProviderType.DOCKER:
                providers[name] = DockerProviderConfig.from_dict(provider_data)
            elif provider_type == SandboxProviderType.AIO:
                providers[name] = AIOProviderConfig.from_dict(provider_data)
            else:
                providers[name] = SandboxProviderConfig.from_dict(provider_data)
        
        security_data = data.get("security_config")
        security_config = SecurityConfig.from_dict(security_data) if security_data else None
        
        return cls(
            default_provider=data.get("default_provider", "local"),
            providers=providers,
            security_config=security_config,
            environment_variables=data.get("environment_variables", {}),
            metadata=data.get("metadata", {}),
        )
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        # 检查默认提供者是否存在
        if self.default_provider not in self.providers:
            errors.append(f"默认提供者 '{self.default_provider}' 不存在")
        
        # 检查默认提供者是否启用
        if self.default_provider in self.providers and not self.providers[self.default_provider].enabled:
            errors.append(f"默认提供者 '{self.default_provider}' 未启用")
        
        # 验证所有提供者配置
        for name, provider in self.providers.items():
            provider_errors = provider.validate()
            if provider_errors:
                errors.extend([f"提供者 '{name}': {error}" for error in provider_errors])
        
        # 验证安全配置
        if self.security_config:
            errors.extend(self.security_config.validate())
        
        return errors
    
    def get_provider(self, name: Optional[str] = None) -> Optional[SandboxProviderConfig]:
        """获取提供者配置"""
        provider_name = name or self.default_provider
        return self.providers.get(provider_name)
    
    def resolve_environment_variables(self, env_vars: Dict[str, str]) -> 'SandboxConfig':
        """解析环境变量"""
        resolved_config = copy.deepcopy(self)
        
        # 解析沙箱级别的环境变量
        for key, value in resolved_config.environment_variables.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                var_name = value[2:-1]
                if var_name in env_vars:
                    resolved_config.environment_variables[key] = env_vars[var_name]
        
        # 解析提供者级别的环境变量
        for provider_name, provider in resolved_config.providers.items():
            if hasattr(provider, 'environment_variables'):
                for key, value in provider.environment_variables.items():
                    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                        var_name = value[2:-1]
                        if var_name in env_vars:
                            provider.environment_variables[key] = env_vars[var_name]
        
        return resolved_config


# ============================================================================
# 技能依赖
# ============================================================================

@dataclass
class SkillDependency:
    """技能依赖类"""
    skill_id: str
    version_constraint: Optional[str] = None  # 版本约束，如 ">=1.0.0", "^2.0.0"
    required: bool = True                    # 是否必需依赖
    description: str = ""                    # 依赖描述
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "skill_id": self.skill_id,
            "version_constraint": self.version_constraint,
            "required": self.required,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillDependency':
        """从字典创建"""
        return cls(
            skill_id=data["skill_id"],
            version_constraint=data.get("version_constraint"),
            required=data.get("required", True),
            description=data.get("description", ""),
        )
    
    def is_version_satisfied(self, version: str) -> bool:
        """检查版本是否满足约束"""
        if not self.version_constraint:
            return True
        
        # 简单的版本约束检查（实际实现需要更复杂的语义化版本解析）
        constraint = self.version_constraint.strip()
        if constraint.startswith(">="):
            required_version = constraint[2:].strip()
            return self._compare_versions(version, required_version) >= 0
        elif constraint.startswith("<="):
            required_version = constraint[2:].strip()
            return self._compare_versions(version, required_version) <= 0
        elif constraint.startswith(">"):
            required_version = constraint[1:].strip()
            return self._compare_versions(version, required_version) > 0
        elif constraint.startswith("<"):
            required_version = constraint[1:].strip()
            return self._compare_versions(version, required_version) < 0
        elif constraint.startswith("^"):
            required_version = constraint[1:].strip()
            return self._is_compatible_version(version, required_version)
        elif constraint.startswith("~"):
            required_version = constraint[1:].strip()
            return self._is_tilde_compatible(version, required_version)
        elif constraint.startswith("=="):
            required_version = constraint[2:].strip()
            return version == required_version
        else:
            # 默认使用 ==
            return version == constraint
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较版本号"""
        v1_parts = [int(part) for part in v1.split('.')]
        v2_parts = [int(part) for part in v2.split('.')]
        
        # 填充到相同长度
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for i in range(max_len):
            if v1_parts[i] > v2_parts[i]:
                return 1
            elif v1_parts[i] < v2_parts[i]:
                return -1
        
        return 0
    
    def _is_compatible_version(self, version: str, required: str) -> bool:
        """检查是否为兼容版本（语义化版本 ^）"""
        if not version or not required:
            return False
        
        version_parts = version.split('.')
        required_parts = required.split('.')
        
        # ^1.2.3 允许 1.x.x 但不允许 2.x.x
        if version_parts[0] != required_parts[0]:
            return False
        
        # 如果主版本号为0，则次版本号不能变（如 ^0.1.2 允许 0.1.x 但不允许 0.2.x）
        if required_parts[0] == '0' and len(required_parts) > 1:
            if len(version_parts) > 1 and version_parts[1] != required_parts[1]:
                return False
        
        return True
    
    def _is_tilde_compatible(self, version: str, required: str) -> bool:
        """检查是否为波浪号兼容版本（如 ~1.2.3 允许 1.2.x）"""
        version_parts = version.split('.')
        required_parts = required.split('.')
        
        min_len = min(len(version_parts), len(required_parts))
        
        for i in range(min_len):
            if i == min_len - 1:
                # 最后一位允许大于等于
                return int(version_parts[i]) >= int(required_parts[i])
            elif version_parts[i] != required_parts[i]:
                return False
        
        return True


# ============================================================================
# 技能配置
# ============================================================================

@dataclass
class SkillConfig:
    """技能配置类"""
    skill_id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    skill_type: SkillType = SkillType.CALCULATOR
    status: SkillStatus = SkillStatus.ENABLED
    author: str = ""
    license: str = "MIT"
    tags: List[str] = field(default_factory=list)
    dependencies: List[SkillDependency] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    sandbox_provider: Optional[str] = None  # 指定沙箱提供者
    security_config: Optional[SecurityConfig] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "skill_type": self.skill_type.value,
            "status": self.status.value,
            "author": self.author,
            "license": self.license,
            "tags": self.tags,
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "parameters": self.parameters,
            "sandbox_provider": self.sandbox_provider,
            "security_config": self.security_config.to_dict() if self.security_config else None,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillConfig':
        """从字典创建"""
        skill_type = SkillType.from_string(data.get("skill_type", "calculator"))
        status = SkillStatus.from_string(data.get("status", "enabled"))
        
        dependencies_data = data.get("dependencies", [])
        dependencies = [SkillDependency.from_dict(dep) for dep in dependencies_data]
        
        security_data = data.get("security_config")
        security_config = SecurityConfig.from_dict(security_data) if security_data else None
        
        return cls(
            skill_id=data["skill_id"],
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            skill_type=skill_type,
            status=status,
            author=data.get("author", ""),
            license=data.get("license", "MIT"),
            tags=data.get("tags", []),
            dependencies=dependencies,
            parameters=data.get("parameters", {}),
            sandbox_provider=data.get("sandbox_provider"),
            security_config=security_config,
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if not self.skill_id.strip():
            errors.append("技能ID不能为空")
        
        if not self.name.strip():
            errors.append("技能名称不能为空")
        
        if not re.match(r'^\d+\.\d+\.\d+$', self.version):
            errors.append(f"版本号格式不正确，应为X.Y.Z格式，当前值: {self.version}")
        
        if self.status == SkillStatus.ENABLED:
            # 检查必需依赖是否都有版本约束
            for dep in self.dependencies:
                if dep.required and not dep.version_constraint:
                    errors.append(f"必需依赖 '{dep.skill_id}' 缺少版本约束")
        
        if self.security_config:
            errors.extend(self.security_config.validate())
        
        return errors
    
    def get_required_dependencies(self) -> List[SkillDependency]:
        """获取必需依赖"""
        return [dep for dep in self.dependencies if dep.required]
    
    def get_optional_dependencies(self) -> List[SkillDependency]:
        """获取可选依赖"""
        return [dep for dep in self.dependencies if not dep.required]
    
    def has_dependency(self, skill_id: str) -> bool:
        """检查是否有指定依赖"""
        return any(dep.skill_id == skill_id for dep in self.dependencies)
    
    def add_dependency(self, dependency: SkillDependency):
        """添加依赖"""
        if not self.has_dependency(dependency.skill_id):
            self.dependencies.append(dependency)
    
    def remove_dependency(self, skill_id: str):
        """移除依赖"""
        self.dependencies = [dep for dep in self.dependencies if dep.skill_id != skill_id]


# ============================================================================
# 技能系统配置
# ============================================================================

@dataclass
class SkillSystemConfig:
    """技能系统配置类"""
    default_sandbox_provider: str = "local"
    sandbox_config: Optional[SandboxConfig] = None
    skills: Dict[str, SkillConfig] = field(default_factory=dict)
    auto_resolve_dependencies: bool = True
    enable_version_check: bool = True
    enable_security_check: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "default_sandbox_provider": self.default_sandbox_provider,
            "sandbox_config": self.sandbox_config.to_dict() if self.sandbox_config else None,
            "skills": {skill_id: skill.to_dict() for skill_id, skill in self.skills.items()},
            "auto_resolve_dependencies": self.auto_resolve_dependencies,
            "enable_version_check": self.enable_version_check,
            "enable_security_check": self.enable_security_check,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillSystemConfig':
        """从字典创建"""
        sandbox_data = data.get("sandbox_config")
        sandbox_config = SandboxConfig.from_dict(sandbox_data) if sandbox_data else None
        
        skills_data = data.get("skills", {})
        skills = {skill_id: SkillConfig.from_dict(skill_data) for skill_id, skill_data in skills_data.items()}
        
        return cls(
            default_sandbox_provider=data.get("default_sandbox_provider", "local"),
            sandbox_config=sandbox_config,
            skills=skills,
            auto_resolve_dependencies=data.get("auto_resolve_dependencies", True),
            enable_version_check=data.get("enable_version_check", True),
            enable_security_check=data.get("enable_security_check", True),
            metadata=data.get("metadata", {}),
        )
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if self.sandbox_config:
            # 验证默认沙箱提供者是否存在
            if self.default_sandbox_provider not in self.sandbox_config.providers:
                errors.append(f"默认沙箱提供者 '{self.default_sandbox_provider}' 不存在")
            
            errors.extend(self.sandbox_config.validate())
        
        # 验证所有技能配置
        for skill_id, skill in self.skills.items():
            skill_errors = skill.validate()
            if skill_errors:
                errors.extend([f"技能 '{skill_id}': {error}" for error in skill_errors])
        
        # 检查技能依赖是否存在
        for skill_id, skill in self.skills.items():
            for dep in skill.dependencies:
                if dep.skill_id not in self.skills and dep.required:
                    errors.append(f"技能 '{skill_id}' 的必需依赖 '{dep.skill_id}' 不存在")
        
        # 检查循环依赖
        try:
            self._detect_circular_dependencies()
        except SkillConfigError as e:
            errors.append(str(e))
        
        return errors
    
    def _detect_circular_dependencies(self):
        """检测循环依赖"""
        graph = {}
        for skill_id, skill in self.skills.items():
            graph[skill_id] = [dep.skill_id for dep in skill.dependencies if dep.required]
        
        visited = set()
        recursion_stack = set()
        
        def dfs(node: str) -> bool:
            if node in recursion_stack:
                return True  # 发现循环
            if node in visited:
                return False
            
            visited.add(node)
            recursion_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor in graph and dfs(neighbor):
                    return True
            
            recursion_stack.remove(node)
            return False
        
        for node in graph:
            if dfs(node):
                raise SkillConfigError(f"检测到循环依赖")
    
    def get_skill(self, skill_id: str) -> Optional[SkillConfig]:
        """获取技能配置"""
        return self.skills.get(skill_id)
    
    def add_skill(self, skill: SkillConfig):
        """添加技能"""
        self.skills[skill.skill_id] = skill
    
    def remove_skill(self, skill_id: str):
        """移除技能"""
        if skill_id in self.skills:
            del self.skills[skill_id]
    
    def get_dependency_order(self) -> List[str]:
        """获取依赖顺序（拓扑排序）"""
        graph = {}
        for skill_id, skill in self.skills.items():
            graph[skill_id] = [dep.skill_id for dep in skill.dependencies if dep.required]
        
        # Kahn算法拓扑排序
        indegree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                indegree[neighbor] = indegree.get(neighbor, 0) + 1
        
        queue = [node for node in graph if indegree[node] == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            for neighbor in graph.get(node, []):
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(graph):
            raise SkillConfigError("存在循环依赖，无法确定依赖顺序")
        
        return result


# ============================================================================
# 配置加载器
# ============================================================================

class SandboxSkillConfigLoader:
    """沙箱和技能配置加载器"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = config_dir
        self.sandbox_config: Optional[SandboxConfig] = None
        self.skill_system_config: Optional[SkillSystemConfig] = None
        self.loaded_at: Optional[float] = None
    
    async def load_from_yaml(self, sandbox_yaml: str, skills_yaml: str, env_vars: Optional[Dict[str, str]] = None) -> None:
        """从YAML文件加载配置"""
        env_vars = env_vars or {}
        
        # 加载沙箱配置
        sandbox_path = self._resolve_path(sandbox_yaml)
        with open(sandbox_path, 'r', encoding='utf-8') as f:
            sandbox_data = yaml.safe_load(f)
        
        self.sandbox_config = SandboxConfig.from_dict(sandbox_data)
        
        # 解析环境变量
        if env_vars:
            self.sandbox_config = self.sandbox_config.resolve_environment_variables(env_vars)
        
        # 加载技能系统配置
        skills_path = self._resolve_path(skills_yaml)
        with open(skills_path, 'r', encoding='utf-8') as f:
            skills_data = yaml.safe_load(f)
        
        self.skill_system_config = SkillSystemConfig.from_dict(skills_data)
        
        # 设置沙箱配置
        if self.skill_system_config and self.sandbox_config:
            self.skill_system_config.sandbox_config = self.sandbox_config
        
        self.loaded_at = time.time()
        logger.info(f"配置加载完成: 沙箱提供者={len(self.sandbox_config.providers)}, 技能={len(self.skill_system_config.skills)}")
    
    async def load_from_dict(self, sandbox_data: Dict[str, Any], skills_data: Dict[str, Any], env_vars: Optional[Dict[str, str]] = None) -> None:
        """从字典加载配置"""
        env_vars = env_vars or {}
        
        self.sandbox_config = SandboxConfig.from_dict(sandbox_data)
        
        if env_vars:
            self.sandbox_config = self.sandbox_config.resolve_environment_variables(env_vars)
        
        self.skill_system_config = SkillSystemConfig.from_dict(skills_data)
        
        if self.skill_system_config and self.sandbox_config:
            self.skill_system_config.sandbox_config = self.sandbox_config
        
        self.loaded_at = time.time()
        logger.info(f"配置加载完成: 沙箱提供者={len(self.sandbox_config.providers)}, 技能={len(self.skill_system_config.skills)}")
    
    def _resolve_path(self, path: str) -> str:
        """解析路径"""
        if os.path.isabs(path):
            return path
        elif self.config_dir:
            return os.path.join(self.config_dir, path)
        else:
            return path
    
    def validate_all(self) -> List[str]:
        """验证所有配置"""
        errors = []
        
        if not self.sandbox_config:
            errors.append("沙箱配置未加载")
        else:
            errors.extend(self.sandbox_config.validate())
        
        if not self.skill_system_config:
            errors.append("技能系统配置未加载")
        else:
            errors.extend(self.skill_system_config.validate())
        
        return errors
    
    def get_sandbox_provider(self, provider_name: Optional[str] = None) -> Optional[SandboxProviderConfig]:
        """获取沙箱提供者配置"""
        if not self.sandbox_config:
            return None
        
        if not provider_name and self.skill_system_config:
            provider_name = self.skill_system_config.default_sandbox_provider
        
        return self.sandbox_config.get_provider(provider_name)
    
    def get_skill_with_dependencies(self, skill_id: str) -> Dict[str, Any]:
        """获取技能及其所有依赖"""
        if not self.skill_system_config:
            return {}
        
        skill = self.skill_system_config.get_skill(skill_id)
        if not skill:
            return {}
        
        result = {
            "skill": skill.to_dict(),
            "dependencies": []
        }
        
        visited = set()
        queue = [skill_id]
        
        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            
            visited.add(current_id)
            current_skill = self.skill_system_config.get_skill(current_id)
            if not current_skill:
                continue
            
            for dep in current_skill.dependencies:
                if dep.skill_id not in visited:
                    queue.append(dep.skill_id)
                    dep_skill = self.skill_system_config.get_skill(dep.skill_id)
                    if dep_skill:
                        result["dependencies"].append({
                            "skill": dep_skill.to_dict(),
                            "relationship": "required" if dep.required else "optional",
                            "version_constraint": dep.version_constraint
                        })
        
        return result
    
    def to_yaml_files(self, sandbox_output: str, skills_output: str):
        """保存配置到YAML文件"""
        if self.sandbox_config:
            with open(sandbox_output, 'w', encoding='utf-8') as f:
                yaml.dump(self.sandbox_config.to_dict(), f, default_flow_style=False, allow_unicode=True)
        
        if self.skill_system_config:
            with open(skills_output, 'w', encoding='utf-8') as f:
                yaml.dump(self.skill_system_config.to_dict(), f, default_flow_style=False, allow_unicode=True)


# ============================================================================
# 示例配置生成器
# ============================================================================

class ExampleConfigGenerator:
    """示例配置生成器"""
    
    @staticmethod
    def generate_sandbox_config() -> SandboxConfig:
        """生成示例沙箱配置"""
        # 默认安全配置
        default_security = SecurityConfig(
            security_level=SecurityLevel.RESTRICTED,
            cpu_limit_percent=50.0,
            memory_limit_mb=512,
            disk_limit_mb=1024,
            network_access=False,
            file_system_access=True,
            max_execution_time_seconds=30.0,
            max_process_count=10
        )
        
        # 本地提供者配置
        local_provider = LocalProviderConfig(
            provider_type=SandboxProviderType.LOCAL,
            name="local",
            description="本地进程沙箱，适用于开发和测试",
            work_dir="/tmp/sandbox",
            python_path="/usr/bin/python3",
            environment_variables={
                "PYTHONPATH": "/usr/local/lib/python3.12",
                "TEMP_DIR": "/tmp"
            },
            security_config=default_security
        )
        
        # Docker提供者配置
        docker_security = SecurityConfig(
            security_level=SecurityLevel.SANDBOXED,
            cpu_limit_percent=30.0,
            memory_limit_mb=256,
            network_access=True,
            network_whitelist=[r"^api\.example\.com$", r"^download\.example\.com$"],
            file_system_access=True,
            read_only_paths=["/usr", "/lib", "/bin"],
            writable_paths=["/tmp", "/var/tmp"],
            max_execution_time_seconds=60.0
        )
        
        docker_provider = DockerProviderConfig(
            provider_type=SandboxProviderType.DOCKER,
            name="docker",
            description="Docker容器沙箱，适用于生产环境",
            image="python",
            tag="3.12-slim",
            volumes=[
                {"host": "/tmp/data", "container": "/data", "mode": "rw"},
                {"host": "/tmp/logs", "container": "/logs", "mode": "ro"}
            ],
            environment_variables={
                "PYTHONUNBUFFERED": "1",
                "API_KEY": "${EXTERNAL_API_KEY}"
            },
            network_mode="bridge",
            privileged=False,
            security_config=docker_security
        )
        
        # 异步I/O提供者配置
        aio_provider = AIOProviderConfig(
            provider_type=SandboxProviderType.AIO,
            name="aio",
            description="异步I/O沙箱，适用于高并发场景",
            max_concurrent_tasks=50,
            task_timeout_seconds=10.0,
            retry_count=2,
            retry_delay_seconds=0.5,
            security_config=default_security
        )
        
        # 创建沙箱配置
        sandbox_config = SandboxConfig(
            default_provider="local",
            providers={
                "local": local_provider,
                "docker": docker_provider,
                "aio": aio_provider
            },
            security_config=default_security,
            environment_variables={
                "LOG_LEVEL": "INFO",
                "MAX_RETRIES": "3",
                "API_TIMEOUT": "30"
            },
            metadata={
                "created_by": "ExampleConfigGenerator",
                "environment": "development"
            }
        )
        
        return sandbox_config
    
    @staticmethod
    def generate_skill_system_config() -> SkillSystemConfig:
        """生成示例技能系统配置"""
        # 先创建沙箱配置
        sandbox_config = ExampleConfigGenerator.generate_sandbox_config()
        
        # 创建技能依赖
        file_reader_dep = SkillDependency(
            skill_id="file-reader",
            version_constraint=">=1.0.0",
            required=True,
            description="文件读取技能依赖"
        )
        
        logger_dep = SkillDependency(
            skill_id="logger",
            version_constraint="^2.0.0",
            required=False,
            description="日志记录技能依赖"
        )
        
        # 创建安全配置
        calculator_security = SecurityConfig(
            security_level=SecurityLevel.TRUSTED,
            cpu_limit_percent=10.0,
            memory_limit_mb=50,
            max_execution_time_seconds=5.0
        )
        
        web_scraper_security = SecurityConfig(
            security_level=SecurityLevel.RESTRICTED,
            cpu_limit_percent=30.0,
            memory_limit_mb=200,
            network_access=True,
            network_whitelist=[r"^api\.example\.com$"],
            max_execution_time_seconds=30.0
        )
        
        # 创建技能配置
        calculator_skill = SkillConfig(
            skill_id="calculator",
            name="计算器",
            description="执行数学计算的基础技能",
            version="1.2.0",
            skill_type=SkillType.CALCULATOR,
            status=SkillStatus.ENABLED,
            author="DeerFlow Team",
            license="MIT",
            tags=["math", "calculation", "basic"],
            parameters={
                "precision": 10,
                "enable_complex": False,
                "default_rounding": "round"
            },
            security_config=calculator_security,
            metadata={
                "category": "utility",
                "difficulty": "beginner"
            }
        )
        
        file_converter_skill = SkillConfig(
            skill_id="file-converter",
            name="文件转换器",
            description="转换不同文件格式的技能",
            version="2.1.3",
            skill_type=SkillType.FILE_CONVERTER,
            status=SkillStatus.ENABLED,
            author="Data Tools Team",
            license="Apache-2.0",
            tags=["file", "conversion", "format"],
            dependencies=[file_reader_dep, logger_dep],
            parameters={
                "supported_formats": ["json", "yaml", "csv", "xml"],
                "max_file_size_mb": 10,
                "enable_compression": True
            },
            sandbox_provider="local",
            metadata={
                "category": "data",
                "difficulty": "intermediate"
            }
        )
        
        web_scraper_skill = SkillConfig(
            skill_id="web-scraper",
            name="网络爬虫",
            description="从网站抓取数据的技能",
            version="3.0.1",
            skill_type=SkillType.WEB_SCRAPER,
            status=SkillStatus.ENABLED,
            author="Web Tools Team",
            license="GPL-3.0",
            tags=["web", "scraping", "data"],
            dependencies=[logger_dep],
            parameters={
                "user_agent": "DeerFlow-Bot/1.0",
                "timeout_seconds": 30,
                "max_retries": 3,
                "respect_robots_txt": True
            },
            sandbox_provider="docker",
            security_config=web_scraper_security,
            metadata={
                "category": "web",
                "difficulty": "advanced"
            }
        )
        
        # 创建依赖技能
        file_reader_skill = SkillConfig(
            skill_id="file-reader",
            name="文件读取器",
            description="读取各种文件格式的基础技能",
            version="1.3.2",
            skill_type=SkillType.FILE_CONVERTER,
            status=SkillStatus.ENABLED,
            author="Core Team",
            license="MIT",
            tags=["file", "io", "basic"],
            parameters={
                "encoding": "utf-8",
                "chunk_size": 4096
            },
            metadata={
                "category": "utility",
                "difficulty": "beginner"
            }
        )
        
        logger_skill = SkillConfig(
            skill_id="logger",
            name="日志记录器",
            description="记录系统日志的技能",
            version="2.2.0",
            skill_type=SkillType.TEXT_PROCESSOR,
            status=SkillStatus.ENABLED,
            author="Infra Team",
            license="MIT",
            tags=["logging", "monitoring", "debug"],
            parameters={
                "log_level": "INFO",
                "log_format": "%(asctime)s - %(levelname)s - %(message)s",
                "max_file_size_mb": 10
            },
            metadata={
                "category": "infrastructure",
                "difficulty": "beginner"
            }
        )
        
        # 创建技能系统配置
        skill_system_config = SkillSystemConfig(
            default_sandbox_provider="local",
            sandbox_config=sandbox_config,
            skills={
                "calculator": calculator_skill,
                "file-converter": file_converter_skill,
                "web-scraper": web_scraper_skill,
                "file-reader": file_reader_skill,
                "logger": logger_skill
            },
            auto_resolve_dependencies=True,
            enable_version_check=True,
            enable_security_check=True,
            metadata={
                "system_name": "DeerFlow Skill System",
                "version": "1.0.0",
                "environment": "development"
            }
        )
        
        return skill_system_config
    
    @staticmethod
    def generate_yaml_example() -> Tuple[str, str]:
        """生成YAML示例"""
        sandbox_config = ExampleConfigGenerator.generate_sandbox_config()
        skill_system_config = ExampleConfigGenerator.generate_skill_system_config()
        
        sandbox_yaml = yaml.dump(sandbox_config.to_dict(), default_flow_style=False, allow_unicode=True)
        skills_yaml = yaml.dump(skill_system_config.to_dict(), default_flow_style=False, allow_unicode=True)
        
        return sandbox_yaml, skills_yaml


# ============================================================================
# 测试函数
# ============================================================================

def test_sandbox_config_creation():
    """测试沙箱配置创建"""
    print("=== 测试沙箱配置创建 ===")
    
    # 创建安全配置
    security_config = SecurityConfig(
        security_level=SecurityLevel.RESTRICTED,
        cpu_limit_percent=50.0,
        memory_limit_mb=512,
        network_access=False
    )
    
    # 创建本地提供者
    local_provider = LocalProviderConfig(
        provider_type=SandboxProviderType.LOCAL,
        name="local-dev",
        description="开发环境本地沙箱",
        work_dir="/tmp/dev",
        security_config=security_config
    )
    
    # 创建Docker提供者
    docker_provider = DockerProviderConfig(
        provider_type=SandboxProviderType.DOCKER,
        name="docker-prod",
        description="生产环境Docker沙箱",
        image="python",
        tag="3.12",
        security_config=security_config
    )
    
    # 创建沙箱配置
    sandbox_config = SandboxConfig(
        default_provider="local-dev",
        providers={
            "local-dev": local_provider,
            "docker-prod": docker_provider
        },
        security_config=security_config
    )
    
    # 验证配置
    errors = sandbox_config.validate()
    assert len(errors) == 0, f"沙箱配置验证失败: {errors}"
    
    # 序列化和反序列化测试
    config_dict = sandbox_config.to_dict()
    restored_config = SandboxConfig.from_dict(config_dict)
    assert restored_config.default_provider == sandbox_config.default_provider
    assert len(restored_config.providers) == len(sandbox_config.providers)
    
    print("✓ 沙箱配置创建测试通过")
    return True


def test_skill_config_creation():
    """测试技能配置创建"""
    print("=== 测试技能配置创建 ===")
    
    # 创建依赖
    dependency = SkillDependency(
        skill_id="file-reader",
        version_constraint=">=1.0.0",
        required=True
    )
    
    # 创建安全配置
    security_config = SecurityConfig(
        security_level=SecurityLevel.RESTRICTED,
        max_execution_time_seconds=10.0
    )
    
    # 创建技能配置
    skill_config = SkillConfig(
        skill_id="calculator-advanced",
        name="高级计算器",
        description="支持复杂数学计算的高级技能",
        version="2.0.0",
        skill_type=SkillType.CALCULATOR,
        status=SkillStatus.ENABLED,
        dependencies=[dependency],
        parameters={
            "precision": 15,
            "enable_symbolic": True
        },
        security_config=security_config
    )
    
    # 验证配置
    errors = skill_config.validate()
    assert len(errors) == 0, f"技能配置验证失败: {errors}"
    
    # 测试依赖检查
    assert skill_config.has_dependency("file-reader")
    assert not skill_config.has_dependency("non-existent")
    
    # 序列化和反序列化测试
    config_dict = skill_config.to_dict()
    restored_config = SkillConfig.from_dict(config_dict)
    assert restored_config.skill_id == skill_config.skill_id
    assert restored_config.version == skill_config.version
    
    print("✓ 技能配置创建测试通过")
    return True


def test_skill_dependency_resolution():
    """测试技能依赖解析"""
    print("=== 测试技能依赖解析 ===")
    
    # 创建技能配置
    skill_a = SkillConfig(
        skill_id="skill-a",
        name="技能A",
        version="1.0.0"
    )
    
    skill_b = SkillConfig(
        skill_id="skill-b",
        name="技能B",
        version="1.0.0",
        dependencies=[SkillDependency(skill_id="skill-a", required=True)]
    )
    
    skill_c = SkillConfig(
        skill_id="skill-c",
        name="技能C",
        version="1.0.0",
        dependencies=[
            SkillDependency(skill_id="skill-a", required=True),
            SkillDependency(skill_id="skill-b", required=True)
        ]
    )
    
    # 创建技能系统配置
    system_config = SkillSystemConfig(
        skills={
            "skill-a": skill_a,
            "skill-b": skill_b,
            "skill-c": skill_c
        }
    )
    
    # 验证配置
    errors = system_config.validate()
    assert len(errors) == 0, f"技能系统配置验证失败: {errors}"
    
    # 测试依赖顺序
    dependency_order = system_config.get_dependency_order()
    assert "skill-a" in dependency_order
    assert "skill-b" in dependency_order
    assert "skill-c" in dependency_order
    
    # 确保依赖顺序正确（A在B之前，B在C之前）
    assert dependency_order.index("skill-a") < dependency_order.index("skill-b")
    assert dependency_order.index("skill-b") < dependency_order.index("skill-c")
    
    print("✓ 技能依赖解析测试通过")
    return True


def test_security_config():
    """测试安全配置"""
    print("=== 测试安全配置 ===")
    
    # 创建安全配置
    security_config = SecurityConfig(
        security_level=SecurityLevel.RESTRICTED,
        cpu_limit_percent=75.0,
        memory_limit_mb=1024,
        network_access=True,
        network_whitelist=[r"^api\.example\.com$", r"^download\.example\.com$"],
        network_blacklist=[r"^malicious\.com$"],
        max_execution_time_seconds=60.0
    )
    
    # 验证配置
    errors = security_config.validate()
    assert len(errors) == 0, f"安全配置验证失败: {errors}"
    
    # 测试网络访问检查
    assert security_config.is_network_allowed("api.example.com")
    assert security_config.is_network_allowed("download.example.com")
    assert not security_config.is_network_allowed("malicious.com")
    assert not security_config.is_network_allowed("other.com")
    
    # 序列化和反序列化测试
    config_dict = security_config.to_dict()
    restored_config = SecurityConfig.from_dict(config_dict)
    assert restored_config.security_level == security_config.security_level
    assert restored_config.cpu_limit_percent == security_config.cpu_limit_percent
    
    print("✓ 安全配置测试通过")
    return True


def test_environment_variable_resolution():
    """测试环境变量解析"""
    print("=== 测试环境变量解析 ===")
    
    # 创建带有环境变量的沙箱配置
    local_provider = LocalProviderConfig(
        provider_type=SandboxProviderType.LOCAL,
        name="local",
        environment_variables={
            "API_KEY": "${EXTERNAL_API_KEY}",
            "BASE_URL": "${API_BASE_URL:https://default.example.com}"
        }
    )
    
    sandbox_config = SandboxConfig(
        default_provider="local",
        providers={"local": local_provider},
        environment_variables={
            "LOG_LEVEL": "${APP_LOG_LEVEL:INFO}"
        }
    )
    
    # 定义环境变量
    env_vars = {
        "EXTERNAL_API_KEY": "sk-test-123456",
        "APP_LOG_LEVEL": "DEBUG"
    }
    
    # 解析环境变量
    resolved_config = sandbox_config.resolve_environment_variables(env_vars)
    
    # 检查解析结果
    local_provider_resolved = resolved_config.providers["local"]
    assert local_provider_resolved.environment_variables["API_KEY"] == "sk-test-123456"
    assert local_provider_resolved.environment_variables["BASE_URL"] == "https://default.example.com"  # 使用默认值
    assert resolved_config.environment_variables["LOG_LEVEL"] == "DEBUG"
    
    print("✓ 环境变量解析测试通过")
    return True


def test_config_loader():
    """测试配置加载器"""
    print("=== 测试配置加载器 ===")
    
    # 创建示例配置
    sandbox_config = ExampleConfigGenerator.generate_sandbox_config()
    skill_system_config = ExampleConfigGenerator.generate_skill_system_config()
    
    # 创建加载器
    loader = SandboxSkillConfigLoader()
    
    # 模拟加载过程
    sandbox_dict = sandbox_config.to_dict()
    skills_dict = skill_system_config.to_dict()
    
    import asyncio
    asyncio.run(loader.load_from_dict(sandbox_dict, skills_dict))
    
    # 验证加载结果
    assert loader.sandbox_config is not None
    assert loader.skill_system_config is not None
    assert len(loader.sandbox_config.providers) > 0
    assert len(loader.skill_system_config.skills) > 0
    
    # 验证配置
    errors = loader.validate_all()
    assert len(errors) == 0, f"配置验证失败: {errors}"
    
    # 测试获取技能依赖
    web_scraper_info = loader.get_skill_with_dependencies("web-scraper")
    assert web_scraper_info["skill"]["skill_id"] == "web-scraper"
    assert len(web_scraper_info["dependencies"]) > 0
    
    print("✓ 配置加载器测试通过")
    return True


def test_circular_dependency_detection():
    """测试循环依赖检测"""
    print("=== 测试循环依赖检测 ===")
    
    # 创建有循环依赖的技能配置
    skill_a = SkillConfig(
        skill_id="skill-a",
        name="技能A",
        version="1.0.0",
        dependencies=[SkillDependency(skill_id="skill-b", required=True)]
    )
    
    skill_b = SkillConfig(
        skill_id="skill-b",
        name="技能B",
        version="1.0.0",
        dependencies=[SkillDependency(skill_id="skill-c", required=True)]
    )
    
    skill_c = SkillConfig(
        skill_id="skill-c",
        name="技能C",
        version="1.0.0",
        dependencies=[SkillDependency(skill_id="skill-a", required=True)]  # 循环依赖
    )
    
    # 创建技能系统配置
    system_config = SkillSystemConfig(
        skills={
            "skill-a": skill_a,
            "skill-b": skill_b,
            "skill-c": skill_c
        }
    )
    
    # 验证配置应该检测到循环依赖
    errors = system_config.validate()
    assert any("循环依赖" in error for error in errors), "应该检测到循环依赖但未检测到"
    
    print("✓ 循环依赖检测测试通过")
    return True


def test_version_constraint_checking():
    """测试版本约束检查"""
    print("=== 测试版本约束检查 ===")
    
    # 创建依赖
    dep1 = SkillDependency(
        skill_id="skill-a",
        version_constraint=">=1.0.0",
        required=True
    )
    
    dep2 = SkillDependency(
        skill_id="skill-b",
        version_constraint="^2.0.0",
        required=True
    )
    
    dep3 = SkillDependency(
        skill_id="skill-c",
        version_constraint="~3.1.0",
        required=True
    )
    
    # 测试版本检查
    assert dep1.is_version_satisfied("1.0.0")
    assert dep1.is_version_satisfied("2.0.0")
    assert not dep1.is_version_satisfied("0.9.0")
    
    assert dep2.is_version_satisfied("2.0.0")
    assert dep2.is_version_satisfied("2.1.0")
    assert not dep2.is_version_satisfied("3.0.0")
    
    assert dep3.is_version_satisfied("3.1.0")
    assert dep3.is_version_satisfied("3.1.5")
    assert not dep3.is_version_satisfied("3.2.0")
    
    print("✓ 版本约束检查测试通过")
    return True


# ============================================================================
# 主函数
# ============================================================================

async def run_demo():
    """运行演示"""
    print("🚀 沙箱与技能配置系统演示")
    print("=" * 60)
    
    # 1. 生成示例配置
    print("\n1. 生成示例配置...")
    generator = ExampleConfigGenerator()
    sandbox_config = generator.generate_sandbox_config()
    skill_system_config = generator.generate_skill_system_config()
    
    print(f"   沙箱提供者数量: {len(sandbox_config.providers)}")
    print(f"   技能数量: {len(skill_system_config.skills)}")
    
    # 2. 验证配置
    print("\n2. 验证配置...")
    sandbox_errors = sandbox_config.validate()
    skill_errors = skill_system_config.validate()
    
    if sandbox_errors:
        print(f"   沙箱配置错误: {sandbox_errors}")
    else:
        print("   ✓ 沙箱配置验证通过")
    
    if skill_errors:
        print(f"   技能系统配置错误: {skill_errors}")
    else:
        print("   ✓ 技能系统配置验证通过")
    
    # 3. 演示配置继承
    print("\n3. 演示配置继承...")
    default_provider = sandbox_config.get_provider()
    if default_provider:
        print(f"   默认提供者: {default_provider.name} ({default_provider.provider_type.value})")
        if default_provider.security_config:
            print(f"   安全级别: {default_provider.security_config.security_level.value}")
    
    # 4. 演示技能依赖解析
    print("\n4. 演示技能依赖解析...")
    dependency_order = skill_system_config.get_dependency_order()
    print(f"   技能依赖顺序: {dependency_order}")
    
    # 5. 演示环境变量解析
    print("\n5. 演示环境变量解析...")
    env_vars = {
        "EXTERNAL_API_KEY": "sk-test-987654",
        "APP_LOG_LEVEL": "WARNING"
    }
    resolved_config = sandbox_config.resolve_environment_variables(env_vars)
    docker_provider = resolved_config.get_provider("docker")
    if docker_provider and hasattr(docker_provider, 'environment_variables'):
        api_key = docker_provider.environment_variables.get("API_KEY", "未设置")
        print(f"   解析后的API_KEY: {api_key[:10]}...")
    
    # 6. 生成YAML示例
    print("\n6. 生成YAML示例...")
    sandbox_yaml, skills_yaml = generator.generate_yaml_example()
    
    sandbox_lines = sandbox_yaml.split('\n')
    skills_lines = skills_yaml.split('\n')
    
    print(f"   沙箱配置YAML行数: {len(sandbox_lines)}")
    print(f"   技能配置YAML行数: {len(skills_lines)}")
    
    # 7. 演示配置加载器
    print("\n7. 演示配置加载器...")
    loader = SandboxSkillConfigLoader()
    await loader.load_from_dict(sandbox_config.to_dict(), skill_system_config.to_dict())
    
    print(f"   配置加载时间: {loader.loaded_at}")
    print(f"   可用技能: {list(loader.skill_system_config.skills.keys())}")
    
    # 8. 演示技能依赖信息获取
    print("\n8. 演示技能依赖信息获取...")
    web_scraper_info = loader.get_skill_with_dependencies("web-scraper")
    deps = [dep["skill"]["skill_id"] for dep in web_scraper_info["dependencies"]]
    print(f"   web-scraper技能依赖: {deps}")
    
    print("\n" + "=" * 60)
    print("🎉 演示完成!")
    
    return True


async def run_tests():
    """运行所有测试"""
    print("🧪 运行沙箱与技能配置测试套件")
    print("=" * 60)
    
    tests = [
        ("沙箱配置创建", test_sandbox_config_creation),
        ("技能配置创建", test_skill_config_creation),
        ("技能依赖解析", test_skill_dependency_resolution),
        ("安全配置", test_security_config),
        ("环境变量解析", test_environment_variable_resolution),
        ("配置加载器", test_config_loader),
        ("循环依赖检测", test_circular_dependency_detection),
        ("版本约束检查", test_version_constraint_checking),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                print(f"✓ {test_name}: 通过")
                passed += 1
            else:
                print(f"✗ {test_name}: 失败")
                failed += 1
        except Exception as e:
            print(f"✗ {test_name}: 错误 - {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 所有测试通过!")
        return True
    else:
        print("⚠️  有测试失败，请检查")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='沙箱与技能配置演示')
    parser.add_argument('--test', action='store_true', help='运行测试')
    parser.add_argument('--demo', action='store_true', help='运行演示')
    parser.add_argument('--all', action='store_true', help='运行所有')
    parser.add_argument('--generate-yaml', action='store_true', help='生成YAML示例')
    
    args = parser.parse_args()
    
    if args.test or args.all:
        print("开始测试...")
        success = asyncio.run(run_tests())
        if not success:
            sys.exit(1)
    
    if args.demo or args.all:
        print("\n开始演示...")
        asyncio.run(run_demo())
    
    if args.generate_yaml:
        print("生成YAML示例...")
        sandbox_yaml, skills_yaml = ExampleConfigGenerator.generate_yaml_example()
        print("\n=== 沙箱配置YAML ===")
        print(sandbox_yaml)
        print("\n=== 技能配置YAML ===")
        print(skills_yaml)
    
    if not any([args.test, args.demo, args.all, args.generate_yaml]):
        # 默认运行演示
        print("默认运行演示...")
        asyncio.run(run_demo())


if __name__ == "__main__":
    main()