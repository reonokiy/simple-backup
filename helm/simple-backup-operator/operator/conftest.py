import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def mock_k8s_config():
    with patch('backup_operator.config') as mock_config:
        yield mock_config


@pytest.fixture
def mock_apis():
    with patch('backup_operator.client.CustomObjectsApi') as mock_custom, \
         patch('backup_operator.client.BatchV1Api') as mock_batch, \
         patch('backup_operator.client.CoreV1Api') as mock_core:
        yield {
            'custom': mock_custom.return_value,
            'batch': mock_batch.return_value,
            'core': mock_core.return_value
        }


@pytest.fixture
def minimal_backupjob():
    return {
        'metadata': {
            'name': 'test-backup',
            'namespace': 'default',
            'uid': 'test-uid-123'
        },
        'spec': {
            'source': {
                'path': '/data'
            },
            'destination': {
                'service': 's3'
            }
        }
    }


@pytest.fixture
def full_backupjob():
    return {
        'metadata': {
            'name': 'full-backup',
            'namespace': 'production',
            'uid': 'full-uid-456'
        },
        'spec': {
            'schedule': '0 2 * * *',
            'compression': 'tar.zst',
            'archiveName': 'myapp',
            'source': {
                'path': '/var/lib/data',
                'pvcName': 'data-pvc'
            },
            'destination': {
                'service': 's3',
                'root': 'backups/',
                'secretRef': 'aws-credentials'
            },
            'retention': {
                'maxBackups': 10,
                'daily': 7,
                'weekly': 4,
                'monthly': 6,
                'yearly': 2
            },
            'encryption': {
                'enabled': True,
                'recipientSecretRef': {
                    'name': 'age-key',
                    'key': 'recipient'
                }
            },
            'resources': {
                'limits': {'cpu': '1', 'memory': '1Gi'},
                'requests': {'cpu': '500m', 'memory': '512Mi'}
            },
            'suspend': False
        }
    }


@pytest.fixture
def s3_backupjob():
    return {
        'metadata': {
            'name': 's3-backup',
            'namespace': 'default',
            'uid': 's3-uid'
        },
        'spec': {
            'source': {'path': '/data'},
            'destination': {
                'service': 's3',
                'root': 's3://my-bucket/backups/',
                'secretRef': 'aws-s3-credentials'
            }
        }
    }


@pytest.fixture
def gcs_backupjob():
    return {
        'metadata': {
            'name': 'gcs-backup',
            'namespace': 'default',
            'uid': 'gcs-uid'
        },
        'spec': {
            'source': {'path': '/data'},
            'destination': {
                'service': 'gcs',
                'root': 'gs://my-bucket/backups/',
                'secretRef': 'gcp-credentials'
            }
        }
    }


@pytest.fixture
def local_backupjob():
    return {
        'metadata': {
            'name': 'local-backup',
            'namespace': 'default',
            'uid': 'local-uid'
        },
        'spec': {
            'source': {'path': '/source', 'pvcName': 'source-pvc'},
            'destination': {
                'service': 'local',
                'root': '/backups'
            }
        }
    }
