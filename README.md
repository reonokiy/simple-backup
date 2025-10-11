# Simple Backup

[WIP] Vibe Coding

A simple backup program that reads from a filesystem folder/file and backs up to remote storage using OpenDAL.

## Features

- Read from filesystem using OpenDAL
- Write to any OpenDAL-supported remote storage service (S3, Azure Blob, GCS, OSS, OBS, COS, WebDAV, local filesystem, etc.)
- **Multiple destinations** - backup to multiple storage locations simultaneously
- **Startup validation** - tests destination connectivity before running backups
- Recursive directory traversal
- Preserves directory structure in backup destination
- Environment variable-based configuration
- Cron scheduling support for automated backups
- Progress logging

## Installation

```bash
uv sync

# For YAML config file support (optional)
uv sync --extra yaml
```

## Configuration

Simple Backup supports three configuration methods:

1. **Configuration files** (TOML or YAML) - Recommended for base configuration
2. **Environment variables** - For secrets and environment-specific overrides
3. **OPENDAL environment variables** - Standard OpenDAL variable names

See the [Configuration Guide](docs/configuration.md) for detailed information.

### Quick Start with Config File

```bash
# Using TOML (recommended)
cp config.example.toml config.toml

# Or using YAML
cp config.example.yaml config.yaml
```

### Quick Start with Config File (YAML)

```bash
# Copy and edit the example config
cp config.yaml.example config.yaml
# Edit config.yaml with your settings
python main.py
```

## Usage

### Basic Usage

```bash
# Using config file
python main.py

# Using environment variables
export BACKUP_SOURCE_PATH=/path/to/backup
export BACKUP_DEST_SERVICE=s3
# ... set other required variables
python main.py
```

### Scheduled Backups

Set `cron_schedule` in your config file or `BACKUP_CRON_SCHEDULE` environment variable:

```toml
# config.toml
cron_schedule = "0 2 * * *"  # Daily at 2 AM
```

Or:

```bash
export BACKUP_CRON_SCHEDULE="0 2 * * *"
python main.py
```

The program will run continuously and execute backups according to the schedule. Press Ctrl+C to stop.

### Multiple Destinations

You can backup to multiple destinations simultaneously. The archive is created once and uploaded to all destinations efficiently.

**Note**: On startup, Simple Backup validates connectivity to all configured destinations by creating and deleting a test file (`.simple-backup-test`). If any destination is unreachable, the backup will not proceed.

#### Config File (TOML)

```toml
# config.toml
source_path = "/home/user/documents"
compression = "tar.zst"

[[destinations]]
service = "s3"
root = "backups/"

[destinations.storage]
bucket = "my-primary-bucket"
region = "us-east-1"

[[destinations]]
service = "azblob"
root = "backups/"

[destinations.storage]
container = "my-backups"
account_name = "myaccount"
```

#### Config File (YAML)

```yaml
# config.yaml
source_path: /home/user/documents
compression: tar.zst

destinations:
  - service: s3
    root: backups/
    storage:
      bucket: my-primary-bucket
      region: us-east-1
  
  - service: azblob
    root: backups/
    storage:
      container: my-backups
      account_name: myaccount
```

### Configuration Priority

When multiple methods are used:
1. `OPENDAL_*` environment variables (highest priority)
2. Service-specific environment variables (`S3_*`, `AZURE_*`, etc.)
3. Configuration file values (lowest priority)

This allows you to keep non-sensitive config in files and override with environment variables for secrets.

### Configuration Options

See [Configuration Guide](docs/configuration.md) for full details. Key options:

- `source_path`: Path to backup (required)
- `destinations`: Array of destinations for backups (required)
- `compression`: Compression format (default: `tar.zst`)
  - Formats: `none`, `tar`, `tar.gz`, `tar.bz2`, `tar.xz`, `tar.zst`, `zip`, `gzip`
- `archive_name`: Custom archive name (optional)
- `cron_schedule`: Cron expression for scheduling (optional)

### Storage Services

Supported services: S3, Azure Blob, GCS, local filesystem, Alibaba OSS, Huawei OBS, Tencent COS, WebDAV

See [Configuration Guide](docs/configuration.md) for service-specific configuration details.

## Examples

### Basic Backup Configuration

```toml
# config.toml
source_path = "/home/user/documents"
compression = "tar.zst"
cron_schedule = "0 2 * * *"  # Daily at 2 AM

[retention]
daily = 7
weekly = 4
monthly = 6

[[destinations]]
service = "s3"
root = "backups/documents/"

[destinations.storage]
bucket = "my-backup-bucket"
region = "us-west-2"
# Credentials set via environment variables for security
```

```bash
export S3_ACCESS_KEY_ID=AKIAxxxxx
export S3_SECRET_ACCESS_KEY=xxxxx
python main.py
```

### Multiple Destinations

```toml
# config.toml
source_path = "/home/user/documents"
compression = "tar.zst"
cron_schedule = "0 2 * * *"

[retention]
daily = 7
weekly = 4
monthly = 6

[[destinations]]
service = "s3"
root = "backups/"

[destinations.storage]
bucket = "primary-backup-bucket"
region = "us-east-1"
access_key_id = "AKIAxxxxx"
secret_access_key = "xxxxx"

[[destinations]]
service = "s3"
root = "backups/"

[destinations.storage]
bucket = "secondary-backup-bucket"
region = "us-west-2"
access_key_id = "AKIAyyyyy"
secret_access_key = "yyyyy"
endpoint = "https://s3-compatible.example.com"

[[destinations]]
service = "azblob"
root = "backups/"

[destinations.storage]
container = "azure-backups"
account_name = "myaccount"
account_key = "xxxxx"
```

### Cron Schedule Examples

Common cron schedule patterns:
- `0 * * * *` - Every hour
- `0 2 * * *` - Daily at 2 AM
- `0 2 * * 0` - Weekly on Sunday at 2 AM
- `0 2 1 * *` - Monthly on the 1st at 2 AM
- `*/30 * * * *` - Every 30 minutes

## License

MIT
