#!/bin/bash
cd /Users/apple/Projects/Thesis_Format_Fixer || exit 1
export PYTHONPATH=src
# 开发/排障辅助入口；macOS 正式交付请使用 dist/ThesisFormatFixer.app
python3 -m thesis_format_fixer.gui
