# Docker Deployment

This guide covers running simple-backup using Docker and Docker Compose.

> **Note:** For Kubernetes deployment including Operator support, see [Kubernetes Deployment Guide](kubernetes.md)

## Quick Start

### 1. Using Docker Compose (Recommended)

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your configuration:**
   ```bash
   # Required
   BACKUP_SOURCE_PATH=/data
   BACKUP_DEST_SERVICE=s3
   BACKUP_COMPRESSION=tar.zst
   
   # S3 Configuration
   S3_BUCKET=my-backup-bucket
   S3_REGION=us-east-1
   S3_ACCESS_KEY_ID=your-access-key
   S3_SECRET_ACCESS_KEY=your-secret-key
   
   # Optional: Schedule backups (daily at 2 AM)
   BACKUP_CRON_SCHEDULE=0 2 * * *
   
   # Optional: Retention policy
   BACKUP_RETENTION_DAILY=7
   BACKUP_RETENTION_WEEKLY=4
   BACKUP_RETENTION_MONTHLY=6
   ```

3. **Update `docker-compose.yml` volumes:**
   ```yaml
   volumes:
     - /path/to/your/data:/data:ro
     - backup-dest:/backups
   ```

4. **Start the container:**
   ```bash
   docker-compose up -d
   ```

5. **View logs:**
   ```bash
   docker-compose logs -f
   ```

### 2. Using Docker CLI

**One-time backup:**
```bash
docker build -t simple-backup .

docker run --rm \
  -e BACKUP_SOURCE_PATH=/data \
  -e BACKUP_DEST_SERVICE=s3 \
  -e BACKUP_COMPRESSION=tar.zst \
  -e S3_BUCKET=my-backup-bucket \
  -e S3_REGION=us-east-1 \
  -e S3_ACCESS_KEY_ID=your-access-key \
  -e S3_SECRET_ACCESS_KEY=your-secret-key \
  -v /path/to/your/data:/data:ro \
  simple-backup
```

**Scheduled backups:**
```bash
docker run -d \
  --name simple-backup \
  -e BACKUP_SOURCE_PATH=/data \
  -e BACKUP_DEST_SERVICE=s3 \
  -e BACKUP_COMPRESSION=tar.zst \
  -e BACKUP_CRON_SCHEDULE="0 2 * * *" \
  -e S3_BUCKET=my-backup-bucket \
  -e S3_REGION=us-east-1 \
  -e S3_ACCESS_KEY_ID=your-access-key \
  -e S3_SECRET_ACCESS_KEY=your-secret-key \
  -v /path/to/your/data:/data:ro \
  --restart unless-stopped \
  simple-backup
```

## Storage Examples

### Local Filesystem

```yaml
services:
  simple-backup:
    build: .
    env_file:
      - .env
    volumes:
      - /path/to/source:/data:ro
      - /path/to/backups:/backups
    environment:
      BACKUP_DEST_SERVICE: fs
      FS_ROOT: /backups
```

### AWS S3

```yaml
services:
  simple-backup:
    build: .
    env_file:
      - .env
    volumes:
      - /path/to/source:/data:ro
    environment:
      BACKUP_DEST_SERVICE: s3
      S3_BUCKET: my-backup-bucket
      S3_REGION: us-east-1
      S3_ACCESS_KEY_ID: ${S3_ACCESS_KEY_ID}
      S3_SECRET_ACCESS_KEY: ${S3_SECRET_ACCESS_KEY}
```

### Azure Blob Storage

```yaml
services:
  simple-backup:
    build: .
    env_file:
      - .env
    volumes:
      - /path/to/source:/data:ro
    environment:
      BACKUP_DEST_SERVICE: azblob
      AZURE_CONTAINER: my-backup-container
      AZURE_ACCOUNT_NAME: ${AZURE_ACCOUNT_NAME}
      AZURE_ACCOUNT_KEY: ${AZURE_ACCOUNT_KEY}
```

### Google Cloud Storage

```yaml
services:
  simple-backup:
    build: .
    env_file:
      - .env
    volumes:
      - /path/to/source:/data:ro
      - ./gcs-credentials.json:/credentials.json:ro
    environment:
      BACKUP_DEST_SERVICE: gcs
      GCS_BUCKET: my-backup-bucket
      GCS_CREDENTIAL: /credentials.json
```

### WebDAV

```yaml
services:
  simple-backup:
    build: .
    env_file:
      - .env
    volumes:
      - /path/to/source:/data:ro
    environment:
      BACKUP_DEST_SERVICE: webdav
      WEBDAV_ENDPOINT: https://webdav.example.com
      WEBDAV_USERNAME: ${WEBDAV_USERNAME}
      WEBDAV_PASSWORD: ${WEBDAV_PASSWORD}
```

## Advanced Configuration

### Multiple Backup Jobs

Create multiple services in `docker-compose.yml` for different backup jobs:

```yaml
services:
  backup-database:
    build: .
    container_name: backup-database
    volumes:
      - /var/lib/postgresql:/data:ro
    environment:
      BACKUP_SOURCE_PATH: /data
      BACKUP_DEST_SERVICE: s3
      BACKUP_COMPRESSION: tar.zst
      BACKUP_CRON_SCHEDULE: "0 3 * * *"
      S3_BUCKET: database-backups
      S3_REGION: us-east-1
      BACKUP_RETENTION_DAILY: 7
      BACKUP_RETENTION_WEEKLY: 4
    env_file:
      - .env
    restart: unless-stopped

  backup-uploads:
    build: .
    container_name: backup-uploads
    volumes:
      - /var/www/uploads:/data:ro
    environment:
      BACKUP_SOURCE_PATH: /data
      BACKUP_DEST_SERVICE: s3
      BACKUP_COMPRESSION: tar.zst
      BACKUP_CRON_SCHEDULE: "0 4 * * *"
      S3_BUCKET: uploads-backups
      S3_REGION: us-east-1
      BACKUP_RETENTION_WEEKLY: 8
      BACKUP_RETENTION_MONTHLY: 12
    env_file:
      - .env
    restart: unless-stopped
```

### Healthchecks

Add a healthcheck to monitor the container:

```yaml
services:
  simple-backup:
    build: .
    env_file:
      - .env
    volumes:
      - /path/to/source:/data:ro
    healthcheck:
      test: ["CMD", "pgrep", "-f", "python"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped
```

### Resource Limits

Limit CPU and memory usage:

```yaml
services:
  simple-backup:
    build: .
    env_file:
      - .env
    volumes:
      - /path/to/source:/data:ro
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
    restart: unless-stopped
```

## Troubleshooting

### View logs
```bash
docker-compose logs -f simple-backup
```

### Check container status
```bash
docker-compose ps
```

### Access container shell
```bash
docker-compose exec simple-backup sh
```

### Test configuration (one-time backup)
```bash
docker-compose run --rm simple-backup
```

### Rebuild after code changes
```bash
docker-compose build
docker-compose up -d
```

## Security Best Practices

1. **Use secrets for sensitive data:**
   ```yaml
   services:
     simple-backup:
       build: .
       secrets:
         - aws_access_key
         - aws_secret_key
       environment:
         S3_ACCESS_KEY_ID_FILE: /run/secrets/aws_access_key
         S3_SECRET_ACCESS_KEY_FILE: /run/secrets/aws_secret_key
   
   secrets:
     aws_access_key:
       file: ./secrets/aws_access_key.txt
     aws_secret_key:
       file: ./secrets/aws_secret_key.txt
   ```

2. **Mount source volumes as read-only** (`:ro` flag)

3. **Don't commit `.env` file** - add it to `.gitignore`

4. **Use specific image tags** instead of `latest` in production

5. **Regularly update base image** for security patches
