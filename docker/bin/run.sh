#!/usr/bin/env bash
set -x

export PATH=$PATH:$HOME/.local/bin
export VIRTUAL_ENV=$HOME/.venv3
source $VIRTUAL_ENV/bin/activate

if [ ! -z "${APRSD_PLUGINS}" ]; then
    OLDIFS=$IFS
    IFS=','
    echo "Installing pypi plugins '$APRSD_PLUGINS'";
    for plugin in ${APRSD_PLUGINS}; do
        IFS=$OLDIFS
        # call your procedure/other scripts here below
        echo "Installing '$plugin'"
        pip3 install $plugin
    done
fi

# check to see if there is a config file
APRSD_CONFIG="/config/aprsd.yml"
if [ ! -e "$APRSD_CONFIG" ]; then
    echo "'$APRSD_CONFIG' File does not exist. Creating."
    aprsd sample-config > $APRSD_CONFIG
fi
$VIRTUAL_ENV/bin/aprsd server -c $APRSD_CONFIG --loglevel DEBUG
