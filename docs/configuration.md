# Configuration

Simple Backup supports configuration through:
1. **Configuration files** (TOML or YAML)
2. **Environment variables** (for overriding credentials)

## Configuration Priority

Storage configuration is read from the `storage` dictionary in each destination. Environment variables are **not** automatically used - they must be explicitly referenced in the configuration file or passed through the Kubernetes operator.

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

You can backup to multiple storage locations simultaneously:

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
  
  - service: s3
    root: backups/
    storage:
      bucket: my-secondary-bucket
      region: us-west-2
      access_key_id: AKIAyyyyy
      secret_access_key: yyyyy
  
  - service: azblob
    root: backups/
    storage:
      container: my-backups
      account_name: myaccount
      account_key: xxxxx
```

Or in TOML:

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

**Features**:
- Backup to multiple storage backends simultaneously
- Each destination has one storage configuration
- Each destination can use different credentials
- Retention policies apply to each destination independently
- Archive is created once and uploaded to all destinations (efficient)
- **Startup validation**: Connectivity to all storage backends is tested before backup runs

**Note**: Credentials should be stored in the `storage` section of each destination.

## Storage Service Configuration

Configure storage credentials directly in the `storage` section of each destination:

### Amazon S3

```yaml
destinations:
  - service: s3
    root: backups/
    storage:
      bucket: my-bucket
      region: us-east-1
      access_key_id: AKIAIOSFODNN7EXAMPLE
      secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
      endpoint: https://s3.amazonaws.com  # Optional
```

### Azure Blob Storage

```yaml
destinations:
  - service: azblob
    root: backups/
    storage:
      container: my-container
      account_name: myaccount
      account_key: your-account-key
```

### Google Cloud Storage

```yaml
destinations:
  - service: gcs
    root: backups/
    storage:
      bucket: my-bucket
      credential: /path/to/service-account.json
```

### Alibaba Cloud OSS

```yaml
destinations:
  - service: oss
    root: backups/
    storage:
      bucket: my-bucket
      endpoint: https://oss-cn-hangzhou.aliyuncs.com
      access_key_id: your-access-key
      access_key_secret: your-secret
```

### Huawei Cloud OBS

```yaml
destinations:
  - service: obs
    root: backups/
    storage:
      bucket: my-bucket
      endpoint: https://obs.region.myhuaweicloud.com
      access_key_id: your-access-key
      secret_access_key: your-secret-key
```

### Tencent Cloud COS

```yaml
destinations:
  - service: cos
    root: backups/
    storage:
      bucket: my-bucket
      region: ap-guangzhou
      secret_id: your-secret-id
      secret_key: your-secret-key
```

### WebDAV

```yaml
destinations:
  - service: webdav
    root: backups/
    storage:
      endpoint: https://webdav.example.com
      username: your-username
      password: your-password
```

### Local Filesystem

```yaml
destinations:
  - service: fs
    root: /path/to/backup/destination
    storage:
      root: /path/to/backup/destination
```



## Best Practices

1. **Configuration Method**: Use config files for base configuration and structure.
2. **Security**: Never commit credentials to version control. Use Kubernetes Secrets or other secret management tools to inject credentials into the `storage` section.
3. **Naming**: Use descriptive `archive_name` values to easily identify backups.
4. **Destination Root**: Use the `root` field in each destination to organize backups by date or purpose (e.g., `backups/2025/01/`).
5. **Compression**: Choose compression based on your needs (see [Compression Guide](compression.md)).
6. **Validation**: Ensure destination paths exist and are writable. Simple Backup validates connectivity on startup by creating a test file (`.simple-backup-test`) in each destination. If validation fails, the backup will not proceed.

## Example Configurations

### Basic Configuration with Credentials

```toml
# config.toml
source_path = "/data"
compression = "tar.zst"

[[destinations]]
service = "s3"
root = "backups/"

[destinations.storage]
bucket = "my-backup-bucket"
region = "us-east-1"
access_key_id = "AKIAxxxxx"
secret_access_key = "xxxxx"
```

### Using Kubernetes Secrets

When using the Kubernetes operator, credentials are automatically injected from the BackupJob CR:

```yaml
apiVersion: backup.reonokiy.com/v1
kind: BackupJob
metadata:
  name: my-backup
spec:
  source:
    pvcName: my-data
    subPath: /data
  
  destination:
    service: s3
    bucket: my-backup-bucket
    region: us-east-1
    accessKeyId: AKIAIOSFODNN7EXAMPLE
    secretAccessKey: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
  
  schedule: "0 2 * * *"
  compression: tar.zst
```

The operator automatically converts these fields to the appropriate storage configuration for the backup container.

