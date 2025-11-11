# Platform Infrastructure

Docker Compose configurations for local development and Kubernetes configurations for production.

## Local Development (Docker Compose)

### Services

#### MinIO (S3-compatible storage)
- **API Port**: 9000
- **Console**: http://localhost:9001
- **Credentials**: minioadmin / minioadmin
- **Purpose**: Dataset and checkpoint storage

#### PostgreSQL (Optional)
- **Port**: 5432
- **Database**: platform
- **Credentials**: platform / platform
- **Purpose**: Production-like database testing

#### Redis (Optional)
- **Port**: 6379
- **Purpose**: Cache and message queue

### Quick Start

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Start MinIO only
docker-compose -f docker-compose.dev.yml up -d minio

# Check status
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs -f minio

# Stop services
docker-compose -f docker-compose.dev.yml down
```

### MinIO Setup

Access console at http://localhost:9001 and create bucket:

1. Login: `minioadmin` / `minioadmin`
2. Create bucket: `vision-platform`

Or use CLI:

```bash
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/vision-platform
```

## Production (Kubernetes)

See `helm/` and `terraform/` directories for production deployment configurations:

- **Helm Charts**: Kubernetes deployments
- **Terraform**: Cloud infrastructure (AWS, Railway, etc.)

## Environment Configuration

Update `.env` files to use local services:

```env
# Backend
DATABASE_URL=postgresql+asyncpg://platform:platform@localhost:5432/platform
S3_ENDPOINT=http://localhost:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
BUCKET_NAME=vision-platform
```

## License

Copyright © 2025 Vision AI Platform Team
