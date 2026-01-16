#!/bin/bash

# =============================================================================
# OccultaShield Installation Script
# =============================================================================
# This script sets up the complete development environment including:
# - System dependencies (ffmpeg, docker)
# - Runtime environments (Bun, Node.js, uv)
# - Interactive .env configuration with shared variable sync
# - Docker services (Neo4j, SurrealDB)
# - Optional: Hugging Face login for Gemma LLM
# - Optional: GDPR Knowledge Graph ingestion
# =============================================================================

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           OccultaShield Setup & Initialization                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# STEP 1: System Update
# =============================================================================
echo -e "${BLUE}[1/10] System Update & Upgrade...${NC}"
echo "Running sudo apt update && sudo apt upgrade -y..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y ffmpeg netcat-openbsd openssl

# =============================================================================
# STEP 2: Git Configuration
# =============================================================================
echo -e "${BLUE}[2/10] Configuring Git...${NC}"
git config --global user.email "gabijuan872@gmail.com"
git config --global user.name "Gabriel Juan"
echo -e "${GREEN}✓ Git identity configured.${NC}"

# =============================================================================
# STEP 3: Bun Setup
# =============================================================================
echo -e "${BLUE}[3/10] Setting up Bun...${NC}"
export BUN_INSTALL="$HOME/.bun"
export PATH="$BUN_INSTALL/bin:$PATH"

if ! command -v bun &> /dev/null; then
    echo "Installing Bun..."
    curl -fsSL https://bun.sh/install | bash
    export BUN_INSTALL="$HOME/.bun"
    export PATH="$BUN_INSTALL/bin:$PATH"
fi
echo -e "${GREEN}✓ Bun version: $(bun -v)${NC}"

# =============================================================================
# STEP 4: Node.js & Angular CLI
# =============================================================================
echo -e "${BLUE}[4/10] Setting up Node.js & Angular CLI...${NC}"
export NVM_DIR="$HOME/.nvm"

if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    echo "Installing NVM..."
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi

echo "Loading NVM..."
\. "$NVM_DIR/nvm.sh"

echo "Installing Node LTS..."
nvm install --lts
nvm use --lts
echo -e "${GREEN}✓ Node version: $(node -v)${NC}"

echo "Installing @angular/cli globally using Bun..."
bun add -g @angular/cli
echo -e "${GREEN}✓ Angular CLI installed${NC}"

# =============================================================================
# STEP 5: Check Dependencies
# =============================================================================
echo -e "${BLUE}[5/10] Checking Dependencies...${NC}"

check_command() {
    local cmd=$1
    if ! command -v "$cmd" &> /dev/null; then
        echo -e "${YELLOW}$cmd not found. Installing...${NC}"
        case $cmd in
            uv)
                if command -v pip &> /dev/null; then
                    pip install uv
                elif command -v pip3 &> /dev/null; then
                    pip3 install uv
                else
                    sudo apt install -y python3-pip
                    pip3 install uv
                fi
                export PATH="$HOME/.local/bin:$PATH"
                ;;
            docker)
                sudo apt install -y docker.io docker-compose-plugin
                sudo systemctl enable --now docker
                sudo usermod -aG docker $USER
                echo -e "${YELLOW}Docker installed. You may need to restart your session.${NC}"
                ;;
            *)
                echo -e "${RED}No installer for $cmd. Please install manually.${NC}"
                return 1
                ;;
        esac
    fi
    echo -e "${GREEN}✓ $cmd found${NC}"
}

check_command uv
check_command docker

# =============================================================================
# STEP 6: Environment Configuration
# =============================================================================
echo -e "${BLUE}[6/10] Environment Configuration...${NC}"

# Check if all .env files exist
all_env_exist=true
skip_env_config=false

[ ! -f "backend/app/.env" ] && all_env_exist=false
[ ! -f "frontend/.env" ] && all_env_exist=false
[ ! -f "docker/.env" ] && all_env_exist=false

if [ "$all_env_exist" = true ]; then
    echo -e "${GREEN}✓ All .env files already exist.${NC}"
    read -p "Do you want to reconfigure them? [y/N]: " reconfigure
    if [[ ! "$reconfigure" =~ ^[Yy]$ ]]; then
        skip_env_config=true
        echo -e "${BLUE}Skipping environment configuration.${NC}"
    fi
fi

if [ "$skip_env_config" = false ]; then
    echo ""
    echo "Environment Configuration Mode:"
    echo "  1) Interactive (configure each variable)"
    echo "  2) Quick (use .env.example defaults)"
    echo "  3) Skip (don't create .env files)"
    read -p "Select [1-3]: " env_mode

    case $env_mode in
        1)
            # ─────────────────────────────────────────────────────────────
            # INTERACTIVE MODE
            # ─────────────────────────────────────────────────────────────
            echo ""
            echo -e "${BLUE}═══ Shared Variables (used by all components) ═══${NC}"
            
            # SurrealDB
            read -p "SURREALDB_PORT [8000]: " SURREALDB_PORT
            SURREALDB_PORT=${SURREALDB_PORT:-8000}
            
            read -p "SURREALDB_USER [root]: " SURREALDB_USER
            SURREALDB_USER=${SURREALDB_USER:-root}
            
            read -sp "SURREALDB_PASS [root]: " SURREALDB_PASS
            SURREALDB_PASS=${SURREALDB_PASS:-root}
            echo ""
            
            read -p "SURREALDB_DB [test]: " SURREALDB_DB
            SURREALDB_DB=${SURREALDB_DB:-test}
            
            read -p "SURREALDB_NAMESPACE [test]: " SURREALDB_NAMESPACE
            SURREALDB_NAMESPACE=${SURREALDB_NAMESPACE:-test}
            
            # Auth Secret
            echo ""
            read -p "Auto-generate BETTERAUTH_SECRET? [Y/n]: " gen_secret
            if [[ ! "$gen_secret" =~ ^[Nn]$ ]]; then
                BETTERAUTH_SECRET=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
                echo -e "${GREEN}Generated: ${BETTERAUTH_SECRET:0:8}...${NC}"
            else
                read -sp "BETTERAUTH_SECRET: " BETTERAUTH_SECRET
                echo ""
            fi
            
            # Neo4j
            read -sp "NEO4J_PASSWORD [password]: " NEO4J_PASSWORD
            NEO4J_PASSWORD=${NEO4J_PASSWORD:-password}
            echo ""
            
            echo ""
            echo -e "${BLUE}═══ Backend-Specific Variables ═══${NC}"
            
            read -p "SERVER_PORT [8980]: " SERVER_PORT
            SERVER_PORT=${SERVER_PORT:-8980}
            
            read -p "CLIENT_URL [http://localhost:4200]: " CLIENT_URL
            CLIENT_URL=${CLIENT_URL:-http://localhost:4200}
            
            echo ""
            echo -e "${BLUE}═══ Frontend-Specific Variables ═══${NC}"
            
            read -p "ADMIN_EMAIL [admin@occultashield.local]: " ADMIN_EMAIL
            ADMIN_EMAIL=${ADMIN_EMAIL:-admin@occultashield.local}
            
            read -sp "ADMIN_PASSWORD [changeme123]: " ADMIN_PASSWORD
            ADMIN_PASSWORD=${ADMIN_PASSWORD:-changeme123}
            echo ""
            
            read -p "ADMIN_NAME [Admin User]: " ADMIN_NAME
            ADMIN_NAME=${ADMIN_NAME:-Admin User}
            
            read -p "SMTP_USER (leave empty to skip): " SMTP_USER
            if [ -n "$SMTP_USER" ]; then
                read -sp "SMTP_PASS: " SMTP_PASS
                echo ""
                read -p "SMTP_FROM [OccultaShield <no-reply@occultashield.local>]: " SMTP_FROM
                SMTP_FROM=${SMTP_FROM:-"OccultaShield <no-reply@occultashield.local>"}
            else
                SMTP_PASS=""
                SMTP_FROM=""
            fi
            ;;
        2)
            # ─────────────────────────────────────────────────────────────
            # QUICK MODE - Use defaults
            # ─────────────────────────────────────────────────────────────
            echo "Using default values from .env.example files..."
            SURREALDB_PORT=8000
            SURREALDB_USER=root
            SURREALDB_PASS=root
            SURREALDB_DB=test
            SURREALDB_NAMESPACE=test
            BETTERAUTH_SECRET=$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)
            NEO4J_PASSWORD=password
            SERVER_PORT=8980
            CLIENT_URL=http://localhost:4200
            ADMIN_EMAIL=admin@occultashield.local
            ADMIN_PASSWORD=changeme123
            ADMIN_NAME="Admin User"
            SMTP_USER=""
            SMTP_PASS=""
            SMTP_FROM=""
            echo -e "${GREEN}✓ Generated BETTERAUTH_SECRET: ${BETTERAUTH_SECRET:0:8}...${NC}"
            ;;
        3)
            skip_env_config=true
            echo -e "${BLUE}Skipping environment configuration.${NC}"
            ;;
        *)
            echo -e "${RED}Invalid option. Skipping configuration.${NC}"
            skip_env_config=true
            ;;
    esac

    # ─────────────────────────────────────────────────────────────────────
    # Generate .env files
    # ─────────────────────────────────────────────────────────────────────
    if [ "$skip_env_config" = false ]; then
        echo ""
        echo "Generating .env files..."
        
        # Backend .env
        cat > backend/app/.env << EOF
# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=$SERVER_PORT
Production=False

# Client Configuration (CORS)
CLIENT_URL=$CLIENT_URL

# Security (Better-Auth)
BETTERAUTH_SECRET=$BETTERAUTH_SECRET

# Database: SurrealDB
SURREALDB_HOST=localhost
SURREALDB_PORT=$SURREALDB_PORT
SURREALDB_USER=$SURREALDB_USER
SURREALDB_PASS=$SURREALDB_PASS
SURREALDB_DB=$SURREALDB_DB
SURREALDB_NAMESPACE=$SURREALDB_NAMESPACE
SURREALDB_LOG=info
SURREALDB_ITEM=test

# Database: Neo4j (GraphRAG)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=$NEO4J_PASSWORD

# AI Models
DETECTION_MODEL_PATH=yolo11n-seg.pt
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"
EOF
        echo -e "${GREEN}✓ backend/app/.env created${NC}"

        # Frontend .env
        cat > frontend/.env << EOF
# Application Settings
Production=False
PORT=4201
CLIENT_URL=$CLIENT_URL

# Better-Auth Security
BETTERAUTH_SECRET=$BETTERAUTH_SECRET

# Admin Auto-Initialization
ADMIN_EMAIL=$ADMIN_EMAIL
ADMIN_PASSWORD=$ADMIN_PASSWORD
ADMIN_NAME="$ADMIN_NAME"

# Email Service (SMTP)
SMTP_USER=$SMTP_USER
SMTP_PASS=$SMTP_PASS
SMTP_FROM="$SMTP_FROM"

# Database: SurrealDB (Direct access for SSR/Server)
SURREALDB_HOST=localhost
SURREALDB_PORT=$SURREALDB_PORT
SURREALDB_USER=$SURREALDB_USER
SURREALDB_PASS=$SURREALDB_PASS
SURREALDB_DB=$SURREALDB_DB
SURREALDB_NAMESPACE=$SURREALDB_NAMESPACE
EOF
        echo -e "${GREEN}✓ frontend/.env created${NC}"

        # Docker .env
        cat > docker/.env << EOF
NEO4J_AUTH=neo4j/$NEO4J_PASSWORD
NEO4J_USER=neo4j
NEO4J_PASS=$NEO4J_PASSWORD
SURREALDB_USER=$SURREALDB_USER
SURREALDB_PASS=$SURREALDB_PASS
SURREALDB_NAMESPACE=$SURREALDB_NAMESPACE
SURREALDB_DATABASE=$SURREALDB_DB
SURREALDB_PORT=$SURREALDB_PORT
SURREALDB_LOG=info
AUTH_SECRET=$BETTERAUTH_SECRET
VITE_API_URL=http://localhost:$SERVER_PORT/api/v1
EOF
        echo -e "${GREEN}✓ docker/.env created${NC}"
    fi
fi

# =============================================================================
# STEP 7: Install Dependencies
# =============================================================================
echo -e "${BLUE}[7/10] Installing Dependencies...${NC}"

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

echo -e "${GREEN}✓ All dependencies installed${NC}"

# =============================================================================
# STEP 8: Infrastructure Setup (Docker)
# =============================================================================
echo -e "${BLUE}[8/10] Infrastructure Setup...${NC}"

read -p "Start Docker services (Neo4j + SurrealDB)? [Y/n]: " start_docker
if [[ ! "$start_docker" =~ ^[Nn]$ ]]; then
    echo "Starting Docker Services..."
    cd docker || exit
    docker compose up -d
    cd ..
    echo -e "${GREEN}✓ Docker services started${NC}"

    echo "Waiting for databases to be ready (15 seconds)..."
    sleep 15
else
    echo -e "${BLUE}Skipping Docker services startup.${NC}"
fi

# =============================================================================
# STEP 9: Optional Setup
# =============================================================================
echo -e "${BLUE}[9/10] Optional Setup...${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# Hugging Face Login (for Gemma LLM)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}Note: The Gemma LLM model requires Hugging Face authentication.${NC}"
echo "If you skip this, the verification module will use fallback rules."
read -p "Setup Hugging Face login? (needed for Gemma LLM) [y/N]: " setup_hf

if [[ "$setup_hf" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Steps to get access:"
    echo "  1. Visit: https://huggingface.co/google/gemma-3n-E4B-it"
    echo "  2. Accept the license agreement"
    echo "  3. Login with your Hugging Face account below"
    echo ""
    
    if ! command -v huggingface-cli &> /dev/null; then
        echo "Installing huggingface_hub..."
        pip install huggingface_hub
    fi
    
    huggingface-cli login
    echo -e "${GREEN}✓ Hugging Face login complete${NC}"
fi

# ─────────────────────────────────────────────────────────────────────────────
# GDPR Knowledge Graph Ingestion
# ─────────────────────────────────────────────────────────────────────────────
echo ""
if nc -z localhost 7687 2>/dev/null; then
    echo -e "${GREEN}✓ Neo4j detected on port 7687${NC}"
    
    read -p "Ingest GDPR data into Neo4j Knowledge Graph? [y/N]: " ingest_gdpr
    if [[ "$ingest_gdpr" =~ ^[Yy]$ ]]; then
        echo "Running GDPR Knowledge Graph Ingestion..."
        cd backend/app || exit

        if [ -f ".kaggle/kaggle.json" ]; then
            echo "✓ Kaggle credentials found"
            KAGGLE_CONFIG_DIR="$(pwd)/.kaggle" uv run python scripts/gdpr_ingestion/enhanced_ingest_gdpr.py
        else
            echo "⚠ Kaggle credentials not found (optional for local PDF)"
            uv run python scripts/gdpr_ingestion/enhanced_ingest_gdpr.py
        fi

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ GDPR Knowledge Graph ingestion completed!${NC}"
        else
            echo -e "${RED}✗ GDPR ingestion failed. Check logs above.${NC}"
        fi
        cd ../..
    else
        echo -e "${BLUE}Skipping GDPR ingestion.${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Neo4j not detected on port 7687${NC}"
    echo "GDPR Knowledge Graph requires Neo4j. You can:"
    echo "  1. Start Docker: cd docker && docker compose up -d"
    echo "  2. Run ingestion later: cd backend/app && ./setup_gdpr.sh"
fi

# =============================================================================
# STEP 10: Execution Menu
# =============================================================================
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      Installation Complete!                       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "What do you want to start?"
echo "  1) Frontend + Backend"
echo "  2) Frontend Only"
echo "  3) Backend Only"
echo "  4) Exit"
read -p "Select [1-4]: " option

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
        echo ""
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Frontend: http://localhost:4200${NC}"
        echo -e "${GREEN}  Backend:  http://localhost:${SERVER_PORT:-8980}${NC}"
        echo -e "${GREEN}  Neo4j:    http://localhost:7474${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
        echo "Press Ctrl+C to stop all services."
        wait $PID_BACKEND $PID_FRONTEND
        ;;
    2)
        start_frontend
        echo -e "${GREEN}Frontend running at http://localhost:4200${NC}"
        wait $PID_FRONTEND
        ;;
    3)
        start_backend
        echo -e "${GREEN}Backend running at http://localhost:${SERVER_PORT:-8980}${NC}"
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
