#!/bin/bash

# Hublink Hypervisor Docker Installation Script
# This script installs the Hublink Hypervisor as a Docker container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_PATH="/opt/hublink-hypervisor"
IMAGE_NAME="neurotechhub/hublink-hypervisor:latest"
APP_PORT="8081"

echo -e "${GREEN}Hublink Hypervisor Docker Installation${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running or user is not in docker group${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker and docker-compose are available${NC}"

# Remove existing installation if it exists
if [ -d "$INSTALL_PATH" ]; then
    echo -e "${YELLOW}Removing existing installation...${NC}"
    rm -rf "$INSTALL_PATH"
fi

# Create installation directory
echo -e "${YELLOW}Creating installation directory...${NC}"
mkdir -p "$INSTALL_PATH"
cd "$INSTALL_PATH"

# Download docker-compose file
echo -e "${YELLOW}Downloading docker-compose configuration...${NC}"
curl -sSL https://raw.githubusercontent.com/Neurotech-Hub/Hublink-Hypervisor/main/docker-compose.hypervisor.yml -o docker-compose.hypervisor.yml

# Pull the Docker image
echo -e "${YELLOW}Pulling Hublink Hypervisor Docker image...${NC}"
docker pull "$IMAGE_NAME"

# Start the container
echo -e "${YELLOW}Starting Hublink Hypervisor container...${NC}"
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.hypervisor.yml up -d
else
    docker compose -f docker-compose.hypervisor.yml up -d
fi

# Wait a moment for the container to start
sleep 5

# Check if container is running
if docker ps --format "table {{.Names}}" | grep -q "hublink-hypervisor"; then
    echo -e "${GREEN}✓ Hublink Hypervisor container is running${NC}"
else
    echo -e "${RED}✗ Failed to start Hublink Hypervisor container${NC}"
    echo -e "${YELLOW}Check logs with: docker logs hublink-hypervisor${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Installation completed successfully!${NC}"
echo ""
echo -e "${YELLOW}Container Information:${NC}"
echo -e "  Container Name: hublink-hypervisor"
echo -e "  Web Interface: http://localhost:$APP_PORT"
echo -e "  Image: $IMAGE_NAME"
echo ""
echo -e "${YELLOW}Container Management:${NC}"
echo -e "  Check Status: docker ps | grep hublink-hypervisor"
echo -e "  View Logs: docker logs -f hublink-hypervisor"
echo -e "  Stop Container: docker-compose -f $INSTALL_PATH/docker-compose.hypervisor.yml down"
echo -e "  Start Container: docker-compose -f $INSTALL_PATH/docker-compose.hypervisor.yml up -d"
echo -e "  Restart Container: docker-compose -f $INSTALL_PATH/docker-compose.hypervisor.yml restart"
echo ""
echo -e "${YELLOW}Auto-Updates:${NC}"
echo -e "  The container is configured for automatic updates via Watchtower"
echo -e "  Watchtower will automatically pull and restart the container when updates are available"
echo ""
echo -e "${YELLOW}Manual Updates:${NC}"
echo -e "  Pull Latest Image: docker pull $IMAGE_NAME"
echo -e "  Restart Container: docker-compose -f $INSTALL_PATH/docker-compose.hypervisor.yml up -d" 