#!/bin/bash

# Enhanced GDPR Ingestion Setup Script
# This script checks prerequisites and runs the enhanced ingestion

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  Enhanced GDPR Knowledge Graph Setup                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
echo "🐍 Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✅ $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.8+${NC}"
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
    read -p "Would you like to start Neo4j with Docker? (y/n) " -n 1 -r
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
            echo "   Web UI: http://localhost:7474"
        else
            echo -e "${RED}❌ Failed to start Neo4j${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Please start Neo4j manually and run this script again${NC}"
        exit 1
    fi
fi

# Check required Python packages
echo ""
echo "📦 Checking Python dependencies..."
REQUIRED_PACKAGES="neo4j sentence-transformers requests python-dotenv"
MISSING_PACKAGES=""

for package in $REQUIRED_PACKAGES; do
    if python3 -c "import ${package//-/_}" 2>/dev/null; then
        echo -e "${GREEN}✅ $package${NC}"
    else
        echo -e "${RED}❌ $package${NC}"
        MISSING_PACKAGES="$MISSING_PACKAGES $package"
    fi
done

# Install missing packages
if [ -n "$MISSING_PACKAGES" ]; then
    echo ""
    echo -e "${YELLOW}Installing missing packages:$MISSING_PACKAGES${NC}"
    pip install $MISSING_PACKAGES
fi

# Check optional Kaggle package
echo ""
echo "🔍 Checking optional Kaggle API..."
if python3 -c "import kaggle" 2>/dev/null; then
    echo -e "${GREEN}✅ Kaggle API available${NC}"
    KAGGLE_CONFIG=~/.kaggle/kaggle.json
    if [ -f "$KAGGLE_CONFIG" ]; then
        echo -e "${GREEN}✅ Kaggle credentials configured${NC}"
    else
        echo -e "${YELLOW}⚠️  Kaggle credentials not found at $KAGGLE_CONFIG${NC}"
        echo "   To use Kaggle datasets:"
        echo "   1. Create API token at https://www.kaggle.com/settings"
        echo "   2. Place kaggle.json in ~/.kaggle/"
    fi
else
    echo -e "${YELLOW}⚠️  Kaggle API not installed (optional)${NC}"
    echo "   Install with: pip install kaggle"
fi

# Check .env file
echo ""
echo "🔍 Checking environment configuration..."
ENV_FILE="../../.env"
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}✅ .env file found${NC}"

    # Check required variables
    if grep -q "NEO4J_URI" "$ENV_FILE" && \
       grep -q "NEO4J_PASSWORD" "$ENV_FILE"; then
        echo -e "${GREEN}✅ Neo4j configuration present${NC}"
    else
        echo -e "${YELLOW}⚠️  Missing Neo4j configuration in .env${NC}"
        echo "   Add: NEO4J_URI=bolt://localhost:7687"
        echo "   Add: NEO4J_PASSWORD=Occultashield_neo4j"
    fi
else
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    echo "   Creating default .env file..."
    cat > "$ENV_FILE" << EOL
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=Occultashield_neo4j
EOL
    echo -e "${GREEN}✅ Created .env file with defaults${NC}"
fi

# Run ingestion
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
read -p "Ready to run Enhanced GDPR Ingestion? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Running Enhanced GDPR Ingestion..."
    echo ""

    cd "$(dirname "$0")"
    python3 enhanced_ingest_gdpr.py

    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo -e "${GREEN}✅ Setup Complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Open Neo4j Browser: http://localhost:7474"
    echo "     (user: neo4j, password: Occultashield_neo4j)"
    echo "  2. Verify data: MATCH (a:Article) RETURN count(a)"
    echo "  3. Start the backend server"
    echo "  4. Test video processing with GDPR verification"
else
    echo ""
    echo "Setup cancelled. Run this script again when ready."
fi
