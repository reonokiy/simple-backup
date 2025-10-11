# Testing

This directory contains tests for the simple-backup Kubernetes operator.

## Operator Unit Tests

Unit tests for the operator are located in `operator/test_operator.py`.

### Running Operator Tests

```bash
cd helm/simple-backup-operator/operator
uv run pytest test_operator.py -v
```

Or with coverage:

```bash
uv run pytest test_operator.py -v --cov=operator --cov-report=term-missing
```

### Test Coverage

The operator tests cover:
- Initialization and configuration loading
- CronJob creation with various configurations
- Environment variable mapping
- Volume and PVC mounting
- Secret references
- Resource limits and requests
- Owner references
- Update and delete operations
- Event handling
- Error handling and edge cases

## Helm Chart Tests

Helm chart tests are located in the `tests/` directory and use the [helm-unittest](https://github.com/helm-unittest/helm-unittest) plugin.

### Installing helm-unittest

```bash
helm plugin install https://github.com/helm-unittest/helm-unittest
```

### Running Helm Chart Tests

From the repository root:

```bash
helm unittest helm/simple-backup-operator
```

With verbose output:

```bash
helm unittest helm/simple-backup-operator -v
```

### Test Coverage

The Helm chart tests cover:
- Deployment configuration and customization
- Service account creation and binding
- RBAC (ClusterRole and ClusterRoleBinding)
- Custom Resource Definition (CRD) validation
- Image configuration
- Resource limits and requests
- Node selectors, tolerations, and affinity
- Security contexts
- Environment variables

## Continuous Integration

To run all tests in CI:

```bash
# Install helm-unittest plugin
helm plugin install https://github.com/helm-unittest/helm-unittest

# Run Helm chart tests
helm unittest helm/simple-backup-operator

# Run operator unit tests
cd helm/simple-backup-operator/operator
uv run pytest test_operator.py -v --cov=operator
```

## Test Structure

```
helm/simple-backup-operator/
├── operator/
│   ├── operator.py           # Operator implementation
│   ├── test_operator.py      # Operator unit tests
│   └── pyproject.toml        # Python dependencies and config
└── tests/                    # Helm chart tests
    ├── deployment_test.yaml
    ├── serviceaccount_test.yaml
    ├── clusterrole_test.yaml
    ├── clusterrolebinding_test.yaml
    └── crd_test.yaml
```
