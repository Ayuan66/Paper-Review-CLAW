# Paper Review CLAW

## Configuration

### Local setup

1. Install the required runtimes:

```bash
# Python 3.11+ recommended
# Node.js 18+ recommended
```

2. Install backend dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Create the backend environment file:

```bash
cd backend
cp .env.example .env
```

4. Edit `backend/.env` and set at least:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
FLASK_DEBUG=true
MAX_AUTHOR_ITERATIONS=5
```

5. Install frontend dependencies:

```bash
cd frontend
npm install
```

### Docker setup

For Docker-based usage, you only need to prepare:

```bash
cp backend/.env.example backend/.env
```

Then update `backend/.env` with your real `OPENROUTER_API_KEY`.

## Run

### Run locally

Start the backend on port `6000`:

```bash
cd backend
source .venv/bin/activate
python app.py
```

Start the frontend on port `3000`:

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:3000
```

The Vite dev server proxies `/api` requests to `http://localhost:6000`.

### Run with Docker Compose

Build the images:

```bash
docker compose build
```

This creates:

```text
paper-review-claw-backend:latest
paper-review-claw-frontend:latest
```

Then start both services:

```bash
docker compose up
```

Then open:

```text
http://localhost:3000
```

The frontend container serves the built app with Nginx and proxies `/api` requests to the backend container.
