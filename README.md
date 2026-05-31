# Lesson 13 — Containers for AI

RAG boilerplate (FastAPI + OpenAI/Ollama embeddings) containerized with Docker.

## Середовище розробки

- **Залізо:** AMD Ryzen 7 6800H · 32 GB RAM · NVIDIA RTX 3050 Ti Laptop (4 GB VRAM)
- **ОС:** Windows 11 Pro
- **Python:** 3.14 (локально) · 3.11 (Docker/production)

## Архітектура

```
localhost:8000  →  app (FastAPI RAG)
localhost:6335  →  Qdrant (vector DB)
localhost:6379  →  Redis
localhost:3000  →  Langfuse v2 (LLM observability)
localhost:11434 →  Ollama (локальний LLM, тільки в ollama compose)
```

## Швидкий старт

```bash
# 1. Скопіюй .env і додай свій ключ
cp .env.example .env
# Відкрий .env і встав OPENAI_API_KEY=sk-...

# 2. Запусти всі сервіси
docker compose up --build

# 3. Перевір що сервер готовий
curl http://localhost:8000/health
# {"status": "ok"}

# 4. Постав питання
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a vector database?"}'
```

## Таблиця метрик

| Метрика | Naive | Multi-stage |
|---|---|---|
| Image size | 1.76 GB | 547 MB |
| Build time (перший) | 69 сек | 91 сек |
| Rebuild after code change | 19 сек | 1.8 сек |
| Cold start (до `/health=ok`) | ~3 сек | ~3 сек |

**Висновок:** multi-stage образ у 3.2× менший і rebuild після зміни коду у 10× швидший.
Перший build multi-stage повільніший бо встановлює build-essential для компіляції,
але цей шар кешується і при наступних запусках не повторюється.

## Структура файлів

```
.
├── .github/
│   └── workflows/
│       └── docker-publish.yml      # CI: build + push у GHCR
├── app/
│   ├── config.py                   # читає OLLAMA_BASE_URL або OpenAI key
│   ├── main.py
│   ├── rag.py                      # підтримує OpenAI і Ollama через env vars
│   └── requirements.txt
├── data/
│   └── faq.jsonl
├── screenshots/
│   ├── ask1.png
│   ├── docker_images.png
│   ├── GHCR.png
│   ├── ollama_ask3.png
│   └── status_all_containers_and_ask2.png
├── .dockerignore
├── docker-compose.ollama.yml       # app + Ollama + Qdrant + Redis (без OpenAI)
├── docker-compose.yml              # app + Qdrant + Redis + Langfuse v2
├── Dockerfile                      # multi-stage, < 600 MB, non-root, HEALTHCHECK
└── Dockerfile.naive                # простий baseline для порівняння (~1.76 GB)
```

## Додатково зроблено

### Push у GHCR

Образ автоматично публікується у GitHub Container Registry після кожного push у main.

```bash
# Завантажити образ без клонування репо:
docker pull ghcr.io/alexawg2015/ai-docker:latest
docker run -p 8000:8000 --env-file .env ghcr.io/alexawg2015/ai-docker:latest
```

GitHub Actions workflow: `.github/workflows/docker-publish.yml`

### Free-tier через Ollama локально

Запуск без OpenAI API ключа — використовує локальні моделі:

```bash
# 1. Запустити
docker compose -f docker-compose.ollama.yml up --build

# 2. Завантажити моделі (одноразово, ~2.3 GB)
docker compose -f docker-compose.ollama.yml exec ollama ollama pull nomic-embed-text
docker compose -f docker-compose.ollama.yml exec ollama ollama pull llama3.2:3b

# 3. Перевірити яка модель відповідає
curl http://localhost:8000/metadata
# {"embedder":"nomic-embed-text","llm":"llama3.2:3b","docs_count":20,"ready":true}
```

Реалізація: `app/rag.py` читає env змінну `OLLAMA_BASE_URL`.
Якщо вона є — ходить туди, якщо ні — до OpenAI. Один код, різна поведінка через конфіг.

---

## Проблеми які виникли і як вирішувались

### 1. Python 3.14 — несумісність з pydantic-core і numpy

**Проблема:** локальна версія Python 3.14 не має pre-built wheels для pydantic-core
(потребує компіляції Rust) і numpy 2.2.0 (потребує компіляції C через Meson).
Встановлення падало з помилкою `linker 'link.exe' not found`.

**Рішення:** пропустили локальний запуск повністю і перейшли до Docker.
Docker будує образ з Python 3.11 де всі залежності встановлюються без проблем.
Це підтверджує головну ідею Docker — незалежність від локального середовища.

---

### 2. Langfuse v3 потребує Clickhouse

**Проблема:** `langfuse/langfuse:latest` (v3) при запуску падав з помилкою:
```
CLICKHOUSE_URL is not configured
```
Версія 3 змінила архітектуру і потребує окремий Clickhouse сервер.

**Рішення:** замінили тег на `langfuse/langfuse:2` — версія 2 працює
тільки з PostgreSQL без Clickhouse.

---

### 3. Qdrant healthcheck — відсутність curl і wget

**Проблема:** Qdrant використовує мінімальний образ без curl і wget.
Healthcheck `wget -qO- http://localhost:6333/healthz` падав з:
```
exec: "wget": executable file not found in $PATH
```

**Рішення:** використали bash TCP trick — відкриває з'єднання без зовнішніх утиліт:
```yaml
test: ["CMD-SHELL", "bash -c 'echo > /dev/tcp/localhost/6333'"]
```

---

### 4. useradd блокував кеш при зміні коду

**Проблема:** `RUN groupadd && useradd` стояв після `COPY app/` і займав ~20 сек.
При кожній зміні коду цей крок перезапускався — замість 1-2 сек rebuild займав 25+ сек.

**Рішення:** переставили `RUN groupadd/useradd` перед `COPY app/` і додали `--chown`:
```dockerfile
RUN groupadd --system appgroup && useradd ...   # тепер кешується
COPY --chown=appuser:appgroup app/ ./app/        # miss тільки тут
```
Результат: rebuild після зміни коду — 1.8 секунди.

---

### 5. GitHub Actions — застарілі версії actions

**Проблема:** перший workflow впав з двома помилками:
- `buildx failed` — не було кроку `setup-buildx-action`
- `Unexpected input 'dockerfile'` — `build-push-action@v5` змінив параметр

**Рішення:** додали `docker/setup-buildx-action@v3` і оновили до `build-push-action@v6`.

---

### 6. Ollama — модель відсутня при старті app

**Проблема:** app стартував і одразу падав з 404:
```
Client error '404 Not Found' for url 'http://ollama:11434/v1/embeddings'
```
Ollama сервер запустився але моделей ще не було.

**Рішення:** завантажили моделі вручну після старту:
```bash
docker compose -f docker-compose.ollama.yml exec ollama ollama pull nomic-embed-text
docker compose -f docker-compose.ollama.yml exec ollama ollama pull llama3.2:3b
```
Моделі зберігаються у volume `ollama_models` і при наступних запусках не потрібно
завантажувати знову.

---

### 7. llama3.2:3b — digest mismatch при завантаженні

**Проблема:** завантаження 2 GB файлу переривалось і файл був пошкоджений:
```
Error: digest mismatch, file must be downloaded again
```

**Рішення:** повторний запуск `ollama pull` — Ollama автоматично визначає
пошкоджений файл і завантажує заново.

---

## Пояснення ключових рішень

### Чому multi-stage?
Builder stage встановлює залежності і компілятори. Runtime stage копіює
тільки готове `.venv` і код — без gcc, apt-кешів, тимчасових файлів.

### Чому non-root user?
Якщо зловмисник зламає додаток — він буде `appuser` без привілеїв,
а не `root` на хості.

### Чому порядок COPY важливий?
```dockerfile
COPY app/requirements.txt .   # кешується окремо — рідко змінюється
RUN pip install ...            # не перезапускається якщо requirements незмінні
COPY app/ ./app/               # часто змінюється — але це лише 0.2 сек
```
