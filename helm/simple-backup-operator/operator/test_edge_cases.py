import pytest
from unittest.mock import Mock, patch
from backup_operator import BackupJobController
from kubernetes.client.rest import ApiException


@pytest.fixture
def controller():
    with patch('backup_operator.config'):
        return BackupJobController()


class TestEdgeCases:
    def test_missing_optional_encryption_fields(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'},
                'encryption': {'enabled': False}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        encryption_recipient_exists = any(
            e.name == 'BACKUP_ENCRYPTION_RECIPIENT' 
            for e in container.env
        )
        assert not encryption_recipient_exists
    
    def test_encryption_enabled_without_secret_ref(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'},
                'encryption': {'enabled': True}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        env_dict = {e.name: e.value for e in container.env if e.value is not None}
        assert env_dict['BACKUP_ENCRYPTION_ENABLED'] == 'true'
        
        encryption_recipient_exists = any(
            e.name == 'BACKUP_ENCRYPTION_RECIPIENT' 
            for e in container.env
        )
        assert not encryption_recipient_exists
    
    def test_empty_retention_policy(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'},
                'retention': {}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        env_dict = {e.name: e.value for e in container.env if e.value is not None}
        assert env_dict['BACKUP_RETENTION_MAX_BACKUPS'] == '0'
        assert env_dict['BACKUP_RETENTION_DAILY'] == '7'
        assert env_dict['BACKUP_RETENTION_WEEKLY'] == '4'
        assert env_dict['BACKUP_RETENTION_MONTHLY'] == '6'
        assert env_dict['BACKUP_RETENTION_YEARLY'] == '2'
    
    def test_empty_archive_name(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'},
                'archiveName': ''
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        env_dict = {e.name: e.value for e in container.env if e.value is not None}
        assert env_dict['BACKUP_ARCHIVE_NAME'] == ''
    
    def test_empty_destination_root(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3', 'root': ''}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        env_dict = {e.name: e.value for e in container.env if e.value is not None}
        assert env_dict['BACKUP_DEST_ROOT'] == ''
    
    def test_missing_destination_root(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        env_dict = {e.name: e.value for e in container.env if e.value is not None}
        assert env_dict.get('BACKUP_DEST_ROOT', '') == ''
    
    def test_cronjob_labels_and_selectors(self, controller):
        backupjob = {
            'metadata': {'name': 'labeled-backup', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        
        assert cronjob.metadata.labels['app'] == 'simple-backup'
        assert cronjob.metadata.labels['backupjob'] == 'labeled-backup'
        
        job_template_labels = cronjob.spec.job_template.metadata.labels
        assert job_template_labels['app'] == 'simple-backup'
        assert job_template_labels['backupjob'] == 'labeled-backup'
        
        pod_labels = cronjob.spec.job_template.spec.template.metadata.labels
        assert pod_labels['app'] == 'simple-backup'
        assert pod_labels['backupjob'] == 'labeled-backup'
    
    def test_pod_restart_policy(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        pod_spec = cronjob.spec.job_template.spec.template.spec
        
        assert pod_spec.restart_policy == 'OnFailure'
    
    def test_job_backoff_limit(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        job_spec = cronjob.spec.job_template.spec
        
        assert job_spec.backoff_limit == 2
    
    def test_concurrent_backup_prevention(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        
        assert cronjob.spec.concurrency_policy == 'Forbid'
    
    def test_job_history_limits(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        
        assert cronjob.spec.successful_jobs_history_limit == 3
        assert cronjob.spec.failed_jobs_history_limit == 3
    
    def test_image_pull_policy(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        assert container.image_pull_policy == 'IfNotPresent'
    
    def test_long_backup_name(self, controller):
        long_name = 'a' * 63
        backupjob = {
            'metadata': {'name': long_name, 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        
        assert cronjob.metadata.name == f"{long_name}-cronjob"
    
    def test_special_characters_in_paths(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data/with spaces/and-special_chars'},
                'destination': {
                    'service': 's3',
                    'root': 'backups/path with spaces/'
                }
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        env_dict = {e.name: e.value for e in container.env if e.value is not None}
        assert env_dict['BACKUP_SOURCE_PATH'] == '/data/with spaces/and-special_chars'
        assert env_dict['BACKUP_DEST_ROOT'] == 'backups/path with spaces/'
    
    def test_zero_retention_values(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'},
                'retention': {
                    'maxBackups': 0,
                    'daily': 0,
                    'weekly': 0,
                    'monthly': 0,
                    'yearly': 0
                }
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        env_dict = {e.name: e.value for e in container.env if e.value is not None}
        assert env_dict['BACKUP_RETENTION_MAX_BACKUPS'] == '0'
        assert env_dict['BACKUP_RETENTION_DAILY'] == '0'
        assert env_dict['BACKUP_RETENTION_WEEKLY'] == '0'
        assert env_dict['BACKUP_RETENTION_MONTHLY'] == '0'
        assert env_dict['BACKUP_RETENTION_YEARLY'] == '0'
