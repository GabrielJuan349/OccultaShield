#!/bin/bash

# Enhanced GDPR Ingestion Setup Script
# Run from: /home/gjuan/OccultaShield/backend/app
# Uses UV environment - all dependencies already installed!

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  Enhanced GDPR Knowledge Graph Setup                      ║"
echo "║  Using UV environment (no pip install needed!)            ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check we're in the right directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ Please run this script from backend/app directory${NC}"
    echo "   cd /home/gjuan/OccultaShield/backend/app"
    echo "   ./setup_gdpr.sh"
    exit 1
fi

# Check UV
echo "🔍 Checking UV..."
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version)
    echo -e "${GREEN}✅ $UV_VERSION${NC}"
else
    echo -e "${RED}❌ UV not found. Please install: https://github.com/astral-sh/uv${NC}"
    exit 1
fi

# Check Neo4j
echo ""
echo "🔍 Checking Neo4j..."
if nc -z localhost 7687 2>/dev/null; then
    echo -e "${GREEN}✅ Neo4j is running on port 7687${NC}"
else
    echo -e "${YELLOW}⚠️  Neo4j not detected on port 7687${NC}"
    echo ""
    echo "Starting Neo4j is recommended. Options:"
    echo ""
    echo "1. Docker (recommended):"
    echo -e "${BLUE}   docker run -d --name neo4j-gdpr -p 7474:7474 -p 7687:7687 \\${NC}"
    echo -e "${BLUE}     -e NEO4J_AUTH=neo4j/Occultashield_neo4j neo4j:latest${NC}"
    echo ""
    echo "2. Local installation:"
    echo -e "${BLUE}   neo4j start${NC}"
    echo ""
    read -p "Would you like to start Neo4j with Docker now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🐳 Starting Neo4j with Docker..."
        docker run -d \
          --name neo4j-gdpr \
          -p 7474:7474 -p 7687:7687 \
          -e NEO4J_AUTH=neo4j/Occultashield_neo4j \
          neo4j:latest

        echo "⏳ Waiting for Neo4j to start (30 seconds)..."
        sleep 30

        if nc -z localhost 7687 2>/dev/null; then
            echo -e "${GREEN}✅ Neo4j started successfully${NC}"
            echo "   📊 Web UI: http://localhost:7474"
            echo "   👤 User: neo4j"
            echo "   🔑 Password: Occultashield_neo4j"
        else
            echo -e "${RED}❌ Failed to start Neo4j${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Please start Neo4j manually and run this script again${NC}"
        exit 1
    fi
fi

# Check .env file
echo ""
echo "🔍 Checking environment configuration..."
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✅ .env file found${NC}"

    # Check required variables
    NEO4J_URI=$(grep "NEO4J_URI" "$ENV_FILE" 2>/dev/null || echo "")
    NEO4J_PASSWORD=$(grep "NEO4J_PASSWORD" "$ENV_FILE" 2>/dev/null || echo "")

    if [ -n "$NEO4J_URI" ] && [ -n "$NEO4J_PASSWORD" ]; then
        echo -e "${GREEN}✅ Neo4j configuration present${NC}"
    else
        echo -e "${YELLOW}⚠️  Adding missing Neo4j configuration to .env${NC}"

        if [ -z "$NEO4J_URI" ]; then
            echo "" >> "$ENV_FILE"
            echo "# Neo4j Configuration" >> "$ENV_FILE"
            echo "NEO4J_URI=bolt://localhost:7687" >> "$ENV_FILE"
        fi

        if [ -z "$NEO4J_PASSWORD" ]; then
            echo "NEO4J_USER=neo4j" >> "$ENV_FILE"
            echo "NEO4J_PASSWORD=Occultashield_neo4j" >> "$ENV_FILE"
        fi

        echo -e "${GREEN}✅ Updated .env file${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  .env file not found, creating...${NC}"
    cat > "$ENV_FILE" << 'EOL'
# Neo4j Configuration for GDPR Knowledge Graph
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=Occultashield_neo4j
EOL
    echo -e "${GREEN}✅ Created .env file with Neo4j defaults${NC}"
fi

# Check optional Kaggle
echo ""
echo "🔍 Checking optional Kaggle API..."
if uv run python -c "import kaggle" 2>/dev/null; then
    echo -e "${GREEN}✅ Kaggle API available in UV environment${NC}"

    # Check for kaggle.json in project directory first, then fallback to home
    LOCAL_KAGGLE_CONFIG=".kaggle/kaggle.json"
    HOME_KAGGLE_CONFIG=~/.kaggle/kaggle.json

    if [ -f "$LOCAL_KAGGLE_CONFIG" ]; then
        echo -e "${GREEN}✅ Kaggle credentials found in project: .kaggle/kaggle.json${NC}"
        # Set KAGGLE_CONFIG_DIR environment variable for the script
        export KAGGLE_CONFIG_DIR="$(pwd)/.kaggle"
    elif [ -f "$HOME_KAGGLE_CONFIG" ]; then
        echo -e "${GREEN}✅ Kaggle credentials found in home: ~/.kaggle/kaggle.json${NC}"
    else
        echo -e "${YELLOW}⚠️  Kaggle credentials not found${NC}"
        echo ""
        echo "   To download Kaggle GDPR datasets:"
        echo "   1. Get API token: https://www.kaggle.com/settings → API → Create Token"
        echo "   2. Place in project directory:"
        echo -e "${BLUE}      .kaggle/kaggle.json${NC} (already exists in your project!)"
        echo ""
        echo "   Script will continue without Kaggle datasets (GDPRtEXT + local data still available)"
    fi
else
    echo -e "${YELLOW}⚠️  Kaggle not in UV environment (optional)${NC}"
    echo "   To add: uv pip install kaggle"
fi

# Summary before execution
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📋 Configuration Summary"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Data sources that will be loaded:"
echo "  ✅ Local JSON files (articles, concepts, mappings)"
echo "  ✅ GitHub GDPRtEXT repository (official GDPR texts)"
if uv run python -c "import kaggle" 2>/dev/null && [ -f "$LOCAL_KAGGLE_CONFIG" -o -f "$HOME_KAGGLE_CONFIG" ]; then
    echo "  ✅ Kaggle datasets (optional enhancement)"
else
    echo "  ⊘  Kaggle datasets (not configured - optional)"
fi
echo ""
echo "Knowledge graph will include:"
echo "  • 99 GDPR Articles with full text"
echo "  • Chapters, Paragraphs, Recitals"
echo "  • Concepts, Data Types, Rights"
echo "  • Detection → Article mappings"
echo "  • Fine tiers and amounts"
echo "  • Semantic embeddings for search"
echo "  • Fulltext indices"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""

# Confirmation
read -p "Ready to run Enhanced GDPR Ingestion? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Setup cancelled. Run again when ready:"
    echo -e "${BLUE}  ./setup_gdpr.sh${NC}"
    exit 0
fi

# Run ingestion with UV
echo ""
echo "🚀 Running Enhanced GDPR Ingestion with UV..."
echo ""

# Execute the ingestion script using UV
# Pass KAGGLE_CONFIG_DIR if it was set
if [ -n "$KAGGLE_CONFIG_DIR" ]; then
    echo "📌 Using Kaggle credentials from: $KAGGLE_CONFIG_DIR"
    KAGGLE_CONFIG_DIR="$KAGGLE_CONFIG_DIR" uv run python scripts/gdpr_ingestion/enhanced_ingest_gdpr.py
else
    uv run python scripts/gdpr_ingestion/enhanced_ingest_gdpr.py
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo -e "${GREEN}✅ GDPR Knowledge Graph Setup Complete!${NC}"
    echo ""
    echo "🎉 Next steps:"
    echo ""
    echo "1. Verify the data in Neo4j Browser:"
    echo -e "   ${BLUE}http://localhost:7474${NC}"
    echo "   User: neo4j"
    echo "   Password: Occultashield_neo4j"
    echo ""
    echo "2. Test queries:"
    echo -e "   ${BLUE}MATCH (a:Article) RETURN count(a)${NC}  # Should return ~99"
    echo -e "   ${BLUE}MATCH (d:DetectionType)-[:VIOLATES]->(a:Article) RETURN d.type, a.number${NC}"
    echo ""
    echo "3. Start the backend server (if not running):"
    echo -e "   ${BLUE}uv run uvicorn main:app --host 0.0.0.0 --port 8980 --reload${NC}"
    echo ""
    echo "4. Test video processing:"
    echo "   Upload a video with faces to verify GDPR compliance checking"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
else
    echo ""
    echo -e "${RED}❌ Ingestion failed. Check logs above for errors.${NC}"
    echo ""
    echo "Common issues:"
    echo "  • Neo4j not running or wrong credentials"
    echo "  • Network issues downloading GDPRtEXT"
    echo "  • Missing Python dependencies (check pyproject.toml)"
    echo ""
    exit 1
fi
