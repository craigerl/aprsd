#!/usr/bin/env bash
#
# This is the docker container healthcheck script
# It's assumed to be running in a working aprsd container.
set -x

source /app/.venv/bin/activate

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

uv run aprsd healthcheck --config $APRSD_CONFIG --loglevel ${LOG_LEVEL}
