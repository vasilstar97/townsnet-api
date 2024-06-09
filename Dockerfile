FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

ENV GIT_SSL_NO_VERIFY=1
ENV PORT=5000

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./app /app/app
EXPOSE $PORT

ARG APP_NAME
ENV APP_NAME=${APP_NAME}
ARG APP_VERSION
ENV APP_VERSION=${APP_VERSION}
