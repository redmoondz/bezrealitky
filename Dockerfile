FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY src ./src
COPY config ./config

RUN mkdir -p /app/output

ENTRYPOINT ["python3", "-m", "src.cli"]
CMD ["--help"]
