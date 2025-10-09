# Configuration

## Environment Variables

All configuration is done through environment variables.

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `BACKUP_SOURCE_PATH` | Local filesystem path to backup | `/home/user/documents` |
| `BACKUP_DEST_SERVICE` | Destination storage service type | `s3`, `azblob`, `gcs`, `fs`, etc. |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKUP_DEST_ROOT` | `""` (empty) | Root path in destination storage |
| `BACKUP_COMPRESSION` | `tar.zst` | Compression format (see [Compression](compression.md)) |
| `BACKUP_ARCHIVE_NAME` | `backup_{dirname}_{timestamp}` | Custom archive filename (without extension) |
| `BACKUP_CRON_SCHEDULE` | None | Cron expression for scheduling (see [Scheduling](scheduling.md)) |

## Service-Specific Configuration

### Amazon S3

```bash
export BACKUP_DEST_SERVICE=s3
export S3_BUCKET=my-bucket
export S3_REGION=us-east-1
export S3_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export S3_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export S3_ENDPOINT=https://s3.amazonaws.com  # Optional
```

### Azure Blob Storage

```bash
export BACKUP_DEST_SERVICE=azblob
export AZURE_CONTAINER=my-container
export AZURE_ACCOUNT_NAME=myaccount
export AZURE_ACCOUNT_KEY=your-account-key
```

### Google Cloud Storage

```bash
export BACKUP_DEST_SERVICE=gcs
export GCS_BUCKET=my-bucket
export GCS_CREDENTIAL=/path/to/service-account.json
```

### Alibaba Cloud OSS

```bash
export BACKUP_DEST_SERVICE=oss
export OSS_BUCKET=my-bucket
export OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
export OSS_ACCESS_KEY_ID=your-access-key
export OSS_ACCESS_KEY_SECRET=your-secret
```

### Huawei Cloud OBS

```bash
export BACKUP_DEST_SERVICE=obs
export OBS_BUCKET=my-bucket
export OBS_ENDPOINT=https://obs.region.myhuaweicloud.com
export OBS_ACCESS_KEY_ID=your-access-key
export OBS_SECRET_ACCESS_KEY=your-secret-key
```

### Tencent Cloud COS

```bash
export BACKUP_DEST_SERVICE=cos
export COS_BUCKET=my-bucket
export COS_REGION=ap-guangzhou
export COS_SECRET_ID=your-secret-id
export COS_SECRET_KEY=your-secret-key
```

### WebDAV

```bash
export BACKUP_DEST_SERVICE=webdav
export WEBDAV_ENDPOINT=https://webdav.example.com
export WEBDAV_USERNAME=your-username
export WEBDAV_PASSWORD=your-password
```

### Local Filesystem

```bash
export BACKUP_DEST_SERVICE=fs
export FS_ROOT=/path/to/backup/destination
```

## Configuration Files

You can also load configuration from a file using `source`:

```bash
# Create a config file
cat > backup.env << EOF
export BACKUP_SOURCE_PATH=/home/user/documents
export BACKUP_DEST_SERVICE=s3
export BACKUP_DEST_ROOT=backups/
export S3_BUCKET=my-backup-bucket
export S3_REGION=us-west-2
export S3_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export S3_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
EOF

# Load and run
source backup.env
python main.py
```

## Best Practices

1. **Security**: Never commit credentials to version control. Use environment variables or secret management tools.
2. **Naming**: Use descriptive `BACKUP_ARCHIVE_NAME` values to easily identify backups.
3. **Destination Root**: Use `BACKUP_DEST_ROOT` to organize backups by date or purpose (e.g., `backups/2025/01/`).
4. **Compression**: Choose compression based on your needs (see [Compression Guide](compression.md)).
