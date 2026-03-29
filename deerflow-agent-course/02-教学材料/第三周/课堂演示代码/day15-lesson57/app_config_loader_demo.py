#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AppConfig加载流程演示代码 - DeerFlow Python Agent 架构师训练营
第57节课：AppConfig加载流程

本模块演示配置系统的完整加载流程，包括：
1. 多源配置加载：默认配置、YAML文件、环境变量、命令行参数
2. 深度合并算法：递归合并嵌套配置字典
3. 配置验证：类型检查、必需字段、值范围验证
4. 错误处理：详细的配置加载错误信息
5. 高级功能：配置模板、变量替换、热更新

使用说明：
1. 直接运行：python app_config_loader_demo.py
2. 运行测试：python app_config_loader_demo.py --test
3. 查看帮助：python app_config_loader_demo.py --help
"""

import os
import sys
import json
import yaml
import argparse
import copy
import re
import time
from typing import Any, Dict, List, Optional, Union, Callable, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """配置错误基类"""
    pass


class ConfigValidationError(ConfigError):
    """配置验证错误"""
    pass


class ConfigMergeError(ConfigError):
    """配置合并错误"""
    pass


class ConfigSource(Enum):
    """配置源枚举"""
    DEFAULT = "default"
    YAML_FILE = "yaml_file"
    ENV_VARS = "environment_variables"
    CLI_ARGS = "command_line_arguments"
    RUNTIME = "runtime"


@dataclass
class ConfigMetadata:
    """配置元数据"""
    source: ConfigSource
    path: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    priority: int = 0  # 优先级，数值越大优先级越高


class DeepMerger:
    """
    深度合并器
    
    实现递归的深度合并算法，支持多种合并策略：
    1. 覆盖合并：后加载的配置覆盖先加载的配置
    2. 数组合并：追加、去重、替换等策略
    3. 字典合并：递归合并嵌套字典
    
    示例：
    >>> merger = DeepMerger()
    >>> base = {"a": 1, "b": {"c": 2}}
    >>> override = {"b": {"d": 3}, "e": 4}
    >>> result = merger.merge(base, override)
    >>> result == {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
    True
    """
    
    class ArrayMergeStrategy(Enum):
        """数组合并策略"""
        REPLACE = "replace"      # 完全替换
        APPEND = "append"        # 追加
        EXTEND = "extend"        # 扩展（扁平化追加）
        UNIQUE = "unique"        # 去重追加
        INTERSECT = "intersect"  # 交集
    
    def __init__(self, array_strategy: ArrayMergeStrategy = ArrayMergeStrategy.EXTEND):
        self.array_strategy = array_strategy
        
    def merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并两个字典
        
        Args:
            base: 基础配置字典
            override: 覆盖配置字典
            
        Returns:
            合并后的配置字典
        """
        result = copy.deepcopy(base)
        
        for key, override_value in override.items():
            if key in result:
                base_value = result[key]
                
                # 递归合并嵌套字典
                if isinstance(base_value, dict) and isinstance(override_value, dict):
                    result[key] = self.merge(base_value, override_value)
                    
                # 数组合并
                elif isinstance(base_value, list) and isinstance(override_value, list):
                    result[key] = self._merge_arrays(base_value, override_value)
                    
                # 其他类型直接覆盖
                else:
                    result[key] = override_value
            else:
                result[key] = override_value
                
        return result
    
    def _merge_arrays(self, base: List[Any], override: List[Any]) -> List[Any]:
        """合并两个数组，根据策略处理"""
        if self.array_strategy == self.ArrayMergeStrategy.REPLACE:
            return copy.deepcopy(override)
            
        elif self.array_strategy == self.ArrayMergeStrategy.APPEND:
            result = copy.deepcopy(base)
            result.extend(copy.deepcopy(override))
            return result
            
        elif self.array_strategy == self.ArrayMergeStrategy.EXTEND:
            result = copy.deepcopy(base)
            # 展平嵌套列表
            for item in override:
                if isinstance(item, list):
                    result.extend(item)
                else:
                    result.append(item)
            return result
            
        elif self.array_strategy == self.ArrayMergeStrategy.UNIQUE:
            result = copy.deepcopy(base)
            seen = set()
            
            # 去重基础列表
            unique_base = []
            for item in result:
                item_hash = self._hash_item(item)
                if item_hash not in seen:
                    seen.add(item_hash)
                    unique_base.append(item)
                    
            # 添加覆盖列表中的新项
            for item in override:
                item_hash = self._hash_item(item)
                if item_hash not in seen:
                    seen.add(item_hash)
                    unique_base.append(item)
                    
            return unique_base
            
        elif self.array_strategy == self.ArrayMergeStrategy.INTERSECT:
            # 只保留两个列表中都存在的项
            base_set = {self._hash_item(item) for item in base}
            override_set = {self._hash_item(item) for item in override}
            intersect_hashes = base_set.intersection(override_set)
            
            result = []
            for item in base:
                if self._hash_item(item) in intersect_hashes:
                    result.append(copy.deepcopy(item))
                    
            return result
            
        else:
            raise ConfigMergeError(f"未知的数组合并策略: {self.array_strategy}")
    
    def _hash_item(self, item: Any) -> str:
        """计算项的哈希值，用于去重"""
        if isinstance(item, (str, int, float, bool, type(None))):
            return f"{type(item).__name__}:{item}"
        elif isinstance(item, (list, dict)):
            return f"{type(item).__name__}:{hash(json.dumps(item, sort_keys=True))}"
        else:
            return f"{type(item).__name__}:{hash(str(item))}"


class ConfigValidator:
    """
    配置验证器
    
    验证配置的完整性和正确性，包括：
    1. 必需字段检查
    2. 类型验证
    3. 值范围验证
    4. 格式验证（正则表达式）
    5. 依赖关系验证
    6. 自定义验证规则
    
    示例：
    >>> validator = ConfigValidator()
    >>> validator.add_required_fields(["database.host", "database.port"])
    >>> config = {"database": {"host": "localhost", "port": 5432}}
    >>> validator.validate(config)  # 通过
    """
    
    def __init__(self):
        self.required_fields: Set[str] = set()
        self.type_rules: Dict[str, type] = {}
        self.range_rules: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
        self.regex_rules: Dict[str, str] = {}
        self.custom_validators: List[Callable[[Dict[str, Any]], List[str]]] = []
        
    def add_required_fields(self, fields: List[str]) -> None:
        """添加必需字段"""
        self.required_fields.update(fields)
        
    def add_type_rule(self, field_path: str, expected_type: type) -> None:
        """添加类型验证规则"""
        self.type_rules[field_path] = expected_type
        
    def add_range_rule(self, field_path: str, min_val: Optional[float] = None, 
                       max_val: Optional[float] = None) -> None:
        """添加值范围验证规则"""
        self.range_rules[field_path] = (min_val, max_val)
        
    def add_regex_rule(self, field_path: str, pattern: str) -> None:
        """添加正则表达式验证规则"""
        self.regex_rules[field_path] = pattern
        
    def add_custom_validator(self, validator: Callable[[Dict[str, Any]], List[str]]) -> None:
        """添加自定义验证器"""
        self.custom_validators.append(validator)
        
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """
        验证配置，返回错误消息列表
        
        Args:
            config: 要验证的配置字典
            
        Returns:
            错误消息列表，空列表表示验证通过
        """
        errors = []
        
        # 检查必需字段
        for field_path in self.required_fields:
            if not self._get_nested_value(config, field_path):
                errors.append(f"必需字段缺失: {field_path}")
                
        # 类型验证
        for field_path, expected_type in self.type_rules.items():
            value = self._get_nested_value(config, field_path)
            if value is not None and not isinstance(value, expected_type):
                errors.append(f"字段类型错误: {field_path} 期望 {expected_type.__name__}, 实际 {type(value).__name__}")
                
        # 值范围验证
        for field_path, (min_val, max_val) in self.range_rules.items():
            value = self._get_nested_value(config, field_path)
            if value is not None and isinstance(value, (int, float)):
                if min_val is not None and value < min_val:
                    errors.append(f"字段值过小: {field_path} 最小值 {min_val}, 实际 {value}")
                if max_val is not None and value > max_val:
                    errors.append(f"字段值过大: {field_path} 最大值 {max_val}, 实际 {value}")
                    
        # 正则表达式验证
        for field_path, pattern in self.regex_rules.items():
            value = self._get_nested_value(config, field_path)
            if value is not None and isinstance(value, str):
                if not re.match(pattern, value):
                    errors.append(f"字段格式错误: {field_path} 不符合正则表达式 {pattern}")
                    
        # 自定义验证器
        for validator in self.custom_validators:
            custom_errors = validator(config)
            errors.extend(custom_errors)
            
        return errors
    
    def _get_nested_value(self, config: Dict[str, Any], field_path: str) -> Optional[Any]:
        """获取嵌套字段的值"""
        parts = field_path.split('.')
        current = config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
                
        return current


class ConfigTemplateEngine:
    """
    配置模板引擎
    
    支持配置模板和变量替换，功能包括：
    1. 变量引用：${variable_name}
    2. 环境变量引用：${ENV_VAR_NAME}
    3. 默认值：${variable_name:default_value}
    4. 条件表达式：${condition ? true_value : false_value}
    5. 函数调用：${upper(string_value)}
    
    示例：
    >>> engine = ConfigTemplateEngine()
    >>> template = {"host": "${DB_HOST:localhost}", "port": "${DB_PORT:5432}"}
    >>> os.environ["DB_HOST"] = "db.example.com"
    >>> result = engine.render(template)
    >>> result == {"host": "db.example.com", "port": "5432"}
    True
    """
    
    def __init__(self):
        self.functions = {
            "upper": lambda x: x.upper() if isinstance(x, str) else x,
            "lower": lambda x: x.lower() if isinstance(x, str) else x,
            "int": lambda x: int(x) if isinstance(x, (str, int, float)) else x,
            "float": lambda x: float(x) if isinstance(x, (str, int, float)) else x,
            "bool": lambda x: bool(x) if isinstance(x, (str, int, float, bool)) else x,
            "env": lambda x: os.getenv(x, ""),
        }
        
    def render(self, template: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """渲染配置模板"""
        if context is None:
            context = {}
            
        result = copy.deepcopy(template)
        self._render_dict(result, context)
        return result
    
    def _render_dict(self, data: Dict[str, Any], context: Dict[str, Any]) -> None:
        """递归渲染字典"""
        for key, value in data.items():
            if isinstance(value, dict):
                self._render_dict(value, context)
            elif isinstance(value, list):
                self._render_list(value, context)
            elif isinstance(value, str):
                data[key] = self._render_string(value, context)
                
    def _render_list(self, data: List[Any], context: Dict[str, Any]) -> None:
        """递归渲染列表"""
        for i, value in enumerate(data):
            if isinstance(value, dict):
                self._render_dict(value, context)
            elif isinstance(value, list):
                self._render_list(value, context)
            elif isinstance(value, str):
                data[i] = self._render_string(value, context)
    
    def _render_string(self, value: str, context: Dict[str, Any]) -> Any:
        """渲染字符串中的模板变量"""
        if not isinstance(value, str) or '${' not in value:
            return value
            
        # 简单变量替换：${variable_name}
        pattern = r'\$\{([^}:]+)(?::([^}]+))?\}'
        
        def replace_match(match):
            var_name = match.group(1)
            default_value = match.group(2)
            
            # 检查环境变量
            if var_name in os.environ:
                return os.environ[var_name]
                
            # 检查上下文
            if var_name in context:
                return str(context[var_name])
                
            # 使用默认值
            if default_value is not None:
                return default_value
                
            # 未找到变量，保持原样
            return match.group(0)
            
        result = re.sub(pattern, replace_match, value)
        
        # 如果结果仍然是字符串且包含${}，可能包含函数调用
        if isinstance(result, str) and '${' in result:
            # 处理函数调用：${function(arg)}
            func_pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\(([^}]+)\)\}'
            
            def replace_func(match):
                func_name = match.group(1)
                func_arg = match.group(2)
                
                if func_name in self.functions:
                    try:
                        return str(self.functions[func_name](func_arg))
                    except Exception as e:
                        logger.warning(f"函数调用失败: {func_name}({func_arg}): {e}")
                        return match.group(0)
                else:
                    logger.warning(f"未知函数: {func_name}")
                    return match.group(0)
                    
            result = re.sub(func_pattern, replace_func, result)
            
        # 尝试转换为适当类型
        try:
            # 整数
            if re.match(r'^-?\d+$', result):
                return int(result)
            # 浮点数
            elif re.match(r'^-?\d+\.\d+$', result):
                return float(result)
            # 布尔值
            elif result.lower() in ('true', 'false'):
                return result.lower() == 'true'
            # None
            elif result.lower() == 'null' or result == '':
                return None
        except (ValueError, TypeError):
            pass
            
        return result


class ConfigLoader:
    """
    配置加载器
    
    从多个源加载配置并合并，支持：
    1. 默认配置（代码中定义）
    2. YAML配置文件
    3. 环境变量
    4. 命令行参数
    5. 运行时配置
    
    加载顺序（优先级从低到高）：
    默认配置 < YAML文件 < 环境变量 < 命令行参数 < 运行时配置
    
    示例：
    >>> loader = ConfigLoader()
    >>> config = loader.load("config.yaml")
    >>> print(config.get("database.host"))
    """
    
    def __init__(self, 
                 env_prefix: str = "APP_",
                 cli_prefix: str = "--config-",
                 array_merge_strategy: DeepMerger.ArrayMergeStrategy = DeepMerger.ArrayMergeStrategy.EXTEND):
        self.env_prefix = env_prefix
        self.cli_prefix = cli_prefix
        self.merger = DeepMerger(array_merge_strategy)
        self.validator = ConfigValidator()
        self.template_engine = ConfigTemplateEngine()
        self.metadata: List[ConfigMetadata] = []
        
    def load(self, 
             config_file: Optional[str] = None,
             default_config: Optional[Dict[str, Any]] = None,
             env_vars: Optional[Dict[str, str]] = None,
             cli_args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        从多个源加载配置
        
        Args:
            config_file: YAML配置文件路径
            default_config: 默认配置字典
            env_vars: 环境变量映射（如果为None，则从os.environ读取）
            cli_args: 命令行参数列表（如果为None，则从sys.argv读取）
            
        Returns:
            合并后的配置字典
        """
        config = {}
        self.metadata = []
        
        # 1. 加载默认配置
        if default_config is not None:
            config = self.merger.merge(config, default_config)
            self.metadata.append(ConfigMetadata(
                source=ConfigSource.DEFAULT,
                priority=10
            ))
            logger.debug("已加载默认配置")
            
        # 2. 加载YAML配置文件
        if config_file and os.path.exists(config_file):
            yaml_config = self._load_yaml_file(config_file)
            config = self.merger.merge(config, yaml_config)
            self.metadata.append(ConfigMetadata(
                source=ConfigSource.YAML_FILE,
                path=config_file,
                priority=20
            ))
            logger.info(f"已加载YAML配置文件: {config_file}")
            
        # 3. 加载环境变量
        env_config = self._load_env_vars(env_vars)
        config = self.merger.merge(config, env_config)
        self.metadata.append(ConfigMetadata(
            source=ConfigSource.ENV_VARS,
            priority=30
        ))
        logger.debug("已加载环境变量配置")
        
        # 4. 加载命令行参数
        cli_config = self._load_cli_args(cli_args)
        config = self.merger.merge(config, cli_config)
        self.metadata.append(ConfigMetadata(
            source=ConfigSource.CLI_ARGS,
            priority=40
        ))
        logger.debug("已加载命令行参数配置")
        
        # 5. 应用模板渲染
        config = self.template_engine.render(config)
        
        # 6. 验证配置
        errors = self.validator.validate(config)
        if errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ConfigValidationError(error_msg)
            
        logger.info("配置加载完成")
        return config
    
    def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """加载YAML配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"YAML文件解析失败: {file_path}: {e}")
        except IOError as e:
            raise ConfigError(f"无法读取YAML文件: {file_path}: {e}")
            
    def _load_env_vars(self, env_vars: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """从环境变量加载配置"""
        if env_vars is None:
            env_vars = os.environ
            
        config = {}
        
        for key, value in env_vars.items():
            if key.startswith(self.env_prefix):
                # 将环境变量名转换为配置路径
                # 例如：APP_DATABASE_HOST -> database.host
                config_path = key[len(self.env_prefix):].lower().replace('_', '.')
                self._set_nested_value(config, config_path, value)
                
        return config
    
    def _load_cli_args(self, cli_args: Optional[List[str]] = None) -> Dict[str, Any]:
        """从命令行参数加载配置"""
        if cli_args is None:
            cli_args = sys.argv[1:]
            
        config = {}
        
        for arg in cli_args:
            if arg.startswith(self.cli_prefix):
                # 例如：--config-database.host=localhost
                key_value = arg[len(self.cli_prefix):]
                if '=' in key_value:
                    key, value = key_value.split('=', 1)
                    self._set_nested_value(config, key, value)
                    
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any) -> None:
        """设置嵌套字典的值"""
        parts = path.split('.')
        current = config
        
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # 最后一部分，设置值
                current[part] = value
            else:
                # 中间部分，确保是字典
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    # 如果当前值不是字典，转换为字典
                    current[part] = {"_value": current[part]}
                    
                current = current[part]
    
    def watch_and_reload(self, config_file: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        监视配置文件变化并自动重新加载
        
        Args:
            config_file: 要监视的配置文件路径
            callback: 配置变化时的回调函数
        """
        # 注意：这里使用简单轮询，实际生产环境可以使用watchdog库
        last_mtime = os.path.getmtime(config_file) if os.path.exists(config_file) else 0
        
        def check_for_changes():
            nonlocal last_mtime
            
            if os.path.exists(config_file):
                current_mtime = os.path.getmtime(config_file)
                if current_mtime > last_mtime:
                    logger.info(f"检测到配置文件变化: {config_file}")
                    try:
                        new_config = self.load(config_file)
                        callback(new_config)
                        last_mtime = current_mtime
                    except ConfigError as e:
                        logger.error(f"配置重新加载失败: {e}")
                        
        # 启动监视线程（简化版，实际需要线程或异步）
        logger.warning("配置监视功能需要实现线程或异步，当前为简化版本")
        return check_for_changes
    
    def get_metadata(self) -> List[ConfigMetadata]:
        """获取配置加载的元数据"""
        return self.metadata.copy()


class AppConfig:
    """
    应用程序配置类
    
    封装配置加载和访问，提供类型安全的配置访问接口。
    
    示例：
    >>> config = AppConfig()
    >>> config.load("config.yaml")
    >>> db_host = config.get("database.host", "localhost")
    >>> db_port = config.get_int("database.port", 5432)
    """
    
    def __init__(self):
        self.loader = ConfigLoader()
        self._config: Dict[str, Any] = {}
        self._loaded = False
        
    def load(self, config_file: Optional[str] = None, **kwargs) -> None:
        """
        加载配置
        
        Args:
            config_file: 配置文件路径
            **kwargs: 传递给ConfigLoader.load的其他参数
        """
        self._config = self.loader.load(config_file, **kwargs)
        self._loaded = True
        logger.info("应用程序配置已加载")
        
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if not self._loaded:
            raise ConfigError("配置未加载，请先调用load()方法")
            
        value = self._get_nested_value(key)
        return value if value is not None else default
        
    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置值"""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"配置值无法转换为整数: {key}={value}")
            return default
            
    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置值"""
        value = self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"配置值无法转换为浮点数: {key}={value}")
            return default
            
    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔值配置值"""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        elif isinstance(value, (int, float)):
            return bool(value)
        elif isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
        else:
            return default
            
    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]:
        """获取列表配置值"""
        value = self.get(key, default or [])
        if isinstance(value, list):
            return value
        elif isinstance(value, (str, int, float, bool)):
            return [value]
        else:
            logger.warning(f"配置值无法转换为列表: {key}={value}")
            return default or []
            
    def get_dict(self, key: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取字典配置值"""
        value = self.get(key, default or {})
        if isinstance(value, dict):
            return value
        else:
            logger.warning(f"配置值无法转换为字典: {key}={value}")
            return default or {}
            
    def set(self, key: str, value: Any) -> None:
        """设置配置值（运行时配置）"""
        self._set_nested_value(key, value)
        
    def reload(self) -> None:
        """重新加载配置"""
        if hasattr(self, '_config_file'):
            self.load(self._config_file)
        else:
            raise ConfigError("无法重新加载，未指定配置文件")
            
    def _get_nested_value(self, key: str) -> Optional[Any]:
        """获取嵌套配置值"""
        parts = key.split('.')
        current = self._config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
                
        return current
        
    def _set_nested_value(self, key: str, value: Any) -> None:
        """设置嵌套配置值"""
        parts = key.split('.')
        current = self._config
        
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                current[part] = value
            else:
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    current[part] = {"_value": current[part]}
                    
                current = current[part]


# ============================================================================
# 测试用例
# ============================================================================

def test_deep_merger() -> None:
    """测试深度合并器"""
    print("测试深度合并器...")
    
    merger = DeepMerger()
    
    # 测试字典合并
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"d": 4, "e": 5}, "f": 6}
    result = merger.merge(base, override)
    
    assert result["a"] == 1, "基础值应保留"
    assert result["b"]["c"] == 2, "嵌套基础值应保留"
    assert result["b"]["d"] == 4, "嵌套值应被覆盖"
    assert result["b"]["e"] == 5, "嵌套新值应添加"
    assert result["f"] == 6, "新键应添加"
    
    # 测试数组合并
    merger_extend = DeepMerger(DeepMerger.ArrayMergeStrategy.EXTEND)
    base_list = {"items": [1, 2, [3, 4]]}
    override_list = {"items": [5, [6, 7]]}
    result_list = merger_extend.merge(base_list, override_list)
    
    assert len(result_list["items"]) == 4, "扩展合并应展平嵌套列表"
    assert 5 in result_list["items"], "新项应添加"
    
    print("深度合并器测试通过 ✓")


def test_config_validator() -> None:
    """测试配置验证器"""
    print("测试配置验证器...")
    
    validator = ConfigValidator()
    validator.add_required_fields(["database.host", "database.port"])
    validator.add_type_rule("database.port", int)
    validator.add_range_rule("database.port", min_val=1, max_val=65535)
    validator.add_regex_rule("database.host", r"^[a-zA-Z0-9.-]+$")
    
    # 有效配置
    valid_config = {
        "database": {
            "host": "localhost",
            "port": 5432
        }
    }
    errors = validator.validate(valid_config)
    assert len(errors) == 0, f"有效配置应通过验证，但得到错误: {errors}"
    
    # 无效配置
    invalid_config = {
        "database": {
            "host": "local_host@",  # 无效字符
            "port": 70000  # 超出范围
        }
    }
    errors = validator.validate(invalid_config)
    assert len(errors) == 2, f"无效配置应产生2个错误，但得到: {len(errors)}"
    
    print("配置验证器测试通过 ✓")


def test_config_template_engine() -> None:
    """测试配置模板引擎"""
    print("测试配置模板引擎...")
    
    engine = ConfigTemplateEngine()
    
    # 设置环境变量
    os.environ["TEST_DB_HOST"] = "test-host"
    
    # 测试模板渲染
    template = {
        "database": {
            "host": "${TEST_DB_HOST:localhost}",
            "port": "${TEST_DB_PORT:5432}",
            "url": "${TEST_DB_HOST:localhost}:${TEST_DB_PORT:5432}"
        },
        "feature": {
            "enabled": "${FEATURE_FLAG:false}"
        }
    }
    
    result = engine.render(template)
    
    assert result["database"]["host"] == "test-host", "环境变量应被替换"
    assert result["database"]["port"] == 5432, "应使用默认值"
    assert result["database"]["url"] == "test-host:5432", "多个变量应被替换"
    assert result["feature"]["enabled"] is False, "布尔值默认值应被转换"
    
    # 清理环境变量
    del os.environ["TEST_DB_HOST"]
    
    print("配置模板引擎测试通过 ✓")


def test_config_loader() -> None:
    """测试配置加载器"""
    print("测试配置加载器...")
    
    # 创建临时配置文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_content = """
        database:
          host: yaml-host
          port: 5433
          credentials:
            username: yaml-user
        logging:
          level: INFO
        """
        f.write(yaml_content)
        temp_file = f.name
    
    try:
        # 设置环境变量
        os.environ["APP_DATABASE_HOST"] = "env-host"
        os.environ["APP_LOGGING_LEVEL"] = "DEBUG"
        
        # 测试配置加载
        loader = ConfigLoader()
        
        default_config = {
            "database": {
                "host": "default-host",
                "port": 5432,
                "max_connections": 10
            },
            "logging": {
                "level": "WARNING",
                "format": "default"
            }
        }
        
        # 模拟命令行参数
        cli_args = [
            f"--config-database.port=5434",
            f"--config-feature.enabled=true"
        ]
        
        config = loader.load(
            config_file=temp_file,
            default_config=default_config,
            cli_args=cli_args
        )
        
        # 验证合并结果
        assert config["database"]["host"] == "env-host", "环境变量应覆盖YAML文件"
        assert config["database"]["port"] == 5434, "命令行参数应覆盖环境变量"
        assert config["database"]["max_connections"] == 10, "默认值应保留"
        assert config["database"]["credentials"]["username"] == "yaml-user", "YAML值应保留"
        assert config["logging"]["level"] == "DEBUG", "环境变量应覆盖YAML"
        assert config["logging"]["format"] == "default", "默认值应保留"
        assert config["feature"]["enabled"] is True, "命令行参数应添加新配置"
        
        # 验证元数据
        metadata = loader.get_metadata()
        assert len(metadata) == 4, f"应有4个配置源，实际: {len(metadata)}"
        
        print("配置加载器测试通过 ✓")
        
    finally:
        # 清理
        os.unlink(temp_file)
        del os.environ["APP_DATABASE_HOST"]
        del os.environ["APP_LOGGING_LEVEL"]


def test_app_config() -> None:
    """测试应用程序配置类"""
    print("测试应用程序配置类...")
    
    # 创建临时配置文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_content = """
        server:
          host: localhost
          port: 8080
          timeout: 30.5
        features:
          enabled: true
          items:
            - auth
            - logging
        """
        f.write(yaml_content)
        temp_file = f.name
    
    try:
        config = AppConfig()
        config.load(temp_file)
        
        # 测试类型安全访问
        assert config.get("server.host") == "localhost"
        assert config.get_int("server.port") == 8080
        assert config.get_float("server.timeout") == 30.5
        assert config.get_bool("features.enabled") is True
        assert config.get_list("features.items") == ["auth", "logging"]
        
        # 测试默认值
        assert config.get("server.unknown", "default") == "default"
        assert config.get_int("server.unknown", 999) == 999
        
        # 测试运行时设置
        config.set("server.port", 9090)
        assert config.get_int("server.port") == 9090
        
        print("应用程序配置类测试通过 ✓")
        
    finally:
        os.unlink(temp_file)


def test_error_handling() -> None:
    """测试错误处理"""
    print("测试错误处理...")
    
    loader = ConfigLoader()
    
    # 测试不存在的配置文件
    try:
        loader.load("non_existent_file.yaml")
        assert False, "应抛出异常"
    except ConfigError:
        pass  # 预期异常
    
    # 测试无效YAML
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: : :")
        temp_file = f.name
    
    try:
        try:
            loader.load(temp_file)
            assert False, "应抛出YAML解析异常"
        except ConfigError:
            pass  # 预期异常
    finally:
        os.unlink(temp_file)
    
    # 测试验证失败
    validator = ConfigValidator()
    validator.add_required_fields(["required.field"])
    
    config = {"other": "value"}
    errors = validator.validate(config)
    assert len(errors) > 0, "验证应失败"
    
    print("错误处理测试通过 ✓")


def test_performance() -> None:
    """测试性能"""
    print("测试性能...")
    
    import time
    
    # 创建大型配置
    large_config = {}
    for i in range(1000):
        large_config[f"key_{i}"] = {
            "nested": {
                "value": i,
                "list": list(range(10))
            }
        }
    
    # 测试合并性能
    merger = DeepMerger()
    
    start = time.time()
    for _ in range(100):
        result = merger.merge(large_config, {"extra": "value"})
    duration = time.time() - start
    
    assert duration < 5.0, f"合并性能太差: {duration:.2f}秒"
    print(f"性能测试通过: 100次合并耗时 {duration:.2f}秒 ✓")


def run_all_tests() -> None:
    """运行所有测试"""
    print("=" * 60)
    print("开始运行AppConfig加载流程测试")
    print("=" * 60)
    
    tests = [
        test_deep_merger,
        test_config_validator,
        test_config_template_engine,
        test_config_loader,
        test_app_config,
        test_error_handling,
        test_performance,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"测试失败: {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    print("=" * 60)
    print(f"测试完成: 通过 {passed}, 失败 {failed}, 总计 {len(tests)}")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)


# ============================================================================
# 示例使用
# ============================================================================

def example_usage() -> None:
    """示例使用"""
    print("=" * 60)
    print("AppConfig加载流程示例使用")
    print("=" * 60)
    
    # 1. 创建配置加载器
    loader = ConfigLoader()
    
    # 2. 定义默认配置
    default_config = {
        "app": {
            "name": "MyApp",
            "version": "1.0.0",
            "debug": False
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "mydb",
            "pool_size": 10
        },
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "timeout": 30
        }
    }
    
    # 3. 创建配置文件（临时）
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml_content = """
        app:
          name: "MyApp-Prod"
          debug: false
          
        database:
          host: "db.production.example.com"
          name: "production_db"
          
        server:
          port: 8080
          
        features:
          caching: true
          monitoring: true
        """
        f.write(yaml_content)
        config_file = f.name
    
    try:
        # 4. 设置环境变量
        os.environ["APP_DATABASE_POOL_SIZE"] = "20"
        os.environ["APP_SERVER_TIMEOUT"] = "60"
        
        # 5. 模拟命令行参数
        cli_args = [
            "--config-app.debug=true",
            "--config-server.host=127.0.0.1"
        ]
        
        # 6. 加载配置
        print("加载配置中...")
        config = loader.load(
            config_file=config_file,
            default_config=default_config,
            cli_args=cli_args
        )
        
        # 7. 显示配置
        print("\n最终配置:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        
        # 8. 显示元数据
        print("\n配置加载元数据:")
        for meta in loader.get_metadata():
            print(f"  - 来源: {meta.source.value}, 优先级: {meta.priority}, 路径: {meta.path}")
        
        # 9. 使用AppConfig包装器
        print("\n使用AppConfig包装器:")
        app_config = AppConfig()
        app_config.load(config_file, default_config=default_config, cli_args=cli_args)
        
        print(f"应用名称: {app_config.get('app.name')}")
        print(f"数据库主机: {app_config.get('database.host')}")
        print(f"数据库连接池大小: {app_config.get_int('database.pool_size')}")
        print(f"服务器端口: {app_config.get_int('server.port')}")
        print(f"调试模式: {app_config.get_bool('app.debug')}")
        print(f"缓存功能: {app_config.get_bool('features.caching', False)}")
        
        # 10. 模板示例
        print("\n配置模板示例:")
        template_engine = ConfigTemplateEngine()
        template = {
            "connection_string": "postgresql://${DB_USER:admin}:${DB_PASSWORD:secret}@${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:mydb}"
        }
        
        # 设置一些环境变量
        os.environ["DB_USER"] = "app_user"
        os.environ["DB_HOST"] = "db.example.com"
        
        rendered = template_engine.render(template)
        print(f"连接字符串: {rendered['connection_string']}")
        
    finally:
        # 清理
        os.unlink(config_file)
        del os.environ["APP_DATABASE_POOL_SIZE"]
        del os.environ["APP_SERVER_TIMEOUT"]
        if "DB_USER" in os.environ:
            del os.environ["DB_USER"]
        if "DB_HOST" in os.environ:
            del os.environ["DB_HOST"]
    
    print("\n示例完成!")


# ============================================================================
# 主程序
# ============================================================================

def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description="AppConfig加载流程演示")
    parser.add_argument("--test", action="store_true", help="运行测试")
    parser.add_argument("--example", action="store_true", help="运行示例")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--config-key", type=str, help="查看特定配置键")
    
    args = parser.parse_args()
    
    if args.test:
        run_all_tests()
    elif args.example:
        example_usage()
    elif args.config:
        # 加载并显示配置
        loader = ConfigLoader()
        config = loader.load(args.config)
        
        if args.config_key:
            # 显示特定键
            from typing import Any
            
            def get_nested_value(data: Dict[str, Any], key: str) -> Any:
                parts = key.split('.')
                current = data
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return None
                return current
            
            value = get_nested_value(config, args.config_key)
            print(f"{args.config_key} = {value}")
        else:
            # 显示所有配置
            print(json.dumps(config, indent=2, ensure_ascii=False))
    else:
        # 默认运行示例
        example_usage()


if __name__ == "__main__":
    main()