# Kubernetes Deployment

This guide covers deploying simple-backup on Kubernetes using two methods: direct CronJob deployment and the Helm chart with Kubernetes Operator.

## Table of Contents

- [Method 1: CronJob Deployment](#method-1-cronjob-deployment)
- [Method 2: Helm Chart with Operator (Recommended)](#method-2-helm-chart-with-operator-recommended)
- [Storage Configuration](#storage-configuration)
- [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)

---

## Method 1: CronJob Deployment

Direct Kubernetes CronJob deployment for simple backup schedules.

### Prerequisites

- Docker image built and pushed to a registry
- PersistentVolumeClaim for data to backup
- Storage credentials

### Quick Start

1. **Build and push the Docker image:**
   ```bash
   docker build -t your-registry/simple-backup:latest .
   docker push your-registry/simple-backup:latest
   ```

2. **Create a secret for storage credentials:**
   ```bash
   kubectl create secret generic simple-backup-secrets \
     --from-literal=S3_ACCESS_KEY_ID=your-key \
     --from-literal=S3_SECRET_ACCESS_KEY=your-secret
   ```

3. **Create ConfigMap for backup configuration:**
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: simple-backup-config
   data:
     BACKUP_SOURCE_PATH: "/data"
     BACKUP_DEST_SERVICE: "s3"
     BACKUP_DEST_ROOT: "backups"
     BACKUP_COMPRESSION: "tar.zst"
     BACKUP_RETENTION_DAILY: "7"
     BACKUP_RETENTION_WEEKLY: "4"
     BACKUP_RETENTION_MONTHLY: "6"
     S3_BUCKET: "my-backup-bucket"
     S3_REGION: "us-east-1"
   ```

4. **Create CronJob:**
   ```yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: simple-backup
   spec:
     schedule: "0 2 * * *"  # Daily at 2 AM
     concurrencyPolicy: Forbid
     successfulJobsHistoryLimit: 3
     failedJobsHistoryLimit: 3
     jobTemplate:
       spec:
         backoffLimit: 2
         template:
           spec:
             restartPolicy: OnFailure
             containers:
             - name: backup
               image: your-registry/simple-backup:latest
               envFrom:
               - configMapRef:
                   name: simple-backup-config
               - secretRef:
                   name: simple-backup-secrets
               volumeMounts:
               - name: data
                 mountPath: /data
                 readOnly: true
               resources:
                 limits:
                   cpu: 500m
                   memory: 512Mi
                 requests:
                   cpu: 250m
                   memory: 256Mi
             volumes:
             - name: data
               persistentVolumeClaim:
                 claimName: data-to-backup
   ```

5. **Apply the manifests:**
   ```bash
   kubectl apply -f configmap.yaml
   kubectl apply -f cronjob.yaml
   ```

### Verify Deployment

```bash
# Check CronJob
kubectl get cronjobs

# View job history
kubectl get jobs

# View logs from latest job
kubectl logs -l job-name=simple-backup-28123456
```

---

## Method 2: Helm Chart with Operator (Recommended)

The Kubernetes Operator provides a declarative way to manage backups using Custom Resource Definitions (CRDs).

### Installation

**Option A: Install Operator via Helm**

1. **Build and push operator image:**
   ```bash
   cd helm/simple-backup-operator/operator
   docker build -t your-registry/simple-backup-operator:latest .
   docker push your-registry/simple-backup-operator:latest
   ```

2. **Install the operator:**
   ```bash
   helm install simple-backup-operator ./helm/simple-backup-operator \
     --create-namespace \
     --namespace simple-backup-system \
     --set image.repository=your-registry/simple-backup-operator \
     --set image.tag=latest
   ```

3. **Verify installation:**
   ```bash
   kubectl get pods -n simple-backup-system
   kubectl get crd backupjobs.backup.simple-backup.io
   ```

**Option B: Install from Values File**

Create `operator-values.yaml`:
```yaml
image:
  repository: your-registry/simple-backup-operator
  tag: "latest"
  pullPolicy: IfNotPresent

replicaCount: 1

resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi

watchNamespace: ""  # Watch all namespaces

operator:
  logLevel: INFO
```

Install:
```bash
helm install simple-backup-operator ./helm/simple-backup-operator \
  -f operator-values.yaml \
  --create-namespace \
  --namespace simple-backup-system
```

### Creating BackupJobs

1. **Build and push backup image:**
   ```bash
   docker build -t your-registry/simple-backup:latest .
   docker push your-registry/simple-backup:latest
   ```

2. **Create storage credentials secret:**
   ```bash
   kubectl create secret generic s3-credentials \
     --from-literal=S3_BUCKET=my-backup-bucket \
     --from-literal=S3_REGION=us-east-1 \
     --from-literal=S3_ACCESS_KEY_ID=your-key \
     --from-literal=S3_SECRET_ACCESS_KEY=your-secret
   ```

3. **Create a BackupJob resource:**
   ```yaml
   apiVersion: backup.simple-backup.io/v1alpha1
   kind: BackupJob
   metadata:
     name: postgres-backup
     namespace: default
   spec:
     source:
       path: /var/lib/postgresql/data
       pvcName: postgres-data
     
     destination:
       service: s3
       root: backups/postgres
       secretRef: s3-credentials
     
     compression: tar.zst
     schedule: "0 2 * * *"
     
     retention:
       daily: 7
       weekly: 4
       monthly: 6
       yearly: 2
     
     resources:
       limits:
         cpu: "1"
         memory: "1Gi"
       requests:
         cpu: "500m"
         memory: "512Mi"
   ```

4. **Apply the BackupJob:**
   ```bash
   kubectl apply -f backupjob.yaml
   ```

### Managing BackupJobs

```bash
# List all backup jobs
kubectl get backupjobs
kubectl get bj  # Short name

# Get detailed info
kubectl describe backupjob postgres-backup

# Check status
kubectl get backupjob postgres-backup -o yaml

# View generated CronJob
kubectl get cronjobs

# View job history
kubectl get jobs

# View logs
kubectl logs -l backupjob=postgres-backup

# Suspend backup
kubectl patch backupjob postgres-backup -p '{"spec":{"suspend":true}}'

# Resume backup
kubectl patch backupjob postgres-backup -p '{"spec":{"suspend":false}}'

# Delete backup job (also deletes generated CronJob)
kubectl delete backupjob postgres-backup
```

### Multiple Backup Jobs Example

```yaml
---
apiVersion: backup.simple-backup.io/v1alpha1
kind: BackupJob
metadata:
  name: database-backup
spec:
  source:
    path: /data/postgres
    pvcName: postgres-data
  destination:
    service: s3
    root: backups/database
    secretRef: s3-credentials
  schedule: "0 2 * * *"
  compression: tar.zst
  retention:
    daily: 7
    weekly: 4

---
apiVersion: backup.simple-backup.io/v1alpha1
kind: BackupJob
metadata:
  name: uploads-backup
spec:
  source:
    path: /app/uploads
    pvcName: uploads-data
  destination:
    service: s3
    root: backups/uploads
    secretRef: s3-credentials
  schedule: "0 3 * * *"
  compression: tar.gz
  retention:
    weekly: 8
    monthly: 12
```

### Encrypted Backups

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: age-encryption
stringData:
  recipient: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
---
apiVersion: backup.simple-backup.io/v1alpha1
kind: BackupJob
metadata:
  name: encrypted-backup
spec:
  source:
    path: /data/sensitive
    pvcName: sensitive-data
  destination:
    service: s3
    root: backups/encrypted
    secretRef: s3-credentials
  encryption:
    enabled: true
    recipientSecretRef:
      name: age-encryption
      key: recipient
  compression: tar.zst
  schedule: "0 2 * * *"
```

---

## Storage Configuration

### AWS S3

```bash
kubectl create secret generic s3-credentials \
  --from-literal=S3_BUCKET=my-bucket \
  --from-literal=S3_REGION=us-east-1 \
  --from-literal=S3_ACCESS_KEY_ID=YOUR_KEY \
  --from-literal=S3_SECRET_ACCESS_KEY=YOUR_SECRET
```

BackupJob:
```yaml
destination:
  service: s3
  root: backups/myapp
  secretRef: s3-credentials
```

### Azure Blob Storage

```bash
kubectl create secret generic azure-credentials \
  --from-literal=AZURE_CONTAINER=my-container \
  --from-literal=AZURE_ACCOUNT_NAME=myaccount \
  --from-literal=AZURE_ACCOUNT_KEY=YOUR_KEY
```

BackupJob:
```yaml
destination:
  service: azblob
  secretRef: azure-credentials
```

### Google Cloud Storage

```bash
kubectl create secret generic gcs-credentials \
  --from-literal=GCS_BUCKET=my-bucket \
  --from-file=GCS_CREDENTIAL=./service-account.json
```

BackupJob:
```yaml
destination:
  service: gcs
  secretRef: gcs-credentials
```

### WebDAV

```bash
kubectl create secret generic webdav-credentials \
  --from-literal=WEBDAV_ENDPOINT=https://webdav.example.com \
  --from-literal=WEBDAV_USERNAME=user \
  --from-literal=WEBDAV_PASSWORD=pass
```

BackupJob:
```yaml
destination:
  service: webdav
  secretRef: webdav-credentials
```

---

## Monitoring and Troubleshooting

### View Operator Logs

```bash
kubectl logs -n simple-backup-system -l app.kubernetes.io/name=simple-backup-operator -f
```

### View Backup Job Logs

```bash
# Get recent jobs
kubectl get jobs --sort-by=.metadata.creationTimestamp

# View logs from specific job
kubectl logs job/postgres-backup-cronjob-28123456

# View logs by label
kubectl logs -l backupjob=postgres-backup
```

### Common Issues

**BackupJob created but no CronJob appears:**
```bash
# Check operator logs
kubectl logs -n simple-backup-system -l app.kubernetes.io/name=simple-backup-operator

# Check RBAC permissions
kubectl auth can-i create cronjobs --as=system:serviceaccount:simple-backup-system:simple-backup-operator
```

**Image pull errors:**
```bash
# Create image pull secret
kubectl create secret docker-registry regcred \
  --docker-server=your-registry.com \
  --docker-username=your-user \
  --docker-password=your-pass

# Add to operator values
imagePullSecrets:
  - name: regcred
```

**Permission errors in backup pod:**
```bash
# Check PVC exists
kubectl get pvc postgres-data

# Check secret exists
kubectl get secret s3-credentials

# Describe pod for details
kubectl describe pod -l backupjob=postgres-backup
```

---

## Uninstallation

### CronJob Method

```bash
kubectl delete cronjob simple-backup
kubectl delete configmap simple-backup-config
kubectl delete secret simple-backup-secrets
```

### Operator Method

```bash
# Delete all BackupJobs (this also deletes generated CronJobs)
kubectl delete backupjobs --all

# Uninstall operator
helm uninstall simple-backup-operator -n simple-backup-system

# Delete CRD (optional - removes BackupJob resource type)
kubectl delete crd backupjobs.backup.simple-backup.io

# Delete namespace
kubectl delete namespace simple-backup-system
```

---

## Security Best Practices

1. **Use RBAC to limit access to BackupJob resources**
2. **Store credentials in Kubernetes Secrets, never in ConfigMaps**
3. **Use read-only volumes for source data**
4. **Regularly rotate storage credentials**
5. **Enable age encryption for sensitive data**
6. **Use external secret management (Vault, AWS Secrets Manager)**
7. **Set resource limits to prevent resource exhaustion**
8. **Use network policies to restrict operator network access**
