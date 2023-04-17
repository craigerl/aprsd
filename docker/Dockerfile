#FROM python:3-bullseye as aprsd
FROM ubuntu:22.04 as aprsd

# Dockerfile for building a container during aprsd development.

ARG UID
ARG GID
ARG TZ
ARG VERSION=3.0.0
ARG BUILDX_QEMU_ENV
ENV APRS_USER=aprs
ENV HOME=/home/aprs
ENV TZ=${TZ:-US/Eastern}
ENV UID=${UID:-1000}
ENV GID=${GID:-1000}
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV APRSD_PIP_VERSION=${VERSION}


ENV DEBIAN_FRONTEND=noninteractive
RUN apt update
RUN apt install -y git build-essential
RUN apt install -y libffi-dev python3-dev libssl-dev libxml2-dev libxslt-dev
RUN apt install -y python3 python3-pip python3-dev python3-lxml

RUN pip3 install -U pip

RUN addgroup --gid $GID $APRS_USER
RUN useradd -m -u $UID -g $APRS_USER $APRS_USER

# Handle an extremely specific issue when building the cryptography package for
# 32-bit architectures within QEMU running on a 64-bit host (issue #30).
RUN if [ "${BUILDX_QEMU_ENV}" = "true" -a "$(getconf LONG_BIT)" = "32" ]; then \
        pip3 install -U cryptography==3.3.2; \
    else \
        pip3 install cryptography ;\
    fi

# Ensure /config is there with a default config file
USER root
# Install aprsd
RUN pip3 install aprsd==$APRSD_PIP_VERSION
RUN mkdir -p /config
RUN aprsd sample-config > /config/aprsd.conf
RUN chown -R $APRS_USER:$APRS_USER /config
RUN chown -R $APRS_USER:$APRS_USER $HOME

# override this to run another configuration
ENV CONF default
VOLUME ["/config", "/plugins"]

USER $APRS_USER
ADD bin/run.sh /usr/local/bin
ADD bin/listen.sh /usr/local/bin
ENTRYPOINT ["/usr/local/bin/run.sh"]

HEALTHCHECK --interval=5m --timeout=12s --start-period=30s \
    CMD aprsd healthcheck --config /config/aprsd.conf
