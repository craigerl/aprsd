FROM python:3.11-slim as build

ARG VERSION=3.1.0
ENV TZ=${TZ:-US/Eastern}
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV APRSD_PIP_VERSION=${VERSION}

ENV PIP_DEFAULT_TIMEOUT=100 \
    # Allow statements and log messages to immediately appear
    PYTHONUNBUFFERED=1 \
    # disable a pip version check to reduce run-time & log-spam
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # cache is useless in docker image, so disable to reduce image size
    PIP_NO_CACHE_DIR=1


RUN set -ex \
    # Create a non-root user
    && addgroup --system --gid 1001 appgroup \
    && useradd --uid 1001 --gid 1001 -s /usr/bin/bash -m -d /app appuser \
    # Upgrade the package index and install security upgrades
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y git build-essential curl libffi-dev \
    python3-dev libssl-dev libxml2-dev libxslt-dev telnet sudo fortune \
    # Install dependencies
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean -y


### Final stage
FROM build as final
WORKDIR /app

RUN pip3 install aprsd==$APRSD_PIP_VERSION
RUN pip install gevent uwsgi
RUN which aprsd
RUN mkdir /config
RUN chown -R appuser:appgroup /app
RUN chown -R appuser:appgroup /config
USER appuser
RUN echo "PATH=\$PATH:/usr/games" >> /app/.bashrc
RUN which aprsd
RUN aprsd sample-config > /config/aprsd.conf

ADD bin/run.sh /app
ADD bin/listen.sh /app
ADD bin/admin.sh /app

# For the web admin interface
EXPOSE 8001

ENTRYPOINT ["/app/run.sh"]
VOLUME ["/config"]

# Set the user to run the application
USER appuser

HEALTHCHECK --interval=1m --timeout=12s --start-period=30s \
    CMD aprsd healthcheck --config /config/aprsd.conf --loglevel DEBUG
