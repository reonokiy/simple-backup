import pytest
from unittest.mock import Mock, MagicMock, patch, call
from kubernetes import client
from kubernetes.client.rest import ApiException
from backup_operator import BackupJobController


@pytest.fixture
def controller():
    with patch('backup_operator.config'):
        return BackupJobController()


@pytest.fixture
def sample_backupjob():
    return {
        'metadata': {
            'name': 'test-backup',
            'namespace': 'default',
            'uid': 'test-uid-123'
        },
        'spec': {
            'schedule': '0 2 * * *',
            'compression': 'tar.zst',
            'archiveName': 'myapp',
            'source': {
                'path': '/data',
                'pvcName': 'data-pvc'
            },
            'destination': {
                'service': 's3',
                'root': 'backups/',
                'secretRef': 'aws-credentials',
                'storage': {
                    'bucket': 'my-bucket'
                }
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
            }
        }
    }


class TestBackupJobController:
    def test_init_incluster_config(self):
        with patch('backup_operator.config.load_incluster_config') as mock_incluster:
            controller = BackupJobController()
            mock_incluster.assert_called_once()
            assert controller.group == "simple-backup.nokiy.net"
            assert controller.version == "v1alpha1"
            assert controller.plural == "backupjobs"
    
    def test_init_fallback_to_kube_config(self):
        with patch('backup_operator.config.load_incluster_config', side_effect=Exception()):
            with patch('backup_operator.config.load_kube_config') as mock_kube:
                controller = BackupJobController()
                mock_kube.assert_called_once()
    
    def test_create_cronjob_basic(self, controller, sample_backupjob):
        controller.batch_api.create_namespaced_cron_job = Mock()
        
        controller.create_cronjob_from_backupjob(sample_backupjob, 'default')
        
        controller.batch_api.create_namespaced_cron_job.assert_called_once()
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        
        assert call_args[1]['namespace'] == 'default'
        cronjob = call_args[1]['body']
        assert cronjob.metadata.name == 'test-backup-cronjob'
        assert cronjob.spec.schedule == '0 2 * * *'
        assert cronjob.spec.concurrency_policy == 'Forbid'
        assert cronjob.spec.successful_jobs_history_limit == 3
        assert cronjob.spec.failed_jobs_history_limit == 3
    
    def test_create_cronjob_with_defaults(self, controller):
        minimal_backupjob = {
            'metadata': {
                'name': 'minimal-backup',
                'namespace': 'default',
                'uid': 'minimal-uid'
            },
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'}
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(minimal_backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        env_dict = {e.name: e.value for e in container.env if e.value is not None}
        
        assert env_dict['BACKUP_COMPRESSION'] == 'tar.zst'
        assert env_dict['BACKUP_RETENTION_MAX_BACKUPS'] == '0'
        assert env_dict['BACKUP_RETENTION_DAILY'] == '7'
        assert env_dict['BACKUP_ENCRYPTION_ENABLED'] == 'false'
        assert cronjob.spec.schedule == '0 2 * * *'
    
    def test_create_cronjob_environment_variables(self, controller, sample_backupjob):
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(sample_backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        env_dict = {e.name: e.value for e in container.env if e.value is not None}
        
        assert env_dict['BACKUP_SOURCE_PATH'] == '/data'
        assert env_dict['BACKUP_DEST_SERVICE'] == 's3'
        assert env_dict['BACKUP_DEST_ROOT'] == 'backups/'
        assert env_dict['BACKUP_STORAGE_BUCKET'] == 'my-bucket'
        assert env_dict['BACKUP_COMPRESSION'] == 'tar.zst'
        assert env_dict['BACKUP_ARCHIVE_NAME'] == 'myapp'
        assert env_dict['BACKUP_RETENTION_MAX_BACKUPS'] == '10'
        assert env_dict['BACKUP_RETENTION_DAILY'] == '7'
        assert env_dict['BACKUP_RETENTION_WEEKLY'] == '4'
        assert env_dict['BACKUP_RETENTION_MONTHLY'] == '6'
        assert env_dict['BACKUP_RETENTION_YEARLY'] == '2'
        assert env_dict['BACKUP_ENCRYPTION_ENABLED'] == 'true'
    
    def test_create_cronjob_encryption_secret_ref(self, controller, sample_backupjob):
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(sample_backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        encryption_env = next(e for e in container.env if e.name == 'BACKUP_ENCRYPTION_RECIPIENT')
        assert encryption_env.value_from.secret_key_ref.name == 'age-key'
        assert encryption_env.value_from.secret_key_ref.key == 'recipient'
    
    def test_create_cronjob_with_pvc(self, controller, sample_backupjob):
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(sample_backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        pod_spec = cronjob.spec.job_template.spec.template.spec
        
        assert len(pod_spec.volumes) == 1
        assert pod_spec.volumes[0].name == 'data'
        assert pod_spec.volumes[0].persistent_volume_claim.claim_name == 'data-pvc'
        
        container = pod_spec.containers[0]
        assert len(container.volume_mounts) == 1
        assert container.volume_mounts[0].name == 'data'
        assert container.volume_mounts[0].mount_path == '/data'
        assert container.volume_mounts[0].read_only == True
    
    def test_create_cronjob_without_pvc(self, controller):
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
        
        assert pod_spec.volumes is None
        assert pod_spec.containers[0].volume_mounts is None
    
    def test_create_cronjob_with_destination_secret(self, controller, sample_backupjob):
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(sample_backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        assert len(container.env_from) == 1
        assert container.env_from[0].secret_ref.name == 'aws-credentials'
    
    def test_create_cronjob_with_resources(self, controller, sample_backupjob):
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(sample_backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        assert container.resources.limits == {'cpu': '1', 'memory': '1Gi'}
        assert container.resources.requests == {'cpu': '500m', 'memory': '512Mi'}
    
    def test_create_cronjob_with_default_resources(self, controller):
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
        
        assert container.resources.limits == {'cpu': '500m', 'memory': '512Mi'}
        assert container.resources.requests == {'cpu': '250m', 'memory': '256Mi'}
    
    def test_create_cronjob_with_suspend(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
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
    
    def test_create_cronjob_owner_reference(self, controller, sample_backupjob):
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(sample_backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        
        assert len(cronjob.metadata.owner_references) == 1
        owner_ref = cronjob.metadata.owner_references[0]
        assert owner_ref.api_version == 'simple-backup.nokiy.net/v1alpha1'
        assert owner_ref.kind == 'BackupJob'
        assert owner_ref.name == 'test-backup'
        assert owner_ref.uid == 'test-uid-123'
        assert owner_ref.controller == True
        assert owner_ref.block_owner_deletion == True
    
    def test_create_cronjob_update_on_conflict(self, controller, sample_backupjob):
        controller.batch_api.create_namespaced_cron_job = Mock(
            side_effect=ApiException(status=409)
        )
        controller.batch_api.replace_namespaced_cron_job = Mock()
        
        controller.create_cronjob_from_backupjob(sample_backupjob, 'default')
        
        controller.batch_api.create_namespaced_cron_job.assert_called_once()
        controller.batch_api.replace_namespaced_cron_job.assert_called_once()
        
        replace_args = controller.batch_api.replace_namespaced_cron_job.call_args
        assert replace_args[1]['name'] == 'test-backup-cronjob'
        assert replace_args[1]['namespace'] == 'default'
    
    def test_create_cronjob_raises_on_other_errors(self, controller, sample_backupjob):
        controller.batch_api.create_namespaced_cron_job = Mock(
            side_effect=ApiException(status=500)
        )
        
        with pytest.raises(ApiException) as exc_info:
            controller.create_cronjob_from_backupjob(sample_backupjob, 'default')
        assert exc_info.value.status == 500
    
    def test_delete_cronjob_success(self, controller):
        controller.batch_api.delete_namespaced_cron_job = Mock()
        
        controller.delete_cronjob('test-backup', 'default')
        
        controller.batch_api.delete_namespaced_cron_job.assert_called_once_with(
            name='test-backup-cronjob',
            namespace='default',
            body=client.V1DeleteOptions(propagation_policy='Foreground')
        )
    
    def test_delete_cronjob_not_found(self, controller):
        controller.batch_api.delete_namespaced_cron_job = Mock(
            side_effect=ApiException(status=404)
        )
        
        controller.delete_cronjob('test-backup', 'default')
        
        controller.batch_api.delete_namespaced_cron_job.assert_called_once()
    
    def test_delete_cronjob_other_error(self, controller):
        controller.batch_api.delete_namespaced_cron_job = Mock(
            side_effect=ApiException(status=500, reason="Server Error")
        )
        
        controller.delete_cronjob('test-backup', 'default')
        
        controller.batch_api.delete_namespaced_cron_job.assert_called_once()
    
    def test_update_status_success(self, controller):
        controller.custom_api.patch_namespaced_custom_object_status = Mock()
        
        status_update = {'lastBackup': '2025-01-01T00:00:00Z'}
        controller.update_status('test-backup', 'default', status_update)
        
        controller.custom_api.patch_namespaced_custom_object_status.assert_called_once_with(
            group='simple-backup.nokiy.net',
            version='v1alpha1',
            namespace='default',
            plural='backupjobs',
            name='test-backup',
            body={'status': status_update}
        )
    
    def test_update_status_error(self, controller):
        controller.custom_api.patch_namespaced_custom_object_status = Mock(
            side_effect=ApiException(status=500)
        )
        
        controller.update_status('test-backup', 'default', {})
        
        controller.custom_api.patch_namespaced_custom_object_status.assert_called_once()
    
    def test_handle_event_added(self, controller, sample_backupjob):
        controller.create_cronjob_from_backupjob = Mock()
        
        event = {
            'type': 'ADDED',
            'object': sample_backupjob
        }
        
        controller.handle_event(event)
        
        controller.create_cronjob_from_backupjob.assert_called_once_with(
            sample_backupjob, 'default'
        )
    
    def test_handle_event_modified(self, controller, sample_backupjob):
        controller.create_cronjob_from_backupjob = Mock()
        
        event = {
            'type': 'MODIFIED',
            'object': sample_backupjob
        }
        
        controller.handle_event(event)
        
        controller.create_cronjob_from_backupjob.assert_called_once_with(
            sample_backupjob, 'default'
        )
    
    def test_handle_event_deleted(self, controller, sample_backupjob):
        controller.delete_cronjob = Mock()
        
        event = {
            'type': 'DELETED',
            'object': sample_backupjob
        }
        
        controller.handle_event(event)
        
        controller.delete_cronjob.assert_called_once_with('test-backup', 'default')
    
    def test_run_watches_events(self, controller):
        mock_watch = Mock()
        mock_events = [
            {'type': 'ADDED', 'object': {
                'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
                'spec': {'source': {'path': '/data'}, 'destination': {'service': 's3'}}
            }}
        ]
        mock_watch.stream = Mock(return_value=iter(mock_events))
        
        controller.handle_event = Mock(side_effect=StopIteration)
        
        with patch('backup_operator.watch.Watch', return_value=mock_watch):
            with pytest.raises(StopIteration):
                controller.run()
        
        controller.handle_event.assert_called_once()
    
    def test_run_handles_exceptions(self, controller):
        mock_watch = Mock()
        mock_events = [
            {'type': 'ADDED', 'object': {
                'metadata': {'name': 'test1', 'namespace': 'default', 'uid': 'uid1'},
                'spec': {'source': {'path': '/data'}, 'destination': {'service': 's3'}}
            }},
            {'type': 'ADDED', 'object': {
                'metadata': {'name': 'test2', 'namespace': 'default', 'uid': 'uid2'},
                'spec': {'source': {'path': '/data'}, 'destination': {'service': 's3'}}
            }}
        ]
        mock_watch.stream = Mock(return_value=iter(mock_events))
        
        controller.handle_event = Mock(side_effect=[Exception("Test error"), StopIteration])
        
        with patch('backup_operator.watch.Watch', return_value=mock_watch):
            with pytest.raises(StopIteration):
                controller.run()
        
        assert controller.handle_event.call_count == 2
    
    def test_create_cronjob_with_pause_workloads_deployment(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data', 'pvcName': 'test-pvc'},
                'destination': {'service': 's3'},
                'pauseWorkloads': True
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        pod_spec = cronjob.spec.job_template.spec.template.spec
        
        assert len(pod_spec.init_containers) == 1
        assert pod_spec.init_containers[0].name == 'pause-workloads'
        assert pod_spec.init_containers[0].image == 'bitnami/kubectl:latest'
        pause_script = pod_spec.init_containers[0].args[0]
        assert 'Finding all pods using PVC test-pvc' in pause_script
        assert 'kubectl get pods' in pause_script
        assert 'kubectl delete pod' in pause_script
        assert 'select(.metadata.labels.app != "simple-backup")' in pause_script
        
        assert len(pod_spec.containers) == 1
        backup_container = pod_spec.containers[0]
        assert backup_container.name == 'backup'
        
        shared_volume = next(v for v in pod_spec.volumes if v.name == 'shared')
        assert shared_volume.empty_dir is not None
        
        assert pod_spec.service_account_name == 'simple-backup-operator'
    
    def test_create_cronjob_with_pause_workloads_statefulset(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data', 'pvcName': 'db-pvc'},
                'destination': {'service': 's3'},
                'pauseWorkloads': True
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        pod_spec = cronjob.spec.job_template.spec.template.spec
        
        assert len(pod_spec.init_containers) == 1
        pause_script = pod_spec.init_containers[0].args[0]
        assert 'Finding all pods using PVC db-pvc' in pause_script
        assert 'kubectl delete pod' in pause_script
        
        assert len(pod_spec.containers) == 1
        assert pod_spec.containers[0].name == 'backup' 
    
    def test_create_cronjob_with_pause_workloads_disabled(self, controller):
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {'service': 's3'},
                'pauseWorkloads': {
                    'enabled': False,
                    'workloads': [
                        {'kind': 'Deployment', 'name': 'myapp'}
                    ]
                }
            }
        }
        
        controller.batch_api.create_namespaced_cron_job = Mock()
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        pod_spec = cronjob.spec.job_template.spec.template.spec
        
        assert pod_spec.init_containers is None
        assert len(pod_spec.containers) == 1
        assert pod_spec.containers[0].name == 'backup'
        assert pod_spec.service_account_name is None
        
        shared_volume = next((v for v in (pod_spec.volumes or []) if v.name == 'shared'), None)
        assert shared_volume is None
    
    def test_create_cronjob_without_pause_workloads(self, controller):
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
        
        assert pod_spec.init_containers is None
        assert len(pod_spec.containers) == 1
        assert pod_spec.containers[0].name == 'backup'
        assert pod_spec.service_account_name is None
    
    def test_generate_pause_script(self, controller):
        script = controller._generate_pause_script('test-pvc', 'default')
        
        assert 'set -e' in script
        assert 'Finding all pods using PVC test-pvc' in script
        assert 'kubectl get pods -n default -o json' in script
        assert 'select(.spec.volumes[]?.persistentVolumeClaim.claimName == "test-pvc")' in script
        assert 'select(.metadata.labels.app != "simple-backup")' in script
        assert 'kubectl delete pod $POD -n default --wait=false' in script
        assert 'kubectl wait --for=delete pod/$POD -n default --timeout=300s' in script
        assert '/shared/paused-pods.txt' in script
    
    def test_generate_resume_script(self, controller):
        script = controller._generate_resume_script('default')
        
        assert 'set -e' in script
        assert 'sleep 5' in script
        assert '/shared/paused-pods.txt' in script
        assert 'Pods will be automatically recreated by their controller' in script
        assert 'Controllers (Deployment/StatefulSet/ReplicaSet) will recreate the deleted pods' in script

    
    def test_load_storage_configs_success(self, controller):
        mock_configmap = Mock()
        mock_configmap.data = {
            'storage-configs.yaml': '''
s3-primary:
  service: s3
  root: backups/
  storage:
    bucket: my-bucket
    region: us-east-1
'''
        }
        controller.core_api.read_namespaced_config_map = Mock(return_value=mock_configmap)
        
        configs = controller._load_storage_configs('default')
        
        assert 's3-primary' in configs
        assert configs['s3-primary']['service'] == 's3'
        assert configs['s3-primary']['root'] == 'backups/'
        assert configs['s3-primary']['storage']['bucket'] == 'my-bucket'
    
    def test_load_storage_configs_not_found(self, controller):
        controller.core_api.read_namespaced_config_map = Mock(
            side_effect=ApiException(status=404)
        )
        
        configs = controller._load_storage_configs('default')
        
        assert configs == {}
    
    def test_load_storage_configs_empty(self, controller):
        mock_configmap = Mock()
        mock_configmap.data = {}
        controller.core_api.read_namespaced_config_map = Mock(return_value=mock_configmap)
        
        configs = controller._load_storage_configs('default')
        
        assert configs == {}
    
    def test_resolve_destination_with_storage_config_ref(self, controller):
        mock_configmap = Mock()
        mock_configmap.data = {
            'storage-configs.yaml': '''
s3-primary:
  service: s3
  root: backups/
  storage:
    bucket: my-bucket
    region: us-east-1
'''
        }
        controller.core_api.read_namespaced_config_map = Mock(return_value=mock_configmap)
        
        destination = {
            'storageConfigRef': 's3-primary',
            'root': 'custom/path',
            'secretRef': 's3-credentials'
        }
        
        resolved = controller._resolve_destination(destination, 'default')
        
        assert resolved['service'] == 's3'
        assert resolved['root'] == 'custom/path'
        assert resolved['storage']['bucket'] == 'my-bucket'
        assert resolved['storage']['region'] == 'us-east-1'
        assert resolved['secretRef'] == 's3-credentials'
    
    def test_resolve_destination_with_storage_config_ref_default_root(self, controller):
        mock_configmap = Mock()
        mock_configmap.data = {
            'storage-configs.yaml': '''
s3-primary:
  service: s3
  root: backups/
  storage:
    bucket: my-bucket
'''
        }
        controller.core_api.read_namespaced_config_map = Mock(return_value=mock_configmap)
        
        destination = {
            'storageConfigRef': 's3-primary'
        }
        
        resolved = controller._resolve_destination(destination, 'default')
        
        assert resolved['service'] == 's3'
        assert resolved['root'] == 'backups/'
        assert resolved['storage']['bucket'] == 'my-bucket'
    
    def test_resolve_destination_with_storage_config_ref_not_found(self, controller):
        mock_configmap = Mock()
        mock_configmap.data = {
            'storage-configs.yaml': '''
s3-primary:
  service: s3
'''
        }
        controller.core_api.read_namespaced_config_map = Mock(return_value=mock_configmap)
        
        destination = {
            'storageConfigRef': 'nonexistent'
        }
        
        with pytest.raises(ValueError, match="Storage config 'nonexistent' not found"):
            controller._resolve_destination(destination, 'default')
    
    def test_resolve_destination_without_storage_config_ref(self, controller):
        destination = {
            'service': 's3',
            'root': 'backups/',
            'storage': {
                'bucket': 'my-bucket'
            },
            'secretRef': 's3-credentials'
        }
        
        resolved = controller._resolve_destination(destination, 'default')
        
        assert resolved == destination
    
    def test_create_cronjob_with_storage_config_ref(self, controller):
        mock_configmap = Mock()
        mock_configmap.data = {
            'storage-configs.yaml': '''
s3-primary:
  service: s3
  root: backups/
  storage:
    bucket: my-bucket
    region: us-east-1
'''
        }
        controller.core_api.read_namespaced_config_map = Mock(return_value=mock_configmap)
        controller.batch_api.create_namespaced_cron_job = Mock()
        
        backupjob = {
            'metadata': {'name': 'test', 'namespace': 'default', 'uid': 'uid'},
            'spec': {
                'source': {'path': '/data'},
                'destination': {
                    'storageConfigRef': 's3-primary',
                    'secretRef': 's3-credentials'
                }
            }
        }
        
        controller.create_cronjob_from_backupjob(backupjob, 'default')
        
        call_args = controller.batch_api.create_namespaced_cron_job.call_args
        cronjob = call_args[1]['body']
        container = cronjob.spec.job_template.spec.template.spec.containers[0]
        
        env_dict = {e.name: e.value for e in container.env if e.value is not None}
        
        assert env_dict['BACKUP_DEST_SERVICE'] == 's3'
        assert env_dict['BACKUP_STORAGE_BUCKET'] == 'my-bucket'
        assert env_dict['BACKUP_STORAGE_REGION'] == 'us-east-1'
        assert container.env_from[0].secret_ref.name == 's3-credentials'

