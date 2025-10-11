import os
import logging
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
        
        self.group = "backup.simple-backup.io"
        self.version = "v1alpha1"
        self.plural = "backupjobs"
        
    def create_cronjob_from_backupjob(self, backupjob, namespace):
        name = backupjob['metadata']['name']
        spec = backupjob['spec']
        
        schedule = spec.get('schedule', '0 2 * * *')
        compression = spec.get('compression', 'tar.zst')
        archive_name = spec.get('archiveName', '')
        
        source = spec['source']
        destination = spec['destination']
        retention = spec.get('retention', {})
        encryption = spec.get('encryption', {})
        resources_spec = spec.get('resources', {})
        
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
        
        container = client.V1Container(
            name="backup",
            image="simple-backup:latest",
            image_pull_policy="IfNotPresent",
            env=env_vars,
            env_from=env_from,
            volume_mounts=volume_mounts if volume_mounts else None,
            resources=resources
        )
        
        pod_template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(
                labels={"app": "simple-backup", "backupjob": name}
            ),
            spec=client.V1PodSpec(
                restart_policy="OnFailure",
                containers=[container],
                volumes=volumes if volumes else None
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
        logger.info("Starting BackupJob controller...")
        
        w = watch.Watch()
        for event in w.stream(
            self.custom_api.list_cluster_custom_object,
            group=self.group,
            version=self.version,
            plural=self.plural
        ):
            try:
                self.handle_event(event)
            except Exception as e:
                logger.error(f"Error handling event: {e}", exc_info=True)


if __name__ == "__main__":
    controller = BackupJobController()
    controller.run()
