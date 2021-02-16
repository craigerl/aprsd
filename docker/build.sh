#!/bin/bash

VERSION="1.6.0"

# Use this script to locally build the docker image
docker buildx build --push --platform linux/arm/v7,linux/arm/v6,linux/arm64,linux/amd64 \
    -t hemna6969/aprsd:$VERSION \
    -t hemna6969/aprsd:latest \
    -t 192.168.1.3:5000/hemna6969/aprsd:latest \
    -t 192.168.1.3:5000/hemna6969/aprsd:$VERSION \
    -f Dockerfile .
