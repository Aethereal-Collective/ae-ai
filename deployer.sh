IMAGE_NAME="ae-ai"
HOST_PORT=5003
CONTAINER_PORT=5003
PROJECT_DIR="$(pwd)"

if ! command -v docker &> /dev/null
then
    echo "Docker Not Found"
    exit 1
fi

echo "Building Docker image..."
docker build -t "$IMAGE_NAME" "$PROJECT_DIR"

echo "Stopping and removing running container..."
docker ps -q --filter "ancestor=$IMAGE_NAME" | xargs -r docker stop | xargs -r docker rm

echo "Running Docker container..."
docker run -d -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE_NAME"

echo "Deployment complete"
