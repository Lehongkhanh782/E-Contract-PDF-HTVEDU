"""Đường dẫn và nạp cấu hình dùng chung.

Backend không định nghĩa lại quy tắc nghiệp vụ. Mọi mức lương, thông tin
đơn vị và chính sách khấu trừ đều đọc từ contract_kit/config để chỉ có một
nguồn sự thật.
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
KIT_DIR = REPO_ROOT / "contract_kit"
CONFIG_DIR = KIT_DIR / "config"
TEMPLATE_DIR = KIT_DIR / "templates"

# contract_kit dùng import ngang hàng (generate_demo nạp salary_engine), nên
# phải đưa thư mục đó vào sys.path trước khi import.
if str(KIT_DIR) not in sys.path:
    sys.path.insert(0, str(KIT_DIR))


def _load(name: str) -> dict:
    return json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def units() -> list[dict]:
    return _load("units.json")["units"]


@lru_cache(maxsize=None)
def business_rules() -> dict:
    return _load("business_rules.json")


@lru_cache(maxsize=None)
def salary_policy() -> dict:
    return _load("salary_policy_example.json")


def positions() -> list[dict]:
    return business_rules()["positions"]
