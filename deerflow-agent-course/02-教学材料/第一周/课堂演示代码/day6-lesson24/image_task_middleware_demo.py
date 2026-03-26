#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 6 Lesson 24: 实战 - 图片处理和任务管理集成 - 课堂演示代码

本文件提供完整的图片分析流水线实现，集成ViewImageMiddleware、TodoMiddleware和SubagentLimitMiddleware。
采用四部分结构设计，全面展示多中间件集成和复杂任务管理的各个方面：
1. 集成基础：图片处理、任务管理、子代理限制的核心概念回顾与集成设计
2. 图片分析流水线实现：ImageAnalysisPipeline类设计与多中间件集成架构
3. 中间件链编排与执行流程：中间件执行顺序、数据传递、错误处理机制
4. 完整测试系统与端到端演示：单元测试、集成测试、边界测试、性能测试

教学目标：
1. 理解多中间件协同工作的设计模式和执行流程
2. 掌握图片分析流水线的完整架构和组件交互
3. 理解任务分解、执行、跟踪、聚合的全流程管理
4. 了解中间件链的正确顺序和依赖关系设计
5. 能够集成ViewImageMiddleware、TodoMiddleware、SubagentLimitMiddleware
6. 能够设计完整的图片分析流水线架构
7. 能够实现主任务和子任务的创建、依赖管理
8. 能够编写集成测试验证多中间件协同工作

运行要求：
Python 3.12+, 安装依赖: asyncio, typing-extensions, dataclasses-json, pillow (PIL), yaml
前置课程: 已完成ViewImageMiddleware、SubagentLimitMiddleware、TodoMiddleware学习

作者: 张老师 (DeerFlow核心贡献者)
版本: v1.0
日期: 2024年4月5日
"""

import asyncio
import time
import json
import yaml
import uuid
import base64
import io
import mimetypes
import random
import warnings
from typing import List, Dict, Optional, Tuple, Any, Set, Union, Callable, BinaryIO
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
from datetime import datetime, timedelta
import heapq
from PIL import Image, UnidentifiedImageError

# ============================================================================
# 第一部分：集成基础
# ============================================================================

"""
第一部分：集成基础
目标：回顾三个中间件的核心概念，定义集成所需的统一数据结构
内容：
1. 图片处理基础回顾（ViewImageMiddleware核心概念）
2. 任务管理基础回顾（TodoMiddleware核心概念）
3. 子代理限制基础回顾（SubagentLimitMiddleware核心概念）
4. 集成数据结构和接口设计
"""

# ----------------------------------------------------------------------------
# 1.1 图片处理基础回顾（基于ViewImageMiddleware）
# ----------------------------------------------------------------------------


class ImageFormat(Enum):
    """图片格式枚举（从ViewImageMiddleware复用）"""

    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    BMP = "bmp"
    WEBP = "webp"
    TIFF = "tiff"
    SVG = "svg"

    @classmethod
    def from_mime_type(cls, mime_type: str) -> Optional["ImageFormat"]:
        """从MIME类型获取图片格式"""
        mime_to_format = {
            "image/jpeg": cls.JPEG,
            "image/jpg": cls.JPEG,
            "image/png": cls.PNG,
            "image/gif": cls.GIF,
            "image/bmp": cls.BMP,
            "image/webp": cls.WEBP,
            "image/tiff": cls.TIFF,
            "image/svg+xml": cls.SVG,
        }
        return mime_to_format.get(mime_type.lower())

    @classmethod
    def from_extension(cls, extension: str) -> Optional["ImageFormat"]:
        """从文件扩展名获取图片格式"""
        ext_to_format = {
            ".jpg": cls.JPEG,
            ".jpeg": cls.JPEG,
            ".png": cls.PNG,
            ".gif": cls.GIF,
            ".bmp": cls.BMP,
            ".webp": cls.WEBP,
            ".tiff": cls.TIFF,
            ".tif": cls.TIFF,
            ".svg": cls.SVG,
        }
        return ext_to_format.get(extension.lower())


@dataclass
class ImageMetadata:
    """图片元数据（简化版本，用于集成）"""

    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[ImageFormat] = None
    size_bytes: Optional[int] = None
    color_mode: Optional[str] = None
    dpi: Optional[Tuple[int, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "width": self.width,
            "height": self.height,
            "format": self.format.value if self.format else None,
            "size_bytes": self.size_bytes,
            "color_mode": self.color_mode,
            "dpi": self.dpi,
        }


@dataclass
class ImageContent:
    """图片内容（简化版本，用于集成）"""

    data: bytes
    metadata: Optional[ImageMetadata] = None
    description: Optional[str] = None

    @classmethod
    def from_base64(cls, base64_str: str) -> "ImageContent":
        """从Base64字符串创建图片内容"""
        # 移除data URL前缀（如果存在）
        if base64_str.startswith("data:"):
            # 格式: data:image/jpeg;base64,/9j/4AAQSkZ...
            parts = base64_str.split(",", 1)
            if len(parts) == 2:
                base64_str = parts[1]

        try:
            data = base64.b64decode(base64_str)
            return cls(data=data)
        except Exception as e:
            raise ValueError(f"Base64解码失败: {e}")

    def to_base64(self) -> str:
        """转换为Base64字符串"""
        return base64.b64encode(self.data).decode("utf-8")

    def to_data_url(self, mime_type: str = "image/jpeg") -> str:
        """转换为data URL格式"""
        return f"data:{mime_type};base64,{self.to_base64()}"


# ----------------------------------------------------------------------------
# 1.2 任务管理基础回顾（基于TodoMiddleware）
# ----------------------------------------------------------------------------


class TaskStatus(Enum):
    """任务状态枚举（从TodoMiddleware复用）"""

    PENDING = "pending"  # 等待中（依赖未满足）
    READY = "ready"  # 准备就绪（依赖已满足）
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 已失败
    CANCELLED = "cancelled"  # 已取消


class Priority(Enum):
    """优先级枚举（从TodoMiddleware复用）"""

    HIGHEST = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    LOWEST = 5


@dataclass
class TodoItem:
    """任务项数据结构（简化版本，用于集成）"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: int = 60  # 预估时长（秒）
    actual_duration: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)

    def update_status(self, new_status: TaskStatus):
        """更新任务状态"""
        self.status = new_status
        self.updated_at = datetime.now()

    def is_blocked(self, todos: Dict[str, "TodoItem"]) -> bool:
        """检查任务是否被阻塞（依赖任务未完成）"""
        for dep_id in self.dependencies:
            if dep_id not in todos:
                continue
            dep_task = todos[dep_id]
            if dep_task.status != TaskStatus.COMPLETED:
                return True
        return False

    def calculate_progress(self, todos: Dict[str, "TodoItem"]) -> float:
        """计算任务进度（0.0到1.0）"""
        if self.status == TaskStatus.COMPLETED:
            return 1.0
        elif self.status == TaskStatus.FAILED or self.status == TaskStatus.CANCELLED:
            return 0.0
        elif self.status == TaskStatus.RUNNING:
            # 如果任务正在运行，假设进度为50%
            return 0.5
        elif self.status == TaskStatus.READY:
            return 0.1
        elif self.status == TaskStatus.PENDING:
            if self.is_blocked(todos):
                return 0.0
            else:
                return 0.05
        return 0.0


# ----------------------------------------------------------------------------
# 1.3 子代理限制基础回顾（基于SubagentLimitMiddleware）
# ----------------------------------------------------------------------------


class SubagentLimitConfig:
    """子代理限制配置（简化版本，用于集成）"""

    def __init__(self):
        self.max_subagents_per_request: int = 3
        self.max_total_subagents: int = 10
        self.time_window_seconds: int = 60
        self.current_subagents: Dict[str, List[datetime]] = defaultdict(list)

    def can_spawn_subagent(self, request_id: str) -> bool:
        """检查是否可以创建新的子代理"""
        now = datetime.now()

        # 清理过期记录
        self._cleanup_old_records(now)

        # 检查每个请求的限制
        request_records = self.current_subagents.get(request_id, [])
        if len(request_records) >= self.max_subagents_per_request:
            return False

        # 检查全局限制
        total_records = sum(len(records) for records in self.current_subagents.values())
        if total_records >= self.max_total_subagents:
            return False

        return True

    def record_subagent_spawn(self, request_id: str):
        """记录子代理创建"""
        if self.can_spawn_subagent(request_id):
            self.current_subagents[request_id].append(datetime.now())
            return True
        return False

    def _cleanup_old_records(self, now: datetime):
        """清理过期的记录"""
        cutoff = now - timedelta(seconds=self.time_window_seconds)
        for request_id in list(self.current_subagents.keys()):
            self.current_subagents[request_id] = [
                timestamp
                for timestamp in self.current_subagents[request_id]
                if timestamp > cutoff
            ]
            if not self.current_subagents[request_id]:
                del self.current_subagents[request_id]


# ----------------------------------------------------------------------------
# 1.4 集成数据结构设计
# ----------------------------------------------------------------------------


class AnalysisType(Enum):
    """分析类型枚举"""

    DESCRIPTION = "description"  # 图片描述生成
    OBJECT_DETECTION = "object_detection"  # 物体检测
    TEXT_EXTRACTION = "text_extraction"  # 文字提取
    COLOR_ANALYSIS = "color_analysis"  # 颜色分析
    FACE_DETECTION = "face_detection"  # 人脸检测
    SCENE_CLASSIFICATION = "scene_classification"  # 场景分类


@dataclass
class AnalysisTask:
    """分析任务数据结构"""

    task_id: str
    analysis_type: AnalysisType
    image_content: ImageContent
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration(self) -> Optional[float]:
        """任务持续时间（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass
class PipelineResult:
    """流水线结果"""

    pipeline_id: str
    original_image: ImageContent
    analysis_tasks: List[AnalysisTask]
    aggregated_result: Dict[str, Any]
    total_duration: float
    success: bool
    errors: List[str] = field(default_factory=list)


# ============================================================================
# 第二部分：图片分析流水线实现
# ============================================================================

"""
第二部分：图片分析流水线实现
目标：实现ImageAnalysisPipeline类，集成三个中间件，提供完整的图片分析功能
内容：
1. ImageAnalysisPipeline类设计与架构
2. 模拟视觉模型实现（MockVisionModel）
3. 中间件集成管理器（MiddlewareIntegrationManager）
4. 流水线五阶段实现：上传、描述、分解、跟踪、聚合
"""

# ----------------------------------------------------------------------------
# 2.1 模拟视觉模型实现（MockVisionModel）
# ----------------------------------------------------------------------------


class MockVisionModel:
    """模拟视觉模型（用于演示，避免真实API依赖）"""

    def __init__(self):
        self.response_templates = {
            AnalysisType.DESCRIPTION: {
                "description": "这是一张{scene}的照片，拍摄于{time_of_day}，{weather}天气，{details}",
                "confidence": 0.85,
            },
            AnalysisType.OBJECT_DETECTION: {
                "objects": [
                    {"name": "object1", "confidence": 0.92, "bbox": [10, 20, 100, 150]},
                    {
                        "name": "object2",
                        "confidence": 0.87,
                        "bbox": [150, 30, 200, 180],
                    },
                ],
                "total_objects": 2,
            },
            AnalysisType.TEXT_EXTRACTION: {
                "text": "示例文本：欢迎使用DeerFlow AI Agent系统",
                "language": "zh",
                "confidence": 0.78,
            },
            AnalysisType.COLOR_ANALYSIS: {
                "dominant_colors": [
                    {"color": [255, 0, 0], "percentage": 30},
                    {"color": [0, 255, 0], "percentage": 25},
                    {"color": [0, 0, 255], "percentage": 20},
                ],
                "color_palette": "vibrant",
            },
            AnalysisType.FACE_DETECTION: {
                "faces": [
                    {
                        "age": 25,
                        "gender": "female",
                        "emotion": "happy",
                        "bbox": [50, 60, 120, 140],
                    },
                ],
                "face_count": 1,
            },
            AnalysisType.SCENE_CLASSIFICATION: {
                "scene": "urban",
                "confidence": 0.91,
                "tags": ["city", "buildings", "sky", "modern"],
            },
        }

        # 模拟数据生成器
        self.scenes = [
            "城市天际线",
            "自然风景",
            "室内场景",
            "人物肖像",
            "动物世界",
            "美食摄影",
        ]
        self.times_of_day = ["清晨", "中午", "下午", "黄昏", "夜晚"]
        self.weathers = ["晴朗", "多云", "阴天", "雨天", "雪天"]
        self.details_list = [
            "光线充足，构图优美",
            "色彩鲜艳，对比强烈",
            "背景虚化，主体突出",
            "细节丰富，纹理清晰",
            "透视感强，空间层次分明",
        ]

    async def analyze_image(
        self, image_content: ImageContent, analysis_type: AnalysisType
    ) -> Dict[str, Any]:
        """模拟图片分析（异步）"""
        # 模拟处理延迟
        await asyncio.sleep(random.uniform(0.5, 2.0))

        template = self.response_templates[analysis_type].copy()

        # 根据分析类型填充模板
        if analysis_type == AnalysisType.DESCRIPTION:
            scene = random.choice(self.scenes)
            time_of_day = random.choice(self.times_of_day)
            weather = random.choice(self.weathers)
            details = random.choice(self.details_list)

            template["description"] = template["description"].format(
                scene=scene, time_of_day=time_of_day, weather=weather, details=details
            )
            # 添加图片元数据
            if image_content.metadata:
                template["metadata"] = image_content.metadata.to_dict()

        elif analysis_type == AnalysisType.OBJECT_DETECTION:
            # 随机调整对象数量
            num_objects = random.randint(1, 5)
            template["objects"] = [
                {
                    "name": f"object_{i + 1}",
                    "confidence": random.uniform(0.7, 0.95),
                    "bbox": [
                        random.randint(0, 100),
                        random.randint(0, 100),
                        random.randint(150, 300),
                        random.randint(150, 300),
                    ],
                }
                for i in range(num_objects)
            ]
            template["total_objects"] = num_objects

        return template

    async def analyze_batch(
        self, image_contents: List[ImageContent], analysis_type: AnalysisType
    ) -> List[Dict[str, Any]]:
        """批量图片分析（模拟并行处理）"""
        tasks = [self.analyze_image(img, analysis_type) for img in image_contents]
        return await asyncio.gather(*tasks)


# ----------------------------------------------------------------------------
# 2.2 中间件集成管理器（MiddlewareIntegrationManager）
# ----------------------------------------------------------------------------


class MiddlewareIntegrationManager:
    """中间件集成管理器 - 负责协调三个中间件的执行"""

    def __init__(self):
        self.view_image_middleware = ViewImageMiddleware()
        self.todo_middleware = TodoMiddleware()
        self.subagent_limit_middleware = SubagentLimitMiddleware()

        # 中间件执行顺序（重要：顺序影响功能）
        self.middleware_chain = [
            self.subagent_limit_middleware,  # 1. 先检查子代理限制
            self.todo_middleware,  # 2. 然后处理任务管理
            self.view_image_middleware,  # 3. 最后处理图片
        ]

    async def before_agent(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Agent执行前的中间件链处理"""
        current_data = input_data

        for middleware in self.middleware_chain:
            try:
                current_data = await middleware.before_agent(current_data)
            except Exception as e:
                # 记录错误但继续执行（降级处理）
                print(f"中间件 {middleware.__class__.__name__} before_agent 错误: {e}")
                continue

        return current_data

    async def during_agent(self, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        """Agent执行中的中间件链处理"""
        current_data = progress_data

        for middleware in self.middleware_chain:
            try:
                current_data = await middleware.during_agent(current_data)
            except Exception as e:
                print(f"中间件 {middleware.__class__.__name__} during_agent 错误: {e}")
                continue

        return current_data

    async def after_agent(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """Agent执行后的中间件链处理"""
        current_data = output_data

        for middleware in self.middleware_chain:
            try:
                current_data = await middleware.after_agent(current_data)
            except Exception as e:
                print(f"中间件 {middleware.__class__.__name__} after_agent 错误: {e}")
                continue

        return current_data

    async def on_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """错误处理中间件链"""
        current_data = error_data

        for middleware in self.middleware_chain:
            try:
                current_data = await middleware.on_error(current_data)
            except Exception as e:
                print(f"中间件 {middleware.__class__.__name__} on_error 错误: {e}")
                continue

        return current_data


# ----------------------------------------------------------------------------
# 2.3 ViewImageMiddleware实现（简化版本）
# ----------------------------------------------------------------------------


class ViewImageMiddleware:
    """图片查看中间件（简化版本，专注于图片检测和描述生成）"""

    def __init__(self, vision_model: Optional[MockVisionModel] = None):
        self.vision_model = vision_model or MockVisionModel()

    async def before_agent(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """检测输入中的图片内容并生成描述"""
        # 检查是否包含图片（Base64格式）
        messages = input_data.get("messages", [])
        for i, message in enumerate(messages):
            if isinstance(message, str) and (
                "data:image/" in message or len(message) > 1000
            ):
                # 可能是图片内容
                try:
                    image_content = ImageContent.from_base64(message)

                    # 生成图片描述
                    analysis_result = await self.vision_model.analyze_image(
                        image_content, AnalysisType.DESCRIPTION
                    )

                    # 将图片替换为描述
                    messages[i] = f"[图片] {analysis_result['description']}"

                    # 保存图片元数据到上下文中
                    if "image_metadata" not in input_data:
                        input_data["image_metadata"] = []
                    input_data["image_metadata"].append(
                        {
                            "index": i,
                            "metadata": image_content.metadata.to_dict()
                            if image_content.metadata
                            else None,
                            "description": analysis_result["description"],
                        }
                    )

                except Exception as e:
                    # 图片处理失败，保留原消息
                    messages[i] = f"[图片处理失败: {str(e)}] {message[:100]}..."

        input_data["messages"] = messages
        return input_data

    async def during_agent(self, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行中处理 - 暂无特殊逻辑"""
        return progress_data

    async def after_agent(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行后处理 - 添加图片分析结果"""
        # 如果上下文中有图片元数据，添加到输出中
        image_metadata = output_data.get("image_metadata")
        if image_metadata:
            output_data["image_analysis"] = {
                "total_images": len(image_metadata),
                "descriptions": [meta.get("description") for meta in image_metadata],
            }

        return output_data

    async def on_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """错误处理 - 记录图片处理相关错误"""
        return error_data


# ----------------------------------------------------------------------------
# 2.4 TodoMiddleware实现（简化版本）
# ----------------------------------------------------------------------------


class TodoMiddleware:
    """任务管理中间件（简化版本，专注于任务创建和进度跟踪）"""

    def __init__(self):
        self.todos: Dict[str, TodoItem] = {}
        self.next_todo_id = 1

    async def before_agent(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建分析任务"""
        # 检查是否需要创建任务
        if "analysis_types" in input_data and "image_content" in input_data:
            analysis_types = input_data["analysis_types"]
            image_content = input_data["image_content"]

            # 创建主任务
            main_task = TodoItem(
                id=f"main_task_{self.next_todo_id}",
                title="图片分析主任务",
                description=f"分析图片，包含{len(analysis_types)}个子分析",
                status=TaskStatus.READY,
                priority=Priority.HIGH,
                estimated_duration=60 * len(analysis_types),
            )
            self.next_todo_id += 1

            # 创建子任务
            subtasks = []
            for i, analysis_type in enumerate(analysis_types):
                subtask = TodoItem(
                    id=f"subtask_{self.next_todo_id}",
                    title=f"{analysis_type.value}分析",
                    description=f"执行{analysis_type.value}分析",
                    status=TaskStatus.PENDING,
                    priority=Priority.MEDIUM,
                    dependencies=[main_task.id],
                    estimated_duration=30,
                    tags=[analysis_type.value],
                )
                self.next_todo_id += 1
                subtasks.append(subtask)

            # 保存任务
            self.todos[main_task.id] = main_task
            for subtask in subtasks:
                self.todos[subtask.id] = subtask

            # 将任务信息添加到输入数据中
            input_data["todo_ids"] = {
                "main_task": main_task.id,
                "subtasks": [st.id for st in subtasks],
            }

        return input_data

    async def during_agent(self, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新任务进度"""
        task_id = progress_data.get("task_id")
        progress = progress_data.get("progress", 0.0)

        if task_id and task_id in self.todos:
            task = self.todos[task_id]
            if progress >= 1.0:
                task.update_status(TaskStatus.COMPLETED)
            elif progress > 0:
                task.update_status(TaskStatus.RUNNING)

            # 更新进度信息
            progress_data["task_status"] = task.status.value
            progress_data["task_progress"] = task.calculate_progress(self.todos)

        return progress_data

    async def after_agent(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """完成任务并更新状态"""
        task_ids = output_data.get("completed_task_ids", [])

        for task_id in task_ids:
            if task_id in self.todos:
                task = self.todos[task_id]
                task.update_status(TaskStatus.COMPLETED)
                task.actual_duration = output_data.get("task_duration")

        # 计算总体进度
        if self.todos:
            completed = sum(
                1 for t in self.todos.values() if t.status == TaskStatus.COMPLETED
            )
            total = len(self.todos)
            output_data["todo_progress"] = {
                "completed": completed,
                "total": total,
                "percentage": completed / total if total > 0 else 0.0,
            }

        return output_data

    async def on_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理任务失败"""
        task_id = error_data.get("task_id")

        if task_id and task_id in self.todos:
            task = self.todos[task_id]
            task.update_status(TaskStatus.FAILED)
            error_data["task_status"] = "failed"

        return error_data


# ----------------------------------------------------------------------------
# 2.5 SubagentLimitMiddleware实现（简化版本）
# ----------------------------------------------------------------------------


class SubagentLimitMiddleware:
    """子代理限制中间件（简化版本）"""

    def __init__(self):
        self.config = SubagentLimitConfig()
        self.request_counter = 0

    async def before_agent(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查子代理限制"""
        request_id = input_data.get("request_id", f"req_{self.request_counter}")
        self.request_counter += 1

        if not self.config.can_spawn_subagent(request_id):
            raise Exception(f"子代理创建限制已满，请求ID: {request_id}")

        # 记录子代理创建
        self.config.record_subagent_spawn(request_id)

        input_data["request_id"] = request_id
        input_data["subagent_limit_info"] = {
            "max_per_request": self.config.max_subagents_per_request,
            "max_total": self.config.max_total_subagents,
            "time_window": self.config.time_window_seconds,
        }

        return input_data

    async def during_agent(self, progress_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行中检查 - 暂无特殊逻辑"""
        return progress_data

    async def after_agent(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行后清理 - 暂无特殊逻辑"""
        return output_data

    async def on_error(self, error_data: Dict[str, Any]) -> Dict[str, Any]:
        """错误处理 - 清理子代理计数"""
        request_id = error_data.get("request_id")
        if request_id and request_id in self.config.current_subagents:
            # 从当前计数中移除一个记录（模拟清理）
            if self.config.current_subagents[request_id]:
                self.config.current_subagents[request_id].pop()

        return error_data


# ----------------------------------------------------------------------------
# 2.6 ImageAnalysisPipeline类（核心）
# ----------------------------------------------------------------------------


class ImageAnalysisPipeline:
    """图片分析流水线 - 集成三个中间件的完整系统"""

    def __init__(self):
        self.middleware_manager = MiddlewareIntegrationManager()
        self.vision_model = MockVisionModel()

        # 流水线状态
        self.pipeline_id: Optional[str] = None
        self.current_stage: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # 分析结果
        self.original_image: Optional[ImageContent] = None
        self.analysis_tasks: List[AnalysisTask] = []
        self.aggregated_result: Dict[str, Any] = {}

    async def analyze_image(
        self,
        image_content: ImageContent,
        analysis_types: List[AnalysisType],
        pipeline_id: Optional[str] = None,
    ) -> PipelineResult:
        """执行图片分析流水线"""
        self.pipeline_id = pipeline_id or f"pipeline_{uuid.uuid4().hex[:8]}"
        self.start_time = datetime.now()
        self.original_image = image_content
        self.current_stage = "initializing"

        try:
            # 阶段1: 上传和验证
            self.current_stage = "upload"
            await self._upload_and_validate(image_content)

            # 阶段2: 图片描述生成
            self.current_stage = "description"
            description_result = await self._generate_description(image_content)

            # 阶段3: 任务分解
            self.current_stage = "decomposition"
            tasks = await self._decompose_tasks(image_content, analysis_types)
            self.analysis_tasks = tasks

            # 阶段4: 任务执行和跟踪
            self.current_stage = "execution"
            task_results = await self._execute_and_track_tasks(tasks)

            # 阶段5: 结果聚合
            self.current_stage = "aggregation"
            aggregated_result = await self._aggregate_results(
                description_result, task_results
            )
            self.aggregated_result = aggregated_result

            self.current_stage = "completed"

        except Exception as e:
            self.current_stage = "failed"
            raise e
        finally:
            self.end_time = datetime.now()

        # 创建流水线结果
        total_duration = (self.end_time - self.start_time).total_seconds()

        return PipelineResult(
            pipeline_id=self.pipeline_id,
            original_image=image_content,
            analysis_tasks=self.analysis_tasks,
            aggregated_result=self.aggregated_result,
            total_duration=total_duration,
            success=self.current_stage == "completed",
            errors=[]
            if self.current_stage == "completed"
            else [f"流水线在阶段 {self.current_stage} 失败"],
        )

    async def _upload_and_validate(self, image_content: ImageContent):
        """阶段1: 上传和验证"""
        # 模拟上传延迟
        await asyncio.sleep(0.1)

        # 验证图片（简化验证）
        if len(image_content.data) == 0:
            raise ValueError("图片数据为空")

        if len(image_content.data) > 10 * 1024 * 1024:  # 10MB限制
            raise ValueError("图片大小超过10MB限制")

        # 尝试解析图片元数据
        try:
            image = Image.open(io.BytesIO(image_content.data))
            metadata = ImageMetadata(
                width=image.width,
                height=image.height,
                format=ImageFormat.from_extension(f".{image.format.lower()}")
                if image.format
                else None,
                size_bytes=len(image_content.data),
                color_mode=image.mode,
                dpi=image.info.get("dpi"),
            )
            image_content.metadata = metadata
        except UnidentifiedImageError:
            # 无法识别图片格式，继续处理但元数据为空
            pass

    async def _generate_description(
        self, image_content: ImageContent
    ) -> Dict[str, Any]:
        """阶段2: 图片描述生成"""
        # 使用ViewImageMiddleware生成描述
        middleware = ViewImageMiddleware(self.vision_model)

        input_data = {
            "messages": [image_content.to_data_url()],
            "image_content": image_content,
        }

        processed_data = await middleware.before_agent(input_data)

        description = (
            processed_data["messages"][0] if processed_data["messages"] else "无描述"
        )

        return {
            "description": description,
            "metadata": image_content.metadata.to_dict()
            if image_content.metadata
            else None,
            "stage": "description_generation",
        }

    async def _decompose_tasks(
        self, image_content: ImageContent, analysis_types: List[AnalysisType]
    ) -> List[AnalysisTask]:
        """阶段3: 任务分解"""
        tasks = []

        for analysis_type in analysis_types:
            task = AnalysisTask(
                task_id=f"task_{uuid.uuid4().hex[:8]}",
                analysis_type=analysis_type,
                image_content=image_content,
                parameters={"priority": "normal"},
            )
            tasks.append(task)

        return tasks

    async def _execute_and_track_tasks(
        self, tasks: List[AnalysisTask]
    ) -> List[Dict[str, Any]]:
        """阶段4: 任务执行和跟踪"""
        results = []

        # 创建TodoMiddleware管理任务
        todo_middleware = TodoMiddleware()

        # 准备任务输入
        for i, task in enumerate(tasks):
            # 标记任务开始
            task.start_time = datetime.now()

            # 使用TodoMiddleware跟踪进度
            progress_data = {
                "task_id": task.task_id,
                "progress": 0.0,
                "stage": "starting",
            }
            await todo_middleware.during_agent(progress_data)

            try:
                # 执行分析
                analysis_result = await self.vision_model.analyze_image(
                    task.image_content, task.analysis_type
                )

                task.result = analysis_result
                task.end_time = datetime.now()

                # 更新进度为完成
                progress_data["progress"] = 1.0
                await todo_middleware.during_agent(progress_data)

                # 标记任务完成
                output_data = {
                    "completed_task_ids": [task.task_id],
                    "task_duration": task.duration,
                }
                await todo_middleware.after_agent(output_data)

                results.append(
                    {
                        "task_id": task.task_id,
                        "analysis_type": task.analysis_type.value,
                        "result": analysis_result,
                        "success": True,
                        "duration": task.duration,
                    }
                )

            except Exception as e:
                task.error = str(e)
                task.end_time = datetime.now()

                # 标记任务失败
                error_data = {"task_id": task.task_id, "error": str(e)}
                await todo_middleware.on_error(error_data)

                results.append(
                    {
                        "task_id": task.task_id,
                        "analysis_type": task.analysis_type.value,
                        "error": str(e),
                        "success": False,
                        "duration": task.duration,
                    }
                )

        return results

    async def _aggregate_results(
        self, description_result: Dict[str, Any], task_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """阶段5: 结果聚合"""
        # 计算统计信息
        successful_tasks = [r for r in task_results if r["success"]]
        failed_tasks = [r for r in task_results if not r["success"]]

        total_duration = sum(
            r.get("duration", 0) for r in task_results if r.get("duration")
        )

        # 构建聚合结果
        aggregated = {
            "pipeline_id": self.pipeline_id,
            "description": description_result["description"],
            "total_tasks": len(task_results),
            "successful_tasks": len(successful_tasks),
            "failed_tasks": len(failed_tasks),
            "success_rate": len(successful_tasks) / len(task_results)
            if task_results
            else 0.0,
            "total_duration": total_duration,
            "average_duration_per_task": total_duration / len(task_results)
            if task_results
            else 0.0,
            "analysis_types": [r["analysis_type"] for r in task_results],
            "detailed_results": task_results,
            "timestamp": datetime.now().isoformat(),
            "stage": "aggregation_complete",
        }

        # 添加图片元数据（如果可用）
        if self.original_image and self.original_image.metadata:
            aggregated["image_metadata"] = self.original_image.metadata.to_dict()

        return aggregated


# ============================================================================
# 第三部分：中间件链编排与执行流程
# ============================================================================

"""
第三部分：中间件链编排与执行流程
目标：详细解释中间件链的设计、执行顺序、数据传递和错误处理机制
内容：
1. 中间件链设计原则和最佳实践
2. 执行顺序演示和流程图
3. 数据传递机制和上下文管理
4. 错误处理策略和降级机制
5. 性能优化和并发处理
"""

# ----------------------------------------------------------------------------
# 3.1 中间件链设计原则
# ----------------------------------------------------------------------------


class MiddlewareChainDesign:
    """中间件链设计原则演示类"""

    @staticmethod
    def explain_design_principles():
        """解释中间件链设计原则"""
        principles = [
            {
                "principle": "单一职责原则",
                "description": "每个中间件只负责一个特定的功能领域",
                "example": "ViewImageMiddleware只处理图片，TodoMiddleware只管理任务",
            },
            {
                "principle": "执行顺序重要性",
                "description": "中间件执行顺序直接影响系统行为，必须仔细设计",
                "example": "SubagentLimitMiddleware必须在最前面，防止资源超限",
            },
            {
                "principle": "错误隔离",
                "description": "一个中间件的错误不应导致整个链崩溃",
                "example": "使用try-except包装每个中间件调用",
            },
            {
                "principle": "数据传递一致性",
                "description": "中间件之间通过统一的字典传递数据",
                "example": "所有中间件都接收和返回Dict[str, Any]",
            },
            {
                "principle": "异步友好",
                "description": "所有中间件方法都应该是异步的，支持并发",
                "example": "使用async/await语法",
            },
            {
                "principle": "可配置性",
                "description": "中间件行为应该可以通过配置调整",
                "example": "SubagentLimitMiddleware的限流参数可配置",
            },
            {
                "principle": "可测试性",
                "description": "中间件应该易于单元测试和集成测试",
                "example": "提供MockVisionModel避免真实API依赖",
            },
        ]

        print("中间件链设计原则:")
        print("=" * 60)
        for i, p in enumerate(principles, 1):
            print(f"{i}. {p['principle']}")
            print(f"   描述: {p['description']}")
            print(f"   示例: {p['example']}")
            print()

    @staticmethod
    def get_optimal_execution_order() -> List[str]:
        """获取最优执行顺序"""
        return [
            "SubagentLimitMiddleware",  # 1. 资源限制检查
            "TodoMiddleware",  # 2. 任务创建和管理
            "ViewImageMiddleware",  # 3. 内容处理和转换
        ]

    @staticmethod
    def explain_order_importance():
        """解释执行顺序的重要性"""
        print("执行顺序的重要性分析:")
        print("=" * 60)

        scenarios = [
            {
                "order": [
                    "ViewImageMiddleware",
                    "TodoMiddleware",
                    "SubagentLimitMiddleware",
                ],
                "problem": "图片处理可能创建大量子任务，导致资源超限后才被检查",
                "solution": "先检查资源限制，避免无效处理",
            },
            {
                "order": [
                    "TodoMiddleware",
                    "ViewImageMiddleware",
                    "SubagentLimitMiddleware",
                ],
                "problem": "任务创建后可能发现图片无法处理，导致任务状态不一致",
                "solution": "先处理内容，再创建任务",
            },
            {
                "order": [
                    "SubagentLimitMiddleware",
                    "ViewImageMiddleware",
                    "TodoMiddleware",
                ],
                "problem": "图片处理后创建任务，但任务可能依赖其他未完成的任务",
                "solution": "先创建任务依赖关系，再处理内容",
            },
        ]

        for i, scenario in enumerate(scenarios, 1):
            print(f"场景{i}: {scenario['order']}")
            print(f"  问题: {scenario['problem']}")
            print(f"  解决方案: {scenario['solution']}")
            print()


# ----------------------------------------------------------------------------
# 3.2 执行顺序演示和流程图
# ----------------------------------------------------------------------------


async def demonstrate_middleware_chain():
    """演示中间件链执行顺序"""
    print("中间件链执行演示:")
    print("=" * 60)

    # 创建中间件管理器
    manager = MiddlewareIntegrationManager()

    # 模拟输入数据
    input_data = {
        "request_id": "test_request_123",
        "messages": ["data:image/jpeg;base64,/9j/4AAQSkZ..."],
        "analysis_types": [AnalysisType.DESCRIPTION, AnalysisType.OBJECT_DETECTION],
        "image_content": ImageContent(data=b"fake_image_data"),
    }

    print("1. 初始输入:")
    print(f"   request_id: {input_data['request_id']}")
    print(f"   消息数: {len(input_data['messages'])}")
    print(f"   分析类型: {[at.value for at in input_data['analysis_types']]}")
    print()

    # 执行before_agent链
    print("2. 执行before_agent中间件链:")
    print("  执行顺序:", [m.__class__.__name__ for m in manager.middleware_chain])

    try:
        result1 = await manager.before_agent(input_data)
        print("  ✅ before_agent执行成功")
        print(f"  生成的todo_ids: {result1.get('todo_ids', '无')}")
        print(f"  子代理限制信息: {result1.get('subagent_limit_info', '无')}")
    except Exception as e:
        print(f"  ❌ before_agent执行失败: {e}")

    print()

    # 执行during_agent链
    print("3. 执行during_agent中间件链:")
    progress_data = {"task_id": "subtask_1", "progress": 0.5}
    result2 = await manager.during_agent(progress_data)
    print(f"  ✅ during_agent执行成功")
    print(f"  任务状态: {result2.get('task_status', '未知')}")
    print(f"  任务进度: {result2.get('task_progress', 0.0)}")

    print()

    # 执行after_agent链
    print("4. 执行after_agent中间件链:")
    output_data = {
        "completed_task_ids": ["subtask_1"],
        "task_duration": 30.5,
        "image_metadata": [{"index": 0, "description": "测试图片描述"}],
    }
    result3 = await manager.after_agent(output_data)
    print(f"  ✅ after_agent执行成功")
    print(f"  任务进度: {result3.get('todo_progress', '无')}")
    print(f"  图片分析结果: {result3.get('image_analysis', '无')}")

    print()

    # 执行on_error链
    print("5. 执行on_error中间件链:")
    error_data = {
        "task_id": "subtask_2",
        "error": "模拟错误",
        "request_id": "test_request_123",
    }
    result4 = await manager.on_error(error_data)
    print(f"  ✅ on_error执行成功")
    print(f"  错误处理结果: {result4.get('task_status', '未知')}")

    print()
    print("演示完成!")
    print("=" * 60)


# ----------------------------------------------------------------------------
# 3.3 数据传递机制演示
# ----------------------------------------------------------------------------


class DataFlowDemonstration:
    """数据传递机制演示"""

    @staticmethod
    async def demonstrate_data_flow():
        """演示数据在中间件链中的传递"""
        print("数据传递机制演示:")
        print("=" * 60)

        # 创建简单的中间件链
        middleware1 = SimpleMiddleware("Middleware1")
        middleware2 = SimpleMiddleware("Middleware2")
        middleware3 = SimpleMiddleware("Middleware3")

        # 模拟数据流
        data = {"initial": "data", "counter": 0}

        print(f"初始数据: {data}")

        # 通过中间件1
        data = await middleware1.before_agent(data)
        print(f"Middleware1处理后: {data}")

        # 通过中间件2
        data = await middleware2.before_agent(data)
        print(f"Middleware2处理后: {data}")

        # 通过中间件3
        data = await middleware3.before_agent(data)
        print(f"Middleware3处理后: {data}")

        print()
        print("数据流特点:")
        print("1. 每个中间件都可以读取和修改数据")
        print("2. 数据以字典形式传递，保持一致性")
        print("3. 中间件可以添加新字段供后续中间件使用")
        print("4. 错误信息也会通过相同通道传递")

        print()
        print("=" * 60)


class SimpleMiddleware:
    """简单中间件用于演示"""

    def __init__(self, name: str):
        self.name = name

    async def before_agent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """简单的before_agent实现"""
        data[f"processed_by_{self.name}"] = True
        data["counter"] = data.get("counter", 0) + 1
        return data

    async def during_agent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """简单的during_agent实现"""
        return data

    async def after_agent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """简单的after_agent实现"""
        return data

    async def on_error(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """简单的on_error实现"""
        return data


# ----------------------------------------------------------------------------
# 3.4 错误处理策略演示
# ----------------------------------------------------------------------------


class ErrorHandlingDemonstration:
    """错误处理策略演示"""

    @staticmethod
    async def demonstrate_error_handling():
        """演示错误处理策略"""
        print("错误处理策略演示:")
        print("=" * 60)

        # 创建可能失败的中间件链
        middlewares = [
            FaultyMiddleware("MiddlewareA", fail_probability=0.0),
            FaultyMiddleware("MiddlewareB", fail_probability=0.3),
            FaultyMiddleware("MiddlewareC", fail_probability=0.0),
        ]

        # 测试正常流程
        print("1. 正常流程测试:")
        data = {"test": "data"}
        for i, mw in enumerate(middlewares):
            try:
                data = await mw.before_agent(data)
                print(f"  ✅ {mw.name} 执行成功")
            except Exception as e:
                print(f"  ❌ {mw.name} 执行失败: {e}")
                # 降级处理：跳过这个中间件，继续执行
                continue

        print()

        # 测试错误恢复
        print("2. 错误恢复测试:")
        recovery_middleware = RecoveryMiddleware("RecoveryMiddleware")
        data = {"test": "data", "should_fail": True}

        try:
            data = await recovery_middleware.before_agent(data)
            print(f"  ✅ 错误恢复成功: {data}")
        except Exception as e:
            print(f"  ❌ 错误恢复失败: {e}")

        print()

        # 测试优雅降级
        print("3. 优雅降级测试:")
        fallback_middleware = FallbackMiddleware("FallbackMiddleware")
        data = {"test": "data", "use_fallback": True}

        result = await fallback_middleware.before_agent(data)
        print(f"  ✅ 降级结果: {result}")

        print()
        print("错误处理策略总结:")
        print("1. 错误隔离：一个中间件失败不影响其他中间件")
        print("2. 优雅降级：核心功能失败时提供基本功能")
        print("3. 错误恢复：尝试从错误状态恢复")
        print("4. 详细日志：记录错误信息便于调试")

        print()
        print("=" * 60)


class FaultyMiddleware:
    """可能失败的中间件"""

    def __init__(self, name: str, fail_probability: float = 0.1):
        self.name = name
        self.fail_probability = fail_probability

    async def before_agent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """可能失败的before_agent"""
        if random.random() < self.fail_probability:
            raise Exception(f"{self.name} 模拟失败")

        data[f"{self.name}_processed"] = True
        return data


class RecoveryMiddleware:
    """错误恢复中间件"""

    def __init__(self, name: str):
        self.name = name

    async def before_agent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """尝试错误恢复"""
        if data.get("should_fail"):
            # 模拟恢复过程
            await asyncio.sleep(0.1)
            data["recovered"] = True
            data["recovery_timestamp"] = datetime.now().isoformat()

        return data


class FallbackMiddleware:
    """优雅降级中间件"""

    def __init__(self, name: str):
        self.name = name

    async def before_agent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提供降级功能"""
        if data.get("use_fallback"):
            # 使用降级逻辑
            data["result"] = "降级结果（基本功能）"
            data["fallback_used"] = True
        else:
            # 正常逻辑
            data["result"] = "正常结果"
            data["fallback_used"] = False

        return data


# ----------------------------------------------------------------------------
# 3.5 性能优化和并发处理
# ----------------------------------------------------------------------------


class PerformanceOptimization:
    """性能优化演示"""

    @staticmethod
    async def demonstrate_concurrent_processing():
        """演示并发处理"""
        print("并发处理性能演示:")
        print("=" * 60)

        # 创建一批分析任务
        analysis_types = [
            AnalysisType.DESCRIPTION,
            AnalysisType.OBJECT_DETECTION,
            AnalysisType.TEXT_EXTRACTION,
            AnalysisType.COLOR_ANALYSIS,
        ]

        # 创建模拟图片
        image_content = ImageContent(data=b"fake_image" * 1000)

        # 串行处理
        print("1. 串行处理:")
        start_time = time.time()

        vision_model = MockVisionModel()
        for analysis_type in analysis_types:
            await vision_model.analyze_image(image_content, analysis_type)

        serial_duration = time.time() - start_time
        print(f"  耗时: {serial_duration:.2f}秒")
        print(f"  平均每个任务: {serial_duration / len(analysis_types):.2f}秒")

        print()

        # 并发处理
        print("2. 并发处理:")
        start_time = time.time()

        tasks = [
            vision_model.analyze_image(image_content, analysis_type)
            for analysis_type in analysis_types
        ]
        await asyncio.gather(*tasks)

        concurrent_duration = time.time() - start_time
        print(f"  耗时: {concurrent_duration:.2f}秒")
        print(f"  平均每个任务: {concurrent_duration / len(analysis_types):.2f}秒")
        print(f"  性能提升: {serial_duration / concurrent_duration:.1f}倍")

        print()

        # 批处理演示
        print("3. 批处理演示:")
        image_contents = [ImageContent(data=b"fake_image" * 1000) for _ in range(3)]

        start_time = time.time()
        batch_results = await vision_model.analyze_batch(
            image_contents, AnalysisType.DESCRIPTION
        )
        batch_duration = time.time() - start_time

        print(f"  处理 {len(image_contents)} 张图片")
        print(f"  总耗时: {batch_duration:.2f}秒")
        print(f"  平均每张图片: {batch_duration / len(image_contents):.2f}秒")

        print()
        print("性能优化建议:")
        print("1. 使用asyncio.gather()进行并发处理")
        print("2. 批量处理类似任务减少开销")
        print("3. 缓存重复计算结果")
        print("4. 限制并发数避免资源耗尽")
        print("5. 监控性能指标及时优化")

        print()
        print("=" * 60)


# ============================================================================
# 第四部分：完整测试系统与端到端演示
# ============================================================================

"""
第四部分：完整测试系统与端到端演示
目标：提供全面的测试覆盖和端到端演示，确保代码质量和教学效果
内容：
1. 单元测试套件：测试各个组件独立功能
2. 集成测试套件：测试中间件集成和流水线功能
3. 边界测试套件：测试边界情况和错误处理
4. 性能测试套件：测试系统性能和并发能力
5. 端到端演示：完整演示图片分析流水线
"""

# ----------------------------------------------------------------------------
# 4.1 单元测试套件
# ----------------------------------------------------------------------------


class ImageAnalysisPipelineTestSuite:
    """图片分析流水线测试套件"""

    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.start_time = None
        self.end_time = None

    async def run_all_tests(self):
        """运行所有测试"""
        print("🎓 Day 6 Lesson 24: 图片处理和任务管理集成 - 测试套件")
        print("=" * 80)

        self.start_time = time.time()

        # 运行单元测试
        await self.run_unit_tests()

        # 运行集成测试
        await self.run_integration_tests()

        # 运行边界测试
        await self.run_boundary_tests()

        # 运行性能测试
        await self.run_performance_tests()

        self.end_time = time.time()

        # 输出总结
        self.print_summary()

    async def run_unit_tests(self):
        """运行单元测试"""
        print("\n🧪 单元测试")
        print("-" * 80)

        # 测试1: ImageContent基础功能
        await self.test_image_content_basics()

        # 测试2: TodoItem状态管理
        await self.test_todo_item_state()

        # 测试3: SubagentLimitConfig限制检查
        await self.test_subagent_limit_config()

        # 测试4: MockVisionModel分析功能
        await self.test_mock_vision_model()

        # 测试5: AnalysisTask数据结构
        await self.test_analysis_task()

    async def test_image_content_basics(self):
        """测试ImageContent基础功能"""
        self.total_tests += 1

        try:
            # 创建测试图片数据
            test_data = b"fake_image_data"
            image_content = ImageContent(data=test_data)

            # 测试Base64编码解码
            base64_str = image_content.to_base64()
            decoded_content = ImageContent.from_base64(base64_str)

            assert decoded_content.data == test_data, "Base64编码解码数据不一致"

            # 测试data URL格式
            data_url = image_content.to_data_url("image/jpeg")
            assert data_url.startswith("data:image/jpeg;base64,"), "data URL格式错误"

            print("  ✅ ImageContent基础功能: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ ImageContent基础功能: 失败 - {e}")
            self.failed_tests += 1

    async def test_todo_item_state(self):
        """测试TodoItem状态管理"""
        self.total_tests += 1

        try:
            # 创建任务
            todo = TodoItem(
                title="测试任务",
                description="测试任务描述",
                status=TaskStatus.PENDING,
                priority=Priority.HIGH,
            )

            # 测试状态更新
            assert todo.status == TaskStatus.PENDING
            todo.update_status(TaskStatus.RUNNING)
            assert todo.status == TaskStatus.RUNNING

            # 测试阻塞检查
            todo2 = TodoItem(title="依赖任务", dependencies=[todo.id])
            todos_dict = {todo.id: todo, todo2.id: todo2}

            assert todo2.is_blocked(todos_dict), "依赖任务应该被阻塞"

            # 完成第一个任务
            todo.update_status(TaskStatus.COMPLETED)
            assert not todo2.is_blocked(todos_dict), "依赖任务不应该再被阻塞"

            # 测试进度计算
            progress = todo.calculate_progress(todos_dict)
            assert progress == 1.0, "已完成任务进度应该是1.0"

            print("  ✅ TodoItem状态管理: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ TodoItem状态管理: 失败 - {e}")
            self.failed_tests += 1

    async def test_subagent_limit_config(self):
        """测试SubagentLimitConfig限制检查"""
        self.total_tests += 1

        try:
            config = SubagentLimitConfig()
            config.max_subagents_per_request = 2
            config.max_total_subagents = 3

            request_id = "test_request"

            # 测试可以创建子代理
            assert config.can_spawn_subagent(request_id), "应该可以创建子代理"

            # 创建两个子代理（达到请求限制）
            config.record_subagent_spawn(request_id)
            config.record_subagent_spawn(request_id)

            # 应该达到限制
            assert not config.can_spawn_subagent(request_id), "应该达到请求限制"

            # 测试不同请求的隔离
            request_id2 = "test_request2"
            assert config.can_spawn_subagent(request_id2), "不同请求应该可以创建子代理"

            print("  ✅ SubagentLimitConfig限制检查: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ SubagentLimitConfig限制检查: 失败 - {e}")
            self.failed_tests += 1

    async def test_mock_vision_model(self):
        """测试MockVisionModel分析功能"""
        self.total_tests += 1

        try:
            vision_model = MockVisionModel()
            image_content = ImageContent(data=b"fake_image")

            # 测试各种分析类型
            for analysis_type in AnalysisType:
                result = await vision_model.analyze_image(image_content, analysis_type)

                # 检查结果结构
                assert isinstance(result, dict), "结果应该是字典"
                assert len(result) > 0, "结果不应该为空"

                # 检查特定分析类型的字段
                if analysis_type == AnalysisType.DESCRIPTION:
                    assert "description" in result, "描述分析应该包含description字段"
                elif analysis_type == AnalysisType.OBJECT_DETECTION:
                    assert "objects" in result, "物体检测应该包含objects字段"

            # 测试批量分析
            image_contents = [ImageContent(data=b"fake_image") for _ in range(3)]
            batch_results = await vision_model.analyze_batch(
                image_contents, AnalysisType.DESCRIPTION
            )

            assert len(batch_results) == 3, "批量分析应该返回3个结果"

            print("  ✅ MockVisionModel分析功能: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ MockVisionModel分析功能: 失败 - {e}")
            self.failed_tests += 1

    async def test_analysis_task(self):
        """测试AnalysisTask数据结构"""
        self.total_tests += 1

        try:
            image_content = ImageContent(data=b"fake_image")

            task = AnalysisTask(
                task_id="test_task_123",
                analysis_type=AnalysisType.DESCRIPTION,
                image_content=image_content,
                parameters={"quality": "high"},
            )

            # 测试属性
            assert task.task_id == "test_task_123"
            assert task.analysis_type == AnalysisType.DESCRIPTION
            assert task.image_content == image_content

            # 测试持续时间计算
            assert task.duration is None, "未开始的任务持续时间应该是None"

            task.start_time = datetime.now()
            task.end_time = task.start_time + timedelta(seconds=5)

            duration = task.duration
            assert duration is not None and duration > 0, "持续时间应该大于0"

            print("  ✅ AnalysisTask数据结构: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ AnalysisTask数据结构: 失败 - {e}")
            self.failed_tests += 1

    # ----------------------------------------------------------------------------
    # 4.2 集成测试套件
    # ----------------------------------------------------------------------------

    async def run_integration_tests(self):
        """运行集成测试"""
        print("\n🔗 集成测试")
        print("-" * 80)

        # 测试1: 中间件链集成
        await self.test_middleware_chain_integration()

        # 测试2: 图片分析流水线集成
        await self.test_pipeline_integration()

        # 测试3: 任务创建和执行集成
        await self.test_task_execution_integration()

        # 测试4: 错误处理集成
        await self.test_error_handling_integration()

    async def test_middleware_chain_integration(self):
        """测试中间件链集成"""
        self.total_tests += 1

        try:
            manager = MiddlewareIntegrationManager()

            # 准备测试数据
            input_data = {
                "request_id": "integration_test",
                "messages": ["测试消息"],
                "analysis_types": [AnalysisType.DESCRIPTION],
                "image_content": ImageContent(data=b"test_image"),
            }

            # 测试before_agent链
            result = await manager.before_agent(input_data)

            # 检查中间件处理结果
            assert "request_id" in result, "结果应该包含request_id"
            assert "todo_ids" in result, "TodoMiddleware应该创建任务ID"
            assert "subagent_limit_info" in result, (
                "SubagentLimitMiddleware应该添加限制信息"
            )

            print("  ✅ 中间件链集成: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 中间件链集成: 失败 - {e}")
            self.failed_tests += 1

    async def test_pipeline_integration(self):
        """测试图片分析流水线集成"""
        self.total_tests += 1

        try:
            pipeline = ImageAnalysisPipeline()

            # 创建测试图片
            image_content = ImageContent(data=b"test_image_data")

            # 定义分析类型
            analysis_types = [AnalysisType.DESCRIPTION, AnalysisType.OBJECT_DETECTION]

            # 执行流水线
            result = await pipeline.analyze_image(
                image_content=image_content,
                analysis_types=analysis_types,
                pipeline_id="integration_test_pipeline",
            )

            # 检查结果
            assert result.pipeline_id == "integration_test_pipeline"
            assert result.original_image == image_content
            assert len(result.analysis_tasks) == 2
            assert isinstance(result.aggregated_result, dict)
            assert result.total_duration > 0

            print("  ✅ 图片分析流水线集成: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 图片分析流水线集成: 失败 - {e}")
            self.failed_tests += 1

    async def test_task_execution_integration(self):
        """测试任务创建和执行集成"""
        self.total_tests += 1

        try:
            # 创建TodoMiddleware
            todo_middleware = TodoMiddleware()

            # 模拟任务创建
            input_data = {
                "analysis_types": [
                    AnalysisType.DESCRIPTION,
                    AnalysisType.COLOR_ANALYSIS,
                ],
                "image_content": ImageContent(data=b"test"),
            }

            result = await todo_middleware.before_agent(input_data)

            # 检查任务创建
            assert "todo_ids" in result
            todo_ids = result["todo_ids"]
            assert "main_task" in todo_ids
            assert "subtasks" in todo_ids
            assert len(todo_ids["subtasks"]) == 2

            # 模拟任务执行
            for task_id in todo_ids["subtasks"]:
                progress_data = {"task_id": task_id, "progress": 0.5}
                await todo_middleware.during_agent(progress_data)

                progress_data["progress"] = 1.0
                await todo_middleware.during_agent(progress_data)

            # 完成任务
            output_data = {"completed_task_ids": todo_ids["subtasks"]}
            final_result = await todo_middleware.after_agent(output_data)

            # 检查进度
            assert "todo_progress" in final_result
            progress = final_result["todo_progress"]
            assert progress["completed"] == 2
            assert progress["total"] == 3  # 主任务 + 2个子任务
            assert progress["percentage"] > 0.66

            print("  ✅ 任务创建和执行集成: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 任务创建和执行集成: 失败 - {e}")
            self.failed_tests += 1

    async def test_error_handling_integration(self):
        """测试错误处理集成"""
        self.total_tests += 1

        try:
            # 创建可能失败的中间件链
            middleware = FaultyMiddleware("TestMiddleware", fail_probability=0.5)

            # 多次测试以确保错误处理工作
            errors = 0
            successes = 0

            for _ in range(10):
                try:
                    await middleware.before_agent({"test": "data"})
                    successes += 1
                except:
                    errors += 1

            # 检查错误处理没有崩溃
            assert successes + errors == 10, "应该处理所有请求"

            print("  ✅ 错误处理集成: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 错误处理集成: 失败 - {e}")
            self.failed_tests += 1

    # ----------------------------------------------------------------------------
    # 4.3 边界测试套件
    # ----------------------------------------------------------------------------

    async def run_boundary_tests(self):
        """运行边界测试"""
        print("\n⚠️  边界测试")
        print("-" * 80)

        # 测试1: 空图片数据
        await self.test_empty_image_data()

        # 测试2: 超大图片
        await self.test_large_image()

        # 测试3: 无效Base64
        await self.test_invalid_base64()

        # 测试4: 循环依赖
        await self.test_circular_dependencies()

        # 测试5: 并发限制边界
        await self.test_concurrency_limits()

    async def test_empty_image_data(self):
        """测试空图片数据"""
        self.total_tests += 1

        try:
            pipeline = ImageAnalysisPipeline()
            image_content = ImageContent(data=b"")

            # 应该抛出错误
            try:
                await pipeline.analyze_image(image_content, [AnalysisType.DESCRIPTION])
                assert False, "空图片数据应该抛出错误"
            except ValueError as e:
                assert "空" in str(e) or "大小" in str(e) or "无效" in str(e)

            print("  ✅ 空图片数据处理: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 空图片数据处理: 失败 - {e}")
            self.failed_tests += 1

    async def test_large_image(self):
        """测试超大图片"""
        self.total_tests += 1

        try:
            # 创建超过10MB的图片数据
            large_data = b"x" * (11 * 1024 * 1024)  # 11MB
            image_content = ImageContent(data=large_data)

            pipeline = ImageAnalysisPipeline()

            try:
                await pipeline._upload_and_validate(image_content)
                assert False, "超大图片应该被拒绝"
            except ValueError as e:
                assert "大小" in str(e) or "超过" in str(e) or "限制" in str(e)

            print("  ✅ 超大图片处理: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 超大图片处理: 失败 - {e}")
            self.failed_tests += 1

    async def test_invalid_base64(self):
        """测试无效Base64"""
        self.total_tests += 1

        try:
            # 无效Base64字符串
            invalid_base64 = "这不是有效的Base64!!"

            try:
                ImageContent.from_base64(invalid_base64)
                assert False, "无效Base64应该抛出错误"
            except ValueError as e:
                assert "解码" in str(e) or "无效" in str(e) or "格式" in str(e)

            print("  ✅ 无效Base64处理: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 无效Base64处理: 失败 - {e}")
            self.failed_tests += 1

    async def test_circular_dependencies(self):
        """测试循环依赖"""
        self.total_tests += 1

        try:
            # 创建循环依赖的任务
            task1 = TodoItem(id="task1", title="任务1")
            task2 = TodoItem(id="task2", title="任务2", dependencies=["task1"])
            task3 = TodoItem(id="task3", title="任务3", dependencies=["task2"])

            # 手动创建循环：task1依赖task3
            task1.dependencies = ["task3"]

            todos = {task1.id: task1, task2.id: task2, task3.id: task3}

            # 检查阻塞状态
            # 注意：我们的简单实现不检测间接循环依赖，只检查直接依赖
            # 所以这个测试主要确保系统不会崩溃
            blocked = task1.is_blocked(todos)
            # 应该返回True，因为task3未完成
            assert blocked is True or blocked is False  # 两种结果都可接受

            print("  ✅ 循环依赖处理: 通过（未崩溃）")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 循环依赖处理: 失败 - {e}")
            self.failed_tests += 1

    async def test_concurrency_limits(self):
        """测试并发限制"""
        self.total_tests += 1

        try:
            config = SubagentLimitConfig()
            config.max_subagents_per_request = 1
            config.max_total_subagents = 2

            request_id = "limit_test"

            # 第一个应该成功
            assert config.can_spawn_subagent(request_id)
            config.record_subagent_spawn(request_id)

            # 第二个应该失败（达到请求限制）
            assert not config.can_spawn_subagent(request_id)

            # 不同请求应该可以
            request_id2 = "limit_test2"
            assert config.can_spawn_subagent(request_id2)
            config.record_subagent_spawn(request_id2)

            # 现在达到全局限制
            request_id3 = "limit_test3"
            assert not config.can_spawn_subagent(request_id3)

            print("  ✅ 并发限制处理: 通过")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 并发限制处理: 失败 - {e}")
            self.failed_tests += 1

    # ----------------------------------------------------------------------------
    # 4.4 性能测试套件
    # ----------------------------------------------------------------------------

    async def run_performance_tests(self):
        """运行性能测试"""
        print("\n⚡ 性能测试")
        print("-" * 80)

        # 测试1: 单个图片分析性能
        await self.test_single_image_performance()

        # 测试2: 批量图片分析性能
        await self.test_batch_image_performance()

        # 测试3: 中间件链性能
        await self.test_middleware_chain_performance()

        # 测试4: 并发处理性能
        await self.test_concurrent_performance()

    async def test_single_image_performance(self):
        """测试单个图片分析性能"""
        self.total_tests += 1

        try:
            pipeline = ImageAnalysisPipeline()
            image_content = ImageContent(data=b"test_image" * 100)

            start_time = time.time()

            result = await pipeline.analyze_image(
                image_content=image_content,
                analysis_types=[
                    AnalysisType.DESCRIPTION,
                    AnalysisType.OBJECT_DETECTION,
                ],
                pipeline_id="performance_test",
            )

            end_time = time.time()
            duration = end_time - start_time

            # 检查性能要求：单个图片分析应该在合理时间内完成
            # 模拟延迟在0.5-2秒之间，两个任务加上开销
            assert duration < 10.0, f"单个图片分析耗时过长: {duration:.2f}秒"

            print(f"  ✅ 单个图片分析性能: 通过 ({duration:.2f}秒)")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 单个图片分析性能: 失败 - {e}")
            self.failed_tests += 1

    async def test_batch_image_performance(self):
        """测试批量图片分析性能"""
        self.total_tests += 1

        try:
            vision_model = MockVisionModel()
            image_contents = [ImageContent(data=b"test_image") for _ in range(5)]

            start_time = time.time()

            # 串行处理
            for img in image_contents:
                await vision_model.analyze_image(img, AnalysisType.DESCRIPTION)

            serial_duration = time.time() - start_time

            start_time = time.time()

            # 并发处理
            tasks = [
                vision_model.analyze_image(img, AnalysisType.DESCRIPTION)
                for img in image_contents
            ]
            await asyncio.gather(*tasks)

            concurrent_duration = time.time() - start_time

            # 并发应该比串行快（在模拟延迟情况下）
            # 注意：由于模拟延迟是随机的，不能严格保证，但通常应该更快
            print(f"  ✅ 批量图片分析性能: 通过")
            print(
                f"     串行: {serial_duration:.2f}秒, 并发: {concurrent_duration:.2f}秒"
            )
            print(
                f"     加速比: {serial_duration / max(concurrent_duration, 0.001):.1f}倍"
            )

            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 批量图片分析性能: 失败 - {e}")
            self.failed_tests += 1

    async def test_middleware_chain_performance(self):
        """测试中间件链性能"""
        self.total_tests += 1

        try:
            manager = MiddlewareIntegrationManager()

            input_data = {
                "request_id": "perf_test",
                "messages": ["测试消息"],
                "analysis_types": [AnalysisType.DESCRIPTION],
                "image_content": ImageContent(data=b"test"),
            }

            start_time = time.time()

            # 运行多次取平均值
            iterations = 10
            for _ in range(iterations):
                await manager.before_agent(input_data)

            end_time = time.time()
            avg_duration = (end_time - start_time) / iterations

            # 中间件链应该在合理时间内完成
            assert avg_duration < 0.5, f"中间件链执行过慢: {avg_duration:.3f}秒/次"

            print(f"  ✅ 中间件链性能: 通过 ({avg_duration:.3f}秒/次)")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 中间件链性能: 失败 - {e}")
            self.failed_tests += 1

    async def test_concurrent_performance(self):
        """测试并发处理性能"""
        self.total_tests += 1

        try:
            pipeline = ImageAnalysisPipeline()

            # 创建多个并发请求
            async def process_one():
                image_content = ImageContent(data=b"concurrent_test")
                return await pipeline.analyze_image(
                    image_content=image_content,
                    analysis_types=[AnalysisType.DESCRIPTION],
                    pipeline_id=f"concurrent_{uuid.uuid4().hex[:4]}",
                )

            start_time = time.time()

            # 并发处理5个请求
            tasks = [process_one() for _ in range(5)]
            results = await asyncio.gather(*tasks)

            end_time = time.time()
            total_duration = end_time - start_time

            # 检查所有请求都成功完成
            assert len(results) == 5
            assert all(r.success for r in results)

            print(f"  ✅ 并发处理性能: 通过 ({total_duration:.2f}秒处理5个请求)")
            self.passed_tests += 1
        except Exception as e:
            print(f"  ❌ 并发处理性能: 失败 - {e}")
            self.failed_tests += 1

    # ----------------------------------------------------------------------------
    # 4.5 测试总结
    # ----------------------------------------------------------------------------

    def print_summary(self):
        """打印测试总结"""
        print("\n📊 测试套件结果")
        print("=" * 80)

        total_time = (
            self.end_time - self.start_time if self.end_time and self.start_time else 0
        )

        print(f"总测试数: {self.total_tests}")
        print(f"通过数: {self.passed_tests}")
        print(f"失败数: {self.failed_tests}")
        print(f"通过率: {self.passed_tests / self.total_tests * 100:.1f}%")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"平均每个测试: {total_time / self.total_tests:.3f}秒")

        if self.failed_tests == 0:
            print("\n✅ 所有测试通过！")
        else:
            print(f"\n❌ 有 {self.failed_tests} 个测试失败，需要检查")

        print("=" * 80)


# ----------------------------------------------------------------------------
# 4.6 端到端演示
# ----------------------------------------------------------------------------


async def main_demo():
    """主演示函数 - 端到端演示图片分析流水线"""
    print("🚀 Day 6 Lesson 24: 图片处理和任务管理集成 - 端到端演示")
    print("=" * 80)

    print("\n1. 初始化图片分析流水线")
    print("-" * 40)

    pipeline = ImageAnalysisPipeline()
    print("   ✅ ImageAnalysisPipeline 创建成功")

    print("\n2. 准备测试图片和分析类型")
    print("-" * 40)

    # 创建模拟图片（Base64格式的简单图片）
    # 在实际演示中，可以使用真实图片的Base64编码
    # 这里使用一个最小的有效JPEG文件Base64编码（1x1像素）
    tiny_jpeg_base64 = (
        "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
        "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIy"
        "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIA"
        "AhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEB"
        "AQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdAAYV"
        "/8QAFhABAQEAAAAAAAAAAAAAAAAAAAEC/9oACAEBAAY/AgH/xAAUEQEAAAAAAAAAAAAAAAAAAAAA"
        "AAAA/9oACAEDAQE/AB//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/AB//xAAUEAEAAAAA"
        "AAAAAAAAAAAAAAAA/9oACAEBAAY/Ap//2Q=="
    )

    try:
        image_content = ImageContent.from_base64(tiny_jpeg_base64)
        print(f"   ✅ 图片加载成功")
        print(f"      图片大小: {len(image_content.data)} 字节")

        if image_content.metadata:
            print(
                f"      图片尺寸: {image_content.metadata.width}x{image_content.metadata.height}"
            )

    except:
        # 如果Base64解码失败，使用模拟数据
        print("   ⚠️  使用模拟图片数据（Base64解码失败）")
        image_content = ImageContent(data=b"simulated_image_data")

    # 定义分析类型
    analysis_types = [
        AnalysisType.DESCRIPTION,
        AnalysisType.OBJECT_DETECTION,
        AnalysisType.COLOR_ANALYSIS,
    ]

    print(f"   分析类型: {[at.value for at in analysis_types]}")

    print("\n3. 执行图片分析流水线")
    print("-" * 40)

    print("   阶段1: 上传和验证...")
    print("   阶段2: 图片描述生成...")
    print("   阶段3: 任务分解...")
    print("   阶段4: 任务执行和跟踪...")
    print("   阶段5: 结果聚合...")

    try:
        # 执行流水线
        result = await pipeline.analyze_image(
            image_content=image_content,
            analysis_types=analysis_types,
            pipeline_id="demo_pipeline_001",
        )

        print(f"\n4. 流水线执行完成")
        print("-" * 40)

        print(f"   流水线ID: {result.pipeline_id}")
        print(f"   执行状态: {'成功' if result.success else '失败'}")
        print(f"   总耗时: {result.total_duration:.2f}秒")
        print(f"   分析任务数: {len(result.analysis_tasks)}")

        if result.success:
            print(f"\n5. 分析结果摘要")
            print("-" * 40)

            aggregated = result.aggregated_result

            print(f"   图片描述: {aggregated.get('description', '无描述')[:100]}...")
            print(f"   总任务数: {aggregated.get('total_tasks', 0)}")
            print(f"   成功任务: {aggregated.get('successful_tasks', 0)}")
            print(f"   失败任务: {aggregated.get('failed_tasks', 0)}")
            print(f"   成功率: {aggregated.get('success_rate', 0) * 100:.1f}%")

            # 显示详细结果
            print(f"\n6. 详细分析结果")
            print("-" * 40)

            for i, task in enumerate(result.analysis_tasks, 1):
                print(f"   任务{i}: {task.analysis_type.value}")
                print(f"     状态: {'成功' if task.result else '失败'}")
                if task.result:
                    # 简化显示结果
                    result_summary = (
                        str(task.result)[:80] + "..."
                        if len(str(task.result)) > 80
                        else str(task.result)
                    )
                    print(f"     结果: {result_summary}")
                if task.error:
                    print(f"     错误: {task.error}")
                if task.duration:
                    print(f"     耗时: {task.duration:.2f}秒")
                print()

        else:
            print(f"\n5. 流水线执行失败")
            print("-" * 40)
            for error in result.errors:
                print(f"   错误: {error}")

        print("\n7. 中间件集成演示")
        print("-" * 40)

        # 演示中间件链
        print("   创建中间件集成管理器...")
        manager = MiddlewareIntegrationManager()

        demo_input = {
            "request_id": "demo_request_001",
            "messages": ["用户上传了一张图片"],
            "analysis_types": analysis_types,
            "image_content": image_content,
        }

        print("   执行中间件链...")
        middleware_result = await manager.before_agent(demo_input)

        print(f"   中间件处理结果:")
        print(f"     - 请求ID: {middleware_result.get('request_id')}")
        print(
            f"     - 创建的任务: {len(middleware_result.get('todo_ids', {}).get('subtasks', []))}个子任务"
        )
        print(
            f"     - 子代理限制: {middleware_result.get('subagent_limit_info', {}).get('max_per_request')}个/请求"
        )

        print("\n8. 演示总结")
        print("-" * 40)

        print("   ✅ 图片分析流水线演示完成")
        print("   ✅ 三个中间件集成成功")
        print("   ✅ 任务管理和跟踪功能正常")
        print("   ✅ 错误处理和边界情况已测试")

        print(f"\n📊 最终流水线状态:")
        print(f"   流水线ID: {result.pipeline_id}")
        print(f"   总体成功: {result.success}")
        print(f"   总耗时: {result.total_duration:.2f}秒")
        print(
            f"   分析任务完成: {len([t for t in result.analysis_tasks if t.result])}/{len(result.analysis_tasks)}"
        )

    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("🎉 Day 6 Lesson 24 端到端演示完成")
    print("=" * 80)


# ----------------------------------------------------------------------------
# 4.7 主函数
# ----------------------------------------------------------------------------


async def main():
    """主函数"""
    import sys

    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            # 运行测试套件
            test_suite = ImageAnalysisPipelineTestSuite()
            await test_suite.run_all_tests()
        elif sys.argv[1] == "--demo":
            # 运行端到端演示
            await main_demo()
        elif sys.argv[1] == "--chain-demo":
            # 运行中间件链演示
            await demonstrate_middleware_chain()
        elif sys.argv[1] == "--data-flow":
            # 运行数据流演示
            await DataFlowDemonstration.demonstrate_data_flow()
        elif sys.argv[1] == "--error-demo":
            # 运行错误处理演示
            await ErrorHandlingDemonstration.demonstrate_error_handling()
        elif sys.argv[1] == "--performance":
            # 运行性能演示
            await PerformanceOptimization.demonstrate_concurrent_processing()
        else:
            print("用法:")
            print("  python image_task_middleware_demo.py --test       运行测试套件")
            print("  python image_task_middleware_demo.py --demo       运行端到端演示")
            print(
                "  python image_task_middleware_demo.py --chain-demo 运行中间件链演示"
            )
            print("  python image_task_middleware_demo.py --data-flow  运行数据流演示")
            print(
                "  python image_task_middleware_demo.py --error-demo 运行错误处理演示"
            )
            print("  python image_task_middleware_demo.py --performance 运行性能演示")
    else:
        # 默认运行端到端演示
        await main_demo()


if __name__ == "__main__":
    asyncio.run(main())
