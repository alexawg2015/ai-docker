# Dockerfile — multi-stage, < 800 MB, non-root user, HEALTHCHECK
#
# ІДЕЯ multi-stage:
#   Stage 1 (builder) — встановлюємо залежності у віртуальне середовище
#   Stage 2 (runtime) — копіюємо ТІЛЬКИ .venv і код, без build-інструментів
#
# Результат: фінальний образ не містить pip, компіляторів, кешу — лише те що треба

# ──────────────────────────────────────────────
# Stage 1: builder — встановлення залежностей
# ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Встановлюємо системні залежності для компіляції (якщо потрібно)
# --no-install-recommends — мінімум пакетів
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Спочатку копіюємо тільки requirements — для кешування шарів Docker
# Якщо змінити лише код (не requirements) — pip install НЕ перезапуститься
COPY app/requirements.txt .

# Встановлюємо в ізольоване venv всередині /app/.venv
RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir --upgrade pip \
    && /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# ──────────────────────────────────────────────
# Stage 2: runtime — фінальний легкий образ
# ──────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Копіюємо ТІЛЬКИ готове venv з builder — без pip, компіляторів, кешу
COPY --from=builder /app/.venv /app/.venv

# ──────────────────────────────────────────────
# Non-root user — безпека
# ──────────────────────────────────────────────
# За замовчуванням Docker запускає контейнер як root — це небезпечно.
# Якщо зломщик вийде з контейнера — він root на хості.
# Створюємо окремого користувача без привілеїв:
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --no-create-home appuser \
    && chown -R appuser:appgroup /app

USER appuser

# Копіюємо код додатку і дані з правами appuser
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup data/ ./data/

# Додаємо venv до PATH щоб python/uvicorn запускались без префіксу
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1


EXPOSE 8000

# ──────────────────────────────────────────────
# HEALTHCHECK — Docker сам перевіряє чи сервіс живий
# ──────────────────────────────────────────────
# --interval=10s  — перевіряти кожні 10 секунд
# --timeout=5s    — якщо не відповів за 5с — помилка
# --start-period=15s — не перевіряти перші 15с (час на запуск)
# --retries=3     — 3 невдалі спроби = unhealthy
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, json; \
        r = urllib.request.urlopen('http://localhost:8000/health'); \
        d = json.loads(r.read()); \
        exit(0 if d.get('status') == 'ok' else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
