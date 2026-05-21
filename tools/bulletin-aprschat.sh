#!/bin/bash
# Send APRS bulletins announcing APRS Chat on Google Play

set -e

source ~/devel/mine/hamradio/aprsd/.venv/bin/activate

export APRS_LOGIN=WB4BOR
export APRS_PASSWORD=24496

aprsd send-message -n BLN0 "APRS Chat now on Google Play Store!"
sleep 2
aprsd send-message -n BLN1 "Install: https://tinyurl.com/APRSChat"
sleep 2
aprsd send-message -n BLN2 "Android app for APRS chat and messaging"
sleep 2
aprsd send-message -n BLN3 "Search Google Play for APRS Chat"
sleep 2
