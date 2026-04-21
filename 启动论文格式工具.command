#!/bin/bash
cd /Users/apple/Projects/Thesis_Format_Fixer || exit 1
export PYTHONPATH=src
python3 -m thesis_format_fixer.gui
