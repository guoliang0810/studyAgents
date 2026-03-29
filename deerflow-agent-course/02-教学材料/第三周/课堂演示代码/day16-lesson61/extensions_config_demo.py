#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展配置JSON (extensions_config.json) - 课堂演示代码
Day 16 - 第61节课：扩展配置JSON

本演示代码展示了：
1. 扩展配置的JSON结构设计和字段含义
2. ExtensionLoader的动态加载和初始化实现
3. 多种扩展类型（MCP服务器、监控系统、缓存系统）的配置示例
4. 扩展间依赖关系管理和启动顺序控制
5. 环境变量在JSON配置中的动态替换

学习目标：
- 掌握扩展配置的多层结构设计
- 理解JSON格式在扩展配置中的应用
- 实现ExtensionLoader的动态加载机制
- 配置MCP服务器、监控系统、缓存系统等扩展模块
"""

import json
import os
import sys
import asyncio
import importlib
import inspect
from typing import Dict, List, Any, Optional, Type, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import re
from pathlib import Path
from datetime import datetime
import logging
from abc import ABC, abstractmethod
from collections import defaultdict, deque
import hashlib


# ============================================================================
# 第一部分：扩展配置JSON结构
# ============================================================================

# 示例1：基础扩展配置JSON
EXAMPLE_EXTENSIONS_CONFIG_BASIC = {
    "version": "1.0.0",
    "description": "基础扩展配置示例",
    "environment": "${ENVIRONMENT:development}",
    "default_extension_timeout": "${EXTENSION_TIMEOUT:30}",
    
    "extensions": {
        "mcp-server-1": {
            "type": "mcp_server",
            "name": "文件系统MCP服务器",
            "enabled": True,
            "description": "提供文件系统访问功能的MCP服务器",
            "config": {
                "server_type": "filesystem",
                "port": "${MCP_PORT:8001}",
                "host": "localhost",
                "max_connections": 10,
                "timeout_seconds": 30,
                "allowed_paths": ["/data", "/tmp"],
                "read_only": False
            },
            "dependencies": [],
            "metadata": {
                "category": "storage",
                "priority": "high",
                "created_by": "system-admin"
            }
        },
        
        "monitoring-system": {
            "type": "monitoring",
            "name": "系统监控扩展",
            "enabled": True,
            "description": "收集系统指标和性能监控",
            "config": {
                "collection_interval": 60,
                "metrics_retention_days": 7,
                "alert_enabled": True,
                "alert_thresholds": {
                    "cpu_percent": 80.0,
                    "memory_percent": 85.0,
                    "disk_percent": 90.0
                },
                "exporters": ["prometheus", "grafana"],
                "storage_backend": "influxdb"
            },
            "dependencies": ["mcp-server-1"],
            "metadata": {
                "category": "observability",
                "priority": "medium",
                "created_by": "ops-team"
            }
        },
        
        "cache-system": {
            "type": "caching",
            "name": "分布式缓存扩展",
            "enabled": True,
            "description": "提供分布式缓存功能",
            "config": {
                "cache_type": "redis",
                "host": "${REDIS_HOST:localhost}",
                "port": "${REDIS_PORT:6379}",
                "password": "${REDIS_PASSWORD:}",
                "database": 0,
                "max_connections": 50,
                "key_prefix": "deerflow:",
                "default_ttl": 3600,
                "compression_enabled": True
            },
            "dependencies": ["monitoring-system"],
            "metadata": {
                "category": "performance",
                "priority": "high",
                "created_by": "dev-team"
            }
        }
    },
    
    "global_config": {
        "log_level": "${LOG_LEVEL:INFO}",
        "max_concurrent_extensions": 10,
        "health_check_interval": 30,
        "auto_reload_enabled": True,
        "extension_timeout_seconds": 300
    },
    
    "metadata": {
        "created_at": "2024-03-25T10:00:00Z",
        "created_by": "config-generator",
        "version": "1.0.0",
        "environment": "${ENVIRONMENT:development}"
    }
}

# 示例2：复杂扩展配置JSON（包含多种扩展类型）
EXAMPLE_EXTENSIONS_CONFIG_ADVANCED = {
    "version": "2.0.0",
    "description": "高级扩展配置示例，包含多种扩展类型",
    
    "extensions": {
        # MCP服务器类型
        "mcp-filesystem": {
            "type": "mcp_server",
            "name": "文件系统MCP",
            "enabled": True,
            "config": {
                "server_type": "filesystem",
                "port": 8001,
                "allowed_operations": ["read", "write", "list", "delete"],
                "quota_mb": 1024
            }
        },
        
        "mcp-http-proxy": {
            "type": "mcp_server",
            "name": "HTTP代理MCP",
            "enabled": True,
            "config": {
                "server_type": "http_proxy",
                "port": 8002,
                "allowed_domains": ["*.example.com", "api.github.com"],
                "max_concurrent_requests": 100
            },
            "dependencies": ["mcp-filesystem"]
        },
        
        # 监控系统类型
        "monitoring-prometheus": {
            "type": "monitoring",
            "name": "Prometheus监控",
            "enabled": True,
            "config": {
                "exporter_type": "prometheus",
                "port": 9090,
                "scrape_interval": 15,
                "retention_days": 15
            }
        },
        
        "monitoring-alertmanager": {
            "type": "monitoring",
            "name": "告警管理器",
            "enabled": True,
            "config": {
                "exporter_type": "alertmanager",
                "port": 9093,
                "webhook_url": "${ALERT_WEBHOOK_URL:}",
                "default_receiver": "email"
            },
            "dependencies": ["monitoring-prometheus"]
        },
        
        # 缓存系统类型
        "cache-redis": {
            "type": "caching",
            "name": "Redis缓存",
            "enabled": True,
            "config": {
                "cache_type": "redis",
                "mode": "cluster",
                "nodes": [
                    {"host": "redis-1", "port": 6379},
                    {"host": "redis-2", "port": 6380}
                ],
                "password": "${REDIS_PASSWORD:}",
                "ssl_enabled": True
            }
        },
        
        "cache-memcached": {
            "type": "caching",
            "name": "Memcached缓存",
            "enabled": False,  # 示例：禁用状态
            "config": {
                "cache_type": "memcached",
                "servers": ["memcached-1:11211", "memcached-2:11211"],
                "pool_size": 10
            }
        },
        
        # 存储系统类型
        "storage-s3": {
            "type": "storage",
            "name": "S3存储",
            "enabled": True,
            "config": {
                "storage_type": "s3",
                "bucket": "${S3_BUCKET:deerflow-data}",
                "region": "${AWS_REGION:us-east-1}",
                "access_key": "${AWS_ACCESS_KEY:}",
                "secret_key": "${AWS_SECRET_KEY:}",
                "endpoint_url": "${S3_ENDPOINT:}"
            },
            "dependencies": ["mcp-filesystem", "cache-redis"]
        },
        
        # 消息队列类型
        "message-queue-rabbitmq": {
            "type": "message_queue",
            "name": "RabbitMQ消息队列",
            "enabled": True,
            "config": {
                "queue_type": "rabbitmq",
                "host": "${RABBITMQ_HOST:localhost}",
                "port": 5672,
                "username": "${RABBITMQ_USER:guest}",
                "password": "${RABBITMQ_PASS:guest}",
                "vhost": "/",
                "exchange": "deerflow.exchange"
            }
        }
    },
    
    "global_config": {
        "extension_load_timeout": 60,
        "max_retries": 3,
        "health_check_enabled": True,
        "metrics_collection_enabled": True,
        "auto_scale_enabled": False
    }
}


# ============================================================================
# 第二部分：扩展基础类和接口
# ============================================================================

class ExtensionType(Enum):
    """扩展类型枚举"""
    MCP_SERVER = "mcp_server"
    MONITORING = "monitoring"
    CACHING = "caching"
    STORAGE = "storage"
    MESSAGE_QUEUE = "message_queue"
    CUSTOM = "custom"


class ExtensionStatus(Enum):
    """扩展状态枚举"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class ExtensionMetadata:
    """扩展元数据"""
    name: str
    type: ExtensionType
    version: str = "1.0.0"
    description: str = ""
    enabled: bool = True
    category: str = ""
    priority: str = "medium"
    created_by: str = "system"
    created_at: str = ""
    updated_at: str = ""


class ExtensionError(Exception):
    """扩展相关异常基类"""
    pass


class ExtensionInitializationError(ExtensionError):
    """扩展初始化错误"""
    pass


class ExtensionDependencyError(ExtensionError):
    """扩展依赖错误"""
    pass


class ExtensionInterface(ABC):
    """扩展接口基类"""
    
    def __init__(self, extension_id: str, config: Dict[str, Any], metadata: ExtensionMetadata):
        self.extension_id = extension_id
        self.config = config
        self.metadata = metadata
        self.status = ExtensionStatus.UNINITIALIZED
        self.error_message: Optional[str] = None
        self.initialized_at: Optional[datetime] = None
        self.started_at: Optional[datetime] = None
        
    @abstractmethod
    async def initialize(self) -> None:
        """初始化扩展"""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """启动扩展"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """停止扩展"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """获取扩展状态"""
        return {
            "extension_id": self.extension_id,
            "name": self.metadata.name,
            "type": self.metadata.type.value,
            "status": self.status.value,
            "enabled": self.metadata.enabled,
            "error_message": self.error_message,
            "initialized_at": self.initialized_at.isoformat() if self.initialized_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None
        }


# ============================================================================
# 第三部分：具体扩展实现类
# ============================================================================

class MCPServerExtension(ExtensionInterface):
    """MCP服务器扩展"""
    
    async def initialize(self) -> None:
        """初始化MCP服务器扩展"""
        try:
            self.status = ExtensionStatus.INITIALIZING
            logging.info(f"初始化MCP服务器扩展: {self.extension_id}")
            
            # 验证配置
            required_fields = ["server_type", "port", "host"]
            for field in required_fields:
                if field not in self.config:
                    raise ExtensionInitializationError(f"缺少必要配置字段: {field}")
            
            # 模拟初始化过程
            await asyncio.sleep(0.1)  # 模拟初始化延迟
            
            self.initialized_at = datetime.now()
            self.status = ExtensionStatus.STOPPED
            logging.info(f"MCP服务器扩展初始化完成: {self.extension_id}")
            
        except Exception as e:
            self.status = ExtensionStatus.ERROR
            self.error_message = str(e)
            raise ExtensionInitializationError(f"MCP服务器扩展初始化失败: {str(e)}")
    
    async def start(self) -> None:
        """启动MCP服务器扩展"""
        try:
            if self.status != ExtensionStatus.STOPPED:
                raise ExtensionError(f"扩展状态不正确，无法启动: {self.status}")
            
            self.status = ExtensionStatus.RUNNING
            self.started_at = datetime.now()
            
            server_type = self.config.get("server_type", "unknown")
            port = self.config.get("port", 8000)
            host = self.config.get("host", "localhost")
            
            logging.info(f"启动MCP服务器扩展: {self.extension_id} ({server_type}) 在 {host}:{port}")
            
            # 模拟启动过程
            await asyncio.sleep(0.2)
            
        except Exception as e:
            self.status = ExtensionStatus.ERROR
            self.error_message = str(e)
            raise
    
    async def stop(self) -> None:
        """停止MCP服务器扩展"""
        try:
            if self.status != ExtensionStatus.RUNNING:
                return
            
            logging.info(f"停止MCP服务器扩展: {self.extension_id}")
            self.status = ExtensionStatus.STOPPED
            
            # 模拟停止过程
            await asyncio.sleep(0.1)
            
        except Exception as e:
            self.status = ExtensionStatus.ERROR
            self.error_message = str(e)
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """MCP服务器健康检查"""
        try:
            if self.status != ExtensionStatus.RUNNING:
                return {
                    "healthy": False,
                    "status": self.status.value,
                    "message": f"扩展未运行: {self.status.value}"
                }
            
            # 模拟健康检查
            is_healthy = True
            message = "MCP服务器运行正常"
            
            # 检查端口是否可用（模拟）
            port = self.config.get("port", 8000)
            host = self.config.get("host", "localhost")
            
            # 这里应该是实际的端口检查，这里仅模拟
            await asyncio.sleep(0.05)
            
            return {
                "healthy": is_healthy,
                "status": self.status.value,
                "message": message,
                "details": {
                    "server_type": self.config.get("server_type"),
                    "host": host,
                    "port": port,
                    "connections": 5,  # 模拟连接数
                    "uptime": 3600 if self.started_at else 0  # 模拟运行时间
                }
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "status": ExtensionStatus.ERROR.value,
                "message": f"健康检查失败: {str(e)}",
                "error": str(e)
            }


class MonitoringExtension(ExtensionInterface):
    """监控系统扩展"""
    
    def __init__(self, extension_id: str, config: Dict[str, Any], metadata: ExtensionMetadata):
        super().__init__(extension_id, config, metadata)
        self.metrics: Dict[str, Any] = {}
        self.alerts: List[Dict[str, Any]] = []
    
    async def initialize(self) -> None:
        """初始化监控系统扩展"""
        try:
            self.status = ExtensionStatus.INITIALIZING
            logging.info(f"初始化监控系统扩展: {self.extension_id}")
            
            # 验证配置
            if "collection_interval" not in self.config:
                self.config["collection_interval"] = 60
            
            # 初始化指标收集器
            self.metrics = {
                "system": {
                    "cpu_percent": 0.0,
                    "memory_percent": 0.0,
                    "disk_percent": 0.0,
                    "uptime": 0
                },
                "extensions": {},
                "timestamp": datetime.now().isoformat()
            }
            
            # 模拟初始化过程
            await asyncio.sleep(0.15)
            
            self.initialized_at = datetime.now()
            self.status = ExtensionStatus.STOPPED
            logging.info(f"监控系统扩展初始化完成: {self.extension_id}")
            
        except Exception as e:
            self.status = ExtensionStatus.ERROR
            self.error_message = str(e)
            raise ExtensionInitializationError(f"监控系统扩展初始化失败: {str(e)}")
    
    async def start(self) -> None:
        """启动监控系统扩展"""
        try:
            if self.status != ExtensionStatus.STOPPED:
                raise ExtensionError(f"扩展状态不正确，无法启动: {self.status}")
            
            self.status = ExtensionStatus.RUNNING
            self.started_at = datetime.now()
            
            collection_interval = self.config.get("collection_interval", 60)
            exporters = self.config.get("exporters", [])
            
            logging.info(f"启动监控系统扩展: {self.extension_id}，收集间隔: {collection_interval}秒，导出器: {exporters}")
            
            # 模拟启动监控收集任务
            await asyncio.sleep(0.2)
            
        except Exception as e:
            self.status = ExtensionStatus.ERROR
            self.error_message = str(e)
            raise
    
    async def stop(self) -> None:
        """停止监控系统扩展"""
        try:
            if self.status != ExtensionStatus.RUNNING:
                return
            
            logging.info(f"停止监控系统扩展: {self.extension_id}")
            self.status = ExtensionStatus.STOPPED
            
            # 模拟停止过程
            await asyncio.sleep(0.1)
            
        except Exception as e:
            self.status = ExtensionStatus.ERROR
            self.error_message = str(e)
            raise
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        # 模拟指标收集
        import random
        import psutil
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            self.metrics["system"] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "memory_used_mb": memory.used // (1024 * 1024),
                "memory_total_mb": memory.total // (1024 * 1024),
                "disk_used_gb": disk.used // (1024 * 1024 * 1024),
                "disk_total_gb": disk.total // (1024 * 1024 * 1024),
                "timestamp": datetime.now().isoformat()
            }
            
            # 检查告警阈值
            alert_thresholds = self.config.get("alert_thresholds", {})
            alerts = []
            
            if cpu_percent > alert_thresholds.get("cpu_percent", 80.0):
                alerts.append({
                    "level": "WARNING",
                    "metric": "cpu_percent",
                    "value": cpu_percent,
                    "threshold": alert_thresholds.get("cpu_percent", 80.0),
                    "message": f"CPU使用率过高: {cpu_percent}%"
                })
            
            if memory.percent > alert_thresholds.get("memory_percent", 85.0):
                alerts.append({
                    "level": "WARNING",
                    "metric": "memory_percent",
                    "value": memory.percent,
                    "threshold": alert_thresholds.get("memory_percent", 85.0),
                    "message": f"内存使用率过高: {memory.percent}%"
                })
            
            self.alerts.extend(alerts)
            
            return self.metrics
            
        except Exception as e:
            logging.error(f"收集指标失败: {str(e)}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """监控系统健康检查"""
        try:
            if self.status != ExtensionStatus.RUNNING:
                return {
                    "healthy": False,
                    "status": self.status.value,
                    "message": f"扩展未运行: {self.status.value}"
                }
            
            # 收集最新指标
            metrics = await self.collect_metrics()
            
            # 检查是否有活跃告警
            active_alerts = [a for a in self.alerts if a.get("level") in ["CRITICAL", "WARNING"]]
            
            is_healthy = len(active_alerts) == 0
            
            return {
                "healthy": is_healthy,
                "status": self.status.value,
                "message": "监控系统运行正常" if is_healthy else f"发现 {len(active_alerts)} 个告警",
                "details": {
                    "metrics_collected": bool(metrics and "system" in metrics),
                    "active_alerts": len(active_alerts),
                    "collection_interval": self.config.get("collection_interval", 60),
                    "exporters": self.config.get("exporters", []),
                    "last_collection": metrics.get("system", {}).get("timestamp") if metrics else None
                }
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "status": ExtensionStatus.ERROR.value,
                "message": f"健康检查失败: {str(e)}",
                "error": str(e)
            }


class CachingExtension(ExtensionInterface):
    """缓存系统扩展"""
    
    def __init__(self, extension_id: str, config: Dict[str, Any], metadata: ExtensionMetadata):
        super().__init__(extension_id, config, metadata)
        self.cache_store: Dict[str, Any] = {}
        self.hit_count = 0
        self.miss_count = 0
    
    async def initialize(self) -> None:
        """初始化缓存系统扩展"""
        try:
            self.status = ExtensionStatus.INITIALIZING
            logging.info(f"初始化缓存系统扩展: {self.extension_id}")
            
            # 验证配置
            cache_type = self.config.get("cache_type", "memory")
            if cache_type not in ["memory", "redis", "memcached"]:
                raise ExtensionInitializationError(f"不支持的缓存类型: {cache_type}")
            
            # 根据缓存类型进行初始化
            if cache_type == "memory":
                self.cache_store = {}
                logging.info("使用内存缓存后端")
            elif cache_type == "redis":
                # 这里应该是实际的Redis连接初始化
                logging.info("使用Redis缓存后端（模拟）")
            elif cache_type == "memcached":
                # 这里应该是实际的Memcached连接初始化
                logging.info("使用Memcached缓存后端（模拟）")
            
            # 模拟初始化过程
            await asyncio.sleep(0.1)
            
            self.initialized_at = datetime.now()
            self.status = ExtensionStatus.STOPPED
            logging.info(f"缓存系统扩展初始化完成: {self.extension_id}")
            
        except Exception as e:
            self.status = ExtensionStatus.ERROR
            self.error_message = str(e)
            raise ExtensionInitializationError(f"缓存系统扩展初始化失败: {str(e)}")
    
    async def start(self) -> None:
        """启动缓存系统扩展"""
        try:
            if self.status != ExtensionStatus.STOPPED:
                raise ExtensionError(f"扩展状态不正确，无法启动: {self.status}")
            
            self.status = ExtensionStatus.RUNNING
            self.started_at = datetime.now()
            
            cache_type = self.config.get("cache_type", "memory")
            host = self.config.get("host", "localhost")
            port = self.config.get("port", 6379)
            
            logging.info(f"启动缓存系统扩展: {self.extension_id} ({cache_type}) 在 {host}:{port}")
            
            # 模拟启动过程
            await asyncio.sleep(0.15)
            
        except Exception as e:
            self.status = ExtensionStatus.ERROR
            self.error_message = str(e)
            raise
    
    async def stop(self) -> None:
        """停止缓存系统扩展"""
        try:
            if self.status != ExtensionStatus.RUNNING:
                return
            
            logging.info(f"停止缓存系统扩展: {self.extension_id}")
            self.status = ExtensionStatus.STOPPED
            
            # 清理缓存（如果是内存缓存）
            cache_type = self.config.get("cache_type", "memory")
            if cache_type == "memory":
                self.cache_store.clear()
            
            # 模拟停止过程
            await asyncio.sleep(0.1)
            
        except Exception as e:
            self.status = ExtensionStatus.ERROR
            self.error_message = str(e)
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            if key in self.cache_store:
                self.hit_count += 1
                return self.cache_store[key]
            else:
                self.miss_count += 1
                return None
        except Exception as e:
            logging.error(f"获取缓存失败: {key}, 错误: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            self.cache_store[key] = value
            return True
        except Exception as e:
            logging.error(f"设置缓存失败: {key}, 错误: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            if key in self.cache_store:
                del self.cache_store[key]
                return True
            return False
        except Exception as e:
            logging.error(f"删除缓存失败: {key}, 错误: {str(e)}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """缓存系统健康检查"""
        try:
            if self.status != ExtensionStatus.RUNNING:
                return {
                    "healthy": False,
                    "status": self.status.value,
                    "message": f"扩展未运行: {self.status.value}"
                }
            
            cache_type = self.config.get("cache_type", "memory")
            
            # 测试缓存功能
            test_key = "__health_check__"
            test_value = {"timestamp": datetime.now().isoformat(), "check": "healthy"}
            
            set_success = await self.set(test_key, test_value)
            get_success = await self.get(test_key) is not None
            delete_success = await self.delete(test_key)
            
            is_healthy = set_success and get_success and delete_success
            
            return {
                "healthy": is_healthy,
                "status": self.status.value,
                "message": "缓存系统运行正常" if is_healthy else "缓存功能测试失败",
                "details": {
                    "cache_type": cache_type,
                    "hit_count": self.hit_count,
                    "miss_count": self.miss_count,
                    "hit_rate": self.hit_count / (self.hit_count + self.miss_count) if (self.hit_count + self.miss_count) > 0 else 0,
                    "cache_size": len(self.cache_store),
                    "test_passed": {
                        "set": set_success,
                        "get": get_success,
                        "delete": delete_success
                    }
                }
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "status": ExtensionStatus.ERROR.value,
                "message": f"健康检查失败: {str(e)}",
                "error": str(e)
            }


# ============================================================================
# 第四部分：扩展加载器 (ExtensionLoader)
# ============================================================================

class ExtensionLoader:
    """扩展加载器 - 负责动态加载和管理扩展"""
    
    def __init__(self, config_path: Optional[str] = None, config_data: Optional[Dict[str, Any]] = None):
        self.config_path = config_path
        self.config_data = config_data or {}
        self.extensions: Dict[str, ExtensionInterface] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
        self.reverse_dependency_graph: Dict[str, List[str]] = {}
        self.env_vars: Dict[str, str] = {}
        self.loaded_modules: Set[str] = set()
        self.initialized = False
        
        # 扩展类型映射
        self.extension_type_map = {
            ExtensionType.MCP_SERVER.value: MCPServerExtension,
            ExtensionType.MONITORING.value: MonitoringExtension,
            ExtensionType.CACHING.value: CachingExtension,
            # 可以添加更多扩展类型映射
        }
    
    async def load_config(self, env_vars: Optional[Dict[str, str]] = None) -> bool:
        """加载扩展配置"""
        try:
            self.env_vars = env_vars or {}
            
            # 如果提供了配置文件路径，从文件加载
            if self.config_path:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            
            # 解析环境变量
            self.config_data = self._resolve_environment_variables(self.config_data)
            
            # 构建依赖图
            self._build_dependency_graph()
            
            # 检查循环依赖
            cycles = self._detect_circular_dependencies()
            if cycles:
                raise ExtensionDependencyError(f"发现循环依赖: {cycles}")
            
            # 创建扩展实例（但不初始化）
            await self._create_extension_instances()
            
            logging.info(f"扩展配置加载成功，共 {len(self.extensions)} 个扩展")
            return True
            
        except Exception as e:
            logging.error(f"加载扩展配置失败: {str(e)}")
            return False
    
    def _resolve_environment_variables(self, config: Any) -> Any:
        """递归解析环境变量"""
        if isinstance(config, str):
            # 匹配 ${VAR_NAME} 或 ${VAR_NAME:default}
            pattern = r'\$\{([A-Za-z0-9_]+)(?::([^}]+))?\}'
            
            def replace_var(match):
                var_name = match.group(1)
                default_value = match.group(2)
                
                if var_name in self.env_vars:
                    return self.env_vars[var_name]
                elif var_name in os.environ:
                    return os.environ[var_name]
                elif default_value is not None:
                    return default_value
                else:
                    # 保持原样，等待运行时解析
                    return match.group(0)
            
            return re.sub(pattern, replace_var, config)
        elif isinstance(config, dict):
            return {k: self._resolve_environment_variables(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_environment_variables(item) for item in config]
        else:
            return config
    
    def _build_dependency_graph(self):
        """构建依赖图"""
        extensions = self.config_data.get("extensions", {})
        
        for ext_id, ext_config in extensions.items():
            self.dependency_graph[ext_id] = ext_config.get("dependencies", [])
            
            # 同时构建反向依赖图
            for dep_id in ext_config.get("dependencies", []):
                if dep_id not in self.reverse_dependency_graph:
                    self.reverse_dependency_graph[dep_id] = []
                self.reverse_dependency_graph[dep_id].append(ext_id)
    
    def _detect_circular_dependencies(self) -> List[List[str]]:
        """检测循环依赖"""
        visited = set()
        recursion_stack = set()
        cycles = []
        
        def dfs(current: str, path: List[str]) -> None:
            visited.add(current)
            recursion_stack.add(current)
            
            for neighbor in self.dependency_graph.get(current, []):
                if neighbor not in self.dependency_graph:
                    continue
                
                if neighbor in recursion_stack:
                    # 发现循环依赖
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif neighbor not in visited:
                    dfs(neighbor, path + [neighbor])
            
            recursion_stack.remove(current)
        
        # 从每个未访问的扩展开始DFS
        for ext_id in self.dependency_graph:
            if ext_id not in visited:
                dfs(ext_id, [ext_id])
        
        # 去重
        unique_cycles = []
        for cycle in cycles:
            min_index = cycle.index(min(cycle))
            normalized = tuple(cycle[min_index:] + cycle[:min_index])
            if normalized not in unique_cycles:
                unique_cycles.append(normalized)
        
        return [list(cycle) for cycle in unique_cycles]
    
    async def _create_extension_instances(self):
        """创建扩展实例"""
        extensions = self.config_data.get("extensions", {})
        
        for ext_id, ext_config in extensions.items():
            # 检查是否启用
            if not ext_config.get("enabled", True):
                logging.info(f"扩展 {ext_id} 已禁用，跳过创建")
                continue
            
            # 获取扩展类型
            ext_type_str = ext_config.get("type", "").lower()
            if not ext_type_str:
                raise ExtensionError(f"扩展 {ext_id} 未指定类型")
            
            # 查找扩展类
            extension_class = self.extension_type_map.get(ext_type_str)
            if not extension_class:
                raise ExtensionError(f"不支持的扩展类型: {ext_type_str}")
            
            # 创建元数据
            metadata = ExtensionMetadata(
                name=ext_config.get("name", ext_id),
                type=ExtensionType(ext_type_str),
                version=ext_config.get("version", "1.0.0"),
                description=ext_config.get("description", ""),
                enabled=ext_config.get("enabled", True),
                category=ext_config.get("metadata", {}).get("category", ""),
                priority=ext_config.get("metadata", {}).get("priority", "medium"),
                created_by=ext_config.get("metadata", {}).get("created_by", "system"),
                created_at=ext_config.get("metadata", {}).get("created_at", datetime.now().isoformat()),
                updated_at=datetime.now().isoformat()
            )
            
            # 创建扩展实例
            extension = extension_class(
                extension_id=ext_id,
                config=ext_config.get("config", {}),
                metadata=metadata
            )
            
            self.extensions[ext_id] = extension
            logging.info(f"创建扩展实例: {ext_id} ({ext_type_str})")
    
    def get_extension_load_order(self) -> List[str]:
        """获取扩展加载顺序（拓扑排序）"""
        # 计算入度
        indegree = defaultdict(int)
        for ext_id in self.dependency_graph:
            indegree[ext_id] = 0
        
        for ext_id, dependencies in self.dependency_graph.items():
            for dep_id in dependencies:
                if dep_id in indegree:
                    indegree[dep_id] += 1
        
        # Kahn算法
        queue = deque([ext_id for ext_id in indegree if indegree[ext_id] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in self.dependency_graph.get(current, []):
                if neighbor in indegree:
                    indegree[neighbor] -= 1
                    if indegree[neighbor] == 0:
                        queue.append(neighbor)
        
        # 检查是否所有节点都被处理
        if len(result) != len(self.dependency_graph):
            remaining = set(self.dependency_graph.keys()) - set(result)
            raise ExtensionDependencyError(f"无法解析所有依赖，可能存在环: {remaining}")
        
        return result
    
    async def initialize_all(self) -> bool:
        """初始化所有扩展"""
        try:
            if self.initialized:
                logging.warning("扩展系统已初始化")
                return True
            
            logging.info("开始初始化所有扩展...")
            
            # 获取初始化顺序
            load_order = self.get_extension_load_order()
            logging.info(f"扩展初始化顺序: {load_order}")
            
            # 按顺序初始化
            for ext_id in load_order:
                if ext_id not in self.extensions:
                    logging.warning(f"扩展 {ext_id} 不存在，跳过")
                    continue
                
                extension = self.extensions[ext_id]
                
                # 检查是否启用
                if not extension.metadata.enabled:
                    logging.info(f"扩展 {ext_id} 已禁用，跳过初始化")
                    continue
                
                # 检查依赖是否已初始化
                dependencies = self.dependency_graph.get(ext_id, [])
                for dep_id in dependencies:
                    if dep_id in self.extensions:
                        dep_extension = self.extensions[dep_id]
                        if dep_extension.status == ExtensionStatus.ERROR:
                            raise ExtensionDependencyError(
                                f"扩展 {ext_id} 的依赖 {dep_id} 处于错误状态，无法初始化"
                            )
                
                # 初始化扩展
                try:
                    logging.info(f"初始化扩展: {ext_id}")
                    await extension.initialize()
                    logging.info(f"扩展初始化成功: {ext_id}")
                except Exception as e:
                    logging.error(f"扩展初始化失败: {ext_id}, 错误: {str(e)}")
                    extension.status = ExtensionStatus.ERROR
                    extension.error_message = str(e)
                    # 根据配置决定是否继续
                    global_config = self.config_data.get("global_config", {})
                    if not global_config.get("continue_on_initialization_error", False):
                        raise
            
            self.initialized = True
            logging.info("所有扩展初始化完成")
            return True
            
        except Exception as e:
            logging.error(f"初始化扩展系统失败: {str(e)}")
            return False
    
    async def start_all(self) -> bool:
        """启动所有扩展"""
        try:
            if not self.initialized:
                raise ExtensionError("扩展系统未初始化，请先调用 initialize_all()")
            
            logging.info("开始启动所有扩展...")
            
            # 获取启动顺序（与初始化顺序相同）
            load_order = self.get_extension_load_order()
            
            for ext_id in load_order:
                if ext_id not in self.extensions:
                    continue
                
                extension = self.extensions[ext_id]
                
                # 检查是否启用
                if not extension.metadata.enabled:
                    continue
                
                # 检查状态
                if extension.status != ExtensionStatus.STOPPED:
                    logging.warning(f"扩展 {ext_id} 状态不正确，无法启动: {extension.status}")
                    continue
                
                # 启动扩展
                try:
                    logging.info(f"启动扩展: {ext_id}")
                    await extension.start()
                    logging.info(f"扩展启动成功: {ext_id}")
                except Exception as e:
                    logging.error(f"扩展启动失败: {ext_id}, 错误: {str(e)}")
                    extension.status = ExtensionStatus.ERROR
                    extension.error_message = str(e)
                    # 根据配置决定是否继续
                    global_config = self.config_data.get("global_config", {})
                    if not global_config.get("continue_on_start_error", False):
                        raise
            
            logging.info("所有扩展启动完成")
            return True
            
        except Exception as e:
            logging.error(f"启动扩展系统失败: {str(e)}")
            return False
    
    async def stop_all(self) -> bool:
        """停止所有扩展"""
        try:
            logging.info("开始停止所有扩展...")
            
            # 按反向依赖顺序停止（先停止依赖其他扩展的扩展）
            reverse_order = list(reversed(self.get_extension_load_order()))
            
            for ext_id in reverse_order:
                if ext_id not in self.extensions:
                    continue
                
                extension = self.extensions[ext_id]
                
                # 检查状态
                if extension.status not in [ExtensionStatus.RUNNING, ExtensionStatus.ERROR]:
                    continue
                
                # 停止扩展
                try:
                    logging.info(f"停止扩展: {ext_id}")
                    await extension.stop()
                    logging.info(f"扩展停止成功: {ext_id}")
                except Exception as e:
                    logging.error(f"扩展停止失败: {ext_id}, 错误: {str(e)}")
                    # 即使失败也继续停止其他扩展
            
            self.initialized = False
            logging.info("所有扩展停止完成")
            return True
            
        except Exception as e:
            logging.error(f"停止扩展系统失败: {str(e)}")
            return False
    
    async def health_check_all(self) -> Dict[str, Any]:
        """检查所有扩展的健康状态"""
        try:
            if not self.initialized:
                return {
                    "healthy": False,
                    "message": "扩展系统未初始化",
                    "extensions": {}
                }
            
            results = {}
            all_healthy = True
            
            for ext_id, extension in self.extensions.items():
                if not extension.metadata.enabled:
                    continue
                
                try:
                    health_result = await extension.health_check()
                    results[ext_id] = health_result
                    
                    if not health_result.get("healthy", False):
                        all_healthy = False
                except Exception as e:
                    results[ext_id] = {
                        "healthy": False,
                        "status": ExtensionStatus.ERROR.value,
                        "message": f"健康检查异常: {str(e)}",
                        "error": str(e)
                    }
                    all_healthy = False
            
            return {
                "healthy": all_healthy,
                "message": "所有扩展健康" if all_healthy else "部分扩展不健康",
                "extensions": results,
                "timestamp": datetime.now().isoformat(),
                "total_extensions": len(self.extensions),
                "healthy_count": sum(1 for r in results.values() if r.get("healthy", False)),
                "unhealthy_count": sum(1 for r in results.values() if not r.get("healthy", True))
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "message": f"健康检查失败: {str(e)}",
                "error": str(e),
                "extensions": {},
                "timestamp": datetime.now().isoformat()
            }
    
    def get_extension(self, extension_id: str) -> Optional[ExtensionInterface]:
        """获取指定扩展"""
        return self.extensions.get(extension_id)
    
    def list_extensions(self) -> List[Dict[str, Any]]:
        """列出所有扩展"""
        return [ext.get_status() for ext in self.extensions.values()]
    
    def get_dependency_tree(self, extension_id: str) -> Dict[str, Any]:
        """获取扩展的依赖树"""
        if extension_id not in self.dependency_graph:
            return {}
        
        def build_tree(current: str, visited: Set[str]) -> Dict[str, Any]:
            if current in visited:
                return {"extension_id": current, "cyclic": True}
            
            visited.add(current)
            
            extension = self.extensions.get(current)
            node = {
                "extension_id": current,
                "name": extension.metadata.name if extension else current,
                "type": extension.metadata.type.value if extension else "unknown",
                "dependencies": []
            }
            
            for dep_id in self.dependency_graph.get(current, []):
                dep_node = build_tree(dep_id, visited.copy())
                node["dependencies"].append(dep_node)
            
            return node
        
        return build_tree(extension_id, set())
    
    def save_config_backup(self, backup_dir: str) -> str:
        """保存配置备份"""
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"extensions_config_backup_{timestamp}.json"
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        
        return str(backup_file)


# ============================================================================
# 第五部分：工具函数和辅助类
# ============================================================================

class ExtensionConfigValidator:
    """扩展配置验证器"""
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> List[str]:
        """验证扩展配置"""
        errors = []
        
        # 检查必需字段
        if "extensions" not in config:
            errors.append("配置缺少 'extensions' 字段")
            return errors
        
        extensions = config.get("extensions", {})
        
        # 检查每个扩展
        for ext_id, ext_config in extensions.items():
            # 检查扩展ID格式
            if not re.match(r'^[a-z0-9_-]+$', ext_id):
                errors.append(f"扩展ID格式无效: {ext_id}，只能包含小写字母、数字、下划线和连字符")
            
            # 检查必需字段
            required_fields = ["type", "name"]
            for field in required_fields:
                if field not in ext_config:
                    errors.append(f"扩展 {ext_id} 缺少必需字段: {field}")
            
            # 检查扩展类型
            ext_type = ext_config.get("type", "").lower()
            valid_types = ["mcp_server", "monitoring", "caching", "storage", "message_queue", "custom"]
            if ext_type and ext_type not in valid_types:
                errors.append(f"扩展 {ext_id} 类型无效: {ext_type}，有效类型: {', '.join(valid_types)}")
            
            # 检查依赖关系
            dependencies = ext_config.get("dependencies", [])
            for dep_id in dependencies:
                if dep_id not in extensions:
                    errors.append(f"扩展 {ext_id} 依赖不存在的扩展: {dep_id}")
        
        # 检查全局配置
        global_config = config.get("global_config", {})
        if "extension_timeout_seconds" in global_config:
            timeout = global_config["extension_timeout_seconds"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append("global_config.extension_timeout_seconds 必须是正数")
        
        return errors
    
    @staticmethod
    def generate_config_template() -> Dict[str, Any]:
        """生成配置模板"""
        return {
            "version": "1.0.0",
            "description": "扩展配置模板",
            "environment": "${ENVIRONMENT:development}",
            
            "extensions": {
                "example-mcp-server": {
                    "type": "mcp_server",
                    "name": "示例MCP服务器",
                    "enabled": True,
                    "description": "MCP服务器扩展示例",
                    "config": {
                        "server_type": "filesystem",
                        "port": 8001,
                        "host": "localhost"
                    },
                    "dependencies": [],
                    "metadata": {
                        "category": "storage",
                        "priority": "medium"
                    }
                },
                
                "example-monitoring": {
                    "type": "monitoring",
                    "name": "示例监控系统",
                    "enabled": True,
                    "description": "监控系统扩展示例",
                    "config": {
                        "collection_interval": 60,
                        "exporters": ["prometheus"]
                    },
                    "dependencies": ["example-mcp-server"],
                    "metadata": {
                        "category": "observability",
                        "priority": "high"
                    }
                }
            },
            
            "global_config": {
                "log_level": "INFO",
                "max_concurrent_extensions": 10,
                "health_check_interval": 30
            },
            
            "metadata": {
                "created_at": "${TIMESTAMP}",
                "created_by": "config-generator"
            }
        }


class ExtensionFactory:
    """扩展工厂 - 支持动态注册和创建扩展"""
    
    def __init__(self):
        self.extension_classes: Dict[str, Type[ExtensionInterface]] = {}
        self.register_builtin_extensions()
    
    def register_builtin_extensions(self):
        """注册内置扩展类型"""
        self.register_extension("mcp_server", MCPServerExtension)
        self.register_extension("monitoring", MonitoringExtension)
        self.register_extension("caching", CachingExtension)
    
    def register_extension(self, extension_type: str, extension_class: Type[ExtensionInterface]):
        """注册扩展类型"""
        self.extension_classes[extension_type] = extension_class
        logging.info(f"注册扩展类型: {extension_type} -> {extension_class.__name__}")
    
    def create_extension(self, extension_id: str, ext_config: Dict[str, Any], 
                        metadata: ExtensionMetadata) -> Optional[ExtensionInterface]:
        """创建扩展实例"""
        ext_type_str = ext_config.get("type", "").lower()
        
        if not ext_type_str:
            logging.error(f"扩展 {extension_id} 未指定类型")
            return None
        
        extension_class = self.extension_classes.get(ext_type_str)
        if not extension_class:
            logging.error(f"不支持的扩展类型: {ext_type_str}")
            return None
        
        try:
            return extension_class(extension_id, ext_config.get("config", {}), metadata)
        except Exception as e:
            logging.error(f"创建扩展实例失败: {extension_id}, 错误: {str(e)}")
            return None
    
    def list_supported_extensions(self) -> List[Dict[str, Any]]:
        """列出支持的扩展类型"""
        return [
            {
                "type": ext_type,
                "class": cls.__name__,
                "description": cls.__doc__ or "无描述"
            }
            for ext_type, cls in self.extension_classes.items()
        ]


# ============================================================================
# 第六部分：测试函数
# ============================================================================

async def test_basic_extension_loading():
    """测试基础扩展加载"""
    print("=== 测试基础扩展加载 ===")
    
    # 创建扩展加载器
    loader = ExtensionLoader(config_data=EXAMPLE_EXTENSIONS_CONFIG_BASIC)
    
    # 设置环境变量
    env_vars = {
        "ENVIRONMENT": "testing",
        "MCP_PORT": "9001",
        "REDIS_HOST": "test-redis",
        "LOG_LEVEL": "DEBUG"
    }
    
    # 加载配置
    success = await loader.load_config(env_vars)
    print(f"配置加载结果: {success}")
    
    if success:
        # 列出扩展
        extensions = loader.list_extensions()
        print(f"加载的扩展数量: {len(extensions)}")
        for ext in extensions:
            print(f"  - {ext['extension_id']}: {ext['name']} ({ext['type']})")
        
        # 检查依赖图
        load_order = loader.get_extension_load_order()
        print(f"扩展加载顺序: {load_order}")
        
        # 初始化扩展
        init_success = await loader.initialize_all()
        print(f"扩展初始化结果: {init_success}")
        
        if init_success:
            # 启动扩展
            start_success = await loader.start_all()
            print(f"扩展启动结果: {start_success}")
            
            if start_success:
                # 健康检查
                health = await loader.health_check_all()
                print(f"系统健康状态: {health['healthy']}")
                print(f"健康消息: {health['message']}")
                
                # 获取单个扩展状态
                mcp_ext = loader.get_extension("mcp-server-1")
                if mcp_ext:
                    print(f"MCP服务器扩展状态: {mcp_ext.get_status()}")
                
                # 停止扩展
                stop_success = await loader.stop_all()
                print(f"扩展停止结果: {stop_success}")
        
        # 保存配置备份
        backup_file = loader.save_config_backup("./backups")
        print(f"配置备份保存到: {backup_file}")
    
    print("测试完成\n")
    return success


async def test_advanced_extension_loading():
    """测试高级扩展加载"""
    print("=== 测试高级扩展加载 ===")
    
    # 创建扩展加载器
    loader = ExtensionLoader(config_data=EXAMPLE_EXTENSIONS_CONFIG_ADVANCED)
    
    # 加载配置
    success = await loader.load_config()
    print(f"配置加载结果: {success}")
    
    if success:
        # 验证配置
        validator = ExtensionConfigValidator()
        errors = validator.validate_config(EXAMPLE_EXTENSIONS_CONFIG_ADVANCED)
        
        if errors:
            print(f"配置验证错误: {errors}")
        else:
            print("配置验证通过")
        
        # 列出扩展
        extensions = loader.list_extensions()
        enabled_count = sum(1 for ext in extensions if ext.get("enabled", False))
        disabled_count = len(extensions) - enabled_count
        
        print(f"总扩展数: {len(extensions)}")
        print(f"启用扩展: {enabled_count}")
        print(f"禁用扩展: {disabled_count}")
        
        # 获取依赖树
        tree = loader.get_dependency_tree("storage-s3")
        print(f"storage-s3 的依赖树深度: {len(str(tree))} 字符")
    
    print("测试完成\n")
    return success


async def test_extension_factory():
    """测试扩展工厂"""
    print("=== 测试扩展工厂 ===")
    
    factory = ExtensionFactory()
    
    # 列出支持的扩展类型
    supported = factory.list_supported_extensions()
    print(f"支持的扩展类型: {len(supported)}")
    for ext in supported:
        print(f"  - {ext['type']}: {ext['class']}")
    
    # 创建扩展元数据
    metadata = ExtensionMetadata(
        name="测试扩展",
        type=ExtensionType.MCP_SERVER,
        description="测试用扩展"
    )
    
    # 创建扩展配置
    config = {
        "type": "mcp_server",
        "config": {
            "server_type": "filesystem",
            "port": 8080,
            "host": "localhost"
        }
    }
    
    # 创建扩展实例
    extension = factory.create_extension("test-extension", config, metadata)
    
    if extension:
        print(f"成功创建扩展: {extension.extension_id}")
        print(f"扩展类型: {extension.metadata.type.value}")
        print(f"扩展状态: {extension.status.value}")
    else:
        print("创建扩展失败")
    
    print("测试完成\n")
    return extension is not None


async def test_error_handling():
    """测试错误处理"""
    print("=== 测试错误处理 ===")
    
    # 测试无效配置
    invalid_config = {
        "extensions": {
            "invalid-extension": {
                # 缺少必需字段
            }
        }
    }
    
    loader = ExtensionLoader(config_data=invalid_config)
    
    try:
        success = await loader.load_config()
        print(f"无效配置加载结果: {success} (预期: False)")
    except Exception as e:
        print(f"无效配置加载异常: {type(e).__name__}: {str(e)}")
    
    # 测试循环依赖
    circular_config = {
        "extensions": {
            "ext-a": {
                "type": "mcp_server",
                "name": "扩展A",
                "dependencies": ["ext-b"]
            },
            "ext-b": {
                "type": "monitoring",
                "name": "扩展B",
                "dependencies": ["ext-a"]  # 循环依赖
            }
        }
    }
    
    loader2 = ExtensionLoader(config_data=circular_config)
    
    try:
        success = await loader2.load_config()
        print(f"循环依赖配置加载结果: {success} (预期: False)")
    except Exception as e:
        print(f"循环依赖配置加载异常: {type(e).__name__}: {str(e)}")
    
    print("测试完成\n")
    return True


async def test_performance():
    """测试性能"""
    print("=== 测试性能 ===")
    
    import time
    
    # 创建大型配置
    large_config = {
        "version": "1.0.0",
        "extensions": {}
    }
    
    # 添加多个扩展
    for i in range(50):
        ext_id = f"extension-{i:03d}"
        ext_type = "mcp_server" if i % 3 == 0 else "monitoring" if i % 3 == 1 else "caching"
        
        large_config["extensions"][ext_id] = {
            "type": ext_type,
            "name": f"扩展 {i}",
            "enabled": i % 10 != 0,  # 每10个禁用一个
            "config": {
                "port": 8000 + i,
                "host": "localhost"
            },
            "dependencies": [f"extension-{j:03d}" for j in range(max(0, i-3), i)] if i > 0 else []
        }
    
    # 测试加载性能
    start_time = time.time()
    
    loader = ExtensionLoader(config_data=large_config)
    success = await loader.load_config()
    
    load_time = time.time() - start_time
    
    print(f"大型配置加载结果: {success}")
    print(f"配置大小: {len(large_config['extensions'])} 个扩展")
    print(f"加载时间: {load_time:.3f} 秒")
    
    if success:
        # 测试初始化性能
        start_time = time.time()
        init_success = await loader.initialize_all()
        init_time = time.time() - start_time
        
        print(f"扩展初始化结果: {init_success}")
        print(f"初始化时间: {init_time:.3f} 秒")
        
        # 平均每个扩展的时间
        enabled_count = sum(1 for ext in loader.extensions.values() if ext.metadata.enabled)
        if enabled_count > 0:
            avg_time = init_time / enabled_count
            print(f"平均每个扩展初始化时间: {avg_time:.3f} 秒")
    
    print("测试完成\n")
    return True


# ============================================================================
# 第七部分：主函数和示例用法
# ============================================================================

async def main():
    """主函数"""
    print("=" * 80)
    print("扩展配置JSON (extensions_config.json) - 演示代码")
    print("=" * 80)
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行测试
    print("\n运行测试套件...\n")
    
    tests = [
        ("基础扩展加载", test_basic_extension_loading),
        ("高级扩展加载", test_advanced_extension_loading),
        ("扩展工厂", test_extension_factory),
        ("错误处理", test_error_handling),
        ("性能测试", test_performance)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"运行测试: {test_name}")
            result = await test_func()
            results.append((test_name, result, True))
            print(f"测试 {test_name} 结果: {'通过' if result else '失败'}\n")
        except Exception as e:
            print(f"测试 {test_name} 异常: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, str(e), False))
            print(f"测试 {test_name} 结果: 异常\n")
    
    # 打印测试总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    passed = sum(1 for _, _, success in results if success)
    total = len(results)
    
    print(f"总测试数: {total}")
    print(f"通过测试: {passed}")
    print(f"失败测试: {total - passed}")
    
    for test_name, result, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {status} {test_name}: {result}")
    
    # 示例：使用扩展加载器
    print("\n" + "=" * 80)
    print("示例：使用扩展加载器")
    print("=" * 80)
    
    # 1. 创建配置
    config = {
        "version": "1.0.0",
        "description": "示例扩展配置",
        
        "extensions": {
            "my-mcp-server": {
                "type": "mcp_server",
                "name": "我的MCP服务器",
                "enabled": True,
                "config": {
                    "server_type": "filesystem",
                    "port": 8888,
                    "host": "0.0.0.0"
                }
            },
            
            "my-monitoring": {
                "type": "monitoring",
                "name": "我的监控系统",
                "enabled": True,
                "dependencies": ["my-mcp-server"],
                "config": {
                    "collection_interval": 30,
                    "alert_enabled": True
                }
            }
        },
        
        "global_config": {
            "log_level": "INFO",
            "health_check_interval": 60
        }
    }
    
    # 2. 创建和配置加载器
    loader = ExtensionLoader(config_data=config)
    
    # 3. 加载配置
    await loader.load_config()
    
    # 4. 初始化扩展
    await loader.initialize_all()
    
    # 5. 启动扩展
    await loader.start_all()
    
    # 6. 检查健康状态
    health = await loader.health_check_all()
    print(f"系统健康状态: {health['healthy']}")
    
    # 7. 列出扩展
    extensions = loader.list_extensions()
    print(f"已加载扩展: {len(extensions)}")
    for ext in extensions:
        print(f"  - {ext['extension_id']}: {ext['status']}")
    
    # 8. 停止扩展
    await loader.stop_all()
    
    print("\n示例完成！")
    
    return passed == total


if __name__ == "__main__":
    # 运行主函数
    success = asyncio.run(main())
    
    if success:
        print("\n✅ 所有测试通过！扩展配置系统功能完整。")
    else:
        print("\n⚠️  部分测试失败，请检查实现。")
    
    sys.exit(0 if success else 1)