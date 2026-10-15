FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1
COPY pipeline/ /app/pipeline/
COPY categorise/ /app/categorise/
COPY classification/ /app/classification/
COPY configs/ /app/configs/
COPY requirements.txt /app/requirements.txt
ENTRYPOINT ["python", "-m", "pipeline"]
