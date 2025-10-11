# Configuration

Simple Backup supports three configuration methods:
1. **Configuration files** (TOML or YAML)
2. **Environment variables**
3. **OPENDAL environment variables** (for storage configuration)

## Configuration Priority

When multiple configuration methods are used, they are applied in this order (highest to lowest priority):
1. `OPENDAL_*` environment variables
2. Service-specific environment variables (`S3_*`, `AZURE_*`, etc.)
3. Configuration file values

## Configuration Files

Simple Backup can load configuration from a TOML or YAML file. The application automatically looks for:
- `config.toml`
- `config.yaml`
- `config.yml`

Copy one of the example files to get started:

```bash
# Using TOML (recommended)
cp config.toml.example config.toml

# Or using YAML
cp config.yaml.example config.yaml
```

### Single Destination (Legacy Format)

```toml
# config.toml
source_path = "/path/to/backup"
dest_service = "s3"
dest_root = "backups/"
compression = "tar.zst"

[retention]
daily = 7
weekly = 4
monthly = 6

[storage]
bucket = "my-backup-bucket"
region = "us-east-1"
access_key_id = "AKIAxxxxx"
secret_access_key = "xxxxx"
```

### Multiple Destinations (New Format)

```toml
# config.toml
source_path = "/path/to/backup"
compression = "tar.zst"

[retention]
daily = 7
weekly = 4
monthly = 6

[[destinations]]
service = "s3"
root = "backups/"

[destinations.storage]
bucket = "my-primary-bucket"
region = "us-east-1"
access_key_id = "AKIAxxxxx"
secret_access_key = "xxxxx"

[[destinations]]
service = "s3"
root = "backups/"

[destinations.storage]
bucket = "my-secondary-bucket"
region = "us-west-2"
access_key_id = "AKIAyyyyy"
secret_access_key = "yyyyy"
```

Or in YAML:

```yaml
# config.yaml
source_path: /path/to/backup
compression: tar.zst

retention:
  daily: 7
  weekly: 4
  monthly: 6

destinations:
  - service: s3
    root: backups/
    storage:
      bucket: my-primary-bucket
      region: us-east-1
      access_key_id: AKIAxxxxx
      secret_access_key: xxxxx
  
  - service: azblob
    root: backups/
    storage:
      container: my-backups
      account_name: myaccount
      account_key: xxxxx
```

**Features**:
- Backup to multiple destinations simultaneously
- Each destination can use different storage services
- Independent storage configurations per destination
- Retention policies apply per destination
- Archive is created once and uploaded to all destinations (efficient)
- **Startup validation**: Connectivity to all destinations is tested before backup runs

**Note**: Sensitive credentials in config files can be overridden by environment variables for better security.

## Environment Variables

All configuration can also be done through environment variables, which take precedence over config file values.

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `BACKUP_SOURCE_PATH` | Local filesystem path to backup | `/home/user/documents` |
| `BACKUP_DEST_SERVICE` | Destination storage service type (legacy single destination) | `s3`, `azblob`, `gcs`, `fs`, etc. |

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

## OPENDAL Environment Variables

You can use [OpenDAL's environment variables](https://opendal.apache.org/docs/) as an alternative to service-specific variables. These take the highest precedence:

```bash
# Example for S3 using OPENDAL variables
export OPENDAL_S3_BUCKET=my-bucket
export OPENDAL_S3_REGION=us-east-1
export OPENDAL_S3_ACCESS_KEY_ID=AKIAxxxxx
export OPENDAL_S3_SECRET_ACCESS_KEY=xxxxx
```

This is especially useful in containerized environments where you want to use standard OpenDAL variable names.

## Environment File

You can also load configuration from an environment file using `source`:

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

1. **Configuration Method**: Use config files for base configuration, environment variables for secrets and environment-specific overrides.
2. **Security**: Never commit credentials to version control. Use environment variables or secret management tools.
3. **Naming**: Use descriptive `BACKUP_ARCHIVE_NAME` values to easily identify backups.
4. **Destination Root**: Use `BACKUP_DEST_ROOT` to organize backups by date or purpose (e.g., `backups/2025/01/`).
5. **Compression**: Choose compression based on your needs (see [Compression Guide](compression.md)).
6. **Validation**: Ensure destination paths exist and are writable. Simple Backup validates connectivity on startup by creating a test file (`.simple-backup-test`) in each destination. If validation fails, the backup will not proceed.

## Example Configurations

### Using Config File with Environment Variable Overrides

```toml
# config.toml - base configuration
source_path = "/data"
dest_service = "s3"
compression = "tar.zst"

[storage]
bucket = "my-backup-bucket"
region = "us-east-1"
```

```bash
# Override credentials via environment variables
export S3_ACCESS_KEY_ID=AKIAxxxxx
export S3_SECRET_ACCESS_KEY=xxxxx
python main.py
```

### Using OPENDAL Variables in Kubernetes

```yaml
env:
  - name: BACKUP_SOURCE_PATH
    value: /data
  - name: BACKUP_DEST_SERVICE
    value: s3
  - name: OPENDAL_S3_BUCKET
    value: my-backup-bucket
  - name: OPENDAL_S3_REGION
    value: us-east-1
  - name: OPENDAL_S3_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef:
        name: s3-credentials
        key: access_key_id
  - name: OPENDAL_S3_SECRET_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: s3-credentials
        key: secret_access_key
```
