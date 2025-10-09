# Scheduling

## Overview

The backup program supports automated scheduled backups using cron expressions. When a schedule is configured, the program runs continuously and executes backups at the specified times.

## Basic Usage

Set the `BACKUP_CRON_SCHEDULE` environment variable with a cron expression:

```bash
export BACKUP_CRON_SCHEDULE="0 2 * * *"  # Daily at 2 AM
python main.py
```

The program will:
1. Start the scheduler
2. Execute backups according to the cron schedule
3. Run continuously until stopped with Ctrl+C or SIGTERM

## Cron Expression Format

Cron expressions use 5 fields:

```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-6, Sunday=0)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

### Special Characters

- `*` - Any value
- `,` - List of values (e.g., `1,15` = 1st and 15th)
- `-` - Range (e.g., `1-5` = 1 through 5)
- `/` - Step values (e.g., `*/15` = every 15 units)

## Common Schedule Examples

### Hourly
```bash
export BACKUP_CRON_SCHEDULE="0 * * * *"  # Every hour at minute 0
```

### Every 30 Minutes
```bash
export BACKUP_CRON_SCHEDULE="*/30 * * * *"
```

### Daily

```bash
# Daily at 2 AM
export BACKUP_CRON_SCHEDULE="0 2 * * *"

# Daily at 3:30 PM
export BACKUP_CRON_SCHEDULE="30 15 * * *"

# Twice daily (6 AM and 6 PM)
export BACKUP_CRON_SCHEDULE="0 6,18 * * *"
```

### Weekly

```bash
# Every Sunday at 2 AM
export BACKUP_CRON_SCHEDULE="0 2 * * 0"

# Every weekday at 11 PM
export BACKUP_CRON_SCHEDULE="0 23 * * 1-5"

# Every Saturday and Sunday at midnight
export BACKUP_CRON_SCHEDULE="0 0 * * 6,0"
```

### Monthly

```bash
# 1st of every month at 3 AM
export BACKUP_CRON_SCHEDULE="0 3 1 * *"

# 15th and last day of month at midnight
export BACKUP_CRON_SCHEDULE="0 0 15,28-31 * *"
```

### Custom Intervals

```bash
# Every 4 hours
export BACKUP_CRON_SCHEDULE="0 */4 * * *"

# Every 15 minutes during business hours (9 AM - 5 PM)
export BACKUP_CRON_SCHEDULE="*/15 9-17 * * *"

# Weekdays at 9 AM and 5 PM
export BACKUP_CRON_SCHEDULE="0 9,17 * * 1-5"
```

## Complete Example

```bash
#!/bin/bash

# Configuration
export BACKUP_SOURCE_PATH=/home/user/important-data
export BACKUP_DEST_SERVICE=s3
export BACKUP_DEST_ROOT=backups/daily/
export BACKUP_COMPRESSION=tar.zst

# S3 credentials
export S3_BUCKET=my-backup-bucket
export S3_REGION=us-west-2
export S3_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export S3_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# Schedule: Daily at 2 AM
export BACKUP_CRON_SCHEDULE="0 2 * * *"

# Run scheduler
python main.py
```

## Running as a Service

### systemd (Linux)

Create `/etc/systemd/system/simple-backup.service`:

```ini
[Unit]
Description=Simple Backup Service
After=network.target

[Service]
Type=simple
User=backup
WorkingDirectory=/opt/simple-backup
EnvironmentFile=/etc/simple-backup/config.env
ExecStart=/opt/simple-backup/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create `/etc/simple-backup/config.env`:

```bash
BACKUP_SOURCE_PATH=/data/important
BACKUP_DEST_SERVICE=s3
BACKUP_DEST_ROOT=backups/
BACKUP_CRON_SCHEDULE=0 2 * * *
BACKUP_COMPRESSION=tar.zst
S3_BUCKET=my-backup-bucket
S3_REGION=us-west-2
S3_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
S3_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable simple-backup
sudo systemctl start simple-backup
sudo systemctl status simple-backup
```

### Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync

COPY main.py ./

CMD ["python", "main.py"]
```

Run with environment variables:

```bash
docker build -t simple-backup .

docker run -d \
  --name simple-backup \
  --restart unless-stopped \
  -e BACKUP_SOURCE_PATH=/data \
  -e BACKUP_DEST_SERVICE=s3 \
  -e BACKUP_CRON_SCHEDULE="0 2 * * *" \
  -e S3_BUCKET=my-bucket \
  -e S3_REGION=us-west-2 \
  -e S3_ACCESS_KEY_ID=xxx \
  -e S3_SECRET_ACCESS_KEY=xxx \
  -v /path/to/data:/data:ro \
  simple-backup
```

### Docker Compose

`docker-compose.yml`:

```yaml
version: '3.8'

services:
  backup:
    build: .
    restart: unless-stopped
    environment:
      BACKUP_SOURCE_PATH: /data
      BACKUP_DEST_SERVICE: s3
      BACKUP_CRON_SCHEDULE: "0 2 * * *"
      BACKUP_COMPRESSION: tar.zst
      S3_BUCKET: my-backup-bucket
      S3_REGION: us-west-2
      S3_ACCESS_KEY_ID: ${S3_ACCESS_KEY_ID}
      S3_SECRET_ACCESS_KEY: ${S3_SECRET_ACCESS_KEY}
    volumes:
      - /path/to/data:/data:ro
```

Run:

```bash
docker-compose up -d
docker-compose logs -f backup
```

## Graceful Shutdown

The scheduler handles graceful shutdown for:
- **Ctrl+C** (SIGINT)
- **SIGTERM** (e.g., from systemd or Docker)

When stopped, the scheduler:
1. Logs shutdown message
2. Stops accepting new jobs
3. Completes current backup (if running)
4. Exits cleanly

## Logging

View logs to monitor scheduled backups:

```bash
# systemd
sudo journalctl -u simple-backup -f

# Docker
docker logs -f simple-backup

# Docker Compose
docker-compose logs -f backup
```

## One-Time vs Scheduled

If `BACKUP_CRON_SCHEDULE` is **not set**, the program runs a one-time backup and exits:

```bash
# One-time backup
unset BACKUP_CRON_SCHEDULE
python main.py
```

If `BACKUP_CRON_SCHEDULE` **is set**, the program runs continuously as a scheduler:

```bash
# Scheduled backup
export BACKUP_CRON_SCHEDULE="0 2 * * *"
python main.py  # Runs until stopped
```

## Troubleshooting

### Scheduler Not Running

Check that cron expression is valid:
- Must be 5 fields
- Values must be in valid ranges
- Quote the expression in shell

### Backups Not Executing

Verify:
1. Scheduler started successfully (check logs)
2. Cron expression is correct
3. System time is correct
4. All required environment variables are set

### High Memory Usage

For large backups, consider:
1. Reducing backup frequency
2. Using `BACKUP_COMPRESSION=none` for streaming backups
3. Splitting into multiple smaller backup jobs
