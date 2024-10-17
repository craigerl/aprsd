FROM python:3.11-slim AS build

ARG VERSION=3.4.0
# pass this in as 'dev' if you want to install from github repo vs pypi
ARG INSTALL_TYPE=pypi

ARG BRANCH=master
ARG BUILDX_QEMU_ENV

ENV APRSD_BRANCH=${BRANCH:-master}
ENV TZ=${TZ:-US/Eastern}
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV APRSD_PIP_VERSION=${VERSION}
ENV PATH="${PATH}:/app/.local/bin"

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
    && usermod -aG sudo appuser \
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
FROM build AS install
WORKDIR /app

RUN pip3 install -U pip
RUN mkdir /config
RUN chown -R appuser:appgroup /app
RUN chown -R appuser:appgroup /config
USER appuser
RUN if [ "$INSTALL_TYPE" = "pypi" ]; then \
       pip3 install aprsd==$APRSD_PIP_VERSION; \
    elif [ "$INSTALL_TYPE" = "github" ]; then \
       git clone -b $APRSD_BRANCH https://github.com/craigerl/aprsd; \
       cd /app/aprsd && pip install .; \
       ls -al /app/.local/lib/python3.11/site-packages/aprsd*; \
    fi
RUN pip install gevent uwsgi
RUN echo "PATH=\$PATH:/usr/games:/app/.local/bin" >> /app/.bashrc
RUN which aprsd
RUN aprsd sample-config > /config/aprsd.conf
RUN aprsd --version

ADD bin/setup.sh /app
ADD bin/admin.sh /app


FROM install AS final
# For the web admin interface
EXPOSE 8001

VOLUME ["/config"]
ENTRYPOINT ["/app/setup.sh"]
CMD ["server"]

# Set the user to run the application
USER appuser

HEALTHCHECK --interval=1m --timeout=12s --start-period=30s \
    CMD aprsd healthcheck --config /config/aprsd.conf --loglevel DEBUG
