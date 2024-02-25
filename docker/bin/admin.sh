#!/usr/bin/env bash
set -x

if [ ! -z "${APRSD_PLUGINS}" ]; then
    OLDIFS=$IFS
    IFS=','
    echo "Installing pypi plugins '$APRSD_PLUGINS'";
    for plugin in ${APRSD_PLUGINS}; do
        IFS=$OLDIFS
        # call your procedure/other scripts here below
        echo "Installing '$plugin'"
        pip3 install --user $plugin
    done
fi
if [ ! -z "${APRSD_EXTENSIONS}" ]; then
    OLDIFS=$IFS
    IFS=','
    echo "Installing APRSD extensions from pypi '$APRSD_EXTENSIONS'";
    for extension in ${APRSD_EXTENSIONS}; do
        IFS=$OLDIFS
        # call your procedure/other scripts here below
        echo "Installing '$extension'"
        pip3 install --user $extension
    done
fi

if [ -z "${LOG_LEVEL}" ] || [[ ! "${LOG_LEVEL}" =~ ^(CRITICAL|ERROR|WARNING|INFO)$ ]]; then
    LOG_LEVEL="DEBUG"
fi

echo "Log level is set to ${LOG_LEVEL}";

# check to see if there is a config file
APRSD_CONFIG="/config/aprsd.conf"
if [ ! -e "$APRSD_CONFIG" ]; then
    echo "'$APRSD_CONFIG' File does not exist. Creating."
    aprsd sample-config > $APRSD_CONFIG
fi

export COLUMNS=200
#exec gunicorn -b :8000 --workers 4 "aprsd.admin_web:create_app(config_file='$APRSD_CONFIG', log_level='$LOG_LEVEL')"
# exec gunicorn -b :8000 --workers 4 "aprsd.wsgi:app"
exec uwsgi --http :8000 --gevent 1000 --http-websockets --master -w aprsd.wsgi --callable app
#exec aprsd listen -c $APRSD_CONFIG --loglevel ${LOG_LEVEL} ${APRSD_LOAD_PLUGINS} ${APRSD_LISTEN_FILTER}
