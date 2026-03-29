# Paper Review Claw

## 配置

1. 安装运行环境：

```bash
# Python 3.11+（建议）
# Node.js 18+（建议）
```

2. 安装后端依赖：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. 配置后端环境变量：

```bash
cd backend
cp .env.example .env
```

然后编辑 `backend/.env`，至少需要填写：

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
FLASK_DEBUG=true
MAX_AUTHOR_ITERATIONS=5
```

4. 安装前端依赖：

```bash
cd frontend
npm install
```

## 运行

1. 启动后端服务（默认端口 `6000`）：

```bash
cd backend
source .venv/bin/activate
python app.py
```

2. 启动前端开发服务（默认端口 `3000`）：

```bash
cd frontend
npm run dev
```

3. 打开浏览器访问：

```text
http://localhost:3000
```

前端会通过 Vite 代理将 `/api` 请求转发到 `http://localhost:6000`，因此本地开发时只需要同时启动前后端即可。
