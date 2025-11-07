#!/bin/bash
# Build script for training Docker images
# Usage: ./build.sh [base|ultralytics|timm|all] [--push] [--tag VERSION]

set -e

# Configuration
REGISTRY="${DOCKER_REGISTRY:-ghcr.io/myorg}"
VERSION="${1:-v1.0}"
PUSH=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH=true
            shift
            ;;
        --tag)
            VERSION="$2"
            shift 2
            ;;
        base|ultralytics|timm|all)
            TARGET="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./build.sh [base|ultralytics|timm|all] [--push] [--tag VERSION]"
            exit 1
            ;;
    esac
done

# Default to all if no target specified
TARGET="${TARGET:-all}"

echo "=========================================="
echo "Building Training Docker Images"
echo "=========================================="
echo "Registry: $REGISTRY"
echo "Version: $VERSION"
echo "Target: $TARGET"
echo "Push: $PUSH"
echo "=========================================="

# Function to build image
build_image() {
    local name=$1
    local dockerfile=$2
    local image_name="${REGISTRY}/trainer-${name}:${VERSION}"
    local latest_name="${REGISTRY}/trainer-${name}:latest"

    echo ""
    echo "Building $name..."
    echo "Image: $image_name"

    # Build from project root (to access mvp/training/ directory)
    cd "$(dirname "$0")/../../.."

    docker build \
        -f "mvp/training/docker/${dockerfile}" \
        -t "$image_name" \
        -t "$latest_name" \
        .

    if [ $? -eq 0 ]; then
        echo "✓ Successfully built $image_name"
    else
        echo "✗ Failed to build $name"
        exit 1
    fi

    # Push if requested
    if [ "$PUSH" = true ]; then
        echo "Pushing $image_name..."
        docker push "$image_name"
        docker push "$latest_name"
        echo "✓ Pushed $image_name"
    fi
}

# Build base image
if [ "$TARGET" = "base" ] || [ "$TARGET" = "all" ]; then
    build_image "base" "Dockerfile.base"
fi

# Build ultralytics image (depends on base)
if [ "$TARGET" = "ultralytics" ] || [ "$TARGET" = "all" ]; then
    build_image "ultralytics" "Dockerfile.ultralytics"
fi

# Build timm image (depends on base)
if [ "$TARGET" = "timm" ] || [ "$TARGET" = "all" ]; then
    build_image "timm" "Dockerfile.timm"
fi

echo ""
echo "=========================================="
echo "Build Complete!"
echo "=========================================="
echo ""
echo "Built images:"
docker images | grep "trainer-" | head -10

echo ""
echo "To test an image locally:"
echo "  docker run --rm ${REGISTRY}/trainer-ultralytics:${VERSION} --help"
echo ""
echo "To load into Kind cluster:"
echo "  kind load docker-image ${REGISTRY}/trainer-ultralytics:${VERSION}"
echo ""
