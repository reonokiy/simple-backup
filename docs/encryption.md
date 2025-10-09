# Encryption

simple-backup supports encrypting backup archives using [age](https://age-encryption.org/), a modern and secure file encryption tool.

## Overview

When encryption is enabled, backup archives are encrypted using the age encryption format before being uploaded to the destination storage. Encrypted files have a `.age` extension appended (e.g., `backup_data_20241009_120000.tar.zst.age`).

## Key Features

- **Modern encryption**: Uses age (Actually Good Encryption) with X25519 keys
- **Simple key management**: Uses public/private key pairs
- **Transparent workflow**: Archives are automatically encrypted after compression
- **Secure**: Encryption happens before upload to remote storage

## Generating Encryption Keys

Generate an age key pair using the `age-keygen` command:

```bash
age-keygen -o key.txt
```

This will output:
```
# created: 2024-10-09T12:00:00Z
# public key: age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
AGE-SECRET-KEY-1XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

- **Public key** (`age1...`): Used for encryption - safe to share and store in configuration
- **Secret key** (`AGE-SECRET-KEY-1...`): Used for decryption - must be kept secure

## Configuration

### Environment Variables

Add the following environment variables to enable encryption:

```bash
# Enable encryption
BACKUP_ENCRYPTION_ENABLED=true

# Public key for encryption (required when encryption is enabled)
BACKUP_ENCRYPTION_RECIPIENT=age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq

# Private key path for decryption (optional, only needed for restore)
BACKUP_ENCRYPTION_IDENTITY=/path/to/key.txt
```

### Example Configuration

```bash
BACKUP_SOURCE_PATH=/data
BACKUP_DEST_SERVICE=s3
BACKUP_DEST_ROOT=/backups
BACKUP_COMPRESSION=tar.zst
BACKUP_ENCRYPTION_ENABLED=true
BACKUP_ENCRYPTION_RECIPIENT=age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq

S3_BUCKET=my-encrypted-backups
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
```

## Usage

### Creating Encrypted Backups

Once configured, backups are automatically encrypted:

```bash
# Run backup (archives will be encrypted automatically)
python main.py
```

The workflow:
1. Source files are compressed into an archive (e.g., `backup.tar.zst`)
2. Archive is encrypted with the recipient public key (e.g., `backup.tar.zst.age`)
3. Encrypted archive is uploaded to destination storage
4. Original unencrypted archive is deleted from temp storage

### Decrypting Backups

To decrypt a backup archive:

```bash
# Download encrypted backup from storage
aws s3 cp s3://my-bucket/backup_data_20241009_120000.tar.zst.age .

# Decrypt using age with your private key
age --decrypt -i key.txt -o backup_data_20241009_120000.tar.zst backup_data_20241009_120000.tar.zst.age

# Extract the archive
tar -I zstd -xf backup_data_20241009_120000.tar.zst
```

## Docker Deployment

### Using Environment Variables

```bash
docker run -d \
  -e BACKUP_SOURCE_PATH=/data \
  -e BACKUP_DEST_SERVICE=s3 \
  -e BACKUP_COMPRESSION=tar.zst \
  -e BACKUP_ENCRYPTION_ENABLED=true \
  -e BACKUP_ENCRYPTION_RECIPIENT=age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq \
  -e S3_BUCKET=my-bucket \
  -e S3_ACCESS_KEY_ID=your-key \
  -e S3_SECRET_ACCESS_KEY=your-secret \
  -v /path/to/data:/data:ro \
  simple-backup
```

### Using Docker Compose

```yaml
version: '3.8'

services:
  backup:
    image: simple-backup
    environment:
      BACKUP_SOURCE_PATH: /data
      BACKUP_DEST_SERVICE: s3
      BACKUP_COMPRESSION: tar.zst
      BACKUP_ENCRYPTION_ENABLED: "true"
      BACKUP_ENCRYPTION_RECIPIENT: age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
      BACKUP_CRON_SCHEDULE: "0 2 * * *"
      S3_BUCKET: my-encrypted-backups
      S3_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      S3_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
    volumes:
      - /path/to/data:/data:ro
```

## Kubernetes Deployment

### Using Secrets

Store the encryption recipient in a Kubernetes Secret:

```bash
kubectl create secret generic backup-encryption \
  --from-literal=recipient=age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
```

### CronJob Example

```yaml
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
            image: simple-backup:latest
            env:
            - name: BACKUP_SOURCE_PATH
              value: "/data"
            - name: BACKUP_DEST_SERVICE
              value: "s3"
            - name: BACKUP_COMPRESSION
              value: "tar.zst"
            - name: BACKUP_ENCRYPTION_ENABLED
              value: "true"
            - name: BACKUP_ENCRYPTION_RECIPIENT
              valueFrom:
                secretKeyRef:
                  name: backup-encryption
                  key: recipient
            - name: S3_BUCKET
              value: "my-encrypted-backups"
            - name: S3_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: s3-credentials
                  key: access-key-id
            - name: S3_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: s3-credentials
                  key: secret-access-key
            volumeMounts:
            - name: data
              mountPath: /data
              readOnly: true
          volumes:
          - name: data
            persistentVolumeClaim:
              claimName: app-data
          restartPolicy: OnFailure
```

### Using the Operator

```yaml
apiVersion: backup.simple-backup.io/v1alpha1
kind: BackupJob
metadata:
  name: encrypted-database-backup
  namespace: production
spec:
  schedule: "0 2 * * *"
  sourcePath: /var/lib/postgresql/data
  compression: tar.zst
  encryption:
    enabled: true
    recipientSecretRef:
      name: backup-encryption
      key: recipient
  destination:
    service: s3
    root: /database-backups
    s3:
      bucket: my-encrypted-backups
      region: us-east-1
      credentialsSecretRef:
        name: s3-credentials
  retention:
    daily: 7
    weekly: 4
    monthly: 6
    yearly: 2
```

## Security Best Practices

### Key Management

1. **Generate strong keys**: Always use `age-keygen` to generate keys
2. **Protect private keys**: Never commit private keys to version control
3. **Use secrets management**: Store keys in Kubernetes Secrets, AWS Secrets Manager, etc.
4. **Rotate keys**: Periodically generate new key pairs and re-encrypt backups
5. **Backup private keys**: Store private keys securely offline for disaster recovery

### Storage Security

1. **Encrypt at rest**: Use encrypted storage backends (S3 SSE, Azure encryption, etc.)
2. **Limit access**: Use IAM policies to restrict access to encrypted backups
3. **Monitor access**: Enable audit logging on storage backends
4. **Test recovery**: Regularly test decryption and restore procedures

### Compliance

- Encrypted backups can help meet compliance requirements (GDPR, HIPAA, PCI-DSS)
- Encryption happens client-side before data leaves your infrastructure
- No encryption keys are ever sent to storage providers

## Troubleshooting

### Encryption fails with "recipient required"

Ensure `BACKUP_ENCRYPTION_RECIPIENT` is set when `BACKUP_ENCRYPTION_ENABLED=true`:

```bash
export BACKUP_ENCRYPTION_ENABLED=true
export BACKUP_ENCRYPTION_RECIPIENT=age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq
```

### Cannot decrypt backup

Verify you're using the correct private key:

```bash
# Check key fingerprint
grep "public key:" key.txt

# Try decrypting
age --decrypt -i key.txt backup.tar.zst.age
```

### Performance impact

Encryption adds minimal overhead:
- CPU: ~5-10% increase for encryption
- Time: Typically <1 second per GB on modern hardware
- Storage: Encrypted files are slightly larger (~1-2% overhead)

## Compatibility

- **age version**: Compatible with age v1.0.0 and later
- **Python library**: Uses `pyrage` for encryption
- **File format**: Standard age encryption format (compatible with age CLI tools)

## Further Reading

- [age encryption specification](https://age-encryption.org/)
- [age GitHub repository](https://github.com/FiloSottile/age)
- [pyrage documentation](https://github.com/woodruffw/pyrage)
