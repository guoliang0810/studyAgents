#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 3 Lesson 11: 技能系统集成 (Skill System Integration)
课堂演示代码 - 技能系统架构与实现

本文件展示了完整的技能系统集成方案，包含四个部分：
1. 技能系统架构模拟 - 展示整体架构设计和核心组件
2. 技能注册表状态机实现 - 实现技能注册、发现、加载的完整状态机
3. 技能模块化设计演示 - 展示具体技能类的实现和模块化设计
4. 技能系统架构分析与最佳实践 - 分析设计模式、性能优化和架构决策

教学目标：
- 理解技能系统在AI Agent架构中的定位和作用
- 掌握技能基类(Skill)的设计原则和接口规范
- 了解技能注册表(SkillRegistry)的实现机制
- 理解动态技能发现和加载的技术原理

作者：张老师（10年AI系统架构经验，DeerFlow核心贡献者）
版本：v1.0
创建日期：2024年3月27日
"""

import os
import sys
import importlib
import importlib.util
import inspect
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import time
import hashlib
import warnings

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("skill_system.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 第一部分：技能系统架构模拟
# ============================================================================


class SkillExecutionResult:
    """技能执行结果类 - 统一结果格式"""

    def __init__(
        self,
        success: bool,
        output: Any = None,
        error_message: Optional[str] = None,
        execution_time_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.output = output
        self.error_message = error_message
        self.execution_time_ms = execution_time_ms
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "output": self.output,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        status = "成功" if self.success else "失败"
        return f"SkillExecutionResult({status}, output={self.output}, time={self.execution_time_ms}ms)"


class SkillCategory(Enum):
    """技能分类枚举"""

    DATA_PROCESSING = auto()  # 数据处理
    FILE_OPERATION = auto()  # 文件操作
    NETWORK_COMMUNICATION = auto()  # 网络通信
    AI_MODEL = auto()  # AI模型
    UTILITY = auto()  # 实用工具
    CUSTOM = auto()  # 自定义


@dataclass
class SkillMetadata:
    """技能元数据 - 描述技能的基本信息"""

    name: str  # 技能名称
    description: str  # 技能描述
    version: str = "1.0.0"  # 版本号
    author: str = "Unknown"  # 作者
    category: SkillCategory = SkillCategory.CUSTOM  # 分类
    tags: List[str] = field(default_factory=list)  # 标签
    dependencies: List[str] = field(default_factory=list)  # 依赖
    input_schema: Optional[Dict[str, Any]] = None  # 输入模式
    output_schema: Optional[Dict[str, Any]] = None  # 输出模式
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))

    def validate(self) -> List[str]:
        """验证元数据的完整性"""
        errors = []
        if not self.name or not self.name.strip():
            errors.append("技能名称不能为空")
        if not self.description or not self.description.strip():
            errors.append("技能描述不能为空")
        if not self.version or not self.version.strip():
            errors.append("版本号不能为空")
        # 验证版本号格式 (语义化版本)
        import re

        version_pattern = r"^\d+\.\d+\.\d+$"
        if not re.match(version_pattern, self.version):
            errors.append(f"版本号格式不正确: {self.version}，应为x.y.z格式")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "category": self.category.name,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "created_at": self.created_at,
        }


class Skill(ABC):
    """技能基类 - 所有技能必须继承此类并实现抽象方法"""

    # 类属性：技能元数据（每个子类必须定义）
    metadata: SkillMetadata

    def __init__(self):
        """初始化技能实例"""
        self._initialized = False
        self._validation_errors = []
        self._initialize()

    def _initialize(self):
        """内部初始化方法"""
        # 验证元数据
        if not hasattr(self, "metadata") or not isinstance(
            self.metadata, SkillMetadata
        ):
            self._validation_errors.append("技能必须定义metadata属性")
            return

        errors = self.metadata.validate()
        if errors:
            self._validation_errors.extend(errors)
            return

        # 调用子类的自定义初始化
        if hasattr(self, "on_initialize"):
            try:
                self.on_initialize()
            except Exception as e:
                self._validation_errors.append(f"初始化失败: {str(e)}")
                return

        self._initialized = True
        logger.info(f"技能 '{self.metadata.name}' 初始化成功")

    @abstractmethod
    def execute(self, **kwargs) -> SkillExecutionResult:
        """
        执行技能的核心方法

        Args:
            **kwargs: 技能执行所需的参数

        Returns:
            SkillExecutionResult: 执行结果
        """
        pass

    @abstractmethod
    def validate_input(self, **kwargs) -> List[str]:
        """
        验证输入参数的合法性

        Args:
            **kwargs: 要验证的输入参数

        Returns:
            List[str]: 错误信息列表，空列表表示验证通过
        """
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """
        获取技能的能力描述

        Returns:
            Dict[str, Any]: 能力描述信息
        """
        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "category": self.metadata.category.name,
            "version": self.metadata.version,
            "input_schema": self.metadata.input_schema,
            "output_schema": self.metadata.output_schema,
        }

    def is_valid(self) -> bool:
        """检查技能是否有效（已正确初始化）"""
        return self._initialized and len(self._validation_errors) == 0

    def get_validation_errors(self) -> List[str]:
        """获取验证错误信息"""
        return self._validation_errors.copy()

    def __repr__(self) -> str:
        status = "有效" if self.is_valid() else "无效"
        return f"Skill(name='{self.metadata.name}', version={self.metadata.version}, status={status})"


class SkillRegistry:
    """技能注册表 - 管理所有技能实例"""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._skill_classes: Dict[str, Type[Skill]] = {}
        self._skill_metadata: Dict[str, SkillMetadata] = {}
        self._category_index: Dict[SkillCategory, Set[str]] = {
            category: set() for category in SkillCategory
        }
        self._tag_index: Dict[str, Set[str]] = {}
        self._initialized = False
        self._initialize_registry()

    def _initialize_registry(self):
        """初始化注册表"""
        self._initialized = True
        logger.info("技能注册表初始化完成")

    def register_skill(self, skill_class: Type[Skill]) -> bool:
        """
        注册技能类

        Args:
            skill_class: 技能类（必须是Skill的子类）

        Returns:
            bool: 注册是否成功
        """
        try:
            # 验证技能类
            if not issubclass(skill_class, Skill):
                logger.error(f"注册失败：{skill_class.__name__} 不是Skill的子类")
                return False

            # 创建技能实例以获取元数据
            skill_instance = skill_class()
            if not skill_instance.is_valid():
                errors = skill_instance.get_validation_errors()
                logger.error(f"技能验证失败：{skill_class.__name__}, 错误: {errors}")
                return False

            skill_name = skill_instance.metadata.name

            # 检查是否已注册
            if skill_name in self._skill_classes:
                logger.warning(f"技能 '{skill_name}' 已注册，跳过重复注册")
                return False

            # 注册技能
            self._skill_classes[skill_name] = skill_class
            self._skill_metadata[skill_name] = skill_instance.metadata

            # 更新索引
            category = skill_instance.metadata.category
            self._category_index[category].add(skill_name)

            for tag in skill_instance.metadata.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(skill_name)

            logger.info(f"技能 '{skill_name}' 注册成功")
            return True

        except Exception as e:
            logger.error(f"注册技能失败：{str(e)}")
            return False

    def get_skill(
        self, skill_name: str, create_instance: bool = True
    ) -> Optional[Union[Skill, Type[Skill]]]:
        """
        获取技能实例或类

        Args:
            skill_name: 技能名称
            create_instance: 是否创建实例（True返回实例，False返回类）

        Returns:
            技能实例或类，如果不存在则返回None
        """
        if skill_name not in self._skill_classes:
            logger.warning(f"技能 '{skill_name}' 未注册")
            return None

        if create_instance:
            # 创建新实例
            try:
                skill_class = self._skill_classes[skill_name]
                instance = skill_class()
                if instance.is_valid():
                    return instance
                else:
                    logger.error(f"技能 '{skill_name}' 实例创建失败")
                    return None
            except Exception as e:
                logger.error(f"创建技能实例失败：{str(e)}")
                return None
        else:
            # 返回技能类
            return self._skill_classes[skill_name]

    def get_skill_metadata(self, skill_name: str) -> Optional[SkillMetadata]:
        """获取技能元数据"""
        return self._skill_metadata.get(skill_name)

    def list_skills(
        self, category: Optional[SkillCategory] = None, tags: Optional[List[str]] = None
    ) -> List[str]:
        """
        列出符合条件的技能名称

        Args:
            category: 技能分类筛选
            tags: 标签筛选（需要包含所有指定标签）

        Returns:
            符合条件的技能名称列表
        """
        if category is None and tags is None:
            # 返回所有技能
            return list(self._skill_classes.keys())

        # 按分类筛选
        if category is not None:
            candidates = self._category_index[category].copy()
        else:
            candidates = set(self._skill_classes.keys())

        # 按标签筛选
        if tags:
            for tag in tags:
                if tag in self._tag_index:
                    candidates &= self._tag_index[tag]
                else:
                    # 如果标签不存在，返回空集
                    candidates = set()
                    break

        return list(candidates)

    def get_skill_count(self) -> int:
        """获取已注册技能数量"""
        return len(self._skill_classes)

    def get_skills_by_category(self) -> Dict[SkillCategory, List[str]]:
        """按分类获取技能"""
        result = {}
        for category, skill_names in self._category_index.items():
            if skill_names:
                result[category] = list(skill_names)
        return result

    def clear(self):
        """清空注册表"""
        self._skills.clear()
        self._skill_classes.clear()
        self._skill_metadata.clear()
        self._category_index = {category: set() for category in SkillCategory}
        self._tag_index.clear()
        logger.info("技能注册表已清空")


# ============================================================================
# 第二部分：技能注册表状态机实现
# ============================================================================


class SkillRegistryState(Enum):
    """技能注册表状态枚举"""

    UNINITIALIZED = auto()  # 未初始化
    INITIALIZING = auto()  # 初始化中
    READY = auto()  # 就绪
    SCANNING = auto()  # 扫描中
    LOADING = auto()  # 加载中
    ERROR = auto()  # 错误
    SHUTDOWN = auto()  # 关闭


class SkillRegistryStateMachine:
    """技能注册表状态机 - 管理注册表生命周期"""

    def __init__(self):
        self._state = SkillRegistryState.UNINITIALIZED
        self._state_transitions = self._create_state_transitions()
        self._state_handlers = self._create_state_handlers()
        self._error_message = None
        self._last_transition_time = time.time()
        self._transition_history = []

    def _create_state_transitions(
        self,
    ) -> Dict[SkillRegistryState, Set[SkillRegistryState]]:
        """创建状态转移规则"""
        transitions = {
            SkillRegistryState.UNINITIALIZED: {
                SkillRegistryState.INITIALIZING,
                SkillRegistryState.ERROR,
            },
            SkillRegistryState.INITIALIZING: {
                SkillRegistryState.READY,
                SkillRegistryState.ERROR,
            },
            SkillRegistryState.READY: {
                SkillRegistryState.SCANNING,
                SkillRegistryState.LOADING,
                SkillRegistryState.SHUTDOWN,
                SkillRegistryState.ERROR,
            },
            SkillRegistryState.SCANNING: {
                SkillRegistryState.READY,
                SkillRegistryState.LOADING,
                SkillRegistryState.ERROR,
            },
            SkillRegistryState.LOADING: {
                SkillRegistryState.READY,
                SkillRegistryState.ERROR,
            },
            SkillRegistryState.ERROR: {
                SkillRegistryState.READY,
                SkillRegistryState.SHUTDOWN,
            },
            SkillRegistryState.SHUTDOWN: set(),  # 终止状态
        }
        return transitions

    def _create_state_handlers(self) -> Dict[SkillRegistryState, Callable]:
        """创建状态处理器"""
        return {
            SkillRegistryState.UNINITIALIZED: self._handle_uninitialized,
            SkillRegistryState.INITIALIZING: self._handle_initializing,
            SkillRegistryState.READY: self._handle_ready,
            SkillRegistryState.SCANNING: self._handle_scanning,
            SkillRegistryState.LOADING: self._handle_loading,
            SkillRegistryState.ERROR: self._handle_error,
            SkillRegistryState.SHUTDOWN: self._handle_shutdown,
        }

    def transition_to(self, new_state: SkillRegistryState, **kwargs) -> bool:
        """
        尝试转移到新状态

        Args:
            new_state: 目标状态
            **kwargs: 转移参数

        Returns:
            bool: 转移是否成功
        """
        # 检查是否允许转移
        if new_state not in self._state_transitions.get(self._state, set()):
            logger.error(f"不允许从 {self._state.name} 转移到 {new_state.name}")
            return False

        # 执行状态退出处理
        if hasattr(self, f"_exit_{self._state.name.lower()}"):
            exit_handler = getattr(self, f"_exit_{self._state.name.lower()}")
            exit_handler(**kwargs)

        old_state = self._state
        self._state = new_state
        self._last_transition_time = time.time()

        # 记录转移历史
        self._transition_history.append(
            {
                "timestamp": time.time(),
                "from": old_state.name,
                "to": new_state.name,
                "kwargs": kwargs,
            }
        )

        logger.info(f"状态转移: {old_state.name} -> {new_state.name}")

        # 执行状态进入处理
        if hasattr(self, f"_enter_{new_state.name.lower()}"):
            enter_handler = getattr(self, f"_enter_{new_state.name.lower()}")
            enter_handler(**kwargs)

        # 执行状态处理器
        handler = self._state_handlers.get(new_state)
        if handler:
            try:
                handler(**kwargs)
            except Exception as e:
                logger.error(f"状态处理器执行失败: {str(e)}")
                self.transition_to(SkillRegistryState.ERROR, error=str(e))
                return False

        return True

    def _handle_uninitialized(self, **kwargs):
        """处理未初始化状态"""
        logger.debug("技能注册表未初始化，等待初始化指令")

    def _handle_initializing(self, **kwargs):
        """处理初始化中状态"""
        logger.info("正在初始化技能注册表...")
        # 模拟初始化过程
        time.sleep(0.1)  # 模拟初始化延迟
        logger.info("技能注册表初始化完成")
        self.transition_to(SkillRegistryState.READY)

    def _handle_ready(self, **kwargs):
        """处理就绪状态"""
        logger.debug("技能注册表就绪，等待操作指令")

    def _handle_scanning(self, **kwargs):
        """处理扫描中状态"""
        scan_path = kwargs.get("scan_path", ".")
        logger.info(f"正在扫描技能目录: {scan_path}")

        # 模拟扫描过程
        time.sleep(0.2)  # 模拟扫描延迟

        # 模拟扫描结果
        discovered_skills = kwargs.get("discovered_skills", [])
        if discovered_skills:
            logger.info(f"发现 {len(discovered_skills)} 个技能")

        # 扫描完成后转移到就绪状态
        self.transition_to(
            SkillRegistryState.READY, discovered_skills=discovered_skills
        )

    def _handle_loading(self, **kwargs):
        """处理加载中状态"""
        skill_module = kwargs.get("skill_module")
        skill_class = kwargs.get("skill_class")

        if skill_module and skill_class:
            logger.info(f"正在加载技能: {skill_class} 来自模块: {skill_module}")
            time.sleep(0.1)  # 模拟加载延迟
            logger.info(f"技能加载成功: {skill_class}")
        else:
            logger.warning("加载技能时缺少必要参数")

        # 加载完成后转移到就绪状态
        self.transition_to(SkillRegistryState.READY)

    def _handle_error(self, **kwargs):
        """处理错误状态"""
        error = kwargs.get("error", "未知错误")
        self._error_message = str(error)
        logger.error(f"技能注册表进入错误状态: {error}")

    def _handle_shutdown(self, **kwargs):
        """处理关闭状态"""
        logger.info("技能注册表正在关闭...")
        # 执行清理操作
        time.sleep(0.1)  # 模拟清理延迟
        logger.info("技能注册表已关闭")

    def get_state(self) -> SkillRegistryState:
        """获取当前状态"""
        return self._state

    def get_error_message(self) -> Optional[str]:
        """获取错误信息"""
        return self._error_message

    def get_transition_history(self) -> List[Dict[str, Any]]:
        """获取转移历史"""
        return self._transition_history.copy()

    def can_transition_to(self, target_state: SkillRegistryState) -> bool:
        """检查是否可以转移到目标状态"""
        return target_state in self._state_transitions.get(self._state, set())

    def initialize(self) -> bool:
        """初始化技能注册表"""
        return self.transition_to(SkillRegistryState.INITIALIZING)

    def scan_directory(self, scan_path: str) -> bool:
        """扫描技能目录"""
        return self.transition_to(SkillRegistryState.SCANNING, scan_path=scan_path)

    def load_skill(self, skill_module: str, skill_class: str) -> bool:
        """加载技能"""
        return self.transition_to(
            SkillRegistryState.LOADING,
            skill_module=skill_module,
            skill_class=skill_class,
        )

    def shutdown(self) -> bool:
        """关闭技能注册表"""
        return self.transition_to(SkillRegistryState.SHUTDOWN)


class DynamicSkillLoader:
    """动态技能加载器 - 实现运行时技能发现和加载"""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.state_machine = SkillRegistryStateMachine()
        self.loaded_modules: Set[str] = set()
        self.skill_directory = "skills"  # 默认技能目录

    def discover_skills(self, directory: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        发现目录中的技能

        Args:
            directory: 要扫描的目录，默认为self.skill_directory

        Returns:
            发现的技能信息列表
        """
        if not self.state_machine.can_transition_to(SkillRegistryState.SCANNING):
            logger.error("无法开始扫描：状态机不允许")
            return []

        scan_dir = directory or self.skill_directory

        # 创建技能目录（如果不存在）
        Path(scan_dir).mkdir(parents=True, exist_ok=True)

        # 开始扫描
        if not self.state_machine.scan_directory(scan_dir):
            logger.error("扫描技能目录失败")
            return []

        discovered_skills = []

        try:
            # 扫描Python文件
            for py_file in Path(scan_dir).glob("*.py"):
                if py_file.name.startswith("_"):
                    continue  # 跳过私有模块

                module_name = py_file.stem
                skills_in_file = self._extract_skills_from_file(py_file, module_name)
                discovered_skills.extend(skills_in_file)

            logger.info(f"在目录 '{scan_dir}' 中发现 {len(discovered_skills)} 个技能")

        except Exception as e:
            logger.error(f"扫描技能目录失败: {str(e)}")
            self.state_machine.transition_to(SkillRegistryState.ERROR, error=str(e))

        return discovered_skills

    def _extract_skills_from_file(
        self, file_path: Path, module_name: str
    ) -> List[Dict[str, Any]]:
        """
        从Python文件中提取技能类

        Args:
            file_path: Python文件路径
            module_name: 模块名称

        Returns:
            技能信息列表
        """
        skills = []

        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                return skills

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找Skill的子类
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, Skill)
                    and obj != Skill
                    and hasattr(obj, "metadata")
                ):
                    skill_info = {
                        "file_path": str(file_path),
                        "module_name": module_name,
                        "skill_class": name,
                        "metadata": obj.metadata.to_dict(),
                        "class_object": obj,
                    }
                    skills.append(skill_info)
                    logger.debug(f"发现技能: {name} 在模块: {module_name}")

        except Exception as e:
            logger.error(f"提取技能失败 {file_path}: {str(e)}")

        return skills

    def load_discovered_skill(self, skill_info: Dict[str, Any]) -> bool:
        """
        加载发现的技能

        Args:
            skill_info: 技能信息字典

        Returns:
            bool: 加载是否成功
        """
        module_name = skill_info["module_name"]
        skill_class = skill_info["skill_class"]

        if not self.state_machine.can_transition_to(SkillRegistryState.LOADING):
            logger.error("无法加载技能：状态机不允许")
            return False

        # 开始加载
        if not self.state_machine.load_skill(module_name, skill_class):
            logger.error("开始加载技能失败")
            return False

        try:
            # 获取技能类
            skill_class_obj = skill_info["class_object"]

            # 注册技能
            success = self.registry.register_skill(skill_class_obj)

            if success:
                self.loaded_modules.add(module_name)
                logger.info(f"技能 '{skill_class}' 加载成功")
            else:
                logger.warning(f"技能 '{skill_class}' 注册失败")

            return success

        except Exception as e:
            logger.error(f"加载技能失败: {str(e)}")
            self.state_machine.transition_to(SkillRegistryState.ERROR, error=str(e))
            return False

    def load_all_discovered_skills(
        self, discovered_skills: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        加载所有发现的技能

        Args:
            discovered_skills: 发现的技能列表

        Returns:
            加载结果字典 {技能名称: 是否成功}
        """
        results = {}

        for skill_info in discovered_skills:
            skill_name = skill_info["metadata"]["name"]
            success = self.load_discovered_skill(skill_info)
            results[skill_name] = success

        return results

    def get_loaded_modules(self) -> List[str]:
        """获取已加载的模块列表"""
        return list(self.loaded_modules)

    def get_loader_status(self) -> Dict[str, Any]:
        """获取加载器状态"""
        return {
            "state": self.state_machine.get_state().name,
            "loaded_modules_count": len(self.loaded_modules),
            "registered_skills_count": self.registry.get_skill_count(),
            "error_message": self.state_machine.get_error_message(),
        }


# ============================================================================
# 第三部分：技能模块化设计演示
# ============================================================================


# 示例技能1：数据分析技能
class DataAnalysisSkill(Skill):
    """数据分析技能 - 演示数据处理功能"""

    metadata = SkillMetadata(
        name="data_analysis",
        description="提供基本的数据分析功能，包括统计、过滤、转换等",
        version="1.2.0",
        author="Data Team",
        category=SkillCategory.DATA_PROCESSING,
        tags=["data", "analysis", "statistics", "pandas"],
        dependencies=["pandas", "numpy"],
        input_schema={
            "type": "object",
            "properties": {
                "data": {"type": "array", "description": "输入数据列表"},
                "operation": {
                    "type": "string",
                    "enum": ["mean", "median", "sum", "filter", "transform"],
                    "description": "操作类型",
                },
                "filter_condition": {
                    "type": "string",
                    "description": "过滤条件（仅对filter操作）",
                },
                "transform_function": {
                    "type": "string",
                    "description": "转换函数（仅对transform操作）",
                },
            },
            "required": ["data", "operation"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "result": {"description": "分析结果"},
                "statistics": {"description": "统计信息"},
                "processed_count": {"type": "integer", "description": "处理的数据量"},
            },
        },
    )

    def on_initialize(self):
        """自定义初始化"""
        try:
            import pandas as pd
            import numpy as np

            self._has_dependencies = True
        except ImportError:
            self._has_dependencies = False
            logger.warning("数据分析技能依赖缺失：pandas, numpy")

    def validate_input(self, **kwargs) -> List[str]:
        """验证输入参数"""
        errors = []

        # 检查必需参数
        if "data" not in kwargs:
            errors.append("缺少必需参数: data")
        if "operation" not in kwargs:
            errors.append("缺少必需参数: operation")

        if errors:
            return errors

        data = kwargs["data"]
        operation = kwargs["operation"]

        # 验证数据类型
        if not isinstance(data, list):
            errors.append("参数 'data' 必须是列表")

        # 验证操作类型
        valid_operations = ["mean", "median", "sum", "filter", "transform"]
        if operation not in valid_operations:
            errors.append(
                f"参数 'operation' 必须是以下之一: {', '.join(valid_operations)}"
            )

        # 验证特定操作的参数
        if operation == "filter" and "filter_condition" not in kwargs:
            errors.append("filter操作需要 'filter_condition' 参数")
        if operation == "transform" and "transform_function" not in kwargs:
            errors.append("transform操作需要 'transform_function' 参数")

        return errors

    def execute(self, **kwargs) -> SkillExecutionResult:
        """执行数据分析"""
        start_time = time.time()

        # 验证输入
        validation_errors = self.validate_input(**kwargs)
        if validation_errors:
            return SkillExecutionResult(
                success=False,
                error_message=f"输入验证失败: {', '.join(validation_errors)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # 检查依赖
        if not self._has_dependencies:
            return SkillExecutionResult(
                success=False,
                error_message="缺少依赖: pandas, numpy",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            import pandas as pd
            import numpy as np

            data = kwargs["data"]
            operation = kwargs["operation"]

            # 创建DataFrame
            df = pd.DataFrame(data)

            # 执行操作
            result = None
            statistics = {}

            if operation == "mean":
                result = df.mean().to_dict()
                statistics = {
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "operation": "mean",
                }

            elif operation == "median":
                result = df.median().to_dict()
                statistics = {
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "operation": "median",
                }

            elif operation == "sum":
                result = df.sum().to_dict()
                statistics = {
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "operation": "sum",
                }

            elif operation == "filter":
                condition = kwargs["filter_condition"]
                # 注意：实际应用中应该安全地处理条件表达式
                filtered_df = df.query(condition) if hasattr(df, "query") else df
                result = filtered_df.to_dict("records")
                statistics = {
                    "original_count": len(df),
                    "filtered_count": len(filtered_df),
                    "filter_condition": condition,
                }

            elif operation == "transform":
                transform_func = kwargs["transform_function"]
                # 注意：实际应用中应该安全地处理转换函数
                transformed_df = df.apply(eval(transform_func))
                result = transformed_df.to_dict("records")
                statistics = {
                    "original_count": len(df),
                    "transformed_count": len(transformed_df),
                    "transform_function": transform_func,
                }

            execution_time_ms = (time.time() - start_time) * 1000

            return SkillExecutionResult(
                success=True,
                output=result,
                execution_time_ms=execution_time_ms,
                metadata={
                    "statistics": statistics,
                    "processed_count": len(data),
                    "operation": operation,
                },
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return SkillExecutionResult(
                success=False,
                error_message=f"执行数据分析失败: {str(e)}",
                execution_time_ms=execution_time_ms,
            )


# 示例技能2：文件处理技能
class FileProcessingSkill(Skill):
    """文件处理技能 - 演示文件操作功能"""

    metadata = SkillMetadata(
        name="file_processing",
        description="提供文件读写、格式转换、批量处理等功能",
        version="1.1.0",
        author="System Team",
        category=SkillCategory.FILE_OPERATION,
        tags=["file", "io", "processing", "batch"],
        dependencies=[],
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read", "write", "convert", "list"],
                    "description": "操作类型",
                },
                "file_path": {"type": "string", "description": "文件路径"},
                "content": {
                    "type": "string",
                    "description": "文件内容（仅对write操作）",
                },
                "source_format": {
                    "type": "string",
                    "description": "源格式（仅对convert操作）",
                },
                "target_format": {
                    "type": "string",
                    "description": "目标格式（仅对convert操作）",
                },
                "directory": {
                    "type": "string",
                    "description": "目录路径（仅对list操作）",
                },
            },
            "required": ["operation"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "result": {"description": "操作结果"},
                "file_info": {"description": "文件信息"},
                "processed_files": {"type": "integer", "description": "处理的文件数量"},
            },
        },
    )

    def validate_input(self, **kwargs) -> List[str]:
        """验证输入参数"""
        errors = []

        if "operation" not in kwargs:
            errors.append("缺少必需参数: operation")
            return errors

        operation = kwargs["operation"]

        if operation in ["read", "write", "convert"]:
            if "file_path" not in kwargs:
                errors.append(f"{operation}操作需要 'file_path' 参数")

        if operation == "write":
            if "content" not in kwargs:
                errors.append("write操作需要 'content' 参数")

        if operation == "convert":
            if "source_format" not in kwargs:
                errors.append("convert操作需要 'source_format' 参数")
            if "target_format" not in kwargs:
                errors.append("convert操作需要 'target_format' 参数")

        if operation == "list":
            if "directory" not in kwargs:
                errors.append("list操作需要 'directory' 参数")

        return errors

    def execute(self, **kwargs) -> SkillExecutionResult:
        """执行文件处理"""
        start_time = time.time()

        # 验证输入
        validation_errors = self.validate_input(**kwargs)
        if validation_errors:
            return SkillExecutionResult(
                success=False,
                error_message=f"输入验证失败: {', '.join(validation_errors)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        operation = kwargs["operation"]

        try:
            result = None
            file_info = {}
            processed_files = 0

            if operation == "read":
                file_path = kwargs["file_path"]
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                result = content
                file_info = {
                    "path": file_path,
                    "size": os.path.getsize(file_path)
                    if os.path.exists(file_path)
                    else 0,
                    "exists": os.path.exists(file_path),
                }
                processed_files = 1

            elif operation == "write":
                file_path = kwargs["file_path"]
                content = kwargs["content"]
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                result = {"message": f"文件写入成功: {file_path}"}
                file_info = {
                    "path": file_path,
                    "size": len(content.encode("utf-8")),
                    "created": True,
                }
                processed_files = 1

            elif operation == "convert":
                # 模拟格式转换
                file_path = kwargs["file_path"]
                source_format = kwargs["source_format"]
                target_format = kwargs["target_format"]

                # 这里只是示例，实际需要实现具体转换逻辑
                result = {
                    "message": f"格式转换: {source_format} -> {target_format}",
                    "original_file": file_path,
                    "converted_file": file_path.replace(
                        f".{source_format}", f".{target_format}"
                    ),
                }
                file_info = {
                    "source_format": source_format,
                    "target_format": target_format,
                    "conversion_supported": True,
                }
                processed_files = 1

            elif operation == "list":
                directory = kwargs["directory"]
                if not os.path.exists(directory):
                    result = {"files": [], "error": "目录不存在"}
                else:
                    files = []
                    for item in os.listdir(directory):
                        item_path = os.path.join(directory, item)
                        files.append(
                            {
                                "name": item,
                                "is_file": os.path.isfile(item_path),
                                "size": os.path.getsize(item_path)
                                if os.path.isfile(item_path)
                                else 0,
                                "modified": time.ctime(os.path.getmtime(item_path)),
                            }
                        )
                    result = {"files": files}
                    processed_files = len(files)

            execution_time_ms = (time.time() - start_time) * 1000

            return SkillExecutionResult(
                success=True,
                output=result,
                execution_time_ms=execution_time_ms,
                metadata={
                    "file_info": file_info,
                    "processed_files": processed_files,
                    "operation": operation,
                },
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return SkillExecutionResult(
                success=False,
                error_message=f"执行文件处理失败: {str(e)}",
                execution_time_ms=execution_time_ms,
            )


# 示例技能3：网络请求技能
class NetworkRequestSkill(Skill):
    """网络请求技能 - 演示HTTP请求功能"""

    metadata = SkillMetadata(
        name="network_request",
        description="提供HTTP请求功能，支持GET、POST等方法和错误处理",
        version="1.0.0",
        author="Network Team",
        category=SkillCategory.NETWORK_COMMUNICATION,
        tags=["http", "request", "api", "network"],
        dependencies=["requests"],
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "请求URL"},
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE"],
                    "description": "HTTP方法",
                },
                "headers": {"type": "object", "description": "请求头"},
                "data": {"type": "object", "description": "请求数据（仅对POST/PUT）"},
                "timeout": {"type": "number", "description": "超时时间（秒）"},
            },
            "required": ["url", "method"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "status_code": {"type": "integer", "description": "HTTP状态码"},
                "response": {"description": "响应内容"},
                "response_time_ms": {
                    "type": "number",
                    "description": "响应时间（毫秒）",
                },
                "headers": {"type": "object", "description": "响应头"},
            },
        },
    )

    def on_initialize(self):
        """自定义初始化"""
        try:
            import requests

            self._has_dependencies = True
        except ImportError:
            self._has_dependencies = False
            logger.warning("网络请求技能依赖缺失：requests")

    def validate_input(self, **kwargs) -> List[str]:
        """验证输入参数"""
        errors = []

        if "url" not in kwargs:
            errors.append("缺少必需参数: url")
        if "method" not in kwargs:
            errors.append("缺少必需参数: method")

        if errors:
            return errors

        url = kwargs["url"]
        method = kwargs["method"]

        # 验证URL格式
        if not url.startswith(("http://", "https://")):
            errors.append("URL必须以 http:// 或 https:// 开头")

        # 验证方法
        valid_methods = ["GET", "POST", "PUT", "DELETE"]
        if method not in valid_methods:
            errors.append(f"method必须是以下之一: {', '.join(valid_methods)}")

        # 验证超时时间
        if "timeout" in kwargs and not isinstance(kwargs["timeout"], (int, float)):
            errors.append("timeout必须是数字")

        return errors

    def execute(self, **kwargs) -> SkillExecutionResult:
        """执行网络请求"""
        start_time = time.time()

        # 验证输入
        validation_errors = self.validate_input(**kwargs)
        if validation_errors:
            return SkillExecutionResult(
                success=False,
                error_message=f"输入验证失败: {', '.join(validation_errors)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        # 检查依赖
        if not self._has_dependencies:
            return SkillExecutionResult(
                success=False,
                error_message="缺少依赖: requests",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            import requests

            url = kwargs["url"]
            method = kwargs["method"]
            headers = kwargs.get("headers", {})
            data = kwargs.get("data")
            timeout = kwargs.get("timeout", 10)

            # 执行请求
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == "POST":
                response = requests.post(
                    url, headers=headers, json=data, timeout=timeout
                )
            elif method == "PUT":
                response = requests.put(
                    url, headers=headers, json=data, timeout=timeout
                )
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            execution_time_ms = (time.time() - start_time) * 1000

            # 解析响应
            try:
                response_data = response.json()
            except ValueError:
                response_data = response.text

            return SkillExecutionResult(
                success=True,
                output={
                    "status_code": response.status_code,
                    "response": response_data,
                    "response_time_ms": execution_time_ms,
                    "headers": dict(response.headers),
                },
                execution_time_ms=execution_time_ms,
                metadata={
                    "url": url,
                    "method": method,
                    "success": response.status_code < 400,
                },
            )

        except requests.exceptions.Timeout:
            execution_time_ms = (time.time() - start_time) * 1000
            return SkillExecutionResult(
                success=False,
                error_message=f"请求超时: {kwargs.get('timeout', 10)}秒",
                execution_time_ms=execution_time_ms,
            )
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            return SkillExecutionResult(
                success=False,
                error_message=f"执行网络请求失败: {str(e)}",
                execution_time_ms=execution_time_ms,
            )


# ============================================================================
# 第四部分：技能系统架构分析与最佳实践
# ============================================================================


class SkillSystemAnalyzer:
    """技能系统分析器 - 分析技能系统的架构和质量"""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def analyze_architecture(self) -> Dict[str, Any]:
        """分析技能系统架构"""
        analysis = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "skill_count": self.registry.get_skill_count(),
            "categories": {},
            "interface_compliance": {},
            "dependency_analysis": {},
            "performance_metrics": {},
            "recommendations": [],
        }

        # 分析技能分类分布
        skills_by_category = self.registry.get_skills_by_category()
        for category, skills in skills_by_category.items():
            analysis["categories"][category.name] = {
                "count": len(skills),
                "skills": skills,
            }

        # 分析接口合规性
        for skill_name in self.registry.list_skills():
            skill_class = self.registry.get_skill(skill_name, create_instance=False)
            if skill_class:
                compliance = self._analyze_interface_compliance(skill_class)
                analysis["interface_compliance"][skill_name] = compliance

        # 分析依赖关系
        for skill_name in self.registry.list_skills():
            metadata = self.registry.get_skill_metadata(skill_name)
            if metadata:
                analysis["dependency_analysis"][skill_name] = {
                    "dependencies": metadata.dependencies,
                    "dependency_count": len(metadata.dependencies),
                }

        # 生成建议
        analysis["recommendations"] = self._generate_recommendations(analysis)

        return analysis

    def _analyze_interface_compliance(self, skill_class: Type[Skill]) -> Dict[str, Any]:
        """分析技能接口合规性"""
        compliance = {
            "abstract_methods_implemented": True,
            "metadata_defined": True,
            "input_validation_implemented": True,
            "error_handling_present": True,
            "issues": [],
        }

        try:
            # 检查是否定义了metadata
            if not hasattr(skill_class, "metadata"):
                compliance["metadata_defined"] = False
                compliance["issues"].append("未定义metadata属性")

            # 检查抽象方法实现
            skill_instance = skill_class()
            methods_to_check = ["execute", "validate_input"]

            for method_name in methods_to_check:
                method = getattr(skill_class, method_name, None)
                if method and getattr(method, "__isabstractmethod__", False):
                    compliance["abstract_methods_implemented"] = False
                    compliance["issues"].append(f"抽象方法 {method_name} 未实现")

            # 检查输入验证
            validation_method = getattr(skill_class, "validate_input", None)
            if validation_method is None or validation_method == Skill.validate_input:
                compliance["input_validation_implemented"] = False
                compliance["issues"].append("未实现自定义输入验证")

            # 检查错误处理
            execute_method = getattr(skill_class, "execute", None)
            if execute_method:
                source = inspect.getsource(execute_method)
                error_keywords = ["try:", "except", "catch", "raise", "error"]
                if not any(keyword in source for keyword in error_keywords):
                    compliance["error_handling_present"] = False
                    compliance["issues"].append("execute方法中缺少错误处理")

        except Exception as e:
            compliance["issues"].append(f"分析过程中出错: {str(e)}")

        return compliance

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """根据分析结果生成建议"""
        recommendations = []

        # 检查分类分布
        categories = analysis.get("categories", {})
        if len(categories) < 3:
            recommendations.append("建议增加更多技能分类，以提高系统多样性")

        # 检查接口合规性
        interface_compliance = analysis.get("interface_compliance", {})
        non_compliant = [
            name
            for name, comp in interface_compliance.items()
            if not all(
                comp.get(key, True)
                for key in [
                    "abstract_methods_implemented",
                    "metadata_defined",
                    "input_validation_implemented",
                ]
            )
        ]

        if non_compliant:
            recommendations.append(
                f"以下技能需要改进接口实现: {', '.join(non_compliant)}"
            )

        # 检查依赖管理
        dependency_analysis = analysis.get("dependency_analysis", {})
        heavy_dependencies = [
            name
            for name, deps in dependency_analysis.items()
            if deps.get("dependency_count", 0) > 5
        ]

        if heavy_dependencies:
            recommendations.append(
                f"以下技能依赖过多，考虑重构: {', '.join(heavy_dependencies)}"
            )

        # 通用建议
        skill_count = analysis.get("skill_count", 0)
        if skill_count < 5:
            recommendations.append("技能数量较少，建议开发更多技能以提高系统能力")
        elif skill_count > 20:
            recommendations.append("技能数量较多，建议建立技能分类和优先级管理机制")

        return recommendations

    def generate_report(self, analysis: Optional[Dict[str, Any]] = None) -> str:
        """生成分析报告"""
        if analysis is None:
            analysis = self.analyze_architecture()

        report_lines = [
            "=" * 60,
            "技能系统架构分析报告",
            "=" * 60,
            f"生成时间: {analysis['timestamp']}",
            f"技能总数: {analysis['skill_count']}",
            "",
            "1. 分类分布:",
        ]

        for category, data in analysis["categories"].items():
            report_lines.append(f"   - {category}: {data['count']} 个技能")

        report_lines.extend(
            [
                "",
                "2. 接口合规性分析:",
            ]
        )

        compliant_count = 0
        for skill_name, compliance in analysis["interface_compliance"].items():
            is_compliant = all(
                compliance.get(key, True)
                for key in [
                    "abstract_methods_implemented",
                    "metadata_defined",
                    "input_validation_implemented",
                    "error_handling_present",
                ]
            )
            status = "✓ 合规" if is_compliant else "✗ 不合规"
            if is_compliant:
                compliant_count += 1
            report_lines.append(f"   - {skill_name}: {status}")

        compliance_rate = (
            compliant_count / max(len(analysis["interface_compliance"]), 1)
        ) * 100
        report_lines.append(f"   合规率: {compliance_rate:.1f}%")

        report_lines.extend(
            [
                "",
                "3. 建议与改进:",
            ]
        )

        for i, recommendation in enumerate(analysis["recommendations"], 1):
            report_lines.append(f"   {i}. {recommendation}")

        report_lines.extend(["", "=" * 60, "报告结束", "=" * 60])

        return "\n".join(report_lines)


class SkillSystemBestPractices:
    """技能系统最佳实践指南"""

    @staticmethod
    def get_design_principles() -> List[str]:
        """获取设计原则"""
        return [
            "1. 单一职责原则：每个技能应该只负责一个明确的功能",
            "2. 接口隔离原则：技能接口应该小而专一，避免臃肿",
            "3. 开闭原则：技能系统应该对扩展开放，对修改关闭",
            "4. 依赖倒置原则：技能应该依赖于抽象接口，而不是具体实现",
            "5. 里氏替换原则：子类技能应该能够替换父类技能而不影响系统",
        ]

    @staticmethod
    def get_implementation_guidelines() -> Dict[str, List[str]]:
        """获取实现指南"""
        return {
            "接口设计": [
                "定义清晰的Skill基类，包含必要的抽象方法",
                "为每个技能提供完整的元数据（metadata）",
                "实现输入验证（validate_input）方法",
                "统一执行结果格式（SkillExecutionResult）",
                "提供错误处理和异常捕获机制",
            ],
            "技能实现": [
                "保持技能功能单一和专注",
                "实现完整的输入验证和错误处理",
                "提供清晰的文档和示例",
                "考虑技能的性能和资源使用",
                "实现技能的生命周期管理",
            ],
            "注册表设计": [
                "提供技能注册和发现机制",
                "实现技能分类和标签系统",
                "支持动态技能加载和卸载",
                "提供技能查询和过滤功能",
                "实现技能依赖管理",
            ],
            "动态加载": [
                "使用Python的importlib实现动态模块加载",
                "实现技能目录扫描和发现",
                "支持技能热更新和版本管理",
                "提供技能验证和安全检查",
                "实现技能加载状态跟踪",
            ],
        }

    @staticmethod
    def get_common_anti_patterns() -> Dict[str, str]:
        """获取常见反模式"""
        return {
            "上帝技能": "一个技能尝试做太多事情，违反单一职责原则",
            "紧密耦合": "技能之间直接依赖，而不是通过接口交互",
            "缺乏验证": "技能没有输入验证，容易导致运行时错误",
            "硬编码配置": "技能配置硬编码在代码中，缺乏灵活性",
            "忽略错误": "技能没有适当的错误处理，导致系统不稳定",
            "重复实现": "多个技能实现相同功能，缺乏代码复用",
            "过度设计": "为不存在的需求设计复杂接口，增加维护成本",
        }

    @staticmethod
    def get_performance_optimization_tips() -> List[str]:
        """获取性能优化提示"""
        return [
            "延迟加载：只在需要时加载技能模块",
            "缓存机制：缓存常用技能的实例或结果",
            "连接池：对于需要外部连接的技能，使用连接池",
            "异步执行：对于IO密集型技能，考虑异步实现",
            "批量处理：支持批量操作，减少频繁调用开销",
            "内存管理：及时释放不再使用的技能实例",
            "监控指标：收集技能执行时间和资源使用指标",
        ]

    @staticmethod
    def get_security_considerations() -> List[str]:
        """获取安全考虑"""
        return [
            "输入验证：严格验证所有输入参数，防止注入攻击",
            "权限控制：为敏感技能实现权限检查和访问控制",
            "沙箱执行：对于不受信任的技能，考虑在沙箱中执行",
            "代码审查：对动态加载的技能进行代码审查",
            "依赖检查：检查技能依赖的安全性",
            "日志审计：记录所有技能执行的关键操作",
            "资源限制：限制技能可以使用的资源和时间",
        ]


# ============================================================================
# 主演示函数
# ============================================================================


def main_demo():
    """主演示函数 - 展示技能系统的完整功能"""
    print("=" * 60)
    print("技能系统集成演示")
    print("=" * 60)

    # 创建技能注册表
    print("\n1. 创建技能注册表...")
    registry = SkillRegistry()

    # 注册示例技能
    print("\n2. 注册示例技能...")
    skills_to_register = [DataAnalysisSkill, FileProcessingSkill, NetworkRequestSkill]

    for skill_class in skills_to_register:
        success = registry.register_skill(skill_class)
        status = "成功" if success else "失败"
        print(f"   - 注册 {skill_class.__name__}: {status}")

    # 显示注册的技能
    print(f"\n3. 已注册技能 ({registry.get_skill_count()} 个):")
    for skill_name in registry.list_skills():
        metadata = registry.get_skill_metadata(skill_name)
        if metadata:
            print(f"   - {metadata.name}: {metadata.description}")

    # 按分类显示技能
    print("\n4. 技能分类分布:")
    skills_by_category = registry.get_skills_by_category()
    for category, skill_names in skills_by_category.items():
        if skill_names:
            print(f"   - {category.name}: {len(skill_names)} 个技能")

    # 演示技能执行
    print("\n5. 演示技能执行...")

    # 执行数据分析技能
    print("\n   5.1 执行数据分析技能:")
    data_skill = registry.get_skill("data_analysis")
    if data_skill and data_skill.is_valid():
        result = data_skill.execute(
            data=[{"value": i} for i in range(10)], operation="mean"
        )
        print(f"      结果: {result.success}")
        print(f"      输出: {result.output}")
        print(f"      执行时间: {result.execution_time_ms:.2f}ms")
    else:
        print("      数据分析技能不可用")

    # 执行文件处理技能
    print("\n   5.2 执行文件处理技能:")
    file_skill = registry.get_skill("file_processing")
    if file_skill and file_skill.is_valid():
        # 创建测试文件
        test_file = "test_demo.txt"
        with open(test_file, "w") as f:
            f.write("这是一个测试文件")

        result = file_skill.execute(operation="read", file_path=test_file)
        print(f"      结果: {result.success}")
        print(f"      输出长度: {len(result.output) if result.output else 0} 字符")
        print(f"      执行时间: {result.execution_time_ms:.2f}ms")

        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
    else:
        print("      文件处理技能不可用")

    # 创建动态技能加载器
    print("\n6. 创建动态技能加载器...")
    loader = DynamicSkillLoader(registry)
    print(f"   加载器状态: {loader.get_loader_status()['state']}")

    # 演示技能发现
    print("\n7. 演示技能发现...")

    # 创建示例技能目录（用于演示）
    skills_dir = "demo_skills"
    os.makedirs(skills_dir, exist_ok=True)

    # 创建示例技能文件
    demo_skill_content = '''
"""
示例技能 - 用于动态加载演示
"""

from skill_system_demo import Skill, SkillMetadata, SkillExecutionResult
import time

class DemoDynamicSkill(Skill):
    """演示动态加载技能"""
    
    metadata = SkillMetadata(
        name="demo_dynamic",
        description="演示动态加载的技能",
        version="1.0.0",
        author="Demo Author",
        category="CUSTOM",
        tags=["demo", "dynamic"]
    )
    
    def validate_input(self, **kwargs):
        return []
    
    def execute(self, **kwargs):
        return SkillExecutionResult(
            success=True,
            output="动态加载的技能执行成功",
            execution_time_ms=10.0
        )
'''

    demo_skill_file = os.path.join(skills_dir, "demo_skill.py")
    with open(demo_skill_file, "w", encoding="utf-8") as f:
        f.write(demo_skill_content)

    # 发现技能
    print(f"   扫描目录: {skills_dir}")
    discovered_skills = loader.discover_skills(skills_dir)
    print(f"   发现 {len(discovered_skills)} 个技能")

    # 加载发现的技能
    if discovered_skills:
        print("\n8. 加载发现的技能...")
        load_results = loader.load_all_discovered_skills(discovered_skills)
        for skill_name, success in load_results.items():
            status = "成功" if success else "失败"
            print(f"   - 加载 {skill_name}: {status}")

    # 分析技能系统
    print("\n9. 分析技能系统架构...")
    analyzer = SkillSystemAnalyzer(registry)
    analysis = analyzer.analyze_architecture()

    print(f"   技能总数: {analysis['skill_count']}")
    print(f"   分类数量: {len(analysis['categories'])}")

    # 显示最佳实践
    print("\n10. 技能系统最佳实践:")
    practices = SkillSystemBestPractices()

    print("\n   设计原则:")
    for principle in practices.get_design_principles():
        print(f"     {principle}")

    # 生成报告
    print("\n11. 生成分析报告...")
    report = analyzer.generate_report(analysis)
    print(report[:500] + "..." if len(report) > 500 else report)

    # 保存报告到文件
    report_file = "skill_system_analysis_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n   报告已保存到: {report_file}")

    # 清理演示文件
    print("\n12. 清理演示文件...")
    if os.path.exists(demo_skill_file):
        os.remove(demo_skill_file)
    if os.path.exists(skills_dir):
        os.rmdir(skills_dir)

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    print("开始运行技能系统集成演示...")
    try:
        main_demo()
    except Exception as e:
        print(f"演示运行失败: {str(e)}")
        import traceback

        traceback.print_exc()
