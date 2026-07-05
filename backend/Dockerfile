FROM python:3.12-slim

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 默认阿里云源（容器内实测最快）；可用 --build-arg PIP_INDEX_URL=... 切换
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
COPY requirements.txt .
RUN pip install --timeout 120 --retries 10 -i "$PIP_INDEX_URL" -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
