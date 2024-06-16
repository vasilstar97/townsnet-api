FROM tiangolo/uvicorn-gunicorn:python3.10

LABEL maintainer="Sebastian Ramirez <tiangolo@gmail.com>"

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY ./app /app

# ARG APP_NAME
# ENV APP_NAME=${APP_NAME}
# ARG APP_VERSION
# ENV APP_VERSION=${APP_VERSION}
