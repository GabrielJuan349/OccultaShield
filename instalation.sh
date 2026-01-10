#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== OccultaShield Setup & Initialization ===${NC}"

# --- System Update ---
echo -e "${BLUE}[1/8] System Update & Upgrade...${NC}"
echo "Running sudo apt update && sudo apt upgrade -y..."
sudo apt update && sudo apt upgrade -y

# --- Git Configuration ---
echo -e "${BLUE}[2/8] Configuring Git...${NC}"
git config --global user.email "gabijuan872@gmail.com"
git config --global user.name "Gabriel Juan"
echo -e "${GREEN}Git identity configured.${NC}"

# --- Bun Setup ---
echo -e "${BLUE}[3/8] Setting up Bun...${NC}"
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

if ! command -v bun &> /dev/null; then
    echo "Installing Bun..."
    curl -fsSL https://bun.sh/install | bash
    # Refresh path for current session
    export BUN_INSTALL="$HOME/.bun"
    export PATH="$BUN_INSTALL/bin:$PATH"
fi
echo -e "${GREEN}Bun version: $(bun -v)${NC}"

# --- Node & Angular CLI (via Bun) ---
echo -e "${BLUE}[4/8] Setting up Node.js & Angular CLI...${NC}"
export NVM_DIR="$HOME/.nvm"

# Install NVM if not exists (Node is still needed for Angular runtime)
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    echo "Installing NVM..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi

# Load NVM
echo "Loading NVM..."
\. "$NVM_DIR/nvm.sh"

# Install Node LTS
echo "Installing Node LTS (Compatible with latest Angular)..."
nvm install --lts
nvm use --lts
echo -e "${GREEN}Node version: $(node -v)${NC}"

# Install Angular CLI Global using BUN
echo "Installing @angular/cli@latest globally using Bun..."
bun add -g @angular/cli


# --- Check Other Dependencies ---
echo -e "${BLUE}[5/8] Checking Other Dependencies...${NC}"

check_command() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        echo -e "${RED}$cmd not found. Attempting installation...${NC}"
        case $cmd in
            uv)
                echo "Installing uv..."
                if command -v pip &> /dev/null; then
                    pip install uv
                elif command -v pip3 &> /dev/null; then
                    pip3 install uv
                else
                    echo "pip not found. Installing python3-pip..."
                    sudo apt install -y python3-pip
                    pip3 install uv
                fi
                # Add local bin to PATH just in case
                export PATH="$HOME/.local/bin:$PATH"
                ;;
            docker)
                echo "Installing Docker..."
                sudo apt install -y docker.io docker-compose-plugin
                # Enable and start docker service
                sudo systemctl enable --now docker
                # Add current user to docker group (requires logout/login usually, but we try)
                sudo usermod -aG docker $USER
                echo "Docker installed. You may need to restart your session to run docker without sudo."
                ;;
            *)
                echo -e "${RED}No installer defined for $cmd. Please install manually.${NC}"
                exit 1
                ;;
        esac

        # Verify installation
        if ! command -v "$cmd" &> /dev/null; then
             # Check if it was uv and update path one more time or warn
             if [ "$cmd" == "uv" ]; then
                 export PATH="$HOME/.local/bin:$PATH"
             fi
        fi

        if ! command -v "$cmd" &> /dev/null; then
             echo -e "${RED}Failed to install $cmd.${NC}"
             exit 1
        fi
        echo -e "${GREEN}$cmd installed successfully.${NC}"
    fi
}

# Bun already checked/installed
check_command uv
check_command docker

echo -e "${GREEN}All dependencies found.${NC}"
# --- Environment Setup ---
echo -e "${BLUE}[6/8] Setting up Environment Variables...${NC}"

# Backend
if [ ! -f "backend/app/.env" ]; then
    if [ -f "backend/app/.env.example" ]; then
        echo "Creating backend/app/.env from backend/app/.env.example"
        cp backend/app/.env.example backend/app/.env
    else
        echo -e "${RED}Warning: backend/app/.env.example not found.${NC}"
    fi
else
    echo "backend/app/.env exists."
fi

# Frontend
if [ ! -f "frontend/.env" ]; then
    if [ -f "frontend/.env.example" ]; then
        echo "Creating frontend/.env from frontend/.env.example"
        cp frontend/.env.example frontend/.env
    else
        echo -e "${RED}Warning: frontend/.env.example not found.${NC}"
    fi
else
    echo "frontend/.env exists."
fi

# Docker
if [ ! -f "docker/.env" ]; then
    if [ -f "docker/.env.example" ]; then
        echo "Creating docker/.env from docker/.env.example"
        cp docker/.env.example docker/.env
    else
        echo -e "${RED}Warning: docker/.env.example not found.${NC}"
    fi
else
    echo "docker/.env exists."
fi


# --- Installation ---
echo -e "${BLUE}[7/8] Installing Dependencies (Front/Back)...${NC}"

# Backend
echo "Installing Backend dependencies (uv)..."
cd backend/app || exit
uv sync
uv add kornia pandas
cd ../..

# Frontend
echo "Installing Frontend dependencies (bun)..."
cd frontend || exit
bun install
cd ..


# --- Infrastructure ---
echo -e "${BLUE}[8/8] Infrastructure Setup...${NC}"

read -p "Do you want to start Docker services (databases)? [y/N]: " start_docker
if [[ "$start_docker" =~ ^[Yy]$ ]]; then
    echo "Starting Docker Services..."
    cd docker || exit
    docker compose up -d
    cd ..
    echo -e "${GREEN}Docker services started.${NC}"
else
    echo -e "${BLUE}Skipping Docker services startup.${NC}"
fi


# --- Execution Menu ---
echo -e "${BLUE}=== Execution Mode ===${NC}"
echo "What do you want to start?"
echo "1) Frontend + Backend"
echo "2) Frontend Only"
echo "3) Backend Only"
echo "4) Exit (Installation Complete)"
read -p "Select option [1-4]: " option

cleanup() {
    echo -e "\n${BLUE}Stopping services...${NC}"
    [ -n "$PID_BACKEND" ] && kill "$PID_BACKEND" 2>/dev/null
    [ -n "$PID_FRONTEND" ] && kill "$PID_FRONTEND" 2>/dev/null
    echo -e "${GREEN}Services stopped.${NC}"
}
trap cleanup EXIT INT TERM

start_backend() {
    echo "Starting Backend (uv run main.py)..."
    cd backend/app || exit
    # Ensure uvicorn runs on proper host/port logic or relies on .env
    uv run main.py &
    PID_BACKEND=$!
    cd ../..
}

start_frontend() {
    echo "Starting Frontend (bun run dev)..."
    cd frontend || exit
    bun run dev &
    PID_FRONTEND=$!
    cd ..
}

case $option in
    1)
        start_backend
        start_frontend
        wait $PID_BACKEND $PID_FRONTEND
        ;;
    2)
        start_frontend
        wait $PID_FRONTEND
        ;;
    3)
        start_backend
        wait $PID_BACKEND
        ;;
    4)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid option."
        exit 1
        ;;
esac
