#!/usr/bin/env python3
# 第89节课：输入验证与清理
import re
from typing import Any


def sanitize_input(text: str) -> str:
    text = re.sub(r'[<>]', '', text)
    return text.strip()


def validate_email(email: str) -> bool:
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))


print(sanitize_input("<script>alert('xss')</script>"))
print(validate_email("test@example.com"))
