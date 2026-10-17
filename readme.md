# 指标管理系统

## 前后端启动

需要先安装 Python、Node.js 和 npm。开发时请分别在两个终端启动后端和前端。

### 1. 启动后端

在项目根目录打开终端，执行：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8800
```

后端只支持达梦数据库。启动时会读取 `backend/.env` 中的达梦连接配置，自动运行 Alembic 迁移，将数据库表结构更新到项目当前版本；首次启动还会初始化系统数据。

请先在 `backend/.env` 中配置达梦连接信息，并确保数据库服务已启动。已有达梦服务可按实际安装路径启动，例如：

```powershell
.\server\bin\dmserver.exe .\indicator\dm.ini
```

迁移仅更新表结构并初始化系统数据，不会导入其他数据库中的业务数据。连接达梦库前请确认配置指向正确的数据库，并备份重要数据。

### 2. 启动前端

保持后端运行，在另一个终端从项目根目录执行：

```powershell
cd frontend
npm install
npm run dev
```

启动后访问 <http://127.0.0.1:5173>。前端开发服务器会将 `/api` 请求代理到 `http://127.0.0.1:8800`。

### 常用地址

- 前端：<http://127.0.0.1:5173>
- 后端健康检查：<http://127.0.0.1:8800/api/health>
- 后端 API 文档：<http://127.0.0.1:8800/docs>

请先启动后端，再启动前端；关闭服务时分别在对应终端按 `Ctrl+C`。