# TASK-033 macOS App 化收口验收

日期：2026-04-22

## 1. 目标

- 将 macOS 主交付形态收口为 `dist/ThesisFormatFixer.app`
- 不再把 `.command` 作为主交付入口
- 确保运行时规则目录从 macOS bundle 的 `Contents/Resources/rules` 稳定加载

## 2. 如何构建 `.app`

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
PYTHON_BIN=./.venv/bin/python ./scripts/build_macos.sh
```

构建成功后主产物为：

- `dist/ThesisFormatFixer.app`

构建脚本会额外做一项强制校验：

- 若 `dist/ThesisFormatFixer.app/Contents/Resources/rules` 不存在，则直接报错退出

## 3. 如何双击启动

- 在 Finder 中双击 `dist/ThesisFormatFixer.app`
- 如果是命令行辅助验证，可执行：

```bash
open -na /Users/apple/Projects/Thesis_Format_Fixer/dist/ThesisFormatFixer.app
```

`.command` 仍保留在仓库中，但它仅用于开发/排障时从源码树启动 GUI，不属于发布交付入口。

## 4. 如何验证 rules 资源已打包

构建后执行：

```bash
find dist/ThesisFormatFixer.app/Contents/Resources -maxdepth 2 -print
```

验收通过的关键条件：

- 存在 `dist/ThesisFormatFixer.app/Contents/Resources/rules`
- 该目录下存在 `FORMAT_RULEBOOK_v1.md`
- 运行时规则定位优先支持三种场景：
  - 开发态源码目录
  - PyInstaller frozen 态
  - macOS `.app` bundle 的 `Contents/Resources`

## 5. 本任务验收关注点

- `packaging/pyinstaller.spec` 已把 `rules/` 作为 bundle 资源打包
- `src/thesis_format_fixer/runtime_paths.py` 已显式识别 macOS `.app` bundle
- `src/thesis_format_fixer/io/rulebook.py` 读取规则时使用运行时资源路径，不依赖源码目录兜底
- 最小 smoke 测试覆盖 macOS bundle 规则路径解析

## 6. 已知限制

- 本任务不包含签名
- 本任务不包含公证
- 本任务不包含 DMG 或安装器封装
- 未签名/未公证的 `.app` 在目标机器上可能触发 Gatekeeper 提示，属于当前交付边界内的已知限制
- 本轮主要验证 `.app` 可构建、bundle 内资源齐备、运行时路径闭环成立；不扩大到 GUI 全量人工回归

## 7. 为什么签名/公证不在本任务内

TASK-033 的目标是先把交付形态稳定收口到可双击启动的 `.app`，并确保 bundle 内资源路径闭环成立。签名、公证、DMG 属于后续发布链路增强，依赖 Apple 开发者证书、账户配置和独立验收标准，超出本任务“最小改动收口”的范围。
