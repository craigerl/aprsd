FROM python:3-bullseye as aprsd

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

RUN apt update
RUN apt install -y git build-essential
RUN apt install -y libffi-dev python3-dev libssl-dev
#RUN apt-get install -y apt-utils
#RUN apt-get install -y pkg-config
#RUN apt upgrade -y
#RUN apk add --update git wget bash
#RUN apk add --update gcc linux-headers musl-dev libffi-dev libc-dev
#RUN apk add --update openssl-dev
#RUN add cmd:pip3 lsb-release

RUN addgroup --gid $GID $APRS_USER
RUN useradd -m -u $UID -g $APRS_USER $APRS_USER

# Install aprsd
RUN /usr/local/bin/pip3 install aprsd==2.3.1

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
