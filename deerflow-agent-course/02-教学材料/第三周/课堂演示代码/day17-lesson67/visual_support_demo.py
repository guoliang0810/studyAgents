"""
视觉能力支持演示代码 - DeerFlow Python Agent架构师训练营 第67节课

本模块展示了如何在AI Agent系统中集成视觉能力，包括：
1. 视觉模型配置管理（VisionModelConfig）
2. 图像处理管道（VisionPipeline）
3. 图像处理器抽象（ImageProcessor）
4. 格式转换、大小调整、质量优化、元数据清理
5. 视觉能力测试和验证

学习目标：
- 理解视觉AI模型的能力特点和配置方法
- 掌握图像预处理管道的重要性和实现
- 能够为不同视觉模型准备合适的输入图像
- 了解图像处理的安全和隐私考虑

作者: DeerFlow教学团队
版本: v1.0
日期: 2024年4月10日
"""

import asyncio
import io
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import yaml


# ============================================================================
# 1. 辅助函数和数据类型
# ============================================================================

def parse_size(size_str: str) -> int:
    """
    解析大小字符串（如"20MB"）为字节数
    
    Args:
        size_str: 大小字符串，支持MB、KB、GB单位
        
    Returns:
        字节数
        
    Example:
        >>> parse_size("20MB")
        20971520
        >>> parse_size("5KB")
        5120
    """
    size_str = size_str.strip().upper()
    
    if size_str.endswith("MB"):
        return int(float(size_str[:-2]) * 1024 * 1024)
    elif size_str.endswith("KB"):
        return int(float(size_str[:-2]) * 1024)
    elif size_str.endswith("GB"):
        return int(float(size_str[:-2]) * 1024 * 1024 * 1024)
    else:
        return int(size_str)


@dataclass
class ImageInfo:
    """图像信息类，用于存储图像数据和元数据"""
    data: bytes
    format: str
    filename: Optional[str] = None
    size_bytes: Optional[int] = None
    
    def __post_init__(self):
        """初始化后计算大小"""
        if self.size_bytes is None:
            self.size_bytes = len(self.data)


@dataclass
class ProcessedImage:
    """处理后的图像信息"""
    data: bytes
    format: str
    original_size: int
    processed_size: int
    
    @property
    def compression_ratio(self) -> float:
        """压缩比例"""
        return self.processed_size / self.original_size if self.original_size > 0 else 1.0
    
    @property
    def size_reduction_percent(self) -> float:
        """大小减少百分比"""
        return (1 - self.compression_ratio) * 100


# ============================================================================
# 2. 视觉模型配置类
# ============================================================================

@dataclass
class VisionModelConfig:
    """视觉模型配置类"""
    provider: str
    model_name: str
    config: Dict[str, Any]
    capabilities: List[str]
    vision_config: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict) -> "VisionModelConfig":
        """从字典创建配置"""
        return cls(
            provider=data["provider"],
            model_name=data["model_name"],
            config=data.get("config", {}),
            capabilities=data.get("capabilities", []),
            vision_config=data.get("vision_config", {})
        )
    
    def can_handle_image(self, image_size: int, image_format: str) -> bool:
        """检查是否能处理指定图像"""
        max_size = parse_size(self.vision_config.get("max_image_size", "0MB"))
        supported_formats = self.vision_config.get("supported_formats", [])
        
        return (image_size <= max_size and 
                image_format.lower() in [f.lower() for f in supported_formats])
    
    def get_max_images_per_request(self) -> int:
        """获取每个请求支持的最大图像数量"""
        return self.vision_config.get("max_images_per_request", 1)
    
    def get_detail_level(self) -> str:
        """获取细节级别（仅Claude-3支持）"""
        return self.vision_config.get("detail_level", "auto")


@dataclass
class VisionConfig:
    """视觉配置容器"""
    vision_models: Dict[str, VisionModelConfig]
    default_model: str = "gpt-4-vision"
    convert_to_supported: bool = True
    optimize_quality: bool = True
    strip_metadata: bool = True
    max_processing_time: int = 30  # 秒
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> "VisionConfig":
        """从YAML内容创建配置"""
        data = yaml.safe_load(yaml_content)
        vision_models = {}
        
        for model_name, model_data in data.get("vision_models", {}).items():
            vision_models[model_name] = VisionModelConfig.from_dict(model_data)
        
        return cls(
            vision_models=vision_models,
            default_model=data.get("default_model", "gpt-4-vision"),
            convert_to_supported=data.get("convert_to_supported", True),
            optimize_quality=data.get("optimize_quality", True),
            strip_metadata=data.get("strip_metadata", True),
            max_processing_time=data.get("max_processing_time", 30)
        )


# ============================================================================
# 3. 图像处理器抽象和具体实现
# ============================================================================

class ImageProcessor(ABC):
    """图像处理器基类"""
    
    def __init__(self, output_format: Optional[str] = None):
        self.output_format = output_format
    
    @abstractmethod
    async def process(self, image_data: bytes, input_format: str) -> bytes:
        """处理图像数据"""
        pass
    
    async def process_image_info(self, image_info: ImageInfo) -> ImageInfo:
        """处理ImageInfo对象"""
        processed_data = await self.process(image_info.data, image_info.format)
        return ImageInfo(
            data=processed_data,
            format=self.output_format or image_info.format,
            filename=image_info.filename,
            size_bytes=len(processed_data)
        )


class FormatConverter(ImageProcessor):
    """格式转换器"""
    
    def __init__(self, supported_formats: List[str], target_format: str = "jpeg"):
        super().__init__(output_format=target_format)
        self.supported_formats = supported_formats
        self.target_format = target_format
    
    async def process(self, image_data: bytes, input_format: str) -> bytes:
        """转换图像格式"""
        # 如果输入格式已经是支持格式，直接返回
        if input_format.lower() in [f.lower() for f in self.supported_formats]:
            return image_data
        
        # 使用Pillow进行格式转换
        try:
            image = Image.open(io.BytesIO(image_data))
            output_buffer = io.BytesIO()
            
            # 根据目标格式保存
            if self.target_format.lower() in ["jpeg", "jpg"]:
                if image.mode in ("RGBA", "LA"):
                    # JPEG不支持透明度，需要转换为RGB
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])
                    image = background
                image.save(output_buffer, format="JPEG", quality=85)
                self.output_format = "jpeg"
            else:
                image.save(output_buffer, format=self.target_format.upper())
                self.output_format = self.target_format.lower()
            
            return output_buffer.getvalue()
        except Exception as e:
            raise ValueError(f"格式转换失败: {e}")


class SizeResizer(ImageProcessor):
    """大小调整器"""
    
    def __init__(self, max_size_bytes: int):
        super().__init__()
        self.max_size_bytes = max_size_bytes
    
    async def process(self, image_data: bytes, input_format: str) -> bytes:
        """调整图像大小以符合大小限制"""
        if len(image_data) <= self.max_size_bytes:
            return image_data
        
        # 使用Pillow逐步降低质量/尺寸直到符合要求
        try:
            image = Image.open(io.BytesIO(image_data))
            current_data = image_data
            original_size = len(image_data)
            
            # 策略1: 降低质量
            for quality in [85, 70, 50, 30, 20]:
                output_buffer = io.BytesIO()
                image.save(output_buffer, format=input_format.upper(), quality=quality)
                current_data = output_buffer.getvalue()
                
                if len(current_data) <= self.max_size_bytes:
                    print(f"大小调整: 通过降低质量到{quality}%解决 ({original_size} -> {len(current_data)} bytes)")
                    return current_data
            
            # 策略2: 降低尺寸
            original_width, original_height = image.size
            for scale_factor in [0.9, 0.7, 0.5, 0.3]:
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                output_buffer = io.BytesIO()
                resized_image.save(output_buffer, format=input_format.upper(), quality=70)
                current_data = output_buffer.getvalue()
                
                if len(current_data) <= self.max_size_bytes:
                    print(f"大小调整: 通过缩放{scale_factor:.0%}解决 ({original_size} -> {len(current_data)} bytes)")
                    return current_data
            
            # 如果仍然超过限制，返回质量最低、尺寸最小的版本
            print(f"警告: 无法将图像大小降低到{self.max_size_bytes}字节以下，使用最小版本")
            return current_data
            
        except Exception as e:
            raise ValueError(f"大小调整失败: {e}")


class QualityOptimizer(ImageProcessor):
    """质量优化器"""
    
    def __init__(self, target_quality: int = 85, sharpen: bool = True):
        super().__init__()
        self.target_quality = target_quality
        self.sharpen = sharpen
    
    async def process(self, image_data: bytes, input_format: str) -> bytes:
        """优化图像质量"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 应用锐化（可选）
            if self.sharpen:
                from PIL import ImageFilter
                image = image.filter(ImageFilter.SHARPEN)
            
            # 调整对比度（轻微）
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.1)  # 增加10%对比度
            
            output_buffer = io.BytesIO()
            image.save(output_buffer, format=input_format.upper(), quality=self.target_quality)
            
            return output_buffer.getvalue()
        except Exception as e:
            print(f"质量优化失败，返回原图: {e}")
            return image_data


class MetadataStripper(ImageProcessor):
    """元数据清理器"""
    
    async def process(self, image_data: bytes, input_format: str) -> bytes:
        """清除图像元数据"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 创建一个新图像，只复制像素数据
            clean_image = Image.new(image.mode, image.size)
            clean_image.putdata(list(image.getdata()))
            
            output_buffer = io.BytesIO()
            clean_image.save(output_buffer, format=input_format.upper())
            
            return output_buffer.getvalue()
        except Exception as e:
            print(f"元数据清理失败，返回原图: {e}")
            return image_data


# ============================================================================
# 4. 视觉管道主类
# ============================================================================

class VisionPipeline:
    """视觉管道 - 负责图像预处理和模型适配"""
    
    def __init__(self, config: VisionConfig):
        self.config = config
        self.processors = self._initialize_processors()
    
    def _initialize_processors(self) -> List[ImageProcessor]:
        """初始化图像处理器"""
        processors = []
        
        # 格式转换器
        if self.config.convert_to_supported:
            # 收集所有模型支持的格式
            all_supported_formats = set()
            for model_config in self.config.vision_models.values():
                formats = model_config.vision_config.get("supported_formats", [])
                all_supported_formats.update(formats)
            
            if all_supported_formats:
                processors.append(FormatConverter(
                    supported_formats=list(all_supported_formats),
                    target_format="jpeg" if "jpeg" in all_supported_formats else list(all_supported_formats)[0]
                ))
        
        # 大小调整器 - 使用默认模型的大小限制
        default_model = self.config.vision_models.get(self.config.default_model)
        if default_model:
            max_size = parse_size(default_model.vision_config.get("max_image_size", "20MB"))
            processors.append(SizeResizer(max_size))
        
        # 质量优化器
        if self.config.optimize_quality:
            processors.append(QualityOptimizer())
        
        # 元数据清理器
        if self.config.strip_metadata:
            processors.append(MetadataStripper())
        
        return processors
    
    async def process_image(self, image_data: bytes, image_format: str) -> bytes:
        """处理单个图像"""
        result = image_data
        current_format = image_format
        
        for processor in self.processors:
            result = await processor.process(result, current_format)
            if processor.output_format:
                current_format = processor.output_format
        
        return result
    
    async def prepare_images_for_model(
        self, 
        images: List[ImageInfo], 
        model_name: str
    ) -> List[ProcessedImage]:
        """为特定模型准备图像"""
        model_config = self.config.vision_models.get(model_name)
        if not model_config:
            raise ValueError(f"视觉模型 {model_name} 未找到")
        
        processed_images = []
        
        for image in images:
            # 检查格式支持
            supported_formats = model_config.vision_config.get("supported_formats", [])
            if image.format.lower() not in [f.lower() for f in supported_formats]:
                # 转换为模型支持的第一个格式
                target_format = supported_formats[0] if supported_formats else "jpeg"
                converter = FormatConverter(supported_formats=[target_format], target_format=target_format)
                image_data = await converter.process(image.data, image.format)
                image_format = target_format
            else:
                image_data = image.data
                image_format = image.format
            
            # 检查大小限制
            max_size = parse_size(model_config.vision_config.get("max_image_size", "0MB"))
            if len(image_data) > max_size:
                resizer = SizeResizer(max_size)
                image_data = await resizer.process(image_data, image_format)
            
            processed_images.append(ProcessedImage(
                data=image_data,
                format=image_format,
                original_size=len(image.data),
                processed_size=len(image_data),
            ))
        
        return processed_images
    
    async def process_batch(self, images: List[ImageInfo]) -> List[ProcessedImage]:
        """批量处理图像"""
        tasks = []
        for image in images:
            task = asyncio.create_task(self._process_single_image(image))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def _process_single_image(self, image: ImageInfo) -> ProcessedImage:
        """处理单个图像（内部方法）"""
        processed_data = await self.process_image(image.data, image.format)
        
        return ProcessedImage(
            data=processed_data,
            format=image.format,  # 注意：实际格式可能已改变
            original_size=len(image.data),
            processed_size=len(processed_data),
        )


# ============================================================================
# 5. 视觉能力测试器
# ============================================================================

class ModelCapabilityTester:
    """模型能力测试器"""
    
    def __init__(self, vision_pipeline: VisionPipeline):
        self.vision_pipeline = vision_pipeline
    
    async def test_capabilities(self, model_name: str, test_images: List[ImageInfo]) -> Dict[str, Any]:
        """测试模型能力"""
        model_config = self.vision_pipeline.config.vision_models.get(model_name)
        if not model_config:
            return {"error": f"模型 {model_name} 未找到"}
        
        results = {
            "model_name": model_name,
            "provider": model_config.provider,
            "capabilities": model_config.capabilities,
            "vision_config": model_config.vision_config,
            "image_tests": []
        }
        
        for image in test_images:
            try:
                # 检查能否处理
                can_handle = model_config.can_handle_image(len(image.data), image.format)
                
                # 准备图像
                processed_images = await self.vision_pipeline.prepare_images_for_model([image], model_name)
                processed = processed_images[0] if processed_images else None
                
                results["image_tests"].append({
                    "filename": image.filename,
                    "original_size": len(image.data),
                    "original_format": image.format,
                    "can_handle": can_handle,
                    "processed_size": processed.processed_size if processed else None,
                    "compression_ratio": processed.compression_ratio if processed else None,
                    "size_reduction_percent": processed.size_reduction_percent if processed else None,
                    "success": processed is not None
                })
            except Exception as e:
                results["image_tests"].append({
                    "filename": image.filename,
                    "error": str(e),
                    "success": False
                })
        
        return results


# ============================================================================
# 6. YAML配置示例
# ============================================================================

VISION_CONFIG_YAML = """
vision_models:
  gpt-4-vision:
    provider: "openai"
    model_name: "gpt-4-vision-preview"
    config:
      temperature: 0.7
      max_tokens: 1000
    capabilities: ["text", "vision"]
    vision_config:
      max_image_size: "20MB"
      supported_formats: ["png", "jpg", "jpeg", "gif", "webp"]
      max_images_per_request: 10
  
  claude-3:
    provider: "anthropic"
    model_name: "claude-3-opus-20240229"
    config:
      temperature: 0.7
      max_tokens: 4000
    capabilities: ["text", "vision", "reasoning"]
    vision_config:
      max_image_size: "5MB"
      supported_formats: ["png", "jpg", "jpeg", "webp"]
      detail_level: "auto"  # low, high, auto
      max_images_per_request: 5

default_model: "gpt-4-vision"
convert_to_supported: true
optimize_quality: true
strip_metadata: true
max_processing_time: 30
"""


# ============================================================================
# 7. 测试函数和演示
# ============================================================================

async def create_test_image(width: int = 800, height: int = 600, format: str = "png") -> ImageInfo:
    """创建测试图像"""
    # 创建一个简单的测试图像
    image = Image.new("RGB", (width, height), color=(73, 109, 137))
    
    output_buffer = io.BytesIO()
    image.save(output_buffer, format=format.upper())
    
    return ImageInfo(
        data=output_buffer.getvalue(),
        format=format,
        filename=f"test_{width}x{height}.{format}",
        size_bytes=len(output_buffer.getvalue())
    )


async def demo_basic_usage():
    """演示基本用法"""
    print("=" * 60)
    print("视觉能力支持演示 - 基本用法")
    print("=" * 60)
    
    # 1. 加载配置
    config = VisionConfig.from_yaml(VISION_CONFIG_YAML)
    print("✅ 配置加载成功")
    print(f"   支持的模型: {list(config.vision_models.keys())}")
    print(f"   默认模型: {config.default_model}")
    
    # 2. 创建视觉管道
    pipeline = VisionPipeline(config)
    print("✅ 视觉管道创建成功")
    print(f"   处理器数量: {len(pipeline.processors)}")
    
    # 3. 创建测试图像
    test_image = await create_test_image(format="png")
    print(f"✅ 测试图像创建成功: {test_image.filename}")
    print(f"   图像大小: {test_image.size_bytes:,} bytes")
    print(f"   图像格式: {test_image.format}")
    
    # 4. 处理图像
    processed_data = await pipeline.process_image(test_image.data, test_image.format)
    print("✅ 图像处理成功")
    print(f"   处理后大小: {len(processed_data):,} bytes")
    print(f"   大小减少: {100 * (1 - len(processed_data) / test_image.size_bytes):.1f}%")
    
    # 5. 为特定模型准备图像
    processed_images = await pipeline.prepare_images_for_model([test_image], "gpt-4-vision")
    if processed_images:
        processed = processed_images[0]
        print("✅ 为GPT-4 Vision准备图像成功")
        print(f"   原始大小: {processed.original_size:,} bytes")
        print(f"   处理后大小: {processed.processed_size:,} bytes")
        print(f"   压缩比例: {processed.compression_ratio:.2f}")
        print(f"   大小减少: {processed.size_reduction_percent:.1f}%")
    
    return pipeline


async def demo_model_testing():
    """演示模型测试"""
    print("\n" + "=" * 60)
    print("视觉能力支持演示 - 模型测试")
    print("=" * 60)
    
    # 加载配置和创建管道
    config = VisionConfig.from_yaml(VISION_CONFIG_YAML)
    pipeline = VisionPipeline(config)
    tester = ModelCapabilityTester(pipeline)
    
    # 创建不同格式的测试图像
    test_images = [
        await create_test_image(800, 600, "png"),
        await create_test_image(1200, 900, "jpeg"),
        await create_test_image(400, 300, "gif"),
    ]
    
    # 测试GPT-4 Vision
    print("测试GPT-4 Vision模型...")
    gpt4_results = await tester.test_capabilities("gpt-4-vision", test_images)
    
    print(f"模型: {gpt4_results['model_name']}")
    print(f"提供商: {gpt4_results['provider']}")
    print(f"能力: {', '.join(gpt4_results['capabilities'])}")
    
    for test in gpt4_results["image_tests"]:
        status = "✅" if test.get("success", False) else "❌"
        print(f"{status} {test['filename']}: {test.get('original_size', 0):,} bytes → {test.get('processed_size', 0):,} bytes "
              f"({test.get('size_reduction_percent', 0):.1f}%减少)")
    
    # 测试Claude-3
    print("\n测试Claude-3模型...")
    claude_results = await tester.test_capabilities("claude-3", test_images[:2])  # Claude不支持GIF
    
    print(f"模型: {claude_results['model_name']}")
    print(f"提供商: {claude_results['provider']}")
    
    for test in claude_results["image_tests"]:
        status = "✅" if test.get("success", False) else "❌"
        print(f"{status} {test['filename']}: {test.get('original_size', 0):,} bytes → {test.get('processed_size', 0):,} bytes")


async def demo_advanced_features():
    """演示高级功能"""
    print("\n" + "=" * 60)
    print("视觉能力支持演示 - 高级功能")
    print("=" * 60)
    
    # 1. 自定义配置
    custom_yaml = """
vision_models:
  custom-vision-model:
    provider: "custom"
    model_name: "vision-model-v1"
    config:
      temperature: 0.5
    capabilities: ["vision", "analysis"]
    vision_config:
      max_image_size: "10MB"
      supported_formats: ["png", "jpg"]
      max_images_per_request: 3
"""
    
    config = VisionConfig.from_yaml(custom_yaml)
    pipeline = VisionPipeline(config)
    
    print("✅ 自定义配置创建成功")
    print(f"   自定义模型: {list(config.vision_models.keys())[0]}")
    
    # 2. 批量处理演示
    print("\n批量处理演示:")
    test_images = [
        await create_test_image(800, 600, "png"),
        await create_test_image(1024, 768, "jpeg"),
        await create_test_image(640, 480, "png"),
    ]
    
    start_time = asyncio.get_event_loop().time()
    processed_images = await pipeline.process_batch(test_images)
    end_time = asyncio.get_event_loop().time()
    
    print(f"✅ 批量处理 {len(test_images)} 张图像完成")
    print(f"   总处理时间: {end_time - start_time:.2f}秒")
    
    for i, processed in enumerate(processed_images):
        print(f"   图像{i+1}: {processed.original_size:,} → {processed.processed_size:,} bytes "
              f"({processed.size_reduction_percent:.1f}%减少)")
    
    # 3. 格式转换演示
    print("\n格式转换演示:")
    png_image = await create_test_image(800, 600, "png")
    converter = FormatConverter(supported_formats=["jpeg", "jpg"], target_format="jpeg")
    
    try:
        jpeg_data = await converter.process(png_image.data, "png")
        print(f"✅ PNG → JPEG转换成功")
        print(f"   原始大小: {len(png_image.data):,} bytes (PNG)")
        print(f"   转换后大小: {len(jpeg_data):,} bytes (JPEG)")
    except Exception as e:
        print(f"❌ 格式转换失败: {e}")


async def main():
    """主演示函数"""
    print("🦌 DeerFlow视觉能力支持演示")
    print("=" * 60)
    
    try:
        # 演示1: 基本用法
        pipeline = await demo_basic_usage()
        
        # 演示2: 模型测试
        await demo_model_testing()
        
        # 演示3: 高级功能
        await demo_advanced_features()
        
        print("\n" + "=" * 60)
        print("✅ 所有演示完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# 8. 单元测试
# ============================================================================

import unittest


class TestVisionSupport(unittest.TestCase):
    """视觉能力支持单元测试"""
    
    def setUp(self):
        """测试前准备"""
        self.config = VisionConfig.from_yaml(VISION_CONFIG_YAML)
        self.pipeline = VisionPipeline(self.config)
        
    def test_parse_size(self):
        """测试大小解析函数"""
        self.assertEqual(parse_size("20MB"), 20 * 1024 * 1024)
        self.assertEqual(parse_size("5KB"), 5 * 1024)
        self.assertEqual(parse_size("1GB"), 1024 * 1024 * 1024)
        self.assertEqual(parse_size("1024"), 1024)
    
    def test_vision_model_config(self):
        """测试视觉模型配置"""
        gpt4_config = self.config.vision_models["gpt-4-vision"]
        
        self.assertEqual(gpt4_config.provider, "openai")
        self.assertEqual(gpt4_config.model_name, "gpt-4-vision-preview")
        self.assertIn("vision", gpt4_config.capabilities)
        
        # 测试图像处理能力检查
        self.assertTrue(gpt4_config.can_handle_image(10 * 1024 * 1024, "png"))  # 10MB PNG
        self.assertFalse(gpt4_config.can_handle_image(30 * 1024 * 1024, "png"))  # 30MB PNG太大
        self.assertFalse(gpt4_config.can_handle_image(10 * 1024 * 1024, "bmp"))  # BMP格式不支持
    
    def test_image_info(self):
        """测试图像信息类"""
        test_data = b"fake_image_data"
        image_info = ImageInfo(data=test_data, format="png", filename="test.png")
        
        self.assertEqual(image_info.data, test_data)
        self.assertEqual(image_info.format, "png")
        self.assertEqual(image_info.filename, "test.png")
        self.assertEqual(image_info.size_bytes, len(test_data))
    
    async def test_format_converter(self):
        """测试格式转换器"""
        # 注意: 这需要实际的图像数据，我们创建简单的测试图像
        image = Image.new("RGB", (100, 100), color=(255, 0, 0))
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="PNG")
        png_data = output_buffer.getvalue()
        
        converter = FormatConverter(supported_formats=["jpeg", "jpg"], target_format="jpeg")
        
        # 测试PNG转JPEG
        jpeg_data = await converter.process(png_data, "png")
        self.assertGreater(len(jpeg_data), 0)
        
        # 测试已经是支持格式的情况
        jpeg_data2 = await converter.process(jpeg_data, "jpeg")
        self.assertEqual(jpeg_data, jpeg_data2)  # 应该返回原数据
    
    async def test_size_resizer(self):
        """测试大小调整器"""
        # 创建一个大图像
        image = Image.new("RGB", (2000, 2000), color=(0, 0, 255))
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="JPEG", quality=95)
        large_data = output_buffer.getvalue()
        
        # 设置较小的最大尺寸
        resizer = SizeResizer(max_size_bytes=10 * 1024)  # 10KB
        
        resized_data = await resizer.process(large_data, "jpeg")
        self.assertLessEqual(len(resized_data), 10 * 1024)  # 应该小于等于10KB


# ============================================================================
# 9. 命令行接口
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="视觉能力支持演示")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    parser.add_argument("--test", action="store_true", help="运行单元测试")
    parser.add_argument("--config", type=str, help="YAML配置文件路径")
    
    args = parser.parse_args()
    
    if args.demo:
        asyncio.run(main())
    elif args.test:
        # 运行单元测试
        import sys
        unittest.main(argv=[sys.argv[0]])
    else:
        print("请使用 --demo 运行演示或 --test 运行单元测试")
        print("示例: python visual_support_demo.py --demo")