FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    git \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip setuptools wheel

RUN pip install \
    torch \
    transformers \
    datasets \
    accelerate \
    peft \
    bitsandbytes \
    trl \
    safetensors \
    boto3 \
    s3fs \
    evaluate \
    rouge-score \
    bert-score \
    sentencepiece \
    protobuf

COPY src/ /app/src/

ENV PYTHONPATH=/app

ENTRYPOINT ["python3", "-m", "src.training.train_llama3_qlora_eks"]