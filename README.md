# 归源 · 家族记忆助手

面向单管理员的中文族谱 Web 应用。它可以维护人物、父母/配偶关系和私密档案，通过确定性规则回答亲属关系，并让托管模型把自然语言整理为待确认草稿。模型不能直接写正式数据。

## 已实现

- 单管理员登录、服务端会话和 CSRF 防护。
- 人物增删改查、父母/配偶关系维护、重复与祖先循环校验。
- 确定性亲属路径和常见中文称谓。
- PDF、图片、文字资料私密上传、哈希校验、鉴权下载和证据关联。
- OpenAI 兼容 Chat Completions 适配层、来源支撑回答、重名与冲突提示。
- 智能体变更草稿、确认前重新校验、事务写入和审计日志。
- React 中文管理界面、Alembic 迁移、Docker Compose、Caddy HTTPS、备份与恢复脚本。

## 本地开发

需要 Node.js 20+ 与 Python 3.12+。

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e "backend[test]"
npm ci
```

可在项目根目录创建未提交的 `.env`：

```dotenv
GUIYUAN_ADMIN_PASSWORD=your-local-admin-password
GUIYUAN_MODEL_API_KEY=your-provider-key
GUIYUAN_MODEL_BASE_URL=https://provider.example/v1
GUIYUAN_MODEL_NAME=provider-model-name
```

分别启动后端和前端：

```bash
python -m alembic -c backend/alembic.ini upgrade head
python -m uvicorn backend.app.main:app --reload
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`。Vite 会把 `/api` 转发到本地 FastAPI。开发环境未配置模型时，普通族谱管理仍可使用，智能体查询会显示模型未配置。

## 测试

```bash
npm run test:all
```

浏览器端到端测试需要 Playwright 浏览器：

```bash
npx playwright install chromium
npm run test:e2e
```

本项目也可以通过 `PLAYWRIGHT_EXECUTABLE_PATH` 使用系统 Chrome/Edge，通过 `E2E_API_COMMAND` 指定测试 API 启动命令。

## 生产部署与备份

复制 `.env.example` 为 `.env`，替换所有示例密钥后执行：

```bash
docker compose config
docker compose up -d --build
```

完整的首次部署、更新、备份和安全恢复流程见 [部署文档](docs/deployment.md)。产品边界见 [产品设计文档](docs/product-design.md)，架构决策见 [技术方案](docs/technical-design.md)。
