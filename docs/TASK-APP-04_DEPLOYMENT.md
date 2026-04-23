# TASK-APP-04 部署与运行说明

日期：2026-04-23

## 1. 目标

- 收口源码运行与打包运行两种形态下的路径、权限与资源定位
- 保证 `rules/`、图标资源、输出目录策略和构建脚本口径一致
- 不扩大到安装器、美化、自动更新、云部署、签名或公证

## 2. 运行形态

### 2.1 源码运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python -m thesis_format_fixer.gui
```

源码态运行时：

- 规则目录定位到仓库根目录下的 `rules/`
- 图标资源定位到仓库根目录下的 `resources/`
- GUI 默认输出目录为 `~/ThesisFormatFixerOutput`

### 2.2 macOS 打包运行

```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
open -na /Users/apple/Projects/Thesis_Format_Fixer/dist/ThesisFormatFixer.app
```

打包后运行时：

- 规则目录定位到 `.app/Contents/Resources/rules`
- 图标资源定位到 `.app/Contents/Resources/resources/icons/macos/`
- 构建脚本会强制校验 `FORMAT_RULEBOOK_v1.md`、`v2.md`、`v3.md`

### 2.3 Windows 打包运行

```bat
scripts\build_windows.bat
dist\ThesisFormatFixer\ThesisFormatFixer.exe
```

Windows 打包产物注意事项：

- 交付对象是整个 `dist\ThesisFormatFixer\` 目录，不是单个 `exe`
- 规则目录应位于 `dist\ThesisFormatFixer\rules\`
- 构建脚本会检查 `rules\FORMAT_RULEBOOK_v1.md`

## 3. 资源定位策略

- 源码态：从仓库根目录读取 `rules/` 与 `resources/`
- PyInstaller `_MEIPASS` 态：从 PyInstaller 解包后的运行时目录读取
- macOS `.app`：从 `Contents/Resources/` 读取
- 规则主入口使用 `rules/FORMAT_RULEBOOK_v1.md`，若缺失则回退尝试 `rules/sources/FORMAT_RULEBOOK_v1.md`

## 4. 输出/报告/临时/日志目录策略

- 输出目录：默认 `~/ThesisFormatFixerOutput`
- 报告目录：与输出目录同目录收口
- 临时目录：约定 `输出目录/temp`
- 日志目录：约定 `输出目录/logs`
- 当前版本主要通过 GUI 中文提示、技术报告和批处理汇总提供排障信息，不引入独立日志服务

可写性策略：

- 执行前先检查用户所选输出目录是否可创建、可写
- 若用户所选目录不可写，且默认输出目录可写，则自动回退到默认输出目录
- 若默认输出目录也不可写，则终止执行并显示中文错误提示
- 不向应用 bundle、`dist/` 资源目录或系统受限目录写结果

## 5. 关键失败提示口径

- 规则目录缺失：提示程序包不完整，请重新解压完整程序包或从项目源码根目录运行
- 规则文件缺失：提示缺少哪几个 `FORMAT_RULEBOOK` 文件
- 输出目录不可写：提示原目录不可写，并在可行时说明已自动切换到默认输出目录
- 输入文件不存在 / 不是 `.docx`：直接显示中文提示
- GUI 打开产物失败：显示中文失败信息，不直接抛 Python traceback 给普通用户

## 6. 构建校验清单

### macOS

- `dist/ThesisFormatFixer.app` 存在
- `dist/ThesisFormatFixer.app/Contents/Resources/rules` 存在
- `FORMAT_RULEBOOK_v1.md`、`v2.md`、`v3.md` 存在
- `dist/ThesisFormatFixer.app/Contents/Resources/ThesisFormatFixer.icns` 存在

### Windows

- `dist\ThesisFormatFixer\ThesisFormatFixer.exe` 存在
- `dist\ThesisFormatFixer\rules` 存在
- `dist\ThesisFormatFixer\rules\FORMAT_RULEBOOK_v1.md` 存在

## 7. 不在本轮范围内

- 不新增后端服务
- 不做云部署
- 不做自动更新
- 不做签名、公证、商店上架
- 不做安装器美化或 DMG/NSIS 深度封装
