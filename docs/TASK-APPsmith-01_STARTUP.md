# TASK-APPsmith-01 启动记录

## 1. 已核验文件

本轮先实际读取并核验了以下文件与目录：

- `README.md`
- `docs/TASK-APP-01_APPSMITH_API_SPEC.md`
- `src/thesis_format_fixer/api/app.py`
- `src/thesis_format_fixer/api/models.py`
- `src/thesis_format_fixer/api/service.py`
- 项目根目录结构与 `src/`、`docs/`、`tests/`、`rules/` 目录

说明：

- 本轮未修改 `src/thesis_format_fixer/app/runner.py` 等核心处理链路文件。
- UI 骨架继续沿用仓内已有的本地 HTTP API 方向，不引入真实外网发布、生产部署或鉴权。

## 2. 实际执行过的命令

以下命令已在本机实际执行：

```bash
pwd
rg --files
rg -n "^#|Appsmith|Docker|docker|README|thesis_format_fixer" README* docs -g 'README*'
ls -la
sed -n '1,220p' README.md
sed -n '1,220p' docs/TASK-APP-01_APPSMITH_API_SPEC.md
docker --version
docker compose version
docker info --format '{{.ServerVersion}}'
which docker
which docker-compose
rg -n "Appsmith|appsmith" .
brew --version
ls /Applications | rg '^Docker\\.app$'
brew info --cask docker
sed -n '1,260p' src/thesis_format_fixer/api/app.py
sed -n '1,260p' src/thesis_format_fixer/api/models.py
sed -n '1,260p' src/thesis_format_fixer/api/service.py
git status --short
```

当前还额外执行了以下安装命令：

```bash
brew install --cask docker
python3 -m http.server 18080
curl -I http://127.0.0.1:18080/appsmith/preview/
curl -I http://127.0.0.1:18080/appsmith/mock/check-result.json
ls -ld /usr/local /usr/local/bin /usr/local/cli-plugins
```

## 3. Docker / Docker Compose 核验结果

本轮首次核验结论：

- `docker` 不存在于当前 PATH
- `docker-compose` 不存在于当前 PATH
- `/Applications/Docker.app` 初始时不存在
- `brew info --cask docker` 可读到 `docker-desktop` 包信息，说明本机可通过 Homebrew 安装 Docker Desktop

因此，真实拉起 Appsmith 的前置条件不是“容器命令失败”，而是“本机尚未安装 Docker Desktop”。

后续安装尝试中，Homebrew 的失败点也已确认：

- 安装流程可下载并开始安装 `docker-desktop`
- 但在链接 CLI 到 `/usr/local/cli-plugins` 时需要系统级权限
- 当前自动化环境无法代替用户输入 `sudo` 密码
- 因此 Docker Desktop 本轮未完成可用安装

## 4. Appsmith 自托管启动方案

仓内已新增：

- `appsmith/docker-compose.yml`

该文件采用 Appsmith Community Edition 的最小 Docker 启动方式，容器名固定为：

- `thesis-format-fixer-appsmith`

预设端口：

- `http://127.0.0.1:8080`
- `https://127.0.0.1:8443`

预设持久化目录：

- `appsmith/stacks/`

待 Docker Desktop 安装完成后，建议按以下顺序执行：

```bash
cd appsmith
docker compose up -d
docker compose ps
docker compose logs --tail=100
```

停止方式：

```bash
cd appsmith
docker compose stop
```

完全移除当前容器但保留数据卷目录：

```bash
cd appsmith
docker compose down
```

## 5. 本轮仓内已落地成果

即使 Appsmith 容器尚未完成拉起，本轮仍已把与 UI 壳子相关的可保留成果落到仓内：

- `appsmith/docker-compose.yml`
- `appsmith/mock/*.json`
- `appsmith/skeleton/page_blueprint.json`
- `appsmith/preview/index.html`
- `appsmith/preview/styles.css`
- `appsmith/preview/app.js`

这些文件实现了：

- Appsmith 页面结构蓝图
- check / fix / 失败 / 空状态四组 mock 数据
- 三层结果语义展示
- 单文件与批量处理布局分区
- 产物下载区和人工复核说明区占位
- 后续真实 API 接入位说明

同时，本轮还已实际验证本地 mock 预览资源可被宿主机访问：

- `http://127.0.0.1:18080/appsmith/preview/` 返回 `HTTP 200`
- `http://127.0.0.1:18080/appsmith/mock/check-result.json` 返回 `HTTP 200`

## 6. 当前卡点

只有在以下两个条件都满足后，才能宣称“Appsmith 已真实启动成功”：

1. Docker Desktop 安装完成并成功启动
2. `docker compose up -d` 成功且本地浏览器可访问 `http://127.0.0.1:8080`

在这两步未完成之前，不能伪造“已启动成功”结论。
