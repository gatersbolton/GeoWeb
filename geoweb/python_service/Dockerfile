FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/mpl

WORKDIR /app

COPY python_service/requirements.txt /app/
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY python_service /app/python_service

RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8000

CMD ["uvicorn", "python_service.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]


