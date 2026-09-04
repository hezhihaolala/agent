# 归源部署与恢复

## 1. 服务器要求

- 一台可联网的 Linux VPS，建议至少 2 核、2 GB 内存。
- 已安装 Docker Engine 与 Docker Compose 插件。
- 一个解析到服务器公网 IP 的域名，80/443 端口已放行。
- 仓库只允许管理员访问；`.env` 和备份文件不得提交到 Git。

## 2. 首次部署

```bash
git clone https://github.com/hezhihaolala/agent.git
cd agent
cp .env.example .env
chmod 600 .env
```

编辑 `.env`，至少替换数据库密码、管理员密码、域名、模型地址、模型名和密钥。管理员密码不能保留示例值。OpenAI 兼容服务的地址通常以 `/v1` 结尾，具体以服务商文档为准。

先检查配置，再启动：

```bash
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 api proxy
```

API 容器每次启动都会先执行 `alembic upgrade head`。Caddy 根据 `GUIYUAN_DOMAIN` 自动申请和续期 HTTPS 证书；数据库没有映射到公网端口。

## 3. 更新

更新前先备份，然后拉取并重建：

```bash
docker compose exec -T -e BACKUP_DIR=/backups api bash scripts/backup.sh
git pull --ff-only
docker compose up -d --build
docker compose ps
```

## 4. 备份

Compose 将备份目录映射到项目下的 `backups/`。执行：

```bash
mkdir -p backups
chmod 700 backups
docker compose exec -T -e BACKUP_DIR=/backups api bash scripts/backup.sh
```

生成的 `guiyuan-backup-*.tar.gz` 同时包含 `database.sql` 和 `archives/`。如果需要保存 `.env`，可额外传入容器内可读的 `ENV_FILE`；包含配置的备份必须加密并离线保存。

建议保留每日 7 份、每周 4 份，并把备份复制到服务器之外。只创建备份不等于可恢复，至少每月在临时环境做一次恢复演练。

## 5. 安全恢复演练

恢复脚本只允许写入空档案目录，避免覆盖现有原件。最安全的方式是在新的目录或新 VPS 上恢复：

```bash
git clone https://github.com/hezhihaolala/agent.git guiyuan-restore
cd guiyuan-restore
cp /secure/location/.env .env
mkdir -p backups
cp /secure/location/guiyuan-backup-YYYYMMDDTHHMMSSZ.tar.gz backups/
docker compose up -d db
docker compose run --rm api bash scripts/restore.sh /backups/guiyuan-backup-YYYYMMDDTHHMMSSZ.tar.gz
docker compose up -d --build
```

登录后抽查人物数量、关系路径、档案下载和操作日志。确认恢复环境无误后，再安排域名切换。不要直接在仍有数据的生产档案卷上执行恢复。

## 6. 故障排查

```bash
docker compose ps
docker compose logs --tail=200 api
docker compose logs --tail=200 db
docker compose exec api python -m alembic -c backend/alembic.ini current
```

- 登录失败：确认 `GUIYUAN_ADMIN_USERNAME` 和首次启动时使用的管理员密码；已有数据库不会因修改环境变量自动重置密码。
- 模型不可用：人物、关系和档案维护仍可使用；检查模型地址、密钥、模型名和服务商兼容性。
- 档案无法下载：确认 `archives` 卷已挂载且 API 容器可以读取文件。
- HTTPS 失败：确认域名已解析到本机，80/443 可从公网访问。
