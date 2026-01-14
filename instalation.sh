#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== OccultaShield Setup & Initialization ===${NC}"

# --- System Update ---
echo -e "${BLUE}[1/9] System Update & Upgrade...${NC}"
echo "Running sudo apt update && sudo apt upgrade -y..."
sudo apt update && sudo apt upgrade -y

# --- Git Configuration ---
echo -e "${BLUE}[2/9] Configuring Git...${NC}"
git config --global user.email "gabijuan872@gmail.com"
git config --global user.name "Gabriel Juan"
echo -e "${GREEN}Git identity configured.${NC}"

# --- Bun Setup ---
echo -e "${BLUE}[3/9] Setting up Bun...${NC}"
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
echo -e "${BLUE}[4/9] Setting up Node.js & Angular CLI...${NC}"
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
echo -e "${BLUE}[5/9] Checking Other Dependencies...${NC}"

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
echo -e "${BLUE}[6/9] Setting up Environment Variables...${NC}"

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
echo -e "${BLUE}[7/9] Installing Dependencies (Front/Back)...${NC}"

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
echo -e "${BLUE}[8/9] Infrastructure Setup...${NC}"

read -p "Do you want to start Docker services (databases)? [y/N]: " start_docker
if [[ "$start_docker" =~ ^[Yy]$ ]]; then
    echo "Starting Docker Services..."
    cd docker || exit
    docker compose up -d
    cd ..
    echo -e "${GREEN}Docker services started.${NC}"

    # Wait for Neo4j to be ready
    echo "Waiting for Neo4j to be ready (10 seconds)..."
    sleep 10
else
    echo -e "${BLUE}Skipping Docker services startup.${NC}"
fi


# --- GDPR Knowledge Graph Ingestion ---
echo -e "${BLUE}[9/9] GDPR Knowledge Graph Setup...${NC}"

# Check if Neo4j is running
if nc -z localhost 7687 2>/dev/null; then
    echo -e "${GREEN}Neo4j detected on port 7687${NC}"

    read -p "Do you want to ingest GDPR data into Neo4j? [Y/n]: " ingest_gdpr
    if [[ ! "$ingest_gdpr" =~ ^[Nn]$ ]]; then
        echo "Running GDPR Knowledge Graph Ingestion..."
        cd backend/app || exit

        # Check if .kaggle/kaggle.json exists and set environment
        if [ -f ".kaggle/kaggle.json" ]; then
            echo "✅ Kaggle credentials found"
            KAGGLE_CONFIG_DIR="$(pwd)/.kaggle" uv run python scripts/gdpr_ingestion/enhanced_ingest_gdpr.py
        else
            echo "⚠️  Kaggle credentials not found (optional)"
            uv run python scripts/gdpr_ingestion/enhanced_ingest_gdpr.py
        fi

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ GDPR Knowledge Graph ingestion completed!${NC}"
        else
            echo -e "${RED}❌ GDPR ingestion failed. Check logs above.${NC}"
        fi
        cd ../..
    else
        echo -e "${BLUE}Skipping GDPR ingestion.${NC}"
    fi
else
    echo -e "${RED}⚠️  Neo4j not detected on port 7687${NC}"
    echo "GDPR Knowledge Graph requires Neo4j. You can:"
    echo "  1. Start Neo4j manually"
    echo "  2. Run setup_gdpr.sh later: cd backend/app && ./setup_gdpr.sh"
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
