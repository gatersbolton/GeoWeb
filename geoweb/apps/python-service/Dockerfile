FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/mpl

WORKDIR /app

COPY apps/python-service/requirements.txt /app/apps/python-service/requirements.txt
RUN pip install -r /app/apps/python-service/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY apps/python-service/python_service /app/apps/python-service/python_service

# 拷入科研算法代码与数据，满足 python_service/core/paths.py 的路径解析
RUN mkdir -p "/app/packages/compute/borehole-ellipticity" "/app/packages/compute/stress-inversion"
COPY ["packages/compute/borehole-ellipticity/borehole_ellipticity.py", "/app/packages/compute/borehole-ellipticity/borehole_ellipticity.py"]
COPY ["packages/compute/borehole-ellipticity/functions.py", "/app/packages/compute/borehole-ellipticity/functions.py"]
COPY ["packages/compute/borehole-ellipticity/vis_wrapper.py", "/app/packages/compute/borehole-ellipticity/vis_wrapper.py"]
COPY ["packages/compute/borehole-ellipticity/vis", "/app/packages/compute/borehole-ellipticity/vis"]
COPY ["packages/compute/borehole-ellipticity/data", "/app/packages/compute/borehole-ellipticity/data"]
COPY ["packages/compute/stress-inversion/V1.0", "/app/packages/compute/stress-inversion/V1.0"]

# 替代大体积 Noto CJK，使用更轻的文泉驿
RUN apt-get update && apt-get install -y --no-install-recommends fonts-wqy-zenhei && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app/apps/python-service

EXPOSE 8000

CMD ["uvicorn", "python_service.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]


