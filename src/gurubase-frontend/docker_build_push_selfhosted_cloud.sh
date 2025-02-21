#!/bin/bash
# Uses https://build.docker.com/
# ./docker_buildcloud_onprem.sh x.y.z

# Get version as argument and default to latest
VERSION=${1:-latest-selfhosted}
PLATFORM=${2:-linux/amd64,linux/arm64}
# DOCKER_IMAGE_TAG=ddosify/kubernetesguru_frontend:$VERSION
DOCKER_IMAGE_TAG=ddosify/gurubase-frontend:$VERSION
DOCKERFILE=Dockerfile.selfhosted

echo "Building $DOCKER_IMAGE_TAG"

# Clean build cache before new build
docker buildx prune -f

docker buildx create --driver cloud ddosify/builder

# docker buildx build --push --platform=$PLATFORM --builder=cloud-ddosify-builder --tag=$DOCKER_IMAGE_TAG --tag=$DOCKER_IMAGE_TAG2 -f $DOCKERFILE .

docker buildx build --push --platform=$PLATFORM --builder=cloud-ddosify-builder --tag=$DOCKER_IMAGE_TAG -f $DOCKERFILE .
