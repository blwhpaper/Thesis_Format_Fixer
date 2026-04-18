"""Application runner placeholders for TASK-001."""

from __future__ import annotations

from pathlib import Path


def run_check(input_file: Path) -> int:
    if not input_file.exists():
        print(f"输入文件不存在: {input_file}")
        return 2
    print("待实现")
    return 0


def run_fix(input_file: Path, output_file: Path) -> int:
    if not input_file.exists():
        print(f"输入文件不存在: {input_file}")
        return 2
    if output_file.is_dir():
        print(f"--out 不能是目录: {output_file}")
        return 2
    print("待实现")
    return 0
