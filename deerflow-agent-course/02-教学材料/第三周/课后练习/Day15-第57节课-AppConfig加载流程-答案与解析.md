# Day 15 - 第57节课：AppConfig加载流程 - 答案与解析

## 📋 答案概览

本答案提供练习任务的参考实现和详细解析，涵盖多配置源加载、深度合并算法优化、高级配置验证、智能模板系统、配置管理和监控等核心功能。每个任务提供关键代码示例和设计思路。

## 🎯 任务1：实现增强版ConfigLoader

### 1.1 扩展配置源支持

#### JSON和INI配置文件支持

```python
import json
import configparser
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class ExtendedConfigLoader:
    """扩展版配置加载器，支持多种配置源"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.sources = []
        self.source_weights = {}
        self.source_health = {}
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """创建带重试机制的HTTP会话"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def load_json(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """加载JSON配置文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"JSON配置文件加载失败 {file_path}: {e}")
            return None
    
    def load_ini(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """加载INI配置文件"""
        try:
            config = configparser.ConfigParser()
            config.read(file_path, encoding='utf-8')
            result = {}
            for section in config.sections():
                result[section] = dict(config.items(section))
            return result
        except (configparser.Error, FileNotFoundError) as e:
            logger.error(f"INI配置文件加载失败 {file_path}: {e}")
            return None
    
    def load_remote(self, url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """从远程API加载配置"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"远程配置加载失败 {url}: {e}")
            return None
    
    def add_source(self, source_type: str, source_path: str, weight: float = 1.0):
        """添加配置源"""
        self.sources.append({
            'type': source_type,
            'path': source_path,
            'weight': weight
        })
        self.source_weights[source_path] = weight
        self.source_health[source_path] = True
    
    def load_all(self) -> Dict[str, Any]:
        """加载所有配置源并加权合并"""
        configs = []
        weights = []
        
        for source in self.sources:
            config = None
            if source['type'] == 'json':
                config = self.load_json(Path(source['path']))
            elif source['type'] == 'ini':
                config = self.load_ini(Path(source['path']))
            elif source['type'] == 'remote':
                config = self.load_remote(source['path'])
            
            if config is not None:
                configs.append(config)
                weights.append(source['weight'])
        
        # 加权合并配置（简化：选择权重最高的）
        if not configs:
            return {}
        max_weight = max(weights)
        max_index = weights.index(max_weight)
        return configs[max_index]
```

#### 健康检查和故障切换

```python
class HealthMonitor:
    """配置源健康监控器"""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.health_status = {}
        self.failure_count = {}
        self.backup_sources = {}
        
    def register_source(self, source_id: str, primary_path: str, backup_paths: list):
        """注册配置源及其备份"""
        self.health_status[source_id] = True
        self.failure_count[source_id] = 0
        self.backup_sources[source_id] = {
            'primary': primary_path,
            'backups': backup_paths,
            'current_index': 0
        }
    
    def check_source(self, source_id: str) -> bool:
        """检查单个配置源健康状态"""
        source_info = self.backup_sources.get(source_id)
        if not source_info:
            return False
        
        current_path = self._get_current_path(source_id)
        is_healthy = self._ping_source(current_path)
        
        if not is_healthy:
            self.failure_count[source_id] += 1
            if self.failure_count[source_id] >= 3:
                self._switch_to_backup(source_id)
                self.failure_count[source_id] = 0
            self.health_status[source_id] = False
        else:
            self.health_status[source_id] = True
            self.failure_count[source_id] = 0
        
        return self.health_status[source_id]
    
    def _get_current_path(self, source_id: str) -> str:
        """获取当前使用的配置源路径"""
        source_info = self.backup_sources[source_id]
        if source_info['current_index'] == 0:
            return source_info['primary']
        else:
            return source_info['backups'][source_info['current_index'] - 1]
    
    def _ping_source(self, path: str) -> bool:
        """检查配置源是否可达"""
        # 简化的可达性检查
        return True
    
    def _switch_to_backup(self, source_id: str):
        """切换到备用配置源"""
        source_info = self.backup_sources[source_id]
        if source_info['current_index'] < len(source_info['backups']):
            source_info['current_index'] += 1
            logger.info(f"配置源 {source_id} 切换到备份 {source_info['current_index']}")
```

### 1.2 优化深度合并算法

#### 高性能深度合并实现

```python
from typing import Any, Dict, List, Union, Set
from collections.abc import Mapping
import copy

class OptimizedDeepMerger:
    """优化的深度合并算法"""
    
    MERGE_STRATEGIES = {
        'replace': '替换',
        'append': '追加',
        'extend': '扩展',
        'union': '并集',
        'intersection': '交集'
    }
    
    def __init__(self, default_strategy: str = 'replace'):
        self.default_strategy = default_strategy
        self.strategy_map = {}
        self.performance_stats = {
            'merge_count': 0,
            'total_time': 0,
            'memory_usage': 0
        }
    
    def merge(self, base: Any, update: Any, path: str = '', strategy: str = None) -> Any:
        """深度合并两个数据结构"""
        start_time = time.time()
        result = self._merge(base, update, path, strategy or self.default_strategy)
        end_time = time.time()
        
        self.performance_stats['merge_count'] += 1
        self.performance_stats['total_time'] += (end_time - start_time)
        
        return result
    
    def _merge(self, base: Any, update: Any, path: str, strategy: str) -> Any:
        """递归合并实现"""
        # 如果update是None，返回base
        if update is None:
            return base
        
        # 如果base是None，返回update
        if base is None:
            return update
        
        # 类型不同，根据策略处理
        if type(base) != type(update):
            return self._handle_type_mismatch(base, update, path, strategy)
        
        # 根据类型选择合并方法
        if isinstance(base, Mapping):
            return self._merge_dict(base, update, path, strategy)
        elif isinstance(base, list):
            return self._merge_list(base, update, path, strategy)
        elif isinstance(base, set):
            return self._merge_set(base, update, path, strategy)
        else:
            # 基本类型，根据策略决定
            if strategy == 'replace':
                return update
            else:
                return base
    
    def _merge_dict(self, base: Dict, update: Dict, path: str, strategy: str) -> Dict:
        """合并字典"""
        result = copy.copy(base)
        
        for key, update_value in update.items():
            new_path = f"{path}.{key}" if path else key
            
            # 检查是否有自定义策略
            item_strategy = self.strategy_map.get(new_path, strategy)
            
            if key in base:
                result[key] = self._merge(base[key], update_value, new_path, item_strategy)
            else:
                result[key] = update_value
        
        return result
    
    def _merge_list(self, base: List, update: List, path: str, strategy: str) -> List:
        """合并列表"""
        if strategy == 'replace':
            return copy.copy(update)
        elif strategy == 'append':
            return base + update
        elif strategy == 'extend':
            result = copy.copy(base)
            result.extend(update)
            return result
        elif strategy == 'union':
            result = copy.copy(base)
            seen = set(result)
            for item in update:
                if item not in seen:
                    result.append(item)
                    seen.add(item)
            return result
        elif strategy == 'intersection':
            return [item for item in base if item in update]
        else:
            return copy.copy(update)
    
    def set_strategy(self, path_pattern: str, strategy: str):
        """为特定路径设置合并策略"""
        self.strategy_map[path_pattern] = strategy
    
    def detect_conflicts(self, base: Any, update: Any, path: str = '') -> List[Dict]:
        """检测合并冲突"""
        conflicts = []
        
        if isinstance(base, Mapping) and isinstance(update, Mapping):
            for key in set(base.keys()) & set(update.keys()):
                new_path = f"{path}.{key}" if path else key
                if base[key] != update[key]:
                    conflicts.append({
                        'path': new_path,
                        'base_value': base[key],
                        'update_value': update[key],
                        'type': 'value_conflict'
                    })
                
                # 递归检查嵌套冲突
                sub_conflicts = self.detect_conflicts(base[key], update[key], new_path)
                conflicts.extend(sub_conflicts)
        
        return conflicts
```

### 1.3 增强错误处理和恢复

#### 结构化错误处理系统

```python
from datetime import datetime
from enum import Enum

class ErrorSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ConfigError(Exception):
    """配置相关错误的基类"""
    
    def __init__(self, 
                 message: str, 
                 severity: ErrorSeverity = ErrorSeverity.ERROR,
                 location: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None,
                 suggestion: Optional[str] = None):
        super().__init__(message)
        self.severity = severity
        self.location = location
        self.context = context or {}
        self.suggestion = suggestion
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'message': str(self),
            'severity': self.severity.value,
            'location': self.location,
            'context': self.context,
            'suggestion': self.suggestion,
            'timestamp': self.timestamp.isoformat()
        }

class EnhancedErrorHandler:
    """增强的错误处理器"""
    
    def __init__(self, enable_retry: bool = True, max_retries: int = 3):
        self.enable_retry = enable_retry
        self.max_retries = max_retries
        self.retry_count = 0
        self.error_log = []
        self.fallback_configs = {}
        
    def handle_error(self, error: Exception, operation: str) -> Optional[Any]:
        """处理配置错误"""
        error_info = self._extract_error_info(error, operation)
        self.error_log.append(error_info)
        
        # 根据错误类型选择处理策略
        if isinstance(error, ConfigError):
            return self._handle_config_error(error, operation)
        elif isinstance(error, (FileNotFoundError, json.JSONDecodeError)):
            return self._handle_file_error(error, operation)
        elif isinstance(error, requests.RequestException):
            return self._handle_network_error(error, operation)
        else:
            return self._handle_unknown_error(error, operation)
    
    def _handle_config_error(self, error: ConfigError, operation: str) -> Optional[Any]:
        """处理配置错误"""
        if error.severity == ErrorSeverity.WARNING:
            logger.warning(f"配置警告: {error.message}")
            return None
        elif error.severity == ErrorSeverity.ERROR:
            if self.enable_retry and self.retry_count < self.max_retries:
                self.retry_count += 1
                logger.info(f"重试{self.retry_count}/{self.max_retries}: {operation}")
                return self._retry_operation(operation)
            else:
                return self._fallback_operation(operation)
        else:  # CRITICAL
            logger.critical(f"配置严重错误: {error.message}")
            raise error
    
    def _handle_file_error(self, error: Exception, operation: str) -> Optional[Any]:
        """处理文件错误"""
        logger.error(f"文件操作失败: {error}")
        
        # 尝试使用备用文件
        fallback_file = self.fallback_configs.get(operation)
        if fallback_file and Path(fallback_file).exists():
            logger.info(f"使用备用文件: {fallback_file}")
            return self._load_fallback_config(fallback_file)
        
        return None
    
    def _handle_network_error(self, error: Exception, operation: str) -> Optional[Any]:
        """处理网络错误"""
        logger.error(f"网络操作失败: {error}")
        
        if self.enable_retry and self.retry_count < self.max_retries:
            self.retry_count += 1
            wait_time = 2 ** self.retry_count  # 指数退避
            logger.info(f"等待{wait_time}秒后重试...")
            time.sleep(wait_time)
            return self._retry_operation(operation)
        
        return None
    
    def add_fallback(self, operation: str, fallback_config: Any):
        """添加降级配置"""
        self.fallback_configs[operation] = fallback_config
```

## 🎯 任务2：实现高级配置验证系统

### 2.1 基于Schema的配置验证

#### JSON Schema验证器

```python
import jsonschema
from jsonschema import validate, ValidationError
from typing import Dict, Any, Optional, List
from datetime import datetime

class SchemaBasedValidator:
    """基于JSON Schema的配置验证器"""
    
    def __init__(self):
        self.schemas = {}
        self.schema_versions = {}
        self.validation_cache = {}
        
    def register_schema(self, 
                       schema_name: str, 
                       schema: Dict[str, Any],
                       version: str = "1.0.0"):
        """注册配置Schema"""
        self.schemas[schema_name] = schema
        self.schema_versions[schema_name] = {
            'version': version,
            'registered_at': datetime.now(),
            'schema': schema
        }
        
        # 验证Schema本身的有效性
        try:
            jsonschema.Draft7Validator.check_schema(schema)
            logger.info(f"Schema '{schema_name}' v{version} 注册成功")
        except jsonschema.SchemaError as e:
            logger.error(f"Schema '{schema_name}' 无效: {e}")
            raise
    
    def validate_config(self, 
                       schema_name: str, 
                       config: Dict[str, Any],
                       strict: bool = False) -> Dict[str, Any]:
        """验证配置是否符合Schema"""
        schema = self.schemas.get(schema_name)
        if not schema:
            raise ValueError(f"Schema '{schema_name}' 未注册")
        
        cache_key = f"{schema_name}:{hash(str(config))}"
        if cache_key in self.validation_cache:
            return self.validation_cache[cache_key]
        
        try:
            # 执行验证
            validate(instance=config, schema=schema)
            
            result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'schema_name': schema_name,
                'schema_version': self.schema_versions[schema_name]['version']
            }
            
            # 如果启用严格模式，进行额外检查
            if strict:
                warnings = self._strict_validation(config, schema)
                result['warnings'] = warnings
            
            self.validation_cache[cache_key] = result
            return result
            
        except ValidationError as e:
            error_info = {
                'path': list(e.path),
                'message': e.message,
                'validator': e.validator,
                'validator_value': e.validator_value
            }
            
            result = {
                'valid': False,
                'errors': [error_info],
                'warnings': [],
                'schema_name': schema_name
            }
            
            self.validation_cache[cache_key] = result
            return result
    
    def generate_schema_from_config(self, 
                                   config: Dict[str, Any],
                                   schema_name: str = None) -> Dict[str, Any]:
        """从配置生成Schema"""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for key, value in config.items():
            prop_schema = self._infer_schema(value)
            schema['properties'][key] = prop_schema
            
            # 如果值不是None，设为必需字段
            if value is not None:
                schema['required'].append(key)
        
        if schema_name:
            self.register_schema(schema_name, schema)
        
        return schema
    
    def _infer_schema(self, value: Any) -> Dict[str, Any]:
        """推断值的Schema"""
        if isinstance(value, bool):
            return {"type": "boolean"}
        elif isinstance(value, int):
            return {"type": "integer"}
        elif isinstance(value, float):
            return {"type": "number"}
        elif isinstance(value, str):
            return {"type": "string"}
        elif isinstance(value, list):
            if value:
                # 推断列表元素类型
                item_schema = self._infer_schema(value[0])
                return {
                    "type": "array",
                    "items": item_schema
                }
            return {"type": "array"}
        elif isinstance(value, dict):
            properties = {}
            for k, v in value.items():
                properties[k] = self._infer_schema(v)
            
            return {
                "type": "object",
                "properties": properties
            }
        else:
            return {"type": "string"}  # 默认字符串类型
```

### 2.2 配置依赖分析和验证

#### 依赖关系分析器

```python
from typing import Dict, List, Set, Optional
from collections import defaultdict
import networkx as nx

class DependencyAnalyzer:
    """配置依赖分析器"""
    
    def __init__(self):
        self.dependency_graph = nx.DiGraph()
        self.config_values = {}
        self.cyclic_dependencies = []
        
    def add_config(self, config_path: str, value: Any, dependencies: List[str] = None):
        """添加配置项及其依赖"""
        self.config_values[config_path] = value
        self.dependency_graph.add_node(config_path)
        
        if dependencies:
            for dep in dependencies:
                self.dependency_graph.add_edge(config_path, dep)
    
    def analyze_dependencies(self) -> Dict[str, Any]:
        """分析依赖关系"""
        # 检测循环依赖
        self.cyclic_dependencies = list(nx.simple_cycles(self.dependency_graph))
        
        # 计算拓扑排序（如果无环）
        try:
            topological_order = list(nx.topological_sort(self.dependency_graph))
            has_cycles = False
        except nx.NetworkXUnfeasible:
            topological_order = []
            has_cycles = True
        
        # 计算依赖深度
        depths = {}
        for node in self.dependency_graph.nodes():
            if not list(self.dependency_graph.predecessors(node)):
                depths[node] = 0
            else:
                depths[node] = max(
                    depths[p] + 1 for p in self.dependency_graph.predecessors(node)
                    if p in depths
                )
        
        return {
            'has_cycles': has_cycles,
            'cyclic_dependencies': self.cyclic_dependencies,
            'topological_order': topological_order,
            'dependency_depths': depths,
            'total_configs': self.dependency_graph.number_of_nodes(),
            'total_dependencies': self.dependency_graph.number_of_edges(),
            'max_depth': max(depths.values()) if depths else 0
        }
    
    def resolve_dependencies(self) -> Dict[str, Any]:
        """解析依赖关系并生成最终配置"""
        analysis = self.analyze_dependencies()
        
        if analysis['has_cycles']:
            raise ValueError(f"存在循环依赖: {analysis['cyclic_dependencies']}")
        
        resolved_config = {}
        
        # 按拓扑顺序解析配置
        for config_path in analysis['topological_order']:
            value = self.config_values[config_path]
            
            # 如果需要，可以在这里注入依赖值
            resolved_config[config_path] = value
        
        return resolved_config
```

### 2.3 配置安全验证

#### 敏感配置检测器

```python
import re
from typing import Dict, List, Any, Optional

class SecurityValidator:
    """配置安全验证器"""
    
    # 敏感模式定义
    SENSITIVE_PATTERNS = {
        'password': re.compile(r'(?i)password|passwd|pwd'),
        'api_key': re.compile(r'(?i)api[._-]?key|apikey'),
        'secret': re.compile(r'(?i)secret|private[._-]?key'),
        'token': re.compile(r'(?i)token|auth[._-]?token|access[._-]?token'),
    }
    
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key
        self.detected_sensitive = []
        self.encrypted_values = {}
        
    def scan_config(self, config: Dict[str, Any], path: str = '') -> List[Dict[str, Any]]:
        """扫描配置中的敏感信息"""
        sensitive_items = []
        
        for key, value in config.items():
            current_path = f"{path}.{key}" if path else key
            
            # 检查键名是否敏感
            key_matches = self._check_sensitive_key(key)
            
            # 检查值是否敏感
            value_matches = self._check_sensitive_value(value)
            
            if key_matches or value_matches:
                item = {
                    'path': current_path,
                    'key': key,
                    'value': self._mask_value(value) if value_matches else value,
                    'key_matches': key_matches,
                    'value_matches': value_matches,
                    'risk_level': self._calculate_risk_level(key_matches, value_matches),
                    'suggestion': self._generate_suggestion(key_matches, value_matches)
                }
                sensitive_items.append(item)
                self.detected_sensitive.append(item)
            
            # 递归扫描嵌套结构
            if isinstance(value, dict):
                nested_items = self.scan_config(value, current_path)
                sensitive_items.extend(nested_items)
        
        return sensitive_items
    
    def _check_sensitive_key(self, key: str) -> List[str]:
        """检查键名是否敏感"""
        matches = []
        
        for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
            if pattern.search(key):
                matches.append(pattern_name)
        
        return matches
    
    def _check_sensitive_value(self, value: Any) -> List[str]:
        """检查值是否敏感"""
        matches = []
        
        if not isinstance(value, str):
            return matches
        
        # 检查高风险值模式
        if value.strip() == '':
            matches.append('empty_string')
        elif value.lower() in ['changeme', 'password', 'secret', 'key', 'token']:
            matches.append('default_value')
        elif len(value) < 8:
            matches.append('short_value')
        elif not any(c in value for c in '!@#$%^&*()'):
            matches.append('no_special_chars')
        
        # 检查值是否看起来像敏感数据
        if self._looks_like_sensitive_data(value):
            matches.append('sensitive_looking')
        
        return matches
    
    def _looks_like_sensitive_data(self, value: str) -> bool:
        """检查值是否看起来像敏感数据"""
        # 长字符串可能是密钥或令牌
        if len(value) >= 20 and ' ' not in value:
            return True
        
        # 包含特殊字符组合
        special_count = sum(1 for c in value if not c.isalnum())
        if special_count >= 3 and len(value) >= 10:
            return True
        
        return False
    
    def _mask_value(self, value: Any) -> str:
        """掩码敏感值"""
        if not isinstance(value, str):
            return str(value)
        
        if len(value) <= 4:
            return '*' * len(value)
        else:
            visible = min(4, len(value) // 4)
            return value[:visible] + '*' * (len(value) - visible)
    
    def generate_security_report(self) -> Dict[str, Any]:
        """生成安全报告"""
        total_sensitive = len(self.detected_sensitive)
        risk_levels = {'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        
        for item in self.detected_sensitive:
            risk_levels[item['risk_level']] += 1
        
        return {
            'total_sensitive_items': total_sensitive,
            'risk_distribution': risk_levels,
            'high_risk_items': [item for item in self.detected_sensitive 
                               if item['risk_level'] == 'high'],
            'encrypted_values': len(self.encrypted_values),
            'recommendations': self._generate_security_recommendations()
        }
```

## 🎯 任务3：实现智能配置模板系统

### 3.1 高级模板功能

#### 支持条件表达式和循环的模板引擎

```python
import re
from typing import Dict, Any, Optional, Callable

class AdvancedTemplateEngine:
    """高级模板引擎"""
    
    def __init__(self):
        self.variables = {}
        self.functions = {
            'upper': str.upper,
            'lower': str.lower,
            'capitalize': str.capitalize,
            'len': len,
            'join': lambda sep, items: sep.join(str(i) for i in items),
            'default': lambda value, default: value if value is not None else default
        }
        self.macros = {}
        
    def register_function(self, name: str, func: Callable):
        """注册自定义函数"""
        self.functions[name] = func
    
    def render(self, template: str, context: Optional[Dict[str, Any]] = None) -> str:
        """渲染模板"""
        if context:
            self.variables.update(context)
        
        # 处理条件表达式
        template = self._process_conditionals(template)
        
        # 处理循环表达式
        template = self._process_loops(template)
        
        # 处理变量替换
        template = self._substitute_variables(template)
        
        # 处理函数调用
        template = self._evaluate_functions(template)
        
        return template
    
    def _process_conditionals(self, template: str) -> str:
        """处理条件表达式"""
        # 支持 {{if condition}} ... {{else}} ... {{endif}}
        pattern = r'\{\{\s*if\s+(.+?)\s*\}\}(.*?)(?:\{\{\s*else\s*\}\}(.*?))?\{\{\s*endif\s*\}\}'
        
        def replace_conditional(match):
            condition_expr = match.group(1).strip()
            true_block = match.group(2).strip()
            false_block = match.group(3).strip() if match.group(3) else ''
            
            try:
                condition = self._evaluate_expression(condition_expr)
                return true_block if condition else false_block
            except Exception as e:
                return f"条件表达式错误: {e}"
        
        # 需要多次处理嵌套条件
        while True:
            new_template = re.sub(pattern, replace_conditional, template, flags=re.DOTALL)
            if new_template == template:
                break
            template = new_template
        
        return template
    
    def _process_loops(self, template: str) -> str:
        """处理循环表达式"""
        # 支持 {{for item in items}} ... {{endfor}}
        pattern = r'\{\{\s*for\s+(\w+)\s+in\s+(.+?)\s*\}\}(.*?)\{\{\s*endfor\s*\}\}'
        
        def replace_loop(match):
            item_var = match.group(1).strip()
            items_expr = match.group(2).strip()
            loop_body = match.group(3).strip()
            
            try:
                items = self._evaluate_expression(items_expr)
                if not isinstance(items, (list, tuple, dict)):
                    return f"循环表达式错误: {items_expr} 不是可迭代对象"
                
                results = []
                if isinstance(items, dict):
                    for key, value in items.items():
                        loop_context = {item_var: {'key': key, 'value': value}}
                        result = self.render(loop_body, loop_context)
                        results.append(result)
                else:
                    for item in items:
                        loop_context = {item_var: item}
                        result = self.render(loop_body, loop_context)
                        results.append(result)
                
                return ''.join(results)
            except Exception as e:
                return f"循环表达式错误: {e}"
        
        # 需要多次处理嵌套循环
        while True:
            new_template = re.sub(pattern, replace_loop, template, flags=re.DOTALL)
            if new_template == template:
                break
            template = new_template
        
        return template
    
    def _substitute_variables(self, template: str) -> str:
        """替换变量"""
        # 支持 ${var} 和 ${var:default} 格式
        pattern = r'\$\{(\w+)(?::([^}]+))?\}'
        
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2)
            
            if var_name in self.variables:
                value = self.variables[var_name]
                return str(value) if value is not None else (default_value or '')
            else:
                return default_value or ''
        
        return re.sub(pattern, replace_var, template)
    
    def validate_template(self, template: str) -> Dict[str, Any]:
        """验证模板语法"""
        issues = []
        
        # 检查未闭合的标签
        tag_pairs = [
            ('if', 'endif'),
            ('for', 'endfor'),
        ]
        
        for start_tag, end_tag in tag_pairs:
            start_count = len(re.findall(r'\{\{\s*' + start_tag + r'\s', template))
            end_count = len(re.findall(r'\{\{\s*' + end_tag + r'\s*\}\}', template))
            
            if start_count != end_count:
                issues.append({
                    'type': 'unclosed_tag',
                    'tag': start_tag,
                    'start_count': start_count,
                    'end_count': end_count,
                    'message': f'{{{{{start_tag}}}}} 和 {{{{end_tag}}}} 数量不匹配'
                })
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
```

### 3.2 动态模板生成

#### 智能模板生成器

```python
from typing import Dict, List, Any, Optional
import json
import yaml

class SmartTemplateGenerator:
    """智能模板生成器"""
    
    def __init__(self):
        self.template_patterns = {}
        self.inference_rules = []
        
    def analyze_config_structure(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """分析配置结构"""
        structure_info = {
            'total_keys': 0,
            'max_depth': 0,
            'key_patterns': {},
            'value_types': {},
            'nested_structures': []
        }
        
        def analyze_node(node: Any, path: str = '', depth: int = 0):
            if depth > structure_info['max_depth']:
                structure_info['max_depth'] = depth
            
            if isinstance(node, dict):
                structure_info['total_keys'] += len(node)
                
                for key, value in node.items():
                    # 记录键名模式
                    key_lower = key.lower()
                    pattern = self._classify_key_pattern(key_lower)
                    structure_info['key_patterns'][pattern] = structure_info['key_patterns'].get(pattern, 0) + 1
                    
                    # 记录值类型
                    value_type = type(value).__name__
                    structure_info['value_types'][value_type] = structure_info['value_types'].get(value_type, 0) + 1
                    
                    # 递归分析嵌套结构
                    new_path = f"{path}.{key}" if path else key
                    analyze_node(value, new_path, depth + 1)
                
                if depth > 0:  # 排除根节点
                    structure_info['nested_structures'].append({
                        'path': path,
                        'depth': depth,
                        'size': len(node)
                    })
                    
            elif isinstance(node, list):
                if node:
                    # 分析列表元素类型
                    elem_types = set(type(item).__name__ for item in node)
                    structure_info['nested_structures'].append({
                        'path': path,
                        'depth': depth,
                        'type': 'list',
                        'size': len(node),
                        'element_types': list(elem_types)
                    })
        
        analyze_node(config)
        return structure_info
    
    def _classify_key_pattern(self, key: str) -> str:
        """分类键名模式"""
        patterns = {
            'url': ['url', 'uri', 'endpoint', 'host', 'domain'],
            'auth': ['auth', 'password', 'token', 'secret', 'key', 'credential'],
            'database': ['db', 'database', 'host', 'port', 'name', 'user'],
            'server': ['server', 'host', 'port', 'address', 'ip'],
            'time': ['time', 'timeout', 'interval', 'delay', 'duration'],
            'log': ['log', 'logger', 'level', 'file', 'path'],
            'cache': ['cache', 'ttl', 'expire', 'memory', 'size']
        }
        
        for pattern, keywords in patterns.items():
            if any(keyword in key for keyword in keywords):
                return pattern
        
        return 'other'
    
    def generate_template(self, 
                         config: Dict[str, Any], 
                         template_type: str = 'full') -> str:
        """生成配置模板"""
        if template_type == 'full':
            return self._generate_full_template(config)
        elif template_type == 'minimal':
            return self._generate_minimal_template(config)
        elif template_type == 'commented':
            return self._generate_commented_template(config)
        else:
            return self._generate_full_template(config)
    
    def _generate_full_template(self, config: Dict[str, Any]) -> str:
        """生成完整模板"""
        template_lines = ["# 完整配置模板", "# 所有配置项都已列出，包含默认值", ""]
        
        def generate_section(node: Any, indent: int = 0, path: str = ''):
            if isinstance(node, dict):
                for key, value in node.items():
                    new_path = f"{path}.{key}" if path else key
                    
                    # 推断注释
                    comment = self._infer_comment(key, value, new_path)
                    if comment:
                        template_lines.append(" " * indent + f"# {comment}")
                    
                    if isinstance(value, dict):
                        template_lines.append(" " * indent + f"{key}:")
                        generate_section(value, indent + 2, new_path)
                    elif isinstance(value, list):
                        template_lines.append(" " * indent + f"{key}:")
                        if value and isinstance(value[0], dict):
                            # 列表中的字典
                            template_lines.append(" " * (indent + 2) + "-")
                            generate_section(value[0], indent + 4, new_path + "[0]")
                        else:
                            # 简单列表
                            example = value[0] if value else "example_value"
                            template_lines.append(" " * (indent + 2) + f"- {example}")
                    else:
                        # 简单值
                        template_lines.append(" " * indent + f"{key}: {self._format_value(value)}")
                        
                    template_lines.append("")  # 空行分隔
        
        generate_section(config)
        return '\n'.join(template_lines)
```

## 🎯 任务4：集成配置管理和监控

### 4.1 配置版本控制和变更管理

#### Git风格的版本控制系统

```python
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ConfigVersion:
    """配置版本"""
    version_id: str
    timestamp: datetime
    author: str
    message: str
    config: Dict[str, Any]
    parent_version: Optional[str] = None
    tags: List[str] = None

class ConfigVersionControl:
    """配置版本控制系统"""
    
    def __init__(self, storage_path: str = ".config_versions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # 版本索引
        self.versions = {}
        self.current_version = None
        self.branches = {'main': None}
        self.current_branch = 'main'
    
    def commit(self, 
               config: Dict[str, Any], 
               author: str, 
               message: str,
               tags: List[str] = None) -> str:
        """提交新配置版本"""
        # 生成版本ID
        import hashlib
        config_str = json.dumps(config, sort_keys=True)
        version_id = hashlib.sha256(config_str.encode()).hexdigest()[:16]
        
        # 检查是否已存在相同版本
        if version_id in self.versions:
            logger.info(f"配置未变化，跳过提交 (版本: {version_id})")
            return version_id
        
        # 创建新版本
        version = ConfigVersion(
            version_id=version_id,
            timestamp=datetime.now(),
            author=author,
            message=message,
            config=config,
            parent_version=self.current_version,
            tags=tags or []
        )
        
        # 保存版本
        self._save_version(version)
        
        # 更新状态
        self.versions[version_id] = version
        self.current_version = version_id
        self.branches[self.current_branch] = version_id
        
        logger.info(f"配置已提交 (版本: {version_id})")
        return version_id
    
    def _save_version(self, version: ConfigVersion):
        """保存版本到文件"""
        file_path = self.storage_path / f"version_{version.version_id}.json"
        
        data = {
            'version_id': version.version_id,
            'timestamp': version.timestamp.isoformat(),
            'author': version.author,
            'message': version.message,
            'config': version.config,
            'parent_version': version.parent_version,
            'tags': version.tags
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def checkout(self, version_id: str) -> Optional[Dict[str, Any]]:
        """检出特定版本"""
        if version_id not in self.versions:
            logger.error(f"版本不存在: {version_id}")
            return None
        
        version = self.versions[version_id]
        self.current_version = version_id
        
        logger.info(f"已检出版本: {version_id} - {version.message}")
        return version.config
    
    def diff(self, version_a: str, version_b: str) -> Dict[str, Any]:
        """比较两个版本的差异"""
        if version_a not in self.versions or version_b not in self.versions:
            return {'error': '版本不存在'}
        
        config_a = self.versions[version_a].config
        config_b = self.versions[version_b].config
        
        return self._compare_configs(config_a, config_b)
    
    def _compare_configs(self, config_a: Dict[str, Any], config_b: Dict[str, Any]) -> Dict[str, Any]:
        """比较两个配置的差异"""
        diff_result = {
            'added': [],
            'removed': [],
            'modified': [],
            'unchanged': []
        }
        
        def compare_dicts(dict_a: Dict, dict_b: Dict, path: str = ''):
            all_keys = set(dict_a.keys()) | set(dict_b.keys())
            
            for key in all_keys:
                new_path = f"{path}.{key}" if path else key
                
                if key in dict_a and key not in dict_b:
                    diff_result['removed'].append({
                        'path': new_path,
                        'old_value': dict_a[key]
                    })
                elif key not in dict_a and key in dict_b:
                    diff_result['added'].append({
                        'path': new_path,
                        'new_value': dict_b[key]
                    })
                else:
                    value_a = dict_a[key]
                    value_b = dict_b[key]
                    
                    if isinstance(value_a, dict) and isinstance(value_b, dict):
                        compare_dicts(value_a, value_b, new_path)
                    elif value_a != value_b:
                        diff_result['modified'].append({
                            'path': new_path,
                            'old_value': value_a,
                            'new_value': value_b
                        })
                    else:
                        diff_result['unchanged'].append(new_path)
        
        compare_dicts(config_a, config_b)
        return diff_result
```

### 4.2 配置监控和告警

#### 配置性能监控器

```python
import time
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class ConfigMonitor:
    """配置监控器"""
    
    def __init__(self, alert_thresholds: Dict[str, float] = None):
        self.metrics = {
            'load_times': [],
            'memory_usage': [],
            'error_rates': [],
            'cache_hits': []
        }
        
        self.alerts = []
        self.alert_thresholds = alert_thresholds or {
            'load_time_ms': 1000,  # 加载时间超过1秒
            'memory_mb': 100,       # 内存使用超过100MB
            'error_rate': 0.1,      # 错误率超过10%
            'cache_hit_rate': 0.8   # 缓存命中率低于80%
        }
        
        self.start_time = datetime.now()
        
    def record_load_time(self, config_size: int, load_time_ms: float):
        """记录配置加载时间"""
        metric = {
            'timestamp': datetime.now(),
            'config_size': config_size,
            'load_time_ms': load_time_ms,
            'throughput_kb_per_sec': (config_size / 1024) / (load_time_ms / 1000) if load_time_ms > 0 else 0
        }
        
        self.metrics['load_times'].append(metric)
        
        # 检查是否触发告警
        if load_time_ms > self.alert_thresholds['load_time_ms']:
            self._create_alert(
                type='slow_load',
                severity='warning',
                message=f'配置加载时间过长: {load_time_ms:.2f}ms',
                details=metric
            )
    
    def record_memory_usage(self):
        """记录内存使用情况"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        metric = {
            'timestamp': datetime.now(),
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent()
        }
        
        self.metrics['memory_usage'].append(metric)
        
        # 检查是否触发告警
        if metric['rss_mb'] > self.alert_thresholds['memory_mb']:
            self._create_alert(
                type='high_memory',
                severity='warning',
                message=f'内存使用过高: {metric["rss_mb"]:.2f}MB',
                details=metric
            )
    
    def record_error(self, error_type: str, operation: str):
        """记录错误"""
        # 更新错误率
        total_ops = len(self.metrics.get('operations', [])) + 1
        error_count = sum(1 for e in self.metrics.get('errors', []) 
                         if e['timestamp'] > datetime.now() - timedelta(minutes=5))
        
        error_rate = error_count / max(total_ops, 1)
        
        metric = {
            'timestamp': datetime.now(),
            'error_type': error_type,
            'operation': operation,
            'error_rate': error_rate
        }
        
        if 'errors' not in self.metrics:
            self.metrics['errors'] = []
        self.metrics['errors'].append(metric)
        
        # 检查是否触发告警
        if error_rate > self.alert_thresholds['error_rate']:
            self._create_alert(
                type='high_error_rate',
                severity='error',
                message=f'错误率过高: {error_rate:.2%}',
                details=metric
            )
    
    def _create_alert(self, 
                     type: str, 
                     severity: str, 
                     message: str, 
                     details: Dict[str, Any]):
        """创建告警"""
        alert = {
            'id': len(self.alerts) + 1,
            'type': type,
            'severity': severity,
            'message': message,
            'timestamp': datetime.now(),
            'details': details,
            'acknowledged': False,
            'resolved': False
        }
        
        self.alerts.append(alert)
        logger.warning(f"[{severity.upper()}] {message}")
    
    def get_metrics_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """获取指标摘要"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        # 加载时间统计
        recent_loads = [m for m in self.metrics.get('load_times', []) 
                       if m['timestamp'] > cutoff_time]
        
        load_stats = {}
        if recent_loads:
            load_times = [m['load_time_ms'] for m in recent_loads]
            
            load_stats = {
                'count': len(recent_loads),
                'avg_load_time_ms': sum(load_times) / len(load_times),
                'max_load_time_ms': max(load_times),
                'min_load_time_ms': min(load_times),
                'p95_load_time_ms': sorted(load_times)[int(len(load_times) * 0.95)]
            }
        
        # 内存使用统计
        recent_memory = [m for m in self.metrics.get('memory_usage', []) 
                        if m['timestamp'] > cutoff_time]
        
        memory_stats = {}
        if recent_memory:
            rss_values = [m['rss_mb'] for m in recent_memory]
            
            memory_stats = {
                'avg_rss_mb': sum(rss_values) / len(rss_values),
                'max_rss_mb': max(rss_values),
                'current_rss_mb': rss_values[-1] if rss_values else 0
            }
        
        return {
            'time_window_minutes': time_window_minutes,
            'load_stats': load_stats,
            'memory_stats': memory_stats,
            'active_alerts': len(self.get_active_alerts()),
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds()
        }
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        return [a for a in self.alerts if not a['resolved']]
```

## 📝 实现要点总结

### 设计原则
1. **约定优于配置**：提供合理的默认值，减少必需配置项
2. **分层覆盖**：清晰的配置优先级，避免歧义
3. **失败快速**：配置错误时立即报错，避免使用错误配置
4. **安全第一**：敏感配置加密存储，最小权限访问

### 性能优化
1. **缓存机制**：减少重复加载和解析开销
2. **懒加载**：按需加载配置，减少启动时间
3. **增量更新**：只重新加载变化的部分
4. **并行加载**：多个配置源并行加载

### 可维护性
1. **模块化设计**：配置加载、合并、验证、模板职责清晰
2. **可扩展性**：易于添加新的配置源、验证规则、模板功能
3. **可观测性**：丰富的监控指标、日志、追踪支持
4. **文档化**：每个配置项都有详细说明和示例

### 安全性
1. **敏感信息保护**：密码、密钥等敏感配置加密存储
2. **访问控制**：配置操作需要权限验证
3. **输入验证**：所有配置输入必须验证，防止注入攻击
4. **审计追踪**：所有配置变更可追溯、可审计

## 🔍 测试策略

### 单元测试
- 每个配置组件独立测试
- 边界条件和异常场景测试
- 性能基准测试

### 集成测试
- 多配置源集成测试
- 端到端配置加载流程测试
- 配置热更新测试

### 安全测试
- 敏感信息泄露测试
- 注入攻击防护测试
- 权限控制测试

### 性能测试
- 大配置文件加载性能测试
- 高并发配置访问测试
- 内存使用和泄漏测试

## 🚀 部署建议

### 开发环境
- 使用本地配置文件
- 启用详细日志
- 开启调试模式

### 测试环境
- 使用环境变量覆盖配置
- 启用配置验证
- 监控配置加载性能

### 生产环境
- 使用配置中心或密钥管理服务
- 启用配置加密
- 配置访问控制和审计
- 监控和告警

---

**注意**：以上为参考实现，实际项目中应根据具体需求调整实现细节。建议先实现核心功能，再逐步添加高级特性。