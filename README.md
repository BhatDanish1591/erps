# EduSaaS CRM - School & College Management Platform

A production-ready multi-tenant SaaS platform for schools and colleges.

## Tech Stack

| Layer    | Technology |
|----------|-----------|
| Backend  | FastAPI, SQLAlchemy 2.0, PostgreSQL, Alembic, Redis, Celery |
| Web      | React, Vite, TypeScript, Tailwind CSS, Material UI |
| Mobile   | React Native, Expo, TypeScript, Expo Router |
| Infra    | Docker, Nginx, GitHub Actions |

## Repository Structure

```
erp/
├── backend/          FastAPI application
├── web/              React web portal
├── mobile/           Expo mobile app
├── packages/         Shared TypeScript packages
├── infrastructure/   Docker, Nginx, CI/CD
└── documentation/    API docs, architecture guides
```

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 20 LTS
- pnpm 9+
- Docker Desktop
- PostgreSQL 16+
- Redis 7+

### 1. Configure environment

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp web/.env.example web/.env
cp mobile/.env.example mobile/.env
```

### 2. Start infrastructure (PostgreSQL + Redis)

```bash
docker compose up postgres redis -d
```

### 3. Run backend

```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Run web application

```bash
cd web
pnpm install
pnpm dev
```

### 5. Run mobile application

```bash
cd mobile
pnpm install
npx expo start
```

### 6. Run full stack with Docker

```bash
docker compose up --build
```

## Service URLs (Development)

| Service     | URL                        |
|-------------|---------------------------|
| Backend API | http://localhost:8000      |
| API Docs    | http://localhost:8000/docs |
| Web App     | http://localhost:5173      |
| PostgreSQL  | localhost:5432             |
| Redis       | localhost:6379             |

## Running Tests

```bash
# Backend
cd backend
pytest -v

# Web type-check
cd web
pnpm type-check

# Web tests
cd web
pnpm test
```
