# EduSaaS CRM — Production Deployment & Operations Guide

This guide details the complete production setup, security configuration, and maintenance procedures for deploying **EduSaaS CRM** on an Ubuntu 22.04 / 24.04 LTS server with Docker, Docker Compose, PostgreSQL 16, Redis 7, Celery, and Nginx.

---

## 1. System Requirements & Architecture

| Component | Minimum Spec | Recommended Production Spec |
|---|---|---|
| **OS** | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| **CPU** | 2 vCPUs | 4 - 8 vCPUs |
| **RAM** | 4 GB | 8 - 16 GB |
| **Disk** | 50 GB NVMe SSD | 100+ GB NVMe SSD |
| **Docker Engine** | 25.0+ | Latest CE |
| **Docker Compose** | 2.24+ | Latest Plugin |

### Architecture Layout
```mermaid
flowchart TD
    Client["Clients (Browser / Mobile)"] -->|HTTPS 443 / WSS| NginxProxy["Nginx SSL Reverse Proxy & Gateway\n(Rate Limiting & Security Headers)"]
    
    subgraph InternalNetwork ["Isolated Docker Bridge Network"]
        NginxProxy -->|/api/ & /ws/| FastAPI["FastAPI Backend Cluster (Gunicorn / Uvicorn)\n(Non-Root 'edusaas' User)"]
        NginxProxy -->|/| WebFrontend["Web Frontend (React / Vite Nginx)"]
        
        FastAPI -->|PostgreSQL Wire (RLS)| PostgresDB[("PostgreSQL 16 (Enterprise)\nRow Level Security Scoped")]
        FastAPI -->|Redis Protocol| RedisCluster[("Redis 7 (LRU Cache &\nCelery Task Broker)")]
        
        CeleryWorker["Celery Distributed Workers\n(Emails, SMS, Push, PDF Exports)"] --> RedisCluster
        CeleryWorker --> PostgresDB
        
        CeleryBeat["Celery Beat Scheduler\n(Attendance Digests & Periodic Reports)"] --> RedisCluster
        
        AutoBackup["Daily Automated Backup Container\n(pg_dump + 30-Day Retention)"] --> PostgresDB
    end
```

---

## 2. Server Provisioning & Initial Hardening

### A. Update Packages & Firewall (UFW)
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git ufw fail2ban jq ca-certificates gnupg lsb-release

# Configure strict firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp     # SSH (or your custom SSH port)
sudo ufw allow 80/tcp     # HTTP (Let's Encrypt renewal)
sudo ufw allow 443/tcp    # HTTPS
sudo ufw enable
```

### B. Install Docker & Docker Compose Plugin
```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

---

## 3. Repository Deployment & Configuration

### A. Clone Repository to Production Root
```bash
sudo mkdir -p /opt/edusaas
sudo chown -R $USER:$USER /opt/edusaas
git clone https://github.com/your-org/edusaas-crm.git /opt/edusaas
cd /opt/edusaas
```

### B. Configure Environment Variables
Copy and customize production environment configurations:
```bash
# 1. Root Compose Environment
cp .env.production.example .env.production

# 2. Backend Environment
cp backend/.env.production.example backend/.env.production

# 3. Web Frontend Environment
cp web/.env.production.example web/.env.production
```

> [!IMPORTANT]
> Generate unique 32-byte cryptographic keys for production:
> ```bash
> # Secret Key for JWT Signing:
> python3 -c "import secrets; print(secrets.token_hex(32))"
> 
> # Database & Redis Passwords:
> openssl rand -hex 32
> ```
> Update `.env.production` and `backend/.env.production` with these generated values. Ensure `DEBUG=false` in `backend/.env.production`.

Use separate passwords for `POSTGRES_USER` and `POSTGRES_APP_USER`. Set `POSTGRES_APP_PASSWORD` in the root file and update the backend `DATABASE_URL` to use the application role and the same password. Keep `backend` in `ALLOWED_HOSTS` for the internal health probe.

For an existing installation, keep the database name and administrator credentials used by the existing PostgreSQL volume. Add the application credentials before running the updated deploy script. The script grants the runtime role access to existing tables without recreating the database.

---

## 4. Let's Encrypt SSL / TLS Setup

To generate SSL certificates for your apex domain and wildcard subdomain:
```bash
# 1. Run temporary certbot challenge
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
  --email ops@edusaas.com --agree-tos --no-eff-email \
  -d edusaas.com -d *.edusaas.com" certbot
```

Certbot will automatically renew certificates every 12 hours via the standing `certbot` container in `docker-compose.prod.yml`.

---

## 5. Deployment Execution

Make scripts executable and execute the automated deployment pipeline:
```bash
chmod +x scripts/*.sh
./scripts/deploy.sh main
```

The script will:
1. Verify pre-flight environment variables.
2. Build optimized multi-stage Docker images for backend and web frontend.
3. Start PostgreSQL and Redis health-checked containers.
4. Provision the limited application role and run Alembic migrations in a separate container with the database administrator credentials.
5. Launch FastAPI cluster, Celery workers, Celery beat, Nginx reverse proxy, and automated backup scheduler.
6. Wait for the readiness endpoint to confirm PostgreSQL, Redis, and active row-level security for the runtime role.

---

## 6. Verification & Health Monitoring

Run cluster diagnostic check:
```bash
./scripts/healthcheck.sh
```

To run high-concurrency performance and stress testing:
```bash
python3 scripts/load_test.py --url https://edusaas.com --users 50 --requests 300
```

---

## 7. Disaster Recovery & Backups

### Automated Backups
The `backup` service in `docker-compose.prod.yml` runs every 24 hours, creating custom-format compressed dumps into the `backups_data` volume and enforcing a 30-day retention window.

### On-Demand Manual Backup
```bash
./scripts/backup.sh /var/backups/edusaas
```

### Full Disaster Restoration
```bash
./scripts/restore.sh /var/backups/edusaas/edusaas_db_YYYYMMDD_HHMMSS.dump
```
