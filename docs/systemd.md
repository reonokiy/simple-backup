# Systemd Deployment

This guide covers running simple-backup as a systemd service on Linux systems.

## Prerequisites

- Python 3.11 or higher
- systemd-enabled Linux distribution
- `uv` package manager (recommended) or `pip`

## Installation

### 1. Install uv (Recommended)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone the Repository

```bash
git clone https://github.com/reonokiy/simple-backup.git
cd simple-backup
```

### 3. Install Dependencies

**Using uv:**
```bash
uv sync
```

**Using pip:**
```bash
pip install -r requirements.txt
```

### 4. Create Environment File

Create `/etc/simple-backup/backup.env` with your configuration:

```bash
sudo mkdir -p /etc/simple-backup
sudo nano /etc/simple-backup/backup.env
```

```bash
BACKUP_SOURCE_PATH=/data
BACKUP_DEST_SERVICE=s3
BACKUP_COMPRESSION=tar.zst

S3_BUCKET=my-backup-bucket
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key

BACKUP_RETENTION_DAILY=7
BACKUP_RETENTION_WEEKLY=4
BACKUP_RETENTION_MONTHLY=6
```

Secure the environment file:
```bash
sudo chmod 600 /etc/simple-backup/backup.env
```

## Deployment Methods

### Recommended: One-Shot Service with Systemd Timer

This method runs backups on a schedule using systemd timers instead of a long-running process.

#### Create the Service File

`/etc/systemd/system/simple-backup.service`:

```ini
[Unit]
Description=Simple Backup Service
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/simple-backup/backup.env
ExecStart=/home/user/simple-backup/.venv/bin/python /home/user/simple-backup/main.py
User=backup
Group=backup
WorkingDirectory=/home/user/simple-backup

StandardOutput=journal
StandardError=journal
SyslogIdentifier=simple-backup

[Install]
WantedBy=multi-user.target
```

#### Create the Timer File

`/etc/systemd/system/simple-backup.timer`:

```ini
[Unit]
Description=Simple Backup Timer
Requires=simple-backup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

#### Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable simple-backup.timer
sudo systemctl start simple-backup.timer
```

#### Check Status

```bash
sudo systemctl status simple-backup.timer
sudo systemctl list-timers simple-backup.timer
```

#### View Logs

```bash
journalctl -u simple-backup.service -f
journalctl -u simple-backup.service --since "1 hour ago"
```

## User Setup

Create a dedicated user for running backups:

```bash
sudo useradd -r -s /bin/false -d /home/backup -m backup
sudo chown -R backup:backup /home/user/simple-backup
```

If backing up system files, grant read permissions:

```bash
sudo usermod -aG adm backup
```

Or configure sudo access for specific directories:

```bash
sudo visudo -f /etc/sudoers.d/simple-backup
```

```
backup ALL=(ALL) NOPASSWD: /usr/bin/tar -czf * /var/lib/postgresql/*
```

## Storage Configuration Examples

### Local Filesystem

```bash
BACKUP_DEST_SERVICE=fs
FS_ROOT=/mnt/backups
```

Ensure the backup user has write access:
```bash
sudo mkdir -p /mnt/backups
sudo chown backup:backup /mnt/backups
```

### AWS S3

```bash
BACKUP_DEST_SERVICE=s3
S3_BUCKET=my-backups
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
S3_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### Azure Blob Storage

```bash
BACKUP_DEST_SERVICE=azblob
AZURE_CONTAINER=backups
AZURE_ACCOUNT_NAME=myaccount
AZURE_ACCOUNT_KEY=mykey
```

### Google Cloud Storage

```bash
BACKUP_DEST_SERVICE=gcs
GCS_BUCKET=my-backups
GCS_CREDENTIAL=/etc/simple-backup/gcs-credentials.json
```

### WebDAV

```bash
BACKUP_DEST_SERVICE=webdav
WEBDAV_ENDPOINT=https://webdav.example.com
WEBDAV_USERNAME=myuser
WEBDAV_PASSWORD=mypass
```

## Multiple Backup Jobs

Create multiple timer/service pairs with different configurations.

### Create Instance-Specific Environment Files

`/etc/simple-backup/database.env`:
```bash
BACKUP_SOURCE_PATH=/var/lib/postgresql
BACKUP_DEST_SERVICE=s3
S3_BUCKET=database-backups
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
BACKUP_RETENTION_DAILY=7
```

`/etc/simple-backup/uploads.env`:
```bash
BACKUP_SOURCE_PATH=/var/www/uploads
BACKUP_DEST_SERVICE=s3
S3_BUCKET=uploads-backups
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
BACKUP_RETENTION_WEEKLY=8
```

### Create Templated Service and Timer

`/etc/systemd/system/simple-backup@.service`:

```ini
[Unit]
Description=Simple Backup Service (%i)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/simple-backup/%i.env
ExecStart=/home/user/simple-backup/.venv/bin/python /home/user/simple-backup/main.py
User=backup
Group=backup
WorkingDirectory=/home/user/simple-backup

StandardOutput=journal
StandardError=journal
SyslogIdentifier=simple-backup-%i

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/simple-backup@.timer`:

```ini
[Unit]
Description=Simple Backup Timer (%i)
Requires=simple-backup@%i.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

### Enable Multiple Instances

```bash
sudo systemctl daemon-reload
sudo systemctl enable simple-backup@database.timer
sudo systemctl enable simple-backup@uploads.timer
sudo systemctl start simple-backup@database.timer
sudo systemctl start simple-backup@uploads.timer
```

### View Status

```bash
systemctl list-timers simple-backup@*
systemctl status simple-backup@*
journalctl -u simple-backup@database.service -f
journalctl -u simple-backup@uploads.service -f
```

## Timer Schedule Examples

Customize the schedule by editing the `OnCalendar` directive in the timer file.

**Daily at 2 AM:**
```ini
[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
```

**Every 6 hours:**
```ini
[Timer]
OnCalendar=*-*-* 00/6:00:00
Persistent=true
```

**Weekly on Sunday at 3 AM:**
```ini
[Timer]
OnCalendar=Sun *-*-* 03:00:00
Persistent=true
```

**Monthly on the 1st at 4 AM:**
```ini
[Timer]
OnCalendar=*-*-01 04:00:00
Persistent=true
```

**Multiple schedules (daily at 2 AM + weekly Sunday at 3 AM):**
```ini
[Timer]
OnCalendar=*-*-* 02:00:00
OnCalendar=Sun *-*-* 03:00:00
Persistent=true
```

**Using shorthand (equivalent to daily):**
```ini
[Timer]
OnCalendar=daily
Persistent=true
```

Available shorthands: `minutely`, `hourly`, `daily`, `weekly`, `monthly`, `yearly`

Test timer syntax:
```bash
systemd-analyze calendar "Mon *-*-* 03:00:00"
systemd-analyze calendar "daily"
```

## Monitoring and Maintenance

### Check Service Health

```bash
systemctl is-active simple-backup.service
systemctl is-enabled simple-backup.service
systemctl is-failed simple-backup.service
```

### Manual Backup Trigger

```bash
sudo systemctl start simple-backup.service
```

### Log Rotation

Configure journald to rotate logs:

`/etc/systemd/journald.conf`:
```ini
[Journal]
SystemMaxUse=1G
SystemMaxFileSize=100M
SystemMaxFiles=10
```

Restart journald:
```bash
sudo systemctl restart systemd-journald
```

### Resource Limits

Add resource limits to service file:

```ini
[Service]
MemoryMax=512M
CPUQuota=50%
IOWeight=100
```

## Troubleshooting

### Service Fails to Start

Check service status and logs:
```bash
sudo systemctl status simple-backup.service
journalctl -u simple-backup.service -n 50
```

### Permission Errors

Ensure backup user has read access to source:
```bash
sudo -u backup ls -la /path/to/source
```

### Environment Variables Not Loading

Verify environment file syntax:
```bash
cat /etc/simple-backup/backup.env
```

Reload systemd after changes:
```bash
sudo systemctl daemon-reload
sudo systemctl restart simple-backup.service
```

### Timer Not Triggering

Check timer status:
```bash
systemctl status simple-backup.timer
journalctl -u simple-backup.timer
systemctl list-timers --all
```

## Security Best Practices

1. **Secure environment files:**
   ```bash
   sudo chmod 600 /etc/simple-backup/*.env
   sudo chown root:root /etc/simple-backup/*.env
   ```

2. **Use dedicated user** with minimal privileges

3. **Store credentials securely** - consider using systemd credentials:
   ```bash
   sudo systemd-creds encrypt --name=s3_secret_key - /etc/credstore/s3_secret_key.cred
   ```

   In service file:
   ```ini
   LoadCredential=s3_secret_key:/etc/credstore/s3_secret_key.cred
   ```

4. **Enable SELinux/AppArmor** for additional isolation

5. **Regular security updates:**
   ```bash
   cd /home/user/simple-backup
   git pull
   uv sync
   sudo systemctl restart simple-backup.service
   ```

6. **Monitor logs** for suspicious activity
   ```bash
   journalctl -u simple-backup.service --since today | grep ERROR
   ```
