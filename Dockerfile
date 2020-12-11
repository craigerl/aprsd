FROM ubuntu:20.04 as aprsd


ENV VERSION=1.0.0
ENV APRS_USER=aprs
ENV HOME=/home/aprs
ENV APRSD=http://github.com/craigerl/aprsd.git
ENV APRSD_BRANCH="master"

ENV INSTALL=$HOME/install
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update
RUN apt-get install -y wget gnupg git-core
RUN apt-get install -y apt-utils pkg-config sudo
RUN apt-get install -y python3 python3-pip python3-virtualenv

# Setup Timezone
ENV TZ=US/Eastern
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get install -y tzdata
RUN dpkg-reconfigure --frontend noninteractive tzdata


RUN addgroup --gid 1000 $APRS_USER
RUN useradd -m -u 1000 -g 1000 -p $APRS_USER $APRS_USER

USER $APRS_USER
RUN echo "export PATH=\$PATH:\$HOME/.local/bin" >> $HOME/.bashrc
VOLUME ["/config"]

WORKDIR $HOME
RUN mkdir $INSTALL
# install librtlsdr from source
RUN git clone -b $APRSD_BRANCH $APRSD $INSTALL/aprsd
USER root
RUN cd $INSTALL/aprsd && pip3 install .
RUN aprsd sample-config > /config/aprsd.yml

# override this to run another configuration
ENV CONF default
USER $APRS_USER

ADD build/bin/run.sh $HOME/
ENTRYPOINT ["/home/aprs/run.sh"]
