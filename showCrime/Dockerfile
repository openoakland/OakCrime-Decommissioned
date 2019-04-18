FROM python:3.6-stretch

WORKDIR /app/showCrime

ENV DJANGO_SETTINGS_MODULE showCrime.settings
ENV MATPLOTLIBRC /app/showCrime
ENV PUBLIC_ROOT /public
ENV LOG_FILE_PATH /logs
ENV ENABLE_LOGGING_TO_FILE true

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
        build-essential \
        gettext \
        libffi-dev \
        libgdal-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/showCrime

RUN make requirements

RUN mkdir -p /logs \
    && touch /logs/app.log \
    && touch /logs/gunicorn.log

VOLUME /public/media

EXPOSE 8000

ENTRYPOINT ["/app/showCrime/docker-entrypoint.sh"]
