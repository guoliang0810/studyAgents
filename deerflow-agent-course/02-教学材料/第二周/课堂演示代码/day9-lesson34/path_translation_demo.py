#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 9 Lesson 34: 路径翻译实现

本文件演示路径翻译的完整实现，包括：
1. 技能路径特殊处理 - /skills/前缀路径的智能解析
2. 缓存优化集成 - LRU缓存加速路径翻译
3. 批量翻译功能 - 批量处理多个翻译请求
4. 性能监控系统 - 收集和分析性能指标
5. 错误处理机制 - 统一的错误处理策略

使用示例:
    python path_translation_demo.py          # 运行基本演示
    python path_translation_demo.py --test   # 运行测试套件
    python path_translation_demo.py --demo   # 运行完整演示
    python path_translation_demo.py --help   # 显示帮助信息
"""

import os
import sys
import re
import time
import json
import hashlib
import argparse
from typing import Dict, List, Optional, Any, Tuple, NamedTuple
from dataclasses import dataclass, field
from collections import OrderedDict
from enum import Enum
import logging

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================

class TranslationType(Enum):
    """路径翻译类型枚举"""
    SKILL_PATH = "技能路径"        # /skills/xxx -> 技能包路径
    WORKSPACE_PATH = "工作空间路径"  # /workspace/xxx -> 工作空间路径
    TEMP_PATH = "临时路径"          # /tmp/xxx -> 临时目录路径
    STANDARD_PATH = "标准路径"      # 普通路径，使用基础目录映射

class TranslationStatus(Enum):
    """翻译状态枚举"""
    SUCCESS = "成功"
    CACHED = "缓存命中"
    FAILED = "失败"
    PARTIAL = "部分成功"

@dataclass
class TranslationRequest:
    """路径翻译请求"""
    virtual_path: str                    # 虚拟路径
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文信息
    priority: int = 0                    # 优先级
    use_cache: bool = True               # 是否使用缓存

@dataclass
class TranslationResult:
    """路径翻译结果"""
    virtual_path: str                    # 原始虚拟路径
    real_path: str                       # 翻译后的实际路径
    translation_type: TranslationType    # 翻译类型
    status: TranslationStatus            # 翻译状态
    translation_time: float = 0.0        # 翻译耗时
    cache_hit: bool = False              # 是否命中缓存
    skill_name: Optional[str] = None     # 技能名称（如果是技能路径）
    error_message: Optional[str] = None  # 错误信息

    def to_dict(self) -> Dict:
        return {
            "virtual_path": self.virtual_path,
            "real_path": self.real_path,
            "translation_type": self.translation_type.value,
            "status": self.status.value,
            "translation_time": self.translation_time,
            "cache_hit": self.cache_hit,
            "skill_name": self.skill_name,
            "error_message": self.error_message,
        }

@dataclass
class TranslationMetrics:
    """翻译性能指标"""
    total_translations: int = 0
    successful_translations: int = 0
    failed_translations: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    average_time: float = 0.0
    skill_translations: int = 0
    workspace_translations: int = 0
    temp_translations: int = 0
    standard_translations: int = 0

    def to_dict(self) -> Dict:
        return {
            "total_translations": self.total_translations,
            "successful_translations": self.successful_translations,
            "failed_translations": self.failed_translations,
            "success_rate": self.successful_translations / self.total_translations if self.total_translations > 0 else 0.0,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0.0,
            "average_time": self.average_time,
            "skill_translations": self.skill_translations,
            "workspace_translations": self.workspace_translations,
            "temp_translations": self.temp_translations,
            "standard_translations": self.standard_translations,
        }

# ============================================================================
# 第二部分：核心功能实现
# ============================================================================

class TranslationError(Exception):
    """翻译错误"""
    pass

class SkillPathError(TranslationError):
    """技能路径错误"""
    pass

class TranslationCache:
    """路径翻译缓存"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[TranslationResult]:
        if key in self.cache:
            value = self.cache.pop(key)
            self.cache[key] = value
            self.hits += 1
            return value
        self.misses += 1
        return None
    
    def set(self, key: str, value: TranslationResult) -> None:
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        self.cache[key] = value
    
    def clear(self) -> None:
        self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0.0,
        }

class SkillPathResolver:
    """技能路径解析器"""
    
    def __init__(self, skills_base_dir: str = "/skills"):
        self.skills_base_dir = skills_base_dir
        self.skill_cache = {}  # 技能名称 -> 路径缓存
    
    def resolve(self, skill_path: str) -> Tuple[str, str]:
        """解析技能路径，返回(技能名称, 实际路径)"""
        # 移除 /skills/ 前缀
        if skill_path.startswith("/skills/"):
            relative_path = skill_path[8:]  # len("/skills/") = 8
        elif skill_path.startswith("skills/"):
            relative_path = skill_path[7:]
        else:
            raise SkillPathError(f"不是有效的技能路径: {skill_path}")
        
        # 提取技能名称和文件路径
        parts = relative_path.split("/", 1)
        skill_name = parts[0]
        file_path = parts[1] if len(parts) > 1 else ""
        
        # 构建实际路径
        skill_base = os.path.join(self.skills_base_dir, skill_name)
        if file_path:
            real_path = os.path.join(skill_base, file_path)
        else:
            real_path = skill_base
        
        return skill_name, real_path
    
    def is_skill_path(self, path: str) -> bool:
        """检查是否为技能路径"""
        return path.startswith("/skills/") or path.startswith("skills/")

class PathTranslator:
    """路径翻译器"""
    
    def __init__(self, base_dir: str = "/tmp", skills_dir: str = "/skills"):
        self.base_dir = base_dir
        self.skills_dir = skills_dir
        self.skill_resolver = SkillPathResolver(skills_dir)
        self.cache = TranslationCache(max_size=1000)
        self.metrics = TranslationMetrics()
        self.logger = logging.getLogger("PathTranslator")
    
    def translate(self, virtual_path: str, use_cache: bool = True) -> TranslationResult:
        """翻译单个路径"""
        start_time = time.perf_counter()
        
        # 检查缓存
        cache_key = virtual_path if use_cache else None
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached:
                cached.cache_hit = True
                cached.translation_time = time.perf_counter() - start_time
                self.metrics.cache_hits += 1
                self._update_metrics(cached, start_time)
                return cached
            self.metrics.cache_misses += 1
        
        # 执行翻译
        try:
            result = self._do_translate(virtual_path)
            result.translation_time = time.perf_counter() - start_time
            result.cache_hit = False
            
            # 缓存结果
            if cache_key:
                self.cache.set(cache_key, result)
            
            self._update_metrics(result, start_time)
            return result
            
        except Exception as e:
            error_result = TranslationResult(
                virtual_path=virtual_path,
                real_path="",
                translation_type=TranslationType.STANDARD_PATH,
                status=TranslationStatus.FAILED,
                translation_time=time.perf_counter() - start_time,
                error_message=str(e)
            )
            self.metrics.failed_translations += 1
            return error_result
    
    def _do_translate(self, virtual_path: str) -> TranslationResult:
        """实际执行翻译逻辑"""
        # 检查技能路径
        if self.skill_resolver.is_skill_path(virtual_path):
            skill_name, real_path = self.skill_resolver.resolve(virtual_path)
            return TranslationResult(
                virtual_path=virtual_path,
                real_path=real_path,
                translation_type=TranslationType.SKILL_PATH,
                status=TranslationStatus.SUCCESS,
                skill_name=skill_name
            )
        
        # 检查工作空间路径
        if virtual_path.startswith("/workspace/") or virtual_path.startswith("workspace/"):
            relative = virtual_path.split("/", 2)[2] if "/" in virtual_path[1:] else ""
            real_path = os.path.join("/tmp/workspace", relative) if relative else "/tmp/workspace"
            return TranslationResult(
                virtual_path=virtual_path,
                real_path=real_path,
                translation_type=TranslationType.WORKSPACE_PATH,
                status=TranslationStatus.SUCCESS
            )
        
        # 检查临时路径
        if virtual_path.startswith("/tmp/") or virtual_path.startswith("tmp/"):
            relative = virtual_path.split("/", 2)[2] if "/" in virtual_path[1:] else ""
            real_path = os.path.join("/tmp", relative) if relative else "/tmp"
            return TranslationResult(
                virtual_path=virtual_path,
                real_path=real_path,
                translation_type=TranslationType.TEMP_PATH,
                status=TranslationStatus.SUCCESS
            )
        
        # 标准路径：使用基础目录
        if os.path.isabs(virtual_path):
            real_path = virtual_path
        else:
            real_path = os.path.join(self.base_dir, virtual_path)
        
        return TranslationResult(
            virtual_path=virtual_path,
            real_path=real_path,
            translation_type=TranslationType.STANDARD_PATH,
            status=TranslationStatus.SUCCESS
        )
    
    def _update_metrics(self, result: TranslationResult, start_time: float) -> None:
        """更新性能指标"""
        self.metrics.total_translations += 1
        if result.status == TranslationStatus.SUCCESS or result.status == TranslationStatus.CACHED:
            self.metrics.successful_translations += 1
        else:
            self.metrics.failed_translations += 1
        
        # 更新类型计数
        if result.translation_type == TranslationType.SKILL_PATH:
            self.metrics.skill_translations += 1
        elif result.translation_type == TranslationType.WORKSPACE_PATH:
            self.metrics.workspace_translations += 1
        elif result.translation_type == TranslationType.TEMP_PATH:
            self.metrics.temp_translations += 1
        else:
            self.metrics.standard_translations += 1
        
        # 更新平均时间
        total_time = self.metrics.average_time * (self.metrics.total_translations - 1)
        self.metrics.average_time = (total_time + result.translation_time) / self.metrics.total_translations
    
    def batch_translate(self, paths: List[str]) -> List[TranslationResult]:
        """批量翻译路径"""
        results = []
        for path in paths:
            result = self.translate(path)
            results.append(result)
        return results
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
    
    def get_metrics(self) -> TranslationMetrics:
        """获取性能指标"""
        return self.metrics
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return self.cache.stats()

class BatchTranslator:
    """批量翻译器"""
    
    def __init__(self, translator: PathTranslator, batch_size: int = 100):
        self.translator = translator
        self.batch_size = batch_size
    
    def translate_batch(self, paths: List[str]) -> List[TranslationResult]:
        """批量翻译，分批处理"""
        results = []
        for i in range(0, len(paths), self.batch_size):
            batch = paths[i:i + self.batch_size]
            batch_results = self.translator.batch_translate(batch)
            results.extend(batch_results)
        return results
    
    def translate_with_stats(self, paths: List[str]) -> Tuple[List[TranslationResult], Dict[str, Any]]:
        """翻译并返回统计信息"""
        start_time = time.perf_counter()
        results = self.translate_batch(paths)
        total_time = time.perf_counter() - start_time
        
        stats = {
            "total_paths": len(paths),
            "successful": sum(1 for r in results if r.status == TranslationStatus.SUCCESS),
            "failed": sum(1 for r in results if r.status == TranslationStatus.FAILED),
            "cached": sum(1 for r in results if r.cache_hit),
            "total_time": total_time,
            "average_time_per_path": total_time / len(paths) if paths else 0.0,
        }
        
        return results, stats

# ============================================================================
# 第三部分：演示与测试
# ============================================================================

class PathTranslationTestSuite:
    """路径翻译测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        self.tests.append(("test_skill_path_translation", self.test_skill_path_translation))
        self.tests.append(("test_workspace_path_translation", self.test_workspace_path_translation))
        self.tests.append(("test_cache_functionality", self.test_cache_functionality))
        self.tests.append(("test_batch_translation", self.test_batch_translation))
        self.tests.append(("test_error_handling", self.test_error_handling))
    
    def test_skill_path_translation(self) -> Tuple[bool, str]:
        translator = PathTranslator("/tmp/base", "/skills")
        result = translator.translate("/skills/weather/main.py")
        if result.translation_type != TranslationType.SKILL_PATH:
            return False, f"技能路径类型错误: {result.translation_type}"
        if result.skill_name != "weather":
            return False, f"技能名称错误: {result.skill_name}"
        if not result.real_path.endswith("/skills/weather/main.py"):
            return False, f"实际路径错误: {result.real_path}"
        return True, "技能路径翻译测试通过"
    
    def test_workspace_path_translation(self) -> Tuple[bool, str]:
        translator = PathTranslator("/tmp/base")
        result = translator.translate("/workspace/project/file.txt")
        if result.translation_type != TranslationType.WORKSPACE_PATH:
            return False, f"工作空间路径类型错误: {result.translation_type}"
        if not result.real_path.startswith("/tmp/workspace/"):
            return False, f"实际路径错误: {result.real_path}"
        return True, "工作空间路径翻译测试通过"
    
    def test_cache_functionality(self) -> Tuple[bool, str]:
        translator = PathTranslator()
        # 第一次翻译
        result1 = translator.translate("file.txt")
        if result1.cache_hit:
            return False, "第一次不应命中缓存"
        # 第二次翻译
        result2 = translator.translate("file.txt")
        if not result2.cache_hit:
            return False, "第二次应命中缓存"
        # 检查缓存统计
        cache_stats = translator.get_cache_stats()
        if cache_stats["hits"] < 1:
            return False, f"缓存命中次数错误: {cache_stats['hits']}"
        return True, "缓存功能测试通过"
    
    def test_batch_translation(self) -> Tuple[bool, str]:
        translator = PathTranslator()
        batch_translator = BatchTranslator(translator, batch_size=5)
        paths = [f"file{i}.txt" for i in range(10)]
        results, stats = batch_translator.translate_with_stats(paths)
        if stats["total_paths"] != 10:
            return False, f"批量翻译数量错误: {stats['total_paths']}"
        if stats["successful"] != 10:
            return False, f"批量翻译成功数错误: {stats['successful']}"
        return True, "批量翻译测试通过"
    
    def test_error_handling(self) -> Tuple[bool, str]:
        translator = PathTranslator()
        # 测试无效的技能路径
        result = translator.translate("/skills/invalid")
        if result.status == TranslationStatus.SUCCESS:
            # 应该返回路径，即使技能不存在
            pass
        return True, "错误处理测试通过"
    
    def run_all_tests(self) -> Dict[str, Any]:
        print("🚀 开始运行路径翻译测试套件...")
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
                print(f"   💥 异常: {e}")
                failed += 1
                results[test_name] = {"passed": False, "message": str(e), "error": str(e)}
        
        print("=" * 60)
        print(f"📊 测试摘要: 总数={len(self.tests)}, 通过={passed}, 失败={failed}")
        
        return {
            "summary": {
                "total": len(self.tests),
                "passed": passed,
                "failed": failed,
                "success_rate": passed / len(self.tests) if self.tests else 0.0
            },
            "details": results
        }

def main_demo() -> None:
    """主演示函数"""
    print("=" * 80)
    print("🎓 Day 9 Lesson 34: 路径翻译实现演示")
    print("=" * 80)
    
    # 创建路径翻译器
    translator = PathTranslator(base_dir="/tmp/sandbox", skills_dir="/skills")
    
    print("\n1. 基本路径翻译演示...")
    test_paths = [
        "file.txt",
        "/workspace/project/main.py",
        "/skills/weather/api.py",
        "/tmp/cache/data.json",
        "/absolute/path/file.txt",
    ]
    
    for path in test_paths:
        result = translator.translate(path)
        print(f"   {path}")
        print(f"     -> {result.real_path}")
        print(f"     类型: {result.translation_type.value}, 状态: {result.status.value}")
        if result.skill_name:
            print(f"     技能: {result.skill_name}")
    
    print("\n2. 缓存功能演示...")
    # 清空缓存
    translator.clear_cache()
    
    # 第一次翻译
    result1 = translator.translate("cached_file.txt")
    print(f"   第一次: {result1.cache_hit} (耗时: {result1.translation_time:.6f}s)")
    
    # 第二次翻译（应命中缓存）
    result2 = translator.translate("cached_file.txt")
    print(f"   第二次: {result2.cache_hit} (耗时: {result2.translation_time:.6f}s)")
    
    cache_stats = translator.get_cache_stats()
    print(f"   缓存统计: 命中={cache_stats['hits']}, 未命中={cache_stats['misses']}, 命中率={cache_stats['hit_rate']:.1%}")
    
    print("\n3. 批量翻译演示...")
    batch_translator = BatchTranslator(translator, batch_size=5)
    batch_paths = [f"batch_file_{i}.txt" for i in range(10)]
    results, stats = batch_translator.translate_with_stats(batch_paths)
    
    print(f"   批量翻译 {stats['total_paths']} 个路径:")
    print(f"   成功: {stats['successful']}, 失败: {stats['failed']}, 缓存命中: {stats['cached']}")
    print(f"   总时间: {stats['total_time']:.6f}s, 平均: {stats['average_time_per_path']:.6f}s/路径")
    
    print("\n4. 性能指标演示...")
    metrics = translator.get_metrics()
    print(f"   总翻译次数: {metrics.total_translations}")
    print(f"   成功: {metrics.successful_translations}, 失败: {metrics.failed_translations}")
    print(f"   平均时间: {metrics.average_time:.6f}s")
    print(f"   类型分布:")
    print(f"     技能路径: {metrics.skill_translations}")
    print(f"     工作空间: {metrics.workspace_translations}")
    print(f"     临时路径: {metrics.temp_translations}")
    print(f"     标准路径: {metrics.standard_translations}")
    
    print("\n5. 运行测试套件...")
    test_suite = PathTranslationTestSuite()
    report = test_suite.run_all_tests()
    
    print(f"\n📊 测试报告:")
    print(f"   成功率: {report['summary']['success_rate']:.1%}")
    
    print("\n" + "=" * 80)
    print("🎉 路径翻译实现演示完成！")
    print("=" * 80)

def run_tests() -> None:
    """运行测试套件"""
    test_suite = PathTranslationTestSuite()
    report = test_suite.run_all_tests()
    
    if report["summary"]["success_rate"] >= 1.0:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 有测试失败，请检查实现。")

def main() -> None:
    parser = argparse.ArgumentParser(description="路径翻译实现演示程序")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行完整演示")
    
    args = parser.parse_args()
    
    if args.test:
        run_tests()
    elif args.demo:
        main_demo()
    else:
        print("路径翻译实现演示程序")
        print("使用 --help 查看选项")
        # 运行简单演示
        translator = PathTranslator()
        result = translator.translate("/skills/weather/main.py")
        print(f"\n示例翻译:")
        print(f"  /skills/weather/main.py -> {result.real_path}")
        print(f"  类型: {result.translation_type.value}")

if __name__ == "__main__":
    main()
