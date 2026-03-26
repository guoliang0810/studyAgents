#!/usr/bin/env python3
"""
DeerFlow 环境配置与第一个Agent运行演示代码
Day 1 第4节课：课堂演示代码

本代码演示DeerFlow开发环境的完整配置流程，包括：
1. 虚拟环境创建与激活
2. 依赖安装与验证
3. API密钥配置与管理
4. 第一个Agent的编写与运行
5. 常见问题诊断与解决

通过模拟实现，展示环境配置的最佳实践和故障排除技巧。
"""

import os
import sys
import subprocess
import platform
import time
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random
import shutil

# ============================================================================
# 第一部分：环境配置模拟
# ============================================================================


class EnvironmentStep(str, Enum):
    """环境配置步骤枚举"""

    CHECK_PREREQUISITES = "检查前提条件"
    GIT_CLONE = "克隆代码库"
    VENV_CREATION = "创建虚拟环境"
    VENV_ACTIVATION = "激活虚拟环境"
    DEPENDENCY_INSTALLATION = "安装依赖"
    CONFIGURATION_SETUP = "配置文件设置"
    AGENT_SCRIPT_CREATION = "创建Agent脚本"
    AGENT_EXECUTION = "运行Agent"
    TEST_EXECUTION = "运行测试"
    PROBLEM_DIAGNOSIS = "问题诊断"


@dataclass
class SystemCheck:
    """系统检查结果"""

    python_version: Tuple[int, int, int]
    git_available: bool
    disk_space_gb: float
    memory_gb: float
    os_type: str
    internet_connection: bool

    def is_python_version_sufficient(self) -> bool:
        """检查Python版本是否满足要求（>=3.12）"""
        return self.python_version >= (3, 12, 0)

    def is_system_adequate(self) -> bool:
        """检查系统是否满足最低要求"""
        return (
            self.is_python_version_sufficient()
            and self.git_available
            and self.disk_space_gb >= 5.0
            and self.memory_gb >= 8.0
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "python_version": f"{self.python_version[0]}.{self.python_version[1]}.{self.python_version[2]}",
            "git_available": self.git_available,
            "disk_space_gb": self.disk_space_gb,
            "memory_gb": self.memory_gb,
            "os_type": self.os_type,
            "internet_connection": self.internet_connection,
            "python_sufficient": self.is_python_version_sufficient(),
            "system_adequate": self.is_system_adequate(),
        }


@dataclass
class Dependency:
    """依赖包信息"""

    name: str
    version: str
    required: bool = True
    installed: bool = False
    installation_error: Optional[str] = None

    def __str__(self) -> str:
        status = "✅ 已安装" if self.installed else "❌ 未安装"
        if self.installation_error:
            status = f"⚠️ 安装失败: {self.installation_error}"
        return f"{self.name}=={self.version} {status}"


class EnvironmentManager:
    """环境管理器"""

    def __init__(self, project_name: str = "deer-flow"):
        self.project_name = project_name
        self.project_path = Path.cwd() / project_name
        self.venv_path = self.project_path / "venv"
        self.config_path = self.project_path / "config.yaml"
        self.requirements_path = self.project_path / "requirements.txt"
        self.steps_completed: Dict[EnvironmentStep, bool] = {}
        self.system_check: Optional[SystemCheck] = None
        self.dependencies: List[Dependency] = []

        # 初始化核心依赖列表
        self._initialize_dependencies()

    def _initialize_dependencies(self) -> None:
        """初始化依赖列表"""
        core_dependencies = [
            Dependency("langchain", "0.1.0", required=True),
            Dependency("langgraph", "0.0.40", required=True),
            Dependency("openai", "1.6.1", required=True),
            Dependency("pydantic", "2.5.0", required=True),
            Dependency("yaml", "6.0.1", required=True),
            Dependency("pytest", "7.4.3", required=False),
            Dependency("black", "23.12.1", required=False),
            Dependency("flake8", "6.1.0", required=False),
        ]
        self.dependencies = core_dependencies

    def check_prerequisites(self) -> SystemCheck:
        """检查系统前提条件"""
        print("\n" + "=" * 60)
        print("步骤1: 检查系统前提条件")
        print("=" * 60)

        # 模拟系统检查
        python_version = (3, 12, 1)  # 模拟Python 3.12.1
        git_available = True
        disk_space_gb = 50.2
        memory_gb = 16.0
        os_type = platform.system()
        internet_connection = True

        self.system_check = SystemCheck(
            python_version=python_version,
            git_available=git_available,
            disk_space_gb=disk_space_gb,
            memory_gb=memory_gb,
            os_type=os_type,
            internet_connection=internet_connection,
        )

        check_result = self.system_check.to_dict()
        for key, value in check_result.items():
            print(f"  {key}: {value}")

        if self.system_check.is_system_adequate():
            print("\n✅ 系统检查通过！满足DeerFlow开发环境要求。")
            self.steps_completed[EnvironmentStep.CHECK_PREREQUISITES] = True
        else:
            print("\n❌ 系统检查未通过！请解决以下问题：")
            if not self.system_check.is_python_version_sufficient():
                print("  - Python版本需要3.12.0或更高")
            if not self.system_check.git_available:
                print("  - Git未安装或不在PATH中")
            if self.system_check.disk_space_gb < 5.0:
                print(f"  - 磁盘空间不足: {self.system_check.disk_space_gb}GB < 5GB")
            if self.system_check.memory_gb < 8.0:
                print(f"  - 内存不足: {self.system_check.memory_gb}GB < 8GB")

        return self.system_check

    def clone_repository(
        self, repo_url: str = "https://github.com/bytedance/deer-flow.git"
    ) -> bool:
        """克隆代码库（模拟）"""
        print("\n" + "=" * 60)
        print("步骤2: 克隆DeerFlow代码库")
        print("=" * 60)

        if not self.system_check or not self.system_check.git_available:
            print("❌ Git不可用，无法克隆代码库")
            return False

        try:
            # 模拟克隆过程
            print(f"正在克隆 {repo_url} 到 {self.project_path}...")
            time.sleep(1)  # 模拟网络延迟

            # 创建项目目录结构（模拟）
            self.project_path.mkdir(exist_ok=True)
            (self.project_path / "README.md").write_text(
                "# DeerFlow AI Agent Framework\n\nWelcome to DeerFlow!"
            )
            (self.project_path / "requirements.txt").write_text(
                "langchain==0.1.0\nlanggraph==0.0.40\nopenai==1.6.1\npydantic==2.5.0\npyyaml==6.0.1\n"
            )
            (self.project_path / "config.example.yaml").write_text(
                'openai:\n  api_key: "your-api-key-here"\n  model: "gpt-4-turbo-preview"\n\n'
                'anthropic:\n  api_key: "your-api-key-here"\n  model: "claude-3-opus-20240229"\n'
            )

            # 创建子目录结构
            (self.project_path / "agents").mkdir(exist_ok=True)
            (self.project_path / "middlewares").mkdir(exist_ok=True)
            (self.project_path / "tools").mkdir(exist_ok=True)
            (self.project_path / "tests").mkdir(exist_ok=True)

            print("✅ 代码库克隆成功！")
            print(f"项目目录结构：")
            for item in self.project_path.iterdir():
                if item.is_dir():
                    print(f"  📁 {item.name}/")
                else:
                    print(f"  📄 {item.name}")

            self.steps_completed[EnvironmentStep.GIT_CLONE] = True
            return True

        except Exception as e:
            print(f"❌ 克隆失败: {e}")
            return False

    def create_virtual_environment(self) -> bool:
        """创建虚拟环境（模拟）"""
        print("\n" + "=" * 60)
        print("步骤3: 创建Python虚拟环境")
        print("=" * 60)

        if not self.project_path.exists():
            print("❌ 项目目录不存在，请先克隆代码库")
            return False

        try:
            # 模拟虚拟环境创建
            print(f"正在创建虚拟环境到 {self.venv_path}...")
            time.sleep(0.5)

            # 创建虚拟环境目录结构（模拟）
            self.venv_path.mkdir(exist_ok=True)
            (self.venv_path / "pyvenv.cfg").write_text(
                "home = /usr/bin\n"
                "include-system-site-packages = false\n"
                "version = 3.12.1\n"
            )
            (self.venv_path / "bin").mkdir(exist_ok=True)
            (self.venv_path / "lib").mkdir(exist_ok=True)
            (self.venv_path / "include").mkdir(exist_ok=True)

            print("✅ 虚拟环境创建成功！")
            print(f"虚拟环境路径: {self.venv_path}")
            print("目录结构:")
            print("  📁 venv/")
            print("    📄 pyvenv.cfg")
            print("    📁 bin/    # 可执行文件")
            print("    📁 lib/    # Python库")
            print("    📁 include/# 头文件")

            self.steps_completed[EnvironmentStep.VENV_CREATION] = True
            return True

        except Exception as e:
            print(f"❌ 虚拟环境创建失败: {e}")
            return False

    def activate_virtual_environment(self) -> bool:
        """激活虚拟环境（模拟）"""
        print("\n" + "=" * 60)
        print("步骤4: 激活虚拟环境")
        print("=" * 60)

        if not self.venv_path.exists():
            print("❌ 虚拟环境不存在，请先创建虚拟环境")
            return False

        # 模拟激活过程
        os_type = platform.system()
        activation_commands = {
            "Linux": "source venv/bin/activate",
            "Darwin": "source venv/bin/activate",  # macOS
            "Windows": "venv\\Scripts\\activate",
        }

        activation_cmd = activation_commands.get(os_type, "source venv/bin/activate")
        print(f"检测到操作系统: {os_type}")
        print(f"激活命令: {activation_cmd}")
        print("\n💡 提示: 激活后，命令行提示符会显示 (venv)")
        print("💡 提示: 要退出虚拟环境，运行 'deactivate'")

        # 模拟Python路径切换
        original_python = sys.executable
        venv_python = self.venv_path / "bin" / "python"
        if os_type == "Windows":
            venv_python = self.venv_path / "Scripts" / "python.exe"

        print(f"激活前Python路径: {original_python}")
        print(f"激活后Python路径: {venv_python}")

        time.sleep(0.5)
        print("✅ 虚拟环境激活成功！（模拟）")

        self.steps_completed[EnvironmentStep.VENV_ACTIVATION] = True
        return True

    def install_dependencies(self) -> bool:
        """安装依赖包（模拟）"""
        print("\n" + "=" * 60)
        print("步骤5: 安装依赖包")
        print("=" * 60)

        if not self.venv_path.exists():
            print("❌ 虚拟环境未激活，请先激活虚拟环境")
            return False

        if not self.requirements_path.exists():
            print("❌ requirements.txt 文件不存在")
            return False

        try:
            print("正在读取 requirements.txt...")
            requirements = self.requirements_path.read_text().strip().split("\n")
            print(f"找到 {len(requirements)} 个依赖包")

            print("\n开始安装依赖...")
            for i, dep in enumerate(requirements, 1):
                dep = dep.strip()
                if not dep or dep.startswith("#"):
                    continue

                print(f"  [{i}/{len(requirements)}] 安装 {dep}...")
                time.sleep(0.2)  # 模拟安装时间

                # 模拟安装成功或失败
                if (
                    "opencv" in dep and random.random() < 0.3
                ):  # 30%概率模拟opencv安装失败
                    print(
                        f"    ❌ 安装失败: 需要编译工具，请安装 build-essential (Linux) 或 Visual C++ Build Tools (Windows)"
                    )
                    # 标记依赖安装失败
                    for d in self.dependencies:
                        if "opencv" in d.name:
                            d.installed = False
                            d.installation_error = "编译失败"
                else:
                    print(f"    ✅ 安装成功")
                    # 标记依赖安装成功
                    for d in self.dependencies:
                        if d.name in dep:
                            d.installed = True

            print("\n✅ 依赖安装完成！")
            print("\n已安装的依赖包:")
            for dep in self.dependencies:
                if dep.installed:
                    print(f"  ✅ {dep.name}=={dep.version}")

            print("\n安装失败的依赖包:")
            failed_deps = [
                d for d in self.dependencies if not d.installed and d.required
            ]
            if failed_deps:
                for dep in failed_deps:
                    print(f"  ❌ {dep.name}: {dep.installation_error or '未知错误'}")
                print("\n💡 解决方案:")
                print("  1. 检查网络连接")
                print(
                    "  2. 使用国内镜像源: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple"
                )
                print(
                    "  3. 安装编译工具: build-essential (Linux) 或 Visual C++ Build Tools (Windows)"
                )
            else:
                print("  （无）")

            self.steps_completed[EnvironmentStep.DEPENDENCY_INSTALLATION] = True
            return len(failed_deps) == 0

        except Exception as e:
            print(f"❌ 依赖安装失败: {e}")
            return False

    def setup_configuration(self, api_key: str = "sk-demo1234567890abcdef") -> bool:
        """设置配置文件（模拟）"""
        print("\n" + "=" * 60)
        print("步骤6: 配置API密钥和配置文件")
        print("=" * 60)

        config_example = self.project_path / "config.example.yaml"
        if not config_example.exists():
            print("❌ 配置文件模板不存在")
            return False

        try:
            print("正在复制配置文件模板...")
            shutil.copy(config_example, self.config_path)

            print("正在配置API密钥...")
            config_content = self.config_path.read_text()

            # 安全提示
            print("\n⚠️ 安全警告:")
            print("  1. 永远不要将API密钥提交到Git仓库")
            print("  2. 使用环境变量存储敏感信息")
            print("  3. 在.gitignore中添加config.yaml")

            # 模拟配置内容
            config_data = {
                "openai": {
                    "api_key": api_key
                    if api_key != "your-api-key-here"
                    else "sk-demo-xxxxxxxx",
                    "model": "gpt-4-turbo-preview",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
                "anthropic": {
                    "api_key": "your-claude-api-key-here",
                    "model": "claude-3-sonnet-20240229",
                },
                "logging": {"level": "INFO", "file": "logs/deerflow.log"},
                "agents": {"default_timeout": 30, "max_retries": 3},
            }

            # 写入配置文件
            import yaml

            with open(self.config_path, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

            print("\n✅ 配置文件创建成功！")
            print(f"配置文件路径: {self.config_path}")
            print("\n配置文件内容预览:")
            print("-" * 40)
            with open(self.config_path, "r") as f:
                lines = f.readlines()[:10]  # 显示前10行
                for line in lines:
                    print(line.rstrip())
            print("...")
            print("-" * 40)

            # 创建.gitignore文件（如果不存在）
            gitignore_path = self.project_path / ".gitignore"
            if not gitignore_path.exists():
                gitignore_content = (
                    "# 配置文件（包含敏感信息）\n"
                    "config.yaml\n"
                    "config.local.yaml\n"
                    "\n"
                    "# 虚拟环境\n"
                    "venv/\n"
                    ".venv/\n"
                    "env/\n"
                    "\n"
                    "# 日志文件\n"
                    "logs/\n"
                    "*.log\n"
                    "\n"
                    "# 环境变量文件\n"
                    ".env\n"
                    ".env.local\n"
                )
                gitignore_path.write_text(gitignore_content)
                print("\n📄 已创建 .gitignore 文件以保护敏感信息")

            self.steps_completed[EnvironmentStep.CONFIGURATION_SETUP] = True
            return True

        except Exception as e:
            print(f"❌ 配置失败: {e}")
            return False

    def create_first_agent(self) -> bool:
        """创建第一个Agent脚本（模拟）"""
        print("\n" + "=" * 60)
        print("步骤7: 创建第一个Agent脚本")
        print("=" * 60)

        agent_script_path = self.project_path / "first_agent.py"

        try:
            agent_code = '''#!/usr/bin/env python3
"""
第一个DeerFlow Agent示例
Day 1 第4节课：实战配置与运行
"""

import asyncio
import yaml
from typing import Dict, Any

# 导入DeerFlow相关模块（模拟）
class MockAgent:
    """模拟Agent类"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.message_history = []
    
    async def run(self, query: str) -> str:
        """运行Agent"""
        print(f"🤖 Agent '{self.name}' 正在处理查询: '{query}'")
        
        # 模拟思考过程
        print("💭 Agent正在思考...")
        await asyncio.sleep(0.5)
        
        # 模拟工具调用
        print("🔧 Agent正在调用工具...")
        await asyncio.sleep(0.3)
        
        # 模拟生成响应
        response = f"我已经处理了您的查询: '{query}'。"
        response += "根据我的分析，这是一个关于DeerFlow环境配置的问题。"
        response += "建议您按照以下步骤检查：1) 确认虚拟环境已激活 2) 验证API密钥配置 3) 检查网络连接。"
        
        print(f"📤 Agent响应: {response}")
        self.message_history.append({"query": query, "response": response})
        
        return response

async def main():
    """主函数"""
    print("🚀 启动第一个DeerFlow Agent...")
    
    try:
        # 1. 加载配置
        print("📄 加载配置文件...")
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        # 2. 创建Agent
        print("🤖 创建Agent实例...")
        agent = MockAgent(
            name="DeerFlow新手助手",
            config=config
        )
        
        # 3. 运行Agent
        print("▶️ 运行Agent...")
        query = "如何配置DeerFlow开发环境？"
        response = await agent.run(query)
        
        # 4. 输出结果
        print("\\n" + "="*50)
        print("🎉 第一个Agent运行成功！")
        print("="*50)
        print(f"查询: {query}")
        print(f"响应: {response}")
        print("="*50)
        
        return True
        
    except FileNotFoundError:
        print("❌ 错误: 找不到配置文件 config.yaml")
        print("💡 解决方案: 请确保已运行配置步骤，或检查文件路径")
        return False
    except yaml.YAMLError as e:
        print(f"❌ 错误: 配置文件格式错误 - {e}")
        print("💡 解决方案: 检查YAML语法，确保缩进正确")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    # 运行异步主函数
    success = asyncio.run(main())
    if success:
        print("\\n✅ 恭喜！您已成功运行第一个DeerFlow Agent！")
        print("💡 下一步: 尝试修改查询内容，观察Agent的不同响应")
    else:
        print("\\n❌ Agent运行失败，请检查上述错误信息")
        sys.exit(1)
'''

            agent_script_path.write_text(agent_code)

            print("✅ Agent脚本创建成功！")
            print(f"脚本路径: {agent_script_path}")
            print("\n脚本结构:")
            print("  📄 first_agent.py")
            print("    ├── MockAgent类 (模拟DeerFlow Agent)")
            print("    ├── main() 异步主函数")
            print("    ├── 配置加载")
            print("    ├── Agent创建")
            print("    └── Agent运行和结果输出")

            self.steps_completed[EnvironmentStep.AGENT_SCRIPT_CREATION] = True
            return True

        except Exception as e:
            print(f"❌ 创建Agent脚本失败: {e}")
            return False

    def run_agent(self) -> bool:
        """运行Agent脚本（模拟）"""
        print("\n" + "=" * 60)
        print("步骤8: 运行第一个Agent")
        print("=" * 60)

        agent_script_path = self.project_path / "first_agent.py"
        if not agent_script_path.exists():
            print("❌ Agent脚本不存在，请先创建脚本")
            return False

        try:
            print("执行命令: python first_agent.py")
            print("\n" + "-" * 40)
            print("模拟输出:")
            print("-" * 40)

            # 模拟Agent运行输出
            output_lines = [
                "🚀 启动第一个DeerFlow Agent...",
                "📄 加载配置文件...",
                "🤖 创建Agent实例...",
                "▶️ 运行Agent...",
                "🤖 Agent 'DeerFlow新手助手' 正在处理查询: '如何配置DeerFlow开发环境？'",
                "💭 Agent正在思考...",
                "🔧 Agent正在调用工具...",
                "📤 Agent响应: 我已经处理了您的查询: '如何配置DeerFlow开发环境？'。根据我的分析，这是一个关于DeerFlow环境配置的问题。建议您按照以下步骤检查：1) 确认虚拟环境已激活 2) 验证API密钥配置 3) 检查网络连接。",
                "",
                "=" * 50,
                "🎉 第一个Agent运行成功！",
                "=" * 50,
                "查询: 如何配置DeerFlow开发环境？",
                "响应: 我已经处理了您的查询: '如何配置DeerFlow开发环境？'。根据我的分析，这是一个关于DeerFlow环境配置的问题。建议您按照以下步骤检查：1) 确认虚拟环境已激活 2) 验证API密钥配置 3) 检查网络连接。",
                "=" * 50,
                "",
                "✅ 恭喜！您已成功运行第一个DeerFlow Agent！",
                "💡 下一步: 尝试修改查询内容，观察Agent的不同响应",
            ]

            for line in output_lines:
                print(line)
                time.sleep(0.1)

            print("-" * 40)
            print("✅ Agent运行成功！")

            self.steps_completed[EnvironmentStep.AGENT_EXECUTION] = True
            return True

        except Exception as e:
            print(f"❌ Agent运行失败: {e}")
            return False

    def run_tests(self) -> bool:
        """运行测试（模拟）"""
        print("\n" + "=" * 60)
        print("步骤9: 运行基本测试")
        print("=" * 60)

        try:
            print("执行命令: pytest tests/ -v")
            print("\n" + "-" * 40)
            print("模拟测试输出:")
            print("-" * 40)

            # 模拟测试输出
            test_results = [
                "collected 5 items",
                "",
                "tests/test_config.py::test_config_loading ✓ PASSED",
                "tests/test_config.py::test_api_key_validation ✓ PASSED",
                "tests/test_basic.py::test_agent_creation ✓ PASSED",
                "tests/test_basic.py::test_agent_execution ✓ PASSED",
                "tests/test_basic.py::test_error_handling ✗ FAILED",
                "",
                "测试结果摘要:",
                "=============",
                "总计: 5",
                "通过: 4",
                "失败: 1",
                "跳过: 0",
                "",
                "失败详情:",
                "tests/test_basic.py::test_error_handling - AssertionError: 预期错误处理未正确执行",
                "",
                "💡 提示: 1个测试失败是正常的，这是为了演示测试框架的工作方式。",
                "💡 提示: 在实际开发中，您需要修复失败的测试。",
            ]

            for line in test_results:
                print(line)
                time.sleep(0.05)

            print("-" * 40)
            print("✅ 测试运行完成！")
            print("💡 虽然有1个测试失败，但这演示了测试框架的工作方式。")

            self.steps_completed[EnvironmentStep.TEST_EXECUTION] = True
            return True

        except Exception as e:
            print(f"❌ 测试运行失败: {e}")
            return False

    def diagnose_problems(self) -> None:
        """诊断常见问题"""
        print("\n" + "=" * 60)
        print("步骤10: 常见问题诊断")
        print("=" * 60)

        print("🔍 正在诊断环境问题...")
        time.sleep(0.5)

        # 模拟问题检测
        potential_problems = []

        # 检查Python版本
        if self.system_check and not self.system_check.is_python_version_sufficient():
            potential_problems.append(
                ("Python版本过低", "需要Python 3.12.0+", "升级Python版本")
            )

        # 检查虚拟环境
        if not self.venv_path.exists():
            potential_problems.append(
                ("虚拟环境不存在", "venv/目录未找到", "运行 python -m venv venv")
            )

        # 检查依赖安装
        failed_deps = [d for d in self.dependencies if not d.installed and d.required]
        if failed_deps:
            potential_problems.append(
                (
                    "依赖安装失败",
                    f"{len(failed_deps)}个依赖未安装",
                    "使用国内镜像源重新安装",
                )
            )

        # 检查配置文件
        if not self.config_path.exists():
            potential_problems.append(
                (
                    "配置文件缺失",
                    "config.yaml不存在",
                    "复制config.example.yaml为config.yaml",
                )
            )

        if potential_problems:
            print("⚠️ 检测到以下潜在问题:")
            for i, (problem, cause, solution) in enumerate(potential_problems, 1):
                print(f"\n{i}. {problem}")
                print(f"   原因: {cause}")
                print(f"   解决方案: {solution}")
        else:
            print("✅ 未检测到明显问题，环境配置正常！")

        print("\n📋 通用问题诊断指南:")
        print("1. Python版本问题: python --version")
        print("2. 虚拟环境激活: 确保命令行提示符显示 (venv)")
        print("3. 依赖冲突: pip list | grep <package>")
        print("4. API密钥错误: 检查config.yaml格式和密钥有效性")
        print("5. 网络连接: ping api.openai.com")
        print(
            "6. 配置文件语法: python -c \"import yaml; yaml.safe_load(open('config.yaml'))\""
        )

        self.steps_completed[EnvironmentStep.PROBLEM_DIAGNOSIS] = True

    def print_summary(self) -> None:
        """打印配置摘要"""
        print("\n" + "=" * 60)
        print("🎉 DeerFlow环境配置完成摘要")
        print("=" * 60)

        total_steps = len(EnvironmentStep)
        completed_steps = sum(1 for step in self.steps_completed.values() if step)

        print(f"总步骤: {total_steps}")
        print(f"完成步骤: {completed_steps}")
        print(f"完成率: {completed_steps / total_steps * 100:.1f}%")

        print("\n✅ 已完成的步骤:")
        for step, completed in self.steps_completed.items():
            if completed:
                print(f"  ✓ {step.value}")

        print("\n📁 生成的文件和目录:")
        print(f"  项目根目录: {self.project_path}")
        print(f"  虚拟环境: {self.venv_path}")
        print(f"  配置文件: {self.config_path}")
        print(f"  Agent脚本: {self.project_path / 'first_agent.py'}")
        print(f"  依赖文件: {self.requirements_path}")

        print("\n🚀 下一步:")
        print("  1. 尝试修改first_agent.py中的查询内容")
        print("  2. 添加新的工具或中间件")
        print("  3. 阅读DeerFlow官方文档")
        print("  4. 加入DeerFlow开发者社区")

        print("\n💡 提示: 环境配置是AI Agent开发的第一步，恭喜您成功迈出第一步！")


# ============================================================================
# 第二部分：配置演示主函数
# ============================================================================


def demonstrate_environment_configuration():
    """演示环境配置全过程"""
    print("🧪 DeerFlow环境配置演示")
    print("=" * 60)
    print("本演示将模拟DeerFlow开发环境的完整配置流程")
    print("包括：系统检查、代码克隆、虚拟环境、依赖安装、")
    print("      API配置、Agent创建、运行测试和问题诊断")
    print("=" * 60)

    # 创建环境管理器
    manager = EnvironmentManager()

    # 执行配置步骤
    manager.check_prerequisites()
    manager.clone_repository()
    manager.create_virtual_environment()
    manager.activate_virtual_environment()
    manager.install_dependencies()
    manager.setup_configuration()
    manager.create_first_agent()
    manager.run_agent()
    manager.run_tests()
    manager.diagnose_problems()

    # 打印摘要
    manager.print_summary()


# ============================================================================
# 第三部分：故障模拟与诊断
# ============================================================================


class ProblemSimulator:
    """问题模拟器：演示常见配置问题"""

    @staticmethod
    def simulate_python_version_problem():
        """模拟Python版本问题"""
        print("\n🔧 故障模拟：Python版本问题")
        print("-" * 40)
        print("问题：Python版本过低 (3.10.0)")
        print("症状：'ImportError: cannot import name...'")
        print("诊断：python --version")
        print("解决方案：安装Python 3.12+，或使用pyenv管理版本")
        print("-" * 40)

    @staticmethod
    def simulate_dependency_conflict():
        """模拟依赖冲突问题"""
        print("\n🔧 故障模拟：依赖冲突")
        print("-" * 40)
        print("问题：langchain版本冲突")
        print("症状：'AttributeError: module...has no attribute...'")
        print("诊断：pip list | grep langchain")
        print("解决方案：pip install langchain==0.1.0")
        print("         或使用虚拟环境隔离")
        print("-" * 40)

    @staticmethod
    def simulate_api_key_error():
        """模拟API密钥错误"""
        print("\n🔧 故障模拟：API密钥错误")
        print("-" * 40)
        print("问题：无效的OpenAI API密钥")
        print("症状：'AuthenticationError: Incorrect API key provided'")
        print("诊断：检查config.yaml格式和密钥有效性")
        print("解决方案：1. 检查YAML缩进")
        print("         2. 验证API密钥有效性")
        print("         3. 检查账户余额")
        print("-" * 40)

    @staticmethod
    def simulate_network_problem():
        """模拟网络问题"""
        print("\n🔧 故障模拟：网络连接问题")
        print("-" * 40)
        print("问题：无法连接到OpenAI API")
        print("症状：'ConnectionError: Failed to connect...'")
        print("诊断：ping api.openai.com")
        print("解决方案：1. 检查防火墙设置")
        print("         2. 配置代理：export HTTPS_PROXY=...")
        print("         3. 使用国内镜像或本地模型")
        print("-" * 40)

    @staticmethod
    def simulate_config_syntax_error():
        """模拟配置语法错误"""
        print("\n🔧 故障模拟：配置文件语法错误")
        print("-" * 40)
        print("问题：YAML语法错误")
        print("症状：'YAMLError: while parsing...'")
        print("诊断：python -c \"import yaml; yaml.safe_load(open('config.yaml'))\"")
        print("解决方案：1. 检查缩进（必须使用空格）")
        print("         2. 检查冒号后的空格")
        print("         3. 使用YAML验证工具")
        print("-" * 40)

    @staticmethod
    def demonstrate_problem_solving():
        """演示问题解决流程"""
        print("\n" + "=" * 60)
        print("🔧 故障诊断与解决演示")
        print("=" * 60)

        problems = [
            ProblemSimulator.simulate_python_version_problem,
            ProblemSimulator.simulate_dependency_conflict,
            ProblemSimulator.simulate_api_key_error,
            ProblemSimulator.simulate_network_problem,
            ProblemSimulator.simulate_config_syntax_error,
        ]

        for i, problem_func in enumerate(problems, 1):
            problem_func()
            if i < len(problems):
                input("\n按Enter继续下一个故障模拟...")

        print("\n📋 故障诊断总结：")
        print("1. 阅读错误信息：错误信息通常包含关键线索")
        print("2. 逐步排查：从最简单的问题开始检查")
        print("3. 使用诊断工具：版本检查、依赖验证、网络测试")
        print("4. 搜索解决方案：错误信息 + '解决方案'")
        print("5. 寻求帮助：GitHub Issues、Discord社区、Stack Overflow")
        print("=" * 60)


# ============================================================================
# 第四部分：最佳实践总结
# ============================================================================


def print_best_practices():
    """打印环境配置最佳实践"""
    print("\n" + "=" * 60)
    print("📚 DeerFlow环境配置最佳实践")
    print("=" * 60)

    practices = [
        ("📁 目录结构", "保持清晰的目录结构，分离代码、配置、日志"),
        ("🐍 虚拟环境", "始终使用虚拟环境，避免系统污染"),
        ("🔐 API密钥安全", "使用环境变量或密钥管理服务，不提交到Git"),
        ("📦 依赖管理", "使用requirements.txt固定版本，定期更新"),
        ("🔧 配置管理", "使用config.example.yaml模板，支持环境特定配置"),
        ("🧪 测试驱动", "编写测试验证环境配置，确保可重复性"),
        ("📝 文档记录", "记录配置步骤和遇到的问题，形成知识库"),
        ("🔄 版本控制", "使用Git管理配置变更，方便回滚"),
        ("🚀 自动化脚本", "编写自动化配置脚本，一键完成环境设置"),
        ("🔍 监控告警", "监控环境状态，设置异常告警"),
    ]

    for title, description in practices:
        print(f"\n{title}:")
        print(f"  {description}")

    print("\n" + "=" * 60)
    print("🎯 成功配置的关键：")
    print("  1. 耐心：环境配置可能需要多次尝试")
    print("  2. 细致：注意每个步骤的细节")
    print("  3. 学习：从问题中学习，积累经验")
    print("  4. 分享：帮助他人解决类似问题")
    print("=" * 60)


# ============================================================================
# 主程序
# ============================================================================


def main():
    """主函数：运行完整的演示"""
    print("=" * 70)
    print("🎓 DeerFlow Day 1 第4节课：环境配置与第一个Agent运行演示")
    print("=" * 70)

    try:
        # 第一部分：环境配置演示
        demonstrate_environment_configuration()

        # 第二部分：故障诊断演示
        ProblemSimulator.demonstrate_problem_solving()

        # 第三部分：最佳实践
        print_best_practices()

        print("\n" + "=" * 70)
        print("🎉 演示完成！您已掌握DeerFlow环境配置的全流程。")
        print("💡 在实际环境中，请按照演示的步骤操作。")
        print("📚 更多资源请参考课程材料和DeerFlow官方文档。")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\n⚠️ 演示被用户中断。")
        print("💡 提示：环境配置可以分步完成，不必一次性做完。")
    except Exception as e:
        print(f"\n\n❌ 演示过程中发生错误: {e}")
        print("💡 提示：这正是实际配置中可能遇到的问题，学习如何解决它！")


if __name__ == "__main__":
    main()
