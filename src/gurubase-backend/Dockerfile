FROM python:3.11.8-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

COPY ./requirements.txt .
RUN apt update -y && apt install -y gcc libcairo2 libcairo2-dev git && rm -rf /var/lib/apt/lists/*
RUN pip --no-cache-dir install -r requirements.txt

WORKDIR /workspace

COPY . /workspace

CMD ["/workspace/entrypoint.sh"]
