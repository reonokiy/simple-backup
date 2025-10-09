import os
import sys
import logging
import signal
import tarfile
import zipfile
import gzip
import bz2
import lzma
import zlib
import tempfile
import shutil
import re
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import opendal
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from pyrage import x25519, passphrase
import pyrage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config():
    config = {
        'source_path': os.getenv('BACKUP_SOURCE_PATH'),
        'dest_service': os.getenv('BACKUP_DEST_SERVICE'),
        'dest_root': os.getenv('BACKUP_DEST_ROOT', ''),
        'cron_schedule': os.getenv('BACKUP_CRON_SCHEDULE'),
        'compression': os.getenv('BACKUP_COMPRESSION', 'tar.zst'),
        'archive_name': os.getenv('BACKUP_ARCHIVE_NAME'),
        'retention_max_backups': int(os.getenv('BACKUP_RETENTION_MAX_BACKUPS', '0')),
        'retention_daily': int(os.getenv('BACKUP_RETENTION_DAILY', '7')),
        'retention_weekly': int(os.getenv('BACKUP_RETENTION_WEEKLY', '4')),
        'retention_monthly': int(os.getenv('BACKUP_RETENTION_MONTHLY', '6')),
        'retention_yearly': int(os.getenv('BACKUP_RETENTION_YEARLY', '2')),
        'encryption_enabled': os.getenv('BACKUP_ENCRYPTION_ENABLED', 'false').lower() == 'true',
        'encryption_recipient': os.getenv('BACKUP_ENCRYPTION_RECIPIENT'),
        'encryption_identity': os.getenv('BACKUP_ENCRYPTION_IDENTITY'),
    }
    
    if not config['source_path']:
        raise ValueError("BACKUP_SOURCE_PATH environment variable is required")
    if not config['dest_service']:
        raise ValueError("BACKUP_DEST_SERVICE environment variable is required")
    
    valid_compressions = ['none', 'tar', 'tar.gz', 'tar.bz2', 'tar.xz', 'tar.zst', 'zip', 'gzip']
    if config['compression'] not in valid_compressions:
        raise ValueError(f"Invalid compression format. Must be one of: {', '.join(valid_compressions)}")
    
    if config['encryption_enabled'] and not config['encryption_recipient']:
        raise ValueError("BACKUP_ENCRYPTION_RECIPIENT is required when encryption is enabled")
    
    return config


def create_source_operator(source_path):
    return opendal.Operator("fs", root=source_path)


def create_dest_operator(service_type):
    service_configs = {
        's3': {
            'bucket': os.getenv('S3_BUCKET'),
            'region': os.getenv('S3_REGION'),
            'access_key_id': os.getenv('S3_ACCESS_KEY_ID'),
            'secret_access_key': os.getenv('S3_SECRET_ACCESS_KEY'),
            'endpoint': os.getenv('S3_ENDPOINT'),
        },
        'azblob': {
            'container': os.getenv('AZURE_CONTAINER'),
            'account_name': os.getenv('AZURE_ACCOUNT_NAME'),
            'account_key': os.getenv('AZURE_ACCOUNT_KEY'),
        },
        'gcs': {
            'bucket': os.getenv('GCS_BUCKET'),
            'credential': os.getenv('GCS_CREDENTIAL'),
        },
        'fs': {
            'root': os.getenv('FS_ROOT'),
        },
        'oss': {
            'bucket': os.getenv('OSS_BUCKET'),
            'endpoint': os.getenv('OSS_ENDPOINT'),
            'access_key_id': os.getenv('OSS_ACCESS_KEY_ID'),
            'access_key_secret': os.getenv('OSS_ACCESS_KEY_SECRET'),
        },
        'obs': {
            'bucket': os.getenv('OBS_BUCKET'),
            'endpoint': os.getenv('OBS_ENDPOINT'),
            'access_key_id': os.getenv('OBS_ACCESS_KEY_ID'),
            'secret_access_key': os.getenv('OBS_SECRET_ACCESS_KEY'),
        },
        'cos': {
            'bucket': os.getenv('COS_BUCKET'),
            'region': os.getenv('COS_REGION'),
            'secret_id': os.getenv('COS_SECRET_ID'),
            'secret_key': os.getenv('COS_SECRET_KEY'),
        },
        'webdav': {
            'endpoint': os.getenv('WEBDAV_ENDPOINT'),
            'username': os.getenv('WEBDAV_USERNAME'),
            'password': os.getenv('WEBDAV_PASSWORD'),
        },
    }
    
    if service_type not in service_configs:
        raise ValueError(f"Unsupported service type: {service_type}")
    
    config = service_configs[service_type]
    config = {k: v for k, v in config.items() if v is not None}
    
    return opendal.Operator(service_type, **config)


def create_archive(source_path, compression_format, archive_name=None):
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


def encrypt_file(input_path, recipient_key):
    try:
        with open(input_path, 'rb') as f:
            plaintext = f.read()
        
        recipient = x25519.Recipient.from_str(recipient_key)
        encrypted = pyrage.encrypt(plaintext, [recipient])
        
        encrypted_path = f"{input_path}.age"
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted)
        
        logger.info(f"Encrypted file: {input_path} -> {encrypted_path}")
        return encrypted_path
    except Exception as e:
        logger.error(f"Failed to encrypt {input_path}: {e}")
        raise e


def decrypt_file(input_path, identity_key):
    try:
        with open(input_path, 'rb') as f:
            encrypted = f.read()
        
        identity = x25519.Identity.from_str(identity_key)
        decrypted = pyrage.decrypt(encrypted, [identity])
        
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


def extract_archive(archive_path, dest_path):
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
                    f_out.write(f_in.read())
        
        else:
            raise ValueError(f"Unsupported archive format: {archive_name}")
        
        logger.info(f"Extracted archive: {archive_path} -> {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to extract {archive_path}: {e}")
        raise e


def restore(backup_path, dest_path, dest_service='fs', identity_key=None):
    logger.info(f"Starting restore from {backup_path} to {dest_path}")
    
    try:
        dest_op = create_dest_operator(dest_service)
        
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


def list_available_backups(dest_service, dest_root=''):
    try:
        dest_op = create_dest_operator(dest_service)
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


def backup_file(src_op, dest_op, rel_path, dest_root):
    try:
        data = src_op.read(rel_path)
        
        dest_path = os.path.join(dest_root, rel_path) if dest_root else rel_path
        
        dest_op.write(dest_path, data)
        logger.info(f"Backed up: {rel_path} -> {dest_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to backup {rel_path}: {e}")
        return False


def list_files_recursive(op, path=""):
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


def parse_backup_timestamp(filename):
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


def list_backups(dest_op, dest_root):
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


def apply_retention_policy(backups, max_backups=0, daily=7, weekly=4, monthly=6, yearly=2):
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


def cleanup_old_backups(dest_op, retention_config):
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


def backup(source_path, dest_service, dest_root, compression='none', archive_name=None, retention_config=None, encryption_enabled=False, encryption_recipient=None):
    logger.info(f"Starting backup from {source_path} to {dest_service}")
    
    dest_op = create_dest_operator(dest_service)
    
    if compression == 'none':
        src_op = create_source_operator(source_path)
        files = list_files_recursive(src_op)
        logger.info(f"Found {len(files)} files to backup")
        
        success_count = 0
        fail_count = 0
        
        for file_path in files:
            if backup_file(src_op, dest_op, file_path, dest_root):
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"Backup completed: {success_count} succeeded, {fail_count} failed")
        success = fail_count == 0
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
            dest_path = os.path.join(dest_root, archive_filename) if dest_root else archive_filename
            
            dest_op.write(dest_path, archive_data)
            logger.info(f"Backup completed: {archive_filename} -> {dest_path}")
            
            success = True
        except Exception as e:
            logger.error(f"Failed to backup archive: {e}")
            success = False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    if success and retention_config:
        cleanup_old_backups(dest_op, retention_config)
    
    return success


def run_backup_job():
    try:
        config = load_config()
        retention_config = {
            'max_backups': config['retention_max_backups'],
            'daily': config['retention_daily'],
            'weekly': config['retention_weekly'],
            'monthly': config['retention_monthly'],
            'yearly': config['retention_yearly'],
            'dest_root': config['dest_root']
        }
        backup(
            config['source_path'],
            config['dest_service'],
            config['dest_root'],
            config['compression'],
            config['archive_name'],
            retention_config,
            config['encryption_enabled'],
            config['encryption_recipient']
        )
    except Exception as e:
        logger.error(f"Scheduled backup failed: {e}")


def main():
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
        identity_key = args.identity_key or os.getenv('AGE_IDENTITY_KEY')
        success = restore(
            args.backup_path,
            args.dest_path,
            args.dest_service,
            identity_key
        )
        sys.exit(0 if success else 1)
    
    elif args.command == 'list':
        list_available_backups(args.dest_service, args.dest_root)
        sys.exit(0)
    
    else:
        try:
            config = load_config()
            
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
                    'dest_root': config['dest_root']
                }
                success = backup(
                    config['source_path'],
                    config['dest_service'],
                    config['dest_root'],
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
