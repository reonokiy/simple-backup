# Simple Backup

[WIP] Vibe Coding

A simple backup program that reads from a filesystem folder/file and backs up to remote storage using OpenDAL.

## Features

- Read from filesystem using OpenDAL
- Write to any OpenDAL-supported remote storage service (S3, Azure Blob, GCS, OSS, OBS, COS, WebDAV, local filesystem, etc.)
- Recursive directory traversal
- Preserves directory structure in backup destination
- Environment variable-based configuration
- Cron scheduling support for automated backups
- Progress logging

## Installation

```bash
uv sync
```

## Usage

### One-Time Backup

Set environment variables and run:

```bash
python main.py
```

### Scheduled Backup with Cron

Set the `BACKUP_CRON_SCHEDULE` environment variable with a cron expression to run backups on a schedule:

```bash
export BACKUP_CRON_SCHEDULE="0 2 * * *"  # Run daily at 2 AM
python main.py
```

The program will run continuously and execute backups according to the cron schedule. Press Ctrl+C to stop.

### Required Environment Variables

- `BACKUP_SOURCE_PATH`: Path to the folder/file to backup
- `BACKUP_DEST_SERVICE`: Destination service type (s3, azblob, gcs, fs, oss, obs, cos, webdav)
- `BACKUP_DEST_ROOT`: Root path in destination storage (optional)
- `BACKUP_CRON_SCHEDULE`: Cron expression for scheduled backups (optional, if not set runs once)
- `BACKUP_COMPRESSION`: Compression format (optional, default: `tar.zst`)
  - Supported formats: `none`, `tar`, `tar.gz`, `tar.bz2`, `tar.xz`, `tar.zst`, `zip`, `gzip`
  - `tar.zst` (Zstandard) is recommended for best compression ratio and speed
  - `none` backs up files individually without archiving
- `BACKUP_ARCHIVE_NAME`: Custom archive name (optional, default: `backup_{dirname}_{timestamp}`)

### Service-Specific Environment Variables

#### S3
```bash
export BACKUP_SOURCE_PATH=/path/to/backup
export BACKUP_DEST_SERVICE=s3
export BACKUP_DEST_ROOT=backups/
export S3_BUCKET=my-bucket
export S3_REGION=us-east-1
export S3_ACCESS_KEY_ID=your-access-key
export S3_SECRET_ACCESS_KEY=your-secret-key
export S3_ENDPOINT=https://s3.amazonaws.com  # optional
```

#### Azure Blob Storage
```bash
export BACKUP_SOURCE_PATH=/path/to/backup
export BACKUP_DEST_SERVICE=azblob
export BACKUP_DEST_ROOT=backups/
export AZURE_CONTAINER=my-container
export AZURE_ACCOUNT_NAME=your-account
export AZURE_ACCOUNT_KEY=your-key
```

#### Google Cloud Storage
```bash
export BACKUP_SOURCE_PATH=/path/to/backup
export BACKUP_DEST_SERVICE=gcs
export BACKUP_DEST_ROOT=backups/
export GCS_BUCKET=my-bucket
export GCS_CREDENTIAL=/path/to/service-account.json
```

#### Local Filesystem
```bash
export BACKUP_SOURCE_PATH=/path/to/backup
export BACKUP_DEST_SERVICE=fs
export BACKUP_DEST_ROOT=backups/
export FS_ROOT=/path/to/destination
```

#### Alibaba Cloud OSS
```bash
export BACKUP_SOURCE_PATH=/path/to/backup
export BACKUP_DEST_SERVICE=oss
export BACKUP_DEST_ROOT=backups/
export OSS_BUCKET=my-bucket
export OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
export OSS_ACCESS_KEY_ID=your-access-key
export OSS_ACCESS_KEY_SECRET=your-secret
```

#### Huawei Cloud OBS
```bash
export BACKUP_SOURCE_PATH=/path/to/backup
export BACKUP_DEST_SERVICE=obs
export BACKUP_DEST_ROOT=backups/
export OBS_BUCKET=my-bucket
export OBS_ENDPOINT=https://obs.region.myhuaweicloud.com
export OBS_ACCESS_KEY_ID=your-access-key
export OBS_SECRET_ACCESS_KEY=your-secret-key
```

#### Tencent Cloud COS
```bash
export BACKUP_SOURCE_PATH=/path/to/backup
export BACKUP_DEST_SERVICE=cos
export BACKUP_DEST_ROOT=backups/
export COS_BUCKET=my-bucket
export COS_REGION=ap-guangzhou
export COS_SECRET_ID=your-secret-id
export COS_SECRET_KEY=your-secret-key
```

#### WebDAV
```bash
export BACKUP_SOURCE_PATH=/path/to/backup
export BACKUP_DEST_SERVICE=webdav
export BACKUP_DEST_ROOT=backups/
export WEBDAV_ENDPOINT=https://webdav.example.com
export WEBDAV_USERNAME=your-username
export WEBDAV_PASSWORD=your-password
```

## Example

### One-Time Backup (with compression)

```bash
export BACKUP_SOURCE_PATH=/home/user/documents
export BACKUP_DEST_SERVICE=s3
export BACKUP_DEST_ROOT=backups/documents/
export BACKUP_COMPRESSION=tar.zst  # Default, uses Zstandard compression
export S3_BUCKET=my-backup-bucket
export S3_REGION=us-west-2
export S3_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export S3_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

python main.py
```

### One-Time Backup (without compression)

```bash
export BACKUP_SOURCE_PATH=/home/user/documents
export BACKUP_DEST_SERVICE=s3
export BACKUP_DEST_ROOT=backups/documents/
export BACKUP_COMPRESSION=none  # Backup individual files
export S3_BUCKET=my-backup-bucket
export S3_REGION=us-west-2
export S3_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export S3_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

python main.py
```

### Scheduled Backup

```bash
export BACKUP_SOURCE_PATH=/home/user/documents
export BACKUP_DEST_SERVICE=s3
export BACKUP_DEST_ROOT=backups/documents/
export BACKUP_CRON_SCHEDULE="0 2 * * *"  # Daily at 2 AM
export S3_BUCKET=my-backup-bucket
export S3_REGION=us-west-2
export S3_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export S3_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

python main.py
```

Common cron schedule examples:
- `0 * * * *` - Every hour
- `0 2 * * *` - Daily at 2 AM
- `0 2 * * 0` - Weekly on Sunday at 2 AM
- `0 2 1 * *` - Monthly on the 1st at 2 AM
- `*/30 * * * *` - Every 30 minutes

## License

MIT
