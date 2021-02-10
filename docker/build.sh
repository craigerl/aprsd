#!/bin/bash

# Use this script to locally build the docker image
docker build --no-cache -t hemna6969/aprsd:latest -f ./Dockerfile .
