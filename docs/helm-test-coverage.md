# Test Coverage Summary

## Operator Tests

### Unit Tests (`test_operator.py`)
- **Initialization**: Config loading (in-cluster and kube config fallback)
- **CronJob Creation**: Basic creation, defaults, environment variables, PVC mounting, secrets, resources, owner references
- **Update Operations**: Conflict handling (409), error handling
- **Delete Operations**: Success, not found (404), error handling
- **Status Updates**: Success and error scenarios
- **Event Handling**: ADDED, MODIFIED, DELETED events
- **Watch Loop**: Event streaming and error recovery

### Integration Tests (`test_integration.py`)
- **S3 Backup Workflow**: Complete end-to-end S3 backup configuration
- **GCS Backup Workflow**: Google Cloud Storage backup configuration
- **Local Filesystem Backup**: Local storage with PVC
- **Suspended Jobs**: Backup job suspension
- **Event Lifecycle**: Full ADDED → MODIFIED → DELETED workflow
- **Multi-namespace**: Multiple backups across different namespaces

### Edge Case Tests (`test_edge_cases.py`)
- **Missing Optional Fields**: Encryption without secret ref, empty retention policies
- **Empty Values**: Archive name, destination root, retention values
- **Labels and Selectors**: Proper labeling throughout resource hierarchy
- **Resource Policies**: Restart policy, backoff limits, concurrency policy
- **History Limits**: Job history retention
- **Image Configuration**: Pull policy settings
- **Name Length**: Long backup names (Kubernetes limits)
- **Special Characters**: Paths with spaces and special characters
- **Zero Values**: Retention with zero values

## Helm Chart Tests

### Deployment Tests (`deployment_test.yaml`)
- Default values rendering
- Custom replica count
- Custom image repository and tag
- Resource limits and requests
- Service account configuration
- Pod annotations
- Node selectors
- Tolerations
- Affinity rules
- Environment variables (WATCH_NAMESPACE, LOG_LEVEL)
- Image pull secrets
- Security contexts (pod and container)

### Service Account Tests (`serviceaccount_test.yaml`)
- Service account creation
- Conditional creation
- Custom service account names
- Service account annotations (e.g., AWS IAM roles)

### Cluster Role Tests (`clusterrole_test.yaml`)
- BackupJob CRD permissions
- BackupJob status permissions
- CronJob permissions
- Secret read permissions
- Event creation permissions

### Cluster Role Binding Tests (`clusterrolebinding_test.yaml`)
- ClusterRole reference
- Service account binding
- Namespace scoping
- Custom service account support

### CRD Tests (`crd_test.yaml`)
- CustomResourceDefinition creation
- API group and version
- Resource scope (Namespaced)
- Plural/singular names
- Required fields (source, destination)
- Optional fields (schedule, compression, retention, encryption, resources)
- Schema validation
- Status subresource

## Test Execution

All tests can be run using:
```bash
cd helm/simple-backup-operator
make test-all
```

Or individually:
- `make test-operator` - Operator unit and integration tests
- `make test-helm` - Helm chart tests
- `make lint-helm` - Helm chart linting

## CI/CD Integration

GitHub Actions workflow (`.github/workflows/helm-tests.yml`) runs:
1. Operator unit tests with coverage
2. Helm chart tests with helm-unittest
3. Helm chart linting
4. Template validation with custom values
5. Coverage reporting to Codecov

## Coverage Goals

- **Operator Code**: >90% coverage (currently comprehensive)
- **Helm Templates**: 100% of templates tested
- **CRD Schema**: All required and optional fields validated
- **RBAC**: All permissions verified
