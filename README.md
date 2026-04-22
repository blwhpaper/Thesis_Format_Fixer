# thesis-format-fixer

`thesis-format-fixer` 是一个针对英文毕业论文 `.docx` 的格式检查/修复工具。

当前阶段：**TASK-031 双平台真实构建验收与发布问题修补**。

## 1. 开发环境安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## 2. 开发运行

### CLI

```bash
thesis-format-fixer --help
```

### GUI

```bash
python -m thesis_format_fixer.gui
```

或在已安装环境中直接运行：

```bash
thesis-format-fixer-gui
```

GUI 默认会把输出目录预填为 `~/ThesisFormatFixerOutput`；你也可以在界面中改为任意可写目录。

## 3. CLI 用法

```bash
# 查看帮助
thesis-format-fixer --help

# 单文件检查（建议显式输出报告路径）
thesis-format-fixer check samples/input/demo.docx \
  --report-json samples/output/demo.check.report.json \
  --report-md samples/output/demo.check.report.md

# 单文件修复（安全输出到新文件，不覆盖原文件）
thesis-format-fixer fix samples/input/demo.docx \
  --out samples/output/demo.fixed.docx

# 批量修复（默认递归）
thesis-format-fixer batch-fix samples/input \
  --out-dir samples/output/batch

# 批量修复（仅当前目录）
thesis-format-fixer batch-fix samples/input \
  --out-dir samples/output/batch \
  --no-recursive
```

## 4. GUI 启动方式

```bash
python -m thesis_format_fixer.gui
```

GUI 模式支持：`check` / `fix` / `batch-fix`。

当前桌面宿主统一为 **PySide6 主窗口**，推荐正式使用方式如下：

1. 安装依赖后启动：

```bash
python3 -m thesis_format_fixer.gui
```

2. 在主窗口中完成：
- 选择输入文件（或批量模式下选择输入目录）
- 确认输出目录（默认是 `~/ThesisFormatFixerOutput`，也可手动改）
- 选择模式：`check` / `fix` / `batch-fix`
- 单文件模式下仅接受 `.docx`；批量模式下仅接受目录
- 点击 `开始执行`

3. 执行完成后，界面内可直接查看：
- `用户版中文摘要`：优先展示总体状态、自动修复数量、未自动修改数量、人工复核数量
- `分类结果`：区分“已自动修复 / 已自动处理”“检测到异常但未自动修改”“需要人工复核”
- `详细结果 / 日志`：查看详细结果、批量逐文件结果与失败时的技术信息
- `报告与输出文件快捷入口`：双击打开关键文件
- `打开输出目录` / `打开关键报告` / `打开用户摘要`

GUI 正式化后的交互约束：
- 未选择必要输入时，`开始执行` 按钮保持不可用。
- 执行中会禁用重复执行与路径修改，避免重复触发。
- 成功后优先展示中文用户摘要，不先把技术字段顶到第一层。
- 失败时主提示为中文可理解错误；详细面板保留技术信息用于排查。
- `batch-fix` 会展示中文批量摘要，并明确列出输出目录、批处理汇总文件、每个文件的修复结果与报告路径。
- `fix` 结果会突出展示：
  - 已自动修复多少项
  - 检测到异常但未自动修改多少项
  - 需要人工复核多少项
  - 生成了哪些输出文件

GUI 结果区说明：
- 主区优先显示用户摘要。
- 下半区显示详细结果与文件快捷入口。
- 技术字段（如 `auto_fix_rule_count`、`reference_blocking_count`）保留在次级区域，便于排障但不干扰普通用户阅读。

## 5. 双平台打包

统一打包方案使用 **PyInstaller**，默认产物直接启动 GUI，不额外引入安装器、自动更新、签名或公证流程。

### macOS

```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

默认产物：

- `dist/ThesisFormatFixer.app`
- 构建脚本默认把 PyInstaller 缓存写到项目内 `.pyinstaller/`，避免受用户目录全局缓存权限影响
- 构建脚本会在完成后立即检查 `dist/ThesisFormatFixer.app/Contents/Resources/rules`
- 2026-04-22 已在 macOS 环境真实构建并成功启动一次 `.app`
- macOS 主交付入口为 `.app`；仓库中的 `.command` 仅保留为开发/排障辅助入口

### Windows

```bat
scripts\build_windows.bat
```

默认产物：

- `dist\ThesisFormatFixer.exe`
- 构建脚本默认把 PyInstaller 缓存写到项目内 `.pyinstaller\`
- Windows 侧本轮仅完成脚本与 README 验收口径补齐，**未在真实 Windows 环境完成构建与启动**

### 打包说明

- PyInstaller 配置文件：`packaging/pyinstaller.spec`
- 打包入口：`src/thesis_format_fixer/gui.py`
- macOS `.app` 会把 `rules/` 打进 `Contents/Resources/rules`
- 源码运行、PyInstaller frozen 运行、macOS `.app` bundle 运行共用同一套规则定位逻辑
- GUI 默认输出目录位于用户主目录下，避免把结果写回临时解包目录或应用 bundle 内部
- Windows 产物为单个 `exe`；macOS 产物为 `.app`
- 当前真实验收结论：
  - macOS：已真实完成 `pip install`、PyInstaller 构建、`.app` 启动
  - Windows：未真实构建，不能宣称已验收

## 6. 发布说明

当前发布闭环为“本地构建后直接分发压缩包 / app / exe”：

- macOS：分发 `dist/ThesisFormatFixer.app`
- Windows：分发 `dist\ThesisFormatFixer.exe`
- `.command` 不再作为 macOS 主交付入口，仅用于开发环境下从源码树快速启动 GUI
- README 中保留源码运行方式，便于开发与验收
- 本轮不包含商店分发、自动更新、签名、公证和安装器美化

建议发布前最少执行：

- `pytest tests/test_smoke.py tests/test_task020_gui.py tests/test_task023_user_summary.py`
- 在目标平台手工启动一次 GUI，确认窗口可打开、可选择输入、可写出结果
- Windows 发布前必须在真实 Windows 环境至少补做一次：
  - `pip install -r requirements.txt`
  - `scripts\build_windows.bat`
  - 启动 `dist\ThesisFormatFixer.exe`

## 7. 单文件处理流程（GUI/CLI 一致走 runner/report）

1. 选择输入 `.docx`。
2. 选择输出目录（GUI）或 `--out`（CLI fix）。
3. 运行 `check` 或 `fix`。
4. 在输出目录查看生成产物（报告或修复文件+报告）。

## 8. 批量处理流程

1. 指定输入目录（默认递归扫描 `.docx`）。
2. 指定输出目录。
3. 执行 `batch-fix`。
4. 查看批处理汇总：`batch_summary.json`、`batch_summary.md`。
5. 查看每个文件的 `exit_code` 与产物路径。

## 9. 输出文件说明

### 单文件 `check`

- `*.check.report.json`
- `*.check.report.md`
- `check.user_summary.md`

### 单文件 `fix`

- `*.fixed.docx`
- `*.report.json`
- `*.report.md`
- `fix.user_summary.md`

### 批量 `batch-fix`

- 每个输入文件对应：`*.fixed.docx` + `*.report.json` + `*.report.md` + `*.user_summary.md`
- 保持输入目录的相对结构
- 汇总文件：
  - `batch_summary.json`
  - `batch_summary.md`

## 10. 当前支持范围（A/B/C 边界内）

- A 类低风险自动修复（已冻结白名单）
- B 类自动检查、报告提示
- C 类保持人工复核，不自动改写
- GUI 与 CLI 共用 `runner` 与 `report_builder` 主链路

规则基线与映射参考：

- `rules/FORMAT_RULEBOOK_v3.md`
- `docs/RULE_TO_ENGINE_MAPPING_TASK-003.md`
- `docs/V1_OUT_OF_SCOPE_TASK-003.md`

## 11. 当前未支持范围

以下仍为 out-of-scope，不应宣称已支持：

- 封皮模板重建与精细布局重建
- 自动目录域重建
- 正文起始分节与页码系统重构
- 脚注按页重编
- 装订线版面重排
- 参考文献内容级语义纠错/复杂重排

## 12. 常见问题与失败提示

- 输入文件不存在：会明确提示 `输入文件不存在`。
- 输入不是 `.docx`：会明确提示 `输入文件必须是 .docx`。
- 批量目录为空：会产出 `batch_summary`，并提示未找到 `.docx`。
- 输出目录不可写：会明确提示 `输出目录不可写/不可创建`。
- 打包后 GUI 无法读取规则：优先检查产物内是否包含 `rules/` 目录；当前 PyInstaller 配置已默认打包该目录。
- 批量中单个文件失败：不会中断全部任务，会在汇总中显示该文件 `exit_code` 与错误信息。
- GUI 运行失败：显示可理解错误信息，不向普通用户直出 Python traceback。

## 13. 规则来源

- `rules/FORMAT_RULEBOOK_v3.md`
- `rules/FORMAT_RULEBOOK_v2.md`
- `rules/sources/FORMAT_RULEBOOK_v1.md`
- `rules/sources/8. 毕业论文正文写作格式要求.docx`
- `rules/sources/10.1论文封皮.pdf`
- `rules/sources/太院教字[2021]03号太原学院毕业论文（设计）管理办法（终稿）.pdf`
