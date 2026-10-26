# Panna API — Azure Container Apps image
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# install deps first for layer caching
COPY pyproject.toml ./
RUN pip install --upgrade pip && \
    pip install fastapi "uvicorn[standard]" pydantic httpx "agent-framework>=1.23" "mcp>=2.0"

# app source
COPY src ./src

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
