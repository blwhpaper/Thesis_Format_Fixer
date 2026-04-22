# TASK-035 macOS 发布验收、图标资源与分发说明收口

日期：2026-04-22

## 1. 本轮目标

- 核验并优化 macOS `.app` 启动体验
- 补齐图标资源接入
- 明确分发产物与命名
- 补齐 README 与 macOS 分发文档
- 新增发布验收 checklist

## 2. 实际读取并核验的文件/目录

已读取：

- `README.md`
- `pyproject.toml`
- `requirements.txt`
- `packaging/pyinstaller.spec`
- `scripts/build_macos.sh`
- `scripts/build_windows.bat`
- `src/thesis_format_fixer/gui.py`
- `src/thesis_format_fixer/app/runner.py`
- `src/thesis_format_fixer/runtime_paths.py`
- `tests/test_smoke.py`
- `tests/test_task020_gui.py`
- `tests/test_task023_user_summary.py`
- `docs/`
- `docs/TASK-031_BUILD_ACCEPTANCE.md`
- `docs/TASK-033_MACOS_APP_ACCEPTANCE.md`

核验结果：

- `assets/`：不存在
- `resources/`：任务开始时不存在，本轮已补建并接入图标资源
- `icons/`：不存在
- 现有 macOS 打包链路已存在：`scripts/build_macos.sh + packaging/pyinstaller.spec`
- 现有运行时 bundle 资源定位已存在：`src/thesis_format_fixer/runtime_paths.py`
- 现有最小 GUI/smoke 测试已存在

## 3. 本轮实际修改

- `resources/icons/macos/ThesisFormatFixer.icns`
- `resources/icons/macos/ThesisFormatFixer.png`
- `packaging/pyinstaller.spec`
- `scripts/build_macos.sh`
- `src/thesis_format_fixer/runtime_paths.py`
- `src/thesis_format_fixer/gui.py`
- `tests/test_smoke.py`
- `README.md`
- `docs/MACOS_DISTRIBUTION_GUIDE.md`
- `docs/TASK-035_MACOS_RELEASE_ACCEPTANCE.md`

## 4. 验收要点

### 4.1 启动体验

- GUI 应用显示名统一为 `Thesis Format Fixer`
- GUI 启动时会主动加载项目图标资源
- `.app` bundle 构建后会强制校验图标文件是否已进入产物

### 4.2 图标资源

- 已新增项目内图标资源：
  - `resources/icons/macos/ThesisFormatFixer.icns`
  - `resources/icons/macos/ThesisFormatFixer.png`
- PyInstaller bundle 图标已从 `icon=None` 改为显式接入项目资源
- 运行时图标定位支持源码态与 bundle 态

### 4.3 分发产物与命名

- 构建原始产物：`dist/ThesisFormatFixer.app`
- 未签名试用分发包：`dist/ThesisFormatFixer-macOS-unsigned.zip`
- 正式发布建议命名：
  - `ThesisFormatFixer-macOS-signed.zip`
  - `ThesisFormatFixer-macOS-notarized.zip`

## 5. 发布验收 Checklist

- [x] 已确认 macOS 主交付形态为 `.app`
- [x] 已确认现有打包链路继续复用 PyInstaller
- [x] 已确认 `rules/` 继续打入 bundle
- [x] 已补齐项目内 macOS 图标资源
- [x] 已将图标资源接入 `packaging/pyinstaller.spec`
- [x] 已将图标资源接入 GUI 运行时
- [x] 已新增未签名试用分发产物命名
- [x] 已在 README 说明 `.app` / zip 的用途与命名
- [x] 已在文档中写清“无账号试用分发”
- [x] 已在文档中写清“有账号签名 + 公证正式分发”
- [x] 已新增独立的 macOS 分发指南
- [x] 已补充最小 smoke 校验，覆盖 bundle 图标路径解析
- [ ] 尚未在真实非开发机上完成未签名试用分发验收
- [ ] 尚未实际执行 Developer ID 签名与公证

## 6. 建议执行的本地验收命令

```bash
PYTHON_BIN=./.venv/bin/python ./scripts/build_macos.sh
open -na /Users/apple/Projects/Thesis_Format_Fixer/dist/ThesisFormatFixer.app
./.venv/bin/python -m pytest tests/test_smoke.py tests/test_task020_gui.py tests/test_task023_user_summary.py
```

可额外检查：

```bash
find dist/ThesisFormatFixer.app/Contents/Resources -maxdepth 3 -print
```

应重点确认：

- 存在 `Contents/Resources/rules`
- 存在 `Contents/Resources/ThesisFormatFixer.icns`
- 存在 `Contents/Resources/resources/icons/macos/ThesisFormatFixer.icns`
- 应用可以正常拉起，不立即闪退

## 7. 当前验收结论

- 代码与文档层面的 macOS 发布收口已完成
- 未签名试用分发口径已可直接指导非技术用户
- 有账号时的签名 + 公证正式分发路径已明确
- 当前仍不宣称已完成正式签名发布，也不宣称已完成 Mac App Store 上架

## 8. 剩余风险

- 当前项目图标来源于现有构建产物中的默认图标资源复用，视觉品牌层面仍可继续替换为正式设计稿
- 未签名试用分发仍会受到目标机器 Gatekeeper 策略影响
- 签名、公证流程尚未在本仓库内自动化，当前提供的是清晰口径与命令骨架
