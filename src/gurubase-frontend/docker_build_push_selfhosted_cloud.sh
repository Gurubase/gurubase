#!/bin/bash
# Uses https://build.docker.com/
# bash docker_build_push_selfhosted_cloud.sh -v latest-selfhosted -p linux/amd64,linux/arm64 -r ddosify/gurubase-frontend -d Dockerfile.selfhosted

# Parse command line arguments
while getopts "v:p:r:d:" opt; do
  case $opt in
    v) VERSION="$OPTARG" ;;
    p) PLATFORM="$OPTARG" ;;
    r) REPOSITORY="$OPTARG" ;;
    d) DOCKERFILE="$OPTARG" ;;
    \?) echo "Invalid option -$OPTARG" >&2; exit 1 ;;
  esac
done

# Set default values if not provided
VERSION=${VERSION:-latest-selfhosted}
PLATFORM=${PLATFORM:-linux/amd64,linux/arm64}
REPOSITORY=${REPOSITORY:-ddosify/gurubase-frontend}
DOCKERFILE=${DOCKERFILE:-Dockerfile.selfhosted}

echo "Do you confirm the following parameters?"
echo "Version: $VERSION"
echo "Platform: $PLATFORM"
echo "Repository: $REPOSITORY"
echo "Dockerfile: $DOCKERFILE"

read -p "Press Enter to continue"

DOCKER_IMAGE_TAG=$REPOSITORY:$VERSION

echo "Building $DOCKER_IMAGE_TAG"

# Clean build cache before new build
docker buildx prune -f

docker buildx create --driver cloud ddosify/builder

# docker buildx build --push --platform=$PLATFORM --builder=cloud-ddosify-builder --tag=$DOCKER_IMAGE_TAG --tag=$DOCKER_IMAGE_TAG2 -f $DOCKERFILE .

docker buildx build --push --platform=$PLATFORM --builder=cloud-ddosify-builder --tag=$DOCKER_IMAGE_TAG -f $DOCKERFILE .
