FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y build-essential ffmpeg libfftw3-dev libyaml-dev git && \
    pip install --upgrade pip

COPY requirements.txt .

RUN pip install -r requirements.txt

WORKDIR /workspace
