FROM python:3.6-jessie

WORKDIR /app/showCrime

ENV DJANGO_SETTINGS_MODULE showCrime.settings
ENV MATPLOTLIBRC /app/showCrime
ENV PUBLIC_ROOT /public/showCrime

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        build-essential \
        gettext \
        libffi-dev \
        libgdal-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY Makefile /app/showCrime
COPY requirements.txt /app/showCrime
COPY requirements.dev.txt /app/showCrime
COPY conf/wait-for-it.sh /app/showCrime

RUN make requirements

COPY showCrime /app/showCrime

RUN mkdir -p /logs \
    && touch /logs/app.log \
    && touch /logs/gunicorn.log

ENV PUBLIC_ROOT /public
ENV LOG_FILE_PATH /logs
ENV ENABLE_LOGGING_TO_FILE true

VOLUME /public/media

EXPOSE 8000

ENTRYPOINT ["/app/showCrime/docker-entrypoint.sh"]
