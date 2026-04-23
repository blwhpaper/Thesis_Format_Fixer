# TASK-APP-04 验收记录

日期：2026-04-23

## 1. 本轮验收目标

- 源码运行可用
- 打包运行路径逻辑可用
- 规则资源缺失、输出目录不可写等关键失败场景有中文提示
- 部署说明与验收口径可复现

## 2. 本轮实际收口项

- `runtime_paths.py` 增加源码态 / frozen 态 / macOS bundle 态统一资源定位
- 增加运行时 `rules/` 完整性校验
- 增加输出目录前置可写性检查与默认目录回退
- `io/rulebook.py` 增加 `rules/sources/FORMAT_RULEBOOK_v1.md` 回退路径
- `scripts/build_macos.sh` 增加规则文件存在性校验
- `scripts/build_windows.bat` 修正文档口径并校验 dist 目录内规则资源
- README 与独立部署文档同步更新

## 3. 验收步骤

### 3.1 源码态

```bash
python -m thesis_format_fixer.gui
```

关注点：

- GUI 能启动
- 默认输出目录显示为 `~/ThesisFormatFixerOutput`
- 规则资源缺失时弹出中文提示
- 输出目录不可写时会自动切回默认输出目录并提示

### 3.2 打包态资源校验

macOS：

```bash
./scripts/build_macos.sh
```

Windows：

```bat
scripts\build_windows.bat
```

关注点：

- 产物中带有 `rules/`
- 必要规则文件已随包进入
- 构建脚本在资源缺失时直接失败，不把不完整产物当成功

### 3.3 最小自动化测试

```bash
pytest tests/test_smoke.py tests/test_task020_gui.py tests/test_task023_user_summary.py
```

## 4. 通过标准

- [x] 源码运行路径与打包路径分流明确
- [x] `rules/` 在运行时有前置校验
- [x] 输出目录不可写时有前置检查
- [x] 输出目录不可写时具备默认目录回退策略
- [x] GUI 对关键失败场景给出中文可读提示
- [x] 新增 1 份部署文档
- [x] 新增 1 份验收文档
- [x] 补充最小测试

## 5. 已知限制

- 本轮未在真实 Windows 机器完成手工启动验收
- 当前日志目录以部署约定形式保留，未扩展为独立日志系统
- 本轮不扩大到签名、公证、自动更新、安装器封装
