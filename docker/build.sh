#!/bin/bash
# Official docker image build script.


usage() {
cat << EOF
usage: $0 options

OPTIONS:
   -t      The tag/version (${TAG}) (default = master)
   -d      Use Dockerfile-dev for a git clone build
EOF
}


ALL_PLATFORMS=0
DEV=0
TAG="master"

while getopts “t:da” OPTION
do
    case $OPTION in
        t)
           TAG=$OPTARG
           ;;
        a)
           ALL_PLATFORMS=1
           ;;
        d)
           DEV=1
           ;;
        ?)
           usage
           exit
           ;;
    esac
done

VERSION="2.2.1"

if [ $ALL_PLATFORMS -eq 1 ]
then
    PLATFORMS="linux/arm/v7,linux/arm/v6,linux/arm64,linux/amd64"
else
    PLATFORMS="linux/amd64"
fi

if [ $DEV -eq 1 ]
then
    # Use this script to locally build the docker image
    docker buildx build --push --platform $PLATFORMS \
        -t harbor.hemna.com/hemna6969/aprsd:$TAG \
        -f Dockerfile-dev --no-cache .
else
    # Use this script to locally build the docker image
    docker buildx build --push --platform $PLATFORMS \
        -t hemna6969/aprsd:$VERSION \
        -t hemna6969/aprsd:latest \
        -t harbor.hemna.com/hemna6969/aprsd:latest \
        -t harbor.hemna.com/hemna6969/aprsd:$VERSION \
        -f Dockerfile .


fi
