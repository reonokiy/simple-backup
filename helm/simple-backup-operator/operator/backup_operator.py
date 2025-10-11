import os
import logging
import yaml
from datetime import datetime
from typing import Dict, Any, Optional
from kubernetes import client, config, watch  # type: ignore
from kubernetes.client.rest import ApiException  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupJobController:
    def __init__(self):
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.custom_api = client.CustomObjectsApi()
        self.batch_api = client.BatchV1Api()
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        
        self.group = "simple-backup.nokiy.net"
        self.version = "v1alpha1"
        self.plural = "backupjobs"
        
        self.service_account_name = os.getenv('SERVICE_ACCOUNT_NAME', 'simple-backup-operator')
        self.backup_image = os.getenv('BACKUP_IMAGE', 'simple-backup:latest')
        self.backup_image_pull_policy = os.getenv('BACKUP_IMAGE_PULL_POLICY', 'IfNotPresent')
        self.storage_config_map = os.getenv('STORAGE_CONFIG_MAP', 'simple-backup-operator-storage-configs')
    
    def _load_storage_configs(self, namespace: str) -> Dict[str, Any]:
        try:
            configmap = self.core_api.read_namespaced_config_map(
                name=self.storage_config_map,
                namespace=namespace
            )
            data = configmap.data.get('storage-configs.yaml', '{}')
            return yaml.safe_load(data) or {}
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Storage ConfigMap {self.storage_config_map} not found in namespace {namespace}")
                return {}
            raise
    
    def _resolve_destination(self, destination: Dict[str, Any], namespace: str) -> Dict[str, Any]:
        if 'storageConfigRef' in destination:
            storage_configs = self._load_storage_configs(namespace)
            config_name = destination['storageConfigRef']
            
            if config_name not in storage_configs:
                raise ValueError(f"Storage config '{config_name}' not found in ConfigMap")
            
            storage_config = storage_configs[config_name]
            resolved_dest = {
                'service': storage_config['service'],
                'root': destination.get('root', storage_config.get('root', '')),
                'storage': storage_config.get('storage', {})
            }
            
            if 'secretRef' in destination:
                resolved_dest['secretRef'] = destination['secretRef']
            
            return resolved_dest
        
        return destination
    
    def _generate_pause_script(self, workloads, namespace):
        script_lines = ["set -e"]
        for wl in workloads:
            kind = wl['kind'].lower()
            name = wl['name']
            
            script_lines.append(f"echo 'Pausing {kind}/{name}...'")
            script_lines.append(f"kubectl get {kind} {name} -n {namespace} -o json | jq '.spec.replicas' > /shared/{name}-replicas.txt")
            script_lines.append(f"kubectl scale {kind} {name} -n {namespace} --replicas=0")
            script_lines.append(f"kubectl wait --for=delete pod -l app={name} -n {namespace} --timeout=300s || true")
            script_lines.append(f"echo '{kind}/{name} paused'")
        
        return "\n".join(script_lines)
    
    def _generate_resume_script(self, workloads, namespace):
        script_lines = ["set -e", "sleep 5"]
        for wl in workloads:
            kind = wl['kind'].lower()
            name = wl['name']
            
            script_lines.append(f"echo 'Resuming {kind}/{name}...'")
            script_lines.append(f"REPLICAS=$(cat /shared/{name}-replicas.txt || echo 1)")
            script_lines.append(f"kubectl scale {kind} {name} -n {namespace} --replicas=$REPLICAS")
            script_lines.append(f"echo \"{kind}/{name} resumed with $REPLICAS replicas\"")
        
        return "\n".join(script_lines)
        
    def create_cronjob_from_backupjob(self, backupjob, namespace):
        name = backupjob['metadata']['name']
        spec = backupjob['spec']
        
        schedule = spec.get('schedule', '0 2 * * *')
        compression = spec.get('compression', 'tar.zst')
        archive_name = spec.get('archiveName', '')
        
        source = spec['source']
        destination = self._resolve_destination(spec['destination'], namespace)
        retention = spec.get('retention', {})
        encryption = spec.get('encryption', {})
        resources_spec = spec.get('resources', {})
        pause_workloads = spec.get('pauseWorkloads', {})
        
        env_vars = [
            client.V1EnvVar(name="BACKUP_SOURCE_PATH", value=source['path']),
            client.V1EnvVar(name="BACKUP_DEST_SERVICE", value=destination['service']),
            client.V1EnvVar(name="BACKUP_DEST_ROOT", value=destination.get('root', '')),
            client.V1EnvVar(name="BACKUP_COMPRESSION", value=compression),
            client.V1EnvVar(name="BACKUP_ARCHIVE_NAME", value=archive_name),
            client.V1EnvVar(name="BACKUP_RETENTION_MAX_BACKUPS", value=str(retention.get('maxBackups', 0))),
            client.V1EnvVar(name="BACKUP_RETENTION_DAILY", value=str(retention.get('daily', 7))),
            client.V1EnvVar(name="BACKUP_RETENTION_WEEKLY", value=str(retention.get('weekly', 4))),
            client.V1EnvVar(name="BACKUP_RETENTION_MONTHLY", value=str(retention.get('monthly', 6))),
            client.V1EnvVar(name="BACKUP_RETENTION_YEARLY", value=str(retention.get('yearly', 2))),
            client.V1EnvVar(name="BACKUP_ENCRYPTION_ENABLED", value=str(encryption.get('enabled', False)).lower()),
        ]
        
        storage_config = destination.get('storage', {}).copy()
        
        legacy_fields = ['bucket', 'region', 'endpoint', 'container', 'account_name', 
                        'account_key', 'credential', 'access_key_id', 'secret_access_key',
                        'access_key_secret', 'secret_id', 'secret_key', 'username', 'password']
        
        for field in legacy_fields:
            if field in destination and field not in storage_config:
                storage_config[field] = destination[field]
        
        if destination['service'] == 'fs' and 'root' not in storage_config:
            storage_config['root'] = destination.get('root', '')
        
        for key, value in storage_config.items():
            if value is not None:
                env_key = f"BACKUP_STORAGE_{key.upper()}"
                env_vars.append(client.V1EnvVar(name=env_key, value=str(value)))
        
        if encryption.get('enabled') and 'recipientSecretRef' in encryption:
            recipient_ref = encryption['recipientSecretRef']
            env_vars.append(
                client.V1EnvVar(
                    name="BACKUP_ENCRYPTION_RECIPIENT",
                    value_from=client.V1EnvVarSource(
                        secret_key_ref=client.V1SecretKeySelector(
                            name=recipient_ref['name'],
                            key=recipient_ref['key']
                        )
                    )
                )
            )
        
        volume_mounts = []
        volumes = []
        
        if 'pvcName' in source:
            volume_mounts.append(
                client.V1VolumeMount(
                    name="data",
                    mount_path=source['path'],
                    read_only=True
                )
            )
            volumes.append(
                client.V1Volume(
                    name="data",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=source['pvcName']
                    )
                )
            )
        
        env_from = []
        if 'secretRef' in destination:
            env_from.append(
                client.V1EnvFromSource(
                    secret_ref=client.V1SecretEnvSource(
                        name=destination['secretRef']
                    )
                )
            )
        
        resources = client.V1ResourceRequirements(
            limits=resources_spec.get('limits', {'cpu': '500m', 'memory': '512Mi'}),
            requests=resources_spec.get('requests', {'cpu': '250m', 'memory': '256Mi'})
        )
        
        containers = []
        init_containers = []
        shared_volume_needed = False
        
        if pause_workloads.get('enabled'):
            workloads = pause_workloads.get('workloads', [])
            if workloads:
                shared_volume_needed = True
                pause_script = self._generate_pause_script(workloads, namespace)
                resume_script = self._generate_resume_script(workloads, namespace)
                
                init_containers.append(
                    client.V1Container(
                        name="pause-workloads",
                        image="bitnami/kubectl:latest",
                        command=["/bin/sh", "-c"],
                        args=[pause_script],
                        volume_mounts=[
                            client.V1VolumeMount(
                                name="shared",
                                mount_path="/shared"
                            )
                        ],
                        resources=client.V1ResourceRequirements(
                            limits={'cpu': '100m', 'memory': '128Mi'},
                            requests={'cpu': '50m', 'memory': '64Mi'}
                        )
                    )
                )
                
                containers.append(
                    client.V1Container(
                        name="resume-workloads",
                        image="bitnami/kubectl:latest",
                        command=["/bin/sh", "-c"],
                        args=[resume_script],
                        volume_mounts=[
                            client.V1VolumeMount(
                                name="shared",
                                mount_path="/shared"
                            )
                        ],
                        resources=client.V1ResourceRequirements(
                            limits={'cpu': '100m', 'memory': '128Mi'},
                            requests={'cpu': '50m', 'memory': '64Mi'}
                        )
                    )
                )
        
        container = client.V1Container(
            name="backup",
            image=self.backup_image,
            image_pull_policy=self.backup_image_pull_policy,
            env=env_vars,
            env_from=env_from,
            volume_mounts=volume_mounts if volume_mounts else None,
            resources=resources
        )
        
        containers.insert(0, container)
        
        if shared_volume_needed:
            volumes.append(
                client.V1Volume(
                    name="shared",
                    empty_dir=client.V1EmptyDirVolumeSource()
                )
            )
        
        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(
                labels={"app": "simple-backup", "backupjob": name}
            ),
            spec=client.V1PodSpec(
                restart_policy="OnFailure",
                init_containers=init_containers if init_containers else None,
                containers=containers,
                volumes=volumes if volumes else None,
                service_account_name=self.service_account_name if pause_workloads.get('enabled') else None
            )
        )
        
        job_template = client.V1JobTemplateSpec(
            metadata=client.V1ObjectMeta(
                labels={"app": "simple-backup", "backupjob": name}
            ),
            spec=client.V1JobSpec(
                backoff_limit=2,
                template=pod_template
            )
        )
        
        cronjob = client.V1CronJob(
            api_version="batch/v1",
            kind="CronJob",
            metadata=client.V1ObjectMeta(
                name=f"{name}-cronjob",
                namespace=namespace,
                labels={"app": "simple-backup", "backupjob": name},
                owner_references=[
                    client.V1OwnerReference(
                        api_version=f"{self.group}/{self.version}",
                        kind="BackupJob",
                        name=name,
                        uid=backupjob['metadata']['uid'],
                        controller=True,
                        block_owner_deletion=True
                    )
                ]
            ),
            spec=client.V1CronJobSpec(
                schedule=schedule,
                concurrency_policy="Forbid",
                successful_jobs_history_limit=3,
                failed_jobs_history_limit=3,
                job_template=job_template,
                suspend=spec.get('suspend', False)
            )
        )
        
        try:
            self.batch_api.create_namespaced_cron_job(
                namespace=namespace,
                body=cronjob
            )
            logger.info(f"Created CronJob {name}-cronjob in namespace {namespace}")
        except ApiException as e:
            if e.status == 409:
                self.batch_api.replace_namespaced_cron_job(
                    name=f"{name}-cronjob",
                    namespace=namespace,
                    body=cronjob
                )
                logger.info(f"Updated CronJob {name}-cronjob in namespace {namespace}")
            else:
                raise
    
    def delete_cronjob(self, backupjob_name, namespace):
        cronjob_name = f"{backupjob_name}-cronjob"
        try:
            self.batch_api.delete_namespaced_cron_job(
                name=cronjob_name,
                namespace=namespace,
                body=client.V1DeleteOptions(propagation_policy='Foreground')
            )
            logger.info(f"Deleted CronJob {cronjob_name} in namespace {namespace}")
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error deleting CronJob {cronjob_name}: {e}")
    
    def update_status(self, backupjob_name, namespace, status_update):
        try:
            self.custom_api.patch_namespaced_custom_object_status(
                group=self.group,
                version=self.version,
                namespace=namespace,
                plural=self.plural,
                name=backupjob_name,
                body={"status": status_update}
            )
            logger.info(f"Updated status for BackupJob {backupjob_name}")
        except ApiException as e:
            logger.error(f"Error updating status: {e}")
    
    def handle_event(self, event):
        event_type = event['type']
        backupjob = event['object']
        namespace = backupjob['metadata']['namespace']
        name = backupjob['metadata']['name']
        
        logger.info(f"Handling {event_type} event for BackupJob {namespace}/{name}")
        
        if event_type in ['ADDED', 'MODIFIED']:
            self.create_cronjob_from_backupjob(backupjob, namespace)
        elif event_type == 'DELETED':
            self.delete_cronjob(name, namespace)
    
    def run(self):
        logger.info(f"Starting BackupJob controller for {self.group}/{self.version}")
        w = watch.Watch()
        for event in w.stream(
            self.custom_api.list_cluster_custom_object,
            group=self.group,
            version=self.version,
            plural=self.plural
        ):
            try:
                self.handle_event(event)
            except StopIteration:
                raise
            except Exception as e:
                logger.error(f"Error handling event: {e}", exc_info=True)


if __name__ == "__main__":
    controller = BackupJobController()
    controller.run()
