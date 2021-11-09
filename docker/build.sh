#!/bin/bash
# Official docker image build script.

# docker buildx create --name multiarch \
# --platform linux/arm/v7,linux/arm/v6,linux/arm64,linux/amd64 \
# --config ./buildkit.toml --use --driver-opt image=moby/buildkit:master


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
TAG="latest"
BRANCH="master"

while getopts “t:dab:” OPTION
do
    case $OPTION in
        t)
           TAG=$OPTARG
           ;;
        b)
           BRANCH=$OPTARG
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

VERSION="2.4.2"

if [ $ALL_PLATFORMS -eq 1 ]
then
    PLATFORMS="linux/arm/v7,linux/arm64,linux/amd64"
    #PLATFORMS="linux/arm/v7,linux/arm/v6,linux/amd64"
else
    PLATFORMS="linux/amd64"
fi

echo "Build with tag=${TAG} BRANCH=${BRANCH} dev?=${DEV} platforms?=${PLATFORMS}"


echo "Destroying old multiarch build container"
docker buildx rm multiarch
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
echo "Creating new buildx container"
docker buildx create --name multiarch --driver docker-container --use --platform linux/arm/v7,linux/arm/v6,linux/arm64,linux/amd64 --config ./buildkit.toml --use --driver-opt image=moby/buildkit:master
docker buildx inspect --bootstrap

if [ $DEV -eq 1 ]
then
    echo "Build -DEV- with tag=${TAG} BRANCH=${BRANCH} platforms?=${PLATFORMS}"
    # Use this script to locally build the docker image
    docker buildx build --push --platform $PLATFORMS \
        -t harbor.hemna.com/hemna6969/aprsd:$TAG \
        -f Dockerfile-dev --build-arg branch=$BRANCH --no-cache .
else
    # Use this script to locally build the docker image
    echo "Build with tag=${TAG} BRANCH=${BRANCH} platforms?=${PLATFORMS}"
    docker buildx build --push --platform $PLATFORMS \
        --allow security.insecure \
        -t hemna6969/aprsd:$VERSION \
        -t hemna6969/aprsd:$TAG \
        -t harbor.hemna.com/hemna6969/aprsd:$TAG \
        -t harbor.hemna.com/hemna6969/aprsd:$VERSION \
        -f Dockerfile .
fi
