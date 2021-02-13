FROM alpine:latest as aprsd

# Dockerfile for building a container during aprsd development.
ARG BRANCH

ENV APRS_USER=aprs
ENV HOME=/home/aprs
ENV APRSD=http://github.com/craigerl/aprsd.git
ENV APRSD_BRANCH=${BRANCH:-master}
ENV VIRTUAL_ENV=$HOME/.venv3

ENV INSTALL=$HOME/install
RUN apk add --update git vim wget py3-pip py3-virtualenv bash fortune
RUN apk add --update gcc python3-dev linux-headers musl-dev libffi-dev libc-dev
RUN apk add --update openssl-dev

# Setup Timezone
ENV TZ=US/Eastern
#RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
#RUN apt-get install -y tzdata
#RUN dpkg-reconfigure --frontend noninteractive tzdata

RUN addgroup --gid 1001 $APRS_USER
RUN adduser -h $HOME -D -u 1001 -G $APRS_USER $APRS_USER

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

USER $APRS_USER
RUN pip3 install wheel
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN echo "export PATH=\$PATH:\$HOME/.local/bin" >> $HOME/.bashrc
VOLUME ["/config", "/plugins"]

WORKDIR $HOME
RUN mkdir $INSTALL
RUN git clone -b $APRSD_BRANCH $APRSD $INSTALL/aprsd
RUN    cd $INSTALL/aprsd && pip3 install .
RUN which aprsd
USER root
RUN aprsd sample-config > /config/aprsd.yml
RUN chown -R $APRS_USER:$APRS_USER /config

# override this to run another configuration
ENV CONF default
USER $APRS_USER

ADD bin/run.sh $HOME/
ENTRYPOINT ["/home/aprs/run.sh"]
