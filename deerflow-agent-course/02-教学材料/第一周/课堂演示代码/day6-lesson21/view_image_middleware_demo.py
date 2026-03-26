#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 6 Lesson 21: ViewImageMiddleware - 课堂演示代码

本文件提供完整的图片查看中间件实现，用于课堂教学演示。
采用四部分结构设计，全面展示图片处理中间件的各个方面：
1. 图片处理基础：图片格式、元数据、处理器基础
2. 图片验证与编码系统：格式验证、Base64编解码、视觉模型集成
3. ViewImageMiddleware实现：中间件核心逻辑与图片描述生成
4. 完整测试系统与端到端演示：单元测试、集成测试、端到端演示

教学目标：
1. 理解现代AI Agent系统中图片处理的核心需求和挑战
2. 掌握Base64编码/解码原理及其在图片传输中的应用
3. 掌握图片验证逻辑（大小、格式、安全性验证）
4. 能够实现基本的图片描述生成中间件
5. 能够测试和验证图片处理系统的健壮性

运行要求：
Python 3.12+, 安装依赖: asyncio, typing-extensions, dataclasses-json, pillow (PIL)
前置课程: 已完成ToolErrorHandlingMiddleware、ClarificationMiddleware、TitleMiddleware学习

作者: 张老师 (DeerFlow核心贡献者)
版本: v1.0
日期: 2024年4月2日
"""

import asyncio
import re
import time
import json
import random
import base64
import io
import mimetypes
from typing import List, Dict, Optional, Tuple, Any, Set, Union, BinaryIO
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter, defaultdict
import heapq
from PIL import Image, UnidentifiedImageError
import warnings

# ============================================================================
# 第一部分：图片处理基础
# ============================================================================


class ImageFormat(Enum):
    """图片格式枚举"""

    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    BMP = "bmp"
    WEBP = "webp"
    TIFF = "tiff"
    SVG = "svg"  # 矢量图，需要特殊处理

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

    def get_mime_type(self) -> str:
        """获取MIME类型"""
        format_to_mime = {
            ImageFormat.JPEG: "image/jpeg",
            ImageFormat.PNG: "image/png",
            ImageFormat.GIF: "image/gif",
            ImageFormat.BMP: "image/bmp",
            ImageFormat.WEBP: "image/webp",
            ImageFormat.TIFF: "image/tiff",
            ImageFormat.SVG: "image/svg+xml",
        }
        return format_to_mime[self]

    def is_supported(self) -> bool:
        """是否支持该格式"""
        # 假设SVG需要特殊处理，其他格式都支持
        return self != ImageFormat.SVG or self.is_supported_svg()

    def is_supported_svg(self) -> bool:
        """是否支持SVG格式（需要额外库）"""
        # 简化实现：假设不支持SVG
        return False

    def get_recommended_extension(self) -> str:
        """获取推荐的文件扩展名"""
        format_to_ext = {
            ImageFormat.JPEG: ".jpg",
            ImageFormat.PNG: ".png",
            ImageFormat.GIF: ".gif",
            ImageFormat.BMP: ".bmp",
            ImageFormat.WEBP: ".webp",
            ImageFormat.TIFF: ".tiff",
            ImageFormat.SVG: ".svg",
        }
        return format_to_ext[self]


@dataclass
class ImageMetadata:
    """图片元数据"""

    width: int  # 宽度（像素）
    height: int  # 高度（像素）
    format: ImageFormat  # 图片格式
    size_bytes: int  # 文件大小（字节）
    color_mode: str  # 颜色模式：RGB, RGBA, L, P等
    has_alpha: bool = False  # 是否有透明通道
    is_animated: bool = False  # 是否是动画（GIF）
    frame_count: int = 1  # 帧数
    dpi: Tuple[int, int] = (72, 72)  # 分辨率（DPI）

    @property
    def aspect_ratio(self) -> float:
        """宽高比"""
        return self.width / self.height if self.height > 0 else 0.0

    @property
    def megapixels(self) -> float:
        """百万像素"""
        return (self.width * self.height) / 1_000_000.0

    @property
    def size_mb(self) -> float:
        """大小（MB）"""
        return self.size_bytes / 1_048_576.0

    def is_landscape(self) -> bool:
        """是否是横向"""
        return self.width > self.height

    def is_portrait(self) -> bool:
        """是否是纵向"""
        return self.height > self.width

    def is_square(self) -> bool:
        """是否是正方形"""
        return self.width == self.height

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "width": self.width,
            "height": self.height,
            "format": self.format.value,
            "size_bytes": self.size_bytes,
            "size_mb": self.size_mb,
            "color_mode": self.color_mode,
            "has_alpha": self.has_alpha,
            "is_animated": self.is_animated,
            "frame_count": self.frame_count,
            "dpi": self.dpi,
            "aspect_ratio": self.aspect_ratio,
            "megapixels": self.megapixels,
            "orientation": "landscape"
            if self.is_landscape()
            else "portrait"
            if self.is_portrait()
            else "square",
        }


@dataclass
class ImageContent:
    """图片内容表示"""

    data: bytes  # 原始二进制数据
    metadata: ImageMetadata  # 图片元数据
    base64_encoded: Optional[str] = None  # Base64编码后的字符串
    description: Optional[str] = None  # 图片描述
    thumbnail_data: Optional[bytes] = None  # 缩略图数据

    def encode_base64(self) -> str:
        """Base64编码"""
        if self.base64_encoded is None:
            self.base64_encoded = base64.b64encode(self.data).decode("utf-8")
        return self.base64_encoded

    def decode_base64(self, base64_string: str) -> bytes:
        """Base64解码"""
        self.base64_encoded = base64_string
        self.data = base64.b64decode(base64_string)
        return self.data

    def create_thumbnail(self, max_size: Tuple[int, int] = (128, 128)) -> bytes:
        """创建缩略图"""
        try:
            img = Image.open(io.BytesIO(self.data))
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # 保存为JPEG格式（兼容性好）
            output = io.BytesIO()
            img.save(output, format="JPEG")
            self.thumbnail_data = output.getvalue()
            return self.thumbnail_data
        except Exception as e:
            warnings.warn(f"创建缩略图失败: {e}")
            return b""

    def get_data_url(self) -> str:
        """获取Data URL"""
        mime_type = self.metadata.format.get_mime_type()
        encoded = self.encode_base64()
        return f"data:{mime_type};base64,{encoded}"


class BaseImageProcessor:
    """基础图片处理器（抽象基类）"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "max_image_size_mb": 10.0,
            "supported_formats": ["jpeg", "png", "gif", "bmp", "webp"],
            "enable_thumbnail": True,
            "thumbnail_size": (128, 128),
        }

    async def process(self, image_data: bytes) -> ImageContent:
        """处理图片（抽象方法）"""
        raise NotImplementedError

    async def validate(self, image_data: bytes) -> Tuple[bool, List[str]]:
        """验证图片（抽象方法）"""
        raise NotImplementedError

    async def extract_metadata(self, image_data: bytes) -> Optional[ImageMetadata]:
        """提取元数据（抽象方法）"""
        raise NotImplementedError


# ============================================================================
# 第二部分：图片验证与编码系统
# ============================================================================


class ImageValidator:
    """图片验证器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "max_size_mb": 10.0,
            "min_width": 10,
            "min_height": 10,
            "max_width": 10000,
            "max_height": 10000,
            "max_aspect_ratio": 10.0,
            "min_aspect_ratio": 0.1,
            "supported_formats": [
                ImageFormat.JPEG,
                ImageFormat.PNG,
                ImageFormat.GIF,
                ImageFormat.WEBP,
            ],
            "block_animated": False,  # 是否阻止动画图片
            "check_corruption": True,
        }

    async def validate(
        self, image_data: bytes
    ) -> Tuple[bool, List[str], Optional[ImageMetadata]]:
        """验证图片"""
        errors = []

        # 1. 检查基本大小
        size_mb = len(image_data) / 1_048_576.0
        if size_mb > self.config["max_size_mb"]:
            errors.append(
                f"图片大小超过限制: {size_mb:.2f}MB > {self.config['max_size_mb']}MB"
            )

        # 2. 尝试打开图片获取元数据
        metadata = await self._extract_metadata(image_data)
        if metadata is None:
            errors.append("无法识别图片格式或图片已损坏")
            return False, errors, None

        # 3. 检查格式支持
        if metadata.format not in self.config["supported_formats"]:
            errors.append(f"不支持的图片格式: {metadata.format.value}")

        # 4. 检查尺寸
        if metadata.width < self.config["min_width"]:
            errors.append(
                f"图片宽度过小: {metadata.width} < {self.config['min_width']}"
            )
        if metadata.height < self.config["min_height"]:
            errors.append(
                f"图片高度过小: {metadata.height} < {self.config['min_height']}"
            )
        if metadata.width > self.config["max_width"]:
            errors.append(
                f"图片宽度过大: {metadata.width} > {self.config['max_width']}"
            )
        if metadata.height > self.config["max_height"]:
            errors.append(
                f"图片高度过大: {metadata.height} > {self.config['max_height']}"
            )

        # 5. 检查宽高比
        aspect_ratio = metadata.aspect_ratio
        min_ratio = self.config["min_aspect_ratio"]
        max_ratio = self.config["max_aspect_ratio"]
        if aspect_ratio < min_ratio or aspect_ratio > max_ratio:
            errors.append(
                f"图片宽高比异常: {aspect_ratio:.2f} (允许范围: {min_ratio}-{max_ratio})"
            )

        # 6. 检查动画
        if self.config["block_animated"] and metadata.is_animated:
            errors.append("动画图片被禁止")

        # 7. 检查损坏（通过PIL验证）
        if self.config["check_corruption"]:
            try:
                Image.open(io.BytesIO(image_data)).verify()
            except Exception as e:
                errors.append(f"图片可能已损坏: {str(e)}")

        return len(errors) == 0, errors, metadata

    async def _extract_metadata(self, image_data: bytes) -> Optional[ImageMetadata]:
        """提取图片元数据"""
        try:
            img = Image.open(io.BytesIO(image_data))

            # 获取格式
            format_str = img.format or "UNKNOWN"
            image_format = ImageFormat.from_extension(f".{format_str.lower()}")
            if image_format is None:
                # 尝试通过MIME类型
                mime_type = mimetypes.guess_type(f"test.{format_str}")[0]
                image_format = (
                    ImageFormat.from_mime_type(mime_type) if mime_type else None
                )

            if image_format is None:
                image_format = ImageFormat.JPEG  # 默认

            # 检查是否动画
            is_animated = getattr(img, "is_animated", False)
            frame_count = getattr(img, "n_frames", 1)

            # 检查是否有透明通道
            has_alpha = img.mode in ("RGBA", "LA", "P") or "transparency" in img.info

            # 获取DPI
            dpi = img.info.get("dpi", (72, 72))
            if isinstance(dpi, (int, float)):
                dpi = (int(dpi), int(dpi))
            else:
                # 确保是整数元组
                dpi = (int(dpi[0]), int(dpi[1]))

            return ImageMetadata(
                width=img.width,
                height=img.height,
                format=image_format,
                size_bytes=len(image_data),
                color_mode=img.mode,
                has_alpha=has_alpha,
                is_animated=is_animated,
                frame_count=frame_count,
                dpi=dpi,
            )
        except Exception as e:
            warnings.warn(f"提取图片元数据失败: {e}")
            return None


class Base64ImageEncoder:
    """Base64图片编码器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "include_data_url_prefix": True,
            "chunk_size": 76,  # Base64每行字符数（RFC 2045）
            "url_safe": False,  # 是否使用URL安全编码
        }

    def encode(self, image_data: bytes, mime_type: Optional[str] = None) -> str:
        """编码图片为Base64"""
        if self.config["url_safe"]:
            encoded = base64.urlsafe_b64encode(image_data).decode("utf-8")
        else:
            encoded = base64.b64encode(image_data).decode("utf-8")

        # 添加Data URL前缀
        if self.config["include_data_url_prefix"] and mime_type:
            return f"data:{mime_type};base64,{encoded}"

        return encoded

    def decode(self, base64_string: str) -> bytes:
        """解码Base64为图片数据"""
        # 移除Data URL前缀
        if base64_string.startswith("data:"):
            # 格式: data:image/png;base64,<encoded>
            parts = base64_string.split(",", 1)
            if len(parts) == 2:
                base64_string = parts[1]

        # 尝试URL安全解码
        try:
            return base64.urlsafe_b64decode(base64_string)
        except Exception:
            # 回退到标准Base64
            return base64.b64decode(base64_string)

    def estimate_size(self, image_data: bytes) -> int:
        """估计Base64编码后的大小"""
        # Base64编码后大小约为原始大小的4/3
        return int(len(image_data) * 4 / 3) + 100  # 加上一些开销

    def chunk_encode(
        self, image_data: bytes, mime_type: Optional[str] = None
    ) -> List[str]:
        """分块编码（用于大图片）"""
        encoded = self.encode(image_data, mime_type=None)

        # 分块
        chunk_size = self.config["chunk_size"]
        chunks = [
            encoded[i : i + chunk_size] for i in range(0, len(encoded), chunk_size)
        ]

        # 添加前缀
        if self.config["include_data_url_prefix"] and mime_type:
            prefix = f"data:{mime_type};base64,"
            chunks[0] = prefix + chunks[0]

        return chunks


class MockVisionModel:
    """模拟视觉模型（用于生成图片描述）"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "model_name": "mock-vision-v1",
            "max_description_length": 200,
            "supported_formats": [ImageFormat.JPEG, ImageFormat.PNG, ImageFormat.WEBP],
            "description_templates": [
                "这是一张{width}x{height}像素的{format}图片，看起来像{subject}。",
                "图片显示{subject}，尺寸为{width}x{height}像素，格式为{format}。",
                "这是一张关于{subject}的图片，分辨率为{width}x{height}。",
                "图片内容为{subject}，采用{format}格式保存。",
            ],
            "subjects": [
                "风景",
                "人物肖像",
                "动物",
                "建筑",
                "食物",
                "车辆",
                "自然景观",
                "城市风光",
                "抽象艺术",
                "文本截图",
                "图表",
                "产品照片",
                "室内设计",
                "夜景",
                "海滩",
                "山脉",
            ],
        }

    async def generate_description(
        self, image_data: bytes, metadata: ImageMetadata
    ) -> str:
        """生成图片描述"""
        # 模拟处理延迟
        await asyncio.sleep(0.1)

        # 基于元数据生成描述
        subject = random.choice(self.config["subjects"])
        template = random.choice(self.config["description_templates"])

        description = template.format(
            width=metadata.width,
            height=metadata.height,
            format=metadata.format.value.upper(),
            subject=subject,
            size_mb=f"{metadata.size_mb:.2f}",
            color_mode=metadata.color_mode,
        )

        # 限制长度
        max_len = self.config["max_description_length"]
        if len(description) > max_len:
            description = description[: max_len - 3] + "..."

        return description

    async def analyze_image(
        self, image_data: bytes, metadata: ImageMetadata
    ) -> Dict[str, Any]:
        """分析图片内容"""
        description = await self.generate_description(image_data, metadata)

        # 生成标签（基于随机选择）
        tags = random.sample(
            [
                "高清",
                "彩色",
                "自然",
                "真实",
                "艺术",
                "专业",
                "明亮",
                "对比度高",
                "细节丰富",
                "构图优美",
            ],
            k=random.randint(2, 5),
        )

        # 生成颜色分析
        color_palette = []
        for _ in range(random.randint(3, 7)):
            color_palette.append(
                f"#{random.randint(0, 255):02x}{random.randint(0, 255):02x}{random.randint(0, 255):02x}"
            )

        return {
            "description": description,
            "tags": tags,
            "color_palette": color_palette,
            "confidence": random.uniform(0.7, 0.95),
            "analysis_time_ms": random.randint(100, 500),
            "model_version": self.config["model_name"],
            "contains_text": random.choice([True, False]),
            "contains_faces": random.choice([True, False]),
            "estimated_subject": random.choice(self.config["subjects"]),
            "aesthetic_score": random.uniform(5.0, 9.5),
        }


# ============================================================================
# 第三部分：ViewImageMiddleware实现
# ============================================================================


@dataclass
class ViewImageState:
    """ViewImageMiddleware状态"""

    conversation_id: str
    processed_images: Dict[str, ImageContent] = field(
        default_factory=dict
    )  # image_id -> ImageContent
    image_descriptions: Dict[str, str] = field(default_factory=dict)  # image_id -> 描述
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    last_processed_time: Optional[float] = None

    def add_image(
        self,
        image_id: str,
        image_content: ImageContent,
        description: Optional[str] = None,
    ):
        """添加处理的图片"""
        self.processed_images[image_id] = image_content
        if description:
            self.image_descriptions[image_id] = description

        self.processing_history.append(
            {
                "image_id": image_id,
                "timestamp": time.time(),
                "size_bytes": image_content.metadata.size_bytes,
                "format": image_content.metadata.format.value,
                "description_added": description is not None,
            }
        )

        self.last_processed_time = time.time()

    def get_image(self, image_id: str) -> Optional[ImageContent]:
        """获取图片"""
        return self.processed_images.get(image_id)

    def get_description(self, image_id: str) -> Optional[str]:
        """获取图片描述"""
        return self.image_descriptions.get(image_id)

    def has_image(self, image_id: str) -> bool:
        """检查是否有图片"""
        return image_id in self.processed_images

    def clear_old_images(self, max_age_seconds: int = 3600):
        """清理旧图片"""
        current_time = time.time()
        to_remove = []

        for image_id, content in self.processed_images.items():
            # 简化实现：使用最后处理时间
            if (
                self.last_processed_time
                and current_time - self.last_processed_time > max_age_seconds
            ):
                to_remove.append(image_id)

        for image_id in to_remove:
            del self.processed_images[image_id]
            if image_id in self.image_descriptions:
                del self.image_descriptions[image_id]

        # 清理历史记录
        cutoff_time = current_time - max_age_seconds
        self.processing_history = [
            entry
            for entry in self.processing_history
            if entry["timestamp"] > cutoff_time
        ]


class ViewImageMiddleware:
    """图片查看中间件"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "enable_validation": True,
            "enable_description": True,
            "max_images_per_conversation": 10,
            "image_retention_seconds": 3600,
            "auto_cleanup": True,
            "generate_thumbnails": True,
            "thumbnail_size": (128, 128),
            "vision_model_config": {},  # 视觉模型配置
        }

        self.validator = ImageValidator()
        self.encoder = Base64ImageEncoder()
        self.vision_model = MockVisionModel(self.config.get("vision_model_config", {}))
        self.states: Dict[str, ViewImageState] = {}  # conversation_id -> state

    async def process(
        self, request: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理图片查看请求"""

        # 1. 获取或创建状态
        conversation_id = request.get("conversation_id", "default")
        state = self._get_or_create_state(conversation_id)

        # 2. 清理旧图片
        if self.config["auto_cleanup"]:
            state.clear_old_images(self.config["image_retention_seconds"])

        # 3. 检查请求类型
        action = request.get("action", "view")

        if action == "upload":
            return await self._handle_upload(request, state, context)
        elif action == "view":
            return await self._handle_view(request, state, context)
        elif action == "describe":
            return await self._handle_describe(request, state, context)
        elif action == "list":
            return await self._handle_list(request, state, context)
        else:
            return self._create_error_response(
                error_code="INVALID_ACTION",
                message=f"不支持的操作: {action}",
                details={"supported_actions": ["upload", "view", "describe", "list"]},
            )

    async def _handle_upload(
        self, request: Dict[str, Any], state: ViewImageState, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理图片上传"""

        # 检查图片数据
        image_data = request.get("image_data")
        image_id = request.get(
            "image_id", f"img_{int(time.time())}_{random.randint(1000, 9999)}"
        )

        if not image_data:
            return self._create_error_response(
                error_code="MISSING_IMAGE_DATA",
                message="缺少图片数据",
                details={"required_field": "image_data"},
            )

        # 检查图片数量限制
        if len(state.processed_images) >= self.config["max_images_per_conversation"]:
            return self._create_error_response(
                error_code="IMAGE_LIMIT_EXCEEDED",
                message=f"图片数量超过限制: {self.config['max_images_per_conversation']}",
                details={"current_count": len(state.processed_images)},
            )

        # 验证图片
        if self.config["enable_validation"]:
            is_valid, errors, metadata = await self.validator.validate(image_data)
            if not is_valid:
                return self._create_error_response(
                    error_code="IMAGE_VALIDATION_FAILED",
                    message="图片验证失败",
                    details={"errors": errors},
                )
        else:
            # 简单验证
            metadata = await self.validator._extract_metadata(image_data)
            if metadata is None:
                return self._create_error_response(
                    error_code="INVALID_IMAGE", message="无法识别图片格式", details={}
                )

        # 类型检查：此时metadata不应为None
        assert metadata is not None, "metadata should not be None at this point"

        # 创建图片内容对象
        image_content = ImageContent(
            data=image_data,
            metadata=metadata,
        )

        # 生成缩略图
        if self.config["generate_thumbnails"]:
            image_content.create_thumbnail(self.config["thumbnail_size"])

        # 保存到状态
        state.add_image(image_id, image_content)

        # 返回响应
        return {
            "success": True,
            "image_id": image_id,
            "metadata": metadata.to_dict(),
            "thumbnail_available": image_content.thumbnail_data is not None,
            "message": "图片上传成功",
            "timestamp": time.time(),
        }

    async def _handle_view(
        self, request: Dict[str, Any], state: ViewImageState, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理图片查看"""

        image_id = request.get("image_id")
        if not image_id:
            return self._create_error_response(
                error_code="MISSING_IMAGE_ID",
                message="缺少图片ID",
                details={"required_field": "image_id"},
            )

        # 获取图片
        image_content = state.get_image(image_id)
        if not image_content:
            return self._create_error_response(
                error_code="IMAGE_NOT_FOUND",
                message=f"图片不存在: {image_id}",
                details={"available_images": list(state.processed_images.keys())},
            )

        # 获取描述（如果存在）
        description = state.get_description(image_id)

        # 构建响应
        response = {
            "success": True,
            "image_id": image_id,
            "metadata": image_content.metadata.to_dict(),
            "description": description,
            "has_thumbnail": image_content.thumbnail_data is not None,
            "base64_preview": None,
        }

        # 如果请求包含预览标记，生成Base64预览
        if request.get("include_preview", False):
            # 使用缩略图或原图（如果缩略图不存在）
            preview_data = image_content.thumbnail_data or image_content.data
            mime_type = image_content.metadata.format.get_mime_type()
            response["base64_preview"] = self.encoder.encode(preview_data, mime_type)
            response["preview_size_bytes"] = len(preview_data)

        return response

    async def _handle_describe(
        self, request: Dict[str, Any], state: ViewImageState, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理图片描述生成"""

        if not self.config["enable_description"]:
            return self._create_error_response(
                error_code="DESCRIPTION_DISABLED",
                message="图片描述功能已禁用",
                details={},
            )

        image_id = request.get("image_id")
        if not image_id:
            return self._create_error_response(
                error_code="MISSING_IMAGE_ID",
                message="缺少图片ID",
                details={"required_field": "image_id"},
            )

        # 获取图片
        image_content = state.get_image(image_id)
        if not image_content:
            return self._create_error_response(
                error_code="IMAGE_NOT_FOUND",
                message=f"图片不存在: {image_id}",
                details={"available_images": list(state.processed_images.keys())},
            )

        # 检查是否已有描述
        existing_description = state.get_description(image_id)
        if existing_description and not request.get("force_regenerate", False):
            return {
                "success": True,
                "image_id": image_id,
                "description": existing_description,
                "regenerated": False,
                "message": "使用现有描述",
                "timestamp": time.time(),
            }

        # 生成描述
        try:
            analysis_result = await self.vision_model.analyze_image(
                image_content.data, image_content.metadata
            )

            description = analysis_result["description"]

            # 保存描述
            state.image_descriptions[image_id] = description

            return {
                "success": True,
                "image_id": image_id,
                "description": description,
                "regenerated": True,
                "analysis_details": {
                    "tags": analysis_result.get("tags", []),
                    "confidence": analysis_result.get("confidence", 0.0),
                    "model_version": analysis_result.get("model_version", "unknown"),
                    "aesthetic_score": analysis_result.get("aesthetic_score", 0.0),
                },
                "message": "图片描述生成成功",
                "timestamp": time.time(),
            }
        except Exception as e:
            return self._create_error_response(
                error_code="DESCRIPTION_GENERATION_FAILED",
                message=f"图片描述生成失败: {str(e)}",
                details={"error": str(e)},
            )

    async def _handle_list(
        self, request: Dict[str, Any], state: ViewImageState, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理图片列表"""

        images = []
        for image_id, image_content in state.processed_images.items():
            images.append(
                {
                    "image_id": image_id,
                    "metadata": image_content.metadata.to_dict(),
                    "has_description": image_id in state.image_descriptions,
                    "has_thumbnail": image_content.thumbnail_data is not None,
                    "uploaded_at": next(
                        (
                            entry["timestamp"]
                            for entry in state.processing_history
                            if entry["image_id"] == image_id
                        ),
                        None,
                    ),
                }
            )

        return {
            "success": True,
            "conversation_id": state.conversation_id,
            "total_images": len(images),
            "images": images,
            "has_auto_cleanup": self.config["auto_cleanup"],
            "image_retention_seconds": self.config["image_retention_seconds"],
            "timestamp": time.time(),
        }

    def _get_or_create_state(self, conversation_id: str) -> ViewImageState:
        """获取或创建状态"""
        if conversation_id not in self.states:
            self.states[conversation_id] = ViewImageState(
                conversation_id=conversation_id
            )
        return self.states[conversation_id]

    def _create_error_response(
        self, error_code: str, message: str, details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details,
                "timestamp": time.time(),
            },
        }


# ============================================================================
# 第四部分：完整测试系统与端到端演示
# ============================================================================


class ViewImageMiddlewareTestSuite:
    """ViewImageMiddleware测试套件"""

    def __init__(self):
        self.middleware = ViewImageMiddleware()
        self.test_images = self._create_test_images()

    def _create_test_images(self) -> Dict[str, bytes]:
        """创建测试图片（使用PIL生成简单图片）"""
        test_images = {}

        # 创建不同格式的测试图片
        formats = ["JPEG", "PNG", "GIF"]
        sizes = [(100, 100), (200, 150), (300, 200)]

        for i, (format_name, size) in enumerate(zip(formats * 2, sizes * 2)):
            # 创建简单图片
            img = Image.new(
                "RGB",
                size,
                color=(
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255),
                ),
            )

            # 保存到字节流
            img_bytes = io.BytesIO()
            img.save(img_bytes, format=format_name)

            test_images[f"test_{i}_{format_name.lower()}"] = img_bytes.getvalue()

        return test_images

    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": {},
            "start_time": time.time(),
        }

        # 运行各个测试
        tests = [
            self.test_image_upload,
            self.test_image_validation,
            self.test_image_description,
            self.test_image_listing,
            self.test_error_handling,
            self.test_concurrent_requests,
        ]

        for test_func in tests:
            test_name = test_func.__name__
            test_results["total_tests"] += 1

            try:
                result = await test_func()
                test_results["test_details"][test_name] = {
                    "status": "passed",
                    "result": result,
                }
                test_results["passed_tests"] += 1
                print(f"✅ {test_name}: 通过")
            except Exception as e:
                test_results["test_details"][test_name] = {
                    "status": "failed",
                    "error": str(e),
                    "traceback": self._format_exception(e),
                }
                test_results["failed_tests"] += 1
                print(f"❌ {test_name}: 失败 - {e}")

        test_results["end_time"] = time.time()
        test_results["duration_seconds"] = (
            test_results["end_time"] - test_results["start_time"]
        )

        return test_results

    async def test_image_upload(self) -> Dict[str, Any]:
        """测试图片上传"""
        image_id = "test_upload_1"
        image_data = self.test_images["test_0_jpeg"]

        request = {
            "action": "upload",
            "image_id": image_id,
            "image_data": image_data,
            "conversation_id": "test_conversation",
        }

        response = await self.middleware.process(request, {})

        assert response["success"] == True, "上传应成功"
        assert response["image_id"] == image_id, "图片ID应匹配"
        assert "metadata" in response, "应包含元数据"

        return response

    async def test_image_validation(self) -> Dict[str, Any]:
        """测试图片验证"""
        # 测试无效图片
        invalid_data = b"not an image"

        request = {
            "action": "upload",
            "image_id": "test_invalid",
            "image_data": invalid_data,
            "conversation_id": "test_conversation",
        }

        response = await self.middleware.process(request, {})

        assert response["success"] == False, "无效图片应失败"
        assert response["error"]["code"] == "IMAGE_VALIDATION_FAILED", (
            "应返回验证失败错误"
        )

        return response

    async def test_image_description(self) -> Dict[str, Any]:
        """测试图片描述生成"""
        # 先上传图片
        image_id = "test_describe_1"
        image_data = self.test_images["test_1_png"]

        upload_request = {
            "action": "upload",
            "image_id": image_id,
            "image_data": image_data,
            "conversation_id": "test_conversation",
        }

        await self.middleware.process(upload_request, {})

        # 请求描述
        describe_request = {
            "action": "describe",
            "image_id": image_id,
            "conversation_id": "test_conversation",
        }

        response = await self.middleware.process(describe_request, {})

        assert response["success"] == True, "描述生成应成功"
        assert "description" in response, "应包含描述"
        assert len(response["description"]) > 0, "描述不应为空"

        return response

    async def test_image_listing(self) -> Dict[str, Any]:
        """测试图片列表"""
        request = {
            "action": "list",
            "conversation_id": "test_conversation",
        }

        response = await self.middleware.process(request, {})

        assert response["success"] == True, "列表查询应成功"
        assert "images" in response, "应包含图片列表"
        assert isinstance(response["images"], list), "图片列表应为列表类型"

        return response

    async def test_error_handling(self) -> Dict[str, Any]:
        """测试错误处理"""
        # 测试缺少图片ID
        request = {
            "action": "view",
            "conversation_id": "test_conversation",
            # 缺少image_id
        }

        response = await self.middleware.process(request, {})

        assert response["success"] == False, "应返回错误"
        assert "error" in response, "应包含错误信息"

        return response

    async def test_concurrent_requests(self) -> Dict[str, Any]:
        """测试并发请求"""
        # 模拟并发上传
        tasks = []
        for i in range(3):
            image_id = f"concurrent_test_{i}"
            image_data = self.test_images[f"test_{i % len(self.test_images)}_jpeg"]

            request = {
                "action": "upload",
                "image_id": image_id,
                "image_data": image_data,
                "conversation_id": "concurrent_conversation",
            }

            tasks.append(self.middleware.process(request, {}))

        responses = await asyncio.gather(*tasks)

        # 检查所有请求都应成功
        for i, response in enumerate(responses):
            assert response["success"] == True, f"并发请求{i}应成功"

        return {"total_requests": len(responses), "all_success": True}

    def _format_exception(self, e: Exception) -> str:
        """格式化异常信息"""
        import traceback

        return traceback.format_exc()

    def print_test_summary(self, test_results: Dict[str, Any]):
        """打印测试摘要"""
        print("\n" + "=" * 60)
        print("ViewImageMiddleware 测试套件结果")
        print("=" * 60)

        print(f"总测试数: {test_results['total_tests']}")
        print(f"通过数: {test_results['passed_tests']}")
        print(f"失败数: {test_results['failed_tests']}")
        print(f"总耗时: {test_results['duration_seconds']:.2f}秒")

        if test_results["failed_tests"] > 0:
            print("\n失败测试详情:")
            for test_name, details in test_results["test_details"].items():
                if details["status"] == "failed":
                    print(f"  - {test_name}: {details['error']}")

        print("\n" + "=" * 60)


async def main_demo():
    """主演示函数"""
    print("🎓 Day 6 Lesson 21: ViewImageMiddleware - 演示系统")
    print("=" * 70)

    # 创建测试套件
    test_suite = ViewImageMiddlewareTestSuite()

    # 运行所有测试
    print("\n🧪 运行测试套件...")
    test_results = await test_suite.run_all_tests()

    # 打印测试摘要
    test_suite.print_test_summary(test_results)

    # 演示端到端流程
    print("\n🚀 端到端流程演示")
    print("-" * 40)

    middleware = ViewImageMiddleware()
    conversation_id = "demo_conversation"

    # 1. 上传图片
    print("1. 上传图片...")
    with open("/dev/null", "rb") as f:  # 使用虚拟数据
        # 在实际演示中，这里会使用真实图片文件
        # 由于环境限制，我们使用生成的测试图片
        test_images = test_suite.test_images
        image_data = test_images["test_0_jpeg"]

    upload_request = {
        "action": "upload",
        "image_id": "demo_image_1",
        "image_data": image_data,
        "conversation_id": conversation_id,
    }

    upload_response = await middleware.process(upload_request, {})
    print(f"   结果: {'成功' if upload_response['success'] else '失败'}")
    if upload_response["success"]:
        metadata = upload_response["metadata"]
        print(
            f"   图片信息: {metadata['width']}x{metadata['height']} {metadata['format']}"
        )

    # 2. 生成图片描述
    print("\n2. 生成图片描述...")
    describe_request = {
        "action": "describe",
        "image_id": "demo_image_1",
        "conversation_id": conversation_id,
    }

    describe_response = await middleware.process(describe_request, {})
    print(f"   结果: {'成功' if describe_response['success'] else '失败'}")
    if describe_response["success"]:
        print(f"   描述: {describe_response['description']}")

    # 3. 查看图片列表
    print("\n3. 查看图片列表...")
    list_request = {
        "action": "list",
        "conversation_id": conversation_id,
    }

    list_response = await middleware.process(list_request, {})
    print(f"   结果: {'成功' if list_response['success'] else '失败'}")
    if list_response["success"]:
        print(f"   图片数量: {list_response['total_images']}")

    # 4. 错误处理演示
    print("\n4. 错误处理演示...")
    error_request = {
        "action": "view",
        # 缺少image_id
        "conversation_id": conversation_id,
    }

    error_response = await middleware.process(error_request, {})
    print(f"   结果: {'成功' if error_response['success'] else '失败'}")
    if not error_response["success"]:
        print(f"   错误代码: {error_response['error']['code']}")
        print(f"   错误消息: {error_response['error']['message']}")

    print("\n" + "=" * 70)
    print("✅ ViewImageMiddleware 演示完成")
    print("=" * 70)


if __name__ == "__main__":
    # 运行主演示
    asyncio.run(main_demo())
