FROM alpine:latest as aprsd

ENV VERSION=1.0.0
ENV APRS_USER=aprs
ENV HOME=/home/aprs
ENV VIRTUAL_ENV=$HOME/.venv3

ENV INSTALL=$HOME/install
RUN apk add --update git wget py3-pip py3-virtualenv bash

# Setup Timezone
ENV TZ=US/Eastern
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get install -y tzdata
RUN dpkg-reconfigure --frontend noninteractive tzdata


RUN addgroup --gid 1000 $APRS_USER
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
RUN pip install aprsd
USER root
RUN aprsd sample-config > /config/aprsd.yml
RUN chown -R $APRS_USER:$APRS_USER /config

# override this to run another configuration
ENV CONF default
USER $APRS_USER

ADD build/bin/run.sh $HOME/
ENTRYPOINT ["/home/aprs/run.sh"]
