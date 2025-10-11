# Simple Backup

A simple, flexible backup tool that supports multiple storage backends and Kubernetes deployments.

## Features

- Multiple storage backends (S3, Azure Blob, GCS, OSS, OBS, COS, WebDAV, etc.)
- Multiple backup destinations
- Compression and encryption support
- Cron scheduling with retention policies
- Docker and Kubernetes deployment
- Kubernetes Operator for automated backups

## Quick Start

```bash
# Install
uv sync

# Configure
cp config.example.toml config.toml
# Edit config.toml

# Run
python main.py
```

## Documentation

Full documentation: https://simple-backup.nokiy.net

- [Configuration](https://simple-backup.nokiy.net/configuration)
- [Docker Deployment](https://simple-backup.nokiy.net/docker)
- [Kubernetes Deployment](https://simple-backup.nokiy.net/kubernetes)
- [Compression](https://simple-backup.nokiy.net/compression)
- [Encryption](https://simple-backup.nokiy.net/encryption)
- [Scheduling](https://simple-backup.nokiy.net/scheduling)

## License

MIT
