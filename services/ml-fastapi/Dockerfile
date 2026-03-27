FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Python 3.10 is required here because the pinned MiDaS/timm path used by the
# depth loader does not import cleanly on Python 3.12 in Docker.
# Cache the official MiDaS repository code used by the local depth model loader.
RUN python -c "import torch; torch.hub.load('isl-org/MiDaS', 'DPT_SwinV2_T_256', pretrained=False, trust_repo=True)"

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
