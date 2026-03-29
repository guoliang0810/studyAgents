#!/usr/bin/env python3
"""
Day 14 - 第55节课：记忆配置管理
================================

本演示代码实现记忆配置管理系统，包括：
1. EnhancedMemoryConfig - 增强的内存配置管理类
2. 四层配置结构：默认、文件、环境变量、运行时
3. 优先级规则系统和冲突解决
4. 动态配置调整和热加载

运行方式:
    python memory_config_management_demo.py          # 运行演示
    python memory_config_management_demo.py --test   # 运行测试
"""

import os
import sys
import time
import json
import yaml
import threading
import hashlib
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import tempfile
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# ============================================================================
# 第一部分：数据模型和枚举定义
# ============================================================================

class ConfigLayer(Enum):
    """配置层枚举"""
    DEFAULT = "default"      # 默认配置（最低优先级）
    FILE = "file"           # 配置文件
    ENV = "env"             # 环境变量
    RUNTIME = "runtime"     # 运行时配置（最高优先级）
    OVERRIDE = "override"   # 临时覆盖配置（特殊用途）


class ConfigFormat(Enum):
    """配置格式枚举"""
    YAML = "yaml"
    JSON = "json"
    INI = "ini"
    ENV = "env"  # 环境变量格式


class ConfigSecurityLevel(Enum):
    """配置安全级别"""
    PUBLIC = "public"       # 公开配置
    INTERNAL = "internal"   # 内部配置
    SECRET = "secret"       # 秘密配置
    ENCRYPTED = "encrypted" # 加密配置


@dataclass
class ConfigEntry:
    """配置条目"""
    key: str
    value: Any
    layer: ConfigLayer
    timestamp: float = field(default_factory=time.time)
    security_level: ConfigSecurityLevel = ConfigSecurityLevel.PUBLIC
    source: str = ""  # 来源描述，如文件路径、环境变量名等
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # 自动设置来源描述
        if not self.source:
            if self.layer == ConfigLayer.ENV:
                self.source = f"env:{self.key}"
            elif self.layer == ConfigLayer.FILE:
                self.source = "config_file"
            elif self.layer == ConfigLayer.RUNTIME:
                self.source = "runtime_set"
            elif self.layer == ConfigLayer.DEFAULT:
                self.source = "default"
            elif self.layer == ConfigLayer.OVERRIDE:
                self.source = "override"


@dataclass
class ConfigValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    fixed_values: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 第二部分：配置优先级规则系统
# ============================================================================

class PriorityRuleSystem:
    """配置优先级规则系统"""
    
    def __init__(self):
        # 默认优先级顺序（从高到低）
        self.default_order = [
            ConfigLayer.OVERRIDE,   # 临时覆盖最高优先级
            ConfigLayer.RUNTIME,    # 运行时配置
            ConfigLayer.ENV,        # 环境变量
            ConfigLayer.FILE,       # 配置文件
            ConfigLayer.DEFAULT,    # 默认配置最低优先级
        ]
        
        # 自定义规则
        self.custom_rules: List[Callable[[str, ConfigLayer, ConfigLayer], bool]] = []
    
    def get_priority(self, layer: ConfigLayer) -> int:
        """获取配置层优先级（数字越小优先级越高）"""
        try:
            return self.default_order.index(layer)
        except ValueError:
            return 100  # 未知层最低优先级
    
    def compare_layers(self, layer1: ConfigLayer, layer2: ConfigLayer) -> int:
        """比较两个配置层的优先级"""
        priority1 = self.get_priority(layer1)
        priority2 = self.get_priority(layer2)
        
        if priority1 < priority2:
            return -1  # layer1优先级更高
        elif priority1 > priority2:
            return 1   # layer2优先级更高
        else:
            return 0   # 优先级相同
    
    def add_custom_rule(self, rule_func: Callable[[str, ConfigLayer, ConfigLayer], bool]):
        """添加自定义优先级规则"""
        self.custom_rules.append(rule_func)
    
    def resolve_conflict(self, key: str, entries: List[ConfigEntry]) -> ConfigEntry:
        """解决配置冲突，返回应使用的条目"""
        if not entries:
            raise ValueError("没有配置条目可解析")
        
        if len(entries) == 1:
            return entries[0]
        
        # 按优先级排序
        sorted_entries = sorted(
            entries,
            key=lambda e: self.get_priority(e.layer)
        )
        
        # 应用自定义规则
        for rule in self.custom_rules:
            for i in range(len(sorted_entries) - 1):
                higher = sorted_entries[i]
                lower = sorted_entries[i + 1]
                
                # 如果自定义规则认为lower应该优先
                if rule(key, higher.layer, lower.layer):
                    # 交换位置
                    sorted_entries[i], sorted_entries[i + 1] = (
                        sorted_entries[i + 1], sorted_entries[i]
                    )
        
        # 返回最高优先级的条目
        return sorted_entries[0]
    
    def get_conflict_report(self, key: str, entries: List[ConfigEntry]) -> Dict[str, Any]:
        """生成配置冲突报告"""
        sorted_entries = sorted(
            entries,
            key=lambda e: self.get_priority(e.layer)
        )
        
        return {
            "key": key,
            "total_entries": len(entries),
            "selected_entry": {
                "value": sorted_entries[0].value,
                "layer": sorted_entries[0].layer.value,
                "source": sorted_entries[0].source,
                "timestamp": sorted_entries[0].timestamp
            },
            "all_entries": [
                {
                    "value": e.value,
                    "layer": e.layer.value,
                    "source": e.source,
                    "timestamp": e.timestamp,
                    "priority": self.get_priority(e.layer)
                }
                for e in sorted_entries
            ]
        }


# ============================================================================
# 第三部分：配置验证器
# ============================================================================

class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        self.validators: Dict[str, List[Callable[[Any], bool]]] = {}
        self.type_checks: Dict[str, type] = {}
        self.value_ranges: Dict[str, tuple] = {}
        self.required_keys: List[str] = []
    
    def add_type_check(self, key: str, expected_type: type):
        """添加类型检查"""
        self.type_checks[key] = expected_type
    
    def add_value_range(self, key: str, min_val: Optional[Any] = None, 
                       max_val: Optional[Any] = None):
        """添加值范围检查"""
        self.value_ranges[key] = (min_val, max_val)
    
    def add_custom_validator(self, key: str, validator: Callable[[Any], bool]):
        """添加自定义验证器"""
        if key not in self.validators:
            self.validators[key] = []
        self.validators[key].append(validator)
    
    def set_required_keys(self, keys: List[str]):
        """设置必填键"""
        self.required_keys = keys
    
    def validate(self, config: Dict[str, Any]) -> ConfigValidationResult:
        """验证配置"""
        errors = []
        warnings = []
        fixed_values = {}
        
        # 检查必填键
        for key in self.required_keys:
            if key not in config:
                errors.append(f"缺少必填配置项: {key}")
        
        # 检查每个配置项
        for key, value in config.items():
            # 类型检查
            if key in self.type_checks:
                expected_type = self.type_checks[key]
                if not isinstance(value, expected_type):
                    # 尝试类型转换
                    try:
                        converted = self._convert_type(value, expected_type)
                        fixed_values[key] = converted
                        warnings.append(f"配置项 {key} 类型自动转换: {type(value).__name__} -> {expected_type.__name__}")
                    except (ValueError, TypeError):
                        errors.append(f"配置项 {key} 类型错误: 期望 {expected_type.__name__}, 实际 {type(value).__name__}")
            
            # 值范围检查
            if key in self.value_ranges:
                min_val, max_val = self.value_ranges[key]
                if min_val is not None and value < min_val:
                    errors.append(f"配置项 {key} 值太小: {value} < {min_val}")
                if max_val is not None and value > max_val:
                    errors.append(f"配置项 {key} 值太大: {value} > {max_val}")
            
            # 自定义验证器
            if key in self.validators:
                for validator in self.validators[key]:
                    if not validator(value):
                        errors.append(f"配置项 {key} 自定义验证失败: {value}")
        
        is_valid = len(errors) == 0
        
        return ConfigValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            fixed_values=fixed_values
        )
    
    def _convert_type(self, value: Any, target_type: type) -> Any:
        """类型转换"""
        if target_type == str:
            return str(value)
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == bool:
            if isinstance(value, str):
                return value.lower() in ("true", "yes", "1", "on")
            else:
                return bool(value)
        elif target_type == list:
            if isinstance(value, str):
                # 尝试解析逗号分隔的列表
                return [item.strip() for item in value.split(",") if item.strip()]
            else:
                return list(value)
        elif target_type == dict:
            if isinstance(value, str):
                # 尝试解析JSON
                return json.loads(value)
            else:
                return dict(value)
        else:
            raise TypeError(f"不支持的类型转换: {type(value)} -> {target_type}")


# ============================================================================
# 第四部分：配置安全管理器
# ============================================================================

class ConfigSecurityManager:
    """配置安全管理器"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key
        self.masked_keys: List[str] = []  # 需要掩码的键（日志中隐藏值）
        self.encrypted_keys: List[str] = []  # 需要加密存储的键
    
    def mask_sensitive_value(self, key: str, value: Any) -> Any:
        """掩码敏感值（用于日志显示）"""
        if key in self.masked_keys:
            if isinstance(value, str):
                if len(value) <= 4:
                    return "***"
                else:
                    return value[:2] + "***" + value[-2:]
            else:
                return "***"
        return value
    
    def encrypt_value(self, key: str, value: Any) -> Any:
        """加密值（简化实现）"""
        if key in self.encrypted_keys and self.encryption_key:
            if isinstance(value, str):
                # 简单加密示例（实际应使用更强的加密算法）
                import base64
                encoded = base64.b64encode(value.encode()).decode()
                return f"encrypted:{encoded}"
            else:
                # 非字符串值转换为JSON再加密
                import base64
                json_str = json.dumps(value)
                encoded = base64.b64encode(json_str.encode()).decode()
                return f"encrypted:{encoded}"
        return value
    
    def decrypt_value(self, key: str, value: Any) -> Any:
        """解密值"""
        if isinstance(value, str) and value.startswith("encrypted:") and self.encryption_key:
            try:
                import base64
                encoded = value.split(":", 1)[1]
                decoded = base64.b64decode(encoded).decode()
                
                # 尝试解析JSON
                try:
                    return json.loads(decoded)
                except json.JSONDecodeError:
                    return decoded
            except:
                return value  # 解密失败返回原值
        return value
    
    def add_masked_key(self, key: str):
        """添加需要掩码的键"""
        if key not in self.masked_keys:
            self.masked_keys.append(key)
    
    def add_encrypted_key(self, key: str):
        """添加需要加密的键"""
        if key not in self.encrypted_keys:
            self.encrypted_keys.append(key)
    
    def get_safe_for_logging(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """获取安全的配置（用于日志）"""
        safe_config = {}
        for key, value in config.items():
            safe_config[key] = self.mask_sensitive_value(key, value)
        return safe_config


# ============================================================================
# 第五部分：增强的内存配置管理类
# ============================================================================

class EnhancedMemoryConfig:
    """增强的内存配置管理类"""
    
    def __init__(self, default_config: Optional[Dict[str, Any]] = None):
        # 配置存储：key -> List[ConfigEntry]
        self._config_store: Dict[str, List[ConfigEntry]] = {}
        
        # 子系统
        self.priority_system = PriorityRuleSystem()
        self.validator = ConfigValidator()
        self.security_manager = ConfigSecurityManager()
        
        # 默认配置
        self._default_config = default_config or {
            "memory.max_size": 1000,
            "memory.ttl_seconds": 3600,
            "injection.max_facts": 10,
            "injection.min_confidence": 0.5,
            "performance.cache_size": 100,
            "performance.enable_async": True,
            "logging.level": "INFO",
            "security.encryption_enabled": False,
        }
        
        # 加载默认配置
        self._load_defaults()
        
        # 热加载相关
        self._file_watchers: Dict[str, Observer] = {}
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._lock = threading.RLock()
        
        # 配置变更历史
        self._change_history: List[Dict[str, Any]] = []
    
    def _load_defaults(self):
        """加载默认配置"""
        for key, value in self._default_config.items():
            self._set_entry(
                ConfigEntry(
                    key=key,
                    value=value,
                    layer=ConfigLayer.DEFAULT,
                    source="builtin_defaults"
                )
            )
    
    def _set_entry(self, entry: ConfigEntry):
        """设置配置条目（内部方法）"""
        with self._lock:
            if entry.key not in self._config_store:
                self._config_store[entry.key] = []
            
            # 添加条目
            self._config_store[entry.key].append(entry)
            
            # 记录变更历史
            self._record_change(entry)
    
    def _record_change(self, entry: ConfigEntry):
        """记录配置变更"""
        change_record = {
            "timestamp": time.time(),
            "key": entry.key,
            "value": self.security_manager.mask_sensitive_value(entry.key, entry.value),
            "layer": entry.layer.value,
            "source": entry.source,
            "action": "set"
        }
        self._change_history.append(change_record)
        
        # 限制历史记录大小
        if len(self._change_history) > 1000:
            self._change_history = self._change_history[-1000:]
    
    def load_from_file(self, filepath: str, format: ConfigFormat = ConfigFormat.YAML):
        """从文件加载配置"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                if format == ConfigFormat.YAML:
                    data = yaml.safe_load(f)
                elif format == ConfigFormat.JSON:
                    data = json.load(f)
                elif format == ConfigFormat.INI:
                    # 简化INI解析
                    import configparser
                    parser = configparser.ConfigParser()
                    parser.read(filepath)
                    data = {}
                    for section in parser.sections():
                        for key, value in parser.items(section):
                            data[f"{section}.{key}"] = value
                else:
                    raise ValueError(f"不支持的格式: {format}")
            
            # 验证配置
            validation = self.validator.validate(data)
            if not validation.is_valid:
                print(f"配置文件验证失败: {validation.errors}")
                # 使用修复后的值
                data.update(validation.fixed_values)
            
            # 添加到配置存储
            for key, value in data.items():
                # 加密敏感值
                safe_value = self.security_manager.encrypt_value(key, value)
                
                entry = ConfigEntry(
                    key=key,
                    value=safe_value,
                    layer=ConfigLayer.FILE,
                    source=filepath,
                    security_level=self._determine_security_level(key, value)
                )
                self._set_entry(entry)
            
            # 设置文件监视（热加载）
            self._setup_file_watcher(filepath)
            
            return True
            
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False
    
    def load_from_env(self, prefix: str = "MEMORY_"):
        """从环境变量加载配置"""
        env_vars = {k: v for k, v in os.environ.items() if k.startswith(prefix)}
        
        for env_key, env_value in env_vars.items():
            # 转换键名：MEMORY_MAX_SIZE -> memory.max_size
            config_key = env_key[len(prefix):].lower().replace('_', '.')
            
            # 尝试推断类型
            typed_value = self._infer_type(env_value)
            
            # 加密敏感值
            safe_value = self.security_manager.encrypt_value(config_key, typed_value)
            
            entry = ConfigEntry(
                key=config_key,
                value=safe_value,
                layer=ConfigLayer.ENV,
                source=f"env:{env_key}",
                security_level=self._determine_security_level(config_key, typed_value)
            )
            self._set_entry(entry)
        
        return len(env_vars)
    
    def _infer_type(self, value: str) -> Any:
        """推断字符串值的类型"""
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        elif value.isdigit():
            return int(value)
        elif self._is_float(value):
            return float(value)
        elif value.startswith("[") and value.endswith("]"):
            # 简单列表解析
            try:
                return json.loads(value)
            except:
                return [item.strip() for item in value[1:-1].split(",") if item.strip()]
        elif value.startswith("{") and value.endswith("}"):
            # 简单字典解析
            try:
                return json.loads(value)
            except:
                return value
        else:
            return value
    
    def _is_float(self, value: str) -> bool:
        """检查字符串是否为浮点数"""
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def _determine_security_level(self, key: str, value: Any) -> ConfigSecurityLevel:
        """确定配置安全级别"""
        sensitive_keywords = ["password", "secret", "key", "token", "credential"]
        if any(kw in key.lower() for kw in sensitive_keywords):
            return ConfigSecurityLevel.SECRET
        elif "internal" in key.lower() or "private" in key.lower():
            return ConfigSecurityLevel.INTERNAL
        else:
            return ConfigSecurityLevel.PUBLIC
    
    def set_runtime(self, key: str, value: Any, source: str = "runtime"):
        """设置运行时配置"""
        # 加密敏感值
        safe_value = self.security_manager.encrypt_value(key, value)
        
        entry = ConfigEntry(
            key=key,
            value=safe_value,
            layer=ConfigLayer.RUNTIME,
            source=source,
            security_level=self._determine_security_level(key, value)
        )
        self._set_entry(entry)
        
        # 触发回调
        self._trigger_callbacks({key: value})
    
    def override(self, key: str, value: Any, reason: str = ""):
        """临时覆盖配置（最高优先级）"""
        entry = ConfigEntry(
            key=key,
            value=value,
            layer=ConfigLayer.OVERRIDE,
            source=f"override:{reason}",
            security_level=ConfigSecurityLevel.INTERNAL
        )
        self._set_entry(entry)
        
        # 触发回调
        self._trigger_callbacks({key: value})
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（考虑优先级）"""
        with self._lock:
            if key not in self._config_store:
                return default
            
            entries = self._config_store[key]
            selected = self.priority_system.resolve_conflict(key, entries)
            
            # 解密值
            decrypted_value = self.security_manager.decrypt_value(key, selected.value)
            return decrypted_value
    
    def get_with_metadata(self, key: str) -> Dict[str, Any]:
        """获取配置值及其元数据"""
        with self._lock:
            if key not in self._config_store:
                return {
                    "value": None,
                    "exists": False,
                    "layer": None,
                    "source": None,
                    "security_level": None
                }
            
            entries = self._config_store[key]
            selected = self.priority_system.resolve_conflict(key, entries)
            
            # 解密值
            decrypted_value = self.security_manager.decrypt_value(key, selected.value)
            
            return {
                "value": decrypted_value,
                "exists": True,
                "layer": selected.layer.value,
                "source": selected.source,
                "security_level": selected.security_level.value,
                "timestamp": selected.timestamp,
                "all_entries": [
                    {
                        "value": self.security_manager.mask_sensitive_value(key, e.value),
                        "layer": e.layer.value,
                        "source": e.source
                    }
                    for e in entries
                ]
            }
    
    def get_all(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """获取所有配置"""
        with self._lock:
            result = {}
            for key in self._config_store.keys():
                value = self.get(key)
                if include_sensitive:
                    result[key] = value
                else:
                    result[key] = self.security_manager.mask_sensitive_value(key, value)
            return result
    
    def get_conflict_report(self, key: str) -> Optional[Dict[str, Any]]:
        """获取配置冲突报告"""
        with self._lock:
            if key not in self._config_store:
                return None
            
            entries = self._config_store[key]
            if len(entries) <= 1:
                return None
            
            return self.priority_system.get_conflict_report(key, entries)
    
    def reload_file(self, filepath: str):
        """重新加载配置文件"""
        # 先清除该文件的所有配置
        with self._lock:
            keys_to_remove = []
            for key, entries in self._config_store.items():
                new_entries = [e for e in entries if e.source != filepath]
                if len(new_entries) != len(entries):
                    self._config_store[key] = new_entries
                    if not new_entries:
                        keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._config_store[key]
        
        # 重新加载文件
        return self.load_from_file(filepath)
    
    def _setup_file_watcher(self, filepath: str):
        """设置文件监视器（热加载）"""
        if filepath in self._file_watchers:
            return
        
        class ConfigFileHandler(FileSystemEventHandler):
            def __init__(self, config_manager, filepath):
                self.config_manager = config_manager
                self.filepath = filepath
                self.last_modified = os.path.getmtime(filepath)
            
            def on_modified(self, event):
                if event.src_path == self.filepath:
                    current_modified = os.path.getmtime(self.filepath)
                    # 防止重复触发
                    if current_modified > self.last_modified + 0.5:  # 0.5秒防抖
                        self.last_modified = current_modified
                        print(f"配置文件已修改，重新加载: {self.filepath}")
                        self.config_manager.reload_file(self.filepath)
        
        handler = ConfigFileHandler(self, filepath)
        observer = Observer()
        observer.schedule(handler, path=os.path.dirname(filepath), recursive=False)
        observer.start()
        
        self._file_watchers[filepath] = observer
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """注册配置变更回调"""
        self._callbacks.append(callback)
    
    def _trigger_callbacks(self, changed_config: Dict[str, Any]):
        """触发配置变更回调"""
        for callback in self._callbacks:
            try:
                callback(changed_config)
            except Exception as e:
                print(f"配置变更回调执行失败: {e}")
    
    def validate_all(self) -> ConfigValidationResult:
        """验证所有配置"""
        all_config = self.get_all(include_sensitive=True)
        return self.validator.validate(all_config)
    
    def get_change_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取配置变更历史"""
        return self._change_history[-limit:] if self._change_history else []
    
    def clear_overrides(self):
        """清除所有覆盖配置"""
        with self._lock:
            for key, entries in list(self._config_store.items()):
                new_entries = [e for e in entries if e.layer != ConfigLayer.OVERRIDE]
                if new_entries:
                    self._config_store[key] = new_entries
                else:
                    del self._config_store[key]
    
    def export_config(self, format: ConfigFormat = ConfigFormat.YAML) -> str:
        """导出配置"""
        config = self.get_all(include_sensitive=False)
        
        if format == ConfigFormat.YAML:
            return yaml.dump(config, default_flow_style=False, allow_unicode=True)
        elif format == ConfigFormat.JSON:
            return json.dumps(config, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的导出格式: {format}")


# ============================================================================
# 第六部分：测试套件
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("🧪 运行记忆配置管理测试套件")
    print("=" * 60)
    
    passed, total = 0, 8
    
    # 测试1: 基础配置加载
    print("\n📊 测试1: 基础配置加载")
    try:
        config = EnhancedMemoryConfig()
        config.set_runtime("test.key", "value")
        assert config.get("test.key") == "value"
        print("   ✅ 基础配置加载正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试2: 优先级规则
    print("\n📊 测试2: 优先级规则")
    try:
        config = EnhancedMemoryConfig()
        config.set_runtime("priority.test", "runtime_value")
        # 模拟文件配置（较低优先级）
        config._set_entry(ConfigEntry(
            key="priority.test",
            value="file_value",
            layer=ConfigLayer.FILE,
            source="test_file"
        ))
        assert config.get("priority.test") == "runtime_value"  # runtime优先级更高
        print("   ✅ 优先级规则正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试3: 环境变量加载
    print("\n📊 测试3: 环境变量加载")
    try:
        import os
        os.environ["MEMORY_TEST_ENV"] = "env_value"
        
        config = EnhancedMemoryConfig()
        count = config.load_from_env(prefix="MEMORY_")
        assert count >= 1
        assert config.get("test.env") == "env_value"
        print("   ✅ 环境变量加载正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试4: 类型推断
    print("\n📊 测试4: 类型推断")
    try:
        config = EnhancedMemoryConfig()
        config.set_runtime("test.int", "123")
        config.set_runtime("test.bool", "true")
        config.set_runtime("test.float", "3.14")
        
        assert isinstance(config.get("test.int"), int)
        assert isinstance(config.get("test.bool"), bool)
        assert isinstance(config.get("test.float"), float)
        print("   ✅ 类型推断正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试5: 配置验证
    print("\n📊 测试5: 配置验证")
    try:
        config = EnhancedMemoryConfig()
        config.validator.add_type_check("validation.test", int)
        config.set_runtime("validation.test", "not_a_number")
        
        result = config.validate_all()
        assert not result.is_valid  # 应该有验证错误
        print("   ✅ 配置验证正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试6: 安全掩码
    print("\n📊 测试6: 安全掩码")
    try:
        config = EnhancedMemoryConfig()
        config.security_manager.add_masked_key("secret.key")
        config.set_runtime("secret.key", "my_password")
        
        safe_config = config.security_manager.get_safe_for_logging(
            {"secret.key": "my_password"}
        )
        assert "***" in str(safe_config["secret.key"])  # 值被掩码
        print("   ✅ 安全掩码正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试7: 配置冲突报告
    print("\n📊 测试7: 配置冲突报告")
    try:
        config = EnhancedMemoryConfig()
        config.set_runtime("conflict.test", "value1")
        config._set_entry(ConfigEntry(
            key="conflict.test",
            value="value2",
            layer=ConfigLayer.FILE,
            source="file1"
        ))
        config._set_entry(ConfigEntry(
            key="conflict.test",
            value="value3",
            layer=ConfigLayer.ENV,
            source="env"
        ))
        
        report = config.get_conflict_report("conflict.test")
        assert report is not None
        assert report["total_entries"] == 3
        print("   ✅ 配置冲突报告正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试8: 配置导出
    print("\n📊 测试8: 配置导出")
    try:
        config = EnhancedMemoryConfig()
        config.set_runtime("export.test", "export_value")
        
        yaml_export = config.export_config(ConfigFormat.YAML)
        assert "export.test" in yaml_export
        assert "export_value" in yaml_export
        print("   ✅ 配置导出正常")
        passed += 1
    except Exception as e:
        print(f"   ❌ {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    if passed == total:
        print("🎉 所有测试通过！")
    return passed == total


# ============================================================================
# 第七部分：演示主程序
# ============================================================================

def run_demo():
    """运行演示"""
    print("⚙️ Day 14 - 第55节课：记忆配置管理演示")
    print("=" * 60)
    
    print("\n📝 演示1: 四层配置结构")
    
    config = EnhancedMemoryConfig()
    
    # 1. 默认配置（已加载）
    print(f"默认配置 memory.max_size: {config.get('memory.max_size')}")
    
    # 2. 文件配置（模拟）
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_content = """
memory:
  max_size: 2000
  ttl_seconds: 7200
injection:
  max_facts: 15
  min_confidence: 0.7
logging:
  level: "DEBUG"
        """
        f.write(yaml_content)
        filepath = f.name
    
    config.load_from_file(filepath)
    print(f"文件配置 injection.max_facts: {config.get('injection.max_facts')}")
    print(f"配置来源: {config.get_with_metadata('injection.max_facts')['layer']}")
    
    # 3. 环境变量配置
    import os
    os.environ["MEMORY_INJECTION_MAX_FACTS"] = "20"
    os.environ["MEMORY_PERFORMANCE_CACHE_SIZE"] = "500"
    
    config.load_from_env(prefix="MEMORY_")
    print(f"环境变量配置 injection.max_facts: {config.get('injection.max_facts')}")
    print(f"配置冲突报告: {config.get_conflict_report('injection.max_facts')}")
    
    # 4. 运行时配置
    config.set_runtime("injection.max_facts", 25, "user_override")
    print(f"运行时配置 injection.max_facts: {config.get('injection.max_facts')}")
    
    print("\n\n📝 演示2: 配置验证和安全")
    
    # 配置验证器
    config.validator.add_type_check("validation.example", int)
    config.validator.add_value_range("validation.example", min_val=0, max_val=100)
    
    # 设置验证通过的值
    config.set_runtime("validation.example", 50)
    validation_result = config.validate_all()
    print(f"验证结果: {'通过' if validation_result.is_valid else '失败'}")
    if validation_result.warnings:
        print(f"警告: {validation_result.warnings}")
    
    # 安全掩码
    config.security_manager.add_masked_key("api.secret_key")
    config.set_runtime("api.secret_key", "super_secret_123")
    
    safe_config = config.get_all(include_sensitive=False)
    print(f"安全配置（掩码后）: {safe_config.get('api.secret_key')}")
    
    print("\n\n📝 演示3: 动态配置和热加载")
    
    # 配置变更回调
    def config_change_callback(changed: Dict[str, Any]):
        print(f"配置变更回调: {changed}")
    
    config.register_callback(config_change_callback)
    
    # 模拟配置变更
    config.set_runtime("dynamic.config", "initial_value")
    config.set_runtime("dynamic.config", "updated_value")
    
    # 查看变更历史
    history = config.get_change_history(limit=5)
    print(f"最近变更历史: {len(history)} 条记录")
    
    print("\n\n📝 演示4: 配置导出")
    
    yaml_config = config.export_config(ConfigFormat.YAML)
    print("YAML导出（前200字符）:")
    print(yaml_config[:200] + "...")
    
    # 清理临时文件
    os.unlink(filepath)
    
    print("\n" + "=" * 60)
    print("✅ 演示完成！")


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(0 if run_tests() else 1)
    else:
        run_demo()