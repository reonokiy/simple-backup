# Configuration

Simple Backup supports two configuration methods:
1. **Configuration files** (TOML or YAML)
2. **OPENDAL environment variables** (for storage configuration)

## Configuration Priority

When multiple configuration methods are used, they are applied in this order (highest to lowest priority):
1. `OPENDAL_*` environment variables
2. Service-specific environment variables (`S3_*`, `AZURE_*`, etc.) in storage config
3. Configuration file values

## Configuration Files

Simple Backup can load configuration from a TOML or YAML file. The application automatically looks for:
- `config.toml`
- `config.yaml`
- `config.yml`

Copy one of the example files to get started:

```bash
# Using TOML (recommended)
cp config.example.toml config.toml

# Or using YAML
cp config.example.yaml config.yaml
```

### Multiple Destinations Configuration
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

## Storage Service Environment Variables

When configuring storage in your `destinations` array, you can use environment variables for credentials. These variables are used when they're referenced in the storage config.

### Amazon S3

```bash
export S3_BUCKET=my-bucket
export S3_REGION=us-east-1
export S3_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export S3_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export S3_ENDPOINT=https://s3.amazonaws.com  # Optional
```

### Azure Blob Storage

```bash
export AZURE_CONTAINER=my-container
export AZURE_ACCOUNT_NAME=myaccount
export AZURE_ACCOUNT_KEY=your-account-key
```

### Google Cloud Storage

```bash
export GCS_BUCKET=my-bucket
export GCS_CREDENTIAL=/path/to/service-account.json
```

### Alibaba Cloud OSS

```bash
export OSS_BUCKET=my-bucket
export OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
export OSS_ACCESS_KEY_ID=your-access-key
export OSS_ACCESS_KEY_SECRET=your-secret
```

### Huawei Cloud OBS

```bash
export OBS_BUCKET=my-bucket
export OBS_ENDPOINT=https://obs.region.myhuaweicloud.com
export OBS_ACCESS_KEY_ID=your-access-key
export OBS_SECRET_ACCESS_KEY=your-secret-key
```

### Tencent Cloud COS

```bash
export COS_BUCKET=my-bucket
export COS_REGION=ap-guangzhou
export COS_SECRET_ID=your-secret-id
export COS_SECRET_KEY=your-secret-key
```

### WebDAV

```bash
export WEBDAV_ENDPOINT=https://webdav.example.com
export WEBDAV_USERNAME=your-username
export WEBDAV_PASSWORD=your-password
```

### Local Filesystem

```bash
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



## Best Practices

1. **Configuration Method**: Use config files for base configuration, environment variables for secrets and environment-specific overrides.
2. **Security**: Never commit credentials to version control. Use environment variables or secret management tools.
3. **Naming**: Use descriptive `archive_name` values to easily identify backups.
4. **Destination Root**: Use the `root` field in each destination to organize backups by date or purpose (e.g., `backups/2025/01/`).
5. **Compression**: Choose compression based on your needs (see [Compression Guide](compression.md)).
6. **Validation**: Ensure destination paths exist and are writable. Simple Backup validates connectivity on startup by creating a test file (`.simple-backup-test`) in each destination. If validation fails, the backup will not proceed.

## Example Configurations

### Using Config File with Environment Variable Overrides

```toml
# config.toml - base configuration
source_path = "/data"
compression = "tar.zst"

[[destinations]]
service = "s3"
root = "backups/"

[destinations.storage]
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
apiVersion: v1
kind: ConfigMap
metadata:
  name: backup-config
data:
  config.yaml: |
    source_path: /data
    compression: tar.zst
    destinations:
      - service: s3
        root: backups/
        storage:
          bucket: my-backup-bucket
          region: us-east-1
---
apiVersion: v1
kind: Secret
metadata:
  name: s3-credentials
type: Opaque
stringData:
  access_key_id: AKIAxxxxx
  secret_access_key: xxxxx
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup-job
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: ghcr.io/reonokiy/simple-backup:latest
            volumeMounts:
              - name: config
                mountPath: /app/config.yaml
                subPath: config.yaml
            env:
              - name: S3_ACCESS_KEY_ID
                valueFrom:
                  secretKeyRef:
                    name: s3-credentials
                    key: access_key_id
              - name: S3_SECRET_ACCESS_KEY
                valueFrom:
                  secretKeyRef:
                    name: s3-credentials
                    key: secret_access_key
          volumes:
            - name: config
              configMap:
                name: backup-config
          restartPolicy: OnFailure
```
