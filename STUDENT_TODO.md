# Lesson 13 — TODO

Запусти boilerplate локально (`make install` → `.env` → `make run`), переконайся що `/ask` відповідає. Далі — контейнеризуй.

## Що зробити

1. **`Dockerfile.naive`** — `FROM python:3.11` + `COPY . .` + `pip install`. Заміряй розмір (baseline).
2. **`Dockerfile`** — multi-stage, **< 800 MB**, non-root user, HEALTHCHECK що перевіряє `status: ok`.
3. **`.dockerignore`**.
4. **`docker-compose.yml`** — твій сервіс + Langfuse / Qdrant / Redis.
5. **`README.md`** з таблицею:

| Метрика | Naive | Multi-stage |
|---|---|---|
| Image size | | |
| Build time | | |
| Rebuild after code change | | |
| Cold start (до `/health=ok`) | | |

6. Скріншот `curl -X POST localhost:8000/ask`.

## Здати

PR у `lesson-13-containers-for-ai/homework/submissions/<нік>/` з:

- `Dockerfile`, `Dockerfile.naive`, `docker-compose.yml`, `.dockerignore`
- `README.md` з таблицею метрик
- Скріншоти: `docker images` (обидва образи), `curl /ask` з відповіддю, `docker compose ps`
