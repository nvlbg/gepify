FROM python:3-alpine
MAINTAINER Nikolay Lazarov <nikolai.lazarov96@gmail.com>

WORKDIR /app

RUN apk update
RUN apk add ffmpeg

COPY . /app

RUN pip install -r requirements.txt

CMD gunicorn --bind 0.0.0.0:8000 runserver:app
