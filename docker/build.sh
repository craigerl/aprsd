#!/bin/bash
# Official docker image build script.

# docker buildx create --name multiarch \
# --platform linux/arm/v7,linux/arm/v6,linux/arm64,linux/amd64 \
# --config ./buildkit.toml --use --driver-opt image=moby/buildkit:master


usage() {
cat << EOF
usage: $0 options

OPTIONS:
   -h      Show help
   -t      The tag/version (${TAG}) (default = master)
   -d      Use Dockerfile-dev for a git clone build
   -b      Branch to use (default = master)
   -r      Destroy and rebuild the buildx environment
   -v      aprsd version to build
EOF
}


ALL_PLATFORMS=0
DEV=0
REBUILD_BUILDX=0
TAG="latest"
BRANCH=${BRANCH:-master}
VERSION="3.0.0"

while getopts “hdart:b:v:” OPTION
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
        r)
           REBUILD_BUILDX=1
           ;;
        d)
           DEV=1
           ;;
        v)
           VERSION=$OPTARG
           ;;
        h)
           usage
           exit 0
           ;;
        ?)
           usage
           exit -1
           ;;
    esac
done


if [ $ALL_PLATFORMS -eq 1 ]
then
    PLATFORMS="linux/arm64,linux/amd64"
    #PLATFORMS="linux/arm/v7,linux/arm/v6,linux/amd64"
    #PLATFORMS="linux/arm64"
else
    PLATFORMS="linux/amd64"
fi



if [ $REBUILD_BUILDX -eq 1 ]
then
    echo "Destroying old multiarch build container"
    docker buildx rm multiarch
    docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
    echo "Creating new buildx container"
    docker buildx create --name multiarch --driver docker-container --use \
        --config ./buildkit.toml --use \
        --driver-opt image=moby/buildkit:master
    docker buildx inspect --bootstrap
fi

if [ $DEV -eq 1 ]
then
    echo "Build -DEV- with tag=${TAG} BRANCH=${BRANCH} platforms?=${PLATFORMS}"
    # Use this script to locally build the docker image
    docker buildx build --push --platform $PLATFORMS \
        -t hemna6969/aprsd:$TAG \
        -f Dockerfile-dev --build-arg branch=$BRANCH \
        --build-arg BUILDX_QEMU_ENV=true \
        --no-cache .
else
    # Use this script to locally build the docker image
    echo "Build with tag=${TAG} BRANCH=${BRANCH} dev?=${DEV} platforms?=${PLATFORMS} VERSION=${VERSION}"
    docker buildx build --push --platform $PLATFORMS \
        --build-arg VERSION=$VERSION \
        --build-arg BUILDX_QEMU_ENV=true \
        -t hemna6969/aprsd:$VERSION \
        -t hemna6969/aprsd:$TAG \
        -t hemna6969/aprsd:latest \
        -f Dockerfile .
fi
