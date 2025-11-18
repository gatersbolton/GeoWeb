FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/mpl

WORKDIR /app

COPY python_service/requirements.txt /app/
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY python_service /app/python_service

# 拷入科研算法代码与数据，满足 python_service/core/paths.py 的路径解析
RUN mkdir -p "/app/python/Borehole ellipticity" "/app/python/BoreholeEllipStressInv"
COPY ["python/Borehole ellipticity/borehole_ellipticity.py", "/app/python/Borehole ellipticity/borehole_ellipticity.py"]
COPY ["python/Borehole ellipticity/functions.py", "/app/python/Borehole ellipticity/functions.py"]
COPY ["python/Borehole ellipticity/vis_wrapper.py", "/app/python/Borehole ellipticity/vis_wrapper.py"]
COPY ["python/Borehole ellipticity/vis", "/app/python/Borehole ellipticity/vis"]
COPY ["python/Borehole ellipticity/data", "/app/python/Borehole ellipticity/data"]
COPY ["python/BoreholeEllipStressInv/V1.0", "/app/python/BoreholeEllipStressInv/V1.0"]

# 替代大体积 Noto CJK，使用更轻的文泉驿
RUN apt-get update && apt-get install -y --no-install-recommends fonts-wqy-zenhei && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8000

CMD ["uvicorn", "python_service.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]


