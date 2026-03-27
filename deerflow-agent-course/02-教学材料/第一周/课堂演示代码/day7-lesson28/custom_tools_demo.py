#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 7 Lesson 28: 实战：创建自定义工具

本文件演示如何从零开始创建自定义工具，包括完整的开发流程：
1. 需求分析和接口设计
2. 安全设计和错误处理  
3. 异步API调用和缓存实现
4. 工具注册和集成测试
5. 完整的测试套件和演示程序

采用四部分结构设计：
第一部分：概念与设计原则 - 定义自定义工具的核心概念和开发流程
第二部分：自定义工具实现 - 实现WeatherTool和ExchangeRateTool
第三部分：集成与工具注册 - 实现ToolRegistry和工具生命周期管理
第四部分：测试与演示 - 提供完整测试套件和演示程序

使用示例:
    python custom_tools_demo.py          # 运行基本演示
    python custom_tools_demo.py --test   # 运行测试套件
    python custom_tools_demo.py --demo   # 运行完整演示
    python custom_tools_demo.py --help   # 显示帮助信息
"""

import asyncio
import json
import time
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
import aiohttp
from dataclasses import dataclass, field, asdict
from cachetools import TTLCache, LRUCache
import logging
from logging.handlers import RotatingFileHandler
import sys
import os

# ============================================================================
# 第一部分：概念与设计原则
# ============================================================================

class ToolCategory(Enum):
    """工具分类枚举"""
    DATA_QUERY = "数据查询"      # 数据查询类工具，如天气、汇率、股票
    CALCULATION = "计算"         # 计算类工具，如数学计算、单位转换
    SYSTEM = "系统"             # 系统类工具，如文件操作、进程管理
    NETWORK = "网络"            # 网络类工具，如HTTP请求、WebSocket
    UTILITY = "实用工具"        # 实用工具类，如时间、随机数、格式化
    CUSTOM = "自定义"           # 自定义工具类别

class SecurityLevel(Enum):
    """安全等级枚举"""
    PUBLIC = "公开"            # 公开工具，无需认证
    PROTECTED = "受保护"       # 需要用户认证
    PRIVATE = "私有"          # 需要特定权限
    RESTRICTED = "受限"       # 受限访问，需要管理员批准

class CacheStrategy(Enum):
    """缓存策略枚举"""
    NONE = "无缓存"           # 不缓存结果
    TTL = "生存时间"          # 基于时间过期
    LRU = "最近最少使用"      # 基于使用频率淘汰
    LFU = "最不经常使用"      # 基于访问次数淘汰
    ADAPTIVE = "自适应"      # 根据访问模式动态调整

@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str                    # 工具名称
    description: str            # 工具描述
    version: str               # 工具版本
    author: str                # 作者
    category: ToolCategory     # 工具分类
    security_level: SecurityLevel  # 安全等级
    cache_strategy: CacheStrategy  # 缓存策略
    rate_limit: int            # 速率限制（次/分钟）
    tags: List[str] = field(default_factory=list)  # 标签
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['category'] = self.category.value
        data['security_level'] = self.security_level.value
        data['cache_strategy'] = self.cache_strategy.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

@dataclass  
class ToolParameter:
    """工具参数定义"""
    name: str                    # 参数名称
    type: str                   # 参数类型（string, number, boolean, array, object）
    description: str            # 参数描述
    required: bool = True       # 是否必需
    default: Any = None        # 默认值
    constraints: Dict = field(default_factory=dict)  # 约束条件（min, max, pattern等）
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

@dataclass
class ToolSchema:
    """工具模式定义"""
    parameters: List[ToolParameter]  # 参数列表
    returns: Dict                    # 返回类型定义
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "parameters": [p.to_dict() for p in self.parameters],
            "returns": self.returns
        }

@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool                  # 是否成功
    data: Any                     # 执行结果数据
    error: Optional[str] = None   # 错误信息（如果失败）
    execution_time: float = 0.0   # 执行时间（秒）
    cache_hit: bool = False       # 是否命中缓存
    metadata: Dict = field(default_factory=dict)  # 元数据
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time": self.execution_time,
            "cache_hit": self.cache_hit,
            "metadata": self.metadata
        }

@dataclass
class ToolExecutionStats:
    """工具执行统计"""
    total_calls: int = 0          # 总调用次数
    successful_calls: int = 0     # 成功调用次数
    failed_calls: int = 0        # 失败调用次数
    total_execution_time: float = 0.0  # 总执行时间
    cache_hits: int = 0          # 缓存命中次数
    cache_misses: int = 0        # 缓存未命中次数
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls
    
    @property
    def avg_execution_time(self) -> float:
        """平均执行时间"""
        if self.total_calls == 0:
            return 0.0
        return self.total_execution_time / self.total_calls
    
    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        total_cache_access = self.cache_hits + self.cache_misses
        if total_cache_access == 0:
            return 0.0
        return self.cache_hits / total_cache_access
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": self.success_rate,
            "total_execution_time": self.total_execution_time,
            "avg_execution_time": self.avg_execution_time,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self.cache_hit_rate
        }

# ============================================================================
# 第二部分：自定义工具实现
# ============================================================================

class BaseCustomTool(ABC):
    """自定义工具基类"""
    
    def __init__(self, metadata: ToolMetadata, schema: ToolSchema):
        """
        初始化自定义工具
        
        Args:
            metadata: 工具元数据
            schema: 工具模式定义
        """
        self.metadata = metadata
        self.schema = schema
        self.stats = ToolExecutionStats()
        self._cache = None
        self._setup_cache()
        self._setup_logging()
        
    def _setup_cache(self):
        """设置缓存"""
        if self.metadata.cache_strategy == CacheStrategy.TTL:
            self._cache = TTLCache(maxsize=100, ttl=300)  # 5分钟TTL
        elif self.metadata.cache_strategy == CacheStrategy.LRU:
            self._cache = LRUCache(maxsize=100)
        elif self.metadata.cache_strategy == CacheStrategy.LFU:
            # 简化实现，实际可使用cachetools.LFUCache
            self._cache = LRUCache(maxsize=100)  # 使用LRU近似
        elif self.metadata.cache_strategy == CacheStrategy.ADAPTIVE:
            self._cache = TTLCache(maxsize=100, ttl=300)  # 自适应简化为TTL
        else:
            self._cache = None
    
    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger(f"tool.{self.metadata.name}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _generate_cache_key(self, **kwargs) -> str:
        """生成缓存键"""
        if not self._cache:
            return None
        
        # 规范化参数：排序确保一致性
        normalized = []
        for key in sorted(kwargs.keys()):
            value = kwargs[key]
            if isinstance(value, (int, float, str, bool, type(None))):
                normalized.append(f"{key}:{value}")
            elif isinstance(value, (list, tuple)):
                normalized.append(f"{key}:{tuple(value)}")
            elif isinstance(value, dict):
                # 字典排序
                sorted_items = sorted(value.items())
                normalized.append(f"{key}:{tuple(sorted_items)}")
            else:
                # 复杂对象使用repr
                normalized.append(f"{key}:{repr(value)}")
        
        cache_key = "|".join(normalized)
        return hashlib.md5(cache_key.encode()).hexdigest()
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        start_time = time.time()
        cache_key = None
        cache_hit = False
        
        try:
            # 1. 参数验证
            self._validate_parameters(kwargs)
            
            # 2. 检查缓存
            if self._cache:
                cache_key = self._generate_cache_key(**kwargs)
                if cache_key in self._cache:
                    cached_result = self._cache[cache_key]
                    execution_time = time.time() - start_time
                    
                    # 更新统计
                    self.stats.total_calls += 1
                    self.stats.successful_calls += 1
                    self.stats.cache_hits += 1
                    self.stats.total_execution_time += execution_time
                    
                    self.logger.info(f"工具 {self.metadata.name} 缓存命中，执行时间: {execution_time:.3f}s")
                    
                    return ToolResult(
                        success=True,
                        data=cached_result,
                        execution_time=execution_time,
                        cache_hit=True,
                        metadata={
                            "tool_name": self.metadata.name,
                            "cache_key": cache_key,
                            "parameters": kwargs
                        }
                    )
                else:
                    cache_hit = False
            
            # 3. 执行工具逻辑
            result_data = await self._run(**kwargs)
            
            # 4. 更新缓存
            if self._cache and cache_key:
                self._cache[cache_key] = result_data
            
            execution_time = time.time() - start_time
            
            # 5. 更新统计
            self.stats.total_calls += 1
            self.stats.successful_calls += 1
            if cache_hit is False and self._cache:
                self.stats.cache_misses += 1
            self.stats.total_execution_time += execution_time
            
            self.logger.info(f"工具 {self.metadata.name} 执行成功，时间: {execution_time:.3f}s")
            
            return ToolResult(
                success=True,
                data=result_data,
                execution_time=execution_time,
                cache_hit=cache_hit,
                metadata={
                    "tool_name": self.metadata.name,
                    "cache_key": cache_key,
                    "parameters": kwargs,
                    "execution_stats": self.stats.to_dict()
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # 更新统计
            self.stats.total_calls += 1
            self.stats.failed_calls += 1
            self.stats.total_execution_time += execution_time
            
            error_msg = f"工具 {self.metadata.name} 执行失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                execution_time=execution_time,
                cache_hit=False,
                metadata={
                    "tool_name": self.metadata.name,
                    "parameters": kwargs,
                    "error_type": type(e).__name__
                }
            )
    
    def _validate_parameters(self, kwargs: Dict):
        """验证参数"""
        # 检查必需参数
        for param in self.schema.parameters:
            if param.required and param.name not in kwargs:
                raise ValueError(f"缺少必需参数: {param.name}")
        
        # 检查参数类型和约束（简化实现）
        for param_name, param_value in kwargs.items():
            param_def = next((p for p in self.schema.parameters if p.name == param_name), None)
            if param_def:
                # 类型检查（简化）
                expected_type = param_def.type
                if expected_type == "string" and not isinstance(param_value, str):
                    raise ValueError(f"参数 {param_name} 应为字符串类型")
                elif expected_type == "number" and not isinstance(param_value, (int, float)):
                    raise ValueError(f"参数 {param_name} 应为数字类型")
                # 更多类型检查...
    
    @abstractmethod
    async def _run(self, **kwargs) -> Any:
        """
        工具实际执行逻辑（子类实现）
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            Any: 执行结果
        """
        pass
    
    def get_stats(self) -> ToolExecutionStats:
        """获取执行统计"""
        return self.stats
    
    def clear_cache(self):
        """清空缓存"""
        if self._cache:
            self._cache.clear()
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.metadata.name} (v{self.metadata.version}) - {self.metadata.description}"


class WeatherTool(BaseCustomTool):
    """天气查询工具"""
    
    def __init__(self, api_key: str = None):
        # 工具元数据
        metadata = ToolMetadata(
            name="weather_query",
            description="查询城市天气信息，支持当前天气和天气预报",
            version="1.0.0",
            author="DeerFlow Team",
            category=ToolCategory.DATA_QUERY,
            security_level=SecurityLevel.PUBLIC,
            cache_strategy=CacheStrategy.TTL,
            rate_limit=60,
            tags=["天气", "查询", "API", "数据"]
        )
        
        # 工具模式定义
        schema = ToolSchema(
            parameters=[
                ToolParameter(
                    name="city",
                    type="string",
                    description="城市名称（中文或英文）",
                    required=True
                ),
                ToolParameter(
                    name="days",
                    type="number",
                    description="预报天数（1-7），默认为1（当前天气）",
                    required=False,
                    default=1,
                    constraints={"min": 1, "max": 7}
                ),
                ToolParameter(
                    name="units",
                    type="string",
                    description="温度单位：metric（摄氏度）或 imperial（华氏度）",
                    required=False,
                    default="metric",
                    constraints={"enum": ["metric", "imperial"]}
                )
            ],
            returns={
                "type": "object",
                "description": "天气信息",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                    "current": {"type": "object", "description": "当前天气"},
                    "forecast": {"type": "array", "description": "天气预报"},
                    "timestamp": {"type": "string", "description": "数据更新时间"}
                }
            }
        )
        
        super().__init__(metadata, schema)
        self.api_key = api_key or os.getenv("WEATHER_API_KEY", "demo_key")
        self.base_url = "http://api.weatherapi.com/v1"
    
    async def _run(self, **kwargs) -> Dict:
        """执行天气查询"""
        city = kwargs["city"]
        days = kwargs.get("days", 1)
        units = kwargs.get("units", "metric")
        
        # 构建API URL
        if self.api_key == "demo_key":
            # 演示模式：返回模拟数据
            return self._get_mock_weather(city, days, units)
        
        # 实际API调用
        url = f"{self.base_url}/forecast.json"
        params = {
            "key": self.api_key,
            "q": city,
            "days": days,
            "aqi": "no",
            "alerts": "no"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_weather_data(data, city, days, units)
                    else:
                        error_text = await response.text()
                        raise Exception(f"天气API错误: {response.status} - {error_text}")
            except aiohttp.ClientError as e:
                raise Exception(f"网络错误: {str(e)}")
    
    def _get_mock_weather(self, city: str, days: int, units: str) -> Dict:
        """获取模拟天气数据（用于演示）"""
        import random
        
        # 温度单位转换
        temp_unit = "°C" if units == "metric" else "°F"
        
        # 生成当前天气
        current_temp = random.randint(15, 30) if units == "metric" else random.randint(59, 86)
        feels_like = current_temp + random.randint(-2, 2)
        
        current_weather = {
            "temp": current_temp,
            "feels_like": feels_like,
            "condition": random.choice(["晴朗", "多云", "局部多云", "小雨", "阵雨"]),
            "humidity": random.randint(40, 90),
            "wind_speed": random.randint(5, 25),
            "wind_dir": random.choice(["北", "东北", "东", "东南", "南", "西南", "西", "西北"]),
            "pressure": random.randint(1000, 1020),
            "visibility": random.randint(5, 20),
            "uv_index": random.randint(0, 10),
            "last_updated": datetime.now().isoformat()
        }
        
        # 生成天气预报
        forecast = []
        for i in range(days):
            date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            day_temp = current_temp + random.randint(-3, 3)
            night_temp = day_temp - random.randint(5, 10)
            
            forecast.append({
                "date": date,
                "day": {
                    "temp": day_temp,
                    "condition": random.choice(["晴朗", "多云", "局部多云", "小雨"]),
                    "humidity": random.randint(40, 80),
                    "wind_speed": random.randint(5, 20)
                },
                "night": {
                    "temp": night_temp,
                    "condition": random.choice(["晴朗", "多云", "局部多云"]),
                    "humidity": random.randint(50, 90),
                    "wind_speed": random.randint(3, 15)
                }
            })
        
        return {
            "city": city,
            "current": current_weather,
            "forecast": forecast,
            "units": units,
            "temp_unit": temp_unit,
            "timestamp": datetime.now().isoformat(),
            "source": "mock_data"
        }
    
    def _format_weather_data(self, data: Dict, city: str, days: int, units: str) -> Dict:
        """格式化天气数据"""
        current = data.get("current", {})
        forecast_days = data.get("forecast", {}).get("forecastday", [])
        
        # 提取当前天气
        current_weather = {
            "temp": current.get("temp_c") if units == "metric" else current.get("temp_f"),
            "feels_like": current.get("feelslike_c") if units == "metric" else current.get("feelslike_f"),
            "condition": current.get("condition", {}).get("text", "未知"),
            "humidity": current.get("humidity"),
            "wind_speed": current.get("wind_kph") if units == "metric" else current.get("wind_mph"),
            "wind_dir": current.get("wind_dir"),
            "pressure": current.get("pressure_mb"),
            "visibility": current.get("vis_km") if units == "metric" else current.get("vis_miles"),
            "uv_index": current.get("uv"),
            "last_updated": current.get("last_updated")
        }
        
        # 提取天气预报
        forecast = []
        for day_data in forecast_days[:days]:
            day = day_data.get("day", {})
            astro = day_data.get("astro", {})
            
            forecast.append({
                "date": day_data.get("date"),
                "day": {
                    "temp": day.get("avgtemp_c") if units == "metric" else day.get("avgtemp_f"),
                    "condition": day.get("condition", {}).get("text", "未知"),
                    "humidity": day.get("avghumidity"),
                    "wind_speed": day.get("maxwind_kph") if units == "metric" else day.get("maxwind_mph")
                },
                "night": {
                    "condition": "晴朗"  # 简化处理
                },
                "sunrise": astro.get("sunrise"),
                "sunset": astro.get("sunset")
            })
        
        return {
            "city": city,
            "current": current_weather,
            "forecast": forecast,
            "units": units,
            "temp_unit": "°C" if units == "metric" else "°F",
            "timestamp": datetime.now().isoformat(),
            "source": "weatherapi.com"
        }


class ExchangeRateTool(BaseCustomTool):
    """汇率查询工具"""
    
    def __init__(self, api_key: str = None):
        # 工具元数据
        metadata = ToolMetadata(
            name="exchange_rate",
            description="查询货币汇率，支持实时汇率和历史汇率",
            version="1.0.0",
            author="DeerFlow Team",
            category=ToolCategory.DATA_QUERY,
            security_level=SecurityLevel.PUBLIC,
            cache_strategy=CacheStrategy.TTL,
            rate_limit=100,
            tags=["汇率", "货币", "金融", "API"]
        )
        
        # 工具模式定义
        schema = ToolSchema(
            parameters=[
                ToolParameter(
                    name="from_currency",
                    type="string",
                    description="源货币代码（如USD, CNY, EUR）",
                    required=True,
                    constraints={"pattern": "^[A-Z]{3}$"}
                ),
                ToolParameter(
                    name="to_currency",
                    type="string",
                    description="目标货币代码（如USD, CNY, EUR）",
                    required=True,
                    constraints={"pattern": "^[A-Z]{3}$"}
                ),
                ToolParameter(
                    name="amount",
                    type="number",
                    description="金额，默认为1",
                    required=False,
                    default=1.0,
                    constraints={"min": 0}
                ),
                ToolParameter(
                    name="date",
                    type="string",
                    description="历史汇率日期（YYYY-MM-DD），默认为当天",
                    required=False
                )
            ],
            returns={
                "type": "object",
                "description": "汇率信息",
                "properties": {
                    "from_currency": {"type": "string", "description": "源货币"},
                    "to_currency": {"type": "string", "description": "目标货币"},
                    "rate": {"type": "number", "description": "汇率"},
                    "amount": {"type": "number", "description": "金额"},
                    "converted": {"type": "number", "description": "转换后金额"},
                    "timestamp": {"type": "string", "description": "汇率更新时间"}
                }
            }
        )
        
        super().__init__(metadata, schema)
        self.api_key = api_key or os.getenv("EXCHANGE_RATE_API_KEY", "demo_key")
        self.base_url = "https://api.exchangerate-api.com/v4"
    
    async def _run(self, **kwargs) -> Dict:
        """执行汇率查询"""
        from_currency = kwargs["from_currency"].upper()
        to_currency = kwargs["to_currency"].upper()
        amount = kwargs.get("amount", 1.0)
        date = kwargs.get("date")
        
        if from_currency == to_currency:
            return {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "rate": 1.0,
                "amount": amount,
                "converted": amount,
                "timestamp": datetime.now().isoformat(),
                "source": "same_currency"
            }
        
        # 演示模式：返回模拟数据
        if self.api_key == "demo_key":
            return self._get_mock_exchange_rate(from_currency, to_currency, amount, date)
        
        # 实际API调用
        if date:
            # 历史汇率
            url = f"{self.base_url}/historical/{date}.json"
        else:
            # 实时汇率
            url = f"{self.base_url}/latest/{from_currency}"
        
        params = {"base": from_currency}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_exchange_data(data, from_currency, to_currency, amount, date)
                    else:
                        error_text = await response.text()
                        raise Exception(f"汇率API错误: {response.status} - {error_text}")
            except aiohttp.ClientError as e:
                raise Exception(f"网络错误: {str(e)}")
    
    def _get_mock_exchange_rate(self, from_currency: str, to_currency: str, amount: float, date: str = None) -> Dict:
        """获取模拟汇率数据（用于演示）"""
        import random
        
        # 常见货币汇率（模拟数据）
        rates = {
            "USD": {"CNY": 7.25, "EUR": 0.92, "JPY": 150.0, "GBP": 0.79},
            "CNY": {"USD": 0.14, "EUR": 0.13, "JPY": 20.7, "GBP": 0.11},
            "EUR": {"USD": 1.09, "CNY": 7.85, "JPY": 163.0, "GBP": 0.86},
            "JPY": {"USD": 0.0067, "CNY": 0.048, "EUR": 0.0061, "GBP": 0.0053},
            "GBP": {"USD": 1.27, "CNY": 9.1, "EUR": 1.16, "JPY": 189.0}
        }
        
        # 获取汇率
        if from_currency in rates and to_currency in rates[from_currency]:
            rate = rates[from_currency][to_currency]
        elif to_currency in rates and from_currency in rates[to_currency]:
            # 计算反向汇率
            rate = 1.0 / rates[to_currency][from_currency]
        else:
            # 随机生成汇率
            rate = random.uniform(0.5, 2.0)
        
        # 添加小幅随机波动
        rate *= random.uniform(0.99, 1.01)
        
        converted = amount * rate
        
        return {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": round(rate, 4),
            "amount": amount,
            "converted": round(converted, 4),
            "timestamp": datetime.now().isoformat(),
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "source": "mock_data"
        }
    
    def _format_exchange_data(self, data: Dict, from_currency: str, to_currency: str, amount: float, date: str = None) -> Dict:
        """格式化汇率数据"""
        rates = data.get("rates", {})
        
        if to_currency not in rates:
            # 尝试通过USD中转计算
            if "USD" in rates and from_currency != "USD":
                # 先计算到USD，再到目标货币
                usd_rate = rates.get("USD")
                if usd_rate and to_currency in rates:
                    rate = (1.0 / usd_rate) * rates[to_currency]
                else:
                    raise Exception(f"不支持货币对: {from_currency}/{to_currency}")
            else:
                raise Exception(f"不支持货币对: {from_currency}/{to_currency}")
        else:
            rate = rates[to_currency]
        
        converted = amount * rate
        
        return {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "rate": rate,
            "amount": amount,
            "converted": converted,
            "timestamp": data.get("date", datetime.now().isoformat()),
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "source": "exchangerate-api.com"
        }

# ============================================================================
# 第三部分：集成与工具注册
# ============================================================================

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, BaseCustomTool] = {}
        self._tool_categories: Dict[ToolCategory, List[str]] = {}
        self._stats = ToolExecutionStats()
        self._lock = asyncio.Lock()
    
    async def register_tool(self, tool: BaseCustomTool) -> bool:
        """
        注册工具
        
        Args:
            tool: 要注册的工具
            
        Returns:
            bool: 是否注册成功
        """
        async with self._lock:
            tool_name = tool.metadata.name
            
            if tool_name in self._tools:
                self.logger.warning(f"工具 {tool_name} 已存在，跳过注册")
                return False
            
            self._tools[tool_name] = tool
            
            # 按分类组织
            category = tool.metadata.category
            if category not in self._tool_categories:
                self._tool_categories[category] = []
            
            if tool_name not in self._tool_categories[category]:
                self._tool_categories[category].append(tool_name)
            
            self.logger.info(f"工具 {tool_name} 注册成功")
            return True
    
    async def unregister_tool(self, tool_name: str) -> bool:
        """
        注销工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 是否注销成功
        """
        async with self._lock:
            if tool_name not in self._tools:
                return False
            
            tool = self._tools[tool_name]
            category = tool.metadata.category
            
            # 从分类中移除
            if category in self._tool_categories and tool_name in self._tool_categories[category]:
                self._tool_categories[category].remove(tool_name)
                if not self._tool_categories[category]:
                    del self._tool_categories[category]
            
            # 从工具字典中移除
            del self._tools[tool_name]
            
            self.logger.info(f"工具 {tool_name} 注销成功")
            return True
    
    async def get_tool(self, tool_name: str) -> Optional[BaseCustomTool]:
        """
        获取工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Optional[BaseCustomTool]: 工具实例，如果不存在则返回None
        """
        return self._tools.get(tool_name)
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 执行结果
        """
        start_time = time.time()
        
        tool = await self.get_tool(tool_name)
        if not tool:
            execution_time = time.time() - start_time
            self._stats.total_calls += 1
            self._stats.failed_calls += 1
            self._stats.total_execution_time += execution_time
            
            return ToolResult(
                success=False,
                data=None,
                error=f"工具 {tool_name} 未找到",
                execution_time=execution_time,
                metadata={"tool_name": tool_name}
            )
        
        # 执行工具
        result = await tool.execute(**kwargs)
        
        # 更新注册表统计
        self._stats.total_calls += 1
        if result.success:
            self._stats.successful_calls += 1
        else:
            self._stats.failed_calls += 1
        
        self._stats.total_execution_time += result.execution_time
        
        if result.cache_hit:
            self._stats.cache_hits += 1
        elif tool.metadata.cache_strategy != CacheStrategy.NONE:
            self._stats.cache_misses += 1
        
        return result
    
    async def list_tools(self, category: ToolCategory = None) -> List[Dict]:
        """
        列出工具
        
        Args:
            category: 工具分类，如果为None则列出所有工具
            
        Returns:
            List[Dict]: 工具信息列表
        """
        if category:
            tool_names = self._tool_categories.get(category, [])
            tools = [self._tools[name] for name in tool_names if name in self._tools]
        else:
            tools = list(self._tools.values())
        
        return [
            {
                "name": tool.metadata.name,
                "description": tool.metadata.description,
                "category": tool.metadata.category.value,
                "version": tool.metadata.version,
                "author": tool.metadata.author,
                "stats": tool.get_stats().to_dict()
            }
            for tool in tools
        ]
    
    async def get_tool_info(self, tool_name: str) -> Optional[Dict]:
        """
        获取工具详细信息
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Optional[Dict]: 工具详细信息
        """
        tool = await self.get_tool(tool_name)
        if not tool:
            return None
        
        return {
            "metadata": tool.metadata.to_dict(),
            "schema": tool.schema.to_dict(),
            "stats": tool.get_stats().to_dict()
        }
    
    def get_registry_stats(self) -> ToolExecutionStats:
        """获取注册表统计"""
        return self._stats
    
    def clear_all_caches(self):
        """清空所有工具缓存"""
        for tool in self._tools.values():
            tool.clear_cache()
        
        self.logger.info("所有工具缓存已清空")
    
    @property
    def logger(self):
        """获取日志器"""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger("tool.registry")
            if not self._logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self._logger.addHandler(handler)
                self._logger.setLevel(logging.INFO)
        return self._logger

# ============================================================================
# 第四部分：测试与演示
# ============================================================================

class CustomToolsTestSuite:
    """自定义工具测试套件"""
    
    def __init__(self):
        self.test_results = []
    
    async def test_weather_tool_basic(self) -> Dict:
        """测试天气工具基本功能"""
        test_name = "weather_tool_basic"
        start_time = time.time()
        
        try:
            tool = WeatherTool()
            
            # 测试当前天气查询
            result = await tool.execute(city="北京", days=1)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            if result.success:
                data = result.data
                assert "city" in data
                assert "current" in data
                assert "timestamp" in data
                
                self.test_results.append({
                    "test_name": test_name,
                    "passed": True,
                    "execution_time": execution_time,
                    "details": "天气工具基本功能测试通过"
                })
                
                return {
                    "passed": True,
                    "execution_time": execution_time,
                    "data_sample": {
                        "city": data["city"],
                        "temp": data["current"].get("temp"),
                        "condition": data["current"].get("condition")
                    }
                }
            else:
                self.test_results.append({
                    "test_name": test_name,
                    "passed": False,
                    "execution_time": execution_time,
                    "error": result.error
                })
                
                return {
                    "passed": False,
                    "execution_time": execution_time,
                    "error": result.error
                }
                
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results.append({
                "test_name": test_name,
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            })
            
            return {
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            }
    
    async def test_weather_tool_forecast(self) -> Dict:
        """测试天气工具天气预报功能"""
        test_name = "weather_tool_forecast"
        start_time = time.time()
        
        try:
            tool = WeatherTool()
            
            # 测试天气预报查询
            result = await tool.execute(city="上海", days=3, units="metric")
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            if result.success:
                data = result.data
                assert "forecast" in data
                assert len(data["forecast"]) == 3
                
                self.test_results.append({
                    "test_name": test_name,
                    "passed": True,
                    "execution_time": execution_time,
                    "details": "天气工具天气预报功能测试通过"
                })
                
                return {
                    "passed": True,
                    "execution_time": execution_time,
                    "forecast_days": len(data["forecast"])
                }
            else:
                self.test_results.append({
                    "test_name": test_name,
                    "passed": False,
                    "execution_time": execution_time,
                    "error": result.error
                })
                
                return {
                    "passed": False,
                    "execution_time": execution_time,
                    "error": result.error
                }
                
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results.append({
                "test_name": test_name,
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            })
            
            return {
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            }
    
    async def test_exchange_rate_tool_basic(self) -> Dict:
        """测试汇率工具基本功能"""
        test_name = "exchange_rate_tool_basic"
        start_time = time.time()
        
        try:
            tool = ExchangeRateTool()
            
            # 测试汇率查询
            result = await tool.execute(from_currency="USD", to_currency="CNY", amount=100)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            if result.success:
                data = result.data
                assert "from_currency" in data
                assert "to_currency" in data
                assert "rate" in data
                assert "converted" in data
                
                # 验证计算正确性
                expected_converted = data["amount"] * data["rate"]
                assert abs(data["converted"] - expected_converted) < 0.01
                
                self.test_results.append({
                    "test_name": test_name,
                    "passed": True,
                    "execution_time": execution_time,
                    "details": "汇率工具基本功能测试通过"
                })
                
                return {
                    "passed": True,
                    "execution_time": execution_time,
                    "data_sample": {
                        "from": data["from_currency"],
                        "to": data["to_currency"],
                        "rate": data["rate"],
                        "converted": data["converted"]
                    }
                }
            else:
                self.test_results.append({
                    "test_name": test_name,
                    "passed": False,
                    "execution_time": execution_time,
                    "error": result.error
                })
                
                return {
                    "passed": False,
                    "execution_time": execution_time,
                    "error": result.error
                }
                
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results.append({
                "test_name": test_name,
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            })
            
            return {
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            }
    
    async def test_exchange_rate_tool_same_currency(self) -> Dict:
        """测试汇率工具相同货币"""
        test_name = "exchange_rate_tool_same_currency"
        start_time = time.time()
        
        try:
            tool = ExchangeRateTool()
            
            # 测试相同货币查询
            result = await tool.execute(from_currency="USD", to_currency="USD", amount=100)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            if result.success:
                data = result.data
                assert data["rate"] == 1.0
                assert data["converted"] == data["amount"]
                
                self.test_results.append({
                    "test_name": test_name,
                    "passed": True,
                    "execution_time": execution_time,
                    "details": "汇率工具相同货币测试通过"
                })
                
                return {
                    "passed": True,
                    "execution_time": execution_time,
                    "rate": data["rate"],
                    "converted": data["converted"]
                }
            else:
                self.test_results.append({
                    "test_name": test_name,
                    "passed": False,
                    "execution_time": execution_time,
                    "error": result.error
                })
                
                return {
                    "passed": False,
                    "execution_time": execution_time,
                    "error": result.error
                }
                
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results.append({
                "test_name": test_name,
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            })
            
            return {
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            }
    
    async def test_tool_registry(self) -> Dict:
        """测试工具注册表"""
        test_name = "tool_registry"
        start_time = time.time()
        
        try:
            registry = ToolRegistry()
            
            # 创建并注册工具
            weather_tool = WeatherTool()
            exchange_tool = ExchangeRateTool()
            
            await registry.register_tool(weather_tool)
            await registry.register_tool(exchange_tool)
            
            # 列出工具
            tools_list = await registry.list_tools()
            assert len(tools_list) == 2
            
            # 执行工具
            result = await registry.execute_tool("weather_query", city="广州", days=1)
            assert result.success
            
            # 获取工具信息
            tool_info = await registry.get_tool_info("exchange_rate")
            assert tool_info is not None
            assert tool_info["metadata"]["name"] == "exchange_rate"
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results.append({
                "test_name": test_name,
                "passed": True,
                "execution_time": execution_time,
                "details": "工具注册表测试通过"
            })
            
            return {
                "passed": True,
                "execution_time": execution_time,
                "tools_registered": len(tools_list)
            }
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results.append({
                "test_name": test_name,
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            })
            
            return {
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            }
    
    async def test_tool_cache(self) -> Dict:
        """测试工具缓存功能"""
        test_name = "tool_cache"
        start_time = time.time()
        
        try:
            tool = WeatherTool()
            
            # 第一次查询（应该未命中缓存）
            result1 = await tool.execute(city="深圳", days=1)
            assert result1.success
            assert not result1.cache_hit
            
            # 第二次查询相同参数（应该命中缓存）
            result2 = await tool.execute(city="深圳", days=1)
            assert result2.success
            assert result2.cache_hit
            
            # 第三次查询不同参数（应该未命中缓存）
            result3 = await tool.execute(city="深圳", days=2)
            assert result3.success
            assert not result3.cache_hit
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results.append({
                "test_name": test_name,
                "passed": True,
                "execution_time": execution_time,
                "details": "工具缓存功能测试通过"
            })
            
            return {
                "passed": True,
                "execution_time": execution_time,
                "cache_tests": {
                    "first_call_cache_hit": result1.cache_hit,
                    "second_call_cache_hit": result2.cache_hit,
                    "third_call_cache_hit": result3.cache_hit
                }
            }
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results.append({
                "test_name": test_name,
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            })
            
            return {
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            }
    
    async def test_error_handling(self) -> Dict:
        """测试错误处理"""
        test_name = "error_handling"
        start_time = time.time()
        
        try:
            registry = ToolRegistry()
            
            # 测试执行不存在的工具
            result = await registry.execute_tool("non_existent_tool", param="test")
            assert not result.success
            assert "未找到" in result.error
            
            # 测试天气工具参数错误
            weather_tool = WeatherTool()
            result = await weather_tool.execute()  # 缺少必需参数
            assert not result.success
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results.append({
                "test_name": test_name,
                "passed": True,
                "execution_time": execution_time,
                "details": "错误处理测试通过"
            })
            
            return {
                "passed": True,
                "execution_time": execution_time,
                "error_tests": 2
            }
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            self.test_results.append({
                "test_name": test_name,
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            })
            
            return {
                "passed": False,
                "execution_time": execution_time,
                "error": str(e)
            }
    
    async def run_all_tests(self) -> Dict:
        """运行所有测试"""
        print("=" * 80)
        print("🧪 自定义工具测试套件")
        print("=" * 80)
        
        test_methods = [
            self.test_weather_tool_basic,
            self.test_weather_tool_forecast,
            self.test_exchange_rate_tool_basic,
            self.test_exchange_rate_tool_same_currency,
            self.test_tool_registry,
            self.test_tool_cache,
            self.test_error_handling
        ]
        
        test_results = []
        passed_tests = 0
        failed_tests = 0
        
        for test_method in test_methods:
            test_name = test_method.__name__
            print(f"\n📋 运行测试: {test_name}")
            
            result = await test_method()
            test_results.append({
                "test_name": test_name,
                "result": result
            })
            
            if result.get("passed", False):
                print(f"  ✅ 通过 ({result['execution_time']:.3f}s)")
                passed_tests += 1
            else:
                print(f"  ❌ 失败 ({result['execution_time']:.3f}s): {result.get('error', 'Unknown error')}")
                failed_tests += 1
        
        total_tests = len(test_methods)
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        print("\n" + "=" * 80)
        print("📊 测试结果摘要")
        print("=" * 80)
        print(f"测试总数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {failed_tests}")
        print(f"成功率: {success_rate:.1%}")
        
        if failed_tests == 0:
            print("\n🎉 所有测试通过！")
        else:
            print(f"\n⚠️  {failed_tests} 个测试失败，需要检查")
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate
            },
            "detailed_results": {
                tr["test_name"]: tr["result"] for tr in test_results
            }
        }


async def main_demo():
    """主演示函数"""
    print("=" * 80)
    print("🎓 Day 7 Lesson 28: 实战：创建自定义工具演示")
    print("=" * 80)
    
    # 1. 创建工具实例
    print("\n1. 创建自定义工具实例...")
    weather_tool = WeatherTool()
    exchange_tool = ExchangeRateTool()
    
    print(f"   ✅ 创建天气查询工具: {weather_tool}")
    print(f"   ✅ 创建汇率查询工具: {exchange_tool}")
    
    # 2. 测试天气工具
    print("\n2. 测试天气查询工具...")
    print("   查询北京当前天气:")
    result = await weather_tool.execute(city="北京", days=1)
    
    if result.success:
        data = result.data
        print(f"     城市: {data['city']}")
        print(f"     温度: {data['current'].get('temp')}{data.get('temp_unit', '°C')}")
        print(f"     天气: {data['current'].get('condition')}")
        print(f"     湿度: {data['current'].get('humidity')}%")
        print(f"     执行时间: {result.execution_time:.3f}s")
        print(f"     缓存命中: {result.cache_hit}")
    else:
        print(f"     ❌ 查询失败: {result.error}")
    
    # 3. 测试汇率工具
    print("\n3. 测试汇率查询工具...")
    print("   查询100 USD到CNY的汇率:")
    result = await exchange_tool.execute(from_currency="USD", to_currency="CNY", amount=100)
    
    if result.success:
        data = result.data
        print(f"     汇率: 1 {data['from_currency']} = {data['rate']} {data['to_currency']}")
        print(f"     转换: {data['amount']} {data['from_currency']} = {data['converted']} {data['to_currency']}")
        print(f"     执行时间: {result.execution_time:.3f}s")
        print(f"     缓存命中: {result.cache_hit}")
    else:
        print(f"     ❌ 查询失败: {result.error}")
    
    # 4. 测试工具注册表
    print("\n4. 测试工具注册表...")
    registry = ToolRegistry()
    
    await registry.register_tool(weather_tool)
    await registry.register_tool(exchange_tool)
    
    tools_list = await registry.list_tools()
    print(f"   已注册工具: {len(tools_list)}个")
    for tool_info in tools_list:
        print(f"     - {tool_info['name']}: {tool_info['description']}")
    
    # 5. 测试缓存功能
    print("\n5. 测试缓存功能...")
    print("   第一次查询上海天气（缓存未命中）:")
    result1 = await weather_tool.execute(city="上海", days=1)
    print(f"     执行时间: {result1.execution_time:.3f}s, 缓存命中: {result1.cache_hit}")
    
    print("   第二次查询上海天气（缓存命中）:")
    result2 = await weather_tool.execute(city="上海", days=1)
    print(f"     执行时间: {result2.execution_time:.3f}s, 缓存命中: {result2.cache_hit}")
    
    time_saved = result1.execution_time - result2.execution_time
    print(f"     缓存节省时间: {time_saved:.3f}s")
    
    # 6. 显示工具统计
    print("\n6. 工具执行统计:")
    weather_stats = weather_tool.get_stats()
    exchange_stats = exchange_tool.get_stats()
    registry_stats = registry.get_registry_stats()
    
    print(f"   天气工具:")
    print(f"     总调用: {weather_stats.total_calls}, 成功: {weather_stats.successful_calls}")
    print(f"     平均时间: {weather_stats.avg_execution_time:.3f}s, 缓存命中率: {weather_stats.cache_hit_rate:.1%}")
    
    print(f"   汇率工具:")
    print(f"     总调用: {exchange_stats.total_calls}, 成功: {exchange_stats.successful_calls}")
    print(f"     平均时间: {exchange_stats.avg_execution_time:.3f}s, 缓存命中率: {exchange_stats.cache_hit_rate:.1%}")
    
    print(f"   注册表统计:")
    print(f"     总调用: {registry_stats.total_calls}, 成功: {registry_stats.successful_calls}")
    print(f"     成功率: {registry_stats.success_rate:.1%}")
    
    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Day 7 Lesson 28: 实战：创建自定义工具演示")
    parser.add_argument("--test", action="store_true", help="运行测试套件")
    parser.add_argument("--demo", action="store_true", help="运行完整演示")
    parser.add_argument("--list", action="store_true", help="列出所有工具")
    
    args = parser.parse_args()
    
    if args.test:
        # 运行测试套件
        test_suite = CustomToolsTestSuite()
        asyncio.run(test_suite.run_all_tests())
    elif args.demo:
        # 运行完整演示
        asyncio.run(main_demo())
    elif args.list:
        # 列出工具信息
        print("Day 7 Lesson 28: 实战：创建自定义工具")
        print("=" * 50)
        print("可用工具类:")
        print("1. WeatherTool - 天气查询工具")
        print("2. ExchangeRateTool - 汇率查询工具")
        print("3. ToolRegistry - 工具注册表")
        print("4. CustomToolsTestSuite - 测试套件")
        print("\n使用示例:")
        print("  python custom_tools_demo.py --demo   # 运行完整演示")
        print("  python custom_tools_demo.py --test   # 运行测试套件")
    else:
        # 默认运行基本演示
        print("Day 7 Lesson 28: 实战：创建自定义工具")
        print("=" * 50)
        print("使用 --help 查看可用选项")
        print("\n快速开始:")
        print("1. 创建工具实例:")
        print("   weather_tool = WeatherTool()")
        print("   exchange_tool = ExchangeRateTool()")
        print("\n2. 执行工具:")
        print("   result = await weather_tool.execute(city='北京', days=3)")
        print("   if result.success:")
        print("       print(result.data)")
        print("\n3. 使用工具注册表:")
        print("   registry = ToolRegistry()")
        print("   await registry.register_tool(weather_tool)")
        print("   result = await registry.execute_tool('weather_query', city='上海')")
        print("\n运行完整演示: python custom_tools_demo.py --demo")


if __name__ == "__main__":
    main()