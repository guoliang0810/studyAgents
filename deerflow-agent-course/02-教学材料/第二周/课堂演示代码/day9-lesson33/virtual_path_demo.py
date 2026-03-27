#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 9 Lesson 33: 虚拟路径系统架构 (Virtual Path System Architecture)

本文件演示虚拟路径系统的完整实现，包括：
1. VirtualPathSystem类 - 实现虚拟路径到实际路径的安全转换和映射管理
2. 路径映射管理 - 前缀映射、正则匹配、优先级管理、动态规则更新
3. 安全机制 - 路径遍历攻击检测、标准化处理、边界检查、安全审计
4. 性能优化 - 路径翻译缓存、LRU策略、并发安全设计、统计监控
5. 系统集成 - 与沙箱系统、技能系统、文件系统的完整集成方案

采用五部分结构设计：
第一部分：概念与设计原则 - 定义虚拟路径系统的核心概念和设计原则
第二部分：接口与协议实现 - 实现虚拟路径系统的核心接口和安全协议
第三部分：核心功能实现 - 实现路径映射、翻译、安全检测、缓存优化等核心功能
第四部分：集成与配置 - 集成虚拟路径系统，支持配置驱动创建和注册
第五部分：测试与演示 - 提供完整测试套件和演示程序

使用示例:
    python virtual_path_demo.py          # 运行基本演示
    python virtual_path_demo.py --test   # 运行测试套件
    python virtual_path_demo.py --demo   # 运行完整演示
    python virtual_path_demo.py --help   # 显示帮助信息
"""

import os
import sys
import re
import json
import time
import hashlib
import pathlib
import argparse
import tempfile
import shutil
import platform
import inspect
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable, Tuple, Set, NamedTuple
from dataclasses import dataclass, field, asdict
from collections import OrderedDict, deque
from functools import lru_cache
import logging
from logging.handlers import RotatingFileHandler
from contextlib import contextmanager
import threading
import concurrent.futures
from datetime import datetime, timedelta

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================

class VirtualPathCapability(Enum):
    """虚拟路径系统能力枚举"""
    PATH_TRANSLATION = "路径翻译"              # 虚拟路径到实际路径的翻译
    PREFIX_MAPPING = "前缀映射"               # 基于前缀的路径映射
    REGEX_MAPPING = "正则映射"                # 基于正则表达式的路径映射
    SECURITY_CHECK = "安全检测"               # 路径遍历攻击检测
    CACHE_OPTIMIZATION = "缓存优化"           # 路径翻译缓存加速
    DYNAMIC_MAPPING = "动态映射"              # 运行时动态更新映射规则
    AUDIT_LOGGING = "审计日志"                # 路径访问审计日志
    CROSS_PLATFORM = "跨平台兼容"             # 跨操作系统路径兼容
    PERFORMANCE_MONITORING = "性能监控"       # 性能指标监控
    
    def description(self) -> str:
        """获取能力描述"""
        descriptions = {
            self.PATH_TRANSLATION: "将用户提供的虚拟路径安全转换为实际文件系统路径",
            self.PREFIX_MAPPING: "基于路径前缀的映射规则，支持优先级和覆盖关系",
            self.REGEX_MAPPING: "基于正则表达式的灵活路径匹配和映射",
            self.SECURITY_CHECK: "检测和阻止路径遍历攻击（如../跨目录访问）",
            self.CACHE_OPTIMIZATION: "使用LRU缓存加速频繁翻译的路径，提高系统性能",
            self.DYNAMIC_MAPPING: "支持运行时动态添加、更新、删除映射规则",
            self.AUDIT_LOGGING: "记录所有路径翻译操作，支持安全审计和问题追踪",
            self.CROSS_PLATFORM: "正确处理不同操作系统（Windows/Linux/macOS）的路径格式",
            self.PERFORMANCE_MONITORING: "监控路径翻译性能指标：命中率、平均耗时、缓存效率等",
        }
        return descriptions.get(self, "未知能力")


class PathMappingType(Enum):
    """路径映射类型枚举"""
    PREFIX = "前缀匹配"      # 前缀匹配：/workspace -> /tmp/workspace
    REGEX = "正则匹配"       # 正则匹配：^/user/(.+)$ -> /home/$1
    EXACT = "精确匹配"       # 精确匹配：/config/app.conf -> /etc/app.conf
    WILDCARD = "通配符匹配"  # 通配符匹配：/data/*.log -> /var/log/*
    
    def description(self) -> str:
        """获取映射类型描述"""
        descriptions = {
            self.PREFIX: "基于路径前缀的匹配，支持最长前缀匹配原则",
            self.REGEX: "基于正则表达式的灵活匹配，支持捕获组和替换",
            self.EXACT: "精确路径匹配，完全相同的路径才会匹配",
            self.WILDCARD: "基于通配符的简单模式匹配，支持*和?通配符",
        }
        return descriptions.get(self, "未知映射类型")


class PathSecurityLevel(Enum):
    """路径安全级别枚举"""
    NONE = "无安全检测"       # 不进行安全检测（仅用于受信任环境）
    BASIC = "基础安全检测"    # 基础路径遍历检测（检测../）
    STRICT = "严格安全检测"   # 严格安全检测（检测所有可能的遍历攻击）
    PARANOID = "偏执安全检测" # 偏执安全检测（检测所有异常路径组件）
    
    def description(self) -> str:
        """获取安全级别描述"""
        descriptions = {
            self.NONE: "不进行安全检测，适用于完全受信任的环境",
            self.BASIC: "基础安全检测，检测常见的路径遍历攻击（如../）",
            self.STRICT: "严格安全检测，检测所有可能的路径遍历攻击和异常组件",
            self.PARANOID: "偏执安全检测，检测所有异常路径组件并记录详细审计日志",
        }
        return descriptions.get(self, "未知安全级别")


@dataclass
class PathMappingRule:
    """路径映射规则"""
    virtual_path: str           # 虚拟路径模式（前缀、正则、精确路径）
    real_path: str             # 实际路径目标
    mapping_type: PathMappingType = PathMappingType.PREFIX  # 映射类型
    priority: int = 0          # 优先级（数字越大优先级越高）
    enabled: bool = True       # 是否启用
    description: str = ""      # 规则描述
    created_at: float = field(default_factory=time.time)  # 创建时间
    updated_at: float = field(default_factory=time.time)  # 更新时间
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "virtual_path": self.virtual_path,
            "real_path": self.real_path,
            "mapping_type": self.mapping_type.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PathMappingRule":
        """从字典创建"""
        return cls(
            virtual_path=data["virtual_path"],
            real_path=data["real_path"],
            mapping_type=PathMappingType(data.get("mapping_type", "前缀匹配")),
            priority=data.get("priority", 0),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class PathTranslationResult:
    """路径翻译结果"""
    virtual_path: str           # 原始虚拟路径
    real_path: str             # 翻译后的实际路径
    mapping_rule: Optional[PathMappingRule] = None  # 使用的映射规则
    security_check_passed: bool = True  # 安全检测是否通过
    security_warnings: List[str] = field(default_factory=list)  # 安全警告
    translation_time: float = 0.0  # 翻译耗时（秒）
    cache_hit: bool = False    # 是否命中缓存
    normalized_path: str = ""  # 标准化后的路径
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        result = {
            "virtual_path": self.virtual_path,
            "real_path": self.real_path,
            "security_check_passed": self.security_check_passed,
            "security_warnings": self.security_warnings,
            "translation_time": self.translation_time,
            "cache_hit": self.cache_hit,
            "normalized_path": self.normalized_path,
        }
        if self.mapping_rule:
            result["mapping_rule"] = self.mapping_rule.to_dict()
        return result


@dataclass
class VirtualPathConfig:
    """虚拟路径系统配置"""
    base_dir: str = ""                     # 基础目录（默认映射目录）
    security_level: PathSecurityLevel = PathSecurityLevel.STRICT  # 安全级别
    enable_cache: bool = True              # 是否启用缓存
    cache_size: int = 1000                 # 缓存大小（条目数）
    enable_audit_log: bool = True          # 是否启用审计日志
    audit_log_file: Optional[str] = None   # 审计日志文件路径
    max_path_length: int = 4096            # 最大路径长度限制
    follow_symlinks: bool = False          # 是否跟踪符号链接
    default_mappings: List[Dict] = field(default_factory=list)  # 默认映射规则
    auto_normalize: bool = True            # 是否自动标准化路径
    case_sensitive: Optional[bool] = None  # 是否大小写敏感（None表示自动检测）
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "base_dir": self.base_dir,
            "security_level": self.security_level.value,
            "enable_cache": self.enable_cache,
            "cache_size": self.cache_size,
            "enable_audit_log": self.enable_audit_log,
            "audit_log_file": self.audit_log_file,
            "max_path_length": self.max_path_length,
            "follow_symlinks": self.follow_symlinks,
            "default_mappings": self.default_mappings,
            "auto_normalize": self.auto_normalize,
            "case_sensitive": self.case_sensitive,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "VirtualPathConfig":
        """从字典创建"""
        return cls(
            base_dir=data.get("base_dir", ""),
            security_level=PathSecurityLevel(data.get("security_level", "严格安全检测")),
            enable_cache=data.get("enable_cache", True),
            cache_size=data.get("cache_size", 1000),
            enable_audit_log=data.get("enable_audit_log", True),
            audit_log_file=data.get("audit_log_file"),
            max_path_length=data.get("max_path_length", 4096),
            follow_symlinks=data.get("follow_symlinks", False),
            default_mappings=data.get("default_mappings", []),
            auto_normalize=data.get("auto_normalize", True),
            case_sensitive=data.get("case_sensitive"),
        )


@dataclass
class VirtualPathMetrics:
    """虚拟路径系统性能指标"""
    total_translations: int = 0           # 总翻译次数
    successful_translations: int = 0      # 成功翻译次数
    failed_translations: int = 0          # 失败翻译次数
    cache_hits: int = 0                   # 缓存命中次数
    cache_misses: int = 0                 # 缓存未命中次数
    cache_size: int = 0                   # 当前缓存大小
    average_translation_time: float = 0.0 # 平均翻译时间（秒）
    max_translation_time: float = 0.0     # 最大翻译时间（秒）
    min_translation_time: float = float('inf')  # 最小翻译时间（秒）
    security_blocks: int = 0              # 安全检测阻止次数
    mapping_misses: int = 0               # 映射未找到次数
    
    def hit_rate(self) -> float:
        """计算缓存命中率"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0
    
    def success_rate(self) -> float:
        """计算翻译成功率"""
        total = self.successful_translations + self.failed_translations
        return self.successful_translations / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_translations": self.total_translations,
            "successful_translations": self.successful_translations,
            "failed_translations": self.failed_translations,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_size": self.cache_size,
            "cache_hit_rate": self.hit_rate(),
            "success_rate": self.success_rate(),
            "average_translation_time": self.average_translation_time,
            "max_translation_time": self.max_translation_time,
            "min_translation_time": self.min_translation_time if self.min_translation_time != float('inf') else 0.0,
            "security_blocks": self.security_blocks,
            "mapping_misses": self.mapping_misses,
        }


# ============================================================================
# 第二部分：接口与协议实现
# ============================================================================

class VirtualPathError(Exception):
    """虚拟路径系统基础异常"""
    pass


class PathTraversalError(VirtualPathError):
    """路径遍历攻击检测异常"""
    pass


class MappingNotFoundError(VirtualPathError):
    """映射未找到异常"""
    pass


class PathNormalizationError(VirtualPathError):
    """路径标准化异常"""
    pass


class PathSecurityChecker(ABC):
    """路径安全检测器抽象基类"""
    
    @abstractmethod
    def check_path(self, path: str, base_dir: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        检查路径安全性
        
        Args:
            path: 要检查的路径
            base_dir: 基础目录（用于相对路径检查）
            
        Returns:
            (是否安全, 警告列表)
        """
        pass
    
    @abstractmethod
    def normalize_path(self, path: str, base_dir: Optional[str] = None) -> str:
        """
        标准化路径
        
        Args:
            path: 要标准化的路径
            base_dir: 基础目录（用于相对路径标准化）
            
        Returns:
            标准化后的路径
        """
        pass


class PathMappingStrategy(ABC):
    """路径映射策略抽象基类"""
    
    @abstractmethod
    def match(self, virtual_path: str, rule: PathMappingRule) -> bool:
        """
        检查路径是否匹配规则
        
        Args:
            virtual_path: 虚拟路径
            rule: 映射规则
            
        Returns:
            是否匹配
        """
        pass
    
    @abstractmethod
    def translate(self, virtual_path: str, rule: PathMappingRule) -> str:
        """
        根据规则翻译路径
        
        Args:
            virtual_path: 虚拟路径
            rule: 映射规则
            
        Returns:
            翻译后的实际路径
        """
        pass


class VirtualPathSystemInterface(ABC):
    """虚拟路径系统接口"""
    
    @abstractmethod
    def translate(self, virtual_path: str, base_dir: Optional[str] = None) -> PathTranslationResult:
        """
        翻译虚拟路径到实际路径
        
        Args:
            virtual_path: 虚拟路径
            base_dir: 基础目录（可选，覆盖默认基础目录）
            
        Returns:
            路径翻译结果
        """
        pass
    
    @abstractmethod
    def add_mapping(self, rule: PathMappingRule) -> bool:
        """
        添加映射规则
        
        Args:
            rule: 映射规则
            
        Returns:
            是否添加成功
        """
        pass
    
    @abstractmethod
    def remove_mapping(self, virtual_path: str, mapping_type: Optional[PathMappingType] = None) -> bool:
        """
        移除映射规则
        
        Args:
            virtual_path: 虚拟路径模式
            mapping_type: 映射类型（可选，None表示移除所有匹配的规则）
            
        Returns:
            是否移除成功
        """
        pass
    
    @abstractmethod
    def list_mappings(self, enabled_only: bool = True) -> List[PathMappingRule]:
        """
        列出所有映射规则
        
        Args:
            enabled_only: 是否只列出启用的规则
            
        Returns:
            映射规则列表
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> VirtualPathMetrics:
        """
        获取性能指标
        
        Returns:
            性能指标
        """
        pass
    
    @abstractmethod
    def clear_cache(self) -> None:
        """清空缓存"""
        pass
    
    @abstractmethod
    def audit_log(self, action: str, virtual_path: str, result: Optional[PathTranslationResult] = None) -> None:
        """
        记录审计日志
        
        Args:
            action: 操作类型（translate, add_mapping, remove_mapping等）
            virtual_path: 虚拟路径
            result: 翻译结果（可选）
        """
        pass


# ============================================================================
# 第三部分：核心功能实现
# ============================================================================

class BasicSecurityChecker(PathSecurityChecker):
    """基础安全检测器"""
    
    def __init__(self, security_level: PathSecurityLevel = PathSecurityLevel.STRICT):
        self.security_level = security_level
        self.traversal_patterns = [
            r'\.\./',          # ../ 跨目录
            r'\.\.\\',         # ..\ 跨目录（Windows）
            r'\.\.\.',         # ... 可疑
            r'//',             # 双斜杠
            r'\\\\',           # 双反斜杠
            r'/~',             # 用户目录引用
            r'/\$',            # 环境变量引用
            r'/\.\.',          # /.. 根目录向上
            r'\\\.\.',         # \.. 根目录向上（Windows）
        ]
        
        if security_level in [PathSecurityLevel.STRICT, PathSecurityLevel.PARANOID]:
            self.traversal_patterns.extend([
                r'%2e%2e',     # URL编码的..
                r'\.\.%2f',    # ../的变体
                r'\.\.%5c',    # ..\的变体
                r'\.\.\.\.',   # ....
                r'\./',        # ./
                r'\.\\',       # .\
            ])
        
        if security_level == PathSecurityLevel.PARANOID:
            self.traversal_patterns.extend([
                r'[\x00-\x1f\x7f]',  # 控制字符
                r'[<>:"|?*]',        # Windows保留字符
                r'//+',              # 多个斜杠
                r'\\\\+',            # 多个反斜杠
            ])
    
    def check_path(self, path: str, base_dir: Optional[str] = None) -> Tuple[bool, List[str]]:
        """检查路径安全性"""
        warnings = []
        
        # 检查路径长度
        if len(path) > 4096:  # 常见文件系统限制
            warnings.append(f"路径过长 ({len(path)} > 4096)")
        
        # 检查路径遍历攻击
        for pattern in self.traversal_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                warnings.append(f"检测到可疑路径组件: {pattern}")
        
        # 检查绝对路径（如果提供了base_dir）
        if base_dir and os.path.isabs(path):
            # 确保绝对路径在base_dir内
            normalized_base = os.path.normpath(base_dir)
            normalized_path = os.path.normpath(path)
            if not normalized_path.startswith(normalized_base):
                warnings.append(f"绝对路径不在基础目录内: {path}")
        
        # 根据安全级别决定是否通过
        if self.security_level == PathSecurityLevel.NONE:
            return True, warnings
        elif self.security_level == PathSecurityLevel.BASIC:
            # 只检查基本遍历攻击
            basic_patterns = [r'\.\./', r'\.\.\\']
            for pattern in basic_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    return False, warnings + [f"基础安全检测阻止: {pattern}"]
            return True, warnings
        elif self.security_level == PathSecurityLevel.STRICT:
            # 检查所有遍历攻击模式
            strict_patterns = [r'\.\./', r'\.\.\\', r'\.\.\.', r'//', r'\\\\']
            for pattern in strict_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    return False, warnings + [f"严格安全检测阻止: {pattern}"]
            return True, warnings
        else:  # PARANOID
            # 有任何警告就阻止
            return len(warnings) == 0, warnings
    
    def normalize_path(self, path: str, base_dir: Optional[str] = None) -> str:
        """标准化路径"""
        # 确保路径使用正确的分隔符
        if platform.system() == 'Windows':
            path = path.replace('/', '\\')
        else:
            path = path.replace('\\', '/')
        
        # 标准化路径
        if base_dir and not os.path.isabs(path):
            # 相对路径相对于base_dir
            normalized = os.path.normpath(os.path.join(base_dir, path))
        else:
            normalized = os.path.normpath(path)
        
        # 移除末尾分隔符（目录除外）
        if normalized.endswith(os.sep) and normalized != os.sep:
            normalized = normalized.rstrip(os.sep)
        
        return normalized


class PrefixMappingStrategy(PathMappingStrategy):
    """前缀映射策略"""
    
    def match(self, virtual_path: str, rule: PathMappingRule) -> bool:
        """检查路径是否匹配前缀规则"""
        if rule.mapping_type != PathMappingType.PREFIX:
            return False
        
        # 前缀匹配：虚拟路径以rule.virtual_path开头
        if platform.system() == 'Windows' or rule.virtual_path.lower() == virtual_path.lower():
            # Windows不区分大小写，或精确匹配时忽略大小写
            return virtual_path.lower().startswith(rule.virtual_path.lower())
        else:
            return virtual_path.startswith(rule.virtual_path)
    
    def translate(self, virtual_path: str, rule: PathMappingRule) -> str:
        """根据前缀规则翻译路径"""
        # 移除虚拟路径前缀，替换为实际路径
        prefix_len = len(rule.virtual_path)
        relative_path = virtual_path[prefix_len:]
        
        # 如果relative_path以分隔符开头，移除它（除非实际路径以分隔符结尾）
        if relative_path.startswith(os.sep) and not rule.real_path.endswith(os.sep):
            relative_path = relative_path[1:]
        
        # 拼接路径
        return os.path.join(rule.real_path, relative_path) if relative_path else rule.real_path


class RegexMappingStrategy(PathMappingStrategy):
    """正则映射策略"""
    
    def match(self, virtual_path: str, rule: PathMappingRule) -> bool:
        """检查路径是否匹配正则规则"""
        if rule.mapping_type != PathMappingType.REGEX:
            return False
        
        try:
            return bool(re.match(rule.virtual_path, virtual_path))
        except re.error:
            return False
    
    def translate(self, virtual_path: str, rule: PathMappingRule) -> str:
        """根据正则规则翻译路径"""
        try:
            # 使用正则替换
            return re.sub(rule.virtual_path, rule.real_path, virtual_path)
        except re.error as e:
            raise VirtualPathError(f"正则替换失败: {e}")


class ExactMappingStrategy(PathMappingStrategy):
    """精确映射策略"""
    
    def match(self, virtual_path: str, rule: PathMappingRule) -> bool:
        """检查路径是否匹配精确规则"""
        if rule.mapping_type != PathMappingType.EXACT:
            return False
        
        if platform.system() == 'Windows':
            return virtual_path.lower() == rule.virtual_path.lower()
        else:
            return virtual_path == rule.virtual_path
    
    def translate(self, virtual_path: str, rule: PathMappingRule) -> str:
        """根据精确规则翻译路径"""
        # 精确匹配直接返回实际路径
        return rule.real_path


class WildcardMappingStrategy(PathMappingStrategy):
    """通配符映射策略"""
    
    def match(self, virtual_path: str, rule: PathMappingRule) -> bool:
        """检查路径是否匹配通配符规则"""
        if rule.mapping_type != PathMappingType.WILDCARD:
            return False
        
        # 将通配符模式转换为正则表达式
        pattern = rule.virtual_path
        pattern = re.escape(pattern)  # 转义特殊字符
        pattern = pattern.replace('\\*', '.*').replace('\\?', '.')  # 替换通配符
        
        # 添加起始和结束锚点
        pattern = f'^{pattern}$'
        
        try:
            return bool(re.match(pattern, virtual_path))
        except re.error:
            return False
    
    def translate(self, virtual_path: str, rule: PathMappingRule) -> str:
        """根据通配符规则翻译路径"""
        # 通配符映射通常需要更复杂的替换逻辑
        # 这里简单返回实际路径（假设是一对一映射）
        return rule.real_path


class PathTranslationCache:
    """路径翻译缓存"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = OrderedDict()  # 使用有序字典实现LRU
        self.hits = 0
        self.misses = 0
        self.lock = threading.RLock()  # 可重入锁
    
    def get(self, key: str) -> Optional[PathTranslationResult]:
        """获取缓存项"""
        with self.lock:
            if key in self.cache:
                # 移动到最新位置（LRU）
                value = self.cache.pop(key)
                self.cache[key] = value
                self.hits += 1
                return value
            self.misses += 1
            return None
    
    def set(self, key: str, value: PathTranslationResult) -> None:
        """设置缓存项"""
        with self.lock:
            if key in self.cache:
                # 更新现有项
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                # 移除最旧的项（LRU）
                self.cache.popitem(last=False)
            self.cache[key] = value
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0.0
            return {
                "size": len(self.cache),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": hit_rate,
                "max_size": self.max_size,
            }


class VirtualPathSystem(VirtualPathSystemInterface):
    """虚拟路径系统实现"""
    
    def __init__(self, config: Optional[VirtualPathConfig] = None):
        self.config = config or VirtualPathConfig()
        self.security_checker = BasicSecurityChecker(self.config.security_level)
        self.mapping_strategies = {
            PathMappingType.PREFIX: PrefixMappingStrategy(),
            PathMappingType.REGEX: RegexMappingStrategy(),
            PathMappingType.EXACT: ExactMappingStrategy(),
            PathMappingType.WILDCARD: WildcardMappingStrategy(),
        }
        self.mappings: List[PathMappingRule] = []
        self.cache = PathTranslationCache(self.config.cache_size) if self.config.enable_cache else None
        self.metrics = VirtualPathMetrics()
        self.logger = self._setup_logger()
        self.lock = threading.RLock()
        
        # 初始化默认映射
        self._init_default_mappings()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"VirtualPathSystem.{id(self)}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # 控制台处理器
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
            
            # 文件处理器（如果配置了审计日志）
            if self.config.enable_audit_log and self.config.audit_log_file:
                file_handler = RotatingFileHandler(
                    self.config.audit_log_file,
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5
                )
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
        
        return logger
    
    def _init_default_mappings(self) -> None:
        """初始化默认映射规则"""
        for mapping_data in self.config.default_mappings:
            try:
                rule = PathMappingRule.from_dict(mapping_data)
                self.add_mapping(rule)
            except Exception as e:
                self.logger.warning(f"初始化默认映射失败: {e}")
    
    def translate(self, virtual_path: str, base_dir: Optional[str] = None) -> PathTranslationResult:
        """翻译虚拟路径到实际路径"""
        start_time = time.perf_counter()
        
        # 使用提供的基础目录或默认基础目录
        actual_base_dir = base_dir if base_dir is not None else self.config.base_dir
        
        # 构建缓存键
        cache_key = None
        if self.cache:
            cache_key = f"{virtual_path}:{actual_base_dir}:{self.config.security_level.value}"
            cached_result = self.cache.get(cache_key)
            if cached_result:
                cached_result.translation_time = time.perf_counter() - start_time
                cached_result.cache_hit = True
                self.metrics.cache_hits += 1
                self.metrics.total_translations += 1
                self.metrics.successful_translations += 1
                return cached_result
        
        # 安全检测
        security_passed, security_warnings = self.security_checker.check_path(
            virtual_path, actual_base_dir
        )
        
        if not security_passed:
            self.metrics.security_blocks += 1
            self.metrics.total_translations += 1
            self.metrics.failed_translations += 1
            raise PathTraversalError(f"路径安全检测失败: {virtual_path}. 警告: {security_warnings}")
        
        # 标准化路径
        normalized_path = self.security_checker.normalize_path(virtual_path, actual_base_dir)
        
        # 查找匹配的映射规则
        matched_rule = None
        translated_path = normalized_path
        
        with self.lock:
            # 按优先级排序（高优先级在前）
            sorted_mappings = sorted(self.mappings, key=lambda r: r.priority, reverse=True)
            
            for rule in sorted_mappings:
                if not rule.enabled:
                    continue
                
                strategy = self.mapping_strategies.get(rule.mapping_type)
                if strategy and strategy.match(virtual_path, rule):
                    matched_rule = rule
                    try:
                        translated_path = strategy.translate(virtual_path, rule)
                        break
                    except Exception as e:
                        self.logger.warning(f"路径翻译失败: {e}")
        
        # 如果没有匹配的规则，使用基础目录
        if not matched_rule and actual_base_dir:
            if os.path.isabs(virtual_path):
                translated_path = virtual_path
            else:
                translated_path = os.path.join(actual_base_dir, virtual_path)
        
        # 再次标准化最终路径
        final_path = self.security_checker.normalize_path(translated_path)
        
        # 检查路径长度限制
        if len(final_path) > self.config.max_path_length:
            raise VirtualPathError(f"路径过长 ({len(final_path)} > {self.config.max_path_length})")
        
        # 记录翻译时间
        translation_time = time.perf_counter() - start_time
        
        # 更新指标
        self.metrics.total_translations += 1
        self.metrics.successful_translations += 1
        self.metrics.cache_misses += 1 if self.cache and not cache_key else 0
        self.metrics.average_translation_time = (
            (self.metrics.average_translation_time * (self.metrics.total_translations - 1) + translation_time) 
            / self.metrics.total_translations
        )
        self.metrics.max_translation_time = max(self.metrics.max_translation_time, translation_time)
        self.metrics.min_translation_time = min(self.metrics.min_translation_time, translation_time)
        
        # 构建结果
        result = PathTranslationResult(
            virtual_path=virtual_path,
            real_path=final_path,
            mapping_rule=matched_rule,
            security_check_passed=security_passed,
            security_warnings=security_warnings,
            translation_time=translation_time,
            cache_hit=False,
            normalized_path=normalized_path,
        )
        
        # 缓存结果
        if self.cache and cache_key:
            self.cache.set(cache_key, result)
            self.metrics.cache_size = self.cache.cache_size
        
        # 记录审计日志
        if self.config.enable_audit_log:
            self.audit_log("translate", virtual_path, result)
        
        return result
    
    def add_mapping(self, rule: PathMappingRule) -> bool:
        """添加映射规则"""
        with self.lock:
            # 检查是否已存在相同规则
            for existing_rule in self.mappings:
                if (existing_rule.virtual_path == rule.virtual_path and 
                    existing_rule.mapping_type == rule.mapping_type):
                    # 更新现有规则
                    existing_rule.real_path = rule.real_path
                    existing_rule.priority = rule.priority
                    existing_rule.enabled = rule.enabled
                    existing_rule.description = rule.description
                    existing_rule.updated_at = time.time()
                    self.logger.info(f"更新映射规则: {rule.virtual_path} -> {rule.real_path}")
                    return True
            
            # 添加新规则
            self.mappings.append(rule)
            self.logger.info(f"添加映射规则: {rule.virtual_path} -> {rule.real_path}")
            
            # 记录审计日志
            if self.config.enable_audit_log:
                self.audit_log("add_mapping", rule.virtual_path)
            
            return True
    
    def remove_mapping(self, virtual_path: str, mapping_type: Optional[PathMappingType] = None) -> bool:
        """移除映射规则"""
        removed = False
        with self.lock:
            remaining_mappings = []
            for rule in self.mappings:
                if rule.virtual_path == virtual_path and (mapping_type is None or rule.mapping_type == mapping_type):
                    self.logger.info(f"移除映射规则: {rule.virtual_path} -> {rule.real_path}")
                    removed = True
                else:
                    remaining_mappings.append(rule)
            
            self.mappings = remaining_mappings
        
        if removed and self.config.enable_audit_log:
            self.audit_log("remove_mapping", virtual_path)
        
        return removed
    
    def list_mappings(self, enabled_only: bool = True) -> List[PathMappingRule]:
        """列出所有映射规则"""
        with self.lock:
            if enabled_only:
                return [rule for rule in self.mappings if rule.enabled]
            return self.mappings.copy()
    
    def get_metrics(self) -> VirtualPathMetrics:
        """获取性能指标"""
        with self.lock:
            # 复制指标对象
            metrics = VirtualPathMetrics()
            for field in metrics.__annotations__:
                setattr(metrics, field, getattr(self.metrics, field))
            
            # 更新缓存统计
            if self.cache:
                cache_stats = self.cache.stats()
                metrics.cache_size = cache_stats["size"]
                metrics.cache_hits = cache_stats["hits"]
                metrics.cache_misses = cache_stats["misses"]
            
            return metrics
    
    def clear_cache(self) -> None:
        """清空缓存"""
        if self.cache:
            self.cache.clear()
            self.logger.info("清空路径翻译缓存")
    
    def audit_log(self, action: str, virtual_path: str, result: Optional[PathTranslationResult] = None) -> None:
        """记录审计日志"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "virtual_path": virtual_path,
            "config": self.config.to_dict(),
        }
        
        if result:
            log_data["result"] = result.to_dict()
        
        self.logger.info(f"审计日志: {json.dumps(log_data, ensure_ascii=False)}")


# ============================================================================
# 第四部分：集成与配置
# ============================================================================

class VirtualPathSystemFactory:
    """虚拟路径系统工厂"""
    
    @staticmethod
    def create_standard(config: Optional[Dict] = None) -> VirtualPathSystem:
        """创建标准虚拟路径系统"""
        vps_config = VirtualPathConfig.from_dict(config or {})
        return VirtualPathSystem(vps_config)
    
    @staticmethod
    def create_secure(config: Optional[Dict] = None) -> VirtualPathSystem:
        """创建安全增强虚拟路径系统"""
        base_config = config or {}
        secure_config = {
            **base_config,
            "security_level": "偏执安全检测",
            "enable_audit_log": True,
            "max_path_length": 1024,
            "follow_symlinks": False,
        }
        vps_config = VirtualPathConfig.from_dict(secure_config)
        return VirtualPathSystem(vps_config)
    
    @staticmethod
    def create_high_performance(config: Optional[Dict] = None) -> VirtualPathSystem:
        """创建高性能虚拟路径系统"""
        base_config = config or {}
        perf_config = {
            **base_config,
            "enable_cache": True,
            "cache_size": 5000,
            "security_level": "基础安全检测",
            "enable_audit_log": False,
        }
        vps_config = VirtualPathConfig.from_dict(perf_config)
        return VirtualPathSystem(vps_config)
    
    @staticmethod
    def create_from_config(config_data: Dict) -> VirtualPathSystem:
        """根据配置数据创建虚拟路径系统"""
        if "type" in config_data:
            factory_methods = {
                "standard": VirtualPathSystemFactory.create_standard,
                "secure": VirtualPathSystemFactory.create_secure,
                "high_performance": VirtualPathSystemFactory.create_high_performance,
            }
            
            system_type = config_data.get("type", "standard")
            factory_method = factory_methods.get(system_type, VirtualPathSystemFactory.create_standard)
            system_config = config_data.get("config", {})
            
            return factory_method(system_config)
        else:
            # 直接使用配置数据
            vps_config = VirtualPathConfig.from_dict(config_data)
            return VirtualPathSystem(vps_config)


class VirtualPathRegistry:
    """虚拟路径系统注册表"""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.systems: Dict[str, VirtualPathSystem] = {}
        self.lock = threading.RLock()
    
    def register(self, name: str, system: VirtualPathSystem) -> bool:
        """注册虚拟路径系统"""
        with self.lock:
            if name in self.systems:
                return False
            self.systems[name] = system
            return True
    
    def get(self, name: str) -> Optional[VirtualPathSystem]:
        """获取虚拟路径系统"""
        with self.lock:
            return self.systems.get(name)
    
    def unregister(self, name: str) -> bool:
        """注销虚拟路径系统"""
        with self.lock:
            if name in self.systems:
                del self.systems[name]
                return True
            return False
    
    def list_all(self) -> List[Dict[str, Any]]:
        """列出所有注册的系统"""
        with self.lock:
            systems_info = []
            for name, system in self.systems.items():
                metrics = system.get_metrics()
                systems_info.append({
                    "name": name,
                    "config": system.config.to_dict(),
                    "metrics": metrics.to_dict(),
                    "mapping_count": len(system.list_mappings(enabled_only=False)),
                })
            return systems_info


# ============================================================================
# 第五部分：测试与演示
# ============================================================================

class VirtualPathTestSuite:
    """虚拟路径系统测试套件"""
    
    def __init__(self):
        self.tests = []
        self.results = {}
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        # 基础功能测试
        self.tests.append(("test_basic_translation", self.test_basic_translation))
        self.tests.append(("test_prefix_mapping", self.test_prefix_mapping))
        self.tests.append(("test_security_check", self.test_security_check))
        self.tests.append(("test_cache_functionality", self.test_cache_functionality))
        
        # 高级功能测试
        self.tests.append(("test_multiple_mappings", self.test_multiple_mappings))
        self.tests.append(("test_dynamic_mapping_updates", self.test_dynamic_mapping_updates))
        self.tests.append(("test_performance_metrics", self.test_performance_metrics))
        
        # 集成测试
        self.tests.append(("test_factory_pattern", self.test_factory_pattern))
        self.tests.append(("test_registry_integration", self.test_registry_integration))
        self.tests.append(("test_error_handling", self.test_error_handling))
    
    def test_basic_translation(self) -> Tuple[bool, str]:
        """测试基础路径翻译"""
        try:
            vps = VirtualPathSystem(VirtualPathConfig(base_dir="/tmp/base"))
            
            # 测试相对路径
            result = vps.translate("file.txt")
            expected = os.path.normpath("/tmp/base/file.txt")
            if result.real_path != expected:
                return False, f"相对路径翻译失败: {result.real_path} != {expected}"
            
            # 测试绝对路径
            result = vps.translate("/absolute/path/file.txt")
            if result.real_path != "/absolute/path/file.txt":
                return False, f"绝对路径翻译失败: {result.real_path}"
            
            return True, "基础路径翻译测试通过"
        except Exception as e:
            return False, f"基础路径翻译测试异常: {e}"
    
    def test_prefix_mapping(self) -> Tuple[bool, str]:
        """测试前缀映射"""
        try:
            vps = VirtualPathSystem(VirtualPathConfig(base_dir="/tmp/base"))
            
            # 添加前缀映射
            rule = PathMappingRule(
                virtual_path="/workspace",
                real_path="/tmp/workspace",
                mapping_type=PathMappingType.PREFIX,
                priority=10,
                description="工作空间映射"
            )
            vps.add_mapping(rule)
            
            # 测试映射
            result = vps.translate("/workspace/project/file.txt")
            expected = os.path.normpath("/tmp/workspace/project/file.txt")
            if result.real_path != expected:
                return False, f"前缀映射失败: {result.real_path} != {expected}"
            
            # 验证使用的映射规则
            if not result.mapping_rule or result.mapping_rule.virtual_path != "/workspace":
                return False, "映射规则未正确应用"
            
            return True, "前缀映射测试通过"
        except Exception as e:
            return False, f"前缀映射测试异常: {e}"
    
    def test_security_check(self) -> Tuple[bool, str]:
        """测试安全检测"""
        try:
            # 创建严格安全检测的系统
            config = VirtualPathConfig(
                base_dir="/tmp/base",
                security_level=PathSecurityLevel.STRICT
            )
            vps = VirtualPathSystem(config)
            
            # 测试安全路径
            result = vps.translate("safe/path/file.txt")
            if not result.security_check_passed:
                return False, "安全路径被错误阻止"
            
            # 测试路径遍历攻击
            try:
                vps.translate("../etc/passwd")
                return False, "路径遍历攻击未被检测到"
            except PathTraversalError:
                pass  # 预期行为
            
            # 测试其他可疑路径
            try:
                vps.translate("//double/slash")
                return False, "双斜杠路径未被检测到"
            except PathTraversalError:
                pass
            
            return True, "安全检测测试通过"
        except Exception as e:
            return False, f"安全检测测试异常: {e}"
    
    def test_cache_functionality(self) -> Tuple[bool, str]:
        """测试缓存功能"""
        try:
            config = VirtualPathConfig(
                base_dir="/tmp/base",
                enable_cache=True,
                cache_size=10
            )
            vps = VirtualPathSystem(config)
            
            # 第一次翻译（应该缓存未命中）
            result1 = vps.translate("file.txt")
            if result1.cache_hit:
                return False, "第一次翻译不应命中缓存"
            
            # 第二次翻译相同路径（应该缓存命中）
            result2 = vps.translate("file.txt")
            if not result2.cache_hit:
                return False, "第二次翻译应命中缓存"
            
            # 验证结果相同
            if result1.real_path != result2.real_path:
                return False, "缓存结果不一致"
            
            # 清空缓存后再次翻译
            vps.clear_cache()
            result3 = vps.translate("file.txt")
            if result3.cache_hit:
                return False, "清空缓存后不应命中缓存"
            
            # 检查缓存统计
            metrics = vps.get_metrics()
            if metrics.cache_hits < 1 or metrics.cache_misses < 2:
                return False, f"缓存统计不正确: hits={metrics.cache_hits}, misses={metrics.cache_misses}"
            
            return True, "缓存功能测试通过"
        except Exception as e:
            return False, f"缓存功能测试异常: {e}"
    
    def test_multiple_mappings(self) -> Tuple[bool, str]:
        """测试多个映射规则"""
        try:
            vps = VirtualPathSystem(VirtualPathConfig(base_dir="/tmp/base"))
            
            # 添加多个映射规则
            rules = [
                PathMappingRule("/app", "/opt/app", priority=5),
                PathMappingRule("/app/data", "/var/data", priority=10),  # 更高优先级
                PathMappingRule("/app/config", "/etc/app", priority=5),
            ]
            
            for rule in rules:
                vps.add_mapping(rule)
            
            # 测试优先级：高优先级规则应优先匹配
            result = vps.translate("/app/data/logs/app.log")
            expected = os.path.normpath("/var/data/logs/app.log")
            if result.real_path != expected:
                return False, f"优先级测试失败: {result.real_path} != {expected}"
            
            # 测试低优先级规则
            result = vps.translate("/app/config/app.conf")
            expected = os.path.normpath("/etc/app/app.conf")
            if result.real_path != expected:
                return False, f"低优先级规则失败: {result.real_path} != {expected}"
            
            # 测试未匹配的路径（应使用基础目录）
            result = vps.translate("/other/path/file.txt")
            expected = os.path.normpath("/tmp/base/other/path/file.txt")
            if result.real_path != expected:
                return False, f"默认映射失败: {result.real_path} != {expected}"
            
            return True, "多个映射规则测试通过"
        except Exception as e:
            return False, f"多个映射规则测试异常: {e}"
    
    def test_dynamic_mapping_updates(self) -> Tuple[bool, str]:
        """测试动态映射更新"""
        try:
            vps = VirtualPathSystem(VirtualPathConfig(base_dir="/tmp/base"))
            
            # 初始映射
            rule1 = PathMappingRule("/old", "/tmp/old", priority=5)
            vps.add_mapping(rule1)
            
            result1 = vps.translate("/old/file.txt")
            expected1 = os.path.normpath("/tmp/old/file.txt")
            if result1.real_path != expected1:
                return False, f"初始映射失败: {result1.real_path} != {expected1}"
            
            # 更新映射（相同虚拟路径，不同实际路径）
            rule2 = PathMappingRule("/old", "/tmp/new", priority=5)
            vps.add_mapping(rule2)  # 应该更新现有规则
            
            result2 = vps.translate("/old/file.txt")
            expected2 = os.path.normpath("/tmp/new/file.txt")
            if result2.real_path != expected2:
                return False, f"映射更新失败: {result2.real_path} != {expected2}"
            
            # 禁用映射规则
            rule2.enabled = False
            vps.add_mapping(rule2)
            
            # 禁用后应使用基础目录
            result3 = vps.translate("/old/file.txt")
            expected3 = os.path.normpath("/tmp/base/old/file.txt")
            if result3.real_path != expected3:
                return False, f"禁用映射失败: {result3.real_path} != {expected3}"
            
            # 移除映射规则
            vps.remove_mapping("/old")
            
            # 移除后应使用基础目录
            result4 = vps.translate("/old/file.txt")
            expected4 = os.path.normpath("/tmp/base/old/file.txt")
            if result4.real_path != expected4:
                return False, f"移除映射失败: {result4.real_path} != {expected4}"
            
            return True, "动态映射更新测试通过"
        except Exception as e:
            return False, f"动态映射更新测试异常: {e}"
    
    def test_performance_metrics(self) -> Tuple[bool, str]:
        """测试性能指标"""
        try:
            config = VirtualPathConfig(
                base_dir="/tmp/base",
                enable_cache=True,
                cache_size=100
            )
            vps = VirtualPathSystem(config)
            
            # 执行多次翻译以收集指标
            paths = ["file1.txt", "file2.txt", "file3.txt", "file1.txt", "file2.txt"]
            
            for path in paths:
                try:
                    vps.translate(path)
                except Exception:
                    pass
            
            # 获取指标
            metrics = vps.get_metrics()
            
            # 验证基本指标
            if metrics.total_translations != len(paths):
                return False, f"总翻译次数不正确: {metrics.total_translations} != {len(paths)}"
            
            if metrics.cache_hits < 0 or metrics.cache_misses < 0:
                return False, f"缓存统计不正确: hits={metrics.cache_hits}, misses={metrics.cache_misses}"
            
            if metrics.average_translation_time < 0:
                return False, f"平均翻译时间为负: {metrics.average_translation_time}"
            
            # 验证缓存命中率计算
            hit_rate = metrics.hit_rate()
            if not (0 <= hit_rate <= 1):
                return False, f"缓存命中率超出范围: {hit_rate}"
            
            return True, "性能指标测试通过"
        except Exception as e:
            return False, f"性能指标测试异常: {e}"
    
    def test_factory_pattern(self) -> Tuple[bool, str]:
        """测试工厂模式"""
        try:
            # 测试标准系统
            standard_config = {"base_dir": "/tmp/standard"}
            standard_vps = VirtualPathSystemFactory.create_standard(standard_config)
            result = standard_vps.translate("file.txt")
            if not result.real_path.endswith("/tmp/standard/file.txt"):
                return False, "标准系统创建失败"
            
            # 测试安全系统
            secure_config = {"base_dir": "/tmp/secure"}
            secure_vps = VirtualPathSystemFactory.create_secure(secure_config)
            if secure_vps.config.security_level != PathSecurityLevel.PARANOID:
                return False, "安全系统配置不正确"
            
            # 测试高性能系统
            perf_config = {"base_dir": "/tmp/perf"}
            perf_vps = VirtualPathSystemFactory.create_high_performance(perf_config)
            if not perf_vps.config.enable_cache:
                return False, "高性能系统缓存未启用"
            
            # 测试配置驱动创建
            config_data = {
                "type": "secure",
                "config": {"base_dir": "/tmp/config"}
            }
            config_vps = VirtualPathSystemFactory.create_from_config(config_data)
            if config_vps.config.security_level != PathSecurityLevel.PARANOID:
                return False, "配置驱动创建失败"
            
            return True, "工厂模式测试通过"
        except Exception as e:
            return False, f"工厂模式测试异常: {e}"
    
    def test_registry_integration(self) -> Tuple[bool, str]:
        """测试注册表集成"""
        try:
            registry = VirtualPathRegistry("test_registry")
            
            # 创建并注册多个系统
            system1 = VirtualPathSystemFactory.create_standard({"base_dir": "/tmp/sys1"})
            system2 = VirtualPathSystemFactory.create_secure({"base_dir": "/tmp/sys2"})
            
            if not registry.register("system1", system1):
                return False, "系统1注册失败"
            
            if not registry.register("system2", system2):
                return False, "系统2注册失败"
            
            # 测试重复注册
            if registry.register("system1", system1):
                return False, "重复注册应失败"
            
            # 测试获取系统
            retrieved = registry.get("system1")
            if retrieved is not system1:
                return False, "获取的系统不一致"
            
            # 测试列表功能
            systems_list = registry.list_all()
            if len(systems_list) != 2:
                return False, f"系统列表数量不正确: {len(systems_list)}"
            
            # 测试注销
            if not registry.unregister("system1"):
                return False, "系统注销失败"
            
            if registry.get("system1") is not None:
                return False, "注销后系统仍可访问"
            
            return True, "注册表集成测试通过"
        except Exception as e:
            return False, f"注册表集成测试异常: {e}"
    
    def test_error_handling(self) -> Tuple[bool, str]:
        """测试错误处理"""
        try:
            vps = VirtualPathSystem(VirtualPathConfig(base_dir="/tmp/base"))
            
            # 测试过长路径
            long_path = "a" * 5000
            try:
                vps.translate(long_path)
                return False, "过长路径未触发错误"
            except VirtualPathError:
                pass  # 预期行为
            
            # 测试不存在的映射
            try:
                vps.translate("/nonexistent/path")
                # 不应触发错误，应使用基础目录
            except Exception as e:
                return False, f"不存在的映射不应触发错误: {e}"
            
            # 测试无效的正则映射
            invalid_rule = PathMappingRule(
                virtual_path="[invalid-regex",
                real_path="/tmp/target",
                mapping_type=PathMappingType.REGEX
            )
            vps.add_mapping(invalid_rule)
            
            try:
                vps.translate("[invalid-regex")
                # 正则错误应在翻译时捕获
            except VirtualPathError:
                pass  # 预期行为
            
            return True, "错误处理测试通过"
        except Exception as e:
            return False, f"错误处理测试异常: {e}"
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行虚拟路径系统测试套件...")
        print("=" * 60)
        
        total_tests = len(self.tests)
        passed_tests = 0
        failed_tests = 0
        detailed_results = {}
        
        for test_name, test_func in self.tests:
            print(f"📋 运行测试: {test_name}...")
            start_time = time.perf_counter()
            
            try:
                passed, message = test_func()
                elapsed = time.perf_counter() - start_time
                
                if passed:
                    print(f"   ✅ 通过 ({elapsed:.3f}s): {message}")
                    passed_tests += 1
                else:
                    print(f"   ❌ 失败 ({elapsed:.3f}s): {message}")
                    failed_tests += 1
                
                detailed_results[test_name] = {
                    "passed": passed,
                    "message": message,
                    "execution_time": elapsed
                }
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                print(f"   💥 异常 ({elapsed:.3f}s): {e}")
                failed_tests += 1
                detailed_results[test_name] = {
                    "passed": False,
                    "message": f"测试异常: {e}",
                    "execution_time": elapsed,
                    "error": str(e)
                }
        
        print("=" * 60)
        print(f"📊 测试摘要:")
        print(f"   总测试数: {total_tests}")
        print(f"   通过测试: {passed_tests}")
        print(f"   失败测试: {failed_tests}")
        print(f"   成功率: {passed_tests/total_tests*100:.1f}%")
        print()
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests/total_tests*100,
            },
            "detailed_results": detailed_results
        }


def main_demo() -> None:
    """主演示函数"""
    print("=" * 80)
    print("🎓 Day 9 Lesson 33: 虚拟路径系统架构演示")
    print("=" * 80)
    print()
    
    # 创建临时目录用于演示
    temp_dir = tempfile.mkdtemp(prefix="virtual_path_demo_")
    base_dir = os.path.join(temp_dir, "base")
    workspace_dir = os.path.join(temp_dir, "workspace")
    data_dir = os.path.join(temp_dir, "data")
    
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(workspace_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    
    try:
        print("1. 创建虚拟路径系统实例...")
        config = VirtualPathConfig(
            base_dir=base_dir,
            security_level=PathSecurityLevel.STRICT,
            enable_cache=True,
            cache_size=100,
            enable_audit_log=True,
            default_mappings=[
                {
                    "virtual_path": "/workspace",
                    "real_path": workspace_dir,
                    "mapping_type": "前缀匹配",
                    "priority": 10,
                    "description": "工作空间映射"
                },
                {
                    "virtual_path": "/data",
                    "real_path": data_dir,
                    "mapping_type": "前缀匹配",
                    "priority": 5,
                    "description": "数据目录映射"
                }
            ]
        )
        
        vps = VirtualPathSystem(config)
        print(f"   ✅ 创建成功")
        print(f"   基础目录: {config.base_dir}")
        print(f"   安全级别: {config.security_level.value}")
        print(f"   缓存启用: {config.enable_cache} (大小: {config.cache_size})")
        print(f"   审计日志: {config.enable_audit_log}")
        print()
        
        print("2. 基本路径翻译演示...")
        test_cases = [
            ("相对路径", "project/file.txt", os.path.join(base_dir, "project/file.txt")),
            ("绝对路径", "/usr/local/file.txt", "/usr/local/file.txt"),
            ("映射路径", "/workspace/src/main.py", os.path.join(workspace_dir, "src/main.py")),
            ("数据路径", "/data/logs/app.log", os.path.join(data_dir, "logs/app.log")),
        ]
        
        for desc, virtual_path, expected in test_cases:
            try:
                result = vps.translate(virtual_path)
                status = "✅" if result.real_path == os.path.normpath(expected) else "❌"
                print(f"   {status} {desc}: {virtual_path} -> {result.real_path}")
                print(f"      安全检测: {'通过' if result.security_check_passed else '失败'}")
                print(f"      缓存命中: {result.cache_hit}")
                print(f"      翻译时间: {result.translation_time:.6f}s")
                if result.mapping_rule:
                    print(f"      使用映射: {result.mapping_rule.virtual_path} -> {result.mapping_rule.real_path}")
            except Exception as e:
                print(f"   ❌ {desc}失败: {e}")
        print()
        
        print("3. 安全检测演示...")
        security_test_cases = [
            ("正常路径", "safe/path/file.txt", True),
            ("路径遍历", "../etc/passwd", False),
            ("双斜杠", "//suspicious/path", False),
            ("点目录", "././file.txt", True),  # 应该通过，但可能有警告
        ]
        
        for desc, virtual_path, should_pass in security_test_cases:
            try:
                result = vps.translate(virtual_path)
                if should_pass:
                    print(f"   ✅ {desc}: {virtual_path} - 安全通过")
                else:
                    print(f"   ❌ {desc}: {virtual_path} - 预期失败但通过了")
            except PathTraversalError as e:
                if not should_pass:
                    print(f"   ✅ {desc}: {virtual_path} - 安全阻止: {str(e)[:50]}...")
                else:
                    print(f"   ❌ {desc}: {virtual_path} - 预期通过但被阻止: {str(e)[:50]}...")
            except Exception as e:
                print(f"   ❌ {desc}异常: {e}")
        print()
        
        print("4. 动态映射管理演示...")
        
        # 添加新映射
        new_rule = PathMappingRule(
            virtual_path="/tmp",
            real_path="/tmp/demo",
            mapping_type=PathMappingType.PREFIX,
            priority=15,
            description="临时目录映射"
        )
        vps.add_mapping(new_rule)
        print(f"   ✅ 添加新映射: /tmp -> /tmp/demo")
        
        # 列出所有映射
        mappings = vps.list_mappings()
        print(f"   当前有效映射规则 ({len(mappings)} 个):")
        for i, rule in enumerate(mappings, 1):
            print(f"     {i}. {rule.virtual_path} -> {rule.real_path} (优先级: {rule.priority})")
        print()
        
        print("5. 性能指标演示...")
        
        # 执行一些翻译以收集指标
        for i in range(20):
            vps.translate(f"/workspace/file{i}.txt")
            if i % 3 == 0:
                vps.translate(f"/data/item{i}.dat")
        
        metrics = vps.get_metrics()
        print(f"   总翻译次数: {metrics.total_translations}")
        print(f"   成功翻译: {metrics.successful_translations}")
        print(f"   失败翻译: {metrics.failed_translations}")
        print(f"   缓存命中率: {metrics.hit_rate():.1%}")
        print(f"   平均翻译时间: {metrics.average_translation_time:.6f}s")
        print(f"   安全阻止次数: {metrics.security_blocks}")
        print()
        
        print("6. 工厂模式演示...")
        
        # 使用工厂创建不同类型系统
        standard_vps = VirtualPathSystemFactory.create_standard({"base_dir": "/tmp/standard"})
        secure_vps = VirtualPathSystemFactory.create_secure({"base_dir": "/tmp/secure"})
        perf_vps = VirtualPathSystemFactory.create_high_performance({"base_dir": "/tmp/perf"})
        
        print(f"   ✅ 创建标准系统: {standard_vps.config.security_level.value}")
        print(f"   ✅ 创建安全系统: {secure_vps.config.security_level.value}")
        print(f"   ✅ 创建高性能系统: 缓存大小={perf_vps.config.cache_size}")
        print()
        
        print("7. 注册表集成演示...")
        
        registry = VirtualPathRegistry("demo_registry")
        registry.register("standard", standard_vps)
        registry.register("secure", secure_vps)
        registry.register("performance", perf_vps)
        
        systems = registry.list_all()
        print(f"   注册表中系统数量: {len(systems)}")
        for sys_info in systems:
            print(f"     - {sys_info['name']}: 映射数={sys_info['mapping_count']}, 翻译次数={sys_info['metrics']['total_translations']}")
        print()
        
        print("8. 清理资源...")
        vps.clear_cache()
        print(f"   ✅ 清理完成")
        
    finally:
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir)
            print(f"   ✅ 清理临时目录: {temp_dir}")
        except Exception as e:
            print(f"   ⚠️  清理临时目录失败: {e}")
    
    print()
    print("=" * 80)
    print("🎉 虚拟路径系统架构演示完成！")
    print("=" * 80)


def run_tests() -> None:
    """运行测试套件"""
    print("=" * 80)
    print("🧪 虚拟路径系统测试套件")
    print("=" * 80)
    print()
    
    test_suite = VirtualPathTestSuite()
    report = test_suite.run_all_tests()
    
    summary = report["summary"]
    print("📋 最终测试结果:")
    print(f"   测试总数: {summary['total_tests']}")
    print(f"   通过测试: {summary['passed_tests']}")
    print(f"   失败测试: {summary['failed_tests']}")
    print(f"   成功率: {summary['success_rate']:.1f}%")
    print()
    
    if summary['success_rate'] >= 100.0:
        print("🎉 所有测试通过！虚拟路径系统实现正确。")
    else:
        print("⚠️  有测试失败，请检查实现代码。")
        
        # 显示失败详情
        print("\n📝 失败测试详情:")
        for test_name, test_result in report["detailed_results"].items():
            if not test_result["passed"]:
                print(f"   ❌ {test_name}: {test_result['message']}")
                if "error" in test_result:
                    print(f"       错误: {test_result['error']}")
    
    print()
    print("=" * 80)


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="虚拟路径系统架构演示程序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s                    # 运行基本演示
  %(prog)s --test            # 运行测试套件
  %(prog)s --demo            # 运行完整演示
  %(prog)s --help            # 显示帮助信息
  
演示功能:
  1. 虚拟路径系统基本使用和配置
  2. 路径映射规则管理（前缀、正则、精确、通配符）
  3. 安全检测机制（路径遍历攻击防护）
  4. 性能优化（缓存、指标监控）
  5. 工厂模式和注册表集成
  6. 完整测试套件验证
        """
    )
    
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="运行测试套件"
    )
    
    parser.add_argument(
        "--demo", 
        action="store_true", 
        help="运行完整演示"
    )
    
    args = parser.parse_args()
    
    if args.test:
        run_tests()
    elif args.demo:
        main_demo()
    else:
        # 默认运行基本演示
        print("虚拟路径系统架构演示程序")
        print("使用 --help 查看可用选项")
        print()
        
        # 创建一个简单示例
        vps = VirtualPathSystem(VirtualPathConfig(base_dir="/tmp/demo"))
        
        # 添加示例映射
        rule = PathMappingRule(
            virtual_path="/workspace",
            real_path="/tmp/workspace",
            priority=10
        )
        vps.add_mapping(rule)
        
        # 演示基本翻译
        print("示例翻译:")
        test_paths = ["file.txt", "/workspace/project/main.py", "../suspicious/path"]
        
        for path in test_paths:
            try:
                result = vps.translate(path)
                print(f"  {path} -> {result.real_path}")
                print(f"    安全: {'✅通过' if result.security_check_passed else '❌失败'}")
                print(f"    缓存: {'✅命中' if result.cache_hit else '❌未命中'}")
                print(f"    时间: {result.translation_time:.6f}s")
            except PathTraversalError as e:
                print(f"  {path} -> ❌安全阻止: {str(e)[:50]}...")
            except Exception as e:
                print(f"  {path} -> ❌错误: {e}")
        
        print()
        print("更多功能请使用 --demo 或 --test 选项")


if __name__ == "__main__":
    main()