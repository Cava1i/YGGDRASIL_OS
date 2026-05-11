# GitHub 上传检查清单

## 上传前

- 确认 `.gitignore` 已排除数据库、上传附件、依赖目录和本地环境文件。
- 删除或替换 README / 手册中的真实账号、真实密码、真实比赛数据。
- 使用 `docs/testdata/yggdrasil_sample_tasks.xlsx` 作为公开演示数据。
- 为截图打码：不要出现真实 token、真实 IP、真实队员隐私。

## 建议提交的内容

- 前端源码：`frontend/src/`、`frontend/package.json`、`frontend/vite.config.js`
- 后端源码：`backend/app.py`、`backend/models.py`、`backend/requirements.txt`
- 文档：`README.md`、`docs/`
- 配置模板：`.env.example`、`frontend/.env.example`、`.editorconfig`
- 启动脚本：`start_backend.bat`、`start_frontend.bat`
- 示例数据：`docs/testdata/yggdrasil_sample_tasks.xlsx`

## 不建议提交的内容

- `node_modules/`
- `frontend/dist/`
- `backend/*.db`
- `backend/instance/*.db`
- `backend/uploads/`
- `.env`
- `.env.local`
- `frontend/.env.local`
- IDE 私有配置，如 `.idea/`

## 首次上传命令参考

```powershell
cd "<项目目录>"
git init
git add .
git commit -m "Initial release"
git branch -M main
git remote add origin https://github.com/Cava1i/YGGDRASIL_OS.git
git push -u origin main
```
