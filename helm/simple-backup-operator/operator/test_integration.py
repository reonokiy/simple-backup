import pytest
from unittest.mock import Mock, patch
from backup_operator import BackupJobController
from kubernetes import client


@pytest.fixture
def controller():
    with patch('backup_operator.config'):
        return BackupJobController()


class TestBackupJobIntegration:
    def test_complete_s3_backup_workflow(self, controller):
        backupjob = {
            'metadata': {
                'name': 's3-backup',
                'namespace': 'production',
                'uid': 's3-uid-123'
            },
            'spec': {
                'schedule': '0 3 * * *',
                'compression': 'tar.zst',
                'archiveName': 'prod-db',
                'source': {
                    'path': '/var/lib/postgresql/data',
                    'pvcName': 'postgres-data'
                },
                'destination': {
                    'service': 's3',
                    'bucket': 'backups/postgresql/',
                    'secretRef': 'aws-s3-credentials'
                },
                'retention': {
                    'daily': 7,
                    'weekly': 4,
                    'monthly': 12,
                    'yearly': 3
                },
                'encryption': {
                    'enabled': True,
                    'recipientSecretRef': {
                        'name': 'age-encryption-key',
                        'key': 'public-key'
                    }
                },
                'resources': {
                    'limits': {'cpu': '2', 'memory': '4Gi'},
                    'requests': {'cpu': '1', 'memory': '2Gi'}
                }
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'production')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        assert cronjob.metadata.namespace == 'production'
        assert cronjob.spec.schedule == '0 3 * * *'
        assert container.image == 'simple-backup:latest'
        
        env_dict = {e.name: e.value for e in container.env if e.value}
        assert env_dict['BACKUP_SOURCE_PATH'] == '/var/lib/postgresql/data'
        assert env_dict['BACKUP_DEST_SERVICE'] == 's3'
        assert env_dict['BACKUP_STORAGE_BUCKET'] == 'backups/postgresql/'
        assert env_dict['BACKUP_ENCRYPTION_ENABLED'] == 'true'
        
        assert container.env_from[0].secret_ref.name == 'aws-s3-credentials'
    
    def test_complete_gcs_backup_workflow(self, controller):
        backupjob = {
            'metadata': {
                'name': 'gcs-backup',
                'namespace': 'default',
                'uid': 'gcs-uid-456'
            },
            'spec': {
                'schedule': '0 */6 * * *',
                'compression': 'tar.gz',
                'archiveName': 'app-data',
                'source': {
                    'path': '/data'
                },
                'destination': {
                    'service': 'gcs',
                    'root': 'backups/',
                    'secretRef': 'gcp-credentials'
                },
                'retention': {
                    'maxBackups': 50
                },
                'encryption': {
                    'enabled': False
                }
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        env_dict = {e.name: e.value for e in container.env if e.value}
        assert env_dict['BACKUP_COMPRESSION'] == 'tar.gz'
        assert env_dict['BACKUP_RETENTION_MAX_BACKUPS'] == '50'
        assert env_dict['BACKUP_ENCRYPTION_ENABLED'] == 'false'
        
        encryption_env_exists = any(
            e.name == 'BACKUP_ENCRYPTION_RECIPIENT' 
            for e in container.env
        )
        assert not encryption_env_exists
    
    def test_local_filesystem_backup_workflow(self, controller):
        backupjob = {
            'metadata': {
                'name': 'local-backup',
                'namespace': 'default',
                'uid': 'local-uid-789'
            },
            'spec': {
                'schedule': '*/30 * * * *',
                'compression': 'tar',
                'source': {
                    'path': '/source',
                    'pvcName': 'source-pvc'
                },
                'destination': {
                    'service': 'local',
                    'root': '/backups'
                },
                'retention': {
                    'maxBackups': 10
                }
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        
        assert cronjob.spec.schedule == '*/30 * * * *'
        
        pod_spec = cronjob.spec.job_template.spec.template.spec
        assert pod_spec.volumes[0].persistent_volume_claim.claim_name == 'source-pvc'
    
    def test_suspended_backup_job(self, controller):
        backupjob = {
            'metadata': {
                'name': 'suspended-backup',
                'namespace': 'default',
                'uid': 'suspended-uid'
            },
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'},
                'suspend': True
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        
        assert cronjob.spec.suspend == True
    
    def test_full_event_lifecycle(self, controller):
        backupjob = {
            'metadata': {
                'name': 'lifecycle-backup',
                'namespace': 'default',
                'uid': 'lifecycle-uid'
            },
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.batch_api.replace_namespaced_cron_job = Mock()
        controller.batch_api.delete_namespaced_cron_job = Mock()
        
        add_event = {'type': 'ADDED', 'object': backupjob}
        controller.handle_event(add_event)
        assert controller.batch_api.create_namespaced_cron_job.call_count == 1
        
        backupjob['spec']['schedule'] = '0 4 * * *'
        modify_event = {'type': 'MODIFIED', 'object': backupjob}
        controller.handle_event(modify_event)
        assert controller.batch_api.create_namespaced_cron_job.call_count == 2
        
        delete_event = {'type': 'DELETED', 'object': backupjob}
        controller.handle_event(delete_event)
        controller.batch_api.delete_namespaced_cron_job.assert_called_once()
    
    def test_multiple_backups_different_namespaces(self, controller):
        controller.batch_api.create_namespaced_cron_job = Mock()
        
        backupjob1 = {
            'metadata': {'name': 'backup1', 'namespace': 'ns1', 'uid': 'uid1'},
            'spec': {'source': {'path': '/data1'}, 'destination': {'service': 's3'}}
        }
        backupjob2 = {
            'metadata': {'name': 'backup2', 'namespace': 'ns2', 'uid': 'uid2'},
            'spec': {'source': {'path': '/data2'}, 'destination': {'service': 'gcs'}}
        }
        
        controller.create_cronjob_from_backupjob(backupjob1, 'ns1')
        controller.create_cronjob_from_backupjob(backupjob2, 'ns2')
        
        assert controller.batch_api.create_namespaced_cron_job.call_count == 2
        
        call1 = controller.batch_api.create_namespaced_cron_job.call_args_list[0]
        call2 = controller.batch_api.create_namespaced_cron_job.call_args_list[1]
        
        assert call1[1]['namespace'] == 'ns1'
        assert call2[1]['namespace'] == 'ns2'
