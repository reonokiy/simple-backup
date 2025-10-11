import os
import sys
import logging
import signal
import tarfile
import zipfile
import gzip
import tempfile
import shutil
import re
import argparse
import tomllib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional, Dict, Any, List, Tuple
import opendal
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pyrage import x25519  # type: ignore
import pyrage  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config_from_file(config_path: Optional[str] = None) -> Dict[str, Any]:
    if not config_path:
        for path in ['config.toml', 'config.yaml', 'config.yml']:
            if os.path.exists(path):
                config_path = path
                break
    
    if not config_path or not os.path.exists(config_path):
        return {}
    
    logger.info(f"Loading configuration from {config_path}")
    
    if config_path.endswith('.toml'):
        with open(config_path, 'rb') as f:
            return tomllib.load(f)
    elif config_path.endswith(('.yaml', '.yml')):
        try:
            import yaml
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            logger.error("PyYAML import failed.")
            return {}
    else:
        logger.warning(f"Unsupported config file format: {config_path}")
        return {}


def load_config() -> Dict[str, Any]:
    file_config = load_config_from_file()
    
    config = {
        'source_path': os.getenv('BACKUP_SOURCE_PATH') or file_config.get('source_path'),
        'cron_schedule': os.getenv('BACKUP_CRON_SCHEDULE') or file_config.get('cron_schedule'),
        'compression': os.getenv('BACKUP_COMPRESSION') or file_config.get('compression', 'tar.zst'),
        'archive_name': os.getenv('BACKUP_ARCHIVE_NAME') or file_config.get('archive_name'),
        'retention_max_backups': int(os.getenv('BACKUP_RETENTION_MAX_BACKUPS') or file_config.get('retention', {}).get('max_backups', 0)),
        'retention_daily': int(os.getenv('BACKUP_RETENTION_DAILY') or file_config.get('retention', {}).get('daily', 7)),
        'retention_weekly': int(os.getenv('BACKUP_RETENTION_WEEKLY') or file_config.get('retention', {}).get('weekly', 4)),
        'retention_monthly': int(os.getenv('BACKUP_RETENTION_MONTHLY') or file_config.get('retention', {}).get('monthly', 6)),
        'retention_yearly': int(os.getenv('BACKUP_RETENTION_YEARLY') or file_config.get('retention', {}).get('yearly', 2)),
        'encryption_enabled': (os.getenv('BACKUP_ENCRYPTION_ENABLED', '').lower() == 'true') or file_config.get('encryption', {}).get('enabled', False),
        'encryption_recipient': os.getenv('BACKUP_ENCRYPTION_RECIPIENT') or file_config.get('encryption', {}).get('recipient'),
        'encryption_identity': os.getenv('BACKUP_ENCRYPTION_IDENTITY') or file_config.get('encryption', {}).get('identity'),
    }
    
    destinations = file_config.get('destinations', [])
    
    config['destinations'] = destinations
    
    if not config['source_path']:
        raise ValueError("BACKUP_SOURCE_PATH environment variable or source_path in config file is required")
    if not config['destinations']:
        raise ValueError("At least one destination is required in 'destinations' array")
    
    valid_compressions = ['none', 'tar', 'tar.gz', 'tar.bz2', 'tar.xz', 'tar.zst', 'zip', 'gzip']
    if config['compression'] not in valid_compressions:
        raise ValueError(f"Invalid compression format. Must be one of: {', '.join(valid_compressions)}")
    
    if config['encryption_enabled'] and not config['encryption_recipient']:
        raise ValueError("BACKUP_ENCRYPTION_RECIPIENT is required when encryption is enabled")
    
    return config


def create_source_operator(source_path: str) -> opendal.Operator:
    return opendal.Operator("fs", root=source_path)


def get_service_config(service_type: str, storage_config: Dict[str, Any]) -> Dict[str, Any]:
    def get_config_value(key: str, env_var: str) -> Optional[str]:
        return os.getenv(env_var) or storage_config.get(key)
    
    service_configs = {
        's3': {
            'bucket': get_config_value('bucket', 'S3_BUCKET'),
            'region': get_config_value('region', 'S3_REGION'),
            'access_key_id': get_config_value('access_key_id', 'S3_ACCESS_KEY_ID'),
            'secret_access_key': get_config_value('secret_access_key', 'S3_SECRET_ACCESS_KEY'),
            'endpoint': get_config_value('endpoint', 'S3_ENDPOINT'),
        },
        'azblob': {
            'container': get_config_value('container', 'AZURE_CONTAINER'),
            'account_name': get_config_value('account_name', 'AZURE_ACCOUNT_NAME'),
            'account_key': get_config_value('account_key', 'AZURE_ACCOUNT_KEY'),
        },
        'gcs': {
            'bucket': get_config_value('bucket', 'GCS_BUCKET'),
            'credential': get_config_value('credential', 'GCS_CREDENTIAL'),
        },
        'fs': {
            'root': get_config_value('root', 'FS_ROOT'),
        },
        'oss': {
            'bucket': get_config_value('bucket', 'OSS_BUCKET'),
            'endpoint': get_config_value('endpoint', 'OSS_ENDPOINT'),
            'access_key_id': get_config_value('access_key_id', 'OSS_ACCESS_KEY_ID'),
            'access_key_secret': get_config_value('access_key_secret', 'OSS_ACCESS_KEY_SECRET'),
        },
        'obs': {
            'bucket': get_config_value('bucket', 'OBS_BUCKET'),
            'endpoint': get_config_value('endpoint', 'OBS_ENDPOINT'),
            'access_key_id': get_config_value('access_key_id', 'OBS_ACCESS_KEY_ID'),
            'secret_access_key': get_config_value('secret_access_key', 'OBS_SECRET_ACCESS_KEY'),
        },
        'cos': {
            'bucket': get_config_value('bucket', 'COS_BUCKET'),
            'region': get_config_value('region', 'COS_REGION'),
            'secret_id': get_config_value('secret_id', 'COS_SECRET_ID'),
            'secret_key': get_config_value('secret_key', 'COS_SECRET_KEY'),
        },
        'webdav': {
            'endpoint': get_config_value('endpoint', 'WEBDAV_ENDPOINT'),
            'username': get_config_value('username', 'WEBDAV_USERNAME'),
            'password': get_config_value('password', 'WEBDAV_PASSWORD'),
        },
    }
    
    if service_type not in service_configs:
        raise ValueError(f"Unsupported service type: {service_type}")
    
    return service_configs[service_type]


def create_dest_operator(service_type: str, storage_config: Optional[Dict[str, Any]] = None) -> opendal.Operator:
    if storage_config is None:
        storage_config = {}
    
    opendal_config: Dict[str, str] = {}
    
    for key, value in os.environ.items():
        if key.startswith('OPENDAL_'):
            config_key = key[8:].lower()
            opendal_config[config_key] = value
    
    if opendal_config:
        logger.info(f"Using OPENDAL_* environment variables for {service_type} configuration")
        return opendal.Operator(service_type, **opendal_config)
    
    config = get_service_config(service_type, storage_config)
    config = {k: v for k, v in config.items() if v is not None}
    
    return opendal.Operator(service_type, **config)


def test_destination_connectivity(dest: Dict[str, Any]) -> bool:
    dest_service = dest['service']
    dest_root = dest.get('root', '')
    storage_config = dest.get('storage', {})
    
    try:
        logger.info(f"Testing connectivity to {dest_service}...")
        dest_op = create_dest_operator(dest_service, storage_config)
        
        test_path = os.path.join(dest_root, '.simple-backup-test') if dest_root else '.simple-backup-test'
        test_data = b'test'
        
        dest_op.write(test_path, test_data)
        logger.debug(f"Write test successful: {test_path}")
        
        read_data = dest_op.read(test_path)
        if read_data != test_data:
            raise ValueError(f"Read test failed: data mismatch")
        logger.debug(f"Read test successful: {test_path}")
        
        dest_op.delete(test_path)
        logger.debug(f"Delete test successful: {test_path}")
        
        logger.info(f"✓ {dest_service} connectivity test passed")
        return True
    
    except Exception as e:
        logger.error(f"✗ {dest_service} connectivity test failed: {e}")
        return False


def validate_destinations(destinations: List[Dict[str, Any]]) -> bool:
    logger.info(f"Validating {len(destinations)} destination(s)...")
    
    results = []
    for idx, dest in enumerate(destinations, 1):
        dest_service = dest['service']
        logger.info(f"Testing destination {idx}/{len(destinations)}: {dest_service}")
        success = test_destination_connectivity(dest)
        results.append({'destination': dest_service, 'success': success})
    
    failed = [r for r in results if not r['success']]
    
    if failed:
        logger.error(f"Destination validation failed: {len(failed)}/{len(destinations)} destination(s) unreachable")
        for fail in failed:
            logger.error(f"  - {fail['destination']}")
        return False
    
    logger.info(f"✓ All {len(destinations)} destination(s) validated successfully")
    return True


def create_archive(source_path: str, compression_format: str, archive_name: Optional[str] = None) -> Tuple[str, str]:
    if not archive_name:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = Path(source_path).name
        archive_name = f"backup_{base_name}_{timestamp}"
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        if compression_format == 'tar':
            archive_path = os.path.join(temp_dir, f"{archive_name}.tar")
            with tarfile.open(archive_path, 'w') as tar:
                tar.add(source_path, arcname=Path(source_path).name)
        
        elif compression_format == 'tar.gz':
            archive_path = os.path.join(temp_dir, f"{archive_name}.tar.gz")
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(source_path, arcname=Path(source_path).name)
        
        elif compression_format == 'tar.bz2':
            archive_path = os.path.join(temp_dir, f"{archive_name}.tar.bz2")
            with tarfile.open(archive_path, 'w:bz2') as tar:
                tar.add(source_path, arcname=Path(source_path).name)
        
        elif compression_format == 'tar.xz':
            archive_path = os.path.join(temp_dir, f"{archive_name}.tar.xz")
            with tarfile.open(archive_path, 'w:xz') as tar:
                tar.add(source_path, arcname=Path(source_path).name)
        
        elif compression_format == 'tar.zst':
            import compression.zstd
            archive_path = os.path.join(temp_dir, f"{archive_name}.tar.zst")
            tar_path = os.path.join(temp_dir, f"{archive_name}.tar")
            
            with tarfile.open(tar_path, 'w') as tar:
                tar.add(source_path, arcname=Path(source_path).name)
            
            with open(tar_path, 'rb') as f_in:
                with open(archive_path, 'wb') as f_out:
                    f_out.write(compression.zstd.compress(f_in.read()))
            
            os.remove(tar_path)
        
        elif compression_format == 'zip':
            archive_path = os.path.join(temp_dir, f"{archive_name}.zip")
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if os.path.isfile(source_path):
                    zipf.write(source_path, Path(source_path).name)
                else:
                    for root, dirs, files in os.walk(source_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, os.path.dirname(source_path))
                            zipf.write(file_path, arcname)
        
        elif compression_format == 'gzip':
            if os.path.isfile(source_path):
                archive_path = os.path.join(temp_dir, f"{archive_name}.gz")
                with open(source_path, 'rb') as f_in:
                    with gzip.open(archive_path, 'wb') as f_out:
                        f_out.writelines(f_in)
            else:
                raise ValueError("gzip compression only supports single files, not directories")
        
        else:
            raise ValueError(f"Unsupported compression format: {compression_format}")
        
        logger.info(f"Created archive: {archive_path}")
        return archive_path, temp_dir
    
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise e


def encrypt_file(input_path: str, recipient_key: str) -> str:
    try:
        with open(input_path, 'rb') as f:
            plaintext = f.read()
        
        recipient = x25519.Recipient.from_str(recipient_key)
        encrypted = pyrage.encrypt(plaintext, [recipient])  # type: ignore
        
        encrypted_path = f"{input_path}.age"
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted)
        
        logger.info(f"Encrypted file: {input_path} -> {encrypted_path}")
        return encrypted_path
    except Exception as e:
        logger.error(f"Failed to encrypt {input_path}: {e}")
        raise e


def decrypt_file(input_path: str, identity_key: str) -> str:
    try:
        with open(input_path, 'rb') as f:
            encrypted = f.read()
        
        identity = x25519.Identity.from_str(identity_key)
        decrypted = pyrage.decrypt(encrypted, [identity])  # type: ignore
        
        if input_path.endswith('.age'):
            decrypted_path = input_path[:-4]
        else:
            decrypted_path = f"{input_path}.decrypted"
        
        with open(decrypted_path, 'wb') as f:
            f.write(decrypted)
        
        logger.info(f"Decrypted file: {input_path} -> {decrypted_path}")
        return decrypted_path
    except Exception as e:
        logger.error(f"Failed to decrypt {input_path}: {e}")
        raise e


def extract_archive(archive_path: str, dest_path: str) -> bool:
    try:
        archive_name = Path(archive_path).name
        
        if archive_name.endswith('.tar.zst'):
            import compression.zstd
            
            decompressed_path = archive_path[:-4]
            with open(archive_path, 'rb') as f_in:
                with open(decompressed_path, 'wb') as f_out:
                    f_out.write(compression.zstd.decompress(f_in.read()))
            
            with tarfile.open(decompressed_path, 'r') as tar:
                tar.extractall(dest_path)
            
            os.remove(decompressed_path)
        
        elif archive_name.endswith('.tar.gz') or archive_name.endswith('.tgz'):
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(dest_path)
        
        elif archive_name.endswith('.tar.bz2'):
            with tarfile.open(archive_path, 'r:bz2') as tar:
                tar.extractall(dest_path)
        
        elif archive_name.endswith('.tar.xz'):
            with tarfile.open(archive_path, 'r:xz') as tar:
                tar.extractall(dest_path)
        
        elif archive_name.endswith('.tar'):
            with tarfile.open(archive_path, 'r') as tar:
                tar.extractall(dest_path)
        
        elif archive_name.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_file:
                zip_file.extractall(dest_path)
        
        elif archive_name.endswith('.gz'):
            import gzip
            output_path = os.path.join(dest_path, archive_name[:-3])
            with gzip.open(archive_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    data = f_in.read()
                    f_out.write(data)
        
        else:
            raise ValueError(f"Unsupported archive format: {archive_name}")
        
        logger.info(f"Extracted archive: {archive_path} -> {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to extract {archive_path}: {e}")
        raise e


def restore(backup_path: str, dest_path: str, dest_service: str = 'fs', identity_key: Optional[str] = None, storage_config: Optional[Dict[str, Any]] = None) -> bool:
    logger.info(f"Starting restore from {backup_path} to {dest_path}")
    
    try:
        dest_op = create_dest_operator(dest_service, storage_config)
        
        temp_dir = tempfile.mkdtemp()
        local_backup_path = os.path.join(temp_dir, Path(backup_path).name)
        
        try:
            backup_data = dest_op.read(backup_path)
            with open(local_backup_path, 'wb') as f:
                f.write(backup_data)
            
            logger.info(f"Downloaded backup: {backup_path} -> {local_backup_path}")
            
            current_path = local_backup_path
            
            if current_path.endswith('.age'):
                if not identity_key:
                    raise ValueError("Encrypted backup requires identity_key for decryption")
                
                logger.info("Decrypting backup...")
                decrypted_path = decrypt_file(current_path, identity_key)
                os.remove(current_path)
                current_path = decrypted_path
            
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
            
            logger.info("Extracting backup...")
            extract_archive(current_path, dest_path)
            
            logger.info(f"Restore completed successfully: {backup_path} -> {dest_path}")
            return True
        
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False


def list_available_backups(dest_service: str, dest_root: str = '', storage_config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    try:
        dest_op = create_dest_operator(dest_service, storage_config)
        backups = list_backups(dest_op, dest_root)
        
        if not backups:
            logger.info("No backups found")
            return []
        
        logger.info(f"Found {len(backups)} backups:")
        for backup in backups:
            size_mb = backup['size'] / (1024 * 1024)
            timestamp_str = backup['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"  {backup['path']} - {timestamp_str} ({size_mb:.2f} MB)")
        
        return backups
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        return []


def backup_file(src_op: opendal.Operator, dest_op: opendal.Operator, rel_path: str, dest_root: str) -> bool:
    try:
        data = src_op.read(rel_path)
        
        dest_path = os.path.join(dest_root, rel_path) if dest_root else rel_path
        
        dest_op.write(dest_path, data)
        logger.info(f"Backed up: {rel_path} -> {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to backup {rel_path}: {e}")
        return False


def list_files_recursive(op: opendal.Operator, path: str = "") -> List[str]:
    files = []
    try:
        entries = op.list(path)
        for entry in entries:
            entry_path = entry.path
            
            if entry_path == '/':
                continue
            
            metadata = op.stat(entry_path)
            if metadata.is_file:
                files.append(entry_path)
            elif metadata.is_dir:
                files.extend(list_files_recursive(op, entry_path))
    except Exception as e:
        logger.error(f"Error listing {path}: {e}")
    
    return files


def parse_backup_timestamp(filename: str) -> Optional[datetime]:
    patterns = [
        r'backup_.*?_(\d{8}_\d{6})',
        r'(\d{8}_\d{6})',
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            timestamp_str = match.group(1)
            try:
                if '_' in timestamp_str:
                    return datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                elif 'T' in timestamp_str:
                    return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                continue
    
    return None


def list_backups(dest_op: opendal.Operator, dest_root: str) -> List[Dict[str, Any]]:
    backups = []
    try:
        path = dest_root if dest_root else ""
        entries = dest_op.list(path)
        
        for entry in entries:
            entry_path = entry.path
            metadata = dest_op.stat(entry_path)
            
            if metadata.is_file:
                timestamp = parse_backup_timestamp(entry_path)
                if timestamp:
                    backups.append({
                        'path': entry_path,
                        'timestamp': timestamp,
                        'size': metadata.content_length
                    })
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
    
    backups.sort(key=lambda x: x['timestamp'], reverse=True)
    return backups


def apply_retention_policy(backups: List[Dict[str, Any]], max_backups: int = 0, daily: int = 7, weekly: int = 4, monthly: int = 6, yearly: int = 2) -> List[Dict[str, Any]]:
    if not backups:
        return []
    
    to_keep = set()
    now = datetime.now()
    
    daily_kept = defaultdict(list)
    weekly_kept = defaultdict(list)
    monthly_kept = defaultdict(list)
    yearly_kept = defaultdict(list)
    
    for backup in backups:
        ts = backup['timestamp']
        
        day_key = (ts.year, ts.month, ts.day)
        week_key = (ts.year, ts.isocalendar()[1])
        month_key = (ts.year, ts.month)
        year_key = ts.year
        
        daily_kept[day_key].append(backup)
        weekly_kept[week_key].append(backup)
        monthly_kept[month_key].append(backup)
        yearly_kept[year_key].append(backup)
    
    for day_key in sorted(daily_kept.keys(), reverse=True)[:daily]:
        if daily_kept[day_key]:
            to_keep.add(daily_kept[day_key][0]['path'])
    
    for week_key in sorted(weekly_kept.keys(), reverse=True)[:weekly]:
        if weekly_kept[week_key]:
            to_keep.add(weekly_kept[week_key][0]['path'])
    
    for month_key in sorted(monthly_kept.keys(), reverse=True)[:monthly]:
        if monthly_kept[month_key]:
            to_keep.add(monthly_kept[month_key][0]['path'])
    
    for year_key in sorted(yearly_kept.keys(), reverse=True)[:yearly]:
        if yearly_kept[year_key]:
            to_keep.add(yearly_kept[year_key][0]['path'])
    
    if max_backups > 0:
        recent_backups = [b['path'] for b in backups[:max_backups]]
        to_keep.update(recent_backups)
    
    to_delete = [b for b in backups if b['path'] not in to_keep]
    
    return to_delete


def cleanup_old_backups(dest_op: opendal.Operator, retention_config: Dict[str, Any]) -> None:
    if not any([
        retention_config.get('max_backups', 0) > 0,
        retention_config.get('daily', 0) > 0,
        retention_config.get('weekly', 0) > 0,
        retention_config.get('monthly', 0) > 0,
        retention_config.get('yearly', 0) > 0
    ]):
        logger.info("No retention policy configured, skipping cleanup")
        return
    
    logger.info("Checking for old backups to clean up...")
    
    backups = list_backups(dest_op, retention_config.get('dest_root', ''))
    
    if not backups:
        logger.info("No backups found")
        return
    
    logger.info(f"Found {len(backups)} existing backups")
    
    to_delete = apply_retention_policy(
        backups,
        max_backups=retention_config.get('max_backups', 0),
        daily=retention_config.get('daily', 7),
        weekly=retention_config.get('weekly', 4),
        monthly=retention_config.get('monthly', 6),
        yearly=retention_config.get('yearly', 2)
    )
    
    if not to_delete:
        logger.info("No backups to delete")
        return
    
    logger.info(f"Deleting {len(to_delete)} old backups...")
    
    deleted_count = 0
    for backup in to_delete:
        try:
            dest_op.delete(backup['path'])
            logger.info(f"Deleted: {backup['path']} (from {backup['timestamp'].strftime('%Y-%m-%d %H:%M:%S')})")
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to delete {backup['path']}: {e}")
    
    logger.info(f"Cleanup completed: {deleted_count} backups deleted, {len(backups) - deleted_count} retained")


def backup(source_path: str, destinations: List[Dict[str, Any]], compression: str = 'none', archive_name: Optional[str] = None, retention_config: Optional[Dict[str, Any]] = None, encryption_enabled: bool = False, encryption_recipient: Optional[str] = None) -> bool:
    logger.info(f"Starting backup from {source_path} to {len(destinations)} destination(s)")
    
    if not destinations:
        logger.error("No destinations provided")
        return False
    
    results = []
    
    if compression == 'none':
        src_op = create_source_operator(source_path)
        files = list_files_recursive(src_op)
        logger.info(f"Found {len(files)} files to backup")
        
        for idx, dest in enumerate(destinations, 1):
            dest_service = dest['service']
            dest_root = dest.get('root', '')
            storage_config = dest.get('storage', {})
            
            logger.info(f"Backing up to destination {idx}/{len(destinations)}: {dest_service}")
            
            try:
                dest_op = create_dest_operator(dest_service, storage_config)
                
                success_count = 0
                fail_count = 0
                
                for file_path in files:
                    if backup_file(src_op, dest_op, file_path, dest_root):
                        success_count += 1
                    else:
                        fail_count += 1
                
                logger.info(f"Destination {idx} completed: {success_count} succeeded, {fail_count} failed")
                dest_success = fail_count == 0
                results.append({'destination': dest_service, 'success': dest_success})
                
                if dest_success and retention_config:
                    retention_with_root = {**retention_config, 'dest_root': dest_root}
                    cleanup_old_backups(dest_op, retention_with_root)
            except Exception as e:
                logger.error(f"Failed to backup to destination {idx} ({dest_service}): {e}")
                results.append({'destination': dest_service, 'success': False})
    else:
        archive_path, temp_dir = create_archive(source_path, compression, archive_name)
        
        try:
            if encryption_enabled and encryption_recipient:
                logger.info("Encrypting archive...")
                encrypted_path = encrypt_file(archive_path, encryption_recipient)
                os.remove(archive_path)
                archive_path = encrypted_path
            
            with open(archive_path, 'rb') as f:
                archive_data = f.read()
            
            archive_filename = Path(archive_path).name
            
            for idx, dest in enumerate(destinations, 1):
                dest_service = dest['service']
                dest_root = dest.get('root', '')
                storage_config = dest.get('storage', {})
                
                logger.info(f"Uploading to destination {idx}/{len(destinations)}: {dest_service}")
                
                try:
                    dest_op = create_dest_operator(dest_service, storage_config)
                    dest_path = os.path.join(dest_root, archive_filename) if dest_root else archive_filename
                    
                    dest_op.write(dest_path, archive_data)
                    logger.info(f"Destination {idx} completed: {archive_filename} -> {dest_path}")
                    
                    results.append({'destination': dest_service, 'success': True})
                    
                    if retention_config:
                        retention_with_root = {**retention_config, 'dest_root': dest_root}
                        cleanup_old_backups(dest_op, retention_with_root)
                except Exception as e:
                    logger.error(f"Failed to upload to destination {idx} ({dest_service}): {e}")
                    results.append({'destination': dest_service, 'success': False})
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    success_count = sum(1 for r in results if r['success'])
    logger.info(f"Backup completed: {success_count}/{len(destinations)} destinations succeeded")
    
    return all(r['success'] for r in results)


def run_backup_job() -> None:
    try:
        config = load_config()
        
        if not validate_destinations(config['destinations']):
            logger.error("Destination validation failed. Aborting backup.")
            return
        
        retention_config = {
            'max_backups': config['retention_max_backups'],
            'daily': config['retention_daily'],
            'weekly': config['retention_weekly'],
            'monthly': config['retention_monthly'],
            'yearly': config['retention_yearly'],
        }
        backup(
            config['source_path'],
            config['destinations'],
            config['compression'],
            config['archive_name'],
            retention_config,
            config['encryption_enabled'],
            config['encryption_recipient']
        )
    except Exception as e:
        logger.error(f"Scheduled backup failed: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Simple Backup - Backup and Restore Tool')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    backup_parser = subparsers.add_parser('backup', help='Create a backup')
    backup_parser.add_argument('--config', action='store_true', help='Use configuration from environment variables')
    
    restore_parser = subparsers.add_parser('restore', help='Restore from a backup')
    restore_parser.add_argument('backup_path', help='Path to the backup file in the destination storage')
    restore_parser.add_argument('dest_path', help='Local directory to restore to')
    restore_parser.add_argument('--dest-service', default='fs', help='Destination service type (default: fs)')
    restore_parser.add_argument('--identity-key', help='Age identity key for decryption (if backup is encrypted)')
    
    list_parser = subparsers.add_parser('list', help='List available backups')
    list_parser.add_argument('--dest-service', default='fs', help='Destination service type (default: fs)')
    list_parser.add_argument('--dest-root', default='', help='Root directory in destination storage')
    
    args = parser.parse_args()
    
    if args.command == 'restore':
        config = load_config()
        first_dest = config['destinations'][0] if config['destinations'] else {}
        storage_config = first_dest.get('storage', {})
        identity_key = args.identity_key or os.getenv('AGE_IDENTITY_KEY')
        success = restore(
            args.backup_path,
            args.dest_path,
            args.dest_service,
            identity_key,
            storage_config
        )
        sys.exit(0 if success else 1)
    
    elif args.command == 'list':
        config = load_config()
        first_dest = config['destinations'][0] if config['destinations'] else {}
        storage_config = first_dest.get('storage', {})
        list_available_backups(args.dest_service, args.dest_root, storage_config)
        sys.exit(0)
    
    else:
        try:
            config = load_config()
            
            if not validate_destinations(config['destinations']):
                logger.error("Destination validation failed. Please check your configuration and network connectivity.")
                sys.exit(1)
            
            if config['cron_schedule']:
                logger.info(f"Starting backup scheduler with cron: {config['cron_schedule']}")
                scheduler = BlockingScheduler()
                scheduler.add_job(
                    run_backup_job,
                    CronTrigger.from_crontab(config['cron_schedule']),
                    id='backup_job'
                )
                
                def signal_handler(signum, frame):
                    logger.info("Shutting down scheduler...")
                    scheduler.shutdown()
                    sys.exit(0)
                
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
                
                logger.info("Backup scheduler started. Press Ctrl+C to stop.")
                scheduler.start()
            else:
                retention_config = {
                    'max_backups': config['retention_max_backups'],
                    'daily': config['retention_daily'],
                    'weekly': config['retention_weekly'],
                    'monthly': config['retention_monthly'],
                    'yearly': config['retention_yearly'],
                }
                success = backup(
                    config['source_path'],
                    config['destinations'],
                    config['compression'],
                    config['archive_name'],
                    retention_config,
                    config['encryption_enabled'],
                    config['encryption_recipient']
                )
                sys.exit(0 if success else 1)
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
