# simple-backup-operator Helm Chart

Kubernetes operator for managing BackupJob custom resources.

## Installation

```bash
helm install simple-backup-operator ./helm/simple-backup-operator
```

## Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of operator replicas | `1` |
| `image.repository` | Operator image repository | `simple-backup-operator` |
| `image.tag` | Operator image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `serviceAccount.create` | Create service account | `true` |
| `resources.limits.cpu` | CPU limit | `200m` |
| `resources.limits.memory` | Memory limit | `256Mi` |
| `resources.requests.cpu` | CPU request | `100m` |
| `resources.requests.memory` | Memory request | `128Mi` |
| `watchNamespace` | Namespace to watch (empty for all) | `""` |
| `operator.logLevel` | Operator log level | `INFO` |

## Development

The operator source code is in the `operator/` directory.

Install dependencies with uv:

```bash
cd helm/simple-backup-operator/operator
uv sync
```

## Testing

See [Helm Testing](./helm-testing.md) for comprehensive testing documentation.

### Quick Start

Run all tests:

```bash
cd helm/simple-backup-operator
make test-all
```

Run operator unit tests only:

```bash
cd helm/simple-backup-operator
make test-operator
```

Run Helm chart tests only:

```bash
cd helm/simple-backup-operator
make test-helm
```

## Building the Operator Image

```bash
cd helm/simple-backup-operator/operator
docker build -t simple-backup-operator:latest .
```

## Example BackupJob

See `operator/example-backupjob.yaml` for custom resource examples.
