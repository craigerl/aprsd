#!/usr/bin/env bash

export PATH=$PATH:$HOME/.local/bin

# check to see if there is a config file
APRSD_CONFIG="/config/aprsd.yml"
if [ ! -e "$APRSD_CONFIG" ]; then
    echo "'$APRSD_CONFIG' File does not exist. Creating."
    aprsd sample-config > $APRSD_CONFIG
fi

aprsd server -c $APRSD_CONFIG
