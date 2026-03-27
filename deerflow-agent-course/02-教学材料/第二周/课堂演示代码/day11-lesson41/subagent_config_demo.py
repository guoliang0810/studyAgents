#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 11 Lesson 41: SubagentConfig配置结构 (Subagent Configuration Structure)

本文件演示子代理配置系统的设计和实现，包括：
1. 配置数据结构 - SubagentConfig数据类定义
2. 配置验证 - 类型检查、范围验证、依赖验证
3. 配置加载 - YAML文件解析和环境变量替换
4. 配置管理 - 多类型子代理配置管理

使用示例:
    python subagent_config_demo.py          # 运行基本演示
    python subagent_config_demo.py --test   # 运行测试套件
    python subagent_config_demo.py --demo   # 运行完整演示
    python subagent_config_demo.py --help   # 显示帮助信息
"""

import os
import yaml
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from pathlib import Path


class SubagentType(Enum):
    """子代理类型枚举"""
    GENERIC = "generic"      # 通用子代理
    BASH = "bash"            # Bash命令执行子代理
    SQL = "sql"              # SQL查询执行子代理
    WEB = "web"              # Web操作子代理
    PYTHON = "python"        # Python代码执行子代理


class Capability(Enum):
    """能力枚举"""
    CODE_EXECUTION = "code_execution"        # 代码执行
    DEBUGGING = "debugging"                  # 调试
    SHELL_EXECUTION = "shell_execution"      # Shell执行
    FILE_OPERATIONS = "file_operations"      # 文件操作
    QUERY_EXECUTION = "query_execution"      # 查询执行
    SCHEMA_ANALYSIS = "schema_analysis"      # 模式分析
    WEB_SCRAPING = "web_scraping"            # Web抓取
    API_CALLING = "api_calling"              # API调用


@dataclass
class SubagentConfig:
    """
    子代理配置数据类
    
    包含子代理的所有配置信息，包括类型、描述、能力和运行时配置。
    """
    name: str                                           # 子代理名称（必填）
    type: SubagentType                                  # 子代理类型（必填）
    description: str                                    # 子代理描述（必填）
    capabilities: List[Capability]                      # 能力列表（必填）
    enabled: bool = True                                # 是否启用
    priority: int = 1                                   # 执行优先级（1-10）
    timeout_seconds: int = 300                          # 超时时间（秒）
    max_memory_mb: int = 512                            # 最大内存（MB）
    config: Dict[str, Any] = field(default_factory=dict)  # 类型特定配置
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "capabilities": [cap.value for cap in self.capabilities],
            "enabled": self.enabled,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "max_memory_mb": self.max_memory_mb,
            "config": self.config
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubagentConfig":
        """从字典创建配置"""
        return cls(
            name=data["name"],
            type=SubagentType(data["type"]),
            description=data["description"],
            capabilities=[Capability(cap) for cap in data["capabilities"]],
            enabled=data.get("enabled", True),
            priority=data.get("priority", 1),
            timeout_seconds=data.get("timeout_seconds", 300),
            max_memory_mb=data.get("max_memory_mb", 512),
            config=data.get("config", {})
        )


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool                          # 是否验证通过
    errors: List[str] = field(default_factory=list)    # 错误列表
    warnings: List[str] = field(default_factory=list)  # 警告列表
    
    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)


class ConfigValidator:
    """配置验证器"""
    
    # 允许的子代理类型
    VALID_TYPES: Set[str] = {t.value for t in SubagentType}
    
    # 允许的能力
    VALID_CAPABILITIES: Set[str] = {c.value for c in Capability}
    
    # 类型到必需能力的映射
    TYPE_REQUIRED_CAPABILITIES: Dict[str, List[str]] = {
        SubagentType.GENERIC.value: [Capability.CODE_EXECUTION.value],
        SubagentType.BASH.value: [Capability.SHELL_EXECUTION.value],
        SubagentType.SQL.value: [Capability.QUERY_EXECUTION.value],
        SubagentType.WEB.value: [Capability.WEB_SCRAPING.value, Capability.API_CALLING.value],
        SubagentType.PYTHON.value: [Capability.CODE_EXECUTION.value, Capability.DEBUGGING.value],
    }
    
    @classmethod
    def validate(cls, config: Dict[str, Any]) -> ValidationResult:
        """
        验证配置
        
        Args:
            config: 配置字典
            
        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(is_valid=True)
        
        # 1. 检查必填字段
        required_fields = ["name", "type", "description", "capabilities"]
        for field_name in required_fields:
            if field_name not in config:
                result.add_error(f"缺少必填字段: {field_name}")
        
        if not result.is_valid:
            return result
        
        # 2. 验证name字段
        name = config["name"]
        if not isinstance(name, str) or len(name) == 0:
            result.add_error("name必须是非空字符串")
        elif len(name) > 64:
            result.add_error("name长度不能超过64个字符")
        elif not name.replace("_", "").replace("-", "").isalnum():
            result.add_error("name只能包含字母、数字、下划线和连字符")
        
        # 3. 验证type字段
        subagent_type = config["type"]
        if subagent_type not in cls.VALID_TYPES:
            result.add_error(f"无效的type值: {subagent_type}，允许的值: {cls.VALID_TYPES}")
        
        # 4. 验证description字段
        description = config["description"]
        if not isinstance(description, str) or len(description) == 0:
            result.add_error("description必须是非空字符串")
        elif len(description) > 256:
            result.add_warning("description长度超过256字符，建议精简")
        
        # 5. 验证capabilities字段
        capabilities = config["capabilities"]
        if not isinstance(capabilities, list) or len(capabilities) == 0:
            result.add_error("capabilities必须是非空列表")
        else:
            for cap in capabilities:
                if cap not in cls.VALID_CAPABILITIES:
                    result.add_error(f"无效的能力: {cap}，允许的值: {cls.VALID_CAPABILITIES}")
            
            # 检查类型必需能力
            if subagent_type in cls.TYPE_REQUIRED_CAPABILITIES:
                required_caps = cls.TYPE_REQUIRED_CAPABILITIES[subagent_type]
                for req_cap in required_caps:
                    if req_cap not in capabilities:
                        result.add_warning(f"{subagent_type}类型建议包含能力: {req_cap}")
        
        # 6. 验证可选字段
        if "timeout_seconds" in config:
            timeout = config["timeout_seconds"]
            if not isinstance(timeout, int) or timeout < 1:
                result.add_error("timeout_seconds必须是正整数")
            elif timeout > 3600:
                result.add_warning("timeout_seconds超过3600秒（1小时），请确认是否合理")
        
        if "max_memory_mb" in config:
            memory = config["max_memory_mb"]
            if not isinstance(memory, int) or memory < 1:
                result.add_error("max_memory_mb必须是正整数")
            elif memory > 8192:
                result.add_warning("max_memory_mb超过8192MB（8GB），请确认是否合理")
        
        if "priority" in config:
            priority = config["priority"]
            if not isinstance(priority, int) or priority < 1 or priority > 10:
                result.add_error("priority必须是1-10之间的整数")
        
        # 7. 验证类型特定配置
        if "config" in config:
            type_config = config["config"]
            if not isinstance(type_config, dict):
                result.add_error("config必须是字典类型")
            else:
                cls._validate_type_specific_config(subagent_type, type_config, result)
        
        return result
    
    @classmethod
    def _validate_type_specific_config(cls, subagent_type: str, 
                                       type_config: Dict[str, Any], 
                                       result: ValidationResult):
        """验证类型特定配置"""
        
        if subagent_type == SubagentType.BASH.value:
            # Bash类型配置验证
            if "allowed_commands" in type_config:
                allowed = type_config["allowed_commands"]
                if not isinstance(allowed, list) or len(allowed) == 0:
                    result.add_error("allowed_commands必须是非空列表")
                elif "*" in allowed:
                    result.add_warning("allowed_commands包含通配符'*'，存在安全风险")
            
            if "workdir" in type_config:
                workdir = type_config["workdir"]
                if not isinstance(workdir, str):
                    result.add_error("workdir必须是字符串")
        
        elif subagent_type == SubagentType.SQL.value:
            # SQL类型配置验证
            if "max_query_size" in type_config:
                max_size = type_config["max_query_size"]
                if not isinstance(max_size, int) or max_size < 1:
                    result.add_error("max_query_size必须是正整数")
            
            if "allowed_operations" in type_config:
                allowed = type_config["allowed_operations"]
                valid_ops = {"SELECT", "INSERT", "UPDATE", "DELETE", "EXPLAIN", "CREATE", "DROP"}
                if not isinstance(allowed, list):
                    result.add_error("allowed_operations必须是列表")
                else:
                    for op in allowed:
                        if op.upper() not in valid_ops:
                            result.add_warning(f"未知的SQL操作: {op}")


class ConfigLoader:
    """配置加载器"""
    
    @classmethod
    def load_from_yaml(cls, yaml_path: str) -> Dict[str, Any]:
        """
        从YAML文件加载配置
        
        Args:
            yaml_path: YAML文件路径
            
        Returns:
            Dict: 配置字典
        """
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {yaml_path}")
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 替换环境变量
        content = cls._replace_env_vars(content)
        
        # 解析YAML
        config = yaml.safe_load(content)
        return config
    
    @classmethod
    def _replace_env_vars(cls, content: str) -> str:
        """
        替换环境变量
        
        支持 ${VAR_NAME} 格式的环境变量替换
        """
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_var, content)
    
    @classmethod
    def load_subagents(cls, yaml_path: str) -> Dict[str, SubagentConfig]:
        """
        加载子代理配置
        
        Args:
            yaml_path: YAML文件路径
            
        Returns:
            Dict[str, SubagentConfig]: 子代理配置字典，以名称为键
        """
        config = cls.load_from_yaml(yaml_path)
        
        if "subagents" not in config:
            raise ValueError("配置文件缺少subagents字段")
        
        subagents = {}
        for name, subagent_config in config["subagents"].items():
            # 添加name字段（从键名获取）
            subagent_config["name"] = name
            
            # 验证配置
            validation = ConfigValidator.validate(subagent_config)
            if not validation.is_valid:
                raise ValueError(f"配置验证失败 - {name}: {validation.errors}")
            
            # 记录警告
            for warning in validation.warnings:
                logging.warning(f"配置警告 - {name}: {warning}")
            
            # 创建配置对象
            subagents[name] = SubagentConfig.from_dict(subagent_config)
        
        return subagents


class SubagentRegistry:
    """子代理注册表"""
    
    def __init__(self):
        self._configs: Dict[str, SubagentConfig] = {}
    
    def register(self, config: SubagentConfig) -> ValidationResult:
        """
        注册子代理配置
        
        Args:
            config: 子代理配置
            
        Returns:
            ValidationResult: 验证结果
        """
        # 创建配置字典进行验证
        config_dict = config.to_dict()
        validation = ConfigValidator.validate(config_dict)
        
        if validation.is_valid:
            self._configs[config.name] = config
            logging.info(f"子代理已注册: {config.name} ({config.type.value})")
        
        return validation
    
    def get(self, name: str) -> Optional[SubagentConfig]:
        """获取子代理配置"""
        return self._configs.get(name)
    
    def list_all(self) -> List[SubagentConfig]:
        """列出所有子代理配置"""
        return list(self._configs.values())
    
    def list_by_type(self, subagent_type: SubagentType) -> List[SubagentConfig]:
        """按类型列出子代理配置"""
        return [c for c in self._configs.values() if c.type == subagent_type]
    
    def list_enabled(self) -> List[SubagentConfig]:
        """列出已启用的子代理配置"""
        return [c for c in self._configs.values() if c.enabled]
    
    def unregister(self, name: str) -> bool:
        """注销子代理配置"""
        if name in self._configs:
            del self._configs[name]
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        configs = list(self._configs.values())
        return {
            "total": len(configs),
            "enabled": len([c for c in configs if c.enabled]),
            "disabled": len([c for c in configs if not c.enabled]),
            "by_type": {
                t.value: len([c for c in configs if c.type == t])
                for t in SubagentType
            }
        }


class ConfigTestSuite:
    """配置系统测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_subagent_config_creation", self.test_subagent_config_creation),
            ("test_config_validation", self.test_config_validation),
            ("test_config_validator", self.test_config_validator),
            ("test_subagent_registry", self.test_subagent_registry),
            ("test_config_serialization", self.test_config_serialization),
        ]
    
    def test_subagent_config_creation(self) -> tuple:
        """测试子代理配置创建"""
        try:
            # 创建配置
            config = SubagentConfig(
                name="test_agent",
                type=SubagentType.GENERIC,
                description="测试子代理",
                capabilities=[Capability.CODE_EXECUTION, Capability.DEBUGGING],
                timeout_seconds=600,
                max_memory_mb=1024
            )
            
            # 验证字段
            if config.name != "test_agent":
                return False, f"name不正确: {config.name}"
            if config.type != SubagentType.GENERIC:
                return False, f"type不正确: {config.type}"
            if len(config.capabilities) != 2:
                return False, f"capabilities长度不正确: {len(config.capabilities)}"
            if config.timeout_seconds != 600:
                return False, f"timeout_seconds不正确: {config.timeout_seconds}"
            
            return True, "子代理配置创建测试通过"
        except Exception as e:
            return False, f"配置创建异常: {e}"
    
    def test_config_validation(self) -> tuple:
        """测试配置验证"""
        try:
            # 有效配置
            valid_config = {
                "name": "valid_agent",
                "type": "generic",
                "description": "有效配置",
                "capabilities": ["code_execution"],
                "timeout_seconds": 300,
                "priority": 5
            }
            
            result = ConfigValidator.validate(valid_config)
            if not result.is_valid:
                return False, f"有效配置验证失败: {result.errors}"
            
            # 无效配置（缺少必填字段）
            invalid_config = {
                "name": "invalid_agent",
                "type": "invalid_type"  # 无效类型
            }
            
            result = ConfigValidator.validate(invalid_config)
            if result.is_valid:
                return False, "无效配置应该验证失败但通过了"
            
            return True, "配置验证测试通过"
        except Exception as e:
            return False, f"配置验证异常: {e}"
    
    def test_config_validator(self) -> tuple:
        """测试配置验证器的各种检查"""
        try:
            # 测试必填字段检查
            missing_fields = {"name": "test"}
            result = ConfigValidator.validate(missing_fields)
            if result.is_valid:
                return False, "缺少必填字段应该验证失败"
            if not any("必填字段" in e for e in result.errors):
                return False, f"错误信息不正确: {result.errors}"
            
            # 测试类型检查
            invalid_type = {
                "name": "test",
                "type": "unknown_type",
                "description": "测试",
                "capabilities": ["code_execution"]
            }
            result = ConfigValidator.validate(invalid_type)
            if result.is_valid:
                return False, "无效类型应该验证失败"
            
            # 测试能力检查
            invalid_capability = {
                "name": "test",
                "type": "generic",
                "description": "测试",
                "capabilities": ["invalid_capability"]
            }
            result = ConfigValidator.validate(invalid_capability)
            if result.is_valid:
                return False, "无效能力应该验证失败"
            
            return True, "配置验证器测试通过"
        except Exception as e:
            return False, f"配置验证器异常: {e}"
    
    def test_subagent_registry(self) -> tuple:
        """测试子代理注册表"""
        try:
            registry = SubagentRegistry()
            
            # 注册配置
            config1 = SubagentConfig(
                name="agent1",
                type=SubagentType.GENERIC,
                description="代理1",
                capabilities=[Capability.CODE_EXECUTION]
            )
            
            config2 = SubagentConfig(
                name="agent2",
                type=SubagentType.BASH,
                description="代理2",
                capabilities=[Capability.SHELL_EXECUTION]
            )
            
            result1 = registry.register(config1)
            if not result1.is_valid:
                return False, f"注册agent1失败: {result1.errors}"
            
            result2 = registry.register(config2)
            if not result2.is_valid:
                return False, f"注册agent2失败: {result2.errors}"
            
            # 查询测试
            if registry.get("agent1") is None:
                return False, "获取agent1失败"
            
            if len(registry.list_all()) != 2:
                return False, f"注册数量不正确: {len(registry.list_all())}"
            
            if len(registry.list_by_type(SubagentType.GENERIC)) != 1:
                return False, "按类型查询失败"
            
            # 统计测试
            stats = registry.get_stats()
            if stats["total"] != 2:
                return False, f"统计总数不正确: {stats['total']}"
            
            return True, "子代理注册表测试通过"
        except Exception as e:
            return False, f"子代理注册表异常: {e}"
    
    def test_config_serialization(self) -> tuple:
        """测试配置序列化"""
        try:
            # 创建配置
            config = SubagentConfig(
                name="serialize_test",
                type=SubagentType.SQL,
                description="序列化测试",
                capabilities=[Capability.QUERY_EXECUTION, Capability.SCHEMA_ANALYSIS],
                config={
                    "max_query_size": 10000,
                    "allowed_operations": ["SELECT", "EXPLAIN"]
                }
            )
            
            # 序列化
            config_dict = config.to_dict()
            
            if config_dict["name"] != "serialize_test":
                return False, "序列化name不正确"
            if config_dict["type"] != "sql":
                return False, "序列化type不正确"
            if len(config_dict["capabilities"]) != 2:
                return False, "序列化capabilities不正确"
            
            # 反序列化
            restored = SubagentConfig.from_dict(config_dict)
            
            if restored.name != config.name:
                return False, "反序列化name不正确"
            if restored.type != config.type:
                return False, "反序列化type不正确"
            if restored.config != config.config:
                return False, "反序列化config不正确"
            
            return True, "配置序列化测试通过"
        except Exception as e:
            return False, f"配置序列化异常: {e}"
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行SubagentConfig配置系统测试套件...")
        print("=" * 60)
        
        passed = 0
        failed = 0
        results = {}
        
        for test_name, test_func in self.tests:
            print(f"📋 运行测试: {test_name}...")
            try:
                success, message = test_func()
                if success:
                    print(f"   ✅ 通过: {message}")
                    passed += 1
                    results[test_name] = {"passed": True, "message": message}
                else:
                    print(f"   ❌ 失败: {message}")
                    failed += 1
                    results[test_name] = {"passed": False, "message": message}
            except Exception as e:
                print(f"   ❌ 异常: {str(e)}")
                failed += 1
                results[test_name] = {"passed": False, "message": str(e)}
        
        print("=" * 60)
        print(f"📊 测试摘要:")
        print(f"   总测试数: {len(self.tests)}")
        print(f"   通过测试: {passed}")
        print(f"   失败测试: {failed}")
        print(f"   成功率: {passed / len(self.tests) * 100:.1f}%")
        
        return {
            "summary": {
                "total_tests": len(self.tests),
                "passed_tests": passed,
                "failed_tests": failed,
                "success_rate": passed / len(self.tests) * 100 if len(self.tests) > 0 else 0
            },
            "detailed_results": results
        }


def main_demo():
    """主演示函数"""
    print("🎓 Day 11 Lesson 41: SubagentConfig配置结构演示")
    print("=" * 60)
    
    # 1. 创建配置对象
    print("\n1. 创建子代理配置:")
    
    python_expert = SubagentConfig(
        name="python_expert",
        type=SubagentType.PYTHON,
        description="Python代码执行专家",
        capabilities=[Capability.CODE_EXECUTION, Capability.DEBUGGING],
        timeout_seconds=300,
        max_memory_mb=1024,
        config={
            "python_version": "3.12",
            "allowed_modules": ["os", "json", "math", "datetime"]
        }
    )
    
    bash_expert = SubagentConfig(
        name="bash_expert",
        type=SubagentType.BASH,
        description="Bash命令执行专家",
        capabilities=[Capability.SHELL_EXECUTION, Capability.FILE_OPERATIONS],
        timeout_seconds=60,
        config={
            "allowed_commands": ["ls", "cat", "grep", "find", "head", "tail"],
            "workdir": "/tmp"
        }
    )
    
    sql_expert = SubagentConfig(
        name="sql_expert",
        type=SubagentType.SQL,
        description="SQL查询执行专家",
        capabilities=[Capability.QUERY_EXECUTION, Capability.SCHEMA_ANALYSIS],
        priority=3,
        config={
            "max_query_size": 10000,
            "allowed_operations": ["SELECT", "EXPLAIN"]
        }
    )
    
    print(f"   ✅ python_expert: {python_expert.type.value} - {python_expert.description}")
    print(f"   ✅ bash_expert: {bash_expert.type.value} - {bash_expert.description}")
    print(f"   ✅ sql_expert: {sql_expert.type.value} - {sql_expert.description}")
    
    # 2. 配置验证演示
    print("\n2. 配置验证演示:")
    
    # 有效配置
    valid_config = {
        "name": "web_agent",
        "type": "web",
        "description": "Web操作代理",
        "capabilities": ["web_scraping", "api_calling"],
        "timeout_seconds": 120
    }
    
    result = ConfigValidator.validate(valid_config)
    print(f"   有效配置验证: {'✅ 通过' if result.is_valid else '❌ 失败'}")
    if result.warnings:
        print(f"   警告: {result.warnings}")
    
    # 无效配置
    invalid_config = {
        "name": "",
        "type": "unknown",
        "description": "测试",
        "capabilities": ["invalid"]
    }
    
    result = ConfigValidator.validate(invalid_config)
    print(f"   无效配置验证: {'✅ 正确拒绝' if not result.is_valid else '❌ 应该拒绝'}")
    print(f"   错误信息: {result.errors}")
    
    # 3. 子代理注册表演示
    print("\n3. 子代理注册表演示:")
    
    registry = SubagentRegistry()
    
    # 注册配置
    for config in [python_expert, bash_expert, sql_expert]:
        result = registry.register(config)
        if result.is_valid:
            print(f"   ✅ 已注册: {config.name}")
        else:
            print(f"   ❌ 注册失败: {config.name} - {result.errors}")
    
    # 查询配置
    print(f"\n   所有子代理: {[c.name for c in registry.list_all()]}")
    print(f"   已启用子代理: {[c.name for c in registry.list_enabled()]}")
    print(f"   generic类型: {[c.name for c in registry.list_by_type(SubagentType.GENERIC)]}")
    print(f"   bash类型: {[c.name for c in registry.list_by_type(SubagentType.BASH)]}")
    
    # 统计信息
    stats = registry.get_stats()
    print(f"\n   注册表统计:")
    print(f"     总数: {stats['total']}")
    print(f"     已启用: {stats['enabled']}")
    print(f"     按类型: {stats['by_type']}")
    
    # 4. 配置序列化演示
    print("\n4. 配置序列化演示:")
    
    config_dict = python_expert.to_dict()
    print(f"   序列化结果（部分）:")
    print(f"     name: {config_dict['name']}")
    print(f"     type: {config_dict['type']}")
    print(f"     capabilities: {config_dict['capabilities']}")
    
    # 反序列化
    restored = SubagentConfig.from_dict(config_dict)
    print(f"   反序列化结果: {restored.name} ({restored.type.value})")
    
    print("\n5. 演示完成!")


def run_tests():
    """运行测试套件"""
    test_suite = ConfigTestSuite()
    report = test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 SubagentConfig配置系统测试套件验证通过")
        return True
    else:
        print("\n⚠️  有测试失败，请检查实现代码")
        return False


if __name__ == "__main__":
    import sys
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
    elif len(sys.argv) > 1 and sys.argv[1] == "--demo":
        main_demo()
    else:
        main_demo()
