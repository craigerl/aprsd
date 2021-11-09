#FROM python:3-bullseye as aprsd
FROM ubuntu:focal as aprsd

# Dockerfile for building a container during aprsd development.

ARG UID
ARG GID
ARG TZ
ENV APRS_USER=aprs
ENV HOME=/home/aprs
ENV TZ=${TZ:-US/Eastern}
ENV UID=${UID:-1000}
ENV GID=${GID:-1000}
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ENV DEBIAN_FRONTEND=noninteractive
RUN apt update
RUN apt install -y git build-essential
RUN apt install -y libffi-dev python3-dev libssl-dev libxml2-dev libxslt-dev
RUN apt install -y python3 python3-pip python3-dev python3-lxml

RUN addgroup --gid $GID $APRS_USER
RUN useradd -m -u $UID -g $APRS_USER $APRS_USER

# Install aprsd
RUN pip install aprsd

# Ensure /config is there with a default config file
USER root
RUN mkdir -p /config
RUN aprsd sample-config > /config/aprsd.yml
RUN chown -R $APRS_USER:$APRS_USER /config

# override this to run another configuration
ENV CONF default
VOLUME ["/config", "/plugins"]

USER $APRS_USER
ADD bin/run.sh /usr/local/bin
ENTRYPOINT ["/usr/local/bin/run.sh"]

HEALTHCHECK --interval=5m --timeout=12s --start-period=30s \
    CMD aprsd healthcheck --config /config/aprsd.yml --url http://localhost:8001/stats
