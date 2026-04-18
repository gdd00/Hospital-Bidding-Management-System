FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json ./package.json
RUN npm install --legacy-peer-deps

COPY frontend/ ./
RUN npm run build


FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY main.py init_db.py ./
COPY models ./models
COPY backend ./backend
COPY --from=frontend-build /app/static ./static

ENV HOSPITAL_DB_PATH=/app/data/hospital.db

EXPOSE 8100

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]
