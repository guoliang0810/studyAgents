#!/usr/bin/env python3
# 第112节课：自定义与白标
from typing import Dict, Any

class ThemeConfig:
    def __init__(self):
        self.colors: Dict[str, str] = {}
        self.logo: str = ""
        self.name: str = "DeerFlow"
    
    def set_color(self, key: str, value: str) -> None:
        self.colors[key] = value
    
    def to_dict(self) -> Dict:
        return {"colors": self.colors, "logo": self.logo, "name": self.name}

class WhitelabelManager:
    def __init__(self):
        self.themes: Dict[str, ThemeConfig] = {}
    
    def create_theme(self, name: str) -> ThemeConfig:
        theme = ThemeConfig()
        theme.name = name
        self.themes[name] = theme
        return theme
    
    def get_theme(self, name: str) -> ThemeConfig:
        return self.themes.get(name)
    
    def apply_theme(self, theme: ThemeConfig, config: Dict[str, Any]) -> Dict[str, Any]:
        config["theme"] = theme.to_dict()
        return config

class FeatureFlags:
    def __init__(self):
        self.flags: Dict[str, bool] = {}
    
    def enable(self, name: str) -> None:
        self.flags[name] = True
    
    def disable(self, name: str) -> None:
        self.flags[name] = False
    
    def is_enabled(self, name: str) -> bool:
        return self.flags.get(name, False)

def run_demo():
    print("自定义与白标演示")
    mgr = WhitelabelManager()
    theme = mgr.create_theme("Acme Corp")
    theme.set_color("primary", "#FF0000")
    theme.set_color("secondary", "#00FF00")
    config = {"title": "Test"}
    result = mgr.apply_theme(theme, config)
    print(f"应用主题: {result}")

def run_tests():
    print("测试: 主题管理")
    mgr = WhitelabelManager()
    t = mgr.create_theme("Test")
    t.set_color("primary", "#000")
    assert mgr.get_theme("Test").colors["primary"] == "#000"
    print("✓ 主题测试通过")
    print("测试: 功能开关")
    flags = FeatureFlags()
    flags.enable("beta")
    assert flags.is_enabled("beta")
    flags.disable("beta")
    assert not flags.is_enabled("beta")
    print("✓ 功能开关测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
