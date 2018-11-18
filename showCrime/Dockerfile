FROM python:3.6-jessie

WORKDIR /app/showCrime

ENV DJANGO_SETTINGS_MODULE showCrime.settings
ENV MATPLOTLIBRC /app/showCrime
ENV PUBLIC_ROOT /public/showCrime

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    libgdal-dev \
    libpq-dev

COPY Makefile /app/showCrime
COPY requirements.txt /app/showCrime

RUN make requirements

COPY . /app/showCrime

RUN mkdir -p /logs/showCrime

# NOTE: Django won't start without a SECRET_KEY configured.
RUN SECRET_KEY=fake DATABASE_URL="sqlite://:memory:" ENABLE_LOGGING_TO_FILE=false make static

EXPOSE 8000
VOLUME /logs
VOLUME /public
