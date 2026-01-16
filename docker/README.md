# 🐳 Docker Infrastructure

This directory contains the Docker Compose configurations for OccultaShield's database infrastructure.

---

## 📁 Directory Structure

```
docker/
├── .env.example            # Template for .env
├── docker-compose.yml      # Development setup (databases only)
├── final-docker-compose.yml # Production setup (full stack)
└── legacy_docker-compose/  # Old configurations (archived)
```

---

## 🚀 Quick Start

### Development (Databases Only)

```bash
cd docker
cp .env.example .env
# Edit .env with your credentials
docker compose up -d
```

This starts:
| Service | Port | Description |
|---------|------|-------------|
| **Neo4j** | 7474 (HTTP), 7687 (Bolt) | GDPR Knowledge Graph |
| **SurrealDB** | 8000 | Application database |

### Check Status

```bash
docker compose ps
docker compose logs -f
```

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```env
# Neo4j
NEO4J_AUTH=neo4j/secret_password
NEO4J_USER=neo4j
NEO4J_PASS=secret_password

# SurrealDB
SURREALDB_USER=root
SURREALDB_PASS=secret_password
SURREALDB_NAMESPACE=test
SURREALDB_DATABASE=Occultashield_database
SURREALDB_PORT=8000
SURREALDB_LOG=info

# Application
AUTH_SECRET=changeme_dev_secret
VITE_API_URL=http://localhost:8900/api/v1
```

> ⚠️ **Important**: These credentials must match in `backend/app/.env` and `frontend/.env`.

---

## 📦 Services

### Neo4j (Knowledge Graph)

- **Image**: `neo4j:latest`
- **Ports**: 7474 (Browser), 7687 (Bolt)
- **Volume**: `./neo4j/` for persistent data
- **Purpose**: Stores GDPR articles for GraphRAG verification

**Access**:
- Browser UI: http://localhost:7474
- Default credentials: `neo4j` / `Occultashield_neo4j`

### SurrealDB (Application Database)

- **Image**: `surrealdb/surrealdb:latest`
- **Port**: 8000
- **Volume**: `./surrealdb-data/` for persistent data
- **Purpose**: Users, sessions, audit logs, video metadata

**Features**:
- Auto-imports schema from `../db_files/schema.surql`
- Health check enabled (30s interval)
- RocksDB backend for persistence

---

## 🏭 Production Setup

Use `final-docker-compose.yml` for full-stack deployment:

```bash
docker compose -f final-docker-compose.yml up -d
```

This includes:
| Service | Port | Notes |
|---------|------|-------|
| **neo4j** | 7474, 7687 | With APOC plugin |
| **surrealdb** | 8000 | Persistent storage |
| **backend** | 8900 | FastAPI + GPU support |
| **frontend** | 4000 | Angular SSR |

### GPU Support

The backend container requests NVIDIA GPU:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

---

## 🔧 Common Operations

### Start Services
```bash
docker compose up -d
```

### Stop Services
```bash
docker compose down
```

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f neo4j
docker compose logs -f surrealdb
```

### Reset Data
```bash
docker compose down -v
rm -rf neo4j-data surrealdb-data neo4j/data
docker compose up -d
```

### Enter Container Shell
```bash
docker exec -it surrealdb /bin/sh
docker exec -it neo4j /bin/bash
```

---

## 🔍 Troubleshooting

### Neo4j Won't Start
```bash
# Check logs
docker compose logs neo4j

# Common fix: reset data
rm -rf neo4j/data neo4j-data
docker compose up -d neo4j
```

### SurrealDB Connection Refused
```bash
# Verify it's running
docker compose ps

# Check health
curl http://localhost:8000/health

# Check credentials match .env
```

### Permission Errors (Linux)
```bash
# SurrealDB runs as root to avoid volume permission issues
# If needed, fix permissions:
sudo chown -R $USER:$USER surrealdb-data
```

### Port Already in Use
```bash
# Find what's using the port
lsof -i :8000
lsof -i :7687

# Kill the process or change port in .env
```

---

## 🗺️ Network Architecture

```
┌─────────────────────────────────────────────────────┐
│                   backend_net                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│   ┌─────────┐      ┌─────────┐      ┌─────────┐   │
│   │  Neo4j  │      │SurrealDB│      │ Backend │   │
│   │  :7687  │◄────►│  :8000  │◄────►│  :8900  │   │
│   └─────────┘      └─────────┘      └─────────┘   │
│                                           │         │
│                                     ┌─────────┐     │
│                                     │Frontend │     │
│                                     │  :4000  │     │
│                                     └─────────┘     │
│                                                     │
└─────────────────────────────────────────────────────┘
         ▲                ▲                 ▲
         │                │                 │
    localhost:7474   localhost:8000   localhost:4000
```

---

## 📚 Related Files

| File | Location | Description |
|------|----------|-------------|
| Database Schema | `../db_files/schema.surql` | SurrealDB tables definition |
| GDPR Ingestion | `../backend/app/scripts/gdpr_ingestion/` | Neo4j data population |

