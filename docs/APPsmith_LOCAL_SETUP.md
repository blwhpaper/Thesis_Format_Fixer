# Appsmith 本地启动说明

## 1. 参考依据

本地启动方案采用 Appsmith 官方自托管 Docker 路径，主要参考：

- Appsmith 官方站点关于平台与自托管入口说明：<https://docs.appsmith.com/>
- Appsmith 官方博客对单容器 Docker 部署架构的说明：<https://www.appsmith.com/blog/appsmith-deployment-architecture>
- Appsmith 官方 Docker Hub 镜像仓库：<https://hub.docker.com/u/appsmith>

说明：

- 结合官方资料可确认，当前 Appsmith 社区版支持通过官方镜像进行本地 Docker 自托管。
- 本仓当前采用最小可运行的 CE 方案，不涉及外部 MongoDB、外部 Redis、鉴权或生产化配置。

## 2. 仓内启动文件

启动文件位置：

- `appsmith/docker-compose.yml`

内容要点：

- 使用 `appsmith/appsmith-ce`
- 映射 `8080 -> 80`
- 映射 `8443 -> 443`
- 把 `./stacks` 挂载到 `/appsmith-stacks`

## 3. 启动命令

前提：

- 本机已完成 Docker Desktop 安装
- Docker Desktop 已手动启动并完成初始化

```bash
cd /Users/apple/Projects/Thesis_Format_Fixer/appsmith
docker compose up -d
```

状态检查：

```bash
docker compose ps
docker compose logs --tail=100
```

本地访问：

- `http://127.0.0.1:8080`

如果浏览器被自动跳转到 HTTPS，也可尝试：

- `https://127.0.0.1:8443`

## 4. 停止 / 重启

停止：

```bash
cd /Users/apple/Projects/Thesis_Format_Fixer/appsmith
docker compose stop
```

重启：

```bash
cd /Users/apple/Projects/Thesis_Format_Fixer/appsmith
docker compose restart
```

移除容器：

```bash
cd /Users/apple/Projects/Thesis_Format_Fixer/appsmith
docker compose down
```

## 5. 本轮 UI 包含的页面与组件

本轮先收口为一个首页骨架，对应布局资产见：

- `appsmith/skeleton/page_blueprint.json`
- `appsmith/preview/index.html`

首页包含以下组件模块：

- 顶部应用标题与模式切换
- 单文件处理卡片
- 批量处理卡片占位
- 结果摘要卡片
- 详细问题表格
- 产物下载区
- 人工复核说明区

其中摘要区固定体现三层结果语义：

- 已自动修复
- 检测到异常但未自动修改
- 需人工复核

## 6. mock 数据组织方式

mock 数据位于：

- `appsmith/mock/empty-result.json`
- `appsmith/mock/check-result.json`
- `appsmith/mock/fix-result.json`
- `appsmith/mock/failure-result.json`

组织原则：

- `empty` 表示未上传文件前的空状态
- `check` 表示检查模式完成后的成功态
- `fix` 表示修复模式完成后的成功态
- `failure` 表示处理失败态

每个 mock 文件都包含：

- 顶层任务状态
- 用户可读摘要
- 三层结果统计
- 详细问题表格行
- 产物区可展示信息

这样后续切换到真实 API 时，只需要把页面绑定从本地 JSON 替换为真实接口响应。

## 7. 本地 UI 预览方式

在 Appsmith 真正启动前，可先运行仓内预览壳子检查页面联动：

```bash
cd /Users/apple/Projects/Thesis_Format_Fixer
python3 -m http.server 18080
```

预览地址：

- `http://127.0.0.1:18080/appsmith/preview/`

本轮已实际验证：

- 预览页 URL 返回 `HTTP 200`
- mock JSON URL 返回 `HTTP 200`

该预览页已实现：

- check / fix 模式切换
- 空状态 / 成功 / 失败切换
- 摘要联动
- 表格联动
- 下载区联动
- 人工复核说明联动

## 8. 下一步如何接本地 API

建议接入顺序如下：

1. 在本机启动现有 Python API

```bash
cd /Users/apple/Projects/Thesis_Format_Fixer
source .venv/bin/activate
thesis-format-fixer-api
```

2. 在 Appsmith 中配置 REST API datasource，指向：

- `http://host.docker.internal:8000`

说明：

- 若 Appsmith 运行在 Docker Desktop 内，容器访问宿主机本地服务通常使用 `host.docker.internal`
- 若未来改为非容器部署，可直接改成 `http://127.0.0.1:8000`

3. 在 Appsmith 中建立查询：

- `submitCheckJob` -> `POST /api/jobs/check`
- `submitFixJob` -> `POST /api/jobs/fix`
- `getJobResult` -> `GET /api/jobs/{{jobId}}`

4. 把页面上的 mock 绑定逐步替换为真实查询返回值

5. 最后再接下载按钮：

- `{{appsmith.store.result.artifacts.download_fixed_docx_url}}`
- `{{appsmith.store.result.artifacts.download_report_md_url}}`

## 9. 本轮不做的事

本轮明确不包含：

- 改写现有 `runner.py` 核心处理链路
- 真实生产部署
- 用户鉴权
- 公网发布
- 批量真实执行 API

## 10. 当前实际阻塞点

本轮未能真实启动 Appsmith 的原因不是配置文件缺失，而是本机 Docker Desktop 安装未完成。

已确认的具体阻塞点：

- `brew install --cask docker` 已进入安装流程
- 但在链接 Docker CLI 时触发 `/usr/local/cli-plugins` 的系统级写权限需求
- 自动化会话无法代替用户输入系统密码

因此，只要用户在本机手动完成 Docker Desktop 安装并启动，本仓内的 `appsmith/docker-compose.yml` 就可继续用于下一步真实拉起。
