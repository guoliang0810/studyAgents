#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能状态管理演示代码
Day 16 - 第63节课：技能状态管理

本演示代码展示了DeerFlow Agent系统中技能状态管理的核心实现，包括：
1. SkillState数据类：定义技能状态的字段和计算属性
2. SkillStateManager：技能状态管理器，支持加载、保存、更新状态
3. 健康度评估算法：基于成功率、使用频率、响应时间的综合健康度评分
4. 状态持久化：JSON格式的状态存储和恢复
5. 实时监控：技能状态变化跟踪和异常检测

学习目标：
- 掌握技能状态数据类的设计方法
- 理解状态管理器的架构和实现
- 能够实现健康度评估算法
- 能够设计状态持久化方案
- 能够构建简单的技能状态监控系统
"""

import os
import sys
import json
import time
import asyncio
import logging
import dataclasses
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import statistics
from pathlib import Path

# ============================================================================
# 枚举和常量定义
# ============================================================================

class SkillStatus(Enum):
    """技能状态枚举"""
    IDLE = "idle"            # 空闲
    LOADING = "loading"      # 加载中
    READY = "ready"          # 准备就绪
    EXECUTING = "executing"  # 执行中
    ERROR = "error"          # 错误
    DISABLED = "disabled"    # 已禁用


class HealthLevel(Enum):
    """健康度等级"""
    CRITICAL = "critical"    # 危急：0-0.2
    POOR = "poor"            # 差：0.2-0.5
    FAIR = "fair"            # 一般：0.5-0.8
    GOOD = "good"            # 良好：0.8-0.95
    EXCELLENT = "excellent"  # 优秀：0.95-1.0


# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class SkillState:
    """技能状态数据类
    
    表示单个技能的状态信息，包括使用统计、性能指标和健康度评估。
    
    Attributes:
        skill_name: 技能名称（唯一标识）
        version: 技能版本
        enabled: 是否启用
        last_used: 最后使用时间（Unix时间戳）
        usage_count: 总使用次数
        success_count: 成功次数
        failure_count: 失败次数
        avg_execution_time: 平均执行时间（秒）
        current_status: 当前状态（SkillStatus枚举值）
        error_message: 错误信息（如果有）
        created_at: 状态创建时间
        last_updated: 最后更新时间
        tags: 技能标签（用于分类）
    """
    
    skill_name: str
    version: str = "1.0.0"
    enabled: bool = True
    last_used: float = 0.0
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_execution_time: float = 0.0
    current_status: str = SkillStatus.IDLE.value
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    
    @property
    def total_attempts(self) -> int:
        """总尝试次数"""
        return self.success_count + self.failure_count
    
    @property
    def success_rate(self) -> float:
        """计算成功率（0.0到1.0）"""
        if self.total_attempts == 0:
            return 0.0
        return self.success_count / self.total_attempts
    
    @property
    def availability(self) -> float:
        """可用性得分（基于启用状态和错误状态）"""
        if not self.enabled:
            return 0.0
        if self.current_status == SkillStatus.ERROR.value:
            return 0.3
        if self.current_status == SkillStatus.DISABLED.value:
            return 0.5
        return 1.0
    
    @property
    def performance_score(self) -> float:
        """性能得分（基于响应时间）"""
        if self.avg_execution_time <= 0:
            return 1.0
        
        # 响应时间评分：小于1秒为满分，超过10秒为0分
        if self.avg_execution_time < 1.0:
            return 1.0
        elif self.avg_execution_time > 10.0:
            return 0.0
        else:
            return 1.0 - (self.avg_execution_time - 1.0) / 9.0
    
    @property
    def usage_score(self) -> float:
        """使用频率得分（基于使用次数）"""
        if self.usage_count == 0:
            return 0.5  # 未使用的技能给中等分数
        
        # 使用次数评分：超过100次为满分
        return min(self.usage_count / 100.0, 1.0)
    
    @property
    def health_score(self) -> float:
        """综合健康度得分（0.0到1.0）
        
        健康度计算公式：
        健康度 = 成功率权重 × 成功率 + 可用性权重 × 可用性 + 
                性能权重 × 性能得分 + 使用权重 × 使用频率得分
        
        权重分配：
        - 成功率：0.4（最重要）
        - 可用性：0.3（次重要）
        - 性能：0.2（重要）
        - 使用频率：0.1（参考）
        """
        weights = {
            'success_rate': 0.4,
            'availability': 0.3,
            'performance': 0.2,
            'usage': 0.1
        }
        
        scores = {
            'success_rate': self.success_rate,
            'availability': self.availability,
            'performance': self.performance_score,
            'usage': self.usage_score
        }
        
        # 计算加权平均
        total_score = 0.0
        for key, weight in weights.items():
            total_score += scores[key] * weight
        
        return round(total_score, 3)
    
    @property
    def health_level(self) -> HealthLevel:
        """健康度等级"""
        score = self.health_score
        
        if score >= 0.95:
            return HealthLevel.EXCELLENT
        elif score >= 0.8:
            return HealthLevel.GOOD
        elif score >= 0.5:
            return HealthLevel.FAIR
        elif score >= 0.2:
            return HealthLevel.POOR
        else:
            return HealthLevel.CRITICAL
    
    @property
    def uptime(self) -> float:
        """运行时间（从创建到现在）"""
        return time.time() - self.created_at
    
    @property
    def idle_time(self) -> float:
        """空闲时间（从最后使用到现在）"""
        if self.last_used == 0:
            return self.uptime
        return time.time() - self.last_used
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        data = dataclasses.asdict(self)
        # 添加计算属性
        data['success_rate'] = self.success_rate
        data['health_score'] = self.health_score
        data['health_level'] = self.health_level.value
        data['total_attempts'] = self.total_attempts
        return data
    
    def update_from_execution(self, success: bool, execution_time: float):
        """根据执行结果更新状态
        
        Args:
            success: 是否执行成功
            execution_time: 执行时间（秒）
        """
        # 更新使用统计
        self.last_used = time.time()
        self.usage_count += 1
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        # 更新平均执行时间（指数移动平均）
        if self.total_attempts == 1:
            self.avg_execution_time = execution_time
        else:
            # EMA系数：0.3，给予新数据更高权重
            alpha = 0.3
            self.avg_execution_time = (
                alpha * execution_time + 
                (1 - alpha) * self.avg_execution_time
            )
        
        # 更新状态
        if success:
            self.current_status = SkillStatus.READY.value
            self.error_message = None
        else:
            self.current_status = SkillStatus.ERROR.value
            # 在实际应用中，这里可以记录详细错误信息
        
        self.last_updated = time.time()


# ============================================================================
# 状态管理器
# ============================================================================

class SkillStateManager:
    """技能状态管理器
    
    负责管理所有技能的状态，提供状态加载、保存、更新和查询功能。
    
    Features:
    1. 状态持久化：JSON格式存储，支持自动保存
    2. 并发安全：使用锁机制确保多线程/协程安全
    3. 状态监控：定期健康检查，自动更新状态
    4. 历史记录：保留技能状态变化历史
    5. 事件通知：支持状态变化事件订阅
    """
    
    def __init__(self, storage_path: str = "skill_states.json"):
        """
        Args:
            storage_path: 状态存储文件路径
        """
        self.storage_path = storage_path
        self.states: Dict[str, SkillState] = {}
        self.history: Dict[str, List[Dict]] = {}
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger("skill.state.manager")
        self.subscribers: List[callable] = []
        
        # 确保存储目录存在
        storage_dir = os.path.dirname(os.path.abspath(storage_path))
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)
        
        # 加载现有状态
        self.load_states()
        
        self.logger.info(f"技能状态管理器初始化完成，已加载 {len(self.states)} 个技能状态")
    
    def load_states(self) -> bool:
        """从存储文件加载技能状态"""
        try:
            if not os.path.exists(self.storage_path):
                self.logger.warning(f"状态文件不存在: {self.storage_path}，使用空状态")
                self.states = {}
                return True
            
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.states = {}
            for skill_name, state_data in data.items():
                try:
                    # 创建SkillState实例
                    # 注意：需要处理可选字段
                    state = SkillState(
                        skill_name=skill_name,
                        version=state_data.get('version', '1.0.0'),
                        enabled=state_data.get('enabled', True),
                        last_used=state_data.get('last_used', 0.0),
                        usage_count=state_data.get('usage_count', 0),
                        success_count=state_data.get('success_count', 0),
                        failure_count=state_data.get('failure_count', 0),
                        avg_execution_time=state_data.get('avg_execution_time', 0.0),
                        current_status=state_data.get('current_status', SkillStatus.IDLE.value),
                        error_message=state_data.get('error_message'),
                        created_at=state_data.get('created_at', time.time()),
                        last_updated=state_data.get('last_updated', time.time()),
                        tags=state_data.get('tags', [])
                    )
                    self.states[skill_name] = state
                    
                    # 初始化历史记录
                    self.history[skill_name] = []
                    
                except Exception as e:
                    self.logger.error(f"加载技能 {skill_name} 状态失败: {e}")
                    continue
            
            self.logger.info(f"成功加载 {len(self.states)} 个技能状态")
            return True
            
        except json.JSONDecodeError as e:
            self.logger.error(f"状态文件格式错误: {e}")
            self.states = {}
            return False
        except Exception as e:
            self.logger.error(f"加载状态失败: {e}")
            self.states = {}
            return False
    
    def save_states(self) -> bool:
        """保存技能状态到存储文件"""
        try:
            data = {}
            for skill_name, state in self.states.items():
                data[skill_name] = state.to_dict()
            
            # 写入临时文件，然后原子重命名
            temp_path = f"{self.storage_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 原子替换
            os.replace(temp_path, self.storage_path)
            
            self.logger.debug(f"技能状态已保存到 {self.storage_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存状态失败: {e}")
            return False
    
    def get_state(self, skill_name: str) -> Optional[SkillState]:
        """获取技能状态"""
        return self.states.get(skill_name)
    
    def get_all_states(self) -> Dict[str, SkillState]:
        """获取所有技能状态"""
        return self.states.copy()
    
    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康度摘要"""
        if not self.states:
            return {"total": 0, "summary": {}}
        
        total_skills = len(self.states)
        enabled_skills = sum(1 for s in self.states.values() if s.enabled)
        error_skills = sum(1 for s in self.states.values() if s.current_status == SkillStatus.ERROR.value)
        
        # 健康度分布
        health_distribution = {level.value: 0 for level in HealthLevel}
        for state in self.states.values():
            health_distribution[state.health_level.value] += 1
        
        # 平均健康度
        avg_health = sum(s.health_score for s in self.states.values()) / total_skills
        
        return {
            "total_skills": total_skills,
            "enabled_skills": enabled_skills,
            "error_skills": error_skills,
            "avg_health_score": round(avg_health, 3),
            "health_distribution": health_distribution,
            "success_rate_avg": round(sum(s.success_rate for s in self.states.values()) / total_skills, 3),
            "avg_execution_time": round(sum(s.avg_execution_time for s in self.states.values()) / total_skills, 3)
        }
    
    async def update_state(self, skill_name: str, updates: Dict[str, Any], auto_save: bool = True) -> bool:
        """更新技能状态
        
        Args:
            skill_name: 技能名称
            updates: 更新字段字典
            auto_save: 是否自动保存
            
        Returns:
            是否更新成功
        """
        async with self.lock:
            try:
                # 获取或创建状态
                if skill_name not in self.states:
                    self.states[skill_name] = SkillState(
                        skill_name=skill_name,
                        created_at=time.time(),
                        last_updated=time.time()
                    )
                    self.history[skill_name] = []
                
                state = self.states[skill_name]
                
                # 记录历史状态（深拷贝）
                history_entry = {
                    'timestamp': time.time(),
                    'before': state.to_dict(),
                    'updates': updates.copy()
                }
                
                # 应用更新
                for key, value in updates.items():
                    if hasattr(state, key):
                        setattr(state, key, value)
                
                # 更新时间戳
                state.last_updated = time.time()
                
                # 记录更新后状态
                history_entry['after'] = state.to_dict()
                self.history[skill_name].append(history_entry)
                
                # 限制历史记录大小
                if len(self.history[skill_name]) > 100:
                    self.history[skill_name] = self.history[skill_name][-100:]
                
                # 通知订阅者
                await self._notify_subscribers(skill_name, updates)
                
                # 自动保存
                if auto_save:
                    self.save_states()
                
                self.logger.debug(f"技能 {skill_name} 状态已更新")
                return True
                
            except Exception as e:
                self.logger.error(f"更新技能 {skill_name} 状态失败: {e}")
                return False
    
    async def record_execution(self, skill_name: str, success: bool, execution_time: float) -> bool:
        """记录技能执行结果
        
        Args:
            skill_name: 技能名称
            success: 是否成功
            execution_time: 执行时间（秒）
            
        Returns:
            是否记录成功
        """
        async with self.lock:
            try:
                if skill_name not in self.states:
                    # 创建新状态
                    await self.update_state(skill_name, {
                        'skill_name': skill_name,
                        'created_at': time.time(),
                        'last_updated': time.time()
                    }, auto_save=False)
                
                state = self.states[skill_name]
                state.update_from_execution(success, execution_time)
                
                # 保存状态
                self.save_states()
                
                self.logger.debug(f"记录技能 {skill_name} 执行结果: 成功={success}, 时间={execution_time}s")
                return True
                
            except Exception as e:
                self.logger.error(f"记录技能 {skill_name} 执行结果失败: {e}")
                return False
    
    def enable_skill(self, skill_name: str) -> bool:
        """启用技能"""
        return asyncio.run(self.update_state(skill_name, {'enabled': True}))
    
    def disable_skill(self, skill_name: str) -> bool:
        """禁用技能"""
        return asyncio.run(self.update_state(skill_name, {'enabled': False}))
    
    def reset_skill_stats(self, skill_name: str) -> bool:
        """重置技能统计信息"""
        return asyncio.run(self.update_state(skill_name, {
            'usage_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'avg_execution_time': 0.0,
            'error_message': None,
            'current_status': SkillStatus.READY.value if self.states.get(skill_name, SkillState(skill_name)).enabled else SkillStatus.DISABLED.value
        }))
    
    def get_history(self, skill_name: str, limit: int = 10) -> List[Dict]:
        """获取技能状态历史记录"""
        return self.history.get(skill_name, [])[-limit:]
    
    def subscribe(self, callback: callable):
        """订阅状态变化事件"""
        self.subscribers.append(callback)
        self.logger.debug(f"添加状态变化订阅者，当前总数: {len(self.subscribers)}")
    
    async def _notify_subscribers(self, skill_name: str, updates: Dict[str, Any]):
        """通知订阅者状态变化"""
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(skill_name, updates)
                else:
                    callback(skill_name, updates)
            except Exception as e:
                self.logger.error(f"通知订阅者失败: {e}")
    
    def export_states(self, export_path: str) -> bool:
        """导出状态到文件"""
        try:
            data = {
                'export_time': time.time(),
                'export_version': '1.0',
                'states': {name: state.to_dict() for name, state in self.states.items()},
                'summary': self.get_health_summary()
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"技能状态已导出到 {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"导出状态失败: {e}")
            return False
    
    def import_states(self, import_path: str) -> bool:
        """从文件导入状态"""
        try:
            if not os.path.exists(import_path):
                self.logger.error(f"导入文件不存在: {import_path}")
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'states' not in data:
                self.logger.error("导入文件格式错误：缺少states字段")
                return False
            
            imported_count = 0
            for skill_name, state_data in data['states'].items():
                try:
                    await self.update_state(skill_name, state_data, auto_save=False)
                    imported_count += 1
                except Exception as e:
                    self.logger.warning(f"导入技能 {skill_name} 失败: {e}")
            
            # 保存所有导入的状态
            self.save_states()
            
            self.logger.info(f"成功导入 {imported_count} 个技能状态")
            return True
            
        except Exception as e:
            self.logger.error(f"导入状态失败: {e}")
            return False


# ============================================================================
# 健康监控器
# ============================================================================

class SkillHealthMonitor:
    """技能健康监控器
    
    定期检查技能健康状态，提供告警和自动恢复功能。
    """
    
    def __init__(self, state_manager: SkillStateManager, check_interval: float = 60.0):
        """
        Args:
            state_manager: 技能状态管理器
            check_interval: 检查间隔（秒）
        """
        self.state_manager = state_manager
        self.check_interval = check_interval
        self.is_monitoring = False
        self.monitor_task = None
        self.logger = logging.getLogger("skill.health.monitor")
        self.alert_handlers = []
        
    def add_alert_handler(self, handler: callable):
        """添加告警处理器"""
        self.alert_handlers.append(handler)
        self.logger.debug(f"添加告警处理器，当前总数: {len(self.alert_handlers)}")
    
    async def _check_health(self):
        """检查所有技能的健康状态"""
        self.logger.info("开始技能健康检查")
        
        states = self.state_manager.get_all_states()
        alerts = []
        
        for skill_name, state in states.items():
            # 检查健康度
            if state.health_level in [HealthLevel.CRITICAL, HealthLevel.POOR]:
                alert = {
                    'skill_name': skill_name,
                    'health_level': state.health_level.value,
                    'health_score': state.health_score,
                    'timestamp': time.time(),
                    'message': f"技能 {skill_name} 健康度{state.health_level.value} (得分: {state.health_score})"
                }
                alerts.append(alert)
                self.logger.warning(f"技能健康度告警: {skill_name} - {state.health_level.value}")
            
            # 检查错误状态
            if state.current_status == SkillStatus.ERROR.value:
                alert = {
                    'skill_name': skill_name,
                    'error_status': True,
                    'error_message': state.error_message,
                    'timestamp': time.time(),
                    'message': f"技能 {skill_name} 处于错误状态: {state.error_message}"
                }
                alerts.append(alert)
                self.logger.error(f"技能错误告警: {skill_name} - {state.error_message}")
            
            # 检查长时间未使用
            if state.idle_time > 7 * 24 * 3600:  # 7天
                alert = {
                    'skill_name': skill_name,
                    'idle_time': state.idle_time,
                    'timestamp': time.time(),
                    'message': f"技能 {skill_name} 已闲置 {state.idle_time/3600:.1f} 小时"
                }
                alerts.append(alert)
                self.logger.info(f"技能闲置告警: {skill_name} - 闲置 {state.idle_time/3600:.1f} 小时")
        
        # 处理告警
        for alert in alerts:
            await self._handle_alert(alert)
        
        self.logger.info(f"健康检查完成，发现 {len(alerts)} 个告警")
    
    async def _handle_alert(self, alert: Dict):
        """处理告警"""
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                self.logger.error(f"告警处理器失败: {e}")
    
    async def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            self.logger.warning("监控已经在运行")
            return
        
        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info(f"技能健康监控已启动，检查间隔: {self.check_interval}秒")
    
    async def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("技能健康监控已停止")
    
    async def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                await self._check_health()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                self.logger.info("监控循环被取消")
                break
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(self.check_interval)


# ============================================================================
# 演示函数
# ============================================================================

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

async def demo_basic_state_management():
    """演示基础状态管理"""
    print("=" * 60)
    print("演示：基础状态管理")
    print("=" * 60)
    
    # 创建状态管理器
    manager = SkillStateManager("demo_states.json")
    
    # 创建几个技能状态
    skills = ["text_generation", "image_recognition", "data_analysis"]
    
    for skill in skills:
        await manager.update_state(skill, {
            'version': '1.0.0',
            'enabled': True,
            'tags': ['ai', 'ml']
        })
    
    # 记录执行结果
    await manager.record_execution("text_generation", success=True, execution_time=0.5)
    await manager.record_execution("text_generation", success=True, execution_time=0.6)
    await manager.record_execution("text_generation", success=False, execution_time=2.0)
    
    await manager.record_execution("image_recognition", success=True, execution_time=1.2)
    
    # 获取并显示状态
    for skill in skills:
        state = manager.get_state(skill)
        if state:
            print(f"\n技能: {state.skill_name}")
            print(f"  健康度: {state.health_score} ({state.health_level.value})")
            print(f"  成功率: {state.success_rate:.1%}")
            print(f"  使用次数: {state.usage_count}")
            print(f"  平均执行时间: {state.avg_execution_time:.2f}s")
    
    # 显示健康度摘要
    summary = manager.get_health_summary()
    print(f"\n健康度摘要:")
    print(f"  总技能数: {summary['total_skills']}")
    print(f"  平均健康度: {summary['avg_health_score']}")
    print(f"  健康度分布: {summary['health_distribution']}")
    
    # 清理演示文件
    if os.path.exists("demo_states.json"):
        os.remove("demo_states.json")
    
    print("\n基础状态管理演示完成!")

async def demo_health_monitoring():
    """演示健康监控"""
    print("\n" + "=" * 60)
    print("演示：健康监控")
    print("=" * 60)
    
    # 创建状态管理器
    manager = SkillStateManager("monitor_demo.json")
    
    # 创建健康监控器
    monitor = SkillHealthMonitor(manager, check_interval=2.0)
    
    # 添加简单的告警处理器
    def simple_alert_handler(alert):
        print(f"[告警] {alert['message']}")
    
    monitor.add_alert_handler(simple_alert_handler)
    
    # 创建一些技能状态
    await manager.update_state("critical_skill", {
        'enabled': True,
        'success_count': 1,
        'failure_count': 9,  # 低成功率
        'avg_execution_time': 15.0,  # 高延迟
        'current_status': SkillStatus.READY.value
    })
    
    await manager.update_state("error_skill", {
        'enabled': True,
        'current_status': SkillStatus.ERROR.value,
        'error_message': "依赖服务不可用"
    })
    
    # 启动监控（短暂运行）
    await monitor.start_monitoring()
    print("健康监控已启动，等待检查...")
    await asyncio.sleep(5)  # 等待几次检查
    await monitor.stop_monitoring()
    
    # 清理演示文件
    if os.path.exists("monitor_demo.json"):
        os.remove("monitor_demo.json")
    
    print("健康监控演示完成!")

async def demo_advanced_features():
    """演示高级功能"""
    print("\n" + "=" * 60)
    print("演示：高级功能")
    print("=" * 60)
    
    manager = SkillStateManager("advanced_demo.json")
    
    # 1. 状态历史记录
    print("1. 状态历史记录演示")
    await manager.update_state("test_skill", {'enabled': True})
    await manager.update_state("test_skill", {'usage_count': 10})
    await manager.update_state("test_skill", {'current_status': SkillStatus.EXECUTING.value})
    
    history = manager.get_history("test_skill", limit=3)
    print(f"  状态历史记录数量: {len(history)}")
    
    # 2. 导出导入
    print("\n2. 导出导入演示")
    export_path = "exported_states.json"
    manager.export_states(export_path)
    print(f"  状态已导出到: {export_path}")
    
    # 创建新管理器并导入
    new_manager = SkillStateManager("imported_demo.json")
    new_manager.import_states(export_path)
    print(f"  状态已导入，技能数: {len(new_manager.get_all_states())}")
    
    # 3. 订阅者模式
    print("\n3. 订阅者模式演示")
    
    async def state_change_handler(skill_name, updates):
        print(f"  状态变化: {skill_name} -> {updates}")
    
    manager.subscribe(state_change_handler)
    await manager.update_state("test_skill", {'tags': ['demo', 'test']})
    
    # 清理演示文件
    for file in ["advanced_demo.json", "imported_demo.json", export_path]:
        if os.path.exists(file):
            os.remove(file)
    
    print("\n高级功能演示完成!")

async def main():
    """主演示函数"""
    setup_logging()
    
    print("🎓 DeerFlow 技能状态管理演示")
    print("=" * 60)
    
    try:
        await demo_basic_state_management()
        await demo_health_monitoring()
        await demo_advanced_features()
        
        print("\n" + "=" * 60)
        print("✅ 所有演示完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# 测试函数
# ============================================================================

def test_skill_state():
    """测试SkillState类"""
    print("测试SkillState类...")
    
    # 创建技能状态
    state = SkillState(
        skill_name="test_skill",
        version="1.0.0",
        enabled=True,
        usage_count=100,
        success_count=80,
        failure_count=20,
        avg_execution_time=1.5
    )
    
    # 测试计算属性
    assert state.total_attempts == 100, f"总尝试次数错误: {state.total_attempts}"
    assert abs(state.success_rate - 0.8) < 0.001, f"成功率错误: {state.success_rate}"
    assert 0 <= state.health_score <= 1, f"健康度得分超出范围: {state.health_score}"
    
    # 测试执行更新
    state.update_from_execution(success=True, execution_time=2.0)
    assert state.usage_count == 101, f"使用次数未更新: {state.usage_count}"
    assert state.success_count == 81, f"成功次数未更新: {state.success_count}"
    
    print("✅ SkillState测试通过")

def test_skill_state_manager():
    """测试SkillStateManager类"""
    print("\n测试SkillStateManager类...")
    
    # 使用临时文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        manager = SkillStateManager(temp_path)
        
        # 测试状态更新
        asyncio.run(manager.update_state("skill1", {'enabled': True}))
        state = manager.get_state("skill1")
        assert state is not None, "状态未创建"
        assert state.enabled == True, "状态更新失败"
        
        # 测试保存和加载
        manager.save_states()
        
        new_manager = SkillStateManager(temp_path)
        new_state = new_manager.get_state("skill1")
        assert new_state is not None, "状态加载失败"
        assert new_state.enabled == True, "状态属性加载错误"
        
        print("✅ SkillStateManager测试通过")
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ============================================================================
# 入口点
# ============================================================================

if __name__ == "__main__":
    # 运行测试
    test_skill_state()
    test_skill_state_manager()
    
    # 运行演示
    asyncio.run(main())