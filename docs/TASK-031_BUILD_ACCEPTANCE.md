# TASK-031 双平台真实构建验收与发布问题修补

日期：2026-04-22

## 1. 验收范围

- 真实安装 `requirements.txt`
- 真实执行 macOS PyInstaller 构建
- 真实尝试启动 macOS 打包产物
- 最小修补构建脚本与 README 发布口径
- 回归 `pytest` 最小测试集

## 2. 实际执行命令

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
PYTHON_BIN=./.venv/bin/python ./scripts/build_macos.sh
PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller" ./.venv/bin/python -m PyInstaller --noconfirm --clean packaging/pyinstaller.spec
open -na /Users/apple/Projects/Thesis_Format_Fixer/dist/ThesisFormatFixer.app
osascript -e 'tell application "System Events" to (name of processes) contains "ThesisFormatFixer"'
./.venv/bin/python -m pytest tests/test_smoke.py tests/test_task020_gui.py tests/test_task023_user_summary.py
```

## 3. macOS 真实结果

- `pip install -r requirements.txt`：成功
- 首次执行 `./scripts/build_macos.sh`：失败
- 首次失败原因：PyInstaller 清理默认全局缓存目录 `~/Library/Application Support/pyinstaller` 时触发 `PermissionError: [Errno 1] Operation not permitted`
- 第一次修补：将 `PYINSTALLER_CONFIG_DIR` 收口到项目内的 `.pyinstaller/`
- 第二次修补：在 `scripts/build_macos.sh` 中显式 `export PYINSTALLER_CONFIG_DIR`，确保子进程实际继承该变量
- 修补后再次构建：成功
- 构建产物：`dist/ThesisFormatFixer.app`
- 真实启动：已执行 `open -na .../dist/ThesisFormatFixer.app`
- 启动核验：重建后短暂等待再查，`osascript` 返回 `true`，说明应用进程已被系统拉起且未立即闪退

## 4. Windows 侧结论

- 本轮环境仅覆盖 macOS
- `scripts/build_windows.bat` 已同步补上项目内 `PYINSTALLER_CONFIG_DIR`
- Windows 构建与启动本轮**未真实执行**
- README 已明确标注 Windows 需要在真实 Windows 环境补做一次构建与启动验收

## 5. 当前遗留风险

- `packaging/pyinstaller.spec` 当前仍是 macOS `.app` 的 onefile 形态，PyInstaller 6.19 会给出弃用提示；本轮未扩大为打包形态重构
- macOS 本轮只验证了产物可成功启动，未做 GUI 人工点击式功能回归
- Windows 侧仍缺少真实机器构建与启动记录
