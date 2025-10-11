#!/bin/bash
set -e

CLUSTER_NAME="simple-backup-e2e-local"
NAMESPACE="default"

echo "=== Simple Backup E2E Local Test ==="
echo ""

# Check if kind cluster exists
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "✓ Kind cluster '${CLUSTER_NAME}' already exists"
else
    echo "Creating kind cluster '${CLUSTER_NAME}'..."
    kind create cluster --name "${CLUSTER_NAME}" --wait 120s
    echo "✓ Kind cluster created"
fi

# Set context
kubectl config use-context "kind-${CLUSTER_NAME}"

echo ""
echo "=== Building Images ==="

echo "Building simple-backup image..."
docker buildx build \
    --tag simple-backup:e2e \
    --load \
    -f Dockerfile \
    .

echo "Building simple-backup-operator image..."
docker buildx build \
    --tag simple-backup-operator:e2e \
    --load \
    -f helm/simple-backup-operator/operator/Dockerfile \
    helm/simple-backup-operator/operator/

echo ""
echo "=== Loading Images into Kind ==="
kind load docker-image simple-backup:e2e --name "${CLUSTER_NAME}"
kind load docker-image simple-backup-operator:e2e --name "${CLUSTER_NAME}"

echo ""
echo "=== Installing Helm Chart ==="
helm upgrade --install simple-backup-operator \
    ./helm/simple-backup-operator \
    --set image.repository=simple-backup-operator \
    --set image.tag=e2e \
    --set image.pullPolicy=Never \
    --set backupImage.repository=simple-backup \
    --set backupImage.tag=e2e \
    --set backupImage.pullPolicy=Never \
    --wait \
    --timeout 2m

echo ""
echo "=== Waiting for Operator ==="
kubectl wait --for=condition=ready pod \
    -l app.kubernetes.io/name=simple-backup-operator-charts \
    --timeout=120s
echo "✓ Operator ready"

echo ""
echo "=== Deploying WebDAV Server ==="
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webdav-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: webdav
  template:
    metadata:
      labels:
        app: webdav
    spec:
      containers:
      - name: webdav
        image: bytemark/webdav:latest
        ports:
        - containerPort: 80
        env:
        - name: AUTH_TYPE
          value: Basic
        - name: USERNAME
          value: testuser
        - name: PASSWORD
          value: testpass
        volumeMounts:
        - name: webdav-data
          mountPath: /var/lib/dav
      volumes:
      - name: webdav-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: webdav-server
spec:
  selector:
    app: webdav
  ports:
  - port: 80
    targetPort: 80
EOF

kubectl wait --for=condition=available deployment/webdav-server --timeout=120s
echo "✓ WebDAV server ready"

echo ""
echo "=== Creating Test Deployment ==="
kubectl create deployment test-app \
    --image=busybox:latest \
    --replicas=2 \
    -- /bin/sh -c 'mkdir -p /data && echo "E2E test data for simple-backup" > /data/test.txt && sleep 3600' || true

kubectl wait --for=condition=available deployment/test-app --timeout=120s

echo ""
echo "=== Creating Test PVC ==="
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
EOF

kubectl wait --for=jsonpath='{.status.phase}'=Bound pvc/test-data --timeout=60s

echo ""
echo "=== Patching Deployment to Use PVC ==="
kubectl patch deployment test-app --type='json' -p='[
  {
    "op": "add",
    "path": "/spec/template/spec/volumes",
    "value": [{"name": "data", "persistentVolumeClaim": {"claimName": "test-data"}}]
  },
  {
    "op": "add",
    "path": "/spec/template/spec/containers/0/volumeMounts",
    "value": [{"name": "data", "mountPath": "/data"}]
  }
]'

kubectl rollout status deployment/test-app --timeout=120s

echo ""
echo "=== Creating BackupJob CRs ==="
kubectl apply -f - <<EOF
apiVersion: simple-backup.nokiy.net/v1alpha1
kind: BackupJob
metadata:
  name: test-backup-fs
spec:
  schedule: "*/5 * * * *"
  source:
    pvcName: test-data
    path: /data
  destination:
    service: fs
    root: /tmp/backups
  compression: tar.zst
  retention:
    daily: 7
    weekly: 4
    monthly: 6
  pauseWorkloads:
    enabled: true
    workloads:
      - kind: Deployment
        name: test-app
---
apiVersion: simple-backup.nokiy.net/v1alpha1
kind: BackupJob
metadata:
  name: test-backup-webdav
spec:
  schedule: "*/5 * * * *"
  source:
    pvcName: test-data
    path: /data
  destination:
    service: webdav
    root: /backups
    storage:
      endpoint: http://webdav-server
      username: testuser
      password: testpass
  compression: tar.gz
  retention:
    daily: 3
  pauseWorkloads:
    enabled: false
EOF

echo ""
echo "=== Waiting for CronJobs Creation ==="
timeout 30 bash -c 'until kubectl get cronjob test-backup-fs-cronjob; do sleep 2; done'
timeout 30 bash -c 'until kubectl get cronjob test-backup-webdav-cronjob; do sleep 2; done'
echo "✓ CronJobs created"

echo ""
echo "=== Verifying CronJob Configurations ==="
echo "Checking FS CronJob env vars..."
kubectl get cronjob test-backup-fs-cronjob -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].env[?(@.name=="BACKUP_STORAGE_ROOT")].value}' | grep -q '/tmp/backups'
echo "✓ FS_ROOT is correct"

echo "Checking WebDAV CronJob env vars..."
kubectl get cronjob test-backup-webdav-cronjob -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].env[?(@.name=="BACKUP_STORAGE_ENDPOINT")].value}' | grep -q 'http://webdav-server'
echo "✓ WEBDAV_ENDPOINT is correct"

kubectl get cronjob test-backup-webdav-cronjob -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].env[?(@.name=="BACKUP_STORAGE_USERNAME")].value}' | grep -q 'testuser'
echo "✓ WEBDAV_USERNAME is correct"

echo ""
echo "=== Triggering Manual Backup Jobs ==="
kubectl create job --from=cronjob/test-backup-fs-cronjob e2e-backup-fs-test
kubectl create job --from=cronjob/test-backup-webdav-cronjob e2e-backup-webdav-test

echo ""
echo "=== Waiting for Backup Jobs to Complete ==="
echo "Waiting for FS backup..."
kubectl wait --for=condition=complete job/e2e-backup-fs-test --timeout=180s
echo "✓ FS backup completed"

echo "Waiting for WebDAV backup..."
kubectl wait --for=condition=complete job/e2e-backup-webdav-test --timeout=180s
echo "✓ WebDAV backup completed"

echo ""
echo "=== Checking Backup Logs ==="
echo ""
echo "--- FS Backup Logs ---"
POD_FS=$(kubectl get pods -l job-name=e2e-backup-fs-test -o jsonpath='{.items[0].metadata.name}')
echo "Pause logs:"
kubectl logs $POD_FS -c pause-workloads
echo ""
echo "Backup logs:"
kubectl logs $POD_FS -c backup
echo ""
echo "Resume logs:"
kubectl logs $POD_FS -c resume-workloads

echo ""
echo "--- WebDAV Backup Logs ---"
POD_WEBDAV=$(kubectl get pods -l job-name=e2e-backup-webdav-test -o jsonpath='{.items[0].metadata.name}')
echo "Backup logs:"
kubectl logs $POD_WEBDAV -c backup

echo ""
echo "=== Verifying Backups Succeeded ==="
kubectl logs $POD_FS -c backup | grep -q "Backup completed: 1/1 destinations succeeded"
echo "✓ FS backup succeeded"

kubectl logs $POD_WEBDAV -c backup | grep -q "Backup completed: 1/1 destinations succeeded"
echo "✓ WebDAV backup succeeded"

echo ""
echo "=== Verifying WebDAV Server Has Backup Files ==="
POD_WEBDAV_SERVER=$(kubectl get pods -l app=webdav -o jsonpath='{.items[0].metadata.name}')
kubectl exec $POD_WEBDAV_SERVER -- ls -lah /var/lib/dav/data/backups/
kubectl exec $POD_WEBDAV_SERVER -- sh -c 'test -n "$(ls -A /var/lib/dav/data/backups/)"'
echo "✓ Backup files exist on WebDAV server"

echo ""
echo "=== Verifying Backup Integrity ==="
echo "Getting original test data..."
TEST_POD=$(kubectl get pods -l app=test-app -o jsonpath='{.items[0].metadata.name}')
ORIGINAL_DATA=$(kubectl exec $TEST_POD -- cat /data/test.txt)
echo "Original data: $ORIGINAL_DATA"

echo ""
echo "Verifying FS backup integrity..."
BACKUP_FILE_FS=$(kubectl exec $POD_FS -c backup -- sh -c 'ls -t /tmp/backups/*.tar.zst | head -1')
echo "Extracting $BACKUP_FILE_FS..."
kubectl exec $POD_FS -c backup -- sh -c "mkdir -p /tmp/restore-fs && tar -xf $BACKUP_FILE_FS -C /tmp/restore-fs"
RESTORED_DATA_FS=$(kubectl exec $POD_FS -c backup -- cat /tmp/restore-fs/data/test.txt)
echo "Restored data (FS): $RESTORED_DATA_FS"

if [ "$ORIGINAL_DATA" != "$RESTORED_DATA_FS" ]; then
    echo "ERROR: FS backup data mismatch!"
    echo "Expected: $ORIGINAL_DATA"
    echo "Got: $RESTORED_DATA_FS"
    exit 1
fi
echo "✓ FS backup integrity verified"

echo ""
echo "Verifying WebDAV backup integrity..."
BACKUP_FILE_WEBDAV=$(kubectl exec $POD_WEBDAV_SERVER -- sh -c 'ls -t /var/lib/dav/data/backups/*.tar.gz | head -1')
echo "Extracting $BACKUP_FILE_WEBDAV..."
kubectl exec $POD_WEBDAV_SERVER -- sh -c "rm -rf /tmp/restore-webdav && mkdir -p /tmp/restore-webdav && tar -xzf $BACKUP_FILE_WEBDAV -C /tmp/restore-webdav"
RESTORED_DATA_WEBDAV=$(kubectl exec $POD_WEBDAV_SERVER -- cat /tmp/restore-webdav/data/test.txt)
echo "Restored data (WebDAV): $RESTORED_DATA_WEBDAV"

if [ "$ORIGINAL_DATA" != "$RESTORED_DATA_WEBDAV" ]; then
    echo "ERROR: WebDAV backup data mismatch!"
    echo "Expected: $ORIGINAL_DATA"
    echo "Got: $RESTORED_DATA_WEBDAV"
    exit 1
fi
echo "✓ WebDAV backup integrity verified"

echo ""
echo "=== Verifying Deployment Restored ==="
REPLICAS=$(kubectl get deployment test-app -o jsonpath='{.spec.replicas}')
if [ "$REPLICAS" != "2" ]; then
    echo "ERROR: Expected 2 replicas, got $REPLICAS"
    exit 1
fi
echo "✓ Deployment has 2 replicas"

kubectl wait --for=condition=available deployment/test-app --timeout=60s
echo "✓ Deployment is available"

echo ""
echo "=== E2E Test Results ==="
echo "✅ All tests passed!"
echo ""
echo "To clean up, run:"
echo "  kubectl delete backupjob --all"
echo "  kubectl delete deployment test-app webdav-server"
echo "  kubectl delete pvc test-data"
echo "  kubectl delete svc webdav-server"
echo "  helm uninstall simple-backup-operator"
echo ""
echo "To delete the cluster:"
echo "  kind delete cluster --name ${CLUSTER_NAME}"
