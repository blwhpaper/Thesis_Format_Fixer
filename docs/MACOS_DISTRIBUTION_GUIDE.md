# macOS Distribution Guide

日期：2026-04-22

## 1. 目标与边界

- 当前 macOS 主交付形态是 `ThesisFormatFixer.app`
- 当前不做 Mac App Store 上架
- 当前保留两套分发口径：
  - 无 Apple Developer 账号：未签名试用分发
  - 有 Apple Developer 账号：Developer ID 签名 + 公证后的正式分发

## 2. 构建产物与命名

执行：

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
PYTHON_BIN=./.venv/bin/python ./scripts/build_macos.sh
```

默认产物：

- `dist/ThesisFormatFixer.app`
- `dist/ThesisFormatFixer-macOS-unsigned.zip`

命名口径：

- `ThesisFormatFixer.app`：本地验收与签名前原始 bundle
- `ThesisFormatFixer-macOS-unsigned.zip`：无账号试用分发的推荐压缩包名
- `ThesisFormatFixer-macOS-signed.zip`：已签名但未必公证时的建议命名
- `ThesisFormatFixer-macOS-notarized.zip`：已签名且已公证时的建议命名

## 3. 未签名试用分发

适用场景：

- 内部试用
- 导师/同学小范围试用
- 没有 Apple Developer 账号

推荐发给用户的文件：

- `ThesisFormatFixer-macOS-unsigned.zip`

推荐同时附带的说明：

1. 解压缩得到 `ThesisFormatFixer.app`
2. 双击 `ThesisFormatFixer.app`
3. 如果系统提示“无法验证开发者”或出现同类拦截，先关闭提示
4. 打开“系统设置 -> 隐私与安全性”，在安全提示区域选择仍要打开
5. 再次打开应用

说明：

- 不同 macOS 版本提示文案会略有差异
- 未签名应用可能被 Gatekeeper 拦截，这是当前试用分发方案内的预期现象，不代表应用本身损坏
- 默认输出目录是 `~/ThesisFormatFixerOutput`

## 4. 有账号时的正式分发

适用场景：

- 面向更广泛用户正式发布
- 希望减少 Gatekeeper 阻拦
- 具备 Apple Developer 账号与 Developer ID 证书

推荐流程：

1. 先通过本仓库构建出 `dist/ThesisFormatFixer.app`
2. 对 `.app` 做 Developer ID Application 签名
3. 对已签名产物执行公证
4. 公证通过后再压缩为对外分发包

可参考的命令骨架：

```bash
codesign --deep --force --options runtime \
  --sign "Developer ID Application: YOUR TEAM" \
  dist/ThesisFormatFixer.app

ditto -c -k --keepParent \
  dist/ThesisFormatFixer.app \
  dist/ThesisFormatFixer-macOS-signed.zip

xcrun notarytool submit dist/ThesisFormatFixer-macOS-signed.zip \
  --keychain-profile "YOUR_NOTARY_PROFILE" \
  --wait

xcrun stapler staple dist/ThesisFormatFixer.app

ditto -c -k --keepParent \
  dist/ThesisFormatFixer.app \
  dist/ThesisFormatFixer-macOS-notarized.zip
```

说明：

- 正式分发建议使用公证完成后的 zip
- 若团队后续需要 DMG，可在 notarized `.app` 稳定后再单独扩展，不属于本轮范围

## 5. 图标与启动体验

当前已接入的图标资源：

- `resources/icons/macos/ThesisFormatFixer.icns`
- `resources/icons/macos/ThesisFormatFixer.png`

接入位置：

- PyInstaller bundle 图标：`packaging/pyinstaller.spec`
- GUI 运行时图标：`src/thesis_format_fixer/gui.py`

验收时建议确认：

- Finder 中 `.app` 图标不是默认空白图标
- 启动后 Dock 图标正常
- 主窗口标题为 `Thesis Format Fixer`

## 6. 对外分发建议文案

未签名试用版可直接使用下面这段简化说明：

```text
请先解压 ThesisFormatFixer-macOS-unsigned.zip，然后双击 ThesisFormatFixer.app。
如果 macOS 提示无法验证开发者，请到“系统设置 > 隐私与安全性”中允许打开后再重试。
处理结果默认输出到用户主目录下的 ThesisFormatFixerOutput 文件夹。
```

正式签名版可使用下面这段简化说明：

```text
请解压并双击 ThesisFormatFixer.app。
该版本已完成 Developer ID 签名与公证，正常情况下无需额外放行即可启动。
处理结果默认输出到用户主目录下的 ThesisFormatFixerOutput 文件夹。
```
