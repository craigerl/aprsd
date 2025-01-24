#!/usr/bin/env bash
set -x

source /app/.venv/bin/activate

# The default command
# Override the command in docker-compose.yml to change
# what command you want to run in the container
COMMAND="server"

if [ ! -z "${@+x}" ]; then
  COMMAND=$@
fi

if [ ! -z "${APRSD_PLUGINS}" ]; then
    OLDIFS=$IFS
    IFS=','
    echo "Installing pypi plugins '$APRSD_PLUGINS'";
    for plugin in ${APRSD_PLUGINS}; do
        IFS=$OLDIFS
        # call your procedure/other scripts here below
        echo "Installing '$plugin'"
        uv pip install $plugin
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
        uv pip install $extension
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

aprsd ${COMMAND} --config ${APRSD_CONFIG} --loglevel ${LOG_LEVEL}
